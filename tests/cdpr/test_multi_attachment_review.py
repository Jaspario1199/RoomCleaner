"""Independent review checks of the four-point claw attachment work (commits b9bc5d0..1c2e968).

Written by the calculation-checker. Nothing here imports the implementer's expectations: every reference value is
recomputed with a different formulation (finite differences of an independently written energy / length function, a
scipy root-finder on the moment balance, the pre-change kinematics module from git, the STEP file itself).

Some tests DOCUMENT a finding (name contains ``finding``): they pass today and are meant to flip when the finding is
fixed. See verification/multi_attachment_review.md.
"""
import itertools
import json
import math
import subprocess
import sys
import types

import numpy as np
import pytest
from scipy.optimize import linprog, minimize, root

from roomcleaner.cdpr.config import load_config
from roomcleaner.cdpr.frames import rot_z, rotvec_to_matrix, rpy_to_matrix
from roomcleaner.cdpr.kinematics import Geometry, geometry_from_config, tension_distribution

from .simkit import fast_cfg
from .test_rigid_body import REVIEW_ANCHORS, REVIEW_ELL, REVIEW_P, make_world, taut_ell

SIM = "config/robot.sim.json"
G = 9.81


# ------------------------------------------------------------------ 1. cable length model and Jacobians
def test_length_model_jacobian_wrt_position_and_rotation_by_finite_difference():
    cfg = load_config(SIM)
    A, b = cfg.anchor_priors(), cfg.attachment_points()
    geo = Geometry(A, b)
    rng = np.random.default_rng(1)
    e = 1e-6
    for _ in range(40):
        p = rng.uniform([0.3, 0.3, 0.6], [3.0, 2.4, 2.1])
        R = rpy_to_matrix(*rng.uniform([-.2, -.2, -3], [.2, .2, 3]))
        u, r = geo.unit_vectors(p, R), b @ R.T
        # independent closed forms: dL = -u.dp  and, for a world-frame rotation w, dL = -w.(r x u)
        Jp, Jw = -u, -np.cross(r, u)
        num_p = np.stack([(geo.lengths(p + e * x, R) - geo.lengths(p - e * x, R)) / (2 * e) for x in np.eye(3)], 1)
        num_w = np.stack([(geo.lengths(p, rotvec_to_matrix(e * x) @ R) - geo.lengths(p, rotvec_to_matrix(-e * x) @ R))
                          / (2 * e) for x in np.eye(3)], 1)
        assert np.allclose(num_p, Jp, atol=1e-7) and np.allclose(num_w, Jw, atol=1e-7)


# ------------------------------------------------------------------ 2. rigid-body equilibrium
def _energy(w, p, R, ell, m, c):
    q = p + (R @ w.attach.T).T
    d = np.linalg.norm(w.anchors - q, axis=1)
    return m * G * (p[2] + (R @ c)[2]) + 0.5 * np.sum(w.EA / ell * np.maximum(d - ell, 0.0) ** 2)


def test_world_equilibrium_balances_force_and_moment_and_hessian_matches_finite_differences():
    w = make_world(fast_cfg(), yaw=0.2)
    m, c = w.mass, w._com()
    rng = np.random.default_rng(4)
    for _ in range(12):
        p0 = rng.uniform([.6, .6, .8], [2.8, 2.1, 2.0])
        R0 = rot_z(rng.uniform(-.5, .5))
        ell = taut_ell(w, p0, R0, rng.uniform(0.002, 0.01, 4))                 # all four taut: smooth energy
        p, R, ok, _ = w._equilibrium(p0, R0, ell)
        assert ok
        q = p + (R @ w.attach.T).T
        dv = w.anchors - q
        d = np.linalg.norm(dv, axis=1)
        n = dv / d[:, None]
        T = w.EA / ell * np.maximum(d - ell, 0.0)
        F = (T[:, None] * n).sum(0) - [0, 0, m * G]                              # force balance
        M = np.cross(q - p - R @ c, T[:, None] * n).sum(0)                       # moment balance about the CoM
        assert np.abs(F).max() < 2e-6 and np.abs(M).max() < 2e-6
        # Hessian: second differences of an independently written energy (valid away from slack/taut kinks)
        pp, RR = p + rng.normal(0, .005, 3), rotvec_to_matrix(rng.normal(0, .03, 3)) @ R
        gr, H = w._grad_hess(pp, RR, ell, m, c, True)
        Uf = lambda x: _energy(w, pp + x[:3], rotvec_to_matrix(x[3:]) @ RR, ell, m, c)
        h = 2e-4
        H2 = np.zeros((6, 6))
        I6 = np.eye(6)
        for i, j in itertools.product(range(6), range(6)):
            a, b_ = h * I6[i], h * I6[j]
            H2[i, j] = (Uf(a + b_) - Uf(a - b_) - Uf(-a + b_) + Uf(-a - b_)) / (4 * h * h)
        assert np.abs(H2 - H).max() / np.abs(H).max() < 1e-5
        gfd = np.array([(Uf(1e-6 * v) - Uf(-1e-6 * v)) / 2e-6 for v in I6])
        assert np.abs(gfd - gr).max() < 1e-6
        # at the solution the Hessian is positive definite (a minimum, not a saddle)
        assert np.linalg.eigvalsh(w._grad_hess(p, R, ell, m, c, True)[1]).min() > 0


def test_non_convergence_is_surfaced_and_state_kept_on_a_real_failure_not_only_a_mock():
    w = make_world(fast_cfg())
    p0 = np.array([1.6, 1.3, 1.3])
    ell = taut_ell(w, p0, w.R, 0.001)
    far = p0 + [0.4, -0.3, 0.2]                                  # start far from the minimum, 2 iterations only
    p, R, ok, resid = w._equilibrium(far, w.R, ell, max_iter=2)
    assert not ok and resid > 1e-4                               # genuinely unconverged, and it says so
    w.on_floor, w.p = False, p0.copy()
    w.ell = lambda: ell
    w._equilibrium = lambda pp, RR, ee, _orig=w._equilibrium, **kw: _orig(far, RR, ee, max_iter=2)
    before = (w.p.copy(), w.R.copy())
    w.settle()
    assert w.eq_failures == 1 and w.events[-1][0] == "no_equilibrium"
    assert np.array_equal(w.p, before[0]) and np.array_equal(w.R, before[1])
    w.strict = True
    with pytest.raises(RuntimeError):
        w.settle()


def test_limit_cycle_state_matches_an_independent_six_dof_minimiser():
    w = make_world(fast_cfg(), anchors=REVIEW_ANCHORS)
    m, c = w.mass, w._com()
    p, R, ok, _ = w._equilibrium(REVIEW_P, w.R, REVIEW_ELL)
    assert ok
    U_new = _energy(w, p, R, REVIEW_ELL, m, c)

    def f(x):
        return _energy(w, REVIEW_P + x[:3], rotvec_to_matrix(x[3:]) @ w.R, REVIEW_ELL, m, c)

    best = minimize(f, np.zeros(6), method="BFGS", options=dict(gtol=1e-10, maxiter=500))
    assert U_new <= best.fun + 1e-9                              # the simulator's state is at least as low
    T = w._forces(p, REVIEW_ELL, R)[0]
    assert T.max() < 7.0                                         # recorded old limit cycle returned 14 / 24 N


# ------------------------------------------------------------------ 3. statics tilt prediction
def _tilt_solve(geo, p, yaw, dist):
    cfgc, m = geo.com, geo.mass_kg
    W = m * np.array([0, 0, G])

    def state(wv):
        R = rotvec_to_matrix(np.array([wv[0], wv[1], 0.0])) @ rot_z(yaw)
        r = geo.attach @ R.T
        d = geo.anchors - (p + r)
        u = d / np.linalg.norm(d, axis=1, keepdims=True)
        if dist == "minnorm":
            T = np.linalg.lstsq(u.T, W, rcond=None)[0]
        else:                                                    # true least TOTAL tension (L1) distribution
            T = linprog(np.ones(4), A_eq=u.T, b_eq=W, bounds=[(0, None)] * 4, method="highs").x
        return np.cross(r - R @ cfgc, T[:, None] * u).sum(0), T

    sol = root(lambda wv: state(wv)[0][:2], [0, 0], tol=1e-13)
    return sol.x, state(sol.x)[1], sol.success


def test_statics_tilt_matches_independent_root_solve_and_is_a_valid_balance():
    cfg = load_config(SIM)
    geo = geometry_from_config(cfg, cfg.anchor_priors(), 0.3)
    for p in ([1.6, 1.3, 1.2], [0.6, 0.6, 1.0], [2.9, 2.3, 1.9], [0.5, 2.2, 1.5]):
        p = np.array(p)
        s = geo._att.solve(p)
        wv, T, ok = _tilt_solve(geo, p, 0.3, "minnorm")
        assert ok and s.ok
        assert np.allclose(np.degrees(wv), np.degrees([s.roll, s.pitch]), atol=1e-6)
        assert np.allclose(T, s.tensions, atol=1e-6)


def test_finding_distribution_is_minimum_norm_not_least_total_tension():
    """Docs/docstrings say 'least-total-tension'. The code uses the minimum 2-norm solution. The LP minimum of sum(T)
    is a different (vertex) distribution with 1-2 lines at zero tension and a different tilt (0.5-1.2 deg here)."""
    cfg = load_config(SIM)
    geo = geometry_from_config(cfg, cfg.anchor_priors(), 0.3)
    diffs = []
    for p in ([1.6, 1.3, 1.2], [0.6, 0.6, 1.0], [2.9, 2.3, 1.9]):
        p = np.array(p)
        w2, T2, _ = _tilt_solve(geo, p, 0.3, "minnorm")
        w1, T1, _ = _tilt_solve(geo, p, 0.3, "minsum")
        assert T1.min() < 1e-6                                   # LP vertex: at least one line carries nothing
        diffs.append(np.degrees(np.linalg.norm(w1 - w2)))
    assert 0.2 < max(diffs) < 2.0


def test_finding_min_norm_tension_can_be_negative_and_R_at_still_uses_it():
    cfg = load_config(SIM)
    geo = geometry_from_config(cfg, cfg.anchor_priors(), 0.0)
    rng = np.random.default_rng(0)
    bad = 0
    for _ in range(600):
        p = rng.uniform([0.2, 0.2, 0.75], [3.15, 2.55, 2.19])
        s = geo._att.solve(p)
        if not s.taut:
            bad += 1
            assert s.ok                                          # reported ok although a tension is negative
            assert np.allclose(geo.R_at(p), s.R)                 # and the prediction is used as is
    assert bad > 0


def test_finding_tilt_prediction_is_sensitive_to_the_com_height_that_the_cad_cannot_know():
    cfg = load_config(SIM)
    A, b = cfg.anchor_priors(), cfg.attachment_points()
    tilts = {}
    for cz in (-0.196, -0.146, -0.10):
        g = Geometry(A, b, com=np.array([0.0008, 0.0012, cz]), mass_kg=0.6)
        s = g._att.solve(np.array([0.6, 0.6, 1.0]))
        tilts[cz] = math.degrees(math.hypot(s.roll, s.pitch))
    assert tilts[-0.10] > 1.5 * tilts[-0.196] and tilts[-0.196] > 5.0      # corner tilt 10 deg -> 17 deg


def _load_old_kinematics():
    src = subprocess.run(["git", "show", "14d5981:roomcleaner/cdpr/kinematics.py"], capture_output=True, text=True)
    if src.returncode != 0:
        pytest.skip("pre-change commit not available")
    mod = types.ModuleType("kin_old")
    sys.modules["kin_old"] = mod                       # dataclasses looks the defining module up
    exec(compile(src.stdout, "kin_old", "exec"), mod.__dict__)
    return mod


def test_single_zero_attachment_point_is_bit_for_bit_the_old_point_claw_model():
    old = _load_old_kinematics()
    cfg = load_config(SIM)
    A = cfg.anchor_priors()
    new = Geometry(A, np.zeros((4, 3)), com=np.array([0.0008, 0.0012, -0.196]), mass_kg=0.6,
                   payload_body=np.array([0, 0, -0.5]))
    oldg = old.Geometry(A, np.zeros((4, 3)))
    assert not new.spaced and new._att is None
    rng = np.random.default_rng(2)
    for _ in range(25):
        p = rng.uniform([0.3, 0.3, 0.6], [3.0, 2.4, 2.1])
        R = rpy_to_matrix(*rng.uniform(-1, 1, 3))
        for RR in (None, R):
            assert np.array_equal(new.lengths(p, RR), oldg.lengths(p, RR))
            assert np.array_equal(new.unit_vectors(p, RR), oldg.unit_vectors(p, RR))
            assert np.array_equal(new.jacobian(p, RR), oldg.jacobian(p, RR))
        assert np.array_equal(new.R_at(p), np.eye(3))
        tn = tension_distribution(new, p, 1.5, t_min=0.5, t_max=40.0, accel=(0, 0, 2.0))
        to = old.tension_distribution(oldg, p, 1.5, t_min=0.5, t_max=40.0, accel=(0, 0, 2.0))
        assert tn.feasible == to.feasible and np.array_equal(tn.tensions, to.tensions)
        assert tn.max_tension == to.max_tension
    L = new.lengths(np.array([1.5, 1.2, 1.1]))
    pn, rn = new.forward(L)
    po, ro = oldg.forward(L)
    assert np.array_equal(pn, po) and rn == ro


# ------------------------------------------------------------------ 4. body frame vs the CAD (STEP file itself)
def test_body_frame_numbers_against_the_step_file():
    cq = pytest.importorskip("cadquery")
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    shp = cq.importers.importStep("exports/step/gripper_electric_housing_with_camera_bay.step")
    origin = np.array([951.8474966951608, 1098.7241179163989, 1103.9898710253387])      # tube axis, inner-mouth height
    holes, walls = [], []
    for f in shp.faces().vals():
        ad = BRepAdaptor_Surface(f.wrapped)
        if ad.GetType() != GeomAbs_Cylinder:
            continue
        ax = ad.Cylinder().Axis()
        P = np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()])
        D = np.array([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
        if abs(ad.Cylinder().Radius() - 0.75) < 1e-3:
            vt, _ = f.tessellate(0.02)
            pts = np.array([[v.x, v.y, v.z] for v in vt])
            D = D if D[1] > 0 else -D
            holes.append((P, D, pts))
        elif abs(abs(D[1]) - 1) < 1e-6 and abs(ad.Cylinder().Radius() - 10.0) < 1e-3:
            walls.append((P, ad.Cylinder().Radius()))
    assert len(holes) == 4
    stations = {}
    for P, D, pts in holes:
        t = (pts - P) @ D
        inner = pts[t < t.min() + 0.6]
        Pc, R = min(walls, key=lambda w_: abs(np.hypot(inner[:, 0] - w_[0][0], inner[:, 2] - w_[0][2]).mean() - w_[1]))
        d, dd = P[[0, 2]] - Pc[[0, 2]], D[[0, 2]]
        a, b_, c_ = dd @ dd, 2 * d @ dd, d @ d - R * R
        ts = [(-b_ + s * math.sqrt(b_ * b_ - 4 * a * c_)) / (2 * a) for s in (1, -1)]
        X = P + min(ts, key=lambda x: abs(x - t.min())) * D
        body_in = np.array([X[0] - origin[0], -(X[2] - origin[2]), X[1] - origin[1]])
        outer = P + t.max() * D
        body_out = np.array([outer[0] - origin[0], -(outer[2] - origin[2]), outer[1] - origin[1]])
        assert abs(math.degrees(math.asin(D[1])) - 21.0) < 0.1
        sx, sy = np.sign(body_in[0]), np.sign(body_in[1])
        stations[{(-1, -1): "A", (1, -1): "B", (1, 1): "C", (-1, 1): "D"}[(int(sx), int(sy))]] = (body_in, body_out)
    cfgb = load_config(SIM).attachment_points()
    for i, s in enumerate("ABCD"):
        bi, bo = stations[s]
        assert np.allclose(bi * 1e-3, cfgb[i], atol=2e-4)                                 # +-42.07 mm, z = 0
        assert abs(abs(bo[0]) - 54.09) < 0.1 and abs(bo[2] - 6.52) < 0.05                 # outer mouth (edge extent)
    anchors = load_config(SIM).anchor_priors()
    c = anchors[:, :2] - anchors[:, :2].mean(0)
    assert np.sign(c).tolist() == np.sign(cfgb[:, :2]).tolist()                           # A-D order matches the room


def test_finding_config_numbers_that_the_cad_has_since_moved_away_from():
    """D28 (-50 mm tube) and the v7 gripper: DECISIONS.md D28 says the tie-off box is 474 mm above the jaw tips when
    gripping; the config still carries the v6 value 517.3 mm. CoM/mass also come from the v6 CAD (2.06 kg of solids)."""
    claw = load_config(SIM).claw
    assert abs(-claw.lowest_point_body_m[2] - 0.474) > 0.04
    assert claw.mass_kg == 0.6                                    # vs 450 g budget and ~1.05-1.25 kg printed estimate
    assert claw.imu is True                                       # D27 removed the IMU


# ------------------------------------------------------------------ 5. reported findings
def test_yaw_sensitivity_reproduces_the_reported_range():
    cfg = fast_cfg()
    A, b = cfg.anchor_priors(), cfg.attachment_points()
    lin = []
    for x, y in itertools.product([0.8, 1.676, 2.55], [0.6, 1.372, 2.1]):
        p = np.array([x, y, 1.2])
        u = (A - (p + b)) / np.linalg.norm(A - (p + b), axis=1, keepdims=True)
        Jm = np.hstack([-u, -np.cross(b, u)[:, 2:3]])
        lin.append(math.degrees(np.linalg.norm(np.linalg.inv(Jm)[3])) * 1e-3)
    assert 5.0 < min(lin) and max(lin) < 6.6                      # tilt-free linear, deg per mm of worst direction
    w = make_world(cfg)
    el = []
    for x, y in itertools.product([0.8, 1.676, 2.55], [0.6, 2.1]):
        p0 = np.array([x, y, 1.2])
        ell0 = taut_ell(w, p0, np.eye(3), 0.002)
        p, R, ok, _ = w._equilibrium(p0, np.eye(3), ell0)
        assert ok
        gy = []
        for i in range(4):
            e = np.zeros(4)
            e[i] = 5e-4
            up = w._equilibrium(p, R, ell0 + e)[1]
            dn = w._equilibrium(p, R, ell0 - e)[1]
            gy.append(math.atan2(up[1, 0], up[0, 0]) - math.atan2(dn[1, 0], dn[0, 0]))
        gy = np.array(gy) / 1e-3
        n = gy / np.linalg.norm(gy)
        R1 = w._equilibrium(p, R, ell0 + 1e-3 * n)[1]
        el.append(abs(math.degrees(math.atan2(R1[1, 0], R1[0, 0]) - math.atan2(R[1, 0], R[0, 0]))))
    assert 2.2 < min(el) and max(el) < 4.0                        # reported 2.4-3.7 deg/mm


def test_finding_attitude_noise_model_cannot_explain_the_reported_sigma_rise():
    """Same sample poses, point-claw vs four-point estimator: the measurement model itself moves the predicted absolute
    sigma by ~1 % (4 mrad attitude noise) to ~9 % (10 mrad), not by the +33 % (11.6 -> 15.4 mm) reported."""
    from roomcleaner.cdpr.calibration import Calibrator, CableLengthModel, PoseSample, box_candidates
    from roomcleaner.cdpr.spool import CableMap
    cfg = load_config(SIM)
    maps = {s.id: CableMap(s.spool, s.drive.usteps_per_rev) for s in cfg.stations}
    b_sp = cfg.attachment_points()

    def synth(aM, L0, pts, rng, b):
        lm = CableLengthModel(maps)
        out = []
        for q in pts:
            R = rot_z(0.25) @ rpy_to_matrix(*rng.normal(0, 0.02, 2), 0.0) @ rot_z(rng.normal(0, 0.15))
            L = np.linalg.norm(aM - (q + b @ R.T), axis=1)
            P = np.array([lm.position(i, L[i], L0[i]) for i in range(4)])
            cov = np.diag([0.004, 0.004, 0.008]) ** 2
            out.append(PoseSample(np.round(P), q + rng.multivariate_normal(np.zeros(3), cov), R, cov, "fit"))
        return out

    ratio4, ratio10 = [], []
    for seed in range(3):
        rng = np.random.default_rng(100 + seed)
        aR = cfg.anchor_priors() + rng.normal(0, 0.05, (4, 3))
        psi = np.array([1.5, 1.45, cfg.marker.heading_prior_rad + 0.15])
        aM = (aR - [psi[0], psi[1], 0]) @ rot_z(psi[2])
        L0 = np.array([2.3, 2.5, 2.4, 2.2])
        big = box_candidates([0, 0, 1.2], (0.8, 0.8, 0.5))
        idx = rng.choice(len(big), 25, replace=False)
        sig = {}
        for name, b, asig in (("point", np.zeros((4, 3)), 0.0), ("sp4", b_sp, 0.004), ("sp10", b_sp, 0.010)):
            smp = synth(aM, L0, big[idx], np.random.default_rng(500 + seed), b)
            c = Calibrator(cfg, maps, attach=b)
            c.cc.attitude_sigma_rad = asig
            sig[name] = c.absolute_sigma(c.fit(smp)).mean()
        ratio4.append(sig["sp4"] / sig["point"])
        ratio10.append(sig["sp10"] / sig["point"])
    assert np.mean(ratio4) < 1.06 and np.mean(ratio10) < 1.15


def test_finding_length_induced_tilt_is_small_so_the_4_degree_cone_does_not_cover_com_uncertainty():
    w = make_world(fast_cfg())
    rng = np.random.default_rng(0)
    p0 = np.array([0.8, 0.6, 1.0])
    ell0 = taut_ell(w, p0, np.eye(3), 0.002)
    p, R, ok, _ = w._equilibrium(p0, np.eye(3), ell0)
    worst = 0.0
    for _ in range(25):
        d = rng.normal(size=4)
        d *= 0.006 / np.linalg.norm(d)                            # 6 mm, the reported predicted length sigma
        RR = w._equilibrium(p, R, ell0 + d)[1]
        worst = max(worst, math.degrees(math.acos(np.clip(RR[:, 2] @ R[:, 2], -1, 1))))
    assert worst < 1.5                                            # length errors tilt the stiff-line claw by ~1 deg
    cfg = load_config(SIM)
    A, b = cfg.anchor_priors(), cfg.attachment_points()
    g0 = Geometry(A, b, com=np.array([0.0, 0.0, -0.196]), mass_kg=0.6)
    g1 = Geometry(A, b, com=np.array([0.0, 0.0, -0.10]), mass_kg=0.6)
    s0, s1 = g0._att.solve(np.array([0.6, 0.6, 1.0])), g1._att.solve(np.array([0.6, 0.6, 1.0]))
    assert math.degrees(math.hypot(s1.roll, s1.pitch) - math.hypot(s0.roll, s0.pitch)) > 4.0   # CoM moves it > 4 deg


def test_finding_straight_chord_to_the_inner_mouth_misplaces_the_line_of_action():
    """A cable that leaves the 1.5 mm x 18.2 mm hole at more than ~2.4 deg from its axis bears on the outer rim: the
    force line of action then passes the rim, not the inner mouth. Pose-dependent path error and lever-arm shift."""
    cfg = load_config(SIM)
    A, b = cfg.anchor_priors(), cfg.attachment_points()
    ax = np.array([[-.6603, -.6603, .3578], [.6603, -.6603, .3578], [.6603, .6603, .3578], [-.6603, .6603, .3578]])
    rng = np.random.default_rng(0)
    th, lat, dl = [], [], []
    for _ in range(1500):
        p = rng.uniform([0.2, 0.2, 0.52], [3.15, 2.55, 1.6])
        for i in range(4):
            u = (A[i] - (p + b[i]))
            u /= np.linalg.norm(u)
            c = float(u @ ax[i])
            th.append(math.degrees(math.acos(c)))
            lat.append(18.22 * math.sqrt(1 - c * c))
            dl.append(18.22 * (1 - c))
    th, lat, dl = map(np.array, (th, lat, dl))
    assert (th < 2.4).mean() < 0.02                                # almost no pose passes freely
    assert np.median(lat) > 6.0 and np.percentile(dl, 95) > 4.0 and dl.max() > 8.0
