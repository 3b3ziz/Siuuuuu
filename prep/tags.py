"""Stoppage rules from Smart Tagging (the automatic tags that ship with the match) and match edges.

  restarts:  every set piece tag is a restart. The tag window starts ~4-6 s before the ball is
             played (kickoffs: 3.5 s, checked against both real kickoffs). Find the restart in the
             tracking: the end of the first "ball not in play" stretch (missing, outside the pitch,
             or still) that ends 1-12 s after the tag starts. Everything from the start of that
             stretch to the restart is a stoppage.
  goals:     after a goal, play is dead until the kickoff. Goal moment = the last ball-out before
             the "Kick Off (After Goal)" tag, inside the GOALS window.
  edges:     before the kickoff of each half is dead; so is any frame with fewer than 10 players
             tracked (teams walking off at the end of the half).
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE]
from sticky import runs  # noqa: E402

KICKOFF_OFFSET = 88      # frames from a kickoff tag's start to the real kickoff (11185-11097)
SEARCH = (25, 300)       # restart is 1-12 s after the tag starts
STILL_MS = 1.0
MIN_STRETCH = 10
DEFAULT_OFFSET = 100     # no stretch found: assume the restart 4 s after the tag starts
MIN_PLAYERS = 10
QUIET_AFTER_RESTART = 250  # frames (10 s) after a tagged restart where the speed rule can't call a stoppage
HOME_NAME = "Barcelona"    # Smart Tagging names clubs; home is Barça (BAR-ATH)


def load_tags():
    from kloppy import sportscode
    from games import asset_paths

    ev = sportscode.load(asset_paths()["smart_tagging"]).to_df()
    ev["a"] = (ev.timestamp.dt.total_seconds() * 25).round().astype(int)
    ev["b"] = (ev.end_timestamp.dt.total_seconds() * 25).round().astype(int)
    return ev


def not_in_play(df, pitch):
    bx, by = df["ball_x"].to_numpy() * pitch[0], df["ball_y"].to_numpy() * pitch[1]
    v = np.hypot(np.diff(bx, prepend=np.nan), np.diff(by, prepend=np.nan)) * 25
    v = pd.Series(v).rolling(5, center=True, min_periods=3).median().to_numpy()
    with np.errstate(invalid="ignore"):
        outside = (bx < 0) | (bx > pitch[0]) | (by < 0) | (by > pitch[1])
        return np.isnan(bx) | outside | (v < STILL_MS)


def restart_frame(nip, a, kickoff=False):
    """(stoppage start, restart frame) for a set piece tag starting at frame a."""
    if kickoff:
        # 3.5 s after the tag starts, or later if the ball still isn't in play (up to 20 s more).
        # The "Kick Off (After Goal)" at 62012 follows a goal that was ruled out: on the video
        # players stand around until the ball reappears at ~62340.
        r = a + KICKOFF_OFFSET
        while r < a + KICKOFF_OFFSET + 500 and nip[r]:
            r += 1
        s = r
        while s > 0 and nip[s - 1]:
            s -= 1
        return s, r
    lo, hi = a + SEARCH[0], a + SEARCH[1]
    a0 = max(a - 500, 0)  # a tag in the first 20 s must not wrap around to the end
    for s, e in runs(nip[a0:hi]):
        s, e = s + a0, e + a0
        if e >= lo and e - s >= MIN_STRETCH and e < hi:
            return s, e
    return a + DEFAULT_OFFSET - 50, a + DEFAULT_OFFSET


def dead_from_restarts(df, pitch, restarts, with_frames=False):
    """restarts: [(tag_start_frame, is_kickoff)]. Optionally also return the restart frames."""
    nip = not_in_play(df, pitch)
    dead = np.zeros(len(df), dtype=bool)
    frames = []
    for a, kickoff in restarts:
        s, r = restart_frame(nip, a, kickoff)
        dead[s:r] = True
        frames.append(r)
    return (dead, frames) if with_frames else dead


THROW_IN_GUESS = False  # no team on the tag (throw-ins): give it to the team that didn't have it last


def restart_team(labels, restarts, teams, max_frames=125):
    """The team taking a set piece has the ball first. teams: 'H', 'A' or None (throw-ins: N/A).

    If our first possession after the restart goes to the other team and switches within
    max_frames (5 s), that first bit was the taker's team.
    """
    labels = labels.copy()
    for r, team in zip(restarts, teams):
        if team is None and THROW_IN_GUESS and r < len(labels):
            c = r - 1
            while c > 0 and labels[c] not in ("H", "A"):
                c -= 1
            team = {"H": "A", "A": "H"}.get(labels[c])
        if team is None or r >= len(labels) or labels[r] not in ("H", "A") or labels[r] == team:
            continue
        c = r
        while c < len(labels) and labels[c] == labels[r]:
            c += 1
        if c - r <= max_frames:
            labels[r:c] = team
    return labels


def dead_after_goals(df, goals):
    """goals: [(goal window start, kickoff tag start)] -> dead from the goal to the kickoff.

    The tracker loses the ball once it's in the net: the window shows the attack (ball seen),
    then nothing until the kickoff. Goal moment = end of the last stretch with the ball
    seen (5 s+, so not the ball being placed for kickoff) that ends at least 20 s before the kickoff.
    A quick attack may show the ball for under 5 s: then fall back to 1 s+.
    Checked on stills: goal 1 scoreboard flips 0-0 -> 1-0 between 46700 and 47200 (rule: 46678).
    """
    seen = df["ball_x"].notna().to_numpy()
    dead = np.zeros(len(df), dtype=bool)
    for g, k in goals:
        r = k + KICKOFF_OFFSET
        for min_len in (125, 25):
            ends = [g + e for s, e in runs(seen[g:r]) if e - s >= min_len and r - (g + e) >= 500]
            if ends:
                dead[ends[-1]:r] = True
                break
    return dead


def dead_at_edges(df, segments, kickoffs):
    """Before each half's kickoff, and whenever fewer than MIN_PLAYERS players are tracked."""
    n = df.filter(regex=r"^\d+_x$").notna().sum(axis=1).to_numpy()
    dead = n < MIN_PLAYERS
    for (a, b), k in zip(segments, kickoffs):
        dead[a:min(b, k)] = True
    return dead


def tag_inputs():
    """From the real match's Smart Tagging: restarts [(tag start, is_kickoff)], the team taking
    each ('H', 'A' or None for throw-ins), each half's kickoff frame, goals [(window start, kickoff tag start)]."""
    ev = load_tags()
    sp = ev[ev.code.str.upper() == "SET PIECES"].sort_values("a")
    types = sp["Type"].astype(str).str.lower().tolist()
    restarts = [(int(a), "kick off" in t) for a, t in zip(sp.a, types)]
    teams = [None if str(x) in ("N/A", "nan") else ("H" if str(x) == HOME_NAME else "A") for x in sp["Team"]]
    kickoffs = sorted(int(a) + KICKOFF_OFFSET for a, t in zip(sp.a, types) if "kick off (start)" in t)
    after_goal = sorted(int(a) for a, t in zip(sp.a, types) if "after goal" in t)
    goals = []
    for r in ev[ev.code.str.upper() == "GOALS"].itertuples():
        k = [x for x in after_goal if r.a <= x <= r.b]
        if k:
            goals.append((int(r.a), k[0]))
    return restarts, teams, kickoffs, goals
