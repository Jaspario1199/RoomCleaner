"""
Motor mount -- cradles a round gear-motor body in a ceiling corner.

Design notes:
  * A base plate screws to the ceiling / a corner block (4 holes).
  * A saddle with a half-cylinder cradle holds the motor body.
  * Zip-tie slots strap the motor firmly into the cradle (simple + strong).
  * Print with the base flat on the bed; the cradle overhang is < 45 deg so it
    needs no supports.
NOTE: this holds the MOTOR. The load-bearing CEILING anchors themselves must be
metal screws into a joist -- never a printed part (see cad/README.md).
"""

from __future__ import annotations

import cadquery as cq

from ..params import MOTOR_BODY_DIA, CLEARANCE, WALL, SCREW_M3

BASE_L = 70.0
BASE_W = 50.0
BASE_T = 5.0
STRAP_SLOT_W = 4.0     # zip-tie slot width
STRAP_SLOT_T = 2.5     # zip-tie slot thickness


def make() -> cq.Workplane:
    cradle_r = MOTOR_BODY_DIA / 2 + CLEARANCE
    saddle_h = cradle_r + WALL          # top of the saddle above the base
    saddle_len = BASE_W                 # cradle runs across the base width

    # Base plate with 4 mounting holes.
    part = cq.Workplane("XY").box(BASE_L, BASE_W, BASE_T, centered=(True, True, False))
    hx, hy = BASE_L / 2 - 7, BASE_W / 2 - 7
    part = (
        part.faces(">Z").workplane()
        .pushPoints([(hx, hy), (-hx, hy), (hx, -hy), (-hx, -hy)])
        .hole(SCREW_M3 + 0.6)
    )

    # Saddle block sitting on one half of the base, cradle axis along Y.
    saddle_cx = -BASE_L / 4 + 4
    saddle = (
        cq.Workplane("XY")
        .center(saddle_cx, 0)
        .box(MOTOR_BODY_DIA + 2 * WALL, saddle_len, saddle_h + cradle_r,
             centered=(True, True, False))
    )
    # Hollow the cradle: a horizontal cylinder (axis Y) at height saddle_h.
    cradle = (
        cq.Workplane("XZ")
        .workplane(offset=saddle_len / 2)
        .center(saddle_cx, saddle_h)
        .circle(cradle_r)
        .extrude(-saddle_len)
    )
    saddle = saddle.cut(cradle)
    # Open the top: chop everything above the cradle center so the motor drops in.
    lid = (
        cq.Workplane("XY")
        .center(saddle_cx, 0)
        .box(MOTOR_BODY_DIA + 2 * WALL, saddle_len, cradle_r,
             centered=(True, True, False))
        .translate((0, 0, saddle_h))
    )
    saddle = saddle.cut(lid)

    # Zip-tie slots: two pairs of thin vertical slots through the saddle walls.
    for sx in (saddle_cx - MOTOR_BODY_DIA / 3, saddle_cx + MOTOR_BODY_DIA / 3):
        slot = (
            cq.Workplane("XY")
            .center(sx, 0)
            .box(STRAP_SLOT_T, saddle_len + 2, STRAP_SLOT_W)
            .translate((0, 0, saddle_h - STRAP_SLOT_W))
        )
        # place slots through the side walls only (near +Y and -Y edges)
        for sy in (saddle_len / 2 - WALL / 2, -saddle_len / 2 + WALL / 2):
            wall_slot = (
                cq.Workplane("XY").center(sx, sy)
                .box(STRAP_SLOT_T, STRAP_SLOT_W, saddle_h + cradle_r)
                .translate((0, 0, 0))
            )
            saddle = saddle.cut(wall_slot)

    return part.union(saddle)


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "motor_mount"))
