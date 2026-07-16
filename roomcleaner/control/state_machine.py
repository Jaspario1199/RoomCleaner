"""
The brain: a state machine that runs the scan -> detect -> grab -> drop loop.

States:

    IDLE     -> waiting to start
    SCAN     -> ask the detector what's on the floor
    SELECT   -> choose the next item (nearest first) and plan a path to it
    APPROACH -> fly to a point above the item at cruise height
    GRAB     -> descend, engage the end-effector, confirm we have the item
    DELIVER  -> fly to the hamper and release
    DONE     -> nothing left on the floor

Keeping the control logic as an explicit state machine (rather than tangled
if-statements) makes it easy to reason about safety and to add states later
(e.g. RECOVER if a grab fails).
"""

from __future__ import annotations

from enum import Enum, auto
import numpy as np

from ..kinematics import CableRobot
from ..perception.detector import Detector, Detection
from .trajectory import safe_transit
from ..config import GRAB_Z, SAFE_MIN_Z


class State(Enum):
    IDLE = auto()
    SCAN = auto()
    SELECT = auto()
    APPROACH = auto()
    GRAB = auto()
    DELIVER = auto()
    DONE = auto()


class Controller:
    """Drives the robot through the cleaning cycle, one item at a time."""

    def __init__(
        self,
        robot: CableRobot,
        detector: Detector,
        hamper_xy: tuple[float, float],
        cruise_z: float | None = None,
    ):
        self.robot = robot
        self.detector = detector
        self.hamper = np.array([hamper_xy[0], hamper_xy[1], SAFE_MIN_Z + 0.3])
        self.cruise_z = cruise_z if cruise_z is not None else robot.cfg.room_height - 0.6

        self.state = State.IDLE
        self.position = np.array(
            [robot.cfg.room_width / 2, robot.cfg.room_depth / 2, self.cruise_z]
        )
        self.target: Detection | None = None
        self.picked_up = 0
        self._log: list[str] = []

    def log(self, msg: str) -> None:
        self._log.append(f"[{self.state.name}] {msg}")

    # ------------------------------------------------------------------
    # One full pickup cycle, yielding the path so a simulator can animate it.
    # ------------------------------------------------------------------
    def plan_next_cycle(self) -> np.ndarray | None:
        """Advance the state machine by one item and return the path to follow.

        Returns an (N, 3) waypoint array for the move, or None when done.
        """
        self.state = State.SCAN
        items = self.detector.detect()
        if not items:
            self.state = State.DONE
            self.log("Floor is clear.")
            return None

        # SELECT: nearest reachable item first.
        self.state = State.SELECT
        reachable = [d for d in items if self.robot.is_reachable(_above(d, SAFE_MIN_Z))]
        if not reachable:
            self.state = State.DONE
            self.log("Remaining items are outside the safe workspace.")
            return None
        self.target = min(
            reachable, key=lambda d: np.linalg.norm(d.position[:2] - self.position[:2])
        )
        self.log(f"Selected {self.target.label} (conf {self.target.confidence:.2f}).")

        # APPROACH + GRAB: transit to a point above the item, then descend.
        approach_pt = _above(self.target, SAFE_MIN_Z)
        grab_pt = _above(self.target, GRAB_Z)
        path_to_item = safe_transit(self.position, approach_pt, self.cruise_z)
        descent = safe_transit(approach_pt, grab_pt, cruise_z=SAFE_MIN_Z)

        self.state = State.GRAB
        self.log(f"Grabbing at {grab_pt.round(2)}.")

        # DELIVER: lift and carry to the hamper, then release.
        lift = safe_transit(grab_pt, approach_pt, cruise_z=self.cruise_z)
        to_hamper = safe_transit(approach_pt, self.hamper, self.cruise_z)

        self.state = State.DELIVER
        self.detector.remove(self.target) if hasattr(self.detector, "remove") else None
        self.picked_up += 1
        self.log(f"Delivered to hamper. Total: {self.picked_up}.")

        self.position = self.hamper.copy()
        return np.vstack([path_to_item, descent, lift, to_hamper])

    def run(self, max_items: int = 20) -> list[np.ndarray]:
        """Run cycles until the floor is clear; return the list of paths taken."""
        paths = []
        for _ in range(max_items):
            path = self.plan_next_cycle()
            if path is None:
                break
            paths.append(path)
        return paths


def _above(detection: Detection, z: float) -> np.ndarray:
    """A point directly above a detection at height z."""
    return np.array([detection.position[0], detection.position[1], z])
