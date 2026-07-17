"""
The full perception -> planning pipeline, end to end.

    # Test on a photo TODAY (no camera needed) -- use a top-down phone photo of
    # your floor with some laundry on it:
    python -m scripts.detect_and_plan --image myfloor.jpg

    # Or live from the webcam once it arrives:
    python -m scripts.detect_and_plan --webcam 0

What it does:
    1. Loads a frame (image file or webcam).
    2. Runs open-vocabulary laundry detection (YOLO-World).
    3. Maps every detection to a floor (x, y) coordinate.
    4. Feeds them to the SAME Controller that drives the simulator, and plans the
       scan -> nearest-first -> grab -> deliver pickup order.
    5. Saves two pictures into ./output/:
         - detected_image.png : your frame with boxes + labels + floor coords
         - detected_scene.png : the 3D room with the detected laundry + plan

Install the vision deps first (on the machine with the photo/camera):
    pip install -r requirements-vision.txt

This is the software half of the robot. The day your camera arrives, point it at
the floor and run --webcam; the detections that come out are exactly what the
real robot will act on.
"""

from __future__ import annotations

import argparse
import os

import numpy as np

from roomcleaner.config import DEFAULT_CONFIG
from roomcleaner.kinematics import CableRobot
from roomcleaner.perception.localization import OverheadLinearMapper
from roomcleaner.perception.vision_detector import YoloWorldDetector, DEFAULT_LAUNDRY_CLASSES
from roomcleaner.perception.live import LiveDetector
from roomcleaner.control.state_machine import Controller
from roomcleaner import simulator

OUT = "output"


def load_frame(args):
    """Return an HxWx3 RGB frame from an image file or the webcam."""
    if args.image:
        import matplotlib.image as mpimg
        frame = mpimg.imread(args.image)
        if frame.dtype != np.uint8:                # matplotlib may return floats
            frame = (frame * 255).clip(0, 255).astype(np.uint8)
        if frame.shape[-1] == 4:                    # drop alpha
            frame = frame[:, :, :3]
        return frame
    from roomcleaner.perception.camera import Webcam
    cam = Webcam(index=args.webcam).open()
    return cam.read()


def draw_detections(frame, detections, path):
    """Save the frame with detection boxes, labels, and floor coordinates."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.imshow(frame)
    for d in detections:
        if d.bbox is None:
            continue
        x1, y1, x2, y2 = d.bbox
        ax.add_patch(Rectangle((x1, y1), x2 - x1, y2 - y1,
                               fill=False, edgecolor="lime", linewidth=2))
        ax.text(x1, max(y1 - 6, 0),
                f"{d.label} {d.confidence:.2f}  @({d.position[0]:.1f},{d.position[1]:.1f})m",
                color="black", fontsize=8,
                bbox=dict(facecolor="lime", edgecolor="none", pad=1))
    ax.set_title(f"Detected {len(detections)} item(s)")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--image", help="path to a top-down photo of the floor")
    g.add_argument("--webcam", type=int, help="webcam index (e.g. 0)")
    ap.add_argument("--conf", type=float, default=0.25, help="detection confidence threshold")
    ap.add_argument("--classes", nargs="*", default=None,
                    help="override the laundry class words to detect")
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    cfg = DEFAULT_CONFIG
    robot = CableRobot(cfg)

    # 1. Get a frame.
    frame = load_frame(args)
    h, w = frame.shape[:2]
    print(f"frame: {w}x{h}")

    # 2. Build the perception pipeline (zero-calibration overhead mapping).
    mapper = OverheadLinearMapper(cfg.room_width, cfg.room_depth, w, h)
    vision = YoloWorldDetector(
        mapper, classes=args.classes or DEFAULT_LAUNDRY_CLASSES, confidence=args.conf
    )
    live = LiveDetector(vision)

    # 3. Detect + localize.
    dets = live.snapshot(frame)
    print(f"\n--- {len(dets)} detection(s) ---")
    for d in dets:
        print(f"  {d.label:10s} conf={d.confidence:.2f} "
              f"floor=({d.position[0]:.2f}, {d.position[1]:.2f}) m")

    draw_detections(frame, dets, os.path.join(OUT, "detected_image.png"))
    print(f"wrote {OUT}/detected_image.png")

    if not dets:
        print("No laundry detected -- try a clearer top-down photo or lower --conf.")
        return

    # 4. Plan the pickups with the real control loop.
    hamper_xy = (cfg.room_width - 0.5, 0.5)
    controller = Controller(robot, live, hamper_xy=hamper_xy)
    paths = controller.run()
    print("\n--- pickup plan ---")
    for line in controller._log:
        print(" ", line)
    print(f"\nPlanned {controller.picked_up} pickup(s) in {len(paths)} trip(s).")

    # 5. Show the detected scene in the 3D room.
    import matplotlib.pyplot as plt
    live.snapshot(frame)  # restore the full item list (run() emptied it)
    simulator.render_frame(
        robot,
        effector=robot.find_rest_position(prefer_xy=hamper_xy),
        detector=live, hamper_xy=hamper_xy,
        rest_xyz=robot.find_rest_position(prefer_xy=hamper_xy),
        title="Detected laundry in the room",
    )
    plt.savefig(os.path.join(OUT, "detected_scene.png"), dpi=110, bbox_inches="tight")
    plt.close("all")
    print(f"wrote {OUT}/detected_scene.png")


if __name__ == "__main__":
    main()
