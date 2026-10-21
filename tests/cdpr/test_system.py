"""Whole-system behaviour in simulation: startup, tasks, faults, recovery.

These run the real sequencer/supervisor/coordinator/station logic against the
physics simulator (roughly 5-60 s wall time each)."""
import numpy as np
import pytest

from roomcleaner.cdpr.calibration import IDS
from roomcleaner.cdpr.homing import BeadVerifier
from roomcleaner.cdpr.kinematics import Geometry, workspace_from_config
from roomcleaner.cdpr.sim.harness import SimRobot
from roomcleaner.cdpr.sim.world import FloorBoard, World
from roomcleaner.cdpr.startup import StartupSequencer
from roomcleaner.cdpr.supervisor import CommandRefused, Supervisor
from roomcleaner.cdpr.tasks import SimItemPerception, TaskRunner
from roomcleaner.cdpr.trajectory import limits_from_config, model_from
from roomcleaner.cdpr.coordinator import Coordinator
from roomcleaner.cdpr.frames import planar_T
from roomcleaner.cdpr.startup import RobotContext
from roomcleaner.cdpr.transport import SimHostTransport
from roomcleaner.cdpr.trust import TrustLedger

from .simkit import (ITEM_CANDIDATES, ModelFrameItemPerception, assert_no_eq_failures, bring_up, build, fast_cfg,
                     item_offsets_with_small_statics_tilt)


def test_full_lifecycle_startup_task_reboot_recovery_park(tmp_path):
    cfg = fast_cfg(**{"startup.bead_search": True})      # D26: the bead search is optional (default off); keep exercising its gating here
    # the floor reference is the printed board (3x3 sheets, 0.25 m pitch, 150 mm tags): the honest noise of the single 6-inch tag
    # at suspended poses (tens of mm per frame, tag-derived) cannot meet the witness criterion and is not what this lifecycle tests
    r = SimRobot(cfg, seed=0, data_dir=tmp_path, camera_kw={"board": FloorBoard.nominal(0.15)})
    sup = Supervisor(r.ctx, state_path=tmp_path / "state.json", ledger_path=tmp_path / "ledger.json")
    assert sup.state == "DISARMED"
    rep = sup.start()
    assert sup.state == "READY", rep.reasons
    assert_no_eq_failures(r, "lifecycle: startup")
    m = rep.measurements
    assert m["camera_mount_offset_rad"] > 0 and r.ctx.mount_angle_rad == m["camera_mount_offset_rad"]   # D27: measured
    # floor stage: every cable found taut within its bound, bearings consistent
    assert all(0 < m[f"slack_{s}_m"] < cfg.startup.max_slack_m[i] for i, s in enumerate(IDS))
    assert m["bearing_rms"] < cfg.startup.bearing_rms_max
    assert abs(m["lift_observed_m"] - m["lift_commanded_m"]) < cfg.startup.lift_slack_budget_m
    # calibration accepted on witnesses; the work-volume model is consistent
    assert m["calibration"]["witness_rms_m"] < cfg.calibration.witness_rms_max_m
    assert (tmp_path / "calibration.json").exists()
    # beads: vision alone cannot pin absolute lengths tightly enough for a safe,
    # complete search with these settings, so they are honestly BLOCKED, not tried;
    # the slack probe is off here, so the margin rule (D26) does not grant VERIFIED either
    assert r.ctx.ledger.level == "LOCAL_ONLY" and r.ctx.ledger.verified_basis is None
    assert m["beads"] and all(b["status"] == "BLOCKED" for b in m["beads"].values())
    for i, s in enumerate(IDS):                    # the reported absolute sigma covers the true error
        err = abs(r.ctx.model.maps[s].L0 - r.world.true_L0(s))
        assert err < 3.5 * m["absolute_sigma_m"][i] + 0.002
    # a task: two items delivered with visual verification. The items lie around where the startup left the claw
    # (inside its scan footprint); where that is depends on the noise stream, so it is not hard-coded to the room centre.
    c = r.world.p[:2].copy()
    r.world.hamper = (np.asarray(cfg.tasks.hamper_room_m), cfg.tasks.hamper_radius_m)
    off_sock, off_jeans = item_offsets_with_small_statics_tilt(r.ctx, ITEM_CANDIDATES)
    r.world.add_item("sock", c + off_sock)
    r.world.add_item("jeans", c + off_jeans, mass=0.9, height=0.08)
    runner = TaskRunner(r.ctx, ModelFrameItemPerception(r.world))
    out = sup.run_task(runner)
    assert sorted(out["done"]) == ["jeans", "sock"] and not out["failed"] and sup.state == "READY", (out, runner.approvals)      # nearest first
    assert all(it["state"] == "hamper" for it in r.world.items)
    # D27: every grip and release was approved on the host after settling (no IMU, no claw-side gate)
    assert len(runner.approvals) == 4 and all(a.get("approved") and a["still_ok"] for a in runner.approvals)
    assert_no_eq_failures(r, "lifecycle: tasks")
    # the host stalls longer than the lease while the claw hangs: every station
    # holds itself; that is a coordinated stop, references are kept (review C2)
    r.rt.wait(1.0e6)
    sup.poll()
    assert sup.state == "FAULT" and r.ctx.ledger.all_valid()
    sup.acknowledge()
    assert sup.state == "READY", sup.reasons[-3:]
    assert_no_eq_failures(r, "lifecycle: lease stall")
    # a station reboots while the claw hangs: recovery is required, nothing resumes
    r.stations["B"].reboot()
    r.co.wait(500000)
    sup.poll()
    assert sup.state == "RECOVERY_REQUIRED"
    with pytest.raises(CommandRefused):
        sup.run_task(TaskRunner(r.ctx, SimItemPerception(r.world)))
    with pytest.raises(CommandRefused):
        sup.disarm("claw_supported")               # vision: not on the floor
    assert sup.recover() and sup.state == "READY"
    assert r.ctx.ledger.stations["B"].source == "visual-recovery"
    # host process restart while hanging: a new host (new coordinator, links,
    # supervisor) must come up in RECOVERY_REQUIRED and be able to recover
    r.rt.wait(1.0e6)                               # host down: stations lease-hold
    co2 = Coordinator(cfg, SimHostTransport(r.net, r.rt.now_us), r.rt)
    ctx2 = RobotContext(cfg, co2, r.claw, r.vision, r.camera, TrustLedger(), data_dir=tmp_path, log=r.ctx.log)
    sup2 = Supervisor(ctx2, state_path=tmp_path / "state.json", ledger_path=tmp_path / "ledger.json")
    assert sup2.state == "RECOVERY_REQUIRED" and ctx2.result is not None
    with pytest.raises(CommandRefused):
        sup2.disarm("claw_supported")
    assert sup2.recover(), sup2.reasons[-3:]
    assert ctx2.ledger.all_valid()
    assert ctx2.mount_angle_rad == r.ctx.mount_angle_rad and ctx2.mount_angle_rad > 0   # restored from the saved model
    assert_no_eq_failures(r, "lifecycle: recovery")
    # pause while lowering stops the descent; lowering again completes
    t_pause = r.rt.t + 3.0e6
    r.rt.hooks.append(lambda t: sup2.pause("operator") if abs(t - t_pause) < 500 else None)
    with pytest.raises(CommandRefused, match="paused"):
        sup2.lower()
    assert not r.world.on_floor
    sup2.lower()
    assert sup2.state == "PARKED" and r.world.on_floor
    with pytest.raises(CommandRefused):
        sup2.disarm("yes")
    sup2.disarm("claw_supported")
    assert sup2.state == "DISARMED"
    assert_no_eq_failures(r, "lifecycle: end")


def test_crash_mid_calibration_fails_closed(tmp_path):
    """Review C3: a host crash while the claw hangs must leave a durable
    'may be hanging' record, and no disarm without vision seeing the floor."""
    cfg = fast_cfg()
    r = SimRobot(cfg, seed=12, data_dir=tmp_path)
    sup = Supervisor(r.ctx, state_path=tmp_path / "state.json", ledger_path=tmp_path / "ledger.json")

    def crash(self):
        raise RuntimeError("host crashed")
    orig = StartupSequencer.calibrate
    StartupSequencer.calibrate = crash
    try:
        with pytest.raises(RuntimeError):
            sup.start()
    finally:
        StartupSequencer.calibrate = orig
    assert not r.world.on_floor
    assert TrustLedger.load(tmp_path / "ledger.json").claw_supported is False
    sup2 = Supervisor(r.ctx, state_path=tmp_path / "state.json", ledger_path=tmp_path / "ledger.json")
    assert sup2.state == "RECOVERY_REQUIRED"
    with pytest.raises(CommandRefused):
        sup2.disarm("claw_supported")
    assert all(r.co.links[s].tel["st"] != 0 for s in IDS)       # torque still on everywhere
    assert_no_eq_failures(r, "crash mid-calibration")


def test_host_restart_while_suspended_never_resumes(tmp_path):
    r = SimRobot(fast_cfg(), seed=1)
    sup = Supervisor(r.ctx, state_path=tmp_path / "s.json", ledger_path=tmp_path / "l.json")
    assert r.ctx.ledger.claw_supported is False        # unknown -> fail closed
    sup._set("READY", "pretend calibrated and hanging")
    r2 = SimRobot(fast_cfg(), seed=1)
    sup2 = Supervisor(r2.ctx, state_path=tmp_path / "s.json", ledger_path=tmp_path / "l.json")
    assert sup2.state == "RECOVERY_REQUIRED"
    with pytest.raises(CommandRefused):
        sup2.start()


def run_startup(cfg, **kw):
    r = SimRobot(cfg, **kw)
    rep = StartupSequencer(r.ctx).run()
    assert_no_eq_failures(r, "startup")
    return r, rep


def test_unattached_cable_is_caught_on_the_floor():
    r, rep = run_startup(fast_cfg(), seed=2, world_kw={"slack_m": (0.05, 0.06, 0.60, 0.05)})
    assert rep.outcome == "FAULT" and rep.state == "FAULT"
    assert "station C" in rep.reasons[-1] and "no taut onset" in rep.reasons[-1]
    assert r.world.on_floor and not rep.measurements["suspended"]


def test_swapped_station_wiring_is_caught_before_lifting():
    r, rep = run_startup(fast_cfg(), seed=3, world_kw={"swap_stations": (0, 1)})
    assert rep.outcome == "FAULT"
    assert "slide directions disagree" in rep.reasons[-1]
    assert r.world.on_floor


def test_covered_marker_pauses_instead_of_guessing():
    cfg = fast_cfg(**{"startup.max_marker_wait_s": 3.0})
    r = SimRobot(cfg, seed=4)
    r.simcam.covered = True
    rep = StartupSequencer(r.ctx).run()
    assert rep.outcome == "PAUSED" and "marker" in rep.reasons[-1]
    assert_no_eq_failures(r, "covered marker")


@pytest.mark.parametrize("change,reason", [
    ({"authorization.suspended_motion_authorized": False}, "suspended_motion_authorized"),
    ({"marker.heading_prior_rad": None}, "configuration incomplete"),
])
def test_self_check_refuses_unsafe_configuration(change, reason):
    r = SimRobot(fast_cfg(), seed=5)
    for path, v in change.items():                 # operator edits the config after the sim is built
        sec, key = path.split(".")
        setattr(getattr(r.ctx.cfg, sec), key, v)
    rep = StartupSequencer(r.ctx).run()
    assert rep.outcome == "FAULT" and reason in rep.reasons[-1]
    assert r.world.on_floor


def test_low_battery_refuses_to_lift():
    r = SimRobot(fast_cfg(), seed=6)
    r.claw.battery_v = 6.4
    rep = StartupSequencer(r.ctx).run()
    assert rep.outcome == "FAULT" and "battery" in rep.reasons[-1]


def _suspended_bead_rig(seed, L0_err):
    cfg = fast_cfg(**{f"stations.{k}.bead.uncertainty_m": 0.001 for k in range(4)})
    cfg_, net, st, rt, co = build(seed, cfg=cfg)
    rng = np.random.default_rng(seed)
    A = cfg.anchor_priors() + rng.normal(0, 0.04, (4, 3))
    home = np.array([1.68, 1.37, 1.0])
    w = World(cfg, st, anchors=A, T_R_M=planar_T(1.6, 1.3, 0.2), claw_xy=home[:2], suspended_at=home)
    rt.world = w
    w.settle()
    bring_up(co)
    L0 = {s: w.true_L0(s) + L0_err for s in IDS}
    model = model_from(Geometry(A, cfg.attachment_points()), cfg, L0)
    ws = workspace_from_config(cfg, A, lowest_point_z=cfg.claw.lowest_point_body_m[2])
    return cfg, co, w, model, ws, home


def test_bead_verification_with_a_good_model():
    cfg, co, w, model, ws, home = _suspended_bead_rig(7, 0.002)
    bv = BeadVerifier(cfg, co, model, limits_from_config(cfg), ws, lambda q: np.full(4, 0.0005), log=lambda s: None)
    out = bv.run(0, p_home=home)
    assert out.status == "VERIFIED", out.reason
    assert_no_eq_failures(w, "bead verification")
    assert len(out.captures) == 2 and out.spread_m <= cfg.stations[0].bead.repeatability_tol_m
    # the model was 2 mm long; the capture residual says so
    assert all(abs(c.residual - 0.002) < 0.002 for c in out.checks)


def test_bead_disagreeing_with_the_model_blocks_and_changes_nothing():
    cfg, co, w, model, ws, home = _suspended_bead_rig(8, -0.009)
    L0_before = {s: model.maps[s].L0 for s in IDS}
    bv = BeadVerifier(cfg, co, model, limits_from_config(cfg), ws, lambda q: np.full(4, 0.0005), log=lambda s: None)
    out = bv.run(1, p_home=home)
    assert out.status == "BLOCKED"
    assert "pre-update" in out.reason or "not found" in out.reason
    assert {s: model.maps[s].L0 for s in IDS} == L0_before
    assert_no_eq_failures(w, "bead disagreement")
