"""Approach 1: sticky possession.

The ball stays with a team until the other team clearly has it. Three rules:

  1. A team is "near the ball" on a frame when one of its players is within ZONE_M metres of it
     and either nobody from the other team is ("alone" rule, the original) or the nearest
     opponent is at least MARGIN_M further away ("closest" rule). Otherwise contested or in
     flight, which changes nothing.
  2. Possession switches when the other team has been near the ball for SWITCH_FRAMES frames in a
     row. The switch is dated back to the first of those frames, so we are not late.
  3. Ball missing for DEAD_FRAMES frames or more = stoppage (D). Shorter gaps keep the current
     team.

Works on any kloppy tracking dataset, so the same code runs on the practice match now and the
real match later.

    python prep/sticky.py        # writes sticky.csv next to the baselines for both practice sets
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sample_game import META, PITCH, RAW, SAMPLE, drop_ball  # noqa: E402
from baseline import write_submission  # noqa: E402

# Params. Football sense, except SWITCH_FRAMES: picked on the practice match (row 8 in docs/notes.md).
ZONE_M = 1.5          # a player this close to the ball can be on it (2.0 before row 11)
SWITCH_FRAMES = 8     # 0.32 s of the other team on the ball before possession changes (was 12 before row 8)
DEAD_FRAMES = 75      # 3 s without a ball = stoppage
MARGIN_M = 0.5        # "closest" rule: must be this much closer than the nearest opponent (1.0 before row 11)


def team_distances(df, players_by_team, pitch=PITCH):
    """(home, away) per-frame distance in metres from the ball to that team's closest player."""
    bx = df["ball_x"].to_numpy()[:, None] * pitch[0]
    by = df["ball_y"].to_numpy()[:, None] * pitch[1]
    out = []
    for ids in players_by_team:
        px = df[[i + "_x" for i in ids]].to_numpy() * pitch[0]
        py = df[[i + "_y" for i in ids]].to_numpy() * pitch[1]
        d = np.sqrt((px - bx) ** 2 + (py - by) ** 2)
        d[np.isnan(d)] = np.inf
        out.append(d.min(axis=1))
    return out


def runs(mask):
    """[(start, stop)] of consecutive True."""
    edges = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def dead_from_missing_ball(ball_seen):
    """Rule 3: the ball missing for DEAD_FRAMES or more is a stoppage."""
    dead = np.zeros(len(ball_seen), dtype=bool)
    for start, stop in runs(~ball_seen):
        if stop - start >= DEAD_FRAMES:
            dead[start:stop] = True
    return dead


def sticky_segment(near, dead):
    """Labels for one half. near: 'H' / 'A' / '' per frame. dead: stoppage mask."""
    labels = np.full(len(near), "D", dtype="<U1")

    team = None  # carries across short stretches only if nothing confirms otherwise
    for start, stop in runs(~dead):
        # Confirmed switches inside this stretch: (frame, team).
        switches = []
        run_team, run_start = "", start
        for i in range(start, stop):
            if near[i] != run_team:
                run_team, run_start = near[i], i
            if run_team and i - run_start + 1 == SWITCH_FRAMES:
                if not switches or switches[-1][1] != run_team:
                    switches.append((run_start, run_team))
        if not switches:
            if team is None:
                continue  # nothing to say: stays D
            labels[start:stop] = team
            continue
        # Before the first confirmed team in a stretch (a restart), that team already had it.
        labels[start:switches[0][0]] = switches[0][1]
        for (s, t), nxt in zip(switches, switches[1:] + [(stop, None)]):
            labels[s:nxt[0]] = t
        team = switches[-1][1]
    return labels


def sticky_labels(df, players_by_team, segments, rule="alone", dead=None, pitch=PITCH):
    """dead: a stoppage mask from elsewhere (e.g. prep/stoppage.py). None = rule 3."""
    d_home, d_away = team_distances(df, players_by_team, pitch)
    if rule == "alone":
        home_on, away_on = d_away > ZONE_M, d_home > ZONE_M
    else:  # "closest"
        home_on, away_on = d_home + MARGIN_M <= d_away, d_away + MARGIN_M <= d_home
    near = np.where((d_home <= ZONE_M) & home_on, "H",
                    np.where((d_away <= ZONE_M) & away_on, "A", ""))
    if dead is None:
        dead = dead_from_missing_ball(~np.isnan(df["ball_x"].to_numpy()))
    labels = np.full(len(df), "X", dtype="<U1")
    for start, stop in segments:
        labels[start:stop] = sticky_segment(near[start:stop], dead[start:stop])
    return labels


def players_by_team(dataset):
    return [[p.player_id for p in team.players] for team in dataset.metadata.teams]


def period_segments(df):
    """[(start, stop)] rows of each period."""
    periods = df["period_id"].to_numpy()
    return [(int(np.flatnonzero(periods == p)[0]), int(np.flatnonzero(periods == p)[-1]) + 1)
            for p in np.unique(periods)]


def main():
    import pandas as pd
    from kloppy import metrica

    ds = metrica.load_tracking_epts(meta_data=META, raw_data=RAW)
    df = ds.to_df()
    segments = period_segments(df)

    gt = pd.read_csv(os.path.join(SAMPLE, "sample_gt.csv"))["label"].to_numpy()
    alive = np.isin(gt, ["H", "A"])
    teams = players_by_team(ds)
    for folder, frame in (("results", df), ("results_noisy", drop_ball(df, alive))):
        for name, rule in (("sticky", "alone"), ("sticky_closest", "closest")):
            path = os.path.join(SAMPLE, folder, name + ".csv")
            write_submission(path, sticky_labels(frame, teams, segments, rule))
            print("wrote", path)


if __name__ == "__main__":
    main()
