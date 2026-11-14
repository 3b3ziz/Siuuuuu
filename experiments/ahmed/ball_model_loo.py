"""Leave-one-game-out versions of the ball-aware team model (prep/ball_model.py), for the bench.

Each practice game gets a model trained on the other games only (Metrica never in training).
"""

import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(ROOT, "prep"), HERE]
import shape_model as sm  # noqa: E402
from ball_model import CACHE, VERSION, full_features, training_blocks as _blocks  # noqa: E402,F401


def training_blocks():
    """{game: [(home, away, gt)]} with the ball hidden two ways (prep/ball_model.TRAIN_HIDING)."""
    path = os.path.join(CACHE, "ballmodel_train_{}.pkl".format(VERSION))
    if os.path.exists(path):
        return pickle.load(open(path, "rb"))
    import bench

    out = {g: _blocks({g: v}) for g, v in bench.load_games().items()}
    pickle.dump(out, open(path, "wb"))
    return out


def loo_models(metrica_train=False):
    """{game: model trained on the other games}."""
    path = os.path.join(CACHE, "ballmodel_loo{}_{}.pkl".format("m" if metrica_train else "", VERSION))
    if os.path.exists(path):
        return pickle.load(open(path, "rb"))
    B = training_blocks()
    out = {}
    for g in B:
        use = [o for o in B if o != g and (metrica_train or o != "metrica3")]
        out[g] = sm.train([blk for o in use for blk in B[o]])
        print("trained without", g, flush=True)
    pickle.dump(out, open(path, "wb"))
    return out
