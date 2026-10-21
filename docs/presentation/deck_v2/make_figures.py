"""New figures for deck v2 (plain, professional style): position vectors, wiring comparison, bead reach, calibration loop.

    /usr/bin/python3 docs/presentation/deck_v2/make_figures.py      -> docs/presentation/deck_v2/fig/*.png

Numbers: room 11 x 9 x 9 ft (3.3528 x 2.7432 x 2.7432 m), anchors 0.05 m in from the corners at 2.5932 m
(config/robot.sim.json), cable routes 6/21/23/32 ft (docs/ROOM_LAYOUT_20261014.md), margins 0.2 m walls / 0.4 m
ceiling (D26). Everything here is geometry, no measured data.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).parent / "fig"
OUT.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "Carlito" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"mathtext.fontset": "custom", "mathtext.rm": "Carlito", "mathtext.it": "Carlito:italic", "mathtext.bf": "Carlito:bold", "font.family": "Carlito", "font.size": 14, "axes.edgecolor": "#8a8f98", "axes.labelcolor": "#1a1a1a",
                     "xtick.color": "#4a4f58", "ytick.color": "#4a4f58", "savefig.dpi": 220})
NAVY, INK, GREY, LIGHT, RED = "#1F3A5F", "#1A1A1A", "#8A8F98", "#E6E8EC", "#B23A2E"
X, Y, H = 3.3528, 2.7432, 2.7432
A = np.array([[0.05, 0.05, 2.5932], [3.3028, 0.05, 2.5932], [3.3028, 2.6932, 2.5932], [0.05, 2.6932, 2.5932]])


def position_vectors():
    fig = plt.figure(figsize=(7.2, 5.6))
    ax = fig.add_subplot(projection="3d")
    ax.set_proj_type("ortho")
    # room edges
    c = np.array([[0, 0, 0], [X, 0, 0], [X, Y, 0], [0, Y, 0]])
    for z in (0, H):
        q = c + [0, 0, z]
        ax.plot(*np.vstack([q, q[:1]]).T, color=LIGHT if z else GREY, lw=1.2)
    for p in c:
        ax.plot([p[0]] * 2, [p[1]] * 2, [0, H], color=LIGHT, lw=1.2)
    p = np.array([2.0, 1.2, 0.9])
    for i, a in enumerate(A):
        ax.plot(*np.vstack([a, p]).T, color=NAVY, lw=2.2)
        ax.scatter(*a, color=NAVY, s=40, depthshade=False)
        ax.text(*(a + [0, 0, 0.12]), rf"$\mathbf{{a}}_{i + 1}$", color=NAVY, fontsize=17, ha="center")
        mid = (a + p) / 2
        ax.text(*(mid + [0.05, 0.05, 0.05]), rf"$\mathbf{{l}}_{i + 1}$", color=INK, fontsize=16)
    ax.scatter(*p, color=RED, s=70, depthshade=False)
    ax.text(*(p + [0.08, -0.1, -0.22]), r"$\mathbf{p}$ (claw)", color=RED, fontsize=16)
    o = np.zeros(3)
    ax.quiver(*o, *p, color=GREY, lw=1.2, arrow_length_ratio=0.06)
    ax.text(0.95, 0.5, 0.25, r"$\mathbf{p}$", color=GREY, fontsize=14)
    ax.text(-0.25, -0.25, -0.1, "O", color=INK, fontsize=12)
    ax.set_box_aspect((X, Y, H)); ax.view_init(elev=18, azim=-58); ax.set_axis_off()
    fig.text(0.5, 0.06, r"$\mathbf{l}_i = \mathbf{a}_i - \mathbf{p}$        $L_i = \Vert\mathbf{a}_i - \mathbf{p}\Vert$        $\mathbf{u}_i = \mathbf{l}_i \,/\, L_i$", ha="center", fontsize=19, color=INK)
    fig.savefig(OUT / "position_vectors.png", bbox_inches="tight", transparent=False, facecolor="white")
    plt.close(fig)


def wiring():
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.8))
    runs = [6, 21, 23, 32]
    corners = [(0.08, 0.92), (0.92, 0.92), (0.92, 0.08), (0.08, 0.08)]
    for ax, central in zip(axs, (True, False)):
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal"); ax.axis("off")
        ax.add_patch(FancyBboxPatch((0.02, 0.02), 0.96, 0.96, boxstyle="round,pad=0,rounding_size=0.02", fc="white", ec=LIGHT, lw=1.5, zorder=0))
        hub = (0.5, 0.5)
        ax.add_patch(FancyBboxPatch((0.38, 0.42), 0.24, 0.16, boxstyle="round,pad=0.01", fc=NAVY if central else "white",
                                    ec=NAVY, lw=1.5, zorder=3))
        ax.text(0.5, 0.5, "controller +\n4 drivers" if central else "12 V supply\n+ fuses", ha="center", va="center",
                color="white" if central else NAVY, fontsize=12, zorder=4)
        for (cx, cy), run in zip(corners, runs):
            ax.add_patch(FancyBboxPatch((cx - 0.06, cy - 0.05), 0.12, 0.10, boxstyle="round,pad=0.005",
                                        fc="white" if central else NAVY, ec=NAVY, lw=1.5, zorder=3))
            ax.text(cx, cy, "motor" if central else "station", ha="center", va="center", fontsize=10.5,
                    color=NAVY if central else "white", zorder=4)
            ax.plot([hub[0], cx], [hub[1], cy], color=NAVY, lw=7 if central else 2, alpha=.85, solid_capstyle="round", zorder=1)
            mx, my = (hub[0] + cx) / 2, (hub[1] + cy) / 2
            ax.text(mx, my + 0.05, f"{run} ft", ha="center", fontsize=11, color=INK,
                    bbox=dict(fc="white", ec="none", pad=0.5))
        ax.set_title("One central box: 10 wires per corner" if central else "Controller in every station: 2 wires per corner",
                     fontsize=15, color=INK, pad=8)
        ax.text(0.5, -0.06, "motor 4 + switch 2 + encoder 4  →  ≈ 820 ft of conductor" if central
                else "12 V + ground only  →  ≈ 164 ft of conductor", ha="center", fontsize=13, color=NAVY if not central else RED)
    fig.savefig(OUT / "wiring_comparison.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def bead_reach():
    """Side view through the room centre (x-z): where the claw can go if all four beads home at the centre."""
    xs = np.linspace(0.2, X - 0.2, 360); zs = np.linspace(0.3, 2.19, 220)
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    xy = np.stack(np.meshgrid(np.linspace(0.2, X - 0.2, 60), np.linspace(0.2, Y - 0.2, 50), indexing="ij"), -1).reshape(-1, 2)
    for ax, zh in zip(axs, (1.0, 2.0)):
        home = np.array([X / 2, Y / 2, zh]); Lh = np.linalg.norm(A - home, axis=1)
        XX, ZZ = np.meshgrid(xs, zs)
        P = np.stack([XX, np.full_like(XX, Y / 2), ZZ], -1)
        L = np.linalg.norm(P[..., None, :] - A, axis=-1)
        ok = (L >= Lh - 1e-9).all(-1)
        ax.contourf(XX, ZZ, ok.astype(float), levels=[0.5, 1.5], colors=[NAVY], alpha=.85)
        ax.contourf(XX, ZZ, (~ok).astype(float), levels=[0.5, 1.5], colors=[LIGHT])
        ax.plot([0, X, X, 0, 0], [0, 0, H, H, 0], color=GREY, lw=1.2)
        for a in A[:2]:
            ax.plot(a[0], a[2], "s", color=INK, ms=7)
        ax.plot(home[0], home[2], "o", color=RED, ms=9)
        ax.text(home[0] + 0.08, home[2] + 0.06, "homing point", color=RED, fontsize=12)
        # whole-volume fraction
        Pv = np.stack(np.meshgrid(np.linspace(0.2, X - 0.2, 60), np.linspace(0.2, Y - 0.2, 50), np.linspace(0.3, 2.19, 50),
                                  indexing="ij"), -1).reshape(-1, 3)
        frac = (np.linalg.norm(Pv[:, None] - A, axis=2) >= Lh - 1e-9).all(1).mean()
        ax.set_title(f"Homing point {zh:.0f} m up: {100 * frac:.0f} % of the room reachable", fontsize=14, color=INK)
        ax.set_xlabel("across the room (m)"); ax.set_xlim(-0.05, X + 0.05); ax.set_ylim(-0.05, H + 0.12)
        ax.spines[["top", "right"]].set_visible(False)
    axs[0].set_ylabel("height (m)")
    fig.text(0.5, -0.03, "Navy = reachable. A bead cannot pass its outlet, so no cable can get shorter than its homing length.",
             ha="center", fontsize=13, color=INK)
    fig.savefig(OUT / "bead_reach.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def calibration_loop():
    steps = ["Take up slack,\none cable\nat a time", "Lift the claw\noff the floor", "Camera reads\nthe floor board",
             "Fit anchors and\ncable lengths", "Check on\nheld-out poses", "Ready, inside\nthe safe margins"]
    fig, ax = plt.subplots(figsize=(11, 3.0)); ax.set_xlim(0, 6); ax.set_ylim(-0.15, 1.0); ax.axis("off")
    for i, s in enumerate(steps):
        last = i == len(steps) - 1
        ax.add_patch(FancyBboxPatch((i + 0.06, 0.28), 0.84, 0.62, boxstyle="round,pad=0.02,rounding_size=0.06",
                                    fc=NAVY if last else "white", ec=NAVY, lw=1.6))
        ax.text(i + 0.48, 0.59, s, ha="center", va="center", fontsize=12.5, color="white" if last else INK, linespacing=1.15)
        if not last:
            ax.add_patch(FancyArrowPatch((i + 0.92, 0.59), (i + 1.04, 0.59), arrowstyle="-|>", mutation_scale=16, color=GREY))
    ax.annotate("", xy=(3.48, 0.24), xytext=(4.48, 0.24), arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.3, connectionstyle="arc3,rad=-0.45"))
    ax.text(3.98, -0.11, "more poses if the fit is not good enough", ha="center", fontsize=11.5, color=GREY)
    fig.savefig(OUT / "calibration_loop.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    position_vectors(); wiring(); bead_reach(); calibration_loop()
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))
