"""
Camera mount -- a small bracket for a Raspberry Pi Camera Module, pointing down
from the end-effector for a close-up "confirm before grabbing" view.

Why a Pi Camera on the effector (not the C920): the C920 is heavy and bulky --
better used as the fixed OVERHEAD "find" camera. A light Pi Camera rides on the
moving effector for the close-up confirm. See docs/VISION.md (hybrid camera plan).

The Pi Camera Module PCB is 25 x 24 mm with 4 mounting holes on a
21 x 12.5 mm pattern (M2). This bracket clips to the effector frame edge and
holds the PCB facing down.

Print flat; no supports.
"""

from __future__ import annotations

import cadquery as cq

from ..params import SCREW_M3

PCB = 25.0
HOLE_X = 21.0
HOLE_Y = 12.5
M2 = 2.4
PLATE_T = 3.0
ARM_H = 16.0
ARM_T = 4.0


def make() -> cq.Workplane:
    # Face plate the camera bolts to (with a lens clearance window).
    plate = cq.Workplane("XY").rect(PCB + 6, PCB + 6).extrude(PLATE_T)
    plate = plate.faces(">Z").workplane().rect(16, 16).cutThruAll()  # lens window
    plate = (
        plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .rect(HOLE_X, HOLE_Y, forConstruction=True).vertices()
        .hole(M2)
    )

    # An arm that stands the plate off and bolts to the effector frame edge.
    arm = (
        cq.Workplane("XY")
        .center(0, (PCB + 6) / 2 + ARM_T / 2)
        .box(PCB + 6, ARM_T, ARM_H, centered=(True, True, False))
    )
    # Two mounting holes through the arm (into the frame edge).
    arm = (
        arm.faces(">Y").workplane(centerOption="CenterOfBoundBox")
        .pushPoints([(10, ARM_H / 2 - 4), (-10, ARM_H / 2 - 4)])
        .hole(SCREW_M3 + 0.4)
    )
    return plate.union(arm)


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "camera_mount"))
