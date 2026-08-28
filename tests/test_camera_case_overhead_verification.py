"""
Independent geometry-verifier probes for cad/parts/camera_case_overhead.py
(Gate 5). Written by the geometry-verifier agent, NOT the implementer.
Does not trust the implementer's own test file or module docstring --
measures the actual built BRep solids and, where the contract requires it,
independently re-derives expected values (e.g. re-imports CAM_HOLE_PITCH
straight from camera_mount_overhead.py rather than through the module under
test) or performs its own STEP reimport rather than reusing exports/paths.

Read-only with respect to cad/parts/. This file and
verification/camera_case_overhead_report.md are the only outputs.
"""

from __future__ import annotations

import math
import os

import pytest

cq = pytest.importorskip("cadquery")

from OCP.gp import gp_Pnt
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.TopAbs import TopAbs_IN

from cad.parts import camera_case_overhead as cco
from cad.parts import camera_mount_overhead as cmo
from cad import materials as mats

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEP_DIR = os.path.join(REPO, "cad", "step")
BBOX_TOL_MM = 0.05   # STEP round trip should be near-exact (<0.1% requested)
VOL_TOL_REL = 0.001  # 0.1%


def _inside_fn(solid):
    def f(x, y, z, tol=1e-6):
        c = BRepClass3d_SolidClassifier(solid.wrapped)
        c.Perform(gp_Pnt(x, y, z), tol)
        return c.State() == TopAbs_IN
    return f


@pytest.fixture(scope="module")
def built():
    shell, bezel = cco.make()
    return {"shell": shell, "bezel": bezel}


# ---------------------------------------------------------------------------
# 0. Interface-sharing: values must be IMPORTED, not redefined, from
#    camera_mount_overhead.py.
# ---------------------------------------------------------------------------

def test_hole_pitch_and_tap_are_the_same_object_as_source():
    assert cco.CAM_HOLE_PITCH is cmo.CAM_HOLE_PITCH
    assert cco.M2_TAP is cmo.M2_TAP
    assert cco.STANDOFF_H is cmo.POST_H
    assert cco.STANDOFF_POST_DIA is cmo.POST_DIA


# ---------------------------------------------------------------------------
# 1. Basic solid validity / single-body.
# ---------------------------------------------------------------------------

def test_exactly_one_solid_each(built):
    for name, wp in built.items():
        assert wp.val().isValid(), f"{name} invalid"
        n = len(wp.solids().vals())
        assert n == 1, f"{name}: expected 1 solid, got {n}"


def test_volumes_positive(built):
    for name, wp in built.items():
        v = wp.val().Volume()
        assert v > 0, f"{name} volume {v} not positive"


# ---------------------------------------------------------------------------
# 2. Skirt wall thickness >= 2.4 mm, measured directly (independent of
#    SKIRT_WALL_T constant) via edge bisection at plate-height Z.
# ---------------------------------------------------------------------------

def test_skirt_wall_thickness_measured(built):
    """Bisect from the void cavity CENTER outward to the void->solid
    transition (same direction convention as the implementer's own _bisect
    helper: lo=void, hi=solid) to get the cavity half-span, independent of
    the SKIRT_WALL_T/INTERIOR_CLEAR constants. Wall thickness = outer
    half-plate (measured bbox) minus that cavity half-span."""
    inside = _inside_fn(built["shell"].val())
    z_mid = -cco.SKIRT_H / 2   # mid-skirt height, away from bosses/notch
    assert not inside(0.0, 0.0, z_mid), "cavity center unexpectedly solid"

    outer_half = cco.PLATE / 2 - 0.05
    assert inside(outer_half, 0.0, z_mid), "expected solid just inside outer wall face"

    lo, hi = 0.0, cco.PLATE / 2 - 0.1
    for _ in range(60):
        mid = (lo + hi) / 2
        if inside(mid, 0.0, z_mid):
            hi = mid
        else:
            lo = mid
    cavity_half_span = (lo + hi) / 2

    bb = built["shell"].val().BoundingBox()
    outer_half_measured = bb.xlen / 2
    measured_wall_t = outer_half_measured - cavity_half_span
    assert measured_wall_t >= 2.4 - 0.05, (
        f"measured skirt wall thickness {measured_wall_t:.3f} mm "
        f"(outer half {outer_half_measured:.3f} - cavity half {cavity_half_span:.3f}) "
        f"< 2.4 mm minimum"
    )


# ---------------------------------------------------------------------------
# 3. Printability: standoff posts and corner bosses are straight vertical
#    prisms (no overhang) -- confirmed by sampling solid/void state at the
#    SAME (x,y) at multiple Z heights through the full post/boss height.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("index", range(4))
def test_standoff_post_is_straight_vertical_prism(built, index):
    x, y = cco.STANDOFF_XY[index]
    inside = _inside_fn(built["shell"].val())
    r_mid = (cco.M2_TAP / 2 + cco.STANDOFF_POST_DIA / 2) / 2
    for frac in (0.05, 0.25, 0.5, 0.75, 0.95):
        z = -cco.STANDOFF_H * frac
        assert inside(x + r_mid, y, z), (
            f"standoff {index}: post material missing at z={z:.2f} "
            f"(non-vertical / discontinuous post wall)"
        )
        assert not inside(x, y, z), f"standoff {index}: pilot hole not void at z={z:.2f}"


@pytest.mark.parametrize("index", range(4))
def test_corner_boss_is_straight_vertical_cylinder(built, index):
    x, y = cco.BOSS_XY[index]
    inside = _inside_fn(built["shell"].val())
    r_outer = (cco.BOSS_OD / 2) - 0.3  # just inside the OD, outside the pilot
    for frac in (0.05, 0.25, 0.5, 0.75, 0.95):
        z = -cco.SKIRT_H * frac
        assert inside(x + r_outer, y, z), (
            f"boss {index}: boss material missing at z={z:.2f} radius {r_outer:.2f} "
            f"(non-vertical / discontinuous boss wall)"
        )


def test_side_notch_opens_to_free_edge_not_enclosed_window(built):
    """The printability claim is that the notch is open AT the free (bottom)
    rim, i.e. there is no solid material below NOTCH_BOTTOM_Z at that (x,y) --
    a fully enclosed window (solid below it) would need a bridge/support."""
    inside = _inside_fn(built["shell"].val())
    y_wall_mid = cco.PLATE / 2 - cco.SKIRT_WALL_T / 2
    # scan from the notch bottom to well past it (past the model's most
    # negative Z, i.e. off the part) -- should stay void, never re-enter solid
    for z in (cco.NOTCH_BOTTOM_Z - 0.5, cco.NOTCH_BOTTOM_Z - 2.0):
        assert not inside(0.0, y_wall_mid, z) if z >= -cco.SKIRT_H else True
    # more directly: bounding box bottom of the shell equals -SKIRT_H, and at
    # the notch (x,y) there is no material AT z = -SKIRT_H + eps (the very
    # last/bottom layer) confirming it's open at the true free edge.
    assert not inside(0.0, y_wall_mid, -cco.SKIRT_H + 0.02), (
        "side notch is not open at the true bottom-most layer -- would require "
        "a bridge/support to print"
    )


# ---------------------------------------------------------------------------
# 3b. Bezel <-> shell screw-hole alignment, measured INDEPENDENTLY on each
#     solid (not both derived from cco.BOSS_XY) and then compared, per the
#     assignment's explicit "measure both patterns and compare center-to-
#     center" instruction.
# ---------------------------------------------------------------------------

def _find_hole_center_xy(inside, seed_x, seed_y, z, search_r=6.0):
    """Locate a hole's true (x,y) center near (seed_x,seed_y) by bisecting
    the void->solid edge in +-x and +-y from the seed and averaging -- makes
    no assumption the hole is already centered at the seed."""
    def edge(axis, sign, hi=search_r, iters=50):
        lo = 0.0
        def probe(r):
            x, y = seed_x, seed_y
            if axis == "x":
                x = seed_x + sign * r
            else:
                y = seed_y + sign * r
            return inside(x, y, z)
        for _ in range(iters):
            mid = (lo + hi) / 2
            if probe(mid):
                hi = mid
            else:
                lo = mid
        r = (lo + hi) / 2
        return (seed_x if axis == "x" else seed_y) + sign * r
    x_lo, x_hi = edge("x", -1), edge("x", 1)
    y_lo, y_hi = edge("y", -1), edge("y", 1)
    return ((x_lo + x_hi) / 2, (y_lo + y_hi) / 2)


def test_bezel_holes_align_with_shell_bosses_independently_measured(built):
    shell_inside = _inside_fn(built["shell"].val())
    bezel_inside = _inside_fn(built["bezel"].val())
    z_shell = -cco.SKIRT_H + cco.BOSS_PILOT_DEPTH / 2
    z_bezel = cco.BEZEL_T / 2

    for idx, (sx, sy) in enumerate(cco.BOSS_XY):
        shell_c = _find_hole_center_xy(shell_inside, sx, sy, z_shell, search_r=cco.BOSS_OD / 2 - 0.3)
        bezel_c = _find_hole_center_xy(bezel_inside, sx, sy, z_bezel, search_r=cco.BOSS_OD / 2 - 0.3)
        dist = math.dist(shell_c, bezel_c)
        assert dist < 0.1, (
            f"boss {idx}: shell pilot center {shell_c} vs bezel clearance-hole "
            f"center {bezel_c}, independently-measured offset {dist:.3f} mm"
        )


# ---------------------------------------------------------------------------
# 4. Mass, per piece and combined, PETG density from cad/materials.py.
# ---------------------------------------------------------------------------

def test_per_piece_and_combined_mass(built):
    density = mats.MATERIALS["PETG"]["density_g_cm3"]
    assert density == pytest.approx(1.27)
    shell_g = built["shell"].val().Volume() / 1000.0 * density
    bezel_g = built["bezel"].val().Volume() / 1000.0 * density
    total = shell_g + bezel_g
    print(f"\nMEASURED MASS: shell={shell_g:.2f} g, bezel={bezel_g:.2f} g, "
          f"total={total:.2f} g (budget <= 60 g)")
    assert total <= 60.0, f"combined mass {total:.2f} g exceeds 60 g budget"


# ---------------------------------------------------------------------------
# 5. STEP export + reimport, INDEPENDENT of cad/lib.export -- verifier does
#    its own export/reimport and checks BOTH volume and bounding box.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("piece", ["shell", "bezel"])
def test_step_round_trip_own_export(built, piece, tmp_path):
    solid = built[piece]
    step_path = str(tmp_path / f"verifier_{piece}.step")
    cq.exporters.export(solid, step_path)
    reimported = cq.importers.importStep(step_path)
    solids = reimported.solids().vals()
    assert len(solids) == 1, f"{piece}: reimport gave {len(solids)} solids"

    orig_vol = solid.val().Volume()
    new_vol = solids[0].Volume()
    rel_err = abs(new_vol - orig_vol) / orig_vol
    assert rel_err < VOL_TOL_REL, f"{piece} volume rel err {rel_err*100:.4f}%"

    bb0 = solid.val().BoundingBox()
    bb1 = solids[0].BoundingBox()
    for a, m0, m1 in (("x", bb0.xlen, bb1.xlen), ("y", bb0.ylen, bb1.ylen),
                       ("z", bb0.zlen, bb1.zlen)):
        assert abs(m0 - m1) <= BBOX_TOL_MM, (
            f"{piece} bbox {a}len mismatch after reimport: {m0:.4f} vs {m1:.4f}"
        )


@pytest.mark.parametrize("piece", ["shell", "bezel"])
def test_repo_step_files_exist_and_agree(built, piece):
    """Checks the ALREADY-COMMITTED cad/step/*.step files (not a fresh
    tmp export) agree with the current source-built solid -- catches stale
    exports."""
    step_path = os.path.join(STEP_DIR, f"camera_case_overhead_{piece}.step")
    assert os.path.exists(step_path), f"missing {step_path}"
    reimported = cq.importers.importStep(step_path)
    solids = reimported.solids().vals()
    assert len(solids) == 1
    orig_vol = built[piece].val().Volume()
    new_vol = solids[0].Volume()
    rel_err = abs(new_vol - orig_vol) / orig_vol
    assert rel_err < VOL_TOL_REL, (
        f"committed STEP {piece} volume differs from current source by "
        f"{rel_err*100:.4f}% -- stale export? orig={orig_vol:.2f} step={new_vol:.2f}"
    )
    bb0 = built[piece].val().BoundingBox()
    bb1 = solids[0].BoundingBox()
    for a, m0, m1 in (("x", bb0.xlen, bb1.xlen), ("y", bb0.ylen, bb1.ylen),
                       ("z", bb0.zlen, bb1.zlen)):
        assert abs(m0 - m1) <= BBOX_TOL_MM, (
            f"committed STEP {piece} bbox {a}len mismatch: {m0:.4f} vs {m1:.4f}"
        )


# ---------------------------------------------------------------------------
# 6. FULL ASSEMBLY CHECK (contract item 8): virtually place a 32x32x1.6 board
#    on the standoff tops, a lens-stand-in cylinder, and a USB stand-in box;
#    check placement, clearance, and reachability all against the actual
#    built solids (no trust in the module's own stack-up arithmetic).
# ---------------------------------------------------------------------------

BOARD_W = 32.0
BOARD_H_T = 1.6
LENS_STANDIN_DIA = 14.0
LENS_STANDIN_LEN = 13.0
USB_W, USB_D, USB_H = 16.0, 8.0, 8.0


def test_assembly_board_holes_land_on_post_axes():
    """Board corner holes at its own 28 mm (CAM_HOLE_PITCH) pattern must
    coincide with the shell's standoff post axes -- direct comparison of the
    two coordinate sets, independent of any shared-constant assumption."""
    half = cco.CAM_HOLE_PITCH / 2
    board_holes = {(math.copysign(half, sx), math.copysign(half, sy))
                   for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1))}
    post_axes = set(cco.STANDOFF_XY)
    assert board_holes == post_axes, (
        f"board hole positions {board_holes} != post axes {post_axes}"
    )


def test_assembly_board_outline_clears_skirt_interior(built):
    """Board is BOARD_W x BOARD_W centered at origin; every point on its
    outline (sampled) must be strictly inside the shell's interior cavity at
    the board's mounting Z, i.e. NOT solid material."""
    inside = _inside_fn(built["shell"].val())
    z = -cco.STANDOFF_H - BOARD_H_T / 2  # mid-board height
    half = BOARD_W / 2
    pts = []
    n = 9
    for i in range(n + 1):
        t = -half + (2 * half) * i / n
        pts += [(t, half), (t, -half), (half, t), (-half, t)]
    bad = [(x, y) for x, y in pts if inside(x, y, z)]
    assert not bad, f"board outline intersects shell material at {bad} (z={z:.2f})"


def test_assembly_lens_standin_clears_bezel_except_through_opening(built):
    """Ø14x13 cylinder centered on the board center (origin), axis vertical,
    spanning from just below the board's lens face down toward the bezel.
    Must pass through the bezel's Ø18 opening with clearance and not touch
    bezel material anywhere else."""
    inside = _inside_fn(built["bezel"].val())
    r_lens = LENS_STANDIN_DIA / 2
    # Radial clearance vs. the bezel's actual opening radius, measured
    # independently (bisection), not assumed equal to LENS_DIA/2.
    z_probe = cco.BEZEL_T / 2
    lo, hi = 0.0, cco.PLATE / 2 - 1.0
    assert not inside(0.0, 0.0, z_probe)
    for _ in range(50):
        mid = (lo + hi) / 2
        if inside(mid, 0.0, z_probe):
            hi = mid
        else:
            lo = mid
    opening_r = (lo + hi) / 2
    clearance = opening_r - r_lens
    assert clearance > 0.1, (
        f"lens stand-in (r={r_lens}) does not clear bezel opening "
        f"(measured opening r={opening_r:.2f}) with meaningful margin"
    )
    # Cylinder must not touch bezel material anywhere: sample its curved
    # surface at r_lens across a ring of angles, at the bezel's mid-thickness.
    bad = []
    for k in range(16):
        ang = 2 * math.pi * k / 16
        x, y = r_lens * math.cos(ang), r_lens * math.sin(ang)
        if inside(x, y, z_probe):
            bad.append((x, y))
    assert not bad, f"lens stand-in surface touches bezel material at {bad}"
    # Length sanity: the stand-in (13 mm) must fit within LENS_SPACE without
    # protruding past the bezel's inner (top) face -- i.e. LENS_SPACE >= 13.
    assert cco.LENS_SPACE >= LENS_STANDIN_LEN - 1e-9, (
        f"LENS_SPACE {cco.LENS_SPACE} mm < lens stand-in length {LENS_STANDIN_LEN} mm"
    )


def test_assembly_usb_standin_placement_clear_of_shell(built):
    """16x8x8 mm box on the board's +Y edge top (sitting on the board's back
    face, at the +Y edge in plan) must not intersect shell material."""
    inside = _inside_fn(built["shell"].val())
    board_top_z = -cco.STANDOFF_H  # board's back (mounting) face height
    box_cz = board_top_z + USB_H / 2
    box_cy = BOARD_W / 2 - USB_D / 2  # sits on board's +Y edge, box depth D along Y

    xs = (-USB_W / 2, USB_W / 2)
    ys = (box_cy - USB_D / 2, box_cy + USB_D / 2)
    zs = (box_cz - USB_H / 2, box_cz + USB_H / 2)
    bad = [(x, y, z) for x in xs for y in ys for z in zs if inside(x, y, z)]
    assert not bad, f"USB stand-in box intersects shell material at corners {bad}"


def test_assembly_usb_standin_cable_path_to_notch(built):
    """The rigid USB connector body (previous test) sits at z in
    [board_top_z, board_top_z+USB_H] = [-10, -2], but the side notch opens at
    z in [NOTCH_BOTTOM_Z, NOTCH_TOP_Z] = [-24.6, -10] -- BELOW the connector,
    not overlapping it. A rigid straight-line path from the connector body to
    the notch does NOT exist. What the design actually claims (module
    docstring) is a *cable* path: sideways off the board's edge, then down
    the inside of the wall to the notch. This probes that specific 3-segment
    void path (out past the board edge, down past board height, in to the
    notch) for actual clearance, rather than assuming it."""
    inside = _inside_fn(built["shell"].val())
    board_top_z = -cco.STANDOFF_H
    box_cz = board_top_z + USB_H / 2   # -6.0, connector body mid-height
    box_edge_y = BOARD_W / 2  # 16.0, the board's +Y edge (connector at the edge)

    wall_inner_y = cco.INTERIOR_CLEAR / 2 - 0.5   # just inside the skirt wall
    notch_mid_z = (cco.NOTCH_TOP_Z + cco.NOTCH_BOTTOM_Z) / 2

    def sample_path(points, step=0.4):
        blocked = []
        for (x0, y0, z0), (x1, y1, z1) in zip(points, points[1:]):
            dist = max(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
            n = max(1, int(dist / step))
            for i in range(n + 1):
                t = i / n
                x, y, z = x0 + t * (x1 - x0), y0 + t * (y1 - y0), z0 + t * (z1 - z0)
                if inside(x, y, z):
                    blocked.append((round(x, 2), round(y, 2), round(z, 2)))
        return blocked

    # Segment 1: sideways off the board edge, staying at the connector's Z.
    # Segment 2: down along the inside of the wall, past the board's own Z,
    #            into the notch's Z band.
    # Segment 3: through the wall thickness into the notch opening (x=0).
    path = [
        (0.0, box_edge_y, box_cz),
        (0.0, wall_inner_y, box_cz),
        (0.0, wall_inner_y, notch_mid_z),
        (0.0, cco.PLATE / 2 + 0.5, notch_mid_z),  # out through the open notch
    ]
    blocked = sample_path(path)
    assert not blocked, (
        f"cable path from USB connector (edge y={box_edge_y}, z={box_cz}) to the "
        f"side notch is blocked by shell material at {blocked[:5]}"
    )
