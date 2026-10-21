// RoomCleaner interview deck v3: v2's story and style, plus equation boxes in the corner of process slides, charts
// from the Google Sheet "RoomCleaner engineering calculations", a heat-fin length slide, a manufacturing section and a
// first-test slide.  Content contract: docs/presentation/DECK_V3_NOTES.md.  v1 and v2 are kept unchanged.
//
//   /usr/bin/python3 docs/presentation/deck_v3/sheet_charts.py     (after exporting the Sheet to deck_v3/sheet_export.pdf)
//   /usr/bin/python3 docs/presentation/deck_v3/make_figures.py
//   NODE_PATH=<pptxgenjs node_modules> APPLY_THEME=<pptx skill>/scripts/apply_theme.js \
//   SOFFICE_PY=<pptx skill>/scripts/office/soffice.py node docs/presentation/deck_v3/build_deck_v3.js
"use strict";
const path = require("path");
const { execFileSync } = require("child_process");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const P = (...p) => path.join(ROOT, ...p);
const OUT = path.join(__dirname, "RoomCleaner_Buntinx_Oct27_v3.pptx");
const { size: imgSize } = require("../deck_v2/img_size.js");
const SHEET_URL = "https://docs.google.com/spreadsheets/d/1UGFnkL1v305WnDYj5aj5zBtgxnxmGP7_TVRN0afZTGs/edit";

const THEME = {
  name: "RoomCleaner v3", headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: "1A1A1A", lt1: "FFFFFF", dk2: "1F3A5F", lt2: "F2F2F4", accent1: "1F3A5F", accent2: "8A8F98",
            accent3: "B23A2E", accent4: "4F6D8F", accent5: "D9DEE5", accent6: "5B6470", hlink: "1F3A5F", folHlink: "4F6D8F" },
};
const HEX = { ink: "1A1A1A", navy: "1F3A5F", grey: "8A8F98", mid: "5B6470", light: "F2F2F4", rule: "D9DEE5", red: "B23A2E", navy2: "4F6D8F", eq: "F5F7FA" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";                       // 13.33 x 7.5 in
pres.author = "Jasper Buntinx";
pres.title = "RoomCleaner";
pres.theme = { headFontFace: "Calibri", bodyFontFace: "Calibri" };
const W = 13.333, M = 0.6;

pres.defineSlideMaster({
  title: "CONTENT", background: { color: "FFFFFF" },
  objects: [
    { line: { x: M, y: 7.0, w: W - 2 * M, h: 0, line: { color: HEX.rule, width: 0.75 } } },
    { text: { text: "RoomCleaner  |  Jasper Buntinx", options: { x: M, y: 7.05, w: 6, h: 0.3, fontSize: 10, color: HEX.grey, fontFace: "Calibri", margin: 0 } } },
  ],
  slideNumber: { x: W - M - 0.6, y: 7.05, w: 0.6, h: 0.3, fontSize: 10, color: HEX.grey, align: "right", fontFace: "Calibri" },
});
pres.defineSlideMaster({ title: "SECTION", background: { color: HEX.navy } });
pres.defineSlideMaster({ title: "TITLE", background: { color: "FFFFFF" } });

// ------------------------------------------------------------------------------------------------ helpers
// "_x" / "_{ab}" after a letter -> subscript run; "**bold**" -> bold run.  Keeps equations readable without equation objects.
function runs(text, base) {
  const out = [];
  const re = /\*\*(.+?)\*\*|_\{([^}]+)\}|_([A-Za-z0-9]+)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push({ text: text.slice(last, m.index), options: { ...base } });
    if (m[1]) out.push({ text: m[1], options: { ...base, bold: true } });
    else out.push({ text: m[2] || m[3], options: { ...base, subscript: true } });
    last = re.lastIndex;
  }
  if (last < text.length) out.push({ text: text.slice(last), options: { ...base } });
  return out;
}
function bullets(sl, items, x, y, w, h, size = 20) {
  const arr = [];
  items.forEach((it, i) => {
    const sub = it.startsWith("- ");
    const t = sub ? it.slice(2) : it;
    const base = { fontSize: sub ? size - 3 : size, color: sub ? HEX.mid : HEX.ink, fontFace: "Calibri" };
    const para = { bullet: sub ? { indent: 18 } : { indent: 20 }, indentLevel: sub ? 1 : 0, paraSpaceAfter: sub ? 4 : 9 };
    const rs = runs(t, { ...base, ...para, align: "left" });   // paragraph options on every run: pptxgenjs takes them from the last run
    rs.forEach((r, j) => { r.options.breakLine = j === rs.length - 1 && i < items.length - 1; });
    arr.push(...rs);
  });
  // align on the box: pptxgenjs then splits paragraphs only at breakLine (not at every run that carries `bullet`)
  sl.addText(arr, { x, y, w, h, valign: "top", align: "left", margin: [2, 4, 2, 0], isTextBox: true, objectName: "bullets" });
}
// Equation box: small, boxed, bottom-left of the slide; the bullets tell the story, the box holds the maths.
const EQ_LINE = 0.34;
const eqHeight = eq => 0.44 + EQ_LINE * eq.lines.length + (eq.note ? 0.26 : 0);
function eqBox(sl, eq, x, y, w) {
  const h = eqHeight(eq);
  sl.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.06, fill: { color: HEX.eq }, line: { color: HEX.rule, width: 0.75 }, objectName: "equation box" });
  sl.addText("EQUATIONS", { x: x + 0.18, y: y + 0.1, w: w - 0.36, h: 0.22, fontSize: 10, bold: true, color: HEX.navy, charSpacing: 1.5,
                            fontFace: "Calibri", margin: 0, isTextBox: true, objectName: "equation label" });
  const arr = [];
  eq.lines.forEach((ln, i) => {
    const rs = runs(ln, { fontSize: 15, color: HEX.ink, fontFace: "Cambria", paraSpaceAfter: 4, align: "left" })
      .flatMap(r => r.text.split(/(→)/).filter(Boolean).map(t => ({ text: t, options: t === "→" ? { ...r.options, fontFace: "Calibri" } : { ...r.options } })));   // own copy: breakLine is set per run
    rs.forEach((r, j) => { r.options.breakLine = j === rs.length - 1 && i < eq.lines.length - 1; });
    arr.push(...rs);
  });
  sl.addText(arr, { x: x + 0.18, y: y + 0.36, w: w - 0.36, h: EQ_LINE * eq.lines.length + 0.02, valign: "top", align: "left", margin: 0,
                    isTextBox: true, objectName: "equations" });
  if (eq.note) sl.addText(eq.note, { x: x + 0.18, y: y + h - 0.33, w: w - 0.36, h: 0.24, fontSize: 10.5, italic: true, color: HEX.grey,
                                     fontFace: "Calibri", margin: 0, isTextBox: true, objectName: "equation source" });
}
function fitImage(sl, file, x, y, w, h, alt, opts = {}) {
  const { w: iw, h: ih } = imgSize(file);
  const s = Math.min(w / iw, h / ih), dw = iw * s, dh = ih * s;
  const dx = x + (opts.alignLeft ? 0 : (w - dw) / 2), dy = y + (opts.alignTop ? 0 : (h - dh) / 2);
  sl.addImage({ path: file, x: dx, y: dy, w: dw, h: dh, altText: alt, objectName: alt.slice(0, 40) });
  return { x: dx, y: dy, w: dw, h: dh };
}
function caption(sl, text, x, y, w) {
  sl.addText(text, { x, y, w, h: 0.32, fontSize: 12, italic: true, color: HEX.grey, fontFace: "Calibri", margin: 0, isTextBox: true, objectName: "caption" });
}
// Chart made in the Google Sheet, cropped from its PDF export by sheet_charts.py.
function sheetChart(sl, name, tab, x, y, w, h) {
  const r = fitImage(sl, path.join(__dirname, "fig", `sheet_${name}.png`), x, y, w, h - 0.42, `Chart from the calculation sheet: ${tab}`, { alignTop: true });
  sl.addShape(pres.shapes.RECTANGLE, { x: r.x, y: r.y, w: r.w, h: r.h, fill: { type: "none" }, line: { color: HEX.rule, width: 0.75 }, objectName: "chart frame" });
  caption(sl, `Expected values: my calculation sheet (Google Sheets), “${tab}” tab`, r.x, r.y + r.h + 0.08, Math.max(r.w, 4.5));
  return r;
}
function head(sl, section, title) {
  sl.addText(section.toUpperCase(), { x: M, y: 0.32, w: 9, h: 0.3, fontSize: 12, bold: true, color: HEX.navy, charSpacing: 1.5,
                                      fontFace: "Calibri", margin: 0, isTextBox: true });
  sl.addText(title, { x: M, y: 0.62, w: W - 2 * M, h: 0.75, fontSize: 30, bold: true, color: HEX.ink, fontFace: "Calibri",
                      margin: 0, valign: "middle", isTextBox: true });
}
let SECTION_NAME = "";
function section(num, title, sub) {
  SECTION_NAME = title;
  pres.addSection({ title });
  const sl = pres.addSlide({ masterName: "SECTION", sectionTitle: title });
  sl.addText(String(num).padStart(2, "0"), { x: M, y: 2.2, w: 3, h: 1.2, fontSize: 60, bold: true, color: "8FA6C2", fontFace: "Calibri", margin: 0, isTextBox: true });
  sl.addText(title, { x: M, y: 3.35, w: 11.5, h: 1.0, fontSize: 40, bold: true, color: "FFFFFF", fontFace: "Calibri", margin: 0, isTextBox: true });
  if (sub) sl.addText(sub, { x: M, y: 4.35, w: 11.5, h: 0.8, fontSize: 20, color: "D9DEE5", fontFace: "Calibri", margin: 0, isTextBox: true });
  sl.addNotes(sub || title);
  return sl;
}
function frame(sl, f, x, y, w, h, alt) {
  sl.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: HEX.light }, line: { color: HEX.light } });
  fitImage(sl, f, x + 0.06, y + 0.06, w - 0.12, h - 0.12, alt);
}
// Standard content slide: bullets left (equation box under them if given), one visual right.
function content(title, items, visual, notes, opts = {}) {
  const sl = pres.addSlide({ masterName: "CONTENT", sectionTitle: SECTION_NAME });
  head(sl, opts.section || SECTION_NAME, title);
  const split = opts.split || 0.52;
  const bw = (W - 2 * M) * split - 0.2;
  const eqH = opts.eq ? eqHeight(opts.eq) : 0;
  bullets(sl, items, M, 1.6, bw, opts.eq ? 5.25 - eqH - 0.2 : 5.2, opts.size || (opts.eq ? 18 : 20));
  if (opts.eq) eqBox(sl, opts.eq, M, 6.85 - eqH, bw);
  const vx = M + bw + 0.45, vw = W - M - vx, vy = 1.6, vh = 5.25;
  if (typeof visual === "function") visual(sl, vx, vy, vw, vh);
  else if (visual && visual.sheet) sheetChart(sl, visual.sheet, visual.tab, vx, vy + 0.1, vw, vh - 0.1);
  else if (visual && visual.grid) {
    const g = 0.12, cw = (vw - g) / 2, ch = (vh - 0.4 - g) / 2;
    visual.grid.forEach((f, i) => frame(sl, f, vx + (i % 2) * (cw + g), vy + Math.floor(i / 2) * (ch + g), cw, ch, visual.alt || path.basename(f)));
    if (visual.caption) caption(sl, visual.caption, vx, vy + vh - 0.32, vw);
  } else if (visual) {
    const files = Array.isArray(visual.file) ? visual.file : [visual.file];
    const gap = 0.15, each = (vw - gap * (files.length - 1)) / files.length, fh = vh - 0.3;
    files.forEach((f, i) => frame(sl, f, vx + i * (each + gap), vy, each, fh, visual.alt || path.basename(f)));
    if (visual.caption) caption(sl, visual.caption, vx, vy + fh + 0.08, vw);
  }
  sl.addNotes(notes || "");
  return sl;
}
// Startup calibration as native shapes: two rows of three, the second row running back right to left.
function calFlow(sl, x, y, w, h) {
  const steps = ["Take up slack, one cable at a time", "Lift the claw off the floor", "Camera reads the floor board",
                 "Fit anchors and cable lengths", "Check on held-out poses", "Ready, inside the safe margins"];
  const gx = 0.34, gy = 0.34, bw = (w - 2 * gx) / 3, bh = (h - gy) / 2;
  const pos = i => (i < 3 ? { x: x + i * (bw + gx), y } : { x: x + (5 - i) * (bw + gx), y: y + bh + gy });
  steps.forEach((s, i) => {
    const p = pos(i), last = i === steps.length - 1;
    sl.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: p.x, y: p.y, w: bw, h: bh, rectRadius: 0.08, fill: { color: last ? HEX.navy : "FFFFFF" },
                                                 line: { color: HEX.navy, width: 1.25 }, objectName: `calibration step ${i + 1}` });
    sl.addText([{ text: `${i + 1}  `, options: { bold: true, color: last ? "FFFFFF" : HEX.navy } }, { text: s, options: { color: last ? "FFFFFF" : HEX.ink } }],
               { x: p.x + 0.08, y: p.y, w: bw - 0.16, h: bh, fontSize: 14, fontFace: "Calibri", valign: "middle", align: "center", margin: 0, isTextBox: true });
  });
  const arrow = (ax, ay, aw, ah, flipH) => sl.addShape(pres.shapes.LINE, { x: ax, y: ay, w: aw, h: ah, flipH, line: { color: HEX.grey, width: 1.5, endArrowType: "triangle" } });
  arrow(x + bw + 0.05, y + bh / 2, gx - 0.1, 0); arrow(x + 2 * bw + gx + 0.05, y + bh / 2, gx - 0.1, 0);
  arrow(x + 2.5 * (bw) + 2 * gx, y + bh + 0.05, 0, gy - 0.1);
  arrow(x + 2 * bw + gx + 0.05, y + bh + gy + bh / 2, gx - 0.1, 0, true); arrow(x + bw + 0.05, y + bh + gy + bh / 2, gx - 0.1, 0, true);
}

const R = f => P("docs/presentation/deck_assets/renders", f);
const PH = f => P("docs/presentation/photos", f);
const FG = f => path.join(__dirname, "fig", f);

// ================================================================================================ 1 title
{
  pres.addSection({ title: "Opening" }); SECTION_NAME = "Opening";
  const sl = pres.addSlide({ masterName: "TITLE", sectionTitle: "Opening" });
  sl.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 5.6, h: 7.5, fill: { color: HEX.navy }, line: { color: HEX.navy } });
  sl.addText("RoomCleaner", { x: M, y: 2.3, w: 4.8, h: 1.0, fontSize: 44, bold: true, color: "FFFFFF", fontFace: "Calibri", margin: 0, isTextBox: true });
  sl.addText("A four-cable ceiling robot that picks laundry off the floor", { x: M, y: 3.35, w: 4.6, h: 1.2, fontSize: 20, color: "D9DEE5", fontFace: "Calibri", margin: 0, isTextBox: true });
  sl.addText("Jasper Buntinx\nTechnical presentation  ·  October 27, 2026", { x: M, y: 6.0, w: 4.8, h: 0.8, fontSize: 14, color: "D9DEE5", fontFace: "Calibri", margin: 0, isTextBox: true });
  fitImage(sl, R("gripper1021_final.png"), 6.0, 0.4, 3.2, 6.7, "Final claw: electronics housing with camera bay, tube and gripper");
  fitImage(sl, PH("13_gen1_station_lifting_test_weight.jpg"), 9.4, 0.9, 3.4, 5.7, "Gen-1 winch station lifting a test weight");
  sl.addNotes("One sentence: a cable robot whose four winches sit in the ceiling corners and move one claw anywhere over the floor.");
}

// ================================================================================================ 2-3 goal, outline
content("Goal and constraints", [
  "Pick clothes off the floor and drop them in a hamper, from anywhere in the room",
  "Four winches near the ceiling corners hold one claw on four cables",
  "Room 11 × 9 ft with a 9 ft ceiling",
  "Working load: a pair of jeans (0.9 kg) with 2 m/s² of acceleration; first test load 1 lb",
  "3D-printed in PETG on a hobby budget, from parts I can buy and fix myself",
  "Safety: anchors in studs, one hard stop (the switched power strip), nobody under the robot",
], { file: R("station_v3_assembly.png"), alt: "Winch station assembly", caption: "One of the four winch stations (CAD)" },
"Requirements first: where it works, what it lifts, what it costs, and how it stays safe.");

{
  const sl = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Opening" });
  head(sl, "Opening", "Outline");
  const items = [["How a cable robot works", "Position vectors, statics, the winch"],
                 ["From one box to modular stations", "Wiring, a controller per winch, the slide-in housing, plug-in power, cooling and the horn-inspired fin"],
                 ["Homing and calibration", "Bead homing, why it limited the motion, the camera-based method"],
                 ["The claw", "Gripper evolution, the four-bar hands, overhead camera to claw camera, weight vs lift"],
                 ["Manufacturing", "Printed PETG parts, and a heat fin cut and drilled on a manual mill"],
                 ["Electronics and software", "Station board, bring-up, control and the phone app"],
                 ["Status and next steps", "First test, what is built, what I learned"]];
  items.forEach(([t, s], i) => {
    const y = 1.6 + i * 0.75;
    sl.addText(String(i + 1), { x: M, y, w: 0.6, h: 0.6, fontSize: 24, bold: true, color: HEX.navy, fontFace: "Calibri", margin: 0, isTextBox: true });
    sl.addText(t, { x: M + 0.7, y: y - 0.02, w: 10, h: 0.38, fontSize: 21, bold: true, color: HEX.ink, fontFace: "Calibri", margin: 0, isTextBox: true });
    sl.addText(s, { x: M + 0.7, y: y + 0.34, w: 10, h: 0.32, fontSize: 15, color: HEX.mid, fontFace: "Calibri", margin: 0, isTextBox: true });
  });
  sl.addNotes("The talk follows the order the problems appeared in.");
}

// ================================================================================================ section 1
section(1, "How a cable robot works", "Four cables, one point, and the vectors that connect them");

content("Position vectors", [
  "Room frame at a floor corner: anchor i (the pulley exit) at **a**_i, the claw at **p**",
  "Each cable is the vector from the claw to its anchor",
  "Its length is the distance between those two points",
  "To move, compute the four lengths at every point on the path",
  "Each spool turns by the change in length over its radius",
  "Closed form: no iteration is needed to command a move",
], { file: FG("position_vectors.png"), alt: "Position vectors from four anchors to the claw" },
"Inverse kinematics of a cable robot is vector subtraction and a norm, done for each cable at every step.",
{ split: 0.56, eq: { lines: [
  "**l**_i = **a**_i − **p**,   **u**_i = **l**_i / L_i",
  "L_i = ‖**a**_i − **p**‖ = √((a_{ix} − p_x)² + (a_{iy} − p_y)² + (a_{iz} − p_z)²)",
  "Δθ_i = ΔL_i / r   (r = spool radius with the wound line)",
] } });

content("Statics: why cable angle matters", [
  "Force balance: the cable pulls and the weight sum to zero",
  "Cables only pull: every tension must stay positive",
  "Centred claw, equal shares: tension rises as the cables flatten",
  "32 N per cable 0.15 m below the anchors; 8.3 N at 0.6 m",
  "At 0.4 m: 12.2 N, right at the 11.9 N design force",
  "So the robot keeps 0.4 m below the anchors, 0.2 m from the walls",
], { sheet: "cable_tension", tab: "Cable tension" },
"D_h = 2.17 m from the room centre to a corner. The tension doubles each time the depth halves near the ceiling; the ceiling margin is set by tension, not by collision.",
{ eq: { lines: [
  "Σ T_i **u**_i + m(**g** + **a**) = **0**,   T_i > 0",
  "T = W / (4 sin φ),   sin φ = d / √(d² + D_h²)",
  "W = (0.45 + 0.454) kg × 9.81 m/s² = 8.87 N",
] } });

content("The winch", [
  "NEMA 17 stepper, printed spool, outlet pulley",
  "Current limit set by the driver's reference voltage: 0.85 V → 1.06 A",
  "Running torque < holding torque: 0.7 assumed, the pull test measures it",
  "Smaller spool: more pull per amp, more turns per metre",
  "v3 spool: 24 N empty, 18 N full → 11.9 N design (÷ 1.5)",
], { sheet: "winch_pull", tab: "Winch pull" },
"Design force = full-spool pull / 1.5 skip margin. The pull test turns the 0.7 ratio into a measurement.",
{ eq: { lines: [
  "I = V_ref / (8 R_s) = 0.85 V / (8 × 0.1 Ω) = 1.06 A",
  "τ_run = 0.7 · τ_hold · I / I_rated = 0.7 × 0.36 × 1.06 / 1.5 = 0.18 N·m",
  "T = τ_run / r:   23.8 N at r = 7.5 mm,   17.9 N at r = 10 mm",
], note: "Current limit: Allegro MicroSystems, A4988 datasheet" } });

// ================================================================================================ section 2
section(2, "From one box to modular stations", "How adding safety features changed the whole architecture");

content("First idea: one central controller", [
  "One Arduino Uno and a CNC shield with four A4988 drivers, in a single box",
  "The computer sends moves; the shield steps all four motors from one clock, so sync is free",
  "Each motor gets a long 4-wire cable from the box to its corner",
  "It worked on the bench: a gen-1 station lifted a test weight",
], { file: [PH("14_gen1_cnc_shield_a4988.jpg"), PH("05_gen1_spool_plate.jpg")], alt: "Gen-1 CNC shield and spool plate", caption: "Gen 1: central shield with four drivers; spool plate on the wall" },
"Simple and synchronised by design. It only stopped working once I wanted more than a motor at each corner.");

content("Why it did not scale: the wiring", [
  "I wanted more safety: a homing switch and an encoder at every winch, plus fault detection",
  "Per corner: motor 4 + switch 2 + encoder 4 = **10 conductors**, not 4",
  "Real cable routes are 6, 21, 23 and 32 ft (82 ft)",
  "The encoder's I²C bus is meant for centimetres, not 10 m runs",
  "Motor phase currents in long cables also radiate noise into the sensor lines",
], { sheet: "wiring", tab: "Wiring" },
"The wire count, not the motors, was the problem. 18 AWG on the same run drops 0.82 V.",
{ eq: { lines: [
  "Conductor = n · ΣL:   10 × 82 ft = 820 ft   vs   2 × 82 ft = 164 ft",
  "ΔV = I · R′ · 2L = 2 A × 4.016 mΩ/ft × 64 ft = 0.51 V",
], note: "16 AWG on the longest run (32 ft); 2 A is illustrative" } });

content("Decision: a controller in every winch", [
  "Each station: XIAO ESP32-C3 + A4988 driver + 5 V buck; only 12 V power travels, on 2 wires",
  "Switch and encoder wires stay inside the station, a few centimetres long",
  "The host computer plans the path and sends each station timed segments over Wi-Fi",
  "Each station runs its segments on its own clock; any lost link → hold position",
  "Cost: timing skew between stations becomes cable mismatch, so segments are time-stamped",
  "Benefit: about 5× less wire, and every station can be built and tested alone",
], { file: [PH("11_gen2_station_assembled.jpg"), PH("09_homing_switch_perfboard.jpg")], alt: "Gen-2 station and its electronics", caption: "Gen 2: the station carries its own controller, driver and buck" },
"Sync moved from wiring into software: time-stamped segments and a host that keeps every station's clock.",
{ eq: { lines: ["Δx = v · Δt = 50 mm/s × 50 ms = 2.5 mm of cable mismatch"] } });

content("Making the units modular", [
  "Gen 1 was a plate screwed into the wall: fine for a bare motor",
  "Each corner now carries a controller, driver, buck, switch and encoder",
  "- they need protection, a clean look and a path for heat",
  "So each station became a housing: motor, spool, pulley and electronics in one unit",
  "Same unit in all four corners: build one, test one, copy it",
], { file: [R("gen1_corner_mount.png"), R("shell_v3.png")], alt: "Gen-1 corner plate vs gen-2 housing", caption: "Gen-1 corner plate (left) vs the gen-2 station housing (right)" },
"Once there are electronics in every corner, the wall plate becomes a product housing.");

content("Slide-in mount", [
  "I take stations down often: to test, rework, repair or modify them",
  "Drilling in and out each time damages the wall and moves the anchor point",
  "A fixed wall frame goes into a stud once; the station slides in and locks",
  "Pull it out, rework it, slide it back: the frame keeps the anchor position",
  "Load: the line pulls the station away from the wall (pull-out and prying)",
  "- design target: SF 3 at 34 N; SolidWorks study planned",
], { file: [R("wall_mount_v3.png"), R("slipin_v3.png")], alt: "Wall frame and slide-in piece", caption: "Fixed wall frame (left) and the slide-in piece (right)" },
"34 N is the snag case: holding torque at the empty spool. The study checks stress below 8.3 MPa (derated PETG / 3) and deflection at the cable exit.",
{ eq: { lines: ["SF = σ_allow / σ_max ≥ 3  →  σ_max ≤ 25 MPa / 3 = 8.3 MPa"], note: "Allowable: derated PETG yield, 25 MPa" } });

content("Self-calibration: set it up anywhere", [
  "Every time the stations go back up, the robot measures its own geometry",
  "- no tape measure, no numbers typed in, nothing for a user to get wrong",
  "The claw camera reads a printed floor board (a grid of tags) to get the claw's pose",
  "The robot moves through a set of poses and fits the anchor positions and cable lengths by least squares",
  "Works in any room the cables can reach, so it can become a consumer product",
], (sl, x, y, w, h) => {
  calFlow(sl, x, y + 0.1, w, 2.3);
  frame(sl, R("gripper1021_final.png"), x, y + 2.7, w, h - 3.0, "Claw with camera bay");
  caption(sl, "Startup calibration; the claw camera looks straight down at the board", x, y + h - 0.25, w);
}, "Simulated so far; the hardware run is the first test.");

content("Plug-in power", [
  "Each station has one cable: a 16 AWG pair from a fused 12 V supply",
  "Plug in to use; unplug and store the cables when the robot is not needed",
  "Stations slide off the wall frames if wanted",
  "Runs cut at 9, 24, 26 and 35 ft (94 ft of a 100 ft roll), a fuse per branch at the supply",
  "The motor stays wired inside the station, so it is never unplugged under power",
  "The switched power strip is the one hard stop",
], { file: [PH("10_buck_converter_wiring.jpg"), PH("08_bench_wiring_b.jpg")], alt: "Station power wiring", caption: "Inside a station: the buck converter and its wiring; only 12 V comes in" },
"Unplugging a motor from an energised A4988 can kill the driver, so the plug carries only 12 V.");

content("Cooling", [
  "A sealed printed housing traps the motor's heat",
  "- PETG at the loaded motor mount softens and creeps: 60 °C limit",
  "Fix: vents, plus an aluminium fin straight up through the shell",
  "Model: motor → shell air → room, the fin a second path out",
  "At 1.06 A: sealed 64 °C without the fin, 46 °C with it",
  "A 90-min hold test will measure it",
], { sheet: "motor_temperature", tab: "Motor temperature" },
"The fin carries about half the heat in the sealed case. PETG softens near 80 °C. Inputs are assumptions until the hold test: 1.8 Ω per phase, 1.5 W of electronics.",
{ eq: { lines: [
  "P_m = I² R = (1.06 A)² × 1.8 Ω = 2.0 W",
  "ΔT = q · R_th   (heat flow × thermal resistance)",
  "Fin in parallel with the shell:  1/R = 1/R_shell + 1/R_fin",
] } });

content("Bio-inspired fin: antelope horns", [
  "Idea from my bio-inspired design class: antelope horns",
  "A horn is a heat exchanger: warm blood flows into its core, heat leaves through the surface",
  "The fin copies that: one tall, thin blade rising straight up from the heat source",
  "- heat conducts up from the motor and leaves along the length; the tip runs cooler, like a horn's",
  "Vertical, so warm air rises freely off both faces",
  "Motor width (44 mm): adds height, not width, to the station",
], { file: [PH("16_heat_fin_on_motor_straight.jpg"), PH("18_heat_fin_on_motor_closeup.jpg")], alt: "Heat fin on the motor", caption: "The fin on the motor: one tall blade rising from the heat source" },
"Background (not on the slide): Taylor's goat experiments found a dense blood supply under the horn sheath and estimated horns carry 1-15 % of the animal's heat loss; Picard et al. found climate-dependent horn structure in bovids. The next slide sizes the length.",
{ eq: { lines: [
  "Horn and fin both shed heat by convection:  q = h · A · (T_s − T_{∞})",
  "Tall and thin: large area for little mass,  A = 2 w L",
] } });

content("Heat fin: how much length is useful", [
  "The far end runs cooler, so each extra mm does less",
  "**0.019 in sheet (built):** 95 % of a long fin's heat by **136 mm**",
  "**1/8 in plate (drawn):** 95 % by **349 mm**",
  "Built 200 mm above the cover: past 136 mm the sheet adds < 5 %",
  "Looks: horn-like, straight up at motor width (44 mm), matte black",
  "- black radiates more than bare aluminium",
], { sheet: "heat_fin", tab: "Heat fin" },
"Efficiency at the built length: 37 % (sheet) vs 74 % (plate); fin resistance 22.1 vs 10.9 K/W. The 200 mm length was sized for the 1/8 in plate; the thin sheet would do the same job at about 140 mm.",
{ eq: { lines: [
  "m = √(2h / (k t)),   η = tanh(mL) / (mL)",
  "95 % length:  tanh(mL) = 0.95  →  L = 1.83 / m",
  "k = 160 W/m·K, h = 7 W/m²·K, t = 0.48 mm → 136 mm",
], note: "Fin equations: Incropera et al., Fundamentals of Heat and Mass Transfer, ch. 3" } });

// ================================================================================================ section 3
section(3, "Homing and calibration", "Why the first homing plan limited the robot, and what replaced it");

content("First plan: bead homing", [
  "A bead on each cable trips a switch at the outlet → a known cable length",
  "The robot zeroes itself from that: set it up anywhere",
  "I expected that to be enough, possibly even without encoders",
  "Detail fixed early: the switch moved below the pulley, so the bead never rides over the pulley groove",
], { file: PH("09_homing_switch_perfboard.jpg"), alt: "Homing switch on the bench", caption: "KW12-3 homing switch on the bench" },
"The idea was a cheap absolute reference per cable.");

content("The problem: beads limit the motion", [
  "A bead cannot pass the outlet, so a cable can never be shorter than its homing length",
  "To home all four at one point, each bead sits at that point's length",
  "- then the claw can never get closer to any anchor than from that point",
  "Homing at the room centre 1 m up → about 5 % of the working volume reachable; 2 m up → about 29 %",
  "And vision alone knows cable length to ~20–25 mm, while a bead allows ~12 mm of overtravel: a bead search was not safe either",
], { sheet: "bead_homing", tab: "Bead homing" },
"Calculated over the working volume with 0.2 m wall and 0.4 m ceiling margins. This tradeoff is physical: software cannot remove it.",
{ eq: { lines: [
  "L_i(**p**) ≥ L_{i,home} = ‖**a**_i − **p**_{home}‖   for every cable i",
  "Reachable: every cable at or above its homing length",
] } });

content("New calibration: camera, floor board and margins", [
  "Startup: take up slack one cable at a time, lift, then look at the floor board from several poses",
  "Least-squares fit of the anchor positions and cable zero lengths; held-out poses check the fit",
  "Safety comes from margins, not precision",
  "- 0.4 m below the anchors and 0.2 m inside the walls unless the error bars allow more",
  "Beads stay as end-of-travel safety switches; encoders watch for lost steps",
], (sl, x, y, w, h) => {
  calFlow(sl, x, y + 0.3, w, 3.2);
  sl.addText("If the fit is not good enough: more poses, then fit again", { x, y: y + 3.7, w, h: 0.35, fontSize: 14, italic: true, color: HEX.mid,
                                                                           fontFace: "Calibri", align: "center", margin: 0, isTextBox: true });
}, "The robot only unlocks the full workspace when k × σ fits inside the margin; otherwise it stays local. Simulated so far.",
{ eq: { lines: [
  "min over **a**_i, L_{i0}:   Σ_k Σ_i ( L_{i0} + d_{ik} − ‖**a**_i − **p**_k‖ )²",
  "Full workspace only if k · σ ≤ margin",
], note: "d: cable paid out at pose k (encoder);  p: claw position from the camera" } });

content("Why a floor board", [
  "Angle error becomes position error through the lever arm",
  "One tag: 12.9 mrad × 0.51 m ≈ 6.6 mm per frame",
  "Four tags in view: about 0.7 mm",
  "The board is a printed grid at 250 mm pitch: cheap, and it works in any room",
  "Averaging frames helps only with random noise, not with a fixed bias",
], { sheet: "floor_board", tab: "Floor board" },
"Two tags: 4.85 mrad → 2.5 mm. Noise model: 0.3 px corner noise, 520 px focal length (camera not yet calibrated).",
{ eq: { lines: ["δx = σ_{θ} · L = 12.9 mrad × 0.51 m = 6.6 mm"] } });

// ================================================================================================ section 4
section(4, "The claw", "From fingers to a parallel-jaw gripper");

content("Claw evolution", [
  "Five tendon-driven TPU fingers → a geared clamp → a lighter open frame → the final parallel-jaw gripper",
  "Each step fixed a problem I found:",
  "- the first clamp's jaws could not pinch thin fabric",
  "- the v6 clamp was about 4.6× its mass budget",
  "- v7 cut the gearbox frame to 143 g",
  "Final: my gear housing and arms, with hands designed to fit them",
], { file: [R("gen1_tentacle_claw.png"), R("claw_v6.png"), R("gripper_v7.png"), R("gripper1021_head.png")], alt: "Claw generations", caption: "Fingers, v6 clamp, v7 open frame, final gripper" },
"Mass drove most of the changes; every gram of claw is a gram of laundry the winches cannot lift.", { split: 0.44 });

content("Final gripper: gears and four-bar hands", [
  "Servo → 18T pinion → 36T/24T compound → 24T sync gear: mirror-image jaws",
  "Each hand: gear crank (53 mm) + swing arm (50 mm), a near-parallelogram four-bar",
  "- jaws stay parallel within about 1° over the stroke",
  "53 mm opening; closing drops the tips ~38 mm: a scoop",
  "Gear teeth at servo stall: safety factor about 2",
  "Swept in CAD: no collisions from open to closed",
], { file: P("renders/gripper1021/hands_on_mechanism_poses.png"), alt: "Hands on the four-bar at open, mid and closed",
     caption: "Hands on the linkage: open, mid, closed" },
"Four-bar: ground 36.5, crank 53, rocker 50, coupler 34.7 mm. Lewis: module 1.5, PETG allowable 22.5 MPa.",
{ split: 0.5, eq: { lines: [
  "Gear ratio i = 36 / 18 = 2   (servo → crank)",
  "Grip: 2 μ N ≥ m g  →  N ≥ 7.4 N per jaw   (1 lb, μ = 0.3)",
  "Lewis: σ = F_t / (b m Y),   F_t = 2τ / d",
] } });

content("First setup: an overhead camera", [
  "One camera on the ceiling, looking straight down and framing the whole floor",
  "A detector that works from words (YOLO-World) finds “sock”, “towel”, “t-shirt” with no training",
  "Each item's bottom-centre pixel, where it meets the floor, becomes a floor position",
  "- straight-down camera: scale by the room size; tilted camera: a homography from four taped floor points",
  "The claw then flies to that point and grabs",
  "The camera board sat in a printed ceiling case: shell plus a screw-on lens bezel",
], { file: R("gen1_overhead_camera.png"), alt: "Gen-1 overhead camera case", caption: "Gen-1 ceiling camera case: shell and lens bezel (45 g PETG)" },
"Gen 1 found laundry from above and mapped it to the floor; the claw only had to go there.",
{ eq: { lines: [
  "Straight down:  x = u · W / w_{img},   y = v · D / h_{img}",
  "Tilted:  (x, y, 1) ∝ **H** · (u, v, 1),   **H** fitted from 4 floor points",
], note: "u, v: pixel;  W × D: floor size;  w × h: image size in pixels" } });

content("Moving the camera to the claw", [
  "The overhead camera was one more device to mount, wire and calibrate in every room",
  "The claw and cables hide the spot right where it grasps: it cannot see the grip",
  "Its floor map assumes a flat floor, but a pile of clothes has height",
  "Now: a XIAO ESP32-S3 Sense camera in a bay in the claw's housing, looking straight down the tube",
  "One camera, two jobs: it guides the grasp up close and reads the floor board for calibration",
  "Cost: it sees less of the room at once, so the robot scans by moving",
], { file: R("gripper1021_final.png"), alt: "Claw with camera bay", caption: "Camera bay on the electronics housing (cover in navy)" },
"Sees the grasp spot from about 17 cm; at contact the jaws hide it, so the last view guides the final approach. The gen-1 camera case and its software are kept in the repository.");

content("Weight vs lift: where it stands", [
  "Driver limit 1.06 A → running pull ≈ 18–24 N per winch (full vs empty spool)",
  "- about 1.1 kg total lift at the worst point in the room",
  "The claw is not weighed yet: CAD says ~0.76 kg printed, plus a 0.1 kg battery",
  "With jeans that is above the capacity today: this is the open problem",
  "Options: lighten the claw, a 3:1 winch reduction (~2.7× pull), or a lighter demo load",
  "- next step: a luggage-scale pull test on one station decides",
], { sheet: "lift_budget", tab: "Lift budget" },
"Honest status: the numbers say the current claw plus jeans is too heavy. The pull test turns the 0.7 running-torque assumption into a measurement.",
{ eq: { lines: [
  "Σ T_i u_{iz} = m (g + a),   0 < T_i ≤ 11.9 N   (worst point in the room)",
  "m_claw ≈ f ρ V + m_tube + m_servo = 0.55 × 927 g + 198 g + 55 g ≈ 0.76 kg",
] } });

// ================================================================================================ section 5
section(5, "Manufacturing", "Printed PETG parts, and a heat fin cut and drilled on a manual mill");

content("Designing parts to be printed", [
  "PETG on a Creality K1 (0.4 mm nozzle, 0.2 mm layers); PLA creeps under load",
  "Orientation: flat face on the bed, loads along the layers, no supports on mating faces",
  "Printed holes come out undersize (bead rounding, shrink, first-layer squash)",
  "- so fits get a lead-in: 687 bearing pocket Ø14.075 with a Ø14.000 entry lip",
  "Heat-set M3 inserts where screws are reused",
  "Fewer parts: camera bay printed into the housing",
], { file: [PH("04_gen2_station_shells.jpg"), PH("20_slicer_creality_k1_petg.jpg")], alt: "Printed shells and the slicer", caption: "Printed PETG station shells; slicing the plate for the K1" },
"Every printed interface is chosen for how it prints and how I can measure it, not just how it looks in CAD.",
{ split: 0.56, eq: { lines: [
  "Clearance c = (D_hole − u) − D_shaft,   u = printer undersize",
  "Spool: Ø5.2 too tight → u ≥ 0.2 mm, so Ø5.45 gives c ≈ 0.25 mm",
] } });

content("Print, measure, adjust: the spool", [
  "v1: longer than the motor shaft could engage, so it was shortened",
  "v2: the Ø5.2 bore printed too tight on the 5 mm shaft",
  "v3: bore opened to Ø5.45 with a D-flat; the set screw on the flat carries the torque",
  "Ø15 core and 16 mm drum: 20 ft of line in 5 layers with 8 mm of flange margin",
  "Next: a fit coupon before every new interface, measured with calipers",
], { file: [R("spool_v1.png"), R("spool_v2.png"), R("spool_v3.png")], alt: "Spool v1, v2, v3", caption: "Spool v1, v2, v3 (CAD)" },
"The bore fit only locates the spool; torque goes through the set screw on the flat.", { split: 0.5 });

content("Machining the heat fin", [
  "Shop drawing first: a 1:1 US Letter print with a hole template and inch dimensions",
  "Sheared the blank from 0.019 in aluminium sheet: 44 × 250 mm (±0.5)",
  "Manual mill, one setup: all five holes located from the bottom and left edges",
  "- 7/8 in pilot for the motor boss and 4 × Ø3.4 on the 31 mm motor square, ±0.1 mm to each other",
  "Deburred, then matte black paint except the motor contact square; thermal paste there",
  "Test fit on the NEMA 17: boss centred, all four screws lined up",
], { grid: [PH("06_shear_with_drawings_and_blanks.jpg"), PH("03_mill_setup_with_shop_drawing.jpg"), PH("02_mill_drilling_fin.jpg"), PH("15_heat_fin_finished_part.jpg")],
     alt: "Fin manufacturing photos", caption: "Shear and blanks, mill setup with the drawing, drilling, the finished fin" },
"One setup from the same two edges means hole-to-hole errors do not stack, so the fin bolts on without reaming.", { split: 0.5 });

// ================================================================================================ section 6
section(6, "Electronics and software", "The station board, a bring-up lesson, and how the robot is controlled");

content("Station board", [
  "The driver boots disabled (EN pull-up): a reset never steps the motor",
  "USB and the 5 V buck cannot back-feed each other: a link jumper plus a Schottky diode",
  "100 µF at the driver's motor supply",
  "Connectors for the motor, homing switch, encoder and 12 V",
  "The KiCad schematic is generated from the soldered board's net list, so the two cannot disagree",
], { file: [R("kicad_station_revD.png"), PH("19_station_perfboard_soldered.jpg")], alt: "Station schematic and the soldered board",
     caption: "KiCad schematic (left), checked net by net against the soldered perfboard (right)" },
"Rules check: 0 errors. 16 nets, 55 pins match the perfboard.", { split: 0.42 });

content("A motor that would not move", [
  "The log said it was stepping; the shaft did not turn",
  "The meter said the logic rail was 1.14 V instead of 3.3 V: a bad connection",
  "After the fix it moved",
  "Since then: a meter checklist before any code",
  "- VDD, SLEEP, ENABLE and the buck output, every new board",
], { file: [PH("07_bench_wiring_a.jpg"), PH("12_bench_bringup_laptop.jpg")], alt: "Bench wiring and bring-up", caption: "Bench wiring and bring-up" },
"Lesson: measure before trusting the software's view of the hardware.");

content("Control software and phone app", [
  "The host plans paths; the stations execute timed segments; a lost link means hold",
  "Stop never disables: there is no brake, so faults and pause keep holding torque",
  "Phone app over home Wi-Fi: robot status, live claw camera, guided setup, chat",
  "- anything that moves the robot asks “yes” first; pause runs at once",
  "Tested in a full simulator of the stations and the claw",
], { file: [P("docs/app_screenshots/01_home.png"), P("docs/app_screenshots/02_camera.png"), P("docs/app_screenshots/04_chat.png")],
     alt: "Phone app screens", caption: "Phone app: home, camera, chat" },
"The software was built against a simulator first, so faults like lost messages and reboots were exercised before hardware.", { split: 0.48 });

// ================================================================================================ section 7
section(7, "Status and next steps");

content("First test", [
  "Stations up in studs, powered from the switched power strip",
  "Self-calibration on the real hardware: slack take-up, lift, floor-board poses, fit",
  "Then a short lift and a 300 mm move at 50 mm/s with the 1 lb test load",
  "Logged: cable lengths, encoder counts, motor temperatures and the fit's error bars",
  "Pass limits written before the run",
], (sl, x, y, w, h) => {
  sl.addShape(pres.shapes.RECTANGLE, { x, y, w, h: h - 0.4, fill: { color: HEX.light }, line: { color: HEX.grey, width: 1, dashType: "dash" }, objectName: "first test photo placeholder" });
  sl.addText("Photo / video from the first test", { x, y: y + (h - 0.4) / 2 - 0.3, w, h: 0.6, fontSize: 18, color: HEX.grey, fontFace: "Calibri",
                                                     align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "placeholder text" });
}, "Placeholder: replace the box with the first-test photo and the measured numbers (calibration error bars, cable error over the 300 mm move).");

content("Status and next steps", [
  "Built: stations, station boards, heat fins, gripper parts",
  "Designed and checked in CAD: the hands and the camera housing",
  "Calibration and control: simulated, then the first test",
  "Next tests, with pass limits written first:",
  "- winch pull test (decides the capacity fix)",
  "- 90-min hold test: motor and printed mount under 60 °C",
  "- SolidWorks static and thermal studies of the station",
  "- four-station lift: 1 lb, 300 mm at 50 mm/s, within 2 mm per cable",
], { file: PH("17_heat_fin_on_motor_angle.jpg"), alt: "Heat fin on the motor", caption: "Built: the heat fin test-fitted on the motor" },
"Everything that is calculated or simulated is called that; the test list is what turns it into measurements.");

content("What I learned", [
  "Measure before trusting a margin: the driver limit and the 1.14 V rail",
  "Print the test coupon before the part: the spool bore",
  "Hold tolerance where it matters: one mill setup for the fin's holes",
  "Design for the worst case: stall, the corner of the room, the hottest hour",
  "Modularity paid for itself: every station can be pulled, fixed and put back",
  "Question each requirement and delete parts: the IMU, the overhead camera, the five-finger hand, the long motor harnesses",
], { file: R("gripper1021_head.png"), alt: "Final gripper head" },
"If I did it again: buy the pulleys and couplers sooner, and build one complete station to test before building four.");

{
  pres.addSection({ title: "Close" }); SECTION_NAME = "Close";
  const sl = pres.addSlide({ masterName: "SECTION", sectionTitle: "Close" });
  sl.addText("Questions", { x: M, y: 2.8, w: 11, h: 1.0, fontSize: 48, bold: true, color: "FFFFFF", fontFace: "Calibri", margin: 0, isTextBox: true });
  sl.addText("Jasper Buntinx  ·  jasper_buntinx@tamu.edu", { x: M, y: 3.9, w: 11, h: 0.6, fontSize: 20, color: "D9DEE5", fontFace: "Calibri", margin: 0, isTextBox: true });
  sl.addNotes("Backups follow: schematics, gear strength, safety, calculations and sources.");
}

// ================================================================================================ backups
pres.addSection({ title: "Backup" }); SECTION_NAME = "Backup";
content("Backup: claw electrical", [
  "One protected 2S pack (7.4 V, 2200 mAh), 5 A fuse, main switch",
  "6 V regulator for the servo only; separate 5 V buck and Schottky diode for the controller",
  "Battery read through 200k / 100k: 8.4 V → 2.80 V at the ADC",
  "Peak ≈ 2.8–3.1 A against a ≈ 3 A pack rating: stalls must stay short",
  "Charged on the claw only with the switch off, attended, at ≤ 1 A",
], { file: R("kicad_claw_revB.png"), alt: "Claw schematic" }, "Rules check 0 errors; 9 nets match the specification.", { section: "Backup", split: 0.42 });

content("Backup: gear strength (Lewis)", [
  "Module 1.5, PETG allowable 22.5 MPa",
  "At 6 V servo stall: pinion SF 2.05, 36T gear 2.50, sync gear 2.00 (one jaw carrying the load)",
  "Module 1 was screened first: SF 0.35–0.41, so the module went up",
], { file: [R("v6r_compound.png"), R("v6r_follower.png")], alt: "Compound and follower gears" }, "Stall torque 1.08 N·m at 6 V (servo rating, not measured).",
{ section: "Backup", eq: { lines: ["σ = F_t / (b m Y),   F_t = 2τ / d,   SF = σ_allow / σ"] } });

content("Backup: safety", [
  "One hard stop: the switched power strip; faults and pause hold torque",
  "Stations anchor into studs; the line load is mostly pull-out and prying",
  "Nobody stands under the robot while it moves",
  "Claw battery: protected pack, charged with the switch off and attended",
  "No safety-rated function is claimed",
], null, "", { section: "Backup", split: 0.9 });

{
  const sl = content("Backup: calculations and sources", [
    "Every chart comes from my calculation sheet in Google Sheets, one tab per topic",
    "- cable tension, winch pull, heat fin, motor temperature, wiring, bead homing, floor board, lift budget, gears",
    "Every result is a formula on its inputs; inputs are marked, with their source or assumption",
    "References used:",
    "- Incropera, DeWitt, Bergman, Lavine: Fundamentals of Heat and Mass Transfer, ch. 3 (extended surfaces)",
    "- Allegro MicroSystems: A4988 datasheet (current limit)",
  ], null, "", { section: "Backup", split: 0.9 });
  sl.addText([{ text: "RoomCleaner engineering calculations (Google Sheets)", options: { hyperlink: { url: SHEET_URL, tooltip: "Open the calculation sheet" } } }],
             { x: M, y: 6.25, w: 8, h: 0.4, fontSize: 16, color: HEX.navy, fontFace: "Calibri", margin: 0, isTextBox: true, objectName: "sheet link" });
}

// ------------------------------------------------------------------------------------------------ write
(async () => {
  await pres.writeFile({ fileName: OUT });
  if (process.env.APPLY_THEME) {
    const { applyTheme } = require(process.env.APPLY_THEME);
    await applyTheme(OUT, THEME);
  }
  if (process.env.SOFFICE_PY) {
    execFileSync("python3", [process.env.SOFFICE_PY, "--headless", "--convert-to", "pdf", "--outdir", __dirname, OUT], { stdio: "inherit" });
  }
  console.log("wrote", OUT);
})();
