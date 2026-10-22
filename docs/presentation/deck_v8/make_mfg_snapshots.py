"""Manufacturing snapshots for deck v8: shaded views of specific areas of Jasper's own parts, straight from his STEP files.

No drawings and no dimensions are added: each snapshot is the CAD geometry itself, some cut open with a section plane so the
fit can be seen. Section faces are shaded blue. Captions and numbers live on the slide (measured from the same files).

    xvfb-run -a -s "-screen 0 1600x1200x24" /usr/bin/python3 docs/presentation/deck_v8/make_mfg_snapshots.py
        -> docs/presentation/deck_v8/fig/snap_*.png
"""
import math
from pathlib import Path

import cadquery as cq
import vtk
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent / "fig"
GR = ROOT / "cad/reference/gripper_1021/parts"
ST = ROOT / "cad/reference/station_1021"
PART = (0.80, 0.82, 0.85)        # printed part, light grey
PART2 = (0.62, 0.66, 0.72)       # mating part, darker grey
CUT = (0.55, 0.68, 0.84)         # section faces of the part
CUT2 = (0.86, 0.79, 0.62)        # section faces of the mating part
STEEL, STEEL_CUT = (0.55, 0.57, 0.60), (0.42, 0.44, 0.47)   # purchased bearing (not in the CAD)
vtk.vtkMapper.SetResolveCoincidentTopologyToPolygonOffset()      # edge lines drawn on top of their faces
SIZE = (1200, 590)


def load(path):
    return cq.importers.importStep(str(path)).val()


def halfspace_cut(solid, point, normal):
    """Remove the material on the +normal side of the plane through point."""
    nx, ny, nz = normal
    box = cq.Solid.makeBox(2000, 2000, 2000, cq.Vector(0, -1000, -1000))       # occupies x >= 0
    n = cq.Vector(nx, ny, nz).normalized()
    ref = cq.Vector(1, 0, 0)
    axis = ref.cross(n)
    if axis.Length > 1e-9:
        ang = math.degrees(math.acos(max(-1.0, min(1.0, ref.dot(n)))))
        box = box.rotate(cq.Vector(0, 0, 0), axis, ang)
    elif ref.dot(n) < 0:
        box = box.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180)
    box = box.translate(cq.Vector(*point))
    return solid.cut(box), (point, (n.x, n.y, n.z))


def face_polydata(faces, tol=0.01, ang=0.1):
    pts, polys = vtk.vtkPoints(), vtk.vtkCellArray()
    for f in faces:
        verts, tris = f.tessellate(tol, ang)
        base = pts.GetNumberOfPoints()
        for v in verts:
            pts.InsertNextPoint(v.x, v.y, v.z)
        for t in tris:
            polys.InsertNextCell(3)
            for i in t:
                polys.InsertCellPoint(base + i)
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(polys)
    return pd


def is_section_face(f, plane):
    if plane is None or BRepAdaptor_Surface(f.wrapped).GetType() != GeomAbs_Plane:
        return False
    (px, py, pz), (nx, ny, nz) = plane
    n = f.normalAt()
    c = f.Center()
    return abs(abs(n.x * nx + n.y * ny + n.z * nz) - 1) < 1e-4 and abs((c.x - px) * nx + (c.y - py) * ny + (c.z - pz) * nz) < 1e-3


def add_shape(ren, solid, color, plane, cut_color=CUT):
    faces = solid.Faces()
    groups = ((False, color), (True, cut_color))
    for want_cut, col in groups:
        sel = [f for f in faces if is_section_face(f, plane) == want_cut]
        if not sel:
            continue
        pd = face_polydata(sel)
        nrm = vtk.vtkPolyDataNormals()
        nrm.SetInputData(pd)
        nrm.SetFeatureAngle(35)
        nrm.SplittingOn()
        nrm.ConsistencyOn()
        nrm.Update()
        m = vtk.vtkPolyDataMapper()
        m.SetInputConnection(nrm.GetOutputPort())
        a = vtk.vtkActor()
        a.SetMapper(m)
        pr = a.GetProperty()
        pr.SetColor(*col)
        pr.SetAmbient(0.25)
        pr.SetDiffuse(0.75)
        pr.SetSpecular(0.15)
        pr.SetSpecularPower(20)
        ren.AddActor(a)
    # silhouette-free edge lines: the B-rep edges themselves, like a CAD viewer
    ep, el = vtk.vtkPoints(), vtk.vtkCellArray()
    for e in solid.Edges():
        pts = e.discretize(Deflection=0.02) if hasattr(e, "discretize") else None
        if pts is None:
            n = 40
            pts = [e.positionAt(i / n) for i in range(n + 1)]
        ids = []
        for p in pts:
            ids.append(ep.InsertNextPoint(p.x, p.y, p.z))
        line = vtk.vtkPolyLine()
        line.GetPointIds().SetNumberOfIds(len(ids))
        for i, pid in enumerate(ids):
            line.GetPointIds().SetId(i, pid)
        el.InsertNextCell(line)
    epd = vtk.vtkPolyData()
    epd.SetPoints(ep)
    epd.SetLines(el)
    em = vtk.vtkPolyDataMapper()
    em.SetInputData(epd)
    ea = vtk.vtkActor()
    ea.SetMapper(em)
    ea.GetProperty().SetColor(0.12, 0.12, 0.14)
    ea.GetProperty().SetLineWidth(2.2)
    ren.AddActor(ea)


def snap(name, shapes, focal, direction, up, scale):
    """shapes: [(solid, color, plane, cut colour)]; direction: from the focal point toward the camera; scale: half the view height (mm)."""
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    for solid, color, plane, cut_color in shapes:
        add_shape(ren, solid, color, plane, cut_color)
    cam = ren.GetActiveCamera()
    cam.ParallelProjectionOn()
    d = [c / math.sqrt(sum(x * x for x in direction)) for c in direction]
    cam.SetFocalPoint(*focal)
    cam.SetPosition(*(f + 500 * c for f, c in zip(focal, d)))
    cam.SetViewUp(*up)
    cam.SetParallelScale(scale)
    ren.ResetCameraClippingRange()
    ren.RemoveAllLights()
    key = vtk.vtkLight()
    key.SetLightTypeToCameraLight()
    key.SetPosition(0.6, 0.8, 1.0)
    key.SetIntensity(0.85)
    ren.AddLight(key)
    fill = vtk.vtkLight()
    fill.SetLightTypeToCameraLight()
    fill.SetPosition(-0.7, -0.3, 1.0)
    fill.SetIntensity(0.35)
    ren.AddLight(fill)
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetMultiSamples(8)
    win.AddRenderer(ren)
    win.SetSize(*SIZE)
    win.Render()
    grab = vtk.vtkWindowToImageFilter()
    grab.SetInput(win)
    grab.SetScale(2)
    grab.Update()
    w = vtk.vtkPNGWriter()
    w.SetFileName(str(OUT / f"snap_{name}.png"))
    w.SetInputConnection(grab.GetOutputPort())
    w.Write()
    print(f"wrote fig/snap_{name}.png")


def main():
    OUT.mkdir(exist_ok=True)
    ax = (970.00, 721.41)                                    # compound gear axis (1021 assembly frame)
    gear = load(GR / "10_gripper_v6r_compound_36T_24T_norelief_NAUO10.step")

    # 1. the entry lip and its 8 T-slots, seen from below
    snap("gear_lip", [(gear, PART, None, CUT)], (ax[0], ax[1], 1083.6), (-0.30, -0.45, -0.85), (0, 0, 1), 9.5)

    # 2. the bearing stack cut open on the gear axis: lip, pocket, printed pin and its socket
    a = math.radians(22.5 + 90)                              # cut between two T-slots
    n = (math.cos(a), math.sin(a), 0.0)
    p = (ax[0], ax[1], 1090.0)
    g_cut, plane = halfspace_cut(gear, p, n)
    upper = load(GR / "03_Gripper_gear_housing_NAUO3.step")
    lower = load(GR / "07_Gripper_gear_housing_Part2_NAUO7.step")
    clip = cq.Solid.makeCylinder(16.0, 80.0, cq.Vector(ax[0], ax[1], 1060.0))   # keep the region around this axis only
    u_cut, _ = halfspace_cut(upper.intersect(clip), p, n)
    l_cut, _ = halfspace_cut(lower.intersect(clip), p, n)
    # the purchased 687 bearing (7 x 14 x 5) is not in Jasper's CAD: shown in steel, seated in the lower pocket (z 1084.94 .. 1089.99)
    ring = cq.Solid.makeCylinder(7.0, 5.0, cq.Vector(ax[0], ax[1], 1084.97)).cut(cq.Solid.makeCylinder(3.5, 5.0, cq.Vector(ax[0], ax[1], 1084.97)))
    b_cut, _ = halfspace_cut(ring, p, n)
    snap("gear_stack", [(g_cut, PART, plane, CUT), (u_cut, PART2, plane, CUT2), (l_cut, PART2, plane, CUT2), (b_cut, STEEL, plane, STEEL_CUT)],
         (ax[0], ax[1], 1084.0), n, (0, 0, 1), 13.0)

    # 3. slide-in in the wall mount, cut level through the dovetails
    slip = load(ST / "Slipin_mount_piecev3.step")
    wall = load(ST / "Wall_Mount_v3.step")
    zc = 11.1
    s_cut, plane = halfspace_cut(slip, (0, 0, zc), (0, 0, 1))
    w_cut, _ = halfspace_cut(wall, (0, 0, zc), (0, 0, 1))
    snap("dovetail", [(s_cut, PART, plane, CUT), (w_cut, PART2, plane, CUT2)], (-32.0, 15.6, zc), (0.30, -0.20, 1.0), (1, 0, 0), 9.0)

    # 4. heat-set insert pocket in the slide-in lug (Ø4.1 x 7 over Ø3.4), cut on its axis
    i_cut, plane = halfspace_cut(slip, (7.85, 15.56, -47.0), (0, 1, 0))
    snap("insert_pocket", [(i_cut, PART, plane, CUT)], (7.85, 15.56, -47.0), (0.25, 1.0, 0.15), (0, 0, 1), 8.0)

    # 5. v3 spool cut through the set-screw hole: D-bore, radial set-screw hole, tie-off hole
    spool = load(ROOT / "solidworks/v3_2026-10-18/Spoolv3.STEP")
    sp_cut, plane = halfspace_cut(spool, (0, 0, 11.0), (0, 1, 0))
    snap("spool", [(sp_cut, PART, plane, CUT)], (0.0, 0.0, 11.0), (0.25, 1.0, 0.35), (0, 0, 1), 13.0)


if __name__ == "__main__":
    main()
