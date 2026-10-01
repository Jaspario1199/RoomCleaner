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
from ..hardware.hw_config import TRAVEL_SPEED_M_S, PICKUP_SPEED_M_S


class State(Enum):
    IDLE = auto()
    SCAN = auto()
    SELECT = auto()
    APPROACH = auto()
    GRAB = auto()
    DELIVER = auto()
    VERIFY_PICKUP = auto()
    VERIFY_DELIVERY = auto()
    FAULT = auto()
    DONE = auto()


class Controller:
    """Drives the robot through the cleaning cycle, one item at a time."""

    def __init__(
        self,
        robot: CableRobot,
        detector: Detector,
        hamper_xy: tuple[float, float],
        cruise_z: float | None = None,
        verifier=None, max_grab_attempts: int = 3, probe_distance_m: float = 0.20,
    ):
        if max_grab_attempts < 1 or probe_distance_m <= 0:
            raise ValueError("Invalid retry/probe configuration")
        self.verifier = verifier
        self.max_grab_attempts = max_grab_attempts
        self.probe_distance_m = probe_distance_m
        self.motion_speed_m_s = 0.02
        self._preview_seen = set()
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
        """Preview one item without claiming execution; None when no targets remain.

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
        reachable = [d for d in items if id(d) not in self._preview_seen
                     and self.robot.is_reachable(_above(d, SAFE_MIN_Z))]
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

        # Preview only: no delivery count, detector removal or physical pose update.
        self._preview_seen.add(id(self.target))

        return [
            ("move", path_to_item),
            ("move", descent),
            ("grip", grab_pt),
            ("move", lift),
            ("move", to_hamper),
            ("release", self.hamper.copy()),
        ]

    def plan_next_cycle(self) -> np.ndarray | None:
        """Preview one item as an (N,3) path; no physical success side effects."""
        actions = self._plan_cycle()
        if actions is None:
            return None
        moves = [payload for kind, payload in actions if kind == "move"]
        return np.vstack(moves)

    def run(self, max_items: int = 20, return_to_rest: bool = True) -> list[np.ndarray]:
        """Simulate explicitly, or preview live detections without claiming delivery."""
        from ..perception.detector import SimulatedDetector
        if isinstance(self.detector, SimulatedDetector):
            return [p for k, p in self.iter_actions(max_items, return_to_rest) if k == "move"]
        paths = []
        for _ in range(max_items):
            path = self.plan_next_cycle()
            if path is None:
                break
            paths.append(path)
        return paths

    def iter_actions(self, max_items: int = 20, return_to_rest: bool = True):
        """Resume after each acknowledged action; verify before advancing a cycle.

        Consumers MUST execute each action successfully before requesting the next.
        Camera failures/ambiguity stop the mission; previews never call this path.
        """
        from ..perception.verification import SimulatedVerifier, VerificationError
        from ..perception.detector import SimulatedDetector
        if self.verifier is None:
            if isinstance(self.detector, SimulatedDetector):
                self.verifier = SimulatedVerifier()
            else:
                raise VerificationError("Live execution requires a camera verifier")
        self._preview_seen.clear()

        def move(goal, cruise, speed):
            self.motion_speed_m_s = speed
            floor = min(SAFE_MIN_Z, GRAB_Z) if (goal[2] <= GRAB_Z+1e-9 or self.position[2] <= GRAB_Z+1e-9) else SAFE_MIN_Z
            path = None
            # A fan-aware endpoint does not imply its higher cruise leg is safe.
            # Try progressively lower transit heights; never waive cable/tension checks.
            for height in np.linspace(cruise, max(min(goal[2], self.position[2]), SAFE_MIN_Z), 12):
                candidate = safe_transit(self.position, goal, height)
                if all(self.robot.is_reachable(p, min_z=floor) for p in candidate):
                    path = candidate
                    break
            if path is None:
                raise VerificationError("No safe transit through configured cable/fan/tension workspace")
            yield ("move", path)
            self.position = np.asarray(goal).copy()

        try:
            for _ in range(max_items):
                self.state = State.SCAN
                items = self.detector.detect()
                reachable = [d for d in items if self.robot.is_reachable(_above(d, SAFE_MIN_Z))]
                if not reachable:
                    self.state = State.DONE
                    break
                self.target = min(reachable, key=lambda d: np.linalg.norm(d.position[:2]-self.position[:2]))
                target = self.target
                approach = _above(target, max(SAFE_MIN_Z, GRAB_Z + 0.10))
                grab = _above(target, GRAB_Z)
                delta = self.hamper[:2] - approach[:2]
                distance = np.linalg.norm(delta)
                if distance < 0.05:
                    raise VerificationError("Target too close to hamper for a visible pickup probe")
                probe = np.array([*(approach[:2] + delta/distance*min(self.probe_distance_m, distance/2)), max(approach[2], 0.45)])
                for attempt in range(self.max_grab_attempts):
                    self.state = State.APPROACH
                    yield from move(approach, self.cruise_z, TRAVEL_SPEED_M_S)
                    yield from move(grab, SAFE_MIN_Z, PICKUP_SPEED_M_S)
                    self.verifier.before_pickup(target)
                    self.state = State.GRAB
                    yield ("grip", grab.copy())
                    yield from move(probe, self.cruise_z, PICKUP_SPEED_M_S)
                    self.state = State.VERIFY_PICKUP
                    if self.verifier.verify_pickup(target, probe):
                        self.log("Camera confirmed payload movement.")
                        break
                    self.log(f"Pickup unconfirmed; attempt {attempt+1}/{self.max_grab_attempts}.")
                    # Return to the original pickup before opening a possibly-held item.
                    yield from move(grab, self.cruise_z, PICKUP_SPEED_M_S)
                    yield ("release", grab.copy())
                    if not self.verifier.retry_target_present(target):
                        raise VerificationError("Target lost/occluded; cannot safely retry its old location")
                else:
                    raise VerificationError("Pickup retry limit reached")
                self.state = State.DELIVER
                yield from move(self.hamper, self.cruise_z, TRAVEL_SPEED_M_S)
                self.verifier.before_release(target)
                yield ("release", self.hamper.copy())
                retreat = probe.copy()
                if hasattr(self.verifier, "validate_retreat"):
                    self.verifier.validate_retreat(retreat)
                yield from move(retreat, self.cruise_z, PICKUP_SPEED_M_S)
                self.state = State.VERIFY_DELIVERY
                if not self.verifier.verify_delivery(target, self.hamper):
                    raise VerificationError("Camera could not confirm payload released into hamper")
                self.picked_up += 1
                if hasattr(self.detector, "remove"):
                    self.detector.remove(target)
                self.log(f"Camera verified delivery. Total: {self.picked_up}.")
            if return_to_rest and np.linalg.norm(self.position-self.rest) > 1e-3:
                self.state = State.IDLE
                yield from move(self.rest, self.cruise_z, TRAVEL_SPEED_M_S)
        except Exception:
            self.state = State.FAULT
            self.log("Mission stopped; delivery count unchanged for unverified item.")
            raise


def _above(detection: Detection, z: float) -> np.ndarray:
    """A point directly above a detection at height z."""
    return np.array([detection.position[0], detection.position[1], z])
