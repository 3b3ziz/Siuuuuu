"""Approach 3: stoppage detector from the players alone, plus sticky possession for the team.

When play stops, everyone slows to a walk. So:

  1. Average speed of all tracked players per frame, from their positions (m/s).
  2. Smoothed with a rolling median over WINDOW_FRAMES, so one sprint or one tracking glitch
     doesn't flip it.
  3. Below SPEED_MS = stoppage.
  4. Clean-up: stoppages shorter than MIN_DEAD_FRAMES are dropped (a real stoppage lasts at
     least a few seconds), and live gaps shorter than MIN_ALIVE_FRAMES inside a stoppage are
     filled.

The ball isn't used here on purpose. In our match it goes missing during live play, so it can't
tell us when play stopped. The team on live frames comes from prep/sticky.py ("closest" rule).

    python prep/stoppage.py      # writes sticky_stoppage.csv for both practice sets
"""

import os
import sys
import warnings

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sample_game import META, PITCH, RAW, SAMPLE, drop_ball  # noqa: E402
from sticky import period_segments, players_by_team, runs, sticky_labels  # noqa: E402
from baseline import write_submission  # noqa: E402

# Params. Picked on the practice match (allowed: it's another game).
SPEED_MS = 1.25
WINDOW_FRAMES = 25
MIN_DEAD_FRAMES = 75    # 3 s
MIN_ALIVE_FRAMES = 50   # 2 s


def mean_player_speed(df, player_ids, pitch=PITCH):
    """Per-frame average speed of all visible players, m/s."""
    x = df[[i + "_x" for i in player_ids]].to_numpy() * pitch[0]
    y = df[[i + "_y" for i in player_ids]].to_numpy() * pitch[1]
    step = np.sqrt(np.diff(x, axis=0, prepend=np.nan) ** 2 +
                   np.diff(y, axis=0, prepend=np.nan) ** 2)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # frames with nobody tracked -> NaN
        return np.nanmean(step, axis=1) * 25.0


def dead_from_players(df, player_ids, segments, speed=SPEED_MS, window=WINDOW_FRAMES,
                      min_dead=MIN_DEAD_FRAMES, min_alive=MIN_ALIVE_FRAMES, pitch=PITCH):
    raw = mean_player_speed(df, player_ids, pitch)
    dead = np.zeros(len(df), dtype=bool)
    for start, stop in segments:
        s = pd.Series(raw[start:stop]).rolling(window, center=True, min_periods=1).median()
        d = (s < speed).to_numpy().copy()  # NaN (nobody tracked) compares False: live
        for a, b in runs(~d):        # fill short live gaps inside stoppages
            if b - a < min_alive and a > 0 and b < len(d):
                d[a:b] = True
        for a, b in runs(d):         # drop stoppages too short to be real
            if b - a < min_dead:
                d[a:b] = False
        dead[start:stop] = d
    return dead


def main():
    from kloppy import metrica

    ds = metrica.load_tracking_epts(meta_data=META, raw_data=RAW)
    df = ds.to_df()
    segments = period_segments(df)
    teams = players_by_team(ds)
    dead = dead_from_players(df, sum(teams, []), segments)  # players only: same for both sets

    gt = pd.read_csv(os.path.join(SAMPLE, "sample_gt.csv"))["label"].to_numpy()
    alive = np.isin(gt, ["H", "A"])
    for folder, frame in (("results", df), ("results_noisy", drop_ball(df, alive))):
        path = os.path.join(SAMPLE, folder, "sticky_stoppage.csv")
        write_submission(path, sticky_labels(frame, teams, segments, "closest", dead=dead))
        print("wrote", path)


if __name__ == "__main__":
    main()
