"""Routing grid and geometry helpers for the RoomCleaner Station Rev E router (own code, no
external routing tools).  The search itself is in pathfinder.py.

Geometry model (mm, board coordinates, y down):
  obstacle items: dict(kind, net, clr, ...)
      kind 'circle': cx, cy, r
      kind 'rect'  : cx, cy, hw, hh          (axis-aligned)
      kind 'seg'   : x1, y1, x2, y2, r       (capsule; r = half track width)
  A cell is free for a track of half-width hw of net N if, for every item of another
  net, distance(cell centre, item) >= max(clr_N, clr_item) + hw + MARGIN.
"""
import heapq
import math

import numpy as np

SQ2 = math.sqrt(2.0)
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
NO_DIR = 8


class Grid:
    def __init__(self, width, height, pitch, edge_clr, margin=0.05):
        self.pitch = pitch
        self.nx = int(round(width / pitch)) + 1
        self.ny = int(round(height / pitch)) + 1
        self.W, self.H = width, height
        self.edge_clr = edge_clr
        self.margin = margin
        xs = np.arange(self.nx) * pitch
        ys = np.arange(self.ny) * pitch
        self.X, self.Y = np.meshgrid(xs, ys)          # shape (ny, nx)
        self.edge_dist = np.minimum(np.minimum(self.X, width - self.X), np.minimum(self.Y, height - self.Y))

    # -- coordinates -----------------------------------------------------------
    def cell(self, x, y):
        return int(round(x / self.pitch)), int(round(y / self.pitch))

    def xy(self, i, j):
        return i * self.pitch, j * self.pitch

    def idx(self, i, j):
        return j * self.nx + i

    # -- distance of every cell in a window to an item ---------------------------
    def _window(self, x0, y0, x1, y1):
        i0 = max(0, int(math.floor(x0 / self.pitch)))
        j0 = max(0, int(math.floor(y0 / self.pitch)))
        i1 = min(self.nx, int(math.ceil(x1 / self.pitch)) + 1)
        j1 = min(self.ny, int(math.ceil(y1 / self.pitch)) + 1)
        return i0, j0, i1, j1

    def dist_window(self, it, R):
        """(slice, distance array) for the window of cells that can be within R of item."""
        k = it["kind"]
        if k == "circle":
            bb = (it["cx"] - it["r"] - R, it["cy"] - it["r"] - R, it["cx"] + it["r"] + R, it["cy"] + it["r"] + R)
        elif k == "rect":
            bb = (it["cx"] - it["hw"] - R, it["cy"] - it["hh"] - R, it["cx"] + it["hw"] + R, it["cy"] + it["hh"] + R)
        else:
            bb = (min(it["x1"], it["x2"]) - it["r"] - R, min(it["y1"], it["y2"]) - it["r"] - R,
                  max(it["x1"], it["x2"]) + it["r"] + R, max(it["y1"], it["y2"]) + it["r"] + R)
        i0, j0, i1, j1 = self._window(*bb)
        if i0 >= i1 or j0 >= j1:
            return None, None
        X = self.X[j0:j1, i0:i1]
        Y = self.Y[j0:j1, i0:i1]
        if k == "circle":
            d = np.hypot(X - it["cx"], Y - it["cy"]) - it["r"]
        elif k == "rect":
            dx = np.maximum(np.abs(X - it["cx"]) - it["hw"], 0)
            dy = np.maximum(np.abs(Y - it["cy"]) - it["hh"], 0)
            d = np.hypot(dx, dy)
        else:
            ax, ay, bx, by = it["x1"], it["y1"], it["x2"], it["y2"]
            vx, vy = bx - ax, by - ay
            L2 = vx * vx + vy * vy
            if L2 == 0:
                t = np.zeros_like(X)
            else:
                t = np.clip(((X - ax) * vx + (Y - ay) * vy) / L2, 0, 1)
            d = np.hypot(X - (ax + t * vx), Y - (ay + t * vy)) - it["r"]
        return (slice(j0, j1), slice(i0, i1)), d

    def blocked_mask(self, items, net, clr, hw, extra_edge=0.0, layer=None):
        """Boolean (ny, nx) array: True where the centre of a track/pad of this net may NOT be.
        layer: only items on that copper layer count (None = all layers)."""
        m = self.edge_dist < self.edge_clr + hw + extra_edge + self.margin
        for it in items:
            if it["net"] == net and net is not None:
                continue
            if layer is not None and layer not in it.get("layers", (0, 1)):
                continue
            R = max(clr, it["clr"]) + hw + self.margin
            sl, d = self.dist_window(it, R)
            if sl is None:
                continue
            m[sl] |= d < R
        return m


def turn_cost(d0, d1):
    if d0 == NO_DIR:
        return 0.0
    t = (d1 - d0) % 8
    if t == 0:
        return 0.0
    if t in (1, 7):
        return 0.35
    if t in (2, 6):
        return 2.0
    return None            # 135 deg or reversal: forbidden (no acute corners)


def simplify(points):
    """Drop interior points of straight runs. points: list of (i, j)."""
    if len(points) <= 2:
        return list(points)
    out = [points[0]]
    for k in range(1, len(points) - 1):
        a, b, c = out[-1], points[k], points[k + 1]
        d1 = (np.sign(b[0] - a[0]), np.sign(b[1] - a[1]))
        d2 = (np.sign(c[0] - b[0]), np.sign(c[1] - b[1]))
        if d1 != d2:
            out.append(b)
    out.append(points[-1])
    return out
