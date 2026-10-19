"""Camera intrinsic calibration with a ChArUco board.

1. Make and print a board (flat, rigid backing):
       python -m tools.calibrate_camera board --out charuco.png
   Measure one printed chessboard square and pass it as --square-mm below.
2. Capture 20-40 photos with the claw camera in the SAME mode it will run
   (resolution, JPEG quality, focus): board at many angles, distances and
   positions across the whole image, including the corners.
3. Calibrate:
       python -m tools.calibrate_camera calibrate --images photos/ --square-mm 30.1 \
           --out config/camera.json
   The result is rejected if the RMS reprojection error exceeds 1.0 px or
   fewer than 12 views are usable. Its calibration_id is recorded with every
   geometric calibration that uses it; changing the camera mode invalidates it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

SQUARES = (8, 6)
DICT = cv2.aruco.DICT_5X5_100


def board(square_m=0.030, marker_ratio=0.72):
    d = cv2.aruco.getPredefinedDictionary(DICT)
    return cv2.aruco.CharucoBoard(SQUARES, square_m, square_m * marker_ratio, d)


def make_board_image(px_per_square=200):
    b = board()
    return b.generateImage((SQUARES[0] * px_per_square, SQUARES[1] * px_per_square), marginSize=40)


def calibrate_images(images, square_m, *, min_views=12, max_rms=1.0):
    b = board(square_m)
    det = cv2.aruco.CharucoDetector(b)
    obj_pts, img_pts, size = [], [], None
    for img in images:
        gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        size = gray.shape[::-1]
        cc, ci, _, _ = det.detectBoard(gray)
        if ci is None or len(ci) < 8:
            continue
        o, i = b.matchImagePoints(cc, ci)
        if o is None or len(o) < 8:
            continue
        obj_pts.append(o)
        img_pts.append(i)
    if len(obj_pts) < min_views:
        raise ValueError(f"only {len(obj_pts)} usable views (need {min_views})")
    rms, K, dist, _, _ = cv2.calibrateCamera(obj_pts, img_pts, size, None, None)
    if rms > max_rms:
        raise ValueError(f"RMS reprojection {rms:.2f} px > {max_rms}: recapture (blur, flatness, coverage)")
    dist = dist.ravel()[:5]
    cal_id = hashlib.sha1(np.concatenate([K.ravel(), dist, size]).tobytes()).hexdigest()[:12]
    return {"image_size": list(size), "K": K.tolist(), "dist": dist.tolist(), "rms_px": float(rms),
            "views": len(obj_pts), "calibration_id": cal_id}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("board")
    b.add_argument("--out", default="charuco.png")
    c = sub.add_parser("calibrate")
    c.add_argument("--images", required=True)
    c.add_argument("--square-mm", type=float, required=True)
    c.add_argument("--out", default="config/camera.json")
    a = ap.parse_args()
    if a.cmd == "board":
        cv2.imwrite(a.out, make_board_image())
        print(f"wrote {a.out} ({SQUARES[0]}x{SQUARES[1]} squares). Print flat, measure a square.")
        return
    imgs = [cv2.imread(str(p)) for p in sorted(Path(a.images).glob("*")) if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    res = calibrate_images([i for i in imgs if i is not None], a.square_mm / 1000)
    Path(a.out).write_text(json.dumps(res, indent=2))
    print(f"wrote {a.out}: rms {res['rms_px']:.3f} px from {res['views']} views, id {res['calibration_id']}")


if __name__ == "__main__":
    main()
