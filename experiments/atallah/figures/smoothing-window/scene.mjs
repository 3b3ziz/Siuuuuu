/* The smoothing window as a state machine. Shared by the Node build (it paints the first frame into the markup)
   and by the page (it animates). `els` are plain targets: { innerHTML } or { setAttribute }, so no DOM is
   needed here. Every number comes from model.mjs (M); every shape from geometry.mjs (G). */

export function createScene({ G, M, k, P, els, calm = false }) {
  const C = G.C, STOPS = M.STOPS, N = M.N, FPS = M.FPS;
  const LEAD = 0.9, SWEEP = 6.4;                         // seconds: the hood returns and resizes, then one sweep
  const eps = 1e-4;
  const follow = (cur, tgt, dt, tau) => (calm || Math.abs(tgt - cur) < eps ? tgt : cur + (tgt - cur) * (1 - Math.exp(-dt / tau)));

  let stopIdx = 3, T = 0;
  let pos = 0, width = STOPS[stopIdx], margin = 0, headZ = C.STAMP.up, knob = stopIdx / (STOPS.length - 1), nTurns = 0, f1 = 0;
  const input = M.inputFrames();
  const truthRuns = M.runs(M.truthFrames());
  const inputRuns = M.runs(input);
  const memo = {};

  const w = () => STOPS[stopIdx];
  const ev = () => M.evaluate(w());

  /* what the machine should be doing at time t (targets, not eased values) */
  function sceneAt(t) {
    const e = ev(), done = t >= LEAD + SWEEP, sweeping = t >= LEAD && !done;
    const posT = t < LEAD ? 0 : Math.min(N - 1, ((t - LEAD) / SWEEP) * (N - 1));
    const v = M.votes(input, Math.round(posT), e.w);
    const revealed = done ? M.SECONDS : posT / FPS;
    return {
      e, done, sweeping, pos: posT, votes: v, margin: (v.h - v.a) / v.n, team: v.h >= v.a ? "H" : "A",
      revealed, turnsOut: done ? e.pred.length : e.pred.filter((r) => r.s < revealed).length,
      headZ: sweeping ? C.STAMP.down : C.STAMP.up, f1: done ? e.sc.mean : 0,
    };
  }
  const tDone = () => LEAD + SWEEP;

  /* ---------- painting ---------- */
  const set = (key, html) => { if (memo[key] !== html) { memo[key] = html; els[key].innerHTML = html; } };
  const move = (key, x) => { const t = k.translateAlong(P, [x, 0, 0]); if (memo["t:" + key] !== t) { memo["t:" + key] = t; els[key].setAttribute("transform", t); } };
  function lane(runs, yc, upTo, pegOf) {
    return runs.map((r, i) => {
      const e = Math.min(r.e, upTo);
      if (e - r.s <= 1e-9) return "";
      let out = G.block(r.team, r.s, e, yc);
      const state = pegOf && pegOf(i);
      if (state && (r.e - r.s) * C.UX >= 7) out += G.peg(state, G.xOf((r.s + r.e) / 2), yc);
      return out;
    }).join("");
  }
  function paint(target) {
    const { e } = target, sc = e.sc;
    const matchedG = new Set(sc.pairs.map((p) => p.gi)), matchedP = new Set(sc.pairs.map((p) => p.pi));
    set("truth", lane(truthRuns, C.YT, M.SECONDS, target.done ? (i) => (matchedG.has(i) ? "taken" : "invented") : null));
    set("input", lane(inputRuns, C.YI, M.SECONDS, null));
    set("output", lane(e.pred, C.YO, target.revealed, target.done ? (i) => (matchedP.has(i) ? "taken" : "invented") : null));
    const xc = G.xOf(pos / FPS), half = (width + 0.5) * C.UF;
    const xl = Math.max(C.X0, xc - half) - xc, xr = Math.min(C.X1, xc + half) - xc;
    set("hood", G.hood(Math.round(xl * 20) / 20, Math.round(xr * 20) / 20));
    set("hoodBack", G.hoodBack());
    set("slider", G.slider());
    set("vote", G.lamp("H", target.sweeping && target.team === "H") + G.lamp("A", target.sweeping && target.team === "A") +
      `<path class="iso-line" data-tone="lit" data-free="start" style="stroke-width:1" d="${G.voteNeedle(margin)}"/>`);
    set("stamp", G.stamp(target.team, Math.round(headZ * 10) / 10));
    ["hoodBack", "hood", "slider", "vote", "stamp"].forEach((key) => move(key, xc));
    els.knobPtr.setAttribute("d", G.knobPointer(knob));
    els.needleTurns.setAttribute("d", G.needle(C.TURNS_AT, nTurns / C.TURNS_MAX));
    els.needleF1.setAttribute("d", G.needle(C.F1_AT, f1));
  }

  function apply(dt, snap) {
    const target = sceneAt(T);
    const f = snap ? (cur, tgt) => tgt : (cur, tgt, tau) => follow(cur, tgt, dt, tau);
    pos = f(pos, target.pos, 0.12);
    width = f(width, w(), 0.28);
    margin = f(margin, target.sweeping ? target.margin : 0, 0.07);
    headZ = f(headZ, target.headZ, 0.1);
    knob = f(knob, stopIdx / (STOPS.length - 1), 0.2);
    nTurns = f(nTurns, target.turnsOut, 0.22);
    f1 = f(f1, target.f1, 0.35);
    paint(target);
    return target;
  }
  const settled = (target) => Math.abs(pos - target.pos) < 0.05 && Math.abs(width - w()) < 0.05 && Math.abs(headZ - target.headZ) < 0.02
    && Math.abs(knob - stopIdx / (STOPS.length - 1)) < 0.002 && Math.abs(f1 - target.f1) < 0.002 && Math.abs(nTurns - target.turnsOut) < 0.02;

  function readout(target) {
    const { e, votes: v } = target, label = `±${e.w} frames`;
    if (target.done) return `${label} · ${e.pred.length} turns out · spellF1 ${e.sc.mean.toFixed(2)} · ${(e.framesRight * 100).toFixed(0)}% of frames right`;
    if (!target.sweeping) return `${label} · window ${2 * e.w + 1} frame${e.w ? "s" : ""} (${((2 * e.w + 1) / FPS).toFixed(2)} s)`;
    return `${label} · ${(target.pos / FPS).toFixed(1)} s · under the hood H ${v.h} · A ${v.a}`;
  }

  return {
    get stop() { return stopIdx; }, get time() { return T; },
    setStop(i) { stopIdx = Math.max(0, Math.min(STOPS.length - 1, i)); T = 0; },
    jumpStill() { T = tDone() + 0.01; return apply(0, true); },
    jumpTo(t) { T = t; return apply(0, true); },
    step(dt) { T += dt; const target = apply(dt, false); return { target, settled: settled(target) && T >= tDone(), done: T >= tDone() }; },
    readout() { return readout(sceneAt(T)); },
    summary() { return ev(); },
    tDone,
  };
}
