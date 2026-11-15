"""Unit checks for features.py and ball_rule.py on a synthetic 6-slot frame. Plain asserts.

    uv run --with numpy --with pandas --with kloppy --with scipy \
        python experiments/atallah/ball_ownership/test_rules.py

Scenes (25 fps, pitch 105 x 68, three home slots h1-h3 and three away slots a1-a3):
  (1) a teammate pass never switches
  (2) an interception switches at the touch frame
  (3) a deflection that returns to the original team within min_spell does not switch
  (4) a 30 m slot jump gives NaN player velocity and keeps the holder
  (5) a 10-frame ball gap holds the team
  (6) a gap with a team change afterwards places the switch inside the gap
  (7) segment_labels with defaults equals sticky_segment on random near/dead pairs
plus feature checks: smoothing keeps NaN, velocities are NaN at gap edges, direction change is 90
degrees at a right-angle corner.
"""

import numpy as np
import pandas as pd

import _paths
from sticky import sticky_segment

import features as F
from ball_rule import DEFAULTS, ball_ownership, ball_ownership_stats
from rules import segment_labels

PITCH = (105.0, 68.0)
FPS = 25.0
TEAMS = [["h1", "h2", "h3"], ["a1", "a2", "a3"]]
FAR = {"h3": (90.0, 60.0), "a2": (85.0, 10.0), "a3": (95.0, 40.0)}   # out of the way by default


def make_df(n, ball, players):
    """ball (n,2) metres (NaN allowed); players: id -> (n,2) metres or a fixed (x, y)."""
    cols = {"frame_id": np.arange(1, n + 1), "period_id": np.ones(n, dtype=int),
            "ball_x": ball[:, 0] / PITCH[0], "ball_y": ball[:, 1] / PITCH[1]}
    for pid in sum(TEAMS, []):
        xy = players.get(pid, FAR.get(pid, (100.0, 65.0)))
        xy = np.asarray(xy, dtype=float)
        if xy.ndim == 1:
            xy = np.tile(xy, (n, 1))
        cols[pid + "_x"], cols[pid + "_y"] = xy[:, 0] / PITCH[0], xy[:, 1] / PITCH[1]
    return pd.DataFrame(cols)


def line(p0, p1, n):
    """n points from p0 to p1 inclusive."""
    t = np.linspace(0.0, 1.0, n)[:, None]
    return np.asarray(p0, float)[None, :] * (1 - t) + np.asarray(p1, float)[None, :] * t


def dribble(start, direction, n, speed=1.0):
    """A player walking from start along direction at speed; the ball 0.4 m ahead of their feet."""
    d = np.asarray(direction, float)
    d = d / np.linalg.norm(d)
    t = np.arange(n)[:, None] / FPS
    player = np.asarray(start, float)[None, :] + d[None, :] * speed * t
    return player, player + 0.4 * d[None, :]


def travel(p0, p1, speed, t0):
    """Frames to travel p0 -> p1 at speed, and the frame of arrival from t0."""
    dist = np.linalg.norm(np.asarray(p1, float) - np.asarray(p0, float))
    frames = int(round(dist / speed * FPS))
    return frames, t0 + frames


def labels_for(df, **params):
    n = len(df)
    dead = np.zeros(n, dtype=bool)
    return ball_ownership(df, TEAMS, [(0, n)], dead, PITCH, **params)


def switch_frames(lab):
    """Frames where the label changes between H and A."""
    lab = np.asarray(lab)
    return [i for i in range(1, len(lab)) if lab[i] != lab[i - 1] and lab[i] in "HA" and lab[i - 1] in "HA"]


# ---------------------------------------------------------------------------------------------
# scenes
# ---------------------------------------------------------------------------------------------

def scene_pass(n=200, kick=40, speed=10.0, receiver="h2", recv_at=(35.0, 30.0), stop_frames=None):
    """h1 dribbles then passes 15 m to `receiver`, who controls the ball and dribbles on."""
    ball = np.full((n, 2), np.nan)
    h1, b1 = dribble((19.0, 30.0), (1.0, 0.0), n)
    ball[:kick] = b1[:kick]
    frames, arrive = travel(b1[kick], recv_at, speed, kick)
    ball[kick:arrive + 1] = line(b1[kick], recv_at, frames + 1)
    rcv, b2 = dribble(np.asarray(recv_at) - (0.4, 0.0), (0.0, 1.0), n - arrive)
    ball[arrive:] = b2
    players = {"h1": np.vstack([h1[:arrive], np.tile(h1[arrive], (n - arrive, 1))]),
               receiver: np.vstack([np.tile(rcv[0], (arrive, 1)), rcv])}
    return ball, players, arrive


def test_teammate_pass():
    ball, players, _ = scene_pass()
    lab = labels_for(make_df(len(ball), ball, players))
    assert set(lab) == {"H"}, set(lab)
    print("(1) teammate pass: all H, no switch")


def test_interception():
    n, kick, speed = 220, 40, 10.0
    ball = np.full((n, 2), np.nan)
    h1, b1 = dribble((19.0, 30.0), (1.0, 0.0), n)
    ball[:kick] = b1[:kick]
    a1 = (28.0, 30.0)                                       # on the path to h2 at (35, 30)
    frames, touch = travel(b1[kick], a1, speed, kick)
    ball[kick:touch + 1] = line(b1[kick], a1, frames + 1)
    a2 = (28.0, 12.0)                                       # a1 plays it square to a2
    frames2, arrive = travel(a1, a2, 8.0, touch)
    ball[touch:arrive + 1] = line(a1, a2, frames2 + 1)
    rcv, b2 = dribble(np.asarray(a2) - (0.0, 0.4), (-1.0, 0.0), n - arrive)
    ball[arrive:] = b2
    players = {"h1": h1, "h2": (35.0, 30.0), "a1": a1,
               "a2": np.vstack([np.tile(rcv[0], (arrive, 1)), rcv])}
    lab = labels_for(make_df(n, ball, players))
    sw = switch_frames(lab)
    assert lab[0] == "H" and lab[-1] == "A", (lab[0], lab[-1])
    assert len(sw) == 1, sw
    assert abs(sw[0] - touch) <= 2, (sw[0], touch)
    print("(2) interception: one switch at frame {} (touch at {})".format(sw[0], touch))


def test_deflection():
    n, kick, speed = 200, 40, 10.0
    ball = np.full((n, 2), np.nan)
    h1, b1 = dribble((19.0, 30.0), (1.0, 0.0), n)
    ball[:kick] = b1[:kick]
    a1 = np.array([28.0, 30.0])
    frames, touch = travel(b1[kick], a1, speed, kick)
    ball[kick:touch + 1] = line(b1[kick], a1, frames + 1)
    ang = np.radians(20.0)                                  # deflected 20 degrees, same speed
    h2 = a1 + 6 * speed / FPS * np.array([np.cos(ang), np.sin(ang)])   # 6 frames on, h2 controls it
    ball[touch:touch + 7] = line(a1, h2, 7)
    arrive = touch + 6
    rcv, b2 = dribble(h2 - (0.4, 0.0), (0.0, 1.0), n - arrive)
    ball[arrive:] = b2
    players = {"h1": h1, "a1": a1, "h2": np.vstack([np.tile(rcv[0], (arrive, 1)), rcv])}
    df = make_df(n, ball, players)
    lab = labels_for(df)                                    # min_spell = 8 by default
    assert set(lab) == {"H"}, set(lab)
    loose = labels_for(df, min_spell=0)                     # the deflection is visible without it
    assert "A" in set(loose), set(loose)
    spell = [i for i in range(n) if loose[i] == "A"]
    assert spell[-1] - spell[0] + 1 < DEFAULTS["min_spell"], (spell[0], spell[-1])
    print("(3) deflection: all H with min_spell=8; min_spell=0 shows an A spell of {} frames".format(len(spell)))


def test_slot_jump():
    n = 120
    h1, ball = dribble((30.0, 30.0), (1.0, 0.0), n)
    a1 = np.tile((80.0, 50.0), (n, 1))
    a1[50:60] = ball[50:60] + (0.6, 0.0)                    # teleports 50 m onto the ball and back
    players = {"h1": h1, "a1": a1}
    df = make_df(n, ball, players)
    B, P, team_of, ids = F.arrays_from_df(df, TEAMS, PITCH)
    PV, fires = F.player_velocity(P)
    k = ids.index("a1")
    assert np.isnan(PV[49:51, k]).all() and np.isnan(PV[59:61, k]).all(), "jump frames must be NaN"
    assert fires >= 4, fires
    assert np.isfinite(PV[20, k]).all() and np.isfinite(PV[55, k]).all()
    lab = labels_for(df)
    assert set(lab) == {"H"}, set(lab)
    print("(4) 30 m slot jump: {} slot-frames blanked, holder kept".format(fires))


def test_ball_gap_holds():
    n = 120
    h1, ball = dribble((30.0, 30.0), (1.0, 0.0), n)
    ball[50:60] = np.nan
    df = make_df(n, ball, {"h1": h1, "a1": (36.0, 31.0)})   # an opponent 4 m away during the gap
    lab = labels_for(df)
    assert set(lab) == {"H"}, set(lab)
    print("(5) 10-frame ball gap: holder kept")


def test_gap_with_change():
    n, kick, gs, ge = 220, 40, 60, 90
    ball, players, arrive = scene_pass(n=n, kick=kick, receiver="a1", recv_at=(35.0, 30.0))
    assert gs < arrive < ge, arrive                          # the arrival is hidden inside the gap
    ball[gs:ge] = np.nan
    df = make_df(n, ball, players)
    lab, stats = ball_ownership_stats(df, TEAMS, [(0, n)], np.zeros(n, dtype=bool), PITCH)
    sw = switch_frames(lab)
    assert lab[0] == "H" and lab[-1] == "A"
    assert len(sw) == 1, sw
    assert gs <= sw[0] < ge, (sw[0], gs, ge)
    assert abs(sw[0] - (arrive - 5)) <= 6, (sw[0], arrive)   # extrapolated to 2 m before the feet
    assert stats["gap_switches"] == 1, stats
    print("(6) gap with a change: switch at frame {} inside the gap [{}, {}), arrival {}".format(
        sw[0], gs, ge, arrive))


def test_segment_defaults_random():
    rng = np.random.default_rng(13)
    total = 0
    for _ in range(40):
        n = int(rng.integers(30, 300))
        near = rng.choice(np.array(["H", "A", ""]), size=n, p=[0.3, 0.3, 0.4]).astype("<U1")
        for s in range(0, n, 9):
            near[s:s + int(rng.integers(1, 9))] = near[s]
        dead = rng.random(n) < 0.08
        for s in range(0, n, 41):
            dead[s:s + int(rng.integers(0, 15))] = rng.random() < 0.3
        total += int((segment_labels(near, dead) != sticky_segment(near, dead)).sum())
    assert total == 0, total
    print("(7) segment_labels defaults == sticky_segment on 40 random pairs")


def test_features():
    n = 60
    ball = np.zeros((n, 2))
    ball[:31] = line((0.0, 0.0), (10.0, 0.0), 31)            # 10 m in 30 frames, right angle at 30
    ball[30:] = line((10.0, 0.0), (10.0, 10.0 * (n - 31) / 30.0), n - 30)
    ball[10:13] = np.nan
    Bs = F.smooth_ball(ball)
    assert np.isnan(Bs[10:13]).all() and not np.isnan(Bs[13:]).any()
    V, speed, med = F.ball_velocity(Bs)
    assert np.isnan(V[9]).all() and np.isnan(V[13]).all() and np.isfinite(V[14]).all()
    assert np.isnan(V[0]).all() and np.isnan(V[-1]).all()
    theta, s_in, s_out = F.direction_change(V)
    v = int(np.nanargmax(theta))
    assert abs(v - 30) <= 1 and 70 < theta[v] <= 90.5, (v, theta[v])
    assert np.isnan(theta[9:17]).all()                      # six-frame windows around the gap
    assert np.nanmax(np.abs(speed[18:26] - 10.0 / (30 / FPS))) < 0.5
    d = np.array([3.0, 2.0, 1.0, 2.0, np.nan, 1.5, 1.0])
    assert list(np.flatnonzero(F.local_min(d))) == [2, 6]
    print("(f) features: NaN kept, gap-edge velocities NaN, 90-degree corner found at {}".format(v))


def main():
    test_features()
    test_teammate_pass()
    test_interception()
    test_deflection()
    test_slot_jump()
    test_ball_gap_holds()
    test_gap_with_change()
    test_segment_defaults_random()
    print("all checks passed")


if __name__ == "__main__":
    main()
