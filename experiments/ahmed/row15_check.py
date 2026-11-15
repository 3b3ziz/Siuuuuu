"""Row 15 exactly as the shared script does it (prep/ball_model.py), vs row 14, on the 6 bench runs.
Raw and "controlled" answer keys.     python experiments/ahmed/row15_check.py
"""
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(ROOT, "prep"), HERE]
from ball_model import CACHE, VERSION, lock_clear, viterbi  # noqa: E402
from ball_model_bench import RUNS, row13_base, row14  # noqa: E402
from controlled import controlled  # noqa: E402
from fastbench import games, spell_f1  # noqa: E402
from tags import restart_team  # noqa: E402
from team_fixes import merge_short, on_ball  # noqa: E402

rows = []
for hard, seed in RUNS:
    G = games(hard=hard, seed=seed)
    P = pickle.load(open(os.path.join(CACHE, "ballmodel_p_{}_{}_{}.pkl".format("h" if hard else "n", seed, VERSION)), "rb"))
    for g, x in G.items():
        p1 = pickle.load(open(os.path.join(CACHE, "shape_p_{}.pkl".format(g)), "rb"))
        ctl, base = controlled(x.gt), row13_base(x)
        new = merge_short(restart_team(viterbi(lock_clear(P[g], on_ball(x.df, x.teams, x.pitch)), np.isin(base, ["H", "A"])),
                                       x.rframes, x.tag_teams))
        old = row14(x, p1)
        rows.append((g, spell_f1(x.gt, old), spell_f1(x.gt, new), spell_f1(ctl, old), spell_f1(ctl, new)))
    print(hard, seed, "row14 {:.4f} row15 {:.4f}   controlled {:.4f} -> {:.4f}".format(*np.mean([r[1:] for r in rows[-8:]], 0)), flush=True)
a = np.array([r[1:] for r in rows])
m = [i for i, r in enumerate(rows) if r[0] == "metrica3"]
print("raw +{:.4f} wins {}/48 worst {:+.3f} | controlled +{:.4f} wins {}/48 | metrica raw {:+.4f} controlled {:+.4f}".format(
    (a[:, 1] - a[:, 0]).mean(), (a[:, 1] > a[:, 0]).sum(), (a[:, 1] - a[:, 0]).min(), (a[:, 3] - a[:, 2]).mean(),
    (a[:, 3] > a[:, 2]).sum(), (a[m, 1] - a[m, 0]).mean(), (a[m, 3] - a[m, 2]).mean()))
