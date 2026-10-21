#!/usr/bin/python3
"""
Build Jasper's v6 gears modified for the 2:1 gearbox (cad/parts/gripper_v6r_gears.py): STEP + STL (print
orientation) per part, the _norelief variant of the compound, STEP round trip, every clearance / mesh / feature
check, masses, renders.

Run:  /usr/bin/python3 scripts/build_gripper_v6r_gears.py              (everything, about 10-20 minutes)
      /usr/bin/python3 scripts/build_gripper_v6r_gears.py --quick      (coarser sweeps, no 3D booleans)
      /usr/bin/python3 scripts/build_gripper_v6r_gears.py --no-render

Writes
  exports/step/gripper_v6r_{pinion,compound_36T_24T,compound_36T_24T_norelief,follower}.step   (placement z: stack
        bottom = 0, closed-pose lug orientation, gear axis on the z axis)
  exports/stl/<same names>.stl                                                                   (print orientation)
  renders/gripper_v6r_gears/*.png
  verification/gripper_v6r_gears_numbers.json
Reads (read-only): solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP   (never modified)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time

import numpy as np
import cadquery as cq

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                   # noqa: E402
from cad.mesh_tools import render, tessellate                 # noqa: E402
from cad.parts import gripper_v6r_gears as G                  # noqa: E402
from cad.v6_loader import V6_STEP                             # noqa: E402

STEP_DIR = os.path.join(REPO, "exports", "step")
STL_DIR = os.path.join(REPO, "exports", "stl")
VER_DIR = os.path.join(REPO, "verification")
REN_DIR = os.path.join(REPO, "renders", "gripper_v6r_gears")

EXPORTS = {"pinion": "gripper_v6r_pinion", "compound": "gripper_v6r_compound_36T_24T",
           "compound_norelief": "gripper_v6r_compound_36T_24T_norelief", "follower": "gripper_v6r_follower"}


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def bbox_list(s: cq.Shape):
    b = s.BoundingBox()
    return [b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax]


def export_parts() -> dict:
    os.makedirs(STEP_DIR, exist_ok=True)
    os.makedirs(STL_DIR, exist_ok=True)
    out = {}
    for key, base in EXPORTS.items():
        s = G.part(key)
        step = os.path.join(STEP_DIR, base + ".step")
        stl = os.path.join(STL_DIR, base + ".stl")
        cq.exporters.export(cq.Workplane(obj=s), step)
        pp = G.print_pose(key, s)
        cq.exporters.export(cq.Workplane(obj=pp), stl, tolerance=0.02, angularTolerance=0.1)
        re = cq.importers.importStep(step).val()
        bb, rb = bbox_list(s), bbox_list(re)
        out[key] = dict(
            valid=bool(s.isValid()), solids=len(s.Solids()), volume_mm3=s.Volume(), area_mm2=s.Area(),
            mass_g_petg=s.Volume() * P.GRIPV6R_DENSITY_PETG / 1000.0, bbox=bb,
            bbox_size=[bb[1] - bb[0], bb[3] - bb[2], bb[5] - bb[4]],
            step=os.path.relpath(step, REPO), stl=os.path.relpath(stl, REPO),
            stl_bbox_print_pose=bbox_list(pp),
            roundtrip=dict(valid=bool(re.isValid()), solids=len(re.Solids()),
                           volume_rel_diff=abs(re.Volume() - s.Volume()) / s.Volume(),
                           bbox_max_diff=max(abs(a - b) for a, b in zip(bb, rb))))
        print("%-18s valid=%s solids=%d  V %9.1f mm3  %.1f g  bbox %.2f x %.2f x %.2f  rt dV %.1e dBB %.1e" % (
            key, out[key]["valid"], out[key]["solids"], out[key]["volume_mm3"], out[key]["mass_g_petg"],
            *out[key]["bbox_size"], out[key]["roundtrip"]["volume_rel_diff"], out[key]["roundtrip"]["bbox_max_diff"]),
            flush=True)
    return out


def lightening_report() -> dict:
    n, d, rr = P.GRIPV6R_LIGHT_N, P.GRIPV6R_LIGHT_D, P.GRIPV6R_LIGHT_R
    alts = []
    for N in range(4, 10):
        best = None
        for r in np.linspace(P.GRIPV6R_POCKET_R + 2.0, G.root_r(P.GRIPV6R_Z_MAIN) - 2.0, 2001):
            dd = min(2 * (G.root_r(P.GRIPV6R_Z_MAIN) - 2.0 - r), 2 * (r - P.GRIPV6R_POCKET_R - 2.0),
                     2 * r * math.sin(math.pi / N) - 2.0)
            if dd > 0 and (best is None or dd > best[0]):
                best = (dd, r)
        if best:
            alts.append(dict(count=N, max_diameter_mm=round(best[0], 2), circle_radius_mm=round(best[1], 2),
                             removed_area_mm2=round(N * math.pi * best[0] ** 2 / 4, 1)))
    return dict(count=n, diameter_mm=d, circle_radius_mm=rr, his_original="8 x D12 on R27 (does not fit inside the 36T root R%.3f)"
                % G.root_r(P.GRIPV6R_Z_MAIN), ligaments_mm=G.lightening_ligaments(),
                min_ligament_required_mm=P.GRIPV6R_LIGHT_MIN_LIG,
                why="largest count of his own D12 holes with every ligament >= 2.0 mm (8 x D12 needs R >= 18.3 but the root "
                    "circle limits R <= 17.1)", alternatives_at_other_sizes=alts)


def crank_report() -> dict:
    return dict(
        convention="angles CCW from +x about the gear axis; his world frame = v7 local frame + (951.8475, 707.9864), "
                   "so his angle convention IS the v7 theta convention (no sign flip, no offset)",
        his_compound_deg=P.GRIPV6R_SRC_ARM_DEG_C, his_follower_deg=P.GRIPV6R_SRC_ARM_DEG_F,
        v7_closed_compound_deg=P.GRIPV6R_ARM_DEG_C, v7_closed_follower_deg=P.GRIPV6R_ARM_DEG_F,
        rotation_applied_compound_deg=G.delta_c(), rotation_applied_follower_deg=G.delta_f(),
        his_pair_mirror_error_deg=180.0 - P.GRIPV6R_SRC_ARM_DEG_C - P.GRIPV6R_SRC_ARM_DEG_F,
        note="his two lugs are 1.34 deg off an exact mirror (the 24T clocking offset he used inside the clearance window); "
             "rotating each part to the exact mirror pair puts the 24T mesh at that offset, i.e. the window centre "
             "(see mesh.sync24 centre_deg at delta 0)",
        v7_pivot_radius=P.GRIPV6R_ARM_R, his_pivot_radius=P.GRIPV6R_SRC_ARM_R,
        stroke_deg=P.GRIPV6R_SWEEP_DEG, pinion_stroke_deg=P.GRIPV6R_SWEEP_DEG * P.GRIPV6R_SWEEP_PINION_RATIO,
        big_gear_tooth_phase_deg=G.main_phase_deg(), pinion_tooth_phase_deg=G.pinion_phase_deg())


def summarise_mesh(rep: dict) -> dict:
    rows = rep["rows"]
    out = {}
    for k in ("pinion36", "sync24"):
        bl = [r[k]["backlash_mm"] for r in rows]
        gp = [r[k]["gap_mm"] for r in rows]
        ct = [r[k]["centre_deg"] for r in rows]
        i = int(np.argmin(bl))
        out[k] = dict(min_backlash_mm=min(bl), max_backlash_mm=max(bl), at_min_delta_deg=rows[i]["delta_deg"],
                      min_neutral_gap_mm=min(gp), min_gap_is_overlap=bool(min(gp) <= 0.0),
                      window_centre_deg_range=[min(ct), max(ct)], poses=len(rows))
    return out


def render_all(parts_json: dict):
    os.makedirs(REN_DIR, exist_ok=True)
    col = {"pinion": (0.35, 0.60, 0.85), "compound": (0.85, 0.55, 0.20), "follower": (0.35, 0.70, 0.40),
           "his": (0.62, 0.62, 0.66)}
    mesh = {k: tessellate(G.deep_copy(G.part(k)), tol=0.05, ang=0.3) for k in EXPORTS}
    his = {"compound": tessellate(G.deep_copy(G.home_compound()), 0.05, 0.3),
           "follower": tessellate(G.deep_copy(G.home_follower()), 0.05, 0.3),
           "pinion": tessellate(G.deep_copy(G.home_pinion()), 0.05, 0.3)}
    views = {"iso": (28, 35), "iso_under": (-28, 215), "top": (90, -90)}
    for key, base in EXPORTS.items():
        for vn, (el, az) in views.items():
            V, F = mesh[key]
            ck = "compound" if key.startswith("compound") else key
            render([(V, F, col[ck], 1.0)], os.path.join(REN_DIR, "%s_%s.png" % (base, vn)), el, az, title="%s (%s)" % (base, vn))
    # side-by-side: his original next to the modified part (same view, same scale)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
    pairs = (("compound", "compound", "06_compound_54T_24T (his)", "compound_36T_24T (v6r)"),
             ("follower", "follower", "24T_Follower (his)", "follower (v6r, lug R53)"),
             ("pinion", "pinion", "Simple_18T_Pinionvlast (his)", "pinion (unchanged)"))
    for his_k, mod_k, t0, t1 in pairs:
        for vn, (el, az) in (("iso", views["iso"]), ("top", views["top"])):
            tmp = []
            bounds = ((-45, -65, -2), (45, 45, 38)) if his_k == "compound" else ((-45, -65, -2), (45, 45, 38))
            for (V, F), rgb, tt, tag in ((his[his_k], col["his"], t0, "a"), (mesh[mod_k], col[his_k], t1, "b")):
                f = os.path.join(REN_DIR, "_tmp_%s_%s_%s.png" % (his_k, vn, tag))
                render([(V, F, rgb, 1.0)], f, el, az, title=tt, bounds=bounds, size=(6, 6), dpi=110)
                tmp.append(f)
            fig, axs = plt.subplots(1, 2, figsize=(12, 6))
            for ax, f in zip(axs, tmp):
                ax.imshow(mpimg.imread(f))
                ax.axis("off")
            fig.tight_layout()
            fig.savefig(os.path.join(REN_DIR, "side_by_side_%s_%s.png" % (his_k, vn)), dpi=110)
            plt.close(fig)
            for f in tmp:
                os.remove(f)
    # closed and open pose, all three gears placed at the v7 centres, top view
    for name, d in (("closed", 0.0), ("open", P.GRIPV6R_SWEEP_DEG)):
        s = G.pose_shapes(d)
        ms = [(*tessellate(G.deep_copy(s[k]), tol=0.05, ang=0.3), col[k], 1.0) for k in ("pinion", "compound", "follower")]
        render(ms, os.path.join(REN_DIR, "assembly_top_%s.png" % name), 90, -90, title="v6r gears at the v7 centres, %s pose" % name,
               bounds=((-60, -70, 0), (60, 60, 40)))
        render(ms, os.path.join(REN_DIR, "assembly_iso_%s.png" % name), 30, 35, title="v6r gears at the v7 centres, %s pose" % name,
               bounds=((-60, -70, 0), (60, 60, 40)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    os.makedirs(VER_DIR, exist_ok=True)
    sha_before = sha256(V6_STEP)
    out: dict = dict(frame="part frame: gear axis on z, stack bottom z = 0 (his world z %.6f), closed-pose lug orientation; "
                           "placement = v7 local frame (his world - (951.8475, 707.9864))" % P.GRIPV6R_SRC_Z0,
                     source=dict(step=P.GRIPV6R_SRC_STEP, sha256_before=sha_before))
    out["parts"] = export_parts()
    print("exported %.0f s" % (time.time() - t0), flush=True)

    out["tooth_form"] = G.radii_report()
    print("tooth form", json.dumps(out["tooth_form"]["tooth_thickness_pitch_mm"]), flush=True)
    out["lightening"] = lightening_report()
    out["crank"] = crank_report()
    out["feature_diff"] = {k: G.feature_diff(k) for k in ("pinion", "compound", "compound_norelief", "follower")}
    bad = [(k, r["feature"]) for k, rows in out["feature_diff"].items() for r in rows if "UNINTENDED" in r["status"]]
    out["feature_diff_unintended"] = bad
    print("feature diff done; unintended rows: %s  (%.0f s)" % (bad, time.time() - t0), flush=True)

    # --- 2D mesh sweeps on the outlines of the real solids -----------------------------------------------------
    step = 5.0 if args.quick else 2.5
    deltas = sorted(set([round(x, 3) for x in np.arange(-30.0, 30.0 + 1e-9, step)] +
                        [round(x, 3) for x in np.arange(0.0, P.GRIPV6R_SWEEP_DEG + 1e-9, step)] + [P.GRIPV6R_SWEEP_DEG]))
    rep = G.mesh_report(deltas)
    out["mesh"] = dict(summary=summarise_mesh(rep), rows=rep["rows"],
                       definition="backlash = free rotation window of the second gear (pinion or follower) with the "
                                  "first fixed, x pitch radius of the moving gear (circumferential, nominal pitch circle); "
                                  "gap = minimum distance between the two outlines at the neutral (window-centre) pose "
                                  "of the closed-pose phasing; poses = crank offsets from the closed pose (+ opens)")
    out["tip_root"] = dict(G.radii_report(), required_min_mm=P.GRIPV6R_TIP_ROOT_MIN)
    print("mesh summary", json.dumps(out["mesh"]["summary"]), "(%.0f s)" % (time.time() - t0), flush=True)

    out["axial"] = G.axial_gaps()
    out["radial_36T_to_follower"] = G.radial_36T_to_follower()
    print("axial", json.dumps(out["axial"]), flush=True)

    sw_deltas = np.linspace(0.0, P.GRIPV6R_SWEEP_DEG, 5 if args.quick else 12)
    sw = G.swept_clearance(sw_deltas)
    out["swept_clearance"] = dict(min=sw["min"], required_min_mm=P.GRIPV6R_SWEEP_CLEAR_MIN, deltas_deg=[float(x) for x in sw_deltas])
    per = {}
    for r in sw["rows"]:
        k = "%s -> %s" % (r["lug"], r["target"])
        if k not in per or r["distance_mm"] < per[k]["distance_mm"]:
            per[k] = dict(distance_mm=r["distance_mm"], at_delta_deg=r["delta_deg"])
    out["swept_clearance"]["per_pair_min"] = per
    print("swept clearance min", json.dumps(sw["min"]), "(%.0f s)" % (time.time() - t0), flush=True)

    if not args.quick:
        i3 = [-30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0, 45.0, 60.0, P.GRIPV6R_SWEEP_DEG]
        out["interference_3d"] = dict(
            relief=G.interference_3d(i3), norelief=G.interference_3d([0.0, 30.0, P.GRIPV6R_SWEEP_DEG], "compound_norelief"),
            positive_control=G.interference_control(),
            threshold_mm3=0.5, note="OCC boolean common volume of the full solids, three gear pairs; the positive control turns "
                                    "the second gear 3 deg out of the clearance window and must show overlap")
        print("3D interference done (%.0f s)" % (time.time() - t0), flush=True)

    out["notes"] = dict(
        pinion_interface="His pinion has NO horn or torque interface: through bore D8.00 against the D6 servo shaft (4 mm "
                         "engagement, 1 mm radial gap), no spline, no screws, no horn pocket.  Reported, not changed.",
        follower_pivot_hole="His follower pivot hole is D8.33 (not D3.5) -- kept as his.  His compound pivot hole is D3.5.",
        pivot_hole_d4="Pivot holes stay D3.5 (M3 clearance).  D4 shoulder screws would need D4.2 holes (not applied).",
        bearing_pockets="D14.075 pockets with D14.000 x 1.95 entry lips (8 lip segments with R0.25 relief notches, as his) are his faces, untouched.",
        pinion_boss_gap="Pinion top is flush with the servo-boss plane in v6.  The 0.30 mm gap is realised by placing the boss plane at "
                        "pinion top + 0.30 (a housing / servo-side dimension; the pinion is not changed).",
        relief_flag="The 0.30 mm annular relief (R%.1f .. tip, z 15.7..16) on the 36T layer top face is the ONLY change beyond tooth "
                    "count and crank length; _norelief export has none." % P.GRIPV6R_RELIEF_R_IN)
    sha_after = sha256(V6_STEP)
    out["source"]["sha256_after"] = sha_after
    out["source"]["unchanged"] = sha_before == sha_after
    with open(os.path.join(VER_DIR, "gripper_v6r_gears_numbers.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print("wrote verification/gripper_v6r_gears_numbers.json  (%.0f s)" % (time.time() - t0), flush=True)
    if not args.no_render:
        render_all(out["parts"])
        print("renders done (%.0f s)" % (time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
