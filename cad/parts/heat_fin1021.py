"""
HEAT FIN 1021 -- aluminium heat-spreader fin of the 10/21 station, 1/8 in production plate and the 0.019 in prototype record.

Spec: cad/HEAT_FIN_1021_SPEC.md.  Master values: cad/params.py, blocks FIN1021_* (and THERMAL_* for cad/thermal_station1021.py).
Build notes / measured results: verification/heat_fin1021_build_notes.md.  Tests: tests/test_heat_fin1021.py.

The outline and the five holes are NOT redrawn.  The fin is the y = 0 face of Jasper's Heat_horn (cad/reference/station_1021/Heat_horn.step)
extruded toward -y by the thickness t, so the plan outline equals his CAD by construction:
    production  t = 3.175 mm (1/8 in)      prototype record  t = 0.483 mm (0.019 in, sheet already in stock; cannot carry 4.05 W alone)
Heat_horn: 42.0 mm bottom edge, 195.6 mm left and 228.6 mm right (long) side edges, 53.4 mm slanted top edge; Ø22.5 centre hole on the motor
axis and 4 x Ø3.4 on a 31 mm square.

Frames
    station_1021   the reference STEP frame: motor axis x = 0, z = +2.64; +y toward the spool (PETG tab face y = 0, fin at y = -t .. 0);
                   +x out of the wall; +z up.  Carries the extraction residual ENC1021_REF_RESIDUAL (0.004 mm).
    assembly       station_1021 + O (cad/reference/station_1021/extract.py): the fin drops into Assem_laundry_v3_step_1021 at the origin.
    flat part      plate in XY, thickness +Z, origin at the bottom-left corner of the 42 mm edge seen from the motor side
                   (X = x - X_MIN, Y = z - Z_MIN, Z = -y: Z = 0 is the PETG-tab face, Z = t the motor contact face).  Residual removed.

    /usr/bin/python3 -m cad.parts.heat_fin1021        (exports, DXF, drawing, renders; about 1 minute)
"""

from __future__ import annotations

import functools
import math
import os

import cadquery as cq

from .. import params as P
from ..reference.station_1021.extract import O as ASM_ORIGIN

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STEP_DIR = os.path.join(_REPO, "exports", "step")
STL_DIR = os.path.join(_REPO, "exports", "stl")
DXF_DIR = os.path.join(_REPO, "exports", "dxf")
RENDER_DIR = os.path.join(_REPO, "renders", "heat_fin1021")
REF_DIR = os.path.join(_REPO, "cad", "reference", "station_1021")
HORN_STEP = os.path.join(REF_DIR, "Heat_horn.step")

# export key -> thickness (mm).  "1p8" = production 1/8 in, "0p019" = prototype record
VARIANTS = {"1p8": P.FIN1021_T_PRODUCTION_MM, "0p019": P.FIN1021_T_PROTOTYPE_MM}
PRODUCTION = "1p8"

# drawing sheet: A3 portrait at true 1:1 (the part is 228.6 mm tall).  Tolerances copied from the 10/18 drawing (motor_heat_plate.py).
SHEET_W, SHEET_H, SHEET_BORDER = 297.0, 420.0, 10.0
TOL_HOLE_REL = 0.1       # hole positions relative to each other, mm
TOL_OUTLINE = 0.5        # sheared / sawn outline, mm
INK, MUTED, CL, WARN = "#111111", "#555555", "#1f5fbf", "#b00020"


def _name(key: str) -> str:
    return f"heat_fin1021_{key}"


# =============================================================================================================================
# the reference
# =============================================================================================================================
@functools.lru_cache(maxsize=None)
def reference_horn() -> cq.Shape:
    """Jasper's Heat_horn, as extracted (station_1021 frame, residual included)."""
    return cq.importers.importStep(HORN_STEP).val()


@functools.lru_cache(maxsize=None)
def reference_face() -> cq.Face:
    """The Heat_horn's y = 0 face (normal +y, the PETG-tab side), outline plus the 5 holes."""
    faces = [f for f in reference_horn().Faces() if f.geomType() == "PLANE" and f.normalAt().y > 0.999]
    assert len(faces) == 1, f"expected one +y planar face on the Heat_horn, found {len(faces)}"
    return faces[0]


def residual() -> tuple:
    """Extraction residual (x, y, z) of the station_1021 files, mm (parameter ENC1021_REF_RESIDUAL)."""
    return tuple(P.ENC1021_REF_RESIDUAL)


def design_offset() -> cq.Vector:
    """Vector that takes a station_1021 point to the residual-free design frame."""
    dx, dy, dz = residual()
    return cq.Vector(-dx, -dy, -dz)


# =============================================================================================================================
# the fin
# =============================================================================================================================
def make_fin(t_mm: float = P.FIN1021_T_PRODUCTION_MM) -> cq.Solid:
    """Fin of thickness `t_mm` in the station_1021 frame: the Heat_horn's y = 0 face extruded toward -y (face at y = +0.0016, back at -t)."""
    assert t_mm > 0.0, "fin thickness must be positive"
    face = reference_face()
    solid = cq.Solid.extrudeLinear(face.outerWire(), face.innerWires(), cq.Vector(0.0, -t_mm, 0.0))
    assert solid.isValid() and solid.Volume() > 0.0
    return solid


def to_assembly(shape: cq.Shape) -> cq.Shape:
    """station_1021 -> assembly coordinates of Assem_laundry_v3_step_1021 (+ O)."""
    return shape.translate(cq.Vector(*ASM_ORIGIN))


def to_flat(shape: cq.Shape) -> cq.Shape:
    """station_1021 -> flat part frame (see module docstring): residual removed, rotated so z -> Y and -y -> Z, bottom-left corner at the origin."""
    s = shape.translate(design_offset())
    s = s.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), -90.0)       # (x, y, z) -> (x, z, -y)
    return s.translate(cq.Vector(-P.FIN1021_X_MIN, -P.FIN1021_Z_MIN, 0.0))


def make_fin_asm(t_mm: float = P.FIN1021_T_PRODUCTION_MM) -> cq.Solid:
    return to_assembly(make_fin(t_mm))


def make_fin_flat(t_mm: float = P.FIN1021_T_PRODUCTION_MM) -> cq.Solid:
    return to_flat(make_fin(t_mm))


def fin_mass_g(solid: cq.Shape) -> float:
    return solid.Volume() * P.FIN1021_AL_G_CM3 / 1000.0


# =============================================================================================================================
# measuring the reference (record + tests): everything below is read from the Heat_horn face, residual removed
# =============================================================================================================================
def measure_outline() -> dict:
    """Outline and holes of the Heat_horn y = 0 face in the design station_1021 frame (residual removed)."""
    face = reference_face()
    dx, _, dz = residual()
    edges = face.outerWire().Edges()
    lengths = sorted(e.Length() for e in edges)
    pts = [(v.X - dx, v.Z - dz) for v in face.outerWire().Vertices()]
    xs, zs = [p[0] for p in pts], [p[1] for p in pts]
    holes = []
    for w in face.innerWires():
        f = cq.Face.makeFromWires(w)
        c = f.Center()
        holes.append((c.x - dx, c.z - dz, 2.0 * math.sqrt(f.Area() / math.pi)))
    return {"area": face.Area(), "edge_lengths": lengths, "x_min": min(xs), "x_max": max(xs), "z_min": min(zs), "z_max": max(zs),
            "holes": sorted(holes, key=lambda h: (-h[2], h[1], h[0])), "corners": pts}


def hole_table() -> list:
    """Hole table in the flat frame for the shop drawing and the DXF: (id, diameter, X from the left edge, X from the long-side edge B,
    Y from the bottom edge A), all mm.  1 = the motor pilot, 2..5 = the M3 clearance holes (lower left, lower right, upper left, upper right)."""
    h = measure_outline()["holes"]
    pilot = [x for x in h if x[2] > 10.0]
    small = sorted((x for x in h if x[2] < 10.0), key=lambda x: (x[1], x[0]))
    rows = []
    width = P.FIN1021_X_MAX - P.FIN1021_X_MIN
    for i, (x, z, d) in enumerate(pilot + small, start=1):
        X, Y = x - P.FIN1021_X_MIN, z - P.FIN1021_Z_MIN
        rows.append((i, d, X, width - X, Y))
    return rows


# =============================================================================================================================
# exports
# =============================================================================================================================
def export_step(shape: cq.Shape, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cq.exporters.export(cq.Workplane("XY").add(shape), path)
    return path


def export_stl(shape: cq.Shape, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cq.exporters.export(cq.Workplane("XY").add(shape), path, tolerance=0.02, angularTolerance=0.1)
    return path


def export_asm_steps(step_dir: str = STEP_DIR) -> dict:
    """heat_fin1021_<key>_asm1021.step for both thicknesses, assembly coordinates."""
    return {k: export_step(make_fin_asm(t), os.path.join(step_dir, f"{_name(k)}_asm1021.step")) for k, t in VARIANTS.items()}


def export_flat(step_dir: str = STEP_DIR, stl_dir: str = STL_DIR) -> dict:
    """Flat part frame STEP + STL of the production fin (heat_fin1021_1p8.*)."""
    flat = make_fin_flat(VARIANTS[PRODUCTION])
    return {"step": export_step(flat, os.path.join(step_dir, f"{_name(PRODUCTION)}.step")),
            "stl": export_stl(flat, os.path.join(stl_dir, f"{_name(PRODUCTION)}.stl"))}


def write_dxf(path: str = os.path.join(DXF_DIR, f"{_name(PRODUCTION)}_profile.dxf")) -> str:
    """2D outline + holes in the flat frame (mm) for cutting and drilling: layer OUTLINE (closed polyline), HOLES (circles), CENTER (crosses)."""
    import ezdxf
    flat = make_fin_flat(VARIANTS[PRODUCTION])
    face = [f for f in flat.Faces() if f.geomType() == "PLANE" and abs(f.normalAt().z + 1.0) < 1e-9][0]        # Z = 0 face, outward normal -Z
    corners = [(v.X, v.Y) for v in face.outerWire().Vertices()]
    cx = sum(p[0] for p in corners) / len(corners)
    cy = sum(p[1] for p in corners) / len(corners)
    corners.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))                                          # convex outline: angular order
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.layers.add("OUTLINE", color=7)
    doc.layers.add("HOLES", color=1)
    doc.layers.add("CENTER", color=5)
    msp = doc.modelspace()
    msp.add_lwpolyline([(round(x, 4), round(y, 4)) for x, y in corners], close=True, dxfattribs={"layer": "OUTLINE"})
    for _, d, X, _, Y in hole_table():
        msp.add_circle((round(X, 4), round(Y, 4)), round(d / 2.0, 4), dxfattribs={"layer": "HOLES"})
        ext = d / 2.0 + 2.0
        msp.add_line((X - ext, Y), (X + ext, Y), dxfattribs={"layer": "CENTER"})
        msp.add_line((X, Y - ext), (X, Y + ext), dxfattribs={"layer": "CENTER"})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc.saveas(path)
    return path


# =============================================================================================================================
# shop drawing (A3 portrait, 1:1): dimensions in mm [inch], hole table from the mill datums A (bottom edge) and B (long side edge)
# =============================================================================================================================
def _mmin(mm: float, nd_mm: int = 2, nd_in: int = 3) -> str:
    return f"{mm:.{nd_mm}f} [{mm / P.FIN1021_MM_PER_IN:.{nd_in}f}]"


def shop_drawing(path_png: str, path_pdf: str, t_mm: float = P.FIN1021_T_PRODUCTION_MM) -> tuple:
    """Dimensioned drawing of the flat fin.  View: from the motor side (the unpainted contact square is on this face); datum A = bottom edge,
    datum B = the 228.6 mm long side (right edge)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon, Rectangle

    W = P.FIN1021_X_MAX - P.FIN1021_X_MIN
    HL, HR = P.FIN1021_H_LEFT, P.FIN1021_H_RIGHT
    rows = hole_table()
    ox, oy = 76.0, 52.0                                    # sheet position of the flat-frame origin (bottom-left corner of the plate)
    fig = plt.figure(figsize=(SHEET_W / 25.4, SHEET_H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, SHEET_W)
    ax.set_ylim(0, SHEET_H)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((SHEET_BORDER, SHEET_BORDER), SHEET_W - 2 * SHEET_BORDER, SHEET_H - 2 * SHEET_BORDER, fill=False, ec=INK, lw=1.0))
    S = lambda X, Y: (ox + X, oy + Y)

    # ---- outline, holes, centre marks
    outline = [S(0, 0), S(W, 0), S(W, HR), S(0, HL)]
    ax.add_patch(Polygon(outline, closed=True, fc="#eef3fa", ec=INK, lw=1.4))
    # unpainted motor contact square (flange 42.3 square about the axis, clipped to the plate)
    ax_X, ax_Y = P.FIN1021_AXIS_XZ[0] - P.FIN1021_X_MIN, P.FIN1021_AXIS_XZ[1] - P.FIN1021_Z_MIN
    half = P.FIN1021_CONTACT_SQ / 2
    cx0, cx1 = max(ax_X - half, 0.0), min(ax_X + half, W)
    cy0, cy1 = max(ax_Y - half, 0.0), ax_Y + half
    ax.add_patch(Rectangle(S(cx0, cy0), cx1 - cx0, cy1 - cy0, fill=False, ec=CL, lw=0.7, ls="--"))
    for _, d, X, _, Y in rows:
        ax.add_patch(Circle(S(X, Y), d / 2, fc="white", ec=INK, lw=1.0))
        ext = d / 2 + 2.5
        ax.plot([S(X, Y)[0] - ext, S(X, Y)[0] + ext], [S(X, Y)[1]] * 2, color=CL, lw=0.35, ls=(0, (6, 2, 1, 2)))
        ax.plot([S(X, Y)[0]] * 2, [S(X, Y)[1] - ext, S(X, Y)[1] + ext], color=CL, lw=0.35, ls=(0, (6, 2, 1, 2)))
    for i, d, X, _, Y in rows:                              # hole ids
        dy = 0.0 if i == 1 else (-4.3 if Y > ax_Y else 4.3)                      # inward in Y: clear of the Ø22.5 pilot (holes are 15.5 from the axis in X)
        ax.text(*S(X, Y + dy), str(i), ha="center", va="center", fontsize=7.5, color=INK, weight="bold")

    def arrow(p, q, lw=0.6):
        ax.annotate("", q, p, arrowprops=dict(arrowstyle="<|-|>", color=INK, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=6))

    # ---- horizontal baseline dimensions from datum B (right edge), below the plate
    xs_from_b = sorted({0.0, rows[0][3], rows[1][3], rows[2][3], W})
    xs_from_b = [v for v in xs_from_b if v > 1e-6]
    for k, dist in enumerate(xs_from_b):
        yv = oy - 7.0 - 6.5 * k
        xb = ox + W                                          # datum B on the sheet
        ax.plot([xb, xb], [oy - 1, yv - 1.5], color=MUTED, lw=0.35)
        ax.plot([xb - dist] * 2, [oy - 1 if dist >= W - 1e-6 else S(0, 0)[1] + rows[0][4] - 5.0, yv - 1.5], color=MUTED, lw=0.35)
        arrow((xb, yv), (xb - dist, yv))
        ax.text(xb - dist / 2, yv + 0.8, _mmin(dist), ha="center", va="bottom", fontsize=6.8, color=INK)
    # ---- vertical baseline dimensions from datum A (bottom edge), left of the plate
    ys_from_a = sorted({rows[1][4], rows[0][4], rows[3][4], HL, HR})
    for k, dist in enumerate(ys_from_a):
        xv = ox - 8.0 - 8.0 * k
        ax.plot([ox - 1, xv - 1.5], [oy, oy], color=MUTED, lw=0.35)
        top_x = ox + W if dist >= HR - 1e-6 else (ox if dist >= HL - 1e-6 else S(rows[1][2] - 3.0, 0)[0])
        ax.plot([top_x, xv - 1.5], [oy + dist] * 2, color=MUTED, lw=0.35)
        arrow((xv, oy), (xv, oy + dist))
        ax.text(xv - 0.8, oy + (dist / 2 if dist > 40 else dist + 1.5), _mmin(dist), rotation=90, ha="right", va="center" if dist > 40 else "bottom",
                fontsize=6.8, color=INK)
    # slanted top edge (reference)
    mid = ((outline[2][0] + outline[3][0]) / 2, (outline[2][1] + outline[3][1]) / 2)
    ax.annotate(f"{_mmin(P.FIN1021_TOP_EDGE_MM, 1, 3)} slanted top edge (REF)\n{_mmin(HR - HL, 1, 3)} rise", mid, (ox + W + 8, oy + HR - 20), fontsize=6.8, color=INK,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.4))

    # ---- callouts, datums
    lx = ox + W + 16.0
    ax.annotate(f"Ø{_mmin(rows[0][1], 1, 3)} THRU (1)\nmotor boss Ø22 + clearance", S(rows[0][2] + rows[0][1] / 2 * 0.707, rows[0][4] + rows[0][1] / 2 * 0.707),
                (lx, S(0, rows[0][4])[1] + 34), fontsize=6.8, color=INK, va="center", arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.6, mutation_scale=6))
    r = rows[4]
    ax.annotate(f"4X Ø{_mmin(r[1], 1, 3)} THRU (2-5)\nM3 clearance, NEMA 17, {P.FIN1021_HOLE_SQ:.0f} sq.", S(r[2] + r[1] / 2 * 0.707, r[4] + r[1] / 2 * 0.707),
                (lx, S(0, r[4])[1] + 56), fontsize=6.8, color=INK, va="center", arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.6, mutation_scale=6))
    ax.annotate(f"MOTOR CONTACT {P.FIN1021_CONTACT_SQ:.1f} SQ.\nleave BARE (thermal paste)", S(cx1, cy0 + 12), (lx, oy + 22.0), fontsize=6.4, color=CL, va="center",
                arrowprops=dict(arrowstyle="-", color=CL, lw=0.4))
    for lab, (px, py) in (("A", (ox + W * 0.5, oy)), ("B", (ox + W, oy + HR * 0.5))):
        ax.add_patch(Rectangle((px - 2.6, py - 2.6), 5.2, 5.2, fc="white", ec=INK, lw=0.7, zorder=5))
        ax.text(px, py, lab, ha="center", va="center", fontsize=7, weight="bold", color=INK, zorder=6)
    ax.text(S(W + 3, HR * 0.5 + 6)[0], S(W + 3, HR * 0.5 + 6)[1], "DATUM B\n= long side", fontsize=6.2, color=MUTED, va="bottom")
    ax.text(S(W / 2, HR + 6)[0], S(W / 2, HR + 6)[1], "FRONT VIEW from the motor side  1:1", ha="center", fontsize=8, weight="bold", color=INK)
    ax.text(S(W / 2, 150)[0], S(W / 2, 150)[1], "FIN\n(cooling area)\nmatte black", ha="center", va="center", fontsize=8, color=MUTED)

    # ---- edge view (thickness): right margin, clear of the notes and the title block
    ex, ey0 = 272.0, 76.0
    tw = max(t_mm, 1.0)
    ax.add_patch(Rectangle((ex, ey0), tw, HR, fc="#eef3fa", ec=INK, lw=1.0))
    yt = ey0 + HR * 0.40
    for x0, x1 in ((ex - 6, ex), (ex + tw + 6, ex + tw)):
        ax.annotate("", (x1, yt), (x0, yt), arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.6, mutation_scale=6))
    ax.text(ex - 7, yt, f"{_mmin(t_mm, 3, 3)}\n1/8 in PLATE", ha="right", va="center", fontsize=6.8, color=INK)
    ax.text(ex + tw / 2, ey0 + HR + 3, "EDGE VIEW 1:1", ha="center", fontsize=7, weight="bold", color=INK)

    # ---- hole table
    tx, ty, rh = 152.0, 392.0, 6.4
    heads = ["ID", "Ø mm [in]", "X from B", "X from left", "Y from A"]
    colx = [tx + 2, tx + 12, tx + 46, tx + 78, tx + 108]
    ax.add_patch(Rectangle((tx, ty - rh * (len(rows) + 1)), 132.0, rh * (len(rows) + 1), fill=False, ec=INK, lw=0.8))
    ax.text(tx + 2, ty + 2, "HOLE TABLE  (mm [inch])  - mill setup: datum A = bottom edge, datum B = long side (228.6 mm edge)", fontsize=6.8, weight="bold", color=INK)
    for cxx, h in zip(colx, heads):
        ax.text(cxx, ty - rh / 2, h, fontsize=6.4, color=MUTED, va="center", weight="bold")
    for i, (idn, d, X, XB, Y) in enumerate(rows, start=1):
        yy = ty - rh * i
        ax.plot([tx, tx + 132.0], [yy, yy], color=INK, lw=0.3)
        vals = [str(idn), _mmin(d, 1, 3), _mmin(XB), _mmin(X), _mmin(Y)]
        for cxx, v in zip(colx, vals):
            ax.text(cxx, yy - rh / 2, v, fontsize=6.4, color=INK, va="center", family="monospace")

    # ---- notes
    vol = make_fin(t_mm).Volume()
    mass = vol * P.FIN1021_AL_G_CM3 / 1000.0
    notes = ["NOTES",
             f"1. MATERIAL: {P.FIN1021_ALLOY.upper()} ({t_mm:.3f} mm).",
             f"2. FINISH: {P.FIN1021_FINISH.upper()}",
             f"   (the {P.FIN1021_CONTACT_SQ:.1f} mm square contact area: bare, thermal paste).",
             f"3. ALL HOLES THRU, ±{TOL_HOLE_REL} RELATIVE TO EACH OTHER; DRILL ALL 5",
             "   IN ONE SETUP FROM DATUMS A AND B. OUTLINE ±" + f"{TOL_OUTLINE}, SHEARED OR SAWN.",
             "4. BREAK ALL EDGES, DEBURR BOTH FACES; MOTOR FACE FLAT, NO BURRS.",
             "5. OUTLINE AND HOLES = Heat_horn of Assem_laundry_v3_step_1021",
             "   (cad/reference/station_1021/Heat_horn.step); thickness changed only.",
             "6. STACK: MOTOR | FIN | 5 mm PETG TAB, M3 x 12 SCREWS FROM THE",
             f"   SPOOL SIDE. MOTOR + SHAFT SIT {abs(t_mm - P.FIN1021_REF_T):.3f} mm {'AWAY FROM' if t_mm > P.FIN1021_REF_T else 'TOWARD'} THE SPOOL",
             f"   vs the {P.FIN1021_REF_T:.1f} mm CAD fin.",
             f"7. MASS {mass:.1f} g ({mass / 453.592:.3f} lb) EACH, VOLUME {vol:.0f} mm3.",
             f"8. PROTOTYPE ONLY: {P.FIN1021_T_PROTOTYPE_IN} in ({P.FIN1021_T_PROTOTYPE_MM} mm) SHEET,",
             "   SAME OUTLINE (heat_fin1021_0p019_asm1021.step)."]
    for i, n in enumerate(notes):
        ax.text(152.0, 344.0 - 4.9 * i, n, fontsize=6.0, color=INK, family="monospace", weight="bold" if i == 0 else "normal")

    # ---- title block
    tb = [("PART", "HEAT FIN 1021  (heat_fin1021)"), ("PROJECT", "RoomCleaner winch station, 10/21 assembly"),
          ("MATERIAL", f"{P.FIN1021_ALLOY}"), ("FINISH", "matte black paint, motor square bare"),
          ("UNITS", "mm [inch]"), ("SCALE", "1:1 on A3 (print at 100 %)"), ("GENERAL TOL.", f"outline ±{TOL_OUTLINE}, holes ±{TOL_HOLE_REL} rel."),
          ("REV", "A   2026-10-22"), ("SOURCE", "cad/parts/heat_fin1021.py")]
    bx, by, bw, brh = 152.0, 14.0, 132.0, 6.0
    ax.add_patch(Rectangle((bx, by), bw, brh * len(tb), fill=False, ec=INK, lw=0.8))
    for i, (k, v) in enumerate(tb):
        yy = by + brh * (len(tb) - 1 - i)
        ax.plot([bx, bx + bw], [yy, yy], color=INK, lw=0.3)
        ax.text(bx + 2, yy + brh / 2, k, fontsize=5.8, color=MUTED, va="center")
        ax.text(bx + 28, yy + brh / 2, v, fontsize=6.6, color=INK, va="center")
    ax.plot([bx + 26] * 2, [by, by + brh * len(tb)], color=INK, lw=0.3)
    # scale bar
    ax.plot([16, 116], [20, 20], color=INK, lw=1.0)
    for xv in (16, 66, 116):
        ax.plot([xv, xv], [18.5, 21.5], color=INK, lw=0.8)
    ax.text(66, 22.5, "SCALE CHECK: this bar must measure 100 mm", ha="center", fontsize=6.2, color=INK)

    os.makedirs(os.path.dirname(path_png), exist_ok=True)
    fig.savefig(path_pdf, facecolor="white")
    fig.savefig(path_png, facecolor="white", dpi=150)
    plt.close(fig)
    return path_png, path_pdf


# =============================================================================================================================
# renders (the standard 7 views of the station frame, shared with the encoder renderer) + a detail of the hole end
# =============================================================================================================================
def render_all(out_dir: str = RENDER_DIR, key: str = PRODUCTION) -> list:
    from . import encoder1021 as E
    os.makedirs(out_dir, exist_ok=True)
    fin = make_fin(VARIANTS[key])
    paths = E.render_part(fin, _name(key), (0.62, 0.67, 0.76), out_dir)
    bb = fin.BoundingBox()
    lo, hi = (bb.xmin - 2.0, bb.ymin - 8.0, P.FIN1021_Z_MIN - 4.0), (bb.xmax + 2.0, bb.ymax + 8.0, 34.0)
    p = os.path.join(out_dir, f"{_name(key)}_detail_holes.png")
    E.render_scene([(fin, (0.62, 0.67, 0.76), 1.0, 0.02)], p, ((0.55, -0.62, 0.56), (0, 0, 1)),
                   f"{_name(key)}: hole end (iso from the motor side), t = {VARIANTS[key]:.3f} mm", px=760, bounds=(lo, hi),
                   note="station_1021 frame: motor axis at x = 0, z = 2.64; centre hole Ø22.5, 4 x Ø3.4 on a 31 mm square")
    paths.append(p)
    return paths


def summary() -> dict:
    out = {}
    for k, t in VARIANTS.items():
        s = make_fin(t)
        bb = s.BoundingBox()
        out[k] = {"t": t, "valid": s.isValid(), "solids": len(s.Solids()), "volume": s.Volume(), "mass_g": fin_mass_g(s),
                  "bbox": (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)}
    return out


def main() -> None:
    for k, d in summary().items():
        bb = d["bbox"]
        print(f"fin {k}: t {d['t']:.3f} valid={d['valid']} solids={d['solids']} vol={d['volume']:.2f} mm3 mass={d['mass_g']:.2f} g "
              f"bbox station x[{bb[0]:.4f},{bb[1]:.4f}] y[{bb[2]:.4f},{bb[3]:.4f}] z[{bb[4]:.4f},{bb[5]:.4f}]")
    for k, p in export_asm_steps().items():
        print("asm1021", k, p)
    flat = export_flat()
    fb = make_fin_flat(VARIANTS[PRODUCTION]).BoundingBox()
    print(f"flat frame bbox X[{fb.xmin:.4f},{fb.xmax:.4f}] Y[{fb.ymin:.4f},{fb.ymax:.4f}] Z[{fb.zmin:.4f},{fb.zmax:.4f}]", flat)
    print("dxf", write_dxf())
    print("drawing", shop_drawing(os.path.join(RENDER_DIR, f"{_name(PRODUCTION)}_drawing.png"), os.path.join(RENDER_DIR, f"{_name(PRODUCTION)}_drawing.pdf")))
    print(len(render_all()), "renders ->", RENDER_DIR)


if __name__ == "__main__":
    main()
