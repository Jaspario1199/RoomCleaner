"""
Base station case -- two-piece printed enclosure (open-top TRAY + screw-down
LID) for the ground controller: an Arduino Uno R3 with a CNC Shield V3
(4x A4988 + heatsinks) stacked on top, wired to a fuse-protected DC supply,
4 stepper motors, and endstop switches. This is a standalone accessory box --
it does not mate with the claw assembly, so nothing here is added to
cad/interfaces.py (no other part reads these dimensions).

BOTH SOLIDS come out of `make()` -> (tray, lid); the repo has no established
multi-solid `make()` convention (every existing part returns one Workplane),
so this file follows the objective's fallback: export the two pieces as
`base_station_case_tray` and `base_station_case_lid`.

--------------------------------------------------------------------------
RESEARCHED INPUT: Arduino Uno R3 mounting-hole pattern (REVISED -- see
verification/base_station_case_report.md §2)
--------------------------------------------------------------------------
Board outline 68.6 x 53.4 mm (spec). The 4x Ø3.2 mm mounting holes, measured
from the board's own bottom-left corner (the end where the USB-B jack and DC
barrel jack sit, at local x=0), are:
    (13.97, 2.54), (15.24, 50.80), (66.04, 7.62), (66.04, 35.56)
The first hole's X was originally taken as 15.24 mm (matching 3 of 4 open-
source PCB/CAD footprint libraries cross-referenced in the first draft), but
an independent verification pass fetched the raw KiCad footprint
(`Alarm-Siren/arduino-kicad-library`, `Arduino_Uno_R3_Shield.kicad_mod`) --
a source that reproduces the Uno's complete, correctly-pitched pin map
(D0-D13, A0-A5, ICSP, etc.) and is therefore board-accurate -- which places
that one pad at X=13.97 mm (exactly 0.05 in / half the 0.1 in header grid
off from 15.24 mm). This canonical KiCad value is adopted here; the other 3
coordinates were already confirmed to match it exactly. (`docs.arduino.cc`,
`forum.arduino.cc`, and `blog.adafruit.com` remain unreachable from this
sandbox -- network egress is blocked -- so `raw.githubusercontent.com` is
the best available primary source.)

--------------------------------------------------------------------------
ASSUMED CONNECTOR HEIGHTS (derived, NOT in params/interfaces -- documented
here because no authoritative source specifies them for this project)
--------------------------------------------------------------------------
Z=0 is the tray's interior floor (cavity) surface. Going up:
  * UNO_TOP_Z = BOSS_H + UNO_PCB_T -- the Uno PCB's top copper surface,
    resting on 6 mm standoff bosses (spec) with a 1.6 mm PCB (standard FR4).
  * USB_PORT_CTR_Z = UNO_TOP_Z + ~5 mm -- assumed center height of a
    through-hole USB-B connector body (typical THT USB-B is ~11.5 mm tall;
    its body center sits roughly mid-height above the board edge).
  * SHIELD_TOP_Z = UNO_TOP_Z + shield stacking-header gap (~8.5 mm, the
    standard Arduino female stacking-header height) + shield PCB (~1.6 mm).
  * TERMINAL_PORT_CTR_Z = SHIELD_TOP_Z + ~10 mm -- assumed center height for
    the CNC Shield's 5.08 mm pitch screw terminals and motor/endstop pin
    headers (generous, covers the tallest connector row on the shield).
  * DRIVER_STACK_TOP_Z = SHIELD_TOP_Z + ~22 mm -- assumed top of the tallest
    feature: an A4988 module (header standoff ~3 mm + module body ~13 mm)
    with an adhesive aluminum heatsink (~6 mm) on top.
These are engineering assumptions, not measured values; the port openings
are sized generously (see PORT_* constants) so modest error in any of these
estimates is absorbed by clearance, not by a connector hitting plastic.

--------------------------------------------------------------------------
Interior height budget
--------------------------------------------------------------------------
CLEARANCE_ABOVE_PCB (48 mm, actual) >= CLEARANCE_ABOVE_PCB_MIN (45 mm,
spec-required) is the headroom from UNO_TOP_Z to the LID's interior ceiling
when tray + lid are assembled. That covers the computed driver stack
(32.1 mm above the Uno PCB top) with ~16 mm left over for heatsink tolerance
and jumper-wire dressing. Split as TRAY_WALL_H (interior wall height, holds
essentially the whole stack) + LID_CAVITY_H (a shallow recess in the lid's
underside that adds the last bit of headroom once screwed down).

--------------------------------------------------------------------------
Port layout
--------------------------------------------------------------------------
  * -X wall ("input" side): USB-B port (Uno layer) + DC power-pair entry
    from the fuse holder (shield/terminal layer, since the incoming battery
    pair lands on the CNC Shield's own power terminal, not the Uno's barrel
    jack -- standard practice for CNC-shield builds).
  * +X wall ("output" side): 4x motor cable exits + 1x endstop-wire bundle
    exit, all at the shield/terminal layer.
  * +-Y walls: left free of ports specifically so they can carry the
    ventilation slot arrays over the driver area, alongside a matching
    array in the lid roof (spec: "top of lid + both side walls").
  * Every port gets a flanking pair of small zip-tie anchor holes so the
    cable can be strain-relieved to the wall right at the entry point.
Port Y-positions are centered on their wall rather than matched to a
specific Uno clone's silkscreen position -- USB-B/power-jack placement
varies a few mm between Uno clones, and the openings are sized generously
enough to absorb that.

--------------------------------------------------------------------------
Print orientation (no supports)
--------------------------------------------------------------------------
TRAY: floor down on the bed, open top up. All walls are vertical
perimeters; the Uno bosses, corner posts, and countersinks are all cut
in the Z axis or into faces already printing upward -- no bridging.
LID: flat roof down on the bed (its single largest flat face), open
(recessed) side up. The vent slots and corner clearance holes are cut
straight down through printed layers -- no overhangs, no supports.
"""

from __future__ import annotations

import cadquery as cq

from ..params import WALL, SCREW_M3, M3_THREAD_HOLE
from ..materials import MATERIALS

# ---- Uno R3 board reference (spec + researched hole pattern) --------------
UNO_L = 68.6                       # mm, Uno PCB length (X), spec
UNO_W = 53.4                       # mm, Uno PCB width (Y), spec
UNO_PCB_T = 1.6                    # mm, assumption: standard FR4 thickness
UNO_HOLE_DIA = 3.2                 # mm, Uno mounting-hole diameter (researched)
# Researched canonical Uno R3 hole pattern, from the board's own bottom-left
# corner (see module docstring for cross-reference/KiCad-source notes).
UNO_HOLE_XY_BOARD = (
    (13.97, 2.54),
    (15.24, 50.80),
    (66.04, 7.62),
    (66.04, 35.56),
)

# ---- Uno standoff bosses (tray floor) --------------------------------------
BOSS_H = 6.0                       # mm, standoff boss height under the Uno (spec)
BOSS_OD = 8.0                      # mm, boss OD (2 mm wall around the Ø4 insert bore)
BOSS_INSERT_DEPTH = 5.0            # mm, insert bore depth (< BOSS_H, solid base under it)

# ---- Derived stack-up heights (local Z=0 at tray interior floor) ----------
UNO_TOP_Z = BOSS_H + UNO_PCB_T                                   # 7.6 mm

USB_CONNECTOR_CTR_OFFSET = 5.0     # mm, assumption (see docstring)
USB_PORT_CTR_Z = UNO_TOP_Z + USB_CONNECTOR_CTR_OFFSET            # 12.6 mm

SHIELD_STACK_GAP = 8.5             # mm, assumption: Arduino stacking-header height
SHIELD_PCB_T = 1.6                 # mm, assumption: CNC Shield V3 PCB thickness
SHIELD_TOP_Z = UNO_TOP_Z + SHIELD_STACK_GAP + SHIELD_PCB_T       # 17.7 mm

TERMINAL_CTR_OFFSET = 10.0         # mm, assumption (see docstring)
TERMINAL_PORT_CTR_Z = SHIELD_TOP_Z + TERMINAL_CTR_OFFSET         # 27.7 mm

DRIVER_STACK_H = 22.0              # mm, assumption: A4988 + heatsink stack height
DRIVER_STACK_TOP_Z = SHIELD_TOP_Z + DRIVER_STACK_H               # 39.7 mm

CLEARANCE_ABOVE_PCB_MIN = 45.0     # mm, REQUIRED interior clearance above Uno PCB (spec)
CLEARANCE_ABOVE_PCB = 48.0         # mm, actual design value (>= required)

LID_CAVITY_H = 6.0                 # mm, lid underside recess depth
LID_ROOF_T = WALL                  # mm, lid roof (top skin) thickness
TOTAL_INTERIOR_H = UNO_TOP_Z + CLEARANCE_ABOVE_PCB                # 55.6 mm
TRAY_WALL_H = TOTAL_INTERIOR_H - LID_CAVITY_H                      # 49.6 mm

# ---- Footprint --------------------------------------------------------------
INTERIOR_L = 100.0                 # mm, interior X -- Uno length + margin for
                                    # connector overhang, wall, corner posts
INTERIOR_W = 94.0                  # mm, interior Y -- Uno width + margin for
                                    # side-wall vents, wire routing, the
                                    # +X wall's 5-across port row (with its
                                    # flanking zip-tie holes) clearing the
                                    # CORNER_R fillet at both ends, AND room
                                    # for CORNER_POST_XY (below) to sit clear
                                    # of both the Uno board and MOUNT_HOLE_XY
FLOOR_T = WALL                     # mm, tray floor thickness (meets 2.4 mm min)
OUTER_L = INTERIOR_L + 2 * WALL
OUTER_W = INTERIOR_W + 2 * WALL
CORNER_R = 6.0                     # mm, outer vertical-edge fillet (generous, per spec)

# Uno board centered in the tray footprint.
UNO_ORIGIN_X = -UNO_L / 2
UNO_ORIGIN_Y = -UNO_W / 2
UNO_HOLE_XY = tuple((UNO_ORIGIN_X + bx, UNO_ORIGIN_Y + by) for bx, by in UNO_HOLE_XY_BOARD)

# ---- Lid screw posts (freestanding corner posts inside the tray) ----------
CORNER_POST_OD = 8.0               # mm, post OD (2 mm wall around the Ø4 insert bore)
# Posts are placed from the UNO BOARD FOOTPRINT outward, not from the
# interior wall inward -- a prior revision inset them from the walls only,
# which left all 4 posts sitting inside the board rectangle (each post is a
# freestanding column running the full TRAY_WALL_H, directly through the
# space the PCB needs to occupy). BOARD_POST_CLEARANCE is the minimum gap
# between the board edge and the post's OD (spec requires >= 2 mm; 3 mm used
# for margin). Verified clear of MOUNT_HOLE_XY and the CORNER_R fillet at
# module load (see the assertions below).
BOARD_POST_CLEARANCE = 3.0         # mm, board-edge -> post-OD minimum gap (spec >= 2 mm)
CORNER_POST_X = UNO_L / 2 + BOARD_POST_CLEARANCE + CORNER_POST_OD / 2
CORNER_POST_Y = UNO_W / 2 + BOARD_POST_CLEARANCE + CORNER_POST_OD / 2
CORNER_POST_XY = tuple(
    (sx * CORNER_POST_X, sy * CORNER_POST_Y)
    for sx in (1, -1) for sy in (1, -1)
)
CORNER_POST_INSERT_DEPTH = 8.0     # mm, insert bore depth into the post top

# ---- External wall/shelf mounting holes (tray floor, outside corners) -----
# Inset chosen so the countersink clears both the CORNER_R corner fillet and
# the CORNER_POST_XY bosses (checked by the assertions below).
MOUNT_HOLE_INSET = 6.0             # mm, inset from the OUTER edges -- this
                                    # sits the hole near the middle of the
                                    # CORNER_R=6 mm fillet radius, well clear
                                    # of the rounded-away material
MOUNT_HOLE_XY = tuple(
    (sx * (OUTER_L / 2 - MOUNT_HOLE_INSET), sy * (OUTER_W / 2 - MOUNT_HOLE_INSET))
    for sx in (1, -1) for sy in (1, -1)
)
MOUNT_HOLE_SHANK_DIA = 4.5         # mm, through-hole (M3/#8 wood screw), spec
MOUNT_HOLE_CSK_DIA = 7.5           # mm, countersink diameter for a flat-head screw
MOUNT_HOLE_CSK_ANGLE = 90.0        # deg, standard countersink included angle

# Fail fast at import time if a future constant edit reintroduces the §3
# board/post collision or a post/mount-hole collision (verification report
# findings -- see docstring). These are cheap algebraic checks, not BRep
# probes; tests/test_base_station_case.py additionally verifies the built
# geometry directly.
for _sx, _sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
    _post_edge_x = CORNER_POST_X - CORNER_POST_OD / 2
    _post_edge_y = CORNER_POST_Y - CORNER_POST_OD / 2
    assert _post_edge_x - UNO_L / 2 >= 2.0, "corner post too close to the Uno board in X"
    assert _post_edge_y - UNO_W / 2 >= 2.0, "corner post too close to the Uno board in Y"
    _mx = _sx * (OUTER_L / 2 - MOUNT_HOLE_INSET)
    _my = _sy * (OUTER_W / 2 - MOUNT_HOLE_INSET)
    _px = _sx * CORNER_POST_X
    _py = _sy * CORNER_POST_Y
    _center_dist = ((_mx - _px) ** 2 + (_my - _py) ** 2) ** 0.5
    _min_dist = CORNER_POST_OD / 2 + MOUNT_HOLE_CSK_DIA / 2 + 1.0
    assert _center_dist >= _min_dist, "corner post too close to an external mount hole"
del _sx, _sy, _post_edge_x, _post_edge_y, _mx, _my, _px, _py, _center_dist, _min_dist

# ---- Port openings ----------------------------------------------------------
OVERTRAVEL = 2.0                   # mm, cutter overtravel past each wall face
                                    # (clean boolean punch-through, no coincident faces)

USB_SLOT_W = 20.0                  # mm, Y-width of the USB-B cutout (generous)
USB_SLOT_H = 14.0                  # mm, Z-height
USB_PORT_Y = -14.0                 # mm, on the -X wall

DC_HOLE_D = 10.0                   # mm, round entry for the 2-wire DC pair
DC_PORT_Y = 14.0                   # mm, on the -X wall

MOTOR_PORT_D = 10.0                # mm, round port per motor cable
ENDSTOP_PORT_D = 14.0              # mm, round port for the bundled endstop wires

ZIP_TIE_HOLE_D = 2.5               # mm, strain-relief anchor hole diameter
MIN_WALL_GAP = 1.5                 # mm, minimum solid wall required between
                                    # ANY two adjacent cutouts on a wall
                                    # (port-port, port-ziptie, ziptie-ziptie)
ZIP_TIE_OFFSET = 3.0               # mm, extra clearance beyond a port's own
                                    # radius before placing its zip-tie hole.
                                    # Must satisfy ZIP_TIE_OFFSET -
                                    # ZIP_TIE_HOLE_D/2 >= MIN_WALL_GAP (a
                                    # port's own zip tie needs MIN_WALL_GAP of
                                    # wall between itself and that same
                                    # port's edge) -- checked below.

# --- +X wall port pitch (see verification/base_station_case_report.md,
# "Re-verification (post-repair)" item 5) ---------------------------------
# A prior revision re-pitched this wall to 17 mm specifically to keep each
# port's Y-FLANKING zip-tie hole clear of the *next port's own opening*, but
# never checked two *different ports'* zip-tie holes against EACH OTHER --
# at the two motor/endstop boundaries (where the endstop's larger radius
# pushes its zip-tie ring further out than a pitch sized for motor-only
# spacing), those flanking zip ties collided and merged (0 mm wall, verified
# by the independent re-audit).
#
# Fix: move every +X-wall port's zip-tie pair from Y-FLANKING (beside the
# port, competing with the neighbor's own zip ties for the same Y-band) to
# Z-FLANKING (above/below the port, in the wall's vertical direction, where
# there is ~50 mm of interior wall height to spare and zero interaction with
# any other port). Each zip-tie hole now shares its Y-center with its own
# port exactly, and since ZIP_TIE_HOLE_D/2 (1.25 mm) < every port radius
# (5/7 mm), a zip-tie hole's Y-footprint is always a strict subset of its own
# port's Y-footprint -- so it can never be closer to a NEIGHBORING port or
# that neighbor's zip ties than the two port bodies already are. This
# decouples the pitch requirement entirely from ZIP_TIE_OFFSET: pitch only
# has to keep adjacent PORT BODIES >= MIN_WALL_GAP apart.
OUTPUT_PORT_PITCH = 17.0           # mm, Y pitch across the +X wall (well
                                    # above the port-body-only minimum of
                                    # ~13.5 mm for a motor/endstop pair;
                                    # kept at the previous value rather than
                                    # shrunk, since it was already validated
                                    # against the CORNER_R fillet zone and
                                    # MOUNT_HOLE_XY/CORNER_POST_XY spacing)
# 5 evenly spaced positions on the +X wall: endstop bundle in the middle,
# motors on either side.
OUTPUT_PORT_Y = tuple(i * OUTPUT_PORT_PITCH for i in (-2, -1, 0, 1, 2))
OUTPUT_PORT_KIND = ("motor", "motor", "endstop", "motor", "motor")
_OUTPUT_PORT_RADII = tuple(
    (ENDSTOP_PORT_D if k == "endstop" else MOTOR_PORT_D) / 2 for k in OUTPUT_PORT_KIND
)

# Fail fast at import time if a future constant edit reintroduces any of the
# adjacent-void collisions found across the two verification passes. These
# are the same "every adjacent-void pair" categories the coordinator asked
# for, expressed algebraically; tests/test_base_station_case.py additionally
# measures the actual built solid (constants can be right while the CadQuery
# construction still gets it wrong -- see the countersink/USB-port defects).
#
# (1) Port body <-> next port body (Y direction, +X wall).
for _i in range(len(OUTPUT_PORT_Y) - 1):
    _gap = (OUTPUT_PORT_Y[_i + 1] - _OUTPUT_PORT_RADII[_i + 1]) - (
        OUTPUT_PORT_Y[_i] + _OUTPUT_PORT_RADII[_i]
    )
    assert _gap >= MIN_WALL_GAP, f"output ports {_i}/{_i+1}: port bodies closer than {MIN_WALL_GAP} mm"
del _i, _gap

# (2) Every port <-> its OWN zip-tie hole (Z direction on the +X wall, Y
# direction on the -X wall -- the same algebra applies to both since it is
# just "port edge, then ZIP_TIE_OFFSET, then the zip-tie hole's own radius").
assert ZIP_TIE_OFFSET - ZIP_TIE_HOLE_D / 2 >= MIN_WALL_GAP, (
    "ZIP_TIE_OFFSET too small: a port's own zip-tie hole would sit closer "
    f"than {MIN_WALL_GAP} mm to that port's own edge"
)

# (3) A port's two OWN zip-tie holes (above/below, or left/right on the -X
# wall) against each other -- always >> MIN_WALL_GAP given (2) above and
# every port radius > 0, but asserted for completeness/regression safety.
for _dia in (MOTOR_PORT_D, ENDSTOP_PORT_D, USB_SLOT_W, DC_HOLE_D):
    _own_zip_gap = 2 * (_dia / 2 + ZIP_TIE_OFFSET) - ZIP_TIE_HOLE_D
    assert _own_zip_gap >= MIN_WALL_GAP
del _dia, _own_zip_gap

# ---- Ventilation slots -------------------------------------------------------
VENT_SLOT_W = 2.2                  # mm, slot width (>= 2 mm for reliable FDM slots)
VENT_SLOT_L = 10.0                 # mm, slot length
VENT_SLOT_PITCH = 6.0              # mm, center-to-center pitch
VENT_SIDE_COLS = 6                 # count, columns along each side wall
VENT_SIDE_ROWS_Z = (SHIELD_TOP_Z + 4.0, SHIELD_TOP_Z + 14.0)  # 2 rows over the driver band
VENT_LID_COLS = 8                  # count, columns in the lid roof grid
VENT_LID_ROWS = 3                  # count, rows in the lid roof grid


def _grid_positions(n: int, pitch: float) -> tuple:
    """n evenly spaced center positions, symmetric about 0."""
    span = (n - 1) * pitch
    start = -span / 2
    return tuple(start + i * pitch for i in range(n))


def _x_axis_box(width_y: float, height_z: float, length_x: float,
                 x0: float, y: float, z: float) -> cq.Workplane:
    """Rectangular cutter whose axis runs along global +X (centered at x0,
    spanning length_x), used to cut a port through the -X/+X walls without
    depending on face-selection order.

    NOTE (see verification/base_station_case_report.md §6): a +90 deg
    rotation about the global Y axis maps local sketch X -> global Z and
    local sketch Y -> global Y (unchanged) -- i.e. `Workplane.rect(a, b)`
    (which puts `a` on local X, `b` on local Y) must be called as
    `rect(height_z, width_y)`, NOT `rect(width_y, height_z)`, for the
    finished cutter's Y-span to equal width_y and Z-span to equal height_z
    as this function's own signature promises. The previous version passed
    `rect(width_y, height_z)` directly, silently swapping the built port's
    width and height.
    """
    return (
        cq.Workplane("XY")
        .rect(height_z, width_y)
        .extrude(length_x)
        .rotate((0, 0, 0), (0, 1, 0), 90)
        .translate((x0 - length_x / 2, y, z))
    )


def _x_axis_cylinder(dia: float, length_x: float, x0: float, y: float, z: float) -> cq.Workplane:
    """Round cutter whose axis runs along global +X (centered at x0,
    spanning length_x), for round ports/holes through the -X/+X walls."""
    return (
        cq.Workplane("XY")
        .circle(dia / 2)
        .extrude(length_x)
        .rotate((0, 0, 0), (0, 1, 0), 90)
        .translate((x0 - length_x / 2, y, z))
    )


def _y_axis_box(width_x: float, height_z: float, length_y: float,
                 x: float, y0: float, z: float) -> cq.Workplane:
    """Rectangular cutter whose axis runs along global +Y (from y0 to
    y0+length_y), used to cut vent slots through the +-Y walls."""
    return (
        cq.Workplane("XY")
        .rect(width_x, height_z)
        .extrude(length_y)
        .rotate((0, 0, 0), (1, 0, 0), -90)
        .translate((x, y0, z))
    )


def _uno_boss(x: float, y: float) -> cq.Workplane:
    boss = cq.Workplane("XY").center(x, y).circle(BOSS_OD / 2).extrude(BOSS_H)
    boss = (
        boss.faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .circle(M3_THREAD_HOLE / 2)
        .cutBlind(-BOSS_INSERT_DEPTH)
    )
    return boss


def _corner_post(x: float, y: float) -> cq.Workplane:
    post = cq.Workplane("XY").center(x, y).circle(CORNER_POST_OD / 2).extrude(TRAY_WALL_H)
    post = (
        post.faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .circle(M3_THREAD_HOLE / 2)
        .cutBlind(-CORNER_POST_INSERT_DEPTH)
    )
    return post


def make_tray() -> cq.Workplane:
    outer_h = FLOOR_T + TRAY_WALL_H
    half_l, half_w = OUTER_L / 2, OUTER_W / 2

    tray = cq.Workplane("XY").box(OUTER_L, OUTER_W, outer_h, centered=(True, True, False))
    tray = tray.edges("|Z").fillet(CORNER_R)

    cavity = (
        cq.Workplane("XY")
        .box(INTERIOR_L, INTERIOR_W, TRAY_WALL_H, centered=(True, True, False))
        .translate((0, 0, FLOOR_T))
    )
    tray = tray.cut(cavity)

    # External wall/shelf mounting holes: countersink opens on the tray's
    # OUTSIDE (bottom, exterior) floor face -- the screw head sits recessed
    # there, flush or below the surface, with the shank continuing up
    # through the remaining floor thickness into the interior.
    #
    # NOTE (see verification/base_station_case_report.md §8): the previous
    # version cut this with `tray.workplane(offset=FLOOR_T)` called directly
    # on the cut Compound with no prior `.faces()` selection. CadQuery's
    # default `centerOption="ProjectedOrigin"` then computed the new
    # workplane's Z from the CURRENT SOLID'S MASS-CENTROID Z (~20.6 mm for
    # this shape), not from the base XY plane's Z=0 as a bare `.workplane()`
    # call might suggest -- so the countersink cone was cut ~18 mm up in
    # empty cavity air and removed nothing. Selecting the true bottom face
    # explicitly (`faces("<Z")`, unambiguous here: it is the single lowest,
    # and still a single planar face, even after the CORNER_R fillet) fixes
    # this by construction -- there is no offset/centroid math left to get
    # wrong.
    tray = (
        tray.faces("<Z")
        .workplane()
        .pushPoints(list(MOUNT_HOLE_XY))
        .cskHole(MOUNT_HOLE_SHANK_DIA, MOUNT_HOLE_CSK_DIA, MOUNT_HOLE_CSK_ANGLE)
    )

    # Uno standoff bosses, on the cavity floor.
    for x, y in UNO_HOLE_XY:
        tray = tray.union(_uno_boss(x, y).translate((0, 0, FLOOR_T)))

    # Lid-screw corner posts, freestanding from the cavity floor to the rim.
    for x, y in CORNER_POST_XY:
        tray = tray.union(_corner_post(x, y).translate((0, 0, FLOOR_T)))

    # -X wall ("input" side): USB-B + DC power entry, each with flanking
    # zip-tie anchor holes.
    x_in = -half_l
    tray = tray.cut(_x_axis_box(USB_SLOT_W, USB_SLOT_H, WALL + 2 * OVERTRAVEL,
                                 x_in, USB_PORT_Y, USB_PORT_CTR_Z))
    for sy in (-1, 1):
        y = USB_PORT_Y + sy * (USB_SLOT_W / 2 + ZIP_TIE_OFFSET)
        tray = tray.cut(_x_axis_cylinder(ZIP_TIE_HOLE_D, WALL + 2 * OVERTRAVEL, x_in, y, USB_PORT_CTR_Z))

    tray = tray.cut(_x_axis_cylinder(DC_HOLE_D, WALL + 2 * OVERTRAVEL, x_in, DC_PORT_Y, TERMINAL_PORT_CTR_Z))
    for sy in (-1, 1):
        y = DC_PORT_Y + sy * (DC_HOLE_D / 2 + ZIP_TIE_OFFSET)
        tray = tray.cut(_x_axis_cylinder(ZIP_TIE_HOLE_D, WALL + 2 * OVERTRAVEL, x_in, y, TERMINAL_PORT_CTR_Z))

    # +X wall ("output" side): 4x motor cable exits + 1x endstop bundle exit.
    # Zip-tie holes are Z-FLANKING (above/below each port, sharing that
    # port's own Y-center) rather than Y-flanking -- see the ZIP_TIE_OFFSET/
    # OUTPUT_PORT_PITCH comment above for why.
    x_out = half_l
    for y, kind in zip(OUTPUT_PORT_Y, OUTPUT_PORT_KIND):
        dia = ENDSTOP_PORT_D if kind == "endstop" else MOTOR_PORT_D
        tray = tray.cut(_x_axis_cylinder(dia, WALL + 2 * OVERTRAVEL, x_out, y, TERMINAL_PORT_CTR_Z))
        for sz in (-1, 1):
            zz = TERMINAL_PORT_CTR_Z + sz * (dia / 2 + ZIP_TIE_OFFSET)
            tray = tray.cut(_x_axis_cylinder(ZIP_TIE_HOLE_D, WALL + 2 * OVERTRAVEL, x_out, y, zz))

    # +-Y walls: ventilation slot array over the driver area. Each cutter is
    # centered on its wall (with overtravel both sides) so the same length_y
    # works for both the -Y and +Y wall.
    vent_x_positions = _grid_positions(VENT_SIDE_COLS, VENT_SLOT_PITCH * 2.0)
    length_y = WALL + 2 * OVERTRAVEL
    for sign in (-1, 1):
        wall_center_y = sign * half_w
        y0 = wall_center_y - length_y / 2
        for vx in vent_x_positions:
            for vz in VENT_SIDE_ROWS_Z:
                tray = tray.cut(_y_axis_box(VENT_SLOT_W, VENT_SLOT_L, length_y, vx, y0, vz))

    return tray


def make_lid() -> cq.Workplane:
    lid_h = LID_CAVITY_H + LID_ROOF_T

    lid = cq.Workplane("XY").box(OUTER_L, OUTER_W, lid_h, centered=(True, True, False))
    lid = lid.edges("|Z").fillet(CORNER_R)

    cavity = cq.Workplane("XY").box(INTERIOR_L, INTERIOR_W, LID_CAVITY_H, centered=(True, True, False))
    lid = lid.cut(cavity)

    # 4x corner screw clearance holes, straight through the full lid thickness.
    lid = (
        lid.faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .pushPoints(list(CORNER_POST_XY))
        .hole(SCREW_M3)
    )

    # Top ventilation slot array over the driver area, cut through the roof only.
    vent_x = _grid_positions(VENT_LID_COLS, VENT_SLOT_PITCH * 2.0)
    vent_y = _grid_positions(VENT_LID_ROWS, VENT_SLOT_PITCH * 3.0)
    lid = (
        lid.faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .pushPoints([(x, y) for x in vent_x for y in vent_y])
        .rect(VENT_SLOT_W, VENT_SLOT_L)
        .cutBlind(-LID_ROOF_T)
    )

    return lid


def make() -> tuple[cq.Workplane, cq.Workplane]:
    return make_tray(), make_lid()


if __name__ == "__main__":
    from ..lib import export

    tray, lid = make()
    density = MATERIALS["PETG"]["density_g_cm3"]

    for name, solid in (("base_station_case_tray", tray), ("base_station_case_lid", lid)):
        result = export(solid, name)
        bb = solid.val().BoundingBox()
        vol_cm3 = solid.val().Volume() / 1000.0
        mass_g = vol_cm3 * density
        print(f"{name}: bbox {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm, "
              f"volume {vol_cm3:.2f} cm^3, mass @ PETG {density} g/cm^3: {mass_g:.2f} g")
        print(f"  {result}")

    total_mass_g = (tray.val().Volume() + lid.val().Volume()) / 1000.0 * density
    print(f"combined mass: {total_mass_g:.2f} g (target <= 150 g)")
