// RoomCleaner interview deck v6: the v5 content in a plain corporate format (Jasper, Oct 22). Talking-point bullets with
// values, tables for targets, trade-offs and decisions, a Gantt chart for the timeline; the equation boxes and the
// calculation-sheet charts are kept from v5. No story tracker, status chips or label-style bullets.
// Content contract: docs/presentation/DECK_V6_NOTES.md.  v1-v5 are kept unchanged; the Sheet charts come from deck_v5/fig.
//
//   NODE_PATH=<pptxgenjs node_modules> APPLY_THEME=<pptx skill>/scripts/apply_theme.js \
//   SOFFICE_PY=<pptx skill>/scripts/office/soffice.py node docs/presentation/deck_v6/build_deck_v6.js
//
// [[text]] in any string is a fact still to fill in: it renders red and bracketed so it cannot be missed.
"use strict";
const path = require("path");
const { execFileSync } = require("child_process");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const P = (...p) => path.join(ROOT, ...p);
const OUT = path.join(__dirname, "RoomCleaner_Buntinx_Oct27_v6.pptx");
const FIGDIR = path.join(__dirname, "..", "deck_v3", "fig");
const SHEETFIG = path.join(__dirname, "..", "deck_v5", "fig");      // Sheet charts at 1.5 A (Oct 22)
const { size: imgSize } = require("../deck_v2/img_size.js");
const SHEET_URL = "https://docs.google.com/spreadsheets/d/1UGFnkL1v305WnDYj5aj5zBtgxnxmGP7_TVRN0afZTGs/edit";

const THEME = {
  name: "RoomCleaner v6", headFontFace: "Arial", bodyFontFace: "Arial",
  colors: { dk1: "1A1A1A", lt1: "FFFFFF", dk2: "1F3A5F", lt2: "F2F2F4", accent1: "1F3A5F", accent2: "8A8F98",
            accent3: "B23A2E", accent4: "4F6D8F", accent5: "D9DEE5", accent6: "5B6470", hlink: "1F3A5F", folHlink: "4F6D8F" },
};
const HEX = { ink: "000000", navy: "1F3A5F", grey: "7F7F7F", mid: "404040", light: "F2F2F2", rule: "BFBFBF", red: "B23A2E",
              navy2: "4F6D8F", pale: "D9DEE5", faint: "A6A6A6" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";                       // 13.33 x 7.5 in
pres.author = "Jasper Buntinx";
pres.title = "RoomCleaner";
pres.theme = { headFontFace: "Arial", bodyFontFace: "Arial" };
const W = 13.333, M = 0.6;

pres.defineSlideMaster({
  title: "CONTENT", background: { color: "FFFFFF" },
  objects: [
    { line: { x: M, y: 7.0, w: W - 2 * M, h: 0, line: { color: HEX.rule, width: 0.75 } } },
    { text: { text: "RoomCleaner  |  Jasper Buntinx  |  October 27, 2026", options: { x: M, y: 7.05, w: 7, h: 0.3, fontSize: 10, color: HEX.grey, fontFace: "Arial", margin: 0 } } },
  ],
  slideNumber: { x: W - M - 0.6, y: 7.05, w: 0.6, h: 0.3, fontSize: 10, color: HEX.grey, align: "right", fontFace: "Arial" },
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
function bullets(sl, items, x, y, w, h, size = 20, o = {}) {
  const arr = [];
  items.forEach((it, i) => {
    const sub = it.startsWith("- ");
    const t = (sub ? it.slice(2) : it).replace(/(\d) (?=[A-Za-z°%Ω])/g, "$1\u00A0");   // keep a number on the same line as its unit
    const base = { fontSize: sub ? size - 3 : size, color: sub ? HEX.mid : HEX.ink, fontFace: "Arial" };
    const mark = o.numbered && !sub ? { type: "number", indent: 26 } : { indent: sub ? 18 : 20 };
    const para = { bullet: mark, indentLevel: sub ? 1 : 0, paraSpaceAfter: sub ? 8 : (o.space || 14) };
    const rs = runs(t, { ...base, ...para, align: "left" });   // paragraph options on every run: pptxgenjs takes them from the last run
    rs.forEach((r, j) => { r.options.breakLine = j === rs.length - 1 && i < items.length - 1; });
    arr.push(...rs);
  });
  sl.addText(arr, { x, y, w, h, valign: "top", align: "left", margin: [2, 4, 2, 0], isTextBox: true, objectName: o.name || "bullets" });
}
// Equation box: a title, the equation, our numbers substituted (results in bold), then a "Where:" line with every input.
const EQ_LINE = 0.36;
const whereLines = (eq, w) => (eq.where ? Math.ceil((eq.where.length + 8) / ((w - 0.36) * 12.0)) : 0);
const eqHeight = (eq, w = 5.4) => 0.42 + EQ_LINE * eq.lines.length + (eq.where ? 0.1 + 0.21 * whereLines(eq, w) : 0);
function eqBox(sl, eq, x, y, w) {
  const h = eqHeight(eq, w);
  sl.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: "F7F8FA" }, line: { color: HEX.navy, width: 1.25 }, objectName: "equation box" });
  sl.addText(eq.title || "Equation", { x: x + 0.18, y: y + 0.08, w: w - 0.36, h: 0.24, fontSize: 11, bold: true, color: HEX.navy,
                                       fontFace: "Arial", margin: 0, isTextBox: true, objectName: "equation title" });
  const arr = [];
  eq.lines.forEach((ln, i) => {
    const rs = runs(ln, { fontSize: 15.5, color: HEX.ink, fontFace: "Cambria", paraSpaceAfter: 4, align: "left" })
      .flatMap(r => r.text.split(/(→)/).filter(Boolean).map(t => ({ text: t, options: t === "→" ? { ...r.options, fontFace: "Arial" } : { ...r.options } })));
    rs.forEach((r, j) => { r.options.breakLine = j === rs.length - 1 && i < eq.lines.length - 1; });
    arr.push(...rs);
  });
  sl.addText(arr, { x: x + 0.18, y: y + 0.34, w: w - 0.36, h: EQ_LINE * eq.lines.length + 0.02, valign: "top", align: "left", margin: 0,
                    isTextBox: true, objectName: "equations" });
  if (eq.where) {
    const wy = y + 0.36 + EQ_LINE * eq.lines.length + 0.04;
    sl.addText(runs("**Where:**  " + eq.where, { fontSize: 11, color: HEX.mid, fontFace: "Arial" }),
               { x: x + 0.18, y: wy, w: w - 0.36, h: 0.21 * whereLines(eq, w) + 0.04, valign: "top", margin: 0, isTextBox: true, objectName: "equation inputs" });
  }
}
function fitImage(sl, file, x, y, w, h, alt, opts = {}) {
  const { w: iw, h: ih } = imgSize(file);
  const s = Math.min(w / iw, h / ih), dw = iw * s, dh = ih * s;
  const dx = x + (opts.alignLeft ? 0 : (w - dw) / 2), dy = y + (opts.alignTop ? 0 : (h - dh) / 2);
  sl.addImage({ path: file, x: dx, y: dy, w: dw, h: dh, altText: alt, objectName: alt.slice(0, 40) });
  return { x: dx, y: dy, w: dw, h: dh };
}
function caption(sl, text, x, y, w) {
  sl.addText(runs(text, { fontSize: 11, color: HEX.grey, fontFace: "Arial" }), { x, y, w, h: 0.32, margin: 0, isTextBox: true, objectName: "caption" });
}
// Chart made in the Google Sheet, cropped from its PDF export by deck_v3/sheet_charts.py.
function sheetChart(sl, name, tab, x, y, w, h) {
  const r = fitImage(sl, path.join(SHEETFIG, `sheet_${name}.png`), x, y, w, h - 0.42, `Chart from the calculation sheet: ${tab}`, { alignTop: true });
  sl.addShape(pres.shapes.RECTANGLE, { x: r.x, y: r.y, w: r.w, h: r.h, fill: { type: "none" }, line: { color: HEX.rule, width: 0.75 }, objectName: "chart frame" });
  caption(sl, `Source: RoomCleaner engineering calculations, “${tab}” (calculated values)`, r.x, r.y + r.h + 0.08, Math.max(r.w, 4.5));
  return r;
}
function frame(sl, f, x, y, w, h, alt) {
  sl.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: HEX.light }, line: { color: HEX.light } });
  fitImage(sl, f, x + 0.06, y + 0.06, w - 0.12, h - 0.12, alt);
}
function placeholderBox(sl, text, x, y, w, h) {
  sl.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: HEX.light }, line: { color: HEX.red, width: 1, dashType: "dash" }, objectName: "placeholder" });
  sl.addText(runs(text, { fontSize: 16, color: HEX.grey, fontFace: "Arial" }), { x: x + 0.2, y, w: w - 0.4, h, align: "center", valign: "middle",
                                                                               margin: 0, isTextBox: true, objectName: "placeholder text" });
}

// Slide frame: title top left, a thin rule under it.
let SECTION = "Introduction";
function section(name) { SECTION = name; pres.addSection({ title: name }); }
function head(sl, title) {
  sl.addText(title, { x: M, y: 0.45, w: W - 2 * M, h: 0.7, fontSize: 28, bold: true, color: HEX.navy, fontFace: "Arial",
                      margin: 0, valign: "middle", isTextBox: true, objectName: "title" });
  sl.addShape(pres.shapes.LINE, { x: M, y: 1.25, w: W - 2 * M, h: 0, line: { color: HEX.rule, width: 0.75 }, objectName: "title rule" });
}
function blank(title) {
  const sl = pres.addSlide({ masterName: "CONTENT", sectionTitle: SECTION });
  head(sl, title);
  return sl;
}
// Standard slide: bullets left (equation box under them if given), one visual right.
function content(title, items, visual, notes, opts = {}) {
  const sl = blank(title);
  const split = opts.split || (opts.eq ? 0.5 : 0.46);
  const bw = (W - 2 * M) * split - 0.2;
  const eqH = opts.eq ? eqHeight(opts.eq, bw) : 0;
  bullets(sl, items, M, opts.top || 1.55, bw, opts.eq ? 5.3 - eqH - 0.2 : 5.25, opts.size || (opts.eq ? 18 : 20), { numbered: opts.numbered, space: opts.space || (opts.eq ? 10 : 14) });
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

// ------------------------------------------------------------------------------------------------ native diagrams
// pptxgenjs draws a line from the top-left to the bottom-right of its box; flipH / flipV mirror it, so the arrow end lands on (x2, y2).
function seg(sl, x1, y1, x2, y2, line) {
  sl.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
                                  flipH: x2 < x1, flipV: y2 < y1, line });
}
function label(sl, text, x, y, w, h, o = {}) {
  sl.addText(runs(text, { fontSize: o.size || 12, bold: !!o.bold, italic: !!o.italic, color: o.color || HEX.ink, fontFace: "Arial" }),
             { x, y, w, h, align: o.align || "left", valign: o.valign || "middle", margin: 0, isTextBox: true, objectName: o.name || "label" });
}
// Column heading: bold navy text over a navy rule.
function colHead(sl, text, x, y, w) {
  label(sl, text, x, y, w, 0.38, { size: 17, bold: true, color: HEX.navy, name: `${text} heading` });
  sl.addShape(pres.shapes.LINE, { x, y: y + 0.42, w, h: 0, line: { color: HEX.navy, width: 1 } });
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
  const lw = 3.7, dw = 1.75, cx = x + lw + dw, cw = x + w - cx, hh = 0.38, rh = 0.42;
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
    label(sl, name, x + 0.1, ry, lw - 0.2, rh, { size: 13 });
    label(sl, dates, x + lw + 0.1, ry, dw - 0.2, rh, { size: 13, color: HEX.mid });
    sl.addShape(pres.shapes.RECTANGLE, { x: cx + a * s, y: ry + 0.1, w: (b - a) * s, h: rh - 0.2, fill: { color: HEX.navy2 }, line: { color: HEX.navy2 },
                                         objectName: `${name} bar` });
  });
  seg(sl, x, bottom, x + w, bottom, { color: HEX.rule, width: 0.75 });
  return bottom;
}
// System block diagram: five layers, top to bottom, with the claw beside the task layer.
function layerStack(sl, x, y, w, h) {
  const layers = [["Phone app", "Start, pause, and approval before every move"],
                  ["Supervisor (laptop)", "Holds one robot state; rejects commands that do not fit it"],
                  ["Startup and tasks (laptop)", "Calibrates, then scans, grips, checks and delivers"],
                  ["Motion planner (laptop)", "Checks every point of a path, then sends timed moves"],
                  ["Wall stations (one controller each)", "Step the motor, read the encoder, hold if the link drops"]];
  const cw = 1.75, mw = w - cw - 0.45, gap = 0.22, bh = (h - 0.45 - gap * 4) / 5;
  layers.forEach(([n, d], i) => {
    const by = y + i * (bh + gap);
    sl.addShape(pres.shapes.RECTANGLE, { x, y: by, w: mw, h: bh, fill: { color: "FFFFFF" }, line: { color: HEX.navy, width: 1.25 },
                                         objectName: `layer ${i + 1}` });
    sl.addText([{ text: n, options: { bold: true, fontSize: 14, color: HEX.navy, breakLine: true } }, { text: d, options: { fontSize: 12, color: HEX.ink } }],
               { x: x + 0.15, y: by, w: mw - 0.3, h: bh, fontFace: "Arial", valign: "middle", margin: 0, isTextBox: true });
    if (i < 4) seg(sl, x + mw / 2, by + bh + 0.02, x + mw / 2, by + bh + gap - 0.02, { color: HEX.grey, width: 1.5, endArrowType: "triangle" });
  });
  const ty = y + 2 * (bh + gap), cx = x + mw + 0.45;
  sl.addShape(pres.shapes.RECTANGLE, { x: cx, y: ty - 0.1, w: cw, h: bh + 0.2, fill: { color: "FFFFFF" }, line: { color: HEX.navy, width: 1.25 }, objectName: "claw" });
  sl.addText([{ text: "Claw", options: { bold: true, fontSize: 14, color: HEX.navy, breakLine: true } }, { text: "Sends camera images; grips only when approved", options: { fontSize: 11.5 } }],
             { x: cx + 0.1, y: ty - 0.1, w: cw - 0.2, h: bh + 0.2, fontFace: "Arial", valign: "middle", margin: 0, isTextBox: true });
  seg(sl, x + mw + 0.04, ty + bh / 2, cx - 0.04, ty + bh / 2, { color: HEX.grey, width: 1.5, beginArrowType: "triangle", endArrowType: "triangle" });
  label(sl, "Commands flow down; status and camera images flow up.", x, y + h - 0.35, w, 0.3, { size: 12, color: HEX.mid, name: "layer note" });
}
// Startup calibration as a process flow: two rows of three, the second row running back right to left.
function calFlow(sl, x, y, w, h) {
  const steps = ["Take up slack, one cable at a time", "Lift the claw off the floor", "Camera reads the floor board",
                 "Fit anchors and cable lengths", "Check on held-out poses", "Ready, inside the safety margins"];
  const gx = 0.34, gy = 0.34, bw = (w - 2 * gx) / 3, bh = (h - gy) / 2;
  const pos = i => (i < 3 ? { x: x + i * (bw + gx), y } : { x: x + (5 - i) * (bw + gx), y: y + bh + gy });
  steps.forEach((s, i) => {
    const p = pos(i);
    sl.addShape(pres.shapes.RECTANGLE, { x: p.x, y: p.y, w: bw, h: bh, fill: { color: "FFFFFF" }, line: { color: HEX.navy, width: 1.25 },
                                         objectName: `calibration step ${i + 1}` });
    sl.addText([{ text: `${i + 1}.  `, options: { bold: true, color: HEX.navy } }, { text: s, options: { color: HEX.ink } }],
               { x: p.x + 0.08, y: p.y, w: bw - 0.16, h: bh, fontSize: 14, fontFace: "Arial", valign: "middle", align: "center", margin: 0, isTextBox: true });
  });
  const arrow = (ax, ay, aw, ah, flipH) => sl.addShape(pres.shapes.LINE, { x: ax, y: ay, w: aw, h: ah, flipH, line: { color: HEX.grey, width: 1.5, endArrowType: "triangle" } });
  arrow(x + bw + 0.05, y + bh / 2, gx - 0.1, 0); arrow(x + 2 * bw + gx + 0.05, y + bh / 2, gx - 0.1, 0);
  arrow(x + 2.5 * (bw) + 2 * gx, y + bh + 0.05, 0, gy - 0.1);
  arrow(x + 2 * bw + gx + 0.05, y + bh + gy + bh / 2, gx - 0.1, 0, true); arrow(x + bw + 0.05, y + bh + gy + bh / 2, gx - 0.1, 0, true);
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
  sl.addText("A cable-driven robot that picks laundry up off the floor", { x: M, y: 3.35, w: 4.6, h: 1.2, fontSize: 22, color: "D9DEE5", fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addText("Jasper Buntinx\nMechanical Engineering, Texas A&M University\nOctober 27, 2026", { x: M, y: 5.7, w: 4.8, h: 1.1, fontSize: 14, color: "D9DEE5", fontFace: "Arial", margin: 0, isTextBox: true });
  fitImage(sl, PH("11_gen2_station_assembled.jpg"), 6.0, 0.6, 3.3, 6.3, "Generation 2 winch station, assembled");
  fitImage(sl, PH("21_claw_printed_tube_servo.jpg"), 9.45, 0.6, 3.3, 6.3, "Printed claw body with its servo");
  sl.addNotes("One sentence: four winches near the ceiling corners hold one claw on cables; it picks clothes off the floor and drops them in a hamper. " +
              "Then straight to who I am.");
}

content("About Me", [
  "B.S. Mechanical Engineering, Texas A&M University, [[graduation month and year]]",
  "Built EcoFil, a filament recycler with a shredder, dryer and extruder",
  "Metal sculptures for the Austin Creek Show, made with fiber laser cutting and welding",
  "Outside of class: [[hobbies and interests]]",
  "Why this project: [[one sentence]]",
], (sl, x, y, w, h) => placeholderBox(sl, "[[Photo of you building: EcoFil, a sculpture, or the workshop]]", x, y, w, h - 0.3),
"One minute. Degree and graduation date, EcoFil (what each stage does, what you learned), the sculptures (fiber laser and welding: real " +
"fabrication), one hobby. Close with why a laundry robot: a problem you have, and a machine you could build end to end yourself.");

content("Agenda", [
  "Project goal, scope and timeline",
  "Design: targets, trade-offs and key calculations",
  "Build: printed parts, machining and electronics",
  "Test: first system test and thermal verification",
  "Good and poor decisions, and lessons learned",
], (sl, x, y, w, h) => {
  frame(sl, FG("position_vectors.png"), x + 0.6, y, w - 1.2, h - 0.4, "Cable robot geometry: four anchors and the claw");
  caption(sl, "Cables from the ceiling anchors a_1 to a_4 to the claw at p", x + 0.6, y + h - 0.3, w - 1.2);
}, "About 40 minutes, then questions. Backup slides at the end cover calibration, control logic, the phone app, obstacles, electrical and safety.",
{ split: 0.5, size: 22, numbered: true, space: 22, top: 1.75 });

content("Project Goal", [
  "Pick up laundry anywhere in an 11 × 9 ft room and drop it in a hamper",
  "Four ceiling-mounted winches suspend one claw on cables",
  "Design load: jeans, 0.9 kg, at 2 m/s² acceleration; first test load is 1 lb",
  "3D-printed PETG (polyethylene terephthalate glycol) parts on a hobby budget",
  "Success: one garment delivered to the hamper with no human input",
], (sl, x, y, w, h) => {
  const files = [R("station_1021_final.png"), R("gripper1021_asbuilt.png")];
  const gap = 0.15, each = (w - gap) / 2;
  files.forEach((f, i) => frame(sl, f, x + i * (each + gap), y, each, h - 0.3, i ? "Final claw" : "Final wall station"));
  caption(sl, "Final design (CAD): wall station, left; claw, right", x, y + h - 0.22, w);
}, "Why a cable robot: it covers the whole floor, nothing stands on the floor, and the moving mass is small. " +
"Safety rules: stations anchor into studs, the switched power strip is the one hard stop, nobody stands under the robot. " +
"0.9 kg is a screening figure for jeans; the first physical test is 1 lb. The claw tube is 10.5 in. " +
"Milestones: one station running repeatably (passed on the bench), three stations holding and moving 1 lb (this week's test), one garment into the hamper.",
{ split: 0.5, size: 20 });

{
  const sl = blank("Scope and Timeline");
  const gy = gantt(sl, [
    ["Concept and requirements", "Jul 16 – Aug 5", 15, 36],
    ["Generation 1: build and bench test", "Aug 6 – Sep 2", 36, 64],
    ["Redesign: sensors and wiring", "Sep 3 – Oct 6", 64, 98],
    ["Generation 2 and final design", "Oct 7 – Oct 21", 98, 113],
    ["Build and first system test", "Oct 22 – Oct 27", 113, 119],
  ], M, 1.55, W - 2 * M);
  const y = gy + 0.35, lw = 6.9, rx = M + lw + 0.4, rw = W - M - rx;
  colHead(sl, "My work (solo project)", M, y, lw);
  bullets(sl, [
    "Requirements, calculations and test plans",
    "All CAD (computer-aided design) in SolidWorks",
    "3D printing, fit testing and machining the heat fin",
    "Wiring, soldering and electronics bring-up",
    "Control software: [[confirm the parts you wrote]]",
  ], M, y + 0.55, lw, 6.85 - y - 0.55, 16, { space: 4, name: "my work" });
  colHead(sl, "Purchased or external", rx, y, rw);
  bullets(sl, [
    "Stepper motors, drivers and controller boards",
    "Servo, camera, battery and encoder boards",
    "Garment detection: YOLO-World, an open-source model",
    "Shop access or mentors: [[if any]]",
  ], rx, y + 0.55, rw, 6.85 - y - 0.55, 16, { space: 4, name: "bought" });
  sl.addNotes("About 15 weeks, alone. Generation 1 (August) worked on the bench: corner plates, one central controller board, a finger claw. " +
              "September to early October was the redesign that drove generation 2: sensors at every winch, the wiring that caused, and the line outlets. " +
              "Generation 2 in October went through three station and three spool versions to the final design on Oct 21. This week: build and the first test. " +
              "Say plainly what is mine and what is bought. [Confirm the start date (git shows Jul 16) and what happened in September.]");
}

content("How It Works", [
  "Four wall stations, each with its own winch, encoder and controller",
  "One claw with a gripper, camera and battery, hung on four cables",
  "Laptop plans each move and checks every cable tension before it runs",
  "Phone app starts, pauses and approves each move",
  "Software simulated end to end; hardware test this week",
], (sl, x, y, w, h) => layerStack(sl, x, y, w, h),
"Zoomed out: only the bottom layer turns a motor. The phone asks the supervisor; the supervisor holds one robot state; the planner checks " +
"every point of a path before anything moves; the stations run the motion on their own clocks and hold if the laptop goes quiet. " +
"The claw is a camera plus a gripper that obeys. Details are in the appendix (operating sequence, obstacles, the phone app).",
{ split: 0.42 });

// ================================================================================================ DESIGN
section("Design");
{
  const sl = blank("Design Targets");
  const NOT = { text: "Not met", color: HEX.red, bold: true };
  table(sl, ["Parameter", "Target", "Current value", "Status"], [
    ["Lift capacity", "1.76 kg: claw, battery and jeans", "1.56 kg (calculated)", NOT],
    ["Claw mass", "0.45 kg", "0.86 kg with battery (estimated); [[weighed]]", NOT],
    ["Motor temperature", "Below 60 °C (PETG limit)", "58 °C prototype fin; 45–49 °C with 1/8 in fin", "Marginal"],
    ["Working area", "Full 11 × 9 ft floor", "All but 0.2 m along the walls", "Met in design"],
    ["Wiring", "One cable per station", "One 12 V pair; 0.51 V drop on the longest run", "Met"],
    ["Positioning accuracy", "2 mm per cable", "0.7 mm (calculated)", "To be tested"],
    ["Speed", "50 mm/s at 2 m/s²", "Not yet run", "To be tested"],
    ["Cost", "Hobby budget", "[[total cost]]", "[[]]"],
  ], M, 1.55, W - 2 * M, [0.2, 0.28, 0.37, 0.15], { size: 14, rowH: 0.52 });
  label(sl, "Safety is a fixed constraint and is not traded against any of these targets.", M, 6.35, W - 2 * M, 0.4, { size: 15 });
  sl.addNotes("Eight targets, each with a number. Two are not met today: lift capacity and claw mass, and they are the same problem " +
              "seen from two sides. Motor temperature is marginal since the 1.5 A change. Working area and wiring are met by the design. Accuracy, " +
              "speed and cost wait on the hardware test and the receipts. Safety is a constraint, not a target: I never trade it for any of the others.");
}

{
  const sl = blank("Design Trade-offs");
  table(sl, ["Design change", "Benefit", "Cost", "Chosen setting"], [
    ["Higher motor current", "41 % more pull at 1.5 A", "Heat rises with current squared: 2.0 W to 4.05 W", "1.5 A, vented shell and heat fin"],
    ["Stronger claw", "Gear safety factor from 0.4 to 2.0", "More claw mass, less payload", "Module 1.5 gears"],
    ["Larger room", "More floor covered", "Longer wires, more voltage drop", "Only 12 V power runs to the stations"],
    ["Working closer to the ceiling", "More working volume", "Cable tension rises from 12 N to 32 N", "Stay 0.4 m below the anchors"],
    ["Smaller spool radius", "More pull per amp", "Slower line speed", "15 mm core: 34 N empty, 25 N full"],
    ["Larger safety margins", "No skipped steps or wall contact", "Less usable force and floor area", "Force ÷ 1.5; 0.2 m from walls"],
  ], M, 1.55, W - 2 * M, [0.21, 0.24, 0.29, 0.26], { size: 14, rowH: 0.62 });
  label(sl, "Key coupling: a heavier claw needs more pull, more pull needs more current, and heat rises with the square of the current.",
        M, 6.15, W - 2 * M, 0.5, { size: 15 });
  sl.addNotes("Every change helps one thing and hurts another, and each design slide after this is one of these trades. " +
              "Current: pull goes with I but heat goes with I squared, so 41 % more pull costs twice the heat. " +
              "Claw strength: the stall check pushed the gears from module 1 to 1.5, and every gram of claw comes out of the payload. " +
              "Room size: wire resistance grows with length, R = ρL/A; that is why only power travels, and the longest 32 ft run drops 0.51 V at 2 A on 16-gauge wire. " +
              "Ceiling: tension doubles each time the depth below the anchors halves. Spool: a smaller radius pulls harder but reels slower, and the radius grows as the line winds on. " +
              "Margins: they buy safety with force and floor area. The last line is why weight matters so much.");
}

content("Cable Tension", [
  "Cables can only pull, so tension must stay positive",
  "Tension rises sharply near the ceiling",
  "32 N per cable at 0.15 m below the anchors; 8.3 N at 0.6 m",
  "Operating limit: 0.4 m below the anchors",
], { sheet: "cable_tension", tab: "Cable tension" },
"Force balance on the claw: the cable pulls and the weight sum to zero. Centered claw, equal shares. D_h = 2.17 m from the room center to a " +
"corner. The tension doubles each time the depth halves near the ceiling, so the ceiling margin is set by tension, not by collision. " +
"At 1.06 A the design force was 11.9 N, so 0.4 m was only just enough standing still (12.2 N). At 1.5 A it is 16.8 N, so 0.4 m also covers the " +
"2 m/s² acceleration case (14.7 N). 0.3 m would now hold standing still (16.2 N) but not while accelerating (19.5 N), so I keep 0.4 m. " +
"If asked about a corner pick: the far cables go near-horizontal and carry little; the planner checks every cable stays inside its tension limits.",
{ eq: { title: "Cable tension at the operating limit", lines: [
  "T = W / (4 sin φ),   sin φ = d / √(d² + D_h²)",
  "sin φ = 0.4 / √(0.4² + 2.17²) = 0.181",
  "T = 8.87 N / (4 × 0.181) = **12.2 N**",
  "With 2 m/s²: 12.2 × 1.20 = **14.7 N** < 16.8 N",
], where: "W = (0.45 + 0.454) kg × 9.81 m/s² = 8.87 N; d = 0.4 m below the anchors; D_h = 2.17 m, room center to corner; 16.8 N = winch design force" } });

content("Winch Pull", [
  "NEMA 17 (National Electrical Manufacturers Association) stepper with a printed spool",
  "Driver current raised to the rated 1.5 A (was 1.06 A)",
  "Pull: 34 N with an empty spool, 25 N when full",
  "Luggage-scale pull test to confirm the torque",
], { sheet: "winch_pull", tab: "Winch pull" },
"Current limit from the driver's reference voltage (A4988 datasheet): the first boards topped out at 0.85 V, which is 1.06 A. I got the " +
"drivers to 1.5 A, the motor's rated current, so every pull goes up 41 % (1.5 / 1.06). [Fill in: how, and the Vref you read.] " +
"The cost is heat: the motor makes twice the heat (next slides). Running torque is lower than holding torque; I assumed 0.7, and the pull " +
"test measures it. A smaller spool gives more pull per amp but more turns per meter. The 1.5 margin covers skipped steps.",
{ eq: { title: "Winch design force at 1.5 A", lines: [
  "I = V_{ref} / (8 R_s) = 1.2 V / (8 × 0.1 Ω) = **1.5 A**",
  "τ_{run} = 0.7 × 0.36 N·m = 0.252 N·m",
  "T = τ / r = 0.252 N·m / 0.010 m = **25.2 N**",
  "F_{design} = 25.2 N / 1.5 = **16.8 N**",
], where: "V_ref = driver reference voltage; R_s = sense resistor; 0.36 N·m = holding torque at 1.5 A; 0.7 = running/holding ratio (assumed); r = 10 mm full spool; 1.5 = skip margin" } });

content("One Controller per Winch", [
  "Generation 1 drove all four motors from one central board",
  "Adding sensors at each winch required 10 wires per corner",
  "Moved to a separate controller in each station",
  "Total wire reduced from 820 ft to 164 ft",
], { sheet: "wiring", tab: "Wiring" },
"Real cable routes are 6, 21, 23 and 32 ft (82 ft). 10 conductors × 82 ft = 820 ft against 2 × 82 ft = 164 ft for one power pair. " +
"The cost: synchronization moved into software. Each station runs time-stamped segments on its own clock; any lost link means hold. " +
"Timing skew becomes cable mismatch: 50 mm/s × 50 ms = 2.5 mm, which is why segments are time-stamped.",
{ eq: { title: "Wire length and timing error", lines: [
  "Wire = n × ΣL",
  "Central board: 10 × 82 ft = **820 ft**",
  "Controller per station: 2 × 82 ft = **164 ft**",
  "Timing error: Δx = v Δt = 50 mm/s × 50 ms = **2.5 mm**",
], where: "n = conductors per corner (motor 4, switch 2, encoder 4); ΣL = 6 + 21 + 23 + 32 ft of cable routes; v = line speed; Δt = clock offset between stations" } });

content("Motor Cooling", [
  "Sealed PETG shell traps motor heat",
  "PETG creeps above 60 °C under load",
  "Aluminum fin added through the top of the shell",
  "90-minute hold test at 1.5 A planned",
], { sheet: "motor_temperature", tab: "Motor temperature" },
"Model: motor to shell air to room, with the fin as a second path out. At 1.5 A the motor makes 4.05 W, double the 2.0 W at 1.06 A. " +
"Sheet results, vented shell: no fin 77 °C, 0.019 in fin 57.6 °C, 1/8 in fin 48.9 °C; sealed: 99, 66 and 54 °C, so the shell stays vented. " +
"With radiation from the black paint included (refined model) the 1/8 in fin gives about 45 °C. The driver chip also heats more; if it overheats it " +
"shuts off and the winch loses torque, so the hold test watches it too. Fallback: 1.35 A. Shape: one tall blade from the heat source.",
{ eq: { title: "Motor heat and temperature at 1.5 A", lines: [
  "P = I² R_{coil} = (1.5 A)² × 1.8 Ω = **4.05 W**",
  "1/R_{th} = 1/R_{shell} + 1/R_{fin},   ΔT = P × R_{th}",
  "0.019 in fin: R_{fin} = 23.1 K/W → **57.6 °C**",
  "1/8 in fin: R_{fin} = 11.9 K/W → **48.9 °C**",
], where: "R_coil = 1.8 Ω per phase (assumed); R_shell = 12 + 1 K/W, motor to shell air to room; room at 23 °C; 1.5 W of electronics in the shell; limit 60 °C" } });

content("Heat Fin Sizing", [
  "0.019 in prototype fin reaches 95 % of its capacity by 136 mm",
  "1/8 in design fin is 74 % efficient at 200 mm",
  "Built length of 200 mm, limited by ceiling clearance",
], { sheet: "heat_fin", tab: "Heat fin" },
"Target length: L95, where a fin gets 95 % of the heat an infinitely long one would. The thin sheet reaches it at 136 mm, so most of its 200 mm " +
"does little; the 1/8 in plate keeps gaining to 349 mm, so 200 mm is a compromise with the ceiling (the fin top is 229 mm above the shaft). " +
"At 200 mm: sheet 37 % efficient and 22.1 K/W; 1/8 in plate 74 % and 10.9 K/W. Fin equations: Incropera, Fundamentals of Heat and Mass Transfer, ch. 3.",
{ eq: { title: "Fin length and efficiency", lines: [
  "m = √(2h / (k t)),   L_{95} = 1.83 / m",
  "0.019 in: m = √(2 × 7 / (160 × 0.00048)) = 13.5 /m",
  "L_{95} = 1.83 / 13.5 = **136 mm**",
  "1/8 in: m = 5.25 /m,  L_{95} = **349 mm**",
  "η = tanh(mL) / (mL) = tanh(1.05) / 1.05 = **0.74**",
  "R_{fin} = 1 / (7 × 0.74 × 0.0176) = **10.9 K/W**",
], where: "h = 7 W/m²·K, still air; k = 160 W/m·K, aluminum; t = fin thickness; L = 200 mm; A = 2 × 44 mm × 200 mm = 0.0176 m²; R_fin = 1 / (h η A)" } });

content("Homing Method", [
  "Original plan: a bead on each cable trips a switch at the outlet",
  "Cables could not get shorter than their homing length",
  "Replaced with camera calibration on a printed floor board",
  "Full room now reachable; beads kept as end stops",
], { sheet: "bead_homing", tab: "Bead homing" },
"This was a poor first plan, caught on paper before it was built. The limit is physical, so software cannot remove it. " +
"Replacement: take up slack one cable at a time, lift, look at the floor board from several poses, least-squares fit of anchors and zero lengths, " +
"check on held-out poses. Safety comes from margins (0.4 m below the anchors, 0.2 m inside the walls), not precision. Four tags in view: 0.7 mm " +
"vs 6.6 mm with one (appendix). Simulated so far; the first hardware run is this week.",
{ eq: { title: "Reachable area with bead homing", lines: [
  "L_i(**p**) ≥ L_{i,home} = ‖**a**_i − **p**_{home}‖",
  "Home 1 m above the floor: **5 %** reachable",
  "Home 2 m above the floor: **29 %** reachable",
], where: "a_i = anchor i; p = claw position; reachable = every cable at or above its home length, inside the 0.2 m wall and 0.4 m ceiling margins" } });

content("Claw Design", [
  "Generation 1 used five TPU (thermoplastic polyurethane) fingers",
  "Fingers could not pinch thin fabric and were 4.6 times over the mass budget",
  "Final design: geared four-bar with parallel jaws and a 53 mm opening",
], { grid: [R("gen1_tentacle_claw.png"), R("claw_v6.png"), R("gripper1021_head.png"), PH("22_gear_train_printed_servo.jpg")],
     alt: "Claw generations and the printed gear train", caption: "Left to right, top to bottom: generation 1 fingers, v6 clamp, final four-bar (CAD), printed gear train" },
"Each generation fixed a problem found in the one before. Mass drove most changes: every gram of claw is a gram of laundry the winches cannot lift. " +
"Four-bar: ground 36.5, crank 53, rocker 50, coupler 34.7 mm; jaws parallel within about 1 degree; closing drops the tips about 38 mm, a scoop. " +
"Gear train: servo, 18-tooth pinion, 36/24-tooth compound, 24-tooth sync gear. Lewis check at servo stall: module 1 safety factor 0.35 to 0.41, so the module went up to 1.5. " +
"The camera also moved from the ceiling into the claw: it sees the grasp and reads the floor board.",
{ eq: { title: "Grip force and gear stress at servo stall", lines: [
  "N ≥ W / (2μ) = 4.45 N / 0.6 = **7.4 N**",
  "F_t = 2τ / d = 2 × 1.078 / 0.027 = 79.9 N",
  "σ = F_t / (b m Y) = 79.9 / (15.7 × 1.5 × 0.309)",
  "σ = 11.0 MPa,  SF = 22.5 / 11.0 = **2.05**",
], where: "N = grip force per jaw; W = 1 lb test load; μ = 0.3; τ = 1.078 N·m servo stall torque; d = 27 mm pitch diameter; b = 15.7 mm face width; m = 1.5 mm module; Y = 0.309 Lewis factor; SF = safety factor" } });

content("Weight Budget: Open Issue", [
  "Lift capacity at 1.5 A is 1.56 kg",
  "Claw with battery estimated at 0.86 kg [[weighed mass]]",
  "1 lb test load fits; jeans exceed capacity by 0.2 kg",
  "Options: a lighter claw or a 3:1 gear reduction on the winch",
], { sheet: "lift_budget", tab: "Lift budget" },
"Be upfront: even at 1.5 A the current claw plus jeans is too heavy, by about 0.2 kg instead of 0.66 kg. Root cause: I set the mass budget " +
"late, after the claw grew. Capacity = design force / (worst tension per unit weight × g) = 16.8 / (1.101 × 9.81) = 1.56 kg; the worst point " +
"is the middle of a long wall at task height. " +
"Claw mass estimate: 0.55 infill fraction × 927 g solid + 198 g tube + 55 g servo ≈ 0.76 kg. The pull test turns the 0.7 running-torque " +
"assumption into a measurement, and that number picks the fix.",
{ eq: { title: "Lift capacity against the required mass", lines: [
  "m_{max} = F_{design} / (k g)",
  "= 16.8 N / (1.101 × 9.81 m/s²) = **1.56 kg**",
  "m_{claw} = 0.55 × 0.927 + 0.198 + 0.055 = **0.76 kg**",
  "Required: 0.76 + 0.10 + 0.90 = **1.76 kg** > 1.56 kg",
], where: "k = worst cable tension per unit weight over the room, with 2 m/s²; 0.55 = print fill; 0.927 kg = solid PETG from CAD; 0.198 kg tube; 0.055 kg servo; 0.10 kg battery; 0.90 kg jeans" } });

// ================================================================================================ BUILD
section("Build");
content("Printed Part Fits", [
  "PETG printed on a Creality K1 at 0.2 mm layers",
  "Printed holes come out undersize by at least 0.2 mm",
  "The spool needed three prints to fit the motor shaft",
  "Fit coupons are now printed before full parts",
], { file: [R("spool_v1.png"), R("spool_v2.png"), R("spool_v3.png")], alt: "Spool v1, v2, v3", caption: "Spool versions 1, 2 and 3 (CAD)" },
"Orientation: flat face on the bed, loads along the layers, no supports on mating faces. Bearing pocket Ø14.075 with a Ø14.000 lead-in lip. " +
"Heat-set M3 inserts where screws are reused. Spool v1 was longer than the motor shaft could engage; v2's Ø5.2 bore printed too tight on the 5 mm " +
"shaft, so the printer undersize is at least 0.2 mm; v3 opened it to Ø5.45 (about 0.25 mm clearance) with a D-flat. Ø15 core, 16 mm drum: 20 ft of line in 5 layers.",
{ eq: { title: "Spool bore clearance", lines: [
  "c = (D_{hole} − u) − D_{shaft}",
  "Ø5.2 bore too tight, so u ≥ 0.2 mm",
  "c = (5.45 − 0.2) − 5.00 = **0.25 mm**",
], where: "c = clearance; u = printer undersize; D_shaft = 5.00 mm motor shaft; version 3 bore Ø5.45 with a D-flat for the set screw" } });

content("Heat Fin Manufacturing", [
  "Shop drawing printed 1:1 and used as a hole template",
  "Prototype cut from 0.019 in aluminum sheet already on hand",
  "All five holes drilled in one mill setup to ±0.1 mm",
  "Fin bolted to the motor without reaming",
], { grid: [PH("06_shear_with_drawings_and_blanks.jpg"), PH("03_mill_setup_with_shop_drawing.jpg"), PH("02_mill_drilling_fin.jpg"), PH("15_heat_fin_finished_part.jpg")],
     alt: "Fin manufacturing photos", caption: "Shear and blanks, mill setup with the drawing, drilling, and the finished fin" },
"One setup from the same two edges means hole-to-hole errors do not stack. Holes: a 7/8 in pilot for the motor boss and 4 × Ø3.4 on the 31 mm " +
"motor square. Paint everywhere except the motor contact square, which gets thermal paste. The production fin is 1/8 in plate. [Fill in: time per fin, how many made, any scrap.]");

content("Electronics Bring-Up", [
  "Driver stays disabled at boot, so a reset cannot move the motor",
  "Schematic generated from the soldered board, 16 nets",
  "First motor failed to turn: logic rail measured 1.14 V instead of 3.3 V",
  "Supply rails are now checked with a meter before any code is loaded",
], { file: [PH("19_station_perfboard_soldered.jpg"), PH("12_bench_bringup_laptop.jpg")], alt: "Soldered station board and bench bring-up",
     caption: "Soldered station board, left; bench bring-up, right" },
"Boot-safe: a 10k pull-up holds the driver's enable pin off until the firmware arms it. USB and the 5 V buck cannot back-feed each other (link jumper " +
"plus a Schottky diode). The schematic is generated from the soldered board's net list, so the two cannot disagree. The 1.14 V story: measure the " +
"hardware before trusting the software's view of it. Checklist: logic supply, sleep, enable and the buck output on every new board. " +
"[Fill in: exact readings, date, what you tried first.]",
{ split: 0.46 });

// ================================================================================================ TEST
section("Test");
content("First System Test", [
  "Three stations: the fewest cables that fully constrain the claw",
  "Sequence: self-check, calibration, short move, then pickup",
  "1 lb test load first, then one garment",
  "Pass limits defined before the run",
], (sl, x, y, w, h) => {
  placeholderBox(sl, "[[Photo or video from the three-station test]]", x, y, w, 2.45);
  table(sl, ["Check", "Pass limit", "Result"], [
    ["Startup self-check", "All stations answer; slack taken up", "[[]]"],
    ["Calibration fit", "Held-out poses inside the safety margin", "[[]]"],
    ["Short move, 1 lb", "300 mm at 50 mm/s, ≤ 2 mm per cable", "[[]]"],
    ["Pickup", "One garment into the hamper", "[[]]"],
  ], x, y + 2.65, w, [0.3, 0.5, 0.2], { size: 13, rowH: 0.48, name: "pass limits" });
}, "Three cables, three unknown tensions, three force equations: statically determinate, so the tensions are solved exactly and slack shows up " +
"directly. It is the simplest real test of the calibration and the coordinated motion. Logged: cable lengths, encoder counts, motor temperatures, " +
"the fit's error bars. Fill in the results after the test, including any that fail.",
{ split: 0.42 });

content("Thermal Verification", [
  "PETG mount must stay below 60 °C",
  "Hand calculation: 56–59 °C with the prototype fin, 45–49 °C with the 1/8 in fin",
  "SolidWorks thermal study of the motor, fin, screws and mount",
  "90-minute hold test at 1.5 A to confirm",
], (sl, x, y, w, h) => {
  placeholderBox(sl, "[[SolidWorks temperature plot: motor, fin, screws and mount]]", x, y, w, 2.4);
  table(sl, ["Method", "0.019 in fin", "1/8 in fin", "PETG mount"], [
    ["Hand calculation", "56–59 °C", "45–49 °C", "2 K below motor"],
    ["SolidWorks", "[[]]", "[[]]", "[[]]"],
    ["Hold test", "[[]]", "[[]]", "[[]]"],
  ], x, y + 2.55, w, [0.28, 0.24, 0.24, 0.24], { size: 14, rowH: 0.5, name: "thermal methods" });
  caption(sl, "Motor temperature at 1.5 A, 23 °C room, vented shell", x, y + 2.55 + 4 * 0.5 + 0.12, w);
}, "The 60 °C limit is for the loaded PETG, and that is the one temperature the hand calculation cannot give: it only knows the motor node. " +
"The SolidWorks thermal study uses my 10/21 assembly with a detailed NEMA 17 (aluminum end caps, black steel stator, copper windings as the 4.05 W source, " +
"plastic connector), the fin, the four M3 screws into the motor, and the PETG slip-in mount; inside the shell 26 to 27 °C, outside 23 °C. " +
"Hand calculation: 56 to 59 °C with the prototype fin, 45 to 49 °C with the 1/8 in fin (the range is the simple and the refined model). " +
"Then the hold test measures it. If they disagree, I fit h and the coil resistance, not the physics.",
{ split: 0.44 });

// ================================================================================================ LESSONS
section("Lessons");
{
  const sl = blank("Good and Poor Decisions");
  const cw = [0.36, 0.64];
  table(sl, ["Good decision", "Outcome"], [
    ["One controller per winch", "Five times less wire; each station tested on its own"],
    ["Slide-in wall mount", "A station comes off while its anchor stays in place"],
    ["Camera calibration instead of bead homing", "Whole room reachable; no tape measure needed"],
    ["Gear strength checked at servo stall", "Module 1 gears would have failed; fixed in CAD before printing"],
  ], M, 1.55, W - 2 * M, cw, { size: 14, rowH: 0.48, name: "good decisions" });
  table(sl, ["Poor decision", "Outcome"], [
    ["Mass budget set late", "Claw and jeans are 0.2 kg over capacity, even at 1.5 A"],
    ["Bead homing as the first plan", "Under a third of the room reachable; redesign needed"],
    ["Spool printed before a fit test", "Three prints to fit the motor shaft"],
    ["Several stations built before one was proven", "Every fix repeated on each station [[confirm]]"],
  ], M, 4.25, W - 2 * M, cw, { size: 14, rowH: 0.48, headColor: HEX.red, name: "poor decisions" });
  sl.addNotes("Good: each was a trade I priced first. Distributed control cost me software synchronization (2.5 mm per 50 ms of skew) but saved 5× the wire. " +
              "The slide-in mount came from taking stations down to rework them. Calibration by camera replaced a plan that physically limited the motion. " +
              "The stall check caught gears that would have sheared before I printed them. " +
              "Poor: the mass budget came after the claw grew, which is the open issue today. Bead homing looked cheap until I computed what it cost. " +
              "The spool bore needed a coupon. And building several stations before one was fully proven meant repeating each fix. [Confirm the last one.]");
}

{
  const sl = blank("Thorough vs. Scrappy");
  const cw = (W - 2 * M - 0.4) / 2, y0 = 1.55;
  const cols = [
    ["Thorough", PH("03_mill_setup_with_shop_drawing.jpg"), "Heat fin: mill setup with the shop drawing", [
      "Heat fin sized by calculation and machined in one mill setup to ±0.1 mm",
      "Station schematic checked net by net against the soldered board",
      "Gear strength checked at servo stall before printing",
    ]],
    ["Scrappy", P("docs/electrical/station_revD_20261021/breadboard_layout_esp32.png"), "ESP32 dev board jumpered onto the station breadboard", [
      "Failed controller replaced by an ESP32 dev board on nine jumpers, same firmware",
      "Floor board made from paper tags on a 250 mm grid",
      "Prototype fin cut from 0.019 in sheet already on hand",
    ]],
  ];
  cols.forEach(([t, img, alt, items], k) => {
    const x = M + k * (cw + 0.4);
    colHead(sl, t, x, y0, cw);
    frame(sl, img, x, y0 + 0.6, cw, 2.3, alt);
    bullets(sl, items, x, y0 + 3.05, cw, 1.75, 16, { space: 8, name: `${t} bullets` });
  });
  label(sl, "Approach: thorough where a mistake is expensive or unsafe, scrappy where it is cheap to undo.", M, 6.4, W - 2 * M, 0.45, { size: 16, bold: true });
  sl.addNotes("Thorough: the fin is machined once, so the hole pattern had to be right before the first cut. The board schematic is generated from the " +
              "soldered net list so the drawing cannot lie. The gear check happened in CAD because a sheared gear costs a print and a jammed claw. " +
              "Scrappy: when a controller board died two days before the test, I moved the same circuit to an ESP32 dev board with nine jumpers and a " +
              "compile-time pin map instead of redesigning the board. The floor board is paper tags because accuracy comes from seeing several tags, not " +
              "from the board. Three stations now, because three cables already test calibration and coordinated motion while the fourth is built.");
}

{
  const sl = blank("Lessons Learned");
  const cw = (W - 2 * M - 0.4) / 2, y0 = 1.55;
  colHead(sl, "What I would do differently", M, y0, cw);
  bullets(sl, [
    "Set the mass budget early, from the measured winch pull",
    "Print fit coupons before full parts",
    "Prove one complete station before building the rest",
    "Check supply rails with a meter before debugging code",
  ], M, y0 + 0.6, cw, 2.6, 17, { space: 8, name: "do differently" });
  const rx = M + cw + 0.4;
  colHead(sl, "Completing it in half the time", rx, y0, cw);
  bullets(sl, [
    "Freeze requirements in the first week",
    "Order long-lead parts on day one",
    "Start with three stations",
    "Limit each part to one generation, gated by a test",
  ], rx, y0 + 0.6, cw, 2.6, 17, { space: 8, name: "half the time" });
  // actual vs half-time schedule, same scale (inches per day)
  const lx = M, lw = 1.7, bx = M + lw, bw = W - M - bx, days = 104, s = bw / days, by = 4.75, bh = 0.6;
  const actual = [["Concept", 21, HEX.pale], ["Generation 1", 28, HEX.navy2], ["Redesign", 34, HEX.pale], ["Gen 2 to final", 15, HEX.navy2], ["Build, test", 6, HEX.navy]];
  const half = [["Plan", 7, HEX.pale], ["One full station and tests", 14, HEX.navy2], ["Copy", 7, HEX.pale], ["Claw, coupons first", 14, HEX.navy2], ["Test", 7, HEX.navy]];
  [[actual, "Actual\n(15 weeks)", by], [half, "Half time\n(7 weeks)", by + bh + 0.3]].forEach(([segs, name, yy]) => {
    label(sl, name, lx, yy, lw - 0.1, bh, { size: 13, bold: true, color: HEX.navy });
    let cx = bx;
    segs.forEach(([t, d, c]) => {
      const sw = d * s;
      sl.addShape(pres.shapes.RECTANGLE, { x: cx, y: yy, w: sw, h: bh, fill: { color: c }, line: { color: "FFFFFF", width: 1.5 }, objectName: t });
      label(sl, t, cx + 0.04, yy, sw - 0.08, bh, { size: sw < 0.9 ? 10 : 12, bold: true, color: c === HEX.pale ? HEX.navy : "FFFFFF", align: "center" });
      cx += sw;
    });
  });
  caption(sl, "Same time scale. Actual schedule: July 16 to October 27.", bx, by + 2 * bh + 0.4, bw);
  sl.addNotes("What I would do differently: weigh the claw and set its mass budget from the measured winch pull before designing it; coupons before " +
              "every new fit; one complete station tested end to end before building more; a meter on every rail before debugging code. " +
              "Half the time: most of the lost time was the redesign (September to early October) and the generations that a frozen requirement and an " +
              "early test would have avoided. Order the slow parts on day one. Three stations are statically determinate and need fewer parts for the first test.");
}

{
  pres.addSection({ title: "Close" });
  const sl = pres.addSlide({ masterName: "SECTION", sectionTitle: "Close" });
  sl.addText("Questions", { x: M, y: 2.8, w: 11, h: 1.0, fontSize: 48, bold: true, color: "FFFFFF", fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addText("Jasper Buntinx  |  jasper_buntinx@tamu.edu", { x: M, y: 3.9, w: 11, h: 0.6, fontSize: 20, color: "D9DEE5", fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addNotes("The appendix follows: project status, fin sizing for 4 W, floor board, calibration, control logic, operating sequence, phone app, obstacles, " +
              "claw electrical, gear strength, safety, acronyms, calculations and sources.");
}

// ================================================================================================ APPENDIX
section("Appendix");
{
  const sl = pres.addSlide({ masterName: "SECTION", sectionTitle: SECTION });
  sl.addText("Appendix", { x: M, y: 2.8, w: 11, h: 1.0, fontSize: 44, bold: true, color: "FFFFFF", fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addText("Supporting detail for questions", { x: M, y: 3.9, w: 11, h: 0.6, fontSize: 20, color: "D9DEE5", fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addNotes("");
}
{
  const sl = blank("Project Status");
  table(sl, ["Part", "Status", "Next test"], [
    ["Wall stations", "Built; bench-commissioned [[how many]]", "Three-station test, then the fourth"],
    ["Station electronics", "Built; drivers at 1.5 A [[how: Vref reading]]", "90-minute hold test at 1.5 A"],
    ["Heat fin", "Prototype 0.019 in built; 1/8 in designed", "Machine the 1/8 in fin; hold test"],
    ["Thermal model of the station", "Hand calculation at 1.5 A; SolidWorks model set up", "Run it; then the hold test"],
    ["Claw body: tube, mount, servo, gears", "Built", "Weigh it"],
    ["Claw hands, camera housing, encoder casing", "Checked in CAD; printing", "Fit checks on the first print"],
    ["Calibration and control software", "Simulated end to end", "First hardware run"],
    ["Winch pull", "Calculated at 1.5 A: 25–34 N", "Luggage-scale pull test"],
  ], M, 1.55, W - 2 * M, [0.32, 0.36, 0.32], { size: 13, rowH: 0.56 });
  sl.addNotes("Everything calculated or simulated is called that; the next-test column is what turns it into measurements.");
}

content("Fin Sizing for 4 W", [
  "Goal: the fin alone carries all 4.05 W",
  "0.019 in sheet cannot at any length; maximum about 2 W",
  "1/8 in plate needs 145–185 mm",
  "Thickness matters more than length",
], (sl, x, y, w, h) => {
  table(sl, ["Painted 6061, 44 mm wide", "Mass", "Motor at 200 mm, fin alone", "Shortest for ≤ 60 °C"], [
    ["0.019 in (prototype)", "14 g", "100–120 °C", "None (2.0 W max)"],
    ["1/16 in", "47 g", "66–72 °C", "None (3.6 W max)"],
    ["0.090 in", "68 g", "60–65 °C", "210 mm or none"],
    ["1/8 in (design)", "94 g", "56–59 °C", "145–185 mm"],
    ["3/16 in", "141 g", "53–55 °C", "125–140 mm"],
    ["1/4 in", "189 g", "51–52 °C", "115–125 mm"],
  ], x, y + 0.1, w, [0.3, 0.12, 0.28, 0.3], { size: 13, rowH: 0.5, name: "fin sizing" });
  caption(sl, "All 4.05 W through the fin, 23 °C room, paste contact. Calculated.", x, y + 0.1 + 7 * 0.5 + 0.12, w);
}, "The built sheet works today only because the motor also sheds about 2.5 W into the vented shell. A thin sheet has a large m = √(2h/kt), " +
"so its far end does almost nothing: the most heat any length can carry is w √(2hkt) θ_b, about 2 W for 0.019 in at a 60 °C base. The 1/8 in plate " +
"of my first drawing, painted, would carry all of it at the same 200 mm, and with the vented shell the motor would run at about 45 °C. Mass is no " +
"problem on a wall station. 1/8 in may be beyond a hand shear: bandsaw and square it on the mill. Ranges: flange at one temperature to heat spread over the patch.",
{ split: 0.4, eq: { title: "Most heat any fin length can carry", lines: [
  "q_{∞} = w √(2 h k t) × θ_b",
  "0.019 in: 0.044 × √(2 × 9.3 × 167 × 0.000483) × 37",
  "= **2.0 W** < 4.05 W",
], where: "w = 0.044 m fin width; h = 9.3 W/m²·K, painted; k = 167 W/m·K, 6061 aluminum; t = 0.000483 m; θ_b = 60 − 23 = 37 K" } });

content("Floor Board Accuracy", [
  "Position error equals angle error times camera height",
  "One tag in view: 6.6 mm; four tags: 0.7 mm",
  "Averaging removes noise, but not bias",
], { sheet: "floor_board", tab: "Floor board" },
"Two tags: 4.85 mrad, 2.5 mm. Noise model: 0.3 px corner noise, 520 px focal length (camera not yet calibrated).",
{ eq: { title: "Position error with one tag in view", lines: ["δx = σ_{θ} × L = 12.9 mrad × 0.51 m = **6.6 mm**"],
  where: "σ_{θ} = pose-angle noise with one tag in view; L = 0.51 m camera height above the board" } });

content("Startup Calibration", [
  "No tape measure needed",
  "Fits anchor positions and cable zero lengths",
  "Held-out poses check the fit",
  "Full room allowed only within the fit's error bars",
], (sl, x, y, w, h) => calFlow(sl, x, y + 0.3, w, 3.4),
"Safety comes from margins, not precision: 0.4 m below the anchors and 0.2 m inside the walls unless the error bars allow more. " +
"If the fit is not good enough: more poses, then fit again.",
{ eq: { title: "Least-squares calibration fit", lines: [
  "min Σ_k Σ_i ( L_{i0} + d_{ik} − ‖**a**_i − **p**_k‖ )²",
  "Full room only if k σ ≤ safety margin",
], where: "a_i = anchor i; p_k = claw pose k from the camera; d_ik = cable paid out, from the encoder; L_i0 = cable zero length; σ = fit error; k = confidence multiplier" } });

{
  const sl = blank("Control Logic: Generation 1 vs. Final");
  table(sl, ["", "Generation 1", "Final"], [
    ["Where is the claw?", "Assumed: where the cables were told to put it", "Measured: claw camera on the floor board, refit at every startup"],
    ["Room geometry", "Point mass; anchors from a tape measure", "Rigid claw; anchors and cable lengths fitted, with error bars"],
    ["Who runs the motors", "One central board steps all four", "Each station runs time-stamped moves; the laptop coordinates"],
    ["Finding laundry", "Ceiling camera, pixel to floor map", "Claw camera, ray from the claw's pose to the floor"],
    ["Did the grab work?", "Assumed once the claw closed", "Camera checks pickup and delivery"],
    ["Faults", "Emergency stop only", "Supervisor: a stop keeps torque; nothing restarts by itself"],
  ], M, 1.55, W - 2 * M, [0.2, 0.36, 0.44], { size: 14, rowH: 0.7 });
  sl.addNotes("Generation 1 trusted its model; the final logic measures before it trusts and checks after it acts. Kept from generation 1: the cable math, the " +
              "state-machine idea and the YOLO-World detector. All simulated so far.");
}

{
  const sl = blank("Operating Sequence");
  const cols = [["1. Start up", ["Self-check", "Take up slack", "Lift a few centimeters", "Calibrate", "Set the trust level"]],
                ["2. Find", ["Rise to scan height", "Detector lists the items", "Map each to the floor", "Choose the nearest"]],
                ["3. Pick and deliver", ["Hover until still", "Descend and close", "Camera confirms the grip", "Move to the hamper and release", "Camera confirms the drop"]],
                ["4. Put away", ["Lower over the floor board", "Camera confirms the floor", "Disarm after a typed confirmation"]]];
  const x = M, y = 1.55, w = W - 2 * M, gap = 0.32, cw = (w - 3 * gap) / 4, hh = 0.5, bodyH = 2.9;
  cols.forEach(([t, lines], i) => {
    const cx = x + i * (cw + gap);
    sl.addShape(pres.shapes.RECTANGLE, { x: cx, y, w: cw, h: hh, fill: { color: HEX.navy }, line: { color: HEX.navy }, objectName: `stage ${i + 1}` });
    label(sl, t, cx + 0.12, y, cw - 0.24, hh, { size: 15, bold: true, color: "FFFFFF" });
    sl.addShape(pres.shapes.RECTANGLE, { x: cx, y: y + hh, w: cw, h: bodyH, fill: { color: "FFFFFF" }, line: { color: HEX.navy, width: 1 } });
    const arr = lines.map((ln, j) => ({ text: ln, options: { bullet: { indent: 12 }, breakLine: j < lines.length - 1, paraSpaceAfter: 6 } }));
    sl.addText(arr, { x: cx + 0.08, y: y + hh + 0.1, w: cw - 0.16, h: bodyH - 0.2, fontSize: 15, color: HEX.ink, fontFace: "Arial", valign: "top",
                      margin: 0, isTextBox: true, objectName: `stage ${i + 1} steps` });
    if (i < 3) seg(sl, cx + cw + 0.04, y + hh / 2, cx + cw + gap - 0.04, y + hh / 2, { color: HEX.grey, width: 1.5, endArrowType: "triangle" });
  });
  bullets(sl, [
    "After each delivery the robot returns to step 2; three failures in a row pause it for the operator",
    "PAUSE or any fault stops every station at the same point on the path, still holding; nothing restarts by itself",
  ], x, y + hh + bodyH + 0.35, w, 1.3, 16, { space: 8, name: "sequence rules" });
  sl.addNotes("Grips wait until the claw stops swinging. A refused release pauses over the hamper. Disarm needs a typed confirmation and a fresh floor " +
              "check, because releasing torque drops a hanging claw. Simulated end to end.");
}

content("Phone App", [
  "Shows status, the live claw camera and guided setup",
  "Every motion asks for confirmation first",
  "PAUSE holds position immediately",
  "The switched power strip is the hard stop",
  "A reboot never resumes a task",
], { file: [P("docs/app_screenshots/01_home.png"), P("docs/app_screenshots/02_camera.png"), P("docs/app_screenshots/04_chat.png")],
     alt: "Phone app screens", caption: "Phone app: home, camera and chat screens" },
"Tested against a full simulator of the stations and the claw, so lost messages and reboots were exercised before hardware.", { split: 0.38 });

content("Obstacles", [
  "Known obstacles modeled as keep-out cylinders",
  "Every cable checked at every point of the path",
  "Moves that fail the check are refused before any motor turns",
  "People are not detected yet, so nobody stands underneath",
], (sl2, x, y, w, h) => {
  const Ld = 4.19, Hc = 2.74, za = 2.59, s = Math.min((w - 0.2) / Ld, (h - 1.0) / Hc);
  const ox = x + (w - Ld * s) / 2, oy = y + 0.15 + Hc * s;
  const X = d => ox + d * s, Y = z => oy - z * s;
  seg(sl2, X(0), Y(0), X(Ld), Y(0), { color: HEX.ink, width: 1.25 });
  seg(sl2, X(0), Y(Hc), X(Ld), Y(Hc), { color: HEX.rule, width: 1 });
  sl2.addShape(pres.shapes.RECTANGLE, { x: X(0.8), y: Y(1.9), w: 0.4 * s, h: 1.9 * s, fill: { color: HEX.pale }, line: { color: HEX.grey, width: 1 }, objectName: "shelf" });
  label(sl2, "Shelf,\n0–1.9 m", X(0.8) - 1.0, Y(1.2), 0.94, 0.5, { size: 11, color: HEX.mid, align: "right" });
  const ok = [2.1, 1.5], bad = [2.1, 0.8];
  [[ok, HEX.navy, "solid"], [bad, HEX.red, "dash"]].forEach(([p, c, d]) => {
    seg(sl2, X(0), Y(za), X(p[0]), Y(p[1]), { color: c, width: 2, dashType: d });
    seg(sl2, X(Ld), Y(za), X(p[0]), Y(p[1]), { color: c, width: 2, dashType: d });
    sl2.addShape(pres.shapes.RECTANGLE, { x: X(p[0]) - 0.09, y: Y(p[1]) - 0.09, w: 0.18, h: 0.18, fill: { color: c }, line: { color: c } });
  });
  label(sl2, "1.5 m: clear", X(ok[0]) - 0.75, Y(ok[1]) + 0.13, 1.5, 0.25, { size: 12, bold: true, color: HEX.navy, align: "center" });
  label(sl2, "0.8 m: refused", X(bad[0]) - 0.9, Y(bad[1]) + 0.13, 1.8, 0.25, { size: 12, bold: true, color: HEX.red, align: "center" });
  caption(sl2, "Side view along a room diagonal: the same floor point at two heights, with an example shelf", x, y + h - 0.55, w);
}, "Next: draw keep-out shapes in the phone app (squares, rectangles, circles with a height), then let the robot build its own room model from the " +
"claw camera's scans. Simulated so far.", { split: 0.46, size: 19 });

content("Claw Electrical", [
  "Two-cell lithium-ion pack: 7.4 V with a 5 A fuse",
  "6 V servo rail and a separate 5 V logic rail",
  "Peak draw of 2.8–3.1 A against a 3 A pack rating",
  "Charged with the switch off, attended, at 1 A or less",
], { file: R("kicad_claw_revB.png"), alt: "Claw schematic" }, "Rules check 0 errors; 9 nets match the specification. Charger: 8.4 V constant current, constant voltage.", { split: 0.42 });

content("Gear Strength", [
  "Module 1.5 gears; PETG allowable stress 22.5 MPa",
  "Safety factors at 6 V stall: 2.05 pinion, 2.50 compound gear, 2.00 sync gear",
  "Module 1 gave safety factors of 0.35–0.41 and was rejected",
], { file: [R("v6r_compound.png"), R("v6r_follower.png")], alt: "Compound and follower gears" },
"Safety factors at the 6 V servo stall: pinion 2.05, 36-tooth gear 2.50, sync gear 2.00 with one jaw taking all the load. Stall torque 1.078 N·m is the servo rating, not measured.",
{ eq: { title: "Lewis bending stress at servo stall", lines: [
  "F_t = 2τ / d = 2 × 1.078 / 0.027 = 79.9 N",
  "σ = F_t / (b m Y) = 79.9 / (15.7 × 1.5 × 0.309) = 11.0 MPa",
  "SF = σ_{allow} / σ = 22.5 / 11.0 = **2.05**",
], where: "τ = servo stall torque; d = pitch diameter (18 teeth × 1.5 mm); b = face width; m = module; Y = Lewis form factor; SF = safety factor" } });

content("Safety", [
  "One hard stop: the switched power strip",
  "Faults and PAUSE hold motor torque",
  "Anchors in wall studs; nobody stands under the robot",
  "Motors are never unplugged under power",
], { file: R("station_1021_final.png"), alt: "Wall station" }, "No safety-rated function is claimed.", { split: 0.55 });

{
  const sl = blank("Acronyms");
  table(sl, ["Term", "Meaning"], [
    ["CAD", "Computer-aided design"],
    ["PETG", "Polyethylene terephthalate glycol (the printed plastic)"],
    ["TPU", "Thermoplastic polyurethane (flexible printed plastic)"],
    ["NEMA 17", "National Electrical Manufacturers Association motor frame, 1.7 in square"],
    ["I²C", "Inter-Integrated Circuit: a short-range two-wire sensor bus"],
    ["ESP32", "A Wi-Fi microcontroller family (Espressif)"],
    ["A4988, AS5600", "Stepper-motor driver chip (Allegro); magnetic angle sensor (ams)"],
    ["YOLO", "“You Only Look Once”: an object-detection model family"],
    ["SF", "Safety factor: allowable stress divided by actual stress"],
  ], M, 1.55, W - 2 * M, [0.22, 0.78], { size: 14, rowH: 0.5 });
  sl.addNotes("");
}

{
  const sl = content("Calculations and Sources", [
    "All charts come from my engineering calculation sheet",
    "Each result is a formula on labeled inputs",
    "Sources:",
    "- Incropera et al., Fundamentals of Heat and Mass Transfer, ch. 3",
    "- Allegro MicroSystems, A4988 datasheet",
  ], { sheet: "cable_tension", tab: "Cable tension" }, "", { split: 0.5 });
  sl.addText([{ text: "RoomCleaner engineering calculations (Google Sheets)", options: { hyperlink: { url: SHEET_URL, tooltip: "Open the calculation sheet" } } }],
             { x: M, y: 6.3, w: 5.5, h: 0.4, fontSize: 15, color: HEX.navy, fontFace: "Arial", margin: 0, isTextBox: true, objectName: "sheet link" });
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
