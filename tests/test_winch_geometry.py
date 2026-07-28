"""
Independent geometry verification for the five winch-side / camera parts
(Gate 5, geometry-verifier role). These parts predate the gated claw-
integration workflow and had never been independently verified.

Parts covered: winch_spool, motor_mount, corner_guide, camera_mount,
camera_mount_overhead. These parts are NOT part of cad/interfaces.py (they
predate that contract file) -- expected values here come from cad/params.py
plus purchased-part facts stated in the assignment (NEMA 17 shaft/hole
pattern, Pi Camera hole pattern, innomaker board ASSUMED hole pattern).

Style follows tests/test_claw_geometry.py: build each part directly from its
`make()` function, measure the actual solid (BRepClass3d point-classification
and pin-boolean probes), and do not trust docstrings or comments.

Skips entirely if cadquery is not installed.
"""

from __future__ import annotations

import math
import os

import pytest

cq = pytest.importorskip("cadquery")

from OCP.gp import gp_Pnt                              # noqa: E402
from OCP.BRepClass3d import BRepClass3d_SolidClassifier  # noqa: E402
from OCP.TopAbs import TopAbs_IN                        # noqa: E402

from cad.parts import (          # noqa: E402
    winch_spool,
    motor_mount,
    corner_guide,
    camera_mount,
    camera_mount_overhead,
)
from cad import params as P      # noqa: E402


BBOX_TOL = 0.3  # mm


# ---------------------------------------------------------------------------
# Shared probe helpers.
# ---------------------------------------------------------------------------

def _inside_fn(solid):
    """Return f(x,y,z) -> True if that point is strictly inside solid
    material, using an exact BRep point classifier (not mesh-based)."""
    def f(x, y, z, tol=1e-6):
        c = BRepClass3d_SolidClassifier(solid.wrapped)
        c.Perform(gp_Pnt(x, y, z), tol)
        return c.State() == TopAbs_IN
    return f


def _bisect_wall(inside, cx, cy, cz, axis, lo=0.0, hi=10.0, iters=45):
    """From a void center point, binary-search outward along `axis` for the
    void -> solid transition radius. `lo` must be void, `hi` must be solid."""
    def probe(r):
        x, y, z = cx, cy, cz
        if axis == "x":
            x = cx + r
        elif axis == "y":
            y = cy + r
        else:
            z = cz + r
        return inside(x, y, z)
    assert not probe(lo), f"center ({cx},{cy},{cz}) is not void (lo={lo})"
    assert probe(hi), f"outer bound ({cx},{cy},{cz}) at r={hi} is not solid"
    for _ in range(iters):
        mid = (lo + hi) / 2
        if probe(mid):
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def _bisect_solid_edge(inside, cx, cy, cz, axis, lo=0.0, hi=10.0, iters=45):
    """From a point known to be SOLID, binary-search outward along `axis`
    for the solid -> void transition radius (opposite sense of
    `_bisect_wall`; used for measuring a post/boss outer diameter)."""
    def probe(r):
        x, y, z = cx, cy, cz
        if axis == "x":
            x = cx + r
        elif axis == "y":
            y = cy + r
        else:
            z = cz + r
        return inside(x, y, z)
    assert probe(lo), f"center ({cx},{cy},{cz}) is not solid (lo={lo})"
    assert not probe(hi), f"outer bound ({cx},{cy},{cz}) at r={hi} is not void"
    for _ in range(iters):
        mid = (lo + hi) / 2
        if probe(mid):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _pin_removed_volume(wp, x, y, z_center, length, diameter=2.0):
    v0 = wp.val().Volume()
    pin = (
        cq.Workplane("XY")
        .workplane(offset=z_center - length / 2)
        .circle(diameter / 2)
        .extrude(length)
        .translate((x, y, 0))
    )
    return v0 - wp.cut(pin).val().Volume()


# ---------------------------------------------------------------------------
# Check 1: build, single solid, bounding box.
# ---------------------------------------------------------------------------

PART_SPECS = {
    "winch_spool": (winch_spool.make, (36.0, 36.0, 32.0)),
    "motor_mount": (motor_mount.make, (56.0, 52.0, 54.0)),
    "corner_guide": (corner_guide.make, (55.0, 34.0, 26.0)),
    "camera_mount": (camera_mount.make, (31.0, 35.0, 16.0)),
    "camera_mount_overhead": (camera_mount_overhead.make, (50.0, 50.0, 14.0)),
}


@pytest.fixture(scope="module")
def built_parts():
    out = {}
    for name, (make_fn, expected) in PART_SPECS.items():
        out[name] = (make_fn(), expected)
    return out


@pytest.mark.parametrize("name", list(PART_SPECS))
def test_part_builds_valid_single_solid(built_parts, name):
    wp, _ = built_parts[name]
    solids = wp.solids().vals()
    assert len(solids) == 1, f"{name}: expected 1 solid, got {len(solids)}"
    assert wp.val().isValid(), f"{name}: solid failed isValid()"
    assert wp.val().Volume() > 0, f"{name}: volume must be > 0"


@pytest.mark.parametrize("name", list(PART_SPECS))
def test_part_bounding_box(built_parts, name):
    wp, expected = built_parts[name]
    bb = wp.val().BoundingBox()
    measured = (bb.xlen, bb.ylen, bb.zlen)
    for axis, (m, e) in zip("xyz", zip(measured, expected)):
        assert abs(m - e) <= BBOX_TOL, (
            f"{name}: {axis} = {m:.3f} mm, expected {e} +/- {BBOX_TOL} mm"
        )


# ---------------------------------------------------------------------------
# Check 2: winch_spool bore -- CRITICAL, must derive from MOTOR_SHAFT_DIA
# (NEMA 17 = 5.0 mm), not a stale value from the old 6 mm motor.
# ---------------------------------------------------------------------------

def test_spool_bore_round_radius_matches_motor_shaft_dia():
    """The un-flattened (round) side of the bore must equal
    (MOTOR_SHAFT_DIA + CLEARANCE) / 2 -- confirms the bore is NOT the stale
    6 mm value from before the NEMA17 (5 mm shaft) motor change."""
    spool = winch_spool.make()
    total_len = P.SPOOL_LEN + 2 * P.SPOOL_FLANGE_THK
    mid_z = total_len / 2
    ins = _inside_fn(spool.val())
    expected_r = (P.MOTOR_SHAFT_DIA + P.CLEARANCE) / 2

    r_round = _bisect_wall(ins, 0, 0, mid_z, "x", 0.0, expected_r + 2, iters=50)
    # probe on the -X side (opposite the flat, which is cut on +X) at y=0
    r_round = _bisect_wall(lambda x, y, z: ins(-x, y, z), 0, 0, mid_z, "x",
                            0.0, expected_r + 2, iters=50)
    assert abs(r_round - expected_r) <= 0.02, (
        f"spool bore round-side radius = {r_round:.4f} mm, expected "
        f"{expected_r:.4f} mm (= (MOTOR_SHAFT_DIA {P.MOTOR_SHAFT_DIA} + "
        f"CLEARANCE {P.CLEARANCE}) / 2). A ~0.5 mm-scale error here would "
        f"indicate a stale 6 mm-shaft bore."
    )


def test_spool_dflat_has_zero_effect_at_flat_center():
    """FAILS by design to document a real defect: MOTOR_SHAFT_FLAT > 0 is
    set in params.py, and winch_spool.make() attempts to cut a D-flat, but
    the cutting box (cad/parts/winch_spool.py `flat`) is built with
    `.center(bore/2 - MOTOR_SHAFT_FLAT, 0).box(MOTOR_SHAFT_FLAT*2, bore,
    total_len*2, ...)` on the XY plane: this only widens the void near the
    Y-extremes of the bore (|y| > ~2.05 mm) where the box's fixed X-range
    [1.6, 2.6] mm reaches past the circle boundary. At y=0 -- the flat's
    intended center, where a real NEMA17 D-shaft flat would contact -- the
    circle alone already spans the full box X-range, so the box cut is a
    complete no-op there. Net effect: the bore is a plain round hole at the
    critical flat location; the anti-rotation flat does not exist where a
    mating D-shaft would need it.
    """
    spool = winch_spool.make()
    total_len = P.SPOOL_LEN + 2 * P.SPOOL_FLANGE_THK
    mid_z = total_len / 2
    ins = _inside_fn(spool.val())
    expected_round_r = (P.MOTOR_SHAFT_DIA + P.CLEARANCE) / 2
    expected_flat_wall = expected_round_r - P.MOTOR_SHAFT_FLAT  # 2.1 mm, spec

    wall_at_y0 = _bisect_wall(ins, 0, 0, mid_z, "x", 0.0, expected_round_r + 1, iters=50)

    assert abs(wall_at_y0 - expected_flat_wall) <= 0.05, (
        f"D-FLAT DEFECT (reproducible): at the bore's flat-center cross "
        f"section (x sweep, y=0, z={mid_z} mm -- i.e. mid-drum height), the "
        f"void->solid wall is at x={wall_at_y0:.4f} mm. Expected the flat "
        f"plane at x = bore_r - MOTOR_SHAFT_FLAT = {expected_flat_wall:.4f} "
        f"mm (params: MOTOR_SHAFT_DIA={P.MOTOR_SHAFT_DIA}, CLEARANCE="
        f"{P.CLEARANCE}, MOTOR_SHAFT_FLAT={P.MOTOR_SHAFT_FLAT}). Measured "
        f"wall sits at the plain round-bore radius ({expected_round_r} mm) "
        f"instead -- the D-flat cut has NO effect at y=0. See "
        f"verification/winch_parts_report.md for the full probe evidence."
    )


# ---------------------------------------------------------------------------
# Check 3: motor_mount -- 4x M3 clearance on the 31 mm NEMA17 square,
# boss clearance >= NEMA17_BOSS_DIA.
# ---------------------------------------------------------------------------

def _motor_mount_face_y():
    BASE_W = 52.0
    T = 5.0
    return -BASE_W / 2 + T / 2


@pytest.mark.parametrize("dx", [-1, 1])
@pytest.mark.parametrize("dz", [-1, 1])
def test_motor_mount_screw_holes_on_nema17_pattern(dx, dz):
    mm = motor_mount.make()
    ins = _inside_fn(mm.val())
    half = P.NEMA17_HOLES / 2
    PATTERN_Z = 30.0
    y_face = _motor_mount_face_y()
    x = dx * half
    z = PATTERN_Z + dz * half

    r = _bisect_wall(ins, x, y_face, z, "x", 0.0, 6.0)
    expected_dia = P.SCREW_M3 + 0.4
    assert abs(2 * r - expected_dia) <= 0.05, (
        f"motor_mount M3 hole at (x={x}, z={z}): measured diameter "
        f"{2*r:.4f} mm, expected {expected_dia} mm"
    )


def test_motor_mount_boss_clearance():
    mm = motor_mount.make()
    ins = _inside_fn(mm.val())
    PATTERN_Z = 30.0
    y_face = _motor_mount_face_y()
    r = _bisect_wall(ins, 0, y_face, PATTERN_Z, "x", 0.0, 15.0)
    assert 2 * r >= P.NEMA17_BOSS_DIA - 0.05, (
        f"motor_mount boss clearance diameter = {2*r:.4f} mm, expected >= "
        f"{P.NEMA17_BOSS_DIA} mm (NEMA17_BOSS_DIA)"
    )
    expected_dia = P.NEMA17_BOSS_DIA + P.CLEARANCE
    assert abs(2 * r - expected_dia) <= 0.05, (
        f"motor_mount boss clearance diameter = {2*r:.4f} mm, expected "
        f"{expected_dia} mm (NEMA17_BOSS_DIA + CLEARANCE)"
    )


# ---------------------------------------------------------------------------
# Check 4: corner_guide -- ear axle holes coaxial, and wall-thickness around
# the axle hole (this is where a real defect was found).
# ---------------------------------------------------------------------------

def _corner_guide_ear_geom():
    BASE_L = 55.0
    EAR_T = 4.0
    GAP = 10.0
    EAR_H = 26.0
    ear_cx = -BASE_L / 2 + EAR_T / 2 + 6
    z = EAR_H - 6
    return ear_cx, z, EAR_T


@pytest.mark.parametrize("sign", [1, -1])
def test_corner_guide_ear_axle_hole_diameter(sign):
    cg = corner_guide.make()
    ins = _inside_fn(cg.val())
    ear_cx, z, EAR_T = _corner_guide_ear_geom()
    GAP = 10.0
    sy = sign * (GAP / 2 + EAR_T / 2)

    # hole axis is along Y; measure diameter by sweeping Z (clear of the
    # thin-wall X direction so this measures the true hole bore, not the
    # ear's own X-thickness).
    r = _bisect_wall(ins, ear_cx, sy, z, "z", 0.0, 3.0)
    expected_dia = P.SCREW_M3 + 0.3
    assert abs(2 * r - expected_dia) <= 0.05, (
        f"corner_guide ear (y={sy}) axle hole diameter = {2*r:.4f} mm, "
        f"expected {expected_dia} mm"
    )


def test_corner_guide_ear_axle_holes_are_coaxial():
    """Both ears' axle holes must share the same (x, z) axis for a straight
    bolt/pulley axle to pass through both."""
    ear_cx_a, z_a, _ = _corner_guide_ear_geom()
    ear_cx_b, z_b, _ = _corner_guide_ear_geom()  # identical formula, both ears
    assert ear_cx_a == ear_cx_b and z_a == z_b


def test_corner_guide_ear_wall_thickness_around_axle_hole():
    """Regression probe for a REAL defect found at verification: the axle hole
    (SCREW_M3 + 0.3 = 3.7 mm) through the original 4.0 mm ear left ~0.15 mm
    walls -- unprintable. The repair sizes the ear plate (EAR_PLATE_T) so the
    printed wall clears EAR_HOLE_MIN_WALL on each side.

    Unlike the first version of this test, this probes the BUILT solid: it
    measures the ear plate's true X-thickness beside the hole and the hole's
    true bore, and derives the wall from those measurements -- no nominal
    arithmetic on local constants.
    """
    from cad.parts.corner_guide import (
        EAR_PLATE_T, EAR_HOLE_DIA, EAR_HOLE_MIN_WALL,
    )

    cg = corner_guide.make()
    ins = _inside_fn(cg.val())
    ear_cx, z, EAR_T = _corner_guide_ear_geom()
    GAP = 10.0
    sy = GAP / 2 + EAR_T / 2

    # 1. True hole bore (sweep Z through the hole center, axis along Y).
    hole_r_meas = _bisect_wall(ins, ear_cx, sy, z, "z", 0.0, 3.0)

    # 2. True plate X-thickness, probed just ABOVE the hole (solid material),
    #    one-sided from the plate centerline x = ear_cx, doubled (the ear box
    #    is X-centered on ear_cx). _bisect_wall expects a void start, so run a
    #    small solid->void bisection inline.
    z_probe = z + hole_r_meas + 0.5
    assert ins(ear_cx, sy, z_probe), "probe start must be inside the ear plate"
    lo, hi = 0.0, 8.0
    assert not ins(ear_cx + hi, sy, z_probe), "outer probe bound must be void"
    for _ in range(40):
        mid = (lo + hi) / 2
        if ins(ear_cx + mid, sy, z_probe):
            lo = mid
        else:
            hi = mid
    plate_t_meas = 2.0 * ((lo + hi) / 2)

    assert abs(plate_t_meas - EAR_PLATE_T) <= 0.05, (
        f"ear plate thickness = {plate_t_meas:.3f} mm, expected {EAR_PLATE_T}"
    )
    assert abs(2 * hole_r_meas - EAR_HOLE_DIA) <= 0.05, (
        f"axle bore = {2*hole_r_meas:.3f} mm, expected {EAR_HOLE_DIA}"
    )

    measured_wall = (plate_t_meas - 2.0 * hole_r_meas) / 2.0
    assert measured_wall >= EAR_HOLE_MIN_WALL, (
        f"wall around axle hole = {measured_wall:.3f} mm, "
        f"minimum printable = {EAR_HOLE_MIN_WALL} mm"
    )

@pytest.mark.parametrize("sx", [-1, 1])
@pytest.mark.parametrize("sy", [-1, 1])
def test_camera_mount_pi_camera_hole_pattern(sx, sy):
    cm = camera_mount.make()
    ins = _inside_fn(cm.val())
    HOLE_X, HOLE_Y, M2, PLATE_T = 21.0, 12.5, 2.4, 3.0
    x, y = sx * HOLE_X / 2, sy * HOLE_Y / 2
    # hi bound kept small: the plate has a 16x16 mm lens window cut through
    # its center (edges at x=+/-8), so a hi bound that reaches toward the
    # window from a hole at x=+/-10.5 must stay short of that edge.
    r = _bisect_wall(ins, x, y, PLATE_T / 2, "x", 0.0, M2 / 2 + 0.3)
    assert abs(2 * r - M2) <= 0.05, (
        f"camera_mount Pi-camera hole at ({x},{y}): diameter {2*r:.4f} mm, "
        f"expected {M2} mm"
    )


# ---------------------------------------------------------------------------
# Check 6: camera_mount_overhead -- 4 posts on the (ASSUMED) 28 mm square,
# M2 tap holes. cad/parts/camera_mount_overhead.py explicitly flags
# CAM_HOLE_PITCH=28.0 as unverified against the real innomaker board.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sx", [-1, 1])
@pytest.mark.parametrize("sy", [-1, 1])
def test_camera_mount_overhead_post_and_tap_hole(sx, sy):
    co = camera_mount_overhead.make()
    ins = _inside_fn(co.val())
    CAM_HOLE_PITCH, M2_TAP, POST_DIA, POST_H = 28.0, 1.7, 6.0, 10.0
    half = CAM_HOLE_PITCH / 2
    x, y, z = sx * half, sy * half, -POST_H / 2

    r_tap = _bisect_wall(ins, x, y, z, "x", 0.0, M2_TAP / 2 + 0.5)
    assert abs(2 * r_tap - M2_TAP) <= 0.05, (
        f"camera_mount_overhead tap hole at ({x},{y}): diameter "
        f"{2*r_tap:.4f} mm, expected {M2_TAP} mm"
    )

    # Post OD: start from a point confidently inside the post ring (beyond
    # the tap hole, short of the OD) and search outward for the solid->void
    # edge -- the opposite sense from the hole probes above.
    r_post = _bisect_solid_edge(
        ins, x, y, z, "x", M2_TAP / 2 + 0.4, POST_DIA / 2 + 1
    )
    assert abs(2 * r_post - POST_DIA) <= 0.05, (
        f"camera_mount_overhead post OD at ({x},{y}): diameter "
        f"{2*r_post:.4f} mm, expected {POST_DIA} mm"
    )


# ---------------------------------------------------------------------------
# Check 7: STEP export + reimport -- bbox and volume agreement.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", list(PART_SPECS))
def test_step_round_trip(built_parts, name, tmp_path):
    wp, _ = built_parts[name]
    step_path = os.path.join(tmp_path, f"{name}.step")
    cq.exporters.export(wp, step_path)
    reimported = cq.importers.importStep(step_path)

    solids = reimported.solids().vals()
    assert len(solids) == 1, f"{name}: reimport produced {len(solids)} solids, expected 1"

    s0, s1 = wp.val(), solids[0]
    bb0, bb1 = s0.BoundingBox(), s1.BoundingBox()
    bbox_diff = max(
        abs(bb0.xlen - bb1.xlen), abs(bb0.ylen - bb1.ylen), abs(bb0.zlen - bb1.zlen)
    )
    assert bbox_diff <= 0.1, f"{name}: STEP round-trip bbox diff {bbox_diff:.4f} mm > 0.1 mm"

    v0, v1 = s0.Volume(), s1.Volume()
    vol_diff_pct = abs(v0 - v1) / v0 * 100
    assert vol_diff_pct <= 1.0, (
        f"{name}: STEP round-trip volume diff {vol_diff_pct:.4f}% > 1%"
    )
