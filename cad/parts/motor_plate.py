"""
Motor plate -- mounts the V5 Smart Motor and gears it up to the flywheel shaft.

A direct-drive flywheel is too slow to launch; this plate carries the motor at
the lower bore and the flywheel shaft one gear-pair away at the upper bore, so a
gear-up (e.g. 12T -> 36T) spins the wheel fast enough to throw the ball. The two
bores sit exactly GEAR_CD apart (a VEX-legal 1.5" centre distance), and the whole
web is perforated on the 0.5" grid, so the V5's own mounting holes land on grid
points and you can re-pick the bore pair to change the ratio.

The lower bore is a clearance for the motor's output pilot; snap a bearing flat
over the upper bore for the flywheel shaft. Print FLAT, no supports. Mounts
outboard of one side plate. PLA/PETG.
"""

from __future__ import annotations

import cadquery as cq

from ..params import VEX_GRID, VEX_HOLE, VEX_SHAFT_CLEAR, GEAR_CD, PLATE_THK
from ..vexlib import grid_points

MOTOR_PILOT = 26.0     # mm, clearance for the V5 output boss (open up for a gearbox)

OUTLINE = [(-38, -40), (38, -40), (38, GEAR_CD + 40), (-38, GEAR_CD + 40)]
MOTOR_BORE = (0.0, 0.0)
FLYWHEEL_BORE = (0.0, GEAR_CD)


def make() -> cq.Workplane:
    plate = (
        cq.Workplane("XY")
        .polyline(OUTLINE).close().extrude(PLATE_THK)
        .edges("|Z").fillet(8)
    )

    plate = plate.faces(">Z").workplane().pushPoints([MOTOR_BORE]).hole(MOTOR_PILOT)
    plate = plate.faces(">Z").workplane().pushPoints([FLYWHEEL_BORE]).hole(VEX_SHAFT_CLEAR)

    holes = grid_points(
        OUTLINE, VEX_GRID, margin=VEX_HOLE / 2 + 3.0,
        keepouts=[(0.0, 0.0, 15.0), (0.0, GEAR_CD, 10.0)],
    )
    plate = plate.faces(">Z").workplane().pushPoints(holes).hole(VEX_HOLE)

    return plate


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "motor_plate"))
