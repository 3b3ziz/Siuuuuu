"""Sweep the "who has the ball" settings on the 8-game bench, with row 10's stoppages fixed.

    python experiments/ahmed/sweep_team.py

SWITCH_FRAMES: frames the other team must be on the ball before we switch.
ZONE_M / MARGIN_M: a team is "on the ball" when its closest player is within ZONE_M of the ball
and at least MARGIN_M closer than the nearest opponent.
"""

import itertools
import os
import shutil
import subprocess
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [HERE]
import bench  # noqa: E402
import sticky  # noqa: E402
from baseline import write_submission  # noqa: E402

GRID = {"SWITCH_FRAMES": [4, 6, 8], "ZONE_M": [1.5, 2.0], "MARGIN_M": [0.5, 1.0]}


def main():
    games = bench.load_games()
    rows = []
    for g, (df, teams, gt, pitch) in games.items():
        segments = sticky.period_segments(df)
        frame = bench.real_like_ball(df, gt, pitch, segments)
        tags = bench.fake_tags(gt, segments)
        dead, post = [(d, p) for n, d, p in bench.approaches(frame, teams, segments, pitch, tags)
                      if n == "row10_quiet_team"][0]
        folder = os.path.join(bench.OUT, "sweep", g)
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(os.path.join(folder, "results"))
        write_submission(os.path.join(folder, "gt.csv"), gt)
        for values in itertools.product(*GRID.values()):
            for k, v in zip(GRID, values):
                setattr(sticky, k, v)
            name = "s{}_z{}_m{}".format(*values)
            labels = post(sticky.sticky_labels(frame, teams, segments, "closest", dead=dead, pitch=pitch))
            write_submission(os.path.join(folder, "results", name + ".csv"), labels)
        subprocess.run([sys.executable, os.path.join(ROOT, "evaluation", "run_evaluation.py"), "--gt",
                        os.path.join(folder, "gt.csv"), "--results", os.path.join(folder, "results"),
                        "--out", os.path.join(folder, "eval")], check=True, capture_output=True)
        s = pd.read_csv(os.path.join(folder, "eval", "scoreboard.csv"))
        for r in s.itertuples():
            rows.append({"game": g, "setting": r.submission, "spellF1": r.spell_f1_mean})
        print(g, "done", flush=True)
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(bench.OUT, "sweep_scores.csv"), index=False)
    p = t.pivot_table(index="setting", columns="game", values="spellF1")
    base = p.loc["s8_z2.0_m1.0"]
    p["mean"] = p.mean(axis=1)
    p["wins_vs_current"] = (p.drop(columns="mean").gt(base, axis=1)).sum(axis=1)
    print(p.sort_values("mean", ascending=False)[["mean", "wins_vs_current"]].round(4))


if __name__ == "__main__":
    main()
