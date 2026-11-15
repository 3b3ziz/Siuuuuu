"""Regression and unit checks for the harness. Plain asserts; prints counts only.

    uv run --with numpy --with pandas --with kloppy --with scipy \
        python experiments/atallah/ball_ownership/test_harness.py

(a) VARIANTS["closest_row8"] on the cached frames equals data/sample/results*/ball_out_or_speed.csv.
(b) rules.labels(rule="closest") equals the same files: segment_labels defaults == sticky_segment.
(c) harness.score gives 0.5025 clean / 0.4444 noisy and 321 predicted spells on noisy.
(d) segment_labels: random equivalence with sticky_segment, then date_back, instant, min_spell.
"""

import os
import time

import numpy as np

import _paths
import possession_metrics as pm
import sample_game
from sticky import sticky_segment

import cache
import harness
import rules


def reference(folder):
    path = os.path.join(sample_game.SAMPLE, folder, "ball_out_or_speed.csv")
    return pm.read_label_csv(path)["label"].to_numpy().astype("<U1")


def mismatches(a, b):
    assert a.shape == b.shape, (a.shape, b.shape)
    return int((a != b).sum())


def test_regression(S):
    for set_name, df, folder in (("clean", S.df_clean, "results"), ("noisy", S.df_noisy, "results_noisy")):
        ref = reference(folder)
        dead = S.dead[set_name]
        row8 = rules.VARIANTS["closest_row8"](df, S.teams, S.segments, dead, S.pitch)
        n = mismatches(row8, ref)
        print("(a) closest_row8 vs {}/ball_out_or_speed.csv: {} mismatches".format(folder, n))
        assert n == 0
        ours = rules.labels(df, S.teams, S.segments, dead, S.pitch, rule="closest")
        n = mismatches(ours, ref)
        print("(b) rules.labels(rule=closest) vs {}/ball_out_or_speed.csv: {} mismatches".format(folder, n))
        assert n == 0


def test_scores():
    # (set, mode) -> (spellF1 to 4 dp, n_pred). Fixed = row 8 as published; oracle = truth D.
    expected = {("clean", "fixed"): (0.5025, 411), ("noisy", "fixed"): (0.4444, 321),
                ("clean", "oracle"): (0.5932, 381), ("noisy", "oracle"): (0.5631, 291)}
    for (set_name, mode), (f1, n_pred) in sorted(expected.items()):
        E = harness.get_set(set_name)
        labels = rules.VARIANTS["closest_row8"](E.df, E.teams, E.segments, E.dead[mode], E.pitch)
        s = harness.score(labels, E)
        print("(c) {} {}: spellF1 {:.6f}  n_pred {}  n_gt {}".format(
            set_name, mode, s["mean_f1"], s["n_pred"], s["n_gt"]))
        assert round(s["mean_f1"], 4) == f1, s["mean_f1"]
        assert s["n_gt"] == 381, s["n_gt"]
        assert s["n_pred"] == n_pred, s["n_pred"]


def seg(near, dead=None, **kw):
    near = np.array(list(near)).astype("<U1")
    near[near == "."] = ""
    if dead is None:
        dead = np.zeros(len(near), dtype=bool)
    return rules.segment_labels(near, dead, **kw)


def test_segment_defaults_random():
    rng = np.random.default_rng(0)
    total = 0
    for _ in range(50):
        n = int(rng.integers(20, 400))
        near = rng.choice(np.array(["H", "A", ""]), size=n, p=[0.3, 0.3, 0.4]).astype("<U1")
        # stretch out the runs so confirmations happen
        for s in range(0, n, 10):
            near[s:s + int(rng.integers(1, 10))] = near[s]
        dead = rng.random(n) < 0.1
        for s in range(0, n, 37):
            dead[s:s + int(rng.integers(0, 20))] = rng.random() < 0.3
        total += mismatches(rules.segment_labels(near, dead), sticky_segment(near, dead))
    print("(d) segment_labels defaults vs sticky_segment on 50 random segments: {} mismatches".format(total))
    assert total == 0


def test_date_back():
    near = "." * 10 + "H" * 20 + "A" * 20
    base = seg(near)
    assert "".join(base) == "H" * 30 + "A" * 20
    early = seg(near, date_back=-3)
    assert "".join(early) == "H" * 27 + "A" * 23, "".join(early)
    late = seg(near, date_back=3)
    assert "".join(late) == "H" * 33 + "A" * 17, "".join(late)
    # clamped to the live stretch: a huge negative date_back cannot leave the stretch or reorder
    far = seg(near, date_back=-100)
    assert "".join(far) == "A" * 50, "".join(far)
    # and never after the next switch / past the end
    far2 = seg(near, date_back=100)
    assert "".join(far2) == "H" * 50, "".join(far2)
    # across a dead gap: date_back stays inside its own live stretch
    dead = np.zeros(50, dtype=bool)
    dead[28:32] = True
    gap = seg(near, dead=dead, date_back=-5)
    assert "".join(gap) == "H" * 28 + "D" * 4 + "A" * 18, "".join(gap)
    print("(d) date_back: ok")


def test_instant():
    # no near confirmation at all: an instant switch is the only evidence
    inst = np.array([""] * 30, dtype="<U1")
    inst[5], inst[20] = "H", "A"
    out = seg("." * 30, instant=inst)
    assert "".join(out) == "H" * 20 + "A" * 10, "".join(out)
    # restart of the count: 12 frames of A near, instant H at 6 -> neither A run reaches 8
    inst = np.array([""] * 12, dtype="<U1")
    inst[6] = "H"
    assert "".join(seg("A" * 12)) == "A" * 12
    out = seg("A" * 12, instant=inst)
    assert "".join(out) == "H" * 12, "".join(out)
    # with 16 frames of A the run from 6 is confirmed at 13, dated to 6: H holds frames 0-5 only
    inst = np.array([""] * 16, dtype="<U1")
    inst[6] = "H"
    out = seg("A" * 16, instant=inst)
    assert "".join(out) == "H" * 6 + "A" * 10, "".join(out)
    # instant for the team already on the ball adds no switch
    inst = np.array([""] * 20, dtype="<U1")
    inst[12] = "H"
    out = seg("H" * 20, instant=inst)
    assert "".join(out) == "H" * 20, "".join(out)
    # instant on a dead frame is ignored (the frame is D, the stretch restarts after)
    inst = np.array([""] * 20, dtype="<U1")
    inst[10] = "A"
    dead = np.zeros(20, dtype=bool)
    dead[8:12] = True
    out = seg("H" * 20, instant=inst, dead=dead)
    assert "".join(out) == "H" * 8 + "D" * 4 + "H" * 8, "".join(out)
    # an instant switch at frame t puts the switch exactly at t: label t-1 is the old team, t the new
    # (H confirmed by near in frames 0-9, then nobody near; the instant is the only later evidence)
    for t in (12, 17, 29):
        inst = np.array([""] * 40, dtype="<U1")
        inst[t] = "A"
        out = seg("H" * 10 + "." * 30, instant=inst)
        assert "".join(out) == "H" * t + "A" * (40 - t), (t, "".join(out))
        assert out[t - 1] == "H" and out[t] == "A"
    # date_back moves near-confirmed switches only (INTERFACES.md: "each confirmed switch frame");
    # the instant switch stays exactly at t while the near-confirmed one beside it moves.
    inst = np.array([""] * 50, dtype="<U1")
    inst[10] = "A"                                        # instant A at 10
    near = "H" * 8 + "." * 22 + "H" * 20                  # H confirmed at 0, again dated to 30
    out = seg(near, instant=inst)
    assert "".join(out) == "H" * 10 + "A" * 20 + "H" * 20, "".join(out)
    for db in (-4, 0, 3):
        out = seg(near, instant=inst, date_back=db)
        assert "".join(out) == "H" * 10 + "A" * (20 + db) + "H" * (20 - db), (db, "".join(out))
        assert out[9] == "H" and out[10] == "A", (db, "".join(out))   # instant stays exactly at 10
    print("(d) instant: ok")


def test_min_spell():
    near = "A" * 10 + "." * 5 + "A" * 10
    inst = np.array([""] * 25, dtype="<U1")
    inst[10] = "H"
    base = seg(near, instant=inst)
    assert "".join(base) == "A" * 10 + "H" * 5 + "A" * 10, "".join(base)
    dropped = seg(near, instant=inst, min_spell=8)
    assert "".join(dropped) == "A" * 25, "".join(dropped)
    kept = seg(near, instant=inst, min_spell=5)        # length 5 is not shorter than 5
    assert "".join(kept) == "".join(base), "".join(kept)
    # confirmed by its own near run inside the spell: not a deflection, kept however short
    near2 = "A" * 10 + "H" * 8 + "A" * 10
    inst2 = np.array([""] * 28, dtype="<U1")
    inst2[10] = "H"
    out = seg(near2, instant=inst2, min_spell=20)
    assert "".join(out) == "A" * 10 + "H" * 8 + "A" * 10, "".join(out)
    # does not revert to the previous team (goes on to a third state): kept
    near3 = "A" * 10 + "." * 5 + "H" * 10
    inst3 = np.array([""] * 25, dtype="<U1")
    inst3[10] = "H"
    out = seg(near3, instant=inst3, min_spell=8)
    assert "".join(out) == "A" * 10 + "H" * 15, "".join(out)
    # revert by a second instant counts too, and the count chain stays consistent
    inst4 = np.array([""] * 25, dtype="<U1")
    inst4[10], inst4[13] = "H", "A"
    out = seg("A" * 10 + "." * 15, instant=inst4, min_spell=8)
    assert "".join(out) == "A" * 25, "".join(out)
    # the spec example: a 5-frame instant spell is removed by min_spell=8, a 10-frame one survives
    inst5 = np.array([""] * 40, dtype="<U1")
    inst5[10], inst5[15] = "H", "A"                       # H for 5 frames, back to A
    out = seg("A" * 10 + "." * 30, instant=inst5, min_spell=8)
    assert "".join(out) == "A" * 40, "".join(out)
    assert "".join(seg("A" * 10 + "." * 30, instant=inst5)) == "A" * 10 + "H" * 5 + "A" * 25
    inst10 = np.array([""] * 40, dtype="<U1")
    inst10[10], inst10[20] = "H", "A"                     # H for 10 frames, back to A
    out = seg("A" * 10 + "." * 30, instant=inst10, min_spell=8)
    assert "".join(out) == "A" * 10 + "H" * 10 + "A" * 20, "".join(out)
    # the same with the revert coming from near (A confirmed again after the H burst)
    inst = np.array([""] * 40, dtype="<U1")
    inst[10] = "H"
    out = seg("A" * 10 + "." * 5 + "A" * 25, instant=inst, min_spell=8)
    assert "".join(out) == "A" * 40, "".join(out)
    out = seg("A" * 10 + "." * 10 + "A" * 20, instant=inst, min_spell=8)
    assert "".join(out) == "A" * 10 + "H" * 10 + "A" * 20, "".join(out)
    print("(d) min_spell: ok")


def main():
    t0 = time.time()
    S = cache.load_practice()
    print("load_practice() from cache: {:.2f} s".format(time.time() - t0))
    test_regression(S)
    test_scores()
    test_segment_defaults_random()
    test_date_back()
    test_instant()
    test_min_spell()
    print("all checks passed")


if __name__ == "__main__":
    main()
