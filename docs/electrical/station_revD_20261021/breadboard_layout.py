"""Rev D station on a solderless breadboard (full-size 830-point board), net-checked.

Same circuit as the perfboard (perfboard_layout.py) and the KiCad schematic (kicad/): the check at the bottom
builds the breadboard's connectivity (row strips a-e and f-j, the four rails, every part pin and jumper) and
compares it pin by pin with the perfboard's net list (kicad/perfboard_data.py). It prints PASS only if every
net matches and no two nets touch.

Board convention used in the drawing and the wiring list:
  rows 1..63 run left to right; columns a-e are the top half, f-j the bottom half (trench between e and f);
  T+ / T- are the two rails along the top edge (next to column a), B+ / B- along the bottom edge (next to j).
  Rails: BOTH + rails = 3V3, BOTH - rails = GND (bridged at row 63). 12 V is on NO rail: it lives only in
  row 20 (f-j, the A4988 VMOT row) and in the red jumper to the buck IN+ (row 36).

    python3 breadboard_layout.py      # writes breadboard_layout.png/.pdf, prints the net check
"""
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kicad"))

TOP, BOT = "abcde", "fghij"
RAILS = ("T+", "T-", "B+", "B-")

# ---------------------------------------------------------------- placement: (ref, pin) -> hole
# pins numbered as in the KiCad schematic (kicad/perfboard_data.py): XIAO pads 1..7 = D0..D6, 8..11 = D7..D10,
# 12 3V3, 13 GND, 14 5V; Pololu A4988 1 GND, 2 VDD, 3 1B, 4 1A, 5 2A, 6 2B, 7 GND, 8 VMOT, 9 EN ... 16 DIR.
PLACE = {}
for i, pad in enumerate(["1", "2", "3", "4", "5", "6", "7"]):           # XIAO D0..D6 on column d, rows 5..11
    PLACE[("U2", pad)] = f"d{5 + i}"
for i, pad in enumerate(["14", "13", "12", "11", "10", "9", "8"]):     # 5V, GND, 3V3, D10, D9, D8, D7 on column h
    PLACE[("U2", pad)] = f"h{5 + i}"
for i, pin in enumerate(["9", "10", "11", "12", "13", "14", "15", "16"]):   # EN MS1 MS2 MS3 RST SLP STEP DIR (logic side)
    PLACE[("U3", pin)] = f"d{20 + i}"
for i, pin in enumerate(["8", "7", "6", "5", "4", "3", "2", "1"]):      # VMOT GND 2B 2A 1A 1B VDD GND (power side)
    PLACE[("U3", pin)] = f"g{20 + i}"
PLACE.update({
    ("U1", "1"): "h33", ("U1", "2"): "h34", ("U1", "3"): "h35", ("U1", "4"): "h36", ("U1", "5"): "h37",  # DROK OUT+ OUT- IN- IN+ EN
    ("D1", "2"): "i33", ("D1", "1"): "i29",              # 1N5819: anode in the buck OUT+ row, stripe (cathode) in row 29
    ("JP1", "1"): "j29", ("JP1", "2"): "i5",             # JP1 = a removable jumper wire j29 -> i5 (standalone only)
    ("C1", "1"): "h20", ("C1", "2"): "h21",              # 100 uF/50 V right at VMOT / GND
    ("R1", "2"): "a20", ("R1", "1"): "T+",               # EN pull-up to 3V3
    ("R2", "1"): "a26", ("R2", "2"): "T-",               # STEP pull-down
    ("R3", "1"): "a27", ("R3", "2"): "T-",               # DIR pull-down
    ("R4", "2"): "j8", ("R4", "1"): "B+",                # HOME pull-up to 3V3
    ("J1", "1"): "i20", ("J1", "2"): "i21",              # 12 V in (22 AWG leads from the WAGO), into the VMOT / GND rows
    ("J2", "1"): "j22", ("J2", "2"): "j23", ("J2", "3"): "j24", ("J2", "4"): "j25",   # motor 2B 2A 1A 1B (same order as the perfboard J2)
    ("J3", "1"): "i8", ("J3", "2"): "B-",                # switch NC to D10's row, COM to GND
    ("J5", "1"): "T+", ("J5", "2"): "T-", ("J5", "3"): "a9", ("J5", "4"): "a10",   # AS5600 VCC GND SDA SCL straight to the XIAO rows
})
# ---------------------------------------------------------------- jumper wires: (from, to, label, colour)
WIRES = [
    ("c6", "c26", "STEP", "#1f77b4"), ("c7", "c27", "DIR", "#2ca02c"), ("c8", "c20", "EN", "#9467bd"),
    ("b21", "T-", "MS1 GND", "#222222"), ("b22", "T-", "MS2 GND", "#222222"), ("b23", "T-", "MS3 GND", "#222222"),
    ("a24", "T+", "RST 3V3", "#ff7f0e"), ("a25", "T+", "SLP 3V3", "#ff7f0e"),
    ("j6", "B-", "XIAO GND", "#222222"), ("j7", "B+", "XIAO 3V3", "#ff7f0e"),
    ("j26", "B+", "VDD 3V3", "#ff7f0e"), ("j21", "B-", "motor GND", "#222222"), ("j27", "B-", "logic GND", "#222222"),
    ("j20", "j36", "12 V to buck IN+", "#d62728"),
    ("j34", "B-", "buck OUT-", "#222222"), ("j35", "B-", "buck IN-", "#222222"),
    ("T+", "B+", "3V3 rail bridge", "#ff7f0e"), ("T-", "B-", "GND rail bridge", "#222222"),
]
JP1_WIRE = ("j29", "i5")        # drawn dashed: plug in ONLY when running from 12 V with USB unplugged
BODIES = {                       # parts that cover holes: (label, col_from, col_to, row_from, row_to)
    "U2": ("XIAO ESP32-C3  (USB-C toward row 1)", "d", "h", 4.4, 11.6),
    "U3": ("A4988  (pot up)", "d", "g", 19.4, 27.6),
}


def strip_of(hole):
    if hole in RAILS:
        return hole
    col, row = hole[0], int(hole[1:])
    return f"{'top' if col in TOP else 'bot'}{row}"


def check():
    from perfboard_data import Perfboard
    pb = Perfboard()
    ref_nets = defaultdict(set)
    for key, net in pb.pin_net.items():
        if net is not None:
            ref_nets[net].add(key)
    missing = set(pb.pin_net) - set(PLACE)
    extra = set(PLACE) - set(pb.pin_net)
    assert not missing and not extra, f"placement incomplete: missing {sorted(missing)} extra {sorted(extra)}"
    # holes covered by a part body may not carry anything except that part's own pins
    cols = "abcdefghij"
    for ref, (_, c0, c1, r0, r1) in BODIES.items():
        own = {h for (rf, _), h in PLACE.items() if rf == ref}
        used = [h for (rf, _), h in PLACE.items() if rf != ref and h not in RAILS] + \
               [h for w in WIRES for h in w[:2] if h not in RAILS]
        for h in used:
            if h in own:
                continue
            if cols.index(c0) <= cols.index(h[0]) <= cols.index(c1) and r0 < int(h[1:]) < r1:
                raise SystemExit(f"hole {h} is under {ref}'s body")
    # one wire end per hole, one pin per hole
    holes = [h for h in PLACE.values() if h not in RAILS] + [h for w in WIRES for h in w[:2] if h not in RAILS]   # JP1's two ends are its PLACE pins
    dup = {h for h in holes if holes.count(h) > 1}
    assert not dup, f"two things in one hole: {sorted(dup)}"
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b, *_ in WIRES:
        parent[find(strip_of(a))] = find(strip_of(b))
    groups = defaultdict(set)
    for key, hole in PLACE.items():
        groups[find(strip_of(hole))].add(key)
    ok = True
    got = {}
    for g, keys in groups.items():
        nets = {pb.pin_net[k] for k in keys if pb.pin_net[k] is not None}
        ncs = [k for k in keys if pb.pin_net[k] is None]
        if len(nets) > 1 or (ncs and (nets or len(keys) > 1)):
            print(f"FAIL short: {sorted(keys)} -> nets {nets} no-connects {ncs}")
            ok = False
        for n in nets:
            got.setdefault(n, set()).update(keys)
    for net, keys in ref_nets.items():
        if got.get(net) != keys:
            print(f"FAIL net {net}: perfboard {sorted(keys)} breadboard {sorted(got.get(net, set()))}")
            ok = False
    # 12 V must never reach a rail
    if any(find(r) == find(strip_of(PLACE[("J1", "1")])) for r in RAILS):
        print("FAIL: 12 V reaches a rail"); ok = False
    print(f"{len(ref_nets)} nets, {sum(len(v) for v in ref_nets.values())} connected pins, "
          f"{sum(1 for v in pb.pin_net.values() if v is None)} no-connects, {len(WIRES)} jumpers + JP1")
    print("PASS" if ok else "FAIL")
    return ok


def draw():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle

    cols = "abcdefghij"
    ypos = {c: 9.5 - i - (1.6 if c in BOT else 0) for i, c in enumerate(cols)}   # a at the top, trench gap
    rail_y = {"T+": 11.6, "T-": 10.9, "B+": -2.9, "B-": -3.6}
    RMAX = 40

    def xy(hole, row_hint=None):
        if hole in RAILS:
            return (row_hint, rail_y[hole])
        return (int(hole[1:]), ypos[hole[0]])

    fig, ax = plt.subplots(figsize=(19, 8.2))
    ax.add_patch(Rectangle((0.2, -4.2), RMAX + 0.6, 16.5, fc="#f4f2ea", ec="#bdb9a8"))
    ax.add_patch(Rectangle((0.2, 3.6), RMAX + 0.6, 1.4, fc="#e4e1d4", ec="none"))     # trench
    for r in range(1, RMAX + 1):
        for c in cols:
            ax.plot(r, ypos[c], "s", ms=4.2, mfc="#ffffff", mec="#9a978a", mew=0.6, zorder=1)
        if r % 5 == 0 or r == 1:
            ax.text(r, 10.25, str(r), ha="center", fontsize=7, color="#6b6a65")
            ax.text(r, -2.25, str(r), ha="center", fontsize=7, color="#6b6a65")
    for c in cols:
        ax.text(-0.4, ypos[c], c, ha="center", va="center", fontsize=9, color="#6b6a65")
    for rail, y in rail_y.items():
        col = "#c2352b" if "+" in rail else "#2459b8"
        ax.plot([0.6, RMAX + 0.4], [y, y], color=col, lw=1.0, alpha=.5)
        for r in range(1, RMAX + 1):
            ax.plot(r, y, "s", ms=3.6, mfc="#ffffff", mec=col, mew=0.6, zorder=1)
        ax.text(-0.6, y, f"{rail}  ({'3V3' if '+' in rail else 'GND'})", ha="right", va="center", fontsize=9, color=col, weight="bold")
    # part bodies
    for ref, (lab, c0, c1, r0, r1) in BODIES.items():
        y0, y1 = ypos[c1] - 0.45, ypos[c0] + 0.45
        ax.add_patch(FancyBboxPatch((r0, y0), r1 - r0, y1 - y0, boxstyle="round,pad=0.05", fc="#2f6f3e" if ref == "U3" else "#1d3557",
                                    ec="#111", alpha=.88, zorder=3))
        ax.text((r0 + r1) / 2, (y0 + y1) / 2, ref + "\n" + lab, ha="center", va="center", color="white", fontsize=8.5, weight="bold", zorder=4)
    names = {"U2": {"1": "D0", "2": "D1 STEP", "3": "D2 DIR", "4": "D3 EN", "5": "D4 SDA", "6": "D5 SCL", "7": "D6",
                    "8": "D7", "9": "D8", "10": "D9", "11": "D10 HOME", "12": "3V3", "13": "GND", "14": "5V"},
             "U3": {"9": "EN", "10": "MS1", "11": "MS2", "12": "MS3", "13": "RST", "14": "SLP", "15": "STEP", "16": "DIR",
                    "8": "VMOT 12V", "7": "GND", "6": "2B", "5": "2A", "4": "1A", "3": "1B", "2": "VDD", "1": "GND"},
             "U1": {"1": "OUT+ 5V", "2": "OUT-", "3": "IN-", "4": "IN+ 12V", "5": "EN (nc)"}}
    for (ref, pin), hole in PLACE.items():
        if ref in names and hole not in RAILS:
            x, y = xy(hole)
            ax.plot(x, y, "o", ms=5.5, mfc="#ffd166", mec="#111", zorder=5)
            off = 0.62 if hole[0] in "abcd" else -0.62
            ax.text(x, y + (0.55 if hole[0] == "d" else -0.55), names[ref][pin], rotation=90, ha="center",
                    va="bottom" if hole[0] == "d" else "top", fontsize=6.3, zorder=6,
                    color="#111", bbox=dict(fc="#fffbe8", ec="none", pad=0.4, alpha=.85))
    # buck body (stands upright on its header)
    ax.add_patch(FancyBboxPatch((32.6, ypos["h"] - 0.45), 4.8, 0.9, boxstyle="round,pad=0.05", fc="#444", ec="#111", alpha=.85, zorder=3))
    ax.text(35, ypos["e"] - 0.1, "U1 DROK buck on its 5-pin header\n(stands up in h33-h37)\nset 5.00 V BEFORE the XIAO goes in",
            ha="center", va="top", fontsize=7.5, zorder=6, bbox=dict(fc="white", ec="#444", lw=0.5, pad=0.8))
    # two-lead parts
    import numpy as np

    def lead(a, b, label, colr, lw=2.5, ls="-", row_a=None, row_b=None, z=7, bend=0.0):
        """A part lead or jumper from hole a to hole b; bend > 0 arcs it toward the top edge, < 0 toward the bottom,
        so a long jumper is never drawn lying on top of the holes it passes over."""
        xa, ya = xy(a, row_a); xb, yb = xy(b, row_b)
        t = np.linspace(0, 1, 40)
        cx, cy = (xa + xb) / 2, (ya + yb) / 2 + bend
        X = (1 - t) ** 2 * xa + 2 * (1 - t) * t * cx + t ** 2 * xb
        Y = (1 - t) ** 2 * ya + 2 * (1 - t) * t * cy + t ** 2 * yb
        ax.plot(X, Y, ls=ls, color=colr, lw=lw, solid_capstyle="round", zorder=z)
        ax.plot([xa, xb], [ya, yb], "o", ms=4.0, color=colr, mec="#111", mew=0.5, zorder=z + 1, ls="none")
        if label:
            ax.text(X[20], Y[20], label, fontsize=6.8, ha="center", va="center", zorder=z + 2,
                    bbox=dict(fc="white", ec=colr, lw=0.6, pad=0.6, alpha=.92))
    lead("a20", "T+", "R1 10k", "#8c564b", row_b=20)
    lead("a26", "T-", "R2 10k", "#8c564b", row_b=26)
    lead("a27", "T-", "R3 10k", "#8c564b", row_b=27.6)
    lead("j8", "B+", "R4 10k", "#8c564b", row_b=8)
    lead("i33", "i29", "", "#555555", lw=4)
    ax.text(31, ypos["i"] - 0.15, "D1 1N5819\nstripe at i29", fontsize=6.5, ha="center", va="top", zorder=9,
            bbox=dict(fc="white", ec="#555", lw=0.5, pad=0.5))
    # C1 drawn as an electrolytic can beside its two legs (a straight bar here read like a 12 V-to-GND short)
    from matplotlib.patches import Circle as _Circle
    (x20, yh), (x21, _) = xy("h20"), xy("h21")
    can_x, can_y = 18.55, (ypos["h"] + ypos["i"]) / 2
    for xl in (x20, x21):
        ax.plot([can_x + (0.18 if xl == x21 else -0.05), xl], [can_y, yh], color="#777", lw=1.2, zorder=7)
    ax.add_patch(_Circle((can_x, can_y), 0.42, fc="#1f5fbf", ec="#111", lw=0.8, zorder=8))
    ax.add_patch(Rectangle((can_x + 0.12, can_y - 0.36), 0.16, 0.72, fc="#d9e2f2", ec="none", zorder=8.5))   # minus stripe
    ax.text(can_x - 0.12, can_y, "C1", fontsize=6.5, color="white", ha="center", va="center", zorder=9, weight="bold")
    ax.plot([x20, x21], [yh, yh], "o", ms=4.0, color="#1f5fbf", mec="#111", mew=0.5, zorder=8, ls="none")
    ax.text(x20 - 0.05, yh + 0.42, "+", fontsize=9, weight="bold", color="#c2352b", ha="center", va="bottom", zorder=9)
    ax.text(x21 + 0.05, yh + 0.42, "-", fontsize=10, weight="bold", color="#2459b8", ha="center", va="bottom", zorder=9)
    ax.text(17.9, can_y, "C1 100 uF capacitor:\n+ leg h20 (12 V row)\n- leg h21 (GND row)\nnot a wire", fontsize=6.6,
            ha="right", va="center", zorder=9, bbox=dict(fc="white", ec="#1f5fbf", lw=0.6, pad=0.6))
    # wires
    rail_row = {"b21": 21, "b22": 22, "b23": 23, "a24": 24, "a25": 25, "j6": 6, "j7": 7, "j26": 26, "j21": 21.4, "j27": 27.4,
                "j34": 34, "j35": 35}
    bends = {("c8", "c20"): 0.55, ("c6", "c26"): 1.0, ("c7", "c27"): 1.45, ("j20", "j36"): -1.15}
    for a, b, lab, colr in WIRES:
        if a in RAILS and b in RAILS:
            continue
        lead(a, b, lab if a[0] == "c" or "12 V" in lab else "", colr, lw=2.2 if "12 V" in lab else 2.0,
             row_b=rail_row.get(a), bend=bends.get((a, b), 0.0))
    # rail bridges at row 40 (drawing) = the board's far end
    ax.plot([RMAX + 0.4, RMAX + 0.4], [rail_y["T+"], rail_y["B+"]], color="#ff7f0e", lw=2)
    ax.plot([RMAX + 0.7, RMAX + 0.7], [rail_y["T-"], rail_y["B-"]], color="#222222", lw=2)
    ax.text(RMAX + 0.9, 4.2, "bridge\n+ to +\n- to -", fontsize=7.5, va="center")
    lead("j29", "i5", "JP1 wire: plug in ONLY with USB unplugged", "#d62728", lw=1.8, ls="--", bend=-2.3)
    for h, t in (("j22", "2B"), ("j23", "2A"), ("j24", "1A"), ("j25", "1B")):
        x, y = xy(h); ax.plot(x, y, "D", ms=6, mfc="#e9c46a", mec="#111", zorder=9)
        ax.text(x, y - 0.42, t, fontsize=6.5, ha="center", va="top", zorder=9, weight="bold")
    for h, t, c in (("i20", "+12 in", "#c2352b"), ("i21", "GND in", "#111")):
        x, y = xy(h); ax.plot(x, y, "D", ms=6, mfc=c, mec="#111", zorder=9)
    # off-board connections
    ax.annotate("12 V IN + (red, from WAGO) -> i20", xy=xy("i20"), xytext=(13.5, -5.6), fontsize=8, color="#c2352b",
                arrowprops=dict(arrowstyle="->", color="#c2352b"), weight="bold")
    ax.annotate("12 V IN - (black) -> i21", xy=xy("i21"), xytext=(22.5, -5.6), fontsize=8, arrowprops=dict(arrowstyle="->"))
    ax.annotate("MOTOR 2B 2A 1A 1B -> j22..j25\n(never unplug with power on)", xy=xy("j23"), xytext=(27.5, -6.6), fontsize=8,
                arrowprops=dict(arrowstyle="->"))
    # AS5600 encoder board (J5), drawn off the board above the top rail, with its four wires and the DIR-to-GND link
    ex0, ey0, ew, eh = 26.4, 13.3, 7.6, 2.0
    ax.add_patch(FancyBboxPatch((ex0, ey0), ew, eh, boxstyle="round,pad=0.05", fc="#5b2a86", ec="#111", zorder=6))
    ax.add_patch(_Circle((ex0 + ew / 2, ey0 + eh / 2 + 0.25), 0.38, fc="#222", ec="#999", zorder=6.5))   # the chip under the magnet
    ax.text(ex0 + ew / 2, ey0 + eh - 0.3, "AS5600 encoder (J5), at the spool", color="white", fontsize=7.5, weight="bold",
            ha="center", va="center", zorder=7)
    epin = {}
    for i, name in enumerate(("VCC", "GND", "DIR", "SCL", "SDA", "OUT", "GPO")):
        px = ex0 + 0.6 + i * 1.07
        epin[name] = px
        ax.add_patch(Rectangle((px - 0.17, ey0 - 0.32), 0.34, 0.32, fc="#d4af37", ec="#111", zorder=6.5))
        ax.text(px, ey0 + 0.25, name, color="white", fontsize=6.3, weight="bold", ha="center", va="bottom", zorder=7)
    py = ey0 - 0.32

    def enc_wire(pin, hole, colr, row=None, drop=0.0):
        """Encoder pin straight down, across above the rails, then down into its hole."""
        hx, hy = xy(hole, row)
        x0 = epin[pin]
        yy = rail_y["T+"] + 0.75 + drop
        ax.plot([x0, x0, hx, hx], [py, yy, yy, hy], color=colr, lw=2.2, zorder=7.5, solid_capstyle="round")
        ax.plot(hx, hy, "o", ms=6, mfc=colr, mec="#111", zorder=9)
    enc_wire("VCC", "T+", "#ff7f0e", row=27)
    enc_wire("GND", "T-", "#222222", row=28, drop=-0.25)
    enc_wire("SCL", "a10", "#7f7f7f", drop=0.45)
    enc_wire("SDA", "a9", "#e377c2", drop=0.15)
    for hole, lab, colr in (("a9", "ENC SDA", "#e377c2"), ("a10", "ENC SCL", "#7f7f7f")):
        hx, hy = xy(hole)
        left = hole == "a9"
        ax.text(hx + (-0.4 if left else 0.4), hy, lab, fontsize=6.3, weight="bold", color=colr,
                ha="right" if left else "left", va="center", zorder=10, bbox=dict(fc="white", ec=colr, lw=0.5, pad=0.3))
    # DIR tied to the board's own GND pin (a short link on the encoder board)
    ax.plot([epin["DIR"], epin["DIR"], epin["GND"], epin["GND"]], [py, py - 0.35, py - 0.35, py], color="#222222", lw=1.6,
            ls=(0, (2, 1.2)), zorder=7.6)
    for name in ("OUT", "GPO"):
        ax.text(epin[name], py - 0.35, "nc", fontsize=6, ha="center", va="top", color="#555", zorder=7)
    ax.text(ex0 + ew + 0.3, ey0 + eh / 2,
            "SDA (pink) -> a9: meets XIAO D4 SDA at d9\nSCL (grey) -> a10: meets XIAO D5 SCL at d10\nVCC -> T+ (3V3),  GND -> T-\n"
            "DIR -> GND (dashed link): must not float\nOUT, GPO: leave unconnected\nPin order differs between boards: read YOUR silkscreen",
            fontsize=6.8, ha="left", va="center", zorder=7, bbox=dict(fc="#f3ecfa", ec="#5b2a86", lw=0.6, pad=0.6))
    # KW12-3 homing microswitch, drawn off the board with its three terminals and the two wires that go to the board
    sx0, sy0, sw, sh = 0.6, -7.9, 5.4, 1.5                      # body (drawing units: 1 = one breadboard row)
    ax.add_patch(FancyBboxPatch((sx0, sy0), sw, sh, boxstyle="round,pad=0.05", fc="#2b2b2b", ec="#111", zorder=6))
    ax.text(sx0 + sw / 2, sy0 + sh / 2 + 0.15, "KW12-3 homing switch", color="white", fontsize=7.5, weight="bold",
            ha="center", va="center", zorder=7)
    ax.text(sx0 + sw / 2, sy0 + sh / 2 - 0.35, "(off the board, at the pulley)", color="#dddddd", fontsize=6.3,
            ha="center", va="center", zorder=7)
    ax.plot([sx0 + 0.4, sx0 + sw - 0.3], [sy0 + sh + 0.05, sy0 + sh + 0.55], color="#9a9a9a", lw=2.2, zorder=6)   # lever
    ax.add_patch(_Circle((sx0 + sw - 0.3, sy0 + sh + 0.6), 0.22, fc="#cfcfcf", ec="#555", zorder=6.5))            # roller
    ax.text(sx0 + 0.35, sy0 + sh + 0.62, "lever (the bead pushes it)", fontsize=6.3, ha="left", va="bottom", zorder=7)
    term = {"C (COM)": sx0 + 0.9, "NO": sx0 + 2.7, "NC": sx0 + 4.5}
    ty = sy0 - 0.05
    for name, tx in term.items():
        ax.add_patch(Rectangle((tx - 0.18, ty - 0.55), 0.36, 0.55, fc="#d4af37", ec="#111", zorder=6.5))
        ax.text(tx + 0.28, ty - 0.45, name, fontsize=7, weight="bold", ha="left", va="center", zorder=7)
    ax.text(term["NO"] + 0.28, ty - 1.0, "(leave empty)", fontsize=6.3, ha="left", va="center", color="#555", zorder=7)
    # NC -> i8 (HOME net: XIAO D10 at h8, R4 pull-up at j8)
    xi8, yi8 = xy("i8")
    ax.plot([term["NC"], term["NC"], xi8, xi8], [ty - 0.55, ty - 1.9, ty - 1.9, yi8], color="#8c564b", lw=2.2, zorder=6,
            solid_capstyle="round")
    ax.plot(xi8, yi8, "o", ms=6.5, mfc="#8c564b", mec="#111", zorder=9)
    ax.text(xi8 + 0.25, -5.1, "NC wire -> i8\n(row 8 = XIAO D10 HOME;\nR4 pull-up is j8)", fontsize=6.8, color="#8c564b", weight="bold",
            ha="left", va="center", zorder=9, bbox=dict(fc="white", ec="#8c564b", lw=0.6, pad=0.5))
    # COM -> bottom GND rail, row 1 (routed round the left of the switch body)
    xg, yg = xy("B-", 1)
    ax.plot([term["C (COM)"], term["C (COM)"], sx0 - 0.45, sx0 - 0.45, xg, xg],
            [ty - 0.55, ty - 1.55, ty - 1.55, yg - 0.8, yg - 0.8, yg], color="#222222", lw=2.2, zorder=6, solid_capstyle="round")
    ax.plot(xg, yg, "o", ms=6.5, mfc="#222222", mec="#111", zorder=9)
    ax.text(sx0 - 0.7, -5.6, "COM wire ->\nB- (GND rail)", fontsize=6.8, weight="bold", ha="right", va="center", zorder=9,
            bbox=dict(fc="white", ec="#222", lw=0.6, pad=0.5))
    ax.text(sx0 + sw + 0.3, sy0 + 0.35, "Read C / NO / NC printed on YOUR switch; the order can differ.\n"
            "NC is used on purpose: at rest NC-COM is closed, so D10 reads LOW; the bead opens it and R4 pulls D10 HIGH.\n"
            "A broken wire also reads HIGH = STOP (fail-safe). Check with a meter: NC-COM beeps at rest, opens when pressed.",
            fontsize=6.8, ha="left", va="center", zorder=7, bbox=dict(fc="#fffbe8", ec="#bbb", lw=0.5, pad=0.6))
    ax.text(12.0, -9.9, "12 V is ONLY in row 20 (f-j) and the red wire j20 -> j36.  Both + rails are 3V3, both - rails are GND.",
            fontsize=9, color="#c2352b", weight="bold")
    ax.set_xlim(-6, RMAX + 3.5); ax.set_ylim(-10.6, 16.2); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("RoomCleaner winch station Rev D on a breadboard (full-size 830). Same nets as the perfboard and KiCad schematic.",
                 fontsize=11, loc="left")
    for ext in ("png", "pdf"):
        fig.savefig(HERE / f"breadboard_layout.{ext}", dpi=170, bbox_inches="tight")


if __name__ == "__main__":
    ok = check()
    draw()
    sys.exit(0 if ok else 1)
