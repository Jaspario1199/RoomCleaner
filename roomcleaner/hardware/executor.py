"""
Run a planned pickup on real hardware.

Consumes the SAME action stream the simulator uses (`Controller.iter_actions`)
and translates it to winch moves + gripper commands through a Driver. Dense
trajectory waypoints are subsampled to ~MOVE_STEP_M apart, since the Arduino
interpolates smoothly between step targets -- we only need the shape, not every
50 Hz point.
"""

from __future__ import annotations

import numpy as np

from .hw_config import MOVE_STEP_M


def subsample_path(path: np.ndarray, step_m: float = MOVE_STEP_M) -> np.ndarray:
    """Keep waypoints roughly `step_m` apart, always including the last point."""
    path = np.asarray(path, dtype=float)
    if len(path) <= 2:
        return path
    kept = [path[0]]
    for p in path[1:]:
        if np.linalg.norm(p - kept[-1]) >= step_m:
            kept.append(p)
    if not np.allclose(kept[-1], path[-1]):
        kept.append(path[-1])
    return np.array(kept)


def run_on_hardware(robot, controller, driver, gripper=None, *,
                    home: bool = True, step_m: float = MOVE_STEP_M):
    """Execute the controller's full plan on hardware.

    `driver`  drives the winch motors (SerialDriver in production, MockDriver in
              tests) -- home() + move_to_point().
    `gripper` works the claw. Pass a WiFiGripper for the wireless effector; if
              None, the gripper falls back to the motor driver's own G command
              (the wired-servo setup). MockGripper for tests.

    Returns the number of (move/grip/release) actions executed.
    """
    grip_target = gripper if gripper is not None else driver
    if home:
        driver.home()
    count = 0
    for kind, payload in controller.iter_actions():
        if kind == "move":
            for wp in subsample_path(payload, step_m):
                driver.move_to_point(wp)
        elif kind == "grip":
            grip_target.grip()
        elif kind == "release":
            grip_target.release()
        count += 1
    return count
