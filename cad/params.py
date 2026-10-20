"""
Shared parameters for all RoomCleaner printed parts (millimeters).

Change values here and re-run `python -m cad.export_all` to regenerate every
STEP/STL. Everything is parametric so the parts adapt to YOUR hardware --
especially MOTOR_SHAFT_DIA (measure your gear motor's shaft) and DYNEEMA_DIA.
"""

# --- Your hardware -- MEASURE THESE and edit ------------------------------
# This build uses NEMA 17 stepper motors (see docs/BOM_ORDER.md). NEMA 17 has a
# 5 mm round shaft and a 42.3 mm square face with an M3 hole pattern.
MOTOR = "NEMA17"          # winch motor type
MOTOR_SHAFT_DIA = 5.0     # mm, NEMA 17 output shaft diameter
MOTOR_SHAFT_FLAT = 0.5    # mm, depth of the D-shaft flat (0 = round shaft)
NEMA17_FACE = 42.3        # mm, NEMA 17 body/face width (square)
NEMA17_HOLES = 31.0       # mm, M3 mounting-hole square pattern
NEMA17_BOSS_DIA = 22.0    # mm, raised pilot boss on the motor face
DYNEEMA_DIA = 1.0         # mm, braided line diameter (100-200 lb ~ 0.8-1.2 mm)
SERVO = "MG996R"          # gripper servo (horn/mount sized for MG996R)

# --- Print / fit tolerances ------------------------------------------------
CLEARANCE = 0.20          # mm, added to holes for a slip fit (tune to printer)
WALL = 2.4                # mm, default wall thickness (~6 perimeters at 0.4 nozzle)
SCREW_M3 = 3.4            # mm, M3 clearance hole
SCREW_M3_TAP = 2.8        # mm, M3 self-tap / thread-forming hole
NUT_M3_AF = 5.5           # mm, M3 nut across-flats (for captive nut pockets)
NUT_M3_THK = 2.4          # mm, M3 nut thickness

# Heat-set inserts: when True, holes that a screw THREADS INTO (i.e. into the
# printed plastic) are widened to the brass insert's melt-in size. Holes that
# only PASS a screw (clearance), thread into METAL (motor/servo), or go into
# flexible TPU (inserts don't hold in TPU) are left alone.
USE_HEATSET_INSERTS = True
INSERT_M3_HOLE = 4.0      # mm, melt-in hole for a standard M3 brass heat-set insert
M3_THREAD_HOLE = INSERT_M3_HOLE if USE_HEATSET_INSERTS else SCREW_M3_TAP

# --- Winch spool -----------------------------------------------------------
SPOOL_DRUM_DIA = 20.0     # mm, core the line winds onto (keep small for torque)
SPOOL_LEN = 26.0          # mm, winding length between flanges
SPOOL_FLANGE_DIA = 36.0   # mm, end flanges that keep the line on
SPOOL_FLANGE_THK = 3.0    # mm

# --- End-effector frame ----------------------------------------------------
EFFECTOR_PLATE = 90.0     # mm, square-ish frame plate size
EFFECTOR_THK = 5.0        # mm, plate thickness
CABLE_EYE_OFFSET = 8.0    # mm, how far cable tie-off sits from the corner

# --- Gripper ---------------------------------------------------------------
SPATULA_WIDTH = 60.0      # mm, blade width that slides under the cloth
SPATULA_LEN = 55.0        # mm, blade length
SPATULA_THK = 1.6         # mm, thin leading edge (print flat!)
SPATULA_RAMP_DEG = 15.0   # deg, shallow ramp angle at the leading edge
FINGER_LEN = 70.0         # mm, Fin Ray finger length
FINGER_BASE = 26.0        # mm, Fin Ray base width
FINGER_RIBS = 6           # number of internal ribs

# --- Claw integration pass (v2 stack-up) ------------------------------------
# Mating values live in cad/interfaces.py (the authoritative contract file);
# they are re-exported here so legacy part scripts keep one import path.
from .interfaces import (   # noqa: F401
    HUB_MOUNT_R, STANDOFF_ANGLES_DEG, STANDOFF_LEN, STANDOFF_OD,
    SERVO_POCKET_L, SERVO_POCKET_W, SERVO_EAR_SPAN, SERVO_EAR_TAP,
    HORN_POCKET_DIA, HORN_POCKET_T, HORN_SCREW_CIRCLE, HORN_SCREW_HOLE,
    DRUM_CORE_R, DRUM_CORE_H, DRUM_FLANGE_R, DRUM_FLANGE_T,
    DRUM_TIEOFF_HOLES, DRUM_TIEOFF_HOLE_D,
    FINGER_SHOULDER_T, FINGER_SHOULDER_GROW, FINGER_SHOULDER_Z0, HUB_THK,
    COVER_SCREW_POS, COVER_INNER_H, COVER_CORNER_NOTCH, COVER_WALL,
    EFFECTOR_REACH_M,
)

# Tendon-relevant finger geometry (authoritative here; the finger part imports it).
# Drum sizing (C1/C2) derives from this value — do not redefine it elsewhere.
NOTCH_GAP = 4.5           # mm, ventral V-notch opening per segment


# =============================================================================
# CLAW CAMERA BAY (CAMBAY_*) -- camera + IMU enclosure unioned onto the
# gripper electrical box ("Gripper_Electric_Housing_Base (2)" in the v6 STEP).
# Master values for cad/parts/claw_camera_bay.py.  Units mm.
# Entries marked MEASURED come from solidworks/gripper_v6_2026-10-20 (read-only
# STEP, see verification/gripper_v6_inspection.md); entries marked VERIFY are
# ASSUMED and must be checked with calipers before printing.
# Bay frame: origin on the tube axis in the box BOTTOM plane (world Y=1091.19),
# axes parallel to the v6 world axes, +Y up (toward the box top lid).
# =============================================================================
# --- electrical box (MEASURED from the v6 STEP) -------------------------------
CAMBAY_BOX_FLANGE_HALF = 63.5     # box outer half-width at the bottom flange (127 mm)
CAMBAY_BOX_FLANGE_T = 5.0         # flat flange height above the box bottom plane
CAMBAY_BOX_UPPER_HALF = 55.0      # outer half-width above the blend (110 mm)
CAMBAY_BOX_BLEND_R = 75.0         # concave R75 blend, flange -> upper wall
CAMBAY_BOX_BLEND_TOP_Y = 39.68    # height where the R75 blend ends (world 1130.87)
CAMBAY_BOX_POCKET_HALF = 45.0     # box interior half-width (90 mm pocket)
CAMBAY_BOX_POCKET_FLOOR_Y = 5.0   # pocket floor height above the box bottom plane
CAMBAY_BOX_LID_SEAT_Y = 73.7      # top-lid seat ledge height (world 1164.89)
CAMBAY_BOX_TOP_Y = 81.2           # box rim height (world 1172.39)
CAMBAY_CORNER_HOLE_Y = 7.05       # cable-line holes through the corner fillets (axis point, world 1098.24)
CAMBAY_CORNER_HOLE_D = 1.5        # their diameter (R0.75); axis on the corner diagonal, rising 21 deg outward
CAMBAY_CORNER_HOLE_EXIT_XZ = 54.4 # mouth centre |x| = |z| (box frame), at height 14.0 above the bottom plane
CAMBAY_CORNER_HOLE_KEEPOUT = 5.0  # required clear distance from those holes

# --- placement ----------------------------------------------------------------
CAMBAY_SIDE = -1                  # -1: bay on the -Z (narrow) side of the claw, +1: +Z
CAMBAY_CAM_R = 90.0               # optical axis distance from the tube axis
CAMBAY_FOV_DIAG_DEG = 70.0        # OV2640 diagonal field of view (assumed)
CAMBAY_SENSOR_ASPECT = (4, 3)     # sensor aspect; long side along bay X (VERIFY)

# --- printed-wall rules -------------------------------------------------------
CAMBAY_WALL = 2.0                 # wall thickness (min allowed)
CAMBAY_FLOOR_T = 2.4              # bay floor, sits on the print bed with the box
CAMBAY_COVER_T = 2.4              # access cover thickness
CAMBAY_BOSS_WALL = 2.5            # min material around a screw/insert hole
CAMBAY_FIT_CLEAR = 0.3            # per-side clearance around boards

# --- Seeed XIAO ESP32-S3 Sense (VERIFY every value with calipers) --------------
# Repo records the OEM-model overall envelope incl. protrusions as 24.363 x 17.78 x 13.96
# (docs/CLAW_SELF_CAD_DESIGN_20261012.md, docs/SELF_CAD_DIMENSIONS_AND_WIRING_20261006.md);
# the cradle is sized for that envelope + CLEAR per side.  USB-C end faces bay +X.
CAMBAY_XIAO_L = 24.363            # envelope along bay X (USB-C end at +X)
CAMBAY_XIAO_W = 17.78             # envelope along the radial direction
CAMBAY_XIAO_H = 13.96             # envelope height, camera face down
CAMBAY_XIAO_USB_Z_FROM_TOP = 1.6  # USB-C centre below the envelope top (VERIFY)
CAMBAY_LENS_DX = 0.0              # lens offset from envelope centre along bay X (VERIFY)
CAMBAY_LENS_DR = 0.0              # lens offset from envelope centre, radial outward + (VERIFY)
CAMBAY_LENS_BARREL_D = 8.0        # lens barrel diameter
CAMBAY_LENS_BARREL_H = 4.5        # barrel protrusion below the board face (VERIFY)
CAMBAY_LENS_WINDOW_X = 17.0       # lens window along bay X (>= 14)
CAMBAY_LENS_WINDOW_R = 16.0       # lens window radial (>= 14); +-3.2 mm lens-position tolerance
CAMBAY_LENS_CHAMFER = 1.0         # 45 deg chamfer on the window's outer edge
CAMBAY_LENS_BLOCK_H = 4.0         # cradle block under the board = hood tunnel depth
CAMBAY_WIRE_HEADROOM = 4.0        # free height above the XIAO for wires / antenna
CAMBAY_USB_PLUG_W = 13.0          # USB-C plug overmould the notch must pass (>= 13)
CAMBAY_USB_PLUG_H = 8.0           # (>= 8); the notch is open at the top and closed by the cover
CAMBAY_USB_PLAY = 0.5             # extra notch width / sill depth around the plug
CAMBAY_ANT_L = 30.0               # flexible U.FL antenna length (VERIFY)
CAMBAY_ANT_W = 10.0               # flexible U.FL antenna width (VERIFY)

# --- Adafruit 3886 MPU6050 breakout (repo-selected IMU; hole positions UNKNOWN ->
# no screw posts: rigid pocket, corner pads, cover pegs, 2 zip-tie slot pairs) ----
CAMBAY_IMU_L = 26.0               # board length (reservation 26 x 17.8 x 4.6)
CAMBAY_IMU_W = 17.8
CAMBAY_IMU_RESERVE_H = 4.6        # height reserved above the pads (board + components)
CAMBAY_IMU_PAD_H = 1.0            # seat pads under the board corners (underside leads/foam)
CAMBAY_IMU_PAD = 3.0              # pad / peg footprint (VERIFY: clear of components)
CAMBAY_IMU_T = 1.6                # PCB thickness (assumed)

# --- wire window into the box (below the lid seat, rim stays continuous) -------
CAMBAY_WIN_W = 10.0               # >= 8
CAMBAY_WIN_H = 7.0                # >= 6
CAMBAY_WIN_Y = 15.5               # window centre height above the box bottom plane
CAMBAY_WIN_FLARE = 1.5            # chamfer flare at both mouths (no wire chafe)

# --- cover fasteners (M3 into heat-set inserts per USE_HEATSET_INSERTS) --------
CAMBAY_COVER_SCREW_R = 70.0       # cover screw columns: radial distance from tube axis
CAMBAY_INSERT_D = 4.1             # heat-set insert melt-in hole (common M3: 4.0-4.2)
CAMBAY_INSERT_LEN = 5.7           # M3 x 5.7 insert
CAMBAY_INSERT_DEPTH = 7.0         # blind hole depth (insert + 1.3 melt-in reserve)
CAMBAY_RIB_T = 2.4                # root gusset rib thickness
CAMBAY_RIB_H = 18.0               # root gusset rib height
CAMBAY_RIB_SPAN_X = 34.0          # gusset reach on the box wall (< 54.4 - 5 keep-out)


# =============================================================================
# GRIPPER v7 -- gearbox redesign (10/20/2026).  Master values for cad/parts/gripper_v7_*.py
# =============================================================================
# v7 LOCAL frame (mm): x lateral (gear-axes plane), +y along the claw/tube axis (toward the tube),
# z along the gear axes, +z toward the servo.
#   origin x : the tube axis (mid-point between the compound and follower axes, as in v6)
#   origin y : the line through the compound/follower axes
#   origin z : the INNER face of the LOWER plate
# World placement for the preview assembly (v6 world frame = local + origin):
GRIPV7_WORLD_ORIGIN = (951.8475, 707.9864, 1079.49)   # gear stack bottom stays at v6 z 1080.49

# --- gear train (MG996R -> 18T pinion -> 36T | 24T -> 24T follower) ---------------------------
GRIPV7_MODULE = 1.5               # mm, unchanged from v6
GRIPV7_Z_PINION = 18              # teeth
GRIPV7_Z_MAIN = 36                # teeth, was 54 (ratio 2:1)
GRIPV7_Z_SYNC = 24                # teeth, compound upper gear and follower (1:1, unchanged)
GRIPV7_TOOTH_THIN = 0.10          # mm thinning per gear at the pitch circle (as v6)
GRIPV7_ROOT_FILLET_R = 0.40       # mm, root blend radius of the v3/v6 generator
GRIPV7_CD_ALLOW = 0.30            # mm added to the nominal centre distance (print allowance; v6 had 0)
GRIPV7_CD_MAIN = GRIPV7_MODULE * (GRIPV7_Z_PINION + GRIPV7_Z_MAIN) / 2 + GRIPV7_CD_ALLOW   # 40.80
GRIPV7_CD_SYNC = GRIPV7_MODULE * GRIPV7_Z_SYNC + GRIPV7_CD_ALLOW                           # 36.30
GRIPV7_FACE_MAIN = 16.0           # pinion and 36T face width (as v6)
GRIPV7_FACE_SYNC = 20.0           # 24T pair face width (as v6)
GRIPV7_RATIO = GRIPV7_Z_MAIN / GRIPV7_Z_PINION   # 2.0
GRIPV7_RIM_MIN_FACTOR = 2.5       # rim radial thickness below root >= 2.5 x module
GRIPV7_SPOKES = 6                 # spokes of the 36T web (>= 5)
GRIPV7_SPOKE_W = 5.0              # mm
GRIPV7_HUB_R = 11.0               # mm, gear hub radius around the bearing pockets

# --- purchased bearings (7x14x5, 607 type) and steel axle pins --------------------------------
GRIPV7_BRG_ID = 7.0
GRIPV7_BRG_OD = 14.0
GRIPV7_BRG_W = 5.0
GRIPV7_BRG_POCKET_D = 14.05       # printed pocket (vertical hole) ...
GRIPV7_BRG_LIP_RELIEF = 0.30      # ... with a 0.3 mm radial relief counterbore at the mouth (NO crush ribs)
GRIPV7_BRG_LIP_RELIEF_DEPTH = 0.6 # mm deep
GRIPV7_BRG_DEPTH_EXTRA = 0.05     # pocket depth = n x 5.0 + 0.05
GRIPV7_BRG_SEAT_BORE = 10.0       # bore past the pocket floor: clears the inner race (VERIFY race OD ~9)
GRIPV7_PIN_D = 7.0                # Ø7 h-tolerance steel dowel pin
GRIPV7_PIN_HOLE_D = 7.05          # blind seat in each plate (vertical print: expect 6.9-7.0 as printed)
GRIPV7_PIN_LEN = 50.0             # buy-able standard length (ISO 2338 series); engagement = (50 - gap)/2
GRIPV7_RACE_BOSS_D = 9.0          # plate boss/ring touching only the stationary inner race (VERIFY race land >= 9.2)
GRIPV7_RACE_AXIAL_GAP = 0.15      # mm gap between race and boss at each end

# --- vertical stack (local z, lower plate inner face = 0) --------------------------------------
GRIPV7_PLATE_T = 6.0              # both plates (flat both faces: print outer face down)
GRIPV7_PLATE_GAP = 42.0           # lower-plate inner face -> upper-plate inner face
GRIPV7_GEAR_Z0 = 1.0              # compound / follower bottom face above the lower plate
GRIPV7_L1_Z0 = GRIPV7_GEAR_Z0                         # main layer (pinion + 36T) 1 .. 17
GRIPV7_L1_Z1 = GRIPV7_L1_Z0 + GRIPV7_FACE_MAIN
GRIPV7_L2_Z0 = GRIPV7_L1_Z1                           # sync layer (24T pair + lugs) 17 .. 37
GRIPV7_L2_Z1 = GRIPV7_L2_Z0 + GRIPV7_FACE_SYNC
GRIPV7_TUBE_Z = 24.5              # tube axis height (v6: 23.5 above the gear stack bottom)
GRIPV7_PIN_ENGAGE = (GRIPV7_PIN_LEN - GRIPV7_PLATE_GAP) / 2     # 4.0 mm into each plate

# --- tube / socket (v6 interface kept: axis, insertion depth) ---------------------------------
GRIPV7_TUBE_OD = 28.54
GRIPV7_TUBE_ID = 22.54
GRIPV7_TUBE_END_Y = 78.4039       # tube lower end (v6: world y 786.39 - 707.99)
GRIPV7_TUBE_INSERT = 42.5         # tube insertion depth into the socket (v6: 828.89 - 786.39)
GRIPV7_TUBE_LEN = 304.8
GRIPV7_TUBE_FIT = 0.15            # radial clearance of the socket bore
GRIPV7_XBOLT_Y_FROM_END = 14.0    # M3 cross-bolt axis (parallel to z) from the tube lower end
GRIPV7_XBOLT_HOLE_D = 3.4         # drilled through the tube along z, and through both plates/saddles

# --- servo MG996R (v6 ESTIMATED reference body -- VERIFY with calipers) ------------------------
GRIPV7_SERVO_X_OFF = 10.0         # shaft axis offset from the servo-body centre / tube axis (v6)
GRIPV7_SERVO_BODY_L = 40.0        # along x
GRIPV7_SERVO_BODY_W = 19.0        # along y
GRIPV7_SERVO_BODY_H = 38.0        # body above the boss
GRIPV7_SERVO_BOSS_D = 17.0
GRIPV7_SERVO_BOSS_H = 2.0
GRIPV7_SERVO_SHAFT_D = 6.0
GRIPV7_SERVO_SHAFT_L = 4.0
GRIPV7_SERVO_EAR_L = 55.0
GRIPV7_SERVO_EAR_T = 3.0
GRIPV7_SERVO_EAR_DROP = 10.0      # boss bottom face -> ear bottom face
GRIPV7_SERVO_EAR_HOLE_DX = 47.0   # ear-hole pitch along x (v6 pattern; interfaces.py says 48.3 -- VERIFY)
GRIPV7_SERVO_EAR_HOLE_DY = 10.0
GRIPV7_SERVO_EAR_HOLE_D = 4.0
GRIPV7_SERVO_CUTOUT_CLEAR = 0.6   # per side: lets the servo float +-0.6 mm so it self-aligns to the pinion pilot before the ear screws are tightened
GRIPV7_SERVO_SCREW = 2.5          # M2.5 ear screws into heat-set inserts (wall at the cutout)
GRIPV7_SERVO_INSERT_D = 3.6       # M2.5 heat-set insert melt-in hole
GRIPV7_SERVO_INSERT_DEPTH = 5.0
# servo boss bottom face = upper-plate TOP face minus the ear drop (ears rest on the plate)
GRIPV7_SERVO_BOSS_Z = GRIPV7_PLATE_GAP + GRIPV7_PLATE_T - GRIPV7_SERVO_EAR_DROP            # 38.0

# --- servo horn (round metal horn, 25T -- envelope, VERIFY every value) -------------------------
GRIPV7_HORN_D = 25.0
GRIPV7_HORN_T = 2.5               # disc
GRIPV7_HORN_HUB_D = 10.0
GRIPV7_HORN_HUB_H = 4.0           # spline hub on the servo side of the disc
GRIPV7_HORN_BOSS_GAP = 0.5        # servo boss bottom -> hub top
GRIPV7_HORN_SCREWS = 4            # M2 screws, from the servo side, into the pinion hub
GRIPV7_HORN_SCREW_R = 8.0         # screw circle radius (VERIFY against the real horn holes)
GRIPV7_HORN_SCREW_D = 2.0
GRIPV7_HORN_SCREW_PILOT_D = 1.7   # self-tapping pilot in PETG
GRIPV7_HORN_SCREW_PILOT_DEPTH = 9.0
GRIPV7_PINION_HUB_D = 20.0        # pinion hub extension above the teeth (carries the horn)
GRIPV7_PINION_PILOT_D = 8.0       # plate pilot post entering the pinion bottom (journal support)
GRIPV7_PINION_PILOT_CLEAR = 0.4   # radial (pilot Ø8.0 in a Ø8.8 bore): safety journal, the servo float absorbs the misalignment
GRIPV7_PINION_PILOT_H = 8.0       # pilot height above the lower plate inner face

# --- jaw four-bar (re-derived for the 2:1 train; see cad/parts/gripper_v7_kin.py) ----------------
# Not a scaled copy of v6: the v6 four-bar (R75, ground 43, coupler 41.3, link 70) is non-Grashof
# and jams at 51 deg of crank travel (arm-link contact), but the 2:1 train needs 76.5 deg at R53.
# The values below come from a constrained search (scratch optimiser, reproducible from the
# constraints listed in calculations/gripper_v7_screening.py / tests): tips meet on x = 0 at the
# closed stop, open gap within 10 % of v6 (97.0 mm), jaw-face tilt <= 3 deg, transmission angles
# >= 30 deg, link clear of both 24T discs, grip force within 10 % of v6 at 20-60 mm gaps.
GRIPV7_CRANK_R = 53.0             # compound / follower lug radius (v6: 75)
GRIPV7_THETA_CLOSED = -78.589     # deg, right crank angle at the closed stop (tips meet on x = 0)
GRIPV7_SWEEP_DEG = 76.5           # deg of compound rotation closed -> open (servo stroke 153 deg / 2)
GRIPV7_LINK_GROUND = (8.0, -30.0)      # right link ground pivot P (x, y); the left one mirrors it
GRIPV7_JAW_AB = 31.81             # crank-pin to link-pin distance on the jaw (v6: 41.3)
GRIPV7_JAW_PSI_CLOSED = -113.589  # deg, direction A -> B at the closed pose (link length follows: 51.7)
GRIPV7_JAW_TIP_DROP = 75.0        # tip of the inner face below the crank pin at the closed pose

# --- frame layout (plates, ties, socket, guards) -----------------------------------------------------
GRIPV7_RIM_W = 4.0                # plate rim width around the lightening windows
GRIPV7_RIB_W = 6.0                # rib width between pin bosses / ties
# plate outline = union of rounded rectangles (x0, x1, y0, y1, corner radius), local frame
GRIPV7_OUTLINE_RECTS = (
    (-46.5, 52.0, -34.0, 34.0, 8.0),     # gear zone: 36T tip R28.5 around C + 5 mm, 24T around F
    (-31.0, 31.0, 26.0, 56.0, 6.0),      # servo / pinion zone (ear holes at x = +-23.5)
    (-25.5, 25.5, 48.0, 122.0, 4.0),     # neck + tube socket (socket y 78.4 .. 120.9)
)
GRIPV7_TIE_XY = ((-34.0, 26.0), (44.5, 26.0), (-19.5, 88.0), (19.5, 88.0), (-19.5, 112.0), (19.5, 112.0))
GRIPV7_TIE_COL_OD = 9.0
GRIPV7_TIE_HOLE_D = 3.4
GRIPV7_TIE_BOLT = "M3x50 socket cap + nyloc (nut in a hex pocket in the lower-plate outer face)"
GRIPV7_NUT_POCKET_AF = 5.7        # M3 nut AF 5.5 + 0.2
GRIPV7_NUT_POCKET_DEPTH = 4.2
GRIPV7_CBORE_D = 6.4              # M3 cap head Ø5.5
GRIPV7_CBORE_DEPTH = 3.2
GRIPV7_SADDLE_RIB_T = 4.0
GRIPV7_SADDLE_SHELL_WALL = 4.0
GRIPV7_SADDLE_HALF_W = 24.0       # saddle half width (x)
GRIPV7_SADDLE_SPLIT_GAP = 0.3     # total gap between the two half saddles at the tube equator
GRIPV7_GUARD_T = 1.4              # mesh guard band thickness (1.2 - 1.6)
GRIPV7_GUARD_CLEAR = 1.5          # guard inner face to gear tip circle
GRIPV7_GUARD_Z_MARGIN = 0.5       # guard end to the nearest gear face
GRIPV7_P_STUB_R = 7.0             # link ground-pivot stub (hangs from the upper plate; bending check in calculations)
GRIPV7_P_TAB_HALF_W = 9.0
