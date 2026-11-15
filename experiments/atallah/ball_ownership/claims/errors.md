# Claims: errors.py (TIKI-12)

Error categorisation of the unmatched truth possessions, switch-offset and first-touch
histograms, truth spell lengths and the sandwich table, for any `rules.VARIANTS` entry on any
`harness` set. Verified on 15 Nov 2026 with the test command below (row 8, clean, fixed:
411 predicted vs 381 truth possessions, 202 matched at IoU 0.5, 179 categorised).

```farabi
claims:
  - id: e1
    text: The CLI takes --variant, --set, --mode fixed|oracle, --iou (default 0.5) and repeatable --param k=v, loads the set through harness.get_set and computes labels with rules.VARIANTS[NAME](df, teams, segments, dead[mode], pitch, **params)
    evidence:
      - file: experiments/atallah/ball_ownership/errors.py:302-310
      - file: experiments/atallah/ball_ownership/errors.py:367-380
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/errors.py --variant closest_row8 --set clean --mode fixed
  - id: e2
    text: Spell matching uses pm.fill_abstentions, pm.possession_spells, pm.spell_overlaps and plot_possessions.greedy_pairs(overlaps, iou), imported, not copied
    evidence:
      - file: experiments/atallah/ball_ownership/errors.py:30-31
      - file: experiments/atallah/ball_ownership/errors.py:306-310
  - id: e3
    text: Every unmatched truth possession gets exactly one category, tested in the order merged by missed stoppage, flip-flop, wrong team, missed switch (flagged short under 16 frames), then late switch / early switch / late or early end from the start and end offsets of the best same-team predicted spell
    evidence:
      - file: experiments/atallah/ball_ownership/errors.py:99-155
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/errors.py --variant closest_row8 --set clean --mode fixed
  - id: e4
    text: A count table per category is printed and the per-spell rows (start, stop, team, len_s, category, start_off, end_off) are written to data/sample/cache/errors_<variant>_<set>_<mode>.csv, a gitignored folder
    evidence:
      - file: experiments/atallah/ball_ownership/errors.py:178-195
      - file: experiments/atallah/ball_ownership/errors.py:327-335
      - file: .gitignore:32
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/errors.py --variant closest_row8 --set clean --mode fixed
  - id: e5
    text: The switch-offset histogram comes from pm.transition_scores(gt_sub, pred_sub, tol=50, typed="to")["pairs"] with both transition lists restricted to H<->A (both codes in {0,1}), binned 4 frames wide from -48 to +48 as ASCII bars with median, p10, p90 and the count of truth switches with no prediction within 50 frames
    evidence:
      - file: experiments/atallah/ball_ownership/errors.py:228-234
      - file: experiments/atallah/ball_ownership/errors.py:312-314
      - file: experiments/atallah/ball_ownership/errors.py:346-350
  - id: e6
    text: The first-touch histogram is, per truth H<->A switch at frame s to team T, s minus the first frame in [s-25, s+25] where a player of T is within 1.0 m of the ball, with distances in metres from the set's teams lists, <id>_x/_y columns and pitch via sticky.team_distances; the practice sets use the clean frame
    evidence:
      - file: experiments/atallah/ball_ownership/errors.py:237-254
      - file: experiments/atallah/ball_ownership/errors.py:319-322
  - id: e7
    text: Truth spell lengths are reported as counts under 8, 12, 20 and 25 frames plus the total
    evidence:
      - file: experiments/atallah/ball_ownership/errors.py:257-261
  - id: e8
    text: The sandwich table lists predicted spells whose frame-adjacent neighbours on both sides are the other team, binned 1-4, 5-8, 9-15, 16-25, 26-50 frames, with the count written, the share overlapping a same-team truth spell and the count of truth sandwiches of that length
    evidence:
      - file: experiments/atallah/ball_ownership/errors.py:266-299
  - id: e9
    text: The script prints aggregates only (counts, shares, percentiles, histogram bars and the csv path) and never a row of the tracking or truth data; per-spell diagnostics go only to the csv under data/sample/cache/
    evidence:
      - file: experiments/atallah/ball_ownership/errors.py:338-363
  - id: e10
    text: idsse is registered with harness.register_set("idsse", idsse.load) only when idsse.py imports, inside a try block, so the practice runs do not depend on it
    evidence:
      - file: experiments/atallah/ball_ownership/errors.py:38-42
  - id: e11
    text: Nothing in errors.py is random or reads the clock, so repeated runs print identical tables
    evidence:
      - file: experiments/atallah/ball_ownership/errors.py:1-383
      - test: uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/errors.py --variant closest_row8 --set clean --mode fixed
```
