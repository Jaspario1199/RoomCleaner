"""
Corner cable guide -- a U-bracket that holds a small pulley in the ceiling corner
and redirects the Dyneema from the spool out into the room.

Design notes:
  * Two upright ears with aligned holes carry an M3 bolt as the pulley axle.
  * Sized for a common ~18-22 mm bearing pulley (edit GAP / EAR_HOLE to fit).
  * A printed pulley works for low-cycle testing, but a bought bearing pulley is
    strongly preferred here -- friction at this redirect point directly costs you
    position accuracy.
  * Base plate screws to the corner. Print base-down, no supports.
"""

from __future__ import annotations

import cadquery as cq

from ..params import SCREW_M3

BASE_L = 55.0
BASE_W = 34.0
BASE_T = 5.0
EAR_H = 26.0
EAR_T = 4.0
GAP = 10.0            # space between ears for the pulley
EAR_HOLE = SCREW_M3   # axle bolt hole


def make() -> cq.Workplane:
    part = cq.Workplane("XY").box(BASE_L, BASE_W, BASE_T, centered=(True, True, False))

    # Base mounting holes (2, along the far end from the ears).
    hx = BASE_L / 2 - 7
    part = (
        part.faces(">Z").workplane()
        .pushPoints([(hx, BASE_W / 2 - 7), (hx, -BASE_W / 2 + 7)])
        .hole(SCREW_M3 + 0.6)
    )

    # Two ears rising from the near end, straddling the pulley gap.
    ear_cx = -BASE_L / 2 + EAR_T / 2 + 6
    for sy in (GAP / 2 + EAR_T / 2, -(GAP / 2 + EAR_T / 2)):
        ear = (
            cq.Workplane("XY")
            .center(ear_cx, sy)
            .box(EAR_T, EAR_T + 8, EAR_H, centered=(True, True, False))
        )
        # Axle hole near the top of the ear.
        ear = (
            ear.faces(">Y").workplane(centerOption="CenterOfBoundBox")
            .center(0, EAR_H / 2 - 6)
            .hole(EAR_HOLE + 0.3)
        )
        part = part.union(ear)

    # Round the top outer corners of the ears a touch for looks/strength.
    return part


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "corner_guide"))
