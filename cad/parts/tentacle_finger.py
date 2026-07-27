"""
Tentacle finger -- a tendon-driven curling soft finger (print in TPU).

How it works:
  * The dorsal (top) side is a continuous thin skin -- the strain-limiting layer.
  * The ventral (inner) side has V-notches between segments. Pulling a tendon
    that runs along the ventral side shortens it, the notches close, and the
    finger CURLS toward the ventral side -- wrapping around whatever it's on.
  * One servo pulls the tendons of ALL fingers at once, so the whole "hand" of
    tentacles closes together and gathers/wraps the laundry.
  * The tendon threads through a channel near the ventral edge and ties off at
    the tip.

Print notes: TPU 95A, ~0.2 mm layers, 3-4 walls, 15-20% infill. Lay the finger
on its dorsal (flat top) face so the notches open upward -- no supports.
Ventral face is flat for a clean first layer.
"""

from __future__ import annotations

import cadquery as cq

from ..params import (
    FINGER_LEN, FINGER_BASE, FINGER_RIBS, DYNEEMA_DIA, SCREW_M3, NOTCH_GAP,
    FINGER_SHOULDER_T, FINGER_SHOULDER_GROW, FINGER_SHOULDER_Z0,
)

# Cross-section (X = width, Y = thickness; ventral face at y=0, dorsal at y=+H).
W_BASE = 16.0
W_TIP = 9.0
H_BASE = 13.0
H_TIP = 7.0
DORSAL_SKIN = 1.6      # continuous top skin left above the notch roots
# NOTCH_GAP is authoritative in cad/params.py (drum sizing derives from it) --
# import it rather than redefining a local copy (D5 single-source-of-truth).
TENDON_DIA = DYNEEMA_DIA + 0.8
TENDON_Y = 2.2         # tendon channel height above the ventral face
BASE_SOLID = 12.0      # solid (un-notched) length at the mounting base


def make() -> cq.Workplane:
    L = FINGER_LEN

    # Tapered bar: loft base rect -> tip rect. Ventral face flat at y=0.
    finger = (
        cq.Workplane("XY")
        .rect(W_BASE, H_BASE, centered=(True, False))
        .workplane(offset=L)
        .rect(W_TIP, H_TIP, centered=(True, False))
        .loft(combine=True)
    )

    # Base shoulder (D5, corrected placement): local z=0 is the MOUNTING END
    # face, which sits flush with the hub TOP. The slot engagement is
    # z in [0, FINGER_SHOULDER_Z0] (= hub thickness), so the oversize shoulder
    # must start at FINGER_SHOULDER_Z0 -- just below the slot -- where it bears
    # on the hub UNDERSIDE. (Placing it at z=0 would block insertion entirely:
    # the lip is wider than the slot, so nothing would engage.)
    shoulder = (
        cq.Workplane("XY")
        .rect(
            W_BASE + 2 * FINGER_SHOULDER_GROW,
            H_BASE + 2 * FINGER_SHOULDER_GROW,
            centered=(True, False),
        )
        .translate((0, -FINGER_SHOULDER_GROW, 0))
        .extrude(FINGER_SHOULDER_T)
        .translate((0, 0, FINGER_SHOULDER_Z0))
    )
    finger = finger.union(shoulder)

    # V-notches from the ventral side, between segments (skip the solid base).
    usable = L - BASE_SOLID
    n = FINGER_RIBS
    for i in range(1, n + 1):
        zc = BASE_SOLID + usable * i / (n + 1)
        # Notch depth leaves DORSAL_SKIN of material at the top.
        h_here = H_BASE + (H_TIP - H_BASE) * (zc / L)
        depth = h_here - DORSAL_SKIN
        # Triangular wedge in the (Z,Y) plane, apex up, extruded across width.
        wedge = (
            cq.Workplane("XZ")   # X across width, work in Z-Y via later placement
        )
        # Build the wedge profile in Y-Z plane and extrude along X.
        prof = (
            cq.Workplane("YZ")
            .polyline([(0, zc - NOTCH_GAP / 2), (0, zc + NOTCH_GAP / 2), (depth, zc)])
            .close()
            .extrude(W_BASE, both=True)
        )
        finger = finger.cut(prof)

    # Tendon channel along the length near the ventral edge.
    channel = (
        cq.Workplane("XY")
        .transformed(offset=(0, TENDON_Y, 0))
        .circle(TENDON_DIA / 2)
        .extrude(L)
    )
    finger = finger.cut(channel)

    # Tip tie-off: a small cross hole near the tip through the tendon height.
    tie = (
        cq.Workplane("XZ")
        .workplane(offset=-W_BASE)
        .center(0, 0)  # placeholder; positioned via translate below
        .circle(TENDON_DIA / 2)
        .extrude(W_BASE * 2)
    )
    tie = tie.translate((0, TENDON_Y, L - 5))
    finger = finger.cut(tie)

    # Base mounting: one axial M3 tap hole in the base end face (z=0), offset to
    # the dorsal side so it clears the tendon channel. The finger seats in a
    # rectangular hub pocket (anti-rotation) and this screw retains it.
    from ..params import SCREW_M3_TAP
    base_screw = (
        cq.Workplane("XY")
        .transformed(offset=(0, H_BASE * 0.62, 0))
        .circle(SCREW_M3_TAP / 2)
        .extrude(11)
    )
    finger = finger.cut(base_screw)
    return finger


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "tentacle_finger"))
