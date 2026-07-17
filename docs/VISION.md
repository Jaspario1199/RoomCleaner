# RoomCleaner — Vision & Calibration (Phase 1)

This is how the robot *sees* laundry and turns a camera pixel into a real floor
position the control loop can drive to.

## The pipeline

```
camera frame ──▶ open-vocabulary detector ──▶ boxes ──▶ floor mapper ──▶ (x, y) on floor
 (Webcam)         (YoloWorldDetector)                    (localization)     → Detection
```

1. **Capture** a frame (`perception/camera.py`, OpenCV).
2. **Detect** laundry (`perception/vision_detector.py`). We use an
   **open-vocabulary** detector (YOLO-World) so it finds laundry from *words* —
   `"sock"`, `"t-shirt"`, `"towel"`, … — with **no training**. Edit the class
   list to taste.
3. **Localize** each box to the floor (`perception/localization.py`): the
   box's *bottom-center* pixel (where the item meets the floor) is mapped to an
   `(x, y)` world coordinate.
4. The result is a `Detection` — the *exact same type* the simulator produced, so
   the Phase-0 control loop runs unchanged.

## Install (on your machine / the Pi)

```bash
pip install -r requirements-vision.txt   # ultralytics + opencv
```

The first detector run auto-downloads the YOLO-World weights. Everything else in
the repo works without these heavy deps — they're imported lazily.

## The two ways to map pixels → floor

### A. Zero-calibration (start here)
Mount **one camera on the ceiling, looking straight down, framing the whole
floor.** Then a pixel maps linearly to the floor rectangle and you only need your
room dimensions:

```python
from roomcleaner.perception.localization import OverheadLinearMapper
mapper = OverheadLinearMapper(room_width=4.0, room_depth=3.0,
                              image_w=1280, image_h=720)
```

Use `flip_x` / `flip_y` if the image comes in mirrored or rotated. This is the
"works out of the box after you enter room dimensions" path.

### B. Precise 4-point homography (when the camera is tilted/off-center)
Tape or note four known floor points (e.g. the room corners, or a measured
rectangle), read their pixel locations once, and fit a homography that corrects
perspective:

```python
from roomcleaner.perception.localization import HomographyMapper
mapper = HomographyMapper.from_correspondences(
    pixels=[[x1,y1],[x2,y2],[x3,y3],[x4,y4]],      # image coords you read off
    floor_xy=[[0,0],[4,0],[4,3],[0,3]],            # the matching floor meters
)
```

Both mappers expose the same `pixel_to_floor(u, v)` / `to_detection_point(u, v)`,
so the detector doesn't care which you use.

## Putting it together

```python
from roomcleaner.perception.camera import Webcam
from roomcleaner.perception.vision_detector import YoloWorldDetector
from roomcleaner.perception.localization import OverheadLinearMapper

cam = Webcam(index=0).open()
w, h = cam.resolution()
mapper = OverheadLinearMapper(4.0, 3.0, w, h)
detector = YoloWorldDetector(mapper)

frame = cam.read()
for d in detector.detect(frame):
    print(d.label, d.confidence, "at floor", d.position[:2])
```

`scripts/detect_webcam.py` is a ready-to-run version of exactly this.

## The full pipeline (detect → localize → plan)

`scripts/detect_and_plan.py` runs the whole software brain end to end and is the
best way to test everything **before hardware**:

```bash
python -m scripts.detect_and_plan --image floor.jpg   # a top-down phone photo
python -m scripts.detect_and_plan --webcam 0           # live, once the cam is up
```

It (1) loads a frame, (2) detects laundry, (3) maps each item to a floor (x, y),
(4) feeds them to the **same `Controller`** that drives the simulator and plans
the scan → nearest-first → grab → deliver order, and (5) writes two pictures to
`./output/`:
- `detected_image.png` — your frame with boxes, labels, and floor coordinates
- `detected_scene.png` — the 3D room showing the detected laundry + the plan

The glue is `perception/live.py::LiveDetector`, which snapshots one frame and
serves it to the planner as the current floor contents. Because the planner is
unchanged, the detections the camera produces are exactly what the real robot
will act on — the only thing that changes at hardware time is that motor commands
go to the winches instead of the simulator.

## Fixed overhead vs. camera-on-the-claw

- **Fixed overhead (recommended to start):** one camera sees the whole floor —
  simplest to calibrate and to scan. This is what the mappers above assume.
- **Camera on the claw:** great for a close-up *confirm before grabbing*, but its
  view moves, so localization must fold in the claw's known position.
- **Hybrid (best long-term):** a wide fixed camera to *find* laundry, the claw
  camera to *confirm* the grab. Add this once the fixed-camera path works.

## Accuracy tips

- A **wide-angle** lens near the ceiling of a small room may add barrel
  distortion; if positions near the edges look off, calibrate the camera
  (OpenCV `calibrateCamera`) and undistort before mapping.
- Re-run calibration whenever the camera moves.
- Cross-check: place an item at a known spot, run detection, confirm the reported
  `(x, y)` matches your tape measure before ever letting a motor move.
