"""Figure of the floor reference the claw camera reads: 3 x 3 US-Letter sheets, one AprilTag 36h11 per sheet (ids 0..8,
150 mm black square, 250 mm pitch), sheet 0 defines the floor frame. Same family/ids/sizes as tools/print_floor_board.py.
Run: /usr/bin/python3 make_floor_board_figure.py -> fig/floor_board.png"""
import sys, cv2, numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
from roomcleaner.cdpr.vision.board import FloorBoardLayout
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrow

OUT = Path(__file__).parent / "fig" / "floor_board.png"
EDGE, PITCH, SHEET_W, SHEET_H = 0.150, 0.250, 0.2159, 0.2794      # m
d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
fig, ax = plt.subplots(figsize=(6.2, 6.2), dpi=250)
ax.set_aspect("equal"); ax.axis("off")
for tid, (cx, cy) in FloorBoardLayout.nominal_positions(PITCH).items():   # id 0 centre, 1..8 clockwise from top-left
    ax.add_patch(Rectangle((cx - SHEET_W / 2, cy - SHEET_H / 2), SHEET_W, SHEET_H, fc="white", ec="#B0B0B0", lw=0.8))
    img = cv2.aruco.generateImageMarker(d, tid, 8 * 20, borderBits=1)   # 8 cells incl. border, as printed
    ax.imshow(img, cmap="gray", vmin=0, vmax=255, extent=(cx - EDGE / 2, cx + EDGE / 2, cy - EDGE / 2, cy + EDGE / 2),
              interpolation="nearest", zorder=2)
    ax.text(cx, cy - EDGE / 2 - 0.012, f"id {tid}" + (" (origin)" if tid == 0 else ""), ha="center", va="top", fontsize=8, color="#404040")
# floor frame on sheet 0
ax.add_patch(FancyArrow(0, 0, 0.09, 0, width=0.004, head_width=0.018, color="#1F3A5F", zorder=3))
ax.add_patch(FancyArrow(0, 0, 0, 0.09, width=0.004, head_width=0.018, color="#1F3A5F", zorder=3))
ax.text(0.095, 0.0, "+X", color="#1F3A5F", fontsize=9, va="center", fontweight="bold")
ax.text(0.0, 0.098, "+Y", color="#1F3A5F", fontsize=9, ha="center", fontweight="bold")
# dimensions
ax.annotate("", xy=(-PITCH - EDGE / 2, -0.43), xytext=(-PITCH + EDGE / 2, -0.43), arrowprops=dict(arrowstyle="<->", color="#404040", lw=0.8))
ax.text(-PITCH, -0.445, "150 mm", ha="center", va="top", fontsize=8, color="#404040")
ax.annotate("", xy=(-PITCH, 0.43), xytext=(0, 0.43), arrowprops=dict(arrowstyle="<->", color="#404040", lw=0.8))
ax.text(-PITCH / 2, 0.44, "250 mm pitch", ha="center", va="bottom", fontsize=8, color="#404040")
ax.set_xlim(-0.46, 0.46); ax.set_ylim(-0.47, 0.47)
ax.set_title("Floor reference: AprilTag 36h11, one tag per sheet, sheet 0 is the origin", fontsize=9, color="#000000")
fig.savefig(OUT, bbox_inches="tight", pad_inches=0.05, facecolor="white")
print("wrote", OUT)
