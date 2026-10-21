#!/usr/bin/python3
"""
Cable-line clearance for the THREE-CABLE holes of the Gripper 1021 electrical housing (cad/GRIPPER_1021_SPEC.md section 5).
Adapted from scripts/analyze_cable_lines_claw_camera_bay.py (that script is unchanged and still analyses the v6 corner holes).

Run:  /usr/bin/python3 scripts/analyze_cable_lines_housing_34.py
Reads config/robot.sim.json (room size, workspace_margin_m, ceiling_margin_m) -- read-only.
Writes verification/gripper1021_housing_34_cable_lines.json

Model
  * Hole k (C, A, B) leaves the housing at its OUTER mouth centre (box frame, cad.parts.gripper1021_housing_cambay.tri_hole_frames()).
    The line runs from that mouth straight to the station anchor prior (CAMBAY1021_TRI_ANCHORS_ROOM_M, docs/THREE_STATION_MODE_SPEC.md).
  * Room frame: x east, y north, z up.  Claw yaw psi rotates the box frame about the vertical: box +x -> room (cos psi, sin psi),
    box +z -> room (sin psi, -cos psi), so body +y = -box z = room +y at psi = 0 (the bay, and hole C, face room +y = station C).
  * Claw reference = the tube axis at the height of the three outer mouths (box y = CAMBAY1021_TRI_Y).  Workspace, as the spec says:
    floor projection inside the A-B-C triangle AND the wall margin (0.2 m), heights from the lowest working height (closed fingertip
    on the floor: mouth height - GRIP1021_TIP_Y) to 0.4 m below the anchors; claw yaw -15 .. +15 deg.
  * A line is FEASIBLE if it leaves the housing, i.e. its direction has a positive component along the hole's outward wall normal.
    Lines that would have to run back into the housing are physically impossible for that pose and are counted, not scored.
  * Clearance of a line = minimum distance from the line (mouth -> anchor) to every exterior surface of housing + bay + cover,
    EXCEPT the line's own outer wall face (the flat wall region around its mouth, incl. its bore, chamfer and label): a line that
    leaves a wall never meets that wall's face again, so "away from its own mouth" = everything but its own wall face.  The pocket
    (interior) surfaces are excluded too: the cable is outside the housing.  The wall's top rim edge is NOT excluded.
  * Surface sampled at <= SAMPLE_AREA mm2 per point plus its edges at <= EDGE_STEP mm; distances from a KD-tree, the line sampled every
    LINE_STEP mm over its first LINE_LEN mm (the housing is within 160 mm of every mouth).  Sampling error: distances over-estimate by
    less than about 0.3 mm.
"""

from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                      # noqa: E402
from cad.parts import gripper1021_housing_cambay as G            # noqa: E402
from cad.mesh_tools import tessellate                            # noqa: E402

CONFIG = os.path.join(REPO, "config", "robot.sim.json")
OUT = os.path.join(REPO, "verification", "gripper1021_housing_34_cable_lines.json")
SAMPLE_AREA = 0.3          # mm2 of surface per sample point
EDGE_STEP = 0.25           # mm between samples along triangle edges
LINE_STEP = 0.25           # mm between points on a line
LINE_LEN = 250.0           # mm of each line that is scored (from the mouth)
WALL_FLAT_HALF = G.BOX_UPPER_HALF - P.CAMBAY1021_TRI_CORNER_R     # 35: flat part of an outer wall
INTERIOR_HALF = P.CAMBAY1021_TRI_LID_RECESS_HALF          # pocket + lid recess are inside |x|, |z| <= 42.5
RIM_Y = P.CAMBAY1021_BOX_TOP_Y
MIN_ALLOWED_MM = P.CAMBAY1021_TRI_KEEPOUT


def surface_cloud(shapes, area_per_sample=SAMPLE_AREA, edge_step=EDGE_STEP, seed=0):
    """Points on the surface of each shape (vertices + area-weighted random points + points along triangle edges).
    Returns (points, source index per point)."""
    rng = np.random.default_rng(seed)
    pts, src = [], []
    for si, shp in enumerate(shapes):
        V, F = tessellate(shp, 0.05, 0.2)
        tri = V[F]
        area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
        n = np.maximum(1, np.ceil(area / area_per_sample).astype(int))
        idx = np.repeat(np.arange(len(F)), n)
        w = rng.dirichlet([1.0, 1.0, 1.0], size=len(idx))
        parts = [V, np.einsum("ij,ijk->ik", w, tri[idx])]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ln = np.linalg.norm(tri[:, b] - tri[:, a], axis=1)
            m = np.maximum(1, np.ceil(ln / edge_step).astype(int))
            e_idx = np.repeat(np.arange(len(F)), m)
            t = (np.concatenate([np.arange(k) for k in m]) + 0.5) / np.repeat(m, m)
            parts.append(tri[e_idx, a] + (tri[e_idx, b] - tri[e_idx, a]) * t[:, None])
        p = np.concatenate(parts)
        pts.append(p)
        src.append(np.full(len(p), si))
    return np.concatenate(pts), np.concatenate(src)


def own_wall_mask(points, fr):
    """Samples that belong to the hole's own outer wall: the wall slab (pocket plane to 0.5 mm outside the outer plane) over the flat
    part of the wall, up to just below the rim (the rim edge itself is kept)."""
    n = points @ np.array(fr["normal"].toTuple())                       # distance along the outward wall normal
    tang = points @ np.array((fr["reading_dir"].x, fr["reading_dir"].y, fr["reading_dir"].z))
    return ((n >= G.POCKET_HALF - 0.05) & (n <= G.BOX_UPPER_HALF + 0.5) & (np.abs(tang) <= WALL_FLAT_HALF + 1e-3)
            & (points[:, 1] >= 31.0) & (points[:, 1] <= RIM_Y - 0.1))


def interior_mask(points):
    """Pocket and lid-recess surfaces (inside the housing): |x|, |z| <= 42.5 above the pocket floor."""
    return (np.abs(points[:, 0]) <= INTERIOR_HALF + 0.05) & (np.abs(points[:, 2]) <= INTERIOR_HALF + 0.05) & (points[:, 1] >= P.CAMBAY1021_BOX_POCKET_FLOOR_Y - 0.01)


def classify(q, source):
    """Which part of the housing a nearest point belongs to (box frame)."""
    if source == 1:
        return "cover"
    if q[2] < -G.BOX_UPPER_HALF - 0.05 and q[1] < 40.0:
        return "bay"
    if q[1] >= RIM_Y - 0.1:
        return "box rim (top edge)"
    if abs(q[0]) > WALL_FLAT_HALF and abs(q[2]) > WALL_FLAT_HALF:
        return "box corner (R10)"
    if abs(q[1] - P.CAMBAY1021_BOX_LID_SEAT_Y) < 6.0:
        return "box upper wall"
    return "other box surface"


def clip_polygon(poly, xmin, xmax, ymin, ymax):
    """Sutherland-Hodgman clip of a convex/any polygon to a rectangle."""
    def clip(pts, inside, inter):
        out = []
        for i, cur in enumerate(pts):
            prev = pts[i - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(inter(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(inter(prev, cur))
        return out

    def ix(xc):
        return lambda a, b: (xc, a[1] + (b[1] - a[1]) * (xc - a[0]) / (b[0] - a[0]))

    def iy(yc):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (yc - a[1]) / (b[1] - a[1]), yc)

    pts = list(poly)
    for inside, inter in ((lambda p: p[0] >= xmin, ix(xmin)), (lambda p: p[0] <= xmax, ix(xmax)),
                          (lambda p: p[1] >= ymin, iy(ymin)), (lambda p: p[1] <= ymax, iy(ymax))):
        pts = clip(pts, inside, inter)
    return pts


def in_triangle(p, a, b, c):
    def s(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
    d1, d2, d3 = s(p, a, b), s(p, b, c), s(p, c, a)
    return not ((d1 < -1e-12 or d2 < -1e-12 or d3 < -1e-12) and (d1 > 1e-12 or d2 > 1e-12 or d3 > 1e-12))


def workspace_points(anchors, W, D, mg, step):
    """Floor positions: a grid over the wall-margin rectangle, kept if inside the anchor triangle, plus the vertices of the clipped
    triangle (the corner cases nearest to the anchors) and the centroid."""
    tri = [(a[0], a[1]) for a in anchors]
    xs = np.arange(mg, W - mg + 1e-9, step)
    ys = np.arange(mg, D - mg + 1e-9, step)
    pts = [(float(x), float(y)) for x in xs for y in ys if in_triangle((x, y), *tri)]
    pts += [tuple(map(float, v)) for v in clip_polygon(tri, mg, W - mg, mg, D - mg)]
    pts.append((sum(t[0] for t in tri) / 3.0, sum(t[1] for t in tri) / 3.0))
    return sorted(set((round(x, 6), round(y, 6)) for x, y in pts))


def analyze(grid_step=0.15, z_levels=8, yaws_deg=None, verbose=True, area_per_sample=SAMPLE_AREA):
    from scipy.spatial import cKDTree
    cfg = json.load(open(CONFIG))
    room = cfg["room"]
    W, D = room["width_m"], room["depth_m"]
    mg, cm = cfg["motion"]["workspace_margin_m"], cfg["motion"]["ceiling_margin_m"]
    frames = G.tri_hole_frames()
    ids = list(frames)
    anchors = {hid: np.array(a) for hid, a in zip(P.CAMBAY1021_TRI_IDS, P.CAMBAY1021_TRI_ANCHORS_ROOM_M)}
    jaw_below = (P.CAMBAY1021_BAY_ORIGIN_WORLD[1] + P.CAMBAY1021_TRI_Y - P.GRIP1021_TIP_Y) / 1000.0
    z_hi = min(a[2] for a in anchors.values()) - cm
    zs = np.linspace(jaw_below, z_hi, z_levels)
    floor_pts = workspace_points([anchors[i] for i in ids], W, D, mg, grid_step)
    yaw_lim = P.CAMBAY1021_TRI_YAW_RANGE_DEG
    yaws = np.radians(np.array([-yaw_lim, -yaw_lim / 2, 0.0, yaw_lim / 2, yaw_lim] if yaws_deg is None else yaws_deg, float))

    housing, cover = G.make_34()
    pts, src = surface_cloud([housing.val(), cover.val()], area_per_sample)
    keep = ~interior_mask(pts)
    pts, src = pts[keep], src[keep]
    if verbose:
        print(f"surface samples (exterior) {len(pts)}; floor positions {len(floor_pts)}; heights {zs[0]:.3f}..{zs[-1]:.3f} m x {z_levels}; "
              f"yaws {np.degrees(yaws).round(1).tolist()}")
    # the bay alone, as the original analysis scored it: the material the bay adds to Jasper's housing, plus the cover
    added = housing.val().cut(G.load_housing_bay_frame().val())
    bay_pts, _ = surface_cloud([added, cover.val()], area_per_sample)
    bay_tree = cKDTree(bay_pts)
    trees, tree_idx = {}, {}
    for hid in ids:
        ok = np.where(~own_wall_mask(pts, frames[hid]))[0]
        tree_idx[hid] = ok
        trees[hid] = cKDTree(pts[ok])

    tline = np.arange(0.0, LINE_LEN + 1e-9, LINE_STEP)
    rows = []          # per scored line: dict arrays collected below
    totals = {hid: {"lines": 0, "feasible": 0, "infeasible": 0} for hid in ids}
    rec = {k: [] for k in ("hole", "yaw", "px", "py", "pz", "elev", "gamma", "dist", "dist_bay", "qx", "qy", "qz", "part", "L")}
    for psi in yaws:
        ex = np.array([math.cos(psi), math.sin(psi)])
        ez = np.array([math.sin(psi), -math.cos(psi)])
        for hid in ids:
            fr = frames[hid]
            m = np.array(fr["outer"].toTuple())
            nrm = np.array(fr["normal"].toTuple())
            axis = np.array(fr["axis"].toTuple())
            anc = anchors[hid]
            dirs, meta = [], []
            for (px, py) in floor_pts:
                for pz in zs:
                    mh = np.array([px, py]) + (m[0] / 1000.0) * ex + (m[2] / 1000.0) * ez
                    d = np.array([anc[0] - mh[0], anc[1] - mh[1], anc[2] - pz])
                    L = np.linalg.norm(d)
                    db = np.array([d[:2] @ ex, d[2], d[:2] @ ez]) / L
                    dirs.append(db)
                    meta.append((px, py, pz, L * 1000.0))
            dirs, meta = np.array(dirs), np.array(meta)
            totals[hid]["lines"] += len(dirs)
            feas = dirs @ nrm > 1e-6
            totals[hid]["feasible"] += int(feas.sum())
            totals[hid]["infeasible"] += int((~feas).sum())
            sel = np.where(feas)[0]
            for k0 in range(0, len(sel), 400):
                ss = sel[k0:k0 + 400]
                tt = np.minimum(tline[None, :], meta[ss, 3][:, None])             # clip the scored length to the line length
                P3 = m[None, None, :] + dirs[ss][:, None, :] * tt[:, :, None]
                dist, ii = trees[hid].query(P3.reshape(-1, 3), workers=-1)
                dist, ii = dist.reshape(len(ss), -1), ii.reshape(len(ss), -1)
                dbay = bay_tree.query(P3.reshape(-1, 3), workers=-1)[0].reshape(len(ss), -1).min(axis=1)
                jbest = dist.argmin(axis=1)
                for r, s_ in enumerate(ss):
                    j = jbest[r]
                    q = pts[tree_idx[hid][ii[r, j]]]
                    qs = src[tree_idx[hid][ii[r, j]]]
                    d_ = dirs[s_]
                    rec["hole"].append(hid)
                    rec["yaw"].append(math.degrees(psi))
                    rec["px"].append(meta[s_, 0]); rec["py"].append(meta[s_, 1]); rec["pz"].append(meta[s_, 2])
                    rec["elev"].append(math.degrees(math.asin(d_[1])))
                    # angle between the horizontal part of the line and the hole axis
                    hz = np.array([d_[0], d_[2]])
                    gam = math.degrees(math.acos(np.clip((hz @ np.array([axis[0], axis[2]])) / (np.linalg.norm(hz) or 1.0), -1, 1)))
                    rec["gamma"].append(gam)
                    rec["dist"].append(float(dist[r, j]))
                    rec["dist_bay"].append(float(dbay[r]))
                    rec["qx"].append(float(q[0])); rec["qy"].append(float(q[1])); rec["qz"].append(float(q[2]))
                    rec["part"].append(classify(q, qs))
                    rec["L"].append(float(meta[s_, 3]))
        if verbose:
            cur = [rec["dist"][i] for i in range(len(rec["dist"])) if abs(rec["yaw"][i] - math.degrees(psi)) < 1e-9]
            print(f"yaw {math.degrees(psi):6.1f}: min distance {min(cur):7.2f} mm over {len(cur)} feasible lines")

    R = {k: np.array(v) for k, v in rec.items()}
    d = R["dist"]
    iw = int(d.argmin())
    out = {
        "model": __doc__,
        "workspace": {"floor_positions": len(floor_pts), "heights_m": [round(float(z), 4) for z in zs], "yaws_deg": np.degrees(yaws).round(2).tolist(),
                      "room_m": [W, D], "wall_margin_m": mg, "ceiling_margin_m": cm, "z_anchor_m": float(max(a[2] for a in anchors.values()))},
        "totals": totals, "sample_points": int(len(pts)), "required_min_mm": MIN_ALLOWED_MM,
        "min_distance_mm": round(float(d.min()), 3),
        "min_at": {"hole": str(R["hole"][iw]), "claw_xyz_m": [float(R["px"][iw]), float(R["py"][iw]), float(R["pz"][iw])],
                   "yaw_deg": float(R["yaw"][iw]), "line_elevation_deg": round(float(R["elev"][iw]), 2),
                   "angle_to_hole_axis_deg": round(float(R["gamma"][iw]), 2), "nearest_point_box_mm": [round(float(R["qx"][iw]), 2), round(float(R["qy"][iw]), 2), round(float(R["qz"][iw]), 2)],
                   "nearest_part": str(R["part"][iw]), "line_length_m": round(float(R["L"][iw]) / 1000.0, 3)},
        "min_distance_bay_cover_only_mm": round(float(R["dist_bay"].min()), 3),
        "lines_below_required": int((d < MIN_ALLOWED_MM).sum()), "lines_scored": int(len(d)),
        "lines_touching_below_0p5mm": int((d < 0.5).sum()),
    }
    per_hole = {}
    for hid in ids:
        s = R["hole"] == hid
        j = int(np.where(s)[0][d[s].argmin()])
        per_hole[hid] = {"min_distance_mm": round(float(d[s].min()), 3), "lines_scored": int(s.sum()), "lines_below_required": int((d[s] < MIN_ALLOWED_MM).sum()),
                         "at_claw_xyz_m": [float(R["px"][j]), float(R["py"][j]), float(R["pz"][j])], "yaw_deg": float(R["yaw"][j]),
                         "elevation_deg": round(float(R["elev"][j]), 2), "angle_to_axis_deg": round(float(R["gamma"][j]), 2), "nearest_part": str(R["part"][j])}
    out["per_hole"] = per_hole
    # distance versus elevation and versus angle to the hole axis (which lines fail, which pass)
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
    out["min_distance_by_elevation_deg"] = {}
    for lo, hi in zip(bins[:-1], bins[1:]):
        s = (R["elev"] >= lo) & (R["elev"] < hi)
        if s.any():
            out["min_distance_by_elevation_deg"][f"{lo}-{hi}"] = {"lines": int(s.sum()), "min_mm": round(float(d[s].min()), 2), "below_required": int((d[s] < MIN_ALLOWED_MM).sum())}
    gb = [0, 15, 30, 45, 60, 75, 90, 180]
    out["min_distance_by_angle_to_axis_deg"] = {}
    for lo, hi in zip(gb[:-1], gb[1:]):
        s = (R["gamma"] >= lo) & (R["gamma"] < hi)
        if s.any():
            out["min_distance_by_angle_to_axis_deg"][f"{lo}-{hi}"] = {"lines": int(s.sum()), "min_mm": round(float(d[s].min()), 2), "below_required": int((d[s] < MIN_ALLOWED_MM).sum())}
    ib = int(R["dist_bay"].argmin())
    out["min_at_bay_cover_only"] = {"hole": str(R["hole"][ib]), "claw_xyz_m": [round(float(R["px"][ib]), 3), round(float(R["py"][ib]), 3), round(float(R["pz"][ib]), 3)],
                                    "yaw_deg": float(R["yaw"][ib]), "elevation_deg": round(float(R["elev"][ib]), 1)}
    out["min_distance_mm_for_elevation_at_most_and_angle_to_axis_at_most"] = {
        f"elev<={E},angle<={Gm}": (round(float(d[(R["elev"] <= E) & (R["gamma"] <= Gm)].min()), 2) if ((R["elev"] <= E) & (R["gamma"] <= Gm)).any() else None)
        for E in (30, 45, 60, 70, 90) for Gm in (10, 15, 20, 30, 45)}
    low = d < MIN_ALLOWED_MM
    out["lines_below_required_by_part"] = {p: int((low & (R["part"] == p)).sum()) for p in sorted(set(R["part"].tolist()))}
    out["lines_below_required_elevation_range_deg"] = [round(float(R["elev"][low].min()), 1), round(float(R["elev"][low].max()), 1)] if low.any() else None
    out["lines_below_required_claw_height_range_m"] = [round(float(R["pz"][low].min()), 2), round(float(R["pz"][low].max()), 2)] if low.any() else None
    # the largest elevation / angle for which every scored line passes
    ok_e = R["elev"][low].min() if low.any() else None
    out["every_line_with_elevation_below_deg_passes"] = round(float(ok_e), 1) if ok_e is not None else None
    # the 20 closest lines, for the record
    order = np.argsort(d)[:20]
    out["closest_lines"] = [{"hole": str(R["hole"][i]), "dist_mm": round(float(d[i]), 3), "claw_xyz_m": [round(float(R["px"][i]), 3), round(float(R["py"][i]), 3), round(float(R["pz"][i]), 3)],
                             "yaw_deg": float(R["yaw"][i]), "elevation_deg": round(float(R["elev"][i]), 1), "angle_to_axis_deg": round(float(R["gamma"][i]), 1),
                             "part": str(R["part"][i]), "nearest_box_mm": [round(float(R["qx"][i]), 1), round(float(R["qy"][i]), 1), round(float(R["qz"][i]), 1)]} for i in order]
    return out


def main():
    res = analyze()
    with open(OUT, "w") as fh:
        json.dump(res, fh, indent=1)
    print(f"minimum distance line -> housing+bay+cover (own wall face excluded): {res['min_distance_mm']} mm  (required >= {MIN_ALLOWED_MM})")
    print("  at", res["min_at"])
    print("  bay + cover only (the original analysis metric):", res["min_distance_bay_cover_only_mm"], "mm at", res["min_at_bay_cover_only"])
    print("  min by (elevation <=, angle to axis <=):", json.dumps(res["min_distance_mm_for_elevation_at_most_and_angle_to_axis_at_most"]))
    print("  lines below required:", res["lines_below_required"], "of", res["lines_scored"], "scored;", res["totals"])
    print("  per hole:", json.dumps(res["per_hole"]))
    print("  by elevation:", json.dumps(res["min_distance_by_elevation_deg"]))
    print("  by angle to axis:", json.dumps(res["min_distance_by_angle_to_axis_deg"]))
    print("  failing lines by part:", res["lines_below_required_by_part"], "elevation range", res["lines_below_required_elevation_range_deg"])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
