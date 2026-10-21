#!/usr/bin/python3
"""
Build, export and check the Gripper 1021 parts (hands first, then housing + camera bay).

Run:  /usr/bin/python3 scripts/build_gripper1021.py hands      # hands: exports, sweep, clearances, renders (~5 min)
      /usr/bin/python3 scripts/build_gripper1021.py hands-renders   # renders only
      /usr/bin/python3 scripts/build_gripper1021.py housing    # housing + bay + cover
      /usr/bin/python3 scripts/build_gripper1021.py all

Reads (read-only): cad/reference/gripper_1021/parts/*.step (Jasper's parts, assembly world frame).
Writes:
  exports/step/gripper1021_hand_right.step   right hand at Jasper's file pose (theta = -52.1 deg), world frame
  exports/step/gripper1021_hand_left.step    left hand, mirrored pose (follower rotated -6 deg into mesh)
  exports/stl/gripper1021_hand_{right,left}.stl   print orientation (bed face z = 1090 down, z min = 0)
  renders/gripper1021/...                    standard views + closed / open pose images on the mechanism
  verification/gripper1021_sweep.json        sweep overlap table (machine readable)
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
    if what in ("housing", "all"):
        raise SystemExit("housing build is added in the housing step")


if __name__ == "__main__":
    main(sys.argv)
