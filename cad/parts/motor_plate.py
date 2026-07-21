"""
Motor plate -- mounts a V5 Smart Motor and gears it to a drive-pulley shaft.

One per belt. Direct drive is too slow to launch, so this plate carries the motor
at the lower bore and the belt's drive-pulley shaft one gear-pair away at the
upper bore; a gear-up (e.g. 12T -> 36T) spins the belt fast enough to fire the
ball. The two bores sit exactly GEAR_CD apart (a VEX-legal 1.5" centre distance),
and the whole web is on the 0.5" grid, so the V5's own mounting holes land on
grid points and you can re-pick the bore pair to change ratio.

Lower bore = clearance for the motor's output pilot; snap a bearing flat over the
upper bore for the pulley shaft. Rounded corners, print FLAT, no supports. Mounts
outboard of a side plate. PLA/PETG.
"""

from __future__ import annotations

import cadquery as cq

from ..params import VEX_GRID, VEX_HOLE, VEX_SHAFT_CLEAR, GEAR_CD, PLATE_THK
from ..vexlib import grid_points

MOTOR_PILOT = 26.0     # mm, clearance for the V5 output boss (open up for a gearbox)

OUTLINE = [(-38, -40), (38, -40), (38, GEAR_CD + 40), (-38, GEAR_CD + 40)]
MOTOR_BORE = (0.0, 0.0)
PULLEY_BORE = (0.0, GEAR_CD)


def make() -> cq.Workplane:
    plate = (
        cq.Workplane("XY")
        .polyline(OUTLINE).close().extrude(PLATE_THK)
        .edges("|Z").fillet(12)
    )

    plate = plate.faces(">Z").workplane().pushPoints([MOTOR_BORE]).hole(MOTOR_PILOT)
    plate = plate.faces(">Z").workplane().pushPoints([PULLEY_BORE]).hole(VEX_SHAFT_CLEAR)

    holes = grid_points(
        OUTLINE, VEX_GRID, margin=VEX_HOLE / 2 + 3.0,
        keepouts=[(0.0, 0.0, 15.0), (0.0, GEAR_CD, 10.0)],
    )
    plate = plate.faces(">Z").workplane().pushPoints(holes).hole(VEX_HOLE)

    return plate


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "motor_plate"))
