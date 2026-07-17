"""
Live perception: snapshot the floor with a camera and feed the results to the
control loop.

The control loop (`control.state_machine.Controller`) expects a Detector whose
`detect()` returns the items currently on the floor and whose `remove()` marks
one as picked up. The real vision detector (`YoloWorldDetector`) instead needs a
camera *frame* each call. `LiveDetector` bridges the two:

    1. `snapshot(frame)` runs the vision model on one frame and caches the result
       (a "look at the floor" moment).
    2. `detect()` then returns that cached snapshot, so the planner can walk the
       list picking items off one at a time -- exactly like the simulator.

With real hardware you'd re-`snapshot()` after each pickup (the camera confirms
the item is gone). For planning and for testing on a still image, one snapshot of
everything on the floor is the right model.
"""

from __future__ import annotations

from .detector import Detector, Detection


class LiveDetector(Detector):
    """Adapts a frame-based vision detector + camera to the Detector interface."""

    def __init__(self, vision_detector, camera=None):
        self.vision = vision_detector      # e.g. YoloWorldDetector (returns floor Detections)
        self.camera = camera               # Webcam, or None if you pass frames directly
        self._items: list[Detection] = []
        self.last_frame = None

    def snapshot(self, frame=None) -> list[Detection]:
        """Grab one frame (from `frame` or the camera), detect, and cache."""
        if frame is None:
            if self.camera is None:
                raise ValueError("LiveDetector needs a camera or an explicit frame.")
            frame = self.camera.read()
        self.last_frame = frame
        self._items = self.vision.detect(frame)
        return self._items

    # -- Detector interface --------------------------------------------------
    def detect(self, frame=None) -> list[Detection]:
        if frame is not None:
            return self.snapshot(frame)
        return list(self._items)

    def remove(self, detection: Detection) -> None:
        self._items = [d for d in self._items if d is not detection]
