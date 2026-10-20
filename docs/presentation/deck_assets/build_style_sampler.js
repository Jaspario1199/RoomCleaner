// Style sampler for the interview deck: one slide per archetype in
// docs/presentation/STYLE_GUIDE.md, built on real layouts so the final deck
// can reuse this file's THEME, layouts and helpers unchanged.
//
//   NODE_PATH=<dir with pptxgenjs> node docs/presentation/deck_assets/build_style_sampler.js
//
// Sample text is illustrative only; the real slides are written with Jasper.

const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "../../..");
const P = (...p) => path.join(ROOT, ...p);
const PHOTO = (n) => P("docs/presentation/photos", n);
const RENDER = (n) => P("docs/presentation/deck_assets/renders", n);
const OUT = P("docs/presentation/deck_assets/style_sampler.pptx");
const APPLY_THEME = process.env.APPLY_THEME;

const HEX = { ink: "0E1116", paper: "FFFFFF", fog: "E9ECEF", steel: "6B7480", signal: "FF6A13", tint: "FFE6D6" };

const THEME = {
  name: "Flight Test Report",
  headFontFace: "Arial",
  bodyFontFace: "Calibri",
  colors: {
    dk1: HEX.ink, lt1: HEX.paper, dk2: HEX.steel, lt2: HEX.fog,
    accent1: HEX.signal, accent2: HEX.steel, accent3: HEX.ink, accent4: "A9B0B8", accent5: HEX.tint, accent6: "3A414B",
    hlink: HEX.signal, folHlink: HEX.steel,
  },
};

const W = 13.333, H = 7.5, M = 0.6;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Jasper Buntinx";
pres.title = "RoomCleaner — deck style sampler";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
// C.text1 = ink, C.text2 = steel, C.background1 = paper, C.background2 = fog, C.accent1 = signal, C.accent5 = tint

// ---------------------------------------------------------------- layouts
const footer = (dark) => [
  { text: { text: "ROOMCLEANER", options: { x: M, y: H - 0.45, w: 4, h: 0.3, fontSize: 9, bold: true, charSpacing: 1.5, color: dark ? C.text2 : C.text2, margin: 0 } } },
];
const slideNum = { x: W - M - 1, y: H - 0.45, w: 1, h: 0.3, fontSize: 9, color: C.text2, align: "right", margin: 0 };

pres.defineSlideMaster({
  title: "Dark Title",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { align: "left", name: "title", type: "title", x: M, y: 2.3, w: 5.6, h: 1.8, fontSize: 44, bold: true, color: C.background1, valign: "bottom", margin: 0 }, text: "Title" } },
    { placeholder: { options: { align: "left", name: "subtitle", type: "body", x: M, y: 4.25, w: 5.4, h: 1.0, fontSize: 18, color: "A9B0B8", valign: "top", margin: 0 }, text: "Subtitle" } },
    { placeholder: { options: { align: "left", name: "byline", type: "body", x: M, y: H - 1.1, w: 5.4, h: 0.4, fontSize: 12, color: C.text2, margin: 0 }, text: "Name · date" } },
  ],
});

pres.defineSlideMaster({
  title: "Dark Section",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { align: "left", name: "number", type: "body", x: M, y: 1.5, w: 4, h: 2.2, fontSize: 140, bold: true, fontFace: "Arial", color: C.accent1, valign: "bottom", margin: 0 }, text: "01" } },
    { placeholder: { options: { align: "left", name: "title", type: "title", x: M, y: 3.9, w: 9, h: 1.2, fontSize: 36, bold: true, color: C.background1, valign: "top", margin: 0 }, text: "Section claim" } },
    { placeholder: { options: { align: "left", name: "body", type: "body", x: M, y: 5.3, w: 8, h: 0.8, fontSize: 16, color: "A9B0B8", valign: "top", margin: 0 }, text: "One line on what this act covers" } },
  ],
  slideNumber: { ...slideNum, color: C.text2 },
});

pres.defineSlideMaster({
  title: "Content",
  background: { color: C.background1 },
  margin: [M, M, 0.6, M],
  objects: [
    { placeholder: { options: { align: "left", name: "eyebrow", type: "body", x: M, y: 0.45, w: 8, h: 0.3, fontSize: 11, bold: true, fontFace: "Arial", charSpacing: 1.5, color: C.text2, margin: 0 }, text: "EYEBROW" } },
    { placeholder: { options: { align: "left", name: "title", type: "title", x: M, y: 0.8, w: W - 2 * M - 1.9, h: 1.05, fontSize: 30, bold: true, color: C.text1, valign: "top", margin: 0 }, text: "Claim title" } },
    ...footer(false),
  ],
  slideNumber: slideNum,
});

pres.defineSlideMaster({
  title: "Dark Closing",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { align: "left", name: "eyebrow", type: "body", x: M, y: 0.8, w: 8, h: 0.3, fontSize: 11, bold: true, fontFace: "Arial", charSpacing: 1.5, color: C.accent1, margin: 0 }, text: "EYEBROW" } },
    { placeholder: { options: { align: "left", name: "title", type: "title", x: M, y: 1.2, w: 11, h: 1.0, fontSize: 36, bold: true, color: C.background1, valign: "top", margin: 0 }, text: "Closing claim" } },
  ],
});

// ---------------------------------------------------------------- helpers
const TAGS = {
  MEASURED:   (o) => ({ fill: { color: C.text1 }, line: { color: C.text1, width: 1 }, color: C.background1 }),
  CALCULATED: (o) => ({ fill: { color: C.background1 }, line: { color: C.text1, width: 1 }, color: C.text1 }),
  SIMULATED:  (o) => ({ fill: { color: C.background1 }, line: { color: C.text2, width: 1, dashType: "dash" }, color: C.text2 }),
  PLANNED:    (o) => ({ fill: { color: C.background2 }, line: { color: C.background2, width: 1 }, color: C.text2 }),
};

/** Evidence pill. Default position: top-right of a content slide. */
function tag(slide, kind, x = W - M - 1.45, y = 0.47, w = 1.45) {
  const s = TAGS[kind]();
  slide.addText(kind, {
    shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.14, x, y, w, h: 0.28,
    fill: s.fill, line: s.line, color: s.color, fontSize: 9, bold: true, fontFace: "Arial",
    charSpacing: 1.2, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: `tag_${kind}`,
  });
}

const RAIL = ["TRIGGER", "OPTIONS", "CONSTRAINT", "CHOICE", "RESULT"];
/** Decision rail across the bottom. active = 0..4 (index being discussed). */
function rail(slide, active, y = H - 1.15) {
  const x0 = M, x1 = W - M, step = (x1 - x0) / RAIL.length;
  slide.addShape(pres.shapes.LINE, { x: x0 + 0.14, y: y + 0.14, w: x1 - x0 - step + 0.0, h: 0, line: { color: C.background2, width: 2 }, objectName: "rail_line" });
  RAIL.forEach((label, i) => {
    const done = i < active, cur = i === active;
    const fill = cur ? C.accent1 : done ? C.text1 : C.background2;
    const x = x0 + i * step;
    slide.addText(String(i + 1), {
      shape: pres.shapes.OVAL, x, y, w: 0.28, h: 0.28, fill: { color: fill }, line: { color: fill, width: 0.75 },
      color: cur || done ? C.background1 : C.text2, fontSize: 9, bold: true, fontFace: "Arial", align: "center", valign: "middle", margin: 0,
      isTextBox: true, objectName: `rail_dot_${i + 1}`,
    });
    slide.addText(label, {
      x: x + 0.38, y: y - 0.01, w: step - 0.45, h: 0.3, fontSize: 10, bold: true, fontFace: "Arial", charSpacing: 1.2,
      color: cur ? C.accent1 : done ? C.text1 : C.text2, margin: 0, valign: "middle", isTextBox: true, objectName: `rail_label_${i + 1}`,
    });
  });
}

/** Dimension callout: Signal dot on the feature (fx,fy), leader to a label at (lx,ly). */
function callout(slide, fx, fy, lx, ly, label, align = "left") {
  const x = Math.min(fx, lx), y = Math.min(fy, ly);
  slide.addShape(pres.shapes.LINE, { x, y, w: Math.abs(lx - fx), h: Math.abs(ly - fy), flipH: (lx < fx) !== (ly < fy), line: { color: C.text1, width: 1 }, objectName: `callout_line_${label}` });
  slide.addShape(pres.shapes.OVAL, { x: fx - 0.06, y: fy - 0.06, w: 0.12, h: 0.12, fill: { color: C.accent1 }, line: { color: C.background1, width: 1 }, objectName: `callout_dot_${label}` });
  const lw = 0.11 * label.length + 0.3;
  slide.addText(label, {
    fill: { color: C.background1 },
    x: align === "left" ? lx + 0.05 : lx - lw - 0.05, y: ly - 0.16, w: lw, h: 0.32, fontSize: 12, bold: true, fontFace: "Arial",
    color: C.text1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: `callout_label_${label}`,
  });
}

function body(slide, lines, x, y, w, h, size = 16) {
  slide.addText(lines.map((t, i) => ({ text: t, options: { breakLine: i < lines.length - 1, paraSpaceAfter: 10 } })), {
    x, y, w, h, fontSize: size, color: C.text1, valign: "top", margin: 0, isTextBox: true,
  });
}

function caption(slide, text, x, y, w) {
  slide.addText(text, { x, y, w, h: 0.3, fontSize: 11, italic: true, color: C.text2, margin: 0, isTextBox: true });
}

/** Place a transparent render at height h, width from the PNG header. */
function render(slide, file, x, y, h, name) {
  const buf = require("fs").readFileSync(RENDER(file));
  const w = h * buf.readUInt32BE(16) / buf.readUInt32BE(20);
  slide.addImage({ path: RENDER(file), x, y, w, h, altText: name, objectName: name });
  return w;
}

// Portrait shop photos are 1200 x 1600.
const PORTRAIT = { w: 1200, h: 1600 };
function photo(slide, file, x, y, w, h, name) {
  slide.addImage({ path: PHOTO(file), x, y, w, h, sizing: { type: "cover", w, h }, altText: name, objectName: name });
}

// ---------------------------------------------------------------- slides
// A — title
pres.addSection({ title: "Archetypes" });
let s = pres.addSlide({ masterName: "Dark Title", sectionTitle: "Archetypes" });
s.addText("RoomCleaner", { placeholder: "title" });
s.addText("A cable-driven robot that picks laundry off the floor", { placeholder: "subtitle" });
s.addText("Jasper Buntinx · Technical presentation · Oct 27, 2026", { placeholder: "byline" });
photo(s, "13_gen1_station_lifting_test_weight.jpg", W * 0.45, 0, W * 0.55, H, "hero_photo");
s.addNotes("SAMPLE — Archetype A. Dark title, full-bleed hero photo right 55%, nothing else.");

// B — section divider
s = pres.addSlide({ masterName: "Dark Section", sectionTitle: "Archetypes" });
s.addText("02", { placeholder: "number" });
s.addText("The winch station had to survive its own motor", { placeholder: "title" });
s.addText("Heat, torque and a spool that kept walking off its shaft", { placeholder: "body" });
s.addNotes("SAMPLE — Archetype B. Giant Signal number, one-line section claim.");

// C — decision story
s = pres.addSlide({ masterName: "Content", sectionTitle: "Archetypes" });
s.addText("DECISION 04 · HEAT", { placeholder: "eyebrow" });
s.addText("An aluminium fin pulls heat out of a sealed printed shell", { placeholder: "title" });
tag(s, "CALCULATED");
photo(s, "02_mill_drilling_fin.jpg", M, 2.05, 5.2, 4.15, "decision_photo");
callout(s, 2.44, 3.4, 3.3, 2.5, "#29 drill · Ø3.4");
const cx = M + 5.6, cw = W - M - cx;
[["TRIGGER", "Sealing the station in PETG made the motor mount its hottest, most loaded joint"],
 ["OPTIONS", "Seven fixes weighed: vents, a cooler driver, ASA, a thermistor, a metal fin …"],
 ["CHOICE", "A 1/8 in 6061 fin, narrowed to 44 × 250 mm to fit the station"]].forEach(([k, v], i) => {
  const y = 2.1 + i * 1.3;
  s.addText(k, { x: cx, y, w: cw, h: 0.3, fontSize: 11, bold: true, fontFace: "Arial", charSpacing: 1.5, color: i === 2 ? C.accent1 : C.text2, margin: 0, isTextBox: true });
  s.addText(v, { x: cx, y: y + 0.32, w: cw, h: 0.8, fontSize: 16, color: C.text1, valign: "top", margin: 0, isTextBox: true });
});
rail(s, 3);
s.addNotes("SAMPLE — Archetype C, the core slide. Photo left with one callout, three labelled lines right, decision rail at the bottom with the current step in Signal. Example numbers are placeholders until the real story is written.");

// D — options compared
s = pres.addSlide({ masterName: "Content", sectionTitle: "Archetypes" });
s.addText("OPTIONS · FIN THICKNESS", { placeholder: "eyebrow" });
s.addText("Thicker spreads heat better, but 1/8 in was the knee", { placeholder: "title" });
tag(s, "CALCULATED");
const opts = [
  ["1/16 in", "54 %", "Fin efficiency", "Lightest and easiest to cut, but gives up almost half of its fin effect."],
  ["1/8 in", "68 %", "Fin efficiency", "Most of the gain at half the mass of 1/4 in. The stock I sheared and drilled.", true],
  ["1/4 in", "81 %", "Fin efficiency", "Best spreading, but twice the aluminium hanging on a printed wall mount."],
];
const cardW = (W - 2 * M - 2 * 0.3) / 3;
opts.forEach(([name, big, lab, why, chosen], i) => {
  const x = M + i * (cardW + 0.3), y = 2.0, h = 4.3;
  s.addShape(pres.shapes.RECTANGLE, { x, y, w: cardW, h, fill: { color: chosen ? C.accent5 : C.background2 }, line: { color: chosen ? C.accent1 : C.background2, width: chosen ? 1.5 : 0.75 }, objectName: `card_${i + 1}` });
  s.addText(name, { x: x + 0.3, y: y + 0.3, w: cardW - 0.6, h: 0.45, fontSize: 20, bold: true, fontFace: "Arial", color: C.text1, margin: 0, isTextBox: true });
  if (chosen) s.addText("CHOSEN", { shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.14, x: x + cardW - 1.25 - 0.3, y: y + 0.33, w: 1.25, h: 0.28,
    fill: { color: C.accent1 }, line: { color: C.accent1, width: 1 }, color: C.background1, fontSize: 9, bold: true, fontFace: "Arial", charSpacing: 1.2,
    align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "chosen_pill" });
  s.addText(big, { x: x + 0.3, y: y + 1.0, w: cardW - 0.6, h: 1.0, fontSize: 54, bold: true, fontFace: "Arial", color: chosen ? C.accent1 : C.text1, margin: 0, isTextBox: true });
  s.addText(lab, { x: x + 0.3, y: y + 2.0, w: cardW - 0.6, h: 0.3, fontSize: 13, color: C.text2, margin: 0, isTextBox: true });
  s.addText(why, { x: x + 0.3, y: y + 2.5, w: cardW - 0.6, h: 1.6, fontSize: 14, color: C.text1, valign: "top", margin: 0, isTextBox: true });
});
s.addNotes("SAMPLE — Archetype D. Rejected options in Fog, chosen option in Signal tint with a Signal outline and Signal number. Numbers are the real fin-efficiency calc.");

// E — big number
s = pres.addSlide({ masterName: "Content", sectionTitle: "Archetypes" });
s.addText("RESULT · CLAW MASS", { placeholder: "eyebrow" });
s.addText("My first full gripper was over four times its mass budget", { placeholder: "title" });
tag(s, "CALCULATED");
s.addText("2.06 kg", { x: M, y: 2.2, w: 6, h: 1.4, fontSize: 96, bold: true, fontFace: "Arial", color: C.accent1, margin: 0, isTextBox: true, objectName: "big_number" });
s.addText("upper-bound mass of gripper v6 against a 450 g budget", { x: M, y: 3.65, w: 6, h: 0.4, fontSize: 16, color: C.text2, margin: 0, isTextBox: true });
s.addText("m = Σ ρ·V  ·  ρ(PETG) = 1.27 g/cm³, 100 % infill bound", { x: M, y: 4.6, w: 6, h: 0.45, fontSize: 18, fontFace: "Cambria", color: C.text1, margin: 0, isTextBox: true, objectName: "equation" });
caption(s, "Source: CAD volume of every body in the v6 STEP, solid PETG", M, 5.15, 6);
render(s, "claw_v6.png", 9.4, 1.95, 4.9, "claw_render");
s.addNotes("SAMPLE — Archetype E. One number, its label, the equation that made it, the source, and the evidence tag.");

// F — chart + commentary
s = pres.addSlide({ masterName: "Content", sectionTitle: "Archetypes" });
s.addText("DATA · FIN EFFICIENCY", { placeholder: "eyebrow" });
s.addText("Doubling the plate past 1/8 in buys only 13 more points", { placeholder: "title" });
tag(s, "CALCULATED");
s.addChart(pres.charts.BAR, [{ name: "Fin efficiency (%)", labels: ['1/16"', '1/8"', '1/4"'], values: [54, 68, 81] }], {
  x: M, y: 1.9, w: 7.4, h: 4.5, barDir: "col", barGapWidthPct: 60,
  chartColors: [HEX.steel, HEX.signal, HEX.steel], invertedColors: [HEX.steel],
  showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 14, dataLabelFontBold: true, dataLabelColor: HEX.ink, dataLabelFontFace: "+mn-lt",
  catAxisLabelColor: HEX.steel, catAxisLabelFontSize: 13, catAxisLabelFontFace: "+mn-lt", catAxisLineShow: false,
  valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 100, valGridLine: { color: HEX.fog, size: 0.75 }, catGridLine: { style: "none" },
  showLegend: false, showTitle: false,
});
body(s, ["Fin efficiency η = tanh(mL)/mL with m = √(2h/kt).", "1/8 in gets 68 % for half the aluminium of 1/4 in.", "That mass sits on a printed wall mount, so the knee wins."], 8.4, 2.1, W - M - 8.4, 3.6);
s.addNotes("SAMPLE — Archetype F. Native chart, focus bar in Signal, others Steel, no legend, light gridlines; takeaways right.");

// G — photo spread
s = pres.addSlide({ masterName: "Content", sectionTitle: "Archetypes" });
s.addText("BUILD · HEAT FIN", { placeholder: "eyebrow" });
s.addText("I sheared, laid out and drilled the fins myself", { placeholder: "title" });
tag(s, "MEASURED");
const gw = (W - 2 * M - 2 * 0.15) / 3, gh = 4.1;
[["06_shear_with_drawings_and_blanks.jpg", "1  Sheared blanks against the Letter drawing"],
 ["03_mill_setup_with_shop_drawing.jpg", "2  Mill set up from the inch drawing"],
 ["01_mill_drilling_fin_closeup.jpg", "3  Drilling the Ø3.4 mounting holes"]].forEach(([f, cap], i) => {
  const x = M + i * (gw + 0.15);
  photo(s, f, x, 1.95, gw, gh, `spread_${i + 1}`);
  caption(s, cap, x, 1.95 + gh + 0.1, gw);
});
s.addNotes("SAMPLE — Archetype G. Three photos, equal size, 0.15 in gaps, numbered captions. No frames or shadows.");

// H — timeline
s = pres.addSlide({ masterName: "Content", sectionTitle: "Archetypes" });
s.addText("PROJECT ARC", { placeholder: "eyebrow" });
s.addText("Five design snapshots in two weeks", { placeholder: "title" });
tag(s, "MEASURED");
const tl = [["Oct 7", "Station v1", "Spool + wall mount"], ["Oct 11", "Station v2", "Slip-in mount"], ["Oct 18", "Station v3", "Shell + spool v3"],
            ["Oct 19", "v3 assembly", "Whole station in CAD"], ["Oct 20", "Gripper v6", "Geared jaws"], ["Oct 27", "Panel", "Today"]];
const ty = 3.7, tx0 = M + 0.2, tx1 = W - M - 0.2, ts = (tx1 - tx0) / (tl.length - 1);
s.addShape(pres.shapes.LINE, { x: tx0, y: ty, w: tx1 - tx0, h: 0, line: { color: C.text1, width: 1.5 }, objectName: "timeline_axis" });
tl.forEach(([d, t, sub], i) => {
  const x = tx0 + i * ts, cur = i === tl.length - 2;
  s.addShape(pres.shapes.OVAL, { x: x - 0.11, y: ty - 0.11, w: 0.22, h: 0.22, fill: { color: cur ? C.accent1 : i === tl.length - 1 ? C.background1 : C.text1 }, line: { color: cur ? C.accent1 : C.text1, width: 1.5 }, objectName: `tl_node_${i + 1}` });
  s.addText(d, { x: x - 0.9, y: ty - 0.85, w: 1.8, h: 0.35, fontSize: 12, bold: true, fontFace: "Arial", color: cur ? C.accent1 : C.text2, align: "center", margin: 0, isTextBox: true });
  s.addText(t, { x: x - 0.95, y: ty + 0.3, w: 1.9, h: 0.35, fontSize: 15, bold: true, fontFace: "Arial", color: C.text1, align: "center", margin: 0, isTextBox: true });
  s.addText(sub, { x: x - 0.95, y: ty + 0.68, w: 1.9, h: 0.6, fontSize: 12, color: C.text2, align: "center", valign: "top", margin: 0, isTextBox: true });
});
s.addNotes("SAMPLE — Archetype H. Dated nodes; the current milestone in Signal; future node hollow. Dates taken from the CAD archive folders.");

// C variant — render with callouts
s = pres.addSlide({ masterName: "Content", sectionTitle: "Archetypes" });
s.addText("DECISION · VISION", { placeholder: "eyebrow" });
s.addText("The camera rides on the narrow side so it can see the jaws' approach", { placeholder: "title" });
tag(s, "SIMULATED");
render(s, "claw_v6_camera_bay.png", 1.6, 1.85, 4.9, "bay_render");
callout(s, 3.05, 2.32, 4.6, 2.32, "Camera bay (new)");
callout(s, 2.0, 2.7, 4.6, 3.1, "Line tie-offs at fillet holes");
callout(s, 2.4, 6.0, 4.6, 5.6, "Jaws");
body(s, ["Lens 512 mm above the floor, looking straight down.", "12 % of the view is blocked by the claw itself.", "Lines can only touch the bay above 1.98 m at ≥ 30° yaw — so tasks are capped at 1.6 m."], 7.6, 2.1, W - M - 7.6, 3.6);
s.addNotes("SAMPLE — Render variant of archetype C. Transparent orthographic render, subject part in Signal, three callouts max.");

// I — closing
s = pres.addSlide({ masterName: "Dark Closing", sectionTitle: "Archetypes" });
s.addText("WHAT I'D TELL MYSELF ON DAY ONE", { placeholder: "eyebrow" });
s.addText("Three things this robot taught me", { placeholder: "title" });
[["01", "Measure before you trust a margin", "Sample lesson text — one line, plain words."],
 ["02", "Every interface is a decision", "Sample lesson text — one line, plain words."],
 ["03", "Make failure visible early", "Sample lesson text — one line, plain words."]].forEach(([n, t, d], i) => {
  const x = M + i * ((W - 2 * M) / 3);
  s.addText(n, { x, y: 3.0, w: 1.5, h: 0.8, fontSize: 40, bold: true, fontFace: "Arial", color: C.accent1, margin: 0, isTextBox: true });
  s.addText(t, { x, y: 3.9, w: 3.6, h: 0.8, fontSize: 20, bold: true, fontFace: "Arial", color: C.background1, valign: "top", margin: 0, isTextBox: true });
  s.addText(d, { x, y: 4.75, w: 3.6, h: 0.8, fontSize: 14, color: "A9B0B8", valign: "top", margin: 0, isTextBox: true });
});
s.addText("jasper_buntinx@tamu.edu", { x: M, y: H - 1.0, w: 6, h: 0.4, fontSize: 12, color: C.text2, margin: 0, isTextBox: true });
s.addNotes("SAMPLE — Archetype I. Dark, three numbered lessons, contact line.");

// Reference sheet
pres.addSection({ title: "Reference" });
s = pres.addSlide({ masterName: "Content", sectionTitle: "Reference" });
s.addText("STYLE REFERENCE", { placeholder: "eyebrow" });
s.addText("Palette, type and evidence tags", { placeholder: "title" });
[["Ink", HEX.ink, C.text1, "Text, dark slides"], ["Paper", HEX.paper, C.background1, "Content background"], ["Fog", HEX.fog, C.background2, "Cards, mats"],
 ["Steel", HEX.steel, C.text2, "Secondary text"], ["Signal", HEX.signal, C.accent1, "The one thing to see"], ["Tint", HEX.tint, C.accent5, "Chosen card only"]].forEach(([n, hex, col, use], i) => {
  const x = M + i * 1.95;
  s.addShape(pres.shapes.RECTANGLE, { x, y: 2.0, w: 1.75, h: 1.1, fill: { color: col }, line: { color: C.background2, width: 0.75 }, objectName: `swatch_${n}` });
  s.addText(n, { x, y: 3.2, w: 1.75, h: 0.3, fontSize: 13, bold: true, fontFace: "Arial", color: C.text1, margin: 0, isTextBox: true });
  s.addText(`${hex} · ${use}`, { x, y: 3.5, w: 1.85, h: 0.3, fontSize: 10, color: C.text2, margin: 0, isTextBox: true });
});
s.addText("Claim title — Arial Bold 32", { x: M, y: 4.25, w: 7, h: 0.5, fontSize: 32, bold: true, fontFace: "Arial", color: C.text1, margin: 0, isTextBox: true });
s.addText("EYEBROW — ARIAL BOLD 11, TRACKED", { x: M, y: 4.85, w: 7, h: 0.3, fontSize: 11, bold: true, fontFace: "Arial", charSpacing: 1.5, color: C.text2, margin: 0, isTextBox: true });
s.addText("Body — Calibri 16. Left aligned, ≤ 30 words a slide, units on every number.", { x: M, y: 5.25, w: 7, h: 0.4, fontSize: 16, color: C.text1, margin: 0, isTextBox: true });
s.addText("Caption / source — Calibri Italic 11", { x: M, y: 5.7, w: 7, h: 0.3, fontSize: 11, italic: true, color: C.text2, margin: 0, isTextBox: true });
["MEASURED", "CALCULATED", "SIMULATED", "PLANNED"].forEach((k, i) => tag(s, k, 8.6, 4.35 + i * 0.42, 1.6));
s.addNotes("Reference sheet — not part of the talk.");

(async () => {
  await pres.writeFile({ fileName: OUT });
  if (APPLY_THEME) {
    const { applyTheme } = require(APPLY_THEME);
    await applyTheme(OUT, THEME);
  }
  console.log("wrote", path.relative(ROOT, OUT));
})();
