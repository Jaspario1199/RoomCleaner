"""
Loads, boundary values and hand-calc targets for the two SolidWorks Simulation
studies Jasper runs for the interview presentation:

  (A) linear static stress of the winch-station wall mount + slide-in housing
      -> docs/simulation/SW_STATIC_STATION_MOUNT.md
  (B) steady-state thermal of the aluminium motor heat fin
      -> docs/simulation/SW_THERMAL_HEAT_FIN.md

Every number the two manuals quote is printed here as a table with its source.
Tags: [REPO] taken from a repo file/decision, [USER] stated in the task brief,
[STEP] measured from the STEP files, [CALC] derived here, [ASSUMED] a flagged
assumption to replace by a measurement.

    /usr/bin/python3 -m calculations.simulation_loads            # everything
    /usr/bin/python3 -m calculations.simulation_loads --no-step  # skip STEP reads
    /usr/bin/python3 -m calculations.simulation_loads --static   # study A only
    /usr/bin/python3 -m calculations.simulation_loads --thermal  # study B only

Companions: calculations/gen2_screening.py, gen2_payload_limit.py (tension
conventions), gen2_motor_thermal.py (two-node motor model used for coupling),
verification/design_review_gen2.md (R3, R6, R10, R11), DECISIONS.md D15/D26/D29/D30.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ASM_STEP = ROOT / "solidworks" / "v3_assembly_2026-10-19" / "Assem_laundry_v3.STEP"
G = 9.81
SIGMA_SB = 5.670374e-8      # W/m^2K^4

# ===========================================================================
# 1. MOTOR, CURRENT AND CABLE TENSION CASES
# ===========================================================================
# Holding torque: the repo uses ONE number everywhere (SIMAX3D 42-38, 36 N.cm at
# the rated 1.5 A: docs/SHOPPING_LIST.md, review R10, calculations/gen2_*.py).
# The task brief names the 17HS4401 at ~40 N.cm; the repo holds no datasheet for
# the 17HS4401 (DESIGN_STATE.md only says the D-flat was seen on "the 17HS4401s").
# We USE 36 N.cm so that the loads equal the authoritative 32 N / 48 N figures
# (DESIGN_STATE.md "Structural design load per cable", D30's "~34 N") and show
# 40 N.cm as a +11 % sensitivity that scales every load and result linearly.
HOLD_36 = 0.36              # N.m at 1.5 A  [REPO]
HOLD_40 = 0.40              # N.m at 1.5 A  [USER] 17HS4401 nameplate, unverified here
I_RATED = 1.5               # A [REPO]
VREF = 0.85                 # V measured carrier maximum [REPO D30]
R_SENSE = 0.100             # ohm, red R100 A4988 [REPO D29/D30]
I_SET = VREF / (8.0 * R_SENSE)          # A, A4988: Vref = 8 * I * Rsense
RUN_FRAC = 0.7              # running / holding torque [REPO gen2_payload_limit.py, R10]
R_EMPTY = 7.5e-3            # m, measured Spoolv3 core [REPO R4]
R_FULL = 10.0e-3            # m, 20 ft of line, 5 layers [REPO R4]
SKIP_SF = 1.5               # [REPO gen2_payload_limit.py]
DYN_FACTOR = 2.0            # [REPO R10 "x2 dynamic"]


def hold_torque(i_amp: float, hold_rated: float = HOLD_36) -> float:
    """Holding torque scales ~linearly with current (same convention as the repo)."""
    return hold_rated * i_amp / I_RATED


def tension_cases(i_amp: float = I_SET, hold_rated: float = HOLD_36) -> dict:
    hold = hold_torque(i_amp, hold_rated)
    slip = hold / R_EMPTY                       # stepper slip limit, empty spool
    run_full = RUN_FRAC * hold / R_FULL         # most the winch can pull while moving
    return dict(hold=hold, slip=slip, work=run_full, work_margin=run_full / SKIP_SF,
                work_core=RUN_FRAC * hold / R_EMPTY, dyn=DYN_FACTOR * slip)


# ===========================================================================
# 2. LINE DIRECTIONS AND WHERE THE FORCE ENTERS
# ===========================================================================
# Station frame (same axes as cad/reference/station_v3/extract.py and
# cad/parts/station_cover_v4.py): origin on the motor shaft axis at the motor
# flange face; +x out of the wall into the room; +y along the shaft toward the
# spool (horizontal, parallel to the wall); +z up.  It is the assembly STEP
# frame translated by O, so force COMPONENTS are identical in both frames.
O_ASM = np.array([1269.0842, 738.7616, 927.5570])    # mm [REPO extract.py]
Y_DRUM = 18.0       # mm, drum mid-plane (22 mm spool symmetric about y = 7..29)  [ASSUMED]
# Directions: polar angle theta from straight-down, azimuth psi from +x toward +y.
THETA_FLOOR = 43.9      # deg [USER; docs/presentation/DECISION_STORIES.md T18: 43.877]
THETA_SCAN = 78.7       # deg [USER; T18: 78.690]
CASES = [   # id, label, theta, psi, comment
    ("D1", "straight down",                      0.0,         0.0,  "claw under the station"),
    ("D2", "floor-centre diagonal",              THETA_FLOOR, 45.0, "room diagonal, cone angle from T18"),
    ("D3", "scan, straight out from the wall",   THETA_SCAN,  0.0,  "max pull-away, claw high at the room centre"),
    ("D4", "scan, along the wall toward -y",     THETA_SCAN, -90.0,  "bound: pure sideways, motor side"),
    ("D5", "scan, along the wall toward +y",     THETA_SCAN,  90.0,  "bound: pure sideways, spool side (optional)"),
]


def unit_vector(theta_deg: float, psi_deg: float) -> np.ndarray:
    t, p = math.radians(theta_deg), math.radians(psi_deg)
    return np.array([math.sin(t) * math.cos(p), math.sin(t) * math.sin(p), -math.cos(t)])


def tangent_point(u: np.ndarray, r_mm: float = R_EMPTY * 1e3) -> np.ndarray:
    """Line leaves the drum tangentially on the room (+x) side. The in-plane
    (x-z) projection of u is perpendicular to the radius to the tangent point."""
    h = math.hypot(u[0], u[2])
    n = np.array([-u[2] / h, 0.0, u[0] / h])
    p = r_mm * n
    p[1] = Y_DRUM
    return p


def fleet_limit_deg() -> float:
    """Largest fleet angle (line vs the plane normal to the shaft) before the line scrubs a
    spool flange: drum 16 mm wide between flanges of r = 18 mm [STEP Spoolv3], line leaving
    from the drum mid-plane (8 mm to each flange), tangent to the r = 7.5 mm core."""
    s_xy = math.sqrt(18.0 ** 2 - (R_EMPTY * 1e3) ** 2)
    return math.degrees(math.atan(8.0 / s_xy))


def fleet_limited_case(theta_deg: float = THETA_SCAN, sign: int = -1) -> np.ndarray:
    """Direction D4f: same cone angle as D3/D4/D5 but the along-shaft share capped at the fleet limit."""
    a = math.radians(fleet_limit_deg())
    t = math.radians(theta_deg)
    inplane = np.array([math.sin(t), 0.0, -math.cos(t)]) * math.cos(a)
    return inplane + np.array([0.0, sign * math.sin(a), 0.0])


def clip_fleet(u: np.ndarray) -> tuple[np.ndarray, float]:
    """Clip the along-shaft component of u to the fleet limit, keeping the in-plane direction.
    Returns the clipped unit vector and the tension factor 1/cos(fleet): at the SAME shaft torque
    the line tension is T = slip / cos(fleet), because only the in-plane share turns the drum."""
    a = math.radians(fleet_limit_deg())
    sy = math.sin(a)
    if abs(u[1]) <= sy:
        return np.array(u, float), 1.0
    h = math.hypot(u[0], u[2])
    k = math.cos(a) / h
    return np.array([u[0] * k, math.copysign(sy, u[1]), u[2] * k]), 1.0 / math.cos(a)


def reachable_cases(t: dict) -> list:
    """The cases the line can actually take with a bare drum between 18 mm flanges.
    id, label, unit vector, tension at the slip-limit torque (N), load point (mm)."""
    out = []
    u1 = unit_vector(0.0, 0.0)
    out.append(("D1", "straight down", u1, t["slip"], tangent_point(u1)))
    uc, f = clip_fleet(unit_vector(THETA_FLOOR, 45.0))
    out.append(("D2c", "floor-centre diagonal, fleet-clipped", uc, t["slip"] * f, tangent_point(uc)))
    u3 = unit_vector(THETA_SCAN, 0.0)
    out.append(("D3", "scan, straight out", u3, t["slip"], tangent_point(u3)))
    u4 = fleet_limited_case()
    out.append(("D4f", "along the wall toward -y, reachable", u4, t["slip"] / math.cos(math.radians(fleet_limit_deg())),
                tangent_point(u4)))
    return out


def real_room_angles() -> dict:
    """Same angles for the real 11 x 9 x 9 ft room (config/robot.sim.json): the
    43.9 / 78.7 deg figures belong to the old 4 x 3 x 2.6 m default room (T18)."""
    ft = 0.3048
    L, W, H = 11 * ft, 9 * ft, 9 * ft
    a = (0.05, 0.05, H - 0.15)                      # station A anchor [REPO config]
    out = {}
    floor_c = (L / 2, W / 2, 0.0)
    d = np.array(floor_c) - np.array(a)
    out["floor centre (z = 0)"] = math.degrees(math.atan2(math.hypot(d[0], d[1]), -d[2]))
    far = (L - 0.2, W - 0.2, a[2] - 0.4)            # wall margin 0.2, ceiling margin 0.4 [REPO D26]
    d = np.array(far) - np.array(a)
    out["far corner at ceiling margin"] = math.degrees(math.atan2(math.hypot(d[0], d[1]), -d[2]))
    near = (L / 2, W / 2, a[2] - 0.4)
    d = np.array(near) - np.array(a)
    out["room centre at ceiling margin"] = math.degrees(math.atan2(math.hypot(d[0], d[1]), -d[2]))
    # default sim room used in T18 (4 x 3 x 2.6 m, anchor at the ceiling corner)
    out["T18 room: floor centre"] = math.degrees(math.atan2(math.hypot(2.0, 1.5), 2.6))
    out["T18 room: 2.1 m scan height"] = math.degrees(math.atan2(math.hypot(2.0, 1.5), 0.5))
    return out


# ===========================================================================
# 3. MATERIAL, ALLOWABLES, DEFLECTION LIMIT
# ===========================================================================
PETG = dict(E=1800.0, nu=0.38, rho=1270.0, uts=45.0, yield_derated=25.0)   # MPa, kg/m3 [REPO SIMULATION_GUIDE.md]
SF_STATIC = 3.0         # [REPO SIMULATION_GUIDE.md]
SF_DYNAMIC = 1.5        # [REPO SIMULATION_GUIDE.md]
Z_STRENGTH = 0.5 * 45.0  # MPa across layers = 50 % of UTS [REPO review R5 PETG allowable 22.5]
HOT_DERATE = 0.7        # [ASSUMED] PETG strength factor for a ~55 C motor-warmed tab (verify)
K_LINE = 3.0            # N/mm, Dyneema 0.5 mm over ~3 m [REPO review R1 estimate]
EXIT_LIMIT_MM = 0.5     # proposed, see deflection_limit()
CLEARANCE_PLAY_MM = 0.30  # total x or y play in the drawn slot/dovetail fits [STEP]


def allowables() -> dict:
    y = PETG["yield_derated"]
    return dict(
        vm_static=y / SF_STATIC,            # 8.33 MPa at the slip-limit load
        vm_dynamic=y / SF_DYNAMIC,          # 16.7 MPa at 2 x slip-limit (the same criterion)
        p1_layer=Z_STRENGTH / SF_STATIC,    # 7.5 MPa first principal across layers
        vm_hot=y * HOT_DERATE / SF_STATIC,
    )


def deflection_limit(t: dict) -> dict:
    k_station = t["slip"] / EXIT_LIMIT_MM
    return dict(limit_slip=EXIT_LIMIT_MM, limit_work=EXIT_LIMIT_MM * t["work"] / t["slip"],
                k_station=k_station, ratio_to_line=k_station / K_LINE,
                added_compliance_pct=100.0 * (1.0 / k_station) / (1.0 / K_LINE + 1.0 / k_station),
                line_stretch_work=t["work"] / K_LINE)


# ===========================================================================
# 4. STRUCTURAL HAND ESTIMATES (sanity band for the FEA, not requirements)
# ===========================================================================
TAB = dict(b=42.3, t=5.0, x_root=-21.15, y_c=2.5, z_c=0.0)     # motor tab root section: 5.0 thick x 42.3 wide (z +-21.15) [STEP]
SCREW_ROWS_Z = (-34.75, 10.25, 55.25)                          # wall screw rows, station z [STEP]
SCREW_COLS_Y = (-2.78, 34.22)
WALL_X = -42.31                                                # wall plane (back face) [STEP]
M_MOTOR, M_SHELL = 0.28, 0.25      # kg: motor [REPO guide 0.28], shell + electronics [ASSUMED, weigh it]
P_MOTOR = np.array([0.0, -19.0, 0.0])   # motor centre of mass (38 mm body behind the flange)
P_SHELL = np.array([39.0, 15.6, 8.0])   # shell centroid, mm [STEP bbox centre]
V_WALL_MM3, V_SLIPIN_MM3 = 602284.0, 217693.0   # [STEP] assembly solids, 100 % solid
SELF_WEIGHT_N = (V_WALL_MM3 + V_SLIPIN_MM3) * 1e-9 * PETG["rho"] * G   # 10.2 N: the two meshed PETG bodies
REMOTE_WEIGHT_N = (M_MOTOR + 0.01 + M_SHELL) * G                        # 5.30 N: motor+spool and shell+electronics


def expected_reaction(F_line: np.ndarray) -> np.ndarray:
    """Sum of the fixture reactions the FEA must show (P5): minus the line force, the 5.30 N remote
    weights and the 10.2 N self-weight of the wall mount and slide-in."""
    return -(np.asarray(F_line, float) + np.array([0.0, 0.0, -(REMOTE_WEIGHT_N + SELF_WEIGHT_N)]))


def tab_root_estimate(F: np.ndarray, P: np.ndarray, E: float = PETG["E"]) -> dict:
    """Cantilever estimate of the root stress of the 5 mm PETG motor tab with a rigid motor. The force
    F (N) acts at P (mm, station frame). Root section: normal x, thickness t in y,
    width b in z (strong axis y, weak axis z)."""
    b, t = TAB["b"], TAB["t"]
    A = b * t
    Iy = t * b ** 3 / 12.0       # bending about y (stress varies along z)
    Iz = b * t ** 3 / 12.0       # bending about z (stress varies along y: THIN direction)
    r = np.array([P[0] - TAB["x_root"], P[1] - TAB["y_c"], P[2] - TAB["z_c"]])
    M = np.cross(r, F)           # N.mm about the root centroid
    sig = abs(F[0]) / A + abs(M[1]) * (b / 2) / Iy + abs(M[2]) * (t / 2) / Iz
    tau = max(1.5 * abs(F[1]) / A, 1.5 * abs(F[2]) / A) + abs(M[0]) / (0.312 * b * t * t)
    vm = math.sqrt(sig ** 2 + 3 * tau ** 2)
    d = tab_displacement(F, P, E)
    ex = tab_exit_estimate(F, P, E)
    return dict(sigma_nom=sig, tau_nom=tau, vm_nom=vm, M=M, defl_total=d["load_point_total"],
                defl_along=d["load_point_along"], holes_max=d["holes_max"], holes_mean=d["holes_mean"],
                exit_total=ex["total"], exit_along=ex["along"], exit_naive=ex["naive_sum"])


def tab_displacement(F: np.ndarray, P: np.ndarray, E: float = PETG["E"], nu: float = PETG["nu"]) -> dict:
    """Displacement of the load point and of the four S3 hole centres for a free cantilever tab
    (rigid motor, so conservative if the real flange stiffens the tab). Euler-Bernoulli bending in y
    (thin direction, I_z) and z (I_y), axial, and torsion (J = 0.312 b t^3, G = E / 2(1+nu)); the
    end loads are F plus the moments of F about the beam axis; points beyond the load point move
    with the end rotation. Read-out rule for the manual: 'gauge' = max over the four S3 holes."""
    b, t = TAB["b"], TAB["t"]
    A = b * t
    Iy = t * b ** 3 / 12.0
    Iz = b * t ** 3 / 12.0
    G_ = E / (2 * (1 + nu))
    J = 0.312 * b * t ** 3
    a = P[0] - TAB["x_root"]
    off = np.array([0.0, P[1] - TAB["y_c"], P[2] - TAB["z_c"]])
    Mend = np.cross(off, F)                         # moments about the beam axis at the load plane
    Fx, Fy, Fz = F
    Mx, My, Mz = Mend

    def at(x_from_root: float, oy: float, oz: float) -> np.ndarray:
        x = min(x_from_root, a)
        ex = max(x_from_root - a, 0.0)              # rigid extension beyond the load point
        v = Fy * (3 * a * x ** 2 - x ** 3) / (6 * E * Iz) + Mz * x ** 2 / (2 * E * Iz)
        th_z = Fy * (2 * a * x - x ** 2) / (2 * E * Iz) + Mz * x / (E * Iz)
        w = Fz * (3 * a * x ** 2 - x ** 3) / (6 * E * Iy) - My * x ** 2 / (2 * E * Iy)
        th_y = -(Fz * (2 * a * x - x ** 2) / (2 * E * Iy) - My * x / (E * Iy))
        th_x = Mx * x / (G_ * J)
        u_ax = Fx * x_from_root / (E * A) if ex == 0 else Fx * a / (E * A)
        v += th_z * ex
        w += -th_y * ex
        return np.array([u_ax + th_y * oz - th_z * oy, v - th_x * oz, w + th_x * oy])

    u_load = at(a, off[1], off[2])
    along = abs(float(u_load @ F) / float(np.linalg.norm(F)))
    holes = []
    holes_u = {}
    for xh in (-15.5, 15.5):
        for zh in (-15.5, 15.5):
            u_h = at(xh - TAB["x_root"], 0.0, zh)
            holes_u[(xh, zh)] = u_h
            holes.append(float(np.linalg.norm(u_h)))
    return dict(load_point_total=float(np.linalg.norm(u_load)), load_point_along=along, u_load=u_load,
                holes_max=max(holes), holes_mean=float(np.mean(holes)), holes_u=holes_u)


def tab_exit_estimate(F: np.ndarray, P: np.ndarray, E: float = PETG["E"], nu: float = PETG["nu"]) -> dict:
    """The manual's section 6.1 recipe for the cable-exit displacement, applied to the hand model (so the manual's
    numbers can be checked against it). Uses displacement COMPONENTS at the four S3 hole centres, never URES magnitudes:
      UX, UY, UZ = means over the four holes
      theta_z = (UY at x=+15.5 - UY at x=-15.5) / 31 ;  theta_x = -(UY at z=+15.5 - UY at z=-15.5) / 31   (rad)
      exit_x = UX - theta_z * LEVER ; exit_z = UZ + theta_x * LEVER ; exit_y = UY
    LEVER = 15.5 mm = drum mid-plane y 18.0 minus tab mid-plane y 2.5."""
    d = tab_displacement(F, P, E, nu)
    hu = d["holes_u"]
    ux = float(np.mean([v[0] for v in hu.values()]))
    uy = float(np.mean([v[1] for v in hu.values()]))
    uz = float(np.mean([v[2] for v in hu.values()]))
    th_z = (np.mean([hu[(15.5, zz)][1] for zz in (-15.5, 15.5)]) - np.mean([hu[(-15.5, zz)][1] for zz in (-15.5, 15.5)])) / 31.0
    th_x = -(np.mean([hu[(xx, 15.5)][1] for xx in (-15.5, 15.5)]) - np.mean([hu[(xx, -15.5)][1] for xx in (-15.5, 15.5)])) / 31.0
    lever = Y_DRUM - TAB["y_c"]
    ex = np.array([ux - th_z * lever, uy, uz + th_x * lever])
    return dict(exit=ex, total=float(np.linalg.norm(ex)), along=abs(float(ex @ F) / float(np.linalg.norm(F))),
                theta_z=float(th_z), theta_x=float(th_x), lever=lever, load_point_total=d["load_point_total"],
                gauge_max=d["holes_max"], mean_ures=float(np.mean([np.linalg.norm(v) for v in hu.values()])),
                # the wrong way (kept to show why it is wrong): mean URES + |rotation| x lever adds orthogonal components
                naive_sum=float(np.mean([np.linalg.norm(v) for v in hu.values()]) + max(abs(th_z), abs(th_x)) * lever))


def screw_group_estimate(F_total: np.ndarray, M_c: np.ndarray) -> dict:
    """Six wall screws (columns y = -2.78 / 34.22, rows z = -34.75 / 10.25 / 55.25), rigid plate, wall bearing
    ignored (conservative). F_total is the force on the plate; M_c the moment of all loads about the screw
    centroid. Tension: Fx/6 + My (rows) + Mz (columns). Shear: (Fy, Fz)/6 + Mx twist; arithmetic worst-case sums."""
    zc = float(np.mean(SCREW_ROWS_Z))
    yc = float(np.mean(SCREW_COLS_Y))
    dz = np.array([z - zc for z in SCREW_ROWS_Z for _ in SCREW_COLS_Y])
    dy = np.array([y - yc for _ in SCREW_ROWS_Z for y in SCREW_COLS_Y])
    t_max = abs(F_total[0]) / 6.0 + abs(M_c[1]) * np.max(np.abs(dz)) / np.sum(dz ** 2) \
        + abs(M_c[2]) * np.max(np.abs(dy)) / np.sum(dy ** 2)
    r2 = dy ** 2 + dz ** 2
    shear = math.hypot(F_total[1], F_total[2]) / 6.0 + abs(M_c[0]) * math.sqrt(np.max(r2)) / np.sum(r2)
    return dict(t_top=float(t_max), shear=float(shear), zc=zc)


# ===========================================================================
# 5. STEP MEASUREMENTS (traceable geometry for the manual)
# ===========================================================================
def measure_step() -> dict | None:
    try:
        import cadquery as cq
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    except Exception:       # cadquery not available
        return None
    if not ASM_STEP.exists():
        return None
    shapes = cq.importers.importStep(str(ASM_STEP))
    sol = sorted(shapes.solids().vals(), key=lambda s: -s.Volume())
    wall, shell, slip, motor = sol[0], sol[1], sol[2], sol[3]

    def faces(p):
        out = []
        for f in p.Faces():
            c = f.Center()
            d = dict(t=f.geomType(), A=f.Area(), c=np.array([c.x, c.y, c.z]) - O_ASM)
            bb = f.BoundingBox()
            d["bb"] = np.array([[bb.xmin, bb.xmax], [bb.ymin, bb.ymax], [bb.zmin, bb.zmax]]) - O_ASM.reshape(3, 1)
            if d["t"] == "PLANE":
                n = f.normalAt()
                d["n"] = np.array([n.x, n.y, n.z])
            if d["t"] == "CYLINDER":
                cy = BRepAdaptor_Surface(f.wrapped).Cylinder()
                ax = cy.Axis()
                d["R"] = cy.Radius()
                d["axis"] = np.array([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
                d["loc"] = np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()]) - O_ASM
            out.append(d)
        return out

    W, S = faces(wall), faces(slip)
    m = {}
    m["solids_mm3"] = dict(wall=wall.Volume(), slipin=slip.Volume(), shell=shell.Volume(), motor=motor.Volume())

    def cyls(F, R, axis_i, tol=0.03):
        pts = {(round(d["loc"][(axis_i + 1) % 3], 2), round(d["loc"][(axis_i + 2) % 3], 2))
               for d in F if d["t"] == "CYLINDER" and abs(d["R"] - R) < tol and abs(abs(d["axis"][axis_i]) - 1) < 1e-6}
        return sorted((float(a), float(b)) for a, b in pts)

    # wall mount: counterbored stud-screw holes (axis ~ x)
    m["wall_hole_yz"] = cyls(W, 1.984, 0)
    cb = [d for d in W if d["t"] == "CYLINDER" and abs(d["R"] - 3.969) < 0.03]
    m["wall_cbore_x"] = (min(d["bb"][0][0] for d in cb), max(d["bb"][0][1] for d in cb))
    th = [d for d in W if d["t"] == "CYLINDER" and abs(d["R"] - 1.984) < 0.03]
    m["wall_hole_x"] = (min(d["bb"][0][0] for d in th), max(d["bb"][0][1] for d in th))
    back = max((d for d in W if d["t"] == "PLANE" and d["n"][0] < -0.99), key=lambda d: d["A"])
    m["wall_back"] = (back["c"][0], back["A"], back["bb"][1], back["bb"][2])
    lips = [d for d in W if d["t"] == "PLANE" and d["n"][0] < -0.99 and 2000 < d["A"] < 3500]
    m["lip_inner"] = sorted((round(float(d["c"][0]), 2), round(float(d["c"][1]), 1), round(float(d["A"]), 0)) for d in lips)
    shelf = [d for d in W if d["t"] == "PLANE" and d["n"][2] > 0.99 and 2500 < d["A"] < 4000 and d["c"][2] < 0]
    m["shelf_top_z"] = [round(float(d["c"][2]), 2) for d in shelf]
    m["wall_extent"] = (min(d["bb"][0][0] for d in W), max(d["bb"][0][1] for d in W),
                        min(d["bb"][1][0] for d in W), max(d["bb"][1][1] for d in W),
                        min(d["bb"][2][0] for d in W), max(d["bb"][2][1] for d in W))
    grooves = [d for d in W if d["t"] == "PLANE" and d["n"][0] > 0.99 and 1100 < d["A"] < 1300]
    m["groove_floor_y"] = sorted(round(float(d["c"][1]), 2) for d in grooves)
    m["groove_floor_x"] = sorted({round(float(d["c"][0]), 2) for d in grooves})

    # slide-in motor tab (plane normal +/-y)
    tab_b = [d for d in S if d["t"] == "PLANE" and d["n"][1] < -0.99 and 1200 < d["A"] < 1500]
    tab_f = [d for d in S if d["t"] == "PLANE" and d["n"][1] > 0.99 and 1100 < d["A"] < 1400]
    m["tab_back_y"] = [round(float(d["c"][1]), 3) for d in tab_b]
    m["tab_front_y"] = [round(float(d["c"][1]), 3) for d in tab_f]
    m["tab_extent"] = tab_b[0]["bb"] if tab_b else None
    m["pilot"] = sorted({(round(float(d["R"]), 3), round(float(d["loc"][0]), 2), round(float(d["loc"][2]), 2)) for d in S
                         if d["t"] == "CYLINDER" and abs(d["R"] - 11.2) < 0.05})
    m["motor_holes_xz"] = [p for p in cyls(S, 1.75, 1, tol=0.01) if abs(p[0]) < 20 and abs(p[1]) < 20]
    deck_top = max((d for d in S if d["t"] == "PLANE" and d["n"][0] > 0.99 and d["A"] > 15000), key=lambda d: d["A"])
    m["deck_top_x"] = round(float(deck_top["c"][0]), 3)
    end_face = [d for d in S if d["t"] == "PLANE" and d["n"][2] < -0.99 and 2000 < d["A"] < 2400]
    m["slip_end_z"] = round(float(end_face[0]["c"][2]), 3) if end_face else None
    rib_y = sorted(round(float(d["c"][1]), 2) for d in S if d["t"] == "PLANE" and d["n"][0] < -0.99 and 1100 < d["A"] < 1200 and d["c"][0] < -34)
    m["rib_tip_y"] = rib_y
    m["slip_extent"] = (min(d["bb"][0][0] for d in S), max(d["bb"][0][1] for d in S),
                        min(d["bb"][1][0] for d in S), max(d["bb"][1][1] for d in S),
                        min(d["bb"][2][0] for d in S), max(d["bb"][2][1] for d in S))
    # shell screw holes through the deck (R1.75, axis x, Ø3.5)
    m["deck_shell_screws_yz"] = [p for p in cyls(S, 1.75, 0, tol=0.01) if abs(p[0]) > 40]
    m["encoder_pocket_yz"] = [p for p in cyls(S, 1.725, 0, tol=0.01)]
    # gaps
    shelf_z = m["shelf_top_z"][0] if m["shelf_top_z"] else float("nan")
    m["shelf_gap_mm"] = m["slip_end_z"] - shelf_z if m["slip_end_z"] is not None else None
    lipx = m["lip_inner"][0][0] if m["lip_inner"] else float("nan")
    m["lip_gap_mm"] = lipx - m["deck_top_x"]
    d = BRepExtrema_DistShapeShape(wall.wrapped, slip.wrapped)
    d.Perform()
    m["min_dist_wall_slipin_mm"] = d.Value()
    com = wall.intersect(slip)
    m["interference_mm3"] = com.Volume() if com.Solids() else 0.0
    m["gap_note"] = "dovetail flanks 0.13-0.21 mm except one centre-rib flank that touches / overlaps ~0.02 mm"
    return m


# ===========================================================================
# 6. THERMAL
# ===========================================================================
R_PHASE = 1.8            # ohm per phase [REPO gen2_motor_thermal.py R_PHASE, "measure"]
T_ROOM_MEAS = 20.6       # C measured 69 F [REPO DESIGN_STATE 10/20]
T_AMB = 23.0             # C near the ceiling [USER / REPO D29]
T_INSIDE_VENTED = 27.0   # C air inside a vented shell: T_amb + (P_motor_air+P_e)*R_sa (computed below)
FIN = dict(w=44.0, h=250.0, z_exit=50.0, axis=21.0, patch_w=42.3, patch_top=42.15,
           hole_d=22.225, bolt_d=3.4, bolt_sq=31.0)          # mm [REPO motor_heat_plate.py, USER]
T_AS_BUILT = 0.483        # mm (0.019 in) [REPO DESIGN_STATE 10/20]
T_DESIGN = 3.175          # mm (1/8 in) [REPO motor_heat_plate.py]
ALLOYS = {"3003-H14": 159.0, "5052-H32": 138.0, "6061-T6": 167.0}   # W/m.K typical handbook [ASSUMED, bound]
EPS = {"bare Al": 0.10, "black paint": 0.90}                       # [USER]
H_INSIDE = 4.0           # W/m^2K inside the shell strip [ASSUMED]
R_MA = {"vented": 12.0, "sealed": 14.0}   # K/W motor case -> shell air [REPO gen2_motor_thermal.py]
R_SA = {"vented": 1.0, "sealed": 3.5}     # K/W shell air -> room [REPO]
P_ELEC = 1.5             # W electronics inside shell [REPO]
C_MOTOR, C_SHELL = 130.0, 600.0           # J/K [REPO]
AIR = dict(k=0.0263, nu=1.59e-5, alpha=2.25e-5, Pr=0.707)   # 300 K, 1 atm


def motor_heat(i_amp: float = I_SET, r_phase: float = R_PHASE) -> float:
    """A4988 holds I_a^2 + I_b^2 = I_trip^2 at any microstep position, so the
    total coil loss is I_trip^2 * R_phase (same as gen2_motor_thermal.py)."""
    return i_amp ** 2 * r_phase


def h_churchill_chu(dT: float, L: float, T_film_K: float = 300.0) -> tuple[float, float, float]:
    Ra = G * (1.0 / T_film_K) * dT * L ** 3 / (AIR["nu"] * AIR["alpha"])
    Nu = (0.825 + 0.387 * Ra ** (1 / 6) / (1 + (0.492 / AIR["Pr"]) ** (9 / 16)) ** (8 / 27)) ** 2
    return Ra, Nu, Nu * AIR["k"] / L


def h_simple(dT: float, L: float) -> float:
    return 1.42 * (dT / L) ** 0.25


def h_rad(eps: float, Ts_C: float, Ta_C: float) -> float:
    Ts, Ta = Ts_C + 273.15, Ta_C + 273.15
    return eps * SIGMA_SB * (Ts ** 2 + Ta ** 2) * (Ts + Ta)


def fin_analytic(k: float, t_mm: float, h: float, L_mm: float = 200.0, w_mm: float = 44.0) -> dict:
    t, L, w = t_mm * 1e-3, L_mm * 1e-3, w_mm * 1e-3
    m = math.sqrt(2 * h / (k * t))
    mL = m * L
    eta = math.tanh(mL) / mL
    A = 2 * w * L
    R = 1.0 / (h * eta * A)
    return dict(m=m, mL=mL, eta=eta, A=A, R=R, tip_ratio=1.0 / math.cosh(mL),
                ratio_at=lambda dz_mm: math.cosh(m * (L - dz_mm * 1e-3)) / math.cosh(mL))


def width_profile(z_mm: np.ndarray, t_hole: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Plate width w(z) (mm) and contact-patch width wc(z) (mm) along the fin."""
    z = np.asarray(z_mm, float)
    cut = np.zeros_like(z)
    r = FIN["hole_d"] / 2
    d = np.abs(z - FIN["axis"])
    cut += np.where(d < r, 2 * np.sqrt(np.maximum(r * r - d * d, 0)), 0.0)
    rb = FIN["bolt_d"] / 2
    for dz in (-FIN["bolt_sq"] / 2, FIN["bolt_sq"] / 2):
        d = np.abs(z - (FIN["axis"] + dz))
        cut += 2 * np.where(d < rb, 2 * np.sqrt(np.maximum(rb * rb - d * d, 0)), 0.0)   # two bolts per row
    w = FIN["w"] - cut
    wc = np.where(z <= FIN["patch_top"], FIN["patch_w"] - cut, 0.0)
    return w, wc


def fin_quasi_1d(k: float, t_mm: float, h_out: float, q_total: float = 1.0, h_in: float = H_INSIDE,
                 dT_inside: float = T_INSIDE_VENTED - T_AMB, dz: float = 0.25, isothermal: bool = False) -> dict:
    """Finite-difference fin along z with the real width profile (hole + bolt
    holes), heat injected over the contact patch, no convection under the
    patch, h_in on the strip inside the shell, h_out above the shell exit.
    Returns temperature RISE over room air (K) for q_total watts.
    isothermal=False: the heat enters as a uniform flux over the patch (the model B-1 'heat power' load).
    isothermal=True: the patch is held at ONE temperature (a NEMA 17 aluminium-nosed flange, or a k = 50 W/m.K
    block, is close to this; the limit that model B-2 approaches) and q_total sets that temperature.
    The truth lies between the two limits; the isothermal limit gives the lower motor temperature."""
    H = FIN["h"]
    z = np.arange(0.0, H + dz / 2, dz)
    n = len(z)
    w, wc = width_profile(z)
    t = t_mm * 1e-3
    # conductances between nodes (W/K)
    wm = 0.5 * (w[:-1] + w[1:]) * 1e-3
    Gc = k * t * wm / (dz * 1e-3)
    hz = np.where(z <= FIN["patch_top"], 0.0, np.where(z <= FIN["z_exit"], h_in, h_out))
    thz = np.where((z > FIN["patch_top"]) & (z <= FIN["z_exit"]), dT_inside, 0.0)
    loss = 2.0 * hz * w * 1e-3 * dz * 1e-3
    diag = loss.copy()
    diag[:-1] += Gc
    diag[1:] += Gc
    off = -Gc                                            # sub- and super-diagonal (symmetric)
    b = loss * thz

    def solve(d, off, rhs):
        """Thomas algorithm for the symmetric tridiagonal system (diagonal d, off-diagonal off) x = rhs; rhs may have several columns."""
        m_ = len(d)
        cp = np.empty(m_ - 1)
        dp = np.empty_like(rhs, dtype=float)
        cp[0] = off[0] / d[0] if m_ > 1 else 0.0
        dp[0] = rhs[0] / d[0]
        for i in range(1, m_):
            den = d[i] - off[i - 1] * cp[i - 1]
            if i < m_ - 1:
                cp[i] = off[i] / den
            dp[i] = (rhs[i] - off[i - 1] * dp[i - 1]) / den
        x = np.empty_like(dp)
        x[-1] = dp[-1]
        for i in range(m_ - 2, -1, -1):
            x[i] = dp[i] - cp[i] * x[i + 1]
        return x

    if isothermal:
        ip = z <= FIN["patch_top"]
        i0 = int(np.argmax(~ip))                         # first node above the patch
        Gint = float(Gc[i0 - 1])                         # the only link between the two blocks (1-D chain)
        # sub-chain of the nodes above the patch: same tridiagonal, first diagonal term loses the (now fixed) patch link
        rhs = np.zeros((n - i0, 2))
        rhs[:, 0] = b[i0:]                               # response to the inside-air offset alone
        rhs[0, 1] = Gint                                 # unit patch temperature through the interface
        sol = solve(diag[i0:], off[i0:], rhs)
        u0, u1 = sol[:, 0], sol[:, 1]
        th_p = (q_total + Gint * u0[0]) / (Gint * (1.0 - u1[0]))
        th = np.empty(n)
        th[ip] = th_p
        th[i0:] = th_p * u1 + u0
        patch_avg = float(th_p)
    else:
        qprime = wc / np.sum(wc)
        th = solve(diag, off, b + q_total * qprime)
        patch_avg = float(np.sum(th * wc) / np.sum(wc))
    return dict(z=z, th=th, patch_avg=patch_avg, base=float(th[np.searchsorted(z, FIN["patch_top"])]),
                exit=float(th[np.searchsorted(z, FIN["z_exit"])]), tip=float(th[-1]),
                at=lambda zz: float(np.interp(zz, z, th)),
                R_patch=patch_avg / q_total)


def contact_area_mm2() -> float:
    p = FIN["patch_w"] * FIN["patch_top"]
    return p - math.pi * (FIN["hole_d"] / 2) ** 2 - 4 * math.pi * (FIN["bolt_d"] / 2) ** 2


def coupled_motor(P: float, R_fin_total: float | None, mode: str = "vented", T_a: float = T_AMB,
                  p_elec: float = P_ELEC) -> dict:
    """Two-node network (as gen2_motor_thermal.py) with the fin as a second path:
    motor -(R_ma)-> shell air -(R_sa)-> room ; motor -(R_fin_total)-> room."""
    Rma, Rsa = R_MA[mode], R_SA[mode]
    g_fin = 0.0 if R_fin_total is None else 1.0 / R_fin_total
    x = (P + p_elec * Rsa / (Rma + Rsa)) / (g_fin + 1.0 / (Rma + Rsa))
    q_fin = x * g_fin
    q_air = P - q_fin
    t_in = T_a + (q_air + p_elec) * Rsa
    return dict(T_motor=T_a + x, rise=x, q_fin=q_fin, q_air=q_air, T_inside=t_in)


def coupled_converged(k: float, t_mm: float, eps: float, R_contact: float, mode: str = "vented",
                      P: float | None = None, isothermal: bool = False) -> dict:
    """Fin + motor-to-air path with the fin's own h (natural convection + radiation)
    re-converged for the heat the fin ACTUALLY carries (not the all-through-the-fin bound).
    isothermal=True holds the fin patch at one temperature (see fin_quasi_1d)."""
    P = motor_heat() if P is None else P
    h = 7.0
    for _ in range(80):
        fd = fin_quasi_1d(k, t_mm, h, q_total=1.0, isothermal=isothermal)
        f = fin_analytic(k, t_mm, h)
        r = coupled_motor(P, R_contact + fd["R_patch"], mode)
        theta_mean = f["eta"] * r["q_fin"] * f["R"]
        h_new = h_churchill_chu(max(theta_mean, 0.5), 0.2)[2] + h_rad(eps, T_AMB + theta_mean, T_AMB)
        if abs(h_new - h) < 1e-4:
            break
        h = h_new
    fd1 = fin_quasi_1d(k, t_mm, h, q_total=r["q_fin"], dT_inside=r["T_inside"] - T_AMB, isothermal=isothermal)
    return dict(h=h, fd=fd1, f=f, r=r, R_tot=R_contact + fd["R_patch"])


def transient_motor(P: float, R_fin_total: float | None, mode: str = "vented", T_a: float = T_AMB,
                    C_fin: float = 13.0, minutes: float = 120.0, dt: float = 2.0) -> list:
    Rma, Rsa = R_MA[mode], R_SA[mode]
    tm = ts = T_a
    out = []
    for k in range(int(minutes * 60 / dt) + 1):
        q_ma = (tm - ts) / Rma
        q_f = 0.0 if R_fin_total is None else (tm - T_a) / R_fin_total
        if k % int(60 / dt) == 0:
            out.append((k * dt / 60.0, tm, ts))
        tm += dt * (P - q_ma - q_f) / (C_MOTOR + C_fin)
        ts += dt * (q_ma + P_ELEC - (ts - T_a) / Rsa) / C_SHELL
    return out


# ===========================================================================
# printing helpers
# ===========================================================================
def hr(title: str) -> None:
    print("\n" + title)
    print("=" * len(title))


def row(name: str, value, unit: str, src: str, w: int = 46) -> None:
    v = f"{value:.4g}" if isinstance(value, float) else str(value)
    print(f"  {name:<{w}} {v:>14} {unit:<8} {src}")


def vec(v) -> str:
    return "(" + ", ".join(f"{x:+.4f}" for x in v) + ")"


# ===========================================================================
# STUDY A REPORT
# ===========================================================================
def report_static(use_step: bool = True) -> dict:
    out = {}
    hr("A1. Motor torque and cable tension cases (36 N.cm basis, repo convention)")
    print(f"  A4988 current: Vref {VREF} V / (8 x {R_SENSE} ohm) = {I_SET:.4f} A  [REPO D30: Vref ~0.85 V ~ 1.06 A]")
    t = tension_cases()
    out["t"] = t
    for i_amp in (1.0, I_SET, 1.5):
        tt = tension_cases(i_amp)
        print(f"  I = {i_amp:.4f} A: hold {HOLD_36}*{i_amp:.4f}/{I_RATED} = {tt['hold']:.4f} N.m ; "
              f"slip-limit = hold/R_empty = {tt['hold']:.4f}/{R_EMPTY*1e3:.1f} mm = {tt['slip']:.2f} N")
    print("  (check vs repo: 32 N @ 1.0 A, 48 N @ 1.5 A: DESIGN_STATE 'Structural design load per cable')")
    row("working max (moving, full spool, no margin)", t["work"], "N",
        f"0.7 x hold / R_full = {RUN_FRAC}*{t['hold']:.4f}/{R_FULL*1e3:.0f} mm [REPO gen2_payload_limit.py]")
    row("running pull at the empty core (r = 7.5 mm)", t["work_core"], "N",
        "0.7 x hold / R_empty; = 23.8 N in the 10/21 erratum to D29/D30 (not a demanded tension)")
    row("working, payload-limited (with 1.5 skip margin)", t["work_margin"], "N", "R10 convention; = 11.9 N design force in the erratum")
    row("slip-limit (stepper pull-out, empty spool)", t["slip"], "N", "hold / R_empty; D30 '~34 N'")
    row("dynamic (abuse bound) = 2 x slip-limit", t["dyn"], "N", "R10 'x2 dynamic'")
    t40 = tension_cases(I_SET, HOLD_40)
    row("sensitivity: slip-limit with 40 N.cm motor", t40["slip"], "N",
        f"x{HOLD_40/HOLD_36:.3f}: SF /{HOLD_40/HOLD_36:.3f} for every result")
    print("  Pass-criterion identity: SF >= 3 at slip-limit  <=>  SF >= 1.5 at 2 x slip-limit (linear model).")

    hr("A2. Line directions (station frame: +x out of wall, +y along shaft toward spool, +z up)")
    print("  T18 angles belong to the old 4 x 3 x 2.6 m room; the real 11 x 9 x 9 ft room gives:")
    for k, v in real_room_angles().items():
        print(f"    {k:<34} {v:6.1f} deg from vertical")
    print(f"  Drum mid-plane Y_DRUM = {Y_DRUM} mm [ASSUMED: Spoolv3 symmetric about y = 7..29 mm]; tangent point on the "
          f"room (+x) side at r = {R_EMPTY*1e3:.1f} mm")
    rows = []
    for cid, label, th, ps, why in CASES:
        u = unit_vector(th, ps)
        p = tangent_point(u)
        F = t["slip"] * u
        rows.append((cid, label, th, ps, u, p, F))
        print(f"  {cid} {label} (theta {th}, psi {ps:+.0f})")
        print(f"      unit vector u = {vec(u)}  [points from station toward the claw]")
        print(f"      load point P_station = ({p[0]:+.2f}, {p[1]:+.2f}, {p[2]:+.2f}) mm ; "
              f"P_assembly = ({p[0]+O_ASM[0]:.2f}, {p[1]+O_ASM[1]:.2f}, {p[2]+O_ASM[2]:.2f}) mm")
        print(f"      force on the station at slip-limit {t['slip']:.2f} N : F = {vec(F)} N")
        print(f"      working {t['work']:.2f} N : {vec(t['work']*u)} ; dynamic {t['dyn']:.2f} N : {vec(t['dyn']*u)}")
    out["rows"] = rows
    a_fl = fleet_limit_deg()
    print(f"\n  Reachability (bare drum between r = 18 mm flanges, line leaving the 16 mm drum mid-plane): the fleet angle "
          f"cannot exceed {a_fl:.1f} deg before the line scrubs a flange. D2 needs {math.degrees(math.asin(0.4903)):.1f} deg and "
          f"D4/D5 need 78.7 deg (D4 would also pass through the tab and motor), so D2 needs an outlet that turns the line, and D4/D5 are "
          f"unreachable bounds. At the same shaft torque the tension along a fleeted line is T = slip / cos(fleet).")
    reach = reachable_cases(t)
    out["reach"] = reach
    for cid, label, u, T, p in reach:
        F = T * u
        print(f"  {cid} {label}: u = {vec(u)}, T = {T:.2f} N, load point ({p[0]:+.2f}, {p[1]:+.2f}, {p[2]:+.2f}) mm")
        print(f"      F at slip-limit = {vec(F)} N ; working x{t['work']/t['slip']:.3f} = {vec(F*t['work']/t['slip'])} ; "
              f"dynamic x2 = {vec(F*2)}")
    out["d4f"] = (reach[3][2], reach[3][4])

    hr("A3. Weights (gravity -z), remote forces and the P5 reaction check")
    row("motor + spool + line (remote force 1)", M_MOTOR + 0.01, "kg", "[REPO guide 0.28 kg] + spool ~10 g at 100 % PETG")
    row("shell + electronics (remote force 2)", M_SHELL, "kg", "[ASSUMED] weigh it; solid shell would be 0.47 kg")
    w_tot = REMOTE_WEIGHT_N
    row("remote weights (applied as forces)", w_tot, "N", "(m1 + m2) g")
    row("self-weight of the two meshed bodies", SELF_WEIGHT_N, "N",
        f"({V_WALL_MM3:,.0f} + {V_SLIPIN_MM3:,.0f}) mm3 x 1270 kg/m3 x g = {(V_WALL_MM3+V_SLIPIN_MM3)*1e-9*1270:.3f} kg [STEP]")
    print("  Expected sum of fixture reactions (P5), station frame, N: minus (line force + weights + self-weight)")
    for cid, label, th, ps, u, p, F in rows:
        print(f"    {cid:<4} {vec(expected_reaction(F))}")
    for cid, label, u, T, p in reach:
        if cid not in ("D1", "D3"):
            print(f"    {cid:<4} {vec(expected_reaction(T*u))}")

    hr("A4. Material, allowables, target SF")
    for k, v in PETG.items():
        row(f"PETG (derated) {k}", v, "MPa" if k in ("E", "uts", "yield_derated") else "", "[REPO SIMULATION_GUIDE.md]")
    al = allowables()
    row("allowable von Mises at slip-limit (SF 3)", al["vm_static"], "MPa", "25 / 3")
    row("allowable von Mises at 2 x slip-limit (SF 1.5)", al["vm_dynamic"], "MPa", "25 / 1.5  (same criterion, x2 load)")
    row("allowable 1st principal across layers (SF 3)", al["p1_layer"], "MPa", "50 % of 45 MPa UTS = 22.5 [REPO R5] / 3")
    row("hot-tab von Mises allowable (SF 3)", al["vm_hot"], "MPa", "[ASSUMED] x0.7 strength at ~55 C motor-warmed PETG")

    hr("A5. Deflection limit at the cable exit")
    d = deflection_limit(t)
    row("proposed limit at slip-limit load", d["limit_slip"], "mm", "elastic, excludes fit clearances")
    row("equivalent limit at working load", d["limit_work"], "mm", "scaled by working / slip-limit")
    row("implied station stiffness", d["k_station"], "N/mm", "slip-limit / limit")
    row("line stiffness (Dyneema, ~3 m)", K_LINE, "N/mm", "[REPO review R1 estimate]")
    row("station stiffness / line stiffness", d["ratio_to_line"], "x", "")
    row("station share of total compliance", d["added_compliance_pct"], "%", "1/k_s / (1/k_s + 1/k_line)")
    row("line stretch alone at working load", d["line_stretch_work"], "mm", "working / k_line (calibrated out)")
    row("drawn fit clearance (total, x or y)", CLEARANCE_PLAY_MM, "mm", "[STEP] 0.15 mm per side, lips and slot ends")
    print("  Rationale: anchor motion maps ~1:1 into claw position error (DECISION_STORIES: calibration sensitivity "
          "study). 0.5 mm is 2.5 % of the ~20 mm absolute-length sigma the vision calibration leaves (D24/D26), "
          "<5 % added compliance in series with the line, and is the repo guide's existing criterion.")

    hr("A6. Hand estimates for the FEA sanity band (hole-only load path, rigid motor, free cantilever tab)")
    print("  tab root: nominal sigma / von Mises (x1.5-2.5 with the root corner); displacement of the load point (total / along the "
          "line), the S3 hole gauge (max / mean over the four holes) and the manual's section 6.1 exit estimate from displacement "
          "components (lever 15.5 mm = drum plane 18.0 - tab mid-plane 2.5); wall screws: max tension / max shear")
    C = np.array([WALL_X, float(np.mean(SCREW_COLS_Y)), float(np.mean(SCREW_ROWS_Z))])
    est_rows = []
    cases6 = [(c[0], c[1], t["slip"] * c[4], c[5]) for c in rows] + \
             [(c[0], c[1], c[3] * c[2], c[4]) for c in reach if c[0] in ("D2c", "D4f")]
    for cid, label, F, p in cases6:
        Mw = np.cross(P_MOTOR - C, np.array([0, 0, -(M_MOTOR + 0.01) * G])) \
            + np.cross(P_SHELL - C, np.array([0, 0, -M_SHELL * G]))
        Mc = np.cross(p - C, F) + Mw
        Ftot = F + np.array([0.0, 0.0, -(REMOTE_WEIGHT_N + SELF_WEIGHT_N)])
        est = tab_root_estimate(F, p)
        sg = screw_group_estimate(Ftot, Mc)
        est_rows.append((cid, est, sg))
        print(f"  {cid:<4} F = {vec(F)} N | sigma {est['sigma_nom']:.2f} MPa, vM {est['vm_nom']:.2f} MPa "
              f"({1.5*est['vm_nom']:.1f}-{2.5*est['vm_nom']:.1f}) | load point {est['defl_total']:.2f}/{est['defl_along']:.2f} mm, "
              f"S3 gauge {est['holes_max']:.2f}/{est['holes_mean']:.2f} mm, exit by components {est['exit_total']:.2f} mm "
              f"(URES-sum recipe, wrong: {est['exit_naive']:.2f}) | screws {sg['t_top']:.1f} N / {sg['shear']:.1f} N")
    out["est_rows"] = est_rows
    out["w_tot"] = w_tot

    hr("A7. Retention check by hand (R3)")
    F3 = t["slip"] * unit_vector(THETA_SCAN, 0.0)
    fx = F3[0]
    rib_flank_mm2 = 420.1      # measured inclined dovetail groove flank area (one per rib side) [STEP]
    lip_mm2 = 2758.5           # J-lip inner face, one per side [STEP]
    p_dt = (fx / 3.0) / (rib_flank_mm2 * math.sin(math.radians(30.0)))
    p_lip = (fx / 2.0) / (0.25 * lip_mm2)
    row("D3 pull-away force Fx at slip-limit", fx, "N", "")
    row("dovetail flank bearing, 3 ribs, 30 deg flank", p_dt, "MPa", "Fx/3 per rib over one 420 mm2 flank, projected; flank normals (-0.5, +-0.866) measured [STEP]")
    row("J-lip bearing if only 25 % of the lip area bears", p_lip, "MPa", "backup path after 0.15 mm slip")
    row("margin to 8.33 MPa allowable", al["vm_static"] / max(p_dt, p_lip), "x", "strength is not the issue; fit/creep is")

    if use_step:
        hr("A8. Geometry measured from solidworks/v3_assembly_2026-10-19/Assem_laundry_v3.STEP (station frame, mm)")
        m = measure_step()
        if m is None:
            print("  (cadquery or the STEP file is not available: skipped)")
        else:
            out["step"] = m
            print(f"  solid volumes mm3: {', '.join(f'{k} {v:,.0f}' for k, v in m['solids_mm3'].items())}")
            print(f"  wall mount extent x[{m['wall_extent'][0]:.2f},{m['wall_extent'][1]:.2f}] "
                  f"y[{m['wall_extent'][2]:.2f},{m['wall_extent'][3]:.2f}] z[{m['wall_extent'][4]:.2f},{m['wall_extent'][5]:.2f}]")
            print(f"  wall back face x = {m['wall_back'][0]:.2f}, area {m['wall_back'][1]:.0f} mm2")
            print(f"  6 stud-screw holes (y,z): {m['wall_hole_yz']}  through x[{m['wall_hole_x'][0]:.2f},{m['wall_hole_x'][1]:.2f}] "
                  f"counterbore x[{m['wall_cbore_x'][0]:.2f},{m['wall_cbore_x'][1]:.2f}]")
            print(f"  J-lip inner faces (x, y, area): {m['lip_inner']}; shelf top z: {m['shelf_top_z']}")
            print(f"  dovetail groove floors at y {m['groove_floor_y']} (x {m['groove_floor_x']})")
            print(f"  slide-in extent x[{m['slip_extent'][0]:.2f},{m['slip_extent'][1]:.2f}] y[{m['slip_extent'][2]:.2f},"
                  f"{m['slip_extent'][3]:.2f}] z[{m['slip_extent'][4]:.2f},{m['slip_extent'][5]:.2f}]; deck top x = {m['deck_top_x']}")
            print(f"  motor tab back y = {m['tab_back_y']}, front y = {m['tab_front_y']}; pilot R/x/z = {m['pilot']}")
            print(f"  motor holes (x,z): {m['motor_holes_xz']}; shell-screw holes in the deck (y,z): {m['deck_shell_screws_yz']}")
            print(f"  dovetail rib tips at y = {m['rib_tip_y']}; encoder pocket holes (y,z, assembly version only): {m['encoder_pocket_yz']}")
            print(f"  gaps: shelf {m['shelf_gap_mm']:.3f} mm, lip {m['lip_gap_mm']:.3f} mm; min distance wall-slipin "
                  f"{m['min_dist_wall_slipin_mm']:.4f}; interference {m['interference_mm3']:.1f} mm3 ({m['gap_note']})")
    return out


# ===========================================================================
# STUDY B REPORT
# ===========================================================================
def converge_h(k: float, t_mm: float, eps: float, P: float, L_mm: float = 200.0) -> tuple[float, dict]:
    """Self-consistent combined h (natural convection + linearised radiation) for a fin
    that receives P watts at its base (all-through-the-fin bound)."""
    h = 8.0
    for _ in range(60):
        f = fin_analytic(k, t_mm, h, L_mm)
        theta_b = P * f["R"]
        theta_mean = theta_b * f["eta"]
        hc = h_churchill_chu(max(theta_mean, 0.5), L_mm * 1e-3)[2]
        hr_ = h_rad(eps, T_AMB + theta_mean, T_AMB)
        h_new = hc + hr_
        if abs(h_new - h) < 1e-4:
            break
        h = h_new
    return h, f


def report_thermal() -> dict:
    out = {}
    hr("B1. Heat load")
    P = motor_heat()
    row("driver current (Vref 0.85 V on R100)", I_SET, "A", "D30")
    row("coil resistance per phase", R_PHASE, "ohm", "[REPO gen2_motor_thermal.py R_PHASE; measure with a meter]")
    row("motor heat P = I_trip^2 x R_phase", P, "W", "convention checked against gen2_motor_thermal.py: p_m = i*i*R_PHASE")
    print("   (A4988 holds I_a^2 + I_b^2 = I_trip^2 at any microstep position, so holding loss does not depend on the "
          "microstep phase; full-step with both coils at 0.707 I_trip gives the same total.)")
    row("electronics heat into the shell air", P_ELEC, "W", "[REPO gen2_motor_thermal.py P_E] (not on the fin)")
    row("room air (bench measurement, 69 F)", T_ROOM_MEAS, "C", "[REPO DESIGN_STATE 10/20]")
    row("air near the ceiling (design value)", T_AMB, "C", "[USER / D29]")
    out["P"] = P

    hr("B2. Natural convection on a vertical plate, L = 0.200 m (exposed fin height)")
    print("   Churchill-Chu: Nu = {0.825 + 0.387 Ra^(1/6) / [1+(0.492/Pr)^(9/16)]^(8/27)}^2 ; h = Nu k / L ; "
          "air at 300 K: k 0.0263, nu 1.59e-5, alpha 2.25e-5, Pr 0.707")
    print("   Simple laminar: h = 1.42 (dT/L)^0.25")
    print("    dT[K]     Ra        Nu     h_CC[W/m2K]  h_simple")
    for dT in (3, 5, 8, 10, 15, 20):
        Ra, Nu, hh = h_churchill_chu(dT, 0.2)
        print(f"    {dT:5.0f}  {Ra:9.3e}  {Nu:6.1f}   {hh:7.2f}      {h_simple(dT, 0.2):6.2f}")
    print("   Radiation (linearised, to room walls): h_r = eps sigma (Ts^2+Ta^2)(Ts+Ta)")
    for name, e in EPS.items():
        for Ts in (28.0, 33.0, 40.0):
            print(f"    {name:<12} eps {e:.2f}  Ts {Ts:.0f} C  Ta {T_AMB:.0f} C : h_r = {h_rad(e, Ts, T_AMB):.2f} W/m2K")
    out["h_cc_ex"] = h_churchill_chu(8.0, 0.2)[2]

    hr("B3. Contact conductance between motor flange and fin (assumption set)")
    A_c = contact_area_mm2()
    row("contact area (42.3 x 42.15 patch - holes)", A_c, "mm2", "[REPO drawing + USER 7/8 in hole]")
    contact = {"thermal paste": 10000.0, "dry flat nominal": 3000.0, "dry, bowed sheet (repo +1 K/W)": 1.0 / (1.0 * A_c * 1e-6)}
    for name, hc in contact.items():
        Rc = 1.0 / (hc * A_c * 1e-6)
        print(f"    {name:<34} h_c {hc:8.0f} W/m2K -> R'' {1.0/hc:9.3e} K.m2/W -> R_c {Rc:5.3f} K/W")
    out["A_contact"] = A_c

    hr("B4. Fin hand calculation  (eta = tanh(mL)/mL, m = sqrt(2h/(k t)), R_fin = 1/(h eta A))")
    print("   Fin: 44 mm wide, 200 mm exposed above the shell, both faces; h fixed from the 6061 converged value per finish "
          "(h is held constant across alloys and thickness so only k and t differ).")
    # converge h on the as-built 6061 fin for each finish, all of P through the fin (bound)
    hfix = {}
    for fin_name, e in EPS.items():
        h, f = converge_h(ALLOYS["6061-T6"], T_AS_BUILT, e, P)
        hfix[fin_name] = round(h, 1)
        print(f"   converged h (6061, 0.483 mm, P={P:.2f} W through fin): {fin_name:<12} h = {h:.2f} -> use {hfix[fin_name]} W/m2K")
    out["hfix"] = hfix

    def fd_case(k, t_mm, h):
        return fin_quasi_1d(k, t_mm, h, q_total=P)

    print("\n   all heat through the fin (bound), Q = %.2f W, patch = contact square" % P)
    print("   t_mm  alloy      finish        h    m[1/m]   mL    eta   R_fin  rise@z50 patch-avg  tip   | Tpatch   Ttip  (C, room 23)")
    table = {}
    for t_mm in (T_AS_BUILT, T_DESIGN):
        for alloy, k in ALLOYS.items():
            for fin_name in EPS:
                h = hfix[fin_name]
                f = fin_analytic(k, t_mm, h)
                fd = fd_case(k, t_mm, h)
                th_b = P * f["R"]
                th_tip = th_b * f["tip_ratio"]
                table[(t_mm, alloy, fin_name)] = dict(f=f, fd=fd, th_b=th_b, th_tip=th_tip, h=h)
                print(f"   {t_mm:5.3f} {alloy:<9} {fin_name:<12} {h:5.1f} {f['m']:7.2f} {f['mL']:5.2f} {f['eta']:6.3f} {f['R']:6.2f} "
                      f"{th_b:7.1f} {fd['patch_avg']:8.1f} {th_tip:7.2f} | {T_AMB+fd['patch_avg']:6.1f} {T_AMB+fd['tip']:6.1f}")
    out["table"] = table
    out["fin_area"] = table[(T_AS_BUILT, '6061-T6', 'black paint')]["f"]["A"]

    hr("B5. Quasi-1D refinement (hole + bolt-hole width loss, heat spread over the patch)")
    print("   Same conditions; compare with the formula column (th_base = Q x R_fin).  Rises in K over room air.")
    for t_mm in (T_AS_BUILT, T_DESIGN):
        for fin_name in EPS:
            k = ALLOYS["6061-T6"]
            h = hfix[fin_name]
            f = fin_analytic(k, t_mm, h)
            fd = fd_case(k, t_mm, h)
            R_extra = fd["R_patch"] - f["R"]
            print(f"   t {t_mm:5.3f} mm {fin_name:<12} R_fin(formula) {f['R']:6.2f} K/W ; R patch-average (quasi-1D) {fd['R_patch']:6.2f} K/W "
                  f"(+{R_extra:4.2f} K/W spreading/constriction) ; FD base(z=42) {fd['base']/P:5.2f} K/W vs formula {f['R']:5.2f}")
    out["fd_ref"] = fd_case(ALLOYS["6061-T6"], T_AS_BUILT, hfix["black paint"])

    hr("B6. Coupled motor temperature (fin + motor-to-air path), room 23 C, 1.0625 A")
    print("   R_fin_total = R_contact + R_patch(quasi-1D); the fin's h is re-converged for the heat it really carries.")
    couple = {}
    print("   fin          t_mm   contact                          h_fin  R_tot | vented: T_motor Q_fin | sealed: T_motor Q_fin")
    for fin_name, e in EPS.items():
        for t_mm in (T_AS_BUILT, T_DESIGN):
            for rc_name, hc in contact.items():
                Rc = 1.0 / (hc * A_c * 1e-6)
                cv = coupled_converged(ALLOYS["6061-T6"], t_mm, e, Rc, "vented")
                cs = coupled_converged(ALLOYS["6061-T6"], t_mm, e, Rc, "sealed")
                couple[(fin_name, t_mm, rc_name)] = (cv, cs)
                print(f"   {fin_name:<12} {t_mm:6.3f}  {rc_name:<32} {cv['h']:5.2f} {cv['R_tot']:6.2f} |  {cv['r']['T_motor']:6.1f}  "
                      f"{cv['r']['q_fin']:5.2f}   |  {cs['r']['T_motor']:6.1f}  {cs['r']['q_fin']:5.2f}")
    for mode in ("vented", "sealed"):
        r0 = coupled_motor(P, None, mode)
        print(f"   no fin, {mode}: T_motor {r0['T_motor']:.1f} C (rise {r0['rise']:.1f} K), shell air {r0['T_inside']:.1f} C")
    out["couple"] = couple
    A_motor = 4 * 42.3 * 38.0 + 42.3 ** 2
    for mode in ("vented", "sealed"):
        row(f"motor-block convection h ({mode}) for model B-2", 1.0 / (R_MA[mode] * A_motor * 1e-6), "W/m2K",
            f"= 1/(R_ma {R_MA[mode]} K/W x {A_motor:.0f} mm2 of free faces)")
    out["A_motor"] = A_motor

    hr("B7. What the 60-minute hold test should read (as-built fin, 6061, painted, paste contact, vented, 23 C)")
    Rc_paste = 1.0 / (contact["thermal paste"] * A_c * 1e-6)
    cv, cs = couple[("black paint", T_AS_BUILT, "thermal paste")]
    r, fd1 = cv["r"], cv["fd"]
    q_fin = r["q_fin"]
    row("fin h (convection + radiation), converged", cv["h"], "W/m2K", "for the heat the fin carries")
    row("motor case rise over room (TC1)", r["rise"], "K", "coupled network")
    row("motor case temperature at 23 C room", r["T_motor"], "C", "")
    row("heat through the fin", q_fin, "W", "of %.2f W" % P)
    row("shell air temperature (vented)", r["T_inside"], "C", "")
    row("fin rise at the top of the contact patch (z=42)", fd1["base"], "K", "quasi-1D")
    row("fin rise at shell exit (z=50 mm)", fd1["exit"], "K", "quasi-1D")
    row("fin rise 50 mm above shell exit (TC2, z=100 mm)", fd1["at"](100.0), "K", "quasi-1D")
    row("fin rise at the tip (z=250 mm)", fd1["tip"], "K", "quasi-1D")
    ratio = fd1["at"](100.0) / r["rise"]
    row("TC2 rise / TC1 rise", ratio, "", "uniform-flux end; see the isothermal limit below")
    out["tc"] = dict(r=r, fd1=fd1, ratio=ratio)
    print("   Prediction RANGES, uniform heat flux into the patch -> isothermal flange (a die-cast aluminium nose on a steel can, or the")
    print("   k = 50 W/m.K block of model B-2, is close to isothermal; the truth lies between). Same inputs, 6061, paste, vented, 23 C:")
    iso_out = {}
    for fin_name, e in EPS.items():
        a = couple[(fin_name, T_AS_BUILT, "thermal paste")][0]
        b = coupled_converged(ALLOYS["6061-T6"], T_AS_BUILT, e, Rc_paste, "vented", isothermal=True)
        bs = coupled_converged(ALLOYS["6061-T6"], T_AS_BUILT, e, Rc_paste, "sealed", isothermal=True)
        iso_out[fin_name] = (a, b, bs)
        print(f"   {fin_name:<12} motor {a['r']['T_motor']:.1f} -> {b['r']['T_motor']:.1f} C (rise {a['r']['rise']:.1f} -> {b['r']['rise']:.1f} K); "
              f"fin heat {a['r']['q_fin']:.2f} -> {b['r']['q_fin']:.2f} W; patch top {a['fd']['base']:.1f} -> {b['fd']['base']:.1f} K; "
              f"y=100 {a['fd']['at'](100.0):.1f} -> {b['fd']['at'](100.0):.1f} K; tip {a['fd']['tip']:.2f} -> {b['fd']['tip']:.2f} K; "
              f"TC2/TC1 {a['fd']['at'](100.0)/a['r']['rise']:.2f} -> {b['fd']['at'](100.0)/b['r']['rise']:.2f}; sealed motor "
              f"{couple[(fin_name, T_AS_BUILT, 'thermal paste')][1]['r']['T_motor']:.1f} -> {bs['r']['T_motor']:.1f} C")
    print("   Hold-test finish test: TC2 steady-state rise painted 6.5-7.4 K, bare 9.9-10.9 K; thresholds painted <= 8 K, bare >= 9.5 K, "
          "8-9.5 K undecided; x 0.94 at 60 minutes. The ratio is only a cross-check (painted and bare ranges are ~0.06 apart).")
    out["iso"] = iso_out
    out["tr"] = {}
    for mode, cc in (("vented", cv), ("sealed", cs)):
        tr = transient_motor(P, cc["R_tot"], mode, minutes=120)
        final = cc["r"]["T_motor"]
        t95 = next((m_ for m_, tm, ts in tr if tm - T_AMB >= 0.95 * (final - T_AMB)), None)
        t60 = next((tm for m_, tm, ts in tr if m_ >= 60), None)
        out["tr"][mode] = tr
        print(f"   {mode}: motor at 60 min = {t60:.1f} C of steady {final:.1f} C; 95 % of the rise at "
              f"{'>120' if t95 is None else f'{t95:.0f}'} min")

    hr("B8. FEA targets (as-built, temperature RISE over ambient)")
    print("   The FORMULA (eta, R_fin, A = 2 x 44 x 200 mm) is referenced to the shell exit, z = 50 mm, where the 200 mm exposed")
    print("   length starts; the FEA at z = 50 should land within +/-20 % of it. At the top of the contact patch (z = 42.15) the")
    print("   rise is about 4 K higher (conduction along the 7.85 mm neck); the patch average is higher still (hole + spreading).")
    for fin_name in EPS:
        for t_mm in (T_AS_BUILT, T_DESIGN):
            tb = table[(t_mm, "6061-T6", fin_name)]
            f = tb["f"]
            fdd = tb["fd"]
            print(f"   {fin_name:<12} t {t_mm:5.3f} mm: eta {f['eta']:.3f}, R_fin {f['R']:.1f} K/W, formula rise at z=50 {tb['th_b']:.1f} K "
                  f"(band {0.8*tb['th_b']:.1f}-{1.2*tb['th_b']:.1f}); quasi-1D: z=42.15 {fdd['base']:.1f}, z=50 {fdd['exit']:.1f}, "
                  f"z=100 {fdd['at'](100.0):.1f}, tip {fdd['tip']:.2f} (formula {tb['th_tip']:.2f}), patch avg {fdd['patch_avg']:.1f} K")
    for alloy in ALLOYS:
        tb = table[(T_AS_BUILT, alloy, "black paint")]
        print(f"   alloy {alloy:<9} (painted, 0.483 mm): eta {tb['f']['eta']:.3f}, R_fin {tb['f']['R']:.1f} K/W, formula rise at z=50 {tb['th_b']:.1f} K")
    return out


def main(argv: list[str]) -> None:
    use_step = "--no-step" not in argv
    only_static = "--static" in argv
    only_thermal = "--thermal" in argv
    print("simulation_loads.py: loads and targets for the SolidWorks Simulation studies")
    if not only_thermal:
        report_static(use_step)
    if not only_static:
        report_thermal()


if __name__ == "__main__":
    main(sys.argv[1:])
