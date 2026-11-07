# Ahmad's experiments

Tools for looking at possessions, plus the figures used in the team brief. Nothing here is part of the submission pipeline.

| File | What it does |
|---|---|
| `plot_possessions.py` | Draws a submission CSV against the ground truth as timeline strips (truth, your file, what spellF1 scores, matched vs invented possessions at a chosen IoU) in one local HTML file. `uv run --with numpy --with pandas python experiments/atallah/plot_possessions.py evaluation/results/baseline_smooth50.csv` |
| `pitch_view.py` + `pitch_view_template.html` | Replays a short window of the real tracking on a stadium canvas (players, ball, trails, missing-ball ring, optional H/A/D banner from any label CSV). `uv run --with numpy --with pandas --with kloppy python experiments/atallah/pitch_view.py --labels evaluation/gt/BAR-ATH_possession_gt_public.csv` |
| `figures/iou-bench/` | Interactive isometric figure: how spellF1 pairs possessions by IoU and grades them. Built pages, a pasteable `fragment.html`, and the source (`model.mjs`, `scene.mjs`, `build.mjs`). |
| `figures/smoothing-window/` | Same style: why majority-vote smoothing lifts spellF1 and then loses short real possessions. |

Both scripts write to `data/views/`, which git ignores, because their output contains match data. The figures use synthetic data only. Rebuilding a figure needs the Anatomy skill (`npx skills add wheresryan22/anatomy`), whose kit the build scripts import from `.agents/skills/anatomy/kit`; the built HTML needs nothing.
