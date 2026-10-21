"""
Gripper 1021 ELECTRICAL HOUSING + CAMERA BAY (one printed part) and the bay's access COVER.

Port of the verified v6 camera bay (cad/parts/claw_camera_bay.py; XIAO ESP32-S3 Sense, no IMU, D27) onto Jasper's
new housing  cad/reference/gripper_1021/parts/05_Gripper_Electric_Housing_Base_2__NAUO5.step  (100 x 100 base with R20
corners, R75 concave blend up to a 90 x 90 box with 5 mm walls, top 55, lid seat 50, Ø30 tube hole, 8 x Ø3.3 holes,
four Ø2 corner cable holes rising 13.8 deg).  The housing STEP is read-only; the bay is UNIONED onto it and the only cut
in the housing is the wire window from the bay neck into the box pocket (x = 0, below the lid seat).

Bay frame (identical to v6, so the lens sits at the same world position and the D28 camera-view study still applies):
  origin  : on the tube axis in the box BOTTOM plane (world y = 1091.1905, x = 951.8475, z = 1103.9899)
  axes    : parallel to the world axes, +Y up, tube axis = Y, optical axis -Y, bay on -Z (CAMBAY_SIDE = -1)
  r       : radial distance outward from the tube axis (z = SIDE * r); optical axis at r = 90 mm
  lens    : centre (x +4.75, y 1.9, r 90) -> world (956.5975, 1093.0905, 1013.9899)

What changed against v6 (everything else is read from the unchanged CAMBAY_* block):
  * box values -> CAMBAY1021_* (flange half 50, upper half 45, blend R75, pocket half 40, lid seat 50, top 55);
  * bay solid starts at r = 42.5, INSIDE the 5 mm wall (pocket wall at r = 40), so nothing enters the pocket;
  * cover inner edge follows the new wall (r = 45.85 at the cover height);
  * root gusset ribs land on the new wall (x <= 30, r = 44.5) and the wire window funnel is re-derived for the 5 mm wall;
  * corner cable holes: Ø2, mouth |x| = |z| = 43.22 at y = 9.95; the keep-out asserts use these.

Print orientation: housing + bay as the box prints (bottom plane on the bed, +Y up; STL = bay frame rotated +90 deg about X,
z min = 0).  Cover: outer face flat on the bed, lip / pegs / antenna corral up.
"""

from __future__ import annotations

import math
import os

import cadquery as cq

from .. import params as P
from ..params import SCREW_M3

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOUSING_STEP = os.path.join(REPO, "cad", "reference", "gripper_1021", "parts",
                            "05_Gripper_Electric_Housing_Base_2__NAUO5.step")
STEP_DIR = os.path.join(REPO, "exports", "step")
STL_DIR = os.path.join(REPO, "exports", "stl")

# --- sign / frame -----------------------------------------------------------------------------------------------------
S = P.CAMBAY_SIDE                       # -1 -> bay on -Z
assert S in (-1, 1)
BAY_ORIGIN_WORLD = P.CAMBAY1021_BAY_ORIGIN_WORLD
OVERTRAVEL = 0.5                        # mm, cutter overshoot for clean cuts

# --- box (Jasper's housing, bay frame) -------------------------------------------------------------------------------------
BOX_FLANGE_HALF = P.CAMBAY1021_BOX_FLANGE_HALF
BOX_FLANGE_T = P.CAMBAY1021_BOX_FLANGE_T
BOX_UPPER_HALF = P.CAMBAY1021_BOX_UPPER_HALF
BOX_BLEND_R = P.CAMBAY1021_BOX_BLEND_R
BOX_BLEND_TOP_Y = P.CAMBAY1021_BOX_BLEND_TOP_Y
POCKET_HALF = P.CAMBAY1021_BOX_POCKET_HALF
POCKET_FLOOR_Y = P.CAMBAY1021_BOX_POCKET_FLOOR_Y
LID_SEAT_Y = P.CAMBAY1021_BOX_LID_SEAT_Y
CORNER_EXIT_XZ = P.CAMBAY1021_CORNER_HOLE_EXIT_XZ
CORNER_KEEPOUT = P.CAMBAY1021_CORNER_HOLE_KEEPOUT


def box_wall_r(y: float) -> float:
    """Radial position of the box outer wall (middle of the -Z face) at height y: flange, then the R75 blend."""
    if y <= BOX_FLANGE_T:
        return BOX_FLANGE_HALF
    cz = BOX_UPPER_HALF + BOX_BLEND_R
    dy = BOX_BLEND_TOP_Y - min(y, BOX_BLEND_TOP_Y)
    return cz - math.sqrt(BOX_BLEND_R ** 2 - dy ** 2)


assert abs(box_wall_r(BOX_FLANGE_T) - BOX_FLANGE_HALF) < 0.01          # the blend meets the flange edge at y = 5

# --- basic dimensions (shared with v6) -----------------------------------------------------------------------------------------
WALL = P.CAMBAY_WALL
FLOOR_T = P.CAMBAY_FLOOR_T
COVER_T = P.CAMBAY_COVER_T

BOARD_CR = P.CAMBAY_CAM_R - P.CAMBAY_LENS_DR    # cradle centre, radial (lens r = CAM_R)
CAV_HALF_X = P.CAMBAY_CRADLE_L / 2              # 11.5
CAV_HALF_R = P.CAMBAY_CRADLE_W / 2              # 9.3
HEAD_R0 = BOARD_CR - CAV_HALF_R                 # 80.7
HEAD_R1 = BOARD_CR + CAV_HALF_R                 # 99.3
OUT_HALF_X = CAV_HALF_X + WALL                  # 13.5
OUT_R1 = HEAD_R1 + WALL                         # 101.3 bay outer end
assert P.CAMBAY_CRADLE_L >= P.CAMBAY_XIAO_L + 0.5 - 1e-9
assert P.CAMBAY_CRADLE_W >= P.CAMBAY_XIAO_W + 0.8 - 1e-9
BOARD_X0 = -P.CAMBAY_XIAO_USB_OVERHANG / 2
BOARD_X_END = BOARD_X0 + P.CAMBAY_XIAO_BOARD_L / 2
LENS_X = BOARD_X_END - P.CAMBAY_LENS_FROM_BOARD_END     # +4.75

LENS_FRONT_Y = P.CAMBAY_LENS_FRONT_Y                    # 1.9
Y_BOARD0 = LENS_FRONT_Y + P.CAMBAY_CAM_PROTRUDE         # 9.9 board seat plane
Y_BOARD1 = Y_BOARD0 + P.CAMBAY_XIAO_H
Y_STACK_TOP = Y_BOARD0 + P.CAMBAY_XIAO_H - P.CAMBAY_CAM_PROTRUDE
H_CAV = Y_BOARD0 + P.CAMBAY_INTERNAL_H                  # 26.9 wall top / cover seat
Y_TOP = H_CAV + COVER_T                                 # 29.3 cover top
assert P.CAMBAY_INTERNAL_H >= 16.0 and H_CAV > Y_BOARD1
assert H_CAV + COVER_T < LID_SEAT_Y - 10, "bay stays far below the lid seat"

WIN_R = P.CAMBAY_LENS_WINDOW_R
WIN_X0 = LENS_X - P.CAMBAY_LENS_POS_TOL - P.CAMBAY_LENS_BARREL_D / 2
WIN_X1 = min(LENS_X + P.CAMBAY_LENS_POS_TOL + P.CAMBAY_LENS_BARREL_D / 2,
             CAV_HALF_X - P.CAMBAY_LENS_WINDOW_END_WALL)
WIN_X = WIN_X1 - WIN_X0
WIN_XC = 0.5 * (WIN_X0 + WIN_X1)
assert WIN_R >= 2 * (P.CAMBAY_LENS_POS_TOL + P.CAMBAY_LENS_BARREL_D / 2)
BLOCK_R0 = BOARD_CR - WIN_R / 2 - P.CAMBAY_LENS_CHAMFER - WALL
assert BLOCK_R0 < HEAD_R0 + 1e-9

# --- box dependent: bay body start, neck, ribs, cover ----------------------------------------------------------------------
BODY_R_IN = P.CAMBAY1021_BODY_R_IN                      # 42.5: inside the wall (pocket r = 40)
assert POCKET_HALF < BODY_R_IN < box_wall_r(H_CAV), "bay solid must start inside the wall, not in the pocket"
NECK_RC = P.CAMBAY1021_NECK_TIE_RC
RIB_P0, RIB_P1 = P.CAMBAY1021_RIB_P0, P.CAMBAY1021_RIB_P1
assert POCKET_HALF < RIB_P1[1] < box_wall_r(P.CAMBAY_RIB_H), "rib ends inside the wall, outside the pocket"
COVER_R0 = box_wall_r(Y_TOP) + P.CAMBAY1021_COVER_WALL_GAP      # cover inner edge off the box wall

# --- wire window ---------------------------------------------------------------------------------------------------------------
WIN_W, WIN_H, WIN_Y = P.CAMBAY_WIN_W, P.CAMBAY_WIN_H, P.CAMBAY_WIN_Y
WIN_ROOF_CH = P.CAMBAY1021_WIN_ROOF_CH
assert WIN_W >= 8.0 and WIN_H >= 6.0
assert POCKET_FLOOR_Y < WIN_Y - WIN_H / 2, "window must clear the pocket floor"
assert WIN_Y + WIN_H / 2 < LID_SEAT_Y - 10, "window must sit well below the lid seat"

# --- cover screw columns ---------------------------------------------------------------------------------------------------------
INS_D, INS_DEPTH = P.CAMBAY_INSERT_D, P.CAMBAY_INSERT_DEPTH
assert INS_DEPTH >= P.CAMBAY_INSERT_LEN + 1.0
COL_OD = max(8.0, INS_D + 2 * P.CAMBAY_BOSS_WALL)
COL_X = OUT_HALF_X + COL_OD / 2 - 1.5
COL_R = P.CAMBAY_COVER_SCREW_R

# --- corner cable-hole keep-outs (bay is at |x| <= COL_X + COL_OD/2 on the -Z side; mouths are on the diagonals) ----------------
BAY_MAX_X = max(OUT_HALF_X, COL_X + COL_OD / 2, RIB_P1[0])
assert BAY_MAX_X + CORNER_KEEPOUT < CORNER_EXIT_XZ, "bay must stay >= 5 mm from the corner hole mouths"
assert RIB_P1[0] + CORNER_KEEPOUT < P.CAMBAY1021_CORNER_HOLE_INNER_XZ
assert WIN_W / 2 + 6.0 + CORNER_KEEPOUT < P.CAMBAY1021_CORNER_HOLE_INNER_XZ

# --- USB-C notch ---------------------------------------------------------------------------------------------------------------------
USB_NOTCH_W = P.CAMBAY_USB_PLUG_W + 2 * P.CAMBAY_USB_PLAY
USB_YC = Y_STACK_TOP - P.CAMBAY_XIAO_USB_Z_FROM_TOP
USB_SILL_Y = Y_BOARD0 + P.CAMBAY_USB_SILL_ABOVE_SEAT
assert USB_YC - P.CAMBAY_USB_PLUG_H / 2 - P.CAMBAY_USB_PLAY >= USB_SILL_Y - 1e-9
assert USB_YC + P.CAMBAY_USB_PLUG_H / 2 < H_CAV - 1.0


# --- geometry helpers -----------------------------------------------------------------------------------------------------------------
def _box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    return (cq.Workplane("XY").box(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0), centered=False)
            .translate((min(x0, x1), min(y0, y1), min(z0, z1))))


def _rbox(x0, x1, y0, y1, r0, r1) -> cq.Workplane:
    """Box given in (x, y, r) with r the radial coordinate (z = S * r)."""
    return _box(x0, x1, y0, y1, S * r0, S * r1)


def _prism_xr(pts, y0, y1) -> cq.Workplane:
    wp = cq.Workplane("XZ").workplane(offset=-y1)
    return wp.polyline([(x, S * r) for x, r in pts]).close().extrude(y1 - y0)


def _cyl_y(x, r, d, y0, y1) -> cq.Workplane:
    return cq.Workplane("XZ").workplane(offset=-y1).center(x, S * r).circle(d / 2).extrude(y1 - y0)


def _frustum_rect_y(x, r, sx_top, sr_top, y_top, sx_bot, sr_bot, y_bot) -> cq.Workplane:
    return (cq.Workplane("XZ").workplane(offset=-y_top).center(x, S * r).rect(sx_top, sr_top)
            .workplane(offset=y_top - y_bot).rect(sx_bot, sr_bot).loft(combine=True))


def _union(shapes) -> cq.Workplane:
    out = None
    for s in shapes:
        out = s if out is None else out.union(s)
    return out


def _cut_all(base, cutters) -> cq.Workplane:
    for c in cutters:
        base = base.cut(c)
    return base


# --- features ----------------------------------------------------------------------------------------------------------------------------
def _ribs() -> cq.Workplane:
    """Two flat gusset ribs from the neck side walls back into the box wall."""
    ribs = []
    p0, p1 = RIB_P0, RIB_P1
    dx, dr = p1[0] - p0[0], p1[1] - p0[1]
    n = math.hypot(dx, dr)
    nx, nr = -dr / n * P.CAMBAY_RIB_T / 2, dx / n * P.CAMBAY_RIB_T / 2
    for sx in (1, -1):
        pts = [(sx * (p0[0] + nx), p0[1] + nr), (sx * (p1[0] + nx), p1[1] + nr),
               (sx * (p1[0] - nx), p1[1] - nr), (sx * (p0[0] - nx), p0[1] - nr)]
        ribs.append(_prism_xr(pts, 0.0, P.CAMBAY_RIB_H))
    return _union(ribs)


def _usb_notch_cutter() -> cq.Workplane:
    return _rbox(CAV_HALF_X - 1.0, OUT_HALF_X + 1.0, USB_SILL_Y, H_CAV + 1.0,
                 BOARD_CR - USB_NOTCH_W / 2, BOARD_CR + USB_NOTCH_W / 2)


def _vent_cutters() -> list:
    cut = []
    sw = 2.0
    for rr in (BOARD_CR - 5.5, BOARD_CR, BOARD_CR + 5.5):
        cut.append(_rbox(-OUT_HALF_X - 1.0, -CAV_HALF_X + 1.0, Y_BOARD0 + 1.0, Y_BOARD0 + 9.0,
                         rr - sw / 2, rr + sw / 2))
    return cut


TIE_R = (NECK_RC - 4.0, NECK_RC + 4.0)
TIE_X = (-4.5, 4.5)


def _tie_cutters() -> list:
    return [_rbox(xx - 0.9, xx + 0.9, -OVERTRAVEL, FLOOR_T + OVERTRAVEL, rr - 1.9, rr + 1.9)
            for rr in TIE_R for xx in TIE_X]


def _lens_cutters() -> list:
    r = BOARD_CR + P.CAMBAY_LENS_DR
    c = P.CAMBAY_LENS_CHAMFER
    tunnel = _box(WIN_X0, WIN_X1, -OVERTRAVEL, Y_BOARD0 + OVERTRAVEL, S * r - WIN_R / 2, S * r + WIN_R / 2)
    flare = _frustum_rect_y(WIN_XC, r, WIN_X, WIN_R, c, WIN_X + 2 * c, WIN_R + 2 * c, 0.0)
    flare_ext = _box(WIN_X0 - c, WIN_X1 + c, -OVERTRAVEL, 0.0, S * r - WIN_R / 2 - c, S * r + WIN_R / 2 + c)
    return [tunnel, flare, flare_ext]


def _locator_ribs() -> cq.Workplane:
    t, w = P.CAMBAY_LOCATOR_RIB_T, P.CAMBAY_LOCATOR_RIB_W
    out = []
    for xc in (-8.0, 7.0):
        out.append(_rbox(xc - w / 2, xc + w / 2, Y_BOARD0 - 0.2, Y_BOARD0 + 8.0, HEAD_R0 - 0.1, HEAD_R0 + t))
        out.append(_rbox(xc - w / 2, xc + w / 2, Y_BOARD0 - 0.2, Y_BOARD0 + 8.0, HEAD_R1 - t, HEAD_R1 + 0.1))
    return _union(out)


def _columns() -> cq.Workplane:
    return _union([_cyl_y(sx * COL_X, COL_R, COL_OD, 0.0, H_CAV) for sx in (1, -1)])


def _column_holes() -> list:
    return [_cyl_y(sx * COL_X, COL_R, INS_D, H_CAV - INS_DEPTH, H_CAV + 1.0) for sx in (1, -1)]


def make_bay_body() -> cq.Workplane:
    """The bay feature as ONE solid (to be unioned with the housing), bay frame."""
    outer = (_rbox(-OUT_HALF_X, OUT_HALF_X, 0.0, H_CAV, BODY_R_IN, OUT_R1)
             .union(_columns()).union(_ribs()))
    xiao_cav = _rbox(-CAV_HALF_X, CAV_HALF_X, FLOOR_T, H_CAV + OVERTRAVEL, BODY_R_IN - 1.0, HEAD_R1)
    body = outer.cut(xiao_cav)
    block = _rbox(-CAV_HALF_X, CAV_HALF_X, FLOOR_T - 0.2, Y_BOARD0, BLOCK_R0, HEAD_R1)
    fence_y1 = Y_BOARD0 + P.CAMBAY_FENCE_H
    fences = [_rbox(a, b, FLOOR_T - 0.2, fence_y1, HEAD_R0 - WALL, HEAD_R0)
              for a, b in ((-CAV_HALF_X, -4.0), (4.0, CAV_HALF_X))]
    body = body.union(block).union(_union(fences)).union(_locator_ribs())
    cutters = (_lens_cutters() + [_usb_notch_cutter()] + _vent_cutters() + _tie_cutters() + _column_holes())
    return _cut_all(body, cutters)


def make_cover() -> cq.Workplane:
    """Screw-down access cover, built at its assembled height H_CAV (bay frame)."""
    y0, y1 = H_CAV, H_CAV + COVER_T
    plate = _rbox(-OUT_HALF_X, OUT_HALF_X, y0, y1, COVER_R0, OUT_R1)
    ears = _union([_cyl_y(sx * COL_X, COL_R, COL_OD, y0, y1) for sx in (1, -1)])
    cover = plate.union(ears)

    lip_t, lip_h, gap = WALL, 1.0, 0.2
    lx = CAV_HALF_X - gap
    lr1 = HEAD_R1 - gap
    lip_r0 = COVER_R0 + 3.0
    lips = [_rbox(lx - lip_t, lx, y0 - lip_h, y0 + 0.1, lip_r0, lr1),
            _rbox(-lx, -lx + lip_t, y0 - lip_h, y0 + 0.1, lip_r0, lr1),
            _rbox(-lx, lx, y0 - lip_h, y0 + 0.1, lr1 - lip_t, lr1)]
    peg = 2.4
    pegs = []
    for sx in (1, -1):
        for sr in (1, -1):
            cx = sx * (CAV_HALF_X - peg / 2 - 0.2)
            cr = BOARD_CR + sr * (CAV_HALF_R - peg / 2 - 0.2)
            pegs.append(_rbox(cx - peg / 2, cx + peg / 2, Y_BOARD0 + P.CAMBAY_PEG_STOP_ABOVE_SEAT, y0 + 0.1,
                              cr - peg / 2, cr + peg / 2))
    rail_t, rail_h = WALL, 1.5
    ant_r0 = 65.0
    ant_r1 = ant_r0 + P.CAMBAY_ANT_L + 0.6
    iw = P.CAMBAY_ANT_W / 2 + 0.3
    rails = [_rbox(iw, iw + rail_t, y0 - rail_h, y0 + 0.1, ant_r0, ant_r1),
             _rbox(-iw - rail_t, -iw, y0 - rail_h, y0 + 0.1, ant_r0, ant_r1),
             _rbox(-iw - rail_t, iw + rail_t, y0 - rail_h, y0 + 0.1, ant_r1, ant_r1 + rail_t)]
    cover = cover.union(_union(lips)).union(_union(pegs)).union(_union(rails))

    cuts = [_cyl_y(sx * COL_X, COL_R, SCREW_M3, y0 - 2, y1 + 1) for sx in (1, -1)]
    r_a, r_b = P.CAMBAY1021_COVER_VENT_R
    for vx in P.CAMBAY1021_COVER_VENT_X:
        cuts.append(_rbox(vx - 1.0, vx + 1.0, y0 - 2, y1 + 1, COVER_R0 + r_a, COVER_R0 + r_b))
    return _cut_all(cover, cuts)


def wire_window_cutter() -> cq.Workplane:
    """Rectangular wire window through the 5 mm wall (box pocket <-> bay cavity) at x = 0, flared at both mouths."""
    fl = P.CAMBAY_WIN_FLARE
    pocket_r = POCKET_HALF
    r_in, r_out = pocket_r - 2.0, P.CAMBAY1021_WIN_R_OUT
    z_a, z_b = S * r_in, S * r_out
    ch = WIN_ROOF_CH
    y0w, y1w = WIN_Y - WIN_H / 2, WIN_Y + WIN_H / 2
    prof = [(-WIN_W / 2, y0w), (WIN_W / 2, y0w), (WIN_W / 2, y1w - ch),
            (WIN_W / 2 - ch, y1w), (-WIN_W / 2 + ch, y1w), (-WIN_W / 2, y1w - ch)]
    straight = (cq.Workplane("XY").workplane(offset=min(z_a, z_b)).polyline(prof).close()
                .extrude(abs(z_b - z_a)))

    def flare(r_small, r_big, grow):
        return (cq.Workplane("XY").workplane(offset=S * r_small).center(0, WIN_Y)
                .rect(WIN_W, WIN_H)
                .workplane(offset=S * (r_big - r_small)).rect(WIN_W + 2 * grow, WIN_H + 2 * grow)
                .loft(combine=True))

    pocket_flare = flare(pocket_r + fl, pocket_r - 1.0, fl + 1.0)
    bay_flare = flare(box_wall_r(WIN_Y) - 2.0, r_out, P.CAMBAY1021_WIN_BAY_FLARE)
    return straight.union(pocket_flare).union(bay_flare)


# --- housing, combination, frames, exports ---------------------------------------------------------------------------------------
def load_housing_bay_frame() -> cq.Workplane:
    """Jasper's housing (read-only STEP) moved into the bay frame (origin on the tube axis in the bottom plane)."""
    shp = cq.importers.importStep(HOUSING_STEP).val()
    ox, oy, oz = BAY_ORIGIN_WORLD
    return cq.Workplane("XY").add(shp).translate((-ox, -oy, -oz))


def combine(box: cq.Workplane) -> cq.Workplane:
    """Union the bay onto the housing (bay frame) and cut the wire window (the ONLY cut in the housing)."""
    return box.union(make_bay_body()).cut(wire_window_cutter())


def to_world(shape: cq.Shape) -> cq.Shape:
    return shape.moved(cq.Location(cq.Vector(*BAY_ORIGIN_WORLD)))


def housing_to_print(wp: cq.Workplane) -> cq.Workplane:
    """Bay frame +Y (up) -> print +Z: rotate +90 deg about X (z min = 0 because the bottom plane is y = 0)."""
    return wp.rotate((0, 0, 0), (1, 0, 0), 90)


def cover_to_print(wp: cq.Workplane) -> cq.Workplane:
    """Cover on its flat outer face (lip / pegs / corral up), z min = 0."""
    r = housing_to_print(wp).rotate((0, 0, 0), (1, 0, 0), 180)
    return r.translate((0, 0, -r.val().BoundingBox().zmin))


LENS_CENTER_BAY = (LENS_X, LENS_FRONT_Y, S * (BOARD_CR + P.CAMBAY_LENS_DR))     # lens glass centre
LENS_CENTER_WORLD = tuple(a + b for a, b in zip(LENS_CENTER_BAY, BAY_ORIGIN_WORLD))
OPTICAL_AXIS_BAY = (0.0, -1.0, 0.0)


def make():
    """(housing + bay, cover), both in the bay frame."""
    return combine(load_housing_bay_frame()), make_cover()


def export_all(step_dir: str = STEP_DIR, stl_dir: str = STL_DIR) -> dict:
    """STEP in the assembly world frame (drops into Jasper's assembly at the origin), STL in print orientation."""
    os.makedirs(step_dir, exist_ok=True)
    os.makedirs(stl_dir, exist_ok=True)
    housing, cover = make()
    out = {}
    for name, wp, pose in (("gripper1021_housing_cambay", housing, housing_to_print),
                           ("gripper1021_housing_cambay_cover", cover, cover_to_print)):
        step = os.path.join(step_dir, name + ".step")
        cq.exporters.export(cq.Workplane("XY").add(to_world(wp.val())), step)
        stl = os.path.join(stl_dir, name + ".stl")
        cq.exporters.export(pose(wp), stl, tolerance=0.05, angularTolerance=0.2)
        out[name] = {"step": step, "stl": stl}
    return out


if __name__ == "__main__":
    housing, cover = make()
    orig = load_housing_bay_frame().val()
    for n, s in (("housing+bay", housing), ("cover", cover)):
        bb = s.val().BoundingBox()
        print(f"{n}: valid={s.val().isValid()} solids={len(s.solids().vals())} "
              f"bbox x[{bb.xmin:.2f},{bb.xmax:.2f}] y[{bb.ymin:.2f},{bb.ymax:.2f}] z[{bb.zmin:.2f},{bb.zmax:.2f}] "
              f"vol={s.val().Volume():.0f} mm3 mass={s.val().Volume() * P.GRIP1021_PETG_G_CM3 / 1000:.1f} g")
    print(f"original housing vol {orig.Volume():.0f} mm3; added by the bay (net) {housing.val().Volume() - orig.Volume():.0f} mm3")
    print("lens centre world", tuple(round(v, 4) for v in LENS_CENTER_WORLD))
    for k, d in export_all().items():
        print(k, d["step"], d["stl"])
