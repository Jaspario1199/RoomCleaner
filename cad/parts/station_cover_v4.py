"""
Winch-station cover v4 -- the user's SolidWorks shell (Shell_Casing.step) MODIFIED
in CadQuery, so every mating interface of the original shell is preserved
exactly (rim plane x = -21.15, four M3 corner pockets, shelves, cable-path
openings in the bottom wall).  Added on top of the imported shell:

  1. Open fin alcove (chimney) for the aluminium heat-spreader fin: top wall and
     -y side wall are removed over the alcove footprint; a floor plate, a +y wall
     and a room-side wall close the electronics/motor interior underneath.
  2. Fin slot through the alcove floor, open all the way to the rim (x = -21.15)
     so the shell can be slid on along -x over an installed fin, with a 1 x 2 mm
     foam-gasket groove around the slot top edge.
  3. M3 heat-set bosses: 4 on the upper shelf (perfboard), 2 on the lower shelf
     (buck module).
  4. Convection vents: inlet slots in the bottom wall, outlet slots high on both
     side walls and on the front wall.  Nothing on the top face, nothing into the
     alcove.
  5. USB-C service port in the front wall.

Station frame (identical to cad/reference/station_v3/*.step):
    origin = motor shaft axis at the motor flange face;  +x out of the wall into
    the room;  +y along the shaft toward the spool;  +z up.  All lengths in mm.

Run:   /usr/bin/python3 -m cad.parts.station_cover_v4
Outputs:
    cad/exports/station_cover_v4/station_cover_v4.step / .stl
    renders/station_cover_v4/*.png            (7 standard views + assembly/sections)
    verification/station_cover_v4_implementer_notes.md
"""

from __future__ import annotations

import math
from pathlib import Path

import cadquery as cq

# --------------------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[2]
REF_DIR = ROOT / "cad" / "reference" / "station_v3"
SHELL_STEP = REF_DIR / "Shell_Casing.step"
EXPORT_DIR = ROOT / "cad" / "exports" / "station_cover_v4"
RENDER_DIR = ROOT / "renders" / "station_cover_v4"
NOTES_PATH = ROOT / "verification" / "station_cover_v4_implementer_notes.md"

# --------------------------------------------------------------------------- imported-shell datums
# Measured from Shell_Casing.step; make() asserts them against the imported solid.
RIM_X = -21.15                 # open face / mating rim plane
SHELL_X_MAX = 98.85            # outer face of the front wall
SHELL_Y_MIN = -48.09           # outer face of the -y side wall
SHELL_Y_MAX_OUTER = 79.21      # outer face of the +y side wall
SHELL_Z_MAX = 68.19            # outer face of the top wall
INNER_Y_MIN = -43.09           # inner face of the -y side wall
INNER_Y_MAX = 74.21            # inner face of the +y side wall
INNER_X_MAX = 93.85            # inner face of the front wall
INNER_Z_TOP = 63.19            # inner face of the top wall
BOTTOM_OUTER_Z = -51.81        # outer face of the bottom wall (flat part)
BOTTOM_INNER_Z = -46.81        # inner face of the bottom wall
WALL_5 = 5.0                   # original wall thickness
FLAT_X_END = 88.85             # outer R10 front rounding starts here
FRONT_FLAT_Y = (-38.09, 69.21)  # flat part of the front wall inner face (y)
SHELF_X_MIN = 38.85            # shelves start here (back edge)
UPPER_SHELF_TOP_Z = 27.19
LOWER_SHELF_TOP_Z = -9.81
SHELF_T = 2.0
SHELF_HOLE_X = (59.85, 69.85)  # the single rounded-square wire hole (R4 corners) in each shelf
SHELF_HOLE_Y = (10.56, 20.56)
CORNER_HOLE_Y = (-43.09, 74.21)      # M3 corner pockets (along x), y positions
CORNER_HOLE_Z = (63.48, -47.10)      # and z positions
CORNER_HOLE_D = 3.4
CORNER_HOLE_DEPTH = 20.0

# --------------------------------------------------------------------------- fin / alcove (design parameters)
FIN_T = 4.76                   # 3/16" plate (3.175 also fits: slot is sized from FIN_T)
FIN_W = 44.0
FIN_X_HALF = FIN_W / 2.0       # fin spans x [-22, +22]
FIN_BOTTOM_Z = -21.0
FIN_H = 250.0
FIN_TOP_Z = FIN_BOTTOM_Z + FIN_H
FIN_SLOT_CLEAR = 0.4           # per side
FIN_AIR_GAP = 12.0
WALL = 2.5                     # new internal walls
ALCOVE_FLOOR_Z = 25.5          # underside of the alcove floor
ALCOVE_X_MAX = FIN_X_HALF + FIN_AIR_GAP + 1.0   # = 35.0, inner face of room-side wall
ALCOVE_Y_MAX = FIN_AIR_GAP                       # inner face of the +y alcove wall
GASKET_DEPTH = 1.0
GASKET_WIDTH = 2.0

# The original -y/top corner M3 pocket lies inside the alcove cut.  Keep the
# original shell material around it (and the wall column down to the floor) so
# the screw pocket and its load path survive.
CORNER_POST_BACK_WALL = 3.0                       # material behind the pocket bottom
CORNER_POST_X_MAX = RIM_X + CORNER_HOLE_DEPTH + CORNER_POST_BACK_WALL   # 1.85
CORNER_POST_Y_MAX = SHELL_Y_MIN + 10.0            # -38.09

# --------------------------------------------------------------------------- electronics bosses
BOSS_D = 7.0
BOSS_H = 6.0
BOSS_SINK = 1.0                # boss starts this far below the shelf top (fuses to the shelf)
BOSS_HOLE_D = 4.0              # M3 heat-set insert
BOSS_HOLE_DEPTH = 5.5
BOARD_CX = 66.35
BOARD_CY = 15.56
PERF_L = 70.0                  # along y
PERF_W = 50.0                  # along x
PERF_HOLE_INSET = 2.0
BUCK_HOLE_PITCH = 30.0         # along y

# --------------------------------------------------------------------------- vents
SLOT_W = 2.5                   # finger / debris safe
VENT_EDGE_KEEPOUT = 6.0        # to wall edges, bosses, holes
VENT_WEB_MIN = 3.0
INLET_L = 22.0
INLET_X0 = 50.0                # first inlet column (x)
INLET_X_PITCH = SLOT_W + 3.5   # 6.0 -> 3.5 mm webs
INLET_N_COLS = 7
INLET_Y_CENTERS = (-24.0, 2.0, 28.0, 54.0)   # grid candidates; keep-out filter drops some
OUTLET_L = 22.0
OUTLET_SIDE_L = 24.0
OUTLET_Z_ROWS = (47.0, 53.0)   # between z 45 and 60
OUTLET_FRONT_Y_PITCH = OUTLET_L + 3.5
OUTLET_FRONT_N = 3
OUTLET_SIDE_X_CENTER = 63.2    # centre of the usable flat part of the side walls (x 43.5..82.85)
VENT_CUT_DEPTH = 8.0           # cutter thickness, centred on the wall mid-plane

# --------------------------------------------------------------------------- USB service port (front wall)
# Motor back-end relief: the fin pushes the motor back by FIN_T, leaving only
# 0.33 mm (4.76 fin) to the -y side wall's inner face. A shallow pocket in that
# wall restores printable clearance (wall stays >= 3 mm there).
MOTOR_HALF = 21.15
MOTOR_BACK_Y = -38.0 - FIN_T           # motor back face with the fin installed
MOTOR_RELIEF_DEPTH = 2.0               # into the 5 mm wall
MOTOR_RELIEF_MARGIN = 1.5              # around the 42.3 mm motor square (x, z)

USB_PORT_W = 12.0              # along y
USB_PORT_H = 7.0               # along z
USB_PORT_R = 3.0               # corner radius
USB_PORT_Y = 15.56
USB_PORT_Z = 35.0

PETG_DENSITY_G_CM3 = 1.27
EPS = 1e-6


# =========================================================================== helpers
def _box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    """Axis-aligned box from min/max coordinates."""
    return (cq.Workplane("XY")
            .box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


def tight_bbox(shape) -> tuple:
    """(xmin, xmax, ymin, ymax, zmin, zmax) without OCC's tolerance padding."""
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape.wrapped, box, False, False)
    x0, y0, z0, x1, y1, z1 = box.Get()
    return (x0, x1, y0, y1, z0, z1)


def _outer_datums(shell: cq.Workplane) -> tuple:
    """Exact plane positions of the rim (x min), outer -y wall and outer top face, read from
    the imported planar faces (bounding boxes carry ~1e-5 mm of tolerance padding)."""
    def plane_pos(normal, axis, pick):
        vals = [getattr(f.Center(), axis) for f in shell.faces().vals()
                if f.geomType() == "PLANE" and (f.normalAt() - cq.Vector(*normal)).Length < 1e-6]
        return pick(vals)
    return (plane_pos((-1, 0, 0), "x", min), plane_pos((0, -1, 0), "y", min),
            plane_pos((0, 0, 1), "z", max))


def _union_all(items):
    out = items[0]
    for it in items[1:]:
        out = out.union(it)
    return out


def _slot_cutter(long_dir: str, through_dir: str, length: float, center) -> cq.Workplane:
    """Stadium-ended slot (SLOT_W wide) as a cutter solid of thickness VENT_CUT_DEPTH.
    long_dir / through_dir in {'x','y','z'}; the third axis is the slot width."""
    base = (cq.Workplane("XY").slot2D(length, SLOT_W, 0)
            .extrude(VENT_CUT_DEPTH / 2.0, both=True))        # long X, width Y, through Z
    key = (long_dir, through_dir)
    if key == ("x", "z"):
        sol = base
    elif key == ("y", "z"):
        sol = base.rotate((0, 0, 0), (0, 0, 1), 90)
    elif key == ("x", "y"):                                    # side walls
        sol = base.rotate((0, 0, 0), (1, 0, 0), 90)
    elif key == ("y", "x"):                                    # front wall
        sol = base.rotate((0, 0, 0), (0, 0, 1), 90).rotate((0, 0, 0), (0, 1, 0), 90)
    else:
        raise ValueError(f"unsupported slot orientation {key}")
    return sol.translate(center)


def _rect_circle_gap(rx0, rx1, ry0, ry1, cx, cy, r) -> float:
    """Distance from an axis-aligned rectangle to a circle's edge (negative = overlap)."""
    dx = max(rx0 - cx, 0.0, cx - rx1)
    dy = max(ry0 - cy, 0.0, cy - ry1)
    return math.hypot(dx, dy) - r


def _rect_rect_gap(a, b) -> float:
    dx = max(a[0] - b[1], b[0] - a[1], 0.0)
    dy = max(a[2] - b[3], b[2] - a[3], 0.0)
    return math.hypot(dx, dy)


# =========================================================================== layout (pure numbers)
def boss_layout():
    """(x, y, shelf_top_z, tag) for every heat-set boss."""
    hx = PERF_W / 2.0 - PERF_HOLE_INSET
    hy = PERF_L / 2.0 - PERF_HOLE_INSET
    out = [(BOARD_CX + sx * hx, BOARD_CY + sy * hy, UPPER_SHELF_TOP_Z, "perf")
           for sx in (-1, 1) for sy in (-1, 1)]
    out += [(BOARD_CX, BOARD_CY + sy * BUCK_HOLE_PITCH / 2.0, LOWER_SHELF_TOP_Z, "buck")
            for sy in (-1, 1)]
    return out


def inlet_layout():
    """Inlet slot centres (x, y) that keep VENT_EDGE_KEEPOUT from bosses, the shelf wire
    hole and the bay edges (plan-view projections)."""
    bosses = boss_layout()
    hole = (SHELF_HOLE_X[0], SHELF_HOLE_X[1], SHELF_HOLE_Y[0], SHELF_HOLE_Y[1])
    half_l = INLET_L / 2.0
    half_w = SLOT_W / 2.0
    y_lo, y_hi = INNER_Y_MIN + VENT_EDGE_KEEPOUT, INNER_Y_MAX - VENT_EDGE_KEEPOUT
    x_hi = FLAT_X_END - 1.0
    pts = []
    for ix in range(INLET_N_COLS):
        x = INLET_X0 + ix * INLET_X_PITCH
        for y in INLET_Y_CENTERS:
            rect = (x - half_w, x + half_w, y - half_l, y + half_l)
            if rect[2] < y_lo or rect[3] > y_hi or rect[1] > x_hi:
                continue
            if any(_rect_circle_gap(*rect, bx, by, BOSS_D / 2.0) < VENT_EDGE_KEEPOUT
                   for bx, by, _, _ in bosses):
                continue
            if _rect_rect_gap(rect, hole) < VENT_EDGE_KEEPOUT:
                continue
            pts.append((x, y))
    return pts


def side_outlet_layout():
    """(x, z) centres on each side wall."""
    return [(OUTLET_SIDE_X_CENTER, z) for z in OUTLET_Z_ROWS]


def front_outlet_layout():
    """(y, z) centres on the front wall."""
    ys = [USB_PORT_Y + (k - (OUTLET_FRONT_N - 1) / 2.0) * OUTLET_FRONT_Y_PITCH
          for k in range(OUTLET_FRONT_N)]
    return [(y, z) for z in OUTLET_Z_ROWS for y in ys]


# =========================================================================== geometry
def load_shell() -> cq.Workplane:
    """The user's SolidWorks shell, verified against the datums above."""
    shell = cq.importers.importStep(str(SHELL_STEP))
    bb = shell.val().BoundingBox()
    for name, got, want in (("xmin", bb.xmin, RIM_X), ("xmax", bb.xmax, SHELL_X_MAX),
                            ("ymin", bb.ymin, SHELL_Y_MIN), ("zmax", bb.zmax, SHELL_Z_MAX)):
        assert abs(got - want) < 0.01, f"input shell {name}={got} differs from datum {want}"
    assert len(shell.solids().vals()) == 1, "input shell must be a single solid"
    return shell


def build_cover() -> cq.Workplane:
    shell = load_shell()
    # The SolidWorks export carries ~5 um of origin offset (rim at -21.1458, not -21.15):
    # take the three outer datum planes from the imported solid so new walls are exactly flush.
    rim_x, y_min, z_max = _outer_datums(shell)
    z_alc_top = ALCOVE_FLOOR_Z + WALL            # 28.0, top of the alcove floor
    x_new_max = ALCOVE_X_MAX + WALL              # 37.5
    y_new_max = ALCOVE_Y_MAX + WALL              # 14.5
    far = 5.0                                    # overshoot of cutters past the outer faces

    # 1a. open the alcove (top + -y side), but keep the original corner-pocket material
    cut_box = _box(rim_x - far, ALCOVE_X_MAX, y_min - far, ALCOVE_Y_MAX,
                   z_alc_top, z_max + far)
    keep_post = _box(rim_x - far, CORNER_POST_X_MAX, y_min - far, CORNER_POST_Y_MAX,
                     z_alc_top - far, z_max + far)
    shell = shell.cut(cut_box.cut(keep_post))

    # 1b. new internal walls (all fuse to the remaining shell)
    floor = _box(rim_x, x_new_max, y_min, y_new_max, ALCOVE_FLOOR_Z, z_alc_top)
    back_wall = _box(rim_x, x_new_max, ALCOVE_Y_MAX, y_new_max, ALCOVE_FLOOR_Z, z_max)
    room_wall = _box(ALCOVE_X_MAX, x_new_max, y_min, y_new_max, ALCOVE_FLOOR_Z, z_max)
    shell = shell.union(floor).union(back_wall).union(room_wall)

    # 2. fin slot, open through the rim; gasket groove around its top edge
    slot = _box(rim_x - far, FIN_X_HALF + FIN_SLOT_CLEAR,
                -FIN_T - FIN_SLOT_CLEAR, FIN_SLOT_CLEAR,
                ALCOVE_FLOOR_Z - 1.0, z_max + far)
    groove = _box(rim_x - far, FIN_X_HALF + FIN_SLOT_CLEAR + GASKET_WIDTH,
                  -FIN_T - FIN_SLOT_CLEAR - GASKET_WIDTH, FIN_SLOT_CLEAR + GASKET_WIDTH,
                  z_alc_top - GASKET_DEPTH, z_max + far)
    shell = shell.cut(slot).cut(groove)

    # 3. heat-set bosses (fuse first, then drill so the hole depth is exact)
    bosses = boss_layout()
    for x, y, zt, _ in bosses:
        post = (cq.Workplane("XY").workplane(offset=zt - BOSS_SINK).center(x, y)
                .circle(BOSS_D / 2.0).extrude(BOSS_H + BOSS_SINK))
        shell = shell.union(post)
    for x, y, zt, _ in bosses:
        hole = (cq.Workplane("XY").workplane(offset=zt + BOSS_H - BOSS_HOLE_DEPTH).center(x, y)
                .circle(BOSS_HOLE_D / 2.0).extrude(BOSS_HOLE_DEPTH + 1.0))
        shell = shell.cut(hole)

    # 4. vents
    cutters = []
    z_mid_bottom = (BOTTOM_OUTER_Z + BOTTOM_INNER_Z) / 2.0
    for x, y in inlet_layout():
        cutters.append(_slot_cutter("y", "z", INLET_L, (x, y, z_mid_bottom)))
    y_mid_neg = (y_min + INNER_Y_MIN) / 2.0
    y_mid_pos = (SHELL_Y_MAX_OUTER + INNER_Y_MAX) / 2.0
    for x, z in side_outlet_layout():
        for y_mid in (y_mid_neg, y_mid_pos):
            cutters.append(_slot_cutter("x", "y", OUTLET_SIDE_L, (x, y_mid, z)))
    x_mid_front = (INNER_X_MAX + SHELL_X_MAX) / 2.0
    for y, z in front_outlet_layout():
        cutters.append(_slot_cutter("y", "x", OUTLET_L, (x_mid_front, y, z)))

    # 4b. motor back-end relief pocket in the -y side wall (inside face only)
    cutters.append(_box(RIM_X - 1.0, MOTOR_HALF + MOTOR_RELIEF_MARGIN,
                        INNER_Y_MIN - MOTOR_RELIEF_DEPTH, INNER_Y_MIN + 0.5,
                        -MOTOR_HALF - MOTOR_RELIEF_MARGIN, MOTOR_HALF + MOTOR_RELIEF_MARGIN))

    # 5. USB-C service port in the front wall (cutter along x)
    usb = (cq.Workplane("YZ").workplane(offset=INNER_X_MAX - 2.0).center(USB_PORT_Y, USB_PORT_Z)
           .rect(USB_PORT_W, USB_PORT_H).extrude(SHELL_X_MAX - INNER_X_MAX + 4.0)
           .edges("|X").fillet(USB_PORT_R))
    cutters.append(usb)

    shell = shell.cut(_union_all(cutters))
    return shell.clean()



def make() -> cq.Workplane:
    """Winch-station cover v4 (single solid, station frame)."""
    return build_cover()


# =========================================================================== neighbours (checks / renders)
def neighbours() -> dict:
    """Reference parts in the same frame.  The motor is shifted by -FIN_T in y: with the
    fin installed it is sandwiched between motor flange and PETG tab, so the fin
    occupies y in [-FIN_T, 0]."""
    load = lambda n: cq.importers.importStep(str(REF_DIR / f"{n}.step"))
    return {
        "motor": load("Motor_Reference").translate((0, -FIN_T, 0)),
        "motor_unshifted": load("Motor_Reference"),
        "spool": load("Spool1011"),
        "slipin": load("Slipin_mount_piecev3"),
        "wall_mount": load("Wall_Mount_v3"),
        "fin": fin_plate(),
    }


def fin_plate() -> cq.Workplane:
    return _box(-FIN_X_HALF, FIN_X_HALF, -FIN_T, 0.0, FIN_BOTTOM_Z, FIN_TOP_Z)


# =========================================================================== verification
def _vol(wp) -> float:
    return sum(s.Volume() for s in wp.solids().vals()) if wp.solids().size() else 0.0


def _common_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    return _vol(a.intersect(b))


def verify(cover: cq.Workplane, step_path: Path) -> dict:
    r = {}
    solids = cover.solids().vals()
    r["solid_count"] = len(solids)
    r["valid"] = bool(cover.val().isValid())
    r["bbox"] = tight_bbox(cover.val())
    r["volume_mm3"] = _vol(cover)
    r["mass_g"] = r["volume_mm3"] / 1000.0 * PETG_DENSITY_G_CM3

    nb = neighbours()
    r["interference_mm3"] = {k: _common_volume(cover, v) for k, v in nb.items()}

    # fin clearance: alcove walls (everything of the cover above the floor) and slot
    above_floor = cover.intersect(_box(-100, 200, -100, 200, ALCOVE_FLOOR_Z + WALL, 100))
    r["fin_to_alcove_walls_mm"] = nb["fin"].val().distance(above_floor.val())
    floor_only = cover.intersect(_box(-100, 200, -100, 200, ALCOVE_FLOOR_Z, ALCOVE_FLOOR_Z + WALL))
    r["fin_to_floor_slot_mm"] = nb["fin"].val().distance(floor_only.val())
    r["fin_gap_requirement_mm"] = FIN_AIR_GAP - 0.5

    # slide-on check: shell pushed back +x by d (as during assembly) must never touch the fin
    r["slide_on_fin_interference_mm3"] = {
        d: _common_volume(cover.translate((d, 0, 0)), nb["fin"]) for d in (0, 10, 30, 60, 120)}
    # unchanged-vs-input checks
    orig = load_shell()
    r["rim_xmin_new"] = tight_bbox(cover.val())[0]
    r["rim_xmin_orig"] = tight_bbox(orig.val())[0]
    y_excl = ALCOVE_Y_MAX + WALL
    z_excl = ALCOVE_FLOOR_Z
    rim0 = r["rim_xmin_orig"]
    slab = _box(rim0 - 1, rim0 + 1.0, -100, 200, -100, 200)
    excl = _box(rim0 - 2, rim0 + 2.0, -100, y_excl, z_excl, 200)
    # the motor relief pocket deliberately runs out through the rim (motor corner at the rim)
    excl_relief = _box(rim0 - 2, rim0 + 2.0, -100, INNER_Y_MIN + 0.5,
                       -MOTOR_HALF - MOTOR_RELIEF_MARGIN, MOTOR_HALF + MOTOR_RELIEF_MARGIN)
    probe = slab.cut(excl).cut(excl_relief)
    r["rim_slab_vol_orig"] = _common_volume(orig, probe)
    r["rim_slab_vol_new"] = _common_volume(cover, probe)
    holes = []
    for hy in CORNER_HOLE_Y:
        for hz in CORNER_HOLE_Z:
            pb = _box(rim0 - 1, rim0 + CORNER_HOLE_DEPTH + 2.0, hy - 4.0, hy + 4.0, hz - 4.0, hz + 4.0)
            holes.append(((hy, hz), _common_volume(orig, pb), _common_volume(cover, pb)))
    r["corner_holes"] = holes
    # alcove-region material check: what was removed from the original shell
    r["removed_from_orig_mm3"] = _vol(orig.cut(cover))
    r["added_to_orig_mm3"] = _vol(cover.cut(orig))

    # minimum boss <-> wire-hole gap (plan view)
    hole = (SHELF_HOLE_X[0], SHELF_HOLE_X[1], SHELF_HOLE_Y[0], SHELF_HOLE_Y[1])
    r["boss_to_wirehole_gap_mm"] = min(
        _rect_circle_gap(*hole, bx, by, BOSS_D / 2.0) for bx, by, _, _ in boss_layout())

    # STEP round trip
    back = cq.importers.importStep(str(step_path))
    r["step_volume_mm3"] = _vol(back)
    r["step_vol_err_pct"] = 100.0 * abs(r["step_volume_mm3"] - r["volume_mm3"]) / r["volume_mm3"]
    r["step_bbox"] = tight_bbox(back.val())
    r["step_solid_count"] = len(back.solids().vals())

    r["inlet_slots"] = len(inlet_layout())
    r["inlet_area_mm2"] = len(inlet_layout()) * (INLET_L * SLOT_W - SLOT_W ** 2 * (1 - math.pi / 4))
    n_side = 2 * len(side_outlet_layout())
    n_front = len(front_outlet_layout())
    r["outlet_slots"] = (n_side, n_front)
    r["outlet_area_mm2"] = (n_side * (OUTLET_SIDE_L * SLOT_W - SLOT_W ** 2 * (1 - math.pi / 4))
                            + n_front * (OUTLET_L * SLOT_W - SLOT_W ** 2 * (1 - math.pi / 4)))
    return r


def _fmt_bbox(b):
    return (f"x[{b[0]:.2f}, {b[1]:.2f}] y[{b[2]:.2f}, {b[3]:.2f}] z[{b[4]:.2f}, {b[5]:.2f}]"
            f"  = {b[1]-b[0]:.2f} x {b[3]-b[2]:.2f} x {b[5]-b[4]:.2f}")


def write_notes(r: dict, render_files) -> str:
    inter = r["interference_mm3"]
    rim_ok = abs(r["rim_slab_vol_orig"] - r["rim_slab_vol_new"]) < 0.01 and \
        abs(r["rim_xmin_new"] - r["rim_xmin_orig"]) < 1e-4
    holes_ok = all(abs(o - n) < 0.01 for _, o, n in r["corner_holes"])
    lines = [
        "# station_cover_v4 - implementer notes (self-check, not an independent verification)",
        "",
        "Generated by `/usr/bin/python3 -m cad.parts.station_cover_v4`. Station frame, mm.",
        "",
        "## Parameters used",
        f"FIN_T={FIN_T}, FIN_W={FIN_W}, FIN_BOTTOM_Z={FIN_BOTTOM_Z}, FIN_H={FIN_H}, "
        f"FIN_SLOT_CLEAR={FIN_SLOT_CLEAR}, FIN_AIR_GAP={FIN_AIR_GAP}, WALL={WALL}, "
        f"ALCOVE_FLOOR_Z={ALCOVE_FLOOR_Z}, ALCOVE_X_MAX={ALCOVE_X_MAX}, ALCOVE_Y_MAX={ALCOVE_Y_MAX}, "
        f"USB_PORT_Y={USB_PORT_Y}, USB_PORT_Z={USB_PORT_Z}.",
        "",
        "## Self-check results",
        f"- Solid count: {r['solid_count']} (valid BREP: {r['valid']})",
        f"- Bounding box: {_fmt_bbox(r['bbox'])}",
        f"- Volume {r['volume_mm3']:.0f} mm3 -> PETG mass {r['mass_g']:.1f} g (rho {PETG_DENSITY_G_CM3} g/cm3, solid, 100 % infill)",
        f"- Material removed from input shell: {r['removed_from_orig_mm3']:.0f} mm3; added: {r['added_to_orig_mm3']:.0f} mm3",
        "- Interference volume (BRep common) with cover, mm3:",
    ]
    for k, v in inter.items():
        lines.append(f"  - {k}: {v:.4f}")
    lines += [
        "- Slide-on along -x over the installed fin (cover offset +d in x, fin interference mm3): "
        + ", ".join(f"d={d}: {v:.4f}" for d, v in r["slide_on_fin_interference_mm3"].items()),
        f"- Min fin -> alcove walls clearance: {r['fin_to_alcove_walls_mm']:.2f} mm "
        f"(requirement >= {r['fin_gap_requirement_mm']:.1f}); fin -> floor slot: {r['fin_to_floor_slot_mm']:.2f} mm (design {FIN_SLOT_CLEAR})",
        f"- Rim plane x = {r["rim_xmin_new"]:.4f} (input {r["rim_xmin_orig"]:.4f}); rim-slab volume outside alcove footprint and motor relief "
        f"input {r['rim_slab_vol_orig']:.3f} vs new {r['rim_slab_vol_new']:.3f} mm3 -> {'PASS' if rim_ok else 'FAIL'}",
        "- Four corner M3 pockets (probe volume input vs new, mm3): "
        + "; ".join(f"(y{hy:.2f},z{hz:.2f}) {o:.2f}/{n:.2f}" for (hy, hz), o, n in r["corner_holes"])
        + f" -> {'PASS' if holes_ok else 'FAIL'}",
        f"- Min plan-view gap boss edge -> shelf wire hole: {r['boss_to_wirehole_gap_mm']:.2f} mm (no boss moved)",
        f"- Vents: {r['inlet_slots']} inlet slots (~{r['inlet_area_mm2']:.0f} mm2), "
        f"{r['outlet_slots'][0]} side + {r['outlet_slots'][1]} front outlet slots (~{r['outlet_area_mm2']:.0f} mm2); slot {SLOT_W} wide",
        f"- STEP round trip: solids {r['step_solid_count']}, volume {r['step_volume_mm3']:.0f} mm3 "
        f"(error {r['step_vol_err_pct']:.4f} %, limit 0.1 %), bbox {_fmt_bbox(r['step_bbox'])}",
        "",
        "## Notes / deviations",
        "- The input shell has ONE rounded-square wire hole per shelf (x 59.85..69.85, y 10.56..20.56, R4 corners), "
        "i.e. the merged 'four D8 holes'; checks use that real outline.",
        f"- The -y/top corner M3 pocket (y {CORNER_HOLE_Y[0]}, z {CORNER_HOLE_Z[0]}) lies inside the alcove cut, so the original "
        f"shell material is kept in x [{RIM_X}, {CORNER_POST_X_MAX:.2f}], y [{SHELL_Y_MIN}, {CORNER_POST_Y_MAX:.2f}], "
        f"z above the floor (a 23 mm wide corner post joined to the floor). This narrows the alcove's -y inlet to x > {CORNER_POST_X_MAX:.2f}.",
        "- Motor is placed at y - FIN_T for the interference check (fin sandwiched at y [-FIN_T, 0]); "
        "'motor_unshifted' is the reference position for information.",
        "- Renders: " + ", ".join(render_files),
        "- Export location follows cad/exports/<part>/ (cad/export_all.py writes cad/step|stl, but those hold only the claw parts).",
    ]
    text = "\n".join(lines) + "\n"
    NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTES_PATH.write_text(text)
    return text


# =========================================================================== rendering (numpy z-buffer)
def _render_scene(items, look, up, frame_bb, out_path, title, width=1100, height=800, ss=2,
                  section=None):
    """Orthographic software render.  items = [(Workplane, (r,g,b), alpha)].
    section = (axis_index, plane_value) marks cap faces on that plane."""
    import numpy as np
    from PIL import Image, ImageDraw

    look = np.asarray(look, float); look /= np.linalg.norm(look)
    up = np.asarray(up, float)
    right = np.cross(look, up); right /= np.linalg.norm(right)
    upv = np.cross(right, look)
    c = np.array([(frame_bb[0] + frame_bb[1]) / 2, (frame_bb[2] + frame_bb[3]) / 2,
                  (frame_bb[4] + frame_bb[5]) / 2])
    corners = np.array([[x, y, z] for x in frame_bb[0:2] for y in frame_bb[2:4] for z in frame_bb[4:6]])
    u_c, v_c = (corners - c) @ right, (corners - c) @ upv
    W, H = width * ss, height * ss
    scale = min(W * 0.90 / (np.ptp(u_c) or 1), H * 0.86 / (np.ptp(v_c) or 1))
    u_mid, v_mid = (u_c.max() + u_c.min()) / 2, (v_c.max() + v_c.min()) / 2

    depth = np.full((H, W), np.inf, np.float32)
    rgb = np.ones((H, W, 3), np.float32) * np.array([0.965, 0.965, 0.955], np.float32)
    nbuf = np.zeros((H, W, 3), np.float32)
    keyl = -look * 0.55 + upv * 0.55 - right * 0.45
    keyl /= np.linalg.norm(keyl)

    def tess(wp):
        v, f = wp.val().tessellate(0.08, 0.12)
        vv = np.array([p.toTuple() for p in v], float)
        return vv, np.array(f, int)

    for wp, col, alpha in sorted(items, key=lambda t: t[2] < 1.0):   # opaque first
        vv, ff = tess(wp)
        tri = vv[ff]
        nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1)[:, None], 1e-12)
        facing = nrm @ look
        if alpha < 1.0:
            keep = facing < 0
            tri, nrm, facing = tri[keep], nrm[keep], facing[keep]
        cap = np.zeros(len(tri), bool)
        if section is not None:
            ax_i, val = section
            cap = np.all(np.abs(tri[:, :, ax_i] - val) < 1e-3, axis=1)
        sx = (((tri - c) @ right) - u_mid) * scale + W / 2
        sy = H / 2 - (((tri - c) @ upv) - v_mid) * scale
        dz = (tri - c) @ look
        shade = 0.38 + 0.42 * np.abs(facing) + 0.30 * np.clip(nrm @ keyl, 0, 1)
        base = np.array(col, np.float32)
        cap_col = np.array([0.88, 0.50, 0.16], np.float32)
        for i in range(len(tri)):
            xs, ys, zs = sx[i], sy[i], dz[i]
            x0 = max(int(np.floor(xs.min())), 0); x1 = min(int(np.ceil(xs.max())), W - 1)
            y0 = max(int(np.floor(ys.min())), 0); y1 = min(int(np.ceil(ys.max())), H - 1)
            if x1 < x0 or y1 < y0:
                continue
            den = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(den) < 1e-9:
                continue
            px, py = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            w0 = ((ys[1] - ys[2]) * (px - xs[2]) + (xs[2] - xs[1]) * (py - ys[2])) / den
            w1 = ((ys[2] - ys[0]) * (px - xs[2]) + (xs[0] - xs[2]) * (py - ys[2])) / den
            w2 = 1.0 - w0 - w1
            m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            if not m.any():
                continue
            d = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
            sub = depth[y0:y1 + 1, x0:x1 + 1]
            vis = m & (d < sub)
            if not vis.any():
                continue
            colr = (cap_col if cap[i] else base) * shade[i]
            if alpha >= 1.0:
                sub[vis] = d[vis]
                rgb[y0:y1 + 1, x0:x1 + 1][vis] = colr
                nbuf[y0:y1 + 1, x0:x1 + 1][vis] = nrm[i]
            else:
                blk = rgb[y0:y1 + 1, x0:x1 + 1]
                blk[vis] = blk[vis] * (1 - alpha) + colr * alpha

    # line work: silhouettes and creases from the depth / normal buffers
    fin = np.isfinite(depth)
    if fin.any():                                     # depth cue: far surfaces slightly darker
        d_lo, d_hi = depth[fin].min(), depth[fin].max()
        rgb[fin] *= (1.0 - 0.32 * (depth[fin] - d_lo) / max(d_hi - d_lo, 1e-6))[:, None]
    dd = np.where(fin, depth, 1e6)
    edge = np.zeros((H, W), bool)
    for sh in ((0, 1), (1, 0)):
        d2 = np.roll(dd, sh, axis=(0, 1))
        n2 = np.roll(nbuf, sh, axis=(0, 1))
        edge |= (np.abs(dd - d2) > 1.2) | ((nbuf * n2).sum(2) < 0.80) & fin
    rgb[edge] *= 0.35

    img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).resize((width, height), Image.LANCZOS)
    dr = ImageDraw.Draw(img)
    dr.text((14, 10), title, fill=(30, 30, 30))
    dr.text((14, height - 22), f"station frame mm | view dir ({look[0]:+.2f},{look[1]:+.2f},{look[2]:+.2f})",
            fill=(90, 90, 90))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path.name


def render_all(cover: cq.Workplane) -> list:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    nb = neighbours()
    C_COVER, C_MOTOR, C_SPOOL = (0.36, 0.60, 0.74), (0.35, 0.35, 0.38), (0.90, 0.75, 0.25)
    C_SLIP, C_FIN = (0.55, 0.72, 0.50), (0.30, 0.55, 0.95)
    cover_bb = tight_bbox(cover.val())
    names = []

    views = {
        "front": ((-1, 0, 0), (0, 0, 1)),        # camera on +x (room side)
        "rear": ((1, 0, 0), (0, 0, 1)),          # camera on -x (rim side)
        "left": ((0, 1, 0), (0, 0, 1)),          # camera on -y (open alcove side)
        "right": ((0, -1, 0), (0, 0, 1)),        # camera on +y
        "top": ((0, 0, -1), (1, 0, 0)),
        "bottom": ((0, 0, 1), (1, 0, 0)),
        "iso": ((-1, 1, -0.8), (0, 0, 1)),
    }
    for name, (look, up) in views.items():
        names.append(_render_scene([(cover, C_COVER, 1.0)], look, up, cover_bb,
                                   RENDER_DIR / f"station_cover_v4_{name}.png",
                                   f"station_cover_v4 - {name}"))

    full = [(cover, C_COVER, 1.0), (nb["motor"], C_MOTOR, 1.0), (nb["spool"], C_SPOOL, 1.0),
            (nb["slipin"], C_SLIP, 1.0), (nb["fin"], C_FIN, 0.35)]
    asm_bb = (RIM_X - 40, SHELL_X_MAX, -75, 105, -75, 120)
    names.append(_render_scene(full, (-1, 1, -0.8), (0, 0, 1), asm_bb,
                               RENDER_DIR / "station_cover_v4_assembly_iso.png",
                               "cover + motor + spool + slip-in + translucent fin (iso)"))
    full_bb = (RIM_X - 40, SHELL_X_MAX, -75, 105, -75, FIN_TOP_Z)
    names.append(_render_scene(full, (-1, 1, -0.8), (0, 0, 1), full_bb,
                               RENDER_DIR / "station_cover_v4_assembly_iso_fullfin.png",
                               "same, full-height fin (iso)", width=800, height=1100))

    def clipped(items, axis, val, keep_greater):
        lo, hi = (val, 500) if keep_greater else (-500, val)
        rng = {0: (lo, hi, -500, 500, -500, 500), 1: (-500, 500, lo, hi, -500, 500),
               2: (-500, 500, -500, 500, lo, hi)}[axis]
        half = _box(*rng)
        return [(wp.intersect(half), col, a) for wp, col, a in items]

    # section through the fin mid-plane: keep y >= -FIN_T/2, camera on -y
    y_fin = -FIN_T / 2.0
    names.append(_render_scene(clipped(full, 1, y_fin, True), (0, 1, 0), (0, 0, 1),
                               (RIM_X - 40, SHELL_X_MAX, -75, 105, -75, 120),
                               RENDER_DIR / "station_cover_v4_section_y_fin_plane.png",
                               f"section y = {y_fin:.2f} (fin mid-plane), looking +y",
                               section=(1, y_fin)))
    # section x = 0 through the fin / alcove / slot: keep x >= 0, camera on -x
    names.append(_render_scene(clipped(full, 0, 0.0, True), (1, 0, 0), (0, 0, 1),
                               (0, SHELL_X_MAX, -52, 80, -75, 120),
                               RENDER_DIR / "station_cover_v4_section_x0_fin_alcove.png",
                               "section x = 0 (fin, slot, alcove walls), looking +x",
                               section=(0, 0.0)))
    # section z = 40: bosses' level / bay, from above
    names.append(_render_scene(clipped([(cover, C_COVER, 1.0), (nb["fin"], C_FIN, 0.35)], 2, 30.0, False),
                               (0, 0, -1), (1, 0, 0), cover_bb,
                               RENDER_DIR / "station_cover_v4_section_z30_bay.png",
                               "section z = 30 (upper-shelf bosses, alcove), looking down",
                               section=(2, 30.0)))
    return names


# =========================================================================== main
def main() -> None:
    cover = make()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    step_path = EXPORT_DIR / "station_cover_v4.step"
    stl_path = EXPORT_DIR / "station_cover_v4.stl"
    cq.exporters.export(cover, str(step_path))
    cq.exporters.export(cover, str(stl_path), tolerance=0.05, angularTolerance=0.2)
    report = verify(cover, step_path)
    renders = render_all(cover)
    print(write_notes(report, renders))


if __name__ == "__main__":
    main()
