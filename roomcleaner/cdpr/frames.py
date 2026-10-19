"""Rigid-body transforms.

Convention: ``T_A_B`` is a 4x4 homogeneous transform that maps coordinates
expressed in frame B into frame A:  ``x_A = T_A_B @ x_B``.  Composition reads
left to right: ``T_A_C = T_A_B @ T_B_C``.  Rotations are proper (det = +1).

Frames used across the system:

    R   room frame: origin on the floor at the corner under station A,
        +X toward station B, +Y toward station D, +Z up (gravity is -Z
        only if the floor is level; see docs).
    M   marker frame: origin at the printed tag centre, X/Y along the tag's
        printed axes, +Z out of the printed face (up, when lying on the floor).
    B   claw body frame: origin at the cable attachment reference point,
        +Z up when the claw hangs upright.
    C   camera optical frame: +X right, +Y down, +Z forward (OpenCV).
"""
from __future__ import annotations

import numpy as np


def rot_x(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], float)


def rot_y(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], float)


def rot_z(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)


def rpy_to_matrix(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """Z-Y-X (yaw, then pitch, then roll) Euler angles -> rotation matrix."""
    return rot_z(yaw) @ rot_y(pitch) @ rot_x(roll)


def matrix_to_rpy(R: np.ndarray) -> np.ndarray:
    """Inverse of :func:`rpy_to_matrix` (valid away from pitch = +-90 deg)."""
    pitch = -np.arcsin(np.clip(R[2, 0], -1.0, 1.0))
    roll = np.arctan2(R[2, 1], R[2, 2])
    yaw = np.arctan2(R[1, 0], R[0, 0])
    return np.array([roll, pitch, yaw])


def rotvec_to_matrix(v) -> np.ndarray:
    """Rodrigues: axis * angle -> rotation matrix."""
    v = np.asarray(v, float)
    th = np.linalg.norm(v)
    if th < 1e-12:
        K = _skew(v)
        return np.eye(3) + K
    k = v / th
    K = _skew(k)
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * (K @ K)


def matrix_to_rotvec(R: np.ndarray) -> np.ndarray:
    c = np.clip((np.trace(R) - 1) / 2, -1.0, 1.0)
    th = np.arccos(c)
    if th < 1e-9:
        return np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / 2
    if np.pi - th < 1e-6:
        # near 180 deg: use the dominant diagonal for the axis
        i = int(np.argmax(np.diag(R)))
        axis = R[:, i] + np.eye(3)[:, i]
        axis /= np.linalg.norm(axis)
        return axis * th
    w = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    return w * th / (2 * np.sin(th))


def _skew(v) -> np.ndarray:
    x, y, z = v
    return np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]], float)


def make_T(R=None, t=None) -> np.ndarray:
    T = np.eye(4)
    if R is not None:
        T[:3, :3] = np.asarray(R, float)
    if t is not None:
        T[:3, 3] = np.asarray(t, float)
    return T


def inv_T(T: np.ndarray) -> np.ndarray:
    R, t = T[:3, :3], T[:3, 3]
    out = np.eye(4)
    out[:3, :3] = R.T
    out[:3, 3] = -R.T @ t
    return out


def apply_T(T: np.ndarray, pts) -> np.ndarray:
    """Transform one point (3,) or many points (N,3)."""
    pts = np.asarray(pts, float)
    if pts.ndim == 1:
        return T[:3, :3] @ pts + T[:3, 3]
    return pts @ T[:3, :3].T + T[:3, 3]


def is_rigid(T: np.ndarray, tol: float = 1e-6) -> bool:
    T = np.asarray(T, float)
    if T.shape != (4, 4) or not np.all(np.isfinite(T)):
        return False
    R = T[:3, :3]
    return (np.allclose(T[3], [0, 0, 0, 1], atol=tol)
            and np.allclose(R.T @ R, np.eye(3), atol=tol)
            and abs(np.linalg.det(R) - 1) < tol)


def tilt_angle(R: np.ndarray) -> float:
    """Angle between the body +Z axis and the parent +Z axis (radians)."""
    return float(np.arccos(np.clip(R[2, 2], -1.0, 1.0)))


def planar_T(x: float, y: float, yaw: float, z: float = 0.0) -> np.ndarray:
    """Transform for a frame lying flat: translation (x,y,z) and yaw about +Z."""
    return make_T(rot_z(yaw), [x, y, z])
