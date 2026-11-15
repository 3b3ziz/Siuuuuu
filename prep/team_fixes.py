"""Two clean-ups of the team labels, after sticky possession (row 12 in docs/notes.md).

  gap_switch:  the ball is missing during live play, and once it's back the other team has it.
               The switch happened somewhere in the gap; sticky possession puts it at the end.
               Put it halfway instead.
  shape_gap:   better than gap_switch (row 13). Uses a players-only model (prep/shape_model.py):
               the switch goes where the model says, and if the same team has it before and after,
               a hidden spell by the other team is put in when the model is sure (2 s+).
  model_override: with the ball visible too (row 14): where nobody is clearly on the ball (ball in
               flight, contested), the model can overrule our team call if it's sure for 2 s+.
               Never on frames where our team is clearly on the ball.
  merge_short: a possession under 1 s isn't "controlled" (CHALLENGE.md: a touch without control
               or a deflection is not a change). Give it to the team before it, or to the team
               after it at the start of a live stretch.
"""

import numpy as np

from sticky import runs

GAP_FRAC = 0.5
CONFIRM = 50     # the new team must show within 2 s of the ball coming back
MIN_POSS_S = 1.0


def gap_switch(labels, ball_seen, frac=GAP_FRAC, confirm=CONFIRM):
    labels = labels.copy()
    for s, e in runs(~ball_seen):
        if s == 0 or e >= len(labels):
            continue
        before = labels[s - 1]
        if before not in ("H", "A") or (labels[s:e] == "D").any():
            continue
        c = e
        while c < min(e + confirm, len(labels)) and labels[c] == before:
            c += 1
        if c < len(labels) and c < e + confirm and labels[c] in ("H", "A") and labels[c] != before:
            labels[s + int((e - s) * frac):c] = labels[c]
    return labels


def merge_short(labels, min_s=MIN_POSS_S):
    labels = np.asarray(labels).copy()
    for s, e in runs(np.isin(labels, ["H", "A"])):
        seg = labels[s:e]
        while True:
            bounds = np.concatenate(([0], np.flatnonzero(seg[1:] != seg[:-1]) + 1, [len(seg)]))
            lens = np.diff(bounds)
            if len(lens) == 1 or lens.min() >= min_s * 25:
                break
            i = int(np.argmin(lens))
            a, b = bounds[i], bounds[i + 1]
            seg[a:b] = seg[a - 1] if a > 0 else seg[b]
        labels[s:e] = seg
    return labels


EPS = 1e-3


def _logs(p):
    p = np.clip(p, EPS, 1 - EPS)
    return {"H": np.log(p), "A": np.log(1 - p)}


def shape_gap(labels, ball_seen, p_home, insert=True, penalty=25.0, min_s=2.0, confirm=CONFIRM):
    labels = labels.copy()
    lp = _logs(p_home)
    for s, e in runs(~ball_seen):
        if s == 0 or e >= len(labels):
            continue
        before = labels[s - 1]
        if before not in ("H", "A") or (labels[s:e] == "D").any():
            continue
        c = e
        while c < min(e + confirm, len(labels)) and labels[c] == before:
            c += 1
        after = labels[c] if c < len(labels) and c < e + confirm else before
        if after not in ("H", "A"):
            after = before
        if after != before:
            # best k: frames [s, k) before, [k, c) after
            gain = np.concatenate(([0.0], np.cumsum(lp[before][s:e] - lp[after][s:e])))
            k = s + int(np.argmax(gain))
            labels[s:k] = before
            labels[k:c] = after
        elif insert:
            other = "A" if before == "H" else "H"
            d = lp[other][s:e] - lp[before][s:e]
            # best stretch [i, j) by max-subarray
            best, cur, ci, bi, bj = 0.0, 0.0, 0, 0, 0
            for t, v in enumerate(d):
                if cur <= 0:
                    cur, ci = v, t
                else:
                    cur += v
                if cur > best:
                    best, bi, bj = cur, ci, t + 1
            if best > penalty and bj - bi >= min_s * 25:
                labels[s + bi:s + bj] = other
    return labels


OTHER = {"H": "A", "A": "H"}


def on_ball(df, teams, pitch):
    """'H' / 'A' / '' per frame: the team clearly on the ball (sticky's "closest" rule)."""
    import sticky

    dh, da = sticky.team_distances(df, teams, pitch)
    return np.where((dh <= sticky.ZONE_M) & (dh + sticky.MARGIN_M <= da), "H",
                    np.where((da <= sticky.ZONE_M) & (da + sticky.MARGIN_M <= dh), "A", ""))


def model_override(labels, p_home, near=None, penalty=150.0, min_s=2.0, max_flips=200):
    """near: if given, never flip a frame where our team is clearly on the ball."""
    labels = labels.copy()
    lp = _logs(p_home)
    for s, e in runs(np.isin(labels, ["H", "A"])):
        for _ in range(max_flips):
            seg = labels[s:e]
            cur = np.where(seg == "H", lp["H"][s:e], lp["A"][s:e])
            alt = np.where(seg == "H", lp["A"][s:e], lp["H"][s:e])
            d = alt - cur
            if near is not None:
                d = np.where(near[s:e] == seg, -1e3, d)
            best, run, ci, bi, bj = 0.0, 0.0, 0, 0, 0
            for t, v in enumerate(d):
                if run <= 0:
                    run, ci = v, t
                else:
                    run += v
                if run > best:
                    best, bi, bj = run, ci, t + 1
            if best <= penalty or bj - bi < min_s * 25:
                break
            seg[bi:bj] = np.where(seg[bi:bj] == "H", "A", "H")
            labels[s:e] = seg
    return labels
