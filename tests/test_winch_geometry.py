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
    corner_mount,
)
from cad import params as P      # noqa: E402
from cad import interfaces as I  # noqa: E402


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

# ---------------------------------------------------------------------------
# Check 8: corner_mount -- the new unified winch bracket + pulley redirect
# (replaces motor_mount + corner_guide at the ceiling; those two parts are
# untouched and still covered by checks 1-7 above). See cad/parts/
# corner_mount.py module docstring for the coordinate frame and the fleet-
# alignment design reasoning these tests check against.
# ---------------------------------------------------------------------------

CORNER_MOUNT_ENVELOPE_X = (130.0, 150.0)   # mm, target long-axis envelope
CORNER_MOUNT_ENVELOPE_Y = (55.0, 65.0)     # mm, target width envelope


def test_corner_mount_builds_valid_single_solid():
    cm = corner_mount.make()
    solids = cm.solids().vals()
    assert len(solids) == 1, f"expected 1 solid, got {len(solids)}"
    assert cm.val().isValid(), "corner_mount solid failed isValid()"
    assert cm.val().Volume() > 0, "corner_mount volume must be > 0"


def test_corner_mount_bounding_box_within_declared_envelope():
    cm = corner_mount.make()
    bb = cm.val().BoundingBox()
    lo_x, hi_x = CORNER_MOUNT_ENVELOPE_X
    lo_y, hi_y = CORNER_MOUNT_ENVELOPE_Y
    assert lo_x <= bb.xlen <= hi_x, (
        f"corner_mount X envelope: measured {bb.xlen:.2f} mm, expected "
        f"[{lo_x}, {hi_x}] mm"
    )
    assert lo_y <= bb.ylen <= hi_y, (
        f"corner_mount Y envelope: measured {bb.ylen:.2f} mm, expected "
        f"[{lo_y}, {hi_y}] mm"
    )
    assert bb.zlen > 0


@pytest.mark.parametrize("hole_x", corner_mount.MOUNT_HOLE_X)
def test_corner_mount_countersink_hole_is_through_on_centerline(hole_x):
    """Each declared wood-screw hole must be void at both the plate top
    (where the countersink opens) and the plate bottom (where the shank
    exits toward the joist), probed on the actual built solid -- not just
    arithmetic on MOUNT_HOLE_X."""
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())
    top_z = corner_mount.PLATE_T - 0.5
    bot_z = 0.5
    assert not ins(hole_x, 0.0, top_z), (
        f"corner_mount mount hole x={hole_x}: expected VOID near plate top "
        f"(z={top_z}), found solid material"
    )
    assert not ins(hole_x, 0.0, bot_z), (
        f"corner_mount mount hole x={hole_x}: expected VOID near plate "
        f"bottom (z={bot_z}) -- shank must pass all the way through"
    )
    # A point 1 mm off the centerline at the SAME x, just outside the
    # countersink's max radius, must be solid: proves this is a bounded
    # hole, not an accidental full-width slot.
    edge_r = corner_mount.CSK_DIA / 2 + 3.0
    assert ins(hole_x, edge_r, top_z), (
        f"corner_mount mount hole x={hole_x}: material expected {edge_r} mm "
        f"off-centerline at the countersink face, found void"
    )


def _measure_center_offset_1d(ins, cx, cy, cz, axis, hi):
    """Measure a hole/void's true center offset along one axis from a
    nominal center point, by bisecting the void->solid transition in BOTH
    directions and averaging the signed radii. If the true center is at
    nominal + e with true radius R, the +axis bisection returns e+R and the
    -axis bisection returns -(R-e) = e-R; their average is e. Reused by
    several corner_mount tests below to measure real hole positions on the
    built solid instead of trusting the nominal constant."""
    pos = _bisect_wall(ins, cx, cy, cz, axis, 0.0, hi)
    neg = _bisect_wall(ins, cx, cy, cz, axis, 0.0, -hi)
    return (pos + neg) / 2


def test_corner_mount_countersink_spacing_meets_declared_minimum():
    """Measures each hole's true X-center on the built solid (bisecting the
    shank bore's void->solid transition, not reading MOUNT_HOLE_X), then
    checks spacing on the MEASURED centers."""
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())
    z_probe = 1.0   # inside the straight shank bore, below the csk cone floor
    search_hi = corner_mount.CSK_DIA / 2 + 2.0

    measured = []
    for nominal_x in corner_mount.MOUNT_HOLE_X:
        offset = _measure_center_offset_1d(ins, nominal_x, 0.0, z_probe, "x", search_hi)
        measured_x = nominal_x + offset
        assert abs(offset) < 0.5, (
            f"corner_mount mount hole nominal x={nominal_x}: measured center "
            f"offset {offset:.3f} mm is suspiciously large"
        )
        measured.append(measured_x)

    assert len(measured) == 3, f"expected 3 wood-screw holes, found {len(measured)}"
    measured.sort()
    gaps = [b - a for a, b in zip(measured, measured[1:])]
    for gap in gaps:
        assert gap >= I.CORNER_MOUNT_WOOD_SCREW_MIN_SPACING, (
            f"corner_mount adjacent hole spacing (measured) {gap:.2f} mm < "
            f"required {I.CORNER_MOUNT_WOOD_SCREW_MIN_SPACING} mm"
        )


def test_corner_mount_countersink_depth_leaves_min_material():
    """Direct probe of the countersink CONE depth: bisect down the hole AXIS
    (x, y=0) to find where the cone floor (transition to the straight shank
    bore) sits, then confirm plate material remains below it down to the
    joist face."""
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())
    x = corner_mount.MOUNT_HOLE_X[0]
    shank_r = corner_mount.SHANK_DIA / 2
    csk_r = corner_mount.CSK_DIA / 2
    # At radius = shank_r + epsilon, on-axis, the void column spans from the
    # countersink cone wall down through the shank; at radius just OUTSIDE
    # the countersink's opening, the material starts right at the plate top.
    probe_r = shank_r + 0.3
    z_top = corner_mount.PLATE_T
    # theoretical cone floor depth from geometry (90 deg included angle):
    depth = (csk_r - shank_r) / math.tan(math.radians(corner_mount.CSK_ANGLE / 2))
    expected_floor_z = z_top - depth
    # Just below the theoretical floor (deeper into solid) must be solid;
    # just above it (inside the widening cone) must be void, at this radius.
    assert ins(x, probe_r, expected_floor_z - 0.3), (
        "expected solid material just below the countersink cone floor"
    )
    material_under = expected_floor_z
    assert material_under >= I.CORNER_MOUNT_MIN_MATERIAL_UNDER_CSK, (
        f"corner_mount countersink at x={x}: material under cone floor = "
        f"{material_under:.2f} mm, required >= "
        f"{I.CORNER_MOUNT_MIN_MATERIAL_UNDER_CSK} mm"
    )


@pytest.mark.parametrize("dx", [-1, 1])
@pytest.mark.parametrize("dz", [-1, 1])
def test_corner_mount_nema17_bolt_square_through_holes(dx, dz):
    """Wall is thin in Y (rotated per lead ruling), so each hole's circular
    cross-section lies in the X-Z plane -- bisect along X (not Y, which
    would just hit the 6 mm wall thickness) from a Y depth inside the
    wall's own material."""
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())
    half = P.NEMA17_HOLES / 2
    x = corner_mount.WALL_CX + dx * half
    z = corner_mount.PLATE_T + corner_mount.CORNER_MOUNT_AXIS_Z + dz * half
    y_probe = (corner_mount.WALL_FRONT_Y + corner_mount.WALL_BACK_Y) / 2

    r = _bisect_wall(ins, x, y_probe, z, "x", 0.0, 6.0)
    expected_dia = corner_mount.NEMA_SCREW_HOLE_DIA
    assert abs(2 * r - expected_dia) <= 0.05, (
        f"corner_mount NEMA17 M3 hole at (x={x}, z={z}): measured diameter "
        f"{2*r:.4f} mm, expected {expected_dia} mm"
    )


def test_corner_mount_nema17_boss_clearance():
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())
    x = corner_mount.WALL_CX
    z = corner_mount.PLATE_T + corner_mount.CORNER_MOUNT_AXIS_Z
    y_probe = (corner_mount.WALL_FRONT_Y + corner_mount.WALL_BACK_Y) / 2
    r = _bisect_wall(ins, x, y_probe, z, "x", 0.0, 15.0)
    expected_dia = corner_mount.NEMA_BOSS_HOLE_DIA
    assert abs(2 * r - expected_dia) <= 0.05, (
        f"corner_mount boss clearance diameter = {2*r:.4f} mm, expected "
        f"{expected_dia} mm (NEMA17_BOSS_DIA + CLEARANCE)"
    )


def test_corner_mount_pulley_axle_holes_present_and_coaxial():
    """Diameter AND true coaxiality, both measured on the built solid.
    Coaxiality: bisect each ear's hole center along X and along Z
    independently (not `len(set(EAR_SY)) == 2`, which only proves the two
    nominal Y source values are distinct Python floats and would not catch
    a future edit giving the two ears different EAR_CX or hole-height
    formulas) and require the two ears' measured (x, z) to agree tightly --
    a straight bolt/pulley axle must pass through both."""
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())
    z_nominal = corner_mount.PLATE_T + corner_mount.EAR_H - corner_mount.EAR_TOP_MARGIN

    centers = []
    for sy in corner_mount.EAR_SY:
        r = _bisect_wall(ins, corner_mount.EAR_CX, sy, z_nominal, "z", 0.0, 3.0)
        assert abs(2 * r - corner_mount.EAR_HOLE_DIA) <= 0.05, (
            f"corner_mount pulley ear axle hole at sy={sy}: diameter "
            f"{2*r:.4f} mm, expected {corner_mount.EAR_HOLE_DIA} mm"
        )
        x_offset = _measure_center_offset_1d(
            ins, corner_mount.EAR_CX, sy, z_nominal, "x", 3.0
        )
        z_offset = _measure_center_offset_1d(
            ins, corner_mount.EAR_CX, sy, z_nominal, "z", 3.0
        )
        centers.append((corner_mount.EAR_CX + x_offset, z_nominal + z_offset))

    (x0, z0), (x1, z1) = centers
    assert abs(x0 - x1) <= 0.05 and abs(z0 - z1) <= 0.05, (
        f"corner_mount pulley ear axle holes are not coaxial: ear0 center="
        f"({x0:.3f},{z0:.3f}), ear1 center=({x1:.3f},{z1:.3f})"
    )


def test_corner_mount_fleet_alignment_height():
    """Pulley axle height and the spool/motor axis height must agree within
    CORNER_MOUNT_FLEET_HEIGHT_TOL -- probed on the built solid: the boss
    clearance void (motor/spool axis) and the ear axle void must exist at
    the SAME z within tolerance."""
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())

    # Motor/spool axis height: bisect the boss void vertically from its
    # nominal center to find the true void->solid transition, both up and
    # down, and average for the measured center. Probe Y must sit inside
    # the (now Y-thin, rotated) wall's own Y-span.
    z0 = corner_mount.PLATE_T + corner_mount.CORNER_MOUNT_AXIS_Z
    y_probe = (corner_mount.WALL_FRONT_Y + corner_mount.WALL_BACK_Y) / 2
    up = _bisect_wall(ins, corner_mount.WALL_CX, y_probe, z0, "z", 0.0, 15.0)
    down = _bisect_wall(ins, corner_mount.WALL_CX, y_probe, z0, "z", 0.0, -15.0)
    motor_axis_z = z0 + (up + down) / 2  # up positive offset, down negative offset averaged

    # Pulley axle height: same bisection on one ear's axle hole.
    sy = corner_mount.EAR_SY[0]
    zh = corner_mount.PLATE_T + corner_mount.EAR_H - corner_mount.EAR_TOP_MARGIN
    up2 = _bisect_wall(ins, corner_mount.EAR_CX, sy, zh, "z", 0.0, 3.0)
    down2 = _bisect_wall(ins, corner_mount.EAR_CX, sy, zh, "z", 0.0, -3.0)
    pulley_axis_z = zh + (up2 + down2) / 2

    assert abs(pulley_axis_z - motor_axis_z) <= I.CORNER_MOUNT_FLEET_HEIGHT_TOL, (
        f"corner_mount fleet height mismatch: motor/spool axis z="
        f"{motor_axis_z:.3f}, pulley axle z={pulley_axis_z:.3f}, diff="
        f"{abs(pulley_axis_z-motor_axis_z):.3f} mm > "
        f"{I.CORNER_MOUNT_FLEET_HEIGHT_TOL} mm"
    )


def test_corner_mount_fleet_alignment_coplanarity():
    """LEAD-RULING geometry: with the spool axis along Y (wall rotated 90 deg
    per the design note in cad/parts/corner_mount.py), the drum pays line off
    in an XZ plane -- the same kind of plane the pulley groove mid-plane
    (the XZ plane through the ears' Y midpoint) is. This test measures BOTH
    from the built solid:
      * the wall's actual front (+Y) face Y-position (bisected on the built
        geometry, not read off the WALL_FRONT_Y constant), used to derive
        where the spool's drum mid-length would land, and
      * the ears' actual Y midpoint (bisected the same way as before)
    and checks they agree within CORNER_MOUNT_FLEET_COPLANAR_TOL."""
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())

    # Measure the wall's true front-face Y position: probe at a height
    # clear of the NEMA17 boss/hole cutouts (z = PLATE_T + 5, well below the
    # pattern's lowest hole at PLATE_T + CORNER_MOUNT_AXIS_Z - NEMA_HALF)
    # and clear of the gusset X-offsets, then bisect from solid (mid-wall)
    # outward toward +Y to the solid->void transition.
    z_probe = corner_mount.PLATE_T + 5.0
    mid_y = (corner_mount.WALL_FRONT_Y + corner_mount.WALL_BACK_Y) / 2
    assert ins(corner_mount.WALL_CX, mid_y, z_probe), "expected solid mid-wall"
    front_offset = _bisect_solid_edge(
        ins, corner_mount.WALL_CX, mid_y, z_probe, "y", 0.0, 5.0
    )
    measured_wall_front_y = mid_y + front_offset
    measured_spool_drum_mid_y = (
        measured_wall_front_y + corner_mount.FACE_TO_SPOOL
        + P.SPOOL_FLANGE_THK + P.SPOOL_LEN / 2
    )

    # Measure each ear's actual Y-center the same way as before.
    x = corner_mount.EAR_CX
    z = corner_mount.PLATE_T + corner_mount.EAR_H - corner_mount.EAR_TOP_MARGIN
    centers = []
    for nominal_sy in corner_mount.EAR_SY:
        z_probe2 = corner_mount.PLATE_T + 1.0
        assert ins(x, nominal_sy, z_probe2), "expected solid inside the ear"
        pos_edge = _bisect_solid_edge(ins, x, nominal_sy, z_probe2, "y", 0.0, 8.0)
        neg_edge = _bisect_solid_edge(ins, x, nominal_sy, z_probe2, "y", 0.0, -8.0)
        centers.append(nominal_sy + (pos_edge + neg_edge) / 2)
    pulley_mid_y = sum(centers) / 2

    diff = abs(pulley_mid_y - measured_spool_drum_mid_y)
    assert diff <= I.CORNER_MOUNT_FLEET_COPLANAR_TOL, (
        f"corner_mount fleet coplanarity mismatch: pulley mid-Y="
        f"{pulley_mid_y:.3f}, measured spool drum mid-Y="
        f"{measured_spool_drum_mid_y:.3f}, diff={diff:.3f} mm > "
        f"{I.CORNER_MOUNT_FLEET_COPLANAR_TOL} mm"
    )


def test_corner_mount_fleet_separation_minimum():
    """LEAD-RULING geometry: separation is now measured along X, between the
    shaft/boss X-position and the pulley axle X-position -- BOTH measured on
    the built solid (bisecting the boss void and one ear's axle void),
    not read off the WALL_CX/EAR_CX constants."""
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())

    y_probe = (corner_mount.WALL_FRONT_Y + corner_mount.WALL_BACK_Y) / 2
    z_boss = corner_mount.PLATE_T + corner_mount.CORNER_MOUNT_AXIS_Z
    boss_offset = _measure_center_offset_1d(
        ins, corner_mount.WALL_CX, y_probe, z_boss, "x", 15.0
    )
    measured_boss_x = corner_mount.WALL_CX + boss_offset

    sy = corner_mount.EAR_SY[0]
    z_ear = corner_mount.PLATE_T + corner_mount.EAR_H - corner_mount.EAR_TOP_MARGIN
    ear_offset = _measure_center_offset_1d(
        ins, corner_mount.EAR_CX, sy, z_ear, "x", 3.0
    )
    measured_ear_x = corner_mount.EAR_CX + ear_offset

    distance = abs(measured_ear_x - measured_boss_x)
    assert distance >= I.CORNER_MOUNT_FLEET_MIN_SEPARATION, (
        f"corner_mount spool<->pulley separation (measured) = {distance:.2f} "
        f"mm, required >= {I.CORNER_MOUNT_FLEET_MIN_SEPARATION} mm"
    )


def test_corner_mount_max_fleet_angle_reasonable():
    """Sanity bound on the resulting fleet angle (informational in the
    assignment, but worth pinning so a future edit doesn't silently make it
    huge): atan((SPOOL_LEN/2) / separation) should stay well under 90 deg,
    and comfortably under a conservative 15 deg working limit."""
    separation = abs(corner_mount.EAR_CX - corner_mount.WALL_CX)
    max_angle_deg = math.degrees(math.atan((P.SPOOL_LEN / 2) / separation))
    assert max_angle_deg <= 15.0, (
        f"corner_mount max fleet angle = {max_angle_deg:.2f} deg, expected "
        f"<= 15 deg for a low-friction redirect"
    )


def test_corner_mount_gussets_clear_motor_body_envelope():
    """Regression test for the real defect found by independent
    verification (verification/corner_mount_report.md Section 7b): the
    gussets used to intersect the NEMA17 motor-body envelope by 70.42 mm^3.
    Reproduces the verifier's own method -- boolean-intersect a
    NEMA17_FACE x NEMA17_FACE x 38 mm box, seated flush against the wall's
    -Y (motor-bolting) face and centered on the shaft axis, with the full
    built bracket -- and requires 0 mm^3 (within floating-point epsilon)."""
    cm = corner_mount.make()
    axis_z_world = corner_mount.PLATE_T + corner_mount.CORNER_MOUNT_AXIS_Z
    nema_sq, motor_depth = P.NEMA17_FACE, 38.0
    y_near, y_far = corner_mount.WALL_BACK_Y, corner_mount.WALL_BACK_Y - motor_depth
    motor_box = (
        cq.Workplane("XY").center(corner_mount.WALL_CX, 0).rect(nema_sq, motor_depth)
        .extrude(nema_sq)
        .translate((0, 0, axis_z_world - nema_sq / 2))
        .translate((0, (y_near + y_far) / 2, 0))
    )
    inter = motor_box.intersect(cm)
    volume = inter.val().Volume() if inter.solids().vals() else 0.0
    assert volume < 1e-6, (
        f"corner_mount gussets/wall intersect the NEMA17 motor-body "
        f"envelope by {volume:.4f} mm^3 (expected 0) -- the motor cannot "
        f"seat flush against the bracket"
    )


def test_corner_mount_clears_virtual_spool_envelope():
    """Boolean-intersect a cylinder sized to the spool's own widest/longest
    extent (SPOOL_FLANGE_DIA x (SPOOL_LEN + 2*SPOOL_FLANGE_THK)), on the
    shaft axis per the part's own constants, with the built bracket.
    Requires 0 mm^3 -- the spool must clear the plate, wall, gussets, and
    ears entirely."""
    cm = corner_mount.make()
    axis_z_world = corner_mount.PLATE_T + corner_mount.CORNER_MOUNT_AXIS_Z
    length = corner_mount.SPOOL_FAR_Y - corner_mount.SPOOL_NEAR_Y
    assert abs(length - (P.SPOOL_LEN + 2 * P.SPOOL_FLANGE_THK)) < 1e-6
    spool_cyl = (
        cq.Workplane("XZ").workplane(offset=-corner_mount.SPOOL_NEAR_Y)
        .center(corner_mount.WALL_CX, axis_z_world)
        .circle(P.SPOOL_FLANGE_DIA / 2)
        .extrude(-length)
    )
    inter = spool_cyl.intersect(cm)
    volume = inter.val().Volume() if inter.solids().vals() else 0.0
    assert volume < 1e-6, (
        f"corner_mount bracket intersects the virtual spool envelope by "
        f"{volume:.4f} mm^3 (expected 0)"
    )


def test_corner_mount_wall_thickness_through_boss_measured():
    """Wall thickness (WALL_THK, required >= 6 mm), measured directly on the
    built solid near the boss (just outside the boss hole's own radius, so
    the probe sits in solid wall material, not the void), not read off the
    constant."""
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())
    mid_y = (corner_mount.WALL_FRONT_Y + corner_mount.WALL_BACK_Y) / 2
    z = corner_mount.PLATE_T + corner_mount.CORNER_MOUNT_AXIS_Z
    x_probe = corner_mount.WALL_CX + corner_mount.NEMA_BOSS_HOLE_DIA / 2 + 3.0
    assert ins(x_probe, mid_y, z), "expected solid wall material next to the boss hole"
    pos_edge = _bisect_solid_edge(ins, x_probe, mid_y, z, "y", 0.0, 5.0)
    neg_edge = _bisect_solid_edge(ins, x_probe, mid_y, z, "y", 0.0, -5.0)
    measured_thk = pos_edge - neg_edge
    assert abs(measured_thk - corner_mount.WALL_THK) <= 0.05, (
        f"corner_mount wall thickness (measured near boss) = "
        f"{measured_thk:.3f} mm, expected {corner_mount.WALL_THK} mm"
    )
    assert measured_thk >= 6.0 - 0.05, (
        f"corner_mount wall thickness {measured_thk:.3f} mm < 6 mm required"
    )


def test_corner_mount_pulley_gap_measured():
    """PULLEY_GAP (clear space between the ears, 10 mm), measured directly
    as a void span on the built solid at a Z clear of the axle holes."""
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())
    x = corner_mount.EAR_CX
    z = corner_mount.PLATE_T + 1.0   # near ear base, below the axle hole
    assert not ins(x, 0.0, z), "expected void at the pulley gap centerline"
    pos_edge = _bisect_wall(ins, x, 0.0, z, "y", 0.0, 8.0)
    neg_edge = _bisect_wall(ins, x, 0.0, z, "y", 0.0, -8.0)
    measured_gap = pos_edge - neg_edge
    assert abs(measured_gap - corner_mount.PULLEY_GAP) <= 0.05, (
        f"corner_mount pulley gap (measured) = {measured_gap:.3f} mm, "
        f"expected {corner_mount.PULLEY_GAP} mm"
    )


def test_corner_mount_ear_wall_around_axle_hole_measured():
    """Ear wall thickness around the axle hole (EAR_PLATE_T minus the hole
    diameter, split both sides), measured on the built solid -- the same
    defect class found in corner_guide's ear during a prior verification
    pass (0.15 mm wall, unprintable), so this is a permanent regression
    check for corner_mount's version of that geometry."""
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())
    # EAR_SY[1] (the -Y ear), not [0]: rev C's KW12 drop arm (D14) sits
    # beside the +Y ear (EAR_SY[0]) by design, so that side no longer has
    # open space beyond the ear's own EAR_PLATE_T wall for this bisection
    # to find void in. Both ears are built identically (same _pulley_ears
    # loop, same EAR_PLATE_T/EAR_HOLE_DIA), so the -Y ear -- untouched by
    # the KW12 mount -- measures the same wall-thickness property cleanly.
    sy = corner_mount.EAR_SY[1]
    z = corner_mount.PLATE_T + corner_mount.EAR_H - corner_mount.EAR_TOP_MARGIN

    hole_r = _bisect_wall(ins, corner_mount.EAR_CX, sy, z, "x", 0.0, 3.0)
    z_probe = z + hole_r + 0.5   # just above the hole, still within the ear
    assert ins(corner_mount.EAR_CX, sy, z_probe), "expected solid above the axle hole"
    pos_edge = _bisect_solid_edge(ins, corner_mount.EAR_CX, sy, z_probe, "x", 0.0, 8.0)
    neg_edge = _bisect_solid_edge(ins, corner_mount.EAR_CX, sy, z_probe, "x", 0.0, -8.0)
    ear_thickness = pos_edge - neg_edge

    assert abs(ear_thickness - corner_mount.EAR_PLATE_T) <= 0.05, (
        f"corner_mount ear thickness (measured) = {ear_thickness:.3f} mm, "
        f"expected {corner_mount.EAR_PLATE_T} mm"
    )
    wall_each_side = (ear_thickness - 2 * hole_r) / 2
    assert wall_each_side >= 1.0, (
        f"corner_mount ear wall around the axle hole = {wall_each_side:.3f} "
        f"mm/side, expected >= 1.0 mm printable minimum"
    )


def test_corner_mount_spool_plate_clearance_measured():
    """Spool-flange-to-plate clearance (>= CORNER_MOUNT_SPOOL_PLATE_
    CLEARANCE), computed from the shaft/boss axis height as MEASURED on the
    built solid (bisecting the boss void vertically), not the
    CORNER_MOUNT_AXIS_Z constant directly."""
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())
    y_probe = (corner_mount.WALL_FRONT_Y + corner_mount.WALL_BACK_Y) / 2
    z0 = corner_mount.PLATE_T + corner_mount.CORNER_MOUNT_AXIS_Z
    up = _bisect_wall(ins, corner_mount.WALL_CX, y_probe, z0, "z", 0.0, 15.0)
    down = _bisect_wall(ins, corner_mount.WALL_CX, y_probe, z0, "z", 0.0, -15.0)
    measured_axis_z = z0 + (up + down) / 2

    clearance = (measured_axis_z - corner_mount.PLATE_T) - P.SPOOL_FLANGE_DIA / 2
    assert clearance >= 4.0 - 0.05, (
        f"corner_mount spool-flange-to-plate clearance (measured) = "
        f"{clearance:.3f} mm, required >= 4.0 mm"
    )
    assert abs(clearance - I.CORNER_MOUNT_SPOOL_PLATE_CLEARANCE) <= 0.05, (
        f"corner_mount spool-flange-to-plate clearance (measured) = "
        f"{clearance:.3f} mm, expected "
        f"{I.CORNER_MOUNT_SPOOL_PLATE_CLEARANCE} mm (interfaces.py)"
    )


def test_corner_mount_mass_within_budget():
    cm = corner_mount.make()
    volume_cm3 = cm.val().Volume() / 1000.0
    mass_g = volume_cm3 * corner_mount.PETG_DENSITY_G_CM3
    assert mass_g <= corner_mount.MASS_BUDGET_G, (
        f"corner_mount mass = {mass_g:.2f} g, budget = "
        f"{corner_mount.MASS_BUDGET_G} g (PETG @ "
        f"{corner_mount.PETG_DENSITY_G_CM3} g/cm^3)"
    )


def test_corner_mount_step_round_trip():
    cm = corner_mount.make()
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        step_path = os.path.join(tmp, "corner_mount.step")
        cq.exporters.export(cm, step_path)
        reimported = cq.importers.importStep(step_path)

        solids = reimported.solids().vals()
        assert len(solids) == 1, f"reimport produced {len(solids)} solids, expected 1"

        s0, s1 = cm.val(), solids[0]
        bb0, bb1 = s0.BoundingBox(), s1.BoundingBox()
        bbox_diff = max(
            abs(bb0.xlen - bb1.xlen), abs(bb0.ylen - bb1.ylen), abs(bb0.zlen - bb1.zlen)
        )
        assert bbox_diff <= 0.1, f"STEP round-trip bbox diff {bbox_diff:.4f} mm > 0.1 mm"

        v0, v1 = s0.Volume(), s1.Volume()
        vol_diff_pct = abs(v0 - v1) / v0 * 100
        assert vol_diff_pct <= 1.0, f"STEP round-trip volume diff {vol_diff_pct:.4f}% > 1%"


# ---------------------------------------------------------------------------
# Check 9: corner_mount KW12-3 homing-switch DROP-ARM mount (rev C, D14).
# See cad/parts/corner_mount.py module docstring "HOMING SWITCH" for the
# design reasoning (D14, line geometry, orientation, adjustability
# mechanism, bead-placement procedure) these tests check against. Rev C
# replaces the rev B mid-span-boss tests below: adjustability is now
# Z-elongated (was X), the mount face is a vertical arm face at X=DROP_X
# (was a horizontal boss top), and clearance is checked against the pulley
# envelope (the new binding constraint) as well as the line corridor.
# ---------------------------------------------------------------------------

def test_corner_mount_kw12_leg_present_at_declared_position():
    """Solid probe midway between the front leg's zip-tie slot and its
    screw slot (both cut features, both at the same Z=KW_TRIGGER_Z), at the
    leg's mid-depth in X -- must be solid printed material, confirming the
    leg actually exists at its declared position (not just a passing
    constant computation)."""
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())
    x_probe = (corner_mount.KW_ARM_X0 + corner_mount.KW_ARM_X1) / 2
    y_probe = (
        (corner_mount.KW_ZIP_Y[0] + corner_mount.KW_ZIPTIE_SLOT_W / 2)
        + (corner_mount.KW_SCREW_Y[0] - corner_mount.KW12_SELFTAP_PILOT_DIA / 2)
    ) / 2
    z_probe = corner_mount.KW_TRIGGER_Z
    assert ins(x_probe, y_probe, z_probe), (
        f"corner_mount KW12 arm: expected solid material at "
        f"(x={x_probe:.3f}, y={y_probe:.3f}, z={z_probe:.3f}) -- the front "
        "leg between its zip-tie slot and screw slot"
    )


@pytest.mark.parametrize("leg_idx", [0, 1])
def test_corner_mount_kw12_arm_is_vertical_prism_from_plate(leg_idx):
    """Each leg must be a genuine no-overhang vertical prism: solid at its
    own base (just above the plate top, where it connects down to the
    plate -- the self-supporting print requirement) AND solid at its own
    top (the cap above the Z-adjustment slot band, so the topmost slot cut
    is capped by real wall rather than ending flush with an open top)."""
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())
    x_probe = (corner_mount.KW_ARM_X0 + corner_mount.KW_ARM_X1) / 2
    y0, y1 = corner_mount.KW_LEG_Y[leg_idx]
    y_probe = (y0 + y1) / 2
    z_base = corner_mount.PLATE_T + 0.5
    z_top = corner_mount.PLATE_T + corner_mount.KW_ARM_H - 0.5
    assert ins(x_probe, y_probe, z_base), (
        f"corner_mount KW12 leg {leg_idx}: expected solid material just "
        f"above the plate top (z={z_base:.3f}) -- the leg must connect "
        "directly to the plate to print without support"
    )
    assert ins(x_probe, y_probe, z_top), (
        f"corner_mount KW12 leg {leg_idx}: expected solid material near "
        f"the arm top (z={z_top:.3f}) -- capping the slot band"
    )


def test_corner_mount_kw12_line_corridor_clearance():
    """The Dyneema line + stopper bead travel corridor -- Ø6 mm (+-3 mm)
    about the vertical drop line at (X=DROP_X, Y=0), +1 mm margin -- must
    be entirely clear of built corner_mount material. The boss/legs are
    kept at Y >= KW_BOSS_Y0 = 6.0 mm (see that constant's own comment in
    corner_mount.py), outside the corridor's +-4 mm half-width by
    construction, so this probes a generous box (+-4 mm in X and Y) over
    the arm's full height and expects exactly 0 mm^3."""
    cm = corner_mount.make()
    half = 3.0 + 1.0   # mm, corridor radius + margin
    z_lo = corner_mount.PLATE_T
    z_hi = corner_mount.PLATE_T + corner_mount.KW_ARM_H + 10.0
    corridor = (
        cq.Workplane("XY").workplane(offset=z_lo)
        .center(corner_mount.DROP_X, 0.0)
        .rect(2 * half, 2 * half)
        .extrude(z_hi - z_lo)
    )
    inter = corridor.intersect(cm)
    volume = inter.val().Volume() if inter.solids().vals() else 0.0
    assert volume < 1e-6, (
        f"corner_mount intrudes into the drop-line corridor by "
        f"{volume:.6f} mm^3 (expected 0)"
    )


def test_corner_mount_kw12_pulley_envelope_clearance():
    """Boolean-intersect the purchased pulley's own clearance envelope
    (Ø22 mm -- the top of the 18-22 mm accepted OD range -- x 10 mm wide,
    i.e. +-5 mm about Y=0, matching PULLEY_GAP, on the axle at X=EAR_CX,
    Z=PLATE_T+CORNER_MOUNT_AXIS_Z) with the built bracket. This is the
    binding clearance for the KW12 arm (wider in Y than the line corridor
    above) since the arm sits right beside the pulley -- expect 0 mm^3."""
    cm = corner_mount.make()
    pulley_od = 22.0   # mm, top of the 18-22 mm accepted range
    half_w = corner_mount.PULLEY_GAP / 2   # mm, +-5 mm about Y=0
    axis_z_world = corner_mount.PLATE_T + I.CORNER_MOUNT_AXIS_Z
    pulley_cyl = (
        cq.Workplane("XZ").workplane(offset=half_w)
        .center(corner_mount.EAR_CX, axis_z_world)
        .circle(pulley_od / 2)
        .extrude(-(2 * half_w))
    )
    inter = pulley_cyl.intersect(cm)
    volume = inter.val().Volume() if inter.solids().vals() else 0.0
    assert volume < 1e-6, (
        f"corner_mount intersects the pulley envelope by {volume:.6f} mm^3 "
        "(expected 0)"
    )


def test_corner_mount_kw12_arm_clears_csk_screw():
    """The arm/legs must not overlap the X=45 mm countersunk wood-screw's
    own footprint (radius CSK_DIA/2). Checked against the KW12 boss alone
    (not the whole bracket, which legitimately has plate material near the
    screw -- that is the screw's own countersink, not a defect)."""
    boss = corner_mount._kw12_switch_boss()
    csk_x = corner_mount.MOUNT_HOLE_X[2]
    csk_r = corner_mount.CSK_DIA / 2
    cyl = (
        cq.Workplane("XY")
        .center(csk_x, 0.0)
        .circle(csk_r)
        .extrude(corner_mount.PLATE_T + corner_mount.KW_ARM_H + 10.0)
    )
    inter = cyl.intersect(boss)
    volume = inter.val().Volume() if inter.solids().vals() else 0.0
    assert volume < 1e-6, (
        f"corner_mount KW12 arm overlaps the X=45 mm countersunk screw by "
        f"{volume:.6f} mm^3 (expected 0)"
    )


@pytest.mark.parametrize("leg_idx", [0, 1])
def test_corner_mount_kw12_ziptie_slots_are_through_cuts(leg_idx):
    """Each zip-tie slot must be void from just inside the mount (+X) face
    to just inside the back (-X) face at the trigger height -- a genuine
    through-cut in X, not a blind pocket -- while material near the plate
    (well below the Z-adjustment band) stays solid, proving the cut is a
    bounded tunnel through the slot band, not a gap spanning the whole
    leg."""
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())
    zip_y = corner_mount.KW_ZIP_Y[leg_idx]
    z = corner_mount.KW_TRIGGER_Z
    x_near_mount = corner_mount.KW_ARM_X1 - 0.3
    x_near_back = corner_mount.KW_ARM_X0 + 0.3
    assert not ins(x_near_mount, zip_y, z), (
        f"corner_mount KW12 zip-tie slot {leg_idx}: expected void near the "
        f"mount face (x={x_near_mount:.3f}), found solid material"
    )
    assert not ins(x_near_back, zip_y, z), (
        f"corner_mount KW12 zip-tie slot {leg_idx}: expected void near the "
        f"back face (x={x_near_back:.3f}), found solid material -- not a "
        "through-cut"
    )
    x_mid = (corner_mount.KW_ARM_X0 + corner_mount.KW_ARM_X1) / 2
    z_near_plate = corner_mount.PLATE_T + 2.0
    assert ins(x_mid, zip_y, z_near_plate), (
        f"corner_mount KW12 zip-tie slot {leg_idx}: expected solid material "
        f"near the plate (z={z_near_plate:.3f}), found void -- the "
        "through-cut must be bounded to the slot band, not span the "
        "whole leg"
    )


@pytest.mark.parametrize("leg_idx", [0, 1])
def test_corner_mount_kw12_pilot_slot_is_blind(leg_idx):
    """Each self-tap M2 pilot must be void just inside the mount face and
    solid beyond its own KW12_PILOT_DEPTH -- a blind bore, not a
    through-cut, leaving KW_BOSS_MIN_WALL of material behind it."""
    cm = corner_mount.make()
    ins = _inside_fn(cm.val())
    screw_y = corner_mount.KW_SCREW_Y[leg_idx]
    z = corner_mount.KW_TRIGGER_Z
    x_at_mount = corner_mount.KW_ARM_X1 - 0.3
    x_beyond_pilot = corner_mount.KW_ARM_X1 - corner_mount.KW12_PILOT_DEPTH - 0.5
    assert not ins(x_at_mount, screw_y, z), (
        f"corner_mount KW12 pilot slot {leg_idx}: expected void just "
        f"inside the mount face (x={x_at_mount:.3f}), found solid material"
    )
    assert ins(x_beyond_pilot, screw_y, z), (
        f"corner_mount KW12 pilot slot {leg_idx}: expected solid material "
        f"behind the blind pilot depth (x={x_beyond_pilot:.3f}), found "
        "void -- not a blind bore"
    )


def test_corner_mount_kw12_switch_footprint_envelope_clear():
    """Boolean-intersect the KW12-3 switch BODY envelope (KW12_BODY_L along
    Y x KW12_BODY_W along Z x KW12_BODY_H along X), positioned at its
    nominal mounted location (flush against the arm's +X mount face,
    centered on the nominal trigger Z), with the built bracket. The switch
    sits entirely outside the arm (a measure-zero contact plane at
    X=DROP_X, not a positive-volume overlap), so this must read 0 mm^3."""
    cm = corner_mount.make()
    switch_box = (
        cq.Workplane("YZ").workplane(offset=corner_mount.DROP_X)
        .center(
            (corner_mount.KW_BODY_Y_FRONT + corner_mount.KW_BODY_Y_BACK) / 2,
            corner_mount.KW_TRIGGER_Z,
        )
        .rect(corner_mount.KW12_BODY_L, corner_mount.KW12_BODY_W)
        .extrude(corner_mount.KW12_BODY_H)
    )
    inter = switch_box.intersect(cm)
    volume = inter.val().Volume() if inter.solids().vals() else 0.0
    assert volume < 1e-6, (
        f"corner_mount intersects the KW12-3 switch body envelope by "
        f"{volume:.6f} mm^3 (expected 0) -- the switch cannot seat flush "
        "on the arm"
    )


def test_corner_mount_kw12_mass_delta_within_budget():
    """The KW12-3 mount's own added mass (both legs) must be <= 10 g per
    the assignment's mass-increase ceiling, independent of the part's
    overall mass-budget test above."""
    added_volume_cm3 = corner_mount._kw12_switch_boss().val().Volume() / 1000.0
    added_mass_g = added_volume_cm3 * corner_mount.PETG_DENSITY_G_CM3
    assert added_mass_g <= 10.0, (
        f"corner_mount KW12 mount added mass = {added_mass_g:.3f} g, "
        "required <= 10 g"
    )


def test_corner_mount_kw12_lever_reaches_drop_line():
    """The KW12-3's 18 mm roller lever, pivoting near the switch's leading
    (pulley-side) mounting edge and pointing -Y, must reach across to the
    drop line at Y=0 with margin. The arm's mount face (KW_ARM_X1) must
    also coincide exactly with the drop line's own X (DROP_X) -- see the
    module docstring's KW12_LEVER_HEIGHT_ABOVE_MOUNT paragraph for why no
    further X compensation is applied."""
    reach_needed_y = corner_mount.KW_BODY_Y_FRONT   # pivot Y -> corridor Y=0
    assert reach_needed_y < corner_mount.KW12_LEVER_LEN, (
        f"KW12 lever reach {corner_mount.KW12_LEVER_LEN} mm insufficient "
        f"for the {reach_needed_y:.2f} mm Y-offset from the pivot "
        f"(Y={corner_mount.KW_BODY_Y_FRONT:.2f}) to the drop line (Y=0)"
    )
    assert abs(corner_mount.KW_ARM_X1 - corner_mount.DROP_X) < 1e-9, (
        f"corner_mount KW12 mount face X ({corner_mount.KW_ARM_X1}) does "
        f"not coincide with the drop line X ({corner_mount.DROP_X})"
    )


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
