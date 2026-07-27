"""
Central configuration for the RoomCleaner cable-driven robot.

Everything here uses SI units:
    - distances in METERS
    - mass in KILOGRAMS
    - angles in RADIANS

The coordinate frame:
    - origin (0, 0, 0) is a corner of the room on the FLOOR
    - +x runs along one wall, +y along the adjacent wall
    - +z points UP toward the ceiling

So the four ceiling corners are at height z = ROOM_HEIGHT, and the floor
(where laundry lives) is the plane z = 0.

============================================================================
  >>> YOU ONLY NEED TO EDIT THE TWO BLOCKS MARKED "EDIT ME" BELOW <<<
      (your room dimensions, and your ceiling-fan location/size)
  Everything else is computed for you.
============================================================================
"""

from dataclasses import dataclass, field
import numpy as np


# ===========================================================================
#  EDIT ME (1/2) --- ROOM GEOMETRY.  Measure your room in meters.
# ===========================================================================
ROOM_WIDTH = 4.0    # meters, along +x  (wall-to-wall)
ROOM_DEPTH = 3.0    # meters, along +y  (wall-to-wall)
ROOM_HEIGHT = 2.6   # meters, floor to ceiling


# ===========================================================================
#  EDIT ME (2/2) --- CEILING FAN.  The robot's cables must NEVER touch it.
#
#  Model the fan as a vertical no-go CYLINDER hanging from the ceiling:
#    - center it at the fan's mounting point (x, y) on the ceiling
#    - radius = half the fan's blade span (tip-to-tip diameter / 2)
#    - it spans from the LOWEST point of the fan up to the ceiling
#
#  Measure: stand under the fan, drop a plumb line (or just eyeball the
#  center), measure how far each blade tip reaches, and how far the lowest
#  part of the fan hangs below the ceiling.
#
#  If you have NO ceiling fan, set HAS_FAN = False and ignore the rest.
# ===========================================================================
HAS_FAN = True
FAN_CENTER_X = 2.0            # meters, fan center along +x  (often room center)
FAN_CENTER_Y = 1.5           # meters, fan center along +y
FAN_BLADE_RADIUS = 0.55      # meters, blade tip reach from center (blade span / 2)
FAN_DROP = 0.35              # meters, how far the LOWEST part hangs below the ceiling
FAN_SAFETY_MARGIN = 0.15     # meters, extra keep-out padding around the whole fan


# ---------------------------------------------------------------------------
# Winch anchor points -- one motor in each ceiling corner.
# Order matters and is fixed everywhere: A, B, C, D going counter-clockwise.
# (Derived from the room dimensions above -- normally no need to edit.)
# ---------------------------------------------------------------------------
ANCHORS = np.array(
    [
        [0.0,        0.0,        ROOM_HEIGHT],   # A  (near-left corner)
        [ROOM_WIDTH, 0.0,        ROOM_HEIGHT],   # B  (near-right corner)
        [ROOM_WIDTH, ROOM_DEPTH, ROOM_HEIGHT],   # C  (far-right corner)
        [0.0,        ROOM_DEPTH, ROOM_HEIGHT],   # D  (far-left corner)
    ],
    dtype=float,
)


# ---------------------------------------------------------------------------
# End-effector (the servo-driven tentacle GRABBER) + payload
# ---------------------------------------------------------------------------
# The workspace/tension math validates the WORST case: the effector carrying its
# heaviest payload. Target payload is a pair of average Levi's jeans (~0.9 kg).
EFFECTOR_ASSEMBLY = 0.45      # kg, printed frame + hub + 5 TPU fingers + servo + camera
MAX_PAYLOAD = 0.90           # kg, heaviest item to carry (jeans ~2 lb)
EFFECTOR_MASS = EFFECTOR_ASSEMBLY + MAX_PAYLOAD   # kg, loaded mass used for statics
GRAVITY = 9.81                # m/s^2
MAX_CABLE_TENSION = 40.0      # N, the most force one motor may pull with (safety limit)
MIN_CABLE_TENSION = 0.5       # N, keep a little tension so cables never go slack

# Safety margins: the effector is not allowed within this distance of a wall,
# and cannot go below this height except during a deliberate "reach down to grab".
WALL_MARGIN = 0.20            # meters
SAFE_MIN_Z = 0.15            # meters -- normal travel height floor clearance

# D9: EFFECTOR_REACH is the cable plane -> fingertip distance (see
# cad/interfaces.py EFFECTOR_REACH_M, the authoritative CAD value).
EFFECTOR_REACH = 0.118       # meters -- cable plane to fingertips (cad/interfaces.py EFFECTOR_REACH_M; integration-measured)
# GRAB_Z is the height of the kinematic point (the cable plane, not the
# fingertips) when grabbing: the fingertips reach the floor once the plate
# is EFFECTOR_REACH above it, plus a small margin so the fingers don't drag.
GRAB_Z = EFFECTOR_REACH + 0.02   # meters -- how low the grabber (cable plane) descends to pick up cloth


@dataclass
class FanZone:
    """A vertical no-go cylinder for a ceiling fan (or any ceiling obstacle).

    The cylinder is centered at (cx, cy), has radius `radius`, and spans
    z in [z_low, z_high]. `radius` and `z_low` already include the safety
    margin (see `from_config`).
    """

    cx: float
    cy: float
    radius: float
    z_low: float
    z_high: float
    enabled: bool = True

    @classmethod
    def from_config(cls, room_height: float = ROOM_HEIGHT) -> "FanZone":
        # Lowest point of the keep-out volume = ceiling minus drop, minus margin.
        z_low = room_height - FAN_DROP - FAN_SAFETY_MARGIN
        return cls(
            cx=FAN_CENTER_X,
            cy=FAN_CENTER_Y,
            radius=FAN_BLADE_RADIUS + FAN_SAFETY_MARGIN,
            z_low=max(0.0, z_low),
            z_high=room_height + 0.01,       # up to (just past) the ceiling
            enabled=HAS_FAN,
        )


@dataclass
class RobotConfig:
    """Bundles the physical description of one robot so we can pass it around."""

    anchors: np.ndarray = field(default_factory=lambda: ANCHORS.copy())
    mass: float = EFFECTOR_MASS
    gravity: float = GRAVITY
    max_tension: float = MAX_CABLE_TENSION
    min_tension: float = MIN_CABLE_TENSION
    room_width: float = ROOM_WIDTH
    room_depth: float = ROOM_DEPTH
    room_height: float = ROOM_HEIGHT
    fan: FanZone = field(default_factory=lambda: FanZone.from_config(ROOM_HEIGHT))

    @property
    def num_cables(self) -> int:
        return len(self.anchors)


DEFAULT_CONFIG = RobotConfig()
