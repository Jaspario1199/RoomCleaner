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
