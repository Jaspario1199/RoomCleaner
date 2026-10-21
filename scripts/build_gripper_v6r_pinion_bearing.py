#!/usr/bin/python3
"""
Build Jasper's 18T pinion with ONE 687 bearing pocket (his own compound pocket, cad/parts/gripper_v6r_pinion_bearing.py).

Run:  /usr/bin/python3 scripts/build_gripper_v6r_pinion_bearing.py [--no-render] [--no-mesh]

Writes  exports/step/gripper_v6r_pinion_1brg.step            (part frame: pocket mouth z = 0, servo face z = 16)
        exports/stl/gripper_v6r_pinion_1brg.stl              (print pose: pocket side UP, teeth / servo face on the bed)
        renders/gripper_v6r_gears/pinion_1brg_{iso,under,section}.png
        verification/gripper_v6r_pinion_1brg_numbers.json
Does not touch the four existing v6r exports or his source STEP.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys

import cadquery as cq

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                   # noqa: E402
from cad.mesh_tools import render, tessellate                 # noqa: E402
from cad.parts import gripper_v6r_gears as G                  # noqa: E402
from cad.parts import gripper_v6r_pinion_bearing as B         # noqa: E402
from cad.v6_loader import V6_STEP                             # noqa: E402

BASE = "gripper_v6r_pinion_1brg"
STEP = os.path.join(REPO, "exports", "step", BASE + ".step")
STL = os.path.join(REPO, "exports", "stl", BASE + ".stl")
REN = os.path.join(REPO, "renders", "gripper_v6r_gears")
JSON = os.path.join(REPO, "verification", BASE + "_numbers.json")
MESH_DELTAS = [0.0, 10.0, 20.0, 30.0, 45.0, 60.0, P.GRIPV6R_SWEEP_DEG, -10.0, -20.0, -30.0]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def bbl(s):
    b = s.BoundingBox()
    return [b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--no-mesh", action="store_true")
    args = ap.parse_args()
    sha0 = sha256(V6_STEP)
    s = B.make_pinion_1brg()
    his = G.home_pinion()
    os.makedirs(os.path.dirname(STEP), exist_ok=True)
    os.makedirs(os.path.dirname(STL), exist_ok=True)
    cq.exporters.export(cq.Workplane(obj=s), STEP)
    pp = B.print_pose_pocket_up(s)
    cq.exporters.export(cq.Workplane(obj=pp), STL, tolerance=0.02, angularTolerance=0.1)
    re = cq.importers.importStep(STEP).val()
    out = dict(
        valid=bool(s.isValid()), solids=len(s.Solids()), volume_mm3=s.Volume(), area_mm2=s.Area(),
        mass_g_petg=s.Volume() * P.GRIPV6R_DENSITY_PETG / 1000.0, bbox=bbl(s), stl_bbox_print_pose=bbl(pp),
        print_orientation="pocket side UP (rotated 180 deg about x; pocket mouth at the top, servo face z=16 and teeth on the bed)",
        his_volume_mm3=his.Volume(), his_mass_g_petg=his.Volume() * P.GRIPV6R_DENSITY_PETG / 1000.0,
        roundtrip=dict(valid=bool(re.isValid()), solids=len(re.Solids()),
                       volume_rel_diff=abs(re.Volume() - s.Volume()) / s.Volume(),
                       bbox_max_diff=max(abs(a - b) for a, b in zip(bbl(s), bbl(re)))))
    rem = B.removed_material()
    out["removed"] = dict(solids=len(rem.Solids()), volume_mm3=float(rem.Volume()), added_volume_mm3=B.added_material(),
                          volume_check=his.Volume() - s.Volume() - rem.Volume())
    # removed volume must lie entirely inside the pocket envelope (R<=R_COPY, z<=bore relief top)
    envelope = cq.Solid.makeCylinder(B.R_COPY, B.BORE_RELIEF_TOP_Z, cq.Vector(0, 0, 0))
    out["removed"]["outside_pocket_envelope_mm3"] = float(rem.cut(envelope).Volume()) if rem.cut(envelope).Solids() else 0.0
    out["donor_profile"] = {k: v for k, v in B.donor_profile().items() if k != "cyl_keys"}
    out["new_profile"] = {k: v for k, v in B.measure_pocket(s).items() if k != "cyl_keys"}
    out["pocket_vs_donor"] = B.pocket_vs_donor(s)
    out["walls"] = B.walls(B.donor_profile())
    on, _ = G._surface_census(s)
    out["bore_servo_side"] = dict(R=4.0, z0=12.0, z1=16.0, area_mm2=on.get((4.0, 12.0, 16.0), (0, 0.0))[1])
    if not args.no_mesh:
        out["mesh_3d"] = dict(rows=B.mesh_overlap_3d(MESH_DELTAS), control_3deg_overlap_mm3=B.mesh_control())
        print("mesh max overlap mm3:", max(max(r["pinion_compound"], r["pinion_follower"]) for r in out["mesh_3d"]["rows"]),
              "control:", out["mesh_3d"]["control_3deg_overlap_mm3"], flush=True)
    out["source_unchanged"] = sha0 == sha256(V6_STEP)
    with open(JSON, "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(json.dumps({k: out[k] for k in ("valid", "solids", "volume_mm3", "mass_g_petg", "bbox", "roundtrip", "removed",
                                          "walls", "pocket_vs_donor")}, indent=1, default=float))
    if not args.no_render:
        os.makedirs(REN, exist_ok=True)
        col = (0.35, 0.60, 0.85)
        V, F = tessellate(G.deep_copy(s), tol=0.03, ang=0.2)
        render([(V, F, col, 1.0)], os.path.join(REN, "pinion_1brg_iso.png"), 28, 35, title="pinion_1brg (iso, servo face up)")
        render([(V, F, col, 1.0)], os.path.join(REN, "pinion_1brg_under.png"), -50, 215, title="pinion_1brg (from below, pocket side)")
        half = cq.Solid.makeBox(60, 30, 40, cq.Vector(-30, 0, -10))          # y > 0 half removed
        sec = G.deep_copy(s).cut(half)
        Vs, Fs = tessellate(sec, tol=0.03, ang=0.2)
        render([(Vs, Fs, col, 1.0)], os.path.join(REN, "pinion_1brg_section.png"), 18, 90,
               title="pinion_1brg section through the axis (y=0)", bounds=((-17, -17, -1), (17, 17, 17)))
    assert out["source_unchanged"]


if __name__ == "__main__":
    main()
