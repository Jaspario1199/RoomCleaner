"""
Independent geometry verification for the six claw parts (Gate 5,
geometry-verifier role). These tests build each part directly from its
`make()` function and measure the result -- they do not trust part
docstrings or comments.

Skips entirely if cadquery is not installed (CI without the CAD extra).

Covers REQUIREMENTS.md A1 (independent geometry verification, STEP
round-trip) and the interface-agreement checks called out in
cad/interfaces.py (D3/D5/D6/D7, C1/C2). Mass rollup (A3) is checked in
test_mass_rollup().
"""

from __future__ import annotations

import math
import os

import pytest

cq = pytest.importorskip("cadquery")

from cad.parts import (          # noqa: E402
    standoff,
    tendon_drum,
    electronics_cover,
    tentacle_hub,
    tentacle_finger,
    effector_frame,
)
from cad.interfaces import (     # noqa: E402
    HUB_MOUNT_R,
    STANDOFF_ANGLES_DEG,
    DRUM_CORE_R,
    DRUM_TIEOFF_HOLES,
    DRUM_FLANGE_T,
    DRUM_CORE_H,
    HORN_POCKET_DIA,
    HORN_POCKET_T,
    COVER_SCREW_POS,
    FINGER_SHOULDER_T,
    FINGER_SHOULDER_GROW,
    SERVO_THROW_DEG,
)
from cad.parts.tentacle_hub import (   # noqa: E402
    POCKET_W,
    POCKET_H,
    HUB_THK,
    HUB_DIA,
    RIM_INSET,
    N_FINGERS,
)
from cad.parts.tentacle_finger import W_BASE, H_BASE   # noqa: E402
from cad.interfaces import FINGER_SHOULDER_Z0          # noqa: E402
from cad.materials import MATERIALS, PURCHASED_MASS_G  # noqa: E402


BBOX_TOL = 0.3   # mm, per assignment

# ---------------------------------------------------------------------------
# Check 1: each part runs, is valid, is a single solid, and matches its
# expected overall bounding box.
# ---------------------------------------------------------------------------

PART_SPECS = {
    "standoff": (standoff.make, (10.0, 10.0, 40.0)),
    "tendon_drum": (tendon_drum.make, (33.0, 33.0, 12.4)),
    "electronics_cover": (electronics_cover.make, (98.8, 98.8, 44.4)),
    "tentacle_hub": (tentacle_hub.make, (88.0, 88.0, 12.0)),
    "tentacle_finger": (tentacle_finger.make, (20.0, 17.0, 70.0)),
    "effector_frame": (effector_frame.make, (92.0, 92.0, 8.0)),
}


def _build(name):
    make_fn, expected = PART_SPECS[name]
    return make_fn(), expected


@pytest.fixture(scope="module")
def built_parts():
    """Build each part exactly once and share across tests in this module."""
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
# Helpers for the pin-probe interface checks.
# ---------------------------------------------------------------------------

def _pin_removed_volume(wp, x, y, z_center, length, diameter=2.0):
    """Volume removed by cutting a pin of `diameter` centered at (x, y,
    z_center) with the given axial `length` out of `wp`. ~0 means a void
    (hole/slot) was already present there; > 0 means solid material was
    there."""
    v0 = wp.val().Volume()
    pin = (
        cq.Workplane("XY")
        .workplane(offset=z_center - length / 2)
        .circle(diameter / 2)
        .extrude(length)
        .translate((x, y, 0))
    )
    v1 = wp.cut(pin).val().Volume()
    return v0 - v1


# ---------------------------------------------------------------------------
# Check 2a: frame and hub standoff-hole circles are IDENTICAL.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("angle_deg", STANDOFF_ANGLES_DEG)
def test_standoff_holes_agree_hub_and_frame(angle_deg):
    hub = tentacle_hub.make()
    frame = effector_frame.make()
    x = HUB_MOUNT_R * math.cos(math.radians(angle_deg))
    y = HUB_MOUNT_R * math.sin(math.radians(angle_deg))

    removed_hub = _pin_removed_volume(hub, x, y, HUB_THK / 2, HUB_THK + 4)
    removed_frame = _pin_removed_volume(frame, x, y, 4, 16)

    assert removed_hub < 1e-2, (
        f"hub: expected hole at angle {angle_deg} deg ({x:.2f},{y:.2f}), "
        f"pin removed {removed_hub:.4f} mm^3 of solid material"
    )
    assert removed_frame < 1e-2, (
        f"frame: expected hole at angle {angle_deg} deg ({x:.2f},{y:.2f}), "
        f"pin removed {removed_frame:.4f} mm^3 of solid material"
    )


def test_standoff_hole_control_point_is_solid():
    """A 6 mm radial offset from a real hole must land in solid material on
    both parts -- proves the probe is discriminating, not just missing."""
    hub = tentacle_hub.make()
    frame = effector_frame.make()
    angle_deg = STANDOFF_ANGLES_DEG[0]
    r = HUB_MOUNT_R + 6.0
    x = r * math.cos(math.radians(angle_deg))
    y = r * math.sin(math.radians(angle_deg))

    removed_hub = _pin_removed_volume(hub, x, y, HUB_THK / 2, HUB_THK + 4)
    removed_frame = _pin_removed_volume(frame, x, y, 4, 16)

    assert removed_hub > 1.0, "hub: control point unexpectedly hollow"
    assert removed_frame > 1.0, "frame: control point unexpectedly hollow"


# ---------------------------------------------------------------------------
# Check 2b: hub finger slots are THROUGH (no floor).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("finger_index", range(N_FINGERS))
def test_hub_finger_slot_is_through(finger_index):
    hub = tentacle_hub.make()
    pocket_r = HUB_DIA / 2 - RIM_INSET - POCKET_H / 2
    ang = 2 * math.pi * finger_index / N_FINGERS
    cx, cy = pocket_r * math.cos(ang), pocket_r * math.sin(ang)
    deg = math.degrees(ang)

    # Pocket-sized pin box, deliberately smaller than the slot (80%) so a
    # snug real slot still clears it, run the full hub height plus margin
    # on both ends to prove it is open top-to-bottom.
    probe = (
        cq.Workplane("XY")
        .box(POCKET_H * 0.8, POCKET_W * 0.8, HUB_THK + 10, centered=(True, True, False))
        .translate((0, 0, -5))
        .rotate((0, 0, 0), (0, 0, 1), deg)
        .translate((cx, cy, 0))
    )
    inter = hub.intersect(probe)
    solids = inter.solids().vals()
    vol = solids[0].Volume() if solids else 0.0
    assert vol < 1e-2, (
        f"hub finger slot {finger_index} at ({cx:.2f},{cy:.2f}) is not clear "
        f"through: probe intersected {vol:.4f} mm^3 of material"
    )


# ---------------------------------------------------------------------------
# Check 2c: finger shoulder dimensions and above-shoulder fit.
# ---------------------------------------------------------------------------

def test_finger_shoulder_footprint_and_height():
    finger = tentacle_finger.make()
    # Corrected D5 contract: the shoulder sits at z in
    # [FINGER_SHOULDER_Z0, FINGER_SHOULDER_Z0 + FINGER_SHOULDER_T] -- just BELOW
    # the hub slot engagement -- not at the mounting end (z=0), where its
    # oversize would have blocked insertion entirely.
    probe = (cq.Workplane("XY")
             .box(1000, 1000, FINGER_SHOULDER_T, centered=(True, True, False))
             .translate((0, 0, FINGER_SHOULDER_Z0)))
    shoulder_slice = finger.intersect(probe)
    bb = shoulder_slice.val().BoundingBox()

    expected_x = W_BASE + 2 * FINGER_SHOULDER_GROW
    expected_y = H_BASE + 2 * FINGER_SHOULDER_GROW
    assert abs(bb.xlen - expected_x) <= BBOX_TOL, (
        f"shoulder X = {bb.xlen:.3f}, expected {expected_x}"
    )
    assert abs(bb.ylen - expected_y) <= BBOX_TOL, (
        f"shoulder Y = {bb.ylen:.3f}, expected {expected_y}"
    )
    # Shoulder pad occupies z in [Z0, Z0 + T]; and the slot engagement zone
    # below it (z in [0, Z0]) must fit through the hub slot (checked next test).
    assert bb.zmin >= FINGER_SHOULDER_Z0 - 1e-6
    assert bb.zmax <= FINGER_SHOULDER_Z0 + FINGER_SHOULDER_T + 1e-6


def test_finger_body_above_shoulder_fits_hub_slot_with_clearance():
    finger = tentacle_finger.make()
    probe = (
        cq.Workplane("XY")
        .workplane(offset=FINGER_SHOULDER_T)
        .box(1000, 1000, HUB_THK - FINGER_SHOULDER_T, centered=(True, True, False))
    )
    body = finger.intersect(probe)
    bb = body.val().BoundingBox()

    # Finger local X is tangential (matches hub POCKET_W); finger local Y is
    # radial (matches hub POCKET_H) once the finger is rotated into a slot.
    clearance_x = POCKET_W - bb.xlen
    clearance_y = POCKET_H - bb.ylen
    assert clearance_x > 0, f"finger body wider than pocket: {bb.xlen:.3f} vs {POCKET_W}"
    assert clearance_y > 0, f"finger body taller than pocket: {bb.ylen:.3f} vs {POCKET_H}"


# ---------------------------------------------------------------------------
# Check 2d: drum winding capacity, tie-off holes, horn pocket.
# ---------------------------------------------------------------------------

def test_drum_winding_capacity_meets_27mm():
    capacity = DRUM_CORE_R * math.radians(SERVO_THROW_DEG)
    assert capacity >= 27.0, (
        f"drum winding capacity {capacity:.3f} mm < 27 mm "
        f"(DRUM_CORE_R={DRUM_CORE_R}, SERVO_THROW_DEG={SERVO_THROW_DEG})"
    )


@pytest.mark.parametrize("hole_index", range(DRUM_TIEOFF_HOLES))
def test_drum_tieoff_hole_through_bottom_flange(hole_index):
    drum = tendon_drum.make()
    ang = 2 * math.pi * hole_index / DRUM_TIEOFF_HOLES
    x, y = DRUM_CORE_R * math.cos(ang), DRUM_CORE_R * math.sin(ang)
    removed = _pin_removed_volume(drum, x, y, DRUM_FLANGE_T / 2, DRUM_FLANGE_T + 1, diameter=1.0)
    assert removed < 1e-1, (
        f"drum tie-off hole {hole_index} at ({x:.2f},{y:.2f}) not clear through "
        f"bottom flange: pin removed {removed:.4f} mm^3"
    )


def test_drum_horn_pocket_in_top_face():
    drum = tendon_drum.make()
    top_z = 2 * DRUM_FLANGE_T + DRUM_CORE_H
    probe = (
        cq.Workplane("XY")
        .workplane(offset=top_z - HORN_POCKET_T + 0.2)
        .circle(HORN_POCKET_DIA / 2 * 0.9)
        .extrude(HORN_POCKET_T - 0.3)
    )
    inter = drum.intersect(probe)
    solids = inter.solids().vals()
    vol = solids[0].Volume() if solids else 0.0
    assert vol < 1e-2, (
        f"drum horn pocket not clear in top face: probe intersected {vol:.4f} mm^3"
    )


# ---------------------------------------------------------------------------
# Check 2e: cover tab holes align with frame cover-insert holes.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "point", [(COVER_SCREW_POS, 0), (-COVER_SCREW_POS, 0), (0, COVER_SCREW_POS), (0, -COVER_SCREW_POS)]
)
def test_cover_and_frame_screw_holes_align(point):
    cover = electronics_cover.make()
    frame = effector_frame.make()
    x, y = point

    removed_cover = _pin_removed_volume(cover, x, y, 0, 10)
    removed_frame = _pin_removed_volume(frame, x, y, 0, 10)

    assert removed_cover < 1e-2, (
        f"cover: expected tab hole at ({x},{y}), pin removed {removed_cover:.4f} mm^3"
    )
    assert removed_frame < 1e-2, (
        f"frame: expected cover-insert hole at ({x},{y}), pin removed {removed_frame:.4f} mm^3"
    )


# ---------------------------------------------------------------------------
# Check 3: STEP round trip -- export, reimport, compare bbox and volume.
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


# ---------------------------------------------------------------------------
# Check 4: mass rollup (A3) -- printed volumes x densities + purchased mass.
# ---------------------------------------------------------------------------

MASS_BUDGET_G = 450.0

# Quantity per claw, and the material each part is printed in.
PART_QTY = {
    "standoff": 4,
    "tendon_drum": 1,
    "electronics_cover": 1,
    "tentacle_hub": 1,
    "tentacle_finger": 5,
    "effector_frame": 1,
}
PART_MATERIAL = {
    "standoff": "PETG",
    "tendon_drum": "PETG",
    "electronics_cover": "PETG",
    "tentacle_hub": "PETG",
    "tentacle_finger": "TPU95A",
    "effector_frame": "PETG",
}


def test_mass_rollup_within_budget(built_parts):
    total_g = 0.0
    breakdown = {}
    for name, qty in PART_QTY.items():
        wp, _ = built_parts[name]
        vol_cm3 = wp.val().Volume() / 1000.0
        density = MATERIALS[PART_MATERIAL[name]]["density_g_cm3"]
        mass_g = vol_cm3 * density * qty
        breakdown[name] = mass_g
        total_g += mass_g

    purchased_g = sum(PURCHASED_MASS_G.values())
    total_g += purchased_g

    assert total_g <= MASS_BUDGET_G, (
        f"claw mass rollup {total_g:.1f} g exceeds {MASS_BUDGET_G} g budget "
        f"(printed breakdown: {breakdown}, purchased: {purchased_g} g)"
    )
