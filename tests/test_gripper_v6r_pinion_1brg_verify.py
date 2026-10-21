"""
INDEPENDENT verification of exports/step/gripper_v6r_pinion_1brg.step (+ .stl).

Written by the geometry-verifier, not the implementer.  It does NOT import cad/parts/gripper_v6r_pinion_bearing.py or
cad/parts/gripper_v6r_gears.py for any measurement; the only repo code used is the read-only STEP loader
(cad/v6_loader.py) and the placement numbers in cad/params.py.  The part under test is the exported STEP / STL file itself.
verification/gripper_v6r_pinion_1brg_numbers.json is NOT read.

Reference solids (all from solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP):
  pinion   Simple_18T_Pinionvlast   (homed by translation only: bore axis on z, stack bottom z = 0)
  donor    06_compound_54T_24T      (homed the same way; lower layer = z 0..7 one-bearing pocket, floor z = 7.0)

Run: /usr/bin/python3 -m pytest -q tests/test_gripper_v6r_pinion_1brg_verify.py
Set VERIFY_DUMP=<path.json> to dump every measured number.
"""

from __future__ import annotations

import json
import math
import os
import struct

import numpy as np
import pytest

cq = pytest.importorskip("cadquery")

from OCP.BRepAdaptor import BRepAdaptor_Surface           # noqa: E402
from OCP.BRepExtrema import BRepExtrema_DistShapeShape    # noqa: E402
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane  # noqa: E402

from cad import params as P                                # noqa: E402
from cad.v6_loader import V6_STEP, find, load_v6           # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEP_PIN = os.path.join(REPO, "exports", "step", "gripper_v6r_pinion_1brg.step")
STL_PIN = os.path.join(REPO, "exports", "stl", "gripper_v6r_pinion_1brg.stl")
STEP_COMP = os.path.join(REPO, "exports", "step", "gripper_v6r_compound_36T_24T.step")
STEP_FOLL = os.path.join(REPO, "exports", "step", "gripper_v6r_follower.step")

# ---- requirement numbers (typed here on purpose: they are the acceptance criteria, not measurements) -------------------
R_LIP, LIP_LEN = 7.000, 1.95
R_POCKET, Z_FLOOR = 7.0375, 7.0
POCKET_DEPTH = 5.05
R_OPEN = 4.15
R_BORE = 4.0
Z_CB_TOP, FACE = 12.0, 16.0
N_NOTCH_FILLETS, N_LIP_ARCS, R_FILLET = 16, 8, 0.25
TOL = 1e-3            # mm, profile tolerance of the requirement
TOL_VOL = 1e-3        # mm3, boolean symmetric-difference tolerance
RHO = 1.27            # g/cc
R_COPY = 9.0

MEAS: dict = {}


def vol(s) -> float:
    return float(s.Volume()) if s.Solids() else 0.0


def symdiff(a, b) -> float:
    return vol(a.cut(b)) + vol(b.cut(a))


def bbt(s):
    b = s.BoundingBox()
    return (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)


def cyl_census(shape, rmax=1e9, zmax=1e9):
    """On-axis (axis on z through origin) cylinder faces: list of dict(R, z0, z1, area, cx, cy, mid_deg)."""
    out = []
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() != GeomAbs_Cylinder:
            continue
        c = a.Cylinder()
        loc, d = c.Axis().Location(), c.Axis().Direction()
        if abs(abs(d.Z()) - 1.0) > 1e-6:
            continue
        b = f.BoundingBox()
        if b.zmin > zmax or max(abs(b.xmin), abs(b.xmax), abs(b.ymin), abs(b.ymax)) > rmax:
            continue
        ctr = f.Center()
        out.append(dict(R=c.Radius(), z0=b.zmin, z1=b.zmax, area=f.Area(), cx=loc.X(), cy=loc.Y(),
                        mid_deg=math.degrees(math.atan2(ctr.y, ctr.x)) % 360.0))
    return out


def _home(shape, ref_radius):
    """Translate so the bore axis (cylinder of ref_radius, axis // z) is the z axis and the stack bottom is z = 0."""
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Cylinder and abs(a.Cylinder().Radius() - ref_radius) < 1e-4:
            loc = a.Cylinder().Axis().Location()
            z0 = shape.BoundingBox().zmin
            return shape.moved(cq.Location(cq.Vector(-loc.X(), -loc.Y(), -z0))), (loc.X(), loc.Y(), z0)
    raise RuntimeError("no bore cylinder R%.3f" % ref_radius)


def cyl(r, z0, z1):
    return cq.Solid.makeCylinder(r, z1 - z0, cq.Vector(0, 0, z0))


def cavity(shape, z0, z1, r=R_COPY):
    return cyl(r, z0, z1).cut(shape)


# =============================================================================================================
# fixtures
# =============================================================================================================
@pytest.fixture(scope="module")
def src():
    parts = load_v6()
    pin, pin_o = _home(find(parts, "Simple_18T_Pinionvlast"), R_BORE)
    don, don_o = _home(find(parts, "06_compound_54T_24T"), R_OPEN)
    MEAS["src_origin_pinion"] = pin_o
    MEAS["src_origin_donor"] = don_o
    return pin, don


@pytest.fixture(scope="module")
def pin(src):
    return src[0]


@pytest.fixture(scope="module")
def donor(src):
    return src[1]


@pytest.fixture(scope="module")
def new():
    """The deliverable: the exported STEP, as imported."""
    s = cq.importers.importStep(STEP_PIN)
    assert len(s.vals()) == 1
    return s.val()


@pytest.fixture(scope="module")
def donor_cav(donor):
    """Donor one-bearing pocket as a solid, z -1 .. 7 (lip slab + R7.0375 pocket), inside R9."""
    return cavity(donor, -1.0, Z_FLOOR)


@pytest.fixture(scope="module", autouse=True)
def _dump():
    yield
    p = os.environ.get("VERIFY_DUMP")
    if p:
        with open(p, "w") as f:
            json.dump(MEAS, f, indent=1, default=float)


# =============================================================================================================
# 0. source untouched / donor sanity
# =============================================================================================================
def test_donor_is_his_one_bearing_pocket(donor):
    c = cyl_census(donor, rmax=R_COPY, zmax=Z_FLOOR + 5.0)
    lip = [x for x in c if abs(x["R"] - R_LIP) < 1e-4 and x["z1"] < 2.5]
    pocket = [x for x in c if abs(x["R"] - R_POCKET) < 1e-4 and x["z0"] < 2.5]
    through = [x for x in c if abs(x["R"] - R_OPEN) < 1e-4]
    assert lip and pocket and through
    assert min(x["z0"] for x in lip) == pytest.approx(0.0, abs=1e-4) and max(x["z1"] for x in lip) == pytest.approx(LIP_LEN, abs=1e-4)
    assert min(x["z0"] for x in pocket) == pytest.approx(LIP_LEN, abs=1e-4)
    assert max(x["z1"] for x in pocket) == pytest.approx(Z_FLOOR, abs=1e-4)
    assert min(x["z0"] for x in through) == pytest.approx(Z_FLOOR, abs=1e-4)      # D8.30 opening starts at the floor
    MEAS["donor_lower_pocket"] = dict(lip_R=lip[0]["R"], lip_z=(min(x["z0"] for x in lip), max(x["z1"] for x in lip)),
                                      pocket_R=pocket[0]["R"], pocket_z=(min(x["z0"] for x in pocket), max(x["z1"] for x in pocket)),
                                      opening_R=through[0]["R"], opening_z0=min(x["z0"] for x in through))
    # the UPPER pocket of the compound is the two-bearing one (10.05 deep) - make sure we compare with the lower, 5.05-deep one
    up = [x for x in cyl_census(donor, rmax=R_COPY) if abs(x["R"] - R_POCKET) < 1e-4 and x["z0"] > 10.0]
    assert up and (max(x["z1"] for x in up) - min(x["z0"] for x in up)) == pytest.approx(10.05, abs=1e-3)


def test_source_step_not_modified():
    import hashlib
    h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
    before = h(V6_STEP)
    load_v6()
    assert h(V6_STEP) == before
    import subprocess
    r = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--", "solidworks"], capture_output=True, text=True)
    assert r.stdout.strip() == ""


# =============================================================================================================
# 1. pocket profile vs donor, within 0.001 mm
# =============================================================================================================
def test_1_profile_numbers_measured_from_the_exported_step(new, donor):
    c = cyl_census(new, rmax=R_COPY, zmax=Z_CB_TOP + 0.5)
    on_axis = [x for x in c if math.hypot(x["cx"], x["cy"]) < 1e-3]
    rows = {}

    def one(name, R, z0, z1):
        m = [x for x in on_axis if abs(x["R"] - R) < TOL and abs(x["z0"] - z0) < TOL and abs(x["z1"] - z1) < TOL]
        rows[name] = [(x["R"], x["z0"], x["z1"]) for x in m]
        assert m, "%s: no on-axis cylinder R%.4f z %.3f..%.3f in %s" % (name, R, z0, z1, sorted((round(x["R"], 4), round(x["z0"], 3), round(x["z1"], 3)) for x in on_axis))
        return m

    lip = [x for x in on_axis if abs(x["R"] - R_LIP) < TOL]
    assert len(lip) == N_LIP_ARCS, len(lip)
    for x in lip:
        assert abs(x["z0"] - 0.0) < TOL and abs(x["z1"] - LIP_LEN) < TOL
    rows["lip_arcs"] = [(x["R"], x["z0"], x["z1"]) for x in lip]
    one("pocket_D14.075", R_POCKET, LIP_LEN, Z_FLOOR)
    one("opening_D8.30", R_OPEN, Z_FLOOR, Z_CB_TOP)
    one("servo_bore_D8.00", R_BORE, Z_CB_TOP, FACE)
    # no other on-axis cylinder in the region (nothing extra was cut)
    known = len(lip) + sum(len(v) for k, v in rows.items() if k != "lip_arcs")
    assert len(on_axis) == known, sorted((round(x["R"], 4), round(x["z0"], 3), round(x["z1"], 3)) for x in on_axis)
    MEAS["new_profile_cylinders"] = rows
    # relief notches: R0.25 cylinders
    fil = [x for x in c if abs(x["R"] - R_FILLET) < TOL]
    assert len(fil) == N_NOTCH_FILLETS, len(fil)
    for x in fil:
        assert abs(x["z0"]) < TOL and abs(x["z1"] - LIP_LEN) < TOL
    # donor fillets (his STEP splits some R0.25 faces at seams: group by axis and sum the areas)
    def by_axis(rows):
        g = {}
        for x in rows:
            k = (round(x["cx"], 3), round(x["cy"], 3))
            g[k] = g.get(k, 0.0) + x["area"]
        return g
    dc = [x for x in cyl_census(donor, rmax=R_COPY, zmax=LIP_LEN + 0.1) if abs(x["R"] - R_FILLET) < TOL]
    gn, gd = by_axis(fil), by_axis(dc)
    assert len(gn) == len(gd) == N_NOTCH_FILLETS
    kn, kd = sorted(gn), sorted(gd)
    dmax = max(math.hypot(p[0] - q[0], p[1] - q[1]) for p, q in zip(kn, kd))
    dar = max(abs(gn[p] - gd[q]) for p, q in zip(kn, kd))
    MEAS["fillet_axis_max_dev_mm"], MEAS["fillet_area_max_dev_mm2"] = dmax, dar
    assert dmax < TOL and dar < TOL
    # 16 fillet axes = 8 relief notches (axes pair up across each notch)
    left = list(kn)
    gaps = []
    while left:
        p = left.pop(0)
        j = min(range(len(left)), key=lambda i: math.hypot(left[i][0] - p[0], left[i][1] - p[1]))
        q = left.pop(j)
        gaps.append(math.hypot(q[0] - p[0], q[1] - p[1]))
    MEAS["notch_count"], MEAS["notch_axis_pitch_mm"] = len(gaps), gaps
    assert len(gaps) == 8
    # lip arcs: total R7.000 cylinder area and angular coverage equal the donor's (his faces may be seam-split)
    dl = [x for x in cyl_census(donor, rmax=R_COPY, zmax=LIP_LEN + 0.1) if abs(x["R"] - R_LIP) < TOL]
    a_new, a_don = sum(x["area"] for x in lip), sum(x["area"] for x in dl)
    MEAS["lip_arc_area_new_donor"] = (a_new, a_don, len(lip), len(dl))
    assert a_new == pytest.approx(a_don, abs=TOL)
    dang = max(min(abs(((p["mid_deg"] - q["mid_deg"] + 180) % 360) - 180) for q in dl) for p in lip)
    MEAS["lip_arc_mid_angle_dev_deg"] = dang
    assert len(dl) >= N_LIP_ARCS
    if len(dl) == len(lip):
        assert dang * math.pi / 180.0 * R_LIP < TOL
    # notch outer extent (max radius of the section at z = 1)
    MEAS["fillet_axis_radii"] = sorted(round(math.hypot(x["cx"], x["cy"]), 4) for x in fil)


def test_1_floor_is_flat_plane_with_D830_opening(new):
    floor = []
    for f in new.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() != GeomAbs_Plane:
            continue
        b = f.BoundingBox()
        if abs(b.zmin - Z_FLOOR) < 1e-4 and abs(b.zmax - Z_FLOOR) < 1e-4 and max(abs(b.xmin), abs(b.xmax)) < R_COPY:
            floor.append(f)
    assert len(floor) == 1
    f = floor[0]
    expect = math.pi * (R_POCKET ** 2 - R_OPEN ** 2)
    MEAS["floor_area_mm2"] = (f.Area(), expect)
    assert f.Area() == pytest.approx(expect, abs=TOL)           # flat annulus R4.15..R7.0375 -> no chamfer / fillet / cone
    assert len(f.Wires()) == 2
    # ledge at z = 1.95 : annulus R7.0 .. R7.0375 plus the 8 notch pockets?  just check it is planar and at 1.95
    ledge = [g for g in new.Faces() if BRepAdaptor_Surface(g.wrapped).GetType() == GeomAbs_Plane and abs(g.BoundingBox().zmin - LIP_LEN) < 1e-4
             and abs(g.BoundingBox().zmax - LIP_LEN) < 1e-4 and max(abs(g.BoundingBox().xmin), abs(g.BoundingBox().xmax)) < 9.0]
    assert ledge
    # nothing but planes and cylinders in the pocket zone
    bad = []
    for g in new.Faces():
        bb = g.BoundingBox()
        if bb.zmin > Z_CB_TOP + 0.5 or max(abs(bb.xmin), abs(bb.xmax), abs(bb.ymin), abs(bb.ymax)) > R_COPY:
            continue
        t = BRepAdaptor_Surface(g.wrapped).GetType()
        if t not in (GeomAbs_Plane, GeomAbs_Cylinder):
            bad.append(str(t))
    assert not bad, bad


def test_1_cavity_equals_donor_cavity(new, donor_cav):
    cn = cavity(new, -1.0, Z_FLOOR)
    sd = symdiff(cn, donor_cav)
    MEAS["pocket_cavity_vol_new_donor_symdiff"] = (vol(cn), vol(donor_cav), sd)
    assert vol(cn) == pytest.approx(vol(donor_cav), abs=TOL_VOL)
    assert sd < TOL_VOL
    # opening: z 7 .. 12 empty space inside R9 must be exactly the R4.15 cylinder
    co = cavity(new, Z_FLOOR, Z_CB_TOP)
    sd2 = symdiff(co, cyl(R_OPEN, Z_FLOOR, Z_CB_TOP))
    MEAS["opening_symdiff_mm3"] = sd2
    assert sd2 < TOL_VOL


# =============================================================================================================
# 2. removed material (boolean against his pinion)
# =============================================================================================================
def test_2_removed_material_is_only_pocket_and_counterbore(pin, new, donor, donor_cav):
    rem, add = pin.cut(new), new.cut(pin)
    v_add = vol(add)
    v_rem = vol(rem)
    MEAS["added_mm3"], MEAS["removed_mm3"] = v_add, v_rem
    MEAS["pinion_vol"], MEAS["new_vol"] = pin.Volume(), new.Volume()
    assert v_add < TOL_VOL
    assert v_rem == pytest.approx(pin.Volume() - new.Volume(), abs=TOL_VOL)
    b = bbt(rem)
    MEAS["removed_bbox"] = b
    assert b[4] >= -1e-4 and b[5] == pytest.approx(Z_CB_TOP, abs=1e-4)
    assert max(abs(b[0]), abs(b[1]), abs(b[2]), abs(b[3])) < R_COPY
    # expected removed volume, built independently: (donor cavity z 0..7 U cylinder R4.15 z 0..12) ^ pinion
    expect_region = donor_cav.fuse(cyl(R_OPEN, -1.0, Z_CB_TOP)).clean()
    expect = pin.intersect(expect_region)
    sd = symdiff(rem, expect)
    MEAS["removed_vs_expected_symdiff_mm3"] = (v_rem, vol(expect), sd)
    assert sd < TOL_VOL
    # independent reconstruction of the whole part: pinion minus expected region == the exported part
    rebuilt = pin.cut(expect_region)
    sd3 = symdiff(rebuilt, new)
    MEAS["rebuilt_vs_exported_symdiff_mm3"] = sd3
    assert sd3 < TOL_VOL


def test_2_teeth_servo_bore_and_outside_identical(pin, new):
    # (a) outside the cylinder R9 x z -1..12 nothing changed, (b) inside R9 above z = 12 nothing changed (bore, face)
    outside = cq.Solid.makeCylinder(60.0, FACE + 2.0, cq.Vector(0, 0, -1.0)).cut(cyl(R_COPY, -1.0, Z_CB_TOP))
    d1 = symdiff(pin.intersect(outside), new.intersect(outside))
    top = cyl(R_COPY, Z_CB_TOP, FACE + 1.0)
    d2 = symdiff(pin.intersect(top), new.intersect(top))
    MEAS["outside_symdiff_mm3"], MEAS["above_z12_symdiff_mm3"] = d1, d2
    assert d1 < TOL_VOL and d2 < TOL_VOL
    # D8.00 servo bore z 12..16 intact, and no R4.00 left below z = 12
    c = [x for x in cyl_census(new, rmax=R_COPY) if abs(x["R"] - R_BORE) < TOL]
    assert len(c) >= 1
    assert min(x["z0"] for x in c) == pytest.approx(Z_CB_TOP, abs=TOL) and max(x["z1"] for x in c) == pytest.approx(FACE, abs=TOL)
    assert sum(x["area"] for x in c) == pytest.approx(2 * math.pi * R_BORE * (FACE - Z_CB_TOP), abs=TOL)
    # his tooth surfaces: non-planar face area outside R9.5 identical
    def outer(s):
        t = 0.0
        for f in s.Faces():
            if BRepAdaptor_Surface(f.wrapped).GetType() == GeomAbs_Plane:
                continue
            b = f.BoundingBox()
            if max(abs(b.xmin), abs(b.xmax), abs(b.ymin), abs(b.ymax)) > 9.5:
                t += f.Area()
        return t
    MEAS["tooth_area_new_pin"] = (outer(new), outer(pin))
    assert outer(new) == pytest.approx(outer(pin), abs=TOL)


# =============================================================================================================
# 3. walls
# =============================================================================================================
def _section_wires(shape, z):
    slab = cq.Solid.makeCylinder(40.0, 0.02, cq.Vector(0, 0, z)).intersect(shape)
    faces = [f for f in slab.Faces() if BRepAdaptor_Surface(f.wrapped).GetType() == GeomAbs_Plane
             and abs(f.BoundingBox().zmin - z) < 1e-6 and abs(f.BoundingBox().zmax - z) < 1e-6]
    assert len(faces) == 1
    return faces[0].outerWire(), faces[0].innerWires()


def _samples(wire, step=0.004):
    """Dense points on a wire (about one point per `step` mm), (N, 2) array.  BRepExtrema vertex-to-wire proved unreliable
    on the tooth outline (returned 12.29 for a 11.625 root), so distances are taken between dense samples."""
    pts = []
    for e in wire.Edges():
        n = max(8, int(e.Length() / step))
        for t in np.linspace(0.0, 1.0, n):
            q = e.positionAt(t)
            pts.append((q.x, q.y))
    return np.array(pts)


def _wall_numbers(new):
    from scipy.spatial import cKDTree
    out4, inn4 = _section_wires(new, 4.0)
    assert len(inn4) == 1
    o4, i4 = _samples(out4), _samples(inn4[0])
    root_r = float(np.hypot(o4[:, 0], o4[:, 1]).min())
    pocket_r = float(np.hypot(i4[:, 0], i4[:, 1]).max())
    wall_pocket = float(cKDTree(o4).query(i4)[0].min())
    out1, inn1 = _section_wires(new, 1.0)
    assert len(inn1) == 1
    o1, i1 = _samples(out1), _samples(inn1[0])
    notch_r = float(np.hypot(i1[:, 0], i1[:, 1]).max())
    wall_notch = float(cKDTree(o1).query(i1)[0].min())
    ax = max(np.abs(i1[:, 0]).max(), np.abs(i1[:, 1]).max())
    return dict(root_r=root_r, pocket_r=pocket_r, wall_pocket=wall_pocket, notch_outer_r=notch_r, notch_outer_axis_aligned_extent=float(ax),
                wall_notch=wall_notch, wall_notch_root_minus_notch_r=root_r - notch_r)


def test_3_wall_pocket_to_root_circle(new):
    w = _wall_numbers(new)
    MEAS["walls"] = w
    assert w["root_r"] == pytest.approx(11.625, abs=2e-3)              # 18T, m1.5: 13.5 - 1.25*1.5
    assert w["pocket_r"] == pytest.approx(R_POCKET, abs=2e-3)
    assert w["wall_pocket"] == pytest.approx(4.5875, abs=0.005)         # about 4.59


def test_3_wall_at_notches_is_consistent_with_notch_geometry(new):
    w = _wall_numbers(new)
    # the true largest radius of the relief notch is fillet-axis radius + 0.25, not the axis-aligned bbox extent
    assert w["notch_outer_r"] == pytest.approx(7.6663 + R_FILLET, abs=2e-3)
    assert w["wall_notch"] == pytest.approx(w["wall_notch_root_minus_notch_r"], abs=0.01)


def test_3_wall_at_notches_at_least_3p83(new):
    """The 3.83 mm figure was the implementer's mis-measured claim (R7.80 is the notch's X/Y bbox extent; its largest
    radius is 7.916, so the true wall to the root circle is 3.709 mm, as the verifier found).  Lead decision: the design
    requirement is the 1.2 mm minimum wall; the claim is corrected to the measured 3.709 mm.  The test now pins the
    measured value and the real requirement."""
    w = _wall_numbers(new)
    MEAS["walls_notch_requirement"] = (w["wall_notch"], 1.2)
    assert w["wall_notch"] == pytest.approx(3.709, abs=0.01), w
    assert w["wall_notch"] >= 1.2, w


# =============================================================================================================
# 4. single valid solid, STEP round trip, STL
# =============================================================================================================
def test_4_step_valid_single_solid_and_roundtrip(new, pin, tmp_path):
    assert new.isValid() and len(new.Solids()) == 1 and len(new.Shells()) == 1
    b = bbt(new)
    assert b[4] == pytest.approx(0.0, abs=1e-5) and b[5] == pytest.approx(FACE, abs=1e-5)
    assert bbt(new) == pytest.approx(bbt(pin), abs=1e-4)                    # same envelope as his pinion
    MEAS["step_bbox"], MEAS["step_vol"], MEAS["step_area"] = b, new.Volume(), new.Area()
    # re-export and re-import: bbox / volume / geometry agreement
    p = str(tmp_path / "rt.step")
    cq.exporters.export(cq.Workplane(obj=new), p)
    re = cq.importers.importStep(p).val()
    assert re.isValid() and len(re.Solids()) == 1
    assert re.Volume() == pytest.approx(new.Volume(), rel=1e-8)
    assert bbt(re) == pytest.approx(bbt(new), abs=1e-6)
    assert symdiff(re, new) < TOL_VOL
    MEAS["roundtrip_vol_delta"] = re.Volume() - new.Volume()


def _read_stl(path):
    raw = open(path, "rb").read()
    n = struct.unpack("<I", raw[80:84])[0]
    assert len(raw) == 84 + 50 * n, "not a binary STL of the stated size"
    rec = np.frombuffer(raw[84:], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=n)
    return rec["v"].astype(np.float64), rec["n"].astype(np.float64)


def test_4_stl_closed_manifold_and_printed_pocket_up(new):
    tri, nrm = _read_stl(STL_PIN)
    n = len(tri)
    pts = tri.reshape(-1, 3)
    q = np.round(pts / 1e-4).astype(np.int64)
    uniq, inv = np.unique(q, axis=0, return_inverse=True)
    idx = inv.reshape(-1, 3)
    de = np.concatenate([idx[:, [0, 1]], idx[:, [1, 2]], idx[:, [2, 0]]])
    code = de[:, 0].astype(np.int64) * len(uniq) + de[:, 1]
    rcode = de[:, 1].astype(np.int64) * len(uniq) + de[:, 0]
    cu, cc = np.unique(code, return_counts=True)
    assert cc.max() == 1, "directed edge used twice (non-manifold / inconsistent orientation)"
    assert np.isin(rcode, cu).all(), "open edge: some edge has no opposite partner (hole in the mesh)"
    # connected components (faces joined through shared vertices)
    parent = np.arange(len(uniq))

    def find_(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b, c in idx:
        ra, rb, rc = find_(a), find_(b), find_(c)
        parent[rb] = ra
        parent[find_(rc)] = ra
    ncomp = len({find_(i) for i in range(len(uniq))})
    v0, v1, v2 = tri[:, 0], tri[:, 1], tri[:, 2]
    svol = float(np.einsum("ij,ij->i", v0, np.cross(v1, v2)).sum() / 6.0)
    area = float(np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1).sum() / 2.0)
    lo, hi = pts.min(0), pts.max(0)
    MEAS["stl"] = dict(triangles=n, vertices=len(uniq), components=ncomp, signed_volume=svol, area=area, bbox_min=lo.tolist(), bbox_max=hi.tolist())
    assert ncomp == 1
    MEAS["stl"]["euler_V_E_F"] = (len(uniq), len(cu) // 2, n, len(uniq) - len(cu) // 2 + n)   # 0 = torus (the bore goes through)
    assert svol > 0
    assert svol == pytest.approx(new.Volume(), rel=0.005)                   # tessellation tolerance
    assert area == pytest.approx(new.Area(), rel=0.005)
    # print pose: lowest point z = 0, height 16
    assert lo[2] == pytest.approx(0.0, abs=1e-4) and hi[2] == pytest.approx(FACE, abs=1e-3)
    # pocket UP : area of up-facing triangles in the top plane (z = 16) equals the STEP pocket-mouth face (z = 0 in STEP frame),
    # area in the bed plane equals the STEP servo face (z = 16 in STEP frame)
    def plane_area(zv, sign):
        m = (np.abs(tri[:, :, 2] - zv) < 1e-3).all(1) & (nrm[:, 2] * sign > 0.9)
        return float(np.linalg.norm(np.cross(v1[m] - v0[m], v2[m] - v0[m]), axis=1).sum() / 2.0)

    def step_plane_area(zv):
        return sum(f.Area() for f in new.Faces() if BRepAdaptor_Surface(f.wrapped).GetType() == GeomAbs_Plane
                   and abs(f.BoundingBox().zmin - zv) < 1e-4 and abs(f.BoundingBox().zmax - zv) < 1e-4)
    top, bed = plane_area(FACE, +1), plane_area(0.0, -1)
    MEAS["stl_top_bed_area"] = (top, bed, step_plane_area(0.0), step_plane_area(FACE))
    assert top == pytest.approx(step_plane_area(0.0), rel=0.002)           # pocket mouth face is on TOP
    assert bed == pytest.approx(step_plane_area(FACE), rel=0.002)          # D8 bore face is on the bed
    assert top < bed - 100.0
    # pocket floor (z = 16 - 7 = 9, normal +z) and ledge (z = 16 - 1.95)
    floor = plane_area(FACE - Z_FLOOR, +1)
    assert floor == pytest.approx(math.pi * (R_POCKET ** 2 - R_OPEN ** 2), rel=0.01)
    assert plane_area(FACE - LIP_LEN, +1) > 1.0


# =============================================================================================================
# 5. mass
# =============================================================================================================
def test_5_mass(new, pin):
    m = new.Volume() * RHO / 1000.0
    m_his = pin.Volume() * RHO / 1000.0
    tri, _ = _read_stl(STL_PIN)
    sv = float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6.0)
    MEAS["mass_g"] = dict(step=m, pinion_his=m_his, stl=sv * RHO / 1000.0)
    assert m == pytest.approx(9.22, abs=0.01)
    assert m < m_his
    assert sv * RHO / 1000.0 == pytest.approx(9.22, abs=0.05)


# =============================================================================================================
# 6. meshing with the 36T compound (exports) at 40.80 mm, sweep
# =============================================================================================================
def _place(shape, xy, deg):
    return shape.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), deg).moved(cq.Location(cq.Vector(xy[0], xy[1], 0.0)))


@pytest.fixture(scope="module")
def gears(new):
    comp = cq.importers.importStep(STEP_COMP).val()
    foll = cq.importers.importStep(STEP_FOLL).val()
    return comp, foll


def test_6_mesh_zero_overlap_sweep(new, gears):
    comp, foll = gears
    sx, sy = P.GRIPV6R_S_XY
    cx, cy = P.GRIPV6R_C_XY
    fx, fy = P.GRIPV6R_F_XY
    cd = math.hypot(sx - cx, sy - cy)
    MEAS["centre_distance"] = cd
    assert cd == pytest.approx(40.80, abs=1e-6)
    # the exported compound's axis is at the origin (bore R4.15 on z) -> placement by translation is valid
    for f in comp.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Cylinder and abs(a.Cylinder().Radius() - R_OPEN) < 1e-4:
            loc = a.Cylinder().Axis().Location()
            assert math.hypot(loc.X(), loc.Y()) < 1e-3
            break
    else:
        pytest.fail("compound bore not found")
    ratio = P.GRIPV6R_Z_MAIN / P.GRIPV6R_Z_PINION
    assert ratio == pytest.approx(2.0)
    deltas = [-30.0, -15.0, 0.0, 7.5, 15.0, 30.0, 45.0, 60.0, P.GRIPV6R_SWEEP_DEG]
    rows = []
    for d in deltas:
        pp = _place(new, (sx, sy), -ratio * d)
        o1 = vol(pp.intersect(_place(comp, (cx, cy), d)))
        o2 = vol(pp.intersect(_place(foll, (fx, fy), -d)))
        rows.append(dict(delta=d, pinion_x_compound=o1, pinion_x_follower=o2))
    MEAS["mesh_rows"] = rows
    for r in rows:
        assert r["pinion_x_compound"] < 1e-6 and r["pinion_x_follower"] < 1e-6, r


def test_6_mesh_positive_control_and_clearance(new, gears):
    comp, _ = gears
    sx, sy = P.GRIPV6R_S_XY
    cx, cy = P.GRIPV6R_C_XY
    ov = vol(_place(new, (sx, sy), 3.0).intersect(_place(comp, (cx, cy), 0.0)))      # 3 deg off the window must collide
    MEAS["mesh_control_overlap_mm3"] = ov
    assert ov > 1.0
    # minimum distance between the two solids at a few poses (exact, BRepExtrema)
    ratio = 2.0
    dist = []
    for d in (0.0, 30.0, 60.0):
        dd = BRepExtrema_DistShapeShape(_place(new, (sx, sy), -ratio * d).wrapped, _place(comp, (cx, cy), d).wrapped)
        dd.Perform()
        dist.append((d, dd.Value()))
    MEAS["mesh_min_distance"] = dist
    assert all(v > 0.0 for _, v in dist)


# =============================================================================================================
# 7. engineering note: 687 floor opening vs inner-ring land (ASSUMPTIONS, not fit/fail items)
# =============================================================================================================
LAND_OD = (8.5, 9.0)        # ASSUMED 687 inner-ring land OD range, mm (no source in the repo; only 'VERIFY race OD ~9' comments)
SHOULDER_ID = (11.5, 12.5)  # ASSUMED 687 outer-ring shoulder ID range, mm


def test_7_engineering_note_floor_opening_vs_inner_ring(new, donor):
    # opening radius of THIS part and of BOTH of his floors (lower one-bearing floor z=7, upper two-bearing floor z=?)
    pr = R_OPEN
    d_rows = [x for x in cyl_census(donor, rmax=R_COPY) if abs(x["R"] - R_OPEN) < 1e-4]
    assert d_rows
    MEAS["note"] = {}
    for lo_od in LAND_OD:
        band = lo_od / 2.0 - pr                                  # radial overlap floor annulus over the inner ring face
        area = math.pi * ((lo_od / 2.0) ** 2 - pr ** 2)
        MEAS["note"]["land_%.1f" % lo_od] = dict(overlap_radial_mm=band, overlap_area_mm2=area)
        assert band > 0.0                                        # opening D8.30 is SMALLER than the land -> floor touches the inner ring
    # contact-with-outer-ring-only window: opening D >= land OD (+margin) and D <= outer shoulder ID
    d_min, d_max = max(LAND_OD), min(SHOULDER_ID)
    MEAS["note"]["opening_window_D_mm"] = (d_min, d_max)
    MEAS["note"]["donor_opening_D"] = 2 * d_rows[0]["R"]
    assert 2 * pr < min(LAND_OD) and d_min < d_max
    # his compound has the SAME opening at BOTH floors: the R4.15 bore runs from the lower floor (z = 7) to the upper floor (z = 24)
    z0 = min(x["z0"] for x in d_rows)
    z1 = max(x["z1"] for x in d_rows)
    MEAS["note"]["donor_opening_z_span"] = (z0, z1)
    assert z0 == pytest.approx(7.0, abs=1e-3) and z1 == pytest.approx(24.0, abs=1e-3)
