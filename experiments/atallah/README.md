# Ahmad's experiments

Tools for looking at possessions, plus the figures used in the team brief. Nothing here is part of the submission pipeline.

| File | What it does |
|---|---|
| `plot_possessions.py` | Draws a submission CSV against the ground truth as timeline strips (truth, your file, what spellF1 scores, matched vs invented possessions at a chosen IoU) in one local HTML file. `uv run --with numpy --with pandas python experiments/atallah/plot_possessions.py evaluation/results/baseline_smooth50.csv` |
| `pitch_view.py` + `pitch_view_template.html` | Replays a short window of the real tracking on a stadium canvas (players, ball, trails, missing-ball ring, optional H/A/D banner from any label CSV). `uv run --with numpy --with pandas --with kloppy python experiments/atallah/pitch_view.py --labels evaluation/gt/BAR-ATH_possession_gt_public.csv` |
| `figures/iou-bench/` | Interactive isometric figure: how spellF1 pairs possessions by IoU and grades them. Built pages, a pasteable `fragment.html`, and the source (`model.mjs`, `scene.mjs`, `build.mjs`). |
| `figures/smoothing-window/` | Same style: why majority-vote smoothing lifts spellF1 and then loses short real possessions. |

## `ball_ownership/`: the row 9 rule, its harness and its proofs

Where row 9 (`prep/ball_ownership.py`, the team's default since TIKI-17) was built and verified. `INTERFACES.md` there fixes every signature. Scripts print aggregates only (counts, scores, hashes), never a row of match data.

| File | What it does |
|---|---|
| `_paths.py` | Puts `prep/`, `starter/`, `evaluation/` and `experiments/atallah/` on `sys.path`; every script starts with `import _paths` |
| `cache.py` | Loads the practice match (Metrica Sample Game 3) once into `data/sample/cache/`: clean and noisy frames, answer key, dead masks (fixed and oracle), team lists. `load_practice()` returns it in a second |
| `features.py` | Per-frame kinematics in metres: Savitzky-Golay ball smoothing, distances, velocities, direction change, swap guard, extremum masks. NaN stays NaN |
| `ball_rule.py` | The ball-ownership rule itself (near / instant arrays from touches, gap switches) on top of `rules.segment_labels`; registers `VARIANTS["ball_ownership"]` |
| `rules.py` | One signature for every rule `fn(df, teams, segments, dead, pitch, **params)`; `segment_labels` is `sticky_segment` generalised (instant switches, date_back, min_spell); `VARIANTS` maps names to rules, `closest_row8` is the regression anchor |
| `harness.py` | Scores a variant with the official metric on clean / noisy / oracle / registered sets, parameter sweeps, bootstrap, `--write` dumps a practice CSV |
| `errors.py` | Categorises the truth possessions a variant misses (late switch, merged, split by a false stoppage, ...) and writes a per-spell table to `data/sample/cache/` |
| `checks.py` | `extra_ballpark(labels, segments)`: spell-shape sanity checks (sub-0.5 s spells, turnover bursts, length percentiles, home share) |
| `idsse.py` | A third practice set from the IDSSE open matches (kloppy Sportec), degraded to our match's ball visibility and slot swaps; registered with the harness |
| `replay_export.py` | Writes `data/sample/views/replay.json` (gitignored): seven 30 s clips of the practice match (noisy copy) with truth / row 8 / row 9 labels and the whole-match label strips, picked deterministically from the scorer's matching. The Ball Ownership Scoreboard's Replay tab reads it as an attached source. Prints counts only |
| `run_real_variant.py` | Runs any variant on the real match the way `prep/run_real.py` does (cached frames under `data/cache/`), writes `evaluation/results/<name>.csv`, validates and scores it |
| `test_harness.py`, `test_rules.py`, `test_promotion.py`, `test_proofs.py` | Plain-assert checks: rows 1-8 still reproduce; the rule on synthetic scenes; `prep/ball_ownership.py` equals the experiment frame for frame; the Lean project builds with no proof holes |
| `proofs/` | Lean 4 (lake) proofs about the segment state machine, gaps, IoU matching and the degradation model |
| `claims/`, `verify.sh` | farabi claims files (one fact per claim with file and test evidence) and the script that verifies them all against the repo's `farabi.yaml` |
| `INTERFACES.md`, `RESULTS.md` | The agreed signatures, and the append-only log of every scored run |

Two commands cover most of it (run from the repo root):

```
uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/harness.py --variant ball_ownership --set both --mode both
uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/run_real_variant.py --variant ball_ownership --name ball_ownership_v1
```

Both scripts above (`plot_possessions.py`, `pitch_view.py`) write to `data/views/`, which git ignores, because their output contains match data. The figures use synthetic data only. Rebuilding a figure needs the Anatomy skill (`npx skills add wheresryan22/anatomy`), whose kit the build scripts import from `.agents/skills/anatomy/kit`; the built HTML needs nothing.
