"""
3D visualiser for the RoomCleaner robot.

Renders the room, the four ceiling winches, the cables, the claw, and the
laundry -- and can either animate a run live or save frames/GIFs headlessly.

Nothing here talks to hardware; it draws whatever positions the controller
produces. That separation is deliberate: the exact same controller code will
later drive real motors, and the simulator just becomes an optional monitor.
"""

from __future__ import annotations

import numpy as np
import matplotlib

# 'Agg' lets us render to files on a machine with no display. A live window
# (plt.show) still works if you swap this for your GUI backend locally.
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers 3d projection)

from .kinematics import CableRobot
from .perception.detector import Detector


def _draw_room(ax, cfg):
    w, d, h = cfg.room_width, cfg.room_depth, cfg.room_height
    # Floor outline.
    floor = np.array([[0, 0, 0], [w, 0, 0], [w, d, 0], [0, d, 0], [0, 0, 0]])
    ax.plot(floor[:, 0], floor[:, 1], floor[:, 2], color="0.6", lw=1)
    # Ceiling outline.
    ceil = floor.copy()
    ceil[:, 2] = h
    ax.plot(ceil[:, 0], ceil[:, 1], ceil[:, 2], color="0.8", lw=1)
    # Vertical edges.
    for cx, cy in [(0, 0), (w, 0), (w, d), (0, d)]:
        ax.plot([cx, cx], [cy, cy], [0, h], color="0.85", lw=0.8)


def _style_axes(ax, cfg):
    ax.set_xlim(0, cfg.room_width)
    ax.set_ylim(0, cfg.room_depth)
    ax.set_zlim(0, cfg.room_height)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_zlabel("z (m)")
    try:
        ax.set_box_aspect((cfg.room_width, cfg.room_depth, cfg.room_height))
    except Exception:
        pass


def render_frame(
    robot: CableRobot,
    effector: np.ndarray,
    detector: Detector | None = None,
    hamper_xy=None,
    ax=None,
    title: str = "RoomCleaner",
):
    """Draw a single snapshot. Returns the axes so callers can save it."""
    cfg = robot.cfg
    if ax is None:
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection="3d")
    ax.clear()

    _draw_room(ax, cfg)

    # Winches at the ceiling corners.
    ax.scatter(
        robot.anchors[:, 0], robot.anchors[:, 1], robot.anchors[:, 2],
        color="black", s=40, marker="s", label="winch",
    )

    # Cables from each anchor to the effector.
    for anchor in robot.anchors:
        ax.plot(
            [anchor[0], effector[0]],
            [anchor[1], effector[1]],
            [anchor[2], effector[2]],
            color="tab:blue", lw=1, alpha=0.7,
        )

    # The claw.
    ax.scatter(*effector, color="tab:red", s=90, marker="o", label="claw")

    # Laundry on the floor.
    if detector is not None:
        items = detector.detect()
        if items:
            pts = np.array([d.position for d in items])
            ax.scatter(
                pts[:, 0], pts[:, 1], pts[:, 2],
                color="tab:green", s=60, marker="*", label="laundry",
            )

    # Hamper.
    if hamper_xy is not None:
        ax.scatter(
            hamper_xy[0], hamper_xy[1], 0,
            color="tab:orange", s=120, marker="P", label="hamper",
        )

    _style_axes(ax, cfg)
    ax.set_title(title)
    ax.legend(loc="upper right", fontsize=8)
    return ax


def animate_run(
    robot: CableRobot,
    paths: list[np.ndarray],
    detector: Detector,
    hamper_xy,
    out_path: str = "run.gif",
    max_frames: int = 120,
    fps: int = 20,
):
    """Render a full cleaning run to an animated GIF.

    `paths` is the list of (N,3) waypoint arrays from Controller.run().
    The waypoints are subsampled to at most `max_frames` so the GIF renders
    quickly no matter how long the run is (3D redraws are expensive).
    """
    from matplotlib.animation import FuncAnimation, PillowWriter

    full = np.vstack(paths)
    stride = max(1, len(full) // max_frames)
    all_points = full[::stride]
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")

    def update(i):
        render_frame(
            robot, all_points[i], detector, hamper_xy, ax=ax,
            title=f"RoomCleaner  (step {i}/{len(all_points)})",
        )
        return []

    anim = FuncAnimation(fig, update, frames=len(all_points), interval=1000 / fps)
    anim.save(out_path, writer=PillowWriter(fps=fps))
    plt.close(fig)
    return out_path
