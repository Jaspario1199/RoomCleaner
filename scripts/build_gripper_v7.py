#!/usr/bin/python3
"""
Build the gripper v7 gearbox redesign: per-part STEP/STL, the preview assembly STEP, the
mass roll-up and the standardised renders.

Run:  /usr/bin/python3 scripts/build_gripper_v7.py            (all)
      /usr/bin/python3 scripts/build_gripper_v7.py --no-render (exports + numbers only)

Writes
  exports/step/gripper_v7_<part>.step      each printed part, v7 LOCAL frame, CLOSED pose
  exports/stl/gripper_v7_<part>.stl        print orientation (z min = 0)
  exports/step/gripper_v7_preview.step     v7 gearbox + jaws + hardware + tube + (v6 cylinder reference)
                                           + camera-bay electrical box, in the v6 WORLD frame
  verification/gripper_v7_numbers.json     mass roll-up, kinematics, force table, round-trip results
  renders/gripper_v7/*.png                 iso, top along gear axes, jaws open/closed, section, guards
Reads (read-only): solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP,
                   exports/step/gripper_electric_housing_with_camera_bay.step
"""

from __future__ import annotations

import json
import os
import sys

import cadquery as cq
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cad import params as P                                   # noqa: E402
from cad.mesh_tools import tessellate, render                 # noqa: E402
from cad.parts import gripper_v7_assembly as AS               # noqa: E402
from cad.parts import gripper_v7_frame as FR                  # noqa: E402
from cad.parts import gripper_v7_gears as GR                  # noqa: E402
from cad.parts import gripper_v7_kin as K                     # noqa: E402
from calculations import gripper_v7_screening as SC           # noqa: E402

STEP_DIR = os.path.join(REPO, "exports", "step")
STL_DIR = os.path.join(REPO, "exports", "stl")
VER_DIR = os.path.join(REPO, "verification")
REN_DIR = os.path.join(REPO, "renders", "gripper_v7")
PETG = 1.27           # g/cm3 (cad/materials.py)
BOX_STEP = os.path.join(STEP_DIR, "gripper_electric_housing_with_camera_bay.step")
COVER_STEP = os.path.join(STEP_DIR, "claw_camera_bay_cover.step")

PRINTED = ("lower_plate", "upper_plate", "pinion", "compound", "follower", "jaw", "link")

# v6 per-part CAD-solid masses (verification/gripper_v6_inspection.md, PETG 1.27 g/cc on CAD volume)
V6_MASS_G = {"compound": 116.0, "follower": 32.0, "pinion": 10.0,
             "housing (upper + Part2)": 385.0 + 354.0, "jaw x2": 2 * 38.0, "link x2": 2 * 8.0}
V6_TUBE_G, V6_SERVO_G = 198.0, 55.0

# purchased-part mass estimates (g): steel 7.85 g/cc computed; the rest ASSUMED catalogue values
HW_MASS_G = {"servo MG996R (supplied)": 55.0, "horn (ASSUMED metal 25T)": 8.0,
             "pins 2 x Ø7x50 steel": 2 * 7.85e-3 * np.pi * 3.5 ** 2 * 50.0,
             "bearings 6 x 607 (ASSUMED 2.0 g)": 6 * 2.0,
             "shoulder screws 6 + nyloc 6 + washer 4 (ASSUMED)": 6 * 2.2 + 6 * 0.5 + 4 * 0.1,
             "M3x50 ties 7 + nyloc 7 (ASSUMED)": 7 * 2.9 + 7 * 0.5,
             "horn screws 4 + M2.5 inserts/screws 4 (ASSUMED)": 4 * 0.2 + 4 * 0.5}


def print_pose(name: str, wp: cq.Workplane) -> cq.Workplane:
    """Print orientation (+z up, z min = 0)."""
    if name == "upper_plate":                      # outer (servo) face down: flip about x
        wp = wp.rotate((0, 0, 0), (1, 0, 0), 180)
    zmin = wp.val().BoundingBox().zmin
    return wp.translate((0, 0, -zmin))


def part_solid(name: str) -> cq.Workplane:
    """Part in the v7 LOCAL frame at the closed pose (STEP frame)."""
    parts = AS.build(None, hardware=False)
    key = {"jaw": "jaw_R", "link": "link_R"}.get(name, name)
    return parts[key][0]


def shell_estimate(shape: cq.Shape, wall: float = 1.2, infill: float = 0.20) -> float:
    """As-printed volume (mm3): `wall` (3 perimeters x 0.4) over the whole surface, rest at `infill`.
    Thin features (< 2 x wall) come out solid.  Top/bottom skins are treated like walls (conservative)."""
    v, a = shape.Volume(), shape.Area()
    shell = min(v, a * wall)
    return shell + infill * (v - shell)


def build_all(render_views: bool = True) -> dict:
    os.makedirs(STEP_DIR, exist_ok=True)
    os.makedirs(STL_DIR, exist_ok=True)
    os.makedirs(VER_DIR, exist_ok=True)
    out: dict = {"parts": {}, "frame": "v7 local (x lateral, y claw axis, z gear axes, z=0 lower-plate inner face)"}
    closed = AS.build(None, hardware=False)

    # ---- per-part exports -----------------------------------------------------------------
    for name in PRINTED:
        wp = part_solid(name)
        shp = wp.val()
        step = os.path.join(STEP_DIR, "gripper_v7_%s.step" % name)
        stl = os.path.join(STL_DIR, "gripper_v7_%s.stl" % name)
        cq.exporters.export(wp, step)
        cq.exporters.export(print_pose(name, wp), stl, tolerance=0.05, angularTolerance=0.2)
        bb = shp.BoundingBox()
        entry = dict(valid=bool(shp.isValid()), solids=len(shp.Solids()), volume_mm3=shp.Volume(),
                     area_mm2=shp.Area(), mass_cad_g=shp.Volume() * PETG / 1000.0,
                     mass_printed_est_g=shell_estimate(shp) * PETG / 1000.0,
                     bbox=[bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax],
                     bbox_size=[bb.xlen, bb.ylen, bb.zlen], step=os.path.relpath(step, REPO),
                     stl=os.path.relpath(stl, REPO))
        # round trip
        re = cq.importers.importStep(step).val()
        rb = re.BoundingBox()
        entry["roundtrip"] = dict(
            volume_rel_diff=abs(re.Volume() - shp.Volume()) / shp.Volume(),
            bbox_max_diff=max(abs(a - b) for a, b in ((bb.xmin, rb.xmin), (bb.xmax, rb.xmax), (bb.ymin, rb.ymin),
                                                      (bb.ymax, rb.ymax), (bb.zmin, rb.zmin), (bb.zmax, rb.zmax))),
            solids=len(re.Solids()))
        out["parts"][name] = entry
        print("%-12s valid=%s  vol %9.0f mm3  CAD %.1f g  printed~%.1f g  bbox %.1f x %.1f x %.1f  rt dV %.1e" % (
            name, entry["valid"], entry["volume_mm3"], entry["mass_cad_g"], entry["mass_printed_est_g"],
            *entry["bbox_size"], entry["roundtrip"]["volume_rel_diff"]))

    # ---- v6 as-printed estimate with the SAME estimator (read-only STEP) --------------------------
    from cad.v6_loader import load_v6
    v6_parts = {}
    for n, shp in load_v6():
        v6_parts.setdefault(n, []).append(shp)
    key6 = {"compound": ("06_compound_54T_24T",), "follower": ("24T_Follower",), "pinion": ("Simple_18T_Pinionvlast",),
            "housing (upper + Part2)": ("Gripper_gear_housing", "Gripper_gear_housing_Part2"),
            "jaw x2": ("Claw_arm_extension",), "link x2": ("Claw_arm_extension3",)}
    v6_est = {}
    for label, names in key6.items():
        tot = 0.0
        for nm in names:
            for shp in v6_parts[nm]:
                tot += shell_estimate(shp) * PETG / 1000.0
        v6_est[label] = tot
    # ---- mass roll-up -----------------------------------------------------------------------
    mult = {"jaw": 2, "link": 2}
    v7_cad = {n: out["parts"][n]["mass_cad_g"] * mult.get(n, 1) for n in PRINTED}
    v7_prt = {n: out["parts"][n]["mass_printed_est_g"] * mult.get(n, 1) for n in PRINTED}
    frame_cad = v7_cad["lower_plate"] + v7_cad["upper_plate"]
    hw = dict(HW_MASS_G)
    roll = dict(
        v6_cad_solid_g=V6_MASS_G, v6_printed_gearbox_total_g=sum(V6_MASS_G.values()),
        v6_printed_est_g=v6_est, v6_printed_gearbox_total_est_g=sum(v6_est.values()),
        v7_cad_solid_g=v7_cad, v7_printed_est_g=v7_prt,
        v7_printed_gearbox_total_cad_g=sum(v7_cad.values()),
        v7_printed_gearbox_total_est_g=sum(v7_prt.values()),
        frame_cad_g=frame_cad, frame_target_g=150.0,
        purchased_g=hw, purchased_total_g=sum(hw.values()),
        v6_gripper_head_cad_g=sum(V6_MASS_G.values()) + V6_SERVO_G,
        v7_gripper_head_cad_g=sum(v7_cad.values()) + sum(hw.values()),
        v7_gripper_head_printed_est_g=sum(v7_prt.values()) + sum(hw.values()),
        note="v6 head = printed gearbox parts + servo; v7 head = printed parts + all purchased parts listed; "
             "tube, Griper Cylinder, electric box and electronics are unchanged and excluded.")
    out["mass_rollup"] = roll
    lines = ["mass roll-up (g)         v6 CAD  v6 print~   v7 CAD  v7 print~   (CAD = solid volume x PETG 1.27 g/cc;",
             "                                                      print~ = 3 walls (1.2 mm skin) + 20 % infill, same estimator both)"]
    pairs = [("compound", "compound"), ("follower", "follower"), ("pinion", "pinion"),
             ("housing / frame", None), ("jaw x2", "jaw"), ("link x2", "link")]
    for label, key in pairs:
        if key is None:
            a6 = V6_MASS_G["housing (upper + Part2)"]
            a6p = v6_est["housing (upper + Part2)"]
            a7, a7p = frame_cad, v7_prt["lower_plate"] + v7_prt["upper_plate"]
        else:
            lab6 = label if label in V6_MASS_G else key
            a6, a6p = V6_MASS_G[lab6], v6_est[lab6]
            a7, a7p = v7_cad[key], v7_prt[key]
        lines.append("  %-16s %8.1f %8.1f  %8.1f %8.1f" % (label, a6, a6p, a7, a7p))
    lines.append("  %-16s %8.1f %8.1f  %8.1f %8.1f" % ("printed total", roll["v6_printed_gearbox_total_g"],
                                                       roll["v6_printed_gearbox_total_est_g"],
                                                       roll["v7_printed_gearbox_total_cad_g"], roll["v7_printed_gearbox_total_est_g"]))
    lines.append("  v7 frame = lower plate %.1f g + upper plate %.1f g (target <= 150 g)" % (
        v7_cad["lower_plate"], v7_cad["upper_plate"]))
    lines.append("  purchased parts (v7): " + "; ".join("%s %.1f g" % (k, v) for k, v in hw.items()))
    lines.append("  purchased total %.1f g -> gripper head (printed + purchased, no tube/cylinder/box): "
                 "v7 CAD %.1f g, as printed %.1f g; v6 CAD %.1f g (printed gearbox + servo)" % (
                     roll["purchased_total_g"], roll["v7_gripper_head_cad_g"], roll["v7_gripper_head_printed_est_g"],
                     roll["v6_gripper_head_cad_g"]))
    print("\n" + "\n".join(lines))
    with open(os.path.join(VER_DIR, "gripper_v7_mass_rollup.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")

    # ---- kinematics + forces -------------------------------------------------------------------
    sc = SC.main()
    fb, fb6 = K.default(), K.v6_reference()
    kin = {}
    for tag, f, th0, th1 in (("v6", fb6, -65.2, -14.2), ("v7", fb, fb.theta_c, fb.theta_open)):
        pc, po = f.pose(th0), f.pose(th1)
        kin[tag] = dict(theta_closed=th0, theta_open=th1, travel_deg=th1 - th0, gap_closed=f.tip_gap(pc),
                        gap_open=f.tip_gap(po), tip_closed=pc.tip.tolist(), tip_open=po.tip.tolist(),
                        link_length=f.L)
    kin["v7"].update(crank_R=fb.R, P=list(map(float, fb.Pg)), jaw_AB=fb.d, tip_drop=fb.tip_drop,
                     max_tilt_deg=max(abs(p.tilt_deg) for p in fb.poses(40)))
    out["kinematics"] = kin
    tab = sc["forces"]
    out["force_table_N"] = {tag: {v: {int(g): SC.interp_force(tab, tag, v, g) for g in (10, 20, 30, 40, 50, 60, 70, 80)}
                                  for v in SC.SERVO_STALL} for tag in ("v6", "v7")}
    out["lewis"] = [r for r in sc["teeth"]]
    out["socket"] = sc["socket"]

    # ---- preview assembly (v6 world frame) ---------------------------------------------------
    full = AS.build(None, hardware=True)
    out["preview"] = export_preview(full)

    with open(os.path.join(VER_DIR, "gripper_v7_numbers.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=float)

    if render_views:
        render_all(full)
    return out


def export_preview(full) -> dict:
    """Assembly STEP in the v6 world frame (tube axis x 951.8475, z 1103.99; gear stack z 1080.49..1116.49)."""
    from cad.v6_loader import load_v6, find, CYLINDER_NAME
    assy = cq.Assembly(name="gripper_v7_preview")
    colors = {"printed": cq.Color(0.55, 0.65, 0.88), "hardware": cq.Color(0.62, 0.62, 0.66),
              "tube": cq.Color(0.78, 0.78, 0.8)}
    solids = []
    for name, (wp, kind) in full.items():
        w = AS.to_world(wp)
        solids.append(w.val())
        assy.add(w, name="v7_" + name, color=colors[kind])
    v6 = load_v6()
    cyl = find(v6, CYLINDER_NAME)                      # v6 extension, reference only (read-only STEP)
    assy.add(cq.Workplane().add(cyl), name="v6_Griper_Cylinder_reference", color=cq.Color(0.3, 0.55, 0.85))
    solids.append(cyl)
    box = cq.importers.importStep(BOX_STEP).val()
    assy.add(cq.Workplane().add(box), name="electric_housing_with_camera_bay", color=cq.Color(0.25, 0.55, 0.85))
    solids.append(box)
    if os.path.exists(COVER_STEP):
        cover = cq.importers.importStep(COVER_STEP).val()
        assy.add(cq.Workplane().add(cover), name="camera_bay_cover", color=cq.Color(0.9, 0.45, 0.15))
        solids.append(cover)
    path = os.path.join(STEP_DIR, "gripper_v7_preview.step")
    assy.save(path, "STEP")
    re = cq.importers.importStep(path)
    re_solids = re.solids().vals()
    tot_re = sum(s.Volume() for s in re_solids)
    tot_src = sum(s.Volume() for s in solids)
    bb0 = cq.Compound.makeCompound(solids).BoundingBox()
    bb1 = cq.Compound.makeCompound(re_solids).BoundingBox()
    res = dict(path=os.path.relpath(path, REPO), n_solids_src=len(solids), n_solids_reimport=len(re_solids),
               volume_src=tot_src, volume_reimport=tot_re, volume_rel_diff=abs(tot_re - tot_src) / tot_src,
               bbox_src=[bb0.xmin, bb0.xmax, bb0.ymin, bb0.ymax, bb0.zmin, bb0.zmax],
               bbox_reimport=[bb1.xmin, bb1.xmax, bb1.ymin, bb1.ymax, bb1.zmin, bb1.zmax],
               bbox_max_diff=max(abs(a - b) for a, b in zip([bb0.xmin, bb0.xmax, bb0.ymin, bb0.ymax, bb0.zmin, bb0.zmax],
                                                           [bb1.xmin, bb1.xmax, bb1.ymin, bb1.ymax, bb1.zmin, bb1.zmax])))
    tube = AS.to_world(full["tube"][0]).val()
    tb = tube.BoundingBox()
    res["tube_world"] = dict(y=[tb.ymin, tb.ymax], z_axis=(tb.zmin + tb.zmax) / 2, x_axis=(tb.xmin + tb.xmax) / 2)
    print("\npreview STEP: %d solids -> %d on reimport, volume diff %.2e, bbox diff %.4f mm" % (
        res["n_solids_src"], res["n_solids_reimport"], res["volume_rel_diff"], res["bbox_max_diff"]))
    return res


# --------------------------------------------------------------------------------------------------
# renders
# --------------------------------------------------------------------------------------------------
COL = {"lower_plate": (0.55, 0.66, 0.9), "upper_plate": (0.42, 0.52, 0.82), "compound": (0.92, 0.55, 0.18),
       "follower": (0.93, 0.75, 0.25), "pinion": (0.8, 0.3, 0.7), "jaw_R": (0.3, 0.72, 0.42),
       "jaw_L": (0.3, 0.72, 0.42), "link_R": (0.15, 0.5, 0.3), "link_L": (0.15, 0.5, 0.3),
       "servo": (0.13, 0.13, 0.18), "horn": (0.75, 0.75, 0.8), "tube": (0.8, 0.8, 0.82)}


def _meshes(parts, only=None, hide_hw_small=True, clip=None, tol=0.2, skip=("tube",)):
    ms = []
    for n, (wp, kind) in parts.items():
        if only and n not in only:
            continue
        if n in skip:
            continue
        if kind == "hardware" and hide_hw_small and n not in ("servo", "horn", "pin_C", "pin_F") \
                and not n.startswith("brg") and not n.startswith("sh_") and not n.startswith("tie"):
            continue
        shp = wp.val()
        if clip is not None:
            shp = shp.intersect(clip)
            if shp.Volume() < 1e-6:
                continue
        V, F = tessellate(shp, tol, 0.35)
        col = COL.get(n, (0.6, 0.6, 0.64))
        ms.append((V, F, col, 1.0))
    return ms


def render_all(full_closed):
    os.makedirs(REN_DIR, exist_ok=True)
    fb = K.default()
    b_all = ((-70, -135, -5), (70, 125, 85))
    closed = full_closed
    open_ = AS.build(fb.theta_open, hardware=True)
    mid = AS.build(0.5 * (fb.theta_c + fb.theta_open), hardware=True)
    m_closed = _meshes(closed)
    render(m_closed, os.path.join(REN_DIR, "iso_closed.png"), 24, -52, "gripper v7 - jaws closed (iso)",
           bounds=b_all, up="z")
    render(_meshes(open_), os.path.join(REN_DIR, "iso_open.png"), 24, -52, "gripper v7 - jaws open (iso)",
           bounds=b_all, up="z")
    render(_meshes(closed, only=[n for n in closed if n != "upper_plate" and n != "servo" and n != "horn"]),
           os.path.join(REN_DIR, "iso_gear_head.png"), 40, -35, "gearbox, upper plate and servo removed",
           bounds=((-60, -130, -5), (70, 70, 60)), up="z")
    render(m_closed, os.path.join(REN_DIR, "top_along_gear_axes.png"), 90, -90, "top view along the gear axes (closed)",
           bounds=((-75, -135, 0), (75, 125, 80)), up="z")
    no_up = [n for n in closed if n not in ("upper_plate", "servo", "horn")]
    render(_meshes(closed, only=no_up), os.path.join(REN_DIR, "top_along_gear_axes_gears.png"), 90, -90,
           "gears, links, jaws (upper plate and servo removed)", bounds=((-75, -135, 0), (75, 65, 50)), up="z")
    for lab, pts in (("open", open_), ("closed", closed), ("mid", mid)):
        no_up = [n for n in pts if n not in ("upper_plate", "servo", "horn")]
        render(_meshes(pts, only=no_up), os.path.join(REN_DIR, "jaws_%s_top.png" % lab), 90, -90,
               "jaws %s (upper plate and servo removed)" % lab, bounds=((-100, -135, 0), (100, 65, 50)), up="z")
    # section through the gear axes (plane y = 0, keep y <= 0, look from +y)
    clip = cq.Workplane("XY").box(400, 300, 200, centered=(True, False, True)).translate((0, -300, 20)).val()
    render(_meshes(closed, clip=clip, tol=0.15), os.path.join(REN_DIR, "section_gear_axes.png"), 0, 90,
           "section through the compound / follower axes (y = 0), looking -y",
           bounds=((-60, -50, -8), (60, 5, 52)), up="z", size=(9, 6))
    # mesh guards: plates translucent, guard bands red, gears underneath
    lp, up = AS.PartCache.get("lower_plate"), AS.PartCache.get("upper_plate")
    g_main, g_sync = FR.main_guard(), FR.sync_guard()
    gm = []
    for n in ("compound", "follower", "pinion"):
        V, F = tessellate(closed[n][0], 0.15, 0.3)
        gm.append((V, F, COL[n], 1.0))
    V, F = tessellate(lp, 0.2, 0.3)
    gm.append((V, F, (0.55, 0.66, 0.9), 0.35))
    V, F = tessellate(up, 0.2, 0.3)
    gm.append((V, F, (0.42, 0.52, 0.82), 0.25))
    for g in (g_main, g_sync):
        V, F = tessellate(g, 0.1, 0.3)
        gm.append((V, F, (0.85, 0.15, 0.15), 1.0))
    render(gm, os.path.join(REN_DIR, "mesh_guards.png"), 42, -50,
           "mesh guard bands (1.4 mm, red): pinion/36T on the lower plate, 24T/24T hanging from the upper plate",
           bounds=((-50, -35, -5), (55, 55, 50)), up="z", size=(9, 7))
    render(gm, os.path.join(REN_DIR, "mesh_guards_top.png"), 90, -90, "mesh guards, top view",
           bounds=((-55, -40, 0), (55, 60, 50)), up="z", size=(8, 7))
    # frame plates (lower solid, upper translucent)
    gp = [tessellate(lp, 0.15, 0.3) + ((0.55, 0.66, 0.9), 1.0), tessellate(up, 0.15, 0.3) + ((0.42, 0.52, 0.82), 0.55)]
    render(gp, os.path.join(REN_DIR, "frame_plates.png"), 30, -50, "frame: lower plate (solid) and upper plate (translucent)",
           bounds=((-50, -45, -8), (55, 125, 50)), up="z")
    # preview overview in the v6 world frame (tube, v6 cylinder reference, camera-bay box)
    from cad.v6_loader import load_v6, find, CYLINDER_NAME
    ox, oy, oz = P.GRIPV7_WORLD_ORIGIN
    ov = []
    for n, (wp, kind) in closed.items():
        if kind == AS.HARDWARE and n not in ("servo",):
            continue
        V, F = tessellate(AS.to_world(wp), 0.8 if kind == AS.TUBE else 0.3, 0.5)
        ov.append((V, F, COL.get(n, (0.6, 0.6, 0.64)), 1.0))
    cyl = find(load_v6(), CYLINDER_NAME)
    ov.append(tessellate(cyl, 1.0, 0.5) + ((0.3, 0.55, 0.85), 1.0))
    box = cq.importers.importStep(BOX_STEP).val()
    ov.append(tessellate(box, 0.8, 0.5) + ((0.25, 0.55, 0.88), 1.0))
    render(ov, os.path.join(REN_DIR, "preview_overview.png"), 20, -40, "preview assembly (v6 world frame, +y up the page)",
           bounds=((ox - 190, 560, oz - 190), (ox + 190, 1200, oz + 190)), up="y", size=(7.5, 9))
    print("renders ->", REN_DIR)


if __name__ == "__main__":
    build_all(render_views="--no-render" not in sys.argv)
