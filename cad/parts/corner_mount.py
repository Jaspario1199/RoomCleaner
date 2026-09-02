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

HOMING SWITCH (KW12-3 cable-homing limit switch mount -- rev D, top pad):

  Rev C relocated the mount per DECISIONS.md D14 (mid-span boss -> a drop
  arm beside the vertical line below the pulley, so the bead lives
  permanently on the vertical span and never crosses the pulley groove).
  That relocation itself was correct; rev C's IMPLEMENTATION of it was not.
  Independent verification (verification/corner_mount_revC_report.md,
  check 5) found rev C mounted the KW12-3 on the drop arm's VERTICAL +X
  face, so the switch's lever ran ALONG the drop line's own travel axis (Z)
  instead of ACROSS it -- the roller landed ~5 mm outboard in X and 10.5 mm
  past the line in Y, and a bead moving -Z would push the lever in a
  direction it does not actuate (pressing along the lever's own length,
  not toward the switch body). Not a tolerance problem: wrong-by-
  construction mechanism placement.

  Rev D fix: re-orient the switch onto a HORIZONTAL, +Z-facing pad on top
  of the same drop arm, long axis along Y (across the line), roller end
  toward Y=0. A bead descending in -Z now lands squarely on the roller from
  above and presses it toward the pad (+Z, the correct actuation direction
  for this switch style) -- see the corrected lever model below. Trigger-
  point adjustment (previously a Z-elongated slot) is no longer a printed
  feature at all: the bead's position on the line is retied to set it, so
  the mounting holes below are elongated in X instead, to tune the roller
  onto the line across the purchased pulley's 18-22 mm OD range.

  Line geometry (local frame, see the module docstring header): the line
  runs horizontally from the spool (X=WALL_CX) to the pulley groove
  (X=EAR_CX), both at Y=0, height CORNER_MOUNT_AXIS_Z above the plate top,
  wraps the pulley's +X side, and drops vertically in +Z at
  X = EAR_CX + CORNER_PULLEY_OD_NOM / 2 (interfaces.py; 18-22 mm purchased-
  pulley range accepted). Reel-in moves the bead in -Z (toward the pulley).

  KW12-3 datasheet values used (subminiature roller-lever micro switch;
  cross-checked across multiple vendor datasheets/listings -- SDTC Tech,
  HiLetgo, Bolsen, Beautyforall, DEVMO -- which agree to within listing
  rounding, and a same-architecture Wurth Elektronik subminiature-microswitch
  datasheet giving 19.8 x 6.4 x 9.5 mm for the identical body style):
    body (pins/lever excluded)   ~20.0 x 6.4 x 10.0 mm (L x W x H)
    mounting holes                2x, 2.0 mm dia, 9.5 mm center-to-center,
                                   on the body's long-axis centerline,
                                   inset (20 - 9.5) / 2 = 5.25 mm from each
                                   end (implies M2 hardware)
    roller diameter                4.5 mm (a hardware dimension, independent
                                   of the lever ARM LENGTH figure below,
                                   which the rev C report showed to be
                                   modeled wrong -- see next paragraph)

  CORRECTED LEVER MODEL (rev D -- replaces the rev B/C "18 mm lever
  sticking out past the body" model, which the rev C report showed to be
  the wrong shape of error for a horizontal mount too: a real KW12-style
  roller lever is a short arm HINGED AT ONE END of the body's TOP face,
  lying back OVER the body, with the roller at the free end. These are
  documented ASSUMPTIONS -- no drawing found gives the internal pivot
  location, and the assumptions below should be caliper-verified against a
  real part before this switch is treated as load-bearing for firmware
  homing logic:
    1. KW12_ROLLER_OVERHANG_Y = 1.5 mm -- how far the roller protrudes past
       the body's roller-end face (the lever is hinged at the body's OTHER,
       far end; the roller sits at the free end, just past the near face).
    2. KW12_LEVER_REST_H = 12.0 mm -- roller-center height above the
       MOUNTING face at rest (body is KW12_BODY_H=10 mm tall; the lever
       rides ~2 mm above the body top).
    3. Which end is hinged: the FAR (non-roller) end, per (1).
  Actuation direction: pressing the roller toward the mounting face (+Z on
  this pad) trips the switch -- a bead descending in -Z strikes the roller
  from above (+Z side) and pushes it toward the pad, i.e. the correct
  direction for this lever geometry, unlike rev C's along-the-lever
  loading.

  Switch placement: body centered in X on DROP_X = EAR_CX +
  CORNER_PULLEY_OD_NOM / 2 (so the roller, riding along the body's own X
  center, lands on the line's nominal X with 0 mm error before any tuning).
  Body's roller-end (near) face at KW_BODY_END_Y = KW_HOMING_BEAD_DIA_NOM / 2
  -- i.e. exactly the assumed 5 mm bead's own reach radius, so the PRINTED
  pad is tangent to (never overlaps) the bead's travel envelope while the
  ROLLER -- purchased hardware, not printed, protruding
  KW12_ROLLER_OVERHANG_Y past that face -- reaches on into the bead's own
  path (KW_ROLLER_Y = KW_BODY_END_Y - KW12_ROLLER_OVERHANG_Y = 1.0 mm,
  inside the bead's +-2.5 mm reach). That overlap -- the ROLLER intruding
  on the bead corridor while the ARM does not -- is the entire point of a
  limit switch; a generic "printed material must clear the line corridor"
  rule cannot apply at the one point that is supposed to touch the line, so
  the corridor-clearance checks below are scoped to Z < KW_TAPER_Z0 (the
  pulley-envelope boundary), below the pad/taper region where the switch is
  deliberately close.

  Mounting face height: KW_PAD_Z = PLATE_T + EAR_H + KW_PAD_STANDOFF_ABOVE_EAR
  (10 mm above the pulley ear top) -- a flat pad, roughly analogous to rev
  C's trigger height but now naming the SWITCH's own resting surface rather
  than a mid-band Z-adjustment target (there is no printed Z adjustment in
  rev D; see "no printed trigger adjustment" above).

  Mounting: two self-tap M2 pilot holes (KW12_SELFTAP_PILOT_DIA, matching
  the M2_TAP convention already established in
  cad/parts/camera_mount_overhead.py), bored -Z (blind, KW12_PILOT_DEPTH
  deep) into the pad at the switch's real 9.5 mm hole pitch, EACH
  X-elongated by KW_ROLLER_TUNE_RANGE (+-2 mm) so the whole switch -- and
  with it the roller, which tracks the body's own X center -- can be
  slid onto the line for any purchased pulley in the 18-22 mm OD range
  (worst case OD-driven line deviation from DROP_X is +-1 mm, well inside
  the +-2 mm slot). Retention: the two screws PLUS a zip tie -- a shallow
  (KW_GROOVE_DEPTH = 1.5 mm) horizontal groove recessed around the arm's
  neck just below the pad, so a tie loops over the switch body (resting on
  the pad above) and around the arm below it. A <=1.5 mm step overhang is
  accepted FDM practice (see the taper discussion below for where else that
  allowance is used); screws carry the working mounting load, the tie is
  drop-out retention, same role zip ties played in rev B/C.

  Arm shape and printability: a single vertical post (not split into two
  legs like rev B/C -- the zip-tie groove now needs a continuous neck to
  loop around) rises self-supporting from the plate top. Below
  KW_TAPER_Z0 = PLATE_T + CORNER_MOUNT_AXIS_Z + (pulley OD_MAX / 2) +
  KW_PULLEY_CLEARANCE_MARGIN -- the pulley envelope's own top, plus margin
  -- the post's near-line (front, -Y) face stays at Y >= KW_ARM_Y_LOWER
  (the pulley's own +-5 mm Y half-width plus the same margin), clearing the
  pulley envelope and the line corridor for its entire height there, same
  as rev C's arm. Above KW_TAPER_Z0 (where the pulley envelope no longer
  exists at any Y), the front face widens toward the pad's KW_BODY_END_Y
  edge across the available Z band (KW_PAD_Z - KW_TAPER_Z0) as an exact
  45-degree chamfer (KW_CHAMFER_DY = KW_CHAMFER_H, rise = run, self-
  supporting) for as much of the needed Y-widening as that band allows,
  with the remainder taken up by a single flat step of KW_STEP_DY (<=
  1.5 mm, the same FDM-accepted allowance used for the zip-tie groove) at
  the very top, capping the pad. No face anywhere overhangs more than that
  declared step. The pad's X footprint (KW_PAD_X0..KW_PAD_X1) is sized for
  the switch body plus print margin on one side and the pilot slots'
  elongation-plus-wall on the other, capped on the outboard (+X) edge by
  the plate boundary itself (X <= BASE_L/2) since DROP_X sits only
  BASE_L/2 - DROP_X mm from that edge -- see the KW_PAD_HALF_X asserts for
  the resulting (checked, not assumed) minimum walls.

  Bead placement (assembly/firmware note, not a geometry parameter): tie or
  crimp the stopper bead on the Dyneema line so it trips this switch
  HOME_BACKOFF steps before the desired mechanical zero. Per firmware
  (roomcleaner ESP32 winch driver), HOME_BACKOFF = 200 steps; at the
  driver's 50930 steps/m, that is 200 / 50930 = 0.003927 m ~= 3.93 mm
  (~4 mm) of line travel between the switch trip point and true zero --
  set the bead that far short of zero, i.e. ~4 mm FURTHER FROM THE PULLEY
  than the roller contact point (a slightly larger Z than KW_ROLLER_Z,
  since -Z is "toward the pulley") so the controller has room to
  decelerate and back off to the true home position after the trip.
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
    CORNER_MOUNT_FLEET_HEIGHT_TOL, CORNER_PULLEY_OD_NOM,
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
MASS_BUDGET_G = 105.0   # g; was 93.5 -- raised +11.5 g (lead-approved, rev C
                        # drop-arm assignment) for the taller vertical arm
                        # the KW12-3 homing-switch mount now needs to clear
                        # the pulley envelope and reach the drop-line trigger
                        # height (see module docstring "HOMING SWITCH" and
                        # DECISIONS.md D14). See __main__ for the measured
                        # mass and the delta vs rev B (92.15 g).
                        # FLAGGED FOR LEAD REVIEW: this is a local
                        # printability/mass budget for this part only, not a
                        # value from cad/params.py or cad/interfaces.py, so
                        # this file is authorized to change it, but it is a
                        # real, deliberate increase to the part's own design
                        # budget and should be reviewed, not rubber-stamped.

# --- KW12-3 cable-homing limit switch mount (rev D, top pad) --------------
# See module docstring "HOMING SWITCH" for the full design reasoning
# (D14, the rev C failure and its fix, corrected lever model, adjustability,
# bead-placement procedure). Values below are the numeric implementation of
# that reasoning; comments here are short, the docstring has the "why".

# KW12-3 datasheet-derived body/hole values -- UNCHANGED from rev B/C.
KW12_BODY_L = 20.0             # mm, body length (long axis = mount Y axis)
KW12_BODY_W = 6.4              # mm, body width (mount X axis)
KW12_BODY_H = 10.0             # mm, body height above its mounting face
                                # (+Z, away from the horizontal pad)
KW12_HOLE_SPACING = 9.5        # mm, 2x mounting holes, center-to-center,
                                # on the body's long-axis (Y) centerline
KW12_HOLE_DIA = 2.0            # mm, switch's own molded hole (M2 clearance)
KW12_ROLLER_DIA = 4.5          # mm, lever roller diameter -- a hardware
                                # dimension, independent of the (corrected,
                                # rev D) lever-arm-length/pivot model above

# CORRECTED lever model (rev D) -- see module docstring. Both values are
# documented ASSUMPTIONS (no drawing found gives the internal pivot
# location or height) pending caliper verification against a real part.
KW12_ROLLER_OVERHANG_Y = 1.5    # mm, ASSUMPTION -- roller protrusion past
                                 # the body's roller-end face (lever hinged
                                 # at the body's OTHER, far end)
KW12_LEVER_REST_H = 12.0        # mm, ASSUMPTION -- roller-center height
                                 # above the MOUNTING face at rest (body is
                                 # KW12_BODY_H=10 mm tall; lever rides ~2 mm
                                 # above the body top)

# Self-tap M2 pilot -- unchanged convention (cad/parts/camera_mount_overhead.py
# M2_TAP = 1.7 mm), now bored -Z (down into the pad) instead of -X.
KW12_SELFTAP_PILOT_DIA = 1.7    # mm
KW12_PILOT_DEPTH = 5.0          # mm, blind hole depth (thread engagement)

# Nominal stopper-bead diameter -- ASSUMPTION, ~5 mm ball/crimp bead on the
# 0.5 mm Dyneema line (the working nominal used throughout
# verification/corner_mount_revC_report.md check 5; DECISIONS.md D14's
# "~4 mm" figure is the HOME_BACKOFF *travel* distance, a different
# quantity from the bead's own diameter).
KW_HOMING_BEAD_DIA_NOM = 5.0     # mm, ASSUMPTION

# Switch body position: long axis Y, roller end toward the drop line (Y=0).
# KW_BODY_END_Y sits at exactly the assumed bead's own reach radius -- the
# printed pad is tangent to (never overlaps) the bead's travel envelope,
# while the ROLLER (purchased hardware, not printed) protrudes past it into
# the bead's own path -- see docstring.
KW_BODY_END_Y = KW_HOMING_BEAD_DIA_NOM / 2        # mm, body roller-end face Y
KW_ROLLER_Y = KW_BODY_END_Y - KW12_ROLLER_OVERHANG_Y   # mm, roller center Y

# Drop line X (D14 / interfaces.py CORNER_PULLEY_OD_NOM): the line wraps the
# pulley's +X side and drops vertically here. The switch body is centered in
# X on this line -- the roller then lands on it with 0 mm nominal error.
DROP_X = EAR_CX + CORNER_PULLEY_OD_NOM / 2   # mm
KW_ROLLER_X = DROP_X   # mm, roller center X at rest (body centered on
                        # DROP_X; the lever lies along Y over the body, so
                        # the roller's X tracks the body's own X center)

# Mounting-face (pad) height: a horizontal, +Z-facing pad standing
# KW_PAD_STANDOFF_ABOVE_EAR above the pulley ear top.
KW_PAD_STANDOFF_ABOVE_EAR = 10.0   # mm
KW_PAD_Z = PLATE_T + EAR_H + KW_PAD_STANDOFF_ABOVE_EAR   # mm, local-to-plate-bottom
KW_PAD_Z_LOCAL = KW_PAD_Z - PLATE_T   # mm, local-to-plate-top (the arm-
                                # building function works in this frame and
                                # gets translated up by PLATE_T in make())

KW_ROLLER_Z = KW_PAD_Z + KW12_LEVER_REST_H   # mm, roller center Z at rest

# --- Import-time geometry asserts (assignment item 4) ----------------------
assert abs(KW_ROLLER_X - DROP_X) <= 0.01, (
    "corner_mount KW12 roller X does not coincide with the drop line "
    "(nominal) -- re-check DROP_X / body centering"
)
assert abs(KW_ROLLER_Y) <= 1.5, (
    f"corner_mount KW12 roller Y = {KW_ROLLER_Y:.3f} mm, required within "
    "+-1.5 mm of the drop line's own Y=0"
)

# --- Pulley/line clearance boundary (assignment item 3) --------------------
# Below this Z, the arm must stay outside the pulley's own Y half-width
# (plus margin) -- above it, the pulley envelope no longer exists at this Z
# (envelope top = PLATE_T + CORNER_MOUNT_AXIS_Z + _PULLEY_ENVELOPE_OD_MAX/2),
# so the pad is free to narrow the Y gap down toward the line.
_PULLEY_ENVELOPE_OD_MAX = 22.0     # mm, top of the 18-22 mm accepted OD range
_PULLEY_ENVELOPE_Y_HALF = PULLEY_GAP / 2   # mm, +-5 mm about Y=0 (envelope
                                # width matches the pulley's own Y footprint)
KW_PULLEY_CLEARANCE_MARGIN = 1.5   # mm
KW_TAPER_Z0 = (
    PLATE_T + CORNER_MOUNT_AXIS_Z + _PULLEY_ENVELOPE_OD_MAX / 2
    + KW_PULLEY_CLEARANCE_MARGIN
)   # mm, local-to-plate-bottom
KW_TAPER_Z0_LOCAL = KW_TAPER_Z0 - PLATE_T   # mm, local-to-plate-top
KW_ARM_Y_LOWER = _PULLEY_ENVELOPE_Y_HALF + KW_PULLEY_CLEARANCE_MARGIN   # mm
assert KW_ARM_Y_LOWER > _PULLEY_ENVELOPE_Y_HALF, (
    "corner_mount KW12 arm dips into the pulley envelope's Y half-width"
)
assert KW_TAPER_Z0 < KW_PAD_Z, (
    "corner_mount KW12 pad sits below the pulley-envelope clearance "
    "boundary -- raise KW_PAD_STANDOFF_ABOVE_EAR"
)
assert KW_ROLLER_Z > PLATE_T + CORNER_MOUNT_AXIS_Z + _PULLEY_ENVELOPE_OD_MAX / 2, (
    "corner_mount KW12 roller Z sits inside the pulley envelope -- raise "
    "KW_PAD_STANDOFF_ABOVE_EAR or KW12_LEVER_REST_H"
)

# --- Pad footprint (assignment item 2/3) ------------------------------------
# Front (near-line) edge: flush with the switch body's own roller-end face.
KW_PAD_Y0 = KW_BODY_END_Y   # mm
# Back (far) edge: body length plus a lip of print wall beyond the far
# mounting hole (reuses the rev B/C "boss lip" convention).
KW_PAD_LIP = 1.5             # mm
KW_PAD_Y1 = KW_BODY_END_Y + KW12_BODY_L + KW_PAD_LIP   # mm

# Screw hole Y-centers, from the switch's own (fixed) 9.5 mm hole pitch,
# inset (KW12_BODY_L - KW12_HOLE_SPACING)/2 from each end -- NOT
# independently chosen.
_kw_hole_inset = (KW12_BODY_L - KW12_HOLE_SPACING) / 2
KW_SCREW_Y = (
    KW_BODY_END_Y + _kw_hole_inset,
    KW_BODY_END_Y + KW12_BODY_L - _kw_hole_inset,
)

# Roller-position tuning: +-2 mm along X (rev D -- slides the whole switch,
# and with it the roller, across the line to absorb the purchased pulley's
# 18-22 mm OD uncertainty, +-1 mm on DROP_X). Both pilot holes are
# X-elongated by this range.
KW_ROLLER_TUNE_RANGE = 4.0    # mm, total X travel (+-2 mm)

# Pad X half-width: the wider of (a) the switch body's own footprint plus a
# print margin each side, and (b) the pilot slot's own X extent (tuning
# range + hole dia) plus a minimum wall.
KW_PAD_X_MARGIN = 2.0          # mm, body-width print margin each side
KW_PILOT_SLOT_WALL = 1.5       # mm, minimum wall beyond the pilot slot's cap
_pad_half_x_body = KW12_BODY_W / 2 + KW_PAD_X_MARGIN
_pilot_slot_halflen_x = (KW_ROLLER_TUNE_RANGE + KW12_SELFTAP_PILOT_DIA) / 2
_pad_half_x_pilot = _pilot_slot_halflen_x + KW_PILOT_SLOT_WALL
KW_PAD_HALF_X = max(_pad_half_x_body, _pad_half_x_pilot)

# X footprint: symmetric about DROP_X where the plate allows it; the +X
# (outboard, toward the plate edge) side is capped at the plate boundary
# (assignment item 2 -- "pad X footprint must stay within the plate").
KW_PAD_X0 = DROP_X - KW_PAD_HALF_X
KW_PAD_X1 = min(DROP_X + KW_PAD_HALF_X, BASE_L / 2)
assert KW_PAD_X1 <= BASE_L / 2 + 1e-9, (
    "corner_mount KW12 pad exceeds the plate's X envelope"
)
_ear_x_edge = EAR_CX + EAR_PLATE_T / 2
assert KW_PAD_X0 - _ear_x_edge >= 1.0, (
    f"corner_mount KW12 pad (X0={KW_PAD_X0:.2f}) crowds the +Y pulley ear "
    f"(edge at {_ear_x_edge:.2f}) -- widen the gap or shrink KW_PAD_HALF_X"
)
_pilot_outboard_wall = KW_PAD_X1 - (DROP_X + _pilot_slot_halflen_x)
assert _pilot_outboard_wall >= 1.0, (
    f"corner_mount KW12 pilot slot outboard wall = {_pilot_outboard_wall:.2f} "
    "mm (< 1.0 mm minimum) -- the plate's X envelope leaves too little room "
    "outboard of DROP_X; shrink KW_ROLLER_TUNE_RANGE or widen BASE_L"
)

# --- Front-face taper (assignment item 3): a documented 45 deg chamfer plus
# a small (<= 1.5 mm) capping step, splitting the total Y-widening
# (KW_ARM_Y_LOWER -> KW_PAD_Y0) across the available Z band
# (KW_TAPER_Z0 -> KW_PAD_Z) without ever exceeding the assignment's own
# <= 1.5 mm step-overhang allowance. --------------------------------------
KW_STEP_DY = 1.5   # mm, the max step overhang the assignment allows
_taper_budget_z = KW_PAD_Z - KW_TAPER_Z0
_total_dy = KW_ARM_Y_LOWER - KW_PAD_Y0
KW_CHAMFER_DY = _total_dy - KW_STEP_DY   # mm, an exact 45 deg run
KW_CHAMFER_H = KW_CHAMFER_DY             # mm (45 deg: rise = run)
KW_STEP_H = _taper_budget_z - KW_CHAMFER_H   # mm
assert KW_CHAMFER_DY > 0, (
    "corner_mount KW12 taper: KW_STEP_DY exceeds the total Y-widening -- "
    "shrink KW_STEP_DY"
)
assert KW_STEP_H > 0, (
    "corner_mount KW12 taper: a 45 deg chamfer alone does not fit the "
    f"available {_taper_budget_z:.2f} mm Z band -- raise "
    "KW_PAD_STANDOFF_ABOVE_EAR or accept a larger (still <= 1.5 mm) KW_STEP_DY"
)
KW_CHAMFER_Z0_LOCAL = KW_TAPER_Z0_LOCAL
KW_CHAMFER_Z1_LOCAL = KW_TAPER_Z0_LOCAL + KW_CHAMFER_H
KW_STEP_Y_MID = KW_ARM_Y_LOWER - KW_CHAMFER_DY   # mm, Y at chamfer-top/step-bottom

# --- Zip-tie retention groove (assignment item 2) --------------------------
# A shallow (<= 1.5 mm) recess around the arm's neck, just below the taper,
# so a zip tie loops over the switch body (resting on the pad above) and
# around the arm -- screws carry the mounting load, the tie is drop-out
# retention (same belt-and-suspenders role zip ties played in rev B/C).
KW_GROOVE_DEPTH = 1.5          # mm, matches the assignment's own accepted
                                # step-overhang limit for this print
KW_GROOVE_H = 4.0              # mm, tall enough for a standard nylon tie
                                # (reuses the rev C zip-tie width convention)
KW_GROOVE_Z1_LOCAL = KW_TAPER_Z0_LOCAL   # mm, groove top = taper start
KW_GROOVE_Z0_LOCAL = KW_GROOVE_Z1_LOCAL - KW_GROOVE_H   # mm
assert KW_GROOVE_Z0_LOCAL > 0.5, (
    "corner_mount KW12 zip-tie groove runs below the plate top -- raise "
    "KW_PAD_STANDOFF_ABOVE_EAR or shrink KW_GROOVE_H"
)

# --- Countersunk wood-screw clearance (assignment item 3) ------------------
# The pad/arm sits at X in [KW_PAD_X0, KW_PAD_X1], far in +X of this screw.
_csk_x, _csk_r = MOUNT_HOLE_X[2], CSK_DIA / 2
assert KW_PAD_X0 - _csk_r > _csk_x + _csk_r, (
    "corner_mount KW12 pad overlaps the X=45 mm countersunk screw -- move "
    "the arm or the screw"
)


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


def _kw12_mount_arm() -> cq.Workplane:
    """The KW12-3 homing-switch mount (rev D): a single vertical post rising
    self-supporting from the plate top, its front (near-line, -Y) face
    staying at Y >= KW_ARM_Y_LOWER (clear of the pulley envelope/line
    corridor -- see docstring) until it passes the pulley envelope's own Z
    extent, then widening via an exact 45 deg chamfer plus a small
    (<= KW_STEP_DY) capping step up to a horizontal, +Z-facing pad. The pad
    carries two X-elongated self-tap pilot slots (bored -Z, blind) and is
    girdled by a shallow zip-tie retention groove just below the taper.
    Built in local Z in [0, KW_PAD_Z_LOCAL] (Z=0 is the plate top); caller
    translates up by PLATE_T like the wall/ears. X/Y are already world
    coordinates, matching how EAR_CX/EAR_SY are used directly in
    _pulley_ears."""
    x0, x1 = KW_PAD_X0, KW_PAD_X1
    y_lo, y_hi = KW_ARM_Y_LOWER, KW_PAD_Y1

    # Lower shaft: constant cross-section, clear of the pulley envelope for
    # its entire height.
    lower = (
        cq.Workplane("XY")
        .center((x0 + x1) / 2, (y_lo + y_hi) / 2)
        .rect(x1 - x0, y_hi - y_lo)
        .extrude(KW_TAPER_Z0_LOCAL)
    )

    # 45 deg chamfer: a trapezoidal cross-section (constant along X) swept
    # from the lower shaft's front-Y edge to the narrower profile at the
    # chamfer top -- built directly as a polyline+extrude (not a loft) so
    # the shape is exact and unambiguous.
    chamfer = (
        cq.Workplane("YZ")
        .workplane(offset=x0)
        .polyline([
            (y_lo, KW_CHAMFER_Z0_LOCAL),
            (y_hi, KW_CHAMFER_Z0_LOCAL),
            (y_hi, KW_CHAMFER_Z1_LOCAL),
            (KW_STEP_Y_MID, KW_CHAMFER_Z1_LOCAL),
        ])
        .close()
        .extrude(x1 - x0)
    )

    # Step cap: the pad itself, flat at KW_PAD_Y0 (the assignment's
    # accepted <= KW_STEP_DY step overhang).
    step = (
        cq.Workplane("XY")
        .workplane(offset=KW_CHAMFER_Z1_LOCAL)
        .center((x0 + x1) / 2, (KW_PAD_Y0 + y_hi) / 2)
        .rect(x1 - x0, y_hi - KW_PAD_Y0)
        .extrude(KW_STEP_H)
    )

    arm = lower.union(chamfer).union(step)

    # Zip-tie retention groove: a shallow ring recess around the neck, just
    # below the taper -- recessed on both X sides and the back (Y_hi) face
    # only. The front (-Y) face is deliberately LEFT UN-recessed: it is the
    # face that starts widening (toward the pad) immediately above this
    # band, and that widening itself forms a shoulder that stops a tie from
    # sliding up on that side, without needing a cut. Recessing it too
    # would have pulled the recess into the front screw hole's own Y
    # position (KW_SCREW_Y[0] = 7.75 mm sits inside a would-be 6.5-8.0 mm
    # recessed band), needlessly deepening that pilot hole -- avoided by
    # this asymmetric groove instead.
    groove_outer = (
        cq.Workplane("XY")
        .workplane(offset=KW_GROOVE_Z0_LOCAL)
        .center((x0 + x1) / 2, (y_lo + y_hi) / 2)
        .rect(x1 - x0, y_hi - y_lo)
        .extrude(KW_GROOVE_H)
    )
    groove_inner = (
        cq.Workplane("XY")
        .workplane(offset=KW_GROOVE_Z0_LOCAL)
        .center((x0 + x1) / 2, (y_lo + (y_hi - KW_GROOVE_DEPTH)) / 2)
        .rect(x1 - x0 - 2 * KW_GROOVE_DEPTH, (y_hi - KW_GROOVE_DEPTH) - y_lo)
        .extrude(KW_GROOVE_H)
    )
    arm = arm.cut(groove_outer.cut(groove_inner))

    # Two X-elongated self-tap pilot slots, blind -Z into the pad, at the
    # switch's own (fixed) hole pitch.
    overshoot = 0.5
    for screw_y in KW_SCREW_Y:
        pilot = (
            cq.Workplane("XY")
            .workplane(offset=KW_PAD_Z_LOCAL + overshoot)
            .center(DROP_X, screw_y)
            .slot2D(KW_ROLLER_TUNE_RANGE + KW12_SELFTAP_PILOT_DIA, KW12_SELFTAP_PILOT_DIA, 0)
            .extrude(-(KW12_PILOT_DEPTH + overshoot))
        )
        arm = arm.cut(pilot)

    return arm


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
    kw12_boss = _kw12_mount_arm()

    part = (
        plate
        .union(wall.translate((0, 0, PLATE_T)))
        .union(ears.translate((0, 0, PLATE_T)))
        .union(kw12_boss.translate((0, 0, PLATE_T)))
    )
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

    REV_C_MASS_G = 96.717   # g, rev C measured mass (verification/
                            # corner_mount_revC_report.md Section 2) -- for
                            # reporting the rev D delta only, not a design
                            # input.
    kw12_volume_mm3 = _kw12_mount_arm().val().Volume()
    kw12_mass_g = kw12_volume_mm3 / 1000.0 * PETG_DENSITY_G_CM3
    print(f"D14 drop line: DROP_X = EAR_CX + CORNER_PULLEY_OD_NOM/2 = "
          f"{DROP_X:.2f} mm")
    print(f"KW12-3 mount (rev D): pad X=[{KW_PAD_X0:.2f},{KW_PAD_X1:.2f}] "
          f"Y=[{KW_ARM_Y_LOWER:.2f}(lower)/{KW_PAD_Y0:.2f}(pad)..{KW_PAD_Y1:.2f}], "
          f"KW_PAD_Z={KW_PAD_Z:.2f} mm (world), taper Z0={KW_TAPER_Z0:.2f} mm")
    print(f"KW12-3 roller (assumption-derived): X={KW_ROLLER_X:.3f}  "
          f"Y={KW_ROLLER_Y:.3f}  Z={KW_ROLLER_Z:.2f} mm")
    print(f"KW12-3 mount added volume = {kw12_volume_mm3/1000.0:.3f} cm^3, "
          f"added mass = {kw12_mass_g:.3f} g")
    print(f"corner_mount total mass = {mass_g:.2f} g vs rev C "
          f"{REV_C_MASS_G:.2f} g (delta {mass_g - REV_C_MASS_G:+.2f} g), "
          f"budget {MASS_BUDGET_G} g")
    print(export(solid, "corner_mount"))
