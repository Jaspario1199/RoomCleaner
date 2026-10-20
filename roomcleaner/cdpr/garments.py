"""Garment perception for the claw camera, built on the gen-1 detector.

Gen-1 already has the detector: ``roomcleaner/perception/vision_detector.py``
(YOLO-World, open vocabulary: "sock", "jeans", "towel", ...). Gen-1 used it on a
FIXED overhead camera with a fixed pixel->floor mapping. In gen-2 the camera
rides on the claw, so this module adds the missing pieces:

* ``ClawFloorMapper``: pixel -> floor point using the claw's CURRENT pose (from
  the marker + IMU, ``perception.VisionSource``), the camera intrinsics and the
  calibrated marker registration -- an exact ray/plane intersection
  (``perception/moving_camera.pixel_to_world_plane``).
* ``ClawGarmentPerception``: the ``tasks.ItemPerception`` used by the task
  runner (which, per the handoff, shifts the claw a short way toward the
  destination before asking ``holding``, so the pickup spot is no longer under
  the jaws), with:
    - ``scan``: detect, map box centres (straight-down camera) to the room,
      give items stable ids across scans;
    - ``holding``: two independent cues must agree -- the jaw region of the
      image (projected from the CAD jaw position) no longer looks like the
      empty-claw reference, AND no garment is still seen on the floor at the
      pickup spot;
    - ``item_at``: claw region looks empty again and the item is either seen
      inside the hamper radius or nowhere on the visible floor outside it.

Any ``perception.detector.Detector`` works (YOLO-World for real use,
``BlobDetector`` for tests/bright items); only its pixel boxes are used.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np

from ..perception.detector import Detection, Detector
from ..perception.localization import FloorMapper
from ..perception.moving_camera import pixel_to_world_plane
from .frames import make_T, rot_z
from .perception import to_room
from .tasks import ItemPerception, ItemSighting


class ClawFloorMapper(FloorMapper):
    """Pixel -> room-floor point for the claw camera at a known pose."""

    def __init__(self, camera, T_R_C, plane_z=0.0):
        self.cam = camera
        self.T_R_C = np.asarray(T_R_C, float)
        self.plane_z = plane_z

    def _undistort(self, u, v):
        p = cv2.undistortPoints(np.array([[[u, v]]], np.float64), self.cam.K, self.cam.dist, P=self.cam.K)
        return float(p[0, 0, 0]), float(p[0, 0, 1])

    def pixel_to_floor(self, u, v):
        uu, vv = self._undistort(u, v)
        p = pixel_to_world_plane(uu, vv, self.cam.K, self.T_R_C, np.array([0.0, 0.0, 1.0]), -self.plane_z)
        return p[:2]

    def to_detection_point(self, u, v):
        xy = self.pixel_to_floor(u, v)
        return np.array([xy[0], xy[1], self.plane_z])

    def floor_to_pixel(self, p_R):
        T_C_R = np.linalg.inv(self.T_R_C)
        pc = (T_C_R @ np.r_[np.asarray(p_R, float), 1.0])[:3]
        return self.cam.project(pc)[0] if pc[2] > 0 else None


class BlobDetector(Detector):
    """Saturated-colour blob detector (no ML). For tests and for bright
    items on a neutral floor; NOT a substitute for the garment model."""

    def __init__(self, mapper=None, min_area_px=150, sat_min=90):
        self.mapper = mapper
        self.min_area = min_area_px
        self.sat_min = sat_min

    def detect(self, frame=None):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = ((hsv[:, :, 1] >= self.sat_min) & (hsv[:, :, 2] >= 40)).astype(np.uint8)
        n, _, stats, _ = cv2.connectedComponentsWithStats(mask)
        out = []
        for k in range(1, n):
            x, y, w, h, a = stats[k]
            if a < self.min_area:
                continue
            out.append(Detection(position=np.zeros(3), label="item", confidence=min(1.0, a / 2000),
                                 bbox=(float(x), float(y), float(x + w), float(y + h))))
        return out


@dataclass
class _Track:
    id: str
    xy: np.ndarray
    label: str
    seen: int = 1
    extra: dict = field(default_factory=dict)


class ClawGarmentPerception(ItemPerception):
    def __init__(self, detector: Detector, camera, frame_fn, *, jaw_roi_px=None, match_radius_m=0.15,
                 min_confidence=0.3, roi_change_min=30.0, spot_radius_m=0.10, item_height_m=0.05,
                 marker_wait_s=2.0):
        """``frame_fn()`` -> BGR image from the claw (captured while still);
        ``jaw_roi_px`` (x1,y1,x2,y2) overrides the ROI projected from CAD."""
        self.det = detector
        self.cam = camera
        self.frame_fn = frame_fn
        self.jaw_roi_px = jaw_roi_px
        self.match_r = match_radius_m
        self.min_conf = min_confidence
        self.roi_change_min = roi_change_min
        self.spot_r = spot_radius_m
        self.item_h = item_height_m
        self.tracks: list[_Track] = []
        self.n = 0
        self.empty_ref = None
        self.target = None
        self.log: list[str] = []
        self.marker_wait_s = marker_wait_s
        self._yaw = None                    # last marker-derived heading of the claw in the room
        self.pose_source = None

    # -- geometry ----------------------------------------------------------
    def _view(self, ctx):
        """(image, mapper, T_R_B) at the current still pose.

        The marker pose is preferred. Low over the garment the marker is
        usually outside the camera's footprint, so then the claw position
        comes from the cable kinematics and the heading from the last marker
        pose (yaw is unobservable from cable lengths; the runner has waited
        for the claw to settle and approved the predicted tilt, so upright is assumed)."""
        sp, why = ctx.vision.still_pose(3, ctx.wait, max_wait_s=self.marker_wait_s)
        if sp is not None:
            T_R_B = ctx.T_R_M @ make_T(sp.R, sp.p)
            self._yaw = math.atan2(T_R_B[1, 0], T_R_B[0, 0])
            src = "marker"
        elif self._yaw is not None:
            p = ctx.model.pose_from_positions(ctx.co.positions())[0]
            T_R_B = make_T(rot_z(self._yaw), p)
            src = "kinematics"
        else:
            raise RuntimeError(f"no camera pose: {why}")
        self.pose_source = src
        img = self.frame_fn()
        return img, ClawFloorMapper(self.cam, T_R_B @ ctx.T_B_C), T_R_B

    def jaw_roi(self, ctx, T_R_B, mapper):
        """Image box where a held item appears: the CAD jaw point +/- the finger
        reach, projected into this camera (or the configured override)."""
        if self.jaw_roi_px is not None:
            return tuple(int(v) for v in self.jaw_roi_px)
        low = np.asarray(ctx.cfg.claw.lowest_point_body_m, float)
        r = 0.06
        pts = [(T_R_B @ np.r_[low + [dx, dy, dz], 1.0])[:3]
               for dx in (-r, r) for dy in (-r, r) for dz in (0.0, 0.1)]
        uv = np.array([p for p in (mapper.floor_to_pixel(q) for q in pts) if p is not None])
        w, h = self.cam.image_size
        x1, y1 = np.clip(uv.min(0), 0, [w - 1, h - 1])
        x2, y2 = np.clip(uv.max(0), 0, [w - 1, h - 1])
        return int(x1), int(y1), int(x2), int(y2)

    def jaw_core(self, ctx, T_R_B, mapper, radius_m=0.04):
        """(u, v, r_px): where a garment held in the jaws is CENTRED in the image
        (projected CAD jaw point) and a tolerance radius, equal to ``radius_m``
        at the jaw's own depth. A floor garment can overlap the generous jaw ROI
        in the image, but its centre is far from this point."""
        low = np.asarray(ctx.cfg.claw.lowest_point_body_m, float)
        p_R = (T_R_B @ np.r_[low, 1.0])[:3]
        uv = mapper.floor_to_pixel(p_R)
        if uv is None:
            return None
        depth = float((np.linalg.inv(mapper.T_R_C) @ np.r_[p_R, 1.0])[2])
        return float(uv[0]), float(uv[1]), radius_m * self.cam.fx / depth

    @staticmethod
    def _roi_stats(img, roi):
        """Jaw-region appearance RELATIVE to the ring of floor around it in the
        same frame (saturation mean, value mean, value spread), so floor
        texture or lighting changes between frames largely cancel."""
        h, w = img.shape[:2]
        x1, y1, x2, y2 = roi
        mx, my = (x2 - x1) // 2, (y2 - y1) // 2
        X1, Y1, X2, Y2 = max(0, x1 - mx), max(0, y1 - my), min(w, x2 + mx), min(h, y2 + my)
        hsv = cv2.cvtColor(img[Y1:Y2, X1:X2], cv2.COLOR_BGR2HSV).astype(float)
        inner = np.zeros(hsv.shape[:2], bool)
        inner[y1 - Y1:y2 - Y1, x1 - X1:x2 - X1] = True

        def st(m):
            return np.array([hsv[:, :, 1][m].mean(), hsv[:, :, 2][m].mean(), hsv[:, :, 2][m].std()])
        ring = st(~inner) if (~inner).any() else np.zeros(3)
        return st(inner) - ring

    def _detections(self, img, mapper, core=None):
        """Floor detections (room xy). ``core`` = ``jaw_core`` output: boxes
        centred on it are the garment in the jaws, not on the floor."""
        self.det.mapper = mapper
        out = []
        for d in self.det.detect(img):
            if d.confidence < self.min_conf or d.bbox is None:
                continue
            x1, y1, x2, y2 = d.bbox
            cu, cv_ = 0.5 * (x1 + x2), 0.5 * (y1 + y2)
            if core is not None and math.hypot(cu - core[0], cv_ - core[1]) <= core[2]:
                continue
            out.append((mapper.pixel_to_floor(cu, cv_), d.label, d.confidence))   # straight-down: box centre
        return out

    # -- ItemPerception --------------------------------------------------------
    def capture_empty_reference(self, ctx):
        img, mapper, T = self._view(ctx)
        self.empty_ref = self._roi_stats(img, self.jaw_roi(ctx, T, mapper))

    def note_target(self, item):
        self.target = item

    def scan(self, ctx):
        img, mapper, T = self._view(ctx)
        roi = self.jaw_roi(ctx, T, mapper)
        if self.empty_ref is None:
            self.empty_ref = self._roi_stats(img, roi)     # scan starts with the claw open and empty
        found = []
        tc = ctx.cfg.tasks
        hamper = None if tc.hamper_room_m is None else np.asarray(tc.hamper_room_m, float)
        for xy, label, conf in self._detections(img, mapper):      # scan starts with the claw empty
            if hamper is not None and np.linalg.norm(xy - hamper) <= tc.hamper_radius_m + 0.05:
                continue                                           # already delivered, not laundry to fetch
            tr = min(self.tracks, key=lambda t: np.linalg.norm(t.xy - xy), default=None)
            if tr is None or np.linalg.norm(tr.xy - xy) > self.match_r:
                self.n += 1
                tr = _Track(f"{label}-{self.n}", np.asarray(xy, float), label)
                self.tracks.append(tr)
            else:
                tr.xy = 0.5 * (tr.xy + xy)
                tr.seen += 1
            found.append(ItemSighting(tr.id, tr.xy.copy(), self.item_h, conf))
        self.log.append(f"scan: {len(found)} item(s)")
        return found

    def holding(self, ctx):
        img, mapper, T = self._view(ctx)
        roi = self.jaw_roi(ctx, T, mapper)
        if self.empty_ref is None:
            raise RuntimeError("no empty-claw reference captured")
        change = float(np.max(np.abs(self._roi_stats(img, roi) - self.empty_ref)))
        in_claw = change >= self.roi_change_min
        spot_clear = True
        if self.target is not None:
            spot_clear = not any(np.linalg.norm(xy - self.target.xy) <= self.spot_r
                                 for xy, _, _ in self._detections(img, mapper, self.jaw_core(ctx, T, mapper)))
        held = in_claw and spot_clear
        self.log.append(f"holding: roi change {change:.1f}, spot clear {spot_clear} -> {held}")
        return held, (0.9 if held else 0.1)

    def item_at(self, ctx, xy, radius):
        img, mapper, T = self._view(ctx)
        roi = self.jaw_roi(ctx, T, mapper)
        change = float(np.max(np.abs(self._roi_stats(img, roi) - self.empty_ref)))
        if change >= self.roi_change_min:
            self.log.append(f"delivery: claw region still occupied ({change:.1f})")
            return False
        # the claw is empty here, so a garment under the jaws IS the delivered one (no ROI exclusion)
        dets = self._detections(img, mapper)
        inside = any(np.linalg.norm(d - np.asarray(xy)) <= radius for d, _, _ in dets)
        outside = [d for d, _, _ in dets if np.linalg.norm(d - np.asarray(xy)) <= radius + 0.3
                   and np.linalg.norm(d - np.asarray(xy)) > radius]
        ok = inside or not outside
        self.log.append(f"delivery: inside {inside}, near-miss outside {len(outside)} -> {ok}")
        if ok and self.target is not None:
            self.tracks = [t for t in self.tracks if t.id != self.target.id]
        return ok
