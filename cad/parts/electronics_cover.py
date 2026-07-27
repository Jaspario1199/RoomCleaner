"""
Electronics cover -- open-bottom box that shrouds the ESP32, 2S LiPo, and
buck converter mounted on top of the 92 mm end-effector plate (D7).

How it works:
  * Inner cavity (94 x 94 x COVER_INNER_H) clears the tallest item on the
    plate -- the inverted MG996R body standing SERVO_BODY_ABOVE above the
    plate -- plus wiring headroom.
  * Walls and roof are COVER_WALL thick; the roof is the top skin, there is
    no separate lid (open face is the bottom, over the plate).
  * All four vertical corners get a large 45 deg chamfer (leg
    COVER_CORNER_NOTCH) so the box clears the frame's corner cable-tie-off
    cones. The chamfer leg is deliberately much bigger than the wall
    thickness -- it is meant to notch well past the wall at each corner,
    not just knock the corner off (see cad/interfaces.py D7 note).
  * Four mounting tabs at the bottom rim, flush with the outer wall face so
    each unions cleanly onto the wall, carry a clearance hole at the shared
    COVER_SCREW_POS radius on the +/-X and +/-Y axes -- one tab per plate
    edge midpoint, matching cad/interfaces.py.
  * A round switch hole in the -Y wall and a USB slot in the +Y wall give
    panel access to the power switch and the ESP32 USB port without pulling
    the cover. Exact panel-cutout sizes/heights are local to this part (not
    shared mating interfaces), so they are plain named constants here
    rather than cad/interfaces.py entries.

Coordinates: open face at Z=0 (sits down over the plate top), roof at
Z = COVER_INNER_H + COVER_WALL.

Print orientation: open face UP, roof down on the bed. The roof is then a
flat skin printing directly on the bed, the walls are clean vertical
perimeters, and the corner chamfers/tab holes/switch hole/USB slot all cut
across print layers or lie in a printed wall -- none need supports.
(Printing open-face-down would put the switch/USB cutouts and the
protruding tabs against the bed, fighting the first-layer/brim.)
"""

from __future__ import annotations

import cadquery as cq

from ..params import SCREW_M3, COVER_SCREW_POS, COVER_INNER_H, COVER_CORNER_NOTCH, COVER_WALL

CAVITY_XY = 94.0                        # mm, inner cavity footprint (spec)
OUTER_XY = CAVITY_XY + 2 * COVER_WALL   # mm, outer footprint
OUTER_H = COVER_INNER_H + COVER_WALL    # mm, overall height (roof included)

TAB_RADIAL = 13.0    # mm, tab length along its mounting axis, flush with the outer wall face
TAB_TANGENT = 10.0   # mm, tab width across
TAB_H = 3.0           # mm, tab thickness

SWITCH_HOLE_D = 12.5  # mm, panel-mount switch bore (spec)
SWITCH_Z = 18.0        # mm, switch hole center height above the bottom rim (spec, ~18 mm)

USB_SLOT_W = 13.0      # mm, USB panel slot width (spec)
USB_SLOT_H = 8.0        # mm, USB panel slot height (spec)
USB_Z = 10.0             # mm, USB slot center height above the bottom rim (spec, ~10 mm)


def _y_axis_cylinder(radius: float, length: float, x: float, y0: float, z: float) -> cq.Workplane:
    """A cylinder whose axis runs along global +Y (from y0 to y0+length),
    used to cut a round hole through the +Y/-Y walls without depending on
    face-selection order."""
    return (
        cq.Workplane("XY")
        .circle(radius)
        .extrude(length)
        .rotate((0, 0, 0), (1, 0, 0), -90)   # +Z extrusion axis -> +Y
        .translate((x, y0, z))
    )


def make() -> cq.Workplane:
    half = OUTER_XY / 2

    cover = cq.Workplane("XY").box(OUTER_XY, OUTER_XY, OUTER_H, centered=(True, True, False))
    cover = cover.edges("|Z").chamfer(COVER_CORNER_NOTCH)

    cavity = cq.Workplane("XY").box(CAVITY_XY, CAVITY_XY, COVER_INNER_H, centered=(True, True, False))
    cover = cover.cut(cavity)

    # Four mounting tabs at the bottom rim, one per plate-edge midpoint.
    # (center_x, center_y, x_len, y_len, hole_x, hole_y)
    tab_specs = [
        (half - TAB_RADIAL / 2, 0, TAB_RADIAL, TAB_TANGENT, COVER_SCREW_POS, 0),
        (-(half - TAB_RADIAL / 2), 0, TAB_RADIAL, TAB_TANGENT, -COVER_SCREW_POS, 0),
        (0, half - TAB_RADIAL / 2, TAB_TANGENT, TAB_RADIAL, 0, COVER_SCREW_POS),
        (0, -(half - TAB_RADIAL / 2), TAB_TANGENT, TAB_RADIAL, 0, -COVER_SCREW_POS),
    ]
    for cx, cy, xlen, ylen, hx, hy in tab_specs:
        tab = (
            cq.Workplane("XY")
            .center(cx, cy)
            .rect(xlen, ylen)
            .extrude(TAB_H)
        )
        cover = cover.union(tab)

        hole = (
            cq.Workplane("XY")
            .center(hx, hy)
            .circle(SCREW_M3 / 2)
            .extrude(TAB_H + 2)
            .translate((0, 0, -1))
        )
        cover = cover.cut(hole)

    # Switch hole, centered on the -Y wall.
    switch = _y_axis_cylinder(SWITCH_HOLE_D / 2, 6, 0, -(half + 2), SWITCH_Z)
    cover = cover.cut(switch)

    # USB slot, centered on the +Y wall.
    usb = (
        cq.Workplane("XY")
        .center(0, half)
        .rect(USB_SLOT_W, 6)
        .extrude(USB_SLOT_H)
        .translate((0, 0, USB_Z - USB_SLOT_H / 2))
    )
    cover = cover.cut(usb)

    return cover


if __name__ == "__main__":
    from ..lib import export
    print(export(make(), "electronics_cover"))
