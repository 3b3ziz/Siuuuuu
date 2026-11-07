"""Replay a few seconds of the tracking on a stadium canvas, in one local HTML file.

Reads a short window of the provided ATD on your machine and writes a self-contained HTML page.
Open it in a browser. Nothing is uploaded and the page makes no network calls.

The window is small on purpose (default 10 s, 250 frames, starting at the first graded frame), so
the page stays light. What you can see:
  * both teams as blue (home) and red (away) dots, the ball in white
  * when the ball is not tracked, a hollow ring marks where it was last seen
  * short trails behind the players and the ball
  * optionally a H/A/D banner per frame from any frame,label CSV (a submission or the public GT)

Terms: the output contains tracking data from the gated bundle. It goes to data/views/, which
git ignores. Do not commit it, share it or upload it anywhere.

    pip install -r requirements-starter.txt     # needs kloppy
    uv run --with numpy --with pandas --with kloppy python experiments/atallah/pitch_view.py
    uv run --with numpy --with pandas --with kloppy python experiments/atallah/pitch_view.py \\
        --start 12000 --seconds 8 --labels evaluation/gt/BAR-ATH_possession_gt_public.csv
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))   # experiments/atallah -> repo root
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "starter"))

# Params
FPS = 25
DEFAULT_START = 11185     # first graded frame, which is also where the public ground truth begins
DEFAULT_SECONDS = 10
DEFAULT_OUT = os.path.join(ROOT, "data", "views", "pitch_view.html")
SIDES = {"home": 0, "away": 1}   # anything else is drawn grey
LABELS = {"H": 0, "A": 1, "D": 2, "X": 3}


def load_window(start, n_frames, source="tactical"):
    """(DataFrame, {object id: 0/1/2}) for video frames [start, start + n_frames).

    kloppy is asked for only the first start + n_frames records, because it reads the file from
    the top. That is a small slice of the 199,319-frame file, so it stays quick.
    """
    from kloppy import metrica
    from load_atd import atd_paths

    meta, raw = atd_paths(source=source)
    last_id = start + n_frames + 1
    try:
        dataset = metrica.load_tracking_epts(meta_data=meta, raw_data=raw, limit=last_id)
    except TypeError:
        dataset = metrica.load_tracking_epts(meta_data=meta, raw_data=raw)

    try:
        frame = dataset.to_df(engine="pandas")
    except TypeError:
        frame = dataset.to_df()

    side_of = {}
    for team in dataset.metadata.teams:
        ground = getattr(getattr(team, "ground", None), "value", "")
        for player in team.players:
            side_of[str(player.player_id)] = SIDES.get(str(ground).lower(), 2)

    ids = frame["frame_id"].astype(int)
    window = frame[(ids >= start + 1) & (ids <= start + n_frames)]
    if window.empty:
        sys.exit("no tracking records for video frames {}..{} (the file has ids {}..{})".format(
            start, start + n_frames - 1, int(ids.min()), int(ids.max())))
    return window.reset_index(drop=True), side_of


def build_payload(window, side_of, start, labels=None):
    """JSON-ready dict: per frame the ball and every tracked object that has a position."""
    import numpy as np

    slots = []
    for column in window.columns:
        if column.endswith("_x") and column != "ball_x":
            slots.append(column[:-2])

    def side(slot):
        if slot in side_of:
            return side_of[slot]
        lowered = slot.lower()
        for name, code in SIDES.items():
            if lowered.startswith(name):
                return code
        return 2

    sides = [side(s) for s in slots]
    xs = window[[s + "_x" for s in slots]].to_numpy(dtype=float)
    ys = window[[s + "_y" for s in slots]].to_numpy(dtype=float)
    bx = window["ball_x"].to_numpy(dtype=float) if "ball_x" in window else None
    by = window["ball_y"].to_numpy(dtype=float) if "ball_y" in window else None
    frame_ids = window["frame_id"].astype(int).to_numpy()

    frames = []
    for i in range(len(window)):
        objects = []
        for j in range(len(slots)):
            if not (np.isnan(xs[i, j]) or np.isnan(ys[i, j])):
                objects.append([j, round(float(xs[i, j]), 4), round(float(ys[i, j]), 4)])
        ball = None
        if bx is not None and not (np.isnan(bx[i]) or np.isnan(by[i])):
            ball = [round(float(bx[i]), 4), round(float(by[i]), 4)]
        frames.append({"f": int(frame_ids[i]) - 1, "b": ball, "p": objects})

    label_codes = None
    if labels is not None:
        label_codes = [LABELS.get(str(labels.get(fr["f"], "X")).strip().upper(), 3) for fr in frames]

    return {"fps": FPS, "start": start, "sides": sides, "frames": frames, "labels": label_codes}


def read_labels(path, start, n_frames):
    """{video frame: label} for the window only, from a frame,label CSV."""
    import pandas as pd
    table = pd.read_csv(path, dtype={"label": "object"})
    table.columns = [str(c).strip().lower() for c in table.columns]
    table = table[(table["frame"] >= start) & (table["frame"] < start + n_frames)]
    return dict(zip(table["frame"].astype(int), table["label"]))


def render(payload):
    with open(os.path.join(HERE, "pitch_view_template.html"), encoding="utf-8") as handle:
        page = handle.read()
    return page.replace("__DATA__", json.dumps(payload, separators=(",", ":")).replace("</", "<\\/"))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", type=int, default=DEFAULT_START, help="first video frame")
    parser.add_argument("--seconds", type=float, default=DEFAULT_SECONDS, help="window length")
    parser.add_argument("--labels", default=None, help="optional frame,label CSV for the banner")
    parser.add_argument("--source", default="tactical", choices=["tactical", "broadcast"])
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args()

    n_frames = max(25, int(round(args.seconds * FPS)))
    if n_frames > 3000:
        sys.exit("keep the window small: at most 120 s (3000 frames)")

    window, side_of = load_window(args.start, n_frames, args.source)
    labels = read_labels(args.labels, args.start, n_frames) if args.labels else None
    payload = build_payload(window, side_of, args.start, labels)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(render(payload))
    counts = [payload["sides"].count(k) for k in (0, 1, 2)]
    print("wrote {} ({} frames from {}; track slots home/away/unassigned: {}/{}/{})".format(
        args.out, len(payload["frames"]), args.start, *counts))


if __name__ == "__main__":
    main()
