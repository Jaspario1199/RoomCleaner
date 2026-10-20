"""
Gripper v7 -- gear parts: 18T pinion, compound (36T + 24T + crank lug), follower (24T + crank lug).

Train: MG996R -> horn -> 18T pinion -> 36T (2:1) | 24T -> 24T follower (1:1 sync, second jaw
counter-rotates).  Module 1.5, 20 deg involute, 0.10 mm thinning per gear, centre distances
nominal + 0.30 mm.  Tooth profile: the v3/v6 involute generator
(cad/gripper_v3_fit_review_20261018/gears.py) is reused unchanged.

All numbers come from cad/params.py (GRIPV7_*).  Each make_*() returns a cq.Workplane in the
PART frame: gear axis = z axis through the origin, z = 0 on the part's lower face.  The assembly
places a part by translating it to its LP-frame axis position and z0 and rotating it about the
axis by (crank angle - closed-pose crank angle).

Mesh phasing is built into the parts for the CLOSED pose (compound crank at GRIPV7_THETA_CLOSED):
  * 36T has a tooth pointing at the pinion axis; the pinion has a space pointing back at the 36T.
  * compound 24T has a tooth pointing at the follower axis; the follower has a space pointing back.
Because 36 = 2 x 18 and 24 = 24, the phasing then holds at every crank angle (n1*phi1 + n2*phi2 = const).

Print orientation (STL): axis vertical, lower face (z = 0) on the bed.  The crank-lug underside
needs supports (tongue sits mid-band); 36T windows are bridged by the 24T underside (about 10 mm).
"""

from __future__ import annotations

import math

import cadquery as cq

from cad import params as P
from cad.gripper_v3_fit_review_20261018.gears import gear as _involute_gear

# --------------------------------------------------------------------------------------------
# derived layout (local frame, mm)
# --------------------------------------------------------------------------------------------
M = P.GRIPV7_MODULE
C_AXIS = (P.GRIPV7_CD_SYNC / 2.0, 0.0)          # compound axis (x, y)
F_AXIS = (-P.GRIPV7_CD_SYNC / 2.0, 0.0)         # follower axis
_S_X = P.GRIPV7_SERVO_X_OFF
S_AXIS = (_S_X, math.sqrt(P.GRIPV7_CD_MAIN ** 2 - (_S_X - C_AXIS[0]) ** 2))   # pinion / servo shaft axis

BRG_N_LOWER = 1        # compound & follower: one bearing at the lower end ...
BRG_N_UPPER = 2        # ... two at the upper end (as v6, follower gets the lower one too)

COMPOUND_H = P.GRIPV7_FACE_MAIN + P.GRIPV7_FACE_SYNC          # 36
FOLLOWER_H = P.GRIPV7_FACE_SYNC                                # 20: 24T only (the 36T layer is below it)
FOLLOWER_Z0 = P.GRIPV7_L2_Z0                                   # LP-frame z of the follower bottom face

# crank lug tongue: 9 mm band centred in the sync layer
LUG_T = 9.0
LUG_Z_ABS0 = (P.GRIPV7_L2_Z0 + P.GRIPV7_L2_Z1) / 2.0 - LUG_T / 2.0       # 22.5 (LP frame)
LUG_Z0 = LUG_Z_ABS0 - P.GRIPV7_GEAR_Z0                                   # 21.5 (compound part frame)
LUG_Z0_FOLLOWER = LUG_Z_ABS0 - FOLLOWER_Z0                               # 5.5  (follower part frame)
LUG_END_R = 8.0                  # round end around the pivot
LUG_ROOT_R = 10.0
LUG_HOLE_D = 4.15                # M3 shoulder (4.0) in the moving part, Ø4.1-4.2
PIVOT_SHOULDER_D = 4.0


def pitch_r(n: int) -> float:
    return M * n / 2.0


def tip_r(n: int) -> float:
    return M * (n + 2) / 2.0


def root_r(n: int) -> float:
    return M * (n - 2.5) / 2.0


def _toothed(n: int, width: float, tooth_center_deg: float) -> cq.Workplane:
    """Involute spur gear, axis z through origin, z in [0, width], tooth #0 centred at
    tooth_center_deg (the v3 generator centres tooth k at phase + 360 k / n)."""
    return _involute_gear(n, M, width, phase=tooth_center_deg,
                          reduction=P.GRIPV7_TOOTH_THIN, root_radius=P.GRIPV7_ROOT_FILLET_R)


def _cyl(r: float, z0: float, z1: float, x: float = 0.0, y: float = 0.0) -> cq.Workplane:
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)


def _bearing_pocket(z_face: float, n: int, from_top: bool) -> cq.Workplane:
    """Cutter for n stacked 7x14x5 bearings entered from the face at z_face: Ø14.05 x (n*5+0.05)
    plus the 0.3 mm radial lip relief counterbore at the mouth."""
    depth = n * P.GRIPV7_BRG_W + P.GRIPV7_BRG_DEPTH_EXTRA
    r = P.GRIPV7_BRG_POCKET_D / 2.0
    rr = r + P.GRIPV7_BRG_LIP_RELIEF
    d_rel = P.GRIPV7_BRG_LIP_RELIEF_DEPTH
    if from_top:
        body = _cyl(r, z_face - depth, z_face)
        relief = _cyl(rr, z_face - d_rel, z_face)
    else:
        body = _cyl(r, z_face, z_face + depth)
        relief = _cyl(rr, z_face, z_face + d_rel)
    return body.union(relief)


def _seat_bore(z0: float, z1: float) -> cq.Workplane:
    return _cyl(P.GRIPV7_BRG_SEAT_BORE / 2.0, z0, z1)


def _lug_profile(theta_deg: float, reach: float, z0: float, z1: float,
                 margin: float = 0.0) -> cq.Workplane:
    """Tongue: hull of a root circle on the axis and an end circle at `reach` along theta.
    margin > 0 grows both circles (keep-out / sweep envelopes) and omits the pivot hole."""
    th = math.radians(theta_deg)
    ex, ey = reach * math.cos(th), reach * math.sin(th)
    r0, r1 = LUG_ROOT_R + margin, LUG_END_R + margin
    # tangent-hull polygon (outer common tangents) + two circles
    a = math.asin((r0 - r1) / reach)
    ca, sa = math.cos(a), math.sin(a)
    # tangent points on each circle for direction theta (rotated by +-(90 deg - a))
    def pt(cx, cy, r, sgn):
        ang = th + sgn * (math.pi / 2 - a)
        return (cx + r * math.cos(ang), cy + r * math.sin(ang))
    poly = [pt(0, 0, r0, +1), pt(ex, ey, r1, +1), pt(ex, ey, r1, -1), pt(0, 0, r0, -1)]
    h = z1 - z0
    body = cq.Workplane("XY").workplane(offset=z0).polyline(poly).close().extrude(h)
    body = body.union(_cyl(r0, z0, z1)).union(_cyl(r1, z0, z1, ex, ey))
    if margin > 0.0:
        return body
    hole = _cyl(LUG_HOLE_D / 2.0, z0 - 1.0, z1 + 1.0, ex, ey)
    return body.cut(hole)


# --------------------------------------------------------------------------------------------
# pinion
# --------------------------------------------------------------------------------------------
def pinion_hub_height() -> float:
    """Hub extension above the 16 mm teeth: horn disc bottom (z=30) minus the layer top (17)."""
    horn_disc_bottom = (P.GRIPV7_SERVO_BOSS_Z - P.GRIPV7_HORN_BOSS_GAP
                        - P.GRIPV7_HORN_HUB_H - P.GRIPV7_HORN_T)
    return horn_disc_bottom - P.GRIPV7_L1_Z1


def make_pinion(tooth_center_deg: float | None = None) -> cq.Workplane:
    """18T pinion + hub extension carrying the servo horn; plate pilot bore in the bottom.
    Part frame: z = 0 on the tooth bottom (= LP z 1.0), shaft axis on z."""
    beta_sc = math.degrees(math.atan2(C_AXIS[1] - S_AXIS[1], C_AXIS[0] - S_AXIS[0]))   # pinion -> 36T
    if tooth_center_deg is None:
        # the 36T has a tooth pointing at the pinion, so the pinion has a SPACE pointing at the 36T
        tooth_center_deg = beta_sc + 180.0 / P.GRIPV7_Z_PINION
    teeth = _toothed(P.GRIPV7_Z_PINION, P.GRIPV7_FACE_MAIN, tooth_center_deg)
    h_hub = pinion_hub_height()
    z_top = P.GRIPV7_FACE_MAIN + h_hub
    hub = _cyl(P.GRIPV7_PINION_HUB_D / 2.0, P.GRIPV7_FACE_MAIN - 0.5, z_top)
    body = teeth.union(hub)
    # plate pilot bore (journal support, bottom)
    pilot_bore_d = P.GRIPV7_PINION_PILOT_D + 2 * P.GRIPV7_PINION_PILOT_CLEAR
    pilot_depth = P.GRIPV7_PINION_PILOT_H - P.GRIPV7_GEAR_Z0 + 0.5
    body = body.cut(_cyl(pilot_bore_d / 2.0, -1.0, pilot_depth))
    # horn centre-screw relief and 4 horn-screw pilots from the hub top
    body = body.cut(_cyl(4.0, z_top - 4.0, z_top + 1.0))
    for k in range(P.GRIPV7_HORN_SCREWS):
        a = math.radians(45.0 + 360.0 * k / P.GRIPV7_HORN_SCREWS)
        body = body.cut(_cyl(P.GRIPV7_HORN_SCREW_PILOT_D / 2.0,
                             z_top - P.GRIPV7_HORN_SCREW_PILOT_DEPTH, z_top + 1.0,
                             P.GRIPV7_HORN_SCREW_R * math.cos(a), P.GRIPV7_HORN_SCREW_R * math.sin(a)))
    return body


# --------------------------------------------------------------------------------------------
# compound: 36T (lower, 16 mm) + 24T (upper, 20 mm) + crank lug
# --------------------------------------------------------------------------------------------
def _web_windows() -> cq.Workplane:
    """Windows of the 36T rim-and-spoke web (blind from the lower face up to the 24T underside)."""
    r_in = P.GRIPV7_HUB_R
    r_out = WINDOW_R_OUT
    n = P.GRIPV7_SPOKES
    ring = _cyl(r_out, -0.01, P.GRIPV7_FACE_MAIN).cut(_cyl(r_in, -1.0, P.GRIPV7_FACE_MAIN + 1.0))
    spokes = None
    for k in range(n):
        a = 360.0 * k / n + 90.0 / n
        sp = (cq.Workplane("XY").workplane(offset=-1.0).rect(r_out * 2 + 4, P.GRIPV7_SPOKE_W)
              .extrude(P.GRIPV7_FACE_MAIN + 2.0).rotate((0, 0, 0), (0, 0, 1), a))
        spokes = sp if spokes is None else spokes.union(sp)
    win = ring.cut(spokes)
    return win


WINDOW_R_OUT = 19.4      # window outer radius: under the 24T disc (R19.5) -> no through slit


def make_compound(theta_lug_deg: float, reach: float | None = None) -> cq.Workplane:
    """Compound gear: 36T (z 0..16) with six-spoke web, 24T (z 16..36), crank lug at theta_lug_deg
    (part frame angle = the closed-pose crank angle).  Bearings: 1 at the lower end, 2 at the upper."""
    reach = P.GRIPV7_CRANK_R if reach is None else reach
    # 36T: tooth centred on the direction to the pinion; 24T: tooth centred on the direction to F
    beta_cs = math.degrees(math.atan2(S_AXIS[1] - C_AXIS[1], S_AXIS[0] - C_AXIS[0]))
    beta_cf = 180.0
    t36 = _toothed(P.GRIPV7_Z_MAIN, P.GRIPV7_FACE_MAIN, beta_cs)
    t24 = _toothed(P.GRIPV7_Z_SYNC, P.GRIPV7_FACE_SYNC, beta_cf).translate((0, 0, P.GRIPV7_FACE_MAIN))
    body = t36.union(t24)
    body = body.cut(_web_windows())
    body = body.union(_lug_profile(theta_lug_deg, reach, LUG_Z0, LUG_Z0 + LUG_T))
    # bearing pockets: 1 at the lower face, 2 at the upper face; seat bore between them
    body = body.cut(_seat_bore(-1.0, COMPOUND_H + 1.0))
    body = body.cut(_bearing_pocket(0.0, BRG_N_LOWER, from_top=False))
    body = body.cut(_bearing_pocket(COMPOUND_H, BRG_N_UPPER, from_top=True))
    return body


# --------------------------------------------------------------------------------------------
# follower: hub tube (z 0..16) + 24T (z 16..36) + crank lug
# --------------------------------------------------------------------------------------------
def make_follower(theta_lug_deg: float, reach: float | None = None) -> cq.Workplane:
    """Follower: 24T (20 mm) with the crank lug; 1 bearing at the lower face, 2 at the upper face
    (the lower race sits on a column of the lower plate).  Part frame: z = 0 on the lower face
    (LP z = GRIPV7_L2_Z0), lug at theta_lug_deg (= 180 - closed crank angle)."""
    reach = P.GRIPV7_CRANK_R if reach is None else reach
    # follower has a SPACE pointing at the compound axis (angle 0): teeth at 0 + half pitch
    tooth_center = 180.0 / P.GRIPV7_Z_SYNC
    body = _toothed(P.GRIPV7_Z_SYNC, P.GRIPV7_FACE_SYNC, tooth_center)
    body = body.union(_lug_profile(theta_lug_deg, reach, LUG_Z0_FOLLOWER, LUG_Z0_FOLLOWER + LUG_T))
    body = body.cut(_seat_bore(-1.0, FOLLOWER_H + 1.0))
    body = body.cut(_bearing_pocket(0.0, BRG_N_LOWER, from_top=False))
    body = body.cut(_bearing_pocket(FOLLOWER_H, BRG_N_UPPER, from_top=True))
    return body


# --------------------------------------------------------------------------------------------
# convenience: place a gear part in the LP frame at a crank angle
# --------------------------------------------------------------------------------------------
def place(part: cq.Workplane, axis_xy, rot_deg: float, z0: float) -> cq.Workplane:
    return (part.rotate((0, 0, 0), (0, 0, 1), rot_deg)
            .translate((axis_xy[0], axis_xy[1], z0)))


if __name__ == "__main__":
    th = P.GRIPV7_THETA_CLOSED
    for name, part in (("pinion", make_pinion()), ("compound", make_compound(th)),
                       ("follower", make_follower(180.0 - th))):
        v = part.val()
        bb = v.BoundingBox()
        print(name, v.isValid(), len(v.Solids()), round(v.Volume(), 1),
              [round(x, 2) for x in (bb.xlen, bb.ylen, bb.zlen)])
