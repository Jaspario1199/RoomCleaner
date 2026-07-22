"""
Simulation 1 -- Cable-tension "cost map".

At a chosen height, colour every floor position by the PEAK tension any one of
the four cables must carry to hold the loaded effector there. This is the map
that justifies your motor choice: it shows where the robot strains hardest
(near the walls/corners) and confirms the worst case stays under the motor limit.

    python -m scripts.sim_tension_map

How it works (the physics):
  At a point P, each cable pulls the effector toward its ceiling anchor along a
  unit vector u_i. Static equilibrium means the cable pulls plus gravity sum to
  zero:  sum_i(t_i * u_i) = (0, 0, m*g),  with every t_i >= 0 (cables only pull).
  `robot.solve_tensions(P)` returns those t_i. We take max(t_i) at each grid
  point -- the load on the busiest motor -- and draw it as a heatmap.
"""

from __future__ import annotations

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from roomcleaner.config import DEFAULT_CONFIG
from roomcleaner.kinematics import CableRobot

OUT = "output"


def tension_grid(robot, z, res=60):
    cfg = robot.cfg
    xs = np.linspace(0, cfg.room_width, res)
    ys = np.linspace(0, cfg.room_depth, res)
    peak = np.full((res, res), np.nan)     # NaN = unreachable (drawn blank)
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            p = np.array([x, y, z])
            if not robot.is_reachable(p):
                continue
            tensions, ok = robot.solve_tensions(p)
            if ok:
                peak[i, j] = tensions.max()
    return xs, ys, peak


def main():
    os.makedirs(OUT, exist_ok=True)
    cfg = DEFAULT_CONFIG
    robot = CableRobot(cfg)

    heights = [0.3, 1.0]                    # grab height and cruise-ish height
    fig, axes = plt.subplots(1, len(heights), figsize=(12, 5))
    for ax, z in zip(axes, heights):
        xs, ys, peak = tension_grid(robot, z)
        im = ax.pcolormesh(xs, ys, peak, shading="auto", cmap="viridis")
        ax.scatter(robot.anchors[:, 0], robot.anchors[:, 1], c="white",
                   edgecolors="black", s=60, marker="s", label="winch", zorder=5)
        if cfg.fan.enabled:
            ax.add_patch(plt.Circle((cfg.fan.cx, cfg.fan.cy), cfg.fan.radius,
                                    color="red", alpha=0.25))
        ax.set_title(f"Peak cable tension at z = {z} m")
        ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)"); ax.set_aspect("equal")
        fig.colorbar(im, ax=ax, label="tension (N)")

    worst = np.nanmax(tension_grid(robot, 0.3)[2])
    fig.suptitle(f"Cable-tension cost map  (loaded {cfg.mass:.2f} kg)  "
                 f"— worst case {worst:.1f} N vs {cfg.max_tension:.0f} N limit")
    plt.tight_layout()
    path = os.path.join(OUT, "tension_map.png")
    plt.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}")
    print(f"worst-case peak tension: {worst:.1f} N  (motor limit {cfg.max_tension:.0f} N)")


if __name__ == "__main__":
    main()
