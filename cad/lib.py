"""
Shared helpers: export a CadQuery solid to STEP + STL, and render a PNG preview.

STEP is the portable CAD interchange format (opens in Fusion 360, SolidWorks,
FreeCAD, Onshape...). STL is the mesh you slice for printing. The PNG is just so
you can eyeball the part without opening anything.
"""

from __future__ import annotations

import os
import numpy as np
import cadquery as cq

HERE = os.path.dirname(__file__)
STEP_DIR = os.path.join(HERE, "step")
STL_DIR = os.path.join(HERE, "stl")
PREVIEW_DIR = os.path.join(HERE, "previews")
for _d in (STEP_DIR, STL_DIR, PREVIEW_DIR):
    os.makedirs(_d, exist_ok=True)


def export(solid: cq.Workplane, name: str, render: bool = True) -> dict:
    """Write <name>.step and <name>.stl (and a preview PNG). Returns paths."""
    step_path = os.path.join(STEP_DIR, f"{name}.step")
    stl_path = os.path.join(STL_DIR, f"{name}.stl")
    cq.exporters.export(solid, step_path)
    cq.exporters.export(solid, stl_path, tolerance=0.05, angularTolerance=0.2)
    out = {"step": step_path, "stl": stl_path}
    if render:
        out["png"] = render_stl(stl_path, os.path.join(PREVIEW_DIR, f"{name}.png"), name)
    return out


def render_stl(stl_path: str, png_path: str, title: str = "") -> str:
    """Render an STL mesh to a shaded PNG using matplotlib (headless)."""
    import trimesh
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    mesh = trimesh.load(stl_path)
    tris = mesh.triangles  # (n, 3, 3)

    # Simple lambert shading from face normals.
    normals = mesh.face_normals
    light = np.array([0.4, -0.5, 0.75])
    light = light / np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(normals @ light, 0, 1)
    base = np.array([0.30, 0.55, 0.85])
    colors = np.clip(shade[:, None] * base[None, :], 0, 1)

    fig = plt.figure(figsize=(6, 5))
    ax = fig.add_subplot(111, projection="3d")
    coll = Poly3DCollection(tris, facecolors=colors, edgecolors=(0, 0, 0, 0.05), linewidths=0.1)
    ax.add_collection3d(coll)

    # Equal aspect around the mesh bounds.
    v = mesh.vertices
    ctr = v.mean(axis=0)
    r = (v.max(axis=0) - v.min(axis=0)).max() / 2 or 1.0
    ax.set_xlim(ctr[0] - r, ctr[0] + r)
    ax.set_ylim(ctr[1] - r, ctr[1] + r)
    ax.set_zlim(ctr[2] - r, ctr[2] + r)
    try:
        ax.set_box_aspect((1, 1, 1))
    except Exception:
        pass
    ax.view_init(elev=22, azim=-58)
    dims = v.max(axis=0) - v.min(axis=0)
    ax.set_title(f"{title}\n{dims[0]:.0f} x {dims[1]:.0f} x {dims[2]:.0f} mm", fontsize=10)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(png_path, dpi=115, bbox_inches="tight")
    plt.close(fig)
    return png_path
