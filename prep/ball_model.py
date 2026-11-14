"""Who has the ball, using the ball when it's there (row 15 in docs/notes.md).

Team model: the players-only features of prep/shape_model.py plus ball features, trained on the 7
Bundesliga games with the ball hidden the way our match loses it (prep/hide_ball.py, seeds 10 and
11). Then a decoder picks the most likely H/A sequence within each live stretch, paying SWITCH_COST
per change of team (Viterbi). Stoppages come from the rest of the pipeline, unchanged.

Ball features, per team, in its own view:
  d       distance from its nearest player to the ball (NaN while the ball is hidden)
  on      1 if it's clearly on the ball (sticky "closest" rule), else 0 (NaN while hidden)
  bx      ball x in its attacking direction
  past / future means of d and on (0.5 s, 2 s), centred means of on (1 s, 4 s)
  last-seen and next-seen d / on, carried through hidden stretches
Shared: frames since / until the ball was seen, ball speed.
Stretches where a team has been clearly on the ball for 2 s+ are locked to it (lock_clear).

Bench (experiments/ahmed/ball_model_bench.py, models never trained on the game they're scored on):
over row 14 +0.07 on all 48 game-runs, Metrica +0.05. Still +0.07 when trained on a different
hiding recipe (experiments/ahmed/ball_model_robust.py), so it isn't learning the fake hiding.
"""

import os
import pickle
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shape_model as sm  # noqa: E402
import sticky  # noqa: E402
from sticky import runs  # noqa: E402
from team_fixes import on_ball  # noqa: E402

CACHE = sm.CACHE
VERSION = "v1"
TRAIN_HIDING = ((10, False), (11, True))  # (seed, hard): differ from the bench seeds 0-2
SWITCH_COST = 7.0  # flat from 5 to 10 on the bench
LOCK_FRAMES = 50   # a team clearly on the ball for 2 s+ keeps it, whatever the model says


def _past(s, w):
    return s.rolling(w, min_periods=1).mean().to_numpy()


def _future(s, w):
    return s[::-1].rolling(w, min_periods=1).mean().to_numpy()[::-1]


def ball_block(df, teams, segments, pitch):
    dh, da = sticky.team_distances(df, teams, pitch)
    seen = df["ball_x"].notna().to_numpy()
    near = on_ball(df, teams, pitch)
    sign = sm.attack_sign(df, teams, segments, pitch)
    bx = df["ball_x"].to_numpy() * pitch[0]
    by = df["ball_y"].to_numpy() * pitch[1]
    with np.errstate(invalid="ignore"):
        bsp = np.hypot(np.diff(bx, prepend=np.nan), np.diff(by, prepend=np.nan)) * 25
    bsp = pd.Series(np.clip(bsp, 0, 40)).rolling(5, center=True, min_periods=1).mean().to_numpy()
    idx = np.arange(len(df))
    last = pd.Series(np.where(seen, idx, np.nan)).ffill().to_numpy()
    nxt = pd.Series(np.where(seen, idx, np.nan)).bfill().to_numpy()
    since, until = idx - last, nxt - idx
    out = []
    for i, (d, t) in enumerate(((dh, "H"), (da, "A"))):
        d = np.where(seen, np.minimum(d, 60), np.nan)
        on = np.where(seen, (near == t).astype(float), np.nan)
        s = sign if i == 0 else -sign
        f = {"d": d, "on": on, "bx": np.where(s > 0, bx, pitch[0] - bx), "since": since, "until": until, "bsp": bsp}
        D, O = pd.Series(d), pd.Series(on)
        for w in (12, 50):
            f["d_p{}".format(w)], f["d_f{}".format(w)] = _past(D, w), _future(D, w)
            f["on_p{}".format(w)], f["on_f{}".format(w)] = _past(O, w), _future(O, w)
        for w in (25, 100):
            f["on_c{}".format(w)] = O.rolling(w, center=True, min_periods=1).mean().to_numpy()
        f["d_last"], f["d_next"] = D.ffill().to_numpy(), D.bfill().to_numpy()
        f["on_last"], f["on_next"] = O.ffill().to_numpy(), O.bfill().to_numpy()
        out.append(pd.DataFrame(f))
    return out


def full_features(name, df, teams, segments, pitch):
    """name: cache key for the players-only part (practice games), None = don't cache."""
    if name is None:
        h, a = sm.features(df, teams, segments, pitch)
    else:
        h, a = sm.game_features(name, df, teams, segments, pitch)
    bh, ba = ball_block(df, teams, segments, pitch)
    return pd.concat([h, bh], axis=1), pd.concat([a, ba], axis=1)


def viterbi(p, live, penalty=SWITCH_COST):
    """Two states within each live run, cost -log p, `penalty` per switch. Elsewhere 'D'."""
    lab = np.full(len(p), "D", dtype="<U1")
    q = np.clip(p, 1e-3, 1 - 1e-3)
    cH, cA = -np.log(q), -np.log(1 - q)
    for s, e in runs(live):
        n = e - s
        back = np.zeros((n, 2), dtype=bool)  # True = came from the other state
        acc = np.array([cH[s], cA[s]])
        for t in range(1, n):
            stay, sw = acc, acc[::-1] + penalty
            back[t] = sw < stay
            acc = np.minimum(stay, sw) + (cH[s + t], cA[s + t])
        k = int(np.argmin(acc))
        out = np.empty(n, dtype=int)
        for t in range(n - 1, -1, -1):
            out[t] = k
            if back[t, k]:
                k = 1 - k
        lab[s:e] = np.where(out == 0, "H", "A")
    return lab


def lock_clear(p, near, min_frames=LOCK_FRAMES):
    """Insurance: where a team has been clearly on the ball for min_frames+, it has it.

    On our match the model overruled such stretches 2x more often than on practice (1.9% vs
    0.4-1% of frames), and on practice those overrules are wrong a third of the time or more. Costs
    -0.001 on the bench.
    """
    q = p.copy()
    for t, v in (("H", 1 - 1e-3), ("A", 1e-3)):
        for s, e in runs(near == t):
            if e - s >= min_frames:
                q[s:e] = v
    return q


def training_blocks(games, hiding=TRAIN_HIDING):
    """[(home, away, answer key)] for each game and each hiding."""
    from hide_ball import real_like_ball

    out = []
    for g, (df, teams, gt, pitch) in games.items():
        segs = sticky.period_segments(df)
        for seed, hard in hiding:
            h, a = full_features(g, real_like_ball(df, gt, pitch, segs, seed=seed, hard=hard), teams, segs, pitch)
            out.append((h, a, gt))
    return out


def trained_model():
    """Trained on the 7 Bundesliga games, cached in data/cache (deterministic, so the cache only saves time)."""
    path = os.path.join(CACHE, "ballmodel_{}.pkl".format(VERSION))
    if os.path.exists(path):
        return pickle.load(open(path, "rb"))
    from bundesliga_data import games

    model = sm.train(training_blocks(games()))
    pickle.dump(model, open(path, "wb"))
    return model
