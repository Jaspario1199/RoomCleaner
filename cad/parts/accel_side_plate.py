"""
Accelerator side plate -- the structural wall of the belt barrel.

One flat plate per side carries all four pulley shafts: the front (muzzle) pair
are fixed bores, the rear (breach) pair ride in TENSION SLOTS so you can slide
the idlers back to tension each belt. Between them the ball runs down the barrel.
Everything else -- the motors, the throat lips, the plow, the drivetrain -- bolts
to the 0.5" grid that fills the web.

Big corner radii and a smooth central lightening window keep it light and clean.
FLIP-SYMMETRIC: all features go straight through, so ONE printed part serves both
sides. Print FLAT, no supports. Structural PLA/PETG, >=4 walls, 40%+ infill.
Print two.
"""

from __future__ import annotations

import cadquery as cq

from ..params import (
    BELT_GAP, PULLEY_PITCH_DIA, BELT_THK, BARREL_LEN, PLATE_THK,
    VEX_GRID, VEX_HOLE, VEX_SHAFT_CLEAR,
)
from ..vexlib import grid_points

XO = BARREL_LEN / 2.0                                   # pulley x offset (barrel)
YO = BELT_GAP / 2.0 + PULLEY_PITCH_DIA / 2.0 + BELT_THK  # pulley y offset (from centre)
HX = XO + 30.0
HY = YO + 34.0
OUTLINE = [(-HX, -HY), (HX, -HY), (HX, HY), (-HX, HY)]

WIN_H = 2 * YO - 66.0     # central window height
WIN_W = 2 * XO - 60.0     # central window width


def make() -> cq.Workplane:
    plate = (
        cq.Workplane("XY")
        .polyline(OUTLINE).close().extrude(PLATE_THK)
        .edges("|Z").fillet(34)
    )

    # Smooth central lightening window (vertical stadium).
    plate = plate.faces(">Z").workplane().slot2D(WIN_H, WIN_W, 90).cutThruAll()

    # Front (muzzle) pulley bores -- fixed.
    plate = plate.faces(">Z").workplane().pushPoints([(XO, YO), (XO, -YO)]).hole(VEX_SHAFT_CLEAR)

    # Rear (breach) pulley bores -- tension slots along the barrel.
    for (bx, by) in [(-XO, YO), (-XO, -YO)]:
        plate = (plate.faces(">Z").workplane()
                 .moveTo(bx, by).slot2D(VEX_SHAFT_CLEAR + 22, VEX_SHAFT_CLEAR, 0)
                 .cutThruAll())

    # 0.5" VEX grid across the web, clear of the bores and the central window.
    holes = grid_points(
        OUTLINE, VEX_GRID, margin=VEX_HOLE / 2 + 3.0,
        keepouts=[(XO, YO, 14.0), (XO, -YO, 14.0), (-XO, YO, 22.0), (-XO, -YO, 22.0)],
    )
    holes = [(x, y) for (x, y) in holes
             if not (abs(x) < WIN_W / 2 + 7 and abs(y) < WIN_H / 2 + 7)]
    plate = plate.faces(">Z").workplane().pushPoints(holes).hole(VEX_HOLE)

    return plate


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "accel_side_plate"))
