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
# A BELT ACCELERATOR ("belt railgun"). The tri-ball runs down a barrel gripped
# between two motor-driven conveyor belts (top + bottom traction belts). Like a
# railgun it accelerates the ball ALONG a barrel -- but the "rails" are belts,
# and belt SURFACE SPEED sets the exit speed. One mechanism, four behaviours:
#   PULL  -- belts run inward (surfaces toward the breach): the ball is drawn in.
#   HOLD  -- belts stopped: the ball is pinched between them (compression grip).
#   LAUNCH-- belts run outward, fast: the ball is spun up to belt speed and fired
#            out the muzzle.
#   PUSH  -- belts off: drive the robot forward and the front plow shoves the
#            ball through a contested zone (no launch at all).
# It targets the VEX system: 1/2" high-strength HEX shafts, the 0.5" (12.7 mm)
# hole grid, and #8-32 hardware, so it bolts to VEX C-channel and V5 motors.
#
# DESIGN BASIS (first-principles sizing -- edit these and re-export):
#   Exit speed (no slip):   v_exit ~= v_belt = (RPM / 60) * pi * PULLEY_PITCH_DIA
#   Grip / no-slip:         mu * N  >=  m_ball * a     (N grows with BALL_COMPRESSION)
#   Channel gap:            BELT_GAP = TRIBALL_DIA - 2 * BALL_COMPRESSION
#   Barrel length:          BARREL_LEN = accel distance for the ball to reach v_belt
# so choose PULLEY_PITCH_DIA + motor RPM for v_exit, BALL_COMPRESSION for grip,
# and BARREL_LEN long enough that the ball leaves at (near) belt speed.

# --- VEX hardware ----------------------------------------------------------
VEX_GRID = 12.7           # mm, 0.5" structure hole-grid pitch
VEX_HOLE = 4.9            # mm, structure hole (0.181" clearance for a #8-32 screw)
VEX_HEX_AF = 12.70        # mm, 1/2" high-strength hex shaft, across-flats
VEX_HEX_CLEAR = 0.35      # mm, added to a hex bore across-flats (slip fit on shaft)
VEX_SHAFT_CLEAR = 16.0    # mm, round hole for a hex shaft to pass / a bearing to seat
GEAR_CD = 3 * VEX_GRID    # mm, motor<->pulley gear centre distance (VEX-legal, 1.5")

# --- Tri-ball game element (VEX Over Under) --------------------------------
TRIBALL_DIA = 178.0       # mm, nominal tri-ball capture diameter (~7 in)

# --- Belt accelerator geometry --------------------------------------------
PLATE_THK = 6.0           # mm, side-plate thickness
BALL_COMPRESSION = 10.0   # mm, how far each belt squeezes into the ball (grip)
BELT_GAP = TRIBALL_DIA - 2 * BALL_COMPRESSION   # mm, inner-run separation (158)
BELT_WIDTH = 150.0        # mm, belt width -- the ball-contact band (along the shaft)
BELT_THK = 4.0            # mm, belt thickness incl. tread
BARREL_LEN = 150.0        # mm, pulley centre-to-centre along the barrel (accel dist)
PULLEY_PITCH_DIA = 50.0   # mm, traction diameter the belt rides on
PULLEY_FLANGE_DIA = 60.0  # mm, belt-retaining flange OD
PULLEY_SPOKES = 5         # lightening windows in the pulley
# The side plates must be wider apart than the ball so it can't squirt out the
# sides while the top/bottom belts grip it -> inside width > TRIBALL_DIA.
SIDE_INNER_HALF = 95.0    # mm, half the inside width between the two side plates
PLOW_DEG = 20.0           # deg, front plow-blade rake (down-and-forward)
