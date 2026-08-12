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
device on your LAN / over Tailscale instead of just this machine).

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

The dashboard has a reserved **Robot & plan** panel for:
- the 3-D room view + computed pickup plan (reuse `simulator.render_frame` +
  `control.state_machine.Controller`),
- per-target cable-length / winch commands (`kinematics.CableRobot`),
- robot status: effector position, payload, hamper count,
- run / pause controls once the hardware loop exists.
