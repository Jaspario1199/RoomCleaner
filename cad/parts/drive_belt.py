"""
Drive belt -- the traction loop that grips and accelerates the tri-ball.

Two of these (top + bottom) form the barrel. The ball rides between their inner
runs; belt surface speed is the ball's exit speed. Modelled as a smooth stadium
loop (two straight runs + two pulley wraps) with a light transverse tread on the
outer faces for grip.

Best made as a COTS timing/traction belt or a welded urethane loop; if printed,
use TPU 95A so it flexes. Modelled here mainly so the assembly reads correctly
and so the barrel length / wrap are dimensioned. Print two.
"""

from __future__ import annotations

import cadquery as cq

from ..params import PULLEY_PITCH_DIA, BELT_THK, BELT_WIDTH, BARREL_LEN

TREAD_N = 11          # transverse tread ribs per straight run
TREAD_W = 1.4         # tread groove width
TREAD_D = 1.1         # tread groove depth (into a shallow surface cut)


def make() -> cq.Workplane:
    r_in = PULLEY_PITCH_DIA / 2.0        # rides on the pulley pitch OD
    r_out = r_in + BELT_THK
    L = BARREL_LEN

    outer = cq.Workplane("YZ").slot2D(L + 2 * r_out, 2 * r_out).extrude(BELT_WIDTH)
    inner = cq.Workplane("YZ").slot2D(L + 2 * r_in, 2 * r_in).extrude(BELT_WIDTH)
    belt = outer.cut(inner).translate((-BELT_WIDTH / 2.0, 0, 0))

    # Light tread across the two outer straight runs.
    for run in (+1, -1):
        for i in range(TREAD_N):
            yy = -L / 2.0 + L * (i + 0.5) / TREAD_N
            groove = (cq.Workplane("XY")
                      .box(BELT_WIDTH + 2, TREAD_W, TREAD_D * 2)
                      .translate((0, yy, run * r_out)))
            belt = belt.cut(groove)

    return belt


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "drive_belt"))
