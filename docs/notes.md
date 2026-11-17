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
2. `python prep/run_real.py` loads the tracking, runs our best approach (row 18), writes `evaluation/results/tiki_data.csv`, runs the official checker, scores it on the 5 public minutes, and prints ballpark checks (stoppage share, number of stoppages and possessions). Dry run passed on the practice match.
3. Watch the 5 public minutes on the tactical video next to the answer key. Questions to answer:
   - Does their stoppage start at the whistle or when the ball crosses the line?
   - Is the ball tracked during stoppages, or does it vanish like in the practice match?
   - Does the ball move during stoppages (decides row 7)?
   - When does their possession switch: first touch, or once a player has it under control?
4. Look at what the automatic tags catch (set pieces, throw-ins) vs what we catch.

### What we found (Nov 13)

- Data unpacked into `data/tactical/` and `data/broadcast/`. Row 8 runs in ~30 s and passes the checker.
- Ball during their stoppages (public 5 min): sometimes tracked the whole time and barely moving (20 s and 14 s stoppages, 100% seen), sometimes mostly missing (7-20% seen). So "ball missing" and "ball still" are both only part of the story.
- Our stoppages on the real match (row 8): 152, the normal is ~110. 70 come only from the speed rule, 33 only from ball-out, 49 from both. 32 last under 4 s.
- Clips with our guess on screen: `python experiments/ahmed/make_clips.py` → `data/clips/` (20 clips, list in `index.csv`). From the stills:
  - Many ball-out "stoppages" last 0.1-0.3 s: the ball flickers just outside a line in live play. Each one splits a possession. Fixed in row 9.
  - Before a corner we go back to live too early (players move, ball still missing), then the ball appears at the corner flag. Fixed in row 9.
  - A speed-only stoppage at 44:45 (half 1) looks real: linesman's flag up, players bunched around the halfway line, keeper about to take a long free kick.

## Football thinking we build on

Our working beliefs about how the game works. We update these as we learn.

- **Goal ruled out by VAR** (from Ahmed): the restart is a free kick for the defending team (offside or foul), not a kickoff, even if the automatic tags say kickoff.
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
- **The truth switches at the first touch, not at control.** On the practice match (event-based answer key) a possession starts the moment the other team touches the ball: an interception, a tackle, a clearance. Waiting until a player "has it" is late by up to half a second, which is a lot when possessions last 0.8 s. So the switch has to be dated to the touch.
- **A flying or loose ball stays with the last team.** A pass in the air, a ball bouncing between players, a ball the tracker has lost: none of it changes who owns the ball until the other team visibly plays it. Loss is never a separate event; only a gain by the other team changes the label. A duel (both teams inside 1 m) freezes it.
- **Touch = zone + kinematics.** "Closest within 2 m for 8 frames" (row 8) confuses a defender running past the ball with a touch. Row 9T (Atallah) asks for a player inside 1 m *and* the ball reacting (direction change over 10° or a speed change over 5 m/s, with the ball moving at 1.5 m/s or more), and places the switch at the vertex of that change. A near run of 8 frames inside 1 m still confirms a switch without a visible kick (a slow dribble).

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
- **Ownership ceiling.** Swapping our stoppage mask for the truth's stoppages shows how much each half of the problem costs: row 8 reaches 0.593 clean / 0.563 noisy with the truth's stoppages, row 9T reaches 0.733 / 0.626. So on noisy data the stoppage mask is now the larger loss (0.626 to 0.509), not the team rule.

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
| 8 | #6 with a quicker switch: other team on the ball for 8 frames (0.32 s) instead of 12 (0.48 s) | 0.503 | **0.444** | 0.400 | – | best on noisy until row 9. 321 possessions (true 381). Tried 4-12 frames and other zone sizes: under 8 starts flip-flopping in duels. Now the default in `prep/sticky.py`, so rows 1-7 ran with 12 |
| 9 | #8 + two stoppage fixes from watching the real match (`prep/stop_fixes.py`): drop stoppages under 2 s; ball missing then reappearing outside the pitch (corner, throw-in being taken) = the missing stretch was a stoppage | 0.528 | **0.469** | – | – | best on noisy. Under the luck line (+0.025) but up on both versions. Real match: 152 → 136 stoppages (normal is ~110). The 2 s rule does most of it |
| 10 | #9 + Smart Tagging (`prep/tags.py`): stoppage from each tagged set piece back to where the ball stopped being in play; speed rule silenced 10 s after each restart; team taking the set piece gets the first bit; dead from goal to kickoff, before each half's kickoff, and under 10 players tracked | bench 0.448 | | 0.400 (sanity) | – | bench = 8 games, see below. 8/8 games beat row 8 (0.422). Goals/edges not on the bench (laws of the game) |
| 11 | #10 with a tighter "on the ball" test: within 1.5 m (was 2) and 0.5 m closer than the nearest opponent (was 1) (`experiments/ahmed/sweep_team.py`; now the defaults in `prep/sticky.py`) | bench 0.464 | | 0.444 (sanity) | – | `ours_row11.csv` (branch `row11-shared`, same file byte for byte as the experiment). Old practice check (`prep/ball_out.py`, Metrica noisy): row 8 with the new settings 0.439 vs 0.444, even within luck. 7/8 games beat row 10. Switching after 6 frames scores higher on Bundesliga but lower on Metrica (tracking like ours), so kept 8. Real match: 348 possessions (row 10: 404) |
| 12 | #11 + two team clean-ups (`prep/team_fixes.py`): a switch hidden in a ball-missing stretch goes halfway into it (was: at the end); possessions under 1 s go to the team before ("touch without control") | bench 0.470 (controlled keys 0.565) | | – | – | `ours_row12.csv`. Better than row 11 on all 6 bench runs (3 seeds × normal/hard): raw keys +0.005, controlled keys +0.028 (8/8 games every run), Metrica +0.022. Real match: only 0.3% of frames change, 347 → 336 possessions, so the real gain is probably smaller |
| 13 | #12, but inside ball-missing stretches a players-only model decides (`prep/shape_model.py`, `prep/team_fixes.py: shape_gap`): where the switch goes, and whether the other team had a hidden spell (2 s+) when the same team has it before and after. Model: team shape and movement (centroid, spread, back/front line, forward speed, at 1/4/10 s), gradient boosting, trained on the 7 Bundesliga games with home/away swapped | bench 0.485 (controlled 0.582) | | – | – | `ours_row13.csv`. Over row 12 on 6 bench runs: raw +0.014 (worst +0.011, 7-8/8 games), Metrica +0.011 (one run -0.003). Players-only model alone: team right on 82-90% of live frames (leave-one-game-out), 87.6% on Metrica (never trained on). On our match it agrees with our labels on 82% of ball-seen frames (bench: 87-88%), so it mostly carries over. Real file: 0.3% of frames change (only ~8,600 live frames have no ball). Needs `requirements-team.txt` and the Bundesliga data |
| 14 | #13 + the players-only model with the ball visible too (`prep/team_fixes.py: model_override`): where nobody is clearly on the ball (in flight, contested), it overrules our team call if sure for 2 s+ (summed log-odds over 150). Never on frames where our team is clearly on the ball | bench 0.505 (controlled 0.601) | | – | – | `ours_row14.csv` (commit c5211ef). Over row 13 on all 6 bench runs: raw +0.021 (8/8 games every run), Metrica +0.025 (worst +0.021). Without the "never when we're clearly on the ball" lock it hurt Metrica and flipped clear ball evidence on our match. Practice: flips 1.5-6% of live frames, 74-95% of flips right. Our match: 5.6% of live frames (36 stretches), inside that range. Possessions 340 → 353 |
| 15 | New team call (`prep/ball_model.py`): one model gives P(home has it) per frame from the players' shape (row 13 features) **plus the ball when it's there** (each team's distance to it, who's clearly on it in the last/next 0.5-2 s, last-seen/next-seen before and after a gap, time since/until seen, ball speed). Trained on the 7 Bundesliga games with the ball hidden like ours (`prep/hide_ball.py`, seeds 10/11, not the bench's). Then the most likely H/A sequence in each live stretch, at a cost of 7 per switch (Viterbi). A team clearly on the ball for 2 s+ keeps it. Stoppages unchanged from row 14 | bench 0.564 (controlled 0.645) | | – | – | `ours_row15.csv` (commit 9f29345). Over row 14 on all 6 bench runs: raw +0.069 (48/48 game-runs, worst +0.035), controlled +0.054 (48/48), Metrica +0.048 (never in training). Model alone: team right on 90% of live frames (players-only: 87%). Most of the gain is the decoder: the same model through row 14's fix-ups gave only +0.014. Not learning the fake hiding: trained on a different hiding recipe (25% of live hidden, gaps 1.5x, fill under 2 s) it still gives +0.069, 48/48 (`experiments/ahmed/ball_model_robust.py`). Switch cost flat from 5 to 10. Pressure features (`shape_v2.py`) added nothing. Our match: 4.2% of frames change vs row 14 (bench 4.1-4.3%), possessions 353 → 349. It overruled "clearly on the ball for 1 s+" 2x more than on practice, hence the 2 s lock (costs -0.001 on the bench). Regenerates byte for byte with caches deleted |
| 9T | Atallah's ball ownership (`prep/ball_ownership.py`, rule `"touch"`): the team changes on a visible touch by the other team (smoothed ball turns by over 10° or its speed changes by over 5 m/s, a player of that team inside 1 m, no opponent within 1.1 m), or after 8 frames inside a 1 m zone; a flying or loose ball and a ball gap stay with the last team; #6's stoppages | **0.624** | **0.509** | 0.456 (sanity only) | – | best on both. 351 possessions found on clean, 289 on noisy (true 381), fewer missed truth possessions than row 8 on every set, also on the IDSSE open matches (0.402 vs 0.336). Was the default on main (as "row 9") before row 16; here it feeds row 16. Constants picked on the practice match only |
| 16 | #15, with Atallah's touch rule (row 9T) as a second opinion: before the decoder, the model's log-odds get +1 towards the team the touch rule names (`prep/ball_model.py: blend_touch`). The touch rule reads the ball's own movement (kicks, turns), the model reads team shape, so they catch different things | bench 0.580 | | – | – | `ours_row16.csv` (commit e84fa25). Over row 15 on all 6 bench runs (45/48 game-runs, worst -0.005): raw +0.017, controlled +0.006, Metrica +0.016 (the touch rule's settings were picked on Metrica, so that one is flattered). Weight 0.5-1 flat, 2+ worse. On the same bench the touch rule alone with our stoppages scores 0.559, Atallah's main (row 8 stoppages) 0.529. Our match: 3.2% of frames change vs row 15, stoppages identical, 349 → 340 possessions. Reproducible. Needs scipy (`requirements.txt`) |
| 17 | #16, but rule-made stoppages under 6 s are dropped (was 2 s; `prep/stop_fixes.py: MIN_STOP_S`). Idea from other teams' public write-ups (ideas only, no code): real stoppages last 10 s+, short ones are the speed rule or ball flicker in live play | bench 0.587 | | – | – | (not submitted, superseded by row 18). Over row 16 on all 6 bench runs: +0.007, 40/48 game-runs, Metrica +0.008 (`experiments/ahmed/stop_min_sweep.py`; 4 s +0.003, 5 s +0.005, 8 s +0.007, so a plateau). Real match: 137 → 106 stoppages (normal ~110), stoppage share 46% → 44%, 340 → 322 possessions, 1.7% of frames change. Slowdown threshold (1.0/1.5 m/s) and quiet time after restarts (5/20 s) tried on top: no gain (`stop_speed_sweep.py`) |
| 18 | #17 + two more: (a) **restart kick**: a stoppage ends when a ball that was still or unseen for 1 s is struck (over 4 m/s); each rule-made stoppage's end moves to the first such kick from 3 s before to 10 s after it, and a ball seen still for 2 s+ then kicked within 1 s was dead until the kick (`prep/stop_fixes.py`); (b) possessions under 0.8 s merged (was 1 s; `prep/team_fixes.py: MIN_POSS_S`). Restart-kick idea from other teams' public write-ups (idea only) | bench 0.601 | | – | – | superseded by row 19. Over row 17 on all 6 bench runs: +0.013, **48/48** game-runs, worst +0.000, Metrica +0.011 (`experiments/ahmed/row18_check.py`). Alone: kick +0.009 (45/48), 0.8 s +0.004 (38/48; 0.4-0.8 a plateau, 0.8 safest on Metrica). Kick trims help, extend-only does nothing; kick speed 3-5 m/s and still time 1-3 s flat (`idea_restart_kick.py`). Switch cost, touch weight, lock time re-checked after row 17: already best (`idea_team_retune.py`). Real match: 0.5% of frames change vs row 17, 106 stoppages, 329 possessions |
| 19 | #18 + a **learned stoppage model** (`prep/dead_model.py`): gradient boosting gives P(stopped) per frame from players' mean speed (several windows, before/after), how often the ball is seen, time since/until seen, ball speed, distance to a line, row 18's rule stoppages and the set-piece tags. Trained on the 7 Bundesliga games with the ball hidden like ours (DFL's alive flag as key). Smoothed 1 s, dead over 0.5, under 6 s dropped, tags always dead | bench **0.631** | | – | – | **submitted** (`tiki_data.csv`). Leave-one-game-out over row 18: +0.030, 47/48, worst -0.001, Metrica +0.016 (never trained on) (`experiments/ahmed/dead_model_bench.py`). Without any ball-visibility inputs still +0.026, 47/48, so it isn't just the bench's hiding recipe. Threshold 0.65: +0.026, 48/48; union with rules: +0.012. **Caveat:** on our match it calls fewer stoppages: 38% of frames (row 18: 44%; league norm 40-48%), 104 stoppages, 351 possessions, 8.3% of frames change. Built at 23:35 on deadline day; not cold-rebuilt before submission (the model trains from the bench's cached games, all seeded) |
| – | #18 + last checks (Nov 17, 23:25): stoppages start 0.5/1/2 s later (`row19_backdate.py`, LATE=1); restart-kick window 5 s before / 15 s after (`row19_window.py`); re-drop short stoppages after the kick trim, fill live gaps under 1/2/3 s between stoppages (`row19_fill.py`) | later starts -0.001/-0.008/-0.018; window +0.002 (33/48, under our bar); re-drop -0.000; fill +0.000/-0.001/-0.004 | | – | – | **all rejected**, row 18 stays. Stoppage start timing is right in both directions |
| – | #18 + stoppage starts moved earlier (players react to the whistle late): every rule stoppage 1/2/3 s earlier, or only slowdown-rule ones 1/2/4 s (`experiments/ahmed/row19_backdate.py`) | worse on every game seen (all: -0.01 to -0.03; slowdown only: -0.001 to -0.008) | | – | – | **rejected**, stopped early. The keys' stoppages don't start before ours; if anything ours start early enough |
| – | #18 re-checked: minimum stoppage 4/8/10 s, and the kick snap applied to tagged restarts too (`experiments/ahmed/row19_sweep.py`) | 4 s -0.004, 8 s +0.001 (33/48), 10 s +0.001 (30/48), tag snap -0.000 | | – | – | no change: row 18 stays. Cold rebuild of row 18 from main matches the submitted file byte for byte (7 min) |
| – | #18 + long ball gap = stoppage: a ball gap of 8 s+ with players' mean speed under 2 m/s is dead (`experiments/ahmed/idea_long_gap.py`) | bench +0.009 vs row 17 (46/48) | | – | – | **rejected**. Probably the bench's hiding recipe talking: it hides stoppages whole and puts live gaps at random times regardless of player speed, so 'long gap + slow players' separates them by construction (~25% of live long gaps pass on the bench, ~70%+ on our match). Would push our match to 47% stopped. Also tried without the speed test (any 8 s gap: -0.004) |

## Test bench: 8 games with the ball lost like on our match (`experiments/ahmed/bench.py`)

How our match loses the ball (measured Nov 13, all graded frames):
- missing 41% overall: about 72% of stoppage frames, 15% of live frames (split by our own labels)
- only ~150 gaps, all long: no gap between 1 s and 5 s, so the tracker fills short losses with a straight line. Live gaps last 5-25 s
- in live play a gap starts 5x more often when the ball was last seen within 2 m of a line

The bench copies that onto the Metrica game and the 7 Bundesliga games (seeded), plus fake set piece tags for 55% of restarts (like the real 59). A change counts as better if the mean goes up and it wins on most of the 8 games, not the single-match 0.04 line.

| version | bench mean | wins vs row 8 |
|---|---|---|
| row 8 | 0.422 | – |
| row 9 | 0.428 | 6/8 |
| row 10 restarts only | 0.440 | 8/8 |
| row 10 (+ team at restart, speed quiet after restart) | 0.448 | 8/8 |
| row 11 (tighter "on the ball") | 0.464 | 8/8 |

Nov 13, round 2 (`experiments/ahmed/fastbench.py`: same bench, in-process, any seed):
- **Where the points are.** Perfect stoppages with our team logic: 0.464 → 0.52. Our stoppages with the perfect team: 0.89. So "who has the ball" is the bottleneck, not stoppages.
- **Team errors:** ~12% of live frames with the ball seen, ~25-38% with it missing. Half are within 1 s of a real change (timing, no bias). Long wrong stretches are mostly switches we miss while the ball is hidden. Perfect calls inside hidden stretches would be worth ~+0.05.
- **Bundesliga keys flip on every touch:** 40-50% of their possessions are under 3 s; the changes we miss mostly last 4-6 frames on the ball. The organisers say a touch without control doesn't count. So a second yardstick, "controlled" keys (`experiments/ahmed/controlled.py`): possessions under 2 s merged into the team before. Mean possession then 9-15 s.
- **Switching after 8 frames is still best**, on both raw and controlled keys (12, 16, 25 all lower).
- **Careful with the controlled keys:** they're built with the same merge as row 12, so any "merge short possessions" change scores well on them by design. Don't tune merge settings on them (2 s merge rejected for that reason). Judge on Metrica and the raw keys.
- **Row 12's practice gain likely overstates the real one:** the merge mostly cleans up noise from the straight-line-filled ball, which is 15% of live frames on Metrica, 3-5% on Bundesliga, ~1.4% on our match. The real file changed on 0.3% of frames.
- **Open call, switch speed:** with row 12, switching after 6 frames is +0.016 to +0.028 on the raw Bundesliga keys but -0.009 to -0.018 on Metrica and lower on controlled keys. The organisers' key comes from their tracking's owning team, the same kind of source as DFL's, so the Bundesliga side isn't obviously wrong. Kept 8 (rulebook "controlled" wording + Metrica). Team decision; not to be settled with the public 5 minutes.
- **Biggest lever left:** who has the ball while it's hidden (worth up to ~+0.05 on practice). Done in row 13 (+0.014), research in `docs/research/possession-without-ball.md`. Row 14 then used it with the ball visible too (+0.021). Row 15 replaced the fix-ups with one ball-aware model and a sequence decoder (+0.069). Next: the published PathCRF model (same 7 games, 92%), or a better players-only model (more features, Metrica in training).
- **Noise between seeds:** row 11 moves 0.457-0.464 across seeds. Accept a change only if it wins on every seed, Metrica included.
- Two bench bugs fixed (both bench-only, the real match can't hit them): a tag in the first 20 s wrapped around and marked the whole half stopped; in `--hard`, a hidden stretch shifted before frame 0 hid the whole half.

Harder version (`bench.py --hard`): hidden stretches start/end up to 3 s off the real stoppage edges, and fake tags only on restarts near a line or in a box (like the real tags: throw-ins, corners, goal kicks). Row 8 0.413, row 9 0.422, row 10 0.436, row 11 0.446: smaller gains, still 8/8 games.

Smart Tagging findings:
- Set piece tags are fixed windows: 35 s (kickoffs 5 s). The restart is ~4-6 s after the tag starts (kickoffs 3.5 s exactly), seen as the ball reappearing, or held outside for a throw-in, then moving.
- Goals: the tracker loses the ball in the net, so the goal moment = end of the attack where the ball was last seen. All 4 checked on the scoreboard: 46678 (1-0 Barça), 73997 (1-1), 157546 (2-1 Barça). The one at 58081 (Athletic) never changed the score, probably ruled out after a video check, but play was dead ~2.5 min anyway.
- Tag team = the team taking the set piece: on goal kicks and free kicks the tagged team's player is nearest the ball at the restart 11 of 15 times, misses mostly where the restart detection looks off. Corners can't be checked this way (crowded box). Barcelona = home.
- The kickoff tag after the ruled-out goal (62012): players stand around until the ball reappears at ~62334, so kickoff restarts now wait for the ball (up to 20 s).
- Second half: graded from 110808 but kickoff is 113748; players were walking around in between, which we called "home has it". Now dead.
- End of first half: from ~89058 only 1-5 players tracked (teams walking off). Under 10 players also happens during goal celebrations.

Answered by Ahmed (Nov 13):
- Goal ruled out by VAR (offside or foul) → restart is a free kick for the defending team where the offence was, not a kickoff. Fits 58081: we have it dead from 58073 to 62334, then Barça (the defenders) on the ball.
- Throw-in side: can't check the video for now. The football rule: the team that didn't touch it last takes it. Tried "give the throw-in to the team that didn't have it last" on the practice games: 0.460 vs 0.464 (normal), 0.444 vs 0.446 (hard), no gain, so it's off (`tags.THROW_IN_GUESS = False`). Caveat: the fake tags apply it to every no-team tag, not just throw-ins.

## More practice matches: 7 Bundesliga games

`experiments/ahmed/bundesliga.py`. Free DFL data (CC-BY), downloaded from huggingface.co/datasets/pysport/idsse-data into `data/bundesliga/` (figshare blocks scripts). Answer key = DFL's own per-frame flags (ball alive/dead, which team has it), so it's their idea of possession, not the organisers'. Play is dead 41-52% of the time, in line with the general stats.

Big difference from our match: DFL tracks the ball 100% of the time, even during stoppages. So rules built on "ball missing" behave differently here. The noisy version hides it in random gaps only.

| approach | 7 games, clean (mean) | 7 games, noisy (mean) | range noisy |
|---|---|---|---|
| row 8 | 0.460 | 0.368 | 0.33-0.39 |
| row 9 | 0.462 | 0.368 | 0.32-0.39 |

Row 9 changes nothing here. Its fixes target the tracker losing the ball near lines, which DFL doesn't do. The same method scores 0.32 to 0.39 from game to game, which backs up the "under 0.04 can be luck" rule.

## Research ideas

- **Possession zones** ([Vidal-Codina et al. 2022](https://arxiv.org/abs/2202.00804)): a player has the ball when it's within a small radius of them. Gains and losses come from who's next in the zone. Simple rules, over 90% event detection across providers. Their [supplement](https://media.springernature.com/original/springer-static/esm/art%3A10.1007%2Fs12283-022-00381-6/MediaObjects/12283_2022_381_MOESM1_ESM.pdf) lists the same problems we have: ball gaps during live play, players going off the edge of the tracking.
- **Ball in play from players only** ([Lang et al. 2022](https://www.nature.com/articles/s41598-022-19948-1)): detects whether play is live or stopped using only player positions, no ball. Exactly what we need for the 41% of frames with no ball.
- Older idea from the same review (Gudmundsson & Wolle): classify live vs stopped over 4-second windows of ball movement.

## Data

- About 6 GB (a teammate's number). It goes in `data/`, which git already ignores. Never commit it, since our repo has to be public.
