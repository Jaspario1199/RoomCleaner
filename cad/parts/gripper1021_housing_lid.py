"""
GRIPPER 1021 HOUSING LID: a light press-fit lid for the open top of the claw's electrical housing, exports/step/gripper1021_housing_cambay_34.step.

Frame: the housing's BAY frame (origin on the tube axis in the box bottom plane, axes parallel to the world axes, +y up) = world minus
CAMBAY1021_BAY_ORIGIN_WORLD.  The STEP export is in the world frame like the housing, the STL in print orientation.

Opening and seat, MEASURED from that STEP (cad/params.py LID1021_*; spec text says only "lid seat 50.0, top 55.0"):
    the open top is an 85 x 85 recess with R12.5 corners (corner centres at +-30), y 50 .. 55; its floor is a 2.5 mm wide seat ring at y = 50
    around the 80 x 80 R10 pocket, which is open down to y = 5.  Nothing else stands in the recess.
Lid (one printed part, no screws):
    * plate 1.8 mm thick on the seat ring, outline = recess offset by 0.25 (R12.25 corners), top face 3.2 mm below the rim, top edge chamfered 0.3;
    * four crush bumps, one per side, each on the end of an in-plane cantilever arm (arm 2.0 x 8 mm free length, freed by a 1 mm L-shaped slot).
      Tip 0.6 wide, standing 0.40 beyond the plate edge = 0.25 clearance + 0.15 interference with the wall.  A rigid plate with rigid bumps cannot
      be pressed into a rigid recess (0.3 mm of shortening across 85 mm of 1.8 mm plate would buckle it long before it pressed in); the arms turn
      the 0.15 mm interference into about 2 N per bump (strain 0.7 %, in the layer plane), independent of FDM size error;
    * 45 deg lead-in on the underside of each bump (the lid goes in underside first);
    * pry notch on the +z side: 14 x 4.5 mm, 2.25 mm of it past the seat ring over the open pocket, so a blade or fingertip reaches under the plate edge.
Print: top face down on the bed; every wall is vertical and the only slanted faces (bump lead-ins, top chamfer) face up or sit on the bed.
"""

from __future__ import annotations

import math
import os

import cadquery as cq

from .. import params as P

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STEP_DIR = os.path.join(_REPO, "exports", "step")
STL_DIR = os.path.join(_REPO, "exports", "stl")
RENDER_DIR = os.path.join(_REPO, "renders", "gripper1021_lid")
HOUSING_STEP = os.path.join(STEP_DIR, "gripper1021_housing_cambay_34.step")
COVER_STEP = os.path.join(STEP_DIR, "gripper1021_housing_cambay_cover.step")
LID_NAME = "gripper1021_housing_lid"
ORIGIN = P.CAMBAY1021_BAY_ORIGIN_WORLD

OVERSHOOT = 1.0          # mm, cutter overshoot beyond a cut face
FUSE = 0.3               # mm, bump base sunk into its arm


class Cfg:
    """Derived sizes, read from cad/params.py at call time."""

    def __init__(self):
        p = P
        self.seat_y, self.rim_y = p.LID1021_SEAT_Y, p.LID1021_RIM_Y
        self.rh, self.rr, self.rc = p.LID1021_RECESS_HALF, p.LID1021_RECESS_R, p.LID1021_RECESS_CORNER_C
        self.ph, self.pr = p.LID1021_POCKET_HALF, p.LID1021_POCKET_R
        self.t, self.clear, self.interf = p.LID1021_THICK, p.LID1021_SIDE_CLEAR, p.LID1021_INTERF
        self.chamfer = p.LID1021_TOP_CHAMFER
        self.H = self.rh - self.clear                         # plate half size 42.25
        self.R = self.rr - self.clear                         # plate corner radius 12.25 (concentric with the recess corners)
        self.top_y = self.seat_y + self.t
        self.bump_p = self.clear + self.interf                # bump tip stands this far beyond the plate edge: 0.40
        self.bump_tip, self.bump_base = p.LID1021_BUMP_TIP, p.LID1021_BUMP_BASE
        self.arm_t, self.slot = p.LID1021_ARM_T, p.LID1021_SLOT
        self.x_root, self.x_free, self.x_bump = p.LID1021_ARM_ROOT_X, p.LID1021_ARM_FREE_X, p.LID1021_BUMP_X
        self.notch_w, self.notch_d, self.notch_r, self.notch_x = p.LID1021_NOTCH
        self.keepout = p.LID1021_KEEPOUT
        self.mu = p.LID1021_FRICTION
        assert self.bump_tip >= 0.45 - 1e-9, "bump tip below 0.45 mm"
        assert self.interf > 0 and self.clear > 0 and self.t >= 1.2
        assert self.x_free < self.x_bump < self.x_root and self.x_bump + self.bump_base / 2 < self.x_root
        assert self.x_bump - self.bump_base / 2 > self.x_free - self.slot, "bump must sit on the arm"
        assert self.H - self.arm_t - self.slot > self.ph - 2.0, "arm slots must not reach far into the pocket void"
        assert abs(self.notch_x) + self.notch_w / 2 <= self.rc - 1.0, "notch on the straight part of the +z edge"
        assert not (self.x_free - self.slot < self.notch_x + self.notch_w / 2 and self.x_root > self.notch_x - self.notch_w / 2), "notch overlaps the +z arm"
        assert self.chamfer < self.t / 2
        assert self.top_y < self.rim_y - 1.0, "lid top must stay below the rim"


# =============================================================================================================================
# the housing and the other reference solids (bay frame)
# =============================================================================================================================
def _load(path: str, corrected: bool):
    s = cq.importers.importStep(path).val()
    dx, dy, dz = P.LID1021_REF_RESIDUAL if corrected else (0.0, 0.0, 0.0)
    return s.translate(cq.Vector(-ORIGIN[0] - dx, -ORIGIN[1] - dy, -ORIGIN[2] - dz))


def load_housing(corrected: bool = True) -> cq.Shape:
    """exports/step/gripper1021_housing_cambay_34.step in the bay frame; corrected=True removes the 1e-5 mm placement residual of its seat / recess."""
    return _load(HOUSING_STEP, corrected)


def load_cover() -> cq.Shape:
    return _load(COVER_STEP, False)


def measure_opening(housing: cq.Shape | None = None) -> dict:
    """Opening, seat and rim read from the faces of the housing STEP: dict of seat_y, rim_y, recess_half (x, z), recess_r, corner_c, pocket_half, pocket_r."""
    h = load_housing(False) if housing is None else housing
    out = {}
    ring = [f for f in h.Faces() if f.geomType() == "PLANE" and abs(f.normalAt().y - 1.0) < 1e-6 and 760 < f.Area() < 800]
    assert len(ring) == 1, "seat ring (plane, normal +y, 777 mm2) not found"
    b = ring[0].BoundingBox()
    out["seat_y"] = b.ymin
    out["recess_half_x"] = (b.xmax - b.xmin) / 2
    out["recess_half_z"] = (b.zmax - b.zmin) / 2
    out["centre_x"], out["centre_z"] = (b.xmax + b.xmin) / 2, (b.zmax + b.zmin) / 2
    rim = [f for f in h.Faces() if f.geomType() == "PLANE" and abs(f.normalAt().y - 1.0) < 1e-6 and 900 < f.Area() < 950]
    assert len(rim) == 1, "rim top face not found"
    out["rim_y"] = rim[0].BoundingBox().ymin
    walls = [f for f in h.Faces() if f.geomType() == "CYLINDER" and abs(f._geomAdaptor().Cylinder().Radius() - 12.5) < 1e-3
             and abs(f.BoundingBox().ymin - out["seat_y"]) < 1e-3]
    assert len(walls) == 4, "four R12.5 recess corners expected"
    out["recess_r"] = walls[0]._geomAdaptor().Cylinder().Radius()
    out["corner_c"] = sorted(round(abs(f._geomAdaptor().Cylinder().Location().X()), 3) for f in walls)[0]
    pk = [f for f in h.Faces() if f.geomType() == "CYLINDER" and abs(f._geomAdaptor().Cylinder().Radius() - 10.0) < 1e-3
          and abs(f.BoundingBox().ymax - out["seat_y"]) < 1e-3 and abs(f.BoundingBox().ymin - 5.0) < 1e-3]
    assert len(pk) == 4, "four R10 pocket corners expected"
    out["pocket_r"] = pk[0]._geomAdaptor().Cylinder().Radius()
    out["pocket_corner_c"] = sorted(round(abs(f._geomAdaptor().Cylinder().Location().X()), 3) for f in pk)[0]
    out["pocket_half"] = out["pocket_corner_c"] + out["pocket_r"]
    return out


# =============================================================================================================================
# the lid
# =============================================================================================================================
def _plane_y(y0: float) -> cq.Plane:
    """Plane normal to +y at y0; local u = +x, local v = -z."""
    return cq.Plane(origin=(0, y0, 0), xDir=(1, 0, 0), normal=(0, 1, 0))


def _box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def _rot(wp: cq.Workplane, ang: float) -> cq.Workplane:
    return wp.rotate((0, 0, 0), (0, 1, 0), ang)


def _arm_slots(c: Cfg) -> cq.Workplane:
    """L-shaped through-slot that frees the +z arm: along the inboard side of the arm and across its free end."""
    y0, y1 = c.seat_y - OVERSHOOT, c.top_y + OVERSHOOT
    z_in = c.H - c.arm_t - c.slot                                       # inboard face of the slot
    inner = _box(c.x_free - c.slot, c.x_root, y0, y1, z_in, c.H - c.arm_t)
    end = _box(c.x_free - c.slot, c.x_free, y0, y1, z_in, c.H + OVERSHOOT)
    return inner.union(end)


def _bump(c: Cfg) -> cq.Workplane:
    """The +z bump: trapezoid in plan (base sunk into the arm, tip 0.6 wide, 0.40 beyond the plate edge), full plate height, with a 45 deg
    lead-in on its underside (the lid goes into the recess underside first)."""
    z_tip = c.H + c.bump_p
    pts = [(c.x_bump - c.bump_base / 2, -(c.H - FUSE)), (c.x_bump + c.bump_base / 2, -(c.H - FUSE)),
           (c.x_bump + c.bump_tip / 2, -z_tip), (c.x_bump - c.bump_tip / 2, -z_tip)]          # local v = -z
    b = cq.Workplane(_plane_y(c.seat_y)).polyline(pts).close().extrude(c.t)
    p = c.bump_p
    ramp = (cq.Workplane("YZ", origin=(c.x_bump - c.bump_base, 0, 0))                          # local (u, v) = (y, z): remove the corner above the 45 deg line
            .polyline([(c.seat_y - OVERSHOOT, c.H - OVERSHOOT), (c.seat_y - OVERSHOOT, z_tip + OVERSHOOT), (c.seat_y + p + OVERSHOOT, z_tip + OVERSHOOT)])
            .close().extrude(2 * c.bump_base))
    return b.cut(ramp)


def _notch(c: Cfg) -> cq.Workplane:
    z_in = c.H - c.notch_d
    n = _box(c.notch_x - c.notch_w / 2, c.notch_x + c.notch_w / 2, c.seat_y - OVERSHOOT, c.top_y + OVERSHOOT, z_in, c.H + OVERSHOOT)
    sel = cq.selectors.BoxSelector((c.notch_x - c.notch_w, c.seat_y - 2 * OVERSHOOT, z_in - 0.05),
                                   (c.notch_x + c.notch_w, c.top_y + 2 * OVERSHOOT, z_in + 0.05))
    return n.edges("|Y").edges(sel).fillet(c.notch_r)


def make_lid(bumps: bool = True) -> cq.Workplane:
    """The lid, one solid, bay frame.  bumps=False leaves the bare plate with its arms (tests: the only contact with the housing is the seat)."""
    c = Cfg()
    plate = cq.Workplane(_plane_y(c.seat_y)).rect(2 * c.H, 2 * c.H).extrude(c.t).edges("|Y").fillet(c.R)
    plate = plate.faces(">Y").edges().chamfer(c.chamfer)
    slots = _arm_slots(c)
    cut = _rot(slots, 0)
    for a in (90.0, 180.0, 270.0):
        cut = cut.union(_rot(slots, a))
    lid = plate.cut(cut).cut(_notch(c))
    if bumps:
        b = _bump(c)
        for a in (0.0, 90.0, 180.0, 270.0):
            lid = lid.union(_rot(b, a))
    return lid.clean()


def arm_estimate() -> dict:
    """Hand calculation of one bump arm (in-plane cantilever, free length L from the root to the bump centre, E from cad/materials.py):
    F = 3 E I d / L^3, I = h t^3 / 12 (h = plate thickness, t = arm width), strain = 3 t d / (2 L^2).  d = interference with the lid centred;
    d_max = the whole bump protrusion (lid pushed against one wall).  Retention = vertical friction of the four bumps, centred."""
    c = Cfg()
    E = P.LID1021_PETG_E_MPA
    L = c.x_root - c.x_bump
    I = c.t * c.arm_t ** 3 / 12.0
    f = lambda d: 3.0 * E * I * d / L ** 3
    strain = lambda d: 3.0 * c.arm_t * d / (2.0 * L ** 2)
    plate_vol = make_lid().val().Volume()
    weight = plate_vol * P.LID1021_PETG_G_CM3 / 1e6 * 9.81        # N
    return {"L_mm": L, "I_mm4": I, "F_nominal_N": f(c.interf), "F_max_N": f(c.bump_p), "strain_nominal_pct": 100 * strain(c.interf),
            "strain_max_pct": 100 * strain(c.bump_p), "retention_N": 4 * f(c.interf) * c.mu, "weight_N": weight,
            "retention_over_weight": 4 * f(c.interf) * c.mu / weight,
            "F_at_interference_range_N": (f(c.interf - 0.05), f(c.interf + 0.05))}


# =============================================================================================================================
# keep-outs, frames, print pose, overhangs
# =============================================================================================================================
def keepout_solids() -> dict:
    """Ø2 bores and the cable lines leaving them as thin cylinders (bay frame): the four corner holes (13.76 deg rise outward) and the T_A/T_B/T_C
    holes (horizontal, plus fans of lines rising 15 .. 90 deg from the outer mouths; 90 = straight up along the outer wall plane, the worst case).
    Lengths 400 mm."""
    from .gripper1021_housing_cambay import tri_hole_frames          # axis / mouths of the three Ø2 teardrop holes (box frame = bay frame)
    out = {}
    ci = (P.CAMBAY1021_CORNER_HOLE_INNER_XZ, P.CAMBAY1021_CORNER_HOLE_INNER_Y)
    co = (P.CAMBAY1021_CORNER_HOLE_EXIT_XZ, P.CAMBAY1021_CORNER_HOLE_EXIT_Y)
    for sx in (-1, 1):
        for sz in (-1, 1):
            a = cq.Vector(sx * ci[0], ci[1], sz * ci[0])
            d = cq.Vector(sx * co[0], co[1], sz * co[0]) - a
            out[f"corner{'+' if sx > 0 else '-'}{'+' if sz > 0 else '-'}"] = cq.Solid.makeCylinder(1.0, 400.0, a, d.normalized())
    up = cq.Vector(0, 1, 0)
    for hid, fr in tri_hole_frames().items():
        out[f"T_{hid}"] = cq.Solid.makeCylinder(1.0, 400.0, fr["inner"] - fr["axis"] * 2.0, fr["axis"])
        for el in (15, 30, 45, 60, 75, 90):
            e = math.radians(el)
            d = fr["axis"] * math.cos(e) + up * math.sin(e)
            out[f"T_{hid}_line{el}"] = cq.Solid.makeCylinder(0.5, 400.0, fr["outer"], d)
    return out


def to_world(shape: cq.Shape) -> cq.Shape:
    return shape.translate(cq.Vector(*ORIGIN))


def to_print_pose(shape: cq.Shape) -> cq.Shape:
    """Top face (y = 51.8) on the bed: rotate about +x by -90 deg (y -> -z), bounding box moved to x = y = z = 0."""
    s = shape.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), -90.0)
    bb = s.BoundingBox()
    return s.translate(cq.Vector(-bb.xmin, -bb.ymin, -bb.zmin))


def overhang_faces(shape: cq.Shape, limit_deg: float = 45.0, tol_deg: float = 0.5, tess: float = 0.02):
    """Downward-facing triangles steeper than limit_deg from vertical in the print orientation (top face down: print z = -y), bed contact excluded."""
    import numpy as np
    verts, tris = shape.tessellate(tess, 0.15)
    V = np.array([[v.x, v.y, v.z] for v in verts], float)
    F = np.array(tris, int).reshape(-1, 3)
    t = V[F]
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    area = 0.5 * np.linalg.norm(n, axis=1)
    nn = n / np.maximum(2 * area, 1e-18)[:, None]
    nz = -nn[:, 1]
    zp = -t[:, :, 1]
    zmin = zp.min()
    on_bed = np.all(np.abs(zp - zmin) < 1e-4, axis=1)
    bad = (nz < -math.sin(math.radians(limit_deg + tol_deg))) & ~on_bed & (area > 1e-9)
    out = []
    if bad.any():
        pts = t[bad].reshape(-1, 3)
        out.append({"area": float(area[bad].sum()), "n_tri": int(bad.sum()), "bbox": (tuple(pts.min(axis=0).round(3)), tuple(pts.max(axis=0).round(3)))})
    return out


def bed_contact_area(shape: cq.Shape) -> float:
    """Area of the top face (the bed face), the planar face at y = top_y with normal +y."""
    c = Cfg()
    return sum(f.Area() for f in shape.Faces() if f.geomType() == "PLANE" and abs(f.normalAt().y - 1.0) < 1e-6 and abs(f.BoundingBox().ymax - c.top_y) < 1e-4)


# =============================================================================================================================
# export / render
# =============================================================================================================================
def export_all(step_dir: str = STEP_DIR, stl_dir: str = STL_DIR) -> dict:
    """STEP in the world frame (drops onto the housing in Jasper's assembly), STL in print orientation (top face down)."""
    os.makedirs(step_dir, exist_ok=True)
    os.makedirs(stl_dir, exist_ok=True)
    lid = make_lid().val()
    step, stl = os.path.join(step_dir, f"{LID_NAME}.step"), os.path.join(stl_dir, f"{LID_NAME}.stl")
    cq.exporters.export(cq.Workplane("XY").add(to_world(lid)), step)
    cq.exporters.export(cq.Workplane("XY").add(to_print_pose(lid)), stl, tolerance=0.02, angularTolerance=0.1)
    return {"step": step, "stl": stl}


# standard views of the lid, bay frame (direction from the part to the camera, screen-up hint): the lid's top face is +y, the +z side carries the notch
LID_VIEWS = {
    "top": ((0, 1, 0), (0, 0, 1)),        # the top face (the bed face when printed), +z up in the picture
    "bottom": ((0, -1, 0), (0, 0, 1)),    # the underside (seat face, arms, slots)
    "front": ((0, 0, -1), (0, 1, 0)),     # from -z (the camera-bay side), edge-on
    "rear": ((0, 0, 1), (0, 1, 0)),       # from +z (the notch side), edge-on
    "left": ((-1, 0, 0), (0, 1, 0)),
    "right": ((1, 0, 0), (0, 1, 0)),
    "iso": ((0.55, 0.65, 0.55), (0, 1, 0)),
}


def render_all(out_dir: str = RENDER_DIR) -> list:
    """7 standard views of the lid (bay frame) and four views of the lid on the housing."""
    from .encoder1021 import render_scene                          # the z-buffer renderer of the encoder module (import only)
    os.makedirs(out_dir, exist_ok=True)
    lid = make_lid().val()
    housing = load_housing()
    c = Cfg()
    bb = lid.BoundingBox()
    half = 0.5 * max(bb.xlen, bb.ylen, bb.zlen)
    ctr = ((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, (bb.zmin + bb.zmax) / 2)
    bounds = ((ctr[0] - half, ctr[1] - half, ctr[2] - half), (ctr[0] + half, ctr[1] + half, ctr[2] + half))
    blue, grey = (0.20, 0.50, 0.90), (0.62, 0.64, 0.68)
    paths = []
    for view, (cam, up) in LID_VIEWS.items():
        p = os.path.join(out_dir, f"{LID_NAME}_{view}.png")
        render_scene([(lid, blue, 1.0, 0.02)], p, (cam, up), f"{LID_NAME} - {view}", px=700, bounds=bounds,
                     note=f"bbox {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm; bay frame, +y up; camera at {cam}")
        paths.append(p)

    def clip(sh, x0=-60, x1=60, y0=30, y1=60, z0=-60, z1=60):
        r = sh.intersect(_box(x0, x1, y0, y1, z0, z1).val())
        return r

    hs = clip(housing)
    p = os.path.join(out_dir, f"{LID_NAME}_on_housing_iso.png")
    render_scene([(hs, grey, 1.0, 0.1), (lid, blue, 1.0, 0.02)], p, ((0.55, 0.62, 0.56), (0, 1, 0)),
                 "lid in the housing's open top (housing clipped to y 30 .. 60)", px=900, bounds=((-55, 30, -55), (55, 60, 55)),
                 note="bay frame, +y up; the pry notch is on the +z side")
    paths.append(p)
    ymid = 0.5 * (c.seat_y + c.top_y)
    p = os.path.join(out_dir, f"{LID_NAME}_on_housing_section_y.png")
    render_scene([(clip(housing, y1=ymid), grey, 1.0, 0.1), (lid.intersect(_box(-60, 60, 40, ymid, -60, 60).val()), blue, 1.0, 0.02)],
                 p, ((0, 1, 0), (0, 0, 1)), f"section at y = {ymid:.1f} seen from above: plate, four arms with bumps, notch, seat ring and recess wall",
                 px=1000, bounds=((-46, 49, -46), (46, 51, 46)), note="+x left? camera at +y looking down, +z up (x mirrored: -x to the right)")
    paths.append(p)
    p = os.path.join(out_dir, f"{LID_NAME}_on_housing_section_arm.png")
    render_scene([(clip(housing, y1=ymid), grey, 1.0, 0.05), (lid.intersect(_box(-60, 60, 40, ymid, -60, 60).val()), blue, 1.0, 0.02)],
                 p, ((0, 1, 0), (0, 0, 1)), "the +z arm and bump, section at mid plate: 0.25 mm edge clearance, bump tip 0.15 mm into the wall",
                 px=1000, bounds=((-16, 49, 34), (16, 51, 46)), note="camera at +y looking down, +z up (-x to the right)")
    paths.append(p)
    p = os.path.join(out_dir, f"{LID_NAME}_on_housing_section_x0.png")
    render_scene([(clip(housing, x1=0.0), grey, 1.0, 0.1), (lid.intersect(_box(-60, 0.0, 40, 60, -60, 60).val()), blue, 1.0, 0.02)],
                 p, ((1, 0, 0), (0, 1, 0)), "section x = 0 at the +z side: lid plate on the seat ring, 3.2 mm below the rim",
                 px=1000, bounds=((-2, 40, 30), (2, 58, 46)), note="camera at +x, +y up, +z to the left")
    paths.append(p)
    return paths


if __name__ == "__main__":
    c = Cfg()
    lid = make_lid().val()
    bb = lid.BoundingBox()
    print(f"lid: valid={lid.isValid()} solids={len(lid.Solids())} vol={lid.Volume():.1f} mm3 mass={lid.Volume() * P.LID1021_PETG_G_CM3 / 1000:.2f} g "
          f"bbox x[{bb.xmin:.3f},{bb.xmax:.3f}] y[{bb.ymin:.3f},{bb.ymax:.3f}] z[{bb.zmin:.3f},{bb.zmax:.3f}]")
    print("measured opening:", {k: round(v, 4) for k, v in measure_opening().items()})
    print("arm:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in arm_estimate().items()})
    d = export_all()
    print(d["step"], d["stl"])
    render_all()
    print("renders ->", RENDER_DIR)
