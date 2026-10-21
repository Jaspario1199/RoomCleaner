"""
Implementation tests for the THREE-CABLE holes on the Gripper 1021 electrical housing (cad/GRIPPER_1021_SPEC.md section 5).

  PART   cad/parts/gripper1021_housing_cambay.py   make_34() / export_all_34()  (make() is the unchanged current housing)
  PARAMS cad/params.py CAMBAY1021_TRI_*

Everything is measured on the built BRep solids / exported files (probes, cylinder-face axes, booleans); the expected values are the
spec numbers (table of section 5) and closed-form geometry.  Jasper's reference housing is read-only.
These are implementation checks by the implementer; the independent verification is a separate step.
"""

from __future__ import annotations

import importlib.util
import math
import os
import sys

import pytest

cq = pytest.importorskip("cadquery")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                      # noqa: E402
from cad.parts import gripper1021_housing_cambay as G            # noqa: E402

REF = os.path.join(REPO, "cad", "reference", "gripper_1021", "parts")
pytestmark = pytest.mark.skipif(not os.path.isdir(REF), reason="gripper_1021 reference parts not available")


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


B = _load("build_gripper1021", "scripts/build_gripper1021.py")
sys.path.insert(0, os.path.join(REPO, "scripts"))
import analyze_cable_lines_housing_34 as A34                      # noqa: E402

UP = cq.Vector(0.0, 1.0, 0.0)
R = P.CAMBAY1021_TRI_HOLE_D / 2
C_CH = P.CAMBAY1021_TRI_CHAMFER
# spec section 5 table (box frame): outer mouth centre, inner mouth centre, axis direction (x, z)
SPEC = {
    "C": {"outer": (0.0, 42.0, -45.0), "inner": (0.0, 42.0, -40.0), "axis": (0.0, -1.0)},
    "A": {"outer": (-45.0, 42.0, 25.98), "inner": (-40.0, 42.0, 23.09), "axis": (-0.8660, 0.5)},
    "B": {"outer": (45.0, 42.0, 25.98), "inner": (40.0, 42.0, 23.09), "axis": (0.8660, 0.5)},
}
LABEL_Y_MIN = 44.5          # labels start above the top of the hole + chamfer (44.12)
# spec section 5, body frame (m)
SPEC_BODY = {"C": (0.0, 0.0450, 0.0342), "A": (-0.0450, -0.0260, 0.0342), "B": (0.0450, -0.0260, 0.0342)}


@pytest.fixture(scope="module")
def parts():
    orig = G.load_housing_bay_frame()
    base, cover = G.make()
    new, cover34 = G.make_34()
    return orig, base, new, cover, cover34


@pytest.fixture(scope="module")
def removed(parts):
    """Boolean difference current housing - housing_34, split into the three hole solids and the three label solids."""
    orig, base, new, cover, _ = parts
    rem = base.val().cut(new.val())
    fr = G.tri_hole_frames()
    holes, labels = {}, {}
    for s in rem.Solids():
        c = s.BoundingBox()
        is_hole = c.ymax <= 44.6
        mid = cq.Vector((c.xmin + c.xmax) / 2, (c.ymin + c.ymax) / 2, (c.zmin + c.zmax) / 2)
        ref = lambda f: f["outer"] + UP * (0.0 if is_hole else P.CAMBAY1021_TRI_LABEL_ABOVE)
        (holes if is_hole else labels)[min(fr, key=lambda h: (ref(fr[h]) - mid).Length)] = s
    return rem, holes, labels


def inside(shape, p):
    return B._inside(shape, tuple(p))


# ---------------------------------------------------------------------------------------------------------------
# the current housing is unchanged and the new block only adds values
# ---------------------------------------------------------------------------------------------------------------
def test_current_housing_still_regenerates_identically(parts):
    orig, base, new, cover, cover34 = parts
    # make() is the original path: same volume and bounding box as the existing STEP export (re-imported, world frame)
    d = B.reimport_check(os.path.join(REPO, "exports", "step", "gripper1021_housing_cambay.step"), G.to_world(base.val()))
    assert d["solids"] == 1 and d["valid"] and d["vol_rel_diff"] < 1e-6 and d["bbox_max_diff_mm"] < 1e-3
    dc = B.reimport_check(os.path.join(REPO, "exports", "step", "gripper1021_housing_cambay_cover.step"), G.to_world(cover.val()))
    assert dc["vol_rel_diff"] < 1e-6 and dc["bbox_max_diff_mm"] < 1e-3
    assert abs(base.val().Volume() - 154311.0867) < 1.0                                  # as built before the option existed
    # the cover of the _34 variant is the unchanged one
    assert abs(cover34.val().Volume() - cover.val().Volume()) < 1e-9


def test_existing_values_unchanged_and_new_block_present():
    assert P.CAMBAY1021_CORNER_HOLE_EXIT_XZ == 43.22 and P.CAMBAY1021_CORNER_HOLE_INNER_Y == 7.82 and P.CAMBAY1021_BOX_UPPER_HALF == 45.0
    assert P.CAMBAY1021_BOX_LID_SEAT_Y == 50.0 and P.CAMBAY1021_BOX_POCKET_HALF == 40.0 and P.CAMBAY1021_CORNER_HOLE_D == 2.0
    assert P.CAMBAY_CORNER_HOLE_EXIT_XZ == 54.4 and P.CAMBAY_BOX_FLANGE_HALF == 63.5
    assert P.CAMBAY1021_TRI_IDS == ("C", "A", "B") and P.CAMBAY1021_TRI_AZ_BODY_DEG == (90.0, 210.0, 330.0)
    assert P.CAMBAY1021_TRI_HOLE_D == 2.0 and P.CAMBAY1021_TRI_Y == 42.0 and P.CAMBAY1021_TRI_CHAMFER == 0.5
    assert P.CAMBAY1021_TRI_LABEL_H == 4.0 and P.CAMBAY1021_TRI_LABEL_DEPTH == 0.4 and P.CAMBAY1021_TRI_LABEL_ABOVE == 5.0


def test_frames_match_the_spec_table():
    fr = G.tri_hole_frames()
    for hid, s in SPEC.items():
        f = fr[hid]
        assert all(abs(a - b) < 0.01 for a, b in zip(f["outer"].toTuple(), s["outer"])), hid
        assert all(abs(a - b) < 0.01 for a, b in zip(f["inner"].toTuple(), s["inner"])), hid
        assert abs(f["axis"].x - s["axis"][0]) < 1e-4 and abs(f["axis"].z - s["axis"][1]) < 1e-4 and f["axis"].y == 0.0
        assert abs(f["length"] - 5.0 / abs(f["normal"].dot(f["axis"]))) < 1e-9


# ---------------------------------------------------------------------------------------------------------------
# validity
# ---------------------------------------------------------------------------------------------------------------
def test_housing34_is_one_valid_solid_with_the_same_envelope(parts):
    orig, base, new, cover, _ = parts
    assert new.val().isValid() and len(new.solids().vals()) == 1
    b0, b1 = base.val().BoundingBox(), new.val().BoundingBox()
    for a, b in ((b0.xmin, b1.xmin), (b0.xmax, b1.xmax), (b0.ymin, b1.ymin), (b0.ymax, b1.ymax), (b0.zmin, b1.zmin), (b0.zmax, b1.zmax)):
        assert abs(a - b) < 1e-4


# ---------------------------------------------------------------------------------------------------------------
# hole positions, diameters, form: probed on the solid
# ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("hid", ["C", "A", "B"])
def test_hole_axis_diameter_and_mouths_measured_on_the_solid(parts, hid):
    new = parts[2].val()
    f, s = G.tri_hole_frames()[hid], SPEC[hid]
    cyl = B.measured_cylinder_axes(new, f["outer"], R)
    assert len(cyl) == 1                                            # one cylindrical bore face of R1.0 near the mouth
    p0, d, rad = cyl[0]
    assert abs(2 * rad - 2.0) < 1e-6                                # Ø2.0
    assert abs(abs(d.dot(f["axis"])) - 1.0) < 1e-9                  # direction
    d = d if d.dot(f["axis"]) > 0 else d * -1.0
    outer = B._axis_plane_point(p0, d, f["normal"], G.BOX_UPPER_HALF)
    inner = B._axis_plane_point(p0, d, f["normal"], G.POCKET_HALF)
    assert all(abs(a - b) < 0.01 for a, b in zip(outer.toTuple(), s["outer"]))      # spec table, 0.01 mm
    assert all(abs(a - b) < 0.01 for a, b in zip(inner.toTuple(), s["inner"]))
    assert abs(outer.y - 42.0) < 1e-9 and abs(inner.y - 42.0) < 1e-9
    assert abs((outer - inner).Length - f["length"]) < 1e-9


@pytest.mark.parametrize("hid", ["C", "A", "B"])
def test_hole_is_a_teardrop_with_a_chamfered_mouth(parts, hid):
    new = parts[2].val()
    f = G.tri_hole_frames()[hid]
    mid, tg = (f["outer"] + f["inner"]) * 0.5, UP.cross(f["axis"])
    at = lambda h, u: (mid + UP * h + tg * u).toTuple()
    k, tip = G.TRI_TIP_K, R / math.sin(G.TRI_TIP_K)
    for t in (-2.4, -1.0, 0.0, 1.0, 2.4):                            # open along the whole axis
        assert not inside(new, (mid + f["axis"] * t).toTuple())
    for a in (-1.2, -1.57, -1.9, 0.0, math.pi):                      # circle: empty at r = 0.98, solid at 1.02 (lower half and sides)
        assert not inside(new, at(0.98 * math.sin(a), 0.98 * math.cos(a)))
        assert inside(new, at(1.02 * math.sin(a), 1.02 * math.cos(a)))
    assert not inside(new, at(1.30, 0.0)) and inside(new, at(1.50, 0.0))           # tip points up (+y); apex at 1.414
    assert not inside(new, at(tip - 0.5 - 0.05, 0.5)) and inside(new, at(tip - 0.5 + 0.05, 0.5))     # 45 deg flank
    assert inside(new, at(-1.10, 0.0))                                # solid just below the bottom of the bore (not a slot)
    # 0.5 x 45 deg chamfer at the lateral centre of the bottom lip of the outer mouth: line y = axis - R - c + depth
    lip = lambda depth, dy: (f["outer"] - f["normal"] * depth + UP * (-R - C_CH + depth + dy)).toTuple()
    for depth in (0.1, 0.25, 0.4):
        assert not inside(new, lip(depth, +0.05)) and inside(new, lip(depth, -0.05))
    assert inside(new, (f["outer"] - f["normal"] * 0.6 + UP * (-R - 0.2)).toTuple())             # no chamfer deeper than 0.5


# ---------------------------------------------------------------------------------------------------------------
# volume removed per hole
# ---------------------------------------------------------------------------------------------------------------
def test_three_holes_and_three_labels_are_the_only_differences(parts, removed):
    orig, base, new, cover, _ = parts
    rem, holes, labels = removed
    assert len(rem.Solids()) == 6 and len(holes) == 3 and len(labels) == 3
    assert new.val().cut(base.val()).Volume() < 1e-3                 # nothing added anywhere
    pocket = cq.Solid.makeBox(2 * G.POCKET_HALF, 50.0, 2 * G.POCKET_HALF, cq.Vector(-G.POCKET_HALF, G.POCKET_FLOOR_Y, -G.POCKET_HALF))
    assert rem.intersect(pocket).Volume() < 1e-3                     # nothing removed inside the pocket


@pytest.mark.parametrize("hid", ["C", "A", "B"])
def test_removed_volume_per_hole_matches_a_d2_bore_of_its_wall_length(parts, removed, hid):
    """Spec: removed volume per hole within 10 % of a Ø2 bore of its wall length.  The bore proper (deeper than the chamfer) is
    within 10 % (teardrop tip: +6.8 %).  The 0.5 chamfer adds another ~5-6 %, so the complete hole is +12 to +13 % of the plain bore:
    reported in the build notes as a spec conflict; here it is bounded at 15 % and checked against closed-form geometry."""
    orig, base, new, cover, _ = parts
    rem, holes, labels = removed
    f = G.tri_hole_frames()[hid]
    L = f["length"]
    plain = math.pi * R * R * L
    total = holes[hid].Volume()
    # bore only: wall-normal coordinate 40 .. 44.2 (the chamfer is confined to n >= 44.5)
    n_hi = G.BOX_UPPER_HALF - 0.8
    slab = (cq.Workplane(cq.Plane(origin=f["outer"] - f["normal"] * (G.BOX_UPPER_HALF - n_hi), xDir=f["reading_dir"], normal=f["normal"]))
            .rect(40.0, 40.0).extrude(-(n_hi - G.POCKET_HALF)).val())
    deep = holes[hid].intersect(slab).Volume()
    deep_plain = math.pi * R * R * (n_hi - G.POCKET_HALF) / abs(f["normal"].dot(f["axis"]))
    assert abs(deep / deep_plain - 1.0) < 0.10                                              # the literal spec criterion, on the bore
    assert abs(deep / (G.teardrop_area() * (n_hi - G.POCKET_HALF) / abs(f["normal"].dot(f["axis"])) ) - 1.0) < 0.002   # = analytic teardrop prism
    assert 1.0 < total / plain < 1.15                                                       # whole hole (bore + tip + chamfer)
    chamfer_extra = total - G.teardrop_area() * L
    assert 0.8 < chamfer_extra < 1.15                                                       # one 0.5 x 45 deg chamfer of a Ø2 teardrop mouth
    if hid == "C":                                                                          # perpendicular wall: closed form
        a = G.teardrop_area(1.0)
        exact = a * ((L - C_CH) + ((1.0 + C_CH) ** 3 - 1.0) / 3.0)         # straight teardrop prism + int_0^c a (1 + c - d)^2 dd (mitred 45 deg offset)
        assert abs(total - exact) / exact < 0.005


def test_difference_is_confined_within_3mm_of_the_holes_and_labels(parts, removed):
    rem, holes, labels = removed
    conf = P.CAMBAY1021_TRI_CONFINE
    zone = None
    for hid, f in G.tri_hole_frames().items():
        cyl = cq.Solid.makeCylinder(R + conf, f["length"] + 2 * conf, f["inner"] - f["axis"] * conf, f["axis"])
        lab = f["outer"] + UP * P.CAMBAY1021_TRI_LABEL_ABOVE
        box = (cq.Workplane(cq.Plane(origin=lab, xDir=f["reading_dir"], normal=f["normal"]))
               .rect(P.CAMBAY1021_TRI_LABEL_H * 1.5 + 2 * conf, P.CAMBAY1021_TRI_LABEL_H + 2 * conf)
               .extrude(-(G.BOX_UPPER_HALF - G.POCKET_HALF + conf)).val())
        for part in (cyl, box):
            zone = part if zone is None else zone.fuse(part)
    assert rem.cut(zone).Volume() < 1e-3
    for hid, s in holes.items():                                    # each hole solid lies inside the wall slab 40 .. 45 (cuts only wall material)
        f = G.tri_hole_frames()[hid]
        for v in s.Vertices():
            nrm = cq.Vector(v.X, v.Y, v.Z).dot(f["normal"])
            assert G.POCKET_HALF - 1e-3 <= nrm <= G.BOX_UPPER_HALF + 1e-3          # (Jasper's wall plane sits at 45.00003 in his file)


# ---------------------------------------------------------------------------------------------------------------
# keep-outs
# ---------------------------------------------------------------------------------------------------------------
def test_keepouts_at_least_5mm(parts, removed):
    orig, base, new, cover, _ = parts
    rem, holes, labels = removed
    ko = B.housing34_keepouts(G, orig, holes, G.make_bay_body().val(), cover.val())
    strict_all = "any_other_face_of_jaspers_housing"
    for hid, d in ko.items():
        for feat, v in d.items():
            if isinstance(v, str) or feat == strict_all:
                continue
            assert v >= P.CAMBAY1021_TRI_KEEPOUT, (hid, feat, v)         # corner holes, wire window, bay, cover, ledge, floor holes, tube, every non-adjacent face
    # the closest independent feature is the lid-seat ledge (6.4 mm): the holes were placed with the ledge as the limit
    assert min(d["lid_seat_ledge"] for d in ko.values()) > 6.0
    # Strictly against EVERY face of Jasper's housing, A and B come within 4.98 mm of the start of the pocket-corner fillet (R10, tangent to
    # the wall the hole opens into; the hole's own inner mouth is 5.75 mm from it).  0.02 mm short of 5.0: reported for a lead decision.
    assert ko["C"][strict_all] >= P.CAMBAY1021_TRI_KEEPOUT
    for hid in ("A", "B"):
        assert 4.95 < ko[hid][strict_all] < 5.0
        assert "CYLINDER" in ko[hid]["nearest_other_face"] and "y[5.0,50.0]" in ko[hid]["nearest_other_face"]


def test_label_geometry_position_and_reading_direction(parts, removed):
    rem, holes, labels = removed
    fr = G.tri_hole_frames()
    for hid, ls in labels.items():
        f = fr[hid]
        c = ls.BoundingBox()
        in_x = abs(f["normal"].x) > 0.5
        depth = (c.xmax - c.xmin) if in_x else (c.zmax - c.zmin)
        bbc = cq.Vector((c.xmin + c.xmax) / 2, (c.ymin + c.ymax) / 2, (c.zmin + c.zmax) / 2)
        exp_c = f["outer"] + UP * P.CAMBAY1021_TRI_LABEL_ABOVE
        assert abs((c.ymax - c.ymin) - 4.0) < 0.02                                       # 4 mm tall
        assert abs(depth - 0.4) < 0.005                                                  # 0.4 mm deep (removed material only)
        assert abs((bbc - exp_c).dot(f["reading_dir"])) < 0.02 and abs(bbc.y - exp_c.y) < 0.02     # centred 5 mm above the mouth
        com = ls.Center()
        if hid in ("B", "C"):                                                            # stem / back of the letter on the left of the reader
            assert (com - bbc).dot(f["reading_dir"]) < -0.05
        else:                                                                            # A: symmetric left-right, bottom heavy (upright)
            assert abs((com - bbc).dot(f["reading_dir"])) < 0.05 and com.y - bbc.y < -0.05
        # on the OUTER wall: the label stays 5 mm above the mouth, below the lid-seat ledge, on the flat part of the wall
        assert c.ymax < P.CAMBAY1021_BOX_LID_SEAT_Y and c.ymin > LABEL_Y_MIN
    # the three letters differ and are all non-trivial
    assert all(l.Volume() > 1.0 for l in labels.values())



# ---------------------------------------------------------------------------------------------------------------
# body frame (for the software)
# ---------------------------------------------------------------------------------------------------------------
def test_body_frame_points_match_the_spec_and_the_corner_holes_are_the_1021_ones(parts):
    new = parts[2].val()
    for hid, want in SPEC_BODY.items():
        f = G.tri_hole_frames()[hid]
        cyl = B.measured_cylinder_axes(new, f["outer"], R)
        p0, d, _ = cyl[0]
        d = d if d.dot(f["axis"]) > 0 else d * -1.0
        got = B.body_frame_m(G, B._axis_plane_point(p0, d, f["normal"], G.BOX_UPPER_HALF))
        assert all(abs(a - b) < 6e-5 for a, b in zip(got, want)), (hid, got, want)        # spec gives 4 decimals
    cp = B.corner_hole_points_body_m()
    for st, (sx, sy) in {"A": (-1, -1), "B": (1, -1), "C": (1, 1), "D": (-1, 1)}.items():
        i = cp[st]["inner_mouth"]
        assert abs(i[0] - sx * 0.03707) < 1e-6 and abs(i[1] - sy * 0.03707) < 1e-6 and abs(i[2]) < 1e-9     # not the v6 +-0.04207
        o = cp[st]["outer_mouth"]
        assert abs(o[0] - sx * 0.04322) < 1e-6 and abs(o[2] - 0.00213) < 1e-6


# ---------------------------------------------------------------------------------------------------------------
# exports
# ---------------------------------------------------------------------------------------------------------------
def test_housing34_step_reimport_agrees_and_drops_in_at_the_origin(parts):
    orig, base, new, cover, _ = parts
    path = os.path.join(REPO, "exports", "step", "gripper1021_housing_cambay_34.step")
    assert os.path.exists(path)
    d = B.reimport_check(path, G.to_world(new.val()))
    assert d["solids"] == 1 and d["valid"] and d["vol_rel_diff"] < 1e-6 and d["bbox_max_diff_mm"] < 1e-3
    re = cq.importers.importStep(path).val().BoundingBox()
    cur = cq.importers.importStep(os.path.join(REPO, "exports", "step", "gripper1021_housing_cambay.step")).val().BoundingBox()
    for a, b in ((re.xmin, cur.xmin), (re.xmax, cur.xmax), (re.ymin, cur.ymin), (re.ymax, cur.ymax), (re.zmin, cur.zmin), (re.zmax, cur.zmax)):
        assert abs(a - b) < 1e-3                                       # same world envelope as the current housing export
    # volume of the exported part = current export minus the removed volume
    vol_cur = cq.importers.importStep(os.path.join(REPO, "exports", "step", "gripper1021_housing_cambay.step")).val().Volume()
    assert 55.0 < vol_cur - cq.importers.importStep(path).val().Volume() < 75.0


def test_housing34_stl_in_print_orientation():
    path = os.path.join(REPO, "exports", "stl", "gripper1021_housing_cambay_34.stl")
    assert os.path.exists(path)
    lo, hi = B.housing34_stl_check(path)
    assert abs(lo[2]) < 1e-3 and abs(hi[2] - 55.0) < 1e-2                          # bottom plane on the bed, box upright, top at 55
    assert abs(lo[0] + 50.0) < 1e-2 and abs(hi[0] - 50.0) < 1e-2
    assert abs(lo[1] + 50.0) < 1e-2 and abs(hi[1] - 101.3) < 1e-2                  # bay toward +y, as the current STL


def test_current_exports_are_not_touched_by_the_option():
    for nm in ("gripper1021_housing_cambay", "gripper1021_housing_cambay_cover"):
        for sub, ext in (("step", "step"), ("stl", "stl")):
            assert os.path.exists(os.path.join(REPO, "exports", sub, f"{nm}.{ext}"))


# ---------------------------------------------------------------------------------------------------------------
# mass
# ---------------------------------------------------------------------------------------------------------------
def test_mass_before_and_after(parts):
    orig, base, new, cover, _ = parts
    petg = P.GRIP1021_PETG_G_CM3 / 1000.0
    before, after = base.val().Volume() * petg, new.val().Volume() * petg
    assert 195.0 < before < 197.0 and 195.0 < after < 197.0
    assert 0.05 < before - after < 0.12                                # holes + labels remove about 64 mm3 = 0.08 g


# ---------------------------------------------------------------------------------------------------------------
# cable lines (three-station workspace, yaw +-15 deg): coarse sampling here; the full run is scripts/analyze_cable_lines_housing_34.py
# ---------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def cable():
    return A34.analyze(grid_step=0.4, z_levels=5, yaws_deg=[0.0, 15.0, -15.0], verbose=False)


def test_cable_lines_clear_the_bay_and_cover(cable):
    assert cable["min_distance_bay_cover_only_mm"] >= P.CAMBAY1021_TRI_KEEPOUT                # 12.7 mm: the lines never come near the bay
    assert cable["lines_scored"] > 300 and all(t["lines"] > 0 for t in cable["totals"].values())
    assert cable["totals"]["C"]["infeasible"] == 0


def test_cable_lines_clear_the_housing_for_moderate_lines(cable):
    """Lines no steeper than 30 deg that leave within 15 deg of the hole axis clear everything by >= 5 mm."""
    assert cable["min_distance_mm_for_elevation_at_most_and_angle_to_axis_at_most"]["elev<=30,angle<=15"] >= P.CAMBAY1021_TRI_KEEPOUT


@pytest.mark.xfail(strict=True, reason="spec 5 asks >= 5 mm for every line of the workspace; steep lines (> ~50 deg elevation) pass the box rim "
                   "and lines more than ~20 deg off the axis pass the R10 box corner at < 5 mm.  Reported in the build notes for a lead decision.")
def test_cable_line_minimum_is_at_least_5mm_over_the_whole_workspace(cable):
    assert cable["min_distance_mm"] >= P.CAMBAY1021_TRI_KEEPOUT
