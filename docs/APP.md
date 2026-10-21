## Phone app (gen-2)

The phone app is served by the gen-2 operator service (`roomcleaner/cdpr/service.py`), the only program that talks to
the stations and the claw. The phone never reaches the hardware directly. Specification and safety rules:
`docs/PHONE_APP_SPEC.md`. Screenshots (390 x 844): `docs/app_screenshots/`. The gen-1 console described below is
unchanged history.

```bash
pip install -r requirements-app.txt                 # Flask (qrcode is optional, see below)
python -m roomcleaner.cdpr.service --sim --host 0.0.0.0 --port 8100                  # simulated robot
python -m roomcleaner.cdpr.service --config config/robot.json --host 0.0.0.0         # hardware
# terminal: "RoomCleaner phone app: http://192.168.x.y:8100/?token=..." (+ a QR code if `pip install qrcode`)
```

Open that address on the phone (same Wi-Fi). The token is read from `?token=` or `#token=`, kept in `sessionStorage`
and sent as `X-Token`; it changes every time the service starts. If the app is opened without it (home-screen icon), it
asks for the token or the full address. `--host` defaults to `0.0.0.0`; use `127.0.0.1` to keep it on this computer. For
access away from home use Tailscale; do not forward ports. The old setup page is at `/v1`. Add to Home Screen gives a
full-screen app (web manifest + icon).

| Tab | What it does |
|---|---|
| Home | State in large text with plain-language detail, trust level and its reasons, stations A-D (online, fault, state, reference), claw (battery V and low flag, grip, camera), busy indicator, last error, recent events |
| Camera | The frame the host already fetched from the claw, about 5 fps (MJPEG, still-JPEG fallback), frame age, marker/board detection status. `--sim`: the simulator's claw view |
| Setup | (a) room and anchors, (b) unmeasured configuration per stage, (c) pre-start safety checklist, (d) Start and live startup steps with reasons, recovery buttons only where the supervisor allows them (Resume, Acknowledge, Recover, Lower, Disarm with the typed `claw_supported`), (e) calibration result and trust |
| Chat | Rule-based "talk to the robot" (no cloud AI, no API key); optional mic and "speak replies" where the browser has speech recognition/synthesis (often only on https or localhost; typing always works) |

PAUSE (hold position) and the line "Emergency stop = the switched power strip. It drops the claw: nobody under the
robot." are on every screen. PAUSE holds torque (D21); the app never claims to be an emergency stop; losing the phone
does nothing to the robot, but PAUSE needs the connection and the app says so loudly when it is lost.

**Chat intents** (`roomcleaner/cdpr/chat.py`): `help`, `status`, `why` (trust and reasons), `battery`, `pause`,
`resume`, `start`, `acknowledge`, `recover`, `lower`, `open grip`, `close grip`; anything else gets "I didn't
understand" plus the help list. `pause` runs at once and cancels any question waiting. Every motion intent (start,
resume, recover, lower, open/close grip) is answered with a question and runs only on "yes"/"confirm" within 30 s (the
question is kept on the server, keyed by the token; any other message drops it; the command is re-checked when "yes"
arrives). `start` is refused with guidance unless the operator has ticked the checklist on the Setup tab (the chat never
ticks it). `acknowledge` runs without a question (it re-arms stations, it does not move the cables). Disarm is not
available from chat. Grip is not a supervisor command: from the phone it is allowed only when the claw is verified on the
floor (PARKED, or DISARMED with the floor confirmed) and the claw is reporting, and it uses the claw client's `grip()` on the
command worker.

**Endpoints added to the service** (all need `X-Token`, except the stream which also takes `?token=`):
`GET /api/events?since=N` (ordered `{id, t, kind, text}` log: state changes, reasons, startup steps, command results),
`POST /api/say {text, checklist?}` -> `{reply, pending_confirm, command_run, goto, chips}`, `GET /api/frame.jpg` (+
`X-Frame-Age-S`), `GET /api/stream.mjpg?token=` (~5 fps, at most 4 open), `/api/status` extended with `stations[*].online`,
`claw`, `camera`, `state_text`, `anchors_m`, `allowed`, `chips`. Pages: `/` (app), `/v1`, `/manifest.webmanifest`,
`/icon.png`. The camera routes serve the frame thread's cache (`claw_link.ThreadedFrameSource.latest_frame()`): they never
fetch from the claw and never touch the host loop. Claw telemetry for `/api/status` is polled every 2 s by a background
thread, not by requests.

Tests: `tests/cdpr/test_phone_app.py` (Flask test client in `--sim`, pure chat tests, claw frame cache against a fake claw).

---

# RoomCleaner console

**One browser app** (`roomcleaner/app`) — mission control and live perception
in the same page. It shares `requirements-app.txt` (Flask) with nothing else
special; the underlying planner/kinematics are the same modules the hardware
executor uses — the console never reimplements robot math.

```bash
pip install -r requirements-app.txt          # Flask; core deps cover the rest
python -m roomcleaner.app --sim              # simulation (default)
python -m roomcleaner.app --live --camera 1  # real camera (+ winches if reachable)
python -m roomcleaner.app --live --demo      # no camera: simulated laundry,
                                             # real detection→plan pipeline
# → http://localhost:8000
```

Options: `--port 8000`, `--host 0.0.0.0` (LAN/Tailscale), `--camera N`,
`--conf 0.25` (starting detection threshold; tune live in the UI), `--demo`
(implies `--live`). Only one program can hold the camera at a time — don't run
the console in `--live` alongside `detect_webcam`. Helper:
`python -m scripts.camera_view --list` finds the camera index (innomaker was
index 1 on Jasper's machine; integrated webcam 0).

## The three modes

| | `--sim` | `--live --camera N` | `--live --demo` |
|---|---|---|---|
| Feed | synthetic top-down render | real camera, boxes drawn live | rendered map of demo items |
| Detections | SimulatedDetector scatter | YOLO-World on camera frames | SimulatedDetector, real plan path |
| Missions | full playback, real time | real winches (needs hardware) | motion disabled |
| Needs | nothing | camera + vision stack (+ serial/ESP32 for motion) | nothing |

- **`--sim`** (default): a continuous simulated session. A Pillow-rendered
  top-down "camera" (room grid, fan keep-out disc, hamper, detection boxes,
  cables, claw with z-halo) streams at `/stream.mjpg`; missions play back in
  real time through the actual `Controller.iter_actions()` stream.
- **`--live`**: the camera feed runs through the capture thread + inference
  thread + self-healing reopen pipeline (`roomcleaner/app/perception.py`),
  ported intact from the retired perception console — it was validated on the
  real innomaker camera (the capture thread keeps video smooth at ~20 fps
  while CPU inference runs at ~1–2 fps; a stalled or frozen UVC stream
  triggers an automatic camera reopen). Winches (serial) and the gripper
  (ESP32 WiFi) are wired **only if reachable**; otherwise the session runs in
  **camera-only live mode** — feed, detections, plan and 3-D view all work,
  motion commands return 409, and the page shows a clear banner.
- **`--live --demo`**: no camera at all — simulated laundry is pushed through
  the REAL detection→plan pipeline. This is how the console is verified
  headlessly (see `tests/test_app.py`).

## Panels

Live feed (MJPEG) with a **detection-sensitivity slider** (confidence
threshold, applied live to the inference thread); status cards (phase, claw
position, items picked, claw link/battery); four per-cable tension bars
against the legal [0.5, 40] N band (state written in words, not color alone);
operations log distinguishing `plan ·` narration from executed events;
controls — Start / Pause / Resume / software **STOP** (the physical kill
switch remains the wall power strip), Home, Park, Grip, Release, and a jog pad
(0.1 m steps, idle/paused only, workspace-clamped and fan-keep-out-checked
server-side); a room/fan/hamper settings drawer (applying restarts the
session with the new geometry).

Below those, the perception row (absorbed from the perception console):

- **Detected items** — label, confidence bar, floor `(x, y)` coordinates.
- **Robot & plan** — turns current detections into a plan with the same
  `Controller` + `CableRobot` the hardware will use: nearest-first pickup
  order, per-target winch cable lengths (A–D), max tension, reachability.
- **3-D room view** (`/api/room.png`) with a **Live view / Animate plan**
  toggle — "Animate plan" renders a GIF of the claw flying the full route
  (`/api/room.gif`, ~10 s, cached by detection signature).

Floor `(x, y)` uses placeholder room dimensions from `roomcleaner/config.py`
until the room is measured; detection is real, coordinates aren't calibrated.

## API

- `GET /api/status` — pose, phase, tensions, claw telemetry, log tail,
  `detections` (label/conf/floor/bbox/area), `motion_enabled`, `hardware`
  (connected + reason), `perception` (cam/infer fps, resolution, reopens;
  null in sim), `config`.
- `POST /api/command` — `start|pause|resume|stop|home|park|grip|release|jog`;
  invalid → 400, valid-but-not-now (incl. motion without hardware) → 409.
- `GET/POST /api/config` — room/fan/hamper geometry (validated; applying
  restarts the session) and `conf` (the sensitivity slider; applied live, no
  restart, clamped to 0.05–0.90).
- `GET /api/plan` — pickup order + per-target cable lengths/tension/reach.
- `GET /api/room.png`, `GET /api/room.gif` — 3-D room snapshot / plan flight.
- `GET /stream.mjpg` — the feed.

Tests: `tests/test_app.py` (Flask test client, no sockets; `--live --demo` is
exercised headlessly there).

## Bench validation still owed (live motion)

Serial homing/moves on real winches; `OverheadLinearMapper` camera calibration
for the actual mount; ESP32 gripper reachability + battery/RSSI telemetry
(needs a firmware endpoint); STOP latency at move-step granularity; live
tensions are model-derived (no load cells). The camera/perception half of live
mode IS validated — the pipeline came over from the perception console intact.

## Changelog

- **2026-08-13 — console convergence.** The two same-day consoles (live
  perception console `scripts/live_app.py`:8000 and operations console
  `roomcleaner/app`:8010) merged into this single app on port **8000**. The
  operations console's session/command architecture absorbed the perception
  console's camera-validated capture+inference threading (now
  `roomcleaner/app/perception.py`, feeding `LiveSession`), its detected-items
  panel, sensitivity slider, Robot & plan panel, 3-D room view, animate-plan
  GIF, and `--demo` mode. `roomcleaner/webapp/` was deleted;
  `scripts/live_app.py` is now a thin forwarder into
  `python -m roomcleaner.app --live`.
