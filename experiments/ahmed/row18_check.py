"""Row 18 = row 17 + restart-kick stoppage edges (idea_restart_kick.py "both") + 0.8 s minimum possession, on the bench.
    python experiments/ahmed/row18_check.py <hard 0/1> <seed>
"""
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(ROOT, "prep"), HERE]
from ball_model import CACHE, VERSION, blend_touch, lock_clear, viterbi  # noqa: E402
from fastbench import games, spell_f1  # noqa: E402
from idea_restart_kick import FPS, ball_speed, kick_ends, kick_frames, still_then_kick  # noqa: E402
from stop_fixes import drop_short  # noqa: E402
from sticky import sticky_labels  # noqa: E402
from tags import QUIET_AFTER_RESTART, restart_team  # noqa: E402
from team_fixes import merge_short, on_ball  # noqa: E402

hard, seed = bool(int(sys.argv[1])), int(sys.argv[2])
G = games(hard=hard, seed=seed)
P = pickle.load(open(os.path.join(CACHE, "ballmodel_p_{}_{}_{}.pkl".format("h" if hard else "n", seed, VERSION)), "rb"))
out = {}
for g, x in G.items():
    quiet = x.speed.copy()
    for r in x.rframes:
        quiet[r:r + QUIET_AFTER_RESTART] = False
    raw = x.ball_out | quiet | x.before
    v = ball_speed(x.df, x.pitch)
    deads = {"r17": drop_short(raw, x.segments, 150) | x.restart,
             "kick": kick_ends(drop_short(raw | still_then_kick(v, x.segments, 2 * FPS), x.segments, 150),
                               x.segments, kick_frames(v), 3 * FPS, 10 * FPS) | x.restart}
    near = on_ball(x.df, x.teams, x.pitch)
    labs = {}
    for k, dead in deads.items():
        base = restart_team(sticky_labels(x.df, x.teams, x.segments, "closest", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
        touch = restart_team(sticky_labels(x.df, x.teams, x.segments, "touch", dead=dead, pitch=x.pitch), x.rframes, x.tag_teams)
        labs[k] = restart_team(viterbi(lock_clear(blend_touch(P[g], touch), near), np.isin(base, ["H", "A"])), x.rframes, x.tag_teams)
    out[(g, "r17")] = spell_f1(x.gt, merge_short(labs["r17"]))
    out[(g, "kick")] = spell_f1(x.gt, merge_short(labs["kick"]))
    out[(g, "poss08")] = spell_f1(x.gt, merge_short(labs["r17"], 0.8))
    out[(g, "r18")] = spell_f1(x.gt, merge_short(labs["kick"], 0.8))
    print(g, " ".join("{}:{:.4f}".format(k, out[(g, k)]) for k in ("r17", "kick", "poss08", "r18")), flush=True)
pickle.dump(out, open(os.path.join(os.environ.get("OUT", "."), "row18_{}_{}.pkl".format(int(hard), seed)), "wb"))
