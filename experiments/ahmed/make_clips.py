"""Short video clips of our predicted stoppages, with our label drawn on screen, for watching.

    python experiments/ahmed/make_clips.py            # writes data/clips/*.mp4 and data/clips/index.csv

Watching only: what we see becomes rules in code, never labels (RULES.md).
Picks (fixed seed, so the same clips every run):
  - the shortest stoppages we predict (likely false alarms)
  - stoppages found only by the "players slowed down" rule (fouls, or false alarms?)
  - stoppages found by the "ball left the pitch" rule (check when they start and end)
Each clip runs from 4 s before our stoppage to 4 s after it (capped at 40 s).
Needs data/cache/ from prep (tactical_df.pkl etc.), see notes.
"""

import csv
import os
import pickle
import sys

import cv2
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [ROOT]
from games import GAME, half_video_blocks  # noqa: E402

VIDEO = os.path.join(ROOT, "data", "tactical", "BAR-ATH_tactical.mp4")
OUT = os.path.join(ROOT, "data", "clips")
PUBLIC = (11185, 18685)  # the 5 public minutes, skipped so we never look at them against our guesses
PAD = 100  # frames (4 s)
MAX_LEN = 1000  # frames (40 s)
SIZE = (960, 540)
COLOURS = {"H": (219, 112, 30), "A": (40, 40, 220), "D": (120, 120, 120), "X": (0, 0, 0)}  # BGR
NAMES = {"H": "HOME has it", "A": "AWAY has it", "D": "STOPPED", "X": "no answer"}


def pick(stops, src, seed=0):
    rng = np.random.default_rng(seed)
    ok = [i for i, (s, e) in enumerate(stops) if e < PUBLIC[0] or s > PUBLIC[1]]
    dur = {i: stops[i][1] - stops[i][0] for i in ok}
    shortest = sorted(ok, key=lambda i: dur[i])[:7]
    rest = [i for i in ok if i not in shortest]
    speed = [i for i in rest if src[i] == "speed"]
    ballout = [i for i in rest if src[i] != "speed"]
    chosen = [("short", i) for i in shortest]
    chosen += [("slowdown", i) for i in sorted(rng.choice(speed, 8, replace=False))]
    chosen += [("ballout", i) for i in sorted(rng.choice(ballout, 5, replace=False))]
    return chosen


def clock(frame):
    for half, first, last in half_video_blocks(GAME):
        if first <= frame <= last:
            t = (frame - first) / 25
            return "half {}  {:02d}:{:02d}".format(half, int(t // 60), int(t % 60))
    return "outside play"


def draw(img, labels, a, b, f):
    lab = labels[f]
    cv2.rectangle(img, (0, 0), (SIZE[0], 44), COLOURS[lab], -1)
    cv2.putText(img, "OUR GUESS: " + NAMES[lab], (12, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(img, "{}   frame {}".format(clock(f), f), (560, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (255, 255, 255), 1)
    # strip of our labels across the whole clip, with a cursor
    y0, h = SIZE[1] - 22, 22
    n = b - a
    for x in range(SIZE[0]):
        cv2.line(img, (x, y0), (x, y0 + h), COLOURS[labels[a + x * n // SIZE[0]]], 1)
    cx = (f - a) * SIZE[0] // n
    cv2.line(img, (cx, y0 - 6), (cx, y0 + h), (255, 255, 255), 3)


def main():
    labels = pd.read_csv(os.path.join(ROOT, "evaluation", "results", "ours_row8.csv")).label.values
    stops, src = pickle.load(open(os.path.join(ROOT, "data", "cache", "our_stops.pkl"), "rb"))
    os.makedirs(OUT, exist_ok=True)
    cap = cv2.VideoCapture(VIDEO)
    rows = []
    for n, (kind, i) in enumerate(pick(stops, src), 1):
        s, e = (int(v) for v in stops[i])
        a, b = s - PAD, min(e + PAD, s - PAD + MAX_LEN)
        name = "{:02d}_{}_{}.mp4".format(n, kind, s)
        out = cv2.VideoWriter(os.path.join(OUT, name), cv2.VideoWriter_fourcc(*"avc1"), 25, SIZE)
        cap.set(cv2.CAP_PROP_POS_FRAMES, a)
        for f in range(a, b):
            ok, img = cap.read()
            if not ok:
                break
            img = cv2.resize(img, SIZE)
            draw(img, labels, a, b, f)
            out.write(img)
        out.release()
        rows.append({"clip": name, "kind": kind, "stop_start": s, "stop_end": e,
                     "stop_seconds": round((e - s) / 25, 1), "found_by": src[i], "when": clock(s)})
        print(name, rows[-1]["stop_seconds"], "s", src[i])
    with open(os.path.join(OUT, "index.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
