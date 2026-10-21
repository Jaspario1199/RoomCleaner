"""
Gripper v6r -- Jasper's own 18T pinion (Simple_18T_Pinionvlast) with ONE 687 bearing pocket, bottom face (z = 0)
= the face AWAY from the servo shaft.  Nothing is designed here: the pocket is his own one-bearing pocket from the
lower layer of his compound (06_compound_54T_24T), measured from his solid and reproduced.

Donor pocket (his compound, part frame z = 0 at the stack bottom; his world Z 1082.44 .. 1087.49 is the R7.0375 part):
  z 0 .. 1.95        entry lip: 8 arc segments on R7.000 (D14.000) separated by 8 relief notches (R0.25 corner
                     fillets, notch outer extent about R7.80).  Not axisymmetric, so it cannot be a pure revolve.
  z 1.95 .. 7.00     pocket R7.0375 (D14.075), 5.05 deep, flat floor (no chamfer, no cone, no fillet anywhere)
  z 7.00 ..          floor opening R4.15 (D8.30): the inner race of a 687 does not bear on the rotating gear.

Reproduction in his pinion frame (his compound and his pinion are both re-homed: axis on z, stack bottom z = 0, his
orientation, so the pocket lands on the pinion axis with his own angular phase):
  * pocket R7.0375 / floor R4.15 / D8.30 counterbore  -> REVOLVE of the measured profile
  * entry lip slab z 0 .. 1.95                         -> copied from his solid: (cylinder R_COPY) minus (his compound),
    which is an exact planar / cylindrical copy (every face of the result is a plane or a cylinder of his).
Everything else of the pinion (teeth, 16 mm face, D8.00 bore) is his, untouched.

D8.30 counterbore depth.  In the compound the D8.30 bore runs through the whole web.  In the pinion the D8.00 bore must
stay on the servo side (the D6 shaft enters it from z = 16 and engages 4 mm), so the D8.30 section stops where that
engagement starts: z = FACE - SHAFT_ENGAGE = 12.  That end plane is the only number not measured from his compound
(derived from his servo-shaft engagement length in verification/gripper_v6_inspection.md).
"""

from __future__ import annotations

import math
from functools import lru_cache

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Plane, GeomAbs_Torus

from cad import params as P
from cad.parts import gripper_v6r_gears as G

# ---------------------------------------------------------------------------------------------------------------
# constants (mm).  Pocket numbers are NOT typed in: they are measured from his compound (measure_pocket()) and
# compared with these reference values only as a sanity check by the build / tests.
# ---------------------------------------------------------------------------------------------------------------
SHAFT_ENGAGE = 4.0                    # his servo shaft engagement in the pinion bore (inspection report)
FACE = P.GRIPV6R_L1_Z1                # 16.0, pinion face width
BORE_RELIEF_TOP_Z = FACE - SHAFT_ENGAGE   # 12.0, top of the D8.30 counterbore
R_COPY = 9.0                          # radius of the cylinder used to copy the donor cavity (> notch extent R7.80)
Z_COPY_BELOW = 1.0                    # copy starts this far below z = 0 (clear of his bottom face)
BRG_D, BRG_W = 7.0, 5.0               # 687: 7 x 14 x 5
BRG_OD = P.GRIPV6R_BRG_OD


def _cylinders(shape: cq.Shape):
    """On-axis cylinders: [(R, z0, z1, area)], area summed over seam-split faces, keyed by (R, z0, z1)."""
    acc = {}
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() != GeomAbs_Cylinder:
            continue
        loc = a.Cylinder().Axis().Location()
        if math.hypot(loc.X(), loc.Y()) > 0.01:
            continue
        b = f.BoundingBox()
        key = (round(a.Cylinder().Radius(), 5), round(b.zmin, 4), round(b.zmax, 4))
        acc[key] = acc.get(key, 0.0) + f.Area()
    return acc


def measure_pocket(shape: cq.Shape, z_max: float = 12.5) -> dict:
    """Pocket profile measured from a shape whose pocket mouth is the z = 0 face (axis on z).  Only the region
    z <= z_max and R <= R_COPY is read.  Returns the axisymmetric profile and the lip / notch census.

    keys: pocket_R, pocket_z (z0, z1), pocket_depth, lip_R, lip_len, lip_segments, lip_ledge_z, bore_R, bore_z,
          notch_fillet_R, notch_count, notch_outer_R, floor_z, forbidden (chamfer / cone / torus faces in the region)
    """
    cyl = _cylinders(shape)
    # --- axisymmetric cylinders in the region -------------------------------------------------------------------
    inreg = {k: v for k, v in cyl.items() if k[1] <= z_max and k[0] < R_COPY}
    lip = {k: v for k, v in inreg.items() if abs(k[0] - 7.0) < 0.01}
    pocket = {k: v for k, v in inreg.items() if abs(k[0] - 7.0375) < 0.01 and k[1] < 2.0}
    bore = {k: v for k, v in inreg.items() if 4.1 < k[0] < 4.2}
    if not lip or not pocket or not bore:
        raise RuntimeError("pocket not found: lip %s pocket %s bore %s" % (lip, pocket, bore))
    lk, pk = sorted(lip)[0], sorted(pocket)[0]
    bk = sorted(bore)[0]
    # --- notch census: off-axis R0.25 cylinders in the lip slab ---------------------------------------------------
    n_fil, n_out = set(), 0.0
    forbidden = 0
    for f in shape.Faces():
        b = f.BoundingBox()
        if b.zmin > z_max or max(abs(b.xmin), abs(b.xmax), abs(b.ymin), abs(b.ymax)) > R_COPY + 0.5:
            continue
        a = BRepAdaptor_Surface(f.wrapped)
        t = a.GetType()
        if t in (GeomAbs_Cone, GeomAbs_Torus):
            forbidden += 1
        if t == GeomAbs_Cylinder and abs(a.Cylinder().Radius() - 0.25) < 1e-3 and b.zmax <= 2.0:
            loc = a.Cylinder().Axis().Location()
            n_fil.add((round(loc.X(), 3), round(loc.Y(), 3)))
        if t == GeomAbs_Cylinder and b.zmax <= 2.0 and a.Cylinder().Radius() < 1.0:
            n_out = max(n_out, max(abs(b.xmin), abs(b.xmax), abs(b.ymin), abs(b.ymax)))
    # floor: planar face at z = pocket z1 with normal pointing into the pocket
    floor_z = pk[2]
    return dict(
        pocket_R=pk[0], pocket_z=(pk[1], pk[2]), pocket_depth=pk[2] - pk[1],
        lip_R=lk[0], lip_len=lk[2] - lk[1], lip_z=(lk[1], lk[2]), lip_segments=_count_lip_segments(shape, lk), lip_ledge_z=pk[1],
        bore_R=bk[0], bore_z=(bk[1], bk[2]),
        notch_fillet_R=0.25, notch_fillet_axes=len(n_fil), notch_outer_extent=n_out,
        floor_z=floor_z, forbidden=forbidden, cyl_keys=sorted(inreg))


def _count_lip_segments(shape: cq.Shape, lk) -> int:
    """Number of distinct R7.000 arc faces of the lip (counted by their mid-angle, immune to seam splitting)."""
    ang = set()
    for f in shape.Faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() != GeomAbs_Cylinder or abs(a.Cylinder().Radius() - lk[0]) > 1e-3:
            continue
        b = f.BoundingBox()
        if b.zmin < lk[1] - 1e-3 or b.zmax > lk[2] + 1e-3:
            continue
        ang.add(round(math.degrees(math.atan2((b.ymin + b.ymax) / 2, (b.xmin + b.xmax) / 2)) % 360.0, 0))
    return len(ang)


# ---------------------------------------------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def donor_profile() -> dict:
    return measure_pocket(G.home_compound())


@lru_cache(maxsize=1)
def donor_cavity() -> cq.Shape:
    """His entry lip slab as a solid: (cylinder R_COPY, z -1 .. 1.95) minus his compound.  Exact copy of the lip
    (z 0..1.95, 8 segments R7.000 + 8 relief notches); the part below z = 0 lies outside his body."""
    z_lip = donor_profile()["lip_len"]            # measured: 1.95 (top of the lip slab = ledge plane of his pocket)
    cyl = cq.Solid.makeCylinder(R_COPY, Z_COPY_BELOW + z_lip, cq.Vector(0, 0, -Z_COPY_BELOW))
    cav = cyl.cut(G.home_compound())
    sol = cav.Solids()
    if len(sol) != 1:
        raise RuntimeError("donor cavity has %d solids" % len(sol))
    return sol[0]


def revolved_profile(p: dict, z_top: float = BORE_RELIEF_TOP_Z) -> cq.Shape:
    """The axisymmetric part of the pocket, REVOLVED from the measured profile (x = radius, y = z):
    R_pocket from the lip ledge up to the floor, floor annulus to R_bore, D8.30 counterbore up to z_top."""
    rp, zf, rb, z0 = p["pocket_R"], p["floor_z"], p["bore_R"], p["lip_ledge_z"]
    pts = [(0.0, z0), (rp, z0), (rp, zf), (rb, zf), (rb, z_top), (0.0, z_top)]
    w = cq.Workplane("XZ").polyline(pts).close().revolve(360.0, (0, 0, 0), (0, 1, 0))
    return w.val()


@lru_cache(maxsize=1)
def make_pinion_1brg() -> cq.Shape:
    """His pinion + his one-bearing pocket in the bottom face (single clean solid, faces unified)."""
    p = donor_profile()
    pin = G.home_pinion()
    s = pin.cut(donor_cavity()).cut(revolved_profile(p))
    s = G.unify(s)
    return G._single_solid(s, "pinion_1brg")


def removed_material() -> cq.Shape:
    """His pinion minus the new part (must equal the pocket and nothing else)."""
    return G.home_pinion().cut(make_pinion_1brg())


def added_material() -> float:
    """Volume of new minus his (must be 0)."""
    r = make_pinion_1brg().cut(G.home_pinion())
    return float(r.Volume()) if r.Solids() else 0.0


def print_pose_pocket_up(shape: cq.Shape) -> cq.Shape:
    """Printed pocket-side UP: flip 180 deg about x so the pocket face (z = 0) is on top, teeth / servo face (z = 16) on the
    bed, lowest point z = 0.  Independent copy."""
    flipped = G.deep_copy(shape).rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 180.0)
    return flipped.moved(cq.Location(cq.Vector(0, 0, -flipped.BoundingBox().zmin)))


def walls(p: dict) -> dict:
    """Radial wall between the pocket and the 18T root circle."""
    root = G.root_r(P.GRIPV6R_Z_PINION)
    return dict(root_r=root, pocket_wall=root - p["pocket_R"], lip_wall=root - p["lip_R"],
                notch_wall=root - p["notch_outer_extent"])


# ---------------------------------------------------------------------------------------------------------------
# checks against the donor
# ---------------------------------------------------------------------------------------------------------------
def cavity_in(shape: cq.Shape, z0: float, z1: float) -> cq.Shape:
    """Empty space of `shape` inside the cylinder R_COPY, z0..z1 (the pocket as a solid)."""
    return cq.Solid.makeCylinder(R_COPY, z1 - z0, cq.Vector(0, 0, z0)).cut(shape)


def pocket_vs_donor(shape: cq.Shape, z_probe: float = 6.5) -> dict:
    """Symmetric difference (mm3) of the pocket cavities of `shape` and of his compound over z -1 .. z_probe
    (lip slab + R7.0375 pocket to 1.5 mm above the bearing seat), and the largest profile-number difference (mm)."""
    a = cavity_in(shape, -Z_COPY_BELOW, z_probe)
    b = cavity_in(G.home_compound(), -Z_COPY_BELOW, z_probe)
    d1, d2 = a.cut(b), b.cut(a)
    v = lambda s: float(s.Volume()) if s.Solids() else 0.0
    pa, pb = measure_pocket(shape), donor_profile()
    num = ("pocket_R", "pocket_depth", "lip_R", "lip_len", "lip_ledge_z", "bore_R", "notch_outer_extent")
    diffs = {k: abs(pa[k] - pb[k]) for k in num}
    diffs.update({"pocket_z%d" % i: abs(pa["pocket_z"][i] - pb["pocket_z"][i]) for i in (0, 1)})
    diffs["floor_z"] = abs(pa["floor_z"] - pb["floor_z"])
    return dict(cavity_volume_new=float(a.Volume()), cavity_volume_donor=float(b.Volume()),
                sym_diff_mm3=v(d1) + v(d2), profile_diffs_mm=diffs, max_profile_diff_mm=max(diffs.values()),
                same_counts=bool(pa["lip_segments"] == pb["lip_segments"] and pa["notch_fillet_axes"] == pb["notch_fillet_axes"]
                                 and pa["forbidden"] == pb["forbidden"] == 0))


def mesh_overlap_3d(deltas, compound: str = "compound") -> list:
    """Boolean common volume (mm3) of the new pinion with the v6r 36T compound (and the follower) at the 40.80 mm centre
    distance for each crank offset delta (deg; pinion turns -2 delta)."""
    pin = make_pinion_1brg()
    comp, fol = G.part(compound), G.part("follower")
    rows = []
    for d in deltas:
        pp = G.place(pin, P.GRIPV6R_S_XY, -P.GRIPV6R_SWEEP_PINION_RATIO * d)
        rows.append(dict(delta_deg=float(d),
                         pinion_compound=G.common_volume(pp, G.place(comp, P.GRIPV6R_C_XY, d)),
                         pinion_follower=G.common_volume(pp, G.place(fol, P.GRIPV6R_F_XY, -d))))
    return rows


def mesh_control(extra_deg: float = 3.0) -> float:
    """Positive control: the new pinion turned `extra_deg` off the clearance window must overlap the 36T ring."""
    pp = G.place(make_pinion_1brg(), P.GRIPV6R_S_XY, extra_deg)
    return G.common_volume(pp, G.place(G.part("compound"), P.GRIPV6R_C_XY, 0.0))
