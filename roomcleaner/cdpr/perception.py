"""Claw pose from the claw camera, with freshness and stillness checks.

``frame_source.observe(now_us) -> MarkerObservation`` is either the real
pipeline (claw JPEG -> MarkerDetector, see claw_link.DetectorFrameSource) or
the simulator's SimCamera. Everything downstream works in the marker frame M;
conversion to the room frame uses the current registration ``T_R_M``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .frames import inv_T, make_T, matrix_to_rotvec, rot_z, rpy_to_matrix, rotvec_to_matrix, tilt_angle
from .vision.marker import claw_cov_from_pose, claw_pose_in_marker, claw_position_cov, roll_pitch_sigma, skew


@dataclass
class PoseObs:
    ok: bool
    reason: str = ""
    T_M_B: np.ndarray | None = None
    cov: np.ndarray | None = None
    t_us: float | None = None
    corners: np.ndarray | None = None      # floor-reference corners in the image (px): the camera motion signal
    up_cam: np.ndarray | None = None       # marker normal (= up) in camera coordinates, unit: mount-offset input
    # raw detector pose and its covariance, for CAMERA-FRAME displacements (see ``cam_displacement``)
    T_C_M: np.ndarray | None = None        # marker -> camera as detected
    pose_cov: np.ndarray | None = None     # 6x6 (dr, dt) covariance of T_C_M in camera axes (random part: no systematic floor)
    anchor_M: np.ndarray | None = None     # point of M whose camera-frame position is best known (corner centroid)
    att_sigma_rad: float | None = None     # 1-sigma of the claw's roll or pitch from this frame (floor included); None = unknown
    n_tags: int = 1
    p_CB: np.ndarray | None = None         # body origin in camera axes (the mount's lever arm)
    R_B_C: np.ndarray | None = None        # camera -> body rotation (mount-corrected): its z row is the body axis a rotation of the claw turns about

    @property
    def p(self):
        return self.T_M_B[:3, 3]

    @property
    def R(self):
        return self.T_M_B[:3, :3]


@dataclass
class StillPose:
    p: np.ndarray            # mean body origin (marker frame)
    R: np.ndarray            # orientation of the last good frame
    cov: np.ndarray          # covariance of the mean
    spread_m: float          # RMS scatter of the individual frames
    n: int
    tilt_rad: float          # body z vs marker normal
    up_cam: np.ndarray | None = None       # mean marker normal in camera coordinates (unit)
    up_sigma_rad: float = 0.0              # standard error of up_cam (frame scatter / sqrt(n)), rad
    # camera-frame bookkeeping (displacements relative to a reference rotation: the tilt-lever noise of the absolute
    # pose cancels there). ``T_C_M`` = mean detector pose, ``pose_cov`` = covariance of that mean.
    T_C_M: np.ndarray | None = None
    pose_cov: np.ndarray | None = None
    anchor_M: np.ndarray | None = None
    cov_cam: np.ndarray | None = None      # covariance (M axes) of the camera-frame position of ``anchor_M`` (mean of n frames)
    spread_cam_m: float = 0.0              # RMS scatter of the frames' camera-frame position (the raw motion + noise)
    att_sigma_rad: float | None = None     # 1-sigma of the mean's roll or pitch (model part / sqrt(n), floor added)
    n_tags: int = 1
    p_CB: np.ndarray | None = None
    R_B_C: np.ndarray | None = None


def anchor_in_camera(o, Q):
    """Camera-frame position of the M-point ``Q`` for a pose-carrying object ``o`` (``PoseObs`` / ``StillPose``) and its
    covariance (3x3, camera axes): ``xi = R Q + t``, ``d xi = -[R Q]x dr + dt``. With ``Q`` near the corners used the
    tilt error barely moves it, which is why displacements are measured here and not through the absolute claw pose."""
    T = np.asarray(o.T_C_M, float)
    R, t = T[:3, :3], T[:3, 3]
    Q = np.asarray(Q, float)
    xi = R @ Q + t
    J = np.hstack([-skew(R @ Q), np.eye(3)])
    return xi, J @ np.asarray(o.pose_cov, float) @ J.T


def cam_displacement(o, ref, *, tilt_k: float = 5.0, kappa: float = 0.04, sigma0: float = 5e-4):
    """Claw displacement (marker axes) of ``o`` relative to the reference ``ref``, measured in the camera frame.

    The absolute pose of every frame carries its own tilt noise times the lever to the claw (6 mm per frame for one tag
    at 0.6 m); the camera-frame position of the tags themselves does not (0.3 mm). So the displacement is built from
    ``xi = R Q + t`` (the camera-frame position of ``Q = ref.anchor_M``, the corner centroid) and ONE reference
    rotation: the body origin is ``u = R_h (p_CB - xi)`` with ``R_h = R_ref exp(rv_h)`` and ``rv_h`` the frame's
    rotation relative to the reference, split into

    * ``psi a``: the turn about the BODY z axis ``a`` (camera axes). A cable take-up yaws the claw by degrees about its
      own axis (the world tilt of that axis stays: verified in the rigid-body simulator); without it the yaw reads as a
      lateral shift of the whole claw, tens of mm at a 0.3 m lever. Measured well (yaw is ~10x better than tilt).
    * ``eps``: the rest, i.e. a change of TILT. It is mostly noise (13 mrad per frame for one tag) but not always zero:
      the claw tilts ~3 % of the yaw it makes. It is used with the weight of a Gauss-Markov shrinkage,
      ``lam = s_p^2 / (s_p^2 + s_e^2)``, ``s_p = kappa |psi| (+ sigma0)`` the expected tilt change and ``s_e`` the tilt
      noise of the two frames (from their own covariances, systematic floor excluded: it cancels): ~0 for one tag,
      ~1 for a board, where the measured tilt change is as good as the absolute pose. If ``|eps|`` exceeds ``tilt_k``
      sigma the claw really tilted and the frame's own rotation is used (full absolute covariance).

    The tilt of an unmoved claw does not change, so there the lever noise of the absolute pose cancels exactly, which
    is what the probe, the take-up and the drag-watch measure. ``d = u_o - u_ref``.

    Returns ``(d, cov_o, cov_ref)``: the displacement and the covariances (marker axes) of the two frames' own noise
    (the reference's enters every displacement as a common offset, which a free ``p0`` absorbs)."""
    Q = np.asarray(ref.anchor_M, float)
    xo, Co = anchor_in_camera(o, Q)
    xr, Cr = anchor_in_camera(ref, Q)
    Rm_o = np.asarray(o.T_C_M, float)[:3, :3].T
    Rm_r = np.asarray(ref.T_C_M, float)[:3, :3].T
    p_CB = np.asarray(o.p_CB if o.p_CB is not None else ref.p_CB, float)
    R_B_C = np.asarray(o.R_B_C if o.R_B_C is not None else ref.R_B_C, float)
    a = R_B_C.T @ np.array([0.0, 0.0, 1.0])              # body z axis in camera axes
    P0 = np.eye(3) - np.outer(a, a)
    rv = matrix_to_rotvec(Rm_r.T @ Rm_o)                 # relative rotation, in the frame's camera axes
    psi = float(rv @ a)
    eps = rv - psi * a
    C_o, C_r = np.asarray(o.pose_cov, float)[:3, :3], np.asarray(ref.pose_cov, float)[:3, :3]
    s_e2 = float(np.trace(P0 @ C_o) + np.trace(P0 @ C_r)) / 2         # tilt noise per axis (both frames)
    v_r = p_CB - xr
    a_r = Rm_r @ v_r
    cov_r = Rm_r @ Cr @ Rm_r.T
    if s_e2 > 0 and float(np.linalg.norm(eps)) > tilt_k * math.sqrt(s_e2):   # the claw tilted for real: own rotation
        return Rm_o @ (p_CB - xo) - a_r, np.array(o.cov, float), cov_r
    s_p2 = (kappa * abs(psi)) ** 2 + sigma0 ** 2
    lam = s_p2 / (s_p2 + s_e2) if (s_p2 + s_e2) > 0 else 1.0
    Rh = Rm_r @ rotvec_to_matrix(psi * a + lam * eps)
    v_o = p_CB - xo
    Pm = np.outer(a, a) + lam * P0                        # rotation noise that enters: psi fully, eps with weight lam
    S = skew(v_o)
    cov_o = Rh @ (Co + S @ (Pm @ C_o @ Pm.T) @ S.T) @ Rh.T
    return Rh @ v_o - a_r, cov_o, cov_r


def floor_displacement(o, ref):
    """:func:`cam_displacement` for a claw RESTING ON THE FLOOR (take-up, pretension): its tilt cannot change, so the tilt is the
    reference's, never the frame's (no Gauss-Markov weight, no fallback): a noise spike of one frame's tilt then cannot read as motion
    through the lever arm (a 16 mrad outlier is 8 mm at 0.5 m). Yaw (the claw slides and turns on its jaws) is still the frame's own."""
    return cam_displacement(o, ref, tilt_k=math.inf, kappa=0.0, sigma0=0.0)


class VisionSource:
    """Claw pose from the floor reference. The camera-to-body rotation is the nominal (CAD) one corrected by the tilt
    offset measured at startup (``set_mount_offset``, see attitude.mount_offset_from_up)."""

    def __init__(self, frame_source, T_B_C, cam_fx, edge_m, *, max_age_s, now_us, pixel_sigma=0.3,
                 rot_sigma=0.01, imu=None, tilt_sigma=0.003, rot_floor=0.001):
        self.src = frame_source
        self.T_B_C_nominal = np.asarray(T_B_C, float)
        self.mount_Q = np.eye(3)                      # R_B_C = R_B_C_nominal @ mount_Q (camera-frame correction)
        self.fx = cam_fx
        self.edge = edge_m
        self.max_age_us = max_age_s * 1e6
        self.now_us = now_us
        self.pixel_sigma = pixel_sigma
        # ``rot_sigma``: attitude sigma used for a frame that carries no covariance of its own (legacy sources, the
        # simulator's fixed-noise mode, claw.vision_attitude_sigma_rad). ``rot_floor``: least attitude sigma added to a
        # frame's own tag-derived covariance (unmodelled systematics: lens, JPEG, print flatness; claw.vision_attitude_floor_rad)
        self.rot_sigma = rot_sigma
        self.rot_floor = rot_floor
        self.last: PoseObs | None = None
        # OPTIONAL gravity fusion (claw.imu, off by default; D27: the claw carries no IMU). With a roll/pitch
        # provider the marker lies flat and the provider measures the claw's roll/pitch, so only the marker's yaw
        # and position are taken from the image. A small marker's tilt is its least accurate quantity and, at
        # height h, every radian of it moves the claw position by h metres.
        self.imu = imu
        self.tilt_sigma = tilt_sigma

    @property
    def T_B_C(self) -> np.ndarray:
        """Camera pose in the body frame used for every pose (nominal rotation corrected by the measured mount tilt)."""
        T = self.T_B_C_nominal.copy()
        T[:3, :3] = T[:3, :3] @ self.mount_Q
        return T

    def set_mount_offset(self, Q) -> None:
        Q = np.asarray(Q, float)
        if Q.shape != (3, 3) or not np.allclose(Q.T @ Q, np.eye(3), atol=1e-9) or abs(np.linalg.det(Q) - 1) > 1e-9:
            raise ValueError("mount offset must be a proper rotation")
        self.mount_Q = Q

    def observe(self) -> PoseObs:
        now = self.now_us()
        obs = self.src.observe(now)
        if not obs.ok:
            return PoseObs(False, obs.reason, t_us=obs.capture_us)
        if obs.capture_us is not None and now - obs.capture_us > self.max_age_us:
            return PoseObs(False, f"frame {(now - obs.capture_us) / 1e3:.0f} ms old", t_us=obs.capture_us)
        if self.imu is not None:
            try:
                T, cov = self._fused(obs)
            except Exception as e:                    # IMU unavailable: no pose, never a guess
                return PoseObs(False, f"IMU: {e}", t_us=obs.capture_us)
            pose_cov, anchor, att, n_tags = self._legacy_pose_cov(obs), np.zeros(3), self.tilt_sigma, 1
        elif obs.pose_cov is not None:
            # the frame's own covariance (tag geometry: range, size, focal length, corner noise, tags in view),
            # propagated through the true lever (marker -> claw): anisotropic, nothing added on top
            T_B_C = self.T_B_C
            T = claw_pose_in_marker(obs.T_C_M, T_B_C)
            pose_cov = np.array(obs.pose_cov, float)          # random part only: the systematic floor cancels in displacements
            cov, cov_att = claw_cov_from_pose(obs.pose_cov, obs.T_C_M, T_B_C, floor_rad=self.rot_floor)
            att, anchor, n_tags = roll_pitch_sigma(cov_att), obs.anchor_M, obs.n_tags
        else:
            T_B_C = self.T_B_C
            T = claw_pose_in_marker(obs.T_C_M, T_B_C)
            cov = claw_position_cov(obs, T_B_C, self.fx, self.edge, pixel_sigma=self.pixel_sigma)
            cov = cov + np.eye(3) * (self.rot_sigma * float(np.linalg.norm(T[:3, 3]))) ** 2
            pose_cov, anchor, att, n_tags = self._legacy_pose_cov(obs), np.zeros(3), self.rot_sigma, 1
        self.last = PoseObs(True, "", T, cov, obs.capture_us, corners=obs.corners,
                            up_cam=np.asarray(obs.T_C_M)[:3, :3] @ np.array([0.0, 0.0, 1.0]),
                            T_C_M=np.asarray(obs.T_C_M, float), pose_cov=pose_cov, anchor_M=anchor,
                            att_sigma_rad=att, n_tags=n_tags, p_CB=inv_T(self.T_B_C)[:3, 3],
                            R_B_C=self.T_B_C[:3, :3].copy())
        return self.last

    def _legacy_pose_cov(self, obs):
        """Pose covariance of a frame that carries none: the old model (marker-position noise in camera axes, lateral /
        depth from the corner noise and the tag span, one isotropic rotation sigma)."""
        s_cam = obs.sigma_cam(self.fx, obs.edge_eff or self.edge, self.pixel_sigma)
        C = np.zeros((6, 6))
        C[:3, :3] = np.eye(3) * self.rot_sigma ** 2
        C[3:, 3:] = np.diag(s_cam ** 2)
        return C

    def _fused(self, obs):
        # prefer the attitude sampled together with this frame (no blocking call,
        # time-aligned); fall back to asking the IMU
        roll, pitch = obs.imu_rp if obs.imu_rp is not None else self.imu.roll_pitch()
        T_B_C = self.T_B_C
        T_raw = claw_pose_in_marker(obs.T_C_M, T_B_C)
        R_raw = T_raw[:3, :3]
        yaw = math.atan2(R_raw[1, 0], R_raw[0, 0])
        R_M_B = rot_z(yaw) @ rpy_to_matrix(roll, pitch, 0.0)
        R_M_C = R_M_B @ T_B_C[:3, :3]
        t = obs.T_C_M[:3, 3]                                    # marker origin in the camera frame
        p_C = -R_M_C @ t
        p_B = p_C + R_M_C @ inv_T(T_B_C)[:3, 3]
        s = obs.sigma_cam(self.fx, obs.edge_eff or self.edge, self.pixel_sigma)
        cov = R_M_C @ np.diag(s ** 2) @ R_M_C.T
        h = float(np.linalg.norm(t))
        horiz = float(np.linalg.norm(p_B[:2]))
        cov += np.diag([(self.tilt_sigma * h) ** 2] * 2 + [0.0])
        cov += np.eye(3) * (self.rot_sigma * horiz) ** 2 + np.eye(3) * 1e-8
        return make_T(R_M_B, p_B), cov

    def still_pose(self, n, wait_s, *, interval_s=0.1, max_wait_s=10.0, spread_max_m=0.003):
        """Average n good frames. Returns (StillPose | None, reason). Frames too scattered (claw swinging) restart the
        window until max_wait.

        Stillness is judged on the RAW motion: the scatter of the frames' camera-frame position (``cam_displacement``
        under one reference rotation) against ``spread_max_m`` plus three times the camera-frame noise of those frames.
        The absolute claw position is NOT used for this: its tilt-lever noise (and the covariance that mirrors it)
        is an order of magnitude larger than the camera-frame noise, and widening the threshold by it lets a 30 mm
        swing pass as 'still' (verification/imu_removal_review.md F6)."""
        good, misses, waited = [], [], 0.0
        while waited <= max_wait_s:
            o = self.observe()
            if o.ok:
                good.append(o)
                if len(good) >= n:
                    sp = self._summarise(good[-n:])
                    # allowed raw scatter = motion budget + 3x the camera-frame noise of the frames themselves
                    noise = float(np.sqrt(np.trace(sp.cov_cam) * sp.n))
                    if sp.spread_cam_m <= math.hypot(spread_max_m, 3 * noise):
                        return sp, ""
                    good = good[-n + 1:]
            else:
                misses.append(o.reason)
            wait_s(interval_s)
            waited += interval_s
        why = f"no still marker pose within {max_wait_s:.0f} s"
        if misses:
            why += f" (last: {misses[-1]})"
        return None, why

    def _summarise(self, frames) -> StillPose:
        n = len(frames)
        P = np.array([g.p for g in frames])
        spread = float(np.sqrt(np.mean(np.sum((P - P.mean(0)) ** 2, axis=1))))
        last = frames[-1]
        cov = np.mean([g.cov for g in frames], axis=0) / n
        U = np.array([g.up_cam for g in frames])
        up = U.mean(0)
        up_sigma = float(np.sqrt(np.mean(np.sum((U - up) ** 2, axis=1)) / n))
        # mean detector pose: rotation averaged about the first frame's, translation averaged
        R0 = frames[0].T_C_M[:3, :3]
        rv = np.mean([matrix_to_rotvec(g.T_C_M[:3, :3] @ R0.T) for g in frames], axis=0)
        T_mean = make_T(rotvec_to_matrix(rv) @ R0, np.mean([g.T_C_M[:3, 3] for g in frames], axis=0))
        att = None
        if all(g.att_sigma_rad is not None for g in frames):
            att = max(float(np.sqrt(np.mean([g.att_sigma_rad ** 2 for g in frames]) / n)), self.rot_floor)
        sp = StillPose(P.mean(0), last.R, cov, spread, n, tilt_angle(last.R), up / np.linalg.norm(up), up_sigma,
                       T_C_M=T_mean, pose_cov=np.mean([g.pose_cov for g in frames], axis=0) / n,
                       anchor_M=np.mean([g.anchor_M for g in frames], axis=0), att_sigma_rad=att,
                       n_tags=int(round(np.mean([g.n_tags for g in frames]))), p_CB=last.p_CB, R_B_C=last.R_B_C)
        # raw scatter of the frames' camera-frame position about the mean pose (tilt-lever noise excluded), and the
        # camera-frame covariance of the mean
        D = np.array([cam_displacement(g, sp)[0] for g in frames])
        sp.spread_cam_m = float(np.sqrt(np.mean(np.sum((D - D.mean(0)) ** 2, axis=1))))
        sp.cov_cam = cam_displacement(sp, sp)[2]
        return sp


def to_room(T_R_M, p_M):
    return (np.asarray(T_R_M) @ np.r_[np.asarray(p_M, float), 1.0])[:3]


def to_marker(T_R_M, p_R):
    return (inv_T(np.asarray(T_R_M)) @ np.r_[np.asarray(p_R, float), 1.0])[:3]
