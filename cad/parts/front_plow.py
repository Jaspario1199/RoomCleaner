"""
Front plow -- the PUSH tool and the front cross-brace, in one part.

When the match wants a ball SHOVED through a contested zone instead of launched,
you leave the belts off and just drive forward: this raked blade gets under the
tri-ball and controls it low. Its two end tabs bolt to the front grid holes of
both side plates, tying them into a rigid frame -- so it doubles as the front
cross-brace of the accelerator.

Rounded leading edge so it slides under the ball cleanly. Print blade-face-down
(tabs up); no supports. Structural PLA/PETG, >=4 walls -- this part takes impact.
"""

from __future__ import annotations

import cadquery as cq

from ..params import SIDE_INNER_HALF, PLOW_DEG, VEX_HOLE

SPAN = 2 * SIDE_INNER_HALF   # blade width (fits between the plates)
BLADE_LEN = 62.0
BLADE_THK = 6.0
LIP_H = 16.0                 # up-turned back lip = cross-brace / ball backstop
EAR_THK = 6.0
TAB_Y = 30.0
TAB_H = 34.0


def make() -> cq.Workplane:
    blade = cq.Workplane("XY").box(SPAN, BLADE_LEN, BLADE_THK, centered=(True, False, True))
    # Round the leading edge so it slides under the ball.
    try:
        blade = blade.edges(">Y and |X").fillet(BLADE_THK / 2 - 0.4)
    except Exception:
        pass
    blade = blade.rotate((0, 0, 0), (1, 0, 0), -PLOW_DEG)

    lip = cq.Workplane("XY").box(SPAN, BLADE_THK, LIP_H, centered=(True, True, False))
    plow = blade.union(lip)

    for s in (+1, -1):
        tab = cq.Workplane("XY").box(EAR_THK, TAB_Y, TAB_H, centered=(True, False, False))
        tab = tab.translate((s * (SPAN / 2 - EAR_THK / 2), -4.0, 0))
        plow = plow.union(tab)

    for s in (+1, -1):
        x0 = s * (SPAN / 2 - EAR_THK - 1.0)
        for (hy, hz) in [(6.0, TAB_H - 9.0), (6.0, TAB_H - 22.0)]:
            cutter = (cq.Workplane("YZ").workplane(offset=x0)
                      .center(hy, hz).circle(VEX_HOLE / 2).extrude(s * (EAR_THK + 3.0)))
            plow = plow.cut(cutter)

    return plow


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "front_plow"))
