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

MIN_STOP_S = 6.0  # was 2.0 before row 17
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


# Row 18: the restart kick (experiments/ahmed/idea_restart_kick.py). A stoppage ends when a ball
# that was still or unseen for a second is struck (over 4 m/s). Each rule-made stoppage's end
# moves to the first such kick from 3 s before to 10 s after it; a ball seen still for 2 s+ and
# then kicked within 1 s was dead until the kick.
FPS = 25
LAG = 5          # ball speed measured over 0.2 s
KICK_MS = 4.0
SLOW_MS = 1.0
STILL_MS = 0.5


def ball_speed(df, pitch):
    """m/s over the next LAG frames, NaN if either end is hidden."""
    x = df["ball_x"].to_numpy() * pitch[0]
    y = df["ball_y"].to_numpy() * pitch[1]
    v = np.full(len(x), np.nan)
    v[:-LAG] = np.hypot(x[LAG:] - x[:-LAG], y[LAG:] - y[:-LAG]) * FPS / LAG
    return v


def kick_frames(v, fast=KICK_MS, slow=SLOW_MS, pre=FPS):
    """Frames where the ball goes fast after a second of being slow or unseen."""
    with np.errstate(invalid="ignore"):
        isfast = v > fast
        notslow = v > slow  # NaN (unseen) counts as slow
    cs = np.concatenate([[0], np.cumsum(notslow)])
    t = np.flatnonzero(isfast)
    t = t[t >= pre]
    return t[(cs[t] - cs[t - pre]) == 0]


def kick_ends(dead, segments, kicks, lo=3 * FPS, hi=10 * FPS):
    """Move each stoppage's end to the first kick in [end - lo, end + hi] (never before start + 1 s)."""
    dead = dead.copy()
    for a, b in segments:
        for s, e in runs(dead[a:b]):
            s, e = a + s, a + e
            i = np.searchsorted(kicks, max(s + FPS, e - lo))
            if i < len(kicks) and kicks[i] <= min(e + hi, b - 1):
                k = kicks[i]
                if k < e:
                    dead[k:e] = False
                else:
                    dead[e:k] = True
    return dead


def still_then_kick(v, segments, n=2 * FPS, still=STILL_MS, gap=FPS):
    """Ball seen still for n+ frames, then a kick within `gap` frames: dead from the still start to the kick."""
    with np.errstate(invalid="ignore"):
        st = v < still
        fast = v > KICK_MS
    out = np.zeros(len(v), dtype=bool)
    for a, b in segments:
        for s, e in runs(st[a:b]):
            s, e = a + s, a + e
            if e - s < n:
                continue
            f = np.flatnonzero(fast[e:min(e + gap, b)])
            if len(f):
                out[s:e + f[0]] = True
    return out


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
