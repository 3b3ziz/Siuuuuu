# Smoothing window

An Anatomy figure (isometric SVG, no WebGL) that shows what majority-vote smoothing does to per-frame labels and
why spellF1 rises and then falls as the window grows (steps 5 and 6 of the MTAH brief). Companion to
`../iou-bench/`: same bench, console, lane parts, card size, camera and Lucius palette. Not committed; the
`figures/` folder is scratch work.

## What it shows

* Three lanes of tiles. Back: the truth (four turns, one of them a genuine 2 s away turn). Middle: the tracker's
  jittery per-frame labels, the truth plus seven short wrong bursts. Front: the output after smoothing.
* A carriage on a beam over the middle lane. Its hood spans exactly ±w frames around the carriage (0.28 units per
  frame), clipped at the strip ends the way the baseline clips its window. A dial on the carriage leans to whichever
  team fills more of the hood, with a lamp for each team, and the stamp arm prints that label on the output lane as
  the carriage sweeps left to right. Ties go to home, as in `starter/baseline.py`.
* The knob at the front has six detents: 0, ±5, ±12, ±25, ±50, ±125 frames. The dials at the back read how many
  turns came out and spellF1. After a sweep, pegs mark the pairing: lime has a partner, red is invented or missed.
* The synthetic strip gives spellF1 0.13, 0.18, 0.80, 1.00, 0.80, 0.53 at the six stops, while frames right stay
  between 90% and 100%. The caption quotes the real baseline (0.05, 0.20, 0.24, 0.22 at 0, ±25, ±50, ±125) as the
  real match, clearly labelled.

Controls: click the knob for the next stop, Left/Right or Up/Down arrows step, Home/End jump, Space steps, Enter
replays. It tours the six stops on its own and stops when off screen. Reduced motion gets the finished still at ±25.

## Files

* `model.mjs`: pure model. The strip, the majority vote of `starter/baseline.py`, and the spellF1 rules of
  `evaluation/possession_metrics.py` (maximal H/A runs, greedy one-to-one by IoU, F1 = 2tp / (real + yours) per
  pass mark, averaged). Every number on the figure and in the caption comes from here; the caption is built from it.
* `geometry.mjs`: all drawing, against an injected kit so it runs in Node and inline in the page.
* `scene.mjs`: the state machine (timeline, easing, painting). The Node build uses it to paint the first frame.
* `build.mjs`: assembles everything and writes the outputs.
* `smoothing-window.html`, `smoothing-window-light.html`: standalone pages (dark and light).
* `fragment.html`: the figure card only (markup, scoped CSS, inline module script). Paste it into another page.
  Every rule is under `.smwin`; the theme follows the host: `html[data-theme="dark"|"light"]`, else
  `prefers-color-scheme`. No external requests. A host rule with `!important` on `svg path` can still override
  stroke colours.
* `shots/`: verification screenshots, the drive steps and the host-page test. Not committed (8 MB of PNGs); the commands below recreate them.

## Rebuild

```
node build.mjs          # Node 20.10+; reads the kit from ../../.agents/skills/anatomy
```

Checks used (Chrome needed):

```
A=../../.agents/skills/anatomy/scripts
node $A/lines.mjs smoothing-window.html --out shots/lines-dark.png     # must print: line ends: 0
node $A/lines.mjs smoothing-window-light.html --out shots/lines-light.png
node $A/drive.mjs smoothing-window.html --actions shots/steps-dark.json  # lines in five poses
node $A/capture.mjs smoothing-window.html --out shots/dark-phone.png --width 390
```
