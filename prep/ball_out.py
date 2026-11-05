"""Approach 5: "the ball left the pitch" = stoppage, straight away.

When the ball crosses a line, play is dead at that moment. No need to wait for players to slow
down. Two ways it shows in the tracking:

  1. The ball is seen outside the pitch.
  2. The ball is last seen within NEAR_LINE_M of a line, then disappears for at least
     MIN_GONE_FRAMES (the tracker usually loses it once it's out).

Either way the stoppage runs from that moment until the ball is next seen inside the pitch.

Variants also add the speed stoppages from prep/stoppage.py (for fouls), and "_moving" lets a
visibly moving ball on the pitch overrule them: if the ball is flying, play is live.

    python prep/ball_out.py      # writes ball_out*.csv for both practice sets
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sample_game import META, PITCH, RAW, SAMPLE, drop_ball  # noqa: E402
from sticky import period_segments, players_by_team, runs, sticky_labels  # noqa: E402
from stoppage import dead_from_players  # noqa: E402
from baseline import write_submission  # noqa: E402

# Params. Football sense, not tuned.
NEAR_LINE_M = 2.0
MIN_GONE_FRAMES = 25   # 1 s
MOVING_MS = 3.0        # ball moving at least this fast on the pitch = play is live


def ball_moving(df, pitch=PITCH, moving=MOVING_MS):
    """Ball visible inside the pitch and moving (1/5 s median speed above MOVING_MS)."""
    bx, by = df["ball_x"].to_numpy() * pitch[0], df["ball_y"].to_numpy() * pitch[1]
    v = np.sqrt(np.diff(bx, prepend=np.nan) ** 2 + np.diff(by, prepend=np.nan) ** 2) * 25
    v = pd.Series(v).rolling(5, center=True, min_periods=3).median().to_numpy()
    with np.errstate(invalid="ignore"):
        inside = (bx >= 0) & (bx <= pitch[0]) & (by >= 0) & (by <= pitch[1])
        return inside & (v > moving)


def dead_from_ball_out(df, segments, near_m=NEAR_LINE_M, min_gone=MIN_GONE_FRAMES, pitch=PITCH):
    bx, by = df["ball_x"].to_numpy(), df["ball_y"].to_numpy()
    seen = ~np.isnan(bx)
    with np.errstate(invalid="ignore"):
        outside = seen & ((bx < 0) | (bx > 1) | (by < 0) | (by > 1))
        mx, my = near_m / pitch[0], near_m / pitch[1]
        near = seen & ((bx < mx) | (bx > 1 - mx) | (by < my) | (by > 1 - my))
    inside = seen & ~outside
    dead = np.zeros(len(df), dtype=bool)
    for start, stop in segments:
        # Out of play from each trigger until the ball is next seen inside the pitch.
        i = start
        while i < stop:
            trigger = outside[i]
            if not trigger and near[i] and i + 1 < stop and not seen[i + 1]:
                j = i + 1
                while j < stop and not seen[j]:
                    j += 1
                trigger = j - (i + 1) >= min_gone
            if trigger:
                j = i + 1
                while j < stop and not inside[j]:
                    j += 1
                dead[i:j] = True
                i = j
            else:
                i += 1
    return dead


def main():
    from kloppy import metrica

    ds = metrica.load_tracking_epts(meta_data=META, raw_data=RAW)
    df = ds.to_df()
    segments = period_segments(df)
    teams = players_by_team(ds)
    speed_dead = dead_from_players(df, sum(teams, []), segments)

    gt = pd.read_csv(os.path.join(SAMPLE, "sample_gt.csv"))["label"].to_numpy()
    alive = np.isin(gt, ["H", "A"])
    for folder, frame in (("results", df), ("results_noisy", drop_ball(df, alive))):
        out = dead_from_ball_out(frame, segments)
        live = ball_moving(frame)
        for name, dead in (("ball_out", out), ("ball_out_or_speed", out | speed_dead),
                           ("ball_out_or_speed_moving", out | (speed_dead & ~live))):
            path = os.path.join(SAMPLE, folder, name + ".csv")
            write_submission(path, sticky_labels(frame, teams, segments, "closest", dead=dead))
            print("wrote", path)


if __name__ == "__main__":
    main()
