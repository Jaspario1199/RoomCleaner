"""
Tendon drum -- mounts on the MG996R servo horn and winds the five finger
tendons to curl the claw (D4, C1/C2).

How it works:
  * Bottom flange carries the five tendon tie-offs, through-drilled at the
    core radius so each Dyneema line leaves right where it starts wrapping
    the core, 72 deg pitch (DRUM_TIEOFF_HOLES).
  * Core radius is sized in calculations/claw_integration.md (C2) so the
    servo's 120 deg usable throw winds >= 27 mm of tendon (C1).
  * Top flange is identical in size but carries NO tie-off holes -- it only
    retains the wound tendon and carries the horn interface.
  * Horn interface (top face): a shallow pocket nests the MG996R round horn,
    four screw holes match the horn's bolt circle, and a central clearance
    hole passes the horn's factory screw. All three horn-side holes run the
    FULL drum height so a screwdriver can reach them from underneath, back
    through the hub bore, once the drum is inside the assembled claw.

Coordinates: built along +Z, bottom flange bottom face at Z=0 (this is the
face the tendons are tied off against). Tie-offs face DOWN so the tendons
are strung and tensioned through the hub bore -- do that BEFORE driving the
horn screws up from below into the horn at the top.

Print vertical (axis on Z), flange down; round profile needs no supports.
"""

from __future__ import annotations

import math
import cadquery as cq

from ..params import (
    DRUM_CORE_R, DRUM_CORE_H, DRUM_FLANGE_R, DRUM_FLANGE_T,
    DRUM_TIEOFF_HOLES, DRUM_TIEOFF_HOLE_D,
    HORN_POCKET_DIA, HORN_POCKET_T, HORN_SCREW_CIRCLE, HORN_SCREW_HOLE,
)

# Central clearance hole for the MG996R horn's own factory screw. This is a
# property of the horn/drum pair only (not a shared assembly interface), so
# it stays a local constant rather than living in cad/interfaces.py.
HORN_CLEARANCE_HOLE = 6.5   # mm

# Small overcut so the tie-off holes break cleanly through the bottom
# flange face instead of risking a witness membrane exactly at the
# flange/core boundary.
TIEOFF_OVERCUT = 0.4        # mm


def make() -> cq.Workplane:
    drum = (
        cq.Workplane("XY")
        .circle(DRUM_FLANGE_R).extrude(DRUM_FLANGE_T)
        .faces(">Z").workplane()
        .circle(DRUM_CORE_R).extrude(DRUM_CORE_H)
        .faces(">Z").workplane()
        .circle(DRUM_FLANGE_R).extrude(DRUM_FLANGE_T)
    )

    # Tendon tie-off holes: through the BOTTOM flange only, at the core
    # radius, 72 deg pitch (five tendons, one per finger).
    tie_pts = [
        (
            DRUM_CORE_R * math.cos(2 * math.pi * i / DRUM_TIEOFF_HOLES),
            DRUM_CORE_R * math.sin(2 * math.pi * i / DRUM_TIEOFF_HOLES),
        )
        for i in range(DRUM_TIEOFF_HOLES)
    ]
    drum = (
        drum.faces("<Z").workplane(centerOption="CenterOfBoundBox")
        .pushPoints(tie_pts)
        .hole(DRUM_TIEOFF_HOLE_D, DRUM_FLANGE_T + TIEOFF_OVERCUT)
    )

    # Horn screw holes and central clearance hole: cut FIRST, while the top
    # face is still a plain flat disc, so the workplane centers unambiguously
    # on the drum axis. Both run the full drum height (see docstring).
    screw_pts = [
        (
            HORN_SCREW_CIRCLE / 2 * math.cos(2 * math.pi * i / 4),
            HORN_SCREW_CIRCLE / 2 * math.sin(2 * math.pi * i / 4),
        )
        for i in range(4)
    ]
    drum = (
        drum.faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .pushPoints(screw_pts)
        .hole(HORN_SCREW_HOLE)
    )
    drum = (
        drum.faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .circle(HORN_CLEARANCE_HOLE / 2)
        .cutThruAll()
    )

    # Horn pocket: shallow blind pocket in the top face that nests the round
    # horn, cut last so it doesn't disturb the face selection above.
    drum = (
        drum.faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .circle(HORN_POCKET_DIA / 2)
        .cutBlind(-HORN_POCKET_T)
    )

    return drum


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "tendon_drum"))
