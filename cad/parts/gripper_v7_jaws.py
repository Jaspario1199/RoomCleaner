"""
Gripper v7 -- jaw (Claw_arm_extension replacement) and link (Claw_arm_extension3 replacement).

Right jaw = four-bar coupler.  Crank pin A (compound lug), link pin B, inner gripping face on x = 0
at the closed pose.  The left jaw is the right jaw mirrored about the tube plane x = 0; because the
jaw is symmetric in z it is the SAME printed part turned over (rotate 180 deg about y).

Z layout (local frame; lug and link tongues sit in the sync layer):
    jaw band   [JAW_Z0, JAW_Z0 + JAW_T]   = [17.5, 36.5]   (19 mm)
    lower ear  4.5 | gap 0.5 | tongue 9 | gap 0.5 | upper ear 4.5
Both A and B are CLEVISES: the jaw ears straddle a 9 mm tongue (the compound lug at A, the link at B).
An M3 shoulder screw (Ø4 shoulder, 20 mm) passes through ears + tongue; its holes are Ø4.15 in the
moving tongue and Ø4.15 in the ears too (the screw is clamped by head + washer + nyloc).
In the slot band the jaw is cut away where the tongue sweeps relative to the jaw (computed
numerically from the four-bar), so ears stay full and the middle band is open only where needed.

Part frame of the jaw: origin on the crank pin A at the CLOSED pose, jaw bottom face at z = 0.
Part frame of the link: origin on the frame pivot P, +x toward B at the closed pose, z = 0 at its
bottom face.
"""

from __future__ import annotations

import math

import cadquery as cq
import numpy as np

from cad import params as P
from cad.parts import gripper_v7_kin as K
from cad.parts import gripper_v7_gears as GR

# ---- layout -------------------------------------------------------------------------------------
TONGUE_T = GR.LUG_T                                   # 9
TONGUE_GAP = P.GRIPV7_TONGUE_GAP                      # printed faces that rotate: 0.5 mm washer gap
EAR_T = P.GRIPV7_EAR_T
JAW_T = 2 * EAR_T + 2 * TONGUE_GAP + TONGUE_T         # 19
SLOT_T = TONGUE_T + 2 * TONGUE_GAP                    # 10
_sync_mid = (P.GRIPV7_L2_Z0 + P.GRIPV7_L2_Z1) / 2.0   # 27.0
JAW_Z0 = _sync_mid - JAW_T / 2.0                      # 17.5
TONGUE_Z0 = _sync_mid - TONGUE_T / 2.0                # 22.5
LINK_Z0 = TONGUE_Z0                                   # link tongue = same band as the lug
BOSS_R = 9.5                                          # jaw boss radius at A and B
LINK_END_R = 6.0
HOLE_D = 4.15                                         # Ø4.1-4.2 for the Ø4 shoulder
PAD_W = 16.0
PAD_H = 36.0
SLOT_MARGIN = 0.8                                     # extra clearance around the swept tongue
SHOULDER_LEN = 20.0                                   # M3 shoulder length at the clevises (stack 19)
LINK_SHOULDER_LEN = 10.0                              # at the frame pivot P (stack 9 + 2 x 0.5)


# ---- small 2D helpers ---------------------------------------------------------------------------
def _hull(points):
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo = []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    up = []
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def _circle_pts(c, r, n=48):
    return [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n))
            for k in range(n)]


def _prism(poly, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).polyline(list(poly)).close().extrude(z1 - z0)


def _cyl(r, z0, z1, x=0.0, y=0.0):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)


def _hull_prism(circles, extra_pts, z0, z1):
    pts = list(extra_pts)
    for c, r in circles:
        pts += _circle_pts(c, r)
    return _prism(_hull(pts), z0, z1)


# ---- kinematic helpers --------------------------------------------------------------------------
def fourbar() -> K.FourBar:
    return K.default()


def _to_jaw_frame(fb: K.FourBar, pose: K.Pose, p):
    """World (closed-pose-aligned) point at `pose` -> jaw frame (= world frame at the closed pose)."""
    t = -math.radians(pose.tilt_deg)
    c, s = math.cos(t), math.sin(t)
    v = np.asarray(p, float) - pose.A
    return fb.Ac + np.array([v[0] * c - v[1] * s, v[0] * s + v[1] * c])


def _swept_tongue_cut(fb: K.FourBar, which: str, n: int = 24) -> cq.Workplane:
    """Union (over the travel) of the tongue seen from the jaw: `crank` tongue at A or `link` at B.
    Returned in LOCAL-frame jaw coordinates, band [TONGUE_Z0 - gap, TONGUE_Z0 + T + gap]."""
    z0 = TONGUE_Z0 - TONGUE_GAP
    z1 = TONGUE_Z0 + TONGUE_T + TONGUE_GAP
    out = None
    for ps in fb.poses(n):
        if which == "crank":
            far = _to_jaw_frame(fb, ps, fb.C)
            near = fb.Ac
            r_near = GR.LUG_END_R + SLOT_MARGIN
            r_far = GR.LUG_ROOT_R + SLOT_MARGIN
        else:
            far = _to_jaw_frame(fb, ps, fb.Pg)
            near = fb.Bc
            r_near = LINK_END_R + SLOT_MARGIN
            r_far = LINK_END_R + SLOT_MARGIN
        s = _hull_prism([(tuple(near), r_near), (tuple(far), r_far)], [], z0, z1)
        out = s if out is None else out.union(s)
    return out


def jaw_outline_solid(fb: K.FourBar) -> cq.Workplane:
    """Full-thickness jaw plate before slots/holes, local-frame coordinates, z in [0, JAW_T]."""
    A, B, tip = tuple(fb.Ac), tuple(fb.Bc), tuple(fb.tip_c)
    y_f = tip[1] + PAD_H
    pad = [(0.0, tip[1]), (PAD_W, tip[1]), (PAD_W, y_f), (0.0, y_f)]
    neck = _hull_prism([(A, BOSS_R), (B, BOSS_R)], [], 0.0, JAW_T)
    strut = _hull_prism([(B, BOSS_R)], pad, 0.0, JAW_T)
    return neck.union(strut)


def make_jaw() -> cq.Workplane:
    """Right jaw in the PART frame (origin on A_closed, z = 0 at the jaw bottom)."""
    fb = fourbar()
    body = jaw_outline_solid(fb)
    # slots: crank tongue sweep at A and link tongue sweep at B, in the band z [5, 15]
    for which in ("crank", "link"):
        cut = _swept_tongue_cut(fb, which).translate((0, 0, -JAW_Z0))
        body = body.cut(cut)
    # shoulder-screw holes through the whole stack
    for c in (tuple(fb.Ac), tuple(fb.Bc)):
        body = body.cut(_cyl(HOLE_D / 2.0, -1.0, JAW_T + 1.0, c[0], c[1]))
    # to part frame: origin on A_closed
    return body.translate((-fb.Ac[0], -fb.Ac[1], 0.0))


def make_link() -> cq.Workplane:
    """Link in the PART frame: pivot P at the origin, B at (L, 0), z in [0, TONGUE_T]."""
    fb = fourbar()
    L = fb.L
    body = _hull_prism([((0.0, 0.0), LINK_END_R), ((L, 0.0), LINK_END_R)], [], 0.0, TONGUE_T)
    for x in (0.0, L):
        body = body.cut(_cyl(HOLE_D / 2.0, -1.0, TONGUE_T + 1.0, x, 0.0))
    return body


# ---- placement ----------------------------------------------------------------------------------
def place_jaw(part: cq.Workplane, pose: K.Pose, fb: K.FourBar, mirror: bool = False) -> cq.Workplane:
    """Right jaw at `pose`: rotate about A_closed by the tilt, translate A_closed -> A(pose)."""
    s = part.rotate((0, 0, 0), (0, 0, 1), pose.tilt_deg).translate((pose.A[0], pose.A[1], JAW_Z0))
    return s.mirror("YZ") if mirror else s


def place_link(part: cq.Workplane, pose: K.Pose, fb: K.FourBar, mirror: bool = False) -> cq.Workplane:
    ang = math.degrees(math.atan2(pose.B[1] - fb.Pg[1], pose.B[0] - fb.Pg[0]))
    s = part.rotate((0, 0, 0), (0, 0, 1), ang).translate((fb.Pg[0], fb.Pg[1], LINK_Z0))
    return s.mirror("YZ") if mirror else s


if __name__ == "__main__":
    for name, part in (("jaw", make_jaw()), ("link", make_link())):
        v = part.val()
        bb = v.BoundingBox()
        print(name, v.isValid(), len(v.Solids()), round(v.Volume(), 1),
              [round(x, 2) for x in (bb.xlen, bb.ylen, bb.zlen)], "mass %.1f g" % (v.Volume() * 1.27e-3))
