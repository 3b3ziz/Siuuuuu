"""Row 17 (6 s minimum stoppage) on the bench, varying the slowdown threshold and the quiet time after restarts.
    python experiments/ahmed/stop_speed_sweep.py <hard 0/1> <seed>
"""
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(ROOT, "prep"), HERE]
import stoppage  # noqa: E402
from ball_model import CACHE, VERSION, blend_touch, lock_clear, viterbi  # noqa: E402
from fastbench import games, spell_f1  # noqa: E402
from stop_fixes import drop_short  # noqa: E402
from sticky import sticky_labels  # noqa: E402
from tags import restart_team  # noqa: E402
from team_fixes import merge_short, on_ball  # noqa: E402

VARIANTS = [(1.25, 250), (1.0, 250), (1.5, 250), (1.25, 125), (1.25, 500)]
hard, seed = bool(int(sys.argv[1])), int(sys.argv[2])
G = games(hard=hard, seed=seed)
P = pickle.load(open(os.path.join(CACHE, "ballmodel_p_{}_{}_{}.pkl".format("h" if hard else "n", seed, VERSION)), "rb"))
out = {}
for g, x in G.items():
    near = on_ball(x.df, x.teams, x.pitch)
    speeds = {}
    for sp, q in VARIANTS:
        if sp not in speeds:
            speeds[sp] = x.speed if sp == 1.25 else stoppage.dead_from_players(x.df, sum(x.teams, []), x.segments, pitch=x.pitch, speed=sp)
        quiet = speeds[sp].copy()
        for r in x.rframes:
            quiet[r:r + q] = False
        dead = drop_short(x.ball_out | quiet | x.before, x.segments, 150) | x.restart
        base = restart_team(sticky_labels(x.df, x.teams, x.segments, "closest", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
        live = np.isin(base, ["H", "A"])
        touch = restart_team(sticky_labels(x.df, x.teams, x.segments, "touch", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
        lab = merge_short(restart_team(viterbi(lock_clear(blend_touch(P[g], touch), near), live), x.rframes, x.tag_teams))
        out[(g, (sp, q))] = spell_f1(x.gt, lab)
    print(g, " ".join("{}:{:.4f}".format(v, out[(g, v)]) for v in VARIANTS), flush=True)
pickle.dump(out, open(os.path.join(os.environ.get("OUT", "."), "stopspeed_{}_{}.pkl".format(int(hard), seed)), "wb"))
