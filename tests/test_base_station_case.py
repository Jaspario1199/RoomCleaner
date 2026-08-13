"""
Independent geometry verification for cad/parts/base_station_case.py (Gate 5,
geometry-verifier role). Builds the tray and lid directly from `make()` and
measures the actual BRep solids -- it does not trust the module's docstring
or comments.

Style follows tests/test_winch_geometry.py: exact BRep point-in-solid probes
(BRepClass3d_SolidClassifier), binary-search radius probes, and boolean
intersection/union checks, rather than mesh/STL sampling or single-point
presence checks alone. This file was hardened after an independent
verification pass (see verification/base_station_case_report.md) found that
several presence-only assertions ("is there a void at this one constant-
derived point?") missed real defects -- a swapped port width/height and a
missing countersink both left the single probed point void either way. The
checks below now measure actual sizes/positions on the built solid wherever
that verification report flagged a gap.

Skips entirely if cadquery is not installed (CI without the CAD extra).
"""

from __future__ import annotations

import pytest

cq = pytest.importorskip("cadquery")

from OCP.gp import gp_Pnt                                 # noqa: E402
from OCP.BRepClass3d import BRepClass3d_SolidClassifier   # noqa: E402
from OCP.TopAbs import TopAbs_IN                           # noqa: E402

from cad.parts import base_station_case as bsc            # noqa: E402
from cad.materials import MATERIALS                        # noqa: E402


BBOX_TOL = 0.3   # mm, matches tests/test_claw_geometry.py's convention
MASS_BUDGET_G = 150.0
# Safe upper radius (beyond a port's own edge) for a solid-material bisection
# probe: stays short of that SAME port's own flanking zip-tie hole, which
# starts at ZIP_TIE_OFFSET beyond the port edge and has its own ZIP_TIE_HOLE_D
# radius -- 0.3 mm short of that hole's near edge, for margin.
_SAFE_ZIP_MARGIN = bsc.ZIP_TIE_OFFSET - bsc.ZIP_TIE_HOLE_D / 2 - 0.3


def _inside_fn(solid):
    """Return f(x,y,z) -> True if that point is strictly inside solid
    material, using an exact BRep point classifier (not mesh-based)."""
    def f(x, y, z, tol=1e-6):
        c = BRepClass3d_SolidClassifier(solid.wrapped)
        c.Perform(gp_Pnt(x, y, z), tol)
        return c.State() == TopAbs_IN
    return f


def _bisect_wall(inside, cx, cy, cz, axis, lo=0.0, hi=6.0, iters=50):
    """From a void center point, binary-search outward along `axis` for the
    void -> solid transition radius. `lo` must be void, `hi` must be solid.
    Matches the idiom used by tests/test_winch_geometry.py."""
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


def _measure_rect_port(solid, x_wall, y_center, z_center, xy_tol=3.0, search=15.0):
    """Measure a rectangular port's actual built opening by finding its
    planar ceiling/floor faces (Y-spanning, Z-flat) near the given wall
    position, and returning (y_span, z_span, z_min, z_max). This reads the
    real BRep face geometry -- it cannot be fooled by a swapped width/height
    the way a single center-point presence probe can."""
    hits = []
    for f in solid.Faces():
        if f.geomType() != "PLANE":
            continue
        c = f.Center()
        if abs(c.x - x_wall) < xy_tol and abs(c.y - y_center) < search and abs(c.z - z_center) < search:
            bb = f.BoundingBox()
            if bb.ylen > 0.5 and bb.zlen < 0.5:
                hits.append((c.z, bb.ylen))
    assert len(hits) >= 2, f"expected >=2 port ceiling/floor faces near x={x_wall}, found {len(hits)}"
    zs = sorted(h[0] for h in hits)
    y_span = hits[0][1]
    return y_span, zs[-1] - zs[0], zs[0], zs[-1]


@pytest.fixture(scope="module")
def built():
    tray, lid = bsc.make()
    return {"tray": tray, "lid": lid}


# ---------------------------------------------------------------------------
# Check 1: build, single valid solid, bounding box.
# ---------------------------------------------------------------------------

def test_tray_is_single_valid_solid(built):
    tray = built["tray"]
    assert tray.val().isValid()
    solids = tray.solids().vals()
    assert len(solids) == 1, f"tray: expected 1 solid, got {len(solids)}"


def test_lid_is_single_valid_solid(built):
    lid = built["lid"]
    assert lid.val().isValid()
    solids = lid.solids().vals()
    assert len(solids) == 1, f"lid: expected 1 solid, got {len(solids)}"


def test_tray_bounding_box(built):
    bb = built["tray"].val().BoundingBox()
    expected = (bsc.OUTER_L, bsc.OUTER_W, bsc.FLOOR_T + bsc.TRAY_WALL_H)
    measured = (bb.xlen, bb.ylen, bb.zlen)
    for m, e, axis in zip(measured, expected, "xyz"):
        assert abs(m - e) <= BBOX_TOL, f"tray {axis}len: expected {e}, measured {m}"


def test_lid_bounding_box(built):
    bb = built["lid"].val().BoundingBox()
    expected = (bsc.OUTER_L, bsc.OUTER_W, bsc.LID_CAVITY_H + bsc.LID_ROOF_T)
    measured = (bb.xlen, bb.ylen, bb.zlen)
    for m, e, axis in zip(measured, expected, "xyz"):
        assert abs(m - e) <= BBOX_TOL, f"lid {axis}len: expected {e}, measured {m}"


# ---------------------------------------------------------------------------
# Check 2: Uno R3 mounting-hole pattern, probed on the built tray.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("index", range(4))
def test_uno_hole_position_has_insert_bore(built, index):
    """Each researched Uno hole XY must sit over a boss whose insert bore
    (M3_THREAD_HOLE dia) is open (void) at mid-boss height, and the boss
    material itself must be present just outside that bore radius."""
    x, y = bsc.UNO_HOLE_XY[index]
    inside = _inside_fn(built["tray"].val())
    z_mid = bsc.FLOOR_T + bsc.BOSS_INSERT_DEPTH / 2

    assert not inside(x, y, z_mid), (
        f"Uno hole {index} at ({x:.2f},{y:.2f}): insert bore is not void at z={z_mid:.2f}"
    )
    # Just inside the boss OD (but outside the bore) must be solid PETG.
    r_solid = (bsc.M3_THREAD_HOLE / 2 + bsc.BOSS_OD / 2) / 2
    assert inside(x + r_solid, y, z_mid), (
        f"Uno hole {index} at ({x:.2f},{y:.2f}): expected boss material at r={r_solid:.2f}"
    )


def test_uno_hole_spacing_matches_researched_pattern():
    """Cross-check: the built UNO_HOLE_XY constants must reproduce the
    researched board-relative pattern (68.6 x 53.4 mm board, holes per
    module docstring) once re-centered on the board origin. NOTE: this only
    checks the module is internally self-consistent (both sides come from
    bsc's own constants) -- see test_uno_hole_pairwise_distances_match_
    canonical_pattern below for a check against an independently-cited
    reference that could catch a wrong *constant*, not just a construction
    bug."""
    for (gx, gy), (bx, by) in zip(bsc.UNO_HOLE_XY, bsc.UNO_HOLE_XY_BOARD):
        assert abs((gx - bsc.UNO_ORIGIN_X) - bx) < 1e-6
        assert abs((gy - bsc.UNO_ORIGIN_Y) - by) < 1e-6
    assert bsc.UNO_L == pytest.approx(68.6)
    assert bsc.UNO_W == pytest.approx(53.4)


# Independent literal citation of the canonical Uno R3 hole pattern (see
# verification/base_station_case_report.md §2 and the module docstring's
# KiCad cross-reference). Hardcoded here rather than read from
# bsc.UNO_HOLE_XY_BOARD, so this test cannot pass merely because the module
# is internally self-consistent -- it fails if a future edit reintroduces
# the old (incorrect) 15.24 mm value at the first hole, or any other drift.
CANONICAL_UNO_HOLES_BOARD_MM = (
    (13.97, 2.54),
    (15.24, 50.80),
    (66.04, 7.62),
    (66.04, 35.56),
)
CANONICAL_UNO_BOARD_L_MM = 68.6
CANONICAL_UNO_BOARD_W_MM = 53.4


def _pairwise_distances(points):
    out = []
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            (x1, y1), (x2, y2) = points[i], points[j]
            out.append(((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5)
    return sorted(out)


def test_uno_hole_pairwise_distances_match_canonical_pattern(built):
    """Measure each boss's ACTUAL (x, y) center on the built tray -- via
    void/solid edge bisection, not by trusting bsc.UNO_HOLE_XY -- and
    confirm the pairwise hole-to-hole distances match the independently
    cited canonical pattern above. Distances (not raw positions) are the
    right invariant here: they are unaffected by the overall board-centering
    choice and directly catch the kind of single-coordinate drift the
    verification report found (a 1.27 mm error at one hole changes 3 of the
    6 pairwise distances measurably)."""
    inside = _inside_fn(built["tray"].val())
    z_mid = bsc.FLOOR_T + bsc.BOSS_INSERT_DEPTH / 2

    def edge(seed_x, seed_y, axis, sign, hi=3.0, iters=50):
        # hi=3.0: strictly between the insert-bore radius (M3_THREAD_HOLE/2
        # = 2.0 mm, must be void) and the boss OD radius (BOSS_OD/2 = 4.0 mm,
        # beyond which the boss ends and the surrounding cavity is void too).
        """Bisect from the (void) seed point outward in the +/-`sign`
        direction along `axis` for the void -> solid transition, returning
        the transition's absolute coordinate on that axis."""
        lo = 0.0
        def probe(r):
            x, y = seed_x, seed_y
            if axis == "x":
                x = seed_x + sign * r
            else:
                y = seed_y + sign * r
            return inside(x, y, z_mid)
        assert not probe(lo), f"seed ({seed_x},{seed_y}) is not void"
        assert probe(hi), f"bound at r={hi} from ({seed_x},{seed_y}) is not solid"
        for _ in range(iters):
            mid = (lo + hi) / 2
            if probe(mid):
                hi = mid
            else:
                lo = mid
        r = (lo + hi) / 2
        return (seed_x if axis == "x" else seed_y) + sign * r

    origin_x = -CANONICAL_UNO_BOARD_L_MM / 2
    origin_y = -CANONICAL_UNO_BOARD_W_MM / 2
    measured_centers = []
    for bx, by in CANONICAL_UNO_HOLES_BOARD_MM:
        seed_x, seed_y = origin_x + bx, origin_y + by
        x_lo = edge(seed_x, seed_y, "x", -1)
        x_hi = edge(seed_x, seed_y, "x", 1)
        y_lo = edge(seed_x, seed_y, "y", -1)
        y_hi = edge(seed_x, seed_y, "y", 1)
        measured_centers.append(((x_lo + x_hi) / 2, (y_lo + y_hi) / 2))

    expected_dists = _pairwise_distances(CANONICAL_UNO_HOLES_BOARD_MM)
    measured_dists = _pairwise_distances(measured_centers)
    for expected, measured in zip(expected_dists, measured_dists):
        assert abs(expected - measured) < 0.1, (
            f"hole pairwise distance {measured:.3f} mm != canonical {expected:.3f} mm"
        )


# ---------------------------------------------------------------------------
# Check 3: interior clearance above the Uno PCB, probed as an actual empty
# vertical column through the assembled tray+lid stack.
# ---------------------------------------------------------------------------

def test_interior_clearance_above_pcb_meets_minimum(built):
    tray, lid = built["tray"], built["lid"]
    lid_z = bsc.FLOOR_T + bsc.TRAY_WALL_H
    assembled = tray.union(lid.translate((0, 0, lid_z)))
    inside = _inside_fn(assembled.val())

    z0 = bsc.FLOOR_T + bsc.UNO_TOP_Z                 # Uno PCB top, global Z
    z1 = bsc.FLOOR_T + bsc.TOTAL_INTERIOR_H          # lid interior ceiling, global Z
    clearance = z1 - z0
    assert clearance >= bsc.CLEARANCE_ABOVE_PCB_MIN, (
        f"interior clearance above PCB {clearance:.2f} mm < required "
        f"{bsc.CLEARANCE_ABOVE_PCB_MIN} mm"
    )

    # Probe the column empty at 5 mm steps at the case center (clear of the
    # off-center Uno bosses, corner posts, and wall ports).
    z = z0
    while z <= z1:
        assert not inside(0.0, 0.0, z), f"material blocks the PCB clearance column at z={z:.2f}"
        z += 5.0


# ---------------------------------------------------------------------------
# Check 4: lid/tray screw-hole alignment (4 corner posts).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("index", range(4))
def test_lid_tray_corner_screw_holes_align(built, index):
    x, y = bsc.CORNER_POST_XY[index]
    tray_inside = _inside_fn(built["tray"].val())
    lid_inside = _inside_fn(built["lid"].val())

    # Tray post top has an open insert bore.
    z_bore = bsc.FLOOR_T + bsc.TRAY_WALL_H - bsc.CORNER_POST_INSERT_DEPTH / 2
    assert not tray_inside(x, y, z_bore), (
        f"corner post {index} at ({x:.2f},{y:.2f}): insert bore not void at z={z_bore:.2f}"
    )
    # Post material present just outside the bore.
    r_solid = (bsc.M3_THREAD_HOLE / 2 + bsc.CORNER_POST_OD / 2) / 2
    assert tray_inside(x + r_solid, y, z_bore)

    # Lid clearance hole, same XY, straight through the lid thickness.
    z_lid_mid = (bsc.LID_CAVITY_H + bsc.LID_ROOF_T) / 2
    assert not lid_inside(x, y, z_lid_mid), (
        f"corner post {index} at ({x:.2f},{y:.2f}): lid clearance hole not void at z={z_lid_mid:.2f}"
    )


# ---------------------------------------------------------------------------
# Check 4b: the Uno board envelope must not intersect the tray at all --
# this is the check that would have caught the corner-post/board collision
# (verification report §3): 245 mm^3 of interference before the fix.
# ---------------------------------------------------------------------------

def test_uno_board_envelope_does_not_intersect_tray(built):
    board = (
        cq.Workplane("XY")
        .box(bsc.UNO_L, bsc.UNO_W, bsc.UNO_PCB_T, centered=(True, True, False))
        .translate((0, 0, bsc.FLOOR_T + bsc.BOSS_H))
    )
    intersection = board.intersect(built["tray"])
    solids = intersection.solids().vals()
    vol = sum(s.Volume() for s in solids) if solids else 0.0
    assert vol < 1e-6, f"Uno board envelope intersects the tray: {vol:.3f} mm^3 (expected 0)"


# ---------------------------------------------------------------------------
# Check 5: ventilation slots present (probed at every computed slot center --
# an exhaustive presence probe standing in for an area measurement, since
# each probed void is one VENT_SLOT_W x VENT_SLOT_L opening of known area).
# ---------------------------------------------------------------------------

def test_lid_vent_slots_present(built):
    inside = _inside_fn(built["lid"].val())
    vent_x = bsc._grid_positions(bsc.VENT_LID_COLS, bsc.VENT_SLOT_PITCH * 2.0)
    vent_y = bsc._grid_positions(bsc.VENT_LID_ROWS, bsc.VENT_SLOT_PITCH * 3.0)
    z_roof_mid = bsc.LID_CAVITY_H + bsc.LID_ROOF_T / 2
    n_checked = 0
    for x in vent_x:
        for y in vent_y:
            assert not inside(x, y, z_roof_mid), f"lid vent slot at ({x:.2f},{y:.2f}) not void"
            n_checked += 1
    expected_area_mm2 = n_checked * bsc.VENT_SLOT_W * bsc.VENT_SLOT_L
    assert n_checked == bsc.VENT_LID_COLS * bsc.VENT_LID_ROWS
    assert expected_area_mm2 > 300.0, "lid vent area implausibly small"


def test_tray_side_wall_vent_slots_present(built):
    inside = _inside_fn(built["tray"].val())
    vent_x = bsc._grid_positions(bsc.VENT_SIDE_COLS, bsc.VENT_SLOT_PITCH * 2.0)
    half_w = bsc.OUTER_W / 2
    n_checked = 0
    for sign in (-1, 1):
        y_wall = sign * (half_w - bsc.WALL / 2)   # mid-wall thickness
        for x in vent_x:
            for z in bsc.VENT_SIDE_ROWS_Z:
                assert not inside(x, y_wall, z), (
                    f"side-wall vent at (x={x:.2f}, y={y_wall:.2f}, z={z:.2f}) not void"
                )
                n_checked += 1
    assert n_checked == 2 * bsc.VENT_SIDE_COLS * len(bsc.VENT_SIDE_ROWS_Z)


# ---------------------------------------------------------------------------
# Check 6: port openings, measured (not just probed for presence at one
# constant-derived point -- see verification report §6/§11 on why a bare
# presence check at the port center is satisfied by a port of ANY size).
# ---------------------------------------------------------------------------

def test_usb_port_measures_documented_width_and_height(built):
    """Reproduces verification report §6's own methodology: find the port's
    actual ceiling/floor faces and measure their span, rather than probing a
    single center point (which a swapped width/height still passes)."""
    x_in = -bsc.OUTER_L / 2
    y_span, z_span, z_lo, z_hi = _measure_rect_port(
        built["tray"].val(), x_in, bsc.USB_PORT_Y, bsc.USB_PORT_CTR_Z
    )
    assert y_span == pytest.approx(bsc.USB_SLOT_W, abs=0.05), (
        f"USB port Y-width measured {y_span:.2f} mm, documented {bsc.USB_SLOT_W} mm"
    )
    assert z_span == pytest.approx(bsc.USB_SLOT_H, abs=0.05), (
        f"USB port Z-height measured {z_span:.2f} mm, documented {bsc.USB_SLOT_H} mm"
    )
    expected_z_lo = bsc.USB_PORT_CTR_Z - bsc.USB_SLOT_H / 2
    assert z_lo == pytest.approx(expected_z_lo, abs=0.05), (
        f"USB port bottom measured z={z_lo:.2f} mm, expected {expected_z_lo:.2f} mm "
        "(the Uno-connector-layer height per the module docstring)"
    )


def test_dc_port_open_and_diameter(built):
    inside = _inside_fn(built["tray"].val())
    x_in = -bsc.OUTER_L / 2 + bsc.WALL / 2
    assert not inside(x_in, bsc.DC_PORT_Y, bsc.TERMINAL_PORT_CTR_Z), "DC power port not open"
    # hi is kept in the narrow solid band between this port's own edge and
    # its own flanking zip-tie hole (not the full diameter, and not
    # ZIP_TIE_OFFSET, both of which can overshoot into a hole).
    hi = bsc.DC_HOLE_D / 2 + _SAFE_ZIP_MARGIN
    r = _bisect_wall(inside, x_in, bsc.DC_PORT_Y, bsc.TERMINAL_PORT_CTR_Z, "y", hi=hi)
    assert r == pytest.approx(bsc.DC_HOLE_D / 2, abs=0.1)


@pytest.mark.parametrize("index", range(5))
def test_output_wall_ports_open_and_diameter(built, index):
    inside = _inside_fn(built["tray"].val())
    x_out = bsc.OUTER_L / 2 - bsc.WALL / 2
    y = bsc.OUTPUT_PORT_Y[index]
    kind = bsc.OUTPUT_PORT_KIND[index]
    expected_dia = bsc.ENDSTOP_PORT_D if kind == "endstop" else bsc.MOTOR_PORT_D
    assert not inside(x_out, y, bsc.TERMINAL_PORT_CTR_Z), f"{kind} port {index} not open"
    # hi stays inside the narrow solid band between this port's own edge and
    # its OWN flanking zip-tie hole -- neither the full diameter nor
    # ZIP_TIE_OFFSET is safe here, both can overshoot into that zip-tie hole
    # (or, at insufficient pitch, into a neighboring port -- see the
    # OUTPUT_PORT_PITCH derivation in the module for why 17 mm is required).
    hi = expected_dia / 2 + _SAFE_ZIP_MARGIN
    r = _bisect_wall(inside, x_out, y, bsc.TERMINAL_PORT_CTR_Z, "y", hi=hi)
    assert r == pytest.approx(expected_dia / 2, abs=0.1), (
        f"{kind} port {index} measured dia {2*r:.2f} mm, expected {expected_dia} mm"
    )


def test_zip_tie_holes_present(built):
    """Verification report §11 gap #2: zip-tie holes were never probed
    anywhere in the previous test file despite 14 existing in the design."""
    inside = _inside_fn(built["tray"].val())
    x_in = -bsc.OUTER_L / 2 + bsc.WALL / 2
    x_out = bsc.OUTER_L / 2 - bsc.WALL / 2
    n_checked = 0

    for sy in (-1, 1):
        y = bsc.USB_PORT_Y + sy * (bsc.USB_SLOT_W / 2 + bsc.ZIP_TIE_OFFSET)
        assert not inside(x_in, y, bsc.USB_PORT_CTR_Z), f"USB zip-tie hole at y={y:.2f} not open"
        n_checked += 1
    for sy in (-1, 1):
        y = bsc.DC_PORT_Y + sy * (bsc.DC_HOLE_D / 2 + bsc.ZIP_TIE_OFFSET)
        assert not inside(x_in, y, bsc.TERMINAL_PORT_CTR_Z), f"DC zip-tie hole at y={y:.2f} not open"
        n_checked += 1
    # +X wall zip ties are Z-FLANKING (above/below each port, at that port's
    # own Y), not Y-flanking -- see the module's ZIP_TIE_OFFSET/
    # OUTPUT_PORT_PITCH comment for why (residual defect from the second
    # verification pass: Y-flanking zip ties on differently-sized adjacent
    # ports collided with each other at the motor/endstop boundaries).
    for y, kind in zip(bsc.OUTPUT_PORT_Y, bsc.OUTPUT_PORT_KIND):
        dia = bsc.ENDSTOP_PORT_D if kind == "endstop" else bsc.MOTOR_PORT_D
        for sz in (-1, 1):
            zz = bsc.TERMINAL_PORT_CTR_Z + sz * (dia / 2 + bsc.ZIP_TIE_OFFSET)
            assert not inside(x_out, y, zz), (
                f"{kind} zip-tie hole at (y={y:.2f}, z={zz:.2f}) not open"
            )
            n_checked += 1
    assert n_checked == 14


# ---------------------------------------------------------------------------
# Check 6a2: +X wall adjacent-void wall-thickness scan, on the BUILT SOLID --
# the second verification pass's own model. It found the residual defect
# (endstop <-> motor zip-tie holes merging at 0 mm wall) via a fine Y-profile
# scan across the wall plus direct edge probes, specifically because a
# constants-only assertion checked port-to-neighbor-port but never zip-tie-
# to-zip-tie. These two tests reproduce that scan against the actual solid
# (not bsc's constants) and check EVERY adjacent void pair, in both
# directions the design now uses (Y for port-to-port, Z for port-to-own-
# zip-tie).
# ---------------------------------------------------------------------------

def _void_runs(inside, positions, x, y, z, axis):
    """Walk `positions` along `axis` (holding the other two coordinates at
    x/y/z) and return a list of (start, end) void runs -- a direct measurement
    of the built solid, not a computation from constants."""
    runs = []
    cur = None
    for p in positions:
        px, py, pz = x, y, z
        if axis == "y":
            py = p
        else:
            pz = p
        void = not inside(px, py, pz)
        if void and cur is None:
            cur = [p, p]
        elif void:
            cur[1] = p
        elif cur is not None:
            runs.append(tuple(cur))
            cur = None
    if cur is not None:
        runs.append(tuple(cur))
    return runs


def test_output_wall_y_scan_has_five_distinct_ports_with_min_wall(built):
    """Fine Y-profile scan across the +X wall at TERMINAL_PORT_CTR_Z must
    show exactly 5 void runs (one per port, none merged with a neighbor --
    this is precisely how the original port-pitch defect and this residual
    defect were both found), each matching its port's own diameter, with
    >= MIN_WALL_GAP of solid wall between every adjacent pair."""
    inside = _inside_fn(built["tray"].val())
    x_out = bsc.OUTER_L / 2 - bsc.WALL / 2
    # Span generously past the outermost port, but clipped to stay inside the
    # actual wall (the CORNER_R-fillet-safe flat region) so the scan doesn't
    # walk off the wall's own Y extent into the void beyond the case, which
    # would show up as spurious extra "runs".
    wanted_span = bsc.OUTPUT_PORT_Y[-1] + bsc.ENDSTOP_PORT_D / 2 + bsc.ZIP_TIE_OFFSET + bsc.ZIP_TIE_HOLE_D + 3.0
    wall_safe_span = bsc.OUTER_W / 2 - bsc.CORNER_R - 1.0
    span = min(wanted_span, wall_safe_span)
    positions = [round(-span + 0.25 * i, 3) for i in range(int(2 * span / 0.25) + 1)]
    runs = _void_runs(inside, positions, x_out, None, bsc.TERMINAL_PORT_CTR_Z, "y")

    assert len(runs) == 5, f"expected 5 distinct port openings on the +X wall, scan found {len(runs)}: {runs}"

    expected_dias = [bsc.ENDSTOP_PORT_D if k == "endstop" else bsc.MOTOR_PORT_D for k in bsc.OUTPUT_PORT_KIND]
    for (start, end), expected_dia in zip(runs, expected_dias):
        width = end - start
        assert width == pytest.approx(expected_dia, abs=0.5), (
            f"port run {start:.2f}-{end:.2f} (width {width:.2f}) != expected diameter {expected_dia}"
        )

    for i in range(len(runs) - 1):
        gap = runs[i + 1][0] - runs[i][1]
        assert gap >= bsc.MIN_WALL_GAP, (
            f"+X wall: only {gap:.2f} mm of solid wall between port runs {i} and {i+1} "
            f"(need >= {bsc.MIN_WALL_GAP} mm)"
        )


@pytest.mark.parametrize("index", range(5))
def test_output_wall_z_scan_port_and_own_zip_ties_have_min_wall(built, index):
    """Per-port Z-profile scan (fixed Y = that port's own center) must show
    exactly 3 void runs (bottom zip-tie, port body, top zip-tie) with
    >= MIN_WALL_GAP of solid wall between each -- the direction the residual
    defect's fix (Z-flanking zip ties) actually relies on."""
    inside = _inside_fn(built["tray"].val())
    x_out = bsc.OUTER_L / 2 - bsc.WALL / 2
    y = bsc.OUTPUT_PORT_Y[index]
    kind = bsc.OUTPUT_PORT_KIND[index]
    dia = bsc.ENDSTOP_PORT_D if kind == "endstop" else bsc.MOTOR_PORT_D

    z_half_span = dia / 2 + bsc.ZIP_TIE_OFFSET + bsc.ZIP_TIE_HOLE_D / 2 + 2.0
    z_lo = bsc.TERMINAL_PORT_CTR_Z - z_half_span
    z_hi = bsc.TERMINAL_PORT_CTR_Z + z_half_span
    n = int((z_hi - z_lo) / 0.1) + 1
    positions = [z_lo + 0.1 * i for i in range(n)]
    runs = _void_runs(inside, positions, x_out, y, None, "z")

    assert len(runs) == 3, f"port {index} ({kind}): expected 3 void runs (zip/port/zip), found {len(runs)}: {runs}"

    port_run = runs[1]
    assert (port_run[1] - port_run[0]) == pytest.approx(dia, abs=0.5)

    for i in range(2):
        gap = runs[i + 1][0] - runs[i][1]
        assert gap >= bsc.MIN_WALL_GAP, (
            f"port {index} ({kind}): only {gap:.2f} mm of solid wall between "
            f"runs {i} and {i+1} (need >= {bsc.MIN_WALL_GAP} mm)"
        )


# ---------------------------------------------------------------------------
# Check 6b: external mounting-hole countersink, measured at two Z levels
# (verification report §8: the previous implementation cut the countersink
# cone ~18 mm up in empty cavity air and produced a plain, un-countersunk
# clearance hole; a single presence probe at floor mid-thickness could not
# tell the difference between a real countersink and a plain hole).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("index", range(4))
def test_external_mount_hole_countersink_widens_at_outside_face(built, index):
    inside = _inside_fn(built["tray"].val())
    x, y = bsc.MOUNT_HOLE_XY[index]

    z_outside = 0.3   # near the exterior (bottom) floor face
    z_inside = bsc.FLOOR_T - 0.3   # near the interior (top) floor face

    r_outside = _bisect_wall(inside, x, y, z_outside, "x", hi=3.5)
    r_inside = _bisect_wall(inside, x, y, z_inside, "x", hi=2.35)

    assert r_outside > (bsc.MOUNT_HOLE_SHANK_DIA / 2) + 0.5, (
        f"mount hole {index}: outside-face radius {r_outside:.2f} mm does not widen "
        f"beyond the shank ({bsc.MOUNT_HOLE_SHANK_DIA/2} mm) -- no countersink cut"
    )
    assert r_inside == pytest.approx(bsc.MOUNT_HOLE_SHANK_DIA / 2, abs=0.1), (
        f"mount hole {index}: inside-face radius {r_inside:.2f} mm should be shank-only "
        f"({bsc.MOUNT_HOLE_SHANK_DIA/2} mm), not countersunk"
    )


# ---------------------------------------------------------------------------
# Check 7: mass rollup.
# ---------------------------------------------------------------------------

def test_combined_mass_within_budget(built):
    density = MATERIALS["PETG"]["density_g_cm3"]
    tray_g = built["tray"].val().Volume() / 1000.0 * density
    lid_g = built["lid"].val().Volume() / 1000.0 * density
    total_g = tray_g + lid_g
    assert total_g > 0
    assert total_g <= MASS_BUDGET_G, f"combined mass {total_g:.1f} g exceeds {MASS_BUDGET_G} g budget"
