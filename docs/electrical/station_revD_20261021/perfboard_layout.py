"""
Perfboard layout for one winch station on a 5x7 cm isolated-pad board
(24 columns A-X, 18 rows 01-18, 2.54 mm pitch). Rev D schematic nets.

Viewed from the COMPONENT side. Bare = tinned wire / solder bridge on the
bottom; insulated = hookup wire on the bottom (crossings are fine).

    /usr/bin/python3 docs/electrical/station_revD_20261021/perfboard_layout.py
Writes perfboard_layout.png / .pdf next to this file and checks that every
hole belongs to exactly one net and every net is connected.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle

OUT = Path(__file__).resolve().parent
COLS = "ABCDEFGHIJKLMNOPQRSTUVWX"


def h(s):            # "C09" -> (col index 0.., row 1..)
    return COLS.index(s[0]), int(s[1:])


# ---------------- component pins: hole -> (net, label)
PINS = {}
def pin(hole, net, label):
    assert hole not in PINS, hole
    PINS[hole] = (net, label)

# U2 XIAO ESP32-C3, USB pointing LEFT off the board edge
for c, (net, lab) in zip("BCDEFGH", [("5V", "5V"), ("GND", "GND"), ("3V3", "3V3"), ("HOME", "D10"),
                                     ("nc", "D9"), ("nc", "D8"), ("nc", "D7")]):
    pin(f"{c}03", net, lab)
for c, (net, lab) in zip("BCDEFGH", [("nc", "D0"), ("STEP", "D1"), ("DIR", "D2"), ("EN", "D3"),
                                     ("SDA", "D4"), ("SCL", "D5"), ("nc", "D6")]):
    pin(f"{c}09", net, lab)
# U3 A4988 carrier, chip + pot facing UP, EN/VMOT at the top
for r, (net, lab) in enumerate([("EN", "EN"), ("GND", "MS1"), ("GND", "MS2"), ("GND", "MS3"),
                                ("3V3", "RST"), ("3V3", "SLP"), ("STEP", "STEP"), ("DIR", "DIR")], start=3):
    pin(f"L{r:02d}", net, lab)
for r, (net, lab) in enumerate([("12V", "VMOT"), ("PGND", "GND"), ("M2B", "2B"), ("M2A", "2A"),
                                ("M1A", "1A"), ("M1B", "1B"), ("3V3", "VDD"), ("GND", "GND")], start=3):
    pin(f"Q{r:02d}", net, lab)
# connectors
pin("X01", "12V", "+12"); pin("X03", "PGND", "GND")                         # J1 power in
for r, n in zip((5, 6, 7, 8), ("M2B", "M2A", "M1A", "M1B")): pin(f"X{r:02d}", n, n[1:])   # J2 motor
pin("C17", "3V3", "3V3"); pin("D17", "GND", "GND"); pin("E17", "SDA", "SDA"); pin("F17", "SCL", "SCL")  # J5 encoder
pin("H17", "HOME", "NC"); pin("I17", "GND", "COM")                           # J3 switch
pin("B01", "5V", "JP1"); pin("C01", "5VD", "JP1")                            # JP1 link
pin("D01", "5VD", "K"); pin("H01", "5VB", "A")                              # D1 1N5819 (stripe = K)
pin("I01", "5VB", "BUCK OUT+")                                               # buck output wire
pin("W01", "12V", "buck IN+"); pin("W03", "PGND", "buck IN-")                # buck input wires
pin("T02", "12V", "C1 +"); pin("T03", "PGND", "C1 -")                        # C1 100uF/50V
pin("C10", "STEP", "R2"); pin("C11", "GND", "R2")                            # R2 STEP pull-down
pin("D10", "DIR", "R3"); pin("D11", "GND", "R3")                             # R3 DIR pull-down
pin("E10", "EN", "R1"); pin("E13", "3V3", "R1")                              # R1 EN pull-up
pin("H16", "HOME", "R4"); pin("H13", "3V3", "R4")                            # R4 HOME pull-up

# ---------------- bare runs (bottom side) and insulated wires
BARE = []
def run(a, b, net):                 # straight run along a row or column
    (ca, ra), (cb, rb) = h(a), h(b)
    assert ca == cb or ra == rb, (a, b)
    BARE.append((a, b, net))
run("B01", "B03", "5V"); run("C01", "D01", "5VD"); run("H01", "I01", "5VB")
run("Q01", "X01", "12V"); run("Q01", "Q03", "12V"); run("T01", "T02", "12V")
run("Q04", "R04", "PGND"); run("R03", "R04", "PGND"); run("R03", "X03", "PGND")
for r in (5, 6, 7, 8): run(f"Q{r:02d}", f"X{r:02d}", ["M2B", "M2A", "M1A", "M1B"][r - 5])
run("C09", "C10", "STEP"); run("D09", "D10", "DIR"); run("E09", "E10", "EN")
run("B11", "P11", "GND"); run("B13", "P13", "3V3"); run("C13", "C17", "3V3")
run("L07", "L08", "3V3"); run("L04", "L06", "GND"); run("H16", "H17", "HOME")

WIRES = [  # insulated: (from, to, net, colour)
    ("C09", "L09", "STEP", "#d62728"), ("D09", "L10", "DIR", "#ff7f0e"), ("E09", "L03", "EN", "#9467bd"),
    ("F09", "E17", "SDA", "#2ca02c"), ("G09", "F17", "SCL", "#17becf"), ("E03", "H17", "HOME", "#8c564b"),
    ("C03", "B11", "GND", "#222222"), ("D03", "B13", "3V3", "#1f77b4"), ("Q09", "P13", "3V3", "#1f77b4"),
    ("Q10", "P11", "GND", "#222222"), ("L08", "L13", "3V3", "#1f77b4"), ("L06", "K11", "GND", "#222222"),
    ("D17", "D11", "GND", "#222222"), ("I17", "I11", "GND", "#222222"), ("S03", "O11", "GND", "#222222"),
]

# ---------------- checks: one net per hole, every net connected
NETMAP = {"PGND": "GND"}                     # power and logic ground are one net (tied by S03-O11)
hole_net = {k: NETMAP.get(v[0], v[0]) for k, v in PINS.items()}
def claim(hole, net):
    net = NETMAP.get(net, net)
    if hole_net.get(hole, net) != net:
        raise SystemExit(f"CONFLICT at {hole}: {hole_net[hole]} vs {net}")
    hole_net[hole] = net
def holes_on(a, b):
    (ca, ra), (cb, rb) = h(a), h(b)
    if ra == rb:
        return [f"{COLS[c]}{ra:02d}" for c in range(min(ca, cb), max(ca, cb) + 1)]
    return [f"{COLS[ca]}{r:02d}" for r in range(min(ra, rb), max(ra, rb) + 1)]
for a, b, net in BARE:
    for x in holes_on(a, b): claim(x, net)
for a, b, net, _ in WIRES:
    claim(a, net); claim(b, net)
parent = {}
def find(x):
    parent.setdefault(x, x)
    while parent[x] != x: x = parent[x]
    return x
def union(a, b): parent[find(a)] = find(b)
for a, b, _ in BARE:
    hs = holes_on(a, b)
    for x, y in zip(hs, hs[1:]): union(x, y)
for a, b, *_ in WIRES: union(a, b)
union("S03", "O11")
groups = {}
for hole, net in hole_net.items():
    if net == "nc": continue
    groups.setdefault(NETMAP.get(net, net), set()).add(find(hole))
bad = {n: len(g) for n, g in groups.items() if len(g) > 1 and n not in ("5VD", "5VB")}
# 5V/5VD/5VB are joined through JP1 and the diode by design
if bad: raise SystemExit(f"UNCONNECTED nets: {bad}")
print("check OK:", len(hole_net), "holes used,", len(groups), "nets, each connected")

# ---------------- drawing
P = 1.0
fig, ax = plt.subplots(figsize=(17, 13))
ax.set_aspect("equal"); ax.axis("off")
X = lambda c: c * P; Y = lambda r: -r * P
ax.add_patch(Rectangle((-1.4, -19.3), 26.8, 19.1, fc="#1f7a3a", ec="#0f4d22", lw=2, zorder=0))
for c in range(24):
    ax.text(X(c), Y(-0.1), COLS[c], ha="center", va="center", color="white", fontsize=11, weight="bold")
    ax.text(X(c), Y(18.9), COLS[c], ha="center", va="center", color="white", fontsize=11, weight="bold")
for r in range(1, 19):
    ax.text(X(-1.0), Y(r), f"{r:02d}", ha="center", va="center", color="white", fontsize=10)
    ax.text(X(24.0), Y(r), f"{r:02d}", ha="center", va="center", color="white", fontsize=10)
    for c in range(24):
        ax.add_patch(Circle((X(c), Y(r)), 0.30, fc="#c9c9c9", ec="#8a8a8a", lw=0.6, zorder=1))
        ax.add_patch(Circle((X(c), Y(r)), 0.11, fc="#1f7a3a", ec="none", zorder=1.1))
# modules
def module(c0, r0, c1, r1, title, fc):
    ax.add_patch(FancyBboxPatch((X(c0) - 0.55, Y(r1) - 0.55), X(c1) - X(c0) + 1.1, Y(r0) - Y(r1) + 1.1,
                                boxstyle="round,pad=0.05", fc=fc, ec="black", lw=1.5, alpha=0.30, zorder=2))
    ax.text((X(c0) + X(c1)) / 2, (Y(r0) + Y(r1)) / 2, title, ha="center", va="center", fontsize=13,
            weight="bold", zorder=6)
module(1, 3, 7, 9, "XIAO ESP32-C3\n(USB points LEFT\noff the edge)", "#4a90d9")
module(11, 3, 16, 10, "A4988\n(chip + pot UP,\nEN & VMOT at top)", "#d94a4a")
ax.annotate("USB", xy=(X(-0.6), Y(6)), xytext=(X(-2.6), Y(6)), fontsize=11, weight="bold", va="center",
            arrowprops=dict(arrowstyle="<-", lw=2), annotation_clip=False)
# bare runs
for a, b, net in BARE:
    (ca, ra), (cb, rb) = h(a), h(b)
    col = {"12V": "#b30000", "PGND": "#333333", "GND": "#333333", "3V3": "#1f5fa8"}.get(net, "#e6e6e6")
    ax.plot([X(ca), X(cb)], [Y(ra), Y(rb)], color=col, lw=7, solid_capstyle="round", alpha=0.85, zorder=3)
# insulated wires drawn as gentle arcs
import numpy as np
for a, b, net, colr in WIRES:
    (ca, ra), (cb, rb) = h(a), h(b)
    xa, ya, xb, yb = X(ca), Y(ra), X(cb), Y(rb)
    mx, my = (xa + xb) / 2, (ya + yb) / 2
    dx, dy = xb - xa, yb - ya
    L = max(np.hypot(dx, dy), 1e-6); bend = 0.12 * L
    cx, cy = mx - dy / L * bend, my + dx / L * bend
    t = np.linspace(0, 1, 40)
    px = (1 - t) ** 2 * xa + 2 * (1 - t) * t * cx + t ** 2 * xb
    py = (1 - t) ** 2 * ya + 2 * (1 - t) * t * cy + t ** 2 * yb
    ax.plot(px, py, color=colr, lw=2.6, zorder=4, alpha=0.95)
# parts on top
def two_lead(a, b, label, fc, text_off=(0.4, 0)):
    (ca, ra), (cb, rb) = h(a), h(b)
    ax.plot([X(ca), X(cb)], [Y(ra), Y(rb)], color="#555", lw=2, zorder=5)
    mx, my = (X(ca) + X(cb)) / 2, (Y(ra) + Y(rb)) / 2
    ax.add_patch(FancyBboxPatch((mx - 0.35, my - 0.35), 0.7, 0.7, boxstyle="round,pad=0.05", fc=fc,
                                ec="black", zorder=5))
    ax.text(mx + text_off[0], my + text_off[1], label, fontsize=10, weight="bold", zorder=6,
            ha="left", va="center", color="white" if fc == "#000000" else "black")
two_lead("C10", "C11", "", "#f2d16b"); two_lead("D10", "D11", "", "#f2d16b"); two_lead("E10", "E13", "", "#f2d16b")
two_lead("H13", "H16", "", "#f2d16b")
for lab, (c, r) in {"R2": (2.0, 10.5), "R3": (3.0, 10.5), "R1": (4.3, 11.9), "R4": (7.3, 14.6)}.items():
    ax.text(X(c), Y(r), lab, fontsize=9.5, weight="bold", ha="center", va="center", zorder=7,
            bbox=dict(fc="white", ec="none", pad=0.5))
(cd, rd), (ca_, ra_) = h("D01"), h("H01")
ax.add_patch(Rectangle((X(cd) + 0.4, Y(rd) - 0.32), X(ca_) - X(cd) - 0.8, 0.64, fc="#111", ec="black", zorder=5))
ax.add_patch(Rectangle((X(cd) + 0.4, Y(rd) - 0.32), 0.35, 0.64, fc="#dddddd", ec="black", zorder=5.1))
ax.text((X(cd) + X(ca_)) / 2 + 0.3, Y(rd), "D1 1N5819  stripe ->JP1", color="white", fontsize=8.5,
        ha="center", va="center", zorder=6)
ax.add_patch(Circle(((X(19)), (Y(2.5))), 0.95, fc="#2b3a8c", ec="black", zorder=5, alpha=0.9))
ax.text(X(19), Y(2.5), "C1\n100uF", color="white", fontsize=8, ha="center", va="center", zorder=6)
ax.text(X(19.9), Y(2.0), "+", color="white", fontsize=12, weight="bold", zorder=6)
for hole, (net, lab) in PINS.items():
    c, r = h(hole)
    if lab in ("R1", "R2", "R3", "R4", "C1 +", "C1 -", "K", "A", "JP1", "buck IN+", "buck IN-", "+12", "GND") and not (c <= 7 or c in (11, 16)):
        ax.add_patch(Circle((X(c), Y(r)), 0.30, fc="#ffd400", ec="black", lw=0.8, zorder=4.5)); continue
    if c in (1, 2, 3, 4, 5, 6, 7) and r in (3, 9) or c in (11, 16) and 3 <= r <= 10:
        off = {3: 0.55, 9: -0.55}.get(r, 0) if c <= 7 else 0
        dxl = -0.62 if c == 11 else (0.62 if c == 16 else 0)
        ax.text(X(c) + dxl, Y(r) + off, lab, fontsize=8.5, weight="bold", ha="center", va="center", zorder=7,
                bbox=dict(fc="white", ec="none", pad=0.4, alpha=0.9))
    elif lab not in ("BUCK OUT+",):
        ax.text(X(c) + 0.38, Y(r) + 0.36, lab, fontsize=8.5, weight="bold", ha="left", va="bottom", zorder=7,
                color="white")
    ax.add_patch(Circle((X(c), Y(r)), 0.30, fc="#ffd400", ec="black", lw=0.8, zorder=4.5))
ax.text(X(22), Y(1.0) - 0.75, "buck IN+", color="white", fontsize=8.5, weight="bold", ha="center", zorder=7)
ax.text(X(22), Y(3.0) + 0.55, "buck IN-", color="white", fontsize=8.5, weight="bold", ha="center", zorder=7)
ax.text(X(8), Y(1.0) + 0.55, "BUCK OUT+", color="white", fontsize=8.5, weight="bold", ha="center", zorder=7)
# connector outlines
for (a, b, name) in [("X01", "X03", "J1 12V IN"), ("X05", "X08", "J2 MOTOR"), ("C17", "F17", "J5 ENCODER"),
                     ("H17", "I17", "J3 SWITCH"), ("B01", "C01", "JP1")]:
    (ca, ra), (cb, rb) = h(a), h(b)
    ax.add_patch(Rectangle((min(X(ca), X(cb)) - 0.45, min(Y(ra), Y(rb)) - 0.45), abs(X(cb) - X(ca)) + 0.9,
                           abs(Y(rb) - Y(ra)) + 0.9, fc="none", ec="white", lw=2, ls="--", zorder=5))
    tx = (X(ca) + X(cb)) / 2; ty = min(Y(ra), Y(rb)) - 0.85
    if name.startswith("J1"):
        tx, ty = X(ca) - 2.2, Y(ra) - 1.0
    if name.startswith("J2"):
        tx, ty = X(ca) - 1.6, (Y(ra) + Y(rb)) / 2
    ax.text(tx, ty, name, color="white", fontsize=10, weight="bold", ha="center", va="center", zorder=7)
ax.text(X(17.3), Y(11.0), "<- GND bus (row 11)", color="white", fontsize=9.5, weight="bold", zorder=7)
ax.text(X(17.3), Y(13.0), "<- 3V3 bus (row 13)", color="white", fontsize=9.5, weight="bold", va="center", zorder=7)
ax.text(X(17.2), Y(1.0) + 0.45, "+12V", color="white", fontsize=9.5, weight="bold", zorder=7)
ax.text(X(19.6), Y(3.0) - 0.45, "GND (motor return)", color="white", fontsize=9, weight="bold", va="top", zorder=7)
ax.text(X(20.3), Y(9.5), "1B 1A pair = coil 1\n2A 2B pair = coil 2", color="white", fontsize=9, zorder=7)
ax.text(-1.2, -20.2, "COMPONENT SIDE VIEW. Thick grey/red/blue = bare wire or solder run on the bottom. "
        "Thin coloured = insulated wire on the bottom (crossings OK). Yellow = soldered hole.",
        fontsize=10.5, ha="left", va="top")
ax.text(-1.2, -21.0, "Match module pin LABELS to the holes before soldering headers: XIAO 5V at B03, D0 at B09; "
        "A4988 EN at L03, VMOT at Q03, DIR at L10.", fontsize=10.5, weight="bold", ha="left", va="top",
        color="#aa0000")
ax.set_xlim(-3.2, 25.2); ax.set_ylim(-21.6, 1.3)
fig.savefig(OUT / "perfboard_layout.png", dpi=150, bbox_inches="tight")
fig.savefig(OUT / "perfboard_layout.pdf", bbox_inches="tight")
print("wrote", OUT / "perfboard_layout.png")
