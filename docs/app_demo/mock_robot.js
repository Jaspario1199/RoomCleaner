/* Demo backend for the RoomCleaner phone app: a small simulated robot that answers the app's /api calls inside
 * the browser, so the real app.js can run on a hosted page with no robot service behind it.
 * The texts, chips, allowed commands and confirmation questions are copied from roomcleaner/cdpr/chat.py and
 * supervisor.py; the status shape was captured from the --sim service. Nothing here reaches hardware. */
(() => {
"use strict";
const CAP = window.__RC_CAPTURE;            // {status0, checks}
const FRAME_SRC = window.__RC_FRAME;        // data: URI of a captured simulator frame

const ESTOP = "Emergency stop = the switched power strip. It drops the claw: nobody under the robot.";
const STATE_TEXT = {
  DISARMED: "Disarmed. The stations are not holding the claw; it should be resting on the floor. Tick the safety checklist on Setup, then Start.",
  STARTUP: "Starting up: taking up slack, lifting and calibrating. Keep clear of the robot.",
  READY: "Ready. Calibrated, holding position.",
  TASK: "Working: running a pickup task.",
  PAUSED: "Paused. Holding position with torque on. Resume, or lower the claw to the floor.",
  FAULT: "Fault. Motion is stopped and the references are still trusted. Acknowledge to clear it.",
  RECOVERY_REQUIRED: "Recovery needed. The claw may be hanging and a reference is no longer trusted. Check the scene, then Recover or Lower.",
  PARKED: "Parked on the floor, cables slack, stations still holding. Start, or Disarm on Setup.",
};
const STATE_HINT = {
  FAULT: "Say 'acknowledge' (or tap Acknowledge on Setup).",
  RECOVERY_REQUIRED: "Check nobody is under the robot, then say 'recover' or 'lower'.",
  PAUSED: "Say 'resume' or 'lower' when you are ready.", PARKED: "The claw is on the floor.",
  READY: "Calibrated and holding position.", DISARMED: "Say 'start' after ticking the checklist on Setup.",
};
const CHIPS = {
  DISARMED: ["Status", "Why?", "Battery", "Start", "Pause", "Help"], STARTUP: ["Status", "Why?", "Battery", "Pause", "Help"],
  READY: ["Status", "Why?", "Battery", "Lower", "Pause", "Help"], TASK: ["Status", "Why?", "Battery", "Pause", "Help"],
  PAUSED: ["Status", "Why?", "Battery", "Resume", "Lower", "Pause", "Help"],
  FAULT: ["Status", "Why?", "Battery", "Acknowledge", "Recover", "Lower", "Pause", "Help"],
  RECOVERY_REQUIRED: ["Status", "Why?", "Battery", "Recover", "Lower", "Pause", "Help"],
  PARKED: ["Status", "Why?", "Battery", "Start", "Open grip", "Close grip", "Pause", "Help"],
};
const ALL = Object.keys(STATE_TEXT);
const ALLOWED = {
  start: ["DISARMED", "PARKED"], pause: ALL, resume: ["PAUSED"], acknowledge: ["FAULT"],
  recover: ["RECOVERY_REQUIRED", "FAULT"], lower: ["READY", "PAUSED", "RECOVERY_REQUIRED", "FAULT"],
  disarm: ["PARKED", "DISARMED", "FAULT", "RECOVERY_REQUIRED", "PAUSED"], task: ["READY"],
};
const QUESTIONS = {
  start: "Run the startup sequence now? The claw takes up slack, lifts off the floor and moves around the room while it calibrates. You have ticked the checklist: nobody under the robot, power strip in reach.",
  resume: "Resume from PAUSED? The robot re-checks the stations and the camera first, then restarts from the safest step. The claw may move.",
  recover: "Run recovery now? The stations are re-armed, one cable may be re-referenced from the camera, and the claw may move slightly while it re-checks.",
  lower: "Lower the claw to the floor now? It moves over the marker and descends. Nobody under the robot.",
  grip_open: "Open the grip now? Whatever the claw is holding will be released.",
  grip_close: "Close the grip now? The fingers curl in.",
};
const STARTED = {
  start: "Starting. Watch Home or Setup for progress. Say 'pause' to hold position at any time.",
  resume: "Resuming. The robot re-checks first; it may refuse and tell you why. Say 'pause' to hold.",
  recover: "Recovering. Say 'pause' to hold position.", lower: "Lowering the claw to the floor. Say 'pause' to hold position.",
  grip_open: "Opening the grip.", grip_close: "Closing the grip.",
};
const HELP = "I understand: status, why (trust and reasons), battery, pause, resume, start, acknowledge, recover, lower, open grip, close grip, help. Anything that moves the robot asks 'yes' first (within 30 s). Pause runs at once. Disarm is only on the Setup screen. " + ESTOP;
// startup steps (seconds of demo time each) and the claw height the camera view follows
const STEPS = [["SELF_CHECK", 4, 0], ["SLACK_TAKEUP", 7, 0], ["INITIAL_LIFT", 5, 0.25], ["VISUAL_INITIALIZATION", 5, 0.3],
               ["CALIBRATION", 9, 0.45], ["REFERENCE_VERIFICATION", 5, 0.35]];
const TTL = 30;

const R = {
  state: "DISARMED", detail: "", busy: null, level: "NONE", stations: "OFF", grip: false, supported: false,
  height: 0, battery: 7.82, frame: 80, step: 0, timer: null, calibrated: false, sup: [], room: CAP.status0.room_m.slice(),
  anchors: JSON.parse(JSON.stringify(CAP.status0.anchors_m)), reasons: [], pending: null,
};
const now = () => Date.now() / 1000, T0 = now();
const events = []; let evId = 0;
const ev = (kind, text) => events.push({id: ++evId, kind, text, t: now(), host_t: +(now() - T0).toFixed(2)});
function setState(s, why) {
  R.state = s; R.sup.push([+(now() - T0).toFixed(1), s, why || ""]);
  const hint = ["FAULT", "RECOVERY_REQUIRED", "PAUSED"].includes(s) ? " " + STATE_HINT[s] : "";
  ev("state", (why ? `${s}: ${why}.` : `${s}.`) + hint);
}
ev("state", "DISARMED: host start (no automatic resume).");
ev("info", "Demo: a simulated robot runs inside this page. Nothing here reaches real hardware.");

const allowed = s => Object.entries(ALLOWED).filter(([c, st]) => st.includes(s) && c !== "pause" && c !== "task").map(([c]) => c);
const lc = s => s.replace(/_/g, " ").toLowerCase();

function trust() {
  if (R.level === "NONE") return {basis: null, full_workspace: false, level: "NONE", margin: {}, reasons: []};
  return {basis: null, full_workspace: false, level: "LOCAL_ONLY",
    reasons: ["slack probe was off: the predicted sigma is not honest (demo)",
              "predicted length sigma 5.3 mm > 5.0 mm gate: full workspace not unlocked"],
    margin: {k: 3.0, ok: false, ceiling_margin_m: 0.4, workspace_margin_m: 0.2, sigma_ceiling_m: 0.0053,
             sigma_wall_m: 0.0061, k_sigma_ceiling_m: 0.0159, k_sigma_wall_m: 0.0183, slack_probe: false, calibration_accepted: true}};
}
function station(id) {
  const st = R.stations, run = st === "RUN";
  return {bead_verified: false, boot: 1000 + id.charCodeAt(0), encoder_valid: st !== "OFF", fault: "NONE", note: "",
          online: true, state: st, tel_age_s: 0.01, valid: st !== "OFF" || R.calibrated, ...(run ? {} : {})};
}
function status() {
  R.battery = Math.max(7.0, R.battery - 0.0004);
  const px = Math.round(155 / (1 + 1.6 * R.height));
  return {
    allowed: allowed(R.state), anchors_m: R.anchors, app_error: null, busy: R.busy,
    camera: {age_s: +(0.1 + Math.random() * 0.15).toFixed(1), available: true, frame_id: R.frame, mode: "sim-800x600", source: "sim",
             detection: {n_tags: R.height > 0.3 ? 2 : 1, ok: true, text: `marker in view (${px} px; modelled, not drawn)`}},
    checklist: CAP.status0.checklist, chips: CHIPS[R.state],
    claw: {age_s: +(0.4 + Math.random()).toFixed(1), battery_low: R.battery < 7.0, battery_min_v: 7.0, battery_v: +R.battery.toFixed(2),
           camera_mode: null, camera_ok: true, grip_closed: R.grip, online: true, stale: false},
    claw_supported: R.supported, detail: R.detail, error: null, events: R.sup.slice(-20), level: R.level, profile: "demo (simulated in the page)",
    reasons: R.reasons.slice(-5), recovery_required: R.state === "RECOVERY_REQUIRED", room_m: R.room, state: R.state,
    state_hint: STATE_HINT[R.state] || "", state_text: STATE_TEXT[R.state],
    stations: Object.fromEntries(["A", "B", "C", "D"].map(id => [id, station(id)])), trust: trust(),
  };
}

// ---------------------------------------------------------------- motion (timers stand in for the sequencer)
function clearRun() { clearTimeout(R.timer); R.timer = null; }
function runStartup(from) {
  clearRun(); R.busy = "start"; R.stations = "RUN"; R.supported = false;
  if (R.state !== "STARTUP") setState("STARTUP", from ? "resume" : "operator start");
  const go = i => {
    if (i >= STEPS.length) {
      R.busy = null; R.detail = ""; R.stations = "IDLE"; R.level = "LOCAL_ONLY"; R.calibrated = true; R.height = 0.4;
      setState("READY", "startup finished (LOCAL_ONLY)");
      ev("command", "'start' finished; state READY"); return;
    }
    R.step = i; const [name, secs, h] = STEPS[i];
    R.detail = name; R.height = h; ev("step", "Startup step: " + lc(name));
    R.timer = setTimeout(() => go(i + 1), secs * 1000);
  };
  ev("command", "Command 'start' started"); go(from || 0);
}
function runLower() {
  clearRun(); R.busy = "lower"; R.stations = "RUN"; R.detail = "LOWERING";
  if (R.state === "PAUSED") R.state = R.resumeTo || "READY";
  ev("command", "Command 'lower' started");
  R.timer = setTimeout(() => {
    R.busy = null; R.detail = ""; R.stations = "IDLE"; R.height = 0; R.supported = true;
    setState("PARKED", "claw lowered onto the floor"); ev("command", "'lower' finished; state PARKED");
  }, 6000);
}
function pause() {
  const was = R.state;
  ev("pause", `Pause pressed in ${was}: holding position.`);
  if (["STARTUP", "READY", "TASK"].includes(was)) {
    clearRun(); R.resumeTo = was; R.resumeStep = R.step; R.busy = null; R.stations = "IDLE";
    setState("PAUSED", "operator pause");
  }
  return was;
}
function exec(cmd, body) {
  const s = R.state;
  const refuse = msg => ({ok: false, error: msg});
  if (cmd !== "pause" && R.busy) return refuse(`busy with '${R.busy}'`);
  if (cmd in ALLOWED && !ALLOWED[cmd].includes(s)) return refuse(`'${cmd}' is only available in ${ALLOWED[cmd].join(", ")}; the robot is ${s}`);
  switch (cmd) {
    case "pause": pause(); break;
    case "start": if (!body.checklist) return refuse("tick the pre-start safety checklist first"); runStartup(0); break;
    case "resume": if (R.resumeTo === "STARTUP") runStartup(R.resumeStep || 0); else { R.stations = "IDLE"; setState(R.resumeTo || "READY", "resume"); } break;
    case "lower": runLower(); break;
    case "disarm":
      if (body.confirm !== "claw_supported") return refuse("type 'claw_supported' to confirm the claw rests on a support");
      clearRun(); R.stations = "OFF"; R.busy = null; R.detail = ""; R.supported = true; setState("DISARMED", "operator disarm"); break;
    case "acknowledge": case "recover": R.stations = "IDLE"; setState("READY", cmd); break;
    case "grip_open": case "grip_close":
      R.grip = cmd === "grip_close"; ev("info", R.grip ? "Grip closed." : "Grip opened."); break;
    case "task": return refuse("tasks are not part of the demo");
    default: return refuse(`unknown command '${cmd}'`);
  }
  return {ok: true, state: R.state};
}

// ---------------------------------------------------------------- chat (same intents and wording as chat.py)
const RX = {
  yes: /^(yes|y|yeah|yep|confirm|do it|ok|okay|go ahead)\b/, no: /^(no|n|nope|cancel|stop asking)\b/,
  help: /\b(help|what can you do|commands)\b/, battery: /\b(battery|volt|charge)\b/, why: /\b(why|trust|reason)/,
  status: /\b(status|state|how are you|what.?s up|report)\b/, pause: /\b(pause|hold|freeze|wait)\b/,
  resume: /\b(resume|continue|carry on)\b/, start: /\b(start|restart|begin|calibrate|calibration|startup|get started|get going)\b/,
  acknowledge: /\b(acknowledge|ack|clear fault)\b/, recover: /\b(recover|recovery)\b/, lower: /\b(lower|land|put (it )?down|park)\b/,
  grip_open: /\b(open|release|let go|drop)\b/, grip_close: /\b(close|grab|grip|pick|clamp)\b/, disarm: /\b(disarm|power off|turn off)\b/,
};
function reply(text, extra) { return Object.assign({ok: true, reply: text, chips: CHIPS[R.state], command_run: null, goto: null, pending_confirm: null}, extra || {}); }
function gripAllowed() { return (R.state === "PARKED" || (R.state === "DISARMED" && R.supported)) && !R.busy; }
function stLine() {
  const st = status(), c = st.claw;
  return `State ${R.state}${R.detail ? " (" + R.detail + ")" : ""}: ${STATE_TEXT[R.state]} Stations: A ok, B ok, C ok, D ok. `
       + `Claw: ${c.battery_v.toFixed(2)} V, grip ${c.grip_closed ? "closed" : "open"}, camera ok.`;
}
function say(body) {
  const raw = (body.text || "").trim(), t = raw.toLowerCase();
  const p = R.pending && R.pending.until > now() ? R.pending : null;
  if (RX.yes.test(t)) {
    if (!p) return reply("Nothing is waiting for confirmation.");
    R.pending = null;
    const res = exec(p.cmd, Object.assign({}, p.body, {checklist: p.body.checklist && body.checklist}));
    if (!res.ok) return reply("I couldn't do that: " + res.error);
    return reply(STARTED[p.cmd], {command_run: p.cmd, chips: CHIPS[R.state]});
  }
  if (RX.no.test(t)) { const had = !!p; R.pending = null; return reply(had ? "Okay, cancelled. Nothing was done." : "Okay. Nothing was waiting for confirmation."); }
  if (RX.help.test(t)) return reply(HELP);
  if (RX.pause.test(t)) { const was = pause(); return reply(`Paused: holding position with torque on (state ${R.state === "PAUSED" ? "PAUSED" : was}). This is not an emergency stop. ${ESTOP}`, {command_run: "pause"}); }
  if (RX.battery.test(t)) return reply(`Claw battery ${R.battery.toFixed(2)} V. OK for lifting.`);
  if (RX.disarm.test(t)) return reply("Disarm is only on the Setup screen, with its typed confirmation.", {goto: "setup"});
  const ask = cmd => {
    R.pending = {cmd, until: now() + TTL, body};
    return reply(QUESTIONS[cmd], {pending_confirm: {action: cmd, question: QUESTIONS[cmd], expires_in_s: TTL}, chips: ["Yes", "No", "Pause"]});
  };
  const cant = cmd => reply(`I can't do that now: '${cmd}' is only available in ${ALLOWED[cmd].join(", ")}; the robot is ${R.state}`);
  for (const cmd of ["resume", "acknowledge", "recover", "lower", "start"]) {
    if (!RX[cmd].test(t)) continue;
    if (!ALLOWED[cmd].includes(R.state)) return cant(cmd);
    if (R.busy) return reply(`I can't do that now: busy with '${R.busy}'. Say 'pause' to hold.`);
    if (cmd === "start" && !body.checklist)
      return reply("Starting needs the pre-start safety checklist, and I can't tick it for you. Open the Setup tab, confirm every item yourself (room cleared, power strip in reach, claw upright over the marker, cables on their pulleys, battery charged), then say 'start' again.", {goto: "setup"});
    if (cmd === "acknowledge") { exec(cmd, body); return reply("Acknowledging the fault: the stations are re-checked. Watch Home for the result.", {command_run: cmd}); }
    return ask(cmd);
  }
  for (const cmd of ["grip_open", "grip_close"]) {
    if (!RX[cmd].test(t)) continue;
    if (!gripAllowed()) return reply(`I can't do that now: the grip can only be moved from the phone when the claw is verified on the floor (PARKED); the robot is ${R.state}. Opening it while hanging could drop what it holds.`);
    return ask(cmd);
  }
  if (RX.why.test(t)) {
    const tr = trust();
    return reply(`State ${R.state}: ${STATE_TEXT[R.state]} Trust ${tr.level}` + (tr.reasons.length ? ": " + tr.reasons.join("; ") + "." : "."));
  }
  if (RX.status.test(t)) return reply(stLine());
  return reply(`I didn't understand “${raw}”. ${HELP}`);
}

// ---------------------------------------------------------------- camera: the captured sim frame, scaled with claw height
const img = new Image(); img.src = FRAME_SRC;
const cv = document.createElement("canvas"); cv.width = 800; cv.height = 600;
function frameBlob() {
  const g = cv.getContext("2d"); R.frame++;
  g.fillStyle = "#969696"; g.fillRect(0, 0, 800, 600);
  const k = 1 / (1 + 1.6 * R.height), moving = R.stations === "RUN", tt = now();
  const jx = moving ? 6 * Math.sin(tt * 1.7) : 0, jy = moving ? 5 * Math.cos(tt * 1.3) : 0;
  if (img.complete && img.naturalWidth) {
    const w = 800 * k, hgt = 600 * k;
    g.save(); g.beginPath(); g.rect(0, 0, 800, 600); g.clip();
    g.drawImage(img, 400 - w / 2 + jx, 300 - hgt / 2 + jy, w, hgt); g.restore();
  }
  for (let i = 0; i < 900; i++) {           // sensor grain, so the feed visibly updates
    const v = 120 + Math.random() * 60 | 0; g.fillStyle = `rgba(${v},${v},${v},0.25)`;
    g.fillRect(Math.random() * 800, Math.random() * 600, 2, 2);
  }
  return new Promise(res => cv.toBlob(b => res(b), "image/jpeg", 0.8));
}

// ---------------------------------------------------------------- fetch shim
const json = (data, status = 200) => new Response(JSON.stringify(data), {status, headers: {"Content-Type": "application/json"}});
const realFetch = window.fetch.bind(window);
window.fetch = async (input, init) => {
  const url = typeof input === "string" ? input : input.url;
  if (!url.startsWith("/api/")) return realFetch(input, init);
  await new Promise(r => setTimeout(r, 40 + Math.random() * 60));     // a little network latency
  const u = new URL(url, "https://demo.invalid"), path = u.pathname, method = (init && init.method) || "GET";
  const body = init && init.body ? JSON.parse(init.body) : {};
  if (path === "/api/status") return json(status());
  if (path === "/api/events") {
    const since = +(u.searchParams.get("since") || 0);
    return json({events: events.filter(e => e.id > since), last_id: evId});
  }
  if (path === "/api/checks") return json(CAP.checks);
  if (path === "/api/calibration") {
    if (!R.calibrated) return json({ok: false, error: "no calibration yet"}, 404);
    return json({result: {norm_rms: 1.08, anchors_room_m: ["A", "B", "C", "D"].map(id => R.anchors[id].map(x => x + (Math.random() - 0.5) * 0.01))},
                 validation: {accepted: true, witness_rms_m: 0.0061, reasons: ["Demo numbers, not a real calibration."]}});
  }
  if (path === "/api/frame.jpg") {
    const b = await frameBlob();
    return new Response(b, {status: 200, headers: {"Content-Type": "image/jpeg", "X-Frame-Age-S": "0.1"}});
  }
  if (path === "/api/room" && method === "POST") {
    const w = +body.width_m, d = +body.depth_m, h = +body.height_m;
    if (!(w > 0.5 && d > 0.5 && h > 0.5)) return json({ok: false, error: "room size must be positive metres"}, 400);
    R.room = [w, d, h];
    R.anchors = body.anchors || {A: [0.05, 0.05, h - 0.15], B: [w - 0.05, 0.05, h - 0.15], C: [w - 0.05, d - 0.05, h - 0.15], D: [0.05, d - 0.05, h - 0.15]};
    ev("info", `Room set to ${w} x ${d} x ${h} m.`);
    return json({ok: true, room_m: R.room, anchors: R.anchors});
  }
  if (path === "/api/command" && method === "POST") {
    const res = exec(body.cmd, body);
    return res.ok ? json(res) : json(res, 409);
  }
  if (path === "/api/say" && method === "POST") return json(say(body));
  return json({ok: false, error: "not in the demo: " + path}, 404);
};

// the app reads its session token from the URL or sessionStorage; the demo has none, so give it one
try { sessionStorage.setItem("rc_token", "demo"); } catch (e) { /* blocked storage: the URL below still works */ }
try { history.replaceState(null, "", location.pathname + "?token=demo" + location.hash); } catch (e) { /* fine */ }
})();
