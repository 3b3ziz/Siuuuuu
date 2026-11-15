"""Run one labelling variant on the real match, exactly the way prep/run_real.py does.

    uv run --with numpy --with pandas --with kloppy --with scipy \\
        python experiments/atallah/ball_ownership/run_real_variant.py \\
        --variant closest_row8 --name check_row8 [--param k=v ...] [--rebuild-cache]

What it does (INTERFACES.md, section run_real_variant.py):
  1. Loads the tracking through run_real.load_frames() once and caches it under data/cache/
     (real_frames.pkl = the reindexed DataFrame, real_teams.json = players_by_team(ds)).
     Later runs read the cache in seconds instead of minutes.
  2. Swaps run_real.sticky_labels for a wrapper over rules.VARIANTS[--variant] and calls
     run_real.predict, so the stoppage mask (ball out | players slow) is the team's, untouched.
  3. Writes evaluation/results/<--name>.csv with starter/baseline.write_submission, prints
     run_real.ballpark and checks.extra_ballpark (when checks.py exists), prints per-slot jump
     statistics of the frame (swap-guard calibration), then runs the official validator and
     evaluation/run_evaluation.py as subprocesses, like run_real.main.
  4. For --variant closest_row8 it compares the labels with evaluation/results/ours_row8.csv
     (the file prep/run_real.py writes) when that file exists, and prints the mismatch count.

Prints aggregates only: counts, shares, hashes. Never a row of the match data.
"""

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    import _paths  # (sibling module, built in parallel)
    ROOT = _paths.ROOT
except ImportError:
    ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
    for _sub in ("prep", "starter", "evaluation", os.path.join("experiments", "atallah")):
        _p = os.path.join(ROOT, _sub)
        if _p not in sys.path:
            sys.path.insert(0, _p)

import run_real  # (prep/run_real.py; pulls in games, ball_out, stoppage, sticky)
from games import GAME, GAMES, half_video_blocks, source_frames
from baseline import write_submission
import sticky

CACHE_DIR = os.path.join(ROOT, "data", "cache")
FRAMES_PKL = os.path.join(CACHE_DIR, "real_frames.pkl")
TEAMS_JSON = os.path.join(CACHE_DIR, "real_teams.json")
RESULTS_DIR = os.path.join(ROOT, "evaluation", "results")

JUMP_M = 3.0        # a slot moving more than this between consecutive frames is a jump
FAST_MS = 12.0      # implied speed above this is not a footballer running


# ---------------------------------------------------------------------------------------------
# cache
# ---------------------------------------------------------------------------------------------

def build_cache():
    """run_real.load_frames() once; pickle the frame and json-dump the team lists."""
    import pandas as pd  # (pickling goes through the DataFrame method)

    os.makedirs(CACHE_DIR, exist_ok=True)
    t0 = time.perf_counter()
    ds, df = run_real.load_frames(GAME)
    teams = sticky.players_by_team(ds)
    df.to_pickle(FRAMES_PKL)
    with open(TEAMS_JSON, "w") as handle:
        json.dump(teams, handle)
    dt = time.perf_counter() - t0
    print("cache built in {:.1f} s: {} rows, {} columns -> {}".format(dt, len(df), df.shape[1],
                                                                       os.path.relpath(FRAMES_PKL, ROOT)))
    return df, teams, dt


def load_cache(rebuild=False):
    """(df, teams, seconds, source) with source 'built' or 'cached'."""
    import pandas as pd

    n_expected = source_frames("tactical", GAME)
    if not rebuild and os.path.isfile(FRAMES_PKL) and os.path.isfile(TEAMS_JSON):
        t0 = time.perf_counter()
        df = pd.read_pickle(FRAMES_PKL)
        with open(TEAMS_JSON) as handle:
            teams = json.load(handle)
        dt = time.perf_counter() - t0
        if len(df) == n_expected and len(teams) == 2:
            print("cache loaded in {:.2f} s: {} rows, {} columns, teams of {} and {} players".format(
                dt, len(df), df.shape[1], len(teams[0]), len(teams[1])))
            return df, teams, dt, "cached"
        print("cache has {} rows, expected {}: rebuilding".format(len(df), n_expected))
    df, teams, dt = build_cache()
    if len(df) != n_expected:
        raise SystemExit("load_frames gave {} rows, games.py says {}".format(len(df), n_expected))
    return df, teams, dt, "built"


# ---------------------------------------------------------------------------------------------
# variants
# ---------------------------------------------------------------------------------------------

def parse_params(items):
    params = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit("--param wants k=v, got {!r}".format(item))
        key, value = item.split("=", 1)
        try:
            params[key] = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            params[key] = value
    return params


def resolve_variant(name, params):
    """fn(df, teams, segments, dead, pitch) -> labels. Falls back to sticky when rules.py is missing."""
    try:
        import rules
    except ImportError as exc:
        if name != "closest_row8":
            raise SystemExit("rules.py is not importable yet ({}); only --variant closest_row8 "
                             "is available".format(exc))
        if params:
            raise SystemExit("closest_row8 without rules.py takes no --param")
        print("note: rules.py not importable ({}); closest_row8 runs sticky.sticky_labels directly"
              .format(exc))

        def fn(df, teams, segments, dead, pitch):
            return sticky.sticky_labels(df, teams, segments, "closest", dead=dead, pitch=pitch)
        return fn, "sticky.sticky_labels(closest)"
    if name not in rules.VARIANTS:
        raise SystemExit("unknown variant {!r}; rules.VARIANTS has: {}".format(
            name, ", ".join(sorted(rules.VARIANTS))))
    variant = rules.VARIANTS[name]

    def fn(df, teams, segments, dead, pitch):
        return variant(df, teams, segments, dead, pitch, **params)
    return fn, "rules.VARIANTS[{!r}]".format(name)


def install(fn, teams):
    """Point run_real.predict at our variant and at the cached team lists (no kloppy dataset)."""
    def sticky_labels(df, players_by_team, segments, rule="closest", dead=None, pitch=None):
        # `rule` is what predict passes for the old API; the variant decides for itself.
        return fn(df, players_by_team, segments, dead, pitch)

    run_real.sticky_labels = sticky_labels
    run_real.players_by_team = lambda ds: teams


# ---------------------------------------------------------------------------------------------
# diagnostics (aggregates only)
# ---------------------------------------------------------------------------------------------

def slot_jump_stats(df, teams, segments, pitch, fps):
    """How often tracked slots teleport. Counts and shares; nothing per frame leaves this function."""
    graded = np.zeros(len(df), dtype=bool)
    for a, b in segments:
        graded[a:b] = True
    pair = graded[1:] & graded[:-1]           # both frames inside a half

    def steps(ids):
        px = df[[i + "_x" for i in ids]].to_numpy(dtype=float) * pitch[0]
        py = df[[i + "_y" for i in ids]].to_numpy(dtype=float) * pitch[1]
        step = np.hypot(np.diff(px, axis=0), np.diff(py, axis=0))     # (N-1, slots)
        valid = ~np.isnan(step) & pair[:, None]
        return step, valid

    ids = sum(teams, [])
    step, valid = steps(ids)
    n_valid = int(valid.sum())
    jump = (step > JUMP_M) & valid
    fast = (step * fps > FAST_MS) & valid
    frames_any_jump = int(jump.any(axis=1).sum())
    frac_fast = fast.sum() / n_valid if n_valid else float("nan")
    seen = step[valid]
    pct = np.percentile(seen, [50, 99, 99.9]) if seen.size else [np.nan] * 3

    print("slot jump statistics (players, {} slots, fps {}, within halves):".format(len(ids), fps))
    print("  slot-frames with a slot seen on both frames : {}".format(n_valid))
    print("  frames where any slot moves > {:.0f} m      : {}  ({:.3%} of {} frame pairs)".format(
        JUMP_M, frames_any_jump, frames_any_jump / max(pair.sum(), 1), int(pair.sum())))
    print("  slot-frames with implied speed > {:.0f} m/s  : {}  ({:.4%} of slot-frames)".format(
        FAST_MS, int(fast.sum()), frac_fast))
    print("  per-frame step p50 / p99 / p99.9 / max (m)  : {:.3f} / {:.3f} / {:.3f} / {:.1f}".format(
        pct[0], pct[1], pct[2], float(seen.max()) if seen.size else float("nan")))
    per_slot = jump.sum(axis=0).tolist()
    print("  > {:.0f} m jumps per slot (home then away)   : {}".format(JUMP_M, per_slot))
    # Slots appearing or vanishing between consecutive frames: the other way identities get lost.
    present = ~np.isnan(df[[i + "_x" for i in ids]].to_numpy(dtype=float))
    flips = (present[1:] != present[:-1]) & pair[:, None]
    print("  slot appear/vanish events                   : {}".format(int(flips.sum())))

    bstep, bvalid = steps(["ball"])
    bn = int(bvalid.sum())
    bjump = int(((bstep > JUMP_M) & bvalid).sum())
    bfast = int(((bstep * fps > FAST_MS) & bvalid).sum())
    print("  ball: seen pairs {}, > {:.0f} m jumps {}, > {:.0f} m/s {} ({:.3%})".format(
        bn, JUMP_M, bjump, FAST_MS, bfast, bfast / bn if bn else float("nan")))
    return {"n_slot_frames": n_valid, "frames_any_jump_gt3m": frames_any_jump,
            "frac_slot_frames_gt12ms": float(frac_fast), "per_slot_jumps": per_slot,
            "ball_jumps_gt3m": bjump, "ball_frac_gt12ms": bfast / bn if bn else None}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_labels(path):
    import pandas as pd
    return pd.read_csv(path)["label"].astype(str).to_numpy()


def compare(out, ref_name):
    ref = os.path.join(RESULTS_DIR, ref_name + ".csv")
    print("sha256 {} : {}".format(os.path.relpath(out, ROOT), sha256(out)))
    if not os.path.isfile(ref):
        print("reference {} not found; skipping the label comparison".format(os.path.relpath(ref, ROOT)))
        return None
    print("sha256 {} : {}".format(os.path.relpath(ref, ROOT), sha256(ref)))
    a, b = read_labels(out), read_labels(ref)
    if len(a) != len(b):
        print("reference check: length {} vs {}: MISMATCH".format(len(a), len(b)))
        return -1
    n = int((a != b).sum())
    print("reference check against {}: {} mismatching frames of {} ({})".format(
        ref_name, n, len(a), "OK" if n == 0 else "MISMATCH"))
    return n


# ---------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--variant", required=True, help="key of rules.VARIANTS, e.g. closest_row8")
    parser.add_argument("--name", required=True, help="evaluation/results/<name>.csv")
    parser.add_argument("--param", action="append", default=[], metavar="k=v",
                        help="keyword argument for the variant (literal_eval'd); repeatable")
    parser.add_argument("--rebuild-cache", action="store_true", help="reload the tracking")
    parser.add_argument("--compare", default=None, metavar="NAME",
                        help="results file to compare labels with (default ours_row8 for closest_row8)")
    parser.add_argument("--no-eval", action="store_true", help="skip validator and run_evaluation")
    args = parser.parse_args()
    params = parse_params(args.param)
    if args.compare is None and args.variant == "closest_row8":
        args.compare = "ours_row8"

    fn, source = resolve_variant(args.variant, params)
    print("variant {} via {} params {}".format(args.variant, source, params or "{}"))

    df, teams, dt, how = load_cache(rebuild=args.rebuild_cache)
    print("frame {} in {:.1f} s".format(how, dt))

    segments = [(first, last + 1) for _, first, last in half_video_blocks(GAME)]
    pitch = GAMES[GAME]["pitch"]
    fps = GAMES[GAME].get("fps", 25)
    install(fn, teams)

    t0 = time.perf_counter()
    labels = run_real.predict(None, df, segments, pitch)
    print("labels computed in {:.1f} s".format(time.perf_counter() - t0))
    labels = np.asarray(labels).astype("<U1")
    if len(labels) != len(df):
        raise SystemExit("variant returned {} labels for {} frames".format(len(labels), len(df)))
    counts = {k: int((labels == k).sum()) for k in "HADX"}
    print("label counts {}".format(counts))

    out = os.path.join(RESULTS_DIR, args.name + ".csv")
    write_submission(out, labels)
    print("wrote", os.path.relpath(out, ROOT))

    run_real.ballpark(labels, segments)
    try:
        import checks
        checks.extra_ballpark(labels, segments)
    except ImportError as exc:
        print("checks.py not importable ({}); skipping extra_ballpark".format(exc))

    slot_jump_stats(df, teams, segments, pitch, fps)

    if args.compare:
        compare(out, args.compare)
    else:
        print("sha256 {} : {}".format(os.path.relpath(out, ROOT), sha256(out)))

    if args.no_eval:
        return
    for script in (["validate_submission.py", out], ["run_evaluation.py"]):
        subprocess.run([sys.executable, os.path.join(ROOT, "evaluation", script[0])] + script[1:],
                       check=False, cwd=ROOT)


if __name__ == "__main__":
    main()
