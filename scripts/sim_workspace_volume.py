"""
Simulation 5 -- The reachable VOLUME.

The 2D maps show one height at a time. This sweeps `is_reachable` over a full 3D
grid and renders every reachable point, so you can see the actual 3D volume the
claw can service -- the "bite" the fan takes out of the top, the wall margins,
and how the workspace narrows toward the ceiling (where tension gives out).

    python -m scripts.sim_workspace_volume

Method: brute force. For each cell of a coarse 3D grid, ask `is_reachable`
(walls + floor clearance + cable tension feasibility + fan clearance). Plot the
reachable cell centers as a point cloud, colored by height.
"""

from __future__ import annotations

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

from roomcleaner.config import DEFAULT_CONFIG
from roomcleaner.kinematics import CableRobot

OUT = "output"


def main():
    os.makedirs(OUT, exist_ok=True)
    cfg = DEFAULT_CONFIG
    robot = CableRobot(cfg)

    xs = np.linspace(0.2, cfg.room_width - 0.2, 26)
    ys = np.linspace(0.2, cfg.room_depth - 0.2, 20)
    zs = np.linspace(0.15, cfg.room_height - 0.15, 18)

    pts = []
    for z in zs:
        for y in ys:
            for x in xs:
                if robot.is_reachable(np.array([x, y, z])):
                    pts.append((x, y, z))
    pts = np.array(pts)
    total = len(xs) * len(ys) * len(zs)
    frac = len(pts) / total

    fig = plt.figure(figsize=(9, 7))
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=pts[:, 2],
               cmap="viridis", s=8, alpha=0.5)
    ax.scatter(robot.anchors[:, 0], robot.anchors[:, 1], robot.anchors[:, 2],
               c="red", s=50, marker="s", label="winch")
    # Fan keep-out outline near the ceiling.
    if cfg.fan.enabled:
        th = np.linspace(0, 2 * np.pi, 40)
        ax.plot(cfg.fan.cx + cfg.fan.radius * np.cos(th),
                cfg.fan.cy + cfg.fan.radius * np.sin(th),
                np.full_like(th, cfg.fan.z_low), color="red", lw=1.5)
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)"); ax.set_zlabel("z (m)")
    ax.set_title(f"Reachable workspace volume — {frac*100:.0f}% of the room box")
    ax.view_init(elev=18, azim=-60)
    try:
        ax.set_box_aspect((cfg.room_width, cfg.room_depth, cfg.room_height))
    except Exception:
        pass
    p = os.path.join(OUT, "workspace_volume.png")
    plt.savefig(p, dpi=110, bbox_inches="tight"); plt.close(fig)

    approx_m3 = frac * cfg.room_width * cfg.room_depth * cfg.room_height
    print(f"wrote {p}")
    print(f"reachable: {frac*100:.0f}% of the room box "
          f"(~{approx_m3:.1f} m^3 of {cfg.room_width*cfg.room_depth*cfg.room_height:.1f} m^3)")


if __name__ == "__main__":
    main()
