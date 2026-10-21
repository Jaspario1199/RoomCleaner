#!/usr/bin/env python3
"""Generate the RoomCleaner winch-station Rev D KiCad 7 project (as soldered).

    /usr/bin/python3 build_kicad.py            # project + exports (+ PCB if pcbnew imports)
    /usr/bin/python3 build_kicad.py --no-export
    /usr/bin/python3 build_kicad.py --no-pcb

Connectivity is NOT typed here: every pin's net comes from perfboard_data.py,
which reads ../perfboard_layout.py (PINS / BARE / WIRES / NETMAP).  This file
only decides where symbols sit on the sheet and how each pin is wired out to a
net label or power symbol.  check_netlist.py then proves the exported netlist
equals the perfboard nets.

Writes (all inside this folder): RoomCleaner_Station_RevD.kicad_pro/.kicad_sch/
.kicad_pcb, RoomCleaner.kicad_sym, RoomCleaner.pretty/*.kicad_mod,
sym-lib-table, fp-lib-table; with exports: netlist XML, PDF, PNG preview.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import perfboard_data as pbd  # noqa: E402

PROJECT = "RoomCleaner_Station_RevD"
SYM_DIR = Path(os.environ.get("KICAD7_SYMBOL_DIR", "/usr/share/kicad/symbols"))
FP_DIR = Path(os.environ.get("KICAD7_FOOTPRINT_DIR", "/usr/share/kicad/footprints"))
NS = uuid.UUID("5b0f1f3e-7a55-4c3e-9d10-20261021aa01")   # fixed: regeneration is reproducible
G = 1.27                                                  # schematic grid (50 mil)
TITLE = "RoomCleaner winch station \u2014 Rev D (as soldered)"
DATE = "2026-10-21"

# ---------------------------------------------------------------------------
# small s-expression helpers
# ---------------------------------------------------------------------------


def fmt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def snap(v):
    return round(round(v / G) * G, 2)


def q(s):
    """Quote a string for a KiCad s-expression."""
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def parse_sexpr(text):
    i, n, stack = 0, len(text), [[]]
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c == "(":
            stack.append([])
            i += 1
        elif c == ")":
            done = stack.pop()
            stack[-1].append(done)
            i += 1
        elif c == '"':
            j, buf = i + 1, []
            while text[j] != '"':
                if text[j] == "\\":
                    buf.append(text[j + 1])
                    j += 2
                else:
                    buf.append(text[j])
                    j += 1
            stack[-1].append("".join(buf))
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in " \t\r\n()":
                j += 1
            stack[-1].append(text[i:j])
            i = j
    return stack[0][0]


def extract_symbol(lib_file, name):
    """Return the exact text of `(symbol "name" ...)` from a .kicad_sym file."""
    t = Path(lib_file).read_text()
    i = t.index(f'(symbol "{name}"')
    depth, j, instr = 0, i, False
    while True:
        ch = t[j]
        if ch == '"' and t[j - 1] != "\\":
            instr = not instr
        elif not instr:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
        j += 1
    text = t[i:j + 1]
    if "(extends " in text.split("\n", 1)[0]:
        raise SystemExit(f"{lib_file}:{name} is a derived symbol; pick a plain one")
    return text


class LibSymbol:
    """A symbol as embedded in the schematic's lib_symbols (name = nick:name)."""

    def __init__(self, nick, name, raw_text):
        self.lib_id = f"{nick}:{name}"
        self.name = name
        self.text = raw_text.replace(f'(symbol "{name}"', f'(symbol "{self.lib_id}"', 1)
        self.tree = parse_sexpr(raw_text)
        self.pins, self.props = {}, {}
        self.is_power = any(isinstance(x, list) and x and x[0] == "power" for x in self.tree)
        self._walk(self.tree)

    def _walk(self, node):
        for x in node:
            if not isinstance(x, list) or not x:
                continue
            if x[0] == "pin":
                at = next(y for y in x if isinstance(y, list) and y[0] == "at")
                ln = next(y for y in x if isinstance(y, list) and y[0] == "length")
                nm = next(y for y in x if isinstance(y, list) and y[0] == "name")
                nu = next(y for y in x if isinstance(y, list) and y[0] == "number")
                self.pins[nu[1]] = dict(num=nu[1], name=nm[1], type=x[1], x=float(at[1]), y=float(at[2]),
                                        ang=float(at[3]), length=float(ln[1]))
            elif x[0] == "property":
                at = next(y for y in x if isinstance(y, list) and y[0] == "at")
                eff = next((y for y in x if isinstance(y, list) and y[0] == "effects"), [])
                just = next((y[1:] for y in eff if isinstance(y, list) and y[0] == "justify"), [])
                hide = "hide" in eff
                self.props[x[1]] = dict(value=x[2], x=float(at[1]), y=float(at[2]), ang=float(at[3]),
                                        justify=just, hide=hide)
            else:
                self._walk(x)


def stock(nick, name):
    return LibSymbol(nick, name, extract_symbol(SYM_DIR / f"{nick}.kicad_sym", name))


# ---------------------------------------------------------------------------
# custom symbols (RoomCleaner.kicad_sym)
# ---------------------------------------------------------------------------
EFF = "(effects (font (size 1.27 1.27)))"
EFF_HIDE = "(effects (font (size 1.27 1.27)) hide)"


def sym_pin(ptype, x, y, ang, length, name, num):
    return (f'      (pin {ptype} line (at {fmt(x)} {fmt(y)} {fmt(ang)}) (length {fmt(length)})\n'
            f'        (name {q(name)} {EFF})\n'
            f'        (number {q(num)} {EFF})\n      )\n')


def custom_symbol(name, footprint, datasheet, keywords, descr, fp_filter, ref_at, val_at, body, pins, body_text=""):
    s = f'  (symbol {q(name)} (in_bom yes) (on_board yes)\n'
    s += f'    (property "Reference" "U" (at {ref_at[0]} {ref_at[1]} 0)\n      {EFF}\n    )\n'
    s += f'    (property "Value" {q(name)} (at {val_at[0]} {val_at[1]} 0)\n      {EFF}\n    )\n'
    s += f'    (property "Footprint" {q(footprint)} (at 0 0 0)\n      {EFF_HIDE}\n    )\n'
    s += f'    (property "Datasheet" {q(datasheet)} (at 0 0 0)\n      {EFF_HIDE}\n    )\n'
    s += f'    (property "ki_keywords" {q(keywords)} (at 0 0 0)\n      {EFF_HIDE}\n    )\n'
    s += f'    (property "ki_description" {q(descr)} (at 0 0 0)\n      {EFF_HIDE}\n    )\n'
    s += f'    (property "ki_fp_filters" {q(fp_filter)} (at 0 0 0)\n      {EFF_HIDE}\n    )\n'
    s += f'    (symbol {q(name + "_0_1")}\n'
    s += (f'      (rectangle (start {fmt(body[0])} {fmt(body[1])}) (end {fmt(body[2])} {fmt(body[3])})\n'
          f'        (stroke (width 0.254) (type default))\n        (fill (type background))\n      )\n')
    s += body_text
    s += '    )\n'
    s += f'    (symbol {q(name + "_1_1")}\n'
    s += "".join(pins)
    s += '    )\n  )\n'
    return s


def xiao_symbol_text():
    # Seeed pad order: 1..7 = D0..D6 (left column), 8..14 = D7,D8,D9,D10,3V3,GND,5V
    # (right column listed bottom-up so that 5V is on top, as on the module).
    pins = []
    for k in range(7):
        pins.append(sym_pin("bidirectional", -12.7, 22.86 - 7.62 * k, 0, 5.08, f"D{k}", str(k + 1)))
    right = [("5V", "14", "power_in"), ("GND", "13", "power_in"), ("3V3", "12", "power_out"),
             ("D10", "11", "bidirectional"), ("D9", "10", "bidirectional"),
             ("D8", "9", "bidirectional"), ("D7", "8", "bidirectional")]
    for k, (nm, num, ty) in enumerate(right):
        pins.append(sym_pin(ty, 12.7, 22.86 - 7.62 * k, 180, 5.08, nm, num))
    body_text = (f'      (text "XIAO" (at 0 3.81 0)\n        {EFF}\n      )\n'
                 f'      (text "ESP32-C3" (at 0 -3.81 0)\n        {EFF}\n      )\n'
                 f'      (text "USB-C" (at 0 26.035 0)\n        {EFF}\n      )\n')
    return custom_symbol(
        "XIAO_ESP32C3", "RoomCleaner:XIAO_ESP32C3_THT",
        "https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/",
        "Seeed XIAO ESP32-C3 ESP32C3 module",
        "Seeed Studio XIAO ESP32-C3, 14 pin module (2 x 7, 2.54 mm), D0-D10 / 3V3 / GND / 5V",
        "XIAO*ESP32C3*", (0, 30.48), (0, -27.94), (-7.62, 27.94, 7.62, -25.4), pins, body_text)


def drok_symbol_text():
    pins = [sym_pin("power_out", 15.24, 5.08, 180, 5.08, "OUT+", "1"),
            sym_pin("passive", 15.24, -5.08, 180, 5.08, "OUT-", "2"),
            sym_pin("passive", -15.24, -5.08, 0, 5.08, "IN-", "3"),
            sym_pin("power_in", -15.24, 5.08, 0, 5.08, "IN+", "4"),
            sym_pin("input", 0, -15.24, 90, 5.08, "EN", "5")]
    body_text = (f'      (text "DROK" (at 0 2.54 0)\n        {EFF}\n      )\n'
                 f'      (text "buck" (at 0 0 0)\n        {EFF}\n      )\n'
                 f'      (text "5.00 V" (at 0 -2.54 0)\n        {EFF}\n      )\n')
    return custom_symbol(
        "DROK_Buck_5pin", "RoomCleaner:DROK_Buck_5pin_Header",
        "https://www.droking.com/10pcs-dc-buck-converter-5v-voltage-regulator",
        "DROK buck converter module 5-pin header",
        "DROK buck module on a 5-pin single-row header: OUT+, OUT-, IN-, IN+, EN (header order). "
        "Non-isolated (IN- = OUT-). Exact revision unverified.",
        "DROK*", (0, 12.7), (0, -17.78), (-10.16, 10.16, 10.16, -10.16), pins, body_text)


def custom_library_text():
    return ('(kicad_symbol_lib (version 20220914) (generator build_kicad)\n'
            + xiao_symbol_text() + drok_symbol_text() + ')\n')


# ---------------------------------------------------------------------------
# custom footprints (RoomCleaner.pretty)
# ---------------------------------------------------------------------------
def fp_header(name, descr, tags):
    return (f'(footprint {q(name)} (version 20221018) (generator build_kicad)\n  (layer "F.Cu")\n'
            f'  (descr {q(descr)})\n  (tags {q(tags)})\n  (attr through_hole)\n')


def fp_line(x1, y1, x2, y2, layer, w):
    return (f'  (fp_line (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) '
            f'(stroke (width {w}) (type solid)) (layer {q(layer)}))\n')


def fp_rect_lines(x1, y1, x2, y2, layer, w):
    return (fp_line(x1, y1, x2, y1, layer, w) + fp_line(x2, y1, x2, y2, layer, w) +
            fp_line(x2, y2, x1, y2, layer, w) + fp_line(x1, y2, x1, y1, layer, w))


def fp_text(kind, text, x, y, layer):
    return (f'  (fp_text {kind} {q(text)} (at {fmt(x)} {fmt(y)}) (layer {q(layer)})\n'
            f'    (effects (font (size 1 1) (thickness 0.15)))\n  )\n')


def fp_pad(num, x, y, shape, size=1.7, drill=1.0):
    return (f'  (pad {q(num)} thru_hole {shape} (at {fmt(x)} {fmt(y)}) (size {size} {size}) (drill {drill}) '
            f'(layers "*.Cu" "*.Mask"))\n')


def xiao_footprint():
    """Seeed XIAO ESP32-C3 on two 2.54 mm headers, rows 15.24 mm apart.
    Origin = pad 1 (D0). Bottom row (y = 0): pads 1..7 = D0..D6.  Top row (y = -15.24):
    pads 14..8 = 5V, GND, 3V3, D10, D9, D8, D7 (so pad 14 sits above pad 1).  USB-C end = -x."""
    s = fp_header("XIAO_ESP32C3_THT",
                  "Seeed XIAO ESP32-C3 on 2 x 7 pin 2.54 mm headers, 15.24 mm row spacing, USB-C on the pad-1 end. "
                  "Outline is approximate (21 x 17.8 mm).", "XIAO ESP32C3 module header")
    s += fp_text("reference", "REF**", 7.62, -18.4, "F.SilkS")
    s += fp_text("value", "XIAO_ESP32C3_THT", 7.62, 3.4, "F.Fab")
    s += fp_text("user", "${REFERENCE}", 7.62, -7.62, "F.Fab")
    y0, y1 = -15.24 - 1.28, 1.28          # body edges: 17.8 mm wide, centred on the pin rows
    x0, x1 = -2.88, 15.24 + 2.88          # 21.0 mm long, centred on the pin array
    s += fp_rect_lines(x0, y0, x1, y1, "F.SilkS", 0.12)
    s += fp_rect_lines(x0 - 1.5, -11.7, x0, -3.5, "F.SilkS", 0.12)          # USB-C shell
    s += fp_text("user", "USB", x0 - 0.75, -7.62, "F.Fab")
    s += fp_rect_lines(-4.65, -16.64, x1 + 0.0, 1.4, "F.CrtYd", 0.05)
    for k in range(7):
        s += fp_pad(str(k + 1), 2.54 * k, 0, "rect" if k == 0 else "oval")
    for k in range(7):
        s += fp_pad(str(14 - k), 2.54 * k, -15.24, "oval")
    return s + ")\n"


def drok_footprint():
    """DROK buck module standing on a 5-pin single-row header.  Origin = pad 1 (OUT+);
    pads run toward -x so that, unrotated, they read OUT+, OUT-, IN-, IN+, EN right-to-left
    exactly as on the perfboard (X15 .. T15).  The module body is NOT modelled."""
    s = fp_header("DROK_Buck_5pin_Header",
                  "DROK buck module on a 5-pin 2.54 mm single-row header (OUT+, OUT-, IN-, IN+, EN). "
                  "Pads run toward -x. Module stands upright; body not modelled.", "DROK buck header 5 pin")
    s += fp_text("reference", "REF**", -5.08, -2.9, "F.SilkS")
    s += fp_text("value", "DROK_Buck_5pin_Header", -5.08, 2.9, "F.Fab")
    s += fp_text("user", "${REFERENCE}", -5.08, 0, "F.Fab")
    s += fp_rect_lines(-11.43, -1.27, 1.27, 1.27, "F.SilkS", 0.12)
    s += fp_rect_lines(-11.43, -1.27, 1.27, 1.27, "F.CrtYd", 0.05)
    for k in range(5):
        s += fp_pad(str(k + 1), -2.54 * k, 0, "rect" if k == 0 else "oval")
    return s + ")\n"


# ---------------------------------------------------------------------------
# parts: lib symbol, footprint, value, placement
# ---------------------------------------------------------------------------
FP = {
    "U1": "RoomCleaner:DROK_Buck_5pin_Header",
    "U2": "RoomCleaner:XIAO_ESP32C3_THT",
    "U3": "Module:Pololu_Breakout-16_15.2x20.3mm",
    "J1": "TerminalBlock:TerminalBlock_bornier-2_P5.08mm",
    "J2": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
    "J5": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
    "J3": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    "JP1": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    "D1": "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
    "C1": "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm",
    "R1": "Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P7.62mm_Horizontal",
    "R2": "Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P2.54mm_Vertical",
    "R3": "Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P2.54mm_Vertical",
    "R4": "Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P7.62mm_Horizontal",
}
VALUE = {
    "U1": "DROK_buck_5.00V", "U2": "XIAO_ESP32C3", "U3": "A4988_carrier",
    "J1": "12V_IN", "J2": "MOTOR_NEMA17", "J5": "ENCODER_AS5600", "J3": "SWITCH_KW12-3",
    "JP1": "USB_EXT_5V_LINK", "D1": "1N5819", "C1": "100\u00b5F/50V",
    "R1": "10k", "R2": "10k", "R3": "10k", "R4": "10k",
}
POWER_NETS = {"+12V": "+12V", "+3V3": "+3V3", "+5V": "+5V", "GND": "GND"}


# ---------------------------------------------------------------------------
# schematic writer
# ---------------------------------------------------------------------------
class Sheet:
    def __init__(self, pb):
        self.pb = pb
        self.root_uuid = str(uuid.uuid5(NS, "root"))
        self.libs = {}            # lib_id -> LibSymbol
        self.items = []           # text blocks
        self.n = 0
        self.pwr_n = 0
        self.flg_n = 0
        self.placed = {}
        self.warnings = []

    # -- ids ---------------------------------------------------------------
    def uid(self, kind=""):
        self.n += 1
        return str(uuid.uuid5(NS, f"{kind}-{self.n}"))

    def lib(self, nick, name):
        key = f"{nick}:{name}"
        if key not in self.libs:
            if nick == "RoomCleaner":
                text = extract_symbol_from_text(custom_library_text(), name)
                self.libs[key] = LibSymbol(nick, name, text)
            else:
                self.libs[key] = stock(nick, name)
        return self.libs[key]

    # -- primitives -------------------------------------------------------------
    def wire(self, p, r):
        if abs(p[0] - r[0]) < 1e-6 and abs(p[1] - r[1]) < 1e-6:
            return
        self.items.append(f'  (wire (pts (xy {fmt(p[0])} {fmt(p[1])}) (xy {fmt(r[0])} {fmt(r[1])}))\n'
                          f'    (stroke (width 0) (type default))\n    (uuid {self.uid("wire")})\n  )\n')

    def path(self, pts):
        for a, b in zip(pts, pts[1:]):
            self.wire(a, b)

    def junction(self, p):
        self.items.append(f'  (junction (at {fmt(p[0])} {fmt(p[1])}) (diameter 0) (color 0 0 0 0)\n'
                          f'    (uuid {self.uid("junction")})\n  )\n')

    def no_connect(self, p):
        self.items.append(f'  (no_connect (at {fmt(p[0])} {fmt(p[1])}) (uuid {self.uid("nc")}))\n')

    def label(self, p, name, ang=0):
        just = "left bottom" if ang in (0, 90) else "right bottom"
        self.items.append(f'  (label {q(name)} (at {fmt(p[0])} {fmt(p[1])} {ang}) (fields_autoplaced)\n'
                          f'    (effects (font (size 1.27 1.27)) (justify {just}))\n'
                          f'    (uuid {self.uid("label")})\n  )\n')

    def text(self, p, s, size=1.27, bold=False, just="left top", ang=0):
        font = f'(font (size {size} {size}){" bold" if bold else ""})'
        self.items.append(f'  (text {q(s)} (at {fmt(p[0])} {fmt(p[1])} {ang})\n'
                          f'    (effects {font} (justify {just}))\n    (uuid {self.uid("text")})\n  )\n')

    def rect(self, a, b, dash=True, width=0.254):
        self.items.append(f'  (rectangle (start {fmt(a[0])} {fmt(a[1])}) (end {fmt(b[0])} {fmt(b[1])})\n'
                          f'    (stroke (width {width}) (type {"dash" if dash else "default"}))\n'
                          f'    (fill (type none))\n    (uuid {self.uid("rect")})\n  )\n')

    # -- symbols ----------------------------------------------------------------
    def place(self, lib, at, rot=0, ref=None, value=None, footprint="", fields=None, power=False):
        """Place a symbol. `fields` overrides {'Reference'/'Value': (dx, dy, justify)} in sheet mm."""
        at = (snap(at[0]), snap(at[1]))
        p = Placed(self, lib, at, rot, ref, value, footprint, fields or {}, power)
        self.items.append(p.sexpr())
        if ref and not ref.startswith("#"):
            self.placed[ref] = p
        return p

    def power_symbol(self, net, at, rot=0):
        name = {"+12V": "+12V", "+3V3": "+3V3", "+5V": "+5V", "GND": "GND"}[net]
        self.pwr_n += 1
        return self.place(self.lib("power", name), at, rot, ref=f"#PWR{self.pwr_n:02d}", value=name, power=True)

    def pwr_flag(self, at, rot=0):
        self.flg_n += 1
        return self.place(self.lib("power", "PWR_FLAG"), at, rot, ref=f"#FLG{self.flg_n:02d}", value="PWR_FLAG",
                          power=True)

    # -- routing a pin out to a label / power symbol ----------------------------
    def net_of(self, ref, pin):
        net = self.pb.pin_net[(ref, pin)]
        return None if net is None else pbd.net_name(net)

    def route(self, ref, pin, steps=None, terminal="auto"):
        """Wire from `ref` pin along `steps` ((dx, dy) in mm), then end in a label or a power symbol."""
        p = self.placed[ref]
        net = self.net_of(ref, pin)
        start = p.pin_xy(pin)
        if net is None:
            self.no_connect(start)
            return start, None
        if steps is None:
            ox, oy = p.pin_out(pin)
            steps = [(5.08 * ox, 5.08 * oy)]
        pts = [start]
        for dx, dy in steps:
            pts.append((round(pts[-1][0] + dx, 2), round(pts[-1][1] + dy, 2)))
        self.path(pts)
        end = pts[-1]
        if terminal == "none":
            return end, net
        if net in POWER_NETS:
            self.power_symbol(net, end)
        else:
            if len(pts) > 1:
                dx, dy = pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1]
            else:
                dx, dy = p.pin_out(pin)
            if abs(dy) > abs(dx):
                self.warnings.append(f"{ref}.{pin}: label {net} ends on a vertical stub")
                ang = 90 if dy < 0 else 270
            else:
                ang = 0 if dx > 0 else 180
            self.label(end, net, ang)
        return end, net


def extract_symbol_from_text(text, name):
    i = text.index(f'(symbol "{name}"')
    depth, j, instr = 0, i, False
    while True:
        ch = text[j]
        if ch == '"' and text[j - 1] != "\\":
            instr = not instr
        elif not instr:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
        j += 1
    return text[i:j + 1]


def rot_xy(px, py, rot):
    """Library offset (y up) -> sheet offset (y down) for a symbol rotated by rot (0/90/180/270 CCW)."""
    c, s = round(math.cos(math.radians(rot))), round(math.sin(math.radians(rot)))
    rx, ry = px * c - py * s, px * s + py * c
    return rx, -ry


class Placed:
    def __init__(self, sheet, lib, at, rot, ref, value, footprint, fields, power):
        self.sheet, self.lib, self.at, self.rot = sheet, lib, at, rot
        self.ref, self.value, self.footprint, self.fields, self.power = ref, value, footprint, fields, power
        self.uuid = sheet.uid("symbol")

    def pin_xy(self, num):
        pn = self.lib.pins[num]
        dx, dy = rot_xy(pn["x"], pn["y"], self.rot)
        return (round(self.at[0] + dx, 2), round(self.at[1] + dy, 2))

    def pin_out(self, num):
        """Unit vector (sheet coords) pointing from the pin's connection point away from the body."""
        a = (self.lib.pins[num]["ang"] + self.rot) % 360
        return {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[int(a)]

    def _prop(self, name, value):
        info = self.lib.props.get(name, dict(x=0, y=0, ang=0, justify=[], hide=True))
        hide = info["hide"] or name in ("Footprint", "Datasheet")
        if name in self.fields:
            dx, dy, just = self.fields[name]
            x, y = self.at[0] + dx, self.at[1] + dy
            justify = [] if just in ("", "center") else just.split()
        else:
            dx, dy = rot_xy(info["x"], info["y"], self.rot)
            x, y = self.at[0] + dx, self.at[1] + dy
            justify = list(info["justify"])
            if self.rot == 180:
                swap = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}
                justify = [swap.get(j, j) for j in justify]
        ang = int(info["ang"]) % 180
        eff = "(effects (font (size 1.27 1.27))" + (f' (justify {" ".join(justify)})' if justify else "") + \
              (" hide" if hide else "") + ")"
        return f'    (property {q(name)} {q(value)} (at {fmt(x)} {fmt(y)} {ang})\n      {eff}\n    )\n'

    def sexpr(self):
        s = (f'  (symbol (lib_id {q(self.lib.lib_id)}) (at {fmt(self.at[0])} {fmt(self.at[1])} {self.rot}) (unit 1)\n'
             f'    (in_bom yes) (on_board yes) (dnp no)\n    (uuid {self.uuid})\n')
        s += self._prop("Reference", self.ref)
        s += self._prop("Value", self.value if self.value is not None else self.lib.props["Value"]["value"])
        s += self._prop("Footprint", self.footprint)
        s += self._prop("Datasheet", self.lib.props.get("Datasheet", {}).get("value", "~") if not self.power else "")
        for num in sorted(self.lib.pins, key=lambda k: (len(k), k)):
            s += f'    (pin {q(num)} (uuid {self.sheet.uid("pin")}))\n'
        s += (f'    (instances\n      (project {q(PROJECT)}\n        (path "/{self.sheet.root_uuid}"\n'
              f'          (reference {q(self.ref)}) (unit 1)\n        )\n      )\n    )\n  )\n')
        return s


# ---------------------------------------------------------------------------
# sheet content
# ---------------------------------------------------------------------------
def build_sheet(pb):
    sh = Sheet(pb)
    L = sh.lib
    R_, C_, D_ = L("Device", "R"), L("Device", "C_Polarized"), L("Device", "D_Schottky")
    JP_ = L("Jumper", "Jumper_2_Open")
    C2, C4 = L("Connector_Generic", "Conn_01x02"), L("Connector_Generic", "Conn_01x04")
    A4988 = L("Driver_Motor", "Pololu_Breakout_A4988")
    XIAO, DROK = L("RoomCleaner", "XIAO_ESP32C3"), L("RoomCleaner", "DROK_Buck_5pin")
    for pwr in ("+12V", "+3V3", "+5V", "GND", "PWR_FLAG"):
        L("power", pwr)

    # sanity: the schematic pin names behind the hole map really are what the perfboard labels say
    for hole, (ref, pin) in pb.hole_pin.items():
        label = pb.PINS[hole][1]
        if ref == "U2" and XIAO.pins[pin]["name"] != label:
            raise SystemExit(f"U2 pin {pin} is {XIAO.pins[pin]['name']} but perfboard {hole} says {label}")
        if ref == "U3":
            want = pbd.A4988_NAME.get(label, label)
            if A4988.pins[pin]["name"] != want:
                raise SystemExit(f"U3 pin {pin} is {A4988.pins[pin]['name']} but perfboard {hole} says {label}")

    def part(lib, ref, at, rot=0, fields=None):
        return sh.place(lib, at, rot, ref=ref, value=VALUE[ref], footprint=FP[ref], fields=fields)

    # ---- frame / headings --------------------------------------------------
    sh.text((15.24, 17.78), "RoomCleaner winch station \u2014 Rev D, as soldered on the 5 x 7 cm perfboard",
            size=2.54, bold=True)
    sh.text((15.24, 24.13), "Net labels and power symbols carry the perfboard net names; every connection below is "
            "generated from perfboard_layout.py (PINS / BARE / WIRES / NETMAP). Same name = same net.", size=1.27)

    # ====================== POWER =========================================
    sh.text((15.24, 33.02), "POWER: 12 V in, buck to 5 V, D1, JP1 link to the XIAO 5V pin", size=1.8, bold=True)
    part(C2, "J1", (45.72, 50.8), fields={"Reference": (0, -3.81, "left"), "Value": (0, 6.35, "left")})
    sh.route("J1", "1", [(-5.08, 0), (-7.62, 0)])
    sh.route("J1", "2", [(-5.08, 0), (-7.62, 0)])
    sh.pwr_flag((35.56, 50.8))
    sh.pwr_flag((35.56, 53.34), rot=180)

    part(C_, "C1", (66.04, 55.88), fields={"Reference": (1.27, -2.54, "left"), "Value": (1.27, 2.54, "left")})
    sh.route("C1", "1", [(0, -5.08)])
    sh.route("C1", "2", [(0, 5.08)])
    sh.text((15.24, 73.66), "J1: pin 1 +12 V, pin 2 GND (perfboard X01, X03,\n"
            "5.08 mm terminal or wires).  12 V comes from the\n"
            "supply branch; the PWR_FLAGs mark J1 as the source.\n"
            "C1 sits at VMOT (perfboard T02 +, T03 -).", size=1.27)

    u1 = part(DROK, "U1", (110.49, 53.34), fields={"Reference": (0, -15.24, "center"), "Value": (0, 17.78, "center")})
    sh.route("U1", "4", [(-5.08, 0)])                 # IN+  -> +12V
    sh.route("U1", "3", [(-5.08, 0)])                 # IN-  -> GND
    sh.route("U1", "2", [(5.08, 0)])                  # OUT- -> GND
    sh.route("U1", "5", [])                           # EN   -> no connect
    d1 = part(D_, "D1", (149.86, 48.26), rot=180, fields={"Reference": (0, -3.81, "center"),
                                                          "Value": (0, 3.81, "center")})
    jp1 = part(JP_, "JP1", (176.53, 48.26), fields={"Reference": (0, -3.81, "center"), "Value": (0, 3.81, "center")})
    # buck OUT+ -> D1 anode (net 5VB), D1 cathode -> JP1 pin 1 (net 5VD), JP1 pin 2 -> +5V
    p_out = u1.pin_xy("1")
    p_a, p_k = d1.pin_xy("2"), d1.pin_xy("1")
    p_j1, p_j2 = jp1.pin_xy("1"), jp1.pin_xy("2")
    net_5vb, net_5vd = sh.net_of("U1", "1"), sh.net_of("D1", "1")
    assert net_5vb == sh.net_of("D1", "2") and net_5vd == sh.net_of("JP1", "1")
    mid = (snap((p_out[0] + p_a[0]) / 2), p_out[1])
    sh.path([p_out, mid, p_a])
    sh.label(mid, net_5vb, 0)
    mid2 = (snap((p_k[0] + p_j1[0]) / 2), p_k[1])
    sh.path([p_k, mid2, p_j1])
    sh.label(mid2, net_5vd, 0)
    sh.route("JP1", "2", [(7.62, 0), (10.16, 0)])     # -> +5V
    sh.pwr_flag((p_j2[0] + 7.62, p_j2[1]))
    sh.text((92.71, 76.2), "U1 EN is unconnected (as soldered).  Select 5 V with the\n"
            "module's 5V pad; set and check 5.00 V BEFORE connecting\nloads.  Non-isolated: IN- = OUT-.", size=1.27)
    sh.text((137.16, 62.23), "D1 1N5819, stripe (cathode)\ntoward the XIAO. Blocks back-\n"
            "feed into the buck; not an\nover-voltage clamp.", size=1.27)
    sh.text((172.72, 62.23), "JP1: OPEN while USB is plugged in.\nCLOSED standalone from 12 V.\n"
            "Change only with all power off.", size=1.27)
    sh.text((172.72, 76.2), "PWR_FLAG on +5V: 5 V comes from USB VBUS or from\nthe buck through D1 + JP1 (never both at once).",
            size=1.27)

    # ====================== CONTROL ====================================
    sh.text((15.24, 91.44), "CONTROL: XIAO ESP32-C3, A4988 carrier, pull resistors, motor", size=1.8, bold=True)
    u2 = part(XIAO, "U2", (63.5, 142.24), fields={"Reference": (-6.35, -30.48, "left"),
                                                   "Value": (-6.35, -27.94, "left")})
    sh.text((26.67, 97.79), "U2 perfboard: top row B03-H03, bottom row B09-H09,\nUSB-C points LEFT off the board edge.",
            size=1.27)
    # left column D0..D6 = pins 1..7 ; right column pins 14..8
    route_left = {"1": None, "2": [(-7.62, 0)], "3": [(-7.62, 0)], "4": [(-7.62, 0)], "5": [(-7.62, 0)],
                  "6": [(-7.62, 0)], "7": None}
    for pin, steps in route_left.items():
        sh.route("U2", pin, steps if steps else [])
    sh.route("U2", "14", [(7.62, 0)])                 # 5V   -> +5V
    sh.route("U2", "13", [(15.24, 0)])                # GND
    sh.route("U2", "12", [(7.62, 0)])                 # 3V3
    sh.route("U2", "11", [(7.62, 0)])                 # D10 -> HOME
    for pin in ("10", "9", "8"):                      # D9 D8 D7 unused
        sh.route("U2", pin, [])

    # pull resistors
    rx = [111.76, 127.0, 142.24, 157.48]
    ry = 142.24
    for ref, x in zip(("R1", "R2", "R3", "R4"), rx):
        part(R_, ref, (x, ry))
    sh.route("R1", "1", [(0, -5.08)])                 # +3V3
    sh.route("R1", "2", [(0, 2.54), (5.08, 0)])       # EN
    sh.route("R2", "1", [(0, -2.54), (5.08, 0)])      # STEP
    sh.route("R2", "2", [(0, 5.08)])                  # GND
    sh.route("R3", "1", [(0, -2.54), (5.08, 0)])      # DIR
    sh.route("R3", "2", [(0, 5.08)])                  # GND
    sh.route("R4", "1", [(0, -5.08)])                 # +3V3
    sh.route("R4", "2", [(0, 2.54), (5.08, 0)])       # HOME
    sh.text((101.6, 162.56), "R1 10k: holds EN high (A4988 disabled) at boot.\n"
            "R2 / R3 10k: hold STEP / DIR low at boot.\nR4 10k: HOME pull-up to 3V3 (switch is NC to GND).", size=1.27)

    # A4988 carrier
    u3 = part(A4988, "U3", (215.9, 142.24), fields={"Reference": (17.78, -19.05, "left"),
                                                    "Value": (17.78, -16.51, "left")})
    pad = {n: u3.pin_xy(n) for n in u3.lib.pins}
    sh.route("U3", "9", [(-7.62, 0)])                 # ENABLE -> EN
    sh.route("U3", "15", [(-7.62, 0)])                # STEP
    sh.route("U3", "16", [(-7.62, 0)])                # DIR
    # RESET + SLEEP bus to +3V3
    bx = pad["13"][0] - 7.62
    sh.route("U3", "13", [(-7.62, 0)], terminal="none")
    sh.route("U3", "14", [(-7.62, 0)], terminal="none")
    sh.path([(bx, pad["14"][1]), (bx, pad["13"][1]), (bx, pad["13"][1] - 5.08)])
    sh.junction((bx, pad["13"][1]))
    sh.power_symbol(sh.net_of("U3", "13"), (bx, pad["13"][1] - 5.08))
    # MS1..MS3 bus to GND
    for n in ("10", "11", "12"):
        sh.route("U3", n, [(-7.62, 0)], terminal="none")
    sh.path([(bx, pad["10"][1]), (bx, pad["11"][1]), (bx, pad["12"][1]), (bx, pad["12"][1] + 2.54)])
    sh.junction((bx, pad["11"][1]))
    sh.junction((bx, pad["12"][1]))
    sh.power_symbol(sh.net_of("U3", "10"), (bx, pad["12"][1] + 2.54))
    sh.route("U3", "2", [(0, -5.08)])                 # VDD  -> +3V3
    sh.route("U3", "8", [(0, -7.62)])                 # VMOT -> +12V
    sh.route("U3", "1", [(0, 5.08)])                  # GND (logic side, pad 1)
    sh.route("U3", "7", [(0, 5.08)])                  # GND (motor return, pad 7)
    for n in ("3", "4", "5", "6"):                    # 1B 1A 2A 2B
        sh.route("U3", n, [(5.08, 0)])
    sh.text((173.99, 168.91), "MS1 MS2 MS3 all LOW = FULL STEP\n(config `microsteps` = 1).", size=1.27)
    sh.text((201.93, 175.26), "U3 perfboard: pads 9-16 in column L (rows 03-10),\n"
            "pads 8-1 in column Q (rows 03-10), chip + pot UP.\n"
            "Pad 7 GND = motor return (PGND on the board), pad 1 GND =\n"
            "logic ground; the board ties them with wire S03-O11.", size=1.27)

    # J2 motor
    part(C4, "J2", (279.4, 142.24), fields={"Reference": (0, -5.08, "left"), "Value": (0, 7.62, "left")})
    for n in ("1", "2", "3", "4"):
        sh.route("J2", n, [(-5.08, 0)])
    sh.text((270.51, 157.48), "J2 MOTOR (X05-X08): pins 1-4 =\n2B 2A 1A 1B.  1A/1B = coil 1,\n2A/2B = coil 2.\n"
            "Never plug / unplug the motor\nwith power on.", size=1.27)

    # ====================== OFF-BOARD ================================
    sh.text((15.24, 198.12), "OFF-BOARD PARTS (connectors on the perfboard, device is not)", size=1.8, bold=True)
    part(C4, "J5", (63.5, 218.44), fields={"Reference": (0, -5.08, "left"), "Value": (0, 7.62, "left")})
    sh.route("J5", "1", [(-7.62, 0), (0, -5.08)])     # 3V3
    sh.route("J5", "2", [(-12.7, 0)])                 # GND
    sh.route("J5", "3", [(-2.54, 0)])                 # SDA
    sh.route("J5", "4", [(-2.54, 0)])                 # SCL
    sh.rect((71.12, 207.0), (160.02, 234.0))
    sh.text((72.39, 208.28), "AS5600 ENCODER BOARD (off-board), J5 C17-F17\n"
            "J5 pins: 1 = VCC (3.3 V), 2 = GND, 3 = SDA, 4 = SCL. 0x36, I2C 400 kHz.\n"
            "Encoder-board DIR strapped to GND and OUT/PGO open: on that board, NOT on J5.\n"
            "Pull-ups to 3.3 V only; set any 3.3 V / 5 V pad to 3.3 V. Never 5 V on ESP32 pins.\n"
            "Magnet: diametric disc on the spool axis, 0.5-3 mm above the chip, centred.\n"
            "Keep SDA/SCL/3V3/GND < 20 cm, twisted, away from motor wires.", size=1.27)

    part(C2, "J3", (63.5, 254.0), fields={"Reference": (0, -3.81, "left"), "Value": (0, 6.35, "left")})
    sh.route("J3", "1", [(-5.08, 0)])                 # HOME
    sh.route("J3", "2", [(-5.08, 0)])                 # GND
    sh.rect((71.12, 245.0), (160.02, 266.0))
    sh.text((72.39, 246.28), "S1 KW12-3 SWITCH (off-board), J3 H17-I17\n"
            "J3 pin 1 = NC contact -> HOME (D10 / GPIO10), pin 2 = COM -> GND. NO unused.\n"
            "NC closed at rest; firmware INPUT_PULLUP + R4 10k to 3V3.\n"
            "Open wire reads STOP, a short to GND can read READY: test both states.", size=1.27)

    # ====================== NOTES (right column / lower middle) ===========
    nx = 172.72
    sh.rect((nx - 2.54, 196.0), (297.18, 252.0), dash=False, width=0.254)
    sh.text((nx, 197.28),
            "A4988 CURRENT LIMIT - DECISIONS.md D30 (2026-10-21)\n"
            "Vref = 0.85 V  (about 1.06 A, at the carrier's maximum).  Vref = 8 x I x Rsense, R100 = 0.100 ohm.\n"
            "Supersedes D29 / Rev D README (1.35 A, 1.08 V): 1.08 V is NOT reachable on this carrier\n"
            "(red R100 clones top out at ~0.79-0.85 V Vref on 3.3 V logic). VDD stays 3.3 V.\n"
            "Set Vref with 12 V on, motor DISCONNECTED, logic powered, EN high: black probe on driver GND,\n"
            "red on the trim pot. Read both sense resistors first. Heatsink stays on; 60 min hold test.",
            size=1.27, bold=False)
    sh.text((nx, 219.0),
            "MICROSTEP (MS1/MS2/MS3): all three tied LOW (GND) = FULL STEP -> config `microsteps` = 1\n"
            "(config/robot.example.json). If they are moved to +3V3 (1/16 step) set `microsteps` = 16 for\n"
            "that station before the first run. Hardware and config MUST match: mismatch = wrong lengths.",
            size=1.27)
    sh.text((nx, 232.0),
            "DO NOT RAISE VDD TO 5 V. A4988 VDD, RESET, SLEEP = 3.3 V from the XIAO 3V3 pin; the ESP32-C3\n"
            "GPIOs (STEP, DIR, EN) are not 5 V tolerant.  Pull-ups to 3.3 V only.",
            size=1.27)
    sh.text((nx, 240.0),
            "FUSING IS AT THE SUPPLY END: branch fuses F1-F4 (rating TBD) and F0 7.5 A (existing, recorded,\n"
            "not approved) sit before the long cables. No fuse, reverse-polarity or over-voltage protection\n"
            "on this board. Rev D TP0-TP4 are not parts on the perfboard: probe the module pins / holes.",
            size=1.27)

    # right-hand column: power-up + hole map
    rx0 = 304.8
    sh.text((rx0, 17.78), "POWER-UP SEQUENCE (summary of Rev D sheet 5)", size=1.8, bold=True)
    sh.text((rx0, 22.86),
            "1. Remove USB and 12 V; let C1 discharge; do not short it with a tool.\n"
            "2. Check the board against this netlist with a meter: both A4988 GND\n"
            "   pads to J1-2; 12V, +3V3, 5VB/5VD/+5V each free of shorts to GND.\n"
            "3. Test the supply and the buck alone; set 5.00 V at U1 OUT+ (net 5VB)\n"
            "   BEFORE connecting any load. JP1 OPEN.\n"
            "4. Add XIAO, then A4988, one at a time; power off between changes.\n"
            "5. 12 V on, EN high, motor disconnected: check +3V3 and set Vref\n"
            "   0.85 V (D30). Never guess Vref from the screw direction.\n"
            "6. Power off; connect the coil pairs (1A/1B, 2A/2B). Never plug or\n"
            "   unplug the motor with power on.\n"
            "7. Run only a short, unloaded jog and the switch test. No suspended\n"
            "   load or room operation until bench-checked.",
            size=1.27)
    sh.text((rx0, 76.2), "USB / EXTERNAL POWER", size=1.8, bold=True)
    sh.text((rx0, 81.28),
            "USB plugged in: JP1 OPEN.  Standalone from 12 V: USB unplugged,\n"
            "JP1 CLOSED.  Never USB + 12 V with JP1 closed (two sources meet\n"
            "on VBUS).  Change JP1 only with all power off.", size=1.27)
    sh.text((rx0, 94.0), "PERFBOARD HOLE MAP (generated, component side, A01 top-left)", size=1.8, bold=True)
    sh.text((rx0, 99.06), hole_map_text(pb), size=1.27)
    sh.text((rx0, 140.0), "DIFFERENCES FROM THE REV D SCHEMATIC (perfboard wins)", size=1.8, bold=True)
    sh.text((rx0, 145.0),
            "Current limit: Rev D sheet 3 / README show 1.35 A, Vref 1.08 V (D29).\n"
            "  This sheet follows D30: Vref 0.85 V, about 1.06 A.\n"
            "Encoder: Rev D sheet 3 draws DIR to GND and OUT open at the encoder.\n"
            "  The board has a 4-pin J5 only (3V3, GND, SDA, SCL), so those two\n"
            "  are on the encoder board, not on the perfboard.\n"
            "Test points TP0-TP4 of Rev D are not parts on the perfboard.\n"
            "Grounds: Rev D shows one GND; the board has two A4988 GND pads (pad 7\n"
            "  motor return, pad 1 logic) tied by wire S03-O11 = one GND net here.\n"
            "Packages as built: R2/R3 stand upright (2.54 mm), R1/R4 lie (7.62 mm);\n"
            "  J1 is a 5.08 mm terminal pitch (2.54 mm header otherwise).\n"
            "Net names: perfboard 3V3 / 5V / 12V are the +3V3 / +5V / +12V power\n"
            "  symbols; 5VB = buck OUT+ / D1 anode, 5VD = D1 cathode / JP1.", size=1.27)
    return sh


def hole_map_text(pb):
    lines = []
    ph = lambda ref: pb.pin_hole(ref)
    for ref in ("J1", "J2", "J5", "J3", "JP1", "C1", "D1", "U1"):
        h = ph(ref)
        lines.append(f"{ref}: " + "  ".join(f"{p}={h[p]}" for p in sorted(h, key=int)))
    for ref in ("R1", "R2", "R3", "R4"):
        h = ph(ref)
        lines.append(f"{ref}: {h['1']} - {h['2']}")
    u2 = sorted(pb.holes_of("U2"), key=lambda x: (x[1:], x[0]))
    lines.append(f"U2: {u2[0]}..{u2[6]} (5V..D7) and {u2[7]}..{u2[13]} (D0..D6)")
    u3 = pb.holes_of("U3")
    lines.append(f"U3: L03..L10 (pads 9..16) and Q03..Q10 (pads 8..1)")
    lines.append("")
    lines.append("Pin 1 = first hole listed.  U1 EN (T15) and XIAO D0, D6, D7,")
    lines.append("D8, D9 are unconnected on the board (no-connect flags).")
    return "\n".join(lines)


def schematic_text(sh):
    s = ('(kicad_sch (version 20230121) (generator build_kicad)\n\n'
         f'  (uuid {sh.root_uuid})\n\n  (paper "A3")\n\n'
         f'  (title_block\n    (title {q(TITLE)})\n    (date "{DATE}")\n    (rev "D")\n'
         '    (company "RoomCleaner")\n'
         '    (comment 1 "Generated by build_kicad.py from perfboard_layout.py; DECISIONS.md D30 current limit")\n'
         '    (comment 2 "Net labels = perfboard nets; PGND and GND are one net (tied by wire S03-O11)")\n  )\n\n')
    s += '  (lib_symbols\n'
    for key in sorted(sh.libs):
        s += "".join("    " + ln + "\n" for ln in sh.libs[key].text.splitlines())
    s += '  )\n\n'
    s += "".join(sh.items)
    s += '\n  (sheet_instances\n    (path "/" (page "1"))\n  )\n)\n'
    return s


# ---------------------------------------------------------------------------
# project files
# ---------------------------------------------------------------------------
STOCK_SYM_LIBS = ["Device", "Driver_Motor", "Connector_Generic", "Jumper", "power"]
STOCK_FP_LIBS = ["Capacitor_THT", "Connector_PinHeader_2.54mm", "Diode_THT", "Module", "Resistor_THT",
                 "TerminalBlock"]


def write_libtables():
    st = '(sym_lib_table\n  (version 7)\n'
    for n in STOCK_SYM_LIBS:
        st += (f'  (lib (name {q(n)})(type "KiCad")(uri "${{KICAD7_SYMBOL_DIR}}/{n}.kicad_sym")'
               f'(options "")(descr "KiCad stock library"))\n')
    st += ('  (lib (name "RoomCleaner")(type "KiCad")(uri "${KIPRJMOD}/RoomCleaner.kicad_sym")(options "")'
           '(descr "RoomCleaner station Rev D: XIAO ESP32-C3, DROK buck"))\n)\n')
    (HERE / "sym-lib-table").write_text(st, encoding="utf-8")
    ft = '(fp_lib_table\n  (version 7)\n'
    for n in STOCK_FP_LIBS:
        ft += (f'  (lib (name {q(n)})(type "KiCad")(uri "${{KICAD7_FOOTPRINT_DIR}}/{n}.pretty")'
               f'(options "")(descr "KiCad stock library"))\n')
    ft += ('  (lib (name "RoomCleaner")(type "KiCad")(uri "${KIPRJMOD}/RoomCleaner.pretty")(options "")'
           '(descr "RoomCleaner station Rev D: XIAO ESP32-C3, DROK buck"))\n)\n')
    (HERE / "fp-lib-table").write_text(ft, encoding="utf-8")


def write_project(sheet_uuid):
    pro = {
        "board": {"design_settings": {"rules": {"min_copper_edge_clearance": 0.0},
                                      "rule_severities": {}}},
        "meta": {"filename": f"{PROJECT}.kicad_pro", "version": 1},
        "net_settings": {"classes": [{"name": "Default", "clearance": 0.2, "track_width": 0.25,
                                      "via_diameter": 0.8, "via_drill": 0.4, "pcb_color": "rgba(0, 0, 0, 0.000)",
                                      "schematic_color": "rgba(0, 0, 0, 0.000)", "wire_width": 6,
                                      "bus_width": 12, "line_style": 0, "diff_pair_gap": 0.25,
                                      "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2,
                                      "microvia_diameter": 0.3, "microvia_drill": 0.1, "priority": 2147483647}],
                         "meta": {"version": 3}, "net_colors": None, "netclass_assignments": None,
                         "netclass_patterns": []},
        "schematic": {"meta": {"version": 1}, "drawing": {"default_line_thickness": 6.0,
                                                          "default_text_size": 50.0},
                      "legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [[sheet_uuid, ""]],
        "text_variables": {},
    }
    (HERE / f"{PROJECT}.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# exports
# ---------------------------------------------------------------------------
def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd))
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=HERE, **kw)
    if r.stdout.strip():
        print("   ", r.stdout.strip().replace("\n", "\n    "))
    if r.stderr.strip():
        print("   ", r.stderr.strip().replace("\n", "\n    "))
    if r.returncode != 0:
        raise SystemExit(f"command failed ({r.returncode})")


def export_all():
    sch = f"{PROJECT}.kicad_sch"
    run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o", f"{PROJECT}_netlist.xml", sch])
    run(["kicad-cli", "sch", "export", "pdf", "-o", f"{PROJECT}.pdf", sch])
    run(["pdftoppm", "-r", "110", "-png", "-singlefile", f"{PROJECT}.pdf", f"{PROJECT}_preview"])


# ---------------------------------------------------------------------------
# PCB (stretch): every footprint on its perfboard hole, nets from the netlist, no routing
# ---------------------------------------------------------------------------
BOARD_W_MM, BOARD_H_MM = 70.0, 50.0          # 5 x 7 cm perfboard, 24 columns x 18 rows
A01_ORIGIN_MM = (101.6, 76.2)                # absolute position of hole A01 (on the 2.54 grid)
MARGIN_X = (BOARD_W_MM - 23 * pbd.PITCH_MM) / 2
MARGIN_Y = (BOARD_H_MM - 17 * pbd.PITCH_MM) / 2


def build_pcb(pb):
    os.environ.setdefault("KICAD7_FOOTPRINT_DIR", str(FP_DIR))
    os.environ.setdefault("KICAD7_SYMBOL_DIR", str(SYM_DIR))
    try:
        import pcbnew
    except ImportError:
        print("pcbnew not importable here (run with /usr/bin/python3); PCB skipped")
        return None
    tree = ET.parse(HERE / f"{PROJECT}_netlist.xml")
    comps = {}
    for c in tree.getroot().find("components"):
        ts = c.find("tstamps")
        comps[c.get("ref")] = dict(value=c.findtext("value"), footprint=c.findtext("footprint"),
                                   tstamp=(ts.text or "").strip() if ts is not None else None)
    nets = {}
    for n in tree.getroot().find("nets"):
        nets[n.get("name")] = [(nd.get("ref"), nd.get("pin")) for nd in n.findall("node")]
    pad_net = {}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            pad_net[(ref, pin)] = name

    board = pcbnew.BOARD()
    mm = pcbnew.FromMM
    V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
    ox, oy = A01_ORIGIN_MM

    def hole_abs(hole):
        x, y = pbd.hole_xy(hole)
        return ox + x, oy + y

    # outline
    x0, y0 = ox - MARGIN_X, oy - MARGIN_Y
    x1, y1 = x0 + BOARD_W_MM, y0 + BOARD_H_MM
    for (a, b) in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(V(*a))
        seg.SetEnd(V(*b))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.1))
        board.Add(seg)

    netinfo = {}
    for name in sorted(nets):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni

    report = []
    for ref in sorted(comps):
        fpid = comps[ref]["footprint"]
        nick, name = fpid.split(":")
        lib_path = HERE / "RoomCleaner.pretty" if nick == "RoomCleaner" else FP_DIR / f"{nick}.pretty"
        fp = pcbnew.FootprintLoad(str(lib_path), name)
        if fp is None:
            raise SystemExit(f"footprint {fpid} not found")
        fp.SetReference(ref)
        fp.SetValue(comps[ref]["value"])
        fp.SetFPID(pcbnew.LIB_ID(nick, name))
        if comps[ref]["tstamp"]:
            fp.SetPath(pcbnew.KIID_PATH("/" + comps[ref]["tstamp"]))
        holes = pb.pin_hole(ref)
        board.Add(fp)
        # place: origin on the hole of pad 1, rotation solved so every pad lands on its own hole
        best = None
        for rot in (0, 90, 180, 270):
            fp.SetPosition(V(*hole_abs(holes["1"])))
            fp.SetOrientationDegrees(rot)
            err = 0.0
            for pad in fp.Pads():
                pin = pad.GetNumber()
                if pin not in holes:
                    err = 1e9
                    break
                hx, hy = hole_abs(holes[pin])
                p = pad.GetPosition()
                err = max(err, math.hypot(pcbnew.ToMM(p.x) - hx, pcbnew.ToMM(p.y) - hy))
            if best is None or err < best[0]:
                best = (err, rot)
        fp.SetPosition(V(*hole_abs(holes["1"])))
        fp.SetOrientationDegrees(best[1])
        report.append((ref, fpid, holes["1"], best[1], best[0]))
        if best[0] > 0.06:
            raise SystemExit(f"{ref}: pads do not land on perfboard holes (worst {best[0]:.3f} mm)")
        for pad in fp.Pads():
            name = pad_net.get((ref, pad.GetNumber()))
            if name:
                pad.SetNet(netinfo[name])
    title = board.GetTitleBlock()
    title.SetTitle(TITLE)
    title.SetDate(DATE)
    title.SetRevision("D")
    pcb_path = HERE / f"{PROJECT}.kicad_pcb"
    board.Save(str(pcb_path))
    print(f"wrote {pcb_path.name}: {len(report)} footprints, {len(nets)} nets")
    for r in report:
        print(f"   {r[0]:4s} {r[1]:62s} pad1@{r[2]} rot {r[3]:3d} worst pad error {r[4]:.3f} mm")
    return pcb_path


def run_drc(pb, pcb_path):
    import pcbnew
    board = pcbnew.LoadBoard(str(pcb_path))
    out = HERE / f"{PROJECT}_drc.rpt"
    ok = pcbnew.WriteDRCReport(board, str(out), pcbnew.EDA_UNITS_MILLIMETRES, True)
    print("DRC report:", out.name, "ok" if ok else "FAILED")


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--no-pcb", action="store_true")
    ap.add_argument("--no-drc", action="store_true")
    a = ap.parse_args()

    pb = pbd.Perfboard()
    print("perfboard:", pb.check_output, "|", len(pb.nets()), "connected nets,", len(pb.no_connects()), "nc pins")

    (HERE / "RoomCleaner.kicad_sym").write_text(custom_library_text(), encoding="utf-8")
    pretty = HERE / "RoomCleaner.pretty"
    pretty.mkdir(exist_ok=True)
    (pretty / "XIAO_ESP32C3_THT.kicad_mod").write_text(xiao_footprint(), encoding="utf-8")
    (pretty / "DROK_Buck_5pin_Header.kicad_mod").write_text(drok_footprint(), encoding="utf-8")
    write_libtables()

    sh = build_sheet(pb)
    for w in sh.warnings:
        print("layout warning:", w)
    (HERE / f"{PROJECT}.kicad_sch").write_text(schematic_text(sh), encoding="utf-8")
    write_project(sh.root_uuid)
    print("wrote schematic with", len(sh.placed), "parts and", len(sh.libs), "lib symbols")

    if not a.no_export:
        export_all()
    if not a.no_pcb and not a.no_export:
        pcb = build_pcb(pb)
        if pcb and not a.no_drc:
            run_drc(pb, pcb)


if __name__ == "__main__":
    main()
