"""Render the six deck v10 charts as PNGs (matplotlib, Agg) from chart_data.json.

The build script (build_deck_v10.js) holds the one source of numbers: it writes chart_data.json (the data arrays plus the
size in inches of the box each chart fills on the slide) and runs this file before placing the images with addImage.
Native pptxgenjs charts were dropped in v10.1: PowerPoint reported the file as needing repair; the images carry the same data.

    /usr/bin/python3 docs/presentation/deck_v10/make_charts.py [chart_data.json] [out_dir]
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).parent
NAVY, GREY, PALE, INK, MID, RULE = "#1F3A5F", "#8A8F98", "#BFC4CB", "#000000", "#404040", "#D9DEE5"
DPI = 300

plt.rcParams.update({
    "font.family": ["Arial", "Liberation Sans", "DejaVu Sans"], "font.size": 7.5, "axes.titlesize": 8.5, "axes.titleweight": "bold",
    "axes.titlecolor": INK, "axes.labelsize": 7.5, "axes.labelcolor": MID, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "xtick.color": MID, "ytick.color": MID, "axes.edgecolor": PALE, "axes.linewidth": 0.6, "legend.fontsize": 7.5, "legend.frameon": False,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
})


def frame(ax, grid="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if grid == "y":
        ax.yaxis.grid(True, color=RULE, linewidth=0.5)
    elif grid == "x":
        ax.xaxis.grid(True, color=RULE, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def fig_for(box, title=None):
    fig = plt.figure(figsize=(box["w"], box["h"]), dpi=DPI)
    if title:
        fig.text(0.02, 0.97, title, ha="left", va="top", fontsize=8.5, fontweight="bold", color=INK)
    return fig


def save(fig, out):
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def bead(d, out):
    fig = fig_for(d["box"], d["title"]); ax = fig.add_axes([0.17, 0.12, 0.78, 0.76])
    ax.plot([p[0] for p in d["points"]], [p[1] for p in d["points"]], color=NAVY, linewidth=1.6, marker="o", markersize=2.5)
    ax.set_xlabel("Homing height (m)")
    ax.set_ylim(0, 40); ax.set_yticks([0, 10, 20, 30, 40]); ax.set_xticks([0.5, 1.0, 1.5, 2.0])
    frame(ax); save(fig, out)


def tension(d, out):
    fig = fig_for(d["box"], d["title"]); ax = fig.add_axes([0.1, 0.18, 0.86, 0.66])
    x = d["depths"]
    ax.plot(x, d["static"], color=NAVY, linewidth=1.4, label="Static (calc)")
    ax.plot(x, d["dynamic"], color=GREY, linewidth=1.4, label="With 1 m/s² (design)")
    ax.plot(x, [d["limit"]] * len(x), color=INK, linewidth=1.1, linestyle="--", label="Limit 16.8 N (calc)")
    ax.set_ylim(0, 50); ax.set_yticks(range(0, 51, 10)); ax.set_xticks([0.2, 0.4, 0.6, 0.8, 1.0, 1.2])
    ax.legend(loc="upper right", handlelength=1.6, fontsize=7)
    frame(ax); save(fig, out)


def temperature(d, out):
    fig = fig_for(d["box"], d["title"]); ax = fig.add_axes([0.1, 0.3, 0.86, 0.54])
    n = len(d["labels"]); w = 0.22; xs = range(n)
    for k, (name, vals, col) in enumerate([("No fin", d["noFin"], PALE), ("0.019 in fin (measured)", d["thin"], NAVY), ("1/8 in fin (design)", d["plate"], GREY)]):
        pos = [i + (k - 1) * w for i in xs]
        bars = ax.bar(pos, vals, width=w * 0.92, color=col, label=name)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.0f}", ha="center", va="bottom", fontsize=7, color=MID)
    ax.axhline(d["limit"], color=INK, linewidth=0.9, linestyle="--", label="60 °C limit (design)")
    ax.set_xticks(list(xs)); ax.set_xticklabels(d["labels"]); ax.set_ylim(0, 120); ax.set_yticks(range(0, 121, 30))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, handlelength=1.0, columnspacing=1.0, fontsize=6.5)
    frame(ax); save(fig, out)


def pull(d, out):
    fig = fig_for(d["box"], d["title"]); ax = fig.add_axes([0.1, 0.3, 0.86, 0.54])
    x = d["radii"]
    ax.plot(x, d["running"], color=NAVY, linewidth=1.4, label="Running pull (calc)")
    ax.plot(x, d["design"], color=GREY, linewidth=1.4, linestyle="--", label="÷ 1.5 (design)")
    ax.plot(x, [d["jeans"]] * len(x), color=INK, linewidth=1.1, linestyle="--", label=f"Jeans {d['jeans']:.1f} N (calc)")
    ax.set_ylim(0, 50); ax.set_yticks(range(0, 51, 10)); ax.set_xticks([6, 7, 8, 9, 10, 11])
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, handlelength=1.4, columnspacing=1.0, fontsize=6.5)
    frame(ax); save(fig, out)


def lift(d, out):
    fig = fig_for(d["box"], d["title"]); ax = fig.add_axes([0.34, 0.14, 0.6, 0.7])
    ys = range(len(d["labels"]))
    bars = ax.barh(list(ys), d["values"], color=d["colors"], height=0.6)
    for b, v in zip(bars, d["values"]):
        ax.text(v + 0.03, b.get_y() + b.get_height() / 2, f"{v:.2f}", va="center", fontsize=7.5, color=MID)
    ax.set_yticks(list(ys)); ax.set_yticklabels(d["labels"]); ax.set_xlim(0, 2.0); ax.set_xticks([0, 0.5, 1.0, 1.5, 2.0])
    frame(ax, grid="x"); save(fig, out)


def weakest(d, out):
    fig = fig_for(d["box"], d["title"]); ax = fig.add_axes([0.3, 0.14, 0.66, 0.7])
    ys = range(len(d["rows"]))
    lows = [r[1] for r in d["rows"]]; highs = [r[2] - r[1] for r in d["rows"]]
    ax.barh(list(ys), lows, color=NAVY, height=0.62)
    ax.barh(list(ys), highs, left=lows, color=PALE, height=0.62)
    ax.set_yticks(list(ys)); ax.set_yticklabels([r[0] for r in d["rows"]], fontsize=7); ax.set_xlim(0, 600); ax.set_xticks([0, 200, 400, 600])
    frame(ax, grid="x"); save(fig, out)


def main(data_file=HERE / "chart_data.json", out_dir=HERE / "fig"):
    data = json.loads(Path(data_file).read_text())
    out_dir = Path(out_dir); out_dir.mkdir(exist_ok=True)
    for name, fn in [("bead", bead), ("tension", tension), ("temperature", temperature), ("pull", pull), ("lift", lift), ("weakest", weakest)]:
        fn(data[name], out_dir / f"{name}.png")
        print(f"{name}.png")


if __name__ == "__main__":
    main(*(Path(a) for a in sys.argv[1:3]))
