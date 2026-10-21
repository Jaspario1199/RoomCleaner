# Phone app: fixes for review findings F1, F2, F4, F5, F6, F14

Date: 2026-10-21. Implementer: Sonnet (did not write the review). Findings: `verification/phone_app_review.md`. Not committed.
Files changed: `roomcleaner/cdpr/chat.py`, `roomcleaner/cdpr/service.py`, `roomcleaner/cdpr/static/app.js`, `static/app.css`,
`tests/cdpr/test_phone_app_review.py`. Untouched: supervisor/startup/coordinator/station_core/config, `Service._run` and
`start_background` (H1/F3), `index.html` (not needed), F7-F13 and F15-F22.

## What changed

| Id | Change | Where |
|---|---|---|
| F1 | The page makes a random 128-bit id at every page load (`crypto.getRandomValues`; `randomUUID` needs https) and sends it as `X-Client` on every request. `/api/say` keys the pending question on `c:<id>`. A malformed id (not 8-64 of `A-Za-z0-9_-`) is a 400. A request with no id uses the old token-keyed bucket (scripts, curl, the existing tests); the two key spaces cannot meet (a token has no ":"), so neither side can confirm the other's question. Chat tables are bounded (expired questions dropped after 120 s, 64 timed-out notes kept). | `service.py` `chat_key`, `/api/say`; `chat.py` `_prune`; `app.js` `CLIENT` |
| F2 | New `chat.hold_report(status)` builds the pause wording from `state` and `stations[*].state/online`. "holding position with torque on" only when every active station is online and IDLE. DISARMED: "nothing is holding position ... not armed". An OFF station: "NOT holding: station B OFF". No/stale telemetry or FAULT or no stations: "Holding state UNKNOWN ... The claw may be hanging or falling: stay clear". RUN/HOLD: "still stopping". The chat reply uses it; `/api/command` `pause` returns it as `hold {kind, text}` and the PAUSE toast shows that text (non-calm kinds in the red toast, 7 s). The event-log line "Pause pressed in X: holding position." lost its fixed claim. | `chat.py`, `service.py`, `app.js` `doPause` |
| F4 | `HEAD` is answered without a generator and without a slot. The slot is also released by `Response.call_on_close` (once-only), so a stream the server never iterates cannot leak one. | `service.py` `stream` |
| F5 | No cached frame at request time: 503 at once (the page already falls back to stills). A stream whose frames stop for `STREAM_NOFRAME_S` = 5 s ends and frees its slot. | `service.py` `stream` |
| F6 | `_RedactToken` logging filter on the `werkzeug` logger (installed once by `create_app`) rewrites `token=<value>` to `token=<redacted>` in the request line. The page removes `token` from `?` and `#` with `history.replaceState` after storing it in `sessionStorage` (only if the store really holds it, so a reload still works where storage is blocked). The startup URL line still prints the token. | `service.py`, `app.js` `stripTokenFromUrl` |
| F14 | `.connect` is `inset: 0 0 var(--dock-h) 0` (ends above the PAUSE dock and tab bar; `showConnect` calls `layout()` to set the height) and `.dock` is `position: relative; z-index: 60` (above the overlay's 50) as a second guard. | `app.css`, `app.js` |

## Measured results

* `tests/cdpr/test_phone_app_review.py tests/cdpr/test_phone_app.py tests/cdpr/test_service.py`: **141 passed** (47 + 90 + 4), 16 s.
  `tests/cdpr/test_three_station_review.py -k h1`: 1 passed, 1 skipped (the old pin, "H1 already fixed").
* The review file has 47 tests (was 25): F1 (4), F2 (4 + 8 table cases), F4 (2), F5 (2), F6 (3), F14 (1 CSS) flipped or added, plus 4 real-browser tests (F14, F6, F1, F2) sharing one Chromium run.
  Run against the old `chat.py`/`service.py`/`static/*` (git stash, the new test file with its import guarded): **29 failed, 18 passed**;
  the 29 are exactly the F1/F2/F4/F5/F6/F14 tests (5/14/2/2/4/2), the 18 that still pass are the unchanged F3 and F7-F11 pins. All 47 pass on the new code.
* F1: phone B and an id-less script answer "Nothing is waiting for confirmation."; the robot stayed PAUSED, no chat command ran; A's own "yes" ran `lower`. In two real Chromium contexts: B's reply was that sentence, A's pending bar stayed, the two page ids differed (32 hex each).
* F2: with no station telemetry DISARMED replies "nothing is holding position"; RECOVERY_REQUIRED and FAULT reply "Holding state UNKNOWN: no current telemetry from stations A, B, C, D ... may be hanging or falling: stay clear"; with the four simulated stations armed and reporting IDLE it still says "every station reports IDLE, holding position with torque on". The browser toast showed the UNKNOWN text.
* F4: before, 4 HEADs left `_streams == 4` and a GET got 429; now 6 HEADs leave 0 and a GET streams (200) and frees its slot when the client closes.
* F5: before, 4 aborted no-frame attempts held 4 slots (5th: 429); now each attempt gets 503 at once and `_streams == 0`. A stream that loses its frames while connected ends after the timeout (0.4 s in the test).
* F6: access log now reads `"GET /?token=<redacted> HTTP/1.1" 200`, `GET /?tab=chat&token=<redacted> ...`, `GET /api/stream.mjpg?token=<redacted>&_=1 ...`; neither the real nor a wrong token appears. In Chromium the address bar after `?token=T&tab=chat` is `?tab=chat` (also from `#token=T`), the page is connected, a reload stays connected.
* F14 (Chromium 1194, Playwright 1.56.1 driven from Node, no token and `?token=WRONG`, 320x568, 360x740, 360x480, 390x844, 768x1024, 1280x800 = 12 cases): in all 12 PAUSE and the e-stop line are inside the viewport and are the topmost element at their centres, the connect card ends above PAUSE, no horizontal scroll. The browser tests skip when node, the `playwright` package or Chromium is missing.

## Notes for the lead

* `tests/cdpr/test_phone_app.py::test_unconfirmed_question_times_out_after_30_seconds` asks `svc.chat.pending(svc.token)`: id-less requests therefore keep the token as their key (the legacy bucket) instead of a separate "anon" key. Only id-less callers share it.
* `docs/APP.md` line 36 still says the question is "keyed by the token" (and `chat.py` no longer does); not edited (outside the allowed files).
* Judgement calls: a station in FAULT is reported as "holding not confirmed" (the protocol says FAULT is still enabled, the review listed it as not holding); the "stopping" toast is a snapshot taken right after the pause and is not updated. Reloading a page drops its pending question (a new id), which matches the page clearing its pending bar.
* Still open by design: the camera `<img>` URL carries `?token=` (redacted in the log, but visible to the browser's own tools); a short-lived stream ticket would remove that.
