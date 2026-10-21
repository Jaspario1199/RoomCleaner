"""Junction ("rail") board for one winch station: the modules stay separate and are wired to this 5x7 cm perfboard,
which only joins the rails and carries the four pull resistors, the 5 V diode and the JP1 link.

    /usr/bin/python3 docs/electrical/station_revD_20261021/rail_board_layout.py
Writes rail_board_layout.png / .pdf next to this file. The check compares every wire against the Rev D connectivity
in perfboard_layout.py (the soldered, net-checked board): each module pin must land on the island of its own net,
islands must not touch, and every Rev D module pin must be either on this board or in the direct-wire list.

Board: 24 columns A-X along the long edge, 18 rows 01-18, component side up. Rails and islands are bare tinned wire
(or solder runs) on the bottom; module wires come in from the component side and are soldered in the named hole.
"""
import contextlib
import io
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parent
COLS = "ABCDEFGHIJKLMNOPQRSTUVWX"


def h(s):
    return COLS.index(s[0]), int(s[1:])


def holes_on(a, b):
    (ca, ra), (cb, rb) = h(a), h(b)
    assert ca == cb or ra == rb, (a, b)
    if ra == rb:
        return [f"{COLS[c]}{ra:02d}" for c in range(min(ca, cb), max(ca, cb) + 1)]
    return [f"{COLS[ca]}{r:02d}" for r in range(min(ra, rb), max(ra, rb) + 1)]


# ---------------- islands: bare runs on the bottom.  name -> (net, [runs])
ISLANDS = {
    "+12 V":        ("12V",  [("B01", "K01")]),
    "GND (power)":  ("PGND", [("B03", "X03")]),
    "ground tie":   ("GND",  [("X04", "X06")]),          # joins the two grounds at ONE point (X03-X07)
    "GND (logic)":  ("GND",  [("B07", "X07")]),
    "STEP":         ("STEP", [("B11", "E11")]),
    "DIR":          ("DIR",  [("G11", "J11")]),
    "EN":           ("EN",   [("L11", "O11")]),
    "HOME":         ("HOME", [("Q11", "T11")]),
    "3V3":          ("3V3",  [("B15", "T15")]),
    "5 V from buck": ("5VB", [("N17", "O17")]),
    "after diode":  ("5VD",  [("S17", "T17")]),
    "XIAO 5 V":     ("5V",   [("U17", "W17")]),
}
# ---------------- module wires landing on the board: hole -> (module pin, Rev D net)
TAPS = {
    "B01": ("Supply +12 V in", "12V"), "E01": ("A4988 VMOT", "12V"), "H01": ("Buck IN+", "12V"),
    "B03": ("Supply - (GND) in", "PGND"), "E03": ("A4988 GND, VMOT side", "PGND"), "H03": ("Buck IN-", "PGND"),
    "K03": ("Buck OUT-", "PGND"),
    "B07": ("XIAO GND", "GND"), "G07": ("A4988 GND, logic side", "GND"), "L07": ("A4988 MS1", "GND"),
    "M07": ("A4988 MS2", "GND"), "N07": ("A4988 MS3", "GND"), "Q07": ("Encoder GND", "GND"),
    "S07": ("Switch COM", "GND"),
    "B11": ("XIAO D1", "STEP"), "C11": ("A4988 STEP", "STEP"),
    "G11": ("XIAO D2", "DIR"), "H11": ("A4988 DIR", "DIR"),
    "L11": ("XIAO D3", "EN"), "M11": ("A4988 EN", "EN"),
    "Q11": ("XIAO D10", "HOME"), "R11": ("Switch NC", "HOME"),
    "B15": ("XIAO 3V3", "3V3"), "E15": ("A4988 VDD", "3V3"), "G15": ("A4988 RST", "3V3"), "H15": ("A4988 SLP", "3V3"),
    "J15": ("Encoder VCC", "3V3"),
    "N17": ("Buck OUT+", "5VB"), "W17": ("XIAO 5V", "5V"),
}
# ---------------- parts on the board: (ref, hole a, hole b, net a, net b)
PARTS = [
    ("R2 10k", "E11", "E07", "STEP", "GND"), ("R3 10k", "J11", "J07", "DIR", "GND"),
    ("R1 10k", "O11", "O15", "EN", "3V3"), ("R4 10k", "T11", "T15", "HOME", "3V3"),
    ("D1 1N5819", "O17", "S17", "5VB", "5VD"),          # anode O17, stripe (cathode) S17
    ("JP1", "T17", "U17", "5VD", "5V"),
]
# ---------------- wires that do NOT go through this board: (from, to, Rev D net)
DIRECT = [
    ("XIAO D4", "Encoder SDA", "SDA"), ("XIAO D5", "Encoder SCL", "SCL"),
    ("A4988 1A", "Motor 1A", "M1A"), ("A4988 1B", "Motor 1B", "M1B"),
    ("A4988 2A", "Motor 2A", "M2A"), ("A4988 2B", "Motor 2B", "M2B"),
    ("C1 + (100 uF)", "A4988 VMOT pin", "12V"), ("C1 - (stripe)", "A4988 GND pin, VMOT side", "PGND"),
]


# ---------------- Rev D connectivity, read from the soldered board's file (its table part only)
def revd_pins():
    src = (OUT / "perfboard_layout.py").read_text()
    code = src.split("# ---------------- drawing")[0]
    env = {"__file__": str(OUT / "perfboard_layout.py"), "__name__": "revd"}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(code, "perfboard_layout.py", "exec"), env)
    pins = env["PINS"]
    exp = {}
    for hole, (net, lab) in pins.items():
        c, r = h(hole)
        if 1 <= c <= 7 and r in (3, 9):
            exp[f"XIAO {lab}"] = net
        elif c == 11 and 3 <= r <= 10:
            exp[f"A4988 {lab}"] = net
        elif c == 16 and 3 <= r <= 10:
            exp[f"A4988 {lab}" + (", VMOT side" if r == 4 else ", logic side" if r == 10 else "")] = net
    exp.update({"Supply +12 V in": "12V", "Supply - (GND) in": "PGND", "Buck IN+": "12V", "Buck IN-": "PGND",
                "Buck OUT-": "PGND", "Buck OUT+": "5VB", "Encoder VCC": "3V3", "Encoder GND": "GND",
                "Encoder SDA": "SDA", "Encoder SCL": "SCL", "Switch NC": "HOME", "Switch COM": "GND",
                "Motor 1A": "M1A", "Motor 1B": "M1B", "Motor 2A": "M2A", "Motor 2B": "M2B"})
    # sanity: the module-side entries above agree with the soldered board's pins
    lab_net = {(lab, net) for net, lab in pins.values()}
    for lab, net in (("+12", "12V"), ("IN+", "12V"), ("IN-", "PGND"), ("OUT-", "PGND"), ("OUT+", "5VB"),
                     ("NC", "HOME"), ("COM", "GND"), ("SDA", "SDA"), ("SCL", "SCL")):
        assert (lab, net) in lab_net, (lab, net)
    return exp


def check():
    exp = revd_pins()
    hole_island = {}
    for name, (net, runs) in ISLANDS.items():
        for a, b in runs:
            for x in holes_on(a, b):
                assert x not in hole_island, f"{x} is on two islands"
                hole_island[x] = name
    island_net = {n: v[0] for n, v in ISLANDS.items()}
    merged = {"PGND": "GND"}                                    # power and logic ground are one net, tied once
    # the tie: X04-X06 bare plus the two rail ends X03 / X07 make one vertical run
    assert {"X03", "X07"} <= set(hole_island) and hole_island["X03"] == "GND (power)" and hole_island["X07"] == "GND (logic)"
    used = set()
    for hole, (mpin, net) in TAPS.items():
        isl = hole_island.get(hole)
        assert isl, f"{hole} ({mpin}) is not on any island"
        assert island_net[isl] == net, f"{hole} {mpin}: island {isl} is {island_net[isl]}, wire is {net}"
        assert exp.get(mpin) == net, f"{mpin}: Rev D says {exp.get(mpin)}, board puts it on {net}"
        assert hole not in used, hole
        used.add(hole)
    for ref, a, b, na, nb in PARTS:
        for x, n in ((a, na), (b, nb)):
            assert x not in used, f"{ref} lead {x} shares a hole with a wire"
            assert island_net[hole_island[x]] == n, f"{ref} {x}: expected {n}"
            used.add(x)
    for a, b, net in DIRECT:
        for p in (a, b):
            if p in exp:
                assert merged.get(exp[p], exp[p]) == merged.get(net, net), f"direct wire {a}-{b}: {p} is {exp[p]}"
    # coverage: every Rev D module pin (not nc) is on the board or in a direct wire
    on_board = {m for m, _ in TAPS.values()}
    direct = {p for a, b, _ in DIRECT for p in (a, b)}
    missing = [p for p, n in exp.items() if n != "nc" and p not in on_board and p not in direct]
    assert not missing, f"Rev D pins not wired: {missing}"
    # resistor / diode functions match Rev D (R1 EN pull-up, R2 STEP and R3 DIR pull-downs, R4 HOME pull-up)
    want = {("STEP", "GND"), ("DIR", "GND"), ("EN", "3V3"), ("HOME", "3V3"), ("5VB", "5VD"), ("5VD", "5V")}
    assert {(na, nb) for _, _, _, na, nb in PARTS} == want
    print(f"check OK: {len(TAPS)} wires on the board, {len(DIRECT)} direct wires, {len(PARTS)} parts, "
          f"{len(ISLANDS)} islands; every Rev D module pin accounted for")
    return hole_island


SHORT = {"Supply +12 V in": "Supply +12 V", "Supply - (GND) in": "Supply GND", "A4988 GND, VMOT side": "A4988 GND by VMOT",
         "A4988 GND, logic side": "A4988 GND by VDD"}


def draw(hole_island):
    fig, ax = plt.subplots(figsize=(17, 14))
    ax.set_aspect("equal"); ax.axis("off")
    X = lambda c: float(c); Y = lambda r: -float(r)
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
    colour = {"12V": "#c00000", "PGND": "#222222", "GND": "#555555", "3V3": "#1f5fa8", "5VB": "#e377c2",
              "5VD": "#e377c2", "5V": "#e377c2"}
    for name, (net, runs) in ISLANDS.items():
        for a, b in runs:
            (ca, ra), (cb, rb) = h(a), h(b)
            ax.plot([X(ca), X(cb)], [Y(ra), Y(rb)], color=colour.get(net, "#e8e8e8"), lw=8, solid_capstyle="round",
                    alpha=0.9, zorder=3)
    ax.plot([X(23), X(23)], [Y(3), Y(7)], color="#333333", lw=8, solid_capstyle="round", zorder=3)
    # rail / island names
    names = {"+12 V": ("L01", "+12 V rail"), "GND (power)": ("P03", "GND power rail (motor + buck return)"),
             "GND (logic)": ("T07", "GND logic rail"), "3V3": ("U15", "3V3 rail"),
             "STEP": ("D11", "STEP"), "DIR": ("I11", "DIR"), "EN": ("N11", "EN"), "HOME": ("S11", "HOME")}
    for isl, (hole, text) in names.items():
        c, r = h(hole)
        if isl in ("STEP", "DIR", "EN", "HOME"):
            ax.text(X(c), Y(r), text, color="white", fontsize=9.5, weight="bold", ha="center", va="center", zorder=7,
                    bbox=dict(fc="#333333", ec="none", pad=0.3))
        else:
            ax.text(X(c), Y(r) + 0.45, text, color="white", fontsize=11, weight="bold", ha="left", va="bottom", zorder=7)
    ax.text(X(22.6), Y(5.0), "single\nground\ntie", color="white", fontsize=9, weight="bold", ha="right", va="center", zorder=7)
    # parts
    for ref, a, b, *_ in PARTS:
        (ca, ra), (cb, rb) = h(a), h(b)
        ax.plot([X(ca), X(cb)], [Y(ra), Y(rb)], color="#666", lw=2.2, zorder=5)
        mx, my = (X(ca) + X(cb)) / 2, (Y(ra) + Y(rb)) / 2
        if ref.startswith("D1"):
            ax.add_patch(Rectangle((X(ca) + 0.5, my - 0.3), X(cb) - X(ca) - 1.0, 0.6, fc="#111", ec="black", zorder=5))
            ax.add_patch(Rectangle((X(cb) - 0.85, my - 0.3), 0.3, 0.6, fc="#dddddd", ec="black", zorder=5.1))
            ax.text(mx - 0.2, my, "D1 1N5819", color="white", fontsize=8.5, ha="center", va="center", zorder=6)
            ax.text(X(cb) - 0.7, my + 0.45, "stripe", color="white", fontsize=8, ha="center", va="bottom", zorder=6)
        elif ref == "JP1":
            ax.add_patch(Rectangle((X(ca) - 0.42, my - 0.42), X(cb) - X(ca) + 0.84, 0.84, fc="none", ec="white", lw=2, ls="--", zorder=5))
            ax.text(mx, my - 0.6, "JP1: cap on only on 12 V,\noff when USB is plugged in", color="white", fontsize=8.5, ha="center", va="top", zorder=6)
        else:
            ax.add_patch(FancyBboxPatch((mx - 0.28, my - 0.75), 0.56, 1.5, boxstyle="round,pad=0.05", fc="#f2d16b", ec="black", zorder=5))
            ax.text(mx + 0.42, my, ref, fontsize=9.5, weight="bold", ha="left", va="center", zorder=7,
                    bbox=dict(fc="white", ec="none", pad=0.4))
        for x in (a, b):
            c, r = h(x)
            ax.add_patch(Circle((X(c), Y(r)), 0.30, fc="#ffd400", ec="black", lw=0.8, zorder=5.5))
    # module wires: yellow hole + label rotated, written into the gap rows
    below = {1: None, 3: 0.55, 7: 0.55, 11: 0.55, 15: 0.55, 17: 0.55}
    for hole, (mpin, net) in TAPS.items():
        c, r = h(hole)
        ax.add_patch(Circle((X(c), Y(r)), 0.30, fc="#ffd400", ec="black", lw=0.8, zorder=6))
        mpin = SHORT.get(mpin, mpin)
        if hole == "N17":
            ax.text(X(c) - 0.45, Y(r), mpin + " in", fontsize=9, weight="bold", ha="right", va="center", zorder=7,
                    bbox=dict(fc="white", ec="none", pad=0.25, alpha=0.95))
            continue
        if hole == "W17":
            ax.text(X(c), Y(r) + 0.55, mpin, rotation=90, fontsize=9, weight="bold", ha="center", va="bottom", zorder=7,
                    bbox=dict(fc="white", ec="none", pad=0.25, alpha=0.95))
            continue
        if r == 1:
            ax.text(X(c), Y(r) + 0.55, mpin, rotation=90, fontsize=9, weight="bold", ha="center", va="bottom", zorder=7,
                    color="black", bbox=dict(fc="white", ec="none", pad=0.25, alpha=0.95))
        else:
            ax.text(X(c), Y(r) - below[r], mpin, rotation=90, fontsize=9, weight="bold", ha="center", va="top", zorder=7,
                    color="black", bbox=dict(fc="white", ec="none", pad=0.25, alpha=0.95))
    ax.text(-1.2, -20.1, "COMPONENT SIDE VIEW of a 5 x 7 cm perfboard (24 x 18 holes). Thick lines = bare wire / solder run on the "
            "bottom (rails and islands). Yellow = a hole you solder: a module wire (white label) or a part lead.",
            fontsize=10.5, ha="left", va="top")
    ax.text(-1.2, -20.8, "NOT on this board: XIAO D4 -> encoder SDA, XIAO D5 -> encoder SCL, A4988 1A/1B/2A/2B -> motor, and C1 100 uF "
            "soldered straight across the A4988 VMOT and GND pins (+ to VMOT).", fontsize=10.5, weight="bold", ha="left",
            va="top", color="#aa0000")
    ax.set_xlim(-2.0, 25.6); ax.set_ylim(-21.4, 4.6)
    fig.savefig(OUT / "rail_board_layout.png", dpi=150, bbox_inches="tight")
    fig.savefig(OUT / "rail_board_layout.pdf", bbox_inches="tight")
    print("wrote", OUT / "rail_board_layout.png")


if __name__ == "__main__":
    draw(check())
