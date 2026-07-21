"""
Intake side plate -- the structural scoop that carries the whole mechanism.

One flat plate holds:
  * the FLYWHEEL shaft bore (front-low, at the origin), and
  * the back CRADLE-ROLLER bore (up and back), which together set the pocket the
    tri-ball rests in.
Everything else -- the launch hood, the front plow, the V5 gearbox, and the
drivetrain C-channel -- bolts to the 0.5" hole grid that perforates the web, so
you can move a bearing flat or a standoff to any grid intersection to tune the
geometry. That grid is what makes it a real VEX plate rather than a slab.

The two shaft bores are round clearance holes; snap a VEX bearing flat over each
(its two screws land on the flanking grid holes) so the hex shaft spins true.

FLIP-SYMMETRIC: every hole goes straight through, so ONE printed part serves
BOTH sides -- just flip it over for the opposite plate. Print FLAT on the bed
(no supports). Structural PLA/PETG, >=4 walls, 40%+ infill. Print two.
"""

from __future__ import annotations

import cadquery as cq

from ..params import VEX_GRID, VEX_HOLE, VEX_SHAFT_CLEAR, PLATE_THK
from ..vexlib import grid_points

# Outline in the plate plane: +X = forward (intake mouth), +Y = up.
OUTLINE = [
    (68, -34),   # front-bottom
    (68, 6),     # front, rising
    (30, 90),    # top-front (hood lip)
    (-34, 90),   # top
    (-72, 46),   # back-top
    (-72, -34),  # back-bottom
]

FLY_BORE = (0.0, 0.0)        # flywheel shaft, on a grid intersection
ROLLER_BORE = (-3 * VEX_GRID, 2 * VEX_GRID)  # back cradle roller: (-38.1, 25.4)


def make() -> cq.Workplane:
    plate = (
        cq.Workplane("XY")
        .polyline(OUTLINE).close().extrude(PLATE_THK)
        .edges("|Z").fillet(8)
    )

    # Two shaft clearance bores (bearing flats snap over these).
    plate = (
        plate.faces(">Z").workplane()
        .pushPoints([FLY_BORE, ROLLER_BORE]).hole(VEX_SHAFT_CLEAR)
    )

    # 0.5" VEX hole grid across the web, clear of the two bores and the edges.
    holes = grid_points(
        OUTLINE, VEX_GRID, margin=VEX_HOLE / 2 + 3.0,
        keepouts=[(FLY_BORE[0], FLY_BORE[1], 10.0),
                  (ROLLER_BORE[0], ROLLER_BORE[1], 10.0)],
    )
    plate = plate.faces(">Z").workplane().pushPoints(holes).hole(VEX_HOLE)

    return plate


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "intake_side_plate"))
