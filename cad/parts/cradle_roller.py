"""
Cradle roller -- the driven back roller that forms the ball pocket.

Sits up and behind the flywheel. Two jobs:
  * INTAKE: geared/banded to spin with the flywheel, it gives the tri-ball a
    SECOND driven contact line, so a big light ball is pulled up cleanly instead
    of skipping off a single wheel.
  * HOLD:  with the flywheel stalled it becomes the back wall of the pocket, so
    the held ball can't roll back out of the robot.

Fluted (axial ribs) for grip on foam, hollow-ish via the hex bore. Rides a 1/2"
VEX hex shaft (live-driven, or dead with the roller free-spinning). Print UPRIGHT
(bore vertical) so the flutes and bore need no supports. PLA/PETG.
"""

from __future__ import annotations

import math
import cadquery as cq

from ..params import PLATE_GAP, ROLLER_DIA, VEX_HEX_AF, VEX_HEX_CLEAR
from ..vexlib import hex_across_corners

N_FLUTES = 12
FLUTE_R = 2.6          # mm, radius of each axial grip groove


def make() -> cq.Workplane:
    L = PLATE_GAP - 4.0
    R = ROLLER_DIA / 2.0

    roller = cq.Workplane("XY").circle(R).extrude(L)

    # Axial grip flutes scalloped around the OD.
    for k in range(N_FLUTES):
        a = math.radians(360.0 * k / N_FLUTES)
        flute = (
            cq.Workplane("XY").center(R * math.cos(a), R * math.sin(a))
            .circle(FLUTE_R).extrude(L)
        )
        roller = roller.cut(flute)

    # 1/2" hex bore.
    ac = hex_across_corners(VEX_HEX_AF + VEX_HEX_CLEAR)
    roller = roller.faces(">Z").workplane(centerOption="CenterOfBoundBox").polygon(6, ac).cutThruAll()

    return roller


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "cradle_roller"))
