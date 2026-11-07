/* Geometry of the smoothing window. `k` is the kit (injected, so the same source runs in Node and inline in the
   page), `P` the projection. World units are about 1 px; x runs along the timeline (7 units = 1 s, 0.28 per
   frame), z is up. Same bench, console and lane parts as the IoU bench so the two figures read as one set. */

export const CFG = {
  UX: 7, UF: 7 / 25, X0: -87.5, X1: 87.5,
  YT: -45, YI: 0, YO: 45,                 // lane centres: truth (back), input (middle), output (front)
  BLOCK_Z: 3, BLOCK_H: 10, BLOCK_D: 18,
  BEAM_Z: 40, BEAM_H: 8, BEAM_Y: 5, BX0: -109, BX1: 109,
  SLIDER: { hw: 10, hd: 11, z: 48, h: 6 },
  HOOD: { z0: 16, z1: 31, hd: 13.5, bar: 4, t: 1.6 },
  STAMP: { armZ: 50, armH: 3, rodR: 1.6, headHW: 3.5, headHD: 8, headH: 4, up: 20, down: 13 },
  DIAL_R: 19, DIAL_Z: 12, DIAL_H: 10, TURNS_AT: [-48, -85], F1_AT: [48, -85],
  SWEEP_FROM: -0.75 * Math.PI, SWEEP: 1.5 * Math.PI,
  KNOB: { x: -62, y: 80, r: 7, from: -0.42 * Math.PI, span: 0.84 * Math.PI },
  PLATE: { x: -142, y: -102, w: 284, d: 200, r: 9 }, PLATE_H: 12, FOOT_H: 5,
  TURNS_MAX: 20,
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

  /* ---------- lanes ---------- */
  function laneRail(yc) {
    const plan = { x: -98, y: yc - 12.5, w: 196, d: 25, r: 2 }, out = [];
    out.push(S(k.slabOf(plan, 0, C.BLOCK_Z, P, 3, 0.4), { tone: "mid" }));
    out.push(L(k.planOutline(k.insetPlan(plan, 2.4), C.BLOCK_Z, P, 3), { tone: "faint" }));
    out.push(D([[plan.x + 4, plan.y + 4], [plan.x + plan.w - 4, plan.y + 4], [plan.x + 4, plan.y + plan.d - 4], [plan.x + plan.w - 4, plan.y + plan.d - 4]].map(([x, y]) => at([x, y, C.BLOCK_Z])), { size: 0.4 }));
    return out.join("");
  }
  function laneLabel(yc, text) {
    return k.faceTextSvg(k.topMatrix([-139.5, yc + 1], 0, P, "x"), text, { size: 2.6, tone: "mid", anchor: "start" });
  }
  function endStops(yc) {
    return [-104.5, 99.5].map((x) => {
      const plan = { x, y: yc - 13.5, w: 5, d: 27, r: 1.2 };
      return S(k.slabOf(plan, 0, 8, P, 3, 0.5), { tone: "mid" }) + D([at([x + 2.5, yc - 7, 8]), at([x + 2.5, yc + 7, 8])], { size: 0.45 });
    }).join("");
  }
  /* one run of a lane between seconds s and e; short runs are plain tiles, long ones get an inset line */
  function block(team, s, e, yc) {
    const w = (e - s) * C.UX - 0.5;
    if (w < 0.5) return "";
    const plan = { x: xOf(s) + 0.25, y: yc - C.BLOCK_D / 2, w, d: C.BLOCK_D, r: Math.min(1, w / 3) };
    const top = C.BLOCK_Z + C.BLOCK_H, steps = w > 4 ? 3 : 2;
    const inner = w > 8 ? L(k.planOutline(k.insetPlan(plan, 2), top, P, steps), { tone: "faint" }) : "";
    return `<g class="tint-${team === "H" ? "h" : "a"}">${S(k.slabOf(plan, C.BLOCK_Z, C.BLOCK_H, P, steps, 0.5), { tone: "hi", crease: "lo", inner })}</g>`;
  }
  function peg(state, cx, yc) {
    const plan = { x: cx - 2.5, y: yc - C.BLOCK_D / 2 + 2, w: 5, d: 4, r: 0.8 }, top = C.BLOCK_Z + C.BLOCK_H;
    return `<g class="peg-${state}">${S(k.slabOf(plan, top, 2.4, P, 2, 0.3), { tone: state === "taken" ? "lit" : "mid", lit: state === "taken", crease: "lo" })}</g>`;
  }

  /* ---------- posts and beam over the input lane ---------- */
  function post(side) {
    const x = side < 0 ? -117 : 109, plan = { x, y: -6, w: 8, d: 12, r: 1.5 }, out = [];
    out.push(S(k.slabOf(plan, 0, 48, P, 3, 0.6), { tone: "mid" }));
    out.push(S(k.slabOf({ x: x - 2, y: -8, w: 12, d: 16, r: 2 }, 0, 4, P, 3, 0.5), { tone: "lo" }));
    out.push(D([at([x + 4, -6, 48]), at([x + 4, 6, 48])], { size: 0.45 }));
    out.push(D([at([x - 0.5, -6, 4]), at([x + 8.5, 6, 4])], { size: 0.4 }));
    return out.join("");
  }
  function beam() {
    const plan = { x: C.BX0, y: -C.BEAM_Y, w: C.BX1 - C.BX0, d: 2 * C.BEAM_Y, r: 1 }, top = C.BEAM_Z + C.BEAM_H, out = [];
    out.push(S(k.slabOf(plan, C.BEAM_Z, C.BEAM_H, P, 3, 0.5), { tone: "mid" }));
    const t = k.sideTicks(xOf(0), xOf(25), C.UX, 5, C.BEAM_Y, top, [2, 3.6], P, "x");
    out.push(L(t.minor, { tone: "lo" }), L(t.major, { tone: "mid" }));
    return out.join("");
  }

  /* ---------- the carriage: hood, slider, vote dial, stamp. Built around x = 0 and moved with translateAlong.
     xl, xr are the hood's inner faces relative to the centre (the window edges, clipped at the strip ends). */
  function hoodBack() {
    const H = C.HOOD, out = [];
    out.push(S(k.cylinder(-5, -9.5, 1.3, H.z1 + H.bar, C.SLIDER.z - H.z1 - H.bar, P, 16), { tone: "mid" }));
    out.push(S(k.cylinder(5, -9.5, 1.3, H.z1 + H.bar, C.SLIDER.z - H.z1 - H.bar, P, 16), { tone: "mid" }));
    return out.join("");
  }
  function hood(xl, xr) {
    const H = C.HOOD, out = [];
    const bar = { x: xl - H.t, y: -H.hd - 1, w: xr - xl + 2 * H.t, d: 2 * H.hd + 2, r: 0.8 };
    out.push(S(k.slabOf({ x: xl - H.t, y: -H.hd, w: H.t, d: 2 * H.hd, r: 0.4 }, H.z0, H.z1 - H.z0, P, 2, 0.3), { tone: "lit", lit: true, crease: "lo" }));
    out.push(S(k.slabOf({ x: xr, y: -H.hd, w: H.t, d: 2 * H.hd, r: 0.4 }, H.z0, H.z1 - H.z0, P, 2, 0.3), { tone: "lit", lit: true, crease: "lo" }));
    out.push(S(k.slabOf(bar, H.z1, H.bar, P, 2, 0.4), { tone: "lit", lit: true, crease: "lo" }));
    if (bar.w > 6) out.push(L(k.planOutline(k.insetPlan(bar, 1.4), H.z1 + H.bar, P, 2), { tone: "faint" }));
    out.push(D([at([bar.x + 1.5, -H.hd + 1.5, H.z1 + H.bar]), at([bar.x + bar.w - 1.5, H.hd - 1.5, H.z1 + H.bar])], { size: 0.4 }));
    return out.join("");
  }
  /* the slider on the beam, with the front drop rod, two lamps and the vote dial face (needle drawn live) */
  const VOTE = { x: 0, y: -1, r: 6, z: C.SLIDER.z + C.SLIDER.h, h: 3.2 };
  function slider() {
    const SL = C.SLIDER, H = C.HOOD, out = [], top = SL.z + SL.h;
    out.push(S(k.cylinder(-5, 9.5, 1.3, H.z1 + H.bar, SL.z - H.z1 - H.bar, P, 16), { tone: "mid" }));
    out.push(S(k.cylinder(5, 9.5, 1.3, H.z1 + H.bar, SL.z - H.z1 - H.bar, P, 16), { tone: "mid" }));
    out.push(S(k.slabOf({ x: -SL.hw, y: -SL.hd, w: 2 * SL.hw, d: 2 * SL.hd, r: 1.5 }, SL.z, SL.h, P, 3, 0.5), { tone: "hi", crease: "lo" }));
    out.push(L(k.planOutline(k.insetPlan({ x: -SL.hw, y: -SL.hd, w: 2 * SL.hw, d: 2 * SL.hd, r: 1.5 }, 1.6), top, P, 3), { tone: "faint" }));
    out.push(D([at([-SL.hw + 2, -SL.hd + 2, top]), at([SL.hw - 2, -SL.hd + 2, top]), at([-SL.hw + 2, SL.hd - 2, top]), at([SL.hw - 2, SL.hd - 2, top])], { size: 0.4 }));
    const dz = VOTE.z + VOTE.h;
    out.push(S(k.cylinder(VOTE.x, VOTE.y, VOTE.r, VOTE.z, VOTE.h, P, 40, 0.4), { tone: "hi", crease: "lo" }));
    out.push(L(k.ring(VOTE.x, VOTE.y, VOTE.r - 1.2, dz, P, 40), { tone: "lo" }));
    const t = k.radialTicks(VOTE.x, VOTE.y, VOTE.r - 1.6, 12, 6, dz, [0.8, 1.6], P, -Math.PI / 2, Math.PI);
    out.push(L(t.minor, { tone: "lo" }), L(t.major, { tone: "mid" }));
    out.push(L(k.ring(VOTE.x, VOTE.y, 0.9, dz, P, 12), { tone: "mid" }));
    return out.join("");
  }
  const voteNeedle = (margin) => {
    const a = Math.max(-1, Math.min(1, margin)) * -Math.PI / 2, top = VOTE.z + VOTE.h + 0.2, r = VOTE.r - 1.4;
    return k.lineOnTop([VOTE.x - Math.sin(a) * 1.6, VOTE.y + Math.cos(a) * 1.6], [VOTE.x + Math.sin(a) * r, VOTE.y - Math.cos(a) * r], top, P);
  };
  function lamp(team, on) {
    const SL = C.SLIDER, x = team === "H" ? -8 : 8, top = SL.z + SL.h;
    return `<g class="tint-${team === "H" ? "h" : "a"}">${S(k.cylinder(x, 8, 1.7, top, 2.2, P, 16, 0.3), on ? { tone: "lit", lit: true } : { tone: "mid" })}</g>`;
  }
  /* the stamp: an arm from the slider over the output lane, a rod, and a head that presses the tile */
  function stamp(team, headZ) {
    const ST = C.STAMP, SL = C.SLIDER, y = C.YO, out = [];
    out.push(S(k.slabOf({ x: -2, y: SL.hd, w: 4, d: y - SL.hd, r: 0.6 }, ST.armZ, ST.armH, P, 2, 0.3), { tone: "mid", crease: "lo" }));
    out.push(S(k.cylinder(0, y, ST.rodR, headZ + ST.headH, ST.armZ - headZ - ST.headH, P, 16), { tone: "mid" }));
    out.push(S(k.slabOf({ x: -ST.headHW, y: y - ST.headHD, w: 2 * ST.headHW, d: 2 * ST.headHD, r: 0.8 }, headZ, ST.headH, P, 2, 0.4), { tone: "hi", crease: "lo" }));
    out.push(D([at([0, y - ST.headHD + 1.5, headZ + ST.headH]), at([0, y + ST.headHD - 1.5, headZ + ST.headH])], { size: 0.4 }));
    /* a tinted cap on the head: the label about to be stamped */
    out.push(`<g class="tint-${team === "H" ? "h" : "a"}">${S(k.cylinder(0, y - 4.2, 1.8, headZ + ST.headH, 1.6, P, 16, 0.2), { tone: "hi", crease: "lo" })}</g>`);
    return out.join("");
  }

  /* ---------- the window knob: six detents, pointer drawn live ---------- */
  const knobAngle = (v) => C.KNOB.from + v * C.KNOB.span;
  function knobBase(stops) {
    const K = C.KNOB, plan = { x: K.x - 13, y: K.y - 13, w: 26, d: 26, r: 5 }, out = [];
    out.push(S(k.slabOf(plan, 0, 2.2, P, 6, 0.5), { tone: "lo", crease: "none" }));
    out.push(L(k.planOutline(k.insetPlan(plan, 2), 2.2, P, 6), { tone: "faint" }));
    /* the detent scale: six ticks between two engraved rings */
    const r0 = K.r + 1.4, r1 = K.r + 3.6;
    out.push(L(k.ring(K.x, K.y, r0, 2.2, P, 40) + k.ring(K.x, K.y, r1, 2.2, P, 40), { tone: "faint" }));
    const ticks = stops.map((_, i) => {
      const a = knobAngle(i / (stops.length - 1)), sx = Math.sin(a), sy = -Math.cos(a);
      return k.lineOnTop([K.x + sx * r0, K.y + sy * r0], [K.x + sx * r1, K.y + sy * r1], 2.2, P);
    });
    out.push(L(ticks.join(""), { tone: "mid" }));
    out.push(S(k.cylinder(K.x, K.y, K.r, 2.2, 5.5, P, 28, 0.4), { tone: "hi", crease: "lo" }));
    out.push(L(k.knurl(K.x, K.y, K.r, 2.2, 7.7, 24, P), { tone: "lo" }));
    out.push(L(k.ring(K.x, K.y, 1.4, 7.7, P, 12), { tone: "mid" }));
    out.push(k.faceTextSvg(k.topMatrix([K.x, K.y + 15.5], 2.2, P, "x"), "±frames", { size: 2.4, tone: "mid", anchor: "middle" }));
    return out.join("");
  }
  const knobPointer = (v) => {
    const K = C.KNOB, a = knobAngle(v), sx = Math.sin(a), sy = -Math.cos(a);
    return k.lineOnTop([K.x + sx * 1.4, K.y + sy * 1.4], [K.x + sx * (K.r - 0.8), K.y + sy * (K.r - 0.8)], 7.9, P);
  };

  return { C, at, S, L, D, xOf, angleOf, plate, console_, dial, needle, laneRail, laneLabel, endStops, block, peg, post, beam, hoodBack, hood, slider, voteNeedle, lamp, stamp, knobBase, knobPointer, closed };
}
