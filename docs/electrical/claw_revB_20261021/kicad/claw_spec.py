"""The claw Rev B connectivity, encoded ONCE.

SOURCE OF TRUTH: docs/electrical/claw_revB_20261021/CLAW_REVB_SPEC.md
  * "Parts" table        -> PARTS
  * "Nets" table         -> SPEC_NETS (strings copied from the table, same wording)
  * "Unconnected:" line  -> SPEC_UNCONNECTED
(Authority behind the spec: DECISIONS.md D31 and firmware/claw_s3/claw_s3.ino.)

build_kicad.py draws the schematic from these tables and check_netlist.py compares the exported
netlist with them.  The only things added here are the mappings from the spec's words
("F1 in", "R1 top", "U3 D2") to symbol pin numbers; they are the one place a drawing choice is made.
If the spec changes, edit the tables below and nothing else; run build_kicad.py again.
"""

# --- Parts table: ref -> (lib_id used in the schematic, Value field = spec "Value / setting") ---
PARTS = {
    "BT1": ("Device:Battery", "Tenergy 7.4V 2200mAh 2S1P"),
    "F1": ("Device:Fuse", "5A blade"),
    "SW1": ("Switch:SW_SPST", "SPST >=5A DC"),
    "U1": ("RoomCleanerClaw:UBEC_ZTW_4pin", "ZTW UBEC 6.0V"),
    "U2": ("RoomCleanerClaw:Buck_MP1584_4pin", "MP1584EN 5.00V"),
    "D1": ("Device:D_Schottky", "1N5819"),
    "U3": ("RoomCleanerClaw:XIAO_ESP32S3", "XIAO ESP32-S3 Sense"),
    "J2": ("RoomCleanerClaw:Servo_Conn_3pin", "MG996R lead"),
    "C1": ("Device:C_Polarized", "1000µF/16V"),
    "C2": ("Device:C", "100nF"),
    "C3": ("Device:C", "100nF"),
    "C4": ("Device:C", "100nF"),
    "R1": ("Device:R", "200k 1%"),
    "R2": ("Device:R", "100k 1%"),
    "U4": ("RoomCleanerClaw:Charger_USBC_2S", "USB-C 2S 8.4V CC/CV 1A"),
}

# --- Nets table, verbatim wording ("REF PIN"; a bare "C2" means the lead of that part on this net) ---
SPEC_NETS = {
    "BAT_POS": ["BT1 +", "F1 in"],
    "BAT_FUSED": ["F1 out", "SW1 in", "U4 B+"],
    "VBAT_SW": ["SW1 out", "U1 IN+", "U2 IN+", "R1 top"],
    "GND": ["BT1 −", "U1 IN−", "U1 OUT−", "U2 IN−", "U2 OUT−", "U3 GND", "J2 GND",
            "C1 −", "C2", "C3", "C4", "R2 bottom", "U4 B−"],
    "+6V_SERVO": ["U1 OUT+", "J2 V+", "C1 +", "C2"],
    "+5V_BUCK": ["U2 OUT+", "D1 anode"],
    "+5V_XIAO": ["D1 cathode", "U3 5V", "C3"],
    "VBAT_SENSE": ["R1 bottom", "R2 top", "C4", "U3 D2"],
    "SERVO_PWM": ["U3 D0", "J2 signal"],
}

# "Unconnected: XIAO D1, D3-D10, 3V3, BAT pads; U2/U1 enable pins (if any) left at their defaults;
#  U4 USB-C input (external adapter)."  Only the XIAO header pins exist as symbol pins; the BAT pads
# (underside), the module enable pins (the generic module symbols have none) and the USB-C input
# (external) are noted on the sheet, not drawn.
SPEC_UNCONNECTED = ["U3 D1", "U3 D3", "U3 D4", "U3 D5", "U3 D6", "U3 D7", "U3 D8", "U3 D9", "U3 D10", "U3 3V3"]

# --- spec words -> symbol pin numbers (the drawing choice) -------------------------------------
PIN_NUMBER = {
    "BT1": {"+": "1", "-": "2"},                      # stock Device:Battery
    "F1": {"in": "1", "out": "2"},                    # stock Device:Fuse (symmetric: 1 = battery side)
    "SW1": {"in": "1", "out": "2"},                   # stock Switch:SW_SPST (A = 1, B = 2)
    "U1": {"IN+": "1", "IN-": "2", "OUT+": "3", "OUT-": "4"},
    "U2": {"IN+": "1", "IN-": "2", "OUT+": "3", "OUT-": "4"},
    "D1": {"cathode": "1", "anode": "2"},             # stock D_Schottky: K = 1, A = 2
    "U3": {"D0": "1", "D1": "2", "D2": "3", "D3": "4", "D4": "5", "D5": "6", "D6": "7", "D7": "8",
           "D8": "9", "D9": "10", "D10": "11", "3V3": "12", "GND": "13", "5V": "14"},   # Seeed pad order
    "J2": {"GND": "1", "V+": "2", "signal": "3"},     # spec: GND / V+ / signal
    "C1": {"+": "1", "-": "2"},
    "R1": {"top": "1", "bottom": "2"},
    "R2": {"top": "1", "bottom": "2"},
    "U4": {"B+": "1", "B-": "2"},
}
# Symmetric two-lead parts listed without a pin in the table: which lead (pin number) sits on which net.
LEAD_PIN = {
    ("C2", "+6V_SERVO"): "1", ("C2", "GND"): "2",
    ("C3", "+5V_XIAO"): "1", ("C3", "GND"): "2",
    ("C4", "VBAT_SENSE"): "1", ("C4", "GND"): "2",
}
# GPIO behind each XIAO ESP32-S3 header pin (Seeed pinout; D0/GPIO1 and D2/GPIO3 are the firmware pins).
XIAO_S3_GPIO = {"D0": 1, "D1": 2, "D2": 3, "D3": 4, "D4": 5, "D5": 6, "D6": 43, "D7": 44, "D8": 7,
                "D9": 8, "D10": 9}


def _norm(s):
    return s.replace("−", "-")


def _split(entry):
    parts = _norm(entry).split(" ", 1)
    return parts[0], (parts[1] if len(parts) > 1 else None)


def expected():
    """-> ({net: {(ref, pin_number)}}, {(ref, pin_number)} unconnected).  Raises on an unmappable entry."""
    nets = {}
    for net, entries in SPEC_NETS.items():
        for e in entries:
            ref, word = _split(e)
            pin = LEAD_PIN[(ref, net)] if word is None else PIN_NUMBER[ref][word]
            nets.setdefault(net, set()).add((ref, pin))
    nc = set()
    for e in SPEC_UNCONNECTED:
        ref, word = _split(e)
        nc.add((ref, PIN_NUMBER[ref][word]))
    return nets, nc


if __name__ == "__main__":
    n, nc = expected()
    for k, v in n.items():
        print(f"{k:11s} {len(v):2d}  {sorted(v)}")
    print("unconnected:", sorted(nc))
