# Interfaces for `experiments/atallah/ball_ownership/` (agreed 15 Nov 2026)

Every module in this folder builds against these signatures. Change them here first, then in code.

## Ground rules

- Never read the contents of `data/tactical/`, `data/broadcast/`, `evaluation/gt/` or `evaluation/results/` into an agent's context. Scripts print aggregates only (counts, scores, histograms). Per-spell diagnostics go to gitignored `data/sample/cache/`.
- Never edit `starter/`, `evaluation/` or `games.py` (organisers' code). `prep/` is shared team code: import from it, do not edit it until promotion.
- Deterministic everywhere: fixed seeds, no wall-clock in outputs.
- Run from the repo root: `uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/<script>.py ...`
- The practice match is Metrica Sample Game 3 in `data/sample/` (already downloaded; answer key `data/sample/sample_gt.csv`; row 8 files `data/sample/results*/ball_out_or_speed.csv`). Row 8 scores 0.5025 clean / 0.4444 noisy, 321 possessions.

## `_paths.py`

```python
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))      # repo root
for sub in ("prep", "starter", "evaluation", os.path.join("experiments", "atallah")):
    p = os.path.join(ROOT, sub)
    if p not in sys.path: sys.path.insert(0, p)
```
Every script starts with `import _paths  # noqa` (same folder), then `import possession_metrics as pm`, `from sticky import ...` etc.

## `cache.py`

```python
Practice = namedtuple("Practice", "name df_clean df_noisy gt_labels gt_codes runs segments teams dead pitch")
def build(force=False) -> None       # loads Sample Game 3 once, writes data/sample/cache/{clean.pkl,noisy.pkl,masks.npz,teams.json}
def load_practice() -> Practice      # builds if the cache is missing
```
- `df_clean`: kloppy `to_df()` of Sample Game 3: `frame_id`, `period_id`, `ball_x`, `ball_y`, `<id>_x`, `<id>_y` (0 to 1 coordinates). `df_noisy = sample_game.drop_ball(df_clean, alive)` with `alive = isin(gt_labels, ["H","A"])`, seed 0.
- `gt_labels`: string array from `sample_gt.csv`; `gt_codes = pm.label_codes(gt_labels)`; `runs = pm.valid_runs(gt_codes)`.
- `segments = sticky.period_segments(df_clean)`; `teams = sticky.players_by_team(ds)` (two lists of player ids).
- `dead`: dict of bool arrays, length N: `"clean" = dead_from_ball_out(df_clean, segments) | dead_from_players(df_clean, sum(teams, []), segments)`, `"noisy"` the same on `df_noisy` (player part identical), `"oracle" = gt_labels == "D"`.
- `pitch = sample_game.PITCH` = (105.0, 68.0). `name = "practice"`.

## `rules.py`

```python
def segment_labels(near, dead, switch_frames=8, date_back=0, instant=None, min_spell=0) -> np.ndarray  # dtype '<U1'
def labels(df, teams, segments, dead, pitch, **params) -> np.ndarray   # '<U1', len(df); 'X' outside segments
VARIANTS: dict[str, callable]   # name -> fn(df, teams, segments, dead, pitch, **params) -> labels
```
- `segment_labels(near, dead)` with defaults must equal `sticky.sticky_segment(near, dead)` element for element.
- `near`: array of "H" / "A" / "" per frame of one segment. `instant`: same shape, "H"/"A"/"" forcing a switch at that frame without confirmation (and restarting the count). `date_back`: integer added to each confirmed switch frame (negative = earlier), clamped to the live stretch. `min_spell`: an instant-caused spell shorter than this that reverts to the previous team with no confirmed near frames in between is dropped.
- `VARIANTS["closest_row8"]` returns exactly `sticky.sticky_labels(df, teams, segments, "closest", dead=dead, pitch=pitch)`.
- `VARIANTS["ball_ownership"]` is the new rule (owned by the rule task). Params are keyword arguments with defaults in one dict `DEFAULTS` at the top of `rules.py`.

## `harness.py`

```python
def score(labels, S) -> dict      # {"mean_f1", "n_pred", "n_gt", "per_iou": {thr: {"f1","n_matched","n_missed","n_spurious"}}}
def run(variant, params=None, sets=("clean","noisy"), dead_mode="fixed") -> list[dict]   # prints one row per (set, mode)
def register_set(name, loader)    # loader() -> object with .df .gt_codes .runs .segments .teams .dead{"fixed","oracle"} .pitch
```
- `score` = `pm.fill_abstentions(pm.label_codes(labels), S.runs)` then `pm.spell_scores(S.gt_codes, filled, S.runs)`.
- Built-in sets: `"clean"` and `"noisy"` from `load_practice()` (df and dead["clean"|"noisy"]); `"oracle"` mode swaps in `dead["oracle"]`.
- CLI: `--variant NAME --set clean|noisy|both|<registered> --mode fixed|oracle|both --param k=v ... --sweep k=a,b,c (max two keys) --bootstrap N --write`. `--write` dumps `data/sample/results_<set>/<variant>[_<params>].csv` via `baseline.write_submission`.
- Printed row: `set mode variant params | spellF1 | n_pred/n_gt | @0.3 m/M/S | @0.5 m/M/S | @0.7 m/M/S` (m matched, M missed, S spurious).

## `checks.py`

```python
def extra_ballpark(labels, segments) -> dict   # prints and returns: spells_under_12, tot_bursts_under_25, spell_len_p10_p50_p90_s, home_share
```

## `errors.py`

CLI `--variant NAME --set clean|noisy|<registered> --mode fixed|oracle --iou 0.5`. Uses `plot_possessions.greedy_pairs` (import, do not copy). Prints the category table, the three histograms and the sandwich table; writes `data/sample/cache/errors_<variant>_<set>_<mode>.csv`.

## `idsse.py`

```python
def build(match_ids=("J03WMX","J03WN1"), force=False)   # kloppy.sportec.load_open_tracking_data; cache under data/idsse/
def load() -> object   # registered with harness.register_set("idsse", idsse.load): .df .gt_codes .runs .segments .teams .dead{"fixed","oracle"} .pitch
```
- Degradation (seeded): remove the ball in contiguous blocks until 41% of in-play frames are missing, biased to frames with 3 or more players within 3 m of the ball; permute slot identities at random intervals. `dead["oracle"]` from `BallStatus`; `dead["fixed"]` from the prep stoppage code on the degraded frame.
- Truth `gt_codes` from `BallPossession` (H/A) and `BallStatus` (D), X outside periods.

## `run_real_variant.py`

CLI `--variant NAME --name OUT [--param k=v ...]`. First run caches `run_real.load_frames()` to `data/cache/real_frames.pkl` and the team lists to `data/cache/real_teams.json`. Replaces `run_real.sticky_labels` with a wrapper over `rules.VARIANTS[NAME]`, calls `run_real.predict`, writes `evaluation/results/OUT.csv`, prints `run_real.ballpark` and `checks.extra_ballpark`, then runs `evaluation/validate_submission.py` and `evaluation/run_evaluation.py` as subprocesses.

## `RESULTS.md`

Append-only. One table row per scored run:
`| date | set | mode | variant | params | spellF1 | n_pred/n_gt | matched/missed/spurious @0.5 | note |`

## Verification (farabi + Lean)

- Claims about each task go in `experiments/atallah/ball_ownership/claims/<task>.md` as a fenced `farabi` block (one fact per claim, `file:` and `test:` evidence).
- Allowed test commands are listed in the repo's `farabi.yaml` (`command.allow`); use only those.
- Lean proofs live in `experiments/atallah/ball_ownership/proofs/` (a lake project). A proof is cited as `file:` evidence plus the `lake build` test command. No `sorry`, `admit` or `axiom`.
