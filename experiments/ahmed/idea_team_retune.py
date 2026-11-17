"""Re-tune the team settings one at a time on top of row 17 (6 s minimum stoppage), one bench run per call.
    python experiments/ahmed/idea_team_retune.py <hard 0/1> <seed>
Settings: (switch cost, touch weight, lock frames, min possession s). Row 17 = (7, 1.0, 50, 1.0).
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
from sticky import sticky_labels  # noqa: E402
from tags import QUIET_AFTER_RESTART, restart_team  # noqa: E402
from team_fixes import merge_short, on_ball  # noqa: E402

ROW17 = (7.0, 1.0, 50, 1.0)
CONFIGS = {"row17": ROW17}
for v in (5.0, 10.0, 14.0):
    CONFIGS["switch={}".format(v)] = (v, 1.0, 50, 1.0)
for v in (0.5, 1.5):
    CONFIGS["touch={}".format(v)] = (7.0, v, 50, 1.0)
for v in (25, 100):
    CONFIGS["lock={}".format(v)] = (7.0, 1.0, v, 1.0)
for v in (0.4, 0.6, 0.8, 1.5):
    CONFIGS["minposs={}".format(v)] = (7.0, 1.0, 50, v)

hard, seed = bool(int(sys.argv[1])), int(sys.argv[2])
G = games(hard=hard, seed=seed)
P = pickle.load(open(os.path.join(CACHE, "ballmodel_p_{}_{}_{}.pkl".format("h" if hard else "n", seed, VERSION)), "rb"))
out = {}
for g, x in G.items():
    quiet = x.speed.copy()
    for r in x.rframes:
        quiet[r:r + QUIET_AFTER_RESTART] = False
    near = on_ball(x.df, x.teams, x.pitch)
    dead = drop_short(x.ball_out | quiet | x.before, x.segments, 150) | x.restart
    base = restart_team(sticky_labels(x.df, x.teams, x.segments, "closest", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
    live = np.isin(base, ["H", "A"])
    touch = restart_team(sticky_labels(x.df, x.teams, x.segments, "touch", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
    for name, (sw, tw, lf, mp) in CONFIGS.items():
        lab = merge_short(restart_team(viterbi(lock_clear(blend_touch(P[g], touch, tw), near, lf), live, sw), x.rframes, x.tag_teams), mp)
        out[(g, name)] = spell_f1(x.gt, lab)
    print(g, " ".join("{}:{:.4f}".format(n, out[(g, n)]) for n in CONFIGS), flush=True)
pickle.dump(out, open(os.path.join(os.environ.get("OUT", "."), "retune_{}_{}.pkl".format(int(hard), seed)), "wb"))
