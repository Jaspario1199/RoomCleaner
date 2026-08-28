"""
Independent geometry verification for cad/parts/camera_case_overhead.py
(Gate 5, geometry-verifier role). Builds the shell and bezel directly from
`make()` and measures the actual BRep solids -- it does not trust the
module's docstring or comments.

Style follows tests/test_base_station_case.py: exact BRep point-in-solid
probes (BRepClass3d_SolidClassifier) and binary-search radius/edge probes,
rather than trusting the module's own constants to describe what got built.

Skips entirely if cadquery is not installed (CI without the CAD extra).
"""

from __future__ import annotations

import pytest

cq = pytest.importorskip("cadquery")

from OCP.gp import gp_Pnt                                 # noqa: E402
from OCP.BRepClass3d import BRepClass3d_SolidClassifier   # noqa: E402
from OCP.TopAbs import TopAbs_IN                           # noqa: E402

from cad.parts import camera_case_overhead as cco          # noqa: E402
from cad.materials import MATERIALS                         # noqa: E402


BBOX_TOL = 0.3   # mm, matches tests/test_base_station_case.py's convention


def _inside_fn(solid):
    """Return f(x,y,z) -> True if that point is strictly inside solid
    material, using an exact BRep point classifier (not mesh-based)."""
    def f(x, y, z, tol=1e-6):
        c = BRepClass3d_SolidClassifier(solid.wrapped)
        c.Perform(gp_Pnt(x, y, z), tol)
        return c.State() == TopAbs_IN
    return f


def _bisect(inside, cx, cy, cz, axis, lo=0.0, hi=10.0, iters=50):
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


@pytest.fixture(scope="module")
def built():
    shell, bezel = cco.make()
    return {"shell": shell, "bezel": bezel}


# ---------------------------------------------------------------------------
# Check 1: build, single valid solid, bounding box.
# ---------------------------------------------------------------------------

def test_shell_is_single_valid_solid(built):
    shell = built["shell"]
    assert shell.val().isValid()
    solids = shell.solids().vals()
    assert len(solids) == 1, f"shell: expected 1 solid, got {len(solids)}"


def test_bezel_is_single_valid_solid(built):
    bezel = built["bezel"]
    assert bezel.val().isValid()
    solids = bezel.solids().vals()
    assert len(solids) == 1, f"bezel: expected 1 solid, got {len(solids)}"


def test_shell_bounding_box(built):
    bb = built["shell"].val().BoundingBox()
    expected = (cco.PLATE, cco.PLATE, cco.PLATE_THK + cco.SKIRT_H)
    measured = (bb.xlen, bb.ylen, bb.zlen)
    for m, e, axis in zip(measured, expected, "xyz"):
        assert abs(m - e) <= BBOX_TOL, f"shell {axis}len: expected {e}, measured {m}"


def test_bezel_bounding_box(built):
    bb = built["bezel"].val().BoundingBox()
    expected = (cco.PLATE, cco.PLATE, cco.BEZEL_T)
    measured = (bb.xlen, bb.ylen, bb.zlen)
    for m, e, axis in zip(measured, expected, "xyz"):
        assert abs(m - e) <= BBOX_TOL, f"bezel {axis}len: expected {e}, measured {m}"


# ---------------------------------------------------------------------------
# Check 2: lens opening diameter, measured via void-radius bisection (not a
# single presence probe -- that would pass for a hole of ANY size).
# ---------------------------------------------------------------------------

def test_lens_opening_diameter(built):
    inside = _inside_fn(built["bezel"].val())
    z_mid = cco.BEZEL_T / 2
    r = _bisect(inside, 0.0, 0.0, z_mid, "x", hi=cco.PLATE / 2 - 1.0)
    measured_dia = 2 * r
    assert measured_dia == pytest.approx(cco.LENS_DIA, abs=0.1), (
        f"lens opening measured {measured_dia:.2f} mm, expected {cco.LENS_DIA} mm"
    )


def test_lens_opening_diameter_perpendicular_axis(built):
    """Same measurement along Y, to catch an accidental non-circular cut."""
    inside = _inside_fn(built["bezel"].val())
    z_mid = cco.BEZEL_T / 2
    r = _bisect(inside, 0.0, 0.0, z_mid, "y", hi=cco.PLATE / 2 - 1.0)
    measured_dia = 2 * r
    assert measured_dia == pytest.approx(cco.LENS_DIA, abs=0.1), (
        f"lens opening (Y axis) measured {measured_dia:.2f} mm, expected {cco.LENS_DIA} mm"
    )


# ---------------------------------------------------------------------------
# Check 3: standoff hole pattern at CAM_HOLE_PITCH (28 mm square), probed on
# the built shell.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("index", range(4))
def test_standoff_hole_position_and_pitch(built, index):
    x, y = cco.STANDOFF_XY[index]
    assert abs(x) == pytest.approx(cco.CAM_HOLE_PITCH / 2, abs=1e-6)
    assert abs(y) == pytest.approx(cco.CAM_HOLE_PITCH / 2, abs=1e-6)

    inside = _inside_fn(built["shell"].val())
    z_mid = -cco.STANDOFF_H / 2   # mid-post height, well inside the pilot hole
    assert not inside(x, y, z_mid), (
        f"standoff {index} at ({x:.2f},{y:.2f}): pilot hole not void at z={z_mid:.2f}"
    )
    # Just outside the M2 pilot but inside the post OD must be solid PETG.
    r_solid = (cco.M2_TAP / 2 + cco.STANDOFF_POST_DIA / 2) / 2
    assert inside(x + r_solid, y, z_mid), (
        f"standoff {index} at ({x:.2f},{y:.2f}): expected post material at r={r_solid:.2f}"
    )


def test_standoff_pitch_measured_via_pairwise_distance(built):
    """Reproduces test_base_station_case.py's pairwise-distance idiom: measure
    each hole's actual (x,y) center on the built solid (not the module's own
    constants) and confirm the square pitch is CAM_HOLE_PITCH."""
    inside = _inside_fn(built["shell"].val())
    z_mid = -cco.STANDOFF_H / 2

    # hi must land strictly between the pilot-hole radius (void) and the
    # post OD radius (beyond which the post ends and the surrounding cavity
    # is void again) -- matches test_base_station_case.py's own convention
    # for the same kind of boss-edge bisection.
    _edge_hi = (cco.M2_TAP / 2 + cco.STANDOFF_POST_DIA / 2) / 2

    def edge(seed_x, seed_y, axis, sign, hi=_edge_hi, iters=50):
        lo = 0.0
        def probe(r):
            x, y = seed_x, seed_y
            if axis == "x":
                x = seed_x + sign * r
            else:
                y = seed_y + sign * r
            return inside(x, y, z_mid)
        assert not probe(lo)
        assert probe(hi)
        for _ in range(iters):
            mid = (lo + hi) / 2
            if probe(mid):
                hi = mid
            else:
                lo = mid
        r = (lo + hi) / 2
        return (seed_x if axis == "x" else seed_y) + sign * r

    measured = []
    for sx, sy in cco.STANDOFF_XY:
        x_lo = edge(sx, sy, "x", -1)
        x_hi = edge(sx, sy, "x", 1)
        y_lo = edge(sx, sy, "y", -1)
        y_hi = edge(sx, sy, "y", 1)
        measured.append(((x_lo + x_hi) / 2, (y_lo + y_hi) / 2))

    # Adjacent-corner distance (side of the square) must equal CAM_HOLE_PITCH.
    (x0, y0) = measured[0]   # (+half, +half)
    (x1, y1) = measured[2]   # (+half, -half) -- same X, adjacent corner
    side = ((x0 - x1) ** 2 + (y0 - y1) ** 2) ** 0.5
    assert side == pytest.approx(cco.CAM_HOLE_PITCH, abs=0.1), (
        f"standoff pitch measured {side:.2f} mm, expected {cco.CAM_HOLE_PITCH} mm"
    )


# ---------------------------------------------------------------------------
# Check 4: ceiling screw holes at the expected corners.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("index", range(4))
def test_ceiling_screw_hole_present_and_sized(built, index):
    c = cco.PLATE / 2 - cco.CEIL_HOLE_INSET
    signs = ((1, 1), (-1, 1), (1, -1), (-1, -1))
    sx, sy = signs[index]
    x, y = sx * c, sy * c

    inside = _inside_fn(built["shell"].val())
    z_mid = cco.PLATE_THK / 2
    assert not inside(x, y, z_mid), (
        f"ceiling screw hole {index} at ({x:.2f},{y:.2f}) not void at z={z_mid:.2f}"
    )
    r = _bisect(inside, x, y, z_mid, "x", hi=cco.CEIL_HOLE_INSET - 0.5)
    assert 2 * r == pytest.approx(cco.CEIL_SCREW, abs=0.1), (
        f"ceiling screw hole {index} measured dia {2*r:.2f} mm, expected {cco.CEIL_SCREW} mm"
    )


# ---------------------------------------------------------------------------
# Check 5: board pocket interior clearance >= 36 mm both axes, measured as
# the actual open void span inside the skirt at the board's mounting height.
# ---------------------------------------------------------------------------

def test_board_pocket_clearance_meets_minimum(built):
    """Measured at the board's own mid-thickness Z. The +Y direction is
    intentionally MORE open than the plain skirt wall here (the side cable
    notch's Z-span covers this height -- see module docstring), so it can
    only add clearance, never remove it; this test bisects the three
    directions that still terminate in the plain skirt wall (+X, -X, -Y) and
    uses each as the representative half-span for its axis."""
    inside = _inside_fn(built["shell"].val())
    z_board = -cco.STANDOFF_H - cco.PCB_T / 2   # mid-board height

    r_pos_x = _bisect(inside, 0.0, 0.0, z_board, "x", hi=cco.PLATE / 2 - 1.0)
    r_neg_x = -_bisect(inside, 0.0, 0.0, z_board, "x", hi=-(cco.PLATE / 2 - 1.0))
    r_neg_y = -_bisect(inside, 0.0, 0.0, z_board, "y", hi=-(cco.PLATE / 2 - 1.0))

    x_span = r_pos_x + r_neg_x
    assert x_span >= cco.BOARD_POCKET_MIN, (
        f"board pocket clear span along x = {x_span:.2f} mm, "
        f"required >= {cco.BOARD_POCKET_MIN} mm"
    )
    y_span = 2 * r_neg_y   # -Y wall is unaffected by the notch; the cavity
                           # is otherwise symmetric, so this is the correct
                           # (and conservative, since +Y only adds room)
                           # representative Y span
    assert y_span >= cco.BOARD_POCKET_MIN, (
        f"board pocket clear span along y = {y_span:.2f} mm, "
        f"required >= {cco.BOARD_POCKET_MIN} mm"
    )


# ---------------------------------------------------------------------------
# Check 6: cable exits -- through-plate slot and the side notch, both open.
# ---------------------------------------------------------------------------

def test_through_plate_cable_slot_open(built):
    inside = _inside_fn(built["shell"].val())
    z_mid = cco.PLATE_THK / 2
    assert not inside(0.0, 0.0, z_mid), "through-plate cable slot not open at center"
    # Slot half-length along X should be void out to just under SLOT_L/2.
    assert not inside(cco.SLOT_L / 2 - 0.5, 0.0, z_mid)
    assert inside(cco.SLOT_L / 2 + 1.0, 0.0, z_mid), "material expected beyond the slot's own length"


def test_side_notch_open_at_free_edge_and_reaches_board_level(built):
    inside = _inside_fn(built["shell"].val())
    y_wall_mid = cco.PLATE / 2 - cco.SKIRT_WALL_T / 2

    # At the free (bottom) rim -- must be open (this is the printability trick).
    assert not inside(0.0, y_wall_mid, cco.NOTCH_BOTTOM_Z + 0.5), (
        "side notch is not open at the skirt's free/bottom rim"
    )
    # At the board's own mounting-face height (the notch's documented top).
    assert not inside(0.0, y_wall_mid, cco.NOTCH_TOP_Z - 0.5), (
        "side notch does not reach the board's mounting-face height"
    )
    # Above the notch (back in solid wall) and well clear of the corner bosses.
    assert inside(0.0, y_wall_mid, -1.0), "wall should be solid just below the plate"

    # Width check: void out to just under NOTCH_W/2, solid beyond it.
    mid_z = (cco.NOTCH_TOP_Z + cco.NOTCH_BOTTOM_Z) / 2
    assert not inside(cco.NOTCH_W / 2 - 0.5, y_wall_mid, mid_z)
    assert inside(cco.NOTCH_W / 2 + 1.0, y_wall_mid, mid_z), (
        "wall material expected just outside the notch's own width"
    )


# ---------------------------------------------------------------------------
# Check 7: corner bosses (bezel screws) -- present, self-tap pilot correct,
# and match the bezel's own clearance-hole positions.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("index", range(4))
def test_corner_boss_pilot_hole(built, index):
    x, y = cco.BOSS_XY[index]
    inside = _inside_fn(built["shell"].val())
    z_mid = -cco.SKIRT_H + cco.BOSS_PILOT_DEPTH / 2   # mid-pilot height

    assert not inside(x, y, z_mid), (
        f"boss {index} at ({x:.2f},{y:.2f}): self-tap pilot not void at z={z_mid:.2f}"
    )
    r_solid = (cco.BOSS_PILOT_DIA / 2 + cco.BOSS_OD / 2) / 2
    assert inside(x + r_solid, y, z_mid), (
        f"boss {index} at ({x:.2f},{y:.2f}): expected boss material at r={r_solid:.2f}"
    )
    # Boss must run the full skirt height for real thread engagement depth --
    # confirm solid material still exists well above the pilot's blind end.
    z_above_pilot = -cco.SKIRT_H + cco.BOSS_PILOT_DEPTH + 2.0
    assert inside(x, y, z_above_pilot), (
        f"boss {index}: expected solid material above the blind pilot's end"
    )


@pytest.mark.parametrize("index", range(4))
def test_bezel_screw_clearance_hole_aligns_with_boss(built, index):
    x, y = cco.BOSS_XY[index]
    inside = _inside_fn(built["bezel"].val())
    z_mid = cco.BEZEL_T / 2
    assert not inside(x, y, z_mid), (
        f"bezel clearance hole {index} at ({x:.2f},{y:.2f}) not void"
    )
    r = _bisect(inside, x, y, z_mid, "x", hi=cco.BOSS_OD / 2 - 0.2)
    assert 2 * r == pytest.approx(cco.BEZEL_SCREW_CLEARANCE, abs=0.1), (
        f"bezel clearance hole {index} measured dia {2*r:.2f} mm, "
        f"expected {cco.BEZEL_SCREW_CLEARANCE} mm"
    )


# ---------------------------------------------------------------------------
# Check 8: mass rollup.
# ---------------------------------------------------------------------------

def test_combined_mass_within_budget(built):
    density = MATERIALS["PETG"]["density_g_cm3"]
    shell_g = built["shell"].val().Volume() / 1000.0 * density
    bezel_g = built["bezel"].val().Volume() / 1000.0 * density
    total_g = shell_g + bezel_g
    assert total_g > 0
    assert total_g <= cco.MASS_BUDGET_G, (
        f"combined mass {total_g:.1f} g exceeds {cco.MASS_BUDGET_G} g budget"
    )


# ---------------------------------------------------------------------------
# Check 9: STEP export + reimport round trip, volume within 0.1%.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("piece", ["shell", "bezel"])
def test_step_round_trip_volume(built, piece, tmp_path):
    solid = built[piece]
    step_path = str(tmp_path / f"{piece}.step")
    cq.exporters.export(solid, step_path)

    reimported = cq.importers.importStep(step_path)
    solids = reimported.solids().vals()
    assert len(solids) == 1, f"{piece}: reimported STEP has {len(solids)} solids, expected 1"

    original_vol = solid.val().Volume()
    reimported_vol = solids[0].Volume()
    rel_err = abs(reimported_vol - original_vol) / original_vol
    assert rel_err < 0.001, (
        f"{piece}: STEP round-trip volume differs by {rel_err*100:.4f}% "
        f"(original {original_vol:.2f} mm^3, reimported {reimported_vol:.2f} mm^3)"
    )
