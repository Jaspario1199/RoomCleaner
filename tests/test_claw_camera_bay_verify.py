"""
INDEPENDENT verification of the claw camera bay (commit 7f63e95).

Written by the geometry-verifier, who did NOT build the part.  Nothing here is
imported from tests/test_claw_camera_bay.py and no helper from cad/mesh_tools.py
is used: ray casting, ray-parity probing, thickness probing and the occupancy
grid are re-implemented below.  What is measured is the SHIPPED export
(exports/step/*.step, exports/stl/*.stl), not the module output, so a stale
export would be caught (see test_exports_not_stale for the regeneration check).

Frames: "bay frame" = v6 world translated by -BAY_ORIGIN (origin on the tube
axis in the box bottom plane, +Y up).  r = -z = radial distance outward on the
-Z (narrow) side.

Tests that document a verifier finding are marked xfail(strict=True) with the
finding id (F1..).  They are expected to FAIL until the design is changed; when
the defect is fixed they XPASS and strict mode flags it so the mark is removed.

Report: verification/claw_camera_bay_verification.md
Run   : /usr/bin/python3 -m pytest tests/test_claw_camera_bay_verify.py -q
"""

from __future__ import annotations

import math
import os
import struct
import subprocess
import sys

import numpy as np
import pytest

cq = pytest.importorskip("cadquery")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from OCP.BRepAdaptor import BRepAdaptor_Surface                 # noqa: E402
from OCP.GeomAbs import GeomAbs_Cylinder                        # noqa: E402
from OCP.BRepExtrema import BRepExtrema_DistShapeShape          # noqa: E402

from cad import params as P                                      # noqa: E402
from cad.v6_loader import V6_STEP, load_v6, find, BOX_NAME       # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.exists(V6_STEP), reason="v6 STEP not available")

STEP = os.path.join(REPO, "exports", "step")
STL = os.path.join(REPO, "exports", "stl")
OX, OY, OZ = 951.8475, 1091.1905, 1103.9899      # bay origin in v6 world (tube axis @ box bottom)
OFF = np.array([OX, OY, OZ])
PETG = 1.27e-3                                    # g/mm3


# --------------------------------------------------------------------------- helpers
def Bx(x0, x1, y0, y1, r0, r1):
    """Axis-aligned box given in bay-frame (x, y, r) -> world solid."""
    return (cq.Workplane().box(x1 - x0, y1 - y0, r1 - r0, centered=False)
            .translate((OX + x0, OY + y0, OZ - r1)).val())


def vol_int(a, b):
    return a.intersect(b).Volume()


def tess(shape, tol=0.03, ang=0.2):
    v, t = shape.tessellate(tol, ang)
    return np.array([[p.x, p.y, p.z] for p in v]), np.array(t).reshape(-1, 3)


def cross_coords(V, F, axis, pts2):
    """Ray-parity crossings: for each (a, b) in pts2 (the two remaining axes, in
    order) return the sorted coordinates where the line parallel to `axis`
    crosses the mesh."""
    o = [i for i in range(3) if i != axis]
    tri = V[F]
    a, b, c = tri[:, :, o[0]], tri[:, :, o[1]], tri[:, :, axis]
    x0, y0, x1, y1, x2, y2 = a[:, 0], b[:, 0], a[:, 1], b[:, 1], a[:, 2], b[:, 2]
    den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    ok = np.abs(den) > 1e-14
    mnx, mxx = np.minimum(np.minimum(x0, x1), x2), np.maximum(np.maximum(x0, x1), x2)
    mny, mxy = np.minimum(np.minimum(y0, y1), y2), np.maximum(np.maximum(y0, y1), y2)
    out = []
    for px, py in pts2:
        idx = np.where(ok & (mnx <= px) & (mxx >= px) & (mny <= py) & (mxy >= py))[0]
        if len(idx) == 0:
            out.append(np.array([]))
            continue
        d = den[idx]
        l0 = ((y1[idx] - y2[idx]) * (px - x2[idx]) + (x2[idx] - x1[idx]) * (py - y2[idx])) / d
        l1 = ((y2[idx] - y0[idx]) * (px - x2[idx]) + (x0[idx] - x2[idx]) * (py - y2[idx])) / d
        l2 = 1 - l0 - l1
        h = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
        idx = idx[h]
        z = l0[h] * c[idx, 0] + l1[h] * c[idx, 1] + l2[h] * c[idx, 2]
        out.append(np.sort(z))
    return out


def mt_first_hit(o, D, V, F, chunk=3000):
    """Moller-Trumbore first hit (t>1e-6) of rays from single origin o along D (n,3)."""
    o = np.asarray(o, float)
    tri = V[F]
    v0, e1, e2 = tri[:, 0], tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    lo, hi = V.min(0), V.max(0)
    best = np.full(len(D), np.inf)
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = 1 / D
        t1, t2 = (lo - o) * inv, (hi - o) * inv
    tmn, tmx = np.nanmax(np.minimum(t1, t2), 1), np.nanmin(np.maximum(t1, t2), 1)
    cand = np.where(tmx >= np.maximum(tmn, 0))[0]
    for k in range(0, len(cand), 100):
        idx = cand[k:k + 100]
        d = D[idx]
        bt = np.full(len(idx), np.inf)
        for s in range(0, len(F), chunk):
            a, b1, b2 = v0[s:s + chunk], e1[s:s + chunk], e2[s:s + chunk]
            pv = np.cross(d[:, None, :], b2[None])
            det = np.einsum("mj,rmj->rm", b1, pv)
            ok = np.abs(det) > 1e-12
            invd = np.where(ok, 1 / np.where(ok, det, 1), 0)
            tv = o[None, None, :] - a[None]
            u = np.einsum("rmj,rmj->rm", np.broadcast_to(tv, pv.shape), pv) * invd
            qv = np.cross(np.broadcast_to(tv, pv.shape), b1[None])
            v = np.einsum("rj,rmj->rm", d, qv) * invd
            t = np.einsum("mj,rmj->rm", b2, qv) * invd
            hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-6)
            bt = np.minimum(bt, np.where(hit, t, np.inf).min(1))
        best[idx] = bt
    return best


def inward_thickness(V, F, mask_fn, minarea=0.05):
    """Local wall thickness: ray from each facet centroid along the inward normal
    to the next surface.  Returns (centroids, thickness) for facets passing mask."""
    tri = V[F]
    c = tri.mean(1)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = 0.5 * np.linalg.norm(n, axis=1)
    n = n / np.linalg.norm(n, axis=1)[:, None]
    sel = np.where(mask_fn(c) & (area > minarea))[0]
    v0, e1, e2 = tri[:, 0], tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    out = np.full(len(sel), np.inf)
    for k0 in range(0, len(sel), 50):
        idx = sel[k0:k0 + 50]
        o, d = c[idx] - n[idx] * 1e-3, -n[idx]
        bt = np.full(len(idx), np.inf)
        for s in range(0, len(F), 3000):
            A, B1, B2 = v0[s:s + 3000], e1[s:s + 3000], e2[s:s + 3000]
            pv = np.cross(d[:, None, :], B2[None])
            det = np.einsum("mj,rmj->rm", B1, pv)
            ok = np.abs(det) > 1e-12
            invd = np.where(ok, 1 / np.where(ok, det, 1), 0)
            tv = o[:, None, :] - A[None]
            u = np.einsum("rmj,rmj->rm", tv, pv) * invd
            qv = np.cross(tv, B1[None])
            v = np.einsum("rj,rmj->rm", d, qv) * invd
            t = np.einsum("mj,rmj->rm", B2, qv) * invd
            hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-6)
            bt = np.minimum(bt, np.where(hit, t, np.inf).min(1))
        out[k0:k0 + 50] = bt
    return c[sel], out


def load_stl(path):
    b = open(path, "rb").read()
    n = struct.unpack("<I", b[80:84])[0]
    d = np.frombuffer(b[84:], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=n)
    return d["v"].reshape(-1, 3, 3).astype(float)


def hole_faces(shape, radius=0.75):
    out = []
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Cylinder and abs(a.Cylinder().Radius() - radius) < 1e-3:
            out.append(f)
    return out


def hole_key(f):
    loc = BRepAdaptor_Surface(f.wrapped).Cylinder().Axis().Location()
    return (1 if loc.X() > OX else -1, 1 if loc.Z() > OZ else -1)


def dist(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value()


# --------------------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def v6():
    return load_v6()


@pytest.fixture(scope="module")
def box(v6):
    return find(v6, BOX_NAME)


@pytest.fixture(scope="module")
def comb():
    return cq.importers.importStep(os.path.join(STEP, "gripper_electric_housing_with_camera_bay.step")).val()


@pytest.fixture(scope="module")
def body():
    return cq.importers.importStep(os.path.join(STEP, "claw_camera_bay_body.step")).val()


@pytest.fixture(scope="module")
def cover():
    return cq.importers.importStep(os.path.join(STEP, "claw_camera_bay_cover.step")).val()


@pytest.fixture(scope="module")
def diff(box, comb):
    """(removed, added) = (box - comb, comb - box)."""
    return box.cut(comb), comb.cut(box)


@pytest.fixture(scope="module")
def mesh_comb(comb):
    V, F = tess(comb, 0.005, 0.05)
    return V - OFF, F


@pytest.fixture(scope="module")
def mesh_cover(cover):
    V, F = tess(cover, 0.005, 0.05)
    return V - OFF, F


def _along(mesh, axis, a, b):
    V, F = mesh
    return cross_coords(V, F, axis, [(a + 1e-5, b + 2e-5)])[0]


# --------------------------------------------------------------------------- 1. validity / exports
def test_v6_step_unchanged_vs_git_head():
    rel = os.path.relpath(V6_STEP, REPO)
    head = subprocess.run(["git", "-C", REPO, "rev-parse", f"HEAD:{rel}"], capture_output=True, text=True)
    cur = subprocess.run(["git", "-C", REPO, "hash-object", V6_STEP], capture_output=True, text=True)
    if head.returncode != 0:
        pytest.skip("git HEAD blob not available")
    assert head.stdout.strip() == cur.stdout.strip(), "v6 STEP differs from git HEAD"


@pytest.mark.parametrize("name,expect_vol", [
    ("gripper_electric_housing_with_camera_bay", 403721.1),
    ("claw_camera_bay_body", 14457.8),
    ("claw_camera_bay_cover", 3323.3)])
def test_exports_valid_single_solid(name, expect_vol):
    s = cq.importers.importStep(os.path.join(STEP, name + ".step")).val()
    assert s.isValid()
    assert len(s.Solids()) == 1 and len(s.Shells()) == 1
    assert s.Volume() > 0
    assert s.Volume() == pytest.approx(expect_vol, rel=2e-4)


def test_step_roundtrip(comb, cover, body, tmp_path):
    for nm, s in (("comb", comb), ("cover", cover), ("body", body)):
        p = str(tmp_path / (nm + ".step"))
        cq.exporters.export(cq.Workplane().add(s), p)
        r = cq.importers.importStep(p).val()
        b0, b1 = s.BoundingBox(), r.BoundingBox()
        assert abs(r.Volume() - s.Volume()) / s.Volume() < 1e-6
        for k in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax"):
            assert abs(getattr(b0, k) - getattr(b1, k)) < 1e-4
        assert len(r.Solids()) == 1 and r.isValid()


def test_preview_assembly_step(v6, comb, cover):
    asm = cq.importers.importStep(os.path.join(STEP, "gripper_v6_with_camera_bay_preview.step"))
    sol = asm.solids().vals()
    assert len(sol) == len(v6) - 1 + 2                      # box replaced, cover added
    exp = sum(s.Volume() for n, s in v6 if n != BOX_NAME) + comb.Volume() + cover.Volume()
    assert sum(s.Volume() for s in sol) == pytest.approx(exp, rel=1e-6)


def test_exports_not_stale(box, comb, body, cover):
    from cad.parts import claw_camera_bay as B
    ox, oy, oz = B.BAY_ORIGIN_WORLD
    box_bay = cq.Workplane().add(box).translate((-ox, -oy, -oz))
    loc = cq.Location(cq.Vector(ox, oy, oz))
    regen = B.combine(box_bay).val().moved(loc)
    assert regen.cut(comb).Volume() < 1.0 and comb.cut(regen).Volume() < 1.0
    rb = B.make_bay_body().val().moved(loc)
    rc = B.make_cover().val().moved(loc)
    assert rb.cut(body).Volume() < 1.0 and body.cut(rb).Volume() < 1.0
    assert rc.cut(cover).Volume() < 1.0 and cover.cut(rc).Volume() < 1.0


@pytest.mark.parametrize("name,zmin_zero", [("gripper_electric_housing_with_camera_bay", True),
                                            ("claw_camera_bay_body", True),
                                            ("claw_camera_bay_cover", False)])
def test_stl_closed_and_matches_step(name, zmin_zero):
    T = load_stl(os.path.join(STL, name + ".stl"))
    vol = np.einsum("ij,ij->i", T[:, 0], np.cross(T[:, 1], T[:, 2])).sum() / 6
    step = cq.importers.importStep(os.path.join(STEP, name + ".step")).val()
    assert vol == pytest.approx(step.Volume(), rel=3e-3)
    pts = np.round(T.reshape(-1, 3), 3)
    u, inv = np.unique(pts, axis=0, return_inverse=True)
    tri = inv.reshape(-1, 3)
    tri = tri[(tri[:, 0] != tri[:, 1]) & (tri[:, 1] != tri[:, 2]) & (tri[:, 0] != tri[:, 2])]
    e = np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]])
    e.sort(1)
    _, cnt = np.unique(e, axis=0, return_counts=True)
    assert (cnt == 2).all(), "STL is not a closed 2-manifold"
    if zmin_zero:
        assert abs(T[:, :, 2].min()) < 1e-3                         # sits on the bed
    else:
        pytest.xfail("F9: cover STL is exported at its assembled height (z>=21.7), not on the bed")


# --------------------------------------------------------------------------- 2. union / cuts only
def test_combined_is_box_plus_bay_minus_intended_cuts_only(box, comb, body, diff):
    removed, added = diff
    # removed material: wire window (+flares) and IMU pilot nick, nothing else
    assert removed.Volume() == pytest.approx(1060.8, abs=15.0)
    for s in removed.Solids():
        bb = s.BoundingBox()
        assert abs(bb.xmin - OX) < 9.2 and abs(bb.xmax - OX) < 9.2          # |x| <= 9.1
        assert 44.9 < (OZ - bb.zmax) and (OZ - bb.zmin) < 63.6               # r in 45 .. 63.5
        assert 2.3 < bb.ymin - OY and bb.ymax - OY < 21.0                    # y 2.4 .. 20.5
    # added material: inside the bay envelope only and a subset of the shipped bay body
    bb = added.BoundingBox()
    assert bb.ymin - OY > -0.01 and bb.ymax - OY < 24.41                     # nothing above the cover seat
    assert max(abs(bb.xmin - OX), abs(bb.xmax - OX)) < 35.0
    assert (OZ - bb.zmax) > 49.9 and (OZ - bb.zmin) < 101.21
    assert added.cut(body).Volume() < 0.5
    assert len(added.Solids()) == 1
    # nothing added or removed on the +Z half / +-X far sides
    far = Bx(-70, 70, -1, 90, -70, 0)                                         # r<0, the +Z side
    assert vol_int(removed, far) < 1e-3 and vol_int(added, far) < 1e-3


def test_corner_cable_holes_untouched(box, comb, diff):
    removed, added = diff
    ho, hc = hole_faces(box), hole_faces(comb)
    assert len(ho) == 8                                       # 4 holes x 2 half faces in the original
    for nm, fs in (("orig", ho), ("comb", hc)):
        per = {}
        for f in fs:
            per[hole_key(f)] = per.get(hole_key(f), 0) + f.Area()
        assert len(per) == 4
        for k, a in per.items():
            assert a == pytest.approx(85.916, abs=0.01), (nm, k)                # identical bore area
    # hole geometry (diameter, length, exit position) from the original
    for f in ho[:1]:
        assert BRepAdaptor_Surface(f.wrapped).Cylinder().Radius() == pytest.approx(P.CAMBAY_CORNER_HOLE_D / 2, abs=1e-3)
    # wall material around each bore (radius 10 mm shell, 40 mm long) unchanged within boolean noise
    d0 = cq.Vector(0.66, 0.358, 0.66).normalized()
    for sx in (1, -1):
        for sz in (1, -1):
            p0 = cq.Vector(OX + sx * 41.174, OY + 7.047, OZ + sz * 41.174)
            d = cq.Vector(sx * d0.x, d0.y, sz * d0.z)
            cyl = cq.Solid.makeCylinder(10.0, 40, p0 - d * 8, d)
            assert abs(box.intersect(cyl).Volume() - comb.intersect(cyl).Volume()) < 2.0
    # nearest approach of anything added/removed to any bore
    for f in hc:
        assert dist(f, added) > 14.0                          # keep-out requirement is 5.0
        assert dist(f, removed) > 30.0


def test_lid_seat_and_rim_unchanged(box, comb, diff):
    removed, added = diff
    for y0 in (60.0, 73.7, 80.0):
        s = Bx(-100, 100, y0, 90, -100, 100)
        assert abs(vol_int(box, s) - vol_int(comb, s)) < 0.05
    for y in (81.2, 73.7):                                    # rim top face and lid-seat ledge areas
        def area(sh):
            return sum(f.Area() for f in sh.Faces()
                       if abs(f.BoundingBox().ymin - (OY + y)) < 0.01 and abs(f.BoundingBox().ymax - (OY + y)) < 0.01)
        assert area(box) == pytest.approx(area(comb), abs=0.01)
    assert removed.BoundingBox().ymax - OY < 21.0 < 73.7 - 50   # window top >= 50 mm under the seat
    assert vol_int(added, Bx(-100, 100, 25.0, 90, -100, 100)) < 0.01


# --------------------------------------------------------------------------- 3. placement / optics
def test_narrow_side_axis_and_optical_offset(v6, mesh_comb):
    hous = [s for n, s in v6 if n.startswith("Gripper_gear_housing")]
    bbs = [s.BoundingBox() for s in hous]
    X = max(b.xmax for b in bbs) - min(b.xmin for b in bbs)
    Z = max(b.zmax for b in bbs) - min(b.zmin for b in bbs)
    assert X == pytest.approx(140.0, abs=0.1) and Z == pytest.approx(80.0, abs=0.1)
    assert Z < X                                              # Z is the narrow dimension
    zc = 0.5 * (max(b.zmax for b in bbs) + min(b.zmin for b in bbs))
    assert zc == pytest.approx(OZ, abs=0.01)                  # housing centred on the tube axis
    # lens window centre measured on the shipped solid: x = 0, r = 90 on the -Z side
    xs = _along(mesh_comb, 0, 3.0, -90.0)                     # along x at y=3, z=-90
    assert list(np.round(xs, 2)) == [-12.8, -7.5, 7.5, 12.8]
    rs = -_along(mesh_comb, 2, 0.0, 3.0)[::-1]                # along z at x=0, y=3 -> r
    rwin = rs[5:7]                                            # crossings: -63.5 -10 | 10 63.5 | 80.8 [82.5 97.5] 101.2
    assert 0.5 * (rwin[0] + rwin[1]) == pytest.approx(90.0, abs=0.02)
    assert rwin[1] - rwin[0] == pytest.approx(15.0, abs=0.02)
    # tube axis position used for the bay origin
    from cad.v6_loader import tube_axis_world
    tx, tz, _, _ = tube_axis_world(load_v6())
    assert tx == pytest.approx(OX, abs=1e-3) and tz == pytest.approx(OZ, abs=1e-3)


@pytest.fixture(scope="module")
def optics(v6, comb, cover):
    meshes = {}
    for n, s in v6:
        if n == BOX_NAME:
            continue
        k, i = n, 0
        while k in meshes:
            i += 1
            k = f"{n}#{i}"
        meshes[k] = tess(s, 0.1, 0.2)
    meshes["BOX+BAY"] = tess(comb, 0.1, 0.2)
    meshes["COVER"] = tess(cover, 0.1, 0.2)
    y_floor = min(s.BoundingBox().ymin for n, s in v6)         # lowest jaw tip, jaws down
    lens = np.array([OX, OY + 1.9, OZ - 90.0])                 # lens glass: 4.5 mm below the 6.4 board seat
    return meshes, y_floor, lens


def _rays(nx, ny, swap=False):
    th = math.tan(math.radians(35.0))
    tx, ty = th * 4 / 5, th * 3 / 5
    if swap:
        tx, ty = ty, tx
    gx = (np.arange(nx) + 0.5) / nx * 2 - 1
    gy = (np.arange(ny) + 0.5) / ny * 2 - 1
    X, Z = np.meshgrid(gx * tx, gy * ty, indexing="ij")
    D = np.stack([X.ravel(), -np.ones(X.size), Z.ravel()], 1)
    return D / np.linalg.norm(D, axis=1)[:, None]


def _cast(optics, D, hide=()):
    meshes, y_floor, lens = optics
    tf = (y_floor - lens[1]) / D[:, 1]
    best = np.full(len(D), np.inf)
    who = np.full(len(D), -1)
    names = [k for k in meshes if k not in hide]
    for i, k in enumerate(names):
        t = mt_first_hit(lens, D, *meshes[k])
        upd = t < best
        best[upd], who[upd] = t[upd], i
    blocked = best < tf
    by = {}
    for i, k in enumerate(names):
        c = int(((who == i) & blocked).sum())
        if c:
            by[k] = c / len(D)
    return blocked, by, tf


def test_lens_height_above_floor(optics):
    _, y_floor, lens = optics
    assert lens[1] - y_floor == pytest.approx(511.7, abs=0.5)      # author claim 511.7
    assert y_floor == pytest.approx(581.43, abs=0.01)              # lowest jaw tip, jaws down


def test_fov_blockage_claim_12p4_percent(optics):
    blocked, by, _ = _cast(optics, _rays(64, 48))                  # 4:3, 70 deg diagonal, long side along X
    frac = blocked.mean()
    assert frac == pytest.approx(0.124, abs=0.015), f"measured {frac:.4f}"
    assert set(by) <= {"Gripper_gear_housing", "Gripper_gear_housing_Part2", "aluminum tubing",
                       "24T_Follower", "06_compound_54T_24T", "Claw_arm_extension", "Claw_arm_extension#1"}
    # the bay itself (box+bay, cover) never clips the field of view
    blocked_b, _, _ = _cast(optics, _rays(40, 30), hide=[k for k in optics[0] if k not in ("BOX+BAY", "COVER")])
    assert blocked_b.sum() == 0
    # rotated sensor is worse
    blocked_r, _, _ = _cast(optics, _rays(48, 64, swap=True))
    assert blocked_r.mean() > frac


def test_floor_between_jaw_tips_is_hidden_by_gear_housing(optics):
    """Documents (not a defect of the part): the grasp zone is NOT visible."""
    meshes, y_floor, lens = optics
    for x, z in ((-40, -13), (0, -13), (40, -13), (-40, 7), (0, 7), (40, 7)):
        tgt = np.array([OX + x, y_floor, OZ + z])
        d = tgt - lens
        L = np.linalg.norm(d)
        d = (d / L)[None]
        hit = min(mt_first_hit(lens, d, *m)[0] for m in meshes.values())
        assert hit < L - 1e-3


@pytest.mark.xfail(strict=True, reason="F5: floor under the jaw tips (the grasp point) is hidden by the gear housing; "
                                       "nearest unobstructed floor is 30 mm from the tube axis")
def test_grasp_point_visible_from_camera(optics):
    meshes, y_floor, lens = optics
    tgt = np.array([OX, y_floor, OZ - 6.0])
    d = tgt - lens
    L = np.linalg.norm(d)
    d = (d / L)[None]
    assert min(mt_first_hit(lens, d, *m)[0] for m in meshes.values()) >= L - 1e-3


# --------------------------------------------------------------------------- 4. cable lines
@pytest.fixture(scope="module")
def cable_setup(box, comb, cover):
    exits = {}
    for f in hole_faces(box):
        a = BRepAdaptor_Surface(f.wrapped).Cylinder()
        ax = a.Axis()
        p0 = np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()])
        d = np.array([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
        k = hole_key(f)
        out = np.array([k[0], 0, k[1]])
        d = d if d @ out > 0 else -d
        t = max((np.array([v.X, v.Y, v.Z]) - p0) @ d for v in f.Vertices())
        e = exits.setdefault(k, [p0, d, -1e9])
        e[2] = max(e[2], t)
    mouths = {k: (v[0] + v[1] * v[2]) - OFF for k, v in exits.items()}
    # exterior bay surfaces = (comb - box) + cover
    added = comb.cut(box)
    Va, Fa = tess(added, 0.05, 0.2)
    Vc, Fc = tess(cover, 0.05, 0.2)
    V = np.concatenate([Va, Vc]) - OFF
    F = np.concatenate([Fa, Fc + len(Va)])
    tri = V[F]
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    rng = np.random.default_rng(0)
    smp = [V]
    n = np.maximum(1, np.ceil(area / 0.3).astype(int))
    for k in range(1, int(n.max()) + 1):
        sel = np.where(n >= k)[0]
        w = rng.dirichlet([1, 1, 1], size=len(sel))
        smp.append(np.einsum("ij,ijk->ik", w, tri[sel]))
    return mouths, V, F, np.concatenate(smp)


def test_corner_cable_exit_positions(cable_setup):
    mouths = cable_setup[0]
    assert len(mouths) == 4
    for (sx, sz), m in mouths.items():
        assert m[0] == pytest.approx(sx * 54.09, abs=0.05) and m[2] == pytest.approx(sz * 54.09, abs=0.05)
        assert m[1] == pytest.approx(14.05, abs=0.05)


def test_cable_lines_clear_of_bay_in_stated_range(cable_setup):
    mouths, V, F, S = cable_setup
    worst = 1e9
    for (sx, sz), m in mouths.items():
        D = []
        for az in np.arange(0, 90.1, 5.0):
            for el in np.arange(10, 90.1, 5.0):
                D.append([sx * math.cos(math.radians(az)) * math.cos(math.radians(el)), math.sin(math.radians(el)),
                          sz * math.sin(math.radians(az)) * math.cos(math.radians(el))])
        D = np.array(D)
        assert np.isinf(mt_first_hit(m, D, V, F)).all(), "a corner line hits the bay"
        rel = S - m
        for d in D:
            tt = np.clip(rel @ d, 0, None)
            worst = min(worst, np.linalg.norm(rel - tt[:, None] * d[None, :], axis=1).min())
    assert worst >= P.CAMBAY_CORNER_HOLE_KEEPOUT, worst        # measured ~20.4 mm


def test_cable_lines_aimed_across_the_bay_face_do_touch_it(cable_setup, comb, cover):
    """Informational boundary (F6): from the two -Z corners, a line aimed across the bay at <= ~12 deg
    elevation (azimuth ~35 deg past the corner quadrant) hits the bay even with the box in the way."""
    mouths, _, _, _ = cable_setup
    Vk, Fk = tess(comb, 0.05, 0.2)
    Vc, Fc = tess(cover, 0.05, 0.2)
    V = np.concatenate([Vk, Vc]) - OFF
    F = np.concatenate([Fk, Fc + len(Vk)])
    m = mouths[(-1, -1)]
    az, el = 320.0, 5.0
    d = np.array([[math.cos(math.radians(az)) * math.cos(math.radians(el)), math.sin(math.radians(el)),
                   math.sin(math.radians(az)) * math.cos(math.radians(el))]])
    t = mt_first_hit(m + np.array([-1, 0.4, -1]) * 0.05, d, V, F)[0]
    assert np.isfinite(t)
    p = m + d[0] * t
    assert p[2] < -63.6 and abs(p[0]) < 36                    # first hit is the bay, not the box


# --------------------------------------------------------------------------- 5. wire window
def test_wire_window_size_position_and_edge_breaks(mesh_comb, diff):
    removed, _ = diff
    for r in (47.0, 50.0, 55.0):                              # straight part of the tunnel (box wall 45 .. 59)
        xs = _along(mesh_comb, 0, 15.5, -r)
        ys = _along(mesh_comb, 1, 0.0, -r)
        # solid -> void edges around the tunnel centre
        xl = [v for v in xs if v < 0][-1]
        xr = [v for v in xs if v > 0][0]
        assert (xr - xl) == pytest.approx(10.0, abs=0.05)
        yb = [v for v in ys if v < 15.5][-1]
        yt = [v for v in ys if v > 15.5][0]
        assert (yb, yt) == pytest.approx((12.0, 19.0), abs=0.05)
        assert (yt - yb) >= 6.0 and (xr - xl) >= 8.0         # requirement: >= 8 x 6
    # roof corner chamfer (45 deg) - bridge limited to 5 mm
    y_corner = [v for v in _along(mesh_comb, 1, 4.5, -50.0) if v > 15.5][0]
    assert y_corner == pytest.approx(17.0, abs=0.05)
    # 1.5 mm x 45 deg flare at the pocket mouth (edge break on the inside)
    xr45 = [v for v in _along(mesh_comb, 0, 15.5, -45.05) if v > 0][0]
    assert xr45 == pytest.approx(6.45, abs=0.06)
    # window top (incl. flare) vs lid seat
    assert removed.BoundingBox().ymax - OY < 21.0 and 73.7 - 21.0 > 50.0


def test_wire_path_continuous_xiao_to_box_interior(mesh_comb, mesh_cover):
    """Occupancy grid (0.25 mm) of box+bay and cover; XIAO 21x17.8x15 and IMU board are added as
    obstacles; widest sphere that can travel from the XIAO neck-side edge / headroom to the box pocket."""
    from scipy import ndimage as ndi
    H = 0.25
    xs = np.arange(-20, 20 + H / 2, H)
    ys = np.arange(-1, 30 + H / 2, H)
    rs = np.arange(40, 104 + H / 2, H)

    def occ(mesh):
        V, F = mesh
        pts = [(x + 1.2e-4, y + 7e-5) for x in xs for y in ys]
        cr = cross_coords(V, F, 2, pts)
        o = np.zeros((len(xs), len(ys), len(rs)), bool)
        k = 0
        for i in range(len(xs)):
            for j in range(len(ys)):
                z = cr[k]
                k += 1
                if len(z):
                    o[i, j, :] = (np.searchsorted(z, -rs) % 2) == 1
        return o

    oc, ov = occ(mesh_comb), occ(mesh_cover)
    X, Y, R = np.meshgrid(xs, ys, rs, indexing="ij")
    xiao = (np.abs(X) <= 10.5) & (Y >= 6.4) & (Y <= 21.4) & (np.abs(R - 90) <= 8.9)
    imu = (np.abs(X) <= 10.5) & (Y >= 8.4) & (Y <= 10.0) & (R >= 62.9) & (R <= 78.5)
    free = ~(oc | ov | xiao | imu)
    edt = ndi.distance_transform_edt(free, sampling=H)
    start = (np.abs(X) <= 7.6) & (Y >= 12) & (Y <= 21) & (R >= 79.5) & (R <= 82.0)
    goal = (R <= 44.5) & (np.abs(X) <= 6) & (Y >= 11) & (Y <= 20)

    def ok(d):
        lab, _ = ndi.label(edt >= d / 2, structure=np.ones((3, 3, 3)))
        a = set(np.unique(lab[start & (edt >= d / 2)])) - {0}
        b = set(np.unique(lab[goal & (edt >= d / 2)])) - {0}
        return bool(a & b)

    lo, hi = 0.0, 8.0
    for _ in range(10):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    assert lo >= 3.0, f"max traversable bundle diameter {lo:.2f} mm"          # measured 3.5 mm


# --------------------------------------------------------------------------- 6. board fits
def test_xiao_cradle_clearance_and_alignment(comb, cover, mesh_comb):
    # exact cradle void: 21.6 x 18.4 (nominal 21.0 x 17.8 + 0.3 per side)
    xs = _along(mesh_comb, 0, 10.0, -85.0)
    assert (xs[2] - xs[1]) == pytest.approx(21.6, abs=0.02)
    rs = -_along(mesh_comb, 2, 7.0, 10.0)[::-1]
    # crossings (r): ... 78.8 80.8 | 99.2 101.2 -> void 80.8 .. 99.2
    assert rs[-2] - rs[-3] == pytest.approx(18.4, abs=0.02)
    for dx, dr in ((0, 0), (0.25, 0), (-0.25, 0), (0, 0.25), (0, -0.25)):
        b = Bx(-10.5 + dx, 10.5 + dx, 6.4, 21.4, 90 - 8.9 + dr, 90 + 8.9 + dr)
        assert vol_int(b, comb) < 1e-3 and vol_int(b, cover) < 1e-3
    for dx, dr in ((0.35, 0), (0, 0.35)):                       # only 0.3 mm of play per side
        b = Bx(-10.5 + dx, 10.5 + dx, 6.4, 21.4, 90 - 8.9 + dr, 90 + 8.9 + dr)
        assert vol_int(b, comb) > 1.0
    # lens barrel (D8 x 4.5) inside the 15 x 15 hood window: tolerates +-3.4 mm lens-position error
    for dx, dr in ((0, 0), (3.0, 0), (0, 3.0), (3.4, 3.4)):
        cyl = cq.Solid.makeCylinder(4.0, 4.5, cq.Vector(OX + dx, OY + 1.9, OZ - (90 + dr)), cq.Vector(0, 1, 0))
        assert vol_int(cyl, comb) < 1e-3
    # board seat ledge around the window (support width): reported, must be >= 1.5
    assert 82.5 - 80.8 >= 1.5 and 7.5 + 0 < 10.8                # radial ledge 1.7, x ledge 3.3


def test_usb_window_reachable_by_plug_8p5x7(comb):
    # a 8.5 x 7 plug (the width at the chamfered roof) passes; used as the control for the 12x7 test below
    yc = 21.4 - 1.6
    b = Bx(9.0, 45.0, yc - 3.5, yc + 3.5, 90 - 4.25, 90 + 4.25)
    assert vol_int(b, comb) < 1e-3


@pytest.mark.xfail(strict=True, reason="F2: USB window has 2 mm 45-deg roof chamfers; a 12 x 7 rectangular plug "
                                       "overmold interferes (6.1 mm3); only <= ~10 x 6 or 8.5 x 7 passes")
def test_usb_window_passes_12x7_plug(comb):
    yc = 21.4 - 1.6
    b = Bx(9.0, 45.0, yc - 3.5, yc + 3.5, 90 - 6.0, 90 + 6.0)
    assert vol_int(b, comb) < 1e-3


def test_usb_window_geometry(mesh_comb):
    ys = _along(mesh_comb, 1, 11.8, -90.0)                      # sill and lintel at x inside +X wall
    assert list(np.round(ys, 2)) == [0.0, 16.3, 23.3, 24.4]
    rs = -_along(mesh_comb, 2, 11.8, 19.8)[::-1]                # ... 83.75 [window] 96.25 101.2
    assert (rs[-2] - rs[-3]) == pytest.approx(12.5, abs=0.02)
    assert 0.5 * (rs[-2] + rs[-3]) == pytest.approx(90.0, abs=0.02)   # window centred on the board / lens axis
    rs_roof = -_along(mesh_comb, 2, 11.8, 23.25)[::-1]            # just below the roof: chamfers leave a narrow flat
    assert (rs_roof[-2] - rs_roof[-3]) <= 8.7

@pytest.mark.xfail(strict=True, reason="F3: wall above the USB window is 1.1 mm (y 23.3 .. 24.4) < 2.0 mm minimum")
def test_usb_lintel_at_least_2mm(mesh_comb):
    ys = _along(mesh_comb, 1, 11.8, -90.0)
    assert (ys[3] - ys[2]) >= 2.0 - 0.05


def test_cover_fasteners_and_fit(comb, cover, box, mesh_comb, mesh_cover):
    # M3 heat-set boss: OD 9.0, hole D4.0 depth 6.0 from the cover seat, 2.5 mm wall (outer side)
    xs = _along(mesh_comb, 0, 20.0, -70.0)
    assert list(np.round(xs, 2)) == [-20.3, -17.8, -13.8, -10.8, 10.8, 13.8, 17.8, 20.3]
    assert (xs[5] - xs[4]) == pytest.approx(3.0, abs=0.02)      # 3.0 mm between cavity and hole
    hole_x = _along(mesh_comb, 1, 15.8, -70.0)
    assert list(np.round(hole_x, 2)) == [0.0, 18.4]              # hole 6.0 deep from y=24.4
    assert 24.4 - 18.4 >= 5.7 + 0.2                              # insert M3x5.7 fits (margin only 0.3, see F8)
    # cover screw holes (D3.4) coaxial with the boss holes
    cx = _along(mesh_cover, 0, 25.5, -70.0)
    assert 0.5 * (cx[3] + cx[2]) == pytest.approx(15.8, abs=0.02) or abs(0.5 * (cx[4] + cx[3]) - 15.8) < 0.02
    assert vol_int(cover, comb) < 1e-3                           # no interference
    assert dist(cover, box) >= 0.2                               # clear of the box wall (0.33 measured)
    # M3x8: 2.4 cover + 5.6 in insert (insert 5.7 deep)
    assert 8.0 - 2.4 <= 6.0


# --------------------------------------------------------------------------- IMU
def test_imu_post_axes_vs_assumed_board(comb):
    axes = []
    for f in comb.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Cylinder and abs(a.Cylinder().Radius() - 1.05) < 1e-3:
            l = a.Cylinder().Axis().Location()
            axes.append((round(l.X() - OX, 3), round(OZ - l.Z(), 3)))
    axes.sort(key=lambda t: t[1])
    assert axes[0] == pytest.approx((-8.0, 63.1), abs=0.01) and axes[1] == pytest.approx((-8.0, 78.3), abs=0.01)
    pitch = axes[1][1] - axes[0][1]
    assert pitch == pytest.approx(15.2, abs=0.01)
    # IMU board (21 x 15.6 x 1.6, y 8.4..10.0) does not collide with anything
    b = Bx(-10.5, 10.5, 8.4, 10.0, 62.9, 78.5)
    assert vol_int(b, comb) < 1e-3


@pytest.mark.xfail(strict=True, reason="F4: pitch 15.2 mm across the 15.6 mm board width puts each hole centre 0.2 mm from "
                                       "the board edge (a D3 hole would break out); inconsistent assumption")
def test_imu_hole_pitch_consistent_with_board_width():
    edge = (P.CAMBAY_IMU_W - P.CAMBAY_IMU_HOLE_PITCH) / 2
    assert edge >= P.CAMBAY_IMU_HOLE_D / 2 + 0.5


@pytest.mark.xfail(strict=True, reason="F4b: IMU post 1 is cut by the wire-window outer flare cutter; only ~36 % of the "
                                       "post top reaches the board seat height 8.4 and the pilot hole 1 opens to the side")
def test_imu_post1_full_height(comb):
    contact = vol_int(Bx(-12, -4, 8.35, 8.4, 62.9, 70.0), comb) / 0.05
    ring = math.pi * (3.55 ** 2 - 1.05 ** 2)
    assert contact >= 0.8 * ring


@pytest.mark.xfail(strict=True, reason="F4c: repo BOM/docs select the Adafruit 3886 MPU6050 (26 x 17.8 x 4.6), which does not fit "
                                       "the 21.6 x ~15.6 mm IMU neck in either orientation")
def test_repo_selected_imu_fits_neck(comb):
    for L, W in ((26, 17.8), (17.8, 26)):
        b = Bx(-L / 2, L / 2, 8.4, 8.4 + 4.6, 70.7 - W / 2, 70.7 + W / 2)
        assert vol_int(b, comb) < 1e-3


# --------------------------------------------------------------------------- min wall / printability
@pytest.fixture(scope="module")
def thickness_scan(comb):
    V, F = tess(comb, 0.03, 0.2)
    V = V - OFF
    c, t = inward_thickness(V, F, lambda c: (np.abs(c[:, 0]) < 40) & (c[:, 2] < -56.5) & (c[:, 1] < 26) & (c[:, 1] > -0.1))
    return c, t


@pytest.mark.xfail(strict=True, reason="F3/F4: sampled wall thickness below 2.0 mm: USB lintel 1.10, pilot-2 to fence face 1.45, "
                                       "IMU post-1 sliver <0.3 (see report)")
def test_min_wall_2mm_in_bay(thickness_scan):
    c, t = thickness_scan
    assert t.min() >= 2.0 - 0.05


def test_min_wall_known_values(thickness_scan):
    c, t = thickness_scan
    # USB lintel
    m = (np.abs(c[:, 0] - 11.5) < 1.5) & (c[:, 1] > 23.0) & (c[:, 1] < 24.5) & (-c[:, 2] > 85) & (-c[:, 2] < 95)
    assert t[m].min() == pytest.approx(1.1, abs=0.05)
    # every other sampled wall (excluding the 3 flagged locations and the 1.7 lens ledge) is >= 1.6
    keep = np.ones(len(t), bool)
    keep &= ~m
    keep &= ~((c[:, 0] < -5) & (c[:, 0] > -11) & (-c[:, 2] > 64) & (-c[:, 2] < 67.5))       # post-1 sliver
    keep &= ~((np.abs(c[:, 0] + 7.8) < 1.0) & (-c[:, 2] > 78.5) & (-c[:, 2] < 80.0))         # pilot-2 wall
    keep &= ~((-c[:, 2] > 80.0) & (-c[:, 2] < 83.0) & (c[:, 1] < 6.5))                        # lens ledge
    assert t[keep].min() >= 1.6


def _along_mesh(V, F, axis, a, b):
    return cross_coords(V, F, axis, [(a + 1e-5, b + 2e-5)])[0]


def pts_width(V, F, x, y):
    """radial extent of the void run that contains r=90 at (x, y) (USB window width at height y)."""
    r = -cross_coords(V, F, 2, [(x + 1e-5, y + 2e-5)])[0][::-1]
    return r[-2] - r[-3]


def pts_width_x(V, F, y, z):
    xs = cross_coords(V, F, 0, [(y + 2e-5, z + 2e-5)])[0]
    xl = [v for v in xs if v < 0][-1]
    xr = [v for v in xs if v > 0][0]
    return xr - xl


def test_overhangs_and_bridges_in_print_orientation(comb, cover):
    """Box+bay printed flange-down (+Y up).  Faces steeper than 45 deg from horizontal facing down are
    overhangs; flat ones are bridges.  Checks: only flat bridges, longest span <= 10 mm."""
    V, F = tess(comb, 0.02, 0.1)
    V = V - OFF
    tri = V[F]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = 0.5 * np.linalg.norm(n, axis=1)
    n = n / np.linalg.norm(n, axis=1)[:, None]
    c = tri.mean(1)
    bay = (np.abs(c[:, 0]) < 40) & (c[:, 2] < -44) & (c[:, 1] < 30) & (c[:, 1] > 0.05) & (area > 1e-4)
    over = np.where(bay & (n[:, 1] < -0.7072))[0]
    flat = over[n[over, 1] < -0.999]
    slanted = over[n[over, 1] >= -0.999]
    assert area[slanted].sum() < 80.0                           # only the window roof chamfers / flare roofs (<45 deg slopes tiny)
    # bridges are limited to the flat part of the 45-degree-chamfered roofs: USB window ~8.5 mm, wire window 5 mm
    yy = _along_mesh(V, F, 1, 11.8, -90.0)
    assert yy[2] == pytest.approx(23.3, abs=0.01)                 # USB roof height
    assert pts_width(V, F, 11.8, 23.29) <= 8.7
    assert pts_width_x(V, F, 18.95, -50.0) <= 5.2

@pytest.mark.xfail(strict=True, reason="F9: cover has features on both faces (pegs 2.7 mm + lip 1.0 mm under, antenna rails 1.5 mm above), "
                                       "so it cannot lie flat on the bed 'either face down' without supports")
def test_cover_prints_flat_either_face(cover):
    bb = cover.BoundingBox()
    assert (bb.ymax - bb.ymin) <= 2.4 + 0.01


# --------------------------------------------------------------------------- stiffness / mass
def test_cantilever_stiffness_sanity(comb, diff, cover):
    _, added = diff
    V, F = tess(comb, 0.02, 0.15)
    V = V - OFF
    H = 0.2
    xs = np.arange(-36, 36, H) + H / 2
    ys = np.arange(0, 30, H) + H / 2
    pts = [(x + 1.2e-4, y + 7e-5) for x in xs for y in ys]
    cr = cross_coords(V, F, 2, pts)
    root_r = 64.0
    A = []
    k = 0
    for x in xs:
        for y in ys:
            z = cr[k]
            k += 1
            if len(z) and (np.searchsorted(z, -root_r) % 2) == 1:
                A.append((x, y))
    A = np.array(A)
    area = len(A) * H * H
    yb = A[:, 1].mean()
    Ix = ((A[:, 1] - yb) ** 2).sum() * H * H
    Iy = (A[:, 0] ** 2).sum() * H * H
    cy = max(yb - A[:, 1].min(), A[:, 1].max() - yb)
    cx = np.abs(A[:, 0]).max()
    assert Ix == pytest.approx(12274, rel=0.03)                 # same I the author used
    # outboard mass and its moment about the root section (r = 64)
    cut = cq.Workplane().box(200, 200, 200, centered=False).translate((OX - 100, OY - 50, OZ - root_r - 200)).val()
    pa, pc = added.intersect(cut), cover.intersect(cut)
    masses = [(pa.Volume() * PETG, OZ - pa.Center().z), (pc.Volume() * PETG, OZ - pc.Center().z),
              (5.0, 90.0), (2.5, 70.7), (3.0, 85.0)]              # XIAO+Sense, IMU, wiring: assumed
    M_w = sum(m * (r - root_r) for m, r in masses) * 1e-3        # kg*mm
    arm = 101.2 - root_r
    g = 9.81
    sig_vert = (M_w * (g + 2.0) + 10.0 * arm) * cy / Ix          # 1 g + 2 m/s2 dynamic + 10 N vertical, N*mm/mm4 = MPa
    sig_side = (M_w * g + 10.0 * arm) * 0 + (10.0 * arm) * cx / Iy
    Kt = 3.0
    allow = 25.0 / 2
    assert Kt * sig_vert < allow and Kt * sig_side < allow
    assert Kt * sig_vert < 5.0                                    # measured ~1.5 MPa
    # tip droop under 10 N vertical (E = 2.1 GPa)
    defl = 10.0 * arm ** 3 / (3 * 2100.0 * Ix)
    assert defl < 0.05


def test_added_mass_small(comb, box, cover):
    m_bay = (comb.Volume() - box.Volume()) * PETG
    m_cov = cover.Volume() * PETG
    assert m_bay + m_cov < 30.0
    assert m_bay + m_cov == pytest.approx(18.2, abs=0.5)         # NET of the window cut; author quotes "~18 g"
    assert (comb.Volume() - box.Volume() + 1060.8) * PETG + m_cov == pytest.approx(19.5, abs=0.5)   # gross
