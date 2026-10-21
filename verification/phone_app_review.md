# Phone app: independent review

Date: 2026-10-21. Reviewer: independent Sonnet reviewer (did not write the code). Contract: `docs/PHONE_APP_SPEC.md`.
Scope: commit 953822d (`roomcleaner/cdpr/service.py`, `chat.py`, `claw_link.py` JPEG cache, `static/*`,
`tests/cdpr/test_phone_app.py`). Interpreter `/usr/bin/python3` 3.13, Flask 3.1.3, Werkzeug 3.1.9, `OMP_NUM_THREADS=1`,
Chromium 1194 via Playwright 1.56.1 (headless). Production code untouched; the only files written are this report and
`tests/cdpr/test_phone_app_review.py` (25 tests, all PASS while the defects below are present). Nothing committed.

How the code under test was fixed: the scope files are identical at 953822d and HEAD 8fa242a. All live runs used a clean
`git archive HEAD` copy (scratchpad `head_tree/`), because the working tree is being edited concurrently (uncommitted
`coordinator.py`, `trajectory.py` and, by the end of the review, three-station work in `service.py`, `startup.py`, `static/app.js`...).
The 109-test run used the working tree as it was at 19:01 (only `coordinator.py` / `trajectory.py` modified).

## Verdict: PASS WITH CONDITIONS

No safety rule of the spec is broken: no chat text moves the robot without a fresh "yes" inside 30 s (the only direct actions
are `pause` and `acknowledge`, which does not move cables), pause is immediate and keeps torque, the token guard has no hole,
nothing is rendered with `innerHTML`, and the camera routes never touch the claw or the host loop. Conditions before the app
is used with the real robot (details in the table): **F1** (one token means every phone can confirm every other phone's
question), **F2** (the pause message claims "torque on" whatever the stations report), **F3** (hardware-only host-loop busy
spin during every command; pre-existing, invisible in `--sim`), and quick fixes **F4/F5** (stream slots), **F6** (token in the
console log). The implementer's reported deviations are judged individually below.

## Judgement of the reported deviations

| Deviation | Judgement |
|---|---|
| Default host 0.0.0.0, token-guarded | Acceptable, and not new: the pre-phone-app service already defaulted to 0.0.0.0 (`git show 953822d^`), and the spec asks for 0.0.0.0 on the home LAN. Plain HTTP means the token is readable by anyone on the same Wi-Fi (F18). |
| Grip from chat only in PARKED or DISARMED+claw_supported, after "yes", via `ctx.claw.grip()` on the command worker, not on `/api/command` | Acceptable with one condition (F12). It is gated three times (`can()` when asked, `can()` again at "yes", `_grip_block()` again in `grip()`), needs the claw online and the command lock, and is not reachable from `/api/command` (test exists). It is not a cable motion, and the spec's own chat list names "open/close grip (only where the supervisor allows it)" while its safety rules say "only existing supervisor commands": the implementer resolved the conflict conservatively. Condition: in DISARMED it trusts the stored `ledger.claw_supported` flag, which the supervisor itself refuses to trust for `disarm` ("no stored flag can substitute", `supervisor.py` docstring). Use PARKED only, or run a fresh vision floor check on the worker before the grip. |
| `start` from chat uses a client-sent checklist flag, re-checked at "yes" | Acceptable: same trust level as `POST /api/command` (the server cannot see the ticks either), re-checked at "yes" (tested). Weakness: the ticks never expire (F9). |
| `acknowledge` without a question | Acceptable with a note (F11): FAULT only, no cable motion (`Supervisor.acknowledge` clears faults, re-configures and re-arms stations, then a visual check), same as the Setup button. Ask for a confirmation when `claw_supported` is False (claw possibly hanging). |
| Claw telemetry polled every 2 s by a background thread | Acceptable: no request handler reaches the claw (checked: the only `ctx.claw` calls are `poll_claw` on its own thread and `grip` on the worker). It is a second `/status` client on the claw node (about 0.5 req/s) and refreshes `HttpClawClient.offset_us` every 2 s (F21, info). |
| Max 4 streams | Acceptable, but the slot accounting leaks (F4, F5). |
| Non-modal confirm sheet | Acceptable and verified: with the sheet open at 360x740 PAUSE is visible and is the top element at its centre point. |

## Findings

Severity: Medium = fix before real-robot use; Low = fix soon; Info = note. "Tests" names the pinning test in
`tests/cdpr/test_phone_app_review.py`.

| Id | Sev | Finding | Evidence (expected vs observed) | Suggested fix |
|---|---|---|---|---|
| F1 | Medium | The pending question is "keyed by the session token" (`chat.py` docstring, `docs/APP.md`), but there is ONE token for every phone and tab, so the key is shared. Phone B's "yes" runs phone A's pending motion within 30 s. Another token cannot exist (401). | Expected: B's "yes" does nothing. Observed (`probe_sec.py` section 4, test `test_f1_...`): A says "lower the claw" (pending lower); B says "yes": `command_run = "lower"`, event log shows "Operator confirmed 'lower' in chat". | Bind the question to a per-client id (random id in `sessionStorage`, sent as `X-Client`) or to a nonce returned in `pending_confirm` that the Yes button echoes; typed "yes" valid only from the same client id. Correct the docs. |
| F2 | Medium | The pause reply (and the PAUSE toast) always says "holding position with torque on", also in DISARMED (nothing is holding) and in RECOVERY_REQUIRED / FAULT with no station telemetry, where the claw may hang. False assurance in the state where it matters most. | Expected: text follows `stations[*].state`. Observed (test `test_f2_...`): DISARMED, RECOVERY_REQUIRED, FAULT with all four stations `state: None` all reply "Paused: holding position with torque on (state X)". `app.js` `doPause` toast is a fixed string too. | Build the sentence from the station states: all IDLE/HOLD/RUN: "holding"; DISARMED: "nothing to hold: stations not armed"; any OFF/None/FAULT: "NOT holding: station B is OFF". Same in the toast (use the status returned by the next tick). |
| F3 | Medium (hardware only; pre-existing since the C1 review) | `main()` passes `real_sleep_s=0.0` for hardware. While a command owns the robot `idle_tick()` returns False at once, so the host-loop thread busy-spins and, through the 5 ms GIL hand-off, makes every 1 ms sleep of the command thread (the real runtime pumps in 1 ms sleeps) take 6.3 ms. `--sim` passes 0.01 and hides it. | Measured with the real `Service` (lock held, 2.66 million `idle_tick` calls/s; a 1 ms sleep takes 6.31 ms vs 1.12 ms without the spinner and 1.12 ms with `real_sleep_s=0.01`). Test `test_f3_...`. It is a model of the hardware path on this machine, not a hardware measurement. | In the loop: `if not self.idle_tick(): time.sleep(0.005)` (or `lock.acquire(timeout=...)`); add a hardware-setting test. |
| F4 | Low | `HEAD /api/stream.mjpg` with the header token takes a slot in the view and never starts the generator, so the `finally` that releases it never runs. Four HEADs lock the camera stream out until restart. | Expected: slots back to 0. Observed (`probe_stream.py` A, test `test_f4_...`): after 4 HEADs `_streams == 4`, a real GET gets 429 and stays 429. | Take the slot inside the generator, or `resp.call_on_close(release)`, or answer HEAD without a slot. |
| F5 | Low | While the claw has no cached frame the stream generator yields nothing: no headers are sent, a client that gave up (the app does after 4 s) is never noticed, and its slot is held. Four Camera-tab visits during an outage fill all slots; they free themselves only when a frame arrives. | Observed (`probe_stream.py` B, test `test_f5_...`): 4 aborted attempts, 0 bytes received each; 3 s later `_streams == 4`, 5th attempt 429; after a frame appears, 0. | Return 503 immediately when `latest_frame()` is None (the JS already falls back to stills), or send a keep-alive part. |
| F6 | Low | The token reaches the console / log file: Werkzeug logs the full request line, so `GET /?token=...` (page load) and every `GET /api/stream.mjpg?token=...` carry it. Spec check 2 says "never in logs beyond the startup URL line". The page also leaves `?token=` in the address bar and history. | Observed (test `test_f6_...`, live log): `"GET /?token=<TOKEN> HTTP/1.1" 200 -` and `"GET /api/stream.mjpg?token=<TOKEN>&_=1 HTTP/1.1" 200 -`. | Redact `token=` in a `WSGIRequestHandler.log_request` override; best: short-lived stream ticket from an authenticated POST so the long-lived token never travels in a URL, and `history.replaceState` to drop `?token=` after reading it. |
| F7 | Low | The mic handler sends every transcript straight to `/api/say`; a bare "yes", "yeah", "go ahead" or "do it" is a valid confirmation. Ambient speech (TV, another person) can confirm a pending motion question. | `app.js`: `rec.onresult = ev => { ...; if (t) send(t); }`; `parse("go ahead") == "confirm"` (test `test_f7_...`, source pin). | Voice never confirms: confirmation only by the Yes button (or typed text). |
| F8 | Low | Chat pause is missed for: a leading question word ("why is it moving stop it" -> why; "what is it doing, stop" -> status; "what the hell stop", "is it going down? stop!", "do stop" -> unknown), typos ("stopp", "stooop") and "hold", "wait". Unknown text gets "I didn't understand". The PAUSE button is the primary control, but pause is always safe so the parser should lean to it. | `probe_sec.py` section 5; test `test_f8_...` (8 cases). | If a message contains a stop-like stem (stop, paus, halt, freez, abort, hold, wait) and is not a recognised "why did you stop" question, pause. |
| F9 | Low | The client-side checklist ticks have no expiry: they stay valid for as long as the state is DISARMED or PARKED (hours), and chat `start` re-uses them. The page text says "Ticks are not remembered", which is only true across reloads. "Nobody under the robot" is asserted once, not at start time. | `app.js` `checklistTicked()` has no time component (test `test_f9_...`, source pin); ticks do clear on reload (verified, Playwright `ticksAfterReload: 0`) and in states other than DISARMED/PARKED. | Expire ticks after about 2 min (or on leaving the Setup tab) and make chat/Setup start require fresh ticks. |
| F10 | Low | JSON hygiene: non-object bodies and odd types give 500 HTML: `/api/command` with `[1]`, `"str"`, `{"cmd":[1]}` (unhashable), `/api/say` with `[1]`, `/api/room` with `anchors: [1]`. `/api/room` accepts NaN (`"nan"` passes both range tests) for room size and anchors and echoes `NaN` (invalid JSON). At 953822d an unknown station id (`{"Z": ...}`) raised a 500 KeyError after the room size was already changed (the uncommitted three-station work already answers 400). The UI cannot produce these; needs a direct API client with the token. | `probe_sec.py` section 3; tests `test_f10_...` (6 cases). | `body = request.get_json(silent=True); if not isinstance(body, dict): 400`; `isinstance(cmd, str)`; `np.isfinite`; validate all anchors before assigning anything. |
| F11 | Low (judged acceptable) | `acknowledge` runs on the first message with no question. See the deviation table. A typed "ack"/"clear faults" or a voice transcript is enough. | `fuzz_chat.py`: 18,000 random messages in 300 sessions, 0 motion commands without a preceding matching question + bare confirmation inside 30 s; only `pause` and `acknowledge` ever run directly. Test `test_f11_...`. | Confirmation when `claw_supported` is False. |
| F12 | Low (judged acceptable) | The chat grip gate in DISARMED trusts the stored `claw_supported` flag. | `service.py` `_grip_block`; `supervisor.py` docstring ("no stored flag can substitute"). | PARKED only, or a fresh `_floor_confirmed()` on the worker before the grip. Also record grip commands in the supervisor event log (today only the app log has them). |
| F13 | Low | No feedback when the network hangs instead of failing: `fetch` has no timeout. A PAUSE whose request never returns shows no toast, banner or pending state; a hung `/api/status` leaves the header "online" (green) and the old state on screen with no staleness cue. Failure is shown only for refused connections (verified: offline shows the banner after about 2 s and PAUSE shows "DID NOT REACH"). | Playwright `ui2.js`/`ui3.js`: `/api/command` never answered, after 8 s: toast null, banner null, "online"; `/api/status` hung for 20 s: "online", `conn ok`, state "DISARMED" unchanged; slow (3 s) PAUSE: no toast at 0.5 s, success toast only at the end. | AbortController timeout (3 s) on every call, "sending..." state on PAUSE with automatic retry (pause is idempotent), "last update N s ago" and dimmed state after 3 missed polls. |
| F14 | Low | The "Connect to the robot" overlay (no token or wrong token, e.g. after the service restarted: the token changes every start) covers the whole screen including PAUSE and the emergency-stop line (z-index 50). The spec wants both on every screen. | Playwright: with no token and with `?token=WRONG`: overlay shown, `pauseOnTop: false` (screenshot `connect_360.png`). PAUSE cannot work without a token, but the e-stop line is the thing to keep. | Repeat the e-stop line in the overlay, or keep the dock above it. |
| F15 | Info | Dark mode: white text on the PAUSE button (`#d9453a`) is 4.32:1 (AA wants 4.5:1; the 18 px bold label is just under "large text"). Everything else measured (31 elements per scheme/width) is at least 4.5:1 (light minimum 5.47). | `ui.js` contrast table. | Use the light-mode `#c2352b` for the dark button too. |
| F16 | Info | `--sim` defaults to the repo-relative, gitignored `data/cdpr` and persists supervisor/ledger/model state across runs and across simulated worlds. The record of the earlier failed run is still there (`state.json`: RECOVERY_REQUIRED, "pretension: claw dragged while tensioning (0.014842997755689768)"), so the literal stock command `python -m roomcleaner.cdpr.service --sim --port <free>` now starts in RECOVERY_REQUIRED and refuses `start` (409 "'start' not allowed in RECOVERY_REQUIRED"; verified on a copy). Starting from a persisted model also changes the pretension (drag peak 2.72 mm instead of 0.95 mm in the same world, twice). | See check 4. | `--sim` should default to a fresh temp data dir (or require `--data`), and print the data dir and the starting state in the banner. |
| F17 | Info (pre-existing, not the service) | The simulated startup is not a pure function of its seed: `_pumped` advances simulated time in proportion to the wall time of the computation (first fit 0.40 sim-s at 0.27 s wall quiet, 0.84 sim-s at 1.04 s wall loaded; second fit 0.72 vs 2.68 sim-s), and full startups diverge afterwards (two outcome branches: "predicted length sigma 14.5-14.6 mm" and "13.5 mm"; a loaded run gave a third coefficient set). Same in the bare harness. Never affected the pretension. | See check 4. | Info for sim-based regression tests: compare with tolerances, never exact values. |
| F18 | Info | Plain HTTP on the LAN, Werkzeug development server (one thread per connection, no limit), default 0.0.0.0. The token is visible to anyone on the same Wi-Fi; an unauthenticated client can exhaust threads. | Banner prints "WARNING: This is a development server". | Print a warning when the host is not loopback; for away-from-home use Tailscale (already in the spec); consider waitress. |
| F19 | Info | No security headers (CSP, `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`); `/v1` (old page) builds HTML with `innerHTML` from server fields (checklist text, station ids): not attacker-controlled today. | `curl`-equivalent on `/`: only `Cache-Control`. | `Content-Security-Policy: default-src 'self'; img-src 'self' blob:` and `nosniff`. |
| F20 | Info | A pause while nothing moves (DISARMED, PARKED) latches `co.pause_requested`; the next command's first motion is refused once. A stray "stop" (voice noise) makes the next `start` end PAUSED with "paused: operator pause (chat)". Fail-safe, pre-existing supervisor semantics, but the chat/voice makes it easy to trigger. | Verified: pause in DISARMED, then `start` -> PAUSED, reason "paused: operator pause (chat)". | Show the latch in the pause reply ("the next motion will be held once"). |
| F21 | Info | The 2 s poll thread calls `HttpClawClient.status()`, which re-estimates `offset_us` whenever the RTT is within 1.5x the best seen. Before the app the mapping was set essentially once; now it moves by up to about +-0.75 x best RTT every 2 s (it also corrects drift, so net effect is small). | Code reading (`claw_link.py` `status()`); not measured on hardware. | Smooth the offset or accept updates only at near-best RTT. |
| F22 | Info | Test gaps: no test of HEAD/OPTIONS or of two clients; `test_host_keepalive_runs_while_the_stream_is_open` runs on the simulated clock (a lease can only expire if someone advances sim time without pumping, so wall-clock starvation cannot show), and nothing runs the hardware loop setting (F3). | Reading the test. | Pin F1/F4/F5/F6 fixes with the flipped tests in `test_phone_app_review.py`. |

## Evidence by check

### 1. Safety rules

* Motion without a fresh "yes": stateful fuzz (`fuzz_chat.py`, scratchpad) over 18,000 random messages built from motion, confirm,
  pause and filler words, two clients, random clock jumps up to 31 s: 0 violations. A motion command (start, resume, recover,
  lower, grip) ran only when the same client's previous message produced a pending question for that command, the message was
  a bare confirmation and no more than 30 s had passed. Only `pause` and `acknowledge` ever run without a question.
  `disarm` was never run (not reachable from chat). Existing tests cover timeout, state change at "yes", checklist at "yes".
* Cross-session confirmation: F1.
* Pause, live (`drive_r4.py`, stock service in `--sim`, 4 MJPEG streams plus status/frame/events/say pollers open, all four
  stations RUN in CALIBRATION): `POST /api/say {"text":"pause"}` answered in 20 ms with `command_run: "pause"`; state PAUSED
  after 36 ms; stations RUN -> HOLD ('HHHH') within 0.1 s -> IDLE ('IIII', armed and holding) at 0.23 s when the worker
  stopped; no faults; 10 s later still IDLE, no LEASE. Pause takes no service lock and no chat lock (`Chat.handle` and
  `Service._command`). The wording problem is F2.
* Losing the phone: `app.js` has no `unload`/`pagehide`/`beforeunload`/beacon/heartbeat; the service has no dead-man. In the
  r4 run the four stream clients and the pollers were dropped abruptly twice while the startup ran: nothing changed.

### 2. Security

* Every `/api` rule needs the token on every method (`probe_sec.py` section 1: all 9 rules x all methods answer 401 without
  it; HEAD/OPTIONS included; `//api/status` 404; `%2f`, `;`, `/./`, trailing-slash variants 401/404). Only
  `GET /api/stream.mjpg` accepts `?token=`; `HEAD`, `POST`, other routes and a wrong header + right query all 401.
* No route echoes the token (12 paths including 404/500 pages and `/`, `/v1`, `app.js`, `manifest`): none. Written to the log: F6.
* JSON-only POSTs: `text/plain` and form bodies 415/401 (existing test plus section 3). CSRF: no CORS headers on any
  response, the preflight (`OPTIONS` with `Origin`) answers 401 without `Access-Control-*`, and the token is a custom header
  that a cross-site page cannot set or read.
* XSS: `grep` finds no `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval` in `app.js` (they exist only
  in the old `/v1` page); all text goes through `textContent`/`createTextNode`. Dynamic test (`ui2.js`): chat text
  `<img src=x onerror=...><script>...</script>` sent through the composer and as the `why` of a pause (so it lands in the event
  log, the chat and Home): `window.__xss` undefined, 0 injected `img[src=x]`, 0 scripts, 0 dialogs; the markup is shown as text.
* Path traversal: only 7 fixed static routes exist (each calls `send_from_directory` with a constant name). 19 raw-socket
  traversal and probing paths (`/../`, `%2e%2e`, `%2f`, `%00`, `//etc/passwd`, `/static/`, `/.git/config`, `/data/cdpr/state.json`,
  `/service.py`, ...) all 404, no content leaked.

### 3. Host-loop safety

* By construction and by test: `/api/frame.jpg`, the stream, `/api/status`, `/api/say` and `can()` read the frame thread's
  cache, the polled claw dict or the event log; the only `ctx.claw` calls in `service.py` are `poll_claw` (own thread) and
  `grip` (command worker). Existing test `test_claw_frame_thread_caches_the_jpeg_and_routes_never_fetch_from_the_claw` counts
  claw hits: 1 frame fetch in total.
* Measured on the live `--sim` service with the keep-alive pings recorded (`launch_gaps.py`, `load4`-style clients, 4 streams
  + status 5 Hz + frame 2 Hz + events 1 Hz + say 0.5 Hz; wall-clock gap between consecutive ping broadcasts, nominal 20 ms of
  simulated time):

  | phase | duration | median | p99 | max |
  |---|---|---|---|---|
  | idle, no clients | 12 s | 11.9 ms | 15.1 ms | 24.3 ms |
  | idle, 4 streams + pollers | 25 s | 12.0 ms | 15.9 ms | 20.4 ms |
  | command (CALIBRATION), no clients | 40 s | 8.7 ms | 22.2 ms | 53.7 ms |
  | command (CALIBRATION), 4 streams + pollers | 50 s | 10.3 ms | 27.2 ms | 56.0 ms |

  The streams add about 1.6 ms median and 5 ms p99; the worst gap (56 ms, from the `_pumped` fits) is about a fifth of the
  300 ms lease. Each stream delivered 4.48 fps at idle and 2.96 fps while the simulator was busy. Request latency (status/
  frame/events/say): median 2-3 ms idle, 22-64 ms during calibration, max 253 ms. Caveat: in `--sim` the lease runs on
  simulated time, so these are wall-clock starvation indicators, not lease evidence; the hardware loop is F3.

### 4. Behaviour on a quiet machine: `start` through `/api/command` (checklist true)

Stock `python -m roomcleaner.cdpr.service --sim --port N` (config `config/robot.sim.json`, seed 0, fresh `--data` directory, one
other agent's pytest process held one of the 4 cores throughout, load average 1.3-2.3):

| run | outcome | time to READY | final reasons |
|---|---|---|---|
| r1 | READY, trust LOCAL_ONLY, stations IDLE/valid | 257.9 s | predicted length sigma 14.6 mm > 5.0 mm |
| r2 | READY, LOCAL_ONLY | 260.6 s | 13.5 mm |
| r3 | READY, LOCAL_ONLY | 249.6 s | 14.6 mm |
| L1 (8 CPU burners + other load, load average 12-15) | READY, LOCAL_ONLY | 827.2 s | different coefficients (a third branch) |

**The failure did not reproduce (0 of 4 service runs).** Further runs on the same scenario: bare harness (no `Service`, no
threads, `Supervisor.start()` directly) quiet x4 (219-230 s), loaded x1 (787 s), and the 953822d tree quiet (210 s): all READY.
A truncated startup (SELF_CHECK, SLACK_TAKEUP, INITIAL_LIFT) 30 times quiet and 15 times under the 8-burner load (3.9x
slower, 85 s each): all 45 pass with the identical pretension drag-watch peak (0.95 mm against the 10 mm threshold) and the
identical simulated time (112 s). So the pretension has a 10x margin and is deterministic here.

Diagnosis of the earlier failure ("claw dragged while tensioning (0.0148...)", record in `data/cdpr/state.json`, 16:59):

* Not CPU load: 0 failures in 55 clean-start runs (10 full startups, 45 truncated), including 4x slowdowns.
* Not the service's threads (render thread, claw poll thread, stream threads, host loop): the bare harness behaves the same and
  the stock service passed at both load levels. The one real wall-clock coupling is `_pumped` (simulated time advances in
  proportion to the computation's wall time; full runs then split into two or three outcome branches, F17), and it
  affected neither the pretension nor the pass/fail outcome.
* Its inputs differed from every run I made: its first onset fit (`ledger.json`/`model.json`: marker pose 1.7296, 1.1531 m,
  yaw -2.5259 rad; L0 within 7 mm of mine) differs from the identical fit of all my runs (1.7324, 1.1614, -2.5293). Two things
  differ between then and now and could not be separated: the working tree (keep-alive round 2 `startup.py`/`config.py` edits
  landed between 16:51 and 19:00) and the persisted `data/cdpr` state, which does change the pretension (0.95 -> 2.72 mm,
  F16). Conclusion: not attributable to the real-time sim wall-clock coupling or to the service; most likely a transient
  startup/config state of that moment and/or contaminated persisted state. Repeat `start` from a clean `--data` directory
  (and note the stale RECOVERY_REQUIRED left in `data/cdpr`).

### 5. UI (Playwright, Chromium, 360x740 and 390x844, light and dark, tabs Home/Camera/Setup/Chat)

* No horizontal scroll on any of the 16 combinations (document, body and tab widths equal the viewport; no element beyond
  the right edge, the quick-reply chip row excepted: it is a deliberate scroller).
* PAUSE is inside the viewport and is the top element at its centre on every tab; the emergency-stop line is present with
  the exact text, inside the viewport, on every tab. Also true with the confirm sheet open (360x740), at 360x330 (keyboard-
  sized: chat log shrinks to about one row, composer, PAUSE and tab bar remain) and in landscape 740x360.
* Exception: the connect overlay (F14). Dark mode readable (screenshots in the scratchpad `ui_out/`); contrast F15.
* Console: the only errors are the expected `/api/calibration` 404 (one or two per session). No page errors, no failed
  requests, no other 4xx/5xx.
* Camera tab (screenshot checked): stream starts, LIVE pill, frame age, marker line ("marker in view ... modelled, not
  drawn") and transport shown. Start is disabled until all five boxes are ticked and enabled after; the tick state is lost on
  reload. Network behaviour: F13.

### 6. Tests

`pytest tests/cdpr/test_phone_app.py tests/cdpr/test_service.py tests/cdpr/test_claw_link.py tests/cdpr/test_margin_trust.py`:
**109 passed in 693 s** (90 + 4 + 3 + 12). The new `tests/cdpr/test_phone_app_review.py`: 25 passed in 7 s against both the
clean HEAD copy and the current working tree.

## What I could not check

* Real hardware: `HttpClawClient` timing, the claw node's single-threaded web server handling `/status` + `/frame` + `/grip`
  together, real Wi-Fi, the `RealRuntime` pump (F3 is a model on this PC), a real `ThreadedFrameSource`, the hardware
  start-up path (`build_hardware_context`), `grip` against the real servo.
* Real phones: only headless Chromium emulation. Not seen on iOS Safari or Android Chrome: speech recognition/synthesis,
  home-screen install and the manifest start URL (which carries no token), safe-area insets, `100dvh` with the real
  keyboard, background-tab throttling, screen-reader behaviour.
* HTTPS / Tailscale access, sniffing on a shared network, long soak (hours: the event log is bounded at 500, threads not
  watched), more than one real client at a time beyond the scripted ones.
* The earlier startup failure itself (not reproduced, root cause not established, see check 4); whether the concurrent
  three-station edits in the working tree change any finding (service.py, app.js and index.html are being modified; F10's
  unknown-station case is already answered with a 400 there).
* `qrcode` rendering (package not installed; only the unit test with a stand-in).

## Reproduction

All scripts are in the session scratchpad, not in the repo: `.../scratchpad/probe_sec.py` (auth matrix, token leakage, JSON,
cross-phone confirm, parse tables), `probe_stream.py` (F4/F5), `fuzz_chat.py`, `drive.py` + `runone.sh` (stock service +
start, item 4), `launch_gaps.py` + `drive_r4.py` + `gapstats.py` (host-loop gaps and pause), `harness_start*.py`,
`first_stage*.py` (bare harness, truncated startups, persisted state), `ui.js`, `ui2.js`, `ui3.js` (Playwright). Run from a
`git archive HEAD` copy with `PYTHONPATH` set to it and `OMP_NUM_THREADS=1`. The regression tests run with
`OMP_NUM_THREADS=1 /usr/bin/python3 -m pytest tests/cdpr/test_phone_app_review.py`.
