"""Follow-ups of the independent re-review of the floor-board attitude path (verification/imu_removal_review.md, round 2: R2.2b/e,
R2.5; results in verification/board_followups_results.md).

1. Physical ranges for the new configuration keys (not just finite and > 0), and a layout file that must exist.
2. The rocking check: a claw that tips about a jaw edge while it rests on the floor is seen by the tilt-change channel when >= 2
   board tags are in view, and is reported as not seeable (previous behaviour) with one tag. The simulator can make the resting
   claw rock (``World(rock=...)``).
3. The board survey at startup (``board_startup.FloorBoardSurveyor``) and the printed instructions that describe it.
"""
import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from roomcleaner.cdpr import frames as F
from roomcleaner.cdpr.config import ATTITUDE_BOUNDS, ConfigError, load_config
from roomcleaner.cdpr.perception import cam_displacement, floor_displacement, tilt_change
from roomcleaner.cdpr.startup import RockWatch, StartupAbort, StartupSequencer
from roomcleaner.cdpr.vision.board import DEFAULT_PITCH_M, FloorBoardLayout

from .simkit import SIM, fast_cfg
from .test_board_attitude import CAM, EDGE_B, EDGE_S, T_B_C, _claw, _frames, grid, tag_corners


def _raw(**changes):
    raw = json.load(open(SIM))
    for path, v in changes.items():
        sec, key = path.split(".")
        raw[sec][key] = v
    return raw


# ======================================================================= 1. configuration ranges
# Companion values that keep the cross-checks of load_config satisfied when one key is moved to the edge of its range.
EDGE_COMPANIONS = {
    "claw.vision_attitude_floor_rad": {"claw.vision_attitude_sigma_rad": 0.02, "calibration.attitude_sigma_rad": 0.02},
    "tasks.grip_period_margin": {"tasks.grip_settle_timeout_s": 120.0},
    "tasks.grip_settle_periods": {"tasks.grip_settle_timeout_s": 120.0},
    "tasks.grip_settle_min_s": {"tasks.grip_settle_timeout_s": 120.0},
}


@pytest.mark.parametrize("key", sorted(ATTITUDE_BOUNDS))
def test_every_bounded_key_is_refused_outside_its_range_and_accepted_at_its_edges(key):
    lo, hi, unit, why = ATTITUDE_BOUNDS[key]
    assert len(why) > 60 and lo < hi                                   # a stated reason for every range
    integer = isinstance(lo, int)
    below, above = (lo - 1, hi + 1) if integer else ((lo * 0.5 if lo > 0 else lo - 0.1), hi * 2.0)
    for bad in (below, above, float("nan"), float("inf"), True, "1", None):
        with pytest.raises(ConfigError, match=key.split(".")[1]) as e:
            load_config(_raw(**{**EDGE_COMPANIONS.get(key, {}), key: bad}))
        if bad in (below, above) and not isinstance(bad, (bool, str)) and bad is not None:
            assert "physically sensible range" in str(e.value) and unit in str(e.value)
    for good in (lo, hi):
        assert load_config(_raw(**{**EDGE_COMPANIONS.get(key, {}), key: good}))      # both edges are allowed


def test_the_review_examples_are_refused_with_a_clear_message():
    with pytest.raises(ConfigError, match=r"camera\.pose_cov_inflate = 0\.05 is outside the physically sensible range \[1, 5\]"):
        load_config(_raw(**{"camera.pose_cov_inflate": 0.05}))
    with pytest.raises(ConfigError, match=r"tasks\.grip_period_margin = 0\.05 is outside the physically sensible range \[1\.2, 3\]"):
        load_config(_raw(**{"tasks.grip_period_margin": 0.05}))
    with pytest.raises(ConfigError, match="compound pendulum"):
        load_config(_raw(**{"tasks.grip_period_margin": 0.05}))
    for bad in ("/no/such/dir/floor_board.json", 5, "", "   ", ["a"], True):
        with pytest.raises(ConfigError, match="board_layout_file"):
            load_config(_raw(**{"marker.board_layout_file": bad}))


def test_the_shipped_defaults_and_profiles_sit_inside_their_ranges():
    for path in (SIM, "config/robot.example.json"):
        cfg = load_config(path)
        for key, (lo, hi, unit, why) in ATTITUDE_BOUNDS.items():
            sec, name = key.split(".")
            v = getattr(getattr(cfg, {"camera": "camera", "claw": "claw", "tasks": "tasks", "startup": "startup"}[sec]), name)
            assert lo <= v <= hi, (path, key, v)


def test_board_layout_file_must_name_an_existing_layout(tmp_path):
    good = tmp_path / "layout.json"
    FloorBoardLayout(0.150).save(good)                                 # the starting layout: only the origin known
    cfg = load_config(_raw(**{"marker.board_layout_file": str(good)}))
    assert cfg.marker.board_layout_file == str(good)
    nominal = tmp_path / "nominal.json"
    FloorBoardLayout.nominal(0.150).save(nominal)
    assert load_config(_raw(**{"marker.board_layout_file": str(nominal)})).marker.board_layout_file == str(nominal)
    assert load_config(_raw(**{"marker.board_layout_file": None})).marker.board_layout_file is None
    # does not exist / is a directory / not JSON / not a layout / wrong version / absurd tag size / origin not among the tags
    bad = {"missing": tmp_path / "nope.json", "dir": tmp_path}
    (tmp_path / "text.json").write_text("this is not json")
    bad["text"] = tmp_path / "text.json"
    d = json.loads(good.read_text())
    variants = {"notags": {**d, "tags": []}, "version": {**d, "version": 2}, "edge": {**d, "edge_m": 3.0},
                "origin": {**d, "origin_id": 99}, "list": [1, 2, 3], "edgestr": {**d, "edge_m": "0.15"}}
    for name, content in variants.items():
        (tmp_path / f"{name}.json").write_text(json.dumps(content))
        bad[name] = tmp_path / f"{name}.json"
    for name, path in bad.items():
        with pytest.raises(ConfigError, match="board_layout_file"):
            load_config(_raw(**{"marker.board_layout_file": str(path)}))
    # the message of a missing file says how to make the starting one
    with pytest.raises(ConfigError, match="--layout-json"):
        load_config(_raw(**{"marker.board_layout_file": str(tmp_path / "nope.json")}))


def test_layout_version_known_to_the_config_is_the_one_of_the_board_module():
    from roomcleaner.cdpr import config
    assert config._LAYOUT_VERSION == FloorBoardLayout.VERSION


def test_the_settle_dwell_has_to_fit_into_the_timeout():
    """5 periods x 3 x 1.5 s = 22.5 s > 15 s: a loaded release could never be approved."""
    with pytest.raises(ConfigError, match="loaded release could never be approved"):
        load_config(_raw(**{"tasks.grip_period_margin": 3.0}))
    assert load_config(_raw(**{"tasks.grip_period_margin": 3.0, "tasks.grip_settle_timeout_s": 30.0}))


def test_the_floor_added_to_a_frames_covariance_may_not_exceed_the_constant_sigma_it_replaces():
    with pytest.raises(ConfigError, match="vision_attitude_floor_rad is above claw.vision_attitude_sigma_rad"):
        load_config(_raw(**{"claw.vision_attitude_floor_rad": 0.012}))


# ======================================================================= 2. rocking check
def _rocked(theta, *, pivot=(0.04, 0.0), z=0.5173, yaw=0.0):
    """T_M_B of a claw standing on the floor (jaw tips at z = 0 in the marker frame, body origin ``z`` above) after it tipped by
    ``theta`` about a horizontal axis through the jaw edge at ``pivot`` (pull along +x: the top moves toward +x)."""
    R0 = F.rot_z(yaw)
    p0 = np.array([0.0, 0.0, z])
    e = np.array([pivot[0], pivot[1], 0.0])
    Q = F.rot_y(theta)                                        # turns the top toward +x
    return F.make_T(Q @ R0, e + Q @ (p0 - e))


def _ref_and_frames(P, poses, seed, px=0.3):
    v = _frames(P, [_claw(0.0, 0.0, 0.5173)] * 10 + list(poses), np.random.default_rng(seed), px=px)
    ref = v._summarise([v.observe() for _ in range(10)])
    return v, ref


def _watch(ref, **kw):
    cfg = load_config(SIM)
    return RockWatch(ref, k=cfg.startup.rocking_tilt_k, min_rad=cfg.startup.rocking_tilt_min_rad,
                     yaw_coupling=cfg.startup.rocking_yaw_coupling, floor_rad=cfg.claw.vision_attitude_floor_rad, **kw)


def test_floor_displacement_is_nearly_blind_to_a_claw_tipping_about_a_jaw_edge_but_the_tilt_change_is_not():
    """15 mrad about the jaw edge 40 mm from the body axis: the body origin moves 7.8 mm (tilt x 0.52 m); floor_displacement
    (reference tilt) reads only tilt x (pivot - tag centroid) ~ 0.6 mm, the general cam_displacement the real 7.8 mm and
    tilt_change the 15 mrad itself."""
    P = grid(DEFAULT_PITCH_M)
    th = 0.015
    truth = _rocked(th)[:3, 3] - np.array([0.0, 0.0, 0.5173])
    v, ref = _ref_and_frames(P, [_rocked(th)] * 20, 1, px=1e-6)
    o = v.observe()
    assert np.linalg.norm(truth) == pytest.approx(0.0078, abs=3e-4)
    assert np.linalg.norm(floor_displacement(o, ref)[0]) < 0.002 < 0.7 * np.linalg.norm(truth)
    assert np.linalg.norm(cam_displacement(o, ref)[0] - truth) < 6e-4
    eps, s_o2, s_r2, psi = tilt_change(o, ref)
    assert np.linalg.norm(eps) == pytest.approx(th, abs=1.5e-4) and abs(psi) < 1e-3
    # and the direction: the top of the claw leans toward the pull (+x), i.e. the displacement of the origin is along +x
    assert cam_displacement(o, ref)[0][0] > 0.9 * np.linalg.norm(truth)


def test_rock_watch_trips_on_rocking_not_on_noise_a_one_frame_spike_or_the_yaw_of_a_take_up():
    P = grid(DEFAULT_PITCH_M)
    # (a) 300 frames of an unmoved claw, noise only: never trips (false alarm rate ~ exp(-k^2/2) = 4e-6 per frame)
    v, ref = _ref_and_frames(P, [_claw(0.0, 0.0, 0.5173)] * 300, 2)
    w = _watch(ref)
    assert w.can_see and not any(w.update(v.observe()) for _ in range(300))
    assert w.max_tilt_rad < 0.5 * w.last_thr_rad                             # a wide margin, not luck
    # (b) 15 mrad of tipping trips it within a few frames and reports it
    v, ref = _ref_and_frames(P, [_rocked(0.015)] * 20, 3)
    w = _watch(ref)
    hits = [w.update(v.observe()) for _ in range(20)]
    assert hits[2] and not hits[1] and w.last_tilt_rad == pytest.approx(0.015, abs=2.5e-3)
    # (c) 4 mrad (2 mm of body-origin motion: inside the noise of the 3-frame mean and below the floor) does not
    v, ref = _ref_and_frames(P, [_rocked(0.004)] * 40, 4)
    w = _watch(ref)
    assert not any(w.update(v.observe()) for _ in range(40))
    # (d) one frame with a tilt outlier of 4.5 sigma of its own reported tilt sigma (a rare noise event; the 0.5 px study had one
    #     of 16 mrad) never trips the 3-frame mean; the same outlier in every frame would
    v, ref = _ref_and_frames(P, [_claw(0.0, 0.0, 0.5173)] * 12, 5)
    w = _watch(ref)
    out = []
    for k in range(12):
        o = v.observe()
        if k == 6:
            sig = math.sqrt(tilt_change(o, ref)[1])
            T = o.T_C_M.copy()
            T[:3, :3] = F.rot_x(4.5 * sig) @ T[:3, :3]
            o.T_C_M = T
        out.append(w.update(o))
    assert not any(out)
    # (e) a take-up yaws the claw about its own axis and a little tilt comes with it (the simulator: ~3-4 % of the yaw):
    #     0.15 rad of yaw with 0.04 x 0.15 = 6 mrad of tilt is no rocking
    R0 = F.rot_z(0.3)
    p = [0.0, 0.0, 0.5173]
    poses = [F.make_T(R0 @ F.rot_z(0.15) @ F.rot_y(0.006), p)] * 20
    v = _frames(P, [F.make_T(R0, p)] * 10 + poses, np.random.default_rng(6))
    ref = v._summarise([v.observe() for _ in range(10)])
    w = _watch(ref)
    assert not any(w.update(v.observe()) for _ in range(20))
    # ... but the same yaw with 30 mrad of tilt is
    poses = [F.make_T(R0 @ F.rot_z(0.15) @ F.rot_y(0.030), p)] * 20
    v = _frames(P, [F.make_T(R0, p)] * 10 + poses, np.random.default_rng(7))
    ref = v._summarise([v.observe() for _ in range(10)])
    w = _watch(ref)
    assert any(w.update(v.observe()) for _ in range(20))


def test_rock_watch_threshold_follows_the_tilt_noise_and_one_tag_cannot_see_rocking_at_all():
    P = grid(DEFAULT_PITCH_M)
    cfg = load_config(SIM)
    st = cfg.startup
    thr = []
    for px in (0.3, 1.2):                                                    # four times the corner noise
        v, ref = _ref_and_frames(P, [_claw(0.0, 0.0, 0.5173)] * 12, 8, px=px)
        w = _watch(ref)
        for _ in range(12):
            o = v.observe()
            w.update(o)
        # the stated rule: max(floor, k x sigma of the 3-frame mean against the reference + the systematic floor) + yaw allowance
        s_o2 = float(np.mean([x[1] for x in w.win]))
        s_r2 = tilt_change(o, ref)[2]
        sig = math.sqrt(s_o2 / 3 + s_r2 + cfg.claw.vision_attitude_floor_rad ** 2)
        want = max(st.rocking_tilt_min_rad, st.rocking_tilt_k * sig) + st.rocking_yaw_coupling * float(np.mean([x[2] for x in w.win]))
        assert w.last_thr_rad == pytest.approx(want, rel=1e-9)
        thr.append(w.last_thr_rad)
    assert thr[1] > 1.4 * thr[0] and thr[0] >= st.rocking_tilt_min_rad       # scaled to the frame's tilt sigma, with the floor
    # ONE tag: 13 mrad of tilt noise per frame; the watch is inert even for a 40 mrad tip, and says so
    one = tag_corners(0.0, 0.0, EDGE_S)
    v, ref = _ref_and_frames(one, [_rocked(0.040)] * 20, 9)
    w = _watch(ref)
    assert not w.can_see and ref.n_tags == 1
    assert not any(w.update(v.observe()) for _ in range(20))
    # a board reference but a frame that has lost all but one tag: that frame carries no tilt information, the window restarts
    v, ref = _ref_and_frames(P, [_rocked(0.020)] * 4, 10)
    w = _watch(ref)
    assert w.can_see
    [w.update(v.observe()) for _ in range(2)]
    o = v.observe()
    o.n_tags = 1
    assert not w.update(o) and w.win == []


# ---- the simulator's rocking option and the startup floor stage
def _rock_robot(board=True, seed=4, rock=None):
    from roomcleaner.cdpr.sim.harness import SimRobot
    from roomcleaner.cdpr.sim.world import FloorBoard
    ck = {"board": FloorBoard.nominal(EDGE_B)} if board else {}
    return SimRobot(fast_cfg(), seed=seed, mount_err_rad=0.02, camera_kw=ck,
                    world_kw={"rock": {"slide": False} if rock is None else rock})


def test_sim_option_rock_tips_the_resting_claw_about_the_jaw_edge_by_the_take_up_it_is_given():
    """The resting claw (friction holds it: ``slide`` False) answers a take-up of cable A beyond the taut point by tipping toward
    the pull, ~2.7 mrad per mm of take-up (1 / attachment height above the pivot), and the cable tension stays at the tipping
    moment (~0.5-0.7 N, far below the 2.4 N of sliding friction): the claw tips INSTEAD of sliding. Without the option it does
    not tilt (it would slide)."""
    from roomcleaner.cdpr.frames import tilt_angle
    r = _rock_robot()
    w = r.world
    d = w.dist()
    p_flat = w.p.copy()
    tilts, forces = [], []
    for stretch in (0.0, 0.001, 0.002, 0.004, 0.008):
        ell = d + 0.05
        ell[0] = d[0] - stretch
        w.ell = lambda ell=ell: ell
        w.settle()
        tilts.append(tilt_angle(w.R))
        forces.append(float(w.tension.max()))
        assert w.eq_failures == 0
    assert tilts[0] == 0.0 and all(a < b for a, b in zip(tilts, tilts[1:]))                 # grows with the take-up
    assert tilts[3] == pytest.approx(0.0112, rel=0.25) and tilts[4] == pytest.approx(0.0228, rel=0.25)
    assert 0.4 < min(forces[1:]) and max(forces) < 0.9 < 0.4 * w.mass * 9.81                 # tipping moment, not friction
    assert w.rock_max_rad == pytest.approx(tilts[-1], rel=1e-9) and not any(e[0] == "tipped" for e in w.events)
    assert 0.0 <= w.lowest_z() < 2e-3                                                          # the jaw tip on the pull side stays down
    assert np.linalg.norm(w.p[:2] - p_flat[:2]) == pytest.approx(tilts[-1] * 0.5173, rel=0.1)   # the origin leans: tilt x lever
    # the plant without the option: no tilt at all (the claw would slide instead)
    r0 = _rock_robot(rock={"slide": True})
    r0.world.rock = None
    ell = r0.world.dist() + 0.05
    ell[0] -= 0.05 + 0.004
    r0.world.ell = lambda: ell
    r0.world.settle()
    assert tilt_angle(r0.world.R) < 1e-6


def test_a_board_floor_stage_stops_a_rocking_claw_at_the_tilt_onset_and_the_four_stations_complete():
    """Pure rocking (friction holds the claw, ``rock = {slide: False}``): floor_displacement reads almost nothing; the tilt
    channel stops each take-up at ~10 mrad (5 sigma of the 3-frame mean) instead of letting the claw tip; the slide directions
    (from the tilt-bearing displacement) still agree with the anchor entries."""
    r = _rock_robot()
    S = StartupSequencer(r.ctx)
    S.self_check()
    S.slack_takeup()
    m = S.rep.measurements
    assert m["rocking_check"] == "active" and "rocking_blind_at" not in m
    tilts = [m[f"rocking_{s}_max_tilt_rad"] for s in "ABCD"]
    assert all(0.004 < t < 0.020 for t in tilts), tilts                      # stopped at the onset: nowhere near the 0.14 rad limit
    assert r.world.rock_max_rad < 0.025 and not any(e[0] == "tipped" for e in r.world.events)
    assert m["bearing_rms"] < r.cfg.startup.bearing_rms_max
    assert len(r.ctx.onsets) == 4
    assert sum("ROCKED" in x for x in r.log_lines) == 4
    assert r.world.eq_failures == 0


def test_with_one_tag_a_rocking_claw_cannot_be_seen_and_the_previous_behaviour_stays():
    """The same claw, one floor tag: the watch is inert, the log and the report say so, nothing stops the take-up at the tilt
    onset (the claw tips on, to ~10x the board's trip angle) and the old guards end it, here the slide-direction check."""
    r = _rock_robot(board=False)
    S = StartupSequencer(r.ctx)
    S.self_check()
    with pytest.raises(StartupAbort):
        S.slack_takeup()
    m = S.rep.measurements
    assert m["rocking_check"].startswith("blind") and m["rocking_blind_at"][0] == "station A take-up"
    assert any("cannot be seen" in x and "1 floor tag" in x for x in r.log_lines)
    assert sum("cannot be seen" in x for x in r.log_lines) == 1              # said once, not per station
    assert r.world.rock_max_rad > 0.05                                         # not stopped at the board's ~0.01
    assert not any("ROCKED" in x for x in r.log_lines)


# ======================================================================= 3. board survey at startup
def _truth(edge, seed, err=0.015, yaw=0.1, pitch=DEFAULT_PITCH_M):
    """The sheets as a user lays them: the nominal grid with a few cm of sloppiness and some rotation (tag 0 defines the frame)."""
    rng = np.random.default_rng(seed + 55)
    lay = FloorBoardLayout.nominal(edge, pitch)
    for i in range(1, 9):
        x, y, _ = lay.pose(i)
        lay.set_pose(i, x + rng.normal(0, err), y + rng.normal(0, err), rng.normal(0, yaw))
    return lay


class _StillCamera:
    """A claw resting on the floor: every observe() is a new frame of the same still view (noisy corner detections of the tags
    of ``truth`` that are fully in the image, like ``PoseObs.dets`` of the board detector)."""

    def __init__(self, truth, T_C_M, seed=0, px=0.3):
        self.truth, self.T, self.px = truth, np.asarray(T_C_M, float), px
        self.rng = np.random.default_rng(seed)
        self.t = 0.0

    def visible_ids(self):
        from .test_board_attitude import in_view
        return [i for i in self.truth.expected_ids if in_view(self.truth.corners_M(i), self.T) is not None]

    def observe(self):
        self.t += 0.1
        dets = {}
        for i in self.visible_ids():
            uv = CAM.project(self.truth.corners_M(i) @ self.T[:3, :3].T + self.T[:3, 3])
            dets[i] = uv + self.rng.normal(0, self.px, uv.shape)
        return SimpleNamespace(ok=True, dets=dets, t_us=self.t * 1e6, duplicate_ids=())


def _surveyor(tmp_path, truth_edge=EDGE_B, **kw):
    from roomcleaner.cdpr.board_startup import FloorBoardSurveyor
    path = tmp_path / "floor_board.json"
    FloorBoardLayout(truth_edge).save(path)                                  # the starting file: only sheet 0 known
    lay = FloorBoardLayout.load(path)
    return FloorBoardSurveyor(lay, CAM, path=path, log=kw.pop("log", lambda *a: None), **kw), lay, path


def _errors(lay, truth, ids=None):
    out = {}
    for i in (lay.surveyed_ids() if ids is None else ids):
        x, y, w = lay.pose(i)
        xt, yt, wt = truth.pose(i)
        out[i] = (math.hypot(x - xt, y - yt), abs(float(np.angle(np.exp(1j * (w - wt))))))
    return out


def test_surveyor_places_the_sheets_in_view_to_better_than_a_millimetre_and_saves_the_layout(tmp_path):
    from .test_board_attitude import cam_pose
    truth = _truth(EDGE_B, 1)
    cam = _StillCamera(truth, cam_pose((0.03, -0.02, 0.52)), seed=1)
    visible = set(cam.visible_ids())
    assert 0 in visible and len(visible) >= 3 and len(visible) < 9               # the resting view sees some of the sheets, not all
    sv, lay, path = _surveyor(tmp_path)
    template = path.read_text()
    out = sv.run(cam, lambda s: None, n_frames=30, interval_s=0.1, edge_m=EDGE_B)
    assert set(out["surveyed_ids"]) == visible and set(out["newly_surveyed"]) == visible - {0}
    errs = _errors(lay, truth, visible - {0})
    assert max(e[0] for e in errs.values()) < 1.0e-3 and max(e[1] for e in errs.values()) < math.radians(0.2), errs
    assert out["max_sigma_xy_m"] < 5e-4 and out["frames"] == 30 and not out["cleared"] and not out["warnings"]
    # every sheet out of view is reported as unsurveyed (with a reason) and is not used
    assert set(out["unsurveyed"]) == set(range(9)) - visible and all(out["unsurveyed"].values())
    # saved: the file holds what was surveyed, the previous contents are kept
    assert out["saved"] == str(path) and FloorBoardLayout.load(path).surveyed_ids() == sorted(visible)
    assert Path(str(path) + ".bak").read_text() == template
    for i in visible - {0}:
        assert np.allclose(FloorBoardLayout.load(path).pose(i), lay.pose(i))
    json.dumps(out)                                                              # the startup report is JSON-friendly


def test_a_second_survey_of_the_same_view_does_not_rewrite_the_file(tmp_path):
    from roomcleaner.cdpr.board_startup import FloorBoardSurveyor
    from .test_board_attitude import cam_pose
    truth = _truth(EDGE_B, 2)
    T = cam_pose((0.02, 0.0, 0.52))
    sv, lay, path = _surveyor(tmp_path)
    sv.run(_StillCamera(truth, T, seed=2), lambda s: None, n_frames=30, interval_s=0.1, edge_m=EDGE_B)
    saved = path.read_text()
    # next startup: same sheets, same view -> verified, nothing to write
    sv2 = FloorBoardSurveyor(FloorBoardLayout.load(path), CAM, path=path, log=lambda *a: None)
    out2 = sv2.run(_StillCamera(truth, T, seed=3), lambda s: None, n_frames=30, interval_s=0.1, edge_m=EDGE_B)
    assert out2["saved"] is None and not out2["cleared"] and not out2["newly_surveyed"] and path.read_text() == saved


@pytest.mark.parametrize("dxy_mm,dyaw_deg", [(3, 0.0), (6, 0.0), (12, 3.0), (30, 6.0), (80, 17.0)])
def test_a_sheet_that_moved_since_the_last_survey_is_found_and_surveyed_again(tmp_path, dxy_mm, dyaw_deg):
    """Between startups a sheet in view was kicked: the saved pose is wrong by 3..80 mm. The detector's consistency check (>= 6 mm)
    flags it, the survey clears it and surveys it afresh in the same startup; a smaller error is simply refined away by the
    bundle adjustment. Either way the layout ends within 1 mm of where the sheet really is."""
    from roomcleaner.cdpr.board_startup import FloorBoardSurveyor
    from .test_board_attitude import cam_pose
    truth = _truth(EDGE_B, 2)
    T = cam_pose((0.02, 0.0, 0.52))
    sv, lay, path = _surveyor(tmp_path)
    sv.run(_StillCamera(truth, T, seed=2), lambda s: None, n_frames=30, interval_s=0.1, edge_m=EDGE_B)
    lay3 = FloorBoardLayout.load(path)
    k = next(i for i in lay3.surveyed_ids() if i != 0)
    x, y, w = lay3.pose(k)
    lay3.set_pose(k, x + dxy_mm * 1e-3, y, w + math.radians(dyaw_deg))                 # the saved pose is stale
    msgs = []
    out = FloorBoardSurveyor(lay3, CAM, path=path, log=msgs.append).run(
        _StillCamera(truth, T, seed=4), lambda s: None, n_frames=30, interval_s=0.1, edge_m=EDGE_B)
    e = _errors(lay3, truth, [k])[k]
    assert k in lay3.surveyed_ids() and e[0] < 1.0e-3 and e[1] < math.radians(0.2), e
    if dxy_mm >= 6:
        assert k in out["cleared"] and "moved" in out["cleared"][k] and any("surveying them again" in m for m in msgs)
    assert out["saved"] == str(path) and np.allclose(FloorBoardLayout.load(path).pose(k), lay3.pose(k))


def test_survey_refuses_a_layout_whose_tag_size_is_not_the_measured_one_and_a_template_adopts_it(tmp_path):
    from roomcleaner.cdpr.board_startup import adopt_edge, edge_mismatch
    sv, lay, path = _surveyor(tmp_path)                                        # layout edge 150.0 mm
    assert edge_mismatch(lay, EDGE_B) is None and edge_mismatch(lay, 0.1503) is None       # 0.2 %: fine
    assert edge_mismatch(lay, None) is None
    msg = edge_mismatch(lay, 0.1524)                                             # 1.6 %
    assert msg and "1.6 %" in msg and "marker.edge_m" in msg and "only ruler" in msg
    from .test_board_attitude import cam_pose
    cam = _StillCamera(_truth(EDGE_B, 1), cam_pose((0.03, -0.02, 0.52)))
    with pytest.raises(ValueError, match="differs from marker.edge_m"):
        sv.run(cam, lambda s: None, n_frames=10, interval_s=0.1, edge_m=0.1524)
    # a layout with nothing surveyed yet takes the measured size; one that was surveyed must agree
    assert adopt_edge(lay, 0.1524) is None and lay.edge_m == 0.1524
    surveyed = FloorBoardLayout.nominal(0.150)
    assert "differs" in adopt_edge(surveyed, 0.1524) and surveyed.edge_m == 0.150


def test_a_layout_file_that_cannot_be_written_is_reported_and_does_not_stop_the_survey(tmp_path):
    from roomcleaner.cdpr.board_startup import FloorBoardSurveyor
    from .test_board_attitude import cam_pose
    blocker = tmp_path / "file"
    blocker.write_text("x")
    msgs = []
    sv = FloorBoardSurveyor(FloorBoardLayout(EDGE_B), CAM, path=blocker / "layout.json", log=msgs.append)   # parent is a file
    out = sv.run(_StillCamera(_truth(EDGE_B, 3), cam_pose((0.03, -0.02, 0.52))), lambda s: None, n_frames=30, interval_s=0.1)
    assert out["newly_surveyed"] and out["saved"] is None and any("could not save" in m for m in msgs)


def test_survey_without_usable_frames_surveys_nothing_and_says_why(tmp_path):
    sv, lay, path = _surveyor(tmp_path)
    blind = SimpleNamespace(observe=lambda: SimpleNamespace(ok=False, dets=None, t_us=None, duplicate_ids=()))
    out = sv.run(blind, lambda s: None, n_frames=10, interval_s=0.1)
    assert out["surveyed_ids"] == [0] and out["frames"] == 0 and out["saved"] is None
    assert set(out["unsurveyed"]) == set(range(1, 9)) and FloorBoardLayout.load(path).surveyed_ids() == [0]


def test_service_adopts_or_refuses_the_layout_edge_and_attaches_the_survey(tmp_path):
    from roomcleaner.cdpr.service import attach_board_survey, build_marker_detector
    cfg = load_config(SIM)                                                        # marker.edge_m 152.4 mm
    tmpl = tmp_path / "template.json"
    FloorBoardLayout(0.150).save(tmpl)
    raw = _raw(**{"marker.board_layout_file": str(tmpl)})
    cfg = load_config(raw)
    det = build_marker_detector(cfg, CAM)
    assert det.layout.edge_m == cfg.marker.edge_m == 0.1524 and det._sel.edge == 0.1524        # the template took the measured size
    ctx = SimpleNamespace(camera=CAM, log=lambda *a: None, floor_board=None, board_survey=None)
    attach_board_survey(ctx, det, cfg)
    assert ctx.board_survey is not None and ctx.board_survey.layout is det.layout and ctx.board_survey.path == tmpl
    assert len(ctx.floor_board.corners) == 1                                       # only sheet 0 known yet
    # switched off: the detector and the design still see the layout, nothing is surveyed
    off = load_config(_raw(**{"marker.board_layout_file": str(tmpl), "startup.board_survey": False}))
    ctx = SimpleNamespace(camera=CAM, log=lambda *a: None, floor_board=None, board_survey=None)
    attach_board_survey(ctx, build_marker_detector(off, CAM), off)
    assert ctx.board_survey is None and ctx.floor_board is not None
    # no layout file: the single tag, nothing attached
    ctx = SimpleNamespace(camera=CAM, log=lambda *a: None, floor_board=None, board_survey=None)
    attach_board_survey(ctx, build_marker_detector(load_config(SIM), CAM), load_config(SIM))
    assert ctx.board_survey is None and ctx.floor_board is None
    # a layout that was surveyed at another tag size is refused at start-up of the service
    other = tmp_path / "surveyed.json"
    FloorBoardLayout.nominal(0.150).save(other)
    with pytest.raises(SystemExit, match="differs from marker.edge_m"):
        build_marker_detector(load_config(_raw(**{"marker.board_layout_file": str(other)})), CAM)


# ---- the startup (SELF_CHECK) with the survey in the loop
def _survey_robot(seed=4, cfg=None, tmp_path=None, **kw):
    from roomcleaner.cdpr.sim.harness import SimRobot
    cfg = cfg or fast_cfg()
    truth = _truth(cfg.marker.edge_m, seed)
    path = None if tmp_path is None else tmp_path / "floor_board.json"
    if path is not None:
        FloorBoardLayout(cfg.marker.edge_m).save(path)
    r = SimRobot(cfg, seed=seed, mount_err_rad=0.02, board_truth=truth, board_path=path, **kw)
    return r, truth, path


def test_self_check_surveys_the_board_first_and_then_the_floor_pose_and_the_mount_use_it(tmp_path):
    r, truth, path = _survey_robot(tmp_path=tmp_path)
    assert r.ctx.board_survey is not None and r.board_layout.surveyed_ids() == [0] and len(r.ctx.floor_board.corners) == 1
    S = StartupSequencer(r.ctx)
    S.self_check()
    m = S.rep.measurements
    bs = m["board_survey"]
    assert bs["ran"] and len(bs["surveyed_ids"]) >= 3 and bs["newly_surveyed"] and bs["frames"] == 30
    # what the startup reports is what is true of the sheets (truth: the sim's own layout), and it is in the file
    errs = _errors(r.board_layout, truth)
    assert max(e[0] for e in errs.values()) < 1.0e-3 and max(e[1] for e in errs.values()) < math.radians(0.2), errs
    assert FloorBoardLayout.load(path).surveyed_ids() == r.board_layout.surveyed_ids() == bs["surveyed_ids"]
    # the design's view of the board was refreshed with the surveyed sheets
    assert len(r.ctx.floor_board.corners) == len(bs["surveyed_ids"])
    # the floor pose and the mount offset were measured on the BOARD (>= 2 tags: ~1 mrad), not on the single tag (13 mrad)
    assert m["floor_tags_in_view"] == len(bs["surveyed_ids"]) >= 3 and m["floor_attitude_sigma_rad"] < 0.004
    assert m["camera_mount_holdout_residual_rad"] < m["camera_mount_holdout_limit_rad"]
    assert any("floor board survey" in x for x in r.log_lines) and any("not surveyed and so not used" in x for x in r.log_lines)
    assert r.world.eq_failures == 0


def test_the_survey_does_not_run_without_a_layout_or_when_switched_off(tmp_path):
    from roomcleaner.cdpr.sim.harness import SimRobot
    # single tag / the study board of the other tests: no surveyor, no report, behaviour unchanged
    r = SimRobot(fast_cfg(), seed=4, mount_err_rad=0.02)
    assert r.ctx.board_survey is None
    S = StartupSequencer(r.ctx)
    S.self_check()
    assert "board_survey" not in S.rep.measurements and S.rep.measurements["floor_tags_in_view"] == 1
    # a layout but startup.board_survey = false: used as it is, the report says it was off
    r, truth, path = _survey_robot(cfg=fast_cfg(**{"startup.board_survey": False}), tmp_path=tmp_path)
    assert r.ctx.board_survey is not None                  # (the SERVICE does not attach one when it is off; the sequencer also checks)
    S = StartupSequencer(r.ctx)
    S.self_check()
    assert S.rep.measurements["board_survey"] == {"ran": False, "why": "startup.board_survey = false"}
    assert r.board_layout.surveyed_ids() == [0] and S.rep.measurements["floor_tags_in_view"] == 1
    assert any("switched off" in x for x in r.log_lines)


def test_self_check_aborts_when_the_layout_tag_size_is_not_the_measured_edge(tmp_path):
    cfg = fast_cfg()
    r, truth, path = _survey_robot(cfg=cfg, tmp_path=tmp_path)
    r.board_layout.edge_m = 0.1400                                                 # layout surveyed at another size than marker.edge_m
    S = StartupSequencer(r.ctx)
    with pytest.raises(StartupAbort, match="differs from marker.edge_m"):
        S.self_check()


# ---- the printed instructions say what the robot does
def test_printed_instructions_describe_the_survey_as_it_is_and_the_starting_layout_file_is_written(tmp_path):
    pytest.importorskip("reportlab")
    pypdf = pytest.importorskip("pypdf")
    from tools import print_floor_board as pfb
    root = Path(__file__).resolve().parents[2] / "prints"
    texts = {"built": " ".join(pypdf.PdfReader(str(pfb.build_pdf(tmp_path / "b.pdf"))).pages[0].extract_text().split()),
             "shipped": " ".join(pypdf.PdfReader(str(root / "floor_board_letter.pdf")).pages[0].extract_text().split())}
    for name, flat in texts.items():
        assert "surveys the layout itself" not in flat, name                        # the old promise
        assert "at EVERY startup the robot SURVEYS the sheets its camera sees from the resting claw" in flat, name
        assert "NOT surveyed and are NOT used" in flat and "usually 2-3 neighbours" in flat, name
        assert "marker.board_layout_file" in flat and "--layout-json" in flat and ".bak" in flat, name
        assert "nothing re-surveys it until the next startup" in flat, name
        assert "run the survey again" not in flat, name                              # there is no such tool
        assert "250 mm centre to centre" in flat and "NEVER cover" in flat, name     # the earlier layout text is intact
    assert texts["built"] == texts["shipped"]                                       # the shipped printout is current
    # the starting layout file: loadable, only the origin known, accepted by the config
    out = pfb.write_layout_template(tmp_path / "d" / "layout.json")
    lay = FloorBoardLayout.load(out)
    assert lay.surveyed_ids() == [0] and lay.expected_ids == list(range(9)) and lay.edge_m == 0.150
    assert load_config(_raw(**{"marker.board_layout_file": str(out)})).marker.board_layout_file == str(out)
    pfb.main(["--layout-json", str(tmp_path / "e.json"), "--no-pdf"])
    assert (tmp_path / "e.json").exists() and not (tmp_path / "prints").exists()
