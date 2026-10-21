"""
Figures for docs/simulation/SW_STATIC_STATION_MOUNT.md and SW_THERMAL_HEAT_FIN.md.

Renders the v3 STEP parts in the STATION frame (+x out of the wall, +y along the
motor shaft toward the spool, +z up; origin on the shaft axis at the motor flange
face) with the load, fixture, contact and defeature faces colour-marked, plus the
line-direction diagram, the heat-fin drawing and the hand-calc fin profiles.
Every number drawn comes from calculations/simulation_loads.py.

    xvfb-run -a /usr/bin/python3 tools/render_simulation_figures.py [name ...]

Outputs: docs/simulation/img/*.png
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "simulation" / "img"
V3 = ROOT / "solidworks" / "v3_2026-10-18"
ASM = ROOT / "solidworks" / "v3_assembly_2026-10-19" / "Assem_laundry_v3.STEP"

from calculations import simulation_loads as SL  # noqa: E402

# palette: validated categorical order from the dataviz reference (blue, orange, aqua, yellow, magenta, green, violet, red)
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")


def rgb(h: str) -> tuple[float, float, float]:
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


GREY = (0.80, 0.81, 0.83)
GREY_D = (0.62, 0.64, 0.68)

# standalone STEP frame -> station frame (rotation rows, translation mm); derived from
# the placements in Assem_laundry_v3.STEP minus the shaft origin O
PLACE = {
    "wall": ([[1, 0, 0], [0, 1, 0], [0, 0, 1]], (-29.6166, 104.4600, -68.6024)),
    "slipin": ([[0, 0, 1], [1, 0, 0], [0, 1, 0]], (-34.6166, 15.5600, -55.0189)),
    "shell": ([[0, 0, 1], [1, 0, 0], [0, 1, 0]], (-21.1500, 79.2100, 68.1944)),
    "spool": ([[1, 0, 0], [0, 0, -1], [0, 1, 0]], (0.0, 29.0, 0.0)),
}
FILES = {"wall": "Wall_Mount_v3.STEP", "slipin": "Slipin_mount_piece_v3.STEP",
         "shell": "Shell_Casing.STEP", "spool": "Spoolv3.STEP"}


def _cq():
    import cadquery as cq
    return cq


_ASM_CACHE = {}


def load_part(name: str):
    """wall / slipin / shell come from the newest geometry (Assem_laundry_v3.STEP, 10/19) shifted into the
    station frame; the spool comes from Spoolv3.STEP (the assembly still holds the older Spool1011)."""
    cq = _cq()
    if name in ("wall", "shell", "slipin"):
        if not _ASM_CACHE:
            sol = sorted(cq.importers.importStep(str(ASM)).solids().vals(), key=lambda s: -s.Volume())
            for key, shp in zip(("wall", "shell", "slipin", "motor"), sol[:4]):
                _ASM_CACHE[key] = shp.translate(cq.Vector(*(-SL.O_ASM)))
        return _ASM_CACHE[name]
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.gp import gp_Trsf
    shp = cq.importers.importStep(str(V3 / FILES[name])).val()
    R, t = PLACE[name]
    tr = gp_Trsf()
    tr.SetValues(R[0][0], R[0][1], R[0][2], t[0], R[1][0], R[1][1], R[1][2], t[1], R[2][0], R[2][1], R[2][2], t[2])
    return cq.Shape.cast(BRepBuilderAPI_Transform(shp.wrapped, tr, True).Shape())


def load_assembly_context():
    """Motor body + shaft from the assembly STEP (station frame)."""
    load_part("wall")
    return _ASM_CACHE["motor"]


def finfo(f):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    c = f.Center()
    bb = f.BoundingBox()
    d = dict(t=f.geomType(), A=f.Area(), c=np.array([c.x, c.y, c.z]),
             bb=np.array([[bb.xmin, bb.xmax], [bb.ymin, bb.ymax], [bb.zmin, bb.zmax]]), f=f)
    if d["t"] == "PLANE":
        n = f.normalAt()
        d["n"] = np.array([n.x, n.y, n.z])
    if d["t"] == "CYLINDER":
        cy = BRepAdaptor_Surface(f.wrapped).Cylinder()
        ax = cy.Axis()
        d["R"] = cy.Radius()
        d["axis"] = np.array([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
        d["loc"] = np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()])
    return d


# ---------------------------------------------------------------- vtk helpers
def _mesh(face_or_shape, tol=0.08, ang=0.12):
    v, t = face_or_shape.tessellate(tol, ang)
    V = np.array([[p.x, p.y, p.z] for p in v], float)
    F = np.array(t, dtype=np.int64).reshape(-1, 3)
    if len(F) and getattr(face_or_shape, "geomType", None) and face_or_shape.geomType() == "PLANE":
        # long sliver triangles on big planar faces: drop degenerates, force the winding to the face normal
        n = face_or_shape.normalAt()
        n = np.array([n.x, n.y, n.z])
        cr = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
        area = np.linalg.norm(cr, axis=1)
        keep = area > 1e-9
        flip = (cr @ n) < 0
        F = F.copy()
        F[flip] = F[flip][:, [0, 2, 1]]
        F = F[keep]
    return V, F


def _merge(meshes):
    V, F, off = [], [], 0
    for v, f in meshes:
        if len(v) == 0:
            continue
        V.append(v)
        F.append(f + off)
        off += len(v)
    return (np.vstack(V), np.vstack(F)) if V else (np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64))


def layers_for(shape, groups, tol=0.08, base=GREY, base_opacity=1.0):
    """groups: list of (list_of_finfo, colour_rgb). Returns layers with the grouped faces removed from the base."""
    fi = [finfo(f) for f in shape.Faces()]
    picked = set()
    out = []
    for g in groups:
        faces, col = g[0], g[1]
        edges = g[2] if len(g) > 2 else True
        ids = {d["f"].hashCode() for d in faces}
        picked |= ids
        if faces:
            out.append(_merge([_mesh(d["f"], tol) for d in faces]) + (col, 1.0, edges))
    rest = [_mesh(d["f"], tol) for d in fi if d["f"].hashCode() not in picked]
    return [_merge(rest) + (base, base_opacity, True)] + out


def render_img(layers, out, **kw):
    sys.path.insert(0, str(ROOT / "tools"))
    import render_deck_assets  # noqa: F401  (only for its vtk helpers; guarded below)


# ---------------------------------------------------------------- own vtk renderer (face colours, arrows, labels)
import vtk  # noqa: E402
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402


def _poly(V, F):
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(np.asarray(V, float), deep=True))
    cells = np.hstack([np.full((len(F), 1), 3, dtype=np.int64), np.asarray(F, dtype=np.int64)]).ravel()
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
    n.ComputePointNormalsOff()
    n.ComputeCellNormalsOn()
    n.AutoOrientNormalsOff()
    n.Update()
    return n.GetOutput()


def _actors(pd, col, opacity=1.0, edges=True):
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(pd)
    m.SetResolveCoincidentTopologyToPolygonOffset()
    a = vtk.vtkActor()
    a.SetMapper(m)
    p = a.GetProperty()
    p.SetColor(*col)
    p.SetAmbient(0.22)
    p.SetDiffuse(0.75)
    p.SetSpecular(0.08)
    p.SetOpacity(opacity)
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
        em.SetResolveCoincidentTopologyToPolygonOffset()
        ea = vtk.vtkActor()
        ea.SetMapper(em)
        ea.GetProperty().SetColor(*[c * 0.4 for c in col])
        ea.GetProperty().SetLineWidth(1.0)
        ea.GetProperty().SetOpacity(min(1.0, 0.7 * opacity + 0.2))
        acts.append(ea)
    return acts


def _arrow(p0, p1, col):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    d = p1 - p0
    L = np.linalg.norm(d)
    src = vtk.vtkArrowSource()
    src.SetTipResolution(24)
    src.SetShaftResolution(24)
    src.SetTipLength(0.28)
    src.SetTipRadius(0.07)
    src.SetShaftRadius(0.028)
    x = d / L
    tmp = np.array([0, 0, 1.0]) if abs(x[2]) < 0.9 else np.array([1.0, 0, 0])
    y = np.cross(tmp, x)
    y /= np.linalg.norm(y)
    z = np.cross(x, y)
    M = vtk.vtkMatrix4x4()
    for i in range(3):
        M.SetElement(i, 0, x[i] * L)
        M.SetElement(i, 1, y[i] * L)
        M.SetElement(i, 2, z[i] * L)
        M.SetElement(i, 3, p0[i])
    tr = vtk.vtkTransform()
    tr.SetMatrix(M)
    tf = vtk.vtkTransformPolyDataFilter()
    tf.SetInputConnection(src.GetOutputPort())
    tf.SetTransform(tr)
    m = vtk.vtkPolyDataMapper()
    m.SetInputConnection(tf.GetOutputPort())
    a = vtk.vtkActor()
    a.SetMapper(m)
    a.GetProperty().SetColor(*col)
    a.GetProperty().SetAmbient(0.5)
    return a


def render(layers, out, view=(1, -1.2, 0.8), up=(0, 0, 1), size=(1500, 1250), arrows=(), labels=(),
           zoom=1.0, focus=None, title=None, legend=None):
    """layers: (V, F, rgb, opacity). arrows: (p0, p1, rgb). labels: (world_pt, text, (dx, dy), rgb)."""
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    allv = []
    for layer in layers:
        V, F, col, op = layer[:4]
        edges = layer[4] if len(layer) > 4 else True
        if len(V) == 0:
            continue
        allv.append(V)
        for a in _actors(_poly(V, F), col, op, edges):
            ren.AddActor(a)
    for p0, p1, col in arrows:
        ren.AddActor(_arrow(p0, p1, col))
    allv = np.vstack(allv)
    c = 0.5 * (allv.min(0) + allv.max(0)) if focus is None else np.array(focus, float)
    rad = 0.5 * np.linalg.norm(allv.max(0) - allv.min(0))
    kit = vtk.vtkLightKit()
    kit.SetKeyLightIntensity(0.95)
    kit.SetKeyLightElevation(50)
    kit.SetKeyLightAzimuth(20)
    kit.SetKeyToFillRatio(2.0)
    kit.AddLightsToRenderer(ren)
    cam = ren.GetActiveCamera()
    cam.ParallelProjectionOn()
    d = np.array(view, float)
    d /= np.linalg.norm(d)
    cam.SetFocalPoint(*c)
    cam.SetPosition(*(c + d * rad * 4))
    cam.SetViewUp(*up)
    ren.ResetCamera()
    cam.SetParallelScale(cam.GetParallelScale() / zoom)
    if focus is not None:
        cam.SetFocalPoint(*c)
        cam.SetPosition(*(c + d * rad * 4))
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
    wr.SetFileName(str(out))
    wr.SetInputConnection(w2i.GetOutputPort())
    wr.Write()
    im = Image.open(out).convert("RGB")
    dr = ImageDraw.Draw(im)
    f_t = _font(26)
    f_b = _font(30, bold=True)
    coord = vtk.vtkCoordinate()
    coord.SetCoordinateSystemToWorld()
    H = size[1]

    def px(pt):
        coord.SetValue(*pt)
        x, y = coord.GetComputedDoubleDisplayValue(ren)
        return x, H - y

    for pt, text, (dx, dy), col in labels:
        x, y = px(pt)
        tx, ty = x + dx, y + dy
        cc = tuple(int(255 * v) for v in col)
        dr.line([(x, y), (tx, ty)], fill=cc, width=3)
        dr.ellipse([x - 6, y - 6, x + 6, y + 6], fill=cc)
        lines = text.split("\n")
        w = max(dr.textlength(s, font=f_t) for s in lines)
        h = 32 * len(lines)
        bx0 = tx - 6 if dx >= 0 else tx - w - 6
        by0 = ty - h / 2 - 4
        dr.rectangle([bx0, by0, bx0 + w + 12, by0 + h + 8], fill=(255, 255, 255), outline=cc, width=3)
        for i, s in enumerate(lines):
            dr.text((bx0 + 6, by0 + 4 + 32 * i), s, fill=(20, 20, 20), font=f_t)
    if title:
        dr.text((24, 18), title, fill=(20, 20, 20), font=f_b)
    if legend:
        y = size[1] - 24 - 36 * len(legend)
        for col, text in legend:
            cc = tuple(int(255 * v) for v in col)
            dr.rectangle([24, y + 4, 54, y + 30], fill=cc, outline=(60, 60, 60))
            dr.text((64, y), text, fill=(20, 20, 20), font=f_t)
            y += 36
    im.save(out)
    return px


def _font(size, bold=False):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def triad(origin, length=30.0):
    o = np.array(origin, float)
    return [(o, o + np.array([length, 0, 0]), (0.85, 0.1, 0.1)),
            (o, o + np.array([0, length, 0]), (0.1, 0.55, 0.1)),
            (o, o + np.array([0, 0, length]), (0.1, 0.2, 0.85))]


def triad_labels(origin, length=30.0):
    o = np.array(origin, float)
    return [(o + np.array([length, 0, 0]), "x out of wall", (30, 0), (0.85, 0.1, 0.1)),
            (o + np.array([0, length, 0]), "y shaft", (30, 0), (0.1, 0.55, 0.1)),
            (o + np.array([0, 0, length]), "z up", (30, 0), (0.1, 0.2, 0.85))]


def side_by_side(paths, out, gap=20):
    ims = [Image.open(p).convert("RGB") for p in paths]
    h = max(i.height for i in ims)
    w = sum(i.width for i in ims) + gap * (len(ims) - 1)
    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    x = 0
    for i in ims:
        canvas.paste(i, (x, 0))
        x += i.width + gap
    canvas.save(out)


# ---------------------------------------------------------------- figure: wall mount
def fig_wall_mount():
    wall = load_part("wall")
    F = [finfo(f) for f in wall.Faces()]

    def sel(fn):
        return [d for d in F if fn(d)]

    holes = sel(lambda d: d["t"] == "CYLINDER" and abs(d["R"] - 1.984) < 0.02 and abs(abs(d["axis"][0]) - 1) < 1e-6) \
        + sel(lambda d: d["t"] == "PLANE" and d["n"][0] > 0.99 and abs(d["A"] - 37.1) < 1.0)
    back = sel(lambda d: d["t"] == "PLANE" and d["n"][0] < -0.99 and d["A"] > 30000)
    lips = sel(lambda d: d["t"] == "PLANE" and d["n"][0] < -0.99 and 2000 < d["A"] < 3500 and d["c"][0] > -22)
    shelf = sel(lambda d: d["t"] == "PLANE" and d["n"][2] > 0.99 and 2500 < d["A"] < 4000 and d["c"][2] < 0)
    groove = sel(lambda d: d["bb"][0][0] > -35.0 and d["bb"][0][1] < -29.75 and d["A"] < 1300
                 and not (d["t"] == "CYLINDER" and d["R"] > 1.9) and not (d["t"] == "PLANE" and d["A"] < 40 and abs(d["n"][0]) > 0.99 and d["c"][0] > -32))
    n_before = (len(holes), len(back), len(lips), len(shelf), len(groove))
    layers = layers_for(wall, [(back, rgb(BLUE), False), (groove, rgb(YELLOW)), (lips, rgb(ORANGE)), (shelf, rgb(VIOLET)), (holes, rgb(GREEN))])
    # panel A: room side
    p = OUT / "_wall_a.png"
    px_labels = [
        (np.array([-31.8, 34.22, 55.25]), "W2  6 stud-screw holes\n(fixed faces)", (-330, -150), rgb(GREEN)),
        (np.array([-34.8, 15.56, 40.0]), "W4  dovetail groove x3\n(primary retention)", (260, -190), rgb(YELLOW)),
        (np.array([-20.97, 90.0, 20.0]), "W3  J-lip inner\nface (backup)", (110, 70), rgb(ORANGE)),
        (np.array([-20.0, 15.56, -55.9]), "W5  shelf top\n(slide-in rests here)", (280, 120), rgb(VIOLET)),
    ]
    render(layers, p, view=(1.0, -0.9, 0.55), size=(1500, 1300), labels=px_labels, zoom=1.15,
           title="Wall_Mount_v3: room side")
    # panel B: wall side
    q = OUT / "_wall_b.png"
    render(layers, q, view=(-1.0, -0.8, 0.5), size=(1100, 1300), zoom=1.05,
           labels=[(np.array([-42.32, 15.0, 0.0]), "W1  back face\n(against the wall)", (-60, 150), rgb(BLUE))],
           title="Wall_Mount_v3: wall side")
    side_by_side([p, q], OUT / "wall_mount_v3_marked.png")
    for f in (p, q):
        f.unlink()
    return n_before


# ---------------------------------------------------------------- figure: slide-in
def fig_slipin():
    si = load_part("slipin")
    F = [finfo(f) for f in si.Faces()]

    def sel(fn):
        return [d for d in F if fn(d)]

    holes = sel(lambda d: d["t"] == "CYLINDER" and abs(d["R"] - 1.75) < 0.01 and abs(abs(d["axis"][1]) - 1) < 1e-6
                and abs(d["c"][0]) < 20 and abs(d["c"][2]) < 20)
    pilot = sel(lambda d: d["t"] == "CYLINDER" and abs(d["R"] - 11.2) < 0.05)
    seat = sel(lambda d: d["t"] == "PLANE" and d["n"][1] < -0.99 and 1200 < d["A"] < 1500 and abs(d["c"][1]) < 0.1)
    ribs = sel(lambda d: d["c"][0] < -29.7 and d["A"] > 100)
    endface = sel(lambda d: d["t"] == "PLANE" and d["n"][2] < -0.99 and 2000 < d["A"] < 2400)
    deck_top = sel(lambda d: d["t"] == "PLANE" and d["n"][0] > 0.99 and d["A"] > 15000)
    enc = sel(lambda d: (d["t"] == "CYLINDER" and abs(d["R"] - 1.725) < 0.01) or
              (d["t"] == "PLANE" and abs(d["A"] - 446.6) < 1.0) or (d["t"] == "PLANE" and abs(d["A"] - 9.3) < 0.2))
    keyhole = sel(lambda d: abs(d["c"][1] - 15.56) < 4.2 and -55.1 < d["c"][2] < -44.9 and d["A"] < 250 and d["bb"][2][1] < -44.9)
    layers = layers_for(si, [(ribs, rgb(YELLOW)), (endface, rgb(VIOLET)), (deck_top, (0.93, 0.78, 0.66), False),
                             (seat, rgb(MAGENTA)), (pilot, rgb(AQUA)), (holes, rgb(RED)),
                             (enc, rgb(YELLOW)), (keyhole, rgb(YELLOW))])
    p = OUT / "_si_a.png"
    render(layers, p, view=(1.0, -0.55, 0.75), size=(1700, 1300), zoom=1.55, focus=(-8, 22, -8),
           labels=[(np.array([-15.5, 0.0, 15.5]), "S3  4 motor holes Ø3.5\n(REMOTE LOAD faces)", (-60, -190), rgb(RED)),
                   (np.array([0.0, 0.0, 11.1]), "S4  pilot bore Ø22.4", (-300, -90), rgb(AQUA)),
                   (np.array([0.0, 0.0, -15.0]), "S5  flange seat face, y = 0\n(optional load face, bound L)", (-300, 60), rgb(MAGENTA)),
                   (np.array([-22.0, 45.0, 0.0]), "S8  encoder pockets x4\n(10/19 assembly only: defeature)", (140, -230), rgb(YELLOW)),
                   (np.array([-21.15, 70.0, 25.0]), "S9  deck top face\n(J-lip backup contact)", (-60, -150), (0.8, 0.55, 0.35)),
                   (np.array([-8.0, 15.56, -49.0]), "S7  lower lug: keyhole slot +\nØ3.4 hole (defeature)", (170, 130), rgb(YELLOW))],
           title="Slipin_mount_piece_v3: motor-tab side", up=(0, 0, 1))
    q = OUT / "_si_b.png"
    render(layers, q, view=(-1.0, -0.6, -0.55), size=(1400, 1300), zoom=0.95, up=(0, 0, 1),
           labels=[(np.array([-34.62, 15.56, 10.0]), "S2  3 dovetail ribs\n(sit in the wall-mount grooves)", (300, -170), rgb(YELLOW)),
                   (np.array([-28.0, 15.56, -55.02]), "S6  bottom end face\n(rests on shelf)", (330, 120), rgb(VIOLET))],
           title="Slipin_mount_piece_v3: wall side")
    side_by_side([p, q], OUT / "slipin_v3_marked.png")
    p.unlink()
    q.unlink()
    return len(holes), len(pilot), len(seat), len(ribs), len(endface), len(enc), len(keyhole)


# ---------------------------------------------------------------- figure: shell and spool (excluded parts)
def fig_shell_spool():
    sh = load_part("shell")
    F = [finfo(f) for f in sh.Faces()]
    corner = [d for d in F if d["t"] == "CYLINDER" and abs(d["R"] - 1.7) < 0.02 and abs(abs(d["axis"][0]) - 1) < 1e-6]
    notch = [d for d in F if d["bb"][2][0] > -55.2 and d["bb"][2][1] < -46.0 and 5.0 < d["c"][1] < 26.0 and d["bb"][0][1] < 14.5
             and d["A"] < 700]
    rim = [d for d in F if d["t"] == "PLANE" and d["n"][0] < -0.99 and abs(d["c"][0] + 21.15) < 0.01]
    layers = layers_for(sh, [(rim, rgb(BLUE)), (corner, rgb(GREEN)), (notch, rgb(ORANGE))], base=(0.78, 0.84, 0.95))
    p = OUT / "_shell.png"
    render(layers, p, view=(-1.0, -0.8, -0.45), size=(1500, 1300), zoom=1.0,
           labels=[(np.array([-15.0, 74.2, 63.48]), "4 M3 corner pockets\n(screw into the slide-in deck)", (260, 90), rgb(GREEN)),
                   (np.array([-21.15, -45.6, 20.0]), "rim plane x = -21.15\n(mates with the deck top)", (-20, -210), rgb(BLUE)),
                   (np.array([-2.0, 15.56, -51.8]), "notch for the lower lug\n(NOT a line outlet)", (230, 80), rgb(ORANGE))],
           title="Shell_Casing: EXCLUDE from Study A")
    # spool
    sp = load_part("spool")
    Fs = [finfo(f) for f in sp.Faces()]
    drum = [d for d in Fs if d["t"] == "CYLINDER" and abs(d["R"] - 7.5) < 0.05]
    bore = [d for d in Fs if d["t"] == "CYLINDER" and 2.4 < d["R"] < 2.8 and abs(abs(d["axis"][1]) - 1) < 1e-6]
    layers = layers_for(sp, [(drum, rgb(RED)), (bore, rgb(BLUE))], base=GREY)
    q = OUT / "_spool.png"
    render(layers, q, view=(0.8, -1.0, 0.7), size=(1300, 1300), zoom=0.95, focus=(0, 18, 0),
           labels=[(np.array([7.5, 18.0, 0.0]), "drum Ø15: line seat\nload plane y = 18", (-60, -380), rgb(RED)),
                   (np.array([0.0, 7.0, 0.0]), "D-bore Ø5.45", (150, 330), rgb(BLUE))],
           title="Spoolv3: EXCLUDE (remote load instead)")
    side_by_side([p, q], OUT / "shell_spool_excluded.png")
    p.unlink()
    q.unlink()
    return len(corner), len(notch), len(rim), len(drum), len(bore)


# ---------------------------------------------------------------- figure: assembled loads
def fig_station_loads():
    wall = load_part("wall")
    si = load_part("slipin")
    sh = load_part("shell")
    sp = load_part("spool")
    motor = load_assembly_context()
    layers = [_merge([_mesh(wall, 0.12)]) + (GREY, 1.0), _merge([_mesh(si, 0.12)]) + ((0.93, 0.78, 0.66), 1.0),
              _merge([_mesh(motor, 0.12)]) + ((0.35, 0.37, 0.42), 0.55),
              _merge([_mesh(sp, 0.12)]) + (rgb(AQUA), 0.8),
              _merge([_mesh(sh, 0.15)]) + ((0.7, 0.8, 0.95), 0.16)]
    t = SL.tension_cases()
    arrows, labels = [], []
    cols = {"D1": rgb(BLUE), "D2c": rgb(ORANGE), "D3": rgb(GREEN), "D4f": rgb(MAGENTA)}
    reach = SL.reachable_cases(t)
    legend = []
    for cid, label, u, T, p in reach:
        tip = p + u * 75.0
        arrows.append((p, tip, cols[cid]))
        labels.append((tip, f"{cid}", (22, -6), cols[cid]))
        legend.append((cols[cid], f"{cid}  {label}  ({(f'{T:.2f}' if abs(T - 34.0) > 0.01 else f'{T:.1f}')} N at the slip limit)"))
    arrows += triad((70, -75, -68), 28)
    labels += triad_labels((70, -75, -68), 28)
    render(layers, OUT / "station_assembly_loads.png", view=(1.0, -1.1, 0.55), size=(1700, 1350), zoom=0.95,
           arrows=arrows, labels=labels, legend=legend,
           title="Station frame, the four reachable line directions at the drum load point (not to scale)")


# ---------------------------------------------------------------- matplotlib figures
def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#6b6a63", "axes.labelcolor": "#2b2b29",
                         "xtick.color": "#6b6a63", "ytick.color": "#6b6a63", "axes.titlecolor": "#2b2b29"})
    return plt


def fig_line_directions():
    plt = _mpl()
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 6.2), dpi=130)
    cols = {"D1": BLUE, "D2c": ORANGE, "D3": GREEN, "D4f": MAGENTA, "D2": ORANGE, "D4": MAGENTA, "D5": VIOLET}
    t = SL.tension_cases()
    reach = SL.reachable_cases(t)
    bounds = [(cid, label, SL.unit_vector(th, ps)) for cid, label, th, ps, *_ in SL.CASES if cid in ("D2", "D4", "D5")]
    for ax, (i, j, xl, yl, ttl) in zip((a, b), ((0, 2, "x  out of the wall (mm)", "z  up (mm)", "Side view (x-z)"),
                                                (0, 1, "x  out of the wall (mm)", "y  along the shaft (mm)", "Top view (x-y)"))):
        ax.set_aspect("equal")
        ax.axhline(0, color="#e4e3dd", lw=0.8)
        ax.axvline(0, color="#e4e3dd", lw=0.8)
        ax.add_patch(plt.Circle((0, 0), 7.5, fill=False, ec="#2b2b29", lw=1.4) if j == 2 else
                     plt.Rectangle((-18, 7), 36, 22, fill=False, ec="#2b2b29", lw=1.2))
        if j == 2:
            ax.add_patch(plt.Circle((0, 0), 18, fill=False, ec="#6b6a63", lw=0.8, ls="--"))
        ax.add_patch(plt.Rectangle((-42.3, -68.6 if j == 2 else -94.4), 33.9, 145 if j == 2 else 220, fc="#eeeeee", ec="#6b6a63", lw=0.8))
        # information bounds first, faint and dashed
        for cid, label, u in bounds:
            p = SL.tangent_point(u)
            tip = p + u * 70
            if math.hypot(tip[i] - p[i], tip[j] - p[j]) < 20:
                continue
            ax.annotate("", xy=(tip[i], tip[j]), xytext=(p[i], p[j]),
                        arrowprops=dict(arrowstyle="-|>", color=cols[cid], lw=1.1, ls="--", alpha=0.35, shrinkA=0, shrinkB=0))
            ax.text(tip[i] + 3, tip[j] - 8, cid + " bound", color="#8a8980", fontsize=8)
        for cid, label, u, T, p in reach:
            tip = p + u * 70
            flat = math.hypot(tip[i] - p[i], tip[j] - p[j]) < 20
            if not flat:
                ax.annotate("", xy=(tip[i], tip[j]), xytext=(p[i], p[j]),
                            arrowprops=dict(arrowstyle="-|>", color=cols[cid], lw=2.2, shrinkA=0, shrinkB=0))
            ax.plot(p[i], p[j], "o", color=cols[cid], ms=5)
            if flat:
                txt = (f"{cid} (points along z, into the page)" if cid == "D1" else f"{cid} (short: mostly along y)")
                if cid == "D1":
                    ax.annotate("D1: points along z, into the page", xy=(p[i], p[j]), xytext=(18, 95), fontsize=8.5, color="#2b2b29",
                                arrowprops=dict(arrowstyle="-", color="#6b6a63", lw=0.7))
            else:
                dx, dy = (3, -13) if (cid == "D4f" and j == 2) else (3, 3)
                ax.text(tip[i] + dx, tip[j] + dy, cid + (" (under D3 here, shorter)" if (cid == "D4f" and j == 2) else ""),
                        color="#2b2b29", fontsize=11 if not (cid == "D4f" and j == 2) else 8.5, weight="bold" if not (cid == "D4f" and j == 2) else "normal")
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.set_title(ttl, loc="left")
        ax.set_xlim(-60, 90)
        ax.set_ylim(-95, 45) if j == 2 else ax.set_ylim(-100, 130)
        ax.grid(True, color="#e4e3dd", lw=0.6)
        ax.spines[["top", "right"]].set_visible(False)
    a.text(-58, -90, "wall mount (grey), drum core r 7.5 mm and flange r 18 mm", fontsize=8.5, color="#6b6a63")
    b.text(-4, -96, "spool flanges y 7..29 mm, load plane y 18 mm", fontsize=8.5, color="#6b6a63")
    fig.suptitle("Study A line directions: solid = the four reachable cases (D1, D2c, D3, D4f), faint dashed = information bounds "
                 "(D2, D4, D5, not required).\nArrows start at the drum tangent point; length is direction only. "
                 f"Slip limit {t['slip']:.1f} N, working {t['work']:.2f} N, dynamic {t['dyn']:.1f} N.",
                 x=0.01, ha="left", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(OUT / "line_directions.png", facecolor="white")


def fig_fin_zones():
    plt = _mpl()
    from matplotlib.patches import Rectangle, Circle
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 8.4), dpi=130, gridspec_kw=dict(width_ratios=[1.0, 1.25]))
    W, H = SL.FIN["w"], SL.FIN["h"]
    cx, cy = W / 2, SL.FIN["axis"]
    zt, zx = SL.FIN["patch_top"], SL.FIN["z_exit"]
    a.add_patch(Rectangle((0, 0), W, zt, fc="#f8d3cf", ec="none"))
    a.add_patch(Rectangle((0, zt), W, zx - zt, fc="#fde4c9", ec="none"))
    a.add_patch(Rectangle((0, zx), W, H - zx, fc="#d6e5f7", ec="none"))
    a.add_patch(Rectangle((0, 0), W, H, fc="none", ec="#2b2b29", lw=1.4))
    a.add_patch(Circle((cx, cy), SL.FIN["hole_d"] / 2, fc="white", ec="#2b2b29", lw=1.2))
    for sx in (-1, 1):
        for sy in (-1, 1):
            a.add_patch(Circle((cx + sx * SL.FIN["bolt_sq"] / 2, cy + sy * SL.FIN["bolt_sq"] / 2), SL.FIN["bolt_d"] / 2,
                               fc="white", ec="#2b2b29", lw=1.0))
    a.add_patch(Rectangle(((W - SL.FIN["patch_w"]) / 2, 0), SL.FIN["patch_w"], zt, fc="none", ec=RED, lw=1.4, ls="--"))
    a.text(W + 6, 18, "F1  contact patch 42.3 x 42.15\n(motor flange one face, PETG tab\nthe other): heat power, no convection", color="#2b2b29", fontsize=9, va="center")
    a.text(W + 6, 46, "F2  inside-shell strip\nh = 4 W/m2K, air 26 to 27 C (vented)", fontsize=9, va="center")
    a.text(W + 6, 150, "F3  exposed fin, 200 mm\nboth faces: h = 5.3 (bare)\nor 9.6 (painted) W/m2K,\nair 23 C", fontsize=9, va="center")
    for yy, s in ((0, "0"), (zt, "42.15"), (zx, "50"), (H, "250")):
        a.plot([-3, 0], [yy, yy], color="#6b6a63", lw=0.8)
        a.text(-4, yy, s, ha="right", va="center", fontsize=8.5, color="#6b6a63")
    a.annotate("", xy=(0, -8), xytext=(W, -8), arrowprops=dict(arrowstyle="<->", color="#2b2b29"))
    a.text(W / 2, -14, "44", ha="center", fontsize=9)
    a.text(W + 6, 21.0 - 21, "", fontsize=8)
    a.annotate("centre hole Ø22.225\n(7/8 in) at (22, 21)", xy=(cx, cy), xytext=(W + 6, 78), fontsize=8.5,
               arrowprops=dict(arrowstyle="-", color="#6b6a63", lw=0.8))
    a.annotate("4 x Ø3.4 on a 31 mm square", xy=(cx + 15.5, cy - 15.5), xytext=(W + 6, 70), fontsize=8.5,
               arrowprops=dict(arrowstyle="-", color="#6b6a63", lw=0.8))
    a.set_xlim(-14, W + 52)
    a.set_ylim(-22, H + 8)
    a.set_aspect("equal")
    a.axis("off")
    a.set_title("Fin sketch (origin bottom-left, 0.483 mm, R3 corners)", loc="left", fontsize=10)
    # right: stack-up + model sketch
    b.axis("off")
    b.set_xlim(0, 100)
    b.set_ylim(0, 100)
    b.set_title("Stack-up at the patch (not to scale) and the two models", loc="left", fontsize=10)
    b.add_patch(Rectangle((8, 56), 24, 28, fc="#7b8190", ec="#2b2b29"))
    b.text(20, 70, "motor\nflange block\n(model B-2 only)", ha="center", va="center", color="white", fontsize=9)
    b.add_patch(Rectangle((32, 56), 1.5, 28, fc="#c9c9c9", ec="#2b2b29"))
    b.text(33.2, 88, "fin\n0.483 mm", ha="center", fontsize=9)
    b.add_patch(Rectangle((33.5, 56), 10, 28, fc="#e8d8b8", ec="#2b2b29"))
    b.text(38.5, 70, "PETG\ntab 5 mm\n(ignored,\ninsulated)", ha="center", va="center", fontsize=8)
    b.annotate("", xy=(31, 50), xytext=(10, 50), arrowprops=dict(arrowstyle="-|>", color=RED, lw=2))
    b.text(20, 45, "P = 2.03 W of heat", ha="center", color=RED, fontsize=9.5)
    b.text(60, 80, "Model B-1 (required): fin only, heat power on F1,\nconvection on F2 and F3, shell or solid mesh.", fontsize=10, va="top")
    b.text(60, 62, "Model B-2 (required for any motor temperature):\nadd the motor block, bonded to F1 with a\ncontact resistance, convection on its free faces\n(h 10.1 vented / 8.7 sealed, air 26 C vented).", fontsize=10, va="top")
    b.text(60, 36, "Hand-calc targets (painted, 6061, 2.03 W through the fin)\n"
                   "eta 0.32, R_fin 18.3 K/W, rise at the shell exit z = 50 mm 37 K,\ntip rise 3.4 K.  Bare: 0.43, 25.1 K/W, 51 K, 10 K.\n"
                   "1/8 in painted: 0.69, 8.5 K/W, 17 K, 9.5 K.", fontsize=10, va="top")
    fig.tight_layout()
    fig.savefig(OUT / "heat_fin_zones.png", facecolor="white")


def fig_thermal_hand_calc():
    plt = _mpl()
    P = SL.motor_heat()
    hfix = {"bare Al": 5.3, "black paint": 9.6}
    fig, ax = plt.subplots(figsize=(10.5, 5.6), dpi=130)
    runs = [("0.019 in, painted", SL.T_AS_BUILT, "black paint", BLUE, "-"),
            ("0.019 in, bare", SL.T_AS_BUILT, "bare Al", BLUE, "--"),
            ("1/8 in, painted", SL.T_DESIGN, "black paint", ORANGE, "-")]
    lab_pos = {"0.019 in, painted": (112, 29.0), "0.019 in, bare": (128, 50.0), "1/8 in, painted": (8, 46.5)}
    for label, t_mm, finish, col, ls in runs:
        fd = SL.fin_quasi_1d(SL.ALLOYS["6061-T6"], t_mm, hfix[finish], q_total=P)
        ax.plot(fd["z"], SL.T_AMB + fd["th"], color=col, lw=2.2, ls=ls)
        zi, yi = lab_pos[label]
        ax.text(zi, yi, label, color="#2b2b29", fontsize=10, ha="left", va="bottom")
    ax.axvspan(0, SL.FIN["patch_top"], color="#f8d3cf", alpha=0.6, lw=0)
    ax.axvspan(SL.FIN["patch_top"], SL.FIN["z_exit"], color="#fde4c9", alpha=0.7, lw=0)
    ax.text(21, 96, "motor\npatch", ha="center", fontsize=8.5, color="#6b6a63")
    ax.text(46, 96, "in\nshell", ha="center", fontsize=8.5, color="#6b6a63")
    ax.axhline(SL.T_AMB, color="#6b6a63", lw=0.8)
    ax.text(248, SL.T_AMB + 1.2, "room 23 C", ha="right", fontsize=8.5, color="#6b6a63")
    ax.set_xlim(0, 250)
    ax.set_ylim(20, 100)
    ax.set_xlabel("distance up the fin from the bottom edge, z (mm)")
    ax.set_ylabel("fin temperature (C)")
    ax.set_title("Hand-calc fin temperature if all 2.03 W went through the fin (6061, 44 mm wide, quasi-1D)", loc="left", fontsize=11)
    ax.grid(True, color="#e4e3dd", lw=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.01, 0.01, "The FEA temperature plot (study B-1) should overlay these curves within about +/-20 % of the rise over room air. "
             "calculations/simulation_loads.py, sections B4-B5.", fontsize=8.5, color="#6b6a63")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "thermal_hand_calc.png", facecolor="white")


FIGS = {
    "wall": fig_wall_mount, "slipin": fig_slipin, "excluded": fig_shell_spool, "loads": fig_station_loads,
    "dirs": fig_line_directions, "fin": fig_fin_zones, "thermal": fig_thermal_hand_calc,
}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for n in (sys.argv[1:] or list(FIGS)):
        print(n, FIGS[n]())
