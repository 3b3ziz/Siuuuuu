"""Idea: stoppages end at the restart kick (still/unseen ball suddenly struck fast). One bench run per call.
    python experiments/ahmed/idea_restart_kick.py <hard 0/1> <seed>
Variants (all on top of row 17 = drop_short(..., 150)):
  r17    row 17 as is
  snap   move each dead stretch's end to the first kick in [end-3 s, end+10 s]
  ext    only extend: if a kick is in [end, end+10 s], stay dead until it
  still  ball still (<0.5 m/s) for 2 s+ then kicked: dead until the kick (added before drop_short)
  both   still, then snap
"""
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(ROOT, "prep"), HERE]
from ball_model import CACHE, VERSION, blend_touch, lock_clear, viterbi  # noqa: E402
from fastbench import games, spell_f1  # noqa: E402
from stop_fixes import drop_short  # noqa: E402
from sticky import runs, sticky_labels  # noqa: E402
from tags import QUIET_AFTER_RESTART, restart_team  # noqa: E402
from team_fixes import merge_short, on_ball  # noqa: E402

FPS, LAG = 25, 5  # speed over 0.2 s


def ball_speed(df, pitch):
    """m/s over the next LAG frames, NaN if either end hidden."""
    x = df["ball_x"].to_numpy() * pitch[0]
    y = df["ball_y"].to_numpy() * pitch[1]
    v = np.full(len(x), np.nan)
    v[:-LAG] = np.hypot(x[LAG:] - x[:-LAG], y[LAG:] - y[:-LAG]) * FPS / LAG
    return v


def kick_frames(v, fast=4.0, slow=1.0, pre=FPS):
    """Frames where the ball goes fast after a second of being slow or unseen."""
    with np.errstate(invalid="ignore"):
        isfast = v > fast
        notslow = v > slow  # NaN (unseen) counts as slow
    cs = np.concatenate([[0], np.cumsum(notslow)])
    t = np.flatnonzero(isfast)
    t = t[t >= pre]
    ok = (cs[t] - cs[t - pre]) == 0
    return t[ok]


def kick_ends(dead, segments, kicks, lo, hi, shrink=True):
    dead = dead.copy()
    for a, b in segments:
        for s, e in runs(dead[a:b]):
            s, e = a + s, a + e
            w0 = max(s + FPS, e - lo) if shrink else e
            i = np.searchsorted(kicks, w0)
            if i < len(kicks) and kicks[i] <= min(e + hi, b - 1):
                k = kicks[i]
                if k < e:
                    dead[k:e] = False
                else:
                    dead[e:k] = True
    return dead


def still_then_kick(v, segments, n, still=0.5, gap=FPS):
    """Ball seen still for n+ frames, then a kick within `gap` frames after: dead from still start to kick."""
    with np.errstate(invalid="ignore"):
        st = v < still
        fast = v > 4.0
    out = np.zeros(len(v), dtype=bool)
    for a, b in segments:
        for s, e in runs(st[a:b]):
            s, e = a + s, a + e
            if e - s < n:
                continue
            f = np.flatnonzero(fast[e:min(e + gap, b)])
            if len(f):
                out[s:e + f[0]] = True
    return out


if __name__ == "__main__":
    hard, seed = bool(int(sys.argv[1])), int(sys.argv[2])
    G = games(hard=hard, seed=seed)
    P = pickle.load(open(os.path.join(CACHE, "ballmodel_p_{}_{}_{}.pkl".format("h" if hard else "n", seed, VERSION)), "rb"))
    out = {}
    V = ["r17", "snap", "ext", "still", "both"]
    for g, x in G.items():
        quiet = x.speed.copy()
        for r in x.rframes:
            quiet[r:r + QUIET_AFTER_RESTART] = False
        near = on_ball(x.df, x.teams, x.pitch)
        v = ball_speed(x.df, x.pitch)
        kicks = kick_frames(v)
        raw = x.ball_out | quiet | x.before
        r17 = drop_short(raw, x.segments, 150)
        st = drop_short(raw | still_then_kick(v, x.segments, 2 * FPS), x.segments, 150)
        masks = {
            "r17": r17 | x.restart,
            "snap": kick_ends(r17, x.segments, kicks, 3 * FPS, 10 * FPS) | x.restart,
            "ext": kick_ends(r17, x.segments, kicks, 0, 10 * FPS, shrink=False) | x.restart,
            "still": st | x.restart,
            "both": kick_ends(st, x.segments, kicks, 3 * FPS, 10 * FPS) | x.restart,
        }
        for m in V:
            dead = masks[m]
            base = restart_team(sticky_labels(x.df, x.teams, x.segments, "closest", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
            live = np.isin(base, ["H", "A"])
            touch = restart_team(sticky_labels(x.df, x.teams, x.segments, "touch", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
            lab = merge_short(restart_team(viterbi(lock_clear(blend_touch(P[g], touch), near), live), x.rframes, x.tag_teams))
            out[(g, m)] = spell_f1(x.gt, lab)
        print(g, len(kicks), {m: int((masks[m] != masks["r17"]).sum()) for m in V[1:]},
              " ".join("{}:{:.4f}".format(m, out[(g, m)]) for m in V), flush=True)
    pickle.dump(out, open(os.path.join(os.environ.get("OUT", "."), "kick_{}_{}.pkl".format(int(hard), seed)), "wb"))
