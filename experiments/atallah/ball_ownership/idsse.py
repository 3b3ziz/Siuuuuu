"""Extra practice matches: the DFL / Sportec IDSSE open data set, degraded to look like our match.

Bassek, Weber, Rein & Memmert (2025), "An integrated dataset of synchronized spatiotemporal and
event data in elite soccer", Scientific Data, https://doi.org/10.1038/s41597-025-04505-y.
Seven Bundesliga matches of 25 Hz Tracab tracking, CC-BY 4.0. Every frame carries BallStatus
(1 alive, 0 dead) and BallPossession (1 home, 2 away), so the truth is the provider's and needs no
event parsing, unlike Metrica Sample Game 3 (prep/sample_game.py).

    uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/idsse.py build
    uv run --with numpy --with pandas --with kloppy --with scipy python experiments/atallah/ball_ownership/idsse.py check

Download. kloppy 3.18.0 has `sportec.load_open_tracking_data(match_id='J03WPY', sample_rate=None,
limit=None, coordinates=None, only_alive=True)`. It points at
https://springernature.figshare.com/ndownloader/files/<id>, which on 15 Nov 2026 answered
HTTP 202 with an empty body for every file (figshare's "being restored" state), and kloppy then
cached the empty body in ~/kloppy_cache and failed with "Document is empty". So this module
downloads the files itself from the figshare API, https://api.figshare.com/v2/file/download/<id>
(HTTP 200, signed S3 redirect), retrying on 202, into data/idsse/raw/, and hands the local paths
to `sportec.load_tracking(meta_data, raw_data, coordinates="metrica", only_alive=False)`.
`only_alive=False` matters: the default drops every dead frame, and we need them for D.
Fetched 15 Nov 2026 10:57 (data/idsse/download.log): J03WMX tracking 418.5 MB in 17 s, J03WN1
tracking 391.7 MB in 16 s, meta files 12 KB each. kloppy parse + to_df takes 68 s per match on
a laptop; the degradation under a second; the cached pickles load in about a second.

Coordinates. Sportec tracking is in metres, origin at the pitch centre, y up (the raw XML shows
X in -52.5..52.5, Y in -34..34; PitchSize X="105.00" Y="68.00" for both matches). The harness
and prep/ code read Metrica-style frames: 0 to 1, origin top left, y down, multiplied back by
the pitch size in metres (`pitch`). Asking kloppy for `coordinates="metrica"` does exactly that
conversion (x' = (x + L/2) / L, y' = 1 - (y + W/2) / W) with the pitch size from the match
metadata (PitchX, PitchY), which `pitch` carries. The build asserts the result sits in
-0.2..1.2 (a ball a little outside the lines is normal; metres would fail).

Players. The metadata squads hold 20 players a side, but unused substitutes never appear in a
frame and kloppy's to_df has no column for them, so `teams` keeps only the tracked players (16+16
for J03WMX, 16+13 for J03WN1; counts in meta.json "squad_sizes" / "untracked_players"). Unlike
the real match, a column follows one player (NaN while off the pitch) in the clean frame; the
slot permutation below is what makes the degraded frame look like the real tracker's slots.

Truth. Per frame: D where ball_state is dead, else H / A from ball_owning_team_id (teams[0] is
home in kloppy's metadata), X nowhere inside a period (kloppy only yields frames inside periods).
Alive frames without an owning team take the previous frame's label (0 such frames in both
matches, counted in meta.json "alive_frames_without_owner"). Frame rows are the kloppy frames
in order; `frame_id` keeps Sportec's frame counter N. Sportec's BallStatus marks a lot of
play dead: 41.5% of frames in J03WMX and 51.7% in J03WN1 (`check` prints the dead-run count,
median and longest run), against roughly a third on Metrica Sample Game 3; the truth has 511
and 500 possessions with mean lengths 6.7 s and 5.5 s. Whether Sportec's dead flag is stricter
than LaLiga's grader is an open question for docs/notes.md, not something to tune on.

Results (15 Nov 2026, closest_row8 through harness.run, both matches concatenated, 1011 truth
possessions, runs cut at the period boundaries): degraded fixed 0.3355 (533 predicted),
degraded oracle 0.3995 (476), clean fixed 0.4262 (670), clean oracle 0.4891 (624). The practice
match gives 0.4444 noisy / 0.5025 clean for the same rule, so IDSSE is the harder set, mostly
through the dead mask: the fixed mask costs 0.06 here. The 2nd-half kickoff frame is already
alive (H) in Sportec's flags, which is why the runs must be cut at the period boundaries.

Degradation (seed 0, numpy default_rng). Two steps, in this order, on a copy of the clean frame:
  1. Ball dropouts. Contiguous blocks of exponential length (mean 2 s) are blanked until 41% of
     alive frames show no ball (the real match shows 59.3% on graded frames, DATA.md). Block
     starts are drawn with weight 3 on frames where 3 or more players stand within 3 m of the
     ball and weight 1 elsewhere, because the tracker loses the ball in crowds.
  2. Slot permutation. The match is cut into random intervals (exponential, mean 90 s) and in
     each interval the player columns of each team are permuted at random, so a column no longer
     follows one player across the match, like the slots of the real tracker.
Clean and degraded frames are both cached, per match, under data/idsse/<match_id>/.

Registered set. `load()` returns one object over the requested matches, concatenated with a row
offset so row indices stay contiguous: .df .gt_labels .gt_codes .runs .segments .teams .dead
{"fixed", "oracle"} .pitch, plus .matches and .offsets. Player id sets differ between matches, so
the concatenated frame has the union of columns (NaN where a player is not in that match) and
`teams` lists every id of either match per side; the prep/ distance and speed code treats NaN as
absent, so this is transparent. `load(clean=True)` is the undegraded version, `load_matches()`
the per-match objects if a single match is wanted. `pitch` is taken from the first match; the
build refuses to concatenate matches whose pitch sizes differ by more than 0.5 m.
harness.py registers it with `harness.register_set("idsse", idsse.load)` (and may register
`idsse.load_clean` as "idsse_clean"); until it does, score with
    import harness, idsse; harness.register_set("idsse", idsse.load); harness.run("closest_row8", sets=("idsse",), dead_mode="both")
"""

import functools
import json
import os
import sys
import time
import urllib.request

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
try:
    import _paths  # noqa: F401
except ImportError:  # same thing INTERFACES.md specifies for _paths.py
    for _sub in ("prep", "starter", "evaluation", os.path.join("experiments", "atallah")):
        _p = os.path.join(ROOT, _sub)
        if _p not in sys.path:
            sys.path.insert(0, _p)
import possession_metrics as pm  # noqa: E402
from sticky import period_segments  # noqa: E402
from stoppage import dead_from_players  # noqa: E402
from ball_out import dead_from_ball_out  # noqa: E402

IDSSE_DIR = os.path.join(ROOT, "data", "idsse")
RAW_DIR = os.path.join(IDSSE_DIR, "raw")
DEFAULT_MATCHES = ("J03WMX", "J03WN1")
# figshare file ids, copied from kloppy._providers.sportec.get_IDSSE_url (kloppy 3.18.0).
FILE_IDS = {
    "J03WPY": {"meta": 51643487, "event": 51643505, "tracking": 51643526},
    "J03WN1": {"meta": 51643472, "event": 51643496, "tracking": 51643517},
    "J03WMX": {"meta": 51643475, "event": 51643493, "tracking": 51643514},
    "J03WOH": {"meta": 51643478, "event": 51643499, "tracking": 51643520},
    "J03WQQ": {"meta": 51643484, "event": 51643508, "tracking": 51643529},
    "J03WOY": {"meta": 51643481, "event": 51643502, "tracking": 51643523},
    "J03WR9": {"meta": 51643490, "event": 51643511, "tracking": 51643532},
}
API_URL = "https://api.figshare.com/v2/file/download/{}"
LICENCE = "CC BY 4.0 (figshare, Springer Nature; Bassek et al. 2025, Sci Data 12, 195)"

FPS = 25
SEED = 0
# Degradation params. The 41% is the real match's missing-ball share; the rest is football sense.
MISSING_SHARE = 0.41       # share of alive frames with no ball after dropouts
GAP_MEAN_S = 2.0           # mean dropout length
CROWD_PLAYERS = 3          # a frame is "crowded" when this many players ...
CROWD_RADIUS_M = 3.0       # ... stand within this distance of the ball
CROWD_WEIGHT = 3.0         # dropout starts land on crowded frames this many times more often
PERM_MEAN_S = 90.0         # mean length of a slot-permutation interval


# -- download and parse ------------------------------------------------------------------------

def raw_paths(match_id):
    return {kind: os.path.join(RAW_DIR, "{}_{}.xml".format(match_id, kind))
            for kind in ("meta", "tracking")}


def fetch(match_id, force=False, retries=40, wait_s=30, log=print):
    """Download meta + tracking XML into data/idsse/raw/, retrying while figshare says 202."""
    if match_id not in FILE_IDS:
        raise ValueError("unknown IDSSE match {}; one of {}".format(match_id, sorted(FILE_IDS)))
    os.makedirs(RAW_DIR, exist_ok=True)
    paths = raw_paths(match_id)
    for kind, dest in paths.items():
        if not force and os.path.exists(dest) and os.path.getsize(dest) > 0:
            continue
        url = API_URL.format(FILE_IDS[match_id][kind])
        for attempt in range(1, retries + 1):
            t0 = time.time()
            with urllib.request.urlopen(url, timeout=900) as response:
                status = response.status
                data = response.read() if status == 200 else b""
            if status == 200 and data:
                with open(dest + ".part", "wb") as handle:
                    handle.write(data)
                os.replace(dest + ".part", dest)
                log("fetched {} {}: {:.1f} MB in {:.0f} s".format(
                    match_id, kind, len(data) / 1e6, time.time() - t0))
                break
            log("{} {}: HTTP {} (attempt {}), waiting {} s".format(match_id, kind, status, attempt, wait_s))
            time.sleep(wait_s)
        else:
            raise RuntimeError("could not download {} {} from {}".format(match_id, kind, url))
    return paths


def load_kloppy(match_id):
    """The kloppy TrackingDataset, all frames, in Metrica (0..1, top-left, y down) coordinates."""
    from kloppy import sportec

    paths = raw_paths(match_id)
    return sportec.load_tracking(meta_data=paths["meta"], raw_data=paths["tracking"],
                                 coordinates="metrica", only_alive=False)


def frame_table(ds):
    """(df, teams, pitch, home_id, names): the harness columns only, truth columns kept aside."""
    md = ds.metadata
    home, away = md.teams
    pitch = (float(md.pitch_dimensions.pitch_length), float(md.pitch_dimensions.pitch_width))
    full = ds.to_df()
    # Unused substitutes are in the metadata squad but never in a frame, so to_df has no
    # column for them; keep the tracked players only (the real match has 11 slots a side too).
    squads = [[p.player_id for p in team.players] for team in (home, away)]
    teams = [[pid for pid in squad if pid + "_x" in full.columns] for squad in squads]
    untracked = [len(squad) - len(ids) for squad, ids in zip(squads, teams)]
    keep = ["frame_id", "period_id", "ball_x", "ball_y"]
    for pid in sum(teams, []):
        keep += [pid + "_x", pid + "_y"]
    missing = [c for c in keep if c not in full.columns]
    if missing:
        raise KeyError("kloppy frame lacks columns {}".format(missing[:5]))
    df = full[keep].reset_index(drop=True)
    df["frame_id"] = df["frame_id"].astype(np.int64)
    df["period_id"] = df["period_id"].astype(np.int64)
    truth = full[["ball_state", "ball_owning_team_id"]].reset_index(drop=True)
    coords = df[[c for c in df.columns if c.endswith(("_x", "_y"))]].to_numpy()
    lo, hi = np.nanmin(coords), np.nanmax(coords)
    if lo < -0.2 or hi > 1.2:  # a ball a little outside the lines is normal; metres are not
        raise ValueError("coordinates not normalised: range {:.2f}..{:.2f}".format(lo, hi))
    names = {"home": home.name, "away": away.name, "home_id": home.team_id, "away_id": away.team_id,
             "coordinate_system": str(md.coordinate_system), "orientation": str(md.orientation),
             "squad_sizes": [len(s) for s in squads], "untracked_players": untracked}
    return df, truth, teams, pitch, names


def truth_labels(truth, home_id, away_id, periods):
    """'D' where the ball is dead, else 'H' / 'A' by owning team. Every kloppy frame is in a period.

    An alive frame with no owning team (should not happen in Sportec data) takes the previous
    frame's label inside its period, or 'D' at a period start. Returns (labels, n_such_frames).
    """
    state = truth["ball_state"].astype(str).str.lower().to_numpy()
    owner = truth["ball_owning_team_id"].astype(str).to_numpy()
    alive = state == "alive"
    labels = np.full(len(state), "D", dtype="<U1")
    labels[alive & (owner == str(home_id))] = "H"
    labels[alive & (owner == str(away_id))] = "A"
    unknown = alive & (owner != str(home_id)) & (owner != str(away_id))
    for i in np.flatnonzero(unknown):
        labels[i] = labels[i - 1] if i > 0 and periods[i - 1] == periods[i] else "D"
    return labels, int(unknown.sum())


# -- degradation -------------------------------------------------------------------------------

def crowded_frames(df, player_ids, pitch, n_players=CROWD_PLAYERS, radius_m=CROWD_RADIUS_M):
    """True where n_players or more are within radius_m of a visible ball."""
    bx = df["ball_x"].to_numpy()[:, None] * pitch[0]
    by = df["ball_y"].to_numpy()[:, None] * pitch[1]
    px = df[[i + "_x" for i in player_ids]].to_numpy() * pitch[0]
    py = df[[i + "_y" for i in player_ids]].to_numpy() * pitch[1]
    with np.errstate(invalid="ignore"):
        close = np.sqrt((px - bx) ** 2 + (py - by) ** 2) <= radius_m
    return np.sum(close, axis=1) >= n_players


def drop_ball(df, alive, crowded, rng, missing_share=MISSING_SHARE, gap_mean_s=GAP_MEAN_S,
              crowd_weight=CROWD_WEIGHT):
    """Blank the ball in contiguous blocks until `missing_share` of alive frames have none.

    Returns (frame, keep_mask, n_blocks). Blocks start on crowded frames `crowd_weight` times
    more often than elsewhere; lengths are exponential with mean gap_mean_s.
    """
    n = len(df)
    keep = ~np.isnan(df["ball_x"].to_numpy())
    weights = np.where(crowded, crowd_weight, 1.0)
    weights /= weights.sum()
    target = 1.0 - missing_share
    n_blocks = 0
    while keep[alive].mean() > target:
        for start in rng.choice(n, size=32, p=weights):  # batched draws: one choice() is O(n)
            if keep[alive].mean() <= target:
                break
            length = max(1, int(rng.exponential(gap_mean_s * FPS)))
            keep[start:start + length] = False
            n_blocks += 1
    out = df.copy()
    out.loc[~keep, ["ball_x", "ball_y"]] = np.nan
    return out, keep, n_blocks


def random_intervals(n, rng, mean_frames):
    """[(start, stop)] covering 0..n with exponential lengths (at least 1 frame)."""
    bounds, pos = [0], 0
    while pos < n:
        pos = min(n, pos + max(1, int(rng.exponential(mean_frames))))
        bounds.append(pos)
    return list(zip(bounds[:-1], bounds[1:]))


def permute_slots(df, teams, rng, mean_s=PERM_MEAN_S):
    """Within random intervals, shuffle which column carries which player, per team. In place."""
    intervals = random_intervals(len(df), rng, mean_s * FPS)
    for ids in teams:
        xcols, ycols = [i + "_x" for i in ids], [i + "_y" for i in ids]
        xs, ys = df[xcols].to_numpy(copy=True), df[ycols].to_numpy(copy=True)
        for start, stop in intervals:
            perm = rng.permutation(len(ids))
            xs[start:stop] = xs[start:stop][:, perm]
            ys[start:stop] = ys[start:stop][:, perm]
        df[xcols], df[ycols] = xs, ys
    return intervals


def degrade(df, labels, teams, pitch, seed=SEED):
    """Clean frame -> (degraded frame, info dict). Seeded; the same input gives the same output."""
    rng = np.random.default_rng(seed)
    alive = np.isin(labels, ["H", "A"])
    crowded = crowded_frames(df, sum(teams, []), pitch)
    visible_before = float((~np.isnan(df["ball_x"].to_numpy()))[alive].mean())
    out, keep, n_blocks = drop_ball(df, alive, crowded, rng)
    intervals = permute_slots(out, teams, rng)
    info = {"ball_visible_alive_before": visible_before,
            "ball_visible_alive_after": float(keep[alive].mean()),
            "crowded_share": float(crowded.mean()),
            "n_ball_blocks": int(n_blocks),
            "n_perm_intervals": len(intervals),
            "seed": seed}
    return out, info


# -- cache -------------------------------------------------------------------------------------

def match_dir(match_id):
    return os.path.join(IDSSE_DIR, match_id)


def cache_paths(match_id):
    d = match_dir(match_id)
    return {"clean": os.path.join(d, "clean.pkl"), "degraded": os.path.join(d, "degraded.pkl"),
            "labels": os.path.join(d, "labels.npy"), "meta": os.path.join(d, "meta.json")}


def is_built(match_id):
    return all(os.path.exists(p) for p in cache_paths(match_id).values())


def build_match(match_id, force=False, log=print):
    paths = cache_paths(match_id)
    if is_built(match_id) and not force:
        log("{}: cached".format(match_id))
        return
    fetch(match_id, log=log)
    t0 = time.time()
    ds = load_kloppy(match_id)
    df, truth, teams, pitch, names = frame_table(ds)
    log("{}: kloppy load + to_df {:.0f} s, {} frames".format(match_id, time.time() - t0, len(df)))
    labels, n_unknown = truth_labels(truth, names["home_id"], names["away_id"],
                                     df["period_id"].to_numpy())
    names["alive_frames_without_owner"] = n_unknown
    log("{}: {} tracked players per side (squads {}), {} alive frames without owner".format(
        match_id, [len(t) for t in teams], names["squad_sizes"], n_unknown))
    t0 = time.time()
    degraded, info = degrade(df, labels, teams, pitch)
    log("{}: degradation {:.1f} s, ball visible on alive frames {:.1%} -> {:.1%}, {} slot intervals".format(
        match_id, time.time() - t0, info["ball_visible_alive_before"],
        info["ball_visible_alive_after"], info["n_perm_intervals"]))
    os.makedirs(match_dir(match_id), exist_ok=True)
    df.to_pickle(paths["clean"])
    degraded.to_pickle(paths["degraded"])
    np.save(paths["labels"], labels)
    meta = dict(names, match_id=match_id, pitch=list(pitch), teams=teams,
                segments=period_segments(df), n_frames=len(df), fps=FPS, licence=LICENCE,
                raw_bytes={k: os.path.getsize(p) for k, p in raw_paths(match_id).items()},
                degradation=info)
    with open(paths["meta"], "w") as handle:
        json.dump(meta, handle, indent=1)


def build(match_ids=DEFAULT_MATCHES, force=False, log=print):
    for match_id in match_ids:
        build_match(match_id, force=force, log=log)


# -- the registered set -------------------------------------------------------------------------

def split_runs(runs, segments):
    """[(start, stop)] of each run cut at every segment boundary (empty pieces dropped)."""
    cuts = sorted({b for a, b in segments} | {a for a, b in segments})
    out = []
    for start, stop in runs:
        edges = [start] + [c for c in cuts if start < c < stop] + [stop]
        out += [(a, b) for a, b in zip(edges[:-1], edges[1:]) if b > a]
    return out


class IdsseSet:
    """What harness.register_set expects, plus the match list and row offsets."""

    def __init__(self, name, df, gt_labels, segments, teams, pitch, matches, offsets):
        self.name = name
        self.df = df
        self.gt_labels = gt_labels
        self.gt_codes = pm.label_codes(gt_labels)
        # kloppy yields no frame outside a period, so there is no X and valid_runs would be one
        # span over both halves of both matches. Cut it at the period boundaries so nothing
        # temporal (spells, abstention filling) crosses a half or a match, as on the real match.
        self.runs = split_runs(pm.valid_runs(self.gt_codes), segments)
        self.segments = segments
        self.teams = teams
        self.pitch = pitch
        self.matches = list(matches)
        self.offsets = list(offsets)
        fixed = dead_from_ball_out(df, segments, pitch=pitch) | \
            dead_from_players(df, sum(teams, []), segments, pitch=pitch)
        self.dead = {"fixed": fixed, "oracle": gt_labels == "D"}

    def __repr__(self):
        return "IdsseSet({}, matches={}, frames={})".format(self.name, self.matches, len(self.df))


def read_match(match_id, clean=False):
    paths = cache_paths(match_id)
    with open(paths["meta"]) as handle:
        meta = json.load(handle)
    df = pd.read_pickle(paths["clean" if clean else "degraded"])
    labels = np.load(paths["labels"]).astype("<U1")
    return df, labels, meta


def load_matches(match_ids=DEFAULT_MATCHES, clean=False):
    """One IdsseSet per match."""
    build(match_ids, log=lambda *a: None)
    out = []
    for match_id in match_ids:
        df, labels, meta = read_match(match_id, clean)
        out.append(IdsseSet("idsse:" + match_id + (":clean" if clean else ""), df, labels,
                            [tuple(s) for s in meta["segments"]], meta["teams"],
                            tuple(meta["pitch"]), [match_id], [0]))
    return out


def load(clean=False, match_ids=DEFAULT_MATCHES):
    """All matches as one set, rows concatenated so row indices stay contiguous."""
    build(match_ids, log=lambda *a: None)
    frames, labels, segments, offsets = [], [], [], []
    teams = [[], []]
    pitch = None
    offset = 0
    for match_id in match_ids:
        df, lab, meta = read_match(match_id, clean)
        if pitch is None:
            pitch = tuple(meta["pitch"])
        elif max(abs(a - b) for a, b in zip(pitch, meta["pitch"])) > 0.5:
            raise ValueError("pitch sizes differ: {} vs {} ({})".format(pitch, meta["pitch"], match_id))
        for side in (0, 1):
            clash = set(teams[side]) & set(meta["teams"][side])
            if clash or set(meta["teams"][side]) & set(teams[1 - side]):
                raise ValueError("player ids shared between matches; concatenation is ambiguous")
            teams[side] += meta["teams"][side]
        segments += [(a + offset, b + offset) for a, b in meta["segments"]]
        offsets.append(offset)
        frames.append(df)
        labels.append(lab)
        offset += len(df)
    df = pd.concat(frames, ignore_index=True, sort=False)
    gt = np.concatenate(labels).astype("<U1")
    return IdsseSet("idsse" + (":clean" if clean else ""), df, gt, segments, teams, pitch,
                    match_ids, offsets)


load_clean = functools.partial(load, clean=True)


# -- self test ---------------------------------------------------------------------------------

def check(match_ids=DEFAULT_MATCHES):
    """Aggregates per match, nothing per frame."""
    build(match_ids)
    total_frames, total_spells = 0, 0
    for match_id in match_ids:
        df, labels, meta = read_match(match_id)
        codes = pm.label_codes(labels)
        runs = pm.valid_runs(codes)
        stats = pm.possession_stats(codes, runs)
        deg = meta["degradation"]
        alive = np.isin(labels, ["H", "A"])
        print("{} {} vs {}".format(match_id, meta["home"], meta["away"]))
        print("  frames {}  periods {}  pitch {:.1f} x {:.1f} m  players {}+{}".format(
            len(df), len(meta["segments"]), meta["pitch"][0], meta["pitch"][1],
            len(meta["teams"][0]), len(meta["teams"][1])))
        dead_runs = [(a, b) for a, b, code in pm.segments(codes, runs) if code == pm.D]
        print("  alive share {:.1%}  dead share {:.1%}  home share of alive {:.1%}".format(
            alive.mean(), (labels == "D").mean(), stats["home_share"]))
        if dead_runs:
            lengths = np.array([b - a for a, b in dead_runs]) / FPS
            print("  dead runs {}  median {:.1f} s  longest {:.0f} s".format(
                len(dead_runs), np.median(lengths), lengths.max()))
        print("  truth possessions {}  mean length {:.2f} s".format(
            stats["n_spells"], stats["mean_duration_s"]))
        print("  ball visible on alive frames {:.1%} -> {:.1%} ({} dropout blocks, {:.1%} of frames crowded)".format(
            deg["ball_visible_alive_before"], deg["ball_visible_alive_after"],
            deg["n_ball_blocks"], deg["crowded_share"]))
        print("  slot permutation intervals {}".format(deg["n_perm_intervals"]))
        total_frames += len(df)
        total_spells += stats["n_spells"]
    print("total frames {}  total truth possessions {}  licence: {}".format(
        total_frames, total_spells, LICENCE))


def main(argv):
    force = "--force" in argv
    words = [a for a in argv[1:] if not a.startswith("--")]
    cmd = words[0] if words else "check"
    ids = tuple(words[1:]) or DEFAULT_MATCHES
    if cmd == "build":
        build(ids, force=force)
    elif cmd == "check":
        check(ids)
    else:
        raise SystemExit("usage: idsse.py build|check [match_id ...] [--force]")


if __name__ == "__main__":
    main(sys.argv)
