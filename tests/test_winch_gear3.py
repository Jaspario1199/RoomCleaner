"""
Acceptance checks for the winch 3:1 spur drive train (cad/parts/winch_gear3.py, parameters WG3_*, spec cad/WINCH_GEAR3_SPEC.md).

Everything is measured on the built B-rep solids (no value is read back from the parameter that produced it, except where a test states the spec number it
checks) and on STEP files written by the builder.  Part tests use the print frame (axis = z, bed face z = 0); drive tests use the station_1021 frame with the
extraction residual subtracted where a design value is compared.
Run with /usr/bin/python3 -m pytest tests/test_winch_gear3.py
"""

from __future__ import annotations

import math
import os
import sys

import pytest

cq = pytest.importorskip("cadquery")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                      # noqa: E402
from cad.parts import nema17_thermal as N                        # noqa: E402
from cad.parts import winch_gear3 as W                           # noqa: E402
from cad.reference.station_1021.extract import O                 # noqa: E402

RES = W.residual()
TOL = 1.0e-3                                                     # mm, measurement tolerance of dimension checks
LIMIT = P.THERMAL_OVERLAP_LIMIT_MM3                              # 0.01 mm3: the no-overlap limit of the spec


# ---------------------------------------------------------------------------------------------------------------------
# fixtures and measuring helpers
# ---------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def parts():
    return W.print_parts()


@pytest.fixture(scope="module")
def drive():
    return W.build_drive()


def _bb(sh):
    b = sh.BoundingBox()
    return b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax


def _inside(shape):
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.TopAbs import TopAbs_IN
    from OCP.gp import gp_Pnt
    c = BRepClass3d_SolidClassifier(shape.Solids()[0].wrapped)

    def f(p):
        c.Perform(gp_Pnt(*p), 1e-7)
        return c.State() == TopAbs_IN
    return f


def _cyl_faces(shape, radius, axis_dir=None, tol=1e-4):
    """Cylindrical faces of this radius (optionally with the axis along 'x', 'y' or 'z'): list of (axis location, bbox of the face)."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    out = []
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() != GeomAbs_Cylinder or abs(a.Cylinder().Radius() - radius) > tol:
            continue
        d = a.Cylinder().Axis().Direction()
        if axis_dir is not None and abs(abs((d.X(), d.Y(), d.Z())["xyz".index(axis_dir)]) - 1.0) > 1e-9:
            continue
        loc = a.Cylinder().Axis().Location()
        out.append(((loc.X(), loc.Y(), loc.Z()), f.BoundingBox()))
    return out


def _plane_faces(shape, axis, value, tol=1e-4):
    """Planar faces whose normal is along `axis` at coordinate `value`."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane
    out = []
    for f in shape.Faces():
        if BRepAdaptor_Surface(f.wrapped).GetType() != GeomAbs_Plane:
            continue
        n, c = f.normalAt(), f.Center()
        i = "xyz".index(axis)
        if abs(abs((n.x, n.y, n.z)[i]) - 1.0) < 1e-6 and abs((c.x, c.y, c.z)[i] - value) < tol:
            out.append(f)
    return out


def _station(design_xyz):
    return tuple(c + r for c, r in zip(design_xyz, RES))


# ---------------------------------------------------------------------------------------------------------------------
# parameters: the spec numbers
# ---------------------------------------------------------------------------------------------------------------------
def test_parameters_are_the_spec_values():
    assert (P.WG3_MODULE, P.WG3_PRESSURE_ANGLE_DEG, P.WG3_Z_PINION, P.WG3_Z_GEAR) == (1.0, 20.0, 20, 60)
    assert P.WG3_RATIO == 3.0
    assert abs(P.WG3_CD_NOMINAL - 40.0) < 1e-12 and abs(P.WG3_CD - 40.20) < 1e-12 and P.WG3_CD_ALLOW == 0.20
    assert P.WG3_GEAR_TOOTH_THIN == 0.10 and P.WG3_FACE == 10.0
    assert abs(P.WG3_SPOOL_XZ[1] - (2.64 - 40.20)) < 1e-12 and abs(P.WG3_SPOOL_XZ[1] + 37.56) < 1e-12 and P.WG3_SPOOL_XZ[0] == 0.0
    assert abs(P.WG3_Y_SHAFT_END - 20.825) < 1e-9 and abs(P.WG3_Y_TEETH0 - 10.825) < 1e-9 and abs(P.WG3_Y_PINION_HUB0 - 5.825) < 1e-9
    assert (P.WG3_WINDOW_N, P.WG3_WINDOW_D, P.WG3_WINDOW_R) == (6, 11.0, 20.0)
    assert (P.WG3_DRUM_D, P.WG3_FLANGE_D, P.WG3_FLANGE_T, P.WG3_HUB_D, P.WG3_BORE_D) == (15.0, 36.0, 3.0, 12.0, 7.00)
    assert abs(P.WG3_Y_DRUM1 - 36.825) < 1e-9 and abs(P.WG3_Y_FLANGE1 - 39.825) < 1e-9 and P.WG3_Y_SPOOL_END == 44.0
    assert (P.WG3_LAND_D, P.WG3_LAND_PROUD, P.WG3_BED_CHAMFER) == (9.0, 0.3, 0.3)
    assert (P.WG3_TIEOFF_D, P.WG3_TIEOFF_OFFSET) == (1.4, 5.25) and abs(P.WG3_TIEOFF_Y - 28.825) < 1e-9
    assert (P.WG3_SPACER_OD, P.WG3_SPACER_BORE_D, P.WG3_SPACER_Y0) == (10.0, 7.10, 5.0) and abs(P.WG3_SPACER_Y1 - 10.825) < 1e-9
    assert (P.WG3_SHAFT_D, P.WG3_SHAFT_Y0, P.WG3_SHAFT_L) == (7.0, -3.0, 55.0)
    assert (P.WG3_CAP_D, P.WG3_CAP_Y0, P.WG3_CAP_BORE_DEPTH, P.WG3_CAP_WEB) == (12.0, 49.3, 3.0, 0.75)
    assert abs(P.WG3_Y_MAGNET0 - 53.05) < 1e-9 and abs(P.WG3_CAP_Y1 - 55.55) < 1e-9 and abs(P.WG3_CAP_POCKET_D - 6.3) < 1e-9
    assert (P.WG3_MAGNET_D, P.WG3_MAGNET_T) == (6.0, 2.5)
    assert abs(P.WG3_CHIP_FACE_Y - 57.05) < 1e-9 and abs(P.WG3_PCB_Y0 - 58.5) < 1e-9 and abs(P.WG3_PCB_Y1 - 60.1) < 1e-9


# ---------------------------------------------------------------------------------------------------------------------
# the printable parts
# ---------------------------------------------------------------------------------------------------------------------
def test_printable_parts_are_single_valid_solids(parts):
    assert set(parts) == {"spool_gear60", "spacer_near_w3", "magnet_cap_w3"}
    for name, s in parts.items():
        assert s.isValid() and len(s.Solids()) == 1 and s.Volume() > 0, name


def test_spool_extent_and_print_frame(parts):
    """Print frame: axis +z, near gear face (design y 10.825) on the bed z = 0; the part runs 33.175 high (y 10.825 .. 44.0)."""
    x0, x1, y0, y1, z0, z1 = _bb(parts["spool_gear60"])
    assert abs(z0) < TOL and abs(z1 - (44.0 - 10.825)) < TOL
    assert 30.9 < x1 < 31.001 and -31.001 < x0 < -30.9 and 30.9 < y1 < 31.001                 # tip circle Ø62 (the teeth do not reach the axes exactly)
    bed = _plane_faces(parts["spool_gear60"], "z", 0.0)
    assert len(bed) == 1 and bed[0].Area() > 1000.0                                           # a flat bed face: the gear's near face
    far = _plane_faces(parts["spool_gear60"], "z", 44.0 - 10.825)
    assert len(far) == 1 and abs(far[0].Area() - math.pi * 4.5 ** 2 + math.pi * 3.5 ** 2) < 0.1   # the far Ø9 land minus the Ø7 bore


def test_gear_teeth_sixty_tip_and_root_diameters(parts):
    s = parts["spool_gear60"]
    tips = _cyl_faces(s, 31.0, "z")
    roots = _cyl_faces(s, 28.75, "z")
    assert len(tips) == 60 and len(roots) == 60                                               # one tip face and one root face per tooth: 60T
    assert all(abs(t[0][0]) < TOL and abs(t[0][1]) < TOL for t in tips)                       # all on the axis
    # teeth span the gear face (the tip faces start 0.3 above the bed face: the chamfer)
    zs = sorted(t[1].zmin for t in tips)
    assert abs(zs[0] - 0.3) < 0.01 and abs(max(t[1].zmax for t in tips) - 10.0) < 0.01


def test_bed_face_tooth_chamfer(parts):
    """0.3 x 45 deg on the tooth edges of the bed face: the outline on the bed face reaches only R 30.7, and the flat bed face is smaller than the section 0.3 up."""
    s = parts["spool_gear60"]
    bed = _plane_faces(s, "z", 0.0)[0]
    r_bed = max(math.hypot(v.X, v.Y) for v in bed.Vertices())
    assert 30.6 < r_bed < 30.71, r_bed
    top = s.intersect(cq.Solid.makeBox(100, 100, 0.01, cq.Vector(-50, -50, 0.30)))
    slab = max(top.Solids(), key=lambda x: x.Volume())
    assert slab.BoundingBox().xlen > s.intersect(cq.Solid.makeBox(100, 100, 0.01, cq.Vector(-50, -50, 0.0))).BoundingBox().xlen + 0.2


def test_lightening_windows(parts):
    s = parts["spool_gear60"]
    wins = [w for w in _cyl_faces(s, 5.5, "z")]
    assert len(wins) == 6                                                                      # six Ø11 windows
    for loc, bb in wins:
        assert abs(math.hypot(loc[0], loc[1]) - 20.0) < TOL                                   # on R 20
        assert bb.zmin < 0.01 and abs(bb.zmax - 10.0) < 0.01                                  # through the 10 mm gear face
    rim = 28.75 - (20.0 + 5.5)
    web = (20.0 - 5.5) - 7.5
    assert abs(rim - 3.25) < 1e-9 and rim >= P.WG3_RIM_MIN                                    # rim below the root >= 3 mm
    assert web >= P.WG3_WEB_MIN                                                               # web to the drum core >= 2 mm


def test_drum_flange_hub_bore_and_lands(parts):
    s = parts["spool_gear60"]
    z0 = 10.825
    drum = _cyl_faces(s, 7.5, "z")
    assert len(drum) >= 1 and abs(min(d[1].zmin for d in drum) - (20.825 - z0)) < TOL and abs(max(d[1].zmax for d in drum) - (36.825 - z0)) < TOL
    fl = _cyl_faces(s, 18.0, "z")
    assert len(fl) >= 1 and abs(min(d[1].zmin for d in fl) - (36.825 - z0)) < TOL and abs(max(d[1].zmax for d in fl) - (39.825 - z0)) < TOL
    hub = _cyl_faces(s, 6.0, "z")
    assert len(hub) >= 1 and abs(min(d[1].zmin for d in hub) - (39.825 - z0)) < TOL and abs(max(d[1].zmax for d in hub) - (43.7 - z0)) < TOL
    land = _cyl_faces(s, 4.5, "z")
    assert len(land) >= 1 and abs(min(d[1].zmin for d in land) - (43.7 - z0)) < TOL and abs(max(d[1].zmax for d in land) - (44.0 - z0)) < TOL   # Ø9, 0.3 proud
    bore = _cyl_faces(s, 3.5, "z")
    assert len(bore) >= 1 and abs(min(d[1].zmin for d in bore)) < TOL and abs(max(d[1].zmax for d in bore) - (44.0 - z0)) < TOL           # Ø7.00 through
    assert all(abs(b[0][0]) < TOL and abs(b[0][1]) < TOL for b in bore)
    inner_flange = _plane_faces(s, "z", 36.825 - z0)                                          # flange inner face (printed on supports)
    assert len(inner_flange) == 1 and inner_flange[0].normalAt().z < 0                        # faces down in the print frame: the overhang over the drum


def test_tie_off_chord_hole(parts):
    s = parts["spool_gear60"]
    holes = _cyl_faces(s, 0.7, "y")
    assert len(holes) >= 1
    zc = 28.825 - 10.825                                                                       # the drum mid-plane y 28.825 in the print frame
    for loc, bb in holes:
        assert abs(loc[0] - 5.25) < TOL and abs(loc[2] - zc) < TOL                           # axis 5.25 mm off the spool axis (toward +x), at the mid-plane
        assert abs((bb.zmin + bb.zmax) / 2 - zc) < TOL and abs((bb.zmax - bb.zmin) - 1.4) < 0.01   # perpendicular to the spool axis: spans the Ø1.4 only
    assert min(bb.ymin for _, bb in holes) < -5.2 and max(bb.ymax for _, bb in holes) > 5.2   # open on the winding surface at both ends (chord +-5.36)
    inside = _inside(s)
    # ligaments along the line through the hole's closest points to the bore and to the core surface (x axis, z = zc, y = 0)
    assert inside((3.6, 0, zc)) and inside((4.54, 0, zc)) and not inside((4.56, 0, zc))      # 1.05 mm of material between the Ø7 bore (R3.5) and the hole (edge 4.55)
    assert not inside((5.25, 0, zc)) and inside((5.96, 0, zc)) and inside((7.49, 0, zc)) and not inside((7.51, 0, zc))   # 1.55 mm to the core surface R7.5 (hole edge 5.95)
    assert abs((5.25 - 0.7 - 3.5) - 1.05) < 1e-9 and abs((7.5 - 5.25 - 0.7) - 1.55) < 1e-9


def test_spacer_near(parts):
    s = parts["spacer_near_w3"]
    x0, x1, y0, y1, z0, z1 = _bb(s)
    assert abs(z0) < TOL and abs(z1 - (10.825 - 5.0)) < TOL and abs(x1 - 5.0) < TOL and abs(x0 + 5.0) < TOL        # Ø10 x 5.825
    assert _cyl_faces(s, 3.55, "z") and abs(_cyl_faces(s, 3.55, "z")[0][1].zmax - 5.825) < TOL                    # Ø7.10 bore, through
    lands = _cyl_faces(s, 4.5, "z")
    assert len(lands) >= 2                                                                    # Ø9 lands on both ends
    zs = sorted((l[1].zmin, l[1].zmax) for l in lands)
    assert abs(zs[0][0]) < TOL and abs(zs[0][1] - 0.3) < TOL and abs(zs[-1][0] - (5.825 - 0.3)) < TOL and abs(zs[-1][1] - 5.825) < TOL
    assert _plane_faces(s, "z", 0.0) and _plane_faces(s, "z", 5.825)                          # flat end faces: prints on either


def test_magnet_cap_geometry(parts):
    s = parts["magnet_cap_w3"]
    x0, x1, y0, y1, z0, z1 = _bb(s)
    assert abs(z0) < TOL and abs(z1 - 6.25) < TOL and abs(x1 - 6.0) < TOL                    # Ø12 x 6.25 (y 49.3 .. 55.55)
    assert _cyl_faces(s, 3.5, "z") and abs(max(c[1].zmax for c in _cyl_faces(s, 3.5, "z")) - 3.0) < TOL           # Ø7 bore 3.0 deep from the bearing side
    pocket = _cyl_faces(s, 3.15, "z")
    assert pocket and abs(min(c[1].zmin for c in pocket) - 3.75) < TOL and abs(max(c[1].zmax for c in pocket) - 6.25) < TOL   # Ø6.3 pocket 2.5 deep
    inside = _inside(s)
    assert inside((0, 0, 3.375)) and not inside((0, 0, 2.9)) and not inside((0, 0, 3.8)) and not inside((0, 0, 6.2))   # web 0.75 between bore floor 3.0 and pocket floor 3.75
    rg = W.magnet_rib_geometry()
    assert abs(rg["r_tip"] - 2.88) < 1e-9 and abs(rg["h"] - 0.27) < 1e-9 and rg["n"] == 3
    for k in range(3):                                                                         # a rib on each of three directions, voids in between
        a = math.radians(P.WG3_MAGNET_RIB_PHASE_DEG + 120 * k)
        assert inside((3.0 * math.cos(a), 3.0 * math.sin(a), 4.5))
        b = a + math.radians(60)
        assert not inside((3.0 * math.cos(b), 3.0 * math.sin(b), 4.5))


def test_magnet_cap_crush_ribs_overlap_the_magnet_only_by_the_designed_crush(drive):
    """The only drive pair that may overlap: 3 crush ribs bite 0.12 mm into the Ø6 magnet (ENC1021_V2 rule)."""
    v = drive["magnet_cap"].intersect(drive["magnet"]).Volume()
    g = W.magnet_rib_geometry()
    crush = P.ENC1021_V2_MAGNET_RIB_CRUSH
    r_mag = P.WG3_MAGNET_D / 2.0
    w_at_magnet = g["tip_w"] + (g["base_w"] - g["tip_w"]) * crush / (g["r_wall"] + W.RIB_INSET - g["r_tip"])
    est = g["n"] * crush * (g["tip_w"] + w_at_magnet) / 2.0 * P.WG3_CAP_POCKET_DEPTH         # no lead-in: an upper bound
    assert 0.6 * est < v <= 1.02 * est, (v, est)
    assert r_mag - g["r_tip"] == pytest.approx(crush)


# ---------------------------------------------------------------------------------------------------------------------
# the purchased pinion
# ---------------------------------------------------------------------------------------------------------------------
def test_pinion(drive):
    p = drive["pinion"]
    assert p.isValid() and len(p.Solids()) == 1
    tips = _cyl_faces(p, 11.0, "y")
    roots = _cyl_faces(p, 8.75, "y")
    assert len(tips) == 20 and len(roots) == 20                                               # 20T, tip Ø22, root Ø17.5
    hub = _cyl_faces(p, 7.0, "y")
    assert hub and abs(min(h[1].ymin for h in hub) - _station((0, 5.825, 0))[1]) < TOL and abs(max(h[1].ymax for h in hub) - _station((0, 10.825, 0))[1]) < TOL
    assert abs(min(t[1].ymin for t in tips) - _station((0, 10.825, 0))[1]) < TOL and abs(max(t[1].ymax for t in tips) - _station((0, 20.825, 0))[1]) < TOL
    bore = _cyl_faces(p, 2.5, "y")
    assert bore and all(abs(b[0][0] - RES[0]) < TOL and abs(b[0][2] - (2.64 + RES[2])) < TOL for b in bore)     # Ø5 bore on the motor axis
    # M3 set-screw hole on the +z side (onto the shaft D-flat) at the hub mid-plane, closed on the -z side
    inside = _inside(p)
    ax, az = RES[0], 2.64 + RES[2]
    ym = _station((0, 8.325, 0))[1]
    assert not inside((ax, ym, az + 5.0)) and inside((ax, ym, az - 5.0))
    # the pinion's tooth (not a space) is on the line of centres toward the gear: the point on the pitch circle there is material
    assert inside((ax, _station((0, 15.825, 0))[1], az - 10.0))


# ---------------------------------------------------------------------------------------------------------------------
# the drive assembly
# ---------------------------------------------------------------------------------------------------------------------
def test_body_list_and_solids(drive):
    expected = ["motor_front_cap", "motor_stator", "motor_winding", "motor_rear_cap", "motor_shaft", "motor_connector", "fin", "pinion", "spool_gear60", "shaft",
                "bearing_near", "bearing_far", "spacer_near", "magnet_cap", "magnet", "as5600_chip", "as5600_board"]
    assert list(drive) == expected
    for k, s in drive.items():
        assert s.isValid() and len(s.Solids()) == 1 and s.Volume() > 0, k


def test_centre_distance_and_ratio(drive):
    pin = W.bore_axis_xz(drive["pinion"], 2.5)
    spo = W.bore_axis_xz(drive["spool_gear60"], 3.5)
    cd = math.hypot(pin[0] - spo[0], pin[1] - spo[1])
    assert abs(cd - 40.20) < 1e-4, cd                                                         # built centre distance
    assert abs(cd - 40.0 - 0.20) < 1e-4
    assert abs(pin[0] - spo[0]) < 1e-9                                                       # the spool is straight below the motor
    assert abs((spo[1] - RES[2]) + 37.56) < 1e-4 and abs((spo[0] - RES[0])) < 1e-4            # spool axis x 0, z -37.56
    assert abs((pin[1] - RES[2]) - 2.64) < 1e-4                                               # motor axis z 2.64
    n_gear = len(_cyl_faces(drive["spool_gear60"], 31.0, "y"))
    n_pinion = len(_cyl_faces(drive["pinion"], 11.0, "y"))
    assert (n_gear, n_pinion) == (60, 20) and n_gear / n_pinion == pytest.approx(3.0)       # ratio 3.00 from the measured tooth counts


def test_motor_stack_and_shaft_end(drive):
    fin_front = drive["fin"].BoundingBox().ymin
    cap = drive["motor_front_cap"]
    assert abs(fin_front - (RES[1] - 3.175)) < 2e-3                                           # 1/8 in fin y -3.175 .. 0
    assert abs(drive["fin"].BoundingBox().ymax - RES[1]) < 2e-3
    pilot_end = cap.BoundingBox().ymax
    front_face = pilot_end - P.NEMA17T_PILOT_H
    assert abs(front_face - fin_front) < 1e-6                                                 # motor front face on the fin's motor face
    shaft = drive["motor_shaft"]
    assert abs(shaft.BoundingBox().ymax - (RES[1] + 20.825)) < 2e-3                          # shaft end y 20.825
    flat = _plane_faces(shaft, "z", 2.64 + RES[2] + 2.0)                                      # 0.5 mm D-flat on the +z side
    assert flat and abs(flat[0].Area() - 2 * math.sqrt(2.5 ** 2 - 2.0 ** 2) * (20.825 - (-3.175 + 2.0))) < 0.5


def test_shaft_bearings_cap_stack_levels(drive):
    def y(name):
        b = drive[name].BoundingBox()
        return b.ymin - RES[1], b.ymax - RES[1]
    near, far = y("bearing_near"), y("bearing_far")
    assert abs(near[0]) < 2e-3 and abs(near[1] - 5.0) < 2e-3 and abs(far[0] - 44.0) < 2e-3 and abs(far[1] - 49.0) < 2e-3        # 687: y 0..5 and 44..49
    sh = y("shaft")
    assert abs(sh[0] + 3.0) < 2e-3 and abs(sh[1] - 52.0) < 2e-3                              # Ø7 x 55, y -3 .. 52
    assert abs(drive["shaft"].BoundingBox().xlen - 7.0) < 2e-3
    sp = y("spacer_near")
    assert abs(sp[0] - 5.0) < 2e-3 and abs(sp[1] - 10.825) < 2e-3
    cp = y("magnet_cap")
    assert abs(cp[0] - 49.3) < 2e-3 and abs(cp[1] - 55.55) < 2e-3
    mg = y("magnet")
    assert abs(mg[0] - 53.05) < 2e-3 and abs(mg[1] - 55.55) < 2e-3 and abs(drive["magnet"].BoundingBox().xlen - 6.0) < 2e-3
    chip, board = y("as5600_chip"), y("as5600_board")
    assert abs(chip[0] - 57.05) < 2e-3 and abs(chip[1] - 58.5) < 2e-3                         # chip face 57.05, chip 1.45 tall
    assert abs(board[0] - 58.5) < 2e-3 and abs(board[1] - 60.1) < 2e-3                        # PCB 1.6 thick behind it
    assert abs((chip[0] - mg[1]) - 1.5) < 2e-3                                                # air gap magnet face to chip face 1.5 (encoder1021 convention)
    bb = drive["as5600_board"].BoundingBox()
    assert abs(bb.xlen - 23.0) < 2e-3 and abs(bb.zlen - 23.0) < 2e-3
    assert abs((bb.xmin + bb.xmax) / 2 - RES[0]) < 2e-3 and abs((bb.zmin + bb.zmax) / 2 - (-37.56 + RES[2])) < 2e-3          # centred on the spool axis
    cb = drive["as5600_chip"].BoundingBox()
    assert abs(cb.xlen - 6.0) < 2e-3 and abs(cb.zlen - 4.0) < 2e-3
    sc = drive["magnet_cap"]
    inside = _inside(sc)
    sa = _station((0.0, 0.0, -37.56))
    assert not inside((sa[0], 52.15 + RES[1], sa[2]))                                         # the shaft end (52.0) is 0.3 mm short of the bore floor (52.3)
    assert abs(drive["shaft"].distance(drive["magnet_cap"])) < 1e-6                           # shaft in the cap bore: touching, not overlapping


def test_no_overlap_between_any_two_drive_bodies(drive):
    ov = W.drive_overlaps(drive)
    allowed = {("magnet_cap", "magnet")}                                                      # the designed crush ribs (previous test bounds it)
    bad = {k: v for k, v in ov.items() if v > LIMIT and k not in allowed}
    assert not bad, bad
    assert ("magnet_cap", "magnet") in ov and ov[("magnet_cap", "magnet")] < 1.0


def test_mesh_has_no_overlap_through_a_tooth_pitch(drive):
    """Pinion and gear at the reference pose and rotated through a pinion pitch (18 deg: 6 deg of the gear): no overlap, positive flank clearance."""
    pin, gear = drive["pinion"], drive["spool_gear60"]
    pa = W.bore_axis_xz(pin, 2.5)
    ga = W.bore_axis_xz(gear, 3.5)
    p_origin, g_origin = cq.Vector(pa[0], 0, pa[1]), cq.Vector(ga[0], 0, ga[1])
    y_axis = cq.Vector(0, 1, 0)
    for th in (0.0, 4.5, 9.0, 13.5, 18.0):
        pr = pin.rotate(p_origin, p_origin + y_axis, th)
        gr = gear.rotate(g_origin, g_origin + y_axis, -th / 3.0)
        assert pr.intersect(gr).Volume() <= LIMIT, th
        assert pr.distance(gr) > 0.05, (th, pr.distance(gr))


def test_clearances(drive):
    gear = drive["spool_gear60"]
    hub = W.axial_to_station(W._cyl(P.WG3_PINION_HUB_D / 2.0, P.WG3_Y_PINION_HUB0, P.WG3_Y_TEETH0), P.WG3_MOTOR_XZ)
    assert gear.distance(hub) >= P.WG3_MIN_CLEAR                                              # gear tip to pinion hub >= 1.5 (about 2.33)
    for k in ("motor_front_cap", "motor_stator", "motor_winding", "motor_rear_cap", "motor_shaft", "motor_connector", "fin"):
        assert gear.distance(drive[k]) >= P.WG3_MIN_CLEAR, k
    tab_face = RES[1] + 5.0
    assert drive["pinion"].BoundingBox().ymin - tab_face == pytest.approx(0.825, abs=2e-3)    # 0.825 clear of the tab face


def test_axial_stack_contacts(drive):
    """Faces that must touch do (distance 0), and the 0.3 mm lands keep the Ø12 / Ø10 bodies off the bearing faces."""
    d = drive
    assert d["spacer_near"].distance(d["bearing_near"]) < 1e-6                                # spacer land on the near inner race (y 5.0)
    assert d["spacer_near"].distance(d["spool_gear60"]) < 1e-6                                # spacer land on the gear's near face (y 10.825)
    assert d["spool_gear60"].distance(d["bearing_far"]) < 1e-6                                # far land on the far inner race (y 44.0)
    assert d["spool_gear60"].distance(d["spacer_near"]) < 1e-6
    assert d["spool_gear60"].distance(d["bearing_near"]) > 5.0                                # nothing else of the spool near the near bearing
    assert d["magnet_cap"].distance(d["bearing_far"]) == pytest.approx(0.3, abs=2e-3)         # cap 0.3 mm above the far bearing
    assert d["magnet"].distance(d["magnet_cap"]) < 1e-6                                       # magnet seated on the pocket floor
    assert d["as5600_chip"].distance(d["as5600_board"]) < 1e-6 and d["magnet"].distance(d["as5600_chip"]) == pytest.approx(1.5, abs=2e-3)


# ---------------------------------------------------------------------------------------------------------------------
# Jasper's current parts: the interferences are redesign inputs, they must stay confined to the expected places
# ---------------------------------------------------------------------------------------------------------------------
def test_interference_with_current_slipin_and_wall_mount(drive):
    refs = {"Slipin_mount_piecev3": W.reference("Slipin_mount_piecev3"), "Wall_Mount_v3": W.reference("Wall_Mount_v3")}
    rows = W.reference_interference(drive, refs)
    by = {(r["body"], r["ref"]): r for r in rows}
    assert by[("spool_gear60", "Slipin_mount_piecev3")]["volume"] > 1000.0                    # the gear cuts through the deck block, the lug cheek and the back plate
    assert ("shaft", "Slipin_mount_piecev3") in by and ("spacer_near", "Slipin_mount_piecev3") in by
    assert ("spool_gear60", "Wall_Mount_v3") in by                                            # teeth against the wall mount's lower part
    untouched = {"pinion", "motor_front_cap", "motor_stator", "motor_winding", "motor_rear_cap", "motor_shaft", "motor_connector", "bearing_near", "bearing_far",
                 "magnet_cap", "magnet", "as5600_chip", "as5600_board"}
    assert not [k for k in by if k[0] in untouched], [k for k in by if k[0] in untouched]     # pinion, motor, bearings and the encoder stack do not touch either


# ---------------------------------------------------------------------------------------------------------------------
# exports: STEP round trip (volume and bounding box within 0.1 %), names, and the files in the repo
# ---------------------------------------------------------------------------------------------------------------------
def _same(a: cq.Shape, b: cq.Shape):
    assert abs(a.Volume() - b.Volume()) <= P.WG3_RT_TOL * a.Volume()
    ba, bb = a.BoundingBox(), b.BoundingBox()
    size = max(ba.xlen, ba.ylen, ba.zlen)
    for u, v in ((ba.xmin, bb.xmin), (ba.xmax, bb.xmax), (ba.ymin, bb.ymin), (ba.ymax, bb.ymax), (ba.zmin, bb.zmin), (ba.zmax, bb.zmax)):
        assert abs(u - v) <= P.WG3_RT_TOL * size
    for u, v in ((ba.xlen, bb.xlen), (ba.ylen, bb.ylen), (ba.zlen, bb.zlen)):
        assert abs(u - v) <= P.WG3_RT_TOL * max(u, 1e-9)


def test_step_round_trip_of_the_parts(parts, tmp_path):
    out = W.export_parts(str(tmp_path / "step"), str(tmp_path / "stl"))
    for name, shape in parts.items():
        back = N.read_named_step(out[name]["step"])
        assert list(back) == [name]
        _same(shape, back[name])
        assert os.path.getsize(out[name]["stl"]) > 1000


def test_step_round_trip_of_the_assemblies(drive, tmp_path):
    out = W.export_assemblies(str(tmp_path))
    asm = W.to_assembly(drive)
    back = N.read_named_step(out["drive"])
    assert list(back) == list(W.BODY_ORDER)
    for k, v in asm.items():
        _same(v, back[k])
    back2 = N.read_named_step(out["with_slipin"])
    assert list(back2) == list(W.BODY_ORDER) + ["slipin_mount", "wall_mount"]
    for k, v in asm.items():
        _same(v, back2[k])
    for k, ref in (("slipin_mount", W.reference("Slipin_mount_piecev3")), ("wall_mount", W.reference("Wall_Mount_v3"))):
        _same(ref.translate(cq.Vector(*O)), back2[k])
    # the fin is the exported fin untouched (assembly coordinates)
    _same(cq.importers.importStep(W.FIN_STEP).val(), back["fin"])


def test_repo_exports_exist_and_match_the_build(parts, drive):
    files = {"spool_gear60": "spool_gear60", "spacer_near_w3": "spacer_near", "magnet_cap_w3": "magnet_cap"}
    for name, stem in files.items():
        step = os.path.join(W.STEP_DIR, f"winch_gear3_{stem}.step")
        stl = os.path.join(W.STL_DIR, f"winch_gear3_{stem}.stl")
        assert os.path.isfile(step) and os.path.isfile(stl), (step, stl)
        _same(parts[name], N.read_named_step(step)[name])
    asm = os.path.join(W.STEP_DIR, "winch_gear3_drive_asm1021.step")
    assert os.path.isfile(asm)
    back = N.read_named_step(asm)
    assert list(back) == list(W.BODY_ORDER)
    assert os.path.isfile(os.path.join(W.STEP_DIR, "winch_gear3_drive_with_slipin_asm1021.step"))
    for tag in ("front", "side", "top", "iso", "mesh", "section_axis"):
        assert os.path.getsize(os.path.join(W.RENDER_DIR, f"winch_gear3_{tag}.png")) > 10000, tag


def test_assembly_bodies_sit_in_assembly_coordinates(drive):
    """asm1021 = station_1021 + O: the fin of the heat-fin export is at the same place as the drive's fin, the motor front face on it."""
    fin = cq.importers.importStep(W.FIN_STEP).val()
    asm = W.to_assembly(drive)
    assert abs(asm["fin"].BoundingBox().ymin - fin.BoundingBox().ymin) < 1e-6
    assert abs(asm["motor_front_cap"].BoundingBox().ymax - P.NEMA17T_PILOT_H - fin.BoundingBox().ymin) < 1e-6
    assert abs((asm["spool_gear60"].BoundingBox().zmin + asm["spool_gear60"].BoundingBox().zmax) / 2 - (O[2] - 37.56 + RES[2])) < 0.5
