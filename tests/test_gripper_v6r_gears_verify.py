"""
Independent verification of the "v6r" gears (Jasper's v6 gears converted to a 2:1 gearbox).

Written by the geometry-verifier, NOT by the implementer.  Nothing is measured with the implementer's builder or its
helper functions (cad.parts.gripper_v6r_gears is imported only by test_83, the "delivered files are current" check).
Every number is measured from:
  * his originals  (solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP through cad.v6_loader), and
  * the delivered files exports/step/gripper_v6r_*.step and exports/stl/gripper_v6r_*.stl.

Run (about 8 min):   /usr/bin/python3 -m pytest -q -s tests/test_gripper_v6r_gears_verify.py
`-s` prints the expected / measured table at the end (one row per check).
"""

from __future__ import annotations

import hashlib
import math
import os
import struct
import subprocess
import tempfile

import numpy as np
import pytest

cq = pytest.importorskip("cadquery")

from matplotlib.path import Path as MPath                    # noqa: E402
from scipy.spatial import cKDTree                            # noqa: E402
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface   # noqa: E402
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section              # noqa: E402
from OCP.BRepTools import BRepTools                          # noqa: E402
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane      # noqa: E402

from cad import params as P                                  # noqa: E402
from cad.parts import gripper_v7_kin as K                    # noqa: E402
from cad.v6_loader import V6_STEP, find, load_v6             # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = 1.5
PETG = 1.27                                   # g/cc
STEP_NAMES = {"pinion": "pinion", "compound": "compound_36T_24T", "compound_norelief": "compound_36T_24T_norelief",
              "follower": "follower"}
C_XY = (P.GRIPV6R_CD_SYNC / 2.0, 0.0)         # placement frame: compound axis (36.30 / 2)
F_XY = (-C_XY[0], 0.0)
S_XY = P.GRIPV6R_S_XY                         # pinion axis (10, 39.978): 40.80 from the compound axis
RESULTS: list = []


# ---------------------------------------------------------------------------------------------------------------
# bookkeeping
# ---------------------------------------------------------------------------------------------------------------
def chk(cid, item, expected, measured, tol, ok):
    RESULTS.append((cid, item, expected, measured, tol, "PASS" if ok else "FAIL"))
    return ok


def num(cid, item, expected, measured, tol):
    return chk(cid, item, "%.6g" % expected, "%.6g" % measured, "+-%.3g" % tol, abs(measured - expected) <= tol)


def ge(cid, item, minimum, measured):
    return chk(cid, item, ">= %.6g" % minimum, "%.6g" % measured, "", measured >= minimum)


def fails_since(n0):
    return [r for r in RESULTS[n0:] if r[5] == "FAIL"]


@pytest.fixture(scope="session", autouse=True)
def _print_table():
    yield
    print("\n\n==== v6r gears verification table (id | item | expected | measured | tol | status) ====")
    for r in RESULTS:
        print(" | ".join(str(x) for x in r))
    print("==== %d checks, %d FAIL ====" % (len(RESULTS), sum(1 for r in RESULTS if r[5] == "FAIL")))


# ---------------------------------------------------------------------------------------------------------------
# geometry helpers (own implementation)
# ---------------------------------------------------------------------------------------------------------------
def rotz(s, deg, about=(0.0, 0.0)):
    return s.rotate(cq.Vector(about[0], about[1], 0), cq.Vector(about[0], about[1], 1), deg)


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def cyl(r, z0, z1, x=0.0, y=0.0):
    return cq.Solid.makeCylinder(r, z1 - z0, cq.Vector(x, y, z0))


def vol(s):
    try:
        return float(s.Volume()) if s.Solids() else 0.0
    except Exception:
        return 0.0


def common(a, b):
    return vol(a.intersect(b))


def place(s, axis, deg):
    return rotz(s, deg).moved(cq.Location(cq.Vector(axis[0], axis[1], 0.0)))


def axis_of_tip(s, r):
    for f in s.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Cylinder and abs(a.Cylinder().Radius() - r) < 1e-3:
            loc = a.Cylinder().Axis().Location()
            return loc.X(), loc.Y()
    raise RuntimeError("no cylinder R%g" % r)


def homed(name, r_tip):
    """His solid, translated so its gear axis is the z axis and the stack bottom is z = 0 (no rotation)."""
    s = find(load_v6(), name)
    ax = axis_of_tip(s, r_tip)
    return s.moved(cq.Location(cq.Vector(-ax[0], -ax[1], -P.GRIPV6R_SRC_Z0))), ax


def census(s):
    """Cylinders {(R, x, y, z0, z1): (faces, area)} and horizontal planes {(z, +-1): (faces, area)}."""
    cy, pl = {}, {}
    BRepTools.Clean_s(s.wrapped)
    for f in s.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        bb = f.BoundingBox()
        if a.GetType() == GeomAbs_Cylinder:
            c = a.Cylinder()
            l = c.Axis().Location()
            k = (round(c.Radius(), 4), round(l.X(), 3), round(l.Y(), 3), round(bb.zmin, 3), round(bb.zmax, 3))
            n0, a0 = cy.get(k, (0, 0.0))
            cy[k] = (n0 + 1, a0 + f.Area())
        elif a.GetType() == GeomAbs_Plane:
            n = a.Plane().Axis().Direction()
            if abs(abs(n.Z()) - 1) < 1e-6:
                k = (round(a.Plane().Location().Z(), 3), 1 if n.Z() > 0 else -1)
                n0, a0 = pl.get(k, (0, 0.0))
                pl[k] = (n0 + 1, a0 + f.Area())
    return cy, pl


def agg_cyl(s):
    """Cylinder census with positions removed: on-axis / off-axis {(R, z0, z1): [faces, area]}."""
    cy, _ = census(s)
    on, off = {}, {}
    for (r, x, y, z0, z1), (n, a) in cy.items():
        d = on if math.hypot(x, y) < 0.01 else off
        v = d.setdefault((r, z0, z1), [0, 0.0])
        v[0] += n
        v[1] += a
    return on, off


def off_axis_centres(s, r):
    out = set()
    for f in s.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() == GeomAbs_Cylinder and abs(a.Cylinder().Radius() - r) < 1e-3:
            l = a.Cylinder().Axis().Location()
            if math.hypot(l.X(), l.Y()) > 0.01:
                out.add((round(l.X(), 3), round(l.Y(), 3)))
    return out


def loops_at(shape, z, step=0.02):
    pl = cq.Face.makePlane(800, 800, basePnt=(0, 0, z), dir=(0, 0, 1))
    sec = BRepAlgoAPI_Section(shape.wrapped, pl.wrapped)
    sec.Build()
    polys = []
    for e in cq.Shape.cast(sec.Shape()).Edges():
        c = BRepAdaptor_Curve(e.wrapped)
        a, b = c.FirstParameter(), c.LastParameter()
        n = max(2, int(math.ceil(e.Length() / step)) + 1)
        pts = [c.Value(a + (b - a) * u) for u in np.linspace(0, 1, n)]
        polys.append(np.array([[p.X(), p.Y()] for p in pts]))
    ends = np.vstack([np.vstack([p[0], p[-1]]) for p in polys])
    tree = cKDTree(ends)
    used = np.zeros(len(polys), bool)
    out = []
    for i0 in range(len(polys)):
        if used[i0]:
            continue
        used[i0] = True
        loop = [polys[i0]]
        s0, e0 = polys[i0][0], polys[i0][-1]
        while np.hypot(*(e0 - s0)) > 3e-4:
            nxt = None
            for j in tree.query_ball_point(e0, 3e-4):
                if not used[j // 2]:
                    nxt = j
                    break
            if nxt is None:
                break
            used[nxt // 2] = True
            e = polys[nxt // 2]
            e = e if nxt % 2 == 0 else e[::-1]
            loop.append(e)
            e0 = e[-1]
        out.append(np.vstack(loop))
    return out


def parea(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def outer(shape, z, step=0.02):
    return max(loops_at(shape, z, step), key=lambda p: abs(parea(p)))


def rot2(p, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.stack([p[:, 0] * c - p[:, 1] * s, p[:, 0] * s + p[:, 1] * c], 1)


# ---------------------------------------------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def new():
    return {k: cq.importers.importStep(os.path.join(REPO, "exports", "step", "gripper_v6r_%s.step" % v)).val()
            for k, v in STEP_NAMES.items()}


@pytest.fixture(scope="module")
def his():
    pin, a1 = homed(P.GRIPV6R_SRC_PINION, 15.0)
    com, a2 = homed(P.GRIPV6R_SRC_COMPOUND, 19.5)
    fol, a3 = homed(P.GRIPV6R_SRC_FOLLOWER, 19.5)
    return dict(pinion=pin, compound=com, follower=fol, axes=dict(pinion=a1, compound=a2, follower=a3))


@pytest.fixture(scope="module")
def outlines(new):
    """Mid-face section outlines (part frame, closed-pose orientation) of the meshing layers."""
    return dict(pin=outer(new["pinion"], 8.0, 0.04), ring=outer(new["compound"], 8.0, 0.04),
                sc=outer(new["compound"], 31.0, 0.04), sf=outer(new["follower"], 31.0, 0.04))


# =================================================================================================================
# 0. source untouched, files present
# =================================================================================================================
def test_00_source_step_untouched_and_files_present():
    n0 = len(RESULTS)
    with open(V6_STEP, "rb") as fh:
        h_now = hashlib.sha256(fh.read()).hexdigest()
    rel = os.path.relpath(V6_STEP, REPO)
    blob = subprocess.run(["git", "-C", REPO, "show", "HEAD:" + rel], capture_output=True)
    if blob.returncode == 0:
        h_git = hashlib.sha256(blob.stdout).hexdigest()
        chk("0.1", "his STEP sha256 equals the git HEAD blob", h_git[:16], h_now[:16], "exact", h_git == h_now)
    for n in STEP_NAMES.values():
        for kind in ("step", "stl"):
            p = os.path.join(REPO, "exports", kind, "gripper_v6r_%s.%s" % (n, kind))
            chk("0.2", "file exists %s" % os.path.basename(p), "exists", "exists" if os.path.isfile(p) else "MISSING", "",
                os.path.isfile(p))
    assert not fails_since(n0)


# =================================================================================================================
# 1. validity, single solid, bbox, volume, mass
# =================================================================================================================
def test_10_single_valid_solids_bbox_volume(new, his):
    n0 = len(RESULTS)
    hb = his["pinion"].BoundingBox()
    pivot_y = -P.GRIPV7_CRANK_R * math.sin(math.radians(-P.GRIPV7_THETA_CLOSED))      # lug pivot y at the closed pose
    exp = dict(pinion=(hb.xlen, hb.ylen, 16.0),
               compound=(None, 28.4835 - (pivot_y - 9.15), 36.0),                    # ring tip envelope .. lug boss R9.15
               compound_norelief=(None, 28.4835 - (pivot_y - 9.15), 36.0),
               follower=(None, 19.4815 - (pivot_y - 9.165), 20.0))                  # 24T tip envelope .. lug boss R9.165
    for k, s in new.items():
        chk("1.1", "%s valid BREP" % k, "True", str(s.isValid()), "", s.isValid())
        chk("1.2", "%s solid count" % k, "1", str(len(s.Solids())), "", len(s.Solids()) == 1)
        ge("1.3", "%s volume > 0 (mm3)" % k, 1.0, s.Volume())
        bb = s.BoundingBox()
        e = exp[k]
        if e[0] is not None:
            num("1.4", "%s bbox x-size = his pinion (mm)" % k, e[0], bb.xlen, 1e-3)
        num("1.5", "%s bbox y-size (derived from lug R53 / tip envelope) (mm)" % k, e[1], bb.ylen, 0.02)
        num("1.6", "%s bbox z-size (stack height) (mm)" % k, e[2], bb.zlen, 1e-3)
        num("1.7", "%s bbox z-min (mm)" % k, 16.0 if k == "follower" else 0.0, bb.zmin, 1e-3)
    num("1.8", "compound x-size = 36T tooth envelope <= 57.0 (mm)", 57.0, new["compound"].BoundingBox().xlen, 0.05)
    assert not fails_since(n0)


# =================================================================================================================
# 2. pinion identical to his (placement only)
# =================================================================================================================
def test_20_pinion_identical(new, his):
    n0 = len(RESULTS)
    h, n = his["pinion"], new["pinion"]
    num("2.1", "pinion volume vs his (mm3)", h.Volume(), n.Volume(), 1e-3)
    num("2.2", "pinion area vs his (mm2)", h.Area(), n.Area(), 1e-2)
    cv = common(h, n)
    chk("2.3", "pinion boolean his minus new (mm3)", "0", "%.5f" % (h.Volume() - cv), "+-0.01", abs(h.Volume() - cv) < 0.01)
    chk("2.4", "pinion boolean new minus his (mm3)", "0", "%.5f" % (n.Volume() - cv), "+-0.01", abs(n.Volume() - cv) < 0.01)
    oh, fh = agg_cyl(h)
    on, fn = agg_cyl(n)
    same = set(oh) == set(on) and set(fh) == set(fn) \
        and all(abs(oh[k][1] - on[k][1]) < 0.01 and oh[k][0] == on[k][0] for k in oh) \
        and all(abs(fh[k][1] - fn[k][1]) < 0.01 and fh[k][0] == fn[k][0] for k in fh)
    chk("2.5", "pinion cylinder census (R, z range, faces, area) vs his", "identical", "identical" if same else "DIFFERENT", "", same)
    num("2.6", "pinion bore diameter (mm)", 8.0, 2 * min(k[0] for k in on if k[0] < 5), 1e-4)
    num("2.7", "pinion tip diameter (mm)", 30.0, 2 * max(k[0] for k in on), 1e-4)
    num("2.8", "pinion root diameter (mm)", 23.25, 2 * sorted(k[0] for k in on)[1], 1e-4)
    num("2.9", "pinion face width (mm)", 16.0, n.BoundingBox().zlen, 1e-4)
    # orientation unchanged: tooth phase of his pinion versus the delivered one
    ph_h = _phase(outer(h, 8.0, 0.01), 18)
    ph_n = _phase(outer(n, 8.0, 0.01), 18)
    num("2.10", "pinion tooth phase deg (his orientation kept)", ph_h, ph_n, 1e-4)
    assert not fails_since(n0)


def _phase(pts, n):
    r = np.hypot(pts[:, 0], pts[:, 1])
    tip = pts[r > r.max() - 2e-3]
    a = np.arctan2(tip[:, 1], tip[:, 0])
    return math.degrees(np.angle(np.exp(1j * n * a).sum()) / n)


# =================================================================================================================
# 3. compound and follower: feature-by-feature against his solids
# =================================================================================================================
def _classified_cyl_diff(h, n):
    oh, fh = agg_cyl(h)
    on, fn = agg_cyl(n)
    diffs = []
    for nm, a, b in (("on-axis", oh, on), ("off-axis", fh, fn)):
        for k in sorted(set(a) | set(b)):
            va, vb = a.get(k, [0, 0.0]), b.get(k, [0, 0.0])
            if abs(va[1] - vb[1]) > 0.01:
                diffs.append((nm, k, va, vb))
    return diffs, oh, on, fh, fn


def test_30_compound_feature_diff(new, his):
    n0 = len(RESULTS)
    for var in ("compound", "compound_norelief"):
        diffs, oh, on, fh, fn = _classified_cyl_diff(his["compound"], new[var])
        intended, unintended = [], []
        for nm, k, va, vb in diffs:
            R_, z0, z1 = k
            if nm == "on-axis" and R_ in (38.625, 42.0) and va[0] == 54:
                intended.append("54T root/tip cylinders removed")
            elif nm == "on-axis" and R_ in (25.125, 28.5) and vb[0] == 36:
                intended.append("36T root/tip cylinders added")
            elif nm == "off-axis" and R_ == 0.4 and va[0] == 108:
                intended.append("108 R0.4 root fillets removed")
            elif nm == "off-axis" and R_ == 0.4 and vb[0] == 72:
                intended.append("72 R0.4 root fillets added")
            elif nm == "off-axis" and R_ == 6.0:
                intended.append("lightening holes %d -> %d faces" % (va[0], vb[0]))
            elif var == "compound" and nm == "on-axis" and R_ == 16.5 and abs(z0 - 15.7) < 1e-3 and abs(z1 - 16.0) < 1e-3:
                intended.append("0.30 relief wall R16.5")
            else:
                unintended.append((nm, k, va, vb))
        chk("3.1", "%s: UNINTENDED cylinder-census differences vs his (all others: %d intended)" % (var, len(intended)),
            "none", str(unintended) if unintended else "none", "", not unintended)
        for (R_, z0, z1, label) in ((7.0375, 1.95, 7.0, "lower bearing pocket Ø14.075 (5.05 deep)"),
                                    (7.0375, 24.0, 34.05, "upper bearing pocket Ø14.075 (10.05 deep)"),
                                    (7.0, 0.0, 1.95, "lower entry lip Ø14.000 x 1.95"),
                                    (7.0, 34.05, 36.0, "upper entry lip Ø14.000 x 1.95"),
                                    (4.15, 7.0, 24.0, "centre shoulder Ø8.30")):
            hit = [k for k in on if abs(k[0] - R_) < 1e-4 and abs(k[1] - z0) < 1e-3 and abs(k[2] - z1) < 1e-3]
            ok = len(hit) == 1 and abs(on[hit[0]][1] - oh[hit[0]][1]) < 0.01
            chk("3.2", "%s: %s present and equal to his" % (var, label), "R%.4f z%.3f..%.3f" % (R_, z0, z1), str(hit), "", ok)
        cen = off_axis_centres(new[var], 6.0)
        chk("3.3", "%s: lightening holes (7 x Ø12)" % var, "7", str(len(cen)), "", len(cen) == 7)
        rr = sorted({round(math.hypot(x, y), 2) for x, y in cen})
        chk("3.4", "%s: lightening circle radius (mm)" % var, "[16.7]", str(rr), "+-0.005", rr == [16.7])
        _, pl = census(new[var])
        levels = sorted({z for (z, s_), (nn, a) in pl.items() if a > 20 or z in (1.95, 34.05)})
        exp_levels = [0.0, 1.95, 7.0, 15.7, 16.0, 24.0, 26.0, 34.05, 36.0] if var == "compound" else \
            [0.0, 1.95, 7.0, 16.0, 24.0, 26.0, 34.05, 36.0]
        chk("3.5", "%s: Z layers (ring top / relief floor, 24T layer 16..36, lug band 16..26, pockets)" % var,
            str(exp_levels), str(levels), "", levels == exp_levels)
    assert not fails_since(n0)


def test_31_follower_feature_diff(new, his):
    n0 = len(RESULTS)
    diffs, oh, on, fh, fn = _classified_cyl_diff(his["follower"], new["follower"])
    chk("3.6", "follower: cylinder census differences vs his", "none", str(diffs) if diffs else "none", "", not diffs)
    for (R_, z0, z1, label) in ((7.0375, 24.0, 34.075, "upper bearing pocket Ø14.075 (10.075 deep)"),
                                (7.0, 34.075, 36.0, "upper lip Ø14.000"), (4.165, 16.0, 24.0, "centre shoulder Ø8.33")):
        hit = [k for k in on if abs(k[0] - R_) < 1e-4 and abs(k[1] - z0) < 1e-3 and abs(k[2] - z1) < 1e-3]
        chk("3.7", "follower: %s present" % label, "R%.4f z%.3f..%.3f" % (R_, z0, z1), str(hit), "", len(hit) == 1)
    assert not fails_since(n0)


def _arm_regions(s_home, s_new, arm_h, arm_n, with_core):
    """A = everything with arm-frame x < 30 above the 36T layer (plus the R8.5 core); B = the lug beyond the removed
    22 mm slab, his shifted by -22 against the new one (a 1 um shift avoids a coincident-face boolean failure; a 0.05 mm
    shift is the sensitivity control)."""
    ho, no = rotz(s_home, -arm_h), rotz(s_new, -arm_n)
    big = 300.0
    A = box(-big, 30.0, -big, big, 16.0, 60.0)
    if with_core:
        A = A.fuse(cyl(8.5, -1.0, 16.0))
    ha, na = ho.intersect(A), no.intersect(A)
    cA = common(ha, na)
    resA = (vol(ha) - cA, vol(na) - cA, vol(ha))
    out = {}
    for sh in (1e-3, 0.05):
        hb = ho.intersect(box(52.0 + 1e-6, big, -big, big, -1.0, 60.0)).moved(cq.Location(cq.Vector(-22.0 + sh, 0, 0)))
        nb = no.intersect(box(30.0 + 1e-6, big, -big, big, -1.0, 60.0))
        cB = common(hb, nb)
        out[sh] = (vol(hb) - cB, vol(nb) - cB, vol(nb))
    return resA, out


def test_32_body_and_lug_identical_apart_from_shortening(new, his):
    n0 = len(RESULTS)
    for which, arm_h, arm_n, core in (("compound", P.GRIPV6R_SRC_ARM_DEG_C, P.GRIPV6R_ARM_DEG_C, True),
                                      ("follower", P.GRIPV6R_SRC_ARM_DEG_F, P.GRIPV6R_ARM_DEG_F, False)):
        resA, resB = _arm_regions(his[which], new[which], arm_h, arm_n, core)
        chk("3.8", "%s: gear body + 24T layer + hub (arm-frame x<30, z>=16, his rotated by %.4f deg): his-new, new-his (mm3)"
            % (which, arm_n - arm_h), "0, 0", "%.4f, %.4f of %.0f" % resA, "+-0.05", abs(resA[0]) < 0.05 and abs(resA[1]) < 0.05)
        b = resB[1e-3]
        chk("3.9", "%s: lug beyond the cut, his shifted -22 mm: his-new, new-his (mm3; 1 um shift adds ~0.3)" % which, "0, 0",
            "%.4f, %.4f of %.0f" % b, "+-1.0", abs(b[0]) < 1.0 and abs(b[1]) < 1.0)
        b2 = resB[0.05]
        chk("3.10", "%s: sensitivity control, same comparison with a 0.05 mm shift (mm3)" % which, "> 3 (detects)",
            "%.2f" % max(b2[0], b2[1]), "", max(b2[0], b2[1]) > 3.0)
        # 24T teeth: tooth form identical regardless of the re-phasing (outline Hausdorff after undoing the rotation)
        ph_h = outer(his[which], 31.0, 0.01)
        ph_n = outer(new[which], 31.0, 0.01)
        back = rot2(ph_n, -(arm_n - arm_h))
        hd = max(cKDTree(back).query(ph_h)[0].max(), cKDTree(ph_h).query(back)[0].max())
        chk("3.10b", "%s: 24T tooth outline at z=31, new rotated back vs his, Hausdorff (mm)" % which, "< 0.001", "%.6f" % hd, "", hd < 1e-3)
        nz, t24, _ = tooth_data(ph_n, 24)
        nzh, t24h, _ = tooth_data(ph_h, 24)
        chk("3.10c", "%s: 24T count / pitch-circle tooth thickness new vs his (mm)" % which, "24 / equal",
            "%d / %.5f vs %.5f" % (nz // 2, t24, t24h), "+-1e-5", nz == 48 and abs(t24 - t24h) < 1e-5)
    assert not fails_since(n0)


def _y_crossings(s, arm, z, xs):
    a = math.radians(-arm)
    c, sn = math.cos(a), math.sin(a)
    loops = [np.stack([p[:, 0] * c - p[:, 1] * sn, p[:, 0] * sn + p[:, 1] * c], 1) for p in loops_at(s, z, 0.05)]
    res = {}
    for x in xs:
        ys = []
        for p in loops:
            u, v = p[:-1], p[1:]
            m = (u[:, 0] - x) * (v[:, 0] - x) < 0
            t = (x - u[m, 0]) / (v[m, 0] - u[m, 0])
            ys += list(u[m, 1] + t * (v[m, 1] - u[m, 1]))
        res[x] = [round(float(q), 3) for q in sorted(ys)]
    return res


def test_33_lug_section_pivot_and_shortening(new, his):
    n0 = len(RESULTS)
    for which, arm_h, arm_n, fork, hole_r in (("compound", P.GRIPV6R_SRC_ARM_DEG_C, P.GRIPV6R_ARM_DEG_C, (9.15, 4.15), 1.75),
                                              ("follower", P.GRIPV6R_SRC_ARM_DEG_F, P.GRIPV6R_ARM_DEG_F, (9.165, 4.165), 4.165)):
        xs_h = [29.9, 40.0, 60.0, 70.0, 80.0]
        xs_n = [x - 22.0 if x > 52 else x for x in xs_h]
        sec_h = _y_crossings(his[which], arm_h, 21.0, xs_h)
        sec_n = _y_crossings(new[which], arm_n, 21.0, xs_n)
        for xh, xn in zip(xs_h, xs_n):
            chk("3.11", "%s: lug section y-crossings at arm x=%g (his) / %g (new)" % (which, xh, xn), "equal",
                "his %s | new %s" % (sec_h[xh], sec_n[xn]), "exact 1e-3", sec_h[xh] == sec_n[xn])
        want = [-fork[0], -fork[1], fork[1], fork[0]]
        chk("3.11b", "%s: fork section Ø%.2f outer, slot %.2f (arm x=40)" % (which, 2 * fork[0], 2 * fork[1]), str(want), str(sec_n[40.0]), "",
            sec_n[40.0] == want)
        bbh = rotz(his[which], -arm_h).BoundingBox()
        bbn = rotz(new[which], -arm_n).BoundingBox()
        num("3.12", "%s: lug end x in arm frame, his - 22 (mm)" % which, bbh.xmax - P.GRIPV6R_ARM_SHORTEN, bbn.xmax, 0.01)
        _, pl = census(new[which])
        zs = {z for (z, s_) in pl if z in (16.0, 26.0)}
        chk("3.13", "%s: lug band z 16..26 (10 mm thick)" % which, "{16.0, 26.0}", str(zs), "", zs == {16.0, 26.0})
        for nm, s, axr in (("his", his[which], 75.0), ("new", new[which], 53.0)):
            ph = [(x, y) for (x, y) in off_axis_centres(s, hole_r) if math.hypot(x, y) > 30.0]
            chk("3.14", "%s %s: pivot hole Ø%.2f at crank radius %.0f" % (which, nm, 2 * hole_r, axr), "1 hole", str(len(ph)), "", len(ph) == 1)
            if ph:
                num("3.15", "%s %s: pivot radius from the gear axis (mm)" % (which, nm), axr, math.hypot(*ph[0]), 2e-3)
    chk("3.16", "observation: his compound pivot hole Ø3.5 but his follower pivot hole Ø8.33 (kept, as his)", "info", "info", "", True)
    assert not fails_since(n0)


# =================================================================================================================
# 4. new 36T tooth form
# =================================================================================================================
def _crossings(pts, n):
    rp = M * n / 2
    r = np.hypot(pts[:, 0], pts[:, 1])
    th = np.unwrap(np.arctan2(pts[:, 1], pts[:, 0]))
    s = r - rp
    ang = []
    for i in np.where(np.sign(s[:-1]) * np.sign(s[1:]) < 0)[0]:
        t = s[i] / (s[i] - s[i + 1])
        ang.append(th[i] + t * (th[i + 1] - th[i]))
    return np.array(sorted(a % (2 * math.pi) for a in ang))


def tooth_data(pts, n):
    """(pitch-circle crossings, tooth thickness at the pitch circle (mm), tooth centre angles (rad))."""
    rp = M * n / 2
    ang = _crossings(pts, n)
    w = np.diff(np.append(ang, ang[0] + 2 * math.pi))
    k0 = 0 if w[0::2].mean() < w[1::2].mean() else 1
    thick = w[k0::2].mean() * rp
    cen = []
    for j in range(k0, len(ang), 2):
        a0, a1 = ang[j], ang[(j + 1) % len(ang)]
        if a1 < a0:
            a1 += 2 * math.pi
        cen.append(0.5 * (a0 + a1))
    return len(ang), thick, np.array(cen)


def involute_fit(pts, n):
    """Scatter of phi_b = |angle from tooth centre| + inv(alpha(r)) over the flank (root fillet and tip corner excluded);
    a true 20 deg involute gives a constant.  Returns (mean, std*rb, max dev*rb, points)."""
    rp = M * n / 2
    rb = rp * math.cos(math.radians(20.0))
    r = np.hypot(pts[:, 0], pts[:, 1])
    th = np.arctan2(pts[:, 1], pts[:, 0])
    _, _, cen = tooth_data(pts, n)
    sel = np.where((r > max(rb, r.min()) + 0.8) & (r < r.max() - 0.15))[0]
    vals = []
    for i in sel:
        d = (th[i] - cen + math.pi) % (2 * math.pi) - math.pi
        dd = d[np.argmin(abs(d))]
        if abs(dd) > math.pi / n * 0.95:
            continue
        a = math.acos(rb / r[i])
        vals.append(abs(dd) + math.tan(a) - a)
    v = np.array(vals)
    return float(v.mean()), float(v.std() * rb), float(abs(v - v.mean()).max() * rb), len(v)


def test_40_new_36T_tooth_form(new, his):
    n0 = len(RESULTS)
    ring = outer(new["compound"], 8.0, 0.01)
    h54 = outer(his["compound"], 8.0, 0.01)
    r = np.hypot(ring[:, 0], ring[:, 1])
    num("4.1", "36T tip radius (mm) [m1.5: 27 + 1.5]", 28.5, r.max(), 1e-4)
    num("4.2", "36T root radius (mm) [27 - 1.875]", 25.125, r.min(), 1e-4)
    n_cross, t36, _ = tooth_data(ring, 36)
    n54, t54, _ = tooth_data(h54, 54)
    chk("4.3", "36T teeth counted (pitch-circle crossings / 2)", "36", str(n_cross // 2), "", n_cross == 72)
    num("4.4", "36T tooth thickness at the R27 pitch circle (mm) [claim 2.2562]", 2.2562, t36, 5e-4)
    num("4.5", "36T thickness minus his 54T thickness at its R40.5 pitch circle (mm)", 0.0, t36 - t54, 1e-4)
    num("4.6", "thinning against ideal pi*m/2 = 2.35619 (mm)", 0.10, math.pi * M / 2 - t36, 5e-4)
    for lab, pts, n in (("new 36T", ring, 36), ("his 54T", h54, 54),
                        ("his 24T (compound above the lug band)", outer(his["compound"], 31.0, 0.01), 24),
                        ("his 18T pinion", outer(his["pinion"], 8.0, 0.01), 18)):
        mean, sd, mx, cnt = involute_fit(pts, n)
        rp = M * n / 2
        thin = (math.pi / (2 * n) + (math.tan(math.radians(20)) - math.radians(20)) - mean) * 2 * rp
        chk("4.7", "%s: flank is a 20 deg involute (max deviation mm), implied thinning (mm)" % lab,
            "dev < 0.002, thinning 0.100", "dev %.1e (%d pts), thinning %.4f" % (mx, cnt, thin), "",
            mx < 0.002 and abs(thin - 0.100) < 5e-4)
    on, off = agg_cyl(new["compound"])
    f04 = sum(v[0] for k, v in off.items() if k[0] == 0.4 and k[1] == 0.0)
    chk("4.8", "36T R0.4 root fillet faces (2 per tooth)", "72", str(f04), "", f04 == 72)
    assert not fails_since(n0)


def test_41_generator_reproduces_his_gears():
    """The 36T ring is made by the repo's v3 involute generator.  Independent test that this generator reproduces HIS
    teeth, root blend included: build 18T / 24T / 54T with it and compare section outlines (Hausdorff) with his."""
    n0 = len(RESULTS)
    from cad.gripper_v3_fit_review_20261018.gears import gear
    for lab, name, rtip, n, z0, z1, zs in (("18T pinion", P.GRIPV6R_SRC_PINION, 15.0, 18, 0.0, 16.0, 8.0),
                                           ("54T ring", P.GRIPV6R_SRC_COMPOUND, 19.5, 54, 0.0, 16.0, 8.0),
                                           ("24T (compound)", P.GRIPV6R_SRC_COMPOUND, 19.5, 24, 26.0, 36.0, 31.0)):
        s, _ = homed(name, rtip)
        pts = outer(s, zs, 0.01)
        _, _, cen = tooth_data(pts, n)
        g = gear(n, M, z1 - z0, phase=math.degrees(cen[0]), reduction=P.GRIPV6R_TOOTH_THIN,
                 root_radius=P.GRIPV6R_ROOT_FILLET_R).val()
        gp = outer(g.moved(cq.Location(cq.Vector(0, 0, z0))), zs, 0.01)
        hd = max(cKDTree(gp).query(pts)[0].max(), cKDTree(pts).query(gp)[0].max())
        chk("4.9", "generator %s vs his outline, Hausdorff distance (mm)" % lab, "< 0.002", "%.5f" % hd, "", hd < 0.002)
    assert not fails_since(n0)


# =================================================================================================================
# 5. mesh clearances (2D outlines swept, own implementation) + 3D booleans
# =================================================================================================================
class Pose:
    def __init__(self, pts, axis, rot_deg):
        self.p = rot2(pts, rot_deg) + np.array(axis)
        self.axis = np.array(axis, float)
        self._path = None

    @property
    def path(self):
        if self._path is None:
            self._path = MPath(self.p)
        return self._path


def gap(A, B, R=9.0):
    """> 0: minimum distance when the outlines are disjoint; < 0: minus the penetration depth when they overlap."""
    mid = 0.5 * (A.axis + B.axis)
    a = A.p[np.hypot(*(A.p - mid).T) < R]
    b = B.p[np.hypot(*(B.p - mid).T) < R]
    ta, tb = cKDTree(a), cKDTree(b)
    da, db = tb.query(a)[0], ta.query(b)[0]
    ia, ib = B.path.contains_points(a), A.path.contains_points(b)
    if ia.any() or ib.any():
        dep = max(da[ia].max() if ia.any() else 0.0, db[ib].max() if ib.any() else 0.0)
        return -max(dep, 1e-9)
    return float(min(da.min(), db.min()))


def window(pts1, ax1, rot1, pts2, ax2, rot2_, lim=4.0, tol=2e-4, step0=0.3):
    """Rotation interval (deg) of gear 2, about its pose, over which it does not touch gear 1 (gear 1 fixed)."""
    A = Pose(pts1, ax1, rot1)
    f = lambda psi: gap(A, Pose(pts2, ax2, rot2_ + psi))
    g0 = f(0.0)
    if g0 <= 0:
        return 0.0, 0.0, g0
    res = []
    for sg in (+1, -1):
        a = 0.0
        while a < lim and f(sg * (a + step0)) > 0:
            a += step0
        if a >= lim:
            res.append(sg * lim)
            continue
        lo, hi = a, a + step0
        while hi - lo > tol:
            mid = 0.5 * (lo + hi)
            if f(sg * mid) > 0:
                lo = mid
            else:
                hi = mid
        res.append(sg * 0.5 * (lo + hi))
    return min(res), max(res), g0


@pytest.fixture(scope="module")
def mesh_rows(outlines):
    ds = list(np.arange(-30.0, P.GRIPV6R_SWEEP_DEG + 1e-9, 1.0)) + [P.GRIPV6R_SWEEP_DEG]
    rows = []
    for d in ds:
        w1 = window(outlines["ring"], C_XY, d, outlines["pin"], S_XY, -2.0 * d)    # compound +d, pinion -2 d
        w2 = window(outlines["sc"], C_XY, d, outlines["sf"], F_XY, -d)             # follower -d
        rows.append((d,) + w1 + w2)
    return np.array(rows)


def test_50_centre_distances():
    n0 = len(RESULTS)
    num("5.1", "pinion-compound centre distance (mm)", 40.80, math.hypot(S_XY[0] - C_XY[0], S_XY[1] - C_XY[1]), 1e-6)
    num("5.2", "compound-follower centre distance (mm)", 36.30, C_XY[0] - F_XY[0], 1e-9)
    num("5.3", "GRIPV7 CD_MAIN (m1.5*(18+36)/2 + 0.30)", 40.80, P.GRIPV7_CD_MAIN, 1e-9)
    num("5.4", "GRIPV7 CD_SYNC (m1.5*24 + 0.30)", 36.30, P.GRIPV7_CD_SYNC, 1e-9)
    assert not fails_since(n0)


def test_51_backlash_over_sweeps(mesh_rows):
    n0 = len(RESULTS)
    R = mesh_rows
    for label, (ilo, ihi, rpc) in (("pinion/36T", (1, 2, 13.5)), ("24T/24T", (4, 5, 18.0))):
        for rng_name, sel in (("+-30 deg sweep", (R[:, 0] >= -30) & (R[:, 0] <= 30)),
                              ("0..76.5 stroke", (R[:, 0] >= 0))):
            lo, hi = R[sel, ilo], R[sel, ihi]
            tot = (hi - lo) * math.pi / 180.0 * rpc
            per = np.minimum(-lo, hi) * math.pi / 180.0 * rpc
            ge("5.5", "%s %s (%d poses): total circumferential backlash, min (mm) [claim >= 0.42]" % (label, rng_name, sel.sum()), 0.42, tot.min())
            ge("5.6", "%s %s: circumferential clearance on the TIGHTER flank at the as-built pose (mm)" % (label, rng_name), 0.20, per.min())
            ge("5.7", "%s %s: normal clearance per flank = that x cos20 (mm) [claim ~0.20]" % (label, rng_name), 0.19,
               per.min() * math.cos(math.radians(20)))
            off = (lo + hi) / 2
            chk("5.8", "%s %s: window-centre offset of the as-built pose (deg)" % (label, rng_name), "|.| < 0.02",
                "%.4f .. %.4f" % (off.min(), off.max()), "", np.abs(off).max() < 0.02)
    ge("5.9", "no tooth overlap: min outline gap at the as-built pose, pinion/36T, all poses (mm)", 0.15, R[:, 3].min())
    ge("5.10", "no tooth overlap: min outline gap at the as-built pose, 24T/24T, all poses (mm)", 0.15, R[:, 6].min())
    assert not fails_since(n0)


def test_52_tip_root_clearance(outlines):
    n0 = len(RESULTS)
    tip = {k: float(np.hypot(*v.T).max()) for k, v in outlines.items()}
    root = {k: float(np.hypot(*v.T).min()) for k, v in outlines.items()}
    cm, cs = P.GRIPV6R_CD_MAIN, P.GRIPV6R_CD_SYNC
    vals = {"pinion tip -> 36T root": cm - tip["pin"] - root["ring"], "36T tip -> pinion root": cm - tip["ring"] - root["pin"],
            "compound 24T tip -> follower root": cs - tip["sc"] - root["sf"], "follower tip -> compound 24T root": cs - tip["sf"] - root["sc"]}
    for k, v in vals.items():
        chk("5.11", "tip-to-root clearance, %s (mm) [claim 0.675]" % k, ">= 0.375 (0.675)", "%.4f" % v, "", v >= 0.375 and abs(v - 0.675) < 1e-3)

    def split(p, tp, rt):
        r = np.hypot(*p.T)
        return p[r > tp - 0.01], p[r < rt + 0.01]
    land = {k: split(v, tip[k], root[k]) for k, v in outlines.items()}
    best = 1e9
    for d in np.arange(-30.0, P.GRIPV6R_SWEEP_DEG + 1e-9, 0.5):
        posed = {"pin": (S_XY, -2 * d), "ring": (C_XY, d), "sc": (C_XY, d), "sf": (F_XY, -d)}
        P_ = {k: (rot2(land[k][0], posed[k][1]) + np.array(posed[k][0]), rot2(land[k][1], posed[k][1]) + np.array(posed[k][0])) for k in land}
        for a, b in (("pin", "ring"), ("ring", "pin"), ("sc", "sf"), ("sf", "sc")):
            best = min(best, cKDTree(P_[b][1]).query(P_[a][0])[0].min())
    chk("5.12", "swept min distance tip land -> root land, 4 pairs, -30..76.5 deg (mm; root band 0.01 mm)", ">= 0.375",
        "%.4f" % best, "", best >= 0.375)
    assert not fails_since(n0)


@pytest.fixture(scope="module")
def pieces(new):
    def lugpiece(s, arm):
        r = rotz(s, -arm)
        return rotz(r.intersect(box(21.0, 400, -400, 400, 15.999, 60)), arm)
    return dict(lc=lugpiece(new["compound"], P.GRIPV6R_ARM_DEG_C), lf=lugpiece(new["follower"], P.GRIPV6R_ARM_DEG_F))


def test_53_interference_3d(new, pieces):
    n0 = len(RESULTS)
    ds = sorted(set(list(np.arange(-20.0, 30.0 + 1e-9, 5.0)) + list(np.arange(0.0, P.GRIPV6R_SWEEP_DEG + 1e-9, 5.0)) +
                    [P.GRIPV6R_SWEEP_DEG]))
    worst = dict(pc=0.0, cf=0.0, pf=0.0, lcf=0.0, lfc=0.0, ll=0.0, lcp=0.0, lfp=0.0)
    for d in ds:
        p, c, f = place(new["pinion"], S_XY, -2 * d), place(new["compound"], C_XY, d), place(new["follower"], F_XY, -d)
        lc, lf = place(pieces["lc"], C_XY, d), place(pieces["lf"], F_XY, -d)
        worst["pc"] = max(worst["pc"], common(p, c))
        worst["cf"] = max(worst["cf"], common(c, f))
        worst["pf"] = max(worst["pf"], common(p, f))
        worst["lcf"] = max(worst["lcf"], common(lc, f))
        worst["lfc"] = max(worst["lfc"], common(lf, c))
        worst["ll"] = max(worst["ll"], common(lc, lf))
        worst["lcp"] = max(worst["lcp"], common(lc, p))
        worst["lfp"] = max(worst["lfp"], common(lf, p))
    for k, lab in (("pc", "pinion x compound"), ("cf", "compound x follower"), ("pf", "pinion x follower"),
                   ("lcf", "compound lug x follower"), ("lfc", "follower lug x compound"), ("ll", "lug x lug"),
                   ("lcp", "compound lug x pinion"), ("lfp", "follower lug x pinion")):
        chk("5.13", "3D common volume %s, max over %d poses -20..76.5 deg (mm3)" % (lab, len(ds)), "0", "%.4g" % worst[k], "+-1e-3",
            worst[k] < 1e-3)
    c0 = place(new["compound"], C_XY, 0.0)
    v1 = common(c0, place(new["follower"], F_XY, 2.5))
    v2 = common(c0, place(new["pinion"], S_XY, 3.0))
    chk("5.14", "positive control: follower turned 2.5 deg off its window overlaps (mm3)", "> 0.5", "%.3f" % v1, "", v1 > 0.5)
    chk("5.15", "positive control: pinion turned 3 deg off its window overlaps (mm3)", "> 0.5", "%.3f" % v2, "", v2 > 0.5)
    v3 = common(place(pieces["lc"], C_XY, -25.0), place(pieces["lf"], F_XY, 25.0))
    chk("5.15b", "positive control: lug x lug at d=-25 deg (past the stop) (mm3)", "> 1", "%.1f" % v3, "", v3 > 1.0)
    assert not fails_since(n0)


def test_54_axial_gaps_and_layers(new):
    n0 = len(RESULTS)

    def levels(s):
        out = set()
        for f in s.Faces():
            a = BRepAdaptor_Surface(f.wrapped)
            if a.GetType() == GeomAbs_Plane and abs(abs(a.Plane().Axis().Direction().Z()) - 1) < 1e-9 and f.Area() > 20:
                out.add(round(a.Plane().Location().Z(), 4))
        return sorted(out)
    fz = [z for z in levels(new["follower"]) if z > 0][0]
    num("5.16", "follower bottom z (mm)", 16.0, fz, 1e-4)
    for var, exp in (("compound", 0.30), ("compound_norelief", 0.0)):
        lower = new[var].intersect(box(-300, 300, -300, 300, -1, 16.0))
        dm = [place(lower, C_XY, d).distance(place(new["follower"], F_XY, -d)) for d in (0.0, 30.0, 76.5)]
        num("5.17", "%s: follower to 36T layer, 3D distance at d=0/30/76.5 (mm)" % var, exp, min(dm), 1e-4)
        num("5.17b", "%s: spread over the three poses (mm)" % var, 0.0, max(dm) - min(dm), 1e-4)
    top = [z for z in levels(new["compound"]) if 10 < z < 16.0]
    num("5.18", "relief floor z = 36T top face (mm)", 15.7, top[0] if top else -1.0, 1e-4)
    annulus = cyl(80, 15.7, 16.0).cut(cyl(16.5, 15, 17))
    num("5.19", "volume removed by the relief = no-relief solid inside annulus R>=16.5, z15.7..16 (mm3)",
        common(new["compound_norelief"], annulus), new["compound_norelief"].Volume() - new["compound"].Volume(), 0.5)
    chk("5.19b", "relief solid inside that annulus (mm3)", "0", "%.4f" % common(new["compound"], annulus), "", common(new["compound"], annulus) < 1e-3)
    num("5.20", "relief inner R16.5 margin to the follower tip circle (36.30 - 19.5 - 16.5) (mm)", 0.30, (P.GRIPV6R_CD_SYNC - 19.5) - 16.5, 1e-6)
    fm = vol(new["follower"].intersect(box(-300, 300, -300, 300, -1, 15.999)))
    chk("5.21", "follower material below z=16 (mm3)", "0", "%.4g" % fm, "", fm < 1e-3)
    num("5.22", "pinion top face z (mm)", 16.0, new["pinion"].BoundingBox().zmax, 1e-4)
    assert not fails_since(n0)


def test_55_swept_lug_clearance(new, pieces):
    n0 = len(RESULTS)

    def pockets(s, r=7.0375):
        zs = set()
        for f in s.Faces():
            a = BRepAdaptor_Surface(f.wrapped)
            if a.GetType() == GeomAbs_Cylinder and abs(a.Cylinder().Radius() - r) < 1e-3:
                bb = f.BoundingBox()
                zs.add((round(bb.zmin, 3), round(bb.zmax, 3)))
        return sorted(zs)
    pc, pf = pockets(new["compound"]), pockets(new["follower"])

    def hw(ax, rng):
        out = [("pin Ø7", cyl(3.5, -3.0, 39.0, ax[0], ax[1]))]
        out += [("bearing Ø14 %.2f..%.2f" % r_, cyl(7.0, r_[0], r_[1], ax[0], ax[1])) for r_ in rng]
        return out
    best = (1e9, None)
    for d in sorted(set(list(np.arange(0.0, P.GRIPV6R_SWEEP_DEG + 1e-9, 5.0)) + [P.GRIPV6R_SWEEP_DEG])):
        p, c, f = place(new["pinion"], S_XY, -2 * d), place(new["compound"], C_XY, d), place(new["follower"], F_XY, -d)
        lc, lf = place(pieces["lc"], C_XY, d), place(pieces["lf"], F_XY, -d)
        tg_c = [("follower gear", f), ("follower lug", lf), ("pinion", p)] + [("F " + n, x) for n, x in hw(F_XY, pf)]
        tg_f = [("compound gear", c), ("compound lug", lc), ("pinion", p)] + [("C " + n, x) for n, x in hw(C_XY, pc)]
        for who, lug, tg in (("compound lug", lc, tg_c), ("follower lug", lf, tg_f)):
            for n, x in tg:
                dist = lug.distance(x)
                if dist < best[0]:
                    best = (dist, (d, who, n))
    ge("5.23", "swept lug/fork clearance to gears, other lug, pinion, pins, bearings; min over 0..76.5 deg (mm) [need >= 1.0]", 1.0, best[0])
    num("5.24", "same minimum against the claim (>= 10.17; at d=%g: %s -> %s) (mm)" % (best[1][0], best[1][1], best[1][2]), 10.17, best[0], 0.01)
    first = None
    for d in np.arange(0.0, -35.0, -0.5):
        if place(pieces["lc"], C_XY, d).distance(place(pieces["lf"], F_XY, -d)) <= 1e-6:
            first = d
            break
    chk("5.26", "lug-to-lug first contact going past the closed stop (deg) [claim -21.5]", "-21.5", str(first), "+-0.5",
        first is not None and abs(first + 21.5) <= 0.5)
    ge("5.27", "lug-to-lug distance at d=0 / -10 / -20 deg, min (mm)", 0.1,
       min(place(pieces["lc"], C_XY, dd).distance(place(pieces["lf"], F_XY, -dd)) for dd in (0.0, -10.0, -20.0)))
    assert not fails_since(n0)


# =================================================================================================================
# 6. crank phasing
# =================================================================================================================
def test_60_crank_phasing(new, his):
    n0 = len(RESULTS)
    pc = [p for p in off_axis_centres(new["compound"], 1.75) if math.hypot(*p) > 30][0]
    pf = [p for p in off_axis_centres(new["follower"], 4.165) if math.hypot(*p) > 30][0]
    ac = math.degrees(math.atan2(pc[1], pc[0]))
    af = math.degrees(math.atan2(pf[1], pf[0])) % 360.0
    num("6.1", "compound lug angle (deg, CCW from +x)", -78.589, ac, 2e-3)
    num("6.2", "follower lug angle (deg)", 258.589, af, 2e-3)
    num("6.3", "mirror symmetry: angle_c + angle_f = 180 mod 360 (deg)", 180.0, (ac + af) % 360.0, 2e-3)
    num("6.4", "crank radius compound (mm)", 53.0, math.hypot(*pc), 1e-3)
    num("6.5", "crank radius follower (mm)", 53.0, math.hypot(*pf), 1e-3)
    pc_w = np.array(C_XY) + np.array(pc)
    pf_w = np.array(F_XY) + np.array(pf)
    num("6.6", "placed pivots mirror about x=0: x_c + x_f (mm)", 0.0, pc_w[0] + pf_w[0], 2e-3)
    num("6.7", "placed pivots mirror about x=0: y_c - y_f (mm)", 0.0, pc_w[1] - pf_w[1], 2e-3)
    fb = K.default()
    num("6.8", "placed compound pivot vs GRIPV7 four-bar crank pin, distance (mm)", 0.0, float(np.hypot(*(pc_w - fb.Ac))), 2e-3)
    num("6.9", "GRIPV7 crank radius R (mm)", 53.0, fb.R, 1e-9)
    num("6.10", "GRIPV7 closed crank angle (deg)", -78.589, fb.theta_c, 1e-9)
    his_c = [p for p in off_axis_centres(his["compound"], 1.75) if math.hypot(*p) > 30][0]
    his_f = [p for p in off_axis_centres(his["follower"], 4.165) if math.hypot(*p) > 30][0]
    hc, hf = math.degrees(math.atan2(his_c[1], his_c[0])), math.degrees(math.atan2(his_f[1], his_f[0])) % 360.0
    chk("6.11", "info: his lugs compound %.4f, follower %.4f (mirror error %.4f deg)" % (hc, hf, (hc + hf) % 360.0 - 180.0), "info", "info", "", True)
    assert not fails_since(n0)


# =================================================================================================================
# 7. structure: lightening ligaments and spoke stress
# =================================================================================================================
def test_70_ligaments_measured(new):
    n0 = len(RESULTS)
    for var in ("compound", "compound_norelief"):
        for z, label in ((3.0, "z=3 (bearing pocket level)"), (10.0, "z=10")):
            L = sorted(loops_at(new[var], z, 0.02), key=lambda p: -abs(parea(p)))
            out_, rest = L[0], L[1:]
            holes = [p for p in rest if math.hypot(*p.mean(0)) > 5]
            core = [p for p in rest if math.hypot(*p.mean(0)) <= 5]
            chk("7.1", "%s %s: section loops (7 holes + 1 core)" % (var, label), "7 + 1", "%d + %d" % (len(holes), len(core)), "",
                len(holes) == 7 and len(core) == 1)
            md = lambda a, b: cKDTree(b).query(a)[0].min()
            lig_root = min(md(h, out_) for h in holes)
            lig_core = min(md(h, core[0]) for h in holes)
            lig_hh = min(md(holes[i], holes[j]) for i in range(7) for j in range(i + 1, 7))
            if z == 3.0:
                num("7.2", "%s: ligament hole -> Ø14.075 pocket wall (mm) [claim 3.66]" % var, 3.6625, lig_core, 0.01)
            else:
                ge("7.2b", "%s: ligament hole -> Ø8.30 shoulder (mm)" % var, 6.0, lig_core)
            num("7.3", "%s %s: ligament hole -> 36T root circle (mm) [claim 2.43]" % (var, label), 2.425, lig_root, 0.01)
            num("7.4", "%s %s: ligament hole -> hole (mm) [claim 2.49]" % (var, label), 2.4917, lig_hh, 0.01)
            ge("7.5", "%s %s: minimum ligament vs 2.0 (mm)" % (var, label), 2.0, min(lig_root, lig_hh, lig_core))
    assert not fails_since(n0)


def spoke_numbers(N, d, Rh, root_lig, t=16.0, mesh_angle_deg=20.0):
    """Quick hand check of the web at 6 V servo stall.  The ring reaches the hub through N spokes (the web between
    adjacent Ø d holes).  Equal share, load at the hole-circle radius; bounds: spoke as a cantilever of length d
    (conservative) and as fixed-guided (M = F L / 2).  Rim bridge over a hole: simply supported span d, radial tooth-load
    component at mid span, thickness = the hole -> root-circle ligament."""
    Ft = K.SERVO_STALL_6V0 / (M * 18 / 2 / 1000.0)         # N at the pinion pitch radius (13.5 mm) = same at the 36T pitch circle
    T36 = Ft * (M * 36 / 2) / 1000.0                       # N m on the 36T gear
    w = 2 * Rh * math.sin(math.pi / N) - d                 # narrowest spoke width (hole to hole)
    Fs = T36 * 1000.0 / (N * Rh)                           # N per spoke
    Z = t * w * w / 6.0
    Fr = Ft * math.tan(math.radians(mesh_angle_deg))
    return dict(Ft=Ft, T36=T36, w=w, Fs=Fs, sig_cant=Fs * d / Z, sig_guided=Fs * d / 2 / Z, tau=1.5 * Fs / (w * t),
                sig_rim=(Fr * d / 4.0) / (t * root_lig ** 2 / 6.0))


def test_71_spoke_stress_7_vs_6_holes():
    n0 = len(RESULTS)
    allow = 22.5
    R7, root, pocket = P.GRIPV6R_LIGHT_R, 25.125, P.GRIPV6R_POCKET_R
    s7 = spoke_numbers(7, 12.0, R7, root - (R7 + 6))
    R6 = (root + pocket) / 2.0                              # balanced: root ligament = pocket ligament
    s6 = spoke_numbers(6, 12.0, R6, root - (R6 + 6))
    s6b = spoke_numbers(6, 12.0, R7, root - (R7 + 6))
    num("7.7", "tangential tooth force at 6 V stall, 11.0 kg cm (N) [claim ~80]", 80.0, s7["Ft"], 1.5)
    for lab, s_ in (("7 x Ø12 @ R16.7", s7), ("6 x Ø12 @ R%.2f (balanced)" % R6, s6), ("6 x Ø12 @ R16.7", s6b)):
        chk("7.8", "%s: spoke w %.2f mm, %.1f N/spoke; bending cantilever / fixed-guided, shear, rim-bridge (MPa)" % (lab, s_["w"], s_["Fs"]),
            "< %.1f" % allow, "%.1f / %.1f / %.2f / %.1f" % (s_["sig_cant"], s_["sig_guided"], s_["tau"], s_["sig_rim"]), "",
            max(s_["sig_cant"], s_["sig_rim"]) < allow)
    ge("7.9", "7 x Ø12 safety factor, conservative cantilever bound (allowable 22.5 MPa)", 1.5, allow / s7["sig_cant"])
    ge("7.10", "7 x Ø12 safety factor, rim bridge over a hole", 1.5, allow / s7["sig_rim"])
    chk("7.11", "6 x Ø12 (balanced) spoke bending stress lower than 7 x Ø12", "lower", "%.1f vs %.1f MPa" % (s6["sig_cant"], s7["sig_cant"]), "",
        s6["sig_cant"] < s7["sig_cant"])
    chk("7.12", "info: mass cost of 6 holes instead of 7 (g, 16 mm PETG)", "info",
        "%.2f g more" % (math.pi * 36 * 16 * PETG / 1000.0), "", True)
    assert not fails_since(n0)


# =================================================================================================================
# 8. exports: STEP round trip, STL, masses, currency
# =================================================================================================================
def read_stl(path):
    data = open(path, "rb").read()
    n = struct.unpack("<I", data[80:84])[0]
    assert len(data) == 84 + 50 * n, "not binary STL"
    arr = np.frombuffer(data[84:84 + 50 * n], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    return arr["v"].reshape(-1, 3, 3).astype(float)


def test_80_step_roundtrip(new):
    n0 = len(RESULTS)
    with tempfile.TemporaryDirectory() as td:
        for k, s in new.items():
            p = os.path.join(td, k + ".step")
            cq.exporters.export(cq.Workplane(obj=s), p)
            r = cq.importers.importStep(p).val()
            bb0, bb1 = s.BoundingBox(), r.BoundingBox()
            dmax = max(abs(a - b) for a, b in ((bb0.xmin, bb1.xmin), (bb0.xmax, bb1.xmax), (bb0.ymin, bb1.ymin),
                                                (bb0.ymax, bb1.ymax), (bb0.zmin, bb1.zmin), (bb0.zmax, bb1.zmax)))
            chk("8.1", "%s STEP re-export + reimport: valid, 1 solid" % k, "True, 1", "%s, %d" % (r.isValid(), len(r.Solids())), "",
                r.isValid() and len(r.Solids()) == 1)
            num("8.2", "%s round-trip volume relative difference" % k, 0.0, abs(r.Volume() - s.Volume()) / s.Volume(), 1e-6)
            num("8.3", "%s round-trip bbox max difference (mm)" % k, 0.0, dmax, 1e-4)
    assert not fails_since(n0)


def test_81_stl_closed_print_pose_and_volume(new):
    n0 = len(RESULTS)
    for k, s in new.items():
        T = read_stl(os.path.join(REPO, "exports", "stl", "gripper_v6r_%s.stl" % STEP_NAMES[k]))
        v = T.reshape(-1, 3)
        u, inv = np.unique(np.round(v, 4), axis=0, return_inverse=True)
        Fi = inv.reshape(-1, 3)
        e = np.sort(np.concatenate([Fi[:, [0, 1]], Fi[:, [1, 2]], Fi[:, [2, 0]]]), axis=1)
        _, cnt = np.unique(e, axis=0, return_counts=True)
        sv = float(np.einsum("ij,ij->i", T[:, 0], np.cross(T[:, 1], T[:, 2])).sum() / 6.0)
        chk("8.4", "%s STL closed 2-manifold: edges not shared by exactly 2 triangles" % k, "0", str(int((cnt != 2).sum())), "", (cnt != 2).sum() == 0)
        chk("8.5", "%s STL signed volume positive (outward normals)" % k, "> 0", "%.1f" % sv, "", sv > 0)
        num("8.6", "%s STL volume vs STEP volume (relative)" % k, 0.0, abs(sv - s.Volume()) / s.Volume(), 1e-3)
        num("8.7", "%s STL z-min on the bed (mm)" % k, 0.0, v[:, 2].min(), 1e-3)
        bb = s.BoundingBox()
        num("8.8", "%s STL height = STEP z-extent, gear axis vertical (mm)" % k, bb.zlen, v[:, 2].max() - v[:, 2].min(), 0.05)
        num("8.9", "%s STL x-extent vs STEP (mm)" % k, bb.xlen, v[:, 0].max() - v[:, 0].min(), 0.05)
        num("8.10", "%s STL y-extent vs STEP (mm)" % k, bb.ylen, v[:, 1].max() - v[:, 1].min(), 0.05)
    assert not fails_since(n0)


def test_82_masses(new):
    n0 = len(RESULTS)
    m = {k: s.Volume() * PETG / 1000.0 for k, s in new.items()}
    for k, expected in (("pinion", 10.19), ("compound", 56.77), ("compound_norelief", 57.14), ("follower", 28.88)):
        num("8.11", "%s mass, PETG 1.27 g/cc (g) [json]" % k, expected, m[k], 0.02)
    tot_new = m["pinion"] + m["compound"] + m["follower"]
    parts = load_v6()
    h = sum(find(parts, n).Volume() for n in (P.GRIPV6R_SRC_PINION, P.GRIPV6R_SRC_COMPOUND, P.GRIPV6R_SRC_FOLLOWER)) * PETG / 1000.0
    chk("8.12", "gear set mass, new vs his (g)", "new < his", "new %.2f, his %.2f" % (tot_new, h), "", tot_new < h)
    assert not fails_since(n0)


def test_83_exports_current_with_builder(new):
    """The delivered STEP files equal a fresh build of the implementer's code (not stale)."""
    n0 = len(RESULTS)
    from cad.parts import gripper_v6r_gears as G
    for k in ("pinion", "compound", "compound_norelief", "follower"):
        b = G.part(k)
        e = new[k]
        c = common(b, e)
        chk("8.13", "%s: fresh build vs delivered STEP, volume difference both ways (mm3)" % k, "0, 0",
            "%.4f, %.4f" % (b.Volume() - c, e.Volume() - c), "+-0.05", abs(b.Volume() - c) < 0.05 and abs(e.Volume() - c) < 0.05)
    assert not fails_since(n0)
