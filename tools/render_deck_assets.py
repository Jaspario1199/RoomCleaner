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
    "gripper_v7": lambda: [
        (*load(S("exports/step/gripper_v7_preview.step"), 0.3, 0.3), PETG, False),
    ],
}

# SolidWorks exports are Y-up; CadQuery parts are Z-up.
YUP = dict(up=(0, 1, 0), view=(1, 0.8, 1))
TALL = dict(size=(1400, 3000))
OPTS = {n: YUP for n in ("claw_v6", "claw_v6_camera_bay", "station_v3_assembly", "spool_v3",
                          "spool_v1", "spool_v2", "wall_mount_v3", "shell_v3", "slipin_v3")}

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
