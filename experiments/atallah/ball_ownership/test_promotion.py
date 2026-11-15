"""Promotion check: prep/ball_ownership.py equals the experiment it was promoted from, and the old
sticky rules are untouched. Plain asserts; prints mismatch counts only.

    uv run --with numpy --with pandas --with kloppy --with scipy \
        python experiments/atallah/ball_ownership/test_promotion.py

(a) prep.ball_ownership.ball_ownership_labels == rules.VARIANTS["ball_ownership"] element for
    element on the practice clean and noisy frames with the fixed dead masks.
(b) sticky.sticky_labels(rule="touch", dead=...) gives the same labels (the prep/run_real.py path).
(c) sticky.sticky_labels(rule="closest", dead=...) still equals data/sample/results*/
    ball_out_or_speed.csv (row 8), and "alone" / "closest" with dead=None still equal
    data/sample/results*/sticky.csv and sticky_closest.csv (rows 1-2 files as last written).
(d) prep.ball_ownership.segment_labels == rules.segment_labels on random near/dead/instant inputs.
(e) data/sample/results*/ball_ownership.csv, when present, equals the labels from (a).
"""

import os

import numpy as np

import _paths
import possession_metrics as pm
import sample_game
import sticky
from ball_ownership import DEFAULTS as PREP_DEFAULTS
from ball_ownership import ball_ownership_labels, segment_labels as prep_segment_labels

import cache
import rules
from ball_rule import DEFAULTS as EXP_DEFAULTS


def read(folder, name):
    path = os.path.join(sample_game.SAMPLE, folder, name + ".csv")
    if not os.path.isfile(path):
        return None
    return pm.read_label_csv(path)["label"].to_numpy().astype("<U1")


def mismatches(a, b):
    assert a.shape == b.shape, (a.shape, b.shape)
    return int((a != b).sum())


def main():
    assert PREP_DEFAULTS == EXP_DEFAULTS, "constants differ: {} vs {}".format(PREP_DEFAULTS, EXP_DEFAULTS)
    print("constants: prep DEFAULTS == experiment DEFAULTS ({} keys)".format(len(PREP_DEFAULTS)))

    S = cache.load_practice()
    for set_name, df, folder in (("clean", S.df_clean, "results"), ("noisy", S.df_noisy, "results_noisy")):
        dead = S.dead[set_name]
        exp = rules.VARIANTS["ball_ownership"](df, S.teams, S.segments, dead, S.pitch)
        prep = ball_ownership_labels(df, S.teams, S.segments, dead, S.pitch)
        n = mismatches(prep, exp)
        print("(a) {}: prep ball_ownership_labels vs rules.VARIANTS[ball_ownership]: {} mismatches".format(set_name, n))
        assert n == 0
        n_x = int((prep == "X").sum())
        inside = sum(b - a for a, b in S.segments)
        assert n_x == len(df) - inside, (n_x, len(df) - inside)

        touch = sticky.sticky_labels(df, S.teams, S.segments, "touch", dead=dead, pitch=S.pitch)
        n = mismatches(touch, prep)
        print("(b) {}: sticky_labels(rule=touch) vs prep ball_ownership_labels: {} mismatches".format(set_name, n))
        assert n == 0

        ref = read(folder, "ball_out_or_speed")
        row8 = sticky.sticky_labels(df, S.teams, S.segments, "closest", dead=dead, pitch=S.pitch)
        n = mismatches(row8, ref)
        print("(c) {}: sticky_labels(rule=closest) vs {}/ball_out_or_speed.csv: {} mismatches".format(set_name, folder, n))
        assert n == 0
        for rule, name in (("alone", "sticky"), ("closest", "sticky_closest")):
            ref = read(folder, name)
            if ref is None:
                print("(c) {}: {}/{}.csv missing, skipped".format(set_name, folder, name))
                continue
            n = mismatches(sticky.sticky_labels(df, S.teams, S.segments, rule, pitch=S.pitch), ref)
            print("(c) {}: sticky_labels(rule={}) vs {}/{}.csv: {} mismatches".format(set_name, rule, folder, name, n))
            assert n == 0

        written = read(folder, "ball_ownership")
        if written is None:
            print("(e) {}: {}/ball_ownership.csv not written yet, skipped".format(set_name, folder))
        else:
            n = mismatches(written, prep)
            print("(e) {}: {}/ball_ownership.csv vs prep labels: {} mismatches".format(set_name, folder, n))
            assert n == 0

    rng = np.random.default_rng(0)
    total = 0
    for _ in range(100):
        n = int(rng.integers(20, 400))
        near = rng.choice(np.array(["H", "A", ""]), size=n, p=[0.3, 0.3, 0.4]).astype("<U1")
        for s in range(0, n, 10):
            near[s:s + int(rng.integers(1, 10))] = near[s]
        dead = rng.random(n) < 0.1
        inst = np.where(rng.random(n) < 0.05, rng.choice(np.array(["H", "A"]), size=n), "").astype("<U1")
        kw = dict(switch_frames=int(rng.integers(4, 13)), date_back=int(rng.integers(-5, 6)),
                  instant=inst, min_spell=int(rng.integers(0, 13)))
        total += mismatches(prep_segment_labels(near, dead, **kw), rules.segment_labels(near, dead, **kw))
    print("(d) prep segment_labels vs rules.segment_labels on 100 random segments: {} mismatches".format(total))
    assert total == 0
    print("all promotion checks passed")


if __name__ == "__main__":
    main()
