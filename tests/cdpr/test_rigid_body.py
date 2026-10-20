"""Multi-attachment (four-point) claw model, rigid-body simulator and the task height limit.

The real claw ties its four lines off at the INNER mouths of the corner cable holes of the electrical box
(config ``claw.attachment_points_body_m``, scripts/extract_claw_body_frame.py). These tests pin down:

* the kinematics L_i = |a_i - (p + R b_i)| against an independent brute-force computation;
* that a single common point reproduces the original point-claw model exactly;
* the simulator hanging the claw as a rigid body (energy minimum, tensions, passive yaw drift, the
  limit-cycle bug of the old undamped Newton);
* calibration with spaced attachments (synthetic data with a rotated claw);
* ``motion.task_max_height_m``.
"""
import json
import math
from types import SimpleNamespace

import numpy as np
import pytest

from roomcleaner.cdpr.calibration import Calibrator, CableLengthModel, PoseSample, box_candidates
from roomcleaner.cdpr.config import ConfigError, load_config
from roomcleaner.cdpr.frames import matrix_to_rpy, rot_z, rotvec_to_matrix, rpy_to_matrix
from roomcleaner.cdpr.kinematics import Geometry, geometry_from_config, tension_distribution
from roomcleaner.cdpr.sim.world import World
from roomcleaner.cdpr.spool import CableMap
from roomcleaner.cdpr.startup import StartupAbort
from roomcleaner.cdpr.tasks import TaskRunner
from roomcleaner.cdpr.trajectory import limits_from_config, model_from, plan_line

from .simkit import build, fast_cfg

SIM = "config/robot.sim.json"
EXAMPLE = "config/robot.example.json"
G = 9.81
COMMON = {"claw.attachment": "common", "claw.attachment_points_body_m": [[0, 0, 0]],
          "claw.lowest_point_body_m": [0, 0, -0.35], "claw.com_body_m": None}


def common_cfg(**kw):
    return fast_cfg(**{**COMMON, **kw})


def make_world(cfg, *, yaw=0.0, xy=(1.6, 1.3), EA=20000.0, mass=0.6, anchors=None):
    _, net, stations, rt, co = build(cfg=cfg)
    w = World(cfg, stations, anchors=cfg.anchor_priors() if anchors is None else anchors, T_R_M=np.eye(4),
              claw_xy=xy, claw_yaw=yaw, EA_n=EA)
    w.mass = w.base_mass = mass
    return w


def taut_ell(w, p, R, stretch):
    """Free lengths that leave the cables stretched by ``stretch`` (m) at the pose (p, R)."""
    d = np.linalg.norm(w.anchors - (p + w.attach @ R.T), axis=1)
    return d - np.asarray(stretch, float)


# ============================================================== configuration from the CAD
def test_config_holds_the_cad_attachment_points():
    cad = json.load(open("verification/claw_body_frame.json"))
    for path in (SIM, EXAMPLE):
        cfg = load_config(path)
        b = cfg.attachment_points()
        assert cfg.claw.attachment == "spaced" and b.shape == (4, 3)
        assert np.allclose(b, cad["attachment_points_body_m"], atol=5e-5)
        # station order A, B, C, D = corners (-,-), (+,-), (+,+), (-,+) of the body frame (yaw 0: body axes = room axes)
        assert np.sign(b[:, :2]).tolist() == [[-1, -1], [1, -1], [1, 1], [-1, 1]]
        assert np.allclose(b[:, 2], 0.0)                        # origin at the height of the inner mouths
        # the config's anchors are in the same corner order at yaw 0
        A = cfg.anchor_priors()
        c = A[:, :2] - A[:, :2].mean(0)
        assert np.sign(c).tolist() == np.sign(b[:, :2]).tolist()
        assert np.allclose(cfg.claw.T_body_cam[:3, 3], cad["camera_in_body"]["translation_m"], atol=5e-5)
        assert cfg.claw.T_body_cam[1, 3] > 0                    # camera bay at body +y
        assert abs(cfg.claw.lowest_point_body_m[2] - cad["lowest_point_body_m"][2]) < 5e-5
        assert cfg.claw.com_body_m is not None and cfg.claw.com_body_m[2] < -0.1
    assert load_config(SIM).motion.task_max_height_m == 1.6 and load_config(EXAMPLE).motion.task_max_height_m == 1.6


# ============================================================== (a) four-point model vs brute force
def brute_lengths(anchors, b, p, R):
    out = []
    for i in range(4):
        q = [p[k] + sum(R[k][j] * b[i][j] for j in range(3)) for k in range(3)]       # q_i = p + R b_i
        out.append(math.sqrt(sum((anchors[i][k] - q[k]) ** 2 for k in range(3))))
    return np.array(out)


def test_four_point_lengths_match_bruteforce():
    rng = np.random.default_rng(5)
    cfg = load_config(SIM)
    A, b = cfg.anchor_priors(), cfg.attachment_points()
    geo = Geometry(A, b)
    for _ in range(40):
        p = rng.uniform([0.3, 0.3, 0.6], [3.0, 2.4, 2.1])
        R = rpy_to_matrix(*rng.uniform([-.2, -.2, -3], [.2, .2, 3]))
        L = brute_lengths(A, b, p, R)
        assert np.allclose(geo.lengths(p, R), L, atol=1e-12)
        U = geo.unit_vectors(p, R)
        for i in range(4):
            q = p + R @ b[i]
            assert np.allclose(U[i], (A[i] - q) / np.linalg.norm(A[i] - q), atol=1e-12)
        eps = 1e-6                                           # dL/dp at fixed R
        num = np.stack([(geo.lengths(p + eps * e, R) - geo.lengths(p - eps * e, R)) / (2 * eps) for e in np.eye(3)], 1)
        assert np.allclose(num, geo.jacobian(p, R), atol=1e-7)
        pf, rms = geo.forward(L, p + 0.02, R)
        assert np.allclose(pf, p, atol=1e-6) and rms < 1e-8
    # the point-claw formula would be wrong by centimetres: the spacing matters
    p = np.array([1.6, 1.3, 1.2])
    assert np.max(np.abs(Geometry(A, np.zeros((4, 3))).lengths(p) - geo.lengths(p, rot_z(0.4)))) > 0.02


def test_planned_attitude_from_statics_balances_the_claw():
    cfg = load_config(SIM)
    geo = geometry_from_config(cfg, cfg.anchor_priors(), yaw=0.35)
    rng = np.random.default_rng(3)
    for _ in range(10):
        p = rng.uniform([0.5, 0.5, 0.8], [2.8, 2.2, 2.0])
        sol = geo._att.solve(p)
        assert sol.ok and sol.taut and sol.residual < 1e-8
        R = sol.R
        assert abs(matrix_to_rpy(R)[2] - 0.35) < 0.01                 # yaw is held, not predicted
        assert np.degrees(math.hypot(sol.roll, sol.pitch)) < 15.0
        # independent wrench balance at the predicted attitude (gravity at the CoM + 4 line tensions)
        U = geo.unit_vectors(p, R)
        F = (sol.tensions[:, None] * U).sum(0) - np.array([0, 0, cfg.claw.mass_kg * G])
        r = geo.attach @ R.T - R @ geo.com
        M = np.cross(r, sol.tensions[:, None] * U).sum(0)
        assert np.allclose(F, 0, atol=1e-7) and np.allclose(M[:2], 0, atol=1e-9)    # forces and both tilt moments
        assert abs(M[2] - sol.yaw_moment) < 1e-9                    # the vertical-axis moment is reported, not balanced
        assert np.allclose(geo.R_at(p), R)                          # what lengths()/planning use
        assert np.allclose(geo.lengths(p), brute_lengths(geo.anchors, geo.attach, p, R), atol=1e-12)
    # no internal pretension, a small vertical-axis moment: the nominal yaw is close to the installed one
    near = geometry_from_config(cfg, cfg.anchor_priors(), yaw=0.0)
    for _ in range(10):
        sol = near._att.solve(rng.uniform([0.5, 0.5, 0.8], [2.8, 2.2, 2.0]))
        assert sol.ok and sol.taut and np.degrees(math.hypot(sol.roll, sol.pitch)) < 12.0 and abs(sol.yaw_moment) < 0.05
    # a payload at the jaws (CoM moves down and the tensions grow): same balance with the heavier claw
    p = np.array([1.6, 1.3, 1.2])
    s0, s1 = geo._att.solve(p), geo._att.solve(p, mass_kg=cfg.claw.mass_kg + 0.9)
    assert s1.ok and s1.tensions.sum() > 2 * s0.tensions.sum()


def test_simulator_relaxes_to_the_predicted_attitude_when_given_consistent_lengths(spaced_world):
    """Planner and plant agree: free lengths d_i - T_i/k_i from the predicted statics put the simulated claw (energy
    minimum) at the predicted position and tilt, with only the passive yaw free to creep."""
    w = spaced_world
    geo = geometry_from_config(load_config(SIM), w.anchors, yaw=0.0)
    rng = np.random.default_rng(5)
    for _ in range(8):
        p = rng.uniform([0.6, 0.6, 0.9], [2.7, 2.1, 2.0])
        sol = geo._att.solve(p)
        d = np.linalg.norm(w.anchors - (p + w.attach @ sol.R.T), axis=1)
        ell = d - sol.tensions / (w.EA / d)
        p1, R1, ok, _ = w._equilibrium(p, np.eye(3), ell)
        assert ok and np.linalg.norm(p1 - p) < 5e-4
        tilt = lambda R: np.array(matrix_to_rpy(R)[:2])
        assert np.max(np.abs(np.degrees(tilt(R1) - tilt(sol.R)))) < 0.3
        assert abs(yaw_of(R1)) < 0.6


def test_prediction_is_anchored_to_the_last_measured_pose():
    """Where a pose has been measured, R_at returns the measurement exactly; elsewhere the statics-predicted change
    is applied on top of it (so the planner never jumps by the nominal tilt at the pose it starts from)."""
    cfg = load_config(SIM)
    geo = geometry_from_config(cfg, cfg.anchor_priors())
    p_ref = np.array([1.6, 1.3, 1.2])
    R_meas = rot_z(0.2) @ rpy_to_matrix(0.03, -0.02, 0.0)          # a tilt the statics do not predict
    nominal_ref = geo.R_at(p_ref)
    geo.set_reference(p_ref, R_meas)
    assert np.allclose(geo.R_at(p_ref), R_meas, atol=1e-12) and abs(geo.yaw - math.atan2(R_meas[1, 0], R_meas[0, 0])) < 1e-12
    assert np.allclose(geo.lengths(p_ref), brute_lengths(geo.anchors, geo.attach, p_ref, R_meas), atol=1e-12)
    p2 = p_ref + [0.4, -0.3, 0.5]
    d_nom = geometry_from_config(cfg, cfg.anchor_priors(), yaw=geo.yaw)
    n2, n1 = d_nom.R_at(p2), d_nom.R_at(p_ref)
    assert np.allclose(geo.R_at(p2), R_meas @ n1.T @ n2, atol=1e-9)   # the statics-predicted change is carried over
    assert np.degrees(math.acos(min(1.0, (np.trace(R_meas @ nominal_ref.T) - 1) / 2))) > 0.5   # the offset was non-trivial


# ============================================================== (b) one common point = the old model
def test_single_point_reproduces_the_point_claw_model_exactly():
    cfg = common_cfg()
    assert cfg.claw.attachment == "common"
    A = cfg.anchor_priors()
    geo = geometry_from_config(cfg, A, yaw=0.9)
    legacy = Geometry(A, np.zeros((4, 3)))
    assert not geo.spaced and geo._att is None
    rng = np.random.default_rng(1)
    for _ in range(20):
        p = rng.uniform([0.3, 0.3, 0.5], [3.0, 2.4, 2.1])
        R = rpy_to_matrix(*rng.uniform(-1, 1, 3))
        assert np.array_equal(geo.R_at(p), np.eye(3))
        assert np.array_equal(geo.lengths(p), legacy.lengths(p))
        assert np.array_equal(geo.lengths(p), np.linalg.norm(A - p, axis=1))
        assert np.allclose(geo.lengths(p, R), np.linalg.norm(A - p, axis=1), atol=1e-14)   # R is irrelevant
        t0 = tension_distribution(geo, p, cfg.claw.mass_kg, t_min=0.5, t_max=15.0)
        t1 = tension_distribution(legacy, p, cfg.claw.mass_kg, t_min=0.5, t_max=15.0)
        assert t0.feasible == t1.feasible and np.array_equal(t0.tensions, t1.tensions)
    # a planned line is identical, knot for knot
    maps0 = {s.id: CableMap(s.spool, s.drive.usteps_per_rev).with_reference(2.0) for s in cfg.stations}
    m_new = model_from(geo, cfg, {s: 2.0 for s in maps0})
    m_old = model_from(legacy, cfg, {s: 2.0 for s in maps0})
    lim = limits_from_config(cfg)
    a, b = np.array([1.2, 1.0, 1.0]), np.array([2.0, 1.6, 1.3])
    p_new, p_old = plan_line(m_new, a, b, lim), plan_line(m_old, a, b, lim)
    assert np.array_equal(p_new.pos, p_old.pos) and np.array_equal(p_new.vel, p_old.vel)


def old_hang(w, p0, ell):
    """The simulator's original 3-DOF Newton (commit before the rigid-body change), for comparison."""
    p = p0.copy()
    for _ in range(30):
        T, n, d, k = w._forces(p, ell)
        g = np.array([0, 0, w.mass * G]) - (T[:, None] * n).sum(0)
        H = np.zeros((3, 3))
        for i in range(4):
            if T[i] > 0:
                H += k[i] * ((1 - ell[i] / d[i]) * np.eye(3) + ell[i] / d[i] * np.outer(n[i], n[i]))
        H += 1e-6 * np.eye(3)
        step = -np.linalg.solve(H, g)
        if np.linalg.norm(step) > 0.05:
            step *= 0.05 / np.linalg.norm(step)
        p = p + step
        if np.linalg.norm(step) < 1e-9:
            break
    return p


def test_single_point_world_is_the_old_three_dof_point():
    w = make_world(common_cfg(), yaw=0.7)
    assert not w.rigid
    rng = np.random.default_rng(4)
    for _ in range(10):
        p0 = rng.uniform([1.0, 0.8, 1.0], [2.2, 1.8, 1.8])
        ell = np.linalg.norm(w.anchors - p0, axis=1) - rng.uniform(0.0005, 0.004, 4)
        R0 = w.R.copy()
        p, R, ok, res = w._equilibrium(p0 + rng.normal(0, 0.01, 3), R0, ell)
        assert ok and np.array_equal(R, R0)                         # orientation untouched
        assert np.allclose(p, old_hang(w, p0, ell), atol=1e-7)      # same equilibrium as the original solver


# ============================================================== (c) rigid-body equilibrium
@pytest.fixture(scope="module")
def spaced_world():
    return make_world(fast_cfg(), yaw=0.15)


def test_rigid_equilibrium_is_an_energy_minimum_with_balanced_wrench(spaced_world):
    w = spaced_world
    assert w.rigid
    rng = np.random.default_rng(7)
    for _ in range(12):
        p0 = rng.uniform([0.8, 0.7, 0.9], [2.6, 2.0, 1.9])
        R0 = rot_z(rng.uniform(-0.4, 0.4))
        ell = taut_ell(w, p0, R0, rng.uniform(0.0003, 0.002, 4))
        p, R, ok, resid = w._equilibrium(p0 + rng.normal(0, 0.01, 3), R0 @ rotvec_to_matrix(rng.normal(0, 0.03, 3)), ell)
        assert ok and resid < 1e-5
        T, n, d, k = w._forces(p, ell, R)
        assert np.all(T >= 0)
        c = w._com()
        # independent wrench check at the returned state
        F = (T[:, None] * n).sum(0) - np.array([0, 0, w.mass * G])
        r = w.attach @ R.T - R @ c
        M = np.cross(r, T[:, None] * n).sum(0)
        assert np.allclose(F, 0, atol=1e-5) and np.allclose(M, 0, atol=1e-6)
        U0 = w._energy(p, R, ell, w.mass, c)
        grad, H = w._grad_hess(p, R, ell, w.mass, c, True)
        assert np.min(np.linalg.eigvalsh(H)) > -1e-6                 # positive semi-definite: a minimum, not a saddle
        for _ in range(60):                                          # no nearby pose has lower energy
            dp, dw = rng.normal(0, 2e-4, 3), rng.normal(0, 2e-4, 3)
            assert w._energy(p + dp, rotvec_to_matrix(dw) @ R, ell, w.mass, c) >= U0 - 1e-9
    assert w.eq_failures == 0


def test_hessian_matches_second_differences(spaced_world):
    w = spaced_world
    p0, R0 = np.array([1.5, 1.2, 1.3]), rot_z(0.2) @ rpy_to_matrix(0.01, -0.02, 0)
    ell = taut_ell(w, p0, R0, [0.0006, 0.0009, 0.0004, 0.0011])
    c = w._com()
    grad, H = w._grad_hess(p0, R0, ell, w.mass, c, True)
    U = lambda x: w._energy(p0 + x[:3], rotvec_to_matrix(x[3:]) @ R0, ell, w.mass, c)
    e, E = 1e-4, np.eye(6)
    Hn = np.array([[(U(e * (E[i] + E[j])) - U(e * (E[i] - E[j])) - U(e * (-E[i] + E[j])) + U(e * (-E[i] - E[j])))
                    / (4 * e * e) for j in range(6)] for i in range(6)])
    gn = np.array([(U(1e-6 * E[i]) - U(-1e-6 * E[i])) / 2e-6 for i in range(6)])
    assert np.allclose(grad, gn, atol=1e-6) and np.allclose(H, Hn, atol=2e-3 * np.abs(H).max() / 1e3 + 1e-3)


def yaw_of(R):
    return math.degrees(matrix_to_rpy(R)[2])


def worst_mode(w, p):
    """Linear (inextensible, tilt-free) yaw sensitivity: the length-error direction with the largest yaw response."""
    r = w.attach
    u = w.anchors - (p + r)
    u /= np.linalg.norm(u, axis=1)[:, None]
    lever = -np.einsum("ij,ij->i", u, np.cross([0, 0, 1], r))
    J = np.hstack([-u, lever[:, None]])
    row = np.linalg.inv(J)[3]
    return row / np.linalg.norm(row), math.degrees(np.linalg.norm(row)) * 1e-3


def test_passive_yaw_drift_under_a_length_error_is_of_the_reviewed_size(spaced_world):
    """Review F6: 3.6 to 6 deg of yaw per mm of line-length inconsistency (rigid claw on inextensible lines,
    tilt-free linear model). The simulator (elastic lines, roll/pitch free) must show the same effect."""
    w = spaced_world
    lin_all, sim_all = [], []
    for xy in ((1.6, 1.3), (0.9, 0.8), (2.4, 1.9)):
        for z in (0.9, 1.3, 1.8):
            p = np.array([*xy, z])
            R0 = rot_z(0.0)
            ell = taut_ell(w, p, R0, 0.001)
            p0, Rb, ok, _ = w._equilibrium(p, R0, ell)
            assert ok
            mode, lin = worst_mode(w, p)
            p1, R1, ok1, _ = w._equilibrium(p0, Rb, ell + mode * 1e-3)     # 1 mm (vector norm) of inconsistency
            assert ok1
            drift = abs(yaw_of(R1) - yaw_of(Rb))
            lin_all.append(lin)
            sim_all.append(drift)
            assert 0.35 * lin < drift < 1.15 * lin, (xy, z, drift, lin)    # elasticity and tilt coupling reduce it
            assert np.linalg.norm(p1 - p0) < 3e-3                           # the position stays put: only yaw gives
    assert 3.6 <= min(lin_all) and max(lin_all) <= 7.0                      # the review's order of magnitude
    assert min(sim_all) > 2.0 and max(sim_all) < 7.0
    # symmetric: the opposite error drifts the other way; no error, no drift
    p = np.array([1.6, 1.3, 1.3])
    ell = taut_ell(w, p, rot_z(0.0), 0.001)
    p0, Rb, _, _ = w._equilibrium(p, rot_z(0.0), ell)
    mode, _ = worst_mode(w, p)
    dyaw = [yaw_of(w._equilibrium(p0, Rb, ell + s * mode * 1e-3)[1]) - yaw_of(Rb) for s in (1, -1)]
    assert dyaw[0] * dyaw[1] < 0 and abs(dyaw[0] + dyaw[1]) < 0.35 * abs(dyaw[0])
    assert abs(yaw_of(w._equilibrium(p0, Rb, ell)[1]) - yaw_of(Rb)) < 1e-6


def test_motor_commands_move_the_claw_without_losing_the_equilibrium():
    """Through the real settle(): the pose follows slow free-length changes and every state is an equilibrium."""
    w = make_world(fast_cfg(), yaw=0.1)
    w.strict = True
    p0 = np.array([1.6, 1.3, 1.3])
    ell = taut_ell(w, p0, w.R, 0.001)
    w.on_floor = False
    w.p = p0
    w.ell = lambda: ell                                               # drive the free lengths directly
    yaws = []
    for k in range(40):
        ell = ell - np.array([0.0004, 0.0, -0.0004, 0.0])             # slow, slightly inconsistent shortening
        w.settle()
        T, n, d, kk = w._forces(w.p, ell)
        c = w._com()
        Rr = w.attach @ w.R.T - w.R @ c
        assert np.allclose((T[:, None] * n).sum(0), [0, 0, w.mass * G], atol=1e-4)
        assert np.allclose(np.cross(Rr, T[:, None] * n).sum(0), 0, atol=1e-5)
        yaws.append(yaw_of(w.R))
    assert w.eq_failures == 0 and max(yaws) - min(yaws) > 0.2          # yaw drifts: passive degree of freedom


# ============================================================== simulator limit-cycle regression
# Recorded state of verification/slack_probe_review.md (seed 6, t = 1806.70 s, z = 1.446 m): the old undamped
# Newton returned an iterate of a 2-cycle (14 / 24 N); the convex energy minimum has at most 5.5 N.
REVIEW_ANCHORS = np.array([[0.09675902233802439, -0.029915812897558028, 2.6281711972113406],
                           [3.3747790902804558, 0.07576337591173413, 2.651577270580651],
                           [3.285081543284766, 2.6212090451906946, 2.5782608973984664],
                           [0.10697483709598357, 2.7489196468982477, 2.5799438462946576]])
REVIEW_ELL = np.array([3.4021554010805435, 2.8125584623644526, 1.5682327696229539, 2.446110875293816])
REVIEW_P = np.array([2.2359623584770616, 2.3368087288241846, 1.4463272851120872])


@pytest.mark.parametrize("profile", ["common", "spaced"])
def test_world_hang_converges_at_the_recorded_limit_cycle_state(profile):
    from scipy.optimize import minimize
    cfg = common_cfg() if profile == "common" else fast_cfg()
    w = make_world(cfg, anchors=REVIEW_ANCHORS)
    w.strict = True
    ell, c = REVIEW_ELL, w._com()
    if profile == "common":                       # the exact state of the review: the old solver does cycle there
        seen_old = []
        p = REVIEW_P.copy()
        for _ in range(6):
            p = old_hang(w, p, ell)
            seen_old.append(float(np.max(w._forces(p, ell)[0])))
        U = lambda p_: w._energy(p_, w.R, ell, w.mass, c)
        pe = minimize(U, REVIEW_P, method="Nelder-Mead", options=dict(xatol=1e-9, fatol=1e-12, maxiter=4000)).x
        T_eq = w._forces(pe, ell)[0].max()
        assert T_eq < 7.0 and max(seen_old) > 3 * T_eq                # documents the old failure
    p, R = REVIEW_P.copy(), w.R.copy()
    tmax = []
    for _ in range(8):                            # successive settles of an unchanged state: a fixed point
        p, R, ok = w._hang_checked(p, R, ell)
        assert ok
        tmax.append(float(np.max(w._forces(p, ell, R)[0])))
    assert max(tmax) < 7.0 and max(tmax) - min(tmax) < 1e-4, tmax
    T, n, d, k = w._forces(p, ell, R)
    r = w.attach @ R.T - R @ c
    assert np.allclose((T[:, None] * n).sum(0), [0, 0, w.mass * G], atol=1e-5)
    assert np.allclose(np.cross(r, T[:, None] * n).sum(0), 0, atol=1e-6)
    assert w.eq_failures == 0


def test_hang_is_stable_over_random_states_and_never_limit_cycles(spaced_world):
    w = spaced_world
    rng = np.random.default_rng(11)
    for _ in range(40):
        A = w.anchors
        p0 = rng.uniform([0.5, 0.5, 0.6], [2.8, 2.2, 2.1])
        R0 = rot_z(rng.uniform(-0.3, 0.3))
        ell = taut_ell(w, p0, R0, rng.uniform(-0.01, 0.01, 4) + 0.002)     # some slack, some taut
        p, R, ok, resid = w._equilibrium(p0 + rng.normal(0, 0.02, 3), R0, ell)
        assert ok, (p0, ell)
        p2, R2, ok2, _ = w._equilibrium(p, R, ell)                          # idempotent: a true fixed point
        assert ok2 and np.allclose(p2, p, atol=1e-8) and np.allclose(R2, R, atol=1e-8)
        assert np.max(w._forces(p, ell, R)[0]) < 60.0


def test_non_convergence_is_reported_not_returned(spaced_world, monkeypatch):
    w = make_world(fast_cfg())
    p0 = np.array([1.6, 1.3, 1.3])
    ell = taut_ell(w, p0, w.R, 0.001)
    w.on_floor, w.p = False, p0.copy()
    w.ell = lambda: ell
    monkeypatch.setattr(w, "_equilibrium", lambda p, R, e, **kw: (p + 0.1, R, False, 3.7))
    p_before, R_before = w.p.copy(), w.R.copy()
    w.settle()
    assert w.eq_failures == 1 and w.events[-1][0] == "no_equilibrium"
    assert np.array_equal(w.p, p_before) and np.array_equal(w.R, R_before)    # the non-equilibrium state is NOT adopted
    w.strict = True
    with pytest.raises(RuntimeError, match="no static equilibrium"):
        w.settle()


# ============================================================== planning with the predicted attitude
def test_plan_line_uses_the_attitude_consistent_lengths():
    cfg = load_config(SIM)
    geo = geometry_from_config(cfg, cfg.anchor_priors(), yaw=0.2)
    model = model_from(geo, cfg, {s.id: 2.5 for s in cfg.stations})
    lim = limits_from_config(cfg)
    a, b = np.array([1.2, 1.0, 1.0]), np.array([2.0, 1.7, 1.5])
    plan = plan_line(model, a, b, lim)
    for q, P in zip(plan.cart, plan.pos):
        Rq = geo.R_at(q)
        L = brute_lengths(geo.anchors, geo.attach, q, Rq)
        assert np.allclose(P, [model.maps[s].position(Li) for s, Li in zip(model.ids, L)], atol=1e-6)
    # feed-forward velocity = derivative of the positions (the tilt that follows the position is included)
    fd = np.gradient(plan.pos, plan.times, axis=0)
    mid = slice(len(plan.times) // 4, 3 * len(plan.times) // 4)
    assert np.allclose(plan.vel[mid], fd[mid], rtol=0.03, atol=0.05 * np.abs(plan.vel).max())


# ============================================================== calibration with spaced attachments
def synth(cfg, maps, aM, L0, pts, rng, *, kind="fit", slack=None, wrong_R=False):
    """Samples of a claw hung from the 4 attachment points with a (random) orientation in the marker frame."""
    b = cfg.attachment_points()
    lm = CableLengthModel(maps)
    out = []
    for k, q in enumerate(pts):
        R = rot_z(0.25) @ rpy_to_matrix(*rng.normal(0, 0.02, 2), 0.0) @ rot_z(rng.normal(0, 0.15))
        L = np.linalg.norm(aM - (q + b @ R.T), axis=1)
        if slack is not None and slack[k] is not None:
            L[slack[k][0]] += slack[k][1]
        P = np.array([lm.position(i, L[i], L0[i]) for i in range(4)])
        cov = np.diag([0.002, 0.002, 0.004]) ** 2
        Rm = np.eye(3) if wrong_R else R
        out.append(PoseSample(np.round(P), q + rng.multivariate_normal(np.zeros(3), cov), Rm, cov, kind))
    return out


@pytest.fixture(scope="module")
def cal_setup():
    cfg = load_config(SIM)
    maps = {s.id: CableMap(s.spool, s.drive.usteps_per_rev) for s in cfg.stations}
    rng = np.random.default_rng(1)
    aR = cfg.anchor_priors() + rng.normal(0, 0.05, (4, 3))
    psi = np.array([1.5, 1.45, cfg.marker.heading_prior_rad + 0.15])
    aM = (aR - [psi[0], psi[1], 0]) @ rot_z(psi[2])
    return cfg, maps, aM, psi, np.array([2.3, 2.5, 2.4, 2.2])


def test_estimator_with_spaced_attachments_recovers_the_truth_and_slack_hypotheses(cal_setup):
    cfg, maps, aM, psi, L0 = cal_setup
    cal = Calibrator(cfg, maps)
    assert cal.spaced
    rng = np.random.default_rng(2)
    big = box_candidates([0, 0, 1.2], (0.8, 0.8, 0.5))
    pick = rng.choice(len(big), 30, replace=False)
    slack = [(1, 0.02) if k == 3 else (2, 0.015) if k == 9 else None for k in range(25)]
    fit = synth(cfg, maps, aM, L0, big[pick[:25]], rng, slack=slack)
    wit = synth(cfg, maps, aM, L0, big[pick[25:]], rng, kind="witness")
    res = cal.fit(fit)
    assert res.norm_rms < cfg.calibration.norm_rms_max
    assert res.slack is not None and res.slack[3, 1] and res.slack[9, 2]      # slack hypotheses use R and b_i
    assert res.slack.sum() == 2
    rep = cal.validate(res, wit, box_candidates([0, 0, 1.0], (0.8, 0.8, 0.5), (3, 3, 3)))
    assert rep["accepted"], rep["reasons"]
    assert abs(math.remainder(res.psi[2] - psi[2], 2 * math.pi)) < 0.05
    assert np.max(np.abs(res.psi[:2] - psi[:2])) < 0.1
    # the posterior is honest where we have not been (predicted attitude at the held yaw is used)
    for q in box_candidates([0, 0, 1.0], (0.6, 0.6, 0.3), (3, 3, 2)):
        Rq = cal.predicted_R(res.anchors_M, q)
        err = np.linalg.norm(res.anchors_M - (q + cfg.attachment_points() @ Rq.T), axis=1) - res.L0 \
            - (np.linalg.norm(aM - (q + cfg.attachment_points() @ Rq.T), axis=1) - L0)
        assert np.all(np.abs(err) < 3 * cal.length_sigma(res, q) + 1e-3)


def test_ignoring_the_attachment_spacing_biases_the_fit(cal_setup):
    """Negative control: the same data fitted as a point claw (b = 0) fits worse than with the b_i."""
    cfg, maps, aM, psi, L0 = cal_setup
    rng = np.random.default_rng(8)
    big = box_candidates([0, 0, 1.2], (0.8, 0.8, 0.5))
    fit = synth(cfg, maps, aM, L0, big[rng.choice(len(big), 12, replace=False)], rng)
    good = Calibrator(cfg, maps).fit(fit)
    bad = Calibrator(cfg, maps, attach=np.zeros((4, 3))).fit(fit)
    assert good.norm_rms < 1.2 and bad.norm_rms > 1.5 * good.norm_rms, (good.norm_rms, bad.norm_rms)


# ============================================================== task height limit
def test_task_layer_refuses_targets_above_task_max_height():
    cfg = load_config(SIM)
    zf = -cfg.claw.lowest_point_body_m[2]
    tc = cfg.tasks
    # the default task heights stay under the limit with this claw
    assert tc.scan_height_m <= cfg.motion.task_max_height_m
    assert zf + tc.hamper_height_m + tc.release_clearance_m <= cfg.motion.task_max_height_m
    ctx = SimpleNamespace(cfg=cfg, validated_volume=None, ledger=SimpleNamespace(level="VERIFIED"))
    runner = TaskRunner(ctx, perception=None)
    with pytest.raises(StartupAbort, match=r"above motion\.task_max_height_m \(1\.60 m\)") as e:
        runner._move(np.array([1.0, 1.0, 1.75]), label="transport")
    assert "transport" in str(e.value) and "1.750" in str(e.value)
    with pytest.raises(StartupAbort, match="task_max_height_m"):
        runner._move(np.array([1.0, 1.0, 1.6 + 1e-3]), label="raise")
    # exactly at the limit passes the height check (it is refused later, for a different reason: no model here)
    with pytest.raises(Exception) as e2:
        runner._move(np.array([1.0, 1.0, 1.6]), label="at limit")
    assert "task_max_height_m" not in str(e2.value)
    # the config knob validates
    raw = json.load(open(SIM))
    raw["motion"]["task_max_height_m"] = -1.0
    with pytest.raises(ConfigError):
        load_config(raw)
