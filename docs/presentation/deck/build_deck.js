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
const BACKUPS = [];
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
  await sharp(c050).extract({ left: 22, top: 92, width: 712, height: 672 }).toFile(c050Panel);

  // ================================================================ 1 · Title
  pres.addSection({ title: SECTION.open });
  let s = pres.addSlide({ masterName: "Dark Title", sectionTitle: SECTION.open });
  slideNo += 1; ALL_SLIDES.push({ n: 1, label: "Title" });
  s.addText("RoomCleaner", { placeholder: "title" });
  s.addText([{ text: "A four-cable ceiling robot", options: { breakLine: true } }, { text: "that picks laundry off the floor" }], { placeholder: "subtitle" });
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
    [["BOUGHT", "A4988 driver, ESP32, DROK buck, MG996R servo.", false], ["MADE BY ME", "Everything else: designed, printed, machined and wired.", true]].forEach(([k, v, mine], i) => {
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
        sl.addChart(pres.charts.SCATTER, [
          { name: "Depth", values: depths },
          { name: "Static: 1 lb + 0.45 kg claw", values: Tst },
          { name: "With +2 m/s²", values: Tdy },
        ], chartOpts({
          ...box, chartColors: [HEX.signal, HEX.steel], lineSize: 3, lineDataSymbol: "none",
          valAxisMinVal: 0, valAxisMaxVal: 40, valAxisMajorUnit: 10, catAxisMinVal: 0.15, catAxisMaxVal: 1.2, catAxisMajorUnit: 0.15,
          valGridLine: { color: HEX.fog, size: 0.75 }, catGridLine: { style: "none" },
          showValAxisTitle: true, valAxisTitle: "Tension per cable (N)", showCatAxisTitle: true, catAxisTitle: "Depth below the anchors (m)",
          showLegend: true, legendPos: "b", layout,
        }));
        limitLine(sl, plotRect(box, layout), 40, V.t01_f_use, "11.9 N winch design force", { color: HEX.ink });
      },
      rail: [
        "Use the whole room.",
        "32 N at 0.15 m depth, 8.3 N at 0.6 m.",
        "Ceiling margin 0.4 m, plus a wall margin.",
        "At task heights, corners bind (1.1 × weight).",
        "Claw mass counts like payload.",
      ],
      fund: { eq: "T = W / (4 sin φ),  sin φ = d / √(d² + D_{h}²)", sub: "W = 8.86 N (1 lb + 0.45 kg claw), D_{h} = 2.17 m: T = 32.1 N at d = 0.15 m, 8.3 N at 0.60 m." },
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
        const cb = { x: b.x, y: b.y + 0.9, w: b.w, h: b.h - 0.9 };
        const layout = { x: 0.13, y: 0.1, w: 0.84, h: 0.56 };
        sl.addChart(pres.charts.BAR, [{ name: "Largest claw that still lifts 0.9 kg jeans (g)", labels, values: vals }], chartOpts({
          ...cb, barDir: "col", barGapWidthPct: 55, chartColors: [HEX.steel, HEX.steel, HEX.signal, HEX.steel], invertedColors: [HEX.steel],
          showValue: true, dataLabelPosition: "inBase", dataLabelColor: HEX.paper, dataLabelFormatCode: '#,##0" g"', valAxisMinVal: 0, valAxisMaxVal: 1250, valAxisMajorUnit: 250,
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
        "Raise current from 1.0 to 1.35 A.",
        "Vref pot maxes at 0.85 V: 1.06 A cap.",
        "Run at the cap; shrink the spool core.",
        "Winches hold ~1.1 kg; claw plus jeans ~2 kg.",
        "Torque factor 0.7 assumed; pull test decides.",
      ],
      fund: { eq: "I = Vref / (8·R_{s}) = 0.85 V / 0.8 Ω = 1.06 A", sub: "T = τ / r: τ_{run} = 0.7 × 0.255 N·m = 0.179 N·m, so T = 23.8 N at r = 7.5 mm and 17.9 N at a full spool (r = 10 mm)." },
      notes: {
        say: "My own numbers told me my claw outgrew my winches: the driver board caps the current at 1.06 A, so I am buying the pull back with geometry instead of hacking the driver.",
        numbers: "Vref pot maximum 0.85 V (MEASURED on the red R100 boards, 3.3 V logic; an earlier entry says 0.79 V, which gives 0.99 A, so there is a 7 % spread). I = Vref / (8 Rs) = 0.85 / 0.8 = 1.06 A. Holding torque 0.36 N·m x 1.0625 / 1.5 = 0.255 N·m; running torque 0.7 x holding = 0.179 N·m (the 0.7 is assumed). Pull T = tau / r: 23.8 N at the 7.5 mm core, 17.9 N at a full 10 mm spool; design force (divided by 1.5) 15.9 N and 11.9 N; snag case 34 N. Largest claw that still lifts 0.9 kg of jeans at the highest task pose: 202 g (Ø15 core, 1.10 kg held), 397 g (Ø12), 478 g (Ø10, +25 %), 570 g (Ø8, which fails the 20:1 bend ratio and the tie-off). Needed: 0.45 kg claw + 0.9 kg = 1.35 kg, which is 1.22 x what the Ø15 spool can hold. Printed claw estimate 1.05 to 1.25 kg (unweighed) gives 2.0 to 2.2 kg with jeans. A 3:1 reduction at each winch buys about 2.7 x (2.98 to 3.09 kg held at a 0.2 m wall margin).",
        qa: [["Why not raise Vref or run 5 V logic?", "I do not want to modify the driver, and a 3.3 V GPIO cannot guarantee a HIGH into a 5 V-logic input. So I run at the board maximum and recover pull mechanically: T = tau / r, so a smaller core gives more tension."],
             ["Is the 0.7 running-torque factor right?", "It is assumed (an earlier table used 0.5). A 15-minute luggage-scale pull test at 1.06 A, empty and full spool, replaces it with a number. Procedure: docs/tests/WINCH_PULL_TEST.md (holding peak by hand, running pull before the motor skips, at 100 / 200 / 400 steps/s, on the core and on a full spool). If the running pull at a full spool is 25 N or more, the direct drive might carry a lighter claw; under 25 N (expected about 18 N) go to the 3:1 reduction (memo option 1), with a lighter payload for the demo."]],
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
        "A clean, closed printed shell.",
        "Holding stepper heats (I²R); PETG conducts 1/800 of aluminium.",
        "Vents plus an aluminium fin.",
        "Sealed, 1.06 A: 64 °C bare, 46 °C finned.",
        "No thermometer data yet; hold test planned.",
      ],
      fund: { eq: "P = I²R;   R_{cond} = L / (k A);   R_{conv} = 1 / (h A)", sub: "P = 1.06² A² × 1.8 Ω = 2.0 W (R assumed). Flange path: PETG 14 K/W vs aluminium 0.011 K/W, 1260 × worse." },
      notes: {
        say: "Sealing the station in PETG meant the motor's only way out for heat was through plastic that conducts about one eight-hundredth as well as aluminium, so the mount that carries the cable load would run hot; I put a fin through the shell.",
        numbers: "A holding stepper dissipates P = I²R continuously: 1.0625² x 1.8 Ω = 2.0 W (coil resistance 1.8 Ω is ASSUMED; measure it with a meter). Conductivity: aluminium 160 vs PETG 0.2 W/m·K (800 x). Conduction resistance through the flange contact (42.3 mm square): 0.011 K/W aluminium vs 14.0 K/W PETG (1260 x). Two-node model at 23 °C ceiling air, h = 7 W/m²·K: sealed shell 64 °C with no fin, 46 °C with the as-built fin (carries 50 % of the heat), 40 °C with the drawn 1/8 in fin (68 %); vented 51 / 41 / 36 °C; open 47 / 39 / 35 °C. The sealed as-built case spans 45 to 49 °C over the h and conductivity ranges. Sealed-shell time constant 35 min.",
        qa: [["How do you know the fin works without a thermometer?", "I do not yet: these are CALCULATED values from a lumped model with an assumed coil resistance, film coefficient and shell resistances. The hold test is planned: thermometers on the motor case, the fin and the PETG tab at 1.06 A, pass limit below 60 °C."],
             ["Why a fin and not a TMC2209 or lower current?", "I weighed seven options (vents, aluminium fin, clip-on sink, TMC2209 drivers, ASA shell, thermistor park, lower current). The fin plus vents is the biggest gain with no new electronics; lower current costs pull, which is exactly the thing slide 5 is short of."]],
        check: "Hold-test length: the storyline and docs/simulation/SW_THERMAL_HEAT_FIN.md section 8 say 60 minutes (D29), on a vented shell with two thermocouples and the fin flattened; FUNDAMENTALS section 3 assumes 90 minutes. Per the thermal manual, 60 minutes reads about 94 % of the steady value for a vented shell but a sealed shell takes about 104 minutes, so a 60-minute reading is compared with 0.94 x the prediction, or run 90 minutes. The planned test is therefore on the vented shell (predicted 41 °C with the as-built fin); the 46 °C sealed figure on this slide is not what it will read. The storyline's '70 to 100 °C' for the PETG joint is not in the fundamentals sheet (the model says 64 °C sealed, no fin); do not quote it unless you have a source.",
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
        "Drawn: 1/8 in plate, fin efficiency 74 %.",
        "The sheet I could drill was 0.019 in.",
        "Re-ran the fin equation: 74 % falls to 37 %.",
        "Still carries about half the heat: 46 °C.",
        "May buzz; screws reach 2.7 mm deeper.",
      ],
      fund: { eq: "η = tanh(mL) / (mL),   m = √(2h / (k t))", sub: "t = 0.483 mm: m = 13.5 /m, mL = 2.69, η = 37 %, R_{fin} = 22 K/W. Drawn 1/8 in: mL = 1.05, η = 74 %, R_{fin} = 10.9 K/W." },
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
      "32 mm drum on a Ø20 core.",
      "Stuck out 14.5 mm past the 24 mm shaft.",
      "Ø15 core, 16 mm drum; radius tracks wound length.",
      "v2 bore too tight: Ø5.2 opened to Ø5.45.",
      "Printed holes shrink; bore never calipered.",
    ],
    fund: { eq: "r(n) = r_{0} + n·d·p;   T = τ / r(n);   ℓ = 2πr", sub: "20 ft of 0.5 mm line on the Ø15 core: 5 layers, r = 7.5 to 10 mm, T = 23.8 to 17.9 N, line per rev 47 to 63 mm (+33 %)." },
    notes: {
      say: "My first spool stuck out about 14.5 millimetres past the end of the motor shaft, and fixing that changed the layer count, the line force and the line paid out per revolution, so the controller has to model radius against wound length.",
      numbers: "Gen-1 spool: Ø20 core x 26 mm winding x 32 mm overall. Spool v3 (from the STEP): Ø36 flanges, Ø15 core (r = 7.5 mm), 16 mm drum, 22 mm overall, bore Ø5.45 with a 0.5 mm D-flat on the Ø5 shaft. 20 ft (6.096 m) of 0.5 mm line at 85 % packing gives 5 layers and a full radius of 10 mm. Line force falls 23.8 to 17.9 N; line per revolution 47.1 to 62.8 mm (+33 %). v2 bore Ø5.2 printed too tight on the Ø5.0 shaft; v3 opened to Ø5.45. Printed holes print undersize (bead rounding, shrink, elephant foot, mesh chords): Ø5.2 too tight means at least 0.2 mm was lost, so the Ø5.45 bore really leaves about 0.25 mm of clearance, not 0.45 mm. A fit coupon (54 holes: -0.10 to +0.30 mm in 0.05 steps at Ø5, Ø7, Ø14, vertical and horizontal) is PLANNED; none has been printed.",
      qa: [["Why not a level-wind?", "I need your answer here (see need list)."],
           ["How does the controller cope with the changing radius?", "It uses radius as a function of wound length, r(n) = r0 + n d p, so the line paid out per step stays right as the spool fills; line per revolution changes by 33 % between the core layer and a full spool."]],
      check: "The 'about 14.5 mm' is derived from the 2026-10-06 dimension note (shaft projection 24 mm, winding from X = 4.5 for 32 mm overall), not from your own measurement. Say it as a derived number unless you measured it.",
      need: "v2 and v3 printed bore caliper readings; what you measured on the shaft (engagement length, flat depth); why the core went Ø20 to Ø15 and the drum 26 to 16 mm; line diameter (the record says 0.5, 0.6 and 1.0 mm in different files); whether you considered a level-wind; printer and filament.",
      src: "DECK_STORYLINE.md slide 8; FUNDAMENTALS.md sections 2 and 12; DECISION_STORIES.md T23, T24.",
    },
  });

  // ================================================================ 9 · Homing switch
  decision({
    n: 9, topic: "HOMING SWITCH", section: SECTION.a2, tags: ["CALCULATED"], active: 3,
    title: "Bead must never cross the pulley; rev C missed by 5 mm.",
    planned: { head: "PLANNED — not yet run", text: "Trip test: a 5 mm bead on real line against the printed rev D arm." },
    hero: (sl, b) => {
      const map = photo(sl, "09_homing_switch_perfboard.jpg", b.x, b.y, b.w, b.h, "hero_photo", { fx: 0.42, fy: 0.6 });
      const roller = map(0.14, 0.753);
      if (roller) callout(sl, roller[0], roller[1], roller[0] + 1.1, roller[1] - 0.75, "Switch roller");
    },
    rail: [
      "Bead on the line trips a home switch.",
      "Mid-span, the bead rides over the pulley.",
      "A drop arm under the pulley.",
      "Rev C missed by 5 mm; rev D overlaps 3.75 mm.",
      "Never trip-tested on real line yet.",
    ],
    fund: { eq: "Y overlap = (r_{bead} + r_{roller}) − Y_{roller}", sub: "(2.5 + 2.25) − 1.0 = 3.75 mm, need ≥ 2.0 mm. X error ≤ 1.0 mm across 18 to 22 mm pulleys, 0 after the ±2 mm slot." },
    notes: {
      say: "The bead on the line must never ride over the pulley, so I moved the switch to a drop arm under it; my first version of that missed the line by 5 millimetres and rev D lands the roller on it.",
      numbers: "Rev C: roller at X = 70.0 against the line at 65.0, so 5.0 mm off in X and 10.5 mm off in Y (no contact) against a 1.5 mm overlap requirement. Rev D: X error 0 at the nominal 20 mm pulley, 1.0 mm untuned at 18 and 22 mm (limit 1.0), 0 after the ±2 mm slot tune; Y: roller 1.0 mm, overlap (2.5 + 2.25) - 1.0 = 3.75 mm on a 5 mm bead (limit 2.0 mm). Roller envelope clear of the pulley and of printed material (0.000 mm³ interference).",
      qa: [["How do you know it will trip?", "I do not yet: rev D passes the geometric checks in CAD, but I have not run a bead past a printed arm on real line. That trip test is the open item."],
           ["What did you notice that showed the problem?", "I need your answer here (see need list)."]],
      need: "What you actually noticed about the bead riding over the groove (this was your find); whether rev D was printed and a bead trip-tested; the real bead diameter. Photo 09 is a bench microswitch on the perfboard, not the rev D arm.",
      src: "DECK_STORYLINE.md slide 9; verification/corner_mount_revD_report.md; DECISION_STORIES.md T16, section 4 item 2.",
    },
  });

  // ================================================================ 10 · Removable station
  decision({
    n: 10, topic: "REMOVABLE STATION", section: SECTION.a2, tags: ["PLANNED"], active: 3,
    title: "A removable station moves the anchor from a screw to a slide.",
    planned: { text: "SolidWorks linear static study (stress, safety factor, deflection) and a physical station pull test." },
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
      "Fixed frame plus slide-in housing, SF ≥ 3.",
      "SolidWorks static study pending.",
      "Statics can't see creep; pull test too.",
    ],
    fund: { eq: "σ = M c / I (rail root);   δ = F L³ / (3 E I) (cable exit)", sub: "Pass limits at the 34 N slip-limit load: peak σ ≤ 8.33 MPa (SF ≥ 3 on 25 MPa derated yield), deflection ≤ 0.5 mm at the cable exit." },
    notes: {
      say: "Making the station removable moved the anchor from a screw to a slide, and anchor error turns one-to-one into claw position error, so I am stress-testing the slide-in.",
      numbers: "PLANNED, no results yet: SolidWorks linear static study of the station mount, reporting peak stress, safety factor and deflection at the cable exit. Pass limits: SF at least 3 on derated PETG; deflection at most 0.5 mm. The line pulls the station away from the wall, so the stud screws see pull-out rather than shear. Load basis: slip-limit tension x a dynamic factor. Linear statics cannot see creep or layer-adhesion weakness, so a physical pull test closes the gap.",
      qa: [["What retains the slide-in, and what load did you check it against?", "I need your answer here (see need list). The design intent is positive retention sized for the slip-limit tension times a dynamic factor."],
           ["Why not keep the screwed-down anchor?", "A hook or loose anchor wanders and that error goes 1:1 into claw position; I bolted the corner down first, then service needs forced removable stations without re-calibrating the room, so the anchor moved onto a fixed frame and the housing slides in."]],
      check: "Do not show any stress or safety-factor result until the study is run. The study manual docs/simulation/SW_STATIC_STATION_MOUNT.md (it was not in the repository when this deck was started; it arrived in commit 7135d7c) gives the answer sheet: P1 peak von Mises at the 34.0 N slip-limit load at most 8.33 MPa (SF 3 on 25 MPa), P4 cable-exit displacement at most 0.50 mm, plus P2, P3, P5 to P7. Its hand estimates (about 3 to 14 MPa at the motor-tab root) are expectations, not results.",
      need: "SolidWorks results (peak stress, SF, deflection) after the study tomorrow; what the gen-1 plate tests (photos 05 and 13) showed; the slide retention mechanism and the load you checked it against; the study document.",
      src: "DECK_STORYLINE.md slide 10; DECISION_STORIES.md T06, T25.",
    },
  });

  // ================================================================ 11 · Gripper
  {
    const cats = ["1 lb\nμ 0.3", "1 lb\nμ 0.6", "Jeans\nμ 0.3", "Jeans\nμ 0.6"];
    const vals = [V.t05_N_lb_mu03, V.t05_N_lb_mu06, V.t05_N_jeans_mu03, V.t05_N_jeans_mu06].map((x) => r1(x));
    decision({
      n: 11, topic: "GRIPPER", section: SECTION.a2, tags: ["CALCULATED", "SIMULATED"], active: 4,
      title: "A clamp stalls the servo every grip, so I sized for stall.",
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
        [["v6_compound_original.png", "My v6 compound, 3:1", "gear set 157 g (CAD)"], ["v6r_compound.png", "Rebuilt, 2:1", "gear set 96 g (CAD)"]].forEach(([f, t, sub], i) => {
          const x = b.x + 0.15 + i * (b.w / 2);
          renderFit(sl, f, x, sy + 0.12, 1.1, sh - 0.24, `gear_render_${i + 1}`);
          sl.addText(t, { x: x + 1.2, y: sy + 0.3, w: b.w / 2 - 1.4, h: 0.5, fontSize: 12, bold: true, fontFace: "Arial", color: C.text1, margin: 0, valign: "top", isTextBox: true });
          sl.addText(sub, { x: x + 1.2, y: sy + 0.85, w: b.w / 2 - 1.4, h: 0.4, fontSize: 11, color: C.text2, margin: 0, valign: "top", isTextBox: true });
        });
      },
      rail: [
        "Five soft tendon fingers.",
        "A clamp is simpler but stalls the servo.",
        "Module 1.5, 2:1 ratio, my own 36T gear.",
        "Gears 157 g to 96 g; 257 checks pass.",
        "Jeans at μ 0.3 need 17.7 N; jaws give 13.3–25 N.",
      ],
      fund: { eq: "σ = F_{t} / (b·m·Y);   N ≥ m(g + a) / (2μ)", sub: "Module 1: SF 0.35–0.41 at stall; module 1.5, 16 mm face: SF 2.0–2.5. Jeans: 0.9 × 11.81 / (2 × 0.3) = 17.7 N per jaw." },
      notes: {
        say: "A clamp does not stop at a position, it stops when the servo stalls, so every grip loads the gear teeth at full stall torque and I sized the teeth for that moment, then rebuilt the train at 2:1 when the claw turned out far over its mass budget.",
        numbers: "MG996R stall 9.4 kg·cm at 4.8 V (0.922 N·m) and 11.0 kg·cm at 6.0 V (1.079 N·m). Lewis bending: F_t = 2 tau / (m z), sigma = F_t / (b m Y), allowable 22.5 MPa (half of 45 MPa PETG for layer adhesion and fatigue). Module 1, 6 mm face, 18T pinion at 6 V: F_t = 119.9 N, 64.7 MPa, SF 0.35 (0.41 at 4.8 V). As built (module 1.5, 16 mm face, 18 / 36 / 24 / 24 teeth): pinion SF 2.40 / 2.05, 36T gear 2.93 / 2.50, sync gear 2.34 / 2.00 at 4.8 / 6.0 V (the 24T sync gear at 6 V is 1.997, accepted as inside the precision of the assumed stall torque). Ratio 2:1: jaw torque 0.83 N·m, stroke 76.5 degrees; 3:1 would give 1.25 N·m, 51 degrees and a sync-gear SF of 1.56 (1.33 at 6 V). The v6 inspection found the gripper at about 2.06 kg against the 450 g budget (4.6 x), so I rebuilt my own gears at 2:1 with a 36T gear instead of 54T and an R53 crank instead of R75, kept my press-fit bearing pockets (Ø14.075 with a Ø14.000 lead-in lip) and added 0.42 mm backlash and a 0.3 mm axial relief; gear set 157 g to 96 g (CAD), all features identical to my originals except the intended changes at 257 checks. Grip: N >= m (g + a) / (2 mu): 1 lb needs 8.9 N per jaw at mu 0.3 (4.5 N at 0.6); jeans need 17.7 N (8.9 N at 0.6). Jaw force at 4.8 V: 13.3 N at the weakest position (gap 0.6 mm) to 25.0 N at a 70 mm grab; 17 % more at 6 V. Margin at the weakest point: 1 lb 1.5 x; jeans at mu 0.3 0.75 x (short); they need a grab of at least 43 mm (22 mm at 6 V). From the storyline: the 7-hole web is SF about 1.7; 6 holes would give 3.75.",
        qa: [["Is the jaw force measured?", "No. It is simulated from the four-bar model (efficiency 0.95 per mesh, no pivot friction); there is no force gauge reading and no printed gear has been stalled. Pad-to-cloth friction has never been measured, which is why TPU pads are on the claw and a pull test is the first thing to run."],
             ["Why 2:1 instead of 3:1?", "Mass and the sync gear: 3:1 loads the sync gear to a margin of 1.3 to 1.6, and the v6 gripper was 4.6 x over the mass budget."]],
        check: "An earlier design review quoted a 2.8 x grip margin for 1 lb; that came from an earlier gearbox estimate (20.8 N). The as-built four-bar gives 1.5 x at the weakest point. Say 1.5 x.",
        need: "When and why you chose module 1.5 with 16 and 20 mm faces; whether you ran strength numbers or printed a test gear before the Oct 19 review; the weighed or sliced claw mass and the new budget; why a 12 in aluminium tube.",
        src: "FUNDAMENTALS.md sections 4 and 5; verification/gripper_v7_verification.md; DECK_STORYLINE.md slide 11.",
      },
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
      caption(sl, "Camera view, 50 mm cut, 140 mm hover. Green box = grasp zone.", px, b.y + 1.0 + ph + 0.05, pw, 0.45);
      callout(sl, rx + 0.9 * rw, ry + 0.107 * rh, px + 0.3, b.y + 0.45, "Camera bay");
    },
    rail: [
      "Long aluminium arm; camera sees the jaws.",
      "At contact, a plate hides the grasp spot.",
      "Cut 50 mm of tube, not 100 mm.",
      "Visible from 140 mm hover (was 172 mm); saves 33 g.",
      "Last ~14 cm is blind; add a hover correction.",
    ],
    fund: { eq: "D* = (k (H_{0} − c) − 93) / (1 − k),   k = 1 − 59.5/97", sub: "k = 0.387, H_{0} = 512 mm: c = 0 gives D* = 171 mm, c = 50 mm gives 140 mm; each mm cut lowers D* by 0.63 mm." },
    notes: {
      say: "I wanted the camera to see everything, but at the moment of contact the gearbox plate hides the grasp spot, so I cut 50 millimetres of tube and added a short visual correction step at the hover.",
      numbers: "Similar triangles: a ray from the lens (512.06 mm above the floor with the jaw tips down, 90 mm off the tube axis) to the far edge of the grasp zone (97 mm from the lens) passes the plate face (59.5 mm from the lens) at k = 1 - 59.5/97 = 0.3866 of the lens height. Minimum hover D* = (k (H0 - c) - 93) / (1 - k): 171.1 mm uncut, 139.6 mm with a 50 mm cut (ray-cast scan over the CAD: 172 and 140 mm), 108 mm at 100 mm cut. Each mm of cut lowers D* by 0.63 mm and saves 0.65 g (32.5 g for 50 mm); the tube can be cut up to 206 mm before the hub meets the head plates. In the 140 mm hover view the grasp zone is 100 % visible and the claw blocks 9.2 % of the 4:3 view with open jaws (7.6 % closed). Why aluminium: a long printed arm under constant load creeps and would slowly shift the camera against the jaws; same tube, same 10 N tip load: 0.04 mm in aluminium vs 1.32 mm in PETG (33 x). Collars and press fits are a stress-relaxation problem, so the tube joints need a positive cross-bolt lock.",
      qa: [["Why not cut 100 mm?", "We can always cut more; a cut cannot be undone. 50 mm already brings the hover from 171 to 140 mm and saves 33 g. A shorter tube also shrinks the view and lowers the cable tie-offs toward furniture."],
           ["What about a pile of laundry?", "A pile raises the floor, so the required hover rises by the pile height; the model assumes a flat bare floor and a claw hanging still."]],
      check: "The tube wall (3 mm in CAD, 28.54 mm OD) and alloy are unmeasured; the figures that depend on them are labelled CALCULATED. Closed-form 171.1 / 139.6 mm vs ray-cast 172 / 140 mm: the scan reports the first whole millimetre, so they agree.",
      need: "Confirm why a 12 in aluminium tube (your reason: creep, so the camera stays registered to the jaws); tube wall thickness and alloy; a re-extracted centre-of-mass depth.",
      src: "FUNDAMENTALS.md sections 6 and 11; renders/claw_tube_length_view/c050_Dstar140.png; DECISION_STORIES.md section 5.",
    },
  });

  // ================================================================ 13 · Distributed electronics
  pres.addSection({ title: SECTION.a3 });
  decision({
    n: 13, topic: "DISTRIBUTED ELECTRONICS", section: SECTION.a3, tags: ["CALCULATED", "SIMULATED"], active: 2,
    title: "One controller per winch fixed the wiring and priced sync error.",
    planned: { head: "PLANNED — not yet run", text: "Four stations, 1 lb, 300 mm at 50 mm/s: pass if each cable is within 2 mm." },
    hero: (sl, b) => {
      const g = 0.12, cw = (b.w - g) / 2;
      [["14_gen1_cnc_shield_a4988.jpg", "JULY · central", 0.5, 0.5], ["10_buck_converter_wiring.jpg", "OCTOBER · per winch", 0.5, 0.62]].forEach(([f, lab, fx, fy], i) => {
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
    fund: { eq: "Δℓ = v·Δt;   F = k·Δℓ;   V = I·ρ·2L / A", sub: "50 mm/s × 50 ms = 2.5 mm; 3 N/mm × 2.5 mm = 7.5 N. 16 AWG, 32 ft, 2 A: 0.51 V drop (18 AWG: 0.82 V)." },
    notes: {
      say: "In July I kept one controller so synchronised motion came for free; in October long harnesses pushed me to one controller per winch, and I priced what that costs: every millisecond of skew becomes force on four over-constrained cables.",
      numbers: "Skew: 50 mm/s x 50 ms = 2.5 mm of length error; with an assumed line stiffness of 3 N/mm (E A / L over a 3 m run), F = 7.5 N, about 90 % of the static tension at 0.6 m depth (8.3 N). The 2 mm pass criterion is 6 N, which a 40 ms skew at full speed produces. Wire: 32 ft (9.75 m) one way, 12 V label, 2 A: 18 AWG drops 0.82 V (6.8 %), 16 AWG 0.51 V (4.3 %); 16 AWG chosen for the long run. Architecture (simulated): the host plans; stations execute Hermite segments on their own clocks with path-time feed-hold and leases; stop never disables (D21), no automatic resume (D25). Simulated: lease-aligned stop spread about 18 ms; 10/10 lossy motions completed at 2 to 5 % packet loss.",
      qa: [["Why not keep the central controller for the 1 lb demo?", "I need your answer here (see need list): whether a central-stepping fallback is still planned."],
           ["What is feed-hold?", "A coordinated stop in path time: all four stations ramp their path rate to zero along the same geometric path, so the claw decelerates along the path instead of one winch stopping first."]],
      check: "The 3 N/mm stiffness and the 50 ms Wi-Fi skew are assumptions. Everything on the control side is SIMULATED; nothing has run on four stations.",
      need: "What bothered you most about the central controller in October (harness length numbers, the one-plug goal); whether a hybrid fallback exists for the 1 lb demo.",
      src: "FUNDAMENTALS.md sections 9 and 10; docs/CONTROL_SYSTEM_V1.md; DECISIONS.md D20, D21, D25.",
    },
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
      sl.addText("read on the meter", { x: tx + 0.15, y: b.y + 2.57, w: tw - 0.3, h: 0.5, fontSize: 12, color: C.text2, margin: 0, valign: "top", isTextBox: true });
    },
    rail: [
      "First motion on the new station board.",
      "Pulses sent, shaft still; logic rail read 1.14 V.",
      "Solder 3.3 V; pull resistors; JP1; measure VDD.",
      "Rev D board, net-checked; motion after repair.",
      "As-built board still needs its meter checklist.",
    ],
    fund: { eq: "I = Vref / (8·R_{s}) = 0.85 V / 0.8 Ω = 1.06 A", sub: "Meter first: logic rail 1.14 V read against 3.3 V expected. The same habit on Oct 21 found the Vref pot topping out at 0.85 V." },
    notes: {
      say: "The log said the driver was stepping, but the meter said the 3.3 volt logic rail was 1.14 volts; since then I measure the supply before I touch the code.",
      numbers: "Command log: pulses sent, ENABLE toggled 3.3 to 0 to 3.3 V; shaft did not move; logic rail 1.14 V (expected 3.3 V) from a poor 3.3 V connection. Oct 21: the same habit caught a second limit, the Vref pot maxing at 0.85 V (1.06 A). Rev D fixes: 3.3 V soldered rather than jumpered; 10 k pull resistors (R1 EN pull-up so the A4988 boots disabled; R2 and R3 STEP and DIR pull-downs); JP1 link with diode D1 (1N5819) so USB and the buck never fight; a measure-VDD step in the bring-up procedure; 100 µF bulk capacitor on VMOT. The perfboard layout is net-checked by script: every hole has exactly one net and every net is connected. Buck output checked at 5.00 V before connecting loads.",
      qa: [["What did you try before the meter?", "I need your answer here (see need list)."],
           ["Is the supply safe for the buck?", "The bench reading was 18 V while the brick label says 12 V and the DROK input limit is 20 V; whether that was an open-circuit reading is still to be answered (T15)."]],
      check: "Show only the 1.14 V and 3.3 V figures; the photo does not show the meter reading.",
      need: "Exact readings and dates (VDD, SLEEP, ENABLE) and VDD after the repair; what the bad connection physically was; what you tried first; whether the XIAO that heated and lost USB is quarantined; a photo of the built perfboard (the layout image is B3).",
      src: "DECK_STORYLINE.md slide 14; DESIGN_STATE.md; docs/electrical/station_revD_20261021/PERFBOARD_LAYOUT.md; DECISION_STORIES.md T29, T30.",
    },
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
      sl.addText("≥ 2 tags in view", { x: fcx + fr * 0.55, y: gy + 3 * pitch - 0.1, w: 1.6, h: 0.28, fontSize: 12, bold: true, fontFace: "Arial", color: C.text1, margin: 0, valign: "middle", isTextBox: true });
      // big comparison
      sl.addText([{ text: "6.6 mm → ", options: { color: C.text1 } }, { text: "0.7 mm", options: { color: C.accent1 } }], { x: b.x + 0.25, y: b.y + 3.9, w: b.w - 0.5, h: 0.55, fontSize: 32, bold: true, fontFace: "Arial", margin: 0, valign: "middle", isTextBox: true, objectName: "big_number" });
      sl.addText("lever-arm error per frame at 0.51 m: one tag vs the four-tag board", { x: b.x + 0.25, y: b.y + 4.45, w: b.w - 0.5, h: 0.3, fontSize: 12, color: C.text2, margin: 0, valign: "top", isTextBox: true });
    },
    rail: [
      "Absolute cable lengths from vision alone.",
      "One tag errs 6.6 mm; σ > 12 mm overtravel.",
      "Margins carry safety; probe slack; drop the IMU.",
      "Simulated: 6/6 startups; 3 of 6 reach full trust.",
      "Claw tilts 13–21° near corners; all simulated.",
    ],
    fund: { eq: "δx = σ_{θ}·L;   σ_{N} = σ / √N", sub: "One tag: 12.9 mrad × 0.51 m = 6.6 mm. Four-tag board: 1.3 mrad × 0.51 m = 0.68 mm. 91–97 % of slack readings resolved (sim)." },
    notes: {
      say: "I stopped trying to buy precision and moved the safety into margins: ceiling and wall margins carry it, and a floor board plus a one-cable-at-a-time slack probe makes the calibration honest.",
      numbers: "Lever-arm error dx = sigma_theta x L. One 152.4 mm tag at 0.51 m with 0.3 px corner noise: 12.9 mrad, 6.6 mm per frame; tilt noise 10.5 / 17.9 / 31.8 / 49.7 mrad at 0.46 / 0.6 / 0.8 / 1.0 m. A four-tag board (150 mm tags, 0.25 m pitch) with at least two tags in view: 1.3 mrad, 0.68 mm (about 10 x better). Simulated: 6/6 startups, 91 to 97 % of slack readings resolved, predicted sigma 12 to 16 mm, 3 of 6 runs reach full-room trust. Calibration sigma stayed above the 12 mm bead overtravel; decisions D26 (margins carry the safety, reel each cable in turn: no motion means slack) and D27 (no IMU on the claw). A converged optimiser is not acceptance: in the one-cable toy both fits had a whitened residual near 1.0, yet the anchor range and length offset were 9 x less identifiable in the small excitation box.",
      qa: [["What prompted the margins decision?", "I need your answer here (see need list)."],
           ["Why does tilt matter?", "The claw hangs tilted near the corners: 12.9 degrees at the largest with the recorded centre-of-mass depth of 0.196 m (stale) and 20.7 degrees with the lumped estimate for the current head (0.116 m); 83 to 92 % of grid points exceed 5 degrees. So the grip-tilt rule needs a decision before tilt gates grips across the room."]],
      check: "The storyline says 'about 13°'; that uses the stale centre-of-mass depth. The slide says 13 to 21° so both numbers are covered. Re-extract the centre of mass from the CAD before quoting either as final.",
      need: "What observation led to D26 and the slide probe; any hardware test planned before the panel; the re-extracted centre-of-mass depth.",
      src: "FUNDAMENTALS.md sections 7 and 8; DECISIONS.md D26, D27; docs/STARTUP_CALIBRATION_V1_20261016.md.",
    },
  });

  // ================================================================ 16 · Evidence table
  pres.addSection({ title: SECTION.close });
  s = addContent(SECTION.close, "16 Evidence so far");
  s.addText("EVIDENCE SO FAR", { placeholder: "eyebrow" });
  s.addText("Measured, calculated, simulated, planned: the test that decides the rest.", { placeholder: "title" });
  {
    const colW = (W - 2 * M) / 4;
    const head = (t) => ({ text: t, options: { bold: true, fontFace: "Arial", fontSize: 12, color: C.text1, fill: { color: C.background2 }, valign: "middle", border: [{ type: "none" }, { type: "none" }, { type: "none" }, { type: "none" }] } });
    const cell = (items, last) => ({
      text: items.map((t, i) => ({ text: kit.nb(t), options: { bullet: { indent: 14 }, breakLine: i < items.length - 1, paraSpaceAfter: 6 } })),
      options: { fontSize: 14, color: C.text1, valign: "top", border: [{ type: "none" }, { type: "none" }, { pt: 0.75, color: HEX.fog }, { type: "none" }], margin: [8, 10, 8, 10] },
    });
    s.addTable([
      [head("MEASURED"), head("CALCULATED"), head("SIMULATED"), head("PLANNED, with pass limits")],
      [
        cell(["Vref cap 0.75–0.85 V", "One motor on all four driver channels", "18 V on the meter at the supply", "Buck output 5.00 V", "Fin fits the motor", "Logic rail 1.14 V (the fault)"]),
        cell(["Cable statics, 32 to 4.6 N", "Gear stress (Lewis)", "Fin efficiency, 74 % to 37 %", "Wire drop, 0.51 V", "Grip force per jaw"]),
        cell(["Control system and sync", "Startup calibration", "Camera view vs tube length", "Jaw force, four-bar model"]),
        cell(["Hold test: motor case below 60 °C", "Station pull test, empty and full spool", "SolidWorks station study: SF ≥ 3, ≤ 0.5 mm", "1 lb, four stations, 300 mm at 50 mm/s: ≤ 2 mm per cable"]),
      ],
    ], { x: M, y: 2.0, w: W - 2 * M, colW: [colW, colW, colW, colW], rowH: [0.42, 3.2], fontFace: "Calibri", objectName: "evidence_table" });
    s.addShape(pres.shapes.RECTANGLE, { x: M, y: 5.85, w: W - 2 * M, h: 0.85, fill: { color: C.accent5 }, line: { color: C.accent1, width: 1.5 }, objectName: "first_test_card" });
    eyebrowLabel(s, "FIRST TEST", M + 0.25, 6.0, 3, C.text1);
    s.addText("Luggage-scale pull at 1.06 A, empty and full spool. Under 25 N at a full spool means a 3:1 reduction.", { x: M + 0.25, y: 6.25, w: W - 2 * M - 0.5, h: 0.35, fontSize: 16, color: C.text1, margin: 0, valign: "middle", isTextBox: true });
  }
  s.addNotes(notes({
    say: "Here is what I have actually measured, what is calculated, what is simulated, and the specific tests that decide the rest, each with its pass limit.",
    numbers: "Measured: Vref 0.75 to 0.85 V; one motor turned on all four driver channels; 18 V on the meter; buck 5.00 V; fin fit; logic rail 1.14 V fault. Calculated: statics, Lewis, fin, wire drop, grip force. Simulated: control system, calibration, camera view, four-bar jaw force. Planned: hold test (motor case below 60 °C); station pull test; SolidWorks station study (SF at least 3, deflection at most 0.5 mm); 1 lb on four stations, 300 mm at 50 mm/s, within 2 mm per cable.",
    qa: [["What is the first test you would run?", "The 15-minute luggage-scale pull test at 1.06 A, empty and full spool (docs/tests/WINCH_PULL_TEST.md), because it replaces the assumed 0.7 running-torque factor: a running pull of 25 N or more at a full spool means the direct drive might carry a lighter claw, under 25 N (expected about 18 N) means the 3:1 reduction; then the hold test."],
         ["Which number are you least sure of?", "The claw mass: the budget is 0.45 kg but the printed claw is estimated at 1.05 to 1.25 kg and has not been weighed, and every capacity number rests on it."]],
    need: "Anything measured since Oct 20 (move it left); confirm each pass limit; hold-test length (60 minutes in the storyline, 90 in the fundamentals sheet).",
    src: "DECK_STORYLINE.md slide 16; FUNDAMENTALS.md 'What must still be measured'.",
  }));

  // ================================================================ 17 · Deletions and lessons
  s = pres.addSlide({ masterName: "Dark Closing", sectionTitle: SECTION.close });
  slideNo += 1; ALL_SLIDES.push({ n: slideNo, label: "17 Deletions and lessons" });
  s.addText("WHAT I DELETED, WHAT I LEARNED", { placeholder: "eyebrow" });
  s.addText("My best decisions were deletions.", { placeholder: "title" });
  {
    eyebrowLabel(s, "DELETED", M, 2.55, 4, C.text2);
    ["The IMU", "The yaw guard", "Five fingers, now two jaws", "50 mm of tube", "The housing block, now an open frame (−600 g)", "The contactor e-stop"].forEach((t, i) => {
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
  s.addNotes(notes({
    say: "My best decisions were deletions: every part I removed was a part that could not fail, so I measured, deleted, and then simplified.",
    numbers: "Deleted: the IMU (D27); the yaw guard; five fingers became two jaws; 50 mm of tube (32.5 g); the housing block replaced by an open frame (-600 g, per the storyline); a contactor e-stop replaced by the switched power strip as the only stop (D21). Lessons: measure before you trust a margin (Vref 0.85 V, 1.14 V rail); print the coupon before the part (spool bore Ø5.2 to Ø5.45; a 54-hole coupon is planned); stall and steady state are the design cases (gear stall; motor holding heat). With half the time again: buy pulleys and couplers sooner; build one station to test before four.",
    qa: [["What would you do differently?", "Buy standard pulleys and couplers instead of designing them, and build and test one complete station before building four."]],
    need: "Confirm what the 'yaw guard' was and the source of the -600 g open-frame figure (storyline only); say whether you want the contact line left on the slide.",
    src: "DECK_STORYLINE.md slide 17; DECISIONS.md D21, D27.",
  }));

  // ================================================================ Backups
  pres.addSection({ title: SECTION.back });
  function backup(n, eyebrow, title, tagList, buildFn, nt) {
    const sl = addContent(SECTION.back, `B${n} ${eyebrow}`);
    sl.addText(`BACKUP B${n} · ${eyebrow}`, { placeholder: "eyebrow" });
    sl.addText(title, { placeholder: "title" });
    if (tagList.length) tags(sl, tagList);
    buildFn(sl);
    sl.addNotes(notes(nt));
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
  }, {
    say: "The four-bar jaw gives the least force when it is closed and more than three times as much near full open, because the effective lever arm shrinks as the gap widens.",
    numbers: "Jaw force per jaw at 4.8 V from the four-bar model: 13.3 N at 0.6 mm gap, 14.1 @ 10, 15.0 @ 20, 17.2 @ 40, 21.1 @ 60, 25.0 @ 70, 33.4 @ 80, 43.6 @ 85 mm. Effective lever arm 59 / 48 / 33 mm at 10 / 40 / 70 mm gap. Jaw torque 0.83 N·m at 4.8 V (N = 2, 0.95 efficiency per mesh); stroke 76.5° from a 153° servo; open gap 91.6 mm; closed gap 0.000 mm; max jaw tilt 2.59°. Requirements: 8.9 N for 1 lb at mu 0.3, 17.7 N for 0.9 kg jeans at mu 0.3 (8.9 N at 0.6).",
    qa: [["Is there a toggle in the stroke?", "No: the gap is monotonic over the whole 76.5° stroke. Near full open the linkage approaches toggle, which is why force rises steeply there (43.6 N at an 85 mm gap)."],
         ["Is this measured?", "No. It is simulated from the model (no pivot friction, 0.95 efficiency per mesh); there is no force-gauge reading yet."]],
    src: "FUNDAMENTALS.md sections 4 and 5; verification/gripper_v7_verification.md claims 4a and 6.",
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
  }, {
    say: "The host plans the path and sends timed segments; each station executes them on its own clock, holds on any fault or lost host, and a stop never disables a motor.",
    numbers: "Segments are Hermite segments executed in each station's own clock; the host estimates each station's clock offset and refuses motion unless the clock uncertainty is within its limit. Feed-hold names a path time and the host resends it every 20 ms to any station still running, so one lost datagram cannot leave a winch running while three hold. Lease: no valid host message within the lease time and the station holds itself and broadcasts the hold to its peers. Simulated: lease-aligned stop spread about 18 ms; 10/10 lossy motions complete at 2 to 5 % packet loss. Skew pricing: 2.5 mm per 50 ms at 50 mm/s is about 7.5 N. Pass test (PLANNED): 1 lb on four stations, 300 mm at 50 mm/s, within 2 mm per cable.",
    qa: [["Why not disable the drivers on a fault?", "There is no brake, so disabling a driver drops the load. Every fault and pause holds torque; only a disarm confirmed with the claw supported removes it (D21). The power strip is the only category-0 stop and no safety-rated function is claimed."]],
    check: "Everything on this slide is simulated or by design; nothing has run on four stations yet.",
    src: "docs/CONTROL_SYSTEM_V1.md sections on clocks, feed-hold and lease; DECISIONS.md D20, D21, D25; FUNDAMENTALS.md section 9.",
  });

  // ---------------------------------------------------------------- B3 Rev D board
  backup(3, "REV D STATION BOARD", "Rev D: soldered 3.3 V, driver boots disabled, no USB-buck fight.", ["CALCULATED", "PLANNED"], (sl) => {
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
  }, {
    say: "Rev D fixes the failure from decision 14 on the board itself: the 3.3 volt rail is soldered, the driver boots disabled through a pull-up, and a link and diode keep USB and the buck from fighting.",
    numbers: "5 x 7 cm perfboard, component-side view, holes named column letter + row number. R1 10 k EN pull-up (E10-E13) so the A4988 boots disabled; R2 10 k STEP pull-down; R3 10 k DIR pull-down; R4 10 k switch pull-up. JP1 (R11-S11) with D1 1N5819 between the XIAO 5 V side and the buck output. DROK buck standing on its 5-pin header: select 5 V by bridging its 5V pad and check 5.00 V before connecting loads. 3V3 bus row 13, GND bus row 11. C1 100 µF/50 V across VMOT. J1 12 V in, J2 motor, J3 switch, J5 encoder. Layout generated and net-checked by perfboard_layout.py.",
    qa: [["Where is the schematic?", "The layout drawing is net-checked, but this backup shows the layout only; add the schematic image if you want it on the slide."]],
    check: "The as-built board still needs its meter checklist; the layout is a drawing, not a measurement.",
    need: "Schematic image (if wanted) and a photo of the built perfboard.",
    src: "docs/electrical/station_revD_20261021/PERFBOARD_LAYOUT.md and perfboard_layout.png; docs/LOCAL_STATION_CONTROL_20261004.md.",
  });

  // ---------------------------------------------------------------- B4 floor-board attitude study
  backup(4, "FLOOR-BOARD ATTITUDE STUDY", "A floor board cuts tilt noise 10×; hanging tilt still reaches 13–21°.", ["CALCULATED", "SIMULATED"], (sl) => {
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
    limitLine(sl, plotRect(rb, rl), 60, V.t08_sig_4, "Four-tag board: 1.3 mrad", { align: "right", labelW: 2.2 });
    fundBox(sl, { eq: "θ ≈ M_{v} / (W·L);   δx = σ_{θ}·L", sub: "Corner tilt grows 1.61× when L falls from 0.196 to 0.116 m (1/L law: 1.70×); 83 % then 92 % of grid points exceed 5°. Board: 0.68 mm vs 6.6 mm for one tag." }, M, 5.8, W - 2 * M, 1.05);
  }, {
    say: "A multi-tag floor board cuts the tilt noise about ten times, but the hanging claw still tilts between 13 and 21 degrees near the corners because of where its centre of mass sits.",
    numbers: "Tilt noise for one 152.4 mm tag at 0.46 / 0.6 / 0.8 / 1.0 m: 10.5 / 17.9 / 31.8 / 49.7 mrad (matches the project's Monte Carlo). Four-tag board with the camera centred over them: 1.3 mrad, 0.68 mm lever-arm error at 0.51 m (9.8 x better than 12.9 mrad, 6.6 mm). Mean of 1 / 4 / 10 / 30 frames (one tag): 12.9 / 6.5 / 4.1 / 2.4 mrad; a static 1 mrad bias still leaves 0.5 mm. Hanging tilt (force and moment balance on four straight lines, 9 x 7 grid): centre-of-mass depth 0.196 m (recorded, stale): centre 0.0°, median 8.7°, largest 12.9°, 83 % of points above 5°; 0.116 m (lumped estimate for the current head, range 0.09 to 0.14 m): median 13.8°, largest 20.7°, 92 % above 5°. Agrees with the project's attitude predictor to numerical precision at five poses.",
    qa: [["Which depth should I quote?", "Neither as final: the recorded 0.196 m belongs to the superseded v6 head; the 0.116 m estimate is a rough lumped figure. Re-extract the centre of mass from the CAD and rerun."]],
    check: "Tilt noise assumes independent Gaussian corner noise (0.3 px), fronto-parallel tags and a 520 px focal length (a camera guess); real corner noise is unmeasured.",
    src: "FUNDAMENTALS.md sections 7 and 8.",
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
      [rc("Heat spreads, mm", "left"), rc("74"), rc("2.6")],
    ], { x: tx, y: 2.45, w: tw, colW: [1.55, 1.25, tw - 2.8], rowH: 0.36, fontFace: "Calibri", objectName: "material_table" });
    plannedCard(sl, "Fin FEA after the SolidWorks study; the hold test replaces the lumped model.", tx, 4.2, tw, 1.0);
    fundBox(sl, { eq: "P_{m} = (T_{m} − T_{room}) / R_{fin} + (T_{m} − T_{shell}) / R_{ma}", sub: "Aluminium 160 vs PETG 0.2 W/m·K gives √(160 / 0.2) = 28× at equal geometry; the flange path alone is 1260× worse. Sealed-shell time constant 35 min." }, M, 5.7, W - 2 * M, 1.15);
  }, {
    say: "The motor has two ways out: through the printed shell, which is slow, and through the aluminium fin straight to room air; the fin is the parallel path that keeps the sealed case cooler.",
    numbers: "Two-node network: motor case to shell interior 12 K/W; shell interior to room 0 / 1 / 3.5 K/W for open / vented / sealed; fin as a second path from the motor case to the room, with 1 K/W contact resistance at the flange. P = 1.0625² x 1.8 = 2.03 W (R assumed); 1.5 W of electronics also heat the shell. Fin as built (0.483 mm): m = 13.5 /m, efficiency 37 %, R_fin 22.1 K/W (19.4 to 26.4 over h = 9 to 5). Drawn (3.175 mm): 74 %, 10.9 K/W. Temperatures (h = 7, 23 °C room): open 47 / 39 / 35; vented 51 / 41 / 36; sealed 64 / 46 / 40 for no fin / as built / drawn. Spreading length 74 mm in 0.48 mm aluminium vs 2.6 mm in PETG; long-fin resistance 22 K/W (0.48 mm Al) vs 182 K/W (5 mm PETG). Shell time constant 35 min: a 90-minute hold covers 92 % of the rise.",
    qa: [["Why not let the PETG mount sink the heat?", "At equal geometry aluminium conducts 28 x better (the square root of 160 / 0.2), and through the flange contact the PETG path is 14.0 K/W against 0.011 K/W (1260 x). Heat in PETG dies out within a few millimetres of the motor, so the PETG around the motor bolts climbs toward the motor temperature while it carries the cable load."]],
    check: "Coil resistance (1.8 Ω), film coefficient and shell resistances are assumptions; the fin FEA and hold test are not done.",
    need: "Fin FEA results after the SolidWorks study (this slide shows none).",
    src: "FUNDAMENTALS.md section 3.",
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
    body(sl, ["Frame 143.5 g (limit 150 g).", "Printed total 332 g; head 481 g.", "72 checks pass; no interference over the sweep.", "Open: servo ear pitch 47.0 vs 48.3 mm."], fx, 2.3, fw, 3.2, 14);
    fundBox(sl, { eq: "SF = σ_{allow} / σ;   σ = F_{t} / (b·m·Y)", sub: "σ_{allow} = 22.5 MPa. At 6 V stall F_{t} = 79.9 N: pinion 11.0 MPa, SF 2.05. Sync gear, one jaw takes all: F_{t} = 113.9 N, SF 1.997." }, M, 5.8, W - 2 * M, 1.05);
  }, {
    say: "The open-frame v7 gearbox is the alternative that replaced the housing block; at stall every gear sits at a safety factor of about two or better.",
    numbers: "Module 1.5; teeth 18 / 36 / 24 / 24; face widths 15.7 and 20 mm; PETG allowable 22.5 MPa. Safety factor at 4.8 / 6.0 V: pinion 2.40 / 2.05; 36T gear 2.93 / 2.50; 24T sync gear (one jaw takes all) 2.34 / 2.00 (1.997 at 6 V, accepted as inside the precision of the stall torque). Frame 143.5 g (78.7 + 64.8; limit 150 g); printed total 332.8 g; head 481 g with purchased parts. Rev 2 re-verification: 72 tests pass; interference over the full sweep 0.000 mm³; jaw travel 76.5°.",
    qa: [["What is still open?", "Servo ear pitch (47.0 mm in the plate vs 48.3 mm in interfaces.py) must be measured on hardware; the Ø9.7 race ring and the Ø3.3 insert hole cannot be checked from CAD; purchased fastener masses are assumed; flank clearance 0.1994 / 0.1997 mm and the 1.997 sync SF are accepted conditions."]],
    check: "The gripper_v7 render in the asset folder is marked work in progress (re-render once verified); swap in the final render if one exists. Verdict is PASS WITH CONDITIONS.",
    src: "verification/gripper_v7_verification.md (revision 2); FUNDAMENTALS.md section 4.",
  });

  // ---------------------------------------------------------------- B7 safety
  {
    const { FiPower, FiAnchor, FiUserX, FiBatteryCharging } = require("react-icons/fi");
    const icons = [await iconPng(FiPower, HEX.ink), await iconPng(FiAnchor, HEX.ink), await iconPng(FiUserX, HEX.ink), await iconPng(FiBatteryCharging, HEX.ink)];
    backup(7, "SAFETY", "Safety: one hard stop, studs only, nobody underneath.", [], (sl) => {
      const cw = (W - 2 * M - 0.75) / 4;
      [["One hard stop", "The switched power strip is the only stop. Faults and pause hold torque."], ["Studs only", "Stations anchor into wall studs; the line pulls them off the wall, so screws see pull-out."],
        ["Nobody under it", "Nobody stands under the robot while it moves."], ["Balance charging", "Charge the 2S LiPo with a matched balance charger, pack off the robot."]].forEach(([h, t], i) => {
        const x = M + i * (cw + 0.25), y = 2.1, ch = 3.4, hot = i === 0;
        sl.addShape(pres.shapes.RECTANGLE, { x, y, w: cw, h: ch, fill: { color: hot ? C.accent5 : C.background2 }, line: { color: hot ? C.accent1 : C.background2, width: hot ? 1.5 : 0.5 }, objectName: `safety_card_${i + 1}` });
        sl.addImage({ data: icons[i], x: x + 0.3, y: y + 0.3, w: 0.7, h: 0.7, altText: h, objectName: `safety_icon_${i + 1}` });
        sl.addText(h, { x: x + 0.3, y: y + 1.25, w: cw - 0.6, h: 0.45, fontSize: 19, bold: true, fontFace: "Arial", color: C.text1, margin: 0, isTextBox: true });
        sl.addText(t, { x: x + 0.3, y: y + 1.8, w: cw - 0.6, h: 1.7, fontSize: 15, color: C.text1, valign: "top", margin: 0, isTextBox: true });
      });
      sl.addText("No safety-rated function is claimed (ISO 13849 and IEC 61508 are not claimed).", { x: M, y: 5.85, w: W - 2 * M, h: 0.4, fontSize: 14, color: C.text2, margin: 0, valign: "middle", isTextBox: true });
    }, {
      say: "There is one hard stop, the switched power strip; the stations go only into studs; nobody stands under the robot; and the LiPo is balance-charged off the robot.",
      numbers: "D21: every fault and pause holds torque; only a disarm confirmed with the claw supported removes it; the power strip is the only category-0 stop; no safety-rated function is claimed (ISO 13849 / IEC 61508 not claimed). Stations: the line pulls the station away from the wall, so the stud screws see pull-out, not shear; SolidWorks study and pull test PLANNED (slide 10). No AC mains inside printed housings (CR9). Claw battery: 2S LiPo, charged with the matched external 2S balance charger with the pack removed from the robot; a protection board is not a charger.",
      qa: [["Is this a safety-rated system?", "No. It is a hobby prototype with a single hard stop (the strip) and a rule that nobody is under it; load-bearing, high-speed or energy-storage parts need qualified supervision and controlled testing before use."]],
      need: "Confirm the stud anchoring and charging statements match what you actually do, and which charger you use.",
      src: "DECISIONS.md D21; REQUIREMENTS.md CR9; docs/CLAW_ELECTRICAL_REVA_20261012.md; DECK_STORYLINE.md B7.",
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
