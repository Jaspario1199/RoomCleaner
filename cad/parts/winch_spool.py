"""
Winch spool -- the drum the Dyneema line winds onto, mounted on a motor shaft.

Design notes:
  * Two end flanges keep the line from walking off the drum.
  * Center bore matches the motor shaft, with an optional D-flat so it can't spin
    on the shaft, plus a radial M3 grub-screw hole to lock it on.
  * A line tie-off hole through the drum wall anchors the cable end.
  * Print upright (bore vertical) for a round bore; no supports needed.
"""

from __future__ import annotations

import cadquery as cq

from ..params import (
    MOTOR_SHAFT_DIA, MOTOR_SHAFT_FLAT, CLEARANCE, SCREW_M3_TAP, DYNEEMA_DIA,
    SPOOL_DRUM_DIA, SPOOL_LEN, SPOOL_FLANGE_DIA, SPOOL_FLANGE_THK,
)


def make() -> cq.Workplane:
    total_len = SPOOL_LEN + 2 * SPOOL_FLANGE_THK
    bore = MOTOR_SHAFT_DIA + CLEARANCE

    # Build along Z: bottom flange, drum, top flange as a stack of cylinders.
    spool = (
        cq.Workplane("XY")
        .circle(SPOOL_FLANGE_DIA / 2).extrude(SPOOL_FLANGE_THK)
        .faces(">Z").workplane()
        .circle(SPOOL_DRUM_DIA / 2).extrude(SPOOL_LEN)
        .faces(">Z").workplane()
        .circle(SPOOL_FLANGE_DIA / 2).extrude(SPOOL_FLANGE_THK)
    )

    # Through bore for the shaft.
    spool = (
        spool.faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .circle(bore / 2).cutThruAll()
    )

    # Optional D-flat: cut a slab off one side of the bore.
    if MOTOR_SHAFT_FLAT > 0:
        flat = (
            cq.Workplane("XY")
            .center(bore / 2 - MOTOR_SHAFT_FLAT, 0)
            .box(MOTOR_SHAFT_FLAT * 2, bore, total_len * 2, centered=(True, True, True))
        )
        spool = spool.cut(flat)

    # Radial grub-screw hole into the lower flange hub to lock onto the shaft.
    grub = (
        cq.Workplane("XZ")
        .workplane(offset=-SPOOL_FLANGE_DIA / 2)
        .center(0, SPOOL_FLANGE_THK / 2)
        .circle(SCREW_M3_TAP / 2)
        .extrude(SPOOL_FLANGE_DIA)  # drive inward toward the bore
    )
    spool = spool.cut(grub)

    # Line tie-off hole through the drum wall (near the drum center height).
    tie = (
        cq.Workplane("XZ")
        .workplane(offset=-SPOOL_DRUM_DIA)
        .center(0, SPOOL_FLANGE_THK + SPOOL_LEN / 2)
        .circle((DYNEEMA_DIA + 0.4) / 2)
        .extrude(SPOOL_DRUM_DIA * 2)
    )
    spool = spool.cut(tie)

    return spool


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "winch_spool"))
