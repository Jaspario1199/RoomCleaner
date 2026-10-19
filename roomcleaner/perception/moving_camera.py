"""Explicit calibrated ray/plane geometry for an image-specific camera pose.

Camera C uses +X right, +Y down and +Z forward. World W uses metres and +Z
upward. ``T_WC`` maps camera coordinates to world coordinates; its translation
is the optical centre. Plane coordinates obey ``normal @ point + offset = 0``.
Pixels MUST already be undistorted into the pixel coordinate system described
by K (not normalized coordinates). Distortion correction, pose estimation,
frame/pose timestamp association and calibration quality are caller concerns.

This module supplies synthetic-testable geometry only. It has no room defaults,
fixed camera fallback, live integration, or pickup/release success inference.
"""

from __future__ import annotations

import numpy as np


_RIGID_ATOL = 1e-8
_PARALLEL_ATOL = 1e-12


def _finite_array(value, shape: tuple[int, ...], name: str) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite numeric array of shape {shape}") from exc
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite numeric array of shape {shape}")
    return array


def pixel_to_world_plane(
    u: float,
    v: float,
    K: np.ndarray,
    T_WC: np.ndarray,
    plane_normal: np.ndarray,
    plane_offset: float,
    *,
    image_size: tuple[int, int] | None = None,
) -> np.ndarray:
    """Return the world 3-vector where an undistorted pixel ray hits a plane.

    All calibration, pose and plane inputs are required. K is the canonical
    pinhole matrix ``[[fx, skew, cx], [0, fy, cy], [0, 0, 1]]`` with positive
    focal lengths. T_WC is a proper rigid 4x4 camera-to-world transform (rotation
    in SO(3), homogeneous last row). Translation and plane offset use metres
    when the normal is unit length; a nonzero scaled normal/offset is allowed.

    Optional image_size is (width, height), positive integers. Its pixel domain
    is ``0 <= u < width, 0 <= v < height`` in the undistorted image. Callers
    must supply the dimensions of that image if it differs from the raw frame.
    Without image_size, bounds cannot be checked. Parallel/near-parallel rays
    (absolute unit-vector dot product <= 1e-12), intersections at the optical
    centre or behind the camera, and invalid inputs raise ValueError. Rigid
    rotation validation uses an absolute tolerance of 1e-8 and no relative
    tolerance. No grazing-angle uncertainty or physical workspace gate is
    inferred from a finite intersection.
    """
    pixel = _finite_array([u, v], (2,), "pixel")
    intrinsics = _finite_array(K, (3, 3), "K")
    if (
        intrinsics[0, 0] <= 0
        or intrinsics[1, 1] <= 0
        or intrinsics[1, 0] != 0
        or not np.array_equal(intrinsics[2], [0, 0, 1])
    ):
        raise ValueError("K must be a canonical pinhole matrix with positive focal lengths")
    pose = _finite_array(T_WC, (4, 4), "T_WC")
    rotation = pose[:3, :3]
    if (
        not np.array_equal(pose[3], [0, 0, 0, 1])
        or not np.allclose(rotation.T @ rotation, np.eye(3), atol=_RIGID_ATOL, rtol=0)
        or not np.isclose(np.linalg.det(rotation), 1, atol=_RIGID_ATOL, rtol=0)
    ):
        raise ValueError("T_WC must be a proper rigid camera-to-world transform")
    normal = _finite_array(plane_normal, (3,), "plane_normal")
    offset = _finite_array(plane_offset, (), "plane_offset").item()
    # Scale before taking norms to avoid overflow/underflow for finite inputs.
    normal_scale = np.max(np.abs(normal))
    if normal_scale == 0:
        raise ValueError("plane_normal must be nonzero")
    normal_scaled = normal / normal_scale
    normal_length = np.linalg.norm(normal_scaled)
    normal_unit = normal_scaled / normal_length
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        offset_unit = (offset / normal_scale) / normal_length
    if not np.isfinite(offset_unit):
        raise ValueError("plane offset is numerically unrepresentable after normalization")
    if image_size is not None:
        try:
            width, height = image_size
        except (TypeError, ValueError) as exc:
            raise ValueError("image_size must contain positive integer width and height") from exc
        if any(isinstance(d, (bool, np.bool_)) or not isinstance(d, (int, np.integer)) or d <= 0
               for d in (width, height)):
            raise ValueError("image_size must contain positive integer width and height")
        if not (0 <= pixel[0] < width and 0 <= pixel[1] < height):
            raise ValueError("pixel lies outside the undistorted image")
    try:
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            ray_camera = np.linalg.solve(intrinsics, [pixel[0], pixel[1], 1.0])
    except np.linalg.LinAlgError as exc:
        raise ValueError("K must be invertible") from exc
    if not np.all(np.isfinite(ray_camera)):
        raise ValueError("K produces a numerically invalid camera ray")
    ray_camera = ray_camera / np.max(np.abs(ray_camera))
    ray_camera = ray_camera / np.linalg.norm(ray_camera)
    ray_world = rotation @ ray_camera
    denominator = normal_unit @ ray_world
    if abs(denominator) <= _PARALLEL_ATOL:
        raise ValueError("camera ray is parallel or nearly parallel to the plane")
    origin = pose[:3, 3]
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        distance = -(normal_unit @ origin + offset_unit) / denominator
        point = origin + distance * ray_world
    if not np.isfinite(distance) or not np.all(np.isfinite(point)):
        raise ValueError("ray/plane intersection is numerically unrepresentable")
    if distance <= 0:
        raise ValueError("plane intersection is at or behind the camera")
    return point
