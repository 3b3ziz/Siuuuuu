"""On top of row 18: re-drop short stoppages after the kick trim (redrop), and fill live gaps under N s between two stoppages (fillN).
    python experiments/ahmed/row19_fill.py <hard 0/1> <seed>
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

hard, seed = bool(int(sys.argv[1])), int(sys.argv[2])
G = games(hard=hard, seed=seed)
P = pickle.load(open(os.path.join(CACHE, "ballmodel_p_{}_{}_{}.pkl".format("h" if hard else "n", seed, VERSION)), "rb"))
out = {}
V = ("r18", "redrop", "fill1", "fill2", "fill3")
for g, x in G.items():
    quiet = x.speed.copy()
    for r in x.rframes:
        quiet[r:r + QUIET_AFTER_RESTART] = False
    v = ball_speed(x.df, x.pitch)
    raw = x.ball_out | quiet | x.before | still_then_kick(v, x.segments, 2 * FPS)
    kicks = kick_frames(v)

    rule = kick_ends(drop_short(raw, x.segments, 150), x.segments, kicks, 3 * FPS, 10 * FPS)

    def fill(dead, n):
        out = dead.copy()
        for a, b in x.segments:
            for s0, e0 in runs(~dead[a:b]):
                if s0 > 0 and a + e0 < b and e0 - s0 < n:
                    out[a + s0:a + e0] = True
        return out
    deads = {"r18": rule | x.restart, "redrop": drop_short(rule, x.segments, 150) | x.restart,
             "fill1": fill(rule | x.restart, FPS), "fill2": fill(rule | x.restart, 2 * FPS),
             "fill3": fill(rule | x.restart, 3 * FPS)}
    near = on_ball(x.df, x.teams, x.pitch)
    for k, dead in deads.items():
        base = restart_team(sticky_labels(x.df, x.teams, x.segments, "closest", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
        touch = restart_team(sticky_labels(x.df, x.teams, x.segments, "touch", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
        lab = restart_team(viterbi(lock_clear(blend_touch(P[g], touch), near), np.isin(base, ["H", "A"])), x.rframes, x.tag_teams)
        out[(g, k)] = spell_f1(x.gt, merge_short(lab, 0.8))
    print(g, " ".join("{}:{:.4f}".format(k, out[(g, k)]) for k in V), flush=True)
pickle.dump(out, open(os.path.join(os.environ.get("OUT", "."), "fill_{}_{}.pkl".format(int(hard), seed)), "wb"))
