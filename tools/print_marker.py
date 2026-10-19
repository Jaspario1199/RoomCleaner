"""Make a printable calibration marker at an exact physical size.

    python -m tools.print_marker --edge-mm 152.4 --id 0 --out marker_id0.png

Print at 100 % scale (no "fit to page"). Then MEASURE the black square's edge
with a ruler or calipers and enter that measured value as marker.edge_m in
config/robot.json -- the printed size, not the requested size, is what counts.
The arrow shows the marker's +X axis: point it roughly toward station A and
enter the approximate room heading as marker.heading_prior_rad.
"""
from __future__ import annotations

import argparse

import cv2
import numpy as np

from roomcleaner.cdpr.vision.marker import _FAMILIES


def make_marker_sheet(edge_mm: float, marker_id: int, family="apriltag_36h11", dpi=300,
                      margin_cells=2) -> np.ndarray:
    d = cv2.aruco.getPredefinedDictionary(_FAMILIES[family])
    px_per_mm = dpi / 25.4
    side = int(round(edge_mm * px_per_mm))
    tag = cv2.aruco.generateImageMarker(d, marker_id, side, borderBits=1)
    cell = side / (d.markerSize + 2)
    m = int(round(margin_cells * cell))
    ruler_h = int(30 * px_per_mm)
    W = side + 2 * m
    H = side + 2 * m + ruler_h
    sheet = np.full((H, W), 255, np.uint8)
    sheet[m:m + side, m:m + side] = tag
    # 100 mm check ruler
    y = side + 2 * m + int(8 * px_per_mm)
    x0 = m
    x1 = x0 + int(round(100 * px_per_mm))
    cv2.line(sheet, (x0, y), (x1, y), 0, 3)
    for k in range(11):
        xk = x0 + int(round(k * 10 * px_per_mm))
        cv2.line(sheet, (xk, y - 15), (xk, y + 15), 0, 2)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(sheet, "100 mm check", (x0, y + int(10 * px_per_mm)), font, 1.2, 0, 2)
    cv2.putText(sheet, f"{family} id {marker_id}  edge {edge_mm:.1f} mm (measure!)",
                (x0, y + int(18 * px_per_mm)), font, 1.0, 0, 2)
    # +X arrow in the top margin
    ax, ay = m + side // 2, m // 2
    cv2.arrowedLine(sheet, (ax - side // 6, ay), (ax + side // 6, ay), 0, 4, tipLength=0.25)
    cv2.putText(sheet, "+X  (toward station A)", (ax + side // 6 + 10, ay + 10), font, 1.0, 0, 2)
    return sheet


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--edge-mm", type=float, default=152.4)
    ap.add_argument("--id", type=int, default=0)
    ap.add_argument("--family", default="apriltag_36h11", choices=sorted(_FAMILIES))
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out", default="marker.png")
    a = ap.parse_args()
    img = make_marker_sheet(a.edge_mm, a.id, a.family, a.dpi)
    cv2.imwrite(a.out, img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    print(f"wrote {a.out}: {img.shape[1]}x{img.shape[0]} px at {a.dpi} dpi "
          f"({img.shape[1] / a.dpi * 25.4:.0f} x {img.shape[0] / a.dpi * 25.4:.0f} mm). Print at 100 %.")


if __name__ == "__main__":
    main()
