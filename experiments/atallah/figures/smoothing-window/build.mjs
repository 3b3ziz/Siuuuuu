/* Builds the smoothing window:  node build.mjs  ->  smoothing-window.html (dark), smoothing-window-light.html,
   fragment.html. fragment.html is the figure card only (markup + scoped CSS + inline script) for pasting into
   another page. Same packaging as ../iou-bench/build.mjs so the two figures read as one set. */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as k from "../../.agents/skills/anatomy/kit/iso-kit.mjs";
import { kitScript } from "../../.agents/skills/anatomy/scripts/inline-kit.mjs";
import * as M from "./model.mjs";
import { geometry, CFG } from "./geometry.mjs";
import { createScene } from "./scene.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const WIDTH = 720, HEIGHT = 410;
const strip = (file) => readFileSync(join(HERE, file), "utf8").replace(/^export /gm, "");

const C = CFG;
const P = k.fitProjection(
  [...k.boxCorners(C.PLATE, -C.PLATE_H - C.FOOT_H, 0), [C.BX0 - 8, -8, 48], [C.BX1 + 8, 8, 48], [0, 0, 62], [-48, -85, 22], [48, -85, 22], [0, C.YO + 8, 53], [C.KNOB.x, C.KNOB.y + 16, 8]],
  WIDTH, HEIGHT, { pad: 14, azimuth: 43 },
);
const G = geometry(k, P);

/* ---------- the layers, back to front ---------- */
const MOVING = ["hoodBack", "hood", "slider", "vote", "stamp"];
function stub() { const attrs = {}; return { innerHTML: "", attrs, setAttribute(n, v) { attrs[n] = v; } }; }
const els = {};
["truth", "input", "output", "knobPtr", "needleTurns", "needleF1", ...MOVING].forEach((key) => { els[key] = stub(); });
const scene = createScene({ G, M, k, P, els, calm: true });
scene.jumpStill();                        // the first frame: the sweep at ±25 frames just finished

const group = (name) => `<g data-el="${name}"${els[name].attrs.transform ? ` transform="${els[name].attrs.transform}"` : ""}>${els[name].innerHTML}</g>`;
const needle = (name) => `<path data-el="${name}" class="iso-line" data-tone="lit" data-free="start" style="stroke-width:1.1" d="${els[name].attrs.d}"/>`;

const body = [
  G.plate(),
  G.console_(),
  G.dial(C.TURNS_AT, "turns out"),
  G.dial(C.F1_AT, "spellF1"),
  needle("needleTurns"),
  needle("needleF1"),
  G.laneRail(C.YT), G.endStops(C.YT), G.laneLabel(C.YT, "TRUTH"),
  group("truth"),
  G.laneRail(C.YI), G.endStops(C.YI), G.laneLabel(C.YI, "INPUT"),
  group("input"),
  G.post(-1),
  group("hoodBack"),
  group("hood"),
  G.beam(),
  group("slider"),
  group("vote"),
  G.laneRail(C.YO), G.endStops(C.YO), G.laneLabel(C.YO, "OUTPUT"),
  group("output"),
  group("stamp"),
  G.post(1),
  `<g data-hit="knob" style="cursor:pointer">${G.knobBase(M.STOPS)}<path data-el="knobPtr" class="iso-line" data-tone="lit" data-free="start" style="stroke-width:1.1" d="${els.knobPtr.attrs.d}"/></g>`,
];

const svg = k.figureSvg({
  width: WIDTH, height: HEIGHT,
  label: "A smoothing bench. Three lanes of tiles: the truth at the back, the tracker's jittery per-frame labels in the middle, and the smoothed output at the front. A carriage rides a beam over the middle lane. Its hood spans plus or minus w frames around the carriage, a dial on the carriage leans to whichever team fills more of the hood, and a stamp arm prints that label on the output lane as the carriage sweeps. A knob at the front sets the window from 0 to plus or minus 125 frames. Two dials at the back read how many turns came out and spellF1.",
  body,
});

/* every number in the caption comes from the model */
const E = M.STOPS.map((w) => M.evaluate(w));
const f2 = (x) => x.toFixed(2);
const caption = `The input runs under the hood. At each frame the hood spans ±w frames, the dial leans to whichever team fills more of it (ties go to home, as in the baseline), and the stamp prints that label on the output lane. ` +
  `Turn the knob: at 0 every blip survives and ${E[0].pred.length} turns come out, spellF1 ${f2(E[0].sc.mean)}. At ±${E[2].w} only the longest blip is left (${f2(E[2].sc.mean)}). At ±${E[3].w} the output matches the truth (${f2(E[3].sc.mean)}). ` +
  `At ±${E[4].w} the genuine 2 s away turn is shrinking (${f2(E[4].sc.mean)}), and at ±${E[5].w} it is gone (${f2(E[5].sc.mean)}). Frames right stay between ${Math.round(Math.min(...E.map((e) => e.framesRight)) * 100)}% and 100% the whole way. ` +
  `Synthetic strip. On the real match the baseline scores ${f2(M.BASELINE[0])} at 0, ${f2(M.BASELINE[25])} at ±25, ${f2(M.BASELINE[50])} at ±50 and ${f2(M.BASELINE[125])} at ±125: the same rise and fall, peaking later, because real possessions are longer.`;

const plateBody = k.plateHtml({
  fig: "Fig 2",
  title: "Smoothing window",
  hint: "Click the knob",
  readout: scene.readout(),
  keys: [
    { mark: "blue", label: "Home label" },
    { mark: "red", label: "Away label" },
    { mark: "lit", label: "The hood: ±w frames, the lit part" },
    { mark: "raised", label: "Carriage, vote dial and stamp" },
    { mark: "dim", label: "Pegs after a sweep: lime has a partner, red is invented or missed" },
  ],
  caption,
  body: `<div class="iso-stage" tabindex="0" role="slider" aria-label="Smoothing window: arrow keys change the window, space steps to the next stop, enter replays" aria-valuemin="0" aria-valuemax="125" aria-valuenow="${M.STOPS[scene.stop]}" aria-valuetext="${scene.readout()}">${svg}</div>`,
});

/* ---------- theme: Lucius (from ~/neo-lucius), following the host page; identical to the IoU bench ---------- */
const COMMON = `--anatomy-weight:.6px;--anatomy-ease:cubic-bezier(.32,.72,0,1);--anatomy-mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;`;
const DARK = `--anatomy-page:#303030;--anatomy-card:#383838;--anatomy-text:#a0a0a0;--anatomy-strong:#d7d7d7;--anatomy-muted:#8a8a8a;--anatomy-paper:#383838;--anatomy-face:#4a4a4a;--anatomy-top:#5a5a5a;--anatomy-shade-0:#3c3c3c;--anatomy-shade-1:#434343;--anatomy-shade-2:#4a4a4a;--anatomy-shade-3:#525252;--anatomy-lit-top:#47573c;--anatomy-lit-shade:#39472f;--anatomy-hi:#d7d7d7;--anatomy-mid:#8a8a8a;--anatomy-lo:#626262;--anatomy-faint:#4a4a4a;--anatomy-lit:#afd787;--anatomy-halo:#1c1c1c;--anatomy-halo-opacity:.9;--anatomy-dot:#d7d7d7;--anatomy-red:#ff5f5f;--anatomy-green:#afd787;--anatomy-blue:#87d7ff;--anatomy-lift:inset 0 1px 0 0 #ffffff0a,0 0 0 1px #00000026,0 12px 12px -6px #00000014;--h-paper:#2f5568;--h-top:#5aa9cc;--h-s3:#4a8cad;--h-s2:#3f7893;--h-s1:#34647b;--h-s0:#2b5266;--h-edge:#87d7ff;--a-paper:#7a3b3b;--a-top:#e06a6a;--a-s3:#c85a5a;--a-s2:#a84c4c;--a-s1:#8a3f3f;--a-s0:#703434;--a-edge:#ff5f5f;--d-paper:#2f2f2f;--d-top:#3d3d3d;--d-s3:#383838;--d-s2:#343434;--d-s1:#303030;--d-s0:#2c2c2c;--d-edge:#626262;`;
const LIGHT = `--anatomy-page:#f3f3f3;--anatomy-card:#ffffff;--anatomy-text:#585858;--anatomy-strong:#1a1a1a;--anatomy-muted:#8a8a8a;--anatomy-paper:#ffffff;--anatomy-face:#ffffff;--anatomy-top:#ffffff;--anatomy-shade-0:#d3d3d3;--anatomy-shade-1:#dcdcdc;--anatomy-shade-2:#e6e6e6;--anatomy-shade-3:#f0f0f0;--anatomy-lit-top:#eaf4e1;--anatomy-lit-shade:#d6e8cb;--anatomy-hi:#1a1a1a;--anatomy-mid:#8a8a8a;--anatomy-lo:#b6b6b6;--anatomy-faint:#dadada;--anatomy-lit:#008700;--anatomy-halo:#808080;--anatomy-halo-opacity:.3;--anatomy-dot:#3a3a3a;--anatomy-red:#b05a68;--anatomy-green:#008700;--anatomy-blue:#005faf;--anatomy-lift:inset 0 1px 0 0 #ffffff,0 0 0 1px #0000000f,0 12px 12px -6px #0000000a;--h-paper:#cfe3f4;--h-top:#9cc6ea;--h-s3:#7fb0dc;--h-s2:#6a9ecb;--h-s1:#5589b8;--h-s0:#4375a3;--h-edge:#005faf;--a-paper:#f1d6da;--a-top:#e3a3ad;--a-s3:#d58e9a;--a-s2:#c07885;--a-s1:#a96472;--a-s0:#905260;--a-edge:#b05a68;--d-paper:#ececec;--d-top:#e4e4e4;--d-s3:#d9d9d9;--d-s2:#cfcfcf;--d-s1:#c5c5c5;--d-s0:#bbbbbb;--d-edge:#9e9e9e;`;

/* every kit rule gets the .smwin prefix, so nothing leaks into the host page */
function scope(css, prefix) {
  let out = "", i = 0;
  const readBlock = (from) => { let depth = 0, j = from; do { if (css[j] === "{") depth++; else if (css[j] === "}") depth--; j++; } while (depth > 0 && j < css.length); return j; };
  while (i < css.length) {
    const open = css.indexOf("{", i);
    if (open < 0) break;
    const head = css.slice(i, open).trim(), end = readBlock(open);
    const inner = css.slice(open + 1, end - 1);
    if (head.startsWith("@keyframes")) out += `${head}{${inner}}`;
    else if (head.startsWith("@media")) out += `${head}{${scope(inner, prefix)}}`;
    else out += head.split(",").map((s) => `${prefix} ${s.trim()}`).join(",") + `{${inner}}`;
    i = end;
  }
  return out;
}
const kitCss = readFileSync(join(HERE, "../../.agents/skills/anatomy/kit/iso.css"), "utf8")
  .replace(/^\.iso\{[^}]*\}\s*/m, "").replace(/^\.iso\[data-theme="light"\]\{[^}]*\}\s*/m, "");
const CSS = [
  `.smwin{${COMMON}${DARK}color-scheme:dark}`,
  `@media (prefers-color-scheme:light){:root:not([data-theme="dark"]) .smwin{${LIGHT}color-scheme:light}}`,
  `:root[data-theme="light"] .smwin{${LIGHT}color-scheme:light}`,
  `:root[data-theme="dark"] .smwin{${DARK}color-scheme:dark}`,
  scope(kitCss, ".smwin"),
  `.smwin .tint-h{--anatomy-paper:var(--h-paper);--anatomy-face:var(--h-paper);--anatomy-top:var(--h-top);--anatomy-shade-0:var(--h-s0);--anatomy-shade-1:var(--h-s1);--anatomy-shade-2:var(--h-s2);--anatomy-shade-3:var(--h-s3)}`,
  `.smwin .tint-a,.smwin .peg-invented{--anatomy-paper:var(--a-paper);--anatomy-face:var(--a-paper);--anatomy-top:var(--a-top);--anatomy-shade-0:var(--a-s0);--anatomy-shade-1:var(--a-s1);--anatomy-shade-2:var(--a-s2);--anatomy-shade-3:var(--a-s3)}`,
  `.smwin .tint-h .iso-edge{stroke:var(--h-edge)}.smwin .tint-a .iso-edge,.smwin .peg-invented .iso-edge{stroke:var(--a-edge)}`,
  `.smwin .tint-h .iso-solid[data-lit]>.iso-top,.smwin .tint-a .iso-solid[data-lit]>.iso-top{fill:var(--anatomy-top)}.smwin .tint-h .iso-solid[data-lit]>.iso-shade,.smwin .tint-a .iso-solid[data-lit]>.iso-shade{fill:var(--anatomy-shade-2)}`,
  `.smwin .iso-swatch[data-mark="dim"] path{stroke:var(--d-edge)}`,
  `.smwin{font:14px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--anatomy-text);-webkit-font-smoothing:antialiased}`,
  `@media (max-width:560px){.smwin .iso-plate{padding:46px 12px 96px}.smwin .iso-plate-corner[data-corner="hint"]{bottom:48px}.smwin .iso-plate-corner[data-corner="readout"]{left:0;right:0;white-space:normal;text-align:left;line-height:1.5}}`,
  `.smwin .smwin-fig{margin:0;padding:0;border:0;display:block}.smwin *{letter-spacing:normal}.smwin svg{max-width:100%;fill:none}`,
  `.smwin .iso-figure{margin:0}.smwin .iso-stage{outline:none}.smwin .iso-stage:focus-visible{outline:1px solid var(--anatomy-lit);outline-offset:4px}`,
].join("\n");

/* ---------- the live code, inlined: model + geometry + scene + boot ---------- */
const BOOT = `
const P = ${JSON.stringify(P)};
const M = { FPS, SECONDS, N, MARKS, STOPS, BASELINE, TRUTH, BLIPS, truthFrames, inputFrames, votes, smooth, runs, overlaps, pairing, score, evaluate, inputRuns };
const G = geometry({ iso, solidSvg, lineSvg, dotsSvg, depthOf, haloOf, cylinder, slabOf, corners, ring, planOutline, insetPlan, lineOnTop, knurl, sideArc, radialTicks, sideTicks, topMatrix, faceTextSvg }, P);
const root = document.querySelector(".smwin");
const stage = root.querySelector(".iso-stage");
const svg = stage.querySelector("svg");
const readoutEl = root.querySelector("[data-readout]");
const still = matchMedia("(prefers-reduced-motion: reduce)");
const els = {};
svg.querySelectorAll("[data-el]").forEach((el) => { els[el.getAttribute("data-el")] = el; });
const scene = createScene({ G, M, k: { translateAlong }, P, els, calm: still.matches });
const LAST = STOPS.length - 1;
let frame = 0, last = 0, visible = false, touring = !still.matches, holdUntil = 0, resumeTimer = 0, text = "";
const say = () => {
  const next = scene.readout();
  if (next === text) return;
  text = next; readoutEl.textContent = next;
  stage.setAttribute("aria-valuetext", next);
  stage.setAttribute("aria-valuenow", String(STOPS[scene.stop]));
};
function tick(now) {
  const dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60;
  last = now;
  const r = scene.step(dt);
  say();
  if (r.settled) {
    if (touring) {
      if (!holdUntil) holdUntil = now + 2800;
      else if (now >= holdUntil) { holdUntil = 0; scene.setStop((scene.stop + 1) % STOPS.length); }
    } else { frame = 0; return; }
  }
  frame = visible ? requestAnimationFrame(tick) : 0;
}
const run = () => { if (!frame && visible) { last = 0; frame = requestAnimationFrame(tick); } };
function choose(i) {
  touring = false; holdUntil = 0;
  clearTimeout(resumeTimer);
  resumeTimer = setTimeout(() => { touring = !still.matches; holdUntil = 0; run(); }, 12000);
  scene.setStop(i);
  if (still.matches) { scene.jumpStill(); say(); return; }
  run();
}
new IntersectionObserver((entries) => { visible = entries[entries.length - 1].isIntersecting; if (visible) run(); }, { rootMargin: "120px 0px" }).observe(stage);
svg.querySelector('[data-hit="knob"]').addEventListener("click", () => choose((scene.stop + 1) % STOPS.length));
stage.addEventListener("keydown", (event) => {
  if (event.key === "ArrowRight" || event.key === "ArrowUp") choose(Math.min(LAST, scene.stop + 1));
  else if (event.key === "ArrowLeft" || event.key === "ArrowDown") choose(Math.max(0, scene.stop - 1));
  else if (event.key === "Home") choose(0);
  else if (event.key === "End") choose(LAST);
  else if (event.key === " " || event.key === "Spacebar") choose((scene.stop + 1) % STOPS.length);
  else if (event.key === "Enter") choose(scene.stop);
  else return;
  event.preventDefault();
});
if (still.matches) { scene.jumpStill(); } else { scene.setStop(0); }
say();
`;
const SCRIPT = [kitScript(), strip("model.mjs"), strip("geometry.mjs"), strip("scene.mjs"), BOOT].join("\n").replace(/<\/(script)/gi, "<\\/$1");

const fragment = `<div class="smwin"><style>${CSS}</style><figure class="smwin-fig">${plateBody.replace(/^<figure class="iso-figure">/, "").replace(/<\/figure>$/, "")}</figure><script type="module">${SCRIPT}</script></div>`;
writeFileSync(join(HERE, "fragment.html"), fragment);

const PAGE_CSS = `*{box-sizing:border-box}html{color-scheme:dark}html[data-theme="light"]{color-scheme:light}body{margin:0;background:#303030}html[data-theme="light"] body{background:#f3f3f3}@media (prefers-color-scheme:light){html:not([data-theme="dark"]) body{background:#f3f3f3}}main{width:min(760px,100% - 32px);margin:56px auto 80px}`;
const page = (theme) => `<!doctype html><html lang="en" data-theme="${theme}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Smoothing window</title><style>${PAGE_CSS}</style></head><body><main>${fragment}</main></body></html>`;
writeFileSync(join(HERE, "smoothing-window.html"), page("dark"));
writeFileSync(join(HERE, "smoothing-window-light.html"), page("light"));

const solids = (svg.match(/class="iso-solid/g) || []).length;
console.log(`wrote smoothing-window.html, smoothing-window-light.html, fragment.html · ${solids} solids in the first frame · ${svg.length} bytes of svg`);
