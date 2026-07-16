"""
Kinematics for a 4-cable Cable-Driven Parallel Robot (CDPR).

This is the mathematical heart of the machine. Two problems live here:

  INVERSE kinematics  -- "I want the claw at point P. How long must each
                         cable be?"  This one is EASY: a cable's length is
                         just the straight-line distance from its ceiling
                         anchor to P.

  FORWARD kinematics   -- "The four cables are these lengths. Where is the
                         claw?"  This one is HARDER: four spheres (one per
                         anchor, radius = cable length) rarely intersect at
                         a perfect point once there's any measurement error,
                         so we solve it as a least-squares fit.

We also answer a third, safety-critical question:

  STATICS / wrench feasibility -- "At point P, can four cables that can only
                         PULL (never push) actually hold the claw against
                         gravity without exceeding the motor force limit?"
                         The set of points where the answer is yes is the
                         robot's usable WORKSPACE.
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import null_space

from .config import RobotConfig, DEFAULT_CONFIG


class CableRobot:
    """A 4-cable parallel robot modelled as a point-mass end-effector."""

    def __init__(self, config: RobotConfig = DEFAULT_CONFIG):
        self.cfg = config
        self.anchors = np.asarray(config.anchors, dtype=float)

    # ------------------------------------------------------------------
    # Inverse kinematics
    # ------------------------------------------------------------------
    def cable_lengths(self, point: np.ndarray) -> np.ndarray:
        """Return the 4 cable lengths needed to place the effector at `point`.

        length_i = || anchor_i - point ||
        """
        point = np.asarray(point, dtype=float)
        return np.linalg.norm(self.anchors - point, axis=1)

    def cable_directions(self, point: np.ndarray) -> np.ndarray:
        """Unit vectors pointing FROM the effector TOWARD each anchor.

        These are the directions each cable can pull the effector.
        Shape: (num_cables, 3).
        """
        point = np.asarray(point, dtype=float)
        vecs = self.anchors - point
        lengths = np.linalg.norm(vecs, axis=1, keepdims=True)
        # Avoid divide-by-zero if the effector sits exactly on an anchor.
        lengths = np.where(lengths < 1e-9, 1e-9, lengths)
        return vecs / lengths

    # ------------------------------------------------------------------
    # Forward kinematics
    # ------------------------------------------------------------------
    def position_from_lengths(
        self, lengths: np.ndarray, guess: np.ndarray | None = None
    ) -> np.ndarray:
        """Estimate effector position given the 4 cable lengths.

        Solved with Gauss-Newton least squares: we look for the point P that
        best makes ||anchor_i - P|| == lengths_i for all i. Because real cable
        lengths carry noise, the four distance constraints are usually slightly
        inconsistent, so "best fit" is the honest answer.
        """
        lengths = np.asarray(lengths, dtype=float)
        # A reasonable starting guess: centre of the room at mid height.
        if guess is None:
            guess = self.anchors.mean(axis=0)
            guess[2] = self.cfg.room_height * 0.5
        p = np.array(guess, dtype=float)

        for _ in range(50):
            diff = p - self.anchors                       # (n, 3)
            dist = np.linalg.norm(diff, axis=1)           # (n,)
            residual = dist - lengths                     # (n,) want this = 0
            # Jacobian of dist wrt p is the unit vector from anchor to p.
            jac = diff / np.where(dist[:, None] < 1e-9, 1e-9, dist[:, None])
            # Gauss-Newton step: solve jac @ step = -residual (least squares).
            step, *_ = np.linalg.lstsq(jac, -residual, rcond=None)
            p = p + step
            if np.linalg.norm(step) < 1e-9:
                break
        return p

    # ------------------------------------------------------------------
    # Statics: can we actually hold position here?
    # ------------------------------------------------------------------
    def solve_tensions(self, point: np.ndarray) -> tuple[np.ndarray, bool]:
        """Compute cable tensions that balance gravity at `point`.

        Physics: the effector is in equilibrium when the cable pull forces plus
        gravity sum to zero.

            sum_i ( t_i * direction_i )  +  (0, 0, -m*g)  =  0
            <=>   A @ t = weight,   with A = directions.T  (3 x n)

        Every tension must stay inside the motor band [min_tension, max_tension]
        -- a cable can only PULL, never push, and a real winch has a force
        ceiling. For a well-behaved cable robot we also want ALL cables taut
        (t_i >= min_tension > 0), otherwise the effector can sway.

        With n=4 cables and 3 equations, the exact solutions form a line:

            t(s) = t_particular + s * n_hat

        where n_hat spans the 1-D null space of A. We search along s for a
        distribution that keeps every cable inside the band, and center it so
        no single cable rides its limit.

        Returns (tensions, feasible).
        """
        A = self.cable_directions(point).T                     # (3, n)
        weight = np.array([0.0, 0.0, self.cfg.mass * self.cfg.gravity])

        # Any particular exact solution (may contain negatives).
        t0, *_ = np.linalg.lstsq(A, weight, rcond=None)
        ns = null_space(A)                                     # (n, k)

        lo, hi = self.cfg.min_tension, self.cfg.max_tension

        if ns.shape[1] == 0:
            # No redundancy to exploit; accept t0 only if already in band.
            feasible = bool(np.all(t0 >= lo) and np.all(t0 <= hi))
            return t0, feasible

        # Use the first (dominant) null-space direction. For s: require
        #   lo <= t0_i + s * n_i <= hi   for every cable i.
        n_hat = ns[:, 0]
        s_lo, s_hi = -np.inf, np.inf
        for t_i, n_i in zip(t0, n_hat):
            if abs(n_i) < 1e-12:
                if not (lo <= t_i <= hi):        # fixed cable already out of band
                    return t0, False
                continue
            a = (lo - t_i) / n_i
            b = (hi - t_i) / n_i
            low, high = min(a, b), max(a, b)
            s_lo, s_hi = max(s_lo, low), min(s_hi, high)

        if s_lo > s_hi:
            return t0, False                     # no s keeps all cables in band

        s = 0.5 * (s_lo + s_hi)                   # center -> most margin
        tensions = t0 + s * n_hat
        feasible = bool(np.all(tensions >= lo - 1e-6) and np.all(tensions <= hi + 1e-6))
        return tensions, feasible

    def is_reachable(self, point: np.ndarray) -> bool:
        """True if `point` is inside the safe, statically-feasible workspace."""
        x, y, z = point
        m = self.cfg
        # Geometric box with wall margins.
        from .config import WALL_MARGIN, SAFE_MIN_Z

        if not (WALL_MARGIN <= x <= m.room_width - WALL_MARGIN):
            return False
        if not (WALL_MARGIN <= y <= m.room_depth - WALL_MARGIN):
            return False
        if not (SAFE_MIN_Z <= z <= m.room_height - 0.1):
            return False
        _, feasible = self.solve_tensions(point)
        return feasible


def reachable_workspace_slice(
    robot: CableRobot, z: float, resolution: int = 40
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample a horizontal slice of the workspace at height `z`.

    Handy for visualising "where can the claw actually go at this height?".
    Returns (xs, ys, mask) suitable for matplotlib's pcolormesh/contourf.
    """
    m = robot.cfg
    xs = np.linspace(0, m.room_width, resolution)
    ys = np.linspace(0, m.room_depth, resolution)
    mask = np.zeros((resolution, resolution), dtype=bool)
    for i, yy in enumerate(ys):
        for j, xx in enumerate(xs):
            mask[i, j] = robot.is_reachable(np.array([xx, yy, z]))
    return xs, ys, mask
