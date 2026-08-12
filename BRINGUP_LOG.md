# Local bring-up log — software + camera milestone

Live progress record for bringing the RoomCleaner **software + live-camera**
milestone up on Jasper's Windows machine (the box with the innomaker USB
camera). Committed to the repo as work proceeds so anyone watching can follow
along. Scope is **only** the software + camera milestone — hardware bench
bring-up (`docs/FIRMWARE.md`) is a separate, later sequence and is not started
here.

- Date started: 2026-08-12
- Machine: Windows 11, Python 3.11.4, CPU-only (no NVIDIA GPU) — CPU torch wheel
- Branch: `claude/magical-cerf-gqr7j7`
- Reference: the "software + camera" handoff (clone → quickstart --vision →
  demo_sim → detector smoke test → camera bring-up)

## Checklist

- [ ] 1. Clone repo + read operating docs
- [ ] 2. `python quickstart.py --vision` → **130 passed** + install-verified line
- [ ] 3. `python -m scripts.demo_sim` → `output/run.gif`
- [ ] 4. Detector smoke test (no camera) — `YoloWorldDetector.detect()` returns a
       list without raising (first call downloads CLIP `ViT-B/32`; may need one
       rerun after the CLIP auto-install)
- [ ] 5a. `detect_and_plan --image <photo>` — full detect→plan pipeline on a
       still photo (camera-free proof of the planner path)
- [ ] 5b. `detect_webcam --camera N` — **live** detection (needs the innomaker
       camera physically plugged in; hand-off point to Jasper)
- [ ] 5c. `detect_and_plan --webcam N` — live detection → cable-length plan
       (completes the milestone)

## Log

- **2026-08-12** — Session start. Verified repo access (public, `gh` as
  `Jaspario1199`), Python 3.11.4, ~37 GB free disk. Cloned to
  `C:\Users\Jasper\Code\RoomCleaner`. Read `CLAUDE.md` (CAD contract — this
  milestone is out of its scope), `quickstart.py`, and the perception code
  (`vision_detector.py`, `detect_webcam.py`, `detect_and_plan.py`). Kicked off
  `python quickstart.py --vision` (core deps installing; torch/ultralytics
  next). Created this log.
