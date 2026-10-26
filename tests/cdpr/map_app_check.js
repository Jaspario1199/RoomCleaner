// Browser check of the Map tab (docs/ROOM_MAP_SPEC.md 5), driven by tests/cdpr/test_room_map_app.py:
//   node map_app_check.js <base url> <token> <width> <height> [screenshot dir]
// Prints one JSON line with what it measured; the Python test makes the assertions.
const { chromium } = require("playwright");
const [base, token, W, H, shots] = process.argv.slice(2);
const w = +W, h = +H;

const geometry = () => {
  const inView = r => r.top >= 0 && r.bottom <= innerHeight + 0.5 && r.left >= 0 && r.right <= innerWidth + 0.5;
  const topAt = el => { const r = el.getBoundingClientRect(); const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!e && (e === el || el.contains(e)); };
  const p = document.getElementById("pause"), s = document.querySelector(".estop");
  return { pause: topAt(p) && inView(p.getBoundingClientRect()), estop: topAt(s) && inView(s.getBoundingClientRect()),
           noHScroll: document.documentElement.scrollWidth <= innerWidth && document.body.scrollWidth <= innerWidth
                      && document.getElementById("tab-map").scrollWidth <= document.getElementById("tab-map").clientWidth + 0.5 };
};
const contrast = () => {
  const rgb = c => { const m = c.match(/[\d.]+/g).map(Number); return m; };
  const lum = c => { const [r, g, b] = rgb(c).slice(0, 3).map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const bgOf = el => { for (let e = el; e; e = e.parentElement) { const c = getComputedStyle(e).backgroundColor; if (c && !/rgba\(.*,\s*0\)$/.test(c) && c !== "transparent") return c; } return getComputedStyle(document.body).backgroundColor; };
  const out = {};
  const lab = document.querySelector("#map .slabel"), shp = document.querySelector("#map .shape");
  if (lab && shp) out.shapeLabel = ratio(getComputedStyle(lab).fill, getComputedStyle(shp).fill);
  for (const sel of ["#mapMsg", "#mapEmpty", "#insp label", "#insp h3", ".pal", "#mapMore summary", ".estop", "#mapNote"]) {
    const e = document.querySelector(sel);
    if (e && e.offsetParent !== null) out[sel] = ratio(getComputedStyle(e).color, bgOf(e));
  }
  return out;
};

(async () => {
  const browser = await chromium.launch();
  const out = { w, h, checks: [] };
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, hasTouch: false });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  const check = async label => out.checks.push({ label, ...(await page.evaluate(geometry)) });
  await page.goto(base + "/?token=" + token + "&tab=map");
  await page.waitForFunction(() => document.getElementById("connText").textContent === "online", null, { timeout: 8000 });
  await page.waitForSelector("#map rect.floor", { timeout: 8000 });
  out.emptyShown = await page.isVisible("#mapEmpty");
  out.moreClosed = !(await page.evaluate(() => document.getElementById("mapMore").open));
  await check("loaded");
  if (shots) await page.screenshot({ path: shots + "/map_empty_light.png" });
  // add a circle by tap
  await page.click(".pal[data-kind=circle]");
  out.afterTap = await page.locator("#map .shape").count();
  await check("circle added");
  // add a rectangle by dragging the palette button onto the map
  const pal = await page.locator(".pal[data-kind=rect]").boundingBox();
  const map = await page.locator("#map").boundingBox();
  await page.mouse.move(pal.x + pal.width / 2, pal.y + pal.height / 2);
  await page.mouse.down();
  const drop = [map.x + map.width * 0.25, map.y + map.height * 0.3];
  for (let k = 1; k <= 10; k++) await page.mouse.move(pal.x + pal.width / 2 + (drop[0] - pal.x - pal.width / 2) * k / 10, pal.y + pal.height / 2 + (drop[1] - pal.y - pal.height / 2) * k / 10);
  await page.mouse.up();
  out.afterDrag = await page.locator("#map .shape").count();
  out.rectDroppedNear = await page.evaluate(([x, y]) => { const r = document.querySelector("#map rect.shape").getBoundingClientRect(); return Math.hypot(r.left + r.width / 2 - x, r.top + r.height / 2 - y); }, drop);
  await check("rectangle dropped");
  // move the circle
  const circ = page.locator("#map circle.shape");
  const c0 = await circ.boundingBox();
  await page.mouse.move(c0.x + c0.width / 2, c0.y + c0.height / 2);
  await page.mouse.down();
  for (let k = 1; k <= 8; k++) await page.mouse.move(c0.x + c0.width / 2 + 6 * k, c0.y + c0.height / 2 + 3 * k);
  await page.mouse.up();
  const c1 = await circ.boundingBox();
  out.circleMovedPx = Math.hypot(c1.x - c0.x, c1.y - c0.y);
  // resize the circle by its rim handle
  const rim = await page.locator("#map circle.hit").first().boundingBox();
  await page.mouse.move(rim.x + rim.width / 2, rim.y + rim.height / 2);
  await page.mouse.down();
  for (let k = 1; k <= 6; k++) await page.mouse.move(rim.x + rim.width / 2 + 4 * k, rim.y + rim.height / 2);
  await page.mouse.up();
  const c2 = await circ.boundingBox();
  out.circleGrewPx = c2.width - c1.width;
  await check("circle moved and resized");
  // select the rectangle, resize it by a corner, then type a height in ft-in
  const r0 = await page.locator("#map rect.shape").boundingBox();
  await page.mouse.click(r0.x + r0.width / 2, r0.y + r0.height / 2);
  const corner = await page.locator("#map circle.hit").first().boundingBox();
  await page.mouse.move(corner.x + corner.width / 2, corner.y + corner.height / 2);
  await page.mouse.down();
  for (let k = 1; k <= 6; k++) await page.mouse.move(corner.x + corner.width / 2 + 5 * k, corner.y + corner.height / 2 + 2 * k);
  await page.mouse.up();
  const r1 = await page.locator("#map rect.shape").boundingBox();
  out.rectResizedPx = Math.abs(r1.width - r0.width) + Math.abs(r1.height - r0.height);
  out.inspectorFields = await page.evaluate(() => [...document.querySelectorAll("#insp > .grid2 label")].map(l => l.firstChild.textContent));
  await page.click("#insp .chip >> text=Shelf");
  const hf = page.locator("#insp > .grid2 input[aria-label=Height]");
  await hf.fill(`6'5"`);
  await hf.press("Enter");
  out.labels = await page.evaluate(() => [...document.querySelectorAll("#map .slabel")].map(t => t.textContent));
  await check("height typed");
  if (shots) await page.screenshot({ path: shots + "/map_shapes_light.png" });
  // the "Where can it pick?" overlay is behind More
  await page.click("#mapMore summary");
  await page.check("#mapCov");
  await page.waitForSelector("#map path.cov-shape, #map path.cov-ok, #map path.cov-trust", { timeout: 8000 });
  out.overlay = await page.locator("#map .cov path").count();
  await check("overlay");
  if (shots) { await page.evaluate(() => { document.getElementById("tab-map").scrollTop = 0; }); await page.screenshot({ path: shots + "/map_overlay_light.png" }); }
  // save
  await page.click("#mapSave");
  await page.waitForFunction(() => /Saved/.test(document.getElementById("mapMsg").textContent), null, { timeout: 8000 });
  out.saved = await page.textContent("#mapMsg");
  out.dotAfterSave = await page.isVisible("#mapDot");
  await check("saved");
  // reload: the shapes come back
  await page.reload();
  await page.waitForSelector("#map rect.floor", { timeout: 8000 });
  await page.waitForFunction(() => document.querySelectorAll("#map .shape").length > 0, null, { timeout: 8000 });
  out.afterReload = await page.locator("#map .shape").count();
  out.labelsAfterReload = await page.evaluate(() => [...document.querySelectorAll("#map .slabel")].map(t => t.textContent));
  await check("reloaded");
  out.lightContrast = await page.evaluate(contrast);
  // dark theme
  await page.emulateMedia({ colorScheme: "dark" });
  await page.mouse.click((await page.locator("#map rect.shape").boundingBox()).x + 5, (await page.locator("#map rect.shape").boundingBox()).y + 5);
  out.darkContrast = await page.evaluate(contrast);
  await check("dark");
  if (shots) {
    await page.evaluate(() => { document.getElementById("tab-map").scrollTop = 0; });
    await page.screenshot({ path: shots + "/map_shapes_dark.png" });
    await page.evaluate(() => { document.getElementById("tab-map").scrollTop = 1e4; });
    await page.screenshot({ path: shots + "/map_inspector_dark.png" });
  }
  out.errors = errors;
  await browser.close();
  console.log(JSON.stringify(out));
})().catch(e => { console.error(String(e && e.stack || e)); process.exit(1); });
