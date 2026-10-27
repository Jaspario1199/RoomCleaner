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
function slide(title, notes) {
  const sl = pres.addSlide({ masterName: "CONTENT", sectionTitle: SECTION });
  sl.addText(title, { placeholder: "title" });
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
// Light-grey card with a bold heading and bullets. Returns the inner box below the heading for extra content.
function card(sl, x, y, w, h, heading, items, o = {}) {
  sl.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.06, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: `card ${heading}` });
  const pad = 0.16;
  sl.addText(heading, { x: x + pad, y: y + 0.1, w: w - 2 * pad, h: 0.3, fontSize: o.headSize || 12.5, bold: true, color: C.text1,
                        valign: "middle", margin: 0, isTextBox: true, objectName: `heading ${heading}` });
  const by = y + 0.44;
  if (items && items.length) bullets(sl, items, x + pad, by, w - 2 * pad, (o.listH || (h - 0.54)), o.size || 11, { space: o.space, name: `bullets ${heading}` });
  return { x: x + pad, y: by, w: w - 2 * pad, h: h - 0.54 };
}
function fitImage(sl, file, x, y, w, h, alt, o = {}) {
  const d = imgSize(file);
  const s = Math.min(w / d.w, h / d.h), dw = d.w * s, dh = d.h * s;
  const dx = x + (o.left ? 0 : (w - dw) / 2), dy = y + (o.top ? 0 : (h - dh) / 2);
  sl.addImage({ path: file, x: dx, y: dy, w: dw, h: dh, altText: alt, objectName: alt.slice(0, 40) });
  return { x: dx, y: dy, w: dw, h: dh };
}
// Photo cropped to fill a box (pptxgenjs "cover" sizing: centre crop), so grids stay rectangular.
function coverImage(sl, file, x, y, w, h, alt) {
  sl.addImage({ path: file, x, y, w, h, altText: alt, objectName: alt.slice(0, 40), sizing: { type: "cover", w, h } });
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
  sl.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.06, fill: { color: HEX.white }, line: { color: HEX.grey, width: 1, dashType: "dash" }, objectName: "placeholder" });
  sl.addText(text, { x: x + 0.15, y, w: w - 0.3, h, fontSize: 12, color: C.text2, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "placeholder text" });
}
// Chart options in the deck's one style: body font, grey axes, no legend unless asked.
function chartOpts(x, y, w, h, title, extra = {}) {
  return {
    x, y, w, h, showTitle: true, title, titleFontSize: 8.5, titleFontFace: "+mn-lt", titleColor: HEX.ink, titleBold: true,
    catAxisLabelFontSize: 7.5, valAxisLabelFontSize: 7.5, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    catAxisLabelColor: HEX.mid, valAxisLabelColor: HEX.mid, valGridLine: { color: HEX.rule, size: 0.5 }, catGridLine: { style: "none" },
    catAxisLineColor: HEX.pale, valAxisLineColor: HEX.pale, showLegend: false, dataLabelFontFace: "+mn-lt", dataLabelFontSize: 7.5,
    dataLabelColor: HEX.mid, legendFontFace: "+mn-lt", legendFontSize: 7.5, legendColor: HEX.mid, catAxisTitleFontFace: "+mn-lt",
    valAxisTitleFontFace: "+mn-lt", catAxisTitleFontSize: 7.5, valAxisTitleFontSize: 7.5, catAxisTitleColor: HEX.mid, valAxisTitleColor: HEX.mid,
    plotArea: { fill: { color: "FFFFFF" } }, chartArea: { fill: { color: "FFFFFF" }, roundedCorners: false },
    ...extra,
  };
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
const BEAD = [[0.3, 0.0], [0.6, 0.4], [0.8, 1.8], [1.0, 4.7], [1.2, 9.1], [1.5, 17.1], [1.8, 25.0], [2.0, 29.1]];

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
  card(sl, M, TOP, bx - M - 0.25, scale, "Jasper Buntinx", [
    "Mechanical Engineering, Texas A&M",
    "Outdoors and endurance: hikes, Ironman 70.3, 2025 marathon",
    "EcoFil: a filament recycler, built with a team",
    "Gladiator Dash build logistics, for Still Creek Ranch",
    "RoomCleaner: built July to October 2026",
  ], { size: 11.5, space: 7 });
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

// ================================================================================================ 4. Generation 1
section("Generation 1");
{
  const sl = slide("Generation 1: one central unit",
    "Generation 1. One central unit (an Uno with a CNC shield) drove all four corner motors over wires run to each corner; an overhead ceiling camera scanned " +
    "the room (DESIGN_INTENT_20261027.md 'Iteration 1'; DECK_V9_NOTES.md v9.2 slide 7 row; DECISIONS D33 for the ceiling camera). A printed corner plate " +
    "screwed into a joist replaced hanging hooks: a hook is a pivot, about 1:1 anchor error to claw error (slide 8 row, D13). Each cable homed against a " +
    "crimped bead at the outlet (PANEL_FEEDBACK_ANSWERS, 'what bead homing is'). Bench: the station lifted a test weight (slide 8 row; the weight and height " +
    "are not recorded). Photos 05, 13, 14 (README rows).");
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
  coverImage(sl, PH("13_gen1_station_lifting_test_weight.jpg"), px, TOP + ph + 0.15, pw, ph, "Gen-1 station lifting a test weight");
  caption(sl, "The central board; a gen-1 corner plate; a gen-1 station lifting a test weight", px, BOT - 0.22, pw);
}

// ================================================================================================ 5. Problems with Generation 1
{
  const sl = slide("Problems with Generation 1",
    "Problems with Gen 1. Everything wired back to one place (DESIGN_INTENT 'Iteration 1'). Bench finds: 18 V on the meter from a supply labelled 12 V; the " +
    "homing switch would have zeroed without moving, logic inverted; the switch had to move below the pulley (DECK_V9_NOTES slide 9 row). Bead homing capped " +
    "the room at 5-29 % of the working volume (slide 10 row; calculations/bead_reach.json: 4.7 % at 1.0 m, 29.1 % at 2.0 m); by floor area at grab height " +
    "45 % at 1 m, 93 % at 1.5 m (PANEL_FEEDBACK_ANSWERS 'floor area'). One central board stepping four motors skews them 2.5 mm per 50 ms (slide 10 row). " +
    "Ceiling camera retired: one more device to mount and calibrate per room; the claw and cables hide the grasp spot from above (DECISIONS D33 via v9 slide 7 notes). " +
    "Chart: bead_reach.json, calculated.");
  const cw = 3.0, ch = BOT - TOP, g = 0.2;
  card(sl, M, TOP, cw, ch, "Wiring and the bench", [
    "Every motor and every sensor wired back to one place",
    "18 V on the meter from a supply labelled 12 V (measured)",
    "A homing switch that would have zeroed without moving: logic inverted",
    "The switch had to move below the pulley",
  ], { space: 5 });
  card(sl, M + cw + g, TOP, cw, ch, "The architecture", [
    "One board stepping four motors skews them: 2.5 mm per 50 ms (calculated)",
    "Bead homing: a cable can never be shorter than at home",
    "So it capped the room at 5-29 % of the working volume (calculated)",
    "The ceiling camera: one more device per room; the claw and cables hide the grasp spot",
  ], { space: 5 });
  const cx = M + 2 * (cw + g), cwid = W - M - cx;
  sl.addChart(pres.charts.LINE, [{ name: "Reachable working volume (%)", labels: BEAD.map(b => b[0].toFixed(1)), values: BEAD.map(b => b[1]) }],
    chartOpts(cx, TOP, cwid, ch - 0.3, "Reachable share of the working volume (%)", {
      chartColors: [HEX.navy], lineSize: 2, lineDataSymbol: "none", valAxisMinVal: 0, valAxisMaxVal: 40, valAxisMajorUnit: 10,
      catAxisTitle: "Homing height above the floor (m)", showCatAxisTitle: true, layout: { x: 0.12, y: 0.14, w: 0.85, h: 0.66 },
    }));
  caption(sl, "Calculated (bead reach model)", cx, BOT - 0.22, cwid);
}

// ================================================================================================ 6. What a winch on a wall needs
section("What a winch needs");
{
  const sl = slide("What a winch on a wall needs to work",
    "What a winch needs. A motor bolted to a wall cannot just run: a camera can fail, a spool can overwind, tension can rip a mount out, a motor can stall; " +
    "so each winch gets a switch (button) and a spool encoder (DESIGN_INTENT 'Why it changed'). The encoder measures discrepancies while testing; if the " +
    "camera proves good enough it can go later; data first (same). Its two jobs today: confirm every commanded step, catch slip as the tension sensor " +
    "(DECK_V9_NOTES slide 20 row). Fail-safe switch wiring: LOW at rest, HIGH pressed or with a broken wire (slide 20 row). Beads stay as end-of-travel " +
    "switches (PANEL_FEEDBACK_ANSWERS 'bead homing'). Wiring from one box: 10 conductors per corner, 250 m (820 ft) of wire (v9.2 slide 10 row). " +
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
    "250 m (820 ft) of wire back to one place (calculated)",
  ], { space: 5 });
  const px = W - M - 2.8;
  photoRow(sl, [[PH("09_homing_switch_perfboard.jpg"), "Homing switch"], [PH("23_slide_in_switch_pressfit.jpg"), "Switch pressed into the slide-in"]], px, TOP, 2.8, 2.0, { cover: true });
  coverImage(sl, PH("39_slide_in_handheld_wiring_hanging.jpg"), px, TOP + 2.1, 2.8, BOT - TOP - 2.1 - 0.26, "Slide-in with the full harness hanging");
  caption(sl, "One slide-in, its harness hanging", px, BOT - 0.22, 2.8);
}

// ================================================================================================ 7. The solution: a modular box
section("Modular box");
{
  const sl = slide("The solution: a modular box that only needs power",
    "Modular box. Each box has its own ESP32 and everything it needs; the only thing entering is power, on a thicker wire (DESIGN_INTENT 'Iteration 2'). " +
    "50 m (164 ft) of wire instead of 250 m (DECK_V9_NOTES v9.2 slide 13 row). Any position and orientation (DESIGN_INTENT). Wire drop: drop = current x loop " +
    "resistance; longest branch 32 ft one way, 64 ft of loop; at 2 A 0.82 V on 18 AWG, 0.51 V on 16 AWG, calculated with 2 A illustrative (FUNDAMENTALS.md section 10; " +
    "PANEL_FEEDBACK_ANSWERS 'How longer wires increase voltage drop'). Cost: 16 AWG 100 ft roll $30.00 (est.), 65 ft used for three stations, $19.50 prorated " +
    "(COST_BREAKDOWN_20261026.md section 1, 16 AWG row). Photos 33, 46 (README rows); SolidWorks screenshot of the station shell, transparent (deck_assets/screens).");
  const cw = (W - 2 * M - 0.2 - 3.1) / 2, ch = BOT - TOP, g = 0.2;
  card(sl, M, TOP, cw, ch, "A box with its own brain", [
    "An ESP32 in each box, with its driver, buck, switch and encoder",
    "The only thing going in is power: one 12 V pair",
    "50 m of wire instead of 250 m (calculated)",
    "Power can come from anywhere, so a box sits in any position and orientation",
    "The room's geometry no longer limits where the winches go",
  ], { space: 5 });
  card(sl, M + cw + g, TOP, cw, ch, "Why 16 AWG", [
    "Drop = current x loop resistance",
    "Longest branch 32 ft one way: 64 ft of loop",
    "At 2 A: 0.82 V lost on 18 AWG, 0.51 V on 16 AWG (calculated)",
    "That is 7 % against 4 % of 12 V; less heat in the wall",
    "Cost: a 100 ft roll about $30; 65 ft used for three stations, about $19.50 (estimated)",
  ], { space: 5 });
  const px = W - M - 2.9;
  coverImage(sl, PH("46_wall_mount_bracket_xt60_power_lead.jpg"), px, TOP, 2.9, 1.95, "Wall mount with its XT60 power connector");
  caption(sl, "The wall mount: one power plug", px, TOP + 1.98, 2.9);
  fitImage(sl, SC("station_shell_transparent_1022.png"), px, TOP + 2.3, 2.9, BOT - TOP - 2.3 - 0.26, "Station shell, transparent (SolidWorks)");
  caption(sl, "The station: board, driver, motor, fin (CAD)", px, BOT - 0.22, 2.9);
}

// ================================================================================================ 8. Modular, for the everyday user
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

// ================================================================================================ 9. Trade-offs
section("Trade-offs");
{
  const sl = slide("Trade-offs: what each component needs",
    "Trade-offs, all calculated unless marked. Tension vs depth: T = W / (4 sin phi) with the weighed claw plus 1 lb; at 0.4 m below the anchors 14.3 N static, " +
    "17.2 N with 2 m/s^2, against the 16.8 N winch limit; with jeans the claw stays 0.6 m down (DECK_V9_NOTES slide 6 row; FUNDAMENTALS section 1). Motor " +
    "temperature at 1.5 A, 23 C room: no fin 77.2 / 99.1 C vented / sealed, 0.019 in prototype fin 57.6 / 66.3, 1/8 in design fin 48.9 / 53.8; PETG limit 60 C " +
    "(deck_v8/fig/sheet_motor_temperature; calculations/fin_sizing_4w.md coupled results 55.9-58.8 C vented). Winch pull: 0.7 x 0.36 N.m holding (0.7 assumed) " +
    "over the spool radius: 34 N empty core, 25 N full; design force = running / 1.5 = 16.8 N; jeans worst cable 16.2 N (calculations/lift_chain_weakest_link.md " +
    "'Demand and the fuse'; slide 17 row). Weight: 0.45 kg budget (R7), 0.86 kg CAD estimate with battery, 0.60 kg weighed 10/22 (PANEL_FEEDBACK_ANSWERS slide 16); " +
    "jeans 1.50 kg against 1.56 kg capacity, 4 % (slide 17 row). Weakest link: cable tension at which each part gives, one station at 1.5 A " +
    "(lift_chain_weakest_link.md ranking table): motor slips at 34-59 N, the designed fuse; the set screw in the printed thread 22-64 N may give first, so it moves " +
    "into a metal insert; screws in a stud 531 N and up (bar capped at 600).");
  const g = 0.15, cols = 3, cw = (W - 2 * M - (cols - 1) * g) / cols, ch = (BOT - TOP - g) / 2;
  const at = (c, r) => ({ x: M + c * (cw + g), y: TOP + r * (ch + g) });
  const need = (p, text) => sl.addText(text, { x: p.x, y: p.y + ch - 0.3, w: cw, h: 0.3, fontSize: 8.5, color: C.text1, bold: true, margin: 0, valign: "middle",
                                                isTextBox: true, objectName: "what we need" });
  // 1. Tension vs depth
  let p = at(0, 0);
  sl.addChart(pres.charts.LINE, [
    { name: "Static (N)", labels: depths.map(String), values: depths.map(d => tension(d, 0)) },
    { name: "With 2 m/s² (N)", labels: depths.map(String), values: depths.map(d => tension(d, A_DYN)) },
    { name: "Winch limit (N)", labels: depths.map(String), values: depths.map(() => WINCH_LIMIT) },
  ], chartOpts(p.x, p.y, cw, ch - 0.3, "Tension per cable (N) vs depth (m)", {
    chartColors: [HEX.navy, HEX.grey, HEX.ink], lineSize: 1.5, lineDataSymbol: "none", lineDash: ["solid", "solid", "dash"],
    showLegend: true, legendPos: "r", valAxisMinVal: 0, valAxisMaxVal: 50, valAxisMajorUnit: 10, layout: { x: 0.1, y: 0.2, w: 0.55, h: 0.66 },
  }));
  need(p, "Need: stay 0.4 m below the anchors with 1 lb, 0.6 m with jeans");
  // 2. Motor temperature
  p = at(1, 0);
  sl.addChart(pres.charts.BAR, [
    { name: "No fin", labels: TEMP.labels, values: TEMP.noFin },
    { name: "0.019 in fin (built)", labels: TEMP.labels, values: TEMP.thin },
    { name: "1/8 in fin (drawn)", labels: TEMP.labels, values: TEMP.plate },
  ], chartOpts(p.x, p.y, cw, ch - 0.3, "Motor case (°C) at 1.5 A; PETG limit 60 °C", {
    barDir: "col", barGrouping: "clustered", barGapWidthPct: 60, chartColors: [HEX.pale, HEX.navy, HEX.grey], showValue: true, dataLabelPosition: "outEnd",
    dataLabelFormatCode: "0", showLegend: true, legendPos: "b", valAxisMinVal: 0, valAxisMaxVal: 120, valAxisMajorUnit: 30, layout: { x: 0.1, y: 0.2, w: 0.86, h: 0.52 },
  }));
  need(p, "Need: below 60 °C; vented shell + built fin 56-59 °C (calculated)");
  // 3. Winch pull
  p = at(2, 0);
  sl.addChart(pres.charts.LINE, [
    { name: "Running pull (N)", labels: radii.map(String), values: radii.map(runPull) },
    { name: "Design force (N)", labels: radii.map(String), values: radii.map(designPull) },
    { name: "Jeans, worst (N)", labels: radii.map(String), values: radii.map(() => JEANS_PEAK) },
  ], chartOpts(p.x, p.y, cw, ch - 0.3, "Pull per winch (N) vs spool radius (mm), 1.5 A", {
    chartColors: [HEX.navy, HEX.grey, HEX.ink], lineSize: 1.5, lineDataSymbol: "none", lineDash: ["solid", "dash", "dash"],
    showLegend: true, legendPos: "r", valAxisMinVal: 0, valAxisMaxVal: 50, valAxisMajorUnit: 10, layout: { x: 0.1, y: 0.2, w: 0.55, h: 0.66 },
  }));
  need(p, "Need: 16.2 N worst cable for jeans; 34 N empty, 25 N full (calculated)");
  // 4. Weight budget
  p = at(0, 1);
  sl.addChart(pres.charts.BAR, [{ name: "kg", labels: LIFT.labels, values: LIFT.values }],
    chartOpts(p.x, p.y, cw, ch - 0.3, "Winches can hold vs must hold (kg)", {
      barDir: "bar", barGapWidthPct: 40, chartColors: [HEX.navy, HEX.grey, HEX.grey, HEX.pale, HEX.navy], showValue: true, dataLabelPosition: "outEnd",
      dataLabelFormatCode: "0.00", valAxisMinVal: 0, valAxisMaxVal: 2.0, valAxisMajorUnit: 0.5, layout: { x: 0.34, y: 0.2, w: 0.6, h: 0.68 },
    }));
  need(p, "Need: a 0.45 kg claw; 0.86 estimated (CAD), 0.60 weighed; jeans 1.50 vs 1.56 (4 %)");
  // 5. Weakest link
  p = at(1, 1);
  sl.addChart(pres.charts.BAR, [
    { name: "Low estimate", labels: WL.map(w => w[0]), values: WL.map(w => w[1]) },
    { name: "Up to high estimate", labels: WL.map(w => w[0]), values: WL.map(w => w[2] - w[1]) },
  ], chartOpts(p.x, p.y, cw, ch - 0.3, "Tension at which each part gives (N)", {
    barDir: "bar", barGrouping: "stacked", barGapWidthPct: 35, chartColors: [HEX.navy, HEX.pale], valAxisMinVal: 0, valAxisMaxVal: 600, valAxisMajorUnit: 200,
    showLegend: false, layout: { x: 0.3, y: 0.2, w: 0.66, h: 0.72 },
  }));
  need(p, "Need: the motor gives first (34-59 N); the printed set screw may not, so: metal insert");
  // 6. The factors, in words
  p = at(2, 1);
  card(sl, p.x, p.y, cw, ch, "The factors", [
    "Pull rises with current; heat rises with current squared",
    "1.0 to 1.5 A: 50 % more pull for 2.25 x the heat",
    "Every gram on the claw is a gram of payload",
    "The pull test and the hold test are still planned",
  ], { size: 10, space: 4 });
}

// ================================================================================================ 10. Mount assembly: the design
section("Mount assembly");
{
  const sl = slide("The mount assembly: slide-in on a dovetail",
    "Mount assembly 1. Slide-in wall mount: the station lifts off its dovetail; the wall mount and its screws stay in the stud (DECK_V9_NOTES slide 12 row). " +
    "Load path: cable, spool, set screw, motor, PETG tab, slide-in, wall mount, screws, stud (same row; lift_chain_weakest_link.md 'The chain and the rule'). " +
    "The motor slips at 34-59 N before anything breaks, the designed fuse; the spool encoder sees the spool fall behind the commanded steps: a tracking fault, " +
    "every station holds (slide 13 row). Dovetail fit 0.175 mm a side on 30 deg flanks, from fit coupons (PANEL_FEEDBACK_ANSWERS 'Manufacturing fits', row " +
    "'Slide-in mount'; slide 19 title 'fits came from coupons'). Photos 45, 46, 24; snap_dovetail.png (deck_v8/fig); station_shell_transparent_1022.png.");
  const cw = 3.5, ch = BOT - TOP;
  card(sl, M, TOP, cw, ch, "What the record says", [
    "The wall mount screws into a stud; the station slides onto it on a dovetail",
    "Dovetail fit: 0.175 mm a side, from fit coupons (measured)",
    "Load path: cable, spool, set screw, motor, tab, mount, screws, stud",
    "The motor slips at 34-59 N before anything breaks: the designed fuse (calculated)",
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

// ================================================================================================ 11. Mount assembly: on the wall
{
  const sl = slide("The mount assembly: fin, vents and the wall",
    "Mount assembly 2. The aluminium fin bolts to the motor face and goes out through a slot in the top of the shell; the shell is vented (DECK_V9_NOTES slide 16 " +
    "and 22 rows; README rows 27, 34, 36). Prototype fin 0.019 in sheet, 56-59 C vented with the fin, calculated; 1/8 in design fin 45-49 C (slide 16 row; " +
    "fin_sizing_4w.md). First station in a stud on the TV wall, 12 V down the wall (slide 22 row). Load path and fuse as on the previous slide. A 1 deg draft " +
    "on the dovetail is the NEXT iteration: the slide-in binds on insertion today (slide 24 row). Photos 32, 33, 44 (README rows).");
  const cw = 3.5, ch = BOT - TOP;
  card(sl, M, TOP, cw, ch, "What the record says", [
    "The fin: aluminium on the motor face, out through a slot in the top of the shell",
    "Vents in the shell; vented shell + fin: 56-59 °C at 1.5 A (calculated)",
    "First station in a stud on the TV wall, 12 V down the wall",
    "The slide-in binds on insertion today; a 1° draft on the dovetail is the next iteration",
  ], { space: 5 });
  const px = M + cw + 0.25, pw = W - M - px;
  photoRow(sl, [[PH("32_wall_station_mounted_tv_wall.jpg"), "On the TV wall, 12 V leads down"], [PH("33_wall_station_mounted_closeup_wires.jpg"), "From below: fin through the slot"],
                [PH("44_wall_station_from_below_line_down.jpg"), "The line leaves the switch tab straight down"]], px, TOP, pw, BOT - TOP, { cover: true });
}

// ================================================================================================ 12. The claw
section("Claw");
{
  const sl = slide("The claw, and why it is modular",
    "Claw. Four-bar hands stay within 1 deg of parallel over the 53 mm opening; a camera bay on the electronics housing; one 7.4 V two-cell pack, a 6 V regulator " +
    "for the servo, a 5 V buck for the board (DECK_V9_NOTES slide 18 row 'The claw'). The gripper attaches modularly at the tube, by design, a test bed for shirts " +
    "(DESIGN_INTENT 'The gripper'; v9.2 slide 18 row). A hard-material pinch was expected to grip better; testing showed alignment problems: the rack-and-pinion " +
    "jaws left a 2 mm gap on thin cloth, Sep 30 (v9.2 slide 18 row; Jasper's account, no cloth-test reading logged). TPU and other pad materials being tried " +
    "(DESIGN_INTENT). The v6 clamp came out at 4.6x its mass budget in CAD, Oct 20; since then mass is tracked per part; the claw weighed 0.60 kg with battery " +
    "against the 0.45 kg budget (slide 11 and 17 rows). Photos 25, 40, 22; renders gripper1021_head.png, claw_v6.png.");
  const cw = (W - 2 * M - 0.2 - 3.9) / 2, ch = BOT - TOP, g = 0.2;
  card(sl, M, TOP, cw, ch, "The claw today", [
    "Four-bar hands: within 1° of parallel over the 53 mm opening (calculated)",
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

// ================================================================================================ 13. Station bench and claw bench
section("Electrical and testing");
{
  const sl = slide("Electrical and testing: on the bench",
    "Bench. Station checklist: driver off at boot, so a reset cannot move a motor; homing switch LOW at rest, HIGH pressed or with a broken wire; the encoder " +
    "answers at its address with the magnet detected; one spool turn within 60 encoder counts: PASS on both boards (DECK_V9_NOTES slide 20 row; Jasper's " +
    "10/25-10/26 bench, to confirm per v9 BUILD_NOTE). The motor that logged steps but did not turn: the logic rail read about 1.14 V instead of 3.3 V, a bad " +
    "3.3 V connection; now the driver VDD is soldered to the regulated rail and measured before enable (slide 20 row; PANEL_FEEDBACK_ANSWERS slide 17 item). " +
    "Claw bench: live video on the phone; battery 7.2 V through the divider, matching the meter; the servo only moved once it had its own hardware timer, the " +
    "camera owned the first (slide 21 row). Photos 29, 31, 37, 43 (README rows).");
  const cw = (W - 2 * M - 0.2 - 3.4) / 2, ch = BOT - TOP, g = 0.2;
  card(sl, M, TOP, cw, ch, "Station bench", [
    "Driver off at boot: a reset cannot move a motor",
    "Switch logic: LOW at rest, HIGH pressed or with a broken wire",
    "Encoder answers, magnet detected",
    "One spool turn within 60 counts: PASS on both boards (measured)",
    "A motor that logged steps but did not turn: logic rail at 1.14 V, not 3.3 V; VDD now soldered and measured first",
  ], { space: 4 });
  card(sl, M + cw + g, TOP, cw, ch, "Claw bench", [
    "Live view from the claw camera on the phone",
    "Battery 7.2 V read through the divider, matching the meter (measured)",
    "The servo only moved once it had its own hardware timer; the camera owned the first",
    "Still open: servo end points unmeasured; camera not yet calibrated",
  ], { space: 5 });
  const px = M + 2 * (cw + g), pw = W - M - px, ph = (BOT - TOP - 0.12 - 0.26) / 2;
  coverImage(sl, PH("43_bench_two_stations_laptop_meter_floor.jpg"), px, TOP, pw, ph, "Bench: two stations, laptop, meter, 12 V supply");
  coverImage(sl, PH("29_station_bench_esp32_wiring_floor.jpg"), px, TOP + ph + 0.12, (pw - 0.1) / 2, ph, "Dev board, driver, spool and end stop");
  coverImage(sl, PH("37_station_bench_red_shell_fuse_12v.jpg"), px + (pw + 0.1) / 2, TOP + ph + 0.12, (pw - 0.1) / 2, ph, "Red shell, fused 12 V lead");
  caption(sl, "Two stations on the bench; a dev board and spool; the red shell with its fuse", px, BOT - 0.22, pw);
}

// ================================================================================================ 14. On the wall
{
  const sl = slide("Electrical and testing: on the wall",
    "On the wall. First station in a stud on the TV wall; boxed stations boot and join Wi-Fi on their own; firmware updates arrive over Wi-Fi, so a boxed " +
    "station never needs a USB cable again; the motor stays off until the phone arms it; a station accepts an update only while disarmed (DECK_V9_NOTES slide 22 row). " +
    "Still planned, no result yet: the pull test at 1.5 A, the hold test, the first three-station lift (slide 25 and 26 rows). Photos 31, 32, 44 (README rows). " +
    "Live view: docs/app_screenshots/02_camera.png is the simulator's view, so it is not shown as the claw camera.");
  const cw = 3.6, ch = BOT - TOP;
  card(sl, M, TOP, cw, ch, "Making it work on the wall", [
    "Wi-Fi auto-join: a boxed station boots and joins the network by itself",
    "OTA: firmware updates arrive over Wi-Fi; no USB cable after boxing",
    "The motor stays off until the phone arms it",
    "A station accepts an update only while disarmed",
    "Still planned: pull test, hold test, first three-station lift",
  ], { space: 5 });
  const px = M + cw + 0.25, pw = W - M - px;
  photoRow(sl, [[PH("32_wall_station_mounted_tv_wall.jpg"), "The first station on the wall"], [PH("44_wall_station_from_below_line_down.jpg"), "From below, line down"],
                [PH("31_station_bench_xiao_breadboard_shell_open.jpg"), "A station open: board on the bench"]], px, TOP, pw, BOT - TOP, { cover: true });
}

// ================================================================================================ 15. Calibration
section("Calibration");
{
  const sl = slide("How the claw calibrates itself",
    "Calibration, from docs/presentation/CALIBRATION_SIMPLE.md (lead, 10/27; from roomcleaner/cdpr/startup.py). The claw starts on the floor on a printed mat " +
    "it can see with its camera; six steps in order; any failed check stops everything and waits for a person. Two rules: it never retries by itself, and if a " +
    "station reboots all six steps run again. Cable lengths after the fit about 12-16 mm (simulated; DECK_V9_NOTES slide 15 row). Photo 42 (README row 42).");
  const steps = [
    ["1  Am I sitting nicely?", ["Camera: upright, right height on the mat", "Every station awake, healthy, switch closed", "Only then: motors armed"]],
    ["2  Who is pulling me?", ["One station at a time reels in until the claw just slides or tips", "That gives each cable's length and direction", "No tug in the slack budget: cable not attached"]],
    ["3  Up we go, a little", ["All cables tighten together, a few mm at a time", "Camera checks: rose as commanded, no drift, no tilt"]],
    ["4  One good look", ["Hanging still, a careful look at the mat", "Now it knows where it really is"]],
    ["5  Explore, bigger and bigger", ["A few spots nearby, then wider, then wider again", "Refit the model between rounds", "Surprise spots check the guesses"]],
    ["6  Can I trust myself?", ["From how well the guesses matched: ready to work, or only near home"]],
  ];
  const cols = 3, g = 0.15, cw = (W - 2 * M - 1.55 - (cols - 1) * g) / cols, ch = (BOT - TOP - 0.5 - g) / 2;
  steps.forEach(([h, items], i) => {
    const x = M + (i % cols) * (cw + g), y = TOP + Math.floor(i / cols) * (ch + g);
    card(sl, x, y, cw, ch, h, items, { size: 10, space: 3, headSize: 11 });
  });
  sl.addText("Two rules: it never retries by itself; if a station reboots, all six steps run again before it is trusted.",
             { x: M, y: BOT - 0.4, w: W - 2 * M - 1.55 - 0.1, h: 0.35, fontSize: 10, bold: true, color: C.text1, margin: 0, valign: "middle", isTextBox: true, objectName: "rules" });
  const px = W - M - 1.4;
  coverImage(sl, PH("42_claw_hanging_three_cables_room_corner.jpg"), px, TOP, 1.4, BOT - TOP - 0.26, "The claw hanging on three cables");
  caption(sl, "Hanging, before its first look", px, BOT - 0.22, 1.4);
}

// ================================================================================================ 16. Next iteration
section("Next iteration");
{
  const sl = slide("Next iteration: what was not working, and what changes",
    "Next iteration (DECK_V9_NOTES slide 24 row, Jasper 10/27). Gear stage: 18T/54T, 3:1, printed PETG pinion, CAD-verified, pinion printed, NOT fitted; " +
    "the mounted stations are direct-drive spools (D40-D42; v9 'correction' update). 2.7x pull at 1.0 A with half the heat (PANEL_FEEDBACK_ANSWERS " +
    "'larger motors'); the slip fuse moves to about 130 N (slide 24 row). Draft: the slide-in binds on insertion; a 1 deg draft on the dovetail, thicker at the " +
    "top (slide 24 row, PLANNED). Mount: holds about 200x the motor's pull, 597 cm^3 solid, to about 200 cm^3 (slide 24 row, PLANNED). Still planned, " +
    "no result: pull test, hold test, first three-station lift (slide 25 and 26 rows). The dashed box is for Jasper's new CAD.");
  const cw = 2.15, g = 0.15, ch = 2.45;
  const cards3 = [
    ["3:1 printed gear stage", ["18T / 54T spur, printed PETG pinion", "Designed and checked in CAD; pinion printed; not fitted", "2.7 x pull at 1.0 A, half the heat (calculated)", "Slip fuse moves to about 130 N (calculated)"]],
    ["1° draft on the dovetail", ["Today the slide-in binds on insertion", "Thicker at the top, thinning toward the bottom", "The station self-locates as it slides in (planned)"]],
    ["Lighter back mount", ["Today: about 200 x the motor's pull, 597 cm³ solid", "Thinner walls and ribs: about 200 cm³ (planned)", "Less print time and filament for anyone building it"]],
  ];
  cards3.forEach(([h, items], i) => card(sl, M + i * (cw + g), TOP, cw, ch, h, items, { size: 10, space: 3, headSize: 11.5 }));
  card(sl, M, TOP + ch + g, 3 * cw + 2 * g, BOT - TOP - ch - g, "Not working yet / still planned", [
    "Pull test at 1.5 A: the measured limit goes into the planner (planned)",
    "Hold test: 90 minutes at 1.5 A, motor below 60 °C (planned)",
    "First three-station lift: self-check, calibration, a short move with 1 lb (planned)",
  ], { size: 10, space: 3, headSize: 11.5 });
  const px = M + 3 * (cw + g), pw = W - M - px;
  placeholderBox(sl, "[Jasper: new CAD]", px, TOP, pw, BOT - TOP - 0.26);
  caption(sl, "Next-iteration parts: gear stage, drafted slide-in, lighter mount", px, BOT - 0.22, pw);
}

// ================================================================================================ 17. Thank you
section("Close");
{
  const sl = pres.addSlide({ masterName: "PLAIN", sectionTitle: SECTION });
  sl.addText("Thank you", { x: M, y: 2.0, w: W - 2 * M, h: 0.9, fontSize: 40, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "thank you" });
  sl.addText("Jasper Buntinx  |  Mechanical Engineering  |  Texas A&M", { x: M, y: 2.95, w: W - 2 * M, h: 0.4, fontSize: 13, color: C.text2, margin: 0, isTextBox: true, objectName: "byline" });
  sl.addNotes("Thank you. Leave this slide up for questions.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
