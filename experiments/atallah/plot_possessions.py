"""Draw your submission next to the ground truth as timeline strips, in one local HTML file.

Everything runs on your machine and the output is a single self-contained HTML page with no
network calls. Open it in a browser. Nothing is uploaded and no other tool needs to see the data.

For the frames where the ground truth is graded (not X), the page shows:
  truth       the ground-truth label for every frame (H blue, A red, D grey)
  your file   your raw labels
  scored as   your labels after X is forward-filled, which is what spellF1 sees
  matches     your possessions, drawn solid if they were matched to a real possession at the
              chosen IoU pass mark and drawn hollow if they are invented

Usage:
    python experiments/atallah/plot_possessions.py my_submission.csv              # public 5 minutes
    python experiments/atallah/plot_possessions.py my_submission.csv --gt path/to/gt.csv --out view.html

The default output is data/views/possession_view.html, which git ignores.
"""

import argparse
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))   # experiments/atallah -> repo root
sys.path.insert(0, os.path.join(ROOT, "evaluation"))
import possession_metrics as pm  # noqa: E402  (organisers' scorer, untouched)

GT_DIR = os.path.join(ROOT, "evaluation", "gt")
GT_PATTERNS = {"public": "*_possession_gt_public.csv", "private": "*_possession_gt.csv"}
DEFAULT_OUT = os.path.join(ROOT, "data", "views", "possession_view.html")


def find_gt(name):
    """Resolve 'public', 'private' or a path to one ground-truth CSV."""
    if name in GT_PATTERNS:
        hits = sorted(glob.glob(os.path.join(GT_DIR, GT_PATTERNS[name])))
        if not hits:
            sys.exit("no {} ground truth found in {}".format(name, GT_DIR))
        return hits[0]
    if not os.path.isfile(name):
        sys.exit("ground truth not found: {}".format(name))
    return name


def greedy_pairs(overlaps, threshold):
    """[(gt_index, pred_index)] one-to-one pairs at this IoU, same greedy rule as the scorer."""
    used_gt, used_pred, pairs = set(), set(), []
    for iou, gi, pi in overlaps:
        if iou < threshold:
            break
        if gi in used_gt or pi in used_pred:
            continue
        used_gt.add(gi)
        used_pred.add(pi)
        pairs.append((gi, pi))
    return pairs


def build_payload(gt_codes, pred_codes):
    runs = pm.valid_runs(gt_codes)
    if not runs:
        sys.exit("the ground truth has no graded frames (all X)")
    filled = pm.fill_abstentions(pred_codes, runs)
    gt_spells = pm.possession_spells(gt_codes, runs)
    pred_spells = pm.possession_spells(filled, runs)
    overlaps = pm.spell_overlaps(gt_spells, pred_spells)

    matched = {}
    for threshold in pm.SPELL_IOUS:
        matched[str(threshold)] = sorted(pi for _, pi in greedy_pairs(overlaps, threshold))

    scores = pm.spell_scores(gt_codes, filled, runs)
    table = [{"iou": t, "matched": v["n_matched"], "invented": v["n_spurious"],
              "missed": v["n_missed"], "f1": v["f1"]} for t, v in scores["per_iou"].items()]

    return {
        "n": int(len(gt_codes)),
        "fps": pm.FPS,
        "runs": [[int(a), int(b)] for a, b in runs],
        "gt": [[a, b, k] for a, b, k in pm.segments(gt_codes, runs)],
        "pred": [[a, b, k] for a, b, k in pm.segments(pred_codes, runs)],
        "filled": [[a, b, k] for a, b, k in pm.segments(filled, runs)],
        "pred_spells": [[a, b, k] for a, b, k in pred_spells],
        "gt_spells": [[a, b, k] for a, b, k in gt_spells],
        "matched": matched,
        "table": table,
        "spell_f1": scores["mean_f1"],
        "n_gt": scores["n_gt"],
        "n_pred": scores["n_pred"],
    }


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Possession view</title>
<style>
:root { --bg:#f1f3ee; --surface:#fafbf8; --ink:#16201a; --muted:#566259; --line:#d3d9d0;
  --home:#1c4fb5; --away:#c8202f; --dead:#8e968f; --accent:#0b6e45; color-scheme: light; }
@media (prefers-color-scheme: dark) { :root { --bg:#0d1310; --surface:#141c17; --ink:#e4eae2;
  --muted:#9aa79d; --line:#27322b; --home:#7aa2ff; --away:#ff6874; --dead:#6d776f;
  --accent:#45d394; color-scheme: dark; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui,sans-serif; }
main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 60px; display: grid; gap: 16px; }
h1 { margin:0; font-size: 26px; }
.muted { color: var(--muted); }
.panel { background: var(--surface); border:1px solid var(--line); border-radius:8px; padding:14px; display:grid; gap:12px; }
.row { display:flex; flex-wrap:wrap; gap:16px; align-items:center; font-size: 13px; }
.big { font-size: 34px; font-weight: 700; color: var(--accent); font-variant-numeric: tabular-nums; }
canvas { width:100%; display:block; background: var(--bg); border-radius:4px; }
table { border-collapse: collapse; width:100%; font-size: 13px; }
th, td { text-align:right; padding:6px 10px; border-bottom:1px solid var(--line); font-variant-numeric: tabular-nums; }
th:first-child, td:first-child { text-align:left; }
.sw { display:inline-block; width:12px; height:12px; border-radius:2px; vertical-align:-1px; margin-right:5px; }
label { display:flex; gap:8px; align-items:center; }
input[type=range] { width: 220px; accent-color: var(--accent); }
</style></head><body><main>
<h1>Possession view</h1>
<p class="muted">Your submission against the ground truth, drawn on this machine only. Blue is H, red is A, grey is D.
A hollow outline on the bottom strip is a possession of yours that has no real partner at the chosen IoU pass mark.</p>
<div class="panel">
  <div class="row"><div><div class="muted">spellF1</div><div class="big" id="spell"></div></div>
    <div class="muted" id="counts"></div></div>
  <table id="tbl"><thead><tr><th>IoU pass mark</th><th>matched</th><th>invented</th><th>missed</th><th>F1</th></tr></thead><tbody></tbody></table>
</div>
<div class="panel">
  <div class="row">
    <label>IoU pass mark <input id="thr" type="range" min="0" max="4" step="1" value="2"><b id="thr-out"></b></label>
    <label>Zoom <input id="zoom" type="range" min="0" max="100" step="1" value="0"><b id="zoom-out"></b></label>
    <label>Start <input id="pos" type="range" min="0" max="1000" step="1" value="0"></label>
  </div>
  <div class="row"><span><i class="sw" style="background:var(--home)"></i>H</span><span><i class="sw" style="background:var(--away)"></i>A</span>
    <span><i class="sw" style="background:var(--dead)"></i>D</span><span class="muted">gaps are frames the ground truth does not grade</span></div>
  <canvas id="cv" height="250"></canvas>
</div>
<script>
var DATA = __DATA__;
(function () {
  var css = getComputedStyle(document.documentElement);
  function col(name) { return css.getPropertyValue(name).trim(); }
  var cv = document.getElementById("cv"), ctx = cv.getContext("2d");
  var thr = document.getElementById("thr"), zoom = document.getElementById("zoom"), pos = document.getElementById("pos");
  var MARKS = Object.keys(DATA.matched);
  var first = DATA.runs[0][0], last = DATA.runs[DATA.runs.length - 1][1], span = last - first;
  document.getElementById("spell").textContent = DATA.spell_f1.toFixed(4);
  document.getElementById("counts").textContent = DATA.n_pred + " possessions in your file, " + DATA.n_gt + " in the ground truth";
  var tb = document.querySelector("#tbl tbody");
  DATA.table.forEach(function (r) {
    var tr = document.createElement("tr");
    [r.iou.toFixed(1), r.matched, r.invented, r.missed, r.f1.toFixed(3)].forEach(function (v) {
      var td = document.createElement("td"); td.textContent = v; tr.appendChild(td);
    });
    tb.appendChild(tr);
  });
  function colour(k) { return k === 0 ? col("--home") : k === 1 ? col("--away") : col("--dead"); }
  function draw() {
    var dpr = window.devicePixelRatio || 1, W = cv.clientWidth, Hh = 250;
    cv.width = W * dpr; cv.height = Hh * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = col("--bg"); ctx.fillRect(0, 0, W, Hh);
    var z = +zoom.value / 100, win = Math.max(250, Math.round(span * Math.pow(1 - z, 2)));
    var maxStart = Math.max(0, span - win), start = first + Math.round(maxStart * (+pos.value / 1000)), end = start + win;
    document.getElementById("zoom-out").textContent = (win / DATA.fps).toFixed(0) + " s on screen";
    document.getElementById("thr-out").textContent = MARKS[+thr.value];
    var L = 90, R = W - 8;
    function x(f) { return L + (f - start) / win * (R - L); }
    function strip(segs, y, h, outline) {
      segs.forEach(function (s) {
        if (s[1] <= start || s[0] >= end) return;
        var x0 = x(Math.max(s[0], start)), x1 = x(Math.min(s[1], end));
        ctx.fillStyle = colour(s[2]); ctx.fillRect(x0, y, Math.max(x1 - x0, 0.6), h);
      });
    }
    var rows = [["truth", DATA.gt, 18], ["your file", DATA.pred, 70], ["scored as", DATA.filled, 122]];
    ctx.font = "12px system-ui"; ctx.textBaseline = "middle";
    rows.forEach(function (r) {
      ctx.fillStyle = col("--muted"); ctx.fillText(r[0], 0, r[2] + 15);
      strip(r[1], r[2], 30);
    });
    ctx.fillStyle = col("--muted"); ctx.fillText("matches", 0, 190 + 15);
    var ok = {}; DATA.matched[MARKS[+thr.value]].forEach(function (i) { ok[i] = 1; });
    DATA.pred_spells.forEach(function (s, i) {
      if (s[1] <= start || s[0] >= end) return;
      var x0 = x(Math.max(s[0], start)), x1 = Math.max(x(Math.min(s[1], end)), x0 + 1);
      if (ok[i]) { ctx.fillStyle = colour(s[2]); ctx.fillRect(x0, 190, x1 - x0, 30); }
      else { ctx.strokeStyle = colour(s[2]); ctx.lineWidth = 2; ctx.strokeRect(x0 + 1, 191, Math.max(x1 - x0 - 2, 1), 28); }
    });
    ctx.fillStyle = col("--muted"); ctx.textBaseline = "alphabetic";
    var step = win > 6000 ? 1500 : win > 1500 ? 250 : 50;
    for (var f = Math.ceil(start / step) * step; f <= end; f += step) {
      var xx = x(f); ctx.fillRect(xx, 228, 1, 5);
      var t = Math.round(f / DATA.fps), label = Math.floor(t / 60) + ":" + String(t % 60).padStart(2, "0");
      ctx.fillText(label, xx - 12, 246);
    }
  }
  [thr, zoom, pos].forEach(function (el) { el.addEventListener("input", draw); });
  window.addEventListener("resize", draw);
  draw();
})();
</script></main></body></html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("submission", help="frame,label CSV to draw")
    parser.add_argument("--gt", default="public", metavar="PUBLIC|PRIVATE|PATH",
                        help="ground truth to compare with (default: public, the 5 public minutes)")
    parser.add_argument("--out", default=DEFAULT_OUT, help="HTML file to write")
    args = parser.parse_args()

    gt_frame = pm.read_label_csv(find_gt(args.gt))
    gt_codes = pm.label_codes(gt_frame)

    pred_frame = pm.read_label_csv(args.submission)
    reason = pm.validate_submission(pred_frame, len(gt_codes))
    if reason:
        sys.exit("submission is not valid: " + reason)
    pred_codes = pm.label_codes(pred_frame)

    payload = build_payload(gt_codes, pred_codes)
    html = PAGE.replace("__DATA__", json.dumps(payload).replace("</", "<\\/"))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(html)
    print("wrote {} (spellF1 {:.4f})".format(args.out, payload["spell_f1"]))


if __name__ == "__main__":
    main()
