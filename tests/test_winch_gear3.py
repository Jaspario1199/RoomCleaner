"""
Acceptance checks for the winch 3:1 spur drive train (cad/parts/winch_gear3.py, parameters WG3_*, spec cad/WINCH_GEAR3_SPEC.md, revision C: 18T/54T, printed PETG pinion, D41/D42).

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


def _motor_hole_radius(shape):
    """Radius of the smallest cylindrical hole wall around the motor axis (axis along y, within 0.5 mm of x = 0, z = 2.64) with a radius above the pinion hub: the bore the
    pinion hub passes through (the fin's 7/8 in hole, the slide-in tab's motor hole)."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    found = []
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() != GeomAbs_Cylinder:
            continue
        ax = a.Cylinder().Axis()
        loc, d = ax.Location(), ax.Direction()
        if abs(abs(d.Y()) - 1.0) < 1e-9 and math.hypot(loc.X() - RES[0], loc.Z() - (2.64 + RES[2])) < 0.5 and a.Cylinder().Radius() > 7.5:
            found.append(a.Cylinder().Radius())
    assert found, "no motor hole in the shape"
    return min(found)


def _station(design_xyz):
    return tuple(c + r for c, r in zip(design_xyz, RES))


# ---------------------------------------------------------------------------------------------------------------------
# parameters: the spec numbers
# ---------------------------------------------------------------------------------------------------------------------
def test_parameters_are_the_spec_values():
    assert (P.WG3_MODULE, P.WG3_PRESSURE_ANGLE_DEG, P.WG3_Z_PINION, P.WG3_Z_GEAR) == (1.0, 20.0, 18, 54)
    assert P.WG3_RATIO == 3.0
    assert abs(P.WG3_CD_NOMINAL - 36.0) < 1e-12 and abs(P.WG3_CD - 36.30) < 1e-12 and P.WG3_CD_ALLOW == 0.30           # revision C: printed against printed
    assert P.WG3_GEAR_TOOTH_THIN == 0.10 and P.WG3_PINION_TOOTH_THIN == 0.10 and P.WG3_FACE == 10.0
    assert abs(P.WG3_SPOOL_XZ[1] - (2.64 - 36.30)) < 1e-12 and abs(P.WG3_SPOOL_XZ[1] + 33.66) < 1e-12 and P.WG3_SPOOL_XZ[0] == 0.0
    assert abs(P.WG3_Y_SHAFT_END - 20.825) < 1e-9 and abs(P.WG3_Y_TEETH0 - 10.825) < 1e-9
    # revision C pinion: hub from 0.5 mm past the pilot boss face (y -3.175 + 2.0 = -1.175) to the teeth, bore = Jasper's printed D-bore, M3 insert pocket + Ø3.0 hole at the hub middle
    assert abs(P.WG3_Y_BOSS_FACE + 1.175) < 1e-9 and P.WG3_PINION_BOSS_CLEAR == 0.5
    assert abs(P.WG3_Y_PINION_HUB0 + 0.675) < 1e-9 and abs(P.WG3_PINION_HUB_L - 11.5) < 1e-9 and P.WG3_PINION_HUB_D == 14.0
    assert (P.WG3_PINION_BORE_D, P.WG3_PINION_BORE_FLAT_X) == (P.ENC1021_BORE_D, P.ENC1021_BORE_FLAT_X) == (5.30, 2.15)
    assert (P.WG3_PINION_INSERT_D, P.WG3_PINION_INSERT_DEPTH, P.WG3_PINION_SETSCREW_D) == (4.0, 4.5, 3.0)
    assert abs(P.WG3_Y_PINION_SETSCREW - (P.WG3_Y_TAB1 + P.WG3_Y_TEETH0) / 2.0) < 1e-12 and abs(P.WG3_Y_PINION_SETSCREW - 7.9) < 0.02      # 7.9125: middle of the exposed hub
    assert P.WG3_PINION_MIN_CLEAR_MOTOR == 0.4
    assert (P.WG3_WINDOW_N, P.WG3_WINDOW_D, P.WG3_WINDOW_R) == (6, 10.0, 17.5)
    assert (P.WG3_MIN_CLEAR, P.WG3_MIN_CLEAR_HUB) == (1.5, 1.0)                                # gear to motor and fin >= 1.5; gear tip to pinion hub >= 1.0 (spec section 5)
    assert (P.WG3_DRUM_D, P.WG3_FLANGE_D, P.WG3_FLANGE_T, P.WG3_HUB_D, P.WG3_BORE_D) == (15.0, 36.0, 3.0, 12.0, 7.00)
    assert abs(P.WG3_Y_DRUM1 - 36.825) < 1e-9 and abs(P.WG3_Y_FLANGE1 - 39.825) < 1e-9 and P.WG3_Y_SPOOL_END == 44.0
    assert (P.WG3_LAND_D, P.WG3_LAND_PROUD, P.WG3_BED_CHAMFER) == (9.0, 0.3, 0.3)
    assert (P.WG3_TIEOFF_D, P.WG3_TIEOFF_OFFSET) == (1.4, 5.25) and abs(P.WG3_TIEOFF_Y - 28.825) < 1e-9
    assert (P.WG3_SPACER_OD, P.WG3_SPACER_BORE_D, P.WG3_SPACER_Y0) == (10.0, 7.10, 5.0) and abs(P.WG3_SPACER_Y1 - 10.825) < 1e-9
    assert (P.WG3_SHAFT_D, P.WG3_SHAFT_Y0, P.WG3_SHAFT_L) == (7.0, -3.0, 55.0)
    assert (P.WG3_CAP_D, P.WG3_CAP_Y0, P.WG3_CAP_BORE_DEPTH, P.WG3_CAP_WEB) == (12.0, 49.3, 3.0, 0.75)
    assert abs(P.WG3_Y_MAGNET0 - 53.05) < 1e-9 and abs(P.WG3_CAP_Y1 - 55.55) < 1e-9 and abs(P.WG3_CAP_POCKET_D - 4.3) < 1e-9
    assert (P.WG3_MAGNET_D, P.WG3_MAGNET_T) == (4.0, 2.5)            # D43: the measured Ø4.0 magnet
    assert abs(P.WG3_CHIP_FACE_Y - 57.05) < 1e-9 and abs(P.WG3_PCB_Y0 - 58.5) < 1e-9 and abs(P.WG3_PCB_Y1 - 60.1) < 1e-9


# ---------------------------------------------------------------------------------------------------------------------
# the printable parts
# ---------------------------------------------------------------------------------------------------------------------
def test_printable_parts_are_single_valid_solids(parts):
    assert set(parts) == {"pinion", "spool_gear54", "spacer_near_w3", "magnet_cap_w3"}
    for name, s in parts.items():
        assert s.isValid() and len(s.Solids()) == 1 and s.Volume() > 0, name


def test_spool_extent_and_print_frame(parts):
    """Print frame: axis +z, near gear face (design y 10.825) on the bed z = 0; the part runs 33.175 high (y 10.825 .. 44.0)."""
    x0, x1, y0, y1, z0, z1 = _bb(parts["spool_gear54"])
    assert abs(z0) < TOL and abs(z1 - (44.0 - 10.825)) < TOL
    assert 27.9 < x1 < 28.001 and -28.001 < x0 < -27.9 and 27.9 < y1 < 28.001 and -28.001 < y0 < -27.9   # tip circle Ø56 (a tooth sits on the x axis, a space on the y axis)
    bed = _plane_faces(parts["spool_gear54"], "z", 0.0)
    assert len(bed) == 1 and bed[0].Area() > 1000.0                                           # a flat bed face: the gear's near face
    far = _plane_faces(parts["spool_gear54"], "z", 44.0 - 10.825)
    assert len(far) == 1 and abs(far[0].Area() - math.pi * 4.5 ** 2 + math.pi * 3.5 ** 2) < 0.1   # the far Ø9 land minus the Ø7 bore


def test_gear_teeth_fifty_four_tip_and_root_diameters(parts):
    s = parts["spool_gear54"]
    tips = _cyl_faces(s, 28.0, "z")
    roots = _cyl_faces(s, 25.75, "z")
    assert len(tips) == 54 and len(roots) == 54                                               # one tip face and one root face per tooth: 54T, tip Ø56, root Ø51.5
    assert all(abs(t[0][0]) < TOL and abs(t[0][1]) < TOL for t in tips)                       # all on the axis
    # teeth span the gear face (the tip faces start 0.3 above the bed face: the chamfer)
    zs = sorted(t[1].zmin for t in tips)
    assert abs(zs[0] - 0.3) < 0.01 and abs(max(t[1].zmax for t in tips) - 10.0) < 0.01


def test_bed_face_tooth_chamfer(parts):
    """0.3 x 45 deg on the tooth edges of the bed face: the outline on the bed face reaches only R 27.7, and the flat bed face is smaller than the section 0.3 up."""
    s = parts["spool_gear54"]
    bed = _plane_faces(s, "z", 0.0)[0]
    r_bed = max(math.hypot(v.X, v.Y) for v in bed.Vertices())
    assert 27.6 < r_bed < 27.71, r_bed
    top = s.intersect(cq.Solid.makeBox(100, 100, 0.01, cq.Vector(-50, -50, 0.30)))
    slab = max(top.Solids(), key=lambda x: x.Volume())
    assert slab.BoundingBox().xlen > s.intersect(cq.Solid.makeBox(100, 100, 0.01, cq.Vector(-50, -50, 0.0))).BoundingBox().xlen + 0.2


def test_lightening_windows(parts):
    s = parts["spool_gear54"]
    wins = [w for w in _cyl_faces(s, 5.0, "z")]
    assert len(wins) == 6                                                                      # six Ø10 windows
    for loc, bb in wins:
        assert abs(math.hypot(loc[0], loc[1]) - 17.5) < TOL                                   # on R 17.5
        assert bb.zmin < 0.01 and abs(bb.zmax - 10.0) < 0.01                                  # through the 10 mm gear face
    rim = 25.75 - (17.5 + 5.0)
    web = (17.5 - 5.0) - 7.5
    assert abs(rim - 3.25) < 1e-9 and rim >= P.WG3_RIM_MIN                                    # rim below the root >= 3 mm
    assert web >= P.WG3_WEB_MIN                                                               # web to the drum core >= 2 mm
    assert (17.5 - 5.0) - 10.0 == pytest.approx(2.5)                                          # inner edge R12.5: 2.5 outside the 10 mm full-spool line radius


def test_drum_flange_hub_bore_and_lands(parts):
    s = parts["spool_gear54"]
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
    s = parts["spool_gear54"]
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
    assert pocket and abs(min(c[1].zmin for c in pocket) - 3.75) < TOL and abs(max(c[1].zmax for c in pocket) - 6.25) < TOL   # Ø4.3 pocket 2.5 deep (D43)
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
    """The only drive pair that may overlap: 3 crush ribs bite 0.12 mm into the Ø4 magnet (ENC1021_V2 rule)."""
    v = drive["magnet_cap"].intersect(drive["magnet"]).Volume()
    g = W.magnet_rib_geometry()
    crush = P.ENC1021_V2_MAGNET_RIB_CRUSH
    r_mag = P.WG3_MAGNET_D / 2.0
    w_at_magnet = g["tip_w"] + (g["base_w"] - g["tip_w"]) * crush / (g["r_wall"] + W.RIB_INSET - g["r_tip"])
    est = g["n"] * crush * (g["tip_w"] + w_at_magnet) / 2.0 * P.WG3_CAP_POCKET_DEPTH         # no lead-in: an upper bound
    assert 0.6 * est < v <= 1.02 * est, (v, est)
    assert r_mag - g["r_tip"] == pytest.approx(crush)


# ---------------------------------------------------------------------------------------------------------------------
# the printed pinion (revision C / D42).  Print frame: axis +z, teeth end (design y 20.825) on the bed z = 0, hub up to z = 21.5 (design y -0.675).
# print z = 20.825 - design y.  In the drive (station frame, residual included) the same solid is checked in design y and station z.
# ---------------------------------------------------------------------------------------------------------------------
PIN_Z_TEETH_TOP = 20.825 - 10.825                                # print z of the teeth/hub joint (design y 10.825)
PIN_Z_TOP = 20.825 + 0.675                                       # print z of the hub end (design y -0.675)


def _tooth_thickness_at(shape, radius, z, step_deg=0.5):
    """Circumferential thickness (mm) of the first full tooth found on the circle of this radius at height z of a gear whose axis is the z axis: scans the
    circle, bisects the two flank crossings."""
    inside = _inside(shape)
    at = lambda a: inside((radius * math.cos(a), radius * math.sin(a), z))
    n = int(360 / step_deg)
    ang = [math.radians(i * step_deg) for i in range(n + 1)]
    for i in range(n):
        if not at(ang[i]) and at(ang[i + 1]):                       # rising edge: tooth starts between ang[i] and ang[i + 1]
            lo, hi = ang[i], ang[i + 1]
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                lo, hi = (lo, mid) if at(mid) else (mid, hi)
            start = hi
            j = i + 1
            while at(ang[j]):
                j += 1
            lo, hi = ang[j - 1], ang[j]
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                lo, hi = (mid, hi) if at(mid) else (lo, mid)
            return radius * (lo - start)
    raise AssertionError("no tooth found")


def test_pinion_is_printable(parts):
    p = parts["pinion"]
    assert p.isValid() and len(p.Solids()) == 1 and p.Volume() > 0
    x0, x1, y0, y1, z0, z1 = _bb(p)
    assert abs(z0) < TOL and abs(z1 - PIN_Z_TOP) < TOL                                        # bed face at z = 0, 21.5 tall
    assert 9.85 < x1 < 10.001 and -10.001 < y0 < -9.85 and -9.95 < x0 < -9.85 and 9.85 < y1 < 10.001   # tip circle Ø20 (a tooth tip near the x or y axis)
    bed = _plane_faces(p, "z", 0.0)
    assert len(bed) == 1 and 150.0 < bed[0].Area() < 200.0                                    # the teeth end face is the one flat bed face (Ø19.4 outline less the D-bore)
    top = _plane_faces(p, "z", PIN_Z_TOP)
    segment = 2.65 ** 2 * math.acos(2.15 / 2.65) - 2.15 * math.sqrt(2.65 ** 2 - 2.15 ** 2)    # circular segment beyond the flat: not part of the bore
    d_bore_area = math.pi * 2.65 ** 2 - segment
    assert len(top) == 1 and abs(top[0].Area() - (math.pi * 7.0 ** 2 - d_bore_area)) < 0.05   # hub end face: Ø14 disc less the D-bore
    assert abs(W.mass_g("pinion", p) - 4.7) < 0.1                                             # about 4.7 g PETG (no insert, no set screw)


def test_pinion_teeth_eighteen_and_thinned(parts):
    p = parts["pinion"]
    tips, roots = _cyl_faces(p, 10.0, "z"), _cyl_faces(p, 7.75, "z")
    assert len(tips) == 18 and len(roots) == 18                                               # 18T, tip Ø20, root Ø15.5
    assert all(abs(t[0][0]) < TOL and abs(t[0][1]) < TOL for t in tips)
    assert abs(min(t[1].zmin for t in tips) - 0.3) < 0.01 and abs(max(t[1].zmax for t in tips) - PIN_Z_TEETH_TOP) < 0.01   # tip faces from z 0.3 (chamfer) to the hub joint z 10
    # tooth thinning: thickness on the pitch circle R9 = pi m / 2 - thinning = 1.5708 - 0.10 = 1.4708, measured on the solid (and the same on the gear, R27)
    t_pin = _tooth_thickness_at(p, 9.0, 5.0)
    assert abs(t_pin - (math.pi / 2.0 - 0.10)) < 0.01, t_pin
    assert abs(t_pin - (math.pi / 2.0 - P.WG3_PINION_TOOTH_THIN)) < 0.01
    t_gear = _tooth_thickness_at(parts["spool_gear54"], 27.0, 5.0)
    assert abs(t_gear - t_pin) < 0.01, (t_gear, t_pin)                                        # the pinion has the gear's thinning


def test_pinion_bed_chamfer(parts):
    """0.3 x 45 deg on the tooth edges of the teeth-end (bed) face: the outline on the bed face reaches only R 9.7 (tip 10.0 - 0.3), and the section 0.3 above the bed is
    wider than the bed outline (the full tip circle is back)."""
    p = parts["pinion"]
    bed = _plane_faces(p, "z", 0.0)[0]
    r_bed = max(math.hypot(v.X, v.Y) for v in bed.Vertices())
    assert 9.6 < r_bed < 9.71, r_bed
    slab = lambda z: max(p.intersect(cq.Solid.makeBox(100, 100, 0.01, cq.Vector(-50, -50, z))).Solids(), key=lambda x: x.Volume()).BoundingBox()
    at_bed, above = slab(0.0), slab(0.30)
    assert above.xlen > at_bed.xlen + 0.2 and above.ylen > at_bed.ylen + 0.2


def test_pinion_hub_d_bore_and_set_screw(drive):
    """Station frame, residual included.  The bore is the printed D-bore Ø5.30 with the flat 2.15 from the axis on the +z side, through the whole pinion; the radial
    Ø4.0 x 4.5 insert pocket and the Ø3.0 hole run from the hub surface to the bore toward +z at y 7.9125."""
    p = drive["pinion"]
    ax, az = RES[0], 2.64 + RES[2]
    y = lambda dy: dy + RES[1]
    hub = _cyl_faces(p, 7.0, "y")
    assert len(hub) == 1 and abs(hub[0][1].ymin - y(-0.675)) < TOL and abs(hub[0][1].ymax - y(10.825)) < TOL                # Ø14 hub y -0.675 .. 10.825
    tips = _cyl_faces(p, 10.0, "y")
    assert abs(min(t[1].ymin for t in tips) - y(10.825)) < TOL and abs(max(t[1].ymax for t in tips) - y(20.825 - 0.3)) < TOL      # tip faces end where the chamfer starts (y 20.525)
    assert abs(p.BoundingBox().ymin - y(-0.675)) < TOL and abs(p.BoundingBox().ymax - y(20.825)) < TOL                      # the pinion spans y -0.675 .. 20.825
    bore = _cyl_faces(p, 2.65, "y")
    assert bore and all(abs(b[0][0] - ax) < TOL and abs(b[0][2] - az) < TOL for b in bore)                                  # Ø5.30 round part on the motor axis
    assert abs(min(b[1].ymin for b in bore) - y(-0.675)) < TOL and abs(max(b[1].ymax for b in bore) - y(20.825)) < TOL       # through
    inside = _inside(p)
    y_open = y(2.0)                                                                           # a plane of the hub away from the set screw
    assert not inside((ax, y_open, az)) and not inside((ax, y_open, az - 2.6)) and not inside((ax + 2.6, y_open, az))        # round part: bore void to R 2.65
    assert not inside((ax, y_open, az + 2.1)) and inside((ax, y_open, az + 2.2)) and inside((ax, y_open, az + 2.4))        # flat on the +z side: void to 2.15, material beyond
    assert not inside((ax, y_open, az - 2.6)) and inside((ax, y_open, az - 2.7))                                           # the -z side is the round bore (R 2.65), not a flat
    flat = _plane_faces(p, "z", az + 2.15)
    assert flat, "no D-flat face at 2.15 from the axis on the +z side"
    half_chord = math.sqrt(2.65 ** 2 - 2.15 ** 2)
    fb = max(flat, key=lambda f: f.Area()).BoundingBox()
    assert abs(fb.xmin - (ax - half_chord)) < 0.01 and abs(fb.xmax - (ax + half_chord)) < 0.01 and abs(fb.ymin - y(-0.675)) < TOL and abs(fb.ymax - y(20.825)) < TOL
    # the pinion fits the motor shaft with 0.15 mm (round part and flat), neither touching nor overlapping
    d_shaft = p.distance(drive["motor_shaft"])
    assert abs(d_shaft - 0.15) < 0.01, d_shaft
    # insert pocket Ø4.0 (R 2.0) and set-screw clearance hole Ø3.0 (R 1.5): axes along z at x = axis, y = 7.9125, opening toward +z
    pocket, hole = _cyl_faces(p, 2.0, "z"), _cyl_faces(p, 1.5, "z")
    assert len(pocket) == 1 and len(hole) == 1
    for (loc, _) in (pocket[0], hole[0]):
        assert abs(loc[0] - ax) < TOL and abs(loc[1] - y(7.9125)) < TOL, loc                  # at y 7.9125 (spec 7.9), on the x of the axis
    pb, hb = pocket[0][1], hole[0][1]
    assert abs(pb.zmin - (az + 2.5)) < TOL and abs(pb.zmax - (az + 7.0)) < TOL               # pocket bottom 4.5 under the hub surface (R 7.0 - 4.5 = 2.5), open at the surface
    assert abs(hb.zmin - (az + 2.15)) < TOL and abs(hb.zmax - (az + 2.5)) < TOL               # hole from the pocket bottom to the bore flat
    assert abs((pb.ymin + pb.ymax) / 2 - y(7.9125)) < TOL and abs((pb.ymax - pb.ymin) - 4.0) < 0.01 and abs((hb.ymax - hb.ymin) - 3.0) < 0.01
    ys = y(7.9125)
    assert not inside((ax, ys, az + 3.0)) and not inside((ax, ys, az + 6.9)) and not inside((ax, ys, az + 2.3))              # pocket and hole are void on the +z side
    assert not inside((ax, ys, az + 7.2))                                                     # outside the hub
    assert inside((ax, ys, az - 4.5)) and inside((ax, ys, az - 6.9))                          # closed on the -z side: no hole there
    assert inside((ax + 1.7, ys, az + 2.3))                                                   # 0.35 mm floor ring around the Ø3.0 hole (hole R1.5 < 1.7 < pocket R2.0)
    assert inside((ax + 2.1, ys, az + 5.0)) and not inside((ax + 1.9, ys, az + 5.0))          # pocket wall at R 2.0
    # the pocket stays in the exposed hub (tab face y 5.0 .. teeth y 10.825) with at least 0.5 mm each side, and does not break into the bore (floor 0.35 above the flat)
    assert pb.ymin - y(5.0) > 0.5 and y(10.825) - pb.ymax > 0.5
    assert (az + 2.5) - (az + 2.15) == pytest.approx(0.35)


# ---------------------------------------------------------------------------------------------------------------------
# the drive assembly
# ---------------------------------------------------------------------------------------------------------------------
def test_body_list_and_solids(drive):
    expected = ["motor_front_cap", "motor_stator", "motor_winding", "motor_rear_cap", "motor_shaft", "motor_connector", "fin", "pinion", "spool_gear54", "shaft",
                "bearing_near", "bearing_far", "spacer_near", "magnet_cap", "magnet", "as5600_chip", "as5600_board"]
    assert list(drive) == expected
    for k, s in drive.items():
        assert s.isValid() and len(s.Solids()) == 1 and s.Volume() > 0, k


def test_centre_distance_and_ratio(drive):
    pin = W.bore_axis_xz(drive["pinion"], 2.65)                                               # Ø5.30 round part of the pinion's D-bore
    spo = W.bore_axis_xz(drive["spool_gear54"], 3.5)
    cd = math.hypot(pin[0] - spo[0], pin[1] - spo[1])
    assert abs(cd - 36.30) < 1e-4, cd                                                         # built centre distance (revision C)
    assert abs(cd - 36.0 - 0.30) < 1e-4
    assert abs(pin[0] - spo[0]) < 1e-9                                                       # the spool is straight below the motor
    assert abs((spo[1] - RES[2]) + 33.66) < 1e-4 and abs((spo[0] - RES[0])) < 1e-4            # spool axis x 0, z -33.66
    assert abs((pin[1] - RES[2]) - 2.64) < 1e-4                                               # motor axis z 2.64
    n_gear = len(_cyl_faces(drive["spool_gear54"], 28.0, "y"))
    n_pinion = len(_cyl_faces(drive["pinion"], 10.0, "y"))
    assert (n_gear, n_pinion) == (54, 18) and n_gear / n_pinion == pytest.approx(3.0)       # ratio 3.00 from the measured tooth counts


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
    assert abs((bb.xmin + bb.xmax) / 2 - RES[0]) < 2e-3 and abs((bb.zmin + bb.zmax) / 2 - (-33.66 + RES[2])) < 2e-3          # centred on the spool axis
    cb = drive["as5600_chip"].BoundingBox()
    assert abs(cb.xlen - 6.0) < 2e-3 and abs(cb.zlen - 4.0) < 2e-3
    sc = drive["magnet_cap"]
    inside = _inside(sc)
    sa = _station((0.0, 0.0, -33.66))
    assert not inside((sa[0], 52.15 + RES[1], sa[2]))                                         # the shaft end (52.0) is 0.3 mm short of the bore floor (52.3)
    assert abs(drive["shaft"].distance(drive["magnet_cap"])) < 1e-6                           # shaft in the cap bore: touching, not overlapping


def test_no_overlap_between_any_two_drive_bodies(drive):
    ov = W.drive_overlaps(drive)
    allowed = {("magnet_cap", "magnet")}                                                      # the designed crush ribs (previous test bounds it)
    bad = {k: v for k, v in ov.items() if v > LIMIT and k not in allowed}
    assert not bad, bad
    assert ("magnet_cap", "magnet") in ov and ov[("magnet_cap", "magnet")] < 1.0


def test_mesh_has_no_overlap_through_a_tooth_pitch(drive):
    """Pinion and gear at the reference pose and rotated through a pinion pitch (20 deg: 6.67 deg of the gear): no overlap, positive flank clearance."""
    pin, gear = drive["pinion"], drive["spool_gear54"]
    pa = W.bore_axis_xz(pin, 2.65)
    ga = W.bore_axis_xz(gear, 3.5)
    p_origin, g_origin = cq.Vector(pa[0], 0, pa[1]), cq.Vector(ga[0], 0, ga[1])
    y_axis = cq.Vector(0, 1, 0)
    for th in (0.0, 5.0, 10.0, 15.0, 20.0):
        pr = pin.rotate(p_origin, p_origin + y_axis, th)
        gr = gear.rotate(g_origin, g_origin + y_axis, -th / 3.0)
        assert pr.intersect(gr).Volume() <= LIMIT, th
        assert pr.distance(gr) > 0.1, (th, pr.distance(gr))                                   # revision C measured minimum flank gap 0.20 (revision B 0.117)


def test_mesh_sweep_in_one_degree_steps_has_no_overlap_and_a_constant_flank_gap(drive):
    """21 poses over one pinion pitch (0 to 20 deg in 1 deg steps, gear -1/3) on the tooth-face slabs: zero overlap, flank gap constant at 0.1997 (revision B 0.1168)."""
    sweep = W.mesh_sweep(drive)
    assert len(sweep) == 21
    assert max(v for _, v, _ in sweep) <= LIMIT
    gaps = [d for _, _, d in sweep]
    assert min(gaps) > 0.15 and max(gaps) - min(gaps) < 0.01, (min(gaps), max(gaps))        # a conjugate pair: the same gap at every pose


def test_gear_space_faces_the_pinion_tooth_at_the_mesh_point(drive):
    """Phasing rule (spec section 2): at the reference pose a gear tooth SPACE is centred on the line of centres toward the pinion and a pinion TOOTH stands in it."""
    gear, pin = drive["spool_gear54"], drive["pinion"]
    ga, pa = W.bore_axis_xz(gear, 3.5), W.bore_axis_xz(pin, 2.65)
    y_mid = _station((0, 15.825, 0))[1]
    in_gear, in_pin = _inside(gear), _inside(pin)
    r_gear_pitch, r_pin_pitch = 27.0, 9.0                                                     # m x z / 2 of the 54T and the 18T
    assert not in_gear((ga[0], y_mid, ga[1] + r_gear_pitch))                                  # a space of the gear on the line of centres
    assert in_pin((pa[0], y_mid, pa[1] - r_pin_pitch))                                        # a tooth of the pinion on the same line
    half_pitch = math.pi / 54                                                                 # the gear's teeth are centred half a pitch either side of the space
    for sgn in (-1, 1):
        a = math.pi / 2 + sgn * half_pitch
        assert in_gear((ga[0] + r_gear_pitch * math.cos(a), y_mid, ga[1] + r_gear_pitch * math.sin(a)))


def test_backlash_measured_on_the_solids(drive):
    """Revision C: both gears printed, CD 36.30 (+0.30) and 0.10 thinning on each gear: transverse backlash at the pinion pitch circle =
    2 x 0.30 x tan 20 + 0.10 + 0.10 = 0.418 mm.  Measured: the gear is held, the pinion is turned each way until the flanks touch (distance < 1e-3 mm)."""
    bl = W.backlash_measured(drive)
    expect = 2 * 0.30 * math.tan(math.radians(20.0)) + 0.10 + 0.10
    assert abs(bl["formula_mm"] - expect) < 1e-9
    assert abs(bl["backlash_mm"] - expect) < 0.015, (bl, expect)
    assert abs(bl["plus_deg"] + bl["minus_deg"]) < 0.02                                       # symmetric: the pinion tooth sits centred in the gear space at the reference pose


def test_clearances(drive):
    gear, pin = drive["spool_gear54"], drive["pinion"]
    assert gear.distance(W.pinion_hub_solid()) >= P.WG3_MIN_CLEAR_HUB                         # gear tip to the pinion hub >= 1.0 (spec section 5); radial 36.30 - 28.0 - 7.0 = 1.3 on the tooth line
    for k in ("motor_front_cap", "motor_stator", "motor_winding", "motor_rear_cap", "motor_shaft", "motor_connector", "fin"):
        assert gear.distance(drive[k]) >= P.WG3_MIN_CLEAR, k
    # the printed pinion: >= 0.4 mm to every motor body the shaft does not carry (the pilot boss face is axial: 0.5 built), the shaft it sits on is the 0.15 bore fit
    boss_face = drive["motor_front_cap"].BoundingBox().ymax
    assert pin.BoundingBox().ymin - boss_face == pytest.approx(0.5, abs=2e-3)                 # hub end 0.5 mm past the pilot boss face
    for k in ("motor_front_cap", "motor_stator", "motor_winding", "motor_rear_cap", "motor_connector"):
        assert pin.distance(drive[k]) >= P.WG3_PINION_MIN_CLEAR_MOTOR, k
    assert pin.distance(drive["motor_front_cap"]) == pytest.approx(0.5, abs=2e-3)
    # >= 1.5 mm radial to the fin's 7/8 in hole and to Jasper's slide-in tab hole (R 11.25 / R 11.2 around the motor axis, hub R 7.0)
    assert pin.distance(drive["fin"]) >= P.WG3_MIN_CLEAR
    slipin = W.reference("Slipin_mount_piecev3")
    assert pin.distance(slipin) >= P.WG3_MIN_CLEAR
    r_tab_hole, r_fin_hole = _motor_hole_radius(slipin), _motor_hole_radius(drive["fin"])      # measured on the reference solids
    assert r_tab_hole == pytest.approx(11.2, abs=0.01) and r_fin_hole == pytest.approx(11.25, abs=0.01)
    assert r_tab_hole - 7.0 >= P.WG3_MIN_CLEAR and r_fin_hole - 7.0 >= P.WG3_MIN_CLEAR        # hub R 7.0: 4.2 / 4.25 mm radial


def test_axial_stack_contacts(drive):
    """Faces that must touch do (distance 0), and the 0.3 mm lands keep the Ø12 / Ø10 bodies off the bearing faces."""
    d = drive
    assert d["spacer_near"].distance(d["bearing_near"]) < 1e-6                                # spacer land on the near inner race (y 5.0)
    assert d["spacer_near"].distance(d["spool_gear54"]) < 1e-6                                # spacer land on the gear's near face (y 10.825)
    assert d["spool_gear54"].distance(d["bearing_far"]) < 1e-6                                # far land on the far inner race (y 44.0)
    assert d["spool_gear54"].distance(d["spacer_near"]) < 1e-6
    assert d["spool_gear54"].distance(d["bearing_near"]) > 5.0                                # nothing else of the spool near the near bearing
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
    assert by[("spool_gear54", "Slipin_mount_piecev3")]["volume"] > 1000.0                    # the gear cuts through the deck block and the back plate (the drum nicks the far cheek)
    assert ("spacer_near", "Slipin_mount_piecev3") in by                                      # the spacer against the near cheek
    assert ("spool_gear54", "Wall_Mount_v3") in by                                            # teeth against the wall mount's lower part
    # revision B (spool axis 4 mm higher; revision C 0.1 mm lower again): the shaft no longer touches the lug cheeks, the drum no longer reaches the deck; nothing else is hit.
    # The printed pinion's hub passes through the tab's R 11.2 motor hole without touching the slide-in (revision C)
    assert set(by) == {("spool_gear54", "Slipin_mount_piecev3"), ("spacer_near", "Slipin_mount_piecev3"), ("spool_gear54", "Wall_Mount_v3")}, sorted(by)
    untouched = {"pinion", "motor_front_cap", "motor_stator", "motor_winding", "motor_rear_cap", "motor_shaft", "motor_connector", "bearing_near", "bearing_far",
                 "magnet_cap", "magnet", "as5600_chip", "as5600_board"}
    assert not [k for k in by if k[0] in untouched], [k for k in by if k[0] in untouched]     # pinion, motor, bearings and the encoder stack do not touch either
    assert 2300.0 < by[("spool_gear54", "Slipin_mount_piecev3")]["volume"] < 2600.0              # revision C 2463 (revision B 2452)


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
    files = {"pinion": "pinion18", "spool_gear54": "spool_gear54", "spacer_near_w3": "spacer_near", "magnet_cap_w3": "magnet_cap"}
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
    assert abs((asm["spool_gear54"].BoundingBox().zmin + asm["spool_gear54"].BoundingBox().zmax) / 2 - (O[2] - 33.66 + RES[2])) < 0.5


# ---------------------------------------------------------------------------------------------------------------------
# the gears as their own STEP files (export_gears): the pinion alone, and the pinion + spool_gear54 pair in assembly coordinates
# ---------------------------------------------------------------------------------------------------------------------
GEAR_REL_TOL = 1.0e-6                                            # volume agreement between files written by the same exporter (relative)
GEAR_BB_TOL = 1.0e-6                                             # mm, bounding-box agreement between those files
GEAR_DIM_TOL = 0.01                                              # mm, measured tip diameter / bore diameter
PINION_STEP = os.path.join(W.STEP_DIR, "winch_gear3_pinion18.step")
GEARS_STEP = os.path.join(W.STEP_DIR, "winch_gear3_gears_asm1021.step")
DRIVE_STEP = os.path.join(W.STEP_DIR, "winch_gear3_drive_asm1021.step")


@pytest.fixture(scope="module")
def pinion_file():
    return N.read_named_step(PINION_STEP)


@pytest.fixture(scope="module")
def gears_file():
    return N.read_named_step(GEARS_STEP)


@pytest.fixture(scope="module")
def drive_file():
    return N.read_named_step(DRIVE_STEP)


def _bb_close(a: cq.Shape, b: cq.Shape, tol: float = GEAR_BB_TOL):
    ba, bb = a.BoundingBox(), b.BoundingBox()
    for u, v in ((ba.xmin, bb.xmin), (ba.xmax, bb.xmax), (ba.ymin, bb.ymin), (ba.ymax, bb.ymax), (ba.zmin, bb.zmin), (ba.zmax, bb.zmax)):
        assert abs(u - v) <= tol, (u, v)


def test_gear_step_files_reimport_with_names_and_one_valid_solid_each(pinion_file, gears_file):
    assert os.path.isfile(PINION_STEP) and os.path.isfile(GEARS_STEP)
    assert list(pinion_file) == ["pinion"]
    assert list(gears_file) == ["pinion", "spool_gear54"]
    assert sum(len(s.Solids()) for s in pinion_file.values()) == 1
    assert sum(len(s.Solids()) for s in gears_file.values()) == 2
    for body in (*pinion_file.values(), *gears_file.values()):
        assert body.isValid() and len(body.Solids()) == 1 and body.Solids()[0].isValid() and body.Volume() > 0


def test_gears_assembly_bodies_equal_those_of_the_drive_assembly(gears_file, drive_file, drive):
    for k in ("pinion", "spool_gear54"):
        ref, got = drive_file[k], gears_file[k]
        assert abs(got.Volume() - ref.Volume()) <= GEAR_REL_TOL * ref.Volume(), (k, got.Volume(), ref.Volume())
        _bb_close(got, ref)
        _same(W.to_assembly(drive)[k], got)                                                   # and both are what the builder makes now


def test_standalone_pinion_is_the_printable_part_in_the_print_frame(pinion_file, gears_file, drive, parts):
    """winch_gear3_pinion18.step is the printable part (revision C): print frame, axis z, teeth end on the bed z = 0, hub up to z = 21.5; one pinion file only."""
    pin = pinion_file["pinion"]
    ref = gears_file["pinion"]
    assert abs(pin.Volume() - ref.Volume()) <= GEAR_REL_TOL * ref.Volume(), (pin.Volume(), ref.Volume())
    _same(parts["pinion"], pin)                                                               # the file is what the builder makes now
    b = pin.BoundingBox()
    assert abs(b.zmin) < TOL and abs(b.zmax - (P.WG3_Y_TEETH1 - P.WG3_Y_PINION_HUB0)) < TOL and abs(b.zmax - 21.5) < TOL
    # tip and bore diameters measured on the cylindrical faces whose axis is the z axis through the origin
    radii = sorted({round(r, 6) for r in _z_axis_cylinder_radii(pin)})
    assert abs(2.0 * radii[-1] - 20.0) <= GEAR_DIM_TOL, radii
    assert abs(2.0 * radii[0] - 5.30) <= GEAR_DIM_TOL, radii                                  # the printed D-bore, Ø5.30
    assert len(_cyl_faces(pin, radii[-1], "z")) == 18 and len(_cyl_faces(pin, radii[0], "z")) >= 1            # 18 tip lands, a Ø5.30 bore
    assert 7.0 in radii                                                                       # Ø14 hub
    # the pinion in the assembly is this solid turned back (rotate 180 deg about x, shift by -20.825) and placed on the motor axis
    back = pin.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 180.0).translate(cq.Vector(0, 0, P.WG3_Y_TEETH1))
    bb = back.BoundingBox()
    assert abs(bb.zmin - P.WG3_Y_PINION_HUB0) < TOL and abs(bb.zmax - P.WG3_Y_TEETH1) < TOL
    only = [f for f in os.listdir(W.STEP_DIR) if f.startswith("winch_gear3_pinion")]
    assert only == ["winch_gear3_pinion18.step"], only                                        # no second (axis-z purchased) pinion export


def _z_axis_cylinder_radii(shape):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() != GeomAbs_Cylinder:
            continue
        ax = a.Cylinder().Axis()
        loc, d = ax.Location(), ax.Direction()
        if abs(abs(d.Z()) - 1.0) < 1e-9 and math.hypot(loc.X(), loc.Y()) < 1e-4:
            yield a.Cylinder().Radius()
