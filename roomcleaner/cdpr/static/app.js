/* RoomCleaner phone app (docs/PHONE_APP_SPEC.md). Plain JS, no build step, no external resources.
 *
 * The app only calls the service's existing endpoints. Losing the connection does nothing to the robot; PAUSE needs the
 * connection, and the app says so loudly when it is lost. Nothing here claims to be an emergency stop. */
(() => {
"use strict";

const $ = id => document.getElementById(id);
const STEPS = ["SELF_CHECK", "SLACK_TAKEUP", "INITIAL_LIFT", "VISUAL_INITIALIZATION", "CALIBRATION",
               "REFERENCE_VERIFICATION", "READY"];
const STATE_CLASS = {READY: "good", TASK: "good", PARKED: "", DISARMED: "", STARTUP: "warn", PAUSED: "warn",
                     FAULT: "bad", RECOVERY_REQUIRED: "bad"};
const STATION_STATE = {OFF: "off (not holding)", IDLE: "holding", RUN: "moving", HOLD: "stopping", FAULT: "fault (holding)"};
const STATION_WORD = {OFF: "off", IDLE: "holding", RUN: "moving", HOLD: "stopping", FAULT: "fault"};
const TABS = ["home", "camera", "setup", "chat"];

let TOKEN = "";
let S = null;                      // last /api/status
let tab = "home";
let lastEvent = 0, firstEvents = true, recent = [];
let netFails = 0, ticking = false;
let pending = null;                // {action, until}
let roomInit = false, lastChecks = 0, calibKey = "", checklistText = "";

// ------------------------------------------------------------------------------------------------ helpers
function h(tag, props, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v === true) e.setAttribute(k, "");
    else if (v !== false && v != null) e.setAttribute(k, v);
  }
  for (const c of kids.flat()) if (c != null) e.append(c.nodeType ? c : document.createTextNode(String(c)));
  return e;
}
const store = {
  get(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { sessionStorage.setItem(k, v); } catch (e) { /* private mode: fine */ } },
};
function readToken() {
  const q = new URLSearchParams(location.search).get("token");
  const f = new URLSearchParams(location.hash.replace(/^#/, "")).get("token");
  const t = q || f;
  if (t) { store.set("rc_token", t); return t; }
  return store.get("rc_token") || "";
}
TOKEN = readToken();
const fmtTime = t => new Date((t || Date.now() / 1000) * 1000).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"});
const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
const mm = x => (x * 1e3).toFixed(0) + " mm";

let toastTimer = null;
function toast(msg, bad = false, ms = 3500) {
  const t = $("toast");
  t.textContent = msg; t.className = "toast" + (bad ? " bad" : ""); t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, bad ? Math.max(ms, 7000) : ms);
}

function layout() {            // sheets and toasts sit just above the PAUSE dock
  const hgt = $("dock").offsetHeight + $("tabs").offsetHeight;
  document.documentElement.style.setProperty("--dock-h", hgt + "px");
}

// ------------------------------------------------------------------------------------------------ network
async function api(path, body) {
  const headers = {"X-Token": TOKEN};
  const opt = {headers, cache: "no-store"};
  if (body !== undefined) { opt.method = "POST"; headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
  let r;
  try { r = await fetch(path, opt); }
  catch (e) { netFails++; setConn(false); return {ok: false, status: 0, data: {error: "no connection to the robot service"}}; }
  netFails = 0; setConn(true);
  if (r.status === 401) showConnect("The session token is missing or wrong. The service makes a new one every time it starts.");
  let data = {};
  try { data = await r.json(); } catch (e) { /* not JSON */ }
  return {ok: r.ok, status: r.status, data};
}

function setConn(ok) {
  $("conn").className = "conn " + (ok ? "ok" : "bad");
  $("connText").textContent = ok ? "online" : "offline";
  const b = $("banner");
  if (!ok && netFails >= 2) {
    b.textContent = "Lost the connection to the robot service. The robot keeps holding its position and does nothing by "
      + "itself, but PAUSE cannot reach it until the connection is back.";
    b.hidden = false;
  } else if (ok && b.dataset.kind !== "app") b.hidden = true;
}

function showConnect(note) {
  if (note) $("connectNote").textContent = note;
  $("connect").hidden = false;
}
$("connectForm").addEventListener("submit", e => {
  e.preventDefault();
  const v = $("connectInput").value.trim();
  const m = v.match(/[?#&]token=([^&\s]+)/);
  TOKEN = m ? decodeURIComponent(m[1]) : v;
  if (!TOKEN) return;
  store.set("rc_token", TOKEN);
  $("connect").hidden = true;
  tick();
});

// ------------------------------------------------------------------------------------------------ confirm sheet
let closeSheet = null;
function ask({title, body, ok = "OK", input = null}) {
  if (closeSheet) closeSheet(null);
  return new Promise(res => {
    const box = $("dlg"), inp = $("dlgInput"), okb = $("dlgOk");
    $("dlgTitle").textContent = title; $("dlgBody").textContent = body;
    inp.hidden = !input; inp.value = ""; inp.placeholder = input || "";
    okb.textContent = ok; okb.disabled = !!input;
    const done = v => { box.hidden = true; closeSheet = null; $("dlgForm").onsubmit = null; $("dlgCancel").onclick = null; inp.oninput = null; res(v); };
    closeSheet = done;
    inp.oninput = () => { okb.disabled = inp.value.trim() !== input; };
    $("dlgForm").onsubmit = e => { e.preventDefault(); if (!okb.disabled) done(input ? inp.value.trim() : true); };
    $("dlgCancel").onclick = () => done(null);
    box.hidden = false; layout();
    (input ? inp : okb).focus({preventScroll: true});
  });
}

// ------------------------------------------------------------------------------------------------ commands
async function cmd(name, extra) {
  const r = await api("/api/command", Object.assign({cmd: name}, extra || {}));
  if (!r.ok) toast((r.data && r.data.error) || ("HTTP " + r.status), true);
  setTimeout(tick, 150);
  return r;
}
async function doPause() {
  const r = await api("/api/command", {cmd: "pause"});
  if (r.ok) toast("Paused: holding position, torque stays on. This is not an emergency stop.");
  else toast("PAUSE DID NOT REACH THE ROBOT SERVICE. Use the power strip if the claw is in danger. " + ((r.data && r.data.error) || ""), true);
  setTimeout(tick, 100);
}
$("pause").addEventListener("click", doPause);

// ------------------------------------------------------------------------------------------------ tabs
function showTab(name) {
  if (!TABS.includes(name)) name = "home";
  tab = name; store.set("rc_tab", name);
  for (const b of document.querySelectorAll("#tabs button")) b.setAttribute("aria-selected", String(b.dataset.tab === name));
  for (const t of TABS) $("tab-" + t).hidden = t !== name;
  if (name === "camera") camStart(); else camStop();
  if (name === "setup") { refreshChecks(); refreshCalib(); }
  if (name === "chat") scrollChat(true);
}
document.querySelectorAll("#tabs button").forEach(b => b.addEventListener("click", () => showTab(b.dataset.tab)));

// ------------------------------------------------------------------------------------------------ status rendering
function trustText(t) {
  if (!t || t.level === "NONE") return "Not calibrated yet: no volume is trusted.";
  const m = t.margin || {};
  if (t.level === "VERIFIED") {
    const nums = (m.k_sigma_ceiling_m !== undefined)
      ? ` (k=${m.k}: ceiling ${mm(m.k_sigma_ceiling_m)} of ${mm(m.ceiling_margin_m)}, walls ${mm(m.k_sigma_wall_m)} of ${mm(m.workspace_margin_m)})` : "";
    return "Full workspace, checked by " + (t.basis === "beads" ? "bead references" : "the ceiling and wall margins" + nums) + ".";
  }
  return "Restricted to the calibrated volume.";
}
function line(label, value, cls) { return h("div", {class: "ln"}, label + ": ", h("b", {class: cls || ""}, value)); }

function stationTile(id, v) {
  const fault = v.fault && v.fault !== "NONE";
  const ref = !v.valid ? "ref INVALID" : (v.bead_verified ? "ref bead" : "ref visual");
  const st = v.online ? (STATION_WORD[v.state] || v.state || "?") : "OFFLINE";
  return h("div", {class: "tile" + (fault || !v.online ? " fault" : ""), title: STATION_STATE[v.state] || ""},
    h("div", {class: "id"}, id),
    h("div", {class: "ln"}, h("b", {class: v.online ? "" : "badc"}, st)),
    h("div", {class: "ln"}, h("b", {class: fault ? "badc" : ""}, fault ? "fault " + v.fault : "no fault")),
    h("div", {class: "ln " + (v.valid ? "" : "badc")}, ref));
}

function kv(label, ...vals) { return h("div", {class: "kv"}, h("span", {}, label), h("b", {}, ...vals)); }

function renderClaw(c) {
  const box = $("claw"); box.replaceChildren();
  if (c.online === null || c.online === undefined) { box.append(kv("Link", "no telemetry yet")); return; }
  const v = c.battery_v;
  box.append(
    kv("Link", h("span", {class: c.online ? "ok" : "badc"}, c.online ? "online" : (c.stale ? "stale" : "OFFLINE")),
       c.age_s != null ? ` (${c.age_s} s ago)` : ""),
    kv("Battery", v == null ? "n/a" : v.toFixed(2) + " V ",
       v == null ? "" : h("span", {class: c.battery_low ? "badc" : "ok"}, c.battery_low ? "LOW (min " + c.battery_min_v + " V to lift)" : "OK")),
    kv("Grip", c.grip_closed == null ? "unknown" : (c.grip_closed ? "closed" : "open")),
    kv("Camera", h("span", {class: c.camera_ok ? "ok" : "badc"}, c.camera_ok == null ? "n/a" : (c.camera_ok ? "OK" : "FAULT")),
       c.camera_mode ? " " + c.camera_mode : ""));
  if (c.error) box.append(kv("Error", c.error));
}

function renderStatus(s) {
  S = s;
  const st = s.state, cls = STATE_CLASS[st] || "";
  $("topState").textContent = st; $("topState").className = "pill " + cls;
  $("state").textContent = st; $("state").className = "bigstate " + cls;
  $("stateText").textContent = s.state_text || "";
  $("busy").hidden = !s.busy; $("busyText").textContent = s.busy ? `Working: ${s.busy} ...` : "";
  const stepNow = s.detail && (STEPS.includes(s.detail) || ["STARTUP", "TASK"].includes(st));
  $("stepLine").textContent = stepNow ? "Step: " + s.detail.replace(/_/g, " ").toLowerCase() : "";
  const err = $("lastErr"); err.hidden = !s.error; err.textContent = s.error ? "Last error: " + s.error : "";
  const ab = $("banner");
  if (s.app_error) { ab.textContent = "App service problem: " + s.app_error; ab.dataset.kind = "app"; ab.hidden = false; }
  else if (ab.dataset.kind === "app") { ab.dataset.kind = ""; ab.hidden = true; }

  // trust
  const t = s.trust || {};
  $("level").textContent = s.level; $("level").className = "pill " + ({VERIFIED: "good", LOCAL_ONLY: "warn", NONE: ""}[s.level] || "");
  $("trustText").textContent = trustText(t);
  $("trustReasons").replaceChildren(...((t.reasons || []).map(r => h("li", {}, r))));

  // stations and claw: only the ACTIVE stations (three-station mode shows three tiles; the service lists no other)
  const tiles = Object.entries(s.stations || {}).sort();
  $("stations").style.gridTemplateColumns = `repeat(${Math.max(tiles.length, 1)}, minmax(0, 1fr))`;
  $("stations").replaceChildren(...tiles.map(([id, v]) => stationTile(id, v)));
  renderClaw(s.claw || {});

  // camera line
  renderCameraStatus(s.camera || {});

  // setup
  renderSetup(s);

  // chat chips follow the state unless a question is waiting
  if (!pending && s.chips) setChips(s.chips);
}

function checklistTicked() {
  const c = [...document.querySelectorAll("#checklist input")];
  return c.length > 0 && c.every(x => x.checked);
}

function renderSetup(s) {
  const st = s.state, idle = !s.busy, ok = c => (s.allowed || []).includes(c);
  // (c) checklist: rebuilt only when the wording changes; ticks never survive movement or a reload
  const txt = (s.checklist || []).join("\n");
  if (txt !== checklistText) {
    checklistText = txt;
    $("checklist").replaceChildren(...(s.checklist || []).map(c => h("label", {},
      h("input", {type: "checkbox", onchange: gate}), h("span", {}, c))));
  }
  if (!["DISARMED", "PARKED"].includes(st)) document.querySelectorAll("#checklist input").forEach(x => { x.checked = false; });
  gate();
  // (a) room: editable only DISARMED / PARKED (the service refuses otherwise)
  const editable = idle && ["DISARMED", "PARKED"].includes(st);
  for (const id of ["rw", "rd", "rh"]) $(id).disabled = !editable;
  document.querySelectorAll("#anchors input").forEach(x => { x.disabled = !editable; });
  $("saveRoom").disabled = !editable;
  const nAct = (s.stations_active || ["A", "B", "C", "D"]).length;
  $("roomNote").textContent = editable ? `Anchors are the cable exit points of the ${nAct === 4 ? "four cables" : nAct + " active cables (" + s.stations_active.join(", ") + ")"} (x, y, z).` : "Room and anchors can only be edited while DISARMED or PARKED.";
  // three-station mode: which cables are used and where the claw goes (the centroid of the active anchors)
  $("modeNote").hidden = !s.mode_text; $("modeNote").textContent = s.mode_text || "";
  $("startPoint").textContent = s.start_point_text || "";
  if (!roomInit && s.room_m) {
    roomInit = true;
    [$("rw").value, $("rd").value, $("rh").value] = s.room_m.map(x => +x.toFixed(3));
    $("anchors").replaceChildren(...Object.entries(s.anchors_m || {}).sort().map(([id, a]) => h("div", {class: "arow"},
      h("b", {}, id), ...a.map((x, i) => h("input", {type: "number", step: "0.01", inputmode: "decimal", "aria-label": `anchor ${id} ${"xyz"[i]}`,
        value: +x.toFixed(3), "data-orig": (+x.toFixed(3)).toString(), "data-id": id, "data-axis": i})))));
  }
  // (d) progress
  const idx = STEPS.indexOf(s.detail);
  $("steps").replaceChildren(...STEPS.map((x, i) => h("li", {class: st === "READY" || i < idx ? "done" : (i === idx ? "now" : "")},
    x.replace(/_/g, " ").toLowerCase())));
  const reasons = [...new Set([s.error, ...(s.reasons || [])].filter(Boolean))];
  $("startReasons").replaceChildren(...reasons.map(r => h("li", {}, r)));
  // what the robot needs from you
  const needs = ["PAUSED", "FAULT", "RECOVERY_REQUIRED"].includes(st);
  $("needs").hidden = !needs;
  $("needsText").textContent = needs ? [s.state_text, s.reasons && s.reasons.length ? "Reason: " + s.reasons[s.reasons.length - 1] : ""].filter(Boolean).join(" ") : "";
  // recovery actions appear only where the supervisor allows them
  const map = {resume: "resume", ack: "acknowledge", recover: "recover", lower: "lower", disarm: "disarm"};
  let any = false;
  for (const [id, c] of Object.entries(map)) { const a = ok(c); $(id).hidden = !a; $(id).disabled = !idle; any = any || a; }
  $("recovery").hidden = !any;
}
function gate() {
  const allowed = S && (S.allowed || []).includes("start") && !S.busy;
  $("start").disabled = !(allowed && checklistTicked());
}

// ------------------------------------------------------------------------------------------------ setup actions
$("start").addEventListener("click", async () => {
  if (!checklistTicked()) return;
  if (await ask({title: "Start calibration?", ok: "Start",
    body: "The claw takes up slack, lifts off the floor and moves around the room. You have confirmed that nobody is under the robot and the power strip is within reach."}))
    cmd("start", {checklist: true});
});
$("resume").addEventListener("click", async () => {
  if (await ask({title: "Resume?", ok: "Resume", body: "The robot re-checks the stations and the camera, then restarts from the safest step. The claw may move."})) cmd("resume");
});
$("ack").addEventListener("click", () => cmd("acknowledge"));
$("recover").addEventListener("click", async () => {
  if (await ask({title: "Recover?", ok: "Recover", body: "Stations are re-armed and the model is re-checked against the camera. The claw may move slightly."})) cmd("recover");
});
$("lower").addEventListener("click", async () => {
  if (await ask({title: "Lower the claw to the floor?", ok: "Lower", body: "The claw moves over the marker and descends. Nobody under the robot."})) cmd("lower");
});
$("disarm").addEventListener("click", async () => {
  const t = await ask({title: "Disarm: remove holding torque", ok: "Disarm", input: "claw_supported",
    body: "The claw will fall if it is not resting on the floor. The camera must confirm it. Type claw_supported to confirm."});
  if (t) cmd("disarm", {confirm: t});
});
$("saveRoom").addEventListener("click", async () => {
  const body = {width_m: +$("rw").value, depth_m: +$("rd").value, height_m: +$("rh").value, anchors: {}};
  document.querySelectorAll("#anchors input").forEach(x => {
    const id = x.dataset.id;
    (body.anchors[id] = body.anchors[id] || [0, 0, 0])[+x.dataset.axis] = +x.value;
  });
  for (const id of Object.keys(body.anchors)) {          // send only the anchors that were edited
    const orig = [...document.querySelectorAll(`#anchors input[data-id="${id}"]`)].every(x => x.value === x.dataset.orig);
    if (orig) delete body.anchors[id];
  }
  const r = await api("/api/room", body);
  if (r.ok) { toast("Room saved."); roomInit = false; } else toast((r.data && r.data.error) || "Could not save the room", true);
  setTimeout(tick, 150);
});

async function refreshChecks() {
  lastChecks = Date.now();
  const r = await api("/api/checks");
  if (!r.ok) return;
  $("checks").replaceChildren(...Object.entries(r.data).map(([stage, miss]) => h("li", {},
    h("b", {}, stage + ": "), miss.length ? h("span", {class: "warnc"}, "unmeasured " + miss.join(", ")) : h("span", {class: "ok"}, "all measured"))));
}

async function refreshCalib() {
  calibKey = S ? S.state + "|" + S.detail + "|" + S.level : "";
  const r = await api("/api/calibration"), box = $("calib");
  box.replaceChildren();
  if (r.ok && r.data.result) {
    const res = r.data.result, val = r.data.validation || {};
    box.append(kv("Accepted", h("span", {class: val.accepted ? "ok" : "badc"}, val.accepted ? "yes" : "NO")));
    if (res.norm_rms != null) box.append(kv("Fit residual (normalised RMS)", res.norm_rms.toFixed(2)));
    if (val.witness_rms_m != null) box.append(kv("Witness RMS", (val.witness_rms_m * 1e3).toFixed(1) + " mm"));
    (res.anchors_room_m || []).forEach((a, i) => box.append(kv("Anchor " + (res.ids || ["A", "B", "C", "D"])[i] + " (m)", a.map(x => x.toFixed(3)).join(", "))));
    const idn = res.identifiability || {};
    if (idn.condition_number != null && res.ids && res.ids.length < 4) box.append(kv("Identifiability (condition number)", idn.condition_number.toFixed(0)));
    (val.reasons || []).forEach(x => box.append(kv("Note", x)));
  } else {
    box.append(h("p", {class: "muted"}, "No calibration yet. The startup makes it."));
  }
  if (S && S.trust) box.append(kv("Trust", S.level), h("p", {class: "muted small"}, trustText(S.trust)));
}

// ------------------------------------------------------------------------------------------------ events and chat
const log = $("chatlog");
function nearBottom() { return log.scrollHeight - log.scrollTop - log.clientHeight < 80; }
function scrollChat(force) { if (force || nearBottom()) log.scrollTop = log.scrollHeight; }

function addMsg(who, text, opt = {}) {
  const stick = nearBottom() || who === "me";
  const m = h("div", {class: "msg " + who + (opt.cls ? " " + opt.cls : "")}, text, h("span", {class: "t"}, fmtTime(opt.t)));
  if (opt.goto) m.append(h("button", {class: "btn go", type: "button", onclick: () => showTab(opt.goto)}, "Open " + cap(opt.goto)));
  log.append(m);
  while (log.children.length > 200) log.firstChild.remove();
  if (stick) log.scrollTop = log.scrollHeight;
}
function eventClass(e) {
  if (e.kind === "error" || e.kind === "refused") return "bad";
  if (e.kind === "pause" || e.kind === "reason") return "warn";
  if (e.kind === "state") return /^(FAULT|RECOVERY)/.test(e.text) ? "bad" : /^(PAUSED)/.test(e.text) ? "warn" : /^(READY|PARKED)/.test(e.text) ? "good" : "";
  return "";
}
function takeEvents(d) {
  if (d.last_id < lastEvent) { lastEvent = 0; firstEvents = true; recent = []; }
  const evs = d.events || [];
  const shown = firstEvents ? evs.slice(-6) : evs;                 // on load: just the last few as history
  for (const e of shown) if (e.kind !== "chat") addMsg("sys", e.text, {cls: eventClass(e) + (firstEvents ? " hist" : ""), t: e.t});
  for (const e of evs) recent.push(e);
  recent = recent.slice(-8);
  firstEvents = false;
  if (evs.length) lastEvent = evs[evs.length - 1].id;
  $("homeEvents").replaceChildren(...recent.slice().reverse().map(e => h("li", {}, h("span", {class: "k"}, fmtTime(e.t)), e.text)));
}

function setChips(list) {
  const items = (list || []).filter(t => !(pending && (t === "Yes" || t === "No")));
  $("chips").replaceChildren(...items.map(t => h("button", {class: "chip", type: "button", onclick: () => send(t)}, t)));
}
let pendTimer = null;
function setPending(p) {
  clearInterval(pendTimer);
  if (!p) { pending = null; $("pendingBar").hidden = true; return; }
  pending = {action: p.action, until: Date.now() + (p.expires_in_s || 30) * 1000};
  $("pendingBar").hidden = false;
  const upd = () => {
    const left = Math.ceil((pending.until - Date.now()) / 1000);
    if (left <= 0) { setPending(null); addMsg("sys", "That question timed out; nothing was done.", {cls: "warn"}); if (S) setChips(S.chips); return; }
    $("pendingText").textContent = `Waiting for your answer: ${p.action.replace("_", " ")} (${left} s)`;
  };
  upd(); pendTimer = setInterval(upd, 500);
}

async function send(text) {
  text = (text || "").trim();
  if (!text) return;
  addMsg("me", text);
  const r = await api("/api/say", {text, checklist: checklistTicked()});
  if (!r.ok) { addMsg("sys", (r.data && r.data.error) || "The robot service did not answer.", {cls: "bad"}); return; }
  const d = r.data;
  setPending(d.pending_confirm);
  addMsg("robot", d.reply, {goto: d.goto});
  setChips(d.chips);
  speakOut(d.reply);
  if (d.command_run) setTimeout(tick, 150);
}
$("composer").addEventListener("submit", e => { e.preventDefault(); const v = $("say").value; $("say").value = ""; send(v); });
$("yes").addEventListener("click", () => send("yes"));
$("no").addEventListener("click", () => send("no"));

// ---- optional voice (browser speech recognition / synthesis; hidden when the browser has none)
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const canTalk = "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
let rec = null;
if (SR) {
  $("mic").hidden = false;
  $("mic").addEventListener("click", () => {
    if (rec) { rec.stop(); return; }
    rec = new SR();
    rec.lang = navigator.language || "en-US"; rec.interimResults = false; rec.maxAlternatives = 1;
    rec.onresult = ev => { const t = ev.results[0][0].transcript; if (t) send(t); };
    rec.onerror = ev => addMsg("sys", "Voice input did not work (" + ev.error + "). Browsers often allow it only on https or localhost; typing always works.", {cls: "warn"});
    rec.onend = () => { rec = null; $("mic").classList.remove("on"); };
    try { rec.start(); $("mic").classList.add("on"); } catch (e) { rec = null; }
  });
}
if (canTalk) {
  $("speakWrap").hidden = false;
  $("speak").checked = store.get("rc_speak") === "1";
  $("speak").addEventListener("change", () => { store.set("rc_speak", $("speak").checked ? "1" : "0"); if (!$("speak").checked) speechSynthesis.cancel(); });
}
function speakOut(text) {
  if (!canTalk || !$("speak").checked) return;
  speechSynthesis.cancel();
  speechSynthesis.speak(new SpeechSynthesisUtterance(text));
}

// ------------------------------------------------------------------------------------------------ camera
let camWatch = null, camTimer = null, camMode = null, camGot = false, camUrl = null;
function camStart() {
  camStop();
  if (!TOKEN) return;
  camMode = "stream"; camGot = false;
  const img = $("cam");
  $("camTransport").textContent = "MJPEG stream (about 5 fps)";
  img.onload = () => { camGot = true; $("camOverlay").hidden = true; };
  img.onerror = () => camFallback("stream error");
  img.src = "/api/stream.mjpg?token=" + encodeURIComponent(TOKEN) + "&_=" + Date.now();   // the one URL that carries the token
  camWatch = setTimeout(() => { if (!camGot) camFallback("no stream frame within 4 s"); }, 4000);
}
function camFallback(why) {
  clearTimeout(camWatch);
  const img = $("cam"); img.onload = img.onerror = null; img.removeAttribute("src");
  camMode = "still"; $("camTransport").textContent = "still JPEG, twice a second (" + why + ")";
  pollStill();
}
async function pollStill() {
  if (camMode !== "still" || tab !== "camera") return;
  try {
    const r = await fetch("/api/frame.jpg", {headers: {"X-Token": TOKEN}, cache: "no-store"});
    if (r.ok) {
      const u = URL.createObjectURL(await r.blob());
      $("cam").src = u; if (camUrl) URL.revokeObjectURL(camUrl);
      camUrl = u; $("camOverlay").hidden = true;
    }
  } catch (e) { /* the status poll shows the connection state */ }
  camTimer = setTimeout(pollStill, 500);
}
function camStop() {
  clearTimeout(camWatch); clearTimeout(camTimer);
  const img = $("cam"); img.onload = img.onerror = null; img.removeAttribute("src");
  camMode = null;
  if (camUrl) { URL.revokeObjectURL(camUrl); camUrl = null; }
}
function renderCameraStatus(c) {
  const live = c.available && c.age_s != null && c.age_s <= 2;
  $("camLive").textContent = !c.available ? "NO FRAME" : (live ? "LIVE" : "STALE");
  $("camLive").className = "pill camlive " + (live ? "good" : "bad");
  $("camAge").textContent = c.age_s == null ? "-" : c.age_s.toFixed(1) + " s" + (c.frame_id != null ? "  (frame " + c.frame_id + ")" : "");
  const d = c.detection || {};
  $("camDet").textContent = d.text || "-"; $("camDet").className = d.ok === true ? "ok" : d.ok === false ? "warnc" : "";
  $("camSrc").textContent = c.source === "sim" ? "simulated claw view" : (c.mode ? "claw camera " + c.mode : "claw camera");
  if (!c.available) { $("camOverlay").textContent = "No camera frame yet"; $("camOverlay").hidden = false; }
}
document.addEventListener("visibilitychange", () => {
  if (document.hidden) camStop(); else if (tab === "camera") camStart();
});

// ------------------------------------------------------------------------------------------------ main loop
async function tick() {
  if (ticking || !TOKEN) return;
  ticking = true;
  try {
    const st = await api("/api/status");
    if (st.ok) renderStatus(st.data);
    const ev = await api("/api/events?since=" + lastEvent);
    if (ev.ok) takeEvents(ev.data);
    if (tab === "setup") {
      const n = Date.now();
      if (n - lastChecks > 5000) refreshChecks();
      if (S && calibKey !== S.state + "|" + S.detail + "|" + S.level) refreshCalib();   // the report changes with the startup, not on a timer
    }
  } finally { ticking = false; }
}
function loop() { tick().finally(() => setTimeout(loop, document.hidden ? 4000 : 1000)); }

window.addEventListener("resize", layout);
layout();
showTab(new URLSearchParams(location.search).get("tab") || store.get("rc_tab") || "home");
if (!TOKEN) showConnect();
loop();
})();
