"""
Gripper v7 -- assembly builder (v7 LOCAL frame) and preview-STEP placement into the v6 world frame.

build(theta_deg) returns an ordered dict name -> (solid, kind) with kind in
{"printed", "hardware", "tube"}.  theta_deg is the RIGHT crank angle (compound); the follower turns
the opposite way, the pinion turns -ratio x the compound angle.  The closed pose is
GRIPV7_THETA_CLOSED (tips meet), the open stop is closed + GRIPV7_SWEEP_DEG.

Assembly sequence (also the service order): lower plate + columns -> pins -> bearings into gears ->
gears on pins -> jaws/links on shoulder screws -> upper plate with servo, horn and pinion -> M3x50 ties.
"""

from __future__ import annotations

import math
from collections import OrderedDict

import cadquery as cq

from cad import params as P
from cad.parts import gripper_v7_frame as FR
from cad.parts import gripper_v7_gears as GR
from cad.parts import gripper_v7_hw as HW
from cad.parts import gripper_v7_jaws as JW
from cad.parts import gripper_v7_kin as K

PRINTED, HARDWARE, TUBE = "printed", "hardware", "tube"


class PartCache:
    """Build each (expensive) part once."""
    _c: dict = {}

    @classmethod
    def get(cls, name):
        if name not in cls._c:
            cls._c[name] = {
                "pinion": GR.make_pinion,
                "compound": lambda: GR.make_compound(P.GRIPV7_THETA_CLOSED),
                "follower": lambda: GR.make_follower(180.0 - P.GRIPV7_THETA_CLOSED),
                "jaw": JW.make_jaw,
                "link": JW.make_link,
                "lower_plate": FR.make_lower_plate,
                "upper_plate": FR.make_upper_plate,
            }[name]()
        return cls._c[name]


def _bearings(ax, z0, height):
    """1 bearing at the lower end, 2 stacked at the upper end of a gear body of given height at z0."""
    top = z0 + height
    b = [HW.bearing(ax[0], ax[1], z0 + P.GRIPV7_BRG_DEPTH_EXTRA)]
    for k in range(GR.BRG_N_UPPER):
        b.append(HW.bearing(ax[0], ax[1], top - (k + 1) * P.GRIPV7_BRG_W - P.GRIPV7_BRG_DEPTH_EXTRA))
    return b


def build(theta_deg: float | None = None, hardware: bool = True) -> "OrderedDict[str, tuple]":
    fb = K.default()
    th = fb.theta_c if theta_deg is None else theta_deg
    delta = th - fb.theta_c
    z0 = P.GRIPV7_GEAR_Z0
    parts: "OrderedDict[str, tuple]" = OrderedDict()

    parts["lower_plate"] = (PartCache.get("lower_plate"), PRINTED)
    parts["upper_plate"] = (PartCache.get("upper_plate"), PRINTED)
    parts["compound"] = (GR.place(PartCache.get("compound"), GR.C_AXIS, delta, z0), PRINTED)
    parts["follower"] = (GR.place(PartCache.get("follower"), GR.F_AXIS, -delta, GR.FOLLOWER_Z0), PRINTED)
    parts["pinion"] = (GR.place(PartCache.get("pinion"), GR.S_AXIS, -P.GRIPV7_RATIO * delta, z0), PRINTED)
    pose = fb.pose(th)
    jaw, link = PartCache.get("jaw"), PartCache.get("link")
    parts["jaw_R"] = (JW.place_jaw(jaw, pose, fb, mirror=False), PRINTED)
    parts["jaw_L"] = (JW.place_jaw(jaw, pose, fb, mirror=True), PRINTED)
    parts["link_R"] = (JW.place_link(link, pose, fb, mirror=False), PRINTED)
    parts["link_L"] = (JW.place_link(link, pose, fb, mirror=True), PRINTED)
    if not hardware:
        return parts

    # --- purchased parts -------------------------------------------------------------------
    for tag, ax, gz0, gh in (("C", GR.C_AXIS, z0, GR.COMPOUND_H), ("F", GR.F_AXIS, GR.FOLLOWER_Z0, GR.FOLLOWER_H)):
        parts["pin_" + tag] = (HW.pin(*ax), HARDWARE)
        for i, b in enumerate(_bearings(ax, gz0, gh)):
            parts["brg_%s%d" % (tag, i)] = (b, HARDWARE)
    sx, sy = GR.S_AXIS
    parts["servo"] = (HW.servo(sx, sy), HARDWARE)
    # horn and its screws turn with the pinion (servo shaft angle = -ratio x compound angle)
    ax0, ax1 = (sx, sy, 0.0), (sx, sy, 1.0)
    rot_pin = -P.GRIPV7_RATIO * delta
    parts["horn"] = (HW.horn(sx, sy).rotate(ax0, ax1, rot_pin), HARDWARE)
    for i, s in enumerate(HW.horn_screws(sx, sy)):
        parts["horn_screw%d" % i] = (s.rotate(ax0, ax1, rot_pin), HARDWARE)
    # clevis shoulder screws: head on top of the upper ear, thread + washer + nyloc below the jaw
    for side, mir in (("R", 1.0), ("L", -1.0)):
        for tag, p in (("A", pose.A), ("B", pose.B)):
            # pin position = jaw part point at this pose
            x, y = mir * p[0], p[1]
            z_head = JW.JAW_Z0 + JW.JAW_T
            z_end = z_head - JW.SHOULDER_LEN
            parts["sh_%s%s" % (tag, side)] = (HW.shoulder_screw(x, y, z_end, JW.SHOULDER_LEN, head_up=True), HARDWARE)
            parts["wa_%s%s" % (tag, side)] = (HW.washer(x, y, z_end - HW.WASHER_T), HARDWARE)
            parts["ny_%s%s" % (tag, side)] = (HW.nyloc(x, y, z_end - HW.WASHER_T - HW.NYLOC_H, up=True), HARDWARE)
        # link ground pivot: shoulder from below into the stub nyloc (nut sits in the stub pocket)
        gx, gy = mir * fb.Pg[0], fb.Pg[1]
        z_sh_end = P.GRIPV7_P_STUB_Z0           # stub bottom face
        sh = HW.shoulder_screw(gx, gy, z_sh_end, JW.LINK_SHOULDER_LEN, head_up=False)
        parts["sh_P%s" % side] = (sh, HARDWARE)
        parts["ny_P%s" % side] = (HW.nyloc(gx, gy, z_sh_end, up=True), HARDWARE)
        parts["wa_P%s" % side] = (HW.washer(gx, gy, z_sh_end + HW.NYLOC_H), HARDWARE)
    # tie bolts + cross-bolt (M3x50 from the upper-plate counterbore down to the lower-plate nyloc)
    z_seat = FR.UP_Z1 - P.GRIPV7_CBORE_DEPTH
    for i, t in enumerate(P.GRIPV7_TIE_XY + (FR.XBOLT_XY,)):
        parts["tie%d" % i] = (HW.cap_bolt_vertical(t[0], t[1], z_seat, 50.0), HARDWARE)
        parts["tienut%d" % i] = (HW.nyloc(t[0], t[1], FR.LP_Z0 + 0.0, up=True), HARDWARE)
    parts["tube"] = (HW.tube(True), TUBE)
    return parts


def to_world(shape: cq.Workplane) -> cq.Workplane:
    """v7 local -> v6 world frame (same tube axis, same gear-stack z)."""
    return shape.translate(P.GRIPV7_WORLD_ORIGIN)


def compound_of(parts, kinds=(PRINTED, HARDWARE, TUBE)) -> cq.Shape:
    solids = []
    for name, (s, k) in parts.items():
        if k in kinds:
            solids.append(s.val() if isinstance(s, cq.Workplane) else s)
    return cq.Compound.makeCompound(solids)
