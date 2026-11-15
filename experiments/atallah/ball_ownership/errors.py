"""Where row 8 (or any variant) loses possessions on the practice match, by category.

    uv run --with numpy --with pandas --with kloppy --with scipy \
        python experiments/atallah/ball_ownership/errors.py \
        --variant closest_row8 --set clean|noisy|idsse --mode fixed|oracle [--iou 0.5] [--param k=v]

Prints aggregates only:
  1. a count table of the unmatched truth possessions by error category (see classify_spell),
  2. the switch-offset histogram (predicted H<->A switch minus the truth switch, frames),
  3. the first-touch histogram (truth switch frame minus the first frame a player of the new
     team is within FIRST_TOUCH_M of the ball),
  4. the truth spell-length counts,
  5. the sandwich table (predicted A B A spells by length, against the truth's).
Per-spell rows (start, stop, team, len_s, category, start_off, end_off) go to the gitignored
data/sample/cache/errors_<variant>_<set>_<mode>.csv. Nothing prints a frame of the data.

The set loads through harness.get_set (clean / noisy from cache.load_practice(); idsse when
idsse.py can be imported). Spell matching is the scorer's own greedy one-to-one rule, through
plot_possessions.greedy_pairs.
"""

import argparse
import csv
import os
from collections import Counter, OrderedDict

import numpy as np

import _paths
import possession_metrics as pm
from plot_possessions import greedy_pairs
from sticky import team_distances

import cache
import harness
import rules

try:  # idsse is optional: register it when the module is importable, load only on request
    import idsse
    harness.register_set("idsse", idsse.load)
except Exception:  # (missing module or data must not block the practice runs)
    idsse = None

FPS = pm.FPS
H, A, D = pm.H, pm.A, pm.D
TEAM_NAME = {H: "H", A: "A"}

MERGE_D_SHARE = 0.5         # over half the truth spell predicted D: merged by a missed stoppage
OTHER_SHARE = 0.5           # over half the truth spell carries the other team
WRONG_TEAM_TOL = 25         # a predicted switch this close to the truth start: wrong team, not missed
SHORT_FRAMES = 16           # a missed truth spell shorter than this is flagged "short"
OFFSET_TOL = 50             # transition matching tolerance for the offset histogram
OFFSET_BIN = 4
OFFSET_RANGE = 48           # bins from -48 to +48
FIRST_TOUCH_M = 1.0
FIRST_TOUCH_WINDOW = 25
LENGTH_CUTS = (8, 12, 20, 25)
SANDWICH_BINS = ((1, 4), (5, 8), (9, 15), (16, 25), (26, 50))

CATEGORIES = (
    "merged by missed stoppage",
    "flip-flop",
    "wrong team",
    "missed switch",
    "missed switch (short)",
    "late switch",
    "early switch",
    "late or early end",
    "other",
)


# --- spell geometry ----------------------------------------------------------------------------

def overlap(a, b, c, d):
    """Frames shared by [a, b) and [c, d)."""
    return max(0, min(b, d) - max(a, c))


def iou(a, b, c, d):
    inter = overlap(a, b, c, d)
    return inter / float(max(b, d) - min(a, c)) if inter else 0.0


def run_of(frame, runs):
    for k, (start, stop) in enumerate(runs):
        if start <= frame < stop:
            return k
    return -1


def covering_spells(spells, a, b):
    """Indices of spells overlapping [a, b), with the shared frame count, in time order."""
    return [(k, overlap(a, b, s, e)) for k, (s, e, _) in enumerate(spells) if overlap(a, b, s, e)]


# --- categorisation ---------------------------------------------------------------------------

def classify_spell(a, b, team, filled, pred_spells, gt_d_segments, pred_trans_in, iou_thr):
    """(category, start_off, end_off) for one unmatched truth possession [a, b) of `team`.

    Order matters: the first rule that fires wins.
      1 merged by missed stoppage: over MERGE_D_SHARE of the frames are predicted D, or the
        predicted spell covering most of the truth spell spans a whole truth D segment.
      2 flip-flop: two or more predicted possessions of alternating team sit mostly inside
        [a, b) and none reaches iou_thr with it.
      3 wrong team: over OTHER_SHARE of the frames carry the other team and a predicted switch
        into any team lies within WRONG_TEAM_TOL frames of a.
      4 missed switch: over OTHER_SHARE of the frames carry the other team, no such switch;
        "(short)" when b - a < SHORT_FRAMES.
      5 late switch / early switch / late or early end from the start and end offsets of the
        same-team predicted spell sharing most frames with [a, b); the larger offset decides.
    start_off = predicted start - a, end_off = predicted stop - b (frames), None without a
    same-team prediction.
    """
    window = filled[a:b]
    n = b - a
    other = A if team == H else H
    d_share = float(np.mean(window == D))
    other_share = float(np.mean(window == other))

    covering = covering_spells(pred_spells, a, b)
    best_any = max(covering, key=lambda item: (item[1], -item[0]))[0] if covering else None
    if d_share > MERGE_D_SHARE:
        return "merged by missed stoppage", None, None
    if best_any is not None:
        ps, pe, _ = pred_spells[best_any]
        if any(ps <= ds and de <= pe for ds, de in gt_d_segments):
            return "merged by missed stoppage", None, None

    inside = [k for k, shared in covering
              if shared * 2 >= (pred_spells[k][1] - pred_spells[k][0])]
    if len(inside) >= 2:
        codes = [pred_spells[k][2] for k in inside]
        alternating = any(x != y for x, y in zip(codes, codes[1:]))
        best_iou = max(iou(a, b, pred_spells[k][0], pred_spells[k][1]) for k in inside
                       if pred_spells[k][2] == team) if team in codes else 0.0
        if alternating and best_iou < iou_thr:
            return "flip-flop", None, None

    if other_share > OTHER_SHARE:
        lo, hi = a - WRONG_TEAM_TOL, a + WRONG_TEAM_TOL
        if np.any((pred_trans_in >= lo) & (pred_trans_in <= hi)):
            return "wrong team", None, None
        return ("missed switch (short)" if n < SHORT_FRAMES else "missed switch"), None, None

    same = [(k, shared) for k, shared in covering if pred_spells[k][2] == team]
    if not same:
        return "other", None, None
    k = max(same, key=lambda item: (item[1], -item[0]))[0]
    ps, pe, _ = pred_spells[k]
    start_off, end_off = ps - a, pe - b
    if abs(start_off) >= abs(end_off) and start_off != 0:
        return ("late switch" if start_off > 0 else "early switch"), start_off, end_off
    return "late or early end", start_off, end_off


def categorise(gt_spells, pred_spells, pairs, filled, gt_codes, runs, iou_thr):
    """[(start, stop, team, len_s, category, start_off, end_off)] for every truth spell.

    Matched spells (per greedy_pairs at iou_thr) get category "matched".
    """
    matched_gt = {gi for gi, _ in pairs}
    gt_d_segments = [(s, e) for s, e, k in pm.segments(gt_codes, runs) if k == D]
    pred_trans_in = np.array([f for f, _, to in pm.transitions(filled, runs) if to in (H, A)],
                             dtype=np.int64)
    rows = []
    for gi, (a, b, team) in enumerate(gt_spells):
        if gi in matched_gt:
            cat, so, eo = "matched", None, None
        else:
            cat, so, eo = classify_spell(a, b, team, filled, pred_spells, gt_d_segments,
                                         pred_trans_in, iou_thr)
        rows.append((a, b, TEAM_NAME[team], round((b - a) / float(FPS), 2), cat, so, eo))
    return rows


def category_table(rows):
    counts = Counter(r[4] for r in rows)
    n_gt = len(rows)
    n_unmatched = n_gt - counts.get("matched", 0)
    lines = ["category                     count  share of unmatched  share of truth  median len s"]
    for cat in CATEGORIES:
        c = counts.get(cat, 0)
        lens = [r[3] for r in rows if r[4] == cat]
        lines.append("{:<28} {:>5}  {:>18}  {:>14}  {:>12}".format(
            cat, c, "{:.1%}".format(c / float(n_unmatched)) if n_unmatched else "-",
            "{:.1%}".format(c / float(n_gt)) if n_gt else "-",
            "{:.2f}".format(float(np.median(lens))) if lens else "-"))
    lines.append("{:<28} {:>5}".format("unmatched total", n_unmatched))
    lines.append("{:<28} {:>5}".format("matched", counts.get("matched", 0)))
    lines.append("{:<28} {:>5}".format("truth possessions", n_gt))
    return "\n".join(lines), counts


# --- histograms -------------------------------------------------------------------------------

def ascii_hist(values, edges, label_fmt="{:>4} to {:<4}", width=40):
    """One bar per bin [edges[i], edges[i+1]); values outside the edges are counted separately."""
    values = np.asarray(values, dtype=np.float64)
    counts, _ = np.histogram(values, bins=edges)
    top = max(1, counts.max()) if len(counts) else 1
    lines = []
    for i, c in enumerate(counts):
        bar = "#" * int(round(width * c / float(top)))
        lines.append("{} {:>4} {}".format(label_fmt.format(int(edges[i]), int(edges[i + 1]) - 1),
                                           int(c), bar))
    below = int(np.sum(values < edges[0]))
    above = int(np.sum(values >= edges[-1]))
    lines.append("below {}: {}   at or above {}: {}".format(int(edges[0]), below, int(edges[-1]), above))
    return "\n".join(lines)


def percentiles(values):
    values = np.asarray(values, dtype=np.float64)
    if not len(values):
        return {"n": 0, "median": None, "p10": None, "p90": None}
    return {"n": int(len(values)), "median": float(np.median(values)),
            "p10": float(np.percentile(values, 10)), "p90": float(np.percentile(values, 90))}


def fmt_pct(p):
    if p["n"] == 0:
        return "n=0"
    return "n={}  median {:+.1f}  p10 {:+.1f}  p90 {:+.1f}".format(p["n"], p["median"], p["p10"], p["p90"])


def switch_offsets(gt_codes, filled, runs, tol=OFFSET_TOL):
    """(offsets, n_missed): predicted minus truth frame over matched H<->A transitions."""
    gt_sub = [t for t in pm.transitions(gt_codes, runs) if t[1] in (H, A) and t[2] in (H, A)]
    pred_sub = [t for t in pm.transitions(filled, runs) if t[1] in (H, A) and t[2] in (H, A)]
    res = pm.transition_scores(gt_sub, pred_sub, tol, typed="to")
    offsets = [pred[0] - gt[0] for gt, pred in res["pairs"]]
    return offsets, len(res["missed"]), len(gt_sub), len(pred_sub)


def first_touch_offsets(gt_codes, runs, df, teams, pitch, radius_m=FIRST_TOUCH_M,
                        window=FIRST_TOUCH_WINDOW):
    """(offsets, n_none): truth switch frame s minus the first frame in [s-window, s+window]
    where a player of the new team is within radius_m of the ball. Positive = touch before s."""
    d_home, d_away = team_distances(df, teams, pitch)
    near = {H: d_home <= radius_m, A: d_away <= radius_m}
    offsets, n_none = [], 0
    for s, frm, to in pm.transitions(gt_codes, runs):
        if frm not in (H, A) or to not in (H, A):
            continue
        k = run_of(s, runs)
        lo, hi = max(runs[k][0], s - window), min(runs[k][1], s + window + 1)
        hits = np.flatnonzero(near[to][lo:hi])
        if not len(hits):
            n_none += 1
            continue
        offsets.append(s - (lo + int(hits[0])))
    return offsets, n_none


def length_counts(gt_spells, cuts=LENGTH_CUTS):
    lengths = np.array([b - a for a, b, _ in gt_spells], dtype=np.int64)
    out = OrderedDict(("under {}".format(c), int(np.sum(lengths < c))) for c in cuts)
    out["total"] = int(len(lengths))
    return out


# --- sandwiches -------------------------------------------------------------------------------

def sandwiches(spells):
    """Indices k of spells whose frame-adjacent neighbours on both sides are the other team."""
    out = []
    for k in range(1, len(spells) - 1):
        ps, pe, pk = spells[k - 1]
        s, e, c = spells[k]
        ns, ne, nk = spells[k + 1]
        if pe == s and e == ns and pk != c and nk != c:
            out.append(k)
    return out


def sandwich_table(pred_spells, gt_spells, bins=SANDWICH_BINS):
    pred_sw = sandwiches(pred_spells)
    gt_sw = sandwiches(gt_spells)
    gt_by_team = {H: [(a, b) for a, b, k in gt_spells if k == H],
                  A: [(a, b) for a, b, k in gt_spells if k == A]}
    lines = ["length (frames)  predicted  share overlapping same-team truth  truth sandwiches"]
    table = []
    for lo, hi in bins:
        mine = [k for k in pred_sw if lo <= pred_spells[k][1] - pred_spells[k][0] <= hi]
        hit = 0
        for k in mine:
            s, e, c = pred_spells[k]
            if any(overlap(s, e, a, b) for a, b in gt_by_team[c]):
                hit += 1
        truth = sum(1 for k in gt_sw if lo <= gt_spells[k][1] - gt_spells[k][0] <= hi)
        share = "{:.0%}".format(hit / float(len(mine))) if mine else "-"
        lines.append("{:>2} to {:<3}         {:>6}  {:>33}  {:>16}".format(lo, hi, len(mine), share, truth))
        table.append((lo, hi, len(mine), hit, truth))
    lines.append("all lengths      {:>6}  {:>33}  {:>16}".format(len(pred_sw), "", len(gt_sw)))
    return "\n".join(lines), table


# --- driver -----------------------------------------------------------------------------------

def analyse(variant, set_name, mode, iou_thr=0.5, params=None, out_dir=None, quiet=False):
    """Run every diagnostic; print them; write the per-spell csv; return a dict of aggregates."""
    S = harness.get_set(set_name)
    labels = rules.VARIANTS[variant](S.df, S.teams, S.segments, S.dead[mode], S.pitch, **(params or {}))
    filled = pm.fill_abstentions(pm.label_codes(labels), S.runs)
    gt_spells = pm.possession_spells(S.gt_codes, S.runs)
    pred_spells = pm.possession_spells(filled, S.runs)
    overlaps = pm.spell_overlaps(gt_spells, pred_spells)
    pairs = greedy_pairs(overlaps, iou_thr)

    rows = categorise(gt_spells, pred_spells, pairs, filled, S.gt_codes, S.runs, iou_thr)
    cat_text, counts = category_table(rows)

    offsets, n_missed, n_gt_sw, n_pred_sw = switch_offsets(S.gt_codes, filled, S.runs)
    edges = np.arange(-OFFSET_RANGE, OFFSET_RANGE + OFFSET_BIN, OFFSET_BIN)
    off_pct = percentiles(offsets)

    ft_df = harness.get_set("clean").df if set_name in ("clean", "noisy") else S.df
    touches, n_no_touch = first_touch_offsets(S.gt_codes, S.runs, ft_df, S.teams, S.pitch)
    ft_pct = percentiles(touches)
    ft_edges = np.arange(-FIRST_TOUCH_WINDOW - 1, FIRST_TOUCH_WINDOW + 3, 2)

    lengths = length_counts(gt_spells)
    sw_text, sw_table = sandwich_table(pred_spells, gt_spells)

    out_dir = out_dir or cache.CACHE
    os.makedirs(out_dir, exist_ok=True)
    tag = "{}_{}_{}".format(variant, set_name, mode)
    csv_path = os.path.join(out_dir, "errors_{}.csv".format(tag))
    with open(csv_path, "w", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(("start", "stop", "team", "len_s", "category", "start_off", "end_off"))
        for r in rows:
            w.writerow(["" if v is None else v for v in r])

    if not quiet:
        print("== errors: variant {} set {} mode {} iou {}  ({} predicted vs {} truth possessions, "
              "{} matched) ==".format(variant, set_name, mode, iou_thr, len(pred_spells),
                                      len(gt_spells), len(pairs)))
        print("\n-- unmatched truth possessions by category --")
        print(cat_text)
        print("\n-- switch offset: predicted H<->A switch minus truth switch (frames, tol {}) --".format(OFFSET_TOL))
        print(ascii_hist(offsets, edges))
        print(fmt_pct(off_pct))
        print("truth H<->A switches {}  predicted {}  truth switches with no prediction within {} frames: {}".format(
            n_gt_sw, n_pred_sw, OFFSET_TOL, n_missed))
        print("\n-- first touch: truth switch frame minus first frame the new team is within {} m "
              "(window +/-{} frames, on the {} frame) --".format(
                  FIRST_TOUCH_M, FIRST_TOUCH_WINDOW, "clean" if set_name in ("clean", "noisy") else set_name))
        print(ascii_hist(touches, ft_edges))
        print(fmt_pct(ft_pct))
        print("switches with no touch in the window: {}".format(n_no_touch))
        print("\n-- truth spell lengths (frames) --")
        print("  ".join("{}: {}".format(k, v) for k, v in lengths.items()))
        print("\n-- sandwiches: predicted spells with the other team on both sides (frame-adjacent) --")
        print(sw_text)
        print("\nper-spell rows: {}".format(os.path.relpath(csv_path, _paths.ROOT)))

    return {"variant": variant, "set": set_name, "mode": mode, "iou": iou_thr,
            "n_pred": len(pred_spells), "n_gt": len(gt_spells), "n_matched": len(pairs),
            "categories": dict(counts), "offset": off_pct, "offset_missed": n_missed,
            "first_touch": ft_pct, "first_touch_none": n_no_touch, "lengths": dict(lengths),
            "sandwiches": sw_table, "csv": csv_path}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--variant", default="closest_row8", help="one of {}".format(sorted(rules.VARIANTS)))
    parser.add_argument("--set", default="clean", help="clean | noisy | <registered, e.g. idsse>")
    parser.add_argument("--mode", default="fixed", choices=("fixed", "oracle"))
    parser.add_argument("--iou", type=float, default=0.5, help="spell IoU for the match (default 0.5)")
    parser.add_argument("--param", action="append", default=[], metavar="k=v")
    args = parser.parse_args()
    if args.variant not in rules.VARIANTS:
        raise SystemExit("unknown variant {!r}; known: {}".format(args.variant, sorted(rules.VARIANTS)))
    if args.set not in harness.SETS:
        raise SystemExit("unknown set {!r}; known: {}".format(args.set, sorted(harness.SETS)))
    analyse(args.variant, args.set, args.mode, iou_thr=args.iou, params=harness.parse_params(args.param))


if __name__ == "__main__":
    main()
