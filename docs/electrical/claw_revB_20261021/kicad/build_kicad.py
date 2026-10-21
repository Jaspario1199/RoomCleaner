#!/usr/bin/env python3
"""Generate the RoomCleaner claw Rev B KiCad 7 project (schematic only; the claw is point-to-point wired).

    /usr/bin/python3 build_kicad.py            # project, libraries, netlist, PDF, PNG, netlist check
    /usr/bin/python3 build_kicad.py --erc      # also KiCad's real ERC (eeschema under Xvfb, about 1 min)
    /usr/bin/python3 build_kicad.py --no-export

Connectivity is NOT typed here: every pin's net comes from claw_spec.py (the "Nets" table of
../CLAW_REVB_SPEC.md).  This file only decides where symbols sit and how each pin is wired out.
The s-expression / symbol / footprint helpers are reused from the station generator
(../../station_revD_20261021/kicad/build_kicad.py) by importing it; that folder is never written to
(bytecode writing is disabled for the import).
"""
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import textwrap
import uuid
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claw_spec as spec  # noqa: E402  (imported before the station module so the names cannot clash)

STATION_DIR = HERE.parents[1] / "station_revD_20261021" / "kicad"
_sp = importlib.util.spec_from_file_location("station_build_kicad", STATION_DIR / "build_kicad.py")
st = importlib.util.module_from_spec(_sp)
sys.modules["station_build_kicad"] = st
_sp.loader.exec_module(st)
if str(STATION_DIR) in sys.path:
    sys.path.remove(str(STATION_DIR))

PROJECT = "RoomCleaner_Claw_RevB"
NICK = "RoomCleanerClaw"
TITLE = "RoomCleaner claw — Rev B"
DATE = "2026-10-21"
# parameterise the reused station code for this project (module globals of the imported copy only)
st.PROJECT = PROJECT
st.NS = uuid.UUID("0d5c3a52-6c0f-4d52-8d1e-20261021cb02")
st.POWER_NETS = {"GND": "GND"}          # the only net drawn with a power symbol; rails use labels
st.TITLE, st.DATE = TITLE, DATE

EFF, EFF_HIDE = st.EFF, st.EFF_HIDE

# ---------------------------------------------------------------------------
# custom symbols (RoomCleanerClaw.kicad_sym)
# ---------------------------------------------------------------------------


def custom_symbol(name, prefix, footprint, datasheet, keywords, descr, fp_filter, ref_at, val_at, body, pins,
                  body_text=""):
    s = f'  (symbol {st.q(name)} (in_bom yes) (on_board yes)\n'
    s += f'    (property "Reference" {st.q(prefix)} (at {ref_at[0]} {ref_at[1]} 0)\n      {EFF}\n    )\n'
    s += f'    (property "Value" {st.q(name)} (at {val_at[0]} {val_at[1]} 0)\n      {EFF}\n    )\n'
    s += f'    (property "Footprint" {st.q(footprint)} (at 0 0 0)\n      {EFF_HIDE}\n    )\n'
    s += f'    (property "Datasheet" {st.q(datasheet)} (at 0 0 0)\n      {EFF_HIDE}\n    )\n'
    s += f'    (property "ki_keywords" {st.q(keywords)} (at 0 0 0)\n      {EFF_HIDE}\n    )\n'
    s += f'    (property "ki_description" {st.q(descr)} (at 0 0 0)\n      {EFF_HIDE}\n    )\n'
    s += f'    (property "ki_fp_filters" {st.q(fp_filter)} (at 0 0 0)\n      {EFF_HIDE}\n    )\n'
    s += f'    (symbol {st.q(name + "_0_1")}\n'
    s += (f'      (rectangle (start {st.fmt(body[0])} {st.fmt(body[1])}) (end {st.fmt(body[2])} {st.fmt(body[3])})\n'
          f'        (stroke (width 0.254) (type default))\n        (fill (type background))\n      )\n')
    s += body_text + '    )\n'
    s += f'    (symbol {st.q(name + "_1_1")}\n' + "".join(pins) + '    )\n  )\n'
    return s


def txt(s, x, y, size=1.27):
    return (f'      (text {st.q(s)} (at {st.fmt(x)} {st.fmt(y)} 0)\n'
            f'        (effects (font (size {size} {size})))\n      )\n')


def xiao_s3_symbol():
    """Seeed XIAO ESP32-S3 (Sense). Pad order as Seeed: 1..7 = D0..D6 (left), 8..14 = D7..D10, 3V3, GND, 5V."""
    pins = []
    for k in range(7):
        nm = f"D{k}"
        pins.append(st.sym_pin("bidirectional", -17.78, 22.86 - 7.62 * k, 0, 5.08,
                               f"{nm}/GPIO{spec.XIAO_S3_GPIO[nm]}", str(k + 1)))
    right = [("5V", "14", "power_in"), ("GND", "13", "power_in"), ("3V3", "12", "power_out")] + \
            [(f"D{n}/GPIO{spec.XIAO_S3_GPIO[f'D{n}']}", str(n + 1), "bidirectional") for n in (10, 9, 8, 7)]
    for k, (nm, num, ty) in enumerate(right):
        pins.append(st.sym_pin(ty, 17.78, 22.86 - 7.62 * k, 180, 5.08, nm, num))
    body = txt("XIAO", 0, 3.81) + txt("ESP32-S3", 0, -3.81) + txt("USB-C", 0, 26.035)
    return custom_symbol(
        "XIAO_ESP32S3", "U", f"{NICK}:XIAO_ESP32S3_Sense_THT",
        "https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/", "Seeed XIAO ESP32-S3 Sense ESP32S3 module",
        "Seeed Studio XIAO ESP32-S3 (Sense), 14 pin module (2 x 7, 2.54 mm): D0-D10 with GPIO numbers, 3V3, GND, 5V. "
        "The Sense camera board is on the factory B2B connector (not drawn); BAT pads on the underside unused.",
        "XIAO*ESP32S3*", (0, 30.48), (0, -27.94), (-12.7, 27.94, 12.7, -25.4), pins, body)


def module4_symbol(name, footprint, datasheet, descr, line1, line2):
    """Generic 4-wire DC-DC module: IN+, IN-, OUT+, OUT-. OUT+ is the only driver; the rest passive."""
    pins = [st.sym_pin("passive", -15.24, 5.08, 0, 5.08, "IN+", "1"),
            st.sym_pin("passive", -15.24, -5.08, 0, 5.08, "IN-", "2"),
            st.sym_pin("power_out", 15.24, 5.08, 180, 5.08, "OUT+", "3"),
            st.sym_pin("passive", 15.24, -5.08, 180, 5.08, "OUT-", "4")]
    body = txt(line1, 0, 1.27) + txt(line2, 0, -1.27)
    return custom_symbol(name, "U", footprint, datasheet, "DC-DC buck module", descr, "WireModule*",
                         (0, 12.7), (0, -12.7), (-10.16, 10.16, 10.16, -10.16), pins, body)


def charger_symbol():
    pins = [st.sym_pin("passive", -15.24, 5.08, 0, 5.08, "B+", "1"),
            st.sym_pin("passive", -15.24, -5.08, 0, 5.08, "B-", "2")]
    body = txt("USB-C 2S", 0, 5.08) + txt("charger", 0, 2.54) + txt("8.4V CC/CV", 0, -1.27) + \
        txt("<= 1 A", 0, -3.81) + txt("USB-C IN: external", 0, -8.0, 1.0)
    return custom_symbol(
        "Charger_USBC_2S", "U", f"{NICK}:WireModule_2pad_P2.54mm", "~", "USB-C 2S Li-ion charger module",
        "USB-C 2S charging module (\"2S1A\"): B+ / B- to the pack side. USB-C input from a 5 V adapter (external, "
        "not drawn). Must be an 8.4 V CC/CV type at <= 1 A.", "WireModule*",
        (0, 12.7), (0, -12.7), (-10.16, 10.16, 10.16, -10.16), pins, body)


def servo_conn_symbol():
    """3-pin servo lead. Numbers follow the spec (1 GND, 2 V+, 3 signal); drawn with GND at the bottom."""
    pins = [st.sym_pin("passive", -5.08, 2.54, 0, 3.81, "SIG", "3"),
            st.sym_pin("passive", -5.08, 0, 0, 3.81, "V+", "2"),
            st.sym_pin("passive", -5.08, -2.54, 0, 3.81, "GND", "1")]
    return custom_symbol(
        "Servo_Conn_3pin", "J", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", "~",
        "servo connector 3 pin", "Servo lead, 3 pin: pin 1 GND (brown), pin 2 V+ (red), pin 3 signal (orange). "
        "Drawn with GND at the bottom.", "Pin*1x03*", (0, 6.35), (0, -6.35), (-1.27, 3.81, 6.35, -3.81), pins)


def custom_library_text():
    return ('(kicad_symbol_lib (version 20220914) (generator build_kicad)\n'
            + xiao_s3_symbol()
            + module4_symbol("UBEC_ZTW_4pin", f"{NICK}:WireModule_4pad_P2.54mm", "~",
                             "ZTW UBEC, 6 A continuous / 10 A peak, output jumper set to 6.0 V. Generic 4-wire module: "
                             "IN+, IN-, OUT+, OUT-. Verify against the labels on the real module.",
                             "ZTW UBEC", "6 A / 10 A pk")
            + module4_symbol("Buck_MP1584_4pin", f"{NICK}:WireModule_4pad_P2.54mm", "~",
                             "MP1584EN buck module, trim to 5.00 V. Generic 4-pin module: IN+, IN-, OUT+, OUT-. "
                             "Verify against the labels on the real module.", "MP1584EN", "buck")
            + charger_symbol() + servo_conn_symbol() + ')\n')


# ---------------------------------------------------------------------------
# custom footprints (RoomCleanerClaw.pretty)
# ---------------------------------------------------------------------------
def xiao_s3_footprint():
    s = st.xiao_footprint()
    s = s.replace("XIAO_ESP32C3_THT", "XIAO_ESP32S3_Sense_THT")
    s = s.replace("Seeed XIAO ESP32-C3 on 2 x 7 pin 2.54 mm headers", "Seeed XIAO ESP32-S3 (Sense) on 2 x 7 pin 2.54 mm headers")
    s = s.replace("XIAO ESP32C3 module header", "XIAO ESP32S3 Sense module header")
    return s


def wire_module_footprint(n, label):
    name = f"WireModule_{n}pad_P2.54mm"
    s = st.fp_header(name, f"{label}: {n} solder pads on a 2.54 mm row for hand-wired leads (module body not modelled).",
                     "wire module pads")
    w = 2.54 * (n - 1)
    s += st.fp_text("reference", "REF**", w / 2, -2.9, "F.SilkS")
    s += st.fp_text("value", name, w / 2, 2.9, "F.Fab")
    s += st.fp_text("user", "${REFERENCE}", w / 2, 0, "F.Fab")
    s += st.fp_rect_lines(-1.27, -1.27, w + 1.27, 1.27, "F.SilkS", 0.12)
    s += st.fp_rect_lines(-1.77, -1.77, w + 1.77, 1.77, "F.CrtYd", 0.05)
    for k in range(n):
        s += st.fp_pad(str(k + 1), 2.54 * k, 0, "rect" if k == 0 else "oval")
    return s + ")\n"


FP = {
    "U1": f"{NICK}:WireModule_4pad_P2.54mm", "U2": f"{NICK}:WireModule_4pad_P2.54mm",
    "U3": f"{NICK}:XIAO_ESP32S3_Sense_THT", "U4": f"{NICK}:WireModule_2pad_P2.54mm",
    "J2": "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
    "D1": "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
    "C1": "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm",
    "C2": "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm", "C3": "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "C4": "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "R1": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "R2": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    # BT1, F1, SW1: chassis / lead-wired parts without a board footprint
}


# ---------------------------------------------------------------------------
# sheet
# ---------------------------------------------------------------------------
class ClawPlaced(st.Placed):
    def _prop(self, name, value):
        if name in self.fields:
            f = self.fields[name]
            dx, dy, just = f[:3]
            ang = f[3] if len(f) > 3 else 0
            info = self.lib.props.get(name, {"hide": True})
            hide = info.get("hide", True) or name in ("Footprint", "Datasheet")
            justify = [] if just in ("", "center") else just.split()
            eff = ("(effects (font (size 1.27 1.27))" + (f' (justify {" ".join(justify)})' if justify else "") +
                   (" hide" if hide else "") + ")")
            return (f'    (property {st.q(name)} {st.q(value)} (at {st.fmt(self.at[0] + dx)} '
                    f'{st.fmt(self.at[1] + dy)} {ang})\n      {eff}\n    )\n')
        return super()._prop(name, value)


class ClawSheet(st.Sheet):
    def __init__(self):
        super().__init__(None)
        self.pin_net = {}
        for net, pins in spec.expected()[0].items():
            for rp in pins:
                self.pin_net[rp] = net
        self.nc = spec.expected()[1]
        self.handled = set()
        self.custom_text = custom_library_text()

    def lib(self, nick, name):
        key = f"{nick}:{name}"
        if key not in self.libs:
            if nick == NICK:
                self.libs[key] = st.LibSymbol(nick, name, st.extract_symbol_from_text(self.custom_text, name))
            else:
                self.libs[key] = st.stock(nick, name)
        return self.libs[key]

    def place(self, lib, at, rot=0, ref=None, value=None, footprint="", fields=None, power=False):
        at = (st.snap(at[0]), st.snap(at[1]))
        p = ClawPlaced(self, lib, at, rot, ref, value, footprint, fields or {}, power)
        self.items.append(p.sexpr())
        if ref and not ref.startswith("#"):
            self.placed[ref] = p
        return p

    def net_of(self, ref, pin):
        if (ref, pin) in self.nc:
            return None
        return self.pin_net[(ref, pin)]       # KeyError = a symbol pin the spec does not mention

    def route(self, ref, pin, steps=None, terminal="auto"):
        self.handled.add((ref, pin))
        return super().route(ref, pin, steps, terminal)

    def join(self, pins, paths, label=None, junctions=()):
        """Hand-drawn wires (`paths` = list of point lists) that must touch every pin in `pins` (one net).
        label = (path index, point index, angle); junctions = list of points."""
        nets = {self.net_of(r, p) for r, p in pins}
        assert len(nets) == 1 and None not in nets, f"{pins} are not one net: {nets}"
        pts = [(round(x, 2), round(y, 2)) for path in paths for x, y in path]
        for r, p in pins:
            assert self.placed[r].pin_xy(p) in pts, (r, p, pts)
            self.handled.add((r, p))
        for path in paths:
            self.path(path)
        for j in junctions:
            self.junction(j)
        if label is not None:
            self.label(paths[label[0]][label[1]], nets.pop(), label[2])


def wrap(text, width=90, indent="    "):
    return textwrap.fill(text, width=width, subsequent_indent=indent, break_long_words=False)


def build_sheet():
    sh = ClawSheet()
    L = sh.lib
    for pwr in ("GND", "PWR_FLAG"):
        L("power", pwr)

    def part(ref, at, rot=0, fields=None):
        lib_id, value = spec.PARTS[ref]
        nick, name = lib_id.split(":")
        return sh.place(L(nick, name), at, rot, ref=ref, value=value, footprint=FP.get(ref, ""), fields=fields)

    # ---- headings -------------------------------------------------------------
    sh.text((15.24, 17.78), "RoomCleaner claw — Rev B", size=2.54, bold=True)
    sh.text((15.24, 24.13), "Point-to-point wired claw. Net names and connections = the net table of CLAW_REVB_SPEC.md "
            "(drawn from claw_spec.py). Design, not yet built or bench-tested.", size=1.27)

    # ====================== battery, fuse, switch, charger =====================
    sh.text((15.24, 33.02), "BATTERY, FUSE, MAIN SWITCH (load side) and CHARGER (pack side)", size=1.8, bold=True)
    bt1 = part("BT1", (40.64, 50.8), rot=270, fields={"Reference": (0, -6.35, "center", 90),
                                                                 "Value": (-3.81, 8.89, "left", 90)})
    f1 = part("F1", (66.04, 50.8), rot=90, fields={"Reference": (0, -4.445, "center", 90),
                                                                 "Value": (0, 4.445, "center", 90)})
    sw1 = part("SW1", (91.44, 50.8), fields={"Reference": (0, -5.08, "center"), "Value": (0, 3.81, "center")})
    sh.join([("BT1", "1"), ("F1", "1")], [[bt1.pin_xy("1"), (53.34, 50.8), f1.pin_xy("1")]], label=(0, 1, 0))
    sh.join([("F1", "2"), ("SW1", "1")], [[f1.pin_xy("2"), (73.66, 50.8), sw1.pin_xy("1")]], label=(0, 1, 0))
    sh.route("SW1", "2", [(5.08, 0)])                                     # VBAT_SW
    sh.route("BT1", "2", [(-5.08, 0), (0, 5.08)])                         # GND
    sh.pwr_flag((30.48, 50.8))                                            # battery negative = the GND source
    sh.text((15.24, 66.04), "BT1: Tenergy 7.4 V 2200 mAh 2S1P Li-ion with protection PCB (31003 assumed: 3 A\n"
            "continuous, 1 A max charge); 8.4 V full, 6.8 V firmware cutoff. Confirm label and connector.\n"
            "F1: 5 A blade fuse in a holder on the battery + lead (provisional); protects the wiring, the pack\n"
            "PCB is the cell protection.  SW1: SPST >= 5 A DC, load side only; the charger stays on the pack side.",
            size=1.27)

    u4 = part("U4", (152.4, 50.8), fields={"Reference": (0, -12.7, "center"), "Value": (0, 12.7, "center")})
    sh.route("U4", "1", [(-5.08, 0)])                                     # BAT_FUSED
    sh.route("U4", "2", [(-5.08, 0)])                                     # GND
    sh.text((175.26, 45.72), "U4: USB-C input from a 5 V adapter is external (not drawn).\n"
            "CHARGE ONLY WITH SW1 OFF.  Charger must be an\n8.4 V CC/CV type at <= 1 A (Tenergy limit).", size=1.27)

    # ====================== converters ======================================
    sh.text((15.24, 84.0), "CONVERTERS: servo rail (UBEC 6.0 V) and logic rail (MP1584 5.00 V through D1)", size=1.8,
            bold=True)
    u1 = part("U1", (60.96, 104.14), fields={"Reference": (0, -12.7, "center"), "Value": (0, 12.7, "center")})
    sh.route("U1", "1", [(-5.08, 0)])                                     # IN+  VBAT_SW
    sh.route("U1", "2", [(-5.08, 0)])                                     # IN-  GND
    sh.route("U1", "3", [(5.08, 0)])                                      # OUT+ +6V_SERVO
    sh.route("U1", "4", [(5.08, 0)])                                      # OUT- GND
    sh.text((101.6, 96.52), "U1: ZTW UBEC (6 A continuous / 10 A peak),\n"
            "jumper set to 6.0 V. Servo only. Measure the\noutput before connecting the servo.", size=1.27)

    u2 = part("U2", (60.96, 139.7), fields={"Reference": (0, -12.7, "center"), "Value": (0, 12.7, "center")})
    d1 = part("D1", (101.6, 134.62), rot=180, fields={"Reference": (0, -3.81, "center"), "Value": (0, 3.81, "center")})
    sh.route("U2", "1", [(-5.08, 0)])                                     # IN+  VBAT_SW
    sh.route("U2", "2", [(-5.08, 0)])                                     # IN-  GND
    sh.route("U2", "4", [(5.08, 0)])                                      # OUT- GND
    sh.join([("U2", "3"), ("D1", "2")], [[u2.pin_xy("3"), (86.36, 134.62), d1.pin_xy("2")]], label=(0, 1, 0))
    sh.route("D1", "1", [(12.7, 0)])                                      # +5V_XIAO
    sh.text((88.9, 148.59), "U2: MP1584EN buck, trim to 5.00 V BEFORE connecting the XIAO. XIAO only.\n"
            "D1 1N5819: anode at U2 OUT+, band (cathode) toward the XIAO; Seeed requires a diode on\n"
            "external 5 V input. Never feed the XIAO 5V pad from the 6 V rail.", size=1.27)

    # ====================== servo connector ====================================
    sh.text((172.72, 84.0), "SERVO CONNECTOR AND DECOUPLING", size=1.8, bold=True)
    c1 = part("C1", (182.88, 104.14), fields={"Reference": (1.27, -2.54, "left"), "Value": (1.27, 2.54, "left")})
    c2 = part("C2", (198.12, 104.14), fields={"Reference": (1.27, -2.54, "left"), "Value": (1.27, 2.54, "left")})
    j2 = part("J2", (226.06, 100.33), fields={"Reference": (3.81, -6.35, "left"), "Value": (3.81, 7.62, "left")})
    rail_y = 100.33
    sh.join([("C1", "1"), ("C2", "1"), ("J2", "2")],
            [[(172.72, rail_y), c1.pin_xy("1"), c2.pin_xy("1"), j2.pin_xy("2")]], label=(0, 0, 180),
            junctions=[c1.pin_xy("1"), c2.pin_xy("1")])
    sh.route("C1", "2", [(0, 5.08)])
    sh.route("C2", "2", [(0, 5.08)])
    sh.route("J2", "1", [(-5.08, 0)])                                     # GND (hangs below the rail)
    sh.route("J2", "3", [(-5.08, 0)])                                     # SERVO_PWM
    sh.text((172.72, 120.65), "C1 1000 uF / 16 V (+ to V+) and C2 100 nF sit at the servo connector.\n"
            "J2 (MG996R lead): pin 1 GND (brown), pin 2 V+ (red), pin 3 signal (orange); check your lead.\n"
            "Signal is 3.3 V PWM from D0 / GPIO1 into a 6 V servo (no buffer, as the firmware assumes).", size=1.27)

    # ====================== logic: XIAO + battery divider ===========================
    sh.text((15.24, 165.1), "LOGIC: XIAO ESP32-S3 Sense, battery sense divider (D2 / GPIO3), 5 V decoupling", size=1.8,
            bold=True)
    r1 = part("R1", (50.8, 187.96), fields={"Reference": (3.81, -1.27, "left"), "Value": (3.81, 1.27, "left")})
    r2 = part("R2", (50.8, 203.2), fields={"Reference": (3.81, -1.27, "left"), "Value": (3.81, 1.27, "left")})
    c4 = part("C4", (66.04, 199.39), fields={"Reference": (1.27, 5.08, "left"), "Value": (1.27, 7.62, "left")})
    u3 = part("U3", (152.4, 203.2), fields={"Reference": (-17.78, -33.02, "left"), "Value": (-17.78, -30.48, "left")})
    node = (50.8, 195.58)
    sh.route("R1", "1", [(0, -2.54), (-5.08, 0)])                         # VBAT_SW
    sh.join([("R1", "2"), ("R2", "1"), ("C4", "1"), ("U3", "3")],
            [[r1.pin_xy("2"), node, r2.pin_xy("1")], [node, c4.pin_xy("1"), (101.6, node[1]), u3.pin_xy("3")]],
            label=(1, 2, 0), junctions=[node])
    sh.route("R2", "2", [(0, 5.08)])
    sh.route("C4", "2", [(0, 5.08)])
    sh.text((15.24, 218.44), "R1 200k 1 % (top) / R2 100k 1 % (bottom), C4 100 nF filter at D2.\n"
            "8.4 V x 100/300 = 2.80 V at D2; the 6.8 V cutoff reads 2.27 V\n"
            "(ESP32-S3 ADC, 11 dB: ~0-3.1 V). Divider drain 28 uA. Firmware BATT_RATIO 3.0.", size=1.27)

    sh.route("U3", "1", [(-7.62, 0)])                                     # D0/GPIO1 SERVO_PWM
    for pin in ("2", "4", "5", "6", "7", "8", "9", "10", "11", "12"):    # D1 D3-D10 3V3 unconnected
        sh.route("U3", pin, [])
    sh.handled.add(("U3", "3"))
    sh.route("U3", "14", [(5.08, 0), (7.62, 0)])                          # 5V -> +5V_XIAO
    sh.pwr_flag((u3.pin_xy("14")[0] + 5.08, u3.pin_xy("14")[1]))
    sh.route("U3", "13", [(5.08, 0)])                                     # GND
    c3 = part("C3", (200.66, 190.5), fields={"Reference": (1.27, 5.08, "left"), "Value": (1.27, 7.62, "left")})
    sh.route("C3", "1", [(0, -2.54), (5.08, 0)])
    sh.route("C3", "2", [(0, 5.08)])
    sh.text((194.31, 207.0), "C3 100 nF at the XIAO 5V pad.\nPWR_FLAG: 5 V reaches the pad through\n"
            "D1 (or from USB-C when programming).", size=1.27)
    sh.rect((111.76, 233.0), (222.25, 250.0))
    sh.text((113.03, 234.3), "SENSE CAMERA BOARD (note only, not wired here)\n"
            "The Sense camera board is attached to the XIAO ESP32-S3 by its factory B2B connector;\n"
            "no header pin is used for it. BAT pads on the underside of the XIAO are unused.\n"
            "USB-C on the XIAO is for programming (5V pad is fed from D1; never from the 6 V rail).", size=1.27)
    sh.text((15.24, 238.76), "UNCONNECTED (per spec): XIAO D1, D3-D10, 3V3 (no-connect flags), BAT pads;\n"
            "U1 / U2 have no enable pins on these symbols; U4 USB-C input is the external adapter.", size=1.27)

    # ====================== notes column ======================================
    x0 = 304.8
    y = 17.78

    def block(title, paras, gap=5.0):
        nonlocal y
        sh.text((x0, y), title, size=1.8, bold=True)
        y += 5.2
        body = "\n".join(wrap(p) for p in paras)
        sh.text((x0, y), body, size=1.27)
        y += 2.15 * (body.count("\n") + 1) + gap

    block("D31 AND AUTHORITY", [
        "DECISIONS.md D31 (2026-10-21): Tenergy 7.4 V 2S pack; ZTW UBEC at 6.0 V for the servo; MP1584 at 5.00 V for "
        "the XIAO through a 1N5819, never from the 6 V rail; USB-C 2S charger on the pack side of the main switch.",
        "Spec: docs/electrical/claw_revB_20261021/CLAW_REVB_SPEC.md. Pin map: firmware/claw_s3/claw_s3.ino "
        "(servo PWM D0 / GPIO1; battery sense D2 / GPIO3, BATT_RATIO 3.0, cutoff 6.8 V)."])
    block("CHARGING RULE (D31)", [
        "CHARGE ONLY WITH SW1 OFF, attended, on a non-flammable surface, with an 8.4 V CC/CV charger at <= 1 A.",
        "The pack's protection PCB must provide per-cell overcharge / over-discharge protection: confirm it on the "
        "label or datasheet before the first charge (a 2-wire pack cannot be balance-charged)."])
    block("EMERGENCY STOP", [
        "The emergency stop is the switched power strip at the stations. SW1 on the claw is a SERVICE DISCONNECT "
        "only; it does not stop the winches."])
    block("CHECKS (calculated, spec)", [
        "- Battery sense: 8.4 V x 100/300 = 2.80 V at D2; 6.8 V cutoff -> 2.27 V. Inside the ESP32-S3 ADC range at "
        "11 dB (~0-3.1 V). Divider drain 28 uA.",
        "- Peak pack current: servo stall ~2.5 A at 6 V (15 W, provisional) + logic ~0.7 A at 5 V (3.5 W) = 18.5 W; "
        "at 88 % efficiency 2.8 A at 7.4 V, 3.1 A at 6.8 V: at the pack's ~3 A continuous rating. Stalls are "
        "short, but the pack PCB may trip on a long stall near empty. Measure the servo stall current.",
        "- Servo signal is 3.3 V PWM into a 6 V servo (no buffer, as the firmware assumes). Most MG996R units "
        "accept it; bench-check the full open/close travel.",
        "- UBEC near empty: 6.8 V in for 6.0 V out leaves little headroom; the servo rail may sag near cutoff, "
        "acceptable because the firmware stops lifts at 6.8 V."])
    block("BEFORE THE FIRST POWER-UP", [
        "1. Set U1 to 6.0 V and U2 to 5.00 V with a meter, nothing connected to their outputs.",
        "2. Confirm U4 is an 8.4 V CC/CV module and its charge current is <= 1 A (Tenergy limit).",
        "3. Check the pack voltage (7.4-8.4 V) and polarity at the connector.",
        "4. Power up with the servo unplugged; check D2 reads ~VBAT/3 in /status.",
        "5. Plug in the servo; run /setup to park it open."])
    return sh


def schematic_text(sh):
    s = ('(kicad_sch (version 20230121) (generator build_kicad)\n\n'
         f'  (uuid {sh.root_uuid})\n\n  (paper "A3")\n\n'
         f'  (title_block\n    (title {st.q(TITLE)})\n    (date "{DATE}")\n    (rev "B")\n'
         '    (company "RoomCleaner")\n'
         '    (comment 1 "Net table of CLAW_REVB_SPEC.md; DECISIONS.md D31")\n'
         '    (comment 2 "Design, not yet built or bench-tested")\n  )\n\n')
    s += '  (lib_symbols\n'
    for key in sorted(sh.libs):
        s += "".join("    " + ln + "\n" for ln in sh.libs[key].text.splitlines())
    s += '  )\n\n' + "".join(sh.items)
    s += '\n  (sheet_instances\n    (path "/" (page "1"))\n  )\n)\n'
    return s


# ---------------------------------------------------------------------------
# project files and exports
# ---------------------------------------------------------------------------
STOCK_SYM_LIBS = ["Device", "Switch", "power"]
STOCK_FP_LIBS = ["Capacitor_THT", "Connector_PinHeader_2.54mm", "Diode_THT", "Resistor_THT"]


def write_libtables():
    q = st.q
    s = '(sym_lib_table\n  (version 7)\n'
    for n in STOCK_SYM_LIBS:
        s += (f'  (lib (name {q(n)})(type "KiCad")(uri "${{KICAD7_SYMBOL_DIR}}/{n}.kicad_sym")(options "")'
              f'(descr "KiCad stock library"))\n')
    s += (f'  (lib (name {q(NICK)})(type "KiCad")(uri "${{KIPRJMOD}}/{NICK}.kicad_sym")(options "")'
          f'(descr "RoomCleaner claw Rev B: XIAO ESP32-S3, generic modules, servo lead"))\n)\n')
    (HERE / "sym-lib-table").write_text(s, encoding="utf-8")
    f = '(fp_lib_table\n  (version 7)\n'
    for n in STOCK_FP_LIBS:
        f += (f'  (lib (name {q(n)})(type "KiCad")(uri "${{KICAD7_FOOTPRINT_DIR}}/{n}.pretty")(options "")'
              f'(descr "KiCad stock library"))\n')
    f += (f'  (lib (name {q(NICK)})(type "KiCad")(uri "${{KIPRJMOD}}/{NICK}.pretty")(options "")'
          f'(descr "RoomCleaner claw Rev B"))\n)\n')
    (HERE / "fp-lib-table").write_text(f, encoding="utf-8")


def write_project(sheet_uuid):
    pro = {
        "meta": {"filename": f"{PROJECT}.kicad_pro", "version": 1},
        "net_settings": {"classes": [{"name": "Default", "clearance": 0.2, "track_width": 0.25, "via_diameter": 0.8,
                                      "via_drill": 0.4, "wire_width": 6, "bus_width": 12, "line_style": 0,
                                      "schematic_color": "rgba(0, 0, 0, 0.000)", "pcb_color": "rgba(0, 0, 0, 0.000)",
                                      "priority": 2147483647}],
                         "meta": {"version": 3}, "net_colors": None, "netclass_assignments": None,
                         "netclass_patterns": []},
        "schematic": {"meta": {"version": 1}, "drawing": {"default_line_thickness": 6.0, "default_text_size": 50.0},
                      "legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [[sheet_uuid, ""]],
        "text_variables": {},
    }
    (HERE / f"{PROJECT}.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n", encoding="utf-8")


def run(cmd):
    print("  $", " ".join(str(c) for c in cmd))
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=HERE)
    for out in (r.stdout, r.stderr):
        if out.strip():
            print("   ", out.strip().replace("\n", "\n    "))
    if r.returncode != 0:
        raise SystemExit(f"command failed ({r.returncode})")


def export_all():
    sch = f"{PROJECT}.kicad_sch"
    run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o", f"{PROJECT}_netlist.xml", sch])
    run(["kicad-cli", "sch", "export", "pdf", "-o", f"{PROJECT}.pdf", sch])
    run(["pdftoppm", "-r", "110", "-png", "-singlefile", f"{PROJECT}.pdf", f"{PROJECT}_preview"])


def netlist_check():
    r = subprocess.run([sys.executable, str(HERE / "check_netlist.py")], capture_output=True, text=True, cwd=HERE)
    (HERE / "netlist_check.txt").write_text(r.stdout, encoding="utf-8")
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr)
    if r.returncode != 0:
        raise SystemExit("check_netlist.py FAILED (see netlist_check.txt)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--erc", action="store_true",
                    help="also run KiCad's real ERC through eeschema under Xvfb (kicad-cli 7.0.11 has no sch erc)")
    a = ap.parse_args()

    (HERE / f"{NICK}.kicad_sym").write_text(custom_library_text(), encoding="utf-8")
    pretty = HERE / f"{NICK}.pretty"
    pretty.mkdir(exist_ok=True)
    (pretty / "XIAO_ESP32S3_Sense_THT.kicad_mod").write_text(xiao_s3_footprint(), encoding="utf-8")
    (pretty / "WireModule_4pad_P2.54mm.kicad_mod").write_text(wire_module_footprint(4, "Generic 4-wire DC-DC module"),
                                                              encoding="utf-8")
    (pretty / "WireModule_2pad_P2.54mm.kicad_mod").write_text(wire_module_footprint(2, "Generic 2-wire module"),
                                                              encoding="utf-8")
    write_libtables()

    sh = build_sheet()
    # every pin of every placed symbol must have been wired or flagged no-connect
    for ref in spec.PARTS:
        for pin in sh.placed[ref].lib.pins:
            if (ref, pin) not in sh.handled:
                raise SystemExit(f"{ref} pin {pin} was never wired or flagged")
    for ref in sh.placed:
        if ref not in spec.PARTS:
            raise SystemExit(f"{ref} is not in the spec's parts table")
    for w in sh.warnings:
        print("layout warning:", w)
    (HERE / f"{PROJECT}.kicad_sch").write_text(schematic_text(sh), encoding="utf-8")
    write_project(sh.root_uuid)
    print("wrote schematic with", len(sh.placed), "parts and", len(sh.libs), "lib symbols")
    if not a.no_export:
        export_all()
        netlist_check()
    if a.erc:
        run([sys.executable, HERE / "run_erc_xvfb.py"])


if __name__ == "__main__":
    main()
