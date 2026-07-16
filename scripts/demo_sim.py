"""
End-to-end Phase 0 demo -- no hardware required.

Run it:

    python -m scripts.demo_sim

What it does:
    1. Builds the cable robot from config.
    2. Scatters some fake laundry on the floor.
    3. Runs the scan -> grab -> deliver state machine to clear the floor.
    4. Prints the controller's decision log.
    5. Saves two images and an animated GIF into ./output/.
"""

from __future__ import annotations

import copy
import os

import numpy as np

from roomcleaner.config import DEFAULT_CONFIG
from roomcleaner.kinematics import CableRobot, reachable_workspace_slice
from roomcleaner.perception.detector import SimulatedDetector
from roomcleaner.control.state_machine import Controller
from roomcleaner import simulator

import matplotlib.pyplot as plt


OUT = "output"


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    cfg = DEFAULT_CONFIG
    robot = CableRobot(cfg)
    detector = SimulatedDetector(cfg, n_items=4, seed=7)

    # Snapshot the laundry BEFORE the run (the controller removes items as it
    # picks them up, and we want the GIF to show where they started).
    initial_detector = copy.deepcopy(detector)

    hamper_xy = (cfg.room_width - 0.5, 0.5)

    # ---- 1. Static "before" frame -----------------------------------------
    ax = simulator.render_frame(
        robot,
        effector=np.array([cfg.room_width / 2, cfg.room_depth / 2, cfg.room_height - 0.6]),
        detector=detector,
        hamper_xy=hamper_xy,
        title="RoomCleaner -- before cleaning",
    )
    plt.savefig(os.path.join(OUT, "scene_before.png"), dpi=110, bbox_inches="tight")
    plt.close("all")
    print(f"wrote {OUT}/scene_before.png")

    # ---- 2. Workspace reachability map at grab height ----------------------
    z = 0.3
    xs, ys, mask = reachable_workspace_slice(robot, z=z, resolution=45)
    plt.figure(figsize=(6, 4.5))
    plt.contourf(xs, ys, mask.astype(float), levels=[0, 0.5, 1], colors=["#f4cccc", "#d9ead3"])
    plt.scatter(robot.anchors[:, 0], robot.anchors[:, 1], color="black", marker="s", label="winch")
    plt.title(f"Safe workspace at z = {z} m  (green = reachable)")
    plt.xlabel("x (m)"); plt.ylabel("y (m)"); plt.legend(); plt.axis("equal")
    plt.savefig(os.path.join(OUT, "workspace.png"), dpi=110, bbox_inches="tight")
    plt.close("all")
    print(f"wrote {OUT}/workspace.png")

    # ---- 3. Run the cleaning cycle ----------------------------------------
    controller = Controller(robot, detector, hamper_xy=hamper_xy)
    paths = controller.run()
    print("\n--- controller log ---")
    for line in controller._log:
        print(" ", line)
    print(f"\nPicked up {controller.picked_up} item(s) in {len(paths)} trip(s).")

    # ---- 4. Animate the run (using the initial laundry snapshot) -----------
    if paths:
        gif = simulator.animate_run(
            robot, paths, initial_detector, hamper_xy,
            out_path=os.path.join(OUT, "run.gif"), max_frames=100, fps=15,
        )
        print(f"wrote {gif}")


if __name__ == "__main__":
    main()
