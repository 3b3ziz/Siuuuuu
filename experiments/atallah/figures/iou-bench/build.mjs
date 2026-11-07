/* Builds the IoU bench:  node build.mjs   ->  iou-bench.html (dark), iou-bench-light.html, fragment.html
   fragment.html is the figure card only (markup + scoped CSS + inline script) for pasting into another page. */
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
  [...k.boxCorners(C.PLATE, -C.PLATE_H - C.FOOT_H, 0), [-130, 0, 50], [130, 0, 50], [-40, -90, 24], [40, -90, 24], [C.COLS[0], 80, 30], [C.COLS[4], 80, 30], [C.SWITCH.x0, 95, 8]],
  WIDTH, HEIGHT, { pad: 14, azimuth: 43 },
);
const G = geometry(k, P);

/* ---------- the layers, back to front ---------- */
const ORDER = ["pins", "needleIou", "needleF1", "real", "yours", "rods", "jaws", "col0", "col1", "col2", "col3", "col4"];
function stub() { const attrs = {}; return { innerHTML: "", attrs, setAttribute(n, v) { attrs[n] = v; } }; }
const els = {};
[...ORDER, "knob", "cap0", "cap1", "cap2", "cap3", "cap4"].forEach((key) => { els[key] = stub(); });
const scene = createScene({ G, M, k, P, els, calm: true });
scene.jumpStill();                       // the first frame is the last pair being released

const group = (name, inner = "", extra = "") => `<g data-el="${name}"${extra}>${inner}</g>`;
const tf = (name) => (els[name].attrs.transform ? ` transform="${els[name].attrs.transform}"` : "");
const needle = (name, tone) => `<path data-el="${name}" class="iso-line" data-tone="lit" data-free="start" style="stroke-width:1.1" d="${els[name].attrs.d}"/>`;
const columns = [0, 1, 2, 3, 4].map((i) => group("col" + i, els["col" + i].innerHTML) + `<g data-el="cap${i}"${tf("cap" + i)}>${G.cap(i)}</g>`).join("");

const body = [
  G.plate(),
  G.console_(),
  G.dial(C.IOU_AT, "IoU"),
  G.dial(C.F1_AT, "spellF1"),
  group("pins", els.pins.innerHTML),
  needle("needleIou"),
  needle("needleF1"),
  G.post(-1),
  G.laneRail(C.YR), G.endStops(C.YR), G.laneLabel(C.YR, "REAL"),
  group("real", els.real.innerHTML),
  G.laneRail(C.YY), G.endStops(C.YY), G.laneLabel(C.YY, "YOURS"),
  group("yours", els.yours.innerHTML),
  G.beam(),
  group("rods", els.rods.innerHTML),
  group("jaws", els.jaws.innerHTML),
  G.post(1),
  columns,
  `<g data-hit="switch" style="cursor:pointer">${G.switchBase()}<g data-el="knob"${tf("knob")}>${G.knob()}</g></g>`,
];

const svg = k.figureSvg({
  width: WIDTH, height: HEIGHT,
  label: "A gauging bench for spellF1. Two lanes of blocks, the real turns at the back and the turns in your file at the front, with a grey low spacer for the dead ball. A caliper beam over the lanes carries two pairs of jaws: the inner pair bounds the overlap of a real turn and your matching turn, the outer pair bounds their union, and the IoU dial at the back reads the ratio. Five columns at the front are the pass marks 0.3 to 0.7. Each pair that clears a mark raises that column by 2 divided by real plus yours, and the dial at the back right reads the average, spellF1. A switch at the front left moves two wrong seconds between the middle of a turn and the edge between two turns.",
  body,
});

const plateBody = k.plateHtml({
  fig: "Fig 1",
  title: "IoU bench",
  hint: "Click the switch",
  readout: scene.readout(),
  keys: [
    { mark: "blue", label: "Home turn" },
    { mark: "red", label: "Away turn" },
    { mark: "dim", label: "Dead ball: a gap, never a turn" },
    { mark: "lit", label: "Overlap rod and jaws, the lit part" },
    { mark: "raised", label: "Union rod and jaws" },
  ],
  caption:
    "Real turns sit at the back, the turns in your file at the front. For each pair, from the best overlap down, the caliper jaws close on the overlap (lit) and on the union (outer), and the IoU dial reads one over the other. Every pass mark the needle clears lights its lamp and lifts its column by 2 ÷ (real + yours); the right dial averages the columns, which is spellF1. Flip the switch to move the 2 wrong seconds from the middle of a turn to the edge between two.",
  body: `<div class="iso-stage" tabindex="0" role="slider" aria-label="IoU bench: arrow keys or space flip the switch, enter replays" aria-valuemin="0" aria-valuemax="1" aria-valuenow="0.6" aria-valuetext="${scene.readout()}">${svg}</div>`,
});

/* ---------- theme: Lucius (from ~/neo-lucius), following the host page ---------- */
const COMMON = `--anatomy-weight:.6px;--anatomy-ease:cubic-bezier(.32,.72,0,1);--anatomy-mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;`;
const DARK = `--anatomy-page:#303030;--anatomy-card:#383838;--anatomy-text:#a0a0a0;--anatomy-strong:#d7d7d7;--anatomy-muted:#8a8a8a;--anatomy-paper:#383838;--anatomy-face:#4a4a4a;--anatomy-top:#5a5a5a;--anatomy-shade-0:#3c3c3c;--anatomy-shade-1:#434343;--anatomy-shade-2:#4a4a4a;--anatomy-shade-3:#525252;--anatomy-lit-top:#47573c;--anatomy-lit-shade:#39472f;--anatomy-hi:#d7d7d7;--anatomy-mid:#8a8a8a;--anatomy-lo:#626262;--anatomy-faint:#4a4a4a;--anatomy-lit:#afd787;--anatomy-halo:#1c1c1c;--anatomy-halo-opacity:.9;--anatomy-dot:#d7d7d7;--anatomy-red:#ff5f5f;--anatomy-green:#afd787;--anatomy-blue:#87d7ff;--anatomy-lift:inset 0 1px 0 0 #ffffff0a,0 0 0 1px #00000026,0 12px 12px -6px #00000014;--h-paper:#2f5568;--h-top:#5aa9cc;--h-s3:#4a8cad;--h-s2:#3f7893;--h-s1:#34647b;--h-s0:#2b5266;--h-edge:#87d7ff;--a-paper:#7a3b3b;--a-top:#e06a6a;--a-s3:#c85a5a;--a-s2:#a84c4c;--a-s1:#8a3f3f;--a-s0:#703434;--a-edge:#ff5f5f;--d-paper:#2f2f2f;--d-top:#3d3d3d;--d-s3:#383838;--d-s2:#343434;--d-s1:#303030;--d-s0:#2c2c2c;--d-edge:#626262;--u-paper:#6a6a6a;--u-top:#8c8c8c;--u-s3:#7c7c7c;--u-s2:#727272;--u-s1:#686868;--u-s0:#5e5e5e;--u-edge:#b0b0b0;`;
const LIGHT = `--anatomy-page:#f3f3f3;--anatomy-card:#ffffff;--anatomy-text:#585858;--anatomy-strong:#1a1a1a;--anatomy-muted:#8a8a8a;--anatomy-paper:#ffffff;--anatomy-face:#ffffff;--anatomy-top:#ffffff;--anatomy-shade-0:#d3d3d3;--anatomy-shade-1:#dcdcdc;--anatomy-shade-2:#e6e6e6;--anatomy-shade-3:#f0f0f0;--anatomy-lit-top:#eaf4e1;--anatomy-lit-shade:#d6e8cb;--anatomy-hi:#1a1a1a;--anatomy-mid:#8a8a8a;--anatomy-lo:#b6b6b6;--anatomy-faint:#dadada;--anatomy-lit:#008700;--anatomy-halo:#808080;--anatomy-halo-opacity:.3;--anatomy-dot:#3a3a3a;--anatomy-red:#b05a68;--anatomy-green:#008700;--anatomy-blue:#005faf;--anatomy-lift:inset 0 1px 0 0 #ffffff,0 0 0 1px #0000000f,0 12px 12px -6px #0000000a;--h-paper:#cfe3f4;--h-top:#9cc6ea;--h-s3:#7fb0dc;--h-s2:#6a9ecb;--h-s1:#5589b8;--h-s0:#4375a3;--h-edge:#005faf;--a-paper:#f1d6da;--a-top:#e3a3ad;--a-s3:#d58e9a;--a-s2:#c07885;--a-s1:#a96472;--a-s0:#905260;--a-edge:#b05a68;--d-paper:#ececec;--d-top:#e4e4e4;--d-s3:#d9d9d9;--d-s2:#cfcfcf;--d-s1:#c5c5c5;--d-s0:#bbbbbb;--d-edge:#9e9e9e;--u-paper:#cdcdcd;--u-top:#eaeaea;--u-s3:#c4c4c4;--u-s2:#b8b8b8;--u-s1:#aeaeae;--u-s0:#a2a2a2;--u-edge:#6a6a6a;`;

/* every kit rule gets the .iobench prefix, so nothing leaks into the host page */
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
  `.iobench{${COMMON}${DARK}color-scheme:dark}`,
  `@media (prefers-color-scheme:light){:root:not([data-theme="dark"]) .iobench{${LIGHT}color-scheme:light}}`,
  `:root[data-theme="light"] .iobench{${LIGHT}color-scheme:light}`,
  `:root[data-theme="dark"] .iobench{${DARK}color-scheme:dark}`,
  scope(kitCss, ".iobench"),
  `.iobench .tint-h{--anatomy-paper:var(--h-paper);--anatomy-face:var(--h-paper);--anatomy-top:var(--h-top);--anatomy-shade-0:var(--h-s0);--anatomy-shade-1:var(--h-s1);--anatomy-shade-2:var(--h-s2);--anatomy-shade-3:var(--h-s3)}`,
  `.iobench .tint-a,.iobench .peg-invented{--anatomy-paper:var(--a-paper);--anatomy-face:var(--a-paper);--anatomy-top:var(--a-top);--anatomy-shade-0:var(--a-s0);--anatomy-shade-1:var(--a-s1);--anatomy-shade-2:var(--a-s2);--anatomy-shade-3:var(--a-s3)}`,
  `.iobench .tint-d{--anatomy-paper:var(--d-paper);--anatomy-top:var(--d-top);--anatomy-shade-0:var(--d-s0);--anatomy-shade-1:var(--d-s1);--anatomy-shade-2:var(--d-s2);--anatomy-shade-3:var(--d-s3)}`,
  `.iobench .tint-u{--anatomy-paper:var(--u-paper);--anatomy-face:var(--u-paper);--anatomy-top:var(--u-top);--anatomy-shade-0:var(--u-s0);--anatomy-shade-1:var(--u-s1);--anatomy-shade-2:var(--u-s2);--anatomy-shade-3:var(--u-s3)}`,
  `.iobench .tint-u .iso-edge{stroke:var(--u-edge)}`,
  `.iobench .tint-h .iso-edge{stroke:var(--h-edge)}.iobench .tint-a .iso-edge,.iobench .peg-invented .iso-edge{stroke:var(--a-edge)}.iobench .tint-d .iso-edge{stroke:var(--d-edge)}`,
  `.iobench .iso-swatch[data-mark="dim"] path{stroke:var(--d-edge)}`,
  `.iobench{font:14px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--anatomy-text);-webkit-font-smoothing:antialiased}`,
  `@media (max-width:560px){.iobench .iso-plate{padding:46px 12px 96px}.iobench .iso-plate-corner[data-corner="hint"]{bottom:48px}.iobench .iso-plate-corner[data-corner="readout"]{left:0;right:0;white-space:normal;text-align:left;line-height:1.5}}`,
  `.iobench .iobench-fig{margin:0;padding:0;border:0;display:block}.iobench *{letter-spacing:normal}.iobench svg{max-width:100%;fill:none}`,
  `.iobench .iso-figure{margin:0}.iobench .iso-stage{outline:none}.iobench .iso-stage:focus-visible{outline:1px solid var(--anatomy-lit);outline-offset:4px}`,
].join("\n");

/* ---------- the live code, inlined: model + geometry + scene + boot ---------- */
const BOOT = `
const P = ${JSON.stringify(P)};
const M = { SECONDS, MARKS, TRUTH, FILES, MODES, spells, overlaps, pairing, score, framesCorrect };
const G = geometry({ iso, solidSvg, lineSvg, dotsSvg, depthOf, haloOf, cylinder, slabOf, corners, ring, planOutline, insetPlan, lineOnTop, knurl, sideArc, radialTicks, sideTicks, topMatrix, faceTextSvg }, P);
const root = document.querySelector(".iobench");
const stage = root.querySelector(".iso-stage");
const svg = stage.querySelector("svg");
const readoutEl = root.querySelector("[data-readout]");
const still = matchMedia("(prefers-reduced-motion: reduce)");
const els = {};
svg.querySelectorAll("[data-el]").forEach((el) => { els[el.getAttribute("data-el")] = el; });
const scene = createScene({ G, M, k: { translateAlong }, P, els, calm: still.matches });
let frame = 0, last = 0, visible = false, touring = !still.matches, holdUntil = 0, resumeTimer = 0, text = "";
const say = () => {
  const next = scene.readout();
  if (next === text) return;
  text = next; readoutEl.textContent = next;
  stage.setAttribute("aria-valuetext", next);
  stage.setAttribute("aria-valuenow", scene.summary().mean.toFixed(2));
};
function tick(now) {
  const dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60;
  last = now;
  const r = scene.step(dt);
  say();
  if (r.settled) {
    if (touring) {
      if (!holdUntil) holdUntil = now + 4200;
      else if (now >= holdUntil) { holdUntil = 0; scene.setMode(1 - scene.mode); }
    } else { frame = 0; return; }
  }
  frame = visible ? requestAnimationFrame(tick) : 0;
}
const run = () => { if (!frame && visible) { last = 0; frame = requestAnimationFrame(tick); } };
function choose(mode) {
  touring = false; holdUntil = 0;
  clearTimeout(resumeTimer);
  resumeTimer = setTimeout(() => { touring = !still.matches; holdUntil = 0; run(); }, 9000);
  if (still.matches) { scene.setMode(mode); scene.jumpStill(); say(); return; }
  scene.setMode(mode); run();
}
new IntersectionObserver((entries) => { visible = entries[entries.length - 1].isIntersecting; if (visible) run(); }, { rootMargin: "120px 0px" }).observe(stage);
svg.querySelector('[data-hit="switch"]').addEventListener("click", () => choose(1 - scene.mode));
stage.addEventListener("keydown", (event) => {
  if (event.key === "ArrowRight" || event.key === "ArrowDown") choose(1);
  else if (event.key === "ArrowLeft" || event.key === "ArrowUp") choose(0);
  else if (event.key === " " || event.key === "Spacebar") choose(1 - scene.mode);
  else if (event.key === "Enter") choose(scene.mode);
  else return;
  event.preventDefault();
});
if (still.matches) { scene.jumpStill(); } else { scene.setMode(0); }
say();
`;
const SCRIPT = [kitScript(), strip("model.mjs"), strip("geometry.mjs"), strip("scene.mjs"), BOOT].join("\n").replace(/<\/(script)/gi, "<\\/$1");

const fragment = `<div class="iobench"><style>${CSS}</style><figure class="iobench-fig">${plateBody.replace(/^<figure class="iso-figure">/, "").replace(/<\/figure>$/, "")}</figure><script type="module">${SCRIPT}</script></div>`;
writeFileSync(join(HERE, "fragment.html"), fragment);

const PAGE_CSS = `*{box-sizing:border-box}html{color-scheme:dark}html[data-theme="light"]{color-scheme:light}body{margin:0;background:#303030}html[data-theme="light"] body{background:#f3f3f3}@media (prefers-color-scheme:light){html:not([data-theme="dark"]) body{background:#f3f3f3}}main{width:min(760px,100% - 32px);margin:56px auto 80px}`;
const page = (theme) => `<!doctype html><html lang="en" data-theme="${theme}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>IoU bench</title><style>${PAGE_CSS}</style></head><body><main>${fragment}</main></body></html>`;
writeFileSync(join(HERE, "iou-bench.html"), page("dark"));
writeFileSync(join(HERE, "iou-bench-light.html"), page("light"));

const solids = (svg.match(/class="iso-solid/g) || []).length;
console.log(`wrote iou-bench.html, iou-bench-light.html, fragment.html · ${solids} solids in the first frame · ${svg.length} bytes of svg`);
