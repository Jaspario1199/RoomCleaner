"""
Hardware constants for the host<->Arduino bridge. These describe the physical
drivetrain so the host can convert a cable length (meters) into motor steps.

MEASURE / MATCH these to your build:
  * MICROSTEP must match the jumpers under the DRV8825 drivers on the CNC shield.
  * DRUM_DIA_M must match your printed winch_spool drum diameter.
  * HOME_CABLE_LENGTHS is a calibration -- see driver.py.
"""

import math

# --- Stepper drivetrain ----------------------------------------------------
STEPS_PER_REV = 200          # 1.8-degree stepper => 200 full steps/rev
MICROSTEP = 16               # DRV8825 microstepping set by the shield jumpers
DRUM_DIA_M = 0.020           # m, winch spool drum diameter (cad SPOOL_DRUM_DIA)

DRUM_CIRC_M = math.pi * DRUM_DIA_M
STEPS_PER_M = STEPS_PER_REV * MICROSTEP / DRUM_CIRC_M   # ~50930 steps per meter

# --- Serial link -----------------------------------------------------------
SERIAL_PORT = "/dev/ttyUSB0"   # Windows: "COM3"; Mac: "/dev/tty.usbserial-XXXX"
BAUD = 115200

# --- Gripper servo angles (degrees) ---------------------------------------
# MUST equal cad/interfaces.py SERVO_GRIP_DEG (drum sizing depends on the 120 deg throw).
GRIP_ANGLE = 140             # tendon pulled -> tentacles curled (grip)
RELEASE_ANGLE = 20           # tendon slack -> tentacles open (release)

# --- Wireless effector (ESP32 on the claw) --------------------------------
# The gripper servo lives on an ESP32 on the effector, commanded over WiFi.
# Set EFFECTOR_HOST to the ESP32's IP (or mDNS name) once it's on your network.
EFFECTOR_HOST = "roomcleaner-claw.local"   # or e.g. "192.168.1.50"
EFFECTOR_PORT = 80

# --- Motion ----------------------------------------------------------------
MOVE_STEP_M = 0.15           # how finely to sample a path into hardware moves

# Measured cable lengths AT bead switch trigger, ordered X,Y,Z,A. None is not zero.
HOME_TRIGGER_LENGTHS_M = (None, None, None, None)
# Measured assembly pose after paying out setup lengths and attaching the claw.
# Four bead-trigger positions generally do NOT constitute a suspended claw pose.
HOME_POSE_M = None
# Commission with elevated calibration points; floor homography is insufficient.
CAMERA_PROJECTION = None  # 3x4 world (metres) -> image projective matrix
HAMPER_ROI_PX = None     # (x1,y1,x2,y2), visible receiving area
# Provisional speeds; tune on the loaded bench. Firmware caps individual axes.
TRAVEL_SPEED_M_S = 0.020
PICKUP_SPEED_M_S = 0.008

# Required measured node IDs/signs, produced by tools/commission_encoders.py.
ENCODER_CALIBRATION_FILE = "encoder_calibration.json"
