"""Three-station mode (docs/THREE_STATION_MODE_SPEC.md): ``stations_active`` selects 3 or 4 of the stations A-D, default all
four. Config validation, 3-cable statics, the rigid-body attitude model with three attachment points, the workspace
(triangle + tension-floor edge margin), full simulated startups with ``config/robot.sim3.json`` (seeds 0, 1, 2), a move
inside and a refused move outside, and the service / phone app listing only the active stations.

The simulated startups run the real sequencer / supervisor / coordinator / station logic against the physics simulator
(about 2 minutes of wall time each); they are cached per seed so every test that needs a started robot shares one run."""
import copy
import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from roomcleaner.cdpr.config import ConfigError, STATION_IDS, load_config, triangle_geometry
from roomcleaner.cdpr.kinematics import (Geometry, barycentric_xy, geometry_from_config, tension_distribution,
                                         workspace_from_config)
from roomcleaner.cdpr.service import CHECKLIST, STATIC, Service, checklist_for, create_app
from roomcleaner.cdpr.sim.harness import SimRobot
from roomcleaner.cdpr.sim.world import FloorBoard
from roomcleaner.cdpr.supervisor import Supervisor
from roomcleaner.cdpr.trajectory import PlanError, plan_line_from
from roomcleaner.cdpr.trust import TrustLedger

from .test_service import Client

SIM = "config/robot.sim.json"
SIM3 = "config/robot.sim3.json"
EX3 = "config/robot.three.example.json"
G = 9.81


def raw_of(path=SIM):
    return json.loads(Path(path).read_text())


def fast3(path=SIM3, **overrides):
    """The three-station sim profile with coarser microstepping and faster moves, exactly what simkit.fast_cfg does for the
    four-station profile (same logic, same checks, whole startups in about two minutes of wall time)."""
    raw = raw_of(path)
    for s in raw["stations"]:
        s["drive"]["microsteps"] = 4
    raw["motion"].update(max_cable_speed_m_s=0.15, max_cable_accel_m_s2=0.3, max_cart_speed_m_s=0.15,
                         max_cart_accel_m_s2=0.3)
    for key, v in overrides.items():
        d = raw
        ks = key.split(".")
        for k in ks[:-1]:
            d = d[int(k)] if isinstance(d, list) else d[k]
        d[ks[-1]] = v
    return load_config(raw)


# ===================================================================================== 1. configuration
def test_default_is_four_stations_and_existing_profiles_are_unchanged():
    for prof in (SIM, "config/robot.example.json"):
        c = load_config(prof)
        assert c.ids == list(STATION_IDS) and c.n_active == 4 and c.inactive_stations == []
        assert [s.id for s in c.all_stations] == list(STATION_IDS)
        assert c.attachment_points().shape == (4, 3) and c.anchor_priors().shape == (4, 3)
        # the start point of four stations is the room centre, exactly as before
        assert np.allclose(c.start_point_xy(), c.room_m[:2] / 2)
        assert checklist_for(c) == CHECKLIST
    assert "stations_active" not in raw_of(SIM) and "stations_active" not in raw_of("config/robot.example.json")


def test_three_is_accepted_the_records_of_all_four_are_kept_and_inactive_gets_no_requirement():
    for prof in (SIM3, EX3):
        c = load_config(prof)
        assert c.ids == ["A", "B", "C"] and c.inactive_ids == ["D"] and c.n_active == 3
        assert [s.id for s in c.all_stations] == list(STATION_IDS) and c.record("D").id == "D"
        with pytest.raises(KeyError):
            c.station("D")                                  # an inactive station is not one the host works with
        with pytest.raises(KeyError):
            c.station_firmware_params("D")                  # ... never configured
        assert c.attachment_points().shape == (3, 3) and c.anchor_priors().shape == (3, 3)
        assert not any("[D]" in m for m in c.missing("bead_verification")), c.missing("bead_verification")
    # the layout of the first test (spec): A, B in the corners of one wall, C in the middle of the opposite wall
    c = load_config(SIM3)
    assert np.allclose(c.anchor_priors(), [[0.05, 0.05, 2.5932], [3.3028, 0.05, 2.5932], [1.6764, 2.6932, 2.5932]])
    assert np.allclose(c.start_point_xy(), [1.6764, (0.05 + 0.05 + 2.6932) / 3])       # the centroid, not the room centre
    ex = load_config(EX3)
    assert np.allclose(ex.anchor_priors(), c.anchor_priors())
    # the hardware profile: no address is needed for the inactive station and the three active ones are the only ones listed
    assert ex.profile == "hardware" and all(s.address is None for s in ex.all_stations)
    assert "stations[A].drive.max_step_rate_hz" in ex.missing("station_bench")
    assert not any("[D]" in m for m in ex.missing("calibration"))


def test_the_active_set_is_sorted_into_a_to_d_order_and_the_spec_spelling_is_accepted():
    raw = raw_of(SIM)
    raw["stations_active"] = ["C", "A", "B"]
    assert load_config(raw).ids == ["A", "B", "C"]
    raw = raw_of(SIM)
    raw["stations.active"] = ["A", "B", "D"]
    c = load_config(raw)
    assert c.ids == ["A", "B", "D"] and c.inactive_ids == ["C"]
    # per-station arrays of the file stay four long and are indexed by the station's own place: D is index 3, not 2
    assert c.station_index("D") == 3 and c.max_slack_for("D") == c.startup.max_slack_m[3]
    assert np.allclose(c.attachment_points(), np.asarray(c.claw.attachment_points_body_m)[[0, 1, 3]])
    raw["stations_active"] = ["A", "B", "C"]                  # both spellings, different: refused
    with pytest.raises(ConfigError, match="both set and differ"):
        load_config(raw)
    raw["stations_active"] = None                              # null: all four
    del raw["stations.active"]
    assert load_config(raw).ids == list(STATION_IDS)


@pytest.mark.parametrize("bad, match", [
    (["A", "B"], r"2 station\(s\).*needs 3 or 4"),
    (["A"], r"1 station\(s\)"),
    ([], r"0 station\(s\)"),
    (["A", "A", "B"], r"duplicate station id\(s\) \['A'\]"),
    (["A", "B", "E"], r"unknown station id\(s\) \['E'\] \(known ids: A, B, C, D\)"),
    (["A", "B", "c"], r"unknown station id"),
    ("ABC", r"must be a list of station ids"),
    ([1, 2, 3], r"must be a list of station ids"),
    (["A", "B", "C", "D", "A"], r"duplicate"),
])
def test_two_duplicates_unknown_ids_and_bad_types_are_refused_with_a_clear_message(bad, match):
    raw = raw_of(SIM)
    raw["stations_active"] = bad
    with pytest.raises(ConfigError, match=match):
        load_config(raw)


def test_a_misspelt_key_cannot_silently_run_all_four():
    raw = raw_of(SIM)
    raw["active_stations"] = ["A", "B", "C"]
    with pytest.raises(ConfigError, match="unknown config key.*stations_active"):
        load_config(raw)


def test_a_degenerate_triangle_is_refused():
    raw = raw_of(SIM3)
    for k, xy, match in (("collinear", [1.6764, 0.05], "collinear or coincide"),
                         ("coincident", [0.05, 0.05], "collinear or coincide"),
                         ("sliver", [1.6764, 0.2], "degenerate triangle.*shortest altitude")):
        r = copy.deepcopy(raw)
        r["stations"][2]["anchor_room_m"] = [xy[0], xy[1], 2.5932]
        with pytest.raises(ConfigError, match=match):
            load_config(r)
    # four stations are not subject to it (existing behaviour)
    r = raw_of(SIM)
    r["stations"][2]["anchor_room_m"] = [1.6764, 0.05, 2.5932]
    assert load_config(r).n_active == 4
    # a tension floor that three cables cannot meet anywhere is refused too
    r = copy.deepcopy(raw)
    r["motion"]["min_tension_n"] = 2.5
    with pytest.raises(ConfigError, match="impossible"):
        load_config(r)


# ===================================================================================== 2. statics
def _geo3(common=False):
    cfg = load_config(SIM3)
    A = cfg.anchor_priors()
    if common:
        return cfg, Geometry(A, np.zeros((3, 3)))
    return cfg, geometry_from_config(cfg, A)


def test_three_cable_tensions_are_the_unique_solution_of_the_3x3_system():
    cfg, geo = _geo3()
    m = cfg.claw.mass_kg
    for p in ([1.6764, 0.931, 1.0], [1.6764, 0.931, 0.5173], [1.2, 0.8, 0.9], [2.0, 1.1, 1.3], [1.6764, 1.372, 1.0]):
        p = np.array(p)
        for acc in ((0, 0, 0), (0, 0, 2.0), (0.3, -0.2, 0.0)):
            r = tension_distribution(geo, p, m, t_min=0.5, t_max=15.0, accel=acc)
            u = geo.unit_vectors(p)
            T = np.linalg.solve(u.T, m * (np.asarray(acc) + [0, 0, G]))          # the direct solve
            assert np.allclose(r.tensions, T, atol=1e-9)
            assert np.allclose(u.T @ r.tensions, m * (np.asarray(acc) + [0, 0, G]), atol=1e-9)    # force balance
            assert r.feasible == bool(T.min() >= 0.5 and T.max() <= 15.0)
    # no distribution to choose: the solution does not depend on the bounds
    p = np.array([1.5, 0.9, 1.0])
    a = tension_distribution(geo, p, m, t_min=0.5, t_max=15.0).tensions
    b = tension_distribution(geo, p, m, t_min=0.0, t_max=1e3).tensions
    assert np.allclose(a, b)


def test_three_cable_tensions_follow_the_barycentric_formula():
    """Anchors at one height H, point claw z below them: T_i = lambda_i W L_i / (H - z), lambda = barycentric coordinates of the
    claw's floor point in the anchors' triangle (so T_i >= lambda_i W, the basis of the edge margin)."""
    cfg, geo = _geo3(common=True)
    A = geo.anchors
    H, m = A[0, 2], 0.6
    for p in ([1.6764, 0.931, 1.0], [1.0, 0.5, 0.4], [2.6, 0.6, 1.5], [1.7, 1.9, 0.8]):
        p = np.array(p)
        lam = barycentric_xy(A[:, :2], p)
        assert np.all(lam > 0) and lam.sum() == pytest.approx(1.0)
        W = m * G
        L = np.linalg.norm(A - p, axis=1)
        T_formula = lam * W * L / (H - p[2])
        T = tension_distribution(geo, p, m, t_min=0.0, t_max=1e3).tensions
        assert np.allclose(T, T_formula, rtol=1e-9)
        assert np.all(T >= lam * W - 1e-9)


def test_a_point_outside_the_triangle_is_infeasible_and_so_is_one_too_close_to_its_edge():
    cfg, geo = _geo3()
    m = cfg.claw.mass_kg
    A = cfg.anchor_priors()
    # outside: toward the missing corner D (0.05, 2.6932), and beyond each of the three edges
    for xy in ([0.15, 2.5], [0.4, 2.1], [2.9, 2.2], [1.6764, -0.1], [-0.1, 1.2]):
        assert np.any(barycentric_xy(A[:, :2], xy) < 0), xy
        for z in (0.52, 1.0, 1.6):
            r = tension_distribution(geo, np.array([xy[0], xy[1], z]), m, t_min=0.5, t_max=15.0)
            assert not r.feasible and r.tensions.min() < 0.5, (xy, z, r.tensions)
    # inside the triangle but below the tension floor: infeasible too (T_i < t_min)
    p = np.array([1.6764, 0.06 + 0.03, 1.0])                    # 3 cm off the A-B edge (the wall)
    assert np.all(barycentric_xy(A[:, :2], p) > 0)
    assert not tension_distribution(geo, p, m, t_min=0.5, t_max=15.0).feasible
    # the workspace of the config rejects what is outside / too close to an edge, accepts the middle
    ws = workspace_from_config(cfg, A, lowest_point_z=float(cfg.claw.lowest_point_body_m[2]))
    lam_min = 0.5 / (m * G)
    assert ws.tri_xy is not None and ws.lam_min == pytest.approx(lam_min)
    assert ws.triangle_violation([1.6764, 0.931]) is None
    assert ws.triangle_violation([1.6764, 1.372]) is None       # the room centre is inside the margin-shrunk triangle too
    msg = ws.triangle_violation([0.4, 2.1])
    assert msg and "outside the edge opposite station" in msg and "must be at least" in msg
    assert "inside the edge" in ws.triangle_violation([1.6764, 0.25])
    assert any("triangle" in v or "edge opposite" in v for v in ws.violations(geo, np.array([0.4, 2.1, 1.0])))
    # four stations: no triangle, the workspace is the box exactly as before
    c4 = load_config(SIM)
    ws4 = workspace_from_config(c4, c4.anchor_priors(), lowest_point_z=float(c4.claw.lowest_point_body_m[2]))
    assert ws4.tri_xy is None and ws4.triangle_violation([0.0, 0.0]) is None and ws4.ids == ("A", "B", "C", "D")


def test_the_edge_margin_is_sized_from_the_tension_floor_and_guarantees_it_at_every_height():
    """lambda_min = T_floor / (m g): inside the margin-shrunk triangle every cable carries >= T_floor at ANY height of the
    claw (T_i >= lambda_i W because L_i >= H - z), and the edge distance is lambda_min x the altitude."""
    cfg, geo = _geo3(common=True)
    m = 0.6
    A = cfg.anchor_priors()
    lam_min = cfg.motion.min_tension_n / (m * G)
    g = triangle_geometry(A[:, :2])
    margins = lam_min * g["altitudes_m"]
    assert margins == pytest.approx([0.2354, 0.2354, 0.2247], abs=2e-3)         # metres, the numbers of the operator guide
    rng = np.random.default_rng(3)
    n_in = 0
    for _ in range(400):
        xy = A[:, :2].T @ rng.dirichlet([1, 1, 1])
        if barycentric_xy(A[:, :2], xy).min() < lam_min:
            continue
        n_in += 1
        z = rng.uniform(0.3, 2.2)
        T = tension_distribution(geo, np.array([xy[0], xy[1], z]), m, t_min=0.0, t_max=1e3).tensions
        assert T.min() >= cfg.motion.min_tension_n - 1e-9, (xy, z, T)
    assert n_in > 100
    # the usable area is the triangle scaled by (1 - 3 lambda): 56 % of it for the simulator's 0.6 kg claw
    assert (1 - 3 * lam_min) ** 2 == pytest.approx(0.556, abs=0.01)


def test_the_rigid_body_attitude_model_converges_with_three_attachment_points():
    """Only the active corners' cables pull: with three attachment points the roll/pitch Newton still converges (3 forces + 2
    moments for 3 tensions + 2 tilts, yaw held) over the whole usable workspace and the predicted tilt stays small."""
    cfg, geo = _geo3()
    assert geo.spaced and geo.n == 3 and geo._att is not None
    A = cfg.anchor_priors()
    ws = workspace_from_config(cfg, A, lowest_point_z=float(cfg.claw.lowest_point_body_m[2]))
    n_ok = n_tot = 0
    worst = 0.0
    for yaw in (0.0, 0.7, -1.5):
        for x in np.arange(0.2, 3.2, 0.25):
            for y in np.arange(0.2, 2.6, 0.25):
                for z in (0.6, 1.2, 1.6):
                    p = np.array([x, y, z])
                    if ws.violations(geo, p):
                        continue
                    sol = geo._att.solve(p, yaw=yaw)
                    n_tot += 1
                    n_ok += bool(sol.ok and sol.taut)
                    worst = max(worst, float(np.degrees(np.hypot(sol.roll, sol.pitch))))
    assert n_tot > 100 and n_ok == n_tot, (n_ok, n_tot)
    assert worst < 15.0, worst              # a few degrees; the number over the workspace is in verification/three_station_mode_results.md
    # a pose outside the triangle has a negative tension in the statics solution (reported, not hidden)
    sol = geo._att.solve(np.array([0.4, 2.1, 1.0]))
    assert not sol.taut


# ===================================================================================== 3. simulation
_RUNS: dict = {}


def started(seed, tmp_path_factory):
    """A full simulated startup with robot.sim3.json (fast variant) for ``seed``, cached: (robot, supervisor, report)."""
    if seed not in _RUNS:
        tmp = tmp_path_factory.mktemp(f"three_{seed}")
        r = SimRobot(fast3(), seed=seed, data_dir=tmp, camera_kw={"board": FloorBoard.nominal(0.15)})
        sup = Supervisor(r.ctx, state_path=tmp / "state.json", ledger_path=tmp / "ledger.json")
        rep = sup.start()
        _RUNS[seed] = (r, sup, rep, tmp)
    return _RUNS[seed]


def test_the_simulator_and_the_host_are_built_with_the_active_stations_only(tmp_path):
    r = SimRobot(fast3(), seed=0, data_dir=tmp_path)
    assert list(r.stations) == ["A", "B", "C"] and r.net.nodes == ["A", "B", "C"]
    assert r.co.ids == ("A", "B", "C") and sorted(r.co.links) == ["A", "B", "C"] and r.ctx.ids == ("A", "B", "C")
    assert r.world.anchors.shape == (3, 3) and r.world.attach.shape == (3, 3) and r.world.ell().shape == (3,)
    assert list(r.ledger.stations) == ["A", "B", "C"] and set(r.net.inbox) == {"host", "A", "B", "C"}     # nothing exists for D
    assert r.ctx.cal.n == 3 and r.ctx.cal.ids == ("A", "B", "C") and r.ctx.priors.anchors_room.shape == (3, 3)
    # the claw and its marker start at the centroid of the active anchors (not at the room centre)
    assert np.linalg.norm(r.world.p[:2] - r.cfg.start_point_xy()) < 0.5
    assert np.linalg.norm(r.world.p[:2] - r.cfg.room_m[:2] / 2) > 0.3


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_a_full_simulated_startup_reaches_ready_with_no_station_faults(seed, tmp_path_factory):
    r, sup, rep, tmp = started(seed, tmp_path_factory)
    assert sup.state == "READY" and rep.outcome == "READY", (rep.reasons, sup.state)
    assert r.ctx.ledger.level in ("VERIFIED", "LOCAL_ONLY")
    if r.ctx.ledger.level == "LOCAL_ONLY":                       # a clearly reported LOCAL_ONLY: it says why
        assert r.ctx.ledger.trust_reasons and all(isinstance(x, str) and x for x in r.ctx.ledger.trust_reasons)
        assert rep.reasons, "LOCAL_ONLY without a stated reason"
    # no station faults, every active station valid, all holding, none of them lost its reference
    for s in ("A", "B", "C"):
        tel = r.co.links[s].tel
        assert tel["flt"] == 0 and tel["st"] != 0, (s, tel)
        assert r.ctx.ledger.stations[s].valid
    assert r.ctx.ledger.all_valid() and r.ctx.ledger.marker_valid
    assert "D" not in r.co.links and "D" not in r.ctx.ledger.stations and "D" not in r.stations
    assert not r.world.on_floor and r.world.eq_failures == 0
    m = rep.measurements
    assert m["active_stations"] == ["A", "B", "C"] and m["inactive_stations"] == ["D"]
    assert m["start_point_room_m"] == pytest.approx([1.6764, 0.9311], abs=1e-4)
    assert all(0 < m[f"slack_{s}_m"] < r.cfg.max_slack_for(s) for s in "ABC") and "slack_D_m" not in m
    assert m["bearing_rms"] < r.cfg.startup.bearing_rms_max
    assert m["calibration"]["witness_rms_m"] < r.cfg.calibration.witness_rms_max_m
    # the fit is over the active stations and zero lengths only, and reports its identifiability
    res = r.ctx.result
    assert res.ids == ("A", "B", "C") and res.anchors_M.shape == (3, 3) and res.L0.shape == (3,)
    assert res.cov_theta.shape == (9 + 3 + 3, 9 + 3 + 3)                          # 3 anchors + 3 L0, + the marker pose
    assert all("D" not in k for k in res.sigma())
    idn = res.identifiability
    assert idn.singular_values.shape == (12,) and np.isfinite(idn.condition_number) and idn.condition_number >= 1.0
    saved = json.loads((tmp / "calibration.json").read_text())["result"]
    assert saved["ids"] == ["A", "B", "C"] and set(saved["L0_m"]) == {"A", "B", "C"} and len(saved["anchors_room_m"]) == 3
    assert saved["identifiability"]["condition_number"] == pytest.approx(idn.condition_number)
    assert set(saved["identifiability"]) >= {"ok", "weak", "condition_number", "singular_value_min"}
    # the trust ledger / supervisor status list the active stations only
    assert sorted(sup.status()["stations"]) == ["A", "B", "C"]
    # the calibrated anchors are close to the (hidden) truth the world was built with
    err = np.linalg.norm(res.anchors_room - r.world.anchors, axis=1)
    assert err.max() < 0.12, err


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_a_300_mm_move_inside_the_triangle_completes(seed, tmp_path_factory):
    r, sup, rep, tmp = started(seed, tmp_path_factory)
    ctx, co = r.ctx, r.co
    here = ctx.model.pose_from_positions(co.positions())[0]
    # a 0.3 m move that stays inside the feasible region (try 8 horizontal directions, take the first that is)
    target = None
    for a in np.arange(0, 2 * np.pi, np.pi / 4):
        q = here + 0.3 * np.array([np.cos(a), np.sin(a), 0.0])
        if not ctx.ws.violations(ctx.model.geometry, q) and tension_distribution(
                ctx.model.geometry, q, ctx.cfg.claw.mass_kg, t_min=0.5, t_max=ctx.cfg.motion.max_tension_n).feasible:
            target = q
            break
    assert target is not None
    truth0 = r.world.p.copy()
    plan = plan_line_from(ctx.model, co.positions(), target, ctx.lim, ws=ctx.ws, label="300 mm inside")
    assert plan.duration > 0 and not plan.is_noop
    res = co.execute(plan)
    assert res.ok, res.reason
    now = ctx.model.pose_from_positions(co.positions())[0]
    assert np.linalg.norm(now - target) < 0.01
    assert np.linalg.norm(r.world.p - truth0) == pytest.approx(0.3, abs=0.02)         # the real claw moved 300 mm
    assert all(co.links[s].tel["flt"] == 0 for s in "ABC") and r.world.eq_failures == 0
    assert sup.state == "READY"
    sup.poll()
    assert sup.state == "READY" and r.ctx.ledger.all_valid()


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_a_move_toward_the_missing_corner_is_refused_before_any_motion(seed, tmp_path_factory):
    r, sup, rep, tmp = started(seed, tmp_path_factory)
    ctx, co = r.ctx, r.co
    here = ctx.model.pose_from_positions(co.positions())[0]
    pos0, mid0 = co.positions().copy(), co.motion_id
    assert ctx.cfg.record("D").anchor_room_m is not None           # the corner (0.05, 2.69) that is not mounted
    for tgt_xy in ((0.4, 2.1), (0.8, 1.9), (0.3, 2.4)):            # toward D, inside the 0.2 m wall margin of the room
        tgt = np.array([tgt_xy[0], tgt_xy[1], here[2]])
        assert ctx.ws.triangle_violation(tgt) is not None
        with pytest.raises(PlanError, match="workspace: .*(outside|inside) the edge opposite station"):
            plan_line_from(ctx.model, co.positions(), tgt, ctx.lim, ws=ctx.ws, label="toward D")
    # the task layer's volume check refuses it as well, and nothing moved, nothing was sent
    from roomcleaner.cdpr.tasks import TrustedVolume
    assert not TrustedVolume(ctx).allows(np.array([0.4, 2.2, here[2]]))
    assert np.array_equal(co.positions(), pos0) and co.motion_id == mid0
    assert all(co.links[s].tel["st"] == 1 for s in "ABC")          # IDLE, holding, untouched
    assert sup.state == "READY"


def test_the_start_point_check_refuses_a_claw_resting_outside_the_triangle(tmp_path):
    """The startup must start at the centroid: a claw put outside the feasible triangle (here: by the missing corner) is refused
    in INITIAL_LIFT, before any cable pretension or lift, with the start point in the message."""
    cfg = fast3()
    r = SimRobot(cfg, seed=0, data_dir=tmp_path, world_kw={"marker_xy": (0.45, 2.15)},
                 camera_kw={"board": FloorBoard.nominal(0.15)})
    sup = Supervisor(r.ctx, state_path=tmp_path / "state.json", ledger_path=tmp_path / "ledger.json")
    rep = sup.start()
    assert sup.state != "READY" and rep.outcome in ("FAULT", "PAUSED")
    assert any("cannot lift it" in x and "outside the edge opposite station" in x and "centroid of the A/B/C anchors" in x
               and "(1.68, 0.93)" in x for x in rep.reasons), rep.reasons
    assert r.world.on_floor and r.world.eq_failures == 0           # it never lifted


# ===================================================================================== 4. trust ledger, service, app
def test_a_ledger_saved_with_another_active_set_is_reconciled():
    lg = TrustLedger()
    for s in "ABCD":
        lg.set_reference(s, 7, 1.0, 0.001, "visual")
    lg.set_level("LOCAL_ONLY")
    assert lg.restrict_to(["A", "B", "C", "D"]) is False and list(lg.stations) == list("ABCD")     # four: untouched
    assert lg.restrict_to(["A", "B", "C"]) is True and list(lg.stations) == list("ABC") and lg.all_valid()
    lg3 = TrustLedger.for_ids(["A", "B", "C"])
    assert list(lg3.stations) == list("ABC") and not lg3.all_valid()
    lg3.restrict_to(list("ABCD"))                                   # a new active station starts invalid
    assert not lg3.stations["D"].valid


def test_service_status_and_the_phone_app_list_only_the_active_stations(tmp_path):
    r = SimRobot(fast3(), seed=11, data_dir=tmp_path)
    svc = Service(r.ctx, data_dir=tmp_path)
    svc.poll_claw()
    c = Client(create_app(svc), svc.token)
    s = c.get("/api/status").get_json()
    assert sorted(s["stations"]) == ["A", "B", "C"] and "D" not in s["stations"]
    assert s["stations_active"] == ["A", "B", "C"] and s["stations_inactive"] == ["D"]
    assert set(s["anchors_m"]) == {"A", "B", "C"}
    assert s["start_point_m"] == pytest.approx([1.6764, 0.9311], abs=1e-4)
    assert "Start point: (1.68, 0.93) m" in s["start_point_text"] and "centroid of anchors A, B, C" in s["start_point_text"]
    assert "THREE-STATION MODE" in s["mode_text"] and "A, B, C" in s["mode_text"]
    # the checklist names the active cables and the start point; the other items are the four-station ones
    cl = s["checklist"]
    assert len(cl) == len(CHECKLIST) == 5 and cl[0] == CHECKLIST[0] and cl[1] == CHECKLIST[1] and cl[4] == CHECKLIST[4]
    assert cl[3] == "All active cables (A, B, C) attached and routed over their pulleys" and "four" not in " ".join(cl)
    assert "(1.68, 0.93) m" in cl[2] and "NOT the room centre" in cl[2]
    ws = s["workspace"]
    assert ws["ids"] == ["A", "B", "C"] and ws["tension_floor_fraction"] == pytest.approx(0.5 / (0.6 * G), abs=1e-3)
    assert ws["edge_margin_m"]["A"] == pytest.approx(0.235, abs=0.003) and 2.0 < ws["usable_area_m2"] < 3.0
    # the phone app draws tiles from that list (and the Setup step shows the start point): no hard-coded four tiles
    js = (STATIC / "app.js").read_text()
    assert "Object.entries(s.stations" in js and "s.start_point_text" in js and "s.mode_text" in js and "s.stations_active" in js
    assert 'id="startPoint"' in (STATIC / "index.html").read_text() and 'id="modeNote"' in (STATIC / "index.html").read_text()
    # four stations: the service lists four tiles, the checklist is exactly the old one
    r4 = SimRobot(load_config(SIM), seed=11, data_dir=tmp_path / "four")
    svc4 = Service(r4.ctx, data_dir=tmp_path / "four")
    s4 = svc4.status()
    assert sorted(s4["stations"]) == list("ABCD") and s4["checklist"] == CHECKLIST and s4["stations_active"] == list("ABCD")
    assert s4["stations_inactive"] == [] and s4["workspace"] is None and s4["mode_text"] == ""


def test_the_setup_page_can_edit_the_anchor_of_an_unmounted_station_without_touching_the_active_set(tmp_path):
    r = SimRobot(fast3(), seed=11, data_dir=tmp_path)
    svc = Service(r.ctx, data_dir=tmp_path)
    out = svc.set_room({"width_m": 3.3528, "depth_m": 2.7432, "height_m": 2.7432, "anchors": {"C": [1.70, 2.69, 2.59]}})
    assert out["room_m"] == pytest.approx([3.3528, 2.7432, 2.7432]) and len(out["anchors"]) == 3
    assert r.cfg.station("C").anchor_room_m == pytest.approx([1.70, 2.69, 2.59])
    assert svc.ctx.priors.anchors_room[2] == pytest.approx([1.70, 2.69, 2.59])
    assert svc.status()["start_point_m"][0] == pytest.approx((0.05 + 3.3028 + 1.70) / 3, abs=1e-3)       # the start point follows
    svc.set_room({"width_m": 3.3528, "depth_m": 2.7432, "height_m": 2.7432, "anchors": {"D": [0.06, 2.69, 2.59]}})
    assert r.cfg.record("D").anchor_room_m == pytest.approx([0.06, 2.69, 2.59]) and r.cfg.ids == ["A", "B", "C"]


def test_a_ledger_and_model_saved_in_one_mode_do_not_break_the_other(tmp_path_factory):
    """The data directory is shared by the modes: a model.json / ledger.json / state.json written by a three-station run must be
    ignored (the model) or reconciled (the ledger) by a four-station host, and the other way round, never crash it."""
    r3, sup3, rep3, tmp3 = started(0, tmp_path_factory)
    assert (tmp3 / "model.json").exists() and (tmp3 / "ledger.json").exists()
    d3 = tmp3.parent / "mode_switch_copy"                                               # (a copy: the cached run stays untouched)
    shutil.copytree(tmp3, d3)
    r4 = SimRobot(load_config(SIM), seed=1, data_dir=d3)
    assert r4.ctx.load_model() is False and r4.ctx.result is None                       # a 3-cable model does not fit 4 cables
    assert any("saved model is for stations A/B/C" in x for x in r4.log_lines)
    sup4 = Supervisor(r4.ctx, state_path=d3 / "state.json", ledger_path=d3 / "ledger.json")
    assert sup4.state == "RECOVERY_REQUIRED"                                            # claw may hang: the safe default
    assert list(r4.ctx.ledger.stations) == list("ABCD") and not r4.ctx.ledger.stations["D"].valid
    assert r4.ctx.ledger.stations["A"].valid                                            # the stations it knew keep their entries
    # and the other way: a four-station ledger reaching a three-station host drops D
    lg = TrustLedger()
    for sid in "ABCD":
        lg.set_reference(sid, 3, 1.0, 0.001, "visual")
    d4 = tmp3.parent / "four_ledger"
    lg.save(d4 / "ledger.json")
    r3b = SimRobot(fast3(), seed=2, data_dir=d4)
    sup3b = Supervisor(r3b.ctx, state_path=d4 / "state.json", ledger_path=d4 / "ledger.json")
    assert list(r3b.ctx.ledger.stations) == list("ABC") and r3b.ctx.ledger.all_valid()
    assert sorted(sup3b.status()["stations"]) == ["A", "B", "C"]


def test_hardware_addresses_and_transport_cover_the_active_stations_only():
    from roomcleaner.cdpr.service import station_addresses
    from roomcleaner.cdpr.transport import UdpHostTransport
    raw = raw_of(EX3)
    raw["claw"]["address"] = "192.168.1.50:80"
    for k, s in enumerate(raw["stations"]):
        s["address"] = None if s["id"] == "D" else f"192.168.1.{10 + k}:8771"           # D has no address and needs none
    cfg = load_config(raw)
    addrs = station_addresses(cfg)
    assert addrs == {"A": ("192.168.1.10", 8771), "B": ("192.168.1.11", 8771), "C": ("192.168.1.12", 8771)}
    tx = UdpHostTransport(addrs, bind=("127.0.0.1", 0))
    try:
        assert sorted(tx.stations) == ["A", "B", "C"] and len(tx.by_addr) == 3         # no transport entry for D: "*" never reaches it
    finally:
        tx.close()
    raw["stations"][2]["address"] = None                                               # an ACTIVE station without an address: refused
    with pytest.raises(SystemExit, match="addresses must be set"):
        station_addresses(load_config(raw))
    raw4 = raw_of("config/robot.example.json")                                         # four stations: D needs one too (unchanged)
    raw4["claw"]["address"] = "192.168.1.50:80"
    for k, s in enumerate(raw4["stations"]):
        s["address"] = None if s["id"] == "D" else f"192.168.1.{10 + k}:8771"
    with pytest.raises(SystemExit, match="addresses must be set"):
        station_addresses(load_config(raw4))
