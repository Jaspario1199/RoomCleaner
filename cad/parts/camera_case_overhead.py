"""
Overhead camera CASE -- a fully enclosed two-piece printed housing for the
bare innomaker 32x32 mm USB board camera on the ceiling, lens pointing
straight down at the floor. Replaces the OPEN BRACKET concept in
cad/parts/camera_mount_overhead.py (left unchanged) with a closed shell +
bezel that protects the bare board from dust, stray fingers, and light leaks
around the lens.

Camera-interface values (hole pitch, self-tap size, ceiling-screw size) are
NOT redefined here -- they are imported directly from camera_mount_overhead.py
so both parts stay tied to one authoritative definition (repo rule: "one
authoritative definition, do not duplicate a master dimension"). The 10 mm
standoff-to-board gap and 6 mm posts are reused the same way, because it is
the SAME physical camera board and the same USB-connector-clearance reasoning
that sized them there.

--------------------------------------------------------------------------
TWO PIECES
--------------------------------------------------------------------------
  * SHELL: the ceiling plate + an integrated perimeter skirt wall descending
    away from the ceiling + 4 internal M2 standoff posts (unchanged pattern
    from camera_mount_overhead.py) that hold the board ~10 mm below the
    plate, plus 4 corner bosses (integral with the skirt, not just the thin
    wall) that the bezel screws into.
  * BEZEL: a flat bottom cover that closes the skirt, with a centered lens
    opening, screwed up into the shell's corner bosses.

Both are returned by `make() -> (shell, bezel)`, following the only existing
two-solid `make()` precedent in this repo (cad/parts/base_station_case.py):
export names `camera_case_overhead_shell` / `camera_case_overhead_bezel`.

--------------------------------------------------------------------------
Coordinate frame (shell)
--------------------------------------------------------------------------
Z=0 is the ceiling plate's BOTTOM (interior) face -- the same "plate bottom
is the local datum" convention camera_mount_overhead.py already uses. +Z is
UP into the ceiling plate (plate top, the mounting face, is at Z=+PLATE_THK).
Everything that hangs into the room (skirt wall, standoff posts, corner
bosses) descends in -Z from Z=0.

--------------------------------------------------------------------------
Interior stack-up (this is the "plate -> standoff -> PCB -> lens space ->
bezel" chain the assignment asks to compute and assert)
--------------------------------------------------------------------------
  Z = 0                        plate bottom (interior face)
  Z = -STANDOFF_H               board's mounting (back) face -- bolts to the
                                 4 standoff posts here, same as
                                 camera_mount_overhead.py's POST_H gap. The
                                 board's BACK (the non-lens side) faces UP
                                 into this gap, which is where its USB
                                 connector/cable actually live -- matching
                                 camera_mount_overhead.py's own docstring
                                 ("USB connector clearance behind the
                                 board").
  Z = -STANDOFF_H - PCB_T       board's LENS face (bottom of the 1.6 mm PCB)
  Z = -SKIRT_H                  bezel's inner (top) surface -- the skirt's
                                 free/open rim, where the bezel seats

LENS_SPACE = SKIRT_H - STANDOFF_H - PCB_T is the clear vertical gap between
the lens face and the bezel's inner surface, and must be >= LENS_SPACE_MIN
(12 mm, "clears an M12 lens barrel with margin -- see LENS_DIA note below).
Asserted below so a future edit to any one term cannot silently break it.

--------------------------------------------------------------------------
VERIFY BEFORE PRINTING (two open assumptions, flagged the same way
camera_mount_overhead.py flags CAM_HOLE_PITCH)
--------------------------------------------------------------------------
  1. CAM_HOLE_PITCH / M2_TAP / CEIL_SCREW: inherited from
     camera_mount_overhead.py -- see that file's own VERIFY note. Re-measure
     your board before printing.
  2. LENS_DIA = 18 mm is sized to clear an assumed M12-mount lens barrel of
     14 mm OD (LENS_BARREL_DIA_REF) with a 2 mm/side margin. The innomaker
     board's actual lens barrel has NOT been measured for this project --
     confirm the physical lens OD (and that it is in fact an M12-style
     barrel, not a fixed-focus lens with a wider flange) before printing the
     bezel. If the real barrel is wider than 16 mm, widen LENS_DIA to match
     (LENS_SPACE only needs to keep clearing the barrel's length, which is
     independent of this diameter check).

--------------------------------------------------------------------------
Cable exits (two, per the assignment)
--------------------------------------------------------------------------
  1. Through-plate slot (SLOT_L x SLOT_W = 16 x 6 mm, matching the literal
     16/6 values camera_mount_overhead.py already cuts) -- routes the cable
     straight up into the ceiling void.
  2. Side notch in the skirt wall (NOTCH_W x NOTCH_H = 12 x 14.6 mm, both
     comfortably over the 10 x 8 mm minimum) -- routes the cable sideways
     along the ceiling instead. It is OPEN to the skirt's free (bottom) rim
     rather than a fully enclosed window: its bottom edge is NOTCH_BOTTOM_Z
     = -SKIRT_H (the rim itself) and its top edge is NOTCH_TOP_Z =
     -STANDOFF_H (the board's own mounting-face height, i.e. exactly where
     the standoff gap -- and the USB connector living in it -- begins). A
     cable leaving the connector in that gap has a clear, unobstructed path
     down the inside of the wall to this opening. Being open at the rim
     (rather than a closed window higher up the wall) is what makes it
     printable with zero bridging in the orientation below -- see PRINT
     ORIENTATION.

--------------------------------------------------------------------------
PRINT ORIENTATION (no supports)
--------------------------------------------------------------------------
SHELL: printed PLATE-DOWN on the bed (the plate's ceiling/mounting face,
Z=+PLATE_THK, sits on the bed) with the skirt rising in +print-Z as printing
proceeds -- i.e. the model's Z axis is inverted in print space, so the
skirt's free/bottom rim (model Z=-SKIRT_H, the bezel-mating edge) is the
LAST thing printed, the single free/open edge of the whole part. The side
notch is open exactly at that edge (see above), so nothing above it needs a
bridge or support -- the printer simply stops depositing material there for
that band of layers. The 4 standoff posts' and 4 corner bosses' M2/M3
self-tap holes are vertical (parallel to the model Z axis = print axis), so
each layer's hole prints as a normal circular perimeter, no bridging. The
ceiling screw holes and cable slot are also straight verticals through the
plate. No feature exceeds a 45-degree overhang.
BEZEL: printed flat, lens-face down or up (a flat plate, either way is
support-free) -- the lens opening and 4 screw clearance holes are both
straight verticals through the BEZEL_T thickness.

No vent is added: the camera dissipates roughly 1 W, well within what an
enclosure this size sheds by conduction/radiation alone -- not enough to
justify compromising the enclosed/dust-protected design intent.
"""

from __future__ import annotations

import cadquery as cq

from ..params import SCREW_M3, SCREW_M3_TAP, WALL
from .camera_mount_overhead import (
    CAM_HOLE_PITCH, M2_TAP, CEIL_SCREW,
    POST_H as STANDOFF_H, POST_DIA as STANDOFF_POST_DIA,
)

# --- Shell plate ------------------------------------------------------------
# Bigger than camera_mount_overhead.py's 50 mm bracket plate (not a
# duplicated value -- a deliberately new size for THIS part) to make room for
# the perimeter skirt wall and its 4 corner bosses around the same 28 mm
# camera hole pattern.
PLATE = 56.0                # mm, ceiling plate footprint (square)
PLATE_THK = 4.0              # mm, ceiling plate thickness
CEIL_HOLE_INSET = 6.0        # mm, corner inset for ceiling screw holes
                              # (matches camera_mount_overhead.py's own inset)

# --- Skirt wall ---------------------------------------------------------
SKIRT_WALL_T = WALL          # mm, perimeter wall thickness (params.WALL =
                              # 2.4 mm, meets the >= 2.4 mm spec exactly)
INTERIOR_CLEAR = PLATE - 2 * SKIRT_WALL_T   # mm, clear XY footprint inside
                                              # the skirt (51.2 mm)

# --- Board stack-up (see module docstring) ----------------------------------
PCB_T = 1.6                  # mm, assumption: standard FR4 thickness (same
                              # assumption base_station_case.py documents for
                              # its Uno PCB)
LENS_DIA = 18.0               # mm, bezel lens opening (see VERIFY note)
LENS_BARREL_DIA_REF = 14.0    # mm, assumed M12 lens barrel OD (UNMEASURED,
                              # see VERIFY note) -- 2 mm/side margin below
LENS_SPACE_MIN = 12.0         # mm, required clear depth from the lens face
                              # to the bezel's inner surface (spec minimum)
LENS_SPACE = 13.0             # mm, actual design value (1 mm margin over the
                              # minimum, for barrel-length tolerance)
assert LENS_DIA - LENS_BARREL_DIA_REF >= 4.0, (
    "LENS_DIA must clear the assumed lens barrel by >= 2 mm/side"
)
assert LENS_SPACE >= LENS_SPACE_MIN, (
    f"LENS_SPACE {LENS_SPACE} mm below the required minimum {LENS_SPACE_MIN} mm"
)

SKIRT_H = STANDOFF_H + PCB_T + LENS_SPACE   # mm, plate bottom -> bezel-mating
                                              # rim (24.6 mm); this IS the
                                              # computed interior stack
BEZEL_T = 3.0                 # mm, bezel thickness

BOARD_POCKET_MIN = 36.0       # mm, required clear interior span each axis
                              # (32 mm board + 2 mm/side, spec)
assert INTERIOR_CLEAR >= BOARD_POCKET_MIN, (
    f"interior clear span {INTERIOR_CLEAR} mm is below the required board "
    f"pocket minimum {BOARD_POCKET_MIN} mm -- widen PLATE or thin SKIRT_WALL_T"
)

# --- Camera board standoff posts (unchanged pattern/values from
# camera_mount_overhead.py -- same board, same USB-clearance reasoning) -----
half_pitch = CAM_HOLE_PITCH / 2
STANDOFF_XY = ((half_pitch, half_pitch), (-half_pitch, half_pitch),
               (half_pitch, -half_pitch), (-half_pitch, -half_pitch))

# --- Cable exits --------------------------------------------------------
SLOT_L = 16.0                 # mm, through-plate cable slot length (matches
                              # camera_mount_overhead.py's own 16 mm literal)
SLOT_W = 6.0                  # mm, through-plate cable slot width (matches
                              # camera_mount_overhead.py's own 6 mm literal)

NOTCH_W = 12.0                 # mm, side notch width (spec minimum 10 mm)
NOTCH_BOTTOM_Z = -SKIRT_H      # mm, notch bottom = the skirt's free rim
NOTCH_TOP_Z = -STANDOFF_H      # mm, notch top = the board's own mounting
                              # face, i.e. the bottom of the standoff gap
                              # where the USB connector/cable actually sit
                              # (see module docstring "Cable exits")
NOTCH_H = NOTCH_TOP_Z - NOTCH_BOTTOM_Z   # mm, 14.6 mm (spec minimum 8 mm)
assert NOTCH_W >= 10.0 and NOTCH_H >= 8.0, "side notch below the spec minimum size"
OVERTRAVEL = 1.0               # mm, cutter overtravel for clean through-cuts

# --- Corner bosses (bezel attachment; integral with the skirt, not just the
# 2.4 mm wall -- see module note below) -------------------------------------
BOSS_OD = 7.0                  # mm. Wall around the SCREW_M3_TAP (2.8 mm)
                              # pilot is (7-2.8)/2 = 2.1 mm -- comparable to
                              # camera_mount_overhead.py's own M2 standoff
                              # ratio ((6-1.7)/2 = 2.15 mm) for the same
                              # self-tap-into-PETG approach.
BOSS_EDGE_INSET = 3.5          # mm, boss center inset from the plate edge
BOSS_CENTER = PLATE / 2 - BOSS_EDGE_INSET   # 24.5 mm
BOSS_XY = ((BOSS_CENTER, BOSS_CENTER), (-BOSS_CENTER, BOSS_CENTER),
           (BOSS_CENTER, -BOSS_CENTER), (-BOSS_CENTER, -BOSS_CENTER))
BOSS_PILOT_DIA = SCREW_M3_TAP   # mm, 2.8 mm self-tap M3 pilot (params)
BOSS_PILOT_DEPTH = 8.0          # mm, blind depth from the bezel-side (bottom)
                              # face upward into the boss -- generous M3
                              # thread engagement, well short of BOSS_OD's
                              # own vertical extent
BEZEL_SCREW_CLEARANCE = SCREW_M3   # mm, bezel-side clearance hole (params)

# Sanity: the boss must sit inside the plate footprint...
assert BOSS_CENTER + BOSS_OD / 2 <= PLATE / 2 + 1e-9, (
    "corner boss pokes past the plate/skirt outer footprint -- shrink BOSS_OD "
    "or raise BOSS_EDGE_INSET"
)
# ...must fuse into (not just brush) the skirt wall -- its span must overlap
# the wall's inner face, i.e. reach past INTERIOR_CLEAR/2...
assert BOSS_CENTER + BOSS_OD / 2 > INTERIOR_CLEAR / 2, (
    "corner boss does not reach the skirt wall -- it would be a free-floating "
    "post self-tapping into nothing but its own thin material, not 'integral "
    "to the skirt' as required"
)
# ...and must stay clear of the board pocket by a real margin.
_BOSS_POCKET_MARGIN = 2.0   # mm
assert BOSS_CENTER - BOSS_OD / 2 >= BOARD_POCKET_MIN / 2 + _BOSS_POCKET_MARGIN, (
    "corner boss intrudes on the board pocket clearance zone"
)
del half_pitch, _BOSS_POCKET_MARGIN

# --- Mass budget ----------------------------------------------------------
PETG_DENSITY_G_CM3 = 1.27   # g/cm^3, fallback if cad.materials is unavailable
try:
    from ..materials import MATERIALS as _MATERIALS
    PETG_DENSITY_G_CM3 = _MATERIALS["PETG"]["density_g_cm3"]
except ImportError:
    pass
MASS_BUDGET_G = 60.0


def _standoff_posts() -> cq.Workplane:
    """4x M2 self-tap standoff posts, unchanged pattern from
    camera_mount_overhead.py. Built to extend from Z=0 (plate bottom) down
    to Z=-STANDOFF_H; the pilot hole runs the post's full length (open at
    both the plate-bottom and board-mount ends) so an M2 screw driven up
    from the board threads all the way into it."""
    posts = None
    for sx, sy in STANDOFF_XY:
        post = (
            cq.Workplane("XY").center(sx, sy)
            .circle(STANDOFF_POST_DIA / 2).extrude(-STANDOFF_H)
        )
        posts = post if posts is None else posts.union(post)
    return posts


def _standoff_pilot_holes() -> cq.Workplane:
    holes = None
    for sx, sy in STANDOFF_XY:
        hole = (
            cq.Workplane("XY").center(sx, sy)
            .circle(M2_TAP / 2).extrude(-(STANDOFF_H + OVERTRAVEL))
        )
        holes = hole if holes is None else holes.union(hole)
    return holes


def _skirt_wall() -> cq.Workplane:
    """Perimeter skirt: outer PLATE x PLATE box minus the inner
    INTERIOR_CLEAR x INTERIOR_CLEAR cavity, spanning Z in
    [-SKIRT_H, 0], with the side cable notch cut into the +Y wall."""
    outer = (
        cq.Workplane("XY")
        .box(PLATE, PLATE, SKIRT_H, centered=(True, True, False))
        .translate((0, 0, -SKIRT_H))
    )
    cavity = (
        cq.Workplane("XY")
        .box(INTERIOR_CLEAR, INTERIOR_CLEAR, SKIRT_H + 2 * OVERTRAVEL,
             centered=(True, True, False))
        .translate((0, 0, -SKIRT_H - OVERTRAVEL))
    )
    skirt = outer.cut(cavity)

    notch_cz = (NOTCH_TOP_Z + NOTCH_BOTTOM_Z) / 2
    notch = (
        cq.Workplane("XY")
        .box(NOTCH_W, SKIRT_WALL_T + 2 * OVERTRAVEL, NOTCH_H, centered=(True, True, True))
        .translate((0, PLATE / 2, notch_cz))
    )
    skirt = skirt.cut(notch)
    return skirt


def _corner_bosses() -> cq.Workplane:
    """4x corner bosses, full skirt height (Z in [-SKIRT_H, 0]), fused into
    the skirt wall corners -- see the BOSS_CENTER assertions above for why
    this counts as 'integral to the skirt' rather than self-tapping into the
    thin wall alone."""
    bosses = None
    for bx, by in BOSS_XY:
        boss = (
            cq.Workplane("XY").center(bx, by)
            .circle(BOSS_OD / 2).extrude(-SKIRT_H)
        )
        bosses = boss if bosses is None else bosses.union(boss)
    return bosses


def _boss_pilot_holes() -> cq.Workplane:
    """Blind self-tap M3 pilots, drilled from the bezel-side (bottom, free
    rim) face upward BOSS_PILOT_DEPTH into each boss."""
    holes = None
    for bx, by in BOSS_XY:
        hole = (
            cq.Workplane("XY").center(bx, by)
            .circle(BOSS_PILOT_DIA / 2)
            .extrude(BOSS_PILOT_DEPTH + OVERTRAVEL)
            .translate((0, 0, -SKIRT_H - OVERTRAVEL))
        )
        holes = hole if holes is None else holes.union(hole)
    return holes


def make_shell() -> cq.Workplane:
    # Ceiling plate, with its own ceiling-screw holes and cable slot cut
    # first (while it is still a plain box) so those cuts land only on the
    # plate itself -- same sequencing discipline base_station_case.py and
    # corner_mount.py use for their own top-face cuts.
    plate = cq.Workplane("XY").box(PLATE, PLATE, PLATE_THK, centered=(True, True, False))

    c = PLATE / 2 - CEIL_HOLE_INSET
    plate = (
        plate.faces(">Z").workplane()
        .pushPoints([(c, c), (-c, c), (c, -c), (-c, -c)])
        .hole(CEIL_SCREW)
    )
    plate = (
        plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .slot2D(SLOT_L, SLOT_W, 0).cutThruAll()
    )

    shell = (
        plate
        .union(_skirt_wall())
        .union(_standoff_posts())
        .union(_corner_bosses())
    )
    shell = shell.cut(_standoff_pilot_holes())
    shell = shell.cut(_boss_pilot_holes())
    return shell


def make_bezel() -> cq.Workplane:
    """Local frame: Z=0 is the bezel's own bottom (exterior, room-facing)
    face; Z=+BEZEL_T is its top (interior) face, which mates against the
    shell's skirt rim and corner bosses."""
    bezel = cq.Workplane("XY").box(PLATE, PLATE, BEZEL_T, centered=(True, True, False))

    bezel = (
        bezel.faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .hole(LENS_DIA)
    )
    bezel = (
        bezel.faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .pushPoints(list(BOSS_XY))
        .hole(BEZEL_SCREW_CLEARANCE)
    )
    return bezel


def make() -> tuple[cq.Workplane, cq.Workplane]:
    return make_shell(), make_bezel()


if __name__ == "__main__":
    from ..lib import export

    shell, bezel = make()

    print("interior stack (plate -> standoff -> PCB -> lens space -> bezel):")
    print(f"  STANDOFF_H = {STANDOFF_H} mm, PCB_T = {PCB_T} mm, "
          f"LENS_SPACE = {LENS_SPACE} mm (min {LENS_SPACE_MIN} mm)")
    print(f"  SKIRT_H (computed) = {SKIRT_H} mm = "
          f"{STANDOFF_H} + {PCB_T} + {LENS_SPACE}")
    print(f"  board pocket clear span = {INTERIOR_CLEAR:.2f} mm "
          f"(required >= {BOARD_POCKET_MIN} mm)")
    print(f"  lens opening = {LENS_DIA} mm (assumed barrel OD "
          f"{LENS_BARREL_DIA_REF} mm, UNVERIFIED -- see module docstring)")

    total_g = 0.0
    for name, solid in (("camera_case_overhead_shell", shell),
                         ("camera_case_overhead_bezel", bezel)):
        assert solid.val().isValid(), f"{name}: invalid geometry"
        bb = solid.val().BoundingBox()
        vol_cm3 = solid.val().Volume() / 1000.0
        mass_g = vol_cm3 * PETG_DENSITY_G_CM3
        total_g += mass_g
        print(f"{name}: bbox {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm, "
              f"volume {vol_cm3:.2f} cm^3, mass @ PETG {PETG_DENSITY_G_CM3} "
              f"g/cm^3: {mass_g:.2f} g")
        result = export(solid, name)
        print(f"  {result}")

    print(f"combined mass: {total_g:.2f} g (budget <= {MASS_BUDGET_G} g)")
    assert total_g <= MASS_BUDGET_G, f"combined mass {total_g:.2f} g exceeds {MASS_BUDGET_G} g budget"
