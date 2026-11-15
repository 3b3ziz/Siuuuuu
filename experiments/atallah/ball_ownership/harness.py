"""Score a possession rule on the practice match (and any registered set), one line per run.

    uv run --with numpy --with pandas --with kloppy --with scipy \
        python experiments/atallah/ball_ownership/harness.py \
        --variant closest_row8 --set both --mode both [--param k=v ...] \
        [--sweep k=a,b,c [--sweep k2=...]] [--bootstrap N] [--write] [--note TEXT]

Printed row:  set mode variant params | spellF1 | n_pred/n_gt | @0.3 m/M/S | @0.5 m/M/S | @0.7 m/M/S
(m matched, M missed, S spurious). Every scored run is also appended as a row to RESULTS.md.

Sets: "clean" and "noisy" are the practice match with the fixed dead mask of that set
(ball_out | player speed); mode "oracle" swaps in the truth's D frames, the ceiling for the
ownership rule alone. Other sets register with register_set(name, loader).
"""

import argparse
import itertools
import os
from datetime import date

import numpy as np

import _paths
import possession_metrics as pm
from baseline import write_submission

import cache
import rules

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_MD = os.path.join(HERE, "RESULTS.md")
RESULTS_HEADER = (
    "# Results log\n\n"
    "Append-only log of every scored run of `harness.py` on the practice match (Metrica Sample\n"
    "Game 3) and any registered set. `set` is the data (`clean` = full ball, `noisy` = ball hidden\n"
    "41% of live frames like the real match); `mode` is the stoppage mask (`fixed` = ball out or\n"
    "players slow, `oracle` = the truth's D frames: the ceiling for the ownership rule alone).\n"
    "spellF1 is the mean possession-spell F1 over IoU 0.3-0.7 (`evaluation/possession_metrics.py`).\n"
    "Reference: row 8 (`closest_row8`) scores 0.5025 clean / 0.4444 noisy, 321 possessions vs 381.\n\n"
    "| date | set | mode | variant | params | spellF1 | n_pred/n_gt | matched/missed/spurious @0.5 | note |\n"
    "|---|---|---|---|---|---|---|---|---|\n"
)
REPORT_IOUS = (0.3, 0.5, 0.7)


class EvalSet(object):
    """What a registered loader returns: .df .gt_codes .runs .segments .teams .dead{} .pitch."""

    def __init__(self, name, df, gt_codes, runs, segments, teams, dead, pitch):
        self.name, self.df, self.gt_codes, self.runs = name, df, gt_codes, runs
        self.segments, self.teams, self.dead, self.pitch = segments, teams, dead, pitch


_practice = []   # loaded once, shared by the two built-in sets


def _practice_set(which):
    if not _practice:
        _practice.append(cache.load_practice())
    P = _practice[0]
    df = P.df_clean if which == "clean" else P.df_noisy
    return EvalSet(which, df, P.gt_codes, P.runs, P.segments, P.teams,
                   {"fixed": P.dead[which], "oracle": P.dead["oracle"]}, P.pitch)


SETS = {
    "clean": lambda: _practice_set("clean"),
    "noisy": lambda: _practice_set("noisy"),
}
_loaded = {}


def register_set(name, loader):
    """loader() -> object with .df .gt_codes .runs .segments .teams .dead{"fixed","oracle"} .pitch"""
    SETS[name] = loader


# Optional set: the two open IDSSE matches (idsse.py, owned by another task). A missing or broken
# idsse.py must never stop the practice-match harness, so any import error is swallowed here.
try:
    import idsse as _idsse
    register_set("idsse", _idsse.load)
    if hasattr(_idsse, "load_clean"):
        register_set("idsse_clean", _idsse.load_clean)
except Exception:  # ImportError, SyntaxError, missing dependency, ...
    pass


def get_set(name):
    if name not in _loaded:
        if name not in SETS:
            raise KeyError("unknown set {!r}; known: {}".format(name, sorted(SETS)))
        _loaded[name] = SETS[name]()
    return _loaded[name]


def score(labels, S):
    """{"mean_f1", "n_pred", "n_gt", "per_iou": {thr: {"f1","n_matched","n_missed","n_spurious"}}}"""
    filled = pm.fill_abstentions(pm.label_codes(labels), S.runs)
    r = pm.spell_scores(S.gt_codes, filled, S.runs)
    return {
        "mean_f1": r["mean_f1"],
        "n_pred": r["n_pred"],
        "n_gt": r["n_gt"],
        "per_iou": {thr: {k: v[k] for k in ("f1", "n_matched", "n_missed", "n_spurious")}
                    for thr, v in r["per_iou"].items()},
    }


def params_str(params):
    return ",".join("{}={}".format(k, params[k]) for k in sorted(params)) if params else "-"


def params_tag(params):
    return "_".join("{}={}".format(k, params[k]) for k in sorted(params)) if params else ""


def format_row(row):
    s = row["score"]
    cells = ["{} {} {} {}".format(row["set"], row["mode"], row["variant"], params_str(row["params"])),
             "{:.4f}".format(s["mean_f1"]), "{}/{}".format(s["n_pred"], s["n_gt"])]
    for thr in REPORT_IOUS:
        p = s["per_iou"][thr]
        cells.append("@{} {}/{}/{}".format(thr, p["n_matched"], p["n_missed"], p["n_spurious"]))
    if row.get("ci") is not None:
        cells.append("ci90 [{:.4f}, {:.4f}]".format(*row["ci"]))
    return " | ".join(cells)


def append_results(row, note=""):
    if not os.path.isfile(RESULTS_MD):
        with open(RESULTS_MD, "w") as handle:
            handle.write(RESULTS_HEADER)
    s = row["score"]
    p = s["per_iou"][0.5]
    line = "| {} | {} | {} | {} | {} | {:.4f} | {}/{} | {}/{}/{} | {} |\n".format(
        date.today().isoformat(), row["set"], row["mode"], row["variant"],
        params_str(row["params"]).replace("|", "/"), s["mean_f1"], s["n_pred"], s["n_gt"],
        p["n_matched"], p["n_missed"], p["n_spurious"], note.replace("|", "/"))
    with open(RESULTS_MD, "a") as handle:
        handle.write(line)


def run(variant, params=None, sets=("clean", "noisy"), dead_mode="fixed", bootstrap=0,
        write=False, note="", log=True):
    """Score one variant on each (set, mode). Prints one row each; returns the rows as dicts.

    Each dict: set, mode, variant, params, score (see score()), labels, ci (or None).
    dead_mode: "fixed" | "oracle" | "both".
    """
    params = dict(params or {})
    fn = rules.VARIANTS[variant]
    modes = ("fixed", "oracle") if dead_mode == "both" else (dead_mode,)
    rows = []
    for set_name in sets:
        S = get_set(set_name)
        for mode in modes:
            labels = fn(S.df, S.teams, S.segments, S.dead[mode], S.pitch, **params)
            row = {"set": set_name, "mode": mode, "variant": variant, "params": params,
                   "score": score(labels, S), "labels": labels, "ci": None}
            if bootstrap:
                filled = pm.fill_abstentions(pm.label_codes(labels), S.runs)
                row["ci"] = pm.bootstrap_spell_f1(S.gt_codes, filled, S.runs, bootstrap)
            print(format_row(row))
            if log:
                append_results(row, note)
            if write:
                tag = variant + ("_" + params_tag(params) if params else "")
                if mode == "oracle":
                    tag += "_oracle"
                path = os.path.join(cache.sample_game.SAMPLE, "results_" + set_name, tag + ".csv")
                write_submission(path, labels)
                print("  wrote", os.path.relpath(path, _paths.ROOT))
            rows.append(row)
    return rows


def parse_value(text):
    """'8' -> 8, '1.5' -> 1.5, 'none' -> None, 'true' -> True, anything else stays a string."""
    low = text.strip().lower()
    if low in ("none", "null"):
        return None
    if low in ("true", "false"):
        return low == "true"
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            pass
    return text.strip()


def parse_params(items):
    out = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit("--param expects k=v, got {!r}".format(item))
        k, v = item.split("=", 1)
        out[k.strip()] = parse_value(v)
    return out


def parse_sweep(items):
    """[(key, [values])] from k=a,b,c strings; at most two keys."""
    out = []
    for item in items or []:
        if "=" not in item:
            raise SystemExit("--sweep expects k=a,b,c, got {!r}".format(item))
        k, vs = item.split("=", 1)
        out.append((k.strip(), [parse_value(v) for v in vs.split(",") if v.strip()]))
    if len(out) > 2:
        raise SystemExit("--sweep takes at most two keys")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--variant", default="closest_row8", help="one of {}".format(sorted(rules.VARIANTS)))
    parser.add_argument("--set", default="both", help="clean | noisy | both | <registered>")
    parser.add_argument("--mode", default="fixed", choices=("fixed", "oracle", "both"))
    parser.add_argument("--param", action="append", default=[], metavar="k=v")
    parser.add_argument("--sweep", action="append", default=[], metavar="k=a,b,c",
                        help="grid over one or two keys (repeat the flag for the second)")
    parser.add_argument("--bootstrap", type=int, default=0, metavar="N",
                        help="draws for the 90%% bootstrap interval of spellF1")
    parser.add_argument("--write", action="store_true",
                        help="dump data/sample/results_<set>/<variant>[_<params>].csv")
    parser.add_argument("--note", default="", help="free text for the RESULTS.md row")
    args = parser.parse_args()

    if args.variant not in rules.VARIANTS:
        raise SystemExit("unknown variant {!r}; known: {}".format(args.variant, sorted(rules.VARIANTS)))
    sets = ("clean", "noisy") if args.set == "both" else (args.set,)
    base = parse_params(args.param)
    sweep = parse_sweep(args.sweep)

    grids = [[(k, v) for v in vs] for k, vs in sweep] or [[]]
    combos = list(itertools.product(*grids)) if sweep else [()]
    for combo in combos:
        params = dict(base)
        params.update(dict(combo))
        run(args.variant, params, sets=sets, dead_mode=args.mode, bootstrap=args.bootstrap,
            write=args.write, note=args.note)


if __name__ == "__main__":
    main()
