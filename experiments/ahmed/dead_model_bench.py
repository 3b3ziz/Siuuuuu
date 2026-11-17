"""Learned stoppage model on top of row 18: HGB P(dead) per frame, leave-one-game-out on the bench.
    python experiments/ahmed/dead_model.py <hard 0/1> <seed>
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(ROOT, "prep"), HERE]
from ball_model import CACHE, VERSION, blend_touch, lock_clear, viterbi  # noqa: E402
from fastbench import games, spell_f1  # noqa: E402
from idea_restart_kick import FPS, ball_speed, kick_ends, kick_frames, still_then_kick  # noqa: E402
from stop_fixes import drop_short  # noqa: E402
from stoppage import mean_player_speed  # noqa: E402
from sticky import sticky_labels  # noqa: E402
from tags import QUIET_AFTER_RESTART, restart_team  # noqa: E402
from team_fixes import merge_short, on_ball  # noqa: E402


def since(mask):
    out = np.zeros(len(mask))
    c = 500
    for i, m in enumerate(mask):
        c = 0 if m else min(c + 1, 500)
        out[i] = c
    return out


def feats(x, rule):
    df, pitch = x.df, x.pitch
    ms = pd.Series(mean_player_speed(df, sum(x.teams, []), pitch)).ffill().fillna(0)
    bx, by = df["ball_x"].to_numpy(), df["ball_y"].to_numpy()
    seen = ~np.isnan(bx)
    v = ball_speed(df, pitch)
    line = np.minimum(np.minimum(bx, 1 - bx) * pitch[0], np.minimum(by, 1 - by) * pitch[1])
    f = {}
    for w in (25, 75, 250):
        f["ms%d" % w] = ms.rolling(w, center=True, min_periods=1).mean().to_numpy()
        f["seen%d" % w] = pd.Series(seen.astype(float)).rolling(w, center=True, min_periods=1).mean().to_numpy()
    f["ms_past"] = ms.rolling(125, min_periods=1).mean().to_numpy()
    f["ms_fut"] = ms[::-1].rolling(125, min_periods=1).mean().to_numpy()[::-1]
    f["since"] = since(seen)
    f["until"] = since(seen[::-1])[::-1]
    f["v"] = np.nan_to_num(v, nan=-1)
    f["vmax25"] = pd.Series(v).rolling(25, center=True, min_periods=1).max().fillna(-1).to_numpy()
    f["line_last"] = pd.Series(line).ffill().fillna(-1).to_numpy()
    f["line_next"] = pd.Series(line).bfill().fillna(-1).to_numpy()
    f["rule"] = rule.astype(float)
    f["rule125"] = pd.Series(rule.astype(float)).rolling(125, center=True, min_periods=1).mean().to_numpy()
    f["tag"] = x.restart.astype(float)
    if os.environ.get("NOVIS"):
        for k in ("seen25", "seen75", "seen250", "since", "until"):
            f.pop(k)
    return pd.DataFrame(f)


hard, seed = bool(int(sys.argv[1])), int(sys.argv[2])
G = games(hard=hard, seed=seed)
P = pickle.load(open(os.path.join(CACHE, "ballmodel_p_{}_{}_{}.pkl".format("h" if hard else "n", seed, VERSION)), "rb"))
F, R18 = {}, {}
for g, x in G.items():
    quiet = x.speed.copy()
    for r in x.rframes:
        quiet[r:r + QUIET_AFTER_RESTART] = False
    v = ball_speed(x.df, x.pitch)
    raw = x.ball_out | quiet | x.before | still_then_kick(v, x.segments, 2 * FPS)
    rule = kick_ends(drop_short(raw, x.segments, 150), x.segments, kick_frames(v), 3 * FPS, 10 * FPS)
    R18[g] = rule | x.restart
    F[g] = feats(x, R18[g])
print("features done", flush=True)
out = {}
V = ("r18", "ml50", "ml65", "or65", "ml80")
bl = [g for g in G if g.startswith("bl_")]
for g, x in G.items():
    tr = [o for o in bl if o != g]
    X, y = [], []
    for o in tr:
        gt = G[o].gt
        keep = np.isin(gt, ["H", "A", "D"])
        idx = np.flatnonzero(keep)[::5]
        X.append(F[o].iloc[idx]); y.append(gt[idx] == "D")
    m = HistGradientBoostingClassifier(max_iter=200, random_state=0).fit(pd.concat(X), np.concatenate(y))
    p = pd.Series(m.predict_proba(F[g])[:, 1]).rolling(25, center=True, min_periods=1).mean().to_numpy()
    deads = {"r18": R18[g],
             "ml50": drop_short(p > .5, x.segments, 150) | x.restart,
             "ml65": drop_short(p > .65, x.segments, 150) | x.restart,
             "or65": R18[g] | drop_short(p > .65, x.segments, 150),
             "ml80": drop_short(p > .8, x.segments, 150) | x.restart}
    near = on_ball(x.df, x.teams, x.pitch)
    for k, dead in deads.items():
        base = restart_team(sticky_labels(x.df, x.teams, x.segments, "closest", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
        touch = restart_team(sticky_labels(x.df, x.teams, x.segments, "touch", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
        lab = restart_team(viterbi(lock_clear(blend_touch(P[g], touch), near), np.isin(base, ["H", "A"])), x.rframes, x.tag_teams)
        out[(g, k)] = spell_f1(x.gt, merge_short(lab, 0.8))
    print(g, " ".join("{}:{:.4f}".format(k, out[(g, k)]) for k in V), flush=True)
pickle.dump(out, open(os.path.join(os.environ.get("OUT", "."), ("dmnv_{}_{}.pkl" if os.environ.get("NOVIS") else "dm_{}_{}.pkl").format(int(hard), seed)), "wb"))
