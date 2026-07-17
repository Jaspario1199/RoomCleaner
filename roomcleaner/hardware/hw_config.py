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
GRIP_ANGLE = 120             # tendon pulled -> tentacles curled (grip)
RELEASE_ANGLE = 20           # tendon slack -> tentacles open (release)

# --- Motion ----------------------------------------------------------------
MOVE_STEP_M = 0.15           # how finely to sample a path into hardware moves
