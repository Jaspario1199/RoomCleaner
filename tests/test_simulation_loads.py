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
    h_paint, _ = SL.converge_h(SL.ALLOYS["6061-T6"], SL.T_AS_BUILT, SL.EPS["black paint"], P)
    assert h_paint == pytest.approx(9.6, abs=0.1)
    h_bare, _ = SL.converge_h(SL.ALLOYS["6061-T6"], SL.T_AS_BUILT, SL.EPS["bare Al"], P)
    assert h_bare == pytest.approx(5.3, abs=0.1)
    f = SL.fin_analytic(SL.ALLOYS["6061-T6"], SL.T_AS_BUILT, h_paint)
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


# ---- numbers Jasper pastes into the manuals (review L5) ---------------------------------------------
def _rc(kind):
    A = SL.contact_area_mm2() * 1e-6
    return 1.0 / ({"paste": 1e4, "dry": 3e3}.get(kind, 736.0) * A)


@pytest.mark.parametrize("eps,t_mm,mode,expect", [
    (0.9, SL.T_AS_BUILT, "vented", 41.6), (0.9, SL.T_AS_BUILT, "sealed", 47.3),
    (0.1, SL.T_AS_BUILT, "vented", 43.2), (0.1, SL.T_AS_BUILT, "sealed", 49.7),
    (0.9, SL.T_DESIGN, "vented", 35.1), (0.9, SL.T_DESIGN, "sealed", 37.7)])
def test_coupled_motor_temperatures(eps, t_mm, mode, expect):
    cv = SL.coupled_converged(167.0, t_mm, eps, _rc("paste"), mode)
    assert cv["r"]["T_motor"] == pytest.approx(expect, abs=0.15)


def test_fin_heat_and_thermocouple_predictions():
    thin = SL.coupled_converged(167.0, SL.T_AS_BUILT, 0.9, _rc("paste"), "vented")
    thick = SL.coupled_converged(167.0, SL.T_DESIGN, 0.9, _rc("paste"), "vented")
    bare = SL.coupled_converged(167.0, SL.T_AS_BUILT, 0.1, _rc("paste"), "vented")
    assert thin["r"]["q_fin"] == pytest.approx(0.72, abs=0.02)
    assert thick["r"]["q_fin"] == pytest.approx(1.21, abs=0.02)
    assert thin["fd"]["at"](100.0) / thin["r"]["rise"] == pytest.approx(0.35, abs=0.01)
    assert bare["fd"]["at"](100.0) / bare["r"]["rise"] == pytest.approx(0.49, abs=0.01)
    assert thin["fd"]["at"](100.0) == pytest.approx(6.5, abs=0.2)


@pytest.mark.parametrize("t_mm,eps,h,patch,top,exit_,z100", [
    (SL.T_AS_BUILT, 0.9, 9.6, 50.2, 39.9, 35.6, 16.6), (SL.T_AS_BUILT, 0.1, 5.3, 62.4, 52.1, 47.8, 27.5),
    (SL.T_DESIGN, 0.9, 9.6, 19.3, 17.7, 17.0, 13.5), (SL.T_DESIGN, 0.1, 5.3, 28.7, 27.1, 26.5, 22.9)])
def test_quasi_1d_targets(t_mm, eps, h, patch, top, exit_, z100):
    P = SL.motor_heat()
    fd = SL.fin_quasi_1d(167.0, t_mm, h, q_total=P)
    assert fd["patch_avg"] == pytest.approx(patch, abs=0.3)
    assert fd["base"] == pytest.approx(top, abs=0.3)
    assert fd["exit"] == pytest.approx(exit_, abs=0.3)
    assert fd["at"](100.0) == pytest.approx(z100, abs=0.3)


def test_formula_is_referenced_to_the_shell_exit():
    P = SL.motor_heat()
    f = SL.fin_analytic(167.0, SL.T_AS_BUILT, 9.6)
    fd = SL.fin_quasi_1d(167.0, SL.T_AS_BUILT, 9.6, q_total=P)
    assert fd["exit"] == pytest.approx(P * f["R"], rel=0.06)       # z = 50 mm, 4 to 5 % below the formula
    assert fd["base"] - fd["exit"] == pytest.approx(4.3, abs=0.5)  # neck conduction, z = 42.15 vs 50


def test_p5_reaction_constants():
    assert SL.SELF_WEIGHT_N == pytest.approx(10.22, abs=0.02)
    assert SL.REMOTE_WEIGHT_N == pytest.approx(5.30, abs=0.01)
    t = SL.tension_cases()
    assert tuple(SL.expected_reaction(t["slip"] * SL.unit_vector(0, 0))) == pytest.approx((0, 0, 49.5), abs=0.05)
    r2 = SL.expected_reaction(t["slip"] * SL.unit_vector(43.9, 45))
    assert tuple(r2) == pytest.approx((-16.67, -16.67, 40.0), abs=0.05)
    r3 = SL.expected_reaction(t["slip"] * SL.unit_vector(78.7, 0))
    assert tuple(r3) == pytest.approx((-33.34, 0, 22.2), abs=0.05)


def test_fleet_limit_and_reachable_cases():
    assert SL.fleet_limit_deg() == pytest.approx(26.05, abs=0.05)
    t = SL.tension_cases()
    reach = {c[0]: c for c in SL.reachable_cases(t)}
    assert set(reach) == {"D1", "D2c", "D3", "D4f"}
    uc = reach["D2c"][2]
    assert tuple(uc) == pytest.approx((0.5054, 0.4392, -0.7429), abs=2e-3)
    assert reach["D2c"][3] == pytest.approx(37.85, abs=0.02)          # 34 / cos(26.05 deg)
    assert tuple(reach["D4f"][2]) == pytest.approx((0.8810, -0.4392, -0.1760), abs=1e-3)
    # the in-plane share that turns the drum is the slip-limit share
    for cid in ("D2c", "D4f"):
        T, u = reach[cid][3], reach[cid][2]
        assert T * math.hypot(u[0], u[2]) == pytest.approx(t["slip"], abs=0.02)


@pytest.mark.parametrize("case,load_pt,along", [("D1", 0.22, 0.22), ("D2", 0.19, 0.17), ("D3", 0.28, 0.23), ("D4", 0.43, 0.33)])
def test_tab_displacement_hand_column(case, load_pt, along):
    t = SL.tension_cases()
    row = [c for c in SL.CASES if c[0] == case][0]
    u = SL.unit_vector(row[2], row[3])
    d = SL.tab_displacement(t["slip"] * u, SL.tangent_point(u))
    assert d["load_point_total"] == pytest.approx(load_pt, abs=0.01)
    assert d["load_point_along"] == pytest.approx(along, abs=0.01)


@pytest.mark.parametrize("case,ten,shear", [("D1", 11.2, 8.4), ("D2", 17.5, 7.9), ("D3", 9.1, 4.1), ("D4", 18.6, 7.9)])
def test_screw_hand_column(case, ten, shear):
    import numpy as np
    t = SL.tension_cases()
    row = [c for c in SL.CASES if c[0] == case][0]
    u = SL.unit_vector(row[2], row[3])
    p = SL.tangent_point(u)
    F = t["slip"] * u
    C = np.array([SL.WALL_X, float(np.mean(SL.SCREW_COLS_Y)), float(np.mean(SL.SCREW_ROWS_Z))])
    Mc = np.cross(p - C, F) + np.cross(SL.P_MOTOR - C, [0, 0, -(SL.M_MOTOR + 0.01) * SL.G]) \
        + np.cross(SL.P_SHELL - C, [0, 0, -SL.M_SHELL * SL.G])
    Ftot = F + np.array([0.0, 0.0, -(SL.REMOTE_WEIGHT_N + SL.SELF_WEIGHT_N)])
    sg = SL.screw_group_estimate(Ftot, Mc)
    assert sg["t_top"] == pytest.approx(ten, abs=0.2)
    assert sg["shear"] == pytest.approx(shear, abs=0.2)


# ---- repair round 2: the governing-case numbers Jasper compares against ----------------------------
def _reach_case(cid):
    t = SL.tension_cases()
    c = {r[0]: r for r in SL.reachable_cases(t)}[cid]
    return c[3] * c[2], c[4]          # force (N), load point (mm)


@pytest.mark.parametrize("cid,gauge_max,gauge_mean,load_pt", [
    ("D1", 0.22, 0.13, 0.22), ("D2c", 0.22, 0.12, 0.21), ("D3", 0.41, 0.19, 0.28), ("D4f", 0.54, 0.27, 0.40)])
def test_s3_gauge_and_load_point_for_reachable_cases(cid, gauge_max, gauge_mean, load_pt):
    F, p = _reach_case(cid)
    d = SL.tab_displacement(F, p)
    assert d["holes_max"] == pytest.approx(gauge_max, abs=0.01)
    assert d["holes_mean"] == pytest.approx(gauge_mean, abs=0.01)
    assert d["load_point_total"] == pytest.approx(load_pt, abs=0.01)


def test_exit_estimate_uses_components_not_urres_sum():
    """Manual section 6.1: D4f's gauge is above 0.50 mm, so the exit-estimate branch decides P4. Adding the URES
    mean to a rotation x lever term (the round 1 recipe) gives a false FAIL (0.53); the component recipe gives 0.38
    against a true load-point displacement of 0.40."""
    F, p = _reach_case("D4f")
    e = SL.tab_exit_estimate(F, p)
    assert e["lever"] == pytest.approx(15.5)                    # drum plane 18.0 - tab mid-plane 2.5, NOT 18
    assert e["gauge_max"] > 0.50
    assert e["load_point_total"] == pytest.approx(0.40, abs=0.01)
    assert e["total"] == pytest.approx(0.38, abs=0.01)
    assert e["total"] < 0.50 < e["naive_sum"]
    assert e["naive_sum"] == pytest.approx(0.53, abs=0.01)
    # the recipe reads at most ~7 % below the true value on D4f and never above it on these cases
    assert 0.90 * e["load_point_total"] < e["total"] <= e["load_point_total"] + 1e-6
    F3, p3 = _reach_case("D3")
    e3 = SL.tab_exit_estimate(F3, p3)
    assert e3["total"] == pytest.approx(0.27, abs=0.01)
    F1, p1 = _reach_case("D1")
    assert SL.tab_exit_estimate(F1, p1)["total"] == pytest.approx(0.13, abs=0.01)    # under-reads the torsion case (0.22)


@pytest.mark.parametrize("cid,ten,shear", [("D2c", 18.8, 8.4), ("D4f", 15.7, 4.8)])
def test_screw_hand_column_new_reachable_cases(cid, ten, shear):
    import numpy as np
    F, p = _reach_case(cid)
    C = np.array([SL.WALL_X, float(np.mean(SL.SCREW_COLS_Y)), float(np.mean(SL.SCREW_ROWS_Z))])
    Mc = np.cross(p - C, F) + np.cross(SL.P_MOTOR - C, [0, 0, -(SL.M_MOTOR + 0.01) * SL.G]) \
        + np.cross(SL.P_SHELL - C, [0, 0, -SL.M_SHELL * SL.G])
    Ftot = F + np.array([0.0, 0.0, -(SL.REMOTE_WEIGHT_N + SL.SELF_WEIGHT_N)])
    sg = SL.screw_group_estimate(Ftot, Mc)
    assert sg["t_top"] == pytest.approx(ten, abs=0.2)
    assert sg["shear"] == pytest.approx(shear, abs=0.2)


def test_p5_reactions_for_the_fleet_limited_cases():
    assert tuple(SL.expected_reaction(_reach_case("D2c")[0])) == pytest.approx((-19.13, -16.62, 43.62), abs=0.05)
    assert tuple(SL.expected_reaction(_reach_case("D4f")[0])) == pytest.approx((-33.34, 16.62, 22.18), abs=0.05)


# ---- repair round 2: isothermal flange versus uniform flux (the B-2 ranges and the hold-test window) ---
@pytest.mark.parametrize("eps,t_mm,mode,uni,iso", [
    (0.9, SL.T_AS_BUILT, "vented", 41.6, 40.2), (0.9, SL.T_AS_BUILT, "sealed", 47.3, 45.1),
    (0.1, SL.T_AS_BUILT, "vented", 43.2, 42.2), (0.9, SL.T_DESIGN, "vented", 35.1, 34.6)])
def test_isothermal_flange_motor_temperature_range(eps, t_mm, mode, uni, iso):
    a = SL.coupled_converged(167.0, t_mm, eps, _rc("paste"), mode)
    b = SL.coupled_converged(167.0, t_mm, eps, _rc("paste"), mode, isothermal=True)
    assert a["r"]["T_motor"] == pytest.approx(uni, abs=0.15)
    assert b["r"]["T_motor"] == pytest.approx(iso, abs=0.15)
    assert b["r"]["T_motor"] < a["r"]["T_motor"]                 # the isothermal flange is the cooler end
    assert b["r"]["q_fin"] > a["r"]["q_fin"]


def test_b2_prediction_ranges_and_the_finish_test_window():
    """Section 5 / 8: uniform flux -> isothermal flange. The painted and bare TC2 ranges must stay apart so the
    8 K / 9.5 K thresholds (undecided between) separate them; the TC2/TC1 ratios are only ~0.06 apart."""
    pa = SL.coupled_converged(167.0, SL.T_AS_BUILT, 0.9, _rc("paste"), "vented")
    pb = SL.coupled_converged(167.0, SL.T_AS_BUILT, 0.9, _rc("paste"), "vented", isothermal=True)
    ba = SL.coupled_converged(167.0, SL.T_AS_BUILT, 0.1, _rc("paste"), "vented")
    bb = SL.coupled_converged(167.0, SL.T_AS_BUILT, 0.1, _rc("paste"), "vented", isothermal=True)
    z = lambda c: c["fd"]["at"](100.0)
    assert (z(pa), z(pb)) == pytest.approx((6.5, 7.4), abs=0.15)
    assert (z(ba), z(bb)) == pytest.approx((9.9, 10.9), abs=0.15)
    assert z(pb) < 8.0 < 9.5 < z(ba)                              # thresholds sit in the gap
    assert (pa["r"]["q_fin"], pb["r"]["q_fin"]) == pytest.approx((0.72, 0.82), abs=0.02)
    assert (pa["fd"]["base"], pb["fd"]["base"]) == pytest.approx((14.9, 17.0), abs=0.3)
    assert (pa["fd"]["tip"], pb["fd"]["tip"]) == pytest.approx((1.46, 1.64), abs=0.1)
    ratio = lambda c: z(c) / c["r"]["rise"]
    assert (ratio(pa), ratio(pb)) == pytest.approx((0.35, 0.43), abs=0.01)
    assert (ratio(ba), ratio(bb)) == pytest.approx((0.49, 0.57), abs=0.01)
    assert ratio(bb) - ratio(pb) < 0.15 and ratio(pb) > 0.42       # a +/-0.07 window around 0.35 would reject the painted fin


def test_b1_targets_do_not_depend_on_how_the_heat_enters():
    """The formula reference (z = 50 mm), z = 42 mm and the tip are identical for a uniform flux and an isothermal
    patch; only the patch average moves (50.2 K -> about 40 K painted), which the manual says in section 0."""
    P = SL.motor_heat()
    u = SL.fin_quasi_1d(167.0, SL.T_AS_BUILT, 9.6, q_total=P)
    i = SL.fin_quasi_1d(167.0, SL.T_AS_BUILT, 9.6, q_total=P, isothermal=True)
    assert i["exit"] == pytest.approx(u["exit"], abs=0.05)
    assert i["tip"] == pytest.approx(u["tip"], abs=0.02)
    assert i["base"] == pytest.approx(u["base"], abs=0.05)
    assert i["patch_avg"] == pytest.approx(40.1, abs=0.3)
    assert u["patch_avg"] == pytest.approx(50.2, abs=0.3)
