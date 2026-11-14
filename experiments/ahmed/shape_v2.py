"""Players-only model, v2: the row-13 team-shape features plus pressure features.

The team under pressure usually has the ball. Per team, per frame (raw pitch metres):
  pmin   distance from its most-pressed player to the nearest opponent
  pmin2  same for its second most-pressed player
  pmean  mean distance of its players to their nearest opponent
  n5     opponents within 5 m of its most-pressed player
  close  how fast the nearest opponent closes on that player (m/s, + = closing)
  vmax   speed of its fastest player
  fwd    its most advanced player beyond the opponents' last line (attacking direction)
Each smoothed over 0.2 s, 1 s, 4 s.

    python experiments/ahmed/shape_v2.py [--metrica-train]
Writes leave-one-game-out P(home) to data/cache/shape_p_v2[m]_<game>.pkl.
"""

import os
import pickle
import sys
import warnings

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(ROOT, "prep"), HERE]
import shape_model as sm  # noqa: E402

VERSION = "v2"
P_WINDOWS = (5, 25, 100)


def _xy(df, ids, pitch):
    return df[[p + "_x" for p in ids]].to_numpy() * pitch[0], df[[p + "_y" for p in ids]].to_numpy() * pitch[1]


def _vel(a):
    v = np.diff(a, axis=0, prepend=np.nan) * 25
    return pd.DataFrame(v).rolling(5, center=True, min_periods=1).mean().to_numpy()


def pressure(df, teams, segments, pitch):
    sign = sm.attack_sign(df, teams, segments, pitch)
    (hx, hy), (ax, ay) = _xy(df, teams[0], pitch), _xy(df, teams[1], pitch)
    out = []
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for i, (mx, my, ox, oy) in enumerate(((hx, hy, ax, ay), (ax, ay, hx, hy))):
            n = len(df)
            d = np.sqrt((mx[:, :, None] - ox[:, None, :]) ** 2 + (my[:, :, None] - oy[:, None, :]) ** 2)
            d = np.where(np.isnan(d), np.inf, d)
            near = d.min(2)                       # frames x my players
            near = np.where(np.isinf(near), np.nan, near)
            srt = np.sort(np.where(np.isnan(near), np.inf, near), 1)
            k = np.argmin(np.where(np.isnan(near), np.inf, near), 1)
            rows = np.arange(n)
            dk = d[rows, k]                       # distances from most-pressed player to every opponent
            n5 = (dk < 5).sum(1).astype(float)
            # closing speed of the nearest opponent on the most-pressed player
            j = np.argmin(dk, 1)
            vmx, vmy, vox, voy = _vel(mx), _vel(my), _vel(ox), _vel(oy)
            rx, ry = mx[rows, k] - ox[rows, j], my[rows, k] - oy[rows, j]
            rv_x, rv_y = vmx[rows, k] - vox[rows, j], vmy[rows, k] - voy[rows, j]
            dist = np.hypot(rx, ry)
            close = -(rx * rv_x + ry * rv_y) / np.maximum(dist, 0.1)
            sp = np.clip(np.hypot(vmx, vmy), 0, 12)
            s = sign if i == 0 else -sign
            mxa = np.where(s[:, None] > 0, mx, pitch[0] - mx)
            oxa = np.where(s[:, None] > 0, ox, pitch[0] - ox)  # opponents in my attacking direction
            f = pd.DataFrame({
                "pmin": np.where(np.isinf(srt[:, 0]), np.nan, srt[:, 0]),
                "pmin2": np.where(np.isinf(srt[:, 1]), np.nan, srt[:, 1]),
                "pmean": np.nanmean(near, 1),
                "n5": n5, "close": np.clip(close, -10, 10),
                "vmax": np.nanmax(sp, 1),
                "fwd": np.nanmax(mxa, 1) - np.nanmax(oxa, 1),
            })
            cols = {}
            for w in P_WINDOWS:
                r = f.rolling(w, center=True, min_periods=1).mean()
                for c in f.columns:
                    cols["{}_{}".format(c, w)] = r[c].to_numpy()
            out.append(pd.DataFrame(cols))
    return out


def features(df, teams, segments, pitch):
    h, a = sm.features(df, teams, segments, pitch)
    ph, pa = pressure(df, teams, segments, pitch)
    return pd.concat([h, ph], axis=1), pd.concat([a, pa], axis=1)


def game_features(name, df, teams, segments, pitch):
    path = os.path.join(sm.CACHE, "shape_{}_{}.pkl".format(VERSION, name))
    if os.path.exists(path):
        return pickle.load(open(path, "rb"))
    f = features(df, teams, segments, pitch)
    pickle.dump(f, open(path, "wb"))
    return f


def main():
    import bench
    from sticky import period_segments

    metrica_train = "--metrica-train" in sys.argv
    tag = VERSION + ("m" if metrica_train else "")
    games = bench.load_games()
    F = {}
    for g, (df, teams, gt, pitch) in games.items():
        F[g] = game_features(g, df, teams, period_segments(df), pitch)
        print("features", g, F[g][0].shape, flush=True)
    for g, (df, teams, gt, pitch) in games.items():
        train_on = [o for o in games if o != g and (metrica_train or o != "metrica3")]
        m = sm.train([(F[o][0], F[o][1], games[o][2]) for o in train_on])
        p = sm.p_home(m, *F[g])
        live = np.isin(gt, ["H", "A"])
        print(g, "team right on {:.1%} of live frames".format((np.where(p > 0.5, "H", "A") == gt)[live].mean()), flush=True)
        pickle.dump(p, open(os.path.join(sm.CACHE, "shape_p_{}_{}.pkl".format(tag, g)), "wb"))


if __name__ == "__main__":
    main()
