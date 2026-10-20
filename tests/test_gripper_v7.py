"""
Gripper v7 gearbox redesign -- executable acceptance checks (Gate 5 style: every number is MEASURED
from the built geometry, nothing is read back from a docstring).

Covers: valid solids, centre distances, tooth counts / OD, bearing pockets (Ø14.05, n x 5.05, lip relief),
pin coaxiality and seats, static interference over the travel, gear-mesh clearance over a +-30 deg sweep,
jaw open / closed geometry, kinematic grip force, masses, Lewis safety factors, tube socket,
mesh guards, servo ear pattern, STEP round trip.

Run:  /usr/bin/python3 -m pytest -q tests/test_gripper_v7.py        (about 3-5 minutes)
"""

from __future__ import annotations

import math
import os

import numpy as np
import pytest

cq = pytest.importorskip("cadquery")

from OCP.BRepAdaptor import BRepAdaptor_Surface          # noqa: E402
from OCP.GeomAbs import GeomAbs_Cylinder                  # noqa: E402

from cad import params as P                               # noqa: E402
from cad.parts import gripper_v7_assembly as AS           # noqa: E402
from cad.parts import gripper_v7_frame as FR              # noqa: E402
from cad.parts import gripper_v7_gears as GR              # noqa: E402
from cad.parts import gripper_v7_hw as HW                 # noqa: E402
from cad.parts import gripper_v7_jaws as JW               # noqa: E402
from cad.parts import gripper_v7_kin as K                 # noqa: E402
from calculations import gripper_v7_screening as SC       # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PETG = 1.27
FB = K.default()
FB6 = K.v6_reference()
EPS_VOL = 0.5                      # mm3, interference threshold from the assignment
# fits that are interference by design: self-tapping M2 screws into Ø1.7 pilots in the pinion hub
INTENDED = {("horn_screw0", "pinion"), ("horn_screw1", "pinion"), ("horn_screw2", "pinion"),
            ("horn_screw3", "pinion")}


# ---- fixtures ---------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def closed():
    return AS.build(None, hardware=True)


@pytest.fixture(scope="module")
def printed(closed):
    return {n: s for n, (s, k) in closed.items() if k == AS.PRINTED}


def cyl_faces(shape, vertical=True):
    """Cylindrical faces with axis parallel to z: list of dicts (r, x, y, z0, z1)."""
    out = []
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() != GeomAbs_Cylinder:
            continue
        cyl = a.Cylinder()
        d = cyl.Axis().Direction()
        if vertical and abs(abs(d.Z()) - 1.0) > 1e-6:
            continue
        loc = cyl.Axis().Location()
        bb = f.BoundingBox()
        out.append(dict(r=cyl.Radius(), x=loc.X(), y=loc.Y(), z0=bb.zmin, z1=bb.zmax, area=f.Area()))
    return out


def vol(a, b):
    return a.intersect(b).Volume()


def overlaps(a, b, tol=1e-6):
    A, B = a.BoundingBox(), b.BoundingBox()
    return not (A.xmax < B.xmin - tol or B.xmax < A.xmin - tol or A.ymax < B.ymin - tol or
                B.ymax < A.ymin - tol or A.zmax < B.zmin - tol or B.zmax < A.zmin - tol)


def slab(z_mid, half=1.0, size=400.0):
    return cq.Workplane("XY").workplane(offset=z_mid - half).rect(size, size).extrude(2 * half).val()


# ---- 1. validity -------------------------------------------------------------------------------
def test_printed_parts_valid_single_solid(printed):
    for name, wp in printed.items():
        v = wp.val()
        assert v.isValid(), name
        assert len(v.Solids()) == 1, "%s has %d solids" % (name, len(v.Solids()))
        assert v.Volume() > 0


def test_hardware_valid(closed):
    for name, (wp, kind) in closed.items():
        assert wp.val().isValid(), name


# ---- 2. centre distances, tooth counts, tooth OD -------------------------------------------------
def test_centre_distances(printed):
    """Axes measured from the bearing-pocket cylinders (compound, follower) and the pilot bore (pinion)."""
    def pocket_axis(name):
        f = [c for c in cyl_faces(printed[name].val()) if abs(c["r"] - P.GRIPV7_BRG_POCKET_D / 2) < 1e-3]
        assert f, name
        xs = {(round(c["x"], 4), round(c["y"], 4)) for c in f}
        assert len(xs) == 1, "%s pocket axes differ %s" % (name, xs)
        return np.array(next(iter(xs)))
    c = pocket_axis("compound")
    fo = pocket_axis("follower")
    pil = [x for x in cyl_faces(printed["pinion"].val())
           if abs(x["r"] - (P.GRIPV7_PINION_PILOT_D / 2 + P.GRIPV7_PINION_PILOT_CLEAR)) < 1e-3]
    s = np.array((pil[0]["x"], pil[0]["y"]))
    nominal_sync = P.GRIPV7_MODULE * P.GRIPV7_Z_SYNC
    nominal_main = P.GRIPV7_MODULE * (P.GRIPV7_Z_PINION + P.GRIPV7_Z_MAIN) / 2
    assert np.linalg.norm(c - fo) == pytest.approx(nominal_sync + 0.30, abs=1e-3)       # 36.30
    assert np.linalg.norm(s - c) == pytest.approx(nominal_main + 0.30, abs=1e-3)        # 40.80
    # symmetric about the tube axis x = 0, on the y = 0 line
    assert c[0] == pytest.approx(-fo[0], abs=1e-6) and abs(c[1]) < 1e-6 and abs(fo[1]) < 1e-6
    # servo shaft offset kept from v6
    assert s[0] == pytest.approx(P.GRIPV7_SERVO_X_OFF, abs=1e-6)


def _teeth(shape, axis_xy, z0, z1, rp):
    ring = (cq.Workplane("XY").workplane(offset=z0).center(*axis_xy).circle(rp + 0.02).circle(rp - 0.02)
            .extrude(z1 - z0).val())
    return len(shape.intersect(ring).Solids())


def test_tooth_counts_and_outside_diameter(printed):
    m = P.GRIPV7_MODULE
    cases = [("pinion", GR.S_AXIS, 1.5, 15.5, 18),                      # teeth z 1..17
             ("compound", GR.C_AXIS, 2.0, 15.0, 36),                    # 36T layer z 1..17
             ("compound", GR.C_AXIS, 17.5, 21.0, 24),                   # 24T layer below the lug band (z 22.5)
             ("follower", GR.F_AXIS, 17.5, 21.0, 24)]
    for name, ax, z0, z1, z in cases:
        n = _teeth(printed[name].val(), ax, z0, z1, m * z / 2)
        assert n == z, "%s: %d teeth counted, expected %d" % (name, n, z)
    # tip circle diameters: farthest section vertex from the axis (tooth centres are not on the x/y axes)
    for name, ax, z_mid, d_expect in (("pinion", GR.S_AXIS, 9.0, 30.0), ("compound", GR.C_AXIS, 9.0, 57.0),
                                       ("compound", GR.C_AXIS, 19.0, 39.0), ("follower", GR.F_AXIS, 19.0, 39.0)):
        sl = printed[name].val().intersect(slab(z_mid, 0.5))
        r_max = max(math.hypot(v.X - ax[0], v.Y - ax[1]) for v in sl.Vertices())
        assert 2 * r_max == pytest.approx(d_expect, abs=0.02), (name, z_mid, 2 * r_max)


# ---- 3. bearing pockets, pins ------------------------------------------------------------------
def test_bearing_pockets(printed):
    r_p = P.GRIPV7_BRG_POCKET_D / 2
    r_rel = r_p + P.GRIPV7_BRG_LIP_RELIEF
    for name, top, bot, n_lo, n_up in (
            ("compound", P.GRIPV7_L2_Z1, P.GRIPV7_GEAR_Z0, GR.BRG_N_LOWER, GR.BRG_N_UPPER),
            ("follower", P.GRIPV7_L2_Z1, GR.FOLLOWER_Z0, GR.BRG_N_LOWER, GR.BRG_N_UPPER)):
        cf = cyl_faces(printed[name].val())
        pockets = [c for c in cf if abs(c["r"] - r_p) < 1e-4]
        assert len(pockets) == 2, name
        lo = min(pockets, key=lambda c: c["z0"])
        up = max(pockets, key=lambda c: c["z1"])
        depth_lo = lo["z1"] - bot                                          # pocket floor above the lower face
        depth_up = top - up["z0"]
        assert depth_lo == pytest.approx(n_lo * 5.0 + 0.05, abs=1e-4)      # 5.05
        assert depth_up == pytest.approx(n_up * 5.0 + 0.05, abs=1e-4)      # 10.05
        reliefs = [c for c in cf if abs(c["r"] - r_rel) < 1e-4]
        assert len(reliefs) == 2 and all(abs((c["z1"] - c["z0"]) - P.GRIPV7_BRG_LIP_RELIEF_DEPTH) < 1e-4 for c in reliefs)
        assert 2 * r_p == pytest.approx(14.05)
        seat = [c for c in cf if abs(c["r"] - P.GRIPV7_BRG_SEAT_BORE / 2) < 1e-4]
        assert seat, "seat bore Ø10 missing in %s" % name
    # total bearings: compound 3 + follower 3 (v6: 5; the follower gets a lower bearing)
    assert GR.BRG_N_LOWER + GR.BRG_N_UPPER == 3


def test_pin_coaxial_and_seats(printed):
    d_seat = P.GRIPV7_PIN_HOLE_D / 2
    for ax in (GR.C_AXIS, GR.F_AXIS):
        found = {}
        for name in ("lower_plate", "upper_plate", "compound", "follower"):
            for c in cyl_faces(printed[name].val()):
                if math.hypot(c["x"] - ax[0], c["y"] - ax[1]) < 1e-5 and (
                        abs(c["r"] - d_seat) < 1e-5 or abs(c["r"] - P.GRIPV7_BRG_POCKET_D / 2) < 1e-5):
                    found.setdefault(name, []).append(c)
        assert set(found) >= {"lower_plate", "upper_plate"}, "pin seats missing at %s" % (ax,)
        # seat depth >= engagement
        lp = max(found["lower_plate"], key=lambda c: c["z1"] - c["z0"])
        up = max(found["upper_plate"], key=lambda c: c["z1"] - c["z0"])
        assert (0.0 - lp["z0"]) >= P.GRIPV7_PIN_ENGAGE - 1e-6
        assert (up["z1"] - P.GRIPV7_PLATE_GAP) >= P.GRIPV7_PIN_ENGAGE - 1e-6
    # the dowel passes through the pockets of every bearing: pin bounds
    pins = {n: s.val() for n, (s, k) in AS.build(None, True).items() if n.startswith("pin_")}
    for n, p in pins.items():
        bb = p.BoundingBox()
        assert bb.zlen == pytest.approx(P.GRIPV7_PIN_LEN)
        assert bb.zmin == pytest.approx(-P.GRIPV7_PIN_ENGAGE) and bb.zmax == pytest.approx(P.GRIPV7_PLATE_GAP + P.GRIPV7_PIN_ENGAGE)
    assert P.GRIPV7_PIN_LEN in (40.0, 45.0, 50.0, 55.0, 60.0)       # ISO 2338 stock length
    # same (x, y) constants feed both plates and both gears: identical to 1e-9
    assert GR.C_AXIS[0] == -GR.F_AXIS[0]


# ---- 4. interference -----------------------------------------------------------------------------
def _interference(parts, tol=EPS_VOL):
    names = list(parts)
    shapes = {n: parts[n][0].val() for n in names}
    bad = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if parts[a][1] == AS.HARDWARE and parts[b][1] == AS.HARDWARE:
                continue
            if (a, b) in INTENDED or (b, a) in INTENDED:
                continue
            if not overlaps(shapes[a], shapes[b]):
                continue
            v = vol(shapes[a], shapes[b])
            if v > tol:
                bad.append((a, b, round(v, 2)))
    return bad


def test_static_interference_closed(closed):
    assert _interference(closed) == []


def test_hardware_vs_hardware(closed):
    """Purchased parts among themselves (bearings on pins, shoulder screws, nuts, servo/horn)."""
    names = [n for n, (s, k) in closed.items() if k != AS.PRINTED]
    shapes = {n: closed[n][0].val() for n in names}
    bad = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if overlaps(shapes[a], shapes[b]) and vol(shapes[a], shapes[b]) > EPS_VOL:
                bad.append((a, b))
    assert bad == []


@pytest.mark.parametrize("frac", [0.5])
def test_no_interference_mid_pose(frac):
    th = FB.theta_c + frac * FB.sweep
    assert _interference(AS.build(th, True)) == []


def test_no_interference_over_travel():
    """13 crank angles closed -> open, moving parts against everything else."""
    angles = np.linspace(FB.theta_c, FB.theta_open, 13)
    moving = {"compound", "follower", "pinion", "jaw_R", "jaw_L", "link_R", "link_L"}
    for th in angles:
        parts = AS.build(float(th), hardware=False)
        names = list(parts)
        sh = {n: parts[n][0].val() for n in names}
        hits = []
        for a in moving:
            for b in names:
                if b == a or (b in moving and b < a):
                    continue
                if not overlaps(sh[a], sh[b]):
                    continue
                v = vol(sh[a], sh[b])
                if v > EPS_VOL:
                    hits.append((a, b, round(v, 2)))
        assert hits == [], "crank %.1f deg: %s" % (th, hits)


# ---- 5. gear mesh clearance over a +-30 deg sweep ----------------------------------------------------
def test_gear_mesh_clearance_sweep(printed):
    """Compound turns -30 .. +30 deg about the mid pose (pinion -+60): 13 poses, both meshes."""
    th_mid = FB.theta_c + FB.sweep / 2
    d0 = th_mid - FB.theta_c
    z_main = (P.GRIPV7_L1_Z0 + P.GRIPV7_L1_Z1) / 2
    z_sync = (P.GRIPV7_L2_Z0 + 22.0) / 2                # 24T layer below the lug band
    sl_main = slab(z_main, 1.0)
    sl_sync = slab(z_sync, 1.0)
    comp_main = printed_closed("compound").intersect(sl_main)
    comp_sync = printed_closed("compound").intersect(sl_sync)
    pin = printed_closed("pinion").intersect(sl_main)
    fol = printed_closed("follower").intersect(sl_sync)
    min_gap_main, min_gap_sync = 1e9, 1e9
    for dd in np.linspace(-30.0, 30.0, 13):
        d = d0 + dd
        c_m = _rot(comp_main, GR.C_AXIS, d)
        p_m = _rot(pin, GR.S_AXIS, -P.GRIPV7_RATIO * d)
        c_s = _rot(comp_sync, GR.C_AXIS, d)
        f_s = _rot(fol, GR.F_AXIS, -d)
        assert vol(c_m, p_m) < 1e-3, "pinion/36T overlap at %+.0f deg" % dd
        assert vol(c_s, f_s) < 1e-3, "24T/24T overlap at %+.0f deg" % dd
        min_gap_main = min(min_gap_main, c_m.distance(p_m))
        min_gap_sync = min(min_gap_sync, c_s.distance(f_s))
    # printed teeth are thinned 0.10 mm each and the centre distance carries +0.30 mm
    assert min_gap_main > 0.05 and min_gap_sync > 0.05
    print("min tooth-to-tooth clearance over the sweep: main %.3f mm, sync %.3f mm" % (min_gap_main, min_gap_sync))


_CACHE = {}


def _rot(shape, axis_xy, deg):
    """Rotate a closed-pose, LP-frame shape about its own (vertical) axis."""
    return shape.rotate(cq.Vector(axis_xy[0], axis_xy[1], 0), cq.Vector(axis_xy[0], axis_xy[1], 1), deg)


def printed_closed(name):
    """Part in LP frame at the closed pose (cached build without hardware)."""
    if "parts" not in _CACHE:
        _CACHE["parts"] = AS.build(None, hardware=False)
    return _CACHE["parts"][name][0].val()


# ---- 6. jaws, four-bar, forces -----------------------------------------------------------------------
def test_jaw_closed_and_open_geometry(closed):
    jr, jl = closed["jaw_R"][0].val(), closed["jaw_L"][0].val()
    # closed: inner faces meet on the tube plane (gap 0, no overlap)
    assert jr.BoundingBox().xmin == pytest.approx(0.0, abs=1e-6)
    assert jl.BoundingBox().xmax == pytest.approx(0.0, abs=1e-6)
    assert vol(jr, jl) < 0.05
    assert FB.tip_gap(FB.pose(FB.theta_c)) == pytest.approx(0.0, abs=1e-6)
    # faces parallel to the claw axis at the closed pose; tilt over the travel small
    assert max(abs(p.tilt_deg) for p in FB.poses(60)) <= 3.0
    # open: tip-to-tip within +-10 % of v6 (97.0 mm), measured on the BUILT jaws
    op = AS.build(FB.theta_open, hardware=False)
    gap_open = op["jaw_L"][0].val().BoundingBox().xmax * -1 + op["jaw_R"][0].val().BoundingBox().xmin
    v6_open = FB6.tip_gap(FB6.pose(-14.2))
    assert v6_open == pytest.approx(97.0, abs=0.5)
    assert 0.9 * v6_open <= gap_open <= 1.1 * v6_open, "open gap %.1f vs v6 %.1f" % (gap_open, v6_open)
    # travel = servo stroke 153 deg / ratio 2
    assert FB.sweep == pytest.approx(153.0 / P.GRIPV7_RATIO, abs=1.0)
    assert 2 * FB.R * math.sin(math.radians(FB.sweep / 2)) > 0  # sanity
    # crank radius shortened from v6 R75
    assert 50.0 <= FB.R <= 56.0


def test_four_bar_never_toggles_inside_the_travel():
    """Transmission angles at A and B stay >= 25 deg and the link stays clear of the gear discs."""
    C, F = np.array(GR.C_AXIS), np.array(GR.F_AXIS)
    for p in FB.poses(60):
        a1 = _angle(p.A - C, p.B - p.A)
        a2 = _angle(p.A - p.B, FB.Pg - p.B)
        assert min(a1, 180 - a1) >= 25.0 and min(a2, 180 - a2) >= 25.0
        for g in (C, F):
            d = _seg_pt(FB.Pg, p.B, g)
            assert d >= 19.5 + JW.LINK_END_R + 1.0, d


def _angle(a, b):
    return math.degrees(math.acos(max(-1, min(1, float(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b))))))


def _seg_pt(p1, p2, q):
    d = p2 - p1
    t = float(np.clip(np.dot(q - p1, d) / np.dot(d, d), 0, 1))
    return float(np.linalg.norm(p1 + t * d - q))


def test_grip_force_vs_v6_and_requirement():
    tab = SC.force_table()
    need = SC.NEED_PER_JAW
    for vname in SC.SERVO_STALL:
        for g in (0.5, 10, 20, 40, 60, 80):
            assert SC.interp_force(tab, "v7", vname, g) >= need, (vname, g)
    # within +-10 % of v6 where the cloth is gripped (20 - 60 mm gaps) at the 4.8 V stall torque
    for g in (20, 40, 60):
        f6 = SC.interp_force(tab, "v6", "4.8 V", g)
        f7 = SC.interp_force(tab, "v7", "4.8 V", g)
        assert abs(f7 / f6 - 1.0) <= 0.10, "gap %d mm: v7 %.1f N vs v6 %.1f N" % (g, f7, f6)


# ---- 7. strength ----------------------------------------------------------------------------------------
def test_lewis_safety_factors():
    rows = SC.tooth_table(P.GRIPV7_RATIO, P.GRIPV7_Z_MAIN, P.GRIPV7_MODULE, P.GRIPV7_FACE_MAIN,
                          P.GRIPV7_FACE_SYNC, "v7")
    for r in rows:
        if r["servo"] == "6.0 V":
            assert r["SF"] >= 1.5, r
    pin6 = next(r for r in rows if r["servo"] == "6.0 V" and r["gear"] == "pinion 18T")
    syn6 = next(r for r in rows if r["servo"] == "6.0 V" and r["gear"] == "sync 24T, one jaw takes all")
    assert pin6["SF"] == pytest.approx(2.09, abs=0.02)          # unchanged pinion (R5: 2.1)
    assert syn6["SF"] > 1.33                                    # v6 worst case was 1.33


def test_gear_web_rim_and_spokes(printed):
    comp = printed["compound"].val()
    root36 = GR.root_r(36)
    rim = root36 - GR.WINDOW_R_OUT
    assert rim >= 2.5 * P.GRIPV7_MODULE
    assert P.GRIPV7_SPOKES >= 5
    # measured: windows in a section of the 36T layer
    sec = comp.intersect(slab(9.0, 0.05))
    faces = sec.Faces()
    big = max(faces, key=lambda f: f.Area())
    n_inner = len(big.innerWires())
    assert n_inner == P.GRIPV7_SPOKES + 1                       # six windows + the bearing seat bore
    # full face width at the teeth: tooth ring spans the whole 16 mm layer
    ring = (cq.Workplane("XY").workplane(offset=P.GRIPV7_L1_Z0 + 0.01).center(*GR.C_AXIS)
            .circle(27.0 + 1.0).circle(27.0 - 1.0).extrude(P.GRIPV7_FACE_MAIN - 0.02).val())
    inter = comp.intersect(ring)
    assert inter.BoundingBox().zlen == pytest.approx(P.GRIPV7_FACE_MAIN - 0.02, abs=1e-3)


# ---- 8. masses ------------------------------------------------------------------------------------------
def test_masses(printed):
    m = {n: s.val().Volume() * PETG / 1000.0 for n, s in printed.items()}
    # v6 CAD-solid: compound 116 g, follower 32 g, pinion 10 g
    assert m["compound"] < 116.0 * 0.6
    assert m["follower"] <= 32.0
    assert m["pinion"] <= 20.0
    frame = m["lower_plate"] + m["upper_plate"]
    assert frame <= 150.0, "frame %.1f g" % frame
    for n in ("jaw", "link"):
        pass
    assert printed["jaw_R"].val().Volume() * PETG / 1000.0 <= 38.0 * 1.05
    assert printed["link_R"].val().Volume() * PETG / 1000.0 <= 8.0 * 1.1


# ---- 9. frame: servo, plates, tube socket, guards ---------------------------------------------------------
def test_servo_ear_holes_and_cutout(printed):
    up = printed["upper_plate"].val()
    ins = [c for c in cyl_faces(up) if abs(c["r"] - P.GRIPV7_SERVO_INSERT_D / 2) < 1e-4]
    pts = sorted((round(c["x"], 3), round(c["y"], 3)) for c in ins)
    sx, sy = GR.S_AXIS
    cx = sx - P.GRIPV7_SERVO_X_OFF
    want = sorted((round(cx + a * P.GRIPV7_SERVO_EAR_HOLE_DX / 2, 3), round(sy + b * P.GRIPV7_SERVO_EAR_HOLE_DY / 2, 3))
                  for a in (-1, 1) for b in (-1, 1))
    assert pts == want
    # v6 ear pattern: 47 x 10 mm (verification/gripper_v6_inspection.md)
    assert P.GRIPV7_SERVO_EAR_HOLE_DX == 47.0 and P.GRIPV7_SERVO_EAR_HOLE_DY == 10.0
    # body cutout passes the MG996R body with clearance and the ears rest on the top face
    servo = AS.build(None, True)["servo"][0].val()
    assert vol(servo, up) < EPS_VOL
    assert servo.BoundingBox().zmax > FR.UP_Z1
    # ear underside sits on the plate top face
    ear_bottom = P.GRIPV7_SERVO_BOSS_Z + P.GRIPV7_SERVO_EAR_DROP
    assert ear_bottom == pytest.approx(FR.UP_Z1)
    # servo axis orientation kept: shaft points -z, body above
    sb = servo.BoundingBox()
    assert sb.zmin < P.GRIPV7_SERVO_BOSS_Z < sb.zmax


def test_pinion_horn_drive(printed):
    pin = printed["pinion"].val()
    pil = [c for c in cyl_faces(pin) if abs(c["r"] - P.GRIPV7_HORN_SCREW_PILOT_D / 2) < 1e-4]
    assert len(pil) == P.GRIPV7_HORN_SCREWS
    for c in pil:
        assert math.hypot(c["x"] - GR.S_AXIS[0], c["y"] - GR.S_AXIS[1]) == pytest.approx(P.GRIPV7_HORN_SCREW_R, abs=1e-6)
    # hub top = horn disc underside (pinion drive bolted to the horn, no bore on the shaft)
    z_top = pin.BoundingBox().zmax
    horn = AS.build(None, True)["horn"][0].val()
    assert z_top == pytest.approx(horn.BoundingBox().zmin, abs=1e-6)
    # servo shaft and pinion are NOT coupled through a bore: no bore at the shaft radius in the pinion
    assert not [c for c in cyl_faces(pin) if abs(c["r"] - P.GRIPV7_SERVO_SHAFT_D / 2) < 0.2 and c["area"] > 20]


def test_tube_socket(closed, printed):
    lp, up = printed["lower_plate"].val(), printed["upper_plate"].val()
    tube = closed["tube"][0].val()
    # bore: Ø28.54 + 2 x 0.15 along y, axis on x = 0, z = tube z
    bores = []
    for sh in (lp, up):
        for f in sh.Faces():
            a = BRepAdaptor_Surface(f.wrapped)
            if a.GetType() == GeomAbs_Cylinder and abs(a.Cylinder().Radius() - (P.GRIPV7_TUBE_OD / 2 + P.GRIPV7_TUBE_FIT)) < 1e-4:
                d = a.Cylinder().Axis().Direction()
                assert abs(abs(d.Y()) - 1.0) < 1e-6
                loc = a.Cylinder().Axis().Location()
                assert abs(loc.X()) < 1e-6 and abs(loc.Z() - P.GRIPV7_TUBE_Z) < 1e-6
                bores.append(f.BoundingBox())
    assert bores
    y0 = min(b.ymin for b in bores)
    y1 = max(b.ymax for b in bores)
    assert y0 == pytest.approx(P.GRIPV7_TUBE_END_Y, abs=1e-3)
    assert y1 - y0 == pytest.approx(P.GRIPV7_TUBE_INSERT, abs=1e-3)          # v6 insertion depth 42.5
    assert vol(tube, lp) < EPS_VOL and vol(tube, up) < EPS_VOL
    # cross-bolt: one Ø3.4 axis parallel to z through plates, saddles AND the tube wall
    xb = (0.0, P.GRIPV7_TUBE_END_Y + P.GRIPV7_XBOLT_Y_FROM_END)
    for sh in (lp, up, tube):
        hole = [c for c in cyl_faces(sh) if abs(c["r"] - P.GRIPV7_XBOLT_HOLE_D / 2) < 1e-4
                and math.hypot(c["x"] - xb[0], c["y"] - xb[1]) < 1e-6]
        assert hole, "cross-bolt hole missing"
    # tube end distance to the cross hole (tear-out) >= 3 x hole diameter
    assert P.GRIPV7_XBOLT_Y_FROM_END >= 3 * P.GRIPV7_XBOLT_HOLE_D
    # carries the full claw load in tension: SF >= 5 on a 100 N design load
    sk = SC.socket_tension_check(100.0)
    assert sk["SF"] >= 5.0, sk
    # >= 4 tie standoffs/bolts
    assert len(P.GRIPV7_TIE_XY) >= 4


def test_ties_and_columns(printed):
    lp = printed["lower_plate"].val()
    for t in P.GRIPV7_TIE_XY:
        cols = [c for c in cyl_faces(lp) if abs(c["r"] - P.GRIPV7_TIE_COL_OD / 2) < 1e-4
                and math.hypot(c["x"] - t[0], c["y"] - t[1]) < 1e-6]
        assert cols and max(c["z1"] for c in cols) == pytest.approx(P.GRIPV7_PLATE_GAP)
        assert [c for c in cyl_faces(lp) if abs(c["r"] - P.GRIPV7_TIE_HOLE_D / 2) < 1e-4
                and math.hypot(c["x"] - t[0], c["y"] - t[1]) < 1e-6]


def _wall_thickness(section_face_area, perimeter):
    h = perimeter / 2.0
    return (h - math.sqrt(max(h * h - 4 * section_face_area, 0.0))) / 2.0


def test_mesh_guards(printed):
    lp, up = printed["lower_plate"].val(), printed["upper_plate"].val()
    # main-mesh guard on the lower plate: section at z = 8 outside the plate/columns region
    for name, shape, z in (("main", lp, 8.0), ("sync", up, 33.5)):
        sec = shape.intersect(slab(z, 0.02))
        walls = [f for f in sec.Faces() if f.Area() < 400 and f.Area() > 5]
        assert walls, name
        ts = []
        for f in walls:
            w = f.outerWire()
            per = sum(e.Length() for e in w.Edges())
            if per / f.Area() > 1.0:                    # thin strip, not a boss
                ts.append(_wall_thickness(f.Area(), per))
        assert ts, name
        for t in ts:
            assert 1.2 - 0.02 <= t <= 1.6 + 0.02, (name, t)
    # guards stand clear of the gear tips by the design clearance
    pin, c36 = printed["pinion"].val(), printed["compound"].val()
    assert vol(lp, c36) < 1e-3 and vol(lp, pin) < 1e-3
    g = FR.main_guard()
    assert g.val().distance(c36) >= P.GRIPV7_GUARD_CLEAR - 0.05
    assert g.val().distance(pin) >= P.GRIPV7_GUARD_CLEAR - 0.05


# ---- 10. interfaces and datums kept from v6 ----------------------------------------------------------------------
def test_v6_interfaces_kept(closed):
    # tube axis (x, z) and lower end in the v6 world frame
    ox, oy, oz = P.GRIPV7_WORLD_ORIGIN
    tube = AS.to_world(closed["tube"][0]).val().BoundingBox()
    assert (tube.xmin + tube.xmax) / 2 == pytest.approx(951.8475, abs=1e-3)
    assert (tube.zmin + tube.zmax) / 2 == pytest.approx(1103.99, abs=1e-2)
    assert tube.ymin == pytest.approx(786.39, abs=2e-2)
    # gear stack z-range same as v6 (1080.49 .. 1116.49)
    comp = AS.to_world(closed["compound"][0]).val().BoundingBox()
    assert comp.zmin == pytest.approx(1080.49, abs=1e-6) and comp.zmax == pytest.approx(1116.49, abs=1e-6)
    # jaw pivot axes: 6 (2 crank pins + 2 link pins on the jaws + 2 frame pivots), as v6
    pivots = [n for n in closed if n.startswith("sh_")]
    assert len(pivots) == 6


# ---- 11. STEP round trip ---------------------------------------------------------------------------------------
def test_step_round_trip(printed, tmp_path):
    for name in ("pinion", "compound", "jaw_R", "lower_plate"):
        shp = printed[name].val()
        path = str(tmp_path / (name + ".step"))
        cq.exporters.export(printed[name], path)
        re = cq.importers.importStep(path).val()
        assert re.isValid() and len(re.Solids()) == 1
        assert re.Volume() == pytest.approx(shp.Volume(), rel=2e-4)
        a, b = shp.BoundingBox(), re.BoundingBox()
        for u, v in ((a.xmin, b.xmin), (a.xmax, b.xmax), (a.ymin, b.ymin), (a.ymax, b.ymax), (a.zmin, b.zmin), (a.zmax, b.zmax)):
            assert u == pytest.approx(v, abs=1e-3)


def test_exported_files_present_if_built():
    step_dir = os.path.join(REPO, "exports", "step")
    pre = os.path.join(step_dir, "gripper_v7_preview.step")
    if not os.path.exists(pre):
        pytest.skip("run scripts/build_gripper_v7.py first")
    asm = cq.importers.importStep(pre)
    solids = asm.solids().vals()
    names = ("lower_plate", "upper_plate", "pinion", "compound", "follower", "jaw", "link")
    for n in names:
        assert os.path.exists(os.path.join(step_dir, "gripper_v7_%s.step" % n))
        assert os.path.exists(os.path.join(REPO, "exports", "stl", "gripper_v7_%s.stl" % n))
    # preview contains the v7 parts, the tube, the v6 cylinder reference and the camera-bay box
    assert len(solids) >= len(AS.build(None, True)) + 2
    bb = cq.Compound.makeCompound(solids).BoundingBox()
    assert bb.ymax > 1150.0 and bb.ymin < 600.0           # jaws at the bottom, box at the top
