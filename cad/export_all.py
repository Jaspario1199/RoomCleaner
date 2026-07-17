"""
Regenerate every RoomCleaner printed part: STEP + STL + preview PNG.

    python -m cad.export_all

Outputs land in cad/step, cad/stl, cad/previews. Also renders an assembled
end-effector preview (frame + hub + fingers + camera mount) so you can see how
the gripper goes together.
"""

from __future__ import annotations

import importlib
import math
import os

import numpy as np
import cadquery as cq

from .lib import export, render_stl, PREVIEW_DIR, STL_DIR

PARTS = [
    "winch_spool",
    "motor_mount",
    "corner_guide",
    "effector_frame",
    "tentacle_hub",
    "tentacle_finger",
    "camera_mount",
    "camera_mount_overhead",
]


def build_all() -> dict:
    results = {}
    for name in PARTS:
        mod = importlib.import_module(f"cad.parts.{name}")
        solid = mod.make()
        results[name] = export(solid, name)
        dims = solid.val().BoundingBox()
        print(f"  {name:16s}  {dims.xlen:5.1f} x {dims.ylen:5.1f} x {dims.zlen:5.1f} mm")
    return results


def build_assembly() -> str:
    """Compose the end-effector to show the tentacle gripper assembled."""
    frame_mod = importlib.import_module("cad.parts.effector_frame")
    hub_mod = importlib.import_module("cad.parts.tentacle_hub")
    finger_mod = importlib.import_module("cad.parts.tentacle_finger")

    frame = frame_mod.make()
    hub = hub_mod.make().translate((0, 0, -hub_mod.HUB_THK - 2))

    asm = frame.union(hub)

    # Place fingers hanging from the hub pockets, curled slightly inward.
    n = hub_mod.N_FINGERS
    pocket_r = hub_mod.HUB_DIA / 2 - hub_mod.RIM_INSET - hub_mod.POCKET_H / 2
    finger = finger_mod.make()
    # Finger length runs +Z from its base; flip so it hangs down (-Z).
    finger = finger.rotate((0, 0, 0), (1, 0, 0), 180)
    z_top = -hub_mod.HUB_THK - 2 + hub_mod.HUB_THK - hub_mod.POCKET_DEPTH
    for i in range(n):
        deg = 360 * i / n
        f = (
            finger
            .rotate((0, 0, 0), (0, 0, 1), deg + 90)
            .translate((pocket_r * math.cos(math.radians(deg)),
                        pocket_r * math.sin(math.radians(deg)),
                        z_top))
        )
        asm = asm.union(f)

    path = os.path.join(STL_DIR, "_assembly.stl")
    cq.exporters.export(asm, path, tolerance=0.08, angularTolerance=0.3)
    return render_stl(path, os.path.join(PREVIEW_DIR, "assembly.png"),
                      "end-effector (tentacle gripper) assembled")


if __name__ == "__main__":
    print("Building parts:")
    build_all()
    print("Building assembly preview...")
    print(" ", build_assembly())
    print("Done. STEP files in cad/step, STLs in cad/stl, previews in cad/previews.")
