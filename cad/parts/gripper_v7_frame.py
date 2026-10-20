"""
Gripper v7 -- open frame: lower plate, upper plate (servo), tie columns, tube socket saddles,
mesh guard bands.  Local frame (z = 0 on the lower-plate INNER face).

Lower plate  z [-6, 0]   : pocketed PETG plate, Ø7.05 blind pin seats (4 mm), inner-race rings
                           Ø9 x 0.85, pinion pilot post, six tie columns (integral, 42 mm, hollow for
                           the M3 bolt), lower tube saddle, main-mesh (pinion/36T) guard bands.
Upper plate  z [42, 48]  : pocketed PETG plate with the MG996R body cutout (ears rest on the top
                           face, M2.5 heat-set inserts), pin seats, race rings, upper saddle,
                           link ground-pivot stubs (2) and the sync-mesh (24T/24T) guard bands.

Tie bolts: M3x50 socket cap from the upper-plate top (counterbore) down through the column into a
nyloc in a hex pocket in the lower-plate outer face.  The tube cross-bolt (M3x50, parallel to z,
through a drilled tube hole) uses the same pattern at (0, tube_end + 14).

Print orientation: both plates OUTER face down (flat); columns, saddles, guards, stubs point up.
The upper plate is printed upside-down relative to its assembly position (STL export flips it).
"""

from __future__ import annotations

import math

import cadquery as cq
import numpy as np

from cad import params as P
from cad.parts import gripper_v7_gears as GR
from cad.parts import gripper_v7_hw as HW
from cad.parts import gripper_v7_kin as K

T = P.GRIPV7_PLATE_T
G = P.GRIPV7_PLATE_GAP
LP_Z0, LP_Z1 = -T, 0.0                  # lower plate
UP_Z0, UP_Z1 = G, G + T                 # upper plate
C = GR.C_AXIS
F = GR.F_AXIS
S = GR.S_AXIS
PIN_XY = (C, F)
TUBE_Z = P.GRIPV7_TUBE_Z
BORE_R = P.GRIPV7_TUBE_OD / 2.0 + P.GRIPV7_TUBE_FIT
XBOLT_XY = (0.0, P.GRIPV7_TUBE_END_Y + P.GRIPV7_XBOLT_Y_FROM_END)
SOCKET_Y0 = P.GRIPV7_TUBE_END_Y
SOCKET_Y1 = P.GRIPV7_TUBE_END_Y + P.GRIPV7_TUBE_INSERT
RACE_R = P.GRIPV7_RACE_BOSS_D / 2.0
PIN_R = P.GRIPV7_PIN_HOLE_D / 2.0
LP_RACE_TOP = P.GRIPV7_GEAR_Z0 - P.GRIPV7_RACE_AXIAL_GAP                  # 0.85
UP_RACE_BOT = P.GRIPV7_L2_Z1 + P.GRIPV7_RACE_AXIAL_GAP                    # 37.15
FOLLOWER_RACE_TOP = GR.FOLLOWER_Z0 - P.GRIPV7_RACE_AXIAL_GAP               # 16.85
MAIN_GUARD_Z1 = P.GRIPV7_L1_Z1 - P.GRIPV7_GUARD_Z_MARGIN                  # 16.5
SYNC_GUARD_Z0 = P.GRIPV7_L2_Z0 + P.GRIPV7_GUARD_Z_MARGIN                  # 17.5


# ---- 2D/3D helpers ----------------------------------------------------------------------------
def _cyl(r, z0, z1, x=0.0, y=0.0):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)


def _rrect(x0, x1, y0, y1, r, z0, z1):
    return (cq.Workplane("XY").workplane(offset=z0).center((x0 + x1) / 2, (y0 + y1) / 2)
            .rect(x1 - x0, y1 - y0).extrude(z1 - z0).edges("|Z").fillet(r))


def _bar(p, q, w, z0, z1):
    p, q = np.asarray(p, float), np.asarray(q, float)
    d = q - p
    n = np.array([-d[1], d[0]]) / np.linalg.norm(d) * w / 2.0
    pts = [tuple(p + n), tuple(q + n), tuple(q - n), tuple(p - n)]
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)


def _poly(pts, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).polyline([tuple(p) for p in pts]).close().extrude(z1 - z0)


def _hex_pocket(x, y, z_face, depth, down_from_top):
    """Hex pocket AF NUT_POCKET_AF; z_face is the open face; pocket goes `depth` into the part
    (toward +z when down_from_top is False, toward -z when True)."""
    d = P.GRIPV7_NUT_POCKET_AF / math.cos(math.radians(30.0))
    if down_from_top:
        return cq.Workplane("XY").workplane(offset=z_face - depth).center(x, y).polygon(6, d).extrude(depth + 0.01)
    return cq.Workplane("XY").workplane(offset=z_face - 0.01).center(x, y).polygon(6, d).extrude(depth + 0.01)


def outline(z0: float, z1: float, p_tabs: bool = False) -> cq.Workplane:
    s = None
    for (x0, x1, y0, y1, r) in P.GRIPV7_OUTLINE_RECTS:
        b = _rrect(x0, x1, y0, y1, r, z0, z1)
        s = b if s is None else s.union(b)
    if p_tabs:
        px, py = P.GRIPV7_LINK_GROUND
        hw = P.GRIPV7_P_TAB_HALF_W
        for sx in (1, -1):
            s = s.union(_rrect(sx * px - hw, sx * px + hw, py - 10.0, py + 12.0, 5.0, z0, z1))
    return s


def _windows(z0, z1, keep: cq.Workplane, p_tabs: bool) -> cq.Workplane:
    """Through lightening windows: outline offset inward by the rim, minus the keep zones."""
    ol = outline(z0 - 1.0, z1 + 1.0, p_tabs)
    wire = ol.faces("<Z").wires().val()
    inner = wire.offset2D(-P.GRIPV7_RIM_W)[0]
    region = cq.Workplane("XY").workplane(offset=z0 - 1.0).add(cq.Face.makeFromWires(inner)) \
        .toPending().extrude(z1 - z0 + 2.0)
    return region.cut(keep)


def _keep_common(z0, z1):
    zz0, zz1 = z0 - 2.0, z1 + 2.0
    k = None
    rr = P.GRIPV7_RIB_W
    def add(s):
        nonlocal k
        k = s if k is None else k.union(s)
    for ax in (C, F):
        add(_cyl(RACE_R + 3.5 + 1.0, zz0, zz1, *ax))
    for t in P.GRIPV7_TIE_XY:
        add(_cyl(P.GRIPV7_TIE_COL_OD / 2.0 + 2.0, zz0, zz1, *t))
    add(_bar(C, F, rr + 1.0, zz0, zz1))
    add(_bar(F, P.GRIPV7_TIE_XY[0], rr, zz0, zz1))
    add(_bar(C, P.GRIPV7_TIE_XY[1], rr, zz0, zz1))
    add(_bar(C, S, rr + 1.0, zz0, zz1))
    add(_bar(F, S, rr, zz0, zz1))
    # under the socket the plate stays solid only below the saddle ribs (3 stations) and the neck bar
    for yc, wy in ((SOCKET_Y0 + P.GRIPV7_SADDLE_RIB_T / 2.0, P.GRIPV7_SADDLE_RIB_T + 2.0),
                   (XBOLT_XY[1], 8.0 + 2.0),
                   (SOCKET_Y1 - P.GRIPV7_SADDLE_RIB_T / 2.0, P.GRIPV7_SADDLE_RIB_T + 2.0)):
        add(_bar((-25.0, yc), (25.0, yc), wy, zz0, zz1))
    add(_bar(S, (0.0, SOCKET_Y0), rr + 2.0, zz0, zz1))
    return k


# ---- tube saddles ----------------------------------------------------------------------------
def _bore(z_center=TUBE_Z):
    return (cq.Workplane("XZ").workplane(offset=-(SOCKET_Y0 - 1.0)).center(0, z_center).circle(BORE_R)
            .extrude(-(P.GRIPV7_TUBE_INSERT + 2.0)))


def _saddle(lower: bool) -> cq.Workplane:
    """Ribbed half saddle.  lower: grows from LP (z 0) up to the tube equator (minus half the split
    gap); upper: grows from UP (z = G) down to the equator."""
    half = P.GRIPV7_SADDLE_SPLIT_GAP / 2.0
    if lower:
        z_plate, z_end = 0.0, TUBE_Z - half
    else:
        z_plate, z_end = G, TUBE_Z + half
    z_lo, z_hi = min(z_plate, z_end), max(z_plate, z_end)
    w = P.GRIPV7_SADDLE_HALF_W
    L = P.GRIPV7_TUBE_INSERT
    t = P.GRIPV7_SADDLE_RIB_T
    ribs = None
    for yc in (SOCKET_Y0 + t / 2.0, XBOLT_XY[1], SOCKET_Y1 - t / 2.0):
        r = (cq.Workplane("XY").workplane(offset=z_lo).center(0, yc).rect(2 * w, t if yc != XBOLT_XY[1] else 8.0)
             .extrude(z_hi - z_lo))
        ribs = r if ribs is None else ribs.union(r)
    # half shell: cylinder R_bore + wall along y, clipped to this half
    shell = (cq.Workplane("XZ").workplane(offset=-SOCKET_Y0).center(0, TUBE_Z)
             .circle(BORE_R + P.GRIPV7_SADDLE_SHELL_WALL).extrude(-L))
    clip = cq.Workplane("XY").workplane(offset=z_lo).center(0, (SOCKET_Y0 + SOCKET_Y1) / 2.0) \
        .rect(2 * w, L).extrude(z_hi - z_lo)
    shell = shell.intersect(clip)
    s = ribs.union(shell)
    # tie-column towers beside the tube are separate (columns); keep the saddle clear of them
    return s.cut(_bore())


def _tie_hole(x, y, z0, z1):
    return _cyl(P.GRIPV7_TIE_HOLE_D / 2.0, z0, z1, x, y)


# ---- guards -----------------------------------------------------------------------------------
def _ext_tangent_walls(c1, r1, c2, r2, t):
    """Quads (thickness t, outward) on both outer common tangents of two circles."""
    c1, c2 = np.asarray(c1, float), np.asarray(c2, float)
    d = c2 - c1
    L = np.linalg.norm(d)
    dh = d / L
    perp = np.array([-dh[1], dh[0]])
    a = math.acos((r1 - r2) / L)
    out = []
    for sgn in (+1, -1):
        n = math.cos(a) * dh + sgn * math.sin(a) * perp
        p1, p2 = c1 + r1 * n, c2 + r2 * n
        out.append([tuple(p1), tuple(p2), tuple(p2 + t * n), tuple(p1 + t * n)])
    return out


def _lug_sweep_notch(z0, z1):
    """Union of both lug sweeps (compound right, follower mirrored), inflated 1 mm, over [z0, z1]."""
    fb = K.default()
    notch = None
    for th in np.linspace(fb.theta_c, fb.theta_open, 10):
        for mirror in (False, True):
            ang = 180.0 - th if mirror else th
            cx = F[0] if mirror else C[0]
            piece = GR._lug_profile(ang, P.GRIPV7_CRANK_R, z0, z1, margin=1.0).translate((cx, 0, 0))
            notch = piece if notch is None else notch.union(piece)
    return notch


def main_guard() -> cq.Workplane:
    """Pinion/36T mesh: two tangent walls from the lower plate up to just above the layer."""
    r_c = GR.tip_r(P.GRIPV7_Z_MAIN) + P.GRIPV7_GUARD_CLEAR
    r_s = GR.tip_r(P.GRIPV7_Z_PINION) + P.GRIPV7_GUARD_CLEAR
    g = None
    for q in _ext_tangent_walls(C, r_c, S, r_s, P.GRIPV7_GUARD_T):
        w = _poly(q, -0.5, MAIN_GUARD_Z1)
        g = w if g is None else g.union(w)
    return g


def sync_guard() -> cq.Workplane:
    """24T/24T mesh: two walls (y = +-(tip + clearance)) hanging from the upper plate; the part that
    the crank lugs sweep through is trimmed to a skirt above the lug band."""
    r = GR.tip_r(P.GRIPV7_Z_SYNC) + P.GRIPV7_GUARD_CLEAR
    z_top = UP_Z0 + 0.5
    g = None
    for q in _ext_tangent_walls(F, r, C, r, P.GRIPV7_GUARD_T):
        w = _poly(q, SYNC_GUARD_Z0, z_top)
        g = w if g is None else g.union(w)
    # lug band (with its jaw-ear clearance): remove from the wall everything below the band top
    z_band_top = GR.LUG_Z0 + P.GRIPV7_GEAR_Z0 + GR.LUG_T + 1.0
    notch = _lug_sweep_notch(SYNC_GUARD_Z0 - 1.0, z_band_top)
    return g.cut(notch)


# ---- lower plate --------------------------------------------------------------------------------
def make_lower_plate() -> cq.Workplane:
    plate = outline(LP_Z0, LP_Z1)
    keep = _keep_common(LP_Z0, LP_Z1).union(_cyl(11.0, LP_Z0 - 2, LP_Z1 + 2, *S))
    win = _windows(LP_Z0, LP_Z1, keep, p_tabs=False)
    plate = plate.cut(win)
    # inner-race rings, pilot post, columns, saddle, guard
    plate = plate.union(_cyl(RACE_R, LP_Z1 - 0.01, LP_RACE_TOP, *C))                 # compound lower race ring
    plate = plate.union(_cyl(RACE_R, LP_Z1 - 0.01, FOLLOWER_RACE_TOP, *F))           # follower race column
    plate = plate.union(_cyl(P.GRIPV7_PINION_PILOT_D / 2.0, LP_Z1 - 0.01, P.GRIPV7_PINION_PILOT_H, *S))
    plate = plate.union(_cyl(6.5, LP_Z1 - 0.01, LP_RACE_TOP, *S))
    for t in P.GRIPV7_TIE_XY:
        plate = plate.union(_cyl(P.GRIPV7_TIE_COL_OD / 2.0, LP_Z1 - 0.01, G, *t))
    plate = plate.union(_saddle(lower=True)).union(main_guard())
    # holes: pin seats (4 mm deep), tie holes, cross-bolt hole
    plate = plate.cut(_cyl(PIN_R, -P.GRIPV7_PIN_ENGAGE, LP_RACE_TOP + 1.0, *C))
    plate = plate.cut(_cyl(PIN_R, -P.GRIPV7_PIN_ENGAGE, FOLLOWER_RACE_TOP + 1.0, *F))
    for t in P.GRIPV7_TIE_XY + (XBOLT_XY,):
        plate = plate.cut(_tie_hole(t[0], t[1], LP_Z0 - 1.0, G + 1.0 if t != XBOLT_XY else TUBE_Z + 1.0))
        plate = plate.cut(_hex_pocket(t[0], t[1], LP_Z0, P.GRIPV7_NUT_POCKET_DEPTH, down_from_top=False))
    return plate


# ---- upper plate --------------------------------------------------------------------------------
def make_upper_plate() -> cq.Workplane:
    plate = outline(UP_Z0, UP_Z1, p_tabs=True)
    # keep zones: common + servo surround + P tabs
    keep = _keep_common(UP_Z0, UP_Z1)
    cx = S[0] - P.GRIPV7_SERVO_X_OFF
    keep = keep.union(_rrect(cx - 28.8, cx + 28.8, S[1] - 14.0, S[1] + 14.0, 3.0, UP_Z0 - 2, UP_Z1 + 2))
    px, py = P.GRIPV7_LINK_GROUND
    hw = P.GRIPV7_P_TAB_HALF_W
    for sx in (1, -1):
        keep = keep.union(_rrect(sx * px - hw, sx * px + hw, py - 10.0, py + 12.0, 5.0, UP_Z0 - 2, UP_Z1 + 2))
        # link reaction (up to ~150 N) goes into the pin bosses: triangulate the tabs to both axes
        for ax in (C, F):
            keep = keep.union(_bar((sx * px, py), ax, P.GRIPV7_RIB_W, UP_Z0 - 2, UP_Z1 + 2))
    win = _windows(UP_Z0, UP_Z1, keep, p_tabs=True)
    plate = plate.cut(win)
    # race rings (underside), P stubs, columns' landing is the plate inner face itself
    for ax in PIN_XY:
        plate = plate.union(_cyl(RACE_R, UP_RACE_BOT, UP_Z0 + 0.01, *ax))
    for sx in (1, -1):
        plate = plate.union(_cyl(P.GRIPV7_P_STUB_R, P.GRIPV7_P_STUB_Z0, UP_Z0 + 0.01, sx * px, py))
    plate = plate.union(_saddle(lower=False)).union(sync_guard())
    for t in P.GRIPV7_TIE_XY:     # the lower-plate columns run through the saddle footprint
        plate = plate.cut(_cyl(P.GRIPV7_TIE_COL_OD / 2.0 + 0.2, 20.0, UP_Z0 + 0.01, *t))
    # servo cutout + M2.5 insert holes
    cl = P.GRIPV7_SERVO_CUTOUT_CLEAR
    plate = plate.cut(cq.Workplane("XY").workplane(offset=UP_Z0 - 1.0).center(cx, S[1])
                      .rect(P.GRIPV7_SERVO_BODY_L + 2 * cl, P.GRIPV7_SERVO_BODY_W + 2 * cl).extrude(T + 2.0))
    for ex, ey in HW.ear_hole_xy(*S):
        plate = plate.cut(_cyl(P.GRIPV7_SERVO_INSERT_D / 2.0, UP_Z1 - P.GRIPV7_SERVO_INSERT_DEPTH, UP_Z1 + 1.0, ex, ey))
    # pin seats, tie holes + head counterbores, cross-bolt hole, nyloc pockets in the stubs
    for ax in PIN_XY:
        plate = plate.cut(_cyl(PIN_R, UP_RACE_BOT - 1.0, UP_Z0 + P.GRIPV7_PIN_ENGAGE, *ax))
    for t in P.GRIPV7_TIE_XY + (XBOLT_XY,):
        plate = plate.cut(_tie_hole(t[0], t[1], 20.0, UP_Z1 + 1.0))
        plate = plate.cut(_cyl(P.GRIPV7_CBORE_D / 2.0, UP_Z1 - P.GRIPV7_CBORE_DEPTH, UP_Z1 + 1.0, *t))
    for sx in (1, -1):
        plate = plate.cut(_cyl(P.GRIPV7_TIE_HOLE_D / 2.0, P.GRIPV7_P_STUB_Z0 - 1.0, P.GRIPV7_P_STUB_Z0 + 8.0, sx * px, py))
        plate = plate.cut(_hex_pocket(sx * px, py, P.GRIPV7_P_STUB_Z0, HW.NYLOC_H + 0.2, down_from_top=False))
        plate = plate.cut(_cyl(HW.WASHER_D / 2.0 + 0.3, P.GRIPV7_P_STUB_Z0 + HW.NYLOC_H, P.GRIPV7_P_STUB_Z0 + HW.NYLOC_H + HW.WASHER_T + 0.2, sx * px, py))
    return plate


if __name__ == "__main__":
    for name, part in (("lower_plate", make_lower_plate()), ("upper_plate", make_upper_plate())):
        v = part.val()
        bb = v.BoundingBox()
        print(name, v.isValid(), len(v.Solids()), round(v.Volume(), 1), "mass %.1f g" % (v.Volume() * 1.27e-3),
              [round(x, 2) for x in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)])
