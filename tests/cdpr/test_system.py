"""Whole-system behaviour in simulation: startup, tasks, faults, recovery.

These run the real sequencer/supervisor/coordinator/station logic against the
physics simulator (roughly 5-60 s wall time each)."""
import numpy as np
import pytest

from roomcleaner.cdpr.calibration import IDS
from roomcleaner.cdpr.homing import BeadVerifier
from roomcleaner.cdpr.kinematics import Geometry, workspace_from_config
from roomcleaner.cdpr.sim.harness import SimRobot
from roomcleaner.cdpr.sim.world import World
from roomcleaner.cdpr.startup import StartupSequencer
from roomcleaner.cdpr.supervisor import CommandRefused, Supervisor
from roomcleaner.cdpr.tasks import SimItemPerception, TaskRunner
from roomcleaner.cdpr.trajectory import limits_from_config, model_from
from roomcleaner.cdpr.frames import planar_T

from .simkit import bring_up, build, fast_cfg


def test_full_lifecycle_startup_task_reboot_recovery_park(tmp_path):
    cfg = fast_cfg()
    r = SimRobot(cfg, seed=0, data_dir=tmp_path)
    sup = Supervisor(r.ctx, state_path=tmp_path / "state.json", ledger_path=tmp_path / "ledger.json")
    assert sup.state == "DISARMED"
    rep = sup.start()
    assert sup.state == "READY", rep.reasons
    m = rep.measurements
    # floor stage: every cable found taut within its bound, bearings consistent
    assert all(0 < m[f"slack_{s}_m"] < cfg.startup.max_slack_m[i] for i, s in enumerate(IDS))
    assert m["bearing_rms"] < cfg.startup.bearing_rms_max
    assert abs(m["lift_observed_m"] - m["lift_commanded_m"]) < cfg.startup.lift_slack_budget_m
    # calibration accepted on witnesses; the work-volume model is consistent
    assert m["calibration"]["witness_rms_m"] < cfg.calibration.witness_rms_max_m
    assert (tmp_path / "calibration.json").exists()
    # beads: vision alone cannot pin absolute lengths tightly enough for a safe,
    # complete search with these settings, so they are honestly BLOCKED, not tried
    assert r.ctx.ledger.level == "LOCAL_ONLY"
    assert all(b["status"] == "BLOCKED" for b in m["beads"].values())
    for i, s in enumerate(IDS):                    # the reported absolute sigma covers the true error
        err = abs(r.ctx.model.maps[s].L0 - r.world.true_L0(s))
        assert err < 3.5 * m["absolute_sigma_m"][i] + 0.002
    # a task: two items delivered with visual verification
    c = cfg.room_m[:2] / 2
    r.world.hamper = (np.asarray(cfg.tasks.hamper_room_m), cfg.tasks.hamper_radius_m)
    r.world.add_item("sock", c + [-0.3, 0.2])
    r.world.add_item("jeans", c + [0.2, 0.35], mass=0.9, height=0.08)
    out = sup.run_task(TaskRunner(r.ctx, SimItemPerception(r.world)))
    assert out["done"] == ["sock", "jeans"] and sup.state == "READY"
    assert all(it["state"] == "hamper" for it in r.world.items)
    # a station reboots while the claw hangs: recovery is required, nothing resumes
    r.stations["B"].reboot()
    r.co.wait(500000)
    sup.poll()
    assert sup.state == "RECOVERY_REQUIRED"
    with pytest.raises(CommandRefused):
        sup.run_task(TaskRunner(r.ctx, SimItemPerception(r.world)))
    with pytest.raises(CommandRefused):
        sup.disarm("claw_supported")               # not allowed while hanging
    assert sup.recover() and sup.state == "READY"
    assert r.ctx.ledger.stations["B"].source == "visual-recovery"
    # park and disarm
    sup.lower()
    assert sup.state == "PARKED" and r.world.on_floor
    with pytest.raises(CommandRefused):
        sup.disarm("yes")
    sup.disarm("claw_supported")
    assert sup.state == "DISARMED"


def test_host_restart_while_suspended_never_resumes(tmp_path):
    r = SimRobot(fast_cfg(), seed=1)
    sup = Supervisor(r.ctx, state_path=tmp_path / "s.json", ledger_path=tmp_path / "l.json")
    r.ctx.ledger.claw_supported = False
    sup._set("READY", "pretend calibrated and hanging")
    r2 = SimRobot(fast_cfg(), seed=1)
    sup2 = Supervisor(r2.ctx, state_path=tmp_path / "s.json", ledger_path=tmp_path / "l.json")
    assert sup2.state == "RECOVERY_REQUIRED"
    with pytest.raises(CommandRefused):
        sup2.start()


def run_startup(cfg, **kw):
    r = SimRobot(cfg, **kw)
    rep = StartupSequencer(r.ctx).run()
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
