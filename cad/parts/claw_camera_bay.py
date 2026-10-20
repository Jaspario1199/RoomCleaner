"""
Claw CAMERA BAY -- Seeed XIAO ESP32-S3 Sense camera enclosure (no IMU, D27) that is
UNIONED onto the gripper electrical box ("Gripper_Electric_Housing_Base (2)" in
solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP, read-only).

The bay hangs off ONE side wall of the box (the narrow -Z side, CAMBAY_SIDE),
standing on the same print bed plane as the box's bottom flange, so box + bay
print without supports.  The camera looks straight DOWN (-Y, parallel to the
tube); its optical axis is CAMBAY_CAM_R = 90 mm from the tube axis (the lens is
CAMBAY_LENS_FROM_BOARD_END = 5 mm from the USB-C end of the board, so it sits
at bay x = +4.75 mm when the cradle is centred on the bay).

--------------------------------------------------------------------------
Bay frame (this file's local frame; v6 world = local + BAY_ORIGIN_WORLD)
--------------------------------------------------------------------------
  origin  : on the tube axis, in the box BOTTOM plane (v6 world Y = 1091.19)
  axes    : parallel to the v6 world axes, +Y = up (toward the box lid),
            tube axis = Y axis, optical axis = -Y, bay on -Z
            (r = radial distance outward from the tube axis, z = SIDE * r)

--------------------------------------------------------------------------
Plan (x, r) -- everything is a vertical extrusion from the bed plane
--------------------------------------------------------------------------
  r 101.3 +--------------------------+   end wall
  r  99.3 |  XIAO cradle 23.0 x 18.6 |   USB-C notch (15 wide, open top, closed by the cover)
  r  80.7 +----fence (gap |x|<4)-----+   in the +X wall; lens window at the +X end
          |  neck: wires, ribs, columns to the box wall |
  r ~ 62  +----- box wall (R75 blend) ------------------+     x = -13.5 .. +13.5
  The wire window (10 x 7) goes through the box wall at x = 0 into the box pocket.

--------------------------------------------------------------------------
Stack (heights above the box bottom plane)
--------------------------------------------------------------------------
  0 .. 2.4      floor (on the bed); lens window through floor + block
  2.4 .. 9.9    cradle block under the board; its seat plane is y = 9.9
  lens glass    y = 1.9 (camera module protrudes 8 mm below the seat, ASSUMED)
  9.9 .. 26.9   cavity, 17.0 mm above the seat (>= 16 for the 15 mm stack); cover seat at 26.9
  board stack   nominal 7 mm above the seat (15 - 8); the whole 15 mm would still fit.

--------------------------------------------------------------------------
Print orientation (no supports for critical surfaces)
--------------------------------------------------------------------------
  Box + bay: as the box prints (bottom flange on the bed, +Y up): walls, floor,
  ribs, columns are vertical.  Only bridge: wire-window roof (chamfered corners, 5 mm
  flat); the USB notch is open-top and needs none.
  Cover: outer face is flat -> print outer face DOWN; lip, pegs and antenna
  corral point up (the STL is exported that way, z min = 0).

--------------------------------------------------------------------------
VERIFY BEFORE PRINTING (assumed dimensions)
--------------------------------------------------------------------------
  Lens centre 5 mm from the USB-C end and centred across the width (window tolerates +-4 mm),
  camera protrusion 8 mm below the board seat, USB-C height 1.6 mm below the stack top,
  antenna 30 x 10 mm.
"""

from __future__ import annotations

import math

import cadquery as cq

from .. import params as P
from ..params import SCREW_M3

# --- sign / frame ---------------------------------------------------------------
S = P.CAMBAY_SIDE                       # -1 -> bay on -Z, +1 -> bay on +Z
assert S in (-1, 1)
BAY_ORIGIN_WORLD = (951.8475, 1091.1905, 1103.9899)   # tube axis @ box bottom plane
OVERTRAVEL = 0.5                        # mm, cutter overshoot for clean cuts

# --- basic dimensions -----------------------------------------------------------
WALL = P.CAMBAY_WALL
FLOOR_T = P.CAMBAY_FLOOR_T
COVER_T = P.CAMBAY_COVER_T

# XIAO cradle (head) --------------------------------------------------------------
BOARD_CR = P.CAMBAY_CAM_R - P.CAMBAY_LENS_DR    # cradle centre, radial (lens r = CAM_R)
CAV_HALF_X = P.CAMBAY_CRADLE_L / 2              # 11.5
CAV_HALF_R = P.CAMBAY_CRADLE_W / 2              # 9.3
HEAD_R0 = BOARD_CR - CAV_HALF_R                 # 80.7
HEAD_R1 = BOARD_CR + CAV_HALF_R                 # 99.3
OUT_HALF_X = CAV_HALF_X + WALL                  # 13.5
OUT_R1 = HEAD_R1 + WALL                         # 101.3 bay outer end
assert P.CAMBAY_CRADLE_L >= P.CAMBAY_XIAO_L + 0.5 - 1e-9     # envelope incl. USB overhang + 0.5
assert P.CAMBAY_CRADLE_W >= P.CAMBAY_XIAO_W + 0.8 - 1e-9
BOARD_X0 = -P.CAMBAY_XIAO_USB_OVERHANG / 2      # base-board centre along x (envelope centred in the pocket)
BOARD_X_END = BOARD_X0 + P.CAMBAY_XIAO_BOARD_L / 2      # USB-C end of the base board (+9.75)
LENS_X = BOARD_X_END - P.CAMBAY_LENS_FROM_BOARD_END     # lens centre along bay X (+4.75)

LENS_FRONT_Y = P.CAMBAY_LENS_FRONT_Y                    # 1.9 lens glass height
Y_BOARD0 = LENS_FRONT_Y + P.CAMBAY_CAM_PROTRUDE         # 9.9 board seat plane
BLOCK_H = Y_BOARD0 - FLOOR_T                            # 7.5 cradle block above the floor
Y_BOARD1 = Y_BOARD0 + P.CAMBAY_XIAO_H                   # 24.9 top of the stack IF all 15 mm sat above the seat
Y_STACK_TOP = Y_BOARD0 + P.CAMBAY_XIAO_H - P.CAMBAY_CAM_PROTRUDE   # 16.9 nominal stack top
H_CAV = Y_BOARD0 + P.CAMBAY_INTERNAL_H                  # 26.9 wall top / cover seat
Y_TOP = H_CAV + COVER_T                                 # 29.3 cover top
assert P.CAMBAY_INTERNAL_H >= 16.0 and H_CAV > Y_BOARD1

# lens window: +-4 mm of lens position for the 8 mm barrel, in X capped by the USB-end pocket wall
WIN_R = P.CAMBAY_LENS_WINDOW_R
WIN_X0 = LENS_X - P.CAMBAY_LENS_POS_TOL - P.CAMBAY_LENS_BARREL_D / 2
WIN_X1 = min(LENS_X + P.CAMBAY_LENS_POS_TOL + P.CAMBAY_LENS_BARREL_D / 2,
             CAV_HALF_X - P.CAMBAY_LENS_WINDOW_END_WALL)
WIN_X = WIN_X1 - WIN_X0                                 # 14.25
WIN_XC = 0.5 * (WIN_X0 + WIN_X1)
assert WIN_R >= 2 * (P.CAMBAY_LENS_POS_TOL + P.CAMBAY_LENS_BARREL_D / 2)
assert WIN_X0 <= LENS_X - P.CAMBAY_LENS_POS_TOL - P.CAMBAY_LENS_BARREL_D / 2 + 1e-9
BLOCK_R0 = BOARD_CR - WIN_R / 2 - P.CAMBAY_LENS_CHAMFER - WALL   # keeps >= WALL under the chamfer foot
assert BLOCK_R0 < HEAD_R0 + 1e-9
BODY_R_IN = 50.0                        # bay solid starts inside the box wall (< 55)
NECK_RC = 70.4                          # centre of the neck (ties)

# Wire window -------------------------------------------------------------------
WIN_W, WIN_H, WIN_Y = P.CAMBAY_WIN_W, P.CAMBAY_WIN_H, P.CAMBAY_WIN_Y
WIN_ROOF_CH = 2.5                       # mm, 45 deg roof-corner chamfer
assert WIN_W >= 8.0 and WIN_H >= 6.0
assert P.CAMBAY_BOX_POCKET_FLOOR_Y < WIN_Y - WIN_H / 2, "window must clear the pocket floor"
assert WIN_Y + WIN_H / 2 < P.CAMBAY_BOX_LID_SEAT_Y - 10, "window must sit well below the lid seat"
assert WIN_W / 2 + 6.0 + P.CAMBAY_CORNER_HOLE_KEEPOUT < 41.0   # corner-hole mouths at |x| >= 41

# Cover screw columns (heat-set M3 inserts) ----------------------------------------
INS_D, INS_DEPTH = P.CAMBAY_INSERT_D, P.CAMBAY_INSERT_DEPTH
assert INS_DEPTH >= P.CAMBAY_INSERT_LEN + 1.0
COL_OD = max(8.0, INS_D + 2 * P.CAMBAY_BOSS_WALL)   # 9.1 (>= 8, wall >= 2.5)
COL_X = OUT_HALF_X + COL_OD / 2 - 1.5
COL_R = P.CAMBAY_COVER_SCREW_R

RIB_X_MAX = P.CAMBAY_RIB_SPAN_X
assert RIB_X_MAX + P.CAMBAY_CORNER_HOLE_KEEPOUT < P.CAMBAY_CORNER_HOLE_EXIT_XZ
assert OUT_HALF_X + P.CAMBAY_CORNER_HOLE_KEEPOUT < P.CAMBAY_CORNER_HOLE_EXIT_XZ


def box_wall_r(y: float) -> float:
    """Radial position of the box outer wall at height y (flange + R75 blend)."""
    if y <= P.CAMBAY_BOX_FLANGE_T:
        return P.CAMBAY_BOX_FLANGE_HALF
    cz = P.CAMBAY_BOX_UPPER_HALF + P.CAMBAY_BOX_BLEND_R
    dy = P.CAMBAY_BOX_BLEND_TOP_Y - min(y, P.CAMBAY_BOX_BLEND_TOP_Y)
    return cz - math.sqrt(P.CAMBAY_BOX_BLEND_R ** 2 - dy ** 2)


COVER_R0 = box_wall_r(Y_TOP) + 0.8      # cover inner edge: 0.8 mm off the box wall

# USB-C notch ----------------------------------------------------------------------
USB_NOTCH_W = P.CAMBAY_USB_PLUG_W + 2 * P.CAMBAY_USB_PLAY            # 15.0
USB_YC = Y_STACK_TOP - P.CAMBAY_XIAO_USB_Z_FROM_TOP                  # connector centre height (nominal)
USB_SILL_Y = Y_BOARD0 + P.CAMBAY_USB_SILL_ABOVE_SEAT                 # 10.9
assert USB_YC - P.CAMBAY_USB_PLUG_H / 2 - P.CAMBAY_USB_PLAY >= USB_SILL_Y - 1e-9   # plug clears the sill
assert USB_YC + P.CAMBAY_USB_PLUG_H / 2 < H_CAV - 1.0                # and the cover lip


# --- geometry helpers --------------------------------------------------------------
def _box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    return (cq.Workplane("XY")
            .box(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0), centered=False)
            .translate((min(x0, x1), min(y0, y1), min(z0, z1))))


def _rbox(x0, x1, y0, y1, r0, r1) -> cq.Workplane:
    """Box given in (x, y, r) with r the radial coordinate (z = S * r)."""
    return _box(x0, x1, y0, y1, S * r0, S * r1)


def _prism_xr(pts, y0, y1) -> cq.Workplane:
    """Extrude a polygon given in (x, r) from y0 up to y1."""
    wp = cq.Workplane("XZ").workplane(offset=-y1)
    return wp.polyline([(x, S * r) for x, r in pts]).close().extrude(y1 - y0)


def _cyl_y(x, r, d, y0, y1) -> cq.Workplane:
    return (cq.Workplane("XZ").workplane(offset=-y1)
            .center(x, S * r).circle(d / 2).extrude(y1 - y0))


def _frustum_y(x, r, size_top, y_top, size_bot, y_bot) -> cq.Workplane:
    wp = (cq.Workplane("XZ").workplane(offset=-y_top).center(x, S * r)
          .rect(size_top, size_top)
          .workplane(offset=y_top - y_bot).rect(size_bot, size_bot).loft(combine=True))
    return wp


def _frustum_rect_y(x, r, sx_top, sr_top, y_top, sx_bot, sr_bot, y_bot) -> cq.Workplane:
    return (cq.Workplane("XZ").workplane(offset=-y_top).center(x, S * r)
            .rect(sx_top, sr_top)
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


# --- features --------------------------------------------------------------------
def _ribs() -> cq.Workplane:
    """Two flat gusset ribs from the neck side walls back to the box wall."""
    ribs = []
    p0 = (OUT_HALF_X - 0.5, 76.0)
    p1 = (RIB_X_MAX, 56.0)
    dx, dr = p1[0] - p0[0], p1[1] - p0[1]
    n = math.hypot(dx, dr)
    nx, nr = -dr / n * P.CAMBAY_RIB_T / 2, dx / n * P.CAMBAY_RIB_T / 2
    for sx in (1, -1):
        pts = [(sx * (p0[0] + nx), p0[1] + nr), (sx * (p1[0] + nx), p1[1] + nr),
               (sx * (p1[0] - nx), p1[1] - nr), (sx * (p0[0] - nx), p0[1] - nr)]
        ribs.append(_prism_xr(pts, 0.0, P.CAMBAY_RIB_H))
    return _union(ribs)


def _usb_notch_cutter() -> cq.Workplane:
    """Open-top USB-C notch through the +X wall (closed by the cover): 15 wide, sill 1 mm above
    the board seat, open up to the wall top.  Passes a 13 x 8 plug overmould with +-1 mm play."""
    return _rbox(CAV_HALF_X - 1.0, OUT_HALF_X + 1.0, USB_SILL_Y, H_CAV + 1.0,
                 BOARD_CR - USB_NOTCH_W / 2, BOARD_CR + USB_NOTCH_W / 2)


def _vent_cutters() -> list:
    """Passive-airflow slots (never over the lens): 3 through the XIAO -X wall, 2.0 mm ligaments.
    The +X wall carries the USB notch."""
    cut = []
    sw = 2.0                                           # slot width
    for rr in (BOARD_CR - 5.5, BOARD_CR, BOARD_CR + 5.5):
        cut.append(_rbox(-OUT_HALF_X - 1.0, -CAV_HALF_X + 1.0, Y_BOARD0 + 1.0, Y_BOARD0 + 9.0,
                         rr - sw / 2, rr + sw / 2))
    return cut


TIE_R = (NECK_RC - 4.0, NECK_RC + 4.0)    # wire strain-relief ties: floor slot pairs in the neck
TIE_X = (-4.5, 4.5)


def _tie_cutters() -> list:
    """Two zip-tie loops for the wire bundle: each is a pair of 3.8 x 1.8 floor slots
    (x = -4.5 / +4.5) straddling the bundle; the tie runs under the floor between them."""
    return [_rbox(xx - 0.9, xx + 0.9, -OVERTRAVEL, FLOOR_T + OVERTRAVEL, rr - 1.9, rr + 1.9)
            for rr in TIE_R for xx in TIE_X]


def _lens_cutters() -> list:
    """Window through floor + cradle block (the tunnel is the hood) with a 45 deg chamfer on the
    outer (bottom) mouth.  14.25 (X) x 16.4 (R): the 8 mm barrel clears for +-4 mm of lens position."""
    r = BOARD_CR + P.CAMBAY_LENS_DR
    c = P.CAMBAY_LENS_CHAMFER
    tunnel = _box(WIN_X0, WIN_X1, -OVERTRAVEL, Y_BOARD0 + OVERTRAVEL, S * r - WIN_R / 2, S * r + WIN_R / 2)
    flare = _frustum_rect_y(WIN_XC, r, WIN_X, WIN_R, c, WIN_X + 2 * c, WIN_R + 2 * c, 0.0)
    flare_ext = _box(WIN_X0 - c, WIN_X1 + c, -OVERTRAVEL, 0.0, S * r - WIN_R / 2 - c, S * r + WIN_R / 2 + c)
    return [tunnel, flare, flare_ext]


def _locator_ribs() -> cq.Workplane:
    """Soft locating ribs on the two long cradle walls (0.4 proud, from the seat up 8 mm): the
    17.8 mm board is held without play, a slightly bigger board squeezes them instead of jamming."""
    t, w = P.CAMBAY_LOCATOR_RIB_T, P.CAMBAY_LOCATOR_RIB_W
    out = []
    for xc in (-8.0, 7.0):          # both clear of the |x| < 4 wire gap in the neck-side fence
        out.append(_rbox(xc - w / 2, xc + w / 2, Y_BOARD0 - 0.2, Y_BOARD0 + 8.0, HEAD_R0 - 0.1, HEAD_R0 + t))
        out.append(_rbox(xc - w / 2, xc + w / 2, Y_BOARD0 - 0.2, Y_BOARD0 + 8.0, HEAD_R1 - t, HEAD_R1 + 0.1))
    return _union(out)


def _columns() -> cq.Workplane:
    return _union([_cyl_y(sx * COL_X, COL_R, COL_OD, 0.0, H_CAV) for sx in (1, -1)])


def _column_holes() -> list:
    return [_cyl_y(sx * COL_X, COL_R, INS_D, H_CAV - INS_DEPTH, H_CAV + 1.0) for sx in (1, -1)]


def make_bay_body() -> cq.Workplane:
    """The bay feature as ONE solid (to be unioned with the box)."""
    outer = (_rbox(-OUT_HALF_X, OUT_HALF_X, 0.0, H_CAV, BODY_R_IN, OUT_R1)
             .union(_columns()).union(_ribs()))
    xiao_cav = _rbox(-CAV_HALF_X, CAV_HALF_X, FLOOR_T, H_CAV + OVERTRAVEL, BODY_R_IN - 1.0, HEAD_R1)
    body = outer.cut(xiao_cav)

    # cradle block under the board (reaches past the window on the neck side), fence on the neck
    # side of the cradle (gap |x| < 4 for the wires), soft locating ribs
    block = _rbox(-CAV_HALF_X, CAV_HALF_X, FLOOR_T - 0.2, Y_BOARD0, BLOCK_R0, HEAD_R1)
    fence_y1 = Y_BOARD0 + P.CAMBAY_FENCE_H
    fences = [_rbox(a, b, FLOOR_T - 0.2, fence_y1, HEAD_R0 - WALL, HEAD_R0)
              for a, b in ((-CAV_HALF_X, -4.0), (4.0, CAV_HALF_X))]
    body = body.union(block).union(_union(fences)).union(_locator_ribs())

    cutters = (_lens_cutters() + [_usb_notch_cutter()] + _vent_cutters()
               + _tie_cutters() + _column_holes())
    return _cut_all(body, cutters)


def make_cover() -> cq.Workplane:
    """Screw-down access cover, built at its assembled height H_CAV.  The outer
    (top) face is flat; lip, board pegs and the antenna corral are on the underside."""
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

    # XIAO hold-down pegs over the four cradle corners (stop CAMBAY_PEG_STOP_ABOVE_SEAT above the seat)
    peg = 2.4
    pegs = []
    for sx in (1, -1):
        for sr in (1, -1):
            cx = sx * (CAV_HALF_X - peg / 2 - 0.2)
            cr = BOARD_CR + sr * (CAV_HALF_R - peg / 2 - 0.2)
            pegs.append(_rbox(cx - peg / 2, cx + peg / 2, Y_BOARD0 + P.CAMBAY_PEG_STOP_ABOVE_SEAT, y0 + 0.1,
                              cr - peg / 2, cr + peg / 2))
    # antenna corral on the UNDERSIDE (flat outer face stays free for printing)
    rail_t, rail_h = WALL, 1.5
    ant_r0 = 65.0
    ant_r1 = ant_r0 + P.CAMBAY_ANT_L + 0.6
    iw = P.CAMBAY_ANT_W / 2 + 0.3
    rails = [_rbox(iw, iw + rail_t, y0 - rail_h, y0 + 0.1, ant_r0, ant_r1),
             _rbox(-iw - rail_t, -iw, y0 - rail_h, y0 + 0.1, ant_r0, ant_r1),
             _rbox(-iw - rail_t, iw + rail_t, y0 - rail_h, y0 + 0.1, ant_r1, ant_r1 + rail_t)]
    cover = cover.union(_union(lips)).union(_union(pegs)).union(_union(rails))

    cuts = [_cyl_y(sx * COL_X, COL_R, SCREW_M3, y0 - 2, y1 + 1) for sx in (1, -1)]
    for vx in (-6.0, 0.0, 6.0):
        cuts.append(_rbox(vx - 1.0, vx + 1.0, y0 - 2, y1 + 1, COVER_R0 + 2.0, COVER_R0 + 7.0))
    return _cut_all(cover, cuts)


def wire_window_cutter() -> cq.Workplane:
    """Rectangular wire window through the shared wall (box pocket <-> bay
    cavity), flared at both mouths so wires cannot chafe on a sharp edge."""
    fl = P.CAMBAY_WIN_FLARE
    pocket_r = P.CAMBAY_BOX_POCKET_HALF
    r_in, r_out = pocket_r - 2.0, 66.0
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
    bay_flare = flare(box_wall_r(WIN_Y) - 2.0, 66.0, 6.0)
    return straight.union(pocket_flare).union(bay_flare)


def combine(box: cq.Workplane) -> cq.Workplane:
    """Union the bay onto the box (box given in the BAY frame) and cut the wire
    window.  Returns a new combined solid (the window is the ONLY cut in the box)."""
    return box.union(make_bay_body()).cut(wire_window_cutter())


def make():
    """Standalone bay solids: (bay_body, cover)."""
    return make_bay_body(), make_cover()


# --- optical pose (bay frame) --------------------------------------------------------
LENS_CENTER_BAY = (LENS_X, LENS_FRONT_Y, S * (BOARD_CR + P.CAMBAY_LENS_DR))   # lens glass centre
OPTICAL_AXIS_BAY = (0.0, -1.0, 0.0)


if __name__ == "__main__":
    body, cover = make()
    for n, s in (("bay_body", body), ("cover", cover)):
        bb = s.val().BoundingBox()
        print(f"{n}: valid={s.val().isValid()} solids={len(s.solids().vals())} "
              f"bbox x[{bb.xmin:.2f},{bb.xmax:.2f}] y[{bb.ymin:.2f},{bb.ymax:.2f}] "
              f"z[{bb.zmin:.2f},{bb.zmax:.2f}] vol={s.val().Volume():.0f} mm3")
