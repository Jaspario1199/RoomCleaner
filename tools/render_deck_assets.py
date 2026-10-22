"""
Presentation-grade product renders for the interview deck.

Clean, consistent look across every part: white or transparent background,
soft three-point lighting, flat PETG grey for context, signal orange for the
part the slide is about, brushed grey for aluminium. Orthographic iso camera
so parts read like engineering views, not like toys.

Run (needs a display; xvfb is fine):
    xvfb-run -a /usr/bin/python3 tools/render_deck_assets.py [name ...]

Outputs PNGs to docs/presentation/deck_assets/renders/.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import cadquery as cq
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "presentation" / "deck_assets" / "renders"

# Deck palette (see docs/presentation/STYLE_GUIDE.md)
INK = (0x0E / 255, 0x11 / 255, 0x16 / 255)
PETG = (0.80, 0.81, 0.83)
PETG_DARK = (0.42, 0.45, 0.50)
ALU = (0.70, 0.72, 0.75)
ORANGE = (1.0, 0x6A / 255, 0x13 / 255)


def load(path: Path, tol=0.15, ang=0.25):
    shape = cq.importers.importStep(str(path)).val()
    verts, tris = shape.tessellate(tol, ang)
    V = np.array([[v.x, v.y, v.z] for v in verts], dtype=float)
    F = np.array(tris, dtype=np.int64).reshape(-1, 3)
    return V, F


def polydata(V, F):
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(V, deep=True))
    cells = np.hstack([np.full((len(F), 1), 3, dtype=np.int64), F]).ravel()
    ca = vtk.vtkCellArray()
    ca.ImportLegacyFormat(numpy_to_vtkIdTypeArray(cells, deep=True))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(ca)
    n = vtk.vtkPolyDataNormals()
    n.SetInputData(pd)
    n.SetFeatureAngle(35)
    n.SplittingOn()
    n.ConsistencyOn()
    n.Update()
    return n.GetOutput()


def actor(pd, rgb, metal=False, edges=True):
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(pd)
    a = vtk.vtkActor()
    a.SetMapper(m)
    p = a.GetProperty()
    p.SetColor(*rgb)
    p.SetAmbient(0.18)
    p.SetDiffuse(0.78)
    p.SetSpecular(0.35 if metal else 0.08)
    p.SetSpecularPower(40 if metal else 12)
    acts = [a]
    if edges:
        fe = vtk.vtkFeatureEdges()
        fe.SetInputData(pd)
        fe.BoundaryEdgesOn()
        fe.FeatureEdgesOn()
        fe.SetFeatureAngle(40)
        fe.ManifoldEdgesOff()
        fe.NonManifoldEdgesOff()
        em = vtk.vtkPolyDataMapper()
        em.SetInputConnection(fe.GetOutputPort())
        em.ScalarVisibilityOff()
        ea = vtk.vtkActor()
        ea.SetMapper(em)
        ea.GetProperty().SetColor(*[c * 0.45 for c in rgb])
        ea.GetProperty().SetLineWidth(1.2)
        ea.GetProperty().SetOpacity(0.55)
        acts.append(ea)
    return acts


def render(layers, out_png, view=(1, -1, 0.8), up=(0, 0, 1), size=(2400, 1800),
           transparent=True, zoom=1.0, rot_x_deg=0.0):
    """layers: list of (V, F, rgb, metal)."""
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)

    R = None
    if rot_x_deg:
        t = np.radians(rot_x_deg)
        R = np.array([[1, 0, 0], [0, np.cos(t), -np.sin(t)], [0, np.sin(t), np.cos(t)]])
    allv = []
    for V, F, rgb, metal in layers:
        if R is not None:
            V = V @ R.T
        allv.append(V)
        for a in actor(polydata(V, F), rgb, metal):
            ren.AddActor(a)
    allv = np.vstack(allv)
    c = 0.5 * (allv.min(0) + allv.max(0))
    rad = 0.5 * np.linalg.norm(allv.max(0) - allv.min(0))

    ren.RemoveAllLights()
    d = np.array(view, float) / np.linalg.norm(view)
    kit = vtk.vtkLightKit()
    kit.SetKeyLightIntensity(0.95)
    kit.SetKeyLightElevation(55)
    kit.SetKeyLightAzimuth(15)
    kit.SetKeyToFillRatio(2.2)
    kit.SetKeyToHeadRatio(2.8)
    kit.AddLightsToRenderer(ren)

    cam = ren.GetActiveCamera()
    cam.ParallelProjectionOn()
    cam.SetFocalPoint(*c)
    cam.SetPosition(*(c + d * rad * 4))
    cam.SetViewUp(*up)
    ren.ResetCamera()
    cam.SetParallelScale(cam.GetParallelScale() / zoom)

    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetSize(*size)

    win.SetMultiSamples(8)
    win.AddRenderer(ren)
    win.Render()

    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(win)
    w2i.SetInputBufferTypeToRGB()
    w2i.ReadFrontBufferOff()
    w2i.Update()
    wr = vtk.vtkPNGWriter()
    wr.SetFileName(str(out_png))
    wr.SetInputConnection(w2i.GetOutputPort())
    wr.Write()
    if transparent:
        _white_to_alpha(out_png)
    print("wrote", out_png.relative_to(ROOT))


def _white_to_alpha(png):
    """Key out the pure-white background and crop to content with a margin."""
    from PIL import Image
    im = np.asarray(Image.open(png).convert("RGB")).astype(np.int16)
    bg = (im >= 254).all(axis=2)
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    rgba = np.dstack([im.astype(np.uint8), alpha])
    ys, xs = np.where(~bg)
    pad = 40
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, im.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, im.shape[1])
    Image.fromarray(rgba[y0:y1, x0:x1], "RGBA").save(png)


# --------------------------------------------------------------------------
S = lambda *p: ROOT.joinpath(*p)

JOBS = {
    # The claw as it stands today, camera bay highlighted
    "claw_v6_camera_bay": lambda: [
        (*load(S("exports/step/gripper_v6_with_camera_bay_preview.step"), 0.3, 0.3), PETG, False),
        (*load(S("exports/step/claw_camera_bay_body.step")), ORANGE, False),
    ],
    "claw_v6": lambda: [
        (*load(S("solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP"), 0.3, 0.3), PETG, False),
    ],
    "heat_fin": lambda: [
        (*load(S("solidworks/heat_plate/motor_heat_plate.step")), ALU, True),
    ],
    "station_v3_assembly": lambda: [
        (*load(S("solidworks/v3_assembly_2026-10-19/Assem_laundry_v3.STEP")), PETG, False),
    ],
    "spool_v3": lambda: [(*load(S("solidworks/v3_2026-10-18/Spoolv3.STEP")), ORANGE, False)],
    "spool_v1": lambda: [(*load(S("solidworks/v1_2026-10-07/Spool_V1_Short_22mm.step")), PETG, False)],
    "spool_v2": lambda: [(*load(S("solidworks/v1_2026-10-07/Spool_V2.step")), PETG, False)],
    "wall_mount_v3": lambda: [(*load(S("solidworks/v3_2026-10-18/Wall_Mount_v3.STEP")), PETG, False)],
    "shell_v3": lambda: [(*load(S("solidworks/v3_2026-10-18/Shell_Casing.STEP")), PETG, False)],
    "slipin_v3": lambda: [(*load(S("solidworks/v3_2026-10-18/Slipin_mount_piece_v3.STEP")), PETG, False)],
    "gen1_corner_mount": lambda: [(*load(S("cad/step/corner_mount.step")), PETG, False)],
    "gen1_winch_spool": lambda: [(*load(S("cad/step/winch_spool.step")), PETG, False)],
    "gen1_tentacle_claw": lambda: [(*load(S("cad/step/claw_assembly.step"), 0.3, 0.3), PETG, False)],
    "v6r_compound": lambda: [(*load(S("exports/step/gripper_v6r_compound_36T_24T.step")), ORANGE, False)],
    "v6r_follower": lambda: [(*load(S("exports/step/gripper_v6r_follower.step")), ORANGE, False)],
    "v6r_pinion_1brg": lambda: [(*load(S("exports/step/gripper_v6r_pinion_1brg.step")), ORANGE, False)],
    "v6_compound_original": lambda: [(*_v6_part("06_compound_54T_24T"), PETG_DARK, False)],
    "gripper_v7": lambda: [
        (*load(S("exports/step/gripper_v7_preview.step"), 0.3, 0.3), PETG, False),
    ],
}

REF1021 = "cad/reference/gripper_1021/parts/"
NAVY = (0x1F / 255, 0x3A / 255, 0x5F / 255)


def _gripper1021(head_only=False):
    """Jasper's final 1021 assembly with the lead-designed hands and the housing + camera bay (deck v2)."""
    keep = ["03_Gripper_gear_housing_NAUO3", "07_Gripper_gear_housing_Part2_NAUO7", "04_Simple_18T_Pinionvlast_NAUO4",
            "08_Claw_arm_extension3_NAUO8", "09_Claw_arm_extension3_NAUO9", "10_gripper_v6r_compound_36T_24T_norelief_NAUO10",
            "11_gripper_v6r_follower_NAUO11", "01_Body_40x19x38_tabs_and_boss_ESTIMATED_step_NAUO13"]
    if not head_only:
        keep += ["00_Griper_Cylinder_NAUO1"]
    layers = [(*load(S(REF1021 + k + ".step"), 0.2, 0.3), PETG, False) for k in keep]
    if not head_only:
        layers.append((*load(S(REF1021 + "06_aluminum_tubing_NAUO6.step"), 0.2, 0.3), ALU, True))
        layers.append((*load(S("exports/step/gripper1021_housing_cambay.step"), 0.2, 0.3), PETG, False))
        layers.append((*load(S("exports/step/gripper1021_housing_cambay_cover.step"), 0.2, 0.3), NAVY, False))
    for h in ("right", "left"):
        layers.append((*load(S(f"exports/step/gripper1021_hand_{h}.step"), 0.15, 0.25), NAVY, False))
    return layers


JOBS["gripper1021_final"] = lambda: _gripper1021(False)
JOBS["gripper1021_head"] = lambda: _gripper1021(True)


# Gen 1: the fixed overhead camera's ceiling case (shell + screw-on bezel), seen from below (deck v3.1)
def _gen1_overhead_camera():
    shell = load(S("cad/step/camera_case_overhead_shell.step"), 0.1, 0.2)
    Vb, Fb = load(S("cad/step/camera_case_overhead_bezel.step"), 0.1, 0.2)
    Vb = Vb + [0, 0, -24.6 - 3.0 - 6.0]            # bezel sits under the skirt (24.6 deep, 3 thick); 6 mm exploded gap
    return [(*shell, PETG, False), (Vb, Fb, NAVY, False)]


JOBS["gen1_overhead_camera"] = _gen1_overhead_camera


def _v6_part(name):
    """One of Jasper's v6 solids, by name, from the v6 assembly STEP (read-only)."""
    sys.path.insert(0, str(ROOT))
    from cad.v6_loader import load_v6, find
    shape = find(load_v6(), name)
    verts, tris = shape.tessellate(0.15, 0.25)
    V = np.array([[v.x, v.y, v.z] for v in verts], dtype=float)
    F = np.array(tris, dtype=np.int64).reshape(-1, 3)
    return V, F


# Final assemblies (deck v4.2, 10/22).
# The wall station as Jasper's 10/21 assembly: wall frame, slide-in mount, shell, motor, spool, heat fin, plus the encoder
# casing and magnet cap. The parts are in cad/reference/station_1021 (station frame, z up); the encoder parts are built in
# the v3 frame and sit +2.64 mm higher there (cad/ENCODER_1021_SPEC.md).
ST1021 = "cad/reference/station_1021/"


def _station1021_final():
    layers = [(*load(S(ST1021 + "Wall_Mount_v3.step")), PETG_DARK, False),
              (*load(S(ST1021 + "Slipin_mount_piecev3.step")), PETG, False),
              (*load(S(ST1021 + "Motor_Reference.step")), PETG_DARK, False),
              (*load(S(ST1021 + "Spool1011.step")), ORANGE, False),
              (*load(S(ST1021 + "Heat_horn.step")), ALU, True),
              (*load(S(ST1021 + "Shell_Casing.step")), PETG, False)]
    for n, col in (("encoder1021_casing", NAVY), ("encoder1021_magnet_cap", ORANGE)):
        V, F = load(S(f"exports/step/{n}.step"))
        layers.append((V + [0, 0, 2.64], F, col, False))
    return layers


JOBS["station_1021_final"] = _station1021_final


# The claw as built (D36): the 1021 head, the lead's hands, the housing with both cable patterns (_34, D34) and its cover,
# on the 10.48 in tube. The STEP has the 12 in tube; the head moves up by the cut and the tube is shortened from its lower end.
TUBE_TOP_Y, TUBE_CUT = 1091.19, 304.8 - 10.48 * 25.4


def _gripper1021_asbuilt():
    head = ["03_Gripper_gear_housing_NAUO3", "07_Gripper_gear_housing_Part2_NAUO7", "04_Simple_18T_Pinionvlast_NAUO4",
            "08_Claw_arm_extension3_NAUO8", "09_Claw_arm_extension3_NAUO9", "10_gripper_v6r_compound_36T_24T_norelief_NAUO10",
            "11_gripper_v6r_follower_NAUO11", "01_Body_40x19x38_tabs_and_boss_ESTIMATED_step_NAUO13"]
    up = np.array([0, TUBE_CUT, 0])
    layers = [((lambda V, F: (V + up, F))(*load(S(REF1021 + k + ".step"), 0.2, 0.3)) + (PETG, False)) for k in head]
    for h in ("right", "left"):
        V, F = load(S(f"exports/step/gripper1021_hand_{h}.step"), 0.15, 0.25)
        layers.append((V + up, F, NAVY, False))
    V, F = load(S(REF1021 + "06_aluminum_tubing_NAUO6.step"), 0.2, 0.3)
    V = V.copy()
    V[:, 1] = TUBE_TOP_Y - (TUBE_TOP_Y - V[:, 1]) * (304.8 - TUBE_CUT) / 304.8      # 12 in -> 10.48 in, top end fixed
    layers.append((V, F, ALU, True))
    layers.append((*load(S(REF1021 + "00_Griper_Cylinder_NAUO1.step"), 0.2, 0.3), PETG, False))
    layers.append((*load(S("exports/step/gripper1021_housing_cambay_34.step"), 0.2, 0.3), PETG, False))
    layers.append((*load(S("exports/step/gripper1021_housing_cambay_cover.step"), 0.2, 0.3), NAVY, False))
    return layers


JOBS["gripper1021_asbuilt"] = _gripper1021_asbuilt


# SolidWorks exports are Y-up; CadQuery parts are Z-up.
YUP = dict(up=(0, 1, 0), view=(1, 0.8, 1))
GEAR = dict(up=(0, 1, 0), view=(0.6, -0.8, 1.2))
TALL = dict(size=(1400, 3000))
OPTS = {n: YUP for n in ("claw_v6", "claw_v6_camera_bay", "station_v3_assembly", "spool_v3",
                          "spool_v1", "spool_v2", "wall_mount_v3", "shell_v3", "slipin_v3")}

for n in ("v6r_compound", "v6r_follower", "v6r_pinion_1brg"):
    OPTS[n] = dict(view=(0.7, -0.9, 1.1))
OPTS["v6_compound_original"] = dict(view=(0.7, -0.9, 1.1))
OPTS["gripper_v7"] = {**YUP, "view": (1, 0.9, 1)}
OPTS["gripper1021_final"] = {**YUP, "view": (1, 0.55, -1.1), **TALL}
OPTS["gripper1021_head"] = {**YUP, "view": (0.9, 0.5, -1.2)}
OPTS["gen1_overhead_camera"] = dict(view=(1, -1.2, -0.75))
OPTS["station_1021_final"] = dict(view=(1.0, -0.75, 0.55))
OPTS["gripper1021_asbuilt"] = {**YUP, "view": (1, 0.55, -1.1), **TALL}
for n in ("claw_v6", "claw_v6_camera_bay", "wall_mount_v3"):
    OPTS[n] = {**OPTS[n], **TALL}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    names = sys.argv[1:] or list(JOBS)
    for n in names:
        try:
            layers = JOBS[n]()
        except Exception as e:  # missing or unreadable source: report, keep going
            print(f"skip {n}: {e}")
            continue
        render(layers, OUT / f"{n}.png", **OPTS.get(n, {}))
