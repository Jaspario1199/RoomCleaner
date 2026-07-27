"""
Standoff -- the round column that joins the end-effector frame to the
tentacle hub (D3/D6).

How it works:
  * A plain cylindrical column, OD = STANDOFF_OD, length = STANDOFF_LEN
    (frame underside -> hub top face, per cad/interfaces.py).
  * Both end faces get a coaxial heat-set insert pocket so an M3 screw
    threads in from the frame side AND from the hub side -- no pass-through
    hardware needed. Insert bore is the shared INSERT_M3_HOLE (cad/params.py);
    the 6.5 mm pocket depth is local to this part (sized for the standard
    ~4-5 mm brass M3 insert plus margin), not a shared mating dimension, so
    it is not duplicated into cad/interfaces.py.
  * Qty 4 per claw. The frame/hub parts place them on the shared
    HUB_MOUNT_R bolt circle (cad/interfaces.py) at STANDOFF_ANGLES_DEG,
    chosen to clear the 5 finger pockets at 72 deg pitch (see
    calculations/claw_integration.md C5).

Print vertical (axis on Z, either end face down on the bed); a round
column needs no supports.
"""

from __future__ import annotations

import cadquery as cq

from ..params import STANDOFF_OD, STANDOFF_LEN, INSERT_M3_HOLE

# Local to this part: not a shared mating dimension (see docstring).
INSERT_POCKET_DEPTH = 6.5   # mm, blind pocket depth for the M3 heat-set insert


def make() -> cq.Workplane:
    standoff = (
        cq.Workplane("XY")
        .circle(STANDOFF_OD / 2)
        .extrude(STANDOFF_LEN)
    )

    # Coaxial insert pocket in the bottom face (Z=0, frame side).
    standoff = (
        standoff.faces("<Z").workplane(centerOption="CenterOfBoundBox")
        .circle(INSERT_M3_HOLE / 2)
        .cutBlind(-INSERT_POCKET_DEPTH)
    )

    # Coaxial insert pocket in the top face (Z=STANDOFF_LEN, hub side).
    standoff = (
        standoff.faces(">Z").workplane(centerOption="CenterOfBoundBox")
        .circle(INSERT_M3_HOLE / 2)
        .cutBlind(-INSERT_POCKET_DEPTH)
    )

    return standoff


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "standoff"))
