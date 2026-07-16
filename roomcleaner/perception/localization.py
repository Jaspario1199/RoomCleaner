"""
Turn a pixel in the camera image into an (x, y) point on the room floor.

This is the "2D -> 3D" step. Two mappers, same interface:

  OverheadLinearMapper  -- ZERO calibration. Assumes one camera on the ceiling
                           looking straight down, framing the whole floor. A
                           pixel maps linearly to the floor rectangle. Needs
                           only your room dimensions -> works out of the box.

  HomographyMapper      -- PRECISE. You mark four known floor points once
                           (e.g. the room corners, or a taped rectangle) and
                           their pixel locations; this fits a homography that
                           corrects perspective and lens tilt. Use this when the
                           camera isn't perfectly centered/level.

The homography is solved with a plain-numpy Direct Linear Transform, so this
module has NO heavy dependencies and is fully unit-tested.
"""

from __future__ import annotations

import numpy as np


class FloorMapper:
    """Base interface: pixel (u, v) -> world (x, y) on the floor (z = 0)."""

    def pixel_to_floor(self, u: float, v: float) -> np.ndarray:
        raise NotImplementedError

    def to_detection_point(self, u: float, v: float) -> np.ndarray:
        """Return a full 3D point on the floor for a pixel."""
        xy = self.pixel_to_floor(u, v)
        return np.array([xy[0], xy[1], 0.0])


class OverheadLinearMapper(FloorMapper):
    """Zero-calibration mapper for a centered, straight-down ceiling camera.

    Assumes the image exactly frames the floor rectangle:
        u in [0, image_w]  ->  x in [0, room_width]
        v in [0, image_h]  ->  y in [0, room_depth]

    `flip_x` / `flip_y` let you fix mirrored/rotated mounting without re-wiring.
    """

    def __init__(
        self,
        room_width: float,
        room_depth: float,
        image_w: int,
        image_h: int,
        flip_x: bool = False,
        flip_y: bool = False,
    ):
        self.room_width = room_width
        self.room_depth = room_depth
        self.image_w = image_w
        self.image_h = image_h
        self.flip_x = flip_x
        self.flip_y = flip_y

    def pixel_to_floor(self, u: float, v: float) -> np.ndarray:
        fx = u / max(self.image_w, 1)
        fy = v / max(self.image_h, 1)
        if self.flip_x:
            fx = 1.0 - fx
        if self.flip_y:
            fy = 1.0 - fy
        return np.array([fx * self.room_width, fy * self.room_depth])


class HomographyMapper(FloorMapper):
    """Perspective-correct mapper from a 4+ point calibration.

    Build it with `from_correspondences([...pixel...], [...floor...])`.
    """

    def __init__(self, H: np.ndarray):
        self.H = np.asarray(H, dtype=float)

    @classmethod
    def from_correspondences(
        cls, pixels: np.ndarray, floor_xy: np.ndarray
    ) -> "HomographyMapper":
        """Fit a homography mapping pixel points -> floor points.

        `pixels`   : (N, 2) image coordinates (u, v), N >= 4
        `floor_xy` : (N, 2) matching world floor coordinates (x, y) in meters
        """
        pixels = np.asarray(pixels, dtype=float)
        floor_xy = np.asarray(floor_xy, dtype=float)
        if len(pixels) < 4 or len(floor_xy) < 4:
            raise ValueError("Need at least 4 point correspondences.")

        # Direct Linear Transform: build the 2N x 9 system A h = 0 and take the
        # smallest singular vector as h (the homography, up to scale).
        A = []
        for (u, v), (x, y) in zip(pixels, floor_xy):
            A.append([-u, -v, -1, 0, 0, 0, u * x, v * x, x])
            A.append([0, 0, 0, -u, -v, -1, u * y, v * y, y])
        A = np.asarray(A, dtype=float)
        _, _, vt = np.linalg.svd(A)
        H = vt[-1].reshape(3, 3)
        if abs(H[2, 2]) > 1e-12:
            H = H / H[2, 2]
        return cls(H)

    def pixel_to_floor(self, u: float, v: float) -> np.ndarray:
        vec = self.H @ np.array([u, v, 1.0])
        if abs(vec[2]) < 1e-12:
            vec[2] = 1e-12
        return np.array([vec[0] / vec[2], vec[1] / vec[2]])
