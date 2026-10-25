"""AS5600 encoder wiring for the Rev D station: the encoder board's pins, the 4-wire cable to the J5 header on the perfboard
(or the breadboard holes), and the fifth connection, DIR to GND, which is made ON the encoder board.

    /usr/bin/python3 docs/electrical/station_revD_20261021/encoder_wiring.py  -> encoder_wiring.png / .pdf
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

HERE = Path(__file__).resolve().parent
WIRES = [  # encoder pin, colour, perfboard J5 hole, breadboard hole, signal
    ("VCC", "#ff7f0e", "C17", "T+ (top red rail)", "3.3 V"),
    ("GND", "#222222", "D17", "T- (top blue rail)", "ground"),
    ("SDA", "#e377c2", "E17", "a9", "I2C data (XIAO D4 / ESP32 D21)"),
    ("SCL", "#7f7f7f", "F17", "a10", "I2C clock (XIAO D5 / ESP32 D22)"),
]
PINS = ["VCC", "GND", "DIR", "SCL", "SDA", "OUT", "GPO"]


def main():
    fig, ax = plt.subplots(figsize=(13, 7.2))
    # encoder board
    bx, by, bw, bh = 0.5, 4.4, 6.8, 2.4
    ax.add_patch(FancyBboxPatch((bx, by), bw, bh, boxstyle="round,pad=0.08", fc="#5b2a86", ec="#111"))
    ax.add_patch(Circle((bx + bw / 2, by + bh / 2 + 0.35), 0.45, fc="#222", ec="#aaa"))
    ax.text(bx + bw / 2, by + bh / 2 + 0.35, "AS5600", color="white", fontsize=7, ha="center", va="center")
    ax.text(bx + bw / 2, by + bh - 0.3, "AS5600 encoder board (at the spool)", color="white",
            fontsize=9, weight="bold", ha="center")
    px = {}
    for i, n in enumerate(PINS):
        x = bx + 0.5 + i * 0.97
        px[n] = x
        ax.add_patch(Rectangle((x - 0.14, by - 0.35), 0.28, 0.35, fc="#d4af37", ec="#111"))
        ax.text(x, by + 0.15, n, color="white", fontsize=8.5, weight="bold", ha="center", va="bottom")
    # the fifth connection: DIR to GND on the encoder board
    y5 = by - 0.75
    ax.plot([px["DIR"], px["DIR"], px["GND"], px["GND"]], [by - 0.35, y5, y5, by - 0.35], color="#d62728", lw=3)
    ax.annotate("5th connection: short wire DIR -> GND\n(soldered on the ENCODER board,\nnot on the perfboard)",
                xy=((px["DIR"] + px["GND"]) / 2, y5), xytext=(bx + bw + 0.4, by + 0.4), color="#d62728", fontsize=9,
                weight="bold", ha="left", va="center", arrowprops=dict(arrowstyle="->", color="#d62728", lw=1.5))
    for n in ("OUT", "GPO"):
        ax.text(px[n], by - 0.5, "leave\nempty", fontsize=7, ha="center", va="top", color="#555")
    # J5 header on the perfboard
    hx, hy = 8.9, 0.6
    ax.add_patch(Rectangle((hx - 0.6, hy - 1.45), 4.5, 1.95, fc="#1f6f3a", ec="#111"))
    ax.text(hx + 1.65, hy - 1.05, "J5 ENCODER header\non the perfboard (row 17)", color="white", fontsize=8.5, weight="bold", ha="center", va="center")
    for i, (n, colr, hole, bb, sig) in enumerate(WIRES):
        x = hx + i * 1.1
        ax.add_patch(Circle((x, hy), 0.22, fc="#ffd166", ec="#111", zorder=5))
        ax.text(x, hy - 0.42, hole, color="white", fontsize=8.5, weight="bold", ha="center", va="top")
        ax.plot([px[n], px[n], x, x], [by - 0.35, 2.3 - i * 0.3, 2.3 - i * 0.3, hy + 0.22], color=colr, lw=3.2,
                solid_capstyle="round", zorder=4)
    # table
    rows = ["Encoder pin   wire      perfboard J5   breadboard          signal"] + [
        f"{n:<13} {['orange', 'black', 'pink', 'grey'][i]:<9} {hole:<14} {bb:<19} {sig}" for i, (n, colr, hole, bb, sig) in enumerate(WIRES)
    ] + ["DIR           short     -              -                   to the encoder's own GND pin (on the encoder)",
         "OUT, GPO      -         -              -                   not connected"]
    ax.text(0.5, -1.3, "\n".join(rows), family="monospace", fontsize=9, va="top",
            bbox=dict(fc="#fafafa", ec="#999", pad=0.6))
    ax.text(0.5, -4.4, "Pin order differs between AS5600 boards: match the NAMES printed on your board, not the positions.\n"
            "Why DIR: it sets the counting direction and must not float; a floating DIR can flip the sign at random.\n"
            "Check: in the bench test, 'i' finds a device at 0x36 and 's' says magnet DETECTED.",
            fontsize=8.5, va="top", color="#333")
    ax.set_xlim(0, 13.4); ax.set_ylim(-5.6, 7.4); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("AS5600 encoder wiring (Rev D station): 4 wires to the board + DIR tied to GND on the encoder", loc="left", fontsize=11)
    for ext in ("png", "pdf"):
        fig.savefig(HERE / f"encoder_wiring.{ext}", dpi=170, bbox_inches="tight")
    print("wrote encoder_wiring.png / .pdf")


if __name__ == "__main__":
    main()
