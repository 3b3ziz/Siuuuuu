"""A practice match we are allowed to tune on: Metrica's public Sample Game 3.

Builds a frame-by-frame answer key for it from its event data, in exactly the format of the
challenge's ground truth, then runs the challenge baseline on it so the official scorer can grade
it. Nothing here touches the challenge match.

    python prep/sample_game.py            # answer key + baseline on clean and noisy ball
    python evaluation/run_evaluation.py --gt data/sample/sample_gt.csv \
        --results data/sample/results --out data/sample/eval

Download first (not committed, data/ is gitignored):
    https://github.com/metrica-sports/sample-data/tree/master/data/Sample_Game_3

Answer-key rules (our reading of the challenge's definition, applied to events):
  - SET PIECE starts play; that team has the ball.
  - PASS / CARRY / RECOVERY / SHOT give the ball to the event's team.
  - CHALLENGE and BALL LOST change nothing on their own (a duel is not control; the switch
    happens at the other team's next RECOVERY / PASS / CARRY).
  - BALL OUT kills play at its end frame, FAULT RECEIVED at its start frame, a GOAL at its end.
  - Any SET PIECE also means play was dead from the previous event's end (catches offsides
    and fouls the event data never logged).
  - Before a period's first event and after its last: X (not graded).
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "starter"))
from baseline import smooth, write_submission  # noqa: E402

SAMPLE = os.path.join(ROOT, "data", "sample")
META = os.path.join(SAMPLE, "Sample_Game_3_metadata.xml")
RAW = os.path.join(SAMPLE, "Sample_Game_3_tracking.txt")
EVENTS = os.path.join(SAMPLE, "Sample_Game_3_events.json")
PITCH = (105.0, 68.0)

GIVES_BALL = {"SET PIECE", "PASS", "CARRY", "RECOVERY", "SHOT"}
HOME, AWAY, NOBODY = 0, 1, -1


def subtype_names(event):
    sub = event.get("subtypes")
    if isinstance(sub, dict):
        return {sub["name"]}
    if isinstance(sub, list):
        return {s["name"] for s in sub}
    return set()


def answer_key(events, n_frames, home_team):
    """Per-frame 'H' / 'A' / 'D' / 'X' from the event list. Frame f -> row f - 1."""
    labels = np.full(n_frames, "X", dtype="<U1")
    for period in sorted({e["period"] for e in events}):
        evs = sorted((e for e in events if e["period"] == period), key=lambda e: e["start"]["frame"])
        changes = []  # (row, label)
        prev_end = None
        for e in evs:
            kind = e["type"]["name"]
            start, end = e["start"]["frame"] - 1, e["end"]["frame"] - 1
            if kind == "SET PIECE" and prev_end is not None and prev_end < start:
                # A restart means play was stopped, even with no foul or ball-out logged before
                # it (offsides, unlogged fouls). Dead from the previous event's end.
                changes.append((prev_end, "D"))
            prev_end = end
            if kind in GIVES_BALL:
                changes.append((start, "H" if e["team"]["name"] == home_team else "A"))
            if kind == "FAULT RECEIVED":
                changes.append((start, "D"))
            if kind == "BALL OUT" or (kind == "SHOT" and "GOAL" in subtype_names(e)):
                changes.append((end, "D"))
        changes.sort(key=lambda c: c[0])
        last = max(e["end"]["frame"] - 1 for e in evs)
        for (row, label), nxt in zip(changes, changes[1:] + [(last + 1, None)]):
            labels[row:max(row, nxt[0])] = label
    return labels


def nearest_player_codes(df, team_of_column):
    """Baseline step 1, vectorised: team of the closest player to the ball, NOBODY if no ball."""
    cols = list(team_of_column)
    px = df[[c + "_x" for c in cols]].to_numpy() * PITCH[0]
    py = df[[c + "_y" for c in cols]].to_numpy() * PITCH[1]
    bx = df["ball_x"].to_numpy()[:, None] * PITCH[0]
    by = df["ball_y"].to_numpy()[:, None] * PITCH[1]
    dist = np.where(np.isnan(px), np.inf, (px - bx) ** 2 + (py - by) ** 2)
    teams = np.array([team_of_column[c] for c in cols], dtype=np.int8)
    codes = teams[np.argmin(dist, axis=1)]
    codes[np.isnan(df["ball_x"].to_numpy()) | np.all(np.isinf(dist), axis=1)] = NOBODY
    return codes


def drop_ball(df, alive, target_visible=0.593, mean_gap_s=2.0, seed=0):
    """Copy of df with the ball blanked in random gaps until ~59% of alive frames show it.

    59.3% is the challenge match's ball visibility on graded frames (DATA.md). Gaps are
    contiguous, exponential in length, because the real tracker loses the ball for stretches,
    not single frames. Seeded, so the file is the same every run.
    """
    rng = np.random.default_rng(seed)
    ball = ~np.isnan(df["ball_x"].to_numpy())
    keep = ball.copy()
    n = len(df)
    while keep[alive].mean() > target_visible:
        start = rng.integers(0, n)
        length = max(1, int(rng.exponential(mean_gap_s * 25)))
        keep[start:start + length] = False
    out = df.copy()
    out.loc[~keep, ["ball_x", "ball_y"]] = np.nan
    return out


def main():
    from kloppy import metrica

    ds = metrica.load_tracking_epts(meta_data=META, raw_data=RAW)
    df = ds.to_df()
    home, away = ds.metadata.teams
    team_of_column = {p.player_id: (HOME if team is home else AWAY)
                      for team in (home, away) for p in team.players}
    frames = df["frame_id"].to_numpy()
    assert frames[0] == 1 and np.all(np.diff(frames) == 1), "tracking frames not contiguous"
    n = len(df)

    with open(EVENTS) as handle:
        events = json.load(handle)["data"]
    gt = answer_key(events, n, home_team=home.name)
    write_submission(os.path.join(SAMPLE, "sample_gt.csv"), gt)

    graded = gt != "X"
    alive = np.isin(gt, ["H", "A"])
    ball = ~np.isnan(df["ball_x"].to_numpy())
    print("home = {}, away = {}".format(home.name, away.name))
    print("frames {}  graded {}  ball visible on alive frames {:.1%}".format(
        n, graded.sum(), ball[alive].mean()))

    noisy = drop_ball(df, alive)
    print("after fake dropouts: ball visible on alive frames {:.1%}".format(
        (~np.isnan(noisy["ball_x"].to_numpy()))[alive].mean()))

    for folder, frame in (("results", df), ("results_noisy", noisy)):
        codes = nearest_player_codes(frame, team_of_column)
        for name, window in (("baseline_raw", 0), ("baseline_smooth25", 25),
                             ("baseline_smooth50", 50), ("baseline_smooth125", 125)):
            write_submission(os.path.join(SAMPLE, folder, name + ".csv"), smooth(codes, window))
    print("wrote answer key, clean and noisy baseline predictions under", SAMPLE)


if __name__ == "__main__":
    main()
