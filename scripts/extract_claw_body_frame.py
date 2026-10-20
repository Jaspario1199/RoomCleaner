#!/usr/bin/python3
"""
Extract the claw BODY FRAME used by the cable-robot control stack from the CAD.

Run (needs CadQuery/OCP, see requirements-cad.txt):
    python scripts/extract_claw_body_frame.py [--check]
Writes verification/claw_body_frame.json (``--check`` compares against the committed
file and the config instead of rewriting, exit code 1 on a mismatch).

What it computes
  * The four cable holes through the corner fillets of the electrical box, from
    exports/step/gripper_electric_housing_with_camera_bay.step (box + camera bay,
    v6 world coordinates, mm).  A hole is a cylindrical face of radius 0.75 mm whose
    axis rises ~21 deg outward on a corner diagonal.
  * Each hole's INNER MOUTH CENTRE = intersection of the hole axis with the INNER wall
    surface (the pocket's corner-fillet cylinder that the hole's inner boundary edges
    lie on).  This is the cable attachment point b_i (user direction 10/20: the line
    ties off on the inner wall at the fillet where the hole enters the box interior).
    The OUTER mouth (axis x outer fillet surface) is recorded too: the line leaves the
    claw there, so the straight-line cable model is exact only up to the short
    in-hole segment (see docs/CONTROL_SYSTEM_V1.md 3.1).
  * Body frame: origin on the tube axis at the mean height of the four inner mouths;
    +z = v6 +Y (up the tube), +x = v6 +X, +y = -v6 Z (so the camera bay, on v6 -Z,
    lies at body +y).  Right handed: x cross y = z.  At claw yaw 0 the body axes
    coincide with the room axes (+x east toward station B, +y toward D).
  * Corner -> station: (+X,+Z)->B, (+X,-Z)->C, (-X,-Z)->D, (-X,+Z)->A, i.e. in the body
    frame (-,-)->A, (+,-)->B, (+,+)->C, (-,+)->D = the same corner order as the
    config station anchors (A (0,0), B (W,0), C (W,D), D (0,D)) at yaw 0.
  * Camera lens centre / optical axis from the camera-bay build (cad/params.py CAMBAY_*,
    cad/parts/claw_camera_bay.py) expressed in the body frame.
  * Lowest point = lowest vertex of the v6 jaws (VERIFY: v7 jaws are being redesigned).
  * Centre of mass of the CAD assembly (printed parts PETG 1.27 g/cc, tube 2.70 g/cc,
    servo 55 g; electronics and sliced-infill NOT modelled) -> VERIFY, estimate only.

Provenance: everything here is derived from CAD geometry; nothing is measured on
hardware.  Entries marked VERIFY must be checked before they are trusted.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

HOUSING_STEP = os.path.join(REPO, "exports", "step", "gripper_electric_housing_with_camera_bay.step")
OUT = os.path.join(REPO, "verification", "claw_body_frame.json")
CONFIGS = [os.path.join(REPO, "config", "robot.sim.json"), os.path.join(REPO, "config", "robot.example.json")]
HOLE_RADIUS_MM = 0.75
STATION_ORDER = ["A", "B", "C", "D"]
# (sx, sz) in v6 world X/Z signs -> station (same table as scripts/analyze_cable_lines_claw_camera_bay.py)
CORNER_TO_STATION = {(1, 1): "B", (1, -1): "C", (-1, -1): "D", (-1, 1): "A"}
PRINTED_G_CC, ALUMINIUM_G_CC, SERVO_G = 1.27e-3, 2.70e-3, 55.0     # g/mm^3, g/mm^3, g


def v6_to_body(P_v6, origin_v6):
    """v6 world (mm) -> body frame (m): x = X, y = -Z, z = Y, origin on the tube axis."""
    d = np.asarray(P_v6, float) - np.asarray(origin_v6, float)
    return np.array([d[0], -d[2], d[1]]) / 1000.0


def dir_v6_to_body(d):
    d = np.asarray(d, float)
    return np.array([d[0], -d[2], d[1]])


def find_holes(shape):
    """Cable holes: dict per corner with axis point/direction (v6 mm) and mouth centres."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.Geom import Geom_Line
    from OCP.GeomAbs import GeomAbs_Cylinder
    from OCP.GeomAPI import GeomAPI_IntCS
    from OCP.gp import gp_Dir, gp_Pnt
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp
    from OCP.TopoDS import TopoDS
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
    import cadquery as cq

    ancestors = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(shape.wrapped, TopAbs_EDGE, TopAbs_FACE, ancestors)
    tube_xz = np.array([951.8475, 1103.9899])               # tube axis (checked against v6_loader below)
    holes = []
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() != GeomAbs_Cylinder or abs(a.Cylinder().Radius() - HOLE_RADIUS_MM) > 1e-3:
            continue
        ax = a.Cylinder().Axis()
        P0 = np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()])
        d = np.array([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
        if (np.array([P0[0], P0[2]]) - tube_xz) @ np.array([d[0], d[2]]) < 0:
            d = -d                                          # point outward (away from the tube axis)
        line = Geom_Line(gp_Pnt(*P0), gp_Dir(*d))
        # boundary edges grouped by the neighbouring face; the neighbour nearest the tube axis is the INNER wall
        groups = {}
        for e in f.Edges():
            for nb in ancestors.FindFromKey(e.wrapped):
                if nb.IsSame(f.wrapped):
                    continue
                groups.setdefault(cq.Shape.cast(nb).hashCode(), (nb, []))[1].append(e)
        if len(groups) != 2:
            raise RuntimeError(f"hole face has {len(groups)} neighbouring faces, expected 2 (inner + outer wall)")
        mouths = []
        for nb, edges in groups.values():
            c = np.mean([e.Center().toTuple() for e in edges], axis=0)
            surf = BRep_Tool.Surface_s(TopoDS.Face_s(nb))
            inter = GeomAPI_IntCS(line, surf)
            cands = [(inter.Point(i).X(), inter.Point(i).Y(), inter.Point(i).Z()) for i in range(1, inter.NbPoints() + 1)]
            if not cands:
                raise RuntimeError("hole axis does not meet its wall surface")
            p = np.array(min(cands, key=lambda q: np.linalg.norm(np.array(q) - c)))
            mouths.append({"point": p, "edge_centroid": c, "surface": cq.Face(TopoDS.Face_s(nb)).geomType(),
                           "radial_mm": float(np.linalg.norm(p[[0, 2]] - tube_xz))})
        mouths.sort(key=lambda m: m["radial_mm"])
        sx, sz = (1 if P0[0] > tube_xz[0] else -1), (1 if P0[2] > tube_xz[1] else -1)
        holes.append({"sx": sx, "sz": sz, "axis_point": P0, "dir": d, "inner": mouths[0], "outer": mouths[1]})
    if len(holes) != 4 or len({(h["sx"], h["sz"]) for h in holes}) != 4:
        raise RuntimeError(f"expected 4 corner holes, found {len(holes)}")
    return holes


def jaw_lowest_point(parts, origin_v6):
    """Midpoint (x, z) of the two jaw tips (each jaw's lowest vertex), lowest y of the pair (v6 mm)."""
    tips = []
    for name, s in parts:
        if name.startswith("Claw_arm_extension") and not name.startswith("Claw_arm_extension3"):
            v = np.array([q.toTuple() for q in s.Vertices()])
            tips.append(v[v[:, 1] < v[:, 1].min() + 0.5].mean(axis=0))
    tips = np.array(tips)
    tip = tips.mean(axis=0)
    tip[1] = tips[:, 1].min()
    return tip


def mass_properties(parts, housing_shape):
    """CAD-solid centre of mass (v6 mm) and mass (g); VERIFY (no electronics, no infill)."""
    tot, mom = 0.0, np.zeros(3)
    rows = []
    for name, s in parts:
        if name == "Gripper_Electric_Housing_Base (2)":
            s = housing_shape                                    # box + camera bay
        if "MG996R body" in name:
            m = SERVO_G
        elif "shaft" in name and "MG996R" in name:
            continue
        elif "aluminum" in name:
            m = s.Volume() * ALUMINIUM_G_CC
        else:
            m = s.Volume() * PRINTED_G_CC
        c = np.array(s.Center().toTuple())
        tot += m
        mom += m * c
        rows.append((name, round(m, 1)))
    return mom / tot, tot, rows


def camera_pose(origin_v6):
    """Lens centre + optical axis in the body frame from the camera-bay build."""
    from cad import params as P
    try:
        from cad.parts import claw_camera_bay as B
        lens_bay = np.array(B.LENS_CENTER_BAY, float)           # bay frame (x, up, z), mm, origin tube axis @ box bottom
        axis_bay = np.array(B.OPTICAL_AXIS_BAY, float)
        src = "cad/parts/claw_camera_bay.py LENS_CENTER_BAY / OPTICAL_AXIS_BAY"
        origin_bay_v6 = np.array(B.BAY_ORIGIN_WORLD, float)
    except Exception as exc:                                    # pragma: no cover
        d = json.load(open(os.path.join(REPO, "verification", "claw_camera_bay_analysis.json")))
        origin_bay_v6 = np.array([951.8475, 1091.1905, 1103.9899])
        lens_bay = np.array(d["lens_center_world"]) - origin_bay_v6
        axis_bay = np.array([0.0, -1.0, 0.0])
        src = f"verification/claw_camera_bay_analysis.json ({exc})"
    lens_v6 = origin_bay_v6 + lens_bay                          # bay axes parallel to v6 world axes
    t = v6_to_body(lens_v6, origin_v6)
    ob = dir_v6_to_body(axis_bay)
    # OpenCV optical frame: z forward = optical axis (down), x = sensor long side = body +x, y = z cross x
    zc = ob / np.linalg.norm(ob)
    xc = np.array([1.0, 0.0, 0.0])
    yc = np.cross(zc, xc)
    R = np.stack([xc, yc, zc], axis=1)
    rx = math.atan2(R[2, 1], R[2, 2])                           # rotation about x only (pure flip) -> rpy (rx, 0, 0)
    assert np.allclose(R, _rot_x(rx), atol=1e-9), "camera orientation is not a pure x rotation"
    return {"translation_m": t.tolist(), "rpy_rad": [rx, 0.0, 0.0], "optical_axis_body": zc.tolist(),
            "source": src, "VERIFY": "sensor rotation about the optical axis (long side along body x) and lens "
                                     "height are assumed (CAMBAY_LENS_*, CAMBAY_SENSOR_ASPECT); measure on the print"}


def _rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def main(check=False):
    import cadquery as cq
    from cad.v6_loader import load_v6, tube_axis_world

    housing = cq.importers.importStep(HOUSING_STEP).val()
    holes = find_holes(housing)
    inner_y = float(np.mean([h["inner"]["point"][1] for h in holes]))
    parts = load_v6()
    tube = tube_axis_world(parts)
    tube_x, tube_z = float(tube[0]), float(tube[1])
    origin_v6 = np.array([tube_x, inner_y, tube_z])
    assert abs(tube_x - 951.8475) < 0.01 and abs(tube_z - 1103.9899) < 0.01, (tube_x, tube_z)

    by_station = {}
    detail = {}
    for h in holes:
        st = CORNER_TO_STATION[(h["sx"], h["sz"])]
        b_in = v6_to_body(h["inner"]["point"], origin_v6)
        b_out = v6_to_body(h["outer"]["point"], origin_v6)
        by_station[st] = b_in
        detail[st] = {
            "corner_v6_signs_XZ": [h["sx"], h["sz"]],
            "attachment_inner_mouth_body_m": b_in.tolist(),
            "outer_mouth_body_m": b_out.tolist(),
            "hole_axis_dir_body_outward": dir_v6_to_body(h["dir"]).tolist(),
            "hole_elevation_deg": math.degrees(math.asin(h["dir"][1])),
            "hole_length_mm": float(np.linalg.norm(h["outer"]["point"] - h["inner"]["point"])),
            "inner_mouth_radial_mm": h["inner"]["radial_mm"], "outer_mouth_radial_mm": h["outer"]["radial_mm"],
            "inner_surface": h["inner"]["surface"], "outer_surface": h["outer"]["surface"],
            "inner_mouth_v6_world_mm": h["inner"]["point"].tolist(),
        }
    pts = np.array([by_station[s] for s in STATION_ORDER])
    # body-frame sanity: station A (-,-), B (+,-), C (+,+), D (-,+) at yaw 0
    signs = np.sign(pts[:, :2]).astype(int).tolist()
    assert signs == [[-1, -1], [1, -1], [1, 1], [-1, 1]], f"corner/station mapping broken: {signs}"

    tip = jaw_lowest_point(parts, origin_v6)
    com_v6, mass_g, mass_rows = mass_properties(parts, housing)
    out = {
        "provenance": {
            "generator": "scripts/extract_claw_body_frame.py",
            "inputs": ["exports/step/gripper_electric_housing_with_camera_bay.step",
                       "solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP",
                       "cad/params.py CAMBAY_*", "cad/parts/claw_camera_bay.py"],
            "status": "CAD-derived, not measured; items marked VERIFY need a physical check (v6 geometry; v7 jaws are being redesigned)",
        },
        "frame": {
            "origin": "on the tube axis at the mean height of the four inner hole mouths",
            "axes": "+z up along the tube (= v6 +Y); +x = v6 +X; +y = -v6 Z (camera bay on v6 -Z lies at body +y)",
            "origin_v6_world_mm": origin_v6.tolist(),
            "at_yaw_0": "body x/y axes = room x/y (x toward station B, y toward station D)",
        },
        "attachment_points_body_m": pts.tolist(),
        "station_order": STATION_ORDER,
        "corner_to_station": {f"({sx:+d}X,{sz:+d}Z)": st for (sx, sz), st in CORNER_TO_STATION.items()},
        "holes": detail,
        "outer_mouth_vs_old_analysis": "scripts/analyze_cable_lines_claw_camera_bay.py used the OUTER mouth (+-54.09, 14.05, +-54.09) mm",
        "camera_in_body": camera_pose(origin_v6),
        "lowest_point_body_m": v6_to_body(tip, origin_v6).tolist(),
        "lowest_point_note": "VERIFY: lowest vertex of the v6 jaws (Claw_arm_extension); v7 jaws are being redesigned",
        "com_body_m": v6_to_body(com_v6, origin_v6).tolist(),
        "com_note": f"VERIFY: CAD-solid estimate (PETG 1.27 g/cc, tube 2.70 g/cc, servo 55 g; total {mass_g:.0f} g; "
                    "electronics/battery and sliced infill NOT modelled, so the real CoM is higher). Used only for "
                    "rigid-body orientation prediction/sim.",
        "com_mass_rows_g": mass_rows,
    }
    if check:
        ref = json.load(open(OUT))
        ok = np.allclose(ref["attachment_points_body_m"], out["attachment_points_body_m"], atol=1e-6)
        for cp in CONFIGS:
            c = json.load(open(cp))["claw"]
            ok &= np.allclose(c["attachment_points_body_m"], out["attachment_points_body_m"], atol=5e-5)
            ok &= np.allclose(c["lowest_point_body_m"], out["lowest_point_body_m"], atol=5e-5)
        print("body-frame check:", "OK" if ok else "MISMATCH")
        return 0 if ok else 1
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    np.set_printoptions(precision=5, suppress=True)
    print("origin (v6 mm):", origin_v6)
    for s, p in zip(STATION_ORDER, pts):
        d = detail[s]
        print(f"  {s}: b = {p} m  (outer mouth {np.array(d['outer_mouth_body_m'])}, hole {d['hole_length_mm']:.1f} mm, "
              f"elev {d['hole_elevation_deg']:.1f} deg)")
    print("camera:", out["camera_in_body"]["translation_m"], out["camera_in_body"]["rpy_rad"])
    print("lowest:", out["lowest_point_body_m"], " com:", out["com_body_m"], f" mass {mass_g:.0f} g")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main(check="--check" in sys.argv))
