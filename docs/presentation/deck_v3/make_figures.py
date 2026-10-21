"""Deck v3 figure: position vectors without the formula line (the formulas sit in the slide's equation box).

    /usr/bin/python3 docs/presentation/deck_v3/make_figures.py      -> docs/presentation/deck_v3/fig/position_vectors.png

Same geometry and style as deck_v2/make_figures.py (room 11 x 9 x 9 ft, anchors 0.05 m in from the corners at
2.5932 m, claw at (2.0, 1.2, 0.9) m). All other deck v3 charts come from the Google Sheet (sheet_charts.py).
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("v2figs", HERE.parent / "deck_v2" / "make_figures.py")
v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)
plt, np = v2.plt, v2.np


def position_vectors():
    X, Y, H, A = v2.X, v2.Y, v2.H, v2.A
    fig = plt.figure(figsize=(7.2, 5.2))
    ax = fig.add_subplot(projection="3d")
    ax.set_proj_type("ortho")
    c = np.array([[0, 0, 0], [X, 0, 0], [X, Y, 0], [0, Y, 0]])
    for z in (0, H):
        q = c + [0, 0, z]
        ax.plot(*np.vstack([q, q[:1]]).T, color=v2.LIGHT if z else v2.GREY, lw=1.2)
    for p in c:
        ax.plot([p[0]] * 2, [p[1]] * 2, [0, H], color=v2.LIGHT, lw=1.2)
    p = np.array([2.0, 1.2, 0.9])
    for i, a in enumerate(A):
        ax.plot(*np.vstack([a, p]).T, color=v2.NAVY, lw=2.2)
        ax.scatter(*a, color=v2.NAVY, s=40, depthshade=False)
        ax.text(*(a + [0, 0, 0.12]), rf"$\mathbf{{a}}_{i + 1}$", color=v2.NAVY, fontsize=17, ha="center")
        ax.text(*((a + p) / 2 + [0.05, 0.05, 0.05]), rf"$L_{i + 1}$", color=v2.INK, fontsize=16)
    ax.scatter(*p, color=v2.RED, s=70, depthshade=False)
    ax.text(*(p + [0.08, -0.1, -0.22]), r"$\mathbf{p}$ (claw)", color=v2.RED, fontsize=16)
    ax.quiver(0, 0, 0, *p, color=v2.GREY, lw=1.2, arrow_length_ratio=0.06)
    ax.text(0.95, 0.5, 0.25, r"$\mathbf{p}$", color=v2.GREY, fontsize=14)
    ax.text(-0.25, -0.25, -0.1, "O", color=v2.INK, fontsize=12)
    ax.set_box_aspect((X, Y, H)); ax.view_init(elev=18, azim=-58); ax.set_axis_off()
    out = HERE / "fig" / "position_vectors.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    position_vectors()
