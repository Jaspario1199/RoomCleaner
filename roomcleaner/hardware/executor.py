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


def run_on_hardware(robot, controller, driver, *, home: bool = True,
                    step_m: float = MOVE_STEP_M):
    """Execute the controller's full plan on hardware via `driver`.

    `driver` is an opened Driver (SerialDriver in production, MockDriver in tests).
    Returns the number of (move/grip/release) actions executed.
    """
    if home:
        driver.home()
    count = 0
    for kind, payload in controller.iter_actions():
        if kind == "move":
            for wp in subsample_path(payload, step_m):
                driver.move_to_point(wp)
        elif kind == "grip":
            driver.grip()
        elif kind == "release":
            driver.release()
        count += 1
    return count
