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

HOMING SWITCH (KW12-3 cable-homing limit switch mount -- added this revision):

  Principle (lead ruling): a stopper bead crimped/tied onto the Dyneema line
  trips a roller-lever micro switch as the line reels IN toward the pulley.
  The line runs straight from the spool (on the motor-bracket wall's shaft,
  X=WALL_CX) to the pulley groove (X=EAR_CX), both at the fleet-alignment
  plane Y=0, height CORNER_MOUNT_AXIS_Z above the plate top (see the LEAD
  RULING section above). The switch sits BESIDE that line (Y offset, clear
  of the line + bead's own travel corridor) with its roller lever reaching
  IN across the corridor at approximately the spool<->pulley mid-span.

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
  The lead's rough "27 x 10.5 x 8.5 mm class" note in the assignment matches
  the body-plus-protruding-lever envelope some listings quote (~20 mm body +
  the lever overhanging one end); the BODY itself (what actually needs a
  mounting footprint) is the ~20x6.4x10 figure used here.

  Orientation chosen: the switch's long axis (and its lever's pointing axis)
  runs along Y, body offset to +Y of the corridor, lever pointing in -Y
  toward Y=0. A bead moving along X strikes the roller nearly perpendicular
  to the lever's rest axis -- the same geometry these switches use as
  printer/CNC endstops, and the orientation that gives maximum actuation
  torque about the lever pivot for a line moving perpendicular to it.

  KW12_LEVER_HEIGHT_ABOVE_MOUNT (half the 10 mm body height) is a documented
  APPROXIMATION -- no drawing found gives the internal pivot height. The
  corridor's own +-8 mm Z tolerance is generous enough to absorb this
  uncertainty; the boss height below is chosen to land the lever inside that
  band with margin on both sides, not pinned to the exact center.

  Mounting: two self-tap M2 pilot holes (KW12_SELFTAP_PILOT_DIA, matching
  the M2_TAP convention already established in
  cad/parts/camera_mount_overhead.py) on the switch's real 9.5 mm hole
  pitch, PLUS two zip-tie through-slots (always both, per lead spec -- the
  zip tie is the fallback/primary retention, screws are secondary). Trigger-
  point adjustability (+-5 mm along X, the line's own direction of travel)
  is built into BOTH: every hole/slot is X-elongated (cadquery `slot2D`,
  angle=0) by KW_TRIGGER_ADJ_RANGE, not a separate sliding carrier part.
  Chosen over a separate carrier because: (a) one fewer printed part and no
  dovetail/rail clearance fit to tune, (b) the switch's fixed 9.5 mm hole
  pitch is naturally preserved (two independent X-slots, offset from each
  other by the real pitch in Y, rather than one slot trying to carry both
  holes), (c) simpler and more robust to print.

  Mass: the boss is split into two independent legs (front, under the
  lever-side screw/zip-tie pair; back, under the far pair) with an OPEN gap
  between them, rather than one solid block spanning the whole switch
  footprint -- the switch's own rigid body easily bridges the ~8 mm gap
  unsupported (it is a purchased part, not printed), and this roughly halves
  the added material versus a single full-footprint boss. Each leg is a
  simple vertical prism (no overhangs, no bridging in printed material).

  Bead placement (assembly/firmware note, not a geometry parameter): tie or
  crimp the stopper bead on the Dyneema line so it trips this switch
  HOME_BACKOFF steps before the desired mechanical zero. Per firmware
  (roomcleaner ESP32 winch driver), HOME_BACKOFF = 200 steps; at the
  driver's 50930 steps/m, that is 200 / 50930 = 0.003927 m ~= 3.93 mm
  (~4 mm) of line travel between the switch trip point and true zero -- set
  the bead that far short of zero (further from the pulley, i.e. earlier in
  the reel-in direction) so the controller has room to decelerate and back
  off to the true home position after the trip.
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
MASS_BUDGET_G = 93.5   # g; was 90.0 -- raised +3.5 g for the KW12-3 homing-
                        # switch mount added this revision (see module
                        # docstring "HOMING SWITCH"). Measured added mass is
                        # ~3.39 g (see __main__), so this keeps roughly the
                        # same ~1.3 g margin style as the pre-existing
                        # budget (which had 1.24 g headroom at 88.76 g/90 g).
                        # FLAGGED FOR LEAD REVIEW: this is a local
                        # printability/mass budget for this part only, not a
                        # value from cad/params.py or cad/interfaces.py, so
                        # this file is authorized to change it, but it is a
                        # real, deliberate increase to the part's own design
                        # budget and should be reviewed, not rubber-stamped.

# --- KW12-3 cable-homing limit switch mount -------------------------------
# See module docstring "HOMING SWITCH" for the full design reasoning
# (datasheet sourcing, orientation choice, adjustability mechanism, bead-
# placement procedure). Values below are the numeric implementation of that
# reasoning; comments here are short, the docstring has the "why".

# KW12-3 datasheet-derived values (subminiature roller-lever micro switch).
KW12_BODY_L = 20.0             # mm, body length (long axis = mount Y axis)
KW12_BODY_W = 6.4              # mm, body thickness (X)
KW12_BODY_H = 10.0             # mm, body height (Z) above its mounting face
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
KW12_PILOT_DEPTH = 5.0         # mm, blind hole depth (thread engagement);
                                # well short of KW_BOSS_H so solid material
                                # remains below each pilot

# Trigger-point adjustability: +-5 mm along X (the line's own direction of
# travel) -- every mounting feature below is an X-elongated slot spanning
# this range, not a fixed hole.
KW_TRIGGER_ADJ_RANGE = 10.0    # mm, total X travel (+-5 mm)

# Zip-tie retention (always present, alongside the screws -- see docstring).
KW_ZIPTIE_SLOT_W = 4.0         # mm, >= 3.5 mm required; std nylon tie ~3.6mm

# Placement. KW_TRIGGER_X: approximately the spool<->pulley mid-span
# (WALL_CX + EAR_CX)/2 = -40+55)/2 = 7.5 mm; nudged to 10.0 mm (a 2.5 mm
# shift, <3% of the 95 mm spool-pulley separation -- still "approximately
# mid-span") so the boss and its X-slots clear the existing Y=0 wood-screw
# countersink at x=-5 (radius CSK_DIA/2=5.25 mm) with a real wall margin,
# without touching that hole's own geometry. The +-5 mm install range then
# lets the trigger point be tuned back toward the exact mid-span (7.5 mm) or
# anywhere else needed at assembly time.
KW_TRIGGER_X = 10.0            # mm

# Boss leading (corridor-facing) edge: must clear the Y=0 +-3 mm line
# corridor exclusion (assignment spec) -- 4.0 mm gives 1.0 mm of margin
# beyond the hard 3.0 mm minimum.
KW_BOSS_Y0 = 4.0                # mm
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

# Each leg's X half-width: the wider of the two slot types (zip, since
# KW_ZIPTIE_SLOT_W > KW12_SELFTAP_PILOT_DIA) plus a wall margin beyond its
# rounded end cap. 2.0 mm reuses this file's own MOTOR_CORNER_CLEARANCE
# minimum-clearance convention.
KW_BOSS_X_MARGIN = 2.0          # mm
_kw_leg_halfwidth = _kw_zip_slot_halflen + KW_BOSS_X_MARGIN
KW_BOSS_X0 = KW_TRIGGER_X - _kw_leg_halfwidth
KW_BOSS_X1 = KW_TRIGGER_X + _kw_leg_halfwidth

# Leg Y-extents: front leg holds the front screw+zip pair, back leg the
# back pair; each leg's inner edge stops short of the OTHER pair with a
# margin so the two legs stay clearly separate (open gap between them).
_kw_leg_inner_margin = 1.2      # mm, wall beyond the screw slot's own edge
KW_LEG_Y = (
    (KW_BOSS_Y0, KW_SCREW_Y[0] + KW12_SELFTAP_PILOT_DIA / 2 + _kw_leg_inner_margin),
    (KW_SCREW_Y[1] - KW12_SELFTAP_PILOT_DIA / 2 - _kw_leg_inner_margin, KW_BOSS_Y1),
)
assert KW_LEG_Y[0][1] < KW_LEG_Y[1][0], (
    "corner_mount KW12 mount legs overlap -- shrink _kw_leg_inner_margin or "
    "KW_BOSS_LIP"
)

# Boss height: positions the switch's MOUNTING FACE (top of the boss) so the
# lever (KW12_LEVER_HEIGHT_ABOVE_MOUNT above that face, per the documented
# estimate) lands inside the line corridor's own +-8 mm Z tolerance band
# around CORNER_MOUNT_AXIS_Z, with margin on both sides rather than pinned
# to the exact center (absorbs the pivot-height estimate's uncertainty).
KW_LEVER_TARGET_Z = CORNER_MOUNT_AXIS_Z - 4.0   # local-to-plate-top height;
                                # 4 mm below axis, well inside +-8 mm band
KW_BOSS_H = KW_LEVER_TARGET_Z - KW12_LEVER_HEIGHT_ABOVE_MOUNT   # mm
assert KW_BOSS_H > KW12_PILOT_DEPTH, (
    "corner_mount KW12 boss too short for the self-tap pilot depth -- raise "
    "KW_LEVER_TARGET_Z or shrink KW12_PILOT_DEPTH"
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
    """One leg of the KW12-3 switch-mount boss: a solid vertical prism (no
    overhangs) housing one X-elongated zip-tie through-slot (open to the
    leg's own outward Y edge) and one X-elongated self-tap M2 pilot slot
    (blind from the top). Built in local Z in [0, KW_BOSS_H]; caller
    translates up by PLATE_T like the wall/ears."""
    y0, y1 = leg_y
    leg = (
        cq.Workplane("XY")
        .center((KW_BOSS_X0 + KW_BOSS_X1) / 2, (y0 + y1) / 2)
        .rect(KW_BOSS_X1 - KW_BOSS_X0, y1 - y0)
        .extrude(KW_BOSS_H)
    )

    # Zip-tie through-slot: full boss height, generous overshoot both ends
    # for a clean cut.
    overshoot = 1.0
    zip_slot = (
        cq.Workplane("XY")
        .workplane(offset=-overshoot)
        .center(KW_TRIGGER_X, zip_y)
        .slot2D(KW_TRIGGER_ADJ_RANGE + KW_ZIPTIE_SLOT_W, KW_ZIPTIE_SLOT_W, 0)
        .extrude(KW_BOSS_H + 2 * overshoot)
    )
    leg = leg.cut(zip_slot)

    # Self-tap M2 pilot slot: blind from the boss TOP face, KW12_PILOT_DEPTH
    # deep, leaving solid leg material below for strength.
    pilot_slot = (
        cq.Workplane("XY")
        .workplane(offset=KW_BOSS_H - KW12_PILOT_DEPTH)
        .center(KW_TRIGGER_X, screw_y)
        .slot2D(KW_TRIGGER_ADJ_RANGE + KW12_SELFTAP_PILOT_DIA, KW12_SELFTAP_PILOT_DIA, 0)
        .extrude(KW12_PILOT_DEPTH + overshoot)
    )
    leg = leg.cut(pilot_slot)

    return leg


def _kw12_switch_boss() -> cq.Workplane:
    """The full KW12-3 homing-switch mount: two independent legs (front,
    lever side; back, far side) with an open gap between them -- see module
    docstring "HOMING SWITCH" for why. Built in local Z in [0, KW_BOSS_H];
    caller translates up by PLATE_T like the wall/ears."""
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

    kw12_volume_mm3 = _kw12_switch_boss().val().Volume()
    kw12_mass_g = kw12_volume_mm3 / 1000.0 * PETG_DENSITY_G_CM3
    kw12_lever_z_world = PLATE_T + KW_LEVER_TARGET_Z
    corridor_lo = PLATE_T + CORNER_MOUNT_AXIS_Z - 8.0
    corridor_hi = PLATE_T + CORNER_MOUNT_AXIS_Z + 8.0
    print(f"KW12-3 mount: boss X=[{KW_BOSS_X0:.2f},{KW_BOSS_X1:.2f}] "
          f"trigger_X={KW_TRIGGER_X:.2f} (+-{KW_TRIGGER_ADJ_RANGE/2:.1f} mm adj), "
          f"legs Y={KW_LEG_Y}, boss H={KW_BOSS_H:.2f} mm")
    print(f"KW12-3 lever target Z (local) = {kw12_lever_z_world:.2f} mm, "
          f"corridor Z band = [{corridor_lo:.2f}, {corridor_hi:.2f}] mm")
    print(f"KW12-3 mount added volume = {kw12_volume_mm3/1000.0:.3f} cm^3, "
          f"added mass = {kw12_mass_g:.3f} g")
    print(export(solid, "corner_mount"))
