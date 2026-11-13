"""Our current best approach (row 12 in docs/notes.md) on the real match: data in, submission out.

    python prep/run_real.py                 # writes evaluation/results/<name>.csv, checks, scores
    python prep/run_real.py --name try2     # pick the file name

Steps:
  1. Load the tracking with the starter's loader (starter/load_atd.py, via kloppy). Takes a few
     minutes: 199,319 frames.
  2. Stoppages: the ball leaves the pitch (prep/ball_out.py), the players slow down
     (prep/stoppage.py, silenced for 10 s after each tagged restart), or the ball reappears outside
     after being missing (prep/stop_fixes.py); then stoppages under 2 s are dropped. Added from the
     automatic tags (prep/tags.py): each set piece back to where play stopped, each goal until the
     kickoff, before each half's kickoff, and frames with under 10 players tracked.
     Team: sticky possession ("closest" rule, prep/sticky.py); the team taking a tagged set piece
     gets the first bit after it. A switch hidden in a ball-missing stretch goes halfway into it,
     and possessions under 1 s go to the team before (prep/team_fixes.py).
  3. X before kickoff, at halftime and after the final whistle (never graded).
  4. Run the official validator, then score against the public 5 minutes. That score is a
     sanity check only, never a way to pick between versions (RULES.md).
  5. Print ballpark checks against general football stats (docs/notes.md).
"""

import argparse
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, ROOT, os.path.join(ROOT, "starter")]
from games import GAME, GAMES, half_video_blocks, source_frames  # noqa: E402
from ball_out import dead_from_ball_out  # noqa: E402
from baseline import write_submission  # noqa: E402
from stoppage import dead_from_players  # noqa: E402
from sticky import players_by_team, runs, sticky_labels  # noqa: E402
from team_fixes import gap_switch, merge_short  # noqa: E402
from stop_fixes import dead_before_restart, drop_short  # noqa: E402
from tags import (QUIET_AFTER_RESTART, dead_after_goals, dead_at_edges, dead_from_restarts,  # noqa: E402
                  restart_team, tag_inputs)


def load_frames(game=GAME):
    """Tracking as a DataFrame with exactly one row per video frame (row i = video frame i)."""
    import load_atd

    ds = load_atd.load(game)
    df = ds.to_df()
    n = source_frames("tactical", game)
    # ATD frame_id counts from 1, video frames from 0 (DATA.md). Reindex so nothing can shift.
    df = df.set_index("frame_id").reindex(range(1, n + 1)).reset_index()
    return ds, df


def predict(ds, df, segments, pitch):
    teams = players_by_team(ds)
    restarts, restart_teams, kickoffs, goals = tag_inputs()
    restart_dead, rframes = dead_from_restarts(df, pitch, restarts, with_frames=True)
    speed = dead_from_players(df, sum(teams, []), segments, pitch=pitch)
    for r in rframes:
        speed[r:r + QUIET_AFTER_RESTART] = False
    dead = drop_short(dead_from_ball_out(df, segments, pitch=pitch) | speed | dead_before_restart(df, segments),
                      segments)
    dead = dead | restart_dead | dead_after_goals(df, goals) | dead_at_edges(df, segments, kickoffs)
    labels = sticky_labels(df, teams, segments, "closest", dead=dead, pitch=pitch)
    labels = restart_team(labels, rframes, restart_teams)
    labels = merge_short(gap_switch(labels, df["ball_x"].notna().to_numpy()))
    graded = np.zeros(len(labels), dtype=bool)
    for a, b in segments:
        graded[a:b] = True
    return np.where(graded, labels, "X")


def ballpark(labels, segments):
    graded = np.zeros(len(labels), dtype=bool)
    for a, b in segments:
        graded[a:b] = True
    lab = labels[graded]
    n_stop = sum(len(runs(labels[a:b] == "D")) for a, b in segments)
    n_poss = sum(len(runs(labels[a:b] == t)) for a, b in segments for t in "HA")
    print("ballpark checks (general football stats, docs/notes.md):")
    print("  stoppage share {:.0%}   expect ~40-48%".format((lab == "D").mean()))
    print("  stoppages      {}     expect ~110".format(n_stop))
    print("  possessions    {}     practice match had 381, public 5 min had 17".format(n_poss))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="ours_row12")
    args = parser.parse_args()

    segments = [(first, last + 1) for _, first, last in half_video_blocks(GAME)]
    pitch = GAMES[GAME]["pitch"]
    print("loading tracking (a few minutes) ...")
    ds, df = load_frames()
    labels = predict(ds, df, segments, pitch)

    out = os.path.join(ROOT, "evaluation", "results", args.name + ".csv")
    write_submission(out, labels)
    print("wrote", out)
    ballpark(labels, segments)
    for script in (["validate_submission.py", out], ["run_evaluation.py"]):
        subprocess.run([sys.executable, os.path.join(ROOT, "evaluation", script[0])] + script[1:],
                       check=False)


if __name__ == "__main__":
    main()
