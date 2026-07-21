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

# ==========================================================================
# VEX build standard -- the dual push/launch/pull/hold tri-ball mechanism
# ==========================================================================
# This mechanism is a SEPARATE subsystem from the ceiling gripper above. It is
# a single flywheel-intake that gets three behaviours out of one driven wheel:
#   PULL  -- flywheel spins inward slowly, friction draws the tri-ball up into
#            the cradle pocket.
#   HOLD  -- motor stalls/creeps, the ball rests in the pocket against the hood
#            and the back roller (control, no launch).
#   LAUNCH-- flywheel spins UP to speed, the same wheel now throws the ball over
#            the hood lip and across the field.
#   PUSH  -- the whole rigid frame (side plates + front plow) is driven forward,
#            plowing a ball through a contested zone with no launch at all.
# It targets the VEX system: 1/2" high-strength HEX shafts, the 0.5" (12.7 mm)
# hole grid, and #8-32 hardware, so it bolts to VEX C-channel and V5 motors.

# --- VEX hardware ----------------------------------------------------------
VEX_GRID = 12.7           # mm, 0.5" structure hole-grid pitch
VEX_HOLE = 4.9            # mm, structure hole (0.181" clearance for a #8-32 screw)
VEX_HEX_AF = 12.70        # mm, 1/2" high-strength hex shaft, across-flats
VEX_HEX_CLEAR = 0.35      # mm, added to a hex bore across-flats (slip fit on shaft)
VEX_SHAFT_CLEAR = 16.0    # mm, round hole for a hex shaft to pass / a bearing to seat
GEAR_CD = 3 * VEX_GRID    # mm, motor<->flywheel gear centre distance (VEX-legal, 1.5")

# --- Tri-ball game element (VEX Over Under) --------------------------------
TRIBALL_DIA = 178.0       # mm, nominal tri-ball capture diameter (~7 in)

# --- Flywheel intake geometry ---------------------------------------------
FLYWHEEL_DIA = 100.0      # mm, driven flywheel outer diameter
FLYWHEEL_WIDTH = 28.0     # mm, flywheel rim width (ball-contact band)
FLYWHEEL_SPACING = 88.0   # mm, centre-to-centre of the two flywheels on the shaft
FLY_SPOKES = 5            # lightening windows / spokes in the flywheel web
FLY_GROOVES = 2           # circumferential traction-band grooves in the rim
PLATE_THK = 6.0           # mm, intake side-plate thickness
PLATE_GAP = 120.0         # mm, inside distance between the two side plates
HOOD_THK = 3.0            # mm, launch-hood wall thickness
HOOD_RADIUS = 74.0        # mm, launch-hood inner arc radius
ROLLER_DIA = 34.0         # mm, driven back cradle-roller diameter
PLOW_DEG = 22.0           # deg, front plow-blade rake (down-and-forward)
