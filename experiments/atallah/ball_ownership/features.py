"""Per-frame kinematic features for the ball-ownership rule (TIKI-13). Pure numpy/scipy, no I/O.

Everything is in metres and seconds at 25 fps. NaN means "not seen" and is preserved: a velocity
needs both neighbours, a direction change needs six, so gaps grow by a few frames on each side.

    B, P, team_of, ids = arrays_from_df(df, teams, pitch)   # (N,2), (N,K,2), (K,) 'H'/'A', [ids]
    Bs = smooth_ball(B)                                      # Savitzky-Golay order 2 window 7
    D = dist_matrix(Bs, P)                                   # (N,K) metres, NaN -> inf
    V, speed, med5 = ball_velocity(Bs)                       # central difference, 5-frame median
    PV, n_swaps = player_velocity(P)                         # NaN where a slot implies > 12 m/s
    theta, s_in, s_out = direction_change(V)                 # degrees between 3-frame mean velocities
    local_max(theta), local_min(d)                           # extremum masks for the touch frame

Practice-match frames have no speed column, so every velocity here is a position difference.
"""

import warnings

import numpy as np
from scipy.signal import savgol_filter

import _paths
from sticky import runs

FPS = 25.0
SG_WINDOW = 7       # Vidal-Codina et al. 2022 / databallpy default
SG_ORDER = 2
SWAP_MS = 12.0      # p99.9 of honest slot steps on the real match is ~9 m/s; 10-12 is clean
TURN_HALF = 3       # frames each side for the in/out mean velocity of direction_change


def arrays_from_df(df, teams, pitch):
    """B (N,2) ball metres, P (N,K,2) slot metres, team_of (K,) 'H'/'A', ids (K,).

    teams: [home_ids, away_ids] as sticky.players_by_team gives them (home first). Coordinates in
    df are 0..1 fractions of the pitch (kloppy Metrica convention), scaled by pitch=(length, width).
    """
    home, away = list(teams[0]), list(teams[1])
    ids = home + away
    team_of = np.array(["H"] * len(home) + ["A"] * len(away), dtype="<U1")
    B = np.column_stack([df["ball_x"].to_numpy(dtype=float) * pitch[0],
                         df["ball_y"].to_numpy(dtype=float) * pitch[1]])
    px = df[[i + "_x" for i in ids]].to_numpy(dtype=float) * pitch[0]
    py = df[[i + "_y" for i in ids]].to_numpy(dtype=float) * pitch[1]
    P = np.stack([px, py], axis=-1)
    return B, P, team_of, ids


def visible(B):
    """bool (N,): both coordinates present."""
    return ~np.isnan(B).any(axis=1)


def smooth_ball(B, window=SG_WINDOW, order=SG_ORDER):
    """Savitzky-Golay per contiguous visible run; runs shorter than the window stay raw; NaN kept."""
    out = np.array(B, dtype=float, copy=True)
    for s, e in runs(visible(B)):
        if e - s >= window:
            out[s:e] = savgol_filter(B[s:e], window, order, axis=0, mode="interp")
    return out


def dist_matrix(B, P):
    """(N,K) ball-to-slot distance in metres; NaN (ball or slot unseen) -> inf."""
    d = np.sqrt(((P - B[:, None, :]) ** 2).sum(axis=-1))
    d[np.isnan(d)] = np.inf
    return d


def ball_velocity(B, fps=FPS, median_frames=5):
    """V (N,2) m/s by central difference (NaN where a neighbour is missing), speed (N,), and the
    centred `median_frames` running median of speed (NaN only where every frame in the window is)."""
    V = np.full_like(B, np.nan, dtype=float)
    V[1:-1] = (B[2:] - B[:-2]) * (fps / 2.0)
    speed = np.sqrt((V ** 2).sum(axis=1))
    med = _nan_running_median(speed, median_frames)
    return V, speed, med


def _nan_running_median(x, window):
    half = window // 2
    n = len(x)
    pad = np.concatenate([np.full(half, np.nan), x, np.full(half, np.nan)])
    stack = np.stack([pad[k:k + n] for k in range(window)], axis=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)      # all-NaN windows give NaN, silently
        return np.nanmedian(stack, axis=1)


def player_velocity(P, fps=FPS, swap_ms=SWAP_MS):
    """PV (N,K,2) m/s by central difference, NaN where either step into the frame implies more than
    swap_ms (an identity swap or teleport, not a run). Returns (PV, n_fires) with n_fires the
    number of slot-frames the guard blanked."""
    step = np.full(P.shape[:2], np.nan)                      # step[i] = speed from i-1 to i
    step[1:] = np.sqrt(((P[1:] - P[:-1]) ** 2).sum(axis=-1)) * fps
    PV = np.full_like(P, np.nan, dtype=float)
    PV[1:-1] = (P[2:] - P[:-2]) * (fps / 2.0)
    with np.errstate(invalid="ignore"):
        bad = step > swap_ms                                 # frame i, from the step into it
    fires = bad.copy()
    fires[:-1] |= bad[1:]                                    # and frame i-1, the step out of it
    PV[fires] = np.nan
    return PV, int(fires.sum())


def swap_mask(P, fps=FPS, swap_ms=SWAP_MS):
    """bool (N,K): the slot's step into or out of this frame implies more than swap_ms."""
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
    """theta (N,) degrees between the incoming and outgoing `half`-frame mean velocities (frames
    i-half..i-1 and i+1..i+half), plus the two mean speeds s_in, s_out. NaN where undefined."""
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
    x = np.asarray(x, dtype=float)
    return local_max(-x)


def event_vertices(mask, score):
    """For each run of True in mask, the frame with the largest score: the touch vertex."""
    out = []
    for s, e in runs(np.asarray(mask, dtype=bool)):
        seg = np.where(np.isfinite(score[s:e]), score[s:e], -np.inf)
        out.append(s + int(np.argmax(seg)))
    return np.array(out, dtype=int)
