"""
Helpers for the VEX-standard tri-ball mechanism.

Two things every VEX plate needs and CadQuery doesn't give you directly:

  * a 1/2" HEX bore (sized by across-flats, not the circumscribed circle), and
  * the 0.5" hole GRID -- the field of #8-32 clearance holes that lets any VEX
    bearing flat, standoff, gear plate, or C-channel bolt anywhere on the part.

`grid_points()` returns only the grid intersections that sit safely inside a
part outline (with edge margin) and clear of the big shaft bores, so the plate
comes out looking like real laser-cut VEX steel instead of a slab with holes
punched off the edge.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence


def hex_across_corners(across_flats: float) -> float:
    """Vertex-to-vertex size of a regular hexagon given its across-flats size.

    CadQuery's ``.polygon(6, d)`` inscribes the polygon in a circle of diameter
    ``d`` (i.e. ``d`` is across-corners). VEX hex is specified across-flats, so
    convert: across_corners = across_flats * 2 / sqrt(3).
    """
    return across_flats * 2.0 / math.sqrt(3.0)


def _seg_dist(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    """Distance from point (px,py) to segment (ax,ay)-(bx,by)."""
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def point_in_poly(px: float, py: float, poly: Sequence[Sequence[float]]) -> bool:
    """Even-odd ray cast: is (px,py) strictly inside polygon ``poly``?"""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > py) != (yj > py):
            x_cross = (xj - xi) * (py - yi) / (yj - yi) + xi
            if px < x_cross:
                inside = not inside
        j = i
    return inside


def min_edge_dist(px: float, py: float, poly: Sequence[Sequence[float]]) -> float:
    n = len(poly)
    return min(
        _seg_dist(px, py, poly[i][0], poly[i][1], poly[(i + 1) % n][0], poly[(i + 1) % n][1])
        for i in range(n)
    )


def grid_points(
    poly: Sequence[Sequence[float]],
    pitch: float,
    margin: float,
    keepouts: Iterable[Sequence[float]] = (),
    origin: Sequence[float] = (0.0, 0.0),
) -> list[tuple[float, float]]:
    """Grid intersections inside ``poly`` at ``pitch`` spacing.

    Kept only if the point is inside the outline, at least ``margin`` from every
    edge, and outside every keepout circle ``(cx, cy, r)``.
    """
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    ox, oy = origin
    i0 = math.floor((min(xs) - ox) / pitch)
    i1 = math.ceil((max(xs) - ox) / pitch)
    j0 = math.floor((min(ys) - oy) / pitch)
    j1 = math.ceil((max(ys) - oy) / pitch)
    kos = list(keepouts)
    out: list[tuple[float, float]] = []
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            x = ox + i * pitch
            y = oy + j * pitch
            if not point_in_poly(x, y, poly):
                continue
            if min_edge_dist(x, y, poly) < margin:
                continue
            if any(math.hypot(x - cx, y - cy) < r for (cx, cy, r) in kos):
                continue
            out.append((x, y))
    return out
