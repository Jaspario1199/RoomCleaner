# Local bring-up log — software + camera milestone

Live progress record for bringing the RoomCleaner **software + live-camera**
milestone up on Jasper's Windows machine (the box with the innomaker USB
camera). Committed to the repo as work proceeds so anyone watching can follow
along. Scope is **only** the software + camera milestone — hardware bench
bring-up (`docs/FIRMWARE.md`) is a separate, later sequence and is not started
here.

- Date: 2026-08-12
- Machine: Windows 11, Python 3.11.4, CPU-only (no NVIDIA GPU)
- Branch: `claude/magical-cerf-gqr7j7`

## Status: software verified ✅ — only the live camera remains (needs the USB cam plugged in)

## Checklist

- [x] 1. Clone repo + read operating docs
- [x] 2. `python quickstart.py --vision` → tests green + install-verified line
      (see deviation #1 on the count; needed fix #2 to finish on Windows)
- [x] 3. `python -m scripts.demo_sim` → `output/run.gif` (+ scene/workspace PNGs)
- [x] 4. Detector smoke test (no camera) — `YoloWorldDetector.detect()` returned
      a list without raising. **This is the step that was blocked in the cloud;
      it works here** (see finding #3).
- [x] 5a. `detect_and_plan --image <photo>` — full detect→plan pipeline on a
      still photo, camera-free (see finding #4).
- [ ] 5b. `detect_webcam --camera N` — **live** detection. NEEDS the innomaker
      camera physically plugged in. → handed to Jasper.
- [ ] 5c. `detect_and_plan --webcam N` — live detection → cable plan. Completes
      the milestone.

## Verified environment

- torch `2.13.0+cpu` (CUDA disabled — the intended CPU wheel, 122 MB, not the
  multi-GB CUDA build), opencv `5.0.0`, ultralytics `8.4.118`.
- Tests: **29 passed, 2 skipped**. The 2 skips are `tests/test_claw_geometry.py`
  and `tests/test_winch_geometry.py`, skipped only because `cadquery` isn't
  installed — that's the CAD stack (`requirements-cad.txt`), out of this
  milestone's scope. Every software/vision test passes.

## Findings & deviations

1. **Test count vs the handoff.** The handoff expected `130 passed`; this repo
   actually collects **29 tests** (`pytest --collect-only` = 29). All 29 pass
   (+2 cadquery skips). Not a failure — just a documentation mismatch worth
   flagging. Nothing was cut on this machine.
2. **Fixed: `quickstart.py` crashed on Windows.** It printed a `✅` (U+2705) on
   success, but Windows stdout defaults to cp1252 and can't encode it →
   `UnicodeEncodeError` aborted setup *after* the tests already passed. Fixed by
   forcing UTF-8 stdout/stderr at startup (commit `959897f`). Setup now finishes
   cleanly with `✅ Install verified`.
3. **The cloud blocker is cleared on the home network.** First `detect()`
   downloaded the YOLO-World weights (`yolov8s-world.pt`, 25.9 MB, GitHub),
   auto-installed CLIP (`git+https://github.com/ultralytics/CLIP.git` → clip
   1.0), and downloaded CLIP `ViT-B/32` (338 MB) from
   `openaipublic.azureedge.net` — the URL the cloud egress proxy 403'd. It
   completed 100% and `detect()` returned a list. Note: the CLIP auto-install
   printed a "restart runtime" warning but did **not** actually require a
   restart here; the same process finished successfully.
4. **detect→plan proven camera-free.** `detect_and_plan --image bus.jpg
   --classes person clothing shirt backpack --conf 0.05` detected 5 people
   (conf 0.14–0.92), mapped each to a floor (x, y), and the same Controller that
   drives the simulator planned the pickups: 3 selected within the safe
   workspace → grabbed at floor coords → delivered to hamper → parked (2
   correctly excluded as out-of-workspace). Wrote `output/detected_image.png`
   (boxes + labels + floor coords) and `output/detected_scene.png`. These are
   **stand-in** detections to exercise the planner; real *laundry* detection
   quality is validated at the live-camera step. NB: on `zidane.jpg` at default
   conf 0.25 the model returned 0 detections — expected/fine per the handoff;
   lower `--conf` to see marginal hits.

## How to finish the milestone (live camera — Jasper)

1. Plug in the innomaker USB camera. Close anything that might hold it (Zoom/
   Teams/Camera app).
2. Activate the venv and try camera indexes:
   ```
   cd C:\Users\Jasper\Code\RoomCleaner
   venv\Scripts\activate
   python -m scripts.detect_webcam --camera 1     # try 0, 1, 2 until it's the USB cam
   ```
   A resolution line prints, then live detections when a shirt/sock is in view
   (conf ≥ ~0.4). Ctrl-C to stop.
3. Then the end-to-end live plan:
   ```
   python -m scripts.detect_and_plan --webcam 1   # same index that worked above
   ```
   Reminder: floor (x, y) uses placeholder `room_width`/`room_depth` from
   `roomcleaner/config.py` until the room is measured — detection is real, the
   coordinates are not yet calibrated.

## Log

- **2026-08-12** — Session start. Verified repo access (public, `gh` as
  `Jaspario1199`), Python 3.11.4, ~37 GB free. Cloned to
  `C:\Users\Jasper\Code\RoomCleaner`. Read `CLAUDE.md` (CAD contract — this
  milestone is out of its scope) + perception code.
- **2026-08-12** — Ran `quickstart.py --vision`: vision stack installed, tests
  ran (29 passed / 2 cadquery-skipped). Hit + fixed the Windows `✅` crash
  (commit `959897f`); re-ran quickstart → clean `✅ Install verified`.
- **2026-08-12** — `demo_sim` ran the full simulated mission (4 pickups →
  hamper → park); wrote `output/run.gif`.
- **2026-08-12** — Detector smoke test passed: YOLO-World + CLIP downloaded
  (incl. the azureedge CLIP model that was blocked in the cloud); `detect()`
  returned a list. `detect_and_plan --image` on a sample photo produced 5
  detections → 3-pickup plan; annotated outputs written. Software milestone
  verified. **Remaining: live camera (5b/5c), handed to Jasper.**
- **2026-08-12** — Live camera confirmed on the **innomaker (index 1**,
  `Innomaker-U20CAM-1080p-S1`, 1280×720): probed indices, ran the real detector
  loop live on it (clean), and grabbed snapshots. (Integrated webcam = index 0.)
- **2026-08-12** — Built the **live web app** (`docs/APP.md`): a browser
  dashboard (Flask) showing the annotated camera feed + detected-items panel +
  live sensitivity slider, with a reserved panel to grow into the full
  RoomCleaner console. `python -m scripts.live_app --camera 1` → http://localhost:8000.
  Verified end-to-end (camera capture thread, inference thread @~2 fps, MJPEG +
  `/snapshot.jpg` + `/api/state`). Test suite still green. New files only
  (`roomcleaner/webapp/`, `scripts/live_app.py`, `requirements-app.txt`,
  `docs/APP.md`); nothing in cad/firmware/contracts touched.
