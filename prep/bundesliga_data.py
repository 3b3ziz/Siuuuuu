"""7 free Bundesliga games (DFL / IDSSE open data, CC-BY 4.0), as practice data and training data.

Get them from huggingface.co/datasets/pysport/idsse-data into data/bundesliga/ (figshare blocks
scripts). Answer key = DFL's own per-frame flags: ball dead -> D, else the ball-owning team.
"""

import glob
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from sticky import players_by_team  # noqa: E402

DATA = os.path.join(ROOT, "data", "bundesliga")
CACHE = os.path.join(ROOT, "data", "cache")


def load(match):
    from kloppy import sportec

    raw = glob.glob(os.path.join(DATA, "DFL_04_03_positions_raw_observed_*{}.xml".format(match)))[0]
    meta = glob.glob(os.path.join(DATA, "DFL_02_01_matchinformation_*{}.xml".format(match)))[0]
    ds = sportec.load_tracking(raw_data=raw, meta_data=meta, coordinates="kloppy", only_alive=False)
    df = ds.to_df()
    pitch = (ds.metadata.pitch_dimensions.pitch_length, ds.metadata.pitch_dimensions.pitch_width)
    return ds, df.reset_index(drop=True), pitch


def answer_key(ds, df):
    home = ds.metadata.teams[0].team_id
    owner = df["ball_owning_team_id"].astype(str).to_numpy()
    alive = (df["ball_state"].astype(str).str.lower().str.contains("alive")).to_numpy()
    return np.where(~alive, "D", np.where(owner == str(home), "H", "A"))


def games():
    """{"bl_<match>": (df, teams, answer key, pitch)}, cached in data/cache (loading takes minutes)."""
    out = {}
    for raw in sorted(glob.glob(os.path.join(DATA, "DFL_04_*.xml"))):
        m = raw.split("DFL-MAT-")[1][:-4]
        path = os.path.join(CACHE, "bl_{}.pkl".format(m))
        if not os.path.exists(path):
            ds, df, pitch = load(m)
            teams = [[p for p in t if p + "_x" in df.columns] for t in players_by_team(ds)]
            pickle.dump((df, teams, answer_key(ds, df), pitch), open(path, "wb"))
        out["bl_" + m] = pickle.load(open(path, "rb"))
    return out
