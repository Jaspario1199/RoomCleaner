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

from .frames import inv_T, make_T, rot_z, rpy_to_matrix, tilt_angle
from .vision.marker import claw_pose_in_marker, claw_position_cov


@dataclass
class PoseObs:
    ok: bool
    reason: str = ""
    T_M_B: np.ndarray | None = None
    cov: np.ndarray | None = None
    t_us: float | None = None

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


class VisionSource:
    def __init__(self, frame_source, T_B_C, cam_fx, edge_m, *, max_age_s, now_us, pixel_sigma=0.3,
                 rot_sigma=0.01, imu=None, tilt_sigma=0.003):
        self.src = frame_source
        self.T_B_C = np.asarray(T_B_C, float)
        self.fx = cam_fx
        self.edge = edge_m
        self.max_age_us = max_age_s * 1e6
        self.now_us = now_us
        self.pixel_sigma = pixel_sigma
        self.rot_sigma = rot_sigma
        self.last: PoseObs | None = None
        # Gravity fusion: the marker lies flat and the IMU measures the claw's
        # roll/pitch, so only the marker's yaw and position are taken from the
        # image. A small marker's tilt is its least accurate quantity and, at
        # height h, every radian of it moves the claw position by h metres.
        self.imu = imu
        self.tilt_sigma = tilt_sigma

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
        else:
            T = claw_pose_in_marker(obs.T_C_M, self.T_B_C)
            cov = claw_position_cov(obs, self.T_B_C, self.fx, self.edge, pixel_sigma=self.pixel_sigma,
                                    rot_sigma_rad=self.rot_sigma)
            cov = cov + np.eye(3) * (self.rot_sigma * float(np.linalg.norm(T[:3, 3]))) ** 2
        self.last = PoseObs(True, "", T, cov, obs.capture_us)
        return self.last

    def _fused(self, obs):
        # prefer the attitude sampled together with this frame (no blocking call,
        # time-aligned); fall back to asking the IMU
        roll, pitch = obs.imu_rp if obs.imu_rp is not None else self.imu.roll_pitch()
        T_raw = claw_pose_in_marker(obs.T_C_M, self.T_B_C)
        R_raw = T_raw[:3, :3]
        yaw = math.atan2(R_raw[1, 0], R_raw[0, 0])
        R_M_B = rot_z(yaw) @ rpy_to_matrix(roll, pitch, 0.0)
        R_M_C = R_M_B @ self.T_B_C[:3, :3]
        t = obs.T_C_M[:3, 3]                                    # marker origin in the camera frame
        p_C = -R_M_C @ t
        p_B = p_C + R_M_C @ inv_T(self.T_B_C)[:3, 3]
        s = obs.sigma_cam(self.fx, obs.edge_eff or self.edge, self.pixel_sigma)
        cov = R_M_C @ np.diag(s ** 2) @ R_M_C.T
        h = float(np.linalg.norm(t))
        horiz = float(np.linalg.norm(p_B[:2]))
        cov += np.diag([(self.tilt_sigma * h) ** 2] * 2 + [0.0])
        cov += np.eye(3) * (self.rot_sigma * horiz) ** 2 + np.eye(3) * 1e-8
        return make_T(R_M_B, p_B), cov

    def still_pose(self, n, wait_s, *, interval_s=0.1, max_wait_s=10.0, spread_max_m=0.003):
        """Average n good frames. Returns (StillPose | None, reason). Frames
        too scattered (claw swinging) restart the window until max_wait."""
        good, misses, waited = [], [], 0.0
        while waited <= max_wait_s:
            o = self.observe()
            if o.ok:
                good.append(o)
                if len(good) >= n:
                    P = np.array([g.p for g in good[-n:]])
                    spread = float(np.sqrt(np.mean(np.sum((P - P.mean(0)) ** 2, axis=1))))
                    # allowed scatter = motion budget + 3x the detector's own expected noise
                    noise = float(np.sqrt(np.mean([np.trace(g.cov) for g in good[-n:]])))
                    if spread <= math.hypot(spread_max_m, 3 * noise):
                        last = good[-1]
                        cov = np.mean([g.cov for g in good[-n:]], axis=0) / n
                        return StillPose(P.mean(0), last.R, cov, spread, n, tilt_angle(last.R)), ""
                    good = good[-n + 1:]
            else:
                misses.append(o.reason)
            wait_s(interval_s)
            waited += interval_s
        why = f"no still marker pose within {max_wait_s:.0f} s"
        if misses:
            why += f" (last: {misses[-1]})"
        return None, why


def to_room(T_R_M, p_M):
    return (np.asarray(T_R_M) @ np.r_[np.asarray(p_M, float), 1.0])[:3]


def to_marker(T_R_M, p_R):
    return (inv_T(np.asarray(T_R_M)) @ np.r_[np.asarray(p_R, float), 1.0])[:3]
