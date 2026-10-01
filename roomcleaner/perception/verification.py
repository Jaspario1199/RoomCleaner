"""Conservative camera evidence gates. Uncertainty fails closed, never delivers.

Projection/ROI and appearance thresholds must be commissioned in the actual room.
Floor homography alone is insufficient for a suspended payload (parallax).
"""
from dataclasses import dataclass
import time
import numpy as np


class VerificationError(RuntimeError):
    pass


class SimulatedVerifier:
    """Explicit simulation evidence; never instantiate for real hardware."""
    def before_pickup(self, target): pass
    def verify_pickup(self, target, probe): return True
    def retry_target_present(self, target): return True
    def before_release(self, target): pass
    def verify_delivery(self, target, hamper): return True


@dataclass
class Observation:
    timestamp: float
    frame: np.ndarray
    detections: list


class CameraVerifier:
    def __init__(self, observe, projection, hamper_roi, *, samples=3,
                 min_motion_px=20, roi_radius_px=100, similarity=0.70,
                 ambiguity_margin=0.10, settle_s=0.5):
        if projection is None or hamper_roi is None:
            raise VerificationError("Measure camera projection and hamper pixel ROI before live missions")
        self.projection = np.asarray(projection, dtype=float)
        self.hamper_roi = np.asarray(hamper_roi, dtype=float)
        if self.projection.shape != (3, 4) or not np.isfinite(self.projection).all():
            raise ValueError("camera projection must be finite 3x4")
        if self.hamper_roi.shape != (4,) or not np.isfinite(self.hamper_roi).all() or np.any(self.hamper_roi[2:] <= self.hamper_roi[:2]):
            raise ValueError("hamper ROI must be x1,y1,x2,y2")
        if samples < 2 or min_motion_px <= 0 or settle_s < 0:
            raise ValueError("Invalid camera verification settings")
        self.observe, self.samples = observe, samples
        self.min_motion, self.radius = min_motion_px, roi_radius_px
        self.similarity, self.margin, self.settle = similarity, ambiguity_margin, settle_s
        self.last_timestamp = -float('inf')
        self.template = self.origin = None

    def _fresh(self):
        obs = self.observe()
        now = time.monotonic()
        if obs.timestamp <= self.last_timestamp or not 0 <= now-obs.timestamp < 2.0:
            raise VerificationError("Stale camera evidence")
        self.last_timestamp = obs.timestamp
        return obs

    def _project(self, point):
        q = self.projection @ np.r_[point, 1.0]
        if q[2] <= 0:
            raise VerificationError("Verification point outside camera projection")
        return q[:2]/q[2]

    @staticmethod
    def _center(d):
        return (np.asarray(d.bbox[:2])+np.asarray(d.bbox[2:]))/2

    @staticmethod
    def _patch(frame, box):
        import cv2
        x1,y1,x2,y2 = np.asarray(box, dtype=int)
        h,w = frame.shape[:2]
        x1,y1,x2,y2 = max(0,x1),max(0,y1),min(w,x2),min(h,y2)
        if x2-x1 < 8 or y2-y1 < 8:
            raise VerificationError("Payload image too small")
        crop = frame[y1:y2,x1:x2]
        if crop.ndim == 3:
            crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        a = cv2.resize(crop, (32,32)).astype(float).ravel()
        a -= a.mean()
        norm = np.linalg.norm(a)
        if norm < 1e-6:
            raise VerificationError("Payload lacks trackable texture")
        return a/norm

    def _match(self, obs, target, region):
        ranked = []
        for d in obs.detections:
            if d.label != target.label or d.bbox is None or d.confidence < 0.5:
                continue
            try:
                score = float(self.template @ self._patch(obs.frame, d.bbox))
            except VerificationError:
                continue
            ranked.append((score,d))
        ranked.sort(key=lambda x:x[0], reverse=True)
        if not ranked or ranked[0][0] < self.similarity:
            return None
        # Include look-alikes anywhere in frame, not just inside the expected ROI.
        if len(ranked)>1 and ranked[0][0]-ranked[1][0] < self.margin:
            return None
        d = ranked[0][1]
        return d if region(self._center(d)) else None

    def before_pickup(self, target):
        if target.bbox is None:
            raise VerificationError("Pickup needs a camera bounding box")
        obs = self._fresh()
        near = [d for d in obs.detections if d.label == target.label and d.bbox is not None
                and np.linalg.norm(self._center(d)-self._center(target)) < self.min_motion]
        if len(near) != 1:
            raise VerificationError("Selected target moved or is ambiguous before grip")
        self.origin = self._center(near[0])
        self.template = self._patch(obs.frame, near[0].bbox)
        # Reject look-alikes already inside the hamper; their presence is not delivery.
        if self._match(obs, target, self._in_hamper) is not None:
            raise VerificationError("Matching payload already in hamper; ambiguous identity")

    def verify_pickup(self, target, probe):
        time.sleep(self.settle)
        expected = self._project(probe)
        for _ in range(self.samples):
            obs = self._fresh()
            d = self._match(obs, target, lambda p: np.linalg.norm(p-expected) < self.radius)
            if d is None or np.linalg.norm(self._center(d)-self.origin) < self.min_motion:
                return False
        return True

    def retry_target_present(self, target):
        obs = self._fresh()
        return self._match(obs,target,lambda p: np.linalg.norm(p-self.origin)<self.min_motion) is not None

    def before_release(self, target):
        obs = self._fresh()
        if self._match(obs,target,self._in_hamper) is None:
            raise VerificationError("Payload not visible over hamper before release")

    def _in_hamper(self, p):
        return bool(np.all(p >= self.hamper_roi[:2]) and np.all(p <= self.hamper_roi[2:]))

    def validate_retreat(self, point):
        pixel = self._project(point)
        expanded = np.r_[self.hamper_roi[:2]-self.radius, self.hamper_roi[2:]+self.radius]
        if np.all(pixel >= expanded[:2]) and np.all(pixel <= expanded[2:]):
            raise VerificationError("Claw retreat does not clear the hamper camera region")

    def verify_delivery(self, target, hamper):
        time.sleep(self.settle)
        centers=[]
        for _ in range(self.samples):
            d=self._match(self._fresh(),target,self._in_hamper)
            if d is None:
                return False
            centers.append(self._center(d))
        # Controller has moved the claw away before this check. Require a stable,
        # positively identified payload, not disappearance or a release command ACK.
        return max(np.linalg.norm(c-centers[0]) for c in centers) < self.min_motion
