"""Row 19: a learned stoppage model (experiments/ahmed/dead_model_bench.py on the bench).

P(play is stopped) per frame from: players' mean speed (1, 3, 10 s; 5 s before and after), how
often the ball is seen (1, 3, 10 s), time since/until it was seen, ball speed, distance of the
last/next seen ball to a line, our rule-made stoppages (row 18) and the set-piece tags.
Gradient boosting, trained on the 7 Bundesliga games with the ball hidden like ours (the bench's
normal and hard runs, seed 0; DFL's ball-alive flag as the key). Smoothed over 1 s; dead where
over 0.5, stoppages under 6 s dropped.
"""

import os
import pickle
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, "data", "cache")
VERSION = "v1"
THRESHOLD = 0.5


def _since(mask):
    out = np.zeros(len(mask))
    c = 500
    for i, m in enumerate(mask):
        c = 0 if m else min(c + 1, 500)
        out[i] = c
    return out


def features(df, teams, pitch, rule, tag):
    from stoppage import mean_player_speed
    from stop_fixes import ball_speed

    ms = pd.Series(mean_player_speed(df, sum(teams, []), pitch)).ffill().fillna(0)
    bx, by = df["ball_x"].to_numpy(), df["ball_y"].to_numpy()
    seen = ~np.isnan(bx)
    v = ball_speed(df, pitch)
    line = np.minimum(np.minimum(bx, 1 - bx) * pitch[0], np.minimum(by, 1 - by) * pitch[1])
    f = {}
    for w in (25, 75, 250):
        f["ms%d" % w] = ms.rolling(w, center=True, min_periods=1).mean().to_numpy()
        f["seen%d" % w] = pd.Series(seen.astype(float)).rolling(w, center=True, min_periods=1).mean().to_numpy()
    f["ms_past"] = ms.rolling(125, min_periods=1).mean().to_numpy()
    f["ms_fut"] = ms[::-1].rolling(125, min_periods=1).mean().to_numpy()[::-1]
    f["since"] = _since(seen)
    f["until"] = _since(seen[::-1])[::-1]
    f["v"] = np.nan_to_num(v, nan=-1)
    f["vmax25"] = pd.Series(v).rolling(25, center=True, min_periods=1).max().fillna(-1).to_numpy()
    f["line_last"] = pd.Series(line).ffill().fillna(-1).to_numpy()
    f["line_next"] = pd.Series(line).bfill().fillna(-1).to_numpy()
    f["rule"] = rule.astype(float)
    f["rule125"] = pd.Series(rule.astype(float)).rolling(125, center=True, min_periods=1).mean().to_numpy()
    f["tag"] = tag.astype(float)
    return pd.DataFrame(f)


def row18_rule(x):
    """Row 18's stoppages on a bench game (same steps as prep/run_real.py, without goals/edges)."""
    from stop_fixes import ball_speed, drop_short, kick_ends, kick_frames, still_then_kick
    from tags import QUIET_AFTER_RESTART

    quiet = x.speed.copy()
    for r in x.rframes:
        quiet[r:r + QUIET_AFTER_RESTART] = False
    v = ball_speed(x.df, x.pitch)
    raw = x.ball_out | quiet | x.before | still_then_kick(v, x.segments)
    return kick_ends(drop_short(raw, x.segments), x.segments, kick_frames(v)) | x.restart


def trained_model():
    path = os.path.join(CACHE, "deadmodel_{}.pkl".format(VERSION))
    if os.path.exists(path):
        return pickle.load(open(path, "rb"))
    from sklearn.ensemble import HistGradientBoostingClassifier

    sys.path.insert(0, os.path.join(ROOT, "experiments", "ahmed"))
    from fastbench import games

    X, y = [], []
    for hard in (False, True):
        for g, x in games(hard=hard, seed=0).items():
            if not g.startswith("bl_"):
                continue
            f = features(x.df, x.teams, x.pitch, row18_rule(x), x.restart)
            idx = np.flatnonzero(np.isin(x.gt, ["H", "A", "D"]))[::5]
            X.append(f.iloc[idx])
            y.append(x.gt[idx] == "D")
    m = HistGradientBoostingClassifier(max_iter=200, random_state=0).fit(pd.concat(X), np.concatenate(y))
    pickle.dump(m, open(path, "wb"))
    return m


def dead_from_model(df, teams, pitch, segments, rule, tag, threshold=THRESHOLD):
    from stop_fixes import drop_short

    p = trained_model().predict_proba(features(df, teams, pitch, rule, tag))[:, 1]
    p = pd.Series(p).rolling(25, center=True, min_periods=1).mean().to_numpy()
    return drop_short(p > threshold, segments) | tag
