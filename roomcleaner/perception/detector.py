"""
Perception interface (Phase 1 lives here).

For Phase 0 we only define the CONTRACT the rest of the system codes against,
plus a fake detector that invents laundry so the simulator has something to
chase. When we build the real vision model, we implement the same interface and
nothing downstream has to change.

The real Phase 1 plan:
    * A camera (or two) sees the floor.
    * An object-detection model (YOLO-class) finds laundry and returns 2D boxes.
    * We convert each 2D detection to a 3D floor position -- easiest if the
      camera is fixed and calibrated, so a pixel maps to a known floor point
      (a homography). With a camera ON the moving effector, we also fold in the
      effector's known position.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass
class Detection:
    """One detected laundry item."""

    position: np.ndarray      # (x, y, z) on the floor, meters, world frame
    label: str                # e.g. "sock", "shirt", "towel"
    confidence: float         # 0..1
    area: float = 0.0         # rough footprint in m^2 (helps pick a grab strategy)


class Detector:
    """Base class -- real and simulated detectors share this interface."""

    def detect(self, frame=None) -> list[Detection]:
        raise NotImplementedError


class SimulatedDetector(Detector):
    """Scatters a few fake laundry items on the floor for the simulator.

    Deterministic given a seed so runs are reproducible.
    """

    LABELS = ["sock", "shirt", "towel", "sock", "pants"]

    def __init__(self, config, n_items: int = 4, seed: int = 7):
        self.cfg = config
        self.rng = np.random.default_rng(seed)
        margin = 0.4
        self._items: list[Detection] = []
        for _ in range(n_items):
            x = self.rng.uniform(margin, config.room_width - margin)
            y = self.rng.uniform(margin, config.room_depth - margin)
            label = self.LABELS[self.rng.integers(len(self.LABELS))]
            self._items.append(
                Detection(
                    position=np.array([x, y, 0.0]),
                    label=label,
                    confidence=float(self.rng.uniform(0.75, 0.99)),
                    area=float(self.rng.uniform(0.02, 0.15)),
                )
            )

    def detect(self, frame=None) -> list[Detection]:
        """Return the laundry still on the floor."""
        return list(self._items)

    def remove(self, detection: Detection) -> None:
        """Simulate a successful pickup -- the item is gone from the floor."""
        self._items = [d for d in self._items if d is not detection]
