"""System configuration: one JSON file describes the physical machine.

Fail-closed rule
----------------
Every machine limit that has not been *measured* is ``null`` in the JSON.
Each operating stage declares the fields it needs; :meth:`SystemConfig.missing`
lists the unset ones and the supervisor refuses to enter that stage while the
list is non-empty. Suspended motion additionally requires
``authorization.suspended_motion_authorized = true``, which is a deliberate
human sign-off after the supervised qualification tests (see docs).

Nothing in this module invents a value for an unmeasured quantity.
Simulation profiles (``config/robot.sim.json``) carry plausible numbers so the
logic can be exercised; they are not hardware settings.

Active stations (docs/THREE_STATION_MODE_SPEC.md)
-------------------------------------------------
The product has four stations (A-D); a test set-up may mount only three. ``load_config`` keeps all four station
records, but ``SystemConfig.stations`` / ``.ids`` hold only the ACTIVE ones, in A-D order, so every loop over
``cfg.stations`` in the host software (coordinator, supervisor, startup, calibration, planner, simulator, phone app)
runs over the active set. The records of the others are in ``SystemConfig.inactive_stations``; they have no address
requirement, no transport, and are never configured or armed. The active set is the JSON key ``stations_active`` (a list
of 3 or 4 ids; ``"stations.active"`` is accepted as a spelling of the same key); absent = all four, so every existing
profile is unchanged. Per-station arrays that are indexed A-D in the file (``claw.attachment_points_body_m``,
``startup.max_slack_m``) stay four long; ``SystemConfig.station_index`` maps an id to its place in them.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import numpy as np

from .frames import make_T, rpy_to_matrix

STATION_IDS = ("A", "B", "C", "D")
G_ACC = 9.81

# Three-station mode: the active anchors must span a triangle (floor projection) that is not a sliver. A point claw on
# three cables is held with all-positive tensions only inside that triangle, and the margin from its edges (below) is
# a fraction of its altitudes, so a triangle whose SHORTEST altitude is under this has no useful workspace.
MIN_TRIANGLE_ALTITUDE_M = 0.25


class ConfigError(ValueError):
    pass


def _f(v, name, *, positive=False, allow_none=True):
    if v is None:
        if allow_none:
            return None
        raise ConfigError(f"{name} is required")
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ConfigError(f"{name} must be a finite number, got {v!r}")
    if positive and v <= 0:
        raise ConfigError(f"{name} must be > 0, got {v!r}")
    return float(v)


def _vec(v, name, n=3, allow_none=True):
    if v is None:
        if allow_none:
            return None
        raise ConfigError(f"{name} is required")
    a = np.asarray(v, float)
    if a.shape != (n,) or not np.all(np.isfinite(a)):
        raise ConfigError(f"{name} must be {n} finite numbers, got {v!r}")
    return a


# ---------------------------------------------------------------------------
# Physical sanity ranges of the keys that tune the vision attitude path, the settle gate and the rocking check
# (D27 follow-up; verification/imu_removal_review.md R2.2e / R4). "Finite and > 0" lets through values that quietly make the
# estimator dishonest (a 0.05 covariance margin, a settle margin that collapses the dwell), so every key has a range and a
# reason; ``load_config`` refuses a value outside it and the message repeats the reason. Ranges are NOT acceptance thresholds
# of the product: they only exclude values that no camera, pendulum or print can have.
ATTITUDE_BOUNDS = {
    "camera.corner_sigma_px": (0.15, 2.0, "px",
        "1-sigma of a detected tag corner. cv2's sub-pixel refinement alone is biased by ~0.15 px on a 50 px tag "
        "(verification/floor_board_detector.md), so a value under 0.15 px claims a corner better than the detector's own "
        "systematic error and, since every covariance scales with its square, makes the estimator overconfident; 2 px is the "
        "detector's own reprojection limit (camera.max_reprojection_px): a frame noisier than that is refused anyway. The "
        "settle gate's still-rate limit has to clear the noise this value implies (tasks.grip_still_rate_rad_s, checked in "
        "load_config)"),
    "camera.pose_cov_inflate": (1.0, 5.0, "x",
        "margin on the Cramer-Rao standard deviation. The bound is the best any unbiased estimator can reach, so a factor "
        "below 1 claims the impossible (0.05 would shrink every covariance 400-fold); above 5 the covariance is 25x too "
        "large and throws away what the board measures (the validated runs use 1.3)"),
    "claw.vision_attitude_floor_rad": (2e-4, 0.02, "rad",
        "least attitude sigma added for what the tag model leaves out (lens, JPEG, print flatness). 0.2 mrad (0.01 deg) is "
        "beyond a printed sheet (0.1 mm of paper curl over a 150 mm tag is 0.7 mrad); 20 mrad is twice the 10 mrad "
        "constant-sigma model this floor replaced (claw.vision_attitude_sigma_rad)"),
    "tasks.grip_period_margin": (1.2, 3.0, "x the simple-pendulum period",
        "a rigid claw is a compound pendulum, T = 2 pi sqrt((k^2 + L^2) / (g L)): 1.2x the simple period for k = 0.13 m about "
        "the centre of mass and L = 0.196 m (imu_removal_review.md F8c). Below that the dwell is shorter than the number of "
        "periods it claims (0.05 collapses it to the grip_settle_min_s floor); 3x would need k = 0.55 m, larger than the claw"),
    "tasks.grip_still_rate_rad_s": (0.015, 0.1, "rad/s",
        "image-motion rate below which the claw counts as still. image_motion_rad_s averages the corner-shift NORMS, which do "
        "not average away however many corners there are (Rayleigh mean 1.2533 x sqrt(2) x sigma = 1.77 sigma): a still "
        "claw's noise-only rate is 1.77 x 0.3 px / (520 px x 0.1 s) = 1.0e-2 rad/s at the default corner noise, not the "
        "8e-3 / 4e-3 of a shift that averages to zero. A limit under ~1.0e-2 never opens; at 1.2e-2 a one-tag view passes 75 % "
        "of the pairs (5 in a row: 24 %), at 1.5e-2 95 % (79 %; three tags 99.8 % / 99 %), so the lower bound is 0.015 = 1.4x "
        "the noise rate at the default corner noise. load_config also refuses a limit below 1.4x the noise rate of the "
        "configured camera.corner_sigma_px at the configured startup.frame_interval_s; 0.1 rad/s is a 17 mrad (1 deg) swing at the 5.9 rad/s of the 1.07 s pendulum, a fifth of the 5 deg grip tilt limit"),
    "tasks.grip_still_frames": (3, 30, "frame pairs",
        "consecutive quiet frame pairs. The image rate of a swinging claw is zero twice per period, so the quiet window must "
        "span a quarter period (0.27 s of the 1.07 s pendulum) to be sure to contain moving frames: 3 pairs at 0.1 s. 30 "
        "pairs (3 s, three periods) is the most a gate that must open within grip_settle_timeout_s can ask for"),
    "tasks.grip_settle_periods": (3.0, 20.0, "pendulum periods",
        "dwell without a camera signal. The review judged 3.8 periods too short (F8c) and fewer than 3 cannot show a decay at "
        "all; 20 periods of the loaded 1.25 s pendulum is 31 s per release, the most an operator should wait"),
    "tasks.grip_settle_min_s": (1.0, 10.0, "s",
        "floor of that dwell for a very short pendulum: at least one full period (0.89 s simple, 1.07 s compound); above 10 s "
        "it exceeds the loaded dwell (5 x 1.25 x 1.25 s = 7.8 s) and the period arithmetic means nothing"),
    "tasks.grip_settle_timeout_s": (10.0, 120.0, "s",
        "give-up time of a claw that is still moving. The unloaded dwell is 5.6 s and a loaded release 7.8 s; wait_until_still "
        "extends the timeout of a loaded release to cover its dwell (max(timeout, dwell + 2 frame intervals)), but a camera that "
        "sees the claw swinging for under 10 s is not yet a claw that will not settle; above 2 minutes the operator waits on a "
        "claw that is not going to settle"),
    "startup.board_survey_frames": (10, 200, "frames",
        "frames of the still claw given to the board survey: a sheet needs >= 8 views with a camera pose (BoardSurvey.min_obs), "
        "so under 10 leaves no spare for frames that lose it; 200 frames (20 s at 0.1 s) is the longest a hand-placed board "
        "and a resting claw are worth waiting for"),
    "startup.rocking_tilt_k": (4.0, 10.0, "sigma",
        "threshold of the rocking check in sigmas of the tilt change. The norm of a 2-D noise vector exceeds k sigma with "
        "probability exp(-k^2/2): 1e-2 at k = 3, 3e-4 at 4, 4e-6 at 5. A take-up is ~430 evaluations of overlapping 3-frame "
        "means, and the simulated share of take-ups with a false trip is 98 % at k = 3, 12.7 % at k = 4 and 0.15 % at k = 5 "
        "(verification/board_followups_review.md L1), so under 4 a resting claw is reported as rocking in most take-ups; "
        "above 10 a board (1.5 mrad) would only trip at 15 mrad = 8 mm of body-origin motion"),
    "startup.rocking_tilt_min_rad": (0.001, 0.02, "rad",
        "least tilt change that counts as rocking: 1 mrad is the systematic floor of a tag-set change "
        "(claw.vision_attitude_floor_rad); 20 mrad is 10 mm of body-origin motion at the 0.52 m lever, 5x the take-up onset"),
    "startup.rocking_yaw_coupling": (0.0, 0.5, "rad of tilt per rad of yaw",
        "tilt that comes with a take-up yaw (rigid-body simulator ~0.03-0.04); 0.5 would let a 10 deg yaw hide 5 deg of tilt"),
}
# Noise-only image rate of a claw that does not move (attitude.image_motion_rad_s): the mean over the corners of the shift
# norm between two frames. Each corner shift is a 2-D Gaussian of 1-sigma sqrt(2) x corner_sigma_px per axis, its norm has the
# Rayleigh mean sqrt(pi/2) x sqrt(2) x sigma = sqrt(pi) x sigma, and that mean does not average away with more corners:
# rate = sqrt(pi) x sigma / (fx x dt) = 1.0e-2 rad/s at 0.3 px, fx = 520 px (the sim camera), dt = 0.1 s (startup.frame_interval_s,
# the interval wait_until_still uses between frames). Linear in sigma, inverse in dt (review N3: the check used to assume 0.1 s whatever
# was configured). fx is only in the intrinsics file, so 520 px stays a disclosed approximation. Monte Carlo with 1-4 tags (review M1,
# tests/cdpr/test_keepalive_pumping.py): the same to 2 %.
STILL_RATE_REF_FX_PX = 520.0
STILL_RATE_REF_DT_S = 0.1
# A limit has to clear that mean by 1.4x: the one-tag rate has a spread of 26 % of its mean (4 corners), so 1.4x passes 93 % of
# the pairs of a one-tag view (99 % with 3 tags) and five quiet pairs in a row 70 % (97 %) of the time per window. At 1.0x half of
# the pairs fail and the gate practically never opens. 1.4 is also below 0.1 / (sqrt(pi) x 2 px / 52) = 1.47, so that even the
# noisiest corner sigma of its range (2 px) has a feasible limit inside the range of tasks.grip_still_rate_rad_s.
STILL_RATE_NOISE_K = 1.4


def still_rate_noise_floor_rad_s(corner_sigma_px, frame_interval_s=STILL_RATE_REF_DT_S):
    """Mean image rate (rad/s) of a claw that does not move, for a corner noise ``corner_sigma_px`` and the frame interval
    ``startup.frame_interval_s`` (reference camera, fx = 520 px)."""
    return math.sqrt(math.pi) * corner_sigma_px / (STILL_RATE_REF_FX_PX * frame_interval_s)


_LAYOUT_VERSION = 1            # vision.board.FloorBoardLayout.VERSION (config must not import cv2 / scipy; a test keeps them equal)


def _in_range(v, key):
    lo, hi, unit, why = ATTITUDE_BOUNDS[key]
    ok = (not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v) and lo <= v <= hi)
    if not ok:
        raise ConfigError(f"{key} = {v!r} is outside the physically sensible range [{lo:g}, {hi:g}] {unit}: {why}")
    return v


def _check_board_layout_file(v):
    """``marker.board_layout_file``: None, or the path of an existing floor-board layout JSON (relative paths are taken from
    the working directory, exactly as the service opens them). The file may hold an unsurveyed layout (only the origin tag):
    the startup surveys the rest (``startup.board_survey``)."""
    if v is None:
        return None
    if not isinstance(v, str) or not v.strip():
        raise ConfigError(f"marker.board_layout_file must be a path string or null, got {v!r}")
    p = Path(v)
    if p.exists() and not p.is_file():
        raise ConfigError(f"marker.board_layout_file {v!r} is not a file")
    if not p.is_file():
        raise ConfigError(f"marker.board_layout_file {v!r} does not exist (relative paths are taken from the working directory): "
                          "create the starting layout with `python -m tools.print_floor_board --layout-json PATH` or leave "
                          "it null to use the single tag")
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError) as e:
        raise ConfigError(f"marker.board_layout_file {v!r} is not readable JSON: {e}")
    tags = d.get("tags") if isinstance(d, dict) else None
    ok = (isinstance(d, dict) and d.get("version") == _LAYOUT_VERSION and isinstance(tags, list) and tags
          and all(isinstance(t, dict) and isinstance(t.get("id"), int) for t in tags)
          and isinstance(d.get("edge_m"), (int, float)) and not isinstance(d.get("edge_m"), bool)
          and math.isfinite(d["edge_m"]) and 0.02 <= d["edge_m"] <= 0.5
          and isinstance(d.get("origin_id"), int) and d["origin_id"] in [t["id"] for t in tags])
    if not ok:
        raise ConfigError(f"marker.board_layout_file {v!r} is not a floor board layout (vision/board.py FloorBoardLayout JSON, "
                          f"version {_LAYOUT_VERSION}: tags, edge_m 0.02..0.5 m, origin_id)")
    return v


# ---------------------------------------------------------------------------
@dataclass
class DriveConfig:
    full_steps_per_rev: int = 200
    microsteps: int = 1               # Rev C wiring: MS1-3 low = full step
    step_sign: int = 1                # +1: positive logical step = DIR high = payout
    max_step_rate_hz: float | None = None

    @property
    def usteps_per_rev(self) -> int:
        return self.full_steps_per_rev * self.microsteps


@dataclass
class EncoderConfig:
    counts_per_rev: int = 4096
    sign: int | None = None           # measured on the bench; +1/-1 so + = payout
    mount: str = "spool"              # "spool" (sees spool slip) or "motor_shaft"
    max_age_s: float | None = None


@dataclass
class SpoolConfig:
    core_radius_m: float = 0.0075     # Spoolv3 measured hub O15
    drum_width_m: float = 0.016       # Spoolv3 measured
    flange_radius_m: float = 0.018    # Spoolv3 measured O36
    line_diameter_m: float | None = None
    packing: float = 0.85
    line_total_m: float | None = None # cut length from attachment to spool anchor
    payout_scale: float = 1.0         # calibrated multiplier, 1.0 until measured
    payout_table: list | None = None  # optional measured [[usteps, payout_m], ...]


@dataclass
class BeadConfig:
    present: bool = True
    trigger_length_m: float | None = None   # external span at first repeatable trigger
    uncertainty_m: float | None = None
    switch_normally_closed: bool = True     # NC: open = actuated OR broken wire
    debounce_s: float = 0.010
    approach_speed_m_s: float | None = None
    search_window_m: float | None = None    # slow-search distance before expected trigger
    max_overtravel_m: float | None = None   # beyond expected trigger before abort
    backoff_m: float | None = None
    repeatability_tol_m: float | None = None
    min_length_margin_m: float = 0.02       # normal motion keeps L >= trigger + margin


@dataclass
class StationConfig:
    id: str
    anchor_room_m: np.ndarray | None = None   # cable exit point, room frame
    anchor_sigma_m: float = 0.10              # 1-sigma of the user's entry
    address: str | None = None                # "ip:port" for UDP; None in sim
    drive: DriveConfig = field(default_factory=DriveConfig)
    encoder: EncoderConfig = field(default_factory=EncoderConfig)
    spool: SpoolConfig = field(default_factory=SpoolConfig)
    bead: BeadConfig = field(default_factory=BeadConfig)


@dataclass
class ClawConfig:
    attachment: str = "common"                       # "common" | "spaced"
    attachment_points_body_m: np.ndarray = field(default_factory=lambda: np.zeros((4, 3)))
    mass_kg: float | None = None
    T_body_cam: np.ndarray | None = None             # camera pose in body frame
    lowest_point_body_m: np.ndarray | None = None    # e.g. jaw tips
    com_body_m: np.ndarray | None = None             # claw centre of mass in the body frame (None = origin)
    imu: bool = False                                # D27: the claw carries NO IMU. True only enables the optional gravity
                                                     # fusion in perception.VisionSource, which then needs a roll/pitch
                                                     # provider that is not the claw node (none exists on the hardware)
    grip_tilt_max_rad: float = math.radians(5)       # host-side grip approval limit (predicted R_at and, when the floor
                                                     # reference is in view, measured tilt)
    vision_attitude_sigma_rad: float = 0.010         # D27: 1-sigma of roll OR pitch for a vision frame that carries NO covariance of
                                                     # its own (legacy source / fixed-noise simulation). Frames from the detectors
                                                     # carry a per-frame, tag-geometry covariance (vision/marker.py) and use this
                                                     # only through the validation below
    vision_attitude_floor_rad: float = 0.001         # least attitude sigma added to a frame's own covariance (unmodelled
                                                     # systematics: lens, JPEG, print flatness)
    statics_attitude_sigma_rad: float = 0.07         # 1-sigma of the cable-model (R_at) tilt: CoM height / payload
                                                     # sensitivity of a few degrees (verification/multi_attachment_review.md)
    mount_offset_max_rad: float = math.radians(5)    # startup aborts if the measured camera-to-body tilt offset exceeds
                                                     # this (mount wrong, or the claw is not resting upright)
    address: str | None = None


@dataclass
class MarkerConfig:
    family: str = "apriltag_36h11"
    id: int = 0
    edge_m: float | None = None                      # measured detected-edge length
    heading_prior_rad: float | None = None           # marker +X toward station A ~ this room yaw
    heading_sigma_rad: float = math.radians(20)
    position_prior_room_m: np.ndarray | None = None  # None -> room centre
    position_sigma_m: float = 0.5
    board_layout_file: str | None = None             # surveyed multi-sheet floor reference (vision/board.py FloorBoardLayout JSON):
                                                     # when set, the BoardDetector replaces the single-tag detector (a frame with
                                                     # >= 2 usable tags gets the joint multi-tag pose, else the single tag)


@dataclass
class CameraConfig:
    intrinsics_file: str | None = None
    max_frame_age_s: float | None = None
    pose_sigma_m: float = 0.005                      # per-axis, used to weight the fit
    pose_sigma_rad: float = 0.01
    min_marker_pixels: float = 40.0
    max_reprojection_px: float = 2.0
    ambiguity_ratio_min: float = 3.0                 # 2nd/1st reprojection error to accept
    corner_sigma_px: float = 0.3                     # 1-sigma of a detected tag corner (px per image axis): the per-frame pose
                                                     # covariance (vision/marker.py) is derived from it. Measure it on real frames.
    pose_cov_inflate: float = 1.3                    # margin on the Cramer-Rao standard deviation of that covariance


@dataclass
class MotionConfig:
    max_cable_speed_m_s: float | None = None
    max_cable_accel_m_s2: float | None = None
    max_cart_speed_m_s: float | None = None
    max_cart_accel_m_s2: float | None = None
    hold_time_s: float = 0.25                        # path-time feed-hold duration at full speed
    min_tension_n: float = 0.5
    max_tension_n: float | None = None               # measured pull capability at speed / margin
    dynamic_accel_m_s2: float = 2.0                  # requirement: payload + 2 m/s^2 dynamic
    workspace_margin_m: float = 0.20
    ceiling_margin_m: float = 0.40                   # keep claw this far below anchor plane
    segment_s: float = 0.10
    lookahead_s: float = 0.8
    start_lead_s: float = 0.40
    task_max_height_m: float = 1.6                   # pickup/delivery transit never plans above this claw-origin height


@dataclass
class StartupConfig:
    probe_packet_m: float | None = None              # retraction per take-up packet
    probe_speed_m_s: float | None = None
    max_slack_m: list | None = None                  # per station cumulative take-up cap
    onset_translation_m: float = 0.002
    onset_tilt_rad: float = math.radians(0.6)
    onset_noise_k: float = 4.0                       # onset threshold >= k * still-noise sigma
    onset_backoff_m: float | None = None
    lift_packet_m: float | None = None               # vertical claw lift per packet
    target_clearance_m: float = 0.075
    max_lift_m: float | None = None                  # abort if no clearance by this lift
    max_lateral_drift_m: float | None = None
    max_tilt_rad: float = math.radians(8)
    still_samples: int = 10
    settle_s: float = 0.5
    max_marker_wait_s: float = 120.0
    battery_min_v: float = 7.0                       # 2S LiPo: refuse to lift below this
    floor_height_tol_m: float = 0.03                 # claw must be resting upright on the floor
    bearing_translation_m: float = 0.006             # keep pulling past onset to see the slide direction
    # Rocking check (floor take-up and pretension; docs/CONTROL_SYSTEM_V1.md 3.2). floor_displacement uses the reference tilt, so it
    # cannot see a claw that tips about a jaw edge. With >= 2 floor tags in view (tilt noise ~1-3 mrad) the measured TILT change of
    # the claw is watched: the mean of the last 3 frames against max(rocking_tilt_min_rad, rocking_tilt_k x the mean's own sigma) plus
    # rocking_yaw_coupling x |yaw change| (a take-up yaws the claw and a little tilt comes with it). One tag: not watched, logged.
    rocking_tilt_k: float = 5.0                      # sigma multiple (a one-frame 4-5 sigma noise spike does not pass the 3-frame mean)
    rocking_tilt_min_rad: float = 0.004              # ~2 mm of body-origin motion over the 0.52 m from the jaw edge (= onset_translation_m)
    rocking_yaw_coupling: float = 0.08               # tilt allowed per rad of yaw (the rigid-body simulator tilts ~0.03-0.04 per rad of yaw)
    # Floor board survey (SELF_CHECK, roomcleaner/cdpr/board_startup.py): with marker.board_layout_file set, the sheets the resting claw
    # sees are surveyed from this many frames and the layout file is updated; sheets already surveyed that are in view are checked.
    board_survey: bool = True
    board_survey_frames: int = 30
    bearing_sigma_rad: float = 0.15
    bearing_rms_max: float = 3.0                     # slide directions vs anchor entries (whitened)
    lift_slack_budget_m: float = 0.015               # commanded - observed lift before abort
    frame_interval_s: float = 0.1
    still_spread_max_m: float = 0.003
    # Per-pose slack probe while suspended (VISUAL_INITIALIZATION and every CALIBRATION pose):
    # each cable in turn is retracted in small steps until the claw moves (taut onset),
    # the slack is measured, the cable is left just taut, the sample is taken with all
    # four taut and the positions are restored afterwards. See docs/CONTROL_SYSTEM_V1.md 6.1a.
    slack_probe: bool = False                        # opt-in: it deliberately tensions taut cables
    probe_step_m: float = 0.0005                     # smallest retraction step (>= 2 microsteps)
    probe_max_step_m: float = 0.002                  # steps grow (x1.5) up to this while no response is seen
    probe_max_m: float = 0.040                       # max total retraction per cable per pose, else abort
    probe_rounds: int = 1                            # extra rounds re-probe cables a later probe may have loosened
    probe_frames: int = 10                           # vision frames averaged per probe measurement (base)
    probe_frames_max: int = 40                       # frames may be raised to this where vision is noisy
    probe_settle_s: float = 0.3                      # wait after each step before the vision measurement
    probe_onset_translation_m: float = 0.001         # least fitted claw motion that counts as onset (differential,
                                                     # same pose: half of the floor take-up's absolute 2 mm)
    probe_overshoot_max_m: float = 0.006             # skip a cable whose detection needs more over-retraction
    probe_response_sigma: float = 0.5                # relative 1-sigma of the predicted claw response
    # D26: beads are end-of-travel switches. The bead SEARCH (REFERENCE_VERIFICATION, homing.py) is optional
    # and off by default; full-workspace trust (VERIFIED) is granted by the ceiling / wall margins instead
    # (startup.py ``assess_margin_trust``). If on, D24's gating (k*sigma <= window, 2*k*sigma <= overtravel)
    # still applies and a verified bead is extra evidence.
    bead_search: bool = False


@dataclass
class FaultConfig:
    tracking_tol_counts: int | None = None
    tracking_dwell_s: float | None = None
    lease_s: float | None = None
    clock_uncertainty_max_s: float | None = None
    telemetry_max_age_s: float | None = None
    sync_interval_s: float = 0.2


@dataclass
class CalibrationConfig:
    min_samples: int = 20
    witness_samples: int = 5
    witness_rms_max_m: float = 0.006
    noise_capture_frames: int = 10
    bead_k_sigma: float = 3.0
    bead_length_sigma_max_m: float = 0.010          # predicted L sigma allowed before a bead approach
    local_box_m: list = field(default_factory=lambda: [0.15, 0.15, 0.10])
    expanded_box_m: list = field(default_factory=lambda: [0.80, 0.80, 0.50])
    fit_payout_scale: bool = False
    length_sigma_m: float = 0.001                   # spool-model / stretch noise per length reading
    attitude_sigma_rad: float = 0.010               # roll/pitch error of the attitude used for each sample (D27: vision
                                                    # only, no IMU; was 0.004 with the IMU); with spaced attachments it
                                                    # moves b_i by |b_i| * sigma
    onset_sigma_m: float = 0.010                    # taut-onset length observation (low weight)
    data_sv_min: float = 1.0                        # data info >= prior info in every direction
    length_sigma_max_m: float = 0.005               # predicted L sigma allowed in the work volume
    norm_rms_max: float = 2.0                       # whitened residual RMS (model adequacy)
    huber_k: float = 2.5                            # robust weighting threshold (sigmas)
    outlier_k: float = 5.0                          # sample rejected beyond this (sigmas)
    slack_k: float = 3.0                            # longest-cable excess classifying it slack
    payout_scale_sigma: float = 0.003               # spool-model scale uncertainty (bead gate)
    ambiguity_dchi2: float = 25.0                   # alternate optimum closer than this -> ambiguous


@dataclass
class TaskConfig:
    hamper_room_m: list | None = None               # hamper opening centre (x, y), room frame
    hamper_radius_m: float = 0.20
    max_payload_kg: float = 0.9                     # jeans (requirement)
    scan_height_m: float = 1.2                      # claw origin height for scanning
    approach_clearance_m: float = 0.25              # lowest point above the item before descending
    grip_clearance_m: float = 0.01                  # lowest point above the floor when closing
    release_clearance_m: float = 0.35               # lowest point above the hamper rim height
    hamper_height_m: float = 0.6
    grip_settle_s: float = 0.8
    verify_shift_m: float = 0.25                    # move toward the hamper before pickup verification
    max_grip_attempts: int = 3
    max_consecutive_failures: int = 3
    # grip approval on the host (D27): wait until the claw is still, then check the tilt
    grip_still_rate_rad_s: float = 0.02             # camera-observed image motion (rad/s: pixel shift / (fx dt)) below which
                                                    # the claw counts as still
    grip_still_frames: int = 5                      # ... for this many consecutive frame pairs
    grip_settle_periods: float = 5.0                # no camera motion signal: dwell this many pendulum periods
    grip_settle_min_s: float = 2.0                  # floor on that dwell (a short pendulum length gives tiny periods)
    grip_period_margin: float = 1.25                # x the simple-pendulum period (a rigid claw is a compound pendulum, ~20 % longer)
    grip_settle_timeout_s: float = 15.0             # give up waiting for stillness after this long


@dataclass
class Authorization:
    suspended_motion_authorized: bool = False
    qualified_by: str | None = None
    qualification_ref: str | None = None


@dataclass
class SystemConfig:
    room_m: np.ndarray                     # (width X, depth Y, height Z)
    room_surveyed: bool
    stations: list[StationConfig]
    claw: ClawConfig
    marker: MarkerConfig
    camera: CameraConfig
    motion: MotionConfig
    startup: StartupConfig
    faults: FaultConfig
    calibration: CalibrationConfig
    authorization: Authorization
    tasks: TaskConfig = field(default_factory=TaskConfig)
    obstacles: list = field(default_factory=list)   # vertical cylinders {x,y,r,z_low,z_high}
    profile: str = "hardware"
    source: str | None = None
    inactive_stations: list = field(default_factory=list)   # records of the stations that are not mounted (never configured/armed)

    # ---------------------------------------------------------------- access
    def station(self, sid: str) -> StationConfig:
        """The record of an ACTIVE station (KeyError for an inactive or unknown one: the host never touches those)."""
        for s in self.stations:
            if s.id == sid:
                return s
        raise KeyError(sid)

    def record(self, sid: str) -> StationConfig:
        """The record of any of the four stations, active or not (the setup page may edit the anchor of an unmounted one)."""
        for s in self.stations + self.inactive_stations:
            if s.id == sid:
                return s
        raise KeyError(sid)

    @property
    def ids(self) -> list[str]:
        """Ids of the ACTIVE stations, in A-D order."""
        return [s.id for s in self.stations]

    @property
    def inactive_ids(self) -> list[str]:
        return [s.id for s in self.inactive_stations]

    @property
    def all_stations(self) -> list[StationConfig]:
        return sorted(self.stations + self.inactive_stations, key=lambda s: STATION_IDS.index(s.id))

    @property
    def n_active(self) -> int:
        return len(self.stations)

    def station_index(self, sid: str) -> int:
        """Place of ``sid`` in the per-station arrays of the file (A-D order, four long)."""
        return STATION_IDS.index(sid)

    def max_slack_for(self, sid: str) -> float:
        return float(self.startup.max_slack_m[self.station_index(sid)])

    def start_point_xy(self) -> np.ndarray:
        """Where the claw starts (floor, room frame): ``marker.position_prior_room_m`` if set; else the room centre for four
        stations (unchanged), else the centroid of the active anchors' floor projection (three stations: the room centre
        may lie on the triangle's edge, where one cable goes slack)."""
        if self.marker.position_prior_room_m is not None:
            return np.asarray(self.marker.position_prior_room_m, float)
        if self.n_active == 4:
            return np.asarray(self.room_m[:2], float) / 2
        return self.anchor_priors()[:, :2].mean(axis=0)

    def tension_floor_fraction(self) -> float | None:
        """Three-cable statics: the least share lambda_i of the claw's weight that cable i must carry,
        ``T_floor / (m g)``; None if the claw mass is not set yet. See ``kinematics.Workspace``."""
        m = self.claw.mass_kg
        return None if not m else float(self.motion.min_tension_n) / (float(m) * G_ACC)

    def anchor_priors(self) -> np.ndarray:
        """Room-frame anchor priors; missing entries default to upper corners."""
        W, D, H = self.room_m
        default = {"A": (0, 0, H), "B": (W, 0, H), "C": (W, D, H), "D": (0, D, H)}
        out = []
        for s in self.stations:
            out.append(s.anchor_room_m if s.anchor_room_m is not None else np.array(default[s.id], float))
        return np.array(out, float)

    def attachment_points(self) -> np.ndarray:
        """(n_active, 3) attachment points in the body frame, one per ACTIVE station (the file lists all four, A-D)."""
        b = np.asarray(self.claw.attachment_points_body_m, float)
        if self.claw.attachment == "common":
            return np.repeat(b[:1], len(self.stations), axis=0)
        return b[[STATION_IDS.index(s.id) for s in self.stations]]

    # ------------------------------------------------------- authorization
    STAGE_REQUIREMENTS = {
        "station_bench": [
            "stations[*].drive.max_step_rate_hz", "stations[*].encoder.sign",
            "stations[*].encoder.max_age_s", "faults.tracking_tol_counts",
            "faults.tracking_dwell_s", "faults.lease_s", "faults.telemetry_max_age_s",
        ],
        "synchronized_motion": [
            "faults.clock_uncertainty_max_s", "motion.max_cable_speed_m_s",
            "motion.max_cable_accel_m_s2", "stations[*].spool.line_diameter_m",
            "stations[*].spool.line_total_m",
        ],
        "floor_startup": [
            "claw.mass_kg", "claw.T_body_cam", "claw.lowest_point_body_m",
            "marker.edge_m", "marker.heading_prior_rad", "camera.intrinsics_file",
            "camera.max_frame_age_s", "startup.probe_packet_m", "startup.probe_speed_m_s",
            "startup.max_slack_m", "startup.onset_backoff_m", "startup.lift_packet_m",
            "startup.max_lift_m", "startup.max_lateral_drift_m", "motion.max_tension_n",
        ],
        "calibration": ["motion.max_cart_speed_m_s", "motion.max_cart_accel_m_s2"],
        "bead_verification": [
            "stations[*].bead.trigger_length_m", "stations[*].bead.uncertainty_m",
            "stations[*].bead.approach_speed_m_s", "stations[*].bead.search_window_m",
            "stations[*].bead.max_overtravel_m", "stations[*].bead.backoff_m",
            "stations[*].bead.repeatability_tol_m",
        ],
    }
    STAGE_ORDER = ["station_bench", "synchronized_motion", "floor_startup", "calibration",
                   "bead_verification"]

    def _get(self, path: str):
        obj: Any = self
        for part in path.split("."):
            obj = getattr(obj, part)
        return obj

    def missing(self, stage: str) -> list[str]:
        """Unset measured fields required for ``stage`` (and all earlier stages)."""
        needed: list[str] = []
        for st in self.STAGE_ORDER[: self.STAGE_ORDER.index(stage) + 1]:
            needed += self.STAGE_REQUIREMENTS[st]
        out = []
        for path in needed:
            if path.startswith("stations[*]."):
                rest = path[len("stations[*]."):]
                for s in self.stations:
                    if s.id == "_":
                        continue
                    obj: Any = s
                    for part in rest.split("."):
                        obj = getattr(obj, part)
                    if obj is None and not (rest.startswith("bead.") and not s.bead.present):
                        out.append(f"stations[{s.id}].{rest}")
            elif self._get(path) is None:
                out.append(path)
        if stage != "station_bench" and not self.authorization.suspended_motion_authorized:
            out.append("authorization.suspended_motion_authorized")
        return out

    def require(self, stage: str) -> None:
        m = self.missing(stage)
        if m:
            raise ConfigError(f"stage '{stage}' is not authorized; unmeasured/unset: " + ", ".join(m))

    # -------------------------------------------------------------- hashing
    def station_firmware_params(self, sid: str) -> dict:
        """The subset pushed to a station; its hash must match before ARM."""
        s = self.station(sid)
        lease = self.faults.lease_s
        return {
            "sid": s.id,
            "usteps_per_rev": s.drive.usteps_per_rev,
            "step_sign": s.drive.step_sign,
            "max_rate_hz": s.drive.max_step_rate_hz,
            "counts_per_rev": s.encoder.counts_per_rev,
            "enc_sign": s.encoder.sign,
            "enc_max_age_us": None if s.encoder.max_age_s is None else int(round(s.encoder.max_age_s * 1e6)),
            "track_tol": self.faults.tracking_tol_counts,
            "track_dwell_us": None if self.faults.tracking_dwell_s is None else int(round(self.faults.tracking_dwell_s * 1e6)),
            "lease_us": None if lease is None else int(round(lease * 1e6)),
            "sw_nc": s.bead.switch_normally_closed,
            "debounce_us": int(round(s.bead.debounce_s * 1e6)),
            "hold_us": int(round(self.motion.hold_time_s * 1e6)),
        }


# ---------------------------------------------------------------------------
def _dc(cls, d: dict | None, name: str):
    d = dict(d or {})
    known = {f for f in cls.__dataclass_fields__}
    unknown = set(d) - known
    if unknown:
        raise ConfigError(f"{name}: unknown keys {sorted(unknown)}")
    return cls(**d)


def _T_from(d, name):
    if d is None:
        return None
    t = _vec(d.get("translation_m"), name + ".translation_m", allow_none=False)
    r = _vec(d.get("rpy_rad", [0, 0, 0]), name + ".rpy_rad", allow_none=False)
    return make_T(rpy_to_matrix(*r), t)


def _parse_active(raw: dict) -> tuple:
    """The active station ids of a config dict, in A-D order (default: all four). JSON key ``stations_active``
    (``"stations.active"`` is the same key spelt the way the spec writes it). Refuses, with the reason: a value that is not a
    list of strings, an unknown id, a duplicate, fewer than three or more than four stations."""
    keys = [k for k in ("stations_active", "stations.active") if k in raw]
    vals = [raw[k] for k in keys]
    if len(vals) == 2 and vals[0] != vals[1]:
        raise ConfigError(f"stations_active and 'stations.active' are both set and differ ({vals[0]!r} vs {vals[1]!r}): use one")
    stray = [k for k in raw if k not in ("stations_active", "stations.active") and "active" in k.lower() and "station" in k.lower()]
    if stray:
        raise ConfigError(f"unknown config key {stray}: the active stations are chosen with 'stations_active' "
                          f"(a list of 3 or 4 of {list(STATION_IDS)}); a misspelt key would silently run all four")
    v = vals[0] if vals else None
    if v is None:
        return STATION_IDS
    if not isinstance(v, (list, tuple)) or not all(isinstance(x, str) for x in v):
        raise ConfigError(f"stations_active must be a list of station ids such as [\"A\", \"B\", \"C\"], got {v!r}")
    dup = sorted({x for x in v if list(v).count(x) > 1})
    if dup:
        raise ConfigError(f"stations_active {list(v)}: duplicate station id(s) {dup} (list each station once)")
    unknown = [x for x in v if x not in STATION_IDS]
    if unknown:
        raise ConfigError(f"stations_active {list(v)}: unknown station id(s) {unknown} (known ids: {', '.join(STATION_IDS)})")
    if not 3 <= len(v) <= 4:
        raise ConfigError(f"stations_active {list(v)}: {len(v)} station(s); three-station mode needs 3 or 4 distinct ids from "
                          f"{', '.join(STATION_IDS)} (a point claw is not held by two cables)")
    return tuple(x for x in STATION_IDS if x in v)


def triangle_geometry(xy) -> dict:
    """Area (m^2), the three side lengths (m) and the three altitudes (m, altitude i is vertex i's height over the opposite
    side) of the triangle with the vertices ``xy`` ((3, 2), floor projection of the anchors)."""
    P = np.asarray(xy, float).reshape(3, 2)
    area = 0.5 * abs((P[1, 0] - P[0, 0]) * (P[2, 1] - P[0, 1]) - (P[2, 0] - P[0, 0]) * (P[1, 1] - P[0, 1]))
    sides = np.array([np.linalg.norm(P[(i + 1) % 3] - P[(i + 2) % 3]) for i in range(3)])      # side i is opposite vertex i
    alt = 2.0 * area / np.maximum(sides, 1e-12)
    return {"area_m2": float(area), "sides_m": sides, "altitudes_m": alt}


def _check_triangle(cfg: "SystemConfig") -> None:
    """Three active stations: their anchors' floor projections must span a triangle with positive area (and no sliver)."""
    if cfg.n_active != 3:
        return
    xy = cfg.anchor_priors()[:, :2]
    ids = "/".join(cfg.ids)
    if not np.all(np.isfinite(xy)):
        raise ConfigError(f"stations_active {cfg.ids}: an anchor of stations {ids} is not a finite position")
    g = triangle_geometry(xy)
    if g["area_m2"] < 1e-9:
        raise ConfigError(f"stations_active {cfg.ids}: the anchors of stations {ids} are collinear or coincide (floor-projection "
                          "triangle of zero area): three cables hold the claw only inside a triangle with positive area. "
                          "Move one anchor off the line of the other two")
    if float(np.min(g["altitudes_m"])) < MIN_TRIANGLE_ALTITUDE_M:
        raise ConfigError(f"stations_active {cfg.ids}: the anchors of stations {ids} span a degenerate triangle (area "
                          f"{g['area_m2']:.3f} m^2, shortest altitude {float(np.min(g['altitudes_m'])):.2f} m < "
                          f"{MIN_TRIANGLE_ALTITUDE_M} m): the claw would be held only along a line. Spread the three anchors out")
    lam = cfg.tension_floor_fraction()
    if lam is not None and lam >= 1.0 / 3.0:
        raise ConfigError(f"motion.min_tension_n = {cfg.motion.min_tension_n:g} N is {lam:.2f} of the claw's weight "
                          f"({cfg.claw.mass_kg:g} kg): with three cables every one must carry at least that share, which is "
                          "impossible at or above 1/3 (no pose would be feasible). Lower the tension floor")


def load_config(path_or_dict) -> SystemConfig:
    if isinstance(path_or_dict, (str, Path)):
        src = str(path_or_dict)
        raw = json.loads(Path(path_or_dict).read_text())
    else:
        src, raw = None, dict(path_or_dict)
    if raw.get("schema_version") != 1:
        raise ConfigError("schema_version must be 1")
    room = raw["room"]
    room_m = np.array([_f(room["width_m"], "room.width_m", positive=True, allow_none=False),
                       _f(room["depth_m"], "room.depth_m", positive=True, allow_none=False),
                       _f(room["height_m"], "room.height_m", positive=True, allow_none=False)])
    stations = []
    for sd in raw["stations"]:
        sd = dict(sd)
        st = StationConfig(
            id=sd.pop("id"),
            anchor_room_m=_vec(sd.pop("anchor_room_m", None), "anchor_room_m"),
            anchor_sigma_m=_f(sd.pop("anchor_sigma_m", 0.10), "anchor_sigma_m", positive=True),
            address=sd.pop("address", None),
            drive=_dc(DriveConfig, sd.pop("drive", None), "drive"),
            encoder=_dc(EncoderConfig, sd.pop("encoder", None), "encoder"),
            spool=_dc(SpoolConfig, sd.pop("spool", None), "spool"),
            bead=_dc(BeadConfig, sd.pop("bead", None), "bead"),
        )
        if sd:
            raise ConfigError(f"station {st.id}: unknown keys {sorted(sd)}")
        stations.append(st)
    ids = [s.id for s in stations]
    if tuple(ids) != STATION_IDS:
        raise ConfigError(f"stations must be exactly {STATION_IDS} in order, got {ids}")
    active_ids = _parse_active(raw)
    for s in stations:
        if s.drive.step_sign not in (1, -1):
            raise ConfigError(f"{s.id}: drive.step_sign must be +1/-1")
        if s.encoder.sign not in (None, 1, -1):
            raise ConfigError(f"{s.id}: encoder.sign must be +1/-1 or null")
        if s.drive.microsteps not in (1, 2, 4, 8, 16):
            raise ConfigError(f"{s.id}: drive.microsteps must be 1,2,4,8,16 (A4988)")
        if s.encoder.mount not in ("spool", "motor_shaft"):
            raise ConfigError(f"{s.id}: encoder.mount must be spool|motor_shaft")
    cd = dict(raw.get("claw", {}))
    cd.pop("_provenance", None)                      # free-text notes (where the CAD-derived numbers come from)
    claw = ClawConfig(
        attachment=cd.pop("attachment", "common"),
        attachment_points_body_m=np.asarray(cd.pop("attachment_points_body_m", [[0, 0, 0]] * 4), float),
        mass_kg=_f(cd.pop("mass_kg", None), "claw.mass_kg", positive=True),
        T_body_cam=_T_from(cd.pop("camera_in_body", None), "claw.camera_in_body"),
        lowest_point_body_m=_vec(cd.pop("lowest_point_body_m", None), "claw.lowest_point_body_m"),
        com_body_m=_vec(cd.pop("com_body_m", None), "claw.com_body_m"),
        imu=bool(cd.pop("imu", False)),
        grip_tilt_max_rad=_f(cd.pop("grip_tilt_max_rad", math.radians(5)), "claw.grip_tilt_max_rad"),
        vision_attitude_sigma_rad=_f(cd.pop("vision_attitude_sigma_rad", 0.010), "claw.vision_attitude_sigma_rad"),
        vision_attitude_floor_rad=_f(cd.pop("vision_attitude_floor_rad", 0.001), "claw.vision_attitude_floor_rad"),
        statics_attitude_sigma_rad=_f(cd.pop("statics_attitude_sigma_rad", 0.07), "claw.statics_attitude_sigma_rad"),
        mount_offset_max_rad=_f(cd.pop("mount_offset_max_rad", math.radians(5)), "claw.mount_offset_max_rad"),
        address=cd.pop("address", None),
    )
    if cd:
        raise ConfigError(f"claw: unknown keys {sorted(cd)}")
    if claw.attachment not in ("common", "spaced"):
        raise ConfigError("claw.attachment must be common|spaced")
    if claw.attachment_points_body_m.shape not in ((4, 3), (1, 3)):
        raise ConfigError("claw.attachment_points_body_m must be 1 or 4 points")
    if claw.attachment == "spaced" and claw.attachment_points_body_m.shape != (4, 3):
        raise ConfigError("spaced attachment needs 4 points")
    md = dict(raw.get("marker", {}))
    marker = MarkerConfig(
        family=md.pop("family", "apriltag_36h11"), id=int(md.pop("id", 0)),
        edge_m=_f(md.pop("edge_m", None), "marker.edge_m", positive=True),
        heading_prior_rad=_f(md.pop("heading_prior_rad", None), "marker.heading_prior_rad"),
        heading_sigma_rad=_f(md.pop("heading_sigma_rad", math.radians(20)), "marker.heading_sigma_rad", positive=True),
        position_prior_room_m=_vec(md.pop("position_prior_room_m", None), "marker.position_prior_room_m", n=2),
        position_sigma_m=_f(md.pop("position_sigma_m", 0.5), "marker.position_sigma_m", positive=True),
        board_layout_file=_check_board_layout_file(md.pop("board_layout_file", None)),
    )
    if md:
        raise ConfigError(f"marker: unknown keys {sorted(md)}")
    cfg = SystemConfig(
        room_m=room_m, room_surveyed=bool(room.get("surveyed", False)),
        stations=[s for s in stations if s.id in active_ids], inactive_stations=[s for s in stations if s.id not in active_ids],
        claw=claw, marker=marker,
        camera=_dc(CameraConfig, raw.get("camera"), "camera"),
        motion=_dc(MotionConfig, raw.get("motion"), "motion"),
        startup=_dc(StartupConfig, raw.get("startup"), "startup"),
        faults=_dc(FaultConfig, raw.get("faults"), "faults"),
        calibration=_dc(CalibrationConfig, raw.get("calibration"), "calibration"),
        authorization=_dc(Authorization, raw.get("authorization"), "authorization"),
        tasks=_dc(TaskConfig, raw.get("tasks"), "tasks"),
        obstacles=list(raw.get("obstacles", [])),
        profile=raw.get("profile", "hardware"), source=src,
    )
    if cfg.startup.max_slack_m is not None and len(cfg.startup.max_slack_m) != 4:
        raise ConfigError("startup.max_slack_m needs 4 values (A-D; the entries of inactive stations are ignored)")
    su = cfg.startup
    for k in ("probe_step_m", "probe_max_step_m", "probe_max_m", "probe_settle_s", "probe_onset_translation_m",
              "probe_overshoot_max_m", "probe_response_sigma"):
        _f(getattr(su, k), f"startup.{k}", positive=True, allow_none=False)
    if not su.probe_step_m <= su.probe_max_step_m <= su.probe_max_m:
        raise ConfigError("startup: need probe_step_m <= probe_max_step_m <= probe_max_m")
    if not isinstance(su.probe_rounds, int) or isinstance(su.probe_rounds, bool) or not 1 <= su.probe_rounds <= 3:
        raise ConfigError("startup.probe_rounds must be an integer 1..3")
    if not isinstance(su.probe_frames, int) or isinstance(su.probe_frames, bool) or su.probe_frames < 3:
        raise ConfigError("startup.probe_frames must be an integer >= 3")
    if not isinstance(su.probe_frames_max, int) or isinstance(su.probe_frames_max, bool) \
            or su.probe_frames_max < su.probe_frames:
        raise ConfigError("startup.probe_frames_max must be an integer >= probe_frames")
    if not isinstance(su.slack_probe, bool):
        raise ConfigError("startup.slack_probe must be true/false")
    if not isinstance(su.bead_search, bool):
        raise ConfigError("startup.bead_search must be true/false")
    if not isinstance(su.board_survey, bool):
        raise ConfigError("startup.board_survey must be true/false")
    if not isinstance(su.board_survey_frames, int) or isinstance(su.board_survey_frames, bool):
        raise ConfigError("startup.board_survey_frames must be an integer")
    for k, v in (("motion.workspace_margin_m", cfg.motion.workspace_margin_m),
                 ("motion.ceiling_margin_m", cfg.motion.ceiling_margin_m),
                 ("motion.task_max_height_m", cfg.motion.task_max_height_m)):
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not v >= 0:
            raise ConfigError(f"{k} must be a number >= 0")
    cl, ca = cfg.claw, cfg.calibration
    for k, v in (("claw.grip_tilt_max_rad", cl.grip_tilt_max_rad), ("claw.vision_attitude_sigma_rad", cl.vision_attitude_sigma_rad),
                 ("claw.vision_attitude_floor_rad", cl.vision_attitude_floor_rad),
                 ("camera.corner_sigma_px", cfg.camera.corner_sigma_px), ("camera.pose_cov_inflate", cfg.camera.pose_cov_inflate),
                 ("tasks.grip_period_margin", cfg.tasks.grip_period_margin),
                 ("claw.statics_attitude_sigma_rad", cl.statics_attitude_sigma_rad),
                 ("claw.mount_offset_max_rad", cl.mount_offset_max_rad),
                 ("calibration.attitude_sigma_rad", ca.attitude_sigma_rad)):
        _f(v, k, positive=True, allow_none=False)
    if not isinstance(cl.imu, bool):
        raise ConfigError("claw.imu must be true/false")
    if cl.grip_tilt_max_rad > math.radians(20) or cl.mount_offset_max_rad > math.radians(20):
        raise ConfigError("claw.grip_tilt_max_rad / mount_offset_max_rad above 20 deg is not a sane limit")
    if not cl.imu and ca.attitude_sigma_rad < cl.vision_attitude_sigma_rad:
        raise ConfigError("calibration.attitude_sigma_rad is below claw.vision_attitude_sigma_rad although the claw has "
                          "no IMU (D27): the calibration would trust the attitude more than vision can deliver")
    tk = cfg.tasks
    for k in ("grip_still_rate_rad_s", "grip_settle_periods", "grip_settle_timeout_s"):
        _f(getattr(tk, k), f"tasks.{k}", positive=True, allow_none=False)
    _f(tk.grip_settle_min_s, "tasks.grip_settle_min_s", allow_none=False)
    if tk.grip_settle_min_s < 0 or tk.grip_settle_timeout_s < tk.grip_settle_min_s:
        raise ConfigError("tasks: need 0 <= grip_settle_min_s <= grip_settle_timeout_s")
    if not isinstance(tk.grip_still_frames, int) or isinstance(tk.grip_still_frames, bool) or tk.grip_still_frames < 2:
        raise ConfigError("tasks.grip_still_frames must be an integer >= 2")
    # physical ranges (ATTITUDE_BOUNDS): after the plain checks above so their messages stay as they were
    for key, v in (("camera.corner_sigma_px", cfg.camera.corner_sigma_px), ("camera.pose_cov_inflate", cfg.camera.pose_cov_inflate),
                   ("claw.vision_attitude_floor_rad", cl.vision_attitude_floor_rad),
                   ("tasks.grip_period_margin", tk.grip_period_margin), ("tasks.grip_still_rate_rad_s", tk.grip_still_rate_rad_s),
                   ("tasks.grip_still_frames", tk.grip_still_frames), ("tasks.grip_settle_periods", tk.grip_settle_periods),
                   ("tasks.grip_settle_min_s", tk.grip_settle_min_s), ("tasks.grip_settle_timeout_s", tk.grip_settle_timeout_s),
                   ("startup.board_survey_frames", su.board_survey_frames), ("startup.rocking_tilt_k", su.rocking_tilt_k), ("startup.rocking_tilt_min_rad", su.rocking_tilt_min_rad),
                   ("startup.rocking_yaw_coupling", su.rocking_yaw_coupling)):
        _in_range(v, key)
    # (There is deliberately no check of the settle dwell against grip_settle_timeout_s: wait_until_still extends the timeout of a
    # loaded release to max(timeout, dwell + 2 dt) and the no-signal dwell is not bounded by it, so every combination of the
    # ranges above can be approved; the removed check hard-coded a 1.5 s period and refused configs that work, review L2.)
    # the still-rate limit has to clear the noise of a claw that does not move at the configured corner noise and frame interval, or
    # the settle gate never opens (it fails closed: an availability fault, but one that only shows on the robot). wait_until_still
    # measures the rate over startup.frame_interval_s, so that is the interval of the noise rate (review N3).
    dt_frame = _f(su.frame_interval_s, "startup.frame_interval_s", positive=True, allow_none=False)
    floor_rate = still_rate_noise_floor_rad_s(cfg.camera.corner_sigma_px, dt_frame)
    need = STILL_RATE_NOISE_K * floor_rate
    if tk.grip_still_rate_rad_s < need:
        ratio = tk.grip_still_rate_rad_s / floor_rate
        # Measured with the real gate on a still claw (review of the keep-alive fix, 400 runs per case, 1 / 2 / 4 floor tags): a limit at
        # 1.4 x the noise rate opens within ~0.5 s (median); at 1.0-1.2 x it always opens but after 1-2.5 s (up to 6 s); at 0.9 x
        # only 75 / 48 / 20 % of the runs open within the 15 s timeout; at 0.6 x none. The message says which of these the ratio is.
        if ratio < 0.9:
            effect = ("the gate would see five quiet frame pairs in a row only rarely and could not approve a grip or release "
                      "(measured on a still claw: 0.9 x opens in 75 / 48 / 20 % of the runs with 1 / 2 / 4 floor tags, 0.6 x in none)")
        elif ratio < 1.0:
            effect = ("the gate would open on a still claw only some of the time within the settle timeout (measured at "
                      "0.9 x: 75 / 48 / 20 % of the runs with 1 / 2 / 4 floor tags), so grips and releases would often time out")
        else:
            effect = ("the gate would open on a still claw, but only after seconds of waiting (measured median 1-2.5 s, up "
                      "to 6 s with one floor tag; at 1.4 x about 0.5 s), so grips and releases would be slow")
        raise ConfigError(
            f"tasks.grip_still_rate_rad_s = {tk.grip_still_rate_rad_s:g} rad/s is below {STILL_RATE_NOISE_K:g} x the image rate "
            f"that sensor noise alone gives a claw that does not move at camera.corner_sigma_px = {cfg.camera.corner_sigma_px:g} px and "
            f"startup.frame_interval_s = {dt_frame:g} s ({floor_rate:.2g} rad/s = sqrt(pi) x sigma / (520 px x {dt_frame:g} s): "
            f"the gate averages corner-shift norms, which do not average to zero). At {ratio:.2f} x that rate {effect}. "
            f"Raise tasks.grip_still_rate_rad_s to at least {need:.2g} rad/s, lower camera.corner_sigma_px (measure it on the real "
            f"camera) or lengthen startup.frame_interval_s")
    if cfg.claw.vision_attitude_floor_rad > cl.vision_attitude_sigma_rad:
        raise ConfigError("claw.vision_attitude_floor_rad is above claw.vision_attitude_sigma_rad: the floor added to a "
                          "frame's own covariance would exceed the constant sigma it replaces")
    k_ = cfg.calibration.bead_k_sigma
    if not isinstance(k_, (int, float)) or isinstance(k_, bool) or not k_ > 0:
        raise ConfigError("calibration.bead_k_sigma must be a positive number")
    _check_triangle(cfg)
    return cfg


def config_to_jsonable(cfg: SystemConfig) -> dict:
    def conv(o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, dict):
            return {k: conv(v) for k, v in o.items()}
        if isinstance(o, list):
            return [conv(v) for v in o]
        return o
    out = conv(asdict(cfg))
    out["stations_active"] = list(cfg.ids)
    return out
