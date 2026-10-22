# Phone app: independent verification of the fixes for F1, F2, F4, F5, F6, F14

Date: 2026-10-21. Verifier: Sonnet (did not write the fixes or the review). Subject: commit `678a704` on `claude/magical-cerf-gqr7j7`
(`chat.py`, `service.py`, `static/app.js`, `static/app.css`, `tests/cdpr/test_phone_app_review.py`). Review: `verification/phone_app_review.md`;
implementer's claims: `verification/phone_app_fixes_results.md`. Scratch probes (not in the repo): `/tmp/claude-0/-home-user-RoomCleaner/c51aa926-76d6-52eb-b707-af7c5e22fd24/scratchpad/verify_app/`.
New test code kept: `tests/cdpr/test_phone_app_fixes_verification.py` (46 tests). Nothing else in the repo was changed by me. I committed nothing; an earlier draft of this report and the test file were picked up by a WIP commit (`fc8418f`) made by someone else while I was working, and later edits to this report are uncommitted.
`roomcleaner/cdpr/garments.py`, `tasks.py` and `startup.py` (another agent's work, uncommitted when I started) were not read, and the `task` command was tested with a stub runner; but every run here used the working tree, so the simulated robot (`SimRobot` imports `startup.py`) ran whatever version of those files was on disk at the time.

## Verdict: PASS WITH CONDITIONS

All six findings behave as the review asked, measured with my own probes (Flask client, real threaded Werkzeug server, the real
`python -m roomcleaner.cdpr.service --sim` process, and Chromium 1194 driven by Playwright). PAUSE (HTTP and chat), start, lower, disarm and
the task command still work, also on the hardware loop setting. `Service._run`, `start_background`, `idle_tick` are source-identical to the
parent commit (AST comparison). No High or Medium issue found. Conditions (none blocks the test, the first is a one-line CSS change I recommend before tonight):

1. Low (new): with the "Connect to the robot" overlay up, pressing PAUSE shows no feedback: its failure toast is drawn under the overlay (see N1).
2. Low: ids-less callers (curl, scripts) still share one confirmation bucket; use only the phone page for confirmations tonight (N2).
3. Low (docs): `docs/APP.md` line 36 still says the question is "keyed by the token".

## Per finding

| Id | Expected behaviour (review) | Measured | Result |
|---|---|---|---|
| F1 | A "yes" from another phone, or from a client without an id, does not confirm a pending motion question; a malformed id is refused. | API, real `Service` over the sim: A asks "lower the claw"; B ("bbbbbbbb22222222"), a client with no header and a client with an empty header each say "yes", "go ahead", "do it": reply "Nothing is waiting for confirmation.", `command_run` None, robot PAUSED and not busy, A's pending still there; A's own "yes" then runs `lower`. Reverse (id-less asks; A or B confirms): nothing runs. `start` (DISARMED, checklist true): A asks, B "yes" with checklist true: nothing runs; A's own "yes" with the ticks cleared is refused. 11 malformed ids (7 and 65 characters, space, `../`, é, `a:b`, `c:...`, leading and trailing space) all 400; 8 and 64 characters accepted. Chromium, two contexts on the live process, both with every checklist box ticked: A types "start" (pending bar shows), B types "yes" and "go ahead" (both "Nothing is waiting for confirmation."), robot stays DISARMED and not busy, A's bar stays, A's "no" cancels. Every `/api` request of the page carries `X-Client` (32 hex), a new id per page load and per context. The PAUSE button path (`/api/command`) ignores the header (200 even with a malformed one). | PASS |
| F2 | Pause text follows `stations[*].state`: not "holding" in DISARMED or with missing/stale telemetry; "NOT holding" for an OFF station. | Real `/api/command` pause and chat "stop", station telemetry set on the coordinator links, 18 cases in `test_v_f2_...` and a larger scratch probe: DISARMED with no telemetry, all OFF, or all IDLE: "nothing is holding position" (kind `disarmed`). RECOVERY_REQUIRED and FAULT with telemetry missing, 30 s stale (IDLE but old), or one station stale: "Holding state UNKNOWN: no current telemetry from ... The claw may be hanging or falling: stay clear." All four stations IDLE and online: "every station reports IDLE, holding position with torque on". One station OFF: "NOT holding: station B OFF (no holding torque) ...". One FAULT: "station C reports FAULT (stopped, holding not confirmed)". RUN or HOLD: "still stopping". Unknown state code: UNKNOWN. The phrase "torque on" never appears in a non-IDLE case. HTTP and chat texts agree in every case. Event-log line "Pause pressed in X." has no holding claim. `status()` raising: HTTP pause still 200 with kind `unknown` and the exception type in the text. Browser: PAUSE toast shows the service text (long UNKNOWN text, 142 px high at 360 px, legible, above PAUSE, inside the viewport at 360x480). | PASS |
| F4 | HEAD on the stream must not take a slot. | Live process, raw sockets: 6 HEADs (header token) return 200; then 4 streams 200 and the 5th 429; after the 4 are closed (and after 4 RST aborts) a new GET gets 200; HEAD with 4 streams open is 200. `_streams` is 0 after the HEADs (in-process test). | PASS |
| F5 | With no cached frame the stream must not hold slots for clients that left. | In-process server: 6 attempts with no frame: 503 in 0-4 ms each, `_streams` 0. With frames then none while 4 clients stay connected: the server closes each after 5.2 s and `_streams` returns to 0 (`STREAM_NOFRAME_S` = 5). | PASS |
| F6 | The token must not reach the access log (page loads, stream requests); a reload must still work. | Live `python -m roomcleaner.cdpr.service --sim` (745 log lines after curl and Chromium runs): the token appears on line 2 only (the startup URL line). 61 request lines show `token=<redacted>`: `/?token=`, `/?tab=chat&token=...&x=1`, `/?TOKEN=`, duplicate `token=` twice, `/v1?token=`, `/api/status?token=` (401), wrong-token stream 401, real stream 200, `/%zz?token=`, a malformed request. Chromium: `/?tab=chat&token=T` leaves `/?tab=chat` in the address bar, `/#token=T` leaves `/`; the token is not in the DOM; the page is "online"; a reload stays connected (also for the hash form); with `sessionStorage` blocked the token stays in the URL and the reload still connects. Connect form still accepts a pasted address at 360x480. | PASS |
| F14 | PAUSE and the emergency-stop line stay visible and on top while the connect overlay is shown, about 360 px wide. | Chromium, no token, `?token=WRONG`, and a valid page that starts receiving 401 (service restart), at 360x740, 360x640, 360x480, 320x568, 390x844, 360x360, light and dark = 36 cases: in all, PAUSE and the e-stop line are inside the viewport, `elementFromPoint` returns them at 9 points each, the overlay ends 8 px above PAUSE, no horizontal scroll, z-index overlay 50 / dock 60, Playwright's actionability-checked `click('#pause')` succeeds. The same probe against the parent commit fails (not topmost, click times out), so it discriminates. At 360x360 the card scrolls inside the overlay (it is not cut off at the top). | PASS (see N1) |

## Regressions and new issues

| Id | Sev | Issue | Reproducible case |
|---|---|---|---|
| N1 | Low | The PAUSE failure toast is hidden behind the connect overlay. The overlay now ends above PAUSE, so the toast (`bottom` = dock height + 8 px, z-index 30) lies inside the overlay area, below its z-index 50. With no or a wrong token PAUSE is pressable but shows nothing ("PAUSE DID NOT REACH THE ROBOT SERVICE. Use the power strip..." never appears). The overlay note and the e-stop line are visible, and PAUSE cannot work without a token anyway; before the fix the button could not be pressed at all. | Chromium 360x740, open `/` with no token, click PAUSE: toast is in the DOM, `elementFromPoint` at its centre returns `#connect`, screenshot shows nothing. Pinned by `test_v_f14_pin_the_pause_failure_toast_is_hidden_behind_the_connect_overlay`. Fix: `.toast { z-index: 70 }` (above `.connect` 50 and `.dock` 60). |
| N2 | Low | Two callers that send no `X-Client` (curl, scripts, an old cached page) share the token bucket, so one can confirm the other's question. The page always sends an id; an id-carrying client and an id-less one cannot reach each other. | Two Flask clients without `X-Client`: the first says "lower", the second says "yes": `lower` runs. Pinned by `test_v_f1_pin_two_requests_without_a_client_id_share_one_bucket`. Fix: id-less requests get no confirmation at all, or a one-shot nonce. |
| N3 | Low | `/api/say` validates `X-Client` before it looks at the text, so a chat "stop" with a malformed id is a 400 and does not pause. The page cannot produce one and the PAUSE button does not read the header. | `POST /api/say {"text":"stop"}` with `X-Client: x`: 400, no pause. Pinned by `test_v_f1_pin_a_chat_stop_with_a_malformed_client_id_is_refused`. Fix: honour pause first, validate the id only on the confirmation path. |
| N4 | Low | A pause no longer cancels other clients' pending questions. Before F1 any phone's chat "stop" cleared the shared question by accident; now only the same client's "stop" does, and the PAUSE button never did (also before). Phone A's "yes" within 30 s runs `lower` after phone B (or the button) paused; the Yes button stays on A's screen. A motion command re-checks `can()` at "yes", so `lower` is legal in PAUSED. | A asks "lower", B says "stop", A says "yes": `lower` runs (parent commit: "Nothing is waiting"). Pinned by `test_v_f1_pin_a_chat_stop_from_another_phone_does_not_cancel_a_pending_question`. Fix: drop every pending question on any pause (chat or button). |
| N5 | Info | `CLIENT_ID_RX` uses `$`, which also matches before a trailing newline: `chat_key("aaaaaaaa\n", t)` returns `"c:aaaaaaaa\n"`. Not reachable over HTTP (header values cannot carry a newline). | `chat_key` call above. Use `fullmatch`. |
| N6 | Info | After the server ends a stream that lost its frames (F5), the page stays in stream mode with the last image until the tab is revisited (an `<img>` multipart end raises no `onerror`). The status pill shows STALE or NO FRAME. Camera is not a control. | Stop frames for more than 5 s with the Camera tab open. |
| N7 | Info | DISARMED wording is state-only: "nothing is holding position ... The claw should be resting on the floor" even if a station reports IDLE. That is what the review asked for and is the conservative direction. The supervisor sends a restart with a possibly hanging claw to RECOVERY_REQUIRED, not DISARMED. | Set all links to IDLE, state DISARMED, pause. |
| N8 | Info | Docs: `docs/APP.md` line 36 says "keyed by the token". The implementer noted it. | `grep -n "keyed by" docs/APP.md` |

Checked and found clean in the diff: no broad `except` that hides an error (`hold_report` failure in the HTTP pause path returns an explicit
"could not read the station states (Type)" text after the pause already ran; the JS catches only fall back to the old behaviour); the
chat tables are bounded (`_pending` entries older than expiry + 120 s are dropped on the next non-pause request, `_lapsed` is capped at 64;
size is bounded by request rate x 150 s and needs the token); the only way a missing header reaches a confirmation is N2; the stream slot
is released exactly once (lock-guarded) by the generator or by `call_on_close`; `Service._run`, `start_background`, `idle_tick`, `_command`,
`command` are identical to `678a704^` (AST comparison; only `Service._ingest` text and the `say` docstring changed), `BUSY_BACKOFF_S`,
`LOCK_WAIT_S`, `MAX_STREAMS` unchanged.

## PAUSE and commands on the hardware loop (`start_background(real_sleep_s=0.0)`, real threaded server, runtime that really sleeps)

| Check | Result |
|---|---|
| HTTP pause and chat "stop"/"pause" while DISARMED | 200, 2-7 ms |
| Chat "start" + "yes" (checklist) while the host loop spins | accepted (`command_run` = start) |
| 5 HTTP pauses, then 5 chat pauses ("stop", "pause", "halt", "freeze", "stop!") while `start` runs | all 200, 2-11 ms (limit 1 s); the startup ends PAUSED ("paused: operator pause") |
| Chat "lower" + "yes" from PAUSED; chat "stop" while `lower` runs | accepted; lower ends PARKED, or PAUSED when paused |
| HTTP `disarm` (confirm `claw_supported`) | 200 |
| With and without `X-Client` | both pass (no-id run repeated) |
| `task` command in READY (stub runner), HTTP pause and chat "stop" during it | 200, ends PAUSED both times |
| `tests/cdpr/test_three_station_review.py -k h1` | 1 passed, 1 skipped ("H1 already fixed") |

## Test counts

| Run | Result |
|---|---|
| `/usr/bin/python3 -m pytest -q tests/cdpr/test_phone_app_review.py tests/cdpr/test_phone_app.py tests/cdpr/test_service.py` | 141 passed, no skips, 17.9 s (matches the implementer's 47 + 90 + 4) |
| `tests/cdpr/test_three_station_review.py -k h1` | 1 passed, 1 skipped |
| `tests/cdpr/test_phone_app_fixes_verification.py` (new, mine) | 46 passed, 21 s; run together with the three files above: 187 passed in 39 s |
| other files that import the service (`test_three_station_review`, `test_three_station`, `test_margin_trust`, `test_board_attitude`, `test_board_followups`) | partial, stopped at about 47 % after 22 min (slow simulated startups): 4 failures, all stale pins on the guide text, unrelated to the phone app and to `garments.py`/`tasks.py`/`startup.py`: `test_l1_pin_...`, `test_l2_pin_...`, `test_m5_l4_pin_...`, `test_d1_pin_...` (each asserts the OLD wrong wording of `docs/THREE_STATION_MODE.md`, which later commits corrected, e.g. the guide now contains `--data`; the tests say "DEFECT ... fixed? flip this test"). One more `F` appeared near `test_board_attitude.py` in that combined run (the run was stopped before its summary, so the name is not recorded); that file passes alone (24 passed, `test_board_attitude.py` only imports `build_marker_detector` from the service, which this change did not touch), consistent with the other agent's `startup.py`/`tasks.py` changing under the run. The two tests in those files that drive the app (`test_service_status_and_the_phone_app_list_only_the_active_stations`, `test_bead_search_is_off_by_default_and_validated`) pass. |
| whole `tests/cdpr` | not run to the end (about 11 % in 7 min, then stopped); the other agent's uncommitted `garments.py`, `tasks.py`, `startup.py` are in the working tree, so a full run would mix in their work |

Browser checks were run from Node (`/opt/node22/lib/node_modules/playwright`, Chromium 1194 from `/opt/pw-browsers`); the repo's own
browser tests in `test_phone_app_review.py` ran as part of the 141 (not skipped).

## Not verified

Real hardware timing (the loop test is a model: simulated stations, real sleeps and threads); a physical phone (soft keyboard, Safari);
voice input (F7 is still open: a transcript of "yes" confirms a question of the same client); F9, F10, F13 are untouched by this change.
