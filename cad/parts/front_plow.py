"""
Front plow -- the PUSH tool and the front cross-brace, in one part.

When the match wants a ball SHOVED through a contested zone instead of launched,
you don't run the flywheel at all: you drive the whole robot forward and this
raked blade plows the tri-ball ahead of it. The blade rakes down-and-forward so
it gets under the ball and controls it low. Its two end tabs bolt to the front
grid holes of both side plates, which also ties the plates together into a rigid
frame -- so it doubles as the structural front cross-brace of the mechanism.

Print blade-face-down (tabs pointing up); the raked blade needs no supports.
Structural PLA/PETG, >=4 walls, this part takes impact.
"""

from __future__ import annotations

import cadquery as cq

from ..params import PLATE_GAP, PLOW_DEG, VEX_HOLE

SPAN = PLATE_GAP            # blade width (fits between the plates)
BLADE_LEN = 60.0
BLADE_THK = 6.0
LIP_H = 16.0               # up-turned back lip = cross-brace / ball backstop
EAR_THK = 6.0
TAB_Y = 30.0
TAB_H = 34.0


def make() -> cq.Workplane:
    # Scoop blade: extends forward (+Y) from the back edge, hinged at y=0.
    blade = cq.Workplane("XY").box(SPAN, BLADE_LEN, BLADE_THK, centered=(True, False, True))
    blade = blade.rotate((0, 0, 0), (1, 0, 0), -PLOW_DEG)

    # Up-turned back lip spanning the full width = rigid cross-brace + backstop.
    lip = cq.Workplane("XY").box(SPAN, BLADE_THK, LIP_H, centered=(True, True, False))
    plow = blade.union(lip)

    # End mounting tabs (rise above the blade so their bolt holes are in tab-only
    # material). They overlap the blade/lip at the back, tying everything solid.
    for s in (+1, -1):
        tab = cq.Workplane("XY").box(EAR_THK, TAB_Y, TAB_H, centered=(True, False, False))
        tab = tab.translate((s * (SPAN / 2 - EAR_THK / 2), -4.0, 0))
        plow = plow.union(tab)

    # Two bolt holes per tab, drilled along X (per end, so the blade is untouched).
    for s in (+1, -1):
        x0 = s * (SPAN / 2 - EAR_THK - 1.0)
        for (hy, hz) in [(6.0, TAB_H - 9.0), (6.0, TAB_H - 22.0)]:
            cutter = (
                cq.Workplane("YZ").workplane(offset=x0)
                .center(hy, hz).circle(VEX_HOLE / 2).extrude(s * (EAR_THK + 3.0))
            )
            plow = plow.cut(cutter)

    return plow


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "front_plow"))
