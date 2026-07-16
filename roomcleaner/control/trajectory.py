"""
Simple motion planning: turn a target point into a smooth path of waypoints.

For Phase 0 we keep this deliberately simple -- straight-line moves with an
ease-in / ease-out velocity profile so the claw doesn't jerk. Later phases can
swap in obstacle avoidance or spline paths behind the same interface.
"""

from __future__ import annotations

import numpy as np


def smoothstep(t: np.ndarray) -> np.ndarray:
    """Classic ease-in/ease-out curve mapping [0,1] -> [0,1] with zero end-slope."""
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def straight_line(
    start: np.ndarray, goal: np.ndarray, speed: float = 0.4, hz: float = 50.0
) -> np.ndarray:
    """Generate waypoints from `start` to `goal`.

    Args:
        speed: cruise speed in m/s.
        hz:    control loop rate; one waypoint is emitted per tick.

    Returns an (N, 3) array of positions, smoothly accelerating and decelerating.
    """
    start = np.asarray(start, dtype=float)
    goal = np.asarray(goal, dtype=float)
    distance = np.linalg.norm(goal - start)
    if distance < 1e-6:
        return goal[None, :]

    duration = max(distance / speed, 1.0 / hz)
    n = max(int(duration * hz), 2)
    ts = np.linspace(0.0, 1.0, n)
    eased = smoothstep(ts)[:, None]
    return start[None, :] + eased * (goal - start)[None, :]


def safe_transit(
    start: np.ndarray, goal: np.ndarray, cruise_z: float, **kw
) -> np.ndarray:
    """Move via a safe cruise height: up, across, then down.

    This is how the real robot should travel -- lift to a clear height, move
    horizontally over the target, then descend -- so the claw never drags
    across the floor or clips furniture at grab height.
    """
    start = np.asarray(start, dtype=float)
    goal = np.asarray(goal, dtype=float)
    up = np.array([start[0], start[1], cruise_z])
    over = np.array([goal[0], goal[1], cruise_z])
    legs = [
        straight_line(start, up, **kw),
        straight_line(up, over, **kw),
        straight_line(over, goal, **kw),
    ]
    return np.vstack(legs)
