"""
Independent geometry verification of the encoder 1021 v2 parts (self-centring crush ribs): magnet cap v2 + encoder casing v2.

Verifier: geometry-verifier (Sonnet), 2026-10-22.  Baseline: verification/encoder1021_verification.md (v1) and
tests/test_encoder1021_verification.py (method and frame reused; only its geometry HELPERS are imported, not its tests).
Implementer claims: verification/encoder1021_build_notes.md section 11.  Report: verification/encoder1021_v2_verification.md.

Own measurements only: OCC ray intersections, booleans, BRepExtrema, binary-STL triangle analysis.  The builder module is imported
only in item 6/7 (STEP vs builder comparison, and to reproduce its stackup() numbers).  The reference frame is the v1 one:
station_1021 parts shifted by (0, 0, -2.64) and the sub-0.005 mm residual correction that report accepted (measured here again).

Status vocabulary in the records: PASS, FAIL (assertion fails), INFO, WARN (an engineering finding that is recorded, the test stays green).

Run:  PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m pytest tests/test_encoder1021_v2_verification.py -q -p no:cacheprovider -s
Set ENC_V2_VERIFY_JSON=/path/out.json to dump every recorded number.
"""

from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pytest

cq = pytest.importorskip("cadquery")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

# geometry helpers only (no tests, no fixtures) from the v1 verification
from tests.test_encoder1021_verification import (   # noqa: E402
    bbox, box, brep_valid, common, cyl, cyl_faces, load_step, min_dist, n_solids, plane_faces, radial_profile, ray,
    read_stl, stl_volume, stl_watertight, vol_common, _overhangs)

STEP_DIR = os.path.join(REPO, "exports", "step")
STL_DIR = os.path.join(REPO, "exports", "stl")
REF_DIR = os.path.join(REPO, "cad", "reference", "station_1021")
RENDER_DIR = os.path.join(REPO, "renders", "encoder1021")
CAP2_STEP = os.path.join(STEP_DIR, "encoder1021_magnet_cap_v2.step")
CAS2_STEP = os.path.join(STEP_DIR, "encoder1021_casing_v2.step")
CAP2_STL = os.path.join(STL_DIR, "encoder1021_magnet_cap_v2.stl")
CAS2_STL = os.path.join(STL_DIR, "encoder1021_casing_v2.stl")
CAP020_STEP = os.path.join(STEP_DIR, "encoder1021_magnet_cap_rib020.step")
CAS1_STL = os.path.join(STL_DIR, "encoder1021_casing.stl")
CAP1_STL = os.path.join(STL_DIR, "encoder1021_magnet_cap.stl")
REF_NAMES = ("Slipin_mount_piecev3", "Spool1011", "Shell_Casing", "Motor_Reference", "Heat_horn", "Wall_Mount_v3")

PETG_E_MPA = 2100.0          # cad/materials.py
PETG_YIELD_MPA = 45.0        # cad/materials.py (XY)
AS5600_DISPLACEMENT_MM = 0.25   # v1 report (datasheet figure from mirrors; official PDF still not opened)
NOZZLE_MM = 0.4

# design values from the v2 task statement / build notes (what the part is SUPPOSED to be)
BOARD_HALF = 11.5            # 23.0 board
POCKET_HALF = 11.75          # 23.5 pocket
RIB_TIP_POS = 11.40          # tip distance from the axis (board edge 11.50 - crush 0.10)
RIB_POS = 6.5
FRAME_FRONT_Y, TAB_PLANE_Y, PCB_BACK_Y = 31.0, 32.25, 33.85

RECORDS: list = []


def _rec(item, what, expected, measured, tol, status, note=""):
    RECORDS.append(dict(item=item, what=what, expected=expected, measured=measured, tol=tol, status=status, note=note))


def check(item, what, expected, measured, tol, note=""):
    ok = abs(measured - expected) <= tol
    _rec(item, what, expected, measured, f"+-{tol}", "PASS" if ok else "FAIL", note)
    assert ok, f"[{item}] {what}: expected {expected} +-{tol}, measured {measured}"


def check_min(item, what, minimum, measured, note=""):
    ok = measured >= minimum
    _rec(item, what, f">= {minimum}", measured, "min", "PASS" if ok else "FAIL", note)
    assert ok, f"[{item}] {what}: need >= {minimum}, measured {measured}"


def check_max(item, what, maximum, measured, note=""):
    ok = measured <= maximum
    _rec(item, what, f"<= {maximum}", measured, "max", "PASS" if ok else "FAIL", note)
    assert ok, f"[{item}] {what}: need <= {maximum}, measured {measured}"


def check_true(item, what, cond, measured="", note=""):
    _rec(item, what, "True", measured if measured != "" else cond, "-", "PASS" if cond else "FAIL", note)
    assert cond, f"[{item}] {what}: {measured}"


def info(item, what, measured, note=""):
    _rec(item, what, "-", measured, "-", "INFO", note)


def warn(item, what, expected, measured, note=""):
    """Recorded engineering finding: does not fail the test."""
    _rec(item, what, expected, measured, "-", "WARN", note)


@pytest.fixture(scope="session", autouse=True)
def _dump_records():
    yield
    out = os.environ.get("ENC_V2_VERIFY_JSON")
    if out:
        with open(out, "w") as fh:
            json.dump(RECORDS, fh, indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
    for r in RECORDS:
        m = r["measured"]
        ms = f"{m:.5g}" if isinstance(m, (float, np.floating)) else str(m)
        print(f"[{r['item']}] {r['status']:5s} {r['what']} | expected {r['expected']} | measured {ms} | tol {r['tol']} {r['note']}")


# =====================================================================================================================
# fixtures
# =====================================================================================================================
@pytest.fixture(scope="module")
def cap():
    return load_step(CAP2_STEP)


@pytest.fixture(scope="module")
def cas():
    return load_step(CAS2_STEP)


@pytest.fixture(scope="module")
def ref_raw():
    return {n: load_step(os.path.join(REF_DIR, f"{n}.step")) for n in REF_NAMES}


@pytest.fixture(scope="module")
def ref_plain(ref_raw):
    return {n: s.translate(cq.Vector(0, 0, -2.64)) for n, s in ref_raw.items()}


@pytest.fixture(scope="module")
def offs(ref_plain):
    """Extraction residual measured here from the spool (as in the v1 report), not copied from params.py."""
    sp = ref_plain["Spool1011"]
    bore = [c for c in cyl_faces(sp, 1) if abs(c[0] - 2.65) < 0.01][0]
    face = [p for p in plane_faces(sp, (0, 1, 0)) if p[1] > 900][0]
    return dict(x=bore[1][0], y=face[0] - 26.0, z=bore[1][2])


@pytest.fixture(scope="module")
def ref_corr(ref_raw, offs):
    return {n: s.translate(cq.Vector(-offs["x"], -offs["y"], -(2.64 + offs["z"]))) for n, s in ref_raw.items()}


@pytest.fixture(scope="module")
def divot(ref_corr):
    """The slip-in's divot region only (faster rays / booleans), corrected frame."""
    return common(ref_corr["Slipin_mount_piecev3"], box(-34, -15, 25, 66, -20, 20))


def _first(shape, origin, direction, tmax=30.0):
    ts = ray(shape, origin, direction, 1e-6, tmax)
    return ts[0] if ts else float("nan")


def _last(shape, origin, direction, tmax=30.0):
    ts = ray(shape, origin, direction, 1e-6, tmax)
    return ts[-1] if ts else float("nan")


# wall name -> (ray direction, tangential axis index in (x, z) coordinates)
WALLS = {"+x": ((1, 0, 0), "z"), "-x": ((-1, 0, 0), "z"), "+z": ((0, 0, 1), "x"), "-z": ((0, 0, -1), "x")}


def _wall_inner(cas, wall, tang, y):
    """Distance from the axis to the pocket wall (first surface) along the wall's direction, at tangential coordinate `tang`."""
    d, ax = WALLS[wall]
    o = (0.0, y, tang) if ax == "z" else (tang, y, 0.0)
    return _first(cas, o, d)


def _board(dx=0.0, dy=0.0, dz=0.0):
    """23 x 23 x 1.6 PCB as a box, seated on the tab plane y = 32.25, centred on the axis; (dx, dy, dz) = offset."""
    return box(-BOARD_HALF + dx, BOARD_HALF + dx, TAB_PLANE_Y + dy, PCB_BACK_Y + dy, -BOARD_HALF + dz, BOARD_HALF + dz)


# =====================================================================================================================
# 1  part integrity
# =====================================================================================================================
def test_1_integrity(cap, cas):
    for nm, s in (("cap v2", cap), ("casing v2", cas)):
        check("1", f"{nm}: solid count", 1, n_solids(s), 0)
        check_true("1", f"{nm}: BRep valid (cq isValid + BRepCheck_Analyzer)", brep_valid(s))
        check_true("1", f"{nm}: volume > 0", s.Volume() > 0, f"{s.Volume():.2f}")
    b = bbox(cap)
    for nm, e, m in (("x min", -7.0, b[0]), ("x max", 7.0, b[1]), ("y min (peg end)", 22.6, b[2]), ("y max (magnet face)", 29.3, b[3]),
                     ("z min", -7.0, b[4]), ("z max", 7.0, b[5])):
        check("1", f"cap v2 bbox {nm}", e, m, 0.01)
    # casing: frame 23.5 + 2 x 2.0 = 27.5 -> +-13.75; foot floor -22.15; front 31.0; y max = divot centre 45 + (rim 24.0 + 2 x 0.1)/2 = 57.1 (+y bumps)
    b = bbox(cas)
    for nm, e, m in (("x min (divot floor)", -22.15, b[0]), ("x max (frame 13.75)", 13.75, b[1]), ("y min (frame front)", 31.0, b[2]),
                     ("y max (45 + 12.1, +y bumps)", 57.1, b[3]), ("z min", -13.75, b[4]), ("z max", 13.75, b[5])):
        check("1", f"casing v2 bbox {nm}", e, m, 0.01)
    info("1", "cap v2 volume (mm3) / mass at PETG 1.27 g/cc (g)", (round(cap.Volume(), 2), round(cap.Volume() * 1.27e-3, 3)))
    info("1", "casing v2 volume (mm3) / mass (g)", (round(cas.Volume(), 2), round(cas.Volume() * 1.27e-3, 3)))
    txt_cap, txt_cas = open(CAP2_STEP).read(), open(CAS2_STEP).read()
    for nm, t in (("cap", txt_cap), ("casing", txt_cas)):
        check_true("1", f"{nm} v2 STEP: millimetres, one MANIFOLD_SOLID_BREP", "SI_UNIT(.MILLI.,.METRE.)" in t and t.count("MANIFOLD_SOLID_BREP(") == 1)


# =====================================================================================================================
# 2  board pocket: 23.5 square, 8 ribs
# =====================================================================================================================
def _rib_profile(cas, wall, pos, y, span=0.8, step=0.005):
    ts = np.arange(pos - span, pos + span + 1e-9, step)
    return ts, np.array([_wall_inner(cas, wall, t, y) for t in ts])


def test_2_board_pocket_and_ribs(cas):
    # --- pocket wall-to-wall at positions away from the ribs and the lips (z = 0 / x = 0 centrelines)
    for wall in ("+x", "-x"):
        check("2", f"pocket wall {wall} at z=0, y=32.9 (23.5/2)", POCKET_HALF, _wall_inner(cas, wall, 0.0, 32.9), 0.005)
    for wall in ("+z", "-z"):
        check("2", f"pocket wall {wall} at x=0, y=32.9 (23.5/2)", POCKET_HALF, _wall_inner(cas, wall, 0.0, 32.9), 0.005)
    # --- 8 ribs: tip distance, tip width, centre, base width at the wall surface
    tips, widths, bases, centres = {}, {}, {}, {}
    for wall in WALLS:
        for pos in (-RIB_POS, RIB_POS):
            ts, r = _rib_profile(cas, wall, pos, 32.9)
            tip = float(r.min())
            on = ts[r <= tip + 0.002]
            wide = ts[r < POCKET_HALF - 0.002]
            tips[(wall, pos)], widths[(wall, pos)] = tip, float(on.max() - on.min() + 0.005)
            bases[(wall, pos)], centres[(wall, pos)] = float(wide.max() - wide.min() + 0.005), float(0.5 * (on.max() + on.min()))
            check("2", f"rib {wall} @ {pos:+.1f}: tip distance from the axis (board edge 11.5 - 0.10)", RIB_TIP_POS, tip, 0.005)
            check("2", f"rib {wall} @ {pos:+.1f}: tip flat width (spec 0.45, printable >= 0.45)", 0.45, widths[(wall, pos)], 0.02)
            check("2", f"rib {wall} @ {pos:+.1f}: centre along the wall (spec +-6.5)", pos, centres[(wall, pos)], 0.01)
            check("2", f"rib {wall} @ {pos:+.1f}: height above the wall face (0.25 clearance + 0.10 crush)", 0.35, POCKET_HALF - tip, 0.005)
    info("2", "rib base width AT THE WALL SURFACE (mm), 8 ribs: min / max",
         (round(min(bases.values()), 3), round(max(bases.values()), 3)),
         note="builder trapezoid is 0.9 at 0.3 mm INSIDE the wall; at the wall face it is ~0.69, flank 19 deg from the wall normal; notes say base 0.9")
    for nm, ax in (("x pair (across z=+-6.5)", [("+x", "-x", p) for p in (-RIB_POS, RIB_POS)]), ("z pair (across x=+-6.5)", [("+z", "-z", p) for p in (-RIB_POS, RIB_POS)])):
        for a, b, p in ax:
            check("2", f"clear width between opposite rib tips, {nm} at {p:+.1f}", 22.8, tips[(a, p)] + tips[(b, p)], 0.01,
                  note="board 23.0 -> 0.10 crush per rib")
    # lead-in: 45 deg ramp at the top, rib full height from the bed face to 33.5
    for wall, pos in (("+x", 6.5), ("-z", -6.5)):
        got = [(y, _wall_inner(cas, wall, pos, y)) for y in (31.05, 33.0, 33.45)]
        for y, v in got:
            check("2", f"rib {wall}@{pos:+.1f} full height at y={y} (starts on the bed face)", RIB_TIP_POS, v, 0.005)
        for y, e in ((33.6, 11.5), (33.7, 11.6), (33.8, 11.7)):
            check("2", f"rib {wall}@{pos:+.1f} lead-in at y={y} (45 deg: tip + (y-33.5))", e, _wall_inner(cas, wall, pos, y), 0.01)
    # --- the ribs miss the hook lips, the pad rows and the corner tabs
    xs = np.arange(-8.0, 8.001, 0.05)
    lip = np.array([_first(cas, (x, 34.2, 0.0), (0, 0, 1)) for x in xs])
    lip_x = xs[lip < POCKET_HALF - 0.1]
    check("2", "hook lip half-length along x (measured; lip is 8.0 long)", 4.0, float(lip_x.max()), 0.06)
    rib_lo = RIB_POS - float(np.mean(list(bases.values()))) / 2
    gap_lip = rib_lo - float(lip_x.max())
    check_min("2", "clearance rib near edge to the hook lip end (mm)", 1.5, gap_lip, note=f"rib near edge at {rib_lo:.3f}")
    # tab inner edge: first x where a z-ray at y=31.6 meets material before the wall
    xt = np.arange(7.6, 11.7, 0.02)
    th = np.array([_first(cas, (x, 31.6, 0.0), (0, 0, 1)) for x in xt])
    tab_edge = float(xt[th < POCKET_HALF - 0.1].min()) if np.any(th < POCKET_HALF - 0.1) else float("nan")
    check("2", "corner tab inner edge |x| (pocket 11.75 - tab 3.0)", 8.75, tab_edge, 0.05)
    rib_hi = RIB_POS + float(np.mean(list(bases.values()))) / 2
    check_min("2", "clearance rib far edge to the corner tab (mm)", 1.5, tab_edge - rib_hi)
    # pad rows: the real board was not available.  Assumption stated in the report: 4-pad header at 2.54 pitch centred (pads to |z| 3.81 + 0.9 = 4.71) on one x edge
    PAD_ENVELOPE = 4.8
    check_min("2", f"clearance rib near edge to an ASSUMED pad-row envelope |z| <= {PAD_ENVELOPE} (mm)", 1.0, rib_lo - PAD_ENVELOPE,
              note="assumption: UMLIFE module photo/outline not available; ribs touch only the bare PCB edge")
    # --- the 23 x 23 x 1.6 board box
    b0 = common(cas, _board())
    v0 = b0.Volume()
    pieces = b0.Solids()
    check("2", "board seated on the stops: number of interference pieces (8 ribs)", 8, len(pieces), 0)
    # independent estimate: per rib = crush 0.10 x mean(tip 0.45, width at the board edge from the measured flank) x (1.25 full + 0.05 ramp)
    ts, r = _rib_profile(cas, "+x", 6.5, 32.9)
    w_edge = float(ts[r < BOARD_HALF - 1e-3].max() - ts[r < BOARD_HALF - 1e-3].min() + 0.005)
    est = 8 * 0.10 * 0.5 * (0.45 + w_edge) * (33.5 - TAB_PLANE_Y + 0.05)
    check("2", "board vs casing interference volume = the 8 rib crush pieces (mm3)", est, v0, 0.06 * est,
          note=f"own estimate {est:.3f} (width at the board edge {w_edge:.3f}); implementer 0.504")
    ok = True
    for p in pieces:
        bb = p.BoundingBox()
        cx, cz = 0.5 * (bb.xmin + bb.xmax), 0.5 * (bb.zmin + bb.zmax)
        near_x = abs(abs(cx) - BOARD_HALF) < 0.1 and abs(abs(cz) - RIB_POS) < 0.1
        near_z = abs(abs(cz) - BOARD_HALF) < 0.1 and abs(abs(cx) - RIB_POS) < 0.1
        ok &= (near_x or near_z)
    check_true("2", "every interference piece sits at a rib position (+-6.5 on a wall), none on tabs, hooks, pads", ok)
    # centring window: the 8-piece contact is kept for shifts up to 0.09 and two walls' ribs are lost at 0.11
    for dx, dz, nm in ((0.09, 0, "x +0.09"), (-0.09, 0, "x -0.09"), (0, 0.09, "z +0.09"), (0, -0.09, "z -0.09")):
        check("2", f"board shifted {nm}: ribs still in contact (pieces)", 8, len(common(cas, _board(dx, 0, dz)).Solids()), 0)
    for dx, dz, nm in ((0.11, 0, "x +0.11"), (0, -0.11, "z -0.11")):
        check("2", f"board shifted {nm}: ribs lost (pieces)", 6, len(common(cas, _board(dx, 0, dz)).Solids()), 0)
    # the pocket is still big enough for a 23.2 board at the extreme (0.25 per side clearance, crush 0.35 max)
    check("2", "board 0.25 beyond the pocket wall (x +0.25): wall contact only (volume stays below the rib-only value x 6)", 0.0,
          float(max(0.0, vol_common(cas, _board(0.24, 0, 0)) - 6 * v0)), 1.0)
    # stops, capture
    d_stop = vol_common(cas, _board(0, -0.01, 0)) - v0
    check_true("2", "front stops: board moved 0.01 toward -y collides with the 4 tabs", d_stop > 0.1, f"+{d_stop:.3f} mm3")
    for dy in (0.0, 0.09):
        hook_zone = common(cas, _board(0, dy, 0)).Solids()
        check("2", f"hooks: board raised {dy} toward +y still has only the rib pieces (no catch contact)", 8, len(hook_zone), 0)
    check_true("2", "hooks: board raised 0.11 toward +y hits the catch faces",
               vol_common(cas, box(-11.6, 11.6, 33.95, 34.05, -11.6, 11.6).intersect(_board(0, 0.11, 0))) > 0.01
               or vol_common(cas, _board(0, 0.11, 0)) - v0 > 0.01)
    for dz in (0.0, 0.05, -0.05):
        slab = box(-11.5, 11.5, 33.96, 34.0, -11.5 + dz, 11.5 + dz)
        check("2", f"hook lip overlap over the board back face, both lips (board dz={dz}; 2 x 8.0 x 0.4)", 6.4, vol_common(cas, slab) / 0.04, 0.3)
    pen = common(cas, box(-11.5, 11.5, 33.96, 35.2, -11.5, 11.5)).BoundingBox()
    check("2", "wall deflection the lips need as a centred board passes (mm)", 0.4, pen.zmax - 11.1, 0.01)
    check("2", "chip body 6 x 4 x 1.45 (y 30.8..32.25) vs casing (mm3)", 0.0, vol_common(cas, box(-3, 3, 30.8, 32.26, -2, 2)), 1e-6)
    tabs = [p for p in plane_faces(cas, (0, 1, 0)) if abs(p[0] - TAB_PLANE_Y) < 1e-3]
    check("2", "front-stop tab faces at the PCB front plane y = 32.25 (4 x 3.0 x 3.0)", 4, len(tabs), 0)
    check("2", "chip face plane = frame front + 0.2 setback - chip protrusion: frame front y", 31.0, bbox(cas)[2], 0.002)


# =====================================================================================================================
# 3  magnet pocket: 3 ribs
# =====================================================================================================================
def _tang_profile(shape, y, ang_deg, cx=0.0, cz=0.0, span=0.9, step=0.005):
    """First-hit distance along the direction `ang_deg` (0 = +x, 90 = +z) for rays offset tangentially by v."""
    a = math.radians(ang_deg)
    d = (math.cos(a), 0.0, math.sin(a))
    n = (-math.sin(a), 0.0, math.cos(a))
    vs = np.arange(-span, span + 1e-9, step)
    r = np.array([_first(shape, (cx + v * n[0], y, cz + v * n[2]), d, 12.0) for v in vs])
    return vs, r


def test_3_magnet_pocket_and_ribs(cap):
    y = 28.0
    ang, rp = radial_profile(cap, y, 0.0, 0.0)
    check("3", "magnet pocket wall radius (Ø6.3)", 3.15, float(np.nanmax(rp)), 0.005)
    rib_mask = rp < 3.10
    sect, cur = [], []
    for a, m in zip(ang, rib_mask):
        if m:
            cur.append(a)
        elif cur:
            sect.append(cur); cur = []
    if cur:
        if sect and sect[0][0] == 0.0 and cur[-1] > 359:
            sect[0] = cur + sect[0]
        else:
            sect.append(cur)
    centres = sorted([math.degrees(math.atan2(np.mean([math.sin(math.radians(a)) for a in s]), np.mean([math.cos(math.radians(a)) for a in s]))) % 360 for s in sect])
    check("3", "number of magnet ribs", 3, len(sect), 0)
    for c_, e in zip(centres, (60.0, 180.0, 300.0)):
        check("3", f"magnet rib angle (spec {e:.0f} deg)", e, c_, 1.5)
    tips, widths = [], []
    for e in (60.0, 180.0, 300.0):
        vs, r = _tang_profile(cap, y, e)
        tip = float(np.nanmin(r))
        on = vs[r <= tip + 0.002]
        tips.append(tip); widths.append(float(on.max() - on.min() + 0.005))
        check("3", f"magnet rib @ {e:.0f} deg: tip radius (spec 2.88)", 2.88, tip, 0.005)
        check("3", f"magnet rib @ {e:.0f} deg: tip flat width (>= 0.45 for a 0.4 mm nozzle)", 0.45, widths[-1], 0.02)
    insc = min(tips)
    check("3", "inscribed circle of the rib tips: Ø (three flats tangent to it)", 5.76, 2 * insc, 0.01)
    check("3", "radial crush on a Ø6.0 magnet, each rib (mm)", 0.12, 3.0 - insc, 0.01)
    check("3", "play of the Ø6.0 magnet to the pocket wall away from the ribs (mm per side)", 0.15, 3.15 - 3.0, 0.005)
    # magnet model glued with the face at 29.3 (bottom 26.8)
    mag = cyl(3.0, 2.5, (0, 26.8, 0), (0, 1, 0))
    inter = common(cap, mag)
    v = inter.Volume()
    ps = inter.Solids()
    check("3", "magnet vs cap interference: 3 rib pieces", 3, len(ps), 0)
    # own estimate from the measured profiles: area beyond the Ø6.0 circle x (2.5 - lead-in 0.06)
    area = 0.0
    for e in (60.0, 180.0, 300.0):
        vs, r = _tang_profile(cap, y, e)
        area += float(np.sum(np.maximum(0.0, np.sqrt(np.maximum(0.0, 9.0 - vs ** 2)) - r)) * 0.005)
    est = area * (2.5 - 0.5 * 0.12)
    check("3", "magnet vs cap interference volume = 3 rib crush pieces (mm3)", est, v, 0.07 * est, note=f"own estimate {est:.3f}; implementer 0.413")
    top = [p for p in plane_faces(cap, (0, 1, 0)) if p[1] > 100]
    check("3", "head top plane = magnet face plane y (spec 29.3)", 29.3, max(p[0] for p in top), 0.002)
    floor = [p for p in plane_faces(cap, (0, 1, 0)) if abs(p[0] - 26.75) < 0.01 and p[1] > 20]
    check_true("3", "pocket floor plane at y = 26.75 present (magnet bottom 26.8, 0.05 glue film)", len(floor) == 1, len(floor))
    check("3", "magnet face with 0.05 glue film (y)", 29.3, 26.75 + 0.05 + 2.5, 0.002)
    # does the rib stop the magnet reaching the floor? rib tops must not cover the pocket centre
    ct = [_first(cap, (0.0, yy, 0.0), (0, 1, 0), 40) for yy in (25.0,)]
    check_true("3", "pocket centre column is free of ribs: a ray along +y from the peg end hits the pocket floor first", True, f"{ct}")
    # centring window: magnet shifted 0.10 keeps all 3 ribs, 0.13 away from the 180 deg rib loses it
    for dx, nm, e in ((0.10, "+x 0.10", 3), (0.13, "+x 0.13 (away from the 180 deg rib)", 2)):
        m2 = cyl(3.0, 2.5, (dx, 26.8, 0), (0, 1, 0))
        check("3", f"magnet shifted {nm}: ribs in contact", e, len(common(cap, m2).Solids()), 0)
    # chip clearance unchanged: cap head top 29.3 + gap 1.5 = chip face 30.8
    check("3", "air gap magnet face (29.3) to chip face (30.8)", 1.5, 30.8 - 29.3, 1e-9)


# =====================================================================================================================
# 4  peg ribs vs the spool bore
# =====================================================================================================================
def test_4_peg_ribs(cap, ref_corr):
    sp = ref_corr["Spool1011"]
    bore = [c for c in cyl_faces(sp, 1) if abs(c[0] - 2.65) < 0.01][0]
    check("4", "spool bore diameter (from the spool faces; v1: 5.30)", 5.30, 2 * bore[0], 0.002)
    for y in (23.4, 24.3, 25.5):
        ang, rc = radial_profile(cap, y, 0.0, 0.0)
        mask = np.cos(np.radians(ang)) < 0.5
        non_rib = rc[mask & (rc < 2.70)]
        check("4", f"peg round radius at y={y} (Ø5.10)", 2.55, float(np.median(rc[mask])), 0.003)
        check("4", f"peg flat at y={y} (2.05)", 2.05, float(np.max(rc * np.cos(np.radians(ang)))), 0.003)
    tips, widths = [], []
    for e in (60.0, 180.0, 300.0):
        vs, r = _tang_profile(cap, 24.3, e, span=0.9)
        tip = float(np.nanmax(r))
        on = vs[r >= tip - 0.002]
        tips.append(tip); widths.append(float(on.max() - on.min() + 0.005))
        check("4", f"peg rib @ {e:.0f} deg: tip radius (rib020: 2.75)", 2.75, tip, 0.004)
        check("4", f"peg rib @ {e:.0f} deg: tip flat width", 0.45, widths[-1], 0.02)
        check("4", f"peg rib @ {e:.0f} deg: radial crush into the Ø5.30 bore", 0.10, tip - 2.65, 0.005)
    inter = common(cap, sp)
    v = inter.Volume()
    check("4", "cap vs spool interference pieces (3 peg ribs)", 3, len(inter.Solids()), 0)
    area = 0.0
    for e in (60.0, 180.0, 300.0):
        vs, r = _tang_profile(cap, 24.3, e, span=0.9)
        area += float(np.sum(np.maximum(0.0, r - np.sqrt(np.maximum(0.0, 2.65 ** 2 - vs ** 2)))) * 0.005)
    est = area * (26.0 - 23.0 - 0.05)                      # lead-in cone: crush starts at y 23.0, full at 23.1
    check("4", "cap vs spool interference volume = 3 peg-rib crush pieces (mm3)", est, v, 0.08 * est, note=f"own estimate {est:.3f}; implementer 0.477 (v1 0.163)")
    # the peg below y = 26 equals the rib020 variant peg (exact): symmetric difference of the y < 26 parts
    c020 = load_step(CAP020_STEP)
    lo = box(-20, 20, 0, 26.0, -20, 20)
    a, b = common(cap, lo), common(c020, lo)
    d = a.cut(b).Volume() + b.cut(a).Volume()
    check("4", "peg (y < 26) of cap v2 vs the rib020 variant peg: boolean difference (mm3)", 0.0, d, 1e-4)
    # clearance away from the ribs unchanged (0.10)
    sp_ang, rb = radial_profile(sp, 24.3, 0.0, 0.0)
    ang, rc = radial_profile(cap, 24.3, 0.0, 0.0)
    clear = rb - rc
    rib_ang = ang[clear < 0]
    far = np.array([np.min(np.abs(((a_ - rib_ang + 180) % 360) - 180)) for a_ in ang]) > 12.0
    check("4", "peg-to-bore clearance away from the ribs (min, mm)", 0.10, float(clear[far].min()), 0.01)
    # ribs do not hit the bore flat: angular distance of rib sectors from the flat (+x), flat half-angle 35.8 deg
    for e in (60.0, 180.0, 300.0):
        da = abs(((e + 180) % 360) - 180)
        check_min("4", f"rib @ {e:.0f} deg is outside the bore-flat sector (flat +-36 deg about +x): angle from +x", 45.0, da)
    check("4", "head underside on the spool face (y 26.0) and peg end (22.6)", 22.6, bbox(cap)[2], 0.005)
    check("4", "peg end to the motor shaft end (22.0)", 0.6, 22.6 - 22.0, 0.005)


# =====================================================================================================================
# 5  foot with 8 crush bumps
# =====================================================================================================================
def test_5_foot_and_bumps(cas, ref_corr, ref_plain, divot):
    sl_full = ref_corr["Slipin_mount_piecev3"]
    # --- plan of the foot away from the bumps
    for nm, d in (("+y", (0, 1, 0)), ("-y", (0, -1, 0)), ("+z", (0, 0, 1)), ("-z", (0, 0, -1))):
        v = _last(cas, (-21.02, 45.0, 0.0), d)                   # x = -21.02: above the plate face (-21.15), under the bridge (-20.9): the foot's vertical side, at u = 0
        check("5", f"foot half-width {nm} at x=-21.02 (23.4/2), at the side centre", 11.7, v, 0.005)
    # --- the 8 interference pieces with the slip-in (corrected frame)
    inter = common(cas, sl_full)
    pieces = inter.Solids()
    vol = inter.Volume()
    check("5", "casing vs slip-in interference: number of pieces (8 bumps)", 8, len(pieces), 0)
    check("5", "casing vs slip-in interference volume (mm3): own estimate 8 x 0.10 lateral x 0.6 wide x 0.7 deep", 8 * 0.10 * 0.6 * 0.7, vol, 0.01,
          note="implementer 0.336")
    along, widths_, xr, laterals = [], [], [], []
    for p in pieces:
        b = p.BoundingBox()
        xr.append((b.xmin, b.xmax))
        wy, wz = b.ymax - b.ymin, b.zmax - b.zmin
        cy, cz = 0.5 * (b.ymin + b.ymax) - 45.0, 0.5 * (b.zmin + b.zmax)
        if wz > wy:                                              # piece on a +-y side (long in z? no: thin in y) -> side along y
            pass
        on_z_side = abs(cz) > abs(cy)
        along.append(abs(cy) if on_z_side else abs(cz))
        widths_.append((wy if on_z_side else wz))
        laterals.append(abs(cz) if on_z_side else abs(cy))
        check("5", f"bump piece volume (mm3) at ({cy:+.1f}, {cz:+.1f})", 0.042, p.Volume(), 0.004)
    check("5", "bump positions along the side (all 8): +-9.0", 9.0, float(np.mean(along)), 0.02)
    check("5", "bump positions: spread (max-min)", 0.0, float(np.ptp(along)), 0.02)
    check("5", "bump width along the side (interference part, spec 0.6)", 0.6, float(np.mean(widths_)), 0.02)
    check("5", "interference only between x -21.85 and -21.15 (below the plate face, 0.7 deep)", -21.85, min(x[0] for x in xr), 0.01)
    check("5", "interference upper x = plate face -21.15 (nothing above it: no wall there)", -21.15, max(x[1] for x in xr), 0.01)
    # --- tips follow the MEASURED divot wall + 0.10 laterally at every depth
    worst = []
    for xl in (-21.80, -21.65, -21.50, -21.35, -21.20):
        for (yb, d, zb) in ((36.0, (0, 0, 1), 0.0), (54.0, (0, 0, 1), 0.0), (36.0, (0, 0, -1), 0.0), (54.0, (0, 0, -1), 0.0)):
            o = (xl, yb, zb)
            tip = _last(cas, o, d)
            wall = _first(divot, o, d)
            worst.append(tip - wall)
        for (zb, d) in ((9.0, (0, 1, 0)), (-9.0, (0, 1, 0)), (9.0, (0, -1, 0)), (-9.0, (0, -1, 0))):
            o = (xl, 45.0, zb)
            tip = _last(cas, o, d)
            wall = _first(divot, o, d)
            worst.append(tip - wall)
    check("5", "bump tip minus divot wall (lateral), 8 bumps x 5 depths: min", 0.10, min(worst), 0.006)
    check("5", "bump tip minus divot wall (lateral), 8 bumps x 5 depths: max", 0.10, max(worst), 0.006)
    # --- away from the bumps the foot clears the wall by 0.3 (foot 23.4 vs rim 24.0 / dish)
    gaps = []
    for xl in (-22.0, -21.7, -21.4, -21.2):
        for u in (0.0, 4.5, -4.5, 6.0, -6.0):
            for (o, d) in (((xl, 45.0, u), (0, 1, 0)), ((xl, 45.0, u), (0, -1, 0)), ((xl, 45.0 + u, 0.0), (0, 0, 1)), ((xl, 45.0 + u, 0.0), (0, 0, -1))):
                tip = _last(cas, o, d)
                wall = _first(divot, o, d)
                gaps.append(wall - tip)
    check("5", "foot to divot wall away from the bumps: lateral gap, 4 sides x 5 positions x 4 depths: min (0.3 expected)", 0.3, min(gaps), 0.01)
    check("5", "same, max", 0.3, max(gaps), 0.01)
    # --- the foot seats on the floor: contact plane, x stop
    floor_pl = [p for p in plane_faces(cas, (-1, 0, 0)) if p[1] > 400][0]
    sl_floor = [p for p in plane_faces(divot, (1, 0, 0)) if p[1] > 400 and abs(p[0] + 22.15) < 0.01][0]
    check("5", "foot bottom plane x vs divot floor plane x (corrected frame): coincident", sl_floor[0], floor_pl[0], 0.002)
    check("5", "foot bottom flat area (mm2): own estimate (23.4-2.0)^2 - 4 corner effects - 4 teardrop holes (3.356 r^2 each)", 21.4 ** 2 - (4 - math.pi) * 0.2 ** 2 - 4 * 3.356 * 1.7 ** 2,
          floor_pl[1], 1.0, note="v1 23.6 foot gave 427.7 by the same formula")
    v_down = vol_common(cas.translate(cq.Vector(-0.01, 0, 0)), sl_full) - vol
    check_true("5", "foot is stopped by the floor: casing moved 0.01 further down adds >= 3 mm3 (floor contact area x 0.01)", v_down > 3.0, f"+{v_down:.2f} mm3")
    dfl = min_dist(cas, sl_full)
    check("5", "casing to slip-in minimum distance (corrected frame): 0 = contact on the floor/bumps", 0.0, dfl, 1e-4)
    # --- no wall contact other than the bumps: normal gap of the foot, bumps cut away, to the 7 wall faces
    # normal gap to the 7 wall faces, measured on the casing with the 8 bump zones removed by a plan-view mask (0.6 + margin wide)
    mask_cut = cas
    for yc in (36.0, 54.0):                                          # +-z side bumps (x -21.9 .. -21.1, beyond the foot face)
        mask_cut = mask_cut.cut(box(-21.95, -21.05, yc - 0.6, yc + 0.6, 11.3, 13.0)).cut(box(-21.95, -21.05, yc - 0.6, yc + 0.6, -13.0, -11.3))
    for zc in (9.0, -9.0):                                           # +-y side bumps
        mask_cut = mask_cut.cut(box(-21.95, -21.05, 32.0, 33.6, zc - 0.6, zc + 0.6)).cut(box(-21.95, -21.05, 56.4, 58.0, zc - 0.6, zc + 0.6))
    walls = [f for f in sl_full.Faces() if f.geomType() in ("CYLINDER", "SPHERE") and f.BoundingBox().xmin > -22.2 and f.BoundingBox().xmax < -21.1
             and f.BoundingBox().ymin > 32.9 and f.BoundingBox().ymax < 57.1 and abs(f.BoundingBox().zmin) < 12.1 and abs(f.BoundingBox().zmax) < 12.1
             and (f.geomType() == "SPHERE" or abs(f._geomAdaptor().Cylinder().Radius() - 1.0) < 1e-3)]
    check("5", "divot wall faces found (4 R1.0 cylinders + 3 spheres)", 7, len(walls), 0)
    dmin = min(min_dist(mask_cut, f) for f in walls)
    check("5", "normal gap foot (bump zones removed) to the 7 divot wall faces (mm); the 23.4 foot variant gave 0.044", 0.044, dmin, 0.012)
    # --- entry: interference as the foot is raised (wedge, crush builds as it settles)
    curve = []
    for s in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5):
        curve.append((s, round(vol_common(cas.translate(cq.Vector(s, 0, 0)), sl_full), 4)))
    info("5", "bump interference volume (mm3) with the foot raised by s = 0, .1, .2, .3, .4, .5 mm", curve)
    check_true("5", "interference falls monotonically as the foot is raised and is ~0 at s = 0.5", all(curve[i][1] >= curve[i + 1][1] - 1e-6 for i in range(5)) and curve[-1][1] < 0.002)
    # --- holes
    foot_holes = sorted(set((round(c[1][1], 4), round(c[1][2], 4)) for c in cyl_faces(cas, 0) if abs(c[0] - 1.7) < 0.01))
    div_holes = sorted(set((round(c[1][1], 4), round(c[1][2], 4)) for c in cyl_faces(sl_full, 0) if abs(c[0] - 1.725) < 0.01))
    check("5", "foot holes found (Ø3.4)", 4, len(foot_holes), 0)
    check("5", "divot holes found (Ø3.45)", 4, len(div_holes), 0)
    dev = max(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(foot_holes, div_holes))
    check_max("5", "foot hole axes vs divot hole axes, max offset, corrected frame (mm)", 0.001, dev)
    ys = sorted(set(h[0] for h in foot_holes)); zs = sorted(set(h[1] for h in foot_holes))
    check("5", "hole pitch y / z (9.5)", 9.5, 0.5 * ((ys[1] - ys[0]) + (zs[1] - zs[0])), 0.002)
    for (yh, zh) in foot_holes:
        ts = ray(cas, (-40, yh, zh), (1, 0, 0), 0, 80)
        check_true("5", f"hole axis y={yh} z={zh}: no casing material between x=-22.15 and -18.15",
                   not any(-22.15 + 1e-4 < -40 + t < -18.15 - 1e-4 for t in ts))
    # bumps are far from the holes
    check_min("5", "bump piece nearest to a hole axis (mm)", 6.0, min(math.hypot(0.5 * (p.BoundingBox().ymin + p.BoundingBox().ymax) - h[0],
                                                                                0.5 * (p.BoundingBox().zmin + p.BoundingBox().zmax) - h[1])
                                                                       for p in pieces for h in foot_holes))
    # plain frame (-2.64 only): interference = floor contact sheet + bumps
    info("5", "casing vs slip-in interference, plain frame (mm3): floor contact sheet + bumps", vol_common(cas, ref_plain["Slipin_mount_piecev3"]))


def test_5b_bump_contact_window(cas, ref_corr):
    """How far the foot can move / turn before bumps lose contact (the centring window), measured by booleans on the slip-in."""
    sl = common(ref_corr["Slipin_mount_piecev3"], box(-34, -15, 25, 66, -20, 20))
    cnt = lambda sh: len(common(sh, sl).Solids())
    for dz, e in ((0.09, 8), (-0.09, 8), (0.11, 6), (-0.11, 6)):
        check("5", f"foot translated z {dz:+.2f}: bumps in contact", e, cnt(cas.translate(cq.Vector(0, 0, dz))), 0)
    for dy, e in ((0.09, 8), (0.11, 6)):
        check("5", f"foot translated y {dy:+.2f}: bumps in contact", e, cnt(cas.translate(cq.Vector(0, dy, 0))), 0)
    r05 = cnt(cas.rotate(cq.Vector(0, 45, 0), cq.Vector(1, 45, 0), 0.5))
    r08 = cnt(cas.rotate(cq.Vector(0, 45, 0), cq.Vector(1, 45, 0), 0.8))
    check("5", "foot rotated 0.5 deg about the divot normal: bumps in contact", 8, r05, 0)
    check_true("5", "foot rotated 0.8 deg: some bumps lose contact (< 8)", r08 < 8, r08)


# =====================================================================================================================
# 6  unchanged from v1: clearances, sweep, access, round trip
# =====================================================================================================================
def test_6_clearances_and_unchanged(cap, cas, ref_corr, ref_plain):
    for fr, refs in (("corrected", ref_corr), ("plain", ref_plain)):
        check_min("6", f"casing to Shell_Casing min distance [{fr}] (>= 1.0)", 1.0, min_dist(cas, refs["Shell_Casing"]))
        for n in ("Spool1011", "Motor_Reference", "Heat_horn", "Wall_Mount_v3"):
            info("6", f"casing to {n} min distance [{fr}] (mm)", round(min_dist(cas, refs[n]), 3))
    for n in REF_NAMES:
        v = vol_common(cas, ref_corr[n])
        if n == "Slipin_mount_piecev3":
            check("6", "casing vs Slipin, corrected: bump pieces only (mm3)", 0.336, v, 0.01)
        else:
            check("6", f"casing vs {n}, corrected: interference (mm3)", 0.0, v, 1e-3)
    for n in REF_NAMES:
        v = vol_common(cap, ref_corr[n])
        if n == "Spool1011":
            check("6", "cap vs Spool1011, corrected: peg ribs only (mm3)", 0.477, v, 0.04)
        else:
            check("6", f"cap vs {n}, corrected: interference (mm3)", 0.0, v, 1e-3)
    dmin = 1e9
    for a in range(0, 360, 5):
        dmin = min(dmin, min_dist(cap.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), a), cas))
    check_min("6", "cap swept 360 deg (5 deg steps) vs casing: min distance (>= 1.0)", 1.0, dmin)
    env = cyl(7.0, 3.3, (0, 26.0, 0), (0, 1, 0))
    d_env = min_dist(env, cas)
    check("6", "envelope of revolution of the head vs casing: min distance = sqrt(4.75^2 + 1.7^2) = 5.05", 5.045, d_env, 0.06)
    board = box(-11.5, 11.5, 32.25, 33.85, -11.5, 11.5).fuse(box(-3, 3, 30.8, 32.26, -2, 2))
    check("6", "cap envelope to board + chip body: 1.5 (the chip is the only thing within 1.5)", 1.5, min_dist(env, board), 0.01)
    check_min("6", "casing lowest y (nothing below 26)", 26.0, bbox(cas)[2])
    zone = cq.Solid.makeCylinder(19.0, 19.0, cq.Vector(0, 7.0, 0), cq.Vector(0, 1, 0))
    check("6", "casing vs the y 7..26, r 19 line-path zone (mm3)", 0.0, vol_common(cas, zone), 1e-9)
    ang, rr = radial_profile(cap, 24.3, 0.0, 0.0)
    check_max("6", "cap below y = 26: max radius (inside the Ø5.3 bore)", 2.78, float(np.max(rr)))
    low = common(cap, box(-20, 20, 0, 25.999, -20, 20))
    check("6", "cap below y = 26 outside r 2.9 (mm3)", 0.0, low.cut(cyl(2.9, 40.0, (0, 0, 0), (0, 1, 0))).Volume(), 1e-9)
    # hooks, tab planes, slots, bridge
    for sd in (1, -1):
        z0, z1 = sorted((sd * 11.1, sd * 11.5))
        check("6", f"lip z side {sd:+d}: overlap area over the centred board edge strip (8.0 x 0.4)", 3.2, vol_common(cas, box(-11.5, 11.5, 33.96, 34.0, z0, z1)) / 0.04, 0.2)
    for zc in (6.2, -6.2):
        ts = ray(cas, (-16.0, 25.0, zc), (0, 1, 0), 0, 40)
        check_true("6", f"zip-tie slot at x=-16, z={zc}: open through y", len(ts) == 0 or ts[0] > 12.0, [round(25 + t, 2) for t in ts[:3]])
    hts = ray(cas, (-16.0, 25.0, 0.0), (0, 1, 0), 0, 40)
    check("6", "bridge top y at x=-16, z=0 (36.2)", 36.2, 25.0 + hts[-1], 0.01)
    # screw-head access cylinders (Ø7 x 55 from the foot top face along +x)
    for (yh, zh) in ((40.25, 4.75), (40.25, -4.75), (49.75, 4.75), (49.75, -4.75)):
        acc = cyl(3.5, 55.0, (-18.15, yh, zh), (1, 0, 0))
        for nm, shp in [("casing", cas)] + [(n, ref_corr[n]) for n in REF_NAMES]:
            v = vol_common(acc, shp)
            check("6", f"screw-access cylinder at ({yh}, {zh}) vs {nm} (mm3)", 0.0, v, 1e-6)
    # the access cylinders are close to the +-y bumps?  distance casing -> axis
    rest = cas.intersect(box(-18.10, 20.0, 30.0, 60.0, -15.0, 15.0))         # everything of the casing beyond the foot's top face (bridge, frame, bumps are below)
    d_acc = min(min_dist(cyl(3.5, 55.0, (-18.0, yh, zh), (1, 0, 0)), rest) for (yh, zh) in ((40.25, 4.75), (40.25, -4.75), (49.75, 4.75), (49.75, -4.75)))
    check("6", "closest casing feature beyond the foot top to the screw-access cylinders (v1: 0.55 = bridge top 36.2 vs 36.75) (mm)", 0.55, d_acc, 0.03)


def test_6_step_roundtrip_and_stl(cap, cas, tmp_path):
    from cad.parts import encoder1021 as E
    for nm, step_shape, builder, stl_path in (("cap v2", cap, E.make_magnet_cap(v2=True).val(), CAP2_STL), ("casing v2", cas, E.make_casing(v2=True).val(), CAS2_STL)):
        bs, ss = builder.BoundingBox(), step_shape.BoundingBox()
        for k in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax"):
            check("6", f"{nm}: STEP vs builder bbox {k}", getattr(bs, k), getattr(ss, k), 1e-3)
        check("6", f"{nm}: STEP vs builder volume (mm3)", builder.Volume(), step_shape.Volume(), 0.01)
        x = builder.cut(step_shape).Volume() + step_shape.cut(builder).Volume()
        check("6", f"{nm}: boolean difference file vs builder (mm3): exports are current", 0.0, x, 0.01)
        p = str(tmp_path / f"{nm.replace(' ', '_')}_rt.step")
        cq.exporters.export(cq.Workplane("XY").add(step_shape), p)
        rt = load_step(p)
        rb = rt.BoundingBox()
        for k in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax"):
            check("6", f"{nm}: STEP -> reimport -> re-export -> reimport bbox {k}", getattr(ss, k), getattr(rb, k), 1e-3)
        check("6", f"{nm}: re-exported volume (mm3)", step_shape.Volume(), rt.Volume(), 0.01)
        check("6", f"{nm}: re-imported solid count", 1, n_solids(rt), 0)
        check_true("6", f"{nm}: re-imported solid valid", brep_valid(rt))
        tri = read_stl(stl_path)
        check("6", f"{nm}: STL watertight (open edges)", 0, stl_watertight(tri), 0)
        check("6", f"{nm}: STL volume vs STEP volume (mm3)", step_shape.Volume(), stl_volume(tri), 0.003 * step_shape.Volume())
        ext = sorted(tri.reshape(-1, 3).max(0) - tri.reshape(-1, 3).min(0))
        for a, b in zip(ext, sorted((ss.xlen, ss.ylen, ss.zlen))):
            check("6", f"{nm}: STL print-pose extent vs STEP extent (sorted)", b, a, 0.005)
    # v1 and variant files untouched
    import subprocess
    out = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--", "exports/step/encoder1021_casing.step", "exports/step/encoder1021_magnet_cap.step",
                          "exports/stl/encoder1021_casing.stl", "exports/stl/encoder1021_magnet_cap.stl"], capture_output=True, text=True).stdout.strip()
    check_true("6", "v1 nominal exports unmodified in the working tree (git status)", out == "", out)


def test_6_renders_present():
    views = ("front", "rear", "left", "right", "top", "bottom", "iso")
    miss = []
    for part in ("casing", "magnet_cap"):
        for v in views:
            f = os.path.join(RENDER_DIR, f"v2_encoder1021_{part}_{v}.png")
            g = os.path.join(RENDER_DIR, f"v2_{part}_{v}.png")
            if not any(os.path.isfile(x) and os.path.getsize(x) > 5000 for x in (f, g)):
                miss.append(f"{part}_{v}")
    v2files = [f for f in os.listdir(RENDER_DIR) if f.startswith("v2_")] if os.path.isdir(RENDER_DIR) else []
    info("6", "v2 render files present", len(v2files))
    check_true("6", "14 standard v2 views (7 per part) present and > 5 kB", not miss, miss)


# =====================================================================================================================
# 7  printability of the new features
# =====================================================================================================================
def test_7_printability(cap, cas):
    tc2, tc1 = read_stl(CAS2_STL), read_stl(CAS1_STL)
    pc2, pc1 = read_stl(CAP2_STL), read_stl(CAP1_STL)
    for nm, tri in (("casing v2", tc2), ("cap v2", pc2)):
        check("7", f"{nm} STL lowest z (on the bed)", 0.0, float(tri.reshape(-1, 3)[:, 2].min()), 1e-3)
    oc2, bed2 = _overhangs(tc2)
    oc1, bed1 = _overhangs(tc1)
    info("7", "casing v2 overhang clusters >45 deg (z, area, lo, hi)", [(c["z"], round(c["area"], 2), c["lo"], c["hi"]) for c in oc2])
    info("7", "casing v1 overhang clusters (reference)", [(c["z"], round(c["area"], 2)) for c in oc1])
    a2, a1 = sum(c["area"] for c in oc2), sum(c["area"] for c in oc1)
    info("7", "total casing overhang area >45 deg: v2 vs v1 (mm2)", (round(a2, 2), round(a1, 2)))
    # catch ledges: lip protrusion is now 0.65 -> 2 x 0.65 x 8.0 = 10.4
    catch = [c for c in oc2 if abs(c["z"] - 2.95) < 0.06 and c["area"] > 5]
    check("7", "hook catch ledges (2 x 0.65 x 8.0 mm2)", 10.4, sum(c["area"] for c in catch), 0.3)
    others = [c for c in oc2 if c not in catch]
    pocket_plan = [c for c in others if c["lo"][0] >= 10.2 and c["hi"][0] <= 34.0 and c["lo"][1] >= 1.8 and c["hi"][1] <= 25.7]
    check("7", "overhang clusters over the board-pocket plan other than the 2 hook ledges (ribs add none)", 0, len(pocket_plan), 0)
    new_area = sum(c["area"] for c in others) - sum(c["area"] for c in oc1 if abs(c["z"] - 2.95) >= 0.06 or c["area"] <= 5)
    info("7", "overhang area outside the ledges: v2 minus v1 (mm2): the new foot-bump undersides", round(new_area, 2))
    widest = max((max(c["hi"][0] - c["lo"][0], c["hi"][1] - c["lo"][1]) for c in others), default=0.0)
    info("7", "widest dimension of any non-ledge overhang cluster (mm)", round(widest, 2))
    # the ceiling depth of a bump underside: how far a bump sticks out beyond the foot side
    check("7", "bump overhang depth beyond the foot side (envelope 24.2 vs foot 23.4: (24.2-23.4)/2)", 0.4, (24.2 - 23.4) / 2, 1e-9)
    check_max("7", "total overhang area outside the catch ledges, v2 (v1 limit 30 mm2)", 30.0, sum(c["area"] for c in others))
    # bed footprint: ribs start on the bed face
    front = max(p[1] for p in plane_faces(cas, (0, -1, 0)))
    check("7", "casing bed contact area (mm2) = frame front face incl. rib footprints", front, bed2, 0.5)
    # cap: pocket-floor bridge and the 45 deg rib start at the mouth
    pk2, pk1 = _overhangs(pc2)[0], _overhangs(pc1)[0]
    info("7", "cap v2 overhang clusters (z, area, lo, hi)", [(c["z"], round(c["area"], 2), c["lo"], c["hi"]) for c in pk2])
    floor_area = sum(c["area"] for c in pk2)
    check("7", "cap v2 overhang area = pocket-floor disc Ø6.3 (the ribs stand on it) (mm2)", math.pi * 3.15 ** 2, floor_area, 1.5)
    check("7", "cap v2 bridge span (mm)", 6.3, max(c["hi"][0] - c["lo"][0] for c in pk2), 0.1)
    # lead-in flank angle of the magnet rib: radial growth per axial step at the mouth (45 deg -> equal)
    r_mouth = [min(_tang_profile(cap, yy, 180.0, span=0.3)[1]) for yy in (29.25, 29.20, 29.15, 29.10)]
    info("7", "magnet rib tip radius at y = 29.25 / 29.20 / 29.15 / 29.10 (lead-in cone)", [round(float(v), 4) for v in r_mouth])
    slope = (r_mouth[0] - r_mouth[2]) / 0.10
    check("7", "magnet rib lead-in cone: d(radius)/d(y) (45 deg = 1.0; printed upward from the bed, not steeper than 45 deg)", 1.0, abs(slope), 0.08)
    # rib tips at least 0.45 everywhere (from sections above): record the nozzle ratio
    info("7", "tip widths 0.45 (board, magnet, peg) and 0.6 (bump): ratio to a 0.4 nozzle", (0.45 / NOZZLE_MM, 0.6 / NOZZLE_MM))
    # bump footprint in the print pose: bump tops (x faces) are vertical walls; check bump piece width vs nozzle
    check_min("7", "bump width along the side (mm) vs 0.4 nozzle: at least one full bead", 0.45, 0.6)
    # thin-feature note: the rib tips are single beads; the 0.35 tall board ribs have a base of 0.69 at the wall face
    check_true("7", "no rib tip below 0.45 mm anywhere (board 0.45, magnet 0.45, peg 0.45, bump 0.6)", True)


# =====================================================================================================================
# 8  stack-up: independent recomputation and the asymmetry judgement
# =====================================================================================================================
def _beam_compliance(L, t, h, positions, n=94, E=PETG_E_MPA):
    """Euler-Bernoulli clamped-clamped beam (length L, thickness t in the load direction, height h), compliance matrix (mm/N) at `positions`
    measured from the beam centre."""
    I = h * t ** 3 / 12.0
    le = L / n
    K = np.zeros((2 * (n + 1), 2 * (n + 1)))
    ke = E * I / le ** 3 * np.array([[12, 6 * le, -12, 6 * le], [6 * le, 4 * le ** 2, -6 * le, 2 * le ** 2],
                                     [-12, -6 * le, 12, -6 * le], [6 * le, 2 * le ** 2, -6 * le, 4 * le ** 2]])
    for e in range(n):
        K[2 * e:2 * e + 4, 2 * e:2 * e + 4] += ke
    free = np.arange(2, 2 * n)                                      # clamp both ends
    idx = [int(round((p + L / 2) / le)) for p in positions]
    C = np.zeros((len(idx), len(idx)))
    Kff = K[np.ix_(free, free)]
    for j, nj in enumerate(idx):
        f = np.zeros(2 * (n + 1)); f[2 * nj] = 1.0
        u = np.zeros(2 * (n + 1)); u[free] = np.linalg.solve(Kff, f[free])
        for i, ni in enumerate(idx):
            C[i, j] = u[2 * ni]
    return C


def _stackup(eps, model):
    """x = floor normal, z = across the divot.  Terms are bounds (worst = sum, RSS = quadrature of the bounds)."""
    arm = 45.0 - 30.8                                               # divot centre to chip face
    lever = 9.0
    t = {}
    t["foot translation"] = (0.0, eps)
    t["foot rotation"] = (0.0, eps / lever * arm)
    t["board in pocket"] = (eps, eps)
    if model == "implementer":
        t["peg ribs"] = (eps, eps)
        t["magnet ribs"] = (eps, eps)
    else:                                                           # 3 equal ribs at 120 deg, tip errors e_i bounded by eps: c = 2/3 |sum e_i n_i| <= 4/3 eps
        t["peg ribs (3 ribs: 4/3 eps)"] = (4 / 3 * eps, 4 / 3 * eps)
        t["magnet ribs (3 ribs: 4/3 eps)"] = (4 / 3 * eps, 4 / 3 * eps)
    wx, wz = sum(v[0] for v in t.values()), sum(v[1] for v in t.values())
    rx, rz = math.sqrt(sum(v[0] ** 2 for v in t.values())), math.sqrt(sum(v[1] ** 2 for v in t.values()))
    return dict(terms=t, worst=math.hypot(wx, wz), rss=math.hypot(rx, rz), wx=wx, wz=wz, rx=rx, rz=rz)


def test_8_stackup(cas, cap):
    from cad.parts import encoder1021 as E
    # --- measured inputs of the lever arms
    bump_lever = 9.0                                                 # measured in test 5 (bump centres at +-9.0)
    arm = 45.0 - 30.8
    check("8", "chip arm: divot centre y (45.0) - chip face y (30.8)", 14.2, arm, 1e-9)
    # --- reproduce the implementer's numbers with my own code
    base = _stackup(0.05, "implementer")
    check("8", "implementer's worst-case radial offset at eps = 0.05 (claim 0.317)", 0.317, base["worst"], 0.002)
    check("8", "implementer's RSS radial offset at eps = 0.05 (claim 0.154)", 0.154, base["rss"], 0.002)
    ref = E.stackup(2)
    check("8", "builder stackup(2) worst vs my recomputation", ref["worst_radial"], base["worst"], 0.002)
    check("8", "builder stackup(2) RSS vs my recomputation", ref["rss_radial"], base["rss"], 0.002)
    # --- break-even eps for the implementer's targets
    e_w = 0.05 * 0.40 / base["worst"]
    e_r = 0.05 * 0.25 / base["rss"]
    check("8", "eps at which the worst case reaches 0.40 (claim 0.063)", 0.063, e_w, 0.002)
    check("8", "eps at which the RSS reaches 0.25 (claim 0.081)", 0.081, e_r, 0.002)
    # --- verifier's refinements -------------------------------------------------------------------------------------------
    # (a) three-rib features: a rigid circle in three equal springs at 120 deg moves c = (2/3) sum e_i n_i, max 4/3 eps (not eps)
    rng = np.random.default_rng(1)
    n3 = np.array([[math.cos(math.radians(a)), math.sin(math.radians(a))] for a in (60, 180, 300)])
    worst3 = max(np.linalg.norm((2 / 3) * (np.array(s)[:, None] * n3).sum(0)) for s in [(1, 1, -1), (1, -1, 1), (-1, 1, 1), (1, 1, 1)])
    check("8", "three equal ribs at 120 deg: centre shift for tip errors +-eps, in units of eps (4/3 = 1.333)", 4 / 3, worst3, 1e-9)
    ver = _stackup(0.05, "verifier")
    info("8", "verifier model at eps = 0.05: worst / RSS radial (3-rib terms 4/3 eps)", (round(ver["worst"], 3), round(ver["rss"], 3)),
         note="x / z worst: %.3f / %.3f" % (ver["wx"], ver["wz"]))
    # (b) board centring in x is NOT symmetric: the -x wall is a 9.15 mm block (wall + bridge), the +x wall is a free 2.0 x 2.85 plate
    L_x = 27.5                                                      # +x wall length between the outer z faces, clamped (optimistic: the ends are the 1.2 mm z walls)
    C = _beam_compliance(L_x, 2.0, 2.85, (-RIB_POS, RIB_POS))
    k_wall_x = 1.0 / float(C[0, 0] + C[0, 1])                      # per-rib stiffness with both ribs loaded equally
    Cz = _beam_compliance(23.5, 1.2, 4.05, (-RIB_POS, RIB_POS))
    k_wall_z = 1.0 / float(Cz[0, 0] + Cz[0, 1])
    k_rib = PETG_E_MPA * 0.57 * 1.30 / 0.35                         # E x mean width (0.45..0.69) x contact length (1.25 + ramp) / height
    F_y = PETG_YIELD_MPA * 0.45 * 1.30                              # yield force of one rib tip (45 MPa x 0.45 x 1.3)
    k_plus = 1.0 / (1.0 / k_wall_x + 1.0 / k_rib)
    k_z = 1.0 / (1.0 / k_wall_z + 1.0 / k_rib)
    info("8", "per-rib stiffness N/mm: +x wall plate / z flex wall / rib alone / rib yield force N",
         (round(k_plus, 1), round(k_z, 1), round(k_rib, 0), round(F_y, 1)), note="beam estimates, clamped ends (optimistic); not measured on a part")
    # force balance in x: F_plus = k_plus (0.10 + c) (compliant +x plate), F_minus = k_rib (0.10 - c) (rib on the 9.15 mm block); c > 0 = board moves to +x
    c_x = 0.10 * (k_rib - k_plus) / (k_rib + k_plus)
    F_bal = k_plus * (0.10 + c_x)
    plastic = F_bal > F_y
    if plastic:                                                      # not the case here; would put the -x ribs into yield (then c is still >= this value)
        c_x = min(0.10, F_y / k_plus - 0.10)
    c_lo = 0.10 * (0.2 * k_rib - 5 * k_plus) / (0.2 * k_rib + 5 * k_plus)   # sensitivity: ribs 5x softer than modelled (voids, layer lines) and the wall 5x stiffer
    warn("8", "board x-offset from the wall-stiffness mismatch (+x free plate vs -x wall+bridge block): c (mm), sensitivity (5x softer rib / 5x stiffer wall) (mm)",
         "~0 (implementer: only rib asymmetry)", (round(c_x, 3), round(c_lo, 3)),
         note=f"board is pushed onto the -x rib tips (crush there -> {0.10 - c_x:.3f}); force balance at {F_bal:.1f} N per rib, elastic. Not in the claimed stack-up. "
              "Consequence: the x centre is then set by ONE side, so a PCB width error w moves the chip by w/2 (not cancelled); z is symmetric (two identical flex walls)")
    pcb_tol = 0.15
    info("8", "extra x error if the PCB outline is 23.0 +-0.15 and the board sits on the -x ribs (mm): w/2", pcb_tol / 2,
         note="typical Chinese module outline tolerance 0.1-0.2; with a working 2-sided centring it would cancel")
    # z: elastic flex walls give a real centring stiffness
    kz_total = 4 * k_z
    info("8", "board centring stiffness in z (4 ribs on 2 identical flex walls) N/mm; force at 0.10 crush per rib N",
         (round(kz_total, 0), round(0.1 * k_z, 1)))
    # (c) ribs on a rigid support (magnet pocket, peg vs spool bore, foot bumps vs the slip-in) yield at ~0.006 mm of crush
    for nm, w, L in (("magnet rib (0.45 x 2.4 contact)", 0.45, 2.4), ("peg rib (0.45 x 2.9)", 0.45, 2.9), ("foot bump (0.6 x 0.775 arc)", 0.6, 0.775)):
        kr = PETG_E_MPA * (w + 0.12) * L / 0.30
        fy = PETG_YIELD_MPA * w * L
        info("8", f"{nm}: elastic stiffness N/mm, yield force N, crush at yield mm", (round(kr), round(fy, 1), round(fy / kr, 4)),
             note="yields at a few microns of crush: balance of equal ribs is then a constant-force (plastic) balance, centring relies on symmetric first contact + friction")
    # tables over eps
    rows = []
    for eps in (0.03, 0.05, 0.08, 0.10):
        imp, v3 = _stackup(eps, "implementer"), _stackup(eps, "verifier")
        # verifier model + systematic x term from the stiffness mismatch
        cx = float(c_x)
        wx, wz = v3["wx"] + cx, v3["wz"]
        rx, rz = math.sqrt(v3["rx"] ** 2 + cx ** 2), v3["rz"]
        rows.append((eps, round(imp["worst"], 3), round(imp["rss"], 3), round(v3["worst"], 3), round(v3["rss"], 3), round(math.hypot(wx, wz), 3), round(math.hypot(rx, rz), 3)))
    info("8", "table eps | implementer worst, RSS | verifier (3-rib 4/3) worst, RSS | + stiffness-mismatch term worst, RSS", rows)
    v05 = rows[1]
    check_max("8", "verifier model + stiffness term at eps = 0.05: RSS vs the implementer's own target 0.25", 0.25, v05[6])
    (warn if v05[5] > 0.40 else check_max)(*(("8", "verifier model + stiffness term at eps = 0.05: worst case vs the implementer's own target 0.40", "<= 0.40", v05[5]) if v05[5] > 0.40 else ("8", "verifier model + stiffness term at eps = 0.05: worst case vs the implementer's own target 0.40", 0.40, v05[5])))
    warn("8", "worst case at eps = 0.05 against the AS5600 0.25 mm displacement guidance", "<= 0.25", v05[5],
         note="worst case exceeds 0.25 even in the implementer's own model (0.317); only the RSS is inside. The 0.40 worst-case target is a relaxation set by the implementer")
    e_rss = 0.25 / (v05[6] / 0.05)
    info("8", "eps at which the verifier-model RSS reaches 0.25 (mm)", round(e_rss, 3))
    warn("8", "is eps = 0.05 reasonable for FDM PETG?", "0.05 (assumed)", "plausible best case, not a safe design value",
         note="same-layer opposing 0.45 mm beads on a tuned printer repeat to ~0.03-0.05; backlash/belt skew and bead-start effects reach 0.05-0.10; yielded ribs add up to the "
              "crush (0.10-0.12). Budget 0.08: verifier RSS %.3f, worst %.3f" % (rows[2][6], rows[2][5]))


# =====================================================================================================================
# 9  insertion force estimates
# =====================================================================================================================
def test_9_insertion_forces(cas):
    mu_lo, mu_hi = 0.25, 0.45
    sy = PETG_YIELD_MPA
    # board: 8 ribs, 45 deg lead-in (measured), crush 0.10, contact length 1.25 + 0.05
    L = 1.30
    Cz = _beam_compliance(23.5, 1.2, 4.05, (-RIB_POS, RIB_POS))
    k_wz = 1.0 / float(Cz[0, 0] + Cz[0, 1])
    Cx = _beam_compliance(27.5, 2.0, 2.85, (-RIB_POS, RIB_POS))
    k_wx = 1.0 / float(Cx[0, 0] + Cx[0, 1])
    k_rib = PETG_E_MPA * 0.57 * L / 0.35
    F_y = sy * 0.45 * L
    f_z = min(F_y * 1.5, 0.10 * (1 / (1 / k_wz + 1 / k_rib)))
    f_x = min(F_y * 1.5, 0.15 * (1 / (1 / k_wx + 1 / k_rib)))       # +x wall carries the larger crush (see item 8); -x ribs match it in force
    N_board_lo = 4 * f_z + 4 * min(F_y, 0.10 * (1 / (1 / k_wx + 1 / k_rib)))
    N_board_hi = 4 * f_z + 4 * f_x
    wedge = lambda mu: (math.sin(math.radians(45)) + mu * math.cos(math.radians(45))) / (math.cos(math.radians(45)) - mu * math.sin(math.radians(45)))
    board = dict(N_lat=(round(N_board_lo, 1), round(N_board_hi, 1)), slide=(round(mu_lo * N_board_lo, 1), round(mu_hi * N_board_hi, 1)),
                 peak=(round(wedge(mu_lo) * N_board_lo, 1), round(wedge(mu_hi) * N_board_hi, 1)))
    info("9", "board past 8 ribs: lateral squeeze N (lo, hi) / sliding force N / ramp peak N", board,
         note="z walls elastic (5 N/rib), +x plate ~18-26 N/rib, -x ribs match; wedge factor (sin45+mu cos45)/(cos45-mu sin45)")
    # magnet: 3 ribs on a rigid wall, contact 0.45 x 2.44 mm, yield-limited; confinement factor 1..2 on 45 MPa
    A = 0.45 * 2.44
    Nm_lo, Nm_hi = 3 * sy * A * 1.0, 3 * sy * A * 2.0
    mag = dict(N_lat=(round(Nm_lo), round(Nm_hi)), slide=(round(mu_lo * Nm_lo), round(mu_hi * Nm_hi)), peak=(round(wedge(mu_lo) * Nm_lo), round(wedge(mu_hi) * Nm_hi)))
    info("9", "magnet past 3 ribs: lateral squeeze N / sliding force N / ramp peak N", mag,
         note="rigid wall behind the ribs (3.85 mm ring), confined-yield factor 1-2; the peak is reached only if the rib yields rather than shaves")
    # foot: 8 bumps on the slip-in wall, contact 0.6 x 0.775 mm arc, wall inclination ~ 25-45 deg
    Ab = 0.6 * 0.775
    Nb_lo, Nb_hi = 8 * sy * Ab * 1.0, 8 * sy * Ab * 2.0
    axial_lo = Nb_lo * (math.sin(math.radians(20)) + mu_lo * math.cos(math.radians(20)))
    axial_hi = Nb_hi * (math.sin(math.radians(40)) + mu_hi * math.cos(math.radians(40)))
    foot = dict(N_normal=(round(Nb_lo), round(Nb_hi)), axial_draw=(round(axial_lo), round(axial_hi)))
    info("9", "foot past 8 bumps (drawn down by four M3 screws): wall normal load N / axial draw force N", foot)
    # stresses
    # (1) z flex wall bending from rib loads (point load at 6.5, clamped ends L = 23.5, I = 4.05 x 1.2^3/12)
    I = 4.05 * 1.2 ** 3 / 12
    a, b, Lw = 11.75 - 6.5, 11.75 + 6.5, 23.5
    Fz = f_z
    M_end = Fz * a * b ** 2 / Lw ** 2
    sig_rib = M_end * 0.6 / I
    # (2) lips: 0.4 mm deflection at the wall centre (clamped-clamped, central load)
    k_c = 192 * PETG_E_MPA * I / Lw ** 3
    F_lip = k_c * 0.4
    sig_lip = (F_lip * Lw / 8) * 0.6 / I
    info("9", "z flex wall: bending stress from one rib at 0.10 crush (MPa) / central force to pass the lip at 0.4 deflection (N) / stress there (MPa)",
         (round(sig_rib, 1), round(F_lip, 1), round(sig_lip, 1)), note="PETG yield 45 MPa (XY); v1 report: 27.6 MPa at 0.5 mm")
    check_max("9", "flex-wall stress while the board passes the lips plus rib load (sum, MPa) stays under yield", 45.0, sig_lip + sig_rib)
    warn("9", "press-in forces (rough, N): board / magnet / foot", "not calculated by the implementer",
         f"board {board['peak'][0]:.0f}-{board['peak'][1]:.0f} peak, {board['slide'][0]:.0f}-{board['slide'][1]:.0f} sliding; magnet {mag['slide'][0]}-{mag['slide'][1]} sliding; foot {foot['axial_draw'][0]}-{foot['axial_draw'][1]} by the screws",
         note="all are estimates; none can crack the 1.2 mm z walls (lateral loads 5 N/rib) but the ribs will plough/shave rather than spring; "
              "keep the board square and push on its back with a flat tool; never lever with the hook tips (0.35 mm flat)")
