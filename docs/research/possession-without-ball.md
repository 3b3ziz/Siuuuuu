# Who has the ball when the ball is missing

Research notes, Nov 2026. Question: how to label home / away / dead ball per frame when ball tracking drops out (about 15% of live frames, gaps of 5-45 s, often near the touchlines), and how to tell real controlled possession from touches and deflections. Every claim links to the paper or code that owns it. Where I only saw an abstract or a search snippet, I say so.

## Most promising for us

- **A ready-made, ball-free model trained on the exact Bundesliga matches we have.** PathCRF (KDD 2026) guesses who has the ball from player movement only. It was trained on the same 7 DFL/IDSSE matches, and the repo ships trained weights. Its team possession is right on 92.4% of frames, with no ball at all ([paper](https://arxiv.org/abs/2602.12080), [repo](https://github.com/hyunsungkim-ds/pathcrf)). We'd only need it inside our gaps, where we also know who had the ball just before and just after. Downsides: it's a PyTorch deep model, not numpy. It runs at 5 frames a second. While the ball is in flight, it outputs a passer→receiver link with no single owner, so we'd have to pick which end counts. The paper doesn't say how it turns those links into teams for the 92.4%, or which frames it counts. And when it moved to a different data provider, scores fell 14-25 points (section 3).
- **A simple sklearn recipe that's been shown to work, worth copying with possession as the target.** Lang et al. (2022) predicted ball in play vs stopped from player positions only, at 92% of frames right on 47 unseen Bundesliga and Bundesliga 2 matches. Setup: AdaBoost (a standard sklearn classifier). Inputs: x, y, speed and acceleration of all 22 players at the current frame plus 7 past and 7 future offsets (0.4, 0.8, 2, 4, 20, 40, 80 s). Training data doubled by swapping home and away. Output smoothed with a 3.64 s median filter ([paper](https://www.nature.com/articles/s41598-022-19948-1)). Nobody has published this exact recipe for possession. Trying it is our idea, not theirs. It also directly targets our "play stopped" label.
- **The published rule for "touch vs real possession": the ball must change direction or speed near the player, and a duel beats possession.** Vidal-Codina et al. (2022): a player "has" the ball when it's within 0.5-1 m of them (the "possession zone"). Two opponents within 1 m of the ball count as a duel, and a duel overrides possession. A spell only counts as a gain if the ball's direction or speed changes during it. Otherwise it's "the ball travelled past" and gets dropped ([paper](https://arxiv.org/abs/2202.00804)). databallpy has a 250-line numpy/pandas version of this, without the duel rule ([code](https://github.com/alek050/databallpy/blob/a2ab78c4c7ba3ad964ab26dd65dd848de3939d18/databallpy/features/player_possession.py)).
- **Be realistic about the middle of a long gap.** Rebuilding the ball from players alone is off by about 2.7-5.4 m on average ([Kim et al. 2023](https://arxiv.org/abs/2306.08206), [Capellera et al. 2024](https://arxiv.org/abs/2410.17785)). The best team-level possession reported without any ball is 84-92% of frames. Strong results with 80-90% of the ball hidden come from *randomly scattered* hidden frames. That's much easier than our long unbroken gaps, so don't count on them.
- **Throw-ins: a cheap trigger.** Our gaps cluster near the touchlines. Vidal-Codina et al. flag a throw-in when, during a dead-ball spell, a player stands beyond the touchline, within a small allowance ([paper](https://arxiv.org/abs/2202.00804)). That player's team takes the restart, so it's possession evidence without seeing the ball.

## Words used

- **Possession zone**: a circle around a player; ball inside it means the player could play it.
- **Duel zone**: a circle around the ball; two opponents inside means a contest, not possession.
- **Imputation**: filling in missing values (here, ball positions) from the context around them.
- **ADE / position error**: average distance in metres between the guessed ball and the real ball.
- **F1**: one score that combines "how many of my calls were right" (precision) and "how many of the real ones I found" (recall). 1 is perfect.
- **Domain shift**: a model trained on one source (league, provider, camera system) doing worse on another.
- **Edge accuracy** (PathCRF): share of frames where it picks the right state, either "player X has it" or "ball travelling from X to Y".

---

## 1. Telling possession from player positions only (no ball)

**What exists with real accuracy numbers:**

| Method | Input | Data | Team possession accuracy | Notes |
|---|---|---|---|---|
| PathCRF, Kim et al. 2026 ([arXiv](https://arxiv.org/abs/2602.12080)) | All 22 player tracks over time | 7 DFL/IDSSE matches (5 train / 1 val / 1 test), down to 5 fps | **92.40% of frames** | Home share 62.64% guessed vs 62.13% real. Authors say errors "tend to cancel out over time". That helps possession *share*, not our per-possession score. Doesn't say which frames are counted. |
| Ball Radar, Kim et al. 2023 ([arXiv](https://arxiv.org/abs/2306.08206), KDD 2023) | 22 players: x, y, velocity, speed, acceleration; 10 s windows at 10 Hz | 15 K League GPS matches plus Metrica's 3 sample games | **85.85%** (best model, no ball at all) | Who exactly has it (player level): 64.70%. Table 2. |
| Baouan et al. 2025 ([arXiv](https://arxiv.org/abs/2501.10299)) | **One** team's 11 players, single frame, pitch flipped so the team attacks right | Ligue 1 2021-22, Stats Perform | 81.7% (logistic regression on a sorted-projection "embedding") | **Average player positions alone: about 59%** (near a coin flip). The split looks like random frames, not by match, so neighbouring frames can leak between train and test. Treat 82% as optimistic. |

**Takeaways:**

- A single snapshot of team shape is weak. Average positions only reach about 59% ([Baouan et al., Table 1](https://arxiv.org/abs/2501.10299)). What works is movement over time across all 22 players (Kim 2023, PathCRF).
- **Gap: I found no primary paper that reports possession accuracy for hand-made team-shape features** (compactness, width/length, defensive line height, centroid speed toward goal) used as a classifier. The papers on these features only describe them:
  - Welch et al. 2021 ([PLOS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0251970)), 2 Norwegian matches at 20 Hz. When defending, the team is more compact (convex-hull area mostly 300-1000 m² vs 300-2000 m² when attacking). It's also more aligned in movement direction, and mostly moves at 3-4 m/s as a group. Out of play, group speed is mostly under 2 m/s. No classifier was trained.
  - Frencken & Lemmink 2011, small-sided 4v4 games ([record](https://lida.sport-iat.de/dfb/Record/4022059)). The two teams' centroids move forward and back together. Before 10 of 19 goals the centroids crossed. Surface area showed no clear pattern. (Abstract only.)
  - Shaw & Glickman 2019 ([PDF](https://www.sportperformanceanalysis.com/s/Dynamic-analysis-of-team-strategy-in-professional-football-By-Laurie-Shaw-And-Mark-Glickman.pdf)), 180 matches. Formations in and out of possession differ clearly. But they pool 2-minute windows and drop possessions under 5 s, so it isn't a per-frame method.
- So team-shape features are reasonable *inputs* to a Lang-style classifier (section 2). But nobody has published how well they work alone. We'd be the first to measure it, on the DFL matches.
- Useful tool: floodlight has team centroid and spread ("stretch index") helpers in [`models/geometry.py`](https://github.com/floodlight-sports/floodlight/blob/699b7fa1e37f6de2351079d64508551bf5fb9ad7/floodlight/models/geometry.py).

## 2. Detecting controlled possession vs touches and deflections

### Vidal-Codina et al. 2022, rule-based ([arXiv](https://arxiv.org/abs/2202.00804))

A fixed set of rules (no learning). Every frame is one of: dead ball, no possession, possession, duel.

- **Possession zone:** radius 0.5 m for Track160 data, 1 m for TRACAB and Hawk-Eye (Section 3). Larger for worse data, per their discussion.
- **Duel zone:** 1 m around the ball. A duel is "at least two opponents" inside it, and duel beats possession.
- **Gain:** a run of frames with the ball in one player's zone counts only if the ball changes direction (dot product of in and out direction below a threshold) or changes speed by more than a threshold on at least one frame. Otherwise "we consider that these control frames are false positives" (the ball just passed near the player).
- **Loss:** the ball leaves the player's zone and moves more than a minimum distance, *and* that player isn't the next one to control it. So a player who pushes the ball ahead and catches up keeps possession.
- **Smoothing:** with noisy ball data, a Savitzky-Golay filter (a standard smoothing filter), 2nd order, 7-frame window.
- **Threshold values** (minimum direction change, speed change, displacement) are **not in the main text**. They're in an online supplement I couldn't reach. The authors recommend re-tuning them for each provider.
- **Results:** passes over 90% precision and recall. Corners, throw-ins and goal kicks over 90%. Shots weaker (precision 78, recall 53), mostly blocked shots read as passes. Data: FIFA Club World Cup 2019/2020 and Bundesliga 2019-20, three providers, 25 Hz. Only pooled numbers, no per-provider split.
- **Set-piece triggers during dead ball.** Throw-in: a player beyond "sideline minus ε_t". Corner: a player within ε_c of a corner mark. Kick-off: everyone in their own half and someone near the centre spot. Goal kick and penalty are similar (Section 2.3.4). Again, the ε values are in the supplement.
- They name "team possession information" as **future work**. The paper doesn't define team possession.

### databallpy (open source, numpy/pandas)

- [`add_individual_player_possession`](https://github.com/alek050/databallpy/blob/a2ab78c4c7ba3ad964ab26dd65dd848de3939d18/databallpy/schemas/tracking_data.py#L348-L403) says it follows Vidal-Codina. **The defaults are the package's own picks, not the paper's:** zone radius 1.5 m, ball speed change 5 m/s, ball direction change 10°, minimum frames 0.
- How it works ([code](https://github.com/alek050/databallpy/blob/a2ab78c4c7ba3ad964ab26dd65dd848de3939d18/databallpy/features/player_possession.py)). The nearest player within the radius is the candidate. A spell is valid if the angle between the ball's incoming and outgoing direction is over 10°, or the frame-to-frame ball speed jumps by over 5 m/s. Possession only covers valid spells, so frames with the ball in flight get no owner. **No duel rule.**
- Its [`add_team_possession`](https://github.com/alek050/databallpy/blob/a2ab78c4c7ba3ad964ab26dd65dd848de3939d18/databallpy/schemas/tracking_data.py#L785) is built from **event data** (team changes on a successful pass, dribble or shot by the other team), not from tracking. So it's no use for us.

### kloppy and floodlight

- They only pass the provider's own possession flag through. No algorithm. E.g. kloppy reads TRACAB's H/A flag ([dat.py](https://github.com/PySport/kloppy/blob/a9651eba7c4dbbe2d2fc6d4cffb4aea63fadac11/kloppy/infra/serializers/tracking/tracab/parsers/raw_data/dat.py#L111-L114)). floodlight reads DFL possession and ball status into "Code" objects ([dfl.py](https://github.com/floodlight-sports/floodlight/blob/699b7fa1e37f6de2351079d64508551bf5fb9ad7/floodlight/io/dfl.py#L644)).

### Link & Hoernig 2017, individual ball possession ([PLOS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0179953))

- Defines several layers. **Ball action** (the player can act on the ball). **Ball control** (a ball action where the player has a real choice of what to do next). **Team ball possession** (from one team's first player possession until the other team's first). Team control is just the union of that team's control spells.
- **Start:** nearest player within distance T_P. Optional "kick detection" also needs a local peak in ball acceleration of at least 4 m/s². This stops a ball flying *over* a player from counting (they had no ball height).
- **End:** another player takes over, or the ball (projected 1 s ahead from its speed and direction) moves out of reach. Projecting the player forward too didn't help.
- **Control vs touch:** a Bayesian network (a small probabilistic model). Features: spell duration, mean and variance of ball speed and acceleration, mean player-ball distance, and the number of opponents within 0.5 m, 1 m, ... 5 m.
- **Results:** ball action F1 0.88, possession F1 0.83. Control was right on 97% of real control spells but only 50% of non-control ones (agreement score κ 0.67, against 0.72 between two humans). The threshold values T_P etc. aren't given in the text.
- **Data:** 60 Bundesliga TRACAB matches, 25 Hz. The text says both 2012/13 and 2013/14. 5 matches were hand-labelled.
- **Known weak spots** (theirs): possession can start before any contact. Light touches under the acceleration threshold get missed. Back-to-ball positions confuse it. "Ping-pong" (ball bouncing between players with no control) is treated as possession without control.
- Earlier conference version (Hoernig et al. 2016): precision and recall 80-92% on clean data, about 4 points less on uncorrected data. *From the abstract only, not checked against the full text.*

### Lang et al. 2022, ball in play vs stopped from players only ([Sci. Rep.](https://www.nature.com/articles/s41598-022-19948-1))

Same Munich group as Link. Relevant to our D label, and a template for a possession classifier.

- **Data:** 102 matches, Bundesliga and Bundesliga 2, 2017/18, TRACAB, 25 fps. Ball status was "collected manually by human observers". Split: 45 train / 10 val / 47 test. All Bundesliga 2 matches are in the test set.
- **Features:** 1320 per frame. That's x, y, speed and acceleration for 22 players, at 15 times: now, plus 0.4, 0.8, 2, 4, 20, 40, 80 s back and forward. Players are ordered by the team sheet. Coordinates are flipped in the 2nd half. Training is doubled by swapping home and away.
- **Models** (sklearn): logistic regression, decision tree, random forest, AdaBoost. AdaBoost was best: **frame accuracy 0.92, F1 0.93**. The others scored 0.87-0.91.
- **Stoppages over 2 s:** after a 3.64 s (91-frame) median filter, AdaBoost F1 is 0.80 (random forest 0.68, logistic regression 0.61). A stoppage counts as found if it overlaps the real one by at least 50%. For 77% of found stoppages the start is within 2 s, and for 81% the end is.
- Use the paper's 92%. TUM's press release says 93%.

### What our training labels mean

- In the DFL/IDSSE data, the per-frame `BallPossession` flag is "defined by the player in control of the ball". `BallStatus` is inactive "when the match is interrupted by the referee" ([Bassek et al. 2025, Sci. Data](https://www.nature.com/articles/s41597-025-04505-y)). That matches our "controlled possession" idea. But **the paper doesn't say how the flag is made** (operators, an algorithm, or both). Open question.
- Label conventions differ between papers. Ball Radar labels a pass's receiver as owner from the moment the pass leaves ([Kim 2023](https://arxiv.org/abs/2306.08206)). PathCRF builds labels from synced event data, not the DFL flag ([PathCRF](https://arxiv.org/abs/2602.12080)). databallpy gives no owner while the ball is in flight. Check which convention the challenge scorer uses before copying any of them.

## 3. Moving from one league or provider to another

- **PathCRF, Appendix B / Table 6** ([arXiv](https://arxiv.org/abs/2602.12080)). Event F1 trained and tested on the same source: K League 79.8, DFL 73.9. Trained on K League, tested on DFL: 66.3 (−13.6 against the model's score on its own training source). Trained on DFL, tested on K League: 49.2 (−24.7, same comparison). Against a model trained on the target source, the drops are −7.6 on DFL and −30.7 on K League. The edge-accuracy drops are similar (−15.5, −25.1). **Caveat:** K League here is wearable GPS and DFL is camera tracking, with different labelling. So this overstates the drop for a camera-to-camera move like ours.
- **Lang et al. 2022** ([Sci. Rep.](https://www.nature.com/articles/s41598-022-19948-1)). Trained on Bundesliga only, tested on Bundesliga 2 and Bundesliga. Stoppage F1 0.79 vs 0.80, almost no drop. Same provider and system, though, so it's weak evidence for a move to another league.
- **Vidal-Codina et al. 2022** ([arXiv](https://arxiv.org/abs/2202.00804)). Needed a different zone radius per provider (0.5 m vs 1 m). They recommend tuning thresholds per provider by cross-validation. No per-provider scores.
- **Kim 2023** ([arXiv](https://arxiv.org/abs/2306.08206)). Mixed GPS and Metrica data in training and testing, but reports no split by source and no cross-provider test.
- **What this means for us** (our inference): rules with physical thresholds (metres, m/s) should move between providers better than a model fed raw coordinates, but expect to re-tune the radius. For any model trained on DFL, check it on Metrica first (another provider) before trusting it on LaLiga.

## 4. Filling in the ball from player positions

| Method | Data | Ball fully hidden | Ball partly hidden | Notes |
|---|---|---|---|---|
| Ball Radar, Kim et al. 2023 ([arXiv](https://arxiv.org/abs/2306.08206)) | K League GPS plus Metrica, 10 Hz, 10 s windows | 3.66 m avg error (best). Team possession 85.85% | Table 3 (apparently the K League test only): 95% hidden 3.0 m and 91.5% team possession. 80% hidden 1.3 m and 97.4% | Hidden frames picked "randomly ... by a certain probability", **scattered, not long gaps.** Table 3's 100%-hidden row is 5.35 m and 84.0% team possession. |
| TranSPORTmer, Capellera et al. 2024 ([arXiv](https://arxiv.org/abs/2410.17785), ACCV 2024) | LaLiga 2022-23, 283 matches, 6.25 Hz, 9.6 s windows | 2.71 m avg error (Ball Radar on the same data: 3.89 m) | 90% hidden about 1.1 m. 80% hidden about 0.8-0.9 m | Also sorts frames into pass / possession / uncontrolled / out of play, with only about 81% accuracy when the ball is fully hidden. It doesn't say whether the hidden frames are in one block. Dataset and table layout taken from the HTML version; check against the PDF before quoting. **Rule risk:** it was trained on LaLiga 2022-23, which could include our own Barça-Athletic match. Using its weights could break the "no outside data about this match" rule. PathCRF (DFL only) and Ball Radar (K League plus Metrica) don't have this problem. |
| Amirli & Alemdar 2022 ([journal](https://dergipark.org.tr/en/pub/apjess/article/1060725)) | Turkish Süper Lig 2017-18, 300 matches | Error 7.56 m along the length, 5.01 m across | – | Simple neural network on player positions. From the abstract. |
| PathCRF's "Ball TP" baseline ([arXiv](https://arxiv.org/abs/2602.12080)) | DFL 7 matches | 2.74 m | – | Guessing the ball and then applying Ball Radar's touch rules gave only 47% edge accuracy, against about 70% for PathCRF. |

- Ball Radar's touch rule after rebuilding the ball ([Kim 2023](https://arxiv.org/abs/2306.08206)). Score = (chance this player has it) / (distance from guessed ball to player). Over 0.5 means touching it. Between 0.2 and 0.5, a local peak over time also counts. The ball is then snapped to the touching player and drawn in straight lines between touches. This made the error a bit *worse* (3.66 → 4.07 m) but made the ball path physically possible.
- **For our 5-45 s gaps:** the middle of a gap is close to "fully hidden", so expect 2.7-5.4 m error and 84-92% team accuracy. Near the edges of a gap the known ball helps, but no paper reports results for long unbroken gaps.
- Ball Radar's repo: [pientist/ballradar](https://github.com/pientist/ballradar). PathCRF's repo has trained weights in `saved/100`-`saved/140` (`140` is the main model), MPL-2.0 licence ([README](https://github.com/hyunsungkim-ds/pathcrf)).

## Open questions

- How is DFL's `BallPossession` flag produced, and does it switch at first touch or at control? It's our training label for any learned model.
- Does PathCRF's 92.4% include dead-ball frames? And how far does it fall at 25 fps once its "ball in flight to receiver" states are mapped to the challenge's convention?
- Nobody has published possession accuracy for compactness / line height / centroid-velocity features. Measurable on the 7 DFL matches with leave-one-match-out, at low cost.
- Vidal-Codina's thresholds sit in an online supplement (Online Resource 1) I couldn't open. Worth fetching from the Springer journal version if we copy the rule closely.

## Only seen in snippets, not checked against the full text

- Hoernig et al. 2016: 80-92% precision and recall ([record](https://portal.fis.tum.de/en/publications/detection-of-individual-ball-possession-in-soccer/)).
- A Data Mining and Knowledge Discovery 2025 paper on match phases ("FeatGRU", about 80% agreement with experts) ([Springer](https://link.springer.com/article/10.1007/s10618-025-01092-9)). It labels phases *given* possession, so it's not directly useful.
- Bauer & Anzer 2021, counterpressing, AUC 87.4% ([Springer](https://link.springer.com/article/10.1007/s10618-021-00763-7)). Uses DFL event plus position data, not tracking-only possession.
