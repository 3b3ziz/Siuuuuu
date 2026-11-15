"""Fast in-process version of bench.py, for trying ideas quickly.

Same 8 games, same real-like ball (seed 0), same fake tags. Scores with the organisers' own
spell-F1 code (evaluation/possession_metrics.py), without writing CSVs.

    from fastbench import games, score
    prepared = games(hard=False)          # cached per game
    score(prepared, my_predict)           # my_predict(g) -> labels; prints per game + mean
"""

import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [HERE, os.path.join(ROOT, "prep"), os.path.join(ROOT, "starter"), os.path.join(ROOT, "evaluation")]
import bench  # noqa: E402
from possession_metrics import label_codes, spell_scores, valid_runs, fill_abstentions  # noqa: E402
from ball_out import dead_from_ball_out  # noqa: E402
from sticky import period_segments  # noqa: E402
from stoppage import dead_from_players  # noqa: E402
from stop_fixes import dead_before_restart, drop_short  # noqa: E402
from tags import QUIET_AFTER_RESTART, dead_from_restarts  # noqa: E402

CACHE = os.path.join(ROOT, "data", "cache")


class Game(dict):
    __getattr__ = dict.__getitem__


def games(hard=False, seed=0):
    path = os.path.join(CACHE, "fastbench{}_s{}.pkl".format("_hard" if hard else "", seed))
    if os.path.exists(path):
        return pickle.load(open(path, "rb"))
    out = {}
    for g, (df, teams, gt, pitch) in bench.load_games().items():
        segments = period_segments(df)
        frame = bench.real_like_ball(df, gt, pitch, segments, seed=seed, hard=hard)
        tag_list, tag_teams = bench.fake_tags(gt, segments, seed=seed, df=df, pitch=pitch, hard=hard)
        restart, rframes = dead_from_restarts(frame, pitch, tag_list, with_frames=True)
        speed = dead_from_players(frame, sum(teams, []), segments, pitch=pitch)
        out_ = dead_from_ball_out(frame, segments, pitch=pitch)
        before = dead_before_restart(frame, segments)
        quiet = speed.copy()
        for r in rframes:
            quiet[r:r + QUIET_AFTER_RESTART] = False
        dead = drop_short(out_ | quiet | before, segments) | restart
        out[g] = Game(df=frame, teams=teams, gt=gt, pitch=pitch, segments=segments, tag_list=tag_list,
                      tag_teams=tag_teams, rframes=rframes, restart=restart, speed=speed, ball_out=out_,
                      before=before, dead=dead)
    pickle.dump(out, open(path, "wb"))
    return out


def spell_f1(gt, labels):
    g, p = label_codes(gt), label_codes(labels)
    runs = valid_runs(g)
    return spell_scores(g, fill_abstentions(p, runs), runs)["mean_f1"]


def score(prepared, predict, base=None, quiet=False):
    """predict(game) -> labels. base: {game: score} to count wins against. Returns {game: score}."""
    res = {g: spell_f1(x.gt, predict(x)) for g, x in prepared.items()}
    mean = np.mean(list(res.values()))
    wins = "" if base is None else "  wins {}/{}".format(sum(res[g] > base[g] for g in res), len(res))
    if not quiet:
        print("  ".join("{} {:.3f}".format(g.replace("bl_", ""), v) for g, v in res.items()))
    print("mean {:.4f}{}".format(mean, wins), flush=True)
    return res


def score_both(prepared, predict, base=None, label=""):
    """Score against the raw keys and the organisers'-style "controlled" keys (controlled.py).
    Returns {game: (raw, controlled)}; prints means and wins vs base."""
    from controlled import controlled

    res = {}
    for g, x in prepared.items():
        lab = predict(x)
        if "ctl" not in x:
            x["ctl"] = controlled(x.gt)
        res[g] = (spell_f1(x.gt, lab), spell_f1(x.ctl, lab))
    raw, ctl = np.mean([v[0] for v in res.values()]), np.mean([v[1] for v in res.values()])
    w = ""
    if base is not None:
        w = "  wins raw {}/8 ctl {}/8  metrica {:+.3f}/{:+.3f}".format(
            sum(res[g][0] > base[g][0] for g in res), sum(res[g][1] > base[g][1] for g in res),
            res["metrica3"][0] - base["metrica3"][0], res["metrica3"][1] - base["metrica3"][1])
    print("{:28s} raw {:.4f}  controlled {:.4f}{}".format(label, raw, ctl, w), flush=True)
    return res
