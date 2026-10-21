"""Multi-sheet floor reference ("board"): layout, joint-PnP detector, survey.

Decision D26: the floor reference is nine US Letter sheets, one AprilTag
(36h11, ids 0..8, black square 150 mm) per sheet, laid out roughly in a 3x3
grid about 1 m across. The user does not place them exactly, so the robot
*surveys* the layout from the air.

Frame M (the marker frame everything else works in) is exactly the single-tag
convention of ``marker.py``: origin at the centre of tag 0 (``origin_id``), X/Y
along the printed tag axes (X right, Y up the page), +Z out of the printed
face. The floor is assumed flat, so every other tag is a planar pose
``(x, y, yaw)`` in M with z = 0.

Parts
-----
``FloorBoardLayout``  per-tag planar pose + covariance + surveyed flag, JSON.
``BoardDetector``     all tags in one frame -> ONE joint PnP over the corners of
                      every surveyed tag -> ``T_C_M`` as a ``MarkerObservation``
                      (so perception.py consumes it unchanged). Ambiguity rules
                      are marker.py's (``MarkerDetector.select_pose``). With a
                      single usable tag it *is* the single-tag detector.
``BoardSurvey``       incremental survey from frames: unsurveyed tags are placed
                      by intersecting their corner rays with the floor plane
                      using the frame's pose from the already-surveyed tags;
                      a tag is accepted after N consistent views, then a planar
                      bundle adjustment (tag poses + per-frame camera pose, tag 0
                      fixed, known tag size, optional gravity) refines
                      everything and gives per-tag sigma. Duplicate ids,
                      mis-scaled sheets and moved sheets are rejected with a
                      reason.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix

from ..frames import inv_T, make_T, matrix_to_rotvec, rotvec_to_matrix
from .marker import _FAMILIES, MarkerDetector, MarkerObservation

DEFAULT_IDS = tuple(range(9))
# Sheet pitch (centre to centre, m) of the printed 3x3 layout: the default of the layout instructions
# (tools/print_floor_board.py) and of the nominal layout below. Chosen so that >= 2 tags are in view when the claw rests
# on the floor (lens ~0.5 m up): verification/imu_removal_review.md measured 1 tag in 8 of 8 seeds at the old 0.42 m,
# 3-4 tags (1.0-2.0 mrad tilt) at 0.25 m; validated up to MAX_PITCH_M (0.30 gave 2 of 3 startups, 0.28 is the
# limit the review recommends).
DEFAULT_PITCH_M = 0.25
MAX_PITCH_M = 0.28


# ----------------------------------------------------------------- geometry
def tag_corners_local(edge_m: float) -> np.ndarray:
    """Black-square corners in the tag frame, OpenCV order TL, TR, BR, BL
    (identical to ``MarkerDetector.obj``)."""
    h = edge_m / 2
    return np.array([[-h, h, 0], [h, h, 0], [h, -h, 0], [-h, -h, 0]], float)


def planar_T(x: float, y: float, yaw: float) -> np.ndarray:
    c, s = math.cos(yaw), math.sin(yaw)
    T = np.eye(4)
    T[:2, :2] = [[c, -s], [s, c]]
    T[0, 3], T[1, 3] = x, y
    return T


def wrap_pi(a):
    return (np.asarray(a) + np.pi) % (2 * np.pi) - np.pi


def _mean_side(c) -> float:
    return float(np.mean([np.linalg.norm(c[i] - c[(i + 1) % 4]) for i in range(4)]))


# ------------------------------------------------------------------- layout
@dataclass
class TagPose:
    id: int
    x: float = float("nan")
    y: float = float("nan")
    yaw: float = float("nan")
    surveyed: bool = False
    cov: np.ndarray = field(default_factory=lambda: np.zeros((3, 3)))   # (x, y, yaw), m, m, rad
    n_obs: int = 0
    note: str = ""

    @property
    def sigma_xy_m(self) -> float:
        return float(math.sqrt(max(0.0, (self.cov[0, 0] + self.cov[1, 1]) / 2)))

    @property
    def sigma_yaw_rad(self) -> float:
        return float(math.sqrt(max(0.0, self.cov[2, 2])))


class FloorBoardLayout:
    """Planar poses of the board tags in the marker frame M. ``origin_id`` is
    fixed at the identity and defines M."""

    VERSION = 1

    def __init__(self, edge_m: float, ids=DEFAULT_IDS, *, family: str = "apriltag_36h11", origin_id: int = 0):
        if family not in _FAMILIES:
            raise ValueError(f"unsupported marker family {family}")
        ids = [int(i) for i in ids]
        if origin_id not in ids:
            raise ValueError("origin_id must be one of the board ids")
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate ids in layout")
        self.edge_m = float(edge_m)
        self.family = family
        self.origin_id = int(origin_id)
        self.tags: dict[int, TagPose] = {i: TagPose(i) for i in ids}
        self.tags[self.origin_id] = TagPose(self.origin_id, 0.0, 0.0, 0.0, True, np.zeros((3, 3)), 0, "origin")

    @staticmethod
    def nominal_positions(pitch_m: float = DEFAULT_PITCH_M, ids=DEFAULT_IDS, origin_id: int | None = None) -> dict:
        """{id: (x, y)} of the intended 3x3 grid (the layout page of the printout): ``origin_id`` (default the first id)
        in the middle, the others clockwise from the top-left corner. Only a nominal layout: the real positions are
        surveyed (BoardSurvey) because the user does not place the sheets exactly."""
        ids = [int(i) for i in ids]
        origin_id = ids[0] if origin_id is None else int(origin_id)
        order = [origin_id] + [i for i in ids if i != origin_id]
        ring = [(-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0)]    # page view: +Y up
        if len(order) > 9:
            raise ValueError("a 3x3 layout holds at most 9 sheets")
        pos = {order[0]: (0.0, 0.0)}
        for i, (gx, gy) in zip(order[1:], ring):
            pos[i] = (gx * float(pitch_m), gy * float(pitch_m))
        return pos

    @classmethod
    def nominal(cls, edge_m: float, pitch_m: float = DEFAULT_PITCH_M, ids=DEFAULT_IDS, *,
                family: str = "apriltag_36h11", origin_id: int = 0, sigma_xy_m: float = 0.02) -> "FloorBoardLayout":
        """Layout with every tag at its nominal grid position, flagged surveyed with a coarse sigma. For tests, the
        simulator and a first guess before the survey: do NOT use it for the absolute accuracy claims of a real board."""
        if pitch_m > MAX_PITCH_M + 1e-9:
            raise ValueError(f"pitch {pitch_m:.3f} m exceeds the validated maximum {MAX_PITCH_M:.2f} m")
        lay = cls(edge_m, ids, family=family, origin_id=origin_id)
        cov = np.diag([sigma_xy_m ** 2, sigma_xy_m ** 2, (sigma_xy_m / edge_m) ** 2])
        for i, (x, y) in cls.nominal_positions(pitch_m, ids, origin_id).items():
            if i != origin_id:
                lay.set_pose(i, x, y, 0.0, cov, 0, "nominal")
        return lay

    # -- queries
    @property
    def expected_ids(self) -> list:
        return sorted(self.tags)

    def surveyed_ids(self) -> list:
        return sorted(i for i, t in self.tags.items() if t.surveyed)

    def is_surveyed(self, i: int) -> bool:
        t = self.tags.get(i)
        return bool(t and t.surveyed)

    def pose(self, i: int):
        t = self.tags[i]
        return t.x, t.y, t.yaw

    def T_M_T(self, i: int) -> np.ndarray:
        return planar_T(*self.pose(i))

    def corners_M(self, i: int) -> np.ndarray:
        """(4, 3) black-square corners of tag ``i`` in M."""
        T = self.T_M_T(i)
        return tag_corners_local(self.edge_m) @ T[:3, :3].T + T[:3, 3]

    def set_pose(self, i, x, y, yaw, cov=None, n_obs=0, note="", surveyed=True):
        if i == self.origin_id:
            raise ValueError("the origin tag is fixed at the identity")
        if i not in self.tags:
            raise KeyError(f"tag {i} is not part of this board")
        self.tags[i] = TagPose(i, float(x), float(y), float(wrap_pi(yaw)), surveyed,
                               np.zeros((3, 3)) if cov is None else np.asarray(cov, float).copy(), int(n_obs), note)

    def clear(self, i):
        if i == self.origin_id:
            raise ValueError("the origin tag cannot be cleared")
        self.tags[i] = TagPose(i)

    # -- persistence
    def to_dict(self) -> dict:
        tags = []
        for i in self.expected_ids:
            t = self.tags[i]
            d = {"id": i, "surveyed": bool(t.surveyed), "n_obs": t.n_obs, "note": t.note}
            if t.surveyed:
                d.update(x=t.x, y=t.y, yaw=t.yaw, cov=np.asarray(t.cov).tolist(),
                         sigma_xy_m=t.sigma_xy_m, sigma_yaw_rad=t.sigma_yaw_rad)
            tags.append(d)
        return {"version": self.VERSION, "family": self.family, "edge_m": self.edge_m,
                "origin_id": self.origin_id, "tags": tags}

    @classmethod
    def from_dict(cls, d: dict) -> "FloorBoardLayout":
        if d.get("version") != cls.VERSION:
            raise ValueError(f"unsupported floor board layout version {d.get('version')!r}")
        ids = [int(t["id"]) for t in d["tags"]]
        lay = cls(d["edge_m"], ids, family=d.get("family", "apriltag_36h11"), origin_id=d.get("origin_id", 0))
        for t in d["tags"]:
            i = int(t["id"])
            if i == lay.origin_id or not t.get("surveyed"):
                continue
            lay.set_pose(i, t["x"], t["y"], t["yaw"], t.get("cov"), t.get("n_obs", 0), t.get("note", ""))
        return lay

    def save(self, path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path) -> "FloorBoardLayout":
        return cls.from_dict(json.loads(Path(path).read_text()))

    def copy(self) -> "FloorBoardLayout":
        return FloorBoardLayout.from_dict(self.to_dict())

    def extent_eff(self, ids) -> float:
        """sqrt(x-extent * y-extent) of the outer corners of ``ids`` in M (the
        same definition as the simulator's FloorBoard 'extent' mode)."""
        c = np.vstack([self.corners_M(i) for i in ids])
        return float(math.sqrt(np.ptp(c[:, 0]) * np.ptp(c[:, 1])))


# ----------------------------------------------------------------- detector
@dataclass
class BoardObservation(MarkerObservation):
    """A ``MarkerObservation`` plus board bookkeeping (still consumable as one)."""
    used_ids: list = field(default_factory=list)
    dropped: dict = field(default_factory=dict)         # id -> why it was not used
    unsurveyed_ids: list = field(default_factory=list)  # detected, not yet in the layout
    per_tag_rms_px: dict = field(default_factory=dict)
    duplicate_ids: list = field(default_factory=list)
    unexpected_ids: list = field(default_factory=list)


class BoardDetector:
    def __init__(self, layout: FloorBoardLayout, camera, *, min_side_px=40.0, max_reprojection_px=2.0,
                 ambiguity_ratio_min=3.0, border_px=4, continuity_rad=0.35, upright_rad=0.6, outlier_px=2.0,
                 corner_inflate_px=0.0, refine=True, corner_sigma_px=0.3, cov_inflate=1.3):
        """``corner_inflate_px``: move every detected corner this far outward from its
        quad's centre. 0 = trust the detector. cv2's sub-pixel refinement of small
        (~50 px) tags is biased inward by ~0.15 px, which scales the whole layout by
        ~0.4 %; a calibrated value removes it (see verification/floor_board_detector.md)."""
        self.layout = layout
        self.cam = camera
        self.inflate = float(corner_inflate_px)
        self.min_side_px = min_side_px
        self.border = border_px
        self.outlier_px = outlier_px
        d = cv2.aruco.getPredefinedDictionary(_FAMILIES[layout.family])
        params = cv2.aruco.DetectorParameters()
        params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        self.detector = cv2.aruco.ArucoDetector(d, params)
        # parameter holder + single-tag pose / ambiguity rules (shared with marker.py)
        self._sel = MarkerDetector(layout.family, layout.origin_id, layout.edge_m, camera, min_side_px=min_side_px,
                                   max_reprojection_px=max_reprojection_px, ambiguity_ratio_min=ambiguity_ratio_min,
                                   border_px=border_px, continuity_rad=continuity_rad, upright_rad=upright_rad,
                                   refine=refine, corner_sigma_px=corner_sigma_px, cov_inflate=cov_inflate)

    # -- raw detection
    def detect_tags(self, image):
        """-> (dets {id: (4,2) corners}, duplicate_ids, unexpected_ids). An id seen
        twice is dropped from ``dets`` (two sheets with one id cannot be trusted)."""
        gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        dets, dups, unexpected = {}, set(), []
        expected = set(self.layout.expected_ids)
        if ids is not None:
            for c, i in zip(corners, ids.ravel()):
                i = int(i)
                if i not in expected:
                    unexpected.append(i)
                elif i in dups:
                    continue
                elif i in dets:
                    dups.add(i)
                    del dets[i]
                else:
                    c = c.reshape(4, 2).astype(float)
                    if self.inflate:
                        v = c - c.mean(0)
                        c = c + self.inflate * v / np.linalg.norm(v, axis=1, keepdims=True)
                    dets[i] = c
        return dets, sorted(dups), sorted(unexpected)

    def detect(self, image, *, prev_T_C_M=None, up_in_cam=(0, 0, -1), up_sigma_rad=None, frame_id=None,
               capture_us=None, exclude=()) -> BoardObservation:
        dets, dups, unexpected = self.detect_tags(image)
        return self.pose_from_detections(dets, prev_T_C_M=prev_T_C_M, up_in_cam=up_in_cam, up_sigma_rad=up_sigma_rad,
                                         frame_id=frame_id, capture_us=capture_us, exclude=exclude, duplicate_ids=dups,
                                         unexpected_ids=unexpected)

    # -- pose from already detected corners
    def pose_from_detections(self, dets, *, prev_T_C_M=None, up_in_cam=(0, 0, -1), up_sigma_rad=None, frame_id=None,
                             capture_us=None, exclude=(), duplicate_ids=(), unexpected_ids=()) -> BoardObservation:
        lay = self.layout
        obs = BoardObservation(False, frame_id=frame_id, capture_us=capture_us, duplicate_ids=list(duplicate_ids),
                               unexpected_ids=list(unexpected_ids), dets={i: np.asarray(c, float) for i, c in dets.items()})
        exclude = set(exclude)
        obs.unsurveyed_ids = sorted(i for i in dets if not lay.is_surveyed(i))
        known = sorted(i for i in dets if lay.is_surveyed(i) and i not in exclude)
        for i in dets:
            if i in exclude and lay.is_surveyed(i):
                obs.dropped[i] = "excluded (flagged as moved / inconsistent)"
        for i in obs.duplicate_ids:
            if lay.is_surveyed(i):
                obs.dropped[i] = "duplicate id: two sheets carry this tag"
        if not known:
            obs.reason = "marker not found"
            return obs
        if len(known) == 1:
            return self._single(known[0], dets[known[0]], obs, prev_T_C_M, up_in_cam, up_sigma_rad)
        # several surveyed tags: use the ones that are large enough and fully inside the image
        usable = {}
        for i in known:
            c = dets[i]
            if _mean_side(c) < self.min_side_px:
                obs.dropped[i] = f"too small ({_mean_side(c):.0f} px)"
            elif not np.all(self.cam.in_image(c, margin=self.border)):
                obs.dropped[i] = "touches image border"
            else:
                usable[i] = c
        if not usable:
            obs.reason = "no usable tag: " + "; ".join(f"{i}: {r}" for i, r in obs.dropped.items())
            return obs
        if len(usable) == 1:
            i = next(iter(usable))
            return self._single(i, usable[i], obs, prev_T_C_M, up_in_cam, up_sigma_rad)
        ids = sorted(usable)
        while True:
            cands = self._solve(ids, usable)
            if not cands:
                obs.reason = "no solution in front of camera"
                return obs
            per = self._per_tag_rms(ids, usable, cands[0][1])
            worst = max(per, key=per.get)
            if per[worst] <= self.outlier_px or len(ids) <= 2:
                break
            obs.dropped[worst] = f"inconsistent with the other tags (rms {per[worst]:.1f} px): sheet moved?"
            ids.remove(worst)
            if len(ids) == 1:
                return self._single(ids[0], usable[ids[0]], obs, prev_T_C_M, up_in_cam, up_sigma_rad)
        obs.used_ids = ids
        obs.per_tag_rms_px = per
        obs.corners = np.vstack([usable[i] for i in ids])
        obs.side_px = float(np.mean([_mean_side(usable[i]) for i in ids]))
        obs.candidates = cands
        self._sel.select_pose(cands, obs, prev_T_C_M=prev_T_C_M, up_in_cam=up_in_cam, up_sigma_rad=up_sigma_rad)
        if obs.ok:
            obs.edge_eff = lay.extent_eff(ids)
            self._sel.attach_covariance(obs, np.vstack([lay.corners_M(i) for i in ids]))
        return obs

    # -- internals
    def _single(self, tid, c, obs, prev_T_C_M, up_in_cam, up_sigma_rad):
        """One tag: exactly the single-tag detector (marker.py), re-expressed in M."""
        T_M_T = self.layout.T_M_T(tid)
        prev = None if prev_T_C_M is None else prev_T_C_M @ T_M_T
        obs.corners = c
        self._sel.pose_from_corners(c, prev_T_C_M=prev, up_in_cam=up_in_cam, up_sigma_rad=up_sigma_rad, obs=obs)
        if tid != self.layout.origin_id:
            T_T_M = inv_T(T_M_T)
            if obs.T_C_M is not None:
                obs.T_C_M = obs.T_C_M @ T_T_M
            obs.candidates = [(e, T @ T_T_M) for e, T in obs.candidates]
        obs.used_ids = [tid]
        obs.edge_eff = None
        if obs.ok:                       # covariance of THIS tag's corners about the pose of M (includes the tag-to-M lever)
            self._sel.attach_covariance(obs, self.layout.corners_M(tid))
        return obs

    def _obj_img(self, ids, dets):
        obj = np.vstack([self.layout.corners_M(i) for i in ids])
        img = np.vstack([dets[i] for i in ids])
        return obj, img

    def _solve(self, ids, dets):
        obj, img = self._obj_img(ids, dets)
        K, dist = self.cam.K, self.cam.dist
        n, rvecs, tvecs, _ = cv2.solvePnPGeneric(obj, img, K, dist, flags=cv2.SOLVEPNP_IPPE)
        cands = []
        for k in range(n):
            rv, tv = cv2.solvePnPRefineLM(obj, img, K, dist, rvecs[k].copy(), tvecs[k].copy())
            T = make_T(rotvec_to_matrix(rv.ravel()), tv.ravel())
            if T[2, 3] <= 0:
                continue
            e = self._corner_errors(obj, img, T)
            cands.append((float(np.sqrt(np.mean(e ** 2))), T))
        cands.sort(key=lambda x: x[0])
        return cands

    def _corner_errors(self, obj, img, T):
        rv = matrix_to_rotvec(T[:3, :3])
        proj, _ = cv2.projectPoints(obj, rv, T[:3, 3], self.cam.K, self.cam.dist)
        return np.linalg.norm(proj.reshape(-1, 2) - img, axis=1)

    def _per_tag_rms(self, ids, dets, T):
        obj, img = self._obj_img(ids, dets)
        e = self._corner_errors(obj, img, T).reshape(len(ids), 4)
        return {i: float(np.sqrt(np.mean(e[k] ** 2))) for k, i in enumerate(ids)}


# ------------------------------------------------------- visibility queries
class BoardGeometry:
    """Which tags of a board are usable from a claw pose, and their corners: the queries the excitation design (and the
    simulator) need. ``corners``: (n, 4, 3) black-square corners in M; ``edge``: tag edge (m); ``span_mode`` as in
    ``sim.world.FloorBoard``. Built from a layout with :meth:`from_layout`."""

    span_mode = "extent"

    def __init__(self, corners, edge, span_mode="extent"):
        self.corners = np.asarray(corners, float)
        self.edge = float(edge)
        self.span_mode = span_mode

    @classmethod
    def from_layout(cls, layout: FloorBoardLayout, ids=None):
        ids = layout.surveyed_ids() if ids is None else list(ids)
        return cls(np.array([layout.corners_M(i) for i in ids]), layout.edge_m)

    def visible_tags(self, camera, T_B_C, T_M_B, *, min_side_px, margin_px=4):
        """Indices of the tags fully in view and at least ``min_side_px`` large."""
        T_C_M = inv_T(np.asarray(T_M_B, float) @ np.asarray(T_B_C, float))
        pc = self.corners @ T_C_M[:3, :3].T + T_C_M[:3, 3]                  # (n, 4, 3)
        ok = np.all(pc[:, :, 2] > 0.05, axis=1)
        out = []
        if not ok.any():
            return out
        idx = np.flatnonzero(ok)
        uv = camera.project(pc[idx].reshape(-1, 3)).reshape(len(idx), 4, 2)
        for j, k in enumerate(idx):
            if not np.all(camera.in_image(uv[j], margin_px)):
                continue
            side = np.mean([np.linalg.norm(uv[j][m] - uv[j][(m + 1) % 4]) for m in range(4)])
            if side >= min_side_px:
                out.append(int(k))
        return out

    def visible(self, camera, T_B_C, T_M_B, *, min_side_px, margin_px=4) -> bool:
        return bool(self.visible_tags(camera, T_B_C, T_M_B, min_side_px=min_side_px, margin_px=margin_px))

    def edge_eff_for(self, ks) -> float:
        c = self.corners[list(ks)].reshape(-1, 3)
        if self.span_mode == "rms":
            r = np.sqrt(np.mean(np.sum((c[:, :2] - c[:, :2].mean(0)) ** 2, axis=1)))
            return float(math.sqrt(2.0) * r)
        ex = c[:, 0].max() - c[:, 0].min()
        ey = c[:, 1].max() - c[:, 1].min()
        return float(math.sqrt(ex * ey))

    def edge_eff(self, camera, T_B_C, T_M_B, *, min_side_px, margin_px=4):
        """Effective span of the tags in view (the single tag edge when none is)."""
        ks = self.visible_tags(camera, T_B_C, T_M_B, min_side_px=min_side_px, margin_px=margin_px)
        return self.edge_eff_for(ks) if ks else self.edge

    def corners_for(self, ks) -> np.ndarray:
        """(4 len(ks), 3) corners of the tags ``ks`` in M."""
        return self.corners[list(ks)].reshape(-1, 3)

    def visible_corners(self, camera, T_B_C, T_M_B, *, min_side_px, margin_px=4):
        """Corners of the tags in view ((4 n, 3)), or None if none is."""
        ks = self.visible_tags(camera, T_B_C, T_M_B, min_side_px=min_side_px, margin_px=margin_px)
        return self.corners_for(ks) if ks else None


# --------------------------------------------------------- synthetic render
def render_board_view(cam, family, edge_m, poses, T_C_M, *, background=200, noise=2.0, blur=0.0, rng=None,
                      px_per_cell=16, supersample=2, quiet_cells=2):
    """Synthetic image of flat tags on the floor. ``poses``: {id: (x, y, yaw)} in M.
    Each tag is drawn with a white quiet zone; the black square edge is
    ``edge_m``. Used by tests and sims to exercise the real detector."""
    d = cv2.aruco.getPredefinedDictionary(_FAMILIES[family])
    bits = d.markerSize + 2
    side = bits * px_per_cell
    border = quiet_cells * px_per_cell
    full = side + 2 * border
    w, h = cam.image_size
    ss = int(supersample)
    big = np.full((h * ss, w * ss), float(background), np.float32)
    src = np.array([[-.5, -.5], [full - .5, -.5], [full - .5, full - .5], [-.5, full - .5]], np.float32)
    half = full * (edge_m / side) / 2
    corners_tag = np.array([[-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0]])
    for tid, (x, y, yaw) in poses.items():
        tag = cv2.aruco.generateImageMarker(d, int(tid), side, borderBits=1)
        canvas = np.full((full, full), 255, np.uint8)
        canvas[border:border + side, border:border + side] = tag
        T = planar_T(x, y, yaw)
        pts_m = corners_tag @ T[:3, :3].T + T[:3, 3]
        pts_c = pts_m @ T_C_M[:3, :3].T + T_C_M[:3, 3]
        if np.any(pts_c[:, 2] <= 0.01):
            continue
        dst = (cam.project(pts_c) + 0.5) * ss - 0.5
        H = cv2.getPerspectiveTransform(src, dst.astype(np.float32))
        warped = cv2.warpPerspective(canvas.astype(np.float32), H, (w * ss, h * ss), flags=cv2.INTER_LINEAR)
        mask = cv2.warpPerspective(np.ones_like(canvas, np.float32), H, (w * ss, h * ss), flags=cv2.INTER_NEAREST)
        big = np.where(mask > 0.5, warped, big)
    img = cv2.resize(big, (w, h), interpolation=cv2.INTER_AREA) if ss > 1 else big
    if blur > 0:
        img = cv2.GaussianBlur(img, (0, 0), blur)
    if noise > 0:
        rng = rng or np.random.default_rng(0)
        img = img + rng.normal(0, noise, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------- survey
@dataclass
class TagStatus:
    id: int
    state: str                      # origin | surveyed | pending | rejected | suspect | unseen
    reason: str = ""
    n_obs: int = 0
    sigma_xy_m: float = float("nan")
    sigma_yaw_rad: float = float("nan")
    spread_xy_m: float = float("nan")
    spread_yaw_rad: float = float("nan")
    rms_px: float = float("nan")
    edge_ratio: float = float("nan")    # measured black-square edge / edge_m

    def __str__(self):
        return (f"tag {self.id}: {self.state}" + (f" ({self.reason})" if self.reason else "") +
                (f" n={self.n_obs} sigma={self.sigma_xy_m * 1e3:.2f} mm / {math.degrees(self.sigma_yaw_rad):.2f} deg"
                 if self.state in ("surveyed", "suspect") and not math.isnan(self.sigma_xy_m) else ""))


@dataclass
class FrameReport:
    ok: bool                         # the frame yielded a camera pose from surveyed tags
    reason: str = ""
    used_ids: list = field(default_factory=list)
    dropped: dict = field(default_factory=dict)
    unsurveyed_ids: list = field(default_factory=list)
    accepted: list = field(default_factory=list)       # tags accepted by the update triggered by this frame
    duplicate_ids: list = field(default_factory=list)


@dataclass
class _Frame:
    idx: int
    frame_id: object
    dets: dict
    up: object                                  # world-up in camera coordinates (unit) or None
    T0: object = None                           # T_C_M from the surveyed tags
    key: object = None                          # surveyed set T0/est were computed for
    est: dict = field(default_factory=dict)     # unsurveyed id -> (x, y, yaw, scale)


class BoardSurvey:
    """Incremental survey of the board from camera frames. See module docstring.

    Typical use::

        lay = FloorBoardLayout(edge_m=0.150)
        survey = BoardSurvey(lay, camera)
        for img, up in frames:
            survey.add_image(img, up_in_cam=up)
        survey.finalize()
        lay.save("floor_board.json"); print(*survey.status().values(), sep="\\n")

    ``lay`` is updated in place as tags are accepted. Thresholds are
    configurable; the defaults suit ~0.3-0.5 px corner noise.
    """

    def __init__(self, layout: FloorBoardLayout, camera, *, detector: BoardDetector | None = None,
                 min_obs=8, spread_xy_m=0.003, spread_yaw_rad=0.015, sigma_xy_m=0.002, sigma_yaw_rad=0.006,
                 scale_tol=0.012, max_tag_rms_px=1.5, pixel_sigma=0.4, gravity_sigma_rad=0.01, use_gravity=True,
                 move_tol_m=0.006, prelim_spread_xy_m=0.06, retry_extra=4, suspect_strikes=3, max_ba_frames=80,
                 default_up_in_cam=(0, 0, -1), min_side_px=40.0, border_px=4):
        self.layout = layout
        self.cam = camera
        self.det = detector or BoardDetector(layout, camera, min_side_px=min_side_px, border_px=border_px)
        self.min_obs, self.spread_xy, self.spread_yaw = min_obs, spread_xy_m, spread_yaw_rad
        self.sigma_xy, self.sigma_yaw = sigma_xy_m, sigma_yaw_rad
        self.scale_tol, self.max_rms = scale_tol, max_tag_rms_px
        self.pixel_sigma, self.grav_sigma, self.use_gravity = pixel_sigma, gravity_sigma_rad, use_gravity
        # the spread / sigma / reprojection limits are quoted for 0.4 px corner noise and grow with pixel_sigma
        self._k = max(1.0, pixel_sigma / 0.4)
        self.move_tol, self.prelim_spread = move_tol_m, prelim_spread_xy_m
        self.retry_extra, self.suspect_strikes, self.max_ba_frames = retry_extra, suspect_strikes, max_ba_frames
        self.default_up = np.asarray(default_up_in_cam, float)
        self.min_side_px, self.border = min_side_px, border_px
        self.frames: list[_Frame] = []
        self._stat: dict[int, TagStatus] = {i: TagStatus(i, "unseen") for i in layout.expected_ids}
        self._stat[layout.origin_id].state = "origin"
        self._suspect: set = set()
        self._dups: set = set()
        self._strikes: dict = {}
        self._tried: dict = {}
        self._warnings: dict = {}
        self._local = tag_corners_local(layout.edge_m)

    # ------------------------------------------------------------- inputs
    def add_image(self, image, *, up_in_cam=None, frame_id=None, update=True) -> FrameReport:
        dets, dups, _ = self.det.detect_tags(image)
        return self.add_detections(dets, duplicate_ids=dups, up_in_cam=up_in_cam, frame_id=frame_id, update=update)

    def add_detections(self, dets, *, duplicate_ids=(), up_in_cam=None, frame_id=None, update=True) -> FrameReport:
        for i in duplicate_ids:
            self._dups.add(i)
            self._stat[i].state = "rejected"
            self._stat[i].reason = "duplicate id: two sheets carry the same tag"
        keep = {}
        for i, c in dets.items():
            if i not in self._stat or i in self._dups:
                continue
            c = np.asarray(c, float).reshape(4, 2)
            if _mean_side(c) < self.min_side_px or not np.all(self.cam.in_image(c, margin=self.border)):
                continue
            keep[i] = c
        up = None
        if up_in_cam is not None:
            up = np.asarray(up_in_cam, float)
            up = up / np.linalg.norm(up)
        rec = _Frame(len(self.frames), frame_id, keep, up)
        self.frames.append(rec)
        obs = self._pose_frame(rec, count_strikes=True)
        rep = FrameReport(obs.ok, obs.reason, list(obs.used_ids), dict(obs.dropped), list(obs.unsurveyed_ids),
                          duplicate_ids=list(duplicate_ids))
        if update:
            rep.accepted = self.update()
        return rep

    def reset_tag(self, tid: int):
        """Forget everything about a tag (e.g. after the user re-placed the sheet)."""
        if tid == self.layout.origin_id:
            raise ValueError("cannot reset the origin tag")
        for f in self.frames:
            f.dets.pop(tid, None)
            f.est.pop(tid, None)
            f.key = None
        self.layout.clear(tid)
        self._suspect.discard(tid)
        self._dups.discard(tid)
        self._strikes.pop(tid, None)
        self._tried.pop(tid, None)
        self._stat[tid] = TagStatus(tid, "unseen")

    # ------------------------------------------------------------- results
    def status(self) -> dict:
        out = {}
        for i, s in self._stat.items():
            t = self.layout.tags[i]
            if t.surveyed and s.state not in ("suspect", "origin"):
                s.state = "surveyed"
                s.sigma_xy_m, s.sigma_yaw_rad, s.n_obs = t.sigma_xy_m, t.sigma_yaw_rad, t.n_obs
            if s.state == "unseen":
                n = self._count_seen(i)
                if n:
                    s.state, s.reason, s.n_obs = "pending", f"seen in {n} frame(s), surveying", n
            out[i] = s
        return out

    def surveyed_count(self) -> int:
        return len(self.layout.surveyed_ids())

    def problems(self) -> dict:
        return {i: f"{s.state}: {s.reason}" for i, s in self.status().items() if s.state in ("rejected", "suspect")}

    # ------------------------------------------------------------- updates
    def update(self) -> list:
        """Accept every pending tag that now satisfies the criteria; returns the ids accepted."""
        accepted = []
        while True:
            self._refresh()
            cands = self._candidates()
            if not cands:
                break
            new = self._try_accept(cands)
            if not new:
                break
            accepted += new
        return accepted

    def refine(self) -> dict:
        """Bundle adjustment over all surveyed tags and stored frames (tag 0 fixed);
        updates the layout, flags tags that moved / are inconsistent. Returns diagnostics."""
        self._refresh()
        free = [i for i in self.layout.surveyed_ids() if i != self.layout.origin_id and i not in self._suspect]
        init = {i: self.layout.pose(i) for i in free}
        res = self._bundle(free, init)
        if res is None:
            return {}
        self._record(res, [], free)
        for i in list(free):
            ok, reason, hard = self._judge(i, res)
            if hard and not ok:
                self._flag_suspect(i, reason)
        self._invalidate()
        return {"rms_px": res["rms_px"], "n_frames": res["n_frames"], "per_tag": res["diag"]}

    def finalize(self) -> dict:
        self.update()
        return self.refine()

    # ------------------------------------------------------------ internals
    def _count_seen(self, i) -> int:
        return sum(1 for f in self.frames if i in f.dets)

    def _invalidate(self):
        for f in self.frames:
            f.key = None

    def _surveyed_key(self):
        lay = self.layout
        return (tuple(lay.surveyed_ids()), tuple(sorted(self._suspect)),
                tuple(round(v, 6) for i in lay.surveyed_ids() for v in lay.pose(i)))

    def _pose_frame(self, rec: _Frame, count_strikes=False):
        up = rec.up if rec.up is not None else self.default_up
        obs = self.det.pose_from_detections(rec.dets, up_in_cam=up, frame_id=rec.frame_id, exclude=self._suspect)
        rec.T0 = obs.T_C_M if obs.ok else None
        if count_strikes:
            for i in rec.dets:
                if not self.layout.is_surveyed(i) or i == self.layout.origin_id or i in self._suspect:
                    continue
                if i in obs.dropped and "inconsistent" in obs.dropped[i]:
                    self._strikes[i] = self._strikes.get(i, 0) + 1
                    if self._strikes[i] >= self.suspect_strikes:
                        self._flag_suspect(i, f"moved or inconsistent with the other tags in "
                                              f"{self._strikes[i]} consecutive frames (sheet kicked?)")
                elif i in obs.used_ids:
                    self._strikes[i] = 0
        return obs

    def _flag_suspect(self, i, reason):
        self._suspect.add(i)
        s = self._stat[i]
        s.state, s.reason = "suspect", reason
        self._invalidate()

    def _refresh(self):
        key = self._surveyed_key()
        for rec in self.frames:
            if rec.key == key:
                continue
            self._pose_frame(rec)
            rec.est = {}
            if rec.T0 is not None:
                for i, c in rec.dets.items():
                    if not self.layout.is_surveyed(i) and i not in self._dups:
                        e = self._plane_estimate(rec.T0, c)
                        if e is not None:
                            rec.est[i] = e
            rec.key = key

    def _plane_estimate(self, T_C_M, c):
        """Place a tag of known size on the floor plane from its corner rays and the
        camera pose: (x, y, yaw, scale) or None."""
        n = cv2.undistortPoints(np.asarray(c, np.float64).reshape(-1, 1, 2), self.cam.K, self.cam.dist).reshape(-1, 2)
        R, t = T_C_M[:3, :3], T_C_M[:3, 3]
        o = -R.T @ t
        d = np.c_[n, np.ones(len(n))] @ R
        if o[2] <= 0.05 or np.any(d[:, 2] >= -1e-3):
            return None
        s = -o[2] / d[:, 2]
        q = (o + s[:, None] * d)[:, :2]
        P = self._local[:, :2]
        qc = q.mean(0)
        qq = q - qc
        yaw = math.atan2(np.sum(P[:, 0] * qq[:, 1] - P[:, 1] * qq[:, 0]), np.sum(P[:, 0] * qq[:, 0] + P[:, 1] * qq[:, 1]))
        Rz = np.array([[math.cos(yaw), -math.sin(yaw)], [math.sin(yaw), math.cos(yaw)]])
        scale = float(np.sum(qq * (P @ Rz.T)) / np.sum(P * P))
        return float(qc[0]), float(qc[1]), yaw, scale

    @staticmethod
    def _summarise(vals):
        """vals: list of (x, y, yaw, scale) -> median pose + spreads."""
        a = np.asarray(vals, float)
        med = np.median(a[:, :3], axis=0)
        yaw_dev = wrap_pi(a[:, 2] - med[2])
        yaw = float(wrap_pi(med[2] + np.median(yaw_dev)))
        sxy = float(np.sqrt(np.mean(np.var(a[:, :2], axis=0, ddof=1)))) if len(a) > 1 else float("inf")
        syaw = float(np.std(yaw_dev, ddof=1)) if len(a) > 1 else float("inf")
        return (float(med[0]), float(med[1]), yaw), sxy, syaw, float(np.median(a[:, 3]))

    def _candidates(self):
        out = []
        by_tag: dict = {}
        for rec in self.frames:
            for i, e in rec.est.items():
                by_tag.setdefault(i, []).append(e)
        for i, vals in by_tag.items():
            st = self._stat[i]
            if i in self._dups or st.state == "rejected" and "duplicate" in st.reason:
                continue
            n = len(vals)
            st.n_obs = n
            if n < self.min_obs:
                st.state, st.reason = "pending", f"{n}/{self.min_obs} views with a camera pose from surveyed tags"
                continue
            pose, sxy, syaw, scale = self._summarise(vals)
            st.spread_xy_m, st.spread_yaw_rad, st.edge_ratio = sxy, syaw, scale
            if sxy > self.prelim_spread:
                st.state, st.reason = "pending", f"views disagree by {sxy * 1e3:.0f} mm (need a better camera pose)"
                continue
            if n < self._tried.get(i, 0) + self.retry_extra:
                continue
            out.append((i, pose))
        return out

    # -- bundle adjustment ---------------------------------------------------
    def _bundle(self, free, init, max_nfev=40):
        lay = self.layout
        origin = lay.origin_id
        fidx = {t: j for j, t in enumerate(free)}
        sel = []
        for rec in self.frames:
            if rec.T0 is None:
                continue
            ids = [t for t in rec.dets if t == origin or t in fidx]
            if len(ids) >= 2:
                sel.append((rec, ids))
        if len(sel) > self.max_ba_frames:
            pick = np.linspace(0, len(sel) - 1, self.max_ba_frames).round().astype(int)
            sel = [sel[k] for k in sorted(set(pick))]
        if not sel:
            return None
        nF, nT = len(sel), len(free)
        x0 = np.zeros(6 * nF + 3 * nT)
        for i, (rec, _) in enumerate(sel):
            x0[6 * i + 3:6 * i + 6] = rec.T0[:3, 3]
        for t, j in fidx.items():
            x0[6 * nF + 3 * j:6 * nF + 3 * j + 3] = init[t]
        grav = self.use_gravity and all(rec.up is not None for rec, _ in sel)
        sig = self.pixel_sigma
        # residual bookkeeping: rows are frame-major (its tags, then its gravity triple)
        rows = []                                  # (frame i, tag id, start row)
        fi_l, tj_l, pos_l, meas_l, pos_g = [], [], [], [], []
        r = 0
        for i, (rec, ids) in enumerate(sel):
            for t in ids:
                rows.append((i, t, r))
                fi_l.append(i)
                tj_l.append(fidx.get(t, -1) if t != origin else -1)
                pos_l.append(r)
                meas_l.append(rec.dets[t])
                r += 8
            if grav:
                pos_g.append(r)
                r += 3
        nres = r
        fi, tj = np.asarray(fi_l), np.asarray(tj_l)
        pos = np.asarray(pos_l)[:, None] + np.arange(8)[None]
        meas = np.asarray(meas_l)                                  # (E, 4, 2)
        up = np.asarray([rec.up for rec, _ in sel]) if grav else None
        pos_g = np.asarray(pos_g)[:, None] + np.arange(3)[None] if grav else None
        R0 = np.asarray([rec.T0[:3, :3] for rec, _ in sel])
        S = lil_matrix((nres, len(x0)), dtype=int)
        for (i, t, r0) in rows:
            S[r0:r0 + 8, 6 * i:6 * i + 6] = 1
            if t != origin:
                S[r0:r0 + 8, 6 * nF + 3 * fidx[t]:6 * nF + 3 * fidx[t] + 3] = 1
        if grav:
            for i in range(nF):
                S[pos_g[i, 0]:pos_g[i, 0] + 3, 6 * i:6 * i + 3] = 1
        Kc = self.cam.K
        d5 = np.zeros(5)
        dd = np.asarray(self.cam.dist, float).ravel()
        if np.any(dd[5:] != 0):
            raise ValueError("BoardSurvey supports the 5-parameter (k1 k2 p1 p2 k3) distortion model")
        d5[:min(5, len(dd))] = dd[:5]
        k1, k2, p1, p2, k3 = d5
        loc2 = self._local[:, :2]

        def cam_R(x):
            d = x[:6 * nF].reshape(nF, 6)[:, :3]
            th = np.linalg.norm(d, axis=1)
            small = th < 1e-9
            ths = np.where(small, 1.0, th)
            A = np.where(small, 1.0, np.sin(ths) / ths)
            B = np.where(small, 0.5, (1 - np.cos(ths)) / ths ** 2)
            Kx = np.zeros((nF, 3, 3))
            Kx[:, 0, 1], Kx[:, 0, 2], Kx[:, 1, 0] = -d[:, 2], d[:, 1], d[:, 2]
            Kx[:, 1, 2], Kx[:, 2, 0], Kx[:, 2, 1] = -d[:, 0], -d[:, 1], d[:, 0]
            R = np.eye(3)[None] + A[:, None, None] * Kx + B[:, None, None] * (Kx @ Kx)
            return R @ R0

        def fun(x):
            R = cam_R(x)
            t = x[:6 * nF].reshape(nF, 6)[:, 3:]
            tagp = np.vstack([x[6 * nF:].reshape(nT, 3), np.zeros((1, 3))])[tj]       # origin -> zeros (index -1)
            c, sn = np.cos(tagp[:, 2]), np.sin(tagp[:, 2])
            Pm = np.zeros((len(tj), 4, 3))
            Pm[:, :, 0] = c[:, None] * loc2[None, :, 0] - sn[:, None] * loc2[None, :, 1] + tagp[:, None, 0]
            Pm[:, :, 1] = sn[:, None] * loc2[None, :, 0] + c[:, None] * loc2[None, :, 1] + tagp[:, None, 1]
            Pc = np.einsum("eij,ekj->eki", R[fi], Pm) + t[fi][:, None, :]
            xn, yn = Pc[..., 0] / Pc[..., 2], Pc[..., 1] / Pc[..., 2]
            r2 = xn * xn + yn * yn
            rad = 1 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3
            xd = xn * rad + 2 * p1 * xn * yn + p2 * (r2 + 2 * xn * xn)
            yd = yn * rad + p1 * (r2 + 2 * yn * yn) + 2 * p2 * xn * yn
            u = Kc[0, 0] * xd + Kc[0, 1] * yd + Kc[0, 2]
            v = Kc[1, 1] * yd + Kc[1, 2]
            out = np.empty(nres)
            out[pos] = (np.stack([u, v], axis=-1) - meas).reshape(-1, 8) / sig
            if grav:
                out[pos_g] = (R[:, :, 2] - up) / self.grav_sigma
            return out

        res = least_squares(fun, x0, jac_sparsity=S.tocsr(), loss="soft_l1", f_scale=3.0, max_nfev=max_nfev,
                            x_scale=1.0, xtol=1e-10, ftol=1e-10, gtol=1e-10)
        x = res.x
        r_final = fun(x)
        chi2 = float(np.sum(r_final ** 2))
        dof = max(1, nres - len(x))
        J = res.jac.toarray()
        cov_all = np.linalg.pinv(J.T @ J, rcond=1e-12) * max(1.0, chi2 / dof)
        cams = {}
        Rfin = cam_R(x)
        for i, (rec, _) in enumerate(sel):
            cams[rec.idx] = make_T(Rfin[i], x[6 * i + 3:6 * i + 6])
        poses, covs, nobs = {}, {}, {}
        for t, j in fidx.items():
            p = x[6 * nF + 3 * j:6 * nF + 3 * j + 3]
            poses[t] = (float(p[0]), float(p[1]), float(wrap_pi(p[2])))
            sl = slice(6 * nF + 3 * j, 6 * nF + 3 * j + 3)
            covs[t] = cov_all[sl, sl]
            nobs[t] = sum(1 for _, ids in sel if t in ids)
        rms_tag = {}
        for (i, t, r0) in rows:
            rms_tag.setdefault(t, []).append(r_final[r0:r0 + 8] * sig)
        rms_px = {t: float(np.sqrt(np.mean(np.concatenate(v) ** 2) * 2)) for t, v in rms_tag.items()}   # per-corner euclid rms
        res_d = {"poses": poses, "cov": covs, "n_obs": nobs, "cams": cams, "rms_px_by_tag": rms_px,
                 "rms_px": float(np.sqrt(np.mean(np.concatenate([np.concatenate(v) for v in rms_tag.values()]) ** 2) * 2)),
                 "n_frames": nF, "diag": {}, "free": list(free), "frames": [rec for rec, _ in sel]}
        # per-tag spread of per-frame estimates against the BA camera poses
        for t in list(free) + [origin]:
            self._diag_tag(t, res_d)
        return res_d

    def _diag_tag(self, t, res):
        """Spread / scale of tag ``t``'s per-frame placements against the adjusted camera poses."""
        vals, frames = [], []
        for rec in res["frames"]:
            if t in rec.dets:
                e = self._plane_estimate(res["cams"][rec.idx], rec.dets[t])
                if e is not None:
                    vals.append(e)
                    frames.append(rec.idx)
        if len(vals) >= 3:
            pose, sxy, syaw, scale = self._summarise(vals)
            res["diag"][t] = {"spread_xy_m": sxy, "spread_yaw_rad": syaw, "edge_ratio": scale, "vals": vals,
                              "frames": frames}
        return res["diag"].get(t)

    def _step_change(self, vals, frames):
        """Best two-segment split of the per-frame (x, y) sequence -> (displacement, split frame) or None."""
        order = np.argsort(frames)
        xy = np.asarray(vals)[order][:, :2]
        fr = np.asarray(frames)[order]
        n = len(xy)
        best = None
        for k in range(3, n - 2):
            a, b = xy[:k], xy[k:]
            sse = np.sum((a - np.median(a, 0)) ** 2) + np.sum((b - np.median(b, 0)) ** 2)
            if best is None or sse < best[0]:
                best = (sse, k)
        if best is None:
            return None
        k = best[1]
        a, b = xy[:k], xy[k:]
        sa = np.sqrt(np.mean(np.var(a, 0)))
        sb = np.sqrt(np.mean(np.var(b, 0)))
        disp = float(np.linalg.norm(np.median(a, 0) - np.median(b, 0)))
        return disp, int(fr[k]), float(max(sa, sb))

    def _judge(self, t, res):
        """-> (ok, reason, hard). hard=True means the tag is inconsistent (reject), not merely under-observed."""
        d = res["diag"].get(t)
        if d is None:
            return False, "too few usable views", False
        if abs(d["edge_ratio"] - 1.0) > self.scale_tol:
            return False, (f"printed size differs from edge_m by {(d['edge_ratio'] - 1) * 100:+.1f} % "
                           f"(measured {d['edge_ratio'] * self.layout.edge_m * 1e3:.1f} mm vs "
                           f"{self.layout.edge_m * 1e3:.1f} mm): printer scaling, or edge_m mis-measured"), True
        if d["spread_xy_m"] > self.spread_xy * self._k or d["spread_yaw_rad"] > self.spread_yaw * self._k:
            sc = self._step_change(d["vals"], d["frames"])
            if sc and sc[0] > self.move_tol and sc[2] < 0.6 * d["spread_xy_m"]:
                return False, (f"sheet moved ~{sc[0] * 1e3:.0f} mm between observations (step at frame {sc[1]}); "
                               f"re-place it and reset_tag({t})"), True
            return False, (f"inconsistent observations (spread {d['spread_xy_m'] * 1e3:.1f} mm, "
                           f"{math.degrees(d['spread_yaw_rad']):.2f} deg): sheet not flat, moving, or glare"), True
        rms = res["rms_px_by_tag"].get(t, 0.0)
        if rms > self.max_rms * self._k:
            return False, f"reprojection {rms:.2f} px > {self.max_rms * self._k:.2f} px (sheet curled / not flat?)", True
        return True, "", False

    def _record(self, res, accepted_ids, free):
        lay = self.layout
        for t in free:
            if t in self._suspect:
                continue
            s = self._stat[t]
            d = res["diag"].get(t, {})
            if t in accepted_ids or lay.is_surveyed(t):
                lay.set_pose(t, *res["poses"][t], cov=res["cov"][t], n_obs=res["n_obs"][t])
                s.state, s.reason = "surveyed", ""
                s.n_obs = res["n_obs"][t]
                s.sigma_xy_m, s.sigma_yaw_rad = lay.tags[t].sigma_xy_m, lay.tags[t].sigma_yaw_rad
                s.spread_xy_m = d.get("spread_xy_m", float("nan"))
                s.spread_yaw_rad = d.get("spread_yaw_rad", float("nan"))
                s.edge_ratio = d.get("edge_ratio", float("nan"))
                s.rms_px = res["rms_px_by_tag"].get(t, float("nan"))
        o = self.layout.origin_id
        so = self._stat[o]
        so.rms_px = res["rms_px_by_tag"].get(o, float("nan"))
        so.edge_ratio = res["diag"].get(o, {}).get("edge_ratio", float("nan"))
        if so.rms_px > self.max_rms * self._k * 1.5:
            so.reason = (f"origin sheet reprojection {so.rms_px:.2f} px: it moved relative to the others "
                         f"(or the others moved); the marker frame is suspect")
            so.state = "suspect"
        elif so.state == "suspect" and so.rms_px <= self.max_rms * self._k:
            so.state, so.reason = "origin", ""
        if not (abs(so.edge_ratio - 1) > self.scale_tol and so.state == "origin"):
            self._warnings.pop(("origin_scale", o), None)
        else:
            self._warn(("origin_scale", o), f"sheet {o} (the origin) reads {so.edge_ratio * 100:.1f} % of edge_m while the other sheets "
                       f"define the scale: re-measure its black square and check the print scale")

    @property
    def warnings(self) -> list:
        """Non-fatal findings (e.g. the origin sheet printed at a different scale)."""
        return list(self._warnings.values())

    def _warn(self, key, msg):
        self._warnings[key] = msg

    def _try_accept(self, cands):
        lay = self.layout
        origin = lay.origin_id
        base = [i for i in lay.surveyed_ids() if i != origin and i not in self._suspect]
        pending = dict(cands)                    # id -> provisional pose
        for i in pending:
            self._tried[i] = self._stat[i].n_obs
        accepted, removed = [], {}
        res = None
        for _ in range(len(cands) + 2):
            free = base + list(pending)
            init = {i: lay.pose(i) for i in base}
            init.update(pending)
            res = self._bundle(free, init)
            if res is None:
                break
            verdict = {}
            for i in pending:
                verdict[i] = self._judge(i, res)
                s = self._stat[i]
                d = res["diag"].get(i, {})
                s.spread_xy_m = d.get("spread_xy_m", s.spread_xy_m)
                s.spread_yaw_rad = d.get("spread_yaw_rad", s.spread_yaw_rad)
                s.edge_ratio = d.get("edge_ratio", s.edge_ratio)
                s.rms_px = res["rms_px_by_tag"].get(i, float("nan"))
                s.n_obs = res["n_obs"].get(i, s.n_obs)
            hard_fail = [i for i, v in verdict.items() if v[2] and not v[0]]
            if hard_fail:
                # remove the worst offender and re-solve so it cannot disturb the others
                worst = max(hard_fail, key=lambda i: res["rms_px_by_tag"].get(i, 0.0) + self._stat[i].spread_xy_m * 1e3)
                removed[worst] = verdict[worst][1]
                self._stat[worst].state, self._stat[worst].reason = "rejected", verdict[worst][1]
                del pending[worst]
                continue
            # no hard failures: tags that are consistent and precise enough are accepted
            for i in list(pending):
                if verdict[i][0]:
                    cv = res["cov"][i]
                    sxy = math.sqrt(max(0.0, (cv[0, 0] + cv[1, 1]) / 2))
                    syaw = math.sqrt(max(0.0, cv[2, 2]))
                    s = self._stat[i]
                    s.sigma_xy_m, s.sigma_yaw_rad = sxy, syaw
                    if res["n_obs"].get(i, 0) < self.min_obs:
                        s.state, s.reason = "pending", f"{res['n_obs'].get(i, 0)}/{self.min_obs} views in the adjustment"
                    elif sxy > self.sigma_xy * self._k or syaw > self.sigma_yaw * self._k:
                        s.state, s.reason = ("pending", f"position sigma {sxy * 1e3:.2f} mm / {math.degrees(syaw):.2f} deg "
                                                        f"still above {self.sigma_xy * self._k * 1e3:.1f} mm / "
                                                        f"{math.degrees(self.sigma_yaw * self._k):.2f} deg: needs more views")
                    else:
                        accepted.append(i)
                else:
                    self._stat[i].state, self._stat[i].reason = "pending", verdict[i][1]
            self._record(res, accepted, base + accepted)
            # surveyed tags that went bad in this adjustment
            for i in base:
                ok, reason, hard = self._judge(i, res)
                if hard and not ok:
                    self._flag_suspect(i, reason)
            # a rejected tag is judged against the cameras of the adjustment that did NOT include it
            for t in removed:
                d = self._diag_tag(t, res)
                if d is not None:
                    self._stat[t].reason = self._judge(t, res)[1] or removed[t]
                    self._stat[t].edge_ratio = d["edge_ratio"]
                    self._stat[t].spread_xy_m = d["spread_xy_m"]
            self._invalidate()
            break
        return accepted
