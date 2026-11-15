/* The model behind the smoothing window: a synthetic 25 s label strip, the majority-vote filter of
   starter/baseline.py (window of ±w frames, ties to H), and the spellF1 rules of
   evaluation/possession_metrics.py (spells = maximal H/A runs, greedy one-to-one by IoU, F1 = 2tp/(nG+nP)
   per pass mark, averaged). Pure: no DOM, no kit. Every number the figure shows comes from here. */

export const FPS = 25;
export const SECONDS = 25;
export const N = FPS * SECONDS;
export const MARKS = [0.3, 0.4, 0.5, 0.6, 0.7];
export const STOPS = [0, 5, 12, 25, 50, 125];            // ±w frames on the knob

/* the real match, for the caption and the knob's engraved marks: baseline_raw, _smooth25, _smooth50, _smooth125 */
export const BASELINE = { 0: 0.0486, 25: 0.1996, 50: 0.2433, 125: 0.2242 };

/* truth: four turns, one of them a genuine 2 s away turn */
export const TRUTH = [
  { s: 0, e: 9, team: "H" },
  { s: 9, e: 11, team: "A" },
  { s: 11, e: 18, team: "H" },
  { s: 18, e: 25, team: "A" },
];
/* the tracker's mistakes: short wrong bursts of 0.2 to 0.5 s inside long turns */
export const BLIPS = [
  { at: 2.6, len: 0.32, team: "A" },
  { at: 5.4, len: 0.2, team: "A" },
  { at: 7.3, len: 0.44, team: "A" },
  { at: 13.2, len: 0.28, team: "A" },
  { at: 15.9, len: 0.6, team: "A" },
  { at: 20.5, len: 0.36, team: "H" },
  { at: 22.8, len: 0.24, team: "H" },
];

const code = (team) => (team === "H" ? 0 : 1);

export function truthFrames() {
  const out = new Int8Array(N);
  for (const t of TRUTH) out.fill(code(t.team), Math.round(t.s * FPS), Math.round(t.e * FPS));
  return out;
}
export function inputFrames() {
  const out = truthFrames();
  for (const b of BLIPS) out.fill(code(b.team), Math.round(b.at * FPS), Math.round((b.at + b.len) * FPS));
  return out;
}

/* majority vote over [i - w, i + w], clipped at the strip ends, exactly as the baseline does it */
export function votes(frames, i, w) {
  const lo = Math.max(0, i - w), hi = Math.min(N, i + w + 1);
  let h = 0;
  for (let j = lo; j < hi; j++) if (frames[j] === 0) h++;
  return { h, a: hi - lo - h, n: hi - lo };
}
export function smooth(frames, w) {
  const out = new Int8Array(N);
  if (w <= 0) { out.set(frames); return out; }
  for (let i = 0; i < N; i++) { const v = votes(frames, i, w); out[i] = v.h >= v.a ? 0 : 1; }
  return out;
}

/* maximal runs, in seconds */
export function runs(frames) {
  const out = [];
  let s = 0;
  for (let i = 1; i <= N; i++) {
    if (i === N || frames[i] !== frames[s]) { out.push({ s: s / FPS, e: i / FPS, team: frames[s] === 0 ? "H" : "A" }); s = i; }
  }
  return out;
}

export function overlaps(gt, pred) {
  const list = [];
  gt.forEach((g, gi) => pred.forEach((p, pi) => {
    if (g.team !== p.team || p.e <= g.s || g.e <= p.s) return;
    const inter = Math.min(g.e, p.e) - Math.max(g.s, p.s), union = Math.max(g.e, p.e) - Math.min(g.s, p.s);
    list.push({ gi, pi, iou: inter / union });
  }));
  list.sort((a, b) => b.iou - a.iou || a.gi - b.gi || a.pi - b.pi);
  return list;
}
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
    return { mark, tp, f1: tp ? (2 * tp) / (gt.length + pred.length) : 0 };
  });
  const mean = perMark.reduce((sum, m) => sum + m.f1, 0) / MARKS.length;
  const matchedP = new Set(pairs.map((p) => p.pi)), matchedG = new Set(pairs.map((p) => p.gi));
  return { pairs, perMark, mean, nG: gt.length, nP: pred.length,
    invented: pred.map((_, i) => i).filter((i) => !matchedP.has(i)), missed: gt.map((_, i) => i).filter((i) => !matchedG.has(i)) };
}

/* everything the figure needs for one knob stop, memoised */
const memo = {};
export function evaluate(w) {
  if (memo[w]) return memo[w];
  const input = inputFrames(), out = smooth(input, w);
  const gt = runs(truthFrames()), pred = runs(out), sc = score(gt, pred);
  let right = 0;
  const truth = truthFrames();
  for (let i = 0; i < N; i++) if (out[i] === truth[i]) right++;
  return (memo[w] = { w, input, out, gt, pred, sc, framesRight: right / N });
}
export const inputRuns = () => runs(inputFrames());
