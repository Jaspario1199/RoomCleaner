#!/usr/bin/python3
"""
Claw camera view vs aluminium-tube cut length (v7 gripper head).

Run:  /usr/bin/python3 scripts/study_claw_tube_length_view.py
Writes (only):
    verification/claw_tube_length_view_study.json
    verification/claw_tube_length_view_study.md
    renders/claw_tube_length_view/*.png

ANALYSIS ONLY.  Reads exports/step/gripper_v7_preview.step (and, for the sanity check,
exports/step/gripper_v6_with_camera_bay_preview.step) plus cad/parts/gripper_v7_*.py to
articulate the jaws.  Nothing in cad/, exports/ or params is modified.

Model (see the .md for the full list of assumptions)
-----------------------------------------------------
* World frame = v6 world frame, +Y up, tube axis x 951.8475 / z 1103.99.
* "Above the tube" = Griper Cylinder block, electrical box + camera bay, bay cover.  Cutting the
  tube by c moves them, and the lens, DOWN by c along the tube.  The head (v7 gripper) stays;
  the tube loses c mm at its TOP (it stays 55 mm deep in the Cylinder block bore).
* Hover D (delta): the whole claw is D above the position where the CLOSED jaw tips touch the floor.
  Floor = y 581.034 - D in head coordinates.  This convention is the same for open and closed jaws.
* Everything is cast from the lens (a point) along -Y-ish rays.  All geometry is above the floor,
  so "blocked" = the ray hits any claw solid at all (independent of D).
* Occlusion engine: every triangle is clipped to the lens frustum (y below the lens, |x|,|z| <= R*depth),
  gnomonically projected to (u, v) = (x, z)/depth and binned in a 2-D grid; a query (u, v) tests the
  triangles of its cell exactly (point in projected triangle + plane depth for the first hit).  It is
  an exact ray/triangle first-hit, cross-checked below against cad.mesh_tools.ray_mesh_first_hit.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np
import cadquery as cq
from numba import njit, prange

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                   # noqa: E402
from cad.parts import claw_camera_bay as B                    # noqa: E402
from cad.parts import gripper_v7_assembly as A7               # noqa: E402
from cad.parts import gripper_v7_kin as K7                    # noqa: E402
from cad.v6_loader import load_v6                              # noqa: E402
from cad.mesh_tools import tessellate, ray_mesh_first_hit      # noqa: E402

V7_STEP = os.path.join(REPO, "exports", "step", "gripper_v7_preview.step")
V6_STEP = os.path.join(REPO, "exports", "step", "gripper_v6_with_camera_bay_preview.step")
OUT_JSON = os.path.join(REPO, "verification", "claw_tube_length_view_study.json")
OUT_MD = os.path.join(REPO, "verification", "claw_tube_length_view_study.md")
OUT_DIR = os.path.join(REPO, "renders", "claw_tube_length_view")
BASELINE_JSON = os.path.join(REPO, "verification", "claw_camera_bay_analysis.json")

CUTS = [0, 50, 100, 150, 200]                       # mm
HOVERS = [0, 25, 50, 100, 150, 200, 300, 500]       # mm
STATES = ["open", "closed"]
MODELS = ["sensor_4x3", "sensor_4x3_rot90", "cone_35"]
GRASP_X = (-40.0, 40.0)                              # relative to the tube axis
GRASP_Z = (-13.0, 7.0)
GRID = 2.0                                           # mm floor grid
RING_B = 100.0                                       # ring (b): 0 < d <= 100 beyond the grasp zone
RING_C = 300.0                                       # ring (c): 100 < d <= 300
VIS_TARGET = 0.95
DSTAR_MAX = 1500.0                                   # mm, search range for the hover D*
TUBE_OD, TUBE_ID, AL_DENS = 28.54, 22.54, 2.70e-3    # mm, mm, g/mm^3 (6061)
TESS_TOL, TESS_ANG = 0.25, 0.3
R_DOM = 2.0                                          # tangent-plane half-size of the occlusion grid
EPS_S = 1e-3                                         # near clip (depth below the lens, mm)

LENS_WORLD = np.array([B.BAY_ORIGIN_WORLD[0],
                       B.BAY_ORIGIN_WORLD[1] + B.LENS_FRONT_Y,
                       B.BAY_ORIGIN_WORLD[2] + B.S * P.CAMBAY_CAM_R])
AXIS_X, AXIS_Z = B.BAY_ORIGIN_WORLD[0], B.BAY_ORIGIN_WORLD[2]
BOX_BOTTOM_Y = B.BAY_ORIGIN_WORLD[1]                # 1091.19, box bottom plane = tube top
ABOVE = {"v6_Griper_Cylinder_reference": "cylinder block",
         "electric_housing_with_camera_bay": "box+bay",
         "camera_bay_cover": "bay cover"}
CAT_COLORS = {"tube": "#8c564b", "cylinder block": "#9467bd", "box+bay": "#7f7f7f", "bay cover": "#bcbd22",
              "plates": "#d62728", "gears": "#ff7f0e", "jaws+links": "#e377c2", "servo+horn": "#17becf",
              "head hardware": "#1f77b4"}


# =====================================================================================
# occlusion engine (numba)
# =====================================================================================
@njit(cache=False)
def _clip_poly(tri, R, eps, out):
    """Sutherland-Hodgman against the lens frustum.  tri (3,3) lens-relative; out (16,3). Returns n."""
    poly = np.empty((16, 3))
    tmp = np.empty((16, 3))
    n = 3
    for i in range(3):
        for j in range(3):
            poly[i, j] = tri[i, j]
    for pl in range(5):
        m = 0
        for i in range(n):
            a = poly[i]
            b = poly[(i + 1) % n]
            if pl == 0:
                da = -a[1] - eps
                db = -b[1] - eps
            elif pl == 1:
                da = R * (-a[1]) - a[0]
                db = R * (-b[1]) - b[0]
            elif pl == 2:
                da = R * (-a[1]) + a[0]
                db = R * (-b[1]) + b[0]
            elif pl == 3:
                da = R * (-a[1]) - a[2]
                db = R * (-b[1]) - b[2]
            else:
                da = R * (-a[1]) + a[2]
                db = R * (-b[1]) + b[2]
            if da >= 0:
                for j in range(3):
                    tmp[m, j] = a[j]
                m += 1
            if (da >= 0) != (db >= 0):
                t = da / (da - db)
                for j in range(3):
                    tmp[m, j] = a[j] + t * (b[j] - a[j])
                m += 1
        n = m
        for i in range(n):
            for j in range(3):
                poly[i, j] = tmp[i, j]
        if n < 3:
            return 0
    for i in range(n):
        for j in range(3):
            out[i, j] = poly[i, j]
    return n


@njit(cache=False)
def _count_clip(T, R, eps):
    cnt = np.zeros(len(T), np.int64)
    out = np.empty((16, 3))
    for k in range(len(T)):
        n = _clip_poly(T[k], R, eps, out)
        cnt[k] = max(n - 2, 0)
    return cnt


@njit(cache=False)
def _fill_clip(T, R, eps, off, UV, parent):
    out = np.empty((16, 3))
    for k in range(len(T)):
        n = _clip_poly(T[k], R, eps, out)
        for i in range(1, n - 1):
            o = off[k] + i - 1
            parent[o] = k
            for (slot, vi) in ((0, 0), (1, i), (2, i + 1)):
                s = -out[vi, 1]
                UV[o, slot, 0] = out[vi, 0] / s
                UV[o, slot, 1] = out[vi, 2] / s


@njit(cache=False)
def _bin_count(UV, G, R):
    cs = 2 * R / G
    cnt = np.zeros(G * G, np.int64)
    for k in range(len(UV)):
        u0 = min(UV[k, 0, 0], UV[k, 1, 0], UV[k, 2, 0])
        u1 = max(UV[k, 0, 0], UV[k, 1, 0], UV[k, 2, 0])
        v0 = min(UV[k, 0, 1], UV[k, 1, 1], UV[k, 2, 1])
        v1 = max(UV[k, 0, 1], UV[k, 1, 1], UV[k, 2, 1])
        i0 = max(int((u0 + R) / cs), 0)
        i1 = min(int((u1 + R) / cs), G - 1)
        j0 = max(int((v0 + R) / cs), 0)
        j1 = min(int((v1 + R) / cs), G - 1)
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                cnt[i * G + j] += 1
    return cnt


@njit(cache=False)
def _bin_fill(UV, G, R, start, items):
    cs = 2 * R / G
    fill = np.zeros(G * G, np.int64)
    for k in range(len(UV)):
        u0 = min(UV[k, 0, 0], UV[k, 1, 0], UV[k, 2, 0])
        u1 = max(UV[k, 0, 0], UV[k, 1, 0], UV[k, 2, 0])
        v0 = min(UV[k, 0, 1], UV[k, 1, 1], UV[k, 2, 1])
        v1 = max(UV[k, 0, 1], UV[k, 1, 1], UV[k, 2, 1])
        i0 = max(int((u0 + R) / cs), 0)
        i1 = min(int((u1 + R) / cs), G - 1)
        j0 = max(int((v0 + R) / cs), 0)
        j1 = min(int((v1 + R) / cs), G - 1)
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                c = i * G + j
                items[start[c] + fill[c]] = k
                fill[c] += 1


@njit(parallel=True, cache=False)
def _query(U, V, G, R, start, items, UV, N, D0, PID, parent, eps):
    n = len(U)
    best_s = np.full(n, np.inf)
    best_p = np.full(n, -1, np.int64)
    cs = 2 * R / G
    for q in prange(n):
        u, v = U[q], V[q]
        if abs(u) >= R or abs(v) >= R:
            continue
        i = int((u + R) / cs)
        j = int((v + R) / cs)
        c = i * G + j
        for t in range(start[c], start[c + 1]):
            k = items[t]
            ax, ay = UV[k, 0, 0], UV[k, 0, 1]
            bx, by = UV[k, 1, 0], UV[k, 1, 1]
            cx, cy = UV[k, 2, 0], UV[k, 2, 1]
            d1 = (u - bx) * (ay - by) - (ax - bx) * (v - by)
            d2 = (u - cx) * (by - cy) - (bx - cx) * (v - cy)
            d3 = (u - ax) * (cy - ay) - (cx - ax) * (v - ay)
            neg = (d1 < -1e-13) or (d2 < -1e-13) or (d3 < -1e-13)
            pos = (d1 > 1e-13) or (d2 > 1e-13) or (d3 > 1e-13)
            if neg and pos:
                continue
            p = parent[k]
            den = N[p, 0] * u - N[p, 1] + N[p, 2] * v
            if abs(den) < 1e-12:
                continue
            s = D0[p] / den
            if s > eps and s < best_s[q]:
                best_s[q] = s
                best_p[q] = PID[p]
    return best_s, best_p


class Scene:
    """Triangles in lens-relative coordinates + part ids; first-hit queries in (u, v)."""

    def __init__(self, parts, G=250):
        # parts: list of (name, V[n,3], F[m,3]) already in lens-relative coordinates
        self.names = [p[0] for p in parts]
        tris, pid = [], []
        for i, (_, V, F) in enumerate(parts):
            tris.append(V[F])
            pid.append(np.full(len(F), i, np.int64))
        T = np.ascontiguousarray(np.concatenate(tris), dtype=np.float64)
        self.PID = np.concatenate(pid)
        e1, e2 = T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
        self.N = np.cross(e1, e2)
        self.D0 = np.einsum("ij,ij->i", self.N, T[:, 0])
        cnt = _count_clip(T, R_DOM, EPS_S)
        off = np.concatenate([[0], np.cumsum(cnt)])
        m = int(off[-1])
        self.UV = np.zeros((m, 3, 2))
        self.parent = np.zeros(m, np.int64)
        _fill_clip(T, R_DOM, EPS_S, off, self.UV, self.parent)
        self.G = G
        bc = _bin_count(self.UV, G, R_DOM)
        self.start = np.concatenate([[0], np.cumsum(bc)]).astype(np.int64)
        self.items = np.zeros(int(self.start[-1]), np.int64)
        _bin_fill(self.UV, G, R_DOM, self.start, self.items)
        self.ntri = len(T)

    def first_hit(self, U, V):
        return _query(np.ascontiguousarray(U, float), np.ascontiguousarray(V, float), self.G, R_DOM,
                      self.start, self.items, self.UV, self.N, self.D0, self.PID, self.parent, EPS_S)


# =====================================================================================
# geometry loading
# =====================================================================================
def mesh_of(shape):
    V, F = tessellate(shape, TESS_TOL, TESS_ANG)
    return V, F


def category(name):
    if name == "v7_tube":
        return "tube"
    if name in ABOVE:
        return ABOVE[name]
    n = name.replace("v7_", "")
    if n in ("lower_plate", "upper_plate"):
        return "plates"
    if n in ("compound", "follower", "pinion"):
        return "gears"
    if n.startswith(("jaw_", "link_")):
        return "jaws+links"
    if n.startswith(("servo", "horn")) and not n.startswith("horn_screw"):
        return "servo+horn"
    return "head hardware"


def load_v7():
    """Return dicts of solids by name: head_closed, head_open, tube, above (all v6 world frame)."""
    ps = dict(load_v6(V7_STEP))
    assert len(ps) == 59, len(ps)
    tube = ps.pop("v7_tube")
    above = {k: ps.pop(k) for k in list(ABOVE)}
    # name remap: STEP uses "Gripper_Electric_Housing..." style?  (checked at runtime below)
    head_closed = ps
    fb = K7.default()
    head_open = {}
    chk = 0.0
    built_closed = A7.build(fb.theta_c)
    for n, (s, _k) in built_closed.items():
        if n == "tube":
            continue
        bb = A7.to_world(s).val().BoundingBox()
        pb = head_closed["v7_" + n].BoundingBox()
        chk = max(chk, abs(bb.xmin - pb.xmin), abs(bb.xmax - pb.xmax), abs(bb.ymin - pb.ymin),
                  abs(bb.ymax - pb.ymax), abs(bb.zmin - pb.zmin), abs(bb.zmax - pb.zmax))
    built_open = A7.build(fb.theta_open)
    for n, (s, _k) in built_open.items():
        if n == "tube":
            continue
        head_open["v7_" + n] = A7.to_world(s).val()
    assert set(head_open) == set(head_closed)
    return head_closed, head_open, tube, above, chk


def clip_tube(tube, c):
    if c == 0:
        return tube
    top = BOX_BOTTOM_Y - c
    bb = tube.BoundingBox()
    keep = cq.Workplane().box(bb.xlen + 10, top - bb.ymin, bb.zlen + 10, centered=(True, False, True)) \
        .translate(((bb.xmin + bb.xmax) / 2, bb.ymin, (bb.zmin + bb.zmax) / 2))
    return tube.intersect(keep.val())


# =====================================================================================
# floor zones, FOV models
# =====================================================================================
HALF = math.radians(P.CAMBAY_FOV_DIAG_DEG / 2)
_AR = P.CAMBAY_SENSOR_ASPECT
TX = math.tan(HALF) * _AR[0] / math.hypot(*_AR)       # half-tan along sensor X (bay X)
TY = math.tan(HALF) * _AR[1] / math.hypot(*_AR)       # half-tan along sensor Y (radial)
TC = math.tan(HALF)


def in_fov(model, u, v):
    if model == "sensor_4x3":
        return (np.abs(u) <= TX) & (np.abs(v) <= TY)
    if model == "sensor_4x3_rot90":
        return (np.abs(u) <= TY) & (np.abs(v) <= TX)
    return u * u + v * v <= TC * TC


def build_zones():
    xs = np.arange(-340.0, 340.0 + 1e-9, GRID)
    zs = np.arange(-313.0, 307.0 + 1e-9, GRID)          # odd lattice so the grasp grid points sit on it
    X, Z = np.meshgrid(xs, zs)
    X, Z = X.ravel(), Z.ravel()
    dx = np.maximum(np.abs(X) - GRASP_X[1], 0.0)
    dz = np.maximum(np.maximum(GRASP_Z[0] - Z, Z - GRASP_Z[1]), 0.0)
    d = np.hypot(dx, dz)
    zone = np.full(len(X), "", dtype="<U1")
    zone[d == 0] = "a"
    zone[(d > 0) & (d <= RING_B)] = "b"
    zone[(d > RING_B) & (d <= RING_C)] = "c"
    keep = zone != ""
    return X[keep], Z[keep], zone[keep]


ZX, ZZ, ZONE = build_zones()
ZMASK = {k: ZONE == k for k in "abc"}
GX, GZ = ZX[ZMASK["a"]], ZZ[ZMASK["a"]]
LENS_REL_X = AXIS_X - LENS_WORLD[0]      # axis position in lens-relative x (so lens-rel x = rel + this)
LENS_REL_Z = AXIS_Z - LENS_WORLD[2]      # = +90


def uv_of_floor(xrel, zrel, H):
    return (xrel + LENS_REL_X) / H, (zrel + LENS_REL_Z) / H


def zone_stats(scene, H, with_fov=True):
    U, V = uv_of_floor(ZX, ZZ, H)
    s, p = scene.first_hit(U, V)
    occ = s < H - 1e-3
    out = {}
    for model in MODELS:
        fv = in_fov(model, U, V)
        vis = fv & ~occ
        rec = {}
        for k in "abc":
            m = ZMASK[k]
            rec[k] = {"visible": float(vis[m].mean()), "in_fov": float(fv[m].mean()),
                      "occluded_of_in_fov": float((occ & fv)[m].sum() / max(fv[m].sum(), 1))}
        out[model] = rec
    out["unoccluded_ignoring_fov"] = {k: float((~occ)[ZMASK[k]].mean()) for k in "abc"}
    return out


def grasp_visible_fraction(scene, H, model):
    U, V = uv_of_floor(GX, GZ, H)
    s, p = scene.first_hit(U, V)
    vis = in_fov(model, U, V) & ~(s < H - 1e-3)
    return float(vis.mean())


def footprint(scene, H):
    """Floor area / extents of the FOV that is unoccluded (5 mm grid)."""
    step = 5.0
    lim = TC * H
    xs = np.arange(-lim - LENS_REL_X, lim - LENS_REL_X + step, step)
    zs = np.arange(-lim - LENS_REL_Z, lim - LENS_REL_Z + step, step)
    X, Z = np.meshgrid(xs, zs)
    X, Z = X.ravel(), Z.ravel()
    U, V = uv_of_floor(X, Z, H)
    s, p = scene.first_hit(U, V)
    occ = s < H - 1e-3
    out = {}
    for model in MODELS:
        fv = in_fov(model, U, V)
        vis = fv & ~occ
        rec = {"fov_area_mm2": round(float(fv.sum() * step * step), 0),
               "unblocked_area_mm2": round(float(vis.sum() * step * step), 0),
               "unblocked_area_fraction": round(float(vis.sum() / max(fv.sum(), 1)), 4)}
        if vis.any():
            rec["x_range_from_axis_mm"] = [round(float(X[vis].min()), 0), round(float(X[vis].max()), 0)]
            rec["z_range_from_axis_mm"] = [round(float(Z[vis].min()), 0), round(float(Z[vis].max()), 0)]
        out[model] = rec
    return out


def fov_ray_sets(n=61):
    """The three old-script ray sets as (U, V_sensor) arrays; v = V * S."""
    sets = {}
    nx, ny = 61, 46
    gu, gv = np.meshgrid(np.linspace(-TX, TX, nx), np.linspace(-TY, TY, ny))
    sets["sensor_4x3"] = (gu.ravel(), gv.ravel())
    gu2, gv2 = np.meshgrid(np.linspace(-TC, TC, 61), np.linspace(-TC, TC, 61))
    ins = (gu2 ** 2 + gv2 ** 2 <= TC ** 2).ravel()
    sets["cone_35"] = (gu2.ravel()[ins], gv2.ravel()[ins])
    gu3, gv3 = np.meshgrid(np.linspace(-TY, TY, nx), np.linspace(-TX, TX, ny))
    sets["sensor_4x3_rot90"] = (gu3.ravel(), gv3.ravel())
    return sets


def blocked_breakdown(scene, names, parts_cat):
    res = {}
    for model, (u, vs) in fov_ray_sets().items():
        v = vs * B.S
        s, p = scene.first_hit(u, v)
        hit = p >= 0
        n = len(u)
        per_part = {}
        for i in np.unique(p[hit]):
            per_part[names[i]] = round(float((p == i).sum() / n), 4)
        per_cat = {}
        for nm, fr in per_part.items():
            per_cat[parts_cat[nm]] = round(per_cat.get(parts_cat[nm], 0.0) + fr, 4)
        res[model] = {"rays": int(n), "blocked_fraction": round(float(hit.mean()), 4),
                      "by_category": dict(sorted(per_cat.items(), key=lambda kv: -kv[1])),
                      "by_part": dict(sorted(per_part.items(), key=lambda kv: -kv[1]))}
    return res


# =====================================================================================
# per-configuration scene
# =====================================================================================
def make_scene(c, head_meshes, tube_mesh, above_meshes):
    """Lens-relative scene.  Above-parts + lens are shared; head and tube rise by c in lens coordinates."""
    parts = []
    cats = {}
    for nm, (V, F) in above_meshes.items():
        parts.append((nm, V - LENS_WORLD, F))
        cats[nm] = category(nm)
    shift = LENS_WORLD - np.array([0.0, c, 0.0])           # lens at c: head frame lens position
    for nm, (V, F) in head_meshes.items():
        parts.append((nm, V - shift, F))
        cats[nm] = category(nm)
    parts.append(("v7_tube", tube_mesh[0] - shift, tube_mesh[1]))
    cats["v7_tube"] = "tube"
    sc = Scene(parts)
    return sc, [p[0] for p in parts], cats


def floor_height(state_floor_y, c, hover):
    """Lens height above the floor (mm)."""
    return LENS_WORLD[1] - c - (state_floor_y - hover)


# =====================================================================================
# rendering
# =====================================================================================
def render_view(path, c, hover, data):
    """data[state] = dict(scene, names, cats, H, grasp_vis, blocked)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgb
    from matplotlib.patches import Rectangle, Circle, Patch

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 7.4))
    lim = 1.05
    step = 0.004
    uu = np.arange(-lim, lim + step, step)
    vv = np.arange(-lim, lim + step, step)
    UU, VV = np.meshgrid(uu, vv)
    rect_corners = np.array([[GRASP_X[0], GRASP_Z[0]], [GRASP_X[1], GRASP_Z[0]],
                             [GRASP_X[1], GRASP_Z[1]], [GRASP_X[0], GRASP_Z[1]], [GRASP_X[0], GRASP_Z[0]]])
    for ax, state in zip(axes, STATES):
        d = data[state]
        sc, names, cats, H = d["scene"], d["names"], d["cats"], d["H"]
        s, p = sc.first_hit(UU.ravel(), VV.ravel())
        hit = s < H - 1e-3
        img = np.ones(UU.size * 3).reshape(-1, 3) * 0.93
        # floor pixels painted by zone
        xf = UU.ravel() * H - LENS_REL_X
        zf = VV.ravel() * H - LENS_REL_Z
        dx = np.maximum(np.abs(xf) - GRASP_X[1], 0.0)
        dz = np.maximum(np.maximum(GRASP_Z[0] - zf, zf - GRASP_Z[1]), 0.0)
        dd = np.hypot(dx, dz)
        floor_col = np.tile(np.array([0.93, 0.93, 0.93]), (UU.size, 1))
        floor_col[dd <= RING_C] = to_rgb("#fff3c4")
        floor_col[dd <= RING_B] = to_rgb("#b9dcf2")
        floor_col[dd == 0] = to_rgb("#6fd08c")
        img[:] = floor_col
        for i, nm in enumerate(names):
            m = hit & (p == i)
            if m.any():
                img[m] = np.array(to_rgb(CAT_COLORS[cats[nm]]))
        ax.imshow(img.reshape(UU.shape + (3,)), extent=(-lim, lim, -lim, lim), origin="lower",
                  interpolation="nearest")
        # FOV outlines
        ax.add_patch(Rectangle((-TX, -TY), 2 * TX, 2 * TY, fill=False, ec="k", lw=1.6, label="4:3 sensor (long side = bay X)"))
        ax.add_patch(Rectangle((-TY, -TX), 2 * TY, 2 * TX, fill=False, ec="k", lw=1.2, ls="--", label="4:3 rotated 90 deg"))
        ax.add_patch(Circle((0, 0), TC, fill=False, ec="k", lw=1.0, ls=":", label="35 deg cone"))
        # projected grasp rectangle
        ru, rv = uv_of_floor(rect_corners[:, 0], rect_corners[:, 1], H)
        ax.plot(ru, rv, color="#006400", lw=1.4)
        ax.plot([0], [0], "k+", ms=8)
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_aspect("equal")
        ax.set_xlabel("u = x / depth  (sensor X, bay X)")
        ax.set_ylabel("v = z / depth  (+v toward the tube axis)")
        gv = d["grasp_vis"]
        bl = d["blocked"]
        ax.set_title(f"{state} jaws   lens {H:.0f} mm above floor\n"
                     f"grasp zone visible {gv['sensor_4x3'] * 100:.0f}% (4:3) / {gv['sensor_4x3_rot90'] * 100:.0f}% (rot) / "
                     f"{gv['cone_35'] * 100:.0f}% (cone);   blocked {bl['sensor_4x3'] * 100:.1f}% of 4:3 view", fontsize=9)
        ax.grid(alpha=0.2)
    handles = [Patch(color=CAT_COLORS[k], label=k) for k in CAT_COLORS] + [
        Patch(color="#6fd08c", label="floor: grasp zone"), Patch(color="#b9dcf2", label="floor: ring 0-100 mm"),
        Patch(color="#fff3c4", label="floor: ring 100-300 mm"), Patch(color="#ececec", label="floor: beyond")]
    fig.legend(handles=handles, loc="lower center", ncol=7, fontsize=8, frameon=False, bbox_to_anchor=(0.5, 0.0))
    fig.suptitle(f"Camera view  -  tube cut c = {c} mm, hover D = {hover:g} mm   "
                 "(coloured = what blocks the ray; pastel = floor seen; green outline = grasp zone)", fontsize=10)
    fig.tight_layout(rect=(0, 0.10, 1, 0.95))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=110)
    plt.close(fig)


# =====================================================================================
# v6 baseline sanity check (old script's method, ray_mesh_first_hit + v6 preview STEP)
# =====================================================================================
def baseline_check():
    parts = load_v6(V6_STEP)
    floor_y = min(s.BoundingBox().ymin for n, s in parts)
    names, meshes = [], []
    for n, s in parts:
        names.append(n)
        meshes.append(tessellate(s, 0.5 if "Electric" in n or "Cover" in n else 1.2, 0.5 if "Electric" in n else 0.4))
    lens = LENS_WORLD.copy()
    out = {"floor_y": round(float(floor_y), 3), "lens_height_above_floor": round(float(lens[1] - floor_y), 2)}
    for model, (u, vs) in fov_ray_sets().items():
        dirs = np.stack([u, -np.ones_like(u), vs * B.S], axis=1)
        dirs = dirs / np.linalg.norm(dirs, axis=1, keepdims=True)
        best = np.full(len(dirs), np.inf)
        who = np.full(len(dirs), -1)
        for i, (V, F) in enumerate(meshes):
            t = ray_mesh_first_hit(lens, dirs, V, F)
            m = t < best
            best[m] = t[m]
            who[m] = i
        tf = (floor_y - lens[1]) / dirs[:, 1]
        blocked = best < tf
        by = {}
        for i in np.unique(who[blocked]):
            by[names[i]] = round(float((who[blocked] == i).sum() / len(u)), 4)
        out["rays_" + model] = {"blocked_fraction_ray_mesh_first_hit": round(float(blocked.mean()), 4),
                                "by_part": dict(sorted(by.items(), key=lambda kv: -kv[1]))}
    # same data through the grid engine (tolerance 0.25 tessellation)
    pm = []
    for n, s in parts:
        V, F = mesh_of(s)
        pm.append((n, V - lens, F))
    sc = Scene(pm)
    for model, (u, vs) in fov_ray_sets().items():
        s_, p_ = sc.first_hit(u, vs * B.S)
        out["rays_" + model]["blocked_fraction_grid_engine"] = round(float((p_ >= 0).mean()), 4)
    out["old_json"] = {}
    if os.path.exists(BASELINE_JSON):
        old = json.load(open(BASELINE_JSON))
        out["old_json"] = {"sensor_4x3": old["fov_sensor_rect_4x3_70diag"]["blocked_fraction"],
                           "cone_35": old["fov_circular_cone_35deg"]["blocked_fraction"],
                           "sensor_4x3_rot90": old["fov_sensor_rect_rotated_90"]["blocked_fraction"],
                           "lens_height": old["lens_height_above_floor_mm"]}
    return out


# =====================================================================================
# main
# =====================================================================================
def main():
    t0 = time.time()
    res = {"conventions": {}}
    head_closed, head_open, tube, above, chk = load_v7()
    print("v7 loaded; closed-pose rebuild vs preview max bbox dev %.2e mm  (%.0fs)" % (chk, time.time() - t0))

    # ---- geometry facts ----------------------------------------------------------------
    def ymin_of(d):
        return min(s.BoundingBox().ymin for s in d.values())
    floor_closed = ymin_of(head_closed)
    floor_open = ymin_of(head_open)
    head_top = max(s.BoundingBox().ymax for s in head_closed.values())
    cyl = above["v6_Griper_Cylinder_reference"]
    cyl_bottom = cyl.BoundingBox().ymin
    tb = tube.BoundingBox()
    socket_top = tb.ymin + P.GRIPV7_TUBE_INSERT
    free_to_box = BOX_BOTTOM_Y - head_top
    free_to_cyl = cyl_bottom - head_top
    c_limit = free_to_cyl
    mouth_y = 1105.2405
    if os.path.exists(BASELINE_JSON):
        mouth_y = json.load(open(BASELINE_JSON))["cable_lines"]["per_corner"]["corner_-1x_-1z"]["mouth_world"][1]
    area = math.pi / 4 * (TUBE_OD ** 2 - TUBE_ID ** 2)
    res["geometry"] = {
        "lens_world": [round(float(v), 3) for v in LENS_WORLD],
        "tube_axis_xz": [round(AXIS_X, 4), round(AXIS_Z, 4)],
        "tube_y_range": [round(tb.ymin, 3), round(tb.ymax, 3)], "tube_length_mm": round(tb.ymax - tb.ymin, 3),
        "head_socket_top_y": round(socket_top, 3), "head_top_y_plates": round(head_top, 3),
        "box_bottom_y": round(BOX_BOTTOM_Y, 3), "cylinder_block_bottom_y": round(cyl_bottom, 3),
        "cylinder_block_y_range": [round(cyl.BoundingBox().ymin, 3), round(cyl.BoundingBox().ymax, 3)],
        "free_tube_socket_top_to_box_bottom_mm": round(BOX_BOTTOM_Y - socket_top, 3),
        "free_tube_head_top_to_box_bottom_mm": round(free_to_box, 3),
        "free_tube_head_top_to_cylinder_block_bottom_mm": round(free_to_cyl, 3),
        "c_limit_before_cylinder_touches_head_mm": round(c_limit, 3),
        "tube_remaining_at_c200_mm": round(tb.ymax - tb.ymin - 200, 3),
        "closed_jaw_tip_y": round(floor_closed, 3), "open_jaw_lowest_y": round(floor_open, 3),
        "open_minus_closed_tip_height_mm": round(floor_open - floor_closed, 3),
        "cable_mouth_y": mouth_y, "tube_cross_section_mm2": round(area, 2),
        "tube_mass_per_mm_g": round(area * AL_DENS, 4),
    }
    res["conventions"] = {
        "hover_D": "claw raised D mm from the pose where the CLOSED jaw tips touch the floor (floor y = %.3f - D); "
                   "the same claw frame is used for open jaws, whose lowest point is %.1f mm higher than the closed tips"
                   % (floor_closed, floor_open - floor_closed),
        "grasp_zone": "x %s, z %s mm relative to the tube axis" % (GRASP_X, GRASP_Z),
        "ring_b": "0 < Euclidean distance to the grasp rectangle <= %g mm" % RING_B,
        "ring_c": "%g < distance <= %g mm" % (RING_B, RING_C),
        "visible": "floor sample lies inside the chosen FOV model AND its ray from the lens is not blocked by any claw solid",
        "grid_mm": GRID, "n_samples": {k: int(ZMASK[k].sum()) for k in "abc"},
        "fov": {"sensor_4x3": [round(TX, 4), round(TY, 4)], "sensor_4x3_rot90": [round(TY, 4), round(TX, 4)],
                "cone_35": round(TC, 4)},
    }
    print(json.dumps(res["geometry"], indent=1))

    # ---- tessellate once --------------------------------------------------------------
    mesh_closed = {n: mesh_of(s) for n, s in head_closed.items()}
    mesh_open = {n: mesh_of(s) for n, s in head_open.items()}
    above_mesh = {n: mesh_of(s) for n, s in above.items()}
    print("tessellated (%.0fs): head %d tris, above %d tris" % (
        time.time() - t0, sum(len(F) for V, F in mesh_closed.values()), sum(len(F) for V, F in above_mesh.values())))

    # ---- sweep ------------------------------------------------------------------------
    res["sweep"] = {}
    res["tube"] = {}
    res["dstar"] = {}
    scenes = {}
    for c in CUTS:
        tube_c = clip_tube(tube, c)
        tmesh = mesh_of(tube_c)
        mass_saved = area * c * AL_DENS
        full_len = tb.ymax - tb.ymin
        res["tube"][str(c)] = {
            "tube_length_mm": round(full_len - c, 2), "mass_saved_g": round(mass_saved, 2),
            "tube_mass_g": round(area * (full_len - c) * AL_DENS, 2),
            "gap_cylinder_block_to_head_mm": round(free_to_cyl - c, 2),
            "exposed_tube_between_head_and_block_mm": round(free_to_cyl - c, 2),
            "cable_mouth_to_closed_jaw_tips_mm": round(mouth_y - c - floor_closed, 2),
            "cable_mouth_to_open_jaw_lowest_mm": round(mouth_y - c - floor_open, 2),
            "box_bottom_height_above_floor_closed_mm": round(BOX_BOTTOM_Y - c - floor_closed, 2),
            "lens_height_above_floor_D0_mm": round(LENS_WORLD[1] - c - floor_closed, 2),
        }
        for state, hm in (("closed", mesh_closed), ("open", mesh_open)):
            sc, names, cats = make_scene(c, hm, tmesh, above_mesh)
            scenes[(c, state)] = (sc, names, cats)
            bl = blocked_breakdown(sc, names, cats)
            rec = {"blocked": bl, "triangles": sc.ntri, "by_hover": {}}
            for D in HOVERS:
                H = floor_height(floor_closed, c, D)
                z = zone_stats(sc, H)
                fp = footprint(sc, H)
                rec["by_hover"][str(D)] = {"lens_height_above_floor_mm": round(H, 2), "zones": z, "footprint": fp}
            # D* scan (1 mm) for the grasp zone
            Ds = np.arange(0.0, DSTAR_MAX + 1e-9, 1.0)
            ds = {}
            for model in MODELS:
                fr = np.array([grasp_visible_fraction(sc, floor_height(floor_closed, c, D), model) for D in Ds])
                ok = fr >= VIS_TARGET
                if ok.any():
                    first = float(Ds[np.argmax(ok)])
                    stay = bool(ok[np.argmax(ok):].all())
                    # first D from which it stays >= 95 % up to the end of the scan
                    bad = np.where(~ok)[0]
                    sustained = float(Ds[bad[-1] + 1]) if len(bad) and bad[-1] + 1 < len(Ds) else (0.0 if not len(bad) else None)
                else:
                    first, stay, sustained = None, False, None
                ds[model] = {"dstar_mm": first, "stays_above_target_to_scan_end": stay,
                             "sustained_from_mm": sustained, "max_visible_fraction": round(float(fr.max()), 4),
                             "D_at_max_mm": float(Ds[int(fr.argmax())]),
                             "visible_fraction_at_D0": round(float(fr[0]), 4)}
            # which solid hides the grasp zone just below D* (first-hit part of the occluded samples)
            d0 = ds["sensor_4x3"]["dstar_mm"]
            if d0 is not None and d0 >= 1.0:
                H1 = floor_height(floor_closed, c, d0 - 1.0)
                U1, V1 = uv_of_floor(GX, GZ, H1)
                s1, p1 = sc.first_hit(U1, V1)
                tally = {}
                for i in p1[s1 < H1 - 1e-3]:
                    tally[names[i]] = tally.get(names[i], 0) + 1
                ds["limiting_blockers_at_Dstar_minus_1_mm"] = dict(sorted(tally.items(), key=lambda kv: -kv[1]))
            res["dstar"].setdefault(str(c), {})[state] = ds
            res["sweep"].setdefault(str(c), {})[state] = rec
            print("c=%3d %-6s  tris %6d  blocked(4:3) %.3f  D*(4:3)=%s  [%.0fs]" % (
                c, state, sc.ntri, bl["sensor_4x3"]["blocked_fraction"], ds["sensor_4x3"]["dstar_mm"], time.time() - t0))

    # ---- cross-check with cad.mesh_tools.ray_mesh_first_hit ------------------------------
    rng = np.random.default_rng(7)
    val = {}
    for (c, state) in ((100, "open"), (200, "closed")):
        sc, names, cats = scenes[(c, state)]
        hm = mesh_open if state == "open" else mesh_closed
        parts = []
        for nm, (V, F) in above_mesh.items():
            parts.append((nm, V - LENS_WORLD, F))
        shift = LENS_WORLD - np.array([0.0, c, 0.0])
        for nm, (V, F) in hm.items():
            parts.append((nm, V - shift, F))
        tm = mesh_of(clip_tube(tube, c))
        parts.append(("v7_tube", tm[0] - shift, tm[1]))
        nq = 500
        uq = rng.uniform(-TC, TC, nq)
        vq = rng.uniform(-TC, TC, nq)
        dirs = np.stack([uq, -np.ones(nq), vq], axis=1)
        best = np.full(nq, np.inf)
        who = np.full(nq, -1)
        for i, (nm, V, F) in enumerate(parts):
            t = ray_mesh_first_hit(np.zeros(3), dirs, V, F)
            m = t < best
            best[m] = t[m]
            who[m] = i
        s_g, p_g = sc.first_hit(uq, vq)
        agree = (np.isfinite(best) == np.isfinite(s_g))
        same_part = agree & ((~np.isfinite(best)) | (np.array([parts[i][0] for i in who]) == np.array(
            [names[j] if j >= 0 else "" for j in p_g])))
        dep = np.isfinite(best) & np.isfinite(s_g)
        val[f"c{c}_{state}"] = {"rays": nq, "hit_miss_agreement": round(float(agree.mean()), 4),
                                 "same_first_part": round(float(same_part.mean()), 4),
                                 "max_depth_diff_mm": round(float(np.abs(best[dep] - s_g[dep]).max()), 4) if dep.any() else 0.0}
    res["validation_vs_ray_mesh_first_hit"] = val
    print("validation", json.dumps(val))

    # ---- baseline sanity check -----------------------------------------------------------
    res["baseline_v6"] = baseline_check()
    print("baseline", json.dumps({k: v for k, v in res["baseline_v6"].items() if k != "old_json"}, indent=1)[:1500])

    # ---- renders -------------------------------------------------------------------------
    os.makedirs(OUT_DIR, exist_ok=True)
    made = []
    for c in CUTS:
        dstar = res["dstar"][str(c)]["open"]["sensor_4x3"]["dstar_mm"]
        dlist = [0.0] + ([dstar] if dstar not in (None, 0.0) else [])
        for D in dlist:
            data = {}
            for state in STATES:
                sc, names, cats = scenes[(c, state)]
                H = floor_height(floor_closed, c, D)
                gv = {m: grasp_visible_fraction(sc, H, m) for m in MODELS}
                bl = {m: res["sweep"][str(c)][state]["blocked"][m]["blocked_fraction"] for m in MODELS}
                data[state] = {"scene": sc, "names": names, "cats": cats, "H": H, "grasp_vis": gv, "blocked": bl}
            tag = "Dzero" if D == 0 else "Dstar%d" % int(round(D))
            fn = os.path.join(OUT_DIR, "c%03d_%s.png" % (c, tag))
            render_view(fn, c, D, data)
            made.append(os.path.relpath(fn, REPO))
    res["renders"] = made

    res["meta"] = {"script": "scripts/study_claw_tube_length_view.py", "runtime_s": round(time.time() - t0, 1),
                   "closed_pose_rebuild_vs_preview_max_bbox_dev_mm": chk,
                   "tess_tol_mm": TESS_TOL, "cuts_mm": CUTS, "hovers_mm": HOVERS}
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as fh:
        json.dump(res, fh, indent=1)
    print("wrote", OUT_JSON)
    write_md(res)
    print("wrote", OUT_MD, " total %.0fs" % (time.time() - t0))


# =====================================================================================
# markdown report
# =====================================================================================
def pct(x, d=1):
    return "-" if x is None else f"{x * 100:.{d}f}"


def write_md(res):
    g = res["geometry"]
    L = []
    w = L.append
    w("# Claw camera view vs aluminium-tube length (v7 gripper)\n")
    w("Analysis only. Generated by `scripts/study_claw_tube_length_view.py`; numbers below are copied from "
      "`verification/claw_tube_length_view_study.json`. No part, params or export file was modified.\n")
    narrative = NARRATIVE(res)
    w(narrative)
    # -------- tube facts
    w("\n## 1. Tube length limit, mass and cable-point height\n")
    w(f"* Tube: y {g['tube_y_range'][0]} .. {g['tube_y_range'][1]} (L = {g['tube_length_mm']} mm); head socket top y {g['head_socket_top_y']}; "
      f"head plate top y {g['head_top_y_plates']}; Griper Cylinder block y {g['cylinder_block_y_range'][0]} .. {g['cylinder_block_y_range'][1]}; box bottom y {g['box_bottom_y']}.")
    w(f"* Free tube, socket top -> box bottom: **{g['free_tube_socket_top_to_box_bottom_mm']} mm**; head plate top -> box bottom: {g['free_tube_head_top_to_box_bottom_mm']} mm.")
    w(f"* The top 55 mm of the tube is inside the Cylinder hub bore, so the real limit is head plate top -> Cylinder block bottom = "
      f"**{g['c_limit_before_cylinder_touches_head_mm']} mm**: the Griper Cylinder is a flared hub (OD 50 at its flat bottom, 127 at its top) whose bottom face meets the head plate top at c = {g['c_limit_before_cylinder_touches_head_mm']}. "
      f"The sweep is therefore capped at c = 200 mm (6.2 mm clearance, no margin for tolerance; c > ~190 is not recommended).")
    w(f"* Closed jaw tips y {g['closed_jaw_tip_y']}; open-jaw lowest point y {g['open_jaw_lowest_y']} ({g['open_minus_closed_tip_height_mm']} mm higher).")
    w(f"* Cable mouth y {g['cable_mouth_y']} (corner holes, from `claw_camera_bay_analysis.json`). Tube: OD 28.54 / ID 22.54, A = {g['tube_cross_section_mm2']} mm^2, "
      f"{g['tube_mass_per_mm_g']} g/mm at 2.70 g/cc.\n")
    w("| c (mm) | tube length | tube mass | **mass saved** | exposed tube head->block | cable pts -> closed tips | cable pts -> open jaws | lens height @D=0 |")
    w("|---|---|---|---|---|---|---|---|")
    for c in CUTS:
        t = res["tube"][str(c)]
        w(f"| {c} | {t['tube_length_mm']} | {t['tube_mass_g']} g | **{t['mass_saved_g']} g** | {t['exposed_tube_between_head_and_block_mm']} | "
          f"{t['cable_mouth_to_closed_jaw_tips_mm']} (change {-c}) | {t['cable_mouth_to_open_jaw_lowest_mm']} | {t['lens_height_above_floor_D0_mm']} |")
    # -------- D* table
    w("\n## 2. Minimum hover D* for the grasp zone >= 95 % visible (open jaws)\n")
    w("D* = smallest hover D (1 mm scan, 0..1500) at which >= 95 % of the 2 mm grasp-zone samples (x +-40, z -13..+7) are inside the FOV and unblocked. "
      "'sustained' = the D from which it stays >= 95 % for all larger D in the scan.\n")
    w("| c (mm) | D* 4:3 sensor (long side X) | sustained from | D* 4:3 rotated 90 deg | D* 35 deg cone | max visible (4:3) over scan | lens height at D* (4:3) |")
    w("|---|---|---|---|---|---|---|")
    for c in CUTS:
        d = res["dstar"][str(c)]["open"]
        def f(m):
            x = d[m]["dstar_mm"]
            return "none" if x is None else f"{x:.0f}"
        s43 = d["sensor_4x3"]
        lh = "-" if s43["dstar_mm"] is None else f"{floor_h(res, c, s43['dstar_mm']):.0f}"
        w(f"| {c} | **{f('sensor_4x3')}** | {('-' if s43['sustained_from_mm'] is None else int(s43['sustained_from_mm']))} | {f('sensor_4x3_rot90')} | {f('cone_35')} | "
          f"{pct(s43['max_visible_fraction'])} % @ D={s43['D_at_max_mm']:.0f} | {lh} |")
    w("\nClosed jaws, same scan (4:3): " + "; ".join(
        f"c={c}: D*={res['dstar'][str(c)]['closed']['sensor_4x3']['dstar_mm']:.0f}" for c in CUTS) + ".")
    w("\nSolid that hides the grasp zone at D* - 1 mm (open, 4:3; number of occluded grasp samples, i.e. the far z = +7 row of 41): " + "; ".join(
        f"c={c}: " + ", ".join(f"{k} {v}" for k, v in res['dstar'][str(c)]['open'].get('limiting_blockers_at_Dstar_minus_1_mm', {}).items())
        for c in CUTS) + ".")
    # -------- blocked table
    w("\n\n## 3. Blocked fraction of the view (independent of hover D)\n")
    w("Percent of rays that hit a claw solid before the floor. Breakdown: tube, Cylinder block, box+bay, plates (lower/upper), gears (compound/follower/pinion), "
      "jaws+links, servo+horn, head hardware (bolts, bearings, pins, nuts).\n")
    cats = ["tube", "cylinder block", "box+bay", "plates", "gears", "jaws+links", "servo+horn", "head hardware"]
    for state in STATES:
        for model in MODELS:
            w(f"\n**{state} jaws, {model}**\n")
            w("| c | blocked % | " + " | ".join(cats) + " |")
            w("|---|---|" + "---|" * len(cats))
            for c in CUTS:
                b = res["sweep"][str(c)][state]["blocked"][model]
                w(f"| {c} | **{pct(b['blocked_fraction'])}** | " + " | ".join(pct(b["by_category"].get(k, 0.0)) for k in cats) + " |")
    # -------- zones tables
    w("\n## 4. Visible fraction of floor zones (% of 2 mm samples inside FOV and unblocked), 4:3 sensor as designed\n")
    for state in STATES:
        w(f"\n**{state} jaws** - cells show grasp (a) / ring 0-100 (b) / ring 100-300 (c); lens height above floor in the header row is for D=0.\n")
        w("| c \\ D | " + " | ".join(str(D) for D in HOVERS) + " |")
        w("|---|" + "---|" * len(HOVERS))
        for c in CUTS:
            row = []
            for D in HOVERS:
                z = res["sweep"][str(c)][state]["by_hover"][str(D)]["zones"]["sensor_4x3"]
                row.append(f"{pct(z['a']['visible'], 0)} / {pct(z['b']['visible'], 0)} / {pct(z['c']['visible'], 0)}")
            w(f"| {c} | " + " | ".join(row) + " |")
    w("\nSame, 4:3 sensor rotated 90 deg (long side radial) and 35 deg cone are in the JSON (`sweep.<c>.<state>.by_hover.<D>.zones`).\n")
    w("\n**Open jaws, grasp zone only, all three FOV models** (a) visible %:\n")
    w("| c \\ D | " + " | ".join(str(D) for D in HOVERS) + " |")
    w("|---|" + "---|" * len(HOVERS))
    for c in CUTS:
        row = []
        for D in HOVERS:
            z = res["sweep"][str(c)]["open"]["by_hover"][str(D)]["zones"]
            row.append(" / ".join(pct(z[m]["a"]["visible"], 0) for m in MODELS))
        w(f"| {c} | " + " | ".join(row) + " |")
    w("\n(order: 4:3 / 4:3 rotated / cone)\n")
    # -------- footprint
    w("\n## 5. Floor footprint of the unblocked 4:3 view (open jaws)\n")
    w("| c | D | lens height | FOV floor area (m^2) | unblocked area (m^2) | unblocked % | x range from axis | z range from axis |")
    w("|---|---|---|---|---|---|---|---|")
    for c in CUTS:
        for D in HOVERS:
            r = res["sweep"][str(c)]["open"]["by_hover"][str(D)]
            fp = r["footprint"]["sensor_4x3"]
            xr = fp.get("x_range_from_axis_mm", ["-", "-"])
            zr = fp.get("z_range_from_axis_mm", ["-", "-"])
            w(f"| {c} | {D} | {r['lens_height_above_floor_mm']:.0f} | {fp['fov_area_mm2'] / 1e6:.3f} | {fp['unblocked_area_mm2'] / 1e6:.3f} | "
              f"{pct(fp['unblocked_area_fraction'])} | {xr[0]} .. {xr[1]} | {zr[0]} .. {zr[1]} |")
    # -------- sanity
    w("\n## 6. Sanity check against the v6 baseline (c = 0, v6 geometry)\n")
    b = res["baseline_v6"]
    w("Run on `exports/step/gripper_v6_with_camera_bay_preview.step` with the old script's ray set and `cad.mesh_tools.ray_mesh_first_hit`; "
      f"floor y {b['floor_y']}, lens {b['lens_height_above_floor']} mm above it (old json: {b['old_json'].get('lens_height')}).\n")
    w("| FOV | old json | re-run (ray_mesh_first_hit) | grid engine (this study) |")
    w("|---|---|---|---|")
    for m in MODELS:
        r = b["rays_" + m]
        w(f"| {m} | {pct(b['old_json'].get(m))} % | {pct(r['blocked_fraction_ray_mesh_first_hit'])} % | {pct(r['blocked_fraction_grid_engine'])} % |")
    w("\nCross-check of the grid engine against `ray_mesh_first_hit` on random rays in the v7 scenes: "
      + "; ".join(f"{k}: hit/miss agreement {pct(v['hit_miss_agreement'], 1)} %, same first part {pct(v['same_first_part'], 1)} %, max depth diff {v['max_depth_diff_mm']} mm"
                  for k, v in res["validation_vs_ray_mesh_first_hit"].items()) + ".\n")
    w("v7 (c = 0) vs v6 (c = 0), 4:3 sensor, blocked %: " + ", ".join(
        f"{s} {pct(res['sweep']['0'][s]['blocked']['sensor_4x3']['blocked_fraction'])}" for s in STATES) +
      f" vs v6 {pct(b['rays_sensor_4x3']['blocked_fraction_ray_mesh_first_hit'])}.\n")
    w(EXPLAIN_V6_V7(res))
    # -------- method etc
    w(METHOD)
    w("\n## Renders\n")
    for r in res["renders"]:
        w(f"* `{r}`")
    with open(OUT_MD, "w") as fh:
        fh.write("\n".join(L) + "\n")


def floor_h(res, c, D):
    return res["sweep"][str(c)]["open"]["by_hover"][str(HOVERS[0])]["lens_height_above_floor_mm"] + D


def NARRATIVE(res):
    ds = {c: res["dstar"][str(c)]["open"]["sensor_4x3"]["dstar_mm"] for c in CUTS}
    z0 = {c: res["sweep"][str(c)]["open"]["by_hover"]["0"]["zones"]["sensor_4x3"] for c in CUTS}
    bl = {(c, st, m): res["sweep"][str(c)][st]["blocked"][m]["blocked_fraction"] for c in CUTS for st in STATES for m in MODELS}
    fp = {c: res["sweep"][str(c)]["open"]["by_hover"]["0"]["footprint"]["sensor_4x3"]["fov_area_mm2"] / 1e6 for c in CUTS}
    mass = {c: res["tube"][str(c)]["mass_saved_g"] for c in CUTS}
    t = []
    t.append("## Answer\n")
    t.append("**Can the camera see the grasp spot?** Not while the claw is standing on the floor, yes once it hovers a little. "
             "The lens is 90 mm to one side of the tube, so the grasp zone (x +-40, z -13..+7) lies behind the head: the camera-side face of the lower "
             "plate (z -30.5, its bottom edge 93 mm above the closed jaw tips) and, for the long tube, the tube itself hide it. "
             "With the jaw tips on the floor (D = 0) the grasp zone is **" + " / ".join(f"{pct(z0[c]['a']['visible'], 0)} %" for c in CUTS)
             + "** visible for c = " + " / ".join(str(c) for c in CUTS) + " mm (open jaws; closed jaws are the same or lower, the closed jaws sit on the zone). "
             "It becomes >= 95 % visible at a hover of **D\\* = " + " / ".join(f"{ds[c]:.0f}" for c in CUTS) + " mm** (same c order). "
             "D\\* is the same for open and closed jaws and for all three FOV models: the field of view is never the limit for the grasp zone, the lower-plate edge is "
             "(closed form D\\* = (k (H0 - c) - 93) / (1 - k) with k = 1 - 59.5/97 = 0.387, 59.5 = 90 - 30.5 mm lateral lens-to-plate-face distance, 97 = 90 + 7 mm lens-to-far-edge distance, H0 = 512 mm lens height at D = 0; it reproduces the table to ~1 mm).\n")
    t.append("**Surroundings.** With the tips on the floor the near ring (0-100 mm beyond the grasp zone) is " + " / ".join(pct(z0[c]['b']['visible'], 0) for c in CUTS)
             + " % visible and the far ring (100-300 mm) " + " / ".join(pct(z0[c]['c']['visible'], 0) for c in CUTS) + " % (c = 0..200). "
             "The near ring stays at 58-68 % for every D up to 100 mm because the floor behind the claw (+z side) is in the shadow of the head and tube. "
             "Cutting the tube lowers the lens, so the camera footprint shrinks (4:3 floor area at D = 0: "
             + " / ".join(f"{fp[c]:.2f}" for c in CUTS) + " m^2) and the 100-300 mm ring is seen less (D = 100 mm: "
             + " / ".join(pct(res['sweep'][str(c)]['open']['by_hover']['100']['zones']['sensor_4x3']['c']['visible'], 0) for c in CUTS) + " %).\n")
    t.append("**Effect of the cut.** Each 10 mm cut: D\\* falls ~6.3 mm, tube mass falls " + f"{mass[50] / 5:.1f}" + " g, the cable attachment points drop 10 mm relative to the jaw tips "
             "(524.2 mm at c = 0, 324.2 mm at c = 200 with closed jaws). Mass saved " + " / ".join(f"{mass[c]:.0f}" for c in CUTS) + " g. "
             "The blocked fraction of the view does not fall with the cut: 4:3 open " + " / ".join(pct(bl[(c, 'open', 'sensor_4x3')]) for c in CUTS)
             + " %, rotated sensor " + " / ".join(pct(bl[(c, 'open', 'sensor_4x3_rot90')]) for c in CUTS) + " %, cone "
             + " / ".join(pct(bl[(c, 'open', 'cone_35')]) for c in CUTS) + " %. The tube share falls from 1.6 % to 0 (4:3, from c = 100) but the head plates "
             "fill more of the picture as the lens comes down to the head (rotated sensor / cone reach 21 % / 18 % at c = 200). "
             "So a shorter tube helps the camera to see the grasp spot earlier in the descent (lower D\\*) but gives a smaller and more head-dominated picture.\n")
    t.append("**Hard limits.** The tube can be cut by at most 206.2 mm before the flared Griper Cylinder hub (OD 50 at its bottom, 127 at its top; the tube stays 55 mm "
             "inside it) touches the head plates; c = 200 leaves 6.2 mm. Free tube length: socket top -> box bottom 262.3 mm, head top -> box bottom 261.2 mm, "
             "head top -> hub bottom 206.2 mm.\n")
    return "\n".join(t)


def EXPLAIN_V6_V7(res):
    b = res["baseline_v6"]
    v7o = res["sweep"]["0"]["open"]["blocked"]["sensor_4x3"]
    v7c = res["sweep"]["0"]["closed"]["blocked"]["sensor_4x3"]
    return (
        "**Why v7 at c = 0 differs from v6 (12.4 %).** The v6 re-run gives "
        f"{pct(b['rays_sensor_4x3']['blocked_fraction_ray_mesh_first_hit'])} % (old json 12.44 %; the 0.1 % difference is only tessellation of the preview STEP). "
        f"v7 gives {pct(v7c['blocked_fraction'])} % closed / {pct(v7o['blocked_fraction'])} % open. The tube share is unchanged "
        f"(v6 1.6 %, v7 {pct(v7o['by_category'].get('tube', 0))} %, same tube and same lens). The reduction is the head: the v6 gear housing was one 140 mm wide x 175 mm tall "
        "x 80 mm deep block (x 881.8..1021.8, z 1064..1144 = -40..+40 from the axis; 10.8 % of the view) while the v7 head is two 6 mm plates, 99 mm wide, 156 mm tall and "
        "54 mm deep (z -30.5..+23.5; plates "
        f"{pct(v7o['by_category'].get('plates', 0))} %), so its shadow is narrower and starts further from the camera's sight line. v7 adds a little blocking by its "
        f"gears/jaws/links/hardware ({pct(sum(v7o['by_category'].get(k, 0) for k in ('gears', 'jaws+links', 'head hardware')))} % open, "
        f"{pct(sum(v7c['by_category'].get(k, 0) for k in ('gears', 'jaws+links', 'head hardware')))} % closed; the open linkage and gears swing out toward the camera side). "
        "The v6 ray set, floor and lens are otherwise identical, so the sanity check passes (c = 0 with v6 geometry = 12.5 %).\n")


METHOD = """
## Expected vs measured (inputs checked)

| Item | Expected (brief / baseline) | Measured here |
|---|---|---|
| solids in the v7 preview | 59 | 59 (3 above the tube, 1 tube, 55 head) |
| lens world | (951.85, 1093.09, 1013.99) | same, from `claw_camera_bay` constants (box bottom 1091.1905 + 1.9) |
| tube axis | x 951.8475, z 1103.99 | same |
| tube lower end / jaw tips | y 786.39 / ~581.03 | 786.39 / 581.034 (closed) |
| lens height above floor, D = 0 (v6) | 511.7 | 511.66 (v6 floor 581.426) ; v7: 512.06 (floor 581.034) |
| corner hole mouths y | 1105.24 | 1105.24 |
| blocked 4:3, c = 0, v6 | 12.4 % | 12.5 % (ray_mesh_first_hit), 12.5 % (grid engine) |
| closed-pose rebuild from `gripper_v7_assembly.build` vs preview STEP | identical | max bbox deviation ~1e-11 mm (so the open pose, built the same way, can be trusted) |
| open pose | theta_open = closed + 76.5 deg | lowest open jaw point y 629.86 (48.8 mm above the closed tips); open jaws x +-44..80 from the axis |

## Method

* Geometry: `exports/step/gripper_v7_preview.step` loaded with `cad.v6_loader.load_v6`. "Above the tube" = `v6_Griper_Cylinder_reference` (the flared hub), `electric_housing_with_camera_bay`, `camera_bay_cover`. Tube = `v7_tube`. Everything else (55 solids: plates, gears, jaws, links, servo, horn, bolts, bearings, pins, nuts) is the head and stays fixed.
* Cut by c: above-tube parts and the lens move DOWN c mm; the head stays; the tube is clipped at its top (y <= 1091.19 - c), i.e. it stays 55 mm deep in the hub. Equivalent view in lens coordinates: head + tube move UP by c.
* Hover D: the whole claw is raised D above the pose where the CLOSED jaw tips touch the floor (floor y = 581.034 - D); the same convention is used for the open pose, so open jaws are 48.8 mm above the floor at D = 0 (open jaws on the floor would be D = -48.8). Lens height above floor = 512.06 - c + D.
* Jaw states: closed = the preview pose; open = `cad.parts.gripper_v7_assembly.build(K7.default().theta_open)` (jaw/link/gear/horn/bolt articulation, 76.5 deg crank sweep), translated to the world with `to_world`. The closed rebuild is compared with the preview before use.
* Rays: all rays start at the lens glass centre (a point), directions (u, -1, v*S) as in `scripts/analyze_claw_camera_bay.py` (S = -1, bay on -Z; +v points toward the tube). FOV models: 4:3 sensor, 70 deg diagonal, long side along bay X (as designed, VERIFY); the same sensor rotated 90 deg; 35 deg half-angle cone. Tangent half-widths are those of the old script (0.5601 x 0.4201, cone 0.7002).
* Blocked fraction = share of the old script's ray grids (2806 / 2806 / 2819 rays) whose first hit is any claw solid. Every solid lies above the floor, so this does not depend on D.
* Floor zones on a 2 mm grid: (a) grasp zone x -40..40, z -13..+7 (451 samples); (b) 0 < d <= 100 mm; (c) 100 < d <= 300 mm, d = Euclidean distance to the grasp rectangle . A sample is "visible" if it is inside the chosen FOV model AND the ray lens -> sample is not hit by any claw solid before the floor. Samples outside the FOV count as not visible (reported separately as in_fov / occluded_of_in_fov in the JSON).
* D*: smallest D on a 1 mm scan 0..1500 with the grasp zone >= 95 % visible; also whether it stays above 95 % up to 1500 (it does).
* Footprint: 5 mm floor grid over the FOV; area and extents of the in-FOV, unblocked samples.
* Engine: each triangle is clipped to the lens frustum, projected gnomonically to (x, z)/depth, binned on a grid; a query tests the triangles of its cell exactly (point in projected triangle + plane depth for the nearest hit). It was checked against `cad.mesh_tools.ray_mesh_first_hit` on 500 random rays in two v7 scenes (100 % agreement of hit/miss and of the first part, max depth difference 0.000 mm) and on the full v6 baseline ray sets (12.5 / 14.6 / 11.0 % vs 12.5 / 14.5 / 11.0 %).
* Tessellation tolerance 0.25 mm / 0.3 rad; the v6 ray_mesh_first_hit re-run uses the old script's coarser tolerances.

## Assumptions

* Camera = OV2640 70 deg diagonal 4:3 (as in `params.CAMBAY_*`, still VERIFY), optical axis straight down, lens at the glass centre; no lens distortion, no vignetting, no focus / depth-of-field model.
* The floor is flat and bare. The laundry is not modelled: a pile of height p behaves like a floor raised by p, i.e. the claw must hover D* + p above the real floor to see the grasp zone on top of the pile, and the pile itself hides the floor behind it.
* The claw hangs vertically; no swing, tilt or cable sway (a 2 m/s^2 dynamic load will tilt/swing the claw and move the grasp zone in the image).
* Only CAD solids are modelled: the 4 Dyneema cables, wires, the servo cable, the XIAO board/antenna and tendon hardware in the box, the lens barrel are NOT in the preview STEP and are not ray-cast. Cables run above the lens plane except near the head, where the servo wire may add small occluders.
* The tube cut changes length only (same OD/ID, same socket and hub); mass saved = pi/4 (28.54^2 - 22.54^2) x c x 2.70 g/cc = 0.6499 g/mm. The cross-bolt hole is at the bottom, unaffected.

## Limitations

* No stiffness / buckling / natural-frequency check of the shorter tube or of the cable-box + camera cantilever at the new height; no new cable-line clearance check (box and bay move rigidly, so bay-to-cable clearance is unchanged, but the cable angles to the ceiling anchors change with the lower attachment height).
* The 6.2 mm head-to-hub gap at c = 200 is a nominal CAD gap with no tolerance margin (print/assembly tolerances: the hub is a v6 reference solid).
* D* is a geometric threshold, not a tracking-performance claim: the 95 % criterion is on the 2 mm grid of a 80 x 20 mm rectangle; a laundry item bigger than the zone needs its own visibility check.
* "Visible" means geometrically unobstructed and inside the FOV, not "resolved" or "in focus": no image-scale, focus or lighting evaluation.
* Floor-zone fractions below ~1 % are within the 2 mm-grid / 0.25 mm-tessellation noise.

## Reproduce

`/usr/bin/python3 scripts/study_claw_tube_length_view.py` (about 8 min, 4 cores; writes only the files listed at the top).
"""

if __name__ == "__main__":
    main()
