# Team repo: More than a Hack 2027, possession challenge

For every frame of one LaLiga match (Barça vs Athletic, 25 frames a second), label who has the ball: `H` home, `A` away, `D` play stopped, `X` no answer. Ranked on how many real possessions we recover (score 0-1). Read `CHALLENGE.md`, `EVALUATION.md` and `RULES.md` before changing approach. This repo started as a clone of the organisers' repo, which is linked as the `upstream` remote.

## Rules that can disqualify us

- No hand labels on this match, in any amount, for anything. Labels must come out of code. Watching the video to get ideas is fine.
- No data about this match from anyone else (Opta, StatsBomb, etc.). General league stats and other matches are fine.
- The 5 public minutes (`evaluation/gt/`) are for checking the pipeline works. Never tune on them or pick between versions with them.
- Never commit the match data. `data/` is gitignored. The repo goes public at submission.
- The repo must regenerate our submitted file exactly. No unseeded randomness.

## Layout

- `prep/`: shared code. The current best approach and the practice-match tools. Change it carefully and tell the team, since everyone builds on it.
- `experiments/<your-name>/`: your own scratch space. Commit freely, nobody else edits it.
- `docs/notes.md`: shared knowledge. Results table of approaches, football reasoning, general stats, open questions. Add a row when an experiment is worth keeping.
- `starter/`, `evaluation/`, `games.py`: organisers' code. Don't edit; pull their updates from `upstream`.

## Setup

```
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt -r requirements-starter.txt
```

Unzip the match data into `data/`. The practice match (Metrica's public Sample Game 3) goes in `data/sample/`, from https://github.com/metrica-sports/sample-data/tree/master/data/Sample_Game_3

## Commands

- `python prep/run_real.py`: current best approach on the real match. Writes the submission, validates it, scores it on the 5 public minutes, prints sanity checks.
- `python prep/sample_game.py`, then `python prep/ball_out.py`: rebuild the practice answer key and run the current approach on the practice match.
- `python evaluation/run_evaluation.py --gt data/sample/sample_gt.csv --results data/sample/results_noisy --out data/sample/eval`: score on the practice match (the noisy version hides the ball 41% of the time, like our match).

## How we work

- Compare ideas on the practice match (noisy version), not the 5 public minutes.
- Score differences under ~0.04 can be luck. One match has only a few hundred possessions.
- Ask before assuming how football works. The team knows football; write down what they say in `docs/notes.md` under "Football thinking".
- Personal preferences go in your own `CLAUDE.local.md` (gitignored) or `~/.claude/CLAUDE.md`, not here.
