"""
Tests for the live perception -> planning wiring, using a MOCK vision detector
so no heavy model (ultralytics/torch) is needed. This proves the camera-frame ->
detection -> floor-coords -> Controller path is sound end to end.
"""

import numpy as np

from roomcleaner.config import DEFAULT_CONFIG
from roomcleaner.kinematics import CableRobot
from roomcleaner.perception.detector import Detector, Detection
from roomcleaner.perception.localization import OverheadLinearMapper
from roomcleaner.perception.live import LiveDetector
from roomcleaner.control.state_machine import Controller


class MockVision(Detector):
    """Stands in for YoloWorldDetector: turns fake pixel boxes into floor Detections."""

    def __init__(self, mapper, boxes):
        self.mapper = mapper
        self.boxes = boxes  # list of (label, conf, (x1,y1,x2,y2))

    def detect(self, frame=None):
        out = []
        for label, conf, (x1, y1, x2, y2) in self.boxes:
            u, v = 0.5 * (x1 + x2), y2
            pos = self.mapper.to_detection_point(u, v)
            out.append(Detection(pos, label, conf, bbox=(x1, y1, x2, y2)))
        return out


def _setup():
    cfg = DEFAULT_CONFIG
    mapper = OverheadLinearMapper(cfg.room_width, cfg.room_depth, 1000, 600)
    boxes = [
        ("sock", 0.9, (450, 250, 550, 350)),    # near center -> reachable
        ("shirt", 0.8, (200, 150, 400, 300)),
    ]
    vision = MockVision(mapper, boxes)
    return cfg, mapper, LiveDetector(vision)


def test_snapshot_maps_boxes_to_floor():
    cfg, mapper, live = _setup()
    frame = np.zeros((600, 1000, 3), dtype=np.uint8)
    items = live.snapshot(frame)
    assert len(items) == 2
    # Center box (~500,350 px) maps to ~ (2.0, 1.75) m in a 4x3 room.
    sock = next(d for d in items if d.label == "sock")
    assert np.allclose(sock.position[:2], [2.0, 1.75], atol=0.1)
    assert sock.position[2] == 0.0
    assert sock.bbox is not None


def test_detect_returns_cached_and_remove_works():
    cfg, mapper, live = _setup()
    live.snapshot(np.zeros((600, 1000, 3), dtype=np.uint8))
    items = live.detect()
    assert len(items) == 2
    live.remove(items[0])
    assert len(live.detect()) == 1


def test_controller_plans_from_live_detections():
    cfg, mapper, live = _setup()
    live.snapshot(np.zeros((600, 1000, 3), dtype=np.uint8))
    robot = CableRobot(cfg)
    controller = Controller(robot, live, hamper_xy=(cfg.room_width - 0.5, 0.5))
    paths = controller.run()
    # Both reachable items should be planned and picked up.
    assert controller.picked_up >= 1
    assert all(p.shape[1] == 3 for p in paths)   # each path is (N,3) waypoints
