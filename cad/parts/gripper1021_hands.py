"""
Gripper 1021 HANDS -- left and right coupler links of Jasper's four-bar gripper
(cad/reference/gripper_1021, spec cad/GRIPPER_1021_SPEC.md).

Each hand joins a crank pin A (compound / follower) to an arm-tip pin B.  Both are M3 screws used as pins
(button head from the top, nyloc nut in a pocket in the bed face).  The hand is built directly in
Jasper's ASSEMBLY WORLD frame at the CLOSED pose (crank angle -62 deg, grip faces on x = tube axis);
`place_hand()` moves it rigidly to any other crank angle (the file pose -52.1 deg for the STEP export,
the sweep angles for the interference check).

Frame (world, mm): tube axis = line x = GRIP1021_AXIS_X, z = GRIP1021_AXIS_Z along y; +y up (toward
the housing), +z toward the servo.  The hand stands on its bed face z = 1090.0 (print orientation = +z up).

Layers (z):   1090.0 .. 1098.0   link plate (hull of R8 @ A, R8.5 @ B, + web down to the palm)
              1098.0 .. 1098.99  A boss  (right; 1099.99 on the left: follower crank sits 1 mm higher)
              1098.0 .. 1101.49  B boss  (both)
              1090.0 .. 1118.0   finger + palm, y <= 628.4 only (full width), grip face x = tube axis

Lightening (all windows go through z, constant section -> prints on the bed face with no supports, no bridges;
every wall >= GRIP1021_WALL_MIN = 3.0 mm, measured from the nominal grip face, i.e. excluding the 0.8 mm ridge grooves):
  * link plate: one waist window between the two nut pockets,
  * finger: closed ladder (grip wall + outer skin + tip wedge) with one slot,
  * palm: triangle frame (grip wall, 3 mm top bar, 45 deg strut to the web foot) with one window.
Mass at 3.0 mm walls is ~21.5 g solid PETG per hand; 2.5 mm walls would give ~19 g (GRIP1021_WALL_MIN).

The right hand is built by _build("R"); the left hand is its mirror about x = tube axis with the A boss 1 mm taller.
Run `python -m cad.parts.gripper1021_hands` to build both, export STEP (file pose) + STL (print pose) into
exports/ and write a preview PNG; scripts/build_gripper1021.py adds the sweep, measurements and all renders.
"""

from __future__ import annotations

import math

import cadquery as cq

from .. import params as P

# --- frame / mechanism (authoritative values live in cad/params.py) ------------------------------------------------
AX = P.GRIP1021_AXIS_X
O2 = P.GRIP1021_O2
O4 = P.GRIP1021_O4
CRANK_R = P.GRIP1021_CRANK_R
ROCKER_R = P.GRIP1021_ROCKER_R
COUPLER = P.GRIP1021_COUPLER
THETA_CLOSED = P.GRIP1021_THETA_CLOSED_DEG
THETA_FILE = P.GRIP1021_THETA_FILE_DEG

ZO = P.GRIP1021_Z_FILE_OFFSET                     # Jasper's files are 0.000129 mm below the nominal z values
Z0 = P.GRIP1021_Z_BED + ZO
Z_PLATE = P.GRIP1021_Z_PLATE_TOP + ZO
Z_TOP = P.GRIP1021_Z_PALM_TOP + ZO
Z_BOSS_B = P.GRIP1021_Z_BOSS_B + ZO
Z_BOSS_A = {"R": P.GRIP1021_Z_BOSS_A_RIGHT + ZO, "L": P.GRIP1021_Z_BOSS_A_LEFT + ZO}
OVERTRAVEL = 0.5                      # mm, cutter overshoot for clean through cuts


# --- four-bar ---------------------------------------------------------------------------------------------------
def solve_fourbar(theta_deg: float, coupler: float = COUPLER):
    """Right-side crank pin A and arm tip B for compound crank angle theta (deg, world frame).

    B is the intersection of the rocker circle (O4, 50) and the coupler circle (A, c) on the
    'parallel' branch (rocker angle nearest the crank angle), as in fourbar.py."""
    t = math.radians(theta_deg)
    a_pt = (O2[0] + CRANK_R * math.cos(t), O2[1] + CRANK_R * math.sin(t))
    dx, dy = a_pt[0] - O4[0], a_pt[1] - O4[1]
    d = math.hypot(dx, dy)
    if d > ROCKER_R + coupler or d < abs(ROCKER_R - coupler):
        raise ValueError(f"four-bar cannot close at theta={theta_deg}")
    a = (ROCKER_R ** 2 - coupler ** 2 + d ** 2) / (2 * d)
    h = math.sqrt(max(ROCKER_R ** 2 - a ** 2, 0.0))
    ux, uy = dx / d, dy / d
    px, py = O4[0] + a * ux, O4[1] + a * uy
    sols = [(px - h * uy, py + h * ux), (px + h * uy, py - h * ux)]

    def branch_gap(b):
        th4 = math.atan2(b[1] - O4[1], b[0] - O4[0])
        return abs(((th4 - t + math.pi) % (2 * math.pi)) - math.pi)

    return a_pt, min(sols, key=branch_gap)


def mirror_pt(p):
    """Mirror a world (x, y) point about the tube-axis plane x = AX."""
    return (2 * AX - p[0], p[1])


A_C, B_C = solve_fourbar(THETA_CLOSED)            # closed pose, right hand
A_F, B_F = solve_fourbar(THETA_FILE)              # Jasper's file pose, right hand
HAND_DIR = math.atan2(B_C[1] - A_C[1], B_C[0] - A_C[0])      # A -> B direction at the closed pose (rad)
assert abs(math.dist(A_C, B_C) - COUPLER) < 1e-9
assert abs((B_C[1] - P.GRIP1021_PALM_B_CLEAR) - P.GRIP1021_PALM_CUT_Y) < 0.05, "palm cut line is B_y - 12.5"

# --- derived dimensions ----------------------------------------------------------------------------------------------
T = P.GRIP1021_WALL_MIN
XG = AX                                           # grip face plane
XF = AX + P.GRIP1021_FINGER_T                     # finger outer face
Y_CUT = P.GRIP1021_PALM_CUT_Y                     # palm / finger top
Y_TIP = P.GRIP1021_TIP_Y
TIP_R = P.GRIP1021_TIP_ROUND_R
TAN_CH = math.tan(math.radians(P.GRIP1021_TIP_CHAMFER_DEG))
Y_CH_END = Y_TIP + (XF - XG - TIP_R) * TAN_CH     # chamfer reaches the outer face at this y
X_PALM_R = B_C[0] + P.GRIP1021_PALM_RIGHT_DX      # palm top-right (strut apex), under the web foot
HOLE_R = P.GRIP1021_PIN_HOLE_D / 2
BOSS_R = P.GRIP1021_BOSS_D / 2
NUT_RC = P.GRIP1021_NUT_AF / math.sqrt(3.0)       # hex circumradius


# --- small helpers -----------------------------------------------------------------------------------------------------
def prism(pts, z0, z1) -> cq.Workplane:
    """Closed polygon (world x, y) extruded from z0 to z1."""
    return cq.Workplane("XY").workplane(offset=z0).polyline(list(pts)).close().extrude(z1 - z0)


def cyl(x, y, r, z0, z1) -> cq.Workplane:
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)


def union_all(shapes):
    out = None
    for s in shapes:
        out = s if out is None else out.union(s)
    return out


def bar(p0, p1, w, z0, z1) -> cq.Workplane:
    """Straight bar of width w (perpendicular to p0 -> p1), ends square, extruded z0..z1."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    n = math.hypot(dx, dy)
    nx, ny = -dy / n * w / 2, dx / n * w / 2
    return prism([(p0[0] + nx, p0[1] + ny), (p1[0] + nx, p1[1] + ny),
                  (p1[0] - nx, p1[1] - ny), (p0[0] - nx, p0[1] - ny)], z0, z1)


def hull_two_circles(c1, r1, c2, r2):
    """Polygon (tangent trapezoid) that, united with the two circles, is their convex hull."""
    dx, dy = c2[0] - c1[0], c2[1] - c1[1]
    d = math.hypot(dx, dy)
    ux, uy = dx / d, dy / d
    k = (r1 - r2) / d
    s = math.sqrt(1 - k * k)
    pts = []
    for sg in (1, -1):
        mx = k * ux - sg * s * uy
        my = k * uy + sg * s * ux
        pts.append(((c1[0] + r1 * mx, c1[1] + r1 * my), (c2[0] + r2 * mx, c2[1] + r2 * my)))
    (a1, b1), (a2, b2) = pts
    return [a1, b1, b2, a2]


# --- link plate ---------------------------------------------------------------------------------------------------------
def make_plate() -> cq.Workplane:
    """z 1090 .. 1098: hull(R8 @ A, R8.5 @ B) + web from B down to the palm cut line."""
    rA, rB = P.GRIP1021_PLATE_R_A, P.GRIP1021_PLATE_R_B
    plate = prism(hull_two_circles(A_C, rA, B_C, rB), Z0, Z_PLATE)
    plate = plate.union(cyl(*A_C, rA, Z0, Z_PLATE)).union(cyl(*B_C, rB, Z0, Z_PLATE))
    # web: from the B circle down to the palm top bar (overlaps the bar by T so the two fuse); it tapers toward the
    # palm apex so it follows the load path to the finger
    web = prism([(B_C[0] - rB, B_C[1]), (B_C[0] + rB, B_C[1]),
                 (X_PALM_R, Y_CUT - T), (X_PALM_R - P.GRIP1021_WEB_FOOT_W, Y_CUT - T)], Z0, Z_PLATE)
    return plate.union(web)


# --- convex window polygons from half-planes ----------------------------------------------------------------------------
def halfplane_polygon(planes, extent=400.0):
    """Convex polygon {p : n.p <= d for every (nx, ny, d)} clipped from a large square around the hand."""
    cx, cy = A_C[0], 0.5 * (A_C[1] + Y_TIP)
    poly = [(cx - extent, cy - extent), (cx + extent, cy - extent), (cx + extent, cy + extent), (cx - extent, cy + extent)]
    for nx, ny, d in planes:
        out = []
        for i, p in enumerate(poly):
            q = poly[(i + 1) % len(poly)]
            sp, sq = nx * p[0] + ny * p[1] - d, nx * q[0] + ny * q[1] - d
            if sp <= 0:
                out.append(p)
            if (sp < 0 < sq) or (sq < 0 < sp):
                u = sp / (sp - sq)
                out.append((p[0] + u * (q[0] - p[0]), p[1] + u * (q[1] - p[1])))
        poly = out
        if not poly:
            raise ValueError("empty window polygon")
    return poly


def line_plane(p0, p1, side_pt, offset=0.0):
    """Half-plane bounded by the line p0-p1 shifted by `offset` toward side_pt (the kept side contains side_pt)."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    n = math.hypot(dx, dy)
    nx, ny = -dy / n, dx / n
    if nx * (side_pt[0] - p0[0]) + ny * (side_pt[1] - p0[1]) < 0:
        nx, ny = -nx, -ny
    # kept side is n.(p - p0) >= 0  ->  (-n).p <= -n.p0 ; shift the line toward the kept side by `offset`
    return (-nx, -ny, -(nx * p0[0] + ny * p0[1]) - offset)


def window_cutter(poly, fillet_r=1.5) -> cq.Workplane:
    """Through-z cutter for a convex window polygon, vertical edges rounded (no stress-raising corners)."""
    w = prism(poly, Z0 - OVERTRAVEL, Z_TOP + OVERTRAVEL)
    return w.edges("|Z").fillet(fillet_r) if fillet_r > 0 else w


# --- finger + palm --------------------------------------------------------------------------------------------------------
Y_GUSSET = Y_CUT - P.GRIP1021_GUSSET_DROP        # where the diagonal strut leaves the finger outer face
SPINE_T = T + (P.GRIP1021_RIDGE_DEPTH if P.GRIP1021_WALL_FROM_RIDGE_ROOT else 0.0)   # grip wall at the crest plane
FIN_R = P.GRIP1021_WINDOW_FILLET_R


def finger_block() -> cq.Workplane:
    """Solid outline (before windows): grip face x = AX from the cut line down to the R3 round, 30 deg wedge
    on the outer bottom edge, outer face up to the strut start, diagonal to the palm top-right, cut line.
    Extruded z 1090 .. 1118."""
    cx, cy = XG + TIP_R, Y_TIP + TIP_R
    mid = (cx - TIP_R * math.cos(math.radians(45)), cy - TIP_R * math.sin(math.radians(45)))
    return (cq.Workplane("XY").workplane(offset=Z0)
            .moveTo(XG, Y_CUT).lineTo(XG, cy).threePointArc(mid, (cx, Y_TIP))
            .lineTo(XF, Y_CH_END).lineTo(XF, Y_GUSSET).lineTo(X_PALM_R, Y_CUT).close()
            .extrude(Z_TOP - Z0))


def finger_windows() -> list:
    """Through-z lightening windows (closed; every wall >= T from the outer surface, grooves included, and from
    the other windows).  Two windows: F in the finger, below the strut; G above the strut (between the grip
    wall, the top bar and the strut)."""
    wedge0, wedge1 = (XG + TIP_R, Y_TIP), (XF, Y_CH_END)
    hyp0, hyp1 = (XF, Y_GUSSET), (X_PALM_R, Y_CUT)          # strut lower (outer) face
    inside_f = (0.5 * (XG + XF), Y_TIP + 20.0)
    slot = halfplane_polygon([
        (-1.0, 0.0, -(XG + SPINE_T)),                 # grip wall
        (1.0, 0.0, XF - T),                           # outer skin
        line_plane(wedge0, wedge1, inside_f, T),      # tip wedge: T off the chamfer face
        line_plane(hyp0, hyp1, inside_f, 0.0),        # strut lower face (the slot ends on it)
    ])
    gus = halfplane_polygon([
        (-1.0, 0.0, -(XG + SPINE_T)),                 # grip wall
        (0.0, 1.0, Y_CUT - T),                        # top bar
        line_plane(hyp0, hyp1, (XG + SPINE_T + 1.0, Y_CUT - 2.0), T),      # strut upper face (strut is T thick)
    ])
    slot_w = (XF - T) - (XG + SPINE_T)
    return [window_cutter(slot, min(FIN_R, 0.4 * slot_w)), window_cutter(gus, FIN_R)]


def ridge_cutters() -> cq.Workplane:
    """Horizontal (along z) V-grooves in the grip face: depth 0.8, pitch 3.0, crest land 0.8.  They are
    cut INTO the face (x >= AX) so the two faces still meet at the closed pose."""
    d, pitch = P.GRIP1021_RIDGE_DEPTH, P.GRIP1021_RIDGE_PITCH
    w = pitch - P.GRIP1021_RIDGE_LAND
    cuts = []
    for k in range(P.GRIP1021_RIDGE_N):
        y0 = P.GRIP1021_RIDGE_Y0 + k * pitch
        cuts.append(prism([(XG - 1.0, y0), (XG, y0), (XG + d, y0 + w / 2), (XG, y0 + w), (XG - 1.0, y0 + w)],
                          Z0 - OVERTRAVEL, Z_TOP + OVERTRAVEL))
    return union_all(cuts)


def plate_window() -> cq.Workplane:
    """One waist window in the link plate between the two nut pockets (walls >= T to the hull sides and
    to the pockets' circumcircles)."""
    rA, rB = P.GRIP1021_PLATE_R_A, P.GRIP1021_PLATE_R_B
    a1, b1, b2, a2 = hull_two_circles(A_C, rA, B_C, rB)
    mid = ((A_C[0] + B_C[0]) / 2, (A_C[1] + B_C[1]) / 2)
    ux, uy = (B_C[0] - A_C[0]) / COUPLER, (B_C[1] - A_C[1]) / COUPLER
    e = NUT_RC + T                                      # keep-out along the link from each pin axis
    poly = halfplane_polygon([
        line_plane(a1, b1, mid, T),
        line_plane(a2, b2, mid, T),
        (-ux, -uy, -(ux * A_C[0] + uy * A_C[1]) - e),   # A end
        (ux, uy, ux * B_C[0] + uy * B_C[1] - e),        # B end
    ])
    w = prism(poly, Z0 - OVERTRAVEL, Z_PLATE + OVERTRAVEL)
    return w.edges("|Z").fillet(FIN_R)


def nut_pocket(c) -> cq.Workplane:
    """M3 nyloc pocket in the bed face: hex 5.7 AF, vertices pointing sideways (across the link), 4.2 deep."""
    base = HAND_DIR + math.pi / 2
    pts = [(c[0] + NUT_RC * math.cos(base + k * math.pi / 3), c[1] + NUT_RC * math.sin(base + k * math.pi / 3))
           for k in range(6)]
    return prism(pts, Z0 - OVERTRAVEL, Z0 + P.GRIP1021_NUT_DEPTH)


def make_hand_right() -> cq.Workplane:
    """Right hand at the closed pose, world frame."""
    return _build("R")


def _build(side: str) -> cq.Workplane:
    block = finger_block()
    for w in finger_windows():
        block = block.cut(w)
    block = block.cut(ridge_cutters())
    hand = block.union(make_plate().cut(plate_window()))
    # joint bosses (washer faces) rising from the plate top
    hand = hand.union(cyl(*A_C, BOSS_R, Z_PLATE - 0.5, Z_BOSS_A[side]))
    hand = hand.union(cyl(*B_C, BOSS_R, Z_PLATE - 0.5, Z_BOSS_B))
    for c in (A_C, B_C):
        hand = hand.cut(cyl(*c, HOLE_R, Z0 - OVERTRAVEL, Z_BOSS_B + OVERTRAVEL)).cut(nut_pocket(c))
    return hand


# --- mirror / pose -------------------------------------------------------------------------------------------------------------
def mirror_x(shape):
    """Mirror about the tube-axis plane x = AX (Workplane or Shape)."""
    if isinstance(shape, cq.Workplane):
        return cq.Workplane("XY").add(shape.val().mirror("YZ", (AX, 0, 0)))
    return shape.mirror("YZ", (AX, 0, 0))


def make_hand_left() -> cq.Workplane:
    """Left hand at the closed pose: mirror of the right hand, A boss 1 mm taller."""
    return mirror_x(_build("L"))


def place_hand(hand, side: str, theta_deg: float):
    """Rigid move of a closed-pose hand (Workplane) so that A and B land on the four-bar positions for
    compound crank angle theta_deg.  side 'R' (compound / right arm) or 'L' (mirrored motion)."""
    if side == "L":
        return mirror_x(place_hand(mirror_x(hand), "R", theta_deg))
    a_t, b_t = solve_fourbar(theta_deg)
    rot = math.degrees(math.atan2(b_t[1] - a_t[1], b_t[0] - a_t[0]) - HAND_DIR)
    s = hand.val().rotate(cq.Vector(A_C[0], A_C[1], 0), cq.Vector(A_C[0], A_C[1], 1), rot)
    s = s.translate(cq.Vector(a_t[0] - A_C[0], a_t[1] - A_C[1], 0))
    return cq.Workplane("XY").add(s)


def hole_centres(hand_shape, tol_r=0.05):
    """Axis positions (x, y) of the Ø3.2 pin holes found in a built hand (cylindrical faces of radius 3.2/2)."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    out = []
    for f in hand_shape.Faces():
        if f.geomType() != "CYLINDER":
            continue
        cy_ = BRepAdaptor_Surface(f.wrapped).Cylinder()
        if abs(cy_.Radius() - HOLE_R) < tol_r:
            loc = cy_.Axis().Location()
            out.append((loc.X(), loc.Y()))
    return out


# --- export (STEP at Jasper's file pose, STL in print orientation) -------------------------------------------------------------------
import os                                                          # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STEP_DIR = os.path.join(_REPO, "exports", "step")
STL_DIR = os.path.join(_REPO, "exports", "stl")


def to_print_pose(shape):
    """Closed-pose hand moved so its bed face is z = 0 and its bounding box starts at x = y = 0."""
    bb = shape.BoundingBox()
    return shape.translate(cq.Vector(-bb.xmin, -bb.ymin, -bb.zmin))


def export_all(step_dir: str = STEP_DIR, stl_dir: str = STL_DIR) -> dict:
    """Write gripper1021_hand_{right,left}.step (assembly world frame, Jasper's file pose, theta = -52.1 deg) and
    gripper1021_hand_{right,left}.stl (closed-pose geometry in print orientation).  Returns the paths."""
    os.makedirs(step_dir, exist_ok=True)
    os.makedirs(stl_dir, exist_ok=True)
    hands = {"right": (make_hand_right(), "R"), "left": (make_hand_left(), "L")}
    out = {}
    for nm, (wp, side) in hands.items():
        step = os.path.join(step_dir, f"gripper1021_hand_{nm}.step")
        cq.exporters.export(place_hand(wp, side, THETA_FILE), step)
        stl = os.path.join(stl_dir, f"gripper1021_hand_{nm}.stl")
        cq.exporters.export(cq.Workplane("XY").add(to_print_pose(wp.val())), stl, tolerance=0.02, angularTolerance=0.1)
        out[nm] = {"step": step, "stl": stl}
    return out


if __name__ == "__main__":
    for nm, mk in (("right", make_hand_right), ("left", make_hand_left)):
        h = mk()
        v = h.val()
        bb = v.BoundingBox()
        print(f"{nm}: valid={v.isValid()} solids={len(h.solids().vals())} vol={v.Volume():.0f} mm3 "
              f"mass={v.Volume() * P.GRIP1021_PETG_G_CM3 / 1000:.2f} g bbox x[{bb.xmin:.3f},{bb.xmax:.3f}] "
              f"y[{bb.ymin:.3f},{bb.ymax:.3f}] z[{bb.zmin:.3f},{bb.zmax:.3f}]")
    paths = export_all()
    from ..mesh_tools import tessellate, render
    prev_dir = os.path.join(_REPO, "renders", "gripper1021")
    os.makedirs(prev_dir, exist_ok=True)
    for nm, mk, col in (("right", make_hand_right, (0.25, 0.55, 0.88)), ("left", make_hand_left, (0.30, 0.72, 0.45))):
        V, F = tessellate(mk(), 0.03, 0.15)
        render([(V, F, col, 1.0)], os.path.join(prev_dir, f"preview_hand_{nm}.png"), 28, -58,
               f"gripper1021 hand {nm} (closed pose, bed face z = 1090)", up="z")
    for nm, d in paths.items():
        print(nm, d["step"], d["stl"])
