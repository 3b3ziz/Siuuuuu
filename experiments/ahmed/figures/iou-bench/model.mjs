/* The model behind the IoU bench: the 30 s worked example from the brief, and the spellF1 rules
   from evaluation/possession_metrics.py (same-team pairs, greedy one-to-one by IoU, F1 = 2tp/(nG+nP)
   at each pass mark, averaged). Pure: no DOM, no kit. Everything the figure shows comes from here. */

export const SECONDS = 30;
export const MARKS = [0.3, 0.4, 0.5, 0.6, 0.7];

/* ground truth: H 10 s, A 6 s, a 3 s dead ball, H 11 s */
export const TRUTH = [
  { id: 0, s: 0, e: 10, team: "H" },
  { id: 1, s: 10, e: 16, team: "A" },
  { id: 2, s: 16, e: 19, team: "D" },
  { id: 3, s: 19, e: 30, team: "H" },
];

/* "your file" is six slots on the bench. In "middle" the 2 wrong seconds sit inside the last turn.
   In "edge" they sit at the boundary of the first two turns, and the last three slots collapse. */
export const FILES = {
  middle: [
    { s: 0, e: 10, team: "H" },
    { s: 10, e: 16, team: "A" },
    { s: 16, e: 19, team: "D" },
    { s: 19, e: 23, team: "H" },
    { s: 23, e: 25, team: "A" },
    { s: 25, e: 30, team: "H" },
  ],
  edge: [
    { s: 0, e: 8, team: "H" },
    { s: 8, e: 16, team: "A" },
    { s: 16, e: 19, team: "D" },
    { s: 19, e: 19, team: "H" },
    { s: 19, e: 19, team: "A" },
    { s: 19, e: 30, team: "H" },
  ],
};
export const MODES = ["middle", "edge"];

/* possessions: maximal runs of H or A. D is never a turn and always cuts one turn from the next. */
export function spells(slots) {
  const out = [];
  for (let id = 0; id < slots.length; id++) {
    const slot = slots[id];
    if (slot.team === "D" || slot.e - slot.s <= 1e-9) continue;
    const last = out[out.length - 1];
    if (last && last.team === slot.team && Math.abs(last.e - slot.s) < 1e-9) { last.e = slot.e; continue; }
    out.push({ id, s: slot.s, e: slot.e, team: slot.team });
  }
  return out;
}

export function overlaps(gt, pred) {
  const list = [];
  gt.forEach((g, gi) => pred.forEach((p, pi) => {
    if (g.team !== p.team || p.e <= g.s || g.e <= p.s) return;
    const inter = [Math.max(g.s, p.s), Math.min(g.e, p.e)];
    const union = [Math.min(g.s, p.s), Math.max(g.e, p.e)];
    list.push({ gi, pi, iou: (inter[1] - inter[0]) / (union[1] - union[0]), inter, union });
  }));
  list.sort((a, b) => b.iou - a.iou || a.gi - b.gi || a.pi - b.pi);
  return list;
}

/* One greedy pass, highest IoU first, each real turn and each of yours used once. The pairs matched
   at pass mark t are exactly the pairs of this pass with iou >= t, which is what the scorer does. */
export function pairing(gt, pred) {
  const usedG = new Set(), usedP = new Set(), pairs = [];
  for (const o of overlaps(gt, pred)) {
    if (usedG.has(o.gi) || usedP.has(o.pi)) continue;
    usedG.add(o.gi); usedP.add(o.pi); pairs.push(o);
  }
  return pairs;
}

export function score(gt, pred) {
  const pairs = pairing(gt, pred);
  const perMark = MARKS.map((mark) => {
    const tp = pairs.filter((p) => p.iou >= mark - 1e-9).length;
    const f1 = tp ? (2 * tp) / (gt.length + pred.length) : 0;
    return { mark, tp, f1 };
  });
  const mean = perMark.reduce((sum, m) => sum + m.f1, 0) / MARKS.length;
  const matchedP = new Set(pairs.map((p) => p.pi));
  return { pairs, perMark, mean, nG: gt.length, nP: pred.length, invented: pred.map((_, i) => i).filter((i) => !matchedP.has(i)) };
}

/* frames correct, for the readout: truth and file compared second by second (25 fps) */
export function framesCorrect(slots) {
  const label = (list, t) => { const hit = list.find((x) => t >= x.s && t < x.e); return hit ? hit.team : "-"; };
  let right = 0, total = SECONDS * 25;
  for (let f = 0; f < total; f++) { const t = (f + 0.5) / 25; if (label(TRUTH, t) === label(slots, t)) right++; }
  return right / total;
}
