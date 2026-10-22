"""
NEMA 17 STEPPER FOR THERMAL SIMULATION -- multi-body, each body a separate named STEP component (SOLIDWORKS Simulation / ANSYS import it
as an assembly, so a material can be assigned per body).

Parameters: cad/params.py, block NEMA17T_*.  Build notes / measured results: verification/heat_fin1021_build_notes.md (section E).
Tests: tests/test_nema17_thermal.py.

Motor frame (exports/step/nema17_thermal.step): front face at y = 0, axis along +y (the station orientation), body toward -y
(y -38 .. 0), pilot boss and shaft toward +y.  42.3 x 42.3 square, 38 long (SIMAX 42-38 class; Motor_Reference of the station is y -40 .. -2),
45 deg x 3 mm chamfers on the four long edges.  Bodies, front to back:

    front_cap   y -8 .. 0       die-cast aluminium; Ø22 x 2 pilot boss on the front face (y 0 .. 2); 4 tapped holes (Ø3.0 x 4.5) on the 31 mm square;
                                Ø5.0 shaft bore through
    stator      y -30 .. -8     laminated silicon steel, black-painted sides; bore Ø34
    winding     y -30 .. -8     copper + slot insulation homogenised: annulus Ø23 .. Ø34, outer face = the stator bore (THE HEAT SOURCE)
    rear_cap    y -38 .. -30    aluminium; blind Ø5.0 shaft seat, 7 deep (bottom = the shaft's back end face)
    shaft       y -37 .. 24     steel Ø5.0 (no D-flat in this model), surface coincident with the cap bores; 1 mm inside the rear cap's back face
    connector   PBT housing 16 (z) x 6 (y, -38 .. -32) x 6 (x, 21.15 .. 27.15) on the rear cap's +x side face, flush with the back face

No rotor: the cavity inside the winding (and around the shaft) is air.  The brief's Ø5.2 bores are built as Ø5.0 (NEMA17T_CAP_BORE_D) so the
shaft touches the caps, as the lead asked.  No pair of bodies overlaps; coincident faces are the contacts (listed by cad/thermal_station1021.py).

    /usr/bin/python3 -m cad.parts.nema17_thermal        (exports, body table, renders)
"""

from __future__ import annotations

import csv
import os

import cadquery as cq

from .. import params as P
from ..reference.station_1021.extract import O as ASM_ORIGIN

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STEP_DIR = os.path.join(_REPO, "exports", "step")
RENDER_DIR = os.path.join(_REPO, "renders", "thermal_station1021")
NAME = "nema17_thermal"

COLORS = {"front_cap": (0.72, 0.74, 0.78), "stator": (0.18, 0.18, 0.20), "winding": (0.80, 0.45, 0.18), "rear_cap": (0.72, 0.74, 0.78),
          "shaft": (0.45, 0.45, 0.50), "connector": (0.15, 0.30, 0.65)}


# =============================================================================================================================
# construction helpers (all in the motor frame, y = axis)
# =============================================================================================================================
def _cyl(r: float, y0: float, y1: float, x: float = 0.0, z: float = 0.0) -> cq.Solid:
    """Cylinder along +y from y0 to y1 on the axis through (x, z)."""
    return cq.Solid.makeCylinder(r, y1 - y0, cq.Vector(x, y0, z), cq.Vector(0, 1, 0))


def _square_prism(y0: float, y1: float) -> cq.Solid:
    """The 42.3 square with 45 deg corner chamfers, from y0 to y1."""
    h, c = P.NEMA17T_SIZE / 2.0, P.NEMA17T_CORNER_CHAMFER
    pts = [(h - c, h), (h, h - c), (h, -(h - c)), (h - c, -h), (-(h - c), -h), (-h, -(h - c)), (-h, h - c), (-(h - c), h)]
    plane = cq.Plane(origin=(0, y0, 0), xDir=(1, 0, 0), normal=(0, 1, 0))             # local (u, v) = (x, -z): the outline is symmetric
    solid = cq.Workplane(plane).polyline(pts).close().extrude(y1 - y0).val()
    assert solid.isValid()
    return solid


def _one(shape: cq.Shape, what: str) -> cq.Solid:
    solids = shape.Solids()
    assert len(solids) == 1 and solids[0].isValid(), f"{what}: expected one valid solid, got {len(solids)}"
    return solids[0]


def levels() -> dict:
    """y levels of the motor frame, derived from NEMA17T_*."""
    L, cap, stat = P.NEMA17T_LEN, P.NEMA17T_CAP_LEN, P.NEMA17T_STATOR_LEN
    assert abs(L - (2 * cap + stat)) < 1e-9, "NEMA17T_LEN must equal two caps plus the stator"
    return {"front": 0.0, "front_cap_back": -cap, "stator_back": -(cap + stat), "back": -L, "boss_end": P.NEMA17T_PILOT_H,
            "shaft_front": P.NEMA17T_SHAFT_PROUD, "shaft_back": -L + P.NEMA17T_SHAFT_REAR_INSET}


def tap_positions() -> list:
    """(x, z) of the 4 tapped holes, (-,-), (+,-), (-,+), (+,+)."""
    h = P.NEMA17T_HOLE_SQ / 2.0
    return [(sx * h, sz * h) for sz in (-1, 1) for sx in (-1, 1)]


# =============================================================================================================================
# the bodies
# =============================================================================================================================
def make_bodies() -> dict:
    """name -> cq.Solid in the motor frame, in the front-to-back order of P.NEMA17T_BODIES."""
    lv = levels()
    r_bore = P.NEMA17T_CAP_BORE_D / 2.0
    front = _square_prism(lv["front_cap_back"], lv["front"]).fuse(_cyl(P.NEMA17T_PILOT_D / 2.0, lv["front"], lv["boss_end"]))
    front = front.cut(_cyl(r_bore, lv["front_cap_back"] - 1.0, lv["boss_end"] + 1.0))
    for x, z in tap_positions():
        front = front.cut(_cyl(P.NEMA17T_TAP_D / 2.0, lv["front"] - P.NEMA17T_TAP_DEPTH, lv["front"] + 1.0, x, z))
    r_stator = P.NEMA17T_STATOR_BORE_D / 2.0
    stator = _square_prism(lv["stator_back"], lv["front_cap_back"]).cut(_cyl(r_stator, lv["stator_back"] - 1.0, lv["front_cap_back"] + 1.0))
    winding = _cyl(r_stator, lv["stator_back"], lv["front_cap_back"]).cut(_cyl(P.NEMA17T_WINDING_ID / 2.0, lv["stator_back"] - 1.0, lv["front_cap_back"] + 1.0))
    seat_bottom = lv["shaft_back"]                                           # blind shaft seat: bottom = the shaft's back end face
    rear = _square_prism(lv["back"], lv["stator_back"]).cut(_cyl(r_bore, seat_bottom, lv["stator_back"] + 1.0))
    shaft = _cyl(P.NEMA17T_SHAFT_D / 2.0, lv["shaft_back"], lv["shaft_front"])
    cz, cy, cx = P.NEMA17T_CONNECTOR                                         # along z, along y, along x (protrusion)
    face_x = P.NEMA17T_SIZE / 2.0
    connector = cq.Workplane("XY").box(cx, cy, cz, centered=False).translate((face_x, lv["back"], -cz / 2.0)).val()
    bodies = {"front_cap": front, "stator": stator, "winding": winding, "rear_cap": rear, "shaft": shaft, "connector": connector}
    assert tuple(bodies) == tuple(P.NEMA17T_BODIES)
    return {k: _one(v, k) for k, v in bodies.items()}


def to_station(shape: cq.Shape, t_mm: float, assembly: bool = False, origin: tuple | None = None) -> cq.Shape:
    """Motor frame -> station_1021 frame with the front face on the fin's motor face (y = -t, residual included so it is the Heat_horn's face
    shifted by the fin thickness); assembly=True adds O (asm1021 coordinates).  `origin` = (x, y, z) puts the motor-frame origin (axis, front face)
    exactly there instead (cad/thermal_station1021.py passes the MEASURED tab-hole axis and fin face, so the shared faces coincide to rounding)."""
    if origin is None:
        dx, dy, dz = P.ENC1021_REF_RESIDUAL
        origin = (dx, dy - t_mm, P.ENC1021_REF_SHIFT_Z + dz)
    s = shape.translate(cq.Vector(*origin))
    return s.translate(cq.Vector(*ASM_ORIGIN)) if assembly else s


# =============================================================================================================================
# body table
# =============================================================================================================================
def material(name: str) -> tuple:
    return next(m for m in P.NEMA17T_MATERIALS if m[0] == name)


def body_table(bodies: dict | None = None) -> list:
    bodies = make_bodies() if bodies is None else bodies
    rows = []
    for name in P.NEMA17T_BODIES:
        _, mat, k, rho, surface, note = material(name)
        v = bodies[name].Volume()
        rows.append({"name": name, "material": mat, "k": k, "density": rho, "volume": v, "mass_g": v * rho / 1000.0, "surface": surface, "note": note})
    return rows


def write_table(path: str = os.path.join(RENDER_DIR, f"{NAME}_bodies.csv"), bodies: dict | None = None) -> str:
    rows = body_table(bodies)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "suggested material", "k W/m.K", "density g/cm3", "volume mm3", "mass g", "exposed surface type", "note"])
        for r in rows:
            w.writerow([r["name"], r["material"], r["k"], r["density"], f"{r['volume']:.2f}", f"{r['mass_g']:.2f}", r["surface"], r["note"]])
        w.writerow(["total", "", "", "", f"{sum(r['volume'] for r in rows):.2f}", f"{sum(r['mass_g'] for r in rows):.2f}", "", ""])
    return path


# =============================================================================================================================
# named STEP (every body a separate named component) and read-back
# =============================================================================================================================
def export_named_step(bodies: dict, path: str, assembly_name: str = NAME, colors: dict | None = None) -> str:
    """One STEP, one named component per body (cq.Assembly), shapes exactly where they are (identity placement)."""
    asm = cq.Assembly(name=assembly_name)
    for name, shape in bodies.items():
        rgb = (colors or {}).get(name, (0.7, 0.7, 0.7))
        asm.add(shape, name=name, color=cq.Color(*rgb))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    asm.export(path, exportType="STEP")
    return path


def read_named_step(path: str) -> dict:
    """name -> cq.Shape of every named solid of a STEP file written by export_named_step (XCAF names), placement applied."""
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDF import TDF_Label, TDF_LabelSequence
    from OCP.TDocStd import TDocStd_Document
    from OCP.XCAFDoc import XCAFDoc_DocumentTool

    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    assert reader.ReadFile(path) == IFSelect_RetDone, f"cannot read {path}"
    reader.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    roots = TDF_LabelSequence()
    st.GetFreeShapes(roots)
    out = {}

    def label_name(lab) -> str:
        a = TDataStd_Name()
        return a.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), a) else ""

    def walk(lab):
        comps = TDF_LabelSequence()
        st.GetComponents_s(lab, comps)
        if comps.Length() == 0:
            return
        for i in range(comps.Length()):
            c = comps.Value(i + 1)
            ref = TDF_Label()
            st.GetReferredShape_s(c, ref)
            sub = TDF_LabelSequence()
            st.GetComponents_s(ref, sub)
            if sub.Length() > 0:
                walk(ref)
            else:
                out[label_name(ref) or label_name(c)] = cq.Shape.cast(st.GetShape_s(c))

    for i in range(roots.Length()):
        walk(roots.Value(i + 1))
    return out


# =============================================================================================================================
# exports + renders
# =============================================================================================================================
def station_variants() -> dict:
    """fin export key -> fin thickness (the asm1021 copies of the motor are made for each fin)."""
    return {"fin1p8": P.FIN1021_T_PRODUCTION_MM, "fin0p019": P.FIN1021_T_PROTOTYPE_MM}


def export_all(step_dir: str = STEP_DIR) -> dict:
    bodies = make_bodies()
    out = {"motor": export_named_step(bodies, os.path.join(step_dir, f"{NAME}.step"), colors=COLORS)}
    for key, t in station_variants().items():
        placed = {k: to_station(v, t, assembly=True) for k, v in bodies.items()}
        out[key] = export_named_step(placed, os.path.join(step_dir, f"{NAME}_{key}_asm1021.step"), colors=COLORS)
    return out


def render_all(out_dir: str = RENDER_DIR) -> list:
    """Iso views of the whole motor and of a half-section (z <= 0) showing the winding inside the stator, the caps and the shaft."""
    from . import encoder1021 as E
    os.makedirs(out_dir, exist_ok=True)
    bodies = make_bodies()
    paths = []
    items = [(bodies[k], COLORS[k], 1.0, 0.03) for k in P.NEMA17T_BODIES]
    for view, tag in (((-0.55, 0.62, 0.40), "front_iso"), ((0.55, -0.62, 0.56), "rear_iso")):          # the front face (boss, shaft) points to +y
        p = os.path.join(out_dir, f"{NAME}_{tag}.png")
        E.render_scene(items, p, (view, (0, 0, 1)), f"{NAME}: {tag.replace('_', ' ')} (front cap, stator, winding, rear cap, shaft, connector)",
                       px=800, note="motor frame: front face y = 0, shaft toward +y; no rotor")
        paths.append(p)
    half = cq.Workplane("XY").box(80, 120, 40, centered=False).translate((-40, -60, -40)).val()      # keeps z <= 0
    cut_items = [(bodies[k].intersect(half), COLORS[k], 1.0, 0.03) for k in P.NEMA17T_BODIES]
    p = os.path.join(out_dir, f"{NAME}_section_z0.png")
    E.render_scene(cut_items, p, ((0, 0, 1), (0, 1, 0)), f"{NAME}: section z = 0 seen from +z (winding Ø23-Ø34 inside the stator, air cavity, shaft)",
                   px=800, bounds=((-26, -42, -2), (26, 28, 2)), note="+x right, +y up (front face at y = 0, shaft end at the top)")
    paths.append(p)
    return paths


def main() -> None:
    bodies = make_bodies()
    tot = 0.0
    for r in body_table(bodies):
        s = bodies[r["name"]]
        bb = s.BoundingBox()
        tot += r["mass_g"]
        print(f"{r['name']:<10} valid={s.isValid()} solids={len(s.Solids())} vol={r['volume']:9.2f} mm3 mass={r['mass_g']:6.2f} g k={r['k']:6.2f} "
              f"bbox x[{bb.xmin:.2f},{bb.xmax:.2f}] y[{bb.ymin:.2f},{bb.ymax:.2f}] z[{bb.zmin:.2f},{bb.zmax:.2f}]  ({r['surface']})")
    print(f"total mass {tot:.1f} g (reference motor mass {P.THERMAL_MOTOR_MASS_G:.0f} g)")
    for k, p in export_all().items():
        print("step", k, p)
    print("table", write_table(bodies=bodies))
    print(len(render_all()), "renders ->", RENDER_DIR)


if __name__ == "__main__":
    main()
