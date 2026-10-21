"""Claw attitude without an IMU (decision D27) and host-side grip gating.

Where roll/pitch come from
--------------------------
* **Floor reference in view**: the vision pose (``perception.VisionSource``). Its roll/pitch are measured against
  the marker normal, i.e. against gravity, through the camera-to-body rotation. The rotation's tilt part is measured at
  EVERY startup, while the claw rests upright on its jaws over the printout (:func:`mount_offset_from_up`), and
  stored; the tilt of a still claw is then read relative to that. Honest 1-sigma: ``claw.vision_attitude_sigma_rad``
  (10 mrad, not the 4 mrad of the IMU it replaces) combined with the standard error of the mount measurement.
* **Away from the reference**: the cable model's static-equilibrium tilt ``Geometry.R_at(p)`` (anchored to the last
  measured pose), valid only after the pendulum has settled. 1-sigma ``claw.statics_attitude_sigma_rad``: it depends
  on the centre-of-mass height and the payload by several degrees.
* Gravity fusion (``claw.imu``) stays as an optional path in ``VisionSource`` and is unused by default.

Not observable on the floor: the camera mount's rotation about the vertical (the claw may rest at any heading). That
part keeps its nominal value; yaw is held/measured elsewhere, never predicted.

Grip gating (``tasks.GRIP``): the claw's own tilt gate is gone. The host waits until the claw is still, then approves.
"Still" = camera-observed image motion of the floor reference below a rate for N consecutive frames; with no camera
motion signal (reference not in view) = a dwell of k pendulum periods, T = 1.25 x 2 pi sqrt(L / g) (the margin covers the
compound pendulum), L = depth of the centre of mass below the attachment plane, counted from the LAST OBSERVED motion. At a
release the loaded pendulum (payload at the jaw tips) and its full dwell apply. The predicted tilt at the grip pose (``R_at``)
must also be within ``grip_tilt_max``. The per-frame attitude sigma of a vision pose comes from the tag geometry
(``vision/marker.py``); see docs/CONTROL_SYSTEM_V1.md 3.2.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .frames import matrix_to_rotvec, rotvec_to_matrix, tilt_angle

G = 9.81


# ------------------------------------------------------------------ camera mount offset
@dataclass
class MountOffset:
    Q: np.ndarray             # rotation (camera frame) such that  R_B_C_corrected = R_B_C_nominal @ Q
    angle_rad: float          # magnitude of the correction (the tilt error of the nominal mount, plus any rest tilt)
    sigma_rad: float          # standard error of the measurement (frame scatter / sqrt(n))
    n: int


def _rot_between(a, b) -> np.ndarray:
    """Minimal rotation taking unit vector ``a`` to unit vector ``b``."""
    a = np.asarray(a, float) / np.linalg.norm(a)
    b = np.asarray(b, float) / np.linalg.norm(b)
    v = np.cross(a, b)
    s = float(np.linalg.norm(v))
    c = float(a @ b)
    if s < 1e-12:
        if c > 0:
            return np.eye(3)
        raise ValueError("vectors are opposite")
    return rotvec_to_matrix(v / s * math.atan2(s, c))


def mount_offset_from_up(R_B_C_nominal, up_cam, *, sigma_rad=0.0, n=1) -> MountOffset:
    """Camera-to-body tilt offset from a claw standing upright.

    With the claw upright the body z axis IS the marker normal. The marker normal measured in camera coordinates is
    ``up_cam`` (unit); the nominal mount says body z is ``R_B_C_nominal.T @ e_z`` there. The minimal rotation between
    the two fixes the two tilt components of the mount; the rotation about the vertical is unobservable and untouched.
    """
    R0 = np.asarray(R_B_C_nominal, float)
    u0 = R0.T @ np.array([0.0, 0.0, 1.0])
    u = np.asarray(up_cam, float)
    u = u / np.linalg.norm(u)
    S = _rot_between(u0, u)                      # camera-frame rotation u0 -> u
    Q = S.T                                      # (R0 @ Q).T e_z = Q.T u0 = S u0 = u
    return MountOffset(Q, float(np.linalg.norm(matrix_to_rotvec(S))), float(sigma_rad), int(n))


# ------------------------------------------------------------------ pendulum settling
def pendulum_length_m(claw) -> float | None:
    """Depth of the centre of mass below the attachment plane (m); None if unknown or not hanging below it."""
    if claw.com_body_m is None:
        return None
    z_attach = float(np.mean(np.asarray(claw.attachment_points_body_m, float).reshape(-1, 3)[:, 2]))
    L = z_attach - float(claw.com_body_m[2])
    return L if L > 1e-3 else None


def pendulum_period_s(L_m: float) -> float:
    """Period of a simple pendulum of length ``L_m``. A rigid claw is a compound pendulum, whose period is longer
    (T = 2 pi sqrt((k^2 + L^2) / (g L)), k = radius of gyration about the centre of mass: ~20 % for k = 0.13 m, L = 0.196 m;
    verification/imu_removal_review.md F8c); the settle gate multiplies this by ``tasks.grip_period_margin``."""
    return 2.0 * math.pi * math.sqrt(L_m / G)


def loaded_pendulum_length_m(claw, payload_kg: float) -> float | None:
    """Pendulum length with ``payload_kg`` held in the jaws: depth of the combined centre of mass below the attachment
    plane, the payload taken at the lowest point of the claw (the jaw tips; conservative, a garment sits a little
    higher). Equal to :func:`pendulum_length_m` for no payload or when the claw gives no mass / lowest point."""
    L = pendulum_length_m(claw)
    if L is None or not payload_kg or payload_kg <= 0:
        return L
    m = getattr(claw, "mass_kg", None)
    low = getattr(claw, "lowest_point_body_m", None)
    if m is None or low is None:
        return L
    z_attach = float(np.mean(np.asarray(claw.attachment_points_body_m, float).reshape(-1, 3)[:, 2]))
    Lp = z_attach - float(np.asarray(low, float)[2])
    if Lp <= L:
        return L
    return (m * L + payload_kg * Lp) / (m + payload_kg)


def settle_dwell_s(claw, tasks, payload_kg: float = 0.0) -> float:
    """Dwell used when no camera motion signal exists: ``grip_settle_periods`` pendulum periods, each the simple-pendulum
    period times ``tasks.grip_period_margin`` (1.25: covers the compound-pendulum lengthening), never less than
    ``grip_settle_min_s``; the minimum alone when the claw geometry gives no valid pendulum length. ``payload_kg``: the
    mass in the jaws (a release): the loaded centre of mass hangs lower, so the period and the dwell are longer."""
    L = loaded_pendulum_length_m(claw, payload_kg)
    if L is None:
        return float(tasks.grip_settle_min_s)
    return float(max(tasks.grip_settle_min_s,
                     tasks.grip_settle_periods * tasks.grip_period_margin * pendulum_period_s(L)))


# ------------------------------------------------------------------ attitude estimate
@dataclass
class AttitudeEstimate:
    R: np.ndarray            # claw orientation, room frame
    tilt_rad: float          # body z against vertical
    sigma_rad: float         # 1-sigma of roll or pitch
    source: str              # "vision" | "statics"


def predicted_tilt_rad(geometry, p_room) -> float:
    """Tilt of the cable model's static-equilibrium attitude at ``p_room``."""
    return tilt_angle(geometry.R_at(np.asarray(p_room, float)))


def estimate_attitude(ctx, p_room) -> AttitudeEstimate:
    """Best attitude now: vision when the floor reference is in view, else the cable model's static tilt."""
    cl = ctx.cfg.claw
    o = ctx.vision.observe()
    if o.ok:
        R = ctx.T_R_M[:3, :3] @ o.R
        # this frame's own attitude sigma (tag geometry, see vision/marker.py), else the configured constant
        att = getattr(o, "att_sigma_rad", None)
        sig = math.hypot(cl.vision_attitude_sigma_rad if att is None else att, getattr(ctx, "mount_sigma_rad", 0.0))
        return AttitudeEstimate(R, tilt_angle(R), sig, "vision")
    R = ctx.model.geometry.R_at(np.asarray(p_room, float))
    return AttitudeEstimate(R, tilt_angle(R), cl.statics_attitude_sigma_rad, "statics")


# ------------------------------------------------------------------ settle, then approve
@dataclass
class SettleResult:
    ok: bool
    method: str              # "camera" | "dwell"
    waited_s: float
    frames: int              # consecutive still frame pairs (camera) or 0
    max_rate_rad_s: float | None
    reason: str = ""


def image_motion_rad_s(prev, cur, fx) -> float | None:
    """Camera-observed motion between two pose observations: mean corner shift of the floor reference in the image
    divided by the focal length and the frame interval (rad/s; a lateral speed v at depth z reads as v/z).
    None if either lacks corners or the frames are not distinct in time."""
    if prev.corners is None or cur.corners is None or prev.t_us is None or cur.t_us is None:
        return None
    dt = (cur.t_us - prev.t_us) / 1e6
    if dt <= 1e-6:
        return None
    shift = float(np.mean(np.linalg.norm(np.asarray(cur.corners) - np.asarray(prev.corners), axis=1)))
    return shift / (fx * dt)


def wait_until_still(ctx, *, interval_s: float | None = None, payload_kg: float = 0.0) -> SettleResult:
    """Wait for the claw to stop moving. Camera motion signal when the floor reference is in view; otherwise a
    dwell of ``grip_settle_periods`` pendulum periods counted from the LAST OBSERVED MOTION (a claw seen swinging and
    then lost is not approved 'early': the time while the camera still saw it moving does not count towards the dwell;
    with no motion ever observed the dwell counts from the start of waiting). Never returns ok on a timeout while
    motion is observed.

    ``payload_kg`` > 0 (a loaded release): the dwell of the LOADED pendulum is applied in full even when the camera
    signal reports stillness, and the timeout is extended to cover it: after a transport with the garment in the jaws
    the swing is larger and slower than the camera test, which needs only ``grip_still_frames`` quiet pairs, can see."""
    tk = ctx.cfg.tasks
    dt = interval_s or ctx.cfg.startup.frame_interval_s
    fx = ctx.camera.fx
    full_dwell = settle_dwell_s(ctx.cfg.claw, tk, payload_kg)
    timeout = tk.grip_settle_timeout_s if payload_kg <= 0 else max(tk.grip_settle_timeout_s, full_dwell + 2 * dt)
    prev, still, misses, waited, worst = None, 0, 0, 0.0, 0.0
    t_motion = 0.0                                   # waiting time of the last observed motion (0 = none seen)
    seen_signal = False
    while waited <= timeout:
        o = ctx.vision.observe()
        if o.ok and getattr(o, "corners", None) is not None:
            rate = image_motion_rad_s(prev, o, fx) if prev is not None else None
            prev, misses = o, 0
            if rate is not None:
                seen_signal = True
                worst = max(worst, rate)
                if rate <= tk.grip_still_rate_rad_s:
                    still += 1
                else:
                    still, t_motion = 0, waited
                if still >= tk.grip_still_frames and (payload_kg <= 0 or waited - t_motion >= full_dwell):
                    return SettleResult(True, "camera", waited, still, rate)
        else:
            misses += 1
            prev, still = None, 0
            if misses >= tk.grip_still_frames:       # no camera motion signal: pendulum dwell instead
                rest = max(full_dwell - (waited - t_motion), 0.0)
                if rest > 0:
                    ctx.wait(rest)
                return SettleResult(True, "dwell", waited + rest, 0, None,
                                    "no camera motion signal (floor reference not in view)")
        ctx.wait(dt)
        waited += dt
    why = "claw still moving" if seen_signal else "no usable frames"
    return SettleResult(False, "camera", waited, still, worst if seen_signal else None,
                        f"{why} after {timeout:.0f} s (worst image rate {worst:.3f} rad/s)")
