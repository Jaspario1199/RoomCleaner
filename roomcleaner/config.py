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
"""

from dataclasses import dataclass, field
import numpy as np


# ---------------------------------------------------------------------------
# Room geometry  (measure YOUR room and change these three numbers)
# ---------------------------------------------------------------------------
ROOM_WIDTH = 4.0    # meters, along +x
ROOM_DEPTH = 3.0    # meters, along +y
ROOM_HEIGHT = 2.6   # meters, floor to ceiling


# ---------------------------------------------------------------------------
# Winch anchor points -- one motor in each ceiling corner.
# Order matters and is fixed everywhere: A, B, C, D going counter-clockwise.
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
# End-effector (the "claw" assembly) physical properties
# ---------------------------------------------------------------------------
EFFECTOR_MASS = 0.6           # kg, the claw + camera + suction head hanging on the cables
GRAVITY = 9.81                # m/s^2
MAX_CABLE_TENSION = 40.0      # N, the most force one motor may pull with (safety limit)
MIN_CABLE_TENSION = 0.5       # N, keep a little tension so cables never go slack

# Safety margins: the effector is not allowed within this distance of a wall,
# and cannot go below this height except during a deliberate "reach down to grab".
WALL_MARGIN = 0.20            # meters
SAFE_MIN_Z = 0.15            # meters -- normal travel height floor clearance
GRAB_Z = 0.03               # meters -- how low the head descends to pick up cloth


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

    @property
    def num_cables(self) -> int:
        return len(self.anchors)


DEFAULT_CONFIG = RobotConfig()
