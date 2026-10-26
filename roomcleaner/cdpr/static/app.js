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
const TABS = ["home", "camera", "setup", "map", "chat"];

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
// Who is talking: a random id made at every page load and sent with every request. The chat keeps a pending "yes?" question
// per client id, so another phone (which shares the session token) cannot confirm it (review F1). crypto.randomUUID needs
// https, so build the id from getRandomValues (works on plain http).
function newClientId() {
  const a = new Uint8Array(16);
  try { crypto.getRandomValues(a); } catch (e) { for (let i = 0; i < a.length; i++) a[i] = Math.floor(Math.random() * 256); }
  return Array.from(a, b => b.toString(16).padStart(2, "0")).join("");
}
const CLIENT = newClientId();
// The token stays in sessionStorage; take it out of the address bar and history (review F6). Only when it was really stored,
// so a reload still works where storage is blocked.
function stripTokenFromUrl() {
  try {
    const u = new URL(location.href);
    u.searchParams.delete("token");
    const hp = new URLSearchParams(u.hash.replace(/^#/, ""));
    hp.delete("token");
    u.hash = hp.toString();
    history.replaceState(history.state, "", u.pathname + u.search + u.hash);
  } catch (e) { /* very old browser: the token stays visible */ }
}
function readToken() {
  const q = new URLSearchParams(location.search).get("token");
  const f = new URLSearchParams(location.hash.replace(/^#/, "")).get("token");
  const t = q || f;
  if (t) {
    store.set("rc_token", t);
    if (store.get("rc_token") === t) stripTokenFromUrl();
    return t;
  }
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
async function api(path, body, method) {
  const headers = {"X-Token": TOKEN, "X-Client": CLIENT};
  const opt = {headers, cache: "no-store"};
  if (body !== undefined) { opt.method = method || "POST"; headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
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
  layout();            // the overlay ends above PAUSE and the emergency-stop line (review F14): it needs the dock height
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
  if (r.ok) {            // the wording comes from the service, built from what the stations really report (review F2)
    const hd = r.data && r.data.hold || {};
    const calm = ["holding", "stopping", "disarmed"].includes(hd.kind);
    toast((hd.text || "Pause sent, but the stations' holding state was not reported: check the station tiles on Home and stay clear of the claw.")
      + " This is not an emergency stop.", !calm, 5000);
  } else toast("PAUSE DID NOT REACH THE ROBOT SERVICE. Use the power strip if the claw is in danger. " + ((r.data && r.data.error) || ""), true);
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
  if (name === "map") mapShow();
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

  mapGate();

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

// ------------------------------------------------------------------------------------------------ map (docs/ROOM_MAP_SPEC.md)
// Top view of the room in room coordinates (metres; origin at the floor corner under anchor A, x along A-B). The SVG uses
// x as is and y flipped (svg y = depth - y), so A is bottom left. Everything is stored in metres; units only change the text.
const SVGNS = "http://www.w3.org/2000/svg";
const INCH = 0.0254, SNAP_WALL = 0.05, MIN_SIZE = 0.03, UNDO_MAX = 20, PREVIEW_MS = 300;
const KINDS = {   // what a palette button adds
  square: {shape: "box", length_m: 0.5, width_m: 0.5, height_m: 0.75},
  rect: {shape: "box", length_m: 1.0, width_m: 0.5, height_m: 0.75},
  circle: {shape: "cylinder", diameter_m: 0.5, height_m: 0.75},
};
const CHIPS = {   // typical sizes; the user edits them afterwards ("hang": a bottom height below the ceiling)
  "Bed": {shape: "box", length_m: 2.03, width_m: 1.52, height_m: 0.65},
  "Desk": {shape: "box", length_m: 1.22, width_m: 0.61, height_m: 0.76},
  "Dresser": {shape: "box", length_m: 1.52, width_m: 0.46, height_m: 0.86},
  "Shelf": {shape: "box", length_m: 0.80, width_m: 0.40, height_m: 1.90},
  "Chair": {shape: "box", length_m: 0.50, width_m: 0.50, height_m: 0.90},
  "Lamp": {shape: "cylinder", diameter_m: 0.40, height_m: 1.60},
  "Ceiling fan": {shape: "cylinder", diameter_m: 1.10, hang: 0.45},
  "Other": {},
};
const M = {
  info: null,                // GET /api/room_map (room, anchors, usable area, ...)
  shapes: [], hamper: null,  // the draft
  savedKey: "",              // JSON of the saved draft: dirty = draft differs
  units: "ft-in", sel: null, undo: [], loaded: false,
  cov: null, covOn: false, covTimer: null, covSeq: 0,
  px: 100,                   // screen px per metre (for handle and text sizes)
  drag: null, raf: 0,
};

// ---- units
function fmtLen(m) {
  if (m == null || !isFinite(m)) return "";
  if (M.units === "m") return m.toFixed(2) + " m";
  const tot = Math.round(m / INCH), ft = Math.floor(tot / 12), inch = tot - 12 * ft;
  return ft ? `${ft}'${inch}"` : `${inch}"`;
}
// `5'6"`, `5 ft 6 in`, `66 in`, `66"`, `1.68 m`, `168 cm`, `1680 mm`; a bare number is inches (ft-in) or metres (m). Returns m or null.
function parseLen(text) {
  let t = String(text || "").trim().toLowerCase().replace(/[’‘′`]/g, "'").replace(/[“”″]/g, '"').replace(/''/g, '"');
  const n = "(\\d+(?:[.,]\\d+)?|[.,]\\d+)", num = x => parseFloat(x.replace(",", "."));
  let m;
  if ((m = t.match(new RegExp(`^${n}\\s*(?:'|ft|feet|foot)\\s*(?:${n}\\s*(?:"|in|inch|inches)?)?$`)))) return (num(m[1]) * 12 + (m[2] ? num(m[2]) : 0)) * INCH;
  if ((m = t.match(new RegExp(`^${n}\\s*(?:"|in|inch|inches)$`)))) return num(m[1]) * INCH;
  if ((m = t.match(new RegExp(`^${n}\\s*(m|cm|mm)$`)))) return num(m[1]) * {m: 1, cm: 0.01, mm: 0.001}[m[2]];
  if ((m = t.match(new RegExp(`^${n}$`)))) return M.units === "m" ? num(m[1]) : num(m[1]) * INCH;
  return null;
}
const snapIn = v => Math.round(v / INCH) * INCH;

// ---- model helpers
const roomW = () => M.info.room_m[0], roomD = () => M.info.room_m[1], roomH = () => M.info.room_m[2];
const isSquare = o => o.shape === "box" && Math.abs(o.length_m - o.width_m) < 1e-6;
const byId = id => M.shapes.find(o => o.id === id);
function halfExtents(o) {      // axis-aligned half sizes of the footprint
  if (o.shape === "cylinder") return [o.diameter_m / 2, o.diameter_m / 2];
  const a = o.yaw_deg * Math.PI / 180, c = Math.abs(Math.cos(a)), s = Math.abs(Math.sin(a));
  return [c * o.length_m / 2 + s * o.width_m / 2, s * o.length_m / 2 + c * o.width_m / 2];
}
function snapPos(o) {          // 1 in grid, flush to a wall within 5 cm, centre inside the room
  const [hx, hy] = halfExtents(o);
  let x = snapIn(o.x), y = snapIn(o.y);
  if (x - hx < SNAP_WALL) x = hx; else if (roomW() - (x + hx) < SNAP_WALL) x = roomW() - hx;
  if (y - hy < SNAP_WALL) y = hy; else if (roomD() - (y + hy) < SNAP_WALL) y = roomD() - hy;
  o.x = Math.min(Math.max(x, 0), roomW()); o.y = Math.min(Math.max(y, 0), roomD());
}
function nextId() { let n = 1; while (M.shapes.some(o => o.id === "o" + n)) n++; return "o" + n; }
function draftKey() { return JSON.stringify({s: M.shapes, h: M.hamper, u: M.units}); }     // the units are saved with the map
function snapshot() {
  M.undo.push(draftKey());
  if (M.undo.length > UNDO_MAX) M.undo.shift();
}
function freeSpot(o) {         // the free floor point nearest the start point where the new footprint overlaps nothing
  const [hx, hy] = halfExtents(o), c = M.info.start_point_m, b = M.info.usable_box, pts = [];
  for (let x = b[0][0] + hx; x <= b[1][0] - hx + 1e-9; x += 0.1) for (let y = b[0][1] + hy; y <= b[1][1] - hy + 1e-9; y += 0.1) pts.push([x, y]);
  pts.sort((p, q) => Math.hypot(p[0] - c[0], p[1] - c[1]) - Math.hypot(q[0] - c[0], q[1] - c[1]));
  const hp = M.hamper, hr = hp ? (hp.radius_m || 0.2) : 0;
  const clear = ([x, y]) => M.shapes.every(s => {
    const [sx, sy] = halfExtents(s);
    return Math.abs(s.x - x) >= sx + hx + 0.05 || Math.abs(s.y - y) >= sy + hy + 0.05;
  }) && (!hp || Math.abs(hp.x - x) >= hr + hx + 0.05 || Math.abs(hp.y - y) >= hr + hy + 0.05)
    // and never over the claw's landing spot (where it is lowered to the floor): the service refuses a map that covers it
    && (M.info.landing_m || []).every(([lx, ly]) => Math.abs(lx - x) >= hx + keepClear() || Math.abs(ly - y) >= hy + keepClear());
  return pts.find(clear) || c;
}
const keepClear = () => (M.info.margin_m || 0.1) + (M.info.claw_body_radius_m || 0.07) + 0.05;
function addShape(kind, at) {
  const t = KINDS[kind];
  const o = Object.assign({id: nextId(), name: "", x: 0, y: 0, z_low_m: 0}, t, t.shape === "box" ? {yaw_deg: 0} : {});
  [o.x, o.y] = at || freeSpot(o);
  snapPos(o);
  snapshot();
  M.shapes.push(o); M.sel = o.id;
  edited(`Added a ${kind === "rect" ? "rectangle" : kind}. Drag it into place, then set its size and height below.`);
}
function edited(msg) {         // after every change of the draft
  mapRender();
  if (msg !== undefined) mapMsg(msg);
  if (M.covOn) schedulePreview();
}
function mapMsg(text, cls) { const e = $("mapMsg"); e.textContent = text || ""; e.className = "small mapmsg" + (cls ? " " + cls : ""); }
function dirty() { return M.loaded && draftKey() !== M.savedKey; }
function shapeLabel(o) {
  const name = o.name || (o.shape === "cylinder" ? "Circle" : isSquare(o) ? "Square" : "Rectangle");
  return o.z_low_m > 0 ? `${name} (hangs, from ${fmtLen(o.z_low_m)})` : `${name} ${fmtLen(o.height_m)}`;
}

// ---- drawing
function el(tag, attrs, parent) {
  const e = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, v);
  if (parent) parent.append(e);
  return e;
}
const sy = y => roomD() - y;
function mapRender() {
  const svg = $("map");
  if (!M.info) return;
  const W = roomW(), D = roomD(), pad = 0.16;
  svg.setAttribute("viewBox", `${-pad} ${-pad} ${W + 2 * pad} ${D + 2 * pad}`);
  M.px = (svg.clientWidth || 320) / (W + 2 * pad);
  const fs = 12.5 / M.px, sw = 1.5 / M.px, dash = `${5 / M.px} ${4 / M.px}`;      // dashes in screen px, not metres
  svg.replaceChildren();
  el("rect", {class: "floor", x: 0, y: 0, width: W, height: D, "stroke-width": 3 / M.px}, svg);
  const clip = el("clipPath", {id: "roomClip"}, el("defs", {}, svg));
  el("rect", {x: 0, y: 0, width: W, height: D}, clip);
  const cov = el("g", {class: "cov", "clip-path": "url(#roomClip)"}, svg);
  if (M.covOn && M.cov) drawCoverage(cov);
  const ub = M.info.usable_box;
  if (M.info.usable_triangle) el("polygon", {class: "usable", points: M.info.usable_triangle.map(p => `${p[0]},${sy(p[1])}`).join(" "), "stroke-width": sw, "stroke-dasharray": dash}, svg);
  else el("rect", {class: "usable", x: ub[0][0], y: sy(ub[1][1]), width: ub[1][0] - ub[0][0], height: ub[1][1] - ub[0][1], "stroke-width": sw, "stroke-dasharray": dash}, svg);
  const sp = M.info.start_point_m;
  el("circle", {class: "start", cx: sp[0], cy: sy(sp[1]), r: 6 / M.px, "stroke-width": sw}, svg);
  const fixed = [];               // labels that stay where they are (anchors); the others are placed around them
  for (const [id, a] of Object.entries(M.info.anchors).sort()) {
    const ax = Math.min(Math.max(a.xyz[0], 0), W), ay = Math.min(Math.max(a.xyz[1], 0), D);
    el("circle", {class: "anchor" + (a.active ? "" : " off"), cx: ax, cy: sy(ay), r: 7 / M.px}, svg);
    const t = el("text", {class: "alabel" + (a.active ? "" : " off"), x: ax + (ax < W / 2 ? 10 : -10) / M.px, y: sy(ay) + (ay < D / 2 ? -6 : 16) / M.px,
      "text-anchor": ax < W / 2 ? "start" : "end", "font-size": fs}, svg);
    t.textContent = a.active ? id : id + " (not used)";
    fixed.push(t);
  }
  // hanging shapes first, so what stands on the floor under them stays visible and on top for the finger
  const order = M.shapes.filter(o => o.z_low_m > 0).concat(M.shapes.filter(o => !(o.z_low_m > 0)));
  for (const o of order) drawShape(svg, o);
  const labels = [];
  let hamperLabel = null;
  if (M.hamper) {
    const hr = M.hamper.radius_m || 0.2;
    el("circle", {class: "hring" + (M.sel === "hamper" ? " sel" : ""), cx: M.hamper.x, cy: sy(M.hamper.y), r: hr, "stroke-width": 3 / M.px}, svg);
    const hp = el("circle", {class: "hamper", cx: M.hamper.x, cy: sy(M.hamper.y), r: Math.max(hr, 24 / M.px), "data-hamper": "1"}, svg);
    hp.setAttribute("aria-label", "hamper");     // the whole marker (at least a finger wide) takes the drag
    hamperLabel = el("text", {class: "hlabel", x: M.hamper.x, y: sy(M.hamper.y), "text-anchor": "middle", "dominant-baseline": "central", "font-size": fs}, svg);
    hamperLabel.textContent = "Hamper";
    labels.push(hamperLabel);
  }
  for (const o of order) {
    const t = el("text", {class: "slabel", x: o.x, y: sy(o.y), "text-anchor": "middle", "dominant-baseline": "central", "font-size": fs}, svg);
    t.textContent = shapeLabel(o);
    labels.push(t);
  }
  placeLabels(svg, fixed, labels, pad);
  if (hamperLabel) {              // an opaque pill behind "Hamper": readable on a shape or on the overlay tint
    const b = hamperLabel.getBBox(), m = 3 / M.px;
    const pill = el("rect", {class: "hpill", x: b.x - m, y: b.y - m / 2, width: b.width + 2 * m, height: b.height + m, rx: 4 / M.px});
    svg.insertBefore(pill, hamperLabel);
  }
  const sel = byId(M.sel);
  if (sel) drawHandles(svg, sel);
  $("mapEmpty").hidden = M.shapes.length > 0;
  $("mapUndo").disabled = !M.undo.length;
  const d = dirty();
  $("mapDot").hidden = !d; $("mapRevert").hidden = !d;
  mapGate();
  renderInspector();
}
function drawShape(svg, o) {
  // the visible body, and over it the grab area: the same outline, or at least a finger (44 px) wide for a thin pole
  const g = el("g", {transform: `translate(${o.x} ${sy(o.y)}) rotate(${o.shape === "box" ? -o.yaw_deg : 0})`, "data-id": o.id}, svg);
  const cls = "sbody" + (o.id === M.sel ? " sel" : "") + (o.z_low_m > 0 ? " hang" : "");
  const st = {"stroke-width": (o.id === M.sel ? 3 : 1.5) / M.px};
  if (o.z_low_m > 0) st["stroke-dasharray"] = `${6 / M.px} ${4 / M.px}`;        // hangs from the ceiling: dashed outline
  const f = 44 / M.px;
  if (o.shape === "cylinder") {
    el("circle", Object.assign({class: cls, cx: 0, cy: 0, r: o.diameter_m / 2}, st), g);
    el("circle", {class: "shape", cx: 0, cy: 0, r: Math.max(o.diameter_m, f) / 2, "data-id": o.id}, g);
  } else {
    el("rect", Object.assign({class: cls, x: -o.length_m / 2, y: -o.width_m / 2, width: o.length_m, height: o.width_m}, st), g);
    const L = Math.max(o.length_m, f), Wd = Math.max(o.width_m, f);
    el("rect", {class: "shape", x: -L / 2, y: -Wd / 2, width: L, height: Wd, "data-id": o.id}, g);
  }
}
function placeLabels(svg, fixed, labels, pad) {
  // Greedy, simple: each label (hamper first, then the shapes) takes the first spot near its own centre (centre, then one, two,
  // three lines above or below, then a little to the side) that overlaps no label already placed and stays inside the drawing.
  // One layout read for all the boxes, then writes only.
  const gap = 2 / M.px, W = roomW(), D = roomD();
  const boxes = fixed.map(t => t.getBBox());
  const sizes = labels.map(t => { const b = t.getBBox(); return [b.width, b.height, +t.getAttribute("x"), +t.getAttribute("y")]; });
  const hit = (a, b) => a.x < b.x + b.width + gap && b.x < a.x + a.width + gap && a.y < b.y + b.height + gap && b.y < a.y + a.height + gap;
  labels.forEach((t, k) => {
    const [w, hgt, cx, cy] = sizes[k];
    let best = null;
    search:
    for (const j of [0, -1, 1, -2, 2, -3, 3, -4, 4, -5, 5]) {
      for (const i of [0, -0.6, 0.6, -1.2, 1.2]) {
        const x = Math.min(Math.max(cx + i * w, -pad + w / 2 + gap), W + pad - w / 2 - gap);
        const y = Math.min(Math.max(cy + j * (hgt + gap), -pad + hgt / 2), D + pad - hgt / 2);
        const b = {x: x - w / 2, y: y - hgt / 2, width: w, height: hgt};
        if (!best) best = [x, y, b];
        if (!boxes.some(o => hit(o, b))) { best = [x, y, b]; break search; }
      }
    }
    t.setAttribute("x", best[0]); t.setAttribute("y", best[1]);
    boxes.push(best[2]);
  });
}
function handlePoints(o) {     // [{kind, x, y}] in room coordinates
  if (o.shape === "cylinder") return [{kind: "rim", x: o.x + o.diameter_m / 2, y: o.y}];
  const a = o.yaw_deg * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
  const at = (u, v) => ({x: o.x + c * u - s * v, y: o.y + s * u + c * v});
  if (isSquare(o) && !o._rect) return [Object.assign({kind: "side"}, at(o.length_m / 2, 0))];
  return [[1, 1], [-1, 1], [-1, -1], [1, -1]].map(([i, j]) => Object.assign({kind: "corner", i, j}, at(i * o.length_m / 2, j * o.width_m / 2)));
}
function drawHandles(svg, o) {
  for (const h of handlePoints(o)) {
    el("circle", {class: "handle", cx: h.x, cy: sy(h.y), r: 8 / M.px, "stroke-width": 2.5 / M.px}, svg);
    el("circle", {class: "hit", cx: h.x, cy: sy(h.y), r: 22 / M.px, "data-handle": h.kind, "data-i": h.i || 0, "data-j": h.j || 0}, svg);
  }
}
function drawCoverage(g) {
  const c = M.cov, kinds = c.reasons.map(r => r.kind), paths = {ok: "", shape: "", area: "", trust: ""}, s = c.cell_m;
  for (let k = 0; k < c.cells.length; k++) {
    const ix = k % c.nx, iy = Math.floor(k / c.nx), x = c.x0 + ix * s, y = c.y0 + iy * s;
    paths[kinds[c.cells[k]]] += `M${x.toFixed(3)} ${sy(y + s).toFixed(3)}h${s}v${s}h${-s}z`;
  }
  for (const [k, d] of Object.entries(paths)) if (d) el("path", {class: "cov-" + k, d}, g);
}

// ---- pointer interaction (pointer events; moves are applied once per animation frame)
function roomPoint(ev) {
  const m = M.drag && M.drag.ctm ? M.drag.ctm : $("map").getScreenCTM().inverse();
  const p = new DOMPoint(ev.clientX, ev.clientY).matrixTransform(m);
  return [p.x, roomD() - p.y];
}
$("map").addEventListener("pointerdown", ev => {
  if (!M.info) return;
  const t = ev.target, ctm = $("map").getScreenCTM().inverse();
  M.drag = {ctm, id: ev.pointerId, moved: false, before: draftKey()};
  const [x, y] = roomPoint(ev);
  const o = byId(M.sel);
  if (t.dataset.handle && o) {
    M.drag.kind = "resize"; M.drag.h = t.dataset.handle;
    const a = (o.yaw_deg || 0) * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
    if (t.dataset.handle === "corner") {      // the opposite corner stays where it is
      const u = -t.dataset.i * o.length_m / 2, v = -t.dataset.j * o.width_m / 2;
      M.drag.fix = [o.x + c * u - s * v, o.y + s * u + c * v];
    } else if (t.dataset.handle === "side") M.drag.fix = [o.x - c * o.length_m / 2, o.y - s * o.length_m / 2];
  } else if (t.dataset.id) {
    M.sel = t.dataset.id; const s = byId(M.sel);
    M.drag.kind = "move"; M.drag.off = [s.x - x, s.y - y];
  } else if (t.dataset.hamper) {
    M.sel = "hamper"; M.drag.kind = "hamper"; M.drag.off = [M.hamper.x - x, M.hamper.y - y];
  } else {
    M.drag.kind = "none"; M.drag.at = [x, y];
  }
  $("map").setPointerCapture(ev.pointerId);
  if (M.drag.kind !== "none") mapRender();
  ev.preventDefault();
});
$("map").addEventListener("pointermove", ev => {
  if (!M.drag || ev.pointerId !== M.drag.id || M.drag.kind === "none") return;
  M.drag.last = roomPoint(ev);
  if (!M.raf) M.raf = requestAnimationFrame(applyDrag);
});
function applyDrag() {
  M.raf = 0;
  const d = M.drag;
  if (!d || !d.last) return;
  const [x, y] = d.last;
  d.moved = true;
  if (d.kind === "hamper") { M.hamper.x = clamp(x + d.off[0], 0, roomW()); M.hamper.y = clamp(y + d.off[1], 0, roomD()); }
  const o = byId(M.sel);
  if (o && d.kind === "move") { o.x = clamp(x + d.off[0], 0, roomW()); o.y = clamp(y + d.off[1], 0, roomD()); }
  if (o && d.kind === "resize") {
    if (d.h === "rim") o.diameter_m = Math.max(MIN_SIZE, 2 * Math.hypot(x - o.x, y - o.y));
    else {
      const a = (o.yaw_deg || 0) * Math.PI / 180, c = Math.cos(a), s = Math.sin(a), dx = x - d.fix[0], dy = y - d.fix[1];
      let du = c * dx + s * dy, dv = -s * dx + c * dy;
      if (d.h === "side") { du = Math.max(MIN_SIZE, du); dv = 0; o.length_m = o.width_m = du; }
      else { o.length_m = Math.max(MIN_SIZE, Math.abs(du)); o.width_m = Math.max(MIN_SIZE, Math.abs(dv)); o._rect = true; }
      const u = Math.sign(du || 1) * o.length_m / 2, v = d.h === "side" ? 0 : Math.sign(dv || 1) * o.width_m / 2;
      o.x = d.fix[0] + c * u - s * v; o.y = d.fix[1] + s * u + c * v;
    }
  }
  mapRender();
}
const clamp = (v, a, b) => Math.min(Math.max(v, a), b);
function endDrag(ev) {
  const d = M.drag;
  if (!d || ev.pointerId !== d.id) return;
  if (M.raf) { cancelAnimationFrame(M.raf); M.raf = 0; applyDrag(); }
  M.drag = null;
  if (d.kind === "none") {                     // a tap on the floor: deselect, or explain the cell under the finger
    M.sel = null;
    const why = M.covOn && M.cov ? cellReason(d.at) : "";
    mapRender();
    if (why) mapMsg(why);
    return;
  }
  const o = byId(M.sel);
  if (o) {
    delete o._rect;
    if (d.kind === "resize") {
      if (o.shape === "cylinder") o.diameter_m = Math.max(MIN_SIZE, snapIn(o.diameter_m));
      else { o.length_m = Math.max(MIN_SIZE, snapIn(o.length_m)); o.width_m = Math.max(MIN_SIZE, snapIn(o.width_m)); }
    }
    snapPos(o);
  }
  if (M.hamper && d.kind === "hamper") { M.hamper.x = snapIn(M.hamper.x); M.hamper.y = snapIn(M.hamper.y); }
  if (d.moved && draftKey() !== d.before) {
    M.undo.push(d.before); if (M.undo.length > UNDO_MAX) M.undo.shift();
    edited("");
  } else mapRender();
}
$("map").addEventListener("pointerup", endDrag);
$("map").addEventListener("pointercancel", endDrag);
function cellReason([x, y]) {
  const c = M.cov, ix = Math.floor((x - c.x0) / c.cell_m), iy = Math.floor((y - c.y0) / c.cell_m);
  if (ix < 0 || iy < 0 || ix >= c.nx || iy >= c.ny) return "";
  const r = c.reasons[c.cells[iy * c.nx + ix]];
  return `Here (${fmtLen(x)}, ${fmtLen(y)}): ${r.kind === "ok" ? "the robot can pick things up here" : plainNames(r.text)}.`;
}

function displayName(o) { return o.name || (o.shape === "cylinder" ? "Circle" : isSquare(o) ? "Square" : "Rectangle"); }
function plainNames(text) {    // the service names an unnamed shape by its id ("shape o3"): show its label instead
  return String(text).replace(/\bshape (o\d+|[A-Za-z0-9_-]+)\b/g, (m, id) => { const o = byId(id); return o ? "the " + displayName(o) : "a shape"; });
}

// ---- palette: tap adds in the middle of the free floor; dragging a button onto the map drops the shape there
document.querySelectorAll(".pal").forEach(b => {
  let start = null, dragging = false, suppress = false;
  b.addEventListener("pointerdown", ev => { start = [ev.clientX, ev.clientY]; dragging = false; b.setPointerCapture(ev.pointerId); });
  b.addEventListener("pointermove", ev => {
    if (!start) return;
    if (!dragging && Math.hypot(ev.clientX - start[0], ev.clientY - start[1]) > 10) dragging = true;
    if (dragging) {
      const g = $("mapGhost");
      g.hidden = false; g.className = "ghost" + (b.dataset.kind === "circle" ? " circle" : "");
      g.style.left = ev.clientX + "px"; g.style.top = ev.clientY + "px";
    }
  });
  const finish = (ev, cancel) => {
    $("mapGhost").hidden = true;
    if (!start) return;
    start = null;
    if (!dragging) return;
    dragging = false; suppress = true; setTimeout(() => { suppress = false; }, 400);
    const r = $("map").getBoundingClientRect();
    if (cancel || !M.info || ev.clientX < r.left || ev.clientX > r.right || ev.clientY < r.top || ev.clientY > r.bottom) return;
    const [x, y] = roomPoint(ev);
    addShape(b.dataset.kind, [x, y]);
  };
  b.addEventListener("pointerup", ev => finish(ev, false));
  b.addEventListener("pointercancel", ev => finish(ev, true));
  b.addEventListener("click", () => { if (!suppress && M.info) addShape(b.dataset.kind); });
});

// ---- inspector (the selected shape or the hamper)
function field(label, value, onset, opts = {}) {
  const inp = h("input", {type: "text", inputmode: opts.numeric ? "decimal" : "text", autocomplete: "off", spellcheck: "false",
    "aria-label": label, value, placeholder: opts.placeholder || ""});
  const lab = h("label", {}, label, inp);
  let typed = false;              // typing the shown value again still sets it exactly (2'6" is 0.762 m, not the 0.75 shown as 2'6")
  inp.addEventListener("input", () => { typed = true; });
  const commit = () => {
    if (!typed && inp.value === value) return;
    typed = false;
    const ok = onset(inp.value);
    if (ok === false) { lab.classList.add("err"); mapMsg(`${label}: "${inp.value}" is not a length I understand (try 5'6", 66 in, 1.68 m or 168 cm).`, "bad"); }
    else if (typeof ok === "string") { lab.classList.add("err"); mapMsg(`${label}: ${ok}`, "bad"); }
  };
  inp.addEventListener("change", commit);
  inp.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); inp.blur(); } });
  return lab;
}
function lenField(label, o, key, apply, check) {
  return field(label, fmtLen(o[key]), txt => {
    const v = parseLen(txt);
    if (v == null || !(v >= 0)) return false;
    const why = check ? check(v) : null;
    if (why) return why;
    change(() => apply ? apply(v) : (o[key] = v));
    return true;
  }, {placeholder: M.units === "m" ? "e.g. 1.68 m" : `e.g. 5'6"`});
}
// plain checks in the user's units, so a refusal never has to come back from the service (M-2, L-4)
const MIN_LEN = 0.021;
const sizeCheck = v => v < MIN_LEN ? `${fmtLen(v)} is not a size the robot can avoid: it must be more than 1 inch (2 cm).`
  : v > Math.max(roomW(), roomD()) ? `${fmtLen(v)} is longer than the room (${fmtLen(roomW())} x ${fmtLen(roomD())}).` : null;
const topCheck = o => v => v < MIN_LEN ? `${fmtLen(v)} is not a height: give the real height of the furniture.`
  : v > roomH() + 0.05 ? `${fmtLen(v)} is above the ceiling (${fmtLen(roomH())}).`
  : v <= o.z_low_m ? `the top must be above its bottom (${fmtLen(o.z_low_m)}).` : null;
const bottomCheck = o => v => v >= o.height_m ? `the bottom must be below its top (${fmtLen(o.height_m)}).` : null;
function draftProblems() {     // the same rules as the service, in plain words and the user's units
  const out = [];
  for (const o of M.shapes) {
    const n = displayName(o), sizes = o.shape === "cylinder" ? [o.diameter_m] : [o.length_m, o.width_m];
    for (const v of sizes) { const w = sizeCheck(v); if (w) out.push(`${n}: ${w}`); }
    const t = topCheck(o)(o.height_m); if (t) out.push(`${n}: ${t}`);
  }
  return out;
}
function change(fn, msg) { snapshot(); fn(); edited(msg === undefined ? "" : msg); }
function renderInspector() {
  const box = $("insp");
  if (M.drag && M.drag.moved) return;                            // dragging: the inspector follows when the finger lifts
  if (document.activeElement && box.contains(document.activeElement) && document.activeElement.tagName === "INPUT"
      && document.activeElement.type === "text") return;        // never rewrite a field while the user types in it
  const o = byId(M.sel);
  if (M.sel === "hamper" && M.hamper) return renderHamperInspector(box);
  if (!o) { box.hidden = true; box.replaceChildren(); return; }
  const wasOpen = !!(box.querySelector("details") && box.querySelector("details").open);
  box.hidden = false;
  const title = h("h3", {}, h("span", {}, o.name || (o.shape === "cylinder" ? "Circle" : isSquare(o) ? "Square" : "Rectangle")),
    h("button", {type: "button", class: "btn", onclick: () => { M.sel = null; mapRender(); }}, "Done"));
  const chips = h("div", {class: "chips", "aria-label": "What is it?"}, ...Object.keys(CHIPS).map(n => h("button", {type: "button", class: "chip",
    "aria-pressed": String(o.name === n), onclick: () => change(() => applyChip(o, n))}, n)));
  const sizes = h("div", {class: "grid2"});
  if (o.shape === "cylinder") sizes.append(lenField("Across", o, "diameter_m", v => { o.diameter_m = Math.max(MIN_SIZE, v); }, sizeCheck));
  else if (isSquare(o)) sizes.append(lenField("Side", o, "length_m", v => { o.length_m = o.width_m = Math.max(MIN_SIZE, v); }, sizeCheck));
  else sizes.append(lenField("Length", o, "length_m", v => { o.length_m = Math.max(MIN_SIZE, v); }, sizeCheck),
                    lenField("Width", o, "width_m", v => { o.width_m = Math.max(MIN_SIZE, v); }, sizeCheck));
  sizes.append(lenField(o.z_low_m > 0 ? "Top height" : "Height", o, "height_m", null, topCheck(o)));
  const acts = h("div", {class: "row"});
  if (o.shape === "box" && !isSquare(o)) acts.append(h("button", {type: "button", class: "btn",
    onclick: () => change(() => { o.yaw_deg = (o.yaw_deg + 90) % 360; snapPos(o); })}, "Turn 90°"));
  acts.append(h("button", {type: "button", class: "btn danger", onclick: () => change(() => {
    M.shapes = M.shapes.filter(s => s !== o); M.sel = null; }, `Removed ${o.name || "the shape"}.`)}, "Delete"));
  // advanced: name text, hanging, exact position, angle, copy
  const more = h("details", {}, h("summary", {}, "More: exact place, angle, hanging"));
  if (wasOpen) more.open = true;
  more.append(h("div", {class: "grid2"},
    field("Name", o.name, v => { change(() => { o.name = v.trim().slice(0, 40); }); return true; }),
    lenField("Position x (from wall A-D)", o, "x", v => { o.x = clamp(v, 0, roomW()); }),
    lenField("Position y (from wall A-B)", o, "y", v => { o.y = clamp(v, 0, roomD()); }),
    o.shape === "box" ? field("Turned (degrees)", String(+o.yaw_deg.toFixed(1)), v => {
      const a = parseFloat(v); if (!isFinite(a)) return false; change(() => { o.yaw_deg = ((a % 360) + 360) % 360; }); return true; }, {numeric: true}) : null));
  const hang = h("input", {type: "checkbox", onchange: () => change(() => {
    if (hang.checked) { o.height_m = roomH(); o.z_low_m = Math.max(0, roomH() - 0.45); } else o.z_low_m = 0; })});
  hang.checked = o.z_low_m > 0;
  more.append(h("label", {class: "chk"}, hang, "Hangs from the ceiling (a fan, a lamp)"));
  if (o.z_low_m > 0) more.append(h("div", {class: "grid2"}, lenField("Bottom height", o, "z_low_m", null, bottomCheck(o))));
  more.append(h("div", {class: "row"}, h("button", {type: "button", class: "btn", onclick: () => change(() => {
    const c = Object.assign({}, o, {id: nextId(), x: o.x + 0.3, y: o.y - 0.3}); snapPos(c); M.shapes.push(c); M.sel = c.id; }, "Copied.")}, "Make a copy")));
  box.replaceChildren(title, h("p", {class: "muted small"}, "Keep the robot away from this. Set what it is, its size and its height."),
    chips, sizes, acts, more);
}
function applyChip(o, n) {
  const t = CHIPS[n];
  o.name = n;
  if (t.shape && t.shape !== o.shape) {          // a lamp is round, a bed is not
    if (t.shape === "cylinder") { delete o.length_m; delete o.width_m; delete o.yaw_deg; o.diameter_m = t.diameter_m; }
    else { delete o.diameter_m; o.yaw_deg = 0; }
  }
  o.shape = t.shape || o.shape;
  for (const k of ["length_m", "width_m", "diameter_m", "height_m"]) if (t[k] != null) o[k] = t[k];
  if (t.hang != null) { o.height_m = roomH(); o.z_low_m = Math.max(0, roomH() - t.hang); } else if (t.shape) o.z_low_m = 0;
  snapPos(o);
}
function renderHamperInspector(box) {
  const hp = M.hamper;
  box.hidden = false;
  box.replaceChildren(
    h("h3", {}, h("span", {}, "Hamper"), h("button", {type: "button", class: "btn", onclick: () => { M.sel = null; mapRender(); }}, "Done")),
    h("p", {class: "muted small"}, "Drag the green circle to where the hamper stands. The robot drops laundry over its rim."),
    h("div", {class: "grid2"}, lenField("Rim height", hp, "height_m"),
      lenField("Position x", hp, "x", v => { hp.x = clamp(v, 0, roomW()); }), lenField("Position y", hp, "y", v => { hp.y = clamp(v, 0, roomD()); })));
}

// ---- server: load, preview, save
async function mapLoad(force) {
  const r = await api("/api/room_map");
  if (!r.ok) { mapMsg((r.data && r.data.error) || "Could not load the map.", "bad"); return; }
  M.info = r.data;
  if (!M.loaded || force) {
    M.shapes = r.data.obstacles.map(o => Object.assign({}, o));
    M.hamper = r.data.hamper ? {x: r.data.hamper.x, y: r.data.hamper.y, height_m: r.data.hamper.height_m, radius_m: r.data.hamper.radius_m} : null;
    M.units = r.data.units || "ft-in";
    M.savedKey = draftKey(); M.loaded = true; M.undo = []; M.sel = null;
  }
  $("mapUnits").textContent = M.units === "m" ? "metres" : "feet and inches";
  $("mapHamper").hidden = !M.hamper;
  mapRender();
  if (M.covOn) schedulePreview();
}
function mapShow() { mapLoad(false); }
function draftBody() {
  return {obstacles: M.shapes.map(o => { const c = Object.assign({}, o); delete c._rect; return c; }),
          hamper: M.hamper ? {x: M.hamper.x, y: M.hamper.y, height_m: M.hamper.height_m} : undefined, units: M.units};
}
function schedulePreview() {
  clearTimeout(M.covTimer);
  M.covTimer = setTimeout(async () => {
    const seq = ++M.covSeq;
    const r = await api("/api/room_map/preview", draftBody());
    if (seq !== M.covSeq || !M.covOn) return;     // an older answer, or the overlay was switched off meanwhile
    if (r.ok && r.data.ok) { M.cov = r.data.coverage; mapRender(); }
    else mapMsg("Cannot show where it can pick: " + ((r.data && (r.data.errors || []).join("; ")) || r.data.error || "no answer"), "bad");
  }, PREVIEW_MS);
}
function mapGate() {           // Save only where the service would accept it (it re-checks)
  if (!M.info || !$("mapSave")) return;
  const st = S ? S.state : M.info.state, busy = S ? S.busy : null;
  const ok = !busy && ["DISARMED", "PARKED", "READY", "PAUSED"].includes(st);
  $("mapSave").disabled = !ok || !dirty();
  $("mapNote").textContent = ok ? (["READY", "PAUSED"].includes(st) ? "The robot is in the air: saving is refused if the claw is where a new shape would be." : "")
    : (busy ? `The robot is busy (${busy}). You can keep drawing; save when it is done.` : `The map can be saved when the robot is stopped (it is ${st}). You can keep drawing.`);
}
$("mapSave").addEventListener("click", async () => {
  const bad = draftProblems();
  if (bad.length) { mapMsg("Not saved: " + bad.join(" "), "bad"); return; }
  const r = await api("/api/room_map", draftBody(), "PUT");
  if (r.ok) {
    M.info = Object.assign(M.info, r.data);
    M.shapes = r.data.obstacles.map(o => Object.assign({}, o));
    M.savedKey = draftKey();
    mapRender(); mapMsg(r.data.text + ".", "good"); toast(r.data.text + ".");
  } else {
    const why = plainNames((r.data && (r.data.errors ? r.data.errors.join("; ") : r.data.error)) || "HTTP " + r.status);
    mapMsg("Not saved: " + why, "bad"); toast("Map not saved: " + why, true);
  }
});
$("mapRevert").addEventListener("click", async () => { await mapLoad(true); mapMsg("Back to the saved map."); });
$("mapUndo").addEventListener("click", () => {
  const k = M.undo.pop();
  if (!k) return;
  const d = JSON.parse(k);
  M.shapes = d.s; M.hamper = d.h; M.units = d.u || M.units;
  if (M.sel !== "hamper" && !byId(M.sel)) M.sel = null;
  edited("Undone.");
});
$("mapUnits").addEventListener("click", () => {
  snapshot(); M.units = M.units === "m" ? "ft-in" : "m";
  $("mapUnits").textContent = M.units === "m" ? "metres" : "feet and inches";
  mapRender();
});
$("mapCov").addEventListener("change", () => {
  M.covOn = $("mapCov").checked; $("covLegend").hidden = !M.covOn;
  if (M.covOn) { schedulePreview(); mapMsg("Tap a spot on the map to see why the robot cannot pick there."); }
  else { M.cov = null; mapRender(); mapMsg(""); }
});
$("mapHamper").addEventListener("click", () => { if (M.hamper) { M.sel = "hamper"; mapRender(); } });
window.addEventListener("resize", () => { if (tab === "map") mapRender(); });

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
