"""
THERMAL STATION 1021 -- simulation-ready geometry of the winch motor stack of the 10/21 station for SOLIDWORKS Simulation / ANSYS:
motor | aluminium heat fin | PETG slip-in motor tab, the 4 motor screws and the candidate brass heat-set inserts.  One STEP per variant,
assembly coordinates (Assem_laundry_v3_step_1021 + nothing: drops in at the origin), every solid a separate NAMED component.

Spec: cad/HEAT_FIN_1021_SPEC.md sections 3B / E.  Parameters: cad/params.py blocks FIN1021_*, THERMAL_*, NEMA17T_*.
Build notes, body tables, contact lists: verification/heat_fin1021_build_notes.md.  Tests: tests/test_thermal_station1021.py.

Variants (cad/params.py THERMAL_VARIANTS):
    fin1p8           1/8 in fin (3.175), motor = the Motor_Reference block (no shaft) shifted by 2.0 - t, 4 x Ø3.0 x 4.0 holes in its front face,
                     screws whose Ø3.0 shank fills those holes exactly (shared cylindrical face, no overlap)
    fin0p019         the same stack with the 0.019 in prototype fin (motor shifted +1.517)
    detailed_fin1p8  1/8 in fin, motor = the multi-body NEMA 17 of cad/parts/nema17_thermal.py (front cap, stator, winding, rear cap, shaft,
                     connector); real M3 x 12 screws reach 3.825 mm into the front cap's Ø3.0 x 4.5 holes

Bodies (names are the STEP component names):  motor_block | front_cap stator winding rear_cap shaft connector;  fin_in, fin_out (the fin split
by the horizontal plane z = THERMAL_FIN_SPLIT_Z = 31.16, the roof plate top at the shell's fin slot, where it leaves the shell enclosure, so each side can
carry its own convection zone);  slipin_mount;
screw_1..4;  insert_deck (candidate: the Ø4.1 x 7 pocket in the deck under the spool);  insert_enc_1..4 (candidate: the four Ø3.45 x 4 divot holes).
THERMAL_INSERTS selects which candidate inserts exist.  Which inserts Jasper means is NOT confirmed.

Work frame: station_1021 (the reference STEP frame, residual included; the fin, slip-in, motor block and holes are all measured / derived in it);
the exported STEP = that + O.  Every position below is MEASURED from the slip-in STEP (not typed): the tab holes, the deck pocket and the divot holes.

    /usr/bin/python3 -m cad.thermal_station1021 [variant ...]        (exports, body + contact tables, section renders; about 2 minutes)
"""

from __future__ import annotations

import csv
import functools
import itertools
import math
import os
import sys

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane

from . import params as P
from .parts import heat_fin1021 as H
from .parts import nema17_thermal as N
from .reference.station_1021.extract import O as ASM_ORIGIN

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEP_DIR = os.path.join(_REPO, "exports", "step")
RENDER_DIR = os.path.join(_REPO, "renders", "thermal_station1021")
REF_DIR = H.REF_DIR
BBOX_TOL = 1.0e-3        # mm, bounding-box slack when deciding which pairs to test
AXIS_TOL = 0.02          # mm, how close a measured cylinder radius must be to the parameter that names it


def _name(key: str) -> str:
    return f"thermal_station1021_{key}"


def variants() -> dict:
    """key -> (fin thickness, motor model)."""
    return {k: (t, m) for k, t, m in P.THERMAL_VARIANTS}


# =============================================================================================================================
# reference parts and measuring them
# =============================================================================================================================
@functools.lru_cache(maxsize=None)
def reference(name: str) -> cq.Shape:
    return cq.importers.importStep(os.path.join(REF_DIR, f"{name}.step")).val()


def _axis_letter(d) -> str:
    return "xyz"[max(range(3), key=lambda i: abs(d[i]))]


def cylinders(shape: cq.Shape, radius: float, axis: str, tol: float = AXIS_TOL) -> list:
    """Cylinder surfaces of `shape` with the given radius whose axis runs along `axis` ('x', 'y' or 'z'), grouped by axis position (the CAD splits every
    hole into two half-cylinder faces): list of dicts {c: (u, v) the axis position in the two other coordinates in xyz order, r, lo, hi: extent along the axis}."""
    groups = {}
    idx = "xyz".index(axis)
    other = [i for i in range(3) if i != idx]
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() != GeomAbs_Cylinder:
            continue
        cy = a.Cylinder()
        d = cy.Axis().Direction()
        loc = cy.Axis().Location()
        d, loc = (d.X(), d.Y(), d.Z()), (loc.X(), loc.Y(), loc.Z())
        if _axis_letter(d) != axis or abs(cy.Radius() - radius) > tol:
            continue
        bb = f.BoundingBox()
        lo, hi = (bb.xmin, bb.ymin, bb.zmin)[idx], (bb.xmax, bb.ymax, bb.zmax)[idx]
        key = (round(loc[other[0]], 3), round(loc[other[1]], 3))
        g = groups.setdefault(key, {"c": (loc[other[0]], loc[other[1]]), "r": cy.Radius(), "lo": lo, "hi": hi})
        g["lo"], g["hi"] = min(g["lo"], lo), max(g["hi"], hi)
    return sorted(groups.values(), key=lambda g: g["c"])


@functools.lru_cache(maxsize=None)
def measure_slipin() -> dict:
    """Tab holes, deck pocket and divot holes, measured on the slip-in STEP (station_1021 frame)."""
    sl = reference("Slipin_mount_piecev3")
    tab = [g for g in cylinders(sl, P.THERMAL_TAB_HOLE_D / 2.0, "y") if g["lo"] < 0.5 and g["hi"] > 4.5]          # the through holes of the 5 mm tab
    deck = cylinders(sl, P.THERMAL_DECK_INSERT_OD / 2.0, "z")
    enc = cylinders(sl, P.THERMAL_ENC_INSERT_OD / 2.0, "x")
    assert len(tab) == 4, f"expected 4 tab holes, found {len(tab)}"
    assert len(deck) == 1, f"expected the single deck pocket, found {len(deck)}"
    assert len(enc) == 4, f"expected 4 divot holes, found {len(enc)}"
    tab_front, tab_back = min(g["lo"] for g in tab), max(g["hi"] for g in tab)
    return {"tab_holes": [g["c"] for g in sorted(tab, key=lambda g: (g["c"][1], g["c"][0]))],         # (x, z): (-,-), (+,-), (-,+), (+,+)
            "tab_front_y": tab_front, "tab_back_y": tab_back, "tab_hole_r": tab[0]["r"],
            "deck": {"xy": deck[0]["c"], "r": deck[0]["r"], "z_top": deck[0]["hi"], "z_bottom": deck[0]["lo"]},
            "enc": [{"yz": g["c"], "r": g["r"], "x_open": g["hi"], "x_bottom": g["lo"]} for g in sorted(enc, key=lambda g: g["c"])]}   # (y, z) sorted


def motor_front_face_y(t_mm: float) -> float:
    """y of the fin's motor-side face = where the motor's front face sits (station_1021 frame, residual included)."""
    return H.make_fin(t_mm).BoundingBox().ymin


@functools.lru_cache(maxsize=None)
def measure_shell_slot() -> dict:
    """The shell's fin slot: the two walls normal to y (station_1021 frame, residual included), their y positions and z span (the roof plate)."""
    horn = H.reference_horn().BoundingBox()
    faces = [f for f in reference("Shell_Casing").Faces() if f.geomType() == "PLANE" and abs(f.normalAt().y) > 0.999
             and f.BoundingBox().xmin < horn.xmax and f.BoundingBox().xmax > horn.xmin
             and 20.0 < f.BoundingBox().zmin < 40.0 and -10.0 < f.BoundingBox().ymin < 10.0 and f.BoundingBox().zlen < 10.0]
    assert len(faces) == 2, f"expected the two slot walls, found {len(faces)}"
    faces.sort(key=lambda f: f.BoundingBox().ymin)
    z_hi = [f.BoundingBox().zmax for f in faces]
    assert abs(z_hi[0] - z_hi[1]) < 1e-3, f"the two slot walls end at different heights: {z_hi}"
    return {"y_motor_side": faces[0].BoundingBox().ymin, "y_spool_side": faces[1].BoundingBox().ymin,
            "z_lo": min(f.BoundingBox().zmin for f in faces), "z_hi": z_hi[0]}


def measure_shell_top_z() -> float:
    """z of the roof plate top at the fin slot = where the fin leaves the shell enclosure: the top of the two slot walls of the Shell_Casing
    (31.16 in the station_1021 frame; roof plate z 27.84 .. 31.16).  The funnel that rises around the slot above it (z 33 at 6 mm off the fin, 36 to 37
    at 9 mm) is outside air and is NOT the split."""
    return measure_shell_slot()["z_hi"]


# =============================================================================================================================
# bodies
# =============================================================================================================================
def _cyl(r: float, p0: tuple, axis: str, length: float) -> cq.Solid:
    """Cylinder from the point p0 along +axis."""
    d = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    return cq.Solid.makeCylinder(r, length, cq.Vector(*p0), cq.Vector(*d))


def _one(shape: cq.Shape, what: str) -> cq.Solid:
    solids = shape.Solids()
    assert len(solids) == 1 and solids[0].isValid() and solids[0].Volume() > 0, f"{what}: expected one valid solid, got {len(solids)}"
    return solids[0]


def split_fin(fin: cq.Solid, z_split: float) -> tuple:
    """(fin_in, fin_out): the fin below / above the horizontal plane z = z_split (they touch on that plane)."""
    big = 1000.0
    below = cq.Workplane("XY").box(2 * big, 2 * big, big, centered=False).translate((-big, -big, z_split - big)).val()
    above = cq.Workplane("XY").box(2 * big, 2 * big, big, centered=False).translate((-big, -big, z_split)).val()
    return _one(fin.intersect(below), "fin_in"), _one(fin.intersect(above), "fin_out")


def motor_block(t_mm: float, holes: list) -> cq.Solid:
    """Motor_Reference block only, moved so its front face is on the fin's motor face (shift 2.0 - t, from the geometry), with 4 x Ø3.0 x 4.0 holes."""
    ref = reference("Motor_Reference")
    block = max(ref.Solids(), key=lambda s: s.Volume())                       # the 42.3 square block; the other solid is the shaft
    y_front = motor_front_face_y(t_mm)
    block = block.translate(cq.Vector(0.0, y_front - block.BoundingBox().ymax, 0.0))
    for x, z in holes:
        block = block.cut(_cyl(P.THERMAL_MOTOR_HOLE_D / 2.0, (x, y_front - P.THERMAL_MOTOR_HOLE_DEPTH, z), "y", P.THERMAL_MOTOR_HOLE_DEPTH + 1.0))
    return _one(block, "motor_block")


def screw(xz: tuple, y_head_bottom: float, y_tip: float) -> cq.Solid:
    """Simplified M3 socket-head screw along y: head Ø5.5 x 3.0 on the tab's spool-side face, shank Ø3.0 from the head down to y_tip."""
    x, z = xz
    head = _cyl(P.THERMAL_SCREW_HEAD_D / 2.0, (x, y_head_bottom, z), "y", P.THERMAL_SCREW_HEAD_H)
    shank = _cyl(P.THERMAL_SCREW_D / 2.0, (x, y_tip, z), "y", y_head_bottom - y_tip)
    return _one(head.fuse(shank), "screw")


def sleeve(r_out: float, r_in: float, p0: tuple, axis: str, length: float) -> cq.Solid:
    """Brass sleeve along +axis from p0: outer radius = the measured pocket / hole radius (shared cylindrical face), bore r_in."""
    return _one(_cyl(r_out, p0, axis, length).cut(_cyl(r_in, tuple(c - (1.0 if a == axis else 0.0) for c, a in zip(p0, "xyz")), axis, length + 2.0)), "insert")


def build_station(key: str) -> dict:
    """name -> cq.Solid for one variant, station_1021 frame (the STEP adds O).  Insertion order = export order."""
    t, model = variants()[key]
    m = measure_slipin()
    holes = m["tab_holes"]
    z_split = P.THERMAL_FIN_SPLIT_Z
    assert abs(measure_shell_top_z() - z_split) <= P.THERMAL_FIN_SPLIT_TOL, \
        f"shell top z {measure_shell_top_z():.3f} differs from THERMAL_FIN_SPLIT_Z {z_split} by more than {P.THERMAL_FIN_SPLIT_TOL}"
    bodies = {}
    y_front = motor_front_face_y(t)
    if model == "block":
        bodies["motor_block"] = motor_block(t, holes)
        y_tip = y_front - P.THERMAL_MOTOR_HOLE_DEPTH                            # shank fills the Ø3.0 x 4.0 holes exactly
    else:
        origin = (sum(h[0] for h in holes) / 4.0, y_front, sum(h[1] for h in holes) / 4.0)       # motor axis = the centre of the 4 measured tab holes, front face on the fin
        for name, shape in N.make_bodies().items():
            bodies[name] = N.to_station(shape, t, origin=origin)
        y_tip = m["tab_back_y"] - P.THERMAL_SCREW_LEN_DETAILED                  # M3 x 12 under the head: 3.825 mm into the front cap
    bodies["fin_in"], bodies["fin_out"] = split_fin(H.make_fin(t), z_split)
    bodies["slipin_mount"] = reference("Slipin_mount_piecev3")
    for i, xz in enumerate(holes, start=1):
        bodies[f"screw_{i}"] = screw(xz, m["tab_back_y"], y_tip)
    if "deck" in P.THERMAL_INSERTS:
        d = m["deck"]
        top = d["z_top"]
        bodies["insert_deck"] = sleeve(d["r"], P.THERMAL_DECK_INSERT_ID / 2.0, (d["xy"][0], d["xy"][1], top - P.THERMAL_DECK_INSERT_LEN), "z", P.THERMAL_DECK_INSERT_LEN)
    if "enc" in P.THERMAL_INSERTS:
        for i, e in enumerate(m["enc"], start=1):
            bodies[f"insert_enc_{i}"] = sleeve(e["r"], P.THERMAL_ENC_INSERT_ID / 2.0, (e["x_open"] - P.THERMAL_ENC_INSERT_LEN, e["yz"][0], e["yz"][1]), "x",
                                               P.THERMAL_ENC_INSERT_LEN)
    return bodies


def to_assembly(bodies: dict) -> dict:
    return {k: v.translate(cq.Vector(*ASM_ORIGIN)) for k, v in bodies.items()}


# =============================================================================================================================
# materials and the body table
# =============================================================================================================================
def material_of(name: str, model: str) -> tuple:
    """(material to assign, density g/cm3, k W/m.K, note) of one body."""
    if name in P.NEMA17T_BODIES:
        _, mat, k, rho, _, note = N.material(name)
        return mat, rho, k, note
    row = next(r for r in P.THERMAL_MATERIALS if name == r[0] or name.startswith(r[0] + "_"))
    dens = dict(P.THERMAL_DENSITY_G_CM3)
    if row[2] == "motor":
        rho = P.THERMAL_MOTOR_MASS_G * 1000.0 / max(reference("Motor_Reference").Solids(), key=lambda s: s.Volume()).Volume()    # g/cm3 = g / (mm3 / 1000)
    else:
        rho = dens[row[2]]
    return row[1], rho, row[3], row[4]


def body_table(bodies: dict, model: str) -> list:
    rows = []
    for name, shape in bodies.items():
        mat, rho, k, note = material_of(name, model)
        v = shape.Volume()
        rows.append({"name": name, "material": mat, "k": k, "density": rho, "volume": v, "mass_g": v * rho / 1000.0, "note": note})
    return rows


# =============================================================================================================================
# interference and contact report
# =============================================================================================================================
def _face_geometry(f: cq.Face):
    a = BRepAdaptor_Surface(f.wrapped)
    if a.GetType() == GeomAbs_Plane:
        ax = a.Plane().Axis()
        n, p = ax.Direction(), ax.Location()
        return ("plane", (n.X(), n.Y(), n.Z()), (p.X(), p.Y(), p.Z()), 0.0)
    if a.GetType() == GeomAbs_Cylinder:
        cy = a.Cylinder()
        n, p = cy.Axis().Direction(), cy.Axis().Location()
        return ("cyl", (n.X(), n.Y(), n.Z()), (p.X(), p.Y(), p.Z()), cy.Radius())
    return None


def _coincident(g1, g2, tol: float) -> bool:
    if g1 is None or g2 is None or g1[0] != g2[0]:
        return False
    d1, p1, d2, p2 = g1[1], g1[2], g2[1], g2[2]
    if abs(sum(a * b for a, b in zip(d1, d2))) < 1.0 - 1e-9:
        return False
    w = [b - a for a, b in zip(p1, p2)]
    if g1[0] == "plane":
        return abs(sum(a * b for a, b in zip(w, d1))) <= tol
    along = sum(a * b for a, b in zip(w, d1))
    perp = math.sqrt(max(sum(a * a for a in w) - along * along, 0.0))
    return abs(g1[3] - g2[3]) <= tol and perp <= tol


def _bbox_hit(a: cq.BoundBox, b: cq.BoundBox, tol: float) -> bool:
    return (a.xmin <= b.xmax + tol and b.xmin <= a.xmax + tol and a.ymin <= b.ymax + tol and b.ymin <= a.ymax + tol
            and a.zmin <= b.zmax + tol and b.zmin <= a.zmax + tol)


def contact_area(a: cq.Shape, b: cq.Shape, tol: float = P.THERMAL_CONTACT_TOL_MM) -> tuple:
    """(area, n_face_pairs, area_by_kind) of the surface two solids share: planar faces on the same plane and cylindrical faces on the same cylinder
    (within tol), intersected face by face."""
    fa = [(f, f.BoundingBox(), _face_geometry(f)) for f in a.Faces()]
    fb = [(f, f.BoundingBox(), _face_geometry(f)) for f in b.Faces()]
    total, n, kinds = 0.0, 0, {}
    for (f1, b1, g1), (f2, b2, g2) in itertools.product(fa, fb):
        if g1 is None or g2 is None or not _bbox_hit(b1, b2, tol) or not _coincident(g1, g2, tol):
            continue
        shared = f1.intersect(f2)
        area = sum(f.Area() for f in shared.Faces())
        if area > 1e-9:
            total += area
            n += 1
            kinds[g1[0]] = kinds.get(g1[0], 0.0) + area
    return total, n, kinds


def interference_report(bodies: dict) -> dict:
    """Pairwise: overlap volume (bounding-box overlapping pairs only) and the contact list (touching pairs and their shared area)."""
    names = list(bodies)
    bbs = {n: bodies[n].BoundingBox() for n in names}
    overlaps, contacts, near = {}, [], []
    for a, b in itertools.combinations(names, 2):
        if not _bbox_hit(bbs[a], bbs[b], BBOX_TOL):
            continue
        vol = bodies[a].intersect(bodies[b]).Volume()
        if vol > 0.0:
            overlaps[(a, b)] = vol
        dist = bodies[a].distance(bodies[b])
        if dist <= P.THERMAL_CONTACT_TOL_MM or vol > 0.0:
            area, n, kinds = contact_area(bodies[a], bodies[b])
            contacts.append({"a": a, "b": b, "area": area, "faces": n, "kinds": kinds, "overlap": vol, "distance": dist})
        elif dist < P.THERMAL_NEAR_GAP_MM:
            near.append({"a": a, "b": b, "gap": dist})
    return {"overlaps": overlaps, "contacts": contacts, "near": near, "max_overlap": max(overlaps.values(), default=0.0)}


# =============================================================================================================================
# findings that are not bodies of the export: the shell's fin slot, the screw lengths
# =============================================================================================================================
def shell_findings() -> dict:
    """Per fin thickness: overlap of the fin (and of the block motor) with the Shell_Casing, which Jasper owns and which is NOT edited here.
    y values are reported in the residual-free design frame (tab face y = 0).  `slot_open_to_y`: where the slot's motor-side wall has to move to
    (fin motor face - THERMAL_SLOT_CLEAR)."""
    shell = reference("Shell_Casing")
    dy = H.residual()[1]
    slot = measure_shell_slot()
    out = {"slot_y": (slot["y_motor_side"] - dy, slot["y_spool_side"] - dy), "slot_z": (slot["z_lo"], slot["z_hi"]), "top_z": measure_shell_top_z(), "variants": {}}
    holes = measure_slipin()["tab_holes"]
    for key, (t, model) in variants().items():
        ov = H.make_fin(t).intersect(shell)
        bb = ov.BoundingBox() if ov.Volume() > 0 else None
        motor = [motor_block(t, holes)] if model == "block" else list(build_station(key).values())[:len(P.NEMA17T_BODIES)]
        out["variants"][key] = {"t": t, "fin_shell_overlap": ov.Volume(), "overlap_y": None if bb is None else (bb.ymin - dy, bb.ymax - dy),
                                "motor_shell_overlap": sum(m.intersect(shell).Volume() for m in motor), "motor_shell_gap": min(m.distance(shell) for m in motor),
                                "slot_open_to_y": -(t + P.THERMAL_SLOT_CLEAR)}
    return out


def screw_findings() -> dict:
    """Thread engagement of real M3 screws behind each fin: screw length - tab - fin thickness (the tab face to the motor face stack)."""
    m = measure_slipin()
    tab = m["tab_back_y"] - m["tab_front_y"]
    rows = {}
    for key, length in (("fin1p8", 12.0), ("fin0p019 (M3 x 8)", 8.0), ("fin0p019 (M3 x 10)", 10.0)):
        t = P.FIN1021_T_PRODUCTION_MM if key.startswith("fin1p8") else P.FIN1021_T_PROTOTYPE_MM
        rows[key] = {"length": length, "stack": tab + t, "engagement": length - tab - t}
    return rows


# =============================================================================================================================
# export
# =============================================================================================================================
def export_station(key: str, step_dir: str = STEP_DIR, out_dir: str = RENDER_DIR) -> dict:
    t, model = variants()[key]
    bodies = build_station(key)
    path = N.export_named_step(to_assembly(bodies), os.path.join(step_dir, f"{_name(key)}.step"), assembly_name=_name(key), colors=_colors(bodies))
    rep = interference_report(bodies)
    os.makedirs(out_dir, exist_ok=True)
    rows = body_table(bodies, model)
    with open(os.path.join(out_dir, f"{_name(key)}_bodies.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "material to assign", "k W/m.K", "density g/cm3", "volume mm3", "mass g", "note"])
        for r in rows:
            w.writerow([r["name"], r["material"], r["k"], f"{r['density']:.3f}", f"{r['volume']:.3f}", f"{r['mass_g']:.3f}", r["note"]])
        w.writerow(["total", "", "", "", f"{sum(r['volume'] for r in rows):.3f}", f"{sum(r['mass_g'] for r in rows):.3f}", ""])
    with open(os.path.join(out_dir, f"{_name(key)}_contacts.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["body A", "body B", "contact area mm2", "face pairs", "planar mm2", "cylindrical mm2", "overlap mm3", "distance mm"])
        for c in sorted(rep["contacts"], key=lambda c: -c["area"]):
            w.writerow([c["a"], c["b"], f"{c['area']:.3f}", c["faces"], f"{c['kinds'].get('plane', 0.0):.3f}", f"{c['kinds'].get('cyl', 0.0):.3f}",
                        f"{c['overlap']:.6f}", f"{c['distance']:.2e}"])
        w.writerow([])
        w.writerow(["near gaps (not touching)", "body B", "gap mm"])
        for c in sorted(rep["near"], key=lambda c: c["gap"]):
            w.writerow([c["a"], c["b"], f"{c['gap']:.4f}"])
    return {"step": path, "bodies": rows, "report": rep}


def _colors(bodies: dict) -> dict:
    pal = {"motor_block": (0.40, 0.42, 0.48), "fin_in": (0.80, 0.82, 0.88), "fin_out": (0.62, 0.66, 0.74), "slipin_mount": (0.85, 0.75, 0.55)}
    out = dict(N.COLORS)
    out.update(pal)
    for n in bodies:
        if n.startswith("screw"):
            out[n] = (0.15, 0.15, 0.18)
        elif n.startswith("insert"):
            out[n] = (0.85, 0.65, 0.13)
    return out


def render_sections(key: str, out_dir: str = RENDER_DIR) -> list:
    """Section through two screws (plane z = the upper screw row, seen from +z) and through the deck insert (plane y = pocket centre, seen from +y)."""
    from .parts import encoder1021 as E
    os.makedirs(out_dir, exist_ok=True)
    bodies = build_station(key)
    m = measure_slipin()
    col = _colors(bodies)
    z_row = max(h[1] for h in m["tab_holes"])

    def keep(sh, **b):
        box = cq.Workplane("XY").box(b["x1"] - b["x0"], b["y1"] - b["y0"], b["z1"] - b["z0"], centered=False).translate((b["x0"], b["y0"], b["z0"])).val()
        r = sh.intersect(box)
        return r if r.Volume() > 0 else None

    paths = []
    win = dict(x0=-30.0, x1=30.0, y0=-50.0, y1=12.0, z0=z_row - 40.0, z1=z_row)
    items = []
    for n, sh in bodies.items():
        if n.startswith("insert"):
            continue
        k = keep(sh, **win)
        if k is not None:
            items.append((k, col.get(n, (0.7, 0.7, 0.7)), 0.9 if n == "slipin_mount" else 1.0, 0.03))
    p = os.path.join(out_dir, f"{_name(key)}_section_screws.png")
    E.render_scene(items, p, ((0, 0, 1), (0, 1, 0)), f"{_name(key)}: section through the upper screw row, z = {z_row:.2f}, seen from +z",
                   px=900, bounds=((-30, -48, z_row - 2), (30, 12, z_row)), note="+x right, +y up: spool side (head on the tab) at the top; motor, fin, tab, screws with their holes; station_1021 frame")
    paths.append(p)
    if "insert_deck" in bodies:
        d = m["deck"]
        y_c = d["xy"][1]
        win = dict(x0=d["xy"][0] - 14, x1=d["xy"][0] + 14, y0=y_c - 20.0, y1=y_c, z0=d["z_bottom"] - 4, z1=d["z_top"] + 6)
        items = []
        for n in ("slipin_mount", "insert_deck"):
            k = keep(bodies[n], **win)
            if k is not None:
                items.append((k, col[n], 1.0, 0.03))
        p = os.path.join(out_dir, f"{_name(key)}_section_deck_insert.png")
        E.render_scene(items, p, ((0, 1, 0), (0, 0, 1)), f"{_name(key)}: section through the deck insert (candidate), plane y = {y_c:.2f}, seen from +y",
                       px=900, bounds=((win["x0"], y_c - 1.0, win["z0"]), (win["x1"], y_c, win["z1"])), note="-x right (camera at +y), +z up: brass sleeve Ø4.1 x 5.7, flush with the deck face, pocket 7 deep")
        paths.append(p)
    return paths


def main(keys=None) -> None:
    for key in (keys or [k for k, _, _ in P.THERMAL_VARIANTS]):
        t, model = variants()[key]
        res = export_station(key)
        rep = res["report"]
        print(f"\n== {key}: fin t {t:.3f}, motor model {model}  ->  {res['step']}")
        for r in res["bodies"]:
            print(f"  {r['name']:<14} V {r['volume']:11.3f} mm3  m {r['mass_g']:8.3f} g  {r['material']}")
        print(f"  max overlap {rep['max_overlap']:.6f} mm3  (limit {P.THERMAL_OVERLAP_LIMIT_MM3}); overlapping pairs: {rep['overlaps']}")
        for c in sorted(rep["contacts"], key=lambda c: -c["area"]):
            print(f"  contact {c['a']:<12} - {c['b']:<12} {c['area']:9.3f} mm2  ({c['faces']} face pairs)")
        for c in sorted(rep["near"], key=lambda c: c["gap"]):
            print(f"  near    {c['a']:<12} - {c['b']:<12} gap {c['gap']:.4f} mm")
        for p in render_sections(key):
            print("  render", p)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
