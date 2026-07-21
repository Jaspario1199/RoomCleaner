"""
Flywheel -- the one driven wheel that does the work in all three ball modes.

    PULL   spin inward slowly  -> friction rolls the tri-ball up into the cradle
    HOLD   stall / creep       -> ball rests against the hood, no launch energy
    LAUNCH spin up to speed    -> the SAME wheel throws the ball over the hood lip

A heavy rim (mass concentrated at the OD) stores rotational energy so the wheel
keeps its speed through the launch instead of bogging when the ball loads it.
Two circumferential grooves take rubber traction bands (or press-on flex-wheel
tyres) so the wheel grips foam without a hard-plastic slip.

Fits a 1/2" VEX high-strength HEX shaft; a radial set-screw access hole lets you
lock it against the hex flat. Print BORE-UP (axis vertical): the rim grooves and
web windows all print cleanly with no supports. Structural PLA/PETG, >=4 walls,
40%+ infill (rim mass = launch energy). Print two -- one per side of the ball.
"""

from __future__ import annotations

import math
import cadquery as cq

from ..params import (
    FLYWHEEL_DIA, FLYWHEEL_WIDTH, FLY_SPOKES, FLY_GROOVES,
    VEX_HEX_AF, VEX_HEX_CLEAR, SCREW_M3_TAP,
)
from ..vexlib import hex_across_corners

HUB_R = 13.0          # mm, central hub radius (carries the hex bore)
RIM_THK = 9.0         # mm, rim radial thickness (mass at the OD = inertia)
GROOVE_DEPTH = 1.8    # mm, traction-band groove depth into the OD
GROOVE_W = 3.2        # mm, traction-band groove width (fits a #64 band)


def make() -> cq.Workplane:
    W = FLYWHEEL_WIDTH
    R = FLYWHEEL_DIA / 2.0
    rim_in = R - RIM_THK

    wheel = cq.Workplane("XY").circle(R).extrude(W)

    # Lightening windows in the web -> leaves hub, rim, and spokes between them.
    win_r = (HUB_R + rim_in) / 2.0
    win_d = (rim_in - HUB_R) - 8.0          # 4 mm web to hub and to rim
    pts = [
        (win_r * math.cos(math.radians(a)), win_r * math.sin(math.radians(a)))
        for a in [360.0 * k / FLY_SPOKES + 36.0 for k in range(FLY_SPOKES)]
    ]
    wheel = wheel.faces(">Z").workplane().pushPoints(pts).hole(win_d)

    # Circumferential traction-band grooves in the rim OD.
    for k in range(FLY_GROOVES):
        zc = W * (k + 1) / (FLY_GROOVES + 1)
        ring = (
            cq.Workplane("XY").workplane(offset=zc - GROOVE_W / 2)
            .circle(R + 2).circle(R - GROOVE_DEPTH).extrude(GROOVE_W)
        )
        wheel = wheel.cut(ring)

    # 1/2" hex bore for the VEX high-strength shaft.
    ac = hex_across_corners(VEX_HEX_AF + VEX_HEX_CLEAR)
    wheel = wheel.faces(">Z").workplane(centerOption="CenterOfBoundBox").polygon(6, ac).cutThruAll()

    # Radial set-screw access hole (locks the hub on the hex flat).
    grub = (
        cq.Workplane("YZ").transformed(offset=(0, W / 2.0, 0))
        .circle(SCREW_M3_TAP / 2.0).extrude(R + 1)
    )
    wheel = wheel.cut(grub)

    return wheel


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "flywheel"))
