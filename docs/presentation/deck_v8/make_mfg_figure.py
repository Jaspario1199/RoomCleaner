"""Manufacturing detail figure for deck v8: Jasper's own geometry, cut from his STEP files.

Panels:
  1. Gear bearing pocket (compound 36T/24T gear of the 1021 claw): section through the pocket axis.
  2. The same pocket's entry lip seen from above: the Ø14.000 lip is cut by 8 T-slots (a 0.4 mm gap backed by a 0.5 mm slot),
     so the lip ends flex outward as the bearing snaps past.
  3. Slide-in mount in the wall mount: horizontal section through one dovetail, with the measured gaps.
  4. Heat fin: Jasper's mill method: the edges locate the bottom-left hole, which then becomes the zero for the other four.

    /usr/bin/python3 docs/presentation/deck_v8/make_mfg_figure.py   -> docs/presentation/deck_v8/fig/mfg_details.png
"""
import math
import sys
from pathlib import Path

import cadquery as cq
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.gp import gp_Dir, gp_Pln, gp_Pnt
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from cad import params as P                     # noqa: E402
from cad.parts import heat_fin1021 as FIN       # noqa: E402

GEAR = ROOT / "cad/reference/gripper_1021/parts/10_gripper_v6r_compound_36T_24T_norelief_NAUO10.step"
SLIPIN = ROOT / "cad/reference/station_1021/Slipin_mount_piecev3.step"
WALL = ROOT / "cad/reference/station_1021/Wall_Mount_v3.step"
OUT = Path(__file__).parent / "fig" / "mfg_details.png"
AXIS = (970.00, 721.41)            # compound gear pocket axis (x, y) in the 1021 assembly frame [measured]
Z0 = 1082.99                       # gear bottom face
INK, MUTED, NAVY, RED, PALE = "#1A1A1A", "#5B6370", "#1F3A5F", "#B23A2E", "#D9DEE5"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})


def section(shape, point, normal, n=60):
    sec = BRepAlgoAPI_Section(shape.wrapped, gp_Pln(gp_Pnt(*point), gp_Dir(*normal)))
    sec.Build()
    ex = TopExp_Explorer(sec.Shape(), TopAbs_EDGE)
    out = []
    while ex.More():
        c = BRepAdaptor_Curve(TopoDS.Edge_s(ex.Current()))
        ts = np.linspace(c.FirstParameter(), c.LastParameter(), n)
        out.append(np.array([[c.Value(t).X(), c.Value(t).Y(), c.Value(t).Z()] for t in ts]))
        ex.Next()
    return out


def dim(ax, p0, p1, text, off=(0, 0), color=INK, size=8, ha="center"):
    ax.annotate("", p1, p0, arrowprops=dict(arrowstyle="<->", lw=0.8, color=color, shrinkA=0, shrinkB=0))
    m = ((p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1])
    ax.text(*m, text, ha=ha, va="center", fontsize=size, color=color)


def panel_pocket_section(ax, gear):
    a = math.radians(22.5)                                  # cut between two relief notches (they sit every 45 deg from 0)
    d = np.array([math.cos(a), math.sin(a), 0.0])
    nrm = (-math.sin(a), math.cos(a), 0.0)
    for s in section(gear, (AXIS[0], AXIS[1], 1100.0), nrm):
        u = (s[:, 0] - AXIS[0]) * d[0] + (s[:, 1] - AXIS[1]) * d[1]
        if np.min(np.abs(u)) > 13:
            continue
        ax.plot(u, s[:, 2] - Z0, color=INK, lw=0.9)
    # the 687 bearings (7 x 14 x 5): one in the lower pocket, two in the upper
    for z in (1.95, 24.0, 29.0):
        for sgn in (-1, 1):
            ax.add_patch(plt.Rectangle((sgn * 3.5 if sgn > 0 else -7.0, z), 3.5, 5.0, fc=PALE, ec=NAVY, lw=0.6, zorder=0))
    ax.set_xlim(-13, 13)
    ax.set_ylim(-1.5, 37.5)
    ax.set_aspect("equal")
    ax.axvline(0, color=MUTED, lw=0.5, ls=(0, (6, 2, 1, 2)))
    dim(ax, (-7.0, -0.9), (7.0, -0.9), "lip Ø14.000", off=(0, -0.9))
    dim(ax, (-7.0375, 34.6), (7.0375, 34.6), "pocket Ø14.075", off=(0, 1.0))
    ax.annotate("entry lip, 1.95 long", (7.0, 1.0), (8.6, 4.8), fontsize=8, color=RED, arrowprops=dict(arrowstyle="-", lw=0.6, color=RED))
    ax.annotate("687 bearing\n7 × 14 × 5", (5.25, 26.5), (8.0, 18.5), fontsize=8, color=NAVY, arrowprops=dict(arrowstyle="-", lw=0.6, color=NAVY))
    ax.annotate("shoulder Ø8.3", (4.15, 13.0), (5.0, 11.0), fontsize=8, color=MUTED)
    ax.set_title("1  Gear bearing pocket, section (mm)", loc="left", fontsize=10, color=INK, weight="bold")
    ax.axis("off")


def panel_lip_plan(ax, gear):
    for s in section(gear, (0, 0, Z0 + 1.0), (0, 0, 1)):
        x, y = s[:, 0] - AXIS[0], s[:, 1] - AXIS[1]
        if np.min(np.hypot(x, y)) > 9.5:
            continue
        ax.plot(x, y, color=INK, lw=0.9)
    t = np.linspace(0, 2 * math.pi, 200)
    ax.plot(7.0375 * np.cos(t), 7.0375 * np.sin(t), color=MUTED, lw=0.6, ls="--")
    ax.set_xlim(-10, 10)
    ax.set_ylim(-10, 10)
    ax.set_aspect("equal")
    ax.text(0, 1.1, "8 T-slots: 0.4 gap in the lip,\n0.5 slot behind it;\nthe lip ends flex as\nthe bearing snaps past", ha="center", va="center", fontsize=8, color=RED)
    ax.text(0, -2.6, "dashed: pocket Ø14.075\nbehind the lip", ha="center", va="center", fontsize=8, color=MUTED)
    ax.set_title("2  Entry lip from above", loc="left", fontsize=10, color=INK, weight="bold")
    ax.axis("off")


def panel_dovetail(ax, slipin, wall):
    y0, y1, x0, x1 = -42.5, -26.5, -43.0, -26.0            # one outer rib (y = -34.4)
    for shape, col, lw in ((wall, NAVY, 1.0), (slipin, RED, 1.0)):
        for s in section(shape, (0, 0, 11.1), (0, 0, 1)):
            m = (s[:, 1] > y0 - 2) & (s[:, 1] < y1 + 2) & (s[:, 0] > x0 - 2) & (s[:, 0] < x1 + 2)
            if m.any():
                ax.plot(s[:, 1], s[:, 0], color=col, lw=lw)
    ax.set_xlim(y0, y1)
    ax.set_ylim(x0, x1)
    ax.set_aspect("equal")
    ax.text(-41.8, -27.2, "slide-in", color=RED, fontsize=8.5, weight="bold")
    ax.text(-41.8, -42.3, "wall mount", color=NAVY, fontsize=8.5, weight="bold")
    ax.annotate("0.175 per side\n(deck, rib tip, lips, ends)", (-30.0, -29.7), (-31.8, -33.4), fontsize=8, color=INK,
                arrowprops=dict(arrowstyle="-", lw=0.6, color=INK))
    ax.annotate("30° flanks:\n0.14 and 0.21", (-37.6, -32.6), (-41.6, -38.6), fontsize=8, color=INK,
                arrowprops=dict(arrowstyle="-", lw=0.6, color=INK))
    ax.set_title("3  Slide-in dovetail, section", loc="left", fontsize=10, color=INK, weight="bold")
    ax.axis("off")


def panel_fin(ax):
    """Jasper's mill method (10/22): the two edges locate only the bottom-left M3 hole; once drilled, that hole is the mill's
    zero and the other four holes are positioned from it, so the sheared edges (±0.5) do not move the hole pattern."""
    W = P.FIN1021_X_MAX - P.FIN1021_X_MIN                   # 42.0
    show = 72.0                                             # lower part of the 228.6 mm plate
    ax.plot([0, 0, W, W], [show, 0, 0, show], color=INK, lw=1.0)          # left side, bottom edge, long side
    ax.plot([-1, W + 1], [show, show], color=MUTED, lw=0.6, ls=(0, (4, 2)))
    ax.text(W / 2, show + 2.0, "plate continues: 195.6 / 228.6 tall", ha="center", fontsize=7.5, color=MUTED)
    rows = FIN.hole_table()
    t = np.linspace(0, 2 * math.pi, 120)
    for i, d, X, XB, Y in rows:
        ax.plot(X + d / 2 * np.cos(t), Y + d / 2 * np.sin(t), color=NAVY, lw=0.9)
    zero = rows[1]                                          # hole 2: lower left M3
    x0, y0 = zero[2], zero[4]
    ax.plot([x0 - 4, x0 + 4], [y0, y0], color=RED, lw=0.8)
    ax.plot([x0, x0], [y0 - 4, y0 + 4], color=RED, lw=0.8)
    ax.text(x0 + 2.4, y0 + 2.2, "X0 Y0", color=RED, fontsize=8, weight="bold")
    dim(ax, (0, -4.0), (x0, -4.0), f"{x0:.1f}", off=(0, -2.2), size=7.5, color=RED)
    dim(ax, (-4.0, 0), (-4.0, y0), f"{y0:.1f}", off=(-3.0, 0), size=7.5, color=RED)
    for i, d, X, XB, Y in rows[2:]:
        ax.text(X + 2.2, Y + 2.2, f"({X - x0:.0f}, {Y - y0:.0f})", fontsize=7.5, color=NAVY)
    pil = rows[0]
    ax.text(pil[2], pil[4] + 2.0, f"Ø{pil[1]:.1f}", ha="center", va="center", fontsize=7.5, color=NAVY)
    ax.text(pil[2], pil[4] - 2.4, f"({pil[2] - x0:.1f}, {pil[4] - y0:.1f})", ha="center", va="center", fontsize=7.5, color=NAVY)
    ax.text(W / 2, 46.0, "edges locate the\nfirst hole only;\ndrilled, it is the\nzero for the rest", ha="center",
            fontsize=7.2, color=INK)
    ax.set_xlim(-14, W + 14)
    ax.set_ylim(-10, show + 5)
    ax.set_aspect("equal")
    ax.set_title("4  Heat fin: first hole is the mill zero", loc="left", fontsize=10, color=INK, weight="bold")
    ax.axis("off")


def main():
    gear = cq.importers.importStep(str(GEAR)).val()
    slipin = cq.importers.importStep(str(SLIPIN)).val()
    wall = cq.importers.importStep(str(WALL)).val()
    fig, axs = plt.subplots(2, 2, figsize=(7.4, 6.2), dpi=220)
    panel_pocket_section(axs[0, 0], gear)
    panel_lip_plan(axs[0, 1], gear)
    panel_dovetail(axs[1, 0], slipin, wall)
    panel_fin(axs[1, 1])
    fig.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.02, wspace=0.08, hspace=0.18)
    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, facecolor="white")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
