#!/usr/bin/python3
"""
Build the claw camera bay onto the v6 electrical box and write exports.

Run:  /usr/bin/python3 scripts/build_claw_camera_bay.py
Reads (read-only): solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP
Writes:
  exports/step/gripper_electric_housing_with_camera_bay.step   box + bay (v6 world frame)
  exports/step/claw_camera_bay_cover.step                       access cover (v6 world frame)
  exports/step/claw_camera_bay_body.step                        bay feature alone (review only)
  exports/step/gripper_v6_with_camera_bay_preview.step          v6 assembly, original box replaced
  exports/stl/*.stl                                             print-orientation STLs (+Z up, z min = 0;
                                                                cover has its flat outer face on the bed)
The original v6 STEP is never modified.
"""

from __future__ import annotations

import os
import sys

import cadquery as cq

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad.parts import claw_camera_bay as B           # noqa: E402
from cad.v6_loader import load_v6, find, BOX_NAME     # noqa: E402

STEP_DIR = os.path.join(REPO, "exports", "step")
STL_DIR = os.path.join(REPO, "exports", "stl")
PETG = 1.27   # g/cm3 (cad/materials.py)


def bay_to_world(shape: cq.Shape) -> cq.Shape:
    return shape.moved(cq.Location(cq.Vector(*B.BAY_ORIGIN_WORLD)))


def bay_to_print(wp: cq.Workplane) -> cq.Workplane:
    """Rotate +90 deg about X so bay +Y (up) becomes print +Z."""
    return wp.rotate((0, 0, 0), (1, 0, 0), 90)


def cover_to_print(wp: cq.Workplane) -> cq.Workplane:
    """Cover print pose: outer (top) face flat on the bed, lip/pegs/corral up, z min = 0."""
    r = bay_to_print(wp).rotate((0, 0, 0), (1, 0, 0), 180)
    zmin = r.val().BoundingBox().zmin
    return r.translate((0, 0, -zmin))


def build():
    os.makedirs(STEP_DIR, exist_ok=True)
    os.makedirs(STL_DIR, exist_ok=True)
    parts = load_v6()
    box_world = find(parts, BOX_NAME)
    ox, oy, oz = B.BAY_ORIGIN_WORLD
    box_bay = cq.Workplane().add(box_world).translate((-ox, -oy, -oz))
    box_vol = box_world.Volume()

    body, cover = B.make()
    combined = B.combine(box_bay)
    assert combined.val().isValid() and len(combined.solids().vals()) == 1

    added_vol = combined.val().Volume() - box_vol
    cover_vol = cover.val().Volume()
    print(f"box volume            {box_vol:10.0f} mm3")
    print(f"combined volume       {combined.val().Volume():10.0f} mm3")
    print(f"added bay (net) vol   {added_vol:10.0f} mm3 = {added_vol * PETG / 1000:.1f} g PETG solid")
    print(f"cover volume          {cover_vol:10.0f} mm3 = {cover_vol * PETG / 1000:.1f} g")
    print(f"bay+cover solid mass  {(added_vol + cover_vol) * PETG / 1000:.1f} g (target <= 30 g)")

    outputs = {}
    world = {
        "gripper_electric_housing_with_camera_bay": bay_to_world(combined.val()),
        "claw_camera_bay_cover": bay_to_world(cover.val()),
        "claw_camera_bay_body": bay_to_world(body.val()),
    }
    for name, shp in world.items():
        path = os.path.join(STEP_DIR, name + ".step")
        cq.exporters.export(cq.Workplane().add(shp), path)
        outputs[name] = path
    printed = {
        "gripper_electric_housing_with_camera_bay": combined,
        "claw_camera_bay_cover": cover,
        "claw_camera_bay_body": body,
    }
    for name, wp in printed.items():
        pose = cover_to_print(wp) if name == "claw_camera_bay_cover" else bay_to_print(wp)
        cq.exporters.export(pose, os.path.join(STL_DIR, name + ".stl"),
                            tolerance=0.05, angularTolerance=0.2)

    # preview assembly: v6 with the original box replaced by box+bay
    assy = cq.Assembly(name="gripper_v6_with_camera_bay")
    for idx, (n, shp) in enumerate(parts):
        if n == BOX_NAME:
            assy.add(cq.Workplane().add(world["gripper_electric_housing_with_camera_bay"]),
                     name="Gripper_Electric_Housing_with_Camera_Bay",
                     color=cq.Color(0.25, 0.55, 0.85))
        else:
            assy.add(cq.Workplane().add(shp), name=f"{idx:02d}_" + n.replace(" ", "_"),
                     color=cq.Color(0.7, 0.7, 0.72))
    assy.add(cq.Workplane().add(world["claw_camera_bay_cover"]), name="Camera_Bay_Cover",
             color=cq.Color(0.9, 0.45, 0.15))
    apath = os.path.join(STEP_DIR, "gripper_v6_with_camera_bay_preview.step")
    assy.save(apath, "STEP")
    outputs["assembly"] = apath

    # STEP round trip
    print("--- STEP round trip ---")
    for name in ("gripper_electric_housing_with_camera_bay", "claw_camera_bay_cover",
                 "claw_camera_bay_body"):
        re = cq.importers.importStep(outputs[name]).val()
        src = world[name]
        bb0, bb1 = src.BoundingBox(), re.BoundingBox()
        dv = abs(re.Volume() - src.Volume()) / src.Volume()
        db = max(abs(a - b) for a, b in ((bb0.xmin, bb1.xmin), (bb0.xmax, bb1.xmax),
                                         (bb0.ymin, bb1.ymin), (bb0.ymax, bb1.ymax),
                                         (bb0.zmin, bb1.zmin), (bb0.zmax, bb1.zmax)))
        print(f"{name}: vol {src.Volume():.0f} -> {re.Volume():.0f} (rel {dv:.2e}), "
              f"bbox max diff {db:.4f} mm, solids {len(re.Solids())}")
    asm = cq.importers.importStep(apath)
    solids = asm.val().Solids() if asm.vals() else []
    tot = sum(s.Volume() for s in asm.solids().vals())
    expect = sum(s.Volume() for n, s in parts if n != BOX_NAME) + \
        world["gripper_electric_housing_with_camera_bay"].Volume() + world["claw_camera_bay_cover"].Volume()
    print(f"assembly STEP: {len(asm.solids().vals())} solids, total volume {tot:.0f} "
          f"vs expected {expect:.0f} (rel {abs(tot - expect) / expect:.2e})")
    return outputs


if __name__ == "__main__":
    out = build()
    for k, v in out.items():
        print(k, "->", v)
