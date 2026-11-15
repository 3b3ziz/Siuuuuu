"""Export practice-match replay clips for the scoreboard's Replay tab, as one JSON file.

    uv run --with numpy --with pandas --with kloppy --with scipy \
        python experiments/atallah/ball_ownership/replay_export.py [--out PATH] [--clip-seconds 30]

Practice match only (Metrica Sample Game 3, public data), noisy copy (ball hidden 41% of the
time), fixed stoppage mask. The real match never goes through here: its tracking is gated.

The page replays each clip on the stadium canvas of experiments/atallah/pitch_view.py and draws the
truth, row 8 and row 9 labels as strips under it, the way plot_possessions.py does. Clips are picked
deterministically from the scorer's own one-to-one matching at IoU 0.5:
  typical   truth possessions both rules match
  fixed     truth possessions row 8 missed and row 9 matches
  missed    truth possessions neither rule matches
  lost      truth possessions row 8 matched and row 9 misses
Within a kind, the candidates are truth possessions at least 12 frames long (shorter ones are the
floor the rules cannot reach); the clip around each is CLIP_S seconds centred on the possession,
kept inside its half, and the kind's clips are the ones whose window holds the most truth
switches, earliest first on ties, windows not overlapping.

Frames are exported every STEP source frames (12.5 a second), positions in metres to 10 cm. The
script prints counts only: never a position or a per-frame label.
"""

import argparse
import json
import os

import numpy as np

import _paths
import possession_metrics as pm
import cache
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
CLIP_S = 30.0
IOU = 0.5
MIN_SPELL = 12            # candidate truth possessions must be at least this long (frames)
PER_KIND = {"typical": 2, "fixed": 2, "missed": 2, "lost": 1}
KIND_TEXT = {
    "typical": "both rules match this possession",
    "fixed": "row 8 missed it, row 9 matches it",
    "missed": "neither rule matches it",
    "lost": "row 8 matched it, row 9 misses it",
}
DEFAULT_OUT = os.path.join(sample_game.SAMPLE, "views", "replay.json")
VARIANTS = {"r8": "closest_row8", "r9": "ball_ownership"}


def filled_labels(P, variant):
    """Scored codes (X forward-filled inside valid runs) of a variant on the noisy practice set."""
    fn = rules.VARIANTS[variant]
    raw = fn(P.df_noisy, P.teams, P.segments, P.dead["noisy"], P.pitch)
    return pm.fill_abstentions(pm.label_codes(raw), P.runs)


def matched_sets(gt_spells, pred_spells):
    """(matched gt indices, matched pred indices) at IOU, same greedy rule as the scorer."""
    pairs = greedy_pairs(pm.spell_overlaps(gt_spells, pred_spells), IOU)
    return {g for g, _ in pairs}, {p for _, p in pairs}


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
    live = np.isin(w, (0, 1))
    w = w[live]
    return int(np.count_nonzero(w[1:] != w[:-1])) if len(w) > 1 else 0


def segment_of(frame, segments):
    for start, stop in segments:
        if start <= frame < stop:
            return start, stop
    raise ValueError("frame outside every segment")


def pick_clips(gt_spells, kinds, gt_codes, segments, clip_frames):
    """[(kind, gt_index, start, end)] deterministic, windows not overlapping."""
    chosen = []

    def overlaps(a, b):
        return any(not (b <= s or e <= a) for _, _, s, e in chosen)

    for kind, want in PER_KIND.items():
        cands = []
        for gi, (a, b, _) in enumerate(gt_spells):
            if kinds[gi] != kind or b - a < MIN_SPELL:
                continue
            seg_a, seg_b = segment_of(a, segments)
            mid = (a + b) // 2
            start = max(seg_a, min(mid - clip_frames // 2, seg_b - clip_frames))
            end = min(seg_b, start + clip_frames)
            cands.append((-switches(gt_codes, start, end), a, gi, start, end))
        cands.sort()
        taken = 0
        for _, _, gi, start, end in cands:
            if taken >= want:
                break
            if overlaps(start, end):
                continue
            chosen.append((kind, gi, start, end))
            taken += 1
    chosen.sort(key=lambda c: c[2])
    return chosen


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
    m8g, m8p = matched_sets(gt_spells, spells["r8"])
    m9g, m9p = matched_sets(gt_spells, spells["r9"])
    kinds = [kind_of(gi, m8g, m9g) for gi in range(len(gt_spells))]
    scores = {k: pm.spell_scores(gt, c, runs)["mean_f1"] for k, c in pred.items()}

    counts = {k: kinds.count(k) for k in PER_KIND}
    print("truth possessions {}: {}".format(len(gt_spells), ", ".join(
        "{} {}".format(v, k) for k, v in counts.items())))
    print("noisy, fixed stoppages: row 8 spellF1 {:.4f} ({} spells), row 9 spellF1 {:.4f} ({} spells)".format(
        scores["r8"], len(spells["r8"]), scores["r9"], len(spells["r9"])))

    clips_meta = pick_clips(gt_spells, kinds, gt, P.segments, clip_frames)
    B, Pm, team_of, _ = F.arrays_from_df(P.df_noisy, P.teams, P.pitch)
    sides = [0 if t == "H" else 1 for t in team_of]

    def r1(v):
        return round(float(v), 1)

    clips = []
    for n, (kind, gi, start, end) in enumerate(clips_meta):
        a, b, k = gt_spells[gi]
        frames = []
        for f in range(start, end, STEP):
            ball = None if np.isnan(B[f]).any() else [r1(B[f, 0]), r1(B[f, 1])]
            players = [[j, r1(Pm[f, j, 0]), r1(Pm[f, j, 1])]
                       for j in range(Pm.shape[1]) if not np.isnan(Pm[f, j]).any()]
            frames.append({"f": int(f), "b": ball, "p": players})
        idx = np.arange(start, end, STEP)
        clips.append({
            "id": "clip-{}".format(n + 1),
            "kind": kind,
            "title": "{}: {} possession {} of {}, {:.1f} s ({})".format(
                kind, "home" if k == 0 else "away", gi + 1, len(gt_spells), (b - a) / FPS, KIND_TEXT[kind]),
            "start": int(start), "end": int(end), "focus": [int(a), int(b)],
            "labels": {"gt": gt[idx].tolist(), "r8": pred["r8"][idx].tolist(), "r9": pred["r9"][idx].tolist()},
            "frames": frames,
        })
        print("  {} {:>7} frames {}..{} ({:.0f} s) truth possession {} [{}..{}), {} truth switches in window, {} frames exported".format(
            clips[-1]["id"], kind, start, end, (end - start) / FPS, gi + 1, a, b, switches(gt, start, end), len(frames)))

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
