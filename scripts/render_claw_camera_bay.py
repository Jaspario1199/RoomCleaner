#!/usr/bin/python3
"""
Standardised renders of the claw camera bay -> renders/claw_camera_bay/

Run:  /usr/bin/python3 scripts/render_claw_camera_bay.py
Views (matplotlib painter's-algorithm renders, +Y up):
  assembly_iso.png          v6 assembly, original box replaced by box+bay (bay in blue, cover orange)
  assembly_narrow_side.png  view from the bay (narrow, -Z) side, looking +Z
  assembly_top.png          top view looking down the tube
  bay_iso.png / bay_iso_no_cover.png / bay_underside_lens.png / bay_section_front.png
                            close-ups of the bay on the box
(camera_view_floor_footprint.png comes from scripts/analyze_claw_camera_bay.py)
"""

from __future__ import annotations

import os
import sys

import cadquery as cq

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad.parts import claw_camera_bay as B            # noqa: E402
from cad.v6_loader import load_v6, find, BOX_NAME     # noqa: E402
from cad.mesh_tools import tessellate, render         # noqa: E402

OUT = os.path.join(REPO, "renders", "claw_camera_bay")
GREY = (0.72, 0.72, 0.75)
BLUE = (0.25, 0.55, 0.88)
ORANGE = (0.95, 0.5, 0.15)


def main():
    os.makedirs(OUT, exist_ok=True)
    parts = load_v6()
    box = find(parts, BOX_NAME)
    ox, oy, oz = B.BAY_ORIGIN_WORLD
    box_bay = cq.Workplane().add(box).translate((-ox, -oy, -oz))
    comb = B.combine(box_bay)
    cover = B.make_cover()
    to_world = cq.Location(cq.Vector(ox, oy, oz))
    comb_w = comb.val().moved(to_world)
    cover_w = cover.val().moved(to_world)

    meshes = []
    for n, s in parts:
        if n != BOX_NAME:
            meshes.append(tessellate(s, 1.0, 0.5) + (GREY, 1.0))
    meshes.append(tessellate(comb_w, 0.5, 0.4) + (BLUE, 1.0))
    meshes.append(tessellate(cover_w, 0.2, 0.3) + (ORANGE, 1.0))

    # whole assembly: bounds are cubic around the claw
    lo = (ox - 330, 560, oz - 330)
    hi = (ox + 330, 1200, oz + 330)
    # plot mapping (up='y'): plot X = world x, plot Y = -world z, plot Z = world y.
    # camera azimuth 90 => camera on the plot +Y side = world -Z side (the bay side).
    render(meshes, f"{OUT}/assembly_iso.png", 22, 55, "v6 + camera bay (bay on -Z narrow side)",
           bounds=((ox - 300, 580, oz - 300), (ox + 300, 1180, oz + 300)), up="y")
    render(meshes, f"{OUT}/assembly_narrow_side.png", 0, 90,
           "View from the narrow (-Z) side: camera bay at the top, looking down",
           bounds=((ox - 330, 560, oz - 330), (ox + 330, 1200, oz + 330)), up="y")
    render(meshes, f"{OUT}/assembly_top.png", 90, 90, "Top view along the tube axis",
           bounds=((ox - 150, 560, oz - 150), (ox + 150, 1200, oz + 150)), up="y")

    # close-ups: crop the combined box to the bay neighbourhood (boolean) so the
    # painter's sort only sees what matters.
    crop = (cq.Workplane("XY").box(110, 70, 90, centered=False)
            .translate((-55, -1, -115)))
    near = comb.intersect(crop).val().moved(to_world)
    nm = tessellate(near, 0.15, 0.25)
    cm = tessellate(cover_w, 0.15, 0.25)
    cb = ((ox - 60, oy - 2, oz - 118), (ox + 60, oy + 62, oz - 22))
    render([nm + (BLUE, 1.0), cm + (ORANGE, 1.0)], f"{OUT}/bay_iso.png", 28, 62,
           "Camera bay on the box (cover fitted)", bounds=cb, up="y", dpi=150)
    render([nm + (BLUE, 1.0)], f"{OUT}/bay_iso_no_cover.png", 42, 70,
           "Camera bay, cover removed (XIAO bay, fence, IMU posts, wire window side)",
           bounds=cb, up="y", dpi=150)
    render([nm + (BLUE, 1.0)], f"{OUT}/bay_underside_lens.png", -70, 80,
           "Underside: 15x15 lens window with 1 mm chamfer", bounds=cb, up="y", dpi=150)
    # vertical section through the bay (x = 0 plane), looking along +X
    half = (cq.Workplane("XY").box(60, 70, 90, centered=False).translate((0, -1, -115)))
    sec = comb.intersect(half).val().moved(to_world)
    sm = tessellate(sec, 0.12, 0.25)
    cs = cover.intersect(cq.Workplane("XY").box(60, 70, 90, centered=False)
                         .translate((0, -1, -115))).val().moved(to_world)
    render([sm + (BLUE, 1.0), tessellate(cs, 0.12, 0.25) + (ORANGE, 1.0)],
           f"{OUT}/bay_section_front.png", 12, 180, "Section through the bay centre (x = 0), seen from -X",
           bounds=((ox - 5, oy - 2, oz - 118), (ox + 55, oy + 62, oz - 22)), up="y", dpi=150)
    for f in sorted(os.listdir(OUT)):
        print(os.path.join(OUT, f))


if __name__ == "__main__":
    main()
