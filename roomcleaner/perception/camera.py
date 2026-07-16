"""
Thin webcam wrapper (OpenCV).

Kept tiny and optional: OpenCV is imported lazily so the rest of the package
imports fine on a machine without it. On your robot's Raspberry Pi you'd
`pip install opencv-python` and a USB webcam (e.g. Logitech C920) is plug-and-play.
"""

from __future__ import annotations

import numpy as np


class Webcam:
    """Grab frames from a USB/CSI camera by index."""

    def __init__(self, index: int = 0, width: int = 1280, height: int = 720):
        self.index = index
        self.width = width
        self.height = height
        self._cap = None

    def open(self):
        try:
            import cv2
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "Webcam capture needs OpenCV: pip install opencv-python"
            ) from exc
        self._cap = cv2.VideoCapture(self.index)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open camera index {self.index}.")
        return self

    def read(self) -> np.ndarray:
        """Return one frame as an HxWx3 array, or raise on failure."""
        if self._cap is None:
            self.open()
        ok, frame = self._cap.read()
        if not ok:
            raise RuntimeError("Failed to read a frame from the camera.")
        return frame

    def resolution(self) -> tuple[int, int]:
        """Actual (width, height) the camera is delivering."""
        if self._cap is None:
            self.open()
        import cv2

        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (w or self.width, h or self.height)

    def release(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *exc):
        self.release()
