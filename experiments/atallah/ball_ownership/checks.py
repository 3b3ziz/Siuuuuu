"""Ballpark checks on a label array beyond prep/run_real.ballpark: spell shape, not just counts."""

import numpy as np

import _paths  # noqa: F401
from sticky import runs

FPS = 25.0


def _spells(labels, segments):
    """[(start, stop, team)] H/A spells inside each segment, in order."""
    out = []
    for a, b in segments:
        seg = labels[a:b]
        for team in ("H", "A"):
            out.extend((a + s, a + e, team) for s, e in runs(seg == team))
    out.sort()
    return out


def extra_ballpark(labels, segments):
    """Prints and returns spells_under_12, tot_bursts_under_25, spell_len_p10_p50_p90_s, home_share.

    - spells_under_12: H/A spells shorter than 12 frames (under half a second: almost always noise).
    - tot_bursts_under_25: turnover bursts, i.e. a spell of one team shorter than 25 frames
      sandwiched directly (no D in between) between two spells of the other team: P T P ping-pong.
    - spell_len_p10_p50_p90_s: percentiles of H/A spell length in seconds.
    - home_share: share of H among H+A frames inside the segments.
    """
    labels = np.asarray(labels).astype("<U1")
    spells = _spells(labels, segments)
    lengths = np.array([e - s for s, e, _ in spells], dtype=float)
    bursts = 0
    for (s0, e0, t0), (s1, e1, t1), (s2, e2, t2) in zip(spells, spells[1:], spells[2:]):
        if t0 == t2 != t1 and e0 == s1 and e1 == s2 and e1 - s1 < 25:
            bursts += 1
    inside = np.zeros(len(labels), dtype=bool)
    for a, b in segments:
        inside[a:b] = True
    h, a_ = int(((labels == "H") & inside).sum()), int(((labels == "A") & inside).sum())
    pct = (np.percentile(lengths, [10, 50, 90]) / FPS).round(2).tolist() if len(lengths) else [0, 0, 0]
    out = {
        "spells_under_12": int((lengths < 12).sum()),
        "tot_bursts_under_25": int(bursts),
        "spell_len_p10_p50_p90_s": pct,
        "home_share": (h / float(h + a_)) if h + a_ else float("nan"),
        "n_spells": len(spells),
    }
    print("extra ballpark: spells {n_spells}  under 12 frames {spells_under_12}  "
          "turnover bursts under 25 frames {tot_bursts_under_25}  "
          "spell length p10/p50/p90 s {spell_len_p10_p50_p90_s}  home share {home_share:.2f}".format(**out))
    return out
