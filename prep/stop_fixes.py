"""Two stoppage fixes, from watching our real-match stoppages (data/clips, experiments/ahmed/make_clips.py).

  min_stop:  no real stoppage lasts under MIN_STOP_S. Our ball-out rule makes 0.1-0.3 s ones when
             the ball flickers just outside a line, and each one splits a real possession in two.
  restart:   the ball is missing, then reappears outside the pitch (corner, throw-in being taken)
             -> the whole missing stretch before it was a stoppage. Players move before a corner,
             so the speed rule ends the stoppage too early.

Scored on the practice match like row 8 (prep/ball_out.py).
    python prep/stop_fixes.py
then score data/sample/results{,_noisy} with evaluation/run_evaluation.py.
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, "starter")]
from ball_out import dead_from_ball_out  # noqa: E402
from baseline import write_submission  # noqa: E402
from sample_game import META, RAW, SAMPLE, drop_ball  # noqa: E402
from sticky import period_segments, players_by_team, runs, sticky_labels  # noqa: E402
from stoppage import dead_from_players  # noqa: E402

MIN_STOP_S = 2.0
MIN_GONE_FRAMES = 25  # ball missing at least 1 s before it reappears outside


def drop_short(dead, segments, min_frames=int(MIN_STOP_S * 25)):
    dead = dead.copy()
    for a, b in segments:
        for s, e in runs(dead[a:b]):
            if e - s < min_frames:
                dead[a + s:a + e] = False
    return dead


def dead_before_restart(df, segments, min_gone=MIN_GONE_FRAMES):
    bx, by = df["ball_x"].to_numpy(), df["ball_y"].to_numpy()
    seen = ~np.isnan(bx)
    with np.errstate(invalid="ignore"):
        outside = seen & ((bx < 0) | (bx > 1) | (by < 0) | (by > 1))
    dead = np.zeros(len(df), dtype=bool)
    for a, b in segments:
        for s, e in runs(~seen[a:b]):
            s, e = a + s, a + e
            if e - s >= min_gone and e < b and outside[e]:
                dead[s:e + 1] = True
    return dead


def main():
    from kloppy import metrica

    ds = metrica.load_tracking_epts(meta_data=META, raw_data=RAW)
    df = ds.to_df()
    segments = period_segments(df)
    teams = players_by_team(ds)
    speed = dead_from_players(df, sum(teams, []), segments)
    gt = pd.read_csv(os.path.join(SAMPLE, "sample_gt.csv"))["label"].to_numpy()
    alive = np.isin(gt, ["H", "A"])
    for folder, frame in (("results", df), ("results_noisy", drop_ball(df, alive))):
        base = dead_from_ball_out(frame, segments) | speed
        restart = dead_before_restart(frame, segments)
        for name, dead in (("fix_min_stop", drop_short(base, segments)),
                           ("fix_restart", base | restart),
                           ("fix_both", drop_short(base | restart, segments))):
            path = os.path.join(SAMPLE, folder, name + ".csv")
            write_submission(path, sticky_labels(frame, teams, segments, "closest", dead=dead))
            print("wrote", path)


if __name__ == "__main__":
    main()
