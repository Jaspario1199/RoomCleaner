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
    # --- tri-ball flywheel intake (push / launch / pull / hold) ------------
    "flywheel",
    "intake_side_plate",
    "launch_hood",
    "cradle_roller",
    "front_plow",
    "motor_plate",
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


def _place_intake():
    """Return (named_solids, ball) for the tri-ball flywheel intake.

    World frame: X = shaft axis (left/right), +Y = forward (intake mouth),
    +Z = up. Each part is modelled in its own print orientation, then rotated
    and translated into place here. The flywheel shaft sits at the origin.
    Returns a list of (label, cq_solid, rgb_hex) plus (ball_center, ball_radius).
    """
    from . import params as P

    fly = importlib.import_module("cad.parts.flywheel").make()
    plate = importlib.import_module("cad.parts.intake_side_plate").make()
    hood = importlib.import_module("cad.parts.launch_hood").make()
    roller = importlib.import_module("cad.parts.cradle_roller").make()
    plow = importlib.import_module("cad.parts.front_plow").make()
    motor = importlib.import_module("cad.parts.motor_plate").make()

    def to_plate_frame(wp):
        # local (forward=+X, up=+Y, thickness=+Z) -> world (Y, Z, X)
        return wp.rotate((0, 0, 0), (0, 0, 1), 90).rotate((0, 0, 0), (0, 1, 0), 90)

    g = P.VEX_GRID
    named = []

    named.append(("Side plate (x2)",
                  to_plate_frame(plate).translate((P.PLATE_GAP / 2, 0, 0)), "#8a97a8"))
    named.append(("_plate_L",
                  to_plate_frame(plate).translate((-(P.PLATE_GAP / 2 + P.PLATE_THK), 0, 0)), "#8a97a8"))

    for i, s in enumerate((+1, -1)):
        f = (fly.rotate((0, 0, 0), (0, 1, 0), 90)
             .translate((-P.FLYWHEEL_WIDTH / 2 + s * P.FLYWHEEL_SPACING / 2, 0, 0)))
        named.append(("Flywheel (x2)" if i == 0 else "_fly2", f, "#e0872f"))

    named.append(("Cradle roller",
                  roller.rotate((0, 0, 0), (0, 1, 0), 90)
                  .translate((-(P.PLATE_GAP - 4) / 2, 0, 0))
                  .translate((0, -3 * g, 2 * g)), "#3fae6a"))

    named.append(("Launch hood", hood.translate((0, 26, 58)), "#4f86d6"))
    named.append(("Front plow", plow.translate((0, 54, -32)), "#c24234"))
    named.append(("V5 motor plate",
                  to_plate_frame(motor).translate((P.PLATE_GAP / 2 + P.PLATE_THK + 8, 0, -P.GEAR_CD)),
                  "#586170"))

    ball = ((0.0, 14.0, 108.0), P.TRIBALL_DIA / 2.0)
    return named, ball


def build_intake_assembly() -> str:
    """Compose + render the tri-ball flywheel intake (colored, with the ball)."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    named, (ball_c, ball_r) = _place_intake()

    # Also commit a merged STL so the whole mechanism opens as one mesh.
    comp = cq.Compound.makeCompound([wp.val() for (_, wp, _) in named])
    cq.exporters.export(comp, os.path.join(STL_DIR, "_intake_assembly.stl"),
                        tolerance=0.1, angularTolerance=0.3)

    light = np.array([0.35, -0.55, 0.78])
    light = light / np.linalg.norm(light)

    def shade(polys, base_hex):
        base = np.array([int(base_hex[i:i + 2], 16) / 255 for i in (1, 3, 5)])
        n = np.cross(polys[:, 1] - polys[:, 0], polys[:, 2] - polys[:, 0])
        ln = np.linalg.norm(n, axis=1, keepdims=True)
        ln[ln == 0] = 1
        n = n / ln
        s = 0.5 + 0.5 * np.clip(np.abs(n @ light), 0, 1)
        return np.clip(s[:, None] * base[None, :], 0, 1)

    fig = plt.figure(figsize=(7.2, 6.4))
    ax = fig.add_subplot(111, projection="3d")
    allpts = []
    for (_, wp, color) in named:
        verts, tris = wp.val().tessellate(0.15)
        V = np.array([[p.x, p.y, p.z] for p in verts])
        F = np.array(tris)
        polys = V[F]
        allpts.append(V)
        ax.add_collection3d(Poly3DCollection(
            polys, facecolors=shade(polys, color),
            edgecolors=(0, 0, 0, 0.05), linewidths=0.08))

    # Translucent tri-ball proxy resting in the pocket.
    u = np.linspace(0, 2 * np.pi, 26)
    v = np.linspace(0, np.pi, 14)
    bx = ball_c[0] + ball_r * np.outer(np.cos(u), np.sin(v))
    by = ball_c[1] + ball_r * np.outer(np.sin(u), np.sin(v))
    bz = ball_c[2] + ball_r * np.outer(np.ones_like(u), np.cos(v))
    ax.plot_surface(bx, by, bz, color="#f0c02a", alpha=0.16, linewidth=0, shade=False)
    allpts.append(np.array([[ball_c[0] - ball_r, ball_c[1] - ball_r, ball_c[2] - ball_r],
                            [ball_c[0] + ball_r, ball_c[1] + ball_r, ball_c[2] + ball_r]]))

    P = np.vstack(allpts)
    ctr = P.mean(axis=0)
    r = (P.max(axis=0) - P.min(axis=0)).max() / 2 or 1.0
    ax.set_xlim(ctr[0] - r, ctr[0] + r)
    ax.set_ylim(ctr[1] - r, ctr[1] + r)
    ax.set_zlim(ctr[2] - r, ctr[2] + r)
    try:
        ax.set_box_aspect((1, 1, 1))
    except Exception:
        pass
    ax.view_init(elev=16, azim=-72)
    ax.set_axis_off()
    ax.set_title("Tri-ball flywheel intake  —  push / launch / pull / hold",
                 fontsize=12, pad=2)

    legend = [(l, c) for (l, _, c) in named if not l.startswith("_")]
    legend.append(("Tri-ball (held)", "#f0c02a"))
    ax.legend(handles=[Patch(facecolor=c, edgecolor="none", label=l) for (l, c) in legend],
              loc="upper left", fontsize=8, framealpha=0.85)
    fig.tight_layout()
    png = os.path.join(PREVIEW_DIR, "intake_assembly.png")
    fig.savefig(png, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return png


if __name__ == "__main__":
    print("Building parts:")
    build_all()
    print("Building assembly previews...")
    print(" ", build_assembly())
    print(" ", build_intake_assembly())
    print("Done. STEP files in cad/step, STLs in cad/stl, previews in cad/previews.")
