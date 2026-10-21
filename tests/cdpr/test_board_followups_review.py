"""Independent review of the board-attitude follow-ups (config ranges, floor rocking watch, board survey at startup),
see verification/board_followups_review.md.

The tests record the reviewer's own derivations and are written to PASS when the finding they document is true; a test that
starts failing means the code or the finding changed. Nothing here edits code or configuration.
Everything is simulation: the real corner noise, the real host CPU and the real lease are unmeasured.
Runtime: about 15 seconds (a few thousand frames through the real BoardDetector, no full startup).
"""
import inspect
import math
import time
from types import SimpleNamespace

import numpy as np
import pytest

from roomcleaner.cdpr import frames as F
from roomcleaner.cdpr.attitude import image_motion_rad_s, settle_dwell_s, wait_until_still
from roomcleaner.cdpr.config import ATTITUDE_BOUNDS, ConfigError, config_to_jsonable, load_config
from roomcleaner.cdpr.frames import make_T
from roomcleaner.cdpr.perception import PoseObs, VisionSource, tilt_change
from roomcleaner.cdpr.startup import RockWatch, StartupSequencer
from roomcleaner.cdpr.vision import board as VB
from roomcleaner.cdpr.vision.board import BoardDetector, DEFAULT_PITCH_M, FloorBoardLayout

from .simkit import SIM, fast_cfg
from .test_attitude import FakeCtx, _obs
from .test_board_attitude import CAM, EDGE_B, T_B_C, cam_pose, tag_corners
from .test_board_followups import _StillCamera, _errors, _ref_and_frames, _survey_robot, _surveyor, _truth

EXAMPLE = "config/robot.example.json"

# Every numeric default of the sections the follow-ups could have touched, as they were at commit 180b015 (dumped from a
# `git archive` of that commit, `robot.sim.json`).
BASE_180B015 = {
    "calibration": {'ambiguity_dchi2': 25.0, 'attitude_sigma_rad': 0.01, 'bead_k_sigma': 3.0, 'bead_length_sigma_max_m': 0.01,
                    'data_sv_min': 1.0, 'huber_k': 2.5, 'length_sigma_m': 0.001, 'length_sigma_max_m': 0.005, 'min_samples': 20,
                    'noise_capture_frames': 10, 'norm_rms_max': 2.0, 'onset_sigma_m': 0.01, 'outlier_k': 5.0,
                    'payout_scale_sigma': 0.003, 'slack_k': 3.0, 'witness_rms_max_m': 0.006, 'witness_samples': 5},
    "startup": {'battery_min_v': 7.0, 'bearing_rms_max': 3.0, 'bearing_sigma_rad': 0.15, 'bearing_translation_m': 0.006,
                'floor_height_tol_m': 0.03, 'frame_interval_s': 0.1, 'lift_packet_m': 0.005, 'lift_slack_budget_m': 0.015,
                'max_lateral_drift_m': 0.05, 'max_lift_m': 0.25, 'max_marker_wait_s': 120.0, 'max_tilt_rad': 0.13962634015954636,
                'onset_backoff_m': 0.02, 'onset_noise_k': 4.0, 'onset_tilt_rad': 0.010471975511965976,
                'onset_translation_m': 0.002, 'probe_frames': 10, 'probe_frames_max': 40, 'probe_max_m': 0.04,
                'probe_max_step_m': 0.002, 'probe_onset_translation_m': 0.001, 'probe_overshoot_max_m': 0.006,
                'probe_packet_m': 0.002, 'probe_response_sigma': 0.5, 'probe_rounds': 1, 'probe_settle_s': 0.3,
                'probe_speed_m_s': 0.005, 'probe_step_m': 0.0005, 'settle_s': 0.5, 'still_samples': 10,
                'still_spread_max_m': 0.003, 'target_clearance_m': 0.075},
    "tasks": {'approach_clearance_m': 0.25, 'grip_clearance_m': 0.01, 'grip_period_margin': 1.25, 'grip_settle_min_s': 2.0,
              'grip_settle_periods': 5.0, 'grip_settle_s': 0.8, 'grip_settle_timeout_s': 15.0, 'grip_still_frames': 5,
              'grip_still_rate_rad_s': 0.02, 'hamper_height_m': 0.6, 'hamper_radius_m': 0.2, 'max_consecutive_failures': 3,
              'max_grip_attempts': 3, 'max_payload_kg': 0.9, 'release_clearance_m': 0.35, 'scan_height_m': 1.2,
              'verify_shift_m': 0.25},
    "claw": {'grip_tilt_max_rad': 0.08726646259971647, 'statics_attitude_sigma_rad': 0.07, 'vision_attitude_floor_rad': 0.001,
             'vision_attitude_sigma_rad': 0.01},
    "camera": {'ambiguity_ratio_min': 3.0, 'corner_sigma_px': 0.3, 'max_frame_age_s': 0.5, 'max_reprojection_px': 2.0,
               'min_marker_pixels': 40.0, 'pose_cov_inflate': 1.3, 'pose_sigma_m': 0.004, 'pose_sigma_rad': 0.01},
}


# ====================================================================== 1. configuration ranges
def test_no_existing_default_changed_and_only_the_new_startup_keys_were_added():
    """The follow-ups touched no acceptance threshold: every numeric default of calibration / startup / tasks / claw / camera is
    the one of 180b015 (both profiles share the dataclass defaults here), and the only additions are the five new startup keys."""
    for prof in (SIM, EXAMPLE):
        cur = config_to_jsonable(load_config(prof))
        for sec, base in BASE_180B015.items():
            for key, v in base.items():
                if prof == EXAMPLE and cur[sec][key] is None:
                    continue                                              # the hardware example keeps unmeasured limits null
                assert cur[sec][key] == pytest.approx(v, rel=1e-12), (prof, sec, key)
        numeric = {k for k, v in cur["startup"].items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        assert numeric - set(BASE_180B015["startup"]) == {"board_survey_frames", "rocking_tilt_k", "rocking_tilt_min_rad",
                                                         "rocking_yaw_coupling"}
        assert cur["startup"]["board_survey"] is True and cur["startup"]["slack_probe"] is False


def test_thirteen_bounded_keys_and_both_shipped_profiles_sit_inside_them():
    assert len(ATTITUDE_BOUNDS) == 13
    for prof in (SIM, EXAMPLE):
        cur = config_to_jsonable(load_config(prof))
        for key, (lo, hi, unit, why) in ATTITUDE_BOUNDS.items():
            sec, name = key.split(".")
            assert lo <= cur[sec][name] <= hi, (prof, key)


def _noisy_still(rng, px, n_tags=3):
    """PoseObs of a claw that does not move: only the corner detection noise differs from frame to frame."""
    base = np.vstack([np.array([[100, 100], [150, 100], [150, 150], [100, 150]], float) + 60 * k for k in range(n_tags)])

    def obs(t):
        return PoseObs(True, "", make_T(np.eye(3), [0, 0, 0.5]), np.eye(3) * 1e-6, t * 1e6,
                       corners=base + rng.normal(0, px, base.shape), up_cam=np.array([0, 0, -1.0]))
    return obs


# converted after fix: M1
def test_still_claw_image_rate_noise_is_10_mrad_per_s_not_4_so_the_lower_bound_and_its_reason_are_wrong_fixed():
    """config.ATTITUDE_BOUNDS said a still claw's rate noise is 0.3 px x sqrt(2) / (520 px x 0.1 s) = 8e-3 rad/s per corner and
    4e-3 over the four corners of a tag. image_motion_rad_s averages the corner shift NORMS, which do not average to zero
    (Rayleigh mean 1.2533 sigma): the noise-only rate is 1.0e-2 rad/s however many corners, so a limit between the old lower
    bound 0.005 and ~0.010 never opens, and it does not scale away with more tags. FIXED: the lower bound is now above that
    noise floor (0.015 = 1.4 x 1.0e-2), a limit under it is refused by load_config, and the shipped 0.02 still opens."""
    rng = np.random.default_rng(1)
    fx = CAM.fx
    for n_tags in (1, 3, 4):
        base = np.vstack([np.array([[100, 100], [150, 100], [150, 150], [100, 150]], float) + 60 * k for k in range(n_tags)])
        r = []
        for _ in range(1500):
            a = SimpleNamespace(corners=base + rng.normal(0, 0.3, base.shape), t_us=0.0)
            b = SimpleNamespace(corners=base + rng.normal(0, 0.3, base.shape), t_us=1e5)
            r.append(image_motion_rad_s(a, b, fx))
        r = np.array(r)
        assert 0.0095 < r.mean() < 0.0110                       # 2.5 x the stated 4e-3, independent of the number of corners
        assert np.mean(r <= 0.005) < 0.05                        # the OLD lower bound (0.005) was below the noise floor
        assert np.mean(r <= 0.015) > 0.90                        # the new lower bound passes >= 95 % of the pairs (one tag; more with more tags)
        assert ATTITUDE_BOUNDS["tasks.grip_still_rate_rad_s"][0] > r.mean()
    # the lower bound is now above the noise floor and load_config refuses a limit under it, because a still claw is never
    # approved with it (anything under ~0.009)
    lo = ATTITUDE_BOUNDS["tasks.grip_still_rate_rad_s"][0]
    assert lo == 0.015
    with pytest.raises(ConfigError, match=r"tasks\.grip_still_rate_rad_s = 0\.008 .*outside the physically sensible range"):
        fast_cfg(**{"tasks.grip_still_rate_rad_s": 0.008})
    cfg = fast_cfg()
    cfg.tasks.grip_still_rate_rad_s = 0.008                              # bypass load_config: what the gate itself does with it
    res = wait_until_still(FakeCtx(cfg, _noisy_still(np.random.default_rng(2), 0.3)))
    assert not res.ok and "still moving" in res.reason
    # ... the new lowest accepted limit and the shipped 0.02 open at the stated corner noise
    res = wait_until_still(FakeCtx(fast_cfg(**{"tasks.grip_still_rate_rad_s": lo}), _noisy_still(np.random.default_rng(2), 0.3)))
    assert res.ok and res.method == "camera"
    res = wait_until_still(FakeCtx(fast_cfg(), _noisy_still(np.random.default_rng(3), 0.3)))
    assert res.ok and res.method == "camera"


# converted after fix: M1
def test_no_cross_check_between_corner_noise_and_the_still_rate_limit_fixed():
    """corner_sigma_px may be anything up to 2 px and the still-rate limit anything down to 0.005, independently: at 1 px the
    noise-only rate (0.034 rad/s) is above the shipped 0.02, so the settle gate can never open (fail-closed, an availability
    fault, not a safety one). load_config used to accept the combination; FIXED: it refuses a limit under 1.4 x the noise-only
    rate of the configured corner noise, and says why."""
    with pytest.raises(ConfigError, match=r"grip_still_rate_rad_s = 0\.02 rad/s is below 1\.4 x the image rate .*corner_sigma_px = 1 px"):
        fast_cfg(**{"camera.corner_sigma_px": 1.0})
    cfg = fast_cfg()
    cfg.camera.corner_sigma_px = 1.0                                       # bypass load_config: the combination the old code accepted
    assert cfg.tasks.grip_still_rate_rad_s == 0.02
    res = wait_until_still(FakeCtx(cfg, _noisy_still(np.random.default_rng(4), 1.0)))
    assert not res.ok                                                      # the gate really cannot open: the refusal is warranted
    ok = fast_cfg(**{"camera.corner_sigma_px": 1.0, "tasks.grip_still_rate_rad_s": 0.05})     # 1.4 x 0.034 = 0.048
    assert wait_until_still(FakeCtx(ok, _noisy_still(np.random.default_rng(4), 1.0))).ok
    # and 0.5 px, inside the range and one of the two values the brief asks about, passes only about 90 % of the pairs
    rng = np.random.default_rng(5)
    base = np.vstack([np.array([[100, 100], [150, 100], [150, 150], [100, 150]], float) + 60 * k for k in range(3)])
    r = np.array([image_motion_rad_s(SimpleNamespace(corners=base + rng.normal(0, 0.5, base.shape), t_us=0.0),
                                     SimpleNamespace(corners=base + rng.normal(0, 0.5, base.shape), t_us=1e5), CAM.fx)
                  for _ in range(1500)])
    assert 0.80 < np.mean(r <= 0.02) < 0.95
    with pytest.raises(ConfigError, match="corner_sigma_px = 0.5 px"):       # ... so 0.5 px with the shipped 0.02 is refused as well
        fast_cfg(**{"camera.corner_sigma_px": 0.5})
    assert fast_cfg(**{"camera.corner_sigma_px": 0.5, "tasks.grip_still_rate_rad_s": 0.025})


# converted after fix: L2
def test_dwell_cross_check_rejects_configurations_the_gate_can_run_so_its_message_is_not_true_fixed():
    """'periods x margin x 1.5 s > timeout: a loaded release could never be approved' is false in the code: wait_until_still
    extends the timeout of a loaded release to the full dwell (max(timeout, dwell + 2 dt)), and the dwell of the no-signal branch
    is not bounded by the timeout at all. The check was conservative, not wrong in effect (it only refused a config that would
    work). FIXED: the check is removed; load_config accepts the configuration and the gate approves a loaded release with it."""
    cfg = fast_cfg(**{"tasks.grip_settle_periods": 10.0})                  # used to raise "could never be approved"
    assert cfg.tasks.grip_settle_periods == 10.0
    dwell = settle_dwell_s(cfg.claw, cfg.tasks, cfg.tasks.max_payload_kg)
    assert dwell > cfg.tasks.grip_settle_timeout_s                         # 15.6 s against the 15 s timeout
    ctx = FakeCtx(cfg, lambda t: _obs(t))                                  # a camera that sees a perfectly still claw
    res = wait_until_still(ctx, payload_kg=cfg.tasks.max_payload_kg)
    assert res.ok and res.method == "camera" and res.waited_s >= dwell - 0.2


def test_compound_pendulum_margin_lower_bound_is_the_exact_ratio_for_an_assumed_gyration_radius():
    """The bound 1.2 is sqrt(1 + (k/L)^2) for k = 0.13 m, a radius of gyration that is not measured (review F8c). It leaves no
    allowance for k: a uniform rod of the claw's length (k = 0.517 m / sqrt(12) = 0.149 m) gives 1.26, above the shipped 1.25. The
    loaded claw (payload at the jaw tips) is much closer to a point pendulum (1.10), so the loaded dwell is conservative."""
    cfg = load_config(SIM)
    L = 0.196
    assert ATTITUDE_BOUNDS["tasks.grip_period_margin"][0] == 1.2
    assert math.sqrt(1 + (0.13 / L) ** 2) == pytest.approx(1.2, abs=0.002)
    assert math.sqrt(1 + (0.517 / math.sqrt(12) / L) ** 2) > cfg.tasks.grip_period_margin
    m, mp, Lp = 0.6, 0.9, 0.5173
    Lc = (m * L + mp * Lp) / (m + mp)
    ratio_loaded = math.sqrt((m * (0.13 ** 2 + L ** 2) + mp * Lp ** 2) / ((m + mp) * Lc ** 2))
    assert ratio_loaded == pytest.approx(1.10, abs=0.01)


# converted after fix: L1
def test_rocking_k_lower_bound_of_three_gives_false_trips_in_most_take_ups_fixed():
    """startup.rocking_tilt_k = 3 was inside the range; the range's own reason says 'several false alarms per take-up'. A take-up is
    about 430 watch evaluations (the implementer's 1721 in 4 take-ups) of overlapping 3-frame means: simulated here with iid
    2-D noise, k = 3 trips in most take-ups, k = 4 in a few percent, k = 5 (the default) essentially never. FIXED: the lower bound
    is 4, so the value that trips in 98 % of the take-ups is refused by load_config."""
    assert ATTITUDE_BOUNDS["startup.rocking_tilt_k"][0] == 4.0
    with pytest.raises(ConfigError, match=r"startup\.rocking_tilt_k = 3\.0 is outside the physically sensible range \[4, 10\]"):
        fast_cfg(**{"startup.rocking_tilt_k": 3.0})
    assert fast_cfg(**{"startup.rocking_tilt_k": 4.0}).startup.rocking_tilt_k == 4.0
    rng = np.random.default_rng(7)
    n_takeups, n_eval = 400, 430
    frac = {}
    for k in (3.0, 4.0, 5.0):
        trips = 0
        for _ in range(n_takeups):
            e = rng.normal(0, 1.0, (n_eval + 2, 2))
            m = (e[:-2] + e[1:-1] + e[2:]) / 3.0
            trips += bool(np.any(np.hypot(m[:, 0], m[:, 1]) > k / math.sqrt(3.0)))
        frac[k] = trips / n_takeups
    assert frac[3.0] > 0.5 and 0.01 < frac[4.0] < 0.35 and frac[5.0] < 0.01


def test_board_layout_file_check_depends_on_the_working_directory(tmp_path, monkeypatch):
    """load_config now touches the file system: a relative layout path is valid or not depending on where the process runs, so a
    profile cannot be validated off the robot (documented in the error text; the service opens the file the same way)."""
    import json
    FloorBoardLayout(0.150).save(tmp_path / "layout.json")
    raw = json.load(open(SIM))
    raw["marker"]["board_layout_file"] = "layout.json"
    monkeypatch.chdir(tmp_path)
    assert load_config(raw).marker.board_layout_file == "layout.json"
    other = tmp_path / "elsewhere"
    other.mkdir()
    monkeypatch.chdir(other)
    with pytest.raises(ConfigError, match="working directory"):
        load_config(raw)


# ====================================================================== 2. rocking watch through the real detector
class _RealBoardVision:
    """Corner pixel noise -> the real BoardDetector (solvePnP + Cramer-Rao covariance) -> VisionSource -> PoseObs, which is what
    RockWatch sees on the robot. The watch's own tests draw the pose error from the covariance model the watch uses; this does not."""

    def __init__(self, true_px, cfg_px, seed):
        self.cfg = load_config(SIM)
        self.lay = FloorBoardLayout.nominal(0.150, DEFAULT_PITCH_M)
        self.det = BoardDetector(self.lay, CAM, corner_sigma_px=cfg_px, cov_inflate=self.cfg.camera.pose_cov_inflate)
        self.rng = np.random.default_rng(seed)
        self.true_px = true_px
        self.T = None
        self.now = 1.0e6
        self.v = VisionSource(SimpleNamespace(observe=self._observe), T_B_C, CAM.fx, 0.150, max_age_s=10.0,
                              now_us=lambda: self.now, rot_floor=self.cfg.claw.vision_attitude_floor_rad, pixel_sigma=cfg_px)

    def _observe(self, _now):
        T_C_M = F.inv_T(self.T @ T_B_C)
        dets = {}
        for i in self.lay.surveyed_ids():
            P = self.lay.corners_M(i) @ T_C_M[:3, :3].T + T_C_M[:3, 3]
            if np.any(P[:, 2] < 0.05):
                continue
            uv = CAM.project(P)
            dets[i] = uv + self.rng.normal(0, self.true_px, uv.shape)
        return self.det.pose_from_detections(dets, up_in_cam=(0, 0, -1), capture_us=self.now)

    def at(self, T):
        self.T = T
        return self

    def reference(self):
        fr = []
        while len(fr) < 10:
            o = self.v.observe()
            if o.ok:
                fr.append(o)
        return self.v._summarise(fr)

    def watch(self, ref):
        st = self.cfg.startup
        return RockWatch(ref, k=st.rocking_tilt_k, min_rad=st.rocking_tilt_min_rad, yaw_coupling=st.rocking_yaw_coupling,
                         floor_rad=self.cfg.claw.vision_attitude_floor_rad, n=3)

    def poses_by_tags(self, per_n=3, seed=0):
        """Resting poses on the board whose reference shows 2, 3 and 4 tags."""
        rng, out, tries = np.random.default_rng(seed), {2: [], 3: [], 4: []}, 0
        while any(len(v) < per_n for v in out.values()) and tries < 400:
            tries += 1
            T = F.make_T(F.rot_z(rng.uniform(-math.pi, math.pi)), [*rng.uniform(-0.30, 0.30, 2), 0.5173])
            self.T = T
            o = self.v.observe()
            if o.ok and o.n_tags in out and len(out[o.n_tags]) < per_n:
                out[o.n_tags].append(T)
        return out


def _rocked(T0, theta, u, d=0.04):
    """T0 after tipping by ``theta`` about a floor line ``d`` behind the body axis, the top leaning toward the unit vector ``u``."""
    p0, R0 = T0[:3, 3], T0[:3, :3]
    e = np.array([p0[0] - d * u[0], p0[1] - d * u[1], 0.0])
    Q = F.rotvec_to_matrix(theta * np.cross([0, 0, 1.0], [u[0], u[1], 0.0]))
    return F.make_T(Q @ R0, e + Q @ (p0 - e))


def _rest_statistics(rv, poses, frames):
    """(trips, thresholds by tag count, mean |mean tilt|^2 / its model variance) over resting windows."""
    trips, thr, z2 = 0, {}, []
    for n, Ts in poses.items():
        for T in Ts:
            ref = rv.at(T).reference()
            w = rv.watch(ref)
            hit = False
            for _ in range(frames):
                o = rv.v.observe()
                if not o.ok:
                    continue
                hit |= bool(w.update(o))
                if len(w.win) == 3:
                    thr.setdefault(n, []).append(w.last_thr_rad)
                    m = np.mean([x[0] for x in w.win], axis=0)
                    z2.append(float(m @ m) / (np.mean([x[1] for x in w.win]) / 3 + tilt_change(o, ref)[2]))
            trips += hit
    return trips, thr, float(np.mean(z2))


def test_rocking_watch_through_the_real_detector_matched_noise_never_trips_at_rest_and_sees_a_15_mrad_rock_with_3_tags():
    rv = _RealBoardVision(0.3, 0.3, seed=11)
    poses = rv.poses_by_tags(per_n=3, seed=3)
    assert all(len(v) == 3 for v in poses.values())
    trips, thr, z2 = _rest_statistics(rv, poses, frames=120)
    assert trips == 0                                                      # 9 windows x 120 frames, 0.3 px true = configured
    # the detector's covariance is calibrated: E|m|^2 / var = 2 / 1.3^2 = 1.18 if exact (mean over a few windows)
    assert 0.9 < z2 < 1.7
    med = {n: float(np.median(v)) for n, v in thr.items()}
    assert med[2] > 0.012 and 0.007 < med[3] < 0.011 and 0.006 < med[4] < 0.009        # 5 sigma, not the 4 mrad floor
    assert min(min(v) for v in thr.values()) > 0.0055                       # the 4 mrad floor is never the binding term
    # detection: a rock of 25 mrad (13 mm of body-origin motion) in every case; 15 mrad with >= 3 tags within 6 frames;
    # 10 mrad is NOT reliably seen with 2 tags (threshold ~15 mrad)
    u = np.array([math.cos(1.1), math.sin(1.1)])
    seen = {}
    for n, Ts in poses.items():
        for th in (0.010, 0.015, 0.025):
            for T in Ts:
                ref = rv.at(T).reference()
                w = rv.watch(ref)
                rv.at(_rocked(T, th, u))
                lat = None
                for k in range(25):
                    o = rv.v.observe()
                    if o.ok and w.update(o):
                        lat = k + 1
                        break
                seen.setdefault((n, th), []).append(lat)
    assert all(l is not None and l <= 10 for n in (2, 3, 4) for l in seen[(n, 0.025)])
    assert all(l is not None and l <= 6 for n in (3, 4) for l in seen[(n, 0.015)])
    assert sum(l is not None for l in seen[(2, 0.010)]) <= 1


def test_rocking_watch_covariance_is_understated_when_the_configured_corner_noise_is_too_small():
    """True corner noise 0.5 px while camera.corner_sigma_px says 0.3: the reported tilt variance is 2.8x too small (E z^2 = 3.35
    against 1.18), the 5 sigma threshold is effectively 3 sigma. Not a code error (corner_sigma_px has to be measured, which the
    follow-ups say) but the range [0.05, 2] cannot protect against it, and a 2x error is enough for false stops in about half of the
    take-ups (analytic: P = exp(-25 / z2) per evaluation; 2x -> 5.6e-3 per evaluation, about 143 independent looks)."""
    rv = _RealBoardVision(0.5, 0.3, seed=12)
    poses = rv.poses_by_tags(per_n=2, seed=4)
    trips, thr, z2 = _rest_statistics(rv, poses, frames=100)
    assert z2 > 2.5
    p_eval = math.exp(-25.0 / (z2 * 1.0))                                   # per-evaluation trip probability for a 5 sigma rule
    p_eval_2x = math.exp(-25.0 / (1.206 * 4.0))
    assert 1.0 - (1.0 - p_eval_2x) ** 143 > 0.4
    assert p_eval > 1e-4


def test_one_tag_fallback_only_logs_and_the_watch_never_fires():
    """With one tag in the reference the watch is inert, the log says so once, measurements say 'blind' and nothing else is
    different from 180b015 (startup.py: 'rocked' stays False, so the onset test is `disp >= thr or False` and the slide direction
    comes from floor_displacement, as before)."""
    r = __import__("roomcleaner.cdpr.sim.harness", fromlist=["SimRobot"]).SimRobot(fast_cfg(), seed=1)
    S = StartupSequencer(r.ctx)
    v, ref = _ref_and_frames(tag_corners(0.0, 0.0, 0.1524), [F.make_T(F.rot_y(0.2), [0.0, 0.0, 0.5173])] * 60, 1)
    assert ref.n_tags == 1
    rw = S._rock_watch(ref, "station A take-up")
    S._rock_watch(ref, "station B take-up")
    assert not rw.can_see and not any(rw.update(v.observe()) for _ in range(50))           # 200 mrad of tilt, nothing
    logs = [x for x in r.log_lines if "cannot be seen" in x]
    assert len(logs) == 1 and "1 floor tag in view (station A take-up)" in logs[0]
    m = S.rep.measurements
    assert m["rocking_check"].startswith("blind") and m["rocking_blind_at"] == ["station A take-up", "station B take-up"]
    src = inspect.getsource(StartupSequencer.slack_takeup)
    assert "if mon[\"onset\"] is None and (disp >= thr or rocked):" in src
    assert "(cam_displacement if mon[\"rocked\"] else floor_displacement)" in src


# ====================================================================== 3. board survey: blocking time and the lease
def test_self_check_survey_runs_before_the_stations_are_configured_or_armed_so_its_stall_is_harmless():
    src = inspect.getsource(StartupSequencer.self_check)
    assert src.index("self._survey_board(S)") < src.index("co.configure()") < src.index("co.arm(")


def _armed_survey_robot(tmp_path):
    r, truth, path = _survey_robot(tmp_path=tmp_path)
    co = r.co
    co.wait(300000)
    co.configure()
    co.wait_synced(3.0)
    co.arm()
    co.wait(100000)
    assert all(co.links[s].tel["st"] == 1 and co.links[s].tel["flt"] == 0 for s in "ABCD")
    return r, co


# converted after fix: H1
def test_a_top_up_that_blocks_longer_than_the_lease_lease_faults_every_armed_station_and_pumping_while_it_runs_does_not_fixed(tmp_path):
    """_survey_topup called sv.flush() on the command thread; while a command owns the robot the idle host loop does not pump
    (service.idle_tick), so nothing kept the stations alive. A stall of 0.9 s (the measured CPU time of an accepting flush of
    3-4 windows on this machine; 2-2.5 s with 60 frames) against faults.lease_s = 0.3 (robot.sim.json): all four stations hold
    themselves (Fault.LEASE = 4, state FAULT) and the startup is lost. The same compute done in slices of 0.1 s that pump between
    them (what a worker thread + `ctx.wait` loop does) leaves the stations fault-free. FIXED: _survey_topup runs the flush through
    StartupSequencer._pumped; the unpumped stall is kept here as the evidence (`_pumped` replaced by a direct call = the old
    code), the stall through the real path no longer faults."""
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "c").mkdir()
    r, co = _armed_survey_robot(tmp_path / "a")
    assert r.cfg.faults.lease_s == 0.3 and co.lease_us == pytest.approx(0.3e6)
    S = StartupSequencer(r.ctx)
    S._pumped = lambda fn, *a, **k: fn(*a, **k)                             # the code before the fix: the flush on the command thread
    sv = r.ctx.board_survey
    sv.flush = lambda: (r.rt.wait(0.9e6), None)[1]                          # compute that advances time but does not pump
    S._survey_topup("CALIBRATION")
    co.pump()
    assert all(co.links[s].tel["flt"] == 4 for s in "ABCD")                 # LEASE on all four, as test_service's 1 s stall
    # the real path: the same 0.9 s of host time (the simulated clock only moves while somebody waits: the worker waits for the
    # command thread's pump to take it 0.9 s on) no longer faults a station
    r3, co3 = _armed_survey_robot(tmp_path / "c")
    S3 = StartupSequencer(r3.ctx)
    t0 = r3.rt.now_us()

    def stall():
        deadline = time.monotonic() + 20.0
        while r3.rt.now_us() < t0 + 0.9e6:
            assert time.monotonic() < deadline, "nothing pumps the stations while the top-up computes"
            time.sleep(0.001)
    r3.ctx.board_survey.flush = stall
    S3._survey_topup("CALIBRATION")
    assert r3.rt.now_us() >= t0 + 0.9e6
    co3.pump()
    assert all(co3.links[s].tel["flt"] == 0 for s in "ABCD")
    r2, co2 = _armed_survey_robot(tmp_path / "b")
    S2 = StartupSequencer(r2.ctx)

    def sliced():
        for _ in range(9):
            time.sleep(0.1)                                                 # 0.1 s of "compute" (sliced); the command thread pumps meanwhile
        return None                                                         # (the worker must not drive the coordinator or the simulated
                                                                            # runtime itself: concurrent rt.wait() ticks raced with the command
                                                                            # thread's pump and faulted stations TIMING once the GIL switch
                                                                            # interval of _pumped went down to 0.5 ms; repair round 2)
    r2.ctx.board_survey.flush = sliced
    S2._survey_topup("CALIBRATION")
    co2.pump()
    assert all(co2.links[s].tel["flt"] == 0 for s in "ABCD")


def test_an_accepting_flush_runs_two_bundle_adjustments_that_hit_the_iteration_cap_and_a_cap_of_8_changes_nothing(tmp_path):
    """Where the blocking time goes (cProfile: ~90 % in BoardSurvey._bundle): update() and then refine() each run a bundle
    adjustment with max_nfev = 40 and ftol = xtol = gtol = 1e-10, which is never met, so several runs stop at the cap. Results at
    max_nfev 40 and 8 are identical (same sheets, <0.05 mm apart): the cap alone saves ~2x but not the 3-8x needed to get under
    a 0.3 s lease (a 60-frame flush still costs ~1.2 s CPU at a cap of 3), so the cap is a complement, not the fix."""
    runs = {}
    orig_bundle, orig_ls = VB.BoardSurvey._bundle, VB.least_squares
    try:
        for cap in (40, 8):
            calls = []

            def ls(*a, _calls=calls, **k):
                res = orig_ls(*a, **k)
                _calls.append(res.nfev)
                return res

            def bundle(self, free, init, max_nfev=40, _cap=cap):
                return orig_bundle(self, free, init, max_nfev=min(max_nfev, _cap))
            VB.least_squares, VB.BoardSurvey._bundle = ls, bundle
            truth = _truth(EDGE_B, 2)
            (tmp_path / f"cap{cap}").mkdir()
            sv, lay, _ = _surveyor(tmp_path / f"cap{cap}")
            sv.run(_StillCamera(truth, cam_pose((0.03, -0.02, 0.52)), seed=2), lambda s: None, n_frames=30, interval_s=0.1,
                   edge_m=EDGE_B)
            per_flush = []
            for k, xyz in enumerate([(0.10, 0.05, 0.62), (-0.12, 0.08, 0.80), (0.05, -0.15, 0.95), (-0.05, -0.05, 1.10)]):
                cam = _StillCamera(truth, cam_pose(xyz), seed=10 + k)
                sv.offer([cam.observe() for _ in range(10)])
                calls.clear()
                out = sv.flush()
                per_flush.append((list(out["new"]), list(calls)))
            runs[cap] = (per_flush, lay.surveyed_ids(), max(e[0] for e in _errors(lay, truth).values()))
    finally:
        VB.least_squares, VB.BoardSurvey._bundle = orig_ls, orig_bundle
    full, capped = runs[40], runs[8]
    accepting = [calls for new, calls in full[0] if new]
    assert accepting and all(len(c) == 2 for c in accepting)                # update() + refine()
    assert any(n >= 40 for c in accepting for n in c)                       # never converges to 1e-10: runs to the cap
    assert full[1] == capped[1] and len(full[1]) == 9
    assert abs(full[2] - capped[2]) < 5e-5 and max(full[2], capped[2]) < 5e-4


def test_slack_probe_is_off_in_both_shipped_profiles_and_the_report_says_the_sigma_is_then_not_honest():
    """Recommendation context (section 4 of the review): the default is unchanged and the startup already refuses full-workspace
    trust without the probe, as D26 requires."""
    for prof in (SIM, EXAMPLE):
        assert load_config(prof).startup.slack_probe is False
    src = inspect.getsource(__import__("roomcleaner.cdpr.startup", fromlist=["x"]))
    assert "slack probe was off: the predicted sigma is not honest" in src


def test_the_recommended_fix_works_a_flush_in_a_worker_thread_leaves_the_pump_loop_alive(tmp_path):
    """The fix recommended in the review (startup.py `out = sv.flush()` -> run it on a one-worker executor while the command thread
    loops `ctx.wait(0.02)`): a 60-frame accepting flush (2.3-2.5 s of compute here) in a worker thread, with the main thread sleeping in
    20 ms steps as the keep-alive grid does, keeps a worst loop gap far below the 0.3 s lease (25-28 ms measured; the bound here is the
    half-lease 0.15 s so a loaded machine does not make this flaky), and gives the same sheets as the direct call."""
    import time
    from concurrent.futures import ThreadPoolExecutor
    truth = _truth(EDGE_B, 1)
    sv, lay, _ = _surveyor(tmp_path)
    sv.run(_StillCamera(truth, cam_pose((0.03, -0.02, 0.52)), seed=1), lambda s: None, n_frames=30, interval_s=0.1, edge_m=EDGE_B)
    rr = np.random.default_rng(1)
    for k in range(24):
        cam = _StillCamera(truth, cam_pose((rr.uniform(-0.15, 0.15), rr.uniform(-0.15, 0.15), rr.uniform(0.6, 1.1))), seed=100 + k)
        cam.t = 100.0 * k
        sv.offer([cam.observe() for _ in range(10)])
    assert len(sv._pending) == 60
    with ThreadPoolExecutor(max_workers=1) as pool:
        t0 = time.perf_counter()
        fut = pool.submit(sv.flush)
        stamps = [t0]
        while not fut.done():
            time.sleep(0.02)
            stamps.append(time.perf_counter())
        out = fut.result()
    gaps = np.diff(stamps)
    assert out["frames"] == 60 and len(lay.surveyed_ids()) == 9 and not out["cleared"]
    assert len(gaps) >= 5 and gaps.max() < 0.15, (len(gaps), gaps.max())
    assert max(e[0] for e in _errors(lay, truth).values()) < 1.0e-3
