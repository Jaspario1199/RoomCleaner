// RoomCleaner deck v9 (Oct 26): the build, in the order it happened. A chronological build story for a 20-30 minute class or
// design-review audience, heavier on the October photos (29-40). Started from deck_v8/build_deck_v8.js: same theme, helpers,
// equation boxes, footer; evidence pills added (style guide section 4); five "acts" in the footer instead of phases.
// Content contract: docs/presentation/DECK_V9_NOTES.md. Every number is v8's or comes from the cited record file. v1-v8 unchanged.
//
//   NODE_PATH=<pptxgenjs node_modules> APPLY_THEME=<pptx skill>/scripts/apply_theme.js \
//   SOFFICE_PY=<pptx skill>/scripts/office/soffice.py node docs/presentation/deck_v9/build_deck_v9.js
//   PART=appendix ... builds the appendix file (divider plus the v8 appendix, the fits table and the schematics).
//
// [[text]] in any string is a fact still to fill in: it renders red and bracketed so it cannot be missed.
"use strict";
const path = require("path");
const { execFileSync } = require("child_process");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const P = (...p) => path.join(ROOT, ...p);
const PART = process.env.PART === "appendix" ? "appendix" : "main";
const OUT = path.join(__dirname, PART === "main" ? "RoomCleaner_Buntinx_v9.pptx" : "RoomCleaner_Buntinx_v9_appendix.pptx");
const FIGDIR = path.join(__dirname, "..", "deck_v3", "fig");
const SHEETFIG = path.join(__dirname, "..", "deck_v8", "fig");   // Sheet charts with the weighed claw (0.60 kg with battery), Oct 22
const V8FIG = SHEETFIG;                                            // part snapshots (make_mfg_snapshots.py)
const { size: imgSize } = require("../deck_v2/img_size.js");

const THEME = {
  name: "RoomCleaner v9", headFontFace: "Arial", bodyFontFace: "Arial",
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
const W = 13.333, H = 7.5, M = 0.6;

pres.defineSlideMaster({
  title: "CONTENT", background: { color: "FFFFFF" },
  objects: [],
  slideNumber: { x: W - M - 0.6, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: HEX.grey, align: "right", fontFace: "Arial" },
});
pres.defineSlideMaster({ title: "SECTION", background: { color: HEX.navy } });
pres.defineSlideMaster({ title: "TITLE", background: { color: "FFFFFF" } });

// ------------------------------------------------------------------------------------------------ helpers (from v8)
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
    const t = (sub ? it.slice(2) : it).replace(/(\d) (?=[A-Za-z°%Ω])/g, "$1 ");   // keep a number on the same line as its unit
    const base = { fontSize: sub ? size - 2 : size, color: sub ? HEX.mid : HEX.ink, fontFace: "Arial" };
    const mark = o.numbered && !sub ? { type: "number", indent: 26 } : { indent: sub ? 18 : 20 };
    const para = { bullet: mark, indentLevel: sub ? 1 : 0, paraSpaceAfter: sub ? 6 : (o.space || 14) };
    const rs = runs(t, { ...base, ...para, align: "left" });
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

// Evidence pills (style guide section 4). MEASURED solid, CALCULATED and CAD outlined, SIMULATED dashed, PLANNED fog.
const TAGS = {
  MEASURED:   { fill: { color: HEX.navy }, line: { color: HEX.navy, width: 1 }, color: "FFFFFF" },
  CALCULATED: { fill: { color: "FFFFFF" }, line: { color: HEX.navy, width: 1 }, color: HEX.navy },
  CAD:        { fill: { color: "FFFFFF" }, line: { color: HEX.navy, width: 1 }, color: HEX.navy },
  SIMULATED:  { fill: { color: "FFFFFF" }, line: { color: HEX.grey, width: 1, dashType: "dash" }, color: HEX.grey },
  PLANNED:    { fill: { color: HEX.light }, line: { color: HEX.light, width: 1 }, color: HEX.grey },
};
const TAG_W = 1.35, TAG_G = 0.12;
function tag(sl, kind, i = 0) {
  const s = TAGS[kind];
  const x = W - M - TAG_W - i * (TAG_W + TAG_G);
  sl.addText(kind, { shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.14, x, y: 0.58, w: TAG_W, h: 0.28,
                     fill: { ...s.fill }, line: { ...s.line }, color: s.color, fontSize: 9, bold: true, fontFace: "Arial", charSpacing: 1.2,
                     align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: `tag ${kind}` });
}

// Slide frame: a claim title (up to two lines), evidence pills top right, the act in the footer.
let SECTION = "Introduction", ACT = "";
function section(name) { SECTION = name; pres.addSection({ title: name }); }
function blank(title, tags = []) {
  const sl = pres.addSlide({ masterName: "CONTENT", sectionTitle: SECTION });
  const tw = W - 2 * M - (tags.length ? tags.length * (TAG_W + TAG_G) + 0.2 : 0);
  sl.addText(title, { x: M, y: 0.3, w: tw, h: 0.85, fontSize: 24, bold: true, color: HEX.ink, fontFace: "Arial",
                      margin: 0, valign: "middle", isTextBox: true, objectName: "title" });
  tags.forEach((t, i) => tag(sl, t, tags.length - 1 - i));
  sl.addText(`Jasper Buntinx  |  RoomCleaner${ACT ? "  |  " + ACT : ""}`, { x: M, y: 7.0, w: 9, h: 0.3, fontSize: 10, color: HEX.grey, fontFace: "Arial",
                                                                            margin: 0, isTextBox: true, objectName: "footer" });
  return sl;
}
// Standard slide: the figure left, two to four statements right, an equation box under them if given.
function content(title, items, visual, notes, opts = {}) {
  const sl = blank(title, opts.tags || []);
  const fw = opts.figW || 7.0, fx = M, fy = 1.3, fh = 5.45;
  const bx = fx + fw + 0.45, bw = W - M - bx, by = 1.35, bottom = 6.75;
  const eqH = opts.eq ? eqHeight(opts.eq) : 0;
  figure(sl, visual, fx, fy, fw, fh);
  bullets(sl, items, bx, by, bw, (opts.eq ? bottom - eqH - 0.2 : bottom) - by, opts.size || 17, { numbered: opts.numbered, space: opts.space || 12 });
  if (opts.eq) eqBox(sl, opts.eq, bx, bottom - eqH, bw);
  sl.addNotes(notes || "");
  return sl;
}
// Photo layouts inside a box: 1 or 2 photos in a row; 3 = one tall left plus two stacked right; 4 = 2 x 2.
// Each entry is [file, caption]. Numbered captions under each photo; portrait photos keep their aspect (fitImage).
// Returns the width actually used, so the statements can start right after the photos.
function photos(sl, list, x, y, w, h, o = {}) {
  const g = 0.12, capH = o.caps === false ? 0 : 0.3;
  const ar = list.map(([f]) => { const d = imgSize(f); return d.w / d.h; });
  const place = (f, cap, px, py, pw, ph, n, capW) => {
    const r = fitImage(sl, f, px, py, pw, ph - capH, cap, { alignTop: true, alignLeft: true });
    if (capH) caption(sl, `${n}  ${cap}`, r.x, r.y + r.h + 0.05, capW || Math.max(r.w, 1.8));
    return r;
  };
  const n = list.length;
  if (n <= 2) {
    const ph = h - capH, natural = ar.reduce((a, b) => a + b, 0) * ph + g * (n - 1);
    const s = Math.min(1, w / natural);
    let cx = x;
    list.forEach(([f, cap], i) => { const pw = ar[i] * ph * s; place(f, cap, cx, y, pw, (ph * s) + capH, i + 1, pw + 0.3); cx += pw + g; });
    return natural * s;
  }
  if (n === 3) {
    const bigW = Math.min(w * 0.6, (h - capH) * ar[0]);
    place(list[0][0], list[0][1], x, y, bigW, h, 1, bigW + 0.3);
    const sh = (h - g) / 2, sx = x + bigW + g;
    const sw = Math.max((sh - capH) * ar[1], (sh - capH) * ar[2]);
    place(list[1][0], list[1][1], sx, y, sw, sh, 2, sw + 0.6);
    place(list[2][0], list[2][1], sx, y + sh + g, sw, sh, 3, sw + 0.6);
    return bigW + g + sw;
  }
  const cw = (w - g) / 2, ch = (h - g) / 2;
  list.forEach(([f, cap], i) => place(f, cap, x + (i % 2) * (cw + g), y + Math.floor(i / 2) * (ch + g), cw, ch, i + 1));
  return w;
}
// Photo slide: photos left (up to 7.4 in wide), statements right starting where the photos end, optional equation box.
function photoSlide(title, items, list, notes, opts = {}) {
  const sl = blank(title, opts.tags || []);
  const fw = opts.figW || 7.4, fx = M, fy = 1.3, fh = 5.45;
  const used = photos(sl, list, fx, fy, fw, fh, opts);
  const bx = fx + used + 0.45, bw = W - M - bx, by = 1.35, bottom = 6.75;
  const eqH = opts.eq ? eqHeight(opts.eq) : 0;
  bullets(sl, items, bx, by, bw, (opts.eq ? bottom - eqH - 0.2 : bottom) - by, opts.size || 17, { space: opts.space || 12 });
  if (opts.eq) eqBox(sl, opts.eq, bx, bottom - eqH, bw);
  sl.addNotes(notes || "");
  return sl;
}
// Divider: act number, name, dates and the act's one-line claim (dark slide, style guide archetype B).
function divider(n, name, dates, goal, notes) {
  section(name);
  const sl = pres.addSlide({ masterName: "SECTION", sectionTitle: name });
  sl.addText(`Act ${n}`, { x: M, y: 2.2, w: 11, h: 0.45, fontSize: 20, color: HEX.pale, fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addText(name, { x: M, y: 2.7, w: 11, h: 0.95, fontSize: 44, bold: true, color: "FFFFFF", fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addText(dates, { x: M, y: 3.7, w: 11, h: 0.45, fontSize: 20, color: HEX.pale, fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addText(goal, { x: M, y: 4.55, w: 11, h: 0.5, fontSize: 20, color: "FFFFFF", fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addNotes(notes || "");
}

// ------------------------------------------------------------------------------------------------ native figures (from v8)
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
function gantt(sl, rows, x, y, w, marks = []) {
  const lw = 2.6, dw = 1.75, cx = x + lw + dw, cw = x + w - cx, hh = 0.4, rh = 0.46;
  const months = [["July", 31], ["August", 31], ["September", 30], ["October", 31]];
  const s = cw / months.reduce((a, [, n]) => a + n, 0), bottom = y + hh + rows.length * rh;
  sl.addShape(pres.shapes.RECTANGLE, { x, y, w, h: hh, fill: { color: HEX.navy }, line: { color: HEX.navy }, objectName: "gantt header" });
  label(sl, "Act", x + 0.1, y, lw - 0.2, hh, { size: 13, bold: true, color: "FFFFFF" });
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
// Option cards (style guide archetype D): title, "Chosen because" and "What it cost later" lines; fog cards, no chosen tint.
function cards(sl, list, x, y, w, h) {
  const g = 0.25, cw = (w - g * (list.length - 1)) / list.length;
  list.forEach((c, i) => {
    const cx = x + i * (cw + g);
    sl.addShape(pres.shapes.RECTANGLE, { x: cx, y, w: cw, h, fill: { color: HEX.light }, line: { color: HEX.light }, objectName: `card ${c.title}` });
    label(sl, c.eyebrow, cx + 0.25, y + 0.2, cw - 0.5, 0.25, { size: 10, bold: true, color: HEX.grey, name: "card eyebrow" });
    label(sl, c.title, cx + 0.25, y + 0.45, cw - 0.5, 0.75, { size: 19, bold: true, color: HEX.navy, valign: "top", name: "card title" });
    label(sl, "CHOSEN BECAUSE", cx + 0.25, y + 1.3, cw - 0.5, 0.25, { size: 10, bold: true, color: HEX.grey, name: "card label" });
    bullets(sl, c.why, cx + 0.25, y + 1.55, cw - 0.5, 1.75, 15, { space: 6, name: "card why" });
    label(sl, "WHAT IT COST LATER", cx + 0.25, y + 3.35, cw - 0.5, 0.25, { size: 10, bold: true, color: HEX.red, name: "card label" });
    bullets(sl, c.cost, cx + 0.25, y + 3.6, cw - 0.5, h - 3.7, 15, { space: 6, name: "card cost" });
  });
}

const R = f => P("docs/presentation/deck_assets/renders", f);
const PH = f => P("docs/presentation/photos", f);
const FG = f => path.join(FIGDIR, f);
const SC = f => P("docs/presentation/deck_assets/screens", f);   // Jasper's SolidWorks screenshots (Oct 22)
const GR = f => P("renders/winch_gear3", f);                       // winch gear stage renders (D40-D43)

// Room elevation to scale, along the 3.35 m wall: walls, ceiling, anchors, the planner's margins, the claw, a hamper (v8).
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

// Three-station room, top view to scale (docs/THREE_STATION_MODE.md section 2): room 3.35 x 2.74 m, A (0.05, 0.05),
// B (3.30, 0.05), C (1.68, 2.69), the D corner empty, the triangle A-B-C and the start point (1.68, 0.93), its centroid.
function threeStationPlan(sl, x, y, w, h) {
  const Wm = 3.35, Hm = 2.74;
  const s = Math.min((w - 1.2) / Wm, (h - 1.35) / Hm);
  const ox = x + 0.6 + (w - 1.2 - Wm * s) / 2, oy = y + 0.45 + Hm * s;
  const X = m => ox + m * s, Y = m => oy - m * s;                 // y runs up the slide (toward the far wall)
  const A = [0.05, 0.05], B = [3.30, 0.05], C = [1.68, 2.69], S = [1.68, 0.93], D = [0.05, 2.69];
  // triangle fill, then walls
  const tri = [A, B, C].map(([px, py]) => [X(px), Y(py)]);
  sl.addShape(pres.shapes.CUSTOM_GEOMETRY, { x: 0, y: 0, w: W, h: H, fill: { color: "F6E3E1" }, line: { color: "F6E3E1", width: 0.5 },
                                             points: [{ x: tri[0][0], y: tri[0][1] }, { x: tri[1][0], y: tri[1][1] }, { x: tri[2][0], y: tri[2][1] }, { x: tri[0][0], y: tri[0][1], close: true }],
                                             objectName: "triangle A B C" });
  sl.addShape(pres.shapes.RECTANGLE, { x: X(0), y: Y(Hm), w: Wm * s, h: Hm * s, fill: { type: "none" }, line: { color: HEX.ink, width: 1.5 }, objectName: "room walls" });
  [[A, B], [B, C], [C, A]].forEach(([p, q]) => seg(sl, X(p[0]), Y(p[1]), X(q[0]), Y(q[1]), { color: HEX.navy, width: 2 }));
  const dot = (p, name, fill) => sl.addShape(pres.shapes.OVAL, { x: X(p[0]) - 0.11, y: Y(p[1]) - 0.11, w: 0.22, h: 0.22, fill: { color: fill }, line: { color: fill }, objectName: name });
  dot(A, "station A", HEX.navy); dot(B, "station B", HEX.navy); dot(C, "station C", HEX.navy);
  sl.addShape(pres.shapes.OVAL, { x: X(D[0]) - 0.11, y: Y(D[1]) - 0.11, w: 0.22, h: 0.22, fill: { color: "FFFFFF" }, line: { color: HEX.grey, width: 1, dashType: "dash" }, objectName: "corner D, empty" });
  sl.addShape(pres.shapes.OVAL, { x: X(S[0]) - 0.09, y: Y(S[1]) - 0.09, w: 0.18, h: 0.18, fill: { color: HEX.red }, line: { color: HEX.red }, objectName: "start point" });
  label(sl, "A (0.05, 0.05)", X(A[0]) - 0.1, Y(A[1]) + 0.12, 1.6, 0.26, { size: 11, bold: true, color: HEX.navy });
  label(sl, "B (3.30, 0.05)", X(B[0]) - 1.5, Y(B[1]) + 0.12, 1.6, 0.26, { size: 11, bold: true, color: HEX.navy, align: "right" });
  label(sl, "C (1.68, 2.69), mid-wall", X(C[0]) - 1.2, Y(C[1]) - 0.4, 2.4, 0.26, { size: 11, bold: true, color: HEX.navy, align: "center" });
  label(sl, "D: not mounted", X(D[0]) - 0.1, Y(D[1]) - 0.4, 1.6, 0.26, { size: 11, color: HEX.grey });
  label(sl, "Start (1.68, 0.93), the centroid", X(S[0]) - 1.3, Y(S[1]) + 0.12, 2.6, 0.26, { size: 11, bold: true, color: HEX.red, align: "center" });
  label(sl, "3.25 m", X((A[0] + B[0]) / 2) - 0.5, Y(A[1]) - 0.3, 1.0, 0.24, { size: 10, color: HEX.navy2, align: "center" });
  label(sl, "3.10 m", X((A[0] + C[0]) / 2) - 0.95, Y((A[1] + C[1]) / 2) - 0.12, 0.8, 0.24, { size: 10, color: HEX.navy2, align: "right" });
  label(sl, "3.10 m", X((B[0] + C[0]) / 2) + 0.15, Y((B[1] + C[1]) / 2) - 0.12, 0.8, 0.24, { size: 10, color: HEX.navy2 });
  label(sl, "3.35 m (11 ft) wall", X(Wm / 2) - 0.9, Y(0) + 0.12, 1.8, 0.26, { size: 11, align: "center", color: HEX.mid });
  label(sl, "2.74 m\n(9 ft)", x, Y(Hm / 2) - 0.3, 0.55, 0.6, { size: 11, align: "right", color: HEX.mid });
  caption(sl, "Top view to scale; anchors at one height, 2.59 m; shaded: where three cables hold the claw", x, y + h - 0.3, w);
}

if (PART === "main") {
// ================================================================================================ OPENING
section("Introduction");
{
  // 1. Title: claim, name, school, dates; photo 38 (the assembled claw, 10/26) full-bleed on the right.
  const sl = pres.addSlide({ masterName: "SECTION", sectionTitle: SECTION });
  const d = imgSize(PH("42_claw_hanging_three_cables_room_corner.jpg")), pw = H * d.w / d.h;
  sl.addImage({ path: PH("42_claw_hanging_three_cables_room_corner.jpg"), x: W - pw, y: 0, w: pw, h: H, altText: "The claw hanging from three cables in the room corner, Oct 27", objectName: "title photo" });
  const tw = W - pw - M - 0.4;
  sl.addText("RoomCleaner", { x: M, y: 1.5, w: tw, h: 0.9, fontSize: 44, bold: true, color: "FFFFFF", fontFace: "Arial", margin: 0, isTextBox: true, objectName: "title" });
  sl.addText("A four-cable ceiling robot that picks laundry off the floor", { x: M, y: 2.45, w: tw, h: 1.3, fontSize: 26, color: HEX.pale, fontFace: "Arial", margin: 0, isTextBox: true, objectName: "subtitle" });
  sl.addText("Jasper Buntinx", { x: M, y: 4.5, w: tw, h: 0.5, fontSize: 24, bold: true, color: "FFFFFF", fontFace: "Arial", margin: 0, isTextBox: true, objectName: "name" });
  sl.addText("Mechanical Engineering, Texas A&M University", { x: M, y: 5.0, w: tw, h: 0.45, fontSize: 18, color: HEX.pale, fontFace: "Arial", margin: 0, isTextBox: true, objectName: "school" });
  sl.addText("Built July to October 2026", { x: M, y: 5.5, w: tw, h: 0.45, fontSize: 18, color: HEX.pale, fontFace: "Arial", margin: 0, isTextBox: true, objectName: "dates" });
  sl.addNotes("Pitch (30 s): I'm building a cable-driven parallel robot that picks laundry off my floor. Three or four winches on the walls, each a " +
              "self-contained module with a stepper, a spool encoder and an ESP32, driving a battery-powered claw on the cables; the photo is the claw hanging " +
              "from the first three stations in my room yesterday. The hardest problem was safety: four cables can pull against each other hard enough to rip a " +
              "mount out of the wall. So the drive is designed to slip at a set tension, 34 to 59 N, well below what the mount can hold, and the spool encoder " +
              "sees the spool fall behind the commanded steps and stops the system. It is in bench testing: both station boards and the claw electronics pass, " +
              "and the first station is on the wall. The talk goes through the build in the order it happened. Every number carries a tag: measured, " +
              "calculated, simulated or planned. If asked: it has not picked up a garment yet; the first three-station lift is the next milestone; the slip " +
              "tension is calculated from the motor's holding torque, not yet measured.");
}

{
  // 2. About me: Jasper's three collage columns (unchanged from v8).
  const sl = blank("About me");
  const cols = ["about_outdoors.png", "about_engineering.png", "about_community.png"];
  const g = 0.2, top = 1.25, maxH = 6.85 - top, ar = cols.map(f => { const d = imgSize(PH(`about_me/${f}`)); return d.w / d.h; });
  const ih = Math.min(maxH, (W - 2 * M - 2 * g) / ar.reduce((a, b) => a + b, 0));
  let cx = M + (W - 2 * M - 2 * g - ih * ar.reduce((a, b) => a + b, 0)) / 2;
  cols.forEach((f, i) => {
    const iw = ih * ar[i];
    sl.addImage({ path: PH(`about_me/${f}`), x: cx, y: top, w: iw, h: ih, altText: f.replace(/about_|\.png/g, ""), objectName: f });
    cx += iw + g;
  });
  sl.addNotes("Talk track (45 s): the photos carry it, left to right. Mechanical Engineering at Texas A&M, class of 2027. " +
              "Left: outdoors and endurance, an Ironman 70.3 in 6:53 and a marathon in 2025; I finish long things. " +
              "Middle: EcoFil, a filament recycler I built with a shredder, dryer and extruder [[one EcoFil number: diameter tolerance or throughput, and what broke]]. " +
              "Right: as Special Events Build Logistics Chair for the One Army Gladiator Dash I headed assembly, repairs and transport of the obstacles; " +
              "the event raised $185K for Still Creek Ranch. If asked: metal sculpture for the Austin Creek Show, with fiber laser cutting and welding.");
}

content("The goal: jeans from anywhere on the floor into the hamper, nobody touching it", [
  "Pick up laundry in a 3.35 × 2.74 m (11 × 9 ft) room under a 2.74 m (9 ft) ceiling; design load 0.9 kg (jeans) plus a 2 m/s² dynamic allowance",
  "Four winches screwed into the studs near the ceiling corners, one claw on four cables, nothing on the floor",
  "PAUSE holds position with torque on; the switched power strip is the emergency stop, and it drops the claw",
  "Success: one garment from floor to hamper with no human touch; I approve each move on the phone",
], (sl, x, y, w, h) => roomSketch(sl, x, y, w, h),
"Talk track (50 s): The problem in one picture. Four anchors 0.15 m below the ceiling, one claw, a hamper. The shaded bands are the margins the planner keeps: " +
"0.2 m from the walls, 0.4 m below the anchors. The load case is a pair of jeans, 0.9 kg, with a 2 m/s² allowance for stops and snags. The safe state is PAUSE: " +
"every station holds with torque on. The emergency stop is the power strip, and because steppers hold only while powered, it drops the claw; nobody stands under " +
"the robot. Success means one garment from floor to hamper with no human touch; I approve each move on the phone. " +
"If asked: 0.9 kg is a screening value, not weighed. Top speed is 50 mm/s, so a diagonal move takes about a minute and a half. Where it stands today: the " +
"stations, their electronics and the claw are built and bench-tested; nothing has picked up a garment yet.",
{ size: 16, space: 10 });

{
  // 4. Timeline and authorship (v8 Gantt; dates per the outline).
  const sl = blank("Five phases in fifteen weeks");
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
    "Self-imposed limits: a hobby budget (about $640 spent, $220–260 of it in the robot), a 450 g claw, 60 °C for loaded printed parts, and a build week that ends on presentation day",
  ], M, gy + 0.6, W - 2 * M, 6.8 - gy - 0.6, 16, { space: 7, name: "scope" });
  sl.addNotes("Talk track (45 s): About fifteen weeks, alone, in five acts: concept in July, a first generation in August, the redesign through September, the " +
              "final design in the first three weeks of October, and the build and test week that ends on presentation day. The three red marks are the failures that " +
              "shaped the design, and each gets its own slide. Scope: the requirements, the decisions, the SolidWorks parts, the printing, machining, wiring and bring-up " +
              "are mine. I dictated the control logic and had Claude Code build it out; it also wrote the calculation scripts and checked my CAD, and I can take you " +
              "through any number on these slides. The motors, drivers, boards, servo, camera, battery and encoders are bought. " +
              "If asked about self-imposed limits and how they shaped the design: four. Money: a hobby budget; the cost breakdown puts everything ordered at about " +
              "$640, of which $220 (three stations) to $260 (four) is in the robot as parts and another $40 to $50 as filament, the rest pack remainders, spares and " +
              "two tools (prices partly recorded, partly typical; say 'about'). Time: fifteen weeks ending on the presentation date. Mass: a 450 g claw, because " +
              "every gram on the claw is a gram of payload. Heat: 60 °C for any loaded printed part. Those limits picked the hardware: NEMA 17 steppers at $33 for " +
              "five instead of self-locking worm-gear motors at $32 each; an A4988 kit chosen by what was in stock; printed parts everywhere except the pulleys; a " +
              "prototype fin cut from sheet already on hand; and a 1 lb test weight before any jeans. " +
              "If asked: the garment detector is YOLO-World, an open-source model. [[hours spent, shop access or mentors; was a dollar ceiling set in advance?]]");
}

// ================================================================================================ ACT 1: CONCEPT
section("Concept"); ACT = "Act 1 of 5: Concept (July)";
{
  const sl = blank("Why a cable robot: four winches cover the whole floor with nothing in the room");
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
  sl.addNotes("Talk track (45 s): Three ways to reach a floor. A floor robot fights the clutter it is meant to clear. A gantry puts a frame across my room. A cable " +
              "robot reaches the whole floor with a 0.6 kg moving mass and nothing on the floor; the room is the frame. So: four ceiling winches and one claw. The " +
              "price is in the geometry: a cable can only pull, so the tension split sets where the claw can go, and that is the next slide. " +
              "If asked: four cables on three position axes is redundant, so the tension split depends on cable-length errors; that is why the planner checks tensions " +
              "and the calibration fits the cable lengths.");
}

content("The first physics: cable tension climbs toward the ceiling", [
  "Weighed claw plus 1 lb, centred 0.4 m below the anchors: 14.3 N static, 17.2 N at 2 m/s²",
  "That is at the 16.8 N winch limit; with jeans the claw must stay at least 0.6 m below the anchors",
  "The planner checks every cable at every path point against the measured pull limit",
], { sheet: "cable_tension", tab: "Cable tension" },
"Talk track (50 s): The first calculation I ran, redone here with the claw as weighed. Tension per cable is the weight over four times the sine of the cable angle, " +
"so the shallower the cable, the more it carries. Centred 0.4 m below the anchors with the 1 lb test weight, each cable sees 14.3 N static and 17.2 N with the " +
"2 m/s² allowance, which is right at the 16.8 N design limit of a winch. With jeans the claw has to stay 0.6 m down. The planner does this check on every cable " +
"at every point of a path, against the pull limit that the pull test will measure. " +
"If asked: off-centre is worse than centred; the claw rises only to scan the floor from above, empty. The 1.5 divisor in the winch limit is the margin against skipped steps. " +
"If asked what a layout offset to a corner of the room does: cables only pull, so the claw can only hang where the horizontal pulls cancel, which means its floor " +
"position has to stay inside the polygon under the anchors. A layout pushed into one corner does not make the rest of the room harder, it makes it unreachable, and " +
"the floor it does cover shrinks by a tension-floor margin at each edge. Near an edge the far cable goes slack and the near ones run flat: the largest tension per " +
"unit of weight climbs from 1.10 at task height to 2.42 at the 0.4 m ceiling line, worst in the middle of a long wall. The three-station layout is the worked " +
"example: anchors in two corners and one mid-wall span a triangle of 47 % of the floor, and after a 0.23 to 0.31 m edge margin only 20 to 27 % is usable, with the " +
"start point 0.44 m off the room centre. So: anchors in the corners, as high and as symmetric as the studs allow. All calculated; nothing measured on the rig.",
{ tags: ["CALCULATED"], eq: { title: "Tension per cable, 1 lb test at 0.4 m", lines: [
  "T = m (g + a) / (4 sin φ)",
  "= 1.054 × 11.81 / (4 × 0.181) = **17.2 N**",
  "Winch limit: **16.8 N**",
] } });

{
  const sl = blank("July's choices, and what each one cost later");
  cards(sl, [
    { eyebrow: "WINCH MOTOR", title: "NEMA 17 steppers",
      why: ["Cheap, and one shield drives all four", "Holds position without a feedback loop"],
      cost: ["No brake: it holds only while powered, so a power loss drops the claw", "Runs hot: holding current is heat, 4.05 W per motor at 1.5 A"] },
    { eyebrow: "GRIPPER", title: "Five tendon fingers",
      why: ["Gathers crumpled cloth with one servo", "Printable in flexible TPU"],
      cost: ["Designed in CAD only, 419 g of a 450 g budget, never built", "Replaced by a clamp, then by the geared four-bar (Act 3)"] },
    { eyebrow: "EMERGENCY STOP", title: "The power strip",
      why: ["A guaranteed stop with no extra part", "The only stop that cannot be overridden by software"],
      cost: ["Cutting power drops the claw", "Nobody stands under the robot; a brake is on the next-steps list"] },
  ], M, 1.3, W - 2 * M, 5.4);
  sl.addNotes("Talk track (55 s): Three July choices that each came back later. Steppers: cheap, one shield drives four, and they hold position without a loop. " +
              "The cost: no brake, so they hold only while powered, and holding current is heat, which becomes the thermal story in Act 4. The gripper: five tendon " +
              "fingers in flexible TPU, pulled by one servo, meant to gather crumpled cloth. It stayed in CAD at 419 g of a 450 g budget and was never built. The " +
              "emergency stop: the switched power strip, the one stop software cannot override; the cost is that it drops the claw, so the rule is nobody under the " +
              "robot. If asked: a worm-gear DC motor would self-lock and hold with zero current, at about $32 each and with a control loop per motor; I chose the " +
              "stepper for cost and simplicity and accepted the drop. " +
              "If asked for the idea behind each trade (the v8 trade-off table). Why heat matters: pull rises with current but coil heat with current squared, " +
              "P = I²R, 2.0 W at 1.06 A and 4.05 W at 1.5 A with the assumed 1.8 Ω phase; the motor is bolted to a printed PETG tab that carries the whole cable " +
              "load, PETG conducts about 1/800 as well as aluminium, so the tab climbs toward motor temperature, and above about 60 °C loaded PETG creeps, the " +
              "motor loosens, the anchor drifts, and anchor error is claw error about one to one. What failure the stronger claw was built for: the gear teeth at " +
              "servo stall. A clamp stops when the servo stalls, so every grip loads the teeth with full stall torque; module 1 with a 6 mm face gave a Lewis safety " +
              "factor of 0.35 at 6 V, the built module 1.5 with 16 and 20 mm faces gives 2.05 on the pinion, against a PETG allowable of half its tensile strength; " +
              "the cost was mass, 0.60 kg against 0.45. How longer wires raise the drop: the longest 12 V branch is 32 ft one way, 64 ft of loop; drop is I × ρ × 2L / A, " +
              "0.82 V on 18 AWG and 0.51 V on 16 AWG at 2 A (illustrative), 7 % against 4 % of 12 V, more when the wire runs warm near the ceiling, so 16 AWG " +
              "went in. How to read the safety margins: three kinds. The 1.5 on the winch pull is a skip margin, running pull divided by 1.5 so a snag does not " +
              "skip steps. The 1.5 in the weakest-link table is the ratio of the tension at which a part gives to the most the motor can pull before it slips, 59 N: " +
              "at or above 1.5 the motor gives first, 1.0 to 1.5 is marginal, below 1.0 the part fails before the motor. Gear and structural SFs are allowable " +
              "stress over calculated stress with printed PETG allowed half its tensile strength and a further 15 % off when warm. All calculated against assumed " +
              "allowables; none is a tested margin.");
}

// ================================================================================================ ACT 2: GENERATION 1
section("Generation 1"); ACT = "Act 2 of 5: Generation 1 (August)";
photoSlide("Generation 1: one Uno, one shield, four corner mounts", [
  "A printed corner plate screwed into a joist replaced hanging hooks: a hook is a pivot, and about 1:1 of anchor error becomes claw position error",
  "One Uno and one CNC shield drove all four motors from one board",
  "Bench: the station lifted a test weight; the cable math held",
], [[PH("05_gen1_spool_plate.jpg"), "Gen-1 corner plate: motor, spool, pulley, switch"], [PH("13_gen1_station_lifting_test_weight.jpg"), "Gen-1 station lifting a test weight"]],
"Talk track (50 s): Generation 1 was built to find out what I did not know. Each corner got a one-piece printed plate with the motor, spool, pulley and homing " +
"switch, screwed into a joist. That replaced the closed-eye hooks of the first order, because a hook is a pivot: the anchor moves, and the calibration study shows " +
"about one-to-one transfer from anchor error to claw position error; an anchor has to be fixed to be calibratable. One Uno with a CNC shield drove all four motors. " +
"On the bench a station lifted a test weight, and the cable tension numbers from the previous slide held. Pause and ask: how would you home a four-cable robot " +
"with no reference pose? [[the test weight and how high it lifted]] " +
"If asked: the plate's ears see 5.5 MPa worst case at 40 N, about five times under PETG's layer-adhesion limit. " +
"If asked what bead homing is: Generation 1's way of finding zero for each cable. A stopper bead is crimped onto each cable, and a lever switch sits in its path " +
"at the outlet. To home, every winch reels in until its bead trips the switch; that pose is the reference and each cable's zero length. Because the bead cannot " +
"pass the outlet, a cable can never be shorter than it was at home, so the home pose caps how high and how far the claw can go, which is the next slide. The " +
"switch had to move below the pulley onto a drop arm so the bead never rides over the pulley groove; the first arm design missed the line by 5 mm in X and " +
"10.5 mm in Y in a CAD check, rev D overlaps a 5 mm bead by 3.75 mm. No bead has tripped a printed arm on real line yet. The beads stay on the final robot as " +
"end-of-travel switches.",
{ tags: ["MEASURED"] });

photoSlide("Bench week found what the drawings could not", [
  "18 V on the meter from a supply labelled 12 V",
  "A homing switch that would have zeroed without moving: fail-safe wiring reads LOW at rest, and the firmware took LOW as pressed; logic inverted",
  "The switch had to move below the pulley, onto a drop arm beside the line; the first arm design failed a CAD check before it was printed",
], [[PH("07_bench_wiring_a.jpg"), "Bench wiring during bring-up"], [PH("09_homing_switch_perfboard.jpg"), "Homing switch"], [PH("12_bench_bringup_laptop.jpg"), "Bench laptop"]],
"Talk track (55 s): Three things the bench found that no drawing would have. First, the meter: with the plug cut off the supply brick and a fuse fitted, the " +
"shield terminal read 18 V, not the nominal 12. Second, the homing switch: I wired it fail-safe, common and normally-closed, so it reads LOW at rest and HIGH " +
"when pressed or when a wire breaks; the firmware took LOW as pressed, so homing would have zeroed instantly without moving. The fix was to invert the logic and " +
"add a command that reports all four switches. Third, the switch position: it had to sit below the pulley, beside the vertical line, on a drop arm; the first arm " +
"design failed an independent CAD check before it was printed. The lesson for the rest of the project: a meter on every rail before code. " +
"If asked: whether the 18 V was an open-circuit reading is not recorded; the supply was later identified as 12 V, 6 A, and the station buck accepts up to 20 V.",
{ tags: ["MEASURED"] });

content("Why Generation 1 could not be the final design", [
  "Bead homing (a stopper bead on each cable trips the outlet switch, so no cable can ever be shorter than at home) left 5–29 % of the room's volume reachable: home 1 m up, 5 %; 2 m up, 29 %. Caught on paper",
  "Floor area at grab height reads better, 45 % with home 1 m up and 93 % at 1.5 m: what bead homing loses is height, for the scan and the hamper, not footprint",
  "One central board would need 10 wires to every corner once each winch had sensors: 250 m (820 ft) of wire",
  "A central board also skews the winches: 50 ms of skew is 2.5 mm of cable error, about 7.5 N",
], { sheet: "bead_homing", tab: "Bead homing" },
"Talk track (55 s): Three calculations killed Generation 1 on paper. Homing: a bead on each cable trips a switch at the outlet, so a cable can never be shorter than " +
"at home. The chart shows what that costs: with home one metre up, 5 % of the room is reachable; two metres up, 29 %. Wiring: once each winch has a switch and an " +
"encoder, a central board needs ten wires to every corner, and with the supply on a stand and the runs down the wall and back up, that is 250 metres of wire. " +
"Timing: one board stepping four motors from one loop skews them; 50 ms of skew is 2.5 mm of cable error, about 7.5 N on a 3 N/mm line. Each of these drives one " +
"decision in Act 3. If asked why not home each cable at its own shortest length: that drags the claw into the high-tension zone next to an anchor. " +
"If asked whether floor area is the better measure (it is the honest one for where clothes are picked): same model as the chart, room 11 by 9 ft, anchors " +
"2.59 m up, 0.2 m wall margin, a floor point counts when the claw can reach it at the lowest working height, 0.3 m. With home 1 m up, 45 % of the floor is " +
"reachable at grab height, not 5 %; at 1.2 m, 67 %; at 1.5 m, 93 %; from 1.8 m up, all of it. Bead homing does not lose floor, it loses height: the claw cannot " +
"rise above the home pose anywhere, and near the walls much less, and the robot needs that height to scan from 1.6 m, lift a garment over the hamper and keep " +
"the cables off furniture; a high home pose also sits in the high-tension zone next to the anchors. So the volume figure is the right one for the robot's job, " +
"and I lead with the floor figure because it is the fair one. Calculated, both.",
{ tags: ["CALCULATED"], size: 16, space: 9 });

// ================================================================================================ ACT 3: REDESIGN
section("Redesign"); ACT = "Act 3 of 5: Redesign (September to early October)";
content("The clamp that could not close on thin cloth (Sep 30)", [
  "Rack-and-pinion jaws could not pinch thin fabric: the pinion travel left a 2 mm gap, so the pads never met",
  "The v6 clamp came out at 4.6 times its mass budget in CAD (Oct 20), with no torque path from the servo",
  "Lesson: mass tracked through every version from then on; the final claw was weighed on Oct 22",
  "Final: a geared four-bar with parallel jaws (Act 4)",
], { grid: [R("gen1_tentacle_claw.png"), R("claw_v6.png"), R("gripper1021_head.png"), PH("22_gear_train_printed_servo.jpg")],
     alt: "Claw versions", caption: "Finger claw (CAD only), v6 clamp (CAD), final four-bar (CAD), printed gear train" },
"Talk track (55 s): The claw went through four versions, and each failed for a reason I can name. The fingers never left CAD. The first clamp, September 30: " +
"rack-and-pinion jaws whose pinion travel left a 2 mm gap, so on thin cloth on a hard floor the pads never met. The v6 clamp, October 20: in CAD it came out at " +
"4.6 times its mass budget, up to 2.06 kg against 0.45, and with no torque path from the servo to the jaws. That was the moment I started tracking mass through " +
"every version, and the final claw was weighed two days later. The final design is the geared four-bar with parallel jaws, in Act 4. " +
"If asked: the mass problem was never the budget; it was that I did not re-check the budget as the claw changed.",
{ tags: ["CAD"] });

{
  const WL = require(P("calculations", "lift_chain_weakest_link.json"));
  const n0 = v => String(Math.round(v));
  content("One plug per station: the station lifts off while the anchor stays in the stud", [
    "Slide-in wall mount: the station lifts off its dovetail; the wall mount and its screws stay in the stud",
    "Load path: cable, spool, set screw, motor, PETG tab, slide-in, wall mount, screws, stud",
    `The motor is the weakest link: it slips at ${n0(WL.fuse.slip_low)}–${n0(WL.fuse.upper)} N before anything breaks, and the spool encoder reports the overload`,
    "Reading the margins: every other part must give at 1.5 × the motor's slip force (calculated, against derated PETG); the 1.5 on the winch pull is the skipped-step margin",
  ], { grid: [SC("station_shell_transparent_1022.png"), PH("24_station_housing_on_wall.jpg"), PH("45_wall_mount_bracket_alone_corner.jpg"), PH("46_wall_mount_bracket_xt60_power_lead.jpg")],
       alt: "Final wall station: CAD, on the wall, and the wall mount alone",
       caption: "SolidWorks, shell transparent; the shell on the wall (Oct 22); the wall mount alone in a corner, and with its XT60 power lead (Oct 27)" },
  "Talk track (55 s): The station that came out of the redesign. One plug per station: the wall mount is screwed into a stud, and the station slides onto it " +
  "on a dovetail, so it lifts off for service while the anchor stays put. Walk the load from the cable to the stud: cable, spool, set screw, motor shaft, the " +
  "printed motor tab, the slide-in, the wall mount, the screws, the stud. The design idea is to make the motor the part that gives first. At 1.5 A it slips at " +
  "34 to 59 N, depending on the spool fill and the cable angle, before any part breaks; the encoder on the spool sees the spool fall behind the command and the " +
  "station stops and reports an overload. Every other part has to outlast that. " +
  "If asked: as drawn, the spool's set screw in printed plastic may slip first and the warm motor tab's sharp corner is only about 1.2 times the motor; the fixes " +
  "are the set screw into metal and a 6 mm tab with fillets. A #6 wood screw in a stud holds about 309 N; in drywall alone about 46 N, so studs only. " +
  "If asked how to read the safety margins: the 1.5 here is the ratio of the cable tension at which a part gives to the most the motor can pull before it " +
  "slips, 59 N; at or above 1.5 the motor is guaranteed to give first, 1.0 to 1.5 is marginal, below 1.0 the part fails before the motor. It is a different 1.5 " +
  "from the skip margin on the winch pull (running pull divided by 1.5 so a snag does not skip steps), and different again from a stress SF, allowable over " +
  "calculated, where printed PETG gets half its tensile strength and 15 % off when warm. All calculated against assumed allowables; none is tested.",
  { tags: ["CALCULATED"], size: 16, space: 9, eq: { title: "Motor slip force (the fuse)", lines: [
    "F = τ_h / r = 0.36 N·m / 0.0075 m = **48 N**",
    "F_{max} = 48 N × 1.11 (motor) × 1.11 (cable angle) = **59 N**",
  ] } });
}

content("The drive slips before the wall does: a designed fuse", [
  "Four cables on three axes can pull against each other; a length error becomes tension, up to a snag that could tear a mount out",
  "The motor's rotor skips at 34–59 N of cable tension, the designed fuse: every other part gives higher, the wall screws in a stud at 9 × and the slide-in dovetails at 225 × the motor's pull",
  "The spool encoder sees the spool fall behind the commanded steps: a TRACKING fault, and every station holds",
  "The same mechanism catches an overweight pickup and a missed over-tension; the one exception as drawn, the set screw in printed plastic (22–64 N), moves into a metal insert",
], { sheet: "weakest_link", tab: "Weakest link" },
"Talk track (55 s): The safety idea in one chart: the cable tension at which each part of the lifting chain gives, from the set screw to the screws in the stud. " +
"Cables only pull, and four of them on three axes are over-constrained, so a length error turns into tension, and a snag can pull far harder than the load. " +
"Rather than make every part strong enough for any snag, I made the motor the fuse: at 1.5 A its rotor skips at 34 to 59 N of cable tension, depending on " +
"the spool fill and the cable angle, and everything else in the chain gives at a higher tension, the wall screws in a stud at nine times the motor, the " +
"dovetails at over two hundred. When the rotor skips, the encoder on the spool sees the spool fall behind the commanded steps, the station raises a tracking " +
"fault and every station holds with torque on. The same mechanism catches a pickup that is too heavy and an over-tension the planner missed. The one part " +
"that may give before the motor as drawn is the set screw in its printed thread, so it moves into a metal insert. " +
"If asked: the slip is the stepper's own torque limit, not a clutch; a mechanical clutch would add a part, a calibration and a cost to each of four stations, and " +
"the stepper already has a sharp, repeatable torque ceiling. What happens after a slip: the station stops and reports; the host does not resume by itself; " +
"the spool count is the truth, so the cable's zero length is re-referenced from the encoder and the calibration before the next move, and a person approves " +
"it. The 3:1 gear stage raises the slip force to about 130 N at 1.0 A, so the new station is sized for 200 N. All calculated from the motor's holding " +
"torque; the slip has not been measured yet, the pull test does that.",
{ tags: ["CALCULATED"], size: 15, space: 9 });

content("One controller per winch", [
  "Generation 1's central box worked within about a day and a half; it had to go: 250 m (820 ft) of wire once each winch had sensors, 2.5 mm of skew per 50 ms, a tangle to unplug and shelve, no modularity",
  "Now: a controller in each station, fed by one 12 V pair: 50 m (164 ft)",
  "Each station is built, tested and swapped on its own",
  "The cost: timing moves into software",
], (sl, x, y, w, h) => {
  figure(sl, { file: [PH("14_gen1_cnc_shield_a4988.jpg"), PH("19_station_perfboard_soldered.jpg")], alt: "Central board and station board",
               caption: "Before: one central driver board. After: a controller in each station." }, x, y, w, 2.45);
  table(sl, ["", "Generation 1", "Final"], [
    ["Where is the claw?", "Assumed from commanded cable lengths", "Measured by the claw camera at every startup"],
    ["Room geometry", "Anchors from a tape measure", "Anchors and cable lengths fitted, with error bars"],
    ["Motor control", "One central board", "A controller per station, coordinated by the laptop"],
    ["Finding laundry", "Ceiling camera", "Claw camera"],
    ["Did the grab work?", "Assumed", "Camera checks pickup and delivery"],
    ["Faults", "Emergency stop only", "PAUSE keeps torque; a power loss drops the claw (no brake) and nothing resumes by itself"],
  ], x, y + 2.5, w, [0.22, 0.33, 0.45], { size: 10.5, rowH: 0.34, name: "control logic" });
},
"Talk track (50 s): Generation 1's central box, one Uno and one shield, worked within about a day and a half, and it had to go for four reasons: wire, once each " +
"winch carried a switch and an encoder, 250 metres against 50; timing, one loop stepping four motors skews them, 2.5 mm per 50 ms; packaging and storage, " +
"every test meant unplugging and handling all of that wiring to put it on a shelf; and no modularity, one box for four winches. So: a controller in each station instead of one central board. Each station gets one 12 V pair, " +
"50 metres of wire in total instead of 250, and it can be built and tested on its own, which is exactly how the bench week in Act 5 went. The cost is that the " +
"four winches now have to agree on time in software: each station runs time-stamped segments on its own clock and holds if the link drops, with a 40 ms skew " +
"budget that keeps the error to 2 mm. The table is the wider change: Generation 1 trusted its model; the final logic measures before it trusts and checks " +
"after it acts. If asked: cable routes are 6, 21, 23 and 32 ft; line stiffness is about 3 N/mm over a 3 m run. " +
"If asked what happens when the motors lose power: a stepper holds only while it is powered, and there is no brake and no self-locking stage, so if the 12 V " +
"goes, from the power strip, a blown fuse or a pulled plug, all four motors lose holding torque and the claw falls, up to 1.5 kg from about 2 m. That is " +
"deliberate: the power strip is the one category-0 stop software cannot override, and the mitigation is that nobody stands under the robot. Each station's " +
"controller runs from the same 12 V pair, so a power loss is also a reboot: the driver's enable line is pulled high at boot so a reset can never move a motor, " +
"and nothing resumes by itself, the host comes back disarmed or in recovery and waits for a person. A lost Wi-Fi link is different: the stations stop and hold " +
"on their own clocks with torque on. A brake or a non-backdrivable stage is on the next-steps list. Designed and simulated; not yet run on four stations.",
{ size: 16, space: 10 });

content("The claw camera replaces bead homing", [
  "The claw camera reads a printed floor board, and a fit finds the anchors and cable lengths: the whole room is reachable",
  "Camera pose per frame, best case: 6.6 mm with one tag in view, 0.7 mm with four",
  "After the fit, cable lengths are known to about 12–16 mm (simulated); the room opens only when the error bars allow it",
  "Beads stay on the cables as end stops: a bead reaching its switch stops that station",
], { sheet: "floor_board", tab: "Floor board" },
"Talk track (55 s): Bead homing died on the reachability chart, so the claw camera does the homing instead. At startup the claw looks down at a printed floor " +
"board; from the tags it sees, a fit finds the anchor positions and the cable lengths, with error bars, and the whole room becomes reachable. The chart is the " +
"camera's per-frame accuracy, best case: 6.6 mm with one tag in view, 0.7 mm with four. That is not the number that matters. The number that matters is the " +
"cable length after the fit, about 12 to 16 mm in simulation; averaging frames removes noise but not bias, and the planner opens the room only as far as the " +
"error bars allow. The beads stay on the cables as end stops. If asked: noise model 0.3 px corner noise and a 520 px focal length, camera not yet calibrated; " +
"realistic tag placements are a few times worse than the four-tag best case. " +
"If asked whether floor area shows the reachable share better than volume: yes for where clothes are picked, and it reads kinder to bead homing: with the beads " +
"set 1 m up, 45 % of the floor is reachable at grab height, 93 % at 1.5 m, all of it from 1.8 m (same model as the Act 2 chart, calculated). What bead homing " +
"loses is height, not footprint: the claw can never rise above its home pose, and the robot needs the height to scan from 1.6 m, lift over the hamper and keep " +
"cables off furniture, and a high home sits in the high-tension zone by the anchors. The camera calibration removes the cap entirely, within the error bars.",
{ tags: ["SIMULATED"], size: 16, space: 10 });

// ================================================================================================ ACT 4: FINAL DESIGN
section("Final design"); ACT = "Act 4 of 5: Final design (October 7-21)";
{
  const sl = blank("Heat: a sealed PETG box would cook its own motor mount", ["CALCULATED"]);
  const fx = M, fw = 6.9, fy = 1.3, fh = 5.45, bx = fx + fw + 0.4, bw = W - M - bx;
  figure(sl, { sheet: "motor_temperature", tab: "Motor temperature; assumed 1.8 Ω coil, 23 °C room" }, fx, fy, fw, fh / 2 - 0.05);
  figure(sl, { sheet: "heat_fin", tab: "Heat fin; Incropera, ch. 3" }, fx, fy + fh / 2 + 0.05, fw, fh / 2 - 0.05);
  bullets(sl, [
    "1.5 A doubles motor heat to 4.05 W; the PETG mount must stay below 60 °C",
    "The fin conducts heat off the motor flange and out of the shell to room air: 35–50 % of the 4.05 W",
    "Vented shell and fin: 56–59 °C with the 0.019 in prototype, 45–49 °C with the 1/8 in design",
    "Thin sheet stops gaining by 136 mm; 1/8 in plate keeps gaining to 349 mm",
  ], bx, 1.35, bw, 1.9, 12, { space: 4, name: "cooling bullets" });
  label(sl, "If the fin alone carried all 4.05 W (painted 6061, 44 mm wide)", bx, 3.26, bw, 0.24, { size: 11, bold: true, color: HEX.navy });
  table(sl, ["Thickness", "Mass", "Shortest for ≤ 60 °C"], [
    ["0.019 in (prototype)", "14 g", "None (2.0 W max)"],
    ["1/16 in", "47 g", "None (3.6 W max)"],
    ["0.090 in", "68 g", "210 mm or none"],
    ["1/8 in (design)", "94 g", "145–185 mm"],
    ["3/16 in", "141 g", "125–140 mm"],
    ["1/4 in", "189 g", "115–125 mm"],
  ], bx, 3.5, bw, [0.42, 0.18, 0.4], { size: 10, rowH: 0.25, name: "fin sizing" });
  eqBox(sl, { title: "Motor heat, P = I² R", lines: ["At 1.06 A: (1.06 A)² × 1.8 Ω = 2.0 W", "At 1.5 A: (1.5 A)² × 1.8 Ω = **4.05 W**"] }, bx, 6.75 - eqHeight({ lines: [1, 2] }), bw);
  sl.addNotes("Talk track (55 s): Raising the drivers to the motor's rated 1.5 A doubles the heat to 4.05 W per motor, and the motor sits in a printed PETG " +
              "mount that softens at 60 °C. A sealed shell would cook it. The answer is a vented shell and an aluminium fin bolted to the motor face and out " +
              "through a slot in the top. Top chart: motor temperature for each fin, vented and sealed; the prototype fin, 0.019 in scrap sheet, lands at 56 to 59 °C, " +
              "one to four degrees of margin; the 1/8 in design fin at 45 to 49. Bottom chart: why thickness beats length; the thin sheet stops gaining by 136 mm, " +
              "the plate keeps gaining to 349. The table answers what fin it would take to carry all the heat alone. " +
              "If asked: built length is 200 mm, limited by the ceiling; the fallback is 1.35 A; warmer air near the ceiling eats the prototype's margin; a 90-minute " +
              "hold test is planned. " +
              "If asked what the fin does for heat dissipation: the motor's only way out of a closed printed box is conduction into the PETG it is bolted to, and " +
              "PETG is an insulator, 0.2 W/m·K against 160 for aluminium; the 5 mm tab is 14 K/W, a 3 mm aluminium plate 0.011 K/W, 1260 times less. The fin is " +
              "that plate: it sits between the motor flange and the tab, takes heat from the flange by conduction, carries it along the sheet and out through the " +
              "slot in the shell top, and sheds it to room air by convection and radiation over both faces, 200 by 44 mm. In the model it carries 35 to 50 % of " +
              "the 4.05 W, cuts the sealed-shell motor from about 99 to 64 °C and the vented from 77 to 56–59, and it keeps the loaded PETG tab under the motor " +
              "cooler, which is the creep concern; it also spreads the bolt load. The thin sheet stops gaining by 136 mm because it cannot conduct more; the 1/8 in " +
              "plate would carry all 4.05 W alone at 56–59 °C. All calculated; no temperature measured yet. " +
              "If asked why the 6061 is painted: paint is for radiation. Bare aluminium has an emissivity near 0.1 and radiates almost nothing; matte black is " +
              "about 0.9, and for a thin plate in still air that nearly doubles the heat it sheds per degree: the effective film coefficient is 10.6 W/m²·K painted " +
              "against 6.2 bare. In the sizing table that is the difference between a 1/8 in fin that works at 145 to 185 mm and a bare one that needs 1/4 in and " +
              "about 300 mm; the motor itself moves less, 1.5 to 3 K, because it also sheds heat into the shell air. The contact square under the motor stays bare " +
              "with thermal paste so paint never sits in the conduction path. The drawing calls for matte black; the photos of the built prototype fin show bare " +
              "metal and the alloy is unconfirmed. [[Jasper: is the built prototype fin painted, with what and when; is the sheet 6061 and how do you know?]]");
}

{
  const sl = blank("Winch pull and what the four winches can lift", ["MEASURED", "CALCULATED"]);
  const fx = M, fw = 6.9, fy = 1.3, fh = 5.45, bx = fx + fw + 0.4, bw = W - M - bx;
  figure(sl, { sheet: "winch_pull", tab: "Winch pull" }, fx, fy, fw, fh / 2 - 0.05);
  figure(sl, { sheet: "lift_budget", tab: "Lift budget" }, fx, fy + fh / 2 + 0.05, fw, fh / 2 - 0.05);
  const eq = { title: "Lift capacity", lines: [
    "m_{max} = F_{design} / (k g) = 16.8 / (1.101 × 9.81)",
    "= **1.56 kg** against 0.60 + 0.90 = **1.50 kg**",
  ] };
  bullets(sl, [
    "Calculated pull at 1.5 A: 34 N on an empty spool, 25 N when full; running torque assumed 0.7 × holding",
    "Claw with battery weighed 0.60 kg (0.86 kg estimated)",
    "Jeans: 1.50 kg against 1.56 kg capacity, a 4 % margin, inside the uncertainty (1.1 kg at 0.5 × holding torque)",
    "The pull test decides: keep 1.5 A, or add a gear stage at each winch",
  ], bx, 1.35, bw, 6.75 - eqHeight(eq) - 0.2 - 1.35, 15, { space: 8, name: "lift bullets" });
  eqBox(sl, eq, bx, 6.75 - eqHeight(eq), bw);
  sl.addNotes("Talk track (55 s): Top chart: what one winch pulls at 1.5 A as the spool fills: 34 N on the empty core, 25 N full, assuming running torque is " +
              "0.7 of holding torque. Divided by 1.5 against skipped steps, that is the 16.8 N design force. Bottom chart: what the four winches hold at task " +
              "height against what they must hold. The claw weighed 0.60 kg with its battery, against 0.86 estimated. With jeans that is 1.50 kg against a " +
              "capacity of 1.56: a 4 % margin, which is inside the uncertainty, because at 0.5 times holding torque the capacity is 1.1 kg. The pull test decides " +
              "whether 1.5 A is enough; the alternative is a gear stage at each winch, which is the next slide. Pause and ask: cut claw mass or add the gear " +
              "stage? If asked: the current is set by the driver reference voltage, I = Vref / (8 × 0.1 Ω) [[how 1.5 A was reached and the Vref read]]; the A4988 runs " +
              "hot at 1.5 A and shuts down if it overheats, so the hold test watches it. " +
              "If asked how the pull value was validated: it has not been; the pull is calculated and the test is planned. The chain is Vref to current, " +
              "1.5 A at 1.2 V; holding torque proportional to current from the 0.36 N·m rating; running torque assumed 0.7 of holding; and torque over spool " +
              "radius, 34 N on the empty 7.5 mm core and 25 N at the full 10 mm. The two weak links are the 0.7, a convention, and the torque basis: if the " +
              "0.36 N·m rating is a two-phase figure the pull could be about 1.4 times lower. The validation is a 15-minute luggage-scale test on one station, " +
              "reeling in against the scale at the empty and the full spool until the motor skips; its result replaces the 0.7 and goes into the planner as the " +
              "tension limit. " +
              "If asked where the 25 % drop from the 0.86 kg estimate came from: same claw, same parts. The tube (198 g in CAD), servo (55 g) and battery (99 g) " +
              "were never in doubt; the printed parts came to about 250 g on the scale against 860 g if they were solid plastic, 677 cm³ of CAD volume. The " +
              "estimate priced them from CAD solids, and printed parts have walls and infill; the exact assumptions behind the 0.86 are not itemized in my notes. " +
              "The lesson: a CAD mass is an upper bound, the budget is checked on the scale. [[Jasper: infill and wall count on the claw parts; did the 0.86 kg " +
              "estimate assume solid parts or a slicer mass?]]");
}

{
  const sl = blank("A 3:1 gear stage, all printed, with the encoder on the spool shaft", ["CALCULATED", "CAD"]);
  const fx = M, fy = 1.3, fh = 5.45;
  const cw = 3.55, g = 0.12;
  // renders cropped of their text strips (deck_v9/fig, from renders/winch_gear3)
  const r1 = fitImage(sl, path.join(__dirname, "fig", "winch_gear3_iso_crop.png"), fx, fy, cw, 2.35, "Winch gear stage, isometric render", { alignTop: true });
  caption(sl, "1  Pinion on the motor; gear and spool in one part", r1.x, r1.y + r1.h + 0.03, cw + 0.3);
  const r2 = fitImage(sl, path.join(__dirname, "fig", "winch_gear3_mesh_crop.png"), fx, fy + 2.75, cw, 2.35, "Gear mesh close-up render", { alignTop: true });
  caption(sl, "2  Mesh: module 1, 36.3 mm centres", r2.x, r2.y + r2.h + 0.03, cw);
  const px = fx + cw + g, pw = (fh - 0.3) * 1932 / 2576;
  const r3 = fitImage(sl, PH("39_slide_in_handheld_wiring_hanging.jpg"), px, fy, pw, fh - 0.3, "Slide-in with motor, spool and end stop, Oct 26", { alignTop: true });
  caption(sl, "3  Slide-in: motor, spool, end stop, harness (Oct 26)", r3.x, r3.y + r3.h + 0.05, pw);
  const bx = px + pw + 0.4, bw = W - M - bx;
  bullets(sl, [
    "18T pinion, 54T gear, module 1: 3:1 at the spool. Lift capacity 1.98–2.80 kg at 1.0 A (was 1.10–1.56 kg), motor heat 1.8 W (was 4.05)",
    "Printed PETG pinion: its teeth hold 1.75 × the motor's slip force at 1.0 A",
    "The spool encoder has two jobs: confirm every commanded step, and detect slip as the tension sensor",
    "Backlash 0.42 mm at the pitch circle, 10 encoder counts of the 60-count tolerance; the magnet moves to the spool shaft end, measured Ø4.0, not the Ø6 assumed",
  ], bx, 1.35, bw, 5.4, 15, { space: 10, name: "gear bullets" });
  sl.addNotes("Talk track (55 s): The gear stage that takes the lift margin from 4 % to a real one. An 18-tooth pinion on the motor drives a 54-tooth gear " +
              "printed in one piece with the spool, module 1, 3:1. At 1.0 A the capacity goes from 1.10 to 1.56 kg up to 1.98 to 2.80 kg, and the motor heat " +
              "drops from 4.05 W to 1.8, which also relaxes the fin. I printed the pinion too: its teeth are the weakest tooth in the train, at 1.75 times the " +
              "most the motor can pull before it slips, so the motor still gives first. Backlash is 0.42 mm, ten encoder counts out of the sixty the tracking " +
              "fault allows. The encoder magnet moves to the end of the spool shaft, and when I measured it, it was 4 mm, not the 6 the spec had assumed, so the " +
              "cap was redrawn. If asked: at 1.5 A the pinion teeth drop to 1.17 and the set screw to 1.00, so the recommendation is 1.0 A; the spool shaft is " +
              "Ø7 steel in two 687 bearings; the stage is verified in CAD, not yet pull-tested.");
}

photoSlide("The claw: geared four-bar hands, camera bay, one 2S pack", [
  "The hands are four-bar couplers: they stay within 1° of parallel over the 53 mm opening",
  "Grip 13.3–25 N per jaw against 17.7 N for jeans: short at the narrowest grab, enough above a 22 mm grab",
  "One 7.4 V two-cell pack: a 6 V regulator for the servo, a 5 V buck for the board, a 200k/100k divider for battery sense",
], [[PH("25_claw_assembled.jpg"), "Claw assembled (Oct 22)"], [PH("40_claw_housing_ubec_wagos_lit.jpg"), "Electronics housing open (Oct 26)"]],
"Talk track (55 s): The final claw. The servo drives an 18-tooth pinion into a 54-tooth gear, 3:1, and each hand is a four-bar coupler on the gear's crank and the " +
"arm, a near-parallelogram, so the hands stay within a degree of parallel across the 53 mm opening. Grip: jeans need 17.7 N per jaw at a friction of 0.3; the " +
"jaws give 13.3 N at the narrowest grab and 25 N at a 70 mm grab, so narrow grabs are short and grippy pads are next. Power: one two-cell 7.4 V pack, a 6 V " +
"regulator for the servo, a 5 V buck for the camera board, a 200k over 100k divider so the board reads its own battery. The right photo is the housing open on " +
"the bench. If asked: gear safety factor 2.05 at servo stall; peak draw 2.8 to 3.1 A at the pack's 3 A rating; 5 A fuse; charged attended at 1 A or less; " +
"the tips drop about 38 mm while closing, so the claw closes from 35 to 40 mm above the floor. " +
"If asked where the 0.3 friction coefficient came from: it is an assumed value for cloth on a bare printed PETG pad, chosen low on purpose, and the numbers " +
"are also run at 0.6 for TPU pads. It has not been measured, which is why the jeans case is marked short and why a pull test with a force gauge on the real " +
"pads is first on the list. [[Jasper: where did 0.3 come from: a handbook value, a class note, a guess, or a quick test with a scale; if a test, what pad, what " +
"cloth, what reading?]] " +
"If asked what a narrow grab is: a grip where the jaw tips are close together when the pads meet the cloth, a thin fold rather than a bunched handful. The " +
"hands ride on a gear crank, so the effective lever arm from the crank to the pad is longest when the jaws are nearly closed, 59 mm at a 10 mm gap, and " +
"shortest at a wide grab, 33 mm at 70 mm; stall torque is fixed, so pad force is lowest at a narrow grab, 13.3 N, and 25 N at 70 mm. Jeans at 0.3 need 17.7 N " +
"per jaw, so the force is short until the grab is at least 43 mm wide at 4.8 V, 22 mm at the 6 V the servo rail actually runs. Grippy pads halve the need.",
{ tags: ["CALCULATED"], eq: { title: "Grip force per jaw, jeans", lines: [
  "N ≥ m (g + a) / (2μ) = 0.9 × 11.81 / 0.6 = **17.7 N**",
  "Jaws: **13.3 N** narrowest, 25 N at a 70 mm grab",
] } });

// ================================================================================================ ACT 5: BUILD AND BRING-UP
section("Build and bring-up"); ACT = "Act 5 of 5: Build and bring-up (October 22-26)";
{
  const sl = blank("Printing and machining: fits came from coupons, not guesses", ["MEASURED"]);
  const fx = M, fy = 1.3, fh = 5.45, g = 0.12, cw = 2.6;
  const col = [[PH("26_slicer_k1_petg_supports.jpg"), "Slicing PETG, 0.2 mm layers"], [V8FIG + "/snap_dovetail.png", "Slide-in rib in the dovetail"],
               [V8FIG + "/snap_gear_lip.png", "Gear: Ø14.000 entry lip, 8 T-slots"]];
  let cy = fy;
  col.forEach(([f, cap], i) => {
    const d = imgSize(f), ih = cw * d.h / d.w;
    fitImage(sl, f, fx, cy, cw, ih, cap, { alignTop: true, alignLeft: true });
    caption(sl, `${i + 1}  ${cap}`, fx, cy + ih + 0.02, cw + 0.4);
    cy += ih + 0.3;
  });
  const px = fx + cw + g + 0.3, pw = (fh - 0.3) * 1932 / 2576;
  const r = fitImage(sl, PH("35_shell_blue_fin_rhyno_logo.jpg"), px, fy, pw, fh - 0.3, "Blue shell with its fin; a failed layer kept", { alignTop: true });
  caption(sl, "4  Blue shell and fin; the failed layer near the top was kept", r.x, r.y + r.h + 0.05, pw + 0.5);
  const bx = px + pw + 0.4, bw = W - M - bx;
  bullets(sl, [
    "The spool bore printed too tight (Ø5.2 on a 5 mm shaft): opened to Ø5.45 after a fit coupon",
    "Fin holes drilled in one setup: the first hole became the mill's zero, so the pattern carries ±0.1 mm, not the sheared edges' ±0.5",
    "One shell kept a failed layer: it is a shell, not a load path",
    "Printed holes come out small, so every printed fit carries an allowance; the drilled fin needs none",
  ], bx, 1.35, bw, 5.4, 15, { space: 10, name: "fits bullets" });
  sl.addNotes("Talk track (55 s): Build week, starting with the parts. Everything structural is PETG on a Creality K1, 0.4 mm nozzle, 0.2 mm layers, loads along " +
              "the layers, mating faces away from supports. The fits came from coupons: the first spool bore, 5.2 mm on a 5 mm shaft, would not go on; v3 opened " +
              "it to 5.45 and now every printed fit carries an allowance. The gear bearing pockets are the ones I am proudest of: the bearing presses past a lip, " +
              "the T-slots let the lip flex, and it sits free in a pocket 0.075 mm larger. The fin is the one machined part: the sheared edges are only good to half " +
              "a millimetre, so I used them to find the first hole, zeroed the mill on it and put the other four in from there. And one shell kept a failed layer " +
              "near the top: it is a shell, not in the load path, so it went on the wall. If asked: the spool's set screw carries the torque; which holes get " +
              "heat-set inserts: M3 in the gear housing, M2.5 at the encoder. [[confirm which spool bore is printed and the insert part number]]");
}

photoSlide("Station electronics on the bench: every check before the motor turns", [
  "Driver off at boot: a reset cannot move a motor",
  "Homing switch LOW at rest, HIGH pressed or with a broken wire; the encoder answers at its address with the magnet detected",
  "One spool turn within 60 encoder counts: PASS on both boards",
  "A short found by the board's LED going out, traced to the switch pull-up",
], [[PH("43_bench_two_stations_laptop_meter_floor.jpg"), "Bench: two stations, laptop, meter, 12 V supply"], [PH("29_station_bench_esp32_wiring_floor.jpg"), "Dev board, driver, spool and end stop"],
    [PH("37_station_bench_red_shell_fuse_12v.jpg"), "Red shell, fused 12 V lead"], [PH("31_station_bench_xiao_breadboard_shell_open.jpg"), "Second board, shell open"]],
"Talk track (55 s): The station electronics went through a bench script one part at a time, before the station firmware went on. Boot on USB alone with 12 V off: " +
"the board's LED on, the board cool. The homing switch reads LOW at rest and HIGH when pressed or when a wire breaks, the fail-safe wiring from Act 2. The encoder " +
"answers at its address and reports the magnet detected. Then 12 V on: the driver must stay off at boot, so a reset can never move a motor. Enable, jog a quarter " +
"turn each way, then one full spool turn, which must land within 60 encoder counts of a revolution: PASS on both boards, the dev board and the smaller one. One " +
"short announced itself by the LED going out; it traced to the switch pull-up. If asked: the sign the one-turn test prints is what the step and encoder signs in " +
"the config must agree on; 60 counts is 0.69 mm of line, about twice the error budget; the magnet reported detected with the Ø4 magnet. " +
"If asked about the earlier motor that would not turn and the bad 3.3 V connection (October, the first gen-2 station): the log said it was stepping and the " +
"shaft said it was not, so I stopped changing code and put the meter on the driver. Enable toggled with the command, 3.3 V idle, 0 V during the run, 3.3 V " +
"after, which cleared the firmware; the sleep pin read about 1 V and the logic rail about 1.14 V instead of 3.3, which pointed at the driver's supply, and it " +
"was a bad 3.3 V connection; after the fix the motor turned, loud and slow. Those readings were on my meter, not logged. The habit that came out of it is this " +
"slide: a meter on every rail before code, and the driver's logic supply now comes off the same regulated rail as the controller, soldered, with a VDD check " +
"before enable. [[Jasper: what you tried before the meter; which wire or pin was the bad 3.3 V connection and what was physically wrong (loose jumper, cold " +
"joint, breadboard contact); VDD after the repair; the date.]]",
{ tags: ["MEASURED"] });

{
  const sl = blank("Claw electronics on the bench: camera, battery, servo", ["MEASURED"]);
  const fx = M, fy = 1.3, fh = 5.45, g = 0.15;
  const pw = (fh - 0.3) * 1932 / 2576;
  const r = fitImage(sl, PH("40_claw_housing_ubec_wagos_lit.jpg"), fx, fy, pw, fh - 0.3, "Claw electronics housing open, lit", { alignTop: true });
  caption(sl, "1  Housing open: regulators, battery, camera board", r.x, r.y + r.h + 0.05, pw + 0.1);
  const sx = r.x + r.w + g, sw = 3.0;
  placeholderBox(sl, "[[Jasper: screenshot of the live view on the phone]]", sx, fy, sw, fh - 0.3);
  caption(sl, "2  Live view from the claw camera", sx, fy + fh - 0.25, sw);
  const bx = sx + sw + 0.4, bw = W - M - bx;
  bullets(sl, [
    "Live video from the claw camera on the phone",
    "Battery 7.2 V read through the divider, matching the meter",
    "The servo only moved once it had its own hardware timer; the camera owned the first one",
    "Still open: servo end points unmeasured; camera not yet calibrated",
  ], bx, 1.35, bw, 5.4, 15, { space: 10, name: "claw bench bullets" });
  sl.addNotes("Talk track (50 s): The claw electronics on the bench, Rev B. Three passes: the camera streams live video to the phone; the board reads its battery " +
              "through the divider at 7.2 V, matching the meter; and the servo moves. The servo was the find: with the camera running it got no pulses at all. " +
              "The camera's clock generator and the servo's PWM were sharing one hardware timer; the servo now drives from its own timer and the camera keeps " +
              "the first. That is the kind of fault the schematic cannot show. Still open: the servo's open and closed end points are not measured, and the " +
              "camera is not calibrated yet. If asked: the 5 V buck is set to 5.16 V and the board sees about 4.9 V after its diode; an earlier 4.33 V reading " +
              "was a meter mis-read, not the pack; the board and the wiring were net-checked against the spec before any power went on.");
}

photoSlide("On the wall", [
  "First station in a stud on the TV wall: 12 V down the wall, the fin out through the slot in the top",
  "Boxed stations boot and join Wi-Fi on their own; firmware updates arrive over Wi-Fi, so a boxed station never needs a USB cable again",
  "The motor stays off until the phone arms it; a station accepts an update only while disarmed",
], [[PH("32_wall_station_mounted_tv_wall.jpg"), "Station mounted high on the TV wall, 12 V leads down"], [PH("44_wall_station_from_below_line_down.jpg"), "From below: the line leaves the switch tab straight down"],
    [PH("36_shell_front_vents_fin_tab.jpg"), "Shell front: vents, fin tab"]],
"Talk track (50 s): The first station on the wall, in a stud on the TV wall, with the 12 V pair running down the wall and the fin out through the slot in the " +
"top of the shell. From below you can see the shell on its grey wall mount, the slide-in from Act 3, and the line leaving the switch tab straight down, with the 12 V lead in a lever nut. Because a station is a sealed box up at the " +
"ceiling, it has to look after itself: it boots, joins Wi-Fi at a fixed address and keeps retrying until the router is up, and firmware updates arrive over " +
"Wi-Fi, so a boxed station never needs a USB cable again. The motor stays off until the phone arms it, and a station only accepts an update while it is " +
"disarmed, so an update can never drop a load. If asked: the one USB flash happens on the bench before boxing; the claw accepts updates only while its grip " +
"is open, for the same reason; the three stations are not on the network yet.");

content("Three stations first: the triangle, the tilt, and no spare cable", [
  "A and B in two corners of one wall, C mid-wall opposite: a 3.25 / 3.10 / 3.10 m triangle, nearly equilateral",
  "Hanging from three of the four corner holes tilts the claw 5.5° at the start point; the lift aborts at 8°",
  "Grips (5° limit) would be refused over 78 % of the floor; a three-hole housing at 120° brings the start tilt to 0.8°",
  "No spare cable: a station fault drops the claw, so the floor under it stays clear and padded",
], (sl, x, y, w, h) => threeStationPlan(sl, x, y, w, h),
"Talk track (55 s): The first system test runs on three stations, not four. A and B sit in the two corners of one wall, C on the stud nearest the middle of the " +
"opposite wall, all at the same height, so the triangle is nearly equilateral and the usable area is as large as it can be; the claw starts at the centroid. " +
"Two costs. Tilt: the claw hangs from three of its four corner holes, so its centre of mass is off the centroid of the holes and it hangs 5.5° over at the " +
"start; the lift aborts at 8°, and the grip check refuses above 5°, which would refuse grips over 78 % of the floor. A housing with three holes at 120° brings " +
"the start tilt to 0.8°; until then, three-station runs are for movement and calibration, not pickups. Redundancy: with four cables a failed station leaves " +
"three; with three, a station fault drops the claw, so the floor is clear and padded. If asked: the entries only seed the calibration, which fits the geometry " +
"itself; a stud 0.2 m off the midpoint leaves about 0.12 m after the fit; all simulated, not yet run.",
{ tags: ["SIMULATED"], size: 16, space: 10 });

// ================================================================================================ RESULTS AND CLOSE
section("Results and close"); ACT = "";
{
  const sl = blank("Results against targets, and what is still planned", ["MEASURED", "CALCULATED", "PLANNED"]);
  const RED = t => ({ text: t, color: HEX.red, bold: true });
  table(sl, ["Target", "Goal", "Current", "Evidence", "Status"], [
    ["Lift capacity", "1.50 kg with jeans", "1.56 kg; 1.1 kg at 0.5 × holding torque; 1.98–2.80 kg with the 3:1 stage", "Calculated", "Marginal; pull test"],
    ["Grip for jeans", "17.7 N per jaw", "13.3–25 N; a narrow grab is a jaw gap under 22 mm at the cloth (6 V), where the lever arm is longest", "Calculated", RED("Short at narrow grabs")],
    ["Claw mass", "0.45 kg", "0.60 kg with battery", "Weighed", RED("Not met")],
    ["Motor temperature", "Below 60 °C", "56–59 °C prototype fin", "Calculated", "Marginal; hold test"],
    ["Weakest link", "Motor slips first", "Set screw may slip first; tab at 1.2 ×", "Calculated", RED("Two fixes")],
    ["Working area", "Floor, 0.2 m wall margin", "All but 0.2 m at the walls", "Calculated", "Met in design"],
    ["Wiring", "One cable per station", "One 12 V pair; 0.51 V drop", "Built", "Met (bench PASS)"],
    ["Station bench test", "Switch, encoder, driver, one turn", "PASS on both boards", "Measured", "Met"],
    ["Claw bench test", "Camera, battery, servo", "Live view; 7.2 V; servo moves", "Measured", "Met"],
    ["Accuracy", "≤ 2 mm cable mismatch", "40 ms skew budget gives 2 mm", "Not measured", "To be tested"],
    ["Obstacle map in the app", "Drawn shapes kept out of every path", "Built; two findings being fixed", "Simulated", "Planned"],
    ["First three-station lift", "Self-check, calibration, short move", "Not yet run", "None", "Planned"],
    ["Cost", "Hobby budget", "About $640 ordered; $220–260 in the robot (3–4 stations), prices partly estimated", "Receipts", "Met"],
  ], M, 1.3, W - 2 * M, [0.17, 0.22, 0.3, 0.12, 0.19], { size: 11, rowH: 0.34 });
  sl.addNotes("Talk track (55 s): Back to the targets, with the evidence for each. Measured so far: the claw mass, the two bench tests and the wiring. Three are not " +
              "met: grip for jeans at narrow grabs, claw mass at 0.60 against 0.45, and the weakest link, which has two cheap fixes. Two are marginal and the next " +
              "tests decide them: lift capacity, where the gear stage is the answer if the pull test comes in low, and the prototype fin's temperature. Planned: the " +
              "map of obstacles in the phone app is built and under independent verification, with two findings being fixed before it runs on hardware; and the " +
              "first three-station lift, which is the next milestone. If asked about the map: the user draws shapes on a top view of the room and every cable and " +
              "the claw body are checked against them before a move; the two findings are a descent that could enter a refused shape and a calibration detour that " +
              "strands the claw at the top of the workspace. Cost: about $640 ordered in total, $220 to $260 of it in the robot as parts for three or four " +
              "stations, plus $40 to $50 of filament; prices partly recorded, partly typical, so say 'about'. " +
              "If asked what narrow grabs are: a grip where the jaw tips are close together when the pads meet the cloth, a thin fold rather than a bunched " +
              "handful. The hands ride on a gear crank, so the lever arm from the crank to the pad is longest at a small gap, 59 mm at 10 mm, and shortest at " +
              "a wide one, 33 mm at 70 mm; with a fixed stall torque the pad force is 13.3 N at the narrowest grab and 25 N at 70 mm. Jeans at a friction of 0.3 " +
              "need 17.7 N, so the grip is short until the gap is at least 22 mm at 6 V (43 mm at 4.8 V). Requirement calculated; jaw force from the four-bar " +
              "model, no force gauge yet; grippy pads halve the need.");
}

{
  const sl = blank("What I would do first next time, and what happens next");
  const cw = [0.4, 0.6], lw = 7.3, x2 = M + lw + 0.5, rw = W - M - x2;
  table(sl, ["Good decision", "Result"], [
    ["One controller per winch", "Five times less wire; each station tested alone"],
    ["Camera calibration instead of bead homing", "Whole room reachable; caught on paper before building"],
    ["A mass budget per part", "The claw was weighed; the gear stage sized to the lift margin"],
  ], M, 1.3, lw, cw, { size: 13, rowH: 0.45, name: "good decisions" });
  table(sl, ["Poor decision", "Result"], [
    ["Mass not tracked through four claw versions", "v6 reached 4.6 times its budget in CAD; the claw is 0.15 kg over"],
    ["Prototype fin cut from scrap sheet", "Only 1–4 K of thermal margin"],
    ["Build and test week ending on presentation day", "System results arrive at the last minute"],
  ], M, 3.45, lw, cw, { size: 13, rowH: 0.45, headColor: HEX.red, name: "poor decisions" });
  bullets(sl, [
    "Half the time: pull-test one winch and weigh a mock claw in week 1; kill the central board, bead homing and the fingers on paper; prove one station first",
  ], M, 5.65, lw, 1.1, 14, { space: 6, name: "half time" });
  label(sl, "Next", x2, 1.3, rw, 0.4, { size: 18, bold: true, color: HEX.navy });
  bullets(sl, [
    "Flash and commission the three stations on the wall",
    "Pull test at 1.5 A; enter the measured limit in the planner",
    "First lift: self-check, calibration, a short move with 1 lb",
    "Then the robot scans its own room: height map and obstacle proposals in the app",
    "A brake or non-backdrivable stage, so a power loss cannot drop the claw",
    "A pole-clamp back for the wall mount (a gym-pole clamp), so a station mounts to a pole, not only a wall",
    "Open-source build on GitHub, so others can build it",
  ], x2, 1.8, rw, 5.0, 14, { space: 8, name: "next steps" });
  sl.addNotes("Talk track (55 s): Three decisions I would make again: a controller in every station, which is why the bench week worked station by station; " +
              "the camera calibration instead of bead homing, killed on paper before anything was built; and a mass budget per part, late, but it is why the " +
              "claw got weighed and the gear stage got sized. Three I would not: not re-checking the claw's mass through four versions; cutting the prototype fin " +
              "from scrap sheet, which left one to four degrees of margin; and a build week that ends on presentation day. In half the time I would pull-test one " +
              "winch and weigh a mock claw in week one and prove one full station before copying it. Next, in order: flash and commission the three stations, " +
              "the pull test, the first lift with a pound, and then the robot scans its own room and proposes the obstacles in the app. Two more: a pole-clamp back " +
              "for the wall mount, a gym-pole clamp, so a station can go on a pole where there is no stud; and the build goes up open-source on GitHub so others can build it. " +
              "Leave this slide up for questions. If asked: the lighter redesign takes about 60 % of the plastic out of the station and brings the claw to its " +
              "0.45 kg budget, lifting the jeans margin from 4 % to about 16 %. " +
              "If asked how the weaker decisions affected the deliverable: each shows up in the results table. Not tracking mass through four claw versions put " +
              "the claw at 0.60 kg against 0.45, which turned the jeans lift margin into 4 % and made the gear stage necessary before any jeans pickup; it is why " +
              "the demo load is 1 lb. Cutting the prototype fin from scrap sheet left 1 to 4 K of thermal margin at 1.5 A, so the stations cannot run at full " +
              "current until a hold test passes, with 1.35 A as the fallback. Ending the build week on presentation day means the first three-station lift, the " +
              "pull test and the hold test have no result on these slides: everything on the robot that moves a load is still planned. And building parts far " +
              "stronger than any load cost about 1.2 L of PETG and days of printing per station, which the lighter redesign takes back. " +
              "If asked why larger motors were not the answer when mass was the constraint: because the mass that matters is on the claw and the motors are on " +
              "the wall; a bigger motor adds nothing to the claw and removes nothing from it. What limits the lift is not the motor's size but the current I can " +
              "put through it and the heat that makes: pull rises with current, heat with current squared, so 1.0 to 1.5 A bought 50 % more pull for 2.25 times " +
              "the heat, and at 1.5 A the printed mount is already at its 60 °C limit. A larger motor would need more current, a bigger driver than the 2 A " +
              "A4988, a bigger supply than the 12 V 6 A brick, thicker wire for the 32 ft run and a new station. The 3:1 stage gives 2.7 times the pull at 1.0 A " +
              "with half the heat, for two printed gears and two bearings I already use, and it keeps the motor as the fuse of the lifting chain. The lever was " +
              "the ratio, not the motor; the other lever is mass off the claw. A larger motor was never on my options list; the options were a smaller spool core, " +
              "the gear stage, a lighter claw and a lighter payload.");
}

}

if (PART === "appendix") {
// ================================================================================================ APPENDIX (v8, plus the fits table and the schematics)
section("Appendix"); ACT = "Appendix";
{
  const sl = pres.addSlide({ masterName: "SECTION", sectionTitle: SECTION });
  sl.addText("Appendix", { x: M, y: 2.8, w: 11, h: 1.0, fontSize: 44, bold: true, color: "FFFFFF", fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addText("Fundamentals, safe state, fits, schematics", { x: M, y: 3.85, w: 11, h: 0.5, fontSize: 20, color: HEX.pale, fontFace: "Arial", margin: 0, isTextBox: true });
  sl.addNotes("");
}
{
  const sl = blank("Safe state and failure modes");
  table(sl, ["Event", "What happens", "Mitigation"], [
    ["PAUSE, or a fault the software detects", "Every station holds position with torque on", "Nothing moves again without approval"],
    ["Wi-Fi link lost", "Stations stop and hold on their own clocks", "Resume needs approval"],
    ["Power loss or emergency stop", "Torque is lost and the claw can fall (1.5 kg from about 2 m)", "Nobody underneath; claw parked low when idle; brake planned"],
    ["Controller reset or brown-out", "Driver disabled at boot, so torque is lost", "Same as power loss"],
    ["Driver over-temperature", "The A4988 shuts its outputs off", "Hold test watches the driver; fallback 1.35 A"],
    ["Three-station run: any station fault", "Every cable is needed; the claw falls", "Floor clear and padded; movement and calibration only"],
  ], M, 1.3, W - 2 * M, [0.26, 0.4, 0.34], { size: 14, rowH: 0.7 });
  sl.addNotes("The safe state is PAUSE: torque on, holding. Anything that removes power drops the claw, which is why nobody stands under it and why a brake or a " +
              "non-backdrivable stage is on the next-steps list.");
}

content("Heat fin length", [
  "0.019 in prototype reaches 95 % of its capacity by 136 mm",
  "1/8 in design keeps gaining to 349 mm",
  "Built at 200 mm, limited by ceiling clearance",
], { sheet: "heat_fin", tab: "Heat fin" },
"L95 is where a fin carries 95 % of the heat an infinitely long one would. h = 7 W/m²·K still air, k = 160 W/m·K aluminum. Source: Incropera, ch. 3.",
{ tags: ["CALCULATED"], eq: { title: "Fin length and efficiency", lines: [
  "m = √(2h / (k t)),   L_{95} = 1.83 / m",
  "η = tanh(mL) / (mL) = **0.74** (1/8 in)",
] } });

content("Fin sizing for 4 W", [
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
}, "The prototype works today only because the motor also sheds heat into the vented shell. Thickness beats length.", { tags: ["CALCULATED"] });

content("Floor board accuracy", [
  "Camera pose error per frame, best case: 6.6 mm with one tag, 0.7 mm with four",
  "This is the camera's view, not the cable length",
  "After the fit, cable lengths are known to about 12–16 mm (simulated)",
], { sheet: "floor_board", tab: "Floor board" },
"Noise model: 0.3 px corner noise and a 520 px focal length (camera not yet calibrated). The four-tag figure is the best placement; realistic placements are a few times worse.",
{ tags: ["SIMULATED"] });

content("Operating sequence", [
  "Start up: self-check, take up slack, calibrate",
  "Find: scan from above, detect garments, choose the nearest",
  "Pick: hover until still, grip, deliver; the camera confirms each step",
  "Every move waits for approval on the phone; PAUSE holds position",
], { file: [P("docs/app_screenshots/01_home.png"), P("docs/app_screenshots/02_camera.png"), P("docs/app_screenshots/04_chat.png")],
     alt: "Phone app screens", caption: "Phone app in simulation: home, claw camera and chat" },
"PAUSE or a detected fault stops every station on the same point of the path, still holding; nothing restarts by itself. The emergency stop is the switched power strip, " +
"and it drops the claw. Known obstacles are keep-out shapes checked against every cable before a move. Simulated end to end.", { tags: ["SIMULATED"] });

{
  const sl = blank("Control logic: Generation 1 vs. final");
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

{
  // Manufacturing fits table (v8 main slide, kept on file). Numbers measured from Jasper's STEP files; snapshots are shaded views of his parts.
  const sl = blank("Manufacturing: fits and datums");
  const fx = M, fw = 6.2, bx = fx + fw + 0.3, bw = W - M - bx;
  const tiles = [
    ["snap_gear_lip.png", "Gear: Ø14.000 entry lip, 8 T-slots"],
    ["snap_gear_stack.png", "Cut open: 687 bearing on the printed pin"],
    ["snap_dovetail.png", "Slide-in rib in the wall-mount dovetail"],
    [PH("23_slide_in_switch_pressfit.jpg"), "End-stop switch pressed into the slide-in"],
    ["snap_spool.png", "v3 spool: D-bore and set-screw hole"],
    [PH("01_mill_drilling_fin_closeup.jpg"), "Fin: holes drilled from the first hole"],
  ];
  const tw = (fw - 0.12) / 2, th = 1.5, rowH = th + 0.3;
  tiles.forEach(([f, cap], i) => {
    const x = fx + (i % 2) * (tw + 0.12), y = 1.2 + Math.floor(i / 2) * rowH;
    const file = path.isAbsolute(f) ? f : path.join(V8FIG, f);
    sl.addShape(pres.shapes.RECTANGLE, { x, y, w: tw, h: th, fill: { color: "FFFFFF" }, line: { color: HEX.rule, width: 0.75 }, objectName: "tile frame" });
    fitImage(sl, file, x + 0.02, y + 0.02, tw - 0.04, th - 0.04, cap);
    sl.addText(cap, { x, y: y + th + 0.02, w: tw, h: 0.24, fontSize: 10.5, color: HEX.mid, fontFace: "Arial", margin: 0, isTextBox: true, objectName: "tile caption" });
  });
  caption(sl, "My SolidWorks parts; blue and tan are cut faces, dark grey the bought bearing", fx, 6.6, fw);
  table(sl, ["Feature", "As drawn", "Fit"], [
    ["Gear bearings (687)", "Ø14.075 pocket behind a Ø14.000 lip, 1.95 long, 8 T-slots", "Snaps past the lip, +0.075 behind it"],
    ["Gear pins", "Printed Ø7.000 pin into a Ø7.05 socket", "Line-to-line in the bearing; +0.05"],
    ["Slide-in mount", "0.175 per side; 30° dovetail flanks", "Slip fit, 0.14–0.21 on the flanks"],
    ["Spool on Ø5 D-shaft", "Ø5.30 bore (10/21), Ø5.45 in v3; 0.5 mm flat", "+0.30 to +0.45: Ø5.2 printed too tight"],
    ["End-stop switch", "Pocket 6.65 × 20.3 × 9 on a 1 mm ledge, lever window below", "Press fit, no screws"],
    ["Heat-set inserts", "M3: Ø4.0 × 5 gear housing; M2.5: Ø3.45 × 4 encoder", "Melt-in; hole deeper than the insert"],
    ["Screw clearance", "M3 Ø3.5 printed, Ø3.4 drilled; wall Ø3.97 (5/32 in)", "+0.5 printed, +0.4 drilled"],
    ["Motor pilot, Ø22 boss", "Ø22.4 printed tab, Ø22.5 drilled fin", "+0.4 / +0.5"],
    ["Fin hole zero", "Edges locate the bottom-left hole; drilled, it is the zero for the other 4", "Pattern ±0.1, free of the ±0.5 sheared edges"],
  ], bx, 1.25, bw, [0.25, 0.44, 0.31], { size: 10.5, rowH: 0.44, name: "fits" });
  bullets(sl, [
    "Printed holes come out small, so every printed fit carries an allowance; the drilled fin needs none",
    "PETG on a Creality K1, 0.4 mm nozzle, 0.2 mm layers; loads along the layers, mating faces off supports",
  ], bx, 5.85, bw, 0.95, 12, { space: 4, name: "printing rules" });
  sl.addNotes("The gear pockets: the bearing presses past a lip, the T-slots let the lip ends flex, and it then sits free in a pocket 0.075 mm larger. " +
              "The slide-in runs on 0.175 mm a side. The fin's sheared edges are only good to half a millimetre, so they locate only the first hole; the rest " +
              "are drilled from it. [[confirm which spool bore is printed, which holes get heat-set inserts, and the insert part number]] " +
              "If asked which feature each fit belongs to, row by row: gear bearings are the 687 ball bearings in the claw's gear housing, a Ø14.075 pocket behind " +
              "a Ø14.000 entry lip with eight T-slots so the lip flexes as the bearing snaps past. Gear pins are the printed Ø7 pins the claw gears turn on, into " +
              "Ø7.05 sockets. Slide-in mount is the station housing's dovetail ribs in the wall-mount grooves, 0.175 mm a side on 30° flanks. Spool on the " +
              "D-shaft is the winch spool's bore on the motor's 5 mm D-flat shaft, Ø5.45 after Ø5.2 printed too tight. End-stop switch is the homing switch " +
              "pressed into a pocket in the station slide-in. Heat-set inserts: M3 in the claw gear housing, M2.5 at the station encoder board. Screw clearance: " +
              "M3 holes in the printed parts and the drilled fin, and the #6 wall-screw holes in the wall mount. Motor pilot is the NEMA 17's Ø22 boss through " +
              "the printed motor tab and the drilled fin. Fin hole zero is the datum scheme for drilling the fin: the first hole from the sheared edges, the other " +
              "four from it. All measured from my parts' CAD files and my fin method.");
}

content("Station electronics, Rev D", [
  "One board per station: a Wi-Fi microcontroller, the A4988 driver, a 12 V to 5 V buck, the homing switch and the spool encoder",
  "Pull-up on ENABLE keeps the driver off at boot; pull-downs on STEP and DIR; a 100 µF reservoir at the driver supply",
  "Fuses at the source end of each 12 V branch; the buck is rated to 20 V in, so the supply stays at 12 V",
], { file: R("kicad_station_revD.png"), alt: "Station Rev D schematic", caption: "Station Rev D schematic" },
"The external 10k pull-up on ENABLE is the reason a reset cannot move a motor; it is also why disabling removes torque, so the pull-up cannot hold a suspended load. " +
"The bench script on the Act 5 slide checks each part of this board in turn.", { figW: 7.6, size: 15 });

content("Station breadboard layout", [
  "The bench build of Rev D on a mini breadboard: the layout was net-checked against the schematic (PASS) before power",
  "Each motor coil carries about 1 A through breadboard contacts: short leads, fully seated",
  "The soldered perfboard and the rail board follow the same net list",
], { file: P("docs/electrical/station_revD_20261021/breadboard_layout.png"), alt: "Station breadboard layout", caption: "Station Rev D breadboard layout, drawn and net-checked" },
"The second bench board (the larger dev module) uses the same layout with the module off the board and nine jumpers into the holes of the small board.", { figW: 7.6, size: 15 });

content("Claw electrical, Rev B", [
  "Two-cell lithium-ion pack, 7.4 V; 5 A fuse for shorts",
  "6 V servo rail and a separate 5 V logic rail; 200k/100k divider for battery sense",
  "Peak draw 2.8–3.1 A, at the pack's 3 A rating",
], { file: R("kicad_claw_revB.png"), alt: "Claw schematic", caption: "Claw Rev B schematic" },
"Rules check 0 errors; 9 nets match the specification. Charger: 8.4 V constant current, constant voltage; charged attended, at 1 A or less. " +
"The peak sits at the pack rating, so a stall longer than a moment is the thing to watch. On the bench (10/26): live view, 7.2 V battery read, servo moves once it had its own timer.",
{ figW: 7.6 });

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

content("Calculations and sources", [
  "All charts come from my engineering calculation sheet",
  "Incropera et al., Fundamentals of Heat and Mass Transfer, ch. 3",
  "Allegro MicroSystems, A4988 datasheet",
], { sheet: "cable_tension", tab: "Cable tension" }, "");

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
