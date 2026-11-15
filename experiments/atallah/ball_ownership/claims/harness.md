# Claims: practice-match harness (TIKI-11)

cache.py, rules.py, harness.py, checks.py and test_harness.py in `experiments/atallah/ball_ownership/`.
Verified on 15 Nov 2026 with the test command below: load_practice() from cache 0.31 s, 0 mismatching
frames against both `ball_out_or_speed.csv` files, row 8 scores reproduced (0.5025 clean / 0.4444 noisy,
321 predicted spells on noisy), oracle ceiling 0.5932 clean / 0.5631 noisy.

```farabi
claims:
  - id: h1
    text: cache.build writes clean.pkl, noisy.pkl, masks.npz and teams.json under data/sample/cache, with the noisy frame from sample_game.drop_ball at seed 0 and the dead masks clean = ball_out OR player speed, noisy the same on the noisy frame, oracle = answer key D
    evidence:
      - file: experiments/atallah/ball_ownership/cache.py:48-77
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_harness.py
  - id: h2
    text: cache.load_practice returns the Practice namedtuple of INTERFACES.md (name df_clean df_noisy gt_labels gt_codes runs segments teams dead pitch) and builds the cache first when it is missing
    evidence:
      - file: experiments/atallah/ball_ownership/cache.py:36
      - file: experiments/atallah/ball_ownership/cache.py:81-104
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_harness.py
  - id: h3
    text: rules.near_closest builds the per-frame H / A / empty array of the row 8 closest rule from sticky.team_distances with zone_m and margin_m
    evidence:
      - file: experiments/atallah/ball_ownership/rules.py:33-38
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_harness.py
  - id: h4
    text: rules.segment_labels(near, dead, switch_frames=8, date_back=0, instant=None, min_spell=0) with its defaults equals sticky.sticky_segment(near, dead) element for element on the practice match and on 50 seeded random segments
    evidence:
      - file: experiments/atallah/ball_ownership/rules.py:41-124
      - file: experiments/atallah/ball_ownership/test_harness.py:74-88
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_harness.py
  - id: h5
    text: A non-empty instant value at frame t forces a switch exactly at t without confirmation and restarts the near confirmation count from t
    evidence:
      - file: experiments/atallah/ball_ownership/rules.py:78-81
      - file: experiments/atallah/ball_ownership/test_harness.py:113-162
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_harness.py
  - id: h6
    text: date_back is added to each near-confirmed switch frame, clamped to the live stretch and kept between the neighbouring switches, and does not move instant switches
    evidence:
      - file: experiments/atallah/ball_ownership/rules.py:106-112
      - file: experiments/atallah/ball_ownership/test_harness.py:91-110
      - file: experiments/atallah/ball_ownership/test_harness.py:150-161
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_harness.py
  - id: h7
    text: An instant-caused spell shorter than min_spell that was never confirmed by its own near run and reverts to the previous team is dropped, so a 5-frame spell is removed by min_spell=8 while a 10-frame spell survives
    evidence:
      - file: experiments/atallah/ball_ownership/rules.py:90-104
      - file: experiments/atallah/ball_ownership/test_harness.py:164-208
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_harness.py
  - id: h8
    text: rules.labels(df, teams, segments, dead, pitch, **params) merges params over DEFAULTS, runs segment_labels per segment and labels frames outside the segments X
    evidence:
      - file: experiments/atallah/ball_ownership/rules.py:23-30
      - file: experiments/atallah/ball_ownership/rules.py:133-147
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_harness.py
  - id: h9
    text: VARIANTS["closest_row8"] calls sticky.sticky_labels(df, teams, segments, "closest", dead=dead, pitch=pitch) unchanged and reproduces data/sample/results/ball_out_or_speed.csv and data/sample/results_noisy/ball_out_or_speed.csv with 0 mismatching frames, as does rules.labels with rule=closest
    evidence:
      - file: experiments/atallah/ball_ownership/rules.py:150-158
      - file: experiments/atallah/ball_ownership/test_harness.py:37-48
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_harness.py
  - id: h10
    text: rules.py ends with a try/except ImportError hook that registers VARIANTS["ball_ownership"] from ball_rule.ball_ownership when that module exists
    evidence:
      - file: experiments/atallah/ball_ownership/rules.py:163-167
  - id: h11
    text: harness.score fills abstentions with pm.fill_abstentions over the valid runs and returns mean_f1, n_pred, n_gt and per_iou f1 / n_matched / n_missed / n_spurious from pm.spell_scores
    evidence:
      - file: experiments/atallah/ball_ownership/harness.py:97-107
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_harness.py
  - id: h12
    text: harness.score of closest_row8 gives spellF1 0.5025 clean and 0.4444 noisy at four decimals with 321 predicted spells on noisy and 381 ground-truth spells, and 0.5932 clean / 0.5631 noisy with the oracle dead mask
    evidence:
      - file: experiments/atallah/ball_ownership/test_harness.py:51-63
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_harness.py
  - id: h13
    text: harness.run scores one variant per (set, mode), prints one row per run in the format set mode variant params | spellF1 | n_pred/n_gt | @0.3 m/M/S | @0.5 m/M/S | @0.7 m/M/S and appends a row to RESULTS.md
    evidence:
      - file: experiments/atallah/ball_ownership/harness.py:118-175
      - file: experiments/atallah/ball_ownership/RESULTS.md:18-21
  - id: h14
    text: The built-in sets clean and noisy come from cache.load_practice with dead fixed = dead[set] and dead oracle = dead["oracle"], and register_set(name, loader) adds a set; idsse is registered through register_set when idsse.py imports, inside a try/except that swallows any import failure
    evidence:
      - file: experiments/atallah/ball_ownership/harness.py:57-86
  - id: h15
    text: The CLI takes --variant, --set clean|noisy|both|registered, --mode fixed|oracle|both, repeated --param k=v, --sweep k=a,b,c with at most two keys, --bootstrap N and --write, which dumps data/sample/results_<set>/<variant>[_<params>].csv via baseline.write_submission
    evidence:
      - file: experiments/atallah/ball_ownership/harness.py:203-243
      - file: experiments/atallah/ball_ownership/harness.py:167-173
  - id: h16
    text: test_harness.py prints only mismatch counts, scores and spell counts, never a frame of the match data
    evidence:
      - file: experiments/atallah/ball_ownership/test_harness.py:27-63
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_harness.py
```
