# Claims: replay export for the scoreboard's Replay tab (TIKI-18, GitHub #16)

`replay_export.py` writes one JSON file (`data/sample/views/replay.json`, gitignored) with fifteen
20-second clips named by situation (throw-in, free kick, fast live play, short possession, wrong
start or end, false stoppage, ...) of the practice match and the whole-match label strips for the truth, row 8 and
row 9. The scoreboard page (Ball Ownership Scoreboard, Replay tab) reads that file as an attached
source and draws the clips on the stadium canvas of `experiments/atallah/pitch_view.py`.

Measured on 15 Nov 2026 (noisy copy, fixed stoppages): 381 truth possessions, of which both rules
match 144, row 9 fixed 30, neither matches 192, row 9 lost 15 (IoU 0.5). Row 8 0.4444 with 321
spells, row 9 0.5087 with 289 spells, the same numbers as `RESULTS.md`. Row 9's 192 misses by
category: 60 merged by a false stoppage, 42 missed switch, 10 short, 25 wrong team, 4 flip-flop,
65 wrong start or end (2 late, 25 early, 38 end), 1 other.

```farabi
claims:
  - id: r1
    text: >-
      replay_export.py loads only the practice match through cache.load_practice and labels its
      noisy copy; nothing from the real match is read
    evidence:
      - file: experiments/atallah/ball_ownership/replay_export.py:105-109
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_replay.py
  - id: r2
    text: >-
      A truth possession is typical, fixed, lost or missed by whether row 8 and row 9 match it in
      the scorer's greedy one-to-one matching at IoU 0.5, and a missed one is named from
      errors.classify_spell's category
    evidence:
      - file: experiments/atallah/ball_ownership/replay_export.py:112-126
      - file: experiments/atallah/ball_ownership/replay_export.py:72-81
      - file: experiments/atallah/ball_ownership/test_replay.py:20-25
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_replay.py
  - id: r3
    text: >-
      A restart clip is named Throw-in, Goal kick or corner, or Free kick from the clean ball
      track inside the truth stoppage before it
    evidence:
      - file: experiments/atallah/ball_ownership/replay_export.py:149-162
      - file: experiments/atallah/ball_ownership/test_replay.py:41-49
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_replay.py
  - id: r4
    text: >-
      Clip picking is deterministic (best score first, earliest on ties), keeps every clip
      inside its half and never overlaps two clips
    evidence:
      - file: experiments/atallah/ball_ownership/replay_export.py:142-146
      - file: experiments/atallah/ball_ownership/replay_export.py:165-176
      - file: experiments/atallah/ball_ownership/test_replay.py:33-58
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_replay.py
  - id: r5
    text: >-
      The whole-match strips are the scorer's own constant-label segments inside the valid runs
    evidence:
      - file: experiments/atallah/ball_ownership/replay_export.py:232-233
      - file: experiments/atallah/ball_ownership/test_replay.py:86-89
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_replay.py
```
