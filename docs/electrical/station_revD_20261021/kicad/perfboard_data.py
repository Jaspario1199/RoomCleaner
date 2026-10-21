"""Bridge between the as-soldered perfboard design and the KiCad project.

ONE SOURCE OF TRUTH: connectivity is read from ../perfboard_layout.py (PINS,
BARE, WIRES, NETMAP).  That file is NOT imported as a module, because doing so
would run its matplotlib drawing code and rewrite perfboard_layout.png/.pdf.
Instead only the table / check section above its "# ---- drawing" marker is
executed (read-only; nothing is written).

This module adds the only things the perfboard file does not say:
  * which schematic pin each perfboard hole is (HOLE_PIN, one dict, below);
  * how perfboard net names are spelled in the schematic (NET_NAME).

Used by build_kicad.py (generator) and check_netlist.py (independent checker).
"""
import contextlib
import io
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PERF_FILE = HERE.parent / "perfboard_layout.py"
DRAW_MARK = "# ---------------- drawing"
PITCH_MM = 2.54

# ---------------------------------------------------------------------------
# Perfboard net name -> schematic net name.
# Power rails use the stock KiCad power symbols, whose net names carry a "+".
# Everything else keeps the perfboard spelling (local labels; the exported
# netlist shows them with a leading "/").  PGND is folded into GND by the
# perfboard file's own NETMAP before this table is applied.
# ---------------------------------------------------------------------------
NET_NAME = {
    "12V": "+12V",   # J1 +12, buck IN+, A4988 VMOT, C1 +
    "3V3": "+3V3",   # XIAO 3V3, A4988 VDD/RST/SLP, R1/R4, J5 pin 1
    "5V": "+5V",     # XIAO 5V pin side of JP1 (USB VBUS / external 5 V)
    "GND": "GND",    # logic + motor ground (perfboard PGND tied by S03-O11)
    # 5VB (buck OUT+ / D1 anode), 5VD (D1 cathode / JP1) and the signal nets
    # keep their perfboard names.
}


def net_name(perf_net):
    return NET_NAME.get(perf_net, perf_net)


# ---------------------------------------------------------------------------
# HOLE -> schematic pin.   {ref: {hole: (pin_number, perfboard_label)}}
# The perfboard label is what PERFBOARD_LAYOUT.md / PINS print for that hole;
# it is cross-checked against PINS so a typo here cannot go unnoticed.
# Two-lead parts (R, JP1) are symmetric; pin 1/2 are assigned so that pin 1 is
# the upper / supply-side lead in the schematic.
# ---------------------------------------------------------------------------
HOLE_PIN = {
    # J1 12 V inlet, 5.08 mm terminal (or wires): pin 1 +12, pin 2 GND
    "J1": {"X01": ("1", "+12"), "X03": ("2", "GND")},
    # J2 motor, 4-pin header, top to bottom as on the board
    "J2": {"X05": ("1", "2B"), "X06": ("2", "2A"), "X07": ("3", "1A"), "X08": ("4", "1B")},
    # J5 AS5600 encoder, 4-pin header
    "J5": {"C17": ("1", "3V3"), "D17": ("2", "GND"), "E17": ("3", "SDA"), "F17": ("4", "SCL")},
    # J3 KW12-3 switch, 2-pin header (pin 1 = NC contact, pin 2 = COM)
    "J3": {"H17": ("1", "NC"), "I17": ("2", "COM")},
    # U1 DROK buck on its 5-pin single-row header, in the order the perfboard
    # file lists it (OUT+, OUT-, IN-, IN+, EN) = header pins 1..5 = X15..T15
    "U1": {"X15": ("1", "OUT+"), "W15": ("2", "OUT-"), "V15": ("3", "IN-"),
           "U15": ("4", "IN+"), "T15": ("5", "EN")},
    # D1 1N5819 lying, stripe = cathode = pin 1 (KiCad D_Schottky: K=1, A=2)
    "D1": {"T11": ("1", "K"), "X11": ("2", "A")},
    # JP1 USB / external-power link: pin 1 diode side (S11), pin 2 XIAO side (R11)
    "JP1": {"S11": ("1", "JP1"), "R11": ("2", "JP1")},
    # C1 100 uF / 50 V, + = pin 1
    "C1": {"T02": ("1", "C1 +"), "T03": ("2", "C1 -")},
    # 10 k resistors (symmetric; pin 1 = upper lead in the drawing)
    "R1": {"E13": ("1", "R1"), "E10": ("2", "R1")},   # EN pull-up: 3V3 / EN
    "R2": {"C10": ("1", "R2"), "C11": ("2", "R2")},   # STEP pull-down: STEP / GND
    "R3": {"D10": ("1", "R3"), "D11": ("2", "R3")},   # DIR pull-down: DIR / GND
    "R4": {"H13": ("1", "R4"), "H16": ("2", "R4")},   # HOME pull-up: 3V3 / HOME
}

# Seeed XIAO ESP32-C3 pin number by perfboard label (Seeed pad order:
# 1..7 = D0..D6 on one edge, 8..14 = D7..D10, 3V3, GND, 5V on the other).
XIAO_PIN = {"D0": "1", "D1": "2", "D2": "3", "D3": "4", "D4": "5", "D5": "6", "D6": "7",
            "D7": "8", "D8": "9", "D9": "10", "D10": "11", "3V3": "12", "GND": "13", "5V": "14"}
# Stock KiCad Driver_Motor:Pololu_Breakout_A4988 pin number by perfboard label.
# The carrier has two GND pads; perfboard holes Q04 (next to VMOT, motor
# return) = pad 7 and Q10 (next to VDD, logic ground) = pad 1.
A4988_PIN = {"EN": "9", "MS1": "10", "MS2": "11", "MS3": "12", "RST": "13", "SLP": "14",
             "STEP": "15", "DIR": "16", "VMOT": "8", "2B": "6", "2A": "5", "1A": "4",
             "1B": "3", "VDD": "2"}
A4988_GND_BY_HOLE = {"Q04": "7", "Q10": "1"}
# Schematic pin names the labels above must correspond to (self-check).
A4988_NAME = {"EN": "~{ENABLE}", "RST": "~{RESET}", "SLP": "~{SLEEP}"}

XIAO_COLS = "BCDEFGH"
U2_HOLES = [f"{c}03" for c in XIAO_COLS] + [f"{c}09" for c in XIAO_COLS]
U3_HOLES = [f"L{r:02d}" for r in range(3, 11)] + [f"Q{r:02d}" for r in range(3, 11)]


def load_perfboard():
    """Execute the table/check part of perfboard_layout.py, return its namespace."""
    src = PERF_FILE.read_text()
    if DRAW_MARK not in src:
        raise SystemExit("perfboard_layout.py: drawing marker not found; update perfboard_data.py")
    head = src.split(DRAW_MARK)[0]
    head = "\n".join(l for l in head.splitlines()
                     if not re.match(r"\s*(import matplotlib|matplotlib\.use|from matplotlib)", l))
    ns = {"__file__": str(PERF_FILE), "__name__": "perfboard_tables"}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(head, str(PERF_FILE), "exec"), ns)
    ns["_check_output"] = buf.getvalue().strip()
    return ns


def hole_xy(hole):
    """Perfboard hole name -> (x, y) in mm from hole A01 (x right, y down, component side)."""
    cols = "ABCDEFGHIJKLMNOPQRSTUVWX"
    return cols.index(hole[0]) * PITCH_MM, (int(hole[1:]) - 1) * PITCH_MM


class Perfboard:
    """Connectivity of the as-soldered board expressed in schematic terms."""

    def __init__(self):
        ns = load_perfboard()
        self.ns = ns
        self.check_output = ns["_check_output"]
        self.PINS = ns["PINS"]
        self.NETMAP = ns["NETMAP"]
        self.BARE, self.WIRES = ns["BARE"], ns["WIRES"]
        # hole -> (ref, pin)
        self.hole_pin = {}
        for ref, d in HOLE_PIN.items():
            for hole, (pin, label) in d.items():
                self._claim(hole, ref, pin)
                perf_label = self.PINS[hole][1]
                if perf_label != label:
                    raise SystemExit(f"label mismatch {ref} {hole}: perfboard '{perf_label}' vs map '{label}'")
        for hole in U2_HOLES:
            net, label = self.PINS[hole]
            self._claim(hole, "U2", XIAO_PIN[label])
        for hole in U3_HOLES:
            net, label = self.PINS[hole]
            pin = A4988_GND_BY_HOLE[hole] if label == "GND" else A4988_PIN[label]
            self._claim(hole, "U3", pin)
        missing = set(self.PINS) - set(self.hole_pin)
        extra = set(self.hole_pin) - set(self.PINS)
        if missing or extra:
            raise SystemExit(f"hole map incomplete: unmapped={sorted(missing)} unknown={sorted(extra)}")
        # (ref, pin) -> perfboard net (after NETMAP) or None for 'nc'
        self.pin_net = {}
        for hole, (ref, pin) in self.hole_pin.items():
            net = self.NETMAP.get(self.PINS[hole][0], self.PINS[hole][0])
            self.pin_net[(ref, pin)] = None if net == "nc" else net
        self._check_copper_groups()

    def _claim(self, hole, ref, pin):
        if hole in self.hole_pin:
            raise SystemExit(f"hole {hole} mapped twice")
        self.hole_pin[hole] = (ref, pin)

    # -- independent re-check of the copper (BARE runs + WIRES) -------------
    def _check_copper_groups(self):
        ns = self.ns
        cols = "ABCDEFGHIJKLMNOPQRSTUVWX"
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            parent[find(a)] = find(b)

        def holes_on(a, b):
            ca, ra = cols.index(a[0]), int(a[1:])
            cb, rb = cols.index(b[0]), int(b[1:])
            if ra == rb:
                return [f"{cols[c]}{ra:02d}" for c in range(min(ca, cb), max(ca, cb) + 1)]
            return [f"{cols[ca]}{r:02d}" for r in range(min(ra, rb), max(ra, rb) + 1)]

        for a, b, _ in self.BARE:
            hs = holes_on(a, b)
            for x, y in zip(hs, hs[1:]):
                union(x, y)
        for a, b, *_ in self.WIRES:
            union(a, b)
        union("S03", "O11")   # the explicit motor-GND / logic-GND tie in perfboard_layout.py
        groups = {}
        for hole, (ref, pin) in self.hole_pin.items():
            net = self.pin_net[(ref, pin)]
            if net is None:
                continue
            groups.setdefault(find(hole), set()).add(net)
        bad = {g: n for g, n in groups.items() if len(n) > 1}
        if bad:
            raise SystemExit(f"copper group joins different nets: {bad}")
        per_net = {}
        for g, nets in groups.items():
            for n in nets:
                per_net.setdefault(n, set()).add(g)
        split = {n: len(g) for n, g in per_net.items() if len(g) > 1}
        if split:
            raise SystemExit(f"net split over several copper groups: {split}")

    # -- results --------------------------------------------------------------
    def nets(self):
        """{schematic net name: set of (ref, pin)} for every connected net."""
        out = {}
        for (ref, pin), net in self.pin_net.items():
            if net is not None:
                out.setdefault(net_name(net), set()).add((ref, pin))
        return out

    def no_connects(self):
        return sorted(k for k, v in self.pin_net.items() if v is None)

    def holes_of(self, ref):
        return sorted((h for h, (r, _) in self.hole_pin.items() if r == ref),
                      key=lambda h: (h[1:], h[0]))

    def pin_hole(self, ref):
        return {pin: hole for hole, (r, pin) in self.hole_pin.items() if r == ref}


if __name__ == "__main__":
    pb = Perfboard()
    print(pb.check_output)
    for n, pins in sorted(pb.nets().items()):
        print(f"{n:6s} {len(pins):2d} pins: {sorted(pins)}")
    print("nc:", pb.no_connects())
