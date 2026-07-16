"""
Live laundry detection from a webcam (Phase 1).

    python -m scripts.detect_webcam

Prereqs (on the machine with the camera):
    pip install -r requirements-vision.txt

It opens your default camera, runs open-vocabulary laundry detection on each
frame, maps every detection to a floor (x, y) coordinate using your room
dimensions from config.py, and prints them. Press Ctrl-C to stop.

This is the perception half of the robot -- it produces exactly the Detections
the control loop consumes, so wiring it to the real robot is just handing these
to a Controller instead of the SimulatedDetector.

NOTE: uses OverheadLinearMapper (zero-calibration) -- correct for a centered,
straight-down ceiling camera. For a tilted camera, switch to a HomographyMapper
(see docs/VISION.md).
"""

from __future__ import annotations

import time

from roomcleaner.config import DEFAULT_CONFIG
from roomcleaner.perception.camera import Webcam
from roomcleaner.perception.localization import OverheadLinearMapper
from roomcleaner.perception.vision_detector import YoloWorldDetector


def main() -> None:
    cfg = DEFAULT_CONFIG
    cam = Webcam(index=0).open()
    w, h = cam.resolution()
    print(f"camera resolution: {w}x{h}")

    mapper = OverheadLinearMapper(cfg.room_width, cfg.room_depth, w, h)
    detector = YoloWorldDetector(mapper)

    print("Detecting laundry. Ctrl-C to stop.\n")
    try:
        while True:
            frame = cam.read()
            dets = detector.detect(frame)
            if dets:
                print(f"--- {len(dets)} item(s) ---")
                for d in dets:
                    x, y = d.position[0], d.position[1]
                    print(f"  {d.label:10s} conf={d.confidence:.2f} "
                          f"floor=({x:.2f}, {y:.2f}) m  area~{d.area:.3f} m^2")
            else:
                print("  (nothing detected)")
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nstopping.")
    finally:
        cam.release()


if __name__ == "__main__":
    main()
