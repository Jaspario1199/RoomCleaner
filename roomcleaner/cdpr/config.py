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
    vision_attitude_sigma_rad: float = 0.010         # honest 1-sigma of roll OR pitch from a vision pose (D27); no IMU
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


@dataclass
class CameraConfig:
    intrinsics_file: str | None = None
    max_frame_age_s: float | None = None
    pose_sigma_m: float = 0.005                      # per-axis, used to weight the fit
    pose_sigma_rad: float = 0.01
    min_marker_pixels: float = 40.0
    max_reprojection_px: float = 2.0
    ambiguity_ratio_min: float = 3.0                 # 2nd/1st reprojection error to accept


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
    grip_still_speed_m_s: float = 0.02              # camera-observed speed below which the claw counts as still
    grip_still_frames: int = 5                      # ... for this many consecutive frame pairs
    grip_settle_periods: float = 5.0                # no camera motion signal: dwell this many pendulum periods
    grip_settle_min_s: float = 2.0                  # floor on that dwell (a short pendulum length gives tiny periods)
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

    # ---------------------------------------------------------------- access
    def station(self, sid: str) -> StationConfig:
        for s in self.stations:
            if s.id == sid:
                return s
        raise KeyError(sid)

    @property
    def ids(self) -> list[str]:
        return [s.id for s in self.stations]

    def anchor_priors(self) -> np.ndarray:
        """Room-frame anchor priors; missing entries default to upper corners."""
        W, D, H = self.room_m
        default = {"A": (0, 0, H), "B": (W, 0, H), "C": (W, D, H), "D": (0, D, H)}
        out = []
        for s in self.stations:
            out.append(s.anchor_room_m if s.anchor_room_m is not None else np.array(default[s.id], float))
        return np.array(out, float)

    def attachment_points(self) -> np.ndarray:
        b = np.asarray(self.claw.attachment_points_body_m, float)
        if self.claw.attachment == "common":
            return np.repeat(b[:1], 4, axis=0)
        return b

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
    )
    if md:
        raise ConfigError(f"marker: unknown keys {sorted(md)}")
    cfg = SystemConfig(
        room_m=room_m, room_surveyed=bool(room.get("surveyed", False)), stations=stations,
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
        raise ConfigError("startup.max_slack_m needs 4 values (A-D)")
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
    for k, v in (("motion.workspace_margin_m", cfg.motion.workspace_margin_m),
                 ("motion.ceiling_margin_m", cfg.motion.ceiling_margin_m),
                 ("motion.task_max_height_m", cfg.motion.task_max_height_m)):
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not v >= 0:
            raise ConfigError(f"{k} must be a number >= 0")
    cl, ca = cfg.claw, cfg.calibration
    for k, v in (("claw.grip_tilt_max_rad", cl.grip_tilt_max_rad), ("claw.vision_attitude_sigma_rad", cl.vision_attitude_sigma_rad),
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
    for k in ("grip_still_speed_m_s", "grip_settle_periods", "grip_settle_timeout_s"):
        _f(getattr(tk, k), f"tasks.{k}", positive=True, allow_none=False)
    _f(tk.grip_settle_min_s, "tasks.grip_settle_min_s", allow_none=False)
    if tk.grip_settle_min_s < 0 or tk.grip_settle_timeout_s < tk.grip_settle_min_s:
        raise ConfigError("tasks: need 0 <= grip_settle_min_s <= grip_settle_timeout_s")
    if not isinstance(tk.grip_still_frames, int) or isinstance(tk.grip_still_frames, bool) or tk.grip_still_frames < 2:
        raise ConfigError("tasks.grip_still_frames must be an integer >= 2")
    k_ = cfg.calibration.bead_k_sigma
    if not isinstance(k_, (int, float)) or isinstance(k_, bool) or not k_ > 0:
        raise ConfigError("calibration.bead_k_sigma must be a positive number")
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
    return conv(asdict(cfg))
