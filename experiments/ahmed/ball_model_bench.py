"""Score the ball-aware team model (ball_model.py) on the 6 bench runs against row 14.

    python experiments/ahmed/ball_model_bench.py [--metrica-train]
"""

import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(ROOT, "prep"), HERE]
import shape_model as sm  # noqa: E402
from ball_model import CACHE, VERSION, full_features, viterbi  # noqa: E402
from ball_model_loo import loo_models  # noqa: E402
from fastbench import games, spell_f1  # noqa: E402
from sticky import sticky_labels  # noqa: E402
from tags import restart_team  # noqa: E402
from team_fixes import merge_short, model_override, on_ball, shape_gap  # noqa: E402

RUNS = [(False, 0), (False, 1), (False, 2), (True, 0), (True, 1), (True, 2)]


def row13_base(x):
    lab = sticky_labels(x.df, x.teams, x.segments, "closest", dead=x.dead, pitch=x.pitch)
    return restart_team(lab, x.rframes, x.tag_teams)


def row14(x, p):
    lab = shape_gap(row13_base(x), x.df["ball_x"].notna().to_numpy(), p)
    return merge_short(model_override(lab, p, near=on_ball(x.df, x.teams, x.pitch)))


def main():
    mt = "--metrica-train" in sys.argv
    models = loo_models(mt)
    P1 = {g: pickle.load(open(os.path.join(CACHE, "shape_p_{}.pkl".format(g)), "rb")) for g in models}
    res = {}
    for hard, seed in RUNS:
        path = os.path.join(CACHE, "ballmodel_p{}_{}_{}_{}.pkl".format("m" if mt else "", "h" if hard else "n", seed, VERSION))
        G = games(hard=hard, seed=seed)
        if os.path.exists(path):
            P = pickle.load(open(path, "rb"))
        else:
            P = {g: sm.p_home(models[g], *full_features(g, x.df, x.teams, x.segments, x.pitch)) for g, x in G.items()}
            pickle.dump(P, open(path, "wb"))
        for g, x in G.items():
            live = np.isin(x.gt, ["H", "A"])
            base = row13_base(x)
            r = {"acc_old": (np.where(P1[g] > .5, "H", "A") == x.gt)[live].mean(),
                 "acc_new": (np.where(P[g] > .5, "H", "A") == x.gt)[live].mean(),
                 "row14": spell_f1(x.gt, row14(x, P1[g]))}
            for pen in (100, 150, 300):
                lab = shape_gap(base, x.df["ball_x"].notna().to_numpy(), P[g])
                r["ovr{}".format(pen)] = spell_f1(x.gt, merge_short(model_override(lab, P[g], near=on_ball(x.df, x.teams, x.pitch), penalty=pen)))
            alive = np.isin(base, ["H", "A"])
            for lam in (5, 7, 10, 20, 40):
                lab = restart_team(viterbi(P[g], alive, lam), x.rframes, x.tag_teams)
                r["vit{}".format(lam)] = spell_f1(x.gt, merge_short(lab))
            res[(hard, seed, g)] = r
        keys = list(r)
        m = {k: np.mean([v[k] for (h, s, g), v in res.items() if (h, s) == (hard, seed)]) for k in keys}
        print("hard" if hard else "normal", seed, "  ".join("{} {:.4f}".format(k, v) for k, v in m.items()), flush=True)
    pickle.dump(res, open(os.path.join(CACHE, "ballmodel_res{}_{}.pkl".format("m" if mt else "", VERSION)), "wb"))
    keys = list(next(iter(res.values())))
    for k in keys:
        if k.startswith("acc"):
            continue
        d = np.array([v[k] - v["row14"] for v in res.values()])
        met = np.mean([v[k] - v["row14"] for (h, s, g), v in res.items() if g == "metrica3"])
        print("{:8s} vs row14 {:+.4f}  wins {}/{}  worst {:+.3f}  metrica {:+.4f}".format(k, d.mean(), (d > 0).sum(), len(d), d.min(), met))


if __name__ == "__main__":
    main()
