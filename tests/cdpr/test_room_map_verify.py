"""INDEPENDENT verification of the room map (docs/ROOM_MAP_SPEC.md 1-5): written by the verifier, not the builder.

Nothing here reuses the builder's checkers: the reference geometry below is a separate implementation (a 1-Lipschitz
"max of slabs" signed function, minimised EXACTLY along each segment because it is convex along a line: a dense scan plus a
golden-section refinement), and the planner-safety tests sample the ACTUAL planned trajectories that the simulated robot
executed (every ``co.execute`` plan, densified to 5 mm) and the TRUE simulated claw and cables at every plant step.

Round 2 (2026-10-26, head fcdf1c5): the confirmed findings of round 1 that the builder fixed are plain tests again; H-2 became
two tests (the landing-column refusal at save, and lowering with a shape NEAR the column); the sim fixtures keep their shapes off
the landing columns (the lead's rule) but as close to the claw as the lift check allows.

Report: verification/room_map_verification.md. Run: /usr/bin/python3 -m pytest -q tests/cdpr/test_room_map_verify.py
(about 10 minutes: three simulated startups, a task and a lowering).
"""
from __future__ import annotations

import copy
import json
import math
import os
import subprocess
import threading
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from roomcleaner.cdpr.config import ConfigError, load_config, validate_obstacles
from roomcleaner.cdpr.kinematics import (claw_hits_obstacle, coverage, geometry_from_config, segment_hits_obstacle,
                                         segments_hit_obstacle, workspace_from_config)
from roomcleaner.cdpr.service import Service, create_app
from roomcleaner.cdpr.sim.harness import SimRobot
from roomcleaner.geometry import segment_intersects_box, segment_intersects_cylinder

from .simkit import fast_cfg
from .test_service import Client

REPO = Path(__file__).resolve().parents[2]
SIM = str(REPO / "config/robot.sim.json")
SIM3 = str(REPO / "config/robot.sim3.json")
BASE_WORKTREE = Path(os.environ.get("ROOM_MAP_BASE", "/tmp/base"))      # git worktree of 8b933e2 (before the room map)
EVIDENCE = REPO / "verification" / "room_map_verify_evidence.json"
_EVID: dict = {}


def _evidence(key, value):
    """Measured numbers for the report (merged into one JSON file)."""
    _EVID[key] = value
    try:
        old = json.loads(EVIDENCE.read_text()) if EVIDENCE.exists() else {}
    except ValueError:
        old = {}
    old.update(_EVID)
    EVIDENCE.write_text(json.dumps(old, indent=1, default=float))


# ===================================================================================== the verifier's own reference geometry
def sdf(q, ob, m=0.0):
    """Max-of-slabs signed function of the shape inflated by ``m``: < 0 strictly inside, > 0 outside, 1-Lipschitz."""
    q = np.asarray(q, float)
    zl, zh = ob["z_low_m"] - m, ob["height_m"] + m
    dz = np.maximum(zl - q[..., 2], q[..., 2] - zh)
    dx, dy = q[..., 0] - ob["x"], q[..., 1] - ob["y"]
    if ob["shape"] == "cylinder":
        dxy = np.sqrt(dx * dx + dy * dy) - (ob["diameter_m"] / 2 + m)
    else:
        a = np.deg2rad(ob["yaw_deg"])
        u = np.cos(a) * dx + np.sin(a) * dy
        v = -np.sin(a) * dx + np.cos(a) * dy
        dxy = np.maximum(np.abs(u) - (ob["length_m"] / 2 + m), np.abs(v) - (ob["width_m"] / 2 + m))
    return np.maximum(dxy, dz)


def seg_min_sdf(a, b, ob, m=0.0, n_dense=64, iters=90):
    """Global minimum of ``sdf`` along each segment a -> b (arrays (..., 3)). ``sdf`` restricted to a line is convex (max of
    |affine|, a norm of an affine map and affine terms), so the dense scan's best bracket holds the global minimum, which the
    golden-section search then pins down to ~1e-15 of the parameter."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    a, b = np.broadcast_arrays(a, b)
    shp = a.shape[:-1]
    a = a.reshape(-1, 3)
    b = b.reshape(-1, 3)
    t = np.linspace(0.0, 1.0, n_dense)
    f = sdf(a[:, None, :] + t[None, :, None] * (b - a)[:, None, :], ob, m)
    k = np.argmin(f, axis=1)
    lo, hi = t[np.maximum(k - 1, 0)], t[np.minimum(k + 1, n_dense - 1)]
    g = (math.sqrt(5) - 1) / 2
    for _ in range(iters):
        c = hi - g * (hi - lo)
        d = lo + g * (hi - lo)
        left = sdf(a + c[:, None] * (b - a), ob, m) < sdf(a + d[:, None] * (b - a), ob, m)
        hi = np.where(left, d, hi)
        lo = np.where(left, lo, c)
    tm = (lo + hi) / 2
    return np.minimum(f.min(axis=1), sdf(a + tm[:, None] * (b - a), ob, m)).reshape(shp)


def dense_hit(a, b, ob, m=0.0, n=20001):
    """Plain brute force (what the spec asks for): any of n points on the segment inside the inflated shape."""
    t = np.linspace(0.0, 1.0, n)[:, None]
    return bool(np.any(sdf(np.asarray(a) + t * (np.asarray(b) - np.asarray(a)), ob, m) <= 0.0))


def footprint_dist(xy, ob, m=0.0):
    """Euclidean floor distance from xy (..., 2) to the footprint inflated by ``m`` (0 inside); rectangle by local clamping."""
    xy = np.asarray(xy, float)
    dx, dy = xy[..., 0] - ob["x"], xy[..., 1] - ob["y"]
    if ob["shape"] == "cylinder":
        return np.maximum(np.sqrt(dx * dx + dy * dy) - ob["diameter_m"] / 2 - m, 0.0)
    a = np.deg2rad(ob["yaw_deg"])
    u = np.abs(np.cos(a) * dx + np.sin(a) * dy) - ob["length_m"] / 2 - m
    v = np.abs(-np.sin(a) * dx + np.cos(a) * dy) - ob["width_m"] / 2 - m
    return np.sqrt(np.maximum(u, 0) ** 2 + np.maximum(v, 0) ** 2)


def footprint_dist_bruteforce(xy, ob, m=0.0, n=600):
    """The same distance by sampling the (inflated) footprint boundary and an inside test: independent of the clamp formula."""
    xy = np.asarray(xy, float)
    if ob["shape"] == "cylinder":
        R = ob["diameter_m"] / 2 + m
        th = np.linspace(0, 2 * np.pi, 4 * n, endpoint=False)
        pts = np.c_[ob["x"] + R * np.cos(th), ob["y"] + R * np.sin(th)]
        inside = np.hypot(xy[0] - ob["x"], xy[1] - ob["y"]) <= R
    else:
        L, W = ob["length_m"] / 2 + m, ob["width_m"] / 2 + m
        s = np.linspace(-1, 1, n)
        loc = np.r_[np.c_[L * s, np.full(n, W)], np.c_[L * s, np.full(n, -W)], np.c_[np.full(n, L), W * s],
                    np.c_[np.full(n, -L), W * s]]
        a = np.deg2rad(ob["yaw_deg"])
        Rm = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
        pts = loc @ Rm.T + [ob["x"], ob["y"]]
        d = Rm.T @ (xy - [ob["x"], ob["y"]])
        inside = abs(d[0]) <= L and abs(d[1]) <= W
    return 0.0 if inside else float(np.min(np.hypot(pts[:, 0] - xy[0], pts[:, 1] - xy[1])))


def body_clearance(xy, z_bot, z_top, ob, m, r):
    """<= 0 iff the vertical claw body (axis at xy from z_bot to z_top, radius r) meets the shape inflated by ``m``."""
    zl, zh = ob["z_low_m"] - m, ob["height_m"] + m
    zgap = np.maximum(zl - np.asarray(z_top, float), np.asarray(z_bot, float) - zh)
    return np.maximum(footprint_dist(xy, ob, m) - r, zgap)


def _product_hit(a, b, ob, m=0.0):
    """The product's scalar exact test (through the shape dictionary, as the planner calls it)."""
    return segment_hits_obstacle(np.asarray(a, float), np.asarray(b, float), ob, m)


# ===================================================================================== random shapes and segments
ROOM = np.array([3.3528, 2.7432, 2.7432])


def _rand_shape(rng, kind=None):
    kind = kind or ("box" if rng.random() < 0.5 else "cylinder")
    zl = 0.0 if rng.random() < 0.6 else float(rng.uniform(0.05, 2.2))       # 40 % hang (z_low > 0)
    top = float(min(zl + rng.uniform(0.03, 1.5), ROOM[2]))
    ob = {"id": "r", "name": "R", "shape": kind, "x": float(rng.uniform(0.3, 3.0)), "y": float(rng.uniform(0.3, 2.4)),
          "z_low_m": zl, "height_m": top}
    if kind == "box":
        yaw = float(rng.choice([0.0, 90.0, 45.0, 180.0, 359.999, rng.uniform(0, 360), rng.uniform(0, 360)]))
        ob.update(length_m=float(rng.uniform(0.025, 1.5)), width_m=float(rng.uniform(0.025, 1.5)), yaw_deg=yaw)
    else:
        ob.update(diameter_m=float(rng.uniform(0.025, 1.2)))
    return ob


def _inside_point(rng, ob, m=0.0):
    zl, zh = ob["z_low_m"] - m, ob["height_m"] + m
    z = rng.uniform(zl, zh)
    if ob["shape"] == "cylinder":
        r = (ob["diameter_m"] / 2 + m) * math.sqrt(rng.random()) * 0.999
        th = rng.uniform(0, 2 * np.pi)
        return np.array([ob["x"] + r * math.cos(th), ob["y"] + r * math.sin(th), z])
    u = rng.uniform(-1, 1) * (ob["length_m"] / 2 + m) * 0.999
    v = rng.uniform(-1, 1) * (ob["width_m"] / 2 + m) * 0.999
    a = math.radians(ob["yaw_deg"])
    return np.array([ob["x"] + math.cos(a) * u - math.sin(a) * v, ob["y"] + math.sin(a) * u + math.cos(a) * v, z])


def _rand_segment(rng, ob, mode, m=0.0):
    far = lambda: np.r_[rng.uniform(-0.2, 3.5), rng.uniform(-0.2, 2.9), rng.uniform(0.0, 2.75)]
    if mode == "free":
        return far(), far()
    if mode == "end_inside":
        return _inside_point(rng, ob, m), far()
    if mode == "both_inside":
        return _inside_point(rng, ob, m), _inside_point(rng, ob, m)
    if mode == "vertical":
        p = _inside_point(rng, ob, m) if rng.random() < 0.5 else far()
        p[:2] += rng.normal(0, 0.05, 2)
        return np.r_[p[:2], rng.uniform(0, 2.75)], np.r_[p[:2], rng.uniform(0, 2.75)]
    if mode == "horizontal":
        z = rng.choice([ob["height_m"] + m, ob["z_low_m"] - m]) + rng.normal(0, 0.003)
        a, b = far(), far()
        a[2] = b[2] = z
        return a, b
    if mode == "through_cable":                                   # a cable-like segment from a ceiling corner
        a = np.r_[rng.choice([0.05, 3.30]), rng.choice([0.05, 2.69]), 2.59]
        return a, _inside_point(rng, ob, m) + rng.normal(0, 0.05, 3)
    if mode == "point":
        p = far() if rng.random() < 0.5 else _inside_point(rng, ob, m)
        return p, p.copy()
    if mode == "graze":                                           # a tangent line to the inflated boundary, shifted +-2 mm
        c = _inside_point(rng, ob, m)
        u = rng.normal(0, 1, 3)
        u /= np.linalg.norm(u)
        lo, hi = 0.0, 4.0
        for _ in range(50):                                       # boundary point along u (sdf is convex: one crossing)
            mid = (lo + hi) / 2
            if sdf(c + mid * u, ob, m) < 0:
                lo = mid
            else:
                hi = mid
        p = c + hi * u
        h = 1e-6
        g = np.array([sdf(p + h * e, ob, m) - sdf(p - h * e, ob, m) for e in np.eye(3)]) / (2 * h)
        g = g / np.linalg.norm(g) if np.linalg.norm(g) > 0 else u
        d = np.cross(g, rng.normal(0, 1, 3))
        d /= np.linalg.norm(d)
        off = rng.uniform(-0.002, 0.002)
        return p - 2 * d + off * g, p + 2 * d + off * g
    raise ValueError(mode)


MODES = ("free", "free", "end_inside", "both_inside", "vertical", "horizontal", "through_cable", "point", "graze", "graze")


# ===================================================================================== 1. geometry
def test_exact_segment_tests_match_an_independent_exact_minimum_and_dense_sampling_on_12000_random_cases():
    """12 000 shape/segment pairs (boxes at any yaw, cylinders, 40 % hanging, all segment modes incl. grazing within 2 mm,
    vertical, horizontal at the top / bottom face, zero length, endpoints inside), margin 0 and margins up to 0.15 m.
    Reference: the exact minimum of the signed function along the segment. A disagreement is allowed only within 1e-7 m of
    the boundary (touching counts as a hit for the product: conservative). The plain dense sampler (20 001 points) may only
    MISS (never invent) a hit, and only for passes within its spacing of the boundary."""
    rng = np.random.default_rng(20261026)
    n, fn, fp, boundary, dense_miss, dense_wrong = 12000, [], [], 0, 0, []
    vec_a, vec_b, vec_ob, vec_m, vec_exp = [], [], [], [], []
    for k in range(n):
        ob = _rand_shape(rng)
        m = 0.0 if k % 3 == 0 else float(rng.choice([0.05, 0.10, 0.15]))
        mode = MODES[k % len(MODES)]
        a, b = _rand_segment(rng, ob, mode, m)
        ref = float(seg_min_sdf(a, b, ob, m))
        got = _product_hit(a, b, ob, m)
        if abs(ref) <= 1e-7:
            boundary += 1
        elif ref < 0 and not got:
            fn.append((mode, ob, a.tolist(), b.tolist(), m, ref))
        elif ref > 0 and got:
            fp.append((mode, ob, a.tolist(), b.tolist(), m, ref))
        if k % 4 == 0:                                            # the spec's brute force, on a quarter of the cases
            dh = dense_hit(a, b, ob, m)
            if dh and ref > 1e-9:
                dense_wrong.append((mode, ref))
            if not dh and ref < 0:
                dense_miss += 1
                spacing = np.linalg.norm(np.asarray(b) - np.asarray(a)) / 20000
                assert -ref <= spacing / 2 + 1e-9, (mode, ref, spacing)
        vec_a.append(a), vec_b.append(b), vec_ob.append(ob), vec_m.append(m), vec_exp.append(got)
    _evidence("geometry_random", {"cases": n, "false_negatives": len(fn), "false_positives": len(fp), "boundary_within_1e-7": boundary,
                                  "dense_sampler_misses_grazing": dense_miss, "dense_sampler_inventions": len(dense_wrong)})
    assert not fn, fn[:3]
    assert not fp, fp[:3]
    assert not dense_wrong, dense_wrong[:3]
    # the vectorised forms (used by the coverage grid) answer exactly as the scalar test, on every case
    mism = [i for i, (a, b, ob, m, e) in enumerate(zip(vec_a, vec_b, vec_ob, vec_m, vec_exp))
            if bool(segments_hit_obstacle(np.asarray(a)[None], np.asarray(b)[None], ob, m)[0]) != e]
    _evidence("geometry_vectorised_mismatches", len(mism))
    assert not mism, [(MODES[i % len(MODES)], vec_ob[i]) for i in mism[:3]]


@pytest.mark.parametrize("yaw", [0.0, 30.0, 45.0, 90.0, 137.0])
def test_box_edge_cases_by_hand(yaw):
    ob = {"shape": "box", "x": 1.5, "y": 1.2, "length_m": 0.8, "width_m": 0.4, "yaw_deg": yaw, "z_low_m": 0.0, "height_m": 1.0}
    c, hl, hw, a = (1.5, 1.2), 0.4, 0.2, math.radians(yaw)
    loc = lambda u, v, z: np.array([1.5 + math.cos(a) * u - math.sin(a) * v, 1.2 + math.sin(a) * u + math.cos(a) * v, z])
    # both endpoints inside / one inside
    assert segment_intersects_box(loc(0.1, 0.05, 0.5), loc(-0.1, 0.0, 0.6), c, hl, hw, a, 0, 1)
    assert segment_intersects_box(loc(0.1, 0.05, 0.5), [3.3, 2.7, 2.6], c, hl, hw, a, 0, 1)
    # vertical: through the top face, stopping 1 mm above it, starting below the floor-level bottom
    assert segment_intersects_box(loc(0.39, 0.19, 2.0), loc(0.39, 0.19, 0.2), c, hl, hw, a, 0, 1)
    assert not segment_intersects_box(loc(0.39, 0.19, 2.0), loc(0.39, 0.19, 1.001), c, hl, hw, a, 0, 1)
    assert not segment_intersects_box(loc(0.401, 0.0, 2.0), loc(0.401, 0.0, 0.0), c, hl, hw, a, 0, 1)
    # just past a corner diagonally (1 mm outside both slabs at the corner) vs 1 mm inside
    # (local line u + v = hl + hw + 2 off: outside for off > 0 since inside needs u + v <= hl + hw)
    for off, hit in ((0.001, False), (-0.001, True)):
        p0, p1 = loc(hl + off - 1.0, hw + off + 1.0, 0.5), loc(hl + off + 1.0, hw + off - 1.0, 0.5)
        assert segment_intersects_box(p0, p1, c, hl, hw, a, 0, 1) == hit, off
    # zero-length segments
    assert segment_intersects_box(loc(0, 0, 0.5), loc(0, 0, 0.5), c, hl, hw, a, 0, 1)
    assert not segment_intersects_box(loc(0.5, 0, 0.5), loc(0.5, 0, 0.5), c, hl, hw, a, 0, 1)
    # a hanging box (z 1.8-2.4): a cable passing under it, and one through its bottom face
    hb = dict(ob, z_low_m=1.8, height_m=2.4)
    assert not _product_hit(loc(-1.0, 0, 1.7), loc(1.0, 0, 1.75), hb)
    assert _product_hit(loc(-1.0, 0, 1.7), loc(1.0, 0, 1.9), hb)


def test_cylinder_edge_cases_by_hand():
    ob = {"shape": "cylinder", "x": 1.0, "y": 1.0, "diameter_m": 0.4, "z_low_m": 0.5, "height_m": 1.5}
    # tangent horizontal line at r = 0.2 exactly, 1 mm outside and 1 mm inside
    assert _product_hit([0, 1.2, 1.0], [2, 1.2, 1.0], ob)                 # touching = hit (conservative)
    assert not _product_hit([0, 1.201, 1.0], [2, 1.201, 1.0], ob)
    assert _product_hit([0, 1.199, 1.0], [2, 1.199, 1.0], ob)
    # vertical inside the radius, entirely below the hanging cylinder vs reaching into it
    assert not _product_hit([1.05, 1.0, 0.0], [1.05, 1.0, 0.499], ob)
    assert _product_hit([1.05, 1.0, 0.0], [1.05, 1.0, 0.501], ob)
    # a slanted cable crossing the radius only above the top
    assert not _product_hit([0.0, 1.0, 2.6], [2.0, 1.0, 1.55], ob)
    # endpoint inside
    assert _product_hit([1.0, 1.0, 1.0], [3.0, 2.5, 2.6], ob)


def test_margin_inflates_sideways_and_in_height_exactly():
    """Every shape is inflated by the margin sideways (box sides, cylinder radius) and at the top and the bottom (hanging)."""
    rng = np.random.default_rng(5)
    for _ in range(300):
        ob = _rand_shape(rng)
        m = float(rng.uniform(0.02, 0.2))
        zmid = (ob["z_low_m"] + ob["height_m"]) / 2
        # sideways: a vertical segment at distance m -/+ 1 mm from the footprint edge, along a random direction
        th = rng.uniform(0, 2 * np.pi)
        dirv = np.array([math.cos(th), math.sin(th)])
        lo, hi = 0.0, 3.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if footprint_dist([ob["x"] + mid * dirv[0], ob["y"] + mid * dirv[1]], ob) > 0:
                hi = mid
            else:
                lo = mid
        for extra, hit in ((m - 0.001, True), (m + 0.001, False)):
            # distance along dirv beyond the edge does not equal Euclidean distance for a box corner region: correct for it
            s = hi
            for _ in range(60):
                p = np.array([ob["x"], ob["y"]]) + s * dirv
                dd = footprint_dist(p, ob)
                s += (extra - dd)
            p = np.array([ob["x"], ob["y"]]) + s * dirv
            exp_hit = footprint_dist(p, ob, m) <= 0
            got = _product_hit(np.r_[p, zmid - 0.01], np.r_[p, zmid + 0.01], ob, m)
            assert got == exp_hit, (ob, m, extra, footprint_dist(p, ob))
            if ob["shape"] == "cylinder" or footprint_dist(p, ob, 0) == footprint_dist(p, ob, 0):
                pass
        # in height: a horizontal segment straight through the centre at top + m -/+ 1 mm (and bottom - m for hanging shapes)
        for z, hit in ((ob["height_m"] + m - 0.001, True), (ob["height_m"] + m + 0.001, False)):
            assert _product_hit([ob["x"] - 2, ob["y"], z], [ob["x"] + 2, ob["y"], z], ob, m) == hit, (ob, m, z)
        if ob["z_low_m"] > m + 0.002:
            for z, hit in ((ob["z_low_m"] - m + 0.001, True), (ob["z_low_m"] - m - 0.001, False)):
                assert _product_hit([ob["x"] - 2, ob["y"], z], [ob["x"] + 2, ob["y"], z], ob, m) == hit, (ob, m, z)


def _cfg_ws(obstacles, path=SIM, **over):
    raw = json.loads(Path(path).read_text())
    raw["obstacles"] = obstacles
    for k, v in over.items():
        d = raw
        ks = k.split(".")
        for x in ks[:-1]:
            d = d.setdefault(x, {})
        d[ks[-1]] = v
    cfg = load_config(raw)
    A = cfg.anchor_priors()
    return cfg, geometry_from_config(cfg, A), workspace_from_config(cfg, A, lowest_point_z=float(cfg.claw.lowest_point_body_m[2]))


def _old_24(a, b, ob, n=24):
    for s in np.linspace(0, 1, n):
        q = a + s * (b - a)
        if ob["z_low_m"] <= q[2] <= ob["height_m"] and math.hypot(q[0] - ob["x"], q[1] - ob["y"]) <= ob["diameter_m"] / 2:
            return True
    return False


def test_a_5_cm_pole_on_any_cable_line_is_caught_and_one_beside_it_is_not():
    """Random claw poses; a 5 cm pole put on a random cable's line at a random place (between the old samples or not),
    offset sideways by up to 24 mm: always refused. Offset by 26 mm (and margin 0, body radius 0, far from the claw):
    not refused by that cable. Then the default 0.10 m margin catches it at up to 0.124 m."""
    cfg, geo, _ = _cfg_ws([])
    A = cfg.anchor_priors()
    rng = np.random.default_rng(11)
    old_missed = caught = 0
    for _ in range(400):
        p = np.r_[rng.uniform(0.5, 2.85), rng.uniform(0.5, 2.25), rng.uniform(0.7, 1.9)]
        att = geo.attach_world(p)
        i = int(rng.integers(4))
        s = rng.uniform(0.08, 0.85)
        q = A[i] + s * (att[i] - A[i])
        d = att[i, :2] - A[i, :2]
        nrm = np.array([-d[1], d[0]]) / np.linalg.norm(d)
        for off, margin, expect in ((rng.uniform(-0.024, 0.024), 0.0, True), (0.026, 0.0, False), (0.124, 0.10, True)):
            pole = {"id": "p", "name": "Pole", "shape": "cylinder", "x": float(q[0] + off * nrm[0]), "y": float(q[1] + off * nrm[1]),
                    "diameter_m": 0.05, "z_low_m": 0.0, "height_m": 2.7}
            if np.hypot(pole["x"] - p[0], pole["y"] - p[1]) < 0.5 or not (0 <= pole["x"] <= W and 0 <= pole["y"] <= D):
                continue
            _, g2, ws = _cfg_ws([pole], **{"motion.obstacle_margin_m": margin, "claw.body_radius_m": 0.0})
            v = ws.obstacle_violations(g2, p)
            hit_i = any(f"cable {cfg.ids[i]} would cross" in x for x in v)
            if expect:
                assert hit_i, (p, i, off, margin, v)
                caught += 1
                if margin == 0.0 and not _old_24(A[i], att[i], pole):
                    old_missed += 1
            else:
                assert not hit_i, (p, i, off, v)
    _evidence("pole_5cm", {"caught": caught, "of_which_the_old_24_sample_test_missed": old_missed})
    assert old_missed > 50                                       # the case the spec is about really exists


def test_the_claw_body_check_matches_an_independent_model():
    """Claw body = vertical axis from its lowest point to its attachment plane, widened by claw.body_radius_m, against each
    shape inflated by the margin. Compared with a brute-force footprint distance (boundary sampling) at +-2 mm of the limit."""
    cfg, geo, ws = _cfg_ws([])
    low = float(cfg.claw.lowest_point_body_m[2])
    m, r = cfg.motion.obstacle_margin_m, cfg.claw.body_radius_m
    assert (m, r) == (0.10, 0.07)
    rng = np.random.default_rng(17)
    n = 0
    for _ in range(250):
        ob = _rand_shape(rng)
        th = rng.uniform(0, 2 * np.pi)
        base = np.array([ob["x"], ob["y"]])
        dirv = np.array([math.cos(th), math.sin(th)])
        for target, hit in ((m + r - 0.002, True), (m + r + 0.002, False)):
            s = 0.0
            for _ in range(80):
                s += target - footprint_dist_bruteforce(base + s * dirv, ob)
            xy = base + s * dirv
            bf = footprint_dist_bruteforce(xy, ob)
            if abs(bf - target) > 5e-4:
                continue
            # claw origin so its body spans the shape's height band
            zc = min(max((ob["z_low_m"] + ob["height_m"]) / 2 - low / 2, 0.0), 2.3)
            got = claw_hits_obstacle(xy, zc + low, zc, ob, m, r)
            exp = bool(body_clearance(xy, zc + low, zc, ob, m, r) <= 0)
            assert got == exp == hit or (exp != hit and got == exp), (ob, target, bf, got, exp)
            n += 1
        # height: lowest point m -/+ 2 mm above the top, axis over the centre
        for dz, hit in ((m - 0.002, True), (m + 0.002, False)):
            zc = ob["height_m"] + dz - low
            assert claw_hits_obstacle(base, zc + low, zc, ob, m, r) == hit, (ob, dz)
        # hanging shapes: the attachment plane (top of the body) m -/+ 2 mm below the bottom
        if ob["z_low_m"] - m > 0.6:
            for dz, hit in ((-m + 0.002, True), (-m - 0.002, False)):
                zc = ob["z_low_m"] + dz
                if zc + low > 0:
                    assert claw_hits_obstacle(base, zc + low, zc, ob, m, r) == hit, (ob, dz)
    assert n > 300
    # through the Workspace (what the planner calls): the deck's shelf held over the claw, and the message text
    shelf = {"id": "s", "name": "Shelf", "shape": "box", "x": 1.6, "y": 1.3, "length_m": 0.8, "width_m": 0.4, "yaw_deg": 0,
             "z_low_m": 0.0, "height_m": 0.5}
    _, g2, ws2 = _cfg_ws([shelf])
    v = ws2.obstacle_violations(g2, [1.6 + 0.4 + 0.17 - 0.003, 1.3, 0.9])
    assert "the claw would enter the Shelf" in v
    assert not any("claw" in x for x in ws2.obstacle_violations(g2, [1.6 + 0.4 + 0.17 + 0.003, 1.3, 0.9]))


# ===================================================================================== 2. configuration
BOX = {"id": "o1", "name": "Shelf", "shape": "box", "x": 0.83, "y": 0.68, "length_m": 0.80, "width_m": 0.40, "yaw_deg": 0.0,
       "z_low_m": 0.0, "height_m": 1.90}
CYL = {"id": "o2", "name": "Ceiling fan", "shape": "cylinder", "x": 1.68, "y": 1.37, "diameter_m": 1.10, "z_low_m": 2.25,
       "height_m": 2.74}
W, D, H = ROOM


@pytest.mark.parametrize("ob, ok, words", [
    (dict(BOX, shape="sphere"), False, "unknown shape"),
    ({k: v for k, v in BOX.items() if k != "shape"}, False, "unknown shape"),
    (dict(BOX, length_m=0.02), False, "too small"),                       # "2 cm or less": exactly 2 cm is refused
    (dict(BOX, width_m=0.0201), True, ""),
    (dict(CYL, diameter_m=0.02), False, "too small"),
    (dict(CYL, diameter_m=-0.3), False, "too small"),
    (dict(BOX, length_m=float(max(W, D)) + 0.01), False, "larger than the room"),
    (dict(CYL, diameter_m=float(max(W, D)) + 0.01, x=1.6, y=1.3, z_low_m=0.0, height_m=1.0), False, "larger than the room"),
    (dict(BOX, z_low_m=1.90), False, "below its top"),                    # z_low == height
    (dict(BOX, z_low_m=1.95), False, "below its top"),
    (dict(BOX, z_low_m=-0.01), False, "below the floor"),
    (dict(CYL, height_m=float(H) + 0.05), True, ""),                      # ceiling + 5 cm is the limit
    (dict(CYL, height_m=float(H) + 0.051), False, "above the ceiling"),
    (dict(BOX, x=0.0, y=0.0), True, ""),                                  # a centre ON the wall line is inside
    (dict(BOX, x=float(W), y=float(D)), True, ""),
    (dict(BOX, x=-0.001), False, "outside the room"),
    (dict(BOX, y=float(D) + 0.001), False, "outside the room"),
    (dict(BOX, x=float("nan")), False, "finite number"),
    (dict(BOX, height_m=float("inf")), False, "finite number"),
    (dict(BOX, height_m=True), False, "finite number"),
    (dict(BOX, x="1.0"), False, "finite number"),
    (dict(BOX, diameter_m=0.5), False, "unknown keys"),
    (dict(CYL, yaw_deg=10.0), False, "unknown keys"),
    (dict(BOX, yaw_deg=-90.0), True, ""),
    (dict(BOX, name="x" * 41), False, "40 characters"),
    (dict(BOX, id=""), False, "id must be text"),
])
def test_every_validation_rule(ob, ok, words):
    out, errs = validate_obstacles([ob], ROOM)
    if ok:
        assert not errs, errs
        assert len(out) == 1
    else:
        assert errs and words in " ".join(errs), errs
        raw = json.loads(Path(SIM).read_text())
        raw["obstacles"] = [ob]
        with pytest.raises(ConfigError):
            load_config(raw)


def test_shape_count_limit_ids_and_canonical_form():
    many = [dict(BOX, id=f"s{i}") for i in range(50)]
    assert not validate_obstacles(many, ROOM)[1]                          # 50 is allowed
    assert any("at most 50" in e for e in validate_obstacles(many + [dict(BOX, id="s50")], ROOM)[1])
    out, errs = validate_obstacles([dict(BOX, id=None), {k: v for k, v in CYL.items() if k != "id"}, dict(BOX, id="o1")], ROOM)
    assert any("duplicate" in e for e in errs) is False and [o["id"] for o in out] == ["o2", "o3", "o1"], (out, errs)
    out, _ = validate_obstacles([dict(BOX, yaw_deg=-90.0)], ROOM)
    assert out[0]["yaw_deg"] == 270.0
    # a square is a box with equal sides (the app keeps them equal); the planner sees a plain box
    sq = dict(BOX, length_m=0.5, width_m=0.5)
    assert validate_obstacles([sq], ROOM)[0][0]["shape"] == "box"


def test_old_cylinder_format_loads_and_gives_the_new_cylinders_answers():
    old = {"x": 1.2, "y": 1.1, "r": 0.15, "z_low": 0.3, "z_high": 1.4, "name": "lamp"}
    out, errs = validate_obstacles([old], ROOM)
    assert not errs and out[0] == {"id": "o1", "name": "lamp", "shape": "cylinder", "x": 1.2, "y": 1.1, "diameter_m": 0.3,
                                   "z_low_m": 0.3, "height_m": 1.4}
    # an old entry is still validated (its rules apply after conversion)
    assert validate_obstacles([dict(old, r=0.005)], ROOM)[1]
    assert validate_obstacles([dict(old, z_low=1.5)], ROOM)[1]
    assert validate_obstacles([dict(old, x=9)], ROOM)[1]
    # mixed with new entries in one file
    raw = json.loads(Path(SIM).read_text())
    raw["obstacles"] = [old, BOX]
    cfg = load_config(raw)
    assert [o["shape"] for o in cfg.obstacles] == ["cylinder", "box"] and cfg.obstacles[0]["id"] == "o2"  # o1 is taken by BOX
    _, geo, ws_old = _cfg_ws([old])
    _, _, ws_new = _cfg_ws([out[0]])
    rng = np.random.default_rng(1)
    for _ in range(500):
        p = np.r_[rng.uniform(0.2, 3.15), rng.uniform(0.2, 2.55), rng.uniform(0.52, 2.19)]
        assert ws_old.violations(geo, p) == ws_new.violations(geo, p)


_BASE_SCRIPT = r"""
import json, sys
import numpy as np
from roomcleaner.cdpr.config import load_config
from roomcleaner.cdpr.kinematics import geometry_from_config, workspace_from_config
from roomcleaner.cdpr.trajectory import limits_from_config, model_from, plan_line
out = {}
for path in sys.argv[1:]:
    cfg = load_config(path)
    A = cfg.anchor_priors()
    geo = geometry_from_config(cfg, A)
    ws = workspace_from_config(cfg, A, lowest_point_z=float(cfg.claw.lowest_point_body_m[2]))
    rng = np.random.default_rng(99)
    pts = np.c_[rng.uniform(-0.1, 3.5, 3000), rng.uniform(-0.1, 2.9, 3000), rng.uniform(0.0, 2.75, 3000)]
    v = [ws.violations(geo, p) for p in pts]
    vl = [ws.violations(geo, p, allow_low=True) for p in pts[:500]]
    model = model_from(geo, cfg, {s.id: float(np.linalg.norm(A[k] - (np.r_[cfg.room_m[:2] / 2, 1.0]))) for k, s in enumerate(cfg.stations)})
    lim = limits_from_config(cfg)
    plans = []
    for a, b in (([1.2, 1.0, 1.0], [2.1, 1.6, 1.4]), ([1.676, 1.0, 0.8], [1.676, 1.0, 1.6])):
        try:
            pl = plan_line(model, np.array(a), np.array(b), lim, ws=ws, label="x")
            plans.append([pl.times.round(9).tolist(), pl.pos.round(6).tolist()])
        except Exception as e:
            plans.append(str(e))
    out[path] = {"pts": pts.round(12).tolist(), "v": v, "vl": vl, "plans": plans}
print(json.dumps(out))
"""


def test_a_config_without_obstacles_behaves_exactly_as_the_base_commit():
    """Same violations (3000 random points per profile, plus allow_low) and the same planned line moves as the code BEFORE the room
    map (git worktree of 8b933e2 at $ROOM_MAP_BASE, default /tmp/base), for the four- and three-station sim profiles."""
    if not (BASE_WORKTREE / "roomcleaner" / "cdpr" / "kinematics.py").exists():
        pytest.skip(f"no base worktree at {BASE_WORKTREE} (git worktree add {BASE_WORKTREE} 8b933e2)")
    script = _BASE_SCRIPT
    paths = [SIM, SIM3]
    env = {**os.environ, "PYTHONPATH": str(BASE_WORKTREE)}
    base = json.loads(subprocess.run(["/usr/bin/python3", "-c", script, *paths], cwd=BASE_WORKTREE, env=env, capture_output=True,
                                     text=True, check=True).stdout)
    env["PYTHONPATH"] = str(REPO)
    head = json.loads(subprocess.run(["/usr/bin/python3", "-c", script, *paths], cwd=REPO, env=env, capture_output=True, text=True,
                                     check=True).stdout)
    for p in paths:
        assert base[p]["pts"] == head[p]["pts"]
        diff = [i for i, (x, y) in enumerate(zip(base[p]["v"], head[p]["v"])) if x != y]
        assert not diff, (p, diff[:3], [base[p]["v"][i] for i in diff[:3]], [head[p]["v"][i] for i in diff[:3]])
        assert base[p]["vl"] == head[p]["vl"]
        assert base[p]["plans"] == head[p]["plans"]
    _evidence("no_obstacles_equals_base", {"points_per_profile": 3000, "profiles": [Path(p).name for p in paths],
                                           "refused_points": [sum(1 for x in head[p]["v"] if x) for p in paths]})


# ===================================================================================== 4. API (no motion needed)
def _svc(tmp_path, config_path=None, cfg=None):
    r = SimRobot(cfg or fast_cfg(), seed=11, data_dir=tmp_path)
    svc = Service(r.ctx, data_dir=tmp_path, config_path=config_path)
    app = create_app(svc)
    return r, svc, Client(app, svc.token), app


def _put(c, body, token=None):
    h = c.h if token is None else {"X-Token": token}
    return c.c.put("/api/room_map", json=body, headers=h)


SHAPES = [dict(BOX), dict(CYL)]


def test_all_three_endpoints_need_the_session_token(tmp_path):
    r, svc, c, app = _svc(tmp_path)
    raw = app.test_client()
    for tok in (None, "", "wrong-token", svc.token[:-1]):
        h = {} if tok is None else {"X-Token": tok}
        assert raw.get("/api/room_map", headers=h).status_code == 401
        assert raw.post("/api/room_map/preview", json={"obstacles": SHAPES}, headers=h).status_code == 401
        assert raw.put("/api/room_map", json={"obstacles": SHAPES}, headers=h).status_code == 401
    assert svc.ctx.cfg.obstacles == []
    assert raw.get("/api/room_map", headers=c.h).status_code == 200
    # the token is not accepted in the URL for these routes (only the MJPEG stream takes it there)
    assert raw.get(f"/api/room_map?token={svc.token}").status_code == 401
    # PUT without a JSON body is refused like a POST
    assert raw.put("/api/room_map", data=json.dumps({"obstacles": []}), content_type="text/plain", headers=c.h).status_code == 415


def test_get_carries_what_the_map_draws(tmp_path):
    r, svc, c, app = _svc(tmp_path)
    g = c.get("/api/room_map").get_json()
    for k in ("obstacles", "hamper", "units", "room_m", "anchors", "stations_active", "usable_box", "start_point_m"):
        assert k in g, k
    assert g["usable_box"] == [[0.2, 0.2], [pytest.approx(W - 0.2), pytest.approx(D - 0.2)]]
    assert g["hamper"]["x"] == pytest.approx(2.1764) and g["units"] == "ft-in"
    r3, svc3, c3, _ = _svc(tmp_path / "three", cfg=load_config(SIM3))
    g3 = c3.get("/api/room_map").get_json()
    assert g3["stations_active"] == ["A", "B", "C"] and g3["anchors"]["D"]["active"] is False
    tri = np.array(g3["usable_triangle"])
    assert tri.shape == (3, 2)
    # the shrunk triangle lies inside the anchors' triangle and contains the start point
    sp = np.array(g3["start_point_m"])
    P = np.array([g3["anchors"][k]["xyz"][:2] for k in "ABC"])
    def bary(T, x):
        M = np.array([[T[0, 0] - T[2, 0], T[1, 0] - T[2, 0]], [T[0, 1] - T[2, 1], T[1, 1] - T[2, 1]]])
        l = np.linalg.solve(M, x - T[2])
        return np.r_[l, 1 - l.sum()]
    assert np.all(bary(tri, sp) > 0) and all(np.all(bary(P, v) >= -1e-9) for v in tri)


def test_preview_never_saves_valid_or_invalid_in_hardware_mode(tmp_path):
    cfgp = tmp_path / "robot.json"
    cfgp.write_text(Path(SIM).read_text())
    before = cfgp.read_bytes()
    r, svc, c, app = _svc(tmp_path / "d", config_path=cfgp)
    for body in ({"obstacles": SHAPES, "hamper": {"x": 1.0, "y": 1.0, "height_m": 0.4}, "units": "m"},
                 {"obstacles": [dict(BOX, x=-5)]}, {"obstacles": "x"}, {"nonsense": 1}):
        res = c.post("/api/room_map/preview", json=body)
        assert res.status_code == 200
    assert cfgp.read_bytes() == before
    assert svc.ctx.cfg.obstacles == [] and svc.ctx.cfg.map_units == "ft-in" and svc.ctx.cfg.tasks.hamper_room_m == [2.1764, 1.0716]
    assert c.get("/api/room_map").get_json()["obstacles"] == []
    # PUT invalid: 400 with plain messages, the file is untouched
    res = _put(c, {"obstacles": [dict(BOX, x=-5)]})
    assert res.status_code == 400 and res.get_json()["errors"]
    assert cfgp.read_bytes() == before


def test_put_persists_to_the_config_file_keeping_everything_else(tmp_path):
    cfgp = tmp_path / "robot.json"
    cfgp.write_text(Path(SIM).read_text())
    orig = json.loads(cfgp.read_text())
    r, svc, c, app = _svc(tmp_path / "d", config_path=cfgp)
    res = _put(c, {"obstacles": SHAPES, "hamper": {"x": 1.0, "y": 2.0, "height_m": 0.45}, "units": "m"})
    assert res.status_code == 200 and res.get_json()["text"] == "Saved: the planner now avoids 2 shapes"
    new = json.loads(cfgp.read_text())
    assert new["obstacles"] == SHAPES and new["map_units"] == "m"
    assert new["tasks"]["hamper_room_m"] == [1.0, 2.0] and new["tasks"]["hamper_height_m"] == 0.45
    for k in orig:
        if k not in ("obstacles", "tasks"):
            assert new[k] == orig[k], k
    assert {k: v for k, v in new["tasks"].items() if k not in ("hamper_room_m", "hamper_height_m")} == \
           {k: v for k, v in orig["tasks"].items() if k not in ("hamper_room_m", "hamper_height_m")}
    again = load_config(cfgp)
    assert again.obstacles == SHAPES and again.map_units == "m"
    # an empty map is a valid save too, and the file loads with no shapes
    assert _put(c, {"obstacles": []}).status_code == 200
    assert load_config(cfgp).obstacles == []


def test_put_in_sim_lives_in_memory_only(tmp_path):
    before = {p: Path(p).read_bytes() for p in (SIM, SIM3)}
    r, svc, c, app = _svc(tmp_path)
    assert svc.config_path is None
    assert _put(c, {"obstacles": SHAPES}).status_code == 200
    assert svc.ctx.cfg.obstacles == SHAPES
    assert all(Path(p).read_bytes() == b for p, b in before.items())
    assert not list(tmp_path.glob("*.json")) or all("obstacles" not in f.read_text() for f in tmp_path.glob("*.json"))


from roomcleaner.cdpr.supervisor import STATES as _SUP_STATES   # noqa: E402


@pytest.mark.parametrize("state", [s for s in _SUP_STATES if s not in ("DISARMED", "PARKED", "READY", "PAUSED")])
def test_put_is_refused_in_every_other_supervisor_state(tmp_path, state):
    """Every supervisor state outside DISARMED / PARKED / READY / PAUSED (the startup's steps all run inside STARTUP)."""
    r, svc, c, app = _svc(tmp_path)
    svc.sup.state = state
    res = _put(c, {"obstacles": SHAPES})
    assert res.status_code == 409, (state, res.get_json())
    assert svc.ctx.cfg.obstacles == []


def test_put_allowed_in_disarmed_and_parked(tmp_path):
    r, svc, c, app = _svc(tmp_path)
    assert _put(c, {"obstacles": SHAPES}).status_code == 200
    svc.sup.state = "PARKED"
    assert _put(c, {"obstacles": [dict(BOX)]}).status_code == 200 and len(svc.ctx.cfg.obstacles) == 1


def test_editing_the_room_size_keeps_the_saved_map_loadable(tmp_path):
    """Round 1 finding M-1 (fixed in round 2): the room edit is refused with the shapes named, or the file still loads."""
    cfgp = tmp_path / "robot.json"
    cfgp.write_text(Path(SIM).read_text())
    r, svc, c, app = _svc(tmp_path / "d", config_path=cfgp)
    shelf = dict(BOX, x=3.1, y=2.5, height_m=2.6)                  # near the far corner, tall
    assert _put(c, {"obstacles": [shelf]}).status_code == 200
    res = c.post("/api/room", json={"width_m": 3.0, "depth_m": 2.4, "height_m": 2.4})
    if res.status_code == 200:                                     # accepted: the file must still load
        load_config(cfgp)
    else:                                                          # or refused with the reason (also acceptable)
        err = res.get_json().get("error", "")
        assert "Shelf" in err and "Map" in err, err
        load_config(cfgp)                                          # and a refused edit changed nothing
        assert svc.ctx.cfg.room_m.tolist() == pytest.approx(list(ROOM))
    _evidence("m1_room_edit", (res.status_code, res.get_json()))


# ===================================================================================== 5. coverage
def _cov_reference(svc, shapes):
    """The verifier's own coverage classification of every cell (first reason, in the product's documented order)."""
    ctx, cfg = svc.ctx, svc.ctx.cfg
    g = Client(create_app(svc), svc.token).get("/api/room_map").get_json()
    lo, hi = np.array(g["usable_box"][0]), np.array(g["usable_box"][1])
    A = cfg.anchor_priors()
    attach = cfg.attachment_points()
    low = float(cfg.claw.lowest_point_body_m[2])
    zf = -low
    h0, h1 = zf + cfg.tasks.grip_clearance_m, zf + 0.10 + cfg.tasks.approach_clearance_m
    hs = np.unique(np.r_[h0, h1, np.arange(h0, h1, 0.1)])
    m, r = cfg.motion.obstacle_margin_m, cfg.claw.body_radius_m
    nx, ny = int(math.ceil(W / 0.1 - 1e-9)), int(math.ceil(D / 0.1 - 1e-9))
    out = []
    for iy in range(ny):
        for ix in range(nx):
            x, y = (ix + 0.5) * 0.1, (iy + 0.5) * 0.1
            why = None
            for ob in shapes:
                name = f"the {ob['name']}" if ob.get("name") else f"shape {ob['id']}"
                for i, sid in enumerate(cfg.ids):
                    a = np.broadcast_to(A[i], (len(hs), 3))
                    b = np.c_[np.full(len(hs), x), np.full(len(hs), y), hs] + attach[i]
                    if np.any(seg_min_sdf(a, b, ob, m) <= 0):
                        why = f"cable {sid} would cross {name}"
                        break
                if why:
                    break
                if body_clearance([x, y], h0 + low, h1 + max(float(attach[:, 2].max()), 0.0), ob, m, r) <= 0:
                    why = f"the claw would enter {name}"
                    break
            if why is None and (x < lo[0] or y < lo[1] or x > hi[0] or y > hi[1]):
                why = "area"
            out.append(why or "ok-or-trust")
    return nx, ny, out


def test_coverage_reason_per_cell_matches_an_independent_computation_and_hand_checked_cells(tmp_path):
    r, svc, c, app = _svc(tmp_path)
    shapes = [dict(BOX), {"id": "o3", "name": "Lamp", "shape": "cylinder", "x": 2.6, "y": 1.9, "diameter_m": 0.3, "z_low_m": 0.0,
                          "height_m": 1.6}, {"id": "o4", "name": "", "shape": "box", "x": 2.2, "y": 0.7, "length_m": 0.5,
                                             "width_m": 0.3, "yaw_deg": 35.0, "z_low_m": 0.0, "height_m": 0.45}, dict(CYL)]
    pv = c.post("/api/room_map/preview", json={"obstacles": shapes}).get_json()
    assert pv["ok"], pv
    cov = pv["coverage"]
    nx, ny, ref = _cov_reference(svc, validate_obstacles(shapes, ROOM)[0])
    assert (cov["nx"], cov["ny"]) == (nx, ny) == (34, 28)
    got = [cov["reasons"][k] for k in cov["cells"]]
    bad = []
    for k, (gr, rr) in enumerate(zip(got, ref)):
        if rr.startswith(("cable", "the claw")):
            ok = gr["text"] == rr
        elif rr == "area":
            ok = gr["kind"] == "area"
        else:
            ok = gr["kind"] in ("ok", "trust")
        if not ok:
            bad.append(((k % nx + 0.5) / 10, (k // nx + 0.5) / 10, gr["text"], rr))
    _evidence("coverage_cells", {"cells": len(ref), "mismatches": len(bad), "first": bad[:5],
                                 "counts": cov["counts"], "server_ms": cov["ms"]})
    assert not bad, bad[:5]

    def at(x, y):
        return cov["reasons"][cov["cells"][int(y / 0.1) * nx + int(x / 0.1)]]
    # hand check 1: cell (1.75, 1.35), the claw's A attachment point at (1.708, 1.308, 0.527) at the grip height. The line from
    # anchor A (0.05, 0.05, 2.593) is inside the shelf's inflated footprint (x 0.33-1.33, y 0.38-0.98) for s = 0.262-0.739 of its
    # length, and below the inflated top 2.00 m for s >= (2.593 - 2.0) / 2.066 = 0.287: it crosses -> cable A, Shelf
    assert at(1.75, 1.35)["text"] == "cable A would cross the Shelf"
    # hand check 2 (lamp alone): cell centre (2.85, 1.85), 0.10 m from the lamp's rim. Cable A's attachment point is at
    # (2.808, 1.808): at x = 2.6 its line is at y = 0.05 + 2.55 * 0.6374 = 1.675, 0.225 m from the lamp axis (< 0.15 + 0.10) and
    # about 0.68 m high (< 1.70): cable A crosses the lamp before the body check is reached
    lamp_only = c.post("/api/room_map/preview", json={"obstacles": [shapes[1]]}).get_json()["coverage"]
    t = lamp_only["reasons"][lamp_only["cells"][18 * nx + 28]]["text"]
    assert t == "cable A would cross the Lamp", t
    # hand check 3: next to the A-B wall, inside the 0.2 m wall margin
    assert at(3.0, 0.05)["kind"] == "area"
    # hand check 4: the unnamed turned box is reported by its id
    assert any("shape o4" in r_["text"] for r_ in cov["reasons"])
    # hand check 5: under the hanging fan (bottom 2.25 m) nothing is blocked by the fan at grip height (cables from the corners
    # pass the fan's height only near the anchors)
    assert "fan" not in at(1.65, 1.35)["text"].lower()
    # before any calibration nothing is "reachable": the rest is "not calibrated"
    assert cov["counts"]["ok"] == 0 and cov["counts"]["trust"] > 0


def test_coverage_is_fast_for_10_shapes_through_the_api(tmp_path):
    r, svc, c, app = _svc(tmp_path)
    rng = np.random.default_rng(4)
    shapes = [_rand_shape(rng) for _ in range(10)]
    for k, s in enumerate(shapes):
        s["id"] = f"t{k}"
    shapes = validate_obstacles(shapes, ROOM)[0]
    assert len(shapes) == 10
    walls, ms = [], []
    for _ in range(7):
        t0 = time.perf_counter()
        pv = c.post("/api/room_map/preview", json={"obstacles": shapes}).get_json()
        walls.append((time.perf_counter() - t0) * 1e3)
        ms.append(pv["coverage"]["ms"])
    _evidence("coverage_timing_10_shapes", {"server_ms_median": float(np.median(ms)), "server_ms_max": float(max(ms)),
                                            "http_roundtrip_ms_median": float(np.median(walls)), "http_ms_max": float(max(walls))})
    assert np.median(ms) < 150 and np.median(walls) < 150, (ms, walls)


# ===================================================================================== 3. planner safety in the simulator
class MotionRecorder:
    """Records every executed plan (with the model geometry and the map in force when it was handed to the stations) and the
    TRUE plant state at every simulated step (with the map in force then)."""

    def __init__(self, r):
        self.r, self.plans, self.true, self.maps = r, [], [], []
        w, ctx = r.world, r.ctx
        step, ex = w.step, r.co.execute

        def map_id():
            ws = ctx.ws
            obs = list(ws.obstacles) if ws is not None else list(ctx.cfg.obstacles)
            key = json.dumps(obs, sort_keys=True)
            if not self.maps or self.maps[-1][0] != key:
                self.maps.append((key, copy.deepcopy(obs), None if ws is None else float(ws.obstacle_margin_m)))
            return len(self.maps) - 1

        def rec_step(t_us, dt_s):
            out = step(t_us, dt_s)
            self.true.append((w.attach_world().copy(), w.p.copy(), w.lowest_z(), map_id()))
            return out

        def execute(plan, *a, **k):
            geo = ctx.model.geometry if ctx.model is not None else None
            self.plans.append({"label": plan.label, "cart": None if plan.cart is None else np.array(plan.cart, float),
                               "geo": geo, "map": map_id(), "lowz": float(ctx.cfg.claw.lowest_point_body_m[2])})
            return ex(plan, *a, **k)
        w.step, r.co.execute = rec_step, execute
        self.anchors_true = w.anchors.copy()

    def planned_clearances(self, step_m=0.005):
        """Per executed Cartesian plan: the minimum clearance (m, < 0 = inside) of every cable and of the claw body to every shape
        inflated by the margin, along the plan densified to ``step_m``. Uses the model geometry the plan was made with."""
        cfg = self.r.cfg
        m, rad = cfg.motion.obstacle_margin_m, cfg.claw.body_radius_m
        rows = []
        for pl in self.plans:
            cart, geo = pl["cart"], pl["geo"]
            shapes = self.maps[pl["map"]][1]
            if cart is None or geo is None or not shapes:
                continue
            pts = [cart[0]]
            for a, b in zip(cart[:-1], cart[1:]):
                n = max(1, int(math.ceil(np.linalg.norm(b - a) / step_m)))
                pts += [a + (b - a) * k / n for k in range(1, n + 1)]
            P = np.array(pts)
            att = np.array([geo.attach_world(p) for p in P])
            for ob in shapes:
                worst = (9.0, "")
                for i in range(len(geo.anchors)):
                    d = float(seg_min_sdf(np.broadcast_to(geo.anchors[i], att[:, i].shape), att[:, i], ob, m).min())
                    worst = min(worst, (d, f"cable {i}"))
                top = np.maximum(att[:, :, 2].max(axis=1), P[:, 2])
                bc = body_clearance(P[:, :2], P[:, 2] + pl["lowz"], top, ob, m, rad)
                worst = min(worst, (float(bc.min()), "body"))
                rows.append({"label": pl["label"], "shape": ob["name"] or ob["id"], "clearance_m": worst[0], "what": worst[1],
                             "n_poses": len(P)})
        return rows

    def true_clearances(self, stride=2):
        """Minimum clearance of the TRUE cables and claw body to every shape of the map in force (no margin, and with it)."""
        cfg = self.r.cfg
        m, rad = cfg.motion.obstacle_margin_m, cfg.claw.body_radius_m
        A = self.anchors_true
        out = {}
        tr = self.true[::stride]
        if not tr:
            return out
        for mid in sorted({t[3] for t in tr}):
            shapes = self.maps[mid][1]
            sel = [t for t in tr if t[3] == mid]
            att = np.array([t[0] for t in sel])
            p = np.array([t[1] for t in sel])
            lz = np.array([t[2] for t in sel])
            for ob in shapes:
                key = ob["name"] or ob["id"]
                for mm, tag in ((0.0, "real"), (m, "inflated")):
                    c = min(float(seg_min_sdf(np.broadcast_to(A[i], att[:, i].shape), att[:, i], ob, mm, n_dense=16, iters=40).min())
                            for i in range(len(A)))
                    b = float(body_clearance(p[:, :2], lz, p[:, 2], ob, mm, rad).min())
                    o = out.setdefault(key, {})
                    o[f"cable_{tag}"] = min(o.get(f"cable_{tag}", 9.0), c)
                    o[f"body_{tag}"] = min(o.get(f"body_{tag}", 9.0), b)
        return out


def _place_near(cfg, rest_xy, template, *, angles, dists, clear_min=0.03, extra_ok=lambda ob: True, avoid=()):
    """The first placement of ``template`` (around the resting claw, angle in degrees, distance of the shape's centre) whose
    inflated shape stays >= ``clear_min`` clear of the straight lift column (prior model, rest to rest + 0.25 m), i.e. a shape put
    as close to the start point as a careful user could without the startup refusing to lift."""
    A = cfg.anchor_priors()
    attach = cfg.attachment_points()
    low = float(cfg.claw.lowest_point_body_m[2])
    m, rad = cfg.motion.obstacle_margin_m, cfg.claw.body_radius_m
    zs = np.arange(-low, -low + 0.25, 0.01)
    for d in dists:
        for ang in angles:
            ob = dict(template, x=float(rest_xy[0] + d * math.cos(math.radians(ang))),
                      y=float(rest_xy[1] + d * math.sin(math.radians(ang))))
            if not (0.05 < ob["x"] < W - 0.05 and 0.05 < ob["y"] < D - 0.05) or not extra_ok(ob):
                continue
            # the lead's rule (round 2): a shape may not cover the claw's landing column (body, floor to the transit height) over
            # the floor marker or the start point; keep 1 cm beyond what the service refuses
            if any(body_clearance(xy, 0.0, cfg.motion.task_max_height_m, ob, m, rad) <= 0.01 for xy in avoid):
                continue
            P = np.c_[np.full(len(zs), rest_xy[0]), np.full(len(zs), rest_xy[1]), zs]
            c = min(float(seg_min_sdf(np.broadcast_to(A[i], (len(zs), 3)), P + attach[i], ob, m).min()) for i in range(len(A)))
            c = min(c, float(body_clearance(P[:, :2], zs + low, zs, ob, m, rad).min()))
            if c >= clear_min:
                return ob
    raise AssertionError(f"no placement for {template['name']}")


def _sim_startup(tmp, cfg, shapes_fn, seed=0):
    """A simulated robot behind the real Service: the map is saved with PUT while DISARMED (as a user would), the startup runs
    through POST /api/command (worker thread). While it runs, PUT must be refused as busy and preview must answer quickly."""
    from roomcleaner.cdpr.sim.world import FloorBoard
    r = SimRobot(cfg, seed=seed, data_dir=tmp, camera_kw={"board": FloorBoard.nominal(0.15)})
    svc = Service(r.ctx, data_dir=tmp)
    c = Client(create_app(svc), svc.token)
    landing = [np.asarray(xy, float) for _w, xy in svc.landing_spots()]
    shapes = shapes_fn(r, landing)
    res = _put(c, {"obstacles": shapes})
    assert res.status_code == 200, res.get_json()
    rec = MotionRecorder(r)
    assert c.post("/api/command", json={"cmd": "start", "checklist": True}).status_code == 200
    busy = {"put": [], "preview_ms": []}
    t0 = time.time()
    while svc.busy and time.time() - t0 < 1500:
        if len(busy["put"]) < 5:
            rp = _put(c, {"obstacles": shapes[:1]})
            busy["put"].append((rp.status_code, rp.get_json().get("error", "")))
            t1 = time.perf_counter()
            pv = c.post("/api/room_map/preview", json={"obstacles": shapes})
            busy["preview_ms"].append((time.perf_counter() - t1) * 1e3)
            assert pv.status_code == 200
            busy.setdefault("coverage_compute_ms", []).append(pv.get_json()["coverage"]["ms"])
        time.sleep(2.0)
    assert not svc.busy, "startup did not finish"
    return r, svc, c, rec, shapes, busy


def _report_motion(name, r, svc, rec, shapes, busy=None):
    rows = rec.planned_clearances()
    tc = rec.true_clearances()
    worst_planned = {}
    for row in rows:
        k = row["shape"]
        if k not in worst_planned or row["clearance_m"] < worst_planned[k]["clearance_m"]:
            worst_planned[k] = row
    detours = [p["label"] for p in rec.plans if "(room map)" in p["label"]]
    skipped = [l for l in r.log_lines if "skipped: the straight move is blocked by the room map" in l]
    ev = {"state": svc.sup.state, "reasons": svc.sup.reasons[-2:] if hasattr(svc.sup, "reasons") else [],
          "shapes": shapes, "plans_executed": len(rec.plans), "cartesian_plans_checked": len({r_["label"] for r_ in rows}),
          "true_steps": len(rec.true), "worst_planned": worst_planned, "true": tc, "detour_legs": detours,
          "skipped_poses": len(skipped), "busy": busy}
    _evidence(name, ev)
    return rows, tc, ev


def _assert_clear(rows, tc):
    inside = [row for row in rows if row["clearance_m"] < -1e-6]
    assert not inside, inside[:5]                                  # no planned pose entered an inflated shape
    for k, o in tc.items():
        assert o["cable_real"] > 0 and o["body_real"] > 0, (k, o)  # the true cables / claw never touched a real shape


THREE_CASES = {   # name: (template, first centre distance from the resting claw)
    "shelf_0.55m": ({"id": "b1", "name": "Shelf", "shape": "box", "length_m": 0.3, "width_m": 0.3, "yaw_deg": 30.0, "z_low_m": 0.0,
                     "height_m": 1.8}, 0.55),
    "pole_0.25m": ({"id": "p1", "name": "Pole", "shape": "cylinder", "diameter_m": 0.05, "z_low_m": 0.0, "height_m": 2.5}, 0.25),
    "shelf_0.33m": ({"id": "b1", "name": "Shelf", "shape": "box", "length_m": 0.3, "width_m": 0.3, "yaw_deg": 30.0, "z_low_m": 0.0,
                     "height_m": 1.8}, 0.33),
}


@pytest.fixture(scope="module", params=list(THREE_CASES))
def three(request, tmp_path_factory):
    """Three-station startup (config/robot.sim3.json, fast profile) with ONE shape placed as close to the resting claw as the
    lift check and the landing-column rule allow (the first angle / distance from the given one whose inflated shape clears the
    straight lift by 3 cm and the landing columns at the marker / start point)."""
    from .test_three_station import fast3
    cfg = fast3()
    tpl, d0 = THREE_CASES[request.param]
    out = _sim_startup(tmp_path_factory.mktemp("rm_three"), cfg,
                       lambda r, landing: [_place_near(cfg, r.world.p[:2], tpl, angles=range(0, 360, 15),
                                                       dists=np.arange(d0, 1.2, 0.02), avoid=landing)])
    return (request.param, *out)


def test_three_station_startup_with_a_shape_near_the_start_point_never_enters_it(three):
    """The safety half (item 3): whatever the outcome of the startup, no planned pose enters the inflated shape and the true
    cables and claw never touch the real one; PUT is refused as busy while it runs."""
    name, r, svc, c, rec, shapes, busy = three
    rows, tc, ev = _report_motion(f"sim3_startup_{name}", r, svc, rec, shapes, busy)
    _evidence(f"sim3_startup_{name}_log", [str(x) for x in r.log_lines if "room map" in str(x) or "FAULT" in str(x)][-6:])
    assert busy["put"] and all(code == 409 and "busy" in err for code, err in busy["put"]), busy
    _assert_clear(rows, tc)


def test_three_station_startup_with_a_shape_near_the_start_reaches_ready_or_names_the_shape(three):
    """Round 1: H-1 (the detour stranded the claw at the top: pole case) and M-5 (an abort that did not name the map: shelf
    0.33 m case). Round 2: the pole and the 0.55 m shelf reach READY; a startup that the map still blocks names the shape and
    says to edit the Map; no detour leg goes above the top less the inset; no move is refused at the top."""
    name, r, svc, c, rec, shapes, busy = three
    if name in ("shelf_0.55m", "pole_0.25m"):
        assert svc.sup.state == "READY", svc.sup.reasons[-2:]
        assert [row for row in rec.planned_clearances()], "no Cartesian plan was checked against the map"
    else:
        last = " ".join(svc.sup.reasons[-1:])
        assert svc.sup.state == "READY" or (shapes[0]["name"] in last and "Map" in last), svc.sup.reasons[-1:]
    inset = float(r.cfg.motion.waypoint_inset_m)
    tops = [float(np.max(p["cart"][:, 2])) for p in rec.plans if p["cart"] is not None and "(room map)" in p["label"]]
    _evidence(f"sim3_startup_{name}_detour_apex", {"legs": len(tops), "max_z": max(tops, default=None),
                                                   "limit": float(r.ctx.ws.hi[2]) - inset})
    assert all(z <= float(r.ctx.ws.hi[2]) - inset + 1e-6 for z in tops), tops
    assert not any("workspace: z=" in str(x) and "above" in str(x) for x in r.log_lines), "a move was refused at the top"


def test_the_landing_spot_search_stays_inside_the_triangle_and_the_box(three):
    """Round 2 regression probe: ``Supervisor._landing_spot`` with a pole over the marker and a crate on the start point (not
    saveable through PUT, so set on the live workspace directly) must pick a spot that is clear of every shape, inside the
    workspace box AND the three-station triangle (with its tension margin), never merely 'clear by the map'; or refuse, naming
    a shape."""
    name, r, svc, c, rec, shapes, busy = three
    if svc.sup.state != "READY":
        pytest.skip(f"not READY ({svc.sup.state})")
    from roomcleaner.cdpr.perception import to_room
    from roomcleaner.cdpr.supervisor import CommandRefused
    ctx = r.ctx
    ws = ctx.ws
    mk = np.asarray(to_room(ctx.T_R_M, [0, 0, 0])[:2], float)
    zf = -float(r.cfg.claw.lowest_point_body_m[2])
    h = max(float(_claw(svc)[2]), zf + 0.30)
    pole = {"id": "z1", "name": "Pole", "shape": "cylinder", "x": float(mk[0]), "y": float(mk[1]), "diameter_m": 0.05, "z_low_m": 0.0,
            "height_m": 2.2}
    sx, sy = r.cfg.start_point_xy()
    big = {"id": "z2", "name": "Crate", "shape": "box", "x": float(sx), "y": float(sy), "length_m": 0.5, "width_m": 0.5, "yaw_deg": 0.0,
           "z_low_m": 0.0, "height_m": 0.5}
    saved = list(ws.obstacles)
    out = {}
    try:
        ws.obstacles = saved + [pole, big]
        try:
            xy = svc.sup._landing_spot(ctx.co.positions(), mk, h, zf)
        except CommandRefused as e:
            out["refused"] = str(e)
            assert "Pole" in str(e) or "Crate" in str(e), str(e)
        else:
            out["spot"] = xy.tolist()
            assert np.all(xy >= ws.lo[:2] - 1e-9) and np.all(xy <= ws.hi[:2] + 1e-9), xy
            assert ws.triangle_violation(np.r_[xy, zf + 0.05]) is None, ws.triangle_violation(np.r_[xy, zf + 0.05])
            for ob in ws.obstacles:
                assert body_clearance(xy, 0.0, h, ob, r.cfg.motion.obstacle_margin_m, r.cfg.claw.body_radius_m) > 0, (ob["name"], xy)
            out["distance_from_marker_m"] = float(np.linalg.norm(xy - mk))
    finally:
        ws.obstacles = saved
    _evidence(f"sim3_landing_spot_{name}", out)


def test_after_the_detours_up_leg_the_next_move_can_be_planned():
    """Round 1 finding H-1 (fixed in round 2): a pose within a microstep of the workspace top can start a move."""
    import itertools
    from roomcleaner.cdpr.trajectory import PlanError, limits_from_config, model_from, plan_line_from
    cfg, geo, ws = _cfg_ws([])
    model = model_from(geo, cfg, {s.id: 3.0 for s in cfg.stations})
    lim = limits_from_config(cfg)
    top = float(ws.hi[2])
    P_top = np.round(model.positions_for(np.array([1.5, 1.2, top])))
    bad = []
    for d in itertools.product([-1, 0, 1], repeat=4):
        try:
            plan_line_from(model, P_top + np.array(d), np.array([2.0, 1.2, 1.0]), lim, ws=ws, label="next")
        except PlanError as e:
            bad.append(str(e))
    _evidence("h1_top_refusals", {"refused": len(bad), "of": 81, "example": bad[:1]})
    assert not bad, (len(bad), bad[:1])


def test_the_1_mm_bound_snap_hides_no_real_out_of_workspace_pose():
    """Round 2 regression probe for the H-1 fix (trajectory.START_BOUND_TOL_M): a start pose up to 1 mm outside the box is put on
    the bound (the offset is faded out), 1.1 mm and more is still refused, the tension and three-station triangle checks still
    apply at a bound, a target outside is never clamped."""
    from roomcleaner.cdpr.trajectory import START_BOUND_TOL_M, PlanError, limits_from_config, model_from, plan_line_from
    assert START_BOUND_TOL_M <= 0.001
    out = {}
    for path in (SIM, SIM3):
        cfg, geo, ws = _cfg_ws([], path)
        model = model_from(geo, cfg, {s.id: 3.0 for s in cfg.stations})
        lim = limits_from_config(cfg)
        c = cfg.start_point_xy()
        top = float(ws.hi[2])
        for dz, ok in ((0.0009, True), (0.0011, False), (0.005, False), (0.05, False)):
            P = model.positions_for(np.array([c[0], c[1], top + dz]))
            try:
                pl = plan_line_from(model, P, np.array([c[0] + 0.3, c[1], 1.0]), lim, ws=ws, label="x")
                assert ok, (path, dz)
                assert abs(float(pl.cart[0][2]) - top) < 1e-9 and np.max(np.abs(pl.meta["start_offset_usteps"])) < 200
            except PlanError as e:
                assert not ok and "above" in str(e), (path, dz, e)
            out[f"{Path(path).name} +{dz * 1e3:.1f} mm"] = "planned" if ok else "refused"
        zlo = float(ws.lo[2])
        P = model.positions_for(np.array([c[0], c[1], zlo - 0.0009]))
        plan_line_from(model, P, np.array([c[0] + 0.3, c[1], 1.0]), lim, ws=ws, label="x")
        with pytest.raises(PlanError):                                                  # a target outside is never clamped
            plan_line_from(model, P, np.array([c[0] + 0.3, c[1], zlo - 0.0009]), lim, ws=ws, label="x")
        P = model.positions_for(np.array([ws.hi[0] + 0.0009, c[1], 1.0]))             # at a side bound: still infeasible there
        with pytest.raises(PlanError):
            plan_line_from(model, P, np.array([c[0], c[1], 1.0]), lim, ws=ws, label="x")
    _evidence("bound_snap", out)


def test_the_detour_apex_is_inset_from_the_top_and_is_the_lowest_that_clears_the_shape():
    """Round 2: ``StartupSequencer._detour_height`` on a dry context: the apex is at most ws.hi[z] - waypoint_inset_m, every leg
    plans, the height is the lowest 0.1 m step that clears a shelf between two poses, and a shelf up to the ceiling gives
    (None, reason)."""
    from types import SimpleNamespace
    from roomcleaner.cdpr.startup import StartupSequencer
    from roomcleaner.cdpr.trajectory import PlanError, limits_from_config, model_from, plan_line
    shelf = {"id": "s", "name": "Shelf", "shape": "box", "x": 1.68, "y": 1.37, "length_m": 0.3, "width_m": 0.3, "yaw_deg": 0.0,
             "z_low_m": 0.0, "height_m": 1.2}
    cfg, geo, ws = _cfg_ws([shelf])
    model = model_from(geo, cfg, {s.id: 3.0 for s in cfg.stations})
    lim = limits_from_config(cfg)
    seq = StartupSequencer.__new__(StartupSequencer)
    seq.ctx = SimpleNamespace(ws=ws, model=model, lim=lim)
    seq.cfg = cfg
    here = q = None
    for dx in np.arange(0.5, 1.3, 0.05):                            # two valid poses whose straight line the shelf blocks
        a, b = np.array([1.68 - dx, 1.37, 0.8]), np.array([1.68 + dx, 1.37, 0.8])
        if ws.violations(geo, a) or ws.violations(geo, b):
            continue
        try:
            plan_line(model, a, b, lim, ws=ws)
        except PlanError as e:
            if "Shelf" in str(e):
                here, q = a, b
                break
    assert here is not None, "no pair of valid poses with the shelf between them"
    z, err = seq._detour_height(here, q)
    assert err is None and z is not None
    limit = float(ws.hi[2]) - float(cfg.motion.waypoint_inset_m)
    assert z <= limit + 1e-9
    for p0, p1 in ((here, np.r_[here[:2], z]), (np.r_[here[:2], z], np.r_[q[:2], z]), (np.r_[q[:2], z], q)):
        plan_line(model, p0, p1, lim, ws=ws)
    with pytest.raises(PlanError):                                   # one 0.1 m step lower does not clear it
        plan_line(model, np.r_[here[:2], z - 0.1], np.r_[q[:2], z - 0.1], lim, ws=ws)
    ws.obstacles = [dict(shelf, height_m=2.7)]
    z2, err2 = seq._detour_height(here, q)
    assert z2 is None and err2
    _evidence("detour_apex", {"z": z, "limit": limit, "blocked_reason": err2})


# ----------------------------------------------------------------------------------------------- four stations: startup, state rules,
# a task next to shapes, and the lowering
@pytest.fixture(scope="module")
def four(tmp_path_factory):
    cfg = fast_cfg()

    def shapes(r, landing):     # saved while DISARMED: a dresser against the A-D wall and a floor lamp in the D corner (outside the
        # calibration poses, so the startup is not blocked: H-1 / M-5); more shapes are saved in READY by the tests below
        return [{"id": "b1", "name": "Dresser", "shape": "box", "x": 0.25, "y": 1.37, "length_m": 0.46, "width_m": 1.2,
                 "yaw_deg": 0.0, "z_low_m": 0.0, "height_m": 0.9},
                {"id": "p1", "name": "Pole", "shape": "cylinder", "x": 0.45, "y": 2.35, "diameter_m": 0.05, "z_low_m": 0.0,
                 "height_m": 1.7}]
    return _sim_startup(tmp_path_factory.mktemp("rm_four"), cfg, shapes)


def _claw(svc):
    return svc.ctx.model.pose_from_positions(svc.ctx.co.positions())[0]


def test_four_station_startup_with_shapes_saved_reaches_ready_without_entering_them(four):
    r, svc, c, rec, shapes, busy = four
    rows, tc, ev = _report_motion("sim4_startup", r, svc, rec, shapes, busy)
    assert all(code == 409 and "busy" in err for code, err in busy["put"]) and busy["put"], busy
    _evidence("preview_while_busy_sim4", busy)
    _assert_clear(rows, tc)
    assert svc.sup.state == "READY", svc.sup.reasons[-2:]
    assert rows


def test_put_in_ready_and_paused_follows_the_pose_rules(four):
    r, svc, c, rec, shapes, busy = four
    assert svc.sup.state == "READY"
    p = _claw(svc)
    low = float(r.cfg.claw.lowest_point_body_m[2])
    out = {}
    # (a) the margin alone reaches the claw: a cabinet whose side is 0.15 m from the claw axis (< 0.10 + 0.07), at its height
    side = dict(shapes[0], id="x1", name="Cabinet", x=float(p[0] + 0.15 + 0.2), y=float(p[1]), length_m=0.4, width_m=0.4, yaw_deg=0.0,
                height_m=2.3)
    # (b) a hanging lamp whose bottom is 5 cm above the attachment plane (inside the 0.10 m margin)
    hang = {"id": "x2", "name": "Lamp", "shape": "cylinder", "x": float(p[0]), "y": float(p[1]), "diameter_m": 0.3,
            "z_low_m": float(p[2] + 0.05), "height_m": float(min(p[2] + 0.5, 2.74))}
    # (c) a low table under the claw, its top 0.11 m below the claw's lowest point (pose fine, lowering not)
    under = {"id": "x3", "name": "Table", "shape": "box", "x": float(p[0]), "y": float(p[1]), "length_m": 0.6, "width_m": 0.6,
             "yaw_deg": 45.0, "z_low_m": 0.0, "height_m": float(p[2] + low - 0.11)}
    # (d) a chair far from the claw
    far = {"id": "x4", "name": "Chair", "shape": "box", "x": float(np.clip(p[0] + 1.1, 0.3, W - 0.3)),
           "y": float(np.clip(p[1] - 0.9, 0.3, D - 0.3)), "length_m": 0.4, "width_m": 0.4, "yaw_deg": 0.0, "z_low_m": 0.0, "height_m": 0.9}
    assert under["height_m"] > 0.05, p
    for st in ("READY", "PAUSED"):
        if st == "PAUSED":
            svc.sup.pause("verifier")
            assert svc.sup.state == "PAUSED"
        for name, ob, ok in (("side", side, False), ("hang", hang, False), ("under", under, False), ("far", far, True)):
            res = _put(c, {"obstacles": shapes + [ob]})
            out[f"{st}_{name}"] = (res.status_code, res.get_json().get("error", res.get_json().get("text")))
            assert (res.status_code == 200) == ok, (st, name, res.get_json())
            if not ok:
                assert ob["name"] in res.get_json()["error"], res.get_json()
            if ok:
                assert svc.ctx.ws.obstacles[-1]["name"] == "Chair" and svc.ctx.cfg.obstacles[-1]["name"] == "Chair"
                # the live planner uses it at once: a straight line through the chair is refused
                from roomcleaner.cdpr.trajectory import PlanError, plan_line
                with pytest.raises(PlanError, match="Chair"):
                    plan_line(svc.ctx.model, np.r_[far["x"] - 0.6, far["y"], 0.75], np.r_[far["x"] + 0.6, far["y"], 0.75],
                              svc.ctx.lim, ws=svc.ctx.ws)
                assert _put(c, {"obstacles": shapes}).status_code == 200
    _evidence("put_state_rules", out)
    # back to READY for the task
    svc.sup.ctx.co.pause_requested = None
    svc.sup.resume()
    assert svc.sup.state == "READY", svc.sup.reasons[-2:]


def test_a_task_next_to_shapes_never_plans_into_them(four):
    """Two reachable items; a 5 cm pole is then saved 0.12 m from the first one (the claw cannot grip there: it would enter the
    pole's margin) and a low ottoman between the claw and the second item. Every planned move of the task is checked."""
    from roomcleaner.cdpr.tasks import TaskRunner
    from .simkit import ModelFrameItemPerception, item_offsets_with_small_statics_tilt
    r, svc, c, rec, shapes, busy = four
    assert svc.sup.state == "READY"
    r.world.hamper = (np.asarray(r.cfg.tasks.hamper_room_m), r.cfg.tasks.hamper_radius_m)
    here = _claw(svc)
    try:
        offs = item_offsets_with_small_statics_tilt(r.ctx, None, n=2)
    except AssertionError as e:
        pytest.skip(f"no two servable items from here: {e}")
    items = [here[:2] + o for o in offs]
    # PUT refuses a map that the claw's CURRENT pose or its straight lowering would break (correctly): try placements until one
    # is accepted (a refused PUT saves nothing)
    placed = None
    for ang in range(0, 360, 30):
        pole = {"id": "t1", "name": "Floor lamp", "shape": "cylinder", "x": float(items[0][0] + 0.12 * math.cos(math.radians(ang))),
                "y": float(items[0][1] + 0.12 * math.sin(math.radians(ang))), "diameter_m": 0.05, "z_low_m": 0.0, "height_m": 1.0}
        for frac in (0.5, 0.65, 0.35):
            mid = here[:2] + frac * (items[1] - here[:2])
            ott = {"id": "t2", "name": "Ottoman", "shape": "box", "x": float(mid[0]), "y": float(mid[1]), "length_m": 0.3,
                   "width_m": 0.3, "yaw_deg": 0.0, "z_low_m": 0.0, "height_m": 0.35}
            if _put(c, {"obstacles": shapes + [pole, ott]}).status_code == 200:
                placed = (pole, ott)
                break
        if placed:
            break
        if _put(c, {"obstacles": shapes + [pole]}).status_code == 200:
            placed = (pole,)
            break
    if placed is None:
        pytest.skip("no accepted placement of the floor lamp next to the first item from this claw pose")
    for k, xy in enumerate(items):
        r.world.add_item(f"item{k}", xy)
    runner = TaskRunner(r.ctx, ModelFrameItemPerception(r.world))
    runner.tc = replace(r.cfg.tasks, max_payload_kg=0.6)
    n0 = len(rec.plans)
    out = svc.sup.run_task(runner)
    task_plans = rec.plans[n0:]
    _evidence("sim4_task", {"result": out, "state": svc.sup.state, "placed": placed, "plans": [p["label"] for p in task_plans],
                            "items": [it["state"] for it in r.world.items]})
    assert out is not None, svc.sup.reasons[-2:]
    failed = dict((f[0], f[1]) for f in out.get("failed", []))
    assert "item0" in failed and "Floor lamp" in failed["item0"], out           # refused BEFORE any move towards it, with the reason
    assert not [p for p in task_plans if "item0" in p["label"]]
    rows = [row for row in rec.planned_clearances() if row["label"] in {p["label"] for p in task_plans}]
    assert rows and not [row for row in rows if row["clearance_m"] < -1e-6], rows
    # second run: the lamp removed, a low ottoman 0.30 m beside the first item instead (grip allowed: 0.15 + 0.10 + 0.07 < 0.30);
    # the items are now picked and carried past it
    second = None
    away = items[0] - np.asarray(r.cfg.tasks.hamper_room_m, float)            # the carry goes toward the hamper: put it behind
    a0 = math.degrees(math.atan2(away[1], away[0]))
    for ang in sorted(range(0, 360, 15), key=lambda a: -math.cos(math.radians(a - a0))):
        ott = {"id": "t3", "name": "Ottoman", "shape": "box", "x": float(items[0][0] + 0.45 * math.cos(math.radians(ang))),
               "y": float(items[0][1] + 0.45 * math.sin(math.radians(ang))), "length_m": 0.3, "width_m": 0.3, "yaw_deg": 0.0,
               "z_low_m": 0.0, "height_m": 0.4}
        if footprint_dist(items[1], ott) < 0.35:
            continue
        if _put(c, {"obstacles": shapes + [ott]}).status_code == 200:
            second = ott
            break
    if second is None:
        pytest.skip("no accepted ottoman placement")
    runner = TaskRunner(r.ctx, ModelFrameItemPerception(r.world))
    runner.tc = replace(r.cfg.tasks, max_payload_kg=0.6)
    n1 = len(rec.plans)
    out2 = svc.sup.run_task(runner)
    plans2 = rec.plans[n1:]
    rows2 = [row for row in rec.planned_clearances() if row["label"] in {p["label"] for p in plans2}]
    _evidence("sim4_task_2", {"result": out2, "state": svc.sup.state, "ottoman": second, "plans": [p["label"] for p in plans2],
                              "items": [it["state"] for it in r.world.items],
                              "worst_planned_m": min((row["clearance_m"] for row in rows2), default=None)})
    assert rows2 and not [row for row in rows2 if row["clearance_m"] < -1e-6], rows2
    # and the true claw / cables never touched any real shape during both tasks
    _assert_clear([], rec.true_clearances())


def test_put_refuses_a_shape_over_the_landing_column_in_every_state(tmp_path):
    """The lead's rule (round 2): a shape covering the claw body's landing column (floor up to the transit height) over the floor
    marker or the start point is refused at save, in DISARMED and PARKED too, naming the shape; a shape beside the column, and a
    hanging shape above the transit height, are accepted."""
    r, svc, c, app = _svc(tmp_path)
    spots = svc.landing_spots()
    assert spots
    what, xy = spots[0]
    m, rad = r.cfg.motion.obstacle_margin_m, r.cfg.claw.body_radius_m
    over = {"id": "l1", "name": "Ottoman", "shape": "box", "x": float(xy[0]), "y": float(xy[1]), "length_m": 0.4, "width_m": 0.4,
            "yaw_deg": 0.0, "z_low_m": 0.0, "height_m": 0.3}
    edge = dict(over, name="Stool", x=float(xy[0] + 0.2 + m + rad - 0.005))             # 5 mm inside the inflated column
    beside = dict(over, name="Chair", x=float(xy[0] + 0.2 + m + rad + 0.01))            # 1 cm outside it
    fan = {"id": "l2", "name": "Ceiling fan", "shape": "cylinder", "x": float(xy[0]), "y": float(xy[1]), "diameter_m": 1.0,
           "z_low_m": float(r.cfg.motion.task_max_height_m + m + 0.02), "height_m": 2.74}
    out = {}
    for st in ("DISARMED", "PARKED"):
        svc.sup.state = st
        for ob, ok in ((over, False), (edge, False), (beside, True), (fan, True)):
            res = _put(c, {"obstacles": [ob]})
            out[f"{st}_{ob['name']}"] = (res.status_code, res.get_json().get("error", res.get_json().get("text")))
            assert (res.status_code == 200) == ok, (st, ob["name"], res.get_json())
            if not ok:
                err = res.get_json()["error"]
                assert ob["name"] in err and "landing spot" in err, err
                assert svc.ctx.cfg.obstacles == [] or svc.ctx.cfg.obstacles[0]["name"] != ob["name"]
    assert _put(c, {"obstacles": []}).status_code == 200
    _evidence("landing_rule_put", out)


def test_lowering_with_a_shape_near_the_landing_column_lands_clear_or_refuses_holding(four):
    """Round 1 finding H-2, reworked for the lead's rule. (1) A box over the marker is refused at save in READY, naming it.
    (2) A tall thin pole NEXT to the landing column (accepted at save: the body column is clear) in the direction of an anchor,
    so that the planned descent over the marker is refused by a cable: lowering must land on a clear spot (inside the box) or
    refuse while holding; the true claw body is never inside a shape; no cable-packet fallback through the map."""
    r, svc, c, rec, shapes, busy = four
    if svc.sup.state != "READY":
        pytest.skip(f"not READY ({svc.sup.state})")
    assert _put(c, {"obstacles": shapes}).status_code == 200          # the task test's extra shapes are removed first
    ctx = r.ctx
    from roomcleaner.cdpr.perception import to_room
    from roomcleaner.cdpr.supervisor import CommandRefused
    from roomcleaner.cdpr.trajectory import PlanError, plan_line, plan_line_from
    mk = np.asarray(to_room(ctx.T_R_M, [0, 0, 0])[:2], float)
    m, rad = r.cfg.motion.obstacle_margin_m, r.cfg.claw.body_radius_m
    zf = -float(r.cfg.claw.lowest_point_body_m[2])
    # the claw high, beside the marker (so that the READY pose check does not fire first)
    tgt = np.r_[mk[0] + 0.45 * np.sign(1.6 - mk[0] + 1e-9), mk[1], 1.25]
    assert ctx.co.execute(plan_line_from(ctx.model, ctx.co.positions(), tgt, ctx.lim, ws=ctx.ws, label="verifier: up")).ok
    # (1) over the marker: refused at save, in READY, by the landing rule
    box = {"id": "l1", "name": "Ottoman", "shape": "box", "x": float(mk[0]), "y": float(mk[1]), "length_m": 0.5, "width_m": 0.5,
           "yaw_deg": 0.0, "z_low_m": 0.0, "height_m": 0.30}
    res = _put(c, {"obstacles": shapes + [box]})
    assert res.status_code == 409 and "Ottoman" in res.get_json()["error"] and "landing" in res.get_json()["error"], res.get_json()
    _evidence("sim4_landing_put_ready", res.get_json())
    # (2) a 5 cm pole just outside the inflated landing column, towards anchor A (so cable A crosses it low over the marker)
    A = ctx.model.geometry.anchors[0]
    d = (A[:2] - mk) / np.linalg.norm(A[:2] - mk)
    pole = None
    for dist in np.arange(0.025 + m + rad + 0.01, 0.45, 0.01):
        cand = {"id": "l3", "name": "Floor lamp", "shape": "cylinder", "x": float(mk[0] + dist * d[0]), "y": float(mk[1] + dist * d[1]),
                "diameter_m": 0.05, "z_low_m": 0.0, "height_m": 2.3}
        res = _put(c, {"obstacles": shapes + [cand]})
        if res.status_code == 200:
            pole = cand
            break
    assert pole is not None, res.get_json()
    with pytest.raises(PlanError, match="Floor lamp"):                # the descent over the marker is indeed refused by the map
        plan_line(ctx.model, np.r_[mk, 1.25], np.r_[mk, zf + 0.05], ctx.lim, ws=ctx.ws, allow_low=True)
    n0, t0 = len(rec.plans), len(rec.true)
    refusal = None
    try:
        svc.sup.lower()
    except CommandRefused as e:
        refusal = str(e)
    labels = [p_["label"] for p_ in rec.plans[n0:]]
    log = [str(x) for x in r.log_lines[-40:] if "lower" in str(x)]
    worst = 9.0
    for att, pp, lz, mid in rec.true[t0:]:
        for ob in ctx.ws.obstacles:
            worst = min(worst, float(body_clearance(pp[:2], lz, pp[2], ob, 0.0, rad)))
    end = r.world.p.copy()
    _evidence("sim4_lower", {"state": svc.sup.state, "refusal": refusal, "labels": labels[:4] + ["..."] + labels[-3:],
                             "n_packets": sum("lower packet" in l for l in labels), "log": log[-4:],
                             "true_body_clearance_to_real_shapes_m": worst, "claw_end": end.tolist(), "marker": mk.tolist(),
                             "claw_lowest_end_m": r.world.lowest_z(), "pole": pole})
    assert worst > 0, f"the claw body went {-worst:.3f} m into a shape while lowering"
    assert not any("using cable packets" in l for l in log), log
    if refusal is None:
        assert svc.sup.state == "PARKED" and r.world.lowest_z() < 0.02, (svc.sup.state, r.world.lowest_z())
        assert any("lowering at (" in l for l in log), log          # it did land elsewhere, and said so
        assert np.all(end[:2] >= ctx.ws.lo[:2] - 1e-6) and np.all(end[:2] <= ctx.ws.hi[:2] + 1e-6), end
        for ob in ctx.ws.obstacles:
            assert body_clearance(end[:2], 0.0, 1.0, ob, m, rad) > 0, ob["name"]
    else:
        assert "Floor lamp" in refusal and svc.sup.state == "READY", (refusal, svc.sup.state)
        assert sum("lower packet" in l for l in labels) == 0
