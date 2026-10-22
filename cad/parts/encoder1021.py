"""
ENCODER 1021 -- magnet cap ("cylinder cap") and AS5600 encoder casing for the 10/21 wall assembly.

Spec: cad/ENCODER_1021_SPEC.md.  Master values: cad/params.py, block ENC1021_*.  Build notes / measured results:
verification/encoder1021_build_notes.md.  Tests: tests/test_encoder1021.py.

Frame (everything below, STEP and tests): the v3 STATION frame = the slip-in mount's own frame
    origin   on the motor shaft axis, in the slip-in's motor-plate face (y = 0)
    +y       along the shaft toward the spool
    +z       up
    +x       out of the wall into the room
cad/reference/station_1021/*.step are this frame shifted by +2.64 mm in z, and carry a common extraction residual of
(+0.004243, +0.001645, +0.003854) mm: reference_parts() puts them into this frame (with or without that residual).

MAGNET CAP  (one per station)
    Ø14 x 3.3 head against the spool's outer face (y 26.0 .. 29.3), Ø6.2 x 2.55 magnet pocket opening toward +y on the axis
    (glue film 0.05 mm: the magnet face sits flush at y = 29.3), 0.8 mm pry notch under the head rim, and a D-peg in the
    spool's empty bore end: Ø5.10 with its flat at x = +2.05, 3 axial crush ribs 0.15 high, 3.4 long (end at y = 22.6,
    0.6 mm clear of the shaft end at 22.0).
    Print: magnet face on the bed, peg up; the only overhang is the 6.2 mm bridge over the magnet pocket.

ENCODER CASING (one per station)
    Board pocket 23.4 x 23.4 centred on the chip axis (pocket outline locates the chip), 2 mm frame walls, four 3 x 3 front-stop
    corner tabs, two snap-hook lips on the +-z walls (the walls are thinned between the corner blocks, so they flex in the
    layer plane), pad edges (+-x) open at the back.  Chip face y = 30.8 (air gap 1.5 to the magnet face at 29.3), PCB front
    32.25, PCB back 33.85.  Frame front / tab front face at y = 31.0.
    A bridge on the frame's -x side carries it to a 23.6 x 23.6 foot (R1.2 corners, bottom edge rounded R1.0 to follow the
    divot's quarter-round wall) that sits 1.0 mm deep in the divot and stands 3.0 mm proud of the plate; four Ø3.4 teardrop
    clearance holes at the divot holes, heads on the foot's +x face with the region above kept open.
    Print: frame front face (y = 31.0) on the bed, +y up; no supports (the hook catch faces are 0.6 mm ledges).

Every level along y is derived from ENC1021_* in Cfg, so one edit of cad/params.py regenerates both parts.
"""

from __future__ import annotations

import functools
import math
import os

import cadquery as cq

from .. import params as P

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STEP_DIR = os.path.join(_REPO, "exports", "step")
STL_DIR = os.path.join(_REPO, "exports", "stl")
RENDER_DIR = os.path.join(_REPO, "renders", "encoder1021")
REF_DIR = os.path.join(_REPO, "cad", "reference", "station_1021")
REF_NAMES = ("Slipin_mount_piecev3", "Spool1011", "Shell_Casing", "Motor_Reference", "Heat_horn", "Wall_Mount_v3")

CAP_NAME = "encoder1021_magnet_cap"
CASING_NAME = "encoder1021_casing"

# construction constants (not design values: overlaps that make unions fuse cleanly, cutter overshoots)
EPS = 0.01          # mm, overlap used to fuse face-touching solids (chip on the PCB, pins on the tabs)
JOIN = 0.5          # mm, boxes that join walls / tabs / bridge run this far into their neighbour
FUSE = 0.3          # mm, snap-hook lip embedded into its wall
OVERSHOOT = 1.0     # mm, cutter / probe overshoot beyond the cut face
RIB_INSET = 0.1     # mm, rib base sunk into the peg surface
CONE_MARGIN = 0.5   # mm, lead-in cone oversize beyond the rib tips
HOOK_TOP_MARGIN = 0.1   # mm, hook-edge wall stands this far above the top of the lip


# =============================================================================================================================
# derived values (read from cad/params.py at CALL time, so a parameter edit -- or a test monkeypatch -- regenerates everything)
# =============================================================================================================================
class Cfg:
    """All derived levels / sizes of both parts.  y levels are in the station frame."""

    def __init__(self):
        p = P
        # --- purchased parts
        self.magnet_d, self.magnet_t = p.ENC1021_MAGNET_D, p.ENC1021_MAGNET_T
        self.pcb_size, self.pcb_t, self.chip_h = p.ENC1021_PCB_SIZE, p.ENC1021_PCB_THICK, p.ENC1021_CHIP_H
        self.chip_off = tuple(p.ENC1021_CHIP_OFFSET)
        self.air_gap = p.ENC1021_AIR_GAP
        self.chip_body = tuple(p.ENC1021_CHIP_BODY)
        # --- interfaces
        self.spool_face_y = p.ENC1021_SPOOL_FACE_Y
        self.shaft_end_y = p.ENC1021_SHAFT_END_Y
        self.bore_d, self.bore_flat_x = p.ENC1021_BORE_D, p.ENC1021_BORE_FLAT_X
        self.plate_x, self.floor_x = p.ENC1021_PLATE_FACE_X, p.ENC1021_DIVOT_FLOOR_X
        self.divot_y, self.divot_z = p.ENC1021_DIVOT_YZ
        self.divot_rim = p.ENC1021_DIVOT_RIM
        self.divot_wall_r = p.ENC1021_DIVOT_WALL_R
        self.divot_hole_d, self.divot_pitch = p.ENC1021_DIVOT_HOLE_D, p.ENC1021_DIVOT_HOLE_PITCH
        # --- magnet cap
        self.head_d = p.ENC1021_CAP_HEAD_D
        self.pocket_d = self.magnet_d + p.ENC1021_CAP_POCKET_CLEAR_D
        self.pocket_depth = self.magnet_t + p.ENC1021_CAP_POCKET_EXTRA_DEPTH
        self.head_t = max(p.ENC1021_CAP_HEAD_T, self.pocket_depth + p.ENC1021_CAP_FLOOR_MIN)
        self.head_chamfer = p.ENC1021_CAP_HEAD_CHAMFER
        self.magnet_face_y = self.spool_face_y + self.head_t              # 29.3
        self.pocket_floor_y = self.magnet_face_y - self.pocket_depth      # 26.75
        self.magnet_bottom_y = self.magnet_face_y - self.magnet_t         # 26.8 (glue film under the magnet)
        self.peg_d, self.peg_flat_x = p.ENC1021_CAP_PEG_D, p.ENC1021_CAP_PEG_FLAT_X
        self.peg_len = p.ENC1021_CAP_PEG_LEN
        self.peg_end_y = self.spool_face_y - self.peg_len                 # 22.6
        self.rib_n, self.rib_h = p.ENC1021_CAP_RIB_N, p.ENC1021_CAP_RIB_H
        self.rib_wb, self.rib_wt = p.ENC1021_CAP_RIB_W_BASE, p.ENC1021_CAP_RIB_W_TIP
        self.lead_in = p.ENC1021_CAP_LEAD_IN
        self.notch_w, self.notch_r, self.notch_h = p.ENC1021_CAP_NOTCH
        # --- board stack
        self.chip_face_y = self.magnet_face_y + self.air_gap              # 30.8
        self.pcb_front_y = self.chip_face_y + self.chip_h                 # 32.25
        self.pcb_back_y = self.pcb_front_y + self.pcb_t                   # 33.85
        self.board_cx, self.board_cz = -self.chip_off[0], -self.chip_off[1]   # board centre (chip is on the axis)
        self.pcb_half = self.pcb_size / 2
        self.pocket_half = self.pcb_half + p.ENC1021_PCB_CLEAR            # 11.7
        self.wall = p.ENC1021_WALL
        self.frame_front_y = self.chip_face_y + p.ENC1021_TAB_SETBACK     # 31.0
        self.tab_t = self.pcb_front_y - self.frame_front_y                # 1.25
        self.tab = p.ENC1021_TAB
        self.flex_t = p.ENC1021_FLEX_WALL_T
        self.hook_w, self.hook_overlap = p.ENC1021_HOOK_W, p.ENC1021_HOOK_OVERLAP
        self.catch_y = self.pcb_back_y + p.ENC1021_HOOK_GAP               # 33.95
        self.hook_lip_y = p.ENC1021_HOOK_LIP_Y
        self.wall_top_x = self.pcb_back_y                                  # pad-edge (+-x) walls end flush with the PCB back
        self.wall_top_z = self.catch_y + self.hook_lip_y + HOOK_TOP_MARGIN # hook-edge (+-z) walls: 35.05
        self.lip_protrusion = self.pocket_half - (self.pcb_half - self.hook_overlap)   # 0.7 beyond the wall's inner face
        # --- foot / bridge
        self.foot = p.ENC1021_FOOT_SIZE
        self.foot_r, self.foot_key_r = p.ENC1021_FOOT_CORNER_R, p.ENC1021_FOOT_KEY_R
        self.foot_top_x = self.floor_x + p.ENC1021_FOOT_H                  # -18.15
        self.foot_hole_d = p.ENC1021_FOOT_HOLE_D
        self.bridge_x0, self.bridge_top_y = p.ENC1021_BRIDGE_X0, p.ENC1021_BRIDGE_TOP_Y
        self.bridge_hz = p.ENC1021_BRIDGE_HALF_Z
        self.tie_l, self.tie_w, self.tie_z = p.ENC1021_TIE_SLOT
        self.tie_x = p.ENC1021_TIE_SLOT_X
        self.screw_access_r = p.ENC1021_SCREW_HEAD_D / 2 + p.ENC1021_TOOL_CLEAR
        self.hole_pts = [(self.divot_y + sy * self.divot_pitch / 2, self.divot_z + sz * self.divot_pitch / 2)
                         for sy in (-1, 1) for sz in (-1, 1)]               # (y, z)
        self.pins_on, self.pin_pitch = p.ENC1021_PINS_ON, p.ENC1021_PIN_PITCH
        self.pin_d = p.ENC1021_PIN_D
        self.pin_len = min(p.ENC1021_PIN_LEN, self.pcb_t - 0.3)
        # --- sanity (a bad parameter edit must fail loudly, not print a wrong part)
        assert self.head_t >= self.pocket_depth + p.ENC1021_CAP_FLOOR_MIN - 1e-9
        assert self.pocket_d < self.head_d - 4.0, "magnet too large for the Ø14 head"
        assert self.tab_t >= 1.0, "front-stop tabs thinner than 1.0 mm (chip too short for the 0.2 mm set-back)"
        assert self.catch_y - self.frame_front_y > 0 and self.lip_protrusion > 0.2
        assert self.hook_lip_y - self.lip_protrusion >= 0.2, "lip needs a flat tip before the 45 deg ramp"
        assert self.bridge_top_y - self.frame_front_y >= 2.0
        hole_y_min = min(h[0] for h in self.hole_pts)
        assert hole_y_min - self.screw_access_r >= self.bridge_top_y + 0.3, "bridge would block the screw heads / driver"
        assert self.foot <= self.divot_rim - 0.2 + 1e-9, "foot needs >= 0.1 mm per side inside the divot rim"
        assert self.foot_r >= 1.2 - 1e-9 and self.foot_key_r < self.foot_r + 1e-9


# =============================================================================================================================
# small construction helpers
# =============================================================================================================================
def _box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    """Axis-aligned box from absolute coordinates."""
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def _plane_y(y0: float, x: float = 0.0, z: float = 0.0) -> cq.Plane:
    """Plane normal to +y at height y0; local u = +x, local v = -z (extrusions run toward +y)."""
    return cq.Plane(origin=(x, y0, z), xDir=(1, 0, 0), normal=(0, 1, 0))


def _cyl_y(r: float, y0: float, y1: float, x: float = 0.0, z: float = 0.0) -> cq.Workplane:
    return cq.Workplane(_plane_y(y0, x, z)).circle(r).extrude(y1 - y0)


def _teardrop_x(y_c: float, z_c: float, r: float, x0: float, x1: float) -> cq.Workplane:
    """Hole along +x with a 45 deg pointed top toward +y (prints without support when +y is up)."""
    k = r / math.sqrt(2)
    wp = lambda: cq.Workplane("YZ", origin=(x0, 0, 0))                         # local (u, v) = (y, z), extrudes toward +x
    circ = wp().center(y_c, z_c).circle(r).extrude(x1 - x0)
    kite = wp().polyline([(y_c, z_c), (y_c + k, z_c + k), (y_c + r * math.sqrt(2), z_c), (y_c + k, z_c - k)]).close().extrude(x1 - x0)
    return circ.union(kite)


# =============================================================================================================================
# MAGNET CAP
# =============================================================================================================================
def make_peg(ribs: bool = True, overlap: float = 0.0) -> cq.Workplane:
    """The D-peg alone: y from the peg end (22.6) up to the head underside (+ `overlap` into the head).

    Ø5.10 round part, flat at x = +2.05 (the bore's flat is at +2.15, its round part Ø5.30), `rib_n` axial crush ribs
    `rib_h` high (tip radius 2.70 = 0.05 mm of radial crush into the bore), 45 deg lead-in at the end."""
    c = Cfg()
    r0 = c.peg_d / 2
    y0, y1 = c.peg_end_y, c.spool_face_y + overlap
    core = _cyl_y(r0, y0, y1).intersect(_box(-r0 - OVERSHOOT, c.peg_flat_x, y0 - OVERSHOOT, y1 + OVERSHOOT,
                                              -r0 - OVERSHOOT, r0 + OVERSHOOT))
    if ribs:
        # one rib opposite the flat (at -x), the others equally spaced; local rib at +x rotated about the y axis
        for i in range(c.rib_n):
            ang = 180.0 + i * 360.0 / c.rib_n
            rib = (cq.Workplane(_plane_y(y0))
                   .polyline([(r0 - RIB_INSET, -c.rib_wb / 2), (r0 + c.rib_h, -c.rib_wt / 2),
                              (r0 + c.rib_h, c.rib_wt / 2), (r0 - RIB_INSET, c.rib_wb / 2)]).close()
                   .extrude(y1 - y0).rotate((0, 0, 0), (0, 1, 0), ang))
            core = core.union(rib)
    # 45 deg lead-in: intersect with a cone that starts at r_lead on the end face
    r_tip = r0 + (c.rib_h if ribs else 0.0)
    r_lead = r_tip - c.lead_in
    r_big = r_tip + CONE_MARGIN
    cone = (cq.Workplane("XY").polyline([(0, y0), (r_lead, y0), (r_big, y0 + (r_big - r_lead)), (r_big, y1 + OVERSHOOT), (0, y1 + OVERSHOOT)]).close()
            .revolve(360, (0, 0, 0), (0, 1, 0)))
    return core.intersect(cone)


def make_magnet_cap(ribs: bool = True) -> cq.Workplane:
    """Head + pocket + pry notch + D-peg, one solid, station frame (peg toward -y).  ribs=False drops the crush ribs (tests)."""
    c = Cfg()
    y_face, y_top = c.spool_face_y, c.magnet_face_y
    head = _cyl_y(c.head_d / 2, y_face, y_top)
    head = head.faces(">Y").edges().chamfer(c.head_chamfer)
    head = head.cut(_cyl_y(c.pocket_d / 2, c.pocket_floor_y, y_top + OVERSHOOT))                      # magnet pocket, opens to +y
    notch = _box(-c.notch_w / 2, c.notch_w / 2, y_face - OVERSHOOT, y_face + c.notch_h, c.head_d / 2 - c.notch_r, c.head_d / 2 + OVERSHOOT)
    head = head.cut(notch)                                                                       # pry notch at +z, under the rim
    cap = head.union(make_peg(ribs=ribs, overlap=JOIN))                                          # peg runs into the head
    return cap


def make_magnet() -> cq.Workplane:
    """Reference magnet (display / fit checks only): Ø6 x 2.5, face flush at the head top, glue film under it."""
    c = Cfg()
    return _cyl_y(c.magnet_d / 2, c.magnet_bottom_y, c.magnet_face_y)


# =============================================================================================================================
# ENCODER CASING
# =============================================================================================================================
def _foot(c: Cfg) -> cq.Workplane:
    """23.6 x 23.6 slab, R1.2 plan corners, bottom edge rounded R1.0 so it follows the divot's quarter-round wall."""
    f = (cq.Workplane("YZ", origin=(c.floor_x, 0, 0)).center(c.divot_y, c.divot_z).rect(c.foot, c.foot)
         .extrude(c.foot_top_x - c.floor_x))
    f = f.edges("|X").fillet(c.foot_r)
    f = f.faces("<X").edges().fillet(c.foot_key_r)
    return f


def _lip(c: Cfg, side: int) -> cq.Workplane:
    """Snap-hook lip on the +z (side = +1) or -z (side = -1) wall: catch face horizontal at catch_y, 45 deg lead-in ramp."""
    z_wall = c.board_cz + side * c.pocket_half                       # inner face of the wall
    z_tip = z_wall - side * c.lip_protrusion
    tip_flat = c.hook_lip_y - c.lip_protrusion
    emb = side * FUSE                                                # embed into the wall to fuse
    pts = [(c.catch_y, z_wall + emb), (c.catch_y, z_tip), (c.catch_y + tip_flat, z_tip),
           (c.catch_y + c.hook_lip_y, z_wall), (c.catch_y + c.hook_lip_y, z_wall + emb)]
    x0 = c.board_cx - c.hook_w / 2
    return cq.Workplane("YZ", origin=(x0, 0, 0)).polyline(pts).close().extrude(c.hook_w)


def make_casing(pins: bool | None = None) -> cq.Workplane:
    """The encoder casing, one solid, station frame."""
    c = Cfg()
    h, W = c.pocket_half, c.wall
    cx, cz = c.board_cx, c.board_cz
    yF = c.frame_front_y
    pins = c.pins_on if pins is None else pins

    # --- frame ring: +-x walls = pad edges (open above the PCB back), +-z walls = hook edges (thinned, longer)
    parts = []
    for s in (-1, 1):
        x0, x1 = sorted((cx + s * h, cx + s * (h + W)))
        parts.append(_box(x0, x1, yF, c.wall_top_x, cz - h - W, cz + h + W))                    # +-x wall incl. corner blocks
        z0, z1 = sorted((cz + s * h, cz + s * (h + c.flex_t)))
        parts.append(_box(cx - h - JOIN, cx + h + JOIN, yF, c.wall_top_x, z0, z1))              # +-z wall, low part
        parts.append(_box(cx - h, cx + h, c.wall_top_x - JOIN, c.wall_top_z, z0, z1))            # +-z wall, hook part
        parts.append(_lip(c, s))
    # --- four front-stop tabs at the pocket corners (front face flush with the frame front, back face on the PCB front face)
    for sx in (-1, 1):
        for sz in (-1, 1):
            x0, x1 = sorted((cx + sx * (h - c.tab), cx + sx * (h + JOIN)))
            z0, z1 = sorted((cz + sz * (h - c.tab), cz + sz * (h + JOIN)))
            parts.append(_box(x0, x1, yF, c.pcb_front_y, z0, z1))
            if pins:
                assert abs(c.pin_pitch / 2) <= h - JOIN and c.pin_pitch / 2 >= h - c.tab, "corner-hole pin must stand on the tab"
                parts.append(_cyl_y(c.pin_d / 2, c.pcb_front_y - EPS, c.pcb_front_y + c.pin_len,
                                    x=cx + sx * c.pin_pitch / 2, z=cz + sz * c.pin_pitch / 2))
    # --- bridge / filler block: from the frame's -x wall to the foot, flush with the frame front face (printed on the bed)
    wall_out_x = cx - h - W
    bz0, bz1 = min(-c.bridge_hz, cz - c.bridge_hz), max(c.bridge_hz, cz + c.bridge_hz)
    bridge = _box(c.bridge_x0, wall_out_x + JOIN, yF, c.bridge_top_y, bz0, bz1)
    for s in (-1, 1):                                                                            # strain-relief zip-tie slots
        zc = s * c.tie_z
        bridge = bridge.cut(_box(c.tie_x - c.tie_l / 2, c.tie_x + c.tie_l / 2, yF - OVERSHOOT, c.bridge_top_y + OVERSHOOT,
                                 zc - c.tie_w / 2, zc + c.tie_w / 2))
    parts.append(bridge)
    # --- foot
    foot = _foot(c)
    parts.append(foot)

    body = parts[0]
    for part in parts[1:]:
        body = body.union(part)
    # --- foot screw holes at the divot holes (cut last: they pass only through the foot)
    for (yh, zh) in c.hole_pts:
        body = body.cut(_teardrop_x(yh, zh, c.foot_hole_d / 2, c.floor_x - OVERSHOOT, c.foot_top_x + OVERSHOOT))
    return body.clean()


# =============================================================================================================================
# reference bodies and the assembly
# =============================================================================================================================
def make_board() -> cq.Workplane:
    """Reference AS5600 board (display / fit checks only): 23 x 23 x 1.6 PCB + SOIC chip body on the front face."""
    c = Cfg()
    pcb = _box(c.board_cx - c.pcb_half, c.board_cx + c.pcb_half, c.pcb_front_y, c.pcb_back_y,
               c.board_cz - c.pcb_half, c.board_cz + c.pcb_half)
    bx, bz = c.chip_body
    chip = _box(-bx / 2, bx / 2, c.chip_face_y, c.pcb_front_y + EPS, -bz / 2, bz / 2)             # chip centre on the axis
    return pcb.union(chip)


@functools.lru_cache(maxsize=None)
def _ref(name: str, corrected: bool):
    path = os.path.join(REF_DIR, f"{name}.step")
    shape = cq.importers.importStep(path).val()
    dx, dy, dz = P.ENC1021_REF_RESIDUAL if corrected else (0.0, 0.0, 0.0)
    return shape.translate(cq.Vector(-dx, -dy, -(P.ENC1021_REF_SHIFT_Z + dz)))


def reference_parts(corrected: bool = True) -> dict:
    """The station_1021 reference solids in the station frame.  corrected=True also removes the (0.004243, 0.001645,
    0.003854) mm extraction residual (axis exactly at x = z = 0, spool face exactly at y = 26.0); corrected=False is the plain
    'subtract (0, 0, 2.64)' of the spec."""
    return {n: _ref(n, corrected) for n in REF_NAMES}


def assembly(include_reference: bool = True) -> dict:
    """name -> cq.Shape for the new parts (+ the reference solids), all in the station frame."""
    out = {"cap": make_magnet_cap().val(), "magnet": make_magnet().val(), "casing": make_casing().val(),
           "board": make_board().val()}
    if include_reference:
        out.update(reference_parts())
    return out


# =============================================================================================================================
# print orientation, overhang analysis, stiffness hand-calculation
# =============================================================================================================================
def to_print_pose(shape: cq.Shape, part: str) -> cq.Shape:
    """Bed pose.  casing: frame front face (y = 31.0) on the bed, +y up.  cap: magnet face (y = 29.3) on the bed, peg up.
    Result bounding box starts at x = y = z = 0."""
    ang = 90.0 if part == "casing" else -90.0                      # rotate about +x: y -> +z (casing) or y -> -z (cap)
    s = shape.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), ang)
    bb = s.BoundingBox()
    return s.translate(cq.Vector(-bb.xmin, -bb.ymin, -bb.zmin))


def overhang_faces(shape: cq.Shape, part: str, limit_deg: float | None = None, tol: float = 0.02, ang: float = 0.15):
    """Downward-facing triangles steeper than `limit_deg` from vertical, in the PRINT orientation of `part`.

    A face is an overhang if its outward normal makes n_z < -sin(limit) (a horizontal ceiling is n_z = -1, a 45 deg slope
    n_z = -0.707).  Triangles lying on the bed (z = 0) are bed contact, not overhang.  Returns a list of dicts with the area,
    print-z level, and the part-frame (station) bounding box of each connected-by-level cluster (clustered on z level rounded
    to 0.05 mm, then split on large gaps in plan)."""
    import numpy as np
    limit = math.radians((P.ENC1021_OVERHANG_DEG if limit_deg is None else limit_deg) + P.ENC1021_OVERHANG_TOL_DEG)
    verts, tris = shape.tessellate(tol, ang)
    V = np.array([[v.x, v.y, v.z] for v in verts], float)
    F = np.array(tris, int).reshape(-1, 3)
    sgn = 1.0 if part == "casing" else -1.0                          # print z = sgn * y (+ const)
    t = V[F]
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    area = 0.5 * np.linalg.norm(n, axis=1)
    nn = np.where(area[:, None] > 0, n / (2 * np.maximum(area, 1e-18))[:, None], 0.0)
    nz = sgn * nn[:, 1]                                                # print-frame normal z component
    zp = sgn * t[:, :, 1]
    zmin = zp.min()
    on_bed = np.all(np.abs(zp - zmin) < 1e-4, axis=1)
    bad = (nz < -math.sin(limit)) & ~on_bed & (area > 1e-9)
    out = []
    if not bad.any():
        return out
    zc = np.round((zp[bad].mean(axis=1) - zmin) / 0.05) * 0.05
    for lvl in np.unique(zc):
        sel = np.where(bad)[0][zc == lvl]
        pts = t[sel].reshape(-1, 3)
        out.append({"print_z": float(lvl), "area": float(area[sel].sum()), "n_tri": int(len(sel)),
                    "min_nz": float(nz[sel].min()),
                    "bbox": (tuple(pts.min(axis=0).round(3)), tuple(pts.max(axis=0).round(3)))})
    return out


def _section_inertia(casing: cq.Shape, x_mid: float, y_min: float = -100.0, dx: float = 0.2):
    """Area and second moments of the casing section at x = x_mid (y-z plane, y >= y_min), from a thin slab of the real solid."""
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    slab = casing.intersect(_box(x_mid - dx / 2, x_mid + dx / 2, y_min, 200, -100, 100).val())
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(slab.wrapped, props)
    m = props.MatrixOfInertia()
    area = props.Mass() / dx
    # slab inertia about its centroid: I_zz = int(x^2 + y^2) dV, I_yy = int(x^2 + z^2) dV ; x term = A dx^3 / 12
    ix = area * dx ** 3 / 12.0
    i_bend_y = (m.Value(3, 3) - ix) / dx          # bending about z (deflection along y):  int (y - yc)^2 dA
    i_bend_z = (m.Value(2, 2) - ix) / dx          # bending about y (deflection along z):  int (z - zc)^2 dA
    return area, i_bend_y, i_bend_z


def stiffness_estimate(casing: cq.Shape | None = None, load_n: float | None = None) -> dict:
    """Hand calculation: chip motion for a push of `load_n` on the far (+x) wall of the frame.

    Model: the foot is clamped by its four screws (rigid slip-in), the frame and PCB are rigid beyond the bridge, and the
    bridge neck at mid-span carries the load as a cantilever of length L (conservative: the whole span uses the weakest
    section of the real solid, and only the part of that section that sits against the foot, y >= foot edge, is counted).  Tip load F at x_l, deflection at the chip (x_c): d = F a^2 (3 L - a) / (6 E I), a = x_c - x_r.
    Axial (x) push: d = F a / (A E)."""
    c = Cfg()
    cas = casing if casing is not None else make_casing().val()
    F = P.ENC1021_STIFF_LOAD_N if load_n is None else load_n
    E = P.ENC1021_PETG_E_MPA
    x_r = c.foot_top_x                                              # root: foot +x face
    x_l = c.board_cx + c.pocket_half + c.wall                       # load on the far (+x) wall
    x_c = 0.0                                                       # chip on the axis
    x_mid = 0.5 * (x_r + (c.board_cx - c.pocket_half - c.wall))     # bridge neck mid-span (through the zip-tie slots)
    y_foot_edge = c.divot_y - c.foot / 2                              # only the bridge section that sits against the foot is clamped
    A, Iy_def, Iz_def = _section_inertia(cas, x_mid, y_min=y_foot_edge)
    L, a = x_l - x_r, x_c - x_r
    d_y = F * a * a * (3 * L - a) / (6 * E * Iy_def)
    d_z = F * a * a * (3 * L - a) / (6 * E * Iz_def)
    d_x = F * a / (A * E)
    return {"x_root": x_r, "x_load": x_l, "x_chip": x_c, "L": L, "a": a, "x_mid": x_mid, "A_mm2": A,
            "I_dy_mm4": Iy_def, "I_dz_mm4": Iz_def, "E_MPa": E, "F_N": F,
            "dy_mm": d_y, "dz_mm": d_z, "dx_mm": d_x, "worst_mm": max(d_y, d_z, d_x)}


def hook_estimate() -> dict:
    """Snap-hook hand calculation: each +-z wall is a beam clamped between the corner blocks (span = pocket width),
    loaded at mid-span by the PCB edge pushing the lip out by `delta`.  Bending stress acts along x, i.e. in the layer plane."""
    c = Cfg()
    E = P.ENC1021_PETG_E_MPA
    L = 2 * c.pocket_half
    b = c.wall_top_z - c.frame_front_y                              # wall height (y)
    t = c.flex_t
    I = b * t ** 3 / 12.0
    delta = c.hook_overlap + 0.1                                    # deflection needed to pass the PCB edge (centred board + margin)
    F = 192.0 * E * I * delta / L ** 3                              # clamped-clamped, central load
    M = F * L / 8.0
    sigma = M * (t / 2) / I
    return {"span_mm": L, "height_mm": b, "t_mm": t, "I_mm4": I, "delta_mm": delta, "F_N": F, "sigma_MPa": sigma,
            "strain_pct": 100.0 * sigma / E}


# =============================================================================================================================
# export / render
# =============================================================================================================================
def export_all(step_dir: str = STEP_DIR, stl_dir: str = STL_DIR) -> dict:
    """STEP in the station frame (SOLIDWORKS assembly pose), STL in the print orientation."""
    os.makedirs(step_dir, exist_ok=True)
    os.makedirs(stl_dir, exist_ok=True)
    out = {}
    for name, part, mk in ((CAP_NAME, "cap", make_magnet_cap), (CASING_NAME, "casing", make_casing)):
        wp = mk()
        step = os.path.join(step_dir, f"{name}.step")
        stl = os.path.join(stl_dir, f"{name}.stl")
        cq.exporters.export(wp, step)
        cq.exporters.export(cq.Workplane("XY").add(to_print_pose(wp.val(), part)), stl, tolerance=0.02, angularTolerance=0.1)
        out[part] = {"step": step, "stl": stl}
    return out


# standard views: name -> (direction from the part TO the camera, screen-up hint), station frame (x room, y toward spool, z up)
VIEWS = {
    "front": ((0, -1, 0), (0, 0, 1)),     # camera at -y: the chip / magnet side; +x right
    "rear": ((0, 1, 0), (0, 0, 1)),       # camera at +y
    "left": ((-1, 0, 0), (0, 0, 1)),      # camera at -x (the wall side)
    "right": ((1, 0, 0), (0, 0, 1)),      # camera at +x (the room side)
    "top": ((0, 0, 1), (0, 1, 0)),        # camera at +z; +x right, +y up
    "bottom": ((0, 0, -1), (0, 1, 0)),    # camera at -z; +y up (x mirrored)
    "iso": ((0.55, -0.62, 0.56), (0, 0, 1)),
}


def _mesh_arrays(shape: cq.Shape, tol: float, ang: float):
    import numpy as np
    verts, tris = shape.tessellate(tol, ang)
    V = np.array([[v.x, v.y, v.z] for v in verts], float)
    F = np.array(tris, int).reshape(-1, 3)
    return V, F


def _camera(cam_dir, up_hint):
    import numpy as np
    d = np.array(cam_dir, float)
    d /= np.linalg.norm(d)                      # toward the camera
    f = -d
    r = np.cross(f, np.array(up_hint, float))
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return d, r, u


def _rasterize(V, F, rgb, cam, scale, centre, shape_px):
    """Orthographic z-buffer.  Returns depth (H, W; larger = nearer, -inf = empty), colour (H, W, 3), normals (H, W, 3)."""
    import numpy as np
    d, r, u = cam
    H, W = shape_px
    P3 = V - centre
    sx = P3 @ r * scale + W / 2.0
    sy = H / 2.0 - P3 @ u * scale
    sz = P3 @ d
    tri = F
    n = np.cross(V[tri[:, 1]] - V[tri[:, 0]], V[tri[:, 2]] - V[tri[:, 0]])
    nl = np.linalg.norm(n, axis=1)
    keep = (nl > 1e-12) & ((n @ d) > 0)         # drop degenerate and back-facing triangles (closed solids)
    n = n[keep] / nl[keep, None]
    tri = tri[keep]
    # shading: key light from the camera's upper left, plus fill from the camera
    light = 0.60 * d + 0.45 * u - 0.35 * r
    light /= np.linalg.norm(light)
    shade = 0.30 + 0.45 * np.clip(n @ d, 0, 1) + 0.35 * np.clip(n @ light, 0, 1)
    depth = np.full((H, W), -np.inf)
    col = np.zeros((H, W, 3))
    nbuf = np.zeros((H, W, 3))
    base = np.array(rgb, float)
    x, y, z = sx[tri], sy[tri], sz[tri]
    for k in range(len(tri)):
        xs, ys, zs = x[k], y[k], z[k]
        x0, x1 = int(max(np.floor(xs.min()), 0)), int(min(np.ceil(xs.max()), W - 1))
        y0, y1 = int(max(np.floor(ys.min()), 0)), int(min(np.ceil(ys.max()), H - 1))
        if x1 < x0 or y1 < y0:
            continue
        den = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(den) < 1e-12:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / den
        w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / den
        w2 = 1.0 - w0 - w1
        m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not m.any():
            continue
        zz = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
        sub = depth[y0:y1 + 1, x0:x1 + 1]
        upd = m & (zz > sub)
        if upd.any():
            sub[upd] = zz[upd]
            col[y0:y1 + 1, x0:x1 + 1][upd] = np.clip(base * shade[k], 0, 1)
            nbuf[y0:y1 + 1, x0:x1 + 1][upd] = n[k]
    return depth, col, nbuf


def _composite(layers, bg=(1.0, 1.0, 1.0)):
    """layers: list of (depth, colour, normals, alpha).  Per-pixel far-to-near alpha compositing with outline darkening."""
    import numpy as np
    H, W = layers[0][0].shape
    D = np.stack([l[0] for l in layers])
    order = np.argsort(D, axis=0)                           # ascending depth: far first
    img = np.ones((H, W, 3)) * np.array(bg)
    alphas = np.array([l[3] for l in layers])
    cols = np.stack([l[1] for l in layers])
    for rank in range(len(layers)):
        idx = order[rank]
        present = np.take_along_axis(D, idx[None], 0)[0] > -np.inf
        a = alphas[idx] * present
        c = np.take_along_axis(cols, idx[None, :, :, None].repeat(3, axis=3), 0)[0]
        img = img * (1 - a[..., None]) + c * a[..., None]
    # outlines: depth jumps and normal creases of the nearest layer
    dmax = D.max(axis=0)
    nearest = np.argmax(D, axis=0)
    N = np.stack([l[2] for l in layers])
    nn = np.take_along_axis(N, nearest[None, :, :, None].repeat(3, axis=3), 0)[0]
    edge = np.zeros((H, W), bool)
    fin = np.where(np.isfinite(dmax), dmax, -1e9)
    jump = 0.6                                              # mm of depth step that counts as an outline
    for ax in (0, 1):
        dj = np.abs(np.diff(fin, axis=ax)) > jump
        cr = (np.sum(nn[1:] * nn[:-1], axis=2) < 0.8) if ax == 0 else (np.sum(nn[:, 1:] * nn[:, :-1], axis=2) < 0.8)
        e = dj | (cr & (np.take(np.isfinite(dmax), range(1, (H if ax == 0 else W)), axis=ax)))
        if ax == 0:
            edge[1:] |= e
        else:
            edge[:, 1:] |= e
    img[edge & np.isfinite(dmax)] *= 0.45
    return np.clip(img, 0, 1)


def _save(img, path, title, note=""):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    H, W = img.shape[:2]
    top_px = 44 if note else 28
    fig = plt.figure(figsize=(W / 110.0, (H + top_px) / 110.0), dpi=110)
    ax = fig.add_axes([0, 0, 1, H / (H + top_px)])
    ax.imshow(img, interpolation="bilinear")
    ax.axis("off")
    fig.text(0.01, 1 - 6.0 / (H + top_px), title, ha="left", va="top", fontsize=9)
    if note:
        fig.text(0.01, 1 - 22.0 / (H + top_px), note, ha="left", va="top", fontsize=7.5, color="0.35")
    fig.savefig(path, dpi=110)
    plt.close(fig)


def render_scene(items, path, view, title, px=760, margin=0.08, bounds=None, note="", bg=(1, 1, 1)):
    """items: list of (cq.Shape, rgb, alpha, tessellation tol).  `view` is a key of VIEWS or (dir, up) tuple."""
    import numpy as np
    cam = _camera(*(VIEWS[view] if isinstance(view, str) else view))
    meshes = [(_mesh_arrays(sh, tol, 0.2), rgb, a) for sh, rgb, a, tol in items]
    allv = np.concatenate([m[0][0] for m in meshes])
    lo, hi = (allv.min(axis=0), allv.max(axis=0)) if bounds is None else (np.array(bounds[0], float), np.array(bounds[1], float))
    centre = (lo + hi) / 2
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]) - centre
    ext = max(np.ptp(corners @ cam[1]), np.ptp(corners @ cam[2]))
    scale = px * (1 - 2 * margin) / ext
    layers = []
    for (V, F), rgb, a in meshes:
        dep, col, nb = _rasterize(V, F, rgb, cam, scale, centre, (px, px))
        layers.append((dep, col, nb, a))
    img = _composite(layers, bg)
    _save(img, path, title, note)
    return path


def render_part(shape: cq.Shape, name: str, rgb, out_dir: str = RENDER_DIR) -> list:
    """The 7 standard views (front, rear, left, right, top, bottom, iso) of one part, station frame, shared scale."""
    os.makedirs(out_dir, exist_ok=True)
    bb = shape.BoundingBox()
    half = 0.5 * max(bb.xlen, bb.ylen, bb.zlen)
    ctr = ((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, (bb.zmin + bb.zmax) / 2)
    bounds = ((ctr[0] - half, ctr[1] - half, ctr[2] - half), (ctr[0] + half, ctr[1] + half, ctr[2] + half))
    note = f"bbox {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm (x, y, z); station frame"
    paths = []
    for view in VIEWS:
        path = os.path.join(out_dir, f"{name}_{view}.png")
        render_scene([(shape, rgb, 1.0, 0.02)], path, view, f"{name} - {view}", px=640, bounds=bounds, note=note)
        paths.append(path)
    return paths


def render_assembly(out_dir: str = RENDER_DIR) -> list:
    """Assembly preview with the slip-in mount, spool, motor and shell (the large parts are clipped to the station zone)."""
    os.makedirs(out_dir, exist_ok=True)
    asm = assembly()
    lo, hi = (-42.0, -6.0, -32.0), (32.0, 72.0, 32.0)
    clip = _box(lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]).val()
    half = _box(lo[0], hi[0], lo[1], hi[1], lo[2], 0.0).val()          # keep z <= 0 for the cut-away
    look = [("Shell_Casing", (0.62, 0.66, 0.72), 0.16, 0.12), ("Slipin_mount_piecev3", (0.55, 0.58, 0.62), 0.42, 0.10),
            ("Motor_Reference", (0.40, 0.42, 0.48), 0.60, 0.08), ("Spool1011", (0.45, 0.72, 0.45), 0.95, 0.05),
            ("cap", (0.95, 0.55, 0.12), 1.0, 0.02), ("magnet", (0.80, 0.12, 0.12), 1.0, 0.02),
            ("casing", (0.20, 0.50, 0.90), 1.0, 0.02), ("board", (0.10, 0.55, 0.30), 1.0, 0.02)]

    def items(box, shell_alpha=None):
        res = []
        for nm, rgb, a, tol in look:
            sh = asm[nm]
            if nm in ("Shell_Casing", "Slipin_mount_piecev3", "Motor_Reference", "Spool1011") or box is half:
                sh = sh.intersect(box)
            if sh.Volume() <= 0:
                continue
            res.append((sh, rgb, shell_alpha if (nm == "Shell_Casing" and shell_alpha) else a, tol))
        return res

    paths = []
    clip_items = items(clip, 0.20)
    p1 = os.path.join(out_dir, "encoder1021_assembly_iso.png")
    render_scene(clip_items, p1, ((0.62, 0.55, 0.56), (0, 0, 1)),
                 "encoder 1021 assembly: magnet cap + casing with slip-in mount, spool, motor, shell (translucent, clipped)",
                 px=900, bounds=(lo, hi), note="station frame (x room, y toward spool, z up); view from the room side, behind the casing")
    paths.append(p1)
    p1b = os.path.join(out_dir, "encoder1021_assembly_iso_front.png")
    render_scene(clip_items, p1b, ((0.55, -0.62, 0.56), (0, 0, 1)),
                 "encoder 1021 assembly: same, seen from the spool side",
                 px=900, bounds=(lo, hi), note="station frame (x room, y toward spool, z up)")
    paths.append(p1b)
    p2 = os.path.join(out_dir, "encoder1021_assembly_section_z0.png")
    render_scene(items(half, 0.22), p2, ((0, 0, 1), (0, 1, 0)),
                 "encoder 1021 assembly: section at z = 0 seen from +z",
                 px=900, bounds=(lo, hi), note="+x right (room), +y up: spool at the bottom, magnet cap, chip, board, casing and foot above; slip-in on the left")
    paths.append(p2)
    return paths


def render_sections(out_dir: str = RENDER_DIR) -> list:
    """Section views: cap in the spool bore (z = 0), casing stack (z = 0 and x = 0), foot through a screw-hole row (z = +4.75)."""
    os.makedirs(out_dir, exist_ok=True)
    c = Cfg()
    cap, mag, cas, brd = (make_magnet_cap().val(), make_magnet().val(), make_casing().val(), make_board().val())
    ref = reference_parts()
    col = {"cap": (0.95, 0.55, 0.12), "mag": (0.80, 0.12, 0.12), "cas": (0.20, 0.50, 0.90), "brd": (0.10, 0.55, 0.30),
           "spool": (0.45, 0.72, 0.45), "slip": (0.60, 0.60, 0.62), "motor": (0.40, 0.42, 0.48)}

    def keep(sh, x0=-1e3, x1=1e3, y0=-1e3, y1=1e3, z0=-1e3, z1=1e3):
        r = sh.intersect(_box(x0, x1, y0, y1, z0, z1).val())
        return r if r.Volume() > 0 else None

    def items(entries):
        return [(sh, col[k], a, tol) for sh, k, a, tol in entries if sh is not None]

    paths = []
    zcut = 0.0
    z_half = dict(z1=zcut)
    p = os.path.join(out_dir, f"{CAP_NAME}_section_z0.png")
    render_scene(items([(keep(ref["Spool1011"], y0=5, y1=40, **z_half), "spool", 0.95, 0.03),
                        (keep(ref["Motor_Reference"], y0=-5, y1=40, x0=-10, x1=10, **z_half), "motor", 0.8, 0.03),
                        (keep(cap, **z_half), "cap", 1.0, 0.02), (keep(mag, **z_half), "mag", 1.0, 0.02),
                        (keep(brd, **z_half), "brd", 1.0, 0.02), (keep(cas, **z_half), "cas", 1.0, 0.02)]),
                 p, ((0, 0, 1), (0, 1, 0)), "magnet cap section z = 0: D-peg in the spool bore, magnet in its pocket, chip 1.5 mm above",
                 px=900, bounds=((-14, 19, -3), (14, 35, 3)), note="+x right, +y up")
    paths.append(p)
    p = os.path.join(out_dir, f"{CASING_NAME}_section_z0.png")
    render_scene(items([(keep(ref["Slipin_mount_piecev3"], x0=-35, x1=-15, y0=25, y1=62, **z_half), "slip", 0.6, 0.05),
                        (keep(cas, **z_half), "cas", 1.0, 0.02), (keep(brd, **z_half), "brd", 1.0, 0.02),
                        (keep(mag, **z_half), "mag", 1.0, 0.02), (keep(cap, **z_half), "cap", 1.0, 0.02)]),
                 p, ((0, 0, 1), (0, 1, 0)), "encoder casing section z = 0: foot in the divot, bridge, board pocket, tabs",
                 px=900, bounds=((-28, 24, -3), (16, 60, 3)), note="+x right, +y up")
    paths.append(p)
    p = os.path.join(out_dir, f"{CASING_NAME}_section_x0.png")
    render_scene(items([(keep(cas, x1=0.0), "cas", 1.0, 0.02), (keep(brd, x1=0.0), "brd", 1.0, 0.02),
                        (keep(mag, x1=0.0), "mag", 1.0, 0.02), (keep(cap, x1=0.0), "cap", 1.0, 0.02)]),
                 p, ((1, 0, 0), (0, 0, 1)), "encoder casing section x = 0 seen from +x: snap-hook lips behind the board, tabs, chip",
                 px=900, bounds=((-3, 21, -16), (3, 43, 16)), note="+y right, +z up")
    paths.append(p)
    z_hole = c.hole_pts[0][1] if c.hole_pts[0][1] > 0 else c.hole_pts[-1][1]
    p = os.path.join(out_dir, f"{CASING_NAME}_section_hole_row.png")
    render_scene(items([(keep(ref["Slipin_mount_piecev3"], x0=-30, x1=-15, y0=25, y1=62, z1=z_hole), "slip", 0.6, 0.03),
                        (keep(cas, z1=z_hole), "cas", 1.0, 0.02)]),
                 p, ((0, 0, 1), (0, 1, 0)), f"foot screw holes over the divot holes: section through the hole row z = {z_hole:+.2f}",
                 px=900, bounds=((-30, 30, -3), (-12, 60, 3)), note="+x right, +y up")
    paths.append(p)
    return paths


# =============================================================================================================================
if __name__ == "__main__":
    c = Cfg()
    for nm, mk, part in (("magnet cap", make_magnet_cap, "cap"), ("encoder casing", make_casing, "casing")):
        wp = mk()
        v = wp.val()
        bb = v.BoundingBox()
        print(f"{nm}: valid={v.isValid()} solids={len(v.Solids())} vol={v.Volume():.1f} mm3 "
              f"mass={v.Volume() * P.ENC1021_PETG_G_CM3 / 1000:.2f} g "
              f"bbox x[{bb.xmin:.3f},{bb.xmax:.3f}] y[{bb.ymin:.3f},{bb.ymax:.3f}] z[{bb.zmin:.3f},{bb.zmax:.3f}] "
              f"size {bb.xlen:.3f} x {bb.ylen:.3f} x {bb.zlen:.3f}")
    print(f"levels: spool face {c.spool_face_y:.3f}  peg end {c.peg_end_y:.3f}  pocket floor {c.pocket_floor_y:.3f}  magnet face "
          f"{c.magnet_face_y:.3f}  chip face {c.chip_face_y:.3f}  PCB {c.pcb_front_y:.3f}..{c.pcb_back_y:.3f}  frame front "
          f"{c.frame_front_y:.3f}  hook catch {c.catch_y:.3f}")
    paths = export_all()
    for k, d in paths.items():
        print(k, d["step"], d["stl"])
    for nm, mk, rgb in ((CAP_NAME, make_magnet_cap, (0.93, 0.55, 0.18)), (CASING_NAME, make_casing, (0.25, 0.55, 0.88))):
        render_part(mk().val(), nm, rgb)
    render_assembly()
    render_sections()
    print("renders ->", RENDER_DIR)
