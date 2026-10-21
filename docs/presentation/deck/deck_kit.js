// Shared visual system for the interview deck ("Flight Test Report").
//
// Copied from docs/presentation/deck_assets/build_style_sampler.js (THEME, four layouts,
// helpers tag(), rail(), callout(), photo(), render()) and extended for the real deck:
//   - photo() keeps the picture's aspect ratio (cover crop with a focus point) and returns a
//     mapper so callouts can be placed on image fractions;
//   - railV(): the same WANTED / REALIZED / DECIDED / RESULT / BUT rail as a vertical ledger
//     beside the hero image, one short line per step, active step in Signal;
//   - fundBox(), plannedCard(), limitLine(), chartOpts(), mat() and a few small text helpers.
// The sampler itself is left untouched; this module is what build_deck.js imports.
//
// Style rules: docs/presentation/STYLE_GUIDE.md.

"use strict";

const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const { imageSize } = require("image-size");

const ROOT = path.resolve(__dirname, "../../..");
const P = (...p) => path.join(ROOT, ...p);
const PHOTO = (n) => P("docs/presentation/photos", n);
const RENDER = (n) => P("docs/presentation/deck_assets/renders", n);

const HEX = { ink: "0E1116", paper: "FFFFFF", fog: "E9ECEF", steel: "6B7480", signal: "FF6A13", tint: "FFE6D6", steelLight: "A9B0B8" };

const THEME = {
  name: "Flight Test Report",
  headFontFace: "Arial",
  bodyFontFace: "Calibri",
  colors: {
    dk1: HEX.ink, lt1: HEX.paper, dk2: HEX.steel, lt2: HEX.fog,
    accent1: HEX.signal, accent2: HEX.steel, accent3: HEX.ink, accent4: HEX.steelLight, accent5: HEX.tint, accent6: "3A414B",
    hlink: HEX.signal, folHlink: HEX.steel,
  },
};

const W = 13.333, H = 7.5, M = 0.6;

// Grid of a decision slide: hero + fundamentals/planned card on the left, rail on the right.
const GRID = {
  LX: M, LW: 5.4,                     // left column (hero)
  RX: 6.4, RW: W - M - 6.4,           // right column (rail + fundamentals box)
  TOP: 1.95, BOT: 6.85,               // content band
  PITCH: 0.70,                        // rail row height
  PLANNED_H: 0.78,                    // height of the PLANNED card when present
};

const RAIL = ["WANTED", "REALIZED", "DECIDED", "RESULT", "BUT"];

function createKit(deckTitle) {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.author = "Jasper Buntinx";
  pres.title = deckTitle;
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;
  // C.text1 = ink, C.text2 = steel, C.background1 = paper, C.background2 = fog, C.accent1 = signal, C.accent5 = tint

  // ---------------------------------------------------------------- layouts
  const footer = () => [
    { text: { text: "ROOMCLEANER", options: { x: M, y: H - 0.45, w: 4, h: 0.3, fontSize: 9, bold: true, charSpacing: 1.5, color: C.text2, margin: 0 } } },
  ];
  const slideNum = { x: W - M - 1, y: H - 0.45, w: 1, h: 0.3, fontSize: 9, color: C.text2, align: "right", margin: 0 };

  pres.defineSlideMaster({
    title: "Dark Title",
    background: { color: C.text1 },
    objects: [
      { placeholder: { options: { align: "left", name: "title", type: "title", x: M, y: 2.1, w: 5.6, h: 2.0, fontSize: 44, bold: true, color: C.background1, valign: "bottom", margin: 0 }, text: "Title" } },
      { placeholder: { options: { align: "left", name: "subtitle", type: "body", x: M, y: 4.3, w: 5.4, h: 1.2, fontSize: 18, color: HEX.steelLight, valign: "top", margin: 0 }, text: "Subtitle" } },
      { placeholder: { options: { align: "left", name: "byline", type: "body", x: M, y: H - 1.1, w: 5.4, h: 0.4, fontSize: 12, color: C.text2, margin: 0 }, text: "Name · date" } },
    ],
  });

  pres.defineSlideMaster({
    title: "Dark Section",
    background: { color: C.text1 },
    objects: [
      { placeholder: { options: { align: "left", name: "number", type: "body", x: M, y: 1.5, w: 4, h: 2.2, fontSize: 140, bold: true, fontFace: "Arial", color: C.accent1, valign: "bottom", margin: 0 }, text: "01" } },
      { placeholder: { options: { align: "left", name: "title", type: "title", x: M, y: 3.9, w: 9, h: 1.2, fontSize: 36, bold: true, color: C.background1, valign: "top", margin: 0 }, text: "Section claim" } },
      { placeholder: { options: { align: "left", name: "body", type: "body", x: M, y: 5.3, w: 8, h: 0.8, fontSize: 16, color: HEX.steelLight, valign: "top", margin: 0 }, text: "One line on what this act covers" } },
    ],
    slideNumber: { ...slideNum, color: C.text2 },
  });

  pres.defineSlideMaster({
    title: "Content",
    background: { color: C.background1 },
    margin: [M, M, 0.6, M],
    objects: [
      { placeholder: { options: { align: "left", name: "eyebrow", type: "body", x: M, y: 0.45, w: 9, h: 0.3, fontSize: 11, bold: true, fontFace: "Arial", charSpacing: 1.5, color: C.text2, margin: 0 }, text: "EYEBROW" } },
      { placeholder: { options: { align: "left", name: "title", type: "title", x: M, y: 0.8, w: W - 2 * M - 1.9, h: 1.05, fontSize: 30, bold: true, color: C.text1, valign: "top", margin: 0 }, text: "Claim title" } },
      ...footer(),
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
    MEASURED:   () => ({ fill: { color: C.text1 }, line: { color: C.text1, width: 1 }, color: C.background1 }),
    CALCULATED: () => ({ fill: { color: C.background1 }, line: { color: C.text1, width: 1 }, color: C.text1 }),
    SIMULATED:  () => ({ fill: { color: C.background1 }, line: { color: C.text2, width: 1, dashType: "dash" }, color: C.text2 }),
    PLANNED:    () => ({ fill: { color: C.background2 }, line: { color: C.background2, width: 1 }, color: C.text2 }),
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

  /** One or two evidence pills stacked at the top-right (kinds: array of tag names). */
  function tags(slide, kinds) {
    kinds.forEach((k, i) => tag(slide, k, W - M - 1.45, 0.47 + i * 0.36));
  }

  /** Decision rail across the bottom (original horizontal helper: dots and labels only). */
  function rail(slide, active, y = H - 1.15) {
    const x0 = M, x1 = W - M, step = (x1 - x0) / RAIL.length;
    slide.addShape(pres.shapes.LINE, { x: x0 + 0.14, y: y + 0.14, w: x1 - x0 - step, h: 0, line: { color: C.background2, width: 2 }, objectName: "rail_line" });
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

  /**
   * Vertical decision rail, one short line per step, beside the hero image.
   * items: five strings (WANTED, REALIZED, DECIDED, RESULT, BUT); active: 0..4 (Signal);
   * steps before it are Ink, steps after it Fog dots with Steel labels. Every line stays Ink
   * so all five remain legible at presentation distance.
   */
  function railV(slide, items, active, x, y, w, pitch = GRID.PITCH) {
    const dot = 0.28;
    slide.addShape(pres.shapes.LINE, { x: x + dot / 2, y: y + pitch / 2, w: 0, h: pitch * (items.length - 1), line: { color: C.background2, width: 2 }, objectName: "railv_line" });
    items.forEach((txt, i) => {
      const done = i < active, cur = i === active;
      const yi = y + i * pitch;
      if (i > 0) slide.addShape(pres.shapes.LINE, { x: x + 0.42, y: yi, w: w - 0.42, h: 0, line: { color: C.background2, width: 0.75 }, objectName: `railv_sep_${i}` });
      const fill = cur ? C.accent1 : done ? C.text1 : C.background2;
      slide.addText(String(i + 1), {
        shape: pres.shapes.OVAL, x, y: yi + (pitch - dot) / 2, w: dot, h: dot, fill: { color: fill }, line: { color: fill, width: 0.75 },
        color: cur || done ? C.background1 : C.text2, fontSize: 9, bold: true, fontFace: "Arial", align: "center", valign: "middle", margin: 0,
        isTextBox: true, objectName: `rail_dot_${i + 1}`,
      });
      slide.addText(RAIL[i], {
        x: x + 0.42, y: yi, w: 1.15, h: pitch, fontSize: 10, bold: true, fontFace: "Arial", charSpacing: 1.2,
        color: cur ? C.accent1 : done ? C.text1 : C.text2, margin: 0, valign: "middle", isTextBox: true, objectName: `rail_label_${i + 1}`,
      });
      slide.addText(txt, {
        x: x + 1.6, y: yi, w: w - 1.6, h: pitch, fontSize: 15, bold: cur, color: C.text1, margin: 0, valign: "middle",
        isTextBox: true, objectName: `rail_text_${i + 1}`,
      });
    });
  }

  /** Dimension callout: Signal dot on the feature (fx,fy), leader to a label at (lx,ly). */
  function callout(slide, fx, fy, lx, ly, label, align = "left") {
    const x = Math.min(fx, lx), y = Math.min(fy, ly);
    slide.addShape(pres.shapes.LINE, { x, y, w: Math.abs(lx - fx), h: Math.abs(ly - fy), flipV: (lx < fx) !== (ly < fy), line: { color: C.text1, width: 1 }, objectName: `callout_line_${label}` });
    slide.addShape(pres.shapes.OVAL, { x: fx - 0.06, y: fy - 0.06, w: 0.12, h: 0.12, fill: { color: C.accent1 }, line: { color: C.background1, width: 1 }, objectName: `callout_dot_${label}` });
    const lw = 0.1 * label.length + 0.3;
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

  function caption(slide, text, x, y, w, h = 0.3) {
    slide.addText(text, { x, y, w, h, fontSize: 11, italic: true, color: C.text2, margin: 0, valign: "top", isTextBox: true });
  }

  function eyebrowLabel(slide, text, x, y, w, color) {
    slide.addText(text, { x, y, w, h: 0.22, fontSize: 10, bold: true, fontFace: "Arial", charSpacing: 1.5, color: color || C.text2, margin: 0, isTextBox: true });
  }

  /** Fog mat behind a render. */
  function mat(slide, x, y, w, h, name = "mat") {
    slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: C.background2 }, line: { color: C.background2, width: 0.5 }, objectName: name });
  }

  /** Place a transparent render at height h (width from the PNG header). Returns the width. */
  function render(slide, file, x, y, h, name) {
    const dim = imageSize(fs.readFileSync(RENDER(file)));
    const w = h * dim.width / dim.height;
    slide.addImage({ path: RENDER(file), x, y, w, h, altText: name, objectName: name });
    return w;
  }

  /** Render fitted inside a box (centred). Returns {x,y,w,h} actually used. */
  function renderFit(slide, file, bx, by, bw, bh, name) {
    const dim = imageSize(fs.readFileSync(RENDER(file)));
    const ar = dim.width / dim.height;
    let w = bw, h = bw / ar;
    if (h > bh) { h = bh; w = bh * ar; }
    const x = bx + (bw - w) / 2, y = by + (bh - h) / 2;
    slide.addImage({ path: RENDER(file), x, y, w, h, altText: name, objectName: name });
    return { x, y, w, h };
  }

  /**
   * Photo, cover-cropped to the box without distortion. focus = {fx, fy} in image fractions
   * (the crop window is centred on it where possible); zoom >= 1 crops tighter.
   * Returns map(nx, ny) -> slide inches for placing callouts on image fractions (or null if cropped out).
   */
  function photo(slide, file, x, y, w, h, name, opts = {}) {
    const abs = file.startsWith("/") ? file : PHOTO(file);
    const dim = imageSize(fs.readFileSync(abs));
    const { fx = 0.5, fy = 0.5, zoom = 1 } = opts;
    const scale = Math.max(w / dim.width, h / dim.height) * zoom;   // inches per pixel
    const iw = dim.width * scale, ih = dim.height * scale;
    const cx = Math.min(Math.max(fx * iw - w / 2, 0), iw - w);
    const cy = Math.min(Math.max(fy * ih - h / 2, 0), ih - h);
    slide.addImage({ path: abs, x, y, w: iw, h: ih, sizing: { type: "crop", x: cx, y: cy, w, h }, altText: name, objectName: name });
    return (nx, ny) => {
      const px = nx * iw - cx, py = ny * ih - cy;
      if (px < 0 || py < 0 || px > w || py > h) return null;
      return [x + px, y + py];
    };
  }

  /** Fundamentals box: label, equation (Cambria) and the numbers substituted. Optional big number cell. */
  function fundBox(slide, f, x, y, w, h) {
    slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: C.background2 }, line: { color: C.background2, width: 0.5 }, objectName: "fund_box" });
    eyebrowLabel(slide, "FUNDAMENTALS", x + 0.2, y + 0.1, 3);
    let ex = x + 0.2, ew = w - 0.4;
    if (f.big) {
      const bw = f.bigW || 2.3;
      slide.addText(f.big, { x: x + 0.2, y: y + 0.3, w: bw, h: 0.5, fontSize: 28, bold: true, fontFace: "Arial", color: C.accent1, margin: 0, valign: "middle", isTextBox: true, objectName: "fund_big" });
      slide.addText(f.bigLabel || "", { x: x + 0.2, y: y + 0.82, w: bw, h: h - 0.9, fontSize: 11, color: C.text2, margin: 0, valign: "top", isTextBox: true, objectName: "fund_big_label" });
      ex = x + 0.2 + bw + 0.2; ew = w - (ex - x) - 0.2;
    }
    const eqSize = f.eqSize || (f.eq.length > 44 && !f.big ? 16 : f.big ? 15 : 18);
    slide.addText(f.eq, { x: ex, y: y + 0.3, w: ew, h: f.big ? 0.42 : 0.4, fontSize: eqSize, fontFace: "Cambria", color: C.text1, margin: 0, valign: "middle", isTextBox: true, objectName: "fund_eq" });
    slide.addText(f.sub, { x: ex, y: y + (f.big ? 0.74 : 0.72), w: ew, h: h - (f.big ? 0.8 : 0.78), fontSize: 13, fontFace: "Cambria", color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: "fund_sub" });
  }

  /** Clearly marked placeholder for a result that does not exist yet. Never holds a number. */
  function plannedCard(slide, line2, x, y, w, h = GRID.PLANNED_H, head = "PLANNED — result after the Oct 22 test") {
    slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: C.background2 }, line: { color: C.text2, width: 1, dashType: "dash" }, objectName: "planned_card" });
    slide.addText(head, { x: x + 0.2, y: y + 0.07, w: w - 0.4, h: 0.28, fontSize: 12, bold: true, fontFace: "Arial", color: C.text1, margin: 0, valign: "middle", isTextBox: true, objectName: "planned_head" });
    slide.addText(line2, { x: x + 0.2, y: y + 0.37, w: w - 0.4, h: h - 0.42, fontSize: 12, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: "planned_text" });
  }

  /**
   * Dashed limit/target line across a native chart's plot area, with a label.
   * plot = absolute inches of the chart's inner plot area; value is on the value axis (0..axisMax).
   */
  function limitLine(slide, plot, axisMax, value, label, o = {}) {
    const y = plot.y + plot.h * (1 - value / axisMax);
    slide.addShape(pres.shapes.LINE, { x: plot.x, y, w: plot.w, h: 0, line: { color: o.color || C.text1, width: 1.25, dashType: "dash" }, objectName: `limit_${label}` });
    const lw = o.labelW || (0.085 * label.length + 0.3);
    slide.addText(label, {
      x: o.align === "left" ? plot.x + 0.05 : plot.x + plot.w - lw - 0.03, y: o.below ? y + 0.03 : y - 0.27, w: lw, h: 0.24,
      fontSize: 11, bold: true, fontFace: "Arial", color: o.color || C.text1, align: o.align === "left" ? "left" : "right", valign: "middle", margin: 0, isTextBox: true, objectName: `limit_label_${label}`,
    });
  }

  /** Quiet native-chart options in the deck's style; merge per-chart options on top. */
  function chartOpts(o) {
    return Object.assign({
      showLegend: false, showTitle: false,
      catAxisLabelColor: HEX.steel, catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", catAxisLineShow: true, catAxisLineColor: HEX.steelLight,
      valAxisLabelColor: HEX.steel, valAxisLabelFontSize: 11, valAxisLabelFontFace: "+mn-lt", valAxisLineShow: false,
      valGridLine: { color: HEX.fog, size: 0.75 }, catGridLine: { style: "none" },
      dataLabelColor: HEX.ink, dataLabelFontFace: "+mn-lt", dataLabelFontSize: 12, dataLabelFontBold: true,
      legendFontFace: "+mn-lt", legendFontSize: 12, legendColor: HEX.ink,
      valAxisTitleFontFace: "+mn-lt", valAxisTitleFontSize: 12, valAxisTitleColor: HEX.steel,
      catAxisTitleFontFace: "+mn-lt", catAxisTitleFontSize: 12, catAxisTitleColor: HEX.steel,
    }, o);
  }

  /** Absolute inches of a chart's inner plot area given the chart box and its fractional layout. */
  function plotRect(box, layout) {
    return { x: box.x + layout.x * box.w, y: box.y + layout.y * box.h, w: layout.w * box.w, h: layout.h * box.h };
  }

  return { pres, C, tag, tags, rail, railV, callout, body, caption, eyebrowLabel, mat, render, renderFit, photo, fundBox, plannedCard, limitLine, chartOpts, plotRect };
}

module.exports = { createKit, THEME, HEX, W, H, M, ROOT, P, PHOTO, RENDER, RAIL, GRID };
