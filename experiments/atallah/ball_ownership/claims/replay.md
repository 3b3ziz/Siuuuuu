# Claims: replay export for the scoreboard's Replay tab (TIKI-18, GitHub #16)

`replay_export.py` writes one JSON file (`data/sample/views/replay.json`, gitignored) with seven
30-second clips of the practice match and the whole-match label strips for the truth, row 8 and
row 9. The scoreboard page (Ball Ownership Scoreboard, Replay tab) reads that file as an attached
source and draws the clips on the stadium canvas of `experiments/atallah/pitch_view.py`.

Measured on 15 Nov 2026 (noisy copy, fixed stoppages): 381 truth possessions, of which both rules
match 144, row 9 fixed 30, neither matches 192, row 9 lost 15 (IoU 0.5). Row 8 0.4444 with 321
spells, row 9 0.5087 with 289 spells, the same numbers as `RESULTS.md`.

```farabi
claims:
  - id: r1
    text: >-
      replay_export.py loads only the practice match through cache.load_practice and labels its
      noisy copy; nothing from the real match is read
    evidence:
      - file: experiments/atallah/ball_ownership/replay_export.py:61-65
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_replay.py
  - id: r2
    text: >-
      A truth possession is typical, fixed, lost or missed by whether row 8 and row 9 match it in
      the scorer's greedy one-to-one matching at IoU 0.5
    evidence:
      - file: experiments/atallah/ball_ownership/replay_export.py:68-82
      - file: experiments/atallah/ball_ownership/test_replay.py:21-25
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_replay.py
  - id: r3
    text: >-
      Clip picking is deterministic, keeps every clip inside its half, never overlaps two clips
      and skips truth possessions shorter than MIN_SPELL frames
    evidence:
      - file: experiments/atallah/ball_ownership/replay_export.py:100-127
      - file: experiments/atallah/ball_ownership/test_replay.py:34-66
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_replay.py
  - id: r4
    text: >-
      The whole-match strips are the scorer's own constant-label segments inside the valid runs
    evidence:
      - file: experiments/atallah/ball_ownership/replay_export.py:130-131
      - file: experiments/atallah/ball_ownership/test_replay.py:69-72
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_replay.py
```
