"""Approach 9: ball ownership from touches, not proximity (row 9 in docs/notes.md).

The team label changes only when the other team visibly gains the ball. Per half, two per-frame
arrays feed one sticky state machine (segment_labels, a generalised prep/sticky.sticky_segment):

  near[i]     the team with a player inside ZONE_M of the smoothed ball while the other team has
              nobody inside ZONE_M + EXIT_M ("" in a duel, in flight, or with the ball unseen).
              HOLD_FRAMES near frames in a row confirm a switch, as in row 8 but with a 1 m zone.
  instant[i]  the team at each confirmed GAIN: a touch vertex (the ball turns by more than
              TURN_DEG or its speed changes by more than DSPEED_MS between the 3-frame windows
              either side, with max(in, out) speed above MIN_SPEED_MS) while one of that team's
              players is inside the zone and nobody from the other team is within ZONE_M + EXIT_M.
              Also a dated switch inside a ball gap when the first confirmed holder after the gap
              is the other team (extrapolated arrival, else the gap midpoint).

Loss is implicit: flight, loose balls and gaps stay with the last team. A duel (both teams within
DUEL_M) freezes the label. A touch with nobody in the zone is noise. An instant spell shorter than
MIN_SPELL frames that bounces straight back to the previous team is a deflection and is dropped.
Headers cannot be seen (no height): accepted.

Pure numpy/pandas/scipy; kloppy only inside main(). The reference implementation this was promoted
from is experiments/atallah/ball_ownership/ (features.py, ball_rule.py, rules.segment_labels);
test_promotion.py there checks the two agree frame for frame on the practice match.

    python prep/ball_ownership.py   # writes ball_ownership.csv for both practice sets
"""

import os
import sys

import numpy as np
from scipy.signal import savgol_filter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sticky import PITCH, runs  # noqa: E402

FPS = 25.0

# Params. Picked on the practice match (row 9 in docs/notes.md).
ZONE_M = 1.0          # a player this close to the smoothed ball is a candidate holder
DUEL_M = 1.0          # both teams this close: duel, label frozen
EXIT_M = 0.10         # the other team must be outside ZONE_M + EXIT_M for a gain / near frame
TURN_DEG = 10.0       # direction change that counts as a touch
DSPEED_MS = 5.0       # speed change that counts as a touch
MIN_SPEED_MS = 1.5    # max(in, out) speed below this: no touch (a still ball jitters)
HOLD_FRAMES = 8       # near frames that confirm a switch without a touch (0.32 s)
MIN_SPELL = 8         # instant spells shorter than this that bounce straight back are deflections
DATE_BACK = 0         # frames added to each near-confirmed switch
SWAP_MS = 12.0        # a player step faster than this is an identity swap: not a candidate that frame
GAP_EXTRAP_S = 1.0    # how far the last ball velocity is extrapolated into a gap
REALITY_M = 2.0       # extrapolated ball within this of a new-team player = arrival; "near enough"

SG_WINDOW = 7         # Savitzky-Golay smoothing of the ball track (Vidal-Codina et al. 2022)
SG_ORDER = 2
TURN_HALF = 3         # frames each side for the in/out mean velocity of a direction change
TOUCH_WINDOW = 2      # frames either side of a vertex searched for the player on the ball

DEFAULTS = dict(
    zone_m=ZONE_M, duel_m=DUEL_M, exit_m=EXIT_M, turn_deg=TURN_DEG, dspeed_ms=DSPEED_MS,
    min_speed_ms=MIN_SPEED_MS, hold_frames=HOLD_FRAMES, min_spell=MIN_SPELL, date_back=DATE_BACK,
    swap_ms=SWAP_MS, gap_extrap_s=GAP_EXTRAP_S, reality_m=REALITY_M,
)


# ---------------------------------------------------------------------------------------------
# kinematic features (metres, seconds; NaN = not seen and stays NaN)
# ---------------------------------------------------------------------------------------------

def arrays_from_df(df, players_by_team, pitch):
    """B (N,2) ball metres, P (N,K,2) player metres, team_of (K,) 'H'/'A'. Home team first."""
    home, away = list(players_by_team[0]), list(players_by_team[1])
    ids = home + away
    team_of = np.array(["H"] * len(home) + ["A"] * len(away), dtype="<U1")
    B = np.column_stack([df["ball_x"].to_numpy(dtype=float) * pitch[0],
                         df["ball_y"].to_numpy(dtype=float) * pitch[1]])
    px = df[[i + "_x" for i in ids]].to_numpy(dtype=float) * pitch[0]
    py = df[[i + "_y" for i in ids]].to_numpy(dtype=float) * pitch[1]
    return B, np.stack([px, py], axis=-1), team_of


def visible(B):
    """bool (N,): both ball coordinates present."""
    return ~np.isnan(B).any(axis=1)


def smooth_ball(B, window=SG_WINDOW, order=SG_ORDER):
    """Savitzky-Golay per contiguous visible run; runs shorter than the window stay raw."""
    out = np.array(B, dtype=float, copy=True)
    for s, e in runs(visible(B)):
        if e - s >= window:
            out[s:e] = savgol_filter(B[s:e], window, order, axis=0, mode="interp")
    return out


def dist_matrix(B, P):
    """(N,K) ball-to-player distance in metres; NaN (ball or player unseen) -> inf."""
    d = np.sqrt(((P - B[:, None, :]) ** 2).sum(axis=-1))
    d[np.isnan(d)] = np.inf
    return d


def ball_velocity(B, fps=FPS):
    """(N,2) m/s by central difference, NaN where a neighbour is missing."""
    V = np.full_like(B, np.nan, dtype=float)
    V[1:-1] = (B[2:] - B[:-2]) * (fps / 2.0)
    return V


def swap_mask(P, fps=FPS, swap_ms=SWAP_MS):
    """bool (N,K): the player's step into or out of this frame implies more than swap_ms."""
    step = np.full(P.shape[:2], np.nan)
    step[1:] = np.sqrt(((P[1:] - P[:-1]) ** 2).sum(axis=-1)) * fps
    with np.errstate(invalid="ignore"):
        bad = step > swap_ms
    out = bad.copy()
    out[:-1] |= bad[1:]
    return out


def _window_mean(V, lo, hi):
    """Mean of V over frames i+lo .. i+hi inclusive (NaN if any is missing)."""
    n = len(V)
    acc = np.zeros_like(V, dtype=float)
    for k in range(lo, hi + 1):
        shifted = np.full_like(V, np.nan, dtype=float)
        if k >= 0:
            shifted[:n - k] = V[k:]
        else:
            shifted[-k:] = V[:n + k]
        acc += shifted
    return acc / float(hi - lo + 1)


def direction_change(V, half=TURN_HALF):
    """theta (N,) degrees between the incoming and outgoing `half`-frame mean velocities, plus
    the two mean speeds s_in, s_out. NaN where undefined."""
    v_in = _window_mean(V, -half, -1)
    v_out = _window_mean(V, 1, half)
    s_in = np.sqrt((v_in ** 2).sum(axis=1))
    s_out = np.sqrt((v_out ** 2).sum(axis=1))
    with np.errstate(invalid="ignore", divide="ignore"):
        cos = (v_in * v_out).sum(axis=1) / (s_in * s_out)
    theta = np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))
    theta[~np.isfinite(cos)] = np.nan
    return theta, s_in, s_out


def local_max(x):
    """bool (N,): x[i] is finite and >= both neighbours (edges count as neighbours of -inf)."""
    x = np.asarray(x, dtype=float)
    y = np.where(np.isfinite(x), x, -np.inf)
    left = np.concatenate([[-np.inf], y[:-1]])
    right = np.concatenate([y[1:], [-np.inf]])
    return np.isfinite(x) & (y >= left) & (y >= right)


def local_min(x):
    """bool (N,): x[i] is finite and <= both neighbours."""
    return local_max(-np.asarray(x, dtype=float))


# ---------------------------------------------------------------------------------------------
# near / instant arrays for one half
# ---------------------------------------------------------------------------------------------

def _team_min(D, mask):
    if not mask.any():
        return np.full(D.shape[0], np.inf)
    return D[:, mask].min(axis=1)


def near_instant(B, P, team_of, dead, p, fps=FPS):
    """(near, instant) for one half. B (n,2), P (n,K,2) metres; dead bool (n,)."""
    n = len(B)
    zone, clear = float(p["zone_m"]), float(p["zone_m"]) + float(p["exit_m"])
    duel_m = float(p["duel_m"])

    Bs = smooth_ball(B)
    D = dist_matrix(Bs, P)
    D[swap_mask(P, fps, float(p["swap_ms"]))] = np.inf
    home = team_of == "H"
    dH, dA = _team_min(D, home), _team_min(D, ~home)

    # near: one team inside the zone, the other clear, no duel
    duel = (dH <= duel_m) & (dA <= duel_m)
    near = np.where((dH <= zone) & (dA > clear) & ~duel, "H",
                    np.where((dA <= zone) & (dH > clear) & ~duel, "A", "")).astype("<U1")

    # touches: a direction or speed change at an extremum with a player in the zone
    V = ball_velocity(Bs, fps)
    theta, s_in, s_out = direction_change(V)
    ds = np.abs(s_out - s_in)
    with np.errstate(invalid="ignore"):
        fast = np.fmax(s_in, s_out) > float(p["min_speed_ms"])
        turn = fast & (theta > float(p["turn_deg"]))
        kick = fast & (ds > float(p["dspeed_ms"]))
    # The touch frame is an extremum: the vertex of the turn or speed change, or the closest
    # approach of a player while the ball turns (two touches a few frames apart share one hump).
    dmin = np.minimum(dH, dA)
    closest = local_min(np.where(np.isfinite(dmin), dmin, np.nan)) & (dmin <= zone)
    vertices = np.flatnonzero((turn & local_max(theta)) | (kick & local_max(ds)) | ((turn | kick) & closest))
    instant = np.full(n, "", dtype="<U1")
    for v in vertices:
        lo, hi = max(0, v - TOUCH_WINDOW), min(n, v + TOUCH_WINDOW + 1)
        dh, da = dH[lo:hi].min(), dA[lo:hi].min()
        if min(dh, da) > zone:
            continue                          # nobody on the ball: a bounce or tracker noise
        if dh <= clear and da <= clear:
            continue                          # both on the ball: frozen
        if dead[v]:
            continue
        instant[v] = "H" if dh < da else "A"

    _gap_switches(Bs, P, V, team_of, dH, dA, near, instant, dead, p, fps)
    return near, instant


def _gap_switches(Bs, P, V, team_of, dH, dA, near, instant, dead, p, fps):
    """Write instant switches inside ball gaps when the holder after the gap is the other team."""
    n = len(Bs)
    hold = int(p["hold_frames"])
    reality = float(p["reality_m"])
    horizon = int(round(float(p["gap_extrap_s"]) * fps))
    idx = np.arange(n)

    weak = (near != "") | (instant != "")
    last_weak = np.maximum.accumulate(np.where(weak, idx, -1))
    confirmed = instant != ""
    for team in ("H", "A"):
        for s, e in runs(near == team):
            if e - s >= hold:
                confirmed[s] = True
    next_conf = np.minimum.accumulate(np.where(confirmed, idx, n)[::-1])[::-1]

    for gs, ge in runs(~visible(Bs)):
        if gs == 0 or ge >= n:
            continue
        j = last_weak[gs - 1]
        f = next_conf[ge]
        if j < 0 or f >= n or dead[j:gs].any() or dead[ge:f + 1].any():
            continue
        pre = instant[j] if instant[j] else near[j]
        post = instant[f] if instant[f] else near[f]
        if pre == post:
            continue
        d_post = dH if post == "H" else dA
        if d_post[ge] > reality:
            continue                          # the ball reappears away from them: switch is visible
        slots = np.flatnonzero(team_of == post)
        t = _arrival(Bs, P, V, slots, gs, min(ge, gs + horizon), reality, fps)
        if t is None:
            t = (gs + ge) // 2
        if dead[t]:
            live = np.flatnonzero(~dead[gs:ge])
            if not len(live):
                continue
            t = gs + live[np.argmin(np.abs(live - (t - gs)))]
        if not instant[t]:
            instant[t] = post


def _arrival(Bs, P, V, slots, gs, lim, reality, fps):
    """First gap frame where the ball, extrapolated with its last velocity, is within `reality` of
    a player of the new team; None when it never is (or no velocity is known)."""
    if lim <= gs:
        return None
    v0 = V[max(0, gs - 4):gs - 1]
    v0 = v0[~np.isnan(v0).any(axis=1)]
    if not len(v0):
        return None
    v0 = v0.mean(axis=0)
    ts = np.arange(gs, lim)
    X = Bs[gs - 1] + v0[None, :] * ((ts - (gs - 1)) / fps)[:, None]
    d = np.sqrt(((P[ts][:, slots, :] - X[:, None, :]) ** 2).sum(axis=-1))
    d[np.isnan(d)] = np.inf
    hit = np.flatnonzero(d.min(axis=1) <= reality)
    return int(ts[hit[0]]) if len(hit) else None


# ---------------------------------------------------------------------------------------------
# sticky state machine (prep/sticky.sticky_segment, generalised)
# ---------------------------------------------------------------------------------------------

def segment_labels(near, dead, switch_frames=HOLD_FRAMES, date_back=0, instant=None, min_spell=0):
    """Labels for one half.

    near:      "H" / "A" / "" per frame. A team near the ball for `switch_frames` frames in a row
               is a confirmed switch, dated to the first of those frames.
    dead:      bool stoppage mask. Dead frames are "D"; the team carries across a live stretch
               with no confirmed switch, and a restart belongs to the first team confirmed in it.
    instant:   optional "H" / "A" / "" per frame. A non-empty value forces a switch at that frame
               without confirmation and restarts the confirmation count.
    date_back: integer added to each near-confirmed switch frame (negative = earlier), clamped to
               the live stretch and kept between its neighbours. Instant switches are not moved.
    min_spell: an instant-caused spell shorter than this, never confirmed by a near run of its own
               team, and followed by a switch back to the team before it, is dropped (deflection).

    With switch_frames=8, date_back=0, instant=None, min_spell=0 this equals sticky_segment.
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


# ---------------------------------------------------------------------------------------------

def ball_ownership_labels(df, players_by_team, segments, dead, pitch=PITCH, **params):
    """'<U1' labels, len(df): 'X' outside the segments, H / A / D inside.

    dead: bool stoppage mask, len(df) (e.g. ball out | players slow, as prep/run_real.py builds).
    params: any key of DEFAULTS; anything else raises ValueError.
    """
    unknown = set(params) - set(DEFAULTS)
    if unknown:
        raise ValueError("unknown ball_ownership params {}; known: {}".format(
            sorted(unknown), sorted(DEFAULTS)))
    p = dict(DEFAULTS)
    p.update(params)
    B, P, team_of = arrays_from_df(df, players_by_team, pitch)
    dead = np.asarray(dead, dtype=bool)
    out = np.full(len(df), "X", dtype="<U1")
    for start, stop in segments:
        near, instant = near_instant(B[start:stop], P[start:stop], team_of, dead[start:stop], p)
        out[start:stop] = segment_labels(
            near, dead[start:stop], switch_frames=int(p["hold_frames"]), date_back=int(p["date_back"]),
            instant=instant, min_spell=int(p["min_spell"]))
    return out


def main():
    import pandas as pd
    from kloppy import metrica

    from sample_game import META, RAW, SAMPLE, drop_ball
    from sticky import period_segments, players_by_team
    from ball_out import dead_from_ball_out
    from stoppage import dead_from_players
    from baseline import write_submission

    ds = metrica.load_tracking_epts(meta_data=META, raw_data=RAW)
    df = ds.to_df()
    segments = period_segments(df)
    teams = players_by_team(ds)
    speed_dead = dead_from_players(df, sum(teams, []), segments)

    gt = pd.read_csv(os.path.join(SAMPLE, "sample_gt.csv"))["label"].to_numpy()
    alive = np.isin(gt, ["H", "A"])
    for folder, frame in (("results", df), ("results_noisy", drop_ball(df, alive))):
        dead = dead_from_ball_out(frame, segments) | speed_dead
        path = os.path.join(SAMPLE, folder, "ball_ownership.csv")
        write_submission(path, ball_ownership_labels(frame, teams, segments, dead))
        print("wrote", path)


if __name__ == "__main__":
    main()
