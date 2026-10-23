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
    ratio      = link_lower / fuse_upper                (torque links: joint torque / the motor's 0.40 N.m)
    PASS >= 1.5   MARGINAL 1.0 to 1.5   GIVES FIRST < 1.0 ; a range that straddles 1.0 is "MAY GIVE FIRST"

1.5 covers the rotor-inertia and cogging overshoot while the motor skips, and scatter in printed parts. The structural
allowable of the static-study manual (SF >= 3 on 25 MPa derated PETG at the slip load) stays the design criterion for the
printed station; this script asks a different question: the ORDER in which things give.

Printed-PETG links are rated warm: the PETG next to the motor runs at about the motor temperature (thermal check 10/22).
Design (1/8 in fin, 45 to 49 C): x0.85 [ASSUMED]; prototype (0.019 in fin, 56 to 59 C): x0.70 (simulation_loads.HOT_DERATE).

Corrected 10/22 after the independent check (verification/lift_chain_weakest_link_check.md, F1 to F9): tab faces paired
with their own root detail and a direction scan; warm-PETG derate; insert fit and pull-out; spool bore from cad/params.py
(the 10/21 reference); fin offset in the shaft and motor-screw levers; torque links shown as unfleeted cable tension.

Tags: [REPO] recorded in the repo (file named), [USER] stated by Jasper, unverified, [SRC] published reference (listed in the
.md), [ASSUMED] engineering assumption to be replaced by a measurement. Units: N, mm, MPa, N.m unless stated.

    PYTHONPATH=. /usr/bin/python3 -m calculations.lift_chain_weakest_link
Writes calculations/lift_chain_weakest_link.json (read by the deck build).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from cad import params as P
from calculations import simulation_loads as S

OUT_JSON = Path(__file__).with_suffix(".json")
G = 9.81
LBF = 4.448222          # N per lbf
INCH = 25.4             # mm per inch

# ===========================================================================
# 0. BASIS
# ===========================================================================
I_SET = 1.5                                  # A [REPO D37; how 1.5 A was reached is not recorded: every load scales with I]
T15 = S.tension_cases(I_SET)                 # hold 0.36 N.m, slip 48.0 N, run 33.6 / 25.2 N  [REPO simulation_loads.py]
HOLD = T15["hold"]                           # N.m, 36 N.cm at the rated 1.5 A [REPO SHOPPING_LIST, R10]
MOTOR_SENS = S.HOLD_40 / S.HOLD_36           # x1.111: a 40 N.cm motor [USER: 17HS4401 nameplate, unverified]
VECTOR_LOW = 1.0 / math.sqrt(2.0)            # x0.707: A4988 current vector at a full step (manual section 0, item 1)
FLEET_DEG = S.fleet_limit_deg()              # 26.1 deg: largest fleet angle before the line scrubs a flange [REPO]
FLEET_K = 1.0 / math.cos(math.radians(FLEET_DEG))
DESIGN_FORCE = T15["work_margin"]            # 16.8 N: running pull at a full spool / 1.5 skip margin [REPO D37]
K_TENSION = 1.101                            # worst line tension per unit weight, +2 m/s2 included [REPO Lift budget]
NEEDED_KG = 1.50                             # claw 0.60 + jeans 0.90 kg [REPO Lift budget]
JEANS_PEAK = NEEDED_KG * K_TENSION * G       # N: worst tension for the whole payload [REPO Lift budget]
FIN_T = P.FIN1021_T_PRODUCTION_MM            # 3.175 mm: the motor sits this far behind the tab's back face (D38)
WARM = dict(design=0.85, prototype=S.HOT_DERATE)   # PETG strength factor near the motor [ASSUMED / REPO]

FUSE = dict(
    hold_nm=HOLD,
    slip_empty=T15["slip"],                  # 48.0 N: holding torque / 7.5 mm core
    slip_full=HOLD / S.R_FULL,               # 36.0 N: full spool, r = 10 mm
    run_empty=T15["work_core"],              # 33.6 N: skips at this pull while moving
    run_full=T15["work"],                    # 25.2 N
    slip_low=T15["slip"] * VECTOR_LOW,       # 33.9 N: if the true torque vector is 1/sqrt(2) of the datasheet figure
    slip_fleet=T15["slip"] * FLEET_K,        # 53.4 N: along a fully fleeted line (only the in-plane share turns the drum)
    upper=T15["slip"] * MOTOR_SENS * FLEET_K,  # 59.4 N: 40 N.cm motor AND fully fleeted line
    upper_hold_nm=HOLD * MOTOR_SENS,         # 0.40 N.m: most torque the motor can put through the spool joint
)
PASS_RATIO = 1.5


def verdict(lo: float, hi: float | None = None) -> str:
    if hi is not None and lo < 1.0 <= hi:
        return "MAY GIVE FIRST"
    return "PASS" if lo >= PASS_RATIO else ("MARGINAL" if lo >= 1.0 else "GIVES FIRST")


# ===========================================================================
# 1. LINE, KNOTS AND TIE-OFFS
# ===========================================================================
LINE_RATED_LBF = 120.0          # 9KM DWLIFE X8 braided Dyneema, 120 lb [REPO docs/SHOPPING_LIST.md]; diameter to measure
KNOT_EFF = (0.50, 0.90)         # braid knot strength / line strength: 50 % (clinch-type knots in braid) to 90 % (Palomar) [SRC]
MU_LINE_PETG = (0.05, 0.10)     # UHMWPE on PETG [ASSUMED], for the dead wraps at the spool
DEAD_WRAPS = 3                  # wraps never paid out (proposed rule)
CLAW_EYE = dict(d=2.0, wall=5.0, edge=8.0)   # claw housing cable hole Ø2 through a 5 mm wall [REPO CAMBAY1021_CORNER_HOLE_D]; edge [ASSUMED]


def line_links() -> dict:
    rated = LINE_RATED_LBF * LBF
    knot = [rated * e for e in KNOT_EFF]
    capstan = [math.exp(-mu * 2 * math.pi * DEAD_WRAPS) for mu in MU_LINE_PETG]
    # Claw eye: knot behind a washer, two shear planes from the hole to the edge [hand bound, geometry to confirm].
    eye = 2 * (CLAW_EYE["edge"] - CLAW_EYE["d"] / 2) * CLAW_EYE["wall"] * PETG_SHEAR[0]
    return dict(rated=rated, knot_lower=knot[0], knot_upper=knot[1],
                tieoff_share_with_wraps=(min(capstan), max(capstan)), claw_eye=eye)


# ===========================================================================
# 2. SPOOL TO SHAFT: SET SCREW ON THE D-FLAT
# ===========================================================================
# Shaft [REPO cad/params.py]: Ø5.0 with a 0.5 mm flat.  Spool: the 10/21 reference spool in cad/params.py (bore 5.30, flat at
# 2.15 mm from the axis); the v3 Spoolv3 (10/18) had 5.45 / 2.225 [REPO review R4].  Radial M3 set screw on the flat's axis, hub Ø15.
SHAFT_D = P.MOTOR_SHAFT_DIA
SHAFT_FLAT_DEPTH = P.MOTOR_SHAFT_FLAT
BORE_D = P.ENC1021_BORE_D                       # 5.30
BORE_FLAT_DEPTH = BORE_D / 2 - P.ENC1021_BORE_FLAT_X   # 0.50
BORE_V3 = (5.45, 0.50)
HUB_R = 7.5
MU_TIP = 0.20                   # steel cup point on the steel flat, dry [ASSUMED]
MU_BORE = 0.25                  # steel shaft on the PETG bore [ASSUMED]
CUP_BITE = 1.15                 # cup-point penetration adds up to ~15 % holding [SRC Machine Design, set screws]
K_NUT = 0.20                    # torque coefficient, dry steel [ASSUMED]
SEAT_TORQUE_STEEL = (3.0 * 0.113, 4.0 * 0.113)   # N.m: 3-4 in-lb for a #4-40 / M3 cup point in a STEEL thread [SRC]
PETG_SHEAR = (0.58 * S.PETG["yield_derated"], 0.58 * S.PETG["uts"])  # 14.5 to 26 MPa, printed thread shear [ASSUMED]
SEAT_FRACTION = (0.5, 0.8)      # set screws in a plastic thread are seated below the strip force [ASSUMED]
SHORT_INSERT_LEN = 4.0          # mm, a short M3 heat-set insert (the standard 5.7 mm one does not fit the hub wall)
INSERT_PULLOUT = (400.0, 750.0)  # N, short M3 insert in warm PETG [ASSUMED; the bench test measures it]


def setscrew_joint() -> dict:
    r_flat = SHAFT_D / 2 - SHAFT_FLAT_DEPTH          # 2.0 mm: screw tip on the flat
    r_bore = SHAFT_D / 2                             # 2.5 mm: line contact with the bore opposite the screw
    lever = MU_TIP * r_flat + MU_BORE * r_bore       # mm: torque per newton of set-screw force
    wall = HUB_R - (BORE_D / 2 - BORE_FLAT_DEPTH)    # 5.35 mm of hub wall at the screw
    l_e = wall - 0.5                                 # 0.5 mm lead-in
    a_strip = 0.5 * math.pi * 3.0 * l_e              # mm2, internal-thread shear area (about half the cylinder)
    warm = WARM["design"]
    f_strip = [a_strip * t * warm for t in PETG_SHEAR]
    f_seat_petg = [f_strip[0] * SEAT_FRACTION[0], f_strip[1] * SEAT_FRACTION[1]]
    f_seat_steel = [t / (K_NUT * 3.0e-3) for t in SEAT_TORQUE_STEEL]     # what the screw itself can be seated to
    f_seat_insert = [min(f_seat_steel[0], INSERT_PULLOUT[0] * warm), min(f_seat_steel[1], INSERT_PULLOUT[1])]
    cap = lambda f: CUP_BITE * f * lever * 1e-3      # N.m
    return dict(r_flat=r_flat, lever_mm=lever, hub_wall=wall, thread_len=l_e, strip_area=a_strip, f_strip=f_strip,
                f_seat_petg=f_seat_petg, f_seat_steel=f_seat_steel, f_seat_insert=f_seat_insert,
                insert_fits=dict(standard_5p7=wall >= 5.7 + 0.3, short=wall >= SHORT_INSERT_LEN + 0.3),
                torque_petg=[cap(f) for f in f_seat_petg], torque_insert=[cap(f) for f in f_seat_insert],
                dflat_now=dflat_engagement(BORE_D, BORE_FLAT_DEPTH), dflat_v3=dflat_engagement(*BORE_V3))


def dflat_engagement(bore_d: float, bore_flat_depth: float) -> dict:
    """If the set screw slips: how far the shaft turns before its flat corner meets the bore's flat, and the lever of that
    contact. The screw pushes the shaft into the round side of the bore, so the whole clearance sits at the flat. The contact
    is a steel edge on PETG, so it crushes rather than drives (the check's Hertz estimate is 113 to 155 MPa)."""
    r = SHAFT_D / 2
    off = (bore_d - SHAFT_D) / 2
    h_bore = bore_d / 2 - bore_flat_depth + off
    h_shaft = r - SHAFT_FLAT_DEPTH
    a0 = math.acos(h_shaft / r)
    a1 = math.acos(min(1.0, h_bore / r))
    lever = r * math.sin(a1)
    return dict(gap=h_bore - h_shaft, turn_deg=math.degrees(a0 - a1), lever_mm=lever,
                contact_force_at_hold=HOLD / (lever * 1e-3) if lever > 0 else float("inf"),
                across_flat=bore_d - bore_flat_depth, bore=bore_d)


# ===========================================================================
# 3. MOTOR SHAFT AND FRONT BEARING
# ===========================================================================
SHAFT_SY = (350.0, 600.0)       # MPa, stepper shaft yield: plain carbon steel to hardened stainless [ASSUMED]
BRG_IN = 3.0                    # mm, front bearing centre behind the motor's flange face [ASSUMED]
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
        dist = (Y[m] - yc) * c + (Z[m] - zc) * s
        I = (dist ** 2).sum() * dA
        best = min(best, I / np.abs(dist).max())
    return best


def shaft_links() -> dict:
    a = S.Y_DRUM + FIN_T + BRG_IN                            # 24.2 mm: drum mid-plane to the front bearing (fin included)
    Z = dflat_section_modulus()
    f_brg = BRG_C0 * BRG_SPAN / (a + BRG_SPAN)
    return dict(lever=a, Z=Z, Z_round=math.pi * SHAFT_D ** 3 / 32, f_yield=SHAFT_SY[0] * Z / a, f_yield_hi=SHAFT_SY[1] * Z / a,
                f_bearing_static=f_brg, front_bearing_at_fuse=FUSE["upper"] * (a + BRG_SPAN) / BRG_SPAN,
                radial_rating=RADIAL_RATING, run_vs_rating=FUSE["run_empty"] / RADIAL_RATING)


# ===========================================================================
# 4. MOTOR TO TAB: 4 x M3 x 12 (D38) through the PETG tab and the fin into the motor's aluminium front cap
# ===========================================================================
M3_ENGAGE = 3.8                 # mm thread in the motor with the 5 mm tab and the 1/8 in fin [REPO D38]
AL_SHEAR = 120.0                # MPa, die-cast / 6061 aluminium shear (lower) [ASSUMED]
HEAD_D, HOLE_D = P.THERMAL_SCREW_HEAD_D, P.THERMAL_TAB_HOLE_D
SCREW_PATTERN = P.NEMA17_HOLES


def motor_screw_links(tab_t: float = 5.0) -> dict:
    engage = M3_ENGAGE - (tab_t - 5.0)                                 # a thicker tab leaves less thread in the motor
    strip_al = 0.6 * math.pi * 3.0 * engage * AL_SHEAR                # N per screw
    punch = math.pi * HEAD_D * tab_t * PETG_SHEAR[0] * WARM["design"]  # head punching through the warm tab, N per screw
    per_screw_per_N = (S.Y_DRUM + FIN_T) / (2 * SCREW_PATTERN)         # tension per screw per N of line (pivot on one row)
    cap = min(strip_al, punch)
    return dict(engage=engage, strip_al=strip_al, punch=punch, per_screw_per_N=per_screw_per_N,
                f_line=cap / per_screw_per_N, f_line_hi=max(strip_al, punch) / per_screw_per_N,
                at_fuse=FUSE["upper"] * per_screw_per_N)


# ===========================================================================
# 5. MOTOR TAB: root section, each face with its own root detail, over every reachable cable direction
# ===========================================================================
# Root section of the tab (normal x): thickness t along y (back face y = 0 against the fin, spool-side face y = t), width
# b = 42.3 along z.  Back-side root: sharp corner as drawn (Kt 2.5); spool-side root: R2.5 fillet as drawn (Kt 1.5).  A 2 mm
# fillet on the back root makes that side Kt 1.5 too.  Kt values follow the static manual's band [ASSUMED].
TAB_B = 42.3
TAB_X_ROOT = -21.15
KT = dict(sharp=2.5, fillet=1.5)
PETG_LAYER = S.Z_STRENGTH       # 22.5 MPa across layers [REPO review R5]


def tab_face_stress(F: np.ndarray, p: np.ndarray, t: float) -> dict:
    """Stresses per newton... at the root for force F (N) at load point p (mm, station frame, y measured from the tab's
    back face).  sigma_x = Fx/A - Mz*y'/Iz + My*z/Iy (y' from the mid-plane), worst corner in z; shear: transverse + torsion."""
    A = TAB_B * t
    Iy = t * TAB_B ** 3 / 12.0
    Iz = TAB_B * t ** 3 / 12.0
    r = np.array([p[0] - TAB_X_ROOT, p[1] - t / 2, p[2]])
    M = np.cross(r, F)
    bend_z = abs(M[1]) * (TAB_B / 2) / Iy
    back = F[0] / A - M[2] * (-t / 2) / Iz + bend_z
    front = F[0] / A - M[2] * (t / 2) / Iz + bend_z
    tau = max(1.5 * abs(F[1]) / A, 1.5 * abs(F[2]) / A) + abs(M[0]) / (0.312 * TAB_B * t * t)
    return dict(back=back, front=front, tau=tau)


def tab_gives_at(u: np.ndarray, t: float, kt_back: float, kt_front: float, warm: float) -> tuple[float, str]:
    """Cable tension along unit vector u at which the first root detail reaches the warm allowable."""
    p = S.tangent_point(u)
    s = tab_face_stress(u, p, t)          # per newton of cable
    worst = (float("inf"), "")
    for face, kt in (("back", kt_back), ("front", kt_front)):
        sig = max(s[face], 0.0)
        vm = math.sqrt(sig ** 2 + 3 * s["tau"] ** 2)
        f_vm = S.PETG["yield_derated"] * warm / (kt * vm)
        f_layer = PETG_LAYER * warm / (kt * sig) if sig > 0 else float("inf")
        f = min(f_vm, f_layer)
        if f < worst[0]:
            worst = (f, face)
    return worst


def reachable_directions() -> list:
    """Every cable direction the bare drum allows: polar angle 0 to 84 deg, azimuth -90 to 90 deg, fleet clipped."""
    out = []
    for th in np.arange(0.0, 84.1, 3.0):
        for ps in np.arange(-90.0, 90.1, 7.5):
            u, k = S.clip_fleet(S.unit_vector(th, ps))
            out.append((float(th), float(ps), u / np.linalg.norm(u), k))
    return out


def tab_links() -> dict:
    dirs = reachable_directions()
    variants = {
        "5 mm, as drawn": (5.0, KT["sharp"], KT["fillet"]),
        "5 mm, 2 mm back fillet": (5.0, KT["fillet"], KT["fillet"]),
        "6 mm, fillets both roots": (6.0, KT["fillet"], KT["fillet"]),
        "7 mm, fillets both roots": (7.0, KT["fillet"], KT["fillet"]),
    }
    out = {}
    for name, (t, kb, kf) in variants.items():
        rows = {}
        for cond, warm in (("room", 1.0), *WARM.items()):
            best = min(((tab_gives_at(u, t, kb, kf, warm), th, ps) for th, ps, u, k in dirs), key=lambda x: x[0][0])
            (f, face), th, ps = best
            rows[cond] = dict(f=f, face=face, theta=th, psi=ps)
        out[name] = rows
    # Static-manual criterion at 1.5 A: SF on the 25 MPa derated yield at the slip force, along-wall reachable case D4f
    u4 = S.fleet_limited_case()
    sf = {}
    for name, (t, kb, kf) in variants.items():
        f, face = tab_gives_at(u4, t, kb, kf, 1.0)
        sf[name] = f / FUSE["slip_fleet"]
    return dict(variants=out, sf_at_slip_D4f=sf)


def retention_link() -> dict:
    # Dovetail flank bearing 0.053 MPa at the D3 pull-away of 33.3 N (manual section 9): linear.
    bearing_per_N = 0.053 / 33.3
    return dict(bearing_at_fuse=bearing_per_N * FUSE["upper"], f_line=S.PETG["yield_derated"] * WARM["design"] / bearing_per_N)


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
DRYWALL_ONLY = dict(bare=(5 * LBF, 10 * LBF), plastic_anchor=(10 * LBF, 25 * LBF))   # tension [SRC]
COL_Y = S.SCREW_COLS_Y
PLATE_Y = (-94.44, 125.56)      # mm, wall mount plate edges [REPO manual W1]


def withdrawal(screw: str, species: str, inches: float = THREAD_IN_STUD_IN) -> dict:
    g = SPECIES_G[species]
    d = SCREW_D_IN[screw]
    return dict(design=2850 * g * g * d * inches * LBF, ultimate=15700 * g * g * d * inches * LBF)


def screw_lateral(screw: str = "#6") -> float:
    """Screw bent in double curvature across the drywall gap (PETG plate clamped, stud holds the other end)."""
    dr = SCREW_ROOT_IN[screw] * INCH
    return 2 * FYB * dr ** 3 / 6.0 / DRYWALL_T


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
    rows = {}
    for cid, label, u, T, p in reach:
        s6, s3 = screws_six(T * u, p), screws_one_column(T * u, p)
        rows[cid] = dict(T=T, six_t=s6["t_top"], six_v=s6["shear"], one_t=s3["t_top"], one_v=s3["shear"],
                         one_t_at_upper=screws_one_column(FUSE["upper"] * u, p)["t_top"],
                         f_design_one=solve_line_force(screws_one_column, u, p, w["design"]),
                         f_ult_one=solve_line_force(screws_one_column, u, p, w["ultimate"]),
                         f_design_six=solve_line_force(screws_six, u, p, w["design"]),
                         f_bare_drywall=solve_line_force(screws_six, u, p, DRYWALL_ONLY["bare"][0]),
                         f_bare_drywall_hi=solve_line_force(screws_six, u, p, DRYWALL_ONLY["bare"][1]),
                         f_plastic_anchor=solve_line_force(screws_six, u, p, DRYWALL_ONLY["plastic_anchor"][0]))
    worst = min(rows, key=lambda c: rows[c]["f_design_one"])
    worst_dw = min(rows, key=lambda c: rows[c]["f_bare_drywall"])
    table = {f"{s} in {sp}": withdrawal(s, sp) for s in SCREW_D_IN for sp in SPECIES_G}
    punch = math.pi * HEAD_6_D * PLATE_T * PETG_SHEAR[0]        # wall plate is away from the motor: room temperature
    cid, label, u, T, p = [c for c in reach if c[0] == worst][0]
    return dict(per_case=rows, worst=worst, worst_drywall=worst_dw, withdrawal_6_spf=w, lateral_6=screw_lateral("#6"),
                table_1in=table, head_punch=punch, f_head_punch=solve_line_force(screws_one_column, u, p, punch))


def stud_bending() -> dict:
    """A 2 x 4 stud (1.5 x 3.5 in, SPF) loaded at mid-height by the worst pull-away, simply supported over 2.44 m.
    The station is near the top plate, so this is an upper bound on the stud's own stress."""
    S_x = (1.5 * INCH) * (3.5 * INCH) ** 2 / 6.0 * 1e-9        # m3
    sigma = (FUSE["upper"] * 2.44 / 4.0) / S_x / 1e6           # MPa
    return dict(F=FUSE["upper"], sigma=sigma, Fb_ref=875 * 0.006895)      # SPF No. 2 reference bending, 875 psi [SRC]


# ===========================================================================
# 7. ENCODER DETECTION OF A SLIP
# ===========================================================================
def detection() -> dict:
    cfg = json.loads((S.ROOT / "config" / "robot.sim.json").read_text())
    tol = cfg["faults"]["tracking_tol_counts"]                  # simulation profile; hardware configs leave it null
    dwell = cfg["faults"]["tracking_dwell_s"]
    cpr = 4096                                                  # AS5600 [REPO EncoderConfig]
    skip_deg = 4 * 360.0 / 200                                  # a stepper loses steps in whole electrical cycles: 4 full steps
    skip_counts = skip_deg / 360.0 * cpr
    return dict(tol_counts=tol, tol_deg=tol * 360.0 / cpr, dwell_s=dwell, skip_deg=skip_deg, skip_counts=skip_counts,
                line_per_skip_mm=math.radians(skip_deg) * S.R_EMPTY * 1e3, margin=skip_counts / tol,
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
    ww = wall["per_case"][wall["worst"]]
    dw = wall["per_case"][wall["worst_drywall"]]
    t_need = FUSE["upper_hold_nm"]
    tv = tab["variants"]
    to_line = 1.0 / S.R_EMPTY                    # N of straight cable on the empty core per N.m through the spool joint
    links = [   # name, lower, upper (cable tension, N), (ratio low, ratio high) or None, basis
        ("Motor torque (the fuse)", FUSE["slip_low"], FUSE["upper"], None,
         "holding torque / spool radius; 33.9 N (1/sqrt2 vector) to 59.4 N (40 N.cm motor, fleeted cable)"),
        ("Spool set screw in the printed thread (as drawn)", ss["torque_petg"][0] * to_line, ss["torque_petg"][1] * to_line,
         (ss["torque_petg"][0] / t_need, ss["torque_petg"][1] / t_need),
         f"{ss['torque_petg'][0]:.2f} to {ss['torque_petg'][1]:.2f} N.m against {t_need:.2f} N.m; seat force capped by the warm PETG thread"),
        ("Motor tab, 5 mm, sharp back corner (as drawn)", tv["5 mm, as drawn"]["design"]["f"], tv["5 mm, as drawn"]["room"]["f"], None,
         f"{tv['5 mm, as drawn']['design']['face']} root governs; warm x{WARM['design']}; room temperature {tv['5 mm, as drawn']['room']['f']:.0f} N"),
        ("Motor tab, 5 mm with a 2 mm back fillet", tv["5 mm, 2 mm back fillet"]["design"]["f"], tv["5 mm, 2 mm back fillet"]["room"]["f"], None,
         f"spool-side R2.5 fillet governs; room temperature {tv['5 mm, 2 mm back fillet']['room']['f']:.0f} N"),
        ("Spool set screw in a short insert or nut", ss["torque_insert"][0] * to_line, ss["torque_insert"][1] * to_line,
         (ss["torque_insert"][0] / t_need, ss["torque_insert"][1] / t_need),
         f"{ss['torque_insert'][0]:.2f} to {ss['torque_insert'][1]:.2f} N.m; seat force capped by the insert's pull-out (400 to 750 N assumed)"),
        ("Motor tab, 6 mm with fillets on both roots", tv["6 mm, fillets both roots"]["design"]["f"], tv["6 mm, fillets both roots"]["room"]["f"], None,
         f"room temperature {tv['6 mm, fillets both roots']['room']['f']:.0f} N; M3 x 12 then has {motor_screw_links(6.0)['engage']:.1f} mm of thread"),
        ("Motor shaft, bending yield at the D-flat", sh["f_yield"], sh["f_yield_hi"], None,
         f"350 to 600 MPa x Z {sh['Z']:.2f} mm3 / {sh['lever']:.1f} mm (fin included); bearing static {sh['f_bearing_static']:.0f} N"),
        ("Line knot (120 lb braid)", line["knot_lower"], line["knot_upper"], None, "50 to 90 % knot efficiency"),
        ("Wall screws, 3 x #6 in one stud column", ww["f_design_one"], ww["f_ult_one"], None,
         f"top screw at the NDS design value (lower, includes the code's ~5 x factor) and the test ultimate (upper)"),
        ("Claw cable eye, knot behind a washer", line["claw_eye"], line["claw_eye"] * PETG_SHEAR[1] / PETG_SHEAR[0], None,
         "two shear planes, Ø2 hole in a 5 mm wall, 8 mm edge (assumed)"),
        ("Motor screws, 4 x M3 x 12 into the motor", ms["f_line"], ms["f_line_hi"], None,
         "head punching through the warm 5 mm tab; thread strip in the aluminium cap"),
        ("Wall plate: screw head pulls through the PETG", wall["f_head_punch"], wall["f_head_punch"] * PETG_SHEAR[1] / PETG_SHEAR[0], None,
         f"#6 head punching through {PLATE_T} mm of PETG, {wall['head_punch']:.0f} N per screw"),
        ("Slide-in dovetails and lips", ret["f_line"], ret["f_line"] * 2, None, f"flank bearing {ret['bearing_at_fuse']:.2f} MPa at the fuse"),
    ]
    rows = []
    for name, lo, hi, rt, basis in links:
        r_lo, r_hi = rt if rt is not None else (lo / FUSE["upper"], hi / FUSE["upper"])
        is_fuse = name.startswith("Motor torque")
        rows.append(dict(link=name, lower=lo, upper=hi, ratio=r_lo, ratio_hi=r_hi,
                         verdict="FUSE" if is_fuse else verdict(r_lo, r_hi if rt is not None else None), basis=basis))
    comparison = dict(link="Six wall screws in drywall only (no stud)", lower=dw["f_bare_drywall"], upper=dw["f_bare_drywall_hi"],
                      ratio=dw["f_bare_drywall"] / FUSE["upper"], verdict="GIVES FIRST")
    return dict(fuse=FUSE, design_force=DESIGN_FORCE, jeans_peak=JEANS_PEAK, warm=WARM, line=line, setscrew=ss, shaft=sh,
                motor_screws=ms, tab=tab, retention=ret, wall=wall, stud=stud, detection=det, ranking=rows, drywall=comparison,
                torque_needed_nm=t_need, pass_ratio=PASS_RATIO, fleet_deg=FLEET_DEG)


def report(r: dict) -> None:
    f = r["fuse"]
    print("=" * 100)
    print("WEAKEST LINK OF THE LIFTING CHAIN, ONE STATION AT 1.5 A")
    print("=" * 100)
    print("\n0. Demand and the fuse (cable tension, N)")
    print(f"  design force (full spool, 1.5 skip margin)      {r['design_force']:6.1f}")
    print(f"  jeans case, worst cable (1.50 kg x 1.101 x g)    {r['jeans_peak']:6.1f}")
    print(f"  motor skips while moving: full / empty spool     {f['run_full']:6.1f} / {f['run_empty']:.1f}")
    print(f"  motor slips while holding: full / empty spool    {f['slip_full']:6.1f} / {f['slip_empty']:.1f}   (hold {f['hold_nm']:.3f} N.m)")
    print(f"  lower bound (1/sqrt2 current vector)             {f['slip_low']:6.1f}")
    print(f"  fully fleeted cable ({r['fleet_deg']:.1f} deg): / cos           {f['slip_fleet']:6.1f}")
    print(f"  UPPER (40 N.cm motor and fleeted cable)          {f['upper']:6.1f}   <- every other link must give above this")
    print(f"  fuse / jeans demand: {f['slip_empty']/r['jeans_peak']:.2f} holding, {f['run_full']/r['jeans_peak']:.2f} moving at a full spool")
    print(f"  warm PETG factor: design {r['warm']['design']} (1/8 in fin), prototype {r['warm']['prototype']} (0.019 in fin)")

    L = r["line"]
    print(f"\n1. Line: rated 120 lb = {L['rated']:.0f} N; knot {L['knot_lower']:.0f} to {L['knot_upper']:.0f} N; with {DEAD_WRAPS} dead wraps "
          f"the spool tie-off sees {L['tieoff_share_with_wraps'][0]*100:.0f} to {L['tieoff_share_with_wraps'][1]*100:.0f} %; claw eye {L['claw_eye']:.0f} N")

    s = r["setscrew"]
    print("\n2. Spool on the shaft (set screw on the D-flat), 10/21 spool (bore 5.30)")
    print(f"  torque per N of set-screw force {s['lever_mm']:.3f} mm, x{CUP_BITE} cup bite; hub wall at the screw {s['hub_wall']:.2f} mm "
          f"(standard 5.7 mm insert fits: {s['insert_fits']['standard_5p7']}, short 4 mm insert fits: {s['insert_fits']['short']})")
    print(f"  printed thread (warm): strips at {s['f_strip'][0]:.0f} to {s['f_strip'][1]:.0f} N, seated {s['f_seat_petg'][0]:.0f} to "
          f"{s['f_seat_petg'][1]:.0f} N -> {s['torque_petg'][0]:.2f} to {s['torque_petg'][1]:.2f} N.m (motor can apply {r['torque_needed_nm']:.2f})")
    print(f"  short insert or nut: seat force {s['f_seat_insert'][0]:.0f} to {s['f_seat_insert'][1]:.0f} N (steel-rated {s['f_seat_steel'][0]:.0f} to "
          f"{s['f_seat_steel'][1]:.0f}, pull-out {INSERT_PULLOUT[0]:.0f} to {INSERT_PULLOUT[1]:.0f}) -> {s['torque_insert'][0]:.2f} to {s['torque_insert'][1]:.2f} N.m")
    for k in ("dflat_now", "dflat_v3"):
        d = s[k]
        print(f"  D-flat backup, bore {d['bore']:.2f} ({d['across_flat']:.2f} across the flat): gap {d['gap']:.2f} mm, engages after {d['turn_deg']:.1f} deg "
              f"at {d['lever_mm']:.2f} mm from the axis -> {d['contact_force_at_hold']:.0f} N of steel-edge contact on PETG at 0.36 N.m")

    h = r["shaft"]
    print(f"\n3. Shaft: lever {h['lever']:.1f} mm, Z(D-flat) {h['Z']:.2f} mm3 (round {h['Z_round']:.2f}); yield at {h['f_yield']:.0f} to "
          f"{h['f_yield_hi']:.0f} N; bearing static {h['f_bearing_static']:.0f} N; running pull at the core {h['run_vs_rating']:.2f} x the 28 N life rating")

    m = r["motor_screws"]
    print(f"\n4. Motor screws: Al strip {m['strip_al']:.0f} N, warm head punch {m['punch']:.0f} N per screw; {m['per_screw_per_N']:.2f} N per N of cable")

    print("\n5. Motor tab (worst reachable direction; cable tension at which the first root detail reaches the allowable)")
    for name, rows in r["tab"]["variants"].items():
        cells = "; ".join(f"{c} {v['f']:.0f} N ({v['face']}, theta {v['theta']:.0f} psi {v['psi']:+.0f})" for c, v in rows.items())
        print(f"  {name:<28} {cells}")
    print("  static manual's SF on 25 MPa at the 1.5 A slip force, along-wall D4f: " +
          ", ".join(f"{k} {v:.2f}" for k, v in r["tab"]["sf_at_slip_D4f"].items()))
    print(f"  slide-in dovetails: {r['retention']['bearing_at_fuse']:.3f} MPa at the fuse")

    w = r["wall"]
    print(f"\n6. Wall: #6 in SPF, 1 in of thread: design {w['withdrawal_6_spf']['design']:.0f} N, ultimate {w['withdrawal_6_spf']['ultimate']:.0f} N; "
          f"lateral {w['lateral_6']:.0f} N per screw")
    for cid, c in w["per_case"].items():
        print(f"  {cid:<4} at {c['T']:.1f} N: top screw {c['six_t']:.1f} N (6) / {c['one_t']:.1f} N (one column), {c['one_t_at_upper']:.1f} N at the fuse upper; "
              f"one column at design {c['f_design_one']:.0f} N, ultimate {c['f_ult_one']:.0f} N; bare drywall {c['f_bare_drywall']:.0f} N")
    print(f"  stud bending at the fuse (upper bound): {r['stud']['sigma']:.2f} MPa vs {r['stud']['Fb_ref']:.1f} MPa reference")
    for k, v in w["table_1in"].items():
        print(f"    {k:<26} {v['design']:6.0f} / {v['ultimate']:6.0f} N per inch of thread")

    d = r["detection"]
    print(f"\n7. Encoder: tracking fault at {d['tol_counts']} counts ({d['tol_deg']:.1f} deg, {d['tol_line_mm']:.2f} mm of cable) held {d['dwell_s']} s; "
          f"one skip = {d['skip_deg']:.1f} deg = {d['skip_counts']:.0f} counts = {d['line_per_skip_mm']:.2f} mm (margin {d['margin']:.2f}); "
          f"hardware configs must set a tolerance below {d['skip_counts']:.0f}")

    print("\nRANKING at the design condition (cable tension at which each link gives, N; ratio = lower / %.1f N, torque links N.m / N.m)" % f["upper"])
    for x in sorted(r["ranking"], key=lambda x: x["lower"]):
        print(f"  {x['link']:<52} {x['lower']:7.0f} to {x['upper']:7.0f}   {x['ratio']:5.2f}  {x['verdict']}")
    c = r["drywall"]
    print(f"  ({c['link']}: {c['lower']:.0f} to {c['upper']:.0f} N, {c['ratio']:.2f}, {c['verdict']})")


def main() -> None:
    r = build()
    report(r)
    OUT_JSON.write_text(json.dumps(r, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))
    print(f"\nwrote {OUT_JSON.relative_to(S.ROOT)}")


if __name__ == "__main__":
    main()
