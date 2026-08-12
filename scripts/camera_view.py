"""Camera bring-up helper: find the right index, grab a snapshot, or preview live.

    python -m scripts.camera_view --list                 # probe indices 0..4
    python -m scripts.camera_view --camera 1 --snapshot out.png
    python -m scripts.camera_view --camera 1             # live preview window (Q/ESC to quit)

Use --list first to find which index is your USB camera (a built-in webcam is
usually 0, a USB cam 1). The live window opens the same way roomcleaner's Webcam
does, so the index that previews here is the one to pass to the detector/app.
"""
from __future__ import annotations

import argparse
import sys

import cv2
import numpy as np


def probe(max_index: int = 4) -> None:
    print(f"Probing camera indices 0..{max_index} (each opens briefly for one frame)\n")
    found = []
    for i in range(max_index + 1):
        cap = cv2.VideoCapture(i)  # default backend == what Webcam uses
        if not cap.isOpened():
            cap.release()
            print(f"  index {i}: (not available)")
            continue
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        ok, frame = cap.read()
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if ok and frame is not None:
            b = float(np.asarray(frame).mean())
            tag = "   <-- BLACK/empty (covered or camera busy?)" if b < 5 else ""
            print(f"  index {i}: OPEN   {w}x{h}   mean_brightness={b:.1f}{tag}")
            found.append(i)
        else:
            print(f"  index {i}: opened but returned NO frame ({w}x{h})")
        cap.release()
    print("\nworking indices:", found if found else "none")


def snapshot(index: int, path: str, width: int, height: int) -> None:
    cap = cv2.VideoCapture(index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not cap.isOpened():
        sys.exit(f"ERROR: could not open camera index {index}")
    frame = None
    for _ in range(12):  # let auto-exposure settle
        ok, frame = cap.read()
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if frame is None:
        sys.exit("ERROR: no frame captured")
    cv2.imwrite(path, frame)
    print(f"saved snapshot {w}x{h} -> {path}")


def live(index: int, width: int, height: int) -> None:
    # DirectShow is steadier than MSMF for continuous live capture on Windows.
    backend = cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else 0
    cap = cv2.VideoCapture(index, backend)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not cap.isOpened():
        sys.exit(f"ERROR: could not open camera index {index}")
    for _ in range(5):  # warm up
        cap.read()
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"live preview: camera {index} {w}x{h} — press Q or ESC in the window to close")
    win = f"camera {index} - press Q or ESC to close"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, 960, 540)
    fails = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            fails += 1
            if fails > 30:
                print("giving up: too many failed reads")
                break
            cv2.waitKey(30)
            continue
        fails = 0
        cv2.putText(frame, f"camera {index}  {w}x{h}  [Q/ESC to close]",
                    (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow(win, frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
            break
    cap.release()
    cv2.destroyAllWindows()
    print("preview closed")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--camera", type=int, default=1, help="camera index")
    ap.add_argument("--list", action="store_true", help="probe indices 0..4 and exit")
    ap.add_argument("--snapshot", metavar="PATH", default=None,
                    help="grab one frame to PATH and exit (no window)")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    args = ap.parse_args()

    if args.list:
        probe()
    elif args.snapshot:
        snapshot(args.camera, args.snapshot, args.width, args.height)
    else:
        live(args.camera, args.width, args.height)


if __name__ == "__main__":
    main()
