"""Export practice-match replay clips for the scoreboard's Replay tab, as one JSON file.

    uv run --with numpy --with pandas --with kloppy --with scipy \
        python experiments/atallah/ball_ownership/replay_export.py [--out PATH] [--clip-seconds 20]

Practice match only (Metrica Sample Game 3, public data), noisy copy (ball hidden 41% of the
time), fixed stoppage mask. The real match never goes through here: its tracking is gated.

The page replays each clip on the stadium canvas of experiments/atallah/pitch_view.py and draws the
truth, row 8 and row 9 labels as strips under it, the way plot_possessions.py does. Clips are named
by football situation, in two groups, and picked deterministically:

  Typical moments (row 9 matches the possession, scorer's one-to-one matching at IoU 0.5)
    Throw-in, Goal kick or corner    a restart after the ball left the pitch (clean ball track)
    Free kick                        a restart after play stopped with the ball on the pitch
    Fast live play                   the window with the most truth switches, all matched
    Row 9 fixes a switch             row 8 missed the possession, row 9 matches it
  Possessions we miss (row 9 does not match it), named by errors.classify_spell
    Short possession                 missed switch, truth possession under SHORT_FRAMES
    Wrong start or end               late or early switch, late or early end
    False stoppage                   merged by a stoppage of ours the truth does not have
    Missed switch                    the other team carried most of the possession
    Wrong team or flip-flop          a switch into the wrong team, or alternating guesses
    False turnover                   a row 9 possession the truth never had, inside an opponent's
    Row 9 lost it                    row 8 matched the possession, row 9 misses it

Within a name the candidates are ranked by truth switches in the window (most first, earliest on
ties); windows never overlap and never cross the half-time hole. Frames are exported every STEP
source frames (12.5 a second), positions in metres to 10 cm. The script prints counts only: never a
position or a per-frame label.
"""

import argparse
import json
import os

import numpy as np

import _paths
import possession_metrics as pm
import cache
import errors
import rules
import features as F
import sample_game
from plot_possessions import greedy_pairs

try:                      # the rule registers itself in rules.VARIANTS when importable
    import ball_rule
    ball_rule.register()
except ImportError:       # pragma: no cover
    pass

FPS = 25
STEP = 2                  # exported frame rate = FPS / STEP
CLIP_S = 20.0
IOU = 0.5
MIN_SPELL = 12            # a possession shorter than this is the floor the rules cannot reach
STOP_FRAMES = 50          # a truth stoppage at least this long with the ball on the pitch: free kick
DEFAULT_OUT = os.path.join(sample_game.SAMPLE, "views", "replay.json")
VARIANTS = {"r8": "closest_row8", "r9": "ball_ownership"}
H, A, D = pm.H, pm.A, pm.D

# (group, name, how many) in page order. The kind gives the chip its outcome colour.
PLAN = (
    ("typical", "Throw-in", 1),
    ("typical", "Goal kick or corner", 1),
    ("typical", "Free kick", 1),
    ("typical", "Fast live play", 1),
    ("typical", "Row 9 fixes a switch", 1),
    ("miss", "Short possession", 2),
    ("miss", "Wrong start or end", 2),
    ("miss", "False stoppage", 2),
    ("miss", "Missed switch", 1),
    ("miss", "Wrong team or flip-flop", 1),
    ("miss", "False turnover", 1),
    ("miss", "Row 9 lost it", 1),
)
CATEGORY_NAME = {
    "missed switch (short)": "Short possession",
    "late switch": "Wrong start or end",
    "early switch": "Wrong start or end",
    "late or early end": "Wrong start or end",
    "merged by missed stoppage": "False stoppage",
    "missed switch": "Missed switch",
    "wrong team": "Wrong team or flip-flop",
    "flip-flop": "Wrong team or flip-flop",
}
WHY = {
    "Throw-in": "row 9 picks up the restart after the ball went out over the touchline",
    "Goal kick or corner": "row 9 picks up the restart after the ball went out over the goal line",
    "Free kick": "row 9 picks up the restart after play stopped with the ball on the pitch",
    "Fast live play": "every possession in the window matched by row 9",
    "Row 9 fixes a switch": "row 8 missed this possession, row 9 matches it",
    "Short possession": "too short for the hold of eight frames, so the switch is never confirmed",
    "Wrong start or end": "row 9 has the possession but starts or ends it too far from the truth",
    "False stoppage": "our stoppage mask calls play dead while the truth keeps it live",
    "Missed switch": "the other team carried most of this possession in row 9",
    "Wrong team or flip-flop": "row 9 switched into the wrong team, or alternated, inside it",
    "False turnover": "row 9 invents a possession the truth never had",
    "Row 9 lost it": "row 8 matched this possession, row 9 misses it",
}


def filled_labels(P, variant):
    """Scored codes (X forward-filled inside valid runs) of a variant on the noisy practice set."""
    fn = rules.VARIANTS[variant]
    raw = fn(P.df_noisy, P.teams, P.segments, P.dead["noisy"], P.pitch)
    return pm.fill_abstentions(pm.label_codes(raw), P.runs)


def matched_pairs(gt_spells, pred_spells):
    """[(gt_index, pred_index)] at IOU, same greedy rule as the scorer."""
    return greedy_pairs(pm.spell_overlaps(gt_spells, pred_spells), IOU)


def kind_of(gi, m8, m9):
    in8, in9 = gi in m8, gi in m9
    if in8 and in9:
        return "typical"
    if in9:
        return "fixed"
    if in8:
        return "lost"
    return "missed"


def switches(codes, a, b):
    """H<->A changes of the truth inside [a, b)."""
    w = codes[a:b]
    w = w[np.isin(w, (H, A))]
    return int(np.count_nonzero(w[1:] != w[:-1])) if len(w) > 1 else 0


def segment_of(frame, segments):
    for start, stop in segments:
        if start <= frame < stop:
            return start, stop
    raise ValueError("frame outside every segment")


def window_for(centre, segments, clip_frames):
    """[start, end) of clip_frames around centre, kept inside centre's half."""
    seg_a, seg_b = segment_of(centre, segments)
    start = max(seg_a, min(centre - clip_frames // 2, seg_b - clip_frames))
    return start, min(seg_b, start + clip_frames)


def stoppage_kind(bx, by, s, e):
    """Name of a truth stoppage [s, e) from the clean ball track, or None."""
    x, y = bx[s:e], by[s:e]
    seen = ~(np.isnan(x) | np.isnan(y))
    with np.errstate(invalid="ignore"):
        side = seen & ((y < 0) | (y > 1))
        goal = seen & ((x < 0) | (x > 1))
    if side.any():
        return "Throw-in"
    if goal.any():
        return "Goal kick or corner"
    if e - s >= STOP_FRAMES:
        return "Free kick"
    return None


def choose(cands, want, chosen):
    """Take up to `want` of cands [(score, centre, payload)], best score first, earliest on ties,
    whose windows do not overlap any in `chosen` [(start, end, ...)]. Appends to chosen."""
    taken = []
    for _, _, start, end, payload in sorted(cands, key=lambda c: (-c[0], c[1])):
        if len(taken) >= want:
            break
        if any(not (end <= s or e <= start) for s, e, _ in chosen):
            continue
        chosen.append((start, end, payload))
        taken.append((start, end, payload))
    return taken


def plan_clips(gt_spells, kinds, cats, gt, segments, clip_frames, d_segments, ball_xy, spurious9):
    """[(start, end, payload)] in page order of PLAN; payload = dict(group, name, kind, focus, gi)."""
    bx, by = ball_xy
    first_after = {a: gi for gi, (a, b, k) in enumerate(gt_spells)}
    matched9 = {gi for gi, k in enumerate(kinds) if k in ("typical", "fixed")}

    def cand(gi, centre, group, name, kind=None):
        a, b, k = gt_spells[gi]
        start, end = window_for(centre, segments, clip_frames)
        payload = {"group": group, "name": name, "kind": kind or kinds[gi], "gi": gi, "focus": [a, b], "team": k}
        return (switches(gt, start, end), start, start, end, payload)

    pools = {name: [] for _, name, _ in PLAN}
    for s, e in d_segments:                       # restarts after a named stoppage
        name = stoppage_kind(bx, by, s, e)
        gi = first_after.get(e)
        if name and gi is not None and gi in matched9:
            pools[name].append(cand(gi, e, "typical", name))
    for gi, (a, b, k) in enumerate(gt_spells):
        if b - a < MIN_SPELL:
            if cats[gi] == "missed switch (short)":
                pools["Short possession"].append(cand(gi, (a + b) // 2, "miss", "Short possession"))
            continue
        mid = (a + b) // 2
        if kinds[gi] == "fixed":
            pools["Row 9 fixes a switch"].append(cand(gi, mid, "typical", "Row 9 fixes a switch"))
        elif kinds[gi] == "lost":
            pools["Row 9 lost it"].append(cand(gi, mid, "miss", "Row 9 lost it"))
        elif kinds[gi] == "missed" and cats[gi] in CATEGORY_NAME:
            pools[CATEGORY_NAME[cats[gi]]].append(cand(gi, mid, "miss", CATEGORY_NAME[cats[gi]]))
        if gi in matched9:
            start, end = window_for(mid, segments, clip_frames)
            inside = [j for j, (x, y, _) in enumerate(gt_spells) if x < end and y > start]
            if all(j in matched9 for j in inside):
                pools["Fast live play"].append(cand(gi, mid, "typical", "Fast live play"))
    for ps, pe, pk in spurious9:                  # a row 9 possession inside an opponent's truth one
        if pe - ps < MIN_SPELL:
            continue
        for gi, (a, b, k) in enumerate(gt_spells):
            if a <= ps and pe <= b and k != pk:
                c = cand(gi, (ps + pe) // 2, "miss", "False turnover", kind="missed")
                c[4]["focus"] = [ps, pe]
                pools["False turnover"].append(c)
                break

    chosen = []
    for group, name, want in PLAN:
        choose(pools[name], want, chosen)
    order = {name: i for i, (_, name, _) in enumerate(PLAN)}
    chosen.sort(key=lambda c: (order[c[2]["name"]], c[0]))
    return chosen, {name: len(pools[name]) for name in pools}


def strip(codes, runs):
    return [[a, b, k] for a, b, k in pm.segments(codes, runs)]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--clip-seconds", type=float, default=CLIP_S)
    args = parser.parse_args()
    clip_frames = int(round(args.clip_seconds * FPS))

    P = cache.load_practice()
    gt, runs = P.gt_codes, P.runs
    pred = {k: filled_labels(P, v) for k, v in VARIANTS.items()}
    gt_spells = pm.possession_spells(gt, runs)
    spells = {k: pm.possession_spells(c, runs) for k, c in pred.items()}
    pairs = {k: matched_pairs(gt_spells, spells[k]) for k in spells}
    m8g = {g for g, _ in pairs["r8"]}
    m9g = {g for g, _ in pairs["r9"]}
    m8p = {p for _, p in pairs["r8"]}
    m9p = {p for _, p in pairs["r9"]}
    kinds = [kind_of(gi, m8g, m9g) for gi in range(len(gt_spells))]
    cats = [row[4] for row in errors.categorise(gt_spells, spells["r9"], pairs["r9"], pred["r9"], gt, runs, IOU)]
    scores = {k: pm.spell_scores(gt, c, runs)["mean_f1"] for k, c in pred.items()}
    d_segments = [(s, e) for s, e, k in pm.segments(gt, runs) if k == D]
    spurious9 = [sp for i, sp in enumerate(spells["r9"]) if i not in m9p]
    ball_xy = (P.df_clean["ball_x"].to_numpy(dtype=float), P.df_clean["ball_y"].to_numpy(dtype=float))

    counts = {k: kinds.count(k) for k in ("typical", "fixed", "missed", "lost")}
    print("truth possessions {}: {}".format(len(gt_spells), ", ".join("{} {}".format(v, k) for k, v in counts.items())))
    print("row 9 misses by category: " + ", ".join(
        "{} {}".format(sum(1 for c in cats if c == name), name) for name in errors.CATEGORIES if name in cats))
    print("noisy, fixed stoppages: row 8 spellF1 {:.4f} ({} spells), row 9 spellF1 {:.4f} ({} spells)".format(
        scores["r8"], len(spells["r8"]), scores["r9"], len(spells["r9"])))

    chosen, pool_sizes = plan_clips(gt_spells, kinds, cats, gt, P.segments, clip_frames, d_segments, ball_xy, spurious9)
    print("candidates per name: " + ", ".join("{} {}".format(v, k) for k, v in pool_sizes.items()))
    B, Pm, team_of, _ = F.arrays_from_df(P.df_noisy, P.teams, P.pitch)
    sides = [0 if t == "H" else 1 for t in team_of]

    def r1(v):
        return round(float(v), 1)

    clips = []
    for n, (start, end, pl) in enumerate(chosen):
        a, b, k = gt_spells[pl["gi"]]
        frames = []
        for f in range(start, end, STEP):
            ball = None if np.isnan(B[f]).any() else [r1(B[f, 0]), r1(B[f, 1])]
            players = [[j, r1(Pm[f, j, 0]), r1(Pm[f, j, 1])]
                       for j in range(Pm.shape[1]) if not np.isnan(Pm[f, j]).any()]
            frames.append({"f": int(f), "b": ball, "p": players})
        idx = np.arange(start, end, STEP)
        who = "home" if k == H else "away"
        clips.append({
            "id": "clip-{}".format(n + 1),
            "group": pl["group"], "name": pl["name"], "kind": pl["kind"],
            "why": "{} possession {} of {}, {:.1f} s: {}".format(who, pl["gi"] + 1, len(gt_spells), (b - a) / FPS, WHY[pl["name"]]),
            "title": "{} ({} possession {} of {}, {:.1f} s)".format(pl["name"], who, pl["gi"] + 1, len(gt_spells), (b - a) / FPS),
            "start": int(start), "end": int(end), "focus": [int(pl["focus"][0]), int(pl["focus"][1])],
            "labels": {"gt": gt[idx].tolist(), "r8": pred["r8"][idx].tolist(), "r9": pred["r9"][idx].tolist()},
            "frames": frames,
        })
        print("  {:<8} {:<8} {:<24} frames {}..{} truth possession {} [{}..{}) {} switches in window".format(
            clips[-1]["id"], pl["group"], pl["name"], start, end, pl["gi"] + 1, a, b, switches(gt, start, end)))

    payload = {
        "source": "Metrica Sample Game 3 (public), noisy copy, fixed stoppage mask",
        "fps": FPS, "step": STEP, "pitch": list(P.pitch), "n_frames": int(len(gt)),
        "sides": sides,
        "scores": {"r8": round(scores["r8"], 4), "r9": round(scores["r9"], 4)},
        "counts": {"gt": len(gt_spells), "r8": len(spells["r8"]), "r9": len(spells["r9"]), "kinds": counts},
        "strips": {
            "runs": [[int(a), int(b)] for a, b in runs],
            "gt": strip(gt, runs), "r8": strip(pred["r8"], runs), "r9": strip(pred["r9"], runs),
            "gt_spells": [[a, b, k, kinds[i]] for i, (a, b, k) in enumerate(gt_spells)],
            "r8_spells": [[a, b, k, int(i in m8p)] for i, (a, b, k) in enumerate(spells["r8"])],
            "r9_spells": [[a, b, k, int(i in m9p)] for i, (a, b, k) in enumerate(spells["r9"])],
        },
        "clips": clips,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"))
    print("wrote {} ({:.0f} KB, {} clips, {} strip segments)".format(
        args.out, os.path.getsize(args.out) / 1024, len(clips),
        sum(len(payload["strips"][k]) for k in ("gt", "r8", "r9"))))


if __name__ == "__main__":
    main()
