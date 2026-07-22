"""
Throat lip -- the smooth flared mouth at the muzzle of the barrel.

One at the top and one at the bottom of the front opening. On PULL it funnels the
tri-ball into the belt channel; on LAUNCH it gives the ball a clean, guided exit
so it leaves straight. A gentle flared arc, not a hard edge, so the foam ball
never snags.

Modelled as a quarter-arc band spanning between the side plates, with a slotted
mounting flange at each end that bolts to the plate's front grid holes. The part
is symmetric -- print two and flip one for the bottom lip. Print on a flange
face; the short arc overhangs mildly (a couple of supports or split-print). PLA/PETG.
"""

from __future__ import annotations

import cadquery as cq

from ..params import SIDE_INNER_HALF, VEX_HOLE

RI = 38.0                       # inner arc radius
RO = 41.0                       # outer arc radius
W = 2 * SIDE_INNER_HALF - 2.0   # span between the plates
EAR_THK = 5.0
FLANGE_Y0 = -8.0
FLANGE_Y1 = 42.0
FLANGE_Z = 8.0                  # +/- half-height of the mounting flange


def make() -> cq.Workplane:
    # Quarter-arc band (front-up flare): keep y>=0 and z>=0 of a tube.
    lip = (cq.Workplane("YZ").workplane(offset=-W / 2)
           .circle(RO).circle(RI).extrude(W))
    below = cq.Workplane("XY").box(4 * RO, 4 * RO, 200).translate((0, 0, -100))
    back = cq.Workplane("XY").box(4 * RO, 200, 4 * RO).translate((0, -100, 0))
    lip = lip.cut(below).cut(back)

    # Mounting flange at each end.
    for s in (+1, -1):
        flange = cq.Workplane("XY").box(
            EAR_THK, FLANGE_Y1 - FLANGE_Y0, 2 * FLANGE_Z)
        flange = flange.translate(
            (s * (W / 2 - EAR_THK / 2), (FLANGE_Y0 + FLANGE_Y1) / 2, 0))
        lip = lip.union(flange)

    # Two bolt holes per flange (cut through both ends at once, in flange-only
    # material well inboard of the arc foot).
    for gy in (8.0, 28.0):
        cutter = (cq.Workplane("YZ").workplane(offset=-W)
                  .center(gy, 0).circle(VEX_HOLE / 2).extrude(2 * W))
        lip = lip.cut(cutter)

    return lip


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "throat_lip"))
