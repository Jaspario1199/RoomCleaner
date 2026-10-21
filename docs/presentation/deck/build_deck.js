// RoomCleaner interview deck (draft) — 17 slides + 7 backups.
//
// Content plan: docs/presentation/DECK_STORYLINE.md. Numbers: docs/presentation/FUNDAMENTALS.md and
// calculations/presentation_fundamentals.json (re-read here; the figures typed into slide text are
// asserted against the JSON before the deck is written). Visual system: deck_kit.js
// (copied from deck_assets/build_style_sampler.js).
//
//   NODE_PATH=<dir with pptxgenjs, react-icons, react, react-dom, sharp> \
//   APPLY_THEME=<pptx skill>/scripts/apply_theme.js \
//   node docs/presentation/deck/build_deck.js
//
// Optional: SOFFICE_PY=<pptx skill>/scripts/office/soffice.py to also write the PDF export.
//
// Pattern used on every decision slide: eyebrow, claim title, evidence pill(s) top-right, hero visual
// left, vertical WANTED / REALIZED / DECIDED / RESULT / BUT rail right (active step in Signal),
// fundamentals box under the rail, PLANNED placeholder card under the hero when a result is not in yet.

"use strict";

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");
const sharp = require("sharp");
const React = require("react");
const ReactDOMServer = require("react-dom/server");

const { createKit, THEME, HEX, W, H, M, ROOT, P, GRID } = require("./deck_kit");
const NOTES = require("./deck_notes");

const OUT_DIR = __dirname;
const OUT = path.join(OUT_DIR, "RoomCleaner_SpaceX_draft.pptx");
const ASSETS = path.join(OUT_DIR, "assets");
const APPLY_THEME = process.env.APPLY_THEME;
const SOFFICE_PY = process.env.SOFFICE_PY;

const kit = createKit("RoomCleaner — technical presentation (draft)");
const { pres, C, tags, railV, callout, body, caption, eyebrowLabel, mat, render, renderFit, photo, fundBox, plannedCard, limitLine, chartOpts, plotRect, tag } = kit;

// ------------------------------------------------------------------ numbers from the fundamentals sheet
const FUND = JSON.parse(fs.readFileSync(P("calculations/presentation_fundamentals.json"), "utf8"));
const V = FUND.values;

/** Every figure typed into a slide must match the JSON within tol; otherwise the build stops. */
const CHECKS = [
  // [json key, value as shown, tolerance]
  ["t01_T_0.15", 32.1, 0.06], ["t01_T_0.30", 16.2, 0.06], ["t01_T_0.60", 8.3, 0.06], ["t01_T_1.20", 4.6, 0.06],
  ["t01_w", 8.86, 0.01], ["t01_dh", 2.17, 0.01], ["t01_f_use", 11.9, 0.01], ["t01_f_full", 17.9, 0.06], ["t01_lp_k_task", 1.1, 0.01],
  ["t01_need_kg", 1.35, 0.001], ["t02_c15_cap", 1.1, 0.01],
  ["t02_current", 1.06, 0.01], ["t02_f_core", 23.8, 0.05], ["t02_f_full", 17.9, 0.06], ["t02_hold", 0.255, 0.001], ["t02_run", 0.179, 0.001],
  ["t02_c15_maxclaw", 202, 0.5], ["t02_c12_maxclaw", 397, 0.5], ["t02_c10_maxclaw", 478, 0.5], ["t02_c8_maxclaw", 570, 0.5],
  ["t02_c15_fuse", 11.9, 0.01], ["t02_c12_fuse", 14.0, 0.01], ["t02_c10_fuse", 14.9, 0.06], ["t02_c8_fuse", 15.9, 0.05], ["t02_c10_gain", 25, 0.01],
  ["t02_c15_lcore", 47.1, 0.05], ["t02_c15_lfull", 62.8, 0.05], ["t02_r_full", 10.0, 0.01], ["t02_layers", 5, 0],
  ["t03_p_m", 2.0, 0.05], ["t03_T_sealed_no", 64, 0.5], ["t03_T_sealed_asbuilt", 46, 0.3], ["t03_T_sealed_design", 40, 0.5],
  ["t03_T_open_no", 47, 0.5], ["t03_T_open_asbuilt", 39, 0.1], ["t03_T_open_design", 35, 0.2], ["t03_T_vented_no", 51, 0.1], ["t03_T_vented_asbuilt", 41, 0.2], ["t03_T_vented_design", 36, 0.4],
  ["t03_as_built_eta", 37, 0.3], ["t03_design_eta", 74, 0.5], ["t03_as_built_rfin", 22, 0.1], ["t03_design_rfin", 10.9, 0.05],
  ["t03_as_built_m", 13.5, 0.05], ["t03_as_built_ml", 2.69, 0.01], ["t03_slab_ratio", 1260, 1], ["t03_slab_petg", 14.0, 0.05],
  ["t04_m1_sf48", 0.41, 0.01], ["t04_m1_sf60", 0.35, 0.01], ["t04_v7_sf_pin60", 2.05, 0.01], ["t04_v7_sf_big60", 2.50, 0.01], ["t04_v7_sf_sync60", 2.0, 0.01],
  ["t04_v7_sf_pin48", 2.40, 0.01], ["t04_v7_sf_big48", 2.93, 0.01], ["t04_v7_sf_sync48", 2.34, 0.01], ["t04_tauj_n2", 0.83, 0.01], ["t04_stroke_n2", 76.5, 0.01],
  ["t05_N_jeans_mu03", 17.7, 0.05], ["t05_N_jeans_mu06", 8.9, 0.05], ["t05_N_lb_mu03", 8.9, 0.05], ["t05_N_lb_mu06", 4.5, 0.05], ["t05_fmin", 13.3, 0.05],
  ["t09_dl", 2.5, 0.01], ["t09_F", 7.5, 0.01], ["t09_share_T06", 90, 0.5],
  ["t10_vd16_2", 0.51, 0.01], ["t10_vd18_2", 0.82, 0.01],
  ["t11_dstar_0", 171.1, 0.05], ["t11_dstar_50", 139.6, 0.05], ["t11_saved_50", 32.5, 0.05], ["t11_slope", -0.63, 0.005],
  ["t08_sig_closed", 12.9, 0.05], ["t08_dx_single", 6.6, 0.05], ["t08_sig_4", 1.3, 0.05], ["t08_dx_board", 0.68, 0.01],
  ["t07_tilt_stale_max", 12.9, 0.05], ["t07_tilt_est_max", 20.7, 0.05], ["t07_tilt_stale_med", 8.7, 0.05], ["t07_tilt_est_med", 13.8, 0.05],
];
for (const [key, shown, tol] of CHECKS) {
  if (shown === null) continue;
  if (!(key in V)) throw new Error(`fundamentals JSON has no key ${key}`);
  if (Math.abs(V[key] - shown) > tol) throw new Error(`slide figure ${shown} disagrees with ${key} = ${V[key]}`);
}
// Torque-basis range (decision: show the one-/two-phase uncertainty as a range). The 0.36 N·m rating is for two coils at
// 1.5 A; if it is a two-phase figure the usable torque at the same total current is 1/sqrt(2) of the one-phase scaling.
const TWO = Math.SQRT1_2;
for (const [label, val, shown, tol] of [
  ["full-spool pull, two-phase", V.t02_f_full * TWO, 12.6, 0.05], ["core pull, two-phase", V.t02_f_core * TWO, 16.8, 0.05],
  ["design force, two-phase", V.t01_f_use * TWO, 8.4, 0.05], ["slip limit, two-phase", V.t02_f_snag * TWO, 24.0, 0.1], ["slip limit, one-phase", V.t02_f_snag, 34.0, 0.05],
  ["design force at the core, two-phase", V.t02_f_use_core * TWO, 11.2, 0.05],
]) if (Math.abs(val - shown) > tol) throw new Error(`${label}: ${val} vs ${shown}`);
// values used straight from the JSON (charts)
const r1 = (x) => Math.round(x * 10) / 10;

// ------------------------------------------------------------------ small helpers
const SECTION = { open: "Open", a1: "Act 1 · Physics sets the limits", a2: "Act 2 · Making it buildable", a3: "Act 3 · Electronics and debugging", close: "Close", back: "Backups" };
const DECISIONS = [];   // collected for the word-count report
const BACKUPS = [];
const ALL_SLIDES = [];  // {n, label, notes}
let slideNo = 0;

function addContent(section, label) {
  const s = pres.addSlide({ masterName: "Content", sectionTitle: section });
  slideNo += 1;
  ALL_SLIDES.push({ n: slideNo, label });
  return s;
}

/** Speaker notes (they travel with the file): what to say, the numbers, likely questions, and an optional first-person line. */
function notes(o) {
  if (!o) throw new Error("missing notes");
  const out = [];
  out.push("SAY: " + o.say);
  if (o.numbers) out.push("NUMBERS: " + o.numbers);
  (o.qa || []).forEach(([q, a], i) => out.push(`LIKELY QUESTION${o.qa.length > 1 ? " " + (i + 1) : ""}: ${q}\nANSWER: ${a}`));
  if (o.fp) out.push(o.fp);
  return out.join("\n\n");
}

/** Decision slide on the common grid. */
function decision(cfg) {
  const s = addContent(cfg.section, `${cfg.n} ${cfg.topic}`);
  s.addText(`DECISION ${String(cfg.n).padStart(2, "0")} · ${cfg.topic}`, { placeholder: "eyebrow" });
  s.addText(cfg.title, { placeholder: "title" });
  tags(s, cfg.tags);
  const planned = cfg.planned;
  const heroH = planned ? GRID.BOT - GRID.TOP - GRID.PLANNED_H - 0.15 : GRID.BOT - GRID.TOP;
  cfg.hero(s, { x: GRID.LX, y: GRID.TOP, w: GRID.LW, h: heroH });
  if (planned) plannedCard(s, planned.text, GRID.LX, GRID.BOT - GRID.PLANNED_H, GRID.LW, GRID.PLANNED_H, planned.head);
  railV(s, cfg.rail, cfg.active, GRID.RX, GRID.TOP, GRID.RW);
  const fy = GRID.TOP + 5 * GRID.PITCH + 0.15;
  fundBox(s, cfg.fund, GRID.RX, fy, GRID.RW, GRID.BOT - fy);
  s.addNotes(notes(NOTES[String(cfg.n)]));
  DECISIONS.push({ n: cfg.n, title: cfg.title, rail: cfg.rail });
  return s;
}

async function iconPng(Icon, color) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Icon, { color: "#" + color, size: 256 }));
  const buf = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// ------------------------------------------------------------------ build
async function build() {
  fs.mkdirSync(ASSETS, { recursive: true });
  // derived asset: left (open-jaws) panel of the camera-view figure, header text cropped away
  const c050 = P("renders/claw_tube_length_view/c050_Dstar140.png");
  const c050Panel = path.join(ASSETS, "c050_open_jaws_panel.png");
  await sharp(c050).extract({ left: 22, top: 92, width: 712, height: 672 }).toFile(c050Panel);

  // ================================================================ 1 · Title
  pres.addSection({ title: SECTION.open });
  let s = pres.addSlide({ masterName: "Dark Title", sectionTitle: SECTION.open });
  slideNo += 1; ALL_SLIDES.push({ n: 1, label: "Title" });
  s.addText("RoomCleaner", { placeholder: "title" });
  s.addText([{ text: "A four-cable ceiling robot", options: { breakLine: true } }, { text: "designed to pick laundry off the floor" }], { placeholder: "subtitle" });
  s.addText("Jasper Buntinx · Technical presentation · Oct 27, 2026", { placeholder: "byline" });
  photo(s, "13_gen1_station_lifting_test_weight.jpg", W * 0.45, 0, W * 0.55, H, "hero_photo", { fx: 0.5, fy: 0.5 });
  s.addNotes(notes(NOTES["1"]));

  // ================================================================ 2 · What I built
  s = addContent(SECTION.open, "2 What I built");
  s.addText("WHAT I BUILT · HOW I WORKED", { placeholder: "eyebrow" });
  s.addText("Solo project: a four-winch cable robot, a camera claw, and the control architecture.", { placeholder: "title" });
  {
    const tl = [["Jul 16", "Concept", "Simulator, BOM, first CAD"], ["Aug", "Gen-1 bench", "Printed plate, test weight"], ["Oct 7", "SolidWorks gen-2", "Station v1 to v3"],
      ["Oct 20", "Gripper v6", "Geared jaws"], ["Oct 27", "Panel", "Today's talk"]];
    const ty = 2.95, tx0 = M + 0.9, tx1 = W - M - 0.9, ts = (tx1 - tx0) / (tl.length - 1);
    s.addShape(pres.shapes.LINE, { x: tx0, y: ty, w: tx1 - tx0, h: 0, line: { color: C.text1, width: 1.5 }, objectName: "timeline_axis" });
    tl.forEach(([d, t, sub], i) => {
      const x = tx0 + i * ts, cur = i === tl.length - 2, fut = i === tl.length - 1;
      s.addShape(pres.shapes.OVAL, { x: x - 0.11, y: ty - 0.11, w: 0.22, h: 0.22, fill: { color: cur ? C.accent1 : fut ? C.background1 : C.text1 }, line: { color: cur ? C.accent1 : C.text1, width: 1.5 }, objectName: `tl_node_${i + 1}` });
      s.addText(d, { x: x - 0.9, y: ty - 0.7, w: 1.8, h: 0.35, fontSize: 14, bold: true, fontFace: "Arial", color: cur ? C.accent1 : C.text2, align: "center", margin: 0, isTextBox: true });
      s.addText(t, { x: x - 1.1, y: ty + 0.25, w: 2.2, h: 0.35, fontSize: 16, bold: true, fontFace: "Arial", color: C.text1, align: "center", margin: 0, isTextBox: true });
      s.addText(sub, { x: x - 1.1, y: ty + 0.62, w: 2.2, h: 0.55, fontSize: 13, color: C.text2, align: "center", valign: "top", margin: 0, isTextBox: true });
    });
    // bought / made
    const cy = 4.5, ch = 2.15, cw = 3.7;
    [["BOUGHT", "Stepper motors, A4988 drivers, ESP32 boards, DROK buck, MG996R servo, bearings, pulleys, line.", false], ["MADE BY ME", "Station and claw design in SolidWorks, printed and machined parts, bench wiring, test plan.", true]].forEach(([k, v, mine], i) => {
      const x = M + i * (cw + 0.25);
      s.addShape(pres.shapes.RECTANGLE, { x, y: cy, w: cw, h: ch, fill: { color: mine ? C.accent5 : C.background2 }, line: { color: mine ? C.accent1 : C.background2, width: mine ? 1.5 : 0.75 }, objectName: `card_${i + 1}` });
      eyebrowLabel(s, k, x + 0.25, cy + 0.25, cw - 0.5, mine ? C.text1 : C.text2);
      s.addText(v, { x: x + 0.25, y: cy + 0.65, w: cw - 0.5, h: ch - 0.8, fontSize: 16, color: C.text1, valign: "top", margin: 0, isTextBox: true });
    });
    // evidence legend
    const lx = 8.55, lw = W - M - lx;
    eyebrowLabel(s, "HOW TO READ THE TAGS", lx, cy + 0.02, lw);
    [["MEASURED", "On hardware, with an instrument"], ["CALCULATED", "Hand or CAD calculation"], ["SIMULATED", "Run in a model or simulator"], ["PLANNED", "Not done yet"]].forEach(([k, v], i) => {
      const y = cy + 0.4 + i * 0.4;
      tag(s, k, lx, y, 1.45);
      s.addText(v, { x: lx + 1.65, y: y - 0.02, w: lw - 1.65, h: 0.32, fontSize: 13, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
    });
  }
  s.addNotes(notes(NOTES["2"]));

  // ================================================================ 3 · Done means
  s = addContent(SECTION.open, "3 Done means");
  s.addText("THE PROBLEM · WHAT DONE MEANS", { placeholder: "eyebrow" });
  s.addText("Done means jeans from anywhere on the floor into the hamper.", { placeholder: "title" });
  {
    const mx = M, my = 2.0, mw = 4.7, mh = 4.85;
    mat(s, mx, my, mw, mh, "render_mat");
    const clawH = 4.1;
    const cw = render(s, "claw_v6_camera_bay.png", mx + 0.35, my + 0.25, clawH, "claw_render");
    const st = renderFit(s, "station_v3_assembly.png", mx + 0.35 + cw + 0.2, my + 0.55, mw - 0.35 - cw - 0.2 - 0.25, 2.9, "station_render");
    caption(s, "Claw v6 with camera bay", mx + 0.25, my + 0.25 + clawH + 0.1, 2.2);
    caption(s, "Winch station v3", st.x - 0.05, st.y + st.h + 0.1, 2.0);
    const cards = [["0.9 kg", "Provisional jeans payload plus 2 m/s²; first gate 1 lb", true], ["≤ 450 g", "Claw mass budget", false], ["4 × studs", "Stations designed to screw into wall studs", false],
      ["1 switch", "The switched power strip is the only kill switch", false], ["0 people", "Nobody under the robot while it moves", false]];
    const x0 = 5.6, w0 = W - M - x0, ch = 0.86, gap = 0.14;
    cards.forEach(([big, lab, hot], i) => {
      const y = 2.0 + i * (ch + gap);
      s.addShape(pres.shapes.RECTANGLE, { x: x0, y, w: w0, h: ch, fill: { color: C.background2 }, line: { color: C.background2, width: 0.5 }, objectName: `req_card_${i + 1}` });
      s.addText(big, { x: x0 + 0.25, y, w: 2.3, h: ch, fontSize: 28, bold: true, fontFace: "Arial", color: hot ? C.accent1 : C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: `req_big_${i + 1}` });
      s.addText(lab, { x: x0 + 2.65, y, w: w0 - 2.85, h: ch, fontSize: 16, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: `req_label_${i + 1}` });
    });
  }
  s.addNotes(notes(NOTES["3"]));

  // ================================================================ 4 · Cable statics
  pres.addSection({ title: SECTION.a1 });
  {
    const depths = []; for (let d = 0.15; d <= 1.2001; d += 0.05) depths.push(Math.round(d * 100) / 100);
    const sinphi = (d) => d / Math.sqrt(d * d + V.t01_dh * V.t01_dh);
    const Tst = depths.map((d) => r1(V.t01_w / (4 * sinphi(d))));
    const Tdy = depths.map((d) => r1(V.t01_w_dyn / (4 * sinphi(d))));
    const box = { x: GRID.LX, y: GRID.TOP, w: GRID.LW, h: GRID.BOT - GRID.TOP };
    const layout = { x: 0.14, y: 0.04, w: 0.82, h: 0.68 };
    decision({
      n: 4, topic: "CABLE STATICS", section: SECTION.a1, tags: ["CALCULATED"], active: 1,
      title: "Cable angle sets the limits: walls bind at task height, ceiling above.",
      hero: (sl) => {
        sl.addChart(pres.charts.SCATTER, [
          { name: "Depth", values: depths },
          { name: "Static: 1 lb + 0.45 kg claw (budget)", values: Tst },
          { name: "With +2 m/s²", values: Tdy },
        ], chartOpts({
          ...box, chartColors: [HEX.signal, HEX.steel], lineSize: 3, lineDataSymbol: "none",
          valAxisMinVal: 0, valAxisMaxVal: 40, valAxisMajorUnit: 10, catAxisMinVal: 0.15, catAxisMaxVal: 1.2, catAxisMajorUnit: 0.15,
          valGridLine: { color: HEX.fog, size: 0.75 }, catGridLine: { style: "none" },
          showValAxisTitle: true, valAxisTitle: "Tension per cable (N)", showCatAxisTitle: true, catAxisTitle: "Depth below the anchors (m)",
          showLegend: true, legendPos: "b", layout,
        }));
        limitLine(sl, plotRect(box, layout), 40, V.t01_f_use, "Winch design force 8.4–11.9 N", { color: HEX.ink });
        limitLine(sl, plotRect(box, layout), 40, V.t01_f_use * TWO, "", { color: HEX.ink });
      },
      rail: [
        "Use the whole room.",
        "32 N at 0.15 m depth, 8.3 N at 0.6 m.",
        "Ceiling margin 0.4 m, plus a wall margin.",
        "Max 0.5 kg at 0.4 m, 1.1 kg at task height.",
        "Claw mass counts like payload; 0.45 kg is a budget.",
      ],
      fund: { eq: "T = W / (4 sin φ)   (claw centred, equal share)", sub: "sin φ = d / √(d² + D_{h}²), D_{h} = 2.17 m, W = 8.86 N: T = 32.1 N at 0.15 m, 8.3 N at 0.60 m. Off-centre needs a linear program." },
    });
  }

  // ================================================================ 5 · Motor, driver, spool
  {
    const cats = [["Ø15", "t02_c15_maxclaw", "t02_c15_fuse"], ["Ø12", "t02_c12_maxclaw", "t02_c12_fuse"], ["Ø10", "t02_c10_maxclaw", "t02_c10_fuse"], ["Ø8", "t02_c8_maxclaw", "t02_c8_fuse"]];
    const labels = cats.map(([d, , f]) => `${d} mm\n${V[f].toFixed(1)} N`);
    const vals = cats.map(([, m]) => Math.round(V[m]));
    decision({
      n: 5, topic: "DRIVE", section: SECTION.a1, tags: ["MEASURED", "CALCULATED"], active: 1,
      title: "The driver, not the motor, capped my pull; the fix is open.",
      planned: { text: "Luggage-scale pull at 1.06 A, empty and full spool; settles the 0.7 factor and one- vs two-phase torque." },
      hero: (sl, b) => {
        sl.addText("0.79–0.85 V → 0.99–1.06 A", { x: b.x, y: b.y - 0.02, w: b.w, h: 0.62, fontSize: 26, bold: true, fontFace: "Arial", color: C.accent1, margin: 0, valign: "middle", isTextBox: true, objectName: "big_number" });
        sl.addText("Vref pot maximum (two readings) and the current it allows", { x: b.x, y: b.y + 0.6, w: b.w, h: 0.26, fontSize: 12, color: C.text2, margin: 0, valign: "top", isTextBox: true });
        const cb = { x: b.x, y: b.y + 0.9, w: b.w, h: b.h - 0.9 };
        const layout = { x: 0.13, y: 0.1, w: 0.84, h: 0.56 };
        sl.addChart(pres.charts.BAR, [{ name: "Largest claw that still lifts 0.9 kg jeans (g)", labels, values: vals }], chartOpts({
          ...cb, barDir: "col", barGapWidthPct: 55, chartColors: [HEX.steel],
          showValue: true, dataLabelPosition: "inBase", dataLabelColor: HEX.paper, dataLabelFormatCode: '#,##0" g"', valAxisMinVal: 0, valAxisMaxVal: 1250, valAxisMajorUnit: 250,
          valAxisLabelFormatCode: "#,##0", showValAxisTitle: true, valAxisTitle: "Largest claw, upper bound (g)", showCatAxisTitle: true, catAxisTitle: "Spool core and one-phase design force", layout,
        }));
        const pr = plotRect(cb, layout);
        // printed-claw estimate band 1,050 to 1,250 g and the 450 g budget
        const yTop = pr.y, yBand = pr.y + pr.h * (1 - 1050 / 1250);
        sl.addShape(pres.shapes.RECTANGLE, { x: pr.x, y: yTop, w: pr.w, h: yBand - yTop, fill: { color: C.background2 }, line: { color: C.text2, width: 1, dashType: "dash" }, objectName: "claw_estimate_band" });
        sl.addText("Printed claw estimate 1,050–1,250 g (unweighed)", { x: pr.x + 0.1, y: yTop, w: pr.w - 0.2, h: yBand - yTop, fontSize: 11, bold: true, fontFace: "Arial", color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "claw_estimate_label" });
        limitLine(sl, pr, 1250, 450, "450 g budget", { align: "left" });
      },
      rail: [
        "Raise current from 1.0 to 1.35 A.",
        "Vref pot maxes at 0.85 V: 1.06 A cap.",
        "Run at the cap; open: core +25 %, or 3:1 gearing.",
        "Winches hold ≤ ~1.1 kg; claw plus jeans ~2 kg.",
        "Full-spool pull 12.6–17.9 N; pull test decides.",
      ],
      fund: { eq: "I = Vref / (8·R_{s}) = 0.85 V / 0.8 Ω = 1.06 A", sub: "τ_{run} = 0.7 τ_{hold}, with τ_{hold} = 0.255 N·m (one-phase) or 0.18 N·m (two-phase). T = τ / r: at r = 10 mm 17.9 or 12.6 N; at the core 23.8 or 16.8 N." },
    });
  }

  // ================================================================ 6 · Heat
  {
    const box = { x: GRID.LX, y: GRID.TOP, w: GRID.LW, h: GRID.BOT - GRID.TOP - GRID.PLANNED_H - 0.15 };
    const layout = { x: 0.13, y: 0.05, w: 0.84, h: 0.62 };
    const f0 = (k) => Math.round(V[k]);
    decision({
      n: 6, topic: "HEAT", section: SECTION.a1, tags: ["CALCULATED"], active: 3,
      title: "A sealed station would heat the motor mount, my most loaded joint.",
      planned: { text: "Hold test, vented shell, 1.06 A: model predicts 41 °C (as-built fin); pass below 60 °C." },
      hero: (sl) => {
        const cat = ["Sealed (the motivation)", "Vented (planned test)", "Open air"];
        sl.addChart(pres.charts.BAR, [
          { name: "No fin", labels: cat, values: [f0("t03_T_sealed_no"), f0("t03_T_vented_no"), f0("t03_T_open_no")] },
          { name: "As-built fin, 0.019 in", labels: cat, values: [f0("t03_T_sealed_asbuilt"), f0("t03_T_vented_asbuilt"), f0("t03_T_open_asbuilt")] },
          { name: "Drawn fin, 1/8 in", labels: cat, values: [f0("t03_T_sealed_design"), f0("t03_T_vented_design"), f0("t03_T_open_design")] },
        ], chartOpts({
          ...box, barDir: "col", barGapWidthPct: 45, barGrouping: "clustered", chartColors: [HEX.steel, HEX.signal, HEX.steelLight],
          showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0", dataLabelFontSize: 11, valAxisMinVal: 0, valAxisMaxVal: 70, valAxisMajorUnit: 10,
          showValAxisTitle: true, valAxisTitle: "Motor case temperature (°C)", showLegend: true, legendPos: "b", legendFontSize: 11, layout,
        }));
        limitLine(sl, plotRect(box, layout), 70, 60, "60 °C target", { align: "right" });
      },
      rail: [
        "A clean, closed printed shell.",
        "Holding stepper heats (I²R); PETG conducts 1/800 of aluminium.",
        "Vents plus an aluminium fin.",
        "Sealed 64 to 46 °C with fin; vented 51 to 41 °C.",
        "No thermometer data yet; vented hold test planned.",
      ],
      fund: { eq: "P = I²R;   R_{cond} = L / (k A);   R_{conv} = 1 / (h A)", sub: "P = 1.06² × 1.8 Ω = 2.0 W (R assumed). Flange path: 5 mm PETG 14 K/W vs 3.2 mm aluminium 0.011 K/W (1260× = 800× k, 1.6× thickness)." },
    });
  }

  // ================================================================ 7 · Building the fin
  {
    decision({
      n: 7, topic: "BUILDING THE FIN", section: SECTION.a1, tags: ["MEASURED", "CALCULATED"], active: 2,
      title: "Drawn at 1/8-inch, built at 0.019-inch, then rechecked the physics.",
      planned: { text: "Hold test: does the thin sheet bow or buzz, and are the screw threads deep enough?" },
      hero: (sl, b) => {
        const g = 0.12, cw = (b.w - g) / 2, chh = (b.h - g) / 2, ph = chh - 0.3;
        const cell = (c, r) => ({ x: b.x + c * (cw + g), y: b.y + r * (chh + g) });
        let p = cell(0, 0);
        photo(sl, "06_shear_with_drawings_and_blanks.jpg", p.x, p.y, cw, ph, "spread_1", { fx: 0.5, fy: 0.55 });
        caption(sl, "1  Sheared blanks, shop drawing", p.x, p.y + ph + 0.04, cw);
        p = cell(1, 0);
        photo(sl, "01_mill_drilling_fin_closeup.jpg", p.x, p.y, cw, ph, "spread_2", { fx: 0.5, fy: 0.36 });
        caption(sl, "2  Drilling the holes on the mill", p.x, p.y + ph + 0.04, cw);
        p = cell(0, 1);
        const map = photo(sl, "16_heat_fin_on_motor_straight.jpg", p.x, p.y, cw, ph, "spread_3", { fx: 0.5, fy: 0.62 });
        caption(sl, "3  Fitted: boss centred, 4 holes line up", p.x, p.y + ph + 0.04, cw);
        const boss = map(0.475, 0.565);
        if (boss) callout(sl, boss[0], boss[1], p.x + cw - 0.08, p.y + 0.3, "7/8 in hole", "right");
        p = cell(1, 1);
        sl.addText("Fin efficiency η, %", { x: p.x, y: p.y, w: cw, h: 0.24, fontSize: 11, bold: true, fontFace: "Arial", color: C.text2, margin: 0, isTextBox: true });
        sl.addChart(pres.charts.BAR, [{ name: "Fin efficiency (%)", labels: ["Drawn 1/8 in", "Built 0.019 in"], values: [Math.round(V.t03_design_eta), Math.round(V.t03_as_built_eta)] }], chartOpts({
          x: p.x, y: p.y + 0.24, w: cw, h: chh - 0.24, barDir: "col", barGapWidthPct: 40, chartColors: [HEX.steel, HEX.signal], invertedColors: [HEX.steel],
          showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0"%"', dataLabelFontSize: 12, valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 100, valGridLine: { style: "none" },
          catAxisLabelFontSize: 11, layout: { x: 0.04, y: 0.04, w: 0.92, h: 0.68 },
        }));
      },
      rail: [
        "Drawing: 1/8 in plate, fin efficiency 74 %.",
        "As built: 0.019 in (0.48 mm) sheet, not the 1/8 in drawn.",
        "Re-ran the fin equation: 74 % falls to 37 %.",
        "Still carries about half the heat: 46 °C.",
        "May buzz; screws reach 2.7 mm deeper.",
      ],
      fund: { eq: "η = tanh(mL) / (mL),   m = √(2h / (k t))", sub: "t = 0.483 mm: m = 13.5 /m, mL = 2.69, η = 37 %, R_{fin} = 22 K/W. Drawn 1/8 in: mL = 1.05, η = 74 %, R_{fin} = 10.9 K/W." },
    });
  }

  // ================================================================ 8 · Spool
  pres.addSection({ title: SECTION.a2 });
  decision({
    n: 8, topic: "SPOOL", section: SECTION.a2, tags: ["CALCULATED"], active: 2,
    title: "My first spool outran its motor shaft; the fix changed the math.",
    hero: (sl, b) => {
      mat(sl, b.x, b.y, b.w, b.h, "render_mat");
      const items = [["gen1_winch_spool.png", "Gen-1 spool", "Ø20 core, 32 mm long"], ["spool_v2.png", "v2", "bore Ø5.2, too tight"], ["spool_v3.png", "v3", "Ø15 core, bore Ø5.45"]];
      const cw = (b.w - 0.4) / 3;
      items.forEach(([f, t, sub], i) => {
        const x = b.x + 0.2 + i * cw;
        renderFit(sl, f, x, b.y + 0.3, cw - 0.1, 2.1, `spool_render_${i + 1}`);
        sl.addText(t, { x, y: b.y + 2.55, w: cw - 0.1, h: 0.3, fontSize: 14, bold: true, fontFace: "Arial", color: C.text1, margin: 0, isTextBox: true });
        sl.addText(sub, { x, y: b.y + 2.85, w: cw - 0.1, h: 0.5, fontSize: 12, color: C.text2, valign: "top", margin: 0, isTextBox: true });
      });
      sl.addShape(pres.shapes.LINE, { x: b.x + 0.2, y: b.y + 3.55, w: b.w - 0.4, h: 0, line: { color: C.text2, width: 0.75 }, objectName: "mat_rule" });
      [["Ø20 → Ø15", "core, mm"], ["32 → 22", "overall length, mm"], ["Ø5.2 → Ø5.45", "bore, mm"]].forEach(([big, lab], i) => {
        const x = b.x + 0.2 + i * cw;
        sl.addText(big, { x, y: b.y + 3.7, w: cw - 0.05, h: 0.4, fontSize: 16, bold: true, fontFace: "Arial", color: i === 2 ? C.accent1 : C.text1, margin: 0, valign: "middle", isTextBox: true });
        sl.addText(lab, { x, y: b.y + 4.1, w: cw - 0.05, h: 0.3, fontSize: 11, color: C.text2, margin: 0, valign: "top", isTextBox: true });
      });
    },
    rail: [
      "32 mm spool (26 mm drum) on a Ø20 core.",
      "About 14.5 mm past the 24 mm shaft (CAD).",
      "Ø15 core, 16 mm drum; radius tracks wound length.",
      "v2 bore too tight: Ø5.2 opened to Ø5.45.",
      "Printed holes shrink; no caliper reading yet.",
    ],
    fund: { eq: "r(n) = r_{0} + n·d·p;   T = τ / r(n);   ℓ = 2πr", sub: "20 ft of line, diameter assumed 0.5 mm (not measured): 5 layers, r = 7.5 to 10 mm, T = 23.8 to 17.9 N (one-phase), line per rev 47 to 63 mm (+33 %)." },
  });

  // ================================================================ 9 · Homing switch
  decision({
    n: 9, topic: "HOMING SWITCH", section: SECTION.a2, tags: [{ kind: "CALCULATED", label: "CALCULATED · CAD", w: 1.75 }], active: 3,
    title: "Bead must not cross the pulley; verification caught rev C.",
    planned: { head: "PLANNED — not yet run", text: "Trip test: 5 mm bead on real line against a printed rev D arm." },
    hero: (sl, b) => {
      const map = photo(sl, "09_homing_switch_perfboard.jpg", b.x, b.y, b.w, b.h, "hero_photo", { fx: 0.42, fy: 0.6 });
      const roller = map(0.14, 0.753);
      if (roller) callout(sl, roller[0], roller[1], roller[0] + 1.1, roller[1] - 0.75, "Bench switch, not rev D");
    },
    rail: [
      "Bead on the line trips a home switch.",
      "Mid-span, the bead rides over the pulley.",
      "A drop arm under the pulley.",
      "Rev C missed in X and Y; rev D overlaps 3.75 mm.",
      "Never trip-tested on real line yet.",
    ],
    fund: { eq: "Y overlap = (r_{bead} + r_{roller}) − Y_{roller}", sub: "(2.5 + 2.25) − 1.0 = 3.75 mm, need ≥ 2.0 mm. Rev C: 5.0 mm off in X, 10.5 mm in Y. X error ≤ 1.0 mm across 18 to 22 mm pulleys." },
  });

  // ================================================================ 10 · Removable station
  decision({
    n: 10, topic: "REMOVABLE STATION", section: SECTION.a2, tags: ["CALCULATED", "PLANNED"], active: 3,
    title: "A removable station moves the anchor from a screw to a slide.",
    planned: { text: "SolidWorks linear static study (stress, safety factor, deflection) and a station-mount pull test." },
    hero: (sl, b) => {
      mat(sl, b.x, b.y, b.w, b.h, "render_mat");
      const wm = renderFit(sl, "wall_mount_v3.png", b.x + 0.25, b.y + 0.2, 1.8, b.h - 0.9, "wall_mount_render");
      const si = renderFit(sl, "slipin_v3.png", b.x + 2.35, b.y + 0.2, b.w - 2.6, b.h - 0.9, "slipin_render");
      caption(sl, "Fixed wall frame", wm.x - 0.05, b.y + b.h - 0.55, 1.9);
      caption(sl, "Slide-in housing", si.x, b.y + b.h - 0.55, 2.3);
    },
    rail: [
      "Swap a station without re-calibrating the room.",
      "Anchor error maps 1:1; studs see pull-out.",
      "Fixed frame plus slide-in; target SF ≥ 3 at 34 N.",
      "Hand estimate: tab root 8–14 MPa vs 8.33 limit; study pending.",
      "Statics can't see creep; pull test too.",
    ],
    fund: { eq: "σ = M c / I (rail root);   δ = F L³ / (3 E I) (cable exit)", sub: "Targets at the 34 N slip load (24 N if two-phase): σ ≤ 8.33 MPa (SF 3 on 25 MPa), ≤ 0.5 mm at the cable exit. Direct drive; 3:1 gearing adds ~2.7×." },
  });

  // ================================================================ 11 · Gripper
  {
    const cats = ["1 lb\nμ 0.3", "1 lb\nμ 0.6", "Jeans\nμ 0.3", "Jeans\nμ 0.6"];
    const vals = [V.t05_N_lb_mu03, V.t05_N_lb_mu06, V.t05_N_jeans_mu03, V.t05_N_jeans_mu06].map((x) => r1(x));
    decision({
      n: 11, topic: "GRIPPER", section: SECTION.a2, tags: ["CALCULATED", "SIMULATED"], active: 4,
      title: "A clamp stalls the servo every grip; teeth are checked at stall.",
      hero: (sl, b) => {
        sl.addText("Bars: needed per jaw  ·  Dashed lines: jaw force available", { x: b.x, y: b.y, w: b.w, h: 0.25, fontSize: 11, bold: true, fontFace: "Arial", color: C.text2, margin: 0, isTextBox: true });
        const cb = { x: b.x, y: b.y + 0.25, w: b.w, h: 3.05 };
        const layout = { x: 0.13, y: 0.05, w: 0.84, h: 0.62 };
        sl.addChart(pres.charts.BAR, [{ name: "Required normal force per jaw (N)", labels: cats, values: vals }], chartOpts({
          ...cb, barDir: "col", barGapWidthPct: 55, chartColors: [HEX.steel, HEX.steel, HEX.signal, HEX.steel], invertedColors: [HEX.steel],
          showValue: true, dataLabelPosition: "inBase", dataLabelColor: HEX.paper, dataLabelFormatCode: '0.0" N"', valAxisMinVal: 0, valAxisMaxVal: 30, valAxisMajorUnit: 10,
          showValAxisTitle: true, valAxisTitle: "Force per jaw (N)", layout,
        }));
        const pr = plotRect(cb, layout);
        limitLine(sl, pr, 30, V.t05_fmin, "13.3 N weakest position", { align: "left", labelW: 2.0 });
        limitLine(sl, pr, 30, 25.0, "25.0 N at a 70 mm grab", { align: "right" });
        // gear renders, before and after
        const sy = b.y + 3.4, sh = b.h - 3.4;
        mat(sl, b.x, sy, b.w, sh, "render_mat");
        [["v6_compound_original.png", "My v6 compound, 3:1", "gear set 157 g (CAD)"], ["v6r_compound.png", "Rebuilt v6r, 2:1", "gear set 96 g (CAD)"]].forEach(([f, t, sub], i) => {
          const x = b.x + 0.15 + i * (b.w / 2);
          renderFit(sl, f, x, sy + 0.12, 1.1, sh - 0.24, `gear_render_${i + 1}`);
          sl.addText(t, { x: x + 1.2, y: sy + 0.3, w: b.w / 2 - 1.4, h: 0.5, fontSize: 12, bold: true, fontFace: "Arial", color: C.text1, margin: 0, valign: "top", isTextBox: true });
          sl.addText(sub, { x: x + 1.2, y: sy + 0.85, w: b.w / 2 - 1.4, h: 0.4, fontSize: 11, color: C.text2, margin: 0, valign: "top", isTextBox: true });
        });
      },
      rail: [
        "Five soft tendon fingers.",
        "A clamp is simpler but stalls the servo.",
        "Module 1.5, 2:1 ratio, 36T gear rebuilt from my v6 gears.",
        "Gears 157 g to 96 g; 257 checks pass with conditions.",
        "Jeans at μ 0.3 need 17.7 N; jaws give 13.3–25 N.",
      ],
      fund: { eq: "σ = F_{t} / (b·m·Y);   N ≥ m(g + a) / (2μ)", sub: "Module 1: SF 0.35–0.41 at stall; module 1.5: teeth 2.0–2.5, 36T web 1.7. Jeans: 0.9 × 11.81 / (2 × 0.3) = 17.7 N per jaw." },
    });
  }

  // ================================================================ 12 · Camera and tube
  decision({
    n: 12, topic: "CAMERA AND TUBE", section: SECTION.a2, tags: ["CALCULATED", "SIMULATED"], active: 3,
    title: "The camera can't see the grasp at contact, and that's fine.",
    hero: (sl, b) => {
      mat(sl, b.x, b.y, b.w, b.h, "render_mat");
      const rh = 4.5, rx = b.x + 0.15, ry = b.y + 0.2;
      const rw = render(sl, "claw_v6_camera_bay.png", rx, ry, rh, "claw_render");
      const px = b.x + 1.85, pw = b.w - 2.0, ph = pw * 672 / 712;
      sl.addImage({ path: path.join(ASSETS, "c050_open_jaws_panel.png"), x: px, y: b.y + 1.0, w: pw, h: ph, altText: "Camera view at 140 mm hover, open jaws", objectName: "camera_view_plot" });
      caption(sl, "Camera view, 50 mm cut, 140 mm hover; green box = grasp zone. Render: v6 head (superseded).", px, b.y + 1.0 + ph + 0.05, pw, 0.45);
      callout(sl, rx + 0.9 * rw, ry + 0.107 * rh, px + 0.3, b.y + 0.45, "Camera bay");
    },
    rail: [
      "Long aluminium arm; camera sees the jaws.",
      "At contact, a plate hides the grasp spot.",
      "Cut 50 mm of tube, not 100 mm.",
      "Visible from 140 mm hover (was 172); saves ~33 g.",
      "Last ~14 cm is blind; add a hover correction.",
    ],
    fund: { eq: "D* = (k (H_{0} − c) − 93) / (1 − k),   k = 1 − 59.5/97", sub: "k = 0.387, H_{0} = 512 mm: c = 0 gives D* = 171 mm (ray-cast 172), c = 50 mm gives 140 mm. Saved 33 g assumes a 3 mm wall." },
  });

  // ================================================================ 13 · Distributed electronics
  pres.addSection({ title: SECTION.a3 });
  decision({
    n: 13, topic: "DISTRIBUTED ELECTRONICS", section: SECTION.a3, tags: ["CALCULATED", "SIMULATED"], active: 2,
    title: "One controller per winch removes long harnesses; a review priced sync.",
    planned: { head: "PLANNED — not yet run", text: "Four stations, 1 lb, 300 mm at 50 mm/s: pass if each cable is within 2 mm." },
    hero: (sl, b) => {
      const g = 0.12, cw = (b.w - g) / 2;
      [["14_gen1_cnc_shield_a4988.jpg", "GEN 1 · central", 0.5, 0.5], ["10_buck_converter_wiring.jpg", "GEN 2 · per winch", 0.5, 0.62]].forEach(([f, lab, fx, fy], i) => {
        const x = b.x + i * (cw + g);
        photo(sl, f, x, b.y, cw, b.h, `hero_photo_${i + 1}`, { fx, fy });
        sl.addText(lab, { fill: { color: C.background1 }, x: x + 0.1, y: b.y + b.h - 0.45, w: cw - 0.2, h: 0.32, fontSize: 11, bold: true, fontFace: "Arial", color: C.text1, valign: "middle", margin: 6, isTextBox: true, objectName: `photo_label_${i + 1}` });
      });
    },
    rail: [
      "July: one controller; synchronised motion came free.",
      "32 ft harnesses; skew becomes force on four cables.",
      "Host plans; stations run timed segments, own clocks.",
      "Control logic simulated only.",
      "Not yet run on four stations.",
    ],
    fund: { eq: "Δℓ = v·Δt;   F = k·Δℓ;   V = I·ρ·2L / A", sub: "50 mm/s × 50 ms = 2.5 mm; assumed 3 N/mm gives 7.5 N (upper bound). 16 AWG, 32 ft, 2 A (illustrative): 0.51 V drop (18 AWG: 0.82 V)." },
  });

  // ================================================================ 14 · The 1.14 V rail
  decision({
    n: 14, topic: "BRING-UP", section: SECTION.a3, tags: ["MEASURED"], active: 1,
    title: "A motor that wouldn't move taught me to measure before coding.",
    planned: { head: "PLANNED — not yet run", text: "Meter checklist on the as-built board: VDD, SLEEP, ENABLE and the buck output." },
    hero: (sl, b) => {
      const tw = 1.75, pw = b.w - tw - 0.12;
      photo(sl, "07_bench_wiring_a.jpg", b.x, b.y, pw, b.h, "hero_photo", { fx: 0.45, fy: 0.55 });
      const tx = b.x + pw + 0.12;
      sl.addShape(pres.shapes.RECTANGLE, { x: tx, y: b.y, w: tw, h: b.h, fill: { color: C.background2 }, line: { color: C.background2, width: 0.5 }, objectName: "stat_tile" });
      sl.addText("3.3 V", { x: tx + 0.15, y: b.y + 0.45, w: tw - 0.3, h: 0.55, fontSize: 30, bold: true, fontFace: "Arial", color: C.text1, margin: 0, valign: "middle", isTextBox: true });
      sl.addText("expected on the logic rail", { x: tx + 0.15, y: b.y + 1.02, w: tw - 0.3, h: 0.5, fontSize: 12, color: C.text2, margin: 0, valign: "top", isTextBox: true });
      sl.addText("1.14 V", { x: tx + 0.15, y: b.y + 2.0, w: tw - 0.3, h: 0.55, fontSize: 30, bold: true, fontFace: "Arial", color: C.accent1, margin: 0, valign: "middle", isTextBox: true });
      sl.addText("read on my meter (not logged)", { x: tx + 0.15, y: b.y + 2.57, w: tw - 0.3, h: 0.5, fontSize: 12, color: C.text2, margin: 0, valign: "top", isTextBox: true });
    },
    rail: [
      "First motion on the new station board.",
      "Pulses sent, shaft still; logic rail read 1.14 V.",
      "Solder 3.3 V; pull resistors; JP1; measure VDD.",
      "Motor moved after repair; Rev D layout net-checked, not built.",
      "As-built board still needs its meter checklist.",
    ],
    fund: { eq: "I = Vref / (8·R_{s}) = 0.85 V / 0.8 Ω = 1.06 A", sub: "Meter first: logic rail 1.14 V read against 3.3 V expected. The same habit on Oct 21 found the Vref pot topping out at 0.85 V." },
  });

  // ================================================================ 15 · Calibration
  decision({
    n: 15, topic: "CALIBRATION", section: SECTION.a3, tags: ["CALCULATED", "SIMULATED"], active: 2,
    title: "I stopped buying precision and moved the safety into margins.",
    hero: (sl, b) => {
      mat(sl, b.x, b.y, b.w, b.h, "render_mat");
      const pitch = 0.95, tg = 0.57, cols = 4, rows = 3;
      const gx = b.x + (b.w - ((cols - 1) * pitch + tg)) / 2, gy = b.y + 0.75;
      const cx = (i) => gx + tg / 2 + i * pitch, cy = (j) => gy + tg / 2 + j * pitch;
      // camera footprint over the two middle tags
      const fr = 1.0, fcx = (cx(1) + cx(2)) / 2, fcy = cy(1);
      sl.addShape(pres.shapes.OVAL, { x: fcx - fr, y: fcy - fr, w: 2 * fr, h: 2 * fr, fill: { color: C.background1, transparency: 100 }, line: { color: C.text2, width: 1.25, dashType: "dash" }, objectName: "camera_footprint" });
      for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
        const x = cx(i) - tg / 2, y = cy(j) - tg / 2;
        sl.addShape(pres.shapes.RECTANGLE, { x, y, w: tg, h: tg, fill: { color: C.text1 }, line: { color: C.text1, width: 0.5 }, objectName: `tag_${i}_${j}` });
        sl.addShape(pres.shapes.RECTANGLE, { x: x + 0.1, y: y + 0.1, w: tg - 0.2, h: tg - 0.2, fill: { color: C.background1 }, line: { color: C.background1, width: 0.5 }, objectName: `tag_in_${i}_${j}` });
        sl.addShape(pres.shapes.RECTANGLE, { x: x + 0.2, y: y + 0.2, w: tg - 0.4, h: tg - 0.4, fill: { color: C.text1 }, line: { color: C.text1, width: 0.5 }, objectName: `tag_core_${i}_${j}` });
      }
      // pitch dimension
      const dy = gy - 0.22;
      sl.addShape(pres.shapes.LINE, { x: cx(0), y: dy, w: pitch, h: 0, line: { color: C.text1, width: 1, beginArrowType: "triangle", endArrowType: "triangle" }, objectName: "pitch_dim" });
      sl.addText("250 mm pitch", { x: cx(0) + pitch + 0.1, y: dy - 0.14, w: 1.6, h: 0.28, fontSize: 12, bold: true, fontFace: "Arial", color: C.text1, margin: 0, valign: "middle", isTextBox: true });
      sl.addText("2 tags in view: 4.9 mrad;  4 tags: 1.3 mrad", { x: b.x + 0.25, y: gy + 2.62, w: b.w - 0.5, h: 0.28, fontSize: 12, bold: true, fontFace: "Arial", color: C.text1, margin: 0, valign: "middle", isTextBox: true });
      // big comparison
      sl.addText([{ text: "6.6 mm → ", options: { color: C.text1 } }, { text: "0.7 mm", options: { color: C.accent1 } }], { x: b.x + 0.25, y: b.y + 3.65, w: b.w - 0.5, h: 0.55, fontSize: 32, bold: true, fontFace: "Arial", margin: 0, valign: "middle", isTextBox: true, objectName: "big_number" });
      sl.addText("per-frame lever-arm error at 0.51 m: one tag vs four tags in view (two tags: 2.5 mm)", { x: b.x + 0.25, y: b.y + 4.2, w: b.w - 0.5, h: 0.5, fontSize: 12, color: C.text2, margin: 0, valign: "top", isTextBox: true });
    },
    rail: [
      "Absolute cable lengths from vision alone.",
      "One tag errs 6.6 mm/frame; cable σ stays above 12 mm.",
      "Margins carry safety; probe slack; drop the IMU.",
      "Simulated: 6/6 startups; 3 of 6 reach full trust.",
      "Claw tilts 13–21° near corners; all simulated.",
    ],
    fund: { eq: "δx = σ_{θ}·L;   σ_{N} = σ / √N", sub: "One tag: 12.9 mrad × 0.51 m = 6.6 mm. Four tags in view: 1.32 mrad × 0.51 m = 0.68 mm; two tags: 4.85 mrad = 2.5 mm." },
  });

  // ================================================================ 16 · Evidence table
  pres.addSection({ title: SECTION.close });
  s = addContent(SECTION.close, "16 Evidence so far");
  s.addText("EVIDENCE SO FAR", { placeholder: "eyebrow" });
  s.addText("Measured, calculated, simulated, planned: the test that decides the rest.", { placeholder: "title" });
  {
    const colW = (W - 2 * M) / 4;
    const head = (t) => ({ text: t, options: { bold: true, fontFace: "Arial", fontSize: 12, color: C.text1, fill: { color: C.background2 }, valign: "middle", border: [{ type: "none" }, { type: "none" }, { type: "none" }, { type: "none" }] } });
    const cell = (items) => ({
      text: items.map((t, i) => {
        const brk = i < items.length - 1;
        if (typeof t === "object") return { text: t.head, options: { bold: true, fontSize: 12, color: C.text2, breakLine: brk, paraSpaceBefore: 6, paraSpaceAfter: 4 } };
        return { text: kit.nb(t), options: { bullet: { indent: 14 }, breakLine: brk, paraSpaceAfter: 6 } };
      }),
      options: { fontSize: 14, color: C.text1, valign: "top", border: [{ type: "none" }, { type: "none" }, { pt: 0.75, color: HEX.fog }, { type: "none" }], margin: [8, 10, 8, 10] },
    });
    s.addTable([
      [head("MEASURED"), head("CALCULATED"), head("SIMULATED"), head("PLANNED, with pass limits")],
      [
        cell(["Vref pot maximum 0.79–0.85 V", "One motor on all four driver channels", "Buck output 5.00 V", "Logic rail 1.14 V (the fault)", { head: "Observed, not instrument-measured" }, "Fin test-fits on the motor (visual)", "18 V read at the supply vs 12 V label (re-measure)"]),
        cell(["Cable statics, 32 to 4.6 N", "Gear stress (Lewis)", "Fin efficiency, 74 % to 37 %", "Wire drop, 0.51 V", "Grip force required per jaw"]),
        cell(["Control system and sync", "Startup calibration", "Camera view vs tube length", "Jaw force, four-bar model"]),
        cell(["Hold test, vented shell: motor case below 60 °C", "Winch pull test (luggage scale), empty and full spool", "Station-mount pull test", "SolidWorks station study: SF ≥ 3 at 34 N, ≤ 0.5 mm", "1 lb, four stations, 300 mm at 50 mm/s: ≤ 2 mm per cable"]),
      ],
    ], { x: M, y: 2.0, w: W - 2 * M, colW: [colW, colW, colW, colW], rowH: [0.42, 3.15], fontFace: "Calibri", objectName: "evidence_table" });
    s.addShape(pres.shapes.RECTANGLE, { x: M, y: 5.8, w: W - 2 * M, h: 1.05, fill: { color: C.accent5 }, line: { color: C.accent1, width: 1.5 }, objectName: "first_test_card" });
    eyebrowLabel(s, "FIRST TEST", M + 0.25, 5.92, 3, C.text1);
    s.addText("Luggage-scale pull at 1.06 A, empty and full spool; under about 25 N points to a 3:1 reduction (decision open).", { x: M + 0.25, y: 6.17, w: W - 2 * M - 0.5, h: 0.32, fontSize: 15, color: C.text1, margin: 0, valign: "middle", isTextBox: true });
    s.addText("Also: confirm VDD = 3.3 V at the driver and measure the line diameter.", { x: M + 0.25, y: 6.5, w: W - 2 * M - 0.5, h: 0.28, fontSize: 13, color: C.text1, margin: 0, valign: "middle", isTextBox: true });
  }
  s.addNotes(notes(NOTES["16"]));

  // ================================================================ 17 · Deletions and lessons
  s = pres.addSlide({ masterName: "Dark Closing", sectionTitle: SECTION.close });
  slideNo += 1; ALL_SLIDES.push({ n: slideNo, label: "17 Deletions and lessons" });
  s.addText("WHAT I DELETED, WHAT I LEARNED", { placeholder: "eyebrow" });
  s.addText("My best decisions were deletions.", { placeholder: "title" });
  {
    eyebrowLabel(s, "DELETED", M, 2.55, 4, C.text2);
    ["The IMU", "Five fingers, now two jaws", "50 mm of tube", "The housing block, now an open frame (−560 g, CAD)", "The 5 lb reserve: a 1 lb gate first"].forEach((t, i) => {
      const y = 2.95 + i * 0.52;
      s.addText("−", { x: M, y, w: 0.3, h: 0.45, fontSize: 20, bold: true, fontFace: "Arial", color: C.text2, margin: 0, valign: "middle", isTextBox: true });
      s.addText(t, { x: M + 0.4, y, w: 5.6, h: 0.45, fontSize: 17, color: C.background1, margin: 0, valign: "middle", isTextBox: true });
    });
    eyebrowLabel(s, "THREE LESSONS", 7.1, 2.55, 4, C.text2);
    [["Measure before you trust a margin", "The 0.85 V Vref cap and the 1.14 V rail"], ["Print the coupon before the part", "The spool bore: Ø5.2 became Ø5.45"], ["Stall is the design case", "Gear stall and motor holding heat, not the average"]].forEach(([t, d], i) => {
      const y = 2.95 + i * 1.12;
      s.addText(String(i + 1).padStart(2, "0"), { x: 7.1, y, w: 0.8, h: 0.5, fontSize: 28, bold: true, fontFace: "Arial", color: C.accent1, margin: 0, valign: "top", isTextBox: true });
      s.addText(t, { x: 7.95, y, w: W - M - 7.95, h: 0.42, fontSize: 19, bold: true, fontFace: "Arial", color: C.background1, margin: 0, valign: "top", isTextBox: true });
      s.addText(d, { x: 7.95, y: y + 0.45, w: W - M - 7.95, h: 0.4, fontSize: 14, color: HEX.steelLight, margin: 0, valign: "top", isTextBox: true });
    });
    s.addText("With half the time again: buy pulleys and couplers sooner, and build one station to test before four.", { x: M, y: 6.25, w: 11.5, h: 0.4, fontSize: 15, color: HEX.steelLight, margin: 0, valign: "middle", isTextBox: true });
    s.addText("jasper_buntinx@tamu.edu", { x: M, y: H - 0.7, w: 6, h: 0.3, fontSize: 12, color: C.text2, margin: 0, isTextBox: true });
  }
  s.addNotes(notes(NOTES["17"]));

  // ================================================================ Backups
  pres.addSection({ title: SECTION.back });
  function backup(n, eyebrow, title, tagList, buildFn) {
    const sl = addContent(SECTION.back, `B${n} ${eyebrow}`);
    sl.addText(`BACKUP B${n} · ${eyebrow}`, { placeholder: "eyebrow" });
    sl.addText(title, { placeholder: "title" });
    if (tagList.length) tags(sl, tagList);
    buildFn(sl);
    sl.addNotes(notes(NOTES["B" + n]));
    BACKUPS.push({ n, title });
  }
  const statTile = (sl, x, y, w, h, big, lab, hot) => {
    sl.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: C.background2 }, line: { color: C.background2, width: 0.5 }, objectName: "stat_tile" });
    sl.addText(big, { x: x + 0.2, y: y + 0.08, w: w - 0.4, h: h * 0.5, fontSize: 26, bold: true, fontFace: "Arial", color: hot ? C.accent1 : C.text1, margin: 0, valign: "middle", isTextBox: true });
    sl.addText(lab, { x: x + 0.2, y: y + h * 0.55, w: w - 0.4, h: h * 0.4, fontSize: 12, color: C.text2, margin: 0, valign: "top", isTextBox: true });
  };

  // ---------------------------------------------------------------- B1 jaw kinematics
  backup(1, "JAW KINEMATICS", "Jaw force is lowest closed and over 3× higher near full open.", ["SIMULATED", "CALCULATED"], (sl) => {
    const gaps = [0.6, 10, 20, 40, 60, 70, 80, 85];
    const force = [13.3, 14.1, 15.0, 17.2, 21.1, 25.0, 33.4, 43.6];
    const box = { x: M, y: 1.95, w: 7.7, h: 3.3 };
    const layout = { x: 0.1, y: 0.05, w: 0.86, h: 0.7 };
    sl.addChart(pres.charts.SCATTER, [{ name: "Gap", values: gaps }, { name: "Force per jaw at 4.8 V (N)", values: force }], chartOpts({
      ...box, chartColors: [HEX.signal], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 8,
      valAxisMinVal: 0, valAxisMaxVal: 50, valAxisMajorUnit: 10, catAxisMinVal: 0, catAxisMaxVal: 90, catAxisMajorUnit: 10,
      showValAxisTitle: true, valAxisTitle: "Force per jaw (N)", showCatAxisTitle: true, catAxisTitle: "Jaw tip gap (mm)", layout,
    }));
    const pr = plotRect(box, layout);
    limitLine(sl, pr, 50, 17.7, "17.7 N: jeans, μ 0.3", { align: "left" });
    limitLine(sl, pr, 50, 8.9, "8.9 N: 1 lb, μ 0.3", { align: "left", below: true });
    caption(sl, "Near full open the four-bar nears toggle: the effective lever arm shrinks (59 mm at a 10 mm gap, 33 mm at 70 mm) and force rises. No toggle inside the stroke.", M, 5.3, 7.7, 0.5);
    statTile(sl, 8.7, 1.95, W - M - 8.7, 1.0, "76.5°", "jaw stroke from a 153° servo (2:1)");
    statTile(sl, 8.7, 3.1, W - M - 8.7, 1.0, "91.6 mm", "open gap, closed gap 0.000 mm");
    statTile(sl, 8.7, 4.25, W - M - 8.7, 1.0, "0.83 N·m", "jaw torque at 4.8 V stall");
    fundBox(sl, { eq: "F_{jaw} = τ_{jaw} / r_{eff};   τ_{jaw} = N·τ_{in}·η² / 2", sub: "τ_{jaw} = 2 × 0.922 N·m × 0.95² / 2 = 0.83 N·m. r_{eff} = 59, 48, 33 mm at 10, 40, 70 mm gap, so F = 14.1, 17.2, 25.0 N." }, M, 5.85, W - 2 * M, 1.0);
  });

  // ---------------------------------------------------------------- B2 control architecture
  backup(2, "CONTROL ARCHITECTURE", "The host plans; each station executes, and stop never disables.", ["SIMULATED"], (sl) => {
    // host
    sl.addShape(pres.shapes.RECTANGLE, { x: M, y: 2.05, w: 2.5, h: 2.35, fill: { color: C.text1 }, line: { color: C.text1, width: 0.5 }, objectName: "host_box" });
    sl.addText("HOST", { x: M + 0.25, y: 2.25, w: 2.0, h: 0.25, fontSize: 11, bold: true, fontFace: "Arial", charSpacing: 1.5, color: HEX.steelLight, margin: 0, isTextBox: true });
    sl.addText("Planner", { x: M + 0.25, y: 2.6, w: 2.0, h: 0.5, fontSize: 24, bold: true, fontFace: "Arial", color: C.background1, margin: 0, isTextBox: true });
    sl.addText("Plans the path and sends timed segments", { x: M + 0.25, y: 3.2, w: 2.0, h: 0.9, fontSize: 14, color: HEX.steelLight, valign: "top", margin: 0, isTextBox: true });
    sl.addShape(pres.shapes.LINE, { x: M + 2.5, y: 3.23, w: 1.15, h: 0, line: { color: C.text1, width: 1.5, endArrowType: "triangle" }, objectName: "arrow_segments" });
    sl.addText("timed\nsegments", { x: M + 2.55, y: 2.65, w: 1.05, h: 0.5, fontSize: 11, bold: true, fontFace: "Arial", color: C.text2, margin: 0, align: "center", isTextBox: true });
    // stations
    for (let i = 0; i < 4; i++) {
      const x = 4.4 + (i % 2) * 2.35, y = 2.05 + Math.floor(i / 2) * 1.3;
      sl.addShape(pres.shapes.RECTANGLE, { x, y, w: 2.15, h: 1.1, fill: { color: C.background2 }, line: { color: C.background2, width: 0.5 }, objectName: `station_${i + 1}` });
      eyebrowLabel(sl, `STATION ${i + 1}`, x + 0.2, y + 0.15, 1.8);
      sl.addText("Own clock", { x: x + 0.2, y: y + 0.4, w: 1.8, h: 0.3, fontSize: 15, bold: true, color: C.text1, margin: 0, isTextBox: true });
      sl.addText("feed-hold · lease", { x: x + 0.2, y: y + 0.7, w: 1.8, h: 0.28, fontSize: 12, color: C.text2, margin: 0, isTextBox: true });
    }
    // stats
    statTile(sl, 9.5, 2.05, W - M - 9.5, 1.1, "≈ 18 ms", "stop spread across stations (simulated)");
    statTile(sl, 9.5, 3.3, W - M - 9.5, 1.1, "10 / 10", "lossy motions completed at 2–5 % packet loss (sim)");
    // rules
    const cw = (W - 2 * M - 0.5) / 3;
    [["Feed-hold in path time", "All four stations ramp to zero along the same geometric path.", false], ["Lease", "No valid host message in time: the station holds and tells its peers.", false], ["Stop never disables", "Faults and pause hold torque. Only a confirmed disarm releases the load.", true]].forEach(([h, t, hot], i) => {
      const x = M + i * (cw + 0.25), y = 4.95;
      sl.addShape(pres.shapes.RECTANGLE, { x, y, w: cw, h: 1.6, fill: { color: hot ? C.accent5 : C.background2 }, line: { color: hot ? C.accent1 : C.background2, width: hot ? 1.5 : 0.5 }, objectName: `rule_card_${i + 1}` });
      sl.addText(h, { x: x + 0.25, y: y + 0.22, w: cw - 0.5, h: 0.4, fontSize: 18, bold: true, fontFace: "Arial", color: C.text1, margin: 0, isTextBox: true });
      sl.addText(t, { x: x + 0.25, y: y + 0.75, w: cw - 0.5, h: 1.0, fontSize: 15, color: C.text1, valign: "top", margin: 0, isTextBox: true });
    });
  });

  // ---------------------------------------------------------------- B3 Rev D board
  backup(3, "REV D STATION BOARD", "Rev D: soldered 3.3 V, driver boots disabled, no USB-buck fight.", ["PLANNED"], (sl) => {
    const ih = 4.9, iw = ih * 1939 / 1531;
    sl.addImage({ path: P("docs/electrical/station_revD_20261021/perfboard_layout.png"), x: M, y: 1.95, w: iw, h: ih, altText: "Rev D perfboard layout, component side", objectName: "perfboard_layout" });
    const at = (fx, fy) => [M + fx * iw, 1.95 + fy * ih];
    const lab = (fx, fy, lx, ly, t) => { const a = at(fx, fy), l = at(lx, ly); callout(sl, a[0], a[1], l[0], l[1], t, "left", 11); };
    lab(0.7066, 0.5356, 0.78, 0.625, "JP1 link");
    lab(0.2512, 0.5585, 0.1, 0.665, "R1 pull-up");
    lab(0.4796, 0.6205, 0.47, 0.7, "3V3 bus");
    const rx = M + iw + 0.4, rw = W - M - rx;
    eyebrowLabel(sl, "WHAT REV D CHANGED", rx, 1.95, rw);
    body(sl, ["3.3 V soldered, not jumpered.", "10 k pull resistors: the driver boots disabled.", "JP1 and diode D1: USB and the buck never fight.", "Net-checked: every hole has one net, every net is connected."], rx, 2.3, rw, 2.9, 15);
    plannedCard(sl, "Meter checklist on the as-built board: VDD, SLEEP, ENABLE, buck output.", rx, 5.9, rw, 0.95);
  });

  // ---------------------------------------------------------------- B4 floor-board attitude study
  backup(4, "FLOOR-BOARD ATTITUDE STUDY", "Floor board cuts tilt noise up to 10×; hanging tilt still 13–21°.", ["CALCULATED", "SIMULATED"], (sl) => {
    const lw = 5.9, lx = M, rx = M + lw + 0.33, rw = W - M - rx;
    eyebrowLabel(sl, "HANGING TILT AT GRID POINTS (°)", lx, 1.95, lw);
    const lb = { x: lx, y: 2.2, w: lw, h: 3.4 }, ll = { x: 0.1, y: 0.05, w: 0.88, h: 0.65 };
    sl.addChart(pres.charts.BAR, [
      { name: "CoM depth 0.196 m (recorded, stale)", labels: ["Median", "Largest, at corners"], values: [r1(V.t07_tilt_stale_med), r1(V.t07_tilt_stale_max)] },
      { name: "CoM depth 0.116 m (current estimate)", labels: ["Median", "Largest, at corners"], values: [r1(V.t07_tilt_est_med), r1(V.t07_tilt_est_max)] },
    ], chartOpts({
      ...lb, barDir: "col", barGapWidthPct: 60, barGrouping: "clustered", chartColors: [HEX.steel, HEX.signal], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0.0"°"',
      valAxisMinVal: 0, valAxisMaxVal: 25, valAxisMajorUnit: 5, showLegend: true, legendPos: "b", legendFontSize: 11, layout: ll,
    }));
    eyebrowLabel(sl, "TILT NOISE, ONE TAG, VS RANGE (mrad)", rx, 1.95, rw);
    const rb = { x: rx, y: 2.2, w: rw, h: 3.4 }, rl = { x: 0.11, y: 0.05, w: 0.85, h: 0.65 };
    sl.addChart(pres.charts.LINE, [{ name: "One 152 mm tag", labels: ["0.46 m", "0.60 m", "0.80 m", "1.00 m"], values: [r1(V.t08_sig_46), r1(V.t08_sig_60), r1(V.t08_sig_80), r1(V.t08_sig_100)] }], chartOpts({
      ...rb, chartColors: [HEX.signal], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 8, showValue: true, dataLabelPosition: "t", dataLabelFormatCode: "0.0",
      valAxisMinVal: 0, valAxisMaxVal: 60, valAxisMajorUnit: 10, showCatAxisTitle: true, catAxisTitle: "Camera range to the tag", layout: rl,
    }));
    limitLine(sl, plotRect(rb, rl), 60, 4.85, "Board: 2 tags 4.9, 4 tags 1.3 mrad", { align: "right", labelW: 2.9 });
    limitLine(sl, plotRect(rb, rl), 60, V.t08_sig_4, "");
    fundBox(sl, { eq: "θ ≈ M_{v} / (W·L);   δx = σ_{θ}·L", sub: "Corner tilt grows 1.61× when L falls from 0.196 to 0.116 m; 83 % then 92 % of grid points exceed 5°. Four tags in view: 0.68 mm vs 6.6 mm for one tag." }, M, 5.8, W - 2 * M, 1.05);
  });

  // ---------------------------------------------------------------- B5 thermal network
  backup(5, "THERMAL NETWORK", "The fin is a parallel heat path; PETG alone can't carry it.", ["CALCULATED", "PLANNED"], (sl) => {
    const box = (x, y, w, h, t1, t2, hot) => {
      sl.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: hot ? C.accent5 : C.background2 }, line: { color: hot ? C.accent1 : C.background2, width: hot ? 1.5 : 0.5 }, objectName: `node_${t1}` });
      eyebrowLabel(sl, t1, x + 0.15, y + 0.12, w - 0.3);
      sl.addText(t2, { x: x + 0.15, y: y + 0.4, w: w - 0.3, h: h - 0.5, fontSize: 14, color: C.text1, valign: "top", margin: 0, isTextBox: true });
    };
    const ny = 2.1, nh = 1.15;
    box(M, ny, 2.1, nh, "MOTOR CASE", "2.0 W of coil heat", true);
    box(3.5, ny, 2.1, nh, "SHELL INTERIOR", "+ 1.5 W electronics");
    box(6.4, ny, 2.0, nh, "ROOM AIR", "23 °C near the ceiling");
    const arrow = (x1, x2, y, lab) => {
      sl.addShape(pres.shapes.LINE, { x: x1, y, w: x2 - x1, h: 0, line: { color: C.text1, width: 1.5 }, objectName: `r_${lab}` });
      sl.addText(lab, { x: x1 - 0.1, y: y - 0.55, w: x2 - x1 + 0.2, h: 0.5, fontSize: 12, bold: true, fontFace: "Arial", color: C.text1, align: "center", valign: "bottom", margin: 0, isTextBox: true });
    };
    arrow(M + 2.1, 3.5, ny + nh / 2, "12 K/W");
    arrow(5.6, 6.4, ny + nh / 2, "3.5 K/W sealed");
    // fin path under the shell
    const fy = 4.05;
    sl.addShape(pres.shapes.LINE, { x: M + 1.05, y: ny + nh, w: 0, h: fy - ny - nh, line: { color: C.accent1, width: 2.5 }, objectName: "fin_down" });
    sl.addShape(pres.shapes.LINE, { x: M + 1.05, y: fy, w: 6.4 + 1.0 - M - 1.05, h: 0, line: { color: C.accent1, width: 2.5 }, objectName: "fin_across" });
    sl.addShape(pres.shapes.LINE, { x: 7.4, y: fy, w: 0, h: -(fy - ny - nh), flipV: true, line: { color: C.accent1, width: 2.5, endArrowType: "triangle" }, objectName: "fin_up" });
    sl.addText("Aluminium fin: 22.1 K/W as built, 10.9 K/W as drawn", { x: 2.0, y: fy + 0.08, w: 6.2, h: 0.3, fontSize: 13, bold: true, fontFace: "Arial", color: C.text1, margin: 0, isTextBox: true });
    sl.addText("Sealed shell, 1.06 A: 64 °C with no fin, 46 °C with the as-built fin, 40 °C with the drawn 1/8 in fin.", { x: M, y: fy + 0.55, w: 7.8, h: 0.6, fontSize: 14, color: C.text1, valign: "top", margin: 0, isTextBox: true });
    // right: material comparison
    const tx = 9.0, tw = W - M - tx;
    eyebrowLabel(sl, "PETG VS ALUMINIUM", tx, 2.1, tw);
    const hc = (t, al) => ({ text: t, options: { bold: true, fontFace: "Arial", fontSize: 12, color: C.text1, fill: { color: C.background2 }, align: al || "left" } });
    const rc = (t, al) => ({ text: t, options: { fontSize: 13, color: C.text1, align: al || "right", border: [{ type: "none" }, { type: "none" }, { pt: 0.75, color: HEX.fog }, { type: "none" }] } });
    sl.addTable([
      [hc(""), hc("Aluminium", "right"), hc("PETG", "right")],
      [rc("k, W/m·K", "left"), rc("160"), rc("0.2")],
      [rc("Flange path, K/W", "left"), rc("0.011"), rc("14.0")],
      [rc("Spread, mm", "left"), rc("74"), rc("2.6")],
    ], { x: tx, y: 2.45, w: tw, colW: [1.5, 1.2, tw - 2.7], rowH: 0.36, fontFace: "Calibri", objectName: "material_table" });
    plannedCard(sl, "Fin FEA after the SolidWorks study; the hold test replaces the lumped model.", tx, 4.2, tw, 1.0);
    fundBox(sl, { eq: "P_{m} = (T_{m} − T_{room}) / R_{fin} + (T_{m} − T_{shell}) / R_{ma}", sub: "Equal geometry: √(160 / 0.2) = 28×; spreading lengths are for a 0.48 mm sheet. Flange path, 5 mm PETG vs 3.2 mm aluminium: 1260× = 800× from k × 1.6× from thickness." }, M, 5.55, W - 2 * M, 1.3);
  });

  // ---------------------------------------------------------------- B6 v7 open-frame gearbox
  backup(6, "V7 OPEN-FRAME GEARBOX", "Open-frame v7 gearbox holds SF of about 2 or better at stall.", ["CALCULATED", "SIMULATED"], (sl) => {
    mat(sl, M, 1.95, 2.5, 3.65, "render_mat");
    renderFit(sl, "gripper_v7.png", M + 0.2, 2.1, 2.1, 3.35, "gripper_v7_render");
    const cb = { x: 3.4, y: 1.95, w: 5.7, h: 3.65 }, cl = { x: 0.1, y: 0.05, w: 0.88, h: 0.68 };
    const cat = ["Pinion 18T", "Gear 36T", "Sync gear 24T"];
    sl.addChart(pres.charts.BAR, [
      { name: "4.8 V stall", labels: cat, values: [V.t04_v7_sf_pin48, V.t04_v7_sf_big48, V.t04_v7_sf_sync48].map((x) => Math.round(x * 100) / 100) },
      { name: "6.0 V stall", labels: cat, values: [V.t04_v7_sf_pin60, V.t04_v7_sf_big60, V.t04_v7_sf_sync60].map((x) => Math.round(x * 100) / 100) },
    ], chartOpts({
      ...cb, barDir: "col", barGapWidthPct: 50, barGrouping: "clustered", chartColors: [HEX.steel, HEX.signal], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00",
      valAxisMinVal: 0, valAxisMaxVal: 3.5, valAxisMajorUnit: 0.5, valAxisLabelFormatCode: "0.0", showValAxisTitle: true, valAxisTitle: "Safety factor; dashed line = 2.0", showLegend: true, legendPos: "b", layout: cl,
    }));
    limitLine(sl, plotRect(cb, cl), 3.5, 2.0, "", { align: "left" });
    const fx = 9.4, fw = W - M - fx;
    eyebrowLabel(sl, "VERIFIED (REV 2)", fx, 1.95, fw);
    body(sl, ["Frame 143.5 g (limit 150 g).", "Printed total 333 g; head 481 g.", "72 checks pass; no interference over the sweep.", "Open: servo ear pitch 47.0 vs 48.3 mm."], fx, 2.3, fw, 3.2, 14);
    fundBox(sl, { eq: "SF = σ_{allow} / σ;   σ = F_{t} / (b·m·Y)", sub: "σ_{allow} = 22.5 MPa. At 6 V stall F_{t} = 79.9 N: pinion 11.0 MPa, SF 2.05. Sync gear, one jaw takes all: F_{t} = 113.9 N, SF 1.997." }, M, 5.8, W - 2 * M, 1.05);
  });

  // ---------------------------------------------------------------- B7 safety
  {
    const { FiPower, FiAnchor, FiUserX, FiBatteryCharging } = require("react-icons/fi");
    const icons = [await iconPng(FiPower, HEX.ink), await iconPng(FiAnchor, HEX.ink), await iconPng(FiUserX, HEX.ink), await iconPng(FiBatteryCharging, HEX.ink)];
    backup(7, "SAFETY", "Safety: one hard stop, anchors in studs, nobody underneath.", [], (sl) => {
      const cw = (W - 2 * M - 0.75) / 4;
      [["One hard stop", "The switched power strip is the only stop. Faults and pause hold torque."], ["Stud anchors", "Designed to screw into wall studs; screw pattern vs stud width and slide-in retention are still open. Line load is mostly pull-out and prying, plus some shear."],
        ["Nobody under it", "Nobody stands under the robot while it moves."], ["Balance charging", "Charge the 2S LiPo with a matched balance charger, pack off the robot."]].forEach(([h, t], i) => {
        const x = M + i * (cw + 0.25), y = 2.1, ch = 3.7, hot = i === 0;
        sl.addShape(pres.shapes.RECTANGLE, { x, y, w: cw, h: ch, fill: { color: hot ? C.accent5 : C.background2 }, line: { color: hot ? C.accent1 : C.background2, width: hot ? 1.5 : 0.5 }, objectName: `safety_card_${i + 1}` });
        sl.addImage({ data: icons[i], x: x + 0.3, y: y + 0.3, w: 0.7, h: 0.7, altText: h, objectName: `safety_icon_${i + 1}` });
        sl.addText(h, { x: x + 0.3, y: y + 1.25, w: cw - 0.6, h: 0.45, fontSize: 19, bold: true, fontFace: "Arial", color: C.text1, margin: 0, isTextBox: true });
        sl.addText(t, { x: x + 0.3, y: y + 1.8, w: cw - 0.6, h: 1.8, fontSize: 14, color: C.text1, valign: "top", margin: 0, isTextBox: true });
      });
      sl.addText("No safety-rated function is claimed (ISO 13849 and IEC 61508 are not claimed).", { x: M, y: 6.05, w: W - 2 * M, h: 0.4, fontSize: 14, color: C.text2, margin: 0, valign: "middle", isTextBox: true });
    });
  }

  await finish();
}

async function finish() {
  await pres.writeFile({ fileName: OUT });
  if (APPLY_THEME) {
    const { applyTheme } = require(APPLY_THEME);
    await applyTheme(OUT, THEME);
  } else {
    console.warn("APPLY_THEME not set: scheme colours fall back to Office defaults");
  }
  console.log("wrote", path.relative(ROOT, OUT), `(${slideNo} slides)`);
  if (SOFFICE_PY) {
    const r = spawnSync("python3", [SOFFICE_PY, "--headless", "--convert-to", "pdf", "--outdir", OUT_DIR, OUT], { encoding: "utf8" });
    if (r.status !== 0) console.warn("PDF export failed:", r.stderr || r.stdout);
    else console.log("wrote", path.relative(ROOT, OUT.replace(/\.pptx$/, ".pdf")));
  }
  // word-count report for the rail lines
  let bad = 0;
  DECISIONS.forEach((d) => {
    const counts = d.rail.map((t) => t.split(/\s+/).length);
    if (counts.some((c) => c > 12)) { bad++; console.warn(`slide ${d.n}: rail line over 12 words`, counts); }
    const total = counts.reduce((a, b) => a + b, 0);
    console.log(`slide ${d.n}: rail words ${total} (${counts.join("/")})  title words ${d.title.split(/\s+/).length}`);
  });
  if (bad) process.exitCode = 1;
}

build().catch((e) => { console.error(e); process.exit(1); });
