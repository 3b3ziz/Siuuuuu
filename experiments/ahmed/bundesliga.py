"""More practice matches: 7 free Bundesliga games (DFL / IDSSE open data, CC-BY 4.0).

The tracking carries the provider's own per-frame flags: ball alive/dead and which team has the
ball. That is our answer key: dead -> D, else H/A from the possession flag. It is DFL's idea of
possession, not the organisers', so use these games to see whether a change helps across many
matches (luck vs real), not to copy their exact timing.

Unlike our match, DFL tracks the ball almost all the time, also during stoppages. The "noisy"
version hides it in random gaps like the practice match (prep/sample_game.py: drop_ball).

    python experiments/ahmed/bundesliga.py     # needs data/bundesliga/*.xml (from huggingface.co/datasets/pysport/idsse-data)

Writes data/bundesliga/<match>/{gt.csv, results/, results_noisy/}, scores each, and prints a table.
"""

import glob
import os
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(ROOT, "prep"), os.path.join(ROOT, "starter")]
from ball_out import dead_from_ball_out  # noqa: E402
from baseline import write_submission  # noqa: E402
from sample_game import drop_ball  # noqa: E402
from sticky import period_segments, players_by_team, sticky_labels  # noqa: E402
from stoppage import dead_from_players  # noqa: E402
from stop_fixes import dead_before_restart, drop_short  # noqa: E402

from bundesliga_data import DATA, answer_key, load  # noqa: E402,F401


def approaches(frame, teams, segments, pitch):
    speed = dead_from_players(frame, sum(teams, []), segments, pitch=pitch)
    base = dead_from_ball_out(frame, segments, pitch=pitch) | speed
    fixed = drop_short(base | dead_before_restart(frame, segments), segments)
    for name, dead in (("row8", base), ("row9", fixed)):
        yield name, sticky_labels(frame, teams, segments, "closest", dead=dead, pitch=pitch)


def main():
    matches = sorted({f.split("DFL-MAT-")[1][:-4] for f in glob.glob(os.path.join(DATA, "DFL_04_*.xml"))})
    table = []
    for m in matches:
        ds, df, pitch = load(m)
        segments = period_segments(df)
        # squad players who never came on have no columns
        teams = [[p for p in t if p + "_x" in df.columns] for t in players_by_team(ds)]
        gt = answer_key(ds, df)
        out = os.path.join(DATA, m)
        os.makedirs(out, exist_ok=True)
        write_submission(os.path.join(out, "gt.csv"), gt)
        alive = np.isin(gt, ["H", "A"])
        print(m, "frames", len(df), "dead {:.0%}".format((gt == "D").mean()),
              "ball seen {:.0%}".format(df["ball_x"].notna().mean()), flush=True)
        for folder, frame in (("results", df), ("results_noisy", drop_ball(df, alive))):
            os.makedirs(os.path.join(out, folder), exist_ok=True)
            for name, labels in approaches(frame, teams, segments, pitch):
                write_submission(os.path.join(out, folder, name + ".csv"), labels)
            subprocess.run([sys.executable, os.path.join(ROOT, "evaluation", "run_evaluation.py"),
                            "--gt", os.path.join(out, "gt.csv"), "--results", os.path.join(out, folder),
                            "--out", os.path.join(out, "eval_" + folder)],
                           check=True, capture_output=True)
            s = pd.read_csv(os.path.join(out, "eval_" + folder, "scoreboard.csv"))
            for _, r in s.iterrows():
                table.append({"match": m, "ball": folder, "approach": r.submission, "spellF1": r.spell_f1_mean})
    t = pd.DataFrame(table)
    t.to_csv(os.path.join(DATA, "scores.csv"), index=False)
    print(t.pivot_table(index=["match"], columns=["ball", "approach"], values="spellF1").round(3))
    print(t.groupby(["ball", "approach"]).spellF1.mean().round(3))


if __name__ == "__main__":
    main()
