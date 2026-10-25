"""Claw Rev B: everything OFF the breadboard, wire by wire (battery, fuse, switch, charger, lever nuts, UBEC, MP1584).

Companion to breadboard_layout_claw.py. Every wire is drawn end to end; wires that go to the breadboard end in a tag
naming the hole. The check at the bottom joins the wire list below and compares the result with kicad/claw_spec.py
(breadboard holes count as the net the breadboard layout gives them). It prints PASS only on an exact match.

    /usr/bin/python3 offboard_wiring_claw.py      # writes offboard_wiring_claw.png/.pdf, prints the check
"""
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kicad"))
sys.dont_write_bytecode = True
from claw_spec import PIN_NUMBER, expected  # noqa: E402

# breadboard landing points and the net the breadboard layout puts there (breadboard_layout_claw.py)
BOARD_NET = {"BB:j11": "+5V_BUCK", "BB:j23": "+6V_SERVO", "BB:j18": "VBAT_SW", "BB:B-": "GND"}

# every off-board wire: (end A, end B). Ends are "REF word" part pins, lever-nut slots "W1.3", or breadboard "BB:..".
WIRES = [
    ("BT1 +", "F1 in"),            # pack + lead into the fuse holder
    ("F1 out", "W3.1"),            # fuse holder out -> 3-way lever nut
    ("U4 B+", "W3.2"),             # charger B+ -> 3-way lever nut
    ("SW1 in", "W3.3"),            # switch input -> 3-way lever nut
    ("SW1 out", "W1.1"),
    ("U2 IN+", "W1.2"),
    ("U1 IN+", "W1.3"),
    ("BB:j18", "W1.4"),            # VBAT sense lead to the breadboard
    ("U4 B-", "W2.1"),
    ("BT1 -", "W2.2"),
    ("U2 IN-", "W2.3"),
    ("U1 IN-", "W2.4"),
    ("BB:B-", "W2.5"),             # GND lead to the breadboard
    ("U2 OUT+", "BB:j11"),
    ("U2 OUT-", "BB:B-"),
    ("U1 OUT+", "BB:j23"),         # UBEC output plug, red hole
    ("U1 OUT-", "BB:B-"),          # UBEC output plug, black/brown hole
]
OFFBOARD_REFS = {"BT1", "F1", "SW1", "U4", "U1", "U2"}


def node(end):
    if end.startswith("W"):
        return end.split(".")[0]          # all slots of one lever nut are one node
    if end.startswith("BB:"):
        return "net:" + BOARD_NET[end]
    ref, word = end.split(" ", 1)
    return (ref, PIN_NUMBER[ref][word])


def check():
    nets, _ = expected()
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    slots = [e for w in WIRES for e in w if e.startswith("W")]
    assert len(slots) == len(set(slots)), "two wires in one lever-nut slot"
    for a, b in WIRES:
        parent[find(node(a))] = find(node(b))
    ok = True
    for net, keys in nets.items():
        off = {k for k in keys if k[0] in OFFBOARD_REFS}
        if not off:
            continue
        roots = {find(k) for k in off}
        board = {n for n in BOARD_NET.values() if find("net:" + n) in roots}
        if len(roots) != 1:
            print(f"FAIL net {net}: off-board pins split into {len(roots)} groups"); ok = False
        on_board = [k for k in keys if k[0] not in OFFBOARD_REFS]
        if on_board and board != {net}:
            print(f"FAIL net {net}: reaches the breadboard as {board or 'nothing'}"); ok = False
        if not on_board and board:
            print(f"FAIL net {net}: should stay off the board but reaches {board}"); ok = False
    # no two spec nets joined
    for n1 in nets:
        for n2 in nets:
            if n1 < n2:
                r1 = {find(k) for k in nets[n1] if k[0] in OFFBOARD_REFS} | ({find("net:" + n1)} if n1 in BOARD_NET.values() else set())
                r2 = {find(k) for k in nets[n2] if k[0] in OFFBOARD_REFS} | ({find("net:" + n2)} if n2 in BOARD_NET.values() else set())
                if r1 & r2:
                    print(f"FAIL short: {n1} and {n2}"); ok = False
    used = {(r, p) for a, b in WIRES for e in (a, b) if not e.startswith(("W", "BB:")) for r, p in [node(e)]}
    need = {k for keys in nets.values() for k in keys if k[0] in OFFBOARD_REFS}
    if used != need:
        print(f"FAIL pins: missing {sorted(need - used)} extra {sorted(used - need)}"); ok = False
    print(f"{len(WIRES)} off-board wires, {len(need)} module/pack pins, 3 lever nuts")
    print("PASS" if ok else "FAIL")
    return ok


def draw():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as pe
    from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

    RED, BLK, ORG = "#d62728", "#222222", "#e67e22"
    halo = [pe.Stroke(linewidth=5.6, foreground="white"), pe.Normal()]
    fig, ax = plt.subplots(figsize=(17, 12))

    def wire(pts, colr, lw=3.0, z=4):
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=colr, lw=lw, zorder=z, solid_capstyle="round", solid_joinstyle="round", path_effects=halo)

    def box(x, y, w, h, fc, text, fs=8.5, tc="white"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06", fc=fc, ec="#111", lw=1.0, zorder=6))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc, weight="bold", zorder=7)

    def pad(x, y, name, side="top", colr="#d4af37"):
        ax.add_patch(Rectangle((x - 0.17, y - 0.12), 0.34, 0.24, fc=colr, ec="#111", zorder=7.5))
        dy = {"top": 0.22, "bottom": -0.22}[side]
        ax.text(x, y + dy, name, ha="center", va="bottom" if side == "top" else "top", fontsize=7.2, weight="bold", zorder=8)

    def tag(x, y, text, colr, ha="left"):
        ax.annotate("", xy=(x + (0.55 if ha == "left" else -0.55), y), xytext=(x, y),
                    arrowprops=dict(arrowstyle="-|>", color=colr, lw=2), zorder=8)
        ax.text(x + (0.65 if ha == "left" else -0.65), y, text, ha=ha, va="center", fontsize=8.2, weight="bold", color=colr, zorder=8,
                bbox=dict(fc="white", ec=colr, lw=1.0, pad=0.35))

    def lever_nut(x, y, n, label, slot_labels, facing, colr):
        """A WAGO 221 drawn from above: n slots side by side; wires enter from `facing` ('down' or 'up')."""
        w = n * 1.2 + 0.2
        ax.add_patch(FancyBboxPatch((x, y), w, 1.3, boxstyle="round,pad=0.05", fc="#e9eef2", ec="#555", lw=1.2, zorder=6))
        xs = []
        for i in range(n):
            sx = x + 0.7 + i * 1.2
            xs.append(sx)
            ax.add_patch(Rectangle((sx - 0.38, y + (0.8 if facing == "down" else 0.15)), 0.76, 0.35, fc="#f39c12", ec="#7a4a00",
                                   zorder=6.5))       # orange lever
            ax.text(sx, y + 0.55 if facing == "down" else y + 0.95, str(i + 1), ha="center", va="center", fontsize=7.5, zorder=7,
                    color="#555")
            ey = y if facing == "down" else y + 1.3
            ax.add_patch(Circle((sx, ey), 0.13, fc="#333", ec="#111", zorder=7))
            if slot_labels[i]:
                pass
        ax.text(x + w + 0.25, y + 0.65, label, ha="left", va="center", fontsize=8.5, weight="bold", color=colr, zorder=7)
        return xs

    # ---------------- lever nuts
    W1y, W2y = 13.0, 0.6
    w1 = lever_nut(10.6, W1y, 5, "WAGO 1 (5-way): VBAT after the switch, 7.0-8.4 V\nslot 5 empty", [1] * 5, "down", RED)
    w2 = lever_nut(10.6, W2y, 5, "WAGO 2 (5-way): GND", [1] * 5, "up", BLK)
    # ---------------- pack chain: BT1 + -> F1 -> WAGO 3 -> SW1 -> WAGO 1 slot 1
    cy = 10.6
    box(0.2, 8.6, 2.6, 3.0, "#2a7f62", "BT1\nTenergy 2S\n7.4 V pack\n\n(its plug +\nmating lead)", fs=7.8)
    ax.text(2.95, 11.0, "+ red", fontsize=7.5, color=RED, weight="bold", ha="left", zorder=8)
    ax.text(1.75, 8.35, "- black", fontsize=7.5, weight="bold", ha="left", va="top", zorder=8)
    wire([(2.8, cy), (3.8, cy)], RED)
    ax.add_patch(FancyBboxPatch((3.8, cy - 0.32), 1.9, 0.64, boxstyle="round,pad=0.04", fc="#111", ec="#111", zorder=6))
    ax.add_patch(Rectangle((4.4, cy - 0.2), 0.7, 0.4, fc="#f1c40f", ec="#7a6000", zorder=6.5))
    ax.text(4.75, cy + 0.55, "F1 inline fuse holder\n5 A blade fuse", ha="center", va="bottom", fontsize=7.5, weight="bold", zorder=8)
    wire([(5.7, cy), (6.25, cy)], RED)
    # WAGO 3 (3-way) at the fuse / switch / charger joint, wires enter from the left... drawn small
    ax.add_patch(FancyBboxPatch((6.25, cy - 0.55), 1.1, 1.75, boxstyle="round,pad=0.04", fc="#e9eef2", ec="#555", lw=1.2, zorder=6))
    for i, yy in enumerate((cy - 0.25, cy + 0.3, cy + 0.85)):
        ax.add_patch(Rectangle((6.85, yy - 0.15), 0.38, 0.3, fc="#f39c12", ec="#7a4a00", zorder=6.5))
        ax.text(6.55, yy, str(i + 1), fontsize=6.8, ha="center", va="center", color="#555", zorder=7)
    ax.text(6.8, cy - 0.75, "WAGO 3\n(3-way)", ha="center", va="top", fontsize=7.5, weight="bold", color=RED, zorder=8)
    # fuse out enters slot 1 (drawn into the nut's left edge); switch in = slot 3; charger B+ = slot 2
    # SW1
    wire([(7.35, cy + 0.85), (8.2, cy + 0.85), (8.2, cy)], RED)
    ax.add_patch(FancyBboxPatch((8.2, cy - 0.4), 1.6, 0.8, boxstyle="round,pad=0.04", fc="#555", ec="#111", zorder=6))
    ax.add_patch(Rectangle((8.75, cy - 0.15), 0.5, 0.3, fc="#c0392b", ec="#111", zorder=6.5))
    ax.text(9.0, cy + 0.55, "SW1 power switch\n(2 terminals)", ha="center", va="bottom", fontsize=7.5, weight="bold", zorder=8)
    ax.text(8.25, cy - 0.55, "in", fontsize=7, ha="left", va="top", zorder=8)
    ax.text(9.75, cy - 0.55, "out", fontsize=7, ha="right", va="top", zorder=8)
    wire([(9.8, cy), (w1[0], cy), (w1[0], W1y)], RED)
    # U4 charger above, B+ down into WAGO 3 slot 2, B- around the left to WAGO 2 slot 1
    box(2.9, 14.2, 4.6, 1.5, "#34495e", "U4 USB-C 2S charger\n(8.4 V, <= 1 A)\nUSB-C in from a 5 V adapter", fs=7.3)
    pad(6.4, 14.2, "B+", side="bottom")
    pad(4.0, 14.2, "B-", side="bottom")
    wire([(6.4, 14.08), (6.4, 13.2), (7.7, 13.2), (7.7, cy + 0.3), (7.35, cy + 0.3)], RED, lw=2.4)
    wire([(4.0, 14.08), (4.0, 13.6), (-0.6, 13.6), (-0.6, 3.2), (w2[0], 3.2), (w2[0], W2y + 1.3)], BLK, lw=2.4)
    # BT1 - down to WAGO 2 slot 2
    wire([(1.5, 8.6), (1.5, 3.8), (w2[1], 3.8), (w2[1], W2y + 1.3)], BLK)
    # ---------------- U2 MP1584 between the nuts: IN+ up to WAGO 1 slot 2, IN- down to WAGO 2 slot 3
    box(11.4, 6.0, 3.6, 2.4, "#3d3d3d", "", fs=7.8)
    ax.text(13.0, 7.15, "U2 MP1584 buck\n(small blue board)\nset 5.00 V FIRST", ha="center", va="center", fontsize=7.2, color="white", weight="bold", zorder=7)
    pad(w1[1], 8.4, "IN+", side="bottom", colr="#e8c547")
    pad(w2[2], 6.0, "IN-", side="top", colr="#e8c547")
    wire([(w1[1], 8.52), (w1[1], W1y)], RED, lw=2.4)
    wire([(w2[2], 5.88), (w2[2], W2y + 1.3)], BLK, lw=2.4)
    ax.text(w1[1] - 0.2, 10.0, "solder a wire\nto each pad", fontsize=6.8, ha="right", va="center", zorder=8, color="#555")
    pad(15.0, 7.7, "", colr="#e8c547"); pad(15.0, 6.7, "", colr="#e8c547")
    ax.text(15.6, 7.95, "OUT+", fontsize=7, ha="center", va="bottom", weight="bold", color=ORG, zorder=8)
    ax.text(15.6, 6.45, "OUT-", fontsize=7, ha="center", va="top", weight="bold", zorder=8)
    wire([(15.17, 7.7), (16.0, 7.7)], ORG, lw=2.4)
    wire([(15.17, 6.7), (16.0, 6.7)], BLK, lw=2.4)
    tag(16.0, 7.7, "to j11", ORG)
    tag(16.0, 6.7, "to B- rail", BLK)
    # ---------------- U1 UBEC: IN+ to WAGO 1 slot 3, IN- to WAGO 2 slot 4, output plug to the board
    ux, uy, uw, uh = 20.6, 6.0, 4.0, 2.4
    box(ux, uy, uw, uh, "#7a1f1f", "U1 ZTW UBEC\n(in heat-shrink)", fs=8.2)
    # voltage jumper on the body
    ax.add_patch(Rectangle((ux + 1.3, uy + 0.25), 1.4, 0.45, fc="#111", ec="#aaa", zorder=7))
    for i in range(3):
        ax.add_patch(Circle((ux + 1.55 + i * 0.45, uy + 0.47), 0.09, fc="#d4af37", zorder=7.5))
    ax.add_patch(Rectangle((ux + 1.42, uy + 0.3), 0.6, 0.35, fc="#2980b9", ec="#111", zorder=7.6, alpha=.9))
    ax.text(ux + 2.0, uy - 0.25, "voltage jumper on the 6V position\n(read the label on YOUR UBEC)", fontsize=7, ha="center",
            va="top", color="#7a1f1f", weight="bold", zorder=8)
    # input wires come out of the left end
    wire([(ux, uy + 1.9), (ux - 0.6, uy + 1.9), (ux - 0.6, 11.6), (w1[2], 11.6), (w1[2], W1y)], RED)
    wire([(ux, uy + 1.1), (ux - 1.0, uy + 1.1), (ux - 1.0, 2.7), (w2[3], 2.7), (w2[3], W2y + 1.3)], BLK)
    ax.text(ux - 0.7, uy + 2.05, "IN+ red", fontsize=7.2, ha="right", va="bottom", color=RED, weight="bold", zorder=8)
    ax.text(ux - 1.1, uy + 0.95, "IN- black", fontsize=7.2, ha="right", va="top", weight="bold", zorder=8)
    # output lead and 3-hole plug on the right end
    wire([(ux + uw, uy + 1.2), (ux + uw + 0.8, uy + 1.2)], "#888", lw=4)
    px = ux + uw + 0.8
    ax.add_patch(Rectangle((px, uy + 0.4), 0.7, 1.6, fc="#111", ec="#111", zorder=6))
    holes = {"signal (empty)": uy + 1.75, "+ red": uy + 1.2, "- black/brown": uy + 0.65}
    for name, hy in holes.items():
        ax.add_patch(Circle((px + 0.35, hy), 0.13, fc="#777", ec="#ccc", zorder=6.5))
    ax.text(px + 0.35, uy + 2.15, "output plug\n(servo-style)", fontsize=7, ha="center", va="bottom", weight="bold", zorder=8)
    wire([(px + 0.5, holes["+ red"]), (px + 1.4, holes["+ red"])], RED, lw=2.4)
    wire([(px + 0.5, holes["- black/brown"]), (px + 1.0, holes["- black/brown"]), (px + 1.0, uy - 1.3), (px + 1.4, uy - 1.3)],
         BLK, lw=2.4)
    tag(px + 1.4, holes["+ red"], "+ hole: male jumper to breadboard j23 (6 V)", RED)
    tag(px + 1.4, uy - 1.3, "- hole: male jumper to breadboard B- rail", BLK)
    ax.text(px + 1.0, holes["signal (empty)"] + 0.05, "3rd hole (if any): nothing", fontsize=7, ha="left", va="center",
            color="#555", zorder=8)
    # ---------------- leads from the nuts to the breadboard
    wire([(w1[3], W1y), (w1[3], 12.2), (24.0, 12.2)], RED, lw=2.2)
    tag(24.0, 12.2, "VBAT lead to breadboard j18 (top of R1)", RED)
    wire([(w2[4], W2y + 1.3), (w2[4], 2.2), (24.0, 2.2)], BLK, lw=2.2)
    tag(24.0, 2.2, "GND lead to breadboard B- rail", BLK)
    # ---------------- slot tables beside the nuts
    ax.text(10.6, W1y + 2.0, "WAGO 1 slots: 1 switch OUT | 2 buck IN+ | 3 UBEC IN+ | 4 VBAT lead to j18 | 5 empty",
            fontsize=8.3, color=RED, weight="bold", ha="left", va="center")
    ax.text(10.6, W2y - 0.45, "WAGO 2 slots: 1 charger B- | 2 battery - | 3 buck IN- | 4 UBEC IN- | 5 GND lead to B- rail",
            fontsize=8.3, weight="bold", ha="left", va="center")
    ax.text(0.2, 16.6, "WAGO 3 slots: 1 fuse OUT | 2 charger B+ | 3 switch IN", fontsize=8.3, color=RED, weight="bold",
            ha="left", va="center")
    # ---------------- steps
    steps = ("Order, with the battery UNPLUGGED and SW1 OFF:\n"
             "1. Solder wire leads to the MP1584 pads (IN+, IN-, OUT+, OUT-). Red for +, black for -.\n"
             "2. Battery side, 18-20 AWG: BT1 + -> fuse holder -> WAGO 3; WAGO 3 -> SW1 'in'; SW1 'out' -> WAGO 1 slot 1.\n"
             "3. Charger: B+ -> WAGO 3 slot 2,  B- -> WAGO 2 slot 1.  Battery - -> WAGO 2 slot 2.\n"
             "4. Modules: buck IN+ and UBEC IN+ -> WAGO 1 (slots 2, 3);  buck IN- and UBEC IN- -> WAGO 2 (slots 3, 4).\n"
             "5. Leave the module OUTPUTS loose. Plug in the battery, SW1 ON, meter the outputs: buck 5.00 V (trim the screw),\n"
             "   UBEC 6.0 V (move its jumper).  SW1 OFF.\n"
             "6. Only now: buck OUT+ -> j11, OUT- -> B-;  UBEC plug + -> j23, - -> B-;  WAGO 1 slot 4 -> j18;  WAGO 2 slot 5 -> B-.\n"
             "Strip 11 mm for a WAGO 221, push the wire in fully, close the lever, tug it.  Charge only with SW1 OFF.")
    ax.text(0.2, -0.9, steps, fontsize=8.4, va="top", ha="left", family="DejaVu Sans",
            bbox=dict(fc="#fffbe8", ec="#bbb", lw=0.6, pad=0.7))
    ax.set_xlim(-1.2, 35.5); ax.set_ylim(-6.4, 17.2); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Claw Rev B: the off-board wiring, every wire (pairs with breadboard_layout_claw.png)", fontsize=12, loc="left")
    for ext in ("png", "pdf"):
        fig.savefig(HERE / f"offboard_wiring_claw.{ext}", dpi=160, bbox_inches="tight")


if __name__ == "__main__":
    ok = check()
    draw()
    sys.exit(0 if ok else 1)
