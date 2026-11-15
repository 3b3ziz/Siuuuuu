"""Plain-assert checks of replay_export.py on synthetic label arrays (no match data is read).

    uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/test_replay.py
"""

import numpy as np

import _paths
import possession_metrics as pm
import replay_export as R

H, A, D = 0, 1, 2


def codes_from(spec):
    """[(code, length)] -> int8 array."""
    return np.concatenate([np.full(n, c, dtype=np.int8) for c, n in spec])


def test_kind_of():
    assert R.kind_of(0, {0}, {0}) == "typical"
    assert R.kind_of(0, set(), {0}) == "fixed"
    assert R.kind_of(0, {0}, set()) == "lost"
    assert R.kind_of(0, set(), set()) == "missed"


def test_switches_counts_only_live_changes():
    codes = codes_from([(H, 10), (D, 5), (H, 10), (A, 10), (D, 3), (H, 4)])
    assert R.switches(codes, 0, len(codes)) == 2          # H->A and A->H; the D gaps do not count
    assert R.switches(codes, 0, 25) == 0                  # a stoppage between two H runs is no switch


def test_pick_clips_is_deterministic_inside_segments_and_disjoint():
    # Two halves of 2000 frames, truth alternating H/A possessions of 40 frames with short D gaps.
    half = []
    for i in range(24):
        half += [(H if i % 2 == 0 else A, 40), (D, 10)]
    gt = np.concatenate([codes_from(half), codes_from(half)])
    n = len(gt)
    segments = [(0, n // 2), (n // 2, n)]
    runs = [(0, n)]
    spells = pm.possession_spells(gt, runs)
    kinds = ["typical" if i % 4 == 0 else "fixed" if i % 4 == 1 else "missed" if i % 4 == 2 else "lost"
             for i in range(len(spells))]
    a = R.pick_clips(spells, kinds, gt, segments, 100)
    b = R.pick_clips(spells, kinds, gt, segments, 100)
    assert a == b, "two runs must pick the same clips"
    assert len(a) == sum(R.PER_KIND.values())
    for kind, gi, start, end in a:
        assert kinds[gi] == kind
        assert end - start == 100
        seg_a, seg_b = R.segment_of(spells[gi][0], segments)
        assert seg_a <= start and end <= seg_b, "a clip never crosses the half-time hole"
        assert start <= spells[gi][0] and spells[gi][1] <= end, "the clip holds the possession it was picked for"
    windows = sorted((s, e) for _, _, s, e in a)
    for (s0, e0), (s1, e1) in zip(windows, windows[1:]):
        assert e0 <= s1, "clip windows do not overlap"


def test_short_truth_possessions_are_not_candidates():
    gt = codes_from([(H, 5), (A, 5)] * 50)
    runs = [(0, len(gt))]
    spells = pm.possession_spells(gt, runs)
    kinds = ["missed"] * len(spells)
    assert all(b - a < R.MIN_SPELL for a, b, _ in spells)
    assert R.pick_clips(spells, kinds, gt, [(0, len(gt))], 100) == []


def test_strip_matches_scorer_segments():
    gt = codes_from([(H, 10), (D, 5), (A, 10)])
    runs = [(0, len(gt))]
    assert R.strip(gt, runs) == [[0, 10, H], [10, 15, D], [15, 25, A]]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok", t.__name__)
    print("{} checks passed".format(len(tests)))
