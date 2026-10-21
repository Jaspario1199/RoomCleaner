"""AprilTag/ArUco detection and pose with explicit ambiguity handling.

Planar squares have two pose solutions (IPPE). Rules:

1. Reject detections that are too small, touch the image border, or whose
   best reprojection RMS exceeds ``max_reprojection_px``.
2. Accept the best solution outright if the second solution's error is at
   least ``ambiguity_ratio_min`` times larger.
3. Otherwise disambiguate with priors: temporal continuity with the last
   accepted pose, and the upright prior (marker lying on the floor, claw
   hanging upright -> the marker normal points back toward the camera).
4. If the priors do not separate the candidates clearly, reject the frame and
   say why. A rejected frame is data; a guessed pose is not.

Pose refinement and per-frame covariance (D27 follow-up, verification/imu_removal_review.md F1, F4, F9)
-------------------------------------------------------------------------------------------------------
* Each IPPE candidate is polished with Levenberg-Marquardt (``cv2.solvePnPRefineLM``) before the candidates are
  ranked; IPPE alone is several times noisier in tilt than the maximum-likelihood pose when the tag is seen nearly
  face-on (55 mrad against 10 mrad at 0.46 m).
* Every accepted frame carries its own 6x6 pose covariance (``MarkerObservation.pose_cov``): the Cramer-Rao bound of
  the pose from the corner reprojection Jacobian for the corners actually used, i.e. it depends on range, tag size,
  focal length, the corner noise in px and the number of tags/corners in view. It is expressed for the perturbation
  ``R' = exp(dr) R, t' = t + dt`` of ``T_C_M`` (``dr``, ``dt`` in camera axes). :func:`claw_cov_from_pose` propagates it
  to the claw origin (the lever arm is the marker-to-claw vector, so the error is anisotropic: mostly horizontal for a
  camera looking down) and to the claw's roll/pitch.

Output pose conventions follow frames.py: ``T_C_M`` maps marker -> camera.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np

from ..frames import inv_T, make_T, matrix_to_rotvec, rotvec_to_matrix

_FAMILIES = {
    "apriltag_36h11": cv2.aruco.DICT_APRILTAG_36h11,
    "apriltag_25h9": cv2.aruco.DICT_APRILTAG_25h9,
    "aruco_4x4_50": cv2.aruco.DICT_4X4_50,
    "aruco_6x6_250": cv2.aruco.DICT_6X6_250,
}


def skew(v) -> np.ndarray:
    v = np.asarray(v, float)
    return np.array([[0.0, -v[2], v[1]], [v[2], 0.0, -v[0]], [-v[1], v[0], 0.0]])


def pose_covariance(obj_M, T_C_M, K, corner_sigma_px: float, inflate: float = 1.0) -> np.ndarray:
    """Cramer-Rao covariance (6x6) of the pose of M from iid corner noise ``corner_sigma_px`` (per image coordinate).

    ``obj_M``: (n, 3) corner coordinates in M (all corners used by the pose: 4 for one tag, 4 per tag for a board).
    Parameters ``x = (dr, dt)``: ``R' = exp(dr) R``, ``t' = t + dt`` (camera axes), so a corner moves by
    ``dX = -[R P]x dr + dt`` in the camera frame; the pinhole projection (``K`` fx, fy) gives the Jacobian.
    ``inflate`` scales the standard deviation (margin for the non-Gaussian tail of the ML estimate near face-on)."""
    P = np.asarray(obj_M, float).reshape(-1, 3)
    R, t = np.asarray(T_C_M, float)[:3, :3], np.asarray(T_C_M, float)[:3, 3]
    RP = P @ R.T
    X = RP + t
    fx, fy = float(K[0, 0]), float(K[1, 1])
    n = len(P)
    Z = X[:, 2]
    Ju = np.zeros((n, 2, 3))
    Ju[:, 0, 0] = fx / Z
    Ju[:, 0, 2] = -fx * X[:, 0] / Z ** 2
    Ju[:, 1, 1] = fy / Z
    Ju[:, 1, 2] = -fy * X[:, 1] / Z ** 2
    S = np.zeros((n, 3, 3))                                  # skew(R P_i)
    S[:, 0, 1], S[:, 0, 2] = -RP[:, 2], RP[:, 1]
    S[:, 1, 0], S[:, 1, 2] = RP[:, 2], -RP[:, 0]
    S[:, 2, 0], S[:, 2, 1] = -RP[:, 1], RP[:, 0]
    J = np.zeros((n, 2, 6))
    J[:, :, :3] = -np.einsum("nij,njk->nik", Ju, S)
    J[:, :, 3:] = Ju
    J = J.reshape(2 * n, 6)
    A = J.T @ J
    try:
        C = np.linalg.inv(A)
    except np.linalg.LinAlgError:
        C = np.linalg.pinv(A)
    return (float(inflate) * float(corner_sigma_px)) ** 2 * 0.5 * (C + C.T)


def claw_cov_from_pose(pose_cov, T_C_M, T_B_C, *, floor_rad: float = 0.0):
    """Propagate a pose covariance to the claw: ``(cov_p, cov_att)`` in the marker frame M.

    ``p_M = R^T (p_CB - t)`` with ``p_CB`` the body origin in camera axes, so ``dp = R^T ([a]x dr - dt)`` with
    ``a = p_CB - t`` (marker origin to body origin, camera axes): the lever of a tilt error is the marker-to-claw
    vector, not an isotropic ball. ``dtheta_M = -R^T dr`` is the orientation error of the body. ``floor_rad`` adds an
    independent attitude error (unmodelled systematics) on all three axes."""
    C = np.array(pose_cov, float)
    if floor_rad:
        C[:3, :3] += floor_rad ** 2 * np.eye(3)
    T_C_M = np.asarray(T_C_M, float)
    R, t = T_C_M[:3, :3], T_C_M[:3, 3]
    p_CB = inv_T(np.asarray(T_B_C, float))[:3, 3]
    a = p_CB - t
    Jp = R.T @ np.hstack([skew(a), -np.eye(3)])
    Ja = np.hstack([-R.T, np.zeros((3, 3))])
    return Jp @ C @ Jp.T, Ja @ C @ Ja.T


def roll_pitch_sigma(cov_att) -> float:
    """1-sigma of the claw's roll or pitch (x, y of M) from an orientation covariance in M."""
    return float(math.sqrt(max(0.0, (cov_att[0, 0] + cov_att[1, 1]) / 2)))


@dataclass
class MarkerObservation:
    ok: bool
    reason: str = ""
    T_C_M: np.ndarray | None = None
    rms_px: float = np.nan
    ambiguity_ratio: float = np.nan
    side_px: float = 0.0
    corners: np.ndarray | None = None
    candidates: list = field(default_factory=list)
    frame_id: int | None = None
    capture_us: float | None = None
    edge_eff: float | None = None          # span of the tag set used (marker board), else None
    imu_rp: tuple | None = None            # roll/pitch sampled with this frame: OPTIONAL gravity fusion (claw.imu), unused (D27)
    pose_cov: np.ndarray | None = None     # 6x6 (dr, dt) covariance of T_C_M in camera axes (see module docstring); None = legacy source
    anchor_M: np.ndarray | None = None     # centroid of the corners used, in M (the point whose camera-frame position is best known)
    n_tags: int = 1                        # tags whose corners entered the pose

    def sigma_cam(self, cam_fx: float, edge_m: float, pixel_sigma=0.3) -> np.ndarray:
        """Rough 1-sigma of the marker position in the camera frame (m):
        lateral ~ s*z/f, depth ~ s*z^2/(f*edge)."""
        z = float(self.T_C_M[2, 3])
        lat = pixel_sigma * z / cam_fx
        dep = pixel_sigma * z * z / (cam_fx * edge_m) * 2
        return np.array([lat, lat, dep])


class MarkerDetector:
    def __init__(self, family: str, marker_id: int, edge_m: float, camera, *,
                 min_side_px=40.0, max_reprojection_px=2.0, ambiguity_ratio_min=3.0,
                 border_px=4, continuity_rad=0.35, upright_rad=0.6, refine=True, corner_sigma_px=0.3,
                 cov_inflate=1.3):
        """``refine``: Levenberg-Marquardt polish of the IPPE candidates (False = the old IPPE-only behaviour).
        ``corner_sigma_px`` / ``cov_inflate``: corner noise and the margin on its Cramer-Rao standard deviation used
        for the per-frame ``pose_cov`` (see the module docstring)."""
        if family not in _FAMILIES:
            raise ValueError(f"unsupported marker family {family}")
        self.dict = cv2.aruco.getPredefinedDictionary(_FAMILIES[family])
        params = cv2.aruco.DetectorParameters()
        params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        self.detector = cv2.aruco.ArucoDetector(self.dict, params)
        self.id = marker_id
        self.edge = edge_m
        self.cam = camera
        self.min_side_px = min_side_px
        self.max_rms = max_reprojection_px
        self.ratio_min = ambiguity_ratio_min
        self.border = border_px
        self.continuity_rad = continuity_rad
        self.upright_rad = upright_rad
        self.refine = bool(refine)
        self.corner_sigma_px = float(corner_sigma_px)
        self.cov_inflate = float(cov_inflate)
        h = edge_m / 2
        # OpenCV corner order: top-left, top-right, bottom-right, bottom-left
        self.obj = np.array([[-h, h, 0], [h, h, 0], [h, -h, 0], [-h, -h, 0]], np.float32)

    def detect(self, image, *, prev_T_C_M=None, up_in_cam=(0, 0, -1), up_sigma_rad=None, frame_id=None,
               capture_us=None):
        gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        obs = MarkerObservation(False, frame_id=frame_id, capture_us=capture_us)
        if ids is None or self.id not in ids.ravel():
            obs.reason = "marker not found"
            return obs
        c = corners[int(np.where(ids.ravel() == self.id)[0][0])].reshape(4, 2).astype(np.float64)
        obs.corners = c
        return self.pose_from_corners(c, prev_T_C_M=prev_T_C_M, up_in_cam=up_in_cam, up_sigma_rad=up_sigma_rad,
                                      obs=obs)

    def pose_from_corners(self, c, *, prev_T_C_M=None, up_in_cam=(0, 0, -1), up_sigma_rad=None, obs=None):
        """``up_in_cam``: world-up direction in camera coordinates (the floor
        marker's normal should match it). From a gravity sensor when one is fitted (D27: the claw has none);
        otherwise from the camera mount assuming an upright claw. ``None`` disables the
        prior. ``up_sigma_rad`` defaults to the detector's upright tolerance."""
        obs = obs or MarkerObservation(False, corners=c)
        side = float(np.mean([np.linalg.norm(c[i] - c[(i + 1) % 4]) for i in range(4)]))
        obs.side_px = side
        if side < self.min_side_px:
            obs.reason = f"marker too small ({side:.0f} px)"
            return obs
        if not np.all(self.cam.in_image(c, margin=self.border)):
            obs.reason = "marker touches image border"
            return obs
        obj64 = self.obj.astype(np.float64)
        img64 = c.astype(np.float64)
        n, rvecs, tvecs, errs = cv2.solvePnPGeneric(obj64, img64, self.cam.K, self.cam.dist,
                                                     flags=cv2.SOLVEPNP_IPPE_SQUARE)
        cands = []
        for k in range(n):
            rv, tv, err = rvecs[k], tvecs[k], float(np.ravel(errs)[k])
            if self.refine:
                rv, tv = cv2.solvePnPRefineLM(obj64, img64, self.cam.K, self.cam.dist, rv.copy(), tv.copy())
                proj, _ = cv2.projectPoints(obj64, rv, tv, self.cam.K, self.cam.dist)
                err = float(np.sqrt(np.mean(np.sum((proj.reshape(-1, 2) - img64) ** 2, axis=1))))
            T = make_T(rotvec_to_matrix(rv.ravel()), tv.ravel())
            if T[2, 3] <= 0:
                continue
            cands.append((err, T))
        cands.sort(key=lambda x: x[0])
        if self.refine and len(cands) > 1:
            # LM from the second IPPE solution often falls into the same minimum: then there is ONE maximum-likelihood
            # pose, not an ambiguity (a flip that is a real local minimum keeps its own, different, pose and error)
            dpos = np.linalg.norm(cands[0][1][:3, 3] - cands[1][1][:3, 3])
            drot = np.linalg.norm(matrix_to_rotvec(cands[0][1][:3, :3].T @ cands[1][1][:3, :3]))
            if dpos < 5e-4 and drot < 2e-3:
                cands = cands[:1]
        obs.candidates = cands
        if not cands:
            obs.reason = "no solution in front of camera"
            return obs
        obs = self.select_pose(cands, obs, prev_T_C_M=prev_T_C_M, up_in_cam=up_in_cam, up_sigma_rad=up_sigma_rad)
        if obs.ok:
            self.attach_covariance(obs, self.obj)
        return obs

    def attach_covariance(self, obs, obj_M):
        """Per-frame pose covariance from the corners used (``obj_M``: (n, 3) in M) at the accepted pose."""
        obj_M = np.asarray(obj_M, float).reshape(-1, 3)
        obs.pose_cov = pose_covariance(obj_M, obs.T_C_M, self.cam.K, self.corner_sigma_px, self.cov_inflate)
        obs.anchor_M = obj_M.mean(axis=0)
        obs.n_tags = len(obj_M) // 4
        return obs
    def select_pose(self, cands, obs, *, prev_T_C_M=None, up_in_cam=(0, 0, -1), up_sigma_rad=None):
        """Accept / disambiguate / reject sorted ``[(rms_px, T_C_M), ...]`` pose
        candidates (rules 1-4 in the module docstring). Shared with the
        multi-tag board detector (vision/board.py)."""
        best_err, best_T = cands[0]
        obs.rms_px = best_err
        if best_err > self.max_rms:
            obs.reason = f"reprojection {best_err:.2f} px > {self.max_rms}"
            return obs
        ratio = cands[1][0] / max(best_err, 1e-9) if len(cands) > 1 else np.inf
        obs.ambiguity_ratio = ratio
        if ratio >= self.ratio_min:
            obs.ok, obs.T_C_M, obs.reason = True, best_T, "unambiguous"
            return obs
        # --- ambiguous: use priors
        scores = []
        for err, T in cands[:2]:
            s = 0.0
            if prev_T_C_M is not None:
                d = np.linalg.norm(matrix_to_rotvec(T[:3, :3].T @ prev_T_C_M[:3, :3]))
                s += d / self.continuity_rad
            if up_in_cam is not None:
                # the floor marker's +Z, seen from the camera, must match world-up
                up = np.asarray(up_in_cam, float)
                up = up / np.linalg.norm(up)
                ang = float(np.arccos(np.clip(T[:3, 2] @ up, -1, 1)))
                s += ang / (up_sigma_rad or self.upright_rad)
            scores.append(s)
        if prev_T_C_M is None and up_in_cam is None:
            obs.reason = f"ambiguous (ratio {ratio:.2f}) and no prior"
            return obs
        i_best = int(np.argmin(scores))
        if abs(scores[0] - scores[1]) < 0.5:
            # both candidates equally plausible: only accept if they agree closely
            dpos = np.linalg.norm(cands[0][1][:3, 3] - cands[1][1][:3, 3])
            drot = np.linalg.norm(matrix_to_rotvec(cands[0][1][:3, :3].T @ cands[1][1][:3, :3]))
            if dpos < 0.003 and drot < 0.02:
                obs.ok, obs.T_C_M, obs.reason = True, cands[0][1], "ambiguous-but-equivalent"
            else:
                obs.reason = f"ambiguous (ratio {ratio:.2f}); priors do not separate candidates"
            return obs
        obs.ok, obs.T_C_M, obs.reason = True, cands[i_best][1], "disambiguated by prior"
        obs.rms_px = cands[i_best][0]
        return obs


def claw_pose_in_marker(T_C_M: np.ndarray, T_B_C: np.ndarray) -> np.ndarray:
    """T_M_B = T_M_C @ T_C_B  (marker <- camera <- body)."""
    return inv_T(T_C_M) @ inv_T(T_B_C)


def render_marker_view(cam, family, marker_id, edge_m, T_C_M, *, background=200, noise=2.0,
                       blur=0.0, rng=None, px_per_cell=40):
    """Synthetic camera image of a flat marker (with white border) at pose T_C_M.
    Used by tests and the simulator to exercise the real detector."""
    d = cv2.aruco.getPredefinedDictionary(_FAMILIES[family])
    bits = d.markerSize + 2
    side = bits * px_per_cell
    tag = cv2.aruco.generateImageMarker(d, marker_id, side, borderBits=1)
    border = 2 * px_per_cell
    canvas = np.full((side + 2 * border, side + 2 * border), 255, np.uint8)
    canvas[border:border + side, border:border + side] = tag
    # canvas pixel -> marker metres (tag edge = detected black square edge)
    s = edge_m / side
    full = canvas.shape[0]
    src = np.array([[0, 0], [full, 0], [full, full], [0, full]], np.float32)
    half = full * s / 2
    pts_m = np.array([[-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0]])
    pts_c = (T_C_M[:3, :3] @ pts_m.T).T + T_C_M[:3, 3]
    if np.any(pts_c[:, 2] <= 0.01):
        return np.full((cam.image_size[1], cam.image_size[0]), background, np.uint8)
    dst = cam.project(pts_c).astype(np.float32)
    H = cv2.getPerspectiveTransform(src, dst)
    w, h = cam.image_size
    img = cv2.warpPerspective(canvas, H, (w, h), flags=cv2.INTER_LINEAR, borderValue=background)
    if blur > 0:
        img = cv2.GaussianBlur(img, (0, 0), blur)
    if noise > 0:
        rng = rng or np.random.default_rng(0)
        img = np.clip(img.astype(float) + rng.normal(0, noise, img.shape), 0, 255).astype(np.uint8)
    return img


def claw_position_cov(obs: MarkerObservation, T_B_C: np.ndarray, cam_fx: float, edge_m: float, *,
                      pixel_sigma=0.3, rot_sigma_rad=None, floor_rad: float = 0.0) -> np.ndarray:
    """Covariance (marker frame, m^2) of the claw body origin from one detection.

    * Observation with a per-frame ``pose_cov`` (this module's detectors, the board detector, the simulator): the
      covariance is the full propagation of the pose covariance, lever arm included (:func:`claw_cov_from_pose`);
      nothing else is to be added.
    * Legacy observation without one: marker-position error in the camera frame (lateral/depth, see ``sigma_cam``)
      rotated into the marker frame. The orientation-error lever is NOT included here any more (it used to add
      ``(rot_sigma * |camera -> body|)^2`` on top of ``perception.VisionSource``'s ``(rot_sigma * |marker -> body|)^2``,
      the same rotation error counted twice; the camera-to-body part is ~1-2 % of the variance): the caller adds the
      single marker-to-body lever. ``rot_sigma_rad`` is accepted for compatibility and unused.
    """
    if getattr(obs, "pose_cov", None) is not None:
        return claw_cov_from_pose(obs.pose_cov, obs.T_C_M, T_B_C, floor_rad=floor_rad)[0]
    T_M_C = inv_T(obs.T_C_M)
    R_M_C = T_M_C[:3, :3]
    s = obs.sigma_cam(cam_fx, edge_m, pixel_sigma)
    return R_M_C @ np.diag(s ** 2) @ R_M_C.T
