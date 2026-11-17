# Tiki Data: who has the ball, frame by frame

More than a Hack 2027, Phase 1. Barcelona (home) vs Athletic Club (away), 199,319 frames at 25 fps.

## In one paragraph

We split the problem in two: **is play stopped?** and, if not, **which team has it?** Stoppages
come from simple, explainable rules: the ball leaves the pitch, the players slow down, plus the
automatic set-piece tags. For the team we trained one model that gives P(home has the ball) for
every frame. It reads the players' team shape, plus the ball whenever the tracker sees it. We
nudged it with a hand-written touch rule, then picked the most likely sequence of H/A in each
live stretch, with a fixed cost per switch. Training uses only 7 public Bundesliga games. Every
choice was made on a test bench of 8 other games with the ball hidden the way our match hides it.

## The approach

### 1. A test bench we're allowed to tune on

The only answer key for our match is the 5 public minutes, and the rules forbid tuning on it.
So we built our own bench from 8 other games:

- Metrica's public Sample Game 3, with an answer key we built from its event data.
- 7 Bundesliga games (DFL/IDSSE open data). The answer key is DFL's own per-frame ball-alive and
  ball-possession flags.

Our match loses the ball 41% of the time, in a particular way. It goes missing in about 72% of
stoppage frames and 15% of live frames. There are only ~150 gaps, all long, because short losses
are filled with a straight line. Live gaps start 5x more often near a line. `prep/hide_ball.py`
copies that pattern onto the bench games, with seeds. We also add fake set-piece tags for 55% of
restarts, like the real tags.

We run every idea on 6 runs: 3 seeds, normal and harder hiding. That gives 48 game-runs. A change
is kept only if the mean goes up and it wins on nearly every game-run. One match is too noisy to
judge alone; the same method scores 0.32-0.39 across the Bundesliga games.

### 2. Stoppages (`D`)

Each rule came from looking at the data or the video and asking what a stoppage looks like.

- **Ball out** (`prep/ball_out.py`). The ball is seen outside the pitch. Or it was last seen
  within 2 m of a line, then stays gone for 1 s+. Play is dead from that moment until the ball is
  back inside.
- **Players slow down** (`prep/stoppage.py`). Mean player speed, 1 s median, under 1.25 m/s for
  3 s+. This catches fouls and offsides, where the ball stays on the pitch.
- **Ball reappears outside** (`prep/stop_fixes.py`). The ball goes missing, then shows up at the
  corner flag or the touchline. The missing stretch was a stoppage, as in a corner or throw-in
  being set up.
- **Smart Tagging** (`prep/tags.py`). Each tagged set piece marks play dead back to where the ball
  stopped being in play. The restart is found as the ball reappearing or going still. For 10 s
  after a restart the slowdown rule is switched off, so a slow build-up isn't called a stoppage.
  A goal is dead until the kickoff. So is the time before each half's kickoff, and any frame with
  under 10 players tracked (teams walking off, celebrations).
- **Stoppages under 2 s are dropped.** Most were the ball flickering just outside a line in live
  play.

### 3. The team (`H` / `A`)

- **One model for P(home has it)** (`prep/ball_model.py`). It uses gradient boosting
  (scikit-learn), with these features:
  - each team's shape and movement (centroid, spread, back and front line, forward speed, smoothed
    over 1, 4 and 10 s)
  - each team's distance to the ball
  - who was clearly on the ball in the last and next 0.5-2 s
  - where the ball was last seen before a gap and first seen after it
  - time since and until the ball is seen
  - ball speed

  It is trained on the 7 Bundesliga games, hidden with different seeds than the bench, with home
  and away swapped as augmentation. Alone it names the right team on ~90% of live frames.
- **Touch rule as a second opinion** (`prep/ball_ownership.py`, by Atallah). The team changes on
  a visible touch: the smoothed ball turns by over 10° or changes speed by over 5 m/s, with a
  player of the other team within 1 m and no opponent close. A loose or flying ball stays with the
  last team, and a duel freezes the label. It adds +1 to the model's log-odds towards the team it
  names. The two catch different things: the rule reads the ball's own movement, the model reads
  the shape.
- **A team clearly on the ball for 2 s+ keeps it**, whatever the model says.
- **Sequence decoding (Viterbi).** Inside each live stretch we pick the H/A sequence with the
  highest total log-probability, paying a cost of 7 for each switch. This gave most of the gain:
  the same model with simple per-frame fix-ups was worth only a fifth as much. It stops
  flip-flopping without delaying real switches.
- **After a tagged set piece**, the tagged team gets the first part of the possession.
- **Possessions under 1 s go to the team before.** A touch without control isn't a change.

### Why this and not something else

- **Why split stoppage and team?** The scorer cuts a possession at every stoppage. Each half has
  its own signals and errors, and we could measure each one's ceiling separately.
- **Why a model and not more rules for the team?** While the ball is hidden (15% of live play)
  only the players are left, and team shape says a lot about who has the ball: the team in
  possession spreads out and pushes up. Rules can't weigh 50 weak clues; boosting can.
- **Why the decoder?** The ranking matches whole possessions by overlap. A 1 s flip-flop splits
  one possession into three, and the long one may no longer match at all. A per-switch cost is
  the simplest honest way to say a team keeps the ball until there's real evidence it lost it.

## Results (bench mean, the number the competition ranks on)

| version | bench | what changed |
|---|---|---|
| organisers' baseline (closest player, smoothed) | 0.31 | – |
| sticky possession + ball-out and slowdown stoppages | 0.42 | rules only |
| + stoppage fixes and Smart Tagging | 0.45 | 8/8 games up |
| + tighter "on the ball" test, short possessions merged | 0.47 | |
| + players-only model inside ball gaps | 0.49–0.51 | |
| + ball-aware model and sequence decoder | 0.56 | 48/48 game-runs up |
| + touch rule as a second opinion (**submitted**) | **0.58** | 45/48 up |

On our match the submitted file has 46% of graded frames stopped (LaLiga is usually ~40-48%),
137 stoppages (~110 is typical) and 340 possessions.

## Assets: used and dropped

- **Tactical tracking (ATD)**: the main input, players and ball.
- **Smart Tagging**: used for set pieces, goals, kickoffs, and the team taking a set piece. We
  checked that the tagged team is usually nearest the ball at the restart (11 of 15 checked). Its
  "phases" (build-up etc.) aren't used, since they aren't possessions.
- **Tactical video**: watched for ideas only, through clips with our labels drawn on. This gave
  the ball-flicker and corner-setup fixes.
- **Broadcast video, broadcast ATD and homography**: not used. The broadcast isn't synchronised
  to the tactical feed, and we spent our time on the bench instead.
- **The 5 public minutes**: only to check the pipeline end to end (frames aligned, file valid).
  Never used to tune or to pick between versions.

## Training data

No labels of any kind from the provided match were used.

| dataset | source | labelled by | amount | used for |
|---|---|---|---|---|
| 7 Bundesliga games (IDSSE) | DFL / Sportec Solutions open data, CC-BY, [huggingface.co/datasets/pysport/idsse-data](https://huggingface.co/datasets/pysport/idsse-data) | DFL's per-frame `BallStatus` and `BallPossession` flags, from TRACAB tracking checked by DFL operators | 7 full matches | training the team model; bench |
| Metrica Sample Game 3 | [metrica-sports/sample-data](https://github.com/metrica-sports/sample-data) | Metrica's event data, turned into a per-frame key by our script (`prep/sample_game.py`) | 1 full match | bench, and picking the touch rule's settings. Never used to train the model |

## The possession rules we implemented

- **A loose ball, a ball in flight or a lost ball stays with the last team.** Losing it is never
  an event on its own; only the other team gaining it changes the label.
- **Switch timing.** The touch rule dates a switch to the first touch (the interception or
  tackle), not to when the player "has it", since that's where possessions start on our practice
  keys. In the final pipeline it's a nudge to the model; the decoder decides where the switch
  lands.
- **A touch without control isn't a switch.** Possessions under 1 s are merged into the team
  before. The touch rule also ignores quick deflections that bounce straight back, and it freezes
  its call in a duel (both teams within 1 m).
- **Restarts.** A stoppage always ends a possession. After a tagged set piece the taking team
  has it. A goal is dead until the kickoff. A kickoff after a goal waits for the ball to
  reappear, which also covers a goal ruled out by VAR: play stays dead until the real restart, and
  the team on the ball then gets it.
- **Stoppages shorter than 2 s don't exist**: those are the tracker, not the referee.

## Limitations, and what we'd fix with more time

- **Stoppages are now the biggest loss.** On one bench run (normal hiding, seed 0), swapping in
  the true stoppages lifts our score from 0.60 to 0.67, with every game up 0.06-0.09. We call ~137 where ~110 is normal, so some slow live play is still called
  stopped. Throw-ins are short (10-16 s) and easy to miss. Next: a learned live/stopped model from
  players only (as in Lang et al. 2022), trained on the Bundesliga alive flag.
- **Our training keys aren't the organisers' keys.** DFL flips on every touch, including blocked
  shots; the challenge says touches without control don't count. We hedge with the 1 s merge, but
  the exact line the organisers drew is unknown to us.
- **The fake ball-hiding is a model of our tracker, not the tracker.** We checked that a different
  hiding recipe gives the same gain, but the real match may still behave differently.
- **Substitutions and injuries** have no rule of their own.
- **Throw-in team.** The tags name no team for throw-ins; guessing "the team that didn't touch it
  last" didn't help on the bench, so it's off.

## Reproduction

Needs Python 3.12 and the match data bundle, plus the 7 Bundesliga games (see the links above).

```
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.txt -r requirements-starter.txt -r requirements-team.txt
# match data in data/ (as DATA.md says); the Bundesliga files (DFL_*.xml) flat in data/bundesliga/
python prep/run_real.py --name tiki_data
```

This writes `evaluation/results/tiki_data.csv` and runs the official validator. It takes about
8 minutes from a cold start, including training the model, and the output is the same
file byte for byte. Everything is seeded and the versions are pinned.
