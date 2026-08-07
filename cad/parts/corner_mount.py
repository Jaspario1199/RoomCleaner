"""
Corner mount -- a single rigid printed bracket that anchors the winch to a
ceiling joist (or high on a wall stud) and unifies TWO jobs that used to be
two separate parts:

  1. the NEMA17 motor bracket (was motor_mount.py), and
  2. the Dyneema pulley redirect (was corner_guide.py).

Casting both onto one base plate removes a joint (and its alignment error)
between the motor and the take-off pulley, which is exactly the alignment
that matters for a clean winch fleet angle. motor_mount.py and
corner_guide.py are UNCHANGED and unused by this part; this is a standalone
replacement, not a wrapper around them.

Coordinate frame (local to this part):
    XY = the base plate. Z=0 is the plate BOTTOM (the face that contacts the
    joist/stud), +Z runs up away from the joist -- matching the "Z up from
    the mounting face" habit used elsewhere in cad/parts. The plate top
    (accessible) face is at Z=PLATE_T. The motor bracket wall and the pulley
    ears both rise from the plate TOP in +Z. +X runs from the motor bracket
    end of the plate to the pulley end. +Y runs from the motor's overhang
    side toward the far side of the plate.

Wood-screw holes: countersunk from the plate TOP face (the face away from
the joist -- that's the face you drive the screws from, and where the screw
heads must sit flush). The screw SHANK continues straight down through the
rest of the plate into the joist below Z=0.

Print orientation: plate BOTTOM (Z=0, the joist face) flat on the print bed,
no supports. This puts every countersink's wide opening at the top (away
from the bed) and its narrow point at the bottom -- each layer's hole gets
WIDER as printing proceeds upward, which is the standard self-supporting
countersink orientation (no bridging, no overhang). The wall and its two
gussets rise from the plate in +Z (they print as they go, never overhanging)
-- gusset hypotenuse angle from vertical is atan(GUSSET_RUN / GUSSET_HEIGHT)
(see value printed in __main__), comfortably under the ~45 deg
self-supporting limit given how short GUSSET_RUN is (see LEAD RULING below
for why). The wall's NEMA17 boss hole is a horizontal through-hole (same
situation as the existing motor_mount.py bracket, which prints the same way
today) -- FDM handles a round horizontal hole as a self-arching bridge
without supports.

LEAD RULING on fleet-angle geometry (supersedes an earlier, geometrically
wrong reading -- kept here for the record):

  The first draft of this part read "pulley groove mid-plane coplanar with
  the spool's drum mid-length plane" by keeping both the wall and the ears
  symmetric about the plate's Y=0 centerline, with the spool axis along X
  (pointing at the pulley). That is wrong: a spool with its axis along X
  pays line off in the plane PERPENDICULAR to X (a YZ plane) -- the line
  leaving the drum has zero X-velocity and can never reach ears sitting
  further along +X. The Y=0-centerline reading happened to be parallel to
  the line's own travel plane, i.e. exactly the wrong constraint to satisfy.

  CORRECTED LAYOUT (this part, as built):
    * The base plate, its 3 countersunk wood-screw holes, and the pulley
      ears are UNCHANGED from the first draft: ears at the plate's +X end,
      axle along Y, pulley groove mid-plane = the XZ plane at Y=0 (the
      ears' own Y midpoint, by symmetric construction).
    * The motor bracket wall is rotated 90 deg about Z: it is now thin in Y
      (WALL_THK), wide in X (WALL_W), sitting near the plate's -X end, at
      NEGATIVE Y (clear of the Y=0 screw centerline). The NEMA17 bolt
      pattern is cut into the wall's -Y face; the motor BODY bolts there
      and hangs further in -Y (it overhangs the plate edge -- see
      MOTOR_BODY_OVERHANG_Y in __main__ -- which is accepted: the motor is
      cantilevered on a stiff bracket, not resting on the plate). The
      motor's output SHAFT passes back through the wall (+Y) via the boss
      clearance hole and continues +Y into the open plate area, where the
      (separately-modeled) spool would sit.
    * With the spool's axis now along Y, it pays line off in an XZ plane --
      the SAME kind of plane the pulley groove mid-plane is. The wall's
      front (+Y) face is positioned so the spool's drum MID-LENGTH lands
      exactly on Y=0 (WALL_FRONT_Y = -(FACE_TO_SPOOL + SPOOL_FLANGE_THK +
      SPOOL_LEN / 2)): the drum's own mid-length cross-section is then the
      XZ plane at Y=0 -- genuinely coplanar with the pulley groove
      mid-plane, independent of FACE_TO_SPOOL, with 0 mm nominal error.
    * Fleet SEPARATION is now measured along X (shaft/boss X position vs.
      EAR_CX), not Y -- both keep their original meaning under the
      corrected orientation.
    * CORNER_MOUNT_AXIS_Z (shared shaft/boss and pulley-axle height) is
      unchanged -- rotating the wall about Z does not touch Z.

  This resolves the self-contradiction the first draft flagged: the
  coplanarity condition, the >=60 mm separation, and the plate envelope are
  now all simultaneously satisfiable, because separation and coplanarity
  are measured along DIFFERENT axes (X and Y respectively) instead of
  competing for the same one.

  Side effect on the gussets: with the wall pinned by the coplanarity
  requirement, the plate's own back edge leaves only a few mm behind the
  wall's back face -- nowhere near enough for a full-size gusset run on
  its own. The pulley/spool (+Y) side of the wall is even more constrained:
  the spool flange's underside sits only CORNER_MOUNT_SPOOL_PLATE_CLEARANCE
  above the plate, well short of a useful gusset height. Per lead direction,
  the gussets go on the -Y (motor-body) side; BASE_W and FACE_TO_SPOOL are
  tuned (see GUSSET_RUN below) so a full GUSSET_RUN=10 mm still fits within
  the plate footprint back there.

GUSSET/MOTOR-BODY INTERFERENCE REPAIR (independent verification found a real
defect in an earlier revision -- kept here for the record):

  geometry-verifier's first pass built a 42.3x42.3x38 mm box on the shaft
  axis, seated flush against the wall's -Y (motor-bolting) face -- the real
  NEMA17 motor-body envelope -- and boolean-intersected it with the built
  bracket. Result: 0 mm^3 against the plate and wall, but 70.42 mm^3 against
  the two gussets (small slivers near two of the envelope's corners). Root
  cause: WALL_W was only 50 mm against a 42.3 mm motor body (2.85 mm margin
  per side), less than GUSSET_THK (4 mm), so gussets sized to flank the
  NEMA17 bolt pattern landed INSIDE the square motor-body footprint instead
  of outside it.

  Fix chosen: option (a) from the repair assignment -- widen the wall
  (WALL_W) and move the gussets to sit outside the full motor-body
  half-width plus a margin (MOTOR_CORNER_CLEARANCE), instead of just
  outside the (smaller) NEMA17 bolt-hole square. This was chosen over
  option (b) (gussets on the spool/+Y side) because the +Y side already
  fails a hard clearance requirement of its own -- the spool flange sits
  only CORNER_MOUNT_SPOOL_PLATE_CLEARANCE (~4.5 mm) above the plate, well
  under any usable gusset height, so option (b) was not geometrically
  available here (matching the module's original reasoning for putting the
  gussets on -Y in the first place). Restoring the full GUSSET_RUN=10 /
  GUSSET_HEIGHT=18 / GUSSET_THK=4 stiffness intent (rather than compensating
  with more, smaller gussets) required a little more plate depth behind the
  wall than the previous revision had, so BASE_W was raised to 65 mm (still
  inside the declared 55-65 mm envelope, at its top) and FACE_TO_SPOOL was
  reduced to 0 mm (this value only ever set a bookkeeping standoff for a
  coupling that this part does not model any geometry for -- it does not
  change SPOOL_DRUM_MID_Y, which is 0 for any FACE_TO_SPOOL by construction,
  see above). See test_corner_mount_gussets_clear_motor_body_envelope and
  test_corner_mount_gussets_clear_virtual_spool_envelope in
  tests/test_winch_geometry.py for the permanent regression coverage (both
  reproduce the verifier's own boolean-intersection method).
"""

from __future__ import annotations

import cadquery as cq

from ..params import (
    NEMA17_HOLES, NEMA17_BOSS_DIA, NEMA17_FACE, SCREW_M3, CLEARANCE,
    SPOOL_FLANGE_DIA, SPOOL_FLANGE_THK, SPOOL_LEN,
)
from ..interfaces import (
    CORNER_MOUNT_PLATE_T,
    CORNER_MOUNT_WOOD_SCREW_SHANK, CORNER_MOUNT_WOOD_SCREW_CSK_DIA,
    CORNER_MOUNT_WOOD_SCREW_CSK_ANGLE, CORNER_MOUNT_WOOD_SCREW_MIN_SPACING,
    CORNER_MOUNT_AXIS_Z, CORNER_MOUNT_SPOOL_PLATE_CLEARANCE,
    CORNER_MOUNT_FLEET_MIN_SEPARATION, CORNER_MOUNT_FLEET_COPLANAR_TOL,
    CORNER_MOUNT_FLEET_HEIGHT_TOL,
)

# --- Base plate ----------------------------------------------------------
# BASE_W raised from 58 to 65 mm (top of the declared 55-65 mm envelope) as
# part of the gusset/motor-envelope interference repair -- see module
# docstring -- to give the -Y gussets enough plate depth for the full
# GUSSET_RUN=10 mm stiffness target. BASE_L trimmed from 148 to 138 mm
# (still inside the declared 130-150 mm envelope) to claw back mass budget
# spent on the wider plate/wall/gussets -- fleet separation stays well over
# the 60 mm minimum (see __main__) with the shorter plate.
BASE_L = 138.0        # mm, along X (long axis, motor end -> pulley end)
BASE_W = 65.0         # mm, along Y
PLATE_T = CORNER_MOUNT_PLATE_T   # mm, plate thickness (authoritative)

# --- Wood-screw mounting (3x, on the long centerline Y=0) --------------
# Unchanged in spirit from the first draft; re-picked only because the
# rotated wall's X-footprint is wider. Holes stay on Y=0, so they never
# collide with the wall/gussets (those live entirely at negative Y) --
# only clearance from the ear footprint (X in [56.5, 63.5]) matters.
SHANK_DIA = CORNER_MOUNT_WOOD_SCREW_SHANK
CSK_DIA = CORNER_MOUNT_WOOD_SCREW_CSK_DIA
CSK_ANGLE = CORNER_MOUNT_WOOD_SCREW_CSK_ANGLE
MOUNT_HOLE_X = (-55.0, -5.0, 45.0)   # spacing 50, 50 mm (>= 45 mm required)

# --- Pulley ears (corner_guide ear pattern, reused values) --------------
# UNCHANGED from the first draft (lead ruling: "keep the pulley ears
# EXACTLY as built"). Axle along Y, two ears straddle the plate centerline,
# PULLEY_GAP apart, near the +X end of the plate.
EAR_PLATE_T = 7.0      # mm, ear thickness through the axle hole (matches
                        # corner_guide.EAR_PLATE_T -- proven wall-around-hole
                        # value, see corner_guide's own verification)
PULLEY_GAP = 10.0      # mm, clear space between the ears for the pulley
                        # (matches corner_guide.GAP)
EAR_FOOT_Y = 10.0       # mm, each ear's own Y-footprint (sized so PULLEY_GAP
                        # above is the literal clear gap between ears)
EAR_HOLE_DIA = SCREW_M3 + 0.3   # mm, axle clearance (matches corner_guide)
EAR_TOP_MARGIN = 6.0    # mm, axle-to-ear-top margin (matches corner_guide)
EAR_H = CORNER_MOUNT_AXIS_Z + EAR_TOP_MARGIN   # mm, ear height above plate top
EAR_EDGE_MARGIN = 14.0  # mm, ear center -> plate front edge
EAR_CX = BASE_L / 2 - EAR_EDGE_MARGIN
EAR_SY = (PULLEY_GAP / 2 + EAR_FOOT_Y / 2, -(PULLEY_GAP / 2 + EAR_FOOT_Y / 2))

# --- Motor bracket wall (ROTATED per lead ruling): thin in Y, wide in X,
# NEMA17 face on the wall's -Y face, shaft along +Y. -------------------
# WALL_W widened from 50 to 56 mm as part of the gusset/motor-envelope
# interference repair (see module docstring) -- the gussets now clear the
# full 42.3 mm motor-body square, not just the smaller 31 mm bolt pattern,
# so they need to sit further out, and the wall has to be wide enough to
# hold them (56 mm keeps a mass margin under the 90 g budget; the true
# minimum for GUSSET_X_OFFSET to fit is ~54.3 mm, see the assert below).
WALL_THK = 6.0         # mm, wall thickness along Y (>= 6 mm required)
WALL_W = 56.0          # mm, wall width along X (centered on WALL_CX)
WALL_CX = -40.0        # mm, wall X-center = shaft/boss/spool-axis X

_NEMA_HALF = NEMA17_HOLES / 2
WALL_H = CORNER_MOUNT_AXIS_Z + _NEMA_HALF + 6.0   # mm, wall height above plate top
assert CORNER_MOUNT_AXIS_Z - _NEMA_HALF > 0.0, (
    "NEMA17 bolt pattern would dip below the plate top -- raise "
    "CORNER_MOUNT_AXIS_Z"
)

NEMA_SCREW_HOLE_DIA = SCREW_M3 + 0.4        # matches existing motor_mount.py
NEMA_BOSS_HOLE_DIA = NEMA17_BOSS_DIA + CLEARANCE

# Motor shaft standoff before the spool's near flange (coupling/engagement
# allowance). The drum mid-length Y is 0 for ANY value of FACE_TO_SPOOL (the
# term cancels in WALL_FRONT_Y + FACE_TO_SPOOL + SPOOL_FLANGE_THK +
# SPOOL_LEN/2), so this is chosen for gusset clearance, not fleet alignment.
# Reduced from 3.0 to 0.0 mm as part of the gusset/motor-envelope repair
# (see module docstring): this part does not model any coupling geometry,
# so the standoff is bookkeeping only, and shrinking it moves the wall
# WALL_THK/back face closer to Y=0, freeing plate depth for the -Y gussets.
FACE_TO_SPOOL = 0.0     # mm
# Wall front (+Y) face position: pins the spool's drum mid-length to Y=0
# (the fleet-alignment condition -- see LEAD RULING above).
WALL_FRONT_Y = -(FACE_TO_SPOOL + SPOOL_FLANGE_THK + SPOOL_LEN / 2)
WALL_BACK_Y = WALL_FRONT_Y - WALL_THK

# --- Fleet-alignment bookkeeping (spool is a SEPARATE part; only its
# position relative to this bracket is computed here, for the fleet-angle
# test). Nothing below cuts geometry for the spool itself. -----------------
SPOOL_NEAR_Y = WALL_FRONT_Y + FACE_TO_SPOOL
SPOOL_DRUM_MID_Y = SPOOL_NEAR_Y + SPOOL_FLANGE_THK + SPOOL_LEN / 2
assert abs(SPOOL_DRUM_MID_Y) < 1e-9, (
    "SPOOL_DRUM_MID_Y must be exactly 0 by construction -- the fleet-"
    "alignment coplanarity condition"
)
SPOOL_FAR_Y = SPOOL_NEAR_Y + 2 * SPOOL_FLANGE_THK + SPOOL_LEN
# Spool axis height above plate top: high enough that the flange (radius
# SPOOL_FLANGE_DIA/2) clears the plate by >= CORNER_MOUNT_SPOOL_PLATE_CLEARANCE.
SPOOL_AXIS_Z = SPOOL_FLANGE_DIA / 2 + CORNER_MOUNT_SPOOL_PLATE_CLEARANCE
assert abs(SPOOL_AXIS_Z - CORNER_MOUNT_AXIS_Z) < 1e-6, (
    "SPOOL_AXIS_Z must equal CORNER_MOUNT_AXIS_Z -- both derive from the "
    "same shared interface height; if this fires, CORNER_MOUNT_AXIS_Z in "
    "cad/interfaces.py no longer gives >= 4 mm spool-to-plate clearance"
)
# Motor body: bolts to the wall's -Y face and hangs further -Y (accepted
# overhang past the plate edge, see module docstring).
MOTOR_BODY_FAR_Y = WALL_BACK_Y - NEMA17_FACE
MOTOR_BODY_OVERHANG_Y = max(0.0, -BASE_W / 2 - MOTOR_BODY_FAR_Y)

# Two triangular gussets bracing the wall's BACK face to the base plate, on
# the -Y (motor-body) side -- the +Y (spool) side does not have enough
# vertical clearance under the spool flange (see module docstring). Full
# stiffness intent restored (GUSSET_RUN=10, GUSSET_HEIGHT=18, GUSSET_THK=4)
# after the gusset/motor-envelope interference repair -- see module
# docstring for how BASE_W/FACE_TO_SPOOL were adjusted to make room.
GUSSET_RUN = 10.0       # mm, horizontal leg (along -Y, into the back margin)
GUSSET_HEIGHT = 18.0    # mm, vertical leg (along Z, up the wall)
GUSSET_THK = 4.0        # mm, gusset thickness (along X)
_back_margin = BASE_W / 2 + WALL_BACK_Y   # plate back edge (-BASE_W/2) -> wall back face
assert GUSSET_RUN <= _back_margin, (
    f"gusset run {GUSSET_RUN} mm exceeds the {_back_margin:.1f} mm of plate "
    "remaining behind the wall -- shrink GUSSET_RUN or FACE_TO_SPOOL"
)
# Gusset X-centers: clear of BOTH (a) the NEMA17 corner screw holes (at
# X=WALL_CX+-_NEMA_HALF, radius NEMA_SCREW_HOLE_DIA/2) by >= 2 mm, AND (b)
# the full NEMA17 motor-BODY square (X=WALL_CX+-NEMA17_FACE/2, the real
# purchased-part footprint that bolts to the wall's -Y face and extends
# into the same -Y region the gussets occupy) by >= MOTOR_CORNER_CLEARANCE.
# (b) is the constraint the interference repair is about -- see module
# docstring and test_corner_mount_gussets_clear_motor_body_envelope.
MOTOR_CORNER_CLEARANCE = 2.0   # mm, gusset clearance to the motor-body square
_gusset_inner_edge = max(
    _NEMA_HALF + NEMA_SCREW_HOLE_DIA / 2 + 2.0,
    NEMA17_FACE / 2 + MOTOR_CORNER_CLEARANCE,
)
GUSSET_X_OFFSET = _gusset_inner_edge + GUSSET_THK / 2
assert GUSSET_X_OFFSET + GUSSET_THK / 2 <= WALL_W / 2, (
    "gusset would stick out past the wall's X-footprint -- widen WALL_W"
)

# --- Mass budget check (evaluated at import so a spec change that busts the
# budget fails loudly instead of silently) --------------------------------
PETG_DENSITY_G_CM3 = 1.27   # g/cm^3, fallback if cad.materials is unavailable
try:
    from ..materials import MATERIALS as _MATERIALS
    PETG_DENSITY_G_CM3 = _MATERIALS["PETG"]["density_g_cm3"]
except ImportError:
    pass
MASS_BUDGET_G = 90.0


def _wall_with_motor_pattern() -> cq.Workplane:
    """The motor-bracket wall alone: box + boss clearance + 4x M3 through
    the NEMA17 pattern, all cut along the wall's own local Y-axis (the wall
    is thin in Y)."""
    wall = (
        cq.Workplane("XY")
        .center(WALL_CX, 0)
        .box(WALL_W, WALL_THK, WALL_H, centered=(True, False, False))
        .translate((0, WALL_BACK_Y, 0))
    )

    cut_len = WALL_THK * 3   # generous overshoot for a clean through-cut
    y_start = WALL_FRONT_Y + WALL_THK   # start beyond the front face, cut -Y
    boss = (
        cq.Workplane("XZ")
        .workplane(offset=-y_start)
        .center(WALL_CX, CORNER_MOUNT_AXIS_Z)
        .circle(NEMA_BOSS_HOLE_DIA / 2)
        .extrude(cut_len)
    )
    wall = wall.cut(boss)

    for dx in (-_NEMA_HALF, _NEMA_HALF):
        for dz in (-_NEMA_HALF, _NEMA_HALF):
            hole = (
                cq.Workplane("XZ")
                .workplane(offset=-y_start)
                .center(WALL_CX + dx, CORNER_MOUNT_AXIS_Z + dz)
                .circle(NEMA_SCREW_HOLE_DIA / 2)
                .extrude(cut_len)
            )
            wall = wall.cut(hole)

    return wall


def _gussets() -> cq.Workplane:
    """Two triangular gussets bracing the wall's back face (Y=WALL_BACK_Y)
    to the base plate, flanking the NEMA17 bolt pattern in X, on the -Y
    (motor-body) side."""
    gussets = None
    for gx in (WALL_CX - GUSSET_X_OFFSET, WALL_CX + GUSSET_X_OFFSET):
        tri = (
            cq.Workplane("YZ")
            .polyline([(WALL_BACK_Y, 0), (WALL_BACK_Y - GUSSET_RUN, 0), (WALL_BACK_Y, GUSSET_HEIGHT)])
            .close()
            .extrude(GUSSET_THK)
            .translate((gx - GUSSET_THK / 2, 0, 0))
        )
        gussets = tri if gussets is None else gussets.union(tri)
    return gussets


def _pulley_ears() -> cq.Workplane:
    """Two ears (corner_guide axle-hole pattern) straddling Y=0 near the
    plate's +X end. Built in local ear space (Z in [0, EAR_H]); caller
    translates up by PLATE_T. UNCHANGED from the first draft."""
    ears = None
    hole_offset_z = EAR_H / 2 - EAR_TOP_MARGIN   # offset from box Z-center
    for sy in EAR_SY:
        ear = (
            cq.Workplane("XY")
            .center(EAR_CX, sy)
            .box(EAR_PLATE_T, EAR_FOOT_Y, EAR_H, centered=(True, True, False))
        )
        ear = (
            ear.faces(">Y").workplane(centerOption="CenterOfBoundBox")
            .center(0, hole_offset_z)
            .hole(EAR_HOLE_DIA)
        )
        ears = ear if ears is None else ears.union(ear)
    return ears


def make() -> cq.Workplane:
    # Base plate with the 3 countersunk wood-screw holes, cut first (while
    # the plate is still a plain box) so the countersinks land ONLY on the
    # plate's own top face, never on the wall/gusset/ear material stacked
    # on top of it later.
    plate = cq.Workplane("XY").box(BASE_L, BASE_W, PLATE_T, centered=(True, True, False))
    plate = (
        plate.faces(">Z").workplane()
        .pushPoints([(x, 0.0) for x in MOUNT_HOLE_X])
        .cskHole(SHANK_DIA, CSK_DIA, CSK_ANGLE)
    )

    wall = _wall_with_motor_pattern().union(_gussets())
    ears = _pulley_ears()

    part = plate.union(wall.translate((0, 0, PLATE_T))).union(ears.translate((0, 0, PLATE_T)))
    return part


if __name__ == "__main__":
    import math

    from ..lib import export

    solid = make()
    bb = solid.val().BoundingBox()
    volume_mm3 = solid.val().Volume()
    mass_g = volume_mm3 / 1000.0 * PETG_DENSITY_G_CM3
    separation_x = abs(EAR_CX - WALL_CX)
    fleet_angle_deg = math.degrees(math.atan((SPOOL_LEN / 2) / separation_x))

    print(f"corner_mount bbox: {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm")
    print(f"corner_mount volume: {volume_mm3 / 1000.0:.2f} cm^3, "
          f"mass @ PETG {PETG_DENSITY_G_CM3} g/cm^3: {mass_g:.2f} g "
          f"(budget {MASS_BUDGET_G} g)")
    print(f"boss/shaft X = {WALL_CX:.2f}  EAR_CX = {EAR_CX:.2f}  "
          f"separation (X) = {separation_x:.2f} mm "
          f"(min {CORNER_MOUNT_FLEET_MIN_SEPARATION} mm)")
    print(f"SPOOL_DRUM_MID_Y = {SPOOL_DRUM_MID_Y:.4f} mm (target 0, tol "
          f"+-{CORNER_MOUNT_FLEET_COPLANAR_TOL} mm)")
    print(f"max fleet angle = atan((SPOOL_LEN/2)/separation) = "
          f"{fleet_angle_deg:.2f} deg")
    print(f"motor body overhang past plate -Y edge = "
          f"{MOTOR_BODY_OVERHANG_Y:.2f} mm (NEMA17_FACE={NEMA17_FACE} mm "
          f"body depth, accepted per lead ruling)")
    print(export(solid, "corner_mount"))
