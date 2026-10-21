"""Pins the load and hand-calc numbers quoted in docs/simulation/*.md.

If a repo input changes (Vref, hold torque, spool radius, fin thickness), these
fail and the two manuals must be refreshed from calculations/simulation_loads.py.
"""
import math

import pytest

from calculations import simulation_loads as SL


def test_tension_cases_match_repo_conventions():
    # 32 N @ 1.0 A and 48 N @ 1.5 A are the repo's structural worst cases
    assert SL.tension_cases(1.0)["slip"] == pytest.approx(32.0, abs=0.01)
    assert SL.tension_cases(1.5)["slip"] == pytest.approx(48.0, abs=0.01)
    t = SL.tension_cases()
    assert SL.I_SET == pytest.approx(1.0625)
    assert t["slip"] == pytest.approx(34.0, abs=0.01)           # D30 "~34 N"
    assert t["dyn"] == pytest.approx(2 * t["slip"])
    assert t["work"] == pytest.approx(17.85, abs=0.01)
    assert SL.tension_cases(SL.I_SET, SL.HOLD_40)["slip"] / t["slip"] == pytest.approx(40 / 36)


def test_direction_vectors_and_tangent_points():
    for _, _, th, ps, _ in SL.CASES:
        u = SL.unit_vector(th, ps)
        assert math.isclose(float((u ** 2).sum()), 1.0, rel_tol=1e-12)
        assert u[2] <= 1e-12                                    # the line never pulls upward
        p = SL.tangent_point(u)
        assert p[0] >= -1e-9                                    # tangent point on the room side
        in_plane = math.hypot(p[0], p[2])
        assert in_plane == pytest.approx(7.5, abs=1e-9)         # on the drum core
        h = math.hypot(u[0], u[2])
        assert abs(p[0] * u[0] + p[2] * u[2]) / (7.5 * h) < 1e-9   # radius perpendicular to the line


def test_allowables_and_identity():
    a = SL.allowables()
    assert a["vm_static"] == pytest.approx(25.0 / 3.0)
    # SF 3 at the slip-limit load is the same stress criterion as SF 1.5 at twice that load
    assert a["vm_dynamic"] == pytest.approx(2 * a["vm_static"])
    assert a["p1_layer"] == pytest.approx(7.5)


def test_motor_heat_matches_two_node_model_convention():
    import calculations.gen2_motor_thermal as mt
    assert SL.R_PHASE == mt.R_PHASE
    assert SL.motor_heat() == pytest.approx(SL.I_SET ** 2 * mt.R_PHASE)
    assert SL.motor_heat() == pytest.approx(2.03, abs=0.01)


def test_fin_hand_calc_targets():
    P = SL.motor_heat()
    f = SL.fin_analytic(SL.ALLOYS["6061-T6"], SL.T_AS_BUILT, 9.6)
    assert f["eta"] == pytest.approx(0.32, abs=0.01)
    assert f["R"] == pytest.approx(18.3, abs=0.5)
    assert P * f["R"] == pytest.approx(37.3, abs=1.0)
    thick = SL.fin_analytic(SL.ALLOYS["6061-T6"], SL.T_DESIGN, 9.6)
    assert thick["R"] < 0.5 * f["R"]                            # the 1/8 in fin more than halves R_fin
    # alloy conductivity sensitivity is small compared with finish
    lo = SL.fin_analytic(SL.ALLOYS["5052-H32"], SL.T_AS_BUILT, 9.6)["R"]
    hi = SL.fin_analytic(SL.ALLOYS["6061-T6"], SL.T_AS_BUILT, 9.6)["R"]
    assert 1.0 < lo / hi < 1.15


def test_natural_convection_correlations_agree():
    for dT in (5.0, 10.0, 20.0):
        h_cc = SL.h_churchill_chu(dT, 0.2)[2]
        assert h_cc == pytest.approx(SL.h_simple(dT, 0.2), rel=0.1)


def test_quasi_1d_energy_balance():
    fd = SL.fin_quasi_1d(167.0, SL.T_AS_BUILT, 9.6, q_total=1.0)
    # all injected heat leaves through the convective faces
    import numpy as np
    w, _ = SL.width_profile(fd["z"])
    hz = np.where(fd["z"] <= SL.FIN["patch_top"], 0.0, np.where(fd["z"] <= SL.FIN["z_exit"], SL.H_INSIDE, 9.6))
    th_in = np.where((fd["z"] > SL.FIN["patch_top"]) & (fd["z"] <= SL.FIN["z_exit"]), SL.T_INSIDE_VENTED - SL.T_AMB, 0.0)
    q_out = float(np.sum(2 * hz * w * 1e-3 * 0.25e-3 * (fd["th"] - th_in)))
    assert q_out == pytest.approx(1.0, rel=0.01)


def test_step_measurements_if_available():
    m = SL.measure_step()
    if m is None:
        pytest.skip("cadquery or the assembly STEP is not available")
    assert len(m["wall_hole_yz"]) == 6
    assert m["motor_holes_xz"] == [(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]
    assert m["tab_back_y"] == [0.0] and m["tab_front_y"] == [5.0]
    assert m["pilot"][0][0] == pytest.approx(11.2)
    assert m["wall_back"][0] == pytest.approx(-42.31, abs=0.02)
