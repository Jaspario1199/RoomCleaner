"""
Simulation 2 -- What happens DURING one pickup.

Runs a single scan->grab->deliver cycle and, at every waypoint along the path,
computes the four cable lengths and tensions. Then plots three things vs. time:

  1. Effector height z(t)          -- the up/across/down shape of the motion
  2. The 4 cable lengths L_i(t)    -- exactly what each winch spools in/out
  3. The 4 cable tensions t_i(t)   -- the load on each motor (with the limit line)

This is the analysis that tells you the motors never exceed their limit through a
real move, and shows how much cable each winch pays out. It's the bridge between
the geometry and the hardware.

    python -m scripts.sim_pickup_run

How it works:
  The Controller plans a pickup as a dense (N,3) waypoint path (same one the sim
  animates and the hardware streams). For each waypoint P we call
  robot.cable_lengths(P) (inverse kinematics) and robot.solve_tensions(P)
  (statics). Stacking those over the path gives time series we can plot.
"""

from __future__ import annotations

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from roomcleaner.config import DEFAULT_CONFIG
from roomcleaner.kinematics import CableRobot
from roomcleaner.perception.detector import SimulatedDetector
from roomcleaner.control.state_machine import Controller

OUT = "output"
LABELS = ["A", "B", "C", "D"]


def main():
    os.makedirs(OUT, exist_ok=True)
    cfg = DEFAULT_CONFIG
    robot = CableRobot(cfg)
    detector = SimulatedDetector(cfg, n_items=1, seed=3)
    controller = Controller(robot, detector, hamper_xy=(cfg.room_width - 0.5, 0.5))

    # One pickup cycle -> its dense path. (grab happens between descent and lift.)
    path = controller.plan_next_cycle()
    hz = 50.0
    t = np.arange(len(path)) / hz

    lengths = np.array([robot.cable_lengths(p) for p in path])       # (N,4)
    tensions = np.full((len(path), 4), np.nan)
    for k, p in enumerate(path):
        ten, ok = robot.solve_tensions(p)
        if ok:
            tensions[k] = ten

    fig, ax = plt.subplots(3, 1, figsize=(9, 9), sharex=True)

    ax[0].plot(t, path[:, 2], color="tab:red")
    ax[0].set_ylabel("effector z (m)")
    ax[0].set_title("One pickup: height, cable lengths, and motor loads over time")
    ax[0].grid(alpha=0.3)

    for i in range(4):
        ax[1].plot(t, lengths[:, i], label=f"cable {LABELS[i]}")
    ax[1].set_ylabel("cable length (m)")
    ax[1].legend(ncol=4, fontsize=8); ax[1].grid(alpha=0.3)

    for i in range(4):
        ax[2].plot(t, tensions[:, i], label=f"cable {LABELS[i]}")
    ax[2].axhline(cfg.max_tension, color="k", ls="--", lw=1, label="motor limit")
    ax[2].set_ylabel("cable tension (N)"); ax[2].set_xlabel("time (s)")
    ax[2].legend(ncol=5, fontsize=8); ax[2].grid(alpha=0.3)

    plt.tight_layout()
    p = os.path.join(OUT, "pickup_run.png")
    plt.savefig(p, dpi=110, bbox_inches="tight")
    plt.close(fig)

    print(f"wrote {p}")
    print(f"peak tension during pickup: {np.nanmax(tensions):.1f} N "
          f"(limit {cfg.max_tension:.0f} N)")
    print(f"max cable length change: {np.ptp(lengths, axis=0).max():.2f} m "
          f"-> ~{np.ptp(lengths, axis=0).max()*50930:.0f} motor steps")


if __name__ == "__main__":
    main()
