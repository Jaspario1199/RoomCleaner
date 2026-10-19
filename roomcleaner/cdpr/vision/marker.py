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

Output pose conventions follow frames.py: ``T_C_M`` maps marker -> camera.
"""
from __future__ import annotations

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
                 border_px=4, continuity_rad=0.35, upright_rad=0.6):
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
        marker's normal should match it). From the IMU when fitted; otherwise
        from the camera mount assuming an upright claw. ``None`` disables the
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
        n, rvecs, tvecs, errs = cv2.solvePnPGeneric(self.obj, c.astype(np.float32), self.cam.K, self.cam.dist,
                                                     flags=cv2.SOLVEPNP_IPPE_SQUARE)
        cands = []
        for k in range(n):
            T = make_T(rotvec_to_matrix(rvecs[k].ravel()), tvecs[k].ravel())
            if T[2, 3] <= 0:
                continue
            cands.append((float(np.ravel(errs)[k]), T))
        cands.sort(key=lambda x: x[0])
        obs.candidates = cands
        if not cands:
            obs.reason = "no solution in front of camera"
            return obs
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
