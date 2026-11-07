/* The bench as a state machine. Shared by the Node build (it paints the first frame into the markup) and by
   the page (it animates). `els` are plain targets: { innerHTML } or { setAttribute }, so no DOM is needed here.
   Every number comes from model.mjs (M); every shape from geometry.mjs (G). */

export function createScene({ G, M, k, P, els, calm = false }) {
  const C = G.C, MARKS = M.MARKS, GT = M.spells(M.TRUTH);
  const T0 = 1.6, CYCLE = 3.2, REL = 1.4, REL_END = 2.6;      // seconds: lead-in, per pair, release start, release end
  const PARK = [-119, -107, -95, -83];                         // jaws rest at the left end: u1, o1, o2, u2
  const xOf = G.xOf;
  const eps = 1e-4;
  const follow = (cur, tgt, dt, tau) => (calm || Math.abs(tgt - cur) < eps ? tgt : cur + (tgt - cur) * (1 - Math.exp(-dt / tau)));

  let modeIdx = 0, T = 0;
  const slots = M.FILES.middle.map((s) => ({ s: s.s, e: s.e }));
  const jaws = PARK.slice();
  let iou = 0, knobX = C.SWITCH.x0;
  const caps = [0, 0, 0, 0, 0];
  let lamps = [false, false, false, false, false], pinsOn = [false, false, false, false, false];
  const memo = {};

  const modeName = () => M.MODES[modeIdx];
  function plan() {
    const pred = M.spells(M.FILES[modeName()]);
    return { pred, sc: M.score(GT, pred) };
  }

  /* what the machine should be doing at time t (targets, not eased values) */
  function sceneAt(t) {
    const { pred, sc } = plan(), n = sc.pairs.length;
    const out = { n, pair: -1, jaw: PARK.slice(), iou: 0, tp: MARKS.map(() => 0), lamps: MARKS.map(() => false),
      gtState: {}, predState: {}, done: t >= T0 + n * CYCLE, sc, pred };
    sc.pairs.forEach((p, i) => {
      const ti = T0 + i * CYCLE;
      if (t >= ti) {
        out.pair = i; out.iou = p.iou;
        out.jaw = [xOf(p.union[0]), xOf(p.inter[0]), xOf(p.inter[1]), xOf(p.union[1])];
      }
      if (t >= ti + REL) {
        MARKS.forEach((m, mi) => { if (p.iou >= m - 1e-9) out.tp[mi]++; });
        out.gtState[GT[p.gi].id] = "taken";
        out.predState[pred[p.pi].id] = "taken";
      }
      if (t >= ti + REL && t < ti + REL_END) MARKS.forEach((m, mi) => { if (p.iou >= m - 1e-9) out.lamps[mi] = true; });
    });
    if (out.done) {
      out.jaw = PARK.slice(); out.iou = 0;
      sc.invented.forEach((pi) => { out.predState[pred[pi].id] = "invented"; });
    }
    out.f1 = out.tp.map((tp) => (tp ? (2 * tp) / (sc.nG + sc.nP) : 0));
    return out;
  }
  const tDone = () => { const { sc } = plan(); return T0 + sc.pairs.length * CYCLE; };
  const tStill = () => { const { sc } = plan(); return T0 + (sc.pairs.length - 1) * CYCLE + 1.8; };

  /* ---------- painting ---------- */
  const set = (key, html) => { if (memo[key] !== html) { memo[key] = html; els[key].innerHTML = html; } };
  function laneMarkup(yc, list, states) {
    return list.map((slot, id) => {
      const w = (slot.e - slot.s) * C.UX - 0.8;
      let out = G.block(slot.team, slot.s, slot.e, yc);
      if (slot.team !== "D" && w >= 7) out += G.peg(states[id] || "free", xOf((slot.s + slot.e) / 2), yc);
      return out;
    }).join("");
  }
  function paint(target) {
    const live = M.FILES[modeName()].map((s, i) => ({ team: s.team, s: slots[i].s, e: slots[i].e }));
    set("real", laneMarkup(C.YR, M.TRUTH, target.gtState));
    set("yours", laneMarkup(C.YY, live, target.predState));
    /* jaws sorted by x so the nearer plate paints last */
    const order = [["union", -1, 0], ["overlap", -1, 1], ["overlap", 1, 2], ["union", 1, 3]].sort((a, b) => jaws[a[2]] - jaws[b[2]]);
    const jawHtml = order.map(([kind, side, ix]) => `<g transform="${k.translateAlong(P, [jaws[ix], 0, 0])}">${jawParts[kind + side]}</g>`).join("");
    set("jaws", jawHtml);
    set("rods", G.rods(jaws[0], jaws[3], jaws[1], jaws[2]));
    els.needleIou.setAttribute("d", G.needle(C.IOU_AT, iou));
    const avg = caps.reduce((a, b) => a + b, 0) / caps.length;
    els.needleF1.setAttribute("d", G.needle(C.F1_AT, avg));
    pinsOn = MARKS.map((m) => iou >= m - 1e-3);
    set("pins", MARKS.map((m, i) => G.pin(m, pinsOn[i])).join(""));
    MARKS.forEach((m, i) => {
      set("col" + i, G.column(i, target.lamps[i]));
      els["cap" + i].setAttribute("transform", k.translateAlong(P, [0, 0, caps[i] * C.CAP_SPAN]));
    });
    els.knob.setAttribute("transform", k.translateAlong(P, [knobX, 0, 0]));
    lamps = target.lamps;
  }
  const jawParts = {
    union_1: G.jaw("union", -1, 0), union1: G.jaw("union", 1, 0), overlap_1: G.jaw("overlap", -1, 0), overlap1: G.jaw("overlap", 1, 0),
  };
  jawParts["union-1"] = jawParts.union_1; jawParts["overlap-1"] = jawParts.overlap_1;

  function apply(dt, snap) {
    const target = sceneAt(T), was = calm;
    const f = snap ? (cur, tgt) => tgt : (cur, tgt, tau) => follow(cur, tgt, dt, tau);
    const goal = M.FILES[modeName()];
    slots.forEach((s, i) => { s.s = f(s.s, goal[i].s, 0.32); s.e = f(s.e, goal[i].e, 0.32); });
    for (let i = 0; i < 4; i++) jaws[i] = f(jaws[i], target.jaw[i], 0.3);
    iou = f(iou, target.iou, 0.34);
    for (let i = 0; i < 5; i++) caps[i] = f(caps[i], target.f1[i], 0.3);
    knobX = f(knobX, modeIdx ? C.SWITCH.x1 : C.SWITCH.x0, 0.18);
    paint(target);
    return target;
  }
  const settled = (target) => {
    const goal = M.FILES[modeName()];
    return slots.every((s, i) => Math.abs(s.s - goal[i].s) < 0.01 && Math.abs(s.e - goal[i].e) < 0.01)
      && jaws.every((x, i) => Math.abs(x - target.jaw[i]) < 0.05) && Math.abs(iou - target.iou) < 0.002
      && caps.every((c, i) => Math.abs(c - target.f1[i]) < 0.002) && Math.abs(knobX - (modeIdx ? C.SWITCH.x1 : C.SWITCH.x0)) < 0.05;
  };

  function readout(target) {
    const { sc, pred } = target;
    const pct = (M.framesCorrect(M.FILES[modeName()]) * 100).toFixed(0);
    if (target.done) return `spellF1 ${sc.mean.toFixed(2)} · ${pct}% of frames right`;
    if (target.pair < 0) return `${sc.nP} turns for ${sc.nG} real`;
    const p = sc.pairs[target.pair], pass = MARKS.filter((m) => p.iou >= m - 1e-9);
    const clears = pass.length === MARKS.length ? "clears all 5 marks" : pass.length ? "clears " + pass.map((m) => m.toFixed(1)).join(", ") : "clears none";
    return `pair ${target.pair + 1}/${target.n} · IoU ${p.iou.toFixed(2)} · ${clears}`;
  }

  return {
    get mode() { return modeIdx; }, get time() { return T; },
    setMode(i) { modeIdx = i; T = 0; },
    jumpStill() { T = tStill(); return apply(0, true); },
    jumpTo(t) { T = t; return apply(0, true); },
    step(dt) { T += dt; const target = apply(dt, false); return { target, settled: settled(target) && T >= tDone(), done: T >= tDone() }; },
    readout() { return readout(sceneAt(T)); },
    summary() { const { sc } = plan(); return sc; },
    tDone,
  };
}
