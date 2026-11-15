"""Leave-one-game-out check of the players-only model (prep/shape_model.py) on the 8 practice games.

    python experiments/ahmed/shape_model.py

Writes P(home has the ball) per game to data/cache/shape_p_<game>.pkl for the bench.
"""

import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [HERE, os.path.join(ROOT, "prep")]
from shape_model import CACHE, game_features, p_home, train  # noqa: E402


def main():
    import bench
    from sticky import period_segments

    games = bench.load_games()
    F = {g: game_features(g, df, teams, period_segments(df), pitch) for g, (df, teams, gt, pitch) in games.items()}
    for g, (df, teams, gt, pitch) in games.items():
        m = train([(F[o][0], F[o][1], games[o][2]) for o in games if o not in (g, "metrica3")])
        p = p_home(m, *F[g])
        live = np.isin(gt, ["H", "A"])
        print(g, "team right on {:.1%} of live frames (players only)".format((np.where(p > 0.5, "H", "A") == gt)[live].mean()), flush=True)
        pickle.dump(p, open(os.path.join(CACHE, "shape_p_{}.pkl".format(g)), "wb"))


if __name__ == "__main__":
    main()
