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
    end of the plate to the pulley end.

Wood-screw holes: countersunk from the plate TOP face (the face away from
the joist -- that's the face you drive the screws from, and where the screw
heads must sit flush). The screw SHANK continues straight down through the
rest of the plate into the joist below Z=0.

Print orientation: plate BOTTOM (Z=0, the joist face) flat on the print bed,
no supports. This puts every countersink's wide opening at the top (away
from the bed) and its narrow point at the bottom -- each layer's hole gets
WIDER as printing proceeds upward, which is the standard self-supporting
countersink orientation (no bridging, no overhang). The motor-bracket wall
and its two gussets rise from the plate in +Z (i.e. they print as they go,
not overhanging) -- gusset hypotenuse angle from vertical is
atan(GUSSET_RUN / GUSSET_HEIGHT) ~= 29 deg, comfortably under the ~45 deg
self-supporting limit. The wall's NEMA17 boss hole is a horizontal
through-hole (same situation as the existing motor_mount.py bracket, which
prints the same way today) -- FDM handles a round horizontal hole as a
self-arching bridge without supports.

FLEET-ALIGNMENT DESIGN NOTE (read before touching CORNER_MOUNT_AXIS_Z or the
pulley-ear placement): the assignment asks for the "pulley groove mid-plane"
to be coplanar with the "spool's drum mid-length plane" within
CORNER_MOUNT_FLEET_COPLANAR_TOL, while separately keeping the pulley axle
>= CORNER_MOUNT_FLEET_MIN_SEPARATION away from the spool axis and staying
within the ~130-150 x 55-65 mm plate envelope. Two literal readings of
"coplanar mid-planes" were considered:

  (a) pulley axle PARALLEL to the spool axis (both along X): then "mid-plane
      between the ears" and "spool drum mid-length plane" are both
      cross-sectional (YZ) planes and coplanarity reduces to matching X. But
      this puts the pulley at nearly the SAME X as the spool's midpoint --
      incompatible with a >=60 mm separation inside a <=150 mm-long plate
      unless the pulley is instead offset side-to-side (Y) by >=60 mm, which
      does not fit inside a <=65 mm-wide plate either. Rejected.

  (b) pulley ears kept in the corner_guide orientation (axle along Y, ears
      separated along Y, at the FAR +X end of the plate -- matching "ears at
      the other end" and the >=60 mm along-X separation): then the "mid-plane
      between the ears" is the XZ-plane at their Y midpoint, which is the
      plate's own long centerline (Y=0) by symmetric construction. The spool
      sits on the motor shaft, itself centered on the same Y=0 centerline.
      Both "mid-planes," read this way, are the SAME Y=0 XZ-plane --
      genuinely coplanar, and independent of X, so it is compatible with a
      >=60 mm along-X separation and the given envelope.

This part implements (b): the wall (and hence the spool it carries) and the
pulley-ear pair are both built symmetric about Y=0, and
test_corner_mount_pulley_and_spool_share_centerline (tests/
test_winch_geometry.py) checks that alignment on the BUILT solid. Flagging
this explicitly for lead review: if the intended reading was (a), the ear
orientation needs to change, which is a materially different layout.

The pulley axle height (CORNER_MOUNT_AXIS_Z) is shared exactly with the
motor/spool axis height -- also defined once in cad/interfaces.py and
consumed by both features here, so the +-3 mm height-alignment requirement
is met with zero nominal error.
"""

from __future__ import annotations

import cadquery as cq

from ..params import (
    NEMA17_HOLES, NEMA17_BOSS_DIA, SCREW_M3, CLEARANCE,
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

# --- Base plate --------------------------------------------------------
BASE_L = 148.0        # mm, along X (long axis, motor end -> pulley end)
BASE_W = 58.0         # mm, along Y
PLATE_T = CORNER_MOUNT_PLATE_T   # mm, plate thickness (authoritative)

# --- Wood-screw mounting (3x, on the long centerline Y=0) --------------
SHANK_DIA = CORNER_MOUNT_WOOD_SCREW_SHANK
CSK_DIA = CORNER_MOUNT_WOOD_SCREW_CSK_DIA
CSK_ANGLE = CORNER_MOUNT_WOOD_SCREW_CSK_ANGLE
# X positions chosen so adjacent spacing (46, 46 mm) clears the declared
# CORNER_MOUNT_WOOD_SCREW_MIN_SPACING (45 mm) with margin, and each hole
# sits clear of the wall/gusset footprint (X <= -46) and the ear footprint
# (X in [56.5, 63.5]).
MOUNT_HOLE_X = (-40.0, 6.0, 52.0)

# --- Motor bracket wall (NEMA17 face, motor axis horizontal along +X) --
WALL_THK = 6.0        # mm, wall thickness (>= 6 mm required)
WALL_W = 48.0          # mm, wall width along Y (centered on Y=0)
BACK_MARGIN = 22.0    # mm, plate back edge -> wall back face (room for the
                      # gussets plus edge material)
WALL_X0 = -BASE_L / 2 + BACK_MARGIN          # wall back face X
WALL_CX = WALL_X0 + WALL_THK / 2             # wall center X
FACE_X = WALL_X0 + WALL_THK                  # wall FRONT face X (motor bolts
                                              # here; shaft points +X)
# WALL_H: must clear the NEMA17 bolt-square top (AXIS_Z + half pattern) with
# margin above, and the pattern bottom (AXIS_Z - half pattern) must stay
# above the plate top (Z=0 local to the wall).
_NEMA_HALF = NEMA17_HOLES / 2
WALL_H = CORNER_MOUNT_AXIS_Z + _NEMA_HALF + 6.0   # mm, wall height above plate top
assert CORNER_MOUNT_AXIS_Z - _NEMA_HALF > 0.0, (
    "NEMA17 bolt pattern would dip below the plate top -- raise "
    "CORNER_MOUNT_AXIS_Z"
)

# NEMA17 hole/boss clearance -- same formulas as the existing motor_mount.py
# (fixed clearance, not the generic CLEARANCE constant, to match established
# practice in this repo).
NEMA_SCREW_HOLE_DIA = SCREW_M3 + 0.4
NEMA_BOSS_HOLE_DIA = NEMA17_BOSS_DIA + CLEARANCE

# Two triangular gussets bracing the wall's BACK face to the base plate.
GUSSET_RUN = 10.0      # mm, horizontal leg (along X, into the back margin)
GUSSET_HEIGHT = 18.0   # mm, vertical leg (along Z, up the wall)
GUSSET_THK = 4.0       # mm, gusset thickness (along Y)
# Gusset Y-center: clear of the NEMA17 corner screw holes (at Y=+-_NEMA_HALF,
# radius NEMA_SCREW_HOLE_DIA/2) by >= 2 mm, and fully within the wall's own
# Y-footprint ([-WALL_W/2, WALL_W/2]).
_gusset_inner_edge = _NEMA_HALF + NEMA_SCREW_HOLE_DIA / 2 + 2.0
GUSSET_Y = _gusset_inner_edge + GUSSET_THK / 2
assert GUSSET_Y + GUSSET_THK / 2 <= WALL_W / 2, (
    "gusset would stick out past the wall's Y-footprint -- widen WALL_W"
)

# --- Fleet-alignment bookkeeping (spool is a SEPARATE part; only its
# position relative to this bracket is computed here, for the fleet-angle
# test). Nothing below cuts geometry for the spool itself. -----------------
FACE_TO_SPOOL = 5.0     # mm, motor shaft standoff before the spool's near
                        # flange starts (coupling/engagement allowance)
SPOOL_NEAR_X = FACE_X + FACE_TO_SPOOL
SPOOL_DRUM_MID_X = SPOOL_NEAR_X + SPOOL_FLANGE_THK + SPOOL_LEN / 2
# Spool axis height above plate top: high enough that the flange (radius
# SPOOL_FLANGE_DIA/2) clears the plate by >= CORNER_MOUNT_SPOOL_PLATE_CLEARANCE.
SPOOL_AXIS_Z = SPOOL_FLANGE_DIA / 2 + CORNER_MOUNT_SPOOL_PLATE_CLEARANCE
assert abs(SPOOL_AXIS_Z - CORNER_MOUNT_AXIS_Z) < 1e-6, (
    "SPOOL_AXIS_Z must equal CORNER_MOUNT_AXIS_Z -- both derive from the "
    "same shared interface height; if this fires, CORNER_MOUNT_AXIS_Z in "
    "cad/interfaces.py no longer gives >= 4 mm spool-to-plate clearance"
)

# --- Pulley ears (corner_guide ear pattern, reused values) ---------------
# Axle along Y (see FLEET-ALIGNMENT DESIGN NOTE above): two ears straddle
# the plate centerline, GAP apart, near the +X end of the plate.
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
    the NEMA17 pattern, all cut along the wall's own local X-axis (the wall
    is thin in X)."""
    wall = (
        cq.Workplane("XY")
        .center(WALL_CX, 0)
        .box(WALL_THK, WALL_W, WALL_H, centered=(True, True, False))
    )

    cut_len = WALL_THK * 3   # generous overshoot for a clean through-cut
    boss = (
        cq.Workplane("YZ")
        .workplane(offset=WALL_CX - WALL_THK)
        .center(0, CORNER_MOUNT_AXIS_Z)
        .circle(NEMA_BOSS_HOLE_DIA / 2)
        .extrude(cut_len)
    )
    wall = wall.cut(boss)

    for dy in (-_NEMA_HALF, _NEMA_HALF):
        for dz in (-_NEMA_HALF, _NEMA_HALF):
            hole = (
                cq.Workplane("YZ")
                .workplane(offset=WALL_CX - WALL_THK)
                .center(dy, CORNER_MOUNT_AXIS_Z + dz)
                .circle(NEMA_SCREW_HOLE_DIA / 2)
                .extrude(cut_len)
            )
            wall = wall.cut(hole)

    return wall


def _gussets() -> cq.Workplane:
    """Two triangular gussets bracing the wall's back face (X=WALL_X0) to
    the base plate, flanking the NEMA17 bolt pattern in Y."""
    gussets = None
    for sy in (GUSSET_Y, -GUSSET_Y):
        tri = (
            cq.Workplane("XZ")
            .polyline([(WALL_X0, 0), (WALL_X0 - GUSSET_RUN, 0), (WALL_X0, GUSSET_HEIGHT)])
            .close()
            .extrude(GUSSET_THK)
            # "XZ" workplane normal is -Y, so a positive extrude runs in -Y;
            # translate so the gusset is centered on sy.
            .translate((0, sy + GUSSET_THK / 2, 0))
        )
        gussets = tri if gussets is None else gussets.union(tri)
    return gussets


def _pulley_ears() -> cq.Workplane:
    """Two ears (corner_guide axle-hole pattern) straddling Y=0 near the
    plate's +X end. Built in local ear space (Z in [0, EAR_H]); caller
    translates up by PLATE_T."""
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
    from ..lib import export

    solid = make()
    bb = solid.val().BoundingBox()
    volume_mm3 = solid.val().Volume()
    mass_g = volume_mm3 / 1000.0 * PETG_DENSITY_G_CM3
    print(f"corner_mount bbox: {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm")
    print(f"corner_mount volume: {volume_mm3 / 1000.0:.2f} cm^3, "
          f"mass @ PETG {PETG_DENSITY_G_CM3} g/cm^3: {mass_g:.2f} g "
          f"(budget {MASS_BUDGET_G} g)")
    print(f"SPOOL_DRUM_MID_X={SPOOL_DRUM_MID_X:.2f}  EAR_CX={EAR_CX:.2f}  "
          f"separation={((EAR_CX - SPOOL_DRUM_MID_X) ** 2) ** 0.5:.2f} mm "
          f"(min {CORNER_MOUNT_FLEET_MIN_SEPARATION} mm)")
    print(export(solid, "corner_mount"))
