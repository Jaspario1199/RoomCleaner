"""
WINCH GEAR 3 -- 3:1 spur reduction of the winch station: drive-train reference that Jasper designs his mount around.

Spec: cad/WINCH_GEAR3_SPEC.md (D40, revision B / D41: 18T/54T, revision C / D42: printed PETG pinion).  Parameters: cad/params.py block WG3_* (plus NEMA17T_*, FIN1021_*, GRIPV7 bearing sizes, ENC1021 values it reuses).
Build notes / measured results / interferences with the current slide-in: verification/winch_gear3_build_notes.md.  Tests: tests/test_winch_gear3.py.

Drive train (station_1021 frame: motor axis x = 0, z = +2.64; +y along the motor shaft toward the spool; +x out of the wall; +z up):

    motor (NEMA 17, front face y -3.175 behind the 1/8 in fin)  ->  printed PETG M1 18T pinion (`pinion18`) on the Ø5 shaft (printed D-bore Ø5.30 / flat 2.15, M3 set screw in a heat-set insert)
        teeth y 10.825 .. 20.825 (0.10 thinning, 0.3 x 45 deg chamfer on the y 20.825 tooth edges), hub Ø14 y -0.675 .. 10.825 (through the fin's and the tab's motor holes,
        0.5 mm clear of the motor's pilot boss face at y -1.175), radial insert pocket Ø4.0 x 4.5 + Ø3.0 hole toward +z at y 7.9125
    printed 54T gear (part of `spool_gear54`) on its own Ø7 shaft, axis x 0, z -33.66 (centre distance 36.30 = 36.00 + 0.30 backlash allowance, printed against printed)
        spool_gear54  y 10.825 .. 44.0: gear 10.825 .. 20.825 (six Ø10 windows on R17.5, 0.3 x 45 deg chamfer on the bed-face teeth), drum Ø15 to 36.825,
                      Ø36 x 3 outer flange, Ø12 far hub with a Ø9 land 0.3 proud, Ø7.00 bore, Ø1.4 chord tie-off hole at y 28.825
        spacer_near_w3 Ø10 / Ø7.10, y 5.0 .. 10.825, Ø9 lands (0.3 proud) on both ends
        shaft Ø7 x 55 (y -3 .. 52), 687 bearings y 0 .. 5 and 44 .. 49, magnet_cap_w3 y 49.3 .. 55.55 (Ø7 bore 3.0 deep, 0.75 web, Ø6.3 x 2.5 pocket with 3 crush
        ribs), Ø6 x 2.5 magnet, AS5600: chip face y 57.05, chip 1.45 tall, PCB 23 x 23 x 1.6 at y 58.5 .. 60.1

Frames.  Parts are built in an AXIAL frame: axis = local z = station y, local x = station x, local y = -station z.  The print frame is that frame with the axis up
and the bed face at z = 0: spool_gear54 prints with its near gear face (y 10.825) on the bed, magnet_cap_w3 on its bearing-side face (magnet face up), spacer_near_w3 on
either end face, and pinion18 teeth end down (y 20.825 on the bed, hub up): the axial frame turned 180 deg about x, then shifted so the bed face is z = 0.
Part STEP / STL files are in the print frame (z = 0 on the bed face).  The assemblies are in assembly coordinates (asm1021 = station_1021 + O, the repo's
convention: they drop into Assem_laundry_v3_step_1021 at the origin) and carry the extraction residual ENC1021_REF_RESIDUAL (0.004 mm), so the drive bodies
coincide with Jasper's STEP files and with exports/step/heat_fin1021_1p8_asm1021.step.  In-memory builders (`build_drive`) use the station_1021 frame.

    xvfb-run -a -s "-screen 0 1600x1200x24" /usr/bin/python3 -m cad.parts.winch_gear3     (exports, tables, interferences, renders)
    /usr/bin/python3 -m cad.parts.winch_gear3 --no-render
"""

from __future__ import annotations

import functools
import itertools
import math
import os
import sys

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane

from .. import params as P
from ..gripper_v3_fit_review_20261018.gears import gear as _involute_gear
from ..reference.station_1021.extract import O as ASM_ORIGIN
from . import nema17_thermal as N

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STEP_DIR = os.path.join(_REPO, "exports", "step")
STL_DIR = os.path.join(_REPO, "exports", "stl")
RENDER_DIR = os.path.join(_REPO, "renders", "winch_gear3")
REF_DIR = os.path.join(_REPO, "cad", "reference", "station_1021")
FIN_STEP = os.path.join(STEP_DIR, "heat_fin1021_1p8_asm1021.step")
NAME = "winch_gear3"

SPOOL = f"spool_gear{P.WG3_Z_GEAR}"                  # printable gear body, part file stem and drive-body name: follow the tooth count (revision B: spool_gear54)
PINION = "pinion"                                    # printable pinion body name (print part, drive body, STEP body name)
PINION_FILE = f"pinion{P.WG3_Z_PINION}"              # its export file stem (revision B/C: pinion18)
SPACER, CAP = "spacer_near_w3", "magnet_cap_w3"
BODY_ORDER = tuple(f"motor_{b}" for b in P.NEMA17T_BODIES) + ("fin", "pinion", SPOOL, "shaft", "bearing_near", "bearing_far", "spacer_near",
                                                                "magnet_cap", "magnet", "as5600_chip", "as5600_board")
COLORS = {"motor_front_cap": (0.72, 0.74, 0.78), "motor_stator": (0.18, 0.18, 0.20), "motor_winding": (0.80, 0.45, 0.18), "motor_rear_cap": (0.72, 0.74, 0.78),
          "motor_shaft": (0.45, 0.45, 0.50), "motor_connector": (0.15, 0.30, 0.65), "fin": (0.80, 0.82, 0.88), "pinion": (0.55, 0.45, 0.80),
          SPOOL: (0.93, 0.62, 0.25), "shaft": (0.38, 0.40, 0.45), "bearing_near": (0.62, 0.64, 0.68), "bearing_far": (0.62, 0.64, 0.68),
          "spacer_near": (0.35, 0.65, 0.85), "magnet_cap": (0.35, 0.75, 0.50), "magnet": (0.75, 0.15, 0.15), "as5600_chip": (0.10, 0.10, 0.12),
          "as5600_board": (0.10, 0.45, 0.25), "slipin_mount": (0.85, 0.75, 0.55), "wall_mount": (0.70, 0.62, 0.50)}

CONSTRUCTION_OVERSHOOT = 1.0     # mm, cutters run this far past the faces they cut through (not a design value)
RIB_INSET = 0.1                  # mm, crush-rib base sunk into the pocket wall so the union fuses (as cad/parts/encoder1021.py)
RIB_FUSE = 0.3                   # mm, crush-rib foot sunk into the web below the pocket floor
CHORD_HALF_LEN = 12.0            # mm, half length of the tie-off cutter (well past the Ø15 core)


# =============================================================================================================================
# frames and small helpers
# =============================================================================================================================
def residual() -> tuple:
    """Extraction residual (x, y, z) of the station_1021 files, mm."""
    return tuple(P.ENC1021_REF_RESIDUAL)


def axial_to_station(shape: cq.Shape, axis_xz: tuple) -> cq.Shape:
    """Axial frame (axis = z = station y, x = station x, y = -station z; axis through the origin) -> station_1021 frame with the axis at station (x, z) = axis_xz
    and the residual added.  Rotation about +x by -90 deg: (X, Y, Z) -> (X, Z, -Y)."""
    dx, dy, dz = residual()
    return shape.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), -90.0).translate(cq.Vector(axis_xz[0] + dx, dy, axis_xz[1] + dz))


def _cyl(r: float, z0: float, z1: float, x: float = 0.0, y: float = 0.0) -> cq.Solid:
    return cq.Solid.makeCylinder(r, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1))


def _ring(r_out: float, r_in: float, z0: float, z1: float) -> cq.Solid:
    return _one(_cyl(r_out, z0, z1).cut(_cyl(r_in, z0 - CONSTRUCTION_OVERSHOOT, z1 + CONSTRUCTION_OVERSHOOT)), "ring")


def _one(shape: cq.Shape, what: str) -> cq.Solid:
    solids = shape.Solids()
    assert len(solids) == 1 and solids[0].isValid() and solids[0].Volume() > 0, f"{what}: expected one valid solid, got {len(solids)}"
    return solids[0]


def _wp(shape: cq.Shape) -> cq.Workplane:
    return cq.Workplane("XY").newObject([shape])


def pitch_r(n: int) -> float:
    return P.WG3_MODULE * n / 2.0


def tip_r(n: int) -> float:
    return P.WG3_MODULE * (n + 2) / 2.0


def root_r(n: int) -> float:
    return P.WG3_MODULE * (n - 2.5) / 2.0


def direction_gear_to_pinion_deg() -> float:
    """Angle (axial frame, from +x toward +y) of the line from the spool axis to the motor axis: the pinion is straight above the spool = station +z = axial -y."""
    return math.degrees(math.atan2(-(P.WG3_MOTOR_XZ[1] - P.WG3_SPOOL_XZ[1]), P.WG3_MOTOR_XZ[0] - P.WG3_SPOOL_XZ[0]))


def gear_phase_deg() -> float:
    """Phase of the gear: a tooth SPACE is centred on the line of centres toward the pinion (tooth k is centred at phase + 360 k / n)."""
    return direction_gear_to_pinion_deg() - 180.0 / P.WG3_Z_GEAR


def pinion_phase_deg() -> float:
    """Phase of the pinion: a tooth is centred on the line of centres toward the gear (which has a space there)."""
    return direction_gear_to_pinion_deg() + 180.0


def _toothed(n: int, phase_deg: float, thin: float) -> cq.Solid:
    """Involute spur gear of the repo generator, axis z through the origin, z 0 .. WG3_FACE."""
    return _one(_involute_gear(n, P.WG3_MODULE, P.WG3_FACE, phase=phase_deg, reduction=thin, root_radius=P.WG3_ROOT_FILLET_R).val(), f"gear {n}T")


# =============================================================================================================================
# the printable parts (axial frame, design values, no residual)
# =============================================================================================================================
def _tooth_end_edges(g: cq.Solid) -> list:
    """Edges of the toothed solid lying in its far face z = WG3_FACE (the outer tooth outline: that face has no other wire before the bore is cut)."""
    return [e for e in g.Edges() if e.BoundingBox().zmin > P.WG3_FACE - 1.0e-6]


def _d_bore_cutter(z0: float, z1: float) -> cq.Solid:
    """Printed D-bore cutter, axial frame, z0 .. z1: Ø WG3_PINION_BORE_D round bore cut off by the flat WG3_PINION_BORE_FLAT_X from the axis on the +z STATION side
    (= axial -y: material beyond the flat, on the -y side), the motor shaft's flat (2.0 from the axis) facing it."""
    r = P.WG3_PINION_BORE_D / 2.0
    keep_from = -P.WG3_PINION_BORE_FLAT_X                                                           # axial y of the flat
    keep = cq.Solid.makeBox(2.0 * (r + CONSTRUCTION_OVERSHOOT), (r + CONSTRUCTION_OVERSHOOT) - keep_from, z1 - z0, cq.Vector(-(r + CONSTRUCTION_OVERSHOOT), keep_from, z0))
    return _one(_cyl(r, z0, z1).intersect(keep), "D-bore cutter")


def make_pinion() -> cq.Solid:
    """Printed PETG M1 18T pinion (revision C / D42), axial frame, axis on the z axis (axial z = station y):
    teeth y 10.825 .. 20.825 with the gear's 0.10 thinning and a 0.3 x 45 deg chamfer on the tooth edges of the y 20.825 end face (the print bed face);
    hub Ø14 from y -0.675 (0.5 mm clear of the motor's pilot boss face) to the teeth; D-bore (Ø5.30, flat 2.15 from the axis on the +z station side) through;
    radial pocket Ø4.0 x 4.5 deep from the hub surface for the M3 heat-set insert, and a Ø3.0 hole from the pocket bottom to the bore, both toward +z station
    (= axial -y, the D-flat side) on the axis y 7.9125."""
    teeth = _toothed(P.WG3_Z_PINION, pinion_phase_deg(), P.WG3_PINION_TOOTH_THIN)
    teeth = teeth.chamfer(P.WG3_BED_CHAMFER, None, _tooth_end_edges(teeth)).translate(cq.Vector(0, 0, P.WG3_Y_TEETH0))      # relief on the tooth edges of the bed face
    hub = _cyl(P.WG3_PINION_HUB_D / 2.0, P.WG3_Y_PINION_HUB0, P.WG3_Y_TEETH0)
    body = teeth.fuse(hub).clean()
    body = body.cut(_d_bore_cutter(P.WG3_Y_PINION_HUB0 - CONSTRUCTION_OVERSHOOT, P.WG3_Y_TEETH1 + CONSTRUCTION_OVERSHOOT))
    r_hub = P.WG3_PINION_HUB_D / 2.0
    r_pocket_bottom = r_hub - P.WG3_PINION_INSERT_DEPTH
    toward_plus_z = cq.Vector(0, -1, 0)                                                              # axial -y = station +z
    pocket = cq.Solid.makeCylinder(P.WG3_PINION_INSERT_D / 2.0, P.WG3_PINION_INSERT_DEPTH + CONSTRUCTION_OVERSHOOT,
                                   cq.Vector(0, -r_pocket_bottom, P.WG3_Y_PINION_SETSCREW), toward_plus_z)
    hole = cq.Solid.makeCylinder(P.WG3_PINION_SETSCREW_D / 2.0, r_pocket_bottom + CONSTRUCTION_OVERSHOOT, cq.Vector(0, 0, P.WG3_Y_PINION_SETSCREW), toward_plus_z)
    return _one(body.cut(pocket).cut(hole), PINION)


def _bed_face_edges(g: cq.Solid) -> list:
    """Edges of the gear solid lying in its z = 0 face (the outer tooth outline: the face has no other wire before the bore and windows are cut)."""
    return [e for e in g.Edges() if e.BoundingBox().zmax < 1.0e-6]


def make_spool_gear() -> cq.Solid:
    """spool_gear54 (name from the tooth count), axial frame (axis = z = station y), y 10.825 .. 44.0, bed face (near gear face) at y 10.825."""
    g = _toothed(P.WG3_Z_GEAR, gear_phase_deg(), P.WG3_GEAR_TOOTH_THIN)
    g = g.chamfer(P.WG3_BED_CHAMFER, None, _bed_face_edges(g))                                       # elephant-foot relief on the tooth edges of the bed face
    g = g.translate(cq.Vector(0, 0, P.WG3_Y_TEETH0))
    y0, y1 = P.WG3_Y_TEETH0 - CONSTRUCTION_OVERSHOOT, P.WG3_Y_TEETH1 + CONSTRUCTION_OVERSHOOT
    for k in range(P.WG3_WINDOW_N):                                                                 # lightening windows
        a = math.radians(P.WG3_WINDOW_PHASE_DEG + 360.0 * k / P.WG3_WINDOW_N)
        g = g.cut(_cyl(P.WG3_WINDOW_D / 2.0, y0, y1, P.WG3_WINDOW_R * math.cos(a), P.WG3_WINDOW_R * math.sin(a)))
    land = P.WG3_LAND_PROUD
    body = (g.fuse(_cyl(P.WG3_DRUM_D / 2.0, P.WG3_Y_TEETH1, P.WG3_Y_DRUM1))                           # drum: the gear's side face is the inner flange
            .fuse(_cyl(P.WG3_FLANGE_D / 2.0, P.WG3_Y_DRUM1, P.WG3_Y_FLANGE1))                       # outer flange
            .fuse(_cyl(P.WG3_HUB_D / 2.0, P.WG3_Y_FLANGE1, P.WG3_Y_SPOOL_END - land))                # far hub
            .fuse(_cyl(P.WG3_LAND_D / 2.0, P.WG3_Y_SPOOL_END - land, P.WG3_Y_SPOOL_END)).clean())    # Ø9 land, 0.3 proud
    body = body.cut(_cyl(P.WG3_BORE_D / 2.0, P.WG3_Y_TEETH0 - CONSTRUCTION_OVERSHOOT, P.WG3_Y_SPOOL_END + CONSTRUCTION_OVERSHOOT))
    # tie-off: chord hole perpendicular to the axis (along axial y = station z), offset toward +x, at the drum mid-plane
    tie = cq.Solid.makeCylinder(P.WG3_TIEOFF_D / 2.0, 2 * CHORD_HALF_LEN, cq.Vector(P.WG3_TIEOFF_OFFSET, -CHORD_HALF_LEN, P.WG3_TIEOFF_Y), cq.Vector(0, 1, 0))
    return _one(body.cut(tie), SPOOL)


def make_spacer_near() -> cq.Solid:
    """spacer_near_w3, axial frame, y 5.0 .. 10.825: Ø10 body, Ø7.10 bore, Ø9 lands 0.3 proud on both end faces."""
    y0, y1, land = P.WG3_SPACER_Y0, P.WG3_SPACER_Y1, P.WG3_LAND_PROUD
    body = (_cyl(P.WG3_LAND_D / 2.0, y0, y0 + land).fuse(_cyl(P.WG3_SPACER_OD / 2.0, y0 + land, y1 - land))
            .fuse(_cyl(P.WG3_LAND_D / 2.0, y1 - land, y1)).clean())
    return _one(body.cut(_cyl(P.WG3_SPACER_BORE_D / 2.0, y0 - CONSTRUCTION_OVERSHOOT, y1 + CONSTRUCTION_OVERSHOOT)), SPACER)


def magnet_rib_geometry() -> dict:
    """Crush-rib numbers of the pocket (ENC1021_V2 rule): protrusion from the wall = 0.15 per side + 0.12 crush, tip radius = magnet radius - crush."""
    r_wall = P.WG3_CAP_POCKET_D / 2.0
    h = (P.WG3_CAP_POCKET_D - P.WG3_MAGNET_D) / 2.0 + P.ENC1021_V2_MAGNET_RIB_CRUSH
    return {"r_wall": r_wall, "h": h, "r_tip": r_wall - h, "n": P.ENC1021_V2_MAGNET_RIB_N, "tip_w": P.ENC1021_V2_MAGNET_RIB_TIP, "base_w": P.ENC1021_V2_MAGNET_RIB_BASE}


def _magnet_ribs() -> cq.Solid:
    """3 crush ribs in the magnet pocket with a 45 deg lead-in at the mouth (the cad/parts/encoder1021.py construction, here for the Ø6 magnet)."""
    g = magnet_rib_geometry()
    z0, z1 = P.WG3_Y_MAGNET0 - RIB_FUSE, P.WG3_CAP_Y1
    ribs = None
    for i in range(g["n"]):
        ang = P.WG3_MAGNET_RIB_PHASE_DEG + 360.0 * i / g["n"]
        rib = (cq.Workplane("XY").workplane(offset=z0)
               .polyline([(g["r_wall"] + RIB_INSET, -g["base_w"] / 2), (g["r_tip"], -g["tip_w"] / 2), (g["r_tip"], g["tip_w"] / 2), (g["r_wall"] + RIB_INSET, g["base_w"] / 2)])
               .close().extrude(z1 - z0).rotate((0, 0, 0), (0, 0, 1), ang))
        ribs = rib if ribs is None else ribs.union(rib)
    h = g["h"]
    cone = cq.Solid.makeCone(g["r_tip"], g["r_tip"] + h + CONSTRUCTION_OVERSHOOT, h + CONSTRUCTION_OVERSHOOT, cq.Vector(0, 0, z1 - h), cq.Vector(0, 0, 1))
    return ribs.cut(_wp(cone)).val()


def make_magnet_cap() -> cq.Solid:
    """magnet_cap_w3, axial frame, y 49.3 .. 55.55: Ø12; Ø7 bore y 49.3 .. 52.3; 0.75 web; Ø6.3 x 2.5 magnet pocket (y 53.05 .. 55.55) with 3 crush ribs."""
    cap = _cyl(P.WG3_CAP_D / 2.0, P.WG3_CAP_Y0, P.WG3_CAP_Y1)
    cap = cap.cut(_cyl(P.WG3_CAP_BORE_D / 2.0, P.WG3_CAP_Y0 - CONSTRUCTION_OVERSHOOT, P.WG3_CAP_Y0 + P.WG3_CAP_BORE_DEPTH))
    cap = cap.cut(_cyl(P.WG3_CAP_POCKET_D / 2.0, P.WG3_Y_MAGNET0, P.WG3_CAP_Y1 + CONSTRUCTION_OVERSHOOT))
    return _one(cap.fuse(_magnet_ribs()).clean(), CAP)


# =============================================================================================================================
# reference / purchased bodies (axial frame)
# =============================================================================================================================
def make_shaft() -> cq.Solid:
    return _cyl(P.WG3_SHAFT_D / 2.0, P.WG3_SHAFT_Y0, P.WG3_SHAFT_Y0 + P.WG3_SHAFT_L)


def make_bearing(y0: float) -> cq.Solid:
    return _ring(P.WG3_BRG_OD / 2.0, P.WG3_BRG_ID / 2.0, y0, y0 + P.WG3_BRG_W)


def make_magnet() -> cq.Solid:
    return _cyl(P.WG3_MAGNET_D / 2.0, P.WG3_Y_MAGNET0, P.WG3_CAP_Y1)


def make_chip() -> cq.Solid:
    """AS5600 chip envelope: footprint ENC1021_CHIP_BODY (x, station z) x ENC1021_CHIP_H, chip face at WG3_CHIP_FACE_Y, centred on the axis (ENC1021_CHIP_OFFSET)."""
    bx, bz = P.ENC1021_CHIP_BODY
    ox, oz = P.ENC1021_CHIP_OFFSET
    return cq.Solid.makeBox(bx, bz, P.ENC1021_CHIP_H, cq.Vector(ox - bx / 2.0, -oz - bz / 2.0, P.WG3_CHIP_FACE_Y))


def make_board() -> cq.Solid:
    s = P.ENC1021_PCB_SIZE
    return cq.Solid.makeBox(s, s, P.ENC1021_PCB_THICK, cq.Vector(-s / 2.0, -s / 2.0, P.WG3_PCB_Y0))


# =============================================================================================================================
# the drive assembly, station_1021 frame (residual included)
# =============================================================================================================================
@functools.lru_cache(maxsize=None)
def fin_station() -> cq.Solid:
    """The 1/8 in fin exactly as exported (assembly coordinates), moved to the station_1021 frame by -O."""
    fin = cq.importers.importStep(FIN_STEP).val()
    return _one(fin.translate(cq.Vector(*ASM_ORIGIN) * -1), "fin")


def motor_front_face_y() -> float:
    """y of the fin's motor-side face = the motor front face (station_1021 frame, residual included), measured on the fin."""
    return fin_station().BoundingBox().ymin


def motor_bodies() -> dict:
    """NEMA17T_* bodies (names motor_<body>) at the fin, axis (0, 2.64); the motor shaft gets the 0.5 mm D-flat on +z from the pilot boss end to the shaft end."""
    dx, _, dz = residual()
    bodies = N.make_bodies()
    r = P.NEMA17T_SHAFT_D / 2.0
    y0 = N.levels()["boss_end"]
    cutter = cq.Solid.makeBox(2 * r + 2.0, N.levels()["shaft_front"] - y0 + 1.0, 1.0 + P.WG3_SHAFT_FLAT_DEPTH, cq.Vector(-r - 1.0, y0, r - P.WG3_SHAFT_FLAT_DEPTH))
    bodies["shaft"] = _one(bodies["shaft"].cut(cutter), "motor shaft with D-flat")
    origin = (P.WG3_MOTOR_XZ[0] + dx, motor_front_face_y(), P.WG3_MOTOR_XZ[1] + dz)
    return {f"motor_{k}": N.to_station(v, 0.0, origin=origin) for k, v in bodies.items()}


def build_drive() -> dict:
    """name -> cq.Solid for every drive body, station_1021 frame (residual included), in BODY_ORDER."""
    motor_xz, spool_xz = P.WG3_MOTOR_XZ, P.WG3_SPOOL_XZ
    b = motor_bodies()
    b["fin"] = fin_station()
    b["pinion"] = axial_to_station(make_pinion(), motor_xz)
    parts = {SPOOL: make_spool_gear(), "shaft": make_shaft(), "bearing_near": make_bearing(P.WG3_BRG_NEAR_Y0), "bearing_far": make_bearing(P.WG3_BRG_FAR_Y0),
             "spacer_near": make_spacer_near(), "magnet_cap": make_magnet_cap(), "magnet": make_magnet(), "as5600_chip": make_chip(), "as5600_board": make_board()}
    for k, v in parts.items():
        b[k] = axial_to_station(v, spool_xz)
    assert tuple(b) == BODY_ORDER, tuple(b)
    return {k: _one(b[k], k) for k in BODY_ORDER}


@functools.lru_cache(maxsize=None)
def reference(name: str) -> cq.Shape:
    """Jasper's reference STEP (station_1021 frame, residual included), read only."""
    return cq.importers.importStep(os.path.join(REF_DIR, f"{name}.step")).val()


def to_assembly(bodies: dict) -> dict:
    return {k: v.translate(cq.Vector(*ASM_ORIGIN)) for k, v in bodies.items()}


# =============================================================================================================================
# print poses
# =============================================================================================================================
PART_FILE = {PINION: PINION_FILE, SPOOL: SPOOL, SPACER: "spacer_near", CAP: "magnet_cap"}     # printable part -> export file stem
PART_COLOR = {PINION: "pinion", SPOOL: SPOOL, SPACER: "spacer_near", CAP: "magnet_cap"}      # printable part -> COLORS key
PRINT_BED_Y = {PINION: P.WG3_Y_TEETH1, SPOOL: P.WG3_Y_TEETH0, SPACER: P.WG3_SPACER_Y0, CAP: P.WG3_CAP_Y0}      # design y of the bed face
PRINT_FLIPPED = {PINION}                                                    # the bed face is the part's HIGHEST-y face: turned 180 deg about x (hub up)
PRINT_NOTE = {PINION: "teeth end (y 20.825, 0.3 x 45 deg chamfered tooth edges) on the bed, axis up, hub up; the Ø14 hub, the D-bore and the radial Ø4.0 insert pocket + Ø3.0 hole "
                      "(horizontal, opening to +y of the print frame) need no supports with bridging; heat-set an M3 x 4 insert in the pocket, M3 cup-point set screw onto the D-flat",
              SPOOL: "near gear face (y 10.825, chamfered tooth edges) on the bed, axis up; the far hub builds on top of the Ø36 flange; the flange's inner face "
                     "(y 36.825) overhangs the Ø15 drum by 10.5 mm: PRINTED ON SUPPORTS, sand that face smooth where the line touches it",
              SPACER: "either end face (both are Ø9 lands) on the bed, axis up; no supports",
              CAP: "bearing-side face (y 49.3, the Ø7 bore opening) on the bed, magnet pocket up: magnet-face up; no supports (the web closes the bore under the pocket)"}


def print_parts() -> dict:
    """name -> solid in the print frame (axial frame translated so the bed face is z = 0)."""
    made = {PINION: make_pinion(), SPOOL: make_spool_gear(), SPACER: make_spacer_near(), CAP: make_magnet_cap()}
    return {k: to_print_frame(k, v) for k, v in made.items()}


def to_print_frame(name: str, shape: cq.Shape) -> cq.Shape:
    """Axial frame -> print frame: bed face at z = 0, axis up.  Flipped parts (pinion: bed face = highest y) are turned 180 deg about the x axis first (z -> -z, y -> -y)."""
    if name in PRINT_FLIPPED:
        return shape.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 180.0).translate(cq.Vector(0, 0, PRINT_BED_Y[name]))
    return shape.translate(cq.Vector(0, 0, -PRINT_BED_Y[name]))


# =============================================================================================================================
# measuring helpers
# =============================================================================================================================
def cylinder_faces(shape: cq.Shape, radius: float, tol: float = 1.0e-4) -> list:
    """(axis location, axis direction) of every cylindrical face of the given radius."""
    out = []
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() != GeomAbs_Cylinder or abs(a.Cylinder().Radius() - radius) > tol:
            continue
        ax = a.Cylinder().Axis()
        out.append(((ax.Location().X(), ax.Location().Y(), ax.Location().Z()), (ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z())))
    return out


def bore_axis_xz(shape: cq.Shape, radius: float) -> tuple:
    """(x, z) of the axis of the cylindrical faces of this radius whose axis runs along y (station frame)."""
    faces = [f for f in cylinder_faces(shape, radius) if abs(abs(f[1][1]) - 1.0) < 1e-9]
    assert faces, f"no y-axis cylinder of radius {radius}"
    return faces[0][0][0], faces[0][0][2]


def overlap_volume(a: cq.Shape, b: cq.Shape) -> float:
    return a.intersect(b).Volume()


def _bbox_hit(a: cq.BoundBox, b: cq.BoundBox, tol: float = 1.0e-3) -> bool:
    return (a.xmin <= b.xmax + tol and b.xmin <= a.xmax + tol and a.ymin <= b.ymax + tol and b.ymin <= a.ymax + tol
            and a.zmin <= b.zmax + tol and b.zmin <= a.zmax + tol)


def drive_overlaps(bodies: dict) -> dict:
    """{(a, b): overlap volume mm3} for every pair of drive bodies with a positive overlap (bounding-box pairs only are intersected)."""
    bbs = {n: s.BoundingBox() for n, s in bodies.items()}
    out = {}
    for a, b in itertools.combinations(bodies, 2):
        if _bbox_hit(bbs[a], bbs[b]):
            v = bodies[a].intersect(bodies[b]).Volume()
            if v > 0.0:
                out[(a, b)] = v
    return out


def reference_interference(bodies: dict, refs: dict, min_vol: float = 0.01) -> list:
    """Overlap of each drive body with each reference part: rows {body, ref, volume, pieces: [(volume, bbox)]} (station frame), pieces smaller than min_vol dropped."""
    rows = []
    for rn, ref in refs.items():
        rb = ref.BoundingBox()
        for bn, body in bodies.items():
            if bn == "fin" or not _bbox_hit(body.BoundingBox(), rb):
                continue
            inter = body.intersect(ref)
            pieces = [(s.Volume(), s.BoundingBox()) for s in inter.Solids() if s.Volume() > min_vol]
            if pieces:
                rows.append({"body": bn, "ref": rn, "volume": sum(p[0] for p in pieces), "pieces": sorted(pieces, key=lambda p: -p[0])})
    return rows


def density(name: str) -> float:
    """g/cm3 of a drive body (typical values, not certified)."""
    d = dict(P.THERMAL_DENSITY_G_CM3)
    if name in P.NEMA17T_BODIES or name.startswith("motor_"):
        return N.material(name.replace("motor_", ""))[3]
    if name in (PINION, "spacer_near", "magnet_cap", SPOOL, SPACER, CAP):
        return d["petg"]
    if name == "fin":
        return d["aluminium"]
    if name == "magnet":
        return P.WG3_MAGNET_G_CM3
    if name in ("as5600_chip", "as5600_board"):
        return 0.0                                                               # envelopes: no mass claimed
    return d["steel"]                                                            # shaft, bearings (solid ring envelope: heavier than a real 687)


def mass_g(name: str, shape: cq.Shape) -> float:
    return shape.Volume() * density(name) / 1000.0


REFERENCE_PARTS = ("Slipin_mount_piecev3", "Wall_Mount_v3", "Shell_Casing", "Spool1011")    # Jasper's STEPs that the drive is checked against (read only)
MESH_POSES_DEG = tuple(float(a) for a in range(0, 21))                                       # pinion rotation, one pinion pitch (360 / 18 = 20 deg); the gear turns -1/3 of it
MESH_SLAB_T = 1.0                                                                            # mm, thickness of the tooth-face slab used for flank distances (spur teeth are prismatic along y)
CONTACT_TOL_MM = 1.0e-3                                                                      # flank distance that counts as tooth contact in the backlash search
BACKLASH_BRACKET_DEG = 4.0                                                                   # pinion rotation within which each flank contact must be found
BACKLASH_RESOLUTION_DEG = 1.0e-3                                                             # bisection stops at this bracket width (0.00016 mm at the pinion pitch circle)


def mesh_slabs(bodies: dict) -> tuple:
    """(pinion slab, gear slab, pinion axis point, gear axis point) in the station frame: the two tooth faces cut to MESH_SLAB_T around the middle of the teeth.  The teeth are
    prismatic along y, so the flank distance of the slabs is that of the whole faces, at a sixth of the cost of a distance between the full bodies."""
    pin, gear = bodies[PINION], bodies[SPOOL]
    pa, ga = bore_axis_xz(pin, P.WG3_PINION_BORE_D / 2.0), bore_axis_xz(gear, P.WG3_BORE_D / 2.0)
    y_mid = residual()[1] + (P.WG3_Y_TEETH0 + P.WG3_Y_TEETH1) / 2.0
    box = cq.Solid.makeBox(400.0, MESH_SLAB_T, 400.0, cq.Vector(-200.0, y_mid - MESH_SLAB_T / 2.0, -200.0))
    return pin.intersect(box), gear.intersect(box), cq.Vector(pa[0], 0, pa[1]), cq.Vector(ga[0], 0, ga[1])


def _rotated_pair(slabs: tuple, pinion_deg: float, gear_deg: float) -> tuple:
    """(pinion, gear) of mesh_slabs (or of full bodies packed the same way) rotated about their own axes (parallel to y) by the given angles."""
    pin, gear, po, go = slabs
    y_axis = cq.Vector(0, 1, 0)
    return pin.rotate(po, po + y_axis, pinion_deg), gear.rotate(go, go + y_axis, gear_deg)


def mesh_sweep(bodies: dict, poses_deg=MESH_POSES_DEG) -> list:
    """[(pinion angle deg, overlap mm3, flank distance mm)] of the tooth-face slabs, the gear turning -1/3 of the pinion angle (ratio 3:1, opposite sense)."""
    slabs = mesh_slabs(bodies)
    out = []
    for th in poses_deg:
        pr, gr = _rotated_pair(slabs, th, -th / P.WG3_RATIO)
        out.append((th, pr.intersect(gr).Volume(), pr.distance(gr)))
    return out


def backlash_measured(bodies: dict) -> dict:
    """Free play measured on the solids: the gear is held at the reference pose and the pinion is turned each way until the flanks touch (slab distance < CONTACT_TOL_MM,
    bisection to BACKLASH_RESOLUTION_DEG).  Returns the contact angles (deg), the total free play at the pinion (deg), the transverse backlash at the pinion pitch circle (mm)
    and the formula value 2 dCD tan(alpha) + both thinnings."""
    pitch_r = P.WG3_MODULE * P.WG3_Z_PINION / 2.0
    slabs = mesh_slabs(bodies)

    def contact(sign: float) -> float:
        lo, hi = 0.0, BACKLASH_BRACKET_DEG                                           # no contact at lo, contact (or overlap) at hi
        pr, gr = _rotated_pair(slabs, 0.0, 0.0)
        assert pr.distance(gr) > CONTACT_TOL_MM, "teeth already touch at the reference pose"
        pr, gr = _rotated_pair(slabs, sign * hi, 0.0)
        assert pr.distance(gr) < CONTACT_TOL_MM, f"no tooth contact within {hi} deg of pinion rotation"
        while hi - lo > BACKLASH_RESOLUTION_DEG:
            mid = 0.5 * (lo + hi)
            pr, gr = _rotated_pair(slabs, sign * mid, 0.0)
            lo, hi = (mid, hi) if pr.distance(gr) > CONTACT_TOL_MM else (lo, mid)
        return sign * 0.5 * (lo + hi)
    minus, plus = contact(-1.0), contact(1.0)
    play = plus - minus
    return {"minus_deg": minus, "plus_deg": plus, "play_deg": play, "backlash_mm": math.radians(play) * pitch_r,
            "formula_mm": 2.0 * P.WG3_CD_ALLOW * math.tan(math.radians(P.WG3_PRESSURE_ANGLE_DEG)) + P.WG3_GEAR_TOOTH_THIN + P.WG3_PINION_TOOTH_THIN}


def pinion_hub_solid() -> cq.Solid:
    """The pinion's Ø14 hub alone (no bore), station frame with the residual: what the gear tip must clear."""
    return axial_to_station(_cyl(P.WG3_PINION_HUB_D / 2.0, P.WG3_Y_PINION_HUB0, P.WG3_Y_TEETH0), P.WG3_MOTOR_XZ)


def clearance_report(bodies: dict) -> dict:
    """Solid-to-solid distances (mm) of the revision C criteria: gear tip to the pinion hub, gear to motor and fin, the pinion to the motor bodies (the shaft it sits on is
    reported apart), to the fin and to the slide-in (whose motor hole is R 11.2)."""
    gear, pin = bodies[SPOOL], bodies[PINION]
    motor = [k for k in bodies if k.startswith("motor_")]
    out = {"gear_hub": gear.distance(pinion_hub_solid())}
    out.update({f"gear_{k}": gear.distance(bodies[k]) for k in motor + ["fin"]})
    out.update({f"pinion_{k}": pin.distance(bodies[k]) for k in motor + ["fin"]})
    out["pinion_slipin"] = pin.distance(reference("Slipin_mount_piecev3"))
    return out


def print_reference_interference(bodies: dict) -> list:
    """Overlap of every drive body with Jasper's slide-in, wall mount, shell and the old spool (design-frame boxes; pieces under 0.01 mm3 dropped)."""
    dx, dy, dz = residual()
    rows = reference_interference(bodies, {n: reference(n) for n in REFERENCE_PARTS})
    for r in sorted(rows, key=lambda r: (REFERENCE_PARTS.index(r["ref"]), -r["volume"])):
        print(f"interference {r['ref']} - {r['body']}: {r['volume']:.2f} mm3 in {len(r['pieces'])} piece(s)")
        for v, bb in r["pieces"][:12]:
            print(f"    {v:10.2f} mm3  x[{bb.xmin - dx:8.2f},{bb.xmax - dx:8.2f}] y[{bb.ymin - dy:8.2f},{bb.ymax - dy:8.2f}] z[{bb.zmin - dz:8.2f},{bb.zmax - dz:8.2f}]")
    return rows


# =============================================================================================================================
# exports
# =============================================================================================================================
def export_parts(step_dir: str = STEP_DIR, stl_dir: str = STL_DIR) -> dict:
    """Print-frame STEP (named, one component) and STL of pinion (file pinion18), spool_gear54, magnet_cap_w3 and spacer_near_w3."""
    os.makedirs(step_dir, exist_ok=True)
    os.makedirs(stl_dir, exist_ok=True)
    out = {}
    for name, shape in print_parts().items():
        file = PART_FILE[name]
        step = N.export_named_step({name: shape}, os.path.join(step_dir, f"{NAME}_{file}.step"), assembly_name=f"{NAME}_{file}", colors={name: COLORS[PART_COLOR[name]]})
        stl = os.path.join(stl_dir, f"{NAME}_{file}.stl")
        cq.exporters.export(_wp(shape), stl, tolerance=0.01, angularTolerance=0.1)
        out[name] = {"step": step, "stl": stl}
    return out


def export_assemblies(step_dir: str = STEP_DIR) -> dict:
    """The named drive STEP, and the same plus Jasper's current slide-in and wall mount (assembly coordinates)."""
    bodies = build_drive()
    colors = dict(COLORS)
    out = {"drive": N.export_named_step(to_assembly(bodies), os.path.join(step_dir, f"{NAME}_drive_asm1021.step"), assembly_name=f"{NAME}_drive_asm1021", colors=colors)}
    with_ref = dict(bodies)
    with_ref["slipin_mount"] = reference("Slipin_mount_piecev3")
    with_ref["wall_mount"] = reference("Wall_Mount_v3")
    out["with_slipin"] = N.export_named_step(to_assembly(with_ref), os.path.join(step_dir, f"{NAME}_drive_with_slipin_asm1021.step"),
                                             assembly_name=f"{NAME}_drive_with_slipin_asm1021", colors=colors)
    return out


def export_gears(step_dir: str = STEP_DIR) -> dict:
    """The pinion + spool_gear54 pair in mesh as one STEP (assembly coordinates of the drive assembly, same colours).  The pinion alone is the printable part
    `winch_gear3_pinion18.step` (export_parts, print frame); there is no second pinion file."""
    pair = (PINION, SPOOL)
    asm = to_assembly(build_drive())
    return {"gears": N.export_named_step({k: asm[k] for k in pair}, os.path.join(step_dir, f"{NAME}_gears_asm1021.step"),
                                         assembly_name=f"{NAME}_gears_asm1021", colors={k: COLORS[k] for k in pair})}


# =============================================================================================================================
# renders (VTK, offscreen: run under xvfb-run)
# =============================================================================================================================
def _plane_section_faces(shape: cq.Shape, axis: int, value: float) -> tuple:
    """(section faces, other faces) of a shape already cut at the plane coordinate[axis] = value."""
    sec, rest = [], []
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Plane:
            n = f.normalAt()
            c = f.Center()
            if abs(abs((n.x, n.y, n.z)[axis]) - 1.0) < 1e-6 and abs((c.x, c.y, c.z)[axis] - value) < 1e-3:
                sec.append(f)
                continue
        rest.append(f)
    return sec, rest


def _cut_halfspace(shape: cq.Shape, axis: int, value: float, keep_low: bool) -> cq.Shape | None:
    """Keep the part of the shape with coordinate[axis] <= value (keep_low) or >= value; None if nothing is left."""
    big = 500.0
    lo = [-big, -big, -big]
    size = [2 * big] * 3
    if keep_low:
        lo[axis], size[axis] = value - big, big
    else:
        lo[axis], size[axis] = value, big
    box = cq.Solid.makeBox(size[0], size[1], size[2], cq.Vector(*lo))
    r = shape.intersect(box)
    return r if r.Volume() > 1e-6 else None


def _polydata(faces, tol: float, ang: float):
    import vtk
    pts, polys = vtk.vtkPoints(), vtk.vtkCellArray()
    for f in faces:
        verts, tris = f.tessellate(tol, ang)
        base = pts.GetNumberOfPoints()
        for v in verts:
            pts.InsertNextPoint(v.x, v.y, v.z)
        for t in tris:
            polys.InsertNextCell(3)
            for i in t:
                polys.InsertCellPoint(base + i)
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(polys)
    return pd


def _add_actor(ren, faces, rgb, tol: float, alpha: float = 1.0):
    import vtk
    if not faces:
        return
    nrm = vtk.vtkPolyDataNormals()
    nrm.SetInputData(_polydata(faces, tol, 0.15))
    nrm.SetFeatureAngle(35)
    nrm.SplittingOn()
    nrm.ConsistencyOn()
    nrm.Update()
    m = vtk.vtkPolyDataMapper()
    m.SetInputConnection(nrm.GetOutputPort())
    a = vtk.vtkActor()
    a.SetMapper(m)
    pr = a.GetProperty()
    pr.SetColor(*rgb)
    pr.SetAmbient(0.25)
    pr.SetDiffuse(0.75)
    pr.SetSpecular(0.15)
    pr.SetSpecularPower(20)
    pr.SetOpacity(alpha)
    ren.AddActor(a)


def _add_edges(ren, shape: cq.Shape, rgb=(0.12, 0.12, 0.14), width: float = 1.4, n: int = 20):
    import vtk
    ep, el = vtk.vtkPoints(), vtk.vtkCellArray()
    for e in shape.Edges():
        line = vtk.vtkPolyLine()
        pts = [e.positionAt(i / n) for i in range(n + 1)]
        line.GetPointIds().SetNumberOfIds(len(pts))
        for i, p in enumerate(pts):
            line.GetPointIds().SetId(i, ep.InsertNextPoint(p.x, p.y, p.z))
        el.InsertNextCell(line)
    pd = vtk.vtkPolyData()
    pd.SetPoints(ep)
    pd.SetLines(el)
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(pd)
    a = vtk.vtkActor()
    a.SetMapper(m)
    a.GetProperty().SetColor(*rgb)
    a.GetProperty().SetLineWidth(width)
    ren.AddActor(a)


def render_scene(items, path: str, focal, direction, up, scale: float, title: str, note: str = "", section=None, size=(1500, 950)) -> str:
    """items: [(shape, rgb)]; section = (axis index, value, keep_low): every item is cut there and its section faces are drawn in a lighter tone of its colour.
    direction = from the focal point toward the camera; scale = half the view height in mm (parallel projection)."""
    import vtk
    vtk.vtkMapper.SetResolveCoincidentTopologyToPolygonOffset()
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    for shape, rgb in items:
        if section is not None:
            shape = _cut_halfspace(shape, *section)
            if shape is None:
                continue
            sec, rest = _plane_section_faces(shape, section[0], section[1])
            _add_actor(ren, rest, rgb, 0.03)
            _add_actor(ren, sec, tuple(0.45 * c + 0.55 for c in rgb), 0.03)
        else:
            _add_actor(ren, shape.Faces(), rgb, 0.05)
        _add_edges(ren, shape)
    cam = ren.GetActiveCamera()
    cam.ParallelProjectionOn()
    norm = math.sqrt(sum(c * c for c in direction))
    d = [c / norm for c in direction]
    cam.SetFocalPoint(*focal)
    cam.SetPosition(*(f + 800.0 * c for f, c in zip(focal, d)))
    cam.SetViewUp(*up)
    cam.SetParallelScale(scale)
    ren.ResetCameraClippingRange()
    ren.RemoveAllLights()
    for pos, inten in (((0.6, 0.8, 1.0), 0.85), ((-0.7, -0.3, 1.0), 0.35)):
        light = vtk.vtkLight()
        light.SetLightTypeToCameraLight()
        light.SetPosition(*pos)
        light.SetIntensity(inten)
        ren.AddLight(light)
    for text, y, fs in ((title, size[1] - 34, 20), (note, 12, 15)):
        if not text:
            continue
        t = vtk.vtkTextActor()
        t.SetInput(text)
        t.GetTextProperty().SetColor(0.1, 0.1, 0.1)
        t.GetTextProperty().SetFontSize(fs)
        t.SetPosition(14, y)
        ren.AddViewProp(t)
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetMultiSamples(8)
    win.AddRenderer(ren)
    win.SetSize(*size)
    win.Render()
    grab = vtk.vtkWindowToImageFilter()
    grab.SetInput(win)
    grab.Update()
    w = vtk.vtkPNGWriter()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    w.SetFileName(path)
    w.SetInputConnection(grab.GetOutputPort())
    w.Write()
    return path


def render_all(out_dir: str = RENDER_DIR) -> list:
    """front, side, top, iso of the drive; the mesh close-up (section through the teeth); sections through the spool axis and through the tie-off."""
    bodies = build_drive()
    dx, dy, dz = residual()
    sx, sz = P.WG3_SPOOL_XZ[0] + dx, P.WG3_SPOOL_XZ[1] + dz
    mx, mz = P.WG3_MOTOR_XZ[0] + dx, P.WG3_MOTOR_XZ[1] + dz
    clip = cq.Solid.makeBox(120.0, 200.0, 70.0, cq.Vector(-60.0, -60.0, mz - 45.0))            # the fin is 228 mm tall: show only the part by the motor
    drawn = {k: (v.intersect(clip) if k == "fin" else v) for k, v in bodies.items()}
    items = [(drawn[k], COLORS[k]) for k in BODY_ORDER]
    paths = []
    zc = (mz + sz) / 2.0
    yc = 12.0
    note = "station_1021 frame: +x out of the wall, +y along the motor shaft toward the spool, +z up (fin shown clipped)"
    views = (("front", (1, 0, 0), (0, 0, 1), 58.0, "front: seen from +x (out of the wall), +y to the right"),
             ("side", (0, 1, 0), (0, 0, 1), 52.0, "side: end view from +y along the shafts (cable-drum side), +x to the left"),
             ("top", (0, 0, 1), (1, 0, 0), 58.0, "top: seen from +z, +y to the left"),
             ("iso", (0.62, 0.55, 0.55), (0, 0, 1), 62.0, "iso: from +x, +y, +z"))
    for tag, direction, up, scale, label in views:
        paths.append(render_scene(items, os.path.join(out_dir, f"{NAME}_{tag}.png"), (mx, yc, zc), direction, up, scale, f"{NAME}: {label}", note))
    # mesh close-up: section through the middle of the tooth faces (y = 15.825) seen from +y
    y_mesh = (P.WG3_Y_TEETH0 + P.WG3_Y_TEETH1) / 2.0 + dy
    mesh_items = [(bodies[k], COLORS[k]) for k in ("pinion", SPOOL, "motor_shaft")]
    paths.append(render_scene(mesh_items, os.path.join(out_dir, f"{NAME}_mesh.png"), (mx, y_mesh, mz - P.WG3_MODULE * P.WG3_Z_PINION / 2.0), (0, 1, 0), (0, 0, 1), 14.0,
                              f"{NAME}: mesh close-up, section y = {y_mesh:.3f} seen from +y",
                              f"{P.WG3_Z_PINION}T printed pinion above, {P.WG3_Z_GEAR}T printed gear below, centre distance {P.WG3_CD:.2f}: a pinion tooth stands in a gear space on the line of centres; +x to the left", section=(1, y_mesh, True)))
    # section through the spool axis (plane x = axis): spool, spacer, pinion, shaft, bearings, cap, magnet, chip, board
    sec_items = [(bodies[k], COLORS[k]) for k in BODY_ORDER if k not in ("fin",)]
    paths.append(render_scene(sec_items, os.path.join(out_dir, f"{NAME}_section_axis.png"), (sx, yc, zc), (1, 0, 0), (0, 0, 1), 58.0,
                              f"{NAME}: section through the spool axis (plane x = {sx:.3f}), seen from +x", "light tone = cut faces; +y to the right; the tie-off hole lies at x +5.25 (next render)",
                              section=(0, sx, True)))
    # zoom on the encoder end: cap bore, web, pocket with a crush rib, magnet, chip, PCB
    cap_items = [(bodies[k], COLORS[k]) for k in ("shaft", "bearing_far", SPOOL, "magnet_cap", "magnet", "as5600_chip", "as5600_board")]
    paths.append(render_scene(cap_items, os.path.join(out_dir, f"{NAME}_section_cap.png"), (sx, 52.0 + dy, sz), (1, 0, 0), (0, 0, 1), 15.0,
                              f"{NAME}: section through the encoder end, plane x = {sx:.3f}, seen from +x",
                              "+y to the right: far bearing, shaft end 0.3 short of the bore floor, 0.75 web, magnet in its pocket (crush rib at -z), chip 1.5 from the magnet, PCB",
                              section=(0, sx, True)))
    # section through the tie-off: plane y = drum mid-plane seen from +y
    y_tie = P.WG3_TIEOFF_Y + dy
    tie_items = [(bodies[k], COLORS[k]) for k in (SPOOL, "shaft")]
    paths.append(render_scene(tie_items, os.path.join(out_dir, f"{NAME}_section_tieoff.png"), (sx, y_tie, sz), (0, 1, 0), (0, 0, 1), 36.0,
                              f"{NAME}: section at the drum mid-plane y = {y_tie:.3f}, seen from +y",
                              "1.4 mm chord hole 5.25 mm off the axis toward +x (left in this view), open on the winding surface at both ends; 7 mm bore, 15 mm core", section=(1, y_tie, True), size=(1100, 1100)))
    return paths


# =============================================================================================================================
# report
# =============================================================================================================================
def main(render: bool = True) -> None:
    parts = print_parts()
    for name, shape in parts.items():
        bb = shape.BoundingBox()
        print(f"{name:<14} valid={shape.isValid()} solids={len(shape.Solids())} vol={shape.Volume():9.2f} mm3 mass={mass_g(name, shape):6.2f} g (PETG) "
              f"bbox x[{bb.xmin:.3f},{bb.xmax:.3f}] y[{bb.ymin:.3f},{bb.ymax:.3f}] z[{bb.zmin:.3f},{bb.zmax:.3f}] (print frame, bed face z = 0)")
        print("   print:", PRINT_NOTE[name])
    for name, files in export_parts().items():
        print("exported", name, files["step"], files["stl"])
    bodies = build_drive()
    tot = 0.0
    for k, s in bodies.items():
        bb = s.BoundingBox()
        m = mass_g(k, s)
        tot += m if k not in ("fin",) and not k.startswith("motor_") else 0.0
        print(f"{k:<16} valid={s.isValid()} vol={s.Volume():10.2f} mm3 mass={m:8.2f} g  x[{bb.xmin:8.3f},{bb.xmax:8.3f}] y[{bb.ymin:8.3f},{bb.ymax:8.3f}] z[{bb.zmin:8.3f},{bb.zmax:8.3f}]")
    print(f"drive train without motor and fin: {tot:.1f} g (no heat-set insert, set screw or magnet-glue mass)")
    dx, dy, dz = residual()
    pin, spo = bore_axis_xz(bodies[PINION], P.WG3_PINION_BORE_D / 2.0), bore_axis_xz(bodies[SPOOL], P.WG3_BORE_D / 2.0)
    print(f"centre distance {math.hypot(pin[0] - spo[0], pin[1] - spo[1]):.4f} (spool axis x {spo[0] - dx:.4f}, z {spo[1] - dz:.4f} in the design frame)")
    for k, v in sorted(drive_overlaps(bodies).items(), key=lambda kv: -kv[1]):
        print(f"overlap {k[0]} - {k[1]}: {v:.4f} mm3")
    for k, v in clearance_report(bodies).items():
        print(f"clearance {k}: {v:.4f} mm")
    sweep = mesh_sweep(bodies)
    print(f"mesh sweep, {len(sweep)} poses over one pinion pitch: max overlap {max(r[1] for r in sweep):.4f} mm3, flank distance min {min(r[2] for r in sweep):.4f} / "
          f"max {max(r[2] for r in sweep):.4f} mm (conjugate pair: the same at every pose)")
    bl = backlash_measured(bodies)
    print(f"backlash: contact at {bl['minus_deg']:.4f} / {bl['plus_deg']:.4f} deg of the pinion, free play {bl['play_deg']:.4f} deg = {bl['backlash_mm']:.4f} mm at the pitch circle "
          f"(formula 2 dCD tan(20) + thinning of both gears = {bl['formula_mm']:.4f} mm)")
    print_reference_interference(bodies)
    for k, p in export_assemblies().items():
        print("exported assembly", k, p)
    for k, p in export_gears().items():
        print("exported gears", k, p)
    if render:
        for p in render_all():
            print("render", p)


if __name__ == "__main__":
    main(render="--no-render" not in sys.argv)
