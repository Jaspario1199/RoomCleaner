"""
Run a planned pickup on real hardware.

Consumes the SAME action stream the simulator uses (`Controller.iter_actions`)
and translates it to winch moves + gripper commands through a Driver. Dense
trajectory waypoints are subsampled to ~MOVE_STEP_M apart, since the Arduino
ramps each segment between step targets -- we only need the shape, not every
50 Hz point. Waypoint timing is not preserved; firmware owns speed/acceleration.
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
    for i, p in enumerate(path[1:], start=1):
        bend = False
        if i < len(path)-1:
            incoming = p-path[i-1]
            # Skip duplicate points at leg junctions when finding outgoing direction.
            j=i+1
            while j < len(path) and np.linalg.norm(path[j]-p)<1e-10:
                j+=1
            if j < len(path):
                outgoing=path[j]-p
                bend = np.linalg.norm(np.cross(incoming,outgoing)) > 1e-10
        if bend or np.linalg.norm(p - kept[-1]) >= step_m:
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
    from .driver import SerialDriver
    from ..perception.verification import SimulatedVerifier
    from ..perception.detector import SimulatedDetector
    if isinstance(driver, SerialDriver) and (isinstance(controller.detector, SimulatedDetector) or isinstance(controller.verifier, SimulatedVerifier)):
        raise ValueError("Simulation evidence cannot drive real hardware")
    if isinstance(driver, SerialDriver) and (home or not driver.pose_initialized):
        raise ValueError("Bench-home detached cables, prepare/confirm setup pose, then execute with home=False")
    grip_target = gripper if gripper is not None else driver
    if home:
        driver.home()
    count = 0
    speed = None
    for kind, payload in controller.iter_actions():
        if kind == "move":
            if controller.motion_speed_m_s != speed:
                speed = controller.motion_speed_m_s
                driver.set_motion_speed(speed)
            for wp in subsample_path(payload, step_m):
                driver.move_to_point(wp)
        elif kind == "grip":
            grip_target.grip()
        elif kind == "release":
            grip_target.release()
        count += 1
    return count
