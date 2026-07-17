"""
Tentacle hub -- the disc that carries the ring of curling fingers and routes all
their tendons to the single gripper servo.

How it works:
  * N rectangular pockets around the rim seat the finger bases (anti-rotation);
    one M3 screw per pocket retains each finger.
  * A tendon guide hole leads from each pocket inward to the central bore, where
    all tendons meet a junction on the servo horn. One servo pull curls every
    finger together.
  * The central bore also gives the downward camera a clear view between the
    fingers.
  * Four holes bolt the hub up to the end-effector frame.

Print flat (disc face on the bed), pockets facing up; no supports.
"""

from __future__ import annotations

import math
import cadquery as cq

from ..params import SCREW_M3, M3_THREAD_HOLE

N_FINGERS = 5
HUB_DIA = 88.0
HUB_THK = 12.0
BORE_DIA = 30.0          # central view / tendon-junction bore
POCKET_W = 16.4          # matches finger W_BASE + clearance
POCKET_H = 13.4          # matches finger H_BASE + clearance
POCKET_DEPTH = 10.0
TENDON_GUIDE = 2.0
RIM_INSET = 3.0          # pocket distance in from the outer edge


def make() -> cq.Workplane:
    hub = cq.Workplane("XY").circle(HUB_DIA / 2).extrude(HUB_THK)
    hub = hub.faces(">Z").workplane().circle(BORE_DIA / 2).cutThruAll()

    pocket_r = HUB_DIA / 2 - RIM_INSET - POCKET_H / 2

    for i in range(N_FINGERS):
        ang = 2 * math.pi * i / N_FINGERS
        cx, cy = pocket_r * math.cos(ang), pocket_r * math.sin(ang)
        deg = math.degrees(ang)

        # Pocket: a rectangular blind slot from the top, radially oriented
        # (POCKET_H is the radial dimension, POCKET_W tangential).
        pocket = (
            cq.Workplane("XY")
            .box(POCKET_H, POCKET_W, POCKET_DEPTH, centered=(True, True, False))
            .translate((0, 0, HUB_THK - POCKET_DEPTH))
            .rotate((0, 0, 0), (0, 0, 1), deg)
            .translate((cx, cy, 0))
        )
        hub = hub.cut(pocket)

        # Retaining screw: clearance hole from the top face into the pocket.
        screw = (
            cq.Workplane("XY")
            .circle((SCREW_M3 + 0.4) / 2)
            .extrude(HUB_THK)
            .rotate((0, 0, 0), (0, 0, 1), deg)
            .translate((cx, cy, 0))
        )
        hub = hub.cut(screw)

        # Tendon guide: a hole from the pocket floor inward to the central bore.
        guide_len = pocket_r  # generous; it will break into the bore
        guide = (
            cq.Workplane("XZ")
            .workplane(offset=0)
            .circle(TENDON_GUIDE / 2)
            .extrude(guide_len)
            .rotate((0, 0, 0), (1, 0, 0), -90)   # point along +Y
            .rotate((0, 0, 0), (0, 0, 1), deg - 90)
            .translate((cx, cy, HUB_THK - POCKET_DEPTH + 3))
        )
        hub = hub.cut(guide)

    # Four mounting holes to the effector frame (between the finger pockets).
    mount_r = HUB_DIA / 2 - RIM_INSET - POCKET_H - 4
    pts = [
        (mount_r * math.cos(a), mount_r * math.sin(a))
        for a in [math.radians(45 + 90 * k) for k in range(4)]
    ]
    # These 4 holes receive the screws that bolt the hub up to the effector
    # frame -> size them for heat-set inserts (or self-tap if disabled).
    hub = hub.faces(">Z").workplane().pushPoints(pts).hole(M3_THREAD_HOLE)

    return hub


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "tentacle_hub"))
