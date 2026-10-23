"""Winch station with the 3:1 spur reduction (D40): what it lifts, what it can pull before the motor slips, and whether each
part of the new drive train outlasts the motor.

Drive train: `cad/WINCH_GEAR3_SPEC.md`, parameters `cad/params.py` WG3_* (built by `cad/parts/winch_gear3.py`). Motor, spool
radii, running fraction, skip margin and the tension-per-weight factor are the repo's (simulation_loads, D37, Lift budget).
Rule from D39: every link >= 1.5 x the most the motor can pull before it slips (`lift_chain_weakest_link.py` = WL).

Revised 10/23 after the independent check (verification/winch_gear3_calc_check.md, F1 to F12) with the lead's decisions:
capacity as a range (A4988 full-step vector); wall screws at the new load point; shaft and bearings over the whole drum width
plus the axial thrust; printed teeth on the spool-side force with a failure basis (in-plane UTS, Kf, thinning) and a Hertz
check; set-screw friction range for a steel hub; tracking tolerance 60 counts with an error budget; efficiency sensitivity;
motor-shaft static checks; spool body and tie-off.

Tags: [REPO] recorded in the repo, [ASSUMED] to be replaced by a measurement, [SRC] published value. Units N, mm, MPa, N.m.

    PYTHONPATH=. /usr/bin/python3 -m calculations.winch_gear3
Writes calculations/winch_gear3.json.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from cad import params as P
from calculations import simulation_loads as S
from calculations import lift_chain_weakest_link as WL
from roomcleaner.cdpr.config import EncoderConfig

OUT_JSON = Path(__file__).with_suffix(".json")
CFG = json.loads((S.ROOT / "config" / "robot.sim.json").read_text())
G = S.G                               # 9.81 m/s2 [REPO]
N_RATIO = P.WG3_RATIO                 # 3.0 [REPO WG3]
ETA = 0.90                            # printed spur stage efficiency, each direction [ASSUMED; the pull test measures the net]
ETAS = (0.70, 0.80, 0.90, 0.95, 1.00)  # sensitivity range [ASSUMED]
K_TENSION = WL.K_TENSION              # worst tension per unit weight, +2 m/s2 included [REPO Lift budget, via WL]
NEEDED_KG = WL.NEEDED_KG              # claw 0.60 + jeans 0.90 [REPO Lift budget, via WL]
R_SENSE = S.R_SENSE                   # 0.100 ohm, red R100 A4988 [REPO D29/D30]
CURRENTS = (1.0, 1.5)                 # A: recommended (D40) and today's setting (D37)
MOTOR_FULL_STEPS = 200                # full steps per motor turn [REPO NEMA 17, 1.8 deg]
Y_LEWIS = {20: 0.320, 60: 0.422}      # Lewis form factors, 20 deg full depth [SRC standard table]
PETG_ALLOW = S.Z_STRENGTH * WL.WARM["design"]   # MPa: Lewis allowable = half the in-plane UTS, warm [REPO review R5, D39; warm ASSUMED in WL]
PETG_UTS = S.PETG["uts"]              # MPa, in-plane tensile strength; Z_STRENGTH is half of it [REPO SIMULATION_GUIDE.md via S]
KF_ROOT = 1.8                         # root fillet stress concentration of a printed tooth [ASSUMED, 1.5 to 2.0]
PETG_COMPRESSIVE = 50.0               # MPa, PETG compressive strength [ASSUMED typical, not in the repo]
STEEL_E, STEEL_NU = 200000.0, 0.30    # MPa, steel pinion [SRC handbook]
STEEL_ALLOW = 150.0                   # MPa, bending allowable of a carbon-steel pinion (UTS >= 450 / 3); sintered or brass is lower [ASSUMED]
MU_STEEL_HUB = (0.10, 0.15, 0.20)     # tip and bore friction, steel set screw / steel shaft in a steel hub, dry to oiled [ASSUMED]
C0_687 = 600.0                        # N, static rating of a 687 (7 x 14 x 5) bearing [ASSUMED, check the datasheet]
SHAFT_SY = 350.0                      # MPa, Ø7 dowel (hardened dowels are much higher) [ASSUMED; same value as WL.SHAFT_SY[0], other part]
MOTOR_RADIAL_N = WL.RADIAL_RATING     # N at 20 mm from the face, 17HS4401 listing [SRC, via WL; check Jasper's motor]
MOTOR_RADIAL_ARM = 20.0               # mm, where that rating applies [SRC, via WL]
SKIP_FULL_STEPS = 4                   # a stepper loses steps in whole electrical cycles [REPO WL.detection]
CPR = EncoderConfig().counts_per_rev  # AS5600 counts per revolution [REPO roomcleaner/cdpr/config.py]
LINE_SPEED = CFG["motion"]["max_cable_speed_m_s"]   # m/s [REPO config/robot.sim.json max_cable_speed_m_s]
TRACKING_TOL = CFG["faults"]["tracking_tol_counts"]  # counts [REPO config/robot.sim.json faults.tracking_tol_counts]
TRACKING_DWELL = CFG["faults"]["tracking_dwell_s"]   # s [REPO config/robot.sim.json faults.tracking_dwell_s]
ROTOR_LAG_STEPS = 1.0                 # full steps of rotor lag before pull-out [ASSUMED]
AS5600_INL_DEG = (0.5, 1.0)           # deg, sensor nonlinearity as mounted [ASSUMED range from the independent check; datasheet from memory]
WALL_SCAN_POINTS = 33                 # cable positions across the drum width for the wall-screw scan
assert math.isclose(S.Z_STRENGTH, 0.5 * PETG_UTS)   # the half-UTS allowable and the failure basis come from the same 45 MPa


def at_current(i_amp: float, eta: float = ETA) -> dict:
    hold = S.hold_torque(i_amp)                                      # motor holding torque, N.m (36 N.cm at 1.5 A basis)
    hold_hi = hold * WL.MOTOR_SENS                                   # 40 N.cm motor
    run_full = S.RUN_FRAC * hold * N_RATIO * eta / S.R_FULL          # running pull at a full spool, N (0.7 was set at 64 rpm, carried to 191 rpm unverified)
    design = run_full / S.SKIP_SF
    cap = design / (K_TENSION * G)
    fuse_low = hold * WL.VECTOR_LOW * N_RATIO / S.R_EMPTY            # straight cable, no friction help
    fuse_up = hold_hi * N_RATIO / eta / S.R_EMPTY * WL.FLEET_K       # back-driven through the stage, fleeted cable
    return dict(i=i_amp, vref=8 * i_amp * R_SENSE, hold=hold, hold_hi=hold_hi, run_full=run_full, run_core=run_full * S.R_FULL / S.R_EMPTY,
                design=design, capacity_kg=cap, capacity_low_kg=cap * WL.VECTOR_LOW,
                margin=(cap - NEEDED_KG) / NEEDED_KG, margin_low=(cap * WL.VECTOR_LOW - NEEDED_KG) / NEEDED_KG,
                fuse_low=fuse_low, fuse_up=fuse_up, need=WL.PASS_RATIO * fuse_up, heat=S.motor_heat(i_amp))


def direct_drive() -> dict:
    """Today's direct-drive winch at 1.5 A on the same basis: working force / (tension factor x g); low = full-step vector."""
    cap = WL.DESIGN_FORCE / (K_TENSION * G)
    return dict(capacity_kg=cap, capacity_low_kg=cap * WL.VECTOR_LOW, margin=(cap - NEEDED_KG) / NEEDED_KG,
                margin_low=(cap * WL.VECTOR_LOW - NEEDED_KG) / NEEDED_KG, fuse_low=WL.FUSE["slip_low"], fuse_up=WL.FUSE["upper"],
                need=WL.PASS_RATIO * WL.FUSE["upper"], heat=S.motor_heat(WL.I_SET))


def gear_teeth(c: dict) -> dict:
    """Printed 60T teeth at the most torque the motor puts through the stage (it slips above that), on the spool-side tangential
    force (back-driven: slip torque x ratio / eta / gear pitch radius), the same force the shaft check uses.
    (a) Lewis SF against the half-UTS allowable. (b) the D39 ratio on a failure basis: the teeth print flat, so they bend along
    the layers (in-plane UTS, warm), root stress x Kf and x the thinning of the root section (t / (t - thin))^2 [approximation:
    the tooth thickness t = pi m / 2 loses the 0.10 mm of printed-gear thinning, the root section is taken to lose the same]."""
    r_p = P.WG3_MODULE * P.WG3_Z_PINION / 2.0 * 1e-3
    r_g = P.WG3_MODULE * P.WG3_Z_GEAR / 2.0 * 1e-3
    f_t = c["hold_hi"] * N_RATIO / ETA / r_g
    t_tooth = math.pi * P.WG3_MODULE / 2.0
    thin = (t_tooth / (t_tooth - P.WG3_GEAR_TOOTH_THIN)) ** 2
    sig = f_t / (P.WG3_FACE * P.WG3_MODULE * Y_LEWIS[P.WG3_Z_GEAR])
    sig_root = sig * KF_ROOT * thin
    allow_fail = PETG_UTS * WL.WARM["design"]
    sig_pin = f_t / (P.WG3_FACE * P.WG3_MODULE * Y_LEWIS[P.WG3_Z_PINION])
    return dict(f_t=f_t, f_t_pinion_side=c["hold_hi"] / r_p, f_r=f_t * math.tan(math.radians(P.WG3_PRESSURE_ANGLE_DEG)),
                sigma_gear=sig, allow=PETG_ALLOW, sf=PETG_ALLOW / sig, kf=KF_ROOT, thin_factor=thin, sigma_root=sig_root,
                allow_fail=allow_fail, ratio=allow_fail / sig_root,
                pinion_sigma=sig_pin, pinion_allow=STEEL_ALLOW, pinion_util=sig_pin / STEEL_ALLOW)


def hertz(t: dict) -> dict:
    """Steel pinion on the printed gear at the pitch point (line contact, nominal 20 deg, 40.0 mm centres): p_max against a warm
    compressive strength. p goes with sqrt(F), so the force ratio is (allow / p)^2."""
    phi = math.radians(P.WG3_PRESSURE_ANGLE_DEG)
    r_p, r_g = P.WG3_MODULE * P.WG3_Z_PINION / 2.0, P.WG3_MODULE * P.WG3_Z_GEAR / 2.0
    rho = 1.0 / (1.0 / (r_p * math.sin(phi)) + 1.0 / (r_g * math.sin(phi)))     # relative radius of curvature, mm
    e_star = 1.0 / ((1 - STEEL_NU ** 2) / STEEL_E + (1 - S.PETG["nu"] ** 2) / S.PETG["E"])
    f_n = t["f_t"] / math.cos(phi)
    p = math.sqrt(f_n / P.WG3_FACE * e_star / (math.pi * rho))
    allow = PETG_COMPRESSIVE * WL.WARM["design"]
    return dict(f_n=f_n, rho=rho, e_star=e_star, p_max=p, allow=allow, ratio=(allow / p) ** 2)


def pinion_setscrew(c: dict) -> dict:
    """The purchased pinion's M3 set screw in a steel hub on the steel D-flat: WL.setscrew_joint's structure (lever = mu_tip r_flat +
    mu_bore r_bore, seat force from 3 to 4 in-lb, cup bite), with steel-hub friction mu_tip = mu_bore over MU_STEEL_HUB."""
    ss = WL.setscrew_joint()
    r_flat, r_bore = ss["r_flat"], WL.SHAFT_D / 2
    torque = lambda f, mu: WL.CUP_BITE * f * (mu * r_flat + mu * r_bore) * 1e-3
    by_mu = {f"{mu:.2f}": dict(torque_lo=torque(ss["f_seat_steel"][0], mu), torque_hi=torque(ss["f_seat_steel"][1], mu),
                               ratio_lo=torque(ss["f_seat_steel"][0], mu) / c["hold_hi"], ratio_hi=torque(ss["f_seat_steel"][1], mu) / c["hold_hi"])
             for mu in MU_STEEL_HUB}
    lo, hi = by_mu[f"{min(MU_STEEL_HUB):.2f}"], by_mu[f"{max(MU_STEEL_HUB):.2f}"]
    assert math.isclose(WL.MU_TIP * r_flat + WL.MU_BORE * r_bore, ss["lever_mm"])      # same lever model as WL
    wl_t = WL.CUP_BITE * ss["f_seat_steel"][0] * ss["lever_mm"] * 1e-3                 # WL's own friction (PETG-bore 0.25), the old basis
    return dict(by_mu=by_mu, torque_lo=lo["torque_lo"], torque_hi=hi["torque_hi"], ratio_lo=lo["ratio_lo"], ratio_hi=hi["ratio_hi"],
                ratio_wl_friction=wl_t / c["hold_hi"])


def spool_shaft(c: dict) -> dict:
    """Ø7 shaft on two 687 bearings (centres y 2.5 and 46.5), simply supported. Loads at the motor's upper slip force: the cable
    (full magnitude, radial, anywhere across the drum width, any reachable in-plane direction 0 to 84 deg from straight down) and
    the mesh force at the gear mid-face (radial toward the spool axis, tangential set by the torque balance, so on the -x side).
    Envelope reactions, the largest bending moment, and the axial thrust of the fleeted line. The shaft carries no torque."""
    y_a, y_b = P.WG3_BRG_NEAR_Y0 + P.WG3_BRG_W / 2, P.WG3_BRG_FAR_Y0 + P.WG3_BRG_W / 2
    span = y_b - y_a
    y_m = (P.WG3_Y_TEETH0 + P.WG3_Y_TEETH1) / 2                      # mesh at the gear mid-face
    r_gear = P.WG3_MODULE * P.WG3_Z_GEAR / 2.0 * 1e-3
    f_t = c["hold_hi"] * N_RATIO / ETA / r_gear                      # back-driven: the gear pushes the pinion at the slip torque
    f_r = f_t * math.tan(math.radians(P.WG3_PRESSURE_ANGLE_DEG))

    def solve(y_c: float, theta_deg: float) -> tuple[float, float, float]:
        th = math.radians(theta_deg)
        loads = [(y_c, c["fuse_up"] * np.array([math.sin(th), -math.cos(th)])), (y_m, np.array([-f_t, -f_r]))]    # (x, z) forces
        rb = sum(f * (y - y_a) for y, f in loads) / span
        ra = sum(f for _, f in loads) - rb
        m = max(np.linalg.norm(ra * (y - y_a) - sum(f * (y - yf) for yf, f in loads if yf < y)) for y, _ in loads)
        return float(np.linalg.norm(ra)), float(np.linalg.norm(rb)), float(m)

    worst = {k: (0.0, 0.0, 0.0) for k in ("near", "far", "moment")}          # value, cable y, direction
    for y_c in np.linspace(P.WG3_Y_TEETH1, P.WG3_Y_DRUM1, 17):
        for th in np.arange(0.0, 84.1, 6.0):
            for k, v in zip(("near", "far", "moment"), solve(float(y_c), float(th))):
                if v > worst[k][0]:
                    worst[k] = (v, float(y_c), float(th))
    r_near, r_far, m = worst["near"][0], worst["far"][0], worst["moment"][0]
    mid = solve((P.WG3_Y_TEETH1 + P.WG3_Y_DRUM1) / 2, 0.0)                   # the old case: straight down at the drum mid-plane
    axial = c["fuse_up"] * math.sin(math.radians(WL.FLEET_DEG))
    p0 = max(r_far, 0.6 * r_far + 0.5 * axial)                               # equivalent static load of the worse bearing, all thrust on it
    sigma = 32 * m / (math.pi * P.WG3_SHAFT_D ** 3)
    return dict(span=span, mesh_t=f_t, mesh_r=f_r, moment=m, sigma=sigma, ratio=SHAFT_SY / sigma, r_near=r_near, r_far=r_far,
                worst_near=dict(y=worst["near"][1], theta=worst["near"][2]), worst_far=dict(y=worst["far"][1], theta=worst["far"][2]),
                worst_moment=dict(y=worst["moment"][1], theta=worst["moment"][2]), midplane=dict(r_near=mid[0], r_far=mid[1], moment=mid[2]),
                axial=axial, p0=p0, brg_ratio=C0_687 / p0, seat_near_need=WL.PASS_RATIO * r_near, seat_far_need=WL.PASS_RATIO * r_far,
                seat_axial_need=WL.PASS_RATIO * axial)


def spool_body(c: dict) -> dict:
    """Torque path through the printed spool (gear teeth to the drum core): shear at the core at the spool-side slip torque, ignoring
    the shaft (press fit) and the web windows (not checked)."""
    t_spool = c["hold_hi"] * N_RATIO / ETA
    j = math.pi / 32 * (P.WG3_DRUM_D ** 4 - P.WG3_BORE_D ** 4)
    tau = t_spool * 1e3 * P.WG3_DRUM_D / 2 / j
    allow = WL.PETG_SHEAR[0] * WL.WARM["design"]
    return dict(torque=t_spool, j=j, tau=tau, allow=allow, ratio=allow / tau)


def tieoff(c: dict, wl: dict) -> dict:
    """Load at the spool tie-off (Ø1.4 chord hole): with WL.DEAD_WRAPS dead wraps the capstan share of the line tension, without all of it."""
    share = wl["line"]["tieoff_share_with_wraps"]
    return dict(wraps=WL.DEAD_WRAPS, share=share, with_wraps=[s * c["fuse_up"] for s in share], without=c["fuse_up"],
                ligament_bore=P.WG3_TIEOFF_OFFSET - P.WG3_TIEOFF_D / 2 - P.WG3_BORE_D / 2,
                ligament_core=P.WG3_DRUM_D / 2 - (P.WG3_TIEOFF_OFFSET + P.WG3_TIEOFF_D / 2))


def motor_shaft(c: dict, wl: dict) -> dict:
    """The pinion's mesh force on the motor shaft, at the pinion mid-face, against the 17HS catalogue limit (a bearing-life rating, not a
    strength) and the static checks with WL's D-flat section modulus and front bearing (3 mm behind the face, 30 mm span, C0)."""
    r_p = P.WG3_MODULE * P.WG3_Z_PINION / 2.0 * 1e-3
    k = 1 / math.cos(math.radians(P.WG3_PRESSURE_ANGLE_DEG))         # resultant of tangential and radial
    t_run = NEEDED_KG * K_TENSION * G * S.R_FULL / (N_RATIO * ETA)    # motor torque, N.m
    arm = (P.WG3_Y_TEETH0 + P.WG3_Y_TEETH1) / 2 - P.WG3_Y_MOTOR_FRONT
    f_slip = c["hold_hi"] / r_p * k
    lever = arm + WL.BRG_IN                                          # mesh to the front bearing
    sigma = f_slip * lever / wl["shaft"]["Z"]
    brg = f_slip * (lever + WL.BRG_SPAN) / WL.BRG_SPAN
    return dict(arm_mm=arm, f_slip=f_slip, f_run=t_run / r_p * k, catalogue=MOTOR_RADIAL_N, catalogue_arm=MOTOR_RADIAL_ARM,
                slip_vs_catalogue=f_slip / MOTOR_RADIAL_N, run_vs_catalogue=t_run / r_p * k / MOTOR_RADIAL_N,
                lever=lever, z=wl["shaft"]["Z"], sigma=sigma, shaft_ratio=WL.SHAFT_SY[0] / sigma, brg_reaction=brg, brg_c0=WL.BRG_C0,
                brg_ratio=WL.BRG_C0 / brg)


def wall_screws(wl: dict) -> dict:
    """Wall-screw links at the NEW load point: the line leaves the r = R_EMPTY tangent point of the spool, whose axis is WG3_CD below the
    motor axis, anywhere across the drum width (y from the gear face to the drum end). WL's one-stud-column model, solved unchanged;
    the minimum over the four reachable cases and the cable positions. Spool and gear weight (about 0.05 kg) not added."""
    w = WL.withdrawal("#6", "spruce-pine-fir")
    punch = wl["wall"]["head_punch"]
    ys = np.linspace(P.WG3_Y_TEETH1, P.WG3_Y_DRUM1, WALL_SCAN_POINTS)
    out = {}
    for name, target in (("withdrawal", w["design"]), ("head_punch", punch)):
        best = None
        for cid, _, u, _, _ in S.reachable_cases(WL.T15):
            for y in ys:
                p = S.tangent_point(u, S.R_EMPTY * 1e3)
                p[1], p[2] = y, p[2] - P.WG3_CD
                f = WL.solve_line_force(WL.screws_one_column, u, p, target)
                if best is None or f < best["f"]:
                    best = dict(f=f, case=cid, y=float(y))
        out[name] = best
    old = wl["wall"]["per_case"][wl["wall"]["worst"]]["f_design_one"]
    return dict(withdrawal_design=w["design"], head_punch_per_screw=punch, withdrawal=out["withdrawal"], head_punch=out["head_punch"],
                wl_old=dict(case=wl["wall"]["worst"], f=old))


def encoder(sp: dict) -> dict:
    """Counts are at the spool: one count is the same line length geared or direct. Tolerance and its error budget."""
    r_core = S.R_EMPTY * 1e3
    count_mm = 2 * math.pi * r_core / CPR                                      # line per count at the core
    full_step = CPR / (MOTOR_FULL_STEPS * N_RATIO)                             # counts per full motor step, at the spool
    skip_counts = SKIP_FULL_STEPS * full_step
    r_gear = P.WG3_MODULE * P.WG3_Z_GEAR / 2.0
    backlash_mm = (2 * P.WG3_CD_ALLOW * math.tan(math.radians(P.WG3_PRESSURE_ANGLE_DEG))
                   + P.WG3_GEAR_TOOTH_THIN - P.WG3_PINION_TOOTH_THIN)          # at the pitch circle
    backlash_counts = backlash_mm / r_gear / (2 * math.pi) * CPR
    inl = [d / 360.0 * CPR for d in AS5600_INL_DEG]
    budget = [("Command quantisation (one full step)", full_step, full_step),
              ("Rotor lag before pull-out (up to one full step)", ROTOR_LAG_STEPS * full_step, ROTOR_LAG_STEPS * full_step),
              ("Gear backlash after a reversal", backlash_counts, backlash_counts),
              ("AS5600 nonlinearity as mounted", inl[0], inl[1])]
    lo, hi = sum(b[1] for b in budget), sum(b[2] for b in budget)
    n_trip = math.ceil(TRACKING_TOL / skip_counts)                             # skips of a continuous slip until the error exceeds the tolerance
    return dict(skip_deg=SKIP_FULL_STEPS * 360.0 / MOTOR_FULL_STEPS / N_RATIO, skip_counts=skip_counts, full_step_counts=full_step,
                skip_counts_direct=SKIP_FULL_STEPS * CPR / MOTOR_FULL_STEPS,
                backlash_mm=backlash_mm, backlash_counts=backlash_counts, tol=TRACKING_TOL, dwell_s=TRACKING_DWELL, count_mm=count_mm,
                tol_mm=TRACKING_TOL * count_mm, skip_mm=skip_counts * count_mm, two_skips_mm=2 * skip_counts * count_mm,
                trip_skips=n_trip, trip_steps=n_trip * SKIP_FULL_STEPS, trip_mm=n_trip * SKIP_FULL_STEPS * sp["mm_per_step_core"],
                trip_ms=n_trip * SKIP_FULL_STEPS / sp["rate_core"] * 1e3,
                budget=[dict(item=b[0], lo=b[1], hi=b[2]) for b in budget], budget_lo=lo, budget_hi=hi,
                margin_lo=TRACKING_TOL / hi, margin_hi=TRACKING_TOL / lo, headroom=TRACKING_TOL - hi)


def speed() -> dict:
    steps_per_rev = int(round(MOTOR_FULL_STEPS * N_RATIO))
    rev_s_core = LINE_SPEED / (2 * math.pi * S.R_EMPTY)                        # spool turns per second at the core
    return dict(full_steps_per_rev=steps_per_rev, rate_core=rev_s_core * steps_per_rev,
                rate_full=LINE_SPEED / (2 * math.pi * S.R_FULL) * steps_per_rev, motor_rpm=rev_s_core * N_RATIO * 60,
                motor_rpm_direct=rev_s_core * 60, mm_per_step_core=2 * math.pi * S.R_EMPTY * 1e3 / steps_per_rev,
                mm_per_step_direct=2 * math.pi * S.R_EMPTY * 1e3 / MOTOR_FULL_STEPS)


def eta_table(wl: dict) -> dict:
    """Efficiency sensitivity at 1.0 A: capacity (nominal), fuse upper, knot ratio; and the efficiency below which the knot fails 1.5."""
    knot = wl["line"]["knot_lower"]
    rows = []
    for e in ETAS:
        c = at_current(CURRENTS[0], e)
        rows.append(dict(eta=e, capacity_kg=c["capacity_kg"], capacity_low_kg=c["capacity_low_kg"], fuse_up=c["fuse_up"], knot_ratio=knot / c["fuse_up"]))
    fuse_up_lossless = at_current(CURRENTS[0], 1.0)["fuse_up"]
    return dict(rows=rows, eta_knot_min=WL.PASS_RATIO * fuse_up_lossless / knot)


def link_rows(c: dict, wl: dict, parts: dict) -> list:
    t, h, pin, s, body, m, wall = (parts[k] for k in ("teeth", "hertz", "setscrew", "shaft", "body", "motor", "wall"))
    fu = c["fuse_up"]
    rows = []

    def add(name: str, load: str, lo: float, hi: float | None = None) -> None:
        rows.append(dict(link=name, load=load, ratio=lo, ratio_hi=hi, verdict=WL.verdict(lo, hi)))

    add("Printed 60T teeth (UTS, Kf, thinning)", f"F_t {t['f_t']:.1f} N, {t['sigma_root']:.1f} MPa vs {t['allow_fail']:.2f}", t["ratio"])
    add("Tooth contact, steel on PETG (Hertz)", f"p {h['p_max']:.1f} MPa vs {h['allow']:.1f}", h["ratio"])
    add("Pinion set screw, steel on steel D-flat", f"{pin['torque_lo']:.2f} to {pin['torque_hi']:.2f} N.m vs {c['hold_hi']:.2f}", pin["ratio_lo"], pin["ratio_hi"])
    add("Spool body, drum core torque", f"{body['torque']:.2f} N.m, {body['tau']:.1f} MPa vs {body['allow']:.1f}", body["ratio"])
    add("Spool shaft Ø7, bending", f"{s['moment']:.0f} N.mm, {s['sigma']:.1f} MPa", s["ratio"])
    add("687 bearings, static", f"{s['r_near']:.1f} N near, {s['r_far']:.1f} N far", s["brg_ratio"])
    add("Motor shaft, bending at the D-flat", f"{m['f_slip']:.1f} N at {m['lever']:.0f} mm, {m['sigma']:.1f} MPa", m["shaft_ratio"])
    add("Motor front bearing, static", f"{m['brg_reaction']:.0f} N vs C0 {m['brg_c0']:.0f}", m["brg_ratio"])
    add("Line knot", f"{wl['line']['knot_lower']:.1f} N vs {fu:.1f}", wl["line"]["knot_lower"] / fu)
    add("Wall screws, one stud column", f"{wall['withdrawal']['f']:.0f} N of line puts the top screw at design withdrawal ({wall['withdrawal']['case']}, cable y {wall['withdrawal']['y']:.1f})", wall["withdrawal"]["f"] / fu)
    add("Wall plate, screw head pulls through", f"{wall['head_punch_per_screw']:.0f} N per screw at {wall['head_punch']['f']:.0f} N of line ({wall['head_punch']['case']}, cable y {wall['head_punch']['y']:.1f})",
        wall["head_punch"]["f"] / fu)
    add("Claw cable eye", f"{wl['line']['claw_eye']:.0f} N", wl["line"]["claw_eye"] / fu)
    add("Slide-in dovetails", f"{wl['retention']['f_line']:.0f} N (WL value scaled by tension)", wl["retention"]["f_line"] / fu)
    return rows


def build() -> dict:
    wl = WL.build()
    wall = wall_screws(wl)
    cur = {f"{i:.1f} A": at_current(i) for i in CURRENTS}
    parts = {}
    for k, c in cur.items():
        t = gear_teeth(c)
        parts[k] = dict(teeth=t, hertz=hertz(t), setscrew=pinion_setscrew(c), shaft=spool_shaft(c), body=spool_body(c), tieoff=tieoff(c, wl),
                        motor=motor_shaft(c, wl), wall=wall)
    sp = speed()
    return dict(ratio=N_RATIO, eta=ETA, currents=cur, direct_drive=direct_drive(), wall=wall, speed=sp, encoder=encoder(sp), eta_table=eta_table(wl),
                teeth={k: v["teeth"] for k, v in parts.items()}, hertz={k: v["hertz"] for k, v in parts.items()},
                setscrew={k: v["setscrew"] for k, v in parts.items()}, shaft={k: v["shaft"] for k, v in parts.items()},
                spool_body={k: v["body"] for k, v in parts.items()}, tieoff={k: v["tieoff"] for k, v in parts.items()},
                motor_radial={k: v["motor"] for k, v in parts.items()},
                links={k: link_rows(cur[k], wl, parts[k]) for k in cur}, knot_lower=wl["line"]["knot_lower"], pass_ratio=WL.PASS_RATIO,
                fleet_deg=WL.FLEET_DEG)


def report(r: dict) -> None:
    print("WINCH WITH THE 3:1 SPUR REDUCTION (D40)")
    print(f"  ratio {r['ratio']:.1f}, stage efficiency {r['eta']} (assumed, each direction)")
    d = r["direct_drive"]
    print(f"  direct drive today at 1.5 A: capacity {d['capacity_low_kg']:.2f} to {d['capacity_kg']:.2f} kg ({d['margin_low']*100:+.0f} to {d['margin']*100:+.0f} % on 1.50 kg), "
          f"fuse {d['fuse_low']:.0f} to {d['fuse_up']:.0f} N, parts must hold {d['need']:.0f} N, heat {d['heat']:.2f} W")
    for k, c in r["currents"].items():
        print(f"  {k}: Vref {c['vref']:.2f} V; hold {c['hold']:.3f} N.m; running pull {c['run_full']:.1f} N full / {c['run_core']:.1f} N core; design {c['design']:.1f} N; "
              f"capacity {c['capacity_low_kg']:.2f} (full-step vector) to {c['capacity_kg']:.2f} kg ({c['margin_low']*100:+.0f} to {c['margin']*100:+.0f} % on 1.50 kg); "
              f"fuse {c['fuse_low']:.0f} to {c['fuse_up']:.0f} N; parts must hold {c['need']:.0f} N; heat {c['heat']:.2f} W")
    for k, t in r["teeth"].items():
        h = r["hertz"][k]
        print(f"  teeth at {k}: spool-side F_t {t['f_t']:.1f} N (pinion side {t['f_t_pinion_side']:.1f}), F_r {t['f_r']:.1f} N; Lewis {t['sigma_gear']:.2f} MPa vs {t['allow']:.1f} "
              f"(SF {t['sf']:.2f} on the half-UTS allowable); root {t['sigma_root']:.1f} MPa (Kf {t['kf']}, thinning x{t['thin_factor']:.3f}) vs {t['allow_fail']:.2f} warm UTS "
              f"-> D39 ratio {t['ratio']:.2f}")
        print(f"      steel pinion: Lewis {t['pinion_sigma']:.1f} MPa = {t['pinion_util']*100:.1f} % of {t['pinion_allow']:.0f} MPa; "
              f"Hertz p_max {h['p_max']:.1f} MPa (F_n {h['f_n']:.1f} N, rho {h['rho']:.2f} mm, E* {h['e_star']:.0f} MPa) vs {h['allow']:.1f}, force ratio {h['ratio']:.2f}")
    for k, s in r["setscrew"].items():
        print(f"  pinion set screw at {k}: {s['torque_lo']:.2f} to {s['torque_hi']:.2f} N.m, ratio {s['ratio_lo']:.2f} to {s['ratio_hi']:.2f}; per mu (low seat): " +
              ", ".join(f"{mu} {v['ratio_lo']:.2f}" for mu, v in s["by_mu"].items()) + f"; WL's PETG-bore friction gave {s['ratio_wl_friction']:.2f}")
    for k, s in r["shaft"].items():
        print(f"  shaft at {k}: span {s['span']:.0f} mm, mesh {s['mesh_t']:.0f} N tangential + {s['mesh_r']:.0f} N radial; envelope bearings {s['r_near']:.1f} N near "
              f"(cable y {s['worst_near']['y']:.1f}, {s['worst_near']['theta']:.0f} deg) / {s['r_far']:.1f} N far (y {s['worst_far']['y']:.1f}, {s['worst_far']['theta']:.0f} deg); "
              f"M {s['moment']:.0f} N.mm (y {s['worst_moment']['y']:.1f}, {s['worst_moment']['theta']:.0f} deg), {s['sigma']:.1f} MPa ({s['ratio']:.2f} x yield); "
              f"mid-plane case {s['midplane']['r_near']:.1f} / {s['midplane']['r_far']:.1f} N, {s['midplane']['moment']:.0f} N.mm")
        print(f"      axial thrust {s['axial']:.1f} N; P0 {s['p0']:.1f} N ({s['brg_ratio']:.2f} x C0); Jasper's seats must hold {s['seat_near_need']:.0f} N (tab) and "
              f"{s['seat_far_need']:.0f} N (far cheek) radial, {s['seat_axial_need']:.0f} N axial")
    for k, b in r["spool_body"].items():
        o = r["tieoff"][k]
        print(f"  spool body at {k}: {b['torque']:.3f} N.m, J {b['j']:.0f} mm4, drum core shear {b['tau']:.2f} MPa vs {b['allow']:.1f} (ratio {b['ratio']:.1f}); tie-off "
              f"{o['with_wraps'][0]:.0f} to {o['with_wraps'][1]:.0f} N with {o['wraps']} dead wraps ({o['share'][0]*100:.0f} to {o['share'][1]*100:.0f} %), {o['without']:.0f} N without; "
              f"ligaments {o['ligament_bore']:.2f} mm to the bore, {o['ligament_core']:.2f} mm to the core surface")
    for k, m in r["motor_radial"].items():
        print(f"  motor shaft at {k}: pinion load {m['f_run']:.1f} N running, {m['f_slip']:.1f} N at the slip torque ({m['slip_vs_catalogue']:.2f} x the {m['catalogue']:.0f} N life rating at "
              f"{m['catalogue_arm']:.0f} mm; arm {m['arm_mm']:.0f} mm); static: {m['sigma']:.1f} MPa at lever {m['lever']:.0f} mm, Z {m['z']:.2f} mm3 ({m['shaft_ratio']:.1f} x yield); "
              f"front bearing {m['brg_reaction']:.0f} N vs C0 {m['brg_c0']:.0f} ({m['brg_ratio']:.1f} x)")
    w = r["wall"]
    print(f"  wall screws at the new load point: design withdrawal at {w['withdrawal']['f']:.0f} N of line ({w['withdrawal']['case']}, cable y {w['withdrawal']['y']:.1f}); "
          f"head punch {w['head_punch_per_screw']:.0f} N per screw at {w['head_punch']['f']:.0f} N ({w['head_punch']['case']}, y {w['head_punch']['y']:.1f}); "
          f"old point: {w['wl_old']['f']:.0f} N ({w['wl_old']['case']})")
    e = r["encoder"]
    print(f"  encoder: one skip = {e['skip_deg']:.1f} deg at the spool = {e['skip_counts']:.1f} counts = {e['skip_mm']:.2f} mm of line (two: {e['two_skips_mm']:.2f}); "
          f"tracking tolerance {e['tol']} counts = {e['tol_mm']:.2f} mm (dwell {e['dwell_s']} s); a continuous slip trips it in {e['trip_skips']} skips = "
          f"{e['trip_steps']} full steps = {e['trip_mm']:.2f} mm = {e['trip_ms']:.1f} ms")
    for b in e["budget"]:
        print(f"      {b['item']:<50} {b['lo']:5.1f} to {b['hi']:5.1f} counts")
    print(f"      persistent worst case {e['budget_lo']:.1f} to {e['budget_hi']:.1f} counts; {e['tol']} counts is x{e['margin_lo']:.2f} to x{e['margin_hi']:.2f} over it ({e['headroom']:.1f} counts of headroom)")
    v = r["speed"]
    print(f"  speed: full_steps_per_rev {v['full_steps_per_rev']}; 50 mm/s needs {v['rate_core']:.0f} steps/s at the core ({v['rate_full']:.0f} full), "
          f"motor {v['motor_rpm']:.0f} rpm (direct drive {v['motor_rpm_direct']:.0f} rpm); {v['mm_per_step_core']:.3f} mm of cable per full step at the core")
    print("  efficiency sensitivity at 1.0 A (capacity nominal / full-step, fuse upper, knot ratio):")
    for x in r["eta_table"]["rows"]:
        print(f"    eta {x['eta']:.2f}: {x['capacity_kg']:.2f} / {x['capacity_low_kg']:.2f} kg, {x['fuse_up']:.1f} N, knot {x['knot_ratio']:.2f}")
    print(f"    the knot passes 1.5 x only while eta >= {r['eta_table']['eta_knot_min']:.2f}")
    for k, rows in r["links"].items():
        print(f"  links at {k} (ratio to the motor's upper slip force; torque links by torque):")
        for x in rows:
            rng = f"{x['ratio']:5.2f} to {x['ratio_hi']:5.2f}" if x["ratio_hi"] is not None else f"{x['ratio']:5.2f}"
            print(f"    {x['link']:<42} {rng:<14} {x['verdict']}")


def main() -> None:
    r = build()
    report(r)
    OUT_JSON.write_text(json.dumps(r, indent=1, default=float))
    print(f"wrote {OUT_JSON.relative_to(S.ROOT)}")


if __name__ == "__main__":
    main()
