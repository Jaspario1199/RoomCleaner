#!/usr/bin/python3
"""
Build, export and check the Gripper 1021 parts (hands first, then housing + camera bay).

Run:  /usr/bin/python3 scripts/build_gripper1021.py hands      # hands: exports, sweep, clearances, renders (~5 min)
      /usr/bin/python3 scripts/build_gripper1021.py hands-renders   # renders only
      /usr/bin/python3 scripts/build_gripper1021.py housing    # housing + bay + cover: exports, measurements, cable lines, renders (~6 min)
      /usr/bin/python3 scripts/build_gripper1021.py housing-renders
      /usr/bin/python3 scripts/build_gripper1021.py housing-34       # housing with the three-cable holes (spec section 5): exports, measurements, cable lines, renders
      /usr/bin/python3 scripts/build_gripper1021.py housing-34-renders
      /usr/bin/python3 scripts/build_gripper1021.py all

Reads (read-only): cad/reference/gripper_1021/parts/*.step (Jasper's parts, assembly world frame).
Writes:
  exports/step/gripper1021_hand_right.step   right hand at Jasper's file pose (theta = -52.1 deg), world frame
  exports/step/gripper1021_hand_left.step    left hand, mirrored pose (follower rotated -6 deg into mesh)
  exports/stl/gripper1021_hand_{right,left}.stl   print orientation (bed face z = 1090 down, z min = 0)
  renders/gripper1021/...                    standard views + closed / open pose images on the mechanism
  exports/step/gripper1021_housing_cambay.step, ..._cover.step   housing + bay and its cover, assembly world frame
  exports/stl/gripper1021_housing_cambay.stl, ..._cover.stl      print orientation (housing bottom plane on the bed; cover on its flat outer face)
  exports/step/gripper1021_housing_cambay_34.step, exports/stl/gripper1021_housing_cambay_34.stl   housing + bay + three-cable holes and labels
  renders/gripper1021/gripper1021_housing_cambay_34_*.png (7 standard views + close-ups per hole)
  verification/gripper1021_housing_34_measurements.json, ..._cable_lines.json   (record: verification/gripper1021_housing_34_build_notes.md)
  (all numbers are printed; the human-readable record is verification/gripper1021_build_notes.md)
"""

from __future__ import annotations

import glob
import json
import math
import os
import sys

import cadquery as cq

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                # noqa: E402
from cad.parts import gripper1021_hands as H               # noqa: E402

REF = os.path.join(REPO, "cad", "reference", "gripper_1021", "parts")
STEP_DIR = os.path.join(REPO, "exports", "step")
STL_DIR = os.path.join(REPO, "exports", "stl")
REND_DIR = os.path.join(REPO, "renders", "gripper1021")
VER_DIR = os.path.join(REPO, "verification")

# short name -> reference file prefix
JASPER_FILES = {
    "cylinder": "00_", "servo_body": "01_", "servo_shaft": "02_", "housing1": "03_", "pinion": "04_",
    "elec_housing": "05_", "tube": "06_", "housing2": "07_", "arm_R": "08_", "arm_L": "09_",
    "compound": "10_", "follower": "11_",
}


# --------------------------------------------------------------------------------------------------------------------
# Jasper's parts and their four-bar motion
# --------------------------------------------------------------------------------------------------------------------
def load_jasper() -> dict:
    out = {}
    for name, prefix in JASPER_FILES.items():
        path = glob.glob(os.path.join(REF, prefix + "*.step"))
        assert len(path) == 1, (name, path)
        out[name] = cq.importers.importStep(path[0]).val()
    return out


def _cyl_axes(shape, radius, tol=0.01):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    res = []
    for f in shape.Faces():
        if f.geomType() == "CYLINDER":
            c = BRepAdaptor_Surface(f.wrapped).Cylinder()
            if abs(c.Radius() - radius) < tol:
                a = c.Axis().Location()
                res.append((a.X(), a.Y()))
    return res


def file_pose_angles(parts: dict) -> dict:
    """Crank / arm angles (deg) of Jasper's FILE pose, measured from the pin-hole axes in the STEP files."""
    O2, O4 = P.GRIP1021_O2, P.GRIP1021_O4
    O4L = H.mirror_pt(O4)
    hole = lambda shp, r: _cyl_axes(shp, r)
    crank = [h for h in hole(parts["compound"], 1.75) if abs(math.hypot(h[0] - O2[0], h[1] - O2[1]) - 53.0) < 0.05]
    armR = [h for h in hole(parts["arm_R"], 1.75) if abs(math.hypot(h[0] - O4[0], h[1] - O4[1]) - 50.0) < 0.05]
    armL = [h for h in hole(parts["arm_L"], 1.75) if abs(math.hypot(h[0] - O4L[0], h[1] - O4L[1]) - 50.0) < 0.05]
    assert crank and armR and armL, (crank, armR, armL)
    ang = lambda c, o: math.degrees(math.atan2(c[1] - o[1], c[0] - o[0]))
    return {"t20": ang(crank[0], O2), "t40R": ang(armR[0], O4), "t40L": ang(armL[0], O4L),
            "crank_xy": crank[0], "armR_xy": armR[0], "armL_xy": armL[0]}


def _rot(shape, centre, deg):
    return shape.rotate(cq.Vector(centre[0], centre[1], 0), cq.Vector(centre[0], centre[1], 1), deg)


def jasper_at(parts: dict, fp: dict, theta_deg: float) -> dict:
    """Jasper's moving parts at compound crank angle theta (follower rotated -6 deg into mesh first, then mirrored
    motion; arms follow the four-bar; pinion turns with the 36T gear: ratio 2, opposite sense)."""
    O2, O4 = P.GRIP1021_O2, P.GRIP1021_O4
    O2L, O4L = H.mirror_pt(O2), H.mirror_pt(O4)
    _, B = H.solve_fourbar(theta_deg)
    t4 = math.degrees(math.atan2(B[1] - O4[1], B[0] - O4[0]))
    d = theta_deg - fp["t20"]
    pin_axis = (961.85, 761.39)                       # pinion axis (servo shaft), from the assembly
    return {
        "compound": _rot(parts["compound"], O2, d),
        "follower": _rot(_rot(parts["follower"], O2L, P.GRIP1021_FOLLOWER_MESH_DEG), O2L, -d),
        "arm_R": _rot(parts["arm_R"], O4, t4 - fp["t40R"]),
        "arm_L": _rot(parts["arm_L"], O4L, (-180.0 - t4) - fp["t40L"]),
        "pinion": _rot(parts["pinion"], pin_axis, -2.0 * d),
        "housing1": parts["housing1"], "housing2": parts["housing2"],
        "elec_housing": parts["elec_housing"], "tube": parts["tube"], "cylinder": parts["cylinder"],
        "servo_body": parts["servo_body"], "servo_shaft": parts["servo_shaft"],
    }


def _bbox_overlap(a, b, pad=1e-6):
    A, B = a.BoundingBox(), b.BoundingBox()
    return not (A.xmax < B.xmin - pad or B.xmax < A.xmin - pad or A.ymax < B.ymin - pad or
                B.ymax < A.ymin - pad or A.zmax < B.zmin - pad or B.zmax < A.zmin - pad)


def overlap_volume(a, b) -> float:
    """Boolean intersection volume (mm3); bounding-box-disjoint pairs are exactly 0."""
    if not _bbox_overlap(a, b):
        return 0.0
    return a.intersect(b).Volume()


def sweep(hand_r, hand_l, angles=P.GRIP1021_SWEEP_DEG, parts=None, fp=None) -> list:
    """Overlap table: for every sweep angle, both hands against every Jasper part (moved by the four-bar) and
    against each other.  Returns a list of dicts."""
    parts = parts or load_jasper()
    fp = fp or file_pose_angles(parts)
    rows = []
    for th in angles:
        moved = jasper_at(parts, fp, th)
        hr = H.place_hand(hand_r, "R", th).val()
        hl = H.place_hand(hand_l, "L", th).val()
        row = {"theta_deg": th, "R": {}, "L": {}}
        for k, shp in moved.items():
            row["R"][k] = overlap_volume(hr, shp)
            row["L"][k] = overlap_volume(hl, shp)
        row["R_vs_L"] = overlap_volume(hr, hl)
        rows.append(row)
    return rows


def sweep_summary(rows) -> str:
    keys = [k for k in rows[0]["R"]]
    lines = ["theta  " + " ".join(f"{k[:9]:>9}" for k in keys) + "  R_vs_L"]
    for r in rows:
        mx = {k: max(r["R"][k], r["L"][k]) for k in keys}
        lines.append(f"{r['theta_deg']:6.1f} " + " ".join(f"{mx[k]:9.3f}" for k in keys) + f" {r['R_vs_L']:8.3f}")
    return "\n".join(lines)



# --------------------------------------------------------------------------------------------------------------------
# measurements on the built solids (used by the build report and by tests/test_gripper1021.py)
# --------------------------------------------------------------------------------------------------------------------
def unique_points(pts, tol=0.01):
    out = []
    for p in pts:
        if not any(abs(p[0] - q[0]) < tol and abs(p[1] - q[1]) < tol for q in out):
            out.append(p)
    return out


def pin_hole_axes(hand_shape):
    """Distinct (x, y) axes of the Ø3.2 pin holes found as cylindrical faces."""
    return unique_points(_cyl_axes(hand_shape, P.GRIP1021_PIN_HOLE_D / 2, 0.01))


def boss_tops(hand_shape, centres, r=P.GRIP1021_BOSS_D / 2):
    """z of the top (+z facing planar annulus) of the boss around each centre."""
    out = []
    for c in centres:
        zs = []
        for f in hand_shape.Faces():
            if f.geomType() != "PLANE":
                continue
            n = f.normalAt()
            if n.z < 0.999:
                continue
            bb = f.BoundingBox()
            cx, cy = 0.5 * (bb.xmin + bb.xmax), 0.5 * (bb.ymin + bb.ymax)
            if math.hypot(cx - c[0], cy - c[1]) < 0.5 and bb.xmax - bb.xmin < 2 * r + 0.2:
                zs.append(bb.zmin)
        out.append(max(zs) if zs else None)
    return out


def section_segments(shape, z, step=0.04):
    import numpy as np
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
    face = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0, 0, z), gp_Dir(0, 0, 1)), -3000, 3000, -3000, 3000).Face()
    sec = BRepAlgoAPI_Section(shape.wrapped, face)
    sec.Build()
    segs = []
    for e in cq.Shape.cast(sec.Shape()).Edges():
        n = max(2, int(e.Length() / step) + 1)
        pts = [e.positionAt(t) for t in np.linspace(0.0, 1.0, n)]
        segs += [(pts[i].x, pts[i].y, pts[i + 1].x, pts[i + 1].y) for i in range(n - 1)]
    return np.array(segs)


def raster_section(shape, z, pix=0.05, margin=2.0):
    """Even-odd raster of the planar section at height z.  Returns (mask, x0, y0, pix)."""
    import numpy as np
    segs = section_segments(shape, z)
    x0, x1 = segs[:, [0, 2]].min() - margin, segs[:, [0, 2]].max() + margin
    y0, y1 = segs[:, [1, 3]].min() - margin, segs[:, [1, 3]].max() + margin
    nx, ny = int((x1 - x0) / pix) + 1, int((y1 - y0) / pix) + 1
    mask = np.zeros((ny, nx), bool)
    sx0, sy0, sx1, sy1 = segs.T
    for j in range(ny):
        yc = y0 + (j + 0.5) * pix
        hit = (sy0 <= yc) != (sy1 <= yc)
        if not hit.any():
            continue
        xs = sx0[hit] + (yc - sy0[hit]) * (sx1[hit] - sx0[hit]) / (sy1[hit] - sy0[hit])
        xs.sort()
        for a, b in zip(xs[0::2], xs[1::2]):
            mask[j, int(round((a - x0) / pix)):int(round((b - x0) / pix))] = True
    return mask, x0, y0, pix


def wall_report(shape, z, fill_ridges=False, pix=0.05, side="R"):
    """Minimum wall around every through-void (window / hole) of the section at height z.

    Returns a list of dicts {area_mm2, min_wall_to_outside, min_wall_to_other_void}.  With fill_ridges the grip-face
    grooves (x in [AX, AX + depth], inside the ridge band) are treated as solid, i.e. walls are measured from
    the nominal face."""
    import numpy as np
    from scipy import ndimage as ndi
    mask, x0, y0, pix = raster_section(shape, z, pix)
    if fill_ridges:
        xs = x0 + (np.arange(mask.shape[1]) + 0.5) * pix
        ys = y0 + (np.arange(mask.shape[0]) + 0.5) * pix
        band_y = (ys >= P.GRIP1021_RIDGE_Y0 - 0.5) & (ys <= P.GRIP1021_RIDGE_Y0 + P.GRIP1021_RIDGE_N * P.GRIP1021_RIDGE_PITCH)
        band_x = ((xs >= H.XG) & (xs <= H.XG + P.GRIP1021_RIDGE_DEPTH) if side == "R"
                  else (xs <= H.XG) & (xs >= H.XG - P.GRIP1021_RIDGE_DEPTH))
        # fill only where the groove is open to the outside on the -x side (nothing solid at x < AX)
        mask = mask | (band_y[:, None] & band_x[None, :])
    void = ~mask
    lab, n = ndi.label(void)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist()) - {0}
    out = []
    for i in range(1, n + 1):
        if i in border:
            continue
        win = lab == i
        area = win.sum() * pix * pix
        if area < 2.0:                                   # skip numerical specks
            continue
        d = ndi.distance_transform_edt(~win) * pix        # distance to this window
        other = (void & ~win)
        ext = np.isin(lab, list(border))
        oth_win = other & ~ext
        out.append({"area_mm2": float(area),
                    "min_wall_to_outside": float(d[ext].min()),
                    "min_wall_to_other_void": float(d[oth_win].min()) if oth_win.any() else None})
    return out


# --------------------------------------------------------------------------------------------------------------------
# exports
# --------------------------------------------------------------------------------------------------------------------
def export_hands(hr, hl):
    """STEP (file pose) + STL (print pose): delegates to the part module, which owns the export."""
    paths = H.export_all(STEP_DIR, STL_DIR)
    out = {}
    for nm in ("right", "left"):
        out[f"gripper1021_hand_{nm}"] = paths[nm]["step"]
        out[f"gripper1021_hand_{nm}_stl"] = paths[nm]["stl"]
    return out


def reimport_check(path, ref_shape):
    re = cq.importers.importStep(path).val()
    b0, b1 = ref_shape.BoundingBox(), re.BoundingBox()
    d = max(abs(a - b) for a, b in ((b0.xmin, b1.xmin), (b0.xmax, b1.xmax), (b0.ymin, b1.ymin),
                                    (b0.ymax, b1.ymax), (b0.zmin, b1.zmin), (b0.zmax, b1.zmax)))
    return {"solids": len(re.Solids()), "valid": re.isValid(), "vol_ref": ref_shape.Volume(), "vol_reimport": re.Volume(),
            "vol_rel_diff": abs(re.Volume() - ref_shape.Volume()) / ref_shape.Volume(), "bbox_max_diff_mm": d}



def hand_without_bosses(wp):
    """Hand with the two joint bosses removed (their seats against the crank / arm undersides are the intended contact)."""
    out = wp
    for c in (H.A_C, H.B_C, H.mirror_pt(H.A_C), H.mirror_pt(H.B_C)):
        out = out.cut(H.cyl(c[0], c[1], H.BOSS_R + 0.01, H.Z_PLATE + 1e-3, H.Z_BOSS_B + 1.0))
    return out


def clearance_rows(hr, hl, thetas=(-62.0, -30.0, -5.0), parts=None, fp=None):
    """Minimum distance (mm) from each hand (bosses removed) to the neighbouring Jasper parts moved by the four-bar."""
    parts = parts or load_jasper()
    fp = fp or file_pose_angles(parts)
    nr, nl = hand_without_bosses(hr).val(), hand_without_bosses(hl).val()
    rows = []
    for th in thetas:
        moved = jasper_at(parts, fp, th)
        hrp = H.place_hand(cq.Workplane("XY").add(nr), "R", th).val()
        hlp = H.place_hand(cq.Workplane("XY").add(nl), "L", th).val()
        row = {"theta_deg": th}
        for k in ("compound", "follower", "arm_R", "arm_L", "housing1", "housing2"):
            row[k] = min(hrp.distance(moved[k]), hlp.distance(moved[k]))
        rows.append(row)
    return rows


# --------------------------------------------------------------------------------------------------------------------
# renders
# --------------------------------------------------------------------------------------------------------------------
VIEWS = {            # name: (elev, azim) for the matplotlib painter (up = world z)
    "front": (0, -90), "rear": (0, 90), "right": (0, 0), "left": (0, 180),
    "top": (90, -90), "bottom": (-90, -90), "iso": (28, -58),
}
HAND_BLUE = (0.25, 0.55, 0.88)
HAND_GREEN = (0.30, 0.72, 0.45)
GREY = (0.72, 0.72, 0.75)
ORANGE = (0.95, 0.5, 0.15)


def standard_views(shape, name, rgb, up="z", bounds=None, tol=0.03):
    """front / rear / left / right / top / bottom / iso PNGs of one shape -> renders/gripper1021/<name>_<view>.png"""
    from cad.mesh_tools import tessellate, render
    os.makedirs(REND_DIR, exist_ok=True)
    V, F = tessellate(shape, tol, 0.15)
    paths = []
    for vn, (el, az) in VIEWS.items():
        path = os.path.join(REND_DIR, f"{name}_{vn}.png")
        render([(V, F, rgb, 1.0)], path, el, az, f"{name} - {vn}", bounds=bounds, up=up, dpi=110, size=(6, 6))
        paths.append(path)
    return paths


def pose_figure(parts, fp, hr, hl, path, thetas=(-5.0, -30.0, -62.0)):
    """Layered semi-transparent projection along z of Jasper's mechanism with both hands at the given crank angles
    (x to the right, y up).  Order: housings, gears, arms, hands (hands drawn last so they stay readable)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from cad.mesh_tools import tessellate
    cache = {}

    def tris(shape, key):
        if key not in cache:
            V, F = tessellate(shape, 0.15, 0.3)
            cache[key] = (V, F)
        return cache[key]

    fig, axes = plt.subplots(1, len(thetas), figsize=(5.0 * len(thetas), 7.2))
    for ax, th in zip(axes, thetas):
        moved = jasper_at(parts, fp, th)
        layers = [("housing2", (0.80, 0.80, 0.82), 0.35), ("housing1", (0.80, 0.80, 0.82), 0.35),
                  ("compound", (0.55, 0.55, 0.60), 0.55), ("follower", (0.55, 0.55, 0.60), 0.55),
                  ("arm_R", ORANGE, 0.75), ("arm_L", ORANGE, 0.75)]
        for key, col, al in layers:
            V, F = tessellate(moved[key], 0.15, 0.3)
            ax.add_collection(PolyCollection(V[F][:, :, :2], facecolors=[col + (al,)], edgecolors="none"))
        for side, wp, col in (("R", hr, HAND_BLUE), ("L", hl, HAND_GREEN)):
            V, F = tessellate(H.place_hand(wp, side, th).val(), 0.05, 0.2)
            ax.add_collection(PolyCollection(V[F][:, :, :2], facecolors=[col + (0.9,)], edgecolors="none"))
        ax.axvline(H.AX, color="k", lw=0.4, ls=":")
        ax.set_xlim(880, 1030)
        ax.set_ylim(560, 735)
        ax.set_aspect("equal")
        ax.set_title(f"crank angle {th:g} deg" + ("  (closed, faces meet)" if th == P.GRIP1021_THETA_CLOSED_DEG else
                                                 "  (max open)" if th == P.GRIP1021_THETA_OPEN_DEG else ""), fontsize=10)
        ax.set_xlabel("world x (mm)")
        ax.set_ylabel("world y (mm)")
    fig.suptitle("Gripper 1021 hands (blue right / green left) on Jasper's four-bar; view along z, +y up", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


# --------------------------------------------------------------------------------------------------------------------
# hands: build + report
# --------------------------------------------------------------------------------------------------------------------
def build_hands(dense=False, renders=True):
    import numpy as np
    hr, hl = H.make_hand_right(), H.make_hand_left()
    rep = {}
    for nm, wp, side in (("right", hr, "R"), ("left", hl, "L")):
        sh = wp.val()
        bb = sh.BoundingBox()
        ax_ = pin_hole_axes(sh)
        spec_a, spec_b = H.A_C, H.B_C
        if side == "L":
            spec_a, spec_b = H.mirror_pt(spec_a), H.mirror_pt(spec_b)
        ha = min(ax_, key=lambda c: math.dist(c, spec_a))
        hb = min(ax_, key=lambda c: math.dist(c, spec_b))
        tops = boss_tops(sh, [ha, hb])
        rep[nm] = {
            "valid": sh.isValid(), "solids": len(wp.solids().vals()), "volume_mm3": sh.Volume(),
            "mass_g": sh.Volume() * P.GRIP1021_PETG_G_CM3 / 1000.0,
            "bbox": [bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax],
            "A_xy": ha, "B_xy": hb, "A_err_mm": math.dist(ha, spec_a), "B_err_mm": math.dist(hb, spec_b),
            "boss_top_A": tops[0], "boss_top_B": tops[1],
            "walls_z1110_nominal": wall_report(sh, 1110.0, True, side=side), "walls_z1110_true": wall_report(sh, 1110.0, False),
            "walls_z1092": wall_report(sh, 1092.0, True, side=side),
        }
        # keep-out: above the plate for y > cut line only the two bosses
        above = cq.Workplane("XY").box(400, 400, 60, centered=False).translate((800, H.Y_CUT + 1e-6, H.Z_PLATE + 1e-6))
        rep[nm]["vol_above_plate_beyond_cut_mm3"] = sh.intersect(above.val()).Volume()
    out = export_hands(hr, hl)
    rep["exports"] = out
    rep["reimport"] = {}
    for nm, wp, side in (("right", H.place_hand(hr, "R", P.GRIP1021_THETA_FILE_DEG), "R"),
                         ("left", H.place_hand(hl, "L", P.GRIP1021_THETA_FILE_DEG), "L")):
        rep["reimport"][nm] = reimport_check(out[f"gripper1021_hand_{nm}"], wp.val())
    # file pose A/B
    for nm, side in (("right", "R"), ("left", "L")):
        sh = H.place_hand(hr if side == "R" else hl, side, P.GRIP1021_THETA_FILE_DEG).val()
        rep[f"file_pose_{nm}_holes"] = pin_hole_axes(sh)
    parts = load_jasper()
    fp = file_pose_angles(parts)
    rep["file_pose_angles"] = fp
    rep["sweep"] = sweep(hr, hl, P.GRIP1021_SWEEP_DEG, parts, fp)
    rep["clearance"] = clearance_rows(hr, hl, (-62.0, -45.0, -30.0, -15.0, -5.0), parts, fp)
    if dense:
        dense_angles = tuple(float(a) for a in np.arange(-5.0, -62.01, -3.0)) + (-62.0,)
        rep["sweep_dense"] = sweep(hr, hl, dense_angles, parts, fp)
    if renders:
        pose_figure(parts, fp, hr, hl, os.path.join(REND_DIR, "hands_on_mechanism_poses.png"))
        for nm, wp, col in (("hand_right", hr, HAND_BLUE), ("hand_left", hl, HAND_GREEN)):
            standard_views(wp.val(), "gripper1021_" + nm, col)
    return rep


def print_hands_report(rep):
    for nm in ("right", "left"):
        r = rep[nm]
        print(f"[{nm}] valid={r['valid']} solids={r['solids']} vol={r['volume_mm3']:.1f} mm3 mass={r['mass_g']:.2f} g (PETG)")
        print(f"   bbox x[{r['bbox'][0]:.4f},{r['bbox'][1]:.4f}] y[{r['bbox'][2]:.3f},{r['bbox'][3]:.3f}] z[{r['bbox'][4]:.4f},{r['bbox'][5]:.4f}]")
        print(f"   A {r['A_xy'][0]:.4f},{r['A_xy'][1]:.4f} (err {r['A_err_mm']:.4f})  B {r['B_xy'][0]:.4f},{r['B_xy'][1]:.4f} (err {r['B_err_mm']:.4f})")
        print(f"   boss tops A {r['boss_top_A']:.4f}  B {r['boss_top_B']:.4f}   above-plate-beyond-cut vol {r['vol_above_plate_beyond_cut_mm3']:.1f} mm3")
        w = lambda L: min(min(x['min_wall_to_outside'], x['min_wall_to_other_void'] or 1e9) for x in L)
        print(f"   min wall (nominal face) z1110 {w(r['walls_z1110_nominal']):.2f}  true incl. grooves {w(r['walls_z1110_true']):.2f}  z1092 {w(r['walls_z1092']):.2f}")
    for nm, d in rep["reimport"].items():
        print(f"[reimport {nm}] solids={d['solids']} valid={d['valid']} vol {d['vol_ref']:.1f}->{d['vol_reimport']:.1f} (rel {d['vol_rel_diff']:.1e}) bbox max diff {d['bbox_max_diff_mm']:.5f}")
    print("file pose holes right", [(round(a, 3), round(b, 3)) for a, b in rep["file_pose_right_holes"]],
          "left", [(round(a, 3), round(b, 3)) for a, b in rep["file_pose_left_holes"]])
    print(sweep_summary(rep["sweep"]))
    print("min clearance hand (bosses removed) to neighbours, mm")
    for r in rep["clearance"]:
        print("  theta %6.1f " % r["theta_deg"] + " ".join(f"{k}={v:6.2f}" for k, v in r.items() if k != "theta_deg"))
    if "sweep_dense" in rep:
        worst = max(max(max(r["R"].values()), max(r["L"].values()), r["R_vs_L"]) for r in rep["sweep_dense"])
        print(f"dense sweep ({len(rep['sweep_dense'])} poses): worst overlap {worst:.4f} mm3")


# --------------------------------------------------------------------------------------------------------------------
# HOUSING + CAMERA BAY: measurements
# --------------------------------------------------------------------------------------------------------------------
def housing_load():
    from cad.parts import gripper1021_housing_cambay as G
    orig = G.load_housing_bay_frame()
    housing, cover = G.make()
    return G, orig, housing, cover


def hole_cylinders(G, length_out=30.0):
    """The four Ø2 corner cable holes as solid cylinders (bay frame): from 2 mm inside the pocket corner to
    `length_out` mm beyond the outer mouth, along the axis (rising by CORNER_HOLE_ELEV_DEG toward the outside)."""
    el = math.radians(P.CAMBAY1021_CORNER_HOLE_ELEV_DEG)
    out = []
    for sx in (1, -1):
        for sz in (1, -1):
            d = cq.Vector(sx * math.cos(el) / math.sqrt(2.0), math.sin(el), sz * math.cos(el) / math.sqrt(2.0))
            a = cq.Vector(sx * P.CAMBAY1021_CORNER_HOLE_EXIT_XZ, P.CAMBAY1021_CORNER_HOLE_EXIT_Y,
                          sz * P.CAMBAY1021_CORNER_HOLE_EXIT_XZ)
            start = a - d * (a.sub(cq.Vector(sx * P.CAMBAY1021_CORNER_HOLE_INNER_XZ, P.CAMBAY1021_CORNER_HOLE_INNER_Y,
                                              sz * P.CAMBAY1021_CORNER_HOLE_INNER_XZ)).Length + 2.0)
            length = (a - start).Length + length_out
            out.append(cq.Solid.makeCylinder(P.CAMBAY1021_CORNER_HOLE_D / 2, length, start, d))
    return out


def thin_features(shape, z, r_open=0.95, pix=0.05, region=None):
    """Features of the planar section at height z that are thinner than 2 * r_open (opening by a disc).  Returns
    [(area_mm2, x, y)] of thin spots (area > 0.4 mm2) whose centroid lies in region = (xmin, xmax, ymin, ymax)."""
    import numpy as np
    from scipy import ndimage as ndi
    mask, x0, y0, pix = raster_section(shape, z, pix, margin=1.0)
    d = ndi.distance_transform_edt(mask) * pix
    opened = ndi.distance_transform_edt(~(d >= r_open)) * pix <= r_open
    lab, n = ndi.label(mask & ~opened)
    out = []
    for i in range(1, n + 1):
        m = lab == i
        a = m.sum() * pix * pix
        if a <= 0.4:
            continue
        yy, xx = np.nonzero(m)
        X, Y = x0 + (xx.mean() + 0.5) * pix, y0 + (yy.mean() + 0.5) * pix
        if region is None or (region[0] <= X <= region[1] and region[2] <= Y <= region[3]):
            out.append((float(a), float(X), float(Y)))
    return out


def housing_report():
    """Boolean and geometric measurements of housing + bay + cover."""
    G, orig, housing, cover = housing_load()
    o, c, cv = orig.val(), housing.val(), cover.val()
    rep = {}
    rep["valid"] = c.isValid() and cv.isValid()
    rep["solids"] = (len(housing.solids().vals()), len(cover.solids().vals()))
    rep["vol"] = {"orig": o.Volume(), "housing_bay": c.Volume(), "bay_net": c.Volume() - o.Volume(), "cover": cv.Volume()}
    rep["mass_g"] = {k: v * P.GRIP1021_PETG_G_CM3 / 1000.0 for k, v in rep["vol"].items()}
    win = G.wire_window_cutter().val()
    removed = o.cut(c)
    rep["removed_vol"] = removed.Volume()
    rep["removed_outside_window"] = removed.cut(win).Volume()
    rep["orig_inter_window"] = o.intersect(win).Volume()
    pocket = cq.Solid.makeBox(2 * G.POCKET_HALF, 50.0, 2 * G.POCKET_HALF, cq.Vector(-G.POCKET_HALF, G.POCKET_FLOOR_Y, -G.POCKET_HALF))
    added = c.cut(o)
    rep["added_vol"] = added.Volume()
    rep["added_in_pocket"] = added.intersect(pocket).Volume()
    rep["removed_in_pocket"] = removed.intersect(pocket).Volume()
    bb = c.BoundingBox()
    rep["bbox"] = [bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax]
    cb = cv.BoundingBox()
    rep["cover_bbox"] = [cb.xmin, cb.xmax, cb.ymin, cb.ymax, cb.zmin, cb.zmax]
    bottom = [f for f in c.Faces() if f.geomType() == "PLANE" and f.normalAt().y < -0.999 and abs(f.BoundingBox().ymin) < 1e-6]
    rep["bottom_faces"] = [(f.Area()) for f in bottom]
    rep["bottom_area_orig"] = sum(f.Area() for f in o.Faces() if f.geomType() == "PLANE" and f.normalAt().y < -0.999
                                  and abs(f.BoundingBox().ymin) < 1e-6)
    rep["cover_vs_housing_overlap"] = cv.intersect(c).Volume()
    # lens centre and the v6 reference
    from cad.parts import claw_camera_bay as V6
    rep["lens_world"] = tuple(G.LENS_CENTER_WORLD)
    rep["lens_world_v6"] = tuple(a + b for a, b in zip(V6.LENS_CENTER_BAY, V6.BAY_ORIGIN_WORLD))
    # the bay head beyond r = 78 is identical to the verified v6 bay (symmetric difference of the bay bodies)
    assert G.S == -1, "regions below assume the bay on -Z"
    far = cq.Solid.makeBox(60, 40, 32, cq.Vector(-30, -1, -110))          # r >= 78 (ribs and columns end before 78)
    b_new, b_v6 = G.make_bay_body().val(), V6.make_bay_body().val()
    nf, vf = b_new.intersect(far), b_v6.intersect(far)
    rep["head_vs_v6_symdiff"] = nf.cut(vf).Volume() + vf.cut(nf).Volume()
    rep["head_vol"] = nf.Volume()
    far2 = cq.Solid.makeBox(60, 40, 45, cq.Vector(-30, -1, -110))          # r >= 65 for the cover (lips, pegs, corral)
    cn, c6 = G.make_cover().val().intersect(far2), V6.make_cover().val().intersect(far2)
    rep["cover_vs_v6_symdiff"] = cn.cut(c6).Volume() + c6.cut(cn).Volume()
    # keep-out distances to the corner cable holes
    holes = hole_cylinders(G)
    bay_all = added.fuse(cv)
    rep["dist_bay_to_holes"] = [bay_all.distance(h) for h in holes]
    rep["dist_cover_to_holes"] = [cv.distance(h) for h in holes]
    # bay solids exist only on the -Z side outside the housing envelope
    rep["bay_added_bbox"] = [added.BoundingBox().xmin, added.BoundingBox().xmax, added.BoundingBox().ymin,
                             added.BoundingBox().ymax, added.BoundingBox().zmin, added.BoundingBox().zmax]
    # thin walls: opening by a 1.9 mm disc on print-frame sections of the housing (bay region only) and the cover
    hp = G.housing_to_print(housing).val()
    cp = G.cover_to_print(cover).val()
    thin = {}
    for z in (1.0, 2.3, 2.6, 5.0, 8.0, 9.8, 10.1, 12.0, 14.0, 17.9, 18.1, 20.0, 24.0, 26.5):
        thin[("housing", z)] = thin_features(hp, z, region=(-25, 25, 47, 110))
    for z in (1.2, 2.9, 3.6, 6.0):
        thin[("cover", z)] = thin_features(cp, z, region=(-30, 30, -10, 120))
    rep["thin"] = {f"{k[0]}@{k[1]}": v for k, v in thin.items()}
    return rep


def reimport_housing(rep_unused=None):
    G, orig, housing, cover = housing_load()
    paths = G.export_all(STEP_DIR, STL_DIR)
    out = {}
    for name, wp in (("gripper1021_housing_cambay", housing), ("gripper1021_housing_cambay_cover", cover)):
        out[name] = reimport_check(paths[name]["step"], G.to_world(wp.val()))
    return out


def assembly_interference():
    """Housing + bay and cover vs every Jasper part at the file pose; the 1 mm gap-free contact with the cylinder is a face."""
    G, orig, housing, cover = housing_load()
    parts = load_jasper()
    hw, cw = G.to_world(housing.val()), G.to_world(cover.val())
    rows = {}
    for k, shp in parts.items():
        if k == "elec_housing":
            continue
        rows[k] = (overlap_volume(hw, shp), overlap_volume(cw, shp))
    return rows


# --------------------------------------------------------------------------------------------------------------------
# cable lines: do the four cables leaving the corner holes clear the bay?  (port of
# scripts/analyze_cable_lines_claw_camera_bay.py to the 1021 housing; same model and sampling)
# --------------------------------------------------------------------------------------------------------------------
CABLE_MAPPING = {(1, 1): "B", (1, -1): "C", (-1, -1): "D", (-1, 1): "A"}     # (sx, sz) -> station, fixed at yaw 0 (as v6)


def cable_line_analysis(step_deg=15.0, verbose=True, yaws_deg=None):
    """Model (identical to the v6 analysis, only the geometry changed):
      * corner hole k leaves the housing at its outer mouth (sx*43.22, 9.95, sz*43.22) in the bay frame; the line runs from
        that mouth straight to its station anchor;
      * room frame: x east, y north, z up; claw yaw psi rotates the bay frame about the vertical (bay +X -> (cos, sin),
        bay +Z -> (sin, -cos)); at psi = 0 the bay faces room +y;
      * claw reference (mouth-plane centre on the tube axis) sampled over the workspace; the lowest claw point is the closed
        fingertip (y = 575.0), i.e. (world mouth height - 575.0) below the mouth plane;
      * lines that pass through the housing body are physically impossible and are excluded;
      * clearance = min distance from the line segment (mouth -> anchor) to the exposed bay surface (bay body + cover)."""
    import numpy as np
    from cad.mesh_tools import tessellate, ray_mesh_first_hit
    G, orig, housing, cover = housing_load()
    cfg = json.load(open(os.path.join(REPO, "config", "robot.sim.json")))
    room = cfg["room"]
    W, D, Hh = room["width_m"], room["depth_m"], room["height_m"]
    mg, cm = cfg["motion"]["workspace_margin_m"], cfg["motion"]["ceiling_margin_m"]
    anchors = {st["id"]: np.array(st["anchor_room_m"]) for st in cfg["stations"]}
    mouth, mouth_y = P.CAMBAY1021_CORNER_HOLE_EXIT_XZ, P.CAMBAY1021_CORNER_HOLE_EXIT_Y
    jaw_below = (P.CAMBAY1021_BAY_ORIGIN_WORLD[1] + mouth_y - P.GRIP1021_TIP_Y) / 1000.0

    Vbox, Fbox = tessellate(orig, 0.3, 0.3)
    added = housing.val().cut(orig.val())
    Va, Fa = tessellate(added, 0.05, 0.2)
    Vc, Fc = tessellate(cover, 0.05, 0.2)
    V = np.concatenate([Va, Vc])
    F = np.concatenate([Fa, Fc + len(Va)])
    tri = V[F]
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    rng = np.random.default_rng(0)
    pts = [V]
    n = np.maximum(1, np.ceil(area / 0.6).astype(int))
    for k in range(1, int(n.max()) + 1):
        sel = np.where(n >= k)[0]
        w = rng.dirichlet([1, 1, 1], size=len(sel))
        pts.append(np.einsum("ij,ijk->ik", w, tri[sel]))
    samples = np.concatenate(pts)

    xs = np.linspace(mg, W - mg, 8)
    ys = np.linspace(mg, D - mg, 7)
    zs = np.linspace(jaw_below, Hh - cm, 6)
    yaws = np.radians(np.arange(0, 360, step_deg) if yaws_deg is None else np.array(yaws_deg, float))
    corners = [(sx, sz) for sx in (1, -1) for sz in (1, -1)]
    mouth_bay = {c: np.array([c[0] * mouth, mouth_y, c[1] * mouth]) for c in corners}
    results = {}
    hit_el, hit_z, hit_pts = [], [], []
    for psi in yaws:
        ex = np.array([math.cos(psi), math.sin(psi)])
        ez = np.array([math.sin(psi), -math.cos(psi)])
        dirs, meta = [], []
        for (sx, sz) in corners:
            anc = anchors[CABLE_MAPPING[(sx, sz)]]
            for px in xs:
                for py in ys:
                    for pz in zs:
                        m_h = np.array([px, py]) + (sx * mouth / 1000.0) * ex + (sz * mouth / 1000.0) * ez
                        d = np.array([anc[0] - m_h[0], anc[1] - m_h[1], anc[2] - pz])
                        L = np.linalg.norm(d)
                        db = np.array([d[:2] @ ex, d[2], d[:2] @ ez])
                        dirs.append(db / L)
                        meta.append((sx, sz, px, py, pz, L * 1000.0, math.degrees(math.asin(d[2] / L))))
        dirs, meta = np.array(dirs), np.array(meta)
        hits = np.zeros(len(dirs), bool)
        mind = np.full(len(dirs), 1e9)
        feasible = np.ones(len(dirs), bool)
        for (sx, sz) in corners:
            sel = np.where((meta[:, 0] == sx) & (meta[:, 1] == sz))[0]
            o = mouth_bay[(sx, sz)]
            tb = np.array([ray_mesh_first_hit(o + d * 0.6, d[None, :], Vbox, Fbox)[0] for d in dirs[sel]])
            feasible[sel] = ~(tb < meta[sel, 5])
            t = ray_mesh_first_hit(o, dirs[sel], V, F)
            hits[sel] = t < meta[sel, 5]
            for kk, tt_ in zip(sel, t):
                if tt_ < meta[kk, 5]:
                    q = o + dirs[kk] * tt_
                    hit_pts.append((round(math.degrees(psi)), int(sx), int(sz), round(float(meta[kk, 6]), 1), round(float(q[0]), 1), round(float(q[1]), 1), round(float(-q[2]), 1)))
            rel = samples - o
            for k0 in range(0, len(sel), 256):
                ss = sel[k0:k0 + 256]
                dd = dirs[ss]
                tt = np.minimum(np.clip(rel @ dd.T, 0, None), meta[ss, 5][None, :])
                r2 = (rel ** 2).sum(1)[:, None]
                dist2 = r2 - 2 * tt * (rel @ dd.T) + tt ** 2
                mind[ss] = np.sqrt(np.maximum(dist2.min(axis=0), 0))
        mind_f = np.where(feasible, mind, 1e9)
        hits_f = hits & feasible
        h_el = [float(meta[ii, 6]) for ii in np.where(hits_f)[0]]
        h_z = [float(meta[ii, 4]) for ii in np.where(hits_f)[0]]
        hit_el += h_el
        hit_z += h_z
        i = int(mind_f.argmin())
        results[round(math.degrees(psi))] = {
            "min_clearance_mm": round(float(mind_f.min()), 2), "lines_hitting_bay": int(hits_f.sum()),
            "lines_feasible": int(feasible.sum()), "lines": len(dirs),
            "worst_elevation_deg": round(float(meta[i, 6]), 1), "worst_claw_z_m": round(float(meta[i, 4]), 2),
            "hit_elevation_deg": [round(min(h_el), 1), round(max(h_el), 1)] if h_el else None,
            "hit_claw_z_m": [round(min(h_z), 2), round(max(h_z), 2)] if h_z else None}
        if verbose:
            print(f"yaw {math.degrees(psi):5.0f}: min clearance {mind_f.min():7.2f} mm, hits {int(hits_f.sum())}/{int(feasible.sum())}")
    allc = {k: v["min_clearance_mm"] for k, v in results.items()}
    near = [k for k in allc if k <= 15 or k >= 345]
    return {
        "mouth_xz": mouth, "mouth_y": mouth_y, "jaw_below_mouth_m": jaw_below,
        "workspace_z_m": [jaw_below, Hh - cm],
        "nominal_yaw0_min_clearance_mm": allc[0],
        "yaw_pm15_min_clearance_mm": min(allc[k] for k in near),
        "all_yaw_min_clearance_mm": min(allc.values()), "worst_yaw_deg": min(allc, key=allc.get),
        "total_lines_hitting_bay": int(sum(v["lines_hitting_bay"] for v in results.values())),
        "hits_pm15deg": int(sum(results[k]["lines_hitting_bay"] for k in results if k <= 15 or k >= 345)),
        "hits_pm30deg": int(sum(results[k]["lines_hitting_bay"] for k in results if k <= 30 or k >= 330)),
        "hit_max_elevation_deg": round(max(hit_el), 1) if hit_el else None,
        "hit_min_claw_height_m": round(min(hit_z), 2) if hit_z else None,
        "per_yaw": results, "hit_points": hit_pts,
    }


def housing_renders(hr=None, hl=None):
    """Standard views of housing + bay and of the cover (print frame, z up), bay close-ups, and the assembly with Jasper's
    parts and both hands at the closed pose."""
    from cad.mesh_tools import tessellate, render
    G, orig, housing, cover = housing_load()
    os.makedirs(REND_DIR, exist_ok=True)
    BLUE = (0.25, 0.55, 0.88)
    hp = G.housing_to_print(housing).val()
    cp = G.cover_to_print(cover).val()
    standard_views(hp, "gripper1021_housing_cambay", BLUE, tol=0.1)
    standard_views(cp, "gripper1021_housing_cambay_cover", ORANGE, tol=0.05)
    # close-ups in the bay frame (+Y up; camera azimuth 90 = the bay (-Z) side)
    crop = cq.Workplane("XY").box(110, 70, 90, centered=False).translate((-55, -1, -115))
    near = housing.intersect(crop)
    nm, cm_ = tessellate(near, 0.15, 0.25), tessellate(cover, 0.15, 0.25)
    cb = ((-60, -2, -118), (60, 62, -22))
    render([nm + (BLUE, 1.0), cm_ + (ORANGE, 1.0)], os.path.join(REND_DIR, "bay_iso.png"), 28, 62,
           "Camera bay on Jasper's housing (cover fitted)", bounds=cb, up="y", dpi=150)
    render([nm + (BLUE, 1.0)], os.path.join(REND_DIR, "bay_iso_no_cover.png"), 42, 70,
           "Camera bay, cover removed", bounds=cb, up="y", dpi=150)
    render([nm + (BLUE, 1.0)], os.path.join(REND_DIR, "bay_underside_lens.png"), -70, 80,
           "Underside: lens window with 1 mm chamfer", bounds=cb, up="y", dpi=150)
    half = cq.Workplane("XY").box(60, 70, 90, centered=False).translate((G.LENS_X, -1, -115))
    sec = housing.intersect(half)
    csec = cover.intersect(cq.Workplane("XY").box(60, 70, 90, centered=False).translate((G.LENS_X, -1, -115)))
    render([tessellate(sec, 0.12, 0.25) + (BLUE, 1.0), tessellate(csec, 0.12, 0.25) + (ORANGE, 1.0)],
           os.path.join(REND_DIR, "bay_section_front.png"), 12, 180,
           f"Section through the lens centre (x = {G.LENS_X:+.2f}), seen from -X",
           bounds=((G.LENS_X - 5, -2, -118), (G.LENS_X + 55, 62, -22)), up="y", dpi=150)
    # assembly (world frame): Jasper's parts, new housing + bay + cover, both hands closed
    ox, oy, oz = G.BAY_ORIGIN_WORLD
    parts = load_jasper()
    fp = file_pose_angles(parts)
    moved = jasper_at(parts, fp, P.GRIP1021_THETA_CLOSED_DEG)
    meshes = []
    for k, shp in moved.items():
        if k != "elec_housing":
            meshes.append(tessellate(shp, 1.0, 0.5) + (GREY, 1.0))
    meshes.append(tessellate(G.to_world(housing.val()), 0.5, 0.4) + (BLUE, 1.0))
    meshes.append(tessellate(G.to_world(cover.val()), 0.2, 0.3) + (ORANGE, 1.0))
    hr = hr or H.make_hand_right()
    hl = hl or H.make_hand_left()
    meshes.append(tessellate(H.place_hand(hr, "R", P.GRIP1021_THETA_CLOSED_DEG).val(), 0.1, 0.3) + (HAND_BLUE, 1.0))
    meshes.append(tessellate(H.place_hand(hl, "L", P.GRIP1021_THETA_CLOSED_DEG).val(), 0.1, 0.3) + (HAND_GREEN, 1.0))
    render(meshes, os.path.join(REND_DIR, "assembly_iso.png"), 22, 55, "Gripper 1021: housing + camera bay + hands (closed)",
           bounds=((ox - 300, 560, oz - 300), (ox + 300, 1180, oz + 300)), up="y")
    render(meshes, os.path.join(REND_DIR, "assembly_bay_side.png"), 0, 90, "Gripper 1021 from the camera-bay (-Z) side",
           bounds=((ox - 330, 560, oz - 330), (ox + 330, 1200, oz + 330)), up="y")


def build_housing(renders=True, cables=True):
    rep = housing_report()
    rep["reimport"] = reimport_housing()
    rep["assembly"] = assembly_interference()
    if cables:
        rep["cables"] = cable_line_analysis(verbose=False)
    if renders:
        housing_renders()
    return rep


def print_housing_report(rep):
    f = lambda L: "[" + ", ".join(f"{v:.3f}" for v in L) + "]"
    print(f"valid={rep['valid']} solids housing/cover={rep['solids']}")
    print(f"volumes mm3: {', '.join(f'{k}={v:.0f}' for k, v in rep['vol'].items())}")
    print(f"mass g (PETG solid): {', '.join(f'{k}={v:.1f}' for k, v in rep['mass_g'].items())}")
    print(f"bbox housing+bay (bay frame) {f(rep['bbox'])}; cover {f(rep['cover_bbox'])}")
    print(f"removed from Jasper's housing: {rep['removed_vol']:.3f} mm3 (outside the window cutter {rep['removed_outside_window']:.6f}, "
          f"in pocket {rep['removed_in_pocket']:.6f}); added {rep['added_vol']:.0f} mm3 (inside the pocket {rep['added_in_pocket']:.6f})")
    print(f"bottom faces on y=0: areas {[round(a, 1) for a in rep['bottom_faces']]} (orig {rep['bottom_area_orig']:.1f})")
    print(f"lens centre world {tuple(round(v, 4) for v in rep['lens_world'])} (v6 {tuple(round(v, 4) for v in rep['lens_world_v6'])})")
    print(f"bay head vs v6 symmetric difference {rep['head_vs_v6_symdiff']:.6f} mm3 of {rep['head_vol']:.0f}; cover vs v6 (r>=65) {rep['cover_vs_v6_symdiff']:.6f}")
    print("distance bay (body+cover) to the four corner-hole cylinders:", f(rep["dist_bay_to_holes"]), "cover alone", f(rep["dist_cover_to_holes"]))
    print("cover vs housing overlap", rep["cover_vs_housing_overlap"])
    print("thin spots (<1.9 mm) in sections:", {k: v for k, v in rep["thin"].items() if v} or "none at all 18 levels")
    for k, d in rep["reimport"].items():
        print(f"[reimport {k}] solids={d['solids']} valid={d['valid']} vol {d['vol_ref']:.1f}->{d['vol_reimport']:.1f} "
              f"(rel {d['vol_rel_diff']:.1e}) bbox diff {d['bbox_max_diff_mm']:.5f}")
    print("assembly overlap (housing, cover) vs Jasper parts at the file pose:",
          {k: (round(a, 4), round(b, 4)) for k, (a, b) in rep["assembly"].items()})
    if "cables" in rep:
        c = rep["cables"]
        print(f"cable lines: yaw0 min clearance {c['nominal_yaw0_min_clearance_mm']} mm, within +-15 deg {c['yaw_pm15_min_clearance_mm']} mm "
              f"(hits {c['hits_pm15deg']}), +-30 deg hits {c['hits_pm30deg']}, all yaws min {c['all_yaw_min_clearance_mm']} mm at yaw {c['worst_yaw_deg']}, "
              f"total hits {c['total_lines_hitting_bay']}, hit elevation max {c['hit_max_elevation_deg']} deg, min claw height {c['hit_min_claw_height_m']} m")


# --------------------------------------------------------------------------------------------------------------------
# HOUSING with the THREE-CABLE holes ("_34", spec section 5): measurements, renders, build
# --------------------------------------------------------------------------------------------------------------------
STEP_NAME_34 = "gripper1021_housing_cambay_34"


def housing34_load():
    from cad.parts import gripper1021_housing_cambay as G
    orig = G.load_housing_bay_frame()
    base, cover = G.make()
    new, _ = G.make_34()
    return G, orig, base, new, cover


def _inside(shape, p):
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.TopAbs import TopAbs_IN
    from OCP.gp import gp_Pnt
    c = BRepClass3d_SolidClassifier(shape.wrapped)
    c.Perform(gp_Pnt(*p), 1e-7)
    return c.State() == TopAbs_IN


def measured_cylinder_axes(shape, centre, radius, near=8.0, tol=1e-6):
    """Axes (point, unit direction) of cylindrical faces of the given radius whose centre lies within `near` of `centre`."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    out = []
    for f in shape.Faces():
        if f.geomType() != "CYLINDER":
            continue
        c = BRepAdaptor_Surface(f.wrapped).Cylinder()
        if abs(c.Radius() - radius) < tol and (f.Center() - centre).Length < near:
            a = c.Axis()
            out.append((cq.Vector(a.Location().X(), a.Location().Y(), a.Location().Z()),
                        cq.Vector(a.Direction().X(), a.Direction().Y(), a.Direction().Z()), c.Radius()))
    return out


def _axis_plane_point(p0, d, normal, plane_n):
    """Point where the line p0 + s d meets the plane normal . x = plane_n."""
    s = (plane_n - normal.dot(p0)) / normal.dot(d)
    return p0 + d * s


def body_frame_m(G, p):
    """Box-frame point (mm) -> claw body frame (m): origin on the tube axis at the corner-hole inner-mouth height, +x = box x, +y = -box z, +z up."""
    return (p.x / 1000.0, -p.z / 1000.0, (p.y - P.CAMBAY1021_TRI_BODY_ORIGIN_Y) / 1000.0)


def corner_hole_points_body_m():
    """The four 1021 corner holes in the body frame (m): inner mouth (the 'attachment point' of verification/claw_body_frame.json) and outer
    mouth.  Order A, B, C, D as in that file: A (-X,+Z), B (+X,+Z), C (+X,-Z), D (-X,-Z) in box signs."""
    order = {"A": (-1, 1), "B": (1, 1), "C": (1, -1), "D": (-1, -1)}
    out = {}
    for st, (sx, sz) in order.items():
        inner = cq.Vector(sx * P.CAMBAY1021_CORNER_HOLE_INNER_XZ, P.CAMBAY1021_CORNER_HOLE_INNER_Y, sz * P.CAMBAY1021_CORNER_HOLE_INNER_XZ)
        outer = cq.Vector(sx * P.CAMBAY1021_CORNER_HOLE_EXIT_XZ, P.CAMBAY1021_CORNER_HOLE_EXIT_Y, sz * P.CAMBAY1021_CORNER_HOLE_EXIT_XZ)
        out[st] = {"inner_mouth": body_frame_m(None, inner), "outer_mouth": body_frame_m(None, outer)}
    return out


def housing34_keepouts(G, orig, new_removed_holes, added, cover):
    """Minimum distance (mm) from each hole's removed solid to every other feature.  Returns {hole: {feature: mm}}."""
    out = {}
    corner = hole_cylinders(G)
    window = G.wire_window_cutter().val()
    fr = G.tri_hole_frames()
    faces = orig.val().Faces()
    ledge = [f for f in faces if abs(f.BoundingBox().ymin - P.CAMBAY1021_BOX_LID_SEAT_Y) < 1e-3]
    floor_holes = [f for f in faces if f.geomType() == "CYLINDER" and abs(f.Area() - 25.92) < 0.01]
    tube = [f for f in faces if f.geomType() == "CYLINDER" and abs(f.Area() - 235.62) < 0.01]
    for hid, hs in new_removed_holes.items():
        own = fr[hid]
        # faces of Jasper's housing that the hole legitimately touches: its own outer wall face and the pocket wall face it opens into
        def own_face(f):
            if f.geomType() != "PLANE":
                return False
            n, c = f.normalAt(), f.Center()
            on_outer = n.dot(own["normal"]) > 0.999 and abs(c.dot(own["normal"]) - G.BOX_UPPER_HALF) < 1e-3
            on_inner = n.dot(own["normal"]) < -0.999 and abs(c.dot(own["normal"]) + G.POCKET_HALF) < 1e-3
            return on_outer or on_inner
        others = [f for f in faces if not own_face(f)]
        dmin, dface = min(((hs.distance(f), f) for f in others), key=lambda t: t[0])
        bb = dface.BoundingBox()
        out[hid] = {
            "corner_holes": min(hs.distance(c) for c in corner),
            "wire_window": hs.distance(window),
            "bay_body": hs.distance(added),
            "bay_cover": hs.distance(cover),
            "lid_seat_ledge": min(hs.distance(f) for f in ledge),
            "floor_holes_8x_d3p3": min(hs.distance(f) for f in floor_holes),
            "tube_hole": min(hs.distance(f) for f in tube),
            "any_other_face_of_jaspers_housing": dmin,
            "nearest_other_face": f"{dface.geomType()} area {dface.Area():.1f} bbox x[{bb.xmin:.1f},{bb.xmax:.1f}] y[{bb.ymin:.1f},{bb.ymax:.1f}] z[{bb.zmin:.1f},{bb.zmax:.1f}]",
        }
    return out


def housing34_report():
    """Measurements of the housing with the three-cable holes, expected vs measured (all from the built solids)."""
    G, orig, base, new, cover = housing34_load()
    o, b, n, cv = orig.val(), base.val(), new.val(), cover.val()
    fr = G.tri_hole_frames()
    petg = P.GRIP1021_PETG_G_CM3 / 1000.0
    rep = {"valid": n.isValid(), "solids": len(new.solids().vals())}
    bb0, bb1 = b.BoundingBox(), n.BoundingBox()
    rep["bbox_current"] = [bb0.xmin, bb0.xmax, bb0.ymin, bb0.ymax, bb0.zmin, bb0.zmax]
    rep["bbox_34"] = [bb1.xmin, bb1.xmax, bb1.ymin, bb1.ymax, bb1.zmin, bb1.zmax]
    rep["vol_current"], rep["vol_34"] = b.Volume(), n.Volume()
    rep["mass_g_current"], rep["mass_g_34"] = b.Volume() * petg, n.Volume() * petg
    removed, added_ = b.cut(n), n.cut(b)
    rep["removed_total_mm3"], rep["added_total_mm3"] = removed.Volume(), added_.Volume()
    rep["mass_removed_g"] = removed.Volume() * petg
    # --- the removed solids: three holes and three labels
    solids = removed.Solids()
    holes, labels = {}, {}
    for s_ in solids:
        c = s_.BoundingBox()
        bucket = holes if c.ymax <= 44.6 else labels
        mid = cq.Vector((c.xmin + c.xmax) / 2, (c.ymin + c.ymax) / 2, (c.zmin + c.zmax) / 2)
        hid = min(fr, key=lambda k: (fr[k]["outer"] + cq.Vector(0.0, 0.0 if bucket is holes else P.CAMBAY1021_TRI_LABEL_ABOVE, 0.0) - mid).Length)
        bucket[hid] = s_
    rep["removed_solids"] = {"holes": len(holes), "labels": len(labels), "total": len(solids)}
    r, k = G.TRI_R, G.TRI_TIP_K
    for hid, f in fr.items():
        d = {}
        # axis measured on the bore's cylindrical face
        cyl = measured_cylinder_axes(n, f["outer"], r)
        assert len(cyl) == 1, (hid, len(cyl))
        p0, dd, rad = cyl[0]
        dd = dd if dd.dot(f["axis"]) > 0 else dd * -1.0
        outer_m = _axis_plane_point(p0, dd, f["normal"], G.BOX_UPPER_HALF)
        inner_m = _axis_plane_point(p0, dd, f["normal"], G.POCKET_HALF)
        d["diameter_measured"] = 2.0 * rad
        d["axis_dir_measured"] = dd.toTuple()
        d["axis_angle_error_deg"] = math.degrees(math.acos(min(1.0, abs(dd.dot(f["axis"])))))
        d["outer_mouth_expected"], d["outer_mouth_measured"] = f["outer"].toTuple(), outer_m.toTuple()
        d["inner_mouth_expected"], d["inner_mouth_measured"] = f["inner"].toTuple(), inner_m.toTuple()
        d["outer_mouth_error_mm"] = (outer_m - f["outer"]).Length
        d["inner_mouth_error_mm"] = (inner_m - f["inner"]).Length
        d["wall_length_expected"], d["wall_length_measured"] = f["length"], (outer_m - inner_m).Length
        # volume removed by the hole (boolean difference to the current housing)
        hv = holes[hid].Volume()
        L = f["length"]
        plain = math.pi * r * r * L
        tear = G.teardrop_area() * L
        d["removed_mm3"] = hv
        d["plain_bore_mm3"], d["teardrop_bore_mm3"] = plain, tear
        d["ratio_to_plain_bore"] = hv / plain
        d["chamfer_extra_mm3"] = hv - tear
        # bore only: the part of the removed solid deeper than the chamfer (wall-normal coordinate 40 .. 44.2), against the plain bore of that length
        depth_hi = G.BOX_UPPER_HALF - 0.8
        slab = cq.Workplane(cq.Plane(origin=f["outer"], xDir=f["reading_dir"], normal=f["normal"])).rect(40.0, 40.0).extrude(-(depth_hi * 0 + (G.BOX_UPPER_HALF - G.POCKET_HALF) - 0.8)).val()
        deep = holes[hid].intersect(slab).Volume()
        deep_len = (G.BOX_UPPER_HALF - 0.8 - G.POCKET_HALF) / abs(f["normal"].dot(f["axis"]))
        d["deep_bore_mm3"], d["deep_bore_ratio_to_plain"] = deep, deep / (math.pi * r * r * deep_len)
        d["deep_bore_ratio_expected_teardrop"] = G.teardrop_area() / (math.pi * r * r)
        # probes on the built solid: empty along the axis, circle and tip, solid just outside
        mid = (f["outer"] + f["inner"]) * 0.5
        up, tg = cq.Vector(0, 1, 0), f["reading_dir"]
        P_ = lambda h, u, base_=mid: base_ + up * h + tg * u
        probes = {
            "axis_empty": all(not _inside(n, (mid + f["axis"] * t).toTuple()) for t in (-2.4, -1.0, 0.0, 1.0, 2.4)),
            "circle_empty_r0p98": all(not _inside(n, P_(0.98 * math.sin(a), 0.98 * math.cos(a)).toTuple()) for a in (-1.2, -1.57, -1.9, 0.0, 3.1416)),
            "outside_circle_solid_r1p02": all(_inside(n, P_(1.02 * math.sin(a), 1.02 * math.cos(a)).toTuple()) for a in (-1.2, -1.57, -1.9, 0.0, 3.1416)),
            "tip_empty_1p30_above_axis": not _inside(n, P_(1.30, 0.0).toTuple()),
            "tip_solid_1p50_above_axis": _inside(n, P_(1.50, 0.0).toTuple()),
            "flank_empty_below_line": not _inside(n, P_(r / math.sin(k) - 0.5 - 0.05, 0.5).toTuple()),
            "flank_solid_above_line": _inside(n, P_(r / math.sin(k) - 0.5 + 0.05, 0.5).toTuple()),
        }
        # chamfer 0.5 x 45 deg at the lateral centre of the bottom lip: line y = (axis_y - r - c) + depth
        c_ = P.CAMBAY1021_TRI_CHAMFER
        def lip(depth, dy, f=f):
            return f["outer"] - f["normal"] * depth + up * (-r - c_ + depth + dy)
        probes["chamfer_empty_inside_cone"] = all(not _inside(n, lip(dp, +0.05).toTuple()) for dp in (0.1, 0.25, 0.4))
        probes["chamfer_solid_below_cone"] = all(_inside(n, lip(dp, -0.05).toTuple()) for dp in (0.1, 0.25, 0.4))
        d["probes"] = probes
        rep.setdefault("holes", {})[hid] = d
    # --- labels
    for hid, f in fr.items():
        ls = labels[hid]
        c = ls.BoundingBox()
        centre = cq.Vector((c.xmin + c.xmax) / 2, (c.ymin + c.ymax) / 2, (c.zmin + c.zmax) / 2)
        exp_c = f["outer"] + cq.Vector(0.0, P.CAMBAY1021_TRI_LABEL_ABOVE, 0.0)
        ext_n = max((cq.Vector(*v) - f["outer"]).dot(f["normal"]) for v in [(c.xmin, c.ymin, c.zmin), (c.xmax, c.ymax, c.zmax), (c.xmin, c.ymin, c.zmax), (c.xmax, c.ymax, c.zmin)])
        ext_n2 = min((cq.Vector(*v) - f["outer"]).dot(f["normal"]) for v in [(c.xmin, c.ymin, c.zmin), (c.xmax, c.ymax, c.zmax), (c.xmin, c.ymin, c.zmax), (c.xmax, c.ymax, c.zmin)])
        tg = f["reading_dir"]
        width = max(abs((cq.Vector(*v) - centre).dot(tg)) for v in [(c.xmin, c.ymin, c.zmin), (c.xmax, c.ymax, c.zmax), (c.xmin, c.ymin, c.zmax), (c.xmax, c.ymax, c.zmin)]) * 2
        # reading test: probe the stroke pattern of the letter in the label frame (u along the reading direction, h up)
        def lp(u, h, f=f, centre=centre):
            return (centre + f["reading_dir"] * u + cq.Vector(0, 1, 0) * h + f["normal"] * 0.0)
        wall_pt = lambda u, h: lp(u, h) + f["normal"] * (-(P.CAMBAY1021_TRI_LABEL_DEPTH / 2))            # mid-depth of the deboss
        pat = {}
        if hid == "A":       # apex at the top centre, two legs at the bottom
            pat = {"apex_top_centre_cut": not _inside(n, wall_pt(0.0, 1.5).toTuple()), "legs_bottom_cut": (not _inside(n, wall_pt(-1.2, -1.7).toTuple())) and (not _inside(n, wall_pt(1.2, -1.7).toTuple())),
                   "top_corners_not_cut": _inside(n, wall_pt(-1.2, 1.7).toTuple()) and _inside(n, wall_pt(1.2, 1.7).toTuple())}
        elif hid == "B":     # vertical stem on the left, bowls to the right
            pat = {"stem_left_cut": not _inside(n, wall_pt(-0.9, 0.0).toTuple()), "left_of_stem_not_cut": _inside(n, wall_pt(-1.6, 0.0).toTuple()),
                   "bowl_right_cut": not _inside(n, wall_pt(0.95, 1.6).toTuple()) or not _inside(n, wall_pt(1.0, -1.6).toTuple())}
        else:                # C: opening to the right, stroke on the left
            pat = {"stroke_left_cut": not _inside(n, wall_pt(-1.35, 0.0).toTuple()), "opening_right_not_cut": _inside(n, wall_pt(1.2, 0.0).toTuple())}
        rep.setdefault("labels", {})[hid] = {"height_mm": c.ymax - c.ymin, "width_mm": width, "centre_error_mm": (centre - exp_c).Length if False else
                                             math.hypot((centre - exp_c).dot(tg), centre.y - exp_c.y), "depth_mm": ext_n - ext_n2 if False else -ext_n2,
                                             "volume_mm3": ls.Volume(), "reading_pattern": pat}
    # --- keep-outs and confinement
    added = n.cut(o)                                                   # material the bay adds (housing + bay + holes minus Jasper's housing)
    hs_min = housing34_keepouts(G, orig, holes, G.make_bay_body().val(), cv)
    rep["keepouts_mm"] = hs_min
    zone = []
    conf = P.CAMBAY1021_TRI_CONFINE
    for hid, f in fr.items():
        zone.append(cq.Solid.makeCylinder(r + conf, f["length"] + 2 * conf, f["inner"] - f["axis"] * conf, f["axis"]))
        lab_c = f["outer"] + cq.Vector(0.0, P.CAMBAY1021_TRI_LABEL_ABOVE, 0.0)
        box = cq.Workplane(cq.Plane(origin=lab_c, xDir=f["reading_dir"], normal=f["normal"])).rect(P.CAMBAY1021_TRI_LABEL_H * 1.5 + 2 * conf, P.CAMBAY1021_TRI_LABEL_H + 2 * conf).extrude(-(G.BOX_UPPER_HALF - G.POCKET_HALF + conf)).val()
        zone.append(box)
    z = zone[0]
    for s_ in zone[1:]:
        z = z.fuse(s_)
    rep["removed_outside_confinement_mm3"] = removed.cut(z).Volume()
    rep["added_outside_confinement_mm3"] = added_.Volume()
    # --- corner holes and bay unchanged: same removed/added test against the sub-features
    pocket = cq.Solid.makeBox(2 * G.POCKET_HALF, 50.0, 2 * G.POCKET_HALF, cq.Vector(-G.POCKET_HALF, G.POCKET_FLOOR_Y, -G.POCKET_HALF))
    rep["removed_in_pocket_mm3"] = removed.intersect(pocket).Volume()
    # --- body frame points (m)
    rep["body_frame_m"] = {hid: {"outer_mouth": body_frame_m(G, rep["holes"][hid] and cq.Vector(*rep["holes"][hid]["outer_mouth_measured"])),
                                  "inner_mouth": body_frame_m(G, cq.Vector(*rep["holes"][hid]["inner_mouth_measured"]))} for hid in fr}
    rep["corner_holes_body_m"] = corner_hole_points_body_m()
    # --- exports: STEP re-import, STL orientation
    paths = G.export_all_34(STEP_DIR, STL_DIR)
    rep["reimport"] = reimport_check(paths[STEP_NAME_34]["step"], G.to_world(n))
    rep["exports"] = paths
    return rep


def housing34_stl_check(path):
    import struct
    import numpy as np
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw[:5] == b"solid" and b"facet" in raw[:400]:
        v = np.array([[float(t) for t in ln.split()[1:4]] for ln in raw.decode().splitlines() if ln.strip().startswith("vertex")])
    else:
        nt = struct.unpack("<I", raw[80:84])[0]
        v = np.frombuffer(raw[84:84 + 50 * nt], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))["v"].reshape(-1, 3)
    return v.min(axis=0).tolist(), v.max(axis=0).tolist()


def housing34_renders():
    """Standard views of the _34 housing (print frame, z up) and one close-up per hole (box frame, camera outside the hole's wall)."""
    from cad.mesh_tools import tessellate, render
    G, orig, base, new, cover = housing34_load()
    os.makedirs(REND_DIR, exist_ok=True)
    BLUE = (0.25, 0.55, 0.88)
    standard_views(G.housing_to_print(new).val(), STEP_NAME_34, BLUE, tol=0.1)
    fr = G.tri_hole_frames()
    paths = []
    for hid, f in fr.items():
        c = f["outer"] + cq.Vector(0.0, 3.0, 0.0)
        half = 9.0
        crop = cq.Workplane("XY").box(2 * half + 8.0, 2 * half + 8.0, 2 * half + 8.0).translate(c.toTuple())
        near = new.intersect(crop)
        mesh = tessellate(near, 0.01, 0.1)
        # camera azimuth in the up='y' plot frame (plot x = x, plot y = -z): the outward wall normal sets it
        nx, nz = f["normal"].x, f["normal"].z
        az = math.degrees(math.atan2(-nz, nx))
        path = os.path.join(REND_DIR, f"{STEP_NAME_34}_closeup_{hid}.png")
        render([mesh + (BLUE, 1.0)], path, 12, az, f"T_{hid}: teardrop hole, chamfer and label (outer wall, box upright)",
               bounds=((c.x - half, c.y - half, c.z - half), (c.x + half, c.y + half, c.z + half)), up="y", dpi=150, size=(6, 6))
        paths.append(path)
    return paths


def build_housing34(renders=True, cables=True):
    rep = housing34_report()
    lo, hi = housing34_stl_check(os.path.join(STL_DIR, STEP_NAME_34 + ".stl"))
    rep["stl_bbox"] = {"min": lo, "max": hi}
    if cables:
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        import analyze_cable_lines_housing_34 as A34
        res = A34.analyze(verbose=False)
        with open(A34.OUT, "w") as fh:
            json.dump(res, fh, indent=1)
        rep["cables"] = res
    if renders:
        rep["renders"] = housing34_renders()
    with open(os.path.join(VER_DIR, "gripper1021_housing_34_measurements.json"), "w") as fh:
        json.dump(rep, fh, indent=1, default=str)
    return rep


def print_housing34_report(rep):
    f3 = lambda v: "(" + ", ".join(f"{x:.4f}" for x in v) + ")"
    print(f"valid={rep['valid']} solids={rep['solids']}; vol current {rep['vol_current']:.2f} -> _34 {rep['vol_34']:.2f} mm3; "
          f"mass {rep['mass_g_current']:.3f} -> {rep['mass_g_34']:.3f} g (removed {rep['removed_total_mm3']:.3f} mm3 = {rep['mass_removed_g']:.4f} g); added {rep['added_total_mm3']:.6f} mm3")
    print("bbox current", [round(v, 4) for v in rep["bbox_current"]], "_34", [round(v, 4) for v in rep["bbox_34"]])
    print("removed solids", rep["removed_solids"], "removed outside the 3 mm confinement", rep["removed_outside_confinement_mm3"], "in pocket", rep["removed_in_pocket_mm3"])
    for hid, d in rep["holes"].items():
        print(f"[T_{hid}] D {d['diameter_measured']:.4f}; outer mouth exp {f3(d['outer_mouth_expected'])} meas {f3(d['outer_mouth_measured'])} err {d['outer_mouth_error_mm']:.2e}; "
              f"inner exp {f3(d['inner_mouth_expected'])} meas {f3(d['inner_mouth_measured'])} err {d['inner_mouth_error_mm']:.2e}; axis angle err {d['axis_angle_error_deg']:.2e} deg; "
              f"wall length exp {d['wall_length_expected']:.4f} meas {d['wall_length_measured']:.4f}")
        print(f"      removed {d['removed_mm3']:.3f} mm3 vs plain Ø2 bore {d['plain_bore_mm3']:.3f} (ratio {d['ratio_to_plain_bore']:.4f}); teardrop bore {d['teardrop_bore_mm3']:.3f}; chamfer extra {d['chamfer_extra_mm3']:.3f}; "
              f"deep bore ratio {d['deep_bore_ratio_to_plain']:.4f} (teardrop expected {d['deep_bore_ratio_expected_teardrop']:.4f})")
        print("      probes:", {k: v for k, v in d["probes"].items()})
        ko = rep["keepouts_mm"][hid]
        print("      keep-outs mm:", {k: (round(v, 2) if not isinstance(v, str) else v) for k, v in ko.items()})
    for hid, d in rep["labels"].items():
        print(f"[label {hid}] height {d['height_mm']:.3f} width {d['width_mm']:.3f} centre err {d['centre_error_mm']:.3f} depth {d['depth_mm']:.3f} vol {d['volume_mm3']:.3f}; reading {d['reading_pattern']}")
    print("body frame (m) outer mouths:", {k: f3(v["outer_mouth"]) for k, v in rep["body_frame_m"].items()})
    print("body frame (m) inner mouths:", {k: f3(v["inner_mouth"]) for k, v in rep["body_frame_m"].items()})
    print("corner holes body (m):", {k: {kk: f3(vv) for kk, vv in v.items()} for k, v in rep["corner_holes_body_m"].items()})
    r = rep["reimport"]
    print(f"[reimport] solids={r['solids']} valid={r['valid']} vol {r['vol_ref']:.2f}->{r['vol_reimport']:.2f} (rel {r['vol_rel_diff']:.1e}) bbox diff {r['bbox_max_diff_mm']:.5f}")
    print("STL bbox", rep.get("stl_bbox"))
    if "cables" in rep:
        c = rep["cables"]
        print(f"cable lines: min {c['min_distance_mm']} mm at {c['min_at']}; bay+cover only {c['min_distance_bay_cover_only_mm']} mm; below 5 mm: {c['lines_below_required']} of {c['lines_scored']}")


def main(argv):
    what = argv[1] if len(argv) > 1 else "hands"
    if what == "hands-renders":
        hr, hl = H.make_hand_right(), H.make_hand_left()
        parts = load_jasper()
        print(pose_figure(parts, file_pose_angles(parts), hr, hl, os.path.join(REND_DIR, "hands_on_mechanism_poses.png")))
        for nm, wp, col in (("hand_right", hr, HAND_BLUE), ("hand_left", hl, HAND_GREEN)):
            standard_views(wp.val(), "gripper1021_" + nm, col)
    if what in ("hands", "all"):
        print_hands_report(build_hands(dense=True))
    if what == "housing-renders":
        housing_renders()
    if what in ("housing", "all"):
        print_housing_report(build_housing())
    if what == "housing-34-renders":
        print(housing34_renders())
    if what in ("housing-34", "all"):
        print_housing34_report(build_housing34())


if __name__ == "__main__":
    main(sys.argv)
