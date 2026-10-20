"""
Claw CAMERA BAY -- XIAO ESP32-S3 Sense camera + GY-521 IMU enclosure that is
UNIONED onto the gripper electrical box ("Gripper_Electric_Housing_Base (2)" in
solidworks/gripper_v6_2026-10-20/LaundryGripperAssem1.STEP, read-only).

The bay is a closed-wall pod hanging off ONE side wall of the box (the narrow
-Z side, see CAMBAY_SIDE), standing on the same print bed plane as the box's
bottom flange, so the whole box+bay prints without supports.  The camera
looks straight DOWN (-Y, parallel to the tube); its optical axis is
CAMBAY_CAM_R = 90 mm from the tube axis.

--------------------------------------------------------------------------
Bay frame (this file's local frame; v6 world = local + BAY_ORIGIN_WORLD)
--------------------------------------------------------------------------
  origin  : on the tube axis, in the box BOTTOM plane (v6 world Y = 1091.19)
  axes    : parallel to the v6 world axes.  +Y = up (toward the box lid),
            tube axis = Y axis, optical axis = -Y, bay lies on -Z
            (r = radial distance outward from the tube axis, z = SIDE * r)
  v6 world frame -> bay frame:  translate by (-951.8475, -1091.1905, -1103.9899)

--------------------------------------------------------------------------
Parts / solids
--------------------------------------------------------------------------
  bay_body : the bay feature (walls, floor, lens cradle block with tunnel,
             gusset ribs, cover columns, IMU posts, USB window, vents).  It is
             a standalone single solid and is meant to be unioned on the box.
  cover    : separate printed access cover (screw-down, 2x M3x8 into heat-set
             inserts), carries board hold-down pegs, antenna corral, vents.
  combine(box) -> box + bay_body with the wire window cut through the shared
             wall (the ONLY cut made into the box, plus the shallow IMU pilot
             hole 1 that threads into the box wall).

--------------------------------------------------------------------------
Stack (heights above the box bottom plane)
--------------------------------------------------------------------------
  0 .. 2.4      bay floor (on the bed)         with 15x15 lens window, 1 mm
                                                outer chamfer
  2.4 .. 6.4    lens cradle block = hood tunnel (window runs through 6.4 mm)
  6.4 .. 21.4   XIAO ESP32-S3 Sense stack (15 mm, camera face down)
  21.4 .. 24.4  wire / antenna-lead headroom, cover pegs hold the board
  24.4 .. 26.8  cover
  IMU (GY-521): board plane parallel to the camera board (both XZ planes), on
  2 posts at 6.0 mm above the floor in the neck between the box and the XIAO.

IMU axis convention (documented for firmware): board plane = bay XZ plane,
long axis (21 mm) along bay X, the mounting-hole row at the bay -X end,
chip face up (+Y).  Map the breakout's silk arrows onto these axes in the
firmware calibration (VERIFY on the real board).

--------------------------------------------------------------------------
Print orientation (no supports for critical surfaces)
--------------------------------------------------------------------------
  Box + bay: as the box prints (bottom flange on the bed, +Y up).  Walls,
  floor, ribs and columns are straight verticals; the only bridges are the
  USB window roof (45 deg chamfered corners) and the wire-window roof.
  Cover: flat on the bed, either face down.

--------------------------------------------------------------------------
VERIFY BEFORE PRINTING (assumed dimensions)
--------------------------------------------------------------------------
  XIAO stack height 15 mm, lens barrel protrusion 4.5 mm, lens position on
  the board (centred), USB-C height above the board, antenna 30 x 10 mm,
  GY-521 hole pitch/edge distance (supplied pitch 15.2 mm is not consistent
  with the 15.6 mm board width), board corner keep-outs under the cover pegs.
"""

from __future__ import annotations

import math

import cadquery as cq

from .. import params as P
from ..params import M3_THREAD_HOLE, SCREW_M3

# --- sign / frame ---------------------------------------------------------------
S = P.CAMBAY_SIDE                       # -1 -> bay on -Z, +1 -> bay on +Z
assert S in (-1, 1)
BAY_ORIGIN_WORLD = (951.8475, 1091.1905, 1103.9899)   # tube axis @ box bottom plane
OVERTRAVEL = 0.5                        # mm, cutter overshoot for clean cuts

# --- derived bay dimensions -----------------------------------------------------
WALL = P.CAMBAY_WALL
FLOOR_T = P.CAMBAY_FLOOR_T
COVER_T = P.CAMBAY_COVER_T
CLR = P.CAMBAY_FIT_CLEAR

# XIAO cradle (head) ------------------------------------------------------------
BOARD_CX = -P.CAMBAY_LENS_DX            # board centre, bay X
BOARD_CR = P.CAMBAY_CAM_R - P.CAMBAY_LENS_DR   # board centre, radial
CAV_HALF_X = P.CAMBAY_XIAO_L / 2 + CLR  # 10.8
CAV_HALF_R = P.CAMBAY_XIAO_W / 2 + CLR  # 9.2
HEAD_R0 = BOARD_CR - CAV_HALF_R         # 80.8  (neck side edge of the XIAO bay)
HEAD_R1 = BOARD_CR + CAV_HALF_R         # 99.2
OUT_HALF_X = CAV_HALF_X + WALL          # 12.8
OUT_R1 = HEAD_R1 + WALL                 # 101.2

BLOCK_H = P.CAMBAY_LENS_BLOCK_H
Y_BOARD0 = FLOOR_T + BLOCK_H                       # 6.4 board seat
Y_BOARD1 = Y_BOARD0 + P.CAMBAY_XIAO_H              # 21.4 stack top
H_CAV = Y_BOARD1 + P.CAMBAY_WIRE_HEADROOM          # 24.4 wall top / cover seat
Y_TOP = H_CAV + COVER_T                            # 26.8 bay top incl. cover

WIN = P.CAMBAY_LENS_WINDOW
assert WIN >= 14.0, "lens window must be >= 14 x 14 mm"
LENS_FRONT_Y = Y_BOARD0 - P.CAMBAY_LENS_BARREL_H   # 1.9 lens glass height

# Neck (IMU) --------------------------------------------------------------------
FENCE_T = WALL
FENCE_R0 = HEAD_R0 - FENCE_T            # 78.8
IMU_R_MAX = FENCE_R0 - CLR              # 78.5
IMU_RC = IMU_R_MAX - P.CAMBAY_IMU_W / 2          # IMU centre (radial)
IMU_XC = 0.0
IMU_HOLE_X = IMU_XC - P.CAMBAY_IMU_L / 2 + P.CAMBAY_IMU_HOLE_EDGE   # -8.0
IMU_HOLES = ((IMU_HOLE_X, IMU_RC - P.CAMBAY_IMU_HOLE_PITCH / 2),
             (IMU_HOLE_X, IMU_RC + P.CAMBAY_IMU_HOLE_PITCH / 2))
IMU_POST_OD = P.CAMBAY_IMU_SCREW_PILOT + 2 * P.CAMBAY_BOSS_WALL
IMU_Y_BOARD = FLOOR_T + P.CAMBAY_IMU_POST_H        # board underside height
BODY_R_IN = 50.0                        # bay solid starts inside the box wall (< 55)

# Wire window -------------------------------------------------------------------
WIN_W, WIN_H, WIN_Y = P.CAMBAY_WIN_W, P.CAMBAY_WIN_H, P.CAMBAY_WIN_Y
WIN_ROOF_CH = 2.5                       # mm, 45 deg roof-corner chamfer
assert WIN_W >= 8.0 and WIN_H >= 6.0
assert P.CAMBAY_BOX_POCKET_FLOOR_Y < WIN_Y - WIN_H / 2, "window must clear the pocket floor"
assert WIN_Y + WIN_H / 2 < P.CAMBAY_BOX_LID_SEAT_Y - 10, "window must sit well below the lid seat"
# corner cable-hole mouths are at |x| >= 41 (diagonal); the window is at |x| <= WIN_W/2 + flare
assert WIN_W / 2 + 6.0 + P.CAMBAY_CORNER_HOLE_KEEPOUT < 41.0

# Cover screw columns ------------------------------------------------------------
COL_OD = M3_THREAD_HOLE + 2 * P.CAMBAY_BOSS_WALL    # 9.0 (insert hole + 2.5 wall)
COL_X = OUT_HALF_X + COL_OD / 2 - 1.5               # centre, overlapping the wall
COL_R = P.CAMBAY_COVER_SCREW_R
COL_INSERT_DEPTH = 6.0

# Corner-line (cable) constraints --------------------------------------------------
RIB_X_MAX = P.CAMBAY_RIB_SPAN_X
assert RIB_X_MAX + P.CAMBAY_CORNER_HOLE_KEEPOUT < P.CAMBAY_CORNER_HOLE_EXIT_XZ

# Cover end (kept just short of the curved box wall) ---------------------------------


def box_wall_r(y: float) -> float:
    """Radial position of the box outer wall at height y (flange + R75 blend)."""
    if y <= P.CAMBAY_BOX_FLANGE_T:
        return P.CAMBAY_BOX_FLANGE_HALF
    cz = P.CAMBAY_BOX_UPPER_HALF + P.CAMBAY_BOX_BLEND_R
    dy = P.CAMBAY_BOX_BLEND_TOP_Y - min(y, P.CAMBAY_BOX_BLEND_TOP_Y)
    return cz - math.sqrt(P.CAMBAY_BOX_BLEND_R ** 2 - dy ** 2)


COVER_R0 = box_wall_r(Y_TOP) + 0.8      # cover inner edge: 0.8 mm off the box wall


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
    """Square-section frustum from y_top (size_top) down to y_bot (size_bot)."""
    wp = (cq.Workplane("XZ").workplane(offset=-y_top).center(x, S * r)
          .rect(size_top, size_top)
          .workplane(offset=y_top - y_bot).rect(size_bot, size_bot).loft(combine=True))
    return wp


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
    """Two flat gusset ribs from the bay side walls back to the box wall.
    Direction in plan: from (OUT_HALF_X, r=82) toward (RIB_X_MAX, r=56)."""
    ribs = []
    p0 = (OUT_HALF_X - 0.5, 82.0)
    p1 = (RIB_X_MAX, 56.0)
    dx, dr = p1[0] - p0[0], p1[1] - p0[1]
    n = math.hypot(dx, dr)
    nx, nr = -dr / n * P.CAMBAY_RIB_T / 2, dx / n * P.CAMBAY_RIB_T / 2
    for sx in (1, -1):
        pts = [(sx * (p0[0] + nx), p0[1] + nr), (sx * (p1[0] + nx), p1[1] + nr),
               (sx * (p1[0] - nx), p1[1] - nr), (sx * (p0[0] - nx), p0[1] - nr)]
        ribs.append(_prism_xr(pts, 0.0, P.CAMBAY_RIB_H))
    return _union(ribs)


def _usb_window_cutter() -> cq.Workplane:
    """USB-C plug opening through the +X wall; roof has 45 deg chamfered
    corners (no bridging)."""
    yc = Y_BOARD1 - P.CAMBAY_XIAO_USB_Z_FROM_TOP
    w, h, ch = P.CAMBAY_USB_W, P.CAMBAY_USB_H, 2.0
    y0, y1 = yc - h / 2, yc + h / 2
    r0 = BOARD_CR - w / 2
    r1 = BOARD_CR + w / 2
    pts = [(r0, y0), (r1, y0), (r1, y1 - ch), (r1 - ch, y1), (r0 + ch, y1), (r0, y1 - ch)]
    # polygon in (r, y) extruded along X through the +X wall
    wp = cq.Workplane("YZ").workplane(offset=CAV_HALF_X - 1.0)
    prof = wp.polyline([(py, S * pr) for pr, py in pts]).close().extrude(WALL + 2.0)
    return prof


def _vent_cutters() -> list:
    cut = []
    sw = 2.0                               # slot width
    # -X wall (XIAO zone): 3 slots facing the board stack
    for rr in (BOARD_CR - 4.0, BOARD_CR, BOARD_CR + 4.0):
        cut.append(_rbox(-OUT_HALF_X - 1, -CAV_HALF_X + 1, 9.0, 17.0, rr - sw / 2, rr + sw / 2))
    # +X wall (IMU zone): 3 slots
    for rr in (IMU_RC - 4.0, IMU_RC, IMU_RC + 4.0):
        cut.append(_rbox(CAV_HALF_X - 1, OUT_HALF_X + 1, 9.0, 17.0, rr - sw / 2, rr + sw / 2))
    return cut


TIE_R = (IMU_RC - 4.0, IMU_RC + 4.0)       # strain-relief tie slots in the -X wall
TIE_Y = (13.0, 17.0)


def _tie_cutters() -> list:
    return [_rbox(-OUT_HALF_X - 1, -CAV_HALF_X + 1, TIE_Y[0], TIE_Y[1], rr - 0.9, rr + 0.9)
            for rr in TIE_R]


def _lens_cutters() -> list:
    """15x15 window through floor + cradle block (the tunnel is the hood),
    with a 45 deg chamfer on the outer (bottom) mouth."""
    x, r = 0.0, P.CAMBAY_CAM_R
    c = P.CAMBAY_LENS_CHAMFER
    tunnel = _box(x - WIN / 2, x + WIN / 2, -OVERTRAVEL, Y_BOARD0 + OVERTRAVEL,
                  S * r - WIN / 2, S * r + WIN / 2)
    flare = _frustum_y(x, r, WIN, c, WIN + 2 * c, 0.0)
    flare_ext = _box(x - WIN / 2 - c, x + WIN / 2 + c, -OVERTRAVEL, 0.0,
                     S * r - WIN / 2 - c, S * r + WIN / 2 + c)
    return [tunnel, flare, flare_ext]


def _imu_posts() -> cq.Workplane:
    posts = []
    for hx, hr in IMU_HOLES:
        p = _cyl_y(hx, hr, IMU_POST_OD, FLOOR_T - 0.2, IMU_Y_BOARD)
        # keep posts out of the XIAO bay keep-out (board stack sits above 6.4)
        p = p.intersect(_rbox(-50, 50, 0, 20, 0, HEAD_R0 - 0.0))
        posts.append(p)
    return _union(posts)


def _imu_pilot_cutters() -> list:
    return [_cyl_y(hx, hr, P.CAMBAY_IMU_SCREW_PILOT, IMU_Y_BOARD - 6.0, IMU_Y_BOARD + 1.0)
            for hx, hr in IMU_HOLES]


def _columns() -> cq.Workplane:
    cols = []
    for sx in (1, -1):
        cols.append(_cyl_y(sx * COL_X, COL_R, COL_OD, 0.0, H_CAV))
    return _union(cols)


def _column_holes() -> list:
    return [_cyl_y(sx * COL_X, COL_R, M3_THREAD_HOLE, H_CAV - COL_INSERT_DEPTH, H_CAV + 1.0)
            for sx in (1, -1)]


def make_bay_body() -> cq.Workplane:
    """The bay feature as ONE solid (to be unioned with the box)."""
    outer = _rbox(-OUT_HALF_X, OUT_HALF_X, 0.0, H_CAV, BODY_R_IN, OUT_R1)
    outer = outer.union(_columns()).union(_ribs())
    cavity = _rbox(-CAV_HALF_X, CAV_HALF_X, FLOOR_T, H_CAV + OVERTRAVEL,
                   BODY_R_IN - 1.0, HEAD_R1)
    body = outer.cut(cavity)

    # lens cradle block (under the XIAO) + fence between the XIAO bay and the neck
    block = _rbox(-CAV_HALF_X, CAV_HALF_X, FLOOR_T - 0.2, Y_BOARD0, HEAD_R0, HEAD_R1)
    fence_y1 = Y_BOARD1 - 2.0
    fences = [_rbox(a, b, FLOOR_T - 0.2, fence_y1, FENCE_R0, HEAD_R0)
              for a, b in ((-CAV_HALF_X, -4.0), (4.0, CAV_HALF_X))]
    body = body.union(block).union(_union(fences)).union(_imu_posts())

    cutters = (_lens_cutters() + [_usb_window_cutter()] + _vent_cutters()
               + _tie_cutters() + _column_holes() + _imu_pilot_cutters())
    return _cut_all(body, cutters)


def make_cover() -> cq.Workplane:
    """Screw-down access cover (placed at its assembled height H_CAV)."""
    y0, y1 = H_CAV, H_CAV + COVER_T
    plate = _rbox(-OUT_HALF_X, OUT_HALF_X, y0, y1, COVER_R0, OUT_R1)
    ears = _union([_cyl_y(sx * COL_X, COL_R, COL_OD, y0, y1) for sx in (1, -1)])
    cover = plate.union(ears)

    # registration lip (U-frame inside the cavity walls), 2.0 x 1.0 mm
    lip_t, lip_h, lip_gap = WALL, 1.0, 0.2
    lx = CAV_HALF_X - lip_gap
    lr1 = HEAD_R1 - lip_gap
    lip_r0 = COVER_R0 + 3.0
    lips = [_rbox(lx - lip_t, lx, y0 - lip_h, y0 + 0.1, lip_r0, lr1),
            _rbox(-lx, -lx + lip_t, y0 - lip_h, y0 + 0.1, lip_r0, lr1),
            _rbox(-lx, lx, y0 - lip_h, y0 + 0.1, lr1 - lip_t, lr1)]
    # board hold-down pegs over the XIAO corners (0.3 mm above the stack top)
    peg = 2.4
    peg_y0 = Y_BOARD1 + CLR
    pegs = []
    for sx in (1, -1):
        for sr in (1, -1):
            cx = sx * (P.CAMBAY_XIAO_L / 2 - peg / 2 - 0.2)
            cr = BOARD_CR + sr * (P.CAMBAY_XIAO_W / 2 - peg / 2 - 0.2)
            pegs.append(_rbox(cx - peg / 2, cx + peg / 2, peg_y0, y0 + 0.1,
                              cr - peg / 2, cr + peg / 2))
    # antenna corral on the top face (rails 2.0 x 1.5 mm)
    rail_t, rail_h = WALL, 1.5
    ant_r0 = BOARD_CR - 22.0
    ant_r1 = ant_r0 + P.CAMBAY_ANT_L + 0.6
    iw = P.CAMBAY_ANT_W / 2 + 0.3
    rails = [_rbox(iw, iw + rail_t, y1 - 0.1, y1 + rail_h, ant_r0, ant_r1),
             _rbox(-iw - rail_t, -iw, y1 - 0.1, y1 + rail_h, ant_r0, ant_r1),
             _rbox(-iw - rail_t, iw + rail_t, y1 - 0.1, y1 + rail_h, ant_r1, ant_r1 + rail_t)]
    cover = cover.union(_union(lips)).union(_union(pegs)).union(_union(rails))

    # cuts: screw holes, U.FL lead hole, vent slots
    cuts = [_cyl_y(sx * COL_X, COL_R, SCREW_M3, y0 - 1, y1 + 1) for sx in (1, -1)]
    cuts.append(_cyl_y(0.0, ant_r0 - 3.0, 3.0, y0 - 1, y1 + 1))
    for vx in (-6.0, 0.0, 6.0):
        cuts.append(_rbox(vx - 1.0, vx + 1.0, y0 - 1, y1 + 1, COVER_R0 + 2.0, COVER_R0 + 7.0))
    return _cut_all(cover, cuts)


def wire_window_cutter() -> cq.Workplane:
    """Rectangular wire window through the shared wall (box pocket <-> bay
    cavity), flared at both mouths so wires cannot chafe on a sharp edge."""
    fl = P.CAMBAY_WIN_FLARE
    pocket_r = P.CAMBAY_BOX_POCKET_HALF
    r_in, r_out = pocket_r - 2.0, 66.0          # pocket side overshoot, bay-cavity side
    z_a, z_b = S * r_in, S * r_out
    # roof corners chamfered 45 deg (WIN_ROOF_CH) so the window needs no wide bridge
    ch = WIN_ROOF_CH
    y0w, y1w = WIN_Y - WIN_H / 2, WIN_Y + WIN_H / 2
    prof = [(-WIN_W / 2, y0w), (WIN_W / 2, y0w), (WIN_W / 2, y1w - ch),
            (WIN_W / 2 - ch, y1w), (-WIN_W / 2 + ch, y1w), (-WIN_W / 2, y1w - ch)]
    straight = (cq.Workplane("XY").workplane(offset=min(z_a, z_b)).polyline(prof).close()
                .extrude(abs(z_b - z_a)))

    def flare(r_small, r_big, grow):
        wp = (cq.Workplane("XY").workplane(offset=S * r_small).center(0, WIN_Y)
              .rect(WIN_W, WIN_H)
              .workplane(offset=S * (r_big - r_small)).rect(WIN_W + 2 * grow, WIN_H + 2 * grow)
              .loft(combine=True))
        return wp

    pocket_flare = flare(pocket_r + fl, pocket_r - 1.0, fl + 1.0)       # 45 deg at the pocket wall
    bay_flare = flare(box_wall_r(WIN_Y) - 2.0, 66.0, 6.0)              # chamfers the outer mouth
    return straight.union(pocket_flare).union(bay_flare)


def combine(box: cq.Workplane) -> cq.Workplane:
    """Union the bay onto the box (box given in the BAY frame) and cut the wire
    window + IMU pilot hole 1.  Returns a new combined solid."""
    comb = box.union(make_bay_body())
    comb = comb.cut(wire_window_cutter())
    comb = _cut_all(comb, _imu_pilot_cutters())
    return comb


def make():
    """Standalone bay solids: (bay_body, cover)."""
    return make_bay_body(), make_cover()


# --- optical pose (bay frame -> reported pose) --------------------------------------
LENS_CENTER_BAY = (0.0, LENS_FRONT_Y, S * P.CAMBAY_CAM_R)   # lens glass centre
OPTICAL_AXIS_BAY = (0.0, -1.0, 0.0)


if __name__ == "__main__":
    print("bay_body / cover built from parameters (see scripts/build_claw_camera_bay.py "
          "for the combined export with the v6 box)")
    body, cover = make()
    for n, s in (("bay_body", body), ("cover", cover)):
        bb = s.val().BoundingBox()
        print(f"{n}: valid={s.val().isValid()} solids={len(s.solids().vals())} "
              f"bbox x[{bb.xmin:.2f},{bb.xmax:.2f}] y[{bb.ymin:.2f},{bb.ymax:.2f}] "
              f"z[{bb.zmin:.2f},{bb.zmax:.2f}] vol={s.val().Volume():.0f} mm3")
