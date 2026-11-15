"""Possession rules behind one signature: fn(df, teams, segments, dead, pitch, **params) -> labels.

Two pieces, so that a new "who owns the ball" rule only has to produce a per-frame `near` array
(and optionally an `instant` array) and reuse the same sticky segment logic:

  near_closest(df, teams, pitch)   the per-frame "H" / "A" / "" array the row 8 rule builds
  segment_labels(near, dead, ...)  sticky_segment generalised: switch_frames, date_back, instant,
                                   min_spell. With defaults it equals sticky.sticky_segment exactly
                                   (test_harness.py checks this on the practice match).

VARIANTS maps a name to a rule. "closest_row8" is the untouched prep/sticky.py call, kept as the
regression anchor. "closest" is the same rule through near_closest + segment_labels, so its
parameters can be swept from harness.py.
"""

import numpy as np

import _paths  # noqa: F401
import sticky
from sticky import MARGIN_M, SWITCH_FRAMES, ZONE_M, runs, team_distances

# Every tunable default in one place. Pass any of them as keyword params to labels().
DEFAULTS = {
    "rule": "closest",          # which near array: "closest" (row 8). Others register below.
    "zone_m": ZONE_M,           # a player this close to the ball can be on it (2.0 m)
    "margin_m": MARGIN_M,       # "closest": must be this much closer than the nearest opponent
    "switch_frames": SWITCH_FRAMES,  # frames of the other team near the ball before a switch
    "date_back": 0,             # frames added to each near-confirmed switch (negative = earlier)
    "min_spell": 0,             # drop instant-caused spells shorter than this that bounce back
}


def near_closest(df, teams, pitch, zone_m=ZONE_M, margin_m=MARGIN_M):
    """'H' / 'A' / '' per frame: the "closest" rule of sticky.sticky_labels, nothing else."""
    d_home, d_away = team_distances(df, teams, pitch)
    home_on, away_on = d_home + margin_m <= d_away, d_away + margin_m <= d_home
    return np.where((d_home <= zone_m) & home_on, "H",
                    np.where((d_away <= zone_m) & away_on, "A", "")).astype("<U1")


def segment_labels(near, dead, switch_frames=SWITCH_FRAMES, date_back=0, instant=None, min_spell=0):
    """Labels for one segment (a half). Generalised copy of sticky.sticky_segment.

    near:     "H" / "A" / "" per frame. A team near the ball for `switch_frames` frames in a
              row is a confirmed switch, dated to the first of those frames.
    dead:     bool stoppage mask, same length. Dead frames are "D"; the team carries across
              a live stretch with no confirmed switch, and a restart belongs to the first team
              confirmed in it (as in sticky_segment).
    instant:  optional "H" / "A" / "" per frame. A non-empty value forces a switch at that frame
              without confirmation, and restarts the confirmation count (a near run straddling
              the frame only counts from the frame on). A frame already held by that team adds no
              switch but still restarts the count.
    date_back: integer added to each near-confirmed switch frame (negative = earlier). Clamped
              to the live stretch and kept between its neighbours (never before the previous
              switch, never after the next one), so spells can shrink to nothing but not reorder.
              Instant switches are not moved.
    min_spell: an instant-caused spell shorter than this that (a) was never confirmed by a near
              run of its own team inside the spell and (b) is followed by a switch back to the
              team that held the ball before it, is dropped: the previous team keeps the ball
              through it (a deflection). The first switch of a stretch has no previous team
              inside the stretch, so it is never dropped.

    With the defaults (switch_frames=8, date_back=0, instant=None, min_spell=0) the result is
    identical to sticky.sticky_segment(near, dead).
    """
    near = np.asarray(near)
    dead = np.asarray(dead, dtype=bool)
    if instant is not None:
        instant = np.asarray(instant)
    labels = np.full(len(near), "D", dtype="<U1")

    team = None  # carries across short stretches only if nothing confirms otherwise
    for start, stop in runs(~dead):
        # Switches inside this stretch: [frame, team, by_instant, confirmed_by_near].
        switches = []
        run_team, run_start = "", start
        for i in range(start, stop):
            if instant is not None and instant[i]:
                if not switches or switches[-1][1] != instant[i]:
                    switches.append([i, instant[i], True, False])
                run_team, run_start = "", i          # restart the confirmation count
            if near[i] != run_team:
                run_team, run_start = near[i], i
            if run_team and i - run_start + 1 == switch_frames:
                if not switches or switches[-1][1] != run_team:
                    switches.append([run_start, run_team, False, True])
                else:
                    switches[-1][3] = True           # the holder is confirmed by near as well

        if min_spell > 0 and len(switches) > 1:
            kept = []
            for k, sw in enumerate(switches):
                frame, t, by_instant, confirmed = sw
                has_next = k + 1 < len(switches)
                nxt_frame = switches[k + 1][0] if has_next else stop
                prev_team = kept[-1][1] if kept else None
                if (by_instant and not confirmed and prev_team is not None and has_next
                        and switches[k + 1][1] == prev_team and nxt_frame - frame < min_spell):
                    continue                         # deflection: previous team keeps the ball
                if kept and kept[-1][1] == t:
                    kept[-1][3] = kept[-1][3] or confirmed   # redundant switch back: merge
                    continue
                kept.append(sw)
            switches = kept

        if date_back:
            for k, sw in enumerate(switches):
                if sw[2]:
                    continue                         # instant switches stay where they are
                lo = switches[k - 1][0] if k else start
                hi = switches[k + 1][0] if k + 1 < len(switches) else stop
                sw[0] = int(min(max(sw[0] + date_back, start, lo), stop, hi))

        if not switches:
            if team is None:
                continue  # nothing to say: stays D
            labels[start:stop] = team
            continue
        # Before the first confirmed team in a stretch (a restart), that team already had it.
        labels[start:switches[0][0]] = switches[0][1]
        for sw, nxt in zip(switches, switches[1:] + [[stop, None]]):
            labels[sw[0]:nxt[0]] = sw[1]
        team = switches[-1][1]
    return labels


# Per-frame "near" builders by rule name. A new rule adds one here and sets params["rule"].
NEAR = {
    "closest": lambda df, teams, pitch, p: near_closest(df, teams, pitch, p["zone_m"], p["margin_m"]),
}


def labels(df, teams, segments, dead, pitch, **params):
    """'<U1' labels for the whole frame: segment_labels per segment, 'X' outside the segments."""
    p = dict(DEFAULTS)
    p.update(params)
    if p["rule"] not in NEAR:
        raise ValueError("unknown rule {!r}; known: {}".format(p["rule"], sorted(NEAR)))
    near = NEAR[p["rule"]](df, teams, pitch, p)
    instant = p.get("instant")
    out = np.full(len(df), "X", dtype="<U1")
    for start, stop in segments:
        out[start:stop] = segment_labels(
            near[start:stop], dead[start:stop], switch_frames=p["switch_frames"],
            date_back=p["date_back"], min_spell=p["min_spell"],
            instant=None if instant is None else instant[start:stop])
    return out


def closest_row8(df, teams, segments, dead, pitch, **params):
    """Row 8 exactly as prep/sticky.py computes it. Params are ignored on purpose."""
    return sticky.sticky_labels(df, teams, segments, "closest", dead=dead, pitch=pitch)


VARIANTS = {
    "closest_row8": closest_row8,
    "closest": labels,
}

# --- hook -------------------------------------------------------------------------------------
# The rule task registers VARIANTS["ball_ownership"] from its own file (ball_rule.py in this
# folder) without editing this one. Until that file exists the import fails and nothing changes.
try:
    from ball_rule import ball_ownership as _ball_ownership
    VARIANTS["ball_ownership"] = _ball_ownership
except ImportError:
    pass
