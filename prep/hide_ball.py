"""Hide the ball on a practice game the way our real match loses it (measured Nov 13, see
docs/notes.md): ~72% of stoppage frames, ~15% of live frames, live gaps with the real lengths and
more likely near a line, every gap under 5 s filled with a straight line like the tracker does.

Used by the bench (experiments/ahmed/bench.py) and to make training data for prep/ball_model.py.
Seeded, so the same seed always hides the same frames.
"""

import numpy as np

from sticky import runs

LIVE_GAPS = [129, 132, 132, 132, 134, 136, 144, 146, 146, 149, 152, 164, 169, 176, 177, 182, 183, 187,
             190, 194, 207, 223, 229, 234, 240, 245, 268, 269, 289, 289, 297, 319, 406, 511, 521, 558,
             604, 611, 743, 1124]  # real live-play gap lengths (frames) on our match
DEAD_HIDDEN = 0.75
LIVE_HIDDEN = 0.15
FILL_UNDER = 125


def real_like_ball(df, gt, pitch, segments, seed=0, hard=False):
    rng = np.random.default_rng(seed)
    bx, by = df["ball_x"].to_numpy().copy(), df["ball_y"].to_numpy().copy()
    hide = np.zeros(len(df), dtype=bool)
    dead = gt == "D"
    for a, b in segments:
        for s, e in runs(dead[a:b]):
            if rng.random() < DEAD_HIDDEN:
                if hard:
                    s, e = s + rng.integers(-75, 76), e + rng.integers(-75, 76)
                    s = max(s, 0)
                    e = max(e, s + 1)  # after s is clamped: a negative e would hide the whole half
                hide[a + s:a + e] = True
    live = np.isin(gt, ["H", "A"])
    with np.errstate(invalid="ignore"):
        x, y = bx * pitch[0], by * pitch[1]
        d = np.fmin.reduce([x, pitch[0] - x, y, pitch[1] - y])
    weight = np.where(d < 2, 5.0, np.where(d < 5, 2.0, np.where(d < 15, 1.5, 0.9)))
    cand = np.flatnonzero(live & ~np.isnan(bx))
    p = weight[cand] / weight[cand].sum()
    while (hide | np.isnan(bx))[live].mean() < LIVE_HIDDEN:
        s = rng.choice(cand, p=p)
        hide[s:s + rng.choice(LIVE_GAPS)] = True
    bx[hide], by[hide] = np.nan, np.nan
    # the tracker fills short gaps with a straight line
    for a, b in segments:
        for s, e in runs(np.isnan(bx[a:b])):
            s, e = a + s, a + e
            if e - s < FILL_UNDER and s > a and e < b:
                t = np.arange(1, e - s + 1) / (e - s + 1)
                bx[s:e] = bx[s - 1] + t * (bx[e] - bx[s - 1])
                by[s:e] = by[s - 1] + t * (by[e] - by[s - 1])
    out = df.copy()
    out["ball_x"], out["ball_y"] = bx, by
    return out
