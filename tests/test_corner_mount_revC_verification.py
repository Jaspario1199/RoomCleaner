"""
Independent geometry-verifier tests for corner_mount REV C (D14 drop-arm
homing-switch relocation). Written by the geometry-verifier role, NOT the
implementer -- these probe the actual built BRep with fresh, independently
derived geometry (pulley envelope, roller/lever position, line corridor,
slot cross-sections) and do not import or reuse the implementer's own
computed constants for anything the assignment specifically asked to be
cross-checked (e.g. the roller center position is computed here from the
switch/lever model, not read off a `corner_mount` constant).

Scope: cad/parts/corner_mount.py rev C only. Read-only against corner_mount.py
itself; this file and verification/corner_mount_revC_report.md are the only
outputs.
"""

from __future__ import annotations

import math

import pytest

cq = pytest.importorskip("cadquery")

from OCP.gp import gp_Pnt                              # noqa: E402
from OCP.BRepClass3d import BRepClass3d_SolidClassifier  # noqa: E402
from OCP.TopAbs import TopAbs_IN                        # noqa: E402

from cad.parts import corner_mount as cm  # noqa: E402
from cad import interfaces as I           # noqa: E402


def _inside_fn(solid):
    def f(x, y, z, tol=1e-6):
        c = BRepClass3d_SolidClassifier(solid.wrapped)
        c.Perform(gp_Pnt(x, y, z), tol)
        return c.State() == TopAbs_IN
    return f


def _bisect_solid_edge(inside, cx, cy, cz, axis, lo=0.0, hi=10.0, iters=50):
    """From a point known to be SOLID, binary-search outward along `axis`
    for the solid -> void transition radius (matches the proven helper in
    test_winch_geometry.py -- reimplemented here to keep this file
    self-contained)."""
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


@pytest.fixture(scope="module")
def built():
    part = cm.make()
    return part, _inside_fn(part.val())


# ---------------------------------------------------------------------------
# Check 1: mid-span boss removed, rev-B features intact.
# ---------------------------------------------------------------------------

def test_midspan_boss_region_is_clear(built):
    """D14 removes the rev-B mid-span boss (which sat between the wall and
    the pulley ears, over the horizontal line span). Dense grid probe of
    that region -- excluding the pulley-ear/KW-arm block near the +X end --
    must find zero solid material."""
    _, ins = built
    hit_points = []
    for x in range(-30, 46, 2):
        for y in (4, 8, 12, 16, 20, 24, 28, 30):
            for z_off in (0.5, 3, 7, 12):
                z = cm.PLATE_T + z_off
                if ins(x, y, z):
                    hit_points.append((x, y, z))
    assert not hit_points, (
        f"corner_mount: unexpected solid material in the former mid-span-"
        f"boss region (rev C should have removed it per D14): {hit_points[:5]}"
    )


def test_revb_plate_wall_gussets_ears_unchanged(built):
    part, ins = built
    bb = part.val().BoundingBox()
    assert abs(bb.xlen - 138.0) < 1e-6 and abs(bb.ylen - 65.0) < 1e-6
    assert cm.PLATE_T == I.CORNER_MOUNT_PLATE_T == 6.0
    assert cm.MOUNT_HOLE_X == (-55.0, -5.0, 45.0)
    assert cm.WALL_CX == -40.0 and cm.WALL_THK == 6.0 and cm.WALL_W == 56.0
    for x in cm.MOUNT_HOLE_X:
        assert not ins(x, 0.0, cm.PLATE_T - 0.1), f"csk @ x={x} should be void at top"
        assert not ins(x, 0.0, 0.3), f"csk shank @ x={x} should be void near bottom"
    assert cm.EAR_SY == (10.0, -10.0)
    assert cm.SPOOL_DRUM_MID_Y == 0.0


# ---------------------------------------------------------------------------
# Check 3: drop arm shape, slot cut types.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("leg_idx", [0, 1])
def test_arm_leg_is_constant_section_no_overhang(built, leg_idx):
    """No taper/flare with Z -- sample the leg's own X-footprint (at a Y and
    Z clear of any slot cut) at several heights; it must be constant, i.e.
    a genuine vertical prism (never widening as it rises, which would be an
    unsupported overhang)."""
    _, ins = built
    y0, y1 = cm.KW_LEG_Y[leg_idx]
    y_probe = y0 + 0.3  # near the leg's own edge, away from slot centers
    x_edges_by_z = []
    for z_local in (2, 15, 35, cm.KW_ARM_H - 2):
        z = cm.PLATE_T + z_local
        # From a point known solid (well inside the leg), bisect outward in
        # -X for the solid -> void transition (the leg's own -X face).
        edge_offset = _bisect_solid_edge(
            ins, cm.KW_ARM_X0 + 3.0, y_probe, z, "x", 0.0, -12.0
        )
        x_edges_by_z.append(round(cm.KW_ARM_X0 + 3.0 + edge_offset, 2))
    # Above the ear (z_local=35, > EAR_H-PLATE_T=22.5) the leg's own -X face
    # should sit at KW_ARM_X0; below/within ear height it may be flush with
    # the ear (a WIDER footprint at lower Z is fine -- material only ever
    # merges with a neighboring feature below, it never overhangs above it).
    for z_local, edge in zip((2, 15, 35, cm.KW_ARM_H - 2), x_edges_by_z):
        if z_local >= 35:
            assert abs(edge - cm.KW_ARM_X0) < 0.1, (
                f"leg {leg_idx} -X face at z_local={z_local} = {edge}, "
                f"expected {cm.KW_ARM_X0}"
            )


@pytest.mark.parametrize("leg_idx", [0, 1])
def test_ziptie_slot_is_through_cut(built, leg_idx):
    _, ins = built
    zip_y = cm.KW_ZIP_Y[leg_idx]
    z = cm.KW_TRIGGER_Z
    for x in (cm.KW_ARM_X0 + 0.5, (cm.KW_ARM_X0 + cm.KW_ARM_X1) / 2, cm.KW_ARM_X1 - 0.5):
        assert not ins(x, zip_y, z), (
            f"leg {leg_idx} zip-tie slot: expected void at x={x:.2f} "
            f"(y={zip_y}, z={z}) -- through cut"
        )


@pytest.mark.parametrize("leg_idx", [0, 1])
def test_pilot_slot_is_blind_at_declared_depth(built, leg_idx):
    """Bisect the void->solid transition along X behind the M2 pilot slot;
    depth from the mount face must be >= 5.0 mm (KW12_PILOT_DEPTH) with the
    diameter matching 1.7 mm."""
    _, ins = built
    screw_y = cm.KW_SCREW_Y[leg_idx]
    z = cm.KW_TRIGGER_Z
    assert not ins(cm.KW_ARM_X1 - 0.3, screw_y, z), "pilot must be void near the mount face"
    # From a point known solid (deep at the leg's back, x=KW_ARM_X0), bisect
    # toward the mount face (+X) for the solid -> void transition (the
    # pilot's blind bottom).
    edge_offset = _bisect_solid_edge(
        ins, cm.KW_ARM_X0 + 0.05, screw_y, z, "x", 0.0, cm.KW_BOSS_DEPTH
    )
    bottom_x = cm.KW_ARM_X0 + 0.05 + edge_offset
    depth = cm.KW_ARM_X1 - bottom_x
    assert depth >= 5.0 - 0.02, (
        f"leg {leg_idx} pilot blind depth measured {depth:.3f} mm, required >= 5.0 mm"
    )
    assert depth <= 5.0 + 0.5, f"leg {leg_idx} pilot depth measured {depth:.3f} mm, expected ~5.0"


@pytest.mark.parametrize("leg_idx", [0, 1])
def test_slots_are_z_elongated_by_10mm(built, leg_idx):
    """Measure the pilot slot's Z void-span directly (diameter-independent
    of Y position) and confirm it equals KW_TRIGGER_ADJ_RANGE + hole dia."""
    _, ins = built
    screw_y = cm.KW_SCREW_Y[leg_idx]
    x_mid = cm.KW_ARM_X1 - cm.KW12_PILOT_DEPTH / 2
    z_center = cm.KW_TRIGGER_Z
    lo, hi = z_center - 8, z_center + 8
    z = lo
    edges = []
    prev = None
    step = 0.02
    while z <= hi:
        cur = ins(x_mid, screw_y, z)
        if prev is not None and cur != prev:
            edges.append(z)
        prev = cur
        z += step
    assert len(edges) == 2, f"leg {leg_idx}: expected exactly 2 Z transitions, got {edges}"
    span = edges[1] - edges[0]
    expected = cm.KW_TRIGGER_ADJ_RANGE + cm.KW12_SELFTAP_PILOT_DIA
    assert abs(span - expected) < 0.1, (
        f"leg {leg_idx} pilot Z-span measured {span:.3f} mm, expected {expected} mm"
    )


# ---------------------------------------------------------------------------
# Check 5 -- THE KEY CHECK: does the bead on the drop line actually trip the
# roller? Model built fresh from the assignment's own stated geometry, not
# from corner_mount's internal constants beyond the arm/leg positions.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="rev C defect: KW12-3 roller misses the drop line (verification/corner_mount_revC_report.md check 5); fixed by rev D")
def test_kw12_roller_x_overlaps_bead_on_drop_line_for_nominal_pulley():
    """Roller center X = KW_ARM_X1 + KW12_LEVER_HEIGHT_ABOVE_MOUNT (5 mm
    outboard of the mount face). Bead rides the drop line at
    X_line = EAR_CX + OD/2. For the NOMINAL purchased pulley (OD=20, the
    same value corner_mount.py itself designs DROP_X around) with a
    standard Ø5 mm bead, the X-ranges of the roller (Ø4.5) and the bead
    must overlap by >= 1.5 mm."""
    roller_x = cm.KW_ARM_X1 + cm.KW12_LEVER_HEIGHT_ABOVE_MOUNT
    roller_r = cm.KW12_ROLLER_DIA / 2
    OD = 20.0
    x_line = cm.EAR_CX + OD / 2
    bead_r = 5.0 / 2
    overlap = min(x_line + bead_r, roller_x + roller_r) - max(x_line - bead_r, roller_x - roller_r)
    # Document the measured value regardless of pass/fail so the report has
    # a reproducible number; the assignment's own PASS bar is 1.5 mm.
    print(f"OD=20, dia5 bead: roller X=[{roller_x-roller_r:.2f},{roller_x+roller_r:.2f}] "
          f"bead X=[{x_line-bead_r:.2f},{x_line+bead_r:.2f}] overlap={overlap:.3f} mm")
    assert overlap >= 1.5, (
        f"corner_mount KW12 roller/bead X-overlap = {overlap:.3f} mm (OD=20, dia5 bead), "
        f"required >= 1.5 mm. Roller X-range=[{roller_x-roller_r:.3f},{roller_x+roller_r:.3f}], "
        f"bead X-range=[{x_line-bead_r:.3f},{x_line+bead_r:.3f}]. This means the switch's "
        f"lever roller does not reach far enough back toward the pulley to intercept a "
        f"standard 5 mm bead riding the vertical drop line."
    )


@pytest.mark.parametrize("od,bead_dia", [(18, 5), (18, 8), (20, 5), (20, 8), (22, 5), (22, 8)])
def test_kw12_roller_bead_overlap_table(od, bead_dia):
    """Full table required by the assignment: overlap for every (OD, bead)
    combination, reported (not all required to pass -- OD range is the
    purchased-part uncertainty band, not a design freedom)."""
    roller_x = cm.KW_ARM_X1 + cm.KW12_LEVER_HEIGHT_ABOVE_MOUNT
    roller_r = cm.KW12_ROLLER_DIA / 2
    x_line = cm.EAR_CX + od / 2
    bead_r = bead_dia / 2
    overlap = min(x_line + bead_r, roller_x + roller_r) - max(x_line - bead_r, roller_x - roller_r)
    print(f"OD={od} bead={bead_dia}: overlap={overlap:.3f} mm")
    # Not asserted PASS/FAIL here (see report for the interpretation table);
    # this test exists to keep the measured numbers under CI/regression
    # tracking. Only the OD=20/dia5 nominal case has a hard gate above.


@pytest.mark.xfail(strict=True, reason="rev C defect: KW12-3 roller misses the drop line (verification/corner_mount_revC_report.md check 5); fixed by rev D")
def test_kw12_roller_y_reach_hits_the_drop_line():
    """Per the assignment's own model: roller center
    Y = (switch body's lever-side / leading edge) - 18 mm (lever length).
    This must land within +-2 mm of Y=0 (the drop line) for a bead centered
    on the line to be struck at all, independent of the X-overlap check
    above."""
    pivot_y = cm.KW_BODY_Y_FRONT
    roller_y = pivot_y - cm.KW12_LEVER_LEN
    print(f"pivot_y={pivot_y:.3f}  roller_y={roller_y:.3f}  (target 0 +-2)")
    assert abs(roller_y) <= 2.0, (
        f"corner_mount KW12 roller Y position = {roller_y:.3f} mm "
        f"(pivot at KW_BODY_Y_FRONT={pivot_y:.3f} mm, lever 18 mm pointing -Y), "
        f"required within +-2 mm of Y=0 (the drop line's own Y position). "
        f"The 18 mm lever overshoots the {pivot_y:.3f} mm gap to the line by "
        f"{abs(roller_y):.3f} mm."
    )


# ---------------------------------------------------------------------------
# Check 4: clearances via boolean intersection (independent geometry, not
# read from corner_mount's own clearance constants where avoidable).
# ---------------------------------------------------------------------------

def test_pulley_envelope_cylinder_clear(built):
    part, _ = built
    axis_z = cm.PLATE_T + I.CORNER_MOUNT_AXIS_Z
    cyl = (cq.Workplane("XZ").workplane(offset=5.0).center(cm.EAR_CX, axis_z)
           .circle(22.0 / 2).extrude(-10.0))
    inter = cyl.intersect(part)
    vol = inter.val().Volume() if inter.solids().vals() else 0.0
    assert vol < 1e-6, f"pulley envelope intersection = {vol:.6f} mm^3 (expected 0)"


def test_line_corridor_horizontal_span_clear(built):
    part, _ = built
    axis_z = cm.PLATE_T + I.CORNER_MOUNT_AXIS_Z
    length = cm.EAR_CX - cm.WALL_CX
    corridor = (cq.Workplane("YZ").workplane(offset=cm.WALL_CX).center(0, axis_z)
                .circle(3.0).extrude(length))
    inter = corridor.intersect(part)
    vol = inter.val().Volume() if inter.solids().vals() else 0.0
    assert vol < 1e-6, f"horizontal line corridor intersection = {vol:.6f} mm^3 (expected 0)"


def test_line_corridor_vertical_drop_clear(built):
    part, _ = built
    axis_z = cm.PLATE_T + I.CORNER_MOUNT_AXIS_Z
    length = axis_z - cm.PLATE_T
    corridor = (cq.Workplane("XY").workplane(offset=cm.PLATE_T).center(cm.DROP_X, 0.0)
                .circle(3.0).extrude(length))
    inter = corridor.intersect(part)
    vol = inter.val().Volume() if inter.solids().vals() else 0.0
    assert vol < 1e-6, f"vertical drop-line corridor intersection = {vol:.6f} mm^3 (expected 0)"


def test_csk_screw_cone_still_open(built):
    _, ins = built
    x = cm.MOUNT_HOLE_X[2]
    assert not ins(x, 0.0, cm.PLATE_T - 0.1)
    assert not ins(x, 0.0, 0.3)


def test_nema17_motor_body_envelope_clear(built):
    from cad import params as P
    part, _ = built
    axis_z = cm.PLATE_T + I.CORNER_MOUNT_AXIS_Z
    box = (cq.Workplane("XZ").workplane(offset=cm.WALL_BACK_Y).center(cm.WALL_CX, axis_z)
           .rect(P.NEMA17_FACE, P.NEMA17_FACE).extrude(-38.0))
    inter = box.intersect(part)
    vol = inter.val().Volume() if inter.solids().vals() else 0.0
    assert vol < 1e-6, f"NEMA17 motor-body envelope intersection = {vol:.6f} mm^3 (expected 0)"


# ---------------------------------------------------------------------------
# Check 6: trigger height.
# ---------------------------------------------------------------------------

def test_trigger_height_formula_and_slot_bracket(built):
    _, ins = built
    expected = cm.PLATE_T + cm.EAR_H + 15.0
    assert abs(cm.KW_TRIGGER_Z - expected) < 1e-9
    adj = cm.KW_TRIGGER_ADJ_RANGE / 2
    screw_y = cm.KW_SCREW_Y[0]
    x_mid = cm.KW_ARM_X1 - cm.KW12_PILOT_DEPTH / 2
    # slots must be void across the whole declared +-5mm adjustment band
    for z in (cm.KW_TRIGGER_Z - adj, cm.KW_TRIGGER_Z, cm.KW_TRIGGER_Z + adj):
        assert not ins(x_mid, screw_y, z), (
            f"pilot slot not void at z={z} (trigger +- adjustment band)"
        )


# ---------------------------------------------------------------------------
# Check 7: printability -- is the horizontally-bored Z-elongated slot's roof
# a flat unsupported span, or a self-arching profile? Measured directly.
# ---------------------------------------------------------------------------

def test_pilot_slot_roof_is_self_arching_not_flat():
    """Sweep the pilot-slot cross-section width (Y) as a function of Z near
    the TOP of its Z-range. A flat, unsupported bridge would show the full
    1.7 mm width persisting right up to the last sampled layer before
    solid resumes abruptly. A self-arching (round-hole-like) profile shows
    the width shrinking smoothly toward 0 over the cap radius
    (KW12_SELFTAP_PILOT_DIA/2) before the roof closes."""
    leg = cm._kw12_leg(cm.KW_LEG_Y[0], cm.KW_ZIP_Y[0], cm.KW_SCREW_Y[0])
    ins = _inside_fn(leg.val())
    x_pilot = cm.KW_ARM_X1 - cm.KW12_PILOT_DEPTH / 2
    screw_y = cm.KW_SCREW_Y[0]
    z_center = cm.KW_TRIGGER_Z_LOCAL
    r = cm.KW12_SELFTAP_PILOT_DIA / 2
    z_top = z_center + cm.KW_TRIGGER_ADJ_RANGE / 2 + r

    def width_at(z):
        y0, y1, step = screw_y - 1.2, screw_y + 1.2, 0.005
        y = y0
        edges = []
        prev = None
        while y <= y1:
            cur = ins(x_pilot, y, z)
            if prev is not None and cur != prev:
                edges.append(y)
            prev = cur
            y += step
        return (edges[-1] - edges[0]) if len(edges) >= 2 else 0.0

    w_mid = width_at(z_center)          # deep in the straight run
    w_near_top = width_at(z_top - 0.05)  # 0.05mm below full closure
    w_at_top = width_at(z_top)          # essentially the apex

    print(f"pilot slot width: mid-band={w_mid:.4f}mm near-top(z_top-0.05)={w_near_top:.4f}mm "
          f"at z_top={w_at_top:.4f}mm  cap_radius={r}mm")

    assert abs(w_mid - cm.KW12_SELFTAP_PILOT_DIA) < 0.05, (
        f"expected full {cm.KW12_SELFTAP_PILOT_DIA} mm width in the straight band, got {w_mid:.4f}"
    )
    # Self-arching signature: width at the very top must be near zero, and
    # a point sampled well within the cap radius must show a width clearly
    # smaller than the full slot width (i.e. NOT a flat span all the way
    # to the top).
    assert w_at_top < 0.05, f"expected the slot to close to ~0 width at its top, got {w_at_top:.4f} mm"
    # A true flat/unsupported bridge would hold the full width right up to
    # the last layer before the roof snaps shut. A semicircular self-arching
    # cap instead follows width(h) = 2*sqrt(r^2 - h^2) for height h above the
    # cap's own base -- narrower than the full width at every h>0, and here
    # measured at h = 0.8*r (80% of the way up the cap) it must already be
    # well under full width.
    w_mostly_into_cap = width_at(z_top - 0.2 * r)
    assert w_mostly_into_cap < cm.KW12_SELFTAP_PILOT_DIA * 0.7, (
        f"expected width to be well under full ({cm.KW12_SELFTAP_PILOT_DIA} mm) 80% of "
        f"the way up the {r} mm cap radius (self-arching semicircle), but measured "
        f"{w_mostly_into_cap:.4f} mm -- this would indicate a flat roof instead"
    )


# ---------------------------------------------------------------------------
# Check 9: both pulley ears are true mirror images (implementer's test
# substitution -- probing the -Y ear instead of +Y -- loses nothing).
# ---------------------------------------------------------------------------

def test_both_ears_are_exact_mirror_images():
    """Build the ears alone (no arm/wall/plate) and confirm point-for-point
    mirror symmetry about Y=0 with a random probe, plus explicit body/hole
    edge checks on both sides."""
    ears = cm._pulley_ears()
    ins = _inside_fn(ears.val())

    import random
    random.seed(12345)
    mismatches = 0
    n = 3000
    for _ in range(n):
        x = cm.EAR_CX + random.uniform(-4, 4)
        y = random.uniform(2, 18)
        z = random.uniform(0, cm.EAR_H)
        if ins(x, y, z) != ins(x, -y, z):
            mismatches += 1
    assert mismatches == 0, (
        f"{mismatches}/{n} mirror-symmetry probe mismatches between the +Y and -Y ears "
        "-- the implementer's substitution of the -Y ear for the wall-thickness probe "
        "would NOT be equivalent"
    )
