"""
Gripper v7 -- purchased-part envelopes (bearings, pins, servo + horn, shoulder screws, nuts, tube).

These are REFERENCE bodies for interference checks and the preview assembly; none is printed.
Every dimension is a GRIPV7_* parameter or a catalogue size listed in VERIFY below.  All
builders work in the v7 LOCAL frame (z = 0 on the lower-plate inner face) and take absolute
positions; nothing here depends on a part module (no circular imports).

VERIFY with calipers before ordering: bearing inner-race OD (pocket seat bore assumes ~9),
servo ear pitch / ear drop / boss size (v6 ESTIMATED body), horn thickness / hub / screw circle,
M3 shoulder-screw head size, nyloc nut height, tube OD.
"""

from __future__ import annotations

import math

import cadquery as cq

from cad import params as P

# ---- catalogue sizes (mm) --------------------------------------------------------------------
SHOULDER_D = 4.0                 # M3 shoulder screw: Ø4 shoulder ...
SHOULDER_THREAD_D = 3.0          # ... M3 thread
SHOULDER_THREAD_L = 6.0
SHOULDER_HEAD_D = 7.0
SHOULDER_HEAD_H = 3.0
NYLOC_AF = 5.5                   # M3 nyloc: across flats 5.5, height 4.0
NYLOC_H = 4.0
WASHER_D = 7.0                   # M3 washer 3.2 / 7 / 0.5
WASHER_T = 0.5
WASHER_ID = 3.2
CAP_HEAD_D = 5.5                 # M3 socket-head cap screw
CAP_HEAD_H = 3.0
M2_CAP_HEAD_D = 3.8
M2_CAP_HEAD_H = 2.0


def _cyl(r, z0, z1, x=0.0, y=0.0):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)


def _hex(af, z0, z1, x=0.0, y=0.0, rot=0.0):
    d = af / math.cos(math.radians(30.0))
    return (cq.Workplane("XY").workplane(offset=z0).center(x, y).polygon(6, d).extrude(z1 - z0)
            .rotate((x, y, z0), (x, y, z0 + 1), rot))


# ---- bearings and pins -------------------------------------------------------------------------
def bearing(x: float, y: float, z0: float) -> cq.Workplane:
    """7x14x5 ring with its lower face at z0 (simplified: plain ring)."""
    return _cyl(P.GRIPV7_BRG_OD / 2, z0, z0 + P.GRIPV7_BRG_W, x, y).cut(
        _cyl(P.GRIPV7_BRG_ID / 2, z0 - 1, z0 + P.GRIPV7_BRG_W + 1, x, y))


def pin(x: float, y: float) -> cq.Workplane:
    """Ø7 steel dowel, length GRIPV7_PIN_LEN, centred on the plate gap."""
    zc = P.GRIPV7_PLATE_GAP / 2.0
    return _cyl(P.GRIPV7_PIN_D / 2, zc - P.GRIPV7_PIN_LEN / 2, zc + P.GRIPV7_PIN_LEN / 2, x, y)


# ---- servo + horn ------------------------------------------------------------------------------
def servo(sx: float, sy: float) -> cq.Workplane:
    """MG996R envelope, shaft axis at (sx, sy), output end DOWN.  Body centred on the tube axis in x
    (shaft offset GRIPV7_SERVO_X_OFF), centred on the shaft in y."""
    zb = P.GRIPV7_SERVO_BOSS_Z
    cx = sx - P.GRIPV7_SERVO_X_OFF
    boss = _cyl(P.GRIPV7_SERVO_BOSS_D / 2, zb, zb + P.GRIPV7_SERVO_BOSS_H, sx, sy)
    body = (cq.Workplane("XY").workplane(offset=zb + P.GRIPV7_SERVO_BOSS_H).center(cx, sy)
            .rect(P.GRIPV7_SERVO_BODY_L, P.GRIPV7_SERVO_BODY_W).extrude(P.GRIPV7_SERVO_BODY_H))
    ear = (cq.Workplane("XY").workplane(offset=zb + P.GRIPV7_SERVO_EAR_DROP).center(cx, sy)
           .rect(P.GRIPV7_SERVO_EAR_L, P.GRIPV7_SERVO_BODY_W).extrude(P.GRIPV7_SERVO_EAR_T))
    shaft = _cyl(P.GRIPV7_SERVO_SHAFT_D / 2, zb - P.GRIPV7_SERVO_SHAFT_L, zb, sx, sy)
    s = boss.union(body).union(ear).union(shaft)
    for ex, ey in ear_hole_xy(sx, sy):
        s = s.cut(_cyl(P.GRIPV7_SERVO_EAR_HOLE_D / 2, zb, zb + 60, ex, ey))
    return s


def ear_hole_xy(sx: float, sy: float):
    cx = sx - P.GRIPV7_SERVO_X_OFF
    return [(cx + sgx * P.GRIPV7_SERVO_EAR_HOLE_DX / 2, sy + sgy * P.GRIPV7_SERVO_EAR_HOLE_DY / 2)
            for sgx in (-1, 1) for sgy in (-1, 1)]


def horn(sx: float, sy: float) -> cq.Workplane:
    """Round horn: spline hub on the servo side, Ø25 disc below, 4 M2 screws through the disc
    (heads on the servo side of the disc, in the hub-height gap)."""
    zb = P.GRIPV7_SERVO_BOSS_Z
    z_hub_top = zb - P.GRIPV7_HORN_BOSS_GAP
    z_disc_top = z_hub_top - P.GRIPV7_HORN_HUB_H
    z_disc_bot = z_disc_top - P.GRIPV7_HORN_T
    h = _cyl(P.GRIPV7_HORN_D / 2, z_disc_bot, z_disc_top, sx, sy).union(
        _cyl(P.GRIPV7_HORN_HUB_D / 2, z_disc_top, z_hub_top, sx, sy))
    # spline bore (envelope: plain Ø6) so the servo shaft is a touching fit; M3 centre screw not modelled
    h = h.cut(_cyl(P.GRIPV7_SERVO_SHAFT_D / 2, z_disc_bot - 1, z_hub_top + 1, sx, sy))
    for x, y in horn_screw_xy(sx, sy):                      # Ø2.2 clearance holes for the M2 screws
        h = h.cut(_cyl(2.2 / 2, z_disc_bot - 1, z_disc_top + 1, x, y))
    return h


def horn_screw_xy(sx: float, sy: float):
    return [(sx + P.GRIPV7_HORN_SCREW_R * math.cos(math.radians(45.0 + 360.0 * k / P.GRIPV7_HORN_SCREWS)),
             sy + P.GRIPV7_HORN_SCREW_R * math.sin(math.radians(45.0 + 360.0 * k / P.GRIPV7_HORN_SCREWS)))
            for k in range(P.GRIPV7_HORN_SCREWS)]


def horn_screws(sx: float, sy: float):
    """List of the four M2 screws (shank into the pinion hub, head above the horn disc)."""
    zb = P.GRIPV7_SERVO_BOSS_Z
    z_disc_top = zb - P.GRIPV7_HORN_BOSS_GAP - P.GRIPV7_HORN_HUB_H
    z_disc_bot = z_disc_top - P.GRIPV7_HORN_T
    out = []
    for k in range(P.GRIPV7_HORN_SCREWS):
        a = math.radians(45.0 + 360.0 * k / P.GRIPV7_HORN_SCREWS)
        x = sx + P.GRIPV7_HORN_SCREW_R * math.cos(a)
        y = sy + P.GRIPV7_HORN_SCREW_R * math.sin(a)
        shank = _cyl(P.GRIPV7_HORN_SCREW_D / 2, z_disc_bot - 6.0, z_disc_top, x, y)
        head = _cyl(M2_CAP_HEAD_D / 2, z_disc_top, z_disc_top + M2_CAP_HEAD_H, x, y)
        out.append(shank.union(head))
    return out


# ---- shoulder screw + nyloc + washer -------------------------------------------------------------
def shoulder_screw(x: float, y: float, z_shoulder_end: float, shoulder_len: float,
                   head_up: bool = True) -> cq.Workplane:
    """M3 shoulder screw (Ø4 shoulder).  The shoulder runs from z_shoulder_end (thread side) to
    z_shoulder_end + shoulder_len when head_up, the head sits on top; head_up False mirrors it
    (head below, thread up)."""
    if head_up:
        z_sh0, z_sh1 = z_shoulder_end, z_shoulder_end + shoulder_len
        # thread points DOWN from the shoulder end
        thread = _cyl(SHOULDER_THREAD_D / 2, z_sh0 - SHOULDER_THREAD_L, z_sh0, x, y)
        head = _cyl(SHOULDER_HEAD_D / 2, z_sh1, z_sh1 + SHOULDER_HEAD_H, x, y)
    else:
        z_sh1, z_sh0 = z_shoulder_end, z_shoulder_end - shoulder_len
        thread = _cyl(SHOULDER_THREAD_D / 2, z_sh1, z_sh1 + SHOULDER_THREAD_L, x, y)
        head = _cyl(SHOULDER_HEAD_D / 2, z_sh0 - SHOULDER_HEAD_H, z_sh0, x, y)
    sh = _cyl(SHOULDER_D / 2, z_sh0, z_sh1, x, y)
    return sh.union(thread).union(head)


def nyloc(x: float, y: float, z0: float, up: bool = True) -> cq.Workplane:
    """M3 nyloc, hole through the middle, lower face at z0 (or upper face at z0 when up=False)."""
    z_a, z_b = (z0, z0 + NYLOC_H) if up else (z0 - NYLOC_H, z0)
    return _hex(NYLOC_AF, z_a, z_b, x, y).cut(_cyl(SHOULDER_THREAD_D / 2, z_a - 1, z_b + 1, x, y))


def washer(x: float, y: float, z0: float) -> cq.Workplane:
    return _cyl(WASHER_D / 2, z0, z0 + WASHER_T, x, y).cut(_cyl(WASHER_ID / 2, z0 - 1, z0 + 2, x, y))


def cap_bolt_vertical(x: float, y: float, z_head_seat: float, length: float) -> cq.Workplane:
    """M3 socket cap bolt pointing DOWN from its head seat (head above z_head_seat)."""
    shank = _cyl(SHOULDER_THREAD_D / 2, z_head_seat - length, z_head_seat, x, y)
    head = _cyl(CAP_HEAD_D / 2, z_head_seat, z_head_seat + CAP_HEAD_H, x, y)
    return shank.union(head)


# ---- tube ----------------------------------------------------------------------------------------
def tube(with_cross_hole: bool = True) -> cq.Workplane:
    """Aluminium tube along +y on the tube axis (x = 0, z = GRIPV7_TUBE_Z), from the lower end."""
    r_o, r_i = P.GRIPV7_TUBE_OD / 2, P.GRIPV7_TUBE_ID / 2
    y0 = P.GRIPV7_TUBE_END_Y
    t = (cq.Workplane("XZ").workplane(offset=-y0).center(0, P.GRIPV7_TUBE_Z).circle(r_o).circle(r_i)
         .extrude(-P.GRIPV7_TUBE_LEN))
    # XZ workplane normal is -y: offset=-y0 puts the plane at y=+y0, extrude(-L) goes toward +y
    if with_cross_hole:
        yb = y0 + P.GRIPV7_XBOLT_Y_FROM_END
        t = t.cut(_cyl(P.GRIPV7_XBOLT_HOLE_D / 2, P.GRIPV7_TUBE_Z - r_o - 1, P.GRIPV7_TUBE_Z + r_o + 1, 0.0, yb))
    return t


if __name__ == "__main__":
    t = tube().val()
    bb = t.BoundingBox()
    print("tube", t.isValid(), round(t.Volume()), [round(v, 2) for v in (bb.ymin, bb.ymax, bb.zmin, bb.zmax)])
