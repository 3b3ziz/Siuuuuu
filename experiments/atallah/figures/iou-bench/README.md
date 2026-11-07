# IoU bench

An Anatomy figure (isometric SVG, no WebGL) that shows how spellF1 pairs your possessions with the real ones
(steps 4 and 5 of the MTAH brief). Not committed; the `figures/` folder is scratch work.

## What it shows

* Two lanes of blocks on a bench: the real turns (back, from the 30 s worked example: H 10 s, A 6 s, D 3 s, H 11 s)
  and the turns in your file (front). Blue is home, red is away. The dead ball is a low grey spacer: a gap, never a turn.
* A caliper beam over the lanes. For each pair, best overlap first, the lit jaws close on the overlap and the outer jaws
  on the union. The IoU dial (back left) reads overlap over union. One real turn and one of yours per pair: the "taken"
  pegs flip lime on both blocks, and turns of yours left over get a red peg (invented).
* Five columns at the front are the pass marks 0.3 to 0.7. A lamp lights when the needle clears the mark, and the
  column's cap rises by 2 / (real + yours). The right dial (back right) reads the average of the five: spellF1.
* The switch (front left) moves the 2 wrong seconds from the middle of a turn (spellF1 0.60, 5 turns for 3)
  to the edge between two turns (spellF1 1.00, 3 for 3). Both are 93% of frames correct.

Controls: click the switch, or Left/Right arrows (Space toggles, Enter replays). It tours both cases on its own and
stops when off screen. Reduced motion gets the finished still.

## Files

* `model.mjs`: pure model of the scoring rules (same as `evaluation/possession_metrics.py`): same-team pairs,
  greedy one-to-one by IoU, F1 = 2tp / (real + yours) per pass mark, averaged. Every number on the figure comes from here.
* `geometry.mjs`: all drawing, written against an injected kit so it runs in Node and inline in the page.
* `scene.mjs`: the state machine (timeline, easing, painting). The Node build uses it to paint the first frame.
* `build.mjs`: assembles everything and writes the outputs.
* `iou-bench.html`, `iou-bench-light.html`: standalone pages (dark and light, Lucius palette from `~/neo-lucius`).
* `fragment.html`: the figure card only (markup, scoped CSS, inline script). Paste it into another page. Every
  rule is under `.iobench`; the theme follows the host: `html[data-theme="dark"|"light"]`, else `prefers-color-scheme`.
  No external requests. A host rule with `!important` on `svg path` can still override stroke colours.
* `shots/`: verification screenshots and test pages.

## Rebuild

```
node build.mjs          # Node 20.10+; reads the kit from ../../.agents/skills/anatomy
```

Checks used (Chrome needed):

```
A=../../.agents/skills/anatomy/scripts
node $A/capture.mjs iou-bench.html --out shots/dark.png --width 390
node $A/lines.mjs iou-bench.html --out shots/lines.png        # must print: line ends: 0
node $A/drive.mjs iou-bench.html --actions shots/steps3.json  # lines in several poses
```
