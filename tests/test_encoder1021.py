"""
Acceptance checks for the encoder 1021 parts (spec: cad/ENCODER_1021_SPEC.md; part module: cad/parts/encoder1021.py):

  MAGNET CAP      one valid solid, D-peg vs the spool bore, peg length / end level, magnet face level, crush ribs, notch
  ENCODER CASING  one valid solid, chip-face plane, board pocket, tabs, hooks, foot in the divot, holes, screw access
  ASSEMBLY        interference / clearance against the station_1021 reference parts, rotating-cap sweep, line path
  PRINT           overhang analysis in the stated print orientation
  EXPORT          STEP round trip, STL check, exports current
  PARAMETERS      one edit in cad/params.py regenerates both parts

Everything is measured on the built B-rep solids / exported files (ray probes, booleans, distances), with the spec numbers as
the expected values.  Reference parts are read-only; they are shifted into the v3 station frame by (0, 0, -2.64), and
(corrected) also by the measured STEP extraction residual of (0.004243, 0.001645, 0.003854) mm so that the contact faces
(foot on the divot floor, cap head on the spool face) coincide exactly; the plain-spec shift is checked as well.
Run with /usr/bin/python3 -m pytest tests/test_encoder1021.py
"""

from __future__ import annotations

import math
import os
import struct
import sys

import pytest

cq = pytest.importorskip("cadquery")

import numpy as np                                               # noqa: E402
from OCP.BRepClass3d import BRepClass3d_SolidClassifier          # noqa: E402
from OCP.TopAbs import TopAbs_IN                                  # noqa: E402
from OCP.gp import gp_Pnt                                         # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                      # noqa: E402
from cad.parts import encoder1021 as E                           # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.isdir(E.REF_DIR), reason="station_1021 reference parts not available")

C0 = E.Cfg()
INTERFERENCE_TOL_MM3 = 1e-3          # a true face contact leaves < 0.001 mm3 of numerical sliver
RECORD_MAGNET_D = 6.0                # magnet Ø of the cap exports made before Jasper measured the magnet (10/22: Ø4.0, ENC1021_MAGNET_D): those files stay as the superseded record
POCKET_D = P.ENC1021_MAGNET_D + P.ENC1021_CAP_POCKET_CLEAR_D     # v1 magnet pocket Ø (4.2 for the Ø4.0 magnet)
POCKET_R = POCKET_D / 2


# ---------------------------------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------------------------------
def _solid(sh):
    s = sh.Solids()
    return s[0] if len(s) == 1 else sh


class Probe:
    """Point-in-solid classifier with ray search for the first surface crossing."""

    def __init__(self, shape):
        self.c = BRepClass3d_SolidClassifier(_solid(shape).wrapped)

    def inside(self, p) -> bool:
        self.c.Perform(gp_Pnt(float(p[0]), float(p[1]), float(p[2])), 1e-7)
        return self.c.State() == TopAbs_IN

    def boundary(self, p0, d, rmax, step=0.02):
        """Distance along unit direction d from p0 to the first change of the in/out state (bisected), or None."""
        p0, d = np.array(p0, float), np.array(d, float)
        d = d / np.linalg.norm(d)
        s0 = self.inside(p0)
        t = 0.0
        while t < rmax:
            t2 = min(t + step, rmax)
            if self.inside(p0 + d * t2) != s0:
                lo, hi = t, t2
                for _ in range(40):
                    mid = 0.5 * (lo + hi)
                    if self.inside(p0 + d * mid) != s0:
                        hi = mid
                    else:
                        lo = mid
                return 0.5 * (lo + hi)
            t = t2
        return None


def _vol(a, b) -> float:
    r = a.intersect(b)
    return r.Volume() if r is not None else 0.0


def _bb(sh):
    b = sh.BoundingBox()
    return b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax


def _cyl_faces(sh, axis, r, tol=0.02):
    """Cylindrical faces of radius r whose axis is parallel to `axis` (0 = x, 1 = y, 2 = z): list of (radius, point on axis)."""
    out = []
    for f in sh.Faces():
        if f.geomType() != "CYLINDER":
            continue
        cyl = f._geomAdaptor().Cylinder()
        d = cyl.Axis().Direction()
        comp = (d.X(), d.Y(), d.Z())
        if abs(abs(comp[axis]) - 1.0) > 1e-6 or abs(cyl.Radius() - r) > tol:
            continue
        loc = cyl.Location()
        out.append((cyl.Radius(), (loc.X(), loc.Y(), loc.Z())))
    return out


def _plane_faces(sh, normal_axis, sign=None):
    out = []
    for f in sh.Faces():
        if f.geomType() != "PLANE":
            continue
        n = f.normalAt()
        comp = (n.x, n.y, n.z)
        if abs(abs(comp[normal_axis]) - 1.0) > 1e-6:
            continue
        if sign is not None and comp[normal_axis] * sign < 0:
            continue
        out.append(f)
    return out


def _angle_probe_radius(probe, y, phi_deg, rmax=4.0):
    """Radius of the solid boundary at height y along the direction phi (from +x toward +z)."""
    a = math.radians(phi_deg)
    return probe.boundary((0.0, y, 0.0), (math.cos(a), 0.0, math.sin(a)), rmax, 0.02)


def _stl_triangles(path):
    d = open(path, "rb").read()
    n = struct.unpack("<I", d[80:84])[0]
    assert len(d) == 84 + 50 * n, "binary STL expected"
    arr = np.frombuffer(d, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=n, offset=84)
    return arr["v"].astype(float)


# ---------------------------------------------------------------------------------------------------------------------
# fixtures (builds are cached per module; the reference shell intersection takes a few seconds)
# ---------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def cap():
    return E.make_magnet_cap().val()


@pytest.fixture(scope="module")
def cap_noribs():
    return E.make_magnet_cap(ribs=False).val()


@pytest.fixture(scope="module")
def casing():
    return E.make_casing().val()


@pytest.fixture(scope="module")
def magnet():
    return E.make_magnet().val()


@pytest.fixture(scope="module")
def board():
    return E.make_board().val()


@pytest.fixture(scope="module")
def ref():
    return E.reference_parts(True)


@pytest.fixture(scope="module")
def ref_raw():
    return E.reference_parts(False)


@pytest.fixture(scope="module")
def cap_probe(cap):
    return Probe(cap)


@pytest.fixture(scope="module")
def casing_probe(casing):
    return Probe(casing)


# =====================================================================================================================
# derived levels and the re-measured interfaces
# =====================================================================================================================
def test_derived_levels_match_spec():
    c = C0
    assert c.magnet_face_y == pytest.approx(29.3, abs=1e-9)
    assert c.chip_face_y == pytest.approx(30.8, abs=1e-9)
    assert c.pcb_front_y == pytest.approx(32.25, abs=1e-9)
    assert c.pcb_back_y == pytest.approx(33.85, abs=1e-9)
    assert c.peg_end_y == pytest.approx(22.6, abs=1e-9)
    assert c.frame_front_y == pytest.approx(31.0, abs=1e-9) and c.frame_front_y >= 31.0 - 1e-9
    assert (c.pocket_d, c.pocket_depth) == (pytest.approx(POCKET_D), pytest.approx(P.ENC1021_MAGNET_T + P.ENC1021_CAP_POCKET_EXTRA_DEPTH))
    assert c.head_t == pytest.approx(3.3)
    assert c.pocket_half * 2 == pytest.approx(23.4) and (c.pocket_half + c.wall) * 2 == pytest.approx(27.4)
    assert c.foot_top_x - c.plate_x == pytest.approx(3.0)            # 3 mm proud of the plate face
    assert c.plate_x - c.floor_x == pytest.approx(1.0)               # keyed 1.0 deep


def holes_planes(sl):
    """Planar hole-bottom faces of the divot holes (normal +x, area pi r^2)."""
    return [f for f in _plane_faces(sl, 0, +1) if abs(f.Area() - math.pi * 1.725 ** 2) < 0.05]


def test_reference_interfaces_remeasured(ref, ref_raw):
    """Spec section 2 re-measured from the STEPs.  Corrected frame vs params: < 0.01 mm; plain 'subtract 2.64' vs the spec
    table: < 0.1 mm (disagreements over 0.1 mm would be reported, there are none)."""
    sp, sl, mo = ref["Spool1011"], ref["Slipin_mount_piecev3"], ref["Motor_Reference"]
    dev = {}
    # --- spool: flanges, core, bore, D-flat
    ys = sorted({round(f.BoundingBox().ymin, 4) for f in _plane_faces(sp, 1)})
    assert len(ys) == 4
    for got, exp in zip(ys, (7.0, 10.0, 23.0, 26.0)):
        dev[f"spool plane y={exp}"] = got - exp
    assert _cyl_faces(sp, 1, 18.0) and _cyl_faces(sp, 1, 7.5), "flange Ø36 and core Ø15"
    bore = _cyl_faces(sp, 1, C0.bore_d / 2)
    assert len(bore) == 2, "bore: two half-cylinder faces"
    for i, (r, loc) in enumerate(bore):
        dev[f"bore r {i}"] = r - C0.bore_d / 2
        dev[f"bore axis x {i}"] = loc[0]
        dev[f"bore axis z {i}"] = loc[2]
    flats = [f for f in _plane_faces(sp, 0, sign=-1) if abs(f.BoundingBox().xmin - 2.15) < 0.05]
    assert len(flats) == 1
    fb = flats[0].BoundingBox()
    dev["bore flat x"] = fb.xmin - C0.bore_flat_x
    assert fb.ymin == pytest.approx(7.0, abs=0.01) and fb.ymax == pytest.approx(26.0, abs=0.01)   # through the whole spool
    # --- motor shaft end
    shaft = min(mo.Solids(), key=lambda s: s.Volume())
    dev["shaft end y"] = shaft.BoundingBox().ymax - C0.shaft_end_y
    assert shaft.BoundingBox().xlen == pytest.approx(5.0, abs=0.01)
    # --- slip-in plate face, divot floor, rim, holes
    plate = [f for f in _plane_faces(sl, 0, sign=+1) if f.Area() > 1000 and abs(f.BoundingBox().xmin - C0.plate_x) < 0.05]
    assert plate, "back-plate face (normal +x) at x = -21.15"
    dev["plate face x"] = plate[0].BoundingBox().xmin - C0.plate_x
    floor = [f for f in _plane_faces(sl, 0, sign=+1) if abs(f.Area() - (22 * 22 - 4 * math.pi * 1.725 ** 2)) < 0.5]
    assert len(floor) == 1
    fb = floor[0].BoundingBox()
    dev["divot floor x"] = fb.xmin - C0.floor_x
    dev["divot centre y"] = 0.5 * (fb.ymin + fb.ymax) - C0.divot_y
    dev["divot centre z"] = 0.5 * (fb.zmin + fb.zmax) - C0.divot_z
    dev["divot floor size"] = (fb.ymax - fb.ymin) - 22.0
    def in_divot(f):
        b = f.BoundingBox()
        return b.xmin > -22.2 and b.xmax < -21.1 and 32.9 < b.ymin and b.ymax < 57.1 and abs(b.zmin) < 12.1 and abs(b.zmax) < 12.1

    wall = [f for f in sl.Faces() if f.geomType() == "CYLINDER" and in_divot(f)
            and abs(f._geomAdaptor().Cylinder().Radius() - C0.divot_wall_r) < 1e-6]
    assert len(wall) == 4, "divot wall = four R1.0 quarter-round faces (floor 22 x 22, rim 24 x 24)"
    zs = [f.BoundingBox().zmax for f in wall] + [f.BoundingBox().zmin for f in wall]
    ys_w = [f.BoundingBox().ymax for f in wall] + [f.BoundingBox().ymin for f in wall]
    dev["divot rim z"] = (max(zs) - min(zs)) - C0.divot_rim
    dev["divot rim y"] = (max(ys_w) - min(ys_w)) - C0.divot_rim
    holes = _cyl_faces(sl, 0, C0.divot_hole_d / 2, tol=0.01)
    centres = sorted({(round(l[1], 3), round(l[2], 3)) for _, l in holes})
    assert len(centres) == 4
    exp = sorted((C0.divot_y + sy * 4.75, C0.divot_z + sz * 4.75) for sy in (-1, 1) for sz in (-1, 1))
    for i, ((gy, gz), (ey, ez)) in enumerate(zip(centres, exp)):
        dev[f"hole {i} centre y"] = gy - ey
        dev[f"hole {i} centre z"] = gz - ez
    hb = holes_planes(sl)
    assert len(hb) == 4
    for i, f in enumerate(hb):
        dev[f"hole {i} bottom x"] = f.BoundingBox().xmin - (C0.floor_x - P.ENC1021_DIVOT_HOLE_DEPTH)
    worst = max(abs(v) for v in dev.values())
    print("max deviation of the re-measured interfaces from ENC1021_* (corrected frame): %.5f mm" % worst)
    assert worst < 0.01, dev
    # --- spec table (plain subtract-2.64 frame, spec's own rounding): nothing disagrees by more than 0.1 mm
    sp_r, sl_r = ref_raw["Spool1011"], ref_raw["Slipin_mount_piecev3"]
    spec = {"spool face y 26.0": (sp_r.BoundingBox().ymax, 26.0), "shaft end y 22.0": (ref_raw["Motor_Reference"].BoundingBox().ymax, 22.0),
            "divot floor x -22.1": (min(f.BoundingBox().xmin for f in _plane_faces(sl_r, 0, +1) if abs(f.Area() - 446.61) < 0.5), -22.1),
            "hole Ø3.46": (2 * _cyl_faces(sl_r, 0, 1.725, 0.01)[0][0], 3.46),
            "spool axis z 0": ((sp_r.BoundingBox().zmin + sp_r.BoundingBox().zmax) / 2, 0.0)}
    for k, (got, exp_) in spec.items():
        assert abs(got - exp_) < 0.1, (k, got, exp_)


# =====================================================================================================================
# MAGNET CAP
# =====================================================================================================================
def test_cap_is_one_valid_solid(cap):
    assert cap.isValid()
    assert len(cap.Solids()) == 1


def test_cap_bbox_and_volume(cap):
    x0, x1, y0, y1, z0, z1 = _bb(cap)
    assert (x0, x1) == (pytest.approx(-7.0, abs=1e-3), pytest.approx(7.0, abs=1e-3))
    assert (z0, z1) == (pytest.approx(-7.0, abs=1e-3), pytest.approx(7.0, abs=1e-3))
    assert y0 == pytest.approx(22.6, abs=1e-3) and y1 == pytest.approx(29.3, abs=1e-3)
    v = cap.Volume()
    assert 450.0 < v < 600.0                                                     # 531.9 for the Ø4.0 magnet (490.2 for the Ø6 record)
    print("cap volume %.1f mm3, mass %.2f g (PETG)" % (v, v * P.ENC1021_PETG_G_CM3 / 1000))


def test_cap_peg_length_and_end_level(cap_probe):
    """Peg 3.4 long: end face at y = 22.6, 0.6 mm clear of the shaft end (22.0); head underside at the spool face (26.0)."""
    y_end = 20.0 + cap_probe.boundary((0, 20.0, 0), (0, 1, 0), 5.0)            # on the axis
    assert y_end == pytest.approx(22.6, abs=0.01)
    y_under = 20.0 + cap_probe.boundary((5.0, 20.0, 0.0), (0, 1, 0), 9.0)      # r = 5: outside the peg, under the head
    assert y_under == pytest.approx(26.0, abs=0.01)
    assert y_under - y_end == pytest.approx(3.4, abs=0.01)
    assert y_end - C0.shaft_end_y == pytest.approx(0.6, abs=0.01)


def test_cap_peg_profile_fits_bore_d_profile(cap_probe, ref):
    """Peg Ø5.10 + flat at +2.05 against the bore Ø5.30 + flat at +2.15: 0.10 mm clear on the round part and on the flat;
    three crush ribs 0.15 high (tip radius 2.70, i.e. 0.05 mm of crush into the Ø5.30 bore)."""
    sp = Probe(ref["Spool1011"])
    y = 24.3                                                       # mid peg, inside the spool's outer flange
    angles = list(range(0, 360, 5))
    peg = {a: _angle_probe_radius(cap_probe, y, a) for a in angles}
    bore = {a: sp.boundary((0.0, y, 0.0), (math.cos(math.radians(a)), 0, math.sin(math.radians(a))), 4.0, 0.02) for a in angles}
    assert bore[0] == pytest.approx(2.15, abs=0.005)                # bore flat
    assert bore[90] == pytest.approx(2.65, abs=0.005) and bore[180] == pytest.approx(2.65, abs=0.005)
    assert peg[0] == pytest.approx(2.05, abs=0.005)                 # peg flat
    rib_angles = [180, 300, 60]
    for a in rib_angles:
        assert peg[a] == pytest.approx(2.70, abs=0.005), (a, peg[a])
    for a in angles:
        sa = min(a, 360 - a)
        if sa <= 35:                                                # flat region: r = 2.05 / cos(a)
            assert peg[a] == pytest.approx(2.05 / math.cos(math.radians(sa)), abs=0.005), (a, peg[a])
            assert bore[a] == pytest.approx(2.15 / math.cos(math.radians(sa)), abs=0.005), (a, bore[a])
    core = [a for a in angles if min(abs((a - r + 180) % 360 - 180) for r in rib_angles) > 15 and min(a, 360 - a) > 40]
    for a in core:                                                  # round part, between the ribs
        assert peg[a] == pytest.approx(2.55, abs=0.005), (a, peg[a])
        assert bore[a] == pytest.approx(2.65, abs=0.005), (a, bore[a])
    clear = min(bore[a] - peg[a] for a in core)                     # excluding the ribs
    assert clear == pytest.approx(0.10, abs=0.01)
    assert (bore[0] - peg[0]) == pytest.approx(0.10, abs=0.01)      # flat clearance
    crush = [peg[a] - bore[a] for a in rib_angles]
    assert all(c == pytest.approx(0.05, abs=0.01) for c in crush), crush
    n_ribs = sum(1 for i, a in enumerate(angles) if peg[a] > 2.62 and peg[angles[i - 1]] <= 2.62)
    assert n_ribs == 3


def test_cap_without_ribs_has_clearance_and_head_contact_only(cap_noribs, ref):
    sp = ref["Spool1011"]
    assert _vol(cap_noribs, sp) < INTERFERENCE_TOL_MM3             # peg clear of the bore, head only touches the face
    peg = E.make_peg(ribs=False).val()                              # the peg alone: 0.10 mm to the bore wall
    assert peg.distance(sp) == pytest.approx(0.10, abs=0.01)


def test_cap_interference_with_spool_is_the_crush_ribs_only(cap, cap_noribs, ref, ref_raw):
    v = _vol(cap, ref["Spool1011"])
    print("crush-rib interference with the bore: %.3f mm3" % v)
    assert 0.05 < v < 0.5                                           # 3 ribs x 3.4 mm x ~0.01 mm2 of crush
    assert _vol(cap_noribs, ref["Spool1011"]) < INTERFERENCE_TOL_MM3     # without the ribs there is none: the ribs are all of it
    v_raw = _vol(cap, ref_raw["Spool1011"])                         # plain subtract-2.64 frame: + 0.0016 mm head overlap
    assert v_raw < v + 0.5


def test_cap_clear_of_motor_shaft_and_all_other_parts(cap, ref):
    for n in ("Motor_Reference", "Heat_horn", "Shell_Casing", "Slipin_mount_piecev3", "Wall_Mount_v3"):
        assert _vol(cap, ref[n]) == 0.0, n
    assert cap.distance(ref["Motor_Reference"]) == pytest.approx(0.6, abs=0.01)       # 0.6 mm from the shaft end


def test_cap_magnet_pocket_and_face_level(cap_probe, magnet, cap):
    """Pocket Ø(magnet + 0.2) x 2.55 on the axis, opening toward +y; the magnet face sits flush at y = 29.3 (+-0.05)."""
    # top face of the head (r = 5): first solid met from above
    y_top = 31.0 - cap_probe.boundary((5.0, 31.0, 0.0), (0, -1, 0), 8.0)
    assert y_top == pytest.approx(29.3, abs=0.01)
    y_floor = 31.0 - cap_probe.boundary((0.0, 31.0, 0.0), (0, -1, 0), 8.0)           # pocket floor on the axis
    assert y_floor == pytest.approx(26.75, abs=0.01)
    assert y_top - y_floor == pytest.approx(2.55, abs=0.01)
    for a in (0, 45, 90, 180, 270):                                                   # pocket radius POCKET_R, centred on the axis
        r = cap_probe.boundary((0.0, 28.0, 0.0), (math.cos(math.radians(a)), 0, math.sin(math.radians(a))), 5.0)
        assert r == pytest.approx(POCKET_R, abs=0.01), a
    # reference magnet: glued flush, and the worst case (bottomed in the pocket) is 0.05 lower
    bb = magnet.BoundingBox()
    assert bb.ymax == pytest.approx(29.3, abs=0.05)
    assert (bb.ymax - 0.05) == pytest.approx(29.3, abs=0.05 + 1e-9)
    assert (bb.xmin + bb.xmax) / 2 == pytest.approx(0.0, abs=0.01) and (bb.zmin + bb.zmax) / 2 == pytest.approx(0.0, abs=0.01)
    assert _vol(magnet, cap) < INTERFERENCE_TOL_MM3
    assert magnet.distance(cap) == pytest.approx(0.05, abs=0.01)                       # 0.05 glue film below, 0.10 radial


def test_cap_pry_notch(cap_probe):
    """0.8 mm notch under the head rim at +z (for a blade); the rim is intact elsewhere."""
    assert not cap_probe.inside((0.0, 26.4, 6.0))            # in the notch
    assert cap_probe.inside((0.0, 27.0, 6.0))                # above it
    assert cap_probe.inside((6.0, 26.4, 0.0)) and cap_probe.inside((0.0, 26.4, -6.0))
    assert cap_probe.inside((3.0, 26.4, 6.0))                # notch is 3 wide: x = 3 is solid


# =====================================================================================================================
# ENCODER CASING
# =====================================================================================================================
def test_casing_is_one_valid_solid(casing):
    assert casing.isValid()
    assert len(casing.Solids()) == 1


def test_casing_bbox_and_volume(casing):
    x0, x1, y0, y1, z0, z1 = _bb(casing)
    assert x0 == pytest.approx(-22.15, abs=1e-3) and x1 == pytest.approx(13.7, abs=1e-3)
    assert y0 == pytest.approx(31.0, abs=1e-3) and y1 == pytest.approx(56.8, abs=1e-3)
    assert z0 == pytest.approx(-13.7, abs=1e-3) and z1 == pytest.approx(13.7, abs=1e-3)
    v = casing.Volume()
    assert 3000.0 < v < 4200.0
    print("casing volume %.1f mm3, mass %.2f g (PETG)" % (v, v * P.ENC1021_PETG_G_CM3 / 1000))


def test_casing_chip_face_plane_and_tabs(casing_probe):
    """Four 3 x 3 front-stop tabs at the pocket corners: back face on the PCB front face (32.25) = chip face + 1.45, so the
    chip face plane is y = 30.8 (+-0.1); tab front face at y >= 31.0."""
    for sx in (-1, 1):
        for sz in (-1, 1):
            ctr = (sx * 10.2, 0.0, sz * 10.2)
            y_front = 30.0 + casing_probe.boundary((ctr[0], 30.0, ctr[2]), (0, 1, 0), 3.0)
            y_back = 33.0 - casing_probe.boundary((ctr[0], 33.0, ctr[2]), (0, -1, 0), 3.0)
            assert y_front >= 31.0 - 1e-3 and y_front == pytest.approx(31.0, abs=0.01)
            assert y_back == pytest.approx(32.25, abs=0.01)
            assert y_back - P.ENC1021_CHIP_H == pytest.approx(30.8, abs=0.1)              # chip face plane
            assert y_back - P.ENC1021_CHIP_H == pytest.approx(C0.chip_face_y, abs=0.01)
            # tab plan size: inner edge 3.0 from the pocket wall
            ex = casing_probe.boundary((0.0, 31.6, ctr[2]), (sx, 0, 0), 14.0)
            ez = casing_probe.boundary((ctr[0], 31.6, 0.0), (0, 0, sz), 14.0)
            assert 11.7 - ex == pytest.approx(3.0, abs=0.02) and 11.7 - ez == pytest.approx(3.0, abs=0.02)
    # no full ledge: mid-edge (x = 0) has no front stop
    assert not casing_probe.inside((0.0, 31.6, 11.0)) and not casing_probe.inside((0.0, 31.6, -11.0))


def test_casing_pocket_centred_on_axis(casing_probe):
    """Board pocket 23.4 x 23.4 centred on the axis within 0.05 mm."""
    y = 32.9                                                          # mid PCB thickness
    xp = casing_probe.boundary((0.0, y, 0.0), (1, 0, 0), 14.0)
    xn = casing_probe.boundary((0.0, y, 0.0), (-1, 0, 0), 14.0)
    zp = casing_probe.boundary((0.0, y, 0.0), (0, 0, 1), 14.0)
    zn = casing_probe.boundary((0.0, y, 0.0), (0, 0, -1), 14.0)
    assert xp + xn == pytest.approx(23.4, abs=0.02) and zp + zn == pytest.approx(23.4, abs=0.02)
    assert abs(xp - xn) / 2 < 0.05 and abs(zp - zn) / 2 < 0.05
    # frame walls: 2.0 mm on the pad edges (+-x), thinned flex wall 1.2 mm on the hook edges (+-z); outer 27.4 over the corner blocks
    xo = casing_probe.boundary((xp + 0.1, y, 0.0), (1, 0, 0), 5.0)
    assert xp + 0.1 + xo - 11.7 == pytest.approx(2.0, abs=0.02)
    zo = casing_probe.boundary((0.0, y, zp + 0.1), (0, 0, 1), 5.0)
    assert zp + 0.1 + zo - 11.7 == pytest.approx(P.ENC1021_FLEX_WALL_T, abs=0.02)


def test_board_fits_pocket_and_hooks_retain_it(casing, casing_probe, board):
    """The PCB sits on the tabs (contact only), 0.2 mm clear of the walls, retained by the two lips 0.1 mm behind its back;
    the pad edges (+-x) are open behind the board, so wires can leave backward."""
    assert _vol(board, casing) == 0.0
    assert board.distance(casing) == pytest.approx(0.0, abs=1e-6)                      # tab contact
    bb = board.BoundingBox()
    assert (bb.ymin, bb.ymax) == (pytest.approx(30.8, abs=1e-6), pytest.approx(33.85, abs=1e-6))   # chip front / PCB back
    # lip: catch face 0.1 behind the PCB back face, overlap 0.4 over the PCB edge, +z and -z
    for s in (1, -1):
        y_catch = 33.85 + casing_probe.boundary((0.0, 33.85, s * 11.3), (0, 1, 0), 2.0)
        assert y_catch == pytest.approx(33.95, abs=0.01)
        z_tip = casing_probe.boundary((0.0, 34.2, 0.0), (0, 0, s), 13.0)
        assert z_tip == pytest.approx(11.5 - P.ENC1021_HOOK_OVERLAP, abs=0.01)
        # the ramp is 45 deg: the lip is 0.3 mm shorter in z halfway up the ramp
        z_ramp = casing_probe.boundary((0.0, 34.6, 0.0), (0, 0, s), 13.0)
        assert z_ramp > z_tip + 0.1
        # lips only over the hook width
        assert not casing_probe.inside((6.0, 34.2, s * 11.3))
    # pad edges open behind the board; wall present beside it
    for s in (1, -1):
        assert casing_probe.inside((s * 12.7, 32.5, 0.0)) and not casing_probe.inside((s * 12.7, 34.5, 0.0))
    # 0.2 mm clearance to every wall for the board outline
    px, pz = C0.pcb_half, C0.pcb_half
    assert 11.7 - px == pytest.approx(0.2)


def test_board_is_retained_and_located_by_the_casing(casing, casing_probe, board):
    """Swept-board checks: the board cannot move back (+y) past the 0.1 mm catch gap, nor forward (tabs), and has 0.2 mm of
    play to the walls; the hook walls are free to flex outward (nothing within 1 mm outside them)."""
    def shifted(dx=0.0, dy=0.0, dz=0.0):
        return board.translate(cq.Vector(dx, dy, dz))
    assert _vol(shifted(dy=0.09), casing) == 0.0                       # inside the 0.1 mm gap behind the board
    assert _vol(shifted(dy=0.30), casing) > 0.5                        # the lips catch it
    assert _vol(shifted(dy=-0.05), casing) > 0.0                       # the tabs stop it from moving forward
    for dx, dz in ((0.19, 0), (-0.19, 0), (0, 0.19), (0, -0.19)):
        assert _vol(shifted(dx=dx, dz=dz), casing) == 0.0, (dx, dz)    # 0.2 mm side clearance
    for dx, dz in ((0.25, 0), (-0.25, 0), (0, 0.25), (0, -0.25)):
        assert _vol(shifted(dx=dx, dz=dz), casing) > 0.0, (dx, dz)
    for x in (-10.0, 0.0, 10.0):
        for y in (32.0, 34.5):
            for s_ in (1, -1):
                assert not casing_probe.inside((x, y, s_ * 13.4)), (x, y, s_)      # flex wall outer face is at 12.9: free beyond


def test_zip_tie_slots_through_the_bridge(casing_probe):
    for s_ in (1, -1):
        for y in (31.5, 34.0, 36.0):
            assert not casing_probe.inside((-16.0, y, s_ * 6.2)), (s_, y)     # slot open through the bridge
            assert casing_probe.inside((-16.0, y, s_ * 3.0)), (s_, y)         # bridge material between the slots
    assert casing_probe.inside((-16.0, 34.0, 0.0))


def test_casing_foot_dimensions_and_key(casing_probe):
    """Foot 23.6 x 23.6 x 4.0 (floor x -22.15 .. -18.15): 1.0 keyed into the divot, 3.0 proud of the plate face (-21.15)."""
    x_bot = -25.0 + casing_probe.boundary((-25.0, 45.0, 0.0), (1, 0, 0), 8.0)
    x_top = -15.0 - casing_probe.boundary((-15.0, 45.0, 0.0), (-1, 0, 0), 8.0)
    # the casing frame is at x > -13.7: probe the foot top from above the foot at y = 50 (away from the bridge)
    assert x_bot == pytest.approx(-22.15, abs=0.01)
    assert x_top == pytest.approx(-18.15, abs=0.01)
    assert x_top - (-21.15) == pytest.approx(3.0, abs=0.01)           # proud of the plate face
    assert (-21.15) - x_bot == pytest.approx(1.0, abs=0.01)           # keyed depth
    # plan size at x = -19.5 (above the plate): y edge at 56.8, z edges at +-11.8
    ey = casing_probe.boundary((-19.5, 45.0, 0.0), (0, 1, 0), 15.0)
    ez_p = casing_probe.boundary((-19.5, 45.0, 0.0), (0, 0, 1), 15.0)
    ez_n = casing_probe.boundary((-19.5, 45.0, 0.0), (0, 0, -1), 15.0)
    assert ey == pytest.approx(11.8, abs=0.01)
    assert ez_p + ez_n == pytest.approx(23.6, abs=0.02)


def test_casing_foot_corner_radius_at_least_1_2(casing):
    """The foot's four plan corners are R1.2 cylinders (axis along x) at the corners of the 23.6 square; the divot's are R1.0."""
    corners = {(round(loc[1], 2), round(loc[2], 2)) for _, loc in _cyl_faces(casing, 0, 1.2, tol=0.05)}
    assert corners == {(round(45.0 + sy * 10.6, 2), round(sz * 10.6, 2)) for sy in (-1, 1) for sz in (-1, 1)}, corners
    assert P.ENC1021_FOOT_CORNER_R >= 1.2 > P.ENC1021_DIVOT_WALL_R


def test_a_plain_square_foot_would_not_seat_in_the_divot(ref):
    """Negative control for the spec's wording (\"24 x 24, R1.0 corners, 1.0 deep\"): the divot wall is a R1.0 QUARTER-ROUND, so
    a straight-sided 23.6 x 23.6 foot bottomed on the floor interferes with it; the casing's foot needs the R1.0 key edge."""
    plain = (cq.Workplane("YZ", origin=(C0.floor_x, 0, 0)).center(45.0, 0.0).rect(23.6, 23.6).extrude(4.0)
             .edges("|X").fillet(1.2)).val()
    v = _vol(plain, ref["Slipin_mount_piecev3"])
    print("plain 23.6 foot bottomed on the floor interferes by %.1f mm3" % v)
    assert v > 5.0                                                  # a wedge along all four walls, 8.6 mm3
    # ... and it only clears the wall when it sits ~0.6 mm higher (wall half-width 11 + sqrt(1 - t^2) = 11.8 at t = 0.6)
    lifted = plain.translate(cq.Vector(0.6, 0, 0))
    assert _vol(lifted, ref["Slipin_mount_piecev3"]) < INTERFERENCE_TOL_MM3


def test_foot_side_clearance_to_divot_is_0_2_mm(casing_probe, ref):
    """Measured against the reference slip-in: at every depth of the key the foot is 0.2 mm inside the divot wall on all four
    sides; on the corner diagonals it is further away (the foot's R1.2 clears the divot's R1.0)."""
    sl = Probe(ref["Slipin_mount_piecev3"])
    for x in (-22.14, -22.05, -21.9, -21.7, -21.5, -21.3, -21.2):
        for d in ((0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            p0 = (x, 45.0, 0.0)
            foot = casing_probe.boundary(p0, d, 14.0, 0.05)
            dish = sl.boundary(p0, d, 14.0, 0.05)
            assert dish - foot == pytest.approx(0.2, abs=0.006), (x, d, dish, foot)
        # corners: ray along the diagonal from a point inside both, past the screw holes (the foot has holes on the diagonal
        # nearer the centre).  The foot's R1.2 corner is 0.366 mm clear of the divot's R1.0 spherical corner at every depth;
        # the STEP's divot has that corner on three of its four corners and a sharp mitre on the (+y, +z) one (larger gap there).
        gaps = []
        for sy, sz in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            p0 = (x, 45.0 + 9.0 * sy, 9.0 * sz)
            dd = (0, sy / math.sqrt(2), sz / math.sqrt(2))
            gaps.append(sl.boundary(p0, dd, 20.0, 0.05) - casing_probe.boundary(p0, dd, 20.0, 0.05))
        assert min(gaps) >= 0.36, (x, gaps)
        assert sum(1 for g in gaps if abs(g - 0.366) < 0.006) == 3, (x, gaps)
        assert max(gaps) > 0.4                                      # the sharp (+y, +z) corner of the divot


def test_foot_holes_coaxial_with_divot_holes_within_0_05(casing, ref):
    """Four Ø3.4 holes (circle part of the teardrop) coaxial with the divot's four Ø3.45 holes, measured from the STEP."""
    mine = _cyl_faces(casing, 0, 1.7, tol=0.01)
    assert len({(round(l[1], 3), round(l[2], 3)) for _, l in mine}) == 4
    theirs = {(round(l[1], 3), round(l[2], 3)) for _, l in _cyl_faces(ref["Slipin_mount_piecev3"], 0, 1.725, tol=0.01)}
    assert len(theirs) == 4
    for (_, l) in mine:
        d = min(math.hypot(l[1] - ty, l[2] - tz) for ty, tz in theirs)
        assert d < 0.05, d
    for (_, l) in mine:
        assert any(abs(l[1] - y) < 0.01 and abs(l[2] - z) < 0.01 for y, z in C0.hole_pts)
    # the holes pass through the whole foot (floor to top face) and the pointed top (print) leaves 45 deg flanks only
    for (y, z) in C0.hole_pts:
        assert casing.isInside(cq.Vector(-20.0, y, z)) is False
        assert casing.isInside(cq.Vector(-22.0, y, z)) is False and casing.isInside(cq.Vector(-18.3, y, z)) is False


def test_screw_heads_reachable_from_the_room_side(casing, ref):
    """Cylinders Ø(head + tool clearance) from the foot's +x face outward along each hole axis hit nothing of the casing
    (or the station parts): the region above the holes is open."""
    r = C0.screw_access_r
    for (y, z) in C0.hole_pts:
        cyl = cq.Workplane("YZ", origin=(C0.foot_top_x, 0, 0)).center(y, z).circle(r).extrude(40.0).val()
        assert _vol(casing, cyl) == 0.0, (y, z)
        for n in ("Slipin_mount_piecev3", "Spool1011", "Motor_Reference", "Wall_Mount_v3", "Heat_horn"):
            assert _vol(ref[n], cyl) < INTERFERENCE_TOL_MM3, (n, y, z)
        above_foot = casing.intersect(cq.Workplane("XY").box(60, 80, 60, centered=False).translate((C0.foot_top_x + 0.05, 0, -30)).val())
        assert above_foot.distance(cyl) >= 0.5                           # bridge top 36.2 vs access cylinder 36.75: 0.55 mm
    # printed, the heads sit directly on the foot face: nothing between the head and the foot
    assert C0.hole_pts[0][0] - r >= P.ENC1021_BRIDGE_TOP_Y + 0.3 - 1e-9


# =====================================================================================================================
# ASSEMBLY CLEARANCES
# =====================================================================================================================
@pytest.mark.parametrize("name", ["Slipin_mount_piecev3", "Spool1011", "Shell_Casing", "Motor_Reference", "Heat_horn", "Wall_Mount_v3"])
def test_casing_zero_interference_with_every_reference_part(casing, ref, ref_raw, name):
    v = _vol(casing, ref[name])
    assert v < INTERFERENCE_TOL_MM3, (name, v)                         # incl. Slipin: foot-on-floor is face contact only
    # plain 'subtract (0, 0, 2.64)' frame: only the 0.0002 .. 0.004 mm extraction residual at the intended foot contact
    v_raw = _vol(casing, ref_raw[name])
    assert v_raw < (2.5 if name == "Slipin_mount_piecev3" else INTERFERENCE_TOL_MM3), (name, v_raw)


def test_foot_touches_the_divot_floor_and_nothing_else(casing, ref):
    sl = ref["Slipin_mount_piecev3"]
    assert casing.distance(sl) == pytest.approx(0.0, abs=1e-6)         # contact
    bottom = [f for f in _plane_faces(casing, 0, sign=-1) if abs(f.BoundingBox().xmin - (-22.15)) < 1e-3]
    assert len(bottom) == 1
    area = bottom[0].Area()
    # flat bottom: 21.6 square with R0.2 corners, minus four teardrop holes (circle + 45 deg point = 9.70 mm2 each)
    r = C0.foot_hole_d / 2
    teardrop = math.pi * r * r + (1 - math.pi / 4) * r * r            # circle + the 45 deg point beyond its tangent chord
    expect = 21.6 ** 2 - (4 - math.pi) * 0.2 ** 2 - 4 * teardrop
    print("foot / divot-floor contact patch: %.1f mm2 (expected %.1f)" % (area, expect))
    assert area == pytest.approx(expect, abs=0.5)
    # everything above the floor is clear: with the bottom 0.03 mm shaved off nothing touches any more
    above = casing.intersect(cq.Workplane("XY").box(100, 100, 100, centered=False).translate((-22.12, -10, -50)).val())
    d = above.distance(sl)
    print("casing above the floor +0.03 mm: %.3f mm from the slip-in (fillet root ~0.03)" % d)
    assert 0.01 < d < 0.05


def test_filler_and_bridge_are_clear_of_the_plate_face(casing, ref):
    """The bridge / filler under the foot (y < 33.0, where the plate is solid up to x = -21.15) sits 0.25 mm above the face."""
    low = casing.intersect(cq.Workplane("XY").box(100, 2.0, 100, centered=False).translate((-50, 30.0, -50)).val())   # y 30 .. 32
    assert low.Volume() > 100.0
    d = low.distance(ref["Slipin_mount_piecev3"])
    assert d == pytest.approx(0.25, abs=0.01)


@pytest.mark.parametrize("name", ["Slipin_mount_piecev3", "Spool1011", "Shell_Casing", "Motor_Reference", "Heat_horn", "Wall_Mount_v3"])
def test_casing_distance_to_reference_parts(casing, ref, name):
    d = casing.distance(ref[name])
    print(f"casing -> {name}: {d:.3f} mm")
    if name == "Slipin_mount_piecev3":
        assert d == pytest.approx(0.0, abs=1e-6)                       # the intended foot contact
    else:
        assert d >= 1.0                                                # >= 1.0 mm to the shell's inner faces and to everything else
    if name == "Shell_Casing":
        assert d >= 10.0


def test_line_path_stays_clear(casing):
    """The line winds on the core between the flanges (y 10-23): nothing of the casing may enter y < 26 within r 19 of the axis."""
    c = casing.BoundingBox()
    assert c.ymin >= 26.0
    assert c.ymin - 26.0 >= 4.9                                         # in fact the frame starts at 31.0
    # explicit cylinder r = 19, y 0 .. 26
    zone = cq.Workplane(E._plane_y(0.0)).circle(19.0).extrude(26.0).val()
    assert _vol(casing, zone) == 0.0


def test_rotating_cap_sweep_keeps_clear_of_the_casing(cap, casing, board):
    """Sweep the cap 360 deg about the shaft axis (10 deg steps + the exact body of revolution): >= 1.0 mm to every casing
    surface; the chip face is the only thing within 1.5 mm."""
    dmin = 1e9
    for a in range(0, 360, 10):
        rc = cap.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), a)
        dmin = min(dmin, rc.distance(casing))
    # exact swept envelope: head cylinder + peg cylinder
    head = cq.Workplane(E._plane_y(26.0)).circle(7.0).extrude(3.3).val()
    peg = cq.Workplane(E._plane_y(22.6)).circle(2.7).extrude(3.5).val()
    d_env = min(head.distance(casing), peg.distance(casing))
    print("swept cap -> casing: min %.3f mm (envelope %.3f)" % (dmin, d_env))
    assert dmin >= 1.0 and d_env >= 1.0 - 1e-6
    assert d_env <= dmin + 1e-6
    # the chip (front of the board) is 1.5 mm from the magnet face / cap head: the air gap
    chip = board.intersect(cq.Workplane("XY").box(100, 1.6, 100, centered=False).translate((-50, 30.0, -50)).val())
    assert chip.BoundingBox().ymin == pytest.approx(30.8, abs=1e-6)
    d_chip = min(cap.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), a).distance(board) for a in range(0, 360, 30))
    assert d_chip == pytest.approx(1.5, abs=0.01)


def test_cap_and_casing_do_not_touch_each_other_or_the_shell_gap(cap, casing, ref):
    assert _vol(cap, casing) == 0.0
    assert cap.distance(ref["Shell_Casing"]) >= 1.0


# =====================================================================================================================
# PRINTABILITY
# =====================================================================================================================
def test_print_pose_bboxes(cap, casing):
    pc = E.to_print_pose(casing, "casing").BoundingBox()
    assert (pc.xmin, pc.ymin, pc.zmin) == (pytest.approx(0, abs=1e-6),) * 3
    assert (pc.xlen, pc.ylen, pc.zlen) == (pytest.approx(35.85, abs=1e-3), pytest.approx(27.4, abs=1e-3), pytest.approx(25.8, abs=1e-3))
    pk = E.to_print_pose(cap, "cap").BoundingBox()
    assert (pk.xmin, pk.ymin, pk.zmin) == (pytest.approx(0, abs=1e-6),) * 3
    assert (pk.xlen, pk.ylen, pk.zlen) == (pytest.approx(14.0, abs=1e-3), pytest.approx(14.0, abs=1e-3), pytest.approx(6.7, abs=1e-3))


def test_casing_prints_without_supports_over_the_pocket(casing):
    """Print orientation: frame front face (y = 31.0) on the bed, +y up.  Downward faces steeper than 45 deg: only the two
    hook catch ledges (inside the pocket plan) and the foot's key-edge ledge (~1 mm wide, beyond the filler, outside the pocket)."""
    over = E.overhang_faces(casing, "casing")
    pocket_plan, foot_edge, other = [], [], []
    for o in over:
        (lo, hi) = o["bbox"]
        inside_pocket = abs(lo[0]) <= 11.71 and abs(hi[0]) <= 11.71 and abs(lo[2]) <= 11.71 and abs(hi[2]) <= 11.71
        if inside_pocket:
            pocket_plan.append(o)
        elif hi[0] <= C0.bridge_x0 + 1e-6 and lo[1] >= 33.1 and hi[1] <= 33.7:
            foot_edge.append(o)
        else:
            other.append(o)
    assert not other, other
    # over the pocket: exactly the two hook catch faces, at y = 33.95, 0.6 x 8 mm each
    assert len(pocket_plan) == 1 and pocket_plan[0]["bbox"][0][1] == pytest.approx(33.95, abs=0.01)
    lip_area = 2 * C0.hook_w * C0.lip_protrusion
    assert pocket_plan[0]["area"] == pytest.approx(lip_area, rel=0.02)
    # foot key-edge ledge: <= 1.3 mm wide in x (from the bridge/filler edge), small area
    assert foot_edge
    width = max(o["bbox"][1][0] - o["bbox"][0][0] for o in foot_edge)
    area = sum(o["area"] for o in foot_edge)
    print("casing overhangs > 45 deg: hook ledges %.1f mm2, foot key-edge ledge %.1f mm2 (%.2f mm wide)" % (pocket_plan[0]["area"], area, width))
    assert width <= 1.3 and area < 40.0


def test_cap_prints_without_supports_one_bridge_over_the_pocket(cap):
    """Print orientation: magnet face (y = 29.3) on the bed, peg up.  The only downward face is the pocket floor seen as a
    ceiling: one bridge of the pocket diameter (4.2 mm for the Ø4.0 magnet; no supports needed for a bridge this short)."""
    over = E.overhang_faces(cap, "cap")
    assert len(over) == 1
    o = over[0]
    assert o["area"] == pytest.approx(math.pi * POCKET_R ** 2, rel=0.03)
    assert o["print_z"] == pytest.approx(2.55, abs=0.06)
    (lo, hi) = o["bbox"]
    assert hi[0] - lo[0] == pytest.approx(POCKET_D, abs=0.05)          # bridge span
    assert hi[0] - lo[0] <= 8.0


# =====================================================================================================================
# STIFFNESS / HOOK HAND CALCULATIONS (they consume the real solid)
# =====================================================================================================================
def test_bridge_stiffness_one_newton_moves_the_chip_less_than_0_1_mm(casing):
    s = E.stiffness_estimate(casing)
    print({k: (round(v, 5) if isinstance(v, float) else v) for k, v in s.items()})
    assert s["F_N"] == 1.0
    # section properties of the real bridge section at mid-span (y >= foot edge): (27.4 - 2 slots) x 3.0 mm
    h = P.ENC1021_BRIDGE_TOP_Y - (C0.divot_y - C0.foot / 2)
    w = 2 * P.ENC1021_BRIDGE_HALF_Z - 2 * C0.tie_w
    assert s["A_mm2"] == pytest.approx(w * h, rel=0.01)
    assert s["I_dy_mm4"] == pytest.approx(w * h ** 3 / 12.0, rel=0.01)     # bending in y about z: rectangle with two full-height slots
    assert s["worst_mm"] < P.ENC1021_STIFF_LIMIT_MM
    assert s["dy_mm"] > s["dz_mm"] and s["dy_mm"] > s["dx_mm"]          # the shaft direction (y) is the weak one


def test_snap_hook_stress_is_in_the_layer_plane_and_below_yield():
    h = E.hook_estimate()
    print({k: round(v, 3) for k, v in h.items()})
    assert h["sigma_MPa"] < 0.75 * 45.0                                 # PETG XY yield 45 MPa (cad/materials.py)
    assert h["strain_pct"] < 2.0
    assert h["F_N"] < 15.0                                              # insertion force per wall


# =====================================================================================================================
# EXPORTS
# =====================================================================================================================
@pytest.mark.parametrize("name,part,mk", [(E.CAP_NAME, "cap", E.make_magnet_cap), (E.CASING_NAME, "casing", E.make_casing)])
def test_step_round_trip(name, part, mk, tmp_path):
    wp = mk()
    path = str(tmp_path / f"{name}.step")
    cq.exporters.export(wp, path)
    back = cq.importers.importStep(path).val()
    a, b = wp.val(), back
    assert b.isValid() and len(b.Solids()) == 1
    assert b.Volume() == pytest.approx(a.Volume(), rel=1e-6)
    for u, v in zip(_bb(a), _bb(b)):
        assert u == pytest.approx(v, abs=1e-4)


@pytest.mark.parametrize("name,part,mk", [(E.CAP_NAME, "cap", E.make_magnet_cap), (E.CASING_NAME, "casing", E.make_casing)])
def test_exports_are_current(name, part, mk):
    """The files in exports/ are the current build: STEP (station frame) and STL (print orientation, bed at z = 0)."""
    step = os.path.join(E.STEP_DIR, f"{name}.step")
    stl = os.path.join(E.STL_DIR, f"{name}.stl")
    assert os.path.exists(step) and os.path.exists(stl), "run /usr/bin/python3 -m cad.parts.encoder1021"
    with E.params_override(ENC1021_MAGNET_D=RECORD_MAGNET_D):                           # the v1 cap on disk was exported for the Ø6 magnet (record)
        fresh = mk().val()
    on_disk = cq.importers.importStep(step).val()
    assert on_disk.Volume() == pytest.approx(fresh.Volume(), rel=1e-5)
    for u, v in zip(_bb(fresh), _bb(on_disk)):
        assert u == pytest.approx(v, abs=1e-3)
    tris = _stl_triangles(stl)
    assert len(tris) > 100
    # watertight: every edge shared by exactly two triangles (welded at 1e-4 mm)
    key = np.round(tris.reshape(-1, 3) * 1e4).astype(np.int64)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.reshape(-1, 3)
    edges = np.sort(np.concatenate([inv[:, [0, 1]], inv[:, [1, 2]], inv[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    assert np.all(counts == 2), f"{int((counts != 2).sum())} non-manifold edges"
    # volume from the mesh agrees with the B-rep (tessellation error only), bounding box = print pose, bed at z = 0
    v0 = tris[:, 0]
    vol = abs(np.sum(np.einsum("ij,ij->i", v0, np.cross(tris[:, 1], tris[:, 2]))) / 6.0)
    assert vol == pytest.approx(fresh.Volume(), rel=0.01)
    pp = E.to_print_pose(fresh, part).BoundingBox()
    lo, hi = tris.reshape(-1, 3).min(axis=0), tris.reshape(-1, 3).max(axis=0)
    assert lo == pytest.approx([0, 0, 0], abs=0.02)                  # mesh chord tolerance 0.02 mm
    assert hi == pytest.approx([pp.xlen, pp.ylen, pp.zlen], abs=0.02)
    assert lo[2] == pytest.approx(0.0, abs=1e-4)                     # the bed plane itself is exact


def test_standard_renders_and_assembly_preview_exist():
    names = []
    for part in (E.CAP_NAME, E.CASING_NAME):
        names += [f"{part}_{v}.png" for v in ("front", "rear", "left", "right", "top", "bottom", "iso")]
    names += ["encoder1021_assembly_iso.png", "encoder1021_assembly_section_z0.png"]
    for n in names:
        path = os.path.join(E.RENDER_DIR, n)
        assert os.path.exists(path), f"missing {path}: run /usr/bin/python3 -m cad.parts.encoder1021"
        with open(path, "rb") as fh:
            head = fh.read(8)
        assert head == b"\x89PNG\r\n\x1a\n" and os.path.getsize(path) > 5000


def test_exported_step_files_pass_the_interference_checks(ref):
    """The deliverables themselves (re-imported from exports/step, not the in-memory models) against the reference parts."""
    cas = cq.importers.importStep(os.path.join(E.STEP_DIR, f"{E.CASING_NAME}.step")).val()
    cap = cq.importers.importStep(os.path.join(E.STEP_DIR, f"{E.CAP_NAME}.step")).val()
    for n, r in ref.items():
        assert _vol(cas, r) < INTERFERENCE_TOL_MM3, n
        if n != "Spool1011":
            assert _vol(cap, r) < INTERFERENCE_TOL_MM3, n
    assert 0.05 < _vol(cap, ref["Spool1011"]) < 0.5                    # the crush ribs
    assert cas.distance(ref["Shell_Casing"]) >= 1.0
    assert cap.distance(cas) >= 1.0
    assert cap.distance(ref["Motor_Reference"]) == pytest.approx(0.6, abs=0.01)


# =====================================================================================================================
# PARAMETERS: one edit regenerates both parts
# =====================================================================================================================
def test_parameter_edit_regenerates_both_parts(monkeypatch):
    for k, v in (("ENC1021_MAGNET_D", 6.5), ("ENC1021_MAGNET_T", 3.0), ("ENC1021_PCB_THICK", 1.8), ("ENC1021_CHIP_H", 1.6),
                 ("ENC1021_AIR_GAP", 2.0), ("ENC1021_PCB_SIZE", 23.5), ("ENC1021_CHIP_OFFSET", (0.3, -0.2))):
        monkeypatch.setattr(P, k, v)
    c = E.Cfg()
    cap = E.make_magnet_cap().val()
    cas = E.make_casing().val()
    assert cap.isValid() and len(cap.Solids()) == 1 and cas.isValid() and len(cas.Solids()) == 1
    # head grows to hold the thicker magnet: floor >= 0.75
    assert c.head_t == pytest.approx(3.0 + 0.05 + 0.75)
    pc = Probe(cap)
    y_top = 31.0 - pc.boundary((5.0, 31.0, 0.0), (0, -1, 0), 8.0)
    assert y_top == pytest.approx(26.0 + 3.8, abs=0.01) and c.magnet_face_y == pytest.approx(29.8)
    assert pc.boundary((0, 28.0, 0), (1, 0, 0), 5.0) == pytest.approx(6.7 / 2, abs=0.01)         # pocket Ø6.7
    # casing: chip face = magnet face + 2.0, tab back face = chip face + 1.6, pocket 23.9 wide centred on the board centre (-0.3, +0.2)
    pk = Probe(cas)
    assert c.chip_face_y == pytest.approx(31.8) and c.pcb_front_y == pytest.approx(33.4) and c.pcb_back_y == pytest.approx(35.2)
    y_back = 34.5 - pk.boundary((-0.3 + 10.4, 34.5, 0.2 + 10.4), (0, -1, 0), 6.0)
    assert y_back == pytest.approx(33.4, abs=0.01)
    assert y_back - 1.6 == pytest.approx(31.8, abs=0.01)
    xp = pk.boundary((-0.3, 33.5, 0.2), (1, 0, 0), 14.0)
    xn = pk.boundary((-0.3, 33.5, 0.2), (-1, 0, 0), 14.0)
    assert xp + xn == pytest.approx(23.9, abs=0.02) and (xp - xn) / 2 == pytest.approx(0.0, abs=0.02)
    # both stay clear of each other and of the divot
    assert cap.distance(cas) >= 1.0
    assert _vol(cas, E.reference_parts(True)["Slipin_mount_piecev3"]) < INTERFERENCE_TOL_MM3
    # foot and holes did not move
    bb = cas.BoundingBox()
    assert bb.xmin == pytest.approx(-22.15, abs=1e-3)


def test_corner_pins_option_is_off_by_default_and_valid_when_on(casing):
    assert P.ENC1021_PINS_ON is False
    with_pins = E.make_casing(pins=True).val()
    assert with_pins.isValid() and len(with_pins.Solids()) == 1
    assert with_pins.Volume() > casing.Volume()
    # pin: Ø2.0 on the tab, 1.2 long, ends inside the PCB (1.6 thick)
    assert with_pins.Volume() - casing.Volume() == pytest.approx(4 * math.pi * 1.0 ** 2 * C0.pin_len, rel=0.05)
