# Claims: promotion of the ball-ownership rule to prep/ (TIKI-17)

`prep/ball_ownership.py` is the row 9 rule moved into the team's shared code (features, touch
rule, gap switches and the generalised state machine from `features.py`, `ball_rule.py` and
`rules.segment_labels`), with `prep/sticky.py` rule `"touch"` delegating to it and
`prep/run_real.py` using it by default. Verified on 15 Nov 2026: `test_promotion.py` reports 0
mismatches on every check; `evaluation/run_evaluation.py` on the written practice files gives
`ball_ownership` 0.6240 clean (351 possessions) and 0.5087 noisy (289); `prep/run_real.py` writes
`evaluation/results/ours_row9.csv` with sha256
`2995e6556e30e8af2294d757ddf2228ef3a41cba621bcb925e4e9716871094d1`, identical to
`ball_ownership_v1.csv` from `run_real_variant.py` (stoppage share 43%, 153 stoppages, 330
possessions; public 5 min 0.4556 as a pipeline check only).

`test_promotion.py` is not yet in `farabi.yaml` `command.allow`; until that line is added, the
claims below that cite it also cite `test_harness.py` where it covers the same fact.

```farabi
claims:
  - id: p1
    text: >-
      prep/ball_ownership.py imports only numpy, scipy.signal.savgol_filter and prep/sticky at
      module level; kloppy is imported inside main() only
    evidence:
      - file: prep/ball_ownership.py:28-36
      - file: prep/ball_ownership.py:387-390
  - id: p2
    text: >-
      Every threshold is a module constant under the comment "picked on the practice match (row 9
      in docs/notes.md)" with the published values (zone 1.0 m, exit 0.1 m, turn 10 deg, speed
      change 5 m/s, min speed 1.5 m/s, hold 8 frames, min_spell 8, swap 12 m/s, gap extrapolation
      1 s, reality 2 m), collected in DEFAULTS, and DEFAULTS equals the experiment's DEFAULTS
    evidence:
      - file: prep/ball_ownership.py:40-63
      - file: experiments/atallah/ball_ownership/test_promotion.py:45-47
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_promotion.py
  - id: p3
    text: >-
      ball_ownership_labels(df, players_by_team, segments, dead, pitch=PITCH, **params) returns a
      '<U1' array of len(df) that is 'X' outside the segments and segment_labels output inside
      them, and an unknown keyword raises ValueError
    evidence:
      - file: prep/ball_ownership.py:364-384
      - file: experiments/atallah/ball_ownership/test_promotion.py:57-59
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_promotion.py
  - id: p4
    text: >-
      prep/ball_ownership.segment_labels is the generalised state machine of the experiment's
      rules.segment_labels (switch_frames, date_back, instant, min_spell) and gives identical
      labels on 100 random near, dead and instant inputs
    evidence:
      - file: prep/ball_ownership.py:285-356
      - file: experiments/atallah/ball_ownership/test_promotion.py:88-101
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_promotion.py
  - id: p5
    text: >-
      On the practice clean and noisy frames with the fixed dead masks, prep ball_ownership_labels
      equals rules.VARIANTS["ball_ownership"] element for element (0 mismatches)
    evidence:
      - file: experiments/atallah/ball_ownership/test_promotion.py:50-56
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_promotion.py
  - id: p6
    text: >-
      sticky.sticky_labels with rule "touch" delegates to ball_ownership_labels with the given
      dead mask, or dead_from_missing_ball when dead is None, and its signature is unchanged
    evidence:
      - file: prep/sticky.py:94-105
      - file: experiments/atallah/ball_ownership/test_promotion.py:61-64
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_promotion.py
  - id: p7
    text: >-
      Rules "alone" and "closest" of sticky.sticky_labels are unchanged. "closest" with the fixed
      dead mask reproduces data/sample/results*/ball_out_or_speed.csv (row 8), and "alone" and
      "closest" with dead=None reproduce sticky.csv and sticky_closest.csv, 0 mismatches
    evidence:
      - file: prep/sticky.py:106-120
      - file: experiments/atallah/ball_ownership/test_promotion.py:66-78
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_harness.py
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_promotion.py
  - id: p8
    text: >-
      prep/run_real.predict calls sticky_labels with rule "touch" and the --name default is
      "ours_row9"; nothing else in the file changed
    evidence:
      - file: prep/run_real.py:46-50
      - file: prep/run_real.py:66-68
  - id: p9
    text: >-
      prep/ball_ownership.main writes data/sample/results/ball_ownership.csv and
      data/sample/results_noisy/ball_ownership.csv with write_submission, using the same dead
      masks as prep/ball_out.py (dead_from_ball_out(frame) | dead_from_players), and the written
      files equal the labels from ball_ownership_labels
    evidence:
      - file: prep/ball_ownership.py:387-410
      - file: experiments/atallah/ball_ownership/test_promotion.py:80-86
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_promotion.py
  - id: p10
    text: scipy is listed in requirements.txt for prep/ball_ownership.py
    evidence:
      - file: requirements.txt:11
  - id: p11
    text: >-
      docs/notes.md has row 9 in the results table (practice 0.624 clean, 0.509 noisy, public
      5 min 0.456 sanity only, real match "-", 351 / 289 possessions found)
    evidence:
      - file: docs/notes.md:97
  - id: p12
    text: >-
      docs/notes.md "Football thinking" has three new bullets (the truth switches at the first
      touch, a flying or loose ball stays with the last team, a 1 m zone with a kinematic
      confirmation replaces closest-within-2-m-for-8-frames) and the practice-match section has
      the "Ownership ceiling" sentence (row 8 0.593 / 0.563, row 9 0.733 / 0.626 with the truth's
      stoppages)
    evidence:
      - file: docs/notes.md:48-50
      - file: docs/notes.md:79
```
