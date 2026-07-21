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
    # --- tri-ball belt accelerator (push / launch / pull / hold) -----------
    "belt_pulley",
    "drive_belt",
    "accel_plate",
    "throat_lip",
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


def _place_accelerator():
    """Return (named_solids, ball) for the tri-ball belt accelerator.

    LEFT/RIGHT belts: the ball runs down the barrel gripped between two vertical
    conveyor belts on its left and right; the top + bottom DECKS contain it and
    the bottom deck is the floor it rides on.

    World frame: X = left/right (belt-gap axis), +Y = forward (the muzzle),
    +Z = up. Each part is modelled in its own print orientation, then rotated
    /translated into place. The barrel centre is the origin. Returns
    [(label, cq_solid, rgb_hex)] + (ball_centre, ball_radius).
    """
    from . import params as P

    bp_mod = importlib.import_module("cad.parts.belt_pulley")
    pulley = bp_mod.make()
    belt = importlib.import_module("cad.parts.drive_belt").make()
    plate = importlib.import_module("cad.parts.accel_plate").make()
    lip = importlib.import_module("cad.parts.throat_lip").make()
    plow = importlib.import_module("cad.parts.front_plow").make()
    motor = importlib.import_module("cad.parts.motor_plate").make()

    PLEN = P.BELT_WIDTH + 2 * bp_mod.FLANGE_THK              # pulley length (vertical)
    YB = P.BARREL_LEN / 2.0                                  # muzzle/breach offset (Y)
    XP = P.BELT_GAP / 2.0 + P.PULLEY_PITCH_DIA / 2.0 + P.BELT_THK  # pulley offset (X)
    XG = P.BELT_GAP / 2.0                                    # inner belt surface (grip)
    ZH = P.SIDE_INNER_HALF                                   # deck half-gap (Z)

    def deck(wp):
        # plate local (X=barrel/2 dir, Y=cross dir) -> world (Y=barrel, X=cross)
        return wp.rotate((0, 0, 0), (0, 0, 1), 90)

    named = []

    # Top + bottom decks.
    named.append(("Deck plate (x2)", deck(plate).translate((0, 0, ZH)), "#8f9bad"))
    named.append(("_deck_bot", deck(plate).translate((0, 0, -ZH - P.PLATE_THK)), "#8f9bad"))

    # Four pulleys (vertical axis): left/right x front/rear.
    first = True
    for sx in (+1, -1):
        for sy in (+1, -1):
            pw = pulley.translate((sx * XP, sy * YB, -PLEN / 2))
            named.append(("Belt pulley (x4)" if first else "_pul", pw, "#e0872f"))
            first = False

    # Two belts (left + right), loops in the horizontal plane.
    for sx, lbl in ((-1, "Drive belt (x2)"), (+1, "_belt2")):
        bw = belt.rotate((0, 0, 0), (0, 1, 0), 90).translate((sx * XP, 0, 0))
        named.append((lbl, bw, "#3b3f47"))

    # Two flared throat lips at the muzzle front edge (top + bottom).
    named.append(("Throat lip (x2)", lip.translate((0, YB + 30, ZH)), "#41b06a"))
    named.append(("_lip2", lip.mirror("XY").translate((0, YB + 30, -ZH)), "#41b06a"))

    # Front plow at the muzzle floor (push mode + cross-brace).
    named.append(("Front plow", plow.translate((0, YB + 34, -ZH + 2)), "#c24234"))

    # V5 motor plate above the top deck, geared to a rear drive pulley.
    named.append(("V5 motor plate (x2)",
                  motor.translate((-XP, -YB - P.GEAR_CD, ZH + P.PLATE_THK + 10)),
                  "#586170"))

    ball = ((0.0, -8.0, -ZH + P.TRIBALL_DIA / 2.0), P.TRIBALL_DIA / 2.0)
    return named, ball


def _smooth_facecolors(V, F, base_hex):
    """Gouraud-style face colours from averaged vertex normals (two lights)."""
    import numpy as np
    base = np.array([int(base_hex[i:i + 2], 16) / 255 for i in (1, 3, 5)])
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    fn /= (np.linalg.norm(fn, axis=1, keepdims=True) + 1e-9)
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, F[:, k], fn)
    vn /= (np.linalg.norm(vn, axis=1, keepdims=True) + 1e-9)
    sn = (vn[F[:, 0]] + vn[F[:, 1]] + vn[F[:, 2]]) / 3.0
    sn /= (np.linalg.norm(sn, axis=1, keepdims=True) + 1e-9)
    key = np.array([0.4, -0.5, 0.78]); key = key / np.linalg.norm(key)
    fill = np.array([-0.6, 0.3, 0.4]); fill = fill / np.linalg.norm(fill)
    s = 0.34 + 0.56 * np.clip(sn @ key, 0, 1) + 0.16 * np.clip(sn @ fill, 0, 1)
    return np.clip(s[:, None] * base[None, :], 0, 1)


def build_accelerator_assembly() -> str:
    """Compose + render the tri-ball belt accelerator (smooth, colour-coded)."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    named, (ball_c, ball_r) = _place_accelerator()

    # Commit a merged STL so the whole mechanism opens as one mesh.
    comp = cq.Compound.makeCompound([wp.val() for (_, wp, _) in named])
    cq.exporters.export(comp, os.path.join(STL_DIR, "_accel_assembly.stl"),
                        tolerance=0.1, angularTolerance=0.3)

    fig = plt.figure(figsize=(7.6, 6.8))
    ax = fig.add_subplot(111, projection="3d")
    allpts = []
    for (_, wp, color) in named:
        verts, tris = wp.val().tessellate(0.04)      # fine mesh -> smooth curves
        V = np.array([[p.x, p.y, p.z] for p in verts])
        F = np.array(tris)
        allpts.append(V)
        ax.add_collection3d(Poly3DCollection(
            V[F], facecolors=_smooth_facecolors(V, F, color),
            edgecolors="none", linewidths=0, shade=False))

    # Translucent tri-ball in the barrel.
    u = np.linspace(0, 2 * np.pi, 40)
    v = np.linspace(0, np.pi, 22)
    bx = ball_c[0] + ball_r * np.outer(np.cos(u), np.sin(v))
    by = ball_c[1] + ball_r * np.outer(np.sin(u), np.sin(v))
    bz = ball_c[2] + ball_r * np.outer(np.ones_like(u), np.cos(v))
    ax.plot_surface(bx, by, bz, color="#f0c02a", alpha=0.14, linewidth=0, shade=False)
    allpts.append(np.array([[ball_c[0] - ball_r, ball_c[1] - ball_r, ball_c[2] - ball_r],
                            [ball_c[0] + ball_r, ball_c[1] + ball_r, ball_c[2] + ball_r]]))

    pts = np.vstack(allpts)
    ctr = pts.mean(axis=0)
    r = (pts.max(axis=0) - pts.min(axis=0)).max() / 2 or 1.0
    ax.set_xlim(ctr[0] - r, ctr[0] + r)
    ax.set_ylim(ctr[1] - r, ctr[1] + r)
    ax.set_zlim(ctr[2] - r, ctr[2] + r)
    try:
        ax.set_box_aspect((1, 1, 1))
    except Exception:
        pass
    ax.view_init(elev=16, azim=114)
    ax.set_axis_off()
    ax.set_title("Tri-ball belt accelerator  —  push / launch / pull / hold",
                 fontsize=12.5, pad=0)

    legend = [(l, c) for (l, _, c) in named if not l.startswith("_")]
    legend.append(("Tri-ball", "#f0c02a"))
    ax.legend(handles=[Patch(facecolor=c, edgecolor="none", label=l) for (l, c) in legend],
              loc="upper left", fontsize=8.5, framealpha=0.9)
    fig.tight_layout()
    png = os.path.join(PREVIEW_DIR, "accel_assembly.png")
    fig.savefig(png, dpi=125, bbox_inches="tight")
    plt.close(fig)
    return png


if __name__ == "__main__":
    print("Building parts:")
    build_all()
    print("Building assembly previews...")
    print(" ", build_assembly())
    print(" ", build_accelerator_assembly())
    print("Done. STEP files in cad/step, STLs in cad/stl, previews in cad/previews.")
