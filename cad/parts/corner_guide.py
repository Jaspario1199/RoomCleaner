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
EAR_T = 4.0           # ear position/footprint reference (drives ear_cx/sy
                       # offsets below -- unchanged, keeps the GAP=10 pulley
                       # clearance and base layout as-is)
GAP = 10.0            # space between ears for the pulley
EAR_HOLE = SCREW_M3   # axle bolt hole
EAR_HOLE_DIA = EAR_HOLE + 0.3  # axle bolt clearance-hole diameter
EAR_HOLE_MIN_WALL = 1.5  # mm, minimum printable wall around the axle hole
# Actual ear plate thickness through the axle hole (X direction). Sized so
# (EAR_PLATE_T - EAR_HOLE_DIA) / 2 clears EAR_HOLE_MIN_WALL on each side of
# the hole, with a small margin over the bare 6.7 mm minimum for FDM
# tolerance: (7.0 - 3.7) / 2 = 1.65 mm >= 1.5 mm.
EAR_PLATE_T = 7.0


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
            .box(EAR_PLATE_T, EAR_T + 8, EAR_H, centered=(True, True, False))
        )
        # Axle hole near the top of the ear.
        ear = (
            ear.faces(">Y").workplane(centerOption="CenterOfBoundBox")
            .center(0, EAR_H / 2 - 6)
            .hole(EAR_HOLE_DIA)
        )
        part = part.union(ear)

    # Round the top outer corners of the ears a touch for looks/strength.
    return part


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "corner_guide"))
