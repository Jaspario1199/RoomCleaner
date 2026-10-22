// RoomCleaner interview deck v8 (Oct 22): v7 with the panel-chair critique applied (docs/presentation/deck_v7/CRITIQUE_EXEC.md).
// Status upfront, numbers reconciled with the weighed claw (0.60 kg with battery), the finger-claw and gear stories corrected against
// DECISION_STORIES.md, grip force and the safe state added, authorship stated, 21 main slides (phase dividers replaced by a phase
// label in the footer). Figure on the left, short statements on the right, slim equation boxes; notes are a short talk track plus
// "If asked" material. Content contract: docs/presentation/DECK_V8_NOTES.md.  v1-v7 are kept unchanged.
//
//   NODE_PATH=<pptxgenjs node_modules> APPLY_THEME=<pptx skill>/scripts/apply_theme.js \
//   SOFFICE_PY=<pptx skill>/scripts/office/soffice.py node docs/presentation/deck_v8/build_deck_v8.js
//
// [[text]] in any string is a fact still to fill in: it renders red and bracketed so it cannot be missed.
"use strict";
const path = require("path");
const { execFileSync } = require("child_process");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const P = (...p) => path.join(ROOT, ...p);
const OUT = path.join(__dirname, "RoomCleaner_Buntinx_Oct27_v8.pptx");
const FIGDIR = path.join(__dirname, "..", "deck_v3", "fig");
const SHEETFIG = path.join(__dirname, "fig");      // Sheet charts with the weighed claw (0.60 kg with battery) in Cable tension and Lift budget, Oct 22
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
  objects: [],
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
    caption(sl, `Calculated (calc sheet: ${v.tab})`, r.x, r.y + r.h + 0.08, Math.max(r.w, 4.5));
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
let SECTION = "Introduction", PHASE = "";   // PHASE: shown in the footer as plain text
function section(name) { SECTION = name; pres.addSection({ title: name }); }
function blank(title) {
  const sl = pres.addSlide({ masterName: "CONTENT", sectionTitle: SECTION });
  sl.addText(title, { x: M, y: 0.4, w: W - 2 * M, h: 0.65, fontSize: 26, bold: true, color: HEX.ink, fontFace: "Arial",
                      margin: 0, valign: "middle", isTextBox: true, objectName: "title" });
  sl.addText(`Jasper Buntinx  |  RoomCleaner${PHASE ? "  |  " + PHASE : ""}`, { x: M, y: 7.0, w: 9, h: 0.3, fontSize: 10, color: HEX.grey, fontFace: "Arial",
                                                                                margin: 0, isTextBox: true, objectName: "footer" });
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
// marks: [number, day, row] milestones drawn as numbered diamonds on their phase row.
function gantt(sl, rows, x, y, w, marks = []) {
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
  marks.forEach(([n, day, row]) => {
    const mx = cx + day * s, my = y + hh + row * rh + rh / 2;
    sl.addShape(pres.shapes.DIAMOND, { x: mx - 0.16, y: my - 0.16, w: 0.32, h: 0.32, fill: { color: HEX.red }, line: { color: "FFFFFF", width: 1 }, objectName: `milestone ${n}` });
    label(sl, String(n), mx - 0.16, my - 0.16, 0.32, 0.32, { size: 10, bold: true, color: "FFFFFF", align: "center" });
  });
  return bottom;
}
// Actual schedule against a half-time plan, same scale (inches per day).
function scheduleBars(sl, x, y, w, half, cap) {
  const lw = 1.45, bx = x + lw, bw = w - lw, s = bw / 104, bh = 0.75;
  const actual = [["Concept", 21, HEX.pale], ["Gen 1", 28, HEX.navy2], ["Redesign", 34, HEX.pale], ["Final", 15, HEX.navy2], ["Build and test", 6, HEX.navy]];
  half = half || [["Plan", 7, HEX.pale], ["One station", 14, HEX.navy2], ["Copy", 7, HEX.pale], ["Claw", 14, HEX.navy2], ["Test", 7, HEX.navy]];
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
  caption(sl, cap || "Same time scale. Half-time plan: prove one station, then copy it.", bx, y + 2 * bh + 0.6, bw);
}

const R = f => P("docs/presentation/deck_assets/renders", f);
const PH = f => P("docs/presentation/photos", f);
const FG = f => path.join(FIGDIR, f);
const SC = f => P("docs/presentation/deck_assets/screens", f);   // Jasper's SolidWorks screenshots (Oct 22)


// Room elevation to scale, along the 3.35 m wall: walls, ceiling, anchors, the planner's margins, the claw, a hamper.
function roomSketch(sl, x, y, w, h) {
  const Wm = 3.35, Hm = 2.74, za = 2.59, wall = 0.2, ceil = 0.4;
  const s = Math.min((w - 1.6) / Wm, (h - 0.95) / Hm);
  const ox = x + 0.9 + (w - 1.6 - Wm * s) / 2, oy = y + 0.25 + Hm * s;
  const X = m => ox + m * s, Y = z => oy - z * s;
  const box = (x0, z0, x1, z1, fill, name) => sl.addShape(pres.shapes.RECTANGLE, { x: X(x0), y: Y(z1), w: (x1 - x0) * s, h: (z1 - z0) * s,
                                                                                    fill: { color: fill }, line: { color: fill }, objectName: name });
  box(0, 0, wall, za, HEX.light, "wall margin left");
  box(Wm - wall, 0, Wm, za, HEX.light, "wall margin right");
  box(wall, za - ceil, Wm - wall, za, "F6E3E1", "ceiling margin");
  seg(sl, X(0), Y(0), X(Wm), Y(0), { color: HEX.ink, width: 2 });
  seg(sl, X(0), Y(0), X(0), Y(Hm), { color: HEX.ink, width: 1.25 });
  seg(sl, X(Wm), Y(0), X(Wm), Y(Hm), { color: HEX.ink, width: 1.25 });
  seg(sl, X(0), Y(Hm), X(Wm), Y(Hm), { color: HEX.ink, width: 1.25 });
  const claw = [1.45, 0.95];
  [0, Wm].forEach(ax => seg(sl, X(ax), Y(za), X(claw[0]), Y(claw[1]), { color: HEX.navy, width: 2 }));
  [0, Wm].forEach(ax => sl.addShape(pres.shapes.RECTANGLE, { x: X(ax) - (ax ? 0.14 : 0), y: Y(za) - 0.07, w: 0.14, h: 0.14,
                                                             fill: { color: HEX.navy }, line: { color: HEX.navy }, objectName: "anchor" }));
  sl.addShape(pres.shapes.RECTANGLE, { x: X(claw[0]) - 0.1, y: Y(claw[1]) - 0.05, w: 0.2, h: 0.3, fill: { color: HEX.navy2 }, line: { color: HEX.navy2 }, objectName: "claw" });
  box(2.6, 0, 3.05, 0.55, HEX.pale, "hamper");
  sl.addShape(pres.shapes.OVAL, { x: X(0.6), y: Y(0.05), w: 0.5 * s, h: 0.05 * s, fill: { color: HEX.grey }, line: { color: HEX.grey }, objectName: "garment" });
  label(sl, "3.35 m (11 ft) wall; room 3.35 × 2.74 m", X(0), Y(0) + 0.08, Wm * s, 0.28, { size: 12, align: "center", color: HEX.mid });
  label(sl, "2.74 m\n(9 ft)\nceiling", x, Y(Hm / 2) - 0.4, 0.8, 0.8, { size: 12, align: "right", color: HEX.mid });
  label(sl, "Anchor, 0.15 m below the ceiling", X(0) + 0.2, Y(za) + 0.04, 3.2, 0.26, { size: 11, color: HEX.navy });
  label(sl, "0.4 m ceiling margin", X(wall) + 0.1, Y(za - ceil) - 0.3, 2.4, 0.26, { size: 11, color: HEX.red });
  label(sl, "0.2 m wall margin", X(Wm - wall) - 1.6, Y(1.6), 1.5, 0.26, { size: 11, color: HEX.mid, align: "right" });
  label(sl, "Claw", X(claw[0]) + 0.16, Y(claw[1]) - 0.02, 0.8, 0.26, { size: 11, bold: true, color: HEX.navy2 });
  label(sl, "Hamper", X(2.6), Y(0.55) - 0.28, 0.45 * s + 0.3, 0.26, { size: 11, color: HEX.mid });
  label(sl, "Garment", X(0.6), Y(0.05) - 0.3, 1.0, 0.26, { size: 11, color: HEX.mid });
  caption(sl, "Room elevation to scale; seen from the side, the four cables appear as two", x, y + h - 0.3, w);
}
// Safe-state and failure table rows are plain text; this keeps the slide consistent with the rest.

// ================================================================================================ INTRODUCTION
section("Introduction");
{
  const sl = pres.addSlide({ masterName: "TITLE", sectionTitle: SECTION });
  sl.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 5.6, h: 7.5, fill: { color: HEX.navy }, line: { color: HEX.navy } });
  sl.addText("RoomCleaner", { x: M, y: 2.3, w: 4.8, h: 1.0, fontSize: 44, bold: true, color: "FFFFFF", fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addText("A four-cable ceiling robot designed to pick laundry off the floor", { x: M, y: 3.35, w: 4.6, h: 1.2, fontSize: 22, color: HEX.pale, fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addText("Jasper Buntinx\nMechanical Engineering, Texas A&M University\nOctober 27, 2026", { x: M, y: 5.7, w: 4.8, h: 1.1, fontSize: 14, color: HEX.pale, fontFace: "Arial", margin: 0, isTextBox: true });
  fitImage(sl, PH("11_gen2_station_assembled.jpg"), 6.0, 0.6, 3.3, 6.0, "Wall station, assembled");
  fitImage(sl, PH("21_claw_printed_tube_servo.jpg"), 9.45, 0.6, 3.3, 6.0, "Printed claw body with its servo");
  label(sl, "Wall station (built)", 6.0, 6.7, 3.3, 0.3, { size: 11, color: HEX.grey, align: "center" });
  label(sl, "Claw body and servo (built)", 9.45, 6.7, 3.3, 0.3, { size: 11, color: HEX.grey, align: "center" });
  sl.addNotes("One sentence: four winches near the ceiling corners hold one claw on cables; it is designed to pick clothes off the floor and drop them in a hamper. Then who I am.");
}

{
  // three photos from Jasper's collage across the top, the statements under them
  const sl = blank("About Me");
  const cols = [["about_endurance.png", "Ironman 70.3, marathon"], ["about_ecofil.png", "EcoFil filament recycler"], ["about_gladiator.png", "Gladiator Dash obstacle build"]];
  const g = 0.25, ar = cols.map(([f]) => { const d = imgSize(PH(`about_me/${f}`)); return d.w / d.h; });
  const ih = Math.min(3.15, (W - 2 * M - 2 * g) / ar.reduce((a, b) => a + b, 0));
  let cx = M + (W - 2 * M - 2 * g - ih * ar.reduce((a, b) => a + b, 0)) / 2;
  cols.forEach(([f, cap], i) => {
    const iw = ih * ar[i];
    sl.addImage({ path: PH(`about_me/${f}`), x: cx, y: 1.3, w: iw, h: ih, altText: cap, objectName: cap });
    sl.addText(cap, { x: cx, y: 1.3 + ih + 0.06, w: iw, h: 0.42, fontSize: 11, color: HEX.grey, fontFace: "Arial", valign: "top", margin: 0, isTextBox: true, objectName: "caption" });
    cx += iw + g;
  });
  bullets(sl, [
    "Mechanical Engineering, Texas A&M University, class of 2027",
    "Built EcoFil, a filament recycler with a shredder, dryer and extruder",
    "Build logistics chair, Gladiator Dash: obstacle assembly, repairs and transport ($185K raised)",
    "Ironman 70.3 in 6:53 and a marathon in 2025",
  ], M + 0.6, 1.3 + ih + 0.55, W - 2 * M - 1.2, 6.85 - (1.3 + ih + 0.55), 17, { space: 6, name: "about bullets" });
  sl.addNotes("Ninety seconds. I build things end to end, and I finish long things. EcoFil: what each stage does, and one result [add one number: filament diameter " +
              "tolerance or throughput, and what broke]. Gladiator Dash: as Special Events Build Logistics Chair I headed assembly, repairs and transport of the obstacles; " +
              "the event raised $185K for Still Creek Ranch. If asked: metal sculpture for the Austin Creek Show, with fiber laser cutting and welding.");
}

content("Project Goal", [
  "Pick up laundry in a 3.35 × 2.74 m (11 × 9 ft) room under a 2.74 m (9 ft) ceiling, and drop it in a hamper",
  "Design load 0.9 kg (jeans); first test 0.45 kg (1 lb)",
  "Success: one garment from floor to hamper with no human touch; I approve each move on the phone",
  "Safe state: PAUSE holds position, and nobody stands under the robot",
], (sl, x, y, w, h) => roomSketch(sl, x, y, w, h),
"The problem in one picture: four anchors 0.15 m below the ceiling, one claw, a hamper. The shaded bands are the 0.2 m wall and 0.4 m ceiling margins the planner keeps. " +
"If asked: 0.9 kg is a screening value for a pair of jeans, not weighed. The 2 m/s² is a 1.2 times dynamic allowance for stops and snags, not the motion " +
"profile; top speed is 50 mm/s, so a diagonal move takes about a minute and a half.",
{ size: 17, space: 12 });

content("Where It Stands Today", [
  "Built: [[how many]] wall stations, station electronics, the claw body and gear train",
  "Measured: claw 0.60 kg with battery; most other numbers in this talk are calculated or simulated, and labeled",
  "Open risks: lift margin rests on an unmeasured torque, jeans grip is short at narrow grabs, the prototype fin has 1–4 K of thermal margin",
  "This week: pull test, 90-minute hold test, three-station test",
], { file: [PH("04_gen2_station_shells.jpg"), PH("16_heat_fin_on_motor_straight.jpg")], alt: "Built hardware", caption: "Built: station shells, and the prototype fin on its motor" },
"Bottom line first. Nothing has picked up a garment yet; the software runs end to end in simulation. I will come back to each open risk in the phase where it came from.",
{ size: 17, space: 12 });

{
  const sl = blank("Timeline and Scope");
  const gy = gantt(sl, [
    ["1. Concept", "Jul 16 – Aug 5", 15, 36],
    ["2. Generation 1", "Aug 6 – Sep 2", 36, 64],
    ["3. Redesign", "Sep 3 – Oct 6", 64, 98],
    ["4. Final design", "Oct 7 – Oct 21", 98, 113],
    ["5. Build and test", "Oct 22 – Oct 27", 113, 119],
  ], M, 1.3, W - 2 * M, [[1, 91, 2], [2, 111, 3], [3, 113, 4]]);
  label(sl, "1  Sep 30: first clamp's jaws cannot close on thin cloth     2  Oct 20: v6 clamp is 4.6 times its mass budget in CAD     3  Oct 22: drivers at 1.5 A; claw weighed",
        M, gy + 0.08, W - 2 * M, 0.3, { size: 12, color: HEX.mid, name: "milestone key" });
  bullets(sl, [
    "Mine: requirements, design decisions, the SolidWorks station and claw, printing, machining, wiring and bring-up",
    "With Claude Code, under my direction: the control software, calculation scripts and CAD checks",
    "Purchased: steppers, drivers, controller boards, servo, camera, battery and encoder boards",
  ], M, gy + 0.6, W - 2 * M, 6.8 - gy - 0.6, 17, { space: 8, name: "scope" });
  sl.addNotes("About 15 weeks, alone. The numbered marks are the failures that shaped the design. I dictated the control logic and had Claude Code build it out; " +
              "it also wrote calculation scripts and checked my CAD, and I can take you through any number on these slides. " +
              "If asked: the garment detector is YOLO-World, an open-source model. [Fill in: hours, total cost, shop access or mentors.]");
}

// ================================================================================================ PHASE 1: CONCEPT
section("Concept"); PHASE = "Phase 1 of 5: Concept";
{
  const sl = blank("Why a Cable Robot");
  const fw = 6.4, bx = M + fw + 0.45, bw = W - M - bx;
  figure(sl, { file: FG("position_vectors.png"), alt: "Cable robot geometry", caption: "Cables from the ceiling anchors a_1 to a_4 to the claw at p" }, M, 1.3, fw, 5.45);
  table(sl, ["", "Floor robot", "Gantry", "Cable robot"], [
    ["Whole floor", "Furniture blocks it", "Yes", "Yes"],
    ["Floor left clear", "No", "Frame spans the room", "Yes"],
    ["Moving mass", "Whole robot", "Heavy beam", "0.6 kg claw"],
  ], bx, 1.4, bw, [0.28, 0.24, 0.24, 0.24], { size: 12, rowH: 0.55, name: "concept comparison" });
  bullets(sl, [
    "Chosen: four ceiling winches and one claw",
    "The cost: cables only pull, so cable tension sets the working space",
  ], bx, 3.85, bw, 2.8, 17, { space: 12, name: "concept bullets" });
  sl.addNotes("A floor robot fights the clutter it is meant to clear; a gantry puts a frame across my room. A cable robot reaches the whole floor with a 0.6 kg moving mass " +
              "and nothing on the floor. The price is on the next two slides. If asked: four cables on three position axes is redundant, so the tension split depends " +
              "on cable-length errors; that is why the planner checks tensions and the calibration fits the cable lengths.");
}

{
  const sl = blank("Design Trade-offs");
  table(sl, ["Lever", "Gain", "Cost"], [
    ["Motor current up", "Pull rises with current", "Heat rises with current squared"],
    ["Stronger claw", "Stronger gears, firmer grip", "More mass, less payload"],
    ["Larger working area", "More floor covered", "Longer wires, more voltage drop"],
    ["Closer to the ceiling", "More working volume", "Cable tension rises steeply"],
    ["Smaller spool radius", "More pull per amp", "Tighter line bend, less room for the set screw"],
    ["Larger safety margins", "No skipped steps, no wall contact", "Less usable force and floor"],
  ], M, 1.3, W - 2 * M, [0.28, 0.33, 0.39], { size: 16, rowH: 0.62 });
  bullets(sl, ["The chain that binds: a heavier claw needs more pull, more pull needs more current, and heat rises with the square of the current"],
          M, 6.0, W - 2 * M, 0.7, 18, { name: "coupling" });
  sl.addNotes("These are the levers I set in the concept phase and came back to in every phase after. Current bound the design, with heat right behind it. " +
              "If asked: the 1.5 divisor on winch force is the margin against skipped steps.");
}

content("Cable Tension Sets the Ceiling Margin", [
  "Weighed claw plus 1 lb, centred 0.4 m below the anchors: 14.3 N, 17.2 N at 2 m/s²",
  "That is at the 16.8 N winch limit; with jeans the claw must stay at least 0.6 m down",
  "The planner checks every cable at every path point against the measured pull limit",
], { sheet: "cable_tension", tab: "Cable tension" },
"Cables only pull, and the shallower the cable, the more tension it carries for the same weight. 0.4 m is the margin for the empty claw (9.8 N there). " +
"With a load, the planner's tension check keeps the claw lower; it needs the measured pull limit entered first, so the pull test comes before the system test. " +
"If asked: off-centre is worse than centred; the claw rises to scan the floor from above.",
{ eq: { title: "Tension per cable, 1 lb test at 0.4 m", lines: [
  "T = m (g + a) / (4 sin φ)",
  "= 1.054 × 11.81 / (4 × 0.181) = **17.2 N**",
  "Winch limit: **16.8 N**",
] } });

// ================================================================================================ PHASE 2: GENERATION 1
section("Generation 1"); PHASE = "Phase 2 of 5: Generation 1";
content("Generation 1: Bench Build and Findings", [
  "A bench station lifted [[weight]]; the cable math held",
  "Bead homing would leave only 5–29 % of the room reachable, caught on paper before it was built",
  "One central board would need 10 wires to every corner once each winch had sensors",
  "Finger claw: designed in CAD (419 g of a 450 g budget), never built",
], { file: [PH("13_gen1_station_lifting_test_weight.jpg"), PH("05_gen1_spool_plate.jpg"), PH("09_homing_switch_perfboard.jpg")],
     alt: "Generation 1 hardware", caption: "Bench lift test, one-piece corner plate, homing switch" },
"Pause and ask: how would you home a four-cable robot without a reference pose? Then: each finding here drives one decision on the next three slides. " +
"Bead homing: a bead on each cable trips a switch at the outlet, so a cable can never be shorter than at home. [Fill in: the weight and how high it lifted.]",
{ size: 17, space: 12 });

// ================================================================================================ PHASE 3: REDESIGN
section("Redesign"); PHASE = "Phase 3 of 5: Redesign";
content("One Controller per Winch", [
  "Generation 1: one central board; with sensors it would need 250 m (820 ft) of wire",
  "Now: a controller in each station, fed by one 12 V pair: 50 m (164 ft)",
  "Each station can be built and tested on its own",
  "Cost: timing moves into software; 50 ms of skew is 2.5 mm of cable error, about 7.5 N",
], { file: [PH("14_gen1_cnc_shield_a4988.jpg"), PH("19_station_perfboard_soldered.jpg")], alt: "Central board and station board",
     caption: "Before: one central driver board. After: a controller in each station." },
"Cable routes are 6, 21, 23 and 32 ft. If asked: each station runs time-stamped segments on its own clock and holds if the link drops; " +
"a 40 ms skew budget keeps the error to 2 mm. Line stiffness is about 3 N/mm over a 3 m run.",
{ size: 17, space: 12 });

content("Camera Calibration Replaces Bead Homing", [
  "Bead homing fixes each cable's shortest length, so most of the room is out of reach",
  "Instead the claw camera reads a printed floor board, and a fit finds the anchors and cable lengths",
  "Simulated: cable lengths known to about 12–16 mm, well inside the 0.2 m and 0.4 m margins",
  "The whole room opens only when the fit's error bars allow it",
], { sheet: "bead_homing", tab: "Bead homing" },
"The curve is why bead homing died: with home 1 m up, 5 % of the room is reachable; 2 m up, 29 %. If asked why not home each cable at its own shortest length: " +
"that drags the claw into the high-tension zone next to an anchor (previous phase). Camera pose per frame is 0.7 mm best case with four tags (appendix); " +
"the number that matters is the cable length after the fit. Simulated so far.",
{ size: 17, space: 12 });

content("Claw: Four Versions to a Parallel Grip", [
  "Fingers (CAD only), then a clamp whose jaws could not close on thin cloth (Sep 30)",
  "v6 clamp: 4.6 times its mass budget in CAD (Oct 20)",
  "Final: geared four-bar, parallel jaws, 53 mm opening; gear safety factor 2.05 at servo stall",
  "Grip for jeans is short at narrow grabs",
], { grid: [R("gen1_tentacle_claw.png"), R("claw_v6.png"), R("gripper1021_head.png"), PH("22_gear_train_printed_servo.jpg")],
     alt: "Claw versions", caption: "Finger claw (CAD only), v6 clamp (CAD), final four-bar (CAD), printed gear train" },
"Each version failed for a reason I can name. The first clamp's pinion travel left a 2 mm gap, so the pads never met on thin cloth. v6 was up to 2.06 kg in CAD " +
"against 0.45 kg, with no torque path from the servo. Final gears: module 1.5 with a 16 mm face (module 1 with a 6 mm face gave a safety factor of 0.35). " +
"Grip assumes friction 0.3; at 6 V the jaws give 17 % more, enough above a 22 mm grab; next are grippy pads. If asked: servo heat while holding, and claw yaw.",
{ size: 17, space: 10, eq: { title: "Grip force per jaw, jeans", lines: [
  "N ≥ m (g + a) / (2μ) = 0.9 × 11.81 / 0.6 = **17.7 N**",
  "Jaws: **13.3 N** narrowest to 25 N at a 70 mm grab",
] } });

// ================================================================================================ PHASE 4: FINAL DESIGN
section("Final Design"); PHASE = "Phase 4 of 5: Final design";
content("Final Wall Station", [
  "Slide-in wall mount: the station lifts off while the anchor stays in the stud",
  "Load path: cable, spool, motor, 5 mm PETG tab, shell, mount, stud",
  "Mount sized for a 34 N cable snag at a safety factor of 3; SolidWorks static study to run",
  "Aluminum fin exits through a slot in the shell top",
], { file: SC("station_shell_transparent_1022.png"), alt: "Final wall station with a transparent shell", caption: "Final wall station (SolidWorks), shell shown transparent" },
"Walk the load from the cable to the stud. 34 N is the spool's slip limit; a stalled winch at 1.5 A could otherwise pull about 48 N over the empty core. " +
"The PETG tab has to carry that below 60 °C, which is where the thermal limit on the cooling slide comes from. " +
"If asked: the 1/8 in fin needs the shell slot about 1 mm wider on the motor side, and M3 × 12 screws.",
{ size: 17, space: 12 });

content("Winch Pull at 1.5 A", [
  "NEMA 17 (National Electrical Manufacturers Association) stepper at its rated 1.5 A, up from 1.06 A: 41 % more pull",
  "Calculated pull: 34 N on an empty spool, 25 N when full",
  "Assumes running torque of 0.7 × holding torque; the pull test measures it",
], { sheet: "winch_pull", tab: "Winch pull" },
"If asked how: the current is set by the driver reference voltage, I = Vref / (8 × 0.1 Ω) [fill in how you reached 1.5 A and the Vref you read]. " +
"Two torque risks: running torque could be nearer 0.5 of holding, and in microstepping the torque can be about 0.7 of the rating. " +
"The A4988 runs hot at 1.5 A; if it shuts down the winch loses torque, so the hold test watches it.",
{ size: 17, space: 12, eq: { title: "Winch design force", lines: [
  "T = τ / r = 0.252 N·m / 0.010 m = **25.2 N**",
  "F_{design} = 25.2 N / 1.5 = **16.8 N**",
] } });

content("Motor Cooling", [
  "1.5 A doubles motor heat to 4.05 W; the PETG mount must stay below 60 °C",
  "Vented shell and aluminum fin: 56–59 °C with the 0.019 in prototype, 45–49 °C with the 1/8 in design fin",
  "Assumed: 1.8 Ω coil (to measure) and a 23 °C room; warmer air near the ceiling uses up the prototype's margin",
  "This week: SolidWorks study and a 90-minute hold test; fallback 1.35 A",
], { sheet: "motor_temperature", tab: "Motor temperature" },
"The ranges are the simple and the refined hand model; the bars show the simple one. The PETG next to the motor runs at about the motor temperature (independent 3-D check). " +
"If asked: measuring the coil resistance takes 30 seconds with a meter; fin sizing is in the appendix, and thickness beats length.",
{ size: 17, space: 10, eq: { title: "Motor heat, P = I² R", lines: [
  "At 1.06 A: (1.06 A)² × 1.8 Ω = 2.0 W",
  "At 1.5 A: (1.5 A)² × 1.8 Ω = **4.05 W**",
] } });

content("Weight Budget", [
  "Claw with battery weighed 0.60 kg (0.86 kg estimated)",
  "Calculated capacity at task height 1.56 kg; jeans need 1.50 kg, a 4 % margin",
  "That margin is inside the uncertainty: at 0.5 × holding torque, capacity is 1.1 kg",
  "The pull test decides: keep 1.5 A, or add a 2:1 gear stage at each winch",
], { sheet: "lift_budget", tab: "Lift budget" },
"Pause and ask: if the pull test comes in low, would you cut claw mass or add a 2:1 gear stage? My answer: the gear stage, because it also lets the current drop " +
"to about 1 A and halves the heat. If asked: task height means the claw at or below 1.6 m, and the worst point is the middle of a long wall. The claw is 0.15 kg " +
"over its 0.45 kg budget; the 198 g aluminum tube is the first place to cut.",
{ size: 17, space: 10, eq: { title: "Lift capacity", lines: [
  "m_{max} = F_{design} / (k g) = 16.8 / (1.101 × 9.81)",
  "= **1.56 kg** against 0.60 + 0.90 = **1.50 kg**",
] } });

// ================================================================================================ PHASE 5: BUILD AND TEST
section("Build and Test"); PHASE = "Phase 5 of 5: Build and test";
content("Build: Printing, Machining, Bring-Up", [
  "One spool bore printed too tight (Ø5.2 on a 5 mm shaft); v3 opened it to Ø5.45",
  "Fin drilled in one mill setup from a 1:1 drawing; the 7/8 in pilot fits the 22 mm motor boss",
  "First motor would not turn: logic rail at 1.14 V, traced to a bad 3.3 V connection",
  "Now: a meter on every rail before code, and fit coupons before new fits",
], { grid: [PH("06_shear_with_drawings_and_blanks.jpg"), PH("15_heat_fin_finished_part.jpg"), PH("19_station_perfboard_soldered.jpg"), PH("03_mill_setup_with_shop_drawing.jpg")],
     alt: "Build photos", caption: "Fin blanks and drawing, finished fin, soldered station board, mill setup" },
"Two lessons from the bench: measure the hardware before trusting the software's view of it, and test a fit before printing the part. " +
"If asked: the driver stays disabled at boot so a reset cannot move a motor, which also means a reset drops a hanging claw (appendix, safe state). [Fill in: readings and date.]",
{ size: 17, space: 12 });

content("First System Test", [
  "Three stations hold the claw under gravity over the triangle they span, about half the floor",
  "Self-check, calibration, short move, then pickup",
  "1 lb first, then one garment; pass limits set before the run",
], (sl, x, y, w, h) => {
  placeholderBox(sl, "[[Photo or video from the three-station test]]", x, y, w, 2.5);
  table(sl, ["Check", "Pass limit", "Result"], [
    ["Self-check", "All stations answer; slack taken up", "[[]]"],
    ["Calibration", "Held-out poses: cable residual ≤ [[20 mm?]]", "[[]]"],
    ["Short move, 1 lb", "300 mm at 50 mm/s; cable mismatch ≤ 2 mm", "[[]]"],
    ["Pickup", "One garment into the hamper", "[[]]"],
  ], x, y + 2.7, w, [0.25, 0.57, 0.18], { size: 13, rowH: 0.48, name: "pass limits" });
}, "Pause and ask: which pass limit would you tighten? If the test has not run by Monday, show the rig as built and the dated plan, not empty cells. " +
"Logged: cable lengths, encoder counts, motor temperatures, the fit's error bars.",
{ size: 17, space: 12 });

// ================================================================================================ RESULTS AND TAKEAWAYS
section("Results and Takeaways"); PHASE = "";
{
  const sl = blank("Results Against Targets");
  const RED = t => ({ text: t, color: HEX.red, bold: true });
  table(sl, ["Target", "Goal", "Current", "Evidence", "Status"], [
    ["Lift capacity", "1.50 kg with jeans", "1.56 kg; 1.1 kg at 0.5 × holding torque", "Calculated", "Marginal; pull test"],
    ["Grip for jeans", "17.7 N per jaw", "13.3–25 N", "Calculated", RED("Short at narrow grabs")],
    ["Claw mass", "0.45 kg", "0.60 kg with battery", "Weighed", RED("Not met")],
    ["Motor temperature", "Below 60 °C", "56–59 °C prototype fin", "Calculated", "Marginal; hold test"],
    ["Working area", "Floor, 0.2 m wall margin", "All but 0.2 m at the walls", "Calculated", "Met in design"],
    ["Wiring", "One cable per station", "One 12 V pair; 0.51 V drop", "Built", "Met"],
    ["Accuracy", "≤ 2 mm cable mismatch", "40 ms skew budget gives 2 mm", "Not measured", "To be tested"],
    ["Speed", "50 mm/s", "Not yet run", "None", "To be tested"],
    ["Cost", "[[budget]]", "[[total]]", "Receipts", "[[]]"],
  ], M, 1.3, W - 2 * M, [0.17, 0.2, 0.3, 0.13, 0.2], { size: 14, rowH: 0.55 });
  sl.addNotes("Back to the targets, with the evidence for each. Two are not met: grip for jeans at narrow grabs and claw mass. Two are marginal and this week's tests decide them: " +
              "lift capacity and the prototype fin's temperature. Only the claw mass is measured so far.");
}

{
  const sl = blank("Good and Poor Decisions");
  const cw = [0.38, 0.62];
  table(sl, ["Good decision", "Result"], [
    ["One controller per winch", "Five times less wire; each station tested alone"],
    ["Camera calibration instead of bead homing", "Whole room reachable; caught on paper before building"],
    ["Teeth checked at servo stall", "A clamp stalls the servo on every grip: safety factor 2.05"],
  ], M, 1.3, W - 2 * M, cw, { size: 15, rowH: 0.5, name: "good decisions" });
  table(sl, ["Poor decision", "Result"], [
    ["Mass not tracked through four claw versions", "v6 reached 4.6 times its budget in CAD; the claw is 0.15 kg over"],
    ["Prototype fin cut from scrap sheet", "Only 1–4 K of thermal margin"],
    ["Build and test week ends on presentation day", "System results arrive at the last minute"],
  ], M, 3.45, W - 2 * M, cw, { size: 15, rowH: 0.5, headColor: HEX.red, name: "poor decisions" });
  bullets(sl, [
    "Thorough where a mistake is expensive: the fin's single mill setup, the stall check on the teeth",
    "Scrappy where it is cheap to undo: a jumpered ESP32 after a controller failed, a floor board printed on paper",
  ], M, 5.65, W - 2 * M, 1.2, 16, { space: 8, name: "thorough and scrappy" });
  sl.addNotes("Good: each was a trade I priced first. Poor: the mass problem was not the budget but that I never re-checked it as the claw changed four times; " +
              "the scrap fin saved a day and cost the thermal margin; and the schedule leaves no slack after the first test. " +
              "Scrappy: when a controller board died two days before the test, I moved the same circuit to an ESP32 dev board with nine jumpers instead of redesigning it. " +
              "[If true, add: several stations built before one was proven.]");
}

content("Takeaways and Next Steps", [
  "Takeaways",
  "- Pull-test one winch and weigh a mock claw in week 1; set the mass budget from that",
  "- Kill ideas on paper first: bead homing and the central board failed calculations I could have run in week 1",
  "- Prove one full station, calibration included, before copying it",
  "Next steps",
  "- Pull test, then enter the measured limit in the planner",
  "- Hold test at 1.5 A, three-station test, grip pads",
  "- A brake or non-backdrivable stage, so a power loss cannot drop the claw",
], (sl, x, y, w, h) => scheduleBars(sl, x, y + 1.3, w,
    [["Plan", 7, HEX.pale], ["One station", 14, HEX.navy2], ["Copy", 7, HEX.pale], ["Clamp", 14, HEX.navy2], ["Test", 7, HEX.navy]],
    "Same time scale. Half time: plan (pull test, mass budget), one station, copy, clamp, test."),
"In half the time I would not build the central board, bead homing or the finger claw at all; the week-1 calculations already killed them. " +
"Next steps in order: the pull test first, because both the lift margin and the planner's tension check depend on it. " +
"Leave this slide up for questions.",
{ figW: 7.0, size: 16, space: 6 });

// ================================================================================================ APPENDIX
section("Appendix"); PHASE = "Appendix";
{
  const sl = pres.addSlide({ masterName: "SECTION", sectionTitle: SECTION });
  sl.addText("Appendix", { x: M, y: 2.8, w: 11, h: 1.0, fontSize: 44, bold: true, color: "FFFFFF", fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addNotes("");
}
{
  const sl = blank("Safe State and Failure Modes");
  table(sl, ["Event", "What happens", "Mitigation"], [
    ["PAUSE, or a fault the software detects", "Every station holds position with torque on", "Nothing moves again without approval"],
    ["Wi-Fi link lost", "Stations stop and hold on their own clocks", "Resume needs approval"],
    ["Power loss or emergency stop", "Torque is lost and the claw can fall (1.5 kg from about 2 m)", "Nobody underneath; claw parked low when idle; brake planned"],
    ["Controller reset or brown-out", "Driver disabled at boot, so torque is lost", "Same as power loss"],
    ["Driver over-temperature", "The A4988 shuts its outputs off", "Hold test watches the driver; fallback 1.35 A"],
  ], M, 1.3, W - 2 * M, [0.26, 0.4, 0.34], { size: 14, rowH: 0.7 });
  sl.addNotes("The safe state is PAUSE: torque on, holding. Anything that removes power drops the claw, which is why nobody stands under it and why a brake or a " +
              "non-backdrivable stage is on the next-steps list.");
}

content("Heat Fin Length", [
  "0.019 in prototype reaches 95 % of its capacity by 136 mm",
  "1/8 in design keeps gaining to 349 mm",
  "Built at 200 mm, limited by ceiling clearance",
], { sheet: "heat_fin", tab: "Heat fin" },
"L95 is where a fin carries 95 % of the heat an infinitely long one would. h = 7 W/m²·K still air, k = 160 W/m·K aluminum. Source: Incropera, ch. 3.",
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
}, "The prototype works today only because the motor also sheds heat into the vented shell. Thickness beats length.");

content("Floor Board Accuracy", [
  "Camera pose error per frame, best case: 6.6 mm with one tag, 0.7 mm with four",
  "This is the camera's view, not the cable length",
  "After the fit, cable lengths are known to about 12–16 mm (simulated)",
], { sheet: "floor_board", tab: "Floor board" },
"Noise model: 0.3 px corner noise and a 520 px focal length (camera not yet calibrated). The four-tag figure is the best placement; realistic placements are a few times worse.");

content("Operating Sequence", [
  "Start up: self-check, take up slack, calibrate",
  "Find: scan from above, detect garments, choose the nearest",
  "Pick: hover until still, grip, deliver; the camera confirms each step",
  "Every move waits for approval on the phone; PAUSE holds position",
], { file: [P("docs/app_screenshots/01_home.png"), P("docs/app_screenshots/02_camera.png"), P("docs/app_screenshots/04_chat.png")],
     alt: "Phone app screens", caption: "Phone app: home, live claw camera and chat" },
"PAUSE or a detected fault stops every station on the same point of the path, still holding; nothing restarts by itself. The emergency stop is the switched power strip, " +
"and it drops the claw. Known obstacles are keep-out cylinders checked against every cable before a move. Simulated end to end.");

{
  const sl = blank("Control Logic: Generation 1 vs. Final");
  table(sl, ["", "Generation 1", "Final"], [
    ["Where is the claw?", "Assumed from the commanded cable lengths", "Measured by the claw camera; refit at every startup"],
    ["Room geometry", "Anchors from a tape measure", "Anchors and cable lengths fitted, with error bars"],
    ["Motor control", "One central board", "A controller per station, coordinated by the laptop"],
    ["Finding laundry", "Ceiling camera", "Claw camera"],
    ["Did the grab work?", "Assumed", "Camera checks pickup and delivery"],
    ["Faults", "Emergency stop only", "PAUSE keeps torque; the emergency stop cuts power and drops the claw"],
  ], M, 1.3, W - 2 * M, [0.2, 0.36, 0.44], { size: 15, rowH: 0.65 });
  sl.addNotes("Generation 1 trusted its model; the final logic measures before it trusts and checks after it acts.");
}

content("Claw Electrical", [
  "Two-cell lithium-ion pack, 7.4 V; 5 A fuse for shorts",
  "6 V servo rail and a separate 5 V logic rail",
  "Peak draw 2.8–3.1 A, at the pack's 3 A rating",
], { file: R("kicad_claw_revB.png"), alt: "Claw schematic", caption: "Claw schematic" },
"Rules check 0 errors; 9 nets match the specification. Charger: 8.4 V constant current, constant voltage; charged attended, at 1 A or less. " +
"The peak sits at the pack rating, so a stall longer than a moment is the thing to watch.");

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
