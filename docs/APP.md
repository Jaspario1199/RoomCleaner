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
