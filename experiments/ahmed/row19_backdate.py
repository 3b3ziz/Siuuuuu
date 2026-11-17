"""On top of row 18: move stoppage starts earlier or later (players react to the whistle late).
  allN:   every rule-made stoppage starts N s earlier
  speedN: only stoppages that start with the slowdown rule (not ball out) start N s earlier
    python experiments/ahmed/row19_backdate.py <hard 0/1> <seed>
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
from idea_restart_kick import FPS, ball_speed, kick_ends, kick_frames, still_then_kick  # noqa: E402
from stop_fixes import drop_short  # noqa: E402
from sticky import runs, sticky_labels  # noqa: E402
from tags import QUIET_AFTER_RESTART, restart_team  # noqa: E402
from team_fixes import merge_short, on_ball  # noqa: E402


def backdate(dead, segments, n, only=None):
    out = dead.copy()
    for a, b in segments:
        for s, e in runs(dead[a:b]):
            s = a + s
            if only is not None and not only[s]:
                continue
            out[max(a, s - n):s] = True
    return out


def delay(dead, segments, n):
    """Each stoppage starts n frames later (kept at least 1 s long)."""
    out = dead.copy()
    for a, b in segments:
        for s, e in runs(dead[a:b]):
            s, e = a + s, a + e
            out[s:min(s + n, e - FPS)] = False
    return out


hard, seed = bool(int(sys.argv[1])), int(sys.argv[2])
G = games(hard=hard, seed=seed)
P = pickle.load(open(os.path.join(CACHE, "ballmodel_p_{}_{}_{}.pkl".format("h" if hard else "n", seed, VERSION)), "rb"))
out = {}
V = ("r18", "late05", "late1", "late2") if os.environ.get("LATE") else ("r18", "all1", "all2", "all3", "speed1", "speed2", "speed4")
for g, x in G.items():
    quiet = x.speed.copy()
    for r in x.rframes:
        quiet[r:r + QUIET_AFTER_RESTART] = False
    v = ball_speed(x.df, x.pitch)
    raw = x.ball_out | quiet | x.before | still_then_kick(v, x.segments, 2 * FPS)
    rule = kick_ends(drop_short(raw, x.segments, 150), x.segments, kick_frames(v), 3 * FPS, 10 * FPS)
    sp = quiet & ~x.ball_out
    deads = {"r18": rule | x.restart}
    if os.environ.get("LATE"):
        for k, n in (("late05", 12), ("late1", FPS), ("late2", 2 * FPS)):
            deads[k] = delay(rule, x.segments, n) | x.restart
    for n in () if os.environ.get("LATE") else (1, 2, 3):
        deads["all{}".format(n)] = backdate(rule, x.segments, n * FPS) | x.restart
    for n in () if os.environ.get("LATE") else (1, 2, 4):
        deads["speed{}".format(n)] = backdate(rule, x.segments, n * FPS, only=sp) | x.restart
    near = on_ball(x.df, x.teams, x.pitch)
    for k, dead in deads.items():
        base = restart_team(sticky_labels(x.df, x.teams, x.segments, "closest", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
        touch = restart_team(sticky_labels(x.df, x.teams, x.segments, "touch", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
        lab = restart_team(viterbi(lock_clear(blend_touch(P[g], touch), near), np.isin(base, ["H", "A"])), x.rframes, x.tag_teams)
        out[(g, k)] = spell_f1(x.gt, merge_short(lab, 0.8))
    print(g, " ".join("{}:{:.4f}".format(k, out[(g, k)]) for k in V), flush=True)
pickle.dump(out, open(os.path.join(os.environ.get("OUT", "."), "{}_{}_{}.pkl".format("late" if os.environ.get("LATE") else "back", int(hard), seed)), "wb"))
