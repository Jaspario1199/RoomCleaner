"""
Regenerate every RoomCleaner printed part: STEP + STL + preview PNG.

    python -m cad.export_all

Outputs land in cad/step, cad/stl, cad/previews. Also renders an assembled
end-effector preview (frame + standoffs + hub + fingers + drum -- the real
claw stack-up, D2-D7) so you can see how the gripper goes together, and
exports the full assembly STEP (mechanism + electronics cover) for
SOLIDWORKS handoff.
"""

from __future__ import annotations

import importlib
import math
import os

import numpy as np
import cadquery as cq

from .lib import export, render_stl, PREVIEW_DIR, STL_DIR, STEP_DIR
from .params import HUB_MOUNT_R, STANDOFF_ANGLES_DEG, STANDOFF_LEN, EFFECTOR_THK

PARTS = [
    "winch_spool",
    "motor_mount",
    "corner_guide",
    "effector_frame",
    "tentacle_hub",
    "tentacle_finger",
    "camera_mount",
    "camera_mount_overhead",
    "standoff",
    "tendon_drum",
    "electronics_cover",
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


# Drum top-face target Z (frame local frame: plate z in [0, EFFECTOR_THK],
# frame underside at z=0). This is the only stack-up number not already
# carried by cad/interfaces.py -- it places the horn pocket just below the
# plate underside, clearing the inverted servo's spline (D2/D4).
DRUM_TOP_Z = -6.0


def placed_components() -> dict:
    """Build every claw component and place it in the claw assembly per the
    real standoff/hub/drum/cover stack-up (cad/interfaces.py D2-D7;
    DECISIONS.md D3-D7). All positions are expressed in the effector_frame's
    own local/build frame: plate z in [0, EFFECTOR_THK], corner bosses to
    z=EFFECTOR_THK+3, frame UNDERSIDE (where the standoffs attach) at z=0.

    Returns a dict of individually-positioned solids (NOT unioned), so
    callers can both compose the final assembly and independently run
    pairwise interference/clearance checks on the untouched geometry.
    """
    frame_mod = importlib.import_module("cad.parts.effector_frame")
    standoff_mod = importlib.import_module("cad.parts.standoff")
    hub_mod = importlib.import_module("cad.parts.tentacle_hub")
    finger_mod = importlib.import_module("cad.parts.tentacle_finger")
    drum_mod = importlib.import_module("cad.parts.tendon_drum")
    cover_mod = importlib.import_module("cad.parts.electronics_cover")

    parts = {"frame": frame_mod.make()}

    # Standoffs x4: built z in [0, STANDOFF_LEN] -> translate z=-STANDOFF_LEN
    # so they hang from the frame underside (z=0) down to the hub top face
    # (z=-STANDOFF_LEN), on the shared HUB_MOUNT_R bolt circle at
    # STANDOFF_ANGLES_DEG (D3/D6 -- same source the frame and hub already
    # used for their own mounting holes).
    for a in STANDOFF_ANGLES_DEG:
        x = HUB_MOUNT_R * math.cos(math.radians(a))
        y = HUB_MOUNT_R * math.sin(math.radians(a))
        parts[f"standoff_{a:g}"] = standoff_mod.make().translate((x, y, -STANDOFF_LEN))

    # Hub: built z in [0, HUB_THK] -> translate so its TOP face lands on the
    # standoff bottom (z=-STANDOFF_LEN), i.e. hub occupies
    # [-(STANDOFF_LEN+HUB_THK), -STANDOFF_LEN].
    hub_z = -(STANDOFF_LEN + hub_mod.HUB_THK)
    parts["hub"] = hub_mod.make().translate((0, 0, hub_z))

    # Fingers x5: rotate 180 deg about X so the mounting end (local z=0)
    # stays "up" and the tip points down, then translate z=-STANDOFF_LEN so
    # the mounting-end face lands FLUSH on the hub TOP face. The
    # un-shouldered base solid (local z in [0, BASE_SOLID] == [0, HUB_THK])
    # then exactly fills the through-slot [-(STANDOFF_LEN+HUB_THK),
    # -STANDOFF_LEN] and the oversize shoulder (local z in
    # [HUB_THK, HUB_THK+FINGER_SHOULDER_T]) lands just below it, bearing on
    # the hub underside (D5). Position/orientation: same 5-pocket, 72 deg
    # convention as the pre-standoff build_assembly -- rotate about Z by
    # (deg+90) after the X-flip so the ventral (notched) face ends up
    # pointing at the hub axis.
    n = hub_mod.N_FINGERS
    pocket_r = hub_mod.HUB_DIA / 2 - hub_mod.RIM_INSET - hub_mod.POCKET_H / 2
    # The finger's local frame is NOT centered on its own axis in the
    # ventral/dorsal (Y) direction -- W_BASE is centered about local x=0, but
    # H_BASE runs from local y=0 (ventral face) to y=H_BASE (dorsal face), so
    # the cross-section centroid sits H_BASE/2 off the local origin. After
    # the X-flip + (deg+90) Z-rotate below, that offset lands the
    # cross-section center at radius H_BASE/2 in the direction of `deg` --
    # so the translate radius must be reduced by H_BASE/2 to actually center
    # the finger's base solid in the hub pocket (verified: an uncorrected
    # translate at the raw pocket_r pushes the finger ~H_BASE/2 = 6.5 mm too
    # far outboard, overlapping the hub by ~445 mm^3 -- see
    # verification/assembly_report.md check 3a).
    finger_r = pocket_r - finger_mod.H_BASE / 2
    finger_flip = finger_mod.make().rotate((0, 0, 0), (1, 0, 0), 180)
    for i in range(n):
        deg = 360 * i / n
        f = (
            finger_flip
            .rotate((0, 0, 0), (0, 0, 1), deg + 90)
            .translate((finger_r * math.cos(math.radians(deg)),
                        finger_r * math.sin(math.radians(deg)),
                        -STANDOFF_LEN))
        )
        parts[f"finger_{i}"] = f

    # Tendon drum: built z in [0, 2*DRUM_FLANGE_T+DRUM_CORE_H] with the horn
    # pocket in the TOP face -> translate so the drum TOP sits at
    # DRUM_TOP_Z, horn facing UP toward the inverted servo's spline (which
    # protrudes down through the plate at z=0).
    drum_span = 2 * drum_mod.DRUM_FLANGE_T + drum_mod.DRUM_CORE_H
    drum_z = DRUM_TOP_Z - drum_span
    parts["drum"] = drum_mod.make().translate((0, 0, drum_z))

    # Electronics cover: built with its open rim at z=0 -> translate so the
    # rim meets the plate TOP face (z=EFFECTOR_THK). Included in the
    # assembly STEP; excluded from the mechanism preview render (it hides
    # everything -- see build_assembly()).
    parts["cover"] = cover_mod.make().translate((0, 0, EFFECTOR_THK))

    return parts


def build_assembly() -> dict:
    """Compose the claw assembly to the real stack-up (D2-D7). Writes the
    mechanism preview PNG WITHOUT the cover, and the full assembly STEP
    (mechanism + cover) for SOLIDWORKS handoff."""
    parts = placed_components()

    mechanism_names = [k for k in parts if k != "cover"]
    mechanism = parts[mechanism_names[0]]
    for k in mechanism_names[1:]:
        mechanism = mechanism.union(parts[k])

    full = mechanism.union(parts["cover"])

    stl_path = os.path.join(STL_DIR, "_assembly.stl")
    cq.exporters.export(mechanism, stl_path, tolerance=0.08, angularTolerance=0.3)
    png_path = render_stl(stl_path, os.path.join(PREVIEW_DIR, "assembly.png"),
                           "end-effector (tentacle gripper) assembled")

    step_path = os.path.join(STEP_DIR, "claw_assembly.step")
    cq.exporters.export(full, step_path)

    return {"png": png_path, "step": step_path}


if __name__ == "__main__":
    print("Building parts:")
    build_all()
    print("Building assembly preview + STEP...")
    print(" ", build_assembly())
    print("Done. STEP files in cad/step, STLs in cad/stl, previews in cad/previews.")
