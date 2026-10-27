// RoomCleaner deck v10 (Oct 27): the simple format of the reference deck, Jasper's flow (DECK_V10_BRIEF.md).
// White slides, bold black title top-left, light-grey cards with a bold heading and short bullets, photos right or in
// cards, a thin black footer bar ("ROOMCLEANER" letter-spaced, page number right), plain title and thank-you slides.
// Content contract: docs/presentation/DECK_V10_BRIEF.md. Every number traces to the record files named in each slide's
// speaker notes (DECK_V9_NOTES.md, PANEL_FEEDBACK_ANSWERS_20261026.md, DESIGN_INTENT_20261027.md, CALIBRATION_SIMPLE.md,
// COST_BREAKDOWN_20261026.md, FUNDAMENTALS.md, calculations/). Chart data is the v8/v9 calculation-sheet data, drawn natively.
//
//   NODE_PATH=<pptxgenjs node_modules> APPLY_THEME=<pptx skill>/scripts/apply_theme.js \
//     node docs/presentation/deck_v10/build_deck_v10.js
"use strict";
const path = require("path");
const fs = require("fs");
const { execFileSync } = require("child_process");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(process.env.APPLY_THEME);
const { size: imgSize } = require("../deck_v2/img_size.js");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const P = (...p) => path.join(ROOT, ...p);
const PH = f => P("docs/presentation/photos", f);
const R = f => P("docs/presentation/deck_assets/renders", f);
const SC = f => P("docs/presentation/deck_assets/screens", f);
const V8FIG = f => P("docs/presentation/deck_v8/fig", f);
const OUT = path.join(__dirname, "RoomCleaner_Buntinx_v10.pptx");
const CHARTDIR = path.join(__dirname, "fig");            // chart PNGs rendered by make_charts.py from chart_data.json (v10.1)

// ------------------------------------------------------------------------------------------------ theme
const THEME = {
  name: "RoomCleaner v10", headFontFace: "Arial", bodyFontFace: "Arial",
  colors: { dk1: "000000", lt1: "FFFFFF", dk2: "404040", lt2: "F2F2F2", accent1: "1F3A5F", accent2: "8A8F98",
            accent3: "BFC4CB", accent4: "404040", accent5: "D9DEE5", accent6: "5B6470", hlink: "1F3A5F", folHlink: "4F6D8F" },
};
const HEX = { ink: "000000", mid: "404040", grey: "8A8F98", light: "F2F2F2", pale: "BFC4CB", navy: "1F3A5F", white: "FFFFFF", rule: "D9DEE5" };

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";                      // 10 x 5.625 in
pres.author = "Jasper Buntinx";
pres.title = "RoomCleaner";
pres.theme = { headFontFace: "Arial", bodyFontFace: "Arial" };
const C = pres.SchemeColor;
const W = 10, H = 5.625, M = 0.4;
const TOP = 0.95, BOT = 5.05;                    // content band
const FOOT_Y = 5.3, FOOT_H = 0.325;

// Layouts: CONTENT (title placeholder + footer bar + page number), PLAIN (footer only, for the title and thank-you slides).
const footer = [
  { rect: { x: 0, y: FOOT_Y, w: W, h: FOOT_H, fill: { color: HEX.ink }, line: { color: HEX.ink } } },
  { text: { text: "ROOMCLEANER", options: { x: M, y: FOOT_Y, w: 3, h: FOOT_H, fontSize: 8, color: HEX.white, fontFace: "Arial",
                                             charSpacing: 6, valign: "middle", margin: 0 } } },
];
pres.defineSlideMaster({
  title: "CONTENT", background: { color: "FFFFFF" },
  objects: [
    ...footer,
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.28, w: W - 2 * M, h: 0.55, fontSize: 24, bold: true,
                                color: HEX.ink, fontFace: "Arial", valign: "middle", align: "left", margin: 0 }, text: "Title" } },
  ],
  slideNumber: { x: W - M - 0.6, y: FOOT_Y, w: 0.6, h: FOOT_H, fontSize: 8, color: HEX.white, align: "right", fontFace: "Arial", valign: "middle" },
});
pres.defineSlideMaster({
  title: "PLAIN", background: { color: "FFFFFF" }, objects: [...footer],
  slideNumber: { x: W - M - 0.6, y: FOOT_Y, w: 0.6, h: FOOT_H, fontSize: 8, color: HEX.white, align: "right", fontFace: "Arial", valign: "middle" },
});

// ------------------------------------------------------------------------------------------------ helpers
let SECTION = "";
function section(name) { SECTION = name; pres.addSection({ title: name }); }
function slide(title, notes, o = {}) {
  const sl = pres.addSlide({ masterName: "CONTENT", sectionTitle: SECTION });
  if (o.titleSize) sl.addText(title, { x: M, y: 0.28, w: W - 2 * M, h: 0.55, fontSize: o.titleSize, bold: true, color: C.text1, valign: "middle",
                                       align: "left", margin: 0, isTextBox: true, objectName: "title" });
  else sl.addText(title, { placeholder: "title" });
  if (notes) sl.addNotes(notes);
  return sl;
}
// "(calculated)" style qualifiers stay plain; "**x**" makes a bold run.
function runs(text, base) {
  const out = [];
  const re = /\*\*(.+?)\*\*/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push({ text: text.slice(last, m.index), options: { ...base } });
    out.push({ text: m[1], options: { ...base, bold: true } });
    last = re.lastIndex;
  }
  if (last < text.length) out.push({ text: text.slice(last), options: { ...base } });
  return out;
}
function bullets(sl, items, x, y, w, h, size = 11, o = {}) {
  const arr = [];
  items.forEach((it, i) => {
    const sub = it.startsWith("- ");
    const t = sub ? it.slice(2) : it;
    const base = { fontSize: sub ? size - 1 : size, color: sub ? C.text2 : C.text1,
                   bullet: { indent: sub ? 10 : 12 }, indentLevel: sub ? 1 : 0, paraSpaceAfter: o.space == null ? 4 : o.space, align: "left" };
    const rs = runs(t, base);
    rs.forEach((r, j) => { r.options.breakLine = j === rs.length - 1 && i < items.length - 1; });
    arr.push(...rs);
  });
  sl.addText(arr, { x, y, w, h, valign: "top", align: "left", margin: [0, 2, 0, 0], isTextBox: true, objectName: o.name || "bullets" });
}
// Light-grey card: ONE rectangle shape that carries its own heading and bullets (v10.2). Earlier builds drew a grey shape and
// separate text boxes on top; the iOS/macOS Quick Look renderer layered those wrongly and hid the text. With the text inside the
// shape there is nothing to mis-layer. o.gapIn leaves empty space under the heading for content placed on top (slide 4).
function card(sl, x, y, w, h, heading, items, o = {}) {
  const pad = 0.16, size = o.size || 11, headSize = o.headSize || 12.5;
  const gapPt = o.gapIn ? o.gapIn * 72 : 6;
  const arr = [{ text: heading, options: { fontSize: headSize, bold: true, color: HEX.ink, paraSpaceAfter: gapPt, align: "left",
                                            breakLine: !!(items && items.length) } }];
  (items || []).forEach((it, i) => {
    const sub = it.startsWith("- ");
    const t = sub ? it.slice(2) : it;
    const base = { fontSize: sub ? size - 1 : size, color: sub ? HEX.mid : HEX.ink, bullet: { indent: sub ? 10 : 12 },
                   indentLevel: sub ? 1 : 0, paraSpaceAfter: o.space == null ? 4 : o.space, align: "left" };
    const rs = runs(t, base);
    rs.forEach((r, j) => { r.options.breakLine = j === rs.length - 1 && i < items.length - 1; });
    arr.push(...rs);
  });
  sl.addText(arr, { shape: pres.shapes.RECTANGLE, x, y, w, h, fill: { color: HEX.light }, line: { color: HEX.light, width: 0 },
                    valign: "top", align: "left", margin: [pad * 72, pad * 72, pad * 72, pad * 72], objectName: `card ${heading}` });
  const by = y + 0.44;
  return { x: x + pad, y: by, w: w - 2 * pad, h: h - 0.54 };
}
function fitImage(sl, file, x, y, w, h, alt, o = {}) {
  const d = imgSize(file);
  const s = Math.min(w / d.w, h / d.h), dw = d.w * s, dh = d.h * s;
  const dx = x + (o.left ? 0 : (w - dw) / 2), dy = y + (o.top ? 0 : (h - dh) / 2);
  sl.addImage({ path: file, x: dx, y: dy, w: dw, h: dh, altText: alt, objectName: alt.slice(0, 40) });
  return { x: dx, y: dy, w: dw, h: dh };
}
// Photo cropped to fill a box (v10.1): the build records a crop job, crop_photos.py (PIL) centre-crops the source to the box's
// exact aspect ratio into img/<name>_<w>x<h>.jpg, and the picture is placed with plain w/h (no sizing option, no stretch).
const IMGDIR = path.join(__dirname, "img");
const CROP_JOBS = [];
function coverImage(sl, file, x, y, w, h, alt) {
  const out = path.join(IMGDIR, `${path.basename(file, path.extname(file))}_${w.toFixed(2)}x${h.toFixed(2)}.jpg`);
  if (!CROP_JOBS.some(j => j.out === out)) CROP_JOBS.push({ src: file, w, h, out });
  sl.addImage({ path: out, x, y, w, h, altText: alt, objectName: alt.slice(0, 40) });
}
function cropPhotos() {
  fs.writeFileSync(path.join(__dirname, "crop_jobs.json"), JSON.stringify(CROP_JOBS, null, 1));
  execFileSync("/usr/bin/python3", [path.join(__dirname, "crop_photos.py")], { stdio: "inherit" });
}
function caption(sl, text, x, y, w, o = {}) {
  sl.addText(text, { x, y, w, h: 0.22, fontSize: 8.5, color: C.text2, margin: 0, isTextBox: true, align: o.align || "left", objectName: "caption" });
}
// Row of photos with captions, each fitted into equal boxes.
function photoRow(sl, list, x, y, w, h, o = {}) {
  const g = o.gap == null ? 0.12 : o.gap, n = list.length, each = (w - g * (n - 1)) / n;
  list.forEach(([file, cap], i) => {
    const bx = x + i * (each + g);
    if (o.cover) coverImage(sl, file, bx, y, each, h - (cap ? 0.26 : 0), cap || path.basename(file));
    else fitImage(sl, file, bx, y, each, h - (cap ? 0.26 : 0), cap || path.basename(file), { top: true });
    if (cap) caption(sl, cap, bx, y + h - 0.22, each);
  });
}
function placeholderBox(sl, text, x, y, w, h) {
  sl.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: HEX.white }, line: { color: HEX.grey, width: 1, dashType: "dash" }, objectName: "placeholder" });
  sl.addText(text, { x: x + 0.15, y, w: w - 0.3, h, fontSize: 12, color: C.text2, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "placeholder text" });
}
// v10.1: charts are PNGs. The build writes chart_data.json (data + box size in inches) and runs make_charts.py, then places the
// images with addImage at the same boxes. (Native pptxgenjs charts made PowerPoint report the file as needing repair.)
const CHART_DATA = {};
function chartImage(sl, name, x, y, w, h, alt) {
  sl.addImage({ path: path.join(CHARTDIR, `${name}.png`), x, y, w, h, altText: alt, objectName: `chart ${name}` });
}
function renderCharts() {
  fs.writeFileSync(path.join(__dirname, "chart_data.json"), JSON.stringify(CHART_DATA, null, 1));
  execFileSync("/usr/bin/python3", [path.join(__dirname, "make_charts.py")], { stdio: "inherit" });
}
const r1 = v => Math.round(v * 10) / 10;

// ------------------------------------------------------------------------------------------------ chart data (record)
// Cable tension vs depth: T = W / (4 sin phi), Dh = 2.166 m (room centre to anchor), W = weighed claw 0.60 kg + 1 lb.
// FUNDAMENTALS.md section 1 / calculations/presentation_fundamentals.json topic 1; weighed claw per DECK_V8_NOTES.md.
const DH = 2.166, M_CLAW_LB = 0.60 + 0.45359, G = 9.81, A_DYN = 2.0, WINCH_LIMIT = 16.8;
const depths = [0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2];
const tension = (d, a) => r1(M_CLAW_LB * (G + a) / (4 * (d / Math.sqrt(d * d + DH * DH))));
// Winch pull vs spool radius at 1.5 A: running torque 0.7 x 0.36 N.m holding (assumed), design force = running / 1.5.
// calculations/lift_chain_weakest_link.json fuse.run_empty 33.6 N (r 7.5 mm), run_full 25.2 N (r 10 mm); design_force 16.8.
const radii = [6, 7, 7.5, 8, 9, 10, 11];
const runPull = r => r1(0.7 * 0.36 / (r / 1000)), designPull = r => r1(runPull(r) / 1.5);
const JEANS_PEAK = 16.2;                        // worst cable, jeans, lift_chain_weakest_link.md "Demand and the fuse"
// Motor case temperature at 1.5 A, 23 C room: deck_v8/fig/sheet_motor_temperature (Sheet "Motor temperature"); PETG limit 60 C.
const TEMP = { labels: ["Vented shell", "Sealed shell"], noFin: [77.2, 99.1], thin: [57.6, 66.3], plate: [48.9, 53.8], limit: 60 };
// Lift budget (kg): sheet_lift_budget; 0.86 kg CAD estimate with battery (DESIGN_STATE 10/22; PANEL_FEEDBACK_ANSWERS slide 16).
const LIFT = { labels: ["Claw + jeans", "Claw + 1 lb", "Claw, weighed", "Claw, CAD estimate", "Capacity, worst point"],   // bottom to top
               values: [1.50, 1.05, 0.60, 0.86, 1.56], budget: 0.45 };
// Weakest link: cable tension at which each part gives, low / high (lift_chain_weakest_link.md ranking; chart capped at 600 N).
const WL = [["Set screw, printed", 22, 64], ["Motor slip (fuse)", 34, 59], ["Set screw, metal", 53, 118], ["Tab as drawn", 70, 82],
            ["Tab 6 mm", 125, 147], ["Motor shaft", 149, 255], ["Line knot", 267, 480], ["Screws in stud", 531, 600]].reverse();   // weakest at top
// Bead homing: reachable share of the working volume vs homing height (calculations/bead_reach.json).
const BEAD = [[0.3, 0.0], [0.6, 0.4], [0.8, 1.8], [1.0, 4.7], [1.2, 9.1], [1.5, 17.1], [1.8, 25.0], [2.0, 29.1], [2.19, 32.0]];

// ================================================================================================ 1. Title
section("Opening");
{
  const sl = pres.addSlide({ masterName: "PLAIN", sectionTitle: SECTION });
  sl.addText("RoomCleaner", { x: M, y: 1.7, w: 6, h: 0.9, fontSize: 40, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "deck title" });
  sl.addText("A four-cable ceiling robot that picks laundry off the floor", { x: M, y: 2.6, w: 6, h: 0.5, fontSize: 16, color: C.text2, margin: 0, isTextBox: true, objectName: "subtitle" });
  sl.addText("Jasper Buntinx  |  Mechanical Engineering  |  Texas A&M", { x: M, y: 3.4, w: 6, h: 0.4, fontSize: 13, color: C.text1, margin: 0, isTextBox: true, objectName: "byline" });
  sl.addText("October 27, 2026", { x: M, y: 3.8, w: 6, h: 0.3, fontSize: 11, color: C.text2, margin: 0, isTextBox: true, objectName: "date" });
  coverImage(sl, PH("42_claw_hanging_three_cables_room_corner.jpg"), 6.6, 0, 3.4, FOOT_Y, "The claw hanging from three cables in the room corner (Oct 27)");
  sl.addNotes("Title. Photo 42: the claw suspended from three cables in the room corner, the first time it hangs (docs/presentation/photos/README.md, row 42, Oct 27). " +
              "Byline per DECK_V10_BRIEF.md (name | Mechanical Engineering | Texas A&M). Subtitle wording from DECK_V9_NOTES.md slide 1 title.");
}

// ================================================================================================ 2. About me
{
  const sl = slide("About me",
    "About me. The three collage columns are Jasper's About Me collage (docs/presentation/photos/README.md, about_me/ row, 10/22): outdoors and endurance " +
    "(hikes, Ironman 70.3, 2025 marathon), engineering (EcoFil, team photo), community (Gladiator Dash for Still Creek Ranch). Degree and school per " +
    "the brief's byline. Nothing else on the slide; add numbers only from memory you can back up.");
  const cols = [["about_outdoors.png", "Outdoors and endurance"], ["about_engineering.png", "Engineering"], ["about_community.png", "Community"]];
  const bx = 3.55, bw = W - M - bx, g = 0.12, ih = BOT - TOP - 0.26;
  const ar = cols.map(([f]) => { const d = imgSize(PH(`about_me/${f}`)); return d.w / d.h; });
  const scale = Math.min(ih, (bw - 2 * g) / ar.reduce((a, b) => a + b, 0));
  let cx = bx;
  cols.forEach(([f, cap], i) => {
    const iw = scale * ar[i];
    sl.addImage({ path: PH(`about_me/${f}`), x: cx, y: TOP, w: iw, h: scale, altText: cap, objectName: f });
    caption(sl, cap, cx, TOP + scale + 0.04, iw);
    cx += iw + g;
  });
  // Three stacked cards in the left column (text supplied by Jasper, 10/27)
  const cw2 = bx - M - 0.25, gap = 0.1, hEdu = 0.78, hHob = 1.62, hExp = (BOT - TOP) - hEdu - hHob - 2 * gap;
  card(sl, M, TOP, cw2, hEdu, "Education: Texas A&M", [
    "Bachelor's, Mechanical Engineering, August 2027",
  ], { size: 10.5, space: 4 });
  card(sl, M, TOP + hEdu + gap, cw2, hExp, "Experience", [
    "ITP Lab, undergraduate research",
    "Rochester Sensors, mechanical intern",
    "Petrobras, mechanical intern",
    "Aggies Create, EcoFil electrical lead",
  ], { size: 10.5, space: 4 });
  card(sl, M, TOP + hEdu + hExp + 2 * gap, cw2, hHob, "Hobbies", [
    "Personal projects",
    "Soccer",
    "Running",
    "Bouldering",
    "And man, do I love hiking.",
  ], { size: 10.5, space: 4 });
}

// ================================================================================================ 3. Project scope
section("Scope");
{
  const sl = slide("Project scope",
    "Scope. Room 3.35 x 2.74 m under a 2.74 m ceiling, as reported (DECK_V9_NOTES.md slide 3; v9.1 origins). Design load 0.9 kg jeans, a screening value, " +
    "plus 2 m/s^2 assumed (REQUIREMENTS R1/R7 via v9.1). Four winches in the studs, one claw on four cables (slide 3 row). PAUSE holds torque; the switched " +
    "power strip is the emergency stop and drops the claw (D21 via slide 3). Success: one garment floor to hamper, each move approved on the phone; first gate " +
    "a 1 lb test weight (D19). Cost: $210.78 of parts in the robot for three stations plus $37.74 filament, prices partly estimated (COST_BREAKDOWN_20261026.md headline table). " +
    "Photo 42 (README row 42).");
  const cw = (W - 2 * M - 2 * 0.2 - 2.3) / 3, ch = BOT - TOP;
  card(sl, M, TOP, cw, ch, "The problem", [
    "Laundry on the floor of a 3.35 x 2.74 m room (as reported)",
    "Ceiling 2.74 m; four studs near the ceiling corners",
    "Design load: a pair of jeans, 0.9 kg (screening value)",
    "Plus 2 m/s² for stops and snags (assumed)",
  ]);
  card(sl, M + cw + 0.2, TOP, cw, ch, "The solution", [
    "Four ceiling winches, one claw on four cables",
    "Nothing on the floor; the room is the frame",
    "A camera on the claw finds the laundry",
    "Floor to hamper with no human touch",
  ]);
  card(sl, M + 2 * (cw + 0.2), TOP, cw, ch, "How we do it", [
    "I approve each move on the phone",
    "PAUSE holds position with torque on",
    "The switched power strip is the emergency stop; it drops the claw",
    "First gate: a 1 lb test weight, then jeans",
    "Parts in the robot: about $211 for three stations, plus $38 filament (partly estimated)",
  ]);
  coverImage(sl, PH("42_claw_hanging_three_cables_room_corner.jpg"), W - M - 2.1, TOP, 2.1, ch - 0.26, "The claw hanging in the room corner");
  caption(sl, "The claw hanging in the room corner (Oct 27)", W - M - 2.1, BOT - 0.22, 2.1);
}

// ================================================================================================ 4. Cable length, torque, tension
section("Fundamentals");
{
  const sl = slide("How cable length becomes position, and torque becomes pull",
    "Fundamentals. Card A: straight taut cable, L_i = ||a_i - p|| (roomcleaner/cdpr/kinematics.py docstring; the full form adds R b_i for the spaced " +
    "attachments). Line per revolution 2 pi r: 47.1 mm at r 7.5 mm to 62.8 mm at r 10 mm (FUNDAMENTALS.md section 2, spool-core study table: Ø15 core, full radius 10.0 mm). Four cable lengths " +
    "against three position unknowns: overdetermined, least squares (kinematics.py docstring; the TENSION split is the indeterminate one); the camera on the floor board fits the anchors and cable lengths at startup " +
    "(DECK_V9_NOTES slide 15); held-out poses check the fit (CALIBRATION_SIMPLE step 5, 'surprise spots'): SIMULATED, no physical position measurement. " +
    "Card B: I = Vref / (8 R_s), tau_hold = tau_rated I / I_rated, tau_run = 0.7 tau_hold assumed, F = tau / r (FUNDAMENTALS section 2); at 1.5 A, the motor's " +
    "rated current (DECISIONS D37), tau_hold 0.36 N.m, tau_run 0.7 x 0.36 = 0.252 N.m, running pull 0.252 / 0.0075 = 33.6 N and 0.252 / 0.010 = 25.2 N (calculations/lift_chain_weakest_link.json " +
    "fuse.run_empty / run_full). Vref MEASURED on the board; 0.7 ASSUMED; pull test PLANNED (FUNDAMENTALS section 2 evidence line). " +
    "Card C: T = W / (4 sin phi), sin phi = d / sqrt(d^2 + D_h^2); W = (0.4536 + 0.45) x 9.81 = 8.86 N (1 lb + the 0.45 kg claw budget), D_h = sqrt(1.676^2 + 1.372^2) = 2.166 m; " +
    "32.1 / 16.2 / 8.3 / 4.6 N at 0.15 / 0.3 / 0.6 / 1.2 m (FUNDAMENTALS section 1 table, recomputed); T ~ W D_h / (4 d) for a shallow cable; " +
    "keep the claw at least 0.4 m below the anchors; CALCULATED, no tension measured on the rig (FUNDAMENTALS section 1). Figure: deck_v3/fig/position_vectors.png.",
    { titleSize: 20 });
  const g = 0.2, cw = (W - 2 * M - 2 * g) / 3, ch = BOT - TOP;
  // A white boxed panel (thin black border) for the equations inside a card; returns its height.
  const eqBox = (x, y, w, lines) => {
    // lines[0] names the typeset PNG from make_equations.py (fig/eq_*.png); the box is sized to the image.
    const file = P("docs/presentation/deck_v10/fig", lines[0] + ".png");
    const d = imgSize(file);
    const iw = w - 0.2, ih = iw * d.h / d.w, h = ih + 0.16;
    sl.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: HEX.white }, line: { color: HEX.ink, width: 0.75 }, objectName: "equation box" });
    sl.addImage({ path: file, x: x + 0.1, y: y + 0.08, w: iw, h: ih, altText: lines.slice(1).join("; "), objectName: "equations" });
    return h;
  };
  const cards3 = [
    ["Cable length → position", ["eq_a", "L_i = ‖ a_i − p ‖", "a_i: anchor exit, p: claw", "straight, taut cable"], [
      "Line per spool turn = 2π·r: 2π·7.5 mm = 47.1 mm (empty) → 2π·10 mm = 62.8 mm (full) (calculated)",
      "Four cable lengths, three position unknowns: overdetermined, solved by least squares",
      "The camera on the floor board fixes the anchors and cable lengths at startup (calibration)",
      "Validated in the simulator and by held-out poses during calibration (simulated); no physical position measurement yet",
    ]],
    ["Torque → pull on the line", ["eq_b", "I = Vref / (8·R_s)", "τ_hold = τ_rated · I / I_rated", "τ_run ≈ 0.7 τ_hold (assumed)", "F = τ / r"], [
      "At 1.5 A: τ_run = 0.7 × 0.36 N·m = 0.252 N·m; F = 0.252 / 0.0075 m = 34 N empty, 0.252 / 0.010 m = 25 N full (calculated)",
      "Validated: Vref measured on the board; the 0.7 running fraction is assumed; the pull test is planned",
    ]],
    ["Pull → what four cables hold", ["eq_c", "T = W / (4 sin φ)", "sin φ = d / √(d² + D_h²)"], [
      "W = (0.454 + 0.45 kg) × 9.81 = 8.86 N, D_h = 2.166 m; d = 0.15 m: 8.86 / (4 × 0.069) = 32 N; 16 / 8.3 / 4.6 N at 0.3 / 0.6 / 1.2 m (calculated)",
      "Shallow cable: T ≈ W·D_h / (4d), so halving the depth doubles the tension",
      "Why the planner keeps the claw at least 0.4 m below the anchors",
      "Validated: calculated only; no cable tension has been measured on the rig",
    ]],
  ];
  cards3.forEach(([h, eq, items], i) => {
    const x = M + i * (cw + g);
    const pad = 0.16, ix = x + pad, iw = cw - 2 * pad, iy = TOP + 0.44;
    // height of the equation area first, so the card's own text can start below it
    const fw = 0.86;
    const eqW = i === 0 ? iw - fw - 0.1 : iw;
    const d = imgSize(P("docs/presentation/deck_v10/fig", eq[0] + ".png"));
    const eqH = (eqW - 0.2) * d.h / d.w + 0.16;
    const area = i === 0 ? Math.max(eqH, fw) : eqH;
    card(sl, x, TOP, cw, ch, h, items, { headSize: 12, size: 10, space: 4, gapIn: area + 0.2 });
    if (i === 0) fitImage(sl, P("docs/presentation/deck_v3/fig/position_vectors.png"), ix + iw - fw, iy, fw, fw, "Cable vectors from the anchors to the claw", { top: true });
    eqBox(ix, iy, eqW, eq);
  });
}

// ================================================================================================ 5. Generation 1
section("Generation 1");
{
  const sl = slide("Generation 1: one central unit",
    "Generation 1. One central unit (an Uno with a CNC shield) drove all four corner motors over wires run to each corner; an overhead ceiling camera scanned " +
    "the room (DESIGN_INTENT_20261027.md 'Iteration 1'; DECK_V9_NOTES.md v9.2 slide 7 row; DECISIONS D33 for the ceiling camera). A printed corner plate " +
    "screwed into a joist replaced hanging hooks: a hook is a pivot, about 1:1 anchor error to claw error (slide 8 row, D13). Each cable homed against a " +
    "crimped bead at the outlet (PANEL_FEEDBACK_ANSWERS, 'what bead homing is'). Bench: the station lifted a test weight (slide 8 row; the weight and height " +
    "not logged). Photos 05, 13, 14 (README rows).");
  const cw = 3.6, ch = BOT - TOP;
  card(sl, M, TOP, cw, ch, "The first design", [
    "One Uno and one CNC shield drove four corner motors",
    "Wires from that one box to every corner",
    "An overhead ceiling camera scanned the room",
    "A printed corner plate screwed into a joist: a hook is a pivot, a plate is not",
    "Each cable found zero against a bead at the outlet",
    "Bench: a station lifted a test weight; the cable math held (measured)",
  ], { space: 5 });
  const px = M + cw + 0.25, pw = W - M - px;
  const ph = (ch - 0.26 - 0.15) / 2;
  coverImage(sl, PH("14_gen1_cnc_shield_a4988.jpg"), px, TOP, pw / 2 - 0.06, ph, "CNC shield with four A4988 drivers");
  coverImage(sl, PH("05_gen1_spool_plate.jpg"), px + pw / 2 + 0.06, TOP, pw / 2 - 0.06, ph, "Gen-1 corner plate: motor, spool, pulley, switch");
  fitImage(sl, PH("13_gen1_station_lifting_test_weight.jpg"), px, TOP + ph + 0.15, pw, ph, "Gen-1 station lifting a test weight", { top: true, left: true });
  caption(sl, "The central board; a gen-1 corner plate; a gen-1 station lifting a test weight", px, BOT - 0.22, pw);
}

// ================================================================================================ 6. Problems with Generation 1
{
  const sl = slide("Problems with Generation 1",
    "Problems with Gen 1. Every motor and sensor wired back to one place (DESIGN_INTENT_20261027.md 'Iteration 1'). One board stepping four motors: " +
    "the cables skew by dx = v dt = 50 mm/s x 0.05 s = 2.5 mm per 50 ms of timing error (DECK_V9_NOTES.md slide 10 row; 50 mm/s maximum cable speed, " +
    "FUNDAMENTALS.md section 2 supplied facts). The ceiling camera: one more device to mount, wire and calibrate in every room; the claw and cables hide the " +
    "grasp spot from above; its floor map assumes a flat floor; retired Oct 21 (DECISIONS.md D33). Bead homing limits the reachable volume: next slide. " +
    "Photo 14 (README row 14). Bench fixes from this period are in DOWN_THE_LINE.md.");
  const g = 0.2, pwid = 2.6, cw = (W - 2 * M - pwid - 2 * g) / 2, ch = BOT - TOP;
  card(sl, M, TOP, cw, ch, "One central board", [
    "Every motor and every sensor wired back to one place",
    "One board steps all four motors; a timing error skews the cables",
    "Skew Δx = v·Δt = 50 mm/s × 0.05 s = 2.5 mm per 50 ms (calculated)",
    "Moving a winch means re-running wire to the box",
  ], { space: 6 });
  card(sl, M + cw + g, TOP, cw, ch, "Ceiling camera and bead homing", [
    "The ceiling camera: one more device to mount, wire and calibrate per room",
    "From above, the claw and cables hide the grasp spot",
    "Its floor map assumes a flat floor; retired Oct 21",
    "Bead homing fixes a minimum length on every cable: next slide",
  ], { space: 6 });
  const px = W - M - pwid;
  coverImage(sl, PH("14_gen1_cnc_shield_a4988.jpg"), px, TOP, pwid, ch - 0.26, "CNC shield with four A4988 drivers");
  caption(sl, "The central board: one shield, four drivers", px, BOT - 0.22, pwid);
}

// ================================================================================================ 7. Homing: beads vs floor board
section("Homing");
{
  const sl = slide("Homing: one floor board instead of four beads",
    "Homing. Bead homing: a stopper bead cannot pass its outlet, so after homing no cable can be shorter than at home; homing all four with the claw at one " +
    "pose fixes a minimum length on every cable at once: reachable(p) iff ||a_i - p|| >= L_i,home for every i (calculations/bead_reach.py docstring). " +
    "Reachable share = fraction of grid points in the working volume (60 x 50 x 50 grid, 0.2 m wall margin, z 0.3 to 2.19 m) that satisfy it, home at the room " +
    "centre: 0.0 % at 0.3 m up, 4.7 % at 1.0 m, 29.1 % at 2.0 m, 32.0 % at 2.19 m (calculations/bead_reach.json). Floor board: nine US-Letter sheets, one " +
    "AprilTag 36h11 per sheet, 150 mm tags, 250 mm pitch, id 0 = origin (tools/print_floor_board.py; make_floor_board_figure.py). The camera measures the claw " +
    "pose against the board; cable lengths follow from L_i = ||a_i - p|| (roomcleaner/cdpr/kinematics.py docstring); the startup fit estimates anchors and " +
    "zero lengths (roomcleaner/cdpr/startup.py, SLACK_TAKEUP to CALIBRATION). No length is clamped, so the whole working volume stays available. Beads stay on " +
    "the cables as end-of-travel switches (startup.py docstring, REFERENCE_VERIFICATION).");
  const g = 0.15, ch = BOT - TOP;
  const lw = 2.95, cwid = 2.05, rw = W - 2 * M - lw - cwid - 2 * g;
  // Left card: equation panel under the heading, then the bullets.
  const eqFile = path.join(CHARTDIR, "eq_d.png"), ed = imgSize(eqFile);
  const pad = 0.16, eqW = lw - 2 * pad, eqH = (eqW - 0.16) * ed.h / ed.w + 0.16;
  card(sl, M, TOP, lw, ch, "Bead homing", [
    "A stopper bead cannot pass its outlet: after homing, no cable can be shorter than at home",
    "Homing all four at once fixes a minimum length on every cable at the same time",
    "Reachable volume, grid count (calculated): 0.0 % (home 0.3 m) to 32.0 % (home 2.19 m); 4.7 % at 1.0 m, 29.1 % at 2.0 m",
  ], { size: 10, space: 5, headSize: 12, gapIn: eqH + 0.18 });
  sl.addShape(pres.shapes.RECTANGLE, { x: M + pad, y: TOP + 0.44, w: eqW, h: eqH, fill: { color: HEX.white }, line: { color: HEX.ink, width: 0.75 }, objectName: "equation box" });
  sl.addImage({ path: eqFile, x: M + pad + 0.08, y: TOP + 0.44 + 0.08, w: eqW - 0.16, h: (eqW - 0.16) * ed.h / ed.w,
                altText: "reachable(p) if and only if ||a_i - p|| >= L_i,home for every cable i", objectName: "equation" });
  // Bead-reach chart beside it.
  const cx = M + lw + g;
  CHART_DATA.bead = { title: "Reachable volume (%)", points: BEAD, box: { w: cwid, h: ch - 0.3 } };
  chartImage(sl, "bead", cx, TOP, cwid, ch - 0.3, "Reachable share of the working volume vs bead homing height (calculated)");
  caption(sl, "Grid count of the condition above", cx, BOT - 0.22, cwid);
  // Right card: the floor board, figure in the lower part of the card.
  const rx = cx + cwid + g;
  card(sl, rx, TOP, rw, ch, "Floor-board homing", [
    "The camera measures the claw pose against tag 0",
    "Cable lengths follow from L_i = ‖a_i − p‖",
    "No length is clamped: the whole working volume stays available",
    "Nine sheets, 150 mm tags, 250 mm pitch, id 0 = origin",
  ], { size: 10, space: 4, headSize: 12 });
  const fd = imgSize(path.join(CHARTDIR, "floor_board.png")), fh = 2.3, fw = fh * fd.w / fd.h;
  fitImage(sl, path.join(CHARTDIR, "floor_board.png"), rx + (rw - fw) / 2, BOT - fh - 0.1, fw, fh, "Floor board: nine AprilTag 36h11 sheets, 150 mm tags, 250 mm pitch, id 0 is the origin");
}

// ================================================================================================ 8. What a winch on a wall needs
section("What a winch needs");
{
  const sl = slide("What a winch on a wall needs to work",
    "What a winch needs. A motor bolted to a wall cannot just run: a camera can fail, a spool can overwind, tension can rip a mount out, a motor can stall; " +
    "so each winch gets a switch (button) and a spool encoder (DESIGN_INTENT 'Why it changed'). The encoder measures discrepancies while testing; if the " +
    "camera proves good enough it can go later; data first (same). Its two jobs today: confirm every commanded step, catch slip as the tension sensor " +
    "(DECK_V9_NOTES slide 20 row). Fail-safe switch wiring: LOW at rest, HIGH pressed or with a broken wire (slide 20 row). Beads stay as end-of-travel " +
    "switches (PANEL_FEEDBACK_ANSWERS 'bead homing'). Wiring from one box: routes 6 + 21 + 23 + 32 = 82 ft, x 10 conductors = 820 ft (250 m) " +
    "(DECK_V2_OUTLINE.md line 85; DECK_V9_NOTES v9.2 slide 10 row). " +
    "Photos 09, 23, 39 (README rows).");
  const cw = (W - 2 * M - 0.2 - 3.0) / 2, ch = 2.55, g = 0.2;
  card(sl, M, TOP, cw, ch, "The switch (button)", [
    "Things go wrong: a camera fails, a spool overwinds, tension rips a mount out, a motor stalls",
    "A switch the cable's bead can hit: that station stops",
    "Fail-safe wiring: LOW at rest, HIGH pressed or with a broken wire",
  ], { space: 5 });
  card(sl, M + cw + g, TOP, cw, ch, "The encoder", [
    "On the spool: measures the discrepancies while testing; data first",
    "Confirms every commanded step",
    "Catches slip: the tension sensor",
    "If the camera proves good enough, it can go later",
  ], { space: 5 });
  card(sl, M, TOP + ch + 0.15, 2 * cw + g, BOT - TOP - ch - 0.15, "And now all this wiring, from one box", [
    "Motor, switch and encoder in every corner: 10 conductors per corner",
    "Routes 6 + 21 + 23 + 32 = 82 ft; × 10 conductors = 820 ft (250 m) of wire to one box (calculated)",
  ], { space: 5 });
  const px = W - M - 2.8;
  photoRow(sl, [[PH("09_homing_switch_perfboard.jpg"), "Homing switch"], [PH("23_slide_in_switch_pressfit.jpg"), "Switch pressed into the slide-in"]], px, TOP, 2.8, 2.0, { cover: true });
  coverImage(sl, PH("39_slide_in_handheld_wiring_hanging.jpg"), px, TOP + 2.1, 2.8, BOT - TOP - 2.1 - 0.26, "Slide-in with the full harness hanging");
  caption(sl, "One slide-in, its harness hanging", px, BOT - 0.22, 2.8);
}

// ================================================================================================ 9. The solution: a modular box
section("Modular box");
{
  const sl = slide("The solution: a modular box that only needs power",
    "Modular box. Each box has its own ESP32 and everything it needs; the only thing entering is power, on a thicker wire (DESIGN_INTENT 'Iteration 2'). " +
    "82 ft of routes x 2 conductors = 164 ft (50 m) instead of x 10 = 820 ft (250 m) (DECK_V2_OUTLINE.md line 85). Any position and orientation (DESIGN_INTENT). Wire drop: V = I R' L_loop; " +
    "longest branch 32 ft one way, 64 ft of loop; 16 AWG loop resistance 0.257 ohm over 64 ft = 4.02 ohm/kft; at 2 A: 2 x 0.257 = 0.51 V, 2 A illustrative (FUNDAMENTALS.md section 10; " +
    "Gen 1 comparison: 24 AWG motor leads, Jasper 10/27, computed with the same formula: R = rho 2L / A, rho = 1.724e-8 ohm m, L = 32 ft = 9.75 m one way, " +
    "AWG diameter 0.127 mm x 92^((36 - n)/39): 24 AWG A = 0.205 mm^2, R = 1.64 ohm, V = 2 x 1.64 = 3.29 V (27 % of 12 V), P = I^2 R = 6.6 W; " +
    "16 AWG A = 1.309 mm^2, R = 0.257 ohm, 0.51 V (4.3 %), 1.0 W (FUNDAMENTALS section 10 table). " +
    "PANEL_FEEDBACK_ANSWERS 'How longer wires increase voltage drop'). Cost: 16 AWG 100 ft roll $30.00 (est.), 65 ft used for three stations, $19.50 prorated " +
    "(COST_BREAKDOWN_20261026.md section 1, 16 AWG row). Photos 33, 46 (README rows); SolidWorks screenshot of the station shell, transparent (deck_assets/screens).");
  const cw = (W - 2 * M - 0.2 - 3.1) / 2, ch = BOT - TOP, g = 0.2;
  card(sl, M, TOP, cw, ch, "A box with its own brain", [
    "An ESP32 in each box, with its driver, buck, switch and encoder",
    "The only thing going in is power: one 12 V pair",
    "82 ft × 2 conductors = 164 ft (50 m) of wire, not 820 ft (calculated)",
    "Power can come from anywhere, so a box sits in any position and orientation",
    "The room's geometry no longer limits where the winches go",
  ], { space: 5 });
  card(sl, M + cw + g, TOP, cw, ch, "Wire drop: Gen 1 leads vs one power pair", [
    "V = I·ρ·2L/A; copper ρ = 1.724×10⁻⁸ Ω·m, L = 9.75 m (32 ft) one way, I = 2 A",
    "24 AWG Gen 1 motor leads, A = 0.205 mm²: R = 1.64 Ω, 3.29 V (27 % of 12 V), 6.6 W (calculated)",
    "16 AWG power pair, A = 1.309 mm²: R = 0.257 Ω, 0.51 V (4.3 %), 1.0 W (calculated)",
    "Thin motor leads over a room-length run lose a quarter of the supply; one thick power pair loses 4 %",
    "16 AWG: $30 per 100 ft × 65 ft = $19.50 (price estimated)",
  ], { size: 10, space: 4 });
  const px = W - M - 2.9;
  coverImage(sl, PH("46_wall_mount_bracket_xt60_power_lead.jpg"), px, TOP, 2.9, 1.95, "Wall mount with its XT60 power connector");
  caption(sl, "The wall mount: one power plug", px, TOP + 1.98, 2.9);
  fitImage(sl, SC("station_shell_transparent_1022.png"), px, TOP + 2.3, 2.9, BOT - TOP - 2.3 - 0.26, "Station shell, transparent (SolidWorks)");
  caption(sl, "The station: board, driver, motor, fin (CAD)", px, BOT - 0.22, 2.9);
}

// ================================================================================================ 10. Modular, for the everyday user
{
  const sl = slide("Modular, for the everyday user",
    "Everyday use. Plug and play: once a box works it works; it slides on and off the wall and plugs and unplugs; guests come, each box slips off and goes " +
    "in a drawer; back on, one plug, it joins the Wi-Fi by itself (DESIGN_INTENT 'Iteration 2'). Slip the station out of the mount to open the electronics, " +
    "close it, slide it back; no unscrewing from the wall: the wall mount and its screws stay in the stud (DECK_V9_NOTES slide 12 row 'One plug per station'). " +
    "A product, not a tangle: individual packaged boxes with one plug and a Wi-Fi setup (DESIGN_INTENT). The mount is separate: today a slide-in screwed into " +
    "a stud, later a clamp onto a pole, like gym equipment (DESIGN_INTENT). Photos 45, 24, 31 (README rows).");
  const cw = 3.4, ch = (BOT - TOP - 0.15) / 2;
  card(sl, M, TOP, cw, ch, "Unmount, remount, plug in", [
    "A box slides off its wall mount and unplugs",
    "Guests coming: each box goes in a drawer",
    "Back on: one plug, it joins the Wi-Fi by itself",
  ], { space: 5 });
  card(sl, M, TOP + ch + 0.15, cw, ch, "No screwdriver on the wall", [
    "Slip the station out of the mount, open the electronics",
    "Close it, slide it back: the mount and its screws stay in the stud",
    "The mount is separate: a stud today, a pole clamp later",
  ], { space: 5 });
  const px = M + cw + 0.25, pw = W - M - px;
  photoRow(sl, [[PH("45_wall_mount_bracket_alone_corner.jpg"), "The wall mount alone, lead hanging"], [PH("24_station_housing_on_wall.jpg"), "The station slid onto it"],
                [PH("31_station_bench_xiao_breadboard_shell_open.jpg"), "Shell open on the bench"]], px, TOP, pw, BOT - TOP, { cover: true });
}

// ================================================================================================ 11. Trade-offs
section("Trade-offs");
{
  const sl = slide("Trade-offs: what each component needs",
    "Trade-offs, all calculated unless marked. Tension vs depth: T = W / (4 sin phi) with the weighed claw plus 1 lb; at 0.4 m below the anchors 14.3 N static, " +
    "17.2 N with 2 m/s^2, against the 16.8 N winch limit; with jeans the claw stays 0.6 m down (DECK_V9_NOTES slide 6 row; FUNDAMENTALS section 1). Motor " +
    "temperature at 1.5 A, 23 C room: no fin 77.2 / 99.1 C vented / sealed, 0.019 in prototype fin 57.6 / 66.3, 1/8 in design fin 48.9 / 53.8; PETG limit 60 C " +
    "(deck_v8/fig/sheet_motor_temperature; calculations/fin_sizing_4w.md coupled results 55.9-58.8 C vented). Winch pull: 0.7 x 0.36 N.m holding (0.7 assumed) " +
    "over the spool radius: 34 N empty core, 25 N full; design force = running / 1.5 = 16.8 N; jeans worst cable 16.2 N (calculations/lift_chain_weakest_link.md " +
    "'Demand and the fuse'; slide 17 row). Weight: 0.45 kg budget (R7), 0.86 kg CAD estimate with battery, 0.60 kg weighed 10/22 (PANEL_FEEDBACK_ANSWERS slide 16); " +
    "capacity m = F_design / (k g) = 16.8 / (1.101 x 9.81) = 1.56 kg, k = 1.101 the worst-cable tension per unit weight (LP, lift_chain_weakest_link.md; winch_gear3.json direct_drive.capacity_kg 1.555); " +
    "jeans 1.50 kg: (1.56 - 1.50) / 1.50 = 4 %. Motor temperature chart: two-node thermal network (fin_sizing_4w.py), input P = I^2 R = 1.5^2 x 1.8 = 4.05 W; no temperature measured. " +
    "Tension Need line: 1 lb + 0.60 kg claw at d 0.4 m: 1.054 x 11.81 / (4 x 0.1816) = 17.1 N; jeans + claw 1.50 kg at d 0.6 m: 16.6 N. Weakest link: cable tension at which each part gives, one station at 1.5 A " +
    "(lift_chain_weakest_link.md ranking table): motor slip 0.36 / 0.0075 = 48 N; low 48 / sqrt 2 = 33.9 N; high 0.36 x 40/36 / 0.0075 / cos 26.05 deg = 59.4 N (json fuse); the set screw in the printed thread 22-64 N may give first, so it moves " +
    "into a metal insert; screws in a stud 531 N and up (bar capped at 600).");
  const g = 0.15, cols = 3, cw = (W - 2 * M - (cols - 1) * g) / cols, ch = (BOT - TOP - g) / 2;
  const at = (c, r) => ({ x: M + c * (cw + g), y: TOP + r * (ch + g) });
  const need = (p, text) => sl.addText(text, { x: p.x, y: p.y + ch - 0.3, w: cw, h: 0.3, fontSize: 8.5, color: C.text1, bold: true, margin: 0, valign: "middle",
                                                isTextBox: true, objectName: "what we need" });
  const box = { w: cw, h: ch - 0.3 };
  // 1. Tension vs depth
  let p = at(0, 0);
  CHART_DATA.tension = { title: "Tension per cable (N) vs depth (m)", depths, static: depths.map(d => tension(d, 0)), dynamic: depths.map(d => tension(d, A_DYN)), limit: WINCH_LIMIT, box };
  chartImage(sl, "tension", p.x, p.y, cw, ch - 0.3, "Tension per cable vs depth below the anchors: static, with 2 m/s2, winch limit (calculated)");
  need(p, "T = m(g + a) / (4 sin φ): 1 lb at d 0.4 m → 17.1 N vs 16.8 N limit; jeans need d ≥ 0.6 m (16.6 N)");
  // 2. Motor temperature
  p = at(1, 0);
  CHART_DATA.temperature = { title: "Motor case (°C) at 1.5 A; PETG limit 60 °C", labels: TEMP.labels, noFin: TEMP.noFin, thin: TEMP.thin, plate: TEMP.plate, limit: TEMP.limit, box };
  chartImage(sl, "temperature", p.x, p.y, cw, ch - 0.3, "Motor case temperature at 1.5 A, vented and sealed shell, by fin (calculated)");
  need(p, "Need < 60 °C. Two-node thermal network; input P = I²R = 1.5² × 1.8 Ω = 4.05 W");
  // 3. Winch pull
  p = at(2, 0);
  CHART_DATA.pull = { title: "Pull per winch (N) vs spool radius (mm), 1.5 A", radii, running: radii.map(runPull), design: radii.map(designPull), jeans: JEANS_PEAK, box };
  chartImage(sl, "pull", p.x, p.y, cw, ch - 0.3, "Pull per winch vs spool radius at 1.5 A: running pull, design force, jeans worst cable (calculated)");
  need(p, "F = 0.252 N·m / r: 34 N (7.5 mm), 25 N (10 mm); ÷ 1.5 = 16.8 N ≥ 16.2 N jeans");
  // 4. Weight budget
  p = at(0, 1);
  CHART_DATA.lift = { title: "Winches can hold vs must hold (kg)", labels: LIFT.labels, values: LIFT.values, colors: ["#1F3A5F", "#8A8F98", "#8A8F98", "#BFC4CB", "#1F3A5F"], box };
  chartImage(sl, "lift", p.x, p.y, cw, ch - 0.3, "What the winches can hold vs what they must hold, kg (measured claw, calculated capacity)");
  need(p, "16.8 N / (1.101 × 9.81) = 1.56 kg vs 1.50 kg: +4 %; claw 0.60 kg weighed vs 0.45 budget");
  // 5. Weakest link
  p = at(1, 1);
  CHART_DATA.weakest = { title: "Tension at which each part gives (N)", rows: WL, box };
  chartImage(sl, "weakest", p.x, p.y, cw, ch - 0.3, "Cable tension at which each part of the lifting chain gives, one station at 1.5 A (calculated)");
  need(p, "Motor slip 0.36 N·m / 7.5 mm = 48 N; × 1/√2 = 34 N, × 1.11 / cos 26° = 59 N");
  // 6. The factors, in words
  p = at(2, 1);
  card(sl, p.x, p.y, cw, ch, "The factors", [
    "Pull ∝ I; heat P = I²R ∝ I²",
    "1.0 → 1.5 A: pull × 1.5, heat × 1.5² = 2.25 (calculated)",
    "Every gram on the claw is a gram of payload",
    "The printed set screw (22–64 N) may slip before the motor: metal insert",
    "The pull test and the hold test are planned",
  ], { size: 10, space: 4 });
}

// ================================================================================================ 12. Mount assembly: the design
section("Mount assembly");
{
  const sl = slide("The mount assembly: slide-in on a dovetail",
    "Mount assembly 1. Slide-in wall mount: the station lifts off its dovetail; the wall mount and its screws stay in the stud (DECK_V9_NOTES slide 12 row). " +
    "Load path: cable, spool, set screw, motor, PETG tab, slide-in, wall mount, screws, stud (same row; lift_chain_weakest_link.md 'The chain and the rule'). " +
    "The motor slips at 34-59 N before anything breaks, the designed fuse; the spool encoder sees the spool fall behind the commanded steps: a tracking fault, " +
    "every station holds (slide 13 row). Fuse: 0.36 / 0.0075 = 48 N, 33.9 to 59.4 N (lift_chain_weakest_link.md 'The chain and the rule'). Dovetail 0.175 mm a side " +
    "on 30 deg flanks, measured on Jasper's STEP files (PANEL_FEEDBACK_ANSWERS 'Manufacturing fits', row 'Slide-in mount'; deck_v8 fits table). Photos 45, 24; " +
    "snap_dovetail.png (deck_v8/fig); station_shell_transparent_1022.png.");
  const cw = 3.5, ch = BOT - TOP;
  card(sl, M, TOP, cw, ch, "Slide-in mount and load path", [
    "The wall mount screws into a stud; the station slides onto it on a dovetail",
    "Dovetail clearance 0.175 mm per side on 30° flanks (measured on the CAD)",
    "Load path: cable, spool, set screw, motor, tab, mount, screws, stud",
    "Motor slips first: F = τ/r = 0.36 N·m / 7.5 mm = 48 N; 34–59 N over torque vector and cable angle (calculated)",
    "The spool encoder sees the slip: tracking fault, every station holds",
  ], { space: 5 });
  const px = M + cw + 0.25, pw = W - M - px, g = 0.12;
  const topH = 2.1;
  coverImage(sl, PH("45_wall_mount_bracket_alone_corner.jpg"), px, TOP, (pw - g) / 2, topH, "The printed wall mount alone in a corner");
  coverImage(sl, PH("24_station_housing_on_wall.jpg"), px + (pw + g) / 2, TOP, (pw - g) / 2, topH, "The station shell on its wall mount");
  caption(sl, "The mount alone, before the station slides in; the station on the mount", px, TOP + topH + 0.03, pw);
  const by = TOP + topH + 0.3, bh = BOT - by - 0.26;
  fitImage(sl, V8FIG("snap_dovetail.png"), px, by, pw * 0.62, bh, "Slide-in rib in the wall-mount dovetail (CAD)", { top: true });
  fitImage(sl, SC("station_shell_transparent_1022.png"), px + pw * 0.62 + g, by, pw * 0.38 - g, bh, "Station shell, transparent (SolidWorks)", { top: true });
  caption(sl, "Rib in the dovetail groove (CAD); the station with its shell transparent (CAD)", px, BOT - 0.22, pw);
}

// ================================================================================================ 13. Mount assembly: on the wall
{
  const sl = slide("The mount assembly: fin, vents and the wall",
    "Mount assembly 2. The aluminium fin bolts to the motor face and goes out through a slot in the top of the shell; the shell is vented (DECK_V9_NOTES slide 16 " +
    "and 22 rows; README rows 27, 34, 36). Heat P = I^2 R = 1.5^2 x 1.8 = 4.05 W, 1.8 ohm assumed (FUNDAMENTALS section 3). The fin temperatures " +
    "come from a two-node thermal network (fin_sizing_4w.py) and are not on the slide. First station in a stud on the TV wall, 12 V down the wall (slide 22 row). Load path and fuse as on the previous slide. A 1 deg draft " +
    "on the dovetail is the NEXT iteration: the slide-in binds on insertion today (slide 24 row). Photos 32, 33, 44 (README rows).");
  const cw = 3.5, ch = BOT - TOP;
  card(sl, M, TOP, cw, ch, "Fin, vents, stud", [
    "The fin: aluminium on the motor face, out through a slot in the top of the shell",
    "Motor heat P = I²R = 1.5² × 1.8 Ω = 4.05 W leaves through vents and fin (calculated)",
    "First station in a stud on the TV wall, 12 V down the wall",
    "The slide-in binds on insertion today; a 1° draft on the dovetail is the next iteration",
  ], { space: 5 });
  const px = M + cw + 0.25, pw = W - M - px;
  photoRow(sl, [[PH("32_wall_station_mounted_tv_wall.jpg"), "On the TV wall, 12 V leads down"], [PH("33_wall_station_mounted_closeup_wires.jpg"), "From below: fin through the slot"],
                [PH("44_wall_station_from_below_line_down.jpg"), "The line leaves the switch tab straight down"]], px, TOP, pw, BOT - TOP, { cover: true });
}

// ================================================================================================ 14. Manufacturing
section("Manufacturing");
{
  const sl = slide("Manufacturing: what was made in-house, and how fits were controlled",
    "Manufacturing. Process: PETG on a Creality K1, 0.4 mm nozzle, 0.20 mm layers, supports at 30 deg (photos 20, 26; deck_v8 'Manufacturing: Fits and Datums' " +
    "printing rules: loads along the layers, mating faces off supports). Fin: blank sheared 44 x 250 mm (+/-0.5), five holes drilled in one setup on the manual " +
    "mill; the edges locate only the first hole, which becomes the mill zero, so the pattern holds +/-0.1 (DECISION_STORIES.md T31/T32 line 277; photo 01). " +
    "Heat-set inserts: M3 in the claw gear housing, M2.5 at the encoder board (deck_v8 fits table). TPU 95A: pad trials (DESIGN_INTENT 'The gripper'); none " +
    "in the current build, the hands are PETG (COST_BREAKDOWN section 2; D32). Fits: printed holes come out undersize (FUNDAMENTALS section 12); spool bore " +
    "Ø5.2 printed too tight on the Ø5.0 shaft, opened to Ø5.45 in v3 (FUNDAMENTALS section 12 supplied facts); dovetail 0.175 mm per side on 30 deg flanks, " +
    "measured on Jasper's STEP files (deck_v8 fits table; PANEL_FEEDBACK_ANSWERS fits row); 687 bearing pocket Ø14.075 behind a Ø14.000 entry lip, 1.95 mm " +
    "long, 8 T-slots (FUNDAMENTALS section 12; snap_gear_lip.png from make_mfg_snapshots.py). The hole-sweep fit coupon (Ø5, Ø7, Ø14, -0.10 to +0.30 mm) is " +
    "PLANNED (FUNDAMENTALS section 12 evidence line). One shell kept a failed layer: a shell, not a load path (DECK_V9_NOTES slide 19 row; photo 35). " +
    "Make vs buy: bought steppers, drivers, controller boards, servo, camera, battery, encoder boards (DECK_V9_NOTES slide 4 row); made: every printed part " +
    "and the fin. Printed per station 762 g (estimate: CAD volume x 1.27 g/cm^3 x fill factor, COST_BREAKDOWN section 2); filament 0.762 kg x $15/kg = $11.43 " +
    "per station; station-only bought parts about $23.70 per station; robot $210.78 parts + $37.74 filament for three stations, prices partly estimated " +
    "(COST_BREAKDOWN headline table and section 1 note).",
    { titleSize: 17 });
  const g = 0.15, lw = 3.05, mw = 2.95, rw = W - 2 * M - lw - mw - 2 * g;
  const h1 = 2.2, h2 = BOT - TOP - h1 - g;
  card(sl, M, TOP, lw, h1, "Processes", [
    "PETG, FDM: 0.4 mm nozzle, 0.20 mm layers, supports at 30°; loads along the layers",
    "Aluminium fin: sheared blank, five holes drilled in one mill setup",
    "First hole is the mill zero: pattern ±0.1 mm vs ±0.5 mm sheared edges",
    "Heat-set inserts: M3 gear housing, M2.5 encoder board",
  ], { size: 9.5, space: 3, headSize: 11.5 });
  card(sl, M, TOP + h1 + g, lw, h2, "Make vs buy", [
    "Bought: steppers, drivers, boards, servo, camera, battery, encoders",
    "Made: every printed part and the fin",
    "Filament per station: 0.762 kg × $15/kg = $11.43 (estimated)",
    "Robot: $210.78 parts + $37.74 filament, three stations (partly estimated)",
  ], { size: 9.5, space: 3, headSize: 11.5 });
  card(sl, M + lw + g, TOP, mw, BOT - TOP, "Fits", [
    "Printed holes come out undersize: every printed fit carries an allowance",
    "Spool bore: Ø5.2 printed too tight on the Ø5.0 shaft; opened to Ø5.45",
    "Dovetail: 0.175 mm per side, 30° flanks (CAD)",
    "Bearing pocket Ø14.075 behind a Ø14.000 entry lip, 8 T-slots",
    "Hole-sweep fit coupon (Ø5, Ø7, Ø14): planned",
    "A failed layer was kept on one shell only: the shell carries no load",
    "TPU 95A: pad trials only; none in the current build",
  ], { size: 9.5, space: 3, headSize: 11.5 });
  const rx = M + lw + mw + 2 * g, cwid = (rw - 0.1) / 2, ph = 1.15;
  coverImage(sl, PH("26_slicer_k1_petg_supports.jpg"), rx, TOP, cwid, ph, "Slicing PETG for the K1, supports at 30 degrees");
  coverImage(sl, PH("01_mill_drilling_fin_closeup.jpg"), rx + cwid + 0.1, TOP, cwid, ph, "Drilling the fin on the manual mill");
  caption(sl, "Slicer (K1, PETG); drilling the fin", rx, TOP + ph + 0.03, rw);
  const sy = TOP + ph + 0.32, sh = (BOT - sy - 0.26 - 0.1) / 2;
  fitImage(sl, V8FIG("snap_dovetail.png"), rx, sy, rw, sh, "Slide-in rib in the wall-mount dovetail (CAD section)", { top: true });
  fitImage(sl, V8FIG("snap_gear_lip.png"), rx, sy + sh + 0.1, rw, sh, "Gear bearing pocket with its entry lip (CAD)", { top: true });
  caption(sl, "Dovetail rib; bearing pocket and lip (CAD)", rx, BOT - 0.22, rw);
}

// ================================================================================================ 15. The claw
section("Claw");
{
  const sl = slide("The claw, and why it is modular",
    "Claw. Four-bar hands on the gear crank, 53 mm opening (CAD; the parallelism figure is a linkage model, not shown); a camera bay on the electronics housing; one 7.4 V two-cell pack, a 6 V regulator " +
    "for the servo, a 5 V buck for the board (DECK_V9_NOTES slide 18 row 'The claw'). The gripper attaches modularly at the tube, by design, a test bed for shirts " +
    "(DESIGN_INTENT 'The gripper'; v9.2 slide 18 row). A hard-material pinch was expected to grip better; testing showed alignment problems: the rack-and-pinion " +
    "jaws left a 2 mm gap on thin cloth, Sep 30 (v9.2 slide 18 row; no cloth-test reading logged). TPU and other pad materials being tried " +
    "(DESIGN_INTENT). The v6 clamp came out at 4.6x its mass budget in CAD, Oct 20; since then mass is tracked per part; the claw weighed 0.60 kg with battery " +
    "against the 0.45 kg budget (slide 11 and 17 rows). Photos 25, 40, 22; renders gripper1021_head.png, claw_v6.png.");
  const cw = (W - 2 * M - 0.2 - 3.9) / 2, ch = BOT - TOP, g = 0.2;
  card(sl, M, TOP, cw, ch, "The claw today", [
    "Four-bar hands on a geared crank; 53 mm opening (CAD)",
    "A camera bay in the electronics housing; the camera looks down the tube",
    "One 7.4 V two-cell pack: 6 V regulator for the servo, 5 V buck for the board",
    "Weighed 0.60 kg with battery against a 0.45 kg budget",
  ], { space: 5 });
  card(sl, M + cw + g, TOP, cw, ch, "Modular, on purpose", [
    "The gripper attaches at the tube, so other grippers can be tried",
    "A hard pinch was expected to grip better; testing showed alignment problems",
    "The first rack-and-pinion jaws left a 2 mm gap on thin cloth (Sep 30)",
    "TPU and other pad materials are being tried; still testing",
    "The v6 clamp was 4.6 x its mass budget in CAD: mass is tracked per part since",
  ], { space: 5 });
  const px = M + 2 * (cw + g), pw = W - M - px;
  coverImage(sl, PH("25_claw_assembled.jpg"), px, TOP, pw, 2.2, "The claw assembled (Oct 22)");
  const by = TOP + 2.2 + 0.12, bh = BOT - by - 0.26, bw = (pw - 2 * 0.1) / 3;
  fitImage(sl, R("gripper1021_head.png"), px, by, bw, bh, "Four-bar hands (CAD)");
  fitImage(sl, R("claw_v6.png"), px + bw + 0.1, by, bw, bh, "The v6 clamp (CAD)");
  coverImage(sl, PH("40_claw_housing_ubec_wagos_lit.jpg"), px + 2 * (bw + 0.1), by, bw, bh, "Electronics housing open");
  caption(sl, "Assembled; the hands (CAD); the v6 clamp (CAD); the housing open", px, BOT - 0.22, pw);
}

// ================================================================================================ 16. Electrical and testing
section("Electrical and testing");
{
  const sl = slide("Electrical and testing: bench, then wall",
    "Electrical. Station boards: the bench checklist (firmware/station_bench_test/README.md) passed on both boards, ELEGOO ESP32 and XIAO (DECK_V9_NOTES slide 20 " +
    "row, 10/25-10/26). Claw Rev B: camera live view, battery sense and servo pass on the bench (DECK_V9_NOTES slide 21 row; DESIGN_STATE 10/26). On the wall: " +
    "boxed stations boot and join Wi-Fi on their own; firmware updates over Wi-Fi; motors off until the phone arms them; updates accepted only while disarmed " +
    "(slide 22 row). Planned: pull test at 1.5 A, 90-minute hold test, first three-station lift (slides 25, 26). Bench details in DOWN_THE_LINE.md. Photos 43, 32 (README rows).");
  const cw = 3.6, g = 0.15, ch1 = 1.75, ch2 = BOT - TOP - ch1 - g;
  card(sl, M, TOP, cw, ch1, "Bench", [
    "Station boards: bench checklist passed on both controller boards (measured)",
    "Claw: camera live view, battery sense and servo pass (measured)",
  ], { space: 5 });
  card(sl, M, TOP + ch1 + g, cw, ch2, "On the wall", [
    "A boxed station boots and joins Wi-Fi by itself",
    "Firmware updates over Wi-Fi; no USB cable after boxing",
    "Motors stay off until the phone arms them; updates only while disarmed",
    "Planned: pull test, hold test, first three-station lift",
  ], { space: 5 });
  const px = M + cw + 0.25, pw = W - M - px;
  photoRow(sl, [[PH("43_bench_two_stations_laptop_meter_floor.jpg"), "Bench: two stations, laptop, meter, 12 V supply"],
                [PH("32_wall_station_mounted_tv_wall.jpg"), "The first station on the wall"]], px, TOP, pw, BOT - TOP, { cover: true });
}

// ================================================================================================ 17. Calibration
section("Calibration");
{
  const sl = slide("Startup and self-calibration: six states before the robot is READY",
    "Startup sequencer, roomcleaner/cdpr/startup.py: states and bounds in the module docstring (lines 1-66), run order in StartupSequencer.run (669-690): " +
    "SELF_CHECK (self_check, 693-761), SLACK_TAKEUP (slack_takeup, 763-848), INITIAL_LIFT (initial_lift, 849-930), VISUAL_INITIALIZATION (visual_init, " +
    "931-1166), CALIBRATION (calibrate, 1167-1436), REFERENCE_VERIFICATION (verify_references, 1437-1619). An abort holds motion with torque on and returns " +
    "PAUSED or FAULT; nothing retries by itself (run, 673-686; CALIBRATION_SIMPLE.md rules). Trust level VERIFIED by the margin check or by beads, else " +
    "LOCAL_ONLY with stated reasons (docstring REFERENCE_VERIFICATION / READY; D26). Tension is not measured in V1: the lift and calibration rely on geometric " +
    "consistency checks (docstring, last paragraph). All of this is designed and simulated; it has not run on the hardware. Photo 42 (README row 42).",
    { titleSize: 20 });
  const steps = [
    ["1  SELF_CHECK", ["Claw online, battery above minimum", "Camera confirms the claw upright at the known height on the floor board", "Stations healthy, homing switches closed; arm"]],
    ["2  SLACK_TAKEUP", ["One cable at a time reeled in until the camera sees the claw slide or tip (onset)", "Records spool position and slide bearing; backs off", "Bearings checked against the anchor layout; first fit of cable lengths"]],
    ["3  INITIAL_LIFT", ["Pretension all cables; lift in small packets", "Abort on lateral drift, tilt, or commanded lift exceeding observed rise (slack cable)"]],
    ["4  VISUAL_INITIALIZATION", ["Settled frame batch of the floor board", "Refit cable lengths and the room-to-marker transform"]],
    ["5  CALIBRATION", ["Local → intermediate → expanded pose sets chosen by D-optimal design; refit between stages", "Held-out witness poses", "Accept on witness residuals, identifiability, predicted length sigma over the work volume"]],
    ["6  REFERENCE_VERIFICATION", ["Optional bead references", "Trust level VERIFIED or LOCAL_ONLY from the margin check"]],
  ];
  const cols = 3, g = 0.15, cw = (W - 2 * M - (cols - 1) * g) / cols, ch = (BOT - TOP - 0.38 - g) / 2;
  steps.forEach(([h, items], i) => {
    const x = M + (i % cols) * (cw + g), y = TOP + Math.floor(i / cols) * (ch + g);
    card(sl, x, y, cw, ch, h, items, { size: 10, space: 3, headSize: 11 });
  });
  sl.addText("No automatic retry; any station reboot forces the full sequence again.",
             { x: M, y: BOT - 0.32, w: W - 2 * M, h: 0.3, fontSize: 10, bold: true, color: C.text1, margin: 0, valign: "middle", isTextBox: true, objectName: "rules" });
}

// ================================================================================================ 18. Next iteration
section("Next iteration");
{
  const sl = slide("Next iteration: what was not working, and what changes",
    "Next iteration (DECK_V9_NOTES slide 24 row, Jasper 10/27). Gear stage: 18T/54T, 3:1, printed PETG pinion, CAD-verified, pinion printed, NOT fitted; " +
    "the mounted stations are direct-drive spools (D40-D42; v9 'correction' update). 2.7x pull at 1.0 A with half the heat (PANEL_FEEDBACK_ANSWERS " +
    "'larger motors'). Draft: the slide-in binds on insertion; a 1 deg draft on the dovetail, thicker at the " +
    "top (slide 24 row, PLANNED). Mount: 597 cm^3 solid (COST_BREAKDOWN section 2), dovetails 225x and screws in a stud 8.9x the motor (lift_chain_weakest_link.md ranking), to about 200 cm^3 (slide 24 row, PLANNED). " +
    "Gear stage: ratio 3, efficiency 0.9 (winch_gear3.json ratio, eta): 3 x 0.9 = 2.7x torque at the spool at equal current; heat at 1.0 A vs 1.5 A: (1.0/1.5)^2 = 0.44 (1.8 W vs 4.05 W, winch_gear3.json heat). Still planned, " +
    "no result: pull test, hold test, first three-station lift (slide 25 and 26 rows). The dashed box is for Jasper's new CAD.");
  const cw = 1.9, g = 0.12, ch = 2.6;
  const cards3 = [
    ["3:1 printed gear stage", ["18T / 54T spur, printed PETG pinion", "Designed and checked in CAD; pinion printed; not fitted", "Pull × 3 × 0.9 (η) = 2.7 at equal current (calculated)", "At 1.0 A: heat × (1.0/1.5)² = 0.44 (calculated)"]],
    ["1° draft on the dovetail", ["Today the slide-in binds on insertion", "Thicker at the top, thinning toward the bottom", "The station self-locates as it slides in (planned)"]],
    ["Lighter back mount", ["Today: 597 cm³ solid, far stronger than the motor can pull", "Thinner walls and ribs: about 200 cm³ (planned)", "Less print time and filament"]],
  ];
  cards3.forEach(([h, items], i) => card(sl, M + i * (cw + g), TOP, cw, ch, h, items, { size: 9.5, space: 2, headSize: 11 }));
  card(sl, M, TOP + ch + g, 3 * cw + 2 * g, BOT - TOP - ch - g, "Not working yet / still planned", [
    "Pull test at 1.5 A: the measured limit goes into the planner (planned)",
    "Hold test: 90 minutes at 1.5 A, motor below 60 °C (planned)",
    "First three-station lift: self-check, calibration, a short move with 1 lb (planned)",
  ], { size: 10, space: 3, headSize: 11.5 });
  const px = M + 3 * (cw + g), pw = W - M - px;
  const ph2 = (BOT - TOP - 0.26 - 0.08) / 2;
  fitImage(sl, PH("49_next_iteration_station_gear_stage_cad.png"), px, TOP, pw, ph2, "Next-iteration station (CAD), front: 3:1 spur stage, motor pinion to spool gear, spool on its own shaft, encoder magnet cap", { top: true });
  fitImage(sl, PH("50_next_iteration_station_back_dovetail_cad.png"), px, TOP + ph2 + 0.08, pw, ph2, "Next-iteration station (CAD), back: slide-in rails on the mount plate, window, screw holes", { top: true });
  caption(sl, "Next iteration (CAD, 10/27). Front: 3:1 spur stage, spool on its own shaft, encoder magnet cap. Back: slide-in rails, window, screw holes", px, BOT - 0.22, pw);
}

// ================================================================================================ 19. Thank you
section("Close");
{
  const sl = pres.addSlide({ masterName: "PLAIN", sectionTitle: SECTION });
  sl.addText("Thank you", { x: M, y: 2.0, w: W - 2 * M, h: 0.9, fontSize: 40, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "thank you" });
  sl.addText("Jasper Buntinx  |  Mechanical Engineering  |  Texas A&M", { x: M, y: 2.95, w: W - 2 * M, h: 0.4, fontSize: 13, color: C.text2, margin: 0, isTextBox: true, objectName: "byline" });
  sl.addNotes("Thank you. Leave this slide up for questions.");
}

(async () => {
  renderCharts();                                   // chart_data.json -> fig/*.png, before writeFile reads the images
  cropPhotos();                                     // crop_jobs.json -> img/*.jpg
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  // pptxgenjs leaves empty ppt/charts/ and ppt/embeddings/ directory entries even with no charts: drop them.
  execFileSync("/usr/bin/python3", ["-c", `
import zipfile, shutil, sys
src = sys.argv[1]; tmp = src + ".tmp"
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        if item.filename.endswith("/"): continue
        zout.writestr(item, zin.read(item.filename))
shutil.move(tmp, src)`, OUT]);
  console.log("wrote", OUT);
})();
