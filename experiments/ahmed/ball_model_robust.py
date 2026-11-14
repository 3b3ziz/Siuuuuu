"""Does the ball-aware model still win when trained on a *different* ball-hiding recipe than the
bench uses? (Guards against it learning the bench's fake hiding instead of football.)

Training hiding: 25% of live play hidden (bench 15%), 50% of stoppages (bench 75%), gaps 1.5x
longer, the tracker's straight-line fill only under 2 s (bench 5 s).
    python experiments/ahmed/ball_model_robust.py
"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(ROOT, "prep"), HERE]
import bench  # noqa: E402
import hide_ball  # noqa: E402
import shape_model as sm  # noqa: E402
import sticky  # noqa: E402
from ball_model import full_features  # noqa: E402
from ball_model import viterbi  # noqa: E402
from ball_model_bench import RUNS, row13_base, row14  # noqa: E402
from fastbench import games, spell_f1  # noqa: E402
from tags import restart_team  # noqa: E402
from team_fixes import merge_short  # noqa: E402
import pickle  # noqa: E402

hide_ball.LIVE_HIDDEN, hide_ball.DEAD_HIDDEN, hide_ball.FILL_UNDER = 0.25, 0.5, 50
hide_ball.LIVE_GAPS = [int(g * 1.5) for g in hide_ball.LIVE_GAPS]

B = {}
for g, (df, teams, gt, pitch) in bench.load_games().items():
    segs = sticky.period_segments(df)
    B[g] = [full_features(g, hide_ball.real_like_ball(df, gt, pitch, segs, seed=20, hard=h), teams, segs, pitch) + (gt,)
            for h in (False, True)]
    print("features", g, flush=True)
P1 = {g: pickle.load(open(os.path.join(sm.CACHE, "shape_p_{}.pkl".format(g)), "rb")) for g in B}
M = {g: sm.train([b for o in B if o not in (g, "metrica3") for b in B[o]]) for g in B}
del B
d = []
for hard, seed in RUNS:
    G = games(hard=hard, seed=seed)
    for g, x in G.items():
        p = sm.p_home(M[g], *full_features(g, x.df, x.teams, x.segments, x.pitch))
        base = row13_base(x)
        lab = merge_short(restart_team(viterbi(p, np.isin(base, ["H", "A"])), x.rframes, x.tag_teams))
        d.append((g, spell_f1(x.gt, lab) - spell_f1(x.gt, row14(x, P1[g]))))
    print(hard, seed, "vs row14 {:+.4f}".format(np.mean([v for _, v in d[-8:]])), flush=True)
v = np.array([x for _, x in d])
print("all: {:+.4f} wins {}/{} worst {:+.3f} metrica {:+.4f}".format(v.mean(), (v > 0).sum(), len(v), v.min(),
      np.mean([x for g, x in d if g == "metrica3"])))
