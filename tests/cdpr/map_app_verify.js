// INDEPENDENT browser verification of the Map tab (docs/ROOM_MAP_SPEC.md 1, 5), driven by tests/cdpr/test_room_map_app_verify.py:
//   node map_app_verify.js <base url> <token> <width> <height> <scheme light|dark> <screenshot dir>
// Prints ONE JSON line of measurements; the Python test makes the assertions and writes the evidence.
// Written by the verifier (not the builder). It drives the page like a user (mouse, and real touch events through CDP on the
// phone sizes) and reads the app's draft state (the page's global `M`) only to check what an action did.
const { chromium } = require("playwright");
const [base, token, W, H, scheme, shots] = process.argv.slice(2);
const w = +W, h = +H, phone = w < 600;

const BANNED = /keep[- ]?out|violation|coverage|obstacle|z_low|height_m|length_m|width_m|diameter_m|yaw_deg/i;

// ------------------------------------------------------------------ in-page probes
function probeLayout() {
  const vis = el => { if (!el) return false; const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none" && el.offsetParent !== null; };
  const inView = r => r.top >= -0.5 && r.bottom <= innerHeight + 0.5 && r.left >= -0.5 && r.right <= innerWidth + 0.5;
  const topAt = el => { const r = el.getBoundingClientRect();
    return [[0.5, 0.5], [0.15, 0.5], [0.85, 0.5]].every(([fx, fy]) => { const e = document.elementFromPoint(r.left + r.width * fx, r.top + r.height * fy); return !!e && (e === el || el.contains(e)); }); };
  const p = document.getElementById("pause"), s = document.querySelector(".estop");
  const tm = document.getElementById("tab-map");
  return { state: document.getElementById("topState").textContent, pause: vis(p) && inView(p.getBoundingClientRect()) && topAt(p), estop: vis(s) && inView(s.getBoundingClientRect()) && topAt(s),
           scrollW: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth), innerW: innerWidth,
           tabScrollW: tm.scrollWidth, tabClientW: tm.clientWidth };
}

function probeTargets() {     // every visible interactive control on the Map tab (and the tab bar): its box
  const out = [];
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && el.offsetParent !== null
    && !(el.closest("details:not([open])") && el.tagName !== "SUMMARY"); };
  const sel = "#tab-map button, #tab-map input:not([type=checkbox]), #tab-map summary, #tab-map label.chk, #tabs button";
  for (const el of document.querySelectorAll(sel)) {
    if (!vis(el)) continue;
    const r = el.getBoundingClientRect();
    out.push({ what: (el.id ? "#" + el.id : el.tagName.toLowerCase() + (el.className ? "." + String(el.className).split(" ")[0] : "")) + " " + (el.textContent || el.getAttribute("aria-label") || "").trim().slice(0, 30),
               w: Math.round(r.width * 10) / 10, h: Math.round(r.height * 10) / 10 });
  }
  for (const el of document.querySelectorAll("#map circle.hit")) { const r = el.getBoundingClientRect(); out.push({ what: "handle " + el.dataset.handle, w: r.width, h: r.height }); }
  for (const el of document.querySelectorAll("#map .shape")) { const r = el.getBoundingClientRect(); out.push({ what: "shape body " + el.dataset.id, w: r.width, h: r.height, shape: true }); }
  return out;
}

function probeText() {        // all text a user can see on the Map tab (incl. the SVG labels and the message line)
  const tm = document.getElementById("tab-map");
  const svgT = [...document.querySelectorAll("#map text")].map(t => t.textContent);
  return { text: tm.innerText + "\n" + svgT.join("\n"), toast: (document.getElementById("toast").hidden ? "" : document.getElementById("toast").innerText),
           tabs: document.getElementById("tabs").innerText };
}

function probeContrast() {    // HTML text: computed colour vs the first opaque ancestor background (alpha-composited)
  const parse = c => { const m = (c || "").match(/[\d.]+/g); if (!m) return null; const v = m.map(Number); return { r: v[0], g: v[1], b: v[2], a: v.length > 3 ? v[3] : 1 }; };
  const lum = c => { const f = x => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const over = (fg, bg) => ({ r: fg.r * fg.a + bg.r * (1 - fg.a), g: fg.g * fg.a + bg.g * (1 - fg.a), b: fg.b * fg.a + bg.b * (1 - fg.a), a: 1 });
  const bgOf = el => { const stack = []; for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0) { stack.push(c); if (c.a >= 1) break; } }
    let bg = stack.length && stack[stack.length - 1].a >= 1 ? stack.pop() : parse(getComputedStyle(document.body).backgroundColor);
    while (stack.length) bg = over(stack.pop(), bg); return bg; };
  const out = [];
  const walker = document.createTreeWalker(document.getElementById("tab-map"), NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while (walker.nextNode()) {
    const n = walker.currentNode, el = n.parentElement;
    if (!n.textContent.trim() || !el || seen.has(el) || el.closest("svg")) continue;
    const r = el.getBoundingClientRect();
    if (!(r.width > 0 && r.height > 0) || el.offsetParent === null) continue;
    seen.add(el);
    const s = getComputedStyle(el);
    let fg = parse(s.color);
    const bg = bgOf(el);
    if (fg.a < 1) fg = over(fg, bg);
    const op = parseFloat(s.opacity);
    out.push({ text: n.textContent.trim().slice(0, 40), ratio: Math.round(ratio(fg, bg) * 100) / 100, size: s.fontSize, weight: s.fontWeight, disabled: !!el.closest("button:disabled") });
  }
  // placeholder text of the inputs
  for (const inp of document.querySelectorAll("#tab-map input[placeholder]")) {
    if (inp.offsetParent === null || !inp.placeholder || inp.value) continue;
    const c = parse(getComputedStyle(inp, "::placeholder").color);
    if (c) out.push({ text: "placeholder " + inp.placeholder, ratio: Math.round(ratio(c.a < 1 ? over(c, bgOf(inp)) : c, bgOf(inp)) * 100) / 100, placeholder: true });
  }
  return out;
}

function probeLabels() {      // SVG labels: boxes (screen px), overlaps between them, and whether a label leaves the drawing
  const svg = document.getElementById("map").getBoundingClientRect();
  const ts = [...document.querySelectorAll("#map text")].map(t => { const r = t.getBoundingClientRect();
    return { text: t.textContent, cls: t.getAttribute("class"), x0: r.left, y0: r.top, x1: r.right, y1: r.bottom, fill: getComputedStyle(t).fill }; });
  const ov = [];
  for (let i = 0; i < ts.length; i++) for (let j = i + 1; j < ts.length; j++) {
    const a = ts[i], b = ts[j];
    const ix = Math.min(a.x1, b.x1) - Math.max(a.x0, b.x0), iy = Math.min(a.y1, b.y1) - Math.max(a.y0, b.y0);
    if (ix > 0.5 && iy > 0.5) ov.push({ a: a.text, b: b.text, overlap_px: [Math.round(ix), Math.round(iy)] });
  }
  const clipped = ts.filter(t => t.x0 < svg.left - 0.5 || t.x1 > svg.right + 0.5).map(t => t.text);
  return { labels: ts, overlaps: ov, clipped, svg: { x0: svg.left, y0: svg.top, x1: svg.right, y1: svg.bottom } };
}

// ------------------------------------------------------------------ driver
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, hasTouch: phone, colorScheme: scheme, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const cdp = phone ? await ctx.newCDPSession(page) : null;
  const out = { w, h, scheme, steps: [], errors: [], notes: [] };
  page.on("pageerror", e => out.errors.push(String(e)));
  const layout = async label => out.steps.push({ label, ...(await page.evaluate(probeLayout)) });
  out.labelShots = {};
  const labelShot = async name => {      // scroll to the top, record the SVG label boxes, then the screenshot they refer to
    await page.evaluate(() => { document.getElementById("tab-map").scrollTop = 0; });
    await page.waitForTimeout(50);
    const L = await page.evaluate(probeLabels);
    const file = `${shots}/${name}_${w}x${h}_${scheme}.png`;
    await page.screenshot({ path: file });
    out.labelShots[name] = { file, labels: L.labels };
  };
  const shot = async name => { if (shots) await page.screenshot({ path: `${shots}/${name}_${w}x${h}_${scheme}.png` }); };
  const draft = () => page.evaluate(() => JSON.parse(JSON.stringify(M.shapes)));
  const sel = () => page.evaluate(() => M.sel);
  const center = async loc => { const b = await loc.boundingBox(); return [b.x + b.width / 2, b.y + b.height / 2]; };
  let taps = 0;
  const tap = async loc => { taps++; await loc.scrollIntoViewIfNeeded(); if (phone) await loc.tap(); else await loc.click(); };
  const touchDrag = async (from, to, n = 12) => {        // a real finger drag (pointerType "touch")
    await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: from[0], y: from[1] }] });
    for (let k = 1; k <= n; k++) {
      await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: from[0] + (to[0] - from[0]) * k / n, y: from[1] + (to[1] - from[1]) * k / n }] });
      await page.waitForTimeout(16);
    }
    await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    await page.waitForTimeout(50);
  };
  const mouseDrag = async (from, to, n = 12) => {
    await page.mouse.move(from[0], from[1]); await page.mouse.down();
    for (let k = 1; k <= n; k++) await page.mouse.move(from[0] + (to[0] - from[0]) * k / n, from[1] + (to[1] - from[1]) * k / n);
    await page.mouse.up(); await page.waitForTimeout(30);
  };
  const drag = (a, b, n) => phone ? touchDrag(a, b, n) : mouseDrag(a, b, n);
  const phase = async (name, fn) => { try { await fn(); } catch (e) { out.errors.push(`${name}: ${String(e && e.stack || e).slice(0, 600)}`); } };
  const typeInto = async (label, text, enter = true) => {
    const f = page.locator(`#insp input[aria-label="${label}"]`).first();
    await f.scrollIntoViewIfNeeded();
    await f.fill(text);
    if (enter) await f.press("Enter"); else await f.dispatchEvent("change");
    await page.waitForTimeout(30);
  };

  // test hook (no product change): app.js is an IIFE, so the served copy gets one extra line at its end that exposes the draft
  // state and a few functions on window, for SETUP and READ-BACK only; user actions go through real input events
  await page.route("**/app.js", async route => {
    const resp = await route.fetch();
    let body = await resp.text();
    const hook = 'Object.defineProperty(window, "M", {get: () => M}); Object.assign(window, {mapRender, dirty, draftKey, snapshot, edited, snapPos, cellReason});\n';
    if (!/\}\)\(\);\s*$/.test(body)) throw new Error("app.js does not end with the IIFE close");
    body = body.replace(/\}\)\(\);\s*$/, hook + "})();\n");
    await route.fulfill({ response: resp, body });
  });
  const openMore = async (want = true) => {
    const isOpen = await page.evaluate(() => document.getElementById("mapMore").open);
    if (isOpen !== want) { await page.locator("#mapMore summary").scrollIntoViewIfNeeded(); await page.locator("#mapMore summary").click(); }
  };
  await page.goto(`${base}/?token=${token}&tab=map`);
  await page.waitForFunction(() => document.getElementById("connText").textContent === "online", null, { timeout: 10000 });
  await page.waitForSelector("#map rect.floor", { timeout: 10000 });
  await page.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
  out.landing = await page.evaluate(() => M.info.landing_m || []);
  const keepClear = await page.evaluate(() => (M.info.margin_m || 0.1) + (M.info.claw_body_radius_m || 0.07));

  // ---------------------------------------------------------------- 0. the first screen
  await phase("first screen", async () => {
    out.first = await page.evaluate(() => {
      const vis = el => el && el.offsetParent !== null && el.getBoundingClientRect().height > 0
        && !(el.closest("details:not([open])") && el.tagName !== "SUMMARY");
      const controls = [...document.querySelectorAll("#tab-map button, #tab-map summary, #tab-map input")].filter(vis)
        .map(e => (e.textContent || e.getAttribute("aria-label") || e.type).trim().slice(0, 40));
      return { emptyHint: vis(document.getElementById("mapEmpty")) ? document.getElementById("mapEmpty").textContent : null,
               moreOpen: document.getElementById("mapMore").open, controls,
               saveDisabled: document.getElementById("mapSave").disabled, revertHidden: document.getElementById("mapRevert").hidden,
               tabs: [...document.querySelectorAll("#tabs button")].map(b => b.textContent.trim()) };
    });
    out.textFirst = await page.evaluate(probeText);
    out.targetsFirst = await page.evaluate(probeTargets);
    out.contrastFirst = await page.evaluate(probeContrast);
    await layout("first screen");
    await shot("01_first");
  });

  // ---------------------------------------------------------------- 1. walkthrough: a first-time user adds "Desk 4 ft x 2 ft, 2'6" tall" and saves
  await phase("walkthrough", async () => {
    taps = 0;
    const scroll0 = await page.evaluate(() => document.getElementById("tab-map").scrollTop);
    await tap(page.locator(".pal[data-kind=rect]"));
    const insp = await page.locator("#insp").boundingBox();
    const dockTop = await page.evaluate(() => document.getElementById("dock").getBoundingClientRect().top);
    out.walk = { inspectorTopPx: insp && insp.y, dockTopPx: dockTop, msgAfterAdd: await page.textContent("#mapMsg") };
    // the user types the sizes rather than trusting a chip: Length, Width, Height, each by tapping the field and typing
    for (const [lab, val] of [["Length", "4 ft"], ["Width", "2 ft"], ["Height", `2'6"`]]) {
      const f = page.locator(`#insp input[aria-label="${lab}"]`).first();
      await tap(f);
      await f.fill(val);
    }
    // ... and taps Save straight away (no Enter, no Done): the last field's change must not be lost and the tap must land
    const save = page.locator("#mapSave");
    await save.scrollIntoViewIfNeeded();
    const before = await save.boundingBox();
    await tap(save);
    await page.waitForTimeout(400);
    const after = await save.boundingBox();
    out.walk.saveMovedPx = Math.round(Math.hypot(after.x - before.x, after.y - before.y));
    out.walk.msg = await page.textContent("#mapMsg");
    out.walk.tapsTyped = taps;
    out.walk.shapes = await draft();
    out.walk.scrolledPx = (await page.evaluate(() => document.getElementById("tab-map").scrollTop)) - scroll0;
    const saved = await page.evaluate(async t => (await (await fetch("/api/room_map", { headers: { "X-Token": t } })).json()).obstacles, token);
    out.walk.serverAfterFirstSave = saved;
    // if the first Save tap did not save, the user taps it again
    if (!/Saved/.test(out.walk.msg)) { await tap(save); await page.waitForTimeout(400); out.walk.msg2 = await page.textContent("#mapMsg");
      out.walk.serverAfterSecondSave = await page.evaluate(async t => (await (await fetch("/api/room_map", { headers: { "X-Token": t } })).json()).obstacles, token); }
    out.walk.tapsTotal = taps;
    await shot("02_walkthrough_saved");
    // the chip route: a second desk by Rectangle -> "Desk" chip -> Save
    taps = 0;
    await tap(page.locator(".pal[data-kind=rect]"));
    await tap(page.locator("#insp .chip", { hasText: "Desk" }));
    const d2 = (await draft()).slice(-1)[0];
    await tap(page.locator("#mapSave"));
    await page.waitForTimeout(400);
    out.walk.chipRoute = { taps, shape: d2, msg: await page.textContent("#mapMsg"), labels: await page.evaluate(() => [...document.querySelectorAll("#map .slabel")].map(t => t.textContent)) };
    await layout("walkthrough");
  });

  // ---------------------------------------------------------------- 2. start over: revert to an empty map (delete both desks, save)
  await phase("clear", async () => {
    await page.evaluate(() => { M.shapes = []; M.sel = null; mapRender(); });
    await page.click("#mapSave"); await page.waitForTimeout(300);
  });

  // ---------------------------------------------------------------- 3. add each shape by tap; labels and overlap with the hamper
  await phase("add by tap", async () => {
    for (const k of ["square", "rect", "circle"]) { await tap(page.locator(`.pal[data-kind=${k}]`)); await layout("added " + k); }
    out.addedByTap = (await draft()).map(o => ({ shape: o.shape, x: o.x, y: o.y, L: o.length_m, Wd: o.width_m, d: o.diameter_m }));
    out.addedClearOfLanding = (await draft()).map(o => Math.min(...out.landing.map(([lx, ly]) =>     // footprint distance (yaw 0)
      o.shape === "cylinder" ? Math.hypot(lx - o.x, ly - o.y) - o.diameter_m / 2
        : Math.hypot(Math.max(Math.abs(lx - o.x) - o.length_m / 2, 0), Math.max(Math.abs(ly - o.y) - o.width_m / 2, 0)))));
    out.hamper = await page.evaluate(() => M.hamper);
    out.labelsAfterTaps = await page.evaluate(probeLabels);
    await labelShot("03_three_by_tap");
  });

  // ---------------------------------------------------------------- 4. move (drag the body) and drag-and-drop from the palette
  await phase("move", async () => {
    const id = (await draft())[2].id;            // the circle
    const loc = page.locator(`#map circle.shape[data-id=${id}]`);
    await loc.scrollIntoViewIfNeeded();
    const c0 = await center(loc);
    const o0 = (await draft())[2];
    await drag(c0, [c0[0] - 40, c0[1] + 25]);
    const o1 = (await draft())[2];
    const px = await page.evaluate(() => M.px);
    out.move = { dxRoom: o1.x - o0.x, dyRoom: o1.y - o0.y, expect: [-40 / px, -25 / px], snappedToInch: [o1.x / 0.0254, o1.y / 0.0254],
                 selected: await sel() };
    // flush to a wall: drag the square to within ~3 cm of the A-D wall (x = 0)
    const sq = (await draft())[0];
    const sl = page.locator(`#map rect.shape[data-id=${sq.id}]`);
    const s0 = await center(sl);
    const target = await page.evaluate(([x, y]) => { const m = document.getElementById("map").getScreenCTM(); const p = new DOMPoint(x, M.info.room_m[1] - y).matrixTransform(m); return [p.x, p.y]; }, [sq.length_m / 2 + 0.03, sq.y]);
    await drag(s0, target);
    const sq1 = (await draft())[0];
    out.wallSnap = { leftEdge: sq1.x - sq1.length_m / 2 };
    // palette drag and drop (finger on the phone)
    const pal = await center(page.locator(".pal[data-kind=circle]"));
    const mb = await page.locator("#map").boundingBox();
    const drop = [mb.x + mb.width * 0.2, mb.y + mb.height * 0.7];
    const n0 = (await draft()).length;
    await drag(pal, drop, 20);
    const after = await draft();
    const dropped = after.slice(-1)[0];
    const dropRoom = await page.evaluate(([x, y]) => { const p = new DOMPoint(x, y).matrixTransform(document.getElementById("map").getScreenCTM().inverse()); return [p.x, M.info.room_m[1] - p.y]; }, drop);
    out.paletteDrop = { added: after.length - n0, errM: Math.hypot(dropped.x - dropRoom[0], dropped.y - dropRoom[1]) };
    await layout("moved");
  });

  // ---------------------------------------------------------------- 5. resize: square side handle, rectangle corner, circle rim
  await phase("resize", async () => {
    const res = {};
    const shapes = await draft();
    for (const [k, o] of [["square", shapes[0]], ["rect", shapes[1]], ["circle", shapes[2]]]) {
      const body = page.locator(`#map [data-id=${o.id}].shape`);
      await body.scrollIntoViewIfNeeded();
      const c = await center(body);
      await (phone ? page.touchscreen.tap(c[0], c[1]) : page.mouse.click(c[0], c[1]));
      await page.waitForTimeout(30);
      const hit = page.locator("#map circle.hit").first();
      const hc = await center(hit);
      const before = (await draft()).find(s => s.id === o.id);
      await drag(hc, [hc[0] + 30, hc[1] - 18]);
      const after = (await draft()).find(s => s.id === o.id);
      res[k] = { before: [before.length_m || before.diameter_m, before.width_m || before.diameter_m],
                 after: [after.length_m || after.diameter_m, after.width_m || after.diameter_m], equalSides: after.length_m === after.width_m,
                 handles: await page.locator("#map circle.hit").count() };
    }
    out.resize = res;
    await layout("resized");
  });

  // ---------------------------------------------------------------- 6. rotate: the Turn 90 button and the exact angle under More
  await phase("rotate", async () => {
    const rect = (await draft())[1];
    await page.evaluate(id => { M.sel = id; mapRender(); }, rect.id);
    const y0 = rect.yaw_deg;
    await tap(page.locator("#insp button", { hasText: "Turn 90" }));
    const y1 = (await draft())[1].yaw_deg;
    await page.locator("#insp details > summary").click();
    await typeInto("Turned (degrees)", "30");
    const y2 = (await draft())[1].yaw_deg;
    out.rotate = { y0, y1, y2, squareHasTurn: null };
    await page.evaluate(id => { M.sel = id; mapRender(); }, (await draft())[0].id);
    out.rotate.squareHasTurn = await page.locator("#insp button", { hasText: "Turn 90" }).count();
    out.rotate.inspectorSquare = await page.evaluate(() => [...document.querySelectorAll("#insp > .grid2 label")].map(l => l.firstChild.textContent));
    await page.evaluate(id => { M.sel = id; mapRender(); }, rect.id);
    out.rotate.inspectorRect = await page.evaluate(() => [...document.querySelectorAll("#insp > .grid2 label")].map(l => l.firstChild.textContent));
    out.rotate.moreFields = await page.evaluate(() => [...document.querySelectorAll("#insp details label")].map(l => l.textContent.trim().slice(0, 40)));
    out.targetsInspector = await page.evaluate(probeTargets);
    out.contrastInspector = await page.evaluate(probeContrast);
    await layout("inspector open");
    await page.evaluate(() => { document.getElementById("tab-map").scrollTop = 1e5; });
    await layout("inspector scrolled to the bottom");
    await shot("04_inspector");
  });

  // ---------------------------------------------------------------- 7. length parsing in both unit modes
  await phase("parse", async () => {
    const rect = (await draft())[1];
    await page.evaluate(id => { M.sel = id; mapRender(); }, rect.id);
    const cases = [`5'6"`, "66 in", "1.68 m", "168 cm", "5 ft 6 in", "5' 6\"", "5'6", "66\"", "66", "5’6”", "1,68 m", "1680 mm", "5'", "2 ft", "abc", "-1 m", "0"];
    const res = [];
    for (const t of cases) {
      await page.evaluate(id => { M.sel = id; mapRender(); }, rect.id);
      await typeInto("Height", t);
      const o = (await draft()).find(s => s.id === rect.id);
      res.push({ input: t, height_m: o.height_m, msg: await page.textContent("#mapMsg") });
      await page.evaluate(([id]) => { const o = M.shapes.find(s => s.id === id); o.height_m = 0.75; mapRender(); }, [rect.id]);
    }
    out.parseFtIn = res;
    // metres mode
    await openMore(true);
    await page.click("#mapUnits");
    out.unitsLabel = await page.textContent("#mapUnits");
    const resM = [];
    for (const t of ["1.68", "1.68 m", "168 cm", `5'6"`]) {
      await page.evaluate(id => { M.sel = id; mapRender(); }, rect.id);
      await typeInto("Height", t);
      resM.push({ input: t, height_m: (await draft()).find(s => s.id === rect.id).height_m });
    }
    out.parseM = resM;
    out.labelsMetres = await page.evaluate(() => [...document.querySelectorAll("#map .slabel")].map(t => t.textContent));
    out.unitsDirtyOnly = await page.evaluate(() => ({ saveDisabled: document.getElementById("mapSave").disabled, dirty: dirty() }));
    await page.click("#mapUnits");                                     // back to ft-in
    await openMore(false);
  });

  // ---------------------------------------------------------------- 8. plain language of what the user is shown when something is wrong
  await phase("plain language", async () => {
    const rect = (await draft())[1];
    await page.evaluate(id => { const o = M.shapes.find(s => s.id === id); o.height_m = 0.75; M.sel = id; mapRender(); }, rect.id);
    const msgs = {};
    for (const [lab, val, key] of [["Height", "0", "zero"], ["Length", "20 ft", "tooLong"], ["Height", "12 ft", "tooTall"]]) {
      await page.evaluate(id => { M.sel = id; mapRender(); }, rect.id);
      await typeInto(lab, val);
      msgs[key] = { field: await page.textContent("#mapMsg"), value: (await draft()).find(s => s.id === rect.id)[lab === "Height" ? "height_m" : "length_m"] };
      await page.click("#mapSave"); await page.waitForTimeout(400);
      msgs[key].afterSave = await page.textContent("#mapSave") && await page.textContent("#mapMsg");
      await page.evaluate(id => { M.sel = id; mapRender(); }, rect.id);
    }
    await typeInto("Height", `2'6"`);
    await typeInto("Length", "3 ft");
    // a refusal that only the service can give: a shape over the claw's landing spot
    await page.evaluate(([x, y]) => { const o = M.shapes[1]; o.x = x; o.y = y; o.name = ""; edited(""); }, out.landing[0]);
    await page.click("#mapSave"); await page.waitForTimeout(500);
    msgs.landing = { afterSave: await page.textContent("#mapMsg"), toast: (await page.evaluate(probeText)).toast };
    out.msgZeroHeight = msgs.zero.field; out.msgTooLong = msgs.tooLong.field; out.msgTooTall = msgs.tooTall.field;
    out.msgs = msgs;
    out.textAfterErrors = await page.evaluate(probeText);
    await page.evaluate(() => { const o = M.shapes[1]; o.x = 0.9; o.y = 2.1; edited(""); });
  });

  // ---------------------------------------------------------------- 9. undo (20 steps), save, revert, reload
  await phase("undo", async () => {
    const k0 = await page.evaluate(() => draftKey());
    const rect = (await draft())[1];
    for (let i = 0; i < 3; i++) { await page.evaluate(id => { M.sel = id; mapRender(); }, rect.id); await typeInto("Height", `${3 + i} ft`); }
    const undoBox0 = await page.locator("#mapUndo").isVisible();
    await openMore(true);
    const undoBox = await page.locator("#mapUndo").boundingBox();
    for (let i = 0; i < 3; i++) await page.click("#mapUndo");
    out.undo = { backToStart: (await page.evaluate(() => draftKey())) === k0 };
    for (let i = 0; i < 25; i++) await page.evaluate(i => { M.sel = M.shapes[1].id; snapshot(); M.shapes[1].height_m = 0.5 + i * 0.01; edited(""); }, i);
    let n = 0;
    while (!(await page.locator("#mapUndo").isDisabled()) && n < 40) { await page.click("#mapUndo"); n++; }
    out.undo.stepsAvailable = n;
    out.undo.undoVisibleWithoutMore = undoBox0;
    await openMore(false);
  });

  await phase("save and reload", async () => {
    // a valid map: square, rectangle (hanging lamp chip on the circle), named shapes
    await page.evaluate(() => { const r = M.shapes[1]; r.height_m = 0.762; r.length_m = 1.2192; r.width_m = 0.6096; r.name = "Desk"; r.x = 0.9; r.y = 2.1; snapPos(r); mapRender(); });
    await page.evaluate(id => { M.sel = id; mapRender(); }, (await draft())[2].id);
    await tap(page.locator("#insp .chip", { hasText: "Ceiling fan" }));
    out.fanChip = (await draft())[2];
    out.dirtyDot = await page.isVisible("#mapDot");
    out.revertVisible = await page.isVisible("#mapRevert");
    await page.click("#mapSave");
    await page.waitForFunction(() => /Saved/.test(document.getElementById("mapMsg").textContent), null, { timeout: 8000 });
    out.saveMsg = await page.textContent("#mapMsg");
    out.dirtyDotAfter = await page.isVisible("#mapDot");
    const kSaved = await page.evaluate(() => JSON.stringify(M.shapes));
    // revert after an edit
    await page.evaluate(() => { M.shapes[0].height_m = 1.5; edited(""); });
    await page.click("#mapRevert"); await page.waitForTimeout(300);
    out.revertOk = (await page.evaluate(() => JSON.stringify(M.shapes))) === kSaved;
    await page.reload();
    await page.waitForFunction(() => document.querySelectorAll("#map .shape").length > 0, null, { timeout: 10000 });
    out.unitsSaved = await (async () => {
      await openMore(true);
      const before = await page.evaluate(() => ({ dirty: dirty(), save: document.getElementById("mapSave").disabled }));
      await page.click("#mapUnits");
      const after = await page.evaluate(() => ({ dirty: dirty(), save: document.getElementById("mapSave").disabled, units: M.units }));
      await page.click("#mapSave"); await page.waitForTimeout(400);
      const server = (await (await page.evaluate(async t => (await (await fetch("/api/room_map", { headers: { "X-Token": t } })).json()), token))).units;
      await page.click("#mapUnits"); await page.click("#mapSave"); await page.waitForTimeout(400);     // back to ft-in, saved
      await openMore(false);
      return { before, after, server };
    })();
    out.reloadSame = (await page.evaluate(() => JSON.stringify(M.shapes.map(({ id, shape, x, y, height_m, z_low_m }) => ({ id, shape, x, y, height_m, z_low_m })))))
                     === JSON.stringify(JSON.parse(kSaved).map(({ id, shape, x, y, height_m, z_low_m }) => ({ id, shape, x, y, height_m, z_low_m })));
    out.labelsAfterReload = await page.evaluate(probeLabels);
    await layout("reloaded");
    await labelShot("05_reloaded");
  });

  // ---------------------------------------------------------------- 10. hamper: move it and set its rim height
  await phase("hamper", async () => {
    await openMore(true);
    await tap(page.locator("#mapHamper"));
    out.hamperInspector = await page.evaluate(() => [...document.querySelectorAll("#insp label")].map(l => l.firstChild.textContent));
    await typeInto("Rim height", "2 ft");
    const hp = page.locator("#map circle.hamper");
    await hp.scrollIntoViewIfNeeded();
    const b = await hp.boundingBox();
    const h0 = await page.evaluate(() => ({ ...M.hamper }));
    // grab the ring (the hamper is fill:none: only its stroke takes the pointer)
    const grab = [b.x + b.width / 2, b.y + 1.5];
    await drag(grab, [grab[0] + 30, grab[1] + 10]);
    const h1 = await page.evaluate(() => ({ ...M.hamper }));
    out.hamperMove = { moved: Math.hypot(h1.x - h0.x, h1.y - h0.y), rim: h1.height_m };
    // grabbing the middle of the ring (what a user does) also moves it?
    const b2 = await hp.boundingBox();
    const mid = [b2.x + b2.width / 2, b2.y + b2.height / 2];
    await drag(mid, [mid[0] - 30, mid[1]]);
    const h2 = await page.evaluate(() => ({ ...M.hamper }));
    out.hamperMove.movedByMiddle = Math.hypot(h2.x - h1.x, h2.y - h1.y);
    await page.click("#mapSave"); await page.waitForTimeout(400);
    out.hamperSaved = await page.evaluate(async t => (await (await fetch("/api/room_map", { headers: { "X-Token": t } })).json()).hamper, token);
  });

  // ---------------------------------------------------------------- 11. "where it can pick" overlay and the reason of a tapped cell
  await phase("overlay", async () => {
    await openMore(true);
    await page.locator("#mapCov").check();
    await page.waitForSelector("#map .cov path", { timeout: 8000 });
    out.overlay = { paths: await page.locator("#map .cov path").count(), legend: await page.isVisible("#covLegend") };
    const t0 = Date.now();
    await page.evaluate(() => { M.shapes[0].x += 0.1; edited(""); });
    await page.waitForFunction(k => M.cov && M.covSeq > k, await page.evaluate(() => M.covSeq), { timeout: 5000 });
    out.overlay.updateMs = Date.now() - t0;
    // tap a cell next to the square (blocked) and one in the open
    const sq = (await draft())[0];
    // a floor cell next to the square: the first candidate (around it, 6 cm out) under which the finger finds the floor itself
    const toScreen = xy => page.evaluate(([x, y]) => { const p = new DOMPoint(x, M.info.room_m[1] - y).matrixTransform(document.getElementById("map").getScreenCTM()); return [p.x, p.y]; }, xy);
    const cands = [[sq.x + sq.length_m / 2 + 0.06, sq.y], [sq.x - sq.length_m / 2 - 0.06, sq.y], [sq.x, sq.y + sq.width_m / 2 + 0.06], [sq.x, sq.y - sq.width_m / 2 - 0.06]];
    let pt = null, cell = null;
    for (const xy of cands) {
      let p = await toScreen(xy);
      await page.evaluate(y => { document.getElementById("tab-map").scrollTop += y - innerHeight / 3; }, p[1]);   // bring it into view
      await page.waitForTimeout(50);
      p = await toScreen(xy);
      const floor = await page.evaluate(([x, y]) => { const e = document.elementFromPoint(x, y); return !!e && e.classList.contains("floor"); }, p);
      if (floor && xy[0] > 0.05 && xy[1] > 0.05) { pt = p; cell = xy; break; }
    }
    if (!pt) throw new Error("no floor cell next to the square");
    out.overlay.under = await page.evaluate(([x, y]) => { const e = document.elementFromPoint(x, y); return e ? e.tagName + "." + e.getAttribute("class") + " id=" + e.dataset.id + " hamper=" + e.dataset.hamper : null; }, pt);
    out.overlay.cellBefore = await page.evaluate(xy => cellReason(xy), cell);
    await (phone ? page.touchscreen.tap(pt[0], pt[1]) : page.mouse.click(pt[0], pt[1]));
    await page.waitForTimeout(100);
    out.overlay.cellMsg = await page.textContent("#mapMsg");
    out.overlay.selAfter = await page.evaluate(() => M.sel);
    out.labelsOverlay = await page.evaluate(probeLabels);
    out.contrastOverlay = await page.evaluate(probeContrast);
    out.textOverlay = await page.evaluate(probeText);
    await layout("overlay");
    await labelShot("06_overlay");
  });

  // ---------------------------------------------------------------- 12. tiny shapes, crowded labels, render cost of a full map
  await phase("labels and scale", async () => {
    await page.locator("#mapCov").uncheck();
    await page.evaluate(() => {
      M.shapes = [
        { id: "a1", name: "Desk", shape: "box", x: 1.0, y: 0.9, length_m: 1.22, width_m: 0.61, yaw_deg: 0, z_low_m: 0, height_m: 0.76 },
        { id: "a2", name: "Chair", shape: "box", x: 1.0, y: 1.45, length_m: 0.5, width_m: 0.5, yaw_deg: 0, z_low_m: 0, height_m: 0.9 },
        { id: "a3", name: "Lamp", shape: "cylinder", x: 1.75, y: 0.9, diameter_m: 0.4, z_low_m: 0, height_m: 1.6 },
        { id: "a4", name: "Ceiling fan", shape: "cylinder", x: 1.68, y: 1.37, diameter_m: 1.1, z_low_m: 2.29, height_m: 2.74 },
        { id: "a5", name: "Pole", shape: "cylinder", x: 2.6, y: 2.0, diameter_m: 0.05, z_low_m: 0, height_m: 2.4 },
        { id: "a6", name: "Dresser", shape: "box", x: 0.23, y: 2.2, length_m: 0.46, width_m: 1.52, yaw_deg: 0, z_low_m: 0, height_m: 0.86 },
      ];
      M.sel = null; mapRender();
    });
    out.labelsCrowded = await page.evaluate(probeLabels);
    out.targetsCrowded = (await page.evaluate(probeTargets)).filter(t => t.shape);
    await labelShot("07_crowded_labels");
    // the screenshot case the lead saw: a circle moved onto the hamper
    await page.evaluate(() => { M.shapes = [{ id: "c1", name: "", shape: "cylinder", x: M.hamper.x + 0.05, y: M.hamper.y + 0.02, diameter_m: 0.76, z_low_m: 0, height_m: 0.75 }]; M.sel = null; mapRender(); });
    out.labelsOnHamper = await page.evaluate(probeLabels);
    await labelShot("08_circle_on_hamper");
    // render cost: 50 shapes + the overlay drawn (one drag frame = one mapRender)
    out.renderMs = await page.evaluate(async () => {
      const sh = [];
      for (let i = 0; i < 50; i++) sh.push({ id: "z" + i, name: "Box", shape: i % 2 ? "box" : "cylinder", x: 0.3 + (i % 10) * 0.3, y: 0.3 + Math.floor(i / 10) * 0.5,
        length_m: 0.2, width_m: 0.2, diameter_m: 0.2, yaw_deg: 10, z_low_m: 0, height_m: 0.5 });
      M.shapes = sh; M.sel = "z3";
      const t0 = performance.now(); for (let k = 0; k < 30; k++) mapRender(); const plain = (performance.now() - t0) / 30;
      return { fiftyShapes: Math.round(plain * 100) / 100 };
    });
    await page.evaluate(() => { M.shapes = []; M.sel = null; mapRender(); });
  });

  // ---------------------------------------------------------------- 13. narrowest phone: no horizontal scroll at 320 px
  await phase("320 px", async () => {
    await page.setViewportSize({ width: 320, height: 640 });
    await page.evaluate(() => { M.shapes = [{ id: "q1", name: "Ceiling fan", shape: "cylinder", x: 1.68, y: 1.37, diameter_m: 1.1, z_low_m: 2.29, height_m: 2.74 }]; M.sel = "q1"; mapRender(); });
    await page.locator("#insp details > summary").click().catch(() => {});
    await openMore(true);
    out.w320 = await page.evaluate(probeLayout);
    out.targets320 = await page.evaluate(probeTargets);
    await shot("09_320px");
    await page.setViewportSize({ width: w, height: h });
  });

  out.taps = taps;
  await browser.close();
  console.log(JSON.stringify(out));
})().catch(e => { console.error(String(e && e.stack || e)); process.exit(1); });
