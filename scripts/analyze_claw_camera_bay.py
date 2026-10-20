#!/usr/bin/python3
"""
Field-of-view and cable-line clearance analysis for the claw camera bay.

Run:  /usr/bin/python3 scripts/analyze_claw_camera_bay.py
Writes: verification/claw_camera_bay_analysis.json
        renders/claw_camera_bay/camera_view_floor_footprint.png

1. FOV: the claw stands on the floor (jaw tips on the floor, tube vertical).
   Rays from the lens through a 4:3 sensor pyramid (70 deg diagonal) and through
   the circular 35 deg half-angle cone are cast against every v6 solid (box +
   bay included).  Reports which solid first blocks each ray, the unblocked
   fraction, the floor footprint of the unblocked rays and the lens height.
2. Cable lines: from each corner cable-hole mouth, rays at azimuth 0..90 deg
   inside that corner's quadrant and elevation 10..90 deg are tested against the
   bay (body + cover); reports the minimum clearance.
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
from cad import params as P                           # noqa: E402
from cad.v6_loader import load_v6, find, BOX_NAME     # noqa: E402
from cad.mesh_tools import tessellate, ray_mesh_first_hit  # noqa: E402

OUT_JSON = os.path.join(REPO, "verification", "claw_camera_bay_analysis.json")
OUT_PNG = os.path.join(REPO, "renders", "claw_camera_bay", "camera_view_floor_footprint.png")


def bay_to_world_shape(wp):
    return wp.val().moved(cq.Location(cq.Vector(*B.BAY_ORIGIN_WORLD)))


def corner_hole_mouths(box_world):
    """Mouth centre (world) and outward unit direction for the 4 corner cable holes."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    holes = {}
    for f in box_world.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() != GeomAbs_Cylinder:
            continue
        c = a.Cylinder()
        if abs(c.Radius() - P.CAMBAY_CORNER_HOLE_D / 2) > 1e-3:
            continue
        ax = c.Axis()
        d = np.array([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
        p0 = np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()])
        cx, cz = B.BAY_ORIGIN_WORLD[0], B.BAY_ORIGIN_WORLD[2]
        key = (np.sign(p0[0] - cx), np.sign(p0[2] - cz))
        verts = np.array([[v.X, v.Y, v.Z] for v in f.Vertices()])
        out_dir = np.array([key[0], 0.0, key[1]]) / math.sqrt(2)
        d = d if d @ out_dir > 0 else -d
        t = (verts - p0) @ d
        rec = holes.setdefault(key, {"p0": p0, "d": d, "tmax": -1e9})
        rec["tmax"] = max(rec["tmax"], t.max())
    out = {}
    for key, r in holes.items():
        out[key] = (r["p0"] + r["d"] * r["tmax"], r["d"])
    return out


def main():
    parts = load_v6()
    box = find(parts, BOX_NAME)
    ox, oy, oz = B.BAY_ORIGIN_WORLD
    box_bay = cq.Workplane().add(box).translate((-ox, -oy, -oz))
    combined_w = bay_to_world_shape(B.combine(box_bay))
    cover_w = bay_to_world_shape(B.make_cover())
    bay_only_w = bay_to_world_shape(B.make_bay_body())
    res = {}

    # ---------------- 1. cable-line clearance -------------------------------------
    mouths = corner_hole_mouths(box)
    Vb, Fb = tessellate(bay_only_w, 0.15, 0.3)
    Vc, Fc = tessellate(cover_w, 0.15, 0.3)
    Vbay = np.concatenate([Vb, Vc])
    Fbay = np.concatenate([Fb, Fc + len(Vb)])
    # dense surface samples of the bay for clearance distance
    tri = Vbay[Fbay]
    rng = np.random.default_rng(1)
    pts = [Vbay]
    for _ in range(4):
        w = rng.dirichlet([1, 1, 1], size=len(tri))
        pts.append(np.einsum("ij,ijk->ik", w, tri))
    samples = np.concatenate(pts)
    min_clear, hits, nrays = 1e9, 0, 0
    worst = None
    azs = np.radians(np.arange(0, 90.1, 5.0))
    els = np.radians(np.arange(10, 90.1, 5.0))
    line_res = {}
    for key, (m, d_out) in mouths.items():
        sx, sz = key
        dirs = []
        for az in azs:
            for el in els:
                dirs.append([sx * math.cos(az) * math.cos(el), math.sin(el),
                             sz * math.sin(az) * math.cos(el)])
        dirs = np.array(dirs)
        t_hit = ray_mesh_first_hit(m, dirs, Vbay, Fbay)
        nh = int(np.isfinite(t_hit).sum())
        # clearance: distance from each ray (t>=0) to the bay surface samples
        mc = 1e9
        for dvec in dirs:
            rel = samples - m
            tt = np.clip(rel @ dvec, 0, None)
            dist = np.linalg.norm(rel - tt[:, None] * dvec[None, :], axis=1)
            k = dist.min()
            if k < mc:
                mc = k
                wd = (dvec, samples[dist.argmin()])
        line_res[f"corner_{int(sx):+d}x_{int(sz):+d}z"] = {
            "mouth_world": [round(float(v), 2) for v in m],
            "mouth_bay_frame": [round(float(m[0] - ox), 2), round(float(m[1] - oy), 2), round(float(m[2] - oz), 2)],
            "rays": len(dirs), "rays_hitting_bay": nh, "min_clearance_mm": round(float(mc), 2)}
        if mc < min_clear:
            min_clear = mc
        hits += nh
        nrays += len(dirs)
    res["cable_lines"] = {"per_corner": line_res, "rays_total": nrays, "rays_hitting_bay": hits,
                          "min_clearance_mm": round(float(min_clear), 2)}
    print("cable lines:", json.dumps(res["cable_lines"], indent=1))

    # ---------------- 2. field of view ---------------------------------------------------
    floor_y = min(s.BoundingBox().ymin for n, s in parts)
    names, meshes = [], []
    for n, s in parts:
        if n == BOX_NAME:
            continue
        names.append(n)
        meshes.append(tessellate(s, 1.2, 0.5))
    names.append("box+camera_bay")
    meshes.append(tessellate(combined_w, 0.5, 0.4))
    names.append("bay_cover")
    meshes.append((Vc, Fc))

    lens = np.array([ox + 0.0, oy + B.LENS_FRONT_Y, oz + B.S * P.CAMBAY_CAM_R])
    res["lens_center_world"] = [round(float(v), 2) for v in lens]
    res["floor_y_world"] = round(float(floor_y), 2)
    res["lens_height_above_floor_mm"] = round(float(lens[1] - floor_y), 1)

    half_diag = math.radians(P.CAMBAY_FOV_DIAG_DEG / 2)
    ar = P.CAMBAY_SENSOR_ASPECT
    diag = math.hypot(*ar)
    tx = math.tan(half_diag) * ar[0] / diag      # half-tan along sensor X (bay X)
    ty = math.tan(half_diag) * ar[1] / diag      # half-tan along sensor Y (radial)

    def cast(dirs):
        best = np.full(len(dirs), np.inf)
        who = np.full(len(dirs), -1)
        for i, (V, F) in enumerate(meshes):
            t = ray_mesh_first_hit(lens, dirs, V, F)
            m = t < best
            best[m] = t[m]
            who[m] = i
        # floor
        with np.errstate(divide="ignore"):
            tf = (floor_y - lens[1]) / dirs[:, 1]
        return best, who, tf

    def summarize(label, U, Vv, inside):
        # x along bay X, y = -1 (down, -Y), z = sensor-v along the outward radial
        dirs = np.stack([U, -np.ones_like(U), Vv * B.S], axis=1)
        dirs = dirs / np.linalg.norm(dirs, axis=1, keepdims=True)
        dirs = dirs[inside]
        best, who, tf = cast(dirs)
        blocked = best < tf                       # something before the floor
        counts = {}
        for i in np.unique(who[blocked]):
            counts[names[i]] = int((who[blocked] == i).sum())
        n = len(dirs)
        out = {"rays": n, "blocked": int(blocked.sum()), "blocked_fraction": round(float(blocked.mean()), 4),
               "unblocked_fraction": round(float(1 - blocked.mean()), 4),
               "blocked_by": {k: round(v / n, 4) for k, v in sorted(counts.items(), key=lambda kv: -kv[1])}}
        pts = lens[None, :] + dirs * tf[:, None]
        ok = ~blocked
        out["floor_footprint_unblocked_x_range_from_tube_axis"] = [round(float(pts[ok, 0].min() - ox), 1), round(float(pts[ok, 0].max() - ox), 1)] if ok.any() else None
        out["floor_footprint_unblocked_z_range_from_tube_axis"] = [round(float(pts[ok, 2].min() - oz), 1), round(float(pts[ok, 2].max() - oz), 1)] if ok.any() else None
        # nearest floor points seen on the camera side / tube side of the claw
        if ok.any():
            out["nearest_floor_point_seen_from_camera_mm"] = round(float(np.linalg.norm(pts[ok][:, [0, 2]] - np.array([lens[0], lens[2]]), axis=1).min()), 1)
        print(label, json.dumps(out, indent=1))
        return out, dirs, blocked, who, best, tf, pts

    nx, ny = 61, 46
    gu, gv = np.meshgrid(np.linspace(-tx, tx, nx), np.linspace(-ty, ty, ny))
    rect = summarize("sensor 4:3 pyramid", gu.ravel(), gv.ravel(), np.ones(gu.size, bool))
    res["fov_sensor_rect_4x3_70diag"] = rect[0]
    # circular cone (35 deg half angle)
    R = math.tan(half_diag)
    gu2, gv2 = np.meshgrid(np.linspace(-R, R, 61), np.linspace(-R, R, 61))
    inside = (gu2 ** 2 + gv2 ** 2 <= R ** 2).ravel()
    cone = summarize("circular 35deg cone", gu2.ravel(), gv2.ravel(), inside)
    res["fov_circular_cone_35deg"] = cone[0]
    # rectangle again but long side along the radial direction (sensor rotated 90 deg)
    gu3, gv3 = np.meshgrid(np.linspace(-ty, ty, nx), np.linspace(-tx, tx, ny))
    rot = summarize("sensor rotated 90 deg", gu3.ravel(), gv3.ravel(), np.ones(gu3.size, bool))
    res["fov_sensor_rect_rotated_90"] = rot[0]

    # FOV clipping by the bay's own hood tunnel (first hit within 15 mm of the lens)
    dirs, blocked, who, best, tf, pts = rect[1:7]
    near = (best < 15.0) & (who == names.index("box+camera_bay"))
    res["hood_tunnel_clipped_rays_sensor_rect"] = int(near.sum())

    # ---------------- visibility of specific floor targets -----------------------------------
    def visible_fraction(xs, zs):
        gx, gz = np.meshgrid(xs, zs)
        tgt = np.stack([ox + gx.ravel(), np.full(gx.size, floor_y), oz + gz.ravel()], axis=1)
        d = tgt - lens
        tf_ = np.linalg.norm(d, axis=1)
        d = d / tf_[:, None]
        best = np.full(len(d), np.inf)
        for V, F in meshes:
            best = np.minimum(best, ray_mesh_first_hit(lens, d, V, F))
        return float((best >= tf_ - 0.5).mean())

    res["visibility"] = {
        "floor_between_jaw_tips_x+-40_z-13..+7": round(visible_fraction(np.linspace(-40, 40, 17), np.linspace(-13, 7, 5)), 3),
        "floor_strip_camera_side_z-60..-34_x+-60": round(visible_fraction(np.linspace(-60, 60, 25), np.linspace(-60, -34, 14)), 3),
        "floor_strip_camera_side_z-34..-20_x+-60": round(visible_fraction(np.linspace(-60, 60, 25), np.linspace(-34, -20, 8)), 3),
        "floor_strip_far_side_z+60..+110_x+-60": round(visible_fraction(np.linspace(-60, 60, 25), np.linspace(60, 110, 11)), 3),
    }
    # camera-side visible floor edge along the radial line toward the claw (|x| < 15)
    edge = None
    for zr in np.arange(-100.0, 20.0, 1.0):
        if visible_fraction(np.linspace(-15, 15, 7), np.array([zr])) < 0.99:
            edge = float(zr)
            break
    res["visibility"]["nearest_fully_visible_floor_toward_claw_from_camera_side_z_rel"] = None if edge is None else edge - 1.0
    print("visibility", json.dumps(res["visibility"]))

    # ---------------- interference with the other v6 parts ---------------------------------
    inter = {}
    for n, sld in parts:
        if n == BOX_NAME:
            continue
        a, b = sld.BoundingBox(), bay_only_w.BoundingBox()
        if a.xmax < b.xmin or b.xmax < a.xmin or a.ymax < b.ymin or b.ymax < a.ymin or a.zmax < b.zmin or b.zmax < a.zmin:
            continue
        inter[n] = round(float(sld.intersect(bay_only_w).Volume()), 3)
    res["bay_interference_mm3_with_other_v6_parts"] = inter

    # ---------------- cantilever stiffness estimate (hand calc, see assumptions) --------------
    E = 2100.0          # MPa PETG (cad/materials.py), XY loading, no knockdown
    Ix = 2 * (B.WALL * B.H_CAV ** 3 / 12) + (2 * B.OUT_HALF_X) * B.FLOOR_T * (B.H_CAV / 2 - B.FLOOR_T / 2) ** 2
    Lc = B.OUT_R1 - (B.box_wall_r(10.0))
    m_tip = 0.030       # kg: bay+cover tip share + XIAO + IMU, generous
    k = 3 * E * Ix / Lc ** 3          # N/mm, bay treated as a cantilever on a rigid wall (U-section, ribs ignored)
    f1 = math.sqrt(k * 1000 / m_tip) / (2 * math.pi)
    res["stiffness_estimate"] = {
        "assumptions": "rigid box wall, U-section (floor + 2 side walls, cover ignored, ribs ignored), E=2.1 GPa, tip mass 30 g",
        "I_mm4": round(Ix), "cantilever_length_mm": round(Lc, 1), "k_N_per_mm": round(k, 1),
        "deflection_under_30g_x_2g_dynamic_mm": round(0.030 * 9.81 * 3 / k, 5),
        "first_mode_hz_upper_bound": round(f1)}

    # ---------------- footprint sketch ----------------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    dirs, blocked, who, best, tf, pts = rect[1:]
    cx, cz = ox, oz
    fig, ax = plt.subplots(figsize=(8, 7.5))
    ok = ~blocked
    ax.scatter(pts[ok, 0] - cx, pts[ok, 2] - cz, s=6, c="#2a9d8f", label="floor seen (unblocked)")
    # blocked rays: show where they strike the occluder projected on the floor along the ray
    bl = blocked
    pb = lens[None, :] + dirs[bl] * tf[bl][:, None]
    ax.scatter(pb[:, 0] - cx, pb[:, 2] - cz, s=6, c="#e76f51", label="floor point hidden behind claw")
    # claw footprints (top view, floor-projected outlines)
    for n, s in parts:
        if n.startswith("Gripper_gear_housing") or n.startswith("Gripper_Electric") or n == "Griper Cylinder":
            bb = s.BoundingBox()
            ax.add_patch(Rectangle((bb.xmin - cx, bb.zmin - cz), bb.xlen, bb.zlen, fill=False,
                                   ec="#264653", lw=1.2, ls="-" if "gear" in n else "--"))
    ax.add_patch(Circle((0, 0), 14.27, fill=False, ec="k"))
    ax.plot([0], [B.S * P.CAMBAY_CAM_R], "k*", ms=14, label="camera (lens)")
    ax.annotate("camera", (0, B.S * P.CAMBAY_CAM_R), textcoords="offset points", xytext=(8, 6))
    ax.set_aspect("equal")
    ax.set_xlabel("world X - tube axis (mm)")
    ax.set_ylabel("world Z - tube axis (mm)")
    ax.set_title(f"Camera floor footprint (claw standing, lens {lens[1] - floor_y:.0f} mm above floor)\n"
                 f"4:3 / 70 deg diag: {rect[0]['unblocked_fraction'] * 100:.0f}% of rays reach the floor, "
                 f"{rect[0]['blocked_fraction'] * 100:.0f}% blocked by the claw")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.25)
    os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
    fig.savefig(OUT_PNG, dpi=130, bbox_inches="tight")
    plt.close(fig)

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as fh:
        json.dump(res, fh, indent=1)
    print("wrote", OUT_JSON)
    print("wrote", OUT_PNG)


if __name__ == "__main__":
    main()
