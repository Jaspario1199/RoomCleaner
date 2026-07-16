"""
The real laundry detector (Phase 1).

It wraps an OPEN-VOCABULARY object detector so it recognizes laundry out of the
box with NO training: you give it text class names ("sock", "t-shirt", "towel",
...) and it finds them. We use Ultralytics YOLO-World, which supports exactly
this "detect these words" mode.

Design:
  * Implements the SAME `Detector` interface as the simulated one, so the
    control loop is unchanged -- swap this in and the robot just works.
  * Each 2D detection box is turned into a floor (x, y) point via a FloorMapper
    (see localization.py), using the BOTTOM-CENTER of the box (where the item
    meets the floor) for a better position estimate.
  * Heavy deps (ultralytics/torch) are imported lazily with a clear message, so
    importing this module never forces the big install until you actually run it.

Install on your machine:
    pip install ultralytics opencv-python
The first run downloads the YOLO-World weights automatically.
"""

from __future__ import annotations

import numpy as np

from .detector import Detector, Detection
from .localization import FloorMapper


# Default laundry vocabulary. Edit freely -- the model detects whatever words
# you give it. Keep them concrete; open-vocab models like specific nouns.
DEFAULT_LAUNDRY_CLASSES = [
    "sock",
    "t-shirt",
    "shirt",
    "towel",
    "pants",
    "jeans",
    "underwear",
    "hoodie",
    "shorts",
    "clothing",
]


class YoloWorldDetector(Detector):
    """Open-vocabulary laundry detector backed by Ultralytics YOLO-World."""

    def __init__(
        self,
        mapper: FloorMapper,
        classes: list[str] | None = None,
        model_name: str = "yolov8s-world.pt",
        confidence: float = 0.25,
    ):
        self.mapper = mapper
        self.classes = classes or list(DEFAULT_LAUNDRY_CLASSES)
        self.confidence = confidence
        self.model_name = model_name
        self._model = None  # lazy

    # -- model loading ---------------------------------------------------
    def _ensure_model(self):
        if self._model is not None:
            return
        try:
            from ultralytics import YOLO
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ImportError(
                "The real detector needs Ultralytics. Install it with:\n"
                "    pip install ultralytics opencv-python\n"
                "Until then, use SimulatedDetector for development."
            ) from exc
        model = YOLO(self.model_name)
        # Tell the open-vocabulary model which words to look for.
        if hasattr(model, "set_classes"):
            model.set_classes(self.classes)
        self._model = model

    # -- the Detector interface -----------------------------------------
    def detect(self, frame=None) -> list[Detection]:
        """Detect laundry in a camera `frame` (an HxWx3 BGR/RGB numpy array).

        Returns Detections with floor positions in world coordinates.
        """
        if frame is None:
            raise ValueError("YoloWorldDetector.detect needs a camera frame.")
        self._ensure_model()

        results = self._model.predict(
            frame, conf=self.confidence, verbose=False
        )
        detections: list[Detection] = []
        for res in results:
            boxes = getattr(res, "boxes", None)
            if boxes is None:
                continue
            names = res.names if hasattr(res, "names") else {}
            for box in boxes:
                xyxy = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                label = names.get(cls_id, str(cls_id)) if names else str(cls_id)
                detections.append(self._box_to_detection(xyxy, conf, label))
        return detections

    def _box_to_detection(self, xyxy, conf, label) -> Detection:
        x1, y1, x2, y2 = xyxy
        # Bottom-center of the box: where the item contacts the floor.
        u = 0.5 * (x1 + x2)
        v = y2
        pos = self.mapper.to_detection_point(u, v)
        # Rough footprint from the box, mapped through two corners.
        p_tl = self.mapper.pixel_to_floor(x1, y1)
        p_br = self.mapper.pixel_to_floor(x2, y2)
        area = float(abs(p_br[0] - p_tl[0]) * abs(p_br[1] - p_tl[1]))
        return Detection(position=pos, label=str(label), confidence=conf, area=area)
