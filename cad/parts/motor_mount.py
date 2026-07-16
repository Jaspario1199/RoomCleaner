"""
Motor mount -- an L-bracket that face-mounts a NEMA 17 stepper in a ceiling
corner. The motor bolts to the vertical face (4x M3), shaft pointing out toward
the room with the winch spool on it; the base plate screws up into the ceiling
(into a joist / solid block).

Print with the base flat on the bed and the face standing up; the gussets keep
it from needing supports. Use PETG for strength.

NOTE: the load-bearing CEILING screws that hold this bracket up must be METAL
into solid wood -- never a printed part (see cad/README.md).
"""

from __future__ import annotations

import cadquery as cq

from ..params import (
    NEMA17_FACE, NEMA17_HOLES, NEMA17_BOSS_DIA, SCREW_M3, CLEARANCE,
)

BASE_L = 56.0          # along X (width)
BASE_W = 52.0          # along Y (depth, into the corner)
T = 5.0                # plate thickness
FACE_H = 54.0          # vertical face height
PATTERN_Z = 30.0       # height of the NEMA 17 hole-pattern centre on the face
CEIL_SCREW = 4.5       # ceiling mounting screws (M4/lag clearance)


def make() -> cq.Workplane:
    half = NEMA17_HOLES / 2  # 15.5

    # Base plate.
    base = cq.Workplane("XY").box(BASE_L, BASE_W, T, centered=(True, True, False))
    # Ceiling mounting holes (4, near the front, away from the face).
    base = (
        base.faces(">Z").workplane()
        .pushPoints([(BASE_L / 2 - 8, BASE_W / 2 - 8), (-BASE_L / 2 + 8, BASE_W / 2 - 8),
                     (BASE_L / 2 - 8, -BASE_W / 2 + 20), (-BASE_L / 2 + 8, -BASE_W / 2 + 20)])
        .hole(CEIL_SCREW)
    )

    # Vertical face at the back edge (y = -BASE_W/2), plate thickness T in Y.
    face = (
        cq.Workplane("XY")
        .box(BASE_L, T, FACE_H, centered=(True, True, False))
        .translate((0, -BASE_W / 2 + T / 2, 0))
    )

    # NEMA 17 pattern on the face: central boss clearance + 4 M3 corners.
    boss = (
        cq.Workplane("XZ").workplane(offset=BASE_W)
        .center(0, PATTERN_Z).circle((NEMA17_BOSS_DIA + CLEARANCE) / 2)
        .extrude(-BASE_W * 2)
    )
    face = face.cut(boss)
    for dx in (-half, half):
        for dz in (-half, half):
            hole = (
                cq.Workplane("XZ").workplane(offset=BASE_W)
                .center(dx, PATTERN_Z + dz).circle((SCREW_M3 + 0.4) / 2)
                .extrude(-BASE_W * 2)
            )
            face = face.cut(hole)

    part = base.union(face)

    # Two side gussets (right triangles) bracing the face to the base.
    for sx in (BASE_L / 2 - T / 2, -BASE_L / 2 + T / 2):
        gusset = (
            cq.Workplane("YZ")
            .polyline([(-BASE_W / 2, 0),
                       (-BASE_W / 2 + 28, 0),
                       (-BASE_W / 2, 34)])
            .close()
            .extrude(T)
            .translate((sx - T / 2, 0, 0))
        )
        part = part.union(gusset)

    return part


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "motor_mount"))
