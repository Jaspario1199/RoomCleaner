# RoomCleaner live app

A browser dashboard onto the robot's real-time perception: the camera feed with
detection boxes drawn on it, a live list of what the software is marking as
laundry (with floor coordinates), and a sensitivity slider. It's built to grow
into the full RoomCleaner console.

## Run it

```bash
# one-time: install the vision + app extras into the venv
venv\Scripts\python.exe -m pip install -r requirements-vision.txt -r requirements-app.txt

# start the app on the innomaker (usually camera index 1)
venv\Scripts\python.exe -m scripts.live_app --camera 1
```

Then open **http://localhost:8000** in your browser. Ctrl-C in the terminal
stops it.

Options: `--camera N` (index), `--port 8000`, `--conf 0.25` (starting
threshold, tunable live in the UI), `--host 0.0.0.0` (reach it from another
device on your LAN / over Tailscale instead of just this machine), `--demo`
(no camera: seed simulated laundry so the whole console works offline).

## Robot & plan panel

Below the feed, the **Robot & plan** panel turns detections into a plan using
the *same* `Controller` + `CableRobot` that drive the (eventual) hardware:
- the nearest-first pickup order,
- per-target **winch cable lengths** (A/B/C/D, the 4 ceiling motors) and the
  max cable tension at the grab point, with a reachable / not-reachable flag,
- a live **3-D room view** (`/api/room.png`): winches, cables, claw at its rest
  pose, detected laundry, hamper, and the fan keep-out volume.

Endpoints: `/api/plan` (JSON plan), `/api/room.png` (rendered 3-D view). The
plan is recomputed from the current detections each request, so it tracks the
live feed. Try it now with `--demo` (no camera needed).

## How it works

- A **capture** thread reads frames from the camera continuously, so the video
  is smooth.
- An **inference** thread runs the YOLO-World open-vocabulary detector (~1–2 fps
  on CPU) on the latest frame and caches the boxes.
- The MJPEG stream draws the latest boxes on the latest frame at ~20 fps, so the
  feed never stutters while waiting on the model.

The detections shown are the exact `Detection` objects (label, confidence, floor
`(x, y)`) that the robot's control loop consumes — this is a window onto the real
perception, not a separate demo.

Endpoints: `/` (dashboard), `/video_feed` (annotated MJPEG),
`/api/state` (JSON), `/api/config` (POST `{"conf": 0.4}` to retune live).

## Notes

- Only one program can hold the camera at a time — stop `detect_webcam` /
  `innomaker_view` before starting the app.
- Floor `(x, y)` uses the placeholder `room_width` / `room_depth` in
  `roomcleaner/config.py` until the room is measured — detection is real,
  coordinates are not yet calibrated.

## Roadmap (the "whole RoomCleaner app")

Done: live feed + detection overlays, detected-items panel, sensitivity slider,
and the **Robot & plan** panel (pickup plan + per-target winch cable lengths +
3-D room view). Still to come as the hardware loop lands:
- live robot **status**: real effector position, payload, hamper count,
- **run / pause / e-stop** controls that drive the winches,
- animate the planned path in the 3-D view (not just the rest pose),
- overlay the reachable-workspace footprint on the room floor.
