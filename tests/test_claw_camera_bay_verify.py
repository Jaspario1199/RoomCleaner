"""
INDEPENDENT verification of the claw camera bay (rounds 1-3; round 3 = commit 769d4e4: IMU removed (D27), 23.0 x 18.6 cradle,
lens window at the USB-C end, D28 tube cut in the v7 preview).

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
LENS_DX = 4.75                                    # round 3: lens centre along bay X (USB-C end of the 21 mm board at -0.75 + 10.5, minus 5.0)
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
    ("gripper_electric_housing_with_camera_bay", 404199.15),    # round 3 (IMU removed, bay ends at r 101.3)
    ("claw_camera_bay_body", 14984.04),
    ("claw_camera_bay_cover", 3597.63)])
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


@pytest.mark.xfail(strict=True, reason="R3-F1: shipped body/housing export is stale vs cad/parts/claw_camera_bay.py: the module puts the "
                                       "1.6 mm locating ribs at x = -8 and +7, the export has 1.2 mm ribs at x = -8 and -1 (the -1 pair stands "
                                       "free in the wire gap, 0.5 mm thick). Cover export matches. Regenerate + re-export to clear.")
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
                                            ("claw_camera_bay_cover", True)])
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
        assert abs(T[:, :, 2].min()) < 1e-3                         # sits on the bed (F9: cover STL now placed on the bed)


# --------------------------------------------------------------------------- 2. union / cuts only
def test_combined_is_box_plus_bay_minus_intended_cuts_only(box, comb, body, diff):
    removed, added = diff
    # removed material: wire window (+flares), nothing else (identical to the previous export)
    assert removed.Volume() == pytest.approx(1050.9, abs=15.0)     # wire window only (pilot nick removed)
    for s in removed.Solids():
        bb = s.BoundingBox()
        assert abs(bb.xmin - OX) < 9.2 and abs(bb.xmax - OX) < 9.2          # |x| <= 9.1
        assert 44.9 < (OZ - bb.zmax) and (OZ - bb.zmin) < 63.6               # r in 45 .. 63.5
        assert 2.3 < bb.ymin - OY and bb.ymax - OY < 21.0                    # y 2.4 .. 20.5
    # added material: inside the bay envelope only and a subset of the shipped bay body
    bb = added.BoundingBox()
    assert bb.ymin - OY > -0.01 and bb.ymax - OY < 26.91                     # nothing above the cover seat (y 26.9)
    assert bb.xmax - OX < 35.0 and OX - bb.xmin < 35.0          # gusset ribs to +-34.83
    assert (OZ - bb.zmax) > 49.9 and (OZ - bb.zmin) < 101.31    # round 3: no IMU pocket, bay ends at r = 101.3
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
    assert vol_int(added, Bx(-100, 100, 27.0, 90, -100, 100)) < 0.01      # nothing above the bay wall top / cover seat (26.9)


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
    # lens window measured on the shipped solid (round 3): x -3.25 .. +11.0 (14.25), r 81.8 .. 98.2 (16.4, centre 90) on the -Z side
    xs = _along(mesh_comb, 0, 3.0, -90.0)                     # along x at y=3, z=-90
    assert list(np.round(xs, 2)) == [-13.5, -3.25, 11.0, 13.5]   # wall + block | 14.25 mm window (USB-C end, +X) | block + wall
    rs = -_along(mesh_comb, 2, 0.0, 3.0)[::-1]                # along z at x=0, y=3 -> r
    rwin = rs[5:7]                                            # crossings: -63.5 -10 | 10 63.5 | 78.8 [81.8 98.2] 101.3
    assert 0.5 * (rwin[0] + rwin[1]) == pytest.approx(90.0, abs=0.02)
    assert rwin[1] - rwin[0] == pytest.approx(16.4, abs=0.02)
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
    lens = np.array([OX + LENS_DX, OY + 1.9, OZ - 90.0])       # lens glass 1.9 above the bed plane, 5 mm from the USB-C end of the board (x = +4.75)
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
    """v6 frame (bay not moved): lens glass world y 1093.09 above the lowest v6 jaw tip 581.43 = 511.66 mm."""
    _, y_floor, lens = optics
    assert lens[1] == pytest.approx(1093.0905, abs=1e-3)
    assert lens[0] == pytest.approx(956.5975, abs=1e-3) and lens[2] == pytest.approx(1013.9899, abs=1e-3)
    assert lens[1] - y_floor == pytest.approx(511.66, abs=0.02)
    assert y_floor == pytest.approx(581.43, abs=0.01)              # lowest jaw tip, jaws down


def test_d28_lens_world_position_and_height_in_v7_preview():
    """D28 (tube cut 50 mm): everything above the tube moves down 50.  Measured from the v7 preview STEP."""
    sol = cq.importers.importStep(os.path.join(STEP, "gripper_v7_preview.step")).solids().vals()
    y_tip = min(s.BoundingBox().ymin for s in sol)                  # lowest point of the closed-jaw v7 head
    assert y_tip == pytest.approx(581.034, abs=0.005)
    lens = (OX + LENS_DX, OY + 1.9 - 50.0, OZ - 90.0)
    assert lens == pytest.approx((956.5975, 1043.0905, 1013.9899), abs=1e-3)
    assert lens[1] - y_tip == pytest.approx(462.06, abs=0.01)      # claimed 462.06


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
    print("CABLE_MIN_CLEARANCE", worst)
    assert worst >= P.CAMBAY_CORNER_HOLE_KEEPOUT, worst        # round 3 value: see the report (earlier 19.25 / 20.4 mm)


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
    """Occupancy grid (0.25 mm) of box+bay and cover; the XIAO board stack (21 x 17.8 centred in the 23.0 pocket, 7 mm above
    the seat, plus the 1.5 mm USB-C overhang) is added as an obstacle; widest sphere that can travel from the neck side
    of the cradle (|x| <= 4 fence gap, above the seat) to the box pocket.  Round 3: no IMU obstacle any more."""
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
    xiao = (X >= -11.25) & (X <= 11.25) & (Y >= 9.9) & (Y <= 16.9) & (np.abs(R - 90) <= 8.9)
    free = ~(oc | ov | xiao)
    edt = ndi.distance_transform_edt(free, sampling=H)
    start = (np.abs(X) <= 3.5) & (Y >= 10.0) & (Y <= 26.0) & (R >= 79.0) & (R <= 81.0)
    goal = (R <= 44.5) & (np.abs(X) <= 6) & (Y >= 11) & (Y <= 20)

    def ok(d):
        lab, _ = ndi.label(edt >= d / 2, structure=np.ones((3, 3, 3)))
        a = set(np.unique(lab[start & (edt >= d / 2)])) - {0}
        b = set(np.unique(lab[goal & (edt >= d / 2)])) - {0}
        return bool(a & b)

    lo, hi = 0.0, 10.0
    for _ in range(10):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    print("WIRE_BUNDLE_MAX_D", lo)
    assert lo >= 3.5, f"max traversable bundle diameter {lo:.2f} mm"


# --------------------------------------------------------------------------- 6. board fits
def test_xiao_cradle_clearance_and_alignment(comb, cover, mesh_comb, mesh_cover):
    """Round 3: pocket 23.0 (X) x 18.6 (r), seat plane y = 9.9, cover seat y = 26.9 (cavity 17.0 above the seat)."""
    xs = _along(mesh_comb, 0, 20.0, -81.5)                                   # wall | pocket | wall at y = 20
    assert list(np.round(xs, 2)) == [-13.5, -11.5, 11.5, 13.5]
    assert xs[2] - xs[1] == pytest.approx(23.0, abs=0.02)
    rs = -_along(mesh_comb, 2, -5.0, 15.0)[::-1]                             # ... fence 78.7..80.7 | pocket | wall 99.3..101.3
    assert list(np.round(rs[-4:], 2)) == [78.7, 80.7, 99.3, 101.3]
    assert rs[-2] - rs[-3] == pytest.approx(18.6, abs=0.02)
    seat = _along(mesh_comb, 1, -6.0, -90.0)[-1]                             # cradle block top (board seat plane)
    assert seat == pytest.approx(9.9, abs=0.01)
    cov_under = _along(mesh_cover, 1, 0.0, -70.0)[0]                         # cover underside (flat, = wall top)
    assert cov_under - seat == pytest.approx(17.0, abs=0.01) and cov_under - seat >= 16.0      # cavity height claim
    # four 0.4 mm locating ribs, two per long wall: pocket between ribs is the 17.8 mm board width
    for r0, r1 in ((80.9, 99.1),):
        x_lo = _along(mesh_comb, 0, 12.0, -r0)
        x_hi = _along(mesh_comb, 0, 12.0, -r1)
        inner = lambda a: [v for v in a if -11.4 < v < 11.4]
        assert len(inner(x_lo)) == 4 and len(inner(x_hi)) == 4, (x_lo, x_hi)                # two ribs (4 crossings) per long wall
    for x in (-8.0,):
        r = -_along(mesh_comb, 2, x, 12.0)[::-1]
        assert (r[-3], r[-2]) == pytest.approx((81.1, 98.9), abs=0.01)                       # 17.8 between the ribs
        assert (r[-3] - 80.7, 99.3 - r[-2]) == pytest.approx((0.4, 0.4), abs=0.01)           # 0.4 proud each
    # board 21 x 17.8 (centred in X with 1.5 mm USB-C overhang on +X: x -11.25 .. 9.75, overhang to 11.25), stack 7 mm above the seat
    def board(w=17.8, hgt=7.0, usb=True, dx=0.0, dr=0.0):
        return Bx(-11.25 + dx, 9.75 + (1.5 if usb else 0.0) + dx, 9.9, 9.9 + hgt, 90 - w / 2 + dr, 90 + w / 2 + dr)
    assert vol_int(board(), comb) < 1e-3 and vol_int(board(), cover) < 1e-3                   # nominal: fits with the ribs
    assert vol_int(board(hgt=15.0, usb=False), comb) < 1e-3                                   # whole 15 mm stack above the seat fits the cradle
    assert vol_int(board(w=17.8, hgt=15.0, usb=False), cover) > 1.0                           # (but then the cover hold-down pegs touch it)
    assert vol_int(board(w=18.0), comb) > 1.0                                                  # ribs squeeze a wider board (interference 3.4 mm3)
    # play: +-0.25 in X (board + USB overhang in the 23.0 pocket), none radially (snug on the ribs)
    assert vol_int(board(dx=0.24), comb) < 1e-3 and vol_int(board(dx=-0.24), comb) < 1e-3
    assert vol_int(board(dx=0.3), comb) > 1e-3 and vol_int(board(dx=-0.3), comb) > 1e-3
    assert vol_int(board(dr=0.05), comb) > 1e-3 and vol_int(board(dr=-0.05), comb) > 1e-3
    # camera module (8.5 square, y 1.9 .. 9.9) at the nominal lens position sits in the window
    assert vol_int(Bx(4.75 - 4.25, 4.75 + 4.25, 1.9, 9.9, 90 - 4.25, 90 + 4.25), comb) < 1e-3


def _barrel(dx, dr, d=8.0):
    return cq.Solid.makeCylinder(d / 2, 8.0, cq.Vector(OX + LENS_DX + dx, OY + 1.9, OZ - (90.0 + dr)), cq.Vector(0, 1, 0))


def _module(dx, dr, side=8.5):
    return Bx(LENS_DX + dx - side / 2, LENS_DX + dx + side / 2, 1.9, 9.9, 90 + dr - side / 2, 90 + dr + side / 2)


def _lens_limit(fn, axis, sign, comb):
    lo, hi = 0.0, 8.0
    for _ in range(14):
        mid = (lo + hi) / 2
        a = (sign * mid, 0.0) if axis == "x" else (0.0, sign * mid)
        lo, hi = (mid, hi) if vol_int(fn(*a), comb) < 1e-4 else (lo, mid)
    return sign * lo


def test_lens_window_size_position_and_shift_limits(comb, mesh_comb):
    """Window 14.25 (X: -3.25 .. +11.0, at the USB-C end) x 16.4 (r 81.8 .. 98.2); limits of lens-centre shift (from x = 4.75, r = 90)."""
    xs = _along(mesh_comb, 0, 3.0, -90.0)
    assert (xs[1], xs[2]) == pytest.approx((-3.25, 11.0), abs=0.01) and xs[2] - xs[1] == pytest.approx(14.25, abs=0.01)
    assert 0.5 * (xs[1] + xs[2]) > 0                                       # window centre toward +X = the USB-C end
    rs = -_along(mesh_comb, 2, 0.0, 3.0)[::-1]
    assert (rs[5], rs[6]) == pytest.approx((81.8, 98.2), abs=0.01) and rs[6] - rs[5] == pytest.approx(16.4, abs=0.01)
    assert xs[3] - xs[2] == pytest.approx(2.5, abs=0.01)                   # wall between the window and the outside (+X end), above the chamfer
    lim = {}
    for nm, fn in (("barrel D8", _barrel), ("module 8.5", _module)):
        lim[nm] = [_lens_limit(fn, "x", -1, comb), _lens_limit(fn, "x", 1, comb), _lens_limit(fn, "r", -1, comb), _lens_limit(fn, "r", 1, comb)]
    assert lim["barrel D8"] == pytest.approx([-4.0, 2.25, -4.2, 4.2], abs=0.03)
    assert lim["module 8.5"] == pytest.approx([-3.75, 2.0, -3.95, 3.95], abs=0.03)
    # claim: shifts -3.9 / +2.25 in X and +-3.9 in R: true for the D8 barrel; the 8.5 module is 0.15 / 0.25 short in X
    for dx, dr in ((-3.9, 0), (2.25 - 0.03, 0), (0, 3.9), (0, -3.9)):
        assert vol_int(_barrel(dx, dr), comb) < 1e-4, (dx, dr)
    assert vol_int(_module(-3.9, 0), comb) > 1e-4 and vol_int(_module(2.25, 0), comb) > 1e-4
    assert vol_int(_module(0, 3.9), comb) < 1e-4 and vol_int(_module(0, -3.9), comb) < 1e-4


@pytest.mark.xfail(strict=True, reason="R3-F2: the lens window does NOT tolerate +-4 mm in every direction for the 8.5 mm module: shortfall "
                                       "X-: 0.25, X+: 1.75 (barrel) / 2.0 (module, capped by the pocket end wall), R: 0.05 (module). "
                                       "The +X cap is physically harmless: the board has only 0.25 mm of slack in X and the module cannot "
                                       "hang off the board end, so the lens cannot move more than about +1.0 mm toward +X.")
def test_lens_window_tolerates_4mm_everywhere(comb):
    for fn in (_barrel, _module):
        for dx, dr in ((4.0, 0), (-4.0, 0), (0, 4.0), (0, -4.0)):
            assert vol_int(fn(dx, dr), comb) < 1e-4, (fn.__name__, dx, dr)


def test_lens_plus_x_cap_does_not_matter(comb):
    """Physically reachable +X lens shift = board slack in the pocket (0.25) + module flush with the board end (lens centre >= 4.25 from the
    end, nominal 5.0 -> 0.75) = 1.0 mm: inside the +2.0 (module) / +2.25 (barrel) the window gives."""
    assert 0.25 + (5.0 - 4.25) == pytest.approx(1.0)
    assert vol_int(_module(1.0, 0), comb) < 1e-4 and vol_int(_barrel(1.0, 0), comb) < 1e-4
    # the window end is capped 0.5 mm short of the pocket end wall (x = 11.0 vs 11.5): the module could not go further +X inside the pocket anyway
    assert LENS_DX + 1.0 + 4.25 <= 11.5


def test_usb_window_reachable_by_plug_8p5x7(comb):
    # control: a narrow 8.5 x 7 plug passes anywhere in the notch height range
    yc = 15.3
    b = Bx(9.0, 45.0, yc - 3.5, yc + 3.5, 90 - 4.25, 90 + 4.25)
    assert vol_int(b, comb) < 1e-3


def test_usb_window_passes_12x7_plug(comb, cover):
    """Round 3: 15 mm wide notch, sill 0.4 above the seat.  Typical USB-C overmould 12 x 6.5 (and 12 x 7, 13 x 8) reaches the
    receptacle (front face at x = 11.25) in place; centre height range with zero interference and lateral play are measured here."""
    def plug(yc, dr=0.0, w=12.0, h=6.5, x0=11.25):
        return Bx(x0, 60.0, yc - h / 2, yc + h / 2, 90 + dr - w / 2, 90 + dr + w / 2)
    for w, h in ((12.0, 6.5), (12.0, 7.0), (13.0, 8.0)):
        b = plug(15.3, 0.0, w, h)
        assert vol_int(b, comb) < 1e-4 and vol_int(b, cover) < 1e-4, (w, h)
    oks = [y for y in np.arange(12.0, 24.0, 0.05) if vol_int(plug(y), comb) < 1e-4 and vol_int(plug(y), cover) < 1e-4]
    assert (min(oks), max(oks)) == pytest.approx((13.55, 22.65), abs=0.06)       # plug centre height range; nominal receptacle centre 15.3
    assert vol_int(plug(15.3, 1.45), comb) < 1e-4 and vol_int(plug(15.3, 1.6), comb) > 1e-4   # lateral play +-1.5 (12 wide plug in the 15 notch)
    assert vol_int(plug(13.4), comb) > 1e-4                                                     # a plug centred only 3.5 above the seat touches the sill
    rec = Bx(2.0, 11.25, 15.3 - 1.63, 15.3 + 1.63, 90 - 4.47, 90 + 4.47)                     # receptacle 8.94 x 3.26
    assert vol_int(rec, comb) < 1e-4


def test_usb_window_geometry(mesh_comb, mesh_cover):
    """Open-top notch through the +X wall (x 11.5 .. 13.5), 15 wide, sill y = 10.3 (0.4 above the seat), closed on top by the cover."""
    ys = _along(mesh_comb, 1, 12.5, -90.0)                      # solid only below the sill
    assert list(np.round(ys, 2)) == [0.0, 10.3]
    assert 10.3 - 9.9 == pytest.approx(0.4, abs=0.01)
    for y in (11.0, 20.0, 26.0):
        rs = -_along(mesh_comb, 2, 12.5, y)[::-1]               # ... 82.5 [notch] 97.5 101.3
        assert (rs[-2] - rs[-3]) == pytest.approx(15.0, abs=0.02), y
        assert 0.5 * (rs[-2] + rs[-3]) == pytest.approx(90.0, abs=0.02)
    xs = _along(mesh_comb, 0, 15.0, -90.0)                       # notch passes the whole wall: no solid at y = 15 along x (vents on -X, notch on +X)
    assert len(xs) == 0
    cy = _along(mesh_cover, 1, 12.5, -90.0)                      # the cover plate (underside y = 26.9) roofs the notch
    assert list(np.round(cy, 2)) == [26.9, 29.3]


def test_usb_notch_has_no_lintel(mesh_comb):
    """No wall above the connector opening (the 1.1 mm lintel is gone)."""
    ys = _along(mesh_comb, 1, 12.5, -90.0)
    assert len(ys) == 2 and ys[1] < 11.0


def test_cover_fasteners_and_fit(comb, cover, box, mesh_comb, mesh_cover):
    # M3 heat-set boss: OD 9.1 (>= 8), insert hole D4.1 x 7.0 deep (5.7 insert + 1.3 reserve), 2.5 mm wall; round 3: columns at x = 16.55
    xs = _along(mesh_comb, 0, 20.0, -70.0)
    assert list(np.round(xs, 2)) == [-21.1, -18.6, -14.5, -11.5, 11.5, 14.5, 18.6, 21.1]
    assert (xs[5] - xs[4]) == pytest.approx(3.0, abs=0.02)      # 3.0 mm between cavity and hole
    assert (xs[6] - xs[5]) == pytest.approx(4.1, abs=0.02)      # insert hole diameter
    assert (xs[7] - xs[6]) >= 2.5 - 0.02                         # outer boss wall
    assert 2 * (xs[7] - 0.5 * (xs[5] + xs[6])) == pytest.approx(9.1, abs=0.03)                  # boss OD 9.1 measured
    hole_x = _along(mesh_comb, 1, 16.55, -70.0)
    assert list(np.round(hole_x, 2)) == [0.0, 19.9]             # hole 7.0 deep from the cover seat y = 26.9
    assert 26.9 - 19.9 >= 5.7 + 1.0                              # insert M3 x 5.7 with >= 1 mm melt-in reserve
    # cover screw holes (D3.4) coaxial with the boss holes
    cx = _along(mesh_cover, 0, 27.5, -70.0)
    assert 0.5 * (cx[4] + cx[3]) == pytest.approx(16.55, abs=0.02)
    assert cx[4] - cx[3] == pytest.approx(3.4, abs=0.02)
    assert vol_int(cover, comb) < 1e-3                           # no interference
    assert dist(cover, box) >= 0.2                               # clear of the box wall (0.8 designed)
    # M3x8: 2.4 cover + 5.6 in the insert (insert 5.7 deep, hole 7.0 deep)
    assert 8.0 - 2.4 <= 7.0


# --------------------------------------------------------------------------- IMU
def test_imu_removed(comb, cover, body, mesh_comb):
    """D27 / round 3: no IMU pocket, pads, side blocks, pegs, pilots or vents; no CAMBAY_IMU_* parameter; the bay ends at r = 101.3."""
    assert [k for k in dir(P) if "IMU" in k.upper()] == []
    for fn in ("cad/params.py", "cad/parts/claw_camera_bay.py"):
        assert "CAMBAY_IMU" not in open(os.path.join(REPO, fn)).read(), fn
    for nm, shp in (("housing", comb), ("body", body), ("cover", cover)):
        bb = shp.BoundingBox()
        assert (OZ - bb.zmin) < 101.31, (nm, OZ - bb.zmin)                      # nothing beyond the XIAO end wall
        for f in shp.Faces():                                                    # no R1.05 IMU post / pilot cylinders
            a = BRepAdaptor_Surface(f.wrapped)
            if a.GetType() == GeomAbs_Cylinder:
                assert abs(a.Cylinder().Radius() - 1.05) > 1e-3
    assert vol_int(comb, Bx(-80, 80, -5, 60, 101.4, 200)) == 0.0 and vol_int(cover, Bx(-80, 80, -5, 60, 101.4, 200)) == 0.0
    assert _along(mesh_comb, 1, 0.0, -110.0).size == 0                             # nothing at all where the IMU pocket used to be (r 101 .. 130)
    # the three XIAO airflow slots in the -X cradle wall (not IMU vents) are still there: open at the slot centres, solid between them
    for r in (84.5, 90.0, 95.5):
        assert _along(mesh_comb, 0, 15.0, -r).size == 0, r
    assert list(np.round(_along(mesh_comb, 0, 15.0, -87.3), 2)) == [-13.5, -11.5]


def test_only_wire_window_removed_from_box(comb, box):
    """The only cut into the original box is the wire window and its flares (nothing near the bay end)."""
    rem = box.cut(comb)
    bb = rem.BoundingBox()
    assert bb.xmax - OX < 12.0 and OX - bb.xmin < 12.0
    assert (OZ - bb.zmin) < 64.0                                 # nothing removed beyond r = 64 (only the wire window cutter touches the box)


# --------------------------------------------------------------------------- min wall / printability
def _box_wall_r(y):
    """Radial position of the box outer wall (flange + R75 blend), vectorised: used to keep only bay facets."""
    y = np.asarray(y, float)
    dy = 39.68 - np.minimum(y, 39.68)
    r = 130.0 - np.sqrt(75.0 ** 2 - dy ** 2)
    return np.where(y <= 5.0, 63.5, r)


@pytest.fixture(scope="module")
def thickness_scan(comb):
    V, F = tess(comb, 0.03, 0.2)
    V = V - OFF
    c, t = inward_thickness(V, F, lambda c: (c[:, 0] > -45) & (c[:, 0] < 40) & (-c[:, 2] > _box_wall_r(c[:, 1]) + 1.0) & (c[:, 1] < 28) & (c[:, 1] > -0.1))
    return c, t


def _rib_zone(c):
    """facets of the 0.4 mm locating ribs (r 80.5 .. 81.2 and 98.8 .. 99.4, y 9.9 .. 18, |x| < 9.2)"""
    r = -c[:, 2]
    return (((r > 80.5) & (r < 81.2)) | ((r > 98.8) & (r < 99.4))) & (c[:, 1] > 9.8) & (c[:, 1] < 18.1) & (np.abs(c[:, 0]) < 9.2)


def test_min_wall_outside_ribs(thickness_scan):
    """Round 3: every wall of the bay other than the 0.4 mm locating ribs is >= 1.95 mm (design: 2.0)."""
    c, t = thickness_scan
    keep = ~_rib_zone(c)
    assert keep.sum() > 1400
    assert t[keep].min() >= 1.95, (t[keep].min(), c[keep][t[keep].argmin()])


@pytest.mark.xfail(strict=True, reason="R3-F1: in the SHIPPED export the second rib pair stands at x = -1.0 inside the |x| < 4 fence gap with no "
                                       "wall behind it: a free-standing 0.5 mm (x 1.2 mm) fin, 8 mm tall; the other ribs are 1.2 mm wide, not "
                                       "the 1.6 mm the module builds.  Regenerating the export from the module clears this.")
def test_min_wall_1p2_everywhere_including_ribs(thickness_scan):
    c, t = thickness_scan
    assert t.min() >= 1.2 - 0.02, (t.min(), c[t.argmin()])


def test_rib_defect_is_confined_to_the_stale_ribs(thickness_scan):
    c, t = thickness_scan
    thin = t < 1.1
    assert thin.sum() > 0 and _rib_zone(c[thin]).all()                       # every facet under 1.1 mm is on a locating rib
    assert t[thin].min() == pytest.approx(0.5, abs=0.02)
    assert np.all(np.abs(c[thin][:, 0] + 1.0) < 0.7)                         # the 0.5 mm fins are the x = -1.0 pair, in the wire gap
    # the other rib faces (x = -8.0) are only 1.2 mm wide (module: 1.6)
    rib = _rib_zone(c) & (np.abs(c[:, 0] + 8.0) < 0.7)
    assert rib.sum() > 0 and t[rib].min() == pytest.approx(1.2, abs=0.02)


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
    bay = (c[:, 0] > -45) & (c[:, 0] < 40) & (c[:, 2] < -44) & (c[:, 1] < 30) & (c[:, 1] > 0.05) & (area > 1e-4)
    over = np.where(bay & (n[:, 1] < -0.7072))[0]
    flat = over[n[over, 1] < -0.999]
    slanted = over[n[over, 1] >= -0.999]
    assert area[slanted].sum() < 80.0                           # only window flare roofs (<45 deg slopes tiny)
    # F2/F3: the USB notch is open-top, so it has no roof at all; the only wide bridge left is the wire window
    ys = _along_mesh(V, F, 1, 12.5, -90.0)
    assert len(ys) == 2                                          # sill only, nothing above
    assert pts_width_x(V, F, 18.95, -50.0) <= 5.2               # wire window roof flat span (5 mm)
    # every remaining downward-facing flat region is a tiny slot roof / window roof: report the largest
    if len(flat):
        assert area[flat].max() < 40.0


def test_cover_has_one_flat_face_for_printing(cover):
    """The outer face is one flat plane (cover prints face-down with lip / pegs / corral up).  Round 3: y = 29.3."""
    top = [f for f in cover.Faces() if abs(f.BoundingBox().ymin - f.BoundingBox().ymax) < 1e-6
           and abs(f.BoundingBox().ymax - (OY + 29.3)) < 1e-3]
    assert len(top) == 1
    flat_area = sum(f.Area() for f in top)
    plan = 27.0 * (101.3 - 56.52)                                # cover plate rectangle (approx., mm2) + two ears
    assert flat_area > 0.85 * plan and flat_area == pytest.approx(1276.9, abs=1.0)
    # nothing rises above the flat face
    assert cover.BoundingBox().ymax - OY == pytest.approx(29.3, abs=0.01)


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
    assert Ix == pytest.approx(15369, rel=0.03)                 # I of the round-3 section at r = 64 (bay now 26.9 tall)
    # outboard mass and its moment about the root section (r = 64)
    cut = cq.Workplane().box(200, 200, 200, centered=False).translate((OX - 100, OY - 50, OZ - root_r - 200)).val()
    pa, pc = added.intersect(cut), cover.intersect(cut)
    masses = [(pa.Volume() * PETG, OZ - pa.Center().z), (pc.Volume() * PETG, OZ - pc.Center().z),
              (5.0, 90.0), (3.0, 85.0)]                            # XIAO+Sense, wiring: assumed (no IMU, D27)
    M_w = sum(m * (r - root_r) for m, r in masses) * 1e-3        # kg*mm
    arm = 101.3 - root_r
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
    assert m_bay + m_cov < 20.0
    assert m_bay + m_cov == pytest.approx(19.1, abs=0.2)         # NET of the window cut (round 3; was 28.7 g with the IMU pocket)
    assert m_bay == pytest.approx(14.56, abs=0.1) and m_cov == pytest.approx(4.57, abs=0.05)
    assert (comb.Volume() - box.Volume() + 1050.9) * PETG + m_cov == pytest.approx(20.46, abs=0.2)   # gross


# =========================================================================== ROUND 2 additions (independent)
def test_r2_thin_wall_unmasked_scan(comb, cover):
    """Own sampling, no 'near box wall' exclusion: facets of the bay (r beyond the box wall) and of the cover.
    Round 3: the locating ribs are excluded from the 1.95 mm floor (they are 0.4 mm proud by design; see the rib findings)."""
    off = OFF
    V, F = tess(comb, 0.02, 0.15)
    V = V - off
    wall = _box_wall_r
    c, t = inward_thickness(V, F, lambda c: (c[:, 0] > -45) & (c[:, 0] < 40) & (-c[:, 2] > wall(c[:, 1])) & (c[:, 1] < 28) & (c[:, 1] > -0.1), minarea=0.02)
    keep = ~_rib_zone(c)
    assert len(t) > 1500 and t[keep].min() >= 1.95, (t[keep].min(), c[keep][t[keep].argmin()])
    Vc, Fc = tess(cover, 0.02, 0.15)
    c2, t2 = inward_thickness(Vc - off, Fc, lambda c: np.ones(len(c), bool), minarea=0.02)
    assert len(t2) > 1000 and t2.min() >= 1.95, (t2.min(), c2[t2.argmin()])


def test_r2_cover_stl_flat_on_bed_no_overhang():
    T = load_stl(os.path.join(STL, "claw_camera_bay_cover.stl"))
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    a = 0.5 * np.linalg.norm(n, axis=1)
    n = n / np.linalg.norm(n, axis=1)[:, None]
    z = T[:, :, 2]
    bed = (np.abs(z).max(1) < 1e-3) & (n[:, 2] < -0.99)
    over = (n[:, 2] < -0.7072) & (z.min(1) > 0.01)
    step = cq.importers.importStep(os.path.join(STEP, "claw_camera_bay_cover.step")).val()
    top = sum(f.Area() for f in step.Faces() if abs(f.BoundingBox().ymin - f.BoundingBox().ymax) < 1e-6
              and abs(f.BoundingBox().ymax - f.BoundingBox().ymin) < 1e-6 and abs(f.BoundingBox().ymax - (OY + 29.3)) < 1e-3)
    assert abs(z.min()) < 1e-3
    assert a[bed].sum() == pytest.approx(top, rel=0.01)           # whole outer face is on the bed
    assert a[over].sum() < 1e-6                                   # nothing overhangs once printed face-down


# ---- realistic cable lines (own implementation; config/robot.sim.json read-only)
@pytest.fixture(scope="module")
def realistic(box, comb, cover):
    import json
    cfg = json.load(open(os.path.join(REPO, "config", "robot.sim.json")))
    W, D, Hh = cfg["room"]["width_m"] * 1000, cfg["room"]["depth_m"] * 1000, cfg["room"]["height_m"] * 1000
    mg, cm = cfg["motion"]["workspace_margin_m"] * 1000, cfg["motion"]["ceiling_margin_m"] * 1000
    anch = {s["id"]: np.array(s["anchor_room_m"]) * 1000 for s in cfg["stations"]}
    added = comb.cut(box)
    Va, Fa = tess(added, 0.05, 0.2)
    Vc, Fc = tess(cover, 0.05, 0.2)
    V = np.concatenate([Va, Vc]) - OFF
    F = np.concatenate([Fa, Fc + len(Va)])
    Vb, Fb = tess(box, 0.3, 0.3)
    return dict(W=W, D=D, H=Hh, mg=mg, cm=cm, anch=anch, V=V, F=F, Vb=Vb - OFF, Fb=Fb)


def _realistic_hits(rz, psi0_deg, delta_deg):
    W, D, Hh, mg, cm, anch = rz["W"], rz["D"], rz["H"], rz["mg"], rz["cm"], rz["anch"]
    corners = [(1, 1), (1, -1), (-1, -1), (-1, 1)]
    mouth, my = 54.09, 14.05

    def vec(psi, bx, bz):
        return bx * np.array([math.cos(psi), math.sin(psi)]) + bz * np.array([math.sin(psi), -math.cos(psi)])
    cen = np.array([W / 2, D / 2])
    psi0 = math.radians(psi0_deg)
    mapping = {}
    for c in corners:                                         # nearest corner diagonal at the installed yaw
        v = vec(psi0, c[0], c[1])
        az = math.atan2(v[1], v[0])
        mapping[c] = min(anch, key=lambda k: abs((math.atan2(*(anch[k][:2] - cen)[::-1]) - az + math.pi) % (2 * math.pi) - math.pi))
    psi = math.radians(psi0_deg + delta_deg)
    ex, ez = np.array([math.cos(psi), math.sin(psi)]), np.array([math.sin(psi), -math.cos(psi)])
    xs, ys, zs = np.linspace(mg, W - mg, 8), np.linspace(mg, D - mg, 7), np.linspace(523.8, Hh - cm, 6)
    hits = feas = 0
    zhit = []
    for c in corners:
        a = anch[mapping[c]]
        h = mouth * (c[0] * ex + c[1] * ez)
        D_, L, pz = [], [], []
        for px in xs:
            for py in ys:
                for z in zs:
                    d = np.array([a[0] - (px + h[0]), a[1] - (py + h[1]), a[2] - z])
                    l = np.linalg.norm(d)
                    D_.append([d[:2] @ ex / l, d[2] / l, d[:2] @ ez / l])
                    L.append(l)
                    pz.append(z)
        D_, L, pz = np.array(D_), np.array(L), np.array(pz)
        o = np.array([c[0] * mouth, my, c[1] * mouth])
        tb = np.array([mt_first_hit(o + d * 0.6, d[None], rz["Vb"], rz["Fb"])[0] for d in D_])
        feasible = ~(tb < L)
        t = mt_first_hit(o, D_, rz["V"], rz["F"])
        hit = (t < L) & feasible
        hits += int(hit.sum())
        feas += int(feasible.sum())
        zhit += list(pz[hit])
    return hits, feas, zhit, mapping


@pytest.mark.parametrize("psi0", [0, 90])
@pytest.mark.parametrize("delta", [-15, 0, 15])
def test_r2_realistic_lines_clear_within_15deg_yaw(realistic, psi0, delta):
    hits, feas, _, _ = _realistic_hits(realistic, psi0, delta)
    assert feas == 1344 and hits == 0


@pytest.mark.parametrize("psi0", [0, 90, 180, 270])
@pytest.mark.parametrize("delta", [-30, 30])
def test_r3_realistic_lines_clear_at_30deg_yaw(realistic, psi0, delta):
    """Round 3 (bay now ends at r 101.3): the +-30 deg hits of round 2 (2 per case) are gone."""
    hits, feas, _, _ = _realistic_hits(realistic, psi0, delta)
    assert feas == 1344 and hits == 0


@pytest.mark.xfail(strict=True, reason="F6 (narrowed in round 3): at |yaw| >= 45 deg from the installed orientation, lines of the two stations on "
                                       "the bay side still hit the bay near the ceiling margin (5 hits at psi0 = 0/180, 7 at 90/270; round 2: 7)")
@pytest.mark.parametrize("delta", [-45, 45])
def test_r2_realistic_lines_clear_at_45deg_yaw(realistic, delta):
    hits, _, _, _ = _realistic_hits(realistic, 0, delta)
    assert hits == 0


def test_r2_hits_only_at_top_of_workspace(realistic):
    hits, feas, zhit, _ = _realistic_hits(realistic, 90, 45)
    assert hits > 0 and min(zhit) >= 1.9e3                      # claw reference >= 1.98 m (top two z levels)
    hits2, _, _, _ = _realistic_hits(realistic, 90, 0)
    assert hits2 == 0


# =========================================================================== ROUND 3 additions (independent)
PREV_COMMIT = "1c2e968"          # last commit before the IMU removal / D28


def _prev_step(name, tmp_path):
    out = subprocess.run(["git", "-C", REPO, "show", f"{PREV_COMMIT}:exports/step/{name}.step"], capture_output=True)
    if out.returncode != 0 or not out.stdout:
        pytest.skip("previous export not available from git")
    p = tmp_path / (name + ".step")
    p.write_bytes(out.stdout)
    return str(p)


def test_r3_unchanged_regions_vs_previous_export(box, comb, tmp_path):
    """Everything outside the bay zone (|x| <= 36, r 50 .. 131, y < 40) is identical to the previous export: corner cable holes,
    lid seat, rim, the +Z half, the box interior and the wire window cut."""
    old = cq.importers.importStep(_prev_step("gripper_electric_housing_with_camera_bay", tmp_path)).val()
    a, b = comb.cut(old), old.cut(comb)
    zone = Bx(-36, 36, -1, 40, 50.0, 131.0)
    assert a.cut(zone).Volume() < 0.01 and b.cut(zone).Volume() < 0.01
    assert vol_int(a, Bx(-200, 200, 27, 100, -200, 200)) < 0.01 and vol_int(b, Bx(-200, 200, 27, 100, -200, 200)) < 0.01
    assert box.cut(old).cut(box.cut(comb)).Volume() < 0.01 and box.cut(comb).cut(box.cut(old)).Volume() < 0.01   # same wire window
    assert box.cut(comb).Volume() == pytest.approx(1050.94, abs=0.05)
    ho, hn = hole_faces(old), hole_faces(comb)
    assert len(ho) == len(hn) and len(hn) in (4, 8)                          # 4 full bores in the exports (8 half faces in the v6 STEP)
    assert sum(f.Area() for f in ho) == pytest.approx(sum(f.Area() for f in hn), abs=0.01)
    # the bay got smaller and lighter
    assert comb.Volume() < old.Volume() - 4000.0


def test_r3_cover_unchanged_in_plan_height_but_shorter(cover):
    bb = cover.BoundingBox()
    assert (OZ - bb.zmin) == pytest.approx(101.3, abs=0.01) and (OZ - bb.zmax) == pytest.approx(56.52, abs=0.02)
    assert bb.ymin - OY == pytest.approx(20.9, abs=0.01) and bb.ymax - OY == pytest.approx(29.3, abs=0.01)


# ---- D28: preview with the 50 mm tube cut
D28_CUT = 50.0


@pytest.fixture(scope="module")
def previews(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("prev")
    new = cq.importers.importStep(os.path.join(STEP, "gripper_v7_preview.step")).solids().vals()
    out = subprocess.run(["git", "-C", REPO, "show", f"{PREV_COMMIT}:exports/step/gripper_v7_preview.step"], capture_output=True)
    if out.returncode != 0 or not out.stdout:
        pytest.skip("previous preview not available from git")
    p = tmp / "old_preview.step"
    p.write_bytes(out.stdout)
    old = cq.importers.importStep(str(p)).solids().vals()
    return old, new


def _bb(s):
    b = s.BoundingBox()
    return np.array([b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax])


def test_d28_tube_length_and_ends(previews):
    old, new = previews
    assert len(old) == len(new) == 59
    # the tube is the only 28.54 mm round solid taller than 200 mm in the preview
    tn = [s for s in new if abs(sorted([_bb(s)[1] - _bb(s)[0], _bb(s)[3] - _bb(s)[2], _bb(s)[5] - _bb(s)[4]])[0] - 28.54) < 0.05
          and max(_bb(s)[3] - _bb(s)[2], _bb(s)[1] - _bb(s)[0], _bb(s)[5] - _bb(s)[4]) > 200]
    to = [s for s in old if abs(sorted([_bb(s)[1] - _bb(s)[0], _bb(s)[3] - _bb(s)[2], _bb(s)[5] - _bb(s)[4]])[0] - 28.54) < 0.05
          and max(_bb(s)[3] - _bb(s)[2], _bb(s)[1] - _bb(s)[0], _bb(s)[5] - _bb(s)[4]) > 200]
    assert len(tn) == 1 and len(to) == 1
    bn, bo = _bb(tn[0]), _bb(to[0])
    assert bn[3] - bn[2] == pytest.approx(254.8, abs=0.01)
    assert bn[2] == pytest.approx(786.39, abs=0.01) and bn[3] == pytest.approx(1041.19, abs=0.01)     # lower end fixed, top 50 lower
    assert bo[2] == pytest.approx(786.39, abs=0.01) and bo[3] == pytest.approx(1091.19, abs=0.01)
    assert bn[[0, 1, 4, 5]] == pytest.approx(bo[[0, 1, 4, 5]], abs=1e-4)
    # tube volume change = annulus x 50
    ann = math.pi * (14.27 ** 2 - 11.27 ** 2)
    assert (to[0].Volume() - tn[0].Volume()) == pytest.approx(ann * D28_CUT, rel=2e-3)
    assert P.GRIPV7_TUBE_LEN == 254.8 and P.GRIPV7_TUBE_LEN_V6 - P.GRIPV7_TUBE_LEN == pytest.approx(D28_CUT)


def test_d28_only_the_four_parts_moved_exactly_50(previews, comb, cover):
    old, new = previews
    moved, same = [], 0
    for i, (a, b) in enumerate(zip(old, new)):
        da = _bb(b) - _bb(a)
        if np.abs(da).max() < 1e-4 and abs(b.Volume() - a.Volume()) < 1e-4 * max(1.0, a.Volume()):
            same += 1
        else:
            moved.append((i, da, b.Volume() - a.Volume()))
    assert same == 55 and len(moved) == 4, [(i, np.round(d, 3)) for i, d, _ in moved]
    byi = {i: (d, dv) for i, d, dv in moved}
    assert set(byi) == {55, 56, 57, 58}                                          # tube, Griper Cylinder, box+bay, cover (order in the file)
    # Griper Cylinder: rigid -50 in y, nothing else
    d, dv = byi[56]
    assert d == pytest.approx([0, 0, -D28_CUT, -D28_CUT, 0, 0], abs=1e-4) and abs(dv) < 1e-3
    assert new[56].cut(old[56].moved(cq.Location(cq.Vector(0, -D28_CUT, 0)))).Volume() < 0.01
    # box+bay and cover: exactly the CURRENT exports shifted by -50 in y
    for idx, ex in ((57, comb), (58, cover)):
        bb, be = _bb(new[idx]), _bb(ex)
        assert bb - be == pytest.approx([0, 0, -D28_CUT, -D28_CUT, 0, 0], abs=1e-4)
        sh = ex.moved(cq.Location(cq.Vector(0, -D28_CUT, 0)))
        assert new[idx].cut(sh).Volume() < 0.01 and sh.cut(new[idx]).Volume() < 0.01


def test_d28_no_new_interference_between_moved_parts_and_head_or_tube(previews):
    old, new = previews

    def inter(A, B):
        a, b = _bb(A), _bb(B)
        if (a[1] < b[0] or b[1] < a[0] or a[3] < b[2] or b[3] < a[2] or a[5] < b[4] or b[5] < a[4]):
            return 0.0
        return A.intersect(B).Volume()

    def table(S):
        out = {}
        for i in (55, 56, 57, 58):
            for j in range(len(S)):
                if j == i or (j in (55, 56, 57, 58) and j < i):
                    continue
                v = inter(S[i], S[j])
                if v > 1e-3:
                    out[(i, j)] = round(v, 3)
        return out

    tn, to = table(new), table(old)
    assert set(tn) == set(to), (tn, to)                          # same touching pairs as before the cut
    assert all(abs(tn[k] - to[k]) < 0.002 for k in tn), (tn, to)  # coincident-face noise only: tube/cylinder 0.037, cylinder/box 0.004-0.005 mm3
    assert max(tn.values()) < 0.05


def test_d28_lens_clearance_to_head_unchanged_geometry_sanity(previews):
    """The moved box sits on the tube top: box bottom plane = tube top = world y 1041.19."""
    _, new = previews
    assert _bb(new[57])[2] == pytest.approx(1041.19, abs=0.01)
    assert _bb(new[55])[3] == pytest.approx(1041.19, abs=0.01)
