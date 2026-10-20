#!/usr/bin/python3
"""
Realistic cable-line clearance for the claw camera bay.

Run:  /usr/bin/python3 scripts/analyze_cable_lines_claw_camera_bay.py
Reads config/robot.sim.json (stations anchor_room_m, room, workspace_margin_m,
ceiling_margin_m) -- read-only.  Writes verification/claw_camera_bay_cable_lines.json

Model
  * Corner hole k leaves the box at the mouth (sx*54.09, 14.05, sz*54.09) in the bay
    frame (bay X, up Y, bay Z).  Each line runs from that mouth straight to its anchor.
  * Room frame: x east, y north, z up.  The claw hangs vertical; claw yaw psi rotates the
    bay frame about the vertical: bay +X -> room (cos psi, sin psi); bay +Z -> room
    (sin psi, -cos psi)  (v6 axes are right-handed with Y up, so Z is clockwise from X
    seen from above).  At psi = 0 the bay (bay -Z side) faces room +y.
  * Corner -> station mapping is fixed at psi = 0 by the nearest corner diagonal:
        corner(+X,+Z) -> B (3.30, 0.05)   corner(+X,-Z) -> C (3.30, 2.69)
        corner(-X,-Z) -> D (0.05, 2.69)   corner(-X,+Z) -> A (0.05, 0.05)
    and kept fixed for every yaw (cables are physically attached to fixed corners).
  * Claw reference (mouth-plane centre on the tube axis) is sampled over the workspace:
    x,y in [margin, size - margin] (margin 0.2 m), z in [lowest-point height, room height -
    ceiling margin 0.4 m]; lowest point = 523.8 mm below the mouth plane (jaw tips, v6).
  * Lines that pass through the box body (cable through the claw) are physically impossible
    for that (position, yaw) and are excluded ("feasible" lines only are scored).
  * Clearance = min distance from the line (mouth -> anchor) to the exposed bay surface
    (bay body outside the box + cover) sampled at <= 0.5 mm spacing.
"""

from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import cadquery as cq

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad.parts import claw_camera_bay as B            # noqa: E402
from cad.v6_loader import load_v6, find, BOX_NAME     # noqa: E402
from cad.mesh_tools import tessellate, ray_mesh_first_hit  # noqa: E402

CONFIG = os.path.join(REPO, "config", "robot.sim.json")
OUT = os.path.join(REPO, "verification", "claw_camera_bay_cable_lines.json")
MOUTH = 54.09
MOUTH_Y = 14.05
JAW_BELOW_MOUTH_M = (1105.24 - 581.43) / 1000.0
MAPPING = {(1, 1): "B", (1, -1): "C", (-1, -1): "D", (-1, 1): "A"}     # (sx, sz) -> station


def bay_surface():
    parts = load_v6()
    box = find(parts, BOX_NAME)
    ox, oy, oz = B.BAY_ORIGIN_WORLD
    box_bay = cq.Workplane().add(box).translate((-ox, -oy, -oz))
    Vbox, Fbox = tessellate(box_bay, 0.3, 0.3)
    comb = B.combine(box_bay)
    added = comb.cut(box_bay)
    cover = B.make_cover()
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
    return V, F, np.concatenate(pts), Vbox, Fbox


def main():
    cfg = json.load(open(CONFIG))
    room = cfg["room"]
    W, D, H = room["width_m"], room["depth_m"], room["height_m"]
    mg, cm = cfg["motion"]["workspace_margin_m"], cfg["motion"]["ceiling_margin_m"]
    anchors = {s["id"]: np.array(s["anchor_room_m"]) for s in cfg["stations"]}
    V, F, samples, Vbox, Fbox = bay_surface()
    print("bay surface samples:", len(samples))

    xs = np.linspace(mg, W - mg, 8)
    ys = np.linspace(mg, D - mg, 7)
    zs = np.linspace(JAW_BELOW_MOUTH_M, H - cm, 6)
    yaws = np.radians(np.arange(0, 360, 15.0))
    corners = [(sx, sz) for sx in (1, -1) for sz in (1, -1)]
    mouth_bay = {c: np.array([c[0] * MOUTH, MOUTH_Y, c[1] * MOUTH]) for c in corners}

    results = {}                                   # yaw_deg -> dict(min clearance, hits, worst config)
    hit_el, hit_z, hit_corner = [], [], {}
    for psi in yaws:
        ex = np.array([math.cos(psi), math.sin(psi)])
        ez = np.array([math.sin(psi), -math.cos(psi)])
        dirs, meta = [], []
        for (sx, sz) in corners:
            anc = anchors[MAPPING[(sx, sz)]]
            for px in xs:
                for py in ys:
                    for pz in zs:
                        mouth_room_h = np.array([px, py]) + (sx * MOUTH / 1000.0) * ex + (sz * MOUTH / 1000.0) * ez
                        d = np.array([anc[0] - mouth_room_h[0], anc[1] - mouth_room_h[1], anc[2] - pz])
                        L = np.linalg.norm(d)                                # metres
                        db = np.array([d[:2] @ ex, d[2], d[:2] @ ez])     # bay frame (x, up, z)
                        dirs.append(db / L)
                        meta.append((sx, sz, px, py, pz, L * 1000.0, math.degrees(math.asin(d[2] / L))))   # L in mm
        dirs = np.array(dirs)
        meta = np.array(meta)
        # ray hits (first hit inside the line length)
        hits = np.zeros(len(dirs), bool)
        mind = np.full(len(dirs), 1e9)
        feasible = np.ones(len(dirs), bool)        # line does not pass through the box body
        for (sx, sz) in corners:
            sel = np.where((meta[:, 0] == sx) & (meta[:, 1] == sz))[0]
            o = mouth_bay[(sx, sz)]
            tb = ray_mesh_first_hit(o + dirs[sel][0] * 0.0 + np.array([0.0, 0.0, 0.0]), dirs[sel], Vbox, Fbox)
            # offset the start 0.6 mm along each line so the mouth surface itself is not counted
            tb = np.array([ray_mesh_first_hit(o + d * 0.6, d[None, :], Vbox, Fbox)[0] for d in dirs[sel]])
            feasible[sel] = ~(tb < meta[sel, 5])
            t = ray_mesh_first_hit(o, dirs[sel], V, F)
            hits[sel] = t < meta[sel, 5]
            # clearance: distance from each line (0..L) to the sample cloud
            rel = samples - o
            for k0 in range(0, len(sel), 256):
                ss = sel[k0:k0 + 256]
                dd = dirs[ss]
                tt = np.clip(rel @ dd.T, 0, None)                       # (n_pts, n_lines)
                tt = np.minimum(tt, meta[ss, 5][None, :])
                # |rel - tt d|^2 = |rel|^2 - 2 tt (rel.d) + tt^2
                r2 = (rel ** 2).sum(1)[:, None]
                dist2 = r2 - 2 * tt * (rel @ dd.T) + tt ** 2
                mind[ss] = np.sqrt(np.maximum(dist2.min(axis=0), 0))
        mind_f = np.where(feasible, mind, 1e9)
        hits_f = hits & feasible
        for ii in np.where(hits_f)[0]:
            hit_el.append(float(meta[ii, 6]))
            hit_z.append(float(meta[ii, 4]))
            key = MAPPING[(int(meta[ii, 0]), int(meta[ii, 1]))]
            hit_corner[key] = hit_corner.get(key, 0) + 1
        i = int(mind_f.argmin())
        results[round(math.degrees(psi))] = {
            "min_clearance_mm": round(float(mind_f.min()), 2),
            "lines_hitting_bay": int(hits_f.sum()),
            "lines_hitting_bay_incl_infeasible": int(hits.sum()),
            "lines_feasible": int(feasible.sum()),
            "lines": len(dirs),
            "worst": {"corner(sx,sz)": [int(meta[i, 0]), int(meta[i, 1])],
                      "station": MAPPING[(int(meta[i, 0]), int(meta[i, 1]))],
                      "claw_xyz_m": [round(float(v), 3) for v in meta[i, 2:5]],
                      "line_length_m": round(float(meta[i, 5]) / 1000.0, 2),
                      "elevation_deg": round(float(meta[i, 6]), 1),
                      "bay_frame_dir": [round(float(v), 3) for v in dirs[i]]},
        }
        print(f"yaw {math.degrees(psi):5.0f}: min clearance {mind_f.min():7.2f} mm, hits {int(hits_f.sum())}/{int(feasible.sum())} feasible "
              f"({int(hits.sum())} incl. lines through the box)")

    allc = {k: v["min_clearance_mm"] for k, v in results.items()}
    worst_yaw = min(allc, key=allc.get)
    near = [k for k in allc if k <= 15 or k >= 345]
    out = {
        "model": __doc__,
        "workspace_m": {"x": [mg, W - mg], "y": [mg, D - mg], "z": [round(JAW_BELOW_MOUTH_M, 3), H - cm]},
        "sampling": {"x": len(xs), "y": len(ys), "z": len(zs), "yaw_step_deg": 15},
        "nominal_yaw0_min_clearance_mm": allc[0],
        "yaw_within_pm15deg_min_clearance_mm": min(allc[k] for k in near),
        "all_yaw_min_clearance_mm": allc[worst_yaw],
        "worst_yaw_deg": worst_yaw,
        "total_lines_hitting_bay_all_yaws": int(sum(v["lines_hitting_bay"] for v in results.values())),
        "hits_within_pm30deg_yaw": int(sum(results[k]["lines_hitting_bay"] for k in results if k <= 30 or k >= 330)),
        "hits_within_pm15deg_yaw": int(sum(results[k]["lines_hitting_bay"] for k in results if k <= 15 or k >= 345)),
        "hit_lines_max_elevation_deg": round(max(hit_el), 1) if hit_el else None,
        "hit_lines_min_claw_height_m": round(min(hit_z), 2) if hit_z else None,
        "hit_lines_by_station": hit_corner,
        "worst_fraction_of_feasible_lines_hitting": round(max(v["lines_hitting_bay"] / max(v["lines_feasible"], 1) for v in results.values()), 4),
        "per_yaw": results,
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print("yaw 0 clearance", out["nominal_yaw0_min_clearance_mm"],
          "| +-15 deg", out["yaw_within_pm15deg_min_clearance_mm"],
          "| all yaws", out["all_yaw_min_clearance_mm"], "at yaw", worst_yaw,
          "| hits (all yaws)", out["total_lines_hitting_bay_all_yaws"])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
