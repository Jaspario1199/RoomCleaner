# Handoff: finish the "software + camera" milestone on the user's machine

**Audience:** an agent running with local machine access (or a network policy
that permits `openaipublic.azureedge.net`) on Jasper's computer, with the
innomaker USB camera physically present.
**Scope:** ONLY the software + live-camera milestone. Hardware bring-up
(steppers, Vref, switches) is a separate, later sequence in
`docs/FIRMWARE.md` — do not start it under this handoff.

## Project context (one paragraph)

RoomCleaner is a ceiling-mounted 4-cable robot that finds laundry with an
overhead camera and YOLO-World open-vocabulary detection, flies a tendon-driven
claw to it, and drops it in a hamper. Repo:
`github.com/Jaspario1199/RoomCleaner`, branch `claude/magical-cerf-gqr7j7`
(the default; all work lives here). `CLAUDE.md` is the operating contract —
read it before changing anything beyond this milestone's scope.

## What is already verified (do not redo)

- 130/130 pytest in a clean cloud container AND via `quickstart.py` in a
  fresh clone (venv creation → installs → self-test all green).
- `python -m scripts.demo_sim` runs the full simulated mission (4 pickups,
  hamper drops, rest park; outputs in `./output/`).
- Vision stack installs cleanly (`requirements-vision.txt`); YOLO-World
  weights (`yolov8s-world.pt`, ~26 MB) download fine from GitHub releases.
- **Known blocker hit in the cloud (the reason for this handoff):** on first
  `detect()`, ultralytics' YOLO-World `set_classes()` builds text embeddings
  with CLIP `ViT-B/32`, downloaded from `openaipublic.azureedge.net` (and it
  auto-installs `git+https://github.com/ultralytics/CLIP.git` on first run —
  after that auto-install, the process must be restarted once). The cloud
  session's egress proxy 403'd the azureedge URL. A normal home network is
  fine.

## Your task list

1. Clone the repo; `python quickstart.py --vision` (Python 3.10+). It creates
   `./venv`, installs core + vision, runs the test suite. Expect several GB
   (torch). Checkpoint: `130 passed` and the ✅ line.
2. Run `python -m scripts.demo_sim` (venv active) — sanity, and gives the user
   `output/run.gif` to look at.
3. Smoke-test the detector WITHOUT the camera first (isolates model downloads
   from camera problems): run a `YoloWorldDetector.detect()` on any indoor
   photo (see `roomcleaner/perception/vision_detector.py` docstring; classes
   are laundry words). First call downloads CLIP; if the process complains
   about the CLIP auto-install, rerun once. Checkpoint: returns a list without
   raising (detections on a non-laundry photo may be empty or "clothing" hits
   on people — both fine).
4. Plug in the innomaker camera (bare-board UVC, driverless). Find its index:
   built-in laptop cam is usually 0, innomaker 1. `python -m
   scripts.detect_webcam --camera 1` (or 0/2). Checkpoint: resolution line
   prints, then live detections when a shirt/sock is in view with conf ≥ ~0.4.
5. Run `python -m scripts.detect_and_plan` — camera detection feeding the
   winch planner; it prints the cable-length plan for the top detection.
   That completes the milestone.
6. Report results back to the user in plain language: what ran, sample
   detection lines, and any deviations.

## Gotchas already discovered

- `detect_webcam.py` takes `--camera N` (added for exactly this bring-up).
- Floor (x, y) coordinates use placeholder room dimensions from
  `roomcleaner/config.py` (`room_width`, `room_depth`) until the user measures
  the room — detection quality is real, coordinates are not yet.
- Torch install: use the default CPU wheel; do NOT chase CUDA unless the
  machine obviously has an NVIDIA GPU. CPU inference at ~1–2 fps is fully
  adequate (the detector loop sleeps 0.2 s between frames anyway).
- Windows: activate venv with `venv\Scripts\activate`; quickstart handles
  venv paths itself.
- If OpenCV opens the wrong device or a black frame, close any app using the
  camera (Zoom/Teams hold it), then re-try index hunting.

## Boundaries

- Do not modify `cad/`, `firmware/`, contracts (`cad/interfaces.py`,
  `cad/params.py`), or the source-of-truth docs (`REQUIREMENTS.md`,
  `DECISIONS.md`) — all verified under the CAD workflow in `CLAUDE.md`.
- Small fixes needed to complete THIS milestone (e.g., a camera-index quirk,
  an import guard) are fine: commit with a clear message and push to
  `claude/magical-cerf-gqr7j7`.
- If something fails outside this scope, record it in `DESIGN_STATE.md` under
  a "local bring-up findings" heading and stop rather than improvising.

## After this milestone (context only — not yours)

Hardware bench sequence is staged in `docs/FIRMWARE.md` (first-power
checklist: Vref 0.8 V on the A4988s, single-motor test, `S` switch test).
Pending user measurements that gate two prints: servo round-disc horn
(→ `HORN_POCKET_DIA`, tendon drum) and motor shaft across-flat sanity check
(spool). Parts still unordered are tracked in `docs/SHOPPING_LIST.md`.
