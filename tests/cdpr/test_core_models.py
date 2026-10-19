import json
import math

import numpy as np
import pytest

from roomcleaner.cdpr import frames as F
from roomcleaner.cdpr.config import ConfigError, load_config
from roomcleaner.cdpr.kinematics import Geometry, tension_distribution, workspace_from_config
from roomcleaner.cdpr.spool import CableMap, SpoolRangeError

SIM = "config/robot.sim.json"
HW = "config/robot.example.json"


def test_frames_roundtrip():
    rng = np.random.default_rng(1)
    for _ in range(50):
        rpy = rng.uniform([-1, -1.2, -3], [1, 1.2, 3])
        R = F.rpy_to_matrix(*rpy)
        assert np.allclose(F.matrix_to_rpy(R), rpy)
        rv = F.matrix_to_rotvec(R)
        assert np.allclose(F.rotvec_to_matrix(rv), R, atol=1e-9)
        T = F.make_T(R, rng.normal(size=3))
        assert F.is_rigid(T)
        assert np.allclose(F.inv_T(T) @ T, np.eye(4))
    assert math.isclose(F.tilt_angle(F.rot_x(0.2)), 0.2)


def test_hardware_template_is_fail_closed():
    c = load_config(HW)
    for stage in c.STAGE_ORDER:
        m = c.missing(stage)
        assert m, stage
        with pytest.raises(ConfigError):
            c.require(stage)
    assert "authorization.suspended_motion_authorized" in c.missing("synchronized_motion")
    assert "authorization.suspended_motion_authorized" not in c.missing("station_bench")


def test_sim_profile_complete():
    c = load_config(SIM)
    for stage in c.STAGE_ORDER:
        assert c.missing(stage) == [], stage


def test_config_rejects_unknown_keys_and_bad_ids(tmp_path):
    raw = json.loads(open(SIM).read())
    raw["motion"]["max_speed_typo"] = 1
    with pytest.raises(ConfigError):
        load_config(raw)
    raw = json.loads(open(SIM).read())
    raw["stations"][0]["id"] = "Z"
    with pytest.raises(ConfigError):
        load_config(raw)
    raw = json.loads(open(SIM).read())
    raw["stations"][1]["drive"]["microsteps"] = 3
    with pytest.raises(ConfigError):
        load_config(raw)


def test_spool_roundtrip_and_derivative():
    c = load_config(SIM)
    s = c.station("B")
    m = CableMap(s.spool, s.drive.usteps_per_rev, L0=2.6)
    Ls = np.linspace(0.3, 5.5, 40)
    Ps = np.array([m.position(L) for L in Ls])
    assert np.all(np.diff(Ps) > 0)                       # payout = more length
    assert np.allclose([m.length(P) for P in Ps], Ls, atol=1e-9)
    for L in (0.8, 2.0, 4.7):
        P = m.position(L)
        num = (m.length(P + 50) - m.length(P - 50)) / 100
        assert math.isclose(num, m.payout_per_ustep(L), rel_tol=0.02)
    assert m.radius(5.5) < m.radius(0.3)                 # less wound when cable long
    with pytest.raises(SpoolRangeError):
        m.position(7.0)                                   # more than the cut length
    with pytest.raises(RuntimeError):
        CableMap(s.spool, s.drive.usteps_per_rev).length(0)


def test_geometry_jacobian_forward_and_statics():
    c = load_config(SIM)
    geo = Geometry(c.anchor_priors(), c.attachment_points())
    p = np.array([1.2, 1.5, 0.9])
    J = geo.jacobian(p)
    eps = 1e-6
    num = np.stack([(geo.lengths(p + eps * e) - geo.lengths(p - eps * e)) / (2 * eps) for e in np.eye(3)], 1)
    assert np.allclose(J, num, atol=1e-6)
    pf, rms = geo.forward(geo.lengths(p))
    assert np.allclose(pf, p, atol=1e-7) and rms < 1e-9
    r = tension_distribution(geo, p, 1.0, t_min=0.5, t_max=50)
    u = geo.unit_vectors(p)
    assert r.feasible
    assert np.allclose(r.tensions @ u, [0, 0, 9.81], atol=1e-6)
    assert np.all(r.tensions >= 0.5 - 1e-9)
    # near the anchor plane the claw cannot be held with small tensions
    top = np.array([1.6, 1.3, c.anchor_priors()[0, 2] - 0.05])
    assert not tension_distribution(geo, top, 1.0, t_min=0.5, t_max=15).feasible


def test_spaced_attachment_lengths():
    b = np.array([[0.05, 0.05, 0], [-0.05, 0.05, 0], [-0.05, -0.05, 0], [0.05, -0.05, 0]])
    a = np.array([[0, 0, 2], [3, 0, 2], [3, 3, 2], [0, 3, 2]], float)
    geo = Geometry(a, b)
    p = np.array([1.5, 1.5, 1.0])
    assert np.allclose(geo.lengths(p), np.linalg.norm(a - (p + b), axis=1))
    R = F.rot_z(0.3)
    assert np.allclose(geo.lengths(p, R), np.linalg.norm(a - (p + b @ R.T), axis=1))


def test_workspace_enforces_bead_minimum_length():
    c = load_config(SIM)
    anchors = c.anchor_priors()
    geo = Geometry(anchors, c.attachment_points())
    ws = workspace_from_config(c, anchors, lowest_point_z=-0.35)
    near_A = anchors[0] + np.array([0.5, 0.5, -0.8])
    v = ws.violations(geo, near_A)
    assert any("cable A" in s and "minimum" in s for s in v)
    assert ws.violations(geo, [1.6, 1.3, 1.0]) == []
    assert ws.violations(geo, [1.6, 1.3, 0.1])            # jaws would be below the floor
    assert ws.violations(geo, [1.6, 1.3, 0.1], allow_low=True) == []
