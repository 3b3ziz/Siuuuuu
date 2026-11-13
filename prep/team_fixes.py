"""Two clean-ups of the team labels, after sticky possession (row 12 in docs/notes.md).

  gap_switch:  the ball is missing during live play, and once it's back the other team has it.
               The switch happened somewhere in the gap; sticky possession puts it at the end.
               Put it halfway instead.
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
