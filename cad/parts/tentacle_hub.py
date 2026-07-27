"""
Tentacle hub -- the disc that carries the ring of curling fingers and routes all
their tendons to the single gripper servo.

How it works:
  * N rectangular THROUGH-slots around the rim seat the finger bases
    (anti-rotation). Each finger is inserted from BELOW; a 2 mm shoulder on the
    finger base bears on the hub underside (D5), and an axial M3 + washer from
    the hub top into the finger base tap carries gravity -- no hub-side
    retaining screw hole is needed.
  * A tendon guide hole leads from each slot inward to the central bore, where
    all tendons meet a junction on the servo horn. One servo pull curls every
    finger together.
  * The central bore also gives the downward camera a clear view between the
    fingers.
  * Four holes bolt the hub up to the end-effector frame, on the shared
    HUB_MOUNT_R / STANDOFF_ANGLES_DEG bolt circle (D6).

Print flat (disc face on the bed), slots facing up; no supports.
"""

from __future__ import annotations

import math
import cadquery as cq

from ..params import M3_THREAD_HOLE, HUB_MOUNT_R, STANDOFF_ANGLES_DEG, HUB_THK

N_FINGERS = 5
HUB_DIA = 88.0
# HUB_THK now comes from cad/interfaces.py (it equals the finger slot
# engagement length, a mating value shared with tentacle_finger).
BORE_DIA = 30.0          # central view / tendon-junction bore
POCKET_W = 16.4          # matches finger W_BASE + clearance
POCKET_H = 13.4          # matches finger H_BASE + clearance
# D5: the pocket is now a THROUGH-slot (no floor) so the finger can be inserted
# from below and its base shoulder can bear on the hub underside. Depth equals
# the full hub thickness. Kept as a named constant (rather than inlining
# HUB_THK at each use site) because cad/export_all.py reads
# tentacle_hub.POCKET_DEPTH to place the assembled finger at the hub underside.
POCKET_DEPTH = HUB_THK
TENDON_GUIDE = 2.0
TENDON_GUIDE_Z = 5.0     # mm above the hub BOTTOM face (re-anchored per D5/D6)
RIM_INSET = 3.0          # pocket distance in from the outer edge


def make() -> cq.Workplane:
    hub = cq.Workplane("XY").circle(HUB_DIA / 2).extrude(HUB_THK)
    hub = hub.faces(">Z").workplane().circle(BORE_DIA / 2).cutThruAll()

    pocket_r = HUB_DIA / 2 - RIM_INSET - POCKET_H / 2

    for i in range(N_FINGERS):
        ang = 2 * math.pi * i / N_FINGERS
        cx, cy = pocket_r * math.cos(ang), pocket_r * math.sin(ang)
        deg = math.degrees(ang)

        # Slot: a rectangular THROUGH-cut (D5), radially oriented (POCKET_H is
        # the radial dimension, POCKET_W tangential). Full HUB_THK depth, no
        # floor -- the finger inserts from below and its shoulder bears on the
        # hub underside, so no per-pocket retaining screw hole is cut here.
        pocket = (
            cq.Workplane("XY")
            .box(POCKET_H, POCKET_W, POCKET_DEPTH, centered=(True, True, False))
            .translate((0, 0, HUB_THK - POCKET_DEPTH))
            .rotate((0, 0, 0), (0, 0, 1), deg)
            .translate((cx, cy, 0))
        )
        hub = hub.cut(pocket)

        # Tendon guide: a hole from the slot void inward to the central bore,
        # anchored TENDON_GUIDE_Z above the hub bottom face (still well within
        # the slot's full-depth void and clear of the finger's tendon channel).
        guide_len = pocket_r  # generous; it will break into the bore
        guide = (
            cq.Workplane("XZ")
            .workplane(offset=0)
            .circle(TENDON_GUIDE / 2)
            .extrude(guide_len)
            .rotate((0, 0, 0), (1, 0, 0), -90)   # point along +Y
            .rotate((0, 0, 0), (0, 0, 1), deg - 90)
            .translate((cx, cy, TENDON_GUIDE_Z))
        )
        hub = hub.cut(guide)

    # Four mounting holes to the effector frame, on the shared bolt circle
    # (D6): HUB_MOUNT_R / STANDOFF_ANGLES_DEG are the single authoritative
    # source (cad/interfaces.py) for both the hub and the frame -- this
    # replaces a previously independently-derived radius (~23.6 mm) that did
    # not match the frame's hole circle.
    pts = [
        (HUB_MOUNT_R * math.cos(math.radians(a)), HUB_MOUNT_R * math.sin(math.radians(a)))
        for a in STANDOFF_ANGLES_DEG
    ]
    # These 4 holes receive the screws that bolt the hub up to the effector
    # frame -> size them for heat-set inserts (or self-tap if disabled).
    hub = hub.faces(">Z").workplane().pushPoints(pts).hole(M3_THREAD_HOLE)

    return hub


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "tentacle_hub"))
