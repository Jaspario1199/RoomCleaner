"""
Independent geometry verification for corner_mount REV D (geometry-verifier
role, Gate 5) -- the KW12-3 homing-switch mount, re-oriented onto a
horizontal top pad after the rev C failure (see
verification/corner_mount_revC_report.md check 5).

Every assertion here is built from FRESH probes against the actual BRep
(OCCT BRepClass3d_SolidClassifier point-in-solid tests, bisection, and
boolean-intersection volumes) or from an independent boolean/geometry
construction -- not copied from cad/parts/corner_mount.py's own tests
(tests/test_winch_geometry.py), which remain the secondary signal (see
verification/corner_mount_revD_report.md section 10).

The KEY CHECK (test_key_check_roller_lands_on_bead_travel_*) deliberately
re-derives the roller's world coordinates from MEASURED mount geometry
(the pad's own found face, the pilot holes' own measured X-center) rather
than importing corner_mount.KW_ROLLER_X/Y/Z directly, per the assignment.

Two probes are expected (and marked strict xfail with a precise reason) to
fail: a real, reproducible geometric defect independent of the rev C
failure this revision fixes -- see verification/corner_mount_revD_report.md
section 3 and section 5 for the full detail. All other probes pass.
"""

from __future__ import annotations

import math

import pytest

cq = pytest.importorskip("cadquery")

from OCP.gp import gp_Pnt                              # noqa: E402
from OCP.BRepClass3d import BRepClass3d_SolidClassifier  # noqa: E402
from OCP.TopAbs import TopAbs_IN, TopAbs_FACE           # noqa: E402
from OCP.TopExp import TopExp_Explorer                  # noqa: E402
from OCP.TopoDS import TopoDS                            # noqa: E402
from OCP.BRepAdaptor import BRepAdaptor_Surface          # noqa: E402
from OCP.GeomAbs import GeomAbs_Plane                     # noqa: E402
from OCP.BRepBndLib import BRepBndLib                     # noqa: E402
from OCP.Bnd import Bnd_Box                                # noqa: E402

from cad.parts import corner_mount as cm   # noqa: E402
from cad import interfaces as I            # noqa: E402


# ---------------------------------------------------------------------------
# Shared probe helpers (independently written; same technique as
# tests/test_winch_geometry.py's _inside_fn/_bisect_wall, not imported).
# ---------------------------------------------------------------------------

def _inside_fn(solid):
    def f(x, y, z, tol=1e-6):
        c = BRepClass3d_SolidClassifier(solid.wrapped)
        c.Perform(gp_Pnt(x, y, z), tol)
        return c.State() == TopAbs_IN
    return f


def _bisect_wall(inside, cx, cy, cz, axis, lo=0.0, hi=10.0, iters=48):
    """From a void point, binary-search outward for the void->solid edge."""
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
    assert probe(hi), f"outer bound at r={hi} is not solid"
    for _ in range(iters):
        mid = (lo + hi) / 2
        if probe(mid):
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def _vol(shape):
    vals = shape.solids().vals()
    return sum(s.Volume() for s in vals) if vals else 0.0


@pytest.fixture(scope="module")
def built():
    part = cm.make()
    return part, _inside_fn(part.val())


# ---------------------------------------------------------------------------
# Check 1: rev-B regression, still intact under rev D.
# ---------------------------------------------------------------------------

def test_regression_plate_footprint_and_countersinks(built):
    part, ins = built
    bb = part.val().BoundingBox()
    assert abs(bb.xlen - 138.0) < 0.01 and abs(bb.ylen - 65.0) < 0.01
    for x in (-55.0, -5.0, 45.0):
        assert not ins(x, 0.0, cm.PLATE_T - 0.5), f"csk at x={x} not void near top"
        assert not ins(x, 0.0, 0.5), f"shank at x={x} not void (through-hole) near bottom"


def test_regression_spool_drum_coplanarity(built):
    assert abs(cm.SPOOL_DRUM_MID_Y) < 1e-9


def test_regression_mid_span_region_empty(built):
    """The rev-B mid-span boss (removed in rev C) must still be absent; the
    rev-D drop arm/pad must not have spread into this region either."""
    part, ins = built
    hits = []
    for x in range(-30, 46, 2):
        if x >= 51.5:   # pulley-ear footprint -- legitimate, not the probed region
            continue
        for y in (4, 8, 12, 16, 20, 24, 28, 30):
            for z in (cm.PLATE_T + 0.5, cm.PLATE_T + 3, cm.PLATE_T + 7, cm.PLATE_T + 12):
                if ins(x, y, z):
                    hits.append((x, y, z))
    assert not hits, f"unexpected solid material in mid-span region: {hits[:5]}"


def test_regression_ears_are_mirror_images():
    """Both pulley ears, built standalone, must be exact mirror images about
    Y=0 -- confirms the ear geometry is untouched by the rev-D drop arm."""
    import random
    ears = cm._pulley_ears()
    ins = _inside_fn(ears.val())
    rng = random.Random(20260902)
    mismatches = 0
    for _ in range(2000):
        lx = rng.uniform(-cm.EAR_PLATE_T, cm.EAR_PLATE_T)
        ly = rng.uniform(-cm.EAR_FOOT_Y, cm.EAR_FOOT_Y)
        lz = rng.uniform(0.1, cm.EAR_H - 0.1)
        x = cm.EAR_CX + lx
        a = ins(x, cm.EAR_SY[0] + ly, lz)
        b = ins(x, -(cm.EAR_SY[0] + ly), lz)
        if a != b:
            mismatches += 1
    assert mismatches == 0, f"{mismatches}/2000 ear mirror-symmetry mismatches"


# ---------------------------------------------------------------------------
# Check 2: validity, mass, bbox.
# ---------------------------------------------------------------------------

def test_solid_validity_mass_bbox(built):
    part, _ins = built
    solid = part.val()
    assert len(part.solids().vals()) == 1
    assert solid.isValid()
    vol = solid.Volume()
    assert vol > 0
    mass_g = vol / 1000.0 * cm.PETG_DENSITY_G_CM3
    assert mass_g <= cm.MASS_BUDGET_G, f"mass {mass_g:.2f} g exceeds budget {cm.MASS_BUDGET_G} g"
    bb = solid.BoundingBox()
    assert bb.xlen <= 150.0 and bb.ylen <= 65.001   # declared plate envelope


def test_kw12_arm_own_mass_under_ceiling():
    added_g = cm._kw12_mount_arm().val().Volume() / 1000.0 * cm.PETG_DENSITY_G_CM3
    assert added_g <= 10.0, f"KW12 mount added mass {added_g:.3f} g > 10 g ceiling"


# ---------------------------------------------------------------------------
# Check 3: pad face + pilot slots + zip groove.
# ---------------------------------------------------------------------------

def _find_pad_face(solid):
    """Find the horizontal (+Z normal), planar face near KW_PAD_Z and
    return (z, xmin, xmax, ymin, ymax)."""
    exp = TopExp_Explorer(solid.wrapped, TopAbs_FACE)
    matches = []
    while exp.More():
        f = TopoDS.Face_s(exp.Current())
        surf = BRepAdaptor_Surface(f, True)
        if surf.GetType() == GeomAbs_Plane:
            pln = surf.Plane()
            loc = pln.Location()
            dirn = pln.Axis().Direction()
            if abs(abs(dirn.Z()) - 1.0) < 1e-6 and abs(loc.Z() - cm.KW_PAD_Z) < 0.05:
                bnd = Bnd_Box()
                BRepBndLib.Add_s(f, bnd)
                xmin, ymin, zmin, xmax, ymax, zmax = bnd.Get()
                matches.append((loc.Z(), xmin, xmax, ymin, ymax))
        exp.Next()
    return matches


def test_pad_face_exists_horizontal_and_within_declared_extent(built):
    part, _ins = built
    matches = _find_pad_face(part.val())
    assert len(matches) == 1, f"expected exactly one pad-height planar face, found {len(matches)}"
    z, xmin, xmax, ymin, ymax = matches[0]
    assert abs(z - (cm.PLATE_T + cm.EAR_H + 10.0)) < 0.01, f"pad Z={z} != PLATE_T+EAR_H+10"
    assert 59.7 <= xmin <= 59.9, f"pad X0={xmin}"
    assert xmax <= cm.BASE_L / 2 + 1e-6, f"pad X1={xmax} exceeds plate half-length"
    assert abs(xmax - 69.0) < 0.05, f"pad X1={xmax} != 69.0"
    assert abs(ymin - 2.5) < 0.05, f"pad Y0={ymin} != 2.5"
    assert 23.9 <= ymax <= 24.1, f"pad Y1={ymax}"


@pytest.mark.parametrize("idx,expected_y", [(0, 7.75), (1, 17.25)])
def test_pilot_dimensions_and_position_measured(built, idx, expected_y):
    part, ins = built
    z_top = cm.KW_PAD_Z - 0.2
    r_narrow = _bisect_wall(ins, cm.DROP_X, expected_y, z_top, "y", 0.0, 1.5)
    assert abs(2 * r_narrow - 1.7) < 0.02, f"pilot {idx} narrow width = {2*r_narrow:.3f}, expected 1.7"
    pos = _bisect_wall(ins, cm.DROP_X, expected_y, z_top, "x", 0.0, 3.3)
    neg = _bisect_wall(ins, cm.DROP_X, expected_y, z_top, "x", 0.0, -3.3)
    assert abs(pos - 2.85) < 0.02 and abs(neg + 2.85) < 0.02, (
        f"pilot {idx} X half-length = ({neg:.3f},{pos:.3f}), expected +-2.85 "
        "(5.7 mm total slot length)"
    )
    center_x = cm.DROP_X + (pos + neg) / 2
    assert abs(center_x - cm.DROP_X) < 0.02, f"pilot {idx} not centered on DROP_X (measured {center_x:.3f})"

    def probe_z(zoff):
        return ins(cm.DROP_X, expected_y, cm.KW_PAD_Z - zoff)
    lo, hi = 0.2, 20.0
    for _ in range(45):
        mid = (lo + hi) / 2
        if probe_z(mid):
            hi = mid
        else:
            lo = mid
    depth = (lo + hi) / 2
    assert depth >= 4.99, f"pilot {idx} blind depth (along its own center axis) = {depth:.3f} mm, required >=5.0"


def test_zip_groove_present_on_x_faces_and_y_hi_but_not_front(built):
    part, ins = built
    z_mid = cm.PLATE_T + (cm.KW_GROOVE_Z0_LOCAL + cm.KW_GROOVE_Z1_LOCAL) / 2
    y_mid = (cm.KW_ARM_Y_LOWER + cm.KW_PAD_Y1) / 2
    x_mid = (cm.KW_PAD_X0 + cm.KW_PAD_X1) / 2
    assert not ins(cm.KW_PAD_X0 + cm.KW_GROOVE_DEPTH / 2, y_mid, z_mid), "X0-side groove not void"
    assert not ins(cm.KW_PAD_X1 - cm.KW_GROOVE_DEPTH / 2, y_mid, z_mid), "X1-side groove not void"
    assert not ins(x_mid, cm.KW_PAD_Y1 - cm.KW_GROOVE_DEPTH / 2, z_mid), "Y_hi-side groove not void"
    assert ins(x_mid, cm.KW_ARM_Y_LOWER + cm.KW_GROOVE_DEPTH / 2, z_mid), (
        "front (-Y) face is grooved -- expected it left flush per the "
        "implementer's own documented, deliberate omission"
    )


def test_front_pilot_center_axis_blind_depth_is_not_shallowed_by_groove(built):
    """Assignment's literal ask: does the groove shallow the front pilot's
    OWN blind depth (measured along its center axis, X=DROP_X)? No -- the
    groove only recesses the arm's X0/X1/Y_hi outer perimeter, and does not
    reach X=DROP_X (the hole's center, where both pilots are actually
    bored)."""
    part, ins = built
    front_y = 7.75
    z_bottom_of_required_depth = cm.KW_PAD_Z - cm.KW12_PILOT_DEPTH - 0.3
    assert ins(cm.DROP_X, front_y, z_bottom_of_required_depth), (
        "front pilot center-axis wall is void at required blind depth -- "
        "the groove IS shallowing the reported depth"
    )


# ---------------------------------------------------------------------------
# Check 4: printability -- no overhang > 45 deg except the declared step.
# ---------------------------------------------------------------------------

def test_lower_shaft_is_constant_no_overhang_prism(built):
    part, ins = built
    x_probe = 61.7   # clear of pilot X-elongation and both groove straps
    for z in (cm.PLATE_T + 1.0, cm.KW_TAPER_Z0 - 1.0):
        edge = _bisect_wall(ins, x_probe, 0.0, z, "y", 0.0, 15.0)
        assert abs(edge - cm.KW_ARM_Y_LOWER) < 0.02, (
            f"lower shaft front-face Y edge at z={z} = {edge:.3f}, "
            f"expected constant {cm.KW_ARM_Y_LOWER} (no taper below KW_TAPER_Z0)"
        )


def test_taper_is_exact_45deg_chamfer_then_declared_step(built):
    part, ins = built
    x_probe = 61.7
    samples = {}
    z = cm.KW_TAPER_Z0
    z_cap = cm.KW_PAD_Z - 0.05   # stay strictly below the top surface (avoid boundary ambiguity)
    while z <= z_cap:
        edge = _bisect_wall(ins, x_probe, 0.0, z, "y", 0.0, 15.0)
        samples[round(z, 3)] = edge
        z += 0.5
    if round(z_cap, 3) not in samples:
        samples[round(z_cap, 3)] = _bisect_wall(ins, x_probe, 0.0, z_cap, "y", 0.0, 15.0)
    # Chamfer band: KW_TAPER_Z0 .. KW_CHAMFER_Z1 (world) -- rise == run.
    z_chamfer_top = cm.PLATE_T + cm.KW_CHAMFER_Z1_LOCAL
    zs_sorted = sorted(k for k in samples if k <= z_chamfer_top + 0.01)
    for a, b in zip(zs_sorted, zs_sorted[1:]):
        dz = b - a
        dy = samples[a] - samples[b]   # Y edge should DECREASE as Z increases (widening toward the line)
        assert abs(dy - dz) < 0.02, (
            f"chamfer band [{a},{b}]: dz={dz:.3f} dy={dy:.3f} -- not an "
            "exact 45 deg run (rise != run)"
        )
    assert abs(samples[round(z_chamfer_top, 3)] - 4.0) < 0.02
    # Step band: a single instantaneous jump <= 1.5 mm, not a graded taper.
    step_dy = samples[round(z_chamfer_top, 3)] - 2.5   # 2.5 = KW_PAD_Y0
    assert 0.0 < step_dy <= 1.5 + 1e-6, f"step overhang = {step_dy:.3f} mm, must be in (0, 1.5]"


# ---------------------------------------------------------------------------
# Check 5: clearances (fresh boolean intersections).
# ---------------------------------------------------------------------------

def test_pulley_envelope_clearance(built):
    part, _ins = built
    axis_z = cm.PLATE_T + I.CORNER_MOUNT_AXIS_Z
    half_w = cm.PULLEY_GAP / 2
    env = (
        cq.Workplane("XZ").workplane(offset=half_w)
        .center(cm.EAR_CX, axis_z).circle(22.0 / 2).extrude(-(2 * half_w))
    )
    assert _vol(env.intersect(part)) < 1e-6


def test_nema17_motor_body_clearance(built):
    """42.3x42.3 face square, 38 mm axial body depth -- matches the real
    NEMA17 envelope and the implementer's own gusset-clearance test
    convention (tests/test_winch_geometry.py, motor_depth=38.0)."""
    part, _ins = built
    from cad import params as P
    axis_z = cm.PLATE_T + I.CORNER_MOUNT_AXIS_Z
    depth = 38.0
    y_c = cm.WALL_BACK_Y - depth / 2
    box = (
        cq.Workplane("XY").center(cm.WALL_CX, y_c).rect(P.NEMA17_FACE, depth)
        .extrude(P.NEMA17_FACE).translate((0, 0, axis_z - P.NEMA17_FACE / 2))
    )
    assert _vol(box.intersect(part)) < 1e-6


def test_csk_screw_x45_is_void_top_and_bottom(built):
    part, ins = built
    assert not ins(45.0, 0.0, cm.PLATE_T - 0.5)
    assert not ins(45.0, 0.0, 0.5)


def test_line_corridor_clear_horizontal_span_full_length(built):
    part, _ins = built
    axis_z = cm.PLATE_T + I.CORNER_MOUNT_AXIS_Z
    length = cm.EAR_CX - cm.WALL_CX
    corridor = (
        cq.Workplane("YZ").workplane(offset=cm.WALL_CX)
        .center(0, axis_z).circle(3.0).extrude(length)
    )
    assert _vol(corridor.intersect(part)) < 1e-6


def test_line_corridor_clear_vertical_drop_below_taper(built):
    part, _ins = built
    z_lo = cm.PLATE_T + I.CORNER_MOUNT_AXIS_Z
    z_hi = cm.KW_TAPER_Z0
    corridor = (
        cq.Workplane("XY").workplane(offset=z_lo)
        .center(cm.DROP_X, 0.0).circle(3.0).extrude(z_hi - z_lo)
    )
    assert _vol(corridor.intersect(part)) < 1e-6


# ---------------------------------------------------------------------------
# Check 6 -- THE KEY CHECK: bead/roller mechanism, from MEASURED mount
# geometry (pad face, pilot-hole positions), not corner_mount's own
# KW_ROLLER_* constants.
# ---------------------------------------------------------------------------

def _measure_roller_center(part, ins):
    pad_matches = _find_pad_face(part.val())
    assert len(pad_matches) == 1
    pad_z, pad_x0, pad_x1, pad_y0, pad_y1 = pad_matches[0]

    z_probe = pad_z - 0.2
    pos = _bisect_wall(ins, cm.DROP_X, 7.75, z_probe, "x", 0.0, 3.3)
    neg = _bisect_wall(ins, cm.DROP_X, 7.75, z_probe, "x", 0.0, -3.3)
    pilot_center_x = cm.DROP_X + (pos + neg) / 2   # the switch's real mount X (pilots are fixed hardware pitch)

    roller_x = pilot_center_x
    roller_y = pad_y0 - 1.5                          # KW12_ROLLER_OVERHANG_Y
    roller_z = pad_z + 12.0                           # KW12_LEVER_REST_H
    return roller_x, roller_y, roller_z, pad_z


def test_key_check_roller_x_lands_on_line_for_accepted_od_range(built):
    part, ins = built
    roller_x, _y, _z, _pad_z = _measure_roller_center(part, ins)
    tune_half = cm.KW_ROLLER_TUNE_RANGE / 2
    for od in (18.0, 20.0, 22.0):
        x_line = cm.EAR_CX + od / 2.0
        err_after_tune = max(0.0, abs(roller_x - x_line) - tune_half)
        assert err_after_tune <= 1.5, f"OD={od}: tuned X error {err_after_tune:.3f} mm > 1.5 mm"
    nominal_err = abs(roller_x - (cm.EAR_CX + I.CORNER_PULLEY_OD_NOM / 2.0))
    assert nominal_err <= 1.0, f"nominal untuned X error {nominal_err:.3f} mm > 1.0 mm"


def test_key_check_roller_y_reaches_the_line_with_margin(built):
    part, ins = built
    _x, roller_y, _z, _pad_z = _measure_roller_center(part, ins)
    assert abs(roller_y) <= 1.5, f"roller Y = {roller_y:.3f} mm, > 1.5 mm from the line's own Y=0"
    bead_r, roller_r = cm.KW_HOMING_BEAD_DIA_NOM / 2, cm.KW12_ROLLER_DIA / 2
    overlap = (bead_r + roller_r) - abs(roller_y)
    assert overlap >= 2.0, f"bead/roller Y overlap = {overlap:.3f} mm, required >= 2.0 mm"


def test_key_check_roller_z_beyond_pulley_and_above_pad(built):
    part, ins = built
    _x, _y, roller_z, pad_z = _measure_roller_center(part, ins)
    pulley_env_top = cm.PLATE_T + I.CORNER_MOUNT_AXIS_Z + 22.0 / 2
    assert roller_z > pulley_env_top, f"roller Z={roller_z} inside pulley envelope (top={pulley_env_top})"
    assert roller_z > pad_z, f"roller Z={roller_z} not above pad Z={pad_z}"


def test_key_check_switch_body_and_lever_envelope_clear_printed_material(built):
    """Switch body (20x6.4x10) seated on the measured pad, roller end
    toward -Y, plus an over-sized lever-sweep box up to the roller -- must
    not intersect any printed material except the pad's own contact
    plane."""
    part, ins = built
    roller_x, roller_y, roller_z, pad_z = _measure_roller_center(part, ins)
    body_y_c = 2.5 + cm.KW12_BODY_L / 2   # body spans Y=[2.5, 22.5]
    body = (
        cq.Workplane("XY").center(roller_x, body_y_c)
        .rect(cm.KW12_BODY_W, cm.KW12_BODY_L)
        .extrude(cm.KW12_BODY_H - 0.01)
        .translate((0, 0, pad_z + 0.01))   # excludes the shared contact skin
    )
    assert _vol(body.intersect(part)) < 1e-6, "switch body envelope intersects printed material"

    roller_r = cm.KW12_ROLLER_DIA / 2
    roller_env = (
        cq.Workplane("XY").center(roller_x, roller_y).circle(roller_r)
        .extrude(4.0).translate((0, 0, roller_z - 2.0))
    )
    assert _vol(roller_env.intersect(part)) < 1e-6, "roller envelope intersects printed material"


def test_key_check_actuation_direction_matches_bead_reel_in_direction():
    """Pressing the roller toward the mounting face (the pad, at the
    SMALLER Z of the two, since +Z runs down/away from the joist) means
    moving in -Z -- the SAME sign as the bead's own reel-in direction
    (interfaces/docstring: 'reel-in moves the bead -Z, toward the pulley').
    So: roller-press direction == bead reel-in direction == -Z. Confirmed
    purely from the frame convention and the measured pad/roller Z order
    (pad Z < roller Z at rest)."""
    part, ins = None, None
    part = cm.make()
    ins = _inside_fn(part.val())
    _x, _y, roller_z, pad_z = _measure_roller_center(part, ins)
    assert pad_z < roller_z, (
        "pad must sit at a SMALLER Z than the roller's resting position for "
        "'press toward the pad' to be the -Z direction"
    )


# ---------------------------------------------------------------------------
# Check 7: bead set-back consistency (firmware-derived, not just docstring).
# ---------------------------------------------------------------------------

def test_home_backoff_distance_matches_firmware_constants():
    import sys
    sys.path.insert(0, "/home/user/RoomCleaner")
    from roomcleaner.hardware.hw_config import STEPS_PER_M
    HOME_BACKOFF = 200   # firmware/roomcleaner_firmware/roomcleaner_firmware.ino
    backoff_mm = HOME_BACKOFF / STEPS_PER_M * 1000.0
    assert abs(backoff_mm - 3.93) < 0.02, f"HOME_BACKOFF travel = {backoff_mm:.3f} mm, docstring claims ~3.93 mm"


# ---------------------------------------------------------------------------
# Check 8: STEP round trip.
# ---------------------------------------------------------------------------

def test_step_round_trip_volume_and_bbox(built, tmp_path):
    part, _ins = built
    v0 = part.val().Volume()
    bb0 = part.val().BoundingBox()
    step_path = str(tmp_path / "corner_mount.step")
    cq.exporters.export(part, step_path)
    reimported = cq.importers.importStep(step_path)
    assert len(reimported.solids().vals()) == 1
    v1 = reimported.val().Volume()
    bb1 = reimported.val().BoundingBox()
    assert abs(v1 - v0) / v0 * 100 < 0.1
    assert abs(bb0.xlen - bb1.xlen) < 0.05
    assert abs(bb0.ylen - bb1.ylen) < 0.05
    assert abs(bb0.zlen - bb1.zlen) < 0.05


# ---------------------------------------------------------------------------
# Strict xfail wrappers for the two genuine defects found above -- kept as
# their own tests (rather than only relying on the raw asserts above being
# reported as FAIL) so the suite stays green while the defect stays on the
# record, per the assignment's instruction.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=True,
    reason=(
        "corner_mount rev D: both M2 pilot slots' outboard (+X) tuning-cap "
        "tip loses its enclosing wall for the deepest 1.5 mm of the nominal "
        "5.0 mm blind depth, breached by the X1-side zip-tie groove (groove "
        "Z band 37-41 mm world overlaps the pilot's own Z band 39.5-44.5 mm "
        "world). Self-tap thread engagement at the extreme +2 mm tuning "
        "position (needed for OD=22 mm pulleys) loses partial wall support "
        "over that 1.5 mm. See verification/corner_mount_revD_report.md "
        "section 3."
    ),
)
def test_XFAIL_pilot_outboard_tip_fully_enclosed_for_full_depth(built):
    part, ins = built
    cap_far_x = cm.DROP_X + cm.KW_ROLLER_TUNE_RANGE / 2 + 1.7 / 2
    for screw_y in cm.KW_SCREW_Y:
        z_bottom = cm.KW_PAD_Z - cm.KW12_PILOT_DEPTH + 0.1
        xs = [cap_far_x + i * 0.05 for i in range(int((cm.KW_PAD_X1 - cap_far_x) / 0.05) + 1)]
        assert any(ins(x, screw_y, z_bottom) for x in xs), "outboard tip wall breached"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "corner_mount rev D: the pad's own capping step (KW_PAD_Y0=2.5 mm "
        "from the line, tangent to the assumed bead's OWN 2.5 mm radius, "
        "not to the broader generic Ø6/r=3 mm line-position-margin "
        "corridor used everywhere else on this part) puts a small but real "
        "sliver of PRINTED material (1.125 mm^3) inside that generic "
        "corridor, confined to the pad's own Z band (KW_TAPER_Z0..KW_PAD_Z, "
        "41.0-44.5 mm world). The assignment's own rule: only the "
        "purchased switch (roller) may intrude above the taper; here "
        "printed material does too, by a small quantified amount. See "
        "verification/corner_mount_revD_report.md section 5."
    ),
)
def test_XFAIL_no_printed_material_above_taper_in_generic_corridor(built):
    part, _ins = built
    z_lo, z_hi = cm.KW_TAPER_Z0, cm.KW_PAD_Z
    corridor = (
        cq.Workplane("XY").workplane(offset=z_lo)
        .center(cm.DROP_X, 0.0).circle(3.0).extrude(z_hi - z_lo)
    )
    volume = _vol(corridor.intersect(part))
    assert volume < 1e-6, f"printed intrusion above taper = {volume:.4f} mm^3"
