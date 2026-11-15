# Claims: run_real_variant.py (TIKI-15)

Real-match runner for the ball-ownership variants. Verified on 15 Nov 2026 with the test command
below: cache built in 44.2 s, cached load 0.14 s, 0 mismatching frames against `ours_row8.csv`
(identical sha256 `a8b56176af6dc8258d35fc2760b2c976af923a120dbdb9728ce3b19668ae86dd`).

```farabi
claims:
  - id: r1
    text: The runner caches run_real.load_frames() as data/cache/real_frames.pkl and players_by_team(ds) as data/cache/real_teams.json on the first run
    evidence:
      - file: experiments/atallah/ball_ownership/run_real_variant.py:63-78
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/run_real_variant.py --variant closest_row8 --name check_row8
  - id: r2
    text: Later runs load the frame and team lists from the cache and print the load time, rebuilding only with --rebuild-cache or when the row count disagrees with games.py
    evidence:
      - file: experiments/atallah/ball_ownership/run_real_variant.py:80-102
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/run_real_variant.py --variant closest_row8 --name check_row8
  - id: r3
    text: run_real.sticky_labels is replaced by a wrapper that ignores the positional rule argument and calls rules.VARIANTS[NAME](df, teams, segments, dead, pitch, **params)
    evidence:
      - file: experiments/atallah/ball_ownership/run_real_variant.py:119-152
  - id: r4
    text: Without rules.py only --variant closest_row8 is accepted and it calls sticky.sticky_labels(df, teams, segments, "closest", dead=dead, pitch=pitch) directly after printing a note
    evidence:
      - file: experiments/atallah/ball_ownership/run_real_variant.py:121-134
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/run_real_variant.py --variant closest_row8 --name check_row8
  - id: r5
    text: Labels come from run_real.predict, so the stoppage mask is dead_from_ball_out OR dead_from_players from prep, unchanged
    evidence:
      - file: experiments/atallah/ball_ownership/run_real_variant.py:268
      - file: prep/run_real.py:46-50
  - id: r6
    text: The submission is written to evaluation/results/OUT.csv with starter/baseline.write_submission
    evidence:
      - file: experiments/atallah/ball_ownership/run_real_variant.py:276-278
  - id: r7
    text: run_real.ballpark is printed and checks.extra_ballpark is printed when checks.py is importable
    evidence:
      - file: experiments/atallah/ball_ownership/run_real_variant.py:280-285
  - id: r8
    text: Per-slot jump statistics are printed as aggregates only, including the number of frames where any slot moves more than 3 m and the fraction of slot-frames with implied speed over 12 m/s
    evidence:
      - file: experiments/atallah/ball_ownership/run_real_variant.py:159-206
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/run_real_variant.py --variant closest_row8 --name check_row8
  - id: r9
    text: For --variant closest_row8 the labels are compared with evaluation/results/ours_row8.csv when it exists and the mismatch count and both sha256 digests are printed
    evidence:
      - file: experiments/atallah/ball_ownership/run_real_variant.py:222-238
      - file: experiments/atallah/ball_ownership/run_real_variant.py:253-254
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/run_real_variant.py --variant closest_row8 --name check_row8
  - id: r10
    text: evaluation/validate_submission.py and evaluation/run_evaluation.py are run as subprocesses with sys.executable, as in run_real.main
    evidence:
      - file: experiments/atallah/ball_ownership/run_real_variant.py:294-298
      - file: prep/run_real.py:81-83
  - id: r11
    text: The runner never prints a row of the match data; every print is a count, share, percentile, path or sha256
    evidence:
      - file: experiments/atallah/ball_ownership/run_real_variant.py:159-238
```
