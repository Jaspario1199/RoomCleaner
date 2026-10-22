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
# CLAW CAMERA BAY (CAMBAY_*) -- camera enclosure (no IMU, D27) unioned onto the
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

# --- Seeed XIAO ESP32-S3 Sense (Seeed top view + dimension drawing, cad/reference/purchased/;
# VERIFY with calipers).  D27: no IMU on the claw -> no IMU pocket.  The cradle is deliberately
# generous ("lean bigger so we aren't having to reprint").  USB-C end faces bay +X; the board
# mounts LENS-DOWN, USB-C / back of the base board face the cover (Jasper solders to the back).
CAMBAY_XIAO_BOARD_L = 21.0        # base board length (USB-C end to U.FL end)
CAMBAY_XIAO_W = 17.8              # base board width (along the radial direction)
CAMBAY_XIAO_USB_OVERHANG = 1.5    # USB-C receptacle overhangs the board edge by ~1-1.5 mm (take 1.5)
CAMBAY_XIAO_L = CAMBAY_XIAO_BOARD_L + CAMBAY_XIAO_USB_OVERHANG   # 22.5 envelope along bay X
CAMBAY_XIAO_H = 15.0              # whole stack incl. camera module (Seeed drawing)
CAMBAY_XIAO_USB_Z_FROM_TOP = 1.6  # USB-C centre below the stack top (VERIFY)
CAMBAY_CRADLE_L = 23.0            # cradle pocket along bay X (envelope 22.5 + 0.5)
CAMBAY_CRADLE_W = 18.6            # cradle pocket radial (board 17.8 + 0.8)
CAMBAY_INTERNAL_H = 17.0          # board seat -> cover seat (>= 16; whole 15 mm stack would still fit above the seat)
CAMBAY_LENS_FROM_BOARD_END = 5.0  # lens centre from the USB-C end of the base board (VERIFY, read off the photo)
CAMBAY_LENS_DR = 0.0              # lens offset from the board centre, radial outward + (VERIFY)
CAMBAY_LENS_POS_TOL = 4.0         # lens position tolerance the window must absorb (+-4 mm, any direction)
CAMBAY_LENS_BARREL_D = 8.0        # lens barrel diameter (module body ~8.5 square is inside the same window)
CAMBAY_CAM_PROTRUDE = 8.0         # camera module + lens protrusion BELOW the board seat plane (VERIFY; the through-window is deeper than needed)
CAMBAY_LENS_FRONT_Y = 1.9         # lens glass height above the bed plane (box bottom plane)
CAMBAY_LENS_WINDOW_R = 16.4       # lens window radial = 2 x (barrel R 4 + tolerance 4) + 0.4
CAMBAY_LENS_WINDOW_END_WALL = 0.5 # window stops this far short of the USB-end pocket wall (keeps the wall >= 1.2 after the chamfer)
CAMBAY_LENS_CHAMFER = 1.0         # 45 deg chamfer on the window's outer edge
CAMBAY_USB_PLUG_W = 13.0          # USB-C plug overmould the notch must pass (>= 13)
CAMBAY_USB_PLUG_H = 8.0           # (>= 8); the notch is open at the top and closed by the cover
CAMBAY_USB_PLAY = 1.0             # extra notch width per side around the plug (+-1.0 mm lateral play)
CAMBAY_USB_SILL_ABOVE_SEAT = 0.4  # notch sill just above the board seat (plug centre is ~5.4 above the seat nominal; 1 mm vertical play kept)
CAMBAY_FENCE_H = 9.0              # neck-side fence height above the seat (gap |x| < 4 for the wires)
CAMBAY_PEG_STOP_ABOVE_SEAT = 11.0 # cover hold-down pegs end this far above the seat (stack top is ~7 above it)
CAMBAY_LOCATOR_RIB_T = 0.4        # soft locating ribs on the long cradle walls (board 17.8 + 2 x 0.4 = 18.6 -> snug)
CAMBAY_LOCATOR_RIB_W = 1.6        # rib width along bay X
CAMBAY_ANT_L = 30.0               # flexible U.FL antenna length (VERIFY)
CAMBAY_ANT_W = 10.0               # flexible U.FL antenna width (VERIFY)

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

# --- purchased bearings (7x14x5 = type 687; a 607 is 7x19x6 and does NOT fit) and steel axle pins --------------------------------
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
GRIPV7_RACE_BOSS_D = 9.7          # plate ring facing the stationary inner race: kept as a FULL ring (it limits the axial float of the gear
                                  # stack, so it is NOT removed), wall (9.7 - 7.05)/2 = 1.325 >= MIN_WALL (1.25 mm = raster-check disc).
                                  # The ring only faces the 687 inner race / recessed shield with 0.15 mm axial clearance and is never in
                                  # contact with a rotating part, so an inner-race land smaller than 9.7 is harmless (VERIFY on hardware)
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
GRIPV7_TUBE_LEN = 254.8           # D28: cut 50 mm (v6/v7 original 304.8); lower end y stays at 786.39 in the world frame
GRIPV7_TUBE_LEN_V6 = 304.8        # original (v6) tube length; everything above the tube moved down by LEN_V6 - LEN (D28)
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
GRIPV7_SERVO_INSERT_D = 3.3       # M2.5 heat-set insert melt-in hole (was 3.6: wall to the servo cut-out 1.10 -> 1.25; VERIFY vs the real insert)
GRIPV7_SERVO_INSERT_DEPTH = 4.7     # blind, from the plate top (6 mm plate): floor 1.3 mm (was 5.0 / 1.0)
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
GRIPV7_PINION_HUB_D = 21.0        # pinion hub extension above the teeth (carries the horn); was 20.0: wall to the R8 pilots 1.15 -> 1.65
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
GRIPV7_LUG_T = 9.0                # crank-lug / link tongue thickness (centred in the sync layer)
GRIPV7_TONGUE_GAP = 0.5           # printed faces that rotate against each other: 0.5 mm washer gap
GRIPV7_EAR_T = 4.5                # jaw clevis ear thickness (2 x 4.5 + 2 x 0.5 + 9 = 19 mm jaw)
# frame pivot stub bottom face = link tongue top + gap (stubs hang from the upper plate)
GRIPV7_P_STUB_Z0 = (GRIPV7_L2_Z0 + GRIPV7_L2_Z1) / 2 + GRIPV7_LUG_T / 2 + GRIPV7_TONGUE_GAP     # 32.0

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

# --- repair round 1 (minimum wall, axial relief between counter-rotating faces) ----------------------
GRIPV7_MIN_WALL = 1.2             # mm, minimum printed wall / ligament anywhere (3 perimeters of 0.4)
GRIPV7_AXIAL_RELIEF = 0.30        # mm, annular relief cut into the 36T-layer top face (rim, teeth, spoke ends): axial gap to the
                                  # follower bottom (which sits at the same z as the 36T top).  36T / pinion mesh face = 16 - 0.30 = 15.7
GRIPV7_RELIEF_R_MARGIN = 0.30     # mm, relief annulus starts this far inside the follower's nearest point (CD_SYNC - tip radius 24T)
GRIPV7_SADDLE_NOTCH_Z = 30.0      # mm, top of the notch cut in the upper saddle around each tie column (ligament to the tube bore >= 1.2 above it)
GRIPV7_SADDLE_NOTCH_X0 = 12.0     # mm, notch starts at |x| = 12 (inside the tube bore, so only shell/rib material is removed)
GRIPV7_SADDLE_NOTCH_Y_PAD = 0.3   # mm, notch half-length in y beyond the column clearance radius
GRIPV7_JAW_BOSS_R_A = 9.8         # mm, jaw boss radius at the crank pin A (was 9.5; B keeps 9.5): wall to the crank slot = 9.8 - (8.0 + 0.5) = 1.3
GRIPV7_JAW_CRANK_SLOT_MARGIN = 0.5  # mm, radial clearance tongue end -> slot wall at A (was 0.8: crescent wall 0.7 mm)


# =============================================================================
# GRIPPER v6r -- Jasper's v6 gears modified for the 2:1 gearbox (10/21/2026).  Master values for
# cad/parts/gripper_v6r_gears.py.  The solids are TAKEN from solidworks/gripper_v6_2026-10-20 (read-only STEP);
# only the tooth count of the big gear, the crank length and one axial relief are changed.
# Frame: part frame = gear axis on the z axis, z = 0 at the bottom of the gear stack (his world z 1080.48987).
# Placement frame = the v7 LOCAL frame (x lateral, tube axis x = 0, gear-axes line y = 0), same as v6 world - origin.
# =============================================================================
GRIPV6R_SRC_STEP = "solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP"
GRIPV6R_SRC_PINION = "Simple_18T_Pinionvlast"
GRIPV6R_SRC_COMPOUND = "06_compound_54T_24T"
GRIPV6R_SRC_FOLLOWER = "24T_Follower"
# his world coordinates (measured from his solids; the module re-measures and asserts to GRIPV6R_SRC_TOL)
GRIPV6R_SRC_Z0 = 1080.489871025   # mm, bottom of his gear stack (plane location in his STEP; layers are exactly 16 + 20 above it)
GRIPV6R_SRC_C_XY = (969.8474967, 707.9863920)      # compound axis
GRIPV6R_SRC_F_XY = (933.8474967, 707.9863920)      # follower axis
GRIPV6R_SRC_S_XY = (961.8474967, 761.3905117)      # pinion / servo axis
GRIPV6R_SRC_TOL = 0.005           # mm
GRIPV6R_SRC_ARM_R = 75.0          # his lug / fork pivot radius
GRIPV6R_SRC_ARM_DEG_C = -31.2259097    # his compound lug angle (world, CCW from +x)
GRIPV6R_SRC_ARM_DEG_F = 209.8828815    # his follower lug angle
# layers (part frame z)
GRIPV6R_L1_Z0, GRIPV6R_L1_Z1 = 0.0, 16.0      # pinion + big gear layer (face 16)
GRIPV6R_L2_Z0, GRIPV6R_L2_Z1 = 16.0, 36.0     # 24T pair layer (face 20) incl. the lug band 16 .. 26
GRIPV6R_LUG_Z1 = 26.0                         # top of the lug / fork band (10 mm thick)

# --- tooth form, measured from his 54T (module 1.5, 20 deg involute, 1.0 m / 1.25 m, R0.4 root blend,
#     0.100 mm thinning at the pitch circle); the v3/v6 generator reproduces his 54T section to 1e-5 mm ---------
GRIPV6R_MODULE = 1.5
GRIPV6R_PRESSURE_ANGLE = 20.0
GRIPV6R_ADDENDUM_K = 1.0          # x module
GRIPV6R_DEDENDUM_K = 1.25         # x module
GRIPV6R_ROOT_FILLET_R = 0.40
GRIPV6R_TOOTH_THIN = 0.10         # mm per gear at the pitch circle (as his; v6 had NO centre-distance allowance)
GRIPV6R_Z_PINION = 18
GRIPV6R_Z_MAIN_V6 = 54            # his big gear
GRIPV6R_Z_MAIN = GRIPV7_Z_MAIN    # 36 (2:1)
GRIPV6R_Z_SYNC = 24
GRIPV6R_CD_MAIN = GRIPV7_CD_MAIN  # 40.80 (nominal 40.5 + 0.3)
GRIPV6R_CD_SYNC = GRIPV7_CD_SYNC  # 36.30 (nominal 36.0 + 0.3)
GRIPV6R_C_XY = (GRIPV6R_CD_SYNC / 2.0, 0.0)       # placement frame: compound axis
GRIPV6R_F_XY = (-GRIPV6R_CD_SYNC / 2.0, 0.0)      # follower axis
GRIPV6R_S_X = GRIPV7_SERVO_X_OFF                  # pinion / servo shaft x (v6 and v7: 10 mm from the tube axis)
GRIPV6R_S_XY = (GRIPV6R_S_X, (GRIPV6R_CD_MAIN ** 2 - (GRIPV6R_S_X - GRIPV6R_C_XY[0]) ** 2) ** 0.5)

# --- big gear web (inside the new root radius his hub, pocket, lips and web are kept) ------------------------------
GRIPV6R_CORE_R = 8.5              # mm, his solid is kept inside this radius (pocket wall R7.0375 + 1.46)
GRIPV6R_POCKET_R = 7.0375         # his Ø14.075 pocket
GRIPV6R_LIGHT_MIN_LIG = 2.0       # mm, minimum ligament: hole to pocket wall, hole to root circle, hole to hole
GRIPV6R_LIGHT_D = 12.0            # mm, his hole Ø is kept
GRIPV6R_LIGHT_N = 7               # largest count of Ø12 holes that keeps every ligament >= 2.0 (8 do not fit)
GRIPV6R_LIGHT_R = 16.7            # mm, hole circle radius (min ligament 2.43: pocket 3.66, root 2.43, hole-hole 2.49)
GRIPV6R_LIGHT_PHASE_DEG = 90.0    # deg, angle of the first hole in the part frame (any: pattern is 7-fold)

# --- the ONLY functional change besides tooth count and crank length (flag to Jasper) --------------------------------
GRIPV6R_RELIEF_DEPTH = GRIPV7_AXIAL_RELIEF        # 0.30 mm
GRIPV6R_RELIEF_R_MARGIN = GRIPV7_RELIEF_R_MARGIN  # 0.30 mm inside the follower's nearest point
GRIPV6R_RELIEF_R_IN = GRIPV6R_CD_SYNC - GRIPV6R_MODULE * (GRIPV6R_Z_SYNC + 2) / 2.0 - GRIPV6R_RELIEF_R_MARGIN   # 16.5
# --- crank --------------------------------------------------------------------------------------------------------
GRIPV6R_ARM_R = GRIPV7_CRANK_R                    # 53.0 (his 75)
GRIPV6R_ARM_SHORTEN = GRIPV6R_SRC_ARM_R - GRIPV6R_ARM_R      # 22.0
GRIPV6R_ARM_CUT_X = 30.0          # mm along the arm from the axis: the constant-section slab removed starts here
GRIPV6R_ARM_DEG_C = GRIPV7_THETA_CLOSED           # compound lug angle at the v7 closed pose (CCW from +x, v7 convention)
GRIPV6R_ARM_DEG_F = 180.0 - GRIPV7_THETA_CLOSED   # follower lug: mirror image about the tube plane x = 0
GRIPV6R_SWEEP_DEG = GRIPV7_SWEEP_DEG              # 76.5 deg closed -> open (compound), follower opposite, pinion x -2
GRIPV6R_SWEEP_PINION_RATIO = GRIPV6R_Z_MAIN / GRIPV6R_Z_PINION   # 2.0

# --- clearances (Jasper addendum 10/21) --------------------------------------------------------------------------
GRIPV6R_BACKLASH_MIN = 0.20       # mm circumferential at the pitch circle, every pose of the +-30 deg sweep and the stroke
GRIPV6R_TIP_ROOT_MIN = 0.25 * GRIPV6R_MODULE      # 0.375 mm
GRIPV6R_AXIAL_GAP_MIN = 0.30      # mm between counter-rotating faces / lug faces and the gear faces they pass
GRIPV6R_PINION_BOSS_GAP = 0.30    # mm: servo-boss plane sits this far above the pinion top face (v6: flush)
GRIPV6R_SWEEP_CLEAR_MIN = 1.0     # mm lug / fork to the other gear, the other lug, pins and bearings over the stroke
GRIPV6R_RADIAL_36T_FOLLOWER_MIN = 1.0   # mm 36T tip to follower hub / body in the 36T layer
GRIPV6R_PIVOT_HOLE_D = 3.5        # his compound pivot hole (M3 clearance); kept.  His follower pivot hole is Ø8.33 (kept).
GRIPV6R_PIVOT_HOLE_D_FOR_SHOULDER_D4 = 4.2   # NOTE only: Ø4 shoulder screws would need Ø4.2 holes (not applied)
GRIPV6R_PIN_D = 7.0               # housing pin on the compound / follower axes (his integral Ø7 pins)
GRIPV6R_BRG_OD = 14.0             # 687 bearings in his pockets
GRIPV6R_DENSITY_PETG = 1.27       # g/cm3 (cad/materials.py)


# =============================================================================
# GRIPPER 1021 -- Jasper's final gripper (cad/reference/gripper_1021) : HANDS (GRIP1021_*)
# Master values for cad/parts/gripper1021_hands.py.  Source of truth: cad/GRIPPER_1021_SPEC.md.
# Units mm / deg.  World frame of Jasper's assembly: tube axis = line x = GRIP1021_AXIS_X,
# z = GRIP1021_AXIS_Z, along y; +y up (toward the housing), +z toward the servo.
# =============================================================================
# --- four-bar (lead analysis, cad/reference/gripper_1021/fourbar.py) -----------------------------------------------
GRIP1021_AXIS_X = 951.8475            # tube axis x (the two grip faces meet on this plane at the closed pose)
GRIP1021_AXIS_Z = 1103.99             # tube axis z
GRIP1021_TUBE_LEN_CAD = 304.8         # tube length in Jasper's 1021 assembly STEP (12 in)
GRIP1021_TUBE_LEN = 10.48 * 25.4      # D36 (Jasper 10/22): tube as built, 266.19 mm; the head sits
                                      # GRIP1021_TUBE_LEN_CAD - GRIP1021_TUBE_LEN = 38.61 mm higher than in the STEP
GRIP1021_O2 = (969.997, 721.413)      # compound (right crank) axis
GRIP1021_O4 = (963.847, 685.391)      # right arm pivot (gear-housing pin)
GRIP1021_CRANK_R = 53.0               # crank pin A at this radius from O2
GRIP1021_ROCKER_R = 50.0              # arm: O4 -> tip hole B
GRIP1021_COUPLER = 34.67              # the HAND: A -> B
GRIP1021_THETA_CLOSED_DEG = -62.0     # compound crank angle, grip faces meet
GRIP1021_THETA_FILE_DEG = -52.1       # Jasper's file pose
GRIP1021_THETA_OPEN_DEG = -5.0        # max open
GRIP1021_FOLLOWER_MESH_DEG = -6.0     # follower is rotated this much (about its axis) into mesh, then moves mirror-wise
GRIP1021_SWEEP_DEG = (-5.0, -10.0, -20.0, -30.0, -40.0, -50.0, -60.0, -62.0)   # required sweep angles

# --- stacking in z (print bed = z 1090, the whole hand stands on it) -------------------------------------------------
GRIP1021_Z_FILE_OFFSET = -0.000129     # Jasper's STEP files carry this z offset (his crank boss underside is 1098.989871, not 1098.99); applied to every hand z so contact faces coincide exactly
GRIP1021_Z_BED = 1090.0
GRIP1021_Z_PLATE_TOP = 1098.0         # link plate z 1090..1098
GRIP1021_Z_PALM_TOP = 1118.0          # palm and finger, full width z 1090..1118
GRIP1021_Z_BOSS_A_RIGHT = 1098.99     # A boss top = underside of the compound crank boss
GRIP1021_Z_BOSS_A_LEFT = 1099.99      # follower crank sits 1 mm higher (the only non-mirror difference)
GRIP1021_Z_BOSS_B = 1101.49           # B boss top = underside of the arm (both hands)

# --- joints -----------------------------------------------------------------------------------------------------------
GRIP1021_PLATE_R_A = 8.0              # link plate hull: circle at A
GRIP1021_PLATE_R_B = 8.5              # circle at B
GRIP1021_BOSS_D = 8.0                 # washer-face boss diameter on both joints
GRIP1021_PIN_HOLE_D = 3.2             # M3 screw used as a pin
GRIP1021_NUT_AF = 5.7                 # M3 nyloc pocket, across flats (vertices point sideways, across the link)
GRIP1021_NUT_DEPTH = 4.2              # pocket depth from the bed face, coaxial with the pin
GRIP1021_SCREW_LEN = 20.0             # M3 x 20 button head from the top (NOTE only, not modelled)

# --- palm and finger (below the cut line) -------------------------------------------------------------------------------
GRIP1021_PALM_CUT_Y = 628.4           # = B_y(closed) - 12.5 ; nothing above the plate for y > this except the two bosses
GRIP1021_PALM_B_CLEAR = 12.5          # B_y - cut line (spec); checked against the solved B in the part
GRIP1021_TIP_Y = 575.0                # fingertip (lowest point) at the closed pose
GRIP1021_FINGER_T = 9.0               # finger thickness (x 951.85 .. 960.85)
GRIP1021_TIP_ROUND_R = 3.0            # R3 round on the grip-face bottom edge
GRIP1021_TIP_CHAMFER_DEG = 30.0       # outer bottom edge: 30 deg off the tip plane (a shallow scraping wedge)
GRIP1021_RIDGE_DEPTH = 0.8            # grip ridges cut into the face (never proud: the faces still meet)
GRIP1021_RIDGE_PITCH = 3.0
GRIP1021_RIDGE_LAND = 0.8             # flat crest between grooves (groove width at the face = pitch - land)
GRIP1021_RIDGE_Y0 = 580.0             # first groove starts here (above the R3 round, which ends at TIP_Y + 3)
GRIP1021_RIDGE_N = 16
GRIP1021_WALL_MIN = 3.0               # lightening windows keep walls >= this (spec)
GRIP1021_MASS_MAX_G = 22.0            # spec target, solid PETG
GRIP1021_PETG_G_CM3 = 1.27            # cad/materials.py
GRIP1021_GUSSET_DROP = 22.0           # strut leaves the finger outer face this far below the cut line (about 45 deg to the apex)
GRIP1021_WINDOW_FILLET_R = 1.5        # corner round of every lightening window
GRIP1021_WALL_FROM_RIDGE_ROOT = False # False: walls are measured from the nominal grip face (grooves excluded, root wall = WALL_MIN - RIDGE_DEPTH); True: from the groove root
GRIP1021_PALM_RIGHT_DX = -3.0         # palm top-right corner (strut apex) relative to B_x
GRIP1021_WEB_FOOT_W = 10.0            # web foot (where the link plate lands on the palm top bar), width along x


# =============================================================================
# CAMERA BAY ON JASPER'S 1021 ELECTRICAL HOUSING (CAMBAY1021_*)
# Box-dependent values for cad/parts/gripper1021_housing_cambay.py.  Everything that is NOT box dependent (cradle,
# lens window, USB-C notch, fence, locating ribs, cover pegs, insert columns, wall rules, bay frame placement) is
# read from the unchanged CAMBAY_* block, so the studied v6 bay / D28 camera view still applies.
# Bay frame is the same as v6: origin on the tube axis in the box bottom plane (world y = 1091.1905), axes parallel to
# the world axes, +y up, bay on -Z (CAMBAY_SIDE), optical axis at r = CAMBAY_CAM_R = 90 mm pointing -y.
# Housing: cad/reference/gripper_1021/parts/05_Gripper_Electric_Housing_Base_2__NAUO5.step, MEASURED (probes + faces):
# =============================================================================
CAMBAY1021_BAY_ORIGIN_WORLD = (951.8475, 1091.1905, 1103.9899)   # tube axis @ box bottom plane (his file z carries -0.000129 mm)
CAMBAY1021_BOX_FLANGE_HALF = 50.0     # 100 x 100 base, R20 corners
CAMBAY1021_BOX_FLANGE_T = 5.0         # flat flange / pocket floor height above the bottom plane
CAMBAY1021_BOX_UPPER_HALF = 45.0      # 90 x 90 box, 5 mm walls, R10 corners
CAMBAY1021_BOX_BLEND_R = 75.0         # concave R75 blend, flange -> upper wall
CAMBAY1021_BOX_BLEND_TOP_Y = 31.926   # = FLANGE_T + sqrt(R^2 - (R - 5)^2): blend ends tangent to the vertical wall (world 1123.12)
CAMBAY1021_BOX_POCKET_HALF = 40.0     # box interior half-width (80 mm pocket, R10 corners)
CAMBAY1021_BOX_POCKET_FLOOR_Y = 5.0
CAMBAY1021_BOX_LID_SEAT_Y = 50.0      # lid seat ledge (world 1141.19)
CAMBAY1021_BOX_TOP_Y = 55.0           # rim (world 1146.19)
CAMBAY1021_TUBE_HOLE_D = 30.0
CAMBAY1021_CORNER_HOLE_D = 2.0        # four cable-line holes through the corner walls, on the diagonals
CAMBAY1021_CORNER_HOLE_ELEV_DEG = 13.764   # rise toward the outside
CAMBAY1021_CORNER_HOLE_EXIT_XZ = 43.22     # outer mouth centre |x| = |z| (box frame)
CAMBAY1021_CORNER_HOLE_EXIT_Y = 9.95       # ... at this height above the bottom plane (world 1101.14)
CAMBAY1021_CORNER_HOLE_INNER_XZ = 37.07    # where the axis leaves the pocket corner (R10 about (30, 30))
CAMBAY1021_CORNER_HOLE_INNER_Y = 7.82
CAMBAY1021_CORNER_HOLE_KEEPOUT = 5.0       # required clear distance from those holes

# --- bay geometry that depends on the wall (re-derived for the 5 mm wall, r 40..45 upper, r 45..50 over the blend) -----
CAMBAY1021_BODY_R_IN = 42.5           # bay solid starts INSIDE the box wall (pocket 40 < 42.5 < wall outer 45): nothing enters the pocket
CAMBAY1021_COVER_WALL_GAP = 0.8       # cover inner edge off the box wall
CAMBAY1021_RIB_P0 = (12.9, 76.0)      # root gusset ribs: start on the neck side wall (x, r) ...
CAMBAY1021_RIB_P1 = (30.0, 44.5)      # ... end inside the box wall (r 44.5 < wall 46..50), x <= 30 (flat part of the wall)
CAMBAY1021_NECK_TIE_RC = 70.4         # wire-tie slots straddle this radius (unchanged from v6: 10.3 mm inboard of the cradle)
CAMBAY1021_WIN_R_OUT = 66.0           # wire window funnel ends here on the bay side
CAMBAY1021_WIN_BAY_FLARE = 6.0        # funnel growth per side at r_out
CAMBAY1021_WIN_ROOF_CH = 2.5          # 45 deg roof-corner chamfers (printable bridge)
CAMBAY1021_COVER_VENT_X = (-6.0, 0.0, 6.0)   # three 2 x 5 slots in the cover next to the box wall (as v6)
CAMBAY1021_COVER_VENT_R = (2.0, 7.0)         # ... from COVER_R0 + 2 to COVER_R0 + 7


# =============================================================================
# THREE-CABLE HOLES ON THE 1021 ELECTRICAL HOUSING (CAMBAY1021_TRI_*)   cad/GRIPPER_1021_SPEC.md section 5
# A second hole pattern, for the three-station test (docs/THREE_STATION_MODE_SPEC.md); the four corner holes stay.
# Box frame of cad/parts/gripper1021_housing_cambay.py: origin on the tube axis in the box bottom plane, +y up.
# Body frame (verification/claw_body_frame.json, re-derived for the 1021 box): origin on the tube axis at the corner-hole
# inner-mouth height, +x = box x, +y = -box z, +z up.  Each hole axis is horizontal and RADIAL (it passes through the tube axis),
# so the body azimuth fixes the whole hole: outer mouth where that ray meets the outer wall plane (|x| or |z| =
# CAMBAY1021_BOX_UPPER_HALF), inner mouth where it meets the pocket wall plane (CAMBAY1021_BOX_POCKET_HALF).
# =============================================================================
CAMBAY1021_TRI_IDS = ("C", "A", "B")                 # station served by each hole (order of every tuple below)
CAMBAY1021_TRI_AZ_BODY_DEG = (90.0, 210.0, 330.0)    # body-frame azimuth of each hole axis (ccw from body +x); C on the bay side
CAMBAY1021_TRI_Y = 42.0               # hole axis height above the box bottom plane (all three equal: level attachment plane)
CAMBAY1021_TRI_HOLE_D = 2.0           # bore diameter (circle of the teardrop)
CAMBAY1021_TRI_TIP_HALF_DEG = 45.0    # teardrop tip: flanks are this far off the vertical (tip points +y, prints without support)
CAMBAY1021_TRI_CHAMFER = 0.5          # 0.5 x 45 deg chamfer at the outer mouth (no chafe where the line turns up)
CAMBAY1021_TRI_LABEL_H = 4.0          # deboss letter height (glyph bounding box)
CAMBAY1021_TRI_LABEL_DEPTH = 0.4      # deboss depth into the outer wall
CAMBAY1021_TRI_LABEL_ABOVE = 5.0      # label centre this far above the mouth centre (on the outer wall plane)
CAMBAY1021_TRI_KEEPOUT = 5.0          # required clear distance to every other feature of the housing
CAMBAY1021_TRI_CONFINE = 3.0          # the part may differ from the 1021 housing only within this distance of the holes / labels
CAMBAY1021_TRI_CORNER_R = 10.0        # box outer and pocket corner radius (measured on Jasper's housing; flat wall half = HALF - R)
CAMBAY1021_TRI_LID_RECESS_HALF = 42.5    # lid-seat recess half width (measured: faces at |x|, |z| = 42.5, y 50 .. 55)
CAMBAY1021_TRI_BODY_ORIGIN_Y = CAMBAY1021_CORNER_HOLE_INNER_Y   # body-frame origin height in the box frame (corner-hole inner mouth, 7.82)
# Station anchor priors, room frame (x east, y north, z up), metres: docs/THREE_STATION_MODE_SPEC.md (C, A, B in IDS order).
CAMBAY1021_TRI_ANCHORS_ROOM_M = ((1.6764, 2.6932, 2.5932), (0.05, 0.05, 2.5932), (3.3028, 0.05, 2.5932))
CAMBAY1021_TRI_YAW_RANGE_DEG = 15.0   # claw yaw range of the cable-line analysis (+-)


# =============================================================================
# ENCODER 1021 -- AS5600 magnet cap + encoder casing for the 10/21 wall assembly (ENC1021_*)   cad/ENCODER_1021_SPEC.md
# Master values for cad/parts/encoder1021.py (both parts).  Units mm.  Frame: the v3 STATION frame = the slip-in mount's own
# frame: origin on the motor shaft axis in the slip-in motor-plate face, +y along the shaft toward the spool, +z up, +x out of
# the wall into the room.  cad/reference/station_1021/*.step are that frame shifted up by ENC1021_REF_SHIFT_Z.
# Every level along y (magnet face, chip face, PCB faces, frame front) is DERIVED in cad/parts/encoder1021.py from the values
# below, so one edit here regenerates both parts.
# =============================================================================
# --- purchased parts: NOMINAL until Jasper measures them (spec section 6) ----------------------------------------------------
ENC1021_MAGNET_D = 6.0                # diametric magnet shipped with the board
ENC1021_MAGNET_T = 2.5
ENC1021_PCB_SIZE = 23.0               # UMLIFE AS5600 module, square
ENC1021_PCB_THICK = 1.6
ENC1021_CHIP_H = 1.45                 # SOIC-8 height above the PCB front face (the face toward the magnet)
ENC1021_CHIP_OFFSET = (0.0, 0.0)      # chip centre minus board centre, board (x, z) = station (x, z); expected centred
ENC1021_AIR_GAP = 1.5                 # magnet face to chip face (AS5600 range about 0.5 - 3 mm)
ENC1021_CHIP_BODY = (6.0, 4.0)        # SOIC-8 footprint incl. leads, station (x, z): used only for the display / clearance body
# optional locating pins in the board's four corner holes: OFF until the hole pitch is measured
ENC1021_PINS_ON = False
ENC1021_PIN_PITCH = 19.0              # corner-hole centre spacing (placeholder, NOT measured)
ENC1021_PIN_D = 2.0
ENC1021_PIN_LEN = 1.2                 # protrusion into the board, capped at PCB_THICK - 0.3 in the builder

# --- station interfaces, re-measured from the STEPs shifted by (0, 0, -2.64) -------------------------------------------------
# The extraction carries a common placement residual (+0.004243, +0.001645, +0.003854) mm in (x, y, z): measured as the spool
# centre (x, z) and the spool outer face (y = 26.001645); the divot floor, holes and shaft end all sit at the same offsets.
# The values below are the exact design values with it removed.
ENC1021_REF_SHIFT_Z = 2.64
ENC1021_REF_RESIDUAL = (0.004243, 0.001645, 0.003854)
ENC1021_SPOOL_FACE_Y = 26.0           # spool outer flange face (flange y 23 - 26, Ø36), plain disc with the bore
ENC1021_SPOOL_FLANGE_D = 36.0
ENC1021_SHAFT_END_Y = 22.0            # motor shaft end (Ø5 with a D-flat at z = +2.0)
ENC1021_BORE_D = 5.30                 # spool bore, through
ENC1021_BORE_FLAT_X = 2.15            # D-flat of the bore at x = +2.15 (material on the +x side)
ENC1021_PLATE_FACE_X = -21.15         # back-plate face the divot is in, normal +x (spec rounds to -21.1)
ENC1021_DIVOT_FLOOR_X = -22.15        # divot floor, 1.0 deep (spec rounds to -22.1)
ENC1021_DIVOT_YZ = (45.0, 0.0)        # divot centre (y, z)
ENC1021_DIVOT_RIM = 24.0              # opening at the plate face; plan corners R1.0
ENC1021_DIVOT_WALL_R = 1.0            # the divot wall is a QUARTER-ROUND R1.0 (floor 22 x 22, sharp corners), not a straight wall
ENC1021_DIVOT_HOLE_D = 3.45           # measured Ø3.45 (spec: Ø3.46), 4.0 deep below the floor
ENC1021_DIVOT_HOLE_DEPTH = 4.0
ENC1021_DIVOT_HOLE_PITCH = 9.5        # 9.5 mm square about the divot centre

# --- magnet cap -----------------------------------------------------------------------------------------------------------------
ENC1021_CAP_HEAD_D = 14.0
ENC1021_CAP_HEAD_T = 3.3              # head against the spool face; grows if a thicker magnet needs it (floor >= CAP_FLOOR_MIN)
ENC1021_CAP_FLOOR_MIN = 0.75          # solid material under the magnet
ENC1021_CAP_HEAD_CHAMFER = 0.3        # 45 deg on the head's outer top edge (elephant-foot relief, magnet-face side on the bed)
ENC1021_CAP_POCKET_CLEAR_D = 0.2      # pocket Ø = MAGNET_D + this
ENC1021_CAP_POCKET_EXTRA_DEPTH = 0.05 # pocket depth = MAGNET_T + this (CA glue film under the magnet)
ENC1021_CAP_PEG_D = 5.10              # D-peg: Ø5.10 round part ...
ENC1021_CAP_PEG_FLAT_X = 2.05         # ... with its flat at x = +2.05 (0.10 inside the bore flat)
ENC1021_CAP_PEG_LEN = 3.4             # peg end at SPOOL_FACE_Y - 3.4 = 22.6, 0.6 mm clear of the shaft end
ENC1021_CAP_RIB_N = 3                 # axial crush ribs, equally spaced, one opposite the flat
ENC1021_CAP_RIB_H = 0.15              # rib height above the peg surface (0.05 mm radial crush into the Ø5.30 bore)
ENC1021_CAP_RIB_W_BASE = 0.8
ENC1021_CAP_RIB_W_TIP = 0.3
ENC1021_CAP_LEAD_IN = 0.5             # 45 deg lead-in on the peg end
ENC1021_CAP_NOTCH = (3.0, 2.0, 0.8)   # pry notch in the head underside at +z: tangential width, radial depth, axial height

# --- encoder casing -------------------------------------------------------------------------------------------------------------
ENC1021_PCB_CLEAR = 0.2               # board pocket clearance per side (pocket 23.4 for the 23.0 board)
ENC1021_WALL = 2.0                    # frame wall around the pocket (outer 27.4)
ENC1021_TAB = 3.0                     # corner front stops, 3 x 3 in plan, at the pocket corners
ENC1021_TAB_SETBACK = 0.2             # front face of the frame and tabs this far BEHIND the chip face (chip sticks out 0.2)
ENC1021_FLEX_WALL_T = 1.2             # the +-z walls are thinned to this between the corner blocks: they flex as the snap hooks
ENC1021_HOOK_W = 8.0                  # snap-hook lip length along x, centred
ENC1021_HOOK_OVERLAP = 0.4            # lip overlap over the PCB back face edge (0.6 beyond the wall's inner face)
ENC1021_HOOK_GAP = 0.1                # catch face this far behind the PCB back face
ENC1021_HOOK_LIP_Y = 1.0              # lip height along y (45 deg lead-in ramp)
ENC1021_FOOT_SIZE = 23.6              # foot plan: 0.2 per side inside the 24.0 divot rim
ENC1021_FOOT_CORNER_R = 1.2           # >= divot plan corner R1.0 + margin
ENC1021_FOOT_H = 4.0                  # divot floor up to the +x face: 1.0 keyed + 3.0 proud
ENC1021_FOOT_KEY_R = 1.0              # bottom-edge round: follows the divot quarter-round so the whole 1.0 depth engages
ENC1021_FOOT_HOLE_D = 3.4             # clearance holes at the divot holes (pass M2.5 and M3), teardrop top for printing
ENC1021_SCREW_HEAD_D = 6.0            # M3 pan head; the region above each hole is kept open to this + tool clearance
ENC1021_TOOL_CLEAR = 0.5
ENC1021_BRIDGE_X0 = -20.9             # bridge / filler -x end: 0.25 mm above the plate face
ENC1021_BRIDGE_TOP_Y = 36.2           # bridge top; must stay >= screw-head radius + tool clearance from the nearest hole row (y 40.25)
ENC1021_BRIDGE_HALF_Z = 13.7          # bridge width = frame width
ENC1021_TIE_SLOT = (3.0, 1.6, 6.2)    # strain-relief zip-tie slots through the bridge: x length, z width, z offset (+-)
ENC1021_TIE_SLOT_X = -16.0            # ... centred at this x
ENC1021_PETG_G_CM3 = 1.27             # cad/materials.py
ENC1021_PETG_E_MPA = 2100.0           # cad/materials.py (1 N stiffness hand calculation)
ENC1021_STIFF_LOAD_N = 1.0            # acceptance: this push on the frame ...
ENC1021_STIFF_LIMIT_MM = 0.1          # ... moves the chip less than this
ENC1021_OVERHANG_DEG = 45.0           # printability limit (a face is flagged above this + ENC1021_OVERHANG_TOL_DEG)
ENC1021_OVERHANG_TOL_DEG = 0.5
