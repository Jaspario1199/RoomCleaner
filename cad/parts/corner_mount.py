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

HOMING SWITCH (KW12-3 cable-homing limit switch mount -- rev C, drop arm):

  Rev C relocates the mount per DECISIONS.md D14: the earlier rev (mid-span
  boss on the horizontal spool<->pulley span) made "home" mean "bead between
  spool and pulley", so the bead had to climb the pulley groove's own flanges
  (sized for 0.5 mm line) on every descent and every homing run. Rev C moves
  the switch to a short DROP ARM beside the vertical line below the pulley,
  where the bead lives permanently -- it never crosses the pulley groove.

  Line geometry (local frame, see the module docstring header): the line
  runs horizontally from the spool (X=WALL_CX) to the pulley groove
  (X=EAR_CX), both at Y=0, height CORNER_MOUNT_AXIS_Z above the plate top,
  wraps the pulley's +X side, and drops vertically in +Z at
  X = EAR_CX + CORNER_PULLEY_OD_NOM / 2 (interfaces.py; 18-22 mm purchased-
  pulley range accepted, +-1 mm X uncertainty absorbed by the 18 mm lever).
  Reel-in moves the bead in -Z (toward the pulley) -- actuation direction is
  now vertical, not horizontal.

  KW12-3 datasheet values used (subminiature roller-lever micro switch;
  cross-checked across multiple vendor datasheets/listings -- SDTC Tech,
  HiLetgo, Bolsen, Beautyforall, DEVMO -- which agree to within listing
  rounding, and a same-architecture Wurth Elektronik subminiature-microswitch
  datasheet giving 19.8 x 6.4 x 9.5 mm for the identical body style):
    body (pins/lever excluded)   ~20.0 x 6.4 x 10.0 mm (L x W x H)
    mounting holes                2x, 2.0 mm dia, 9.5 mm center-to-center,
                                   on the body's long-axis centerline
                                   (implies M2 hardware)
    roller lever                  ~18 mm pivot-to-roller-center, 4.5 mm
                                   roller dia
  These constants are UNCHANGED from rev B -- only their orientation in
  space (and the arm that carries them) changed.

  Orientation (rev C): the switch's long axis is still Y (unchanged -- the
  same 9.5 mm hole pitch runs along Y), body offset to Y >= KW_BOSS_Y0 mm
  (now driven by the PULLEY envelope's own +-5 mm Y half-width, not the
  narrower +-3 mm line-corridor exclusion -- the pulley is the binding
  clearance at this location), lever pointing -Y toward Y=0 to reach the
  drop line. What rotates 90 deg from rev B is the MOUNTING FACE: rev B's
  switch sat flat on a boss TOP (face normal +Z, in-plane axes X/Y, X being
  both the switch's width axis and the trigger-adjustment axis because the
  bead traveled in X). Rev C's bead travels in Z, so the mounting face is
  now a vertical arm face (normal +X, in-plane axes Y/Z, Z being both the
  switch's width axis and the trigger-adjustment axis). The switch's height
  axis (KW12_BODY_H, away from the mount face) now points in +X instead of
  +Z. Mounting screws bore in -X (perpendicular to the new mount face,
  same role -Z played in rev B); zip-tie slots are through-cuts in X.

  KW12_LEVER_HEIGHT_ABOVE_MOUNT (half the 10 mm body height) is a documented
  APPROXIMATION -- no drawing found gives the internal pivot height. In rev B
  this offset was perpendicular to the bead's own travel (Z above a face
  whose in-plane axes were the travel axis X and the pitch axis Y), so it
  only nudged the lever's Z alignment within a generous +-8 mm corridor
  band. In rev C the mount-face normal (X) IS the estimate's own axis, so a
  literal translation would shift the lever's plane off DROP_X by the full
  estimate (~5 mm) -- but compensating for that (moving the mount face 5 mm
  closer to the pulley) would push the arm's legs into the pulley ear's own
  axle-hole footprint (X ~= EAR_CX +- EAR_HOLE_DIA/2). Given the switch's
  4.5 mm roller and 18 mm lever reach already absorb the assignment's
  documented +-1 mm OD-driven X uncertainty, a few mm of additional,
  similarly-uncharacterized mechanism uncertainty is accepted the same way
  -- the mount face is set directly at DROP_X (no compensation), matching
  the arm's actual built position (KW_ARM_X1 = DROP_X). Field calibration
  (moving the whole corner_mount, or re-crimping the bead) is the fallback
  if as-built testing shows this needs tightening.

  Mounting: two self-tap M2 pilot holes (KW12_SELFTAP_PILOT_DIA, matching
  the M2_TAP convention already established in
  cad/parts/camera_mount_overhead.py) on the switch's real 9.5 mm hole
  pitch, PLUS two zip-tie through-slots (always both, per lead spec -- the
  zip tie is the fallback/primary retention, screws are secondary). Trigger-
  point adjustability (+-5 mm, now along Z -- the line's own direction of
  travel in this revision) is built into BOTH: every hole/slot is
  Z-elongated (cadquery `slot2D`, drawn in the ZY plane and extruded along
  X) by KW_TRIGGER_ADJ_RANGE, not a separate sliding carrier part. Chosen
  over a separate carrier for the same reasons as rev B: (a) one fewer
  printed part and no dovetail/rail clearance fit to tune, (b) the switch's
  fixed 9.5 mm hole pitch is naturally preserved (two independent Z-slots,
  offset from each other by the real pitch in Y, rather than one slot
  trying to carry both holes), (c) simpler and more robust to print.

  Arm and mass: a single vertical arm rises from the plate top (self-
  supporting, no overhang -- see "Print orientation" above) beside the +Y
  pulley ear, out to X = EAR_CX + CORNER_PULLEY_OD_NOM / 2 so its vertical
  mount face lines up with the drop line's own X. The arm is split into two
  independent legs (front, lever-side screw/zip-tie pair; back, far pair)
  with an OPEN Y gap between them -- same mass-saving rationale as rev B
  (the switch's own rigid body bridges the ~5 mm gap unsupported; it is a
  purchased part, not printed). Each leg is a simple vertical prism (box,
  extruded in +Z from the plate top -- self-supporting) with the mounting
  slots bored HORIZONTALLY into its +X face -- the same "round/slotted
  horizontal hole self-arches without supports" precedent already used for
  the wall's NEMA17 boss and bolt holes above, just applied to a narrower
  slot. No cantilevered material and no top-down overhang anywhere in the
  arm.

  Bead placement (assembly/firmware note, not a geometry parameter): tie or
  crimp the stopper bead on the Dyneema line so it trips this switch
  HOME_BACKOFF steps before the desired mechanical zero. Per firmware
  (roomcleaner ESP32 winch driver), HOME_BACKOFF = 200 steps; at the
  driver's 50930 steps/m, that is 200 / 50930 = 0.003927 m ~= 3.93 mm
  (~4 mm) of line travel between the switch trip point and true zero -- set
  the bead that far short of zero. In rev C that means ~4 mm FURTHER FROM
  THE PULLEY than the trigger point (earlier in the reel-in, i.e. -Z is
  "toward the pulley" so the bead sits at a slightly larger Z than
  KW_TRIGGER_Z) so the controller has room to decelerate and back off to the
  true home position after the trip.
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

# --- KW12-3 cable-homing limit switch drop-arm mount (rev C) --------------
# See module docstring "HOMING SWITCH" for the full design reasoning
# (D14, line geometry, orientation choice, adjustability mechanism, bead-
# placement procedure). Values below are the numeric implementation of that
# reasoning; comments here are short, the docstring has the "why".

# KW12-3 datasheet-derived values (subminiature roller-lever micro switch).
# UNCHANGED from rev B -- only the mount's orientation changed (see below).
KW12_BODY_L = 20.0             # mm, body length (long axis = mount Y axis)
KW12_BODY_W = 6.4              # mm, body thickness (now the mount's Z axis)
KW12_BODY_H = 10.0             # mm, body height above its mounting face
                                # (now the mount's +X axis -- see docstring)
KW12_HOLE_SPACING = 9.5        # mm, 2x mounting holes, center-to-center
KW12_HOLE_DIA = 2.0            # mm, switch's own molded hole (M2 clearance)
KW12_LEVER_LEN = 18.0          # mm, roller lever pivot -> roller center
KW12_ROLLER_DIA = 4.5          # mm, lever roller diameter
KW12_LEVER_HEIGHT_ABOVE_MOUNT = KW12_BODY_H / 2   # mm, documented estimate
                                # (no datasheet gives the internal pivot
                                # height; see docstring)

# Fastener: self-tap M2 pilot, reusing the project's established M2 self-tap
# convention (cad/parts/camera_mount_overhead.py M2_TAP = 1.7 mm).
KW12_SELFTAP_PILOT_DIA = 1.7   # mm
KW12_PILOT_DEPTH = 5.0         # mm, blind hole depth (thread engagement),
                                # bored in -X from the arm's mount face

# Trigger-point adjustability: +-5 mm along Z (rev C -- the line's own
# direction of travel is now vertical) -- every mounting feature below is a
# Z-elongated slot spanning this range, not a fixed hole. Same total range
# as rev B's X-elongated slots, only the axis changed.
KW_TRIGGER_ADJ_RANGE = 10.0    # mm, total Z travel (+-5 mm)

# Zip-tie retention (always present, alongside the screws -- see docstring).
KW_ZIPTIE_SLOT_W = 4.0         # mm, >= 3.5 mm required; std nylon tie ~3.6mm

# Drop line X (D14 / interfaces.py CORNER_PULLEY_OD_NOM): the line wraps the
# pulley's +X side and drops vertically here. The arm's mount face sits at
# this X so the lever, pointing -Y, reaches the line without any X offset.
DROP_X = EAR_CX + CORNER_PULLEY_OD_NOM / 2   # mm

# Trigger height (assignment spec, D14): local-to-plate-bottom Z, adjustable
# +-5 mm via the Z-elongated slots below.
KW_TRIGGER_Z = PLATE_T + EAR_H + 15.0   # mm
KW_TRIGGER_Z_LOCAL = KW_TRIGGER_Z - PLATE_T   # mm, local-to-plate-top (= EAR_H
                                # + 15.0); used inside the leg-building
                                # functions, which work in the same
                                # local-to-plate-top frame as the wall/ears
                                # and get translated up by PLATE_T in make()

# Arm/boss leading (pulley-facing) edge: the PULLEY ENVELOPE (Ø22 mm, i.e.
# +-11 mm, but only 10 mm WIDE in Y -- +-5 mm about Y=0, per the assignment)
# is the binding Y clearance here (wider than the +-3 mm line-corridor
# exclusion used at this same offset in rev B). KW_BOSS_Y0 = 6.0 mm gives
# 1.0 mm of margin beyond the pulley envelope's 5.0 mm Y half-width, and
# comfortably clears the narrower 3.0 mm line-corridor exclusion too.
KW_BOSS_Y0 = 6.0                # mm
# Extra boss material fwd/aft of the switch body's own footprint, hosting
# the zip-tie notches with real wall margin from the (fixed-pitch) screw
# holes -- see docstring "Mounting".
KW_BOSS_LIP = 1.5               # mm
KW_BODY_Y_FRONT = KW_BOSS_Y0 + KW_BOSS_LIP     # switch body leading edge
KW_BODY_Y_BACK = KW_BODY_Y_FRONT + KW12_BODY_L  # switch body trailing edge
KW_BOSS_Y1 = KW_BODY_Y_BACK + KW_BOSS_LIP       # boss trailing edge

# Screw hole Y-centers, from the switch's own (fixed) hole pitch, referenced
# off the body's actual leading edge -- NOT independently chosen.
_kw_hole_inset = (KW12_BODY_L - KW12_HOLE_SPACING) / 2
KW_SCREW_Y = (
    KW_BODY_Y_FRONT + _kw_hole_inset,
    KW_BODY_Y_BACK - _kw_hole_inset,
)
# Zip-tie slot Y-centers: flush/open to the boss's own leading/trailing
# edges (a printable open notch, not an enclosed hole -- needs no forward
# wall), sized so the inward edge clears the nearest screw slot.
KW_ZIP_Y = (
    KW_BOSS_Y0 + KW_ZIPTIE_SLOT_W / 2,
    KW_BOSS_Y1 - KW_ZIPTIE_SLOT_W / 2,
)
_kw_screw_slot_halflen = (KW_TRIGGER_ADJ_RANGE + KW12_SELFTAP_PILOT_DIA) / 2
_kw_zip_slot_halflen = (KW_TRIGGER_ADJ_RANGE + KW_ZIPTIE_SLOT_W) / 2
assert KW_ZIP_Y[0] + KW_ZIPTIE_SLOT_W / 2 < KW_SCREW_Y[0] - KW12_SELFTAP_PILOT_DIA / 2, (
    "front zip-tie slot would overlap the front screw slot -- widen "
    "KW_BOSS_LIP or shrink KW_ZIPTIE_SLOT_W"
)
assert KW_ZIP_Y[1] - KW_ZIPTIE_SLOT_W / 2 > KW_SCREW_Y[1] + KW12_SELFTAP_PILOT_DIA / 2, (
    "back zip-tie slot would overlap the back screw slot -- widen "
    "KW_BOSS_LIP or shrink KW_ZIPTIE_SLOT_W"
)

# Each leg's Z half-height (rev C: was X half-width in rev B): the wider of
# the two slot types (zip, since KW_ZIPTIE_SLOT_W > KW12_SELFTAP_PILOT_DIA)
# plus a wall margin beyond its rounded end cap. 2.0 mm reuses this file's
# own MOTOR_CORNER_CLEARANCE minimum-clearance convention.
KW_BOSS_Z_MARGIN = 2.0          # mm
_kw_leg_halfheight = _kw_zip_slot_halflen + KW_BOSS_Z_MARGIN
KW_BOSS_Z0 = KW_TRIGGER_Z - _kw_leg_halfheight   # mm, local-to-plate-bottom
KW_BOSS_Z1 = KW_TRIGGER_Z + _kw_leg_halfheight   # mm, local-to-plate-bottom

# Leg Y-extents: front leg holds the front screw+zip pair, back leg the
# back pair; each leg's inner edge stops short of the OTHER pair with a
# margin so the two legs stay clearly separate (open gap between them).
# UNCHANGED formula from rev B -- Y layout is independent of the X/Z swap.
_kw_leg_inner_margin = 1.2      # mm, wall beyond the screw slot's own edge
KW_LEG_Y = (
    (KW_BOSS_Y0, KW_SCREW_Y[0] + KW12_SELFTAP_PILOT_DIA / 2 + _kw_leg_inner_margin),
    (KW_SCREW_Y[1] - KW12_SELFTAP_PILOT_DIA / 2 - _kw_leg_inner_margin, KW_BOSS_Y1),
)
assert KW_LEG_Y[0][1] < KW_LEG_Y[1][0], (
    "corner_mount KW12 mount legs overlap -- shrink _kw_leg_inner_margin or "
    "KW_BOSS_LIP"
)

# Leg depth (X, into the arm from its +X mount face): the self-tap pilot's
# blind depth (KW12_PILOT_DEPTH) plus a minimum wall behind it (assignment
# spec item 4, >= 3 mm). Also comfortably clears the >= 6 mm "stout section
# at the plate/ear joint" requirement (see KW_LEG_Y widths, both 8.8 mm, and
# this 8.0 mm depth).
KW_BOSS_MIN_WALL = 3.0          # mm, minimum wall behind the deepest cut
KW_BOSS_DEPTH = KW12_PILOT_DEPTH + KW_BOSS_MIN_WALL   # mm
assert KW_BOSS_DEPTH >= 6.0, (
    "corner_mount KW12 arm leg depth below the 6 mm plate/ear joint "
    "stoutness requirement -- raise KW12_PILOT_DEPTH or KW_BOSS_MIN_WALL"
)

# Arm X-extent: mount face flush at DROP_X (+X face), bulk extends -X back
# toward the ear/plate interior.
KW_ARM_X0 = DROP_X - KW_BOSS_DEPTH
KW_ARM_X1 = DROP_X

# Arm height (local, above plate top): rises from the plate top (self-
# supporting vertical extrusion, always full height -- the leg's BOTTOM
# already has abundant captured material below the slot band, all the way
# down to the plate) up past KW_BOSS_Z1 by one more KW_BOSS_Z_MARGIN, so the
# TOP of the arm also caps the slot band with a real wall instead of ending
# flush with the topmost slot cut.
KW_ARM_H = KW_BOSS_Z1 - PLATE_T + KW_BOSS_Z_MARGIN   # mm

# --- D14 clearance checks, evaluated at import (assignment item 3) --------
# Pulley envelope: Ø22 mm (top of the declared 18-22 mm accepted OD range;
# this is the RADIAL size, in the XZ plane) x 10 mm WIDE (the Y-extent,
# matching PULLEY_GAP -- the pulley wheel's own width between the ears),
# centered on the axle at (X=EAR_CX, Z=PLATE_T+CORNER_MOUNT_AXIS_Z, Y=0).
# The arm/legs clear it for ANY X or Z because their entire Y-extent is
# >= KW_BOSS_Y0, outside the envelope's own +-5 mm Y half-width.
_PULLEY_ENVELOPE_OD_MAX = 22.0   # mm, top of the 18-22 mm accepted OD range
_PULLEY_ENVELOPE_Y_HALF = PULLEY_GAP / 2   # mm, +-5 mm about Y=0 (envelope
                                # width matches the pulley's own Y footprint)
assert KW_BOSS_Y0 > _PULLEY_ENVELOPE_Y_HALF, (
    "corner_mount KW12 arm dips into the pulley envelope's Y half-width -- "
    "raise KW_BOSS_Y0"
)
# Line corridor: Ø6 mm (+-3 mm) about the line (horizontal span at Y=0, and
# the vertical drop at X=DROP_X, Y=0) plus 1 mm margin -- same >= 4 mm Y
# clearance rule as rev B, already satisfied by the (larger) pulley check
# above.
_LINE_CORRIDOR_Y_HALF = 3.0      # mm
_LINE_CORRIDOR_MARGIN = 1.0      # mm
assert KW_BOSS_Y0 >= _LINE_CORRIDOR_Y_HALF + _LINE_CORRIDOR_MARGIN, (
    "corner_mount KW12 arm dips into the line corridor -- raise KW_BOSS_Y0"
)
# Countersunk wood-screw at X=45 (MOUNT_HOLE_X[2]), CSK radius CSK_DIA/2.
# The arm sits at X in [KW_ARM_X0, DROP_X], far in +X of this screw.
_csk_x, _csk_r = MOUNT_HOLE_X[2], CSK_DIA / 2
assert KW_ARM_X0 - _csk_r > _csk_x + _csk_r, (
    "corner_mount KW12 arm overlaps the X=45 mm countersunk screw -- move "
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


def _kw12_leg(leg_y: tuple, zip_y: float, screw_y: float) -> cq.Workplane:
    """One leg of the KW12-3 switch-mount drop arm: a solid vertical prism
    (no overhangs -- rises straight from the plate top like the wall/ears)
    housing one Z-elongated zip-tie through-slot and one Z-elongated
    self-tap M2 pilot slot, both bored HORIZONTALLY into the leg's +X
    (mount) face -- the same self-arching-horizontal-hole precedent already
    used for the wall's NEMA17 boss/bolt holes, just narrower. Built in
    local Z in [0, KW_ARM_H] (Z=0 is the plate top); caller translates up
    by PLATE_T like the wall/ears. X/Y are already world coordinates (only
    Z is local here), matching how EAR_CX/EAR_SY are used directly in
    _pulley_ears."""
    y0, y1 = leg_y
    leg = (
        cq.Workplane("XY")
        .center((KW_ARM_X0 + KW_ARM_X1) / 2, (y0 + y1) / 2)
        .rect(KW_ARM_X1 - KW_ARM_X0, y1 - y0)
        .extrude(KW_ARM_H)
    )

    # Zip-tie through-slot: full leg depth in X (mount face to back wall),
    # generous overshoot both ends for a clean cut. Z-elongated (angle=90 on
    # the YZ sketch plane -> local-x=Y, local-y=Z, so 90 deg elongates along
    # Z), at fixed Y=zip_y.
    overshoot = 1.0
    zip_slot = (
        cq.Workplane("YZ")
        .workplane(offset=KW_ARM_X0 - overshoot)
        .center(zip_y, KW_TRIGGER_Z_LOCAL)
        .slot2D(KW_TRIGGER_ADJ_RANGE + KW_ZIPTIE_SLOT_W, KW_ZIPTIE_SLOT_W, 90)
        .extrude(KW_BOSS_DEPTH + 2 * overshoot)
    )
    leg = leg.cut(zip_slot)

    # Self-tap M2 pilot slot: blind from the mount FACE (+X, DROP_X),
    # KW12_PILOT_DEPTH deep, leaving KW_BOSS_MIN_WALL of solid leg material
    # behind it for strength. Z-elongated, at fixed Y=screw_y.
    pilot_slot = (
        cq.Workplane("YZ")
        .workplane(offset=DROP_X - KW12_PILOT_DEPTH)
        .center(screw_y, KW_TRIGGER_Z_LOCAL)
        .slot2D(KW_TRIGGER_ADJ_RANGE + KW12_SELFTAP_PILOT_DIA, KW12_SELFTAP_PILOT_DIA, 90)
        .extrude(KW12_PILOT_DEPTH + overshoot)
    )
    leg = leg.cut(pilot_slot)

    return leg


def _kw12_switch_boss() -> cq.Workplane:
    """The full KW12-3 homing-switch drop-arm mount: two independent legs
    (front, lever side / near the pulley; back, far side) with an open Y
    gap between them -- see module docstring "HOMING SWITCH" for why. Built
    in local Z in [0, KW_ARM_H]; caller translates up by PLATE_T like the
    wall/ears."""
    front = _kw12_leg(KW_LEG_Y[0], KW_ZIP_Y[0], KW_SCREW_Y[0])
    back = _kw12_leg(KW_LEG_Y[1], KW_ZIP_Y[1], KW_SCREW_Y[1])
    return front.union(back)


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
    kw12_boss = _kw12_switch_boss()

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

    REV_B_MASS_G = 92.15   # g, rev B measured mass (mid-span KW12 boss) --
                            # for reporting the rev C delta only, not a
                            # design input.
    kw12_volume_mm3 = _kw12_switch_boss().val().Volume()
    kw12_mass_g = kw12_volume_mm3 / 1000.0 * PETG_DENSITY_G_CM3
    kw12_lever_z_world = PLATE_T + KW_TRIGGER_Z_LOCAL + KW12_LEVER_HEIGHT_ABOVE_MOUNT
    print(f"D14 drop line: DROP_X = EAR_CX + CORNER_PULLEY_OD_NOM/2 = "
          f"{DROP_X:.2f} mm")
    print(f"KW12-3 drop-arm mount: legs X=[{KW_ARM_X0:.2f},{KW_ARM_X1:.2f}] "
          f"(depth {KW_BOSS_DEPTH:.1f} mm), trigger_Z={KW_TRIGGER_Z:.2f} mm "
          f"(local, +-{KW_TRIGGER_ADJ_RANGE/2:.1f} mm adj), legs Y={KW_LEG_Y}, "
          f"arm H={KW_ARM_H:.2f} mm")
    print(f"KW12-3 lever target Z (local, world) = {kw12_lever_z_world:.2f} mm "
          f"(trigger {KW_TRIGGER_Z:.2f} mm +- {KW_TRIGGER_ADJ_RANGE/2:.1f} mm "
          f"adjustment)")
    print(f"KW12-3 mount added volume = {kw12_volume_mm3/1000.0:.3f} cm^3, "
          f"added mass = {kw12_mass_g:.3f} g")
    print(f"corner_mount total mass = {mass_g:.2f} g vs rev B "
          f"{REV_B_MASS_G:.2f} g (delta {mass_g - REV_B_MASS_G:+.2f} g), "
          f"budget {MASS_BUDGET_G} g")
    print(export(solid, "corner_mount"))
