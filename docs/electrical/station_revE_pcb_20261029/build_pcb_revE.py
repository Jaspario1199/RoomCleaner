#!/usr/bin/env python3
"""Build RoomCleaner Station Rev E (plug-in carrier) for automated assembly.

    /usr/bin/python3 build_pcb_revE.py              # everything (re-uses routing.json if present)
    /usr/bin/python3 build_pcb_revE.py --reroute    # run the router again (writes routing.json)
    /usr/bin/python3 build_pcb_revE.py --place-only # footprints + placement only

Circuit = Rev D, read-only, via ../station_revD_20261021/kicad/perfboard_data.py (which reads
perfboard_layout.py).  Nothing in the Rev D folder is written (bytecode writing is disabled).
Connectivity changes: none.  Pin numbering change: motor connector J2 re-numbered 1A 1B 2A 2B
(J2_REMAP).  Part swap: D1 1N5819 (DO-41) -> SS14 (SMA), same function, pin 1 = cathode.

Board: 70 x 50 mm, 2 layers, plated vias.  SMD parts (R1-R4 1206, D1 SMA) on the top side only
(one stencil, one reflow); modules on female-header sockets and the off-board connectors stay
through-hole and are hand-soldered afterwards (all hand joints on the bottom side).  GND poured on
both layers.  Routing: pathfinder.py (own negotiated-congestion router), checked by KiCad DRC.
Writes into this folder only.
"""
import argparse
import csv
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True            # never write __pycache__ into the Rev D folder
HERE = Path(__file__).resolve().parent
REVD = HERE.parent / "station_revD_20261021" / "kicad"
sys.path.insert(0, str(REVD))
import perfboard_data as pbd  # noqa: E402  (read-only)
sys.path.insert(0, str(HERE))
import maze_router as mr  # noqa: E402
import pathfinder as pf  # noqa: E402

os.environ.setdefault("KICAD7_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
FP_DIR = Path(os.environ["KICAD7_FOOTPRINT_DIR"])
PROJECT = "RoomCleaner_Station_RevE"
LIBNICK = "RoomCleanerRevE"
LIBDIR = HERE / f"{LIBNICK}.pretty"
TITLE = "RoomCleaner Station Rev E (plug-in carrier)"
DATE = "2026-10-29"

BOARD_W, BOARD_H = 70.0, 50.0
OX, OY = 100.0, 100.0          # board (0,0) = KiCad (100 mm, 100 mm); y down, top view
HOLE_INSET = 3.5
HOLES = [(HOLE_INSET, HOLE_INSET), (BOARD_W - HOLE_INSET, HOLE_INSET),
         (HOLE_INSET, BOARD_H - HOLE_INSET), (BOARD_W - HOLE_INSET, BOARD_H - HOLE_INSET)]

# ---------------------------------------------------------------------------
# rules: wide tracks, big clearances (kept from the mill-safe pass)
# ---------------------------------------------------------------------------
EDGE_CLR = 0.5
CLASSES = {   # name: (track width, clearance)
    "Power": (1.2, 0.5),    # +12V / VMOT, motor coils
    "P5V": (0.8, 0.5),      # buck output, diode output, XIAO 5 V
    "GND": (0.8, 0.5),
    "Default": (0.6, 0.4),  # signals and +3V3
}
NET_CLASS = {"+12V": "Power", "M1A": "Power", "M1B": "Power", "M2A": "Power", "M2B": "Power",
             "5VB": "P5V", "5VD": "P5V", "+5V": "P5V", "GND": "GND"}
VIA_D, VIA_DRILL = 1.0, 0.5
ZONE_CLR, ZONE_MIN_W, SPOKE_W, SPOKE_GAP = 0.5, 0.5, 0.6, 0.5
GRID = 0.254


def ncls(net):
    return NET_CLASS.get(net, "Default")


# ---------------------------------------------------------------------------
# connectivity: Rev D nets, J2 renumbered, test pads added (no new nets)
# ---------------------------------------------------------------------------
# Rev D J2: 1 = 2B, 2 = 2A, 3 = 1A, 4 = 1B (as soldered, top to bottom).
# Rev E J2: 1 = 1A, 2 = 1B, 3 = 2A, 4 = 2B (A4988 label order).  Same four nets.
J2_REMAP = {"3": "1", "4": "2", "2": "3", "1": "4"}          # Rev D pin -> Rev E pin
TESTPADS = {"TP1": "+12V", "TP2": "5VB", "TP3": "+3V3", "TP4": "GND"}


def reve_pin(ref, pin):
    return (ref, J2_REMAP[pin]) if ref == "J2" else (ref, pin)


def reve_nets(pb):
    return {n: {reve_pin(r, p) for r, p in pins} for n, pins in pb.nets().items()}


VALUE = {
    "U1": "DROK buck 5.00V", "U2": "XIAO ESP32-C3", "U3": "A4988 carrier",
    "J1": "12V IN", "J2": "MOTOR", "J5": "ENCODER", "J3": "SWITCH",
    "JP1": "USB/EXT 5V link", "D1": "SS14", "C1": "100uF 50V",
    "R1": "10k", "R2": "10k", "R3": "10k", "R4": "10k",
    "TP1": "TP 12V", "TP2": "TP 5V", "TP3": "TP 3V3", "TP4": "TP GND",
    "H1": "M3", "H2": "M3", "H3": "M3", "H4": "M3",
    "FID1": "fiducial", "FID2": "fiducial", "FID3": "fiducial",
}

# ---------------------------------------------------------------------------
# footprint library (THT footprints generated into RoomCleanerRevE.pretty; SMD = stock libraries)
# ---------------------------------------------------------------------------
PAD_LAYERS = '(layers "*.Cu" "*.Mask")'


def fmt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def pad_txt(num, x, y, shape, size, drill):
    return (f'  (pad {q(num)} thru_hole {shape} (at {fmt(x)} {fmt(y)}) (size {fmt(size)} {fmt(size)}) '
            f'(drill {fmt(drill)}) {PAD_LAYERS})\n')


def line_txt(x1, y1, x2, y2, layer, w):
    return (f'  (fp_line (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) '
            f'(stroke (width {w}) (type solid)) (layer {q(layer)}))\n')


def rect_txt(x1, y1, x2, y2, layer, w):
    return (line_txt(x1, y1, x2, y1, layer, w) + line_txt(x2, y1, x2, y2, layer, w) +
            line_txt(x2, y2, x1, y2, layer, w) + line_txt(x1, y2, x1, y1, layer, w))


def poly_txt(pts, layer):
    p = " ".join(f"(xy {fmt(x)} {fmt(y)})" for x, y in pts)
    return f'  (fp_poly (pts {p}) (stroke (width 0.1) (type solid)) (fill solid) (layer {q(layer)}))\n'


def text_txt(kind, text, x, y, layer, size=1.0, th=0.15):
    return (f'  (fp_text {kind} {q(text)} (at {fmt(x)} {fmt(y)}) (layer {q(layer)})\n'
            f'    (effects (font (size {size} {size}) (thickness {th})))\n  )\n')


def header(name, descr, tags, attr="through_hole"):
    return (f'(footprint {q(name)} (version 20221018) (generator build_pcb_revE)\n  (layer "F.Cu")\n'
            f'  (descr {q(descr)})\n  (tags {q(tags)})\n  (attr {attr})\n'
            + text_txt("reference", "REF**", 0, -3, "F.SilkS", 0.9)
            + text_txt("value", name, 0, 3, "F.Fab"))


def fp_xiao():
    """XIAO ESP32-C3 socket: 2 x 1x7 female headers, rows 15.24 mm apart (Rev D RoomCleaner.pretty
    spacing).  Origin = pad 1 (D0).  Row y = 0: pads 1..7 = D0..D6.  Row y = -15.24: pads 14..8 =
    5V, GND, 3V3, D10, D9, D8, D7.  USB-C toward -x."""
    n = "XIAO_ESP32C3_Socket_2x7"
    s = header(n, "Seeed XIAO ESP32-C3 plugged into 2 x 1x7 female headers (2.54 mm), rows 15.24 mm apart; "
                  "USB-C toward -x. Pads 2.0 mm / drill 1.0 mm.", "XIAO ESP32C3 socket")
    x0, x1, y0, y1 = -2.88, 15.24 + 2.88, -15.24 - 1.28, 1.28
    s += rect_txt(x0, y0, x1, y1, "F.SilkS", 0.15)
    s += rect_txt(x0, y0, x1, y1, "F.Fab", 0.1)
    s += rect_txt(-1.27, -1.27, 15.24 + 1.27, 1.27, "F.Fab", 0.1)
    s += rect_txt(-1.27, -15.24 - 1.27, 15.24 + 1.27, -15.24 + 1.27, "F.Fab", 0.1)
    cy = -7.62
    s += poly_txt([(-2.3, cy), (-0.4, cy - 1.4), (-0.4, cy + 1.4)], "F.SilkS")     # USB arrow
    s += rect_txt(-4.4, cy - 4.1, x0, cy + 4.1, "F.Fab", 0.1)                      # USB-C shell
    s += rect_txt(-3.2, y0 - 0.3, x1 + 0.3, y1 + 0.3, "F.CrtYd", 0.05)
    for k in range(7):
        s += pad_txt(str(k + 1), 2.54 * k, 0, "rect" if k == 0 else "circle", 2.0, 1.0)
    for k in range(7):
        s += pad_txt(str(14 - k), 2.54 * k, -15.24, "circle", 2.0, 1.0)
    return n, s + ")\n"


def fp_a4988():
    """Pololu A4988 carrier socket: 2 x 1x8 female headers.  Pad numbers and positions = stock
    Module:Pololu_Breakout-16_15.2x20.3mm (pad 1 GND, 2 VDD, 3 1B, 4 1A, 5 2A, 6 2B, 7 GND,
    8 VMOT at x = 0; 9 EN .. 16 DIR at x = 12.7).  Pads 1.6/0.8 -> 2.0/1.0 for header pins."""
    n = "Pololu_A4988_Socket_2x8"
    s = header(n, "Pololu-style A4988 carrier plugged into 2 x 1x8 female headers; pad map of the stock "
                  "Pololu_Breakout-16_15.2x20.3mm footprint; pads 2.0 mm / drill 1.0 mm.", "A4988 Pololu socket")
    s += rect_txt(-1.5, -1.5, 14.2, 19.28, "F.SilkS", 0.15)
    s += rect_txt(-1.27, -1.27, 13.97, 19.05, "F.Fab", 0.1)
    s += poly_txt([(-1.75, 17.78), (-3.25, 16.78), (-3.25, 18.78)], "F.SilkS")     # arrow at VMOT (pad 8)
    s += rect_txt(-1.75, -1.75, 14.45, 19.55, "F.CrtYd", 0.05)
    for k in range(8):
        s += pad_txt(str(k + 1), 0, 2.54 * k, "rect" if k == 0 else "circle", 2.0, 1.0)
    for k in range(8):
        s += pad_txt(str(16 - k), 12.7, 2.54 * k, "circle", 2.0, 1.0)
    return n, s + ")\n"


def fp_drok():
    """DROK buck on a 1x5 female header, pads toward -x: 1 OUT+, 2 OUT-, 3 IN-, 4 IN+, 5 EN (Rev D)."""
    n = "DROK_Buck_Socket_1x5"
    s = header(n, "DROK buck module on a 1x5 2.54 mm female header (OUT+, OUT-, IN-, IN+, EN); pads run "
                  "toward -x as in Rev D RoomCleaner.pretty; pads 2.0 mm / drill 1.0 mm.", "DROK buck socket")
    s += rect_txt(-11.43 - 0.3, -1.6, 1.27 + 0.3, 1.6, "F.SilkS", 0.15)
    s += rect_txt(-11.43 - 0.55, -1.85, 1.27 + 0.55, 1.85, "F.CrtYd", 0.05)
    for k in range(5):
        s += pad_txt(str(k + 1), -2.54 * k, 0, "rect" if k == 0 else "circle", 2.0, 1.0)
    return n, s + ")\n"


def fp_testpad():
    n = "TestPad_THT_D2.5mm_Drill1.0mm"
    s = header(n, "Bare plated test pad, 2.5 mm, drill 1.0 mm (meter probe or wire loop).", "test point",
               attr="through_hole exclude_from_pos_files exclude_from_bom")
    s += '  (fp_circle (center 0 0) (end 1.6 0) (stroke (width 0.15) (type solid)) (fill none) (layer "F.SilkS"))\n'
    s += '  (fp_circle (center 0 0) (end 1.85 0) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))\n'
    s += pad_txt("1", 0, 0, "circle", 2.5, 1.0)
    return n, s + ")\n"


def fp_mounting_hole():
    n = "MountingHole_3.2mm_M3_NPTH"
    s = header(n, "M3 mounting hole, 3.2 mm, not plated, no copper.", "mounting hole",
               attr="exclude_from_pos_files exclude_from_bom")
    s += '  (fp_circle (center 0 0) (end 2.75 0) (stroke (width 0.15) (type solid)) (fill none) (layer "F.SilkS"))\n'
    s += '  (fp_circle (center 0 0) (end 3.0 0) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))\n'
    s += '  (pad "" np_thru_hole circle (at 0 0) (size 3.2 3.2) (drill 3.2) (layers "*.Cu" "*.Mask"))\n'
    return n, s + ")\n"


# stock THT footprints re-padded (bigger pads for hand soldering): key -> (lib, name, new name, pad size, drill)
STOCK_DERIVED = {
    "JST_XH_4": ("Connector_JST", "JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
                 "JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical_BigPad", 2.0, 1.0),
    "JST_XH_2": ("Connector_JST", "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",
                 "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical_BigPad", 2.0, 1.0),
    "MKDS2": ("TerminalBlock_Phoenix", "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
              "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal_BigPad", 2.6, 1.3),
    "CP8": ("Capacitor_THT", "CP_Radial_D8.0mm_P3.50mm", "CP_Radial_D8.0mm_P3.50mm_BigPad", 2.0, 0.8),
    "HDR2": ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical",
             "PinHeader_1x02_P2.54mm_Vertical_BigPad", 2.0, 1.0),
}
# stock SMD footprints used as they are
STOCK_SMD = {
    "R1206": ("Resistor_SMD", "R_1206_3216Metric"),
    "SMA": ("Diode_SMD", "D_SMA"),
    "FID": ("Fiducial", "Fiducial_1mm_Mask2mm"),
}
PAD_RE = re.compile(r'^\s*\(pad "([^"]*)" thru_hole (\w+) \(at ([-\d.]+) ([-\d.]+)(?: [-\d.]+)?\).*$')
LINE_RE = re.compile(r'^\s*\(fp_line \(start ([-\d.]+) ([-\d.]+)\) \(end ([-\d.]+) ([-\d.]+)\).*\(layer "F\.SilkS"\)')


def seg_point_dist(ax, ay, bx, by, px, py):
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


def derive_stock(lib, name, new, size, drill):
    """Copy a stock THT footprint with bigger round pads (pad 1 square); drop silk lines that would touch them."""
    lines = (FP_DIR / f"{lib}.pretty" / f"{name}.kicad_mod").read_text().splitlines()
    pads = [(m.group(1), float(m.group(3)), float(m.group(4))) for m in map(PAD_RE.match, lines) if m]
    out = []
    for ln in lines:
        m = PAD_RE.match(ln)
        if m:
            num, x, y = m.group(1), float(m.group(3)), float(m.group(4))
            out.append(pad_txt(num, x, y, "rect" if num == "1" else "circle", size, drill).rstrip("\n"))
            continue
        m = LINE_RE.match(ln)
        if m and any(seg_point_dist(*map(float, m.groups()), px, py) < size / 2 + 0.25 for _, px, py in pads):
            continue
        out.append(ln)
    txt = "\n".join(out) + "\n"
    txt = txt.replace(f'(footprint "{name}"', f'(footprint "{new}"', 1)
    txt = re.sub(r'\(descr "', '(descr "Copy of the KiCad stock footprint with bigger pads. ', txt, count=1)
    return new, txt


def write_library():
    shutil.rmtree(LIBDIR, ignore_errors=True)
    LIBDIR.mkdir()
    names = {}
    for key, gen in [("XIAO", fp_xiao), ("A4988", fp_a4988), ("DROK", fp_drok), ("TP", fp_testpad),
                     ("HOLE", fp_mounting_hole)]:
        n, t = gen()
        (LIBDIR / f"{n}.kicad_mod").write_text(t, encoding="utf-8")
        names[key] = (LIBNICK, n, LIBDIR)
    for key, (lib, name, new, size, drill) in STOCK_DERIVED.items():
        n, t = derive_stock(lib, name, new, size, drill)
        (LIBDIR / f"{n}.kicad_mod").write_text(t, encoding="utf-8")
        names[key] = (LIBNICK, n, LIBDIR)
    for key, (lib, name) in STOCK_SMD.items():
        names[key] = (lib, name, FP_DIR / f"{lib}.pretty")
    return names


def write_libtables():
    libs = sorted({lib for lib, _ in STOCK_SMD.values()})
    t = '(fp_lib_table\n  (version 7)\n'
    for lib in libs:
        t += (f'  (lib (name "{lib}")(type "KiCad")(uri "${{KICAD7_FOOTPRINT_DIR}}/{lib}.pretty")(options "")'
              '(descr "KiCad stock library"))\n')
    t += (f'  (lib (name "{LIBNICK}")(type "KiCad")(uri "${{KIPRJMOD}}/{LIBNICK}.pretty")(options "")'
          '(descr "RoomCleaner Station Rev E through-hole footprints (generated by build_pcb_revE.py)"))\n)\n')
    (HERE / "fp-lib-table").write_text(t, encoding="utf-8")


# ---------------------------------------------------------------------------
# placement (board mm, top view; THT: pad 1 position; SMD: footprint centre; rotation CCW deg)
# ---------------------------------------------------------------------------
PLACE = {
    "U2": ("XIAO", 3.81, 25.40, 0),        # USB-C at the left edge; D0..D6 row at y 25.40
    "U3": ("A4988", 52.07, 29.21, 180),    # pad 1 GND bottom-right; VMOT (8) top-right; EN (9) top-left
    "C1": ("CP8", 52.07, 5.08, 180),       # + at 52.07, - at 48.57; 6.35 mm from VMOT
    "J1": ("MKDS2", 64.77, 16.51, 90),     # 12 V: pin 1 (+) y 16.51, pin 2 (-) y 11.43; wires from the right edge
    "J2": ("JST_XH_4", 66.04, 30.48, 90),  # motor: pin 1 (1A) bottom .. pin 4 (2B) top, right edge
    "U1": ("DROK", 29.21, 4.06, 180),      # OUT+ 29.21, OUT- 31.75, IN- 34.29, IN+ 36.83, EN 39.37
    "D1": ("SMA", 20.32, 5.08, 0),         # SMD: K (pad 1) left, A right
    "JP1": ("HDR2", 11.43, 4.06, 270),     # pin 1 (diode side) 11.43, pin 2 (XIAO 5V) 8.89
    "R1": ("R1206", 34.29, 11.43, 0),      # SMD: pad 1 3V3 left, pad 2 EN right (U3 EN at 39.37)
    "R2": ("R1206", 34.29, 26.67, 180),    # SMD: pad 1 STEP right, pad 2 GND left
    "R3": ("R1206", 34.29, 29.21, 180),    # SMD: pad 1 DIR right, pad 2 GND left
    "R4": ("R1206", 25.40, 37.50, 270),    # SMD: pad 1 3V3 top, pad 2 HOME bottom (J3.1 below)
    "J5": ("JST_XH_4", 10.16, 45.72, 0),   # encoder 3V3 GND SDA SCL, bottom edge
    "J3": ("JST_XH_2", 25.40, 45.72, 0),   # switch NC/HOME, COM/GND, bottom edge
    "TP1": ("TP", 57.15, 5.08, 0),
    "TP2": ("TP", 26.67, 11.43, 0),
    "TP3": ("TP", 45.72, 44.45, 0),
    "TP4": ("TP", 50.80, 44.45, 0),
    "FID1": ("FID", 3.50, 40.00, 0),
    "FID2": ("FID", 61.00, 3.50, 0),
    "FID3": ("FID", 66.50, 39.50, 0),
}
for k, (hx, hy) in enumerate(HOLES):
    PLACE[f"H{k + 1}"] = ("HOLE", hx, hy, 0)


# ---------------------------------------------------------------------------
# board helpers
# ---------------------------------------------------------------------------
def V(pcbnew, x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))


def bxy(pcbnew, p):
    return pcbnew.ToMM(p.x) - OX, pcbnew.ToMM(p.y) - OY


def add_outline(pcbnew, board):
    pts = [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H)]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(pcbnew, *a))
        s.SetEnd(V(pcbnew, *b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(pcbnew.FromMM(0.1))
        board.Add(s)


def build_board(pcbnew, nets, libnames):
    board = pcbnew.BOARD()
    add_outline(pcbnew, board)
    netinfo = {}
    for n in sorted(nets):
        ni = pcbnew.NETINFO_ITEM(board, n)
        board.Add(ni)
        netinfo[n] = ni
    pad_net = {rp: n for n, pins in nets.items() for rp in pins}
    for ref, (key, x, y, rot) in PLACE.items():
        nick, name, path = libnames[key]
        fp = pcbnew.FootprintLoad(str(path), name)
        if fp is None:
            raise SystemExit(f"footprint {name} not found")
        fp.SetFPID(pcbnew.LIB_ID(nick, name))
        fp.SetReference(ref)
        fp.SetValue(VALUE.get(ref, name))
        fp.Value().SetLayer(pcbnew.F_Fab)
        board.Add(fp)
        fp.SetPosition(V(pcbnew, x, y))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            n = pad_net.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
            if ref.startswith("FID"):
                pad.SetLocalClearance(pcbnew.FromMM(1.5))     # copper-free ring well outside the 2 mm mask opening
    return board, netinfo


def pad_items(pcbnew, board):
    """Router obstacle items for every pad and NPTH hole; pad centres and layers per (ref, pin)."""
    items, centres = [], {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            x, y = bxy(pcbnew, pad.GetPosition())
            net = pad.GetNetname() or None
            sz = pad.GetSize()
            sx, sy = pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y)
            if round(pad.GetOrientationDegrees()) % 180 == 90:
                sx, sy = sy, sx
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                items.append(dict(kind="circle", cx=x, cy=y, r=pcbnew.ToMM(pad.GetDrillSize().x) / 2,
                                  net=None, clr=0.5, layers=(0, 1), hole=True))
                continue
            layers = tuple(l for l, lid in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)) if pad.IsOnLayer(lid))
            clr = CLASSES[ncls(net)][1] if net else 0.4
            if pad.GetShape() == pcbnew.PAD_SHAPE_CIRCLE:
                it = dict(kind="circle", cx=x, cy=y, r=sx / 2)
            else:
                it = dict(kind="rect", cx=x, cy=y, hw=sx / 2, hh=sy / 2)
            it.update(net=net, clr=clr, layers=layers, hole=pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH)
            items.append(it)
            centres[(fp.GetReference(), pad.GetNumber())] = (x, y, net, layers)
    return items, centres


# ---------------------------------------------------------------------------
# routing
# ---------------------------------------------------------------------------
ROUTE_ORDER = ["+12V", "M2B", "M2A", "M1A", "M1B", "5VB", "5VD", "+5V", "EN", "STEP", "DIR", "SDA", "SCL",
               "HOME", "+3V3", "GND"]


def route_all(items, centres, nets, iters, log=print):
    import numpy as np
    grid = mr.Grid(BOARD_W, BOARD_H, GRID, EDGE_CLR)
    # no via within 2.0 mm of any drilled hole centre or on top of any SMD pad
    near_hole = np.zeros((grid.ny, grid.nx), dtype=bool)
    for it in items:
        R = 2.0 if it.get("hole") else (max(it.get("hw", 0), it.get("hh", 0), it.get("r", 0)) + 0.8)
        sl, d = grid.dist_window(dict(kind="circle", cx=it["cx"], cy=it["cy"], r=0), R)
        if sl is not None:
            near_hole[sl] |= d < R
    pnets, hard, vok, exact = [], {}, {}, {}
    for name in ROUTE_ORDER:
        w, clr = CLASSES[ncls(name)]
        masks = [grid.blocked_mask(items, name, clr, w / 2, layer=l) for l in (0, 1)]
        pins = []
        for rp in nets[name]:
            x, y, _, layers = centres[rp]
            i, j = grid.cell(x, y)
            k = grid.idx(i, j)
            for l in layers:
                masks[l][j, i] = False
            pins.append((rp, x, y, k, layers))
            exact[k] = (x, y)
        hard[name] = [bytearray((~m).astype(np.uint8).ravel().tobytes()) for m in masks]
        mv = grid.blocked_mask(items, name, max(clr, 0.5), pf.VIA_R) | near_hole
        vok[name] = bytearray((~mv).astype(np.uint8).ravel().tobytes())
        pnets.append(pf.Net(name, w / 2, pins))
    neg = pf.Negotiator(grid, pnets, hard, vok)
    ok = neg.run(ROUTE_ORDER, iters=iters, log=log)
    conf, _ = neg.conflicts()
    tracks = neg.tracks(lambda n: CLASSES[ncls(n)][0], exact)
    return dict(ok=ok, conflicts=sum(conf.values()), tracks=tracks, vias=neg.via_list(),
                length=round(sum(math.hypot(t[4] - t[2], t[5] - t[3]) for t in tracks), 1))


# ---------------------------------------------------------------------------
# finishing: tracks, vias, labels, pours
# ---------------------------------------------------------------------------
def add_via(pcbnew, board, ni, x, y):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(V(pcbnew, x, y))
    v.SetWidth(pcbnew.FromMM(VIA_D))
    v.SetDrill(pcbnew.FromMM(VIA_DRILL))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(ni)
    board.Add(v)
    return v


def add_tracks(pcbnew, board, netinfo, tracks, vias):
    for net, layer, x1, y1, x2, y2, w in tracks:
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(V(pcbnew, x1, y1))
        t.SetEnd(V(pcbnew, x2, y2))
        t.SetWidth(pcbnew.FromMM(w))
        t.SetLayer(pcbnew.F_Cu if layer == 0 else pcbnew.B_Cu)
        t.SetNet(netinfo[net])
        board.Add(t)
    for net, x, y in vias:
        add_via(pcbnew, board, netinfo[net], x, y)


def text(pcbnew, board, s, x, y, layer, size=1.0, th=0.15, rot=0, just="c"):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    t.SetTextThickness(pcbnew.FromMM(th))
    t.SetTextAngleDegrees(rot)
    t.SetHorizJustify({"l": pcbnew.GR_TEXT_H_ALIGN_LEFT, "c": pcbnew.GR_TEXT_H_ALIGN_CENTER,
                       "r": pcbnew.GR_TEXT_H_ALIGN_RIGHT}[just])
    t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    t.SetPosition(V(pcbnew, x, y))
    board.Add(t)
    return t


def silk_labels(pcbnew, board, centres):
    F = pcbnew.F_SilkS

    def P(r, n):
        return centres[(r, n)][:2]

    def tx(s, x, y, **k):
        return text(pcbnew, board, s, x, y, F, **k)

    tx("RoomCleaner Station Rev E", 45.72, 35.6, size=1.1, th=0.17)
    tx(DATE, 45.72, 37.6, size=0.9)
    # J1 12 V
    x, y = P("J1", "1"); tx("+", x - 7.2, y, size=1.6, th=0.25)
    x, y = P("J1", "2"); tx("−", x - 7.2, y, size=1.6, th=0.25)
    tx("12V", x - 7.2, y + 2.55, size=0.9)
    # J2 motor
    for pin, name in (("1", "1A"), ("2", "1B"), ("3", "2A"), ("4", "2B")):
        x, y = P("J2", pin); tx(name, x - 3.6, y, size=0.8, just="r")
    x, y = P("J2", "1"); tx("MOTOR", x + 0.4, y + 4.6, size=1.0)
    # J5 encoder, J3 switch
    for pin, name in (("1", "3V3"), ("2", "GND"), ("3", "SDA"), ("4", "SCL")):
        x, y = P("J5", pin); tx(name, x, y - 4.6, size=0.8, rot=90)
    x, y = P("J5", "1"); tx("ENCODER", x + 3.75, y - 8.0, size=1.0)
    for pin, name in (("1", "NC"), ("2", "COM")):
        x, y = P("J3", pin); tx(name, x, y - 4.6, size=0.8, rot=90)
    x, y = P("J3", "2"); tx("SWITCH", x + 6.4, y + 1.0, size=1.0)
    # XIAO
    x, y = P("U2", "1"); tx("XIAO ESP32-C3", x + 9.5, y - 7.62, size=1.0)
    tx("USB", x + 0.6, y - 7.62, size=0.8, rot=90)
    for pin, name in (("14", "5V"), ("13", "GND"), ("12", "3V3"), ("11", "D10")):
        x, y = P("U2", pin); tx(name, x, y + 2.9, size=0.8, rot=90)
    for pin, name in (("2", "STEP"), ("3", "DIR"), ("4", "EN"), ("5", "SDA"), ("6", "SCL")):
        x, y = P("U2", pin); tx(name, x, y - 3.2, size=0.8, rot=90)
    # A4988: pin names inside the socket outline, VMOT marker outside
    for pin, name in (("8", "VMOT"), ("7", "GND"), ("6", "2B"), ("5", "2A"), ("4", "1A"), ("3", "1B"),
                      ("2", "VDD"), ("1", "GND")):
        x, y = P("U3", pin); tx(name, x - 1.6, y, size=0.8, just="r")
    for pin, name in (("9", "EN"), ("10", "MS1"), ("11", "MS2"), ("12", "MS3"), ("13", "RST"), ("14", "SLP"),
                      ("15", "STEP"), ("16", "DIR")):
        x, y = P("U3", pin); tx(name, x + 1.6, y, size=0.8, just="l")
    x, y = P("U3", "8"); tx("A4988", x - 6.35, y + 9.5, size=1.0, rot=90)
    tx("VMOT", x + 3.4, y - 1.9, size=0.8)
    # DROK buck
    for pin, name in (("1", "O+"), ("2", "O-"), ("3", "I-"), ("4", "I+"), ("5", "EN")):
        x, y = P("U1", pin); tx(name, x, y + 2.3, size=0.8)
    x, y = P("U1", "3"); tx("DROK 5V BUCK", x, y - 2.5, size=0.8)
    # JP1
    x, y = P("JP1", "2"); tx("JP1: OFF for USB, ON for 12 V", x - 1.0, y + 3.6, size=0.8, just="l")
    # test pads
    for tp, name in (("TP1", "12V"), ("TP2", "5V"), ("TP3", "3V3"), ("TP4", "GND")):
        x, y = P(tp, "1"); tx(name, x, y + 2.5, size=0.8)


REF_OFFSET = {   # reference designator position relative to the footprint anchor (board mm)
    "U2": (9.5, -9.4), "U3": (-6.35, -3.0), "U1": (-1.5, -2.5), "J1": (-2.5, -8.6), "J2": (-3.6, 3.5),
    "J5": (3.75, -10.2), "J3": (6.4, -1.0), "JP1": (-1.27, -2.4), "D1": (0, -2.6), "C1": (-7.35, 0),
    "R1": (0, -2.0), "R2": (-4.3, 0), "R3": (-4.3, 0), "R4": (-2.6, 0),
}


def set_refs(pcbnew, board):
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        r = fp.Reference()
        if ref not in REF_OFFSET:
            r.SetVisible(False)
            continue
        r.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.9), pcbnew.FromMM(0.9)))
        r.SetTextThickness(pcbnew.FromMM(0.15))
        dx, dy = REF_OFFSET[ref]
        x, y = bxy(pcbnew, fp.GetPosition())
        r.SetPosition(V(pcbnew, x + dx, y + dy))
        r.SetTextAngleDegrees(0)


def add_gnd_pours(pcbnew, board, netinfo):
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(netinfo["GND"])
        ol = z.Outline()
        ol.NewOutline()
        for x, y in [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H)]:
            ol.Append(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))
        z.SetLocalClearance(pcbnew.FromMM(ZONE_CLR))
        z.SetMinThickness(pcbnew.FromMM(ZONE_MIN_W))
        z.SetThermalReliefGap(pcbnew.FromMM(SPOKE_GAP))
        z.SetThermalReliefSpokeWidth(pcbnew.FromMM(SPOKE_W))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetZoneName("GND_F" if layer == pcbnew.F_Cu else "GND_B")
        board.Add(z)


def stitch_positions(items, tracks, vias, pitch=5.08):
    """GND stitching via sites on a grid wherever a via fits clear of all other copper."""
    grid = mr.Grid(BOARD_W, BOARD_H, GRID, EDGE_CLR + 1.0)
    obst = []
    for net, layer, x1, y1, x2, y2, w in tracks:
        obst.append(dict(kind="seg", x1=x1, y1=y1, x2=x2, y2=y2, r=w / 2, net=net, clr=0.6))
    for net, x, y in vias:
        obst.append(dict(kind="circle", cx=x, cy=y, r=VIA_D / 2, net=net, clr=0.6))
    for it in items:   # keep stitching vias off every pad and hole, GND ones too
        clr = 1.2 if it.get("hole") else (2.0 if it["net"] is None else 0.6)     # fiducials: wide ring
        obst.append(dict(it, net="__pad__", clr=clr))
    m = grid.blocked_mask(obst, "GND", 0.6, VIA_D / 2)
    out = []
    y = pitch / 2
    while y < BOARD_H:
        x = pitch / 2
        while x < BOARD_W:
            i, j = grid.cell(x, y)
            if not m[j, i]:
                out.append((round(x, 3), round(y, 3)))
            x += pitch
        y += pitch
    return out


def fill_zones(pcbnew, board):
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def prune_stitching(pcbnew, board, sites):
    """Remove stitching vias that do not land in the GND fill on both layers."""
    zones = {z.GetLayer(): z for z in board.Zones()}
    want = {(round(x, 2), round(y, 2)) for x, y in sites}
    removed = 0
    for t in list(board.GetTracks()):
        if t.GetClass() != "PCB_VIA" or t.GetNetname() != "GND":
            continue
        x, y = bxy(pcbnew, t.GetPosition())
        if (round(x, 2), round(y, 2)) not in want:
            continue
        p = t.GetPosition()
        if not (zones[pcbnew.F_Cu].HitTestFilledArea(pcbnew.F_Cu, p) and
                zones[pcbnew.B_Cu].HitTestFilledArea(pcbnew.B_Cu, p)):
            board.Remove(t)
            removed += 1
    return removed


# ---------------------------------------------------------------------------
# project file
# ---------------------------------------------------------------------------
def patch_project():
    path = HERE / f"{PROJECT}.kicad_pro"
    d = json.loads(path.read_text()) if path.exists() else {}
    bd = d.setdefault("board", {}).setdefault("design_settings", {})
    rules = bd.setdefault("rules", {})
    rules.update({"min_clearance": 0.4, "min_track_width": 0.6, "min_copper_edge_clearance": EDGE_CLR,
                  "min_hole_clearance": 0.25, "min_hole_to_hole": 0.5, "min_through_hole_diameter": 0.5,
                  "min_via_diameter": VIA_D, "min_via_annular_width": 0.25, "min_connection": 0.5,
                  "min_resolved_spokes": 1, "min_text_height": 0.7, "min_text_thickness": 0.12,
                  "min_silk_clearance": 0.0, "solder_mask_to_copper_clearance": 0.0, "max_error": 0.005})
    bd["via_dimensions"] = [{"diameter": 0.0, "drill": 0.0}, {"diameter": VIA_D, "drill": VIA_DRILL}]
    sev = bd.setdefault("rule_severities", {})
    sev.update({"courtyards_overlap": "error", "lib_footprint_issues": "ignore", "lib_footprint_mismatch": "ignore"})
    classes = []
    for name, (w, c) in CLASSES.items():
        classes.append({"name": name, "clearance": c, "track_width": w, "via_diameter": VIA_D, "via_drill": VIA_DRILL,
                        "microvia_diameter": 0.3, "microvia_drill": 0.1, "diff_pair_gap": 0.25,
                        "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2, "line_style": 0, "wire_width": 6,
                        "bus_width": 12, "pcb_color": "rgba(0, 0, 0, 0.000)",
                        "schematic_color": "rgba(0, 0, 0, 0.000)",
                        "priority": 2147483647 if name == "Default" else 0})
    d["net_settings"] = {"classes": classes, "meta": {"version": 3}, "net_colors": None,
                         "netclass_assignments": None,
                         "netclass_patterns": [{"netclass": c, "pattern": n} for n, c in sorted(NET_CLASS.items())]}
    d.setdefault("meta", {"filename": f"{PROJECT}.kicad_pro", "version": 1})
    path.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# DRC, exports, BOM
# ---------------------------------------------------------------------------
def run(cmd, cwd=HERE):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise SystemExit(f"command failed: {' '.join(map(str, cmd))}")
    return r.stdout


def drc(pcbnew):
    board = pcbnew.LoadBoard(str(HERE / f"{PROJECT}.kicad_pcb"))
    out = HERE / f"{PROJECT}_drc.rpt"
    pcbnew.WriteDRCReport(board, str(out), pcbnew.EDA_UNITS_MILLIMETRES, True)
    txt = out.read_text()
    nv = int(re.search(r"Found (\d+) DRC violations", txt).group(1))
    nu = int(re.search(r"Found (\d+) unconnected pads", txt).group(1))
    nerr = len(re.findall(r"Severity: error", txt))
    nwarn = len(re.findall(r"Severity: warning", txt))
    print(f"DRC: {nv} violations ({nerr} errors, {nwarn} warnings), {nu} unconnected")
    return nv, nerr, nwarn, nu


def exports():
    pcb = f"{PROJECT}.kicad_pcb"
    g = HERE / "gerbers"
    shutil.rmtree(g, ignore_errors=True)
    g.mkdir()
    run(["kicad-cli", "pcb", "export", "gerbers", "-l",
         "F.Cu,B.Cu,F.Paste,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts", "--subtract-soldermask", "-o", "gerbers/", pcb])
    run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm",
         "--drill-origin", "absolute", "--excellon-separate-th", "-o", "gerbers/", pcb])
    z = HERE / f"{PROJECT}_fab.zip"
    z.unlink(missing_ok=True)
    files = sorted(p.name for p in g.iterdir())
    run(["zip", "-j", "-X", str(z)] + [str(g / f) for f in files])
    print(f"  {z.name}: {', '.join(files)}")
    shutil.rmtree(g)            # the zip is the deliverable
    run(["kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "front", "--smd-only",
         "--use-drill-file-origin", "-o", f"{PROJECT}_pos.csv", pcb])
    run(["kicad-cli", "pcb", "export", "pdf", "-l", "F.SilkS,F.Fab,F.Paste,Edge.Cuts", "--ibt",
         "-o", f"{PROJECT}_assembly.pdf", pcb])
    tmp = HERE / "_render"
    tmp.mkdir(exist_ok=True)
    run(["kicad-cli", "pcb", "export", "pdf", "-l", "F.Cu,F.Paste,F.SilkS,Edge.Cuts", "--drill-shape-opt", "2",
         "-o", str(tmp / "top.pdf"), pcb])
    run(["kicad-cli", "pcb", "export", "pdf", "-l", "B.Cu,B.SilkS,Edge.Cuts", "--drill-shape-opt", "2", "--mirror",
         "-o", str(tmp / "bottom.pdf"), pcb])
    for side in ("top", "bottom"):
        run(["pdftoppm", "-r", "300", "-png", "-singlefile", str(tmp / f"{side}.pdf"), str(tmp / side)])
        run(["convert", str(tmp / f"{side}.png"), "-trim", "+repage", "-bordercolor", "white", "-border", "20",
             str(HERE / f"{PROJECT}_{side}.png")])
    shutil.rmtree(tmp)


BOM_INFO = {   # ref prefix or ref: (description, manufacturer part number, supplier note)
    "R": ("10k 1% 1/4 W thick film, 1206", "Yageo RC1206FR-0710KL", "LCSC C17902 (verify before ordering)"),
    "D1": ("Schottky 40 V 1 A, SMA (replaces 1N5819 DO-41, same function)", "onsemi SS14 / MDD SS14",
           "LCSC C2480 (verify before ordering)"),
    "C1": ("100 uF 50 V aluminium electrolytic, radial 8 mm, 3.5 mm pitch", "Panasonic EEU-FR1H101", ""),
    "J1": ("Screw terminal 2-pole 5.08 mm", "Phoenix Contact 1729128 (MKDS 1,5/ 2-5,08)", ""),
    "J2": ("JST-XH 4-pin, top entry", "JST B4B-XH-A(LF)(SN)", "mating XHP-4 + SXH-001T-P0.6 crimps"),
    "J5": ("JST-XH 4-pin, top entry", "JST B4B-XH-A(LF)(SN)", "mating XHP-4 + SXH-001T-P0.6 crimps"),
    "J3": ("JST-XH 2-pin, top entry", "JST B2B-XH-A(LF)(SN)", "mating XHP-2 + SXH-001T-P0.6 crimps"),
    "JP1": ("1x2 male header 2.54 mm + jumper shunt", "Sullins PRPC002SAAN-RC + QPC02SXGN-RC", ""),
    "U1": ("Socket: 1x5 female header 2.54 mm (module: DROK mini buck, set to 5.00 V)", "Sullins PPTC051LFBN-RC", ""),
    "U2": ("Socket: 2 x 1x7 female header 2.54 mm (module: Seeed XIAO ESP32-C3, 113991054)",
           "Sullins PPTC071LFBN-RC", "2 strips per board"),
    "U3": ("Socket: 2 x 1x8 female header 2.54 mm (module: Pololu A4988 carrier, #1182)",
           "Sullins PPTC081LFBN-RC", "2 strips per board"),
}


def bom(pcbnew):
    board = pcbnew.LoadBoard(str(HERE / f"{PROJECT}.kicad_pcb"))

    def order(r):
        return re.sub(r"\d", "", r), int(re.sub(r"\D", "", r) or 0)

    groups = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if re.match(r"^(H|TP|FID)\d", ref):
            continue
        smd = bool(fp.GetAttributes() & pcbnew.FP_SMD)
        key = (smd, fp.GetValue(), str(fp.GetFPID().GetLibNickname()) + ":" + str(fp.GetFPID().GetLibItemName()))
        groups.setdefault(key, []).append(ref)
    out = HERE / f"{PROJECT}_BOM.csv"
    lines = 0
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Process", "Reference", "Qty/board", "Qty/10 boards", "Value", "Description", "Footprint",
                    "Manufacturer part", "Supplier / note"])
        for smd in (True, False):
            rows = sorted(((k, v) for k, v in groups.items() if k[0] == smd),
                          key=lambda kv: order(sorted(kv[1], key=order)[0]))
            for (_, val, fpn), refs in rows:
                refs = sorted(refs, key=order)
                info = BOM_INFO.get(refs[0]) or BOM_INFO.get(re.sub(r"\d", "", refs[0]), ("", "", ""))
                per = len(refs) * (2 if refs[0] in ("U2", "U3") else 1)
                w.writerow(["machine placed (SMD, top, reflow)" if smd else "hand soldered (THT, after reflow)",
                            " ".join(refs), per, per * 10, val, info[0], fpn, info[1], info[2]])
                lines += 1
        w.writerow(["not a part", "TP1 TP2 TP3 TP4", 4, 40, "test pads", "bare plated pads", "", "", ""])
        w.writerow(["not a part", "FID1 FID2 FID3", 3, 30, "fiducials", "1 mm copper, 2 mm mask opening", "", "", ""])
        w.writerow(["not a part", "H1 H2 H3 H4", 4, 40, "M3 holes", "3.2 mm unplated", "", "", ""])
        w.writerow(["modules (plug in)", "U1 U2 U3", "1 each", "10 each", "DROK buck, XIAO ESP32-C3, A4988 carrier",
                    "plugged into the sockets, not soldered to this board", "", "", ""])
    print("BOM:", out.name, lines, "part lines")
    return lines


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reroute", action="store_true")
    ap.add_argument("--place-only", action="store_true")
    ap.add_argument("--route-only", action="store_true")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--iters", type=int, default=40)
    a = ap.parse_args()
    import pcbnew
    pb = pbd.Perfboard()
    nets = reve_nets(pb)
    for tp, n in TESTPADS.items():
        nets[n].add((tp, "1"))
    libnames = write_library()
    write_libtables()
    board, netinfo = build_board(pcbnew, nets, libnames)
    items, centres = pad_items(pcbnew, board)
    pcb_path = HERE / f"{PROJECT}.kicad_pcb"
    if a.place_only:
        board.Save(str(pcb_path))
        print("placement saved")
        return
    rpath = HERE / "routing.json"
    if a.reroute or not rpath.exists():
        t0 = time.time()
        res = route_all(items, centres, nets, a.iters)
        print(f"routing: ok={res['ok']} conflicts={res['conflicts']} vias={len(res['vias'])} "
              f"length={res['length']} mm ({time.time() - t0:.0f} s)")
        rpath.write_text(json.dumps(res, indent=1))
    R = json.loads(rpath.read_text())
    if a.route_only:
        return
    if not R["ok"]:
        raise SystemExit("routing.json holds an unfinished routing; run --reroute")
    add_tracks(pcbnew, board, netinfo, R["tracks"], R["vias"])
    sites = stitch_positions(items, R["tracks"], R["vias"])
    for x, y in sites:
        add_via(pcbnew, board, netinfo["GND"], x, y)
    silk_labels(pcbnew, board, centres)
    set_refs(pcbnew, board)
    tb = board.GetTitleBlock()
    tb.SetTitle(TITLE)
    tb.SetDate(DATE)
    tb.SetRevision("E")
    board.GetDesignSettings().SetAuxOrigin(V(pcbnew, 0, BOARD_H))      # pick-and-place origin: lower-left corner
    add_gnd_pours(pcbnew, board, netinfo)
    board.Save(str(pcb_path))
    patch_project()
    board = pcbnew.LoadBoard(str(pcb_path))       # reload with the project rules (net classes)
    fill_zones(pcbnew, board)
    rm = prune_stitching(pcbnew, board, sites)
    fill_zones(pcbnew, board)
    board.Save(str(pcb_path))
    patch_project()
    print(f"stitching vias: {len(sites) - rm} kept ({rm} pruned)")
    drc(pcbnew)
    if not a.no_export:
        exports()
        bom(pcbnew)


if __name__ == "__main__":
    main()
