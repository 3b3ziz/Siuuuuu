"""Row 16 on the bench with a different minimum stoppage length (drop_short), one bench run per call.
    python experiments/ahmed/stop_min_sweep.py <hard 0/1> <seed>
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

MINS = tuple(float(v) for v in os.environ.get("MINS", "1,1.5,2,3,4").split(","))
hard, seed = bool(int(sys.argv[1])), int(sys.argv[2])
G = games(hard=hard, seed=seed)
P = pickle.load(open(os.path.join(CACHE, "ballmodel_p_{}_{}_{}.pkl".format("h" if hard else "n", seed, VERSION)), "rb"))
out = {}
for g, x in G.items():
    quiet = x.speed.copy()
    for r in x.rframes:
        quiet[r:r + QUIET_AFTER_RESTART] = False
    near = on_ball(x.df, x.teams, x.pitch)
    for m in MINS:
        dead = drop_short(x.ball_out | quiet | x.before, x.segments, int(m * 25)) | x.restart
        base = restart_team(sticky_labels(x.df, x.teams, x.segments, "closest", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
        live = np.isin(base, ["H", "A"])
        touch = restart_team(sticky_labels(x.df, x.teams, x.segments, "touch", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
        lab = merge_short(restart_team(viterbi(lock_clear(blend_touch(P[g], touch), near), live), x.rframes, x.tag_teams))
        out[(g, m)] = spell_f1(x.gt, lab)
    print(g, " ".join("{}:{:.4f}".format(m, out[(g, m)]) for m in MINS), flush=True)
pickle.dump(out, open(os.path.join(os.environ.get("OUT", "."), "stopmin_{}_{}_{}.pkl".format(int(hard), seed, os.environ.get("MINS", "a"))), "wb"))
