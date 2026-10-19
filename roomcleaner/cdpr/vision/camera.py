"""Pinhole camera with OpenCV distortion, loaded from a calibration file.

Calibration files are produced by tools/calibrate_camera.py and are valid only
for the exact sensor mode (resolution, crop, lens focus) they were captured
with; the calibration_id is recorded with every calibration result.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class CameraModel:
    K: np.ndarray
    dist: np.ndarray
    image_size: tuple       # (width, height)
    calibration_id: str

    @classmethod
    def load(cls, path) -> "CameraModel":
        d = json.loads(Path(path).read_text())
        K = np.asarray(d["K"], float)
        dist = np.asarray(d.get("dist", [0, 0, 0, 0, 0]), float)
        if K.shape != (3, 3) or K[0, 0] <= 0 or K[1, 1] <= 0:
            raise ValueError("invalid intrinsics")
        return cls(K, dist, tuple(d["image_size"]), d.get("calibration_id", Path(path).stem))

    @property
    def fx(self) -> float:
        return float(self.K[0, 0])

    def project(self, pts_cam: np.ndarray) -> np.ndarray:
        pts = np.asarray(pts_cam, float).reshape(-1, 3)
        img, _ = cv2.projectPoints(pts, np.zeros(3), np.zeros(3), self.K, self.dist)
        return img.reshape(-1, 2)

    def in_image(self, uv, margin=0) -> np.ndarray:
        w, h = self.image_size
        uv = np.atleast_2d(uv)
        return (uv[:, 0] >= margin) & (uv[:, 0] < w - margin) & (uv[:, 1] >= margin) & (uv[:, 1] < h - margin)
