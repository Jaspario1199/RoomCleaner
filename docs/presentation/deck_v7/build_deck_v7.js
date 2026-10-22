// RoomCleaner interview deck v7 (Jasper, Oct 22): one story told by project phase, Concept -> Generation 1 -> Redesign ->
// Final design -> Build and test, then results and lessons. Every content slide is a figure on the left and two to four short
// statements on the right; Jasper talks, the slide shows the data. Plain titles, no boxed diagrams; slim equation boxes on the
// calculation slides. Smaller topics (phone app, safety, obstacles, fin sizing, gear strength) live inside the slide they belong
// to or in the appendix. Content contract: docs/presentation/DECK_V7_NOTES.md.  v1-v6 are kept unchanged.
//
//   NODE_PATH=<pptxgenjs node_modules> APPLY_THEME=<pptx skill>/scripts/apply_theme.js \
//   SOFFICE_PY=<pptx skill>/scripts/office/soffice.py node docs/presentation/deck_v7/build_deck_v7.js
//
// [[text]] in any string is a fact still to fill in: it renders red and bracketed so it cannot be missed.
"use strict";
const path = require("path");
const { execFileSync } = require("child_process");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const P = (...p) => path.join(ROOT, ...p);
const OUT = path.join(__dirname, "RoomCleaner_Buntinx_Oct27_v7.pptx");
const FIGDIR = path.join(__dirname, "..", "deck_v3", "fig");
const SHEETFIG = path.join(__dirname, "..", "deck_v5", "fig");      // Sheet charts at 1.5 A (Oct 22)
const { size: imgSize } = require("../deck_v2/img_size.js");
const SHEET_URL = "https://docs.google.com/spreadsheets/d/1UGFnkL1v305WnDYj5aj5zBtgxnxmGP7_TVRN0afZTGs/edit";

const THEME = {
  name: "RoomCleaner v7", headFontFace: "Arial", bodyFontFace: "Arial",
  colors: { dk1: "1A1A1A", lt1: "FFFFFF", dk2: "1F3A5F", lt2: "F2F2F4", accent1: "1F3A5F", accent2: "8A8F98",
            accent3: "B23A2E", accent4: "4F6D8F", accent5: "D9DEE5", accent6: "5B6470", hlink: "1F3A5F", folHlink: "4F6D8F" },
};
const HEX = { ink: "1A1A1A", navy: "1F3A5F", grey: "7F7F7F", mid: "404040", light: "F2F2F2", rule: "BFBFBF", red: "B23A2E",
              navy2: "4F6D8F", pale: "D9DEE5" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";                       // 13.33 x 7.5 in
pres.author = "Jasper Buntinx";
pres.title = "RoomCleaner";
pres.theme = { headFontFace: "Arial", bodyFontFace: "Arial" };
const W = 13.333, M = 0.6;

pres.defineSlideMaster({
  title: "CONTENT", background: { color: "FFFFFF" },
  objects: [{ text: { text: "Jasper Buntinx  |  RoomCleaner", options: { x: M, y: 7.0, w: 6, h: 0.3, fontSize: 10, color: HEX.grey, fontFace: "Arial", margin: 0 } } }],
  slideNumber: { x: W - M - 0.6, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: HEX.grey, align: "right", fontFace: "Arial" },
});
pres.defineSlideMaster({ title: "SECTION", background: { color: HEX.navy } });
pres.defineSlideMaster({ title: "TITLE", background: { color: "FFFFFF" } });

// ------------------------------------------------------------------------------------------------ helpers
// "_x" / "_{ab}" after a letter -> subscript run; "**bold**" -> bold run; "[[fill in]]" -> red italic placeholder.
function runs(text, base) {
  const out = [];
  const re = /\*\*(.+?)\*\*|\[\[(.+?)\]\]|_\{([^}]+)\}|_([A-Za-z0-9]+)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push({ text: text.slice(last, m.index), options: { ...base } });
    if (m[1]) out.push({ text: m[1], options: { ...base, bold: true } });
    else if (m[2]) out.push({ text: `[${m[2]}]`, options: { ...base, italic: true, color: HEX.red } });
    else out.push({ text: m[3] || m[4], options: { ...base, subscript: true } });
    last = re.lastIndex;
  }
  if (last < text.length) out.push({ text: text.slice(last), options: { ...base } });
  return out;
}
// Bulleted list; "- " starts a sub-bullet. o.numbered gives 1, 2, 3 instead of bullets.
function bullets(sl, items, x, y, w, h, size = 18, o = {}) {
  const arr = [];
  items.forEach((it, i) => {
    const sub = it.startsWith("- ");
    const t = (sub ? it.slice(2) : it).replace(/(\d) (?=[A-Za-z°%Ω])/g, "$1 ");   // keep a number on the same line as its unit
    const base = { fontSize: sub ? size - 2 : size, color: sub ? HEX.mid : HEX.ink, fontFace: "Arial" };
    const mark = o.numbered && !sub ? { type: "number", indent: 26 } : { indent: sub ? 18 : 20 };
    const para = { bullet: mark, indentLevel: sub ? 1 : 0, paraSpaceAfter: sub ? 6 : (o.space || 14) };
    const rs = runs(t, { ...base, ...para, align: "left" });   // paragraph options on every run: pptxgenjs takes them from the last run
    rs.forEach((r, j) => { r.options.breakLine = j === rs.length - 1 && i < items.length - 1; });
    arr.push(...rs);
  });
  sl.addText(arr, { x, y, w, h, valign: "top", align: "left", margin: [2, 4, 2, 0], isTextBox: true, objectName: o.name || "bullets" });
}
// Equation box: a title, then two or three lines with our numbers substituted (results in bold).
const EQ_LINE = 0.37;
const eqHeight = eq => 0.44 + EQ_LINE * eq.lines.length;
function eqBox(sl, eq, x, y, w) {
  const h = eqHeight(eq);
  sl.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: "F7F8FA" }, line: { color: HEX.navy, width: 1 }, objectName: "equation box" });
  sl.addText(eq.title, { x: x + 0.16, y: y + 0.08, w: w - 0.32, h: 0.24, fontSize: 11, bold: true, color: HEX.navy,
                         fontFace: "Arial", margin: 0, isTextBox: true, objectName: "equation title" });
  const arr = [];
  eq.lines.forEach((ln, i) => {
    const rs = runs(ln, { fontSize: 15, color: HEX.ink, fontFace: "Cambria", paraSpaceAfter: 4, align: "left" });
    rs.forEach((r, j) => { r.options.breakLine = j === rs.length - 1 && i < eq.lines.length - 1; });
    arr.push(...rs);
  });
  sl.addText(arr, { x: x + 0.16, y: y + 0.36, w: w - 0.32, h: EQ_LINE * eq.lines.length + 0.02, valign: "top", align: "left", margin: 0,
                    isTextBox: true, objectName: "equations" });
}
function fitImage(sl, file, x, y, w, h, alt, opts = {}) {
  const { w: iw, h: ih } = imgSize(file);
  const s = Math.min(w / iw, h / ih), dw = iw * s, dh = ih * s;
  const dx = x + (opts.alignLeft ? 0 : (w - dw) / 2), dy = y + (opts.alignTop ? 0 : (h - dh) / 2);
  sl.addImage({ path: file, x: dx, y: dy, w: dw, h: dh, altText: alt, objectName: alt.slice(0, 40) });
  return { x: dx, y: dy, w: dw, h: dh };
}
function caption(sl, text, x, y, w) {
  sl.addText(runs(text, { fontSize: 11, color: HEX.grey, fontFace: "Arial" }), { x, y, w, h: 0.3, margin: 0, isTextBox: true, objectName: "caption" });
}
function placeholderBox(sl, text, x, y, w, h) {
  sl.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: HEX.light }, line: { color: HEX.red, width: 1, dashType: "dash" }, objectName: "placeholder" });
  sl.addText(runs(text, { fontSize: 16, color: HEX.grey, fontFace: "Arial" }), { x: x + 0.2, y, w: w - 0.4, h, align: "center", valign: "middle",
                                                                               margin: 0, isTextBox: true, objectName: "placeholder text" });
}
// The figure on the left: a calculation-sheet chart, a 2 x 2 grid, a row of images, or a drawing function.
function figure(sl, v, x, y, w, h) {
  if (typeof v === "function") return v(sl, x, y, w, h);
  if (v.sheet) {
    const r = fitImage(sl, path.join(SHEETFIG, `sheet_${v.sheet}.png`), x, y, w, h - 0.4, `Chart from the calculation sheet: ${v.tab}`, { alignTop: true });
    caption(sl, `Source: RoomCleaner engineering calculations, “${v.tab}” (calculated)`, r.x, r.y + r.h + 0.08, Math.max(r.w, 4.5));
    return;
  }
  const g = 0.12;
  if (v.grid) {
    const cw = (w - g) / 2, ch = (h - 0.4 - g) / 2;
    v.grid.forEach((f, i) => fitImage(sl, f, x + (i % 2) * (cw + g), y + Math.floor(i / 2) * (ch + g), cw, ch, v.alt || path.basename(f)));
  } else {
    const files = Array.isArray(v.file) ? v.file : [v.file];
    const each = (w - g * (files.length - 1)) / files.length;
    files.forEach((f, i) => fitImage(sl, f, x + i * (each + g), y, each, h - 0.4, v.alt || path.basename(f)));
  }
  if (v.caption) caption(sl, v.caption, x, y + h - 0.3, w);
}

// Slide frame: a plain title, nothing else.
let SECTION = "Introduction";
function section(name) { SECTION = name; pres.addSection({ title: name }); }
function blank(title) {
  const sl = pres.addSlide({ masterName: "CONTENT", sectionTitle: SECTION });
  sl.addText(title, { x: M, y: 0.4, w: W - 2 * M, h: 0.65, fontSize: 26, bold: true, color: HEX.ink, fontFace: "Arial",
                      margin: 0, valign: "middle", isTextBox: true, objectName: "title" });
  return sl;
}
// Standard slide: the figure left, two to four statements right, an equation box under them if given.
function content(title, items, visual, notes, opts = {}) {
  const sl = blank(title);
  const fw = opts.figW || 7.0, fx = M, fy = 1.3, fh = 5.45;
  const bx = fx + fw + 0.45, bw = W - M - bx, by = 1.35, bottom = 6.75;
  const eqH = opts.eq ? eqHeight(opts.eq) : 0;
  figure(sl, visual, fx, fy, fw, fh);
  bullets(sl, items, bx, by, bw, (opts.eq ? bottom - eqH - 0.2 : bottom) - by, opts.size || 18, { numbered: opts.numbered, space: opts.space });
  if (opts.eq) eqBox(sl, opts.eq, bx, bottom - eqH, bw);
  sl.addNotes(notes || "");
  return sl;
}
// Phase divider: number, name, dates and the phase goal.
function divider(n, name, dates, goal, notes) {
  section(name);
  const sl = pres.addSlide({ masterName: "SECTION", sectionTitle: name });
  sl.addText(`Phase ${n}`, { x: M, y: 2.2, w: 11, h: 0.45, fontSize: 20, color: HEX.pale, fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addText(name, { x: M, y: 2.7, w: 11, h: 0.95, fontSize: 44, bold: true, color: "FFFFFF", fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addText(dates, { x: M, y: 3.7, w: 11, h: 0.45, fontSize: 20, color: HEX.pale, fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addText(goal, { x: M, y: 4.55, w: 11, h: 0.5, fontSize: 20, color: "FFFFFF", fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addNotes(notes || "");
}

// ------------------------------------------------------------------------------------------------ native figures
function seg(sl, x1, y1, x2, y2, line) {
  sl.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
                                  flipH: x2 < x1, flipV: y2 < y1, line });
}
function label(sl, text, x, y, w, h, o = {}) {
  sl.addText(runs(text, { fontSize: o.size || 12, bold: !!o.bold, color: o.color || HEX.ink, fontFace: "Arial" }),
             { x, y, w, h, align: o.align || "left", valign: o.valign || "middle", margin: 0, isTextBox: true, objectName: o.name || "label" });
}
// A native table with a header row; "[[...]]" cells render as red placeholders, { text, color } cells take their own colour.
function table(sl, head, rows, x, y, w, colW, o = {}) {
  const cell = (c, j) => {
    const bold = j === 0 && o.boldFirst !== false;
    if (c && typeof c === "object") return { text: c.text, options: { bold: bold || !!c.bold, color: c.color || HEX.ink } };
    const ph = /^\[\[(.*)\]\]$/.exec(c);
    if (ph) return { text: `[${ph[1] || "fill in"}]`, options: { italic: true, color: HEX.red } };
    if (c.includes("[[")) return { text: runs(c, { bold, color: HEX.ink }), options: {} };
    return { text: c, options: { bold, color: HEX.ink } };
  };
  const hc = o.headColor || HEX.navy;
  const data = [head.map(t => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: hc } } })), ...rows.map(r => r.map(cell))];
  sl.addTable(data, { x, y, w, colW: colW.map(f => f * w), fontFace: "Arial", fontSize: o.size || 13, valign: "middle",
                      border: { type: "solid", pt: 0.75, color: HEX.rule }, rowH: o.rowH || 0.5, margin: 0.06, objectName: o.name || "table" });
}
// Gantt chart: one row per phase, a date column, bars on a July-October axis (day 0 = July 1, end day exclusive).
function gantt(sl, rows, x, y, w) {
  const lw = 2.6, dw = 1.75, cx = x + lw + dw, cw = x + w - cx, hh = 0.4, rh = 0.46;
  const months = [["July", 31], ["August", 31], ["September", 30], ["October", 31]];
  const s = cw / months.reduce((a, [, n]) => a + n, 0), bottom = y + hh + rows.length * rh;
  sl.addShape(pres.shapes.RECTANGLE, { x, y, w, h: hh, fill: { color: HEX.navy }, line: { color: HEX.navy }, objectName: "gantt header" });
  label(sl, "Phase", x + 0.1, y, lw - 0.2, hh, { size: 13, bold: true, color: "FFFFFF" });
  label(sl, "Dates", x + lw + 0.1, y, dw - 0.2, hh, { size: 13, bold: true, color: "FFFFFF" });
  rows.forEach((r, i) => {
    if (i % 2) sl.addShape(pres.shapes.RECTANGLE, { x, y: y + hh + i * rh, w, h: rh, fill: { color: HEX.light }, line: { color: HEX.light } });
  });
  let d = 0;
  months.forEach(([m, n], k) => {
    label(sl, m, cx + d * s, y, n * s, hh, { size: 13, bold: true, color: "FFFFFF", align: "center" });
    if (k) seg(sl, cx + d * s, y + hh, cx + d * s, bottom, { color: HEX.rule, width: 0.75 });
    d += n;
  });
  rows.forEach(([name, dates, a, b], i) => {
    const ry = y + hh + i * rh;
    label(sl, name, x + 0.1, ry, lw - 0.2, rh, { size: 14 });
    label(sl, dates, x + lw + 0.1, ry, dw - 0.2, rh, { size: 14, color: HEX.mid });
    sl.addShape(pres.shapes.RECTANGLE, { x: cx + a * s, y: ry + 0.1, w: (b - a) * s, h: rh - 0.2, fill: { color: HEX.navy2 }, line: { color: HEX.navy2 },
                                         objectName: `${name} bar` });
  });
  seg(sl, x, bottom, x + w, bottom, { color: HEX.rule, width: 0.75 });
  return bottom;
}
// Actual schedule against a half-time plan, same scale (inches per day).
function scheduleBars(sl, x, y, w) {
  const lw = 1.45, bx = x + lw, bw = w - lw, s = bw / 104, bh = 0.75;
  const actual = [["Concept", 21, HEX.pale], ["Gen 1", 28, HEX.navy2], ["Redesign", 34, HEX.pale], ["Final", 15, HEX.navy2], ["Build and test", 6, HEX.navy]];
  const half = [["Plan", 7, HEX.pale], ["One station", 14, HEX.navy2], ["Copy", 7, HEX.pale], ["Claw", 14, HEX.navy2], ["Test", 7, HEX.navy]];
  [[actual, "Actual\n(15 weeks)", y], [half, "Half time\n(7 weeks)", y + bh + 0.45]].forEach(([segs, name, yy]) => {
    label(sl, name, x, yy, lw - 0.1, bh, { size: 13, bold: true, color: HEX.navy });
    let cx = bx;
    segs.forEach(([t, d, c]) => {
      const sw = d * s;
      sl.addShape(pres.shapes.RECTANGLE, { x: cx, y: yy, w: sw, h: bh, fill: { color: c }, line: { color: "FFFFFF", width: 1.5 }, objectName: t });
      if (Math.max(...t.split(" ").map(x => x.length)) * 0.075 > sw - 0.04) label(sl, t, cx + sw - 1.2, yy + bh + 0.03, 1.2, 0.25, { size: 10, bold: true, color: HEX.navy, align: "right" });   // too narrow: label under the bar
      else label(sl, t, cx + 0.03, yy, sw - 0.06, bh, { size: sw < 0.5 ? 9 : sw < 0.9 ? 10.5 : 12, bold: true, color: c === HEX.pale ? HEX.navy : "FFFFFF", align: "center" });
      cx += sw;
    });
  });
  caption(sl, "Same time scale. Half-time plan: prove one station, then copy it.", bx, y + 2 * bh + 0.6, bw);
}

const R = f => P("docs/presentation/deck_assets/renders", f);
const PH = f => P("docs/presentation/photos", f);
const FG = f => path.join(FIGDIR, f);

// ================================================================================================ INTRODUCTION
section("Introduction");
{
  const sl = pres.addSlide({ masterName: "TITLE", sectionTitle: SECTION });
  sl.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 5.6, h: 7.5, fill: { color: HEX.navy }, line: { color: HEX.navy } });
  sl.addText("RoomCleaner", { x: M, y: 2.3, w: 4.8, h: 1.0, fontSize: 44, bold: true, color: "FFFFFF", fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addText("A cable-driven robot that picks laundry up off the floor", { x: M, y: 3.35, w: 4.6, h: 1.2, fontSize: 22, color: HEX.pale, fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addText("Jasper Buntinx\nMechanical Engineering, Texas A&M University\nOctober 27, 2026", { x: M, y: 5.7, w: 4.8, h: 1.1, fontSize: 14, color: HEX.pale, fontFace: "Arial", margin: 0, isTextBox: true });
  fitImage(sl, PH("11_gen2_station_assembled.jpg"), 6.0, 0.6, 3.3, 6.3, "Generation 2 winch station, assembled");
  fitImage(sl, PH("21_claw_printed_tube_servo.jpg"), 9.45, 0.6, 3.3, 6.3, "Printed claw body with its servo");
  sl.addNotes("One sentence: four winches near the ceiling corners hold one claw on cables; it picks clothes off the floor and drops them in a hamper. " +
              "Then straight to who I am.");
}

content("About Me", [
  "Mechanical Engineering, Texas A&M University, [[graduation year]]",
  "Built EcoFil, a filament recycler: shredder, dryer and extruder",
  "Metal sculpture with fiber laser cutting and welding",
  "[[hobbies]]",
], (sl, x, y, w, h) => placeholderBox(sl, "[[Photo of you building: EcoFil, a sculpture, or the workshop]]", x, y, w, h - 0.4),
"One minute. Degree and graduation date, EcoFil (what each stage does, what you learned), the sculptures for the Austin Creek Show (fiber laser and welding: real " +
"fabrication), one hobby. Close with why a laundry robot: a problem you have, and a machine you could build end to end yourself.");

content("Project Goal", [
  "Pick up laundry anywhere in an 11 × 9 ft room and drop it in a hamper",
  "Design load: jeans, 0.9 kg, at 2 m/s²; first test with 1 lb",
  "3D-printed PETG (polyethylene terephthalate glycol) on a hobby budget",
  "Success: one garment to the hamper with no human input",
], { file: [R("station_1021_final.png"), R("gripper1021_asbuilt.png")], alt: "Final wall station and claw", caption: "Final design (CAD): wall station and claw" },
"Why: a real problem in my own room, and a machine I could design, build and program end to end. " +
"0.9 kg is a screening figure for jeans; the first physical test is 1 lb. " +
"Safety rules from day one: stations anchor into studs, a switched power strip is the one hard stop, nobody stands under the robot, and any fault holds position. " +
"The talk follows the project in five phases, the same five as the timeline on the next slide.");

{
  const sl = blank("Timeline and Scope");
  const gy = gantt(sl, [
    ["1. Concept", "Jul 16 – Aug 5", 15, 36],
    ["2. Generation 1", "Aug 6 – Sep 2", 36, 64],
    ["3. Redesign", "Sep 3 – Oct 6", 64, 98],
    ["4. Final design", "Oct 7 – Oct 21", 98, 113],
    ["5. Build and test", "Oct 22 – Oct 27", 113, 119],
  ], M, 1.3, W - 2 * M);
  bullets(sl, [
    "Solo project: requirements, calculations, all CAD (computer-aided design), printing, machining, wiring and [[software parts you wrote]]",
    "Purchased: stepper motors, drivers, controller boards, servo, camera, battery and encoder boards",
    "Garment detection uses YOLO-World, an open-source model",
  ], M, gy + 0.4, W - 2 * M, 6.8 - gy - 0.4, 18, { space: 10, name: "scope" });
  sl.addNotes("About 15 weeks, alone. Each phase that follows starts with what I set out to do and ends with what it taught me. " +
              "Say plainly what is mine and what is bought. [Confirm the start date (git shows Jul 16), what happened in September, and shop access or mentors if any.]");
}

// ================================================================================================ PHASE 1: CONCEPT
divider(1, "Concept", "July 16 – August 5", "Choose the architecture and set the limits",
        "Three weeks of requirements, a simulator and the parts list, before anything was printed.");

content("Why a Cable Robot", [
  "Four ceiling winches hold one claw: the whole floor is reachable and nothing stands on it",
  "The four cable lengths set the claw position",
  "A laptop plans every move; a phone app starts, pauses and approves it",
], { file: FG("position_vectors.png"), alt: "Cable robot geometry", caption: "Cables run from the ceiling anchors a_1 to a_4 to the claw at p" },
"Alternatives I considered: a floor robot (furniture and cords in the way, small reach) and a gantry (a rigid frame across the room). " +
"A cable robot covers the whole floor with a small moving mass and nothing on the floor. The catch: cables can only pull, which sets the limits on the next two slides. " +
"System: each wall station has its own winch, encoder and controller; the claw carries a gripper, camera and battery; the laptop checks every point of a path " +
"before anything moves, and every move waits for a yes on the phone. PAUSE holds position.");

{
  const sl = blank("Design Trade-offs");
  table(sl, ["Design change", "Benefit", "Cost", "Chosen setting"], [
    ["Higher motor current", "41 % more pull at 1.5 A", "Heat rises with current squared", "1.5 A, vented shell and heat fin"],
    ["Stronger claw", "Gear safety factor 0.4 to 2.0", "More claw mass, less payload", "Module 1.5 gears"],
    ["Larger room", "More floor covered", "Longer wires, more voltage drop", "Only 12 V power runs to stations"],
    ["Closer to the ceiling", "More working volume", "Cable tension 12 N to 32 N", "Stay 0.4 m below the anchors"],
    ["Smaller spool radius", "More pull per amp", "Slower line speed", "15 mm core: 25–34 N pull"],
    ["Larger safety margins", "No skipped steps or wall contact", "Less usable force and floor", "Force ÷ 1.5; 0.2 m from walls"],
  ], M, 1.3, W - 2 * M, [0.21, 0.25, 0.27, 0.27], { size: 15, rowH: 0.62 });
  bullets(sl, ["A heavier claw needs more pull, more pull needs more current, and heat rises with the square of the current"],
          M, 6.0, W - 2 * M, 0.7, 18, { name: "coupling" });
  sl.addNotes("These are the levers I set in the concept phase and revisited in every phase after; each later slide is one of these trades. " +
              "Current: pull goes with I but heat goes with I squared, so 41 % more pull costs twice the heat. Claw strength: every gram comes out of the payload. " +
              "Room size: wire resistance grows with length, so only power travels; the longest 32 ft run drops 0.51 V at 2 A on 16-gauge wire. " +
              "Spool: a smaller radius pulls harder but reels slower, and the radius grows as the line winds on. Margins buy safety with force and floor area.");
}

content("Cable Tension Limit", [
  "Tension rises sharply near the ceiling: 32 N at 0.15 m, 8.3 N at 0.6 m",
  "Operating limit set 0.4 m below the anchors",
  "Covers 2 m/s² acceleration within the 16.8 N winch limit",
], { sheet: "cable_tension", tab: "Cable tension" },
"Force balance on the claw: the cable pulls and the weight sum to zero. Centered claw, equal shares; D_h = 2.17 m from the room center to a corner; " +
"W = (0.45 + 0.454) kg × 9.81 = 8.87 N; sin φ = 0.4 / √(0.4² + 2.17²) = 0.181. The tension doubles each time the depth halves near the ceiling, so the ceiling " +
"margin is set by tension, not by collision. 0.3 m would hold standing still (16.2 N) but not while accelerating (19.5 N), so I keep 0.4 m. " +
"Corner picks: the far cables go near-horizontal and carry little; the planner checks every cable stays inside its limits, and also refuses any path whose cables " +
"would cross a keep-out zone such as a shelf.",
{ eq: { title: "Tension per cable at 0.4 m", lines: [
  "T = W / (4 sin φ)",
  "= 8.87 N / (4 × 0.181) = **12.2 N**",
  "With 2 m/s²: **14.7 N** < 16.8 N",
] } });

// ================================================================================================ PHASE 2: GENERATION 1
divider(2, "Generation 1", "August 6 – September 2", "Prove the idea on the bench",
        "The goal was a working station on the bench as fast as possible, to find out what I did not know.");

content("Generation 1 Build", [
  "One-piece corner plates: motor, spool, pulley and home switch",
  "One central board drove all four motors",
  "Five flexible TPU (thermoplastic polyurethane) fingers on the claw",
  "A station lifted a test weight on the bench [[weight]]",
], { grid: [PH("13_gen1_station_lifting_test_weight.jpg"), PH("05_gen1_spool_plate.jpg"), PH("14_gen1_cnc_shield_a4988.jpg"), R("gen1_tentacle_claw.png")],
     alt: "Generation 1 hardware", caption: "Bench lift test, corner plate, central driver board, finger claw (CAD)" },
"Generation 1 worked on the bench: the winch lifted a test weight and the cable math held. The central board was a CNC shield with four A4988 drivers, " +
"which kept the first build simple. The ceiling camera mapped laundry to the floor. Each of these choices was cheap and fast, and each one showed a limit in the next slide. " +
"[Fill in: the test weight and how high it lifted.]");

content("What Generation 1 Taught Me", [
  "Bead homing left only 5–29 % of the room reachable",
  "Adding a sensor at each winch meant 10 wires per corner",
  "Finger claw could not pinch fabric and was 4.6 times over its mass budget",
], { sheet: "bead_homing", tab: "Bead homing" },
"Homing: a bead on each cable trips a switch at the outlet. A cable can then never get shorter than its homing length, so the claw cannot reach anything closer " +
"to an anchor than home. With home 1 m up, 5 % of the room is reachable; 2 m up, 29 %. This was caught on paper, before it was built. " +
"Wiring: once every winch needed an encoder and a switch, the central board needed 10 conductors run to every corner. " +
"Claw: soft fingers wrap round objects but cannot pinch a flat T-shirt, and the finger claw was far over its mass budget. These three findings drove the redesign.");

// ================================================================================================ PHASE 3: REDESIGN
divider(3, "Redesign", "September 3 – October 6", "Fix what generation 1 exposed",
        "Three decisions, one for each finding: distributed control, camera calibration, and a rigid claw.");

content("One Controller per Winch", [
  "A controller in each station instead of one central board",
  "Only a 12 V pair runs to each station: five times less wire",
  "Cost: synchronization moves into software",
], { sheet: "wiring", tab: "Wiring" },
"Real cable routes are 6, 21, 23 and 32 ft (82 ft). 10 conductors per corner (motor 4, switch 2, encoder 4) × 82 ft = 820 ft against 2 × 82 ft = 164 ft for one power pair. " +
"Each station runs time-stamped segments on its own clock; a lost link means hold. Timing skew becomes cable mismatch: 50 mm/s × 50 ms = 2.5 mm, " +
"which is why every segment carries a time stamp. Each station can also be tested on its own.",
{ eq: { title: "Wire to the four stations", lines: [
  "Central board: 10 × 82 ft = **820 ft**",
  "Per station: 2 × 82 ft = **164 ft**",
] } });

content("Camera Calibration Replaces Homing", [
  "The claw camera reads a printed floor board from several poses",
  "A fit finds the anchor positions and cable lengths: no tape measure",
  "Position error: 6.6 mm with one tag in view, 0.7 mm with four",
  "Whole room reachable; the beads stay as end stops",
], { sheet: "floor_board", tab: "Floor board" },
"Startup: take up slack one cable at a time, lift the claw, look at the floor board from several poses, least-squares fit of the anchors and cable zero lengths, " +
"then check the fit on poses it did not use. Error = angle error × camera height: 12.9 mrad × 0.51 m = 6.6 mm with one tag; averaging tags removes noise but not bias. " +
"Safety comes from margins (0.4 m below the anchors, 0.2 m inside the walls), not precision; the full room opens only when the fit's error bars allow it. " +
"Simulated end to end so far; the first hardware run is this week.");

content("Geared Four-Bar Claw", [
  "Parallel jaws pinch thin fabric; 53 mm opening",
  "Camera moved into the claw to see each grasp",
  "Stall check moved the gears from module 1 to 1.5",
], { grid: [R("claw_v6.png"), R("gripper1021_head.png"), PH("21_claw_printed_tube_servo.jpg"), PH("22_gear_train_printed_servo.jpg")],
     alt: "Claw design and printed parts", caption: "v6 clamp, final four-bar (CAD), printed claw body and gear train" },
"Four-bar: ground 36.5, crank 53, rocker 50, coupler 34.7 mm; jaws stay parallel within about 1 degree, and closing drops the tips about 38 mm, a scoop. " +
"Gear train: MG996R servo, 18-tooth pinion, 36/24-tooth compound, 24-tooth sync gear. Lewis bending check at servo stall: with module 1 the safety factor was " +
"0.35 to 0.41, so the module went to 1.5: pinion 2.05, compound 2.50, sync gear 2.00. Stall torque 1.078 N·m is the servo rating, not measured. " +
"Electrical: a two-cell lithium-ion pack with a 5 A fuse, a 6 V servo rail and a separate 5 V logic rail (appendix).",
{ eq: { title: "Gear stress at servo stall", lines: [
  "σ = F_t / (b m Y) = **11.0 MPa**",
  "SF = 22.5 MPa / 11.0 MPa = **2.05**",
] } });

// ================================================================================================ PHASE 4: FINAL DESIGN
divider(4, "Final Design", "October 7 – October 21", "Size the winch, the cooling and the weight in SolidWorks",
        "Three station versions and three spool versions in SolidWorks, ending with the final design on October 21.");

content("Winch Pull at 1.5 A", [
  "NEMA 17 (National Electrical Manufacturers Association) stepper on a printed spool",
  "Driver current raised from 1.06 A to the rated 1.5 A: 41 % more pull",
  "34 N with an empty spool, 25 N when full",
], { sheet: "winch_pull", tab: "Winch pull" },
"Current limit from the driver's reference voltage (A4988 datasheet): I = Vref / (8 × 0.1 Ω). The first boards topped out at 0.85 V, which is 1.06 A; I got them to " +
"1.2 V, 1.5 A, the motor's rated current. [Fill in: how, and the Vref you read.] Running torque assumed 0.7 of the 0.36 N·m holding torque; the luggage-scale pull " +
"test measures it. The 1.5 divisor is the margin against skipped steps. The cost of the extra pull is heat, next slide.",
{ eq: { title: "Winch design force", lines: [
  "T = τ / r = 0.252 N·m / 0.010 m = **25.2 N**",
  "F_{design} = 25.2 N / 1.5 = **16.8 N**",
] } });

content("Motor Cooling", [
  "1.5 A doubles motor heat to 4.05 W",
  "PETG creeps above 60 °C, so the shell is vented and finned",
  "Motor at 45–49 °C with the 1/8 in fin, 56–59 °C with the 0.019 in prototype",
], { sheet: "motor_temperature", tab: "Motor temperature" },
"Model: motor to shell air to room, with an aluminum fin through the top of the shell as a second path out. Sealed, the motor would reach 99 °C with no fin, so the " +
"shell stays vented. Fin sizing: the 0.019 in prototype sheet reaches 95 % of its capacity by 136 mm, so most of its length does little; the 1/8 in plate keeps " +
"gaining to 349 mm and is 74 % efficient at the 200 mm the ceiling allows (appendix). The PETG next to the motor runs at about the motor temperature, within 1 K. " +
"Next: a SolidWorks thermal study and a 90-minute hold test at 1.5 A. Fallback: 1.35 A.",
{ eq: { title: "Motor heat, P = I² R", lines: [
  "At 1.06 A: (1.06 A)² × 1.8 Ω = 2.0 W",
  "At 1.5 A: (1.5 A)² × 1.8 Ω = **4.05 W**",
] } });

content("Weight Budget: Open Issue", [
  "Lift capacity at 1.5 A: 1.56 kg",
  "Claw with battery estimated at 0.86 kg [[weighed]]",
  "1 lb test fits; jeans are 0.2 kg over",
  "Next: a lighter claw or a gear reduction at each winch",
], { sheet: "lift_budget", tab: "Lift budget" },
"Be upfront: even at 1.5 A the claw plus jeans is too heavy, by about 0.2 kg (it was 0.66 kg at 1.06 A). Root cause: I set the mass budget late, after the claw grew. " +
"k = 1.101 is the worst cable tension per unit weight over the room with 2 m/s²: the middle of a long wall at task height. " +
"Claw estimate: 0.55 fill × 927 g solid + 198 g tube + 55 g servo ≈ 0.76 kg, plus 0.10 kg battery. " +
"A 2:1 or 3:1 gear stage at each winch clears it with margin and lets the current drop back to about 1 A, which also halves the heat; the pull test result picks the fix.",
{ eq: { title: "Lift capacity", lines: [
  "m_{max} = F_{design} / (k g)",
  "= 16.8 / (1.101 × 9.81) = **1.56 kg**",
  "Needed with jeans: **1.76 kg**",
] } });

// ================================================================================================ PHASE 5: BUILD AND TEST
divider(5, "Build and Test", "October 22 – October 27", "Build the stations and run the first system test",
        "This week: print, machine, wire, then the three-station test.");

content("Printing and Machining", [
  "Printed holes come out at least 0.2 mm undersize: the spool took three prints",
  "Fit coupons are now printed before full parts",
  "Fin holes drilled in one mill setup to ±0.1 mm",
], { grid: [R("spool_v2.png"), R("spool_v3.png"), PH("03_mill_setup_with_shop_drawing.jpg"), PH("15_heat_fin_finished_part.jpg")],
     alt: "Printing and machining", caption: "Spool v2 (bore too tight) and v3, fin mill setup, finished fin" },
"PETG on a Creality K1 at 0.2 mm layers; flat face on the bed, loads along the layers, heat-set M3 inserts where screws are reused. " +
"Spool: v1 was longer than the shaft could engage; v2's Ø5.2 bore printed too tight on the 5 mm shaft; v3 opened it to Ø5.45 (0.25 mm clearance) with a D-flat. " +
"Fin: a 1:1 shop drawing used as the hole template; a 7/8 in pilot for the motor boss and four Ø3.4 holes on the 31 mm square, all from the same two edges so errors do not stack. " +
"The prototype is 0.019 in sheet I had; the design is 1/8 in plate. [Fill in: time per fin, how many made.]");

content("Electronics Bring-Up", [
  "Driver stays off at boot, so a reset cannot move a motor",
  "First motor failed to turn: logic rail at 1.14 V, not 3.3 V",
  "Supply rails are now checked with a meter before any code",
], { file: [PH("19_station_perfboard_soldered.jpg"), PH("12_bench_bringup_laptop.jpg")], alt: "Station board and bench bring-up",
     caption: "Soldered station board and bench bring-up" },
"Boot-safe: a 10k pull-up holds the driver's enable pin off until the firmware arms it. USB and the 5 V buck cannot back-feed each other (link jumper plus a Schottky diode). " +
"The schematic is generated from the soldered board's net list (16 nets), so the two cannot disagree. The 1.14 V story: measure the hardware before trusting the software's view of it. " +
"[Fill in: exact readings, date, what you tried first.]");

content("First System Test", [
  "Three stations: the fewest cables that fully hold the claw",
  "Self-check, calibration, short move, then pickup",
  "1 lb first, then one garment; pass limits set before the run",
], (sl, x, y, w, h) => {
  placeholderBox(sl, "[[Photo or video from the three-station test]]", x, y, w, 2.6);
  table(sl, ["Check", "Pass limit", "Result"], [
    ["Self-check", "All stations answer; slack taken up", "[[]]"],
    ["Calibration", "Held-out poses inside the margin", "[[]]"],
    ["Short move, 1 lb", "300 mm at 50 mm/s, ≤ 2 mm per cable", "[[]]"],
    ["Pickup", "One garment into the hamper", "[[]]"],
  ], x, y + 2.8, w, [0.27, 0.53, 0.2], { size: 13, rowH: 0.48, name: "pass limits" });
}, "Three cables, three unknown tensions, three force equations: statically determinate, so slack shows up directly. It is the simplest real test of calibration " +
"and coordinated motion. Logged: cable lengths, encoder counts, motor temperatures, the fit's error bars. Fill in the results after the test, including any that fail.");

content("Thermal Verification", [
  "PETG mount must stay below 60 °C",
  "Hand calculation, SolidWorks study, then a 90-minute hold test",
  "The PETG runs at about the motor temperature",
], (sl, x, y, w, h) => {
  placeholderBox(sl, "[[SolidWorks temperature plot: motor, fin, screws and mount]]", x, y, w, 2.6);
  table(sl, ["Method", "0.019 in fin", "1/8 in fin"], [
    ["Hand calculation", "56–59 °C", "45–49 °C"],
    ["SolidWorks", "[[]]", "[[]]"],
    ["Hold test", "[[]]", "[[]]"],
  ], x, y + 2.8, w, [0.4, 0.3, 0.3], { size: 14, rowH: 0.5, name: "thermal methods" });
}, "The 60 °C limit is for the loaded PETG. The SolidWorks study uses my 10/21 assembly with a detailed NEMA 17 (aluminum end caps, black steel stator, copper windings as the " +
"4.05 W source), the fin, the four M3 screws and the PETG mount. An independent 3-D check showed the PETG next to the motor runs at about the motor temperature, within 1 K. " +
"If the calculation, simulation and test disagree, I fit the convection coefficient and the coil resistance, not the physics.");

// ================================================================================================ RESULTS AND LESSONS
section("Results and Lessons");
{
  const sl = blank("Results Against Targets");
  const NOT = { text: "Not met", color: HEX.red, bold: true };
  table(sl, ["Target", "Goal", "Current", "Status"], [
    ["Lift capacity", "1.76 kg with jeans", "1.56 kg (calculated)", NOT],
    ["Claw mass", "0.45 kg", "0.86 kg with battery; [[weighed]]", NOT],
    ["Motor temperature", "Below 60 °C", "45–49 °C with the 1/8 in fin", "Met in design"],
    ["Working area", "Full 11 × 9 ft floor", "All but 0.2 m along the walls", "Met in design"],
    ["Wiring", "One cable per station", "One 12 V pair; 0.51 V drop", "Met"],
    ["Accuracy", "2 mm per cable", "0.7 mm (calculated)", "To be tested"],
    ["Speed", "50 mm/s at 2 m/s²", "Not yet run", "To be tested"],
    ["Cost", "Hobby budget", "[[total cost]]", "[[]]"],
  ], M, 1.3, W - 2 * M, [0.22, 0.25, 0.35, 0.18], { size: 15, rowH: 0.6 });
  sl.addNotes("Back to the targets from the start. Two are not met, and they are the same problem: lift capacity and claw mass. Motor temperature and working area " +
              "are met by the design and wait on the hold test; accuracy and speed wait on the system test.");
}

{
  const sl = blank("Good and Poor Decisions");
  const cw = [0.38, 0.62];
  table(sl, ["Good decision", "Result"], [
    ["One controller per winch", "Five times less wire; each station tested alone"],
    ["Camera calibration instead of bead homing", "Whole room reachable"],
    ["Gear strength checked at servo stall", "Failure caught in CAD, before printing"],
  ], M, 1.3, W - 2 * M, cw, { size: 16, rowH: 0.55, name: "good decisions" });
  table(sl, ["Poor decision", "Result"], [
    ["Mass budget set late", "0.2 kg over capacity with jeans"],
    ["Bead homing as the first plan", "Under a third of the room reachable"],
    ["Several stations built before one was proven", "Every fix repeated on each station [[confirm]]"],
  ], M, 3.95, W - 2 * M, cw, { size: 16, rowH: 0.55, headColor: HEX.red, name: "poor decisions" });
  sl.addNotes("Good: each was a trade I priced first. Distributed control cost software synchronization but saved five times the wire. Calibration by camera " +
              "replaced a plan that physically limited the motion. The stall check caught gears that would have sheared. " +
              "Poor: the mass budget came after the claw grew, which is the open issue today. Bead homing looked cheap until I computed what it cost. " +
              "Building several stations before one was fully proven meant repeating each fix. Also the spool printed before a fit coupon: three prints. [Confirm the stations one.]");
}

content("Thorough vs. Scrappy", [
  "Thorough where a mistake is expensive or unsafe",
  "- Heat fin: one mill setup, ±0.1 mm",
  "- Gears: strength checked before printing",
  "Scrappy where it is cheap to undo",
  "- Failed controller replaced by a jumpered ESP32 board",
  "- Floor board printed on paper",
], { file: [PH("03_mill_setup_with_shop_drawing.jpg"), P("docs/electrical/station_revD_20261021/breadboard_layout_esp32.png")],
     alt: "Mill setup and jumpered ESP32 board", caption: "Thorough: fin mill setup. Scrappy: jumpered ESP32 controller board." },
"Thorough: the fin is machined once, so the hole pattern had to be right before the first cut; the board schematic is generated from the soldered net list; " +
"the gear check happened in CAD because a sheared gear costs a print and a jammed claw. Scrappy: when a controller board died two days before the test, I moved the same " +
"circuit to an ESP32 dev board with nine jumpers and a compile-time pin map instead of redesigning the board. The floor board is paper because accuracy comes from " +
"seeing several tags, not from the board. The prototype fin is the 0.019 in sheet I already had.");

content("Lessons Learned", [
  "Set the mass budget first, from the measured winch pull",
  "Prove one station before building the rest",
  "Print fit coupons before full parts",
  "In half the time: freeze requirements in week 1 and order long-lead parts on day 1",
], (sl, x, y, w, h) => scheduleBars(sl, x, y + 1.5, w),
"What I would do differently: weigh the claw and set its budget from the measured pull before designing it; one complete station tested end to end before building more; " +
"coupons before every new fit; a meter on every rail before debugging code. Half the time: most lost time was the redesign and the generations a frozen requirement " +
"and an early test would have avoided. Three stations are statically determinate and need fewer parts for the first test.",
{ figW: 7.4 });

{
  pres.addSection({ title: "Close" });
  const sl = pres.addSlide({ masterName: "SECTION", sectionTitle: "Close" });
  sl.addText("Questions", { x: M, y: 2.8, w: 11, h: 1.0, fontSize: 48, bold: true, color: "FFFFFF", fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addText("Jasper Buntinx  |  jasper_buntinx@tamu.edu", { x: M, y: 3.9, w: 11, h: 0.6, fontSize: 20, color: HEX.pale, fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addNotes("The appendix covers fin sizing, the operating sequence and phone app, control logic, claw electrical, acronyms and the calculation sources.");
}

// ================================================================================================ APPENDIX
section("Appendix");
{
  const sl = pres.addSlide({ masterName: "SECTION", sectionTitle: SECTION });
  sl.addText("Appendix", { x: M, y: 2.8, w: 11, h: 1.0, fontSize: 44, bold: true, color: "FFFFFF", fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addNotes("");
}

content("Heat Fin Length", [
  "0.019 in prototype reaches 95 % of its capacity by 136 mm",
  "1/8 in design keeps gaining to 349 mm",
  "Built at 200 mm, limited by ceiling clearance",
], { sheet: "heat_fin", tab: "Heat fin" },
"L95 is where a fin carries 95 % of the heat an infinitely long one would. h = 7 W/m²·K still air, k = 160 W/m·K aluminum. At 200 mm: sheet 37 % efficient and " +
"22.1 K/W; 1/8 in plate 74 % and 10.9 K/W. Source: Incropera, Fundamentals of Heat and Mass Transfer, ch. 3.",
{ eq: { title: "Fin length and efficiency", lines: [
  "m = √(2h / (k t)),   L_{95} = 1.83 / m",
  "η = tanh(mL) / (mL) = **0.74** (1/8 in)",
] } });

content("Fin Sizing for 4 W", [
  "If the fin alone had to carry all 4.05 W",
  "0.019 in sheet: not possible at any length",
  "1/8 in plate: 145–185 mm",
], (sl, x, y, w, h) => {
  table(sl, ["Painted 6061, 44 mm wide", "Mass", "Shortest for ≤ 60 °C"], [
    ["0.019 in (prototype)", "14 g", "None (2.0 W max)"],
    ["1/16 in", "47 g", "None (3.6 W max)"],
    ["0.090 in", "68 g", "210 mm or none"],
    ["1/8 in (design)", "94 g", "145–185 mm"],
    ["3/16 in", "141 g", "125–140 mm"],
    ["1/4 in", "189 g", "115–125 mm"],
  ], x, y, w, [0.45, 0.17, 0.38], { size: 14, rowH: 0.52, name: "fin sizing" });
  caption(sl, "All 4.05 W through the fin, 23 °C room, paste contact. Calculated.", x, y + 7 * 0.52 + 0.12, w);
}, "The prototype works today only because the motor also sheds heat into the vented shell. A thin sheet's far end does almost nothing: the most heat any length " +
"can carry is w √(2hkt) θ_b, about 2 W for 0.019 in at a 60 °C base (approximate, about 10 % low). Thickness beats length.");

content("Operating Sequence", [
  "Start up: self-check, take up slack, calibrate",
  "Find: scan from above, detect garments, choose the nearest",
  "Pick: hover until still, grip, deliver; the camera confirms each step",
  "Every move waits for approval on the phone; PAUSE holds position",
], { file: [P("docs/app_screenshots/01_home.png"), P("docs/app_screenshots/02_camera.png"), P("docs/app_screenshots/04_chat.png")],
     alt: "Phone app screens", caption: "Phone app: home, live claw camera and chat" },
"A fault or PAUSE stops every station at the same point on the path, still holding; nothing restarts by itself, and a reboot never resumes a task. " +
"Known obstacles are keep-out cylinders and every cable is checked against them before a move. People are not detected, so nobody stands underneath. " +
"Three failures in a row pause for the operator. Disarm needs a typed confirmation because releasing torque drops a hanging claw. Simulated end to end.");

{
  const sl = blank("Control Logic: Generation 1 vs. Final");
  table(sl, ["", "Generation 1", "Final"], [
    ["Where is the claw?", "Assumed from the commanded cable lengths", "Measured by the claw camera; refit at every startup"],
    ["Room geometry", "Anchors from a tape measure", "Anchors and cable lengths fitted, with error bars"],
    ["Motor control", "One central board", "A controller per station, coordinated by the laptop"],
    ["Finding laundry", "Ceiling camera", "Claw camera"],
    ["Did the grab work?", "Assumed", "Camera checks pickup and delivery"],
    ["Faults", "Emergency stop only", "A stop keeps torque; nothing restarts by itself"],
  ], M, 1.3, W - 2 * M, [0.2, 0.36, 0.44], { size: 15, rowH: 0.65 });
  sl.addNotes("Generation 1 trusted its model; the final logic measures before it trusts and checks after it acts. Kept from generation 1: the cable math, the " +
              "state-machine idea and the YOLO-World detector.");
}

content("Claw Electrical", [
  "Two-cell lithium-ion pack: 7.4 V with a 5 A fuse",
  "6 V servo rail and a separate 5 V logic rail",
  "Peak 2.8–3.1 A against a 3 A pack rating",
], { file: R("kicad_claw_revB.png"), alt: "Claw schematic", caption: "Claw schematic" },
"Rules check 0 errors; 9 nets match the specification. Charger: 8.4 V constant current, constant voltage; charged with the switch off, attended, at 1 A or less.");

{
  const sl = blank("Acronyms");
  table(sl, ["Term", "Meaning"], [
    ["CAD", "Computer-aided design"],
    ["PETG", "Polyethylene terephthalate glycol (the printed plastic)"],
    ["TPU", "Thermoplastic polyurethane (flexible printed plastic)"],
    ["NEMA 17", "National Electrical Manufacturers Association motor frame, 1.7 in square"],
    ["CNC", "Computer numerical control"],
    ["ESP32", "A Wi-Fi microcontroller family (Espressif)"],
    ["A4988", "Stepper-motor driver chip (Allegro)"],
    ["YOLO", "“You Only Look Once”: an object-detection model family"],
    ["SF", "Safety factor: allowable stress divided by actual stress"],
  ], M, 1.3, W - 2 * M, [0.22, 0.78], { size: 15, rowH: 0.52 });
  sl.addNotes("");
}

{
  const sl = content("Calculations and Sources", [
    "All charts come from my engineering calculation sheet",
    "Incropera et al., Fundamentals of Heat and Mass Transfer, ch. 3",
    "Allegro MicroSystems, A4988 datasheet",
  ], { sheet: "cable_tension", tab: "Cable tension" }, "");
  sl.addText([{ text: "RoomCleaner engineering calculations (Google Sheets)", options: { hyperlink: { url: SHEET_URL, tooltip: "Open the calculation sheet" } } }],
             { x: 8.05, y: 4.6, w: 4.7, h: 0.4, fontSize: 15, color: HEX.navy, fontFace: "Arial", margin: 0, isTextBox: true, objectName: "sheet link" });
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
