"""Test bench: 8 practice games with the ball lost the way our real match loses it.

Games: Metrica Sample Game 3 + 7 Bundesliga (experiments/ahmed/bundesliga.py). Answer keys come
from each game's own events / provider flags, never from our match.

"Real-like" ball (measured on our match, Nov 13, see docs/notes.md):
  - the ball is missing on ~41% of graded frames: ~72% of stoppage frames, ~15% of live frames
  - no gaps between 1 s and 5 s: the tracker fills short losses with a straight line
  - in live play, gaps start 5x more often near a line; they last 5-25 s
So: hide 75% of stoppages whole (seeded), add live gaps with the real lengths, more likely near
lines, until 15% of live frames are hidden, then fill every gap under 5 s with a straight line.

Fake Smart Tagging: a set piece tag for a random 55% of restarts (59 tags vs ~110 stoppages on
our match), starting 3-6 s before the restart.

    python experiments/ahmed/bench.py             # scores every approach, game by game
    python experiments/ahmed/bench.py --hard      # harsher: gap edges off by up to 3 s, tags only near lines/box
"""

import glob
import os
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [HERE, os.path.join(ROOT, "prep"), os.path.join(ROOT, "starter")]
from ball_out import dead_from_ball_out  # noqa: E402
from baseline import write_submission  # noqa: E402
from sticky import period_segments, players_by_team, runs, sticky_labels  # noqa: E402
from stoppage import dead_from_players  # noqa: E402
from stop_fixes import dead_before_restart, drop_short  # noqa: E402
from tags import QUIET_AFTER_RESTART, dead_from_restarts, restart_team  # noqa: E402

CACHE = os.path.join(ROOT, "data", "cache")
OUT = os.path.join(ROOT, "data", "bench")
LIVE_GAPS = [129, 132, 132, 132, 134, 136, 144, 146, 146, 149, 152, 164, 169, 176, 177, 182, 183, 187,
             190, 194, 207, 223, 229, 234, 240, 245, 268, 269, 289, 289, 297, 319, 406, 511, 521, 558,
             604, 611, 743, 1124]  # real live-play gap lengths (frames) on our match
DEAD_HIDDEN = 0.75
LIVE_HIDDEN = 0.15
FILL_UNDER = 125
TAG_SHARE = 0.55


def load_games():
    games = {}
    path = os.path.join(CACHE, "metrica3.pkl")
    if not os.path.exists(path):
        from kloppy import metrica
        from sample_game import META, RAW, SAMPLE

        ds = metrica.load_tracking_epts(meta_data=META, raw_data=RAW)
        df = ds.to_df()
        gt = pd.read_csv(os.path.join(SAMPLE, "sample_gt.csv"))["label"].to_numpy()
        pickle.dump((df, players_by_team(ds), gt, (105.0, 68.0)), open(path, "wb"))
    games["metrica3"] = pickle.load(open(path, "rb"))
    from bundesliga_data import games as bundesliga_games

    games.update(bundesliga_games())
    return games


HARD = "--hard" in sys.argv  # gap edges off the stoppage edges by up to 3 s; tags only near lines/box


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


NO_TEAM = 0.45  # throw-ins: 26 of 59 real tags have no team


def fake_tags(gt, segments, seed=0, df=None, pitch=None, hard=False):
    """[(tag start, is_kickoff)], [team or None].

    hard: like the real tags, only restarts near a line or in a box (throw-ins, corners, goal
    kicks), almost no free kicks in midfield. Ball position at the restart from the clean data.
    """
    rng = np.random.default_rng(seed + 1)
    tags, teams = [], []
    dead = gt == "D"
    if hard:
        x, y = df["ball_x"].to_numpy() * pitch[0], df["ball_y"].to_numpy() * pitch[1]
    for a, b in segments:
        for s, e in runs(dead[a:b]):
            r = a + e
            if hard and r < b:
                with np.errstate(invalid="ignore"):
                    edge = min(x[r], pitch[0] - x[r], y[r], pitch[1] - y[r]) < 3 or \
                        x[r] < 16.5 or x[r] > pitch[0] - 16.5
                if not edge:
                    continue
            if r < b and rng.random() < (0.8 if hard else TAG_SHARE):
                tags.append((int(r - rng.integers(75, 150)), False))
                teams.append(None if rng.random() < NO_TEAM or gt[r] not in ("H", "A") else gt[r])
    return tags, teams


def approaches(frame, teams, segments, pitch, tags):
    """yield name, dead, post (labels -> labels)."""
    tag_list, tag_teams = tags
    players = sum(teams, [])
    speed = dead_from_players(frame, players, segments, pitch=pitch)
    out = dead_from_ball_out(frame, segments, pitch=pitch)
    restart, rframes = dead_from_restarts(frame, pitch, tag_list, with_frames=True)
    keep = lambda x: x  # noqa: E731
    yield "row8", out | speed, keep
    yield "row9", drop_short(out | speed | dead_before_restart(frame, segments), segments), keep
    row10 = drop_short(out | speed | dead_before_restart(frame, segments), segments) | restart
    yield "row10_restarts", row10, keep
    yield "row10_team", row10, lambda lab: restart_team(lab, rframes, tag_teams)
    quiet = speed.copy()
    for r in rframes:
        quiet[r:r + QUIET_AFTER_RESTART] = False
    row10q = drop_short(out | quiet | dead_before_restart(frame, segments), segments) | restart
    yield "row10_quiet", row10q, keep
    yield "row10_quiet_team", row10q, lambda lab: restart_team(lab, rframes, tag_teams)
    yield "row11", row10q, lambda lab: restart_team(lab, rframes, tag_teams)
    yield "row11_throw", row10q, lambda lab: throw_team(lab, rframes, tag_teams)


def throw_team(lab, rframes, tag_teams):
    import tags

    tags.THROW_IN_GUESS = True
    try:
        return restart_team(lab, rframes, tag_teams)
    finally:
        tags.THROW_IN_GUESS = False


ROW11 = {"ZONE_M": 1.5, "MARGIN_M": 0.5}  # now the defaults in prep/sticky.py
BEFORE_ROW11 = {"ZONE_M": 2.0, "MARGIN_M": 1.0}


def main():
    import sticky

    default = BEFORE_ROW11
    games = load_games()
    rows = []
    for g, (df, teams, gt, pitch) in games.items():
        segments = period_segments(df)
        frame = real_like_ball(df, gt, pitch, segments, hard=HARD)
        tags = fake_tags(gt, segments, df=df, pitch=pitch, hard=HARD)
        folder = os.path.join(OUT + ("_hard" if HARD else ""), g)
        os.makedirs(os.path.join(folder, "results"), exist_ok=True)
        write_submission(os.path.join(folder, "gt.csv"), gt)
        print(g, "ball missing: dead {:.0%} live {:.0%}  tags {}".format(
            np.isnan(frame.ball_x.to_numpy())[gt == "D"].mean(),
            np.isnan(frame.ball_x.to_numpy())[np.isin(gt, ["H", "A"])].mean(), len(tags[0])), flush=True)
        for name, dead, post in approaches(frame, teams, segments, pitch, tags):
            for k, v in (ROW11 if name.startswith("row11") else default).items():
                setattr(sticky, k, v)
            labels = post(sticky_labels(frame, teams, segments, "closest", dead=dead, pitch=pitch))
            write_submission(os.path.join(folder, "results", name + ".csv"), labels)
        subprocess.run([sys.executable, os.path.join(ROOT, "evaluation", "run_evaluation.py"), "--gt",
                        os.path.join(folder, "gt.csv"), "--results", os.path.join(folder, "results"),
                        "--out", os.path.join(folder, "eval")], check=True, capture_output=True)
        s = pd.read_csv(os.path.join(folder, "eval", "scoreboard.csv"))
        for r in s.itertuples():
            rows.append({"game": g, "approach": r.submission, "spellF1": r.spell_f1_mean, "macroF1": r.macro_f1})
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(OUT, "scores_hard.csv" if HARD else "scores.csv"), index=False)
    p = t.pivot_table(index="game", columns="approach", values="spellF1")
    print(p.round(3))
    print("mean", p.mean().round(3).to_dict())
    for c in p.columns:
        if c != "row8":
            print(c, "beats row8 on {}/{} games".format(int((p[c] > p["row8"]).sum()), len(p)))


if __name__ == "__main__":
    main()
