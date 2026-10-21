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
// values used straight from the JSON (charts)
const r1 = (x) => Math.round(x * 10) / 10;

// ------------------------------------------------------------------ small helpers
const SECTION = { open: "Open", a1: "Act 1 · Physics sets the limits", a2: "Act 2 · Making it buildable", a3: "Act 3 · Electronics and debugging", close: "Close", back: "Backups" };
const DECISIONS = [];   // collected for the word-count report
const ALL_SLIDES = [];  // {n, label, notes}
let slideNo = 0;

function addContent(section, label) {
  const s = pres.addSlide({ masterName: "Content", sectionTitle: section });
  slideNo += 1;
  ALL_SLIDES.push({ n: slideNo, label });
  return s;
}

/** Speaker notes: the sentence to say, the numbers, likely question(s), need-from-Jasper, sources. */
function notes(o) {
  const out = [];
  out.push("SAY: " + o.say);
  if (o.numbers) out.push("NUMBERS: " + o.numbers);
  (o.qa || []).forEach(([q, a], i) => out.push(`LIKELY QUESTION${o.qa.length > 1 ? " " + (i + 1) : ""}: ${q}\nANSWER: ${a}`));
  if (o.check) out.push("CHECK BEFORE SAYING: " + o.check);
  if (o.need) out.push("NEED FROM JASPER: " + o.need);
  if (o.src) out.push("SOURCE: " + o.src);
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
  s.addNotes(notes(cfg.notes));
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
  await sharp(c050).extract({ left: 22, top: 92, width: 712, height: 690 }).toFile(c050Panel);

  // ================================================================ 1 · Title
  pres.addSection({ title: SECTION.open });
  let s = pres.addSlide({ masterName: "Dark Title", sectionTitle: SECTION.open });
  slideNo += 1; ALL_SLIDES.push({ n: 1, label: "Title" });
  s.addText("RoomCleaner", { placeholder: "title" });
  s.addText("A four-cable ceiling robot that picks laundry off the floor", { placeholder: "subtitle" });
  s.addText("Jasper Buntinx · Technical presentation · Oct 27, 2026", { placeholder: "byline" });
  photo(s, "13_gen1_station_lifting_test_weight.jpg", W * 0.45, 0, W * 0.55, H, "hero_photo", { fx: 0.5, fy: 0.5 });
  s.addNotes(notes({
    say: "I set out to build a ceiling robot that picks laundry off my floor; every time a measurement disagreed with my plan I changed the design, and every change traces back to a first-principles equation.",
    numbers: "Four wall winch stations, one claw on four cables. Target payload 0.9 kg of jeans (provisional screening reference). About 30 minutes of content, 12 decision slides (4 to 15), 7 backups.",
    qa: [["Give me the 30-second version.", "Four wall-mounted winch stations hold a claw on four cables. The claw descends onto the laundry, closes its jaws with one servo, carries the load and releases it over a hamper. I will show twelve decisions where a calculation or a measurement forced me to change the plan, including the ones that did not work out."]],
    need: "Confirm the title wording and the panel date (Tue Oct 27). Photo 13 is the gen-1 station lifting the test weight (no weight, duration or result is recorded, so the slide makes no claim about it).",
    src: "docs/presentation/DECK_STORYLINE.md slide 1; photo 13.",
  }));

  // ================================================================ 2 · What I built
  s = addContent(SECTION.open, "2 What I built");
  s.addText("WHAT I BUILT · HOW I WORKED", { placeholder: "eyebrow" });
  s.addText("Solo build: four winch stations, a camera claw, and the software.", { placeholder: "title" });
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
    const cy = 4.65, ch = 1.75, cw = 3.55;
    [["BOUGHT", "A4988 driver, ESP32, DROK buck, MG996R servo.", false], ["DESIGNED, PRINTED, MACHINED, WIRED BY ME", "Everything else.", true]].forEach(([k, v, mine], i) => {
      const x = M + i * (cw + 0.25);
      s.addShape(pres.shapes.RECTANGLE, { x, y: cy, w: cw, h: ch, fill: { color: mine ? C.accent5 : C.background2 }, line: { color: mine ? C.accent1 : C.background2, width: mine ? 1.5 : 0.75 }, objectName: `card_${i + 1}` });
      eyebrowLabel(s, k, x + 0.25, cy + 0.25, cw - 0.5, mine ? C.text1 : C.text2);
      s.addText(v, { x: x + 0.25, y: cy + 0.75, w: cw - 0.5, h: ch - 0.95, fontSize: 18, color: C.text1, valign: "top", margin: 0, isTextBox: true });
    });
    // evidence legend
    const lx = 8.55, lw = W - M - lx;
    eyebrowLabel(s, "HOW TO READ THE TAGS", lx, cy + 0.02, lw);
    [["MEASURED", "On hardware, with an instrument"], ["CALCULATED", "Hand calculation, stated inputs"], ["SIMULATED", "Run in a model or simulator"], ["PLANNED", "Not done yet"]].forEach(([k, v], i) => {
      const y = cy + 0.4 + i * 0.4;
      tag(s, k, lx, y, 1.45);
      s.addText(v, { x: lx + 1.65, y: y - 0.02, w: lw - 1.65, h: 0.32, fontSize: 13, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
    });
  }
  s.addNotes(notes({
    say: "This is a solo build over about three months: I bought a few modules and designed, printed, machined and wired everything else.",
    numbers: "Jul 16 first commit (simulator, BOM, first CAD); Aug gen-1 printed plate and bench; Oct 7 SolidWorks gen-2 station; Oct 20 gripper v6; Oct 27 panel. Purchased: A4988 driver, ESP32, DROK buck, MG996R servo. Tags: MEASURED = instrument on hardware, CALCULATED = hand calculation, SIMULATED = ran in a model, PLANNED = not done yet.",
    qa: [["What did you actually do yourself?", "I drew the parts, printed them (PETG structural, TPU 95A fingers), sheared and drilled the aluminium fins on a manual mill, wired the bench and perfboard electronics, and wrote the control logic. The purchased modules are the driver, the ESP32, the buck converter and the servo."]],
    need: "Confirm the true start date (git says Jul 16; the older outline said Aug 6) and the printer and filament used for fit-critical parts (K1 or K1 Max, brand).",
    src: "DECK_STORYLINE.md slide 2; DECISION_STORIES.md section 4 item 1 and Q20.",
  }));

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
    const cards = [["0.9 kg", "Payload of jeans, plus 2 m/s² acceleration", true], ["≤ 450 g", "Claw mass budget", false], ["4 × studs", "Winch stations screwed into wall studs", false],
      ["1 switch", "The switched power strip is the only kill switch", false], ["0 people", "Nobody under the robot while it moves", false]];
    const x0 = 5.6, w0 = W - M - x0, ch = 0.86, gap = 0.14;
    cards.forEach(([big, lab, hot], i) => {
      const y = 2.0 + i * (ch + gap);
      s.addShape(pres.shapes.RECTANGLE, { x: x0, y, w: w0, h: ch, fill: { color: C.background2 }, line: { color: C.background2, width: 0.5 }, objectName: `req_card_${i + 1}` });
      s.addText(big, { x: x0 + 0.25, y, w: 2.3, h: ch, fontSize: 28, bold: true, fontFace: "Arial", color: hot ? C.accent1 : C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: `req_big_${i + 1}` });
      s.addText(lab, { x: x0 + 2.65, y, w: w0 - 2.85, h: ch, fontSize: 16, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: `req_label_${i + 1}` });
    });
  }
  s.addNotes(notes({
    say: "Done means a pair of jeans, about 0.9 kg, goes from anywhere on the floor into the hamper with nobody touching it.",
    numbers: "Payload 0.9 kg (provisional screening reference for jeans) plus 2 m/s² vertical acceleration; first test load 1 lb (0.454 kg). Claw mass budget 0.45 kg (requirement R7; the printed claw is estimated at 1.05 to 1.25 kg and has not been weighed). Four stations screwed into studs. The switched power strip is the only stop (decision D21; no safety-rated function is claimed). Nobody under the robot.",
    qa: [["Why 0.9 kg?", "It is a provisional screening reference for a pair of jeans, not a measured garment; the first physical test load is 1 lb. Weighing a representative pair is on my list."]],
    need: "Weigh a representative pair of jeans. Decide which claw mass you want to defend: the 450 g requirement against the unweighed 1.05 to 1.25 kg estimate (slide 5 depends on it).",
    src: "REQUIREMENTS.md R1, R7; DECISIONS.md D21; FUNDAMENTALS.md section 5 and the note on the 0.45 kg input risk.",
  }));

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
      title: "Cable angle, not payload, sets the limits; walls bind before the ceiling.",
      hero: (sl) => {
        sl.addChart(pres.charts.LINE, [
          { name: "Static: 1 lb + 0.45 kg claw", labels: depths.map((d) => d.toFixed(2)), values: Tst },
          { name: "With +2 m/s²", labels: depths.map((d) => d.toFixed(2)), values: Tdy },
        ], chartOpts({
          ...box, chartColors: [HEX.signal, HEX.steel], lineSize: 3, lineDataSymbol: "none", lineSmooth: false,
          valAxisMinVal: 0, valAxisMaxVal: 40, valAxisMajorUnit: 10, catAxisLabelFrequency: 3,
          showValAxisTitle: true, valAxisTitle: "Tension per cable (N)", showCatAxisTitle: true, catAxisTitle: "Depth below the anchors (m)",
          showLegend: true, legendPos: "b", layout,
        }));
        limitLine(sl, plotRect(box, layout), 40, V.t01_f_use, "11.9 N winch design force", { color: HEX.ink });
      },
      rail: [
        "Use the whole room.",
        "Tension: 32 N at 0.15 m depth, 8.3 N at 0.6 m.",
        "Keep a 0.4 m ceiling margin plus a wall margin.",
        "At task heights, corners bind: 1.1 × total weight.",
        "The claw's own mass counts exactly like payload.",
      ],
      fund: { eq: "T = W / (4 sin φ),  sin φ = d / √(d² + D_h²)", sub: "W = 8.86 N (1 lb + 0.45 kg claw), D_h = 2.17 m: T = 32.1 N at d = 0.15 m, 8.3 N at d = 0.60 m." },
      notes: {
        say: "Cable tension scales as one over the sine of the cable angle, so the room's limits come from cable geometry and the claw's own weight, not from the payload.",
        numbers: "Equal share, claw centred: W = (0.454 + 0.45) kg x 9.81 = 8.86 N; D_h = 2.17 m. T = 32.1 / 16.2 / 8.3 / 4.6 N per cable at 0.15 / 0.30 / 0.60 / 1.20 m below the anchors; with +2 m/s² 38.6 / 19.4 / 10.0 / 5.5 N. Winch design force 11.9 N (17.9 N running at a full spool, divided by a 1.5 skip margin, slide 5). Shallowest centred depth the winches can hold: 0.27 m static, 0.33 m with +2 m/s², 0.50 m with the 1.5 margin. Whole-room worst case (best split by linear program, 0.2 m wall margin, 1.06 A, 1.5 margin): largest tension 1.10 x total weight at the highest task pose (0.99 m below the anchors), holding 1.10 kg total.",
        qa: [["What about off-centre?", "The four-cable split is statically indeterminate (four cables, three force equations), so I find the best split by a linear program that minimises the largest tension. The worst spot is high against the middle of a long wall; the equal-share table is a lower bound for any pose off the centre."],
             ["Why a 0.4 m ceiling margin if the corner binds?", "Tension doubles each time the depth halves, so the planner never lets the claw closer than 0.4 m to the anchors; at that limit the same linear program only allows 0.50 kg total (2.42 x weight), so the margin is a floor, not a comfortable value."]],
        check: "Say 'at task heights' when you say the corner binds. At the 0.4 m ceiling limit the capacity is lower (2.42 x weight, 0.50 kg), so 'the walls bind before the ceiling' only holds for task poses (highest task pose 0.99 m below the anchors).",
        need: "A weighed claw mass: every capacity number uses the 0.45 kg budget, which has not been weighed.",
        src: "FUNDAMENTALS.md section 1; docs/decisions/WINCH_CAPACITY_20261021.md.",
      },
    });
  }

  // ================================================================ 5 · Motor, driver, spool
  {
    const cats = [["Ø15", "t02_c15_maxclaw", "t02_c15_fuse"], ["Ø12", "t02_c12_maxclaw", "t02_c12_fuse"], ["Ø10", "t02_c10_maxclaw", "t02_c10_fuse"], ["Ø8", "t02_c8_maxclaw", "t02_c8_fuse"]];
    const labels = cats.map(([d, , f]) => `${d} mm\n${V[f].toFixed(1)} N`);
    const vals = cats.map(([, m]) => Math.round(V[m]));
    decision({
      n: 5, topic: "DRIVE", section: SECTION.a1, tags: ["MEASURED", "CALCULATED"], active: 1,
      title: "The driver, not the motor, capped my pull; geometry buys it back.",
      planned: { text: "Luggage-scale pull at 1.06 A, empty and full spool; replaces the assumed 0.7 running-torque factor." },
      hero: (sl, b) => {
        sl.addText("0.85 V → 1.06 A", { x: b.x, y: b.y - 0.02, w: b.w, h: 0.62, fontSize: 38, bold: true, fontFace: "Arial", color: C.accent1, margin: 0, valign: "middle", isTextBox: true, objectName: "big_number" });
        sl.addText("Vref cap on my A4988 boards, and the current it allows", { x: b.x, y: b.y + 0.6, w: b.w, h: 0.26, fontSize: 12, color: C.text2, margin: 0, valign: "top", isTextBox: true });
        const cb = { x: b.x, y: b.y + 0.95, w: b.w, h: b.h - 0.95 };
        const layout = { x: 0.13, y: 0.1, w: 0.84, h: 0.56 };
        sl.addChart(pres.charts.BAR, [{ name: "Largest claw that still lifts 0.9 kg jeans (g)", labels, values: vals }], chartOpts({
          ...cb, barDir: "col", barGapWidthPct: 55, chartColors: [HEX.steel, HEX.steel, HEX.signal, HEX.steel], invertedColors: [HEX.steel],
          showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '#,##0" g"', valAxisMinVal: 0, valAxisMaxVal: 1250, valAxisMajorUnit: 250,
          valAxisLabelFormatCode: "#,##0", showValAxisTitle: true, valAxisTitle: "Largest claw (g)", showCatAxisTitle: true, catAxisTitle: "Spool core and design force", layout,
        }));
        const pr = plotRect(cb, layout);
        // printed-claw estimate band 1,050 to 1,250 g and the 450 g budget
        const yTop = pr.y, yBand = pr.y + pr.h * (1 - 1050 / 1250);
        sl.addShape(pres.shapes.RECTANGLE, { x: pr.x, y: yTop, w: pr.w, h: yBand - yTop, fill: { color: C.background2 }, line: { color: C.text2, width: 1, dashType: "dash" }, objectName: "claw_estimate_band" });
        sl.addText("Printed claw estimate 1,050–1,250 g (unweighed)", { x: pr.x + 0.1, y: yTop, w: pr.w - 0.2, h: yBand - yTop, fontSize: 11, bold: true, fontFace: "Arial", color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "claw_estimate_label" });
        limitLine(sl, pr, 1250, 450, "450 g budget", { align: "left" });
      },
      rail: [
        "Raise drive current from 1.0 to 1.35 A for more pull.",
        "Vref pot maxes at 0.85 V: current caps at 1.06 A.",
        "Run at the cap; recover pull with a smaller spool core.",
        "Winches hold about 1.1 kg; claw plus jeans is about 2 kg.",
        "The 0.7 running-torque factor is assumed; a pull test decides.",
      ],
      fund: { eq: "I = Vref / (8·R_s) = 0.85 V / 0.8 Ω = 1.06 A", sub: "T = τ / r: τ_run = 0.7 × 0.255 N·m = 0.179 N·m → 23.8 N at r = 7.5 mm, 17.9 N at a full spool (r = 10 mm)." },
      notes: {
        say: "My own numbers told me my claw outgrew my winches: the driver board caps the current at 1.06 A, so I am buying the pull back with geometry instead of hacking the driver.",
        numbers: "Vref pot maximum 0.85 V (MEASURED on the red R100 boards, 3.3 V logic; an earlier entry says 0.79 V, which gives 0.99 A, so there is a 7 % spread). I = Vref / (8 Rs) = 0.85 / 0.8 = 1.06 A. Holding torque 0.36 N·m x 1.0625 / 1.5 = 0.255 N·m; running torque 0.7 x holding = 0.179 N·m (the 0.7 is assumed). Pull T = tau / r: 23.8 N at the 7.5 mm core, 17.9 N at a full 10 mm spool; design force (divided by 1.5) 15.9 N and 11.9 N; snag case 34 N. Largest claw that still lifts 0.9 kg of jeans at the highest task pose: 202 g (Ø15 core, 1.10 kg held), 397 g (Ø12), 478 g (Ø10, +25 %), 570 g (Ø8, which fails the 20:1 bend ratio and the tie-off). Needed: 0.45 kg claw + 0.9 kg = 1.35 kg, which is 1.22 x what the Ø15 spool can hold. Printed claw estimate 1.05 to 1.25 kg (unweighed) gives 2.0 to 2.2 kg with jeans. A 3:1 reduction at each winch buys about 2.7 x (2.98 to 3.09 kg held at a 0.2 m wall margin).",
        qa: [["Why not raise Vref or run 5 V logic?", "I do not want to modify the driver, and a 3.3 V GPIO cannot guarantee a HIGH into a 5 V-logic input. So I run at the board maximum and recover pull mechanically: T = tau / r, so a smaller core gives more tension."],
             ["Is the 0.7 running-torque factor right?", "It is assumed (an earlier table used 0.5). A 15-minute luggage-scale pull test at 1.06 A, empty and full spool, replaces it with a number. If the full-spool pull is under about 25 N, which is likely, the memo recommends a 3:1 reduction for gen 3 and a lighter payload for the demo."]],
        check: "Do not quote the old '43 N', '34 N per cable' or '750 g claw budget' (D29/D30): they used holding torque, not running pull. Three different things are called tension: running pull (23.8 / 17.9 N), derated design value (11.9 N), snag load (34 N).",
        need: "Decision D31: 3:1 reduction, Ø10 core with a lighter claw, or a lighter payload for the demo. The pull-test readings. A weighed claw.",
        src: "FUNDAMENTALS.md section 2; docs/decisions/WINCH_CAPACITY_20261021.md.",
      },
    });
  }

  // ================================================================ 6 · Heat
  {
    const box = { x: GRID.LX, y: GRID.TOP, w: GRID.LW, h: GRID.BOT - GRID.TOP - GRID.PLANNED_H - 0.15 };
    const layout = { x: 0.13, y: 0.05, w: 0.84, h: 0.62 };
    const f0 = (k) => Math.round(V[k]);
    decision({
      n: 6, topic: "HEAT", section: SECTION.a1, tags: ["CALCULATED"], active: 3,
      title: "Sealing the station made the motor mount its hottest, most loaded joint.",
      planned: { text: "Hold test at 1.06 A with thermometers on the motor case, fin and PETG tab; pass limit below 60 °C." },
      hero: (sl) => {
        const cat = ["Open air", "Vented shell", "Sealed shell"];
        sl.addChart(pres.charts.BAR, [
          { name: "No fin", labels: cat, values: [f0("t03_T_open_no"), f0("t03_T_vented_no"), f0("t03_T_sealed_no")] },
          { name: "As-built fin, 0.019 in", labels: cat, values: [f0("t03_T_open_asbuilt"), f0("t03_T_vented_asbuilt"), f0("t03_T_sealed_asbuilt")] },
          { name: "Drawn fin, 1/8 in", labels: cat, values: [f0("t03_T_open_design"), f0("t03_T_vented_design"), f0("t03_T_sealed_design")] },
        ], chartOpts({
          ...box, barDir: "col", barGapWidthPct: 45, barGrouping: "clustered", chartColors: [HEX.steel, HEX.signal, HEX.steelLight],
          showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0", dataLabelFontSize: 11, valAxisMinVal: 0, valAxisMaxVal: 70, valAxisMajorUnit: 10,
          showValAxisTitle: true, valAxisTitle: "Motor case temperature (°C)", showLegend: true, legendPos: "b", legendFontSize: 11, layout,
        }));
        limitLine(sl, plotRect(box, layout), 70, 60, "60 °C target", { align: "left" });
      },
      rail: [
        "A clean, closed printed shell around each winch.",
        "A holding stepper dissipates I²R; PETG conducts 1/800 as well as aluminium.",
        "Vents plus an aluminium fin through the shell.",
        "Sealed, 1.06 A: 64 °C bare, 46 °C with the fin.",
        "No thermometer reading yet; the hold test is planned.",
      ],
      fund: { eq: "P = I²R;   R_cond = L / (k A);   R_conv = 1 / (h A)", sub: "P = 1.06² A² × 1.8 Ω = 2.0 W (R assumed). Flange path: PETG 14 K/W vs aluminium 0.011 K/W, 1260 × worse." },
      notes: {
        say: "Sealing the station in PETG meant the motor's only way out for heat was through plastic that conducts about one eight-hundredth as well as aluminium, so the mount that carries the cable load would run hot; I put a fin through the shell.",
        numbers: "A holding stepper dissipates P = I²R continuously: 1.0625² x 1.8 Ω = 2.0 W (coil resistance 1.8 Ω is ASSUMED; measure it with a meter). Conductivity: aluminium 160 vs PETG 0.2 W/m·K (800 x). Conduction resistance through the flange contact (42.3 mm square): 0.011 K/W aluminium vs 14.0 K/W PETG (1260 x). Two-node model at 23 °C ceiling air, h = 7 W/m²·K: sealed shell 64 °C with no fin, 46 °C with the as-built fin (carries 50 % of the heat), 40 °C with the drawn 1/8 in fin (68 %); vented 51 / 41 / 36 °C; open 47 / 39 / 35 °C. The sealed as-built case spans 45 to 49 °C over the h and conductivity ranges. Sealed-shell time constant 35 min.",
        qa: [["How do you know the fin works without a thermometer?", "I do not yet: these are CALCULATED values from a lumped model with an assumed coil resistance, film coefficient and shell resistances. The hold test is planned: thermometers on the motor case, the fin and the PETG tab at 1.06 A, pass limit below 60 °C."],
             ["Why a fin and not a TMC2209 or lower current?", "I weighed seven options (vents, aluminium fin, clip-on sink, TMC2209 drivers, ASA shell, thermistor park, lower current). The fin plus vents is the biggest gain with no new electronics; lower current costs pull, which is exactly the thing slide 5 is short of."]],
        check: "Hold-test length: the storyline says 60 minutes, FUNDAMENTALS section 3 says 90 minutes (covers 92 % of the final rise; 60 minutes covers about 82 % with the 35-minute time constant). Decide before the test. The storyline's '70 to 100 °C' for the PETG joint is not in the fundamentals sheet (the model says 64 °C sealed, no fin); do not quote it unless you have a source.",
        need: "What first made you suspect heat (warm motor, soft PETG, a calculation); which other options you actually considered and why each lost; any thermometer reading; coil resistance measured with a meter.",
        src: "FUNDAMENTALS.md section 3; DECK_STORYLINE.md slide 6.",
      },
    });
  }

  // ================================================================ 7 · Building the fin
  {
    decision({
      n: 7, topic: "BUILDING THE FIN", section: SECTION.a1, tags: ["MEASURED", "CALCULATED"], active: 2,
      title: "I drew 1/8-inch, built 0.019-inch, then re-checked the physics.",
      planned: { text: "Hold test: does the thin sheet bow or buzz, and are the screw threads deep enough?" },
      hero: (sl, b) => {
        const g = 0.12, cw = (b.w - g) / 2, chh = (b.h - g) / 2, ph = chh - 0.3;
        const cell = (c, r) => ({ x: b.x + c * (cw + g), y: b.y + r * (chh + g) });
        let p = cell(0, 0);
        photo(sl, "06_shear_with_drawings_and_blanks.jpg", p.x, p.y, cw, ph, "spread_1", { fx: 0.5, fy: 0.55 });
        caption(sl, "1  Sheared blanks beside my drawing", p.x, p.y + ph + 0.04, cw);
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
        "The drawn 1/8 in plate: fin efficiency about 74 %.",
        "The sheet I could shear and drill was 0.019 in.",
        "Re-run the fin equation first: efficiency falls 74 % to 37 %.",
        "Fin still carries about half the heat: 46 °C sealed.",
        "Thin sheet may buzz; screws reach 2.7 mm deeper, so check threads.",
      ],
      fund: { eq: "η = tanh(mL) / (mL),   m = √(2h / (k t))", sub: "t = 0.483 mm: m = 13.5 /m, mL = 2.69, η = 37 %, R_fin 10.9 → 22 K/W. Drawn 1/8 in: mL = 1.05, η = 74 %." },
      notes: {
        say: "The sheet I could shear and drill on the bench was 0.019 inch, not the 1/8 inch I drew, so before accepting it I re-ran the fin equation: efficiency drops from 74 to 37 percent but the fin still carries about half of the motor's heat.",
        numbers: "Fin parameter m = sqrt(2h/(k t)) with h = 7 W/m²·K, k = 160, L = 200 mm exposed. As built t = 0.483 mm: m = 13.5 /m, mL = 2.69, efficiency 37 % (33 to 43 % over h = 9 to 5), R_fin 22.1 K/W. Drawn t = 3.175 mm: m = 5.25, mL = 1.05, efficiency 74 % (70 to 80 %), R_fin 10.9 K/W. Sealed shell at 1.06 A: 46 °C (fin share 50 %) vs 40 °C (68 %) for the drawn plate: the thin fin costs about 6 K. Fit: 7/8 in (22.225 mm) centre hole over the 22.0 mm motor pilot boss, about 0.1 mm per side. Screws now reach 3.175 - 0.483 = 2.7 mm deeper into the motor.",
        qa: [["Why does a thinner fin still work?", "The exposed area is the same, so the fin still carries about half the heat; the efficiency halves, so the sealed motor runs about 6 K hotter than with the drawn plate. I checked that before accepting the sheet."],
             ["What tolerance did you reach?", "The drawing called for positions within 0.1 mm of each other in one setup; I have not caliper-checked the as-built part (need from me)."]],
        check: "Drawing notes (DECISION_STORIES story 1) give a Ø22.5 pilot hole; the as-built part uses a 7/8 in (22.225 mm) hole per the storyline and photo README. Confirm which is on the part. Say 'about 74 %' (the storyline's 'about 75 %' is the same number rounded).",
        need: "Photo of the fin installed in the station; hole-position tolerance (calipers); time per fin and any scrap; how the dimensions moved from 100 x 100 to 44 x 150 to 44 x 250 and why 1/8 in stock; where you sourced it and how many fins you made. Photo 03 (mill set-up with the printed drawing) is not on this slide: use it if you want the drawing shown.",
        src: "FUNDAMENTALS.md section 3; DECK_STORYLINE.md slide 7; photos 06, 01, 16.",
      },
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
