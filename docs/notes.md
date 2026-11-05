# Notes

## What makes us different

Everyone will use Claude or similar, so everyone gets the same decent first version fast (closest player to the ball, then smooth it). That's not an edge.

The edge is judgment:

- **Get how they score.** They grade whole possessions, not individual frames. Design for that: no flip-flopping between teams, but don't switch late either.
- **Actually look at the data and the video.** AI can't watch the match for us. Spot the real patterns (where the ball tracker drops out, what players do before a restart) and turn them into rules.
- **Don't fool ourselves.** The only answer key is 5 minutes. Use it to check the pipeline works, not to tweak until it looks good. Reason about what makes sense for a full match.
- **Clean repo and write-up.** The top 20 go on to pitch, so explaining *why* we did what we did counts.

Use Claude to move fast. Spend human time watching the match, thinking about what possession really means, and not overfitting.

## When the real data lands

1. Unzip into `data/` (names as they arrive, see DATA.md).
2. `python prep/run_real.py` loads the tracking, runs our best approach (row 8), writes `evaluation/results/ours_row8.csv`, runs the official checker, scores it on the 5 public minutes, and prints ballpark checks (stoppage share, number of stoppages and possessions). Dry run passed on the practice match.
3. Watch the 5 public minutes on the tactical video next to the answer key. Questions to answer:
   - Does their stoppage start at the whistle or when the ball crosses the line?
   - Is the ball tracked during stoppages, or does it vanish like in the practice match?
   - Does the ball move during stoppages (decides row 7)?
   - When does their possession switch: first touch, or once a player has it under control?
4. Look at what the automatic tags catch (set pieces, throw-ins) vs what we catch.

## Football thinking we build on

Our working beliefs about how the game works. We update these as we learn.

- **Play time.** Ball in play is only ~55% of the match in LaLiga (Barça 55%, Athletic 56%, Opta season averages). So expect ~45% stoppages over the full match. Just a ballpark check on our output, never a setting in the code.
- **Two kinds of stoppage.** Ball out (throw-in, corner, goal kick): the ball crosses the line, which shows up in the tracking. Foul or offside: the ball stays on the pitch and play can carry on for a second after the whistle, so the ball position tells you nothing.
- **Whistle delay.** Players take ~0.5-1 s to react to the whistle, then everyone slows down together. Spot that slowdown and date the stoppage back. The practice match's event data gives the real foul times, so we can measure the delay.
- **Work back from the restart.** A free kick is easy to spot (ball still, one player over it, a wall). Find it, then look back for when play actually stopped. Their automatic tags include set pieces too.
- **Slowdown alone isn't enough.** Players also slow down in live play (slow buildup, keeper holding the ball, a team holding the ball at the back to invite pressure). A slowdown should only count once something confirms play stopped: a restart (free kick, throw-in, corner shape), the ball off the pitch, or a set-piece tag.
- **Players off the pitch during live play are normal.** An injured player getting treatment, or subs warming up (if the tracker picks them up). So "someone's off the pitch" isn't a stoppage sign on its own. Tried as a confirmation and it made the score worse.
- **Substitutions are stoppages too.** Not handled yet.
- **What stoppages look like.** After a foul a player is often down and others crowd the ref arguing for a card. Sometimes players fight (rare, but it happens in LaLiga). Before a free kick near the box, players spend time setting up a wall. These are long and look very different from live play: players gathered and standing, not spread out and running. Substitutions take time too.
- **Shape.** Not the formation, but the organisation. In live play everyone has a job: 1-2 press the ball holder, the rest mark someone or cover space. Out of shape = that organisation is gone: 5 players around the ref, a wall of players together, nobody marking. Idea to measure it: a tight bunch of players from both teams (5+ within a few meters) standing still, or a still line of one team's players (a wall). The tracker doesn't follow the ref, so we only see players crowding an empty spot.
- **Speed is a weak sign both ways.** Live play can be slow (inviting pressure). And stoppages can be fast: before a corner or throw-in, players keep moving to lose their marker and get free to receive. So speed shouldn't be the main stoppage signal.
- **Ball out = stoppage straight away.** Seen in the throw-in replay: B intercepts, the ball goes out, and approach #3 keeps saying "B" for seconds, until the players slow down. When the ball crosses the line, play is dead right then. No need to wait for players.
- **Goals.** A goal and the celebration are a long stoppage (45-58 s until kickoff). The ball crossing the goal line should be caught by the ball-out rule. Celebrations are another case where players run around while play is stopped. The practice match has 2 goals. Not checked specifically yet.
- **Missing ball ≠ stoppage.** The tracker loses the ball in crowds and in the air during live play, so stoppages need player-based signals too.
- **Control.** A touch, deflection or aerial duel isn't a change. But their answers switch fast (possessions as short as 0.8 s), so "keeps it a few seconds" is too strict. Half a second of the other team clearly on the ball is our compromise.
- **Does the ball move during a stoppage?** Depends on the stoppage type. Revisit with the real data (decides whether "moving ball = live" from row 7 is safe).
- **Ball between two players.** When the ball is about halfway between a player from each team, guess from who passed it: a pass from A is probably going to an A teammate. Right now we just keep the last team when it's unclear.
- **Who's on the ball.** A dribbler keeps it within about 1 m, so 2 m works as "near". "No opponent within 2 m" is unrealistic in duels and crowded areas. "Clearly closest" works better.

## Football stats (general, not about our match)

Ranges, not targets. Providers measure differently.

- **Ball in play:** LaLiga ~52-60% per match ([CIES](https://www.football-observatory.com/IMG/pdf/mr64en.pdf)). Under 45% or over 70% for one match = suspicious. It drops through the match: 66% in the first 15 min, 56% in the last 15 ([JSSM](https://jssm.org/17-4-662.p_d_f)). Probably part of why the 5 public opening minutes have only 20% stoppages.
- **~110 stoppages per match**, over one a minute: ~44 throw-ins, 33-41 free kicks, ~19 goal kicks, 9-10 corners, 2-3 kickoffs, up to ~6 subs ([Augste & Cordes](https://opus.bibliothek.uni-augsburg.de/opus4/files/76143/IJPAS_Game_stoppages_manuscript.pdf)). LaLiga: ~27 fouls a match ([CIES](https://www.football-observatory.com/IMG/pdf/mr64en.pdf)). Sanity check: our output should land near 110 stoppages.
- **How long they last (s):** throw-in 10-16, goal kick 20-28, corner 25-34, free kick 21-27, free kick with a wall 55-70, kickoff after a goal 45-58, sub 40-45, injury with treatment 83-99 (same sources plus Opta and [Lang](https://pmc.ncbi.nlm.nih.gov/articles/PMC9522646/)). Throw-ins are the most common and the shortest, so they're the easiest to miss.
- **Possessions:** ~250 per match including the ones under 5 s ([Cooper & Pulling](https://eprints.chi.ac.uk/id/eprint/5037/)). Definitions vary a lot. Ours: a stoppage always ends a possession.
- **Lang et al. 2022 (live vs stopped from players only):** 92% of frames right, 80% of stoppages found, start/end usually within 2 s. What players do in the seconds *before and after* matters more than the moment itself. Fails on short throw-ins (2-4 s free kicks get smoothed away) and on bursts of movement during long stoppages.

## What their 5 minutes of answers show

- 17 possessions and 4 stoppages in 5 minutes. Stoppages last 5-20 s.
- Lots of short possessions: 6 of the 17 are under 4 s, the shortest is 0.8 s. So their "possession" switches fast. It isn't only counted after long control. Heavy smoothing will erase these.
- Most switches go straight from one team to the other, with no stoppage in between.
- Scoring: a stoppage splits a possession in two (H, stop, H counts as 2). So missing a stoppage merges two possessions, and inventing one splits a possession. Both hurt. Getting stoppages right matters as much as the team.
- Writing X ("don't know") = repeat the last answer. Free in the middle of a possession, costly at a switch.

## Practice match (allowed to tune on)

- Metrica's free Sample Game 3. Same company, same format. `python prep/sample_game.py` builds an answer key from its event data, plus the baseline's answers.
- Score with `python evaluation/run_evaluation.py --gt data/sample/sample_gt.csv --results data/sample/results --out data/sample/eval`
- 381 possessions, about 10.5 s each (theirs: 14.2 s). Stoppages are 30% of frames (their 5 min: 20%).
- Clean ball: the best baseline version is the same one that wins on the real full match (smooth50). The rest of the order differs, but those gaps are within noise on the real match anyway.
- `results_noisy` blanks the ball at random until it's visible 59% of the time, like ours. That makes the heaviest smoothing win, which is the wrong pick on the real match. Random dropouts aren't how the real tracker fails (it loses the ball in crowds and in the air). **Compare ideas on the clean version** until we have a more realistic dropout model.
- It's much cleaner than our match: real player IDs that never swap, no speed column, ball visible about 96% of live play. Don't build anything that relies on a player keeping the same ID.
- Our answer key comes from event data, so it's not exactly how theirs is made. Use it to compare ideas, not to chase their exact numbers.

## Approaches and results

Score = spellF1, the number we're ranked on. Practice = sample match (clean ball unless noted). Public 5 min = sanity check only, never pick between versions with it.

| # | approach | practice | practice, noisy ball | public 5 min | real match | notes |
|---|---|---|---|---|---|---|
| 0 | their baseline: closest player, majority vote ±2 s (smooth50) | 0.397 | 0.272 | 0.326 | 0.243 (official) | missing ball = stoppage |
| 1 | sticky (`prep/sticky.py`): switch after the other team is alone within 2 m of the ball for 0.5 s, dated back; ball missing 3 s+ = stoppage | 0.537 | 0.321 | – | – | 281 possessions vs 381 true: misses switches. Untuned. Stoppage rule still only uses the ball, so it's flattered on practice |
| 2 | sticky, "closest" rule: within 2 m and at least 1 m closer than the nearest opponent (instead of alone within 2 m) | 0.572 | 0.329 | – | – | small win. Still 280 possessions, so the missed switches come from somewhere else |
| 3 | #2 + stoppages from players only (`prep/stoppage.py`): average player speed, 1 s median, below 1.25 m/s for 3 s+ = stoppage. Ball not used | 0.484 | 0.399 | – | – | best when the ball is unreliable, which is our real case. Worse on clean only because practice's "ball missing = stopped" is unrealistically perfect. Tried 0.75-1.75 m/s: lower misses stoppages, higher invents them. Finds only 216 possessions on noisy, so it misses stoppages |
| – | #3 + restart signs (player off the pitch 1 s+, at the corner flag, kickoff shape) confirm looser slowdowns | 0.43-0.46 | 0.36-0.38 | – | – | worse. Off-pitch players are normal in live play (treatment, subs warming up), and many stoppages show no sign. Dropped |
| 4 | #3 + "standing bunch" (3+ players of both teams within 5 m, all under 2 m/s, for 1 s) confirms looser slowdowns (under 1.5 m/s) | 0.486 | 0.406 | – | – | almost never happens in live play (under 1% of frames) but only shows in ~20% of stoppages. Tiny gain, within noise. Possession count still ~215, so the bigger problem is elsewhere |
| 5 | ball left the pitch (`prep/ball_out.py`): ball seen outside, or last seen within 2 m of a line then gone 1 s+ = stoppage from that moment until the ball is back inside | 0.507 | 0.364 | – | – | catches stoppages within 0.5 s (speed: 4.1 s late). But alone it misses fouls: 24 of 94 stoppages on clean, 42 on noisy |
| 6 | #5 + #3's speed stoppages | 0.511 | **0.408** | – | – | best on noisy so far. Catches 82-88 of 94 stoppages. Speed is still doing work here (probably the fouls), just late |
| 7 | #6, but a moving ball on the pitch (over 3 m/s) overrules the speed stoppage: flying ball = live | 0.511 | 0.401 | – | – | no change. Fixes the throw-in / goal-kick cases from the replays (more possessions found: 317 vs 292), but probably breaks stoppages where the ball moves while play is dead |
| 8 | #6 with a quicker switch: other team on the ball for 8 frames (0.32 s) instead of 12 (0.48 s) | 0.503 | **0.444** | – | – | best on noisy so far. 321 possessions (true 381). Tried 4-12 frames and other zone sizes: under 8 starts flip-flopping in duels. Now the default in `prep/sticky.py`, so rows 1-7 ran with 12 |

## Research ideas

- **Possession zones** ([Vidal-Codina et al. 2022](https://arxiv.org/abs/2202.00804)): a player has the ball when it's within a small radius of them. Gains and losses come from who's next in the zone. Simple rules, over 90% event detection across providers. Their [supplement](https://media.springernature.com/original/springer-static/esm/art%3A10.1007%2Fs12283-022-00381-6/MediaObjects/12283_2022_381_MOESM1_ESM.pdf) lists the same problems we have: ball gaps during live play, players going off the edge of the tracking.
- **Ball in play from players only** ([Lang et al. 2022](https://www.nature.com/articles/s41598-022-19948-1)): detects whether play is live or stopped using only player positions, no ball. Exactly what we need for the 41% of frames with no ball.
- Older idea from the same review (Gudmundsson & Wolle): classify live vs stopped over 4-second windows of ball movement.

## Data

- About 6 GB (a teammate's number). It goes in `data/`, which git already ignores. Never commit it, since our repo has to be public.
