"""Who has the ball, from the players alone (no ball): team shape and movement.

Idea from Lang et al. 2022 (docs/research/possession-without-ball.md): they got in-play vs
stopped right on 92% of Bundesliga frames from players only. Same recipe, possession as the target,
but with team summaries instead of 22 named players so it carries over to another league.

Per team, in its own attacking direction (attacks towards +x), per frame:
  centroid x / y, spread x / y, 10th / 90th percentile of x (back line / front line),
  mean forward speed, mean speed.
Then each at 3 time scales (centered means over 1 s, 4 s, 10 s) and the 2 s-ahead minus
2 s-back change of the centroid. Training doubled by swapping the two teams (label flipped), so
the model can't learn "home has it more".

Trained on the 7 Bundesliga games (prep/bundesliga_data.py), deterministic (random_state=0).
Leave-one-game-out: team right on 82-90% of live frames, 87.6% on Metrica (never trained on).
    python experiments/ahmed/shape_model.py    # that check
"""

import os
import pickle
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

CACHE = os.path.join(ROOT, "data", "cache")
WINDOWS = (25, 100, 250)
STEP = 5  # train on every 5th frame


def attack_sign(df, teams, segments, pitch):
    """+1 where home attacks towards +x, -1 otherwise, per frame (from where each team stands)."""
    sign = np.ones(len(df))
    for a, b in segments:
        hx = np.nanmean(df[[p + "_x" for p in teams[0]]].to_numpy()[a:b])
        ax = np.nanmean(df[[p + "_x" for p in teams[1]]].to_numpy()[a:b])
        sign[a:b] = 1.0 if hx < ax else -1.0
    return sign


def _team_block(x, y, pitch):
    """x already in the team's attacking direction (metres). -> DataFrame of per-frame features."""
    import warnings

    with np.errstate(invalid="ignore"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN frames (players not tracked)
            vx = np.diff(x, axis=0, prepend=np.nan) * 25
            vy = np.diff(y, axis=0, prepend=np.nan) * 25
            vx = pd.DataFrame(vx).rolling(5, center=True, min_periods=1).mean().to_numpy()
            vy = pd.DataFrame(vy).rolling(5, center=True, min_periods=1).mean().to_numpy()
            f = {
                "cx": np.nanmean(x, 1), "cy": np.abs(np.nanmean(y, 1) - pitch[1] / 2),
                "sx": np.nanstd(x, 1), "sy": np.nanstd(y, 1),
                "q10": np.nanpercentile(x, 10, axis=1), "q90": np.nanpercentile(x, 90, axis=1),
                "vx": np.nanmean(np.clip(vx, -12, 12), 1),
                "sp": np.nanmean(np.clip(np.hypot(vx, vy), 0, 12), 1),
            }
    return pd.DataFrame(f)


def features(df, teams, segments, pitch):
    """(home features, away features), each a DataFrame, same columns."""
    sign = attack_sign(df, teams, segments, pitch)[:, None]
    out = []
    for i, ids in enumerate(teams):
        x = df[[p + "_x" for p in ids]].to_numpy() * pitch[0]
        y = df[[p + "_y" for p in ids]].to_numpy() * pitch[1]
        s = sign if i == 0 else -sign
        x = np.where(s > 0, x, pitch[0] - x)
        base = _team_block(x, y, pitch)
        cols = {}
        for w in WINDOWS:
            r = base.rolling(w, center=True, min_periods=1).mean()
            for c in base.columns:
                cols["{}_{}".format(c, w)] = r[c].to_numpy()
        cx = base["cx"]
        cols["dcx_50"] = (cx.shift(-50) - cx.shift(50)).to_numpy()
        out.append(pd.DataFrame(cols))
    return out


def design(home, away):
    """Model input: home block, away block, and their difference."""
    d = home.to_numpy() - away.to_numpy()
    return np.hstack([home.to_numpy(), away.to_numpy(), d])


def game_features(name, df, teams, segments, pitch):
    path = os.path.join(CACHE, "shape_{}.pkl".format(name))
    if os.path.exists(path):
        return pickle.load(open(path, "rb"))
    f = features(df, teams, segments, pitch)
    pickle.dump(f, open(path, "wb"))
    return f


def train(blocks):
    """blocks: [(home, away, labels)] -> fitted model. Labels 'H'/'A'; other frames dropped."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    X, y = [], []
    for home, away, lab in blocks:
        keep = np.flatnonzero(np.isin(lab, ["H", "A"]))[::STEP]
        X.append(design(home.iloc[keep], away.iloc[keep])); y.append(lab[keep] == "H")
        X.append(design(away.iloc[keep], home.iloc[keep])); y.append(lab[keep] == "A")  # swapped
    model = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.1, max_leaf_nodes=31,
                                           l2_regularization=1.0, random_state=0)
    model.fit(np.vstack(X), np.concatenate(y))
    return model


def p_home(model, home, away):
    """P(home has the ball) per frame, averaged over both team orders so it's symmetric."""
    a = model.predict_proba(design(home, away))[:, 1]
    b = model.predict_proba(design(away, home))[:, 1]
    return (a + 1 - b) / 2


def trained_model():
    """The model trained on all 7 Bundesliga games."""
    from bundesliga_data import games
    from sticky import period_segments

    blocks = []
    for g, (df, teams, gt, pitch) in games().items():
        home, away = game_features(g, df, teams, period_segments(df), pitch)
        blocks.append((home, away, gt))
    return train(blocks)
