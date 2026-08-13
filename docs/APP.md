# RoomCleaner consoles

There are currently **two browser consoles**, built the same day on opposite
sides of the project, that will converge into one app (see "Convergence"
below). They share `requirements-app.txt` (Flask) and the same underlying
planner/kinematics — neither reimplements robot math.

| | Live perception console | Operations console |
|---|---|---|
| Run | `python -m scripts.live_app --camera 1` | `python -m roomcleaner.app --sim` |
| Port | http://localhost:8000 | http://localhost:8010 |
| Star of the show | The REAL camera feed | The mission execution loop |
| Validated on | Jasper's Windows machine + innomaker camera | Cloud, headless browser, full sim missions |

Only one program can hold the camera at a time — don't run the perception
console and `detect_webcam` (or, later, the operations console in `--live`)
simultaneously.

---

## 1 · Live perception console (`scripts/live_app.py`)

A window onto the robot's real-time perception: the annotated camera feed
(capture thread + ~1–2 fps CPU inference thread + ~20 fps MJPEG overlay so the
video never stutters), a live detected-items panel with floor coordinates, and
a sensitivity slider.

- **Robot & plan panel** — turns current detections into a plan with the same
  `Controller` + `CableRobot` the hardware will use: nearest-first pickup
  order, per-target winch cable lengths (A–D) + max tension + reachability.
- **3-D room view** (`/api/room.png`) with a **Live view / Animate plan**
  toggle — "Animate plan" renders a GIF of the claw flying the full route
  (`/api/room.gif`, ~10 s, cached by detection signature).
- `--demo` seeds simulated laundry so the whole console runs camera-free.
- Options: `--camera N`, `--port`, `--conf 0.25`, `--host 0.0.0.0` (LAN).
- Endpoints: `/`, `/video_feed`, `/snapshot.jpg`, `/api/state`,
  `/api/config` (POST `{"conf": 0.4}`), `/api/plan`, `/api/room.png`,
  `/api/room.gif`.
- Floor `(x, y)` uses placeholder room dimensions from `roomcleaner/config.py`
  until the room is measured; detection is real, coordinates aren't calibrated.
- Helper: `python -m scripts.camera_view --list` finds the camera index
  (innomaker was index 1 on Jasper's machine; integrated webcam 0).

## 2 · Operations console (`roomcleaner/app`)

Mission control for the robot — the same UI in two modes:

- `--sim` (default): a continuous simulated session. A Pillow-rendered
  top-down "camera" (room grid, fan keep-out disc, hamper, detection boxes,
  cables, claw with z-halo) streams at `/stream.mjpg`; missions play back in
  real time through the actual `Controller.iter_actions()` stream.
- `--live`: wires the real Webcam + YoloWorldDetector + serial winch driver +
  WiFi gripper through the identical session interface. **Not yet
  bench-validated** — needs real winches homed, camera calibration, and the
  ESP32 reachable; see "Bench validation" below.

Panels: live feed; status cards (phase, claw position, items picked, claw
link/battery); four per-cable tension bars against the legal [0.5, 40] N band
(state written in words, not color alone); operations log distinguishing
`plan ·` narration (planner, logged ahead of time) from executed events;
controls — Start / Pause / Resume / software **STOP** (the physical kill
switch remains the wall power strip), Home, Park, Grip, Release, and a jog pad
(0.1 m steps, idle/paused only, workspace-clamped and fan-keep-out-checked
server-side); a room/fan/hamper settings drawer (applying restarts the sim
session with the new geometry).

API: `GET /api/status` · `POST /api/command`
(`start|pause|resume|stop|home|park|grip|release|jog`; invalid → 400,
valid-but-not-now → 409) · `GET/POST /api/config`. Tests: `tests/test_app.py`
(Flask test client, no sockets).

### Bench validation still owed (live mode)

Serial homing/moves on real winches; `OverheadLinearMapper` camera
calibration; ESP32 gripper reachability + battery/RSSI telemetry (needs a
firmware endpoint); STOP latency at move-step granularity; live tensions are
model-derived (no load cells).

## Convergence

Target end-state: **one app** — the operations console's session/command
architecture absorbing the perception console's proven capture/overlay
pipeline (its capture+inference threading becomes `LiveSession`'s feed) and
its plan/3-D panels. That merge must happen on the machine with the camera so
the live path stays validated; tracked in DESIGN_STATE.md. Until then: run the
perception console to watch the camera, the operations console to fly
missions in sim.
