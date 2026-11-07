/* Geometry of the IoU bench. `k` is the kit (injected, so the same source runs in Node and inline in the page),
   `P` the projection. World units are about 1 px; x runs along the timeline (7 units = 1 s), z is up. */

export const CFG = {
  UX: 7, X0: -105,
  YR: -26, YY: 26,                 // lane centres: real turns (back), your turns (front)
  BLOCK_Z: 3, BLOCK_H: 10, SPACER_H: 3.4, BLOCK_D: 18,
  BEAM_Z: 38, BEAM_H: 8, BEAM_Y: 7,
  COLS: [-72, -36, 0, 36, 72], COL_Y: 66, COL_D: 12, COL_H: 26, CAP_LO: 5.5, CAP_SPAN: 15,
  DIAL_R: 19, DIAL_Z: 12, DIAL_H: 10, IOU_AT: [-48, -85], F1_AT: [48, -85],
  SWEEP_FROM: -0.75 * Math.PI, SWEEP: 1.5 * Math.PI,
  SWITCH: { x0: -38, x1: -8, y: 88 },
  PLATE: { x: -142, y: -102, w: 284, d: 200, r: 9 }, PLATE_H: 12, FOOT_H: 5,
};

export function geometry(k, P) {
  const C = CFG;
  const at = (p) => k.iso(p, P);
  const S = (paths, style) => k.solidSvg(paths, style);
  const L = (d, style) => k.lineSvg(d, style);
  const D = (points, style) => k.dotsSvg(points, style);
  const xOf = (t) => C.X0 + t * C.UX;
  const byDepth = (points) => [...points].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));
  const angleOf = (v) => C.SWEEP_FROM + v * C.SWEEP;
  const closed = (points) => "M" + points.map((p) => p[0].toFixed(1) + " " + p[1].toFixed(1)).join("L") + "Z";

  /* ---------- the bench ---------- */
  function plate() {
    const PL = C.PLATE, out = [`<path class="iso-halo" d="${k.haloOf(PL, -C.PLATE_H - C.FOOT_H, C.PLATE_H, P)}"/>`];
    for (const [x, y] of byDepth(k.corners(PL, 20))) {
      out.push(S(k.cylinder(x, y, 7, -C.PLATE_H - C.FOOT_H, 1.6, P, 28), { tone: "lo" }));
      out.push(S(k.cylinder(x, y, 5.4, -C.PLATE_H - C.FOOT_H + 1.6, C.FOOT_H - 1.6, P, 28), { tone: "mid" }));
    }
    out.push(S(k.slabOf(PL, -C.PLATE_H, C.PLATE_H, P, 8, 1.6), { tone: "mid" }));
    out.push(L(k.planOutline(k.insetPlan(PL, 5), 0, P), { tone: "lo" }));
    const screws = k.corners(PL, 10);
    out.push(L(screws.map(([x, y]) => k.ring(x, y, 2.2, 0, P, 16)).join(""), { tone: "lo" }));
    out.push(D(screws.map(([x, y]) => at([x, y, 0])), { size: 0.5 }));
    /* label plate with three engraved rule lines, front right */
    const tag = { x: 98, y: 76, w: 34, d: 17, r: 2 };
    out.push(S(k.slabOf(tag, 0, 0.8, P, 4), { tone: "lo", crease: "none" }));
    out.push(L(k.planOutline(k.insetPlan(tag, 1.6), 0.8, P, 4), { tone: "faint" }));
    [[tag.y + 5, 22], [tag.y + 8.5, 15], [tag.y + 12, 19]].forEach(([y, len]) => {
      out.push(L(k.lineOnTop([tag.x + 5, y], [tag.x + 5 + len, y], 0.8, P), { tone: "lo", free: true }));
    });
    out.push(D([at([tag.x + 3, tag.y + 3, 0.8]), at([tag.x + tag.w - 3, tag.y + tag.d - 3, 0.8])], { size: 0.45 }));
    return out.join("");
  }

  function console_() {
    const out = [], B = { x: -112, y: -101, w: 224, d: 31, r: 5 };
    out.push(`<path class="iso-halo" d="${k.haloOf(B, 0, 12, P)}" style="filter:blur(5px)"/>`);
    out.push(S(k.slabOf(B, 0, C.DIAL_Z, P, 6, 1), { tone: "mid" }));
    out.push(L(k.planOutline(k.insetPlan(B, 3.4), C.DIAL_Z, P, 6), { tone: "faint" }));
    out.push(D([[B.x + 6, B.y + 6], [B.x + B.w - 6, B.y + 6], [B.x + 6, B.y + B.d - 6], [B.x + B.w - 6, B.y + B.d - 6]].map(([x, y]) => at([x, y, C.DIAL_Z])), { size: 0.45 }));
    return out.join("");
  }

  function dial(centre, label) {
    const [x, y] = centre, R = C.DIAL_R, top = C.DIAL_Z + C.DIAL_H, out = [];
    out.push(S(k.cylinder(x, y, R, C.DIAL_Z, C.DIAL_H, P, 64, 0.8), { tone: "hi", crease: "lo" }));
    out.push(L(k.knurl(x, y, R, top - 3.4, top, 84, P, 0.3), { tone: "lo" }));
    out.push(L(k.sideArc(x, y, R, top - 3.4, P, 40), { tone: "faint" }));
    out.push(L(k.ring(x, y, R - 2.2, top, P, 64), { tone: "lo" }));
    const t = k.radialTicks(x, y, R - 3, 50, 5, top, [1.3, 2.8], P, C.SWEEP_FROM, C.SWEEP);
    out.push(L(t.minor, { tone: "lo" }), L(t.major, { tone: "mid" }));
    out.push(L(k.ring(x, y, 1.6, top, P, 16), { tone: "mid" }));
    out.push(k.faceTextSvg(k.topMatrix([x, y + 10.5], top, P, "x"), label, { size: 2.8, tone: "mid", anchor: "middle" }));
    return out.join("");
  }

  const needle = (centre, v) => {
    const [x, y] = centre, a = angleOf(Math.min(1, Math.max(0, v))), top = C.DIAL_Z + C.DIAL_H + 0.2;
    return k.lineOnTop([x - Math.sin(a) * 3.6, y + Math.cos(a) * 3.6], [x + Math.sin(a) * (C.DIAL_R - 2.2), y - Math.cos(a) * (C.DIAL_R - 2.2)], top, P);
  };

  /* a pass-mark pin beside the IoU dial: lit once the needle has reached it */
  const pinAt = (m) => {
    const a = angleOf(m), r = C.DIAL_R + 4.2;
    return [C.IOU_AT[0] + Math.sin(a) * r, C.IOU_AT[1] - Math.cos(a) * r];
  };
  function pin(m, on) {
    const [x, y] = pinAt(m);
    return S(k.cylinder(x, y, 1.9, C.DIAL_Z, 4.2, P, 16, 0.3), on ? { tone: "lit", lit: true } : { tone: "mid" });
  }

  /* ---------- lanes ---------- */
  function laneRail(yc) {
    const plan = { x: -113, y: yc - 12.5, w: 226, d: 25, r: 2 }, out = [];
    out.push(S(k.slabOf(plan, 0, C.BLOCK_Z, P, 3, 0.4), { tone: "mid" }));
    out.push(L(k.planOutline(k.insetPlan(plan, 2.4), C.BLOCK_Z, P, 3), { tone: "faint" }));
    out.push(D([[plan.x + 4, plan.y + 4], [plan.x + plan.w - 4, plan.y + 4], [plan.x + 4, plan.y + plan.d - 4], [plan.x + plan.w - 4, plan.y + plan.d - 4]].map(([x, y]) => at([x, y, C.BLOCK_Z])), { size: 0.4 }));
    return out.join("");
  }
  function laneLabel(yc, text) {
    return k.faceTextSvg(k.topMatrix([-139.5, yc + 1], 0, P, "x"), text, { size: 2.6, tone: "mid", anchor: "start" });
  }
  function endStops(yc) {
    return [-119.5, 114.5].map((x) => {
      const plan = { x, y: yc - 13.5, w: 5, d: 27, r: 1.2 };
      return S(k.slabOf(plan, 0, 8, P, 3, 0.5), { tone: "mid" }) + D([at([x + 2.5, yc - 7, 8]), at([x + 2.5, yc + 7, 8])], { size: 0.45 });
    }).join("");
  }

  /* one turn (or the dead-ball spacer) of a lane, between times s and e */
  function block(team, s, e, yc) {
    const w = (e - s) * C.UX - 0.8;
    if (w < 0.6) return "";
    const plan = { x: xOf(s) + 0.4, y: yc - C.BLOCK_D / 2, w, d: C.BLOCK_D, r: Math.min(1, w / 3) };
    if (team === "D") {
      return `<g class="tint-d">${S(k.slabOf(plan, C.BLOCK_Z, C.SPACER_H, P, 3, 0.3), { tone: "lo", crease: "none" })}</g>`;
    }
    const top = C.BLOCK_Z + C.BLOCK_H, steps = 3;
    const inner = w > 8 ? L(k.planOutline(k.insetPlan(plan, 2), top, P, steps), { tone: "faint" }) : "";
    return `<g class="tint-${team === "H" ? "h" : "a"}">${S(k.slabOf(plan, C.BLOCK_Z, C.BLOCK_H, P, steps, 0.5), { tone: "hi", crease: "lo", inner })}</g>`;
  }
  /* the "taken" peg on a turn: free, taken (lime) or invented (red) */
  function peg(state, cx, yc) {
    const plan = { x: cx - 2.5, y: yc - C.BLOCK_D / 2 + 2, w: 5, d: 4, r: 0.8 }, top = C.BLOCK_Z + C.BLOCK_H;
    return `<g class="peg-${state}">${S(k.slabOf(plan, top, 2.4, P, 2, 0.3), { tone: state === "taken" ? "lit" : "mid", lit: state === "taken", crease: "lo" })}</g>`;
  }

  /* ---------- caliper beam, rods and jaws ---------- */
  const BX0 = -124, BX1 = 124;
  function post(side) {
    const x = side < 0 ? -132 : 124, plan = { x, y: -6, w: 8, d: 12, r: 1.5 }, out = [];
    out.push(S(k.slabOf(plan, 0, 46, P, 3, 0.6), { tone: "mid" }));
    out.push(S(k.slabOf({ x: x - 2, y: -8, w: 12, d: 16, r: 2 }, 0, 4, P, 3, 0.5), { tone: "lo" }));
    out.push(D([at([x + 4, -6, 46]), at([x + 4, 6, 46])], { size: 0.45 }));
    out.push(D([at([x - 0.5, -6, 4]), at([x + 8.5, 6, 4])], { size: 0.4 }));
    return out.join("");
  }
  function beam() {
    const plan = { x: BX0, y: -C.BEAM_Y, w: BX1 - BX0, d: 2 * C.BEAM_Y, r: 1 }, top = C.BEAM_Z + C.BEAM_H, out = [];
    out.push(S(k.slabOf(plan, C.BEAM_Z, C.BEAM_H, P, 3, 0.5), { tone: "mid" }));
    const t = k.sideTicks(xOf(0), xOf(30), C.UX, 5, C.BEAM_Y, top, [2, 3.6], P, "x");
    out.push(L(t.minor, { tone: "lo" }), L(t.major, { tone: "mid" }));
    return out.join("");
  }
  /* the two measuring rods on the beam: union (outer) and overlap (lit) */
  function rods(u1, u2, o1, o2) {
    const top = C.BEAM_Z + C.BEAM_H, out = [];
    if (u2 - u1 > 0.5) out.push(S(k.slabOf({ x: u1, y: -5.6, w: u2 - u1, d: 4.2, r: 0.6 }, top, 2.2, P, 2, 0.3), { tone: "mid", crease: "lo" }));
    if (o2 - o1 > 0.5) out.push(S(k.slabOf({ x: o1, y: 1.4, w: o2 - o1, d: 4.2, r: 0.6 }, top, 2.2, P, 2, 0.3), { tone: "lit", lit: true, crease: "lo" }));
    return out.join("");
  }
  /* a jaw: a thin plate hanging from a slider on the beam. kind "union" or "overlap". The plate's inner face is at x. */
  function jaw(kind, side, x) {
    const lit = kind === "overlap", span = lit ? 36 : 41, z0 = lit ? 26 : 22, out = [];
    const px = side < 0 ? (lit ? x : x - 2) : (lit ? x - 2 : x);
    out.push(S(k.slabOf({ x: px, y: -span, w: 2, d: 2 * span, r: 0.6 }, z0, 37 - z0, P, 2, 0.3), lit ? { tone: "lit", lit: true, crease: "lo" } : { tone: "hi", crease: "lo" }));
    const sy = lit ? -0.5 : -9.5, sd = 9.5;
    const sx = px + 1 - 4;
    out.push(S(k.slabOf({ x: sx, y: sy, w: 8, d: sd, r: 1 }, 36, 13, P, 3, 0.4), lit ? { tone: "lit", lit: true, crease: "lo" } : { tone: "mid" }));
    out.push(D([at([sx + 4, sy + sd / 2, 49])], { size: 0.5 }));
    return lit ? out.join("") : `<g class="tint-u">${out.join("")}</g>`;
  }

  /* ---------- the five pass-mark columns ---------- */
  function column(i, lampOn) {
    const x = C.COLS[i], y = C.COL_Y, out = [];
    const house = { x: x - 8.5, y, w: 17, d: C.COL_D, r: 2 }, face = y + C.COL_D, top = C.COL_H;
    out.push(`<path class="iso-halo" d="${k.haloOf(house, 0, top, P)}" style="filter:blur(4px)"/>`);
    out.push(S(k.slabOf(house, 0, top, P, 4, 0.6), { tone: "mid" }));
    /* closed slot on the front face, scale dots beside it */
    const sx0 = x - 2.4, sx1 = x + 2.4, z0 = C.CAP_LO - 2.4, z1 = C.CAP_LO + C.CAP_SPAN + 2.6;
    out.push(L(closed([at([sx0, face, z0]), at([sx1, face, z0]), at([sx1, face, z1]), at([sx0, face, z1])]), { tone: "faint" }));
    const dots = [0, 0.25, 0.5, 0.75, 1].map((v) => at([x + 6, face, C.CAP_LO + v * C.CAP_SPAN]));
    out.push(D(dots, { size: 0.5, tone: "mid" }));
    out.push(D([at([x - 6.2, face, z0]), at([x - 6.2, face, z1])], { size: 0.4, tone: "lo" }));
    out.push(S(k.cylinder(x, y + 5, 3.6, top, 3, P, 24, 0.3), lampOn ? { tone: "lit", lit: true } : { tone: "mid" }));
    out.push(L(k.ring(x, y + 5, 5, top, P, 24), { tone: "faint" }));
    out.push(k.faceTextSvg(k.topMatrix([x, y + 10.8], top, P, "x"), C.MARKS_TXT[i], { size: 2.9, tone: "mid", anchor: "middle" }));
    return out.join("");
  }
  /* the sliding cap, built at the bottom of its slot and moved with translateAlong */
  function cap(i) {
    const x = C.COLS[i], face = C.COL_Y + C.COL_D;
    return S(k.slabOf({ x: x - 3.6, y: face - 0.4, w: 7.2, d: 3.2, r: 0.8 }, C.CAP_LO - 1.4, 2.8, P, 2, 0.3), { tone: "lit", lit: true, crease: "lo" });
  }

  /* ---------- the switch: where do the 2 wrong seconds go ---------- */
  function switchBase() {
    const W = C.SWITCH, plan = { x: W.x0 - 10, y: W.y - 6.5, w: W.x1 - W.x0 + 20, d: 13, r: 5 }, out = [];
    out.push(S(k.slabOf(plan, 0, 2.2, P, 6, 0.5), { tone: "lo", crease: "none" }));
    out.push(L(k.planOutline(k.insetPlan(plan, 2), 2.2, P, 6), { tone: "faint" }));
    out.push(D([W.x0, W.x1].map((x) => at([x, W.y, 2.2])), { size: 0.55, tone: "mid" }));
    out.push(D([at([plan.x + 2.6, W.y, 2.2]), at([plan.x + plan.w - 2.6, W.y, 2.2])], { size: 0.4, tone: "lo" }));
    return out.join("");
  }
  function knob() {
    const W = C.SWITCH, out = [];
    out.push(S(k.cylinder(0, W.y, 5.4, 2.2, 5.5, P, 28, 0.4), { tone: "hi", crease: "lo" }));
    out.push(L(k.knurl(0, W.y, 5.4, 2.2, 7.7, 24, P), { tone: "lo" }));
    out.push(L(k.lineOnTop([0, W.y], [4.9, W.y], 7.7, P), { tone: "lit" }));
    return out.join("");
  }

  return { C, at, S, L, D, xOf, angleOf, plate, console_, dial, needle, pinAt, pin, laneRail, laneLabel, endStops, block, peg, post, beam, rods, jaw, column, cap, switchBase, knob, closed };
}
CFG.MARKS_TXT = ["0.3", "0.4", "0.5", "0.6", "0.7"];
