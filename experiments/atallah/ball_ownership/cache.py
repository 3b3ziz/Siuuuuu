"""Practice match (Metrica Sample Game 3) loaded once, cached under data/sample/cache/.

    uv run --with numpy --with pandas --with kloppy --with scipy \
        python experiments/atallah/ball_ownership/cache.py [--force]

The kloppy load takes about a minute; load_practice() from the cache takes a second or two.
Nothing here prints frame contents, only counts.
"""

import argparse
import json
import os
import pickle
import time
from collections import namedtuple

import numpy as np
import pandas as pd

import _paths
import possession_metrics as pm
import sample_game
from ball_out import dead_from_ball_out
from stoppage import dead_from_players
from sticky import period_segments, players_by_team

CACHE = os.path.join(sample_game.SAMPLE, "cache")
GT_CSV = os.path.join(sample_game.SAMPLE, "sample_gt.csv")
FILES = {
    "clean": os.path.join(CACHE, "clean.pkl"),
    "noisy": os.path.join(CACHE, "noisy.pkl"),
    "masks": os.path.join(CACHE, "masks.npz"),
    "teams": os.path.join(CACHE, "teams.json"),
}

Practice = namedtuple("Practice", "name df_clean df_noisy gt_labels gt_codes runs segments teams dead pitch")


def gt_labels():
    """The answer key as a '<U1' array, straight from sample_gt.csv."""
    return pd.read_csv(GT_CSV, dtype={"label": "object"})["label"].to_numpy().astype("<U1")


def cached():
    return all(os.path.isfile(p) for p in FILES.values())


def build(force=False):
    """Load Sample Game 3 with kloppy, derive the noisy copy and the dead masks, write the cache."""
    if cached() and not force:
        return
    from kloppy import metrica

    os.makedirs(CACHE, exist_ok=True)
    t0 = time.time()
    ds = metrica.load_tracking_epts(meta_data=sample_game.META, raw_data=sample_game.RAW)
    df = ds.to_df()
    print("kloppy load: {} frames in {:.0f} s".format(len(df), time.time() - t0))

    gt = gt_labels()
    assert len(gt) == len(df), "answer key has {} rows, tracking {}".format(len(gt), len(df))
    alive = np.isin(gt, ["H", "A"])
    noisy = sample_game.drop_ball(df, alive)     # seed 0, same call as prep/ball_out.py

    segments = period_segments(df)
    teams = players_by_team(ds)
    speed_dead = dead_from_players(df, sum(teams, []), segments)   # players only: same both sets
    dead_clean = dead_from_ball_out(df, segments) | speed_dead
    dead_noisy = dead_from_ball_out(noisy, segments) | speed_dead
    dead_oracle = gt == "D"

    df.to_pickle(FILES["clean"])
    noisy.to_pickle(FILES["noisy"])
    np.savez_compressed(FILES["masks"], clean=dead_clean, noisy=dead_noisy, oracle=dead_oracle)
    with open(FILES["teams"], "w") as handle:
        json.dump(teams, handle)
    print("cache written to {}: dead share clean {:.1%} noisy {:.1%} oracle {:.1%}".format(
        CACHE, dead_clean.mean(), dead_noisy.mean(), dead_oracle.mean()))


def load_practice():
    """Practice namedtuple from the cache (builds it first when missing)."""
    if not cached():
        build()
    df_clean = pd.read_pickle(FILES["clean"])
    df_noisy = pd.read_pickle(FILES["noisy"])
    masks = np.load(FILES["masks"])
    with open(FILES["teams"]) as handle:
        teams = json.load(handle)
    gt = gt_labels()
    gt_codes = pm.label_codes(gt)
    return Practice(
        name="practice",
        df_clean=df_clean,
        df_noisy=df_noisy,
        gt_labels=gt,
        gt_codes=gt_codes,
        runs=pm.valid_runs(gt_codes),
        segments=period_segments(df_clean),
        teams=teams,
        dead={"clean": masks["clean"].astype(bool), "noisy": masks["noisy"].astype(bool),
              "oracle": masks["oracle"].astype(bool)},
        pitch=sample_game.PITCH,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="rebuild even if the cache exists")
    args = parser.parse_args()
    build(force=args.force)
    t0 = time.time()
    S = load_practice()
    print("load_practice() from cache: {:.2f} s".format(time.time() - t0))
    print("frames {}  segments {}  teams {}+{} players  gt spells {}".format(
        len(S.df_clean), S.segments, len(S.teams[0]), len(S.teams[1]),
        len(pm.possession_spells(S.gt_codes, S.runs))))
    for k, m in S.dead.items():
        print("  dead[{}]: {} frames ({:.1%})".format(k, int(m.sum()), m.mean()))


if __name__ == "__main__":
    main()
