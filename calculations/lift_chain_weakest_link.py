"""Weakest link of the lifting chain, one winch station at 1.5 A (D37): which part gives first?

Asked by Jasper (10/22): "validate the weakest links in the chain for each module for lifting: first how much the studs
can hold, then the mount itself, then the cable and the joint holding the motor, then the torque. The goal is to make the
motor torque the smallest force that gives first, so the motor slips before anything is damaged, and the encoder picks it
up and reports an overload."

Chain (line force from the claw to the house):
    claw tie-off -> Dyneema line -> spool tie-off -> spool hub -> set screw on the D-flat -> motor shaft and bearings
    -> motor (torque: the intended fuse) -> 4 x M3 into the motor -> 5 mm PETG motor tab -> slide-in dovetails
    -> wall mount plate -> wall screws -> wood stud

Method. One number per link: the LINE TENSION at which that link gives (breaks, strips, yields or slips), lower and upper
estimates. The motor is the fuse: above its holding torque the rotor skips, the spool turns away from the command, and the
station's TRACKING fault (encoder on the spool vs commanded steps) stops it. Every other link must give at a higher line
tension than the HIGHEST force the motor can put on the line before it skips.

    fuse_upper = hold(1.5 A) x 40/36 (motor sensitivity) / r_empty / cos(fleet limit)      (the most the motor can pull)
    ratio      = link_lower / fuse_upper
    PASS >= 1.5   MARGINAL 1.0 to 1.5   GIVES FIRST < 1.0

1.5 covers the rotor-inertia and cogging overshoot while the motor skips, and scatter in printed parts. The structural
allowable of the static-study manual (SF >= 3 on 25 MPa derated PETG at the slip load) stays the design criterion for the
printed station; this script asks a different question: the ORDER in which things give.

Tags: [REPO] recorded in the repo (file named), [SRC] published reference (listed in the .md), [ASSUMED] engineering
assumption to be replaced by a measurement, [CALC] derived here. Units: N, mm, MPa, N.m unless stated.

    PYTHONPATH=. /usr/bin/python3 -m calculations.lift_chain_weakest_link
Writes calculations/lift_chain_weakest_link.json (read by the deck build).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from calculations import simulation_loads as S

OUT_JSON = Path(__file__).with_suffix(".json")
G = 9.81
LBF = 4.448222          # N per lbf
INCH = 25.4             # mm per inch

# ===========================================================================
# 0. BASIS
# ===========================================================================
I_SET = 1.5                                  # A [REPO D37]
T15 = S.tension_cases(I_SET)                 # hold 0.36 N.m, slip 48.0 N, run 33.6 / 25.2 N  [REPO simulation_loads.py]
HOLD = T15["hold"]                           # N.m, 36 N.cm at the rated 1.5 A [REPO SHOPPING_LIST, R10]
MOTOR_SENS = S.HOLD_40 / S.HOLD_36           # x1.111: a 40 N.cm motor (17HS4401 nameplate, unverified) [REPO]
VECTOR_LOW = 1.0 / math.sqrt(2.0)            # x0.707: A4988 current vector at a full step (manual section 0, item 1)
FLEET_DEG = S.fleet_limit_deg()              # 26.1 deg: largest fleet angle before the line scrubs a flange [REPO]
FLEET_K = 1.0 / math.cos(math.radians(FLEET_DEG))
DESIGN_FORCE = T15["work_margin"]            # 16.8 N: running pull at a full spool / 1.5 skip margin [REPO D37]
JEANS_PEAK = 1.50 * 1.101 * G                # N: claw 0.60 + jeans 0.90 kg, worst tension per weight 1.101 (+2 m/s2) [REPO Lift budget]

FUSE = dict(
    hold_nm=HOLD,
    slip_empty=T15["slip"],                  # 48.0 N: holding torque / 7.5 mm core
    slip_full=HOLD / S.R_FULL,               # 36.0 N: full spool, r = 10 mm
    run_empty=T15["work_core"],              # 33.6 N: skips at this pull while moving
    run_full=T15["work"],                    # 25.2 N
    slip_low=T15["slip"] * VECTOR_LOW,       # 33.9 N: if the true torque vector is 1/sqrt(2) of the datasheet figure
    slip_fleet=T15["slip"] * FLEET_K,        # 53.5 N: along a fully fleeted line (only the in-plane share turns the drum)
    upper=T15["slip"] * MOTOR_SENS * FLEET_K,  # 59.4 N: 40 N.cm motor AND fully fleeted line
    upper_hold_nm=HOLD * MOTOR_SENS,         # 0.40 N.m: most torque the motor can put through the spool joint
)
PASS_RATIO = 1.5


def verdict(ratio: float) -> str:
    return "PASS" if ratio >= PASS_RATIO else ("MARGINAL" if ratio >= 1.0 else "GIVES FIRST")


# ===========================================================================
# 1. LINE AND KNOTS
# ===========================================================================
LINE_RATED_LBF = 120.0          # 9KM DWLIFE X8 braided Dyneema, 120 lb [REPO docs/SHOPPING_LIST.md]
KNOT_EFF = (0.50, 0.90)         # braid knot strength / line strength: 50 % (clinch-type knots in braid) to 90 % (Palomar) [SRC]
MU_LINE_PETG = (0.05, 0.10)     # UHMWPE on PETG [ASSUMED], for the dead wraps at the spool
DEAD_WRAPS = 3                  # wraps never paid out (proposed rule)


def line_links() -> dict:
    rated = LINE_RATED_LBF * LBF
    knot = [rated * e for e in KNOT_EFF]
    # Capstan: with n dead wraps the spool tie-off sees T exp(-mu 2 pi n); the knot at the claw sees the full T.
    capstan = [math.exp(-mu * 2 * math.pi * DEAD_WRAPS) for mu in MU_LINE_PETG]
    return dict(rated=rated, knot_lower=knot[0], knot_upper=knot[1],
                tieoff_share_with_wraps=(min(capstan), max(capstan)))


# ===========================================================================
# 2. SPOOL TO SHAFT: SET SCREW ON THE D-FLAT
# ===========================================================================
# Geometry [REPO verification/design_review_gen2.md R4, Spoolv3]: bore 5.45 with a 0.50 mm flat (4.95 across the flat),
# radial M3 set screw (2.8 hole) on the flat's axis, hub (core) 15 mm.  Shaft 5.0 with a 0.50 mm flat (4.50 across).
SHAFT_D = 5.0
SHAFT_FLAT_DEPTH = 0.5
BORE_D = 5.45
BORE_FLAT_DEPTH = 0.5
HUB_R = 7.5
MU_TIP = 0.20                   # steel cup point on the steel flat, dry [ASSUMED]
MU_BORE = 0.25                  # steel shaft on the PETG bore [ASSUMED]
CUP_BITE = 1.15                 # cup-point penetration adds up to ~15 % holding [SRC Machine Design, set screws]
K_NUT = 0.20                    # torque coefficient, dry steel [ASSUMED]
SEAT_TORQUE_STEEL = (3.0 * 0.113, 4.0 * 0.113)   # N.m: 3-4 in-lb for a #4-40 / M3 cup point in a STEEL thread [SRC]
PETG_SHEAR = (0.58 * S.PETG["yield_derated"], 0.58 * S.PETG["uts"])  # 14.5 to 26 MPa, printed thread shear [ASSUMED]
SEAT_FRACTION = (0.5, 0.8)      # set screws in a plastic thread are seated below the strip force [ASSUMED]


def setscrew_joint() -> dict:
    r_flat = SHAFT_D / 2 - SHAFT_FLAT_DEPTH          # 2.0 mm: screw tip on the flat
    r_bore = SHAFT_D / 2                             # 2.5 mm: line contact with the bore opposite the screw
    lever = MU_TIP * r_flat + MU_BORE * r_bore       # mm: torque per newton of set-screw force
    # Thread length in the hub at the flat: hub radius minus the bore flat's distance from the axis.
    l_e = HUB_R - (BORE_D / 2 - BORE_FLAT_DEPTH) - 0.5          # 4.8 mm (0.5 mm lead-in)
    a_strip = 0.5 * math.pi * 3.0 * l_e                         # mm2, internal-thread shear area (about half the cylinder)
    f_strip = [a_strip * t for t in PETG_SHEAR]
    f_seat_petg = [f_strip[0] * SEAT_FRACTION[0], f_strip[1] * SEAT_FRACTION[1]]
    f_seat_insert = [t / (K_NUT * 3.0e-3) for t in SEAT_TORQUE_STEEL]   # brass insert: seat to the steel rating
    cap = lambda f: CUP_BITE * f * lever * 1e-3                 # N.m
    petg = [cap(f) for f in f_seat_petg]
    insert = [cap(f) for f in f_seat_insert]
    return dict(r_flat=r_flat, lever_mm=lever, thread_len=l_e, strip_area=a_strip, f_strip=f_strip,
                f_seat_petg=f_seat_petg, f_seat_insert=f_seat_insert,
                torque_petg=petg, torque_insert=insert,
                dflat_now=dflat_engagement(BORE_D, BORE_FLAT_DEPTH),
                dflat_tight=dflat_engagement(5.15, 0.5 + 0.10 - 0.075))


def dflat_engagement(bore_d: float, bore_flat_depth: float) -> dict:
    """If the set screw slips: how far the shaft turns before its flat corner meets the bore's flat, and the lever of that
    contact. The screw pushes the shaft into the round side of the bore, so the whole clearance sits at the flat."""
    r = SHAFT_D / 2
    off = (bore_d - SHAFT_D) / 2                             # shaft centre pushed away from the flat
    h_bore = bore_d / 2 - bore_flat_depth + off              # bore flat from the shaft axis
    h_shaft = r - SHAFT_FLAT_DEPTH
    a0 = math.acos(h_shaft / r)                              # corner angle from the flat normal
    a1 = math.acos(min(1.0, h_bore / r))
    turn = math.degrees(a0 - a1)
    lever = r * math.sin(a1)
    force = HOLD / (lever * 1e-3) if lever > 0 else float("inf")
    return dict(gap=h_bore - h_shaft, turn_deg=turn, lever_mm=lever, contact_force_at_hold=force,
                across_flat=bore_d - bore_flat_depth)


# ===========================================================================
# 3. MOTOR SHAFT AND FRONT BEARING
# ===========================================================================
SHAFT_SY = (350.0, 600.0)       # MPa, stepper shaft yield: plain carbon steel to hardened stainless [ASSUMED]
BRG_IN = 3.0                    # mm, front bearing centre behind the flange face [ASSUMED]
BRG_SPAN = 30.0                 # mm, front-to-rear bearing spacing, 38-40 mm body [ASSUMED]
BRG_C0 = 380.0                  # N, static rating of a 625-size (5 x 16 x 5) deep-groove bearing [ASSUMED, check datasheet]
RADIAL_RATING = 28.0            # N at 20 mm from the flange: service (life) rating, 17HS4401-1704A listing [SRC]


def dflat_section_modulus(d: float = SHAFT_D, depth: float = SHAFT_FLAT_DEPTH, n: int = 1200) -> float:
    """Smallest elastic section modulus of a D-section over all bending axes (the flat turns with the shaft)."""
    r = d / 2
    ys = np.linspace(-r, r, n)
    zs = np.linspace(-r, r, n)
    Y, Z = np.meshgrid(ys, zs)
    m = (Y ** 2 + Z ** 2 <= r * r) & (Z <= r - depth)
    dA = (ys[1] - ys[0]) * (zs[1] - zs[0])
    A = m.sum() * dA
    yc, zc = (Y[m].sum() * dA) / A, (Z[m].sum() * dA) / A
    best = float("inf")
    for ang in np.linspace(0, math.pi, 73):
        c, s = math.cos(ang), math.sin(ang)
        dist = (Y[m] - yc) * c + (Z[m] - zc) * s          # distance from a neutral axis at angle ang
        I = (dist ** 2).sum() * dA
        best = min(best, I / np.abs(dist).max())
    return best


def shaft_links() -> dict:
    a = S.Y_DRUM + BRG_IN                                    # 21 mm: line force to the front bearing
    Z = dflat_section_modulus()
    f_yield = SHAFT_SY[0] * Z / a
    f_yield_hi = SHAFT_SY[1] * Z / a
    r_front = lambda F: F * (a + BRG_SPAN) / BRG_SPAN       # overhung load on the front bearing
    f_brg = BRG_C0 * BRG_SPAN / (a + BRG_SPAN)
    return dict(lever=a, Z=Z, Z_round=math.pi * SHAFT_D ** 3 / 32, f_yield=f_yield, f_yield_hi=f_yield_hi, f_bearing_static=f_brg,
                front_bearing_at_fuse=r_front(FUSE["upper"]),
                radial_rating=RADIAL_RATING, run_vs_rating=FUSE["run_empty"] / RADIAL_RATING)


# ===========================================================================
# 4. MOTOR TO TAB: 4 x M3 x 12 (D38) through the 5 mm PETG tab into the motor's aluminium front cap
# ===========================================================================
M3_ENGAGE = 3.8                 # mm thread in the motor [REPO D38]
AL_SHEAR = 120.0                # MPa, die-cast / 6061 aluminium shear (lower) [ASSUMED]
HEAD_D, HOLE_D, TAB_T = 5.5, 3.5, 5.0   # [REPO THERMAL_SCREW_HEAD_D, S3 hole, tab]
SCREW_PATTERN = 31.0            # mm [REPO NEMA17_HOLES]


def motor_screw_links() -> dict:
    strip_al = 0.6 * math.pi * 3.0 * M3_ENGAGE * AL_SHEAR             # N per screw
    punch = math.pi * HEAD_D * TAB_T * PETG_SHEAR[0]                   # head punching through the tab, N per screw
    per_screw_per_N = S.Y_DRUM / (2 * SCREW_PATTERN)                   # tension per screw per N of line (pivot on one row)
    cap = min(strip_al, punch)
    return dict(strip_al=strip_al, punch=punch, per_screw_per_N=per_screw_per_N,
                f_line=cap / per_screw_per_N, at_fuse=FUSE["upper"] * per_screw_per_N)


# ===========================================================================
# 5. MOTOR TAB (5 mm PETG), SLIDE-IN RETENTION: the hand model of the static-study manual, scaled to 1.5 A
# ===========================================================================
KT = dict(sharp=2.5, fillet_2mm=1.5)    # stress concentration at the tab root: sharp back corner (as drawn), 2 mm fillet [ASSUMED]
PETG_LAYER = S.Z_STRENGTH               # 22.5 MPa across layers [REPO review R5]


def tab_links() -> dict:
    out = {}
    for cid, label, u, T, p in S.reachable_cases(T15):
        est = S.tab_root_estimate(T * u, p)          # at the 1.5 A slip tension for that direction
        per_N_vm, per_N_sig = est["vm_nom"] / T, est["sigma_nom"] / T
        rows = {}
        for k, kt in KT.items():
            f_vm = S.PETG["yield_derated"] / (kt * per_N_vm)
            f_sig = PETG_LAYER / (kt * per_N_sig)
            rows[k] = min(f_vm, f_sig)
        out[cid] = dict(label=label, T_slip=T, vm_at_slip=est["vm_nom"], sig_at_slip=est["sigma_nom"],
                        fail_sharp=rows["sharp"], fail_fillet=rows["fillet_2mm"], nominal=S.PETG["yield_derated"] / per_N_vm)
    worst = min(out, key=lambda c: out[c]["fail_sharp"])
    return dict(cases=out, worst=worst)


def retention_link() -> dict:
    # Dovetail flank bearing 0.053 MPa at the D3 pull-away of 33.3 N (manual section 9): linear.
    bearing_per_N = 0.053 / 33.3
    return dict(bearing_at_fuse=bearing_per_N * FUSE["upper"], f_line=S.PETG["yield_derated"] / bearing_per_N)


# ===========================================================================
# 6. WALL SCREWS AND THE STUD
# ===========================================================================
# NDS (AWC) reference withdrawal design value of a wood screw in side grain: W = 2850 G^2 D  (lb per inch of thread in the
# main member; G specific gravity, D screw diameter in inches).  Normal load duration (C_D = 1.0), dry service.
# Average ultimate from tests, Wood Handbook form: P = 15 700 G^2 D L (secondary source; about 5.5 x the design value).
SPECIES_G = {"spruce-pine-fir": 0.42, "Douglas fir-larch": 0.50, "southern pine": 0.55}   # [SRC NDS]
SCREW_D_IN = {"#6": 0.138, "#8": 0.164, "#10": 0.190}
SCREW_ROOT_IN = {"#6": 0.097, "#8": 0.113, "#10": 0.124}  # root diameters [SRC NDS Table L3]
FYB = 690.0                     # MPa, bending yield of #6-#8 wood screws (100 ksi) [SRC NDS Table I1]
PLATE_T = 10.53                 # mm, PETG under the counterbore [REPO manual W2: x -42.32 to -31.79]
DRYWALL_T = 12.7                # mm, 1/2 in gypsum [ASSUMED]
THREAD_IN_STUD_IN = 1.0         # inches of thread in the stud (#6 x 2-1/2 in partly threaded) [ASSUMED, measure]
HEAD_6_D = 6.6                  # mm, #6 pan head under the counterbore [ASSUMED]
DRYWALL_ONLY = dict(bare=(5 * LBF, 10 * LBF), plastic_anchor=(10 * LBF, 25 * LBF), zinc_selfdrill=(60 * LBF, 60 * LBF))  # tension [SRC]
COL_Y = S.SCREW_COLS_Y
PLATE_Y = (-94.44, 125.56)      # mm, wall mount plate edges [REPO manual W1]


def withdrawal(screw: str, species: str, inches: float = THREAD_IN_STUD_IN) -> dict:
    g = SPECIES_G[species]
    d = SCREW_D_IN[screw]
    return dict(design=2850 * g * g * d * inches * LBF, ultimate=15700 * g * g * d * inches * LBF)


def screw_lateral(screw: str = "#6") -> float:
    """Screw bent in double curvature across the drywall gap (PETG plate clamped, stud holds the other end)."""
    dr = SCREW_ROOT_IN[screw] * INCH
    mp = FYB * dr ** 3 / 6.0
    return 2 * mp / DRYWALL_T


def _moments(F: np.ndarray, p: np.ndarray, C: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    Mw = np.cross(S.P_MOTOR - C, np.array([0, 0, -(S.M_MOTOR + 0.01) * G])) \
        + np.cross(S.P_SHELL - C, np.array([0, 0, -S.M_SHELL * G]))
    Ftot = F + np.array([0.0, 0.0, -(S.REMOTE_WEIGHT_N + S.SELF_WEIGHT_N)])
    return Ftot, np.cross(p - C, F) + Mw


def screws_six(F: np.ndarray, p: np.ndarray) -> dict:
    C = np.array([S.WALL_X, float(np.mean(COL_Y)), float(np.mean(S.SCREW_ROWS_Z))])
    Ftot, Mc = _moments(F, p, C)
    return S.screw_group_estimate(Ftot, Mc)


def screws_one_column(F: np.ndarray, p: np.ndarray, col_y: float = COL_Y[0]) -> dict:
    """Only one column (3 screws) lands in the stud: the 37.0 mm column spacing does not fit a 38.1 mm stud.
    Tension = Fx/3 + My (rows) + Mz / e, with e the lever from the column to the plate edge the plate tips about
    (rigid plate bearing on the wall at that edge); conservative: the nearer edge."""
    C = np.array([S.WALL_X, col_y, float(np.mean(S.SCREW_ROWS_Z))])
    Ftot, Mc = _moments(F, p, C)
    dz = np.array(S.SCREW_ROWS_Z) - np.mean(S.SCREW_ROWS_Z)
    e = min(abs(col_y - PLATE_Y[0]), abs(PLATE_Y[1] - col_y))
    t = abs(Ftot[0]) / 3 + abs(Mc[1]) * np.max(np.abs(dz)) / np.sum(dz ** 2) + abs(Mc[2]) / e / 3
    shear = math.hypot(Ftot[1], Ftot[2]) / 3 + abs(Mc[0]) * np.max(np.abs(dz)) / np.sum(dz ** 2)
    return dict(t_top=float(t), shear=float(shear), lever_e=e)


def solve_line_force(fn, u: np.ndarray, p: np.ndarray, target: float, key: str = "t_top") -> float:
    """Line tension at which fn(T u, p)[key] reaches target (bisection; weights make it affine, abs makes it piecewise)."""
    lo, hi = 0.0, 1.0e5
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if fn(mid * u, p)[key] < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def wall_links() -> dict:
    reach = S.reachable_cases(T15)
    w = withdrawal("#6", "spruce-pine-fir")
    lat = screw_lateral("#6")
    rows = {}
    for cid, label, u, T, p in reach:
        s6, s3 = screws_six(T * u, p), screws_one_column(T * u, p)
        rows[cid] = dict(T=T, six_t=s6["t_top"], six_v=s6["shear"], one_t=s3["t_top"], one_v=s3["shear"],
                         f_design_one=solve_line_force(screws_one_column, u, p, w["design"]),
                         f_ult_one=solve_line_force(screws_one_column, u, p, w["ultimate"]),
                         f_design_six=solve_line_force(screws_six, u, p, w["design"]),
                         f_bare_drywall=solve_line_force(screws_six, u, p, DRYWALL_ONLY["bare"][0]),
                         f_plastic_anchor=solve_line_force(screws_six, u, p, DRYWALL_ONLY["plastic_anchor"][0]))
    worst = min(rows, key=lambda c: rows[c]["f_design_one"])
    table = {f"{s} in {sp}": withdrawal(s, sp) for s in SCREW_D_IN for sp in SPECIES_G}
    punch = math.pi * HEAD_6_D * PLATE_T * PETG_SHEAR[0]          # head punching through the 10.5 mm PETG under the counterbore
    cid, label, u, T, p = [c for c in reach if c[0] == worst][0]
    f_punch = solve_line_force(screws_one_column, u, p, punch)
    return dict(per_case=rows, worst=worst, withdrawal_6_spf=w, lateral_6=lat, table_1in=table,
                head_punch=punch, f_head_punch=f_punch)


def stud_bending() -> dict:
    """A 2 x 4 stud (1.5 x 3.5 in, SPF) loaded at mid-height by the worst pull-away, simply supported over 2.44 m.
    The station is near the top plate, so this is an upper bound on the stud's own stress."""
    L = 2.44
    S_x = (1.5 * INCH) * (3.5 * INCH) ** 2 / 6.0 * 1e-9        # m3
    F = FUSE["upper"]
    sigma = (F * L / 4.0) / S_x / 1e6                          # MPa
    return dict(F=F, sigma=sigma, Fb_ref=875 * 0.006895)      # SPF No. 2 reference bending, 875 psi [SRC NDS supplement]


# ===========================================================================
# 7. ENCODER DETECTION OF A SLIP
# ===========================================================================
def detection() -> dict:
    cfg = json.loads((S.ROOT / "config" / "robot.sim.json").read_text())
    tol = cfg["faults"]["tracking_tol_counts"]
    dwell = cfg["faults"]["tracking_dwell_s"]
    cpr = 4096                                                  # AS5600 [REPO EncoderConfig]
    skip_deg = 4 * 360.0 / 200                                  # a stepper loses steps in whole electrical cycles: 4 full steps
    return dict(tol_counts=tol, tol_deg=tol * 360.0 / cpr, dwell_s=dwell, skip_deg=skip_deg,
                skip_counts=skip_deg / 360.0 * cpr, line_per_skip_mm=math.radians(skip_deg) * S.R_EMPTY * 1e3,
                tol_line_mm=math.radians(tol * 360.0 / cpr) * S.R_EMPTY * 1e3)


# ===========================================================================
# REPORT
# ===========================================================================
def build() -> dict:
    line = line_links()
    ss = setscrew_joint()
    sh = shaft_links()
    ms = motor_screw_links()
    tab = tab_links()
    ret = retention_link()
    wall = wall_links()
    stud = stud_bending()
    det = detection()
    tw = tab["cases"][tab["worst"]]
    ww = wall["per_case"][wall["worst"]]
    t_need = FUSE["upper_hold_nm"]
    k_line = FLEET_K / S.R_EMPTY           # N of line (fleeted, empty core) per N.m through the spool joint
    links = [   # name, lower, upper (line tension, N), ratio basis, basis text
        ("Motor torque (the fuse)", FUSE["slip_low"], FUSE["upper"], None,
         "holding torque / spool radius; 33.9 N (1/sqrt2 vector) to 59.4 N (40 N.cm motor, fleeted line)"),
        ("Spool on shaft: set screw in a printed thread", ss["torque_petg"][0] * k_line, ss["torque_petg"][1] * k_line,
         ss["torque_petg"][0] / t_need,
         f"{ss['torque_petg'][0]:.2f} to {ss['torque_petg'][1]:.2f} N.m against {t_need:.2f} N.m: seat force capped by the PETG thread"),
        ("Motor tab root, sharp back corner (as drawn)", tw["fail_sharp"], tw["nominal"], None,
         f"hand model of the static manual, worst reachable direction {tab['worst']}, 25 MPa derated / 22.5 MPa across layers"),
        ("Spool on shaft: set screw in a brass heat-set insert", ss["torque_insert"][0] * k_line, ss["torque_insert"][1] * k_line,
         ss["torque_insert"][0] / t_need,
         f"{ss['torque_insert'][0]:.2f} to {ss['torque_insert'][1]:.2f} N.m: screw seated to the steel-thread rating (3-4 in-lb)"),
        ("Motor tab root with a 2 mm fillet", tw["fail_fillet"], tw["nominal"], None, "same model, Kt 1.5"),
        ("Motor shaft (bending yield at the D-flat)", sh["f_yield"], sh["f_yield_hi"], None,
         f"350 to 600 MPa x Z {sh['Z']:.2f} mm3 / {sh['lever']:.0f} mm; front-bearing static rating at {sh['f_bearing_static']:.0f} N"),
        ("Line knot (120 lb braid)", line["knot_lower"], line["knot_upper"], None, "50 to 90 % knot efficiency"),
        ("Wall screws: 3 x #6 in one stud column", ww["f_design_one"], ww["f_ult_one"], None,
         f"top screw at the NDS design value (lower) and the test ultimate (upper); 1 in of thread in SPF, "
         f"{wall['withdrawal_6_spf']['design']:.0f} / {wall['withdrawal_6_spf']['ultimate']:.0f} N per screw"),
        ("Wall plate: screw head pulls through the PETG", wall["f_head_punch"], wall["f_head_punch"] * PETG_SHEAR[1] / PETG_SHEAR[0], None,
         f"#6 head punching through {PLATE_T} mm of PETG, {wall['head_punch']:.0f} N per screw"),
        ("Motor screws (4 x M3 x 12 into the motor)", ms["f_line"], ms["strip_al"] / ms["per_screw_per_N"], None,
         "head punching through the 5 mm PETG tab; thread strip in the aluminium cap"),
        ("Slide-in dovetails and lips", 1000.0, ret["f_line"], None,
         f"flank bearing {ret['bearing_at_fuse']:.2f} MPa at the fuse; not limiting (shown as > 1 kN)"),
    ]
    rows = []
    for name, lo, hi, ratio_t, basis in links:
        ratio = ratio_t if ratio_t is not None else lo / FUSE["upper"]
        rows.append(dict(link=name, lower=lo, upper=hi, ratio=ratio,
                         verdict="FUSE" if name.startswith("Motor torque") else verdict(ratio), basis=basis))
    return dict(fuse=FUSE, design_force=DESIGN_FORCE, jeans_peak=JEANS_PEAK, line=line, setscrew=ss, shaft=sh,
                motor_screws=ms, tab=tab, retention=ret, wall=wall, stud=stud, detection=det, ranking=rows,
                torque_needed_nm=t_need, pass_ratio=PASS_RATIO, fleet_deg=FLEET_DEG)


def report(r: dict) -> None:
    f = r["fuse"]
    print("=" * 100)
    print("WEAKEST LINK OF THE LIFTING CHAIN, ONE STATION AT 1.5 A")
    print("=" * 100)
    print("\n0. Demand and the fuse (line tension, N)")
    print(f"  design force (full spool, 1.5 skip margin)      {r['design_force']:6.1f}")
    print(f"  jeans case, worst cable (1.50 kg x 1.101 x g)    {r['jeans_peak']:6.1f}")
    print(f"  motor skips while moving: full / empty spool     {f['run_full']:6.1f} / {f['run_empty']:.1f}")
    print(f"  motor slips while holding: full / empty spool    {f['slip_full']:6.1f} / {f['slip_empty']:.1f}   (hold {f['hold_nm']:.3f} N.m)")
    print(f"  lower bound (1/sqrt2 current vector)             {f['slip_low']:6.1f}")
    print(f"  fully fleeted line ({r['fleet_deg']:.1f} deg): / cos            {f['slip_fleet']:6.1f}")
    print(f"  UPPER (40 N.cm motor and fleeted line)           {f['upper']:6.1f}   <- every other link must give above this")
    print(f"  fuse / jeans demand: {f['slip_empty']/r['jeans_peak']:.2f} holding, {f['run_full']/r['jeans_peak']:.2f} moving at a full spool")

    print("\n1. Line")
    L = r["line"]
    print(f"  rated 120 lb = {L['rated']:.0f} N; knot {L['knot_lower']:.0f} to {L['knot_upper']:.0f} N; "
          f"with {DEAD_WRAPS} dead wraps the spool tie-off sees {L['tieoff_share_with_wraps'][0]*100:.0f} to "
          f"{L['tieoff_share_with_wraps'][1]*100:.0f} % of the line tension")

    print("\n2. Spool on the shaft (set screw on the D-flat)")
    s = r["setscrew"]
    print(f"  torque per N of set-screw force: {s['lever_mm']:.3f} mm (mu_tip {MU_TIP} x {s['r_flat']} + mu_bore {MU_BORE} x 2.5), x{CUP_BITE} cup bite")
    print(f"  printed thread: {s['thread_len']:.1f} mm long, strip area {s['strip_area']:.1f} mm2, strips at "
          f"{s['f_strip'][0]:.0f} to {s['f_strip'][1]:.0f} N; seated {s['f_seat_petg'][0]:.0f} to {s['f_seat_petg'][1]:.0f} N")
    print(f"  -> torque capacity {s['torque_petg'][0]:.2f} to {s['torque_petg'][1]:.2f} N.m   (needed: motor can apply {r['torque_needed_nm']:.2f} N.m)")
    print(f"  brass insert, seated to 3-4 in-lb: {s['f_seat_insert'][0]:.0f} to {s['f_seat_insert'][1]:.0f} N -> "
          f"{s['torque_insert'][0]:.2f} to {s['torque_insert'][1]:.2f} N.m")
    for k in ("dflat_now", "dflat_tight"):
        d = s[k]
        print(f"  D-flat backup, bore {d['across_flat']:.2f} across the flat: gap {d['gap']:.2f} mm, engages after {d['turn_deg']:.1f} deg "
              f"at {d['lever_mm']:.2f} mm from the axis -> {d['contact_force_at_hold']:.0f} N line contact at 0.36 N.m")

    print("\n3. Shaft and bearing")
    h = r["shaft"]
    print(f"  lever {h['lever']:.0f} mm, Z(D-flat) {h['Z']:.2f} mm3 (round {h['Z_round']:.2f}); yield at {h['f_yield']:.0f} to {h['f_yield_hi']:.0f} N; "
          f"front bearing static at {h['f_bearing_static']:.0f} N; bearing load at the fuse {h['front_bearing_at_fuse']:.0f} N")
    print(f"  service rating 28 N at 20 mm: running pull at the core is {h['run_vs_rating']:.2f} x the rating (bearing life, not strength)")

    print("\n4. Motor screws")
    m = r["motor_screws"]
    print(f"  per screw: Al thread strip {m['strip_al']:.0f} N, head punch-through {m['punch']:.0f} N; "
          f"tension {m['per_screw_per_N']:.2f} N per N of line ({m['at_fuse']:.0f} N at the fuse)")

    print("\n5. Motor tab (hand model of the static manual, at the 1.5 A slip tension for each direction)")
    for cid, c in r["tab"]["cases"].items():
        print(f"  {cid:<4} T {c['T_slip']:5.1f} N: vM nominal {c['vm_at_slip']:.2f} MPa; gives at {c['fail_sharp']:.0f} N (sharp), "
              f"{c['fail_fillet']:.0f} N (2 mm fillet), {c['nominal']:.0f} N (no concentration)")
    print(f"  slide-in dovetails: {r['retention']['bearing_at_fuse']:.3f} MPa at the fuse; would need {r['retention']['f_line']:.0f} N")

    print("\n6. Wall screws and stud")
    w = r["wall"]
    print(f"  #6 in SPF, 1 in of thread: design {w['withdrawal_6_spf']['design']:.0f} N, ultimate {w['withdrawal_6_spf']['ultimate']:.0f} N; "
          f"lateral (bending across 1/2 in drywall) {w['lateral_6']:.0f} N per screw")
    for cid, c in w["per_case"].items():
        print(f"  {cid:<4} at {c['T']:.1f} N: top screw {c['six_t']:.1f} N (6 screws) / {c['one_t']:.1f} N (one column); "
              f"one column reaches the design value at {c['f_design_one']:.0f} N, ultimate at {c['f_ult_one']:.0f} N; "
              f"6 screws in bare drywall give at {c['f_bare_drywall']:.0f} N, in plastic anchors at {c['f_plastic_anchor']:.0f} N")
    print(f"  wall plate: #6 head punching through the PETG at {w['head_punch']:.0f} N per screw -> line {w['f_head_punch']:.0f} N")
    st = r["stud"]
    print(f"  stud bending at the fuse (mid-height, upper bound): {st['sigma']:.2f} MPa vs {st['Fb_ref']:.1f} MPa reference")
    print("  withdrawal per inch of thread (design / ultimate, N):")
    for k, v in w["table_1in"].items():
        print(f"    {k:<26} {v['design']:6.0f} / {v['ultimate']:6.0f}")

    print("\n7. Encoder detection")
    d = r["detection"]
    print(f"  tracking fault at {d['tol_counts']} counts ({d['tol_deg']:.1f} deg, {d['tol_line_mm']:.2f} mm of line) held {d['dwell_s']} s; "
          f"one skip = {d['skip_deg']:.1f} deg = {d['skip_counts']:.0f} counts = {d['line_per_skip_mm']:.2f} mm of line -> caught")

    print("\nRANKING (line tension at which each link gives, N; ratio = lower / fuse upper %.1f N, torque links: N.m / N.m)" % f["upper"])
    for x in sorted(r["ranking"], key=lambda x: x["lower"]):
        print(f"  {x['link']:<72} {x['lower']:7.0f} to {x['upper']:7.0f}   {x['ratio']:5.2f}  {x['verdict']}")


def main() -> None:
    r = build()
    report(r)
    OUT_JSON.write_text(json.dumps(r, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))
    print(f"\nwrote {OUT_JSON.relative_to(S.ROOT)}")


if __name__ == "__main__":
    main()
