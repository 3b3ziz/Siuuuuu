"""Idea: a long stretch with the ball hidden is evidence of a stoppage. Row 17 vs 4 gap rules, one bench run per call.
    python experiments/ahmed/idea_long_gap.py <hard 0/1> <seed>
Prints per game: row 17 score, each variant's score, and live (gt H/A) frames each variant newly makes dead.
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(ROOT, "prep"), HERE]
from ball_model import CACHE, VERSION, blend_touch, lock_clear, viterbi  # noqa: E402
from fastbench import games, spell_f1  # noqa: E402
from stop_fixes import drop_short  # noqa: E402
from sticky import runs, sticky_labels  # noqa: E402
from stoppage import mean_player_speed  # noqa: E402
from tags import QUIET_AFTER_RESTART, restart_team  # noqa: E402
from team_fixes import merge_short, on_ball  # noqa: E402


def long_gap_dead(df, segments, speed, min_s, max_speed=None, part=False):
    """Frames inside a ball-hidden stretch of min_s seconds or more. With max_speed: only gaps whose mean
    player speed is below it (part=False), or only the gap frames where the 2 s rolling median player
    speed is below it (part=True)."""
    seen = ~np.isnan(df["ball_x"].to_numpy())
    out = np.zeros(len(df), dtype=bool)
    for a, b in segments:
        smooth = pd.Series(speed[a:b]).rolling(50, center=True, min_periods=1).median().to_numpy()
        for s, e in runs(~seen[a:b]):
            if e - s < min_s * 25:
                continue
            if max_speed is None:
                out[a + s:a + e] = True
            elif part:
                out[a + s:a + e] = smooth[s:e] < max_speed
            elif np.nanmean(speed[a + s:a + e]) < max_speed:
                out[a + s:a + e] = True
    return out


VARIANTS = {
    "row17": None,
    "gap8": dict(min_s=8),
    "gap5_v2.5": dict(min_s=5, max_speed=2.5),
    "gap8_v2.0": dict(min_s=8, max_speed=2.0),
    "gap5_part2.5": dict(min_s=5, max_speed=2.5, part=True),
    # neighbours of the winner, only to check it is not a knife edge
    "gap8_v1.5": dict(min_s=8, max_speed=1.5),
    "gap8_v2.5": dict(min_s=8, max_speed=2.5),
    "gap12_v2.0": dict(min_s=12, max_speed=2.0),
    "gap5_v2.0": dict(min_s=5, max_speed=2.0),
}

if __name__ == "__main__":
    hard, seed = bool(int(sys.argv[1])), int(sys.argv[2])
    G = games(hard=hard, seed=seed)
    P = pickle.load(open(os.path.join(CACHE, "ballmodel_p_{}_{}_{}.pkl".format("h" if hard else "n", seed, VERSION)), "rb"))
    out = {}
    for g, x in G.items():
        quiet = x.speed.copy()
        after = np.zeros(len(x.df), dtype=bool)
        for r in x.rframes:
            after[r:r + QUIET_AFTER_RESTART] = True
        quiet &= ~after
        near = on_ball(x.df, x.teams, x.pitch)
        spd = mean_player_speed(x.df, sum(x.teams, []), x.pitch)
        livegt = np.isin(x.gt, ["H", "A"])
        dead17 = drop_short(x.ball_out | quiet | x.before, x.segments, 150) | x.restart
        for name, kw in VARIANTS.items():
            extra = np.zeros(len(x.df), dtype=bool) if kw is None else long_gap_dead(x.df, x.segments, spd, **kw) & ~after
            dead = drop_short(x.ball_out | quiet | x.before | extra, x.segments, 150) | x.restart
            base = restart_team(sticky_labels(x.df, x.teams, x.segments, "closest", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
            live = np.isin(base, ["H", "A"])
            touch = restart_team(sticky_labels(x.df, x.teams, x.segments, "touch", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
            lab = merge_short(restart_team(viterbi(lock_clear(blend_touch(P[g], touch), near), live), x.rframes, x.tag_teams))
            out[(g, name)] = (spell_f1(x.gt, lab), int((dead & ~dead17 & livegt).sum()), int((dead & ~dead17 & ~livegt).sum()), int(livegt.sum()))
        print(g, " ".join("{}:{:.4f}/{}".format(n, out[(g, n)][0], out[(g, n)][1]) for n in VARIANTS), flush=True)
    pickle.dump(out, open(os.path.join(os.environ.get("OUT", "."), "longgap_{}_{}.pkl".format(int(hard), seed)), "wb"))
