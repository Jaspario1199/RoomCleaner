"""
Gripper v7 -- jaw four-bar kinematics (pure Python / numpy, no CAD).

Right jaw (+x side), all in the v7 local frame (x lateral, y along the claw, tube axis at x = 0):

    ground  C --- P      C = compound axis, P = link ground pivot (frame)
    crank   C --- A      length GRIPV7_CRANK_R, crank angle theta (measured from +x, CCW)
    jaw     A --- B      coupler, length GRIPV7_JAW_AB; the gripping face is a rigid part of it
    link    P --- B      length derived from closure at the CLOSED pose

Closing = the compound rotating clockwise (theta decreasing).  The compound turns by
GRIPV7_SWEEP_DEG between the closed and the open stop; the jaw frame is the world frame at
the closed pose (inner face vertical, on x = 0 so the two tips meet).  The left jaw is the
mirror image (follower, counter-rotating).

Grip force at the tip by virtual work:  F_normal = T_jaw / (dx_tip / dtheta)
with T_jaw = tau_servo * ratio * eta^2 / 2   (review R5 convention: two printed meshes in series,
torque split between the jaws; eta = 0.95 per mesh).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from cad import params as P

ETA_MESH = 0.95                      # review R5 (calculations/gen2_screening.py ETA_MESH)
G = 9.81
SERVO_STALL_4V8 = 9.4 * G / 100.0    # N m (MG996R, review R5)
SERVO_STALL_6V0 = 11.0 * G / 100.0

C_RIGHT = np.array([P.GRIPV7_CD_SYNC / 2.0, 0.0])


def jaw_torque(tau_servo: float, ratio: float, eta: float = ETA_MESH) -> float:
    """Torque delivered to ONE jaw crank (both jaws share equally, two meshes in series)."""
    return tau_servo * ratio * eta ** 2 / 2.0


@dataclass(frozen=True)
class Pose:
    theta_deg: float
    A: np.ndarray            # crank pin
    B: np.ndarray            # link-jaw pivot
    psi_deg: float           # jaw angle (A->B direction)
    tilt_deg: float          # jaw rotation relative to the closed pose
    tip: np.ndarray          # lowest point of the inner face


class FourBar:
    """Right-jaw four-bar built from GRIPV7_* parameters (or explicit overrides)."""

    def __init__(self, R=None, theta_closed=None, sweep=None, P_xy=None, d=None, psi_c=None,
                 tip_drop=None, cx=None, tip_offset=None):
        self.R = P.GRIPV7_CRANK_R if R is None else R
        self.theta_c = P.GRIPV7_THETA_CLOSED if theta_closed is None else theta_closed
        self.sweep = P.GRIPV7_SWEEP_DEG if sweep is None else sweep
        self.Pg = np.array(P.GRIPV7_LINK_GROUND if P_xy is None else P_xy, float)
        self.d = P.GRIPV7_JAW_AB if d is None else d
        self.psi_c = P.GRIPV7_JAW_PSI_CLOSED if psi_c is None else psi_c
        self.tip_drop = P.GRIPV7_JAW_TIP_DROP if tip_drop is None else tip_drop
        self.C = C_RIGHT.copy() if cx is None else np.array([cx, 0.0])
        th = math.radians(self.theta_c)
        self.Ac = self.C + self.R * np.array([math.cos(th), math.sin(th)])
        ps = math.radians(self.psi_c)
        self.Bc = self.Ac + self.d * np.array([math.cos(ps), math.sin(ps)])
        self.L = float(np.linalg.norm(self.Bc - self.Pg))          # link length (pin to pin)
        # tip in the reference-pose jaw frame (world axes).  Default: inner face on x = 0 (tips meet),
        # tip_drop below A.  tip_offset=(dx, dy) from A overrides (used for the v6 reference).
        if tip_offset is None:
            self.tip_c = np.array([0.0, self.Ac[1] - self.tip_drop])
        else:
            self.tip_c = self.Ac + np.asarray(tip_offset, float)
        self._branch_prev = self.Bc.copy()

    # ---- solving -----------------------------------------------------------------------------
    def _B_of(self, A, prev):
        d, L = self.d, self.L
        dd = float(np.linalg.norm(self.Pg - A))
        if dd > d + L or dd < abs(d - L):
            raise ValueError("four-bar cannot close at this crank angle")
        a = (d * d - L * L + dd * dd) / (2 * dd)
        h = math.sqrt(max(d * d - a * a, 0.0))
        u = (self.Pg - A) / dd
        perp = np.array([-u[1], u[0]])
        m = A + a * u
        c1, c2 = m + h * perp, m - h * perp
        return c1 if np.linalg.norm(c1 - prev) < np.linalg.norm(c2 - prev) else c2

    def pose(self, theta_deg: float) -> Pose:
        """Pose at an absolute crank angle; the branch is tracked from the closed pose."""
        n = max(2, int(abs(theta_deg - self.theta_c) / 0.5) + 1)
        prev = self.Bc.copy()
        B = prev
        A = self.Ac
        for t in np.linspace(self.theta_c, theta_deg, n):
            th = math.radians(t)
            A = self.C + self.R * np.array([math.cos(th), math.sin(th)])
            B = self._B_of(A, prev)
            prev = B
        psi = math.degrees(math.atan2(B[1] - A[1], B[0] - A[0]))
        tilt = psi - self.psi_c
        c, s = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
        rel = self.tip_c - self.Ac
        tip = A + np.array([rel[0] * c - rel[1] * s, rel[0] * s + rel[1] * c])
        return Pose(theta_deg, A, B, psi, tilt, tip)

    def poses(self, n: int):
        return [self.pose(t) for t in np.linspace(self.theta_c, self.theta_c + self.sweep, n)]

    @property
    def theta_open(self) -> float:
        return self.theta_c + self.sweep

    # ---- derived numbers ----------------------------------------------------------------------
    def tip_gap(self, pose: Pose) -> float:
        """Tip-to-tip distance (the two inner faces are mirror images about x = 0)."""
        return 2.0 * float(pose.tip[0])

    def tip_force(self, theta_deg: float, tau_servo: float, ratio: float, d_theta: float = 0.25) -> float:
        """Grip force (N) normal to the inner face, per jaw, by virtual work."""
        p1, p2 = self.pose(theta_deg - d_theta), self.pose(theta_deg + d_theta)
        dx = (p2.tip[0] - p1.tip[0]) * 1e-3                       # m
        dth = math.radians(2 * d_theta)
        if dx <= 1e-12:
            return float("inf")
        return jaw_torque(tau_servo, ratio) * dth / dx

    def link_force_ratio(self, pose: Pose) -> float:
        """Link axial force divided by the tip normal force (jaw statics, moment about A)."""
        # unit link direction (B -> P); tip force acts along -x on the jaw (pushing it outward = reaction)
        u = self.Pg - pose.B
        u = u / np.linalg.norm(u)
        rb = pose.B - pose.A
        rt = pose.tip - pose.A
        # moment about A: rb x (Fl u) + rt x (F (-1, 0)) = 0
        m_link = rb[0] * u[1] - rb[1] * u[0]
        m_tip = rt[0] * 0.0 - rt[1] * (-1.0)
        return abs(m_tip / m_link) if abs(m_link) > 1e-9 else float("inf")


def mirror_x(v):
    """Mirror a point (or array of points) about the tube plane x = 0."""
    a = np.array(v, float)
    a[..., 0] = -a[..., 0]
    return a


def default() -> FourBar:
    return FourBar()


def v6_reference() -> FourBar:
    """The measured v6 jaw four-bar (verification/gripper_v6_inspection.md) in the same local frame
    (tube axis x = 0, gear-axes line y = 0): compound axis x = +18, link ground pin (12, -42.6),
    crank R75, jaw pins 41.34 apart, link 70; reference pose = the exported assembly pose
    (crank -31.2 deg); inner-face tip 41.75 left / 87.68 below the crank pin."""
    return FourBar(R=75.0, theta_closed=-31.2, sweep=0.0, P_xy=(12.0, -42.6), d=41.3356,
                   psi_c=-104.4, tip_drop=87.68, cx=18.0, tip_offset=(-41.75, -87.68))


if __name__ == "__main__":
    fb = default()
    print("R %.2f  theta_c %.2f  sweep %.1f  P %s  d %.2f  link %.2f" %
          (fb.R, fb.theta_c, fb.sweep, fb.Pg, fb.d, fb.L))
    for th in np.linspace(fb.theta_c, fb.theta_open, 7):
        ps = fb.pose(th)
        print("theta %7.2f  A (%6.2f,%7.2f)  B (%6.2f,%7.2f)  tilt %5.2f  tip (%6.2f,%7.2f)  gap %6.2f  F4.8 %5.1f"
              % (th, *ps.A, *ps.B, ps.tilt_deg, *ps.tip, fb.tip_gap(ps),
                 fb.tip_force(th, SERVO_STALL_4V8, P.GRIPV7_RATIO)))
