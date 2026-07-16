"""
End-effector frame -- the body that hangs on the four cables and carries the
gripper servo, the tentacle hub (bolted underneath), and a downward camera.

Features:
  * Rounded-square plate, lightened with a central bore (camera view + tendon
    path down to the fingers).
  * Four corner cable eyes -- the four winch cables tie off here. Spreading them
    to the corners maximizes tilt stability of the hanging effector.
  * A central MG996R servo pocket with mounting holes; the horn faces down and
    pulls all finger tendons through the bore.
  * Four holes matching the tentacle hub, to bolt it on underneath.

Print flat, pocket side up; no supports.
"""

from __future__ import annotations

import math
import cadquery as cq

from ..params import SCREW_M3, SCREW_M3_TAP

PLATE = 92.0
THK = 5.0
BORE = 30.0
CABLE_HOLE = 3.2         # tie-off hole for the Dyneema at each corner
CORNER_INSET = 9.0

# MG996R servo pocket.
SERVO_L = 41.0
SERVO_W = 20.2
SERVO_EAR_SPAN = 48.3    # centre-to-centre of the two mounting-tab holes
SERVO_SCREW = SCREW_M3


def make() -> cq.Workplane:
    # Rounded-square plate.
    plate = (
        cq.Workplane("XY")
        .rect(PLATE, PLATE).extrude(THK)
        .edges("|Z").fillet(10)
    )
    # Central bore.
    plate = plate.faces(">Z").workplane().circle(BORE / 2).cutThruAll()

    # Four corner cable eyes: reinforcing bosses + tie holes.
    c = PLATE / 2 - CORNER_INSET
    corners = [(c, c), (-c, c), (-c, -c), (c, -c)]
    for (x, y) in corners:
        boss = (
            cq.Workplane("XY").center(x, y).circle(6).extrude(THK + 3)
        )
        plate = plate.union(boss)
    plate = (
        plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .pushPoints(corners).hole(CABLE_HOLE)
    )

    # Servo pocket (through), centred, with two mounting-tab holes.
    plate = (
        plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .rect(SERVO_L, SERVO_W).cutThruAll()
    )
    plate = (
        plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .pushPoints([(SERVO_EAR_SPAN / 2, 0), (-SERVO_EAR_SPAN / 2, 0)])
        .hole(SERVO_SCREW + 0.4)
    )

    # Four hub-mounting holes (match tentacle_hub mount pattern, r ~ 27).
    mount_r = 27.0
    pts = [
        (mount_r * math.cos(a), mount_r * math.sin(a))
        for a in [math.radians(45 + 90 * k) for k in range(4)]
    ]
    plate = plate.faces(">Z").workplane(centerOption="CenterOfBoundBox").pushPoints(pts).hole(SCREW_M3 + 0.4)

    return plate


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "effector_frame"))
