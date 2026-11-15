"""Ball ownership: who has the ball while play is live, from touches rather than proximity (TIKI-13).

Team-level state on top of rules.segment_labels. Per segment this module builds two per-frame
arrays and hands them to the shared state machine:

  near[i]     team with a slot inside zone_m of the smoothed ball while the other team has nobody
              inside zone_m + exit_m ("" in a duel, in flight, or when the ball is unseen). A near
              run of hold_frames confirms a switch (the row 8 mechanism, with a 1 m zone).
  instant[i]  team at each confirmed GAIN: a touch vertex (ball turns by more than turn_deg or its
              speed changes by more than dspeed_ms between the 3-frame windows either side, with
              max(in, out) above min_speed_ms) while a slot of that team is inside the zone and the
              other team is not within zone_m + exit_m. Placed at the extremum (vertex) frame.
              Also the dated switch inside a ball gap when the first confirmed holder after the
              gap is the other team (extrapolated arrival, else the gap midpoint).

Loss is implicit: the label only changes on a confirmed gain by the other team, so flight, loose
balls and gaps stay with the last controller. A duel (both teams within duel_m) freezes the label.
A touch vertex with no slot inside the zone is ignored as noise. min_spell drops an instant spell
that reverts to the previous team within min_spell frames without a confirmation of its own
(a deflection). Headers cannot be seen (no height): accepted.

    uv run --with numpy --with pandas --with kloppy --with scipy \
        python experiments/atallah/ball_ownership/ball_rule.py --set both --mode both [harness args]

__main__ registers the variant in rules.VARIANTS (if the hook has not) and runs harness.main().
"""

import sys

import numpy as np

import _paths
from sticky import runs

import features as F
import rules

FPS = 25.0
TOUCH_WINDOW = 2    # frames either side of a vertex searched for the slot on the ball

DEFAULTS = dict(
    zone_m=1.0,        # a slot this close to the smoothed ball is a candidate holder
    duel_m=1.0,        # both teams this close: duel, label frozen
    turn_deg=10.0,     # direction change that counts as a touch
    dspeed_ms=5.0,     # speed change that counts as a touch
    exit_m=0.10,       # the other team must be outside zone_m + exit_m for a gain / near frame
    min_speed_ms=1.5,  # max(in, out) speed below this: no touch (a still ball jitters)
    hold_frames=8,     # near frames that confirm a switch without a touch
    min_spell=8,       # instant spells shorter than this that bounce straight back are deflections
    date_back=0,       # frames added to each near-confirmed switch
    swap_ms=12.0,      # a slot step faster than this is an identity swap: not a candidate that frame
    gap_extrap_s=1.0,  # how far the last ball velocity is extrapolated into a gap
    reality_m=2.0,     # extrapolated ball within this of a new-team slot = arrival; also "near enough"
)


def _team_min(D, mask):
    if not mask.any():
        return np.full(D.shape[0], np.inf)
    return D[:, mask].min(axis=1)


def near_instant(B, P, team_of, dead, p, fps=FPS):
    """(near, instant, stats) for one segment. B (n,2), P (n,K,2) metres; dead bool (n,)."""
    n = len(B)
    zone, clear = float(p["zone_m"]), float(p["zone_m"]) + float(p["exit_m"])
    duel_m, hold = float(p["duel_m"]), int(p["hold_frames"])
    stats = {}

    Bs = F.smooth_ball(B)
    D = F.dist_matrix(Bs, P)
    swaps = F.swap_mask(P, fps, float(p["swap_ms"]))
    stats["swap_slot_frames"] = int(swaps.sum())
    D[swaps] = np.inf
    home = team_of == "H"
    dH, dA = _team_min(D, home), _team_min(D, ~home)

    # --- near: one team inside the zone, the other clear -------------------------------------
    duel = (dH <= duel_m) & (dA <= duel_m)
    near = np.where((dH <= zone) & (dA > clear) & ~duel, "H",
                    np.where((dA <= zone) & (dH > clear) & ~duel, "A", "")).astype("<U1")
    stats["near_share"] = float((near != "").mean()) if n else 0.0
    stats["duel_frames"] = int(duel.sum())

    # --- touches: direction or speed change at an extremum with a slot in the zone ------------
    V, _, _ = F.ball_velocity(Bs, fps)
    theta, s_in, s_out = F.direction_change(V)
    ds = np.abs(s_out - s_in)
    with np.errstate(invalid="ignore"):
        fast = np.fmax(s_in, s_out) > float(p["min_speed_ms"])
        turn = fast & (theta > float(p["turn_deg"]))
        kick = fast & (ds > float(p["dspeed_ms"]))
    # A touch frame is an extremum: the vertex of the turn or speed change, or the closest approach
    # of a slot while the ball is turning (two touches a few frames apart share one blurred hump).
    dmin = np.minimum(dH, dA)
    closest = F.local_min(np.where(np.isfinite(dmin), dmin, np.nan)) & (dmin <= zone)
    vertices = np.flatnonzero((turn & F.local_max(theta)) | (kick & F.local_max(ds)) | ((turn | kick) & closest))
    instant = np.full(n, "", dtype="<U1")
    n_gain = n_noise = n_duel = 0
    for v in vertices:
        lo, hi = max(0, v - TOUCH_WINDOW), min(n, v + TOUCH_WINDOW + 1)
        dh, da = dH[lo:hi].min(), dA[lo:hi].min()
        if min(dh, da) > zone:
            n_noise += 1                      # nobody on the ball: a bounce or tracker noise
            continue
        if dh <= clear and da <= clear:
            n_duel += 1                       # both on the ball: frozen
            continue
        if dead[v]:
            continue
        instant[v] = "H" if dh < da else "A"
        n_gain += 1
    stats.update(vertices=int(len(vertices)), gains=n_gain, noise_vertices=n_noise, duel_vertices=n_duel)

    # --- gaps: hold; a confirmed change after the gap is dated inside it ----------------------
    stats["gap_switches"] = _gap_switches(Bs, P, V, team_of, dH, dA, near, instant, dead, p, fps)
    return near, instant, stats


def _gap_switches(Bs, P, V, team_of, dH, dA, near, instant, dead, p, fps):
    """Write instant switches inside ball gaps. Returns how many were placed."""
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

    placed = 0
    for gs, ge in runs(~F.visible(Bs)):
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
            placed += 1
    return placed


def _arrival(Bs, P, V, slots, gs, lim, reality, fps):
    """First gap frame where the ball, extrapolated with its last velocity, is within `reality` of
    a slot of the new team; None when it never is (or no velocity is known)."""
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


def _params(params):
    unknown = set(params) - set(DEFAULTS)
    if unknown:
        raise ValueError("unknown ball_ownership params {}; known: {}".format(
            sorted(unknown), sorted(DEFAULTS)))
    p = dict(DEFAULTS)
    p.update(params)
    return p


def ball_ownership(df, teams, segments, dead, pitch, **params):
    """'<U1' labels, len(df): segment_labels over the touch-based near/instant arrays; 'X' outside."""
    return _run(df, teams, segments, dead, pitch, params)[0]


def ball_ownership_stats(df, teams, segments, dead, pitch, **params):
    """(labels, stats): the same labels plus aggregate counters (nothing per frame)."""
    return _run(df, teams, segments, dead, pitch, params)


def _run(df, teams, segments, dead, pitch, params):
    p = _params(params)
    B, P, team_of, _ = F.arrays_from_df(df, teams, pitch)
    dead = np.asarray(dead, dtype=bool)
    out = np.full(len(df), "X", dtype="<U1")
    total = {}
    for start, stop in segments:
        near, instant, stats = near_instant(B[start:stop], P[start:stop], team_of, dead[start:stop], p)
        out[start:stop] = rules.segment_labels(
            near, dead[start:stop], switch_frames=int(p["hold_frames"]), date_back=int(p["date_back"]),
            instant=instant, min_spell=int(p["min_spell"]))
        for k, v in stats.items():
            total[k] = total.get(k, 0) + v
    if "near_share" in total and segments:
        total["near_share"] /= float(len(segments))
    return out, total


def register():
    """Make the variant visible to harness.py / run_real_variant.py when rules.py has no hook yet."""
    rules.VARIANTS.setdefault("ball_ownership", ball_ownership)
    for k, v in DEFAULTS.items():
        rules.DEFAULTS.setdefault(k, v)


def main(argv=None):
    import harness

    register()
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--variant" not in argv:
        argv = ["--variant", "ball_ownership"] + argv
    if "--stats" in argv:
        argv.remove("--stats")
        import cache
        S = cache.load_practice()
        for which in ("clean", "noisy"):
            df = S.df_clean if which == "clean" else S.df_noisy
            _, stats = ball_ownership_stats(df, S.teams, S.segments, S.dead[which], S.pitch,
                                            **harness.parse_params([a for a in argv if "=" in a and
                                                                    not a.startswith("--")]))
            print(which, "stats:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in stats.items()})
        return
    sys.argv = [sys.argv[0]] + argv
    harness.main()


if __name__ == "__main__":
    main()
