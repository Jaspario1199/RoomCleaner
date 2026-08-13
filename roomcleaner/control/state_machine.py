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

        # Choose a cruise height that is (a) well below the ceiling, where a
        # cable robot has GOOD tension/stiffness -- near the ceiling the cables
        # go almost horizontal and can't hold the weight -- and (b) below the
        # fan's keep-out band so horizontal transits never enter the fan.
        default_cruise = 0.55 * robot.cfg.room_height
        fan = robot.cfg.fan
        if fan is not None and fan.enabled:
            default_cruise = min(default_cruise, fan.z_low - 0.15)
        self.cruise_z = cruise_z if cruise_z is not None else max(default_cruise, SAFE_MIN_Z + 0.4)

        # A safe, out-of-the-way parking pose (auto-computed, fan-aware).
        self.rest = robot.find_rest_position(prefer_xy=hamper_xy)

        self.state = State.IDLE
        self.position = self.rest.copy()
        self.target: Detection | None = None
        self.picked_up = 0
        self._log: list[str] = []

    def log(self, msg: str) -> None:
        self._log.append(f"[{self.state.name}] {msg}")

    @property
    def log_lines(self) -> list[str]:
        """Read-only copy of the decision log (for UIs and reports)."""
        return list(self._log)

    # ------------------------------------------------------------------
    # One full pickup cycle, as a list of structured ACTIONS.
    # ------------------------------------------------------------------
    def _plan_cycle(self) -> list[tuple] | None:
        """Advance one item; return a list of actions, or None when done.

        Actions are tuples the sim and the hardware both understand:
            ("move", path)   -- follow this (N,3) waypoint array
            ("grip", point)  -- close the gripper (at `point`)
            ("release", point) -- open the gripper (at `point`)
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

        # Geometry: transit above the item, descend, grip, lift, carry, release.
        approach_pt = _above(self.target, SAFE_MIN_Z)
        grab_pt = _above(self.target, GRAB_Z)
        path_to_item = safe_transit(self.position, approach_pt, self.cruise_z)
        descent = safe_transit(approach_pt, grab_pt, cruise_z=SAFE_MIN_Z)
        lift = safe_transit(grab_pt, approach_pt, cruise_z=self.cruise_z)
        to_hamper = safe_transit(approach_pt, self.hamper, self.cruise_z)

        self.state = State.GRAB
        self.log(f"Grabbing at {grab_pt.round(2)}.")
        self.detector.remove(self.target) if hasattr(self.detector, "remove") else None
        self.picked_up += 1
        self.state = State.DELIVER
        self.log(f"Delivered to hamper. Total: {self.picked_up}.")
        self.position = self.hamper.copy()

        return [
            ("move", path_to_item),
            ("move", descent),
            ("grip", grab_pt),
            ("move", lift),
            ("move", to_hamper),
            ("release", self.hamper.copy()),
        ]

    def plan_next_cycle(self) -> np.ndarray | None:
        """Advance one item; return the concatenated (N,3) path (for the sim)."""
        actions = self._plan_cycle()
        if actions is None:
            return None
        moves = [payload for kind, payload in actions if kind == "move"]
        return np.vstack(moves)

    def run(self, max_items: int = 20, return_to_rest: bool = True) -> list[np.ndarray]:
        """Run cycles until the floor is clear; return the list of paths taken.

        When done, the effector transits back to its safe parking pose so it
        sits out of the way (and clear of the fan) between jobs.
        """
        paths = []
        for _ in range(max_items):
            path = self.plan_next_cycle()
            if path is None:
                break
            paths.append(path)
        if return_to_rest and np.linalg.norm(self.position - self.rest) > 1e-3:
            self.state = State.IDLE
            park = safe_transit(self.position, self.rest, self.cruise_z)
            self.position = self.rest.copy()
            self.log(f"Parked at rest pose {self.rest.round(2)}.")
            paths.append(park)
        return paths

    def iter_actions(self, max_items: int = 20, return_to_rest: bool = True):
        """Yield every action across the whole run -- what HARDWARE executes.

        Same plan as run(), but as a stream of ("move"|"grip"|"release", payload)
        so a hardware backend can move the winches and work the gripper in order.
        """
        for _ in range(max_items):
            actions = self._plan_cycle()
            if actions is None:
                break
            yield from actions
        if return_to_rest and np.linalg.norm(self.position - self.rest) > 1e-3:
            self.state = State.IDLE
            park = safe_transit(self.position, self.rest, self.cruise_z)
            self.position = self.rest.copy()
            self.log(f"Parked at rest pose {self.rest.round(2)}.")
            yield ("move", park)


def _above(detection: Detection, z: float) -> np.ndarray:
    """A point directly above a detection at height z."""
    return np.array([detection.position[0], detection.position[1], z])
