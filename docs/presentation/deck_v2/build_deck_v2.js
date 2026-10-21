// RoomCleaner interview deck v2: plain professional style, bullets on every slide, Jasper's narrative order.
// Content contract: docs/presentation/DECK_V2_OUTLINE.md.  v1 (docs/presentation/deck/) is kept unchanged.
//
//   NODE_PATH=<pptxgenjs node_modules> APPLY_THEME=<pptx skill>/scripts/apply_theme.js \
//   SOFFICE_PY=<pptx skill>/scripts/office/soffice.py node docs/presentation/deck_v2/build_deck_v2.js
"use strict";
const path = require("path");
const fs = require("fs");
const { execFileSync } = require("child_process");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const P = (...p) => path.join(ROOT, ...p);
const OUT = path.join(__dirname, "RoomCleaner_Buntinx_Oct27.pptx");
const { size: imgSize } = require("./img_size.js");

const THEME = {
  name: "RoomCleaner v2", headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: "1A1A1A", lt1: "FFFFFF", dk2: "1F3A5F", lt2: "F2F2F4", accent1: "1F3A5F", accent2: "8A8F98",
            accent3: "B23A2E", accent4: "4F6D8F", accent5: "D9DEE5", accent6: "5B6470", hlink: "1F3A5F", folHlink: "4F6D8F" },
};
const HEX = { ink: "1A1A1A", navy: "1F3A5F", grey: "8A8F98", mid: "5B6470", light: "F2F2F4", rule: "D9DEE5", red: "B23A2E", navy2: "4F6D8F" };

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
// "_x" after a letter -> subscript run; "**bold**" -> bold run.  Keeps equations readable without equation objects.
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
function fitImage(sl, file, x, y, w, h, alt, opts = {}) {
  const { w: iw, h: ih } = imgSize(file);
  const s = Math.min(w / iw, h / ih), dw = iw * s, dh = ih * s;
  const dx = x + (opts.alignLeft ? 0 : (w - dw) / 2), dy = y + (opts.alignTop ? 0 : (h - dh) / 2);
  sl.addImage({ path: file, x: dx, y: dy, w: dw, h: dh, altText: alt, objectName: alt.slice(0, 40) });
  return { x: dx, y: dy, w: dw, h: dh };
}
function caption(sl, text, x, y, w) {
  sl.addText(text, { x, y, w, h: 0.32, fontSize: 12, italic: true, color: HEX.grey, fontFace: "Calibri", margin: 0, isTextBox: true });
}
function head(sl, section, title) {
  sl.addText(section.toUpperCase(), { x: M, y: 0.32, w: 9, h: 0.3, fontSize: 12, bold: true, color: HEX.navy, charSpacing: 1.5,
                                      fontFace: "Calibri", margin: 0, isTextBox: true });
  sl.addText(title, { x: M, y: 0.62, w: W - 2 * M, h: 0.75, fontSize: 30, bold: true, color: HEX.ink, fontFace: "Calibri",
                      margin: 0, valign: "middle", isTextBox: true });
}
let SECTION_NAME = "";
const SECTIONS = [];
function section(num, title, sub) {
  SECTION_NAME = title;
  pres.addSection({ title });
  SECTIONS.push(title);
  const sl = pres.addSlide({ masterName: "SECTION", sectionTitle: title });
  sl.addText(String(num).padStart(2, "0"), { x: M, y: 2.2, w: 3, h: 1.2, fontSize: 60, bold: true, color: "8FA6C2", fontFace: "Calibri", margin: 0, isTextBox: true });
  sl.addText(title, { x: M, y: 3.35, w: 11.5, h: 1.0, fontSize: 40, bold: true, color: "FFFFFF", fontFace: "Calibri", margin: 0, isTextBox: true });
  if (sub) sl.addText(sub, { x: M, y: 4.35, w: 11.5, h: 0.8, fontSize: 20, color: "D9DEE5", fontFace: "Calibri", margin: 0, isTextBox: true });
  sl.addNotes(sub || title);
  return sl;
}
// Standard content slide: bullets left, one visual right.
function content(title, items, visual, notes, opts = {}) {
  const sl = pres.addSlide({ masterName: "CONTENT", sectionTitle: SECTION_NAME });
  head(sl, opts.section || SECTION_NAME, title);
  const split = opts.split || 0.52;
  const bw = (W - 2 * M) * split - 0.2;
  bullets(sl, items, M, 1.6, bw, 5.2, opts.size || 20);
  const vx = M + bw + 0.45, vw = W - M - vx, vy = 1.6, vh = opts.capt === false ? 5.25 : 4.95;
  if (typeof visual === "function") visual(sl, vx, vy, vw, vh);
  else if (visual) {
    const files = Array.isArray(visual.file) ? visual.file : [visual.file];
    const gap = 0.15, each = (vw - gap * (files.length - 1)) / files.length;
    files.forEach((f, i) => {
      sl.addShape(pres.shapes.RECTANGLE, { x: vx + i * (each + gap), y: vy, w: each, h: vh, fill: { color: HEX.light }, line: { color: HEX.light } });
      fitImage(sl, f, vx + i * (each + gap) + 0.08, vy + 0.08, each - 0.16, vh - 0.16, visual.alt || path.basename(f));
    });
    if (visual.caption) caption(sl, visual.caption, vx, vy + vh + 0.08, vw);
  }
  sl.addNotes(notes || "");
  return sl;
}
const chartBase = (x, y, w, h) => ({
  x, y, w, h, catAxisLabelColor: HEX.mid, valAxisLabelColor: HEX.mid, catAxisLabelFontSize: 12, valAxisLabelFontSize: 12,
  catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", valGridLine: { color: "E6E8EC", size: 0.75 }, catGridLine: { style: "none" },
  legendFontSize: 12, legendFontFace: "+mn-lt", legendColor: HEX.mid, titleFontFace: "+mn-lt", titleFontSize: 14, titleColor: HEX.ink,
  valAxisTitleFontFace: "+mn-lt", catAxisTitleFontFace: "+mn-lt", valAxisTitleColor: HEX.mid, catAxisTitleColor: HEX.mid,
  valAxisTitleFontSize: 12, catAxisTitleFontSize: 12, dataLabelFontFace: "+mn-lt", dataLabelFontSize: 12, dataLabelColor: HEX.ink,
});

const R = f => P("docs/presentation/deck_assets/renders", f);
const PH = f => P("docs/presentation/photos", f);
const FG = f => P("docs/presentation/deck_v2/fig", f);

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
                 ["From one box to modular stations", "Wiring, a controller per winch, the slide-in housing, plug-in power, cooling"],
                 ["Homing and calibration", "Bead homing, why it limited the motion, the camera-based method"],
                 ["The claw", "Gripper evolution, the four-bar hands, the camera, weight vs lift"],
                 ["Electronics and software", "Station board, bring-up, control and the phone app"],
                 ["Status and next steps", "What is built, what is tested next, what I learned"]];
  items.forEach(([t, s], i) => {
    const y = 1.65 + i * 0.85;
    sl.addText(String(i + 1), { x: M, y, w: 0.6, h: 0.6, fontSize: 24, bold: true, color: HEX.navy, fontFace: "Calibri", margin: 0, isTextBox: true });
    sl.addText(t, { x: M + 0.7, y: y - 0.02, w: 10, h: 0.4, fontSize: 21, bold: true, color: HEX.ink, fontFace: "Calibri", margin: 0, isTextBox: true });
    sl.addText(s, { x: M + 0.7, y: y + 0.36, w: 10, h: 0.35, fontSize: 15, color: HEX.mid, fontFace: "Calibri", margin: 0, isTextBox: true });
  });
  sl.addNotes("The talk follows the order the problems appeared in.");
}

// ================================================================================================ section 1
section(1, "How a cable robot works", "Four cables, one point, and the vectors that connect them");

content("Position vectors", [
  "Room frame at a floor corner; anchor i (the pulley exit) at position vector **a**_i, claw at **p**",
  "Cable vector **l**_i = **a**_i − **p**",
  "Cable length L_i = ‖**a**_i − **p**‖, direction **u**_i = **l**_i / L_i",
  "To move: for every point **p**(t) on the path, compute the four lengths L_i(t)",
  "Spool turn: Δθ_i = ΔL_i / r, with r the spool radius including the wound line",
  "Closed form: no iteration is needed to command a move",
], { file: FG("position_vectors.png"), alt: "Position vectors from four anchors to the claw" },
"Inverse kinematics of a cable robot is just vector subtraction and a norm, done for each cable at every step.", { split: 0.56 });

content("Statics: why cable angle matters", [
  "Force balance on the claw: Σ T_i **u**_i + m(**g** + **a**) = 0",
  "Cables only pull, so every T_i must stay positive",
  "Centred claw, equal share: T = W / (4 sin φ), φ = cable angle above horizontal",
  "1 lb + 0.45 kg claw: 32.1 N per cable 0.15 m below the anchors, 8.3 N at 0.6 m, 4.6 N at 1.2 m",
  "Flat cables near the ceiling or a wall need large tension",
  "So the robot keeps margins: 0.4 m below the anchors, 0.2 m from the walls",
], (sl, x, y, w, h) => {
  const Dh = 2.17, Wn = 8.86;
  const depths = [0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2];
  const T = d => Wn / (4 * (d / Math.sqrt(d * d + Dh * Dh)));
  const lab = depths.map(d => d.toFixed(2));
  sl.addChart(pres.charts.LINE, [
    { name: "Static", labels: lab, values: depths.map(d => +T(d).toFixed(1)) },
    { name: "With +2 m/s²", labels: lab, values: depths.map(d => +(T(d) * (9.81 + 2) / 9.81).toFixed(1)) },
    { name: "Winch design force 11.9 N", labels: lab, values: depths.map(() => 11.9) },
  ], { ...chartBase(x, y, w, h), chartColors: [HEX.navy, HEX.navy2, HEX.red], lineSize: 2.5, lineDataSymbol: "circle", lineDataSymbolSize: 6,
       showLegend: true, legendPos: "b", showTitle: true, title: "Tension per cable vs depth below the anchors (centred claw)",
       showValAxisTitle: true, valAxisTitle: "N", showCatAxisTitle: true, catAxisTitle: "depth below anchors (m)", valAxisMinVal: 0 });
}, "Numbers: W = (0.454 + 0.45) kg × 9.81 = 8.86 N, D_h = 2.17 m from the room centre to a corner. The tension doubles each time the depth halves near the ceiling.");

content("The winch", [
  "NEMA 17 stepper, printed spool and a bearing pulley at the outlet, one per corner",
  "Pull from torque: T = τ / r",
  "- smaller spool radius → more pull per amp, more turns per metre",
  "Spool v1 → v3: Ø20 → Ø15 core with a 16 mm drum",
  "- the first print's bore was too tight on the shaft: opened from Ø5.2 to Ø5.45",
  "Steps open loop; an encoder at the spool checks for lost steps",
], { file: [R("spool_v1.png"), R("spool_v2.png"), R("spool_v3.png")], alt: "Spool v1, v2, v3", caption: "Spool v1, v2, v3" },
"Running torque is lower than holding torque; the pull test will measure the real value.");

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
  "- ≈ 820 ft of conductor, against ≈ 164 ft for power only",
  "The encoder's I²C bus is meant for centimetres, not 10 m runs",
  "Motor phase currents in long cables also radiate noise into the sensor lines",
], { file: FG("wiring_comparison.png"), alt: "Central box vs controller per station wiring" },
"The wire count, not the motors, was the problem. 16 AWG over 32 ft at 2 A drops 0.51 V; 18 AWG 0.82 V.", { split: 0.47 });

content("Decision: a controller in every winch", [
  "Each station: XIAO ESP32-C3 + A4988 driver + 5 V buck; only 12 V power travels, on 2 wires",
  "Switch and encoder wires stay inside the station, a few centimetres long",
  "The host computer plans the path and sends each station timed segments over Wi-Fi",
  "Each station runs its segments on its own clock; any lost link → hold position",
  "Cost: a 50 ms timing skew at 50 mm/s is 2.5 mm of cable mismatch, so segments are time-stamped",
  "Benefit: about 5× less wire, and every station can be built and tested alone",
], { file: [PH("11_gen2_station_assembled.jpg"), PH("09_homing_switch_perfboard.jpg")], alt: "Gen-2 station and its electronics", caption: "Gen 2: the station carries its own controller, driver and buck" },
"Sync moved from wiring into software: time-stamped segments and a host that keeps every station's clock.");

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
  "- design target: safety factor 3 at 34 N; SolidWorks static study planned",
], { file: [R("wall_mount_v3.png"), R("slipin_v3.png")], alt: "Wall frame and slide-in piece", caption: "Fixed wall frame (left) and the slide-in piece (right)" },
"34 N is the snag case: holding torque at the empty spool. The study checks stress below 8.3 MPa (derated PETG / 3) and deflection at the cable exit.");

content("Self-calibration: set it up anywhere", [
  "Every time the stations go back up, the robot measures its own geometry",
  "- no tape measure, no numbers typed in, nothing for a user to get wrong",
  "The claw camera reads a printed floor board (a grid of tags) to get the claw's pose",
  "The robot moves through a set of poses and fits the anchor positions and cable lengths by least squares",
  "Works in any room the cables can reach, so it can become a consumer product",
], (sl, x, y, w, h) => {
  fitImage(sl, FG("calibration_loop.png"), x, y + 0.2, w, 1.9, "Calibration loop");
  sl.addShape(pres.shapes.RECTANGLE, { x, y: y + 2.35, w, h: h - 2.35, fill: { color: HEX.light }, line: { color: HEX.light } });
  fitImage(sl, R("gripper1021_final.png"), x + 0.1, y + 2.45, w - 0.2, h - 2.55, "Claw with camera bay");
  caption(sl, "Startup calibration loop; the claw camera looks straight down", x, y + h + 0.08, w);
}, "Simulated so far; the hardware run comes after the four-station lift test.");

content("Plug-in power", [
  "Each station has one cable: a 16 AWG pair from a fused 12 V supply",
  "Plug in to use; unplug and store the cables when the robot is not needed",
  "Stations slide off the wall frames if wanted",
  "Runs cut at 9, 24, 26 and 35 ft (94 ft of a 100 ft roll), a fuse per branch at the supply",
  "The motor stays wired inside the station, so it is never unplugged under power",
  "The switched power strip is the one hard stop",
], { file: FG("wiring_comparison.png"), alt: "Power-only wiring to each station", caption: "Only power reaches the stations" },
"Unplugging a motor from an energised A4988 can kill the driver, so the plug carries only 12 V.");

content("Cooling", [
  "In a sealed printed housing the motor's heat has nowhere to go",
  "- PETG next to the loaded motor mount softens and creeps",
  "Fix: an aluminium fin from the motor face up through the shell, plus vents",
  "Fin efficiency η = tanh(mL) / (mL), with m = √(2h / (k t))",
  "Built from 0.019 in sheet: η ≈ 37 % (74 % for the 1/8 in plate drawn)",
  "Calculated at 1.06 A: sealed 64 °C without the fin, 46 °C with it; a 90-min hold test is planned",
], (sl, x, y, w, h) => {
  const labels = ["Vented shell", "Sealed shell"];
  sl.addChart(pres.charts.BAR, [
    { name: "No fin", labels, values: [51, 64] },
    { name: "0.019 in fin (built)", labels, values: [41, 46] },
    { name: "1/8 in fin (drawn)", labels, values: [36, 40] },
  ], { ...chartBase(x, y, w, h * 0.62), barDir: "col", barGrouping: "clustered", barGapWidthPct: 60, chartColors: ["8A8F98", HEX.navy, "8FA6C2"],
       showLegend: true, legendPos: "b", showValue: true, dataLabelPosition: "outEnd", showTitle: true,
       title: "Motor case temperature at 1.06 A, 23 °C room (°C, calculated)", valAxisMinVal: 0, valAxisMaxVal: 70 });
  const pw = (w - 0.15) / 2, py = y + h * 0.66, ph = h * 0.34;
  [PH("15_heat_fin_finished_part.jpg"), PH("16_heat_fin_on_motor_straight.jpg")].forEach((f, i) => {
    sl.addShape(pres.shapes.RECTANGLE, { x: x + i * (pw + 0.15), y: py, w: pw, h: ph, fill: { color: HEX.light }, line: { color: HEX.light } });
    fitImage(sl, f, x + i * (pw + 0.15) + 0.05, py + 0.05, pw - 0.1, ph - 0.1, "Heat fin photo");
  });
  caption(sl, "The fin as built and on the motor", x, y + h + 0.08, w);
}, "Fin carries about half the heat in the sealed case. 60 °C is the limit used for loaded printed parts; PETG softens near 80 °C.");

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
  "- then the claw can never move closer to any anchor than from that point",
  "Home at the room centre 1 m up → about 5 % of the working volume reachable; 2 m up → about 29 %",
  "And vision alone knows cable length to ~20–25 mm, while a bead allows ~12 mm of overtravel",
  "- a bead search was not safe either",
], { file: FG("bead_reach.png"), alt: "Reachable region with beads set at a centre homing point" },
"Calculated over the working volume with 0.2 m wall and 0.4 m ceiling margins. This tradeoff is physical: software cannot remove it.", { split: 0.46 });

content("New calibration: camera, floor board and margins", [
  "Startup: take up slack one cable at a time, lift, then look at the floor board from several poses",
  "Least-squares fit of the anchor positions and cable zero lengths; held-out poses check the fit",
  "Safety comes from margins, not precision",
  "- 0.4 m below the anchors and 0.2 m inside the walls unless the error bars allow more",
  "Beads stay as end-of-travel safety switches; encoders watch for lost steps",
  "Simulated so far; the hardware run follows the four-station lift",
], { file: FG("calibration_loop.png"), alt: "Calibration loop" },
"The robot only unlocks the full workspace when k × σ fits inside the margin; otherwise it stays local.", { split: 0.5 });

content("Why a floor board", [
  "Angle error becomes position error through the lever arm: δx = σ_θ · L",
  "One tag: 12.9 mrad × 0.51 m ≈ 6.6 mm per frame",
  "Four tags in view: about 0.7 mm",
  "The board is a printed grid at 250 mm pitch: cheap, and it works in any room",
  "Averaging frames helps only with random noise, not with a fixed bias",
], (sl, x, y, w, h) => {
  sl.addChart(pres.charts.BAR, [{ name: "Position error per frame (mm)", labels: ["One tag", "Two tags", "Four tags"], values: [6.6, 2.5, 0.7] }],
    { ...chartBase(x, y + 0.3, w, h - 0.6), barDir: "col", barGapWidthPct: 70, chartColors: [HEX.navy], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0",
      showLegend: false, showTitle: true, title: "Lever-arm position error per frame at 0.51 m (mm, calculated)", valAxisMinVal: 0 });
}, "Two tags: 4.85 mrad → 2.5 mm. Noise model: 0.3 px corner noise, 520 px focal length (camera not yet calibrated).");

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
  "Servo → 18T pinion → 36T/24T compound (2:1) → 24T sync gear: the jaws move as mirror images",
  "Each hand joins a gear crank (53 mm) to a swing arm (50 mm): a near-parallelogram four-bar",
  "- the jaws stay parallel within about 1° over the stroke",
  "53 mm opening; closing also moves the tips down ~38 mm, a scoop that lifts fabric",
  "Gear teeth checked with the Lewis equation: safety factor about 2 at servo stall",
  "Full motion swept in CAD: no collisions from open to closed",
], { file: P("renders/gripper1021/hands_on_mechanism_poses.png"), alt: "Hands on the four-bar at open, mid and closed",
     caption: "Hands on the linkage: open, mid, closed" },
"Four-bar: ground 36.5, crank 53, rocker 50, coupler 34.7 mm. Lewis: σ = F_t / (b m Y).", { split: 0.45 });

content("Camera on the claw", [
  "XIAO ESP32-S3 Sense camera in a bay built into the electronics housing",
  "It looks straight down along the tube at the grasp spot",
  "Sees the spot from about 17 cm above it; at contact the jaws hide it, so the last view guides the final approach",
  "The same camera reads the floor board for calibration",
  "One printed part: the bay is part of the housing, with a screwed cover",
], { file: R("gripper1021_final.png"), alt: "Claw with camera bay", caption: "Camera bay on the electronics housing (cover in navy)" },
"Lens position kept from the studied design, so the view study still applies.");

content("Weight vs lift: where it stands", [
  "The driver boards top out at Vref 0.85 V → about 1.06 A per motor",
  "Running pull ≈ 18–24 N per winch (full vs empty spool)",
  "- about 1.1 kg total lift at the worst point in the room",
  "The claw is not weighed yet: CAD says ~0.8 kg printed (1.2 kg solid), plus a 0.1 kg battery",
  "With jeans that is above the capacity today: this is the open problem",
  "Options: lighten the claw, a 3:1 winch reduction (~2.7× pull), or a lighter demo load",
  "- next step: a luggage-scale pull test on one station decides",
], (sl, x, y, w, h) => {
  sl.addChart(pres.charts.BAR, [{ name: "kg", labels: ["Lift capacity, worst point", "Claw (CAD, printed est.) + battery", "Claw + battery + jeans"], values: [1.1, 0.9, 1.8] }],
    { ...chartBase(x, y + 0.2, w, h - 0.4), barDir: "bar", barGapWidthPct: 55, chartColors: [HEX.navy, "8A8F98", HEX.red], showValue: true,
      dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0", showLegend: false, showTitle: true, title: "Mass the four winches can hold vs what they must hold (kg)", valAxisMinVal: 0, valAxisMaxVal: 2.2 });
}, "Honest status: the numbers say the current claw plus jeans is too heavy. The pull test turns the 0.7 running-torque assumption into a measurement.");

// ================================================================================================ section 5
section(5, "Electronics and software", "The station board, a bring-up lesson, and how the robot is controlled");

content("Station board", [
  "The driver boots disabled (EN pull-up): a reset never steps the motor",
  "USB and the 5 V buck cannot back-feed each other: a link jumper plus a Schottky diode",
  "100 µF at the driver's motor supply",
  "Connectors for the motor, homing switch, encoder and 12 V",
  "The KiCad schematic is generated from the soldered board's net list, so the two cannot disagree",
], { file: R("kicad_station_revD.png"), alt: "Station schematic", caption: "Station schematic (KiCad), checked net by net against the board" },
"Rules check: 0 errors. 16 nets, 55 pins match the perfboard.", { split: 0.44 });

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
  "Tested in a full simulator of the four stations and the claw",
], { file: [P("docs/app_screenshots/01_home.png"), P("docs/app_screenshots/02_camera.png"), P("docs/app_screenshots/04_chat.png")],
     alt: "Phone app screens", caption: "Phone app: home, camera, chat" },
"The software was built against a simulator first, so faults like lost messages and reboots were exercised before hardware.", { split: 0.48 });

// ================================================================================================ section 6
section(6, "Status and next steps");

content("Status and next steps", [
  "Built: stations, station boards, heat fins, gripper parts",
  "Designed and checked in CAD: the hands and the camera housing",
  "Calibration and control: simulated",
  "Next tests, with pass limits written first:",
  "- winch pull test (decides the capacity fix)",
  "- 90-min hold test: motor and printed mount under 60 °C",
  "- SolidWorks static and thermal studies of the station",
  "- first four-station lift: 1 lb, 300 mm at 50 mm/s, within 2 mm per cable",
], { file: PH("04_gen2_station_shells.jpg"), alt: "Gen-2 station shells", caption: "Gen-2 station shells" },
"Everything that is calculated or simulated is called that; the test list is what turns it into measurements.");

content("What I learned", [
  "Measure before trusting a margin: the driver limit and the 1.14 V rail",
  "Print the test coupon before the part: the spool bore",
  "Design for the worst case: stall, the corner of the room, the hottest hour",
  "Modularity paid for itself: every station can be pulled, fixed and put back",
  "Question each requirement and delete parts: the IMU, the five-finger hand (now two jaws), the long motor harnesses",
], { file: R("gripper1021_head.png"), alt: "Final gripper head" },
"If I did it again: buy the pulleys and couplers sooner, and build one complete station to test before building four.");

{
  pres.addSection({ title: "Close" }); SECTION_NAME = "Close";
  const sl = pres.addSlide({ masterName: "SECTION", sectionTitle: "Close" });
  sl.addText("Questions", { x: M, y: 2.8, w: 11, h: 1.0, fontSize: 48, bold: true, color: "FFFFFF", fontFace: "Calibri", margin: 0, isTextBox: true });
  sl.addText("Jasper Buntinx  ·  jasper_buntinx@tamu.edu", { x: M, y: 3.9, w: 11, h: 0.6, fontSize: 20, color: "D9DEE5", fontFace: "Calibri", margin: 0, isTextBox: true });
  sl.addNotes("Backups follow: schematics, gear strength, thermal network, safety.");
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
  "σ = F_t / (b m Y), F_t = 2τ / d",
  "Module 1.5, PETG allowable 22.5 MPa",
  "At 6 V servo stall: pinion SF 2.05, 36T gear 2.50, sync gear 2.00 (one jaw carrying the load)",
  "Module 1 was screened first: SF 0.35–0.41, so the module went up",
], { file: [R("v6r_compound.png"), R("v6r_follower.png")], alt: "Compound and follower gears" }, "Stall torque 1.08 N·m at 6 V (servo rating, not measured).", { section: "Backup" });

content("Backup: safety", [
  "One hard stop: the switched power strip; faults and pause hold torque",
  "Stations anchor into studs; the line load is mostly pull-out and prying",
  "Nobody stands under the robot while it moves",
  "Claw battery: protected pack, charged with the switch off and attended",
  "No safety-rated function is claimed",
], null, "", { section: "Backup", split: 0.9 });

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
