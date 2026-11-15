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


def test_window_stays_inside_the_half():
    segments = [(0, 1000), (1000, 2000)]
    assert R.window_for(500, segments, 300) == (350, 650)
    assert R.window_for(20, segments, 300) == (0, 300)            # clamped at the start of the half
    assert R.window_for(1990, segments, 300) == (1700, 2000)      # clamped at the end, never into the hole
    assert R.window_for(1010, segments, 300) == (1000, 1300)


def test_stoppage_kind_from_the_clean_ball_track():
    nan = np.nan
    bx = np.array([0.5, 0.5, 0.5, nan, 0.5, 0.5, 1.2, 0.9, 0.5, 0.5])
    by = np.array([0.5, -0.1, 0.5, nan, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    assert R.stoppage_kind(bx, by, 0, 3) == "Throw-in"
    assert R.stoppage_kind(bx, by, 5, 8) == "Goal kick or corner"
    assert R.stoppage_kind(bx, by, 8, 10) is None                 # on the pitch and short
    bx2 = np.full(60, 0.5)
    assert R.stoppage_kind(bx2, bx2, 0, 60) == "Free kick"        # on the pitch for STOP_FRAMES


def test_choose_is_deterministic_and_disjoint():
    cands = [(3, 100, 100, 200, "a"), (3, 50, 50, 150, "b"), (1, 900, 900, 1000, "c"), (5, 120, 120, 220, "d")]
    chosen = []
    taken = R.choose(cands, 2, chosen)
    assert [t[2] for t in taken] == ["d", "c"], "best score first, then an earlier non-overlapping one"
    assert R.choose(cands, 2, []) == R.choose(cands, 2, [])
    assert R.choose(cands, 3, chosen) == [], "nothing left that does not overlap"


def test_plan_names_restarts_and_misses():
    # One half: H 40, D 60 (ball out over the touchline), A 40, D 10, H 6, A 40, D 60 (ball on the pitch), H 40, D 10, A 40.
    spec = [(H, 40), (D, 60), (A, 40), (D, 10), (H, 6), (A, 40), (D, 60), (H, 40), (D, 10), (A, 40)]
    gt = codes_from(spec)
    n = len(gt)
    runs, segments = [(0, n)], [(0, n)]
    spells = pm.possession_spells(gt, runs)                       # H, A, H(6), A, H, A
    kinds = ["typical", "typical", "missed", "typical", "typical", "fixed"]
    cats = ["matched", "matched", "missed switch (short)", "matched", "matched", "matched"]
    bx = np.full(n, 0.5)
    by = np.full(n, 0.5)
    by[41] = -0.2                                                 # out over the touchline in the first stoppage
    d_segments = [(s, e) for s, e, k in pm.segments(gt, runs) if k == D]
    chosen, pools = R.plan_clips(spells, kinds, cats, gt, segments, 40, d_segments, (bx, by), [])
    names = [c[2]["name"] for c in chosen]
    for want in ("Throw-in", "Free kick", "Short possession", "Row 9 fixes a switch"):
        assert want in names, (want, names)
    assert pools["Goal kick or corner"] == 0
    for start, end, payload in chosen:
        assert 0 <= start < end <= n and end - start <= 40
    windows = sorted((s, e) for s, e, _ in chosen)
    for (s0, e0), (s1, e1) in zip(windows, windows[1:]):
        assert e0 <= s1, "clip windows do not overlap"


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
