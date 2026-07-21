"""
Launch hood -- the curved deflector that makes one wheel intake AND launch.

It is the piece that separates HOLD from LAUNCH. At low flywheel speed the hood's
concave face keeps the tri-ball trapped in the pocket (it can't climb out), so
the wheel just holds/controls it. Spin the wheel up and the ball now carries
enough energy to ride up the hood and shoot off its lip -- the hood sets the
launch angle. Slide the slotted end flanges on the side-plate grid holes to trim
that angle for near/far shots.

Modelled as an arc segment spanning between the two side plates, with a flat
mounting flange at each end. Print on one flat flange face; the arch overhangs
mildly -- a few supports under the lip, or split-print, are fine. PLA/PETG.
"""

from __future__ import annotations

import cadquery as cq

from ..params import PLATE_GAP, HOOD_RADIUS, HOOD_THK, VEX_HOLE, VEX_GRID

WH = PLATE_GAP - 1.0        # span between the plates
EAR_THK = 5.0               # end-flange thickness (along the shaft axis)
FLANGE_Y = 40.0             # flange fore/aft extent
FLANGE_Z0 = -22.0           # flange bottom (reaches down to plate grid holes)
FLANGE_Z1 = 6.0             # flange top (overlaps the arch feet)


def make() -> cq.Workplane:
    Ri = HOOD_RADIUS
    Ro = Ri + HOOD_THK

    # Full tube along X, then trim to a front-top arc segment (deflector).
    hood = (
        cq.Workplane("YZ").workplane(offset=-WH / 2)
        .circle(Ro).circle(Ri).extrude(WH)
    )
    below = cq.Workplane("XY").box(4 * Ro, 4 * Ro, 200).translate((0, 0, -100))
    back = cq.Workplane("XY").box(4 * Ro, 200, 4 * Ro).translate((0, -100 - 8, 0))
    hood = hood.cut(below).cut(back)          # keep z>=0 and y>=-8 (front-top arc)

    # End flanges + slotted mounts.
    for s in (+1, -1):
        flange = cq.Workplane("XY").box(EAR_THK, FLANGE_Y, FLANGE_Z1 - FLANGE_Z0)
        flange = flange.translate(
            (s * (WH / 2 - EAR_THK / 2), 6.0, (FLANGE_Z0 + FLANGE_Z1) / 2)
        )
        hood = hood.union(flange)

    # Two vertical adjustment slots per flange (cut through both ends at once;
    # at z<0 there is only flange material, so the arch is untouched).
    for gy in (+VEX_GRID, -VEX_GRID):
        slot = (
            cq.Workplane("YZ").workplane(offset=-WH)
            .center(gy + 6.0, -9.0).slot2D(14.0, VEX_HOLE, 90)
            .extrude(2 * WH)
        )
        hood = hood.cut(slot)

    return hood


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "launch_hood"))
