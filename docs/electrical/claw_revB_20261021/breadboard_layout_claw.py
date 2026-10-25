"""Claw Rev B on a solderless breadboard (full-size 830-point board, rows 1-30 used), net-checked.

Same circuit as CLAW_REVB_SPEC.md and the KiCad schematic (kicad/): the check at the bottom builds the
breadboard's connectivity (row strips a-e and f-j, the rails, every part pin, jumper and off-board joint) and
compares it pin by pin with kicad/claw_spec.py. It prints PASS only if every net matches and no two nets touch.

Board convention (same as the station layouts):
  rows run left to right; columns a-e are the top half, f-j the bottom half (trench between e and f);
  T+ / T- are the rails along the top edge, B+ / B- along the bottom edge.
  Only ONE rail is used: B- = GND. T+, T- and B+ stay empty. No battery voltage and no 6 V is on any rail.

Off the board (the high-current pack side): the battery, fuse, switch and charger, joined by two lever nuts
(WAGO 1 = VBAT after the switch, WAGO 2 = GND). The UBEC and MP1584 inputs go straight to those WAGOs, so the
servo's input current never runs through the breadboard.

    python3 breadboard_layout_claw.py      # writes breadboard_layout_claw.png/.pdf, prints the net check
"""
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kicad"))
sys.dont_write_bytecode = True
from claw_spec import PIN_NUMBER, expected  # noqa: E402

TOP, BOT = "abcde", "fghij"
RAILS = ("T+", "T-", "B+", "B-")
UNUSED_RAILS = ("T+", "T-", "B+")


def P(ref, word):
    """(ref, pin number) from the spec's pin word, e.g. P("U3", "D0") -> ("U3", "1")."""
    return ref, PIN_NUMBER[ref][word]


# ---------------------------------------------------------------- placement: (ref, pin) -> hole or off-board joint
# XIAO ESP32-S3 straddles the trench, USB-C toward row 1 (off the board's end): D0..D6 on column d rows 3..9,
# 5V, GND, 3V3, D10, D9, D8, D7 on column h rows 3..9 (Seeed pad order, as the station XIAO).
PLACE = {}
for i, w in enumerate(["D0", "D1", "D2", "D3", "D4", "D5", "D6"]):
    PLACE[P("U3", w)] = f"d{3 + i}"
for i, w in enumerate(["5V", "GND", "3V3", "D10", "D9", "D8", "D7"]):
    PLACE[P("U3", w)] = f"h{3 + i}"
PLACE.update({
    # XIAO 5 V supply: D1 stripe (cathode) in the 5V row, C3 right at the 5V / GND pads
    P("D1", "cathode"): "j3", P("D1", "anode"): "i11",
    ("C3", "1"): "i3", ("C3", "2"): "i4",
    # MP1584 buck (off the board): output leads into row 11 and the GND rail, input leads to the WAGOs
    P("U2", "OUT+"): "j11", P("U2", "OUT-"): "B-", P("U2", "IN+"): "X:VBAT_SW", P("U2", "IN-"): "X:GND",
    # battery sense: R1 200k from the VBAT row 18 to row 14, R2 100k and C4 from row 14 to GND
    P("R1", "top"): "h18", P("R1", "bottom"): "h14",
    P("R2", "top"): "j14", P("R2", "bottom"): "B-",
    ("C4", "1"): "i14", ("C4", "2"): "B-",
    # servo: J2 3-pin header f22 GND, f23 V+, f24 signal; C1 / C2 across rows 22-23; UBEC output into row 23 and GND
    P("J2", "GND"): "f22", P("J2", "V+"): "f23", P("J2", "signal"): "f24",
    ("C2", "1"): "g23", ("C2", "2"): "g22",
    P("C1", "+"): "h23", P("C1", "-"): "h22",
    P("U1", "OUT+"): "j23", P("U1", "OUT-"): "B-", P("U1", "IN+"): "X:VBAT_SW", P("U1", "IN-"): "X:GND",
    # pack side, all off the board
    P("BT1", "+"): "X:BAT_POS", P("BT1", "-"): "X:GND",
    P("F1", "in"): "X:BAT_POS", P("F1", "out"): "X:BAT_FUSED",
    P("SW1", "in"): "X:BAT_FUSED", P("SW1", "out"): "X:VBAT_SW",
    P("U4", "B+"): "X:BAT_FUSED", P("U4", "B-"): "X:GND",
})
# ---------------------------------------------------------------- jumper wires: (from, to, label, colour)
WIRES = [
    ("c3", "g24", "D0 servo PWM", "#e67e22"),
    ("c5", "g14", "D2 battery sense", "#8e44ad"),
    ("j4", "B-", "XIAO GND", "#222222"),
    ("j22", "B-", "servo GND", "#222222"),
    ("X:VBAT_SW", "j18", "VBAT (7-8.4 V) to row 18", "#d62728"),
    ("X:GND", "B-", "battery GND to B-", "#222222"),
]
BODIES = {   # parts that cover holes: (label, col_from, col_to, row_from, row_to)
    "U3": ("XIAO ESP32-S3 Sense\n(USB-C toward row 1)", "d", "h", 2.4, 9.6),
}


def is_hole(h):
    return h not in RAILS and not h.startswith("X:")


def strip_of(hole):
    if not is_hole(hole):
        return hole
    col, row = hole[0], int(hole[1:])
    return f"{'top' if col in TOP else 'bot'}{row}"


def check():
    nets, nc = expected()
    pin_net = {k: n for n, keys in nets.items() for k in keys}
    pin_net.update({k: None for k in nc})
    missing = set(pin_net) - set(PLACE)
    extra = set(PLACE) - set(pin_net)
    assert not missing and not extra, f"placement incomplete: missing {sorted(missing)} extra {sorted(extra)}"
    cols = "abcdefghij"
    for ref, (_, c0, c1, r0, r1) in BODIES.items():
        used = [h for (rf, _), h in PLACE.items() if rf != ref and is_hole(h)] + [h for w in WIRES for h in w[:2] if is_hole(h)]
        for h in used:
            if cols.index(c0) <= cols.index(h[0]) <= cols.index(c1) and r0 < int(h[1:]) < r1:
                raise SystemExit(f"hole {h} is under {ref}'s body")
    holes = [h for h in PLACE.values() if is_hole(h)] + [h for w in WIRES for h in w[:2] if is_hole(h)]
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
    for keys in groups.values():
        gn = {pin_net[k] for k in keys if pin_net[k] is not None}
        ncs = [k for k in keys if pin_net[k] is None]
        if len(gn) > 1 or (ncs and (gn or len(keys) > 1)):
            print(f"FAIL short: {sorted(keys)} -> nets {gn} no-connects {ncs}")
            ok = False
        for n in gn:
            got.setdefault(n, set()).update(keys)
    for net, keys in nets.items():
        if got.get(net) != keys:
            print(f"FAIL net {net}: spec {sorted(keys)} breadboard {sorted(got.get(net, set()))}")
            ok = False
    used_rails = {h for h in PLACE.values() if h in RAILS} | {h for w in WIRES for h in w[:2] if h in RAILS}
    if used_rails & set(UNUSED_RAILS):
        print(f"FAIL: something on a rail that must stay empty: {sorted(used_rails & set(UNUSED_RAILS))}"); ok = False
    if find("B-") != find(strip_of(PLACE[P("U3", "GND")])):
        print("FAIL: B- is not GND"); ok = False
    print(f"{len(nets)} nets, {sum(len(v) for v in nets.values())} connected pins, {len(nc)} no-connects, "
          f"{len(WIRES)} jumpers/leads")
    print("PASS" if ok else "FAIL")
    return ok


def draw():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as pe
    import numpy as np
    from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

    cols = "abcdefghij"
    ypos = {c: 9.5 - i - (1.6 if c in BOT else 0) for i, c in enumerate(cols)}
    rail_y = {"T+": 11.6, "T-": 10.9, "B+": -2.9, "B-": -3.6}
    RMAX = 30
    halo = [pe.Stroke(linewidth=4.6, foreground="white"), pe.Normal()]

    def xy(hole, row_hint=None):
        if hole in RAILS:
            return (row_hint, rail_y[hole])
        return (int(hole[1:]), ypos[hole[0]])

    fig, ax = plt.subplots(figsize=(16, 13.5))
    ax.add_patch(Rectangle((0.2, -4.2), RMAX + 0.6, 16.5, fc="#f4f2ea", ec="#bdb9a8"))
    ax.add_patch(Rectangle((0.2, 3.6), RMAX + 0.6, 1.4, fc="#e4e1d4", ec="none"))
    for r in range(1, RMAX + 1):
        for c in cols:
            ax.plot(r, ypos[c], "s", ms=4.6, mfc="#ffffff", mec="#9a978a", mew=0.6, zorder=1)
        if r % 5 == 0 or r == 1:
            ax.text(r, 10.25, str(r), ha="center", fontsize=7.5, color="#6b6a65")
            ax.text(r, -2.25, str(r), ha="center", fontsize=7.5, color="#6b6a65")
    for c in cols:
        ax.text(-0.4, ypos[c], c, ha="center", va="center", fontsize=9, color="#6b6a65")
    for rail, y in rail_y.items():
        col = "#c2352b" if "+" in rail else "#2459b8"
        used = rail == "B-"
        ax.plot([0.6, RMAX + 0.4], [y, y], color=col, lw=1.0, alpha=.5 if used else .2)
        for r in range(1, RMAX + 1):
            ax.plot(r, y, "s", ms=3.8, mfc="#ffffff", mec=col, mew=0.6, zorder=1, alpha=1 if used else .4)
        ax.text(-0.6, y, f"{rail}  ({'GND' if used else 'not used'})", ha="right", va="center", fontsize=9, color=col,
                weight="bold" if used else "normal", alpha=1 if used else .6)
    # XIAO body and pin names
    names = {"1": "D0 SERVO", "2": "D1 nc", "3": "D2 VBAT", "4": "D3 nc", "5": "D4 nc", "6": "D5 nc", "7": "D6 nc",
             "8": "D7 nc", "9": "D8 nc", "10": "D9 nc", "11": "D10 nc", "12": "3V3 nc", "13": "GND", "14": "5V in"}
    for ref, (lab, c0, c1, r0, r1) in BODIES.items():
        y0, y1 = ypos[c1] - 0.45, ypos[c0] + 0.45
        ax.add_patch(FancyBboxPatch((r0, y0), r1 - r0, y1 - y0, boxstyle="round,pad=0.05", fc="#1d3557", ec="#111", alpha=.9, zorder=3))
        ax.text((r0 + r1) / 2, (y0 + y1) / 2 + 0.05, "U3 XIAO ESP32-S3 Sense\nUSB-C toward row 1", ha="center", va="center", color="white",
                fontsize=6.4, weight="bold", zorder=4, linespacing=1.0)
    for (ref, pin), hole in PLACE.items():
        if ref == "U3":
            x, y = xy(hole)
            used = "nc" not in names[pin]
            ax.plot(x, y, "o", ms=5.5, mfc="#ffd166" if used else "#cfcfcf", mec="#111", zorder=5)
            top = hole[0] == "d"
            ax.text(x, y + (-0.4 if top else 0.4), names[pin], rotation=90, ha="center", va="top" if top else "bottom",
                    fontsize=6.2, zorder=6, color="#ffd166" if used else "#aab4c3", weight="bold" if used else "normal")
    ax.annotate("USB-C (laptop) for flashing\nand the Serial Monitor", xy=(2.4, (ypos["d"] + ypos["h"]) / 2), xytext=(-5.6, 5.6),
                fontsize=7.5, arrowprops=dict(arrowstyle="->", color="#555"), color="#333")

    def lead(a, b, label, colr, lw=2.4, row_a=None, row_b=None, z=7, bend=0.0, lab_t=20, fs=6.8):
        xa, ya = xy(a, row_a); xb, yb = xy(b, row_b)
        t = np.linspace(0, 1, 41)
        cx, cy = (xa + xb) / 2, (ya + yb) / 2 + bend
        X = (1 - t) ** 2 * xa + 2 * (1 - t) * t * cx + t ** 2 * xb
        Y = (1 - t) ** 2 * ya + 2 * (1 - t) * t * cy + t ** 2 * yb
        ax.plot(X, Y, color=colr, lw=lw, solid_capstyle="round", zorder=z, path_effects=halo)
        ax.plot([xa, xb], [ya, yb], "o", ms=4.2, color=colr, mec="#111", mew=0.5, zorder=z + 1, ls="none")
        if label:
            ax.text(X[lab_t], Y[lab_t], label, fontsize=fs, ha="center", va="center", zorder=z + 2,
                    bbox=dict(fc="white", ec=colr, lw=0.6, pad=0.5, alpha=.95))

    # parts on the board
    lead("j3", "i11", "", "#555555", lw=4.2, bend=-0.35)
    ax.text(7, ypos["j"] - 0.75, "D1 1N5819: stripe at j3 (5V row),\nplain end at i11 (buck row)", fontsize=6.6, ha="center",
            va="top", zorder=9, bbox=dict(fc="white", ec="#555", lw=0.5, pad=0.5))
    lead("i3", "i4", "", "#c9a227", lw=3.2, z=8)
    ax.text(3.5, ypos["i"] - 0.2, "C3", fontsize=6.4, ha="center", weight="bold", zorder=9, color="#7a5c00")
    lead("h14", "h18", "R1 200k", "#8c564b", lab_t=20)
    lead("j14", "B-", "R2 100k", "#8c564b", row_b=14, lab_t=18)
    lead("i14", "B-", "C4", "#c9a227", row_b=15.4, lw=2.0, lab_t=36)
    lead("g22", "g23", "", "#c9a227", lw=3.2, z=8)
    ax.text(22.5, ypos["g"] + 0.45, "C2", fontsize=6.4, ha="center", weight="bold", zorder=9, color="#7a5c00")
    # C1 electrolytic can between its legs h22 (-) and h23 (+)
    (x22, yh), (x23, _) = xy("h22"), xy("h23")
    can_x, can_y = 25.6, yh - 0.1
    for xl in (x22, x23):
        ax.plot([can_x - 0.4, xl], [can_y, yh], color="#777", lw=1.2, zorder=7)
    ax.add_patch(Circle((can_x, can_y), 0.5, fc="#1f5fbf", ec="#111", lw=0.8, zorder=8))
    ax.add_patch(Rectangle((can_x - 0.12, can_y - 0.44), 0.18, 0.88, fc="#d9e2f2", ec="none", zorder=8.5))
    ax.plot([x22, x23], [yh, yh], "o", ms=4.2, color="#1f5fbf", mec="#111", mew=0.5, zorder=8, ls="none")
    ax.text(x22, yh - 0.2, "-", fontsize=10, weight="bold", color="#2459b8", ha="center", va="top", zorder=9)
    ax.text(x23, yh - 0.2, "+", fontsize=9, weight="bold", color="#c2352b", ha="center", va="top", zorder=9)
    ax.text(26.3, can_y + 0.05, "C1 1000 uF:\n+ leg h23 (6 V row)\n- leg h22 (GND row)", fontsize=6.5, ha="left", va="center",
            zorder=9, bbox=dict(fc="white", ec="#1f5fbf", lw=0.6, pad=0.5))
    # jumpers
    lead("c3", "g24", "XIAO D0 -> servo signal", "#e67e22", bend=4.2, lab_t=22)
    lead("c5", "g14", "XIAO D2 -> sense row 14", "#8e44ad", bend=2.2, lab_t=22)
    lead("j4", "B-", "", "#222222", row_b=4)
    lead("j22", "B-", "", "#222222", row_b=22)
    # J2 servo header f22-f24 and the MG996R lead coming in from above the board
    for h, c in (("f22", "#6b3e1f"), ("f23", "#d62728"), ("f24", "#e67e22")):
        x, y = xy(h)
        ax.plot([x, x], [y, 13.3], color=c, lw=2.6, zorder=6.5, path_effects=halo)
        ax.plot(x, y, "s", ms=7, mfc="#e9c46a", mec="#111", zorder=9)
    ax.add_patch(FancyBboxPatch((17.4, 13.3), 11.2, 1.5, boxstyle="round,pad=0.05", fc="#222", ec="#111", zorder=7))
    ax.text(23, 14.05, "J2: MG996R servo lead\nbrown GND f22, red V+ f23, orange signal f24", color="white", fontsize=7,
            weight="bold", ha="center", va="center", zorder=8)
    ax.text(28.9, 14.05, "plugs onto a 3-pin male header\nin f22-f24 (check YOUR lead's colours)", fontsize=6.6,
            ha="left", va="center", zorder=8)
    # module and pack-side drawing below the board
    VB, GB = -10.6, -13.2            # WAGO 1 (VBAT_SW) and WAGO 2 (GND), drawn as bus bars

    def wire(pts, colr, lw=2.4, z=6):
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=colr, lw=lw, zorder=z, solid_capstyle="round", path_effects=halo)

    def dot(x, y, colr):
        ax.plot(x, y, "o", ms=6.5, mfc=colr, mec="#111", zorder=9)

    def module(x0, w, label, sub, fc):
        ax.add_patch(FancyBboxPatch((x0, -7.9), w, 1.5, boxstyle="round,pad=0.05", fc=fc, ec="#111", zorder=7))
        ax.text(x0 + w / 2, -7.15, label + "\n" + sub, color="white", fontsize=7, weight="bold", ha="center", va="center", zorder=8)

    # U2 MP1584 (5.00 V): OUT+ -> j11, OUT- -> B- row 12, IN+ / IN- down to the WAGOs
    module(8.4, 4.6, "U2 MP1584 buck", "set 5.00 V first", "#3d3d3d")
    wire([(11, -6.4), xy("j11")], "#ff7f0e"); dot(*xy("j11"), "#ff7f0e")
    wire([(12, -6.4), xy("B-", 12)], "#222222"); dot(*xy("B-", 12), "#222222")
    ax.text(10.85, -5.0, "OUT+\n-> j11", fontsize=6.4, ha="right", color="#b35900", weight="bold", zorder=9)
    ax.text(12.15, -5.0, "OUT-\n-> B-", fontsize=6.4, ha="left", color="#222", weight="bold", zorder=9)
    wire([(9.2, -7.9), (9.2, VB)], "#d62728"); dot(9.2, VB, "#d62728")
    wire([(10.0, -7.9), (10.0, GB)], "#222222"); dot(10.0, GB, "#222222")
    ax.text(9.1, -8.4, "IN+", fontsize=6.3, ha="right", color="#d62728", weight="bold", zorder=9)
    ax.text(10.1, -8.4, "IN-", fontsize=6.3, ha="left", weight="bold", zorder=9)
    # U1 ZTW UBEC (6.0 V): OUT+ -> j23, OUT- -> B- row 25, IN+ / IN- to the WAGOs
    module(20.4, 5.2, "U1 ZTW UBEC", "jumper set to 6.0 V", "#7a1f1f")
    wire([(23, -6.4), xy("j23")], "#d62728"); dot(*xy("j23"), "#d62728")
    wire([(25, -6.4), xy("B-", 25)], "#222222"); dot(*xy("B-", 25), "#222222")
    ax.text(22.85, -5.0, "OUT+ 6 V\n-> j23", fontsize=6.4, ha="right", color="#d62728", weight="bold", zorder=9)
    ax.text(25.15, -5.0, "OUT-\n-> B-", fontsize=6.4, ha="left", weight="bold", zorder=9)
    wire([(21.2, -7.9), (21.2, VB)], "#d62728"); dot(21.2, VB, "#d62728")
    wire([(22.0, -7.9), (22.0, GB)], "#222222"); dot(22.0, GB, "#222222")
    ax.text(21.1, -8.4, "IN+", fontsize=6.3, ha="right", color="#d62728", weight="bold", zorder=9)
    ax.text(22.1, -8.4, "IN-", fontsize=6.3, ha="left", weight="bold", zorder=9)
    # VBAT lead to j18 and battery GND lead to B- row 16
    wire([(18, VB), xy("j18")], "#d62728", lw=2.0); dot(18, VB, "#d62728"); dot(*xy("j18"), "#d62728")
    ax.text(18.2, -5.4, "VBAT lead\n-> j18 (R1 top)", fontsize=6.4, ha="left", color="#d62728", weight="bold", zorder=9,
            bbox=dict(fc="white", ec="none", pad=0.3, alpha=.9))
    wire([(16, GB), xy("B-", 16)], "#222222"); dot(16, GB, "#222222"); dot(*xy("B-", 16), "#222222")
    ax.text(15.8, -5.4, "GND lead\n-> B-", fontsize=6.4, ha="right", weight="bold", zorder=9,
            bbox=dict(fc="white", ec="none", pad=0.3, alpha=.9))
    # bus bars = the two lever nuts
    wire([(7.6, VB), (27, VB)], "#d62728", lw=5, z=5)
    wire([(1.4, GB), (27, GB)], "#222222", lw=5, z=5)
    ax.text(27.3, VB, "WAGO 1: VBAT after SW1 (7.0-8.4 V)\nSW1 out, UBEC IN+, buck IN+, VBAT lead", fontsize=7, va="center",
            color="#d62728", weight="bold")
    ax.text(27.3, GB, "WAGO 2: GND\nbattery -, charger B-, UBEC IN-, buck IN-, GND lead", fontsize=7, va="center", weight="bold")
    # pack side: BT1 -> F1 -> (charger B+) -> SW1 -> WAGO 1
    ax.add_patch(FancyBboxPatch((0.3, -12.4), 2.4, 1.0, boxstyle="round,pad=0.05", fc="#2a7f62", ec="#111", zorder=7))
    ax.text(1.5, -11.9, "BT1 2S pack\n7.4 V", color="white", fontsize=6.8, weight="bold", ha="center", va="center", zorder=8)
    wire([(1.5, -11.4), (1.5, VB), (2.8, VB)], "#d62728")
    wire([(1.4, -12.4), (1.4, GB)], "#222222")
    ax.add_patch(Rectangle((2.8, VB - 0.25), 1.4, 0.5, fc="#f1c40f", ec="#111", zorder=7))
    ax.text(3.5, VB + 0.45, "F1 5 A", fontsize=6.8, ha="center", weight="bold", zorder=8)
    wire([(4.2, VB), (5.9, VB)], "#d62728"); dot(5.2, VB, "#d62728")
    ax.add_patch(Rectangle((5.9, VB - 0.3), 1.5, 0.6, fc="#555", ec="#111", zorder=7))
    ax.text(6.65, VB + 0.5, "SW1", fontsize=6.8, ha="center", weight="bold", zorder=8)
    wire([(7.4, VB), (7.6, VB)], "#d62728")
    ax.add_patch(FancyBboxPatch((3.6, -12.6), 3.4, 1.2, boxstyle="round,pad=0.05", fc="#34495e", ec="#111", zorder=7))
    ax.text(5.3, -12.0, "U4 USB-C 2S charger\nB+ / B- (8.4 V, <= 1 A)", color="white", fontsize=6.2, weight="bold",
            ha="center", va="center", zorder=8)
    wire([(5.2, -11.4), (5.2, VB)], "#d62728", lw=1.8)
    wire([(6.2, -12.6), (6.2, GB)], "#222222", lw=1.8)
    ax.text(0.3, -14.2, "Pack side, all OFF the board (solder or lever nuts, 18-20 AWG): BT1 + -> F1 -> SW1 -> WAGO 1.  "
            "The charger's B+ joins between F1 and SW1,\nso it charges with SW1 OFF (the only way to charge).  Battery -, "
            "charger B- and both module IN- go to WAGO 2.", fontsize=7.4, va="top")
    # notes
    ax.text(0.3, -15.9,
            "Rails: only B- (bottom blue) is used, as GND.  T+, T- and B+ stay EMPTY: no 7.4 V and no 6 V is on any rail.\n"
            "7.4-8.4 V is only in WAGO 1 and row 18 (f-j).  6 V is only in row 23 (f-j).  5 V is only in rows 11 and 3 (f-j, through D1).\n"
            "Servo current (up to ~2.5 A stalled) runs through rows 22-23 only: fine for bench travel tests, but do not hold a stall\n"
            "for more than a second on the breadboard.  The claw itself gets soldered.",
            fontsize=7.6, va="top", color="#c2352b", weight="bold")
    ax.set_xlim(-6.2, RMAX + 12); ax.set_ylim(-18.6, 15.4); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("RoomCleaner claw Rev B on a breadboard (full-size 830, rows 1-30). Same nets as CLAW_REVB_SPEC.md and the KiCad schematic.",
                 fontsize=11, loc="left")
    for ext in ("png", "pdf"):
        fig.savefig(HERE / f"breadboard_layout_claw.{ext}", dpi=170, bbox_inches="tight")


if __name__ == "__main__":
    ok = check()
    draw()
    sys.exit(0 if ok else 1)
