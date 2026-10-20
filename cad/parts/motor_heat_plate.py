"""
Gen-2 accessory: aluminium heat-spreader fin (vertical only, motor-width) for the NEMA 17 winch
motor (design review R11). Sandwiched between the motor's front flange and
the 5 mm PETG motor tab of Slipin_mount_piece_v3; the upper part passes
through a slot in the shell into room air.

Interface (measured from solidworks/v3_2026-10-18/Slipin_mount_piece_v3.STEP):
motor tab pilot hole Ø22.4, 4× Ø3.5 on a 31.0 mm square, motor axis 21.1 mm
above the deck top (z 34.6 vs deck 13.47).

    /usr/bin/python3 -m cad.parts.motor_heat_plate
"""
import cadquery as cq

T = 3.175          # mm, 1/8" 6061-T6 or 5052-H32 plate (enough now that only ~7 mm is covered)
W = 44.0           # mm, width: motor flange 42.3 + ~0.85 each side (vertical fin only)
H = 250.0          # mm, height: ~200 mm in open air above the cover's fin-pocket floor
AXIS_FROM_BOTTOM = 21.0   # mm, motor axis above the plate's bottom edge (deck clearance 0.1 mm)
PILOT_D = 22.5     # mm, motor boss Ø22.0 + clearance
BOLT_SQ = 31.0     # mm, NEMA 17 bolt square
BOLT_D = 3.4       # mm, M3 clearance
CORNER_R = 3.0


def make():
    cx, cy = W / 2, AXIS_FROM_BOTTOM
    plate = (cq.Workplane("XY").rect(W, H, centered=False).extrude(T)
             .edges("|Z").fillet(CORNER_R))
    h = BOLT_SQ / 2
    plate = (plate.faces(">Z").workplane(origin=(0, 0, T))
             .pushPoints([(cx, cy)]).hole(PILOT_D)
             .faces(">Z").workplane(origin=(0, 0, T))
             .pushPoints([(cx + dx, cy + dy) for dx in (-h, h) for dy in (-h, h)])
             .hole(BOLT_D))
    return plate


def drawing(path, mass_g):
    """Dimensioned drawing + hole table (PNG), numbers taken from the constants."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Circle
    INK, MUTED, ACC = "#2b2b29", "#6b6a63", "#2a78d6"
    cx, cy, sq = W / 2, AXIS_FROM_BOTTOM, BOLT_SQ / 2
    fig, ax = plt.subplots(figsize=(11, 14), dpi=150)
    ax.add_patch(FancyBboxPatch((0, 0), W, H, boxstyle=f"round,pad=0,rounding_size={CORNER_R}",
                                fc="#eef3fa", ec=INK, lw=1.6))
    ax.add_patch(Circle((cx, cy), PILOT_D / 2, fc="white", ec=INK, lw=1.4))
    ax.text(cx, cy, "A", ha="center", va="center", fontsize=9, color=INK)
    holes = {(-1, -1): "B", (1, -1): "C", (-1, 1): "D", (1, 1): "E"}
    for (sx, sy), lab in holes.items():
        ax.add_patch(Circle((cx + sx * sq, cy + sy * sq), BOLT_D / 2, fc="white", ec=INK, lw=1.2))
        ax.text(cx + sx * (sq - 3.4), cy + sy * (sq - 3.4), lab, ha="center", va="center",
                fontsize=7.5, color=INK)
    ax.add_patch(plt.Rectangle((cx - 21.15, cy - 21.15), 42.3, 42.3, fill=False, ec=ACC, lw=1.2, ls="--"))
    ax.text(cx, cy + 21.15 + 2, "motor flange 42.3 \u25a1\nthermal paste here", color=ACC, fontsize=7.5,
            ha="center", va="bottom")
    ax.text(cx, (H + 42.3) / 2 + 10, "FIN\n\nmust sit in\nroom air\n\nblack,\nvertical",
            color=INK, fontsize=8.5, ha="center", va="center")

    def vdim(x, y1, y2, txt, off):
        ax.annotate("", (x + off, y1), (x + off, y2), arrowprops=dict(arrowstyle="<->", color=INK, lw=0.9))
        ax.text(x + off - 1.5, (y1 + y2) / 2, txt, rotation=90, ha="right", va="center", fontsize=8.5, color=INK)
        for y in (y1, y2):
            ax.plot([x, x + off], [y, y], color=MUTED, lw=0.6)

    def hdim(y, x1, x2, txt, off):
        ax.annotate("", (x1, y + off), (x2, y + off), arrowprops=dict(arrowstyle="<->", color=INK, lw=0.9))
        ax.text((x1 + x2) / 2, y + off - 1.5, txt, ha="center", va="top", fontsize=8.5, color=INK)
        for x in (x1, x2):
            ax.plot([x, x], [y, y + off], color=MUTED, lw=0.6)

    hdim(0, 0, W, f"{W:.1f}", -12)
    hdim(0, 0, cx, f"{cx:.1f}", -5)
    vdim(0, 0, H, f"{H:.0f}", -14)
    vdim(0, 0, cy, f"{cy:.1f}", -6)
    rows = [("A", f"\u00d8{PILOT_D} thru", cx, cy, "motor pilot")] + [
        (lab, f"\u00d8{BOLT_D} thru", cx + sx * sq, cy + sy * sq, "M3 motor bolt")
        for (sx, sy), lab in sorted(holes.items(), key=lambda kv: kv[1])]
    x0, y0, cols = W + 28, H - 10, [0, 7, 27, 38, 49]
    ax.text(x0, y0 + 6, "HOLE TABLE (origin = bottom-left corner)", fontsize=8.5, color=INK, weight="bold")
    for j, hd in enumerate(["ID", "Size", "X", "Y", "Purpose"]):
        ax.text(x0 + cols[j], y0, hd, fontsize=8, color=MUTED)
    for i, (a, b, x, y, e) in enumerate(rows):
        for j, v in enumerate([a, b, f"{x:.1f}", f"{y:.1f}", e]):
            ax.text(x0 + cols[j], y0 - 7 * (i + 1), v, fontsize=8, color=INK)
    edge = cx - sq - BOLT_D / 2
    notes = [f"Material: {T} mm (1/8\") 6061-T6 or 5052-H32 plate",
             f"Blank: {W:.1f} x {H:.0f} mm (shear), tol +/-0.5",
             "Holes: positions +/-0.1 relative to each other;",
             "  datum = BOTTOM edge + LEFT edge (drill all 5",
             "  in one setup on the mill)",
             f"Corners: break edges; R{CORNER_R:.0f} optional",
             "Deburr both faces; motor face must stay flat",
             "Finish: matte black paint EXCEPT the motor",
             "  contact square (thermal paste there)",
             f"Mass: {mass_g:.0f} g",
             "BOTTOM edge sits on the slide-in deck;",
             f"  motor axis {AXIS_FROM_BOTTOM:.0f} mm above it (v3 STEP)",
             f"Bolt-hole edge to plate side: {edge:.1f} mm",
             "Stack: motor | plate | 5 mm PETG tab",
             "  -> M3 x 12 motor bolts (was x 10)",
             f"  -> motor + spool move {T:.1f} mm along the shaft",
             "Cover fin pocket: slot (T+0.8) x 44.8 open to",
             "  the mating face; 10-12 mm air each face;",
             "  floor >= 25.5 mm above shaft; open top + side"]
    for i, n in enumerate(notes):
        ax.text(x0, y0 - 52 - 7.0 * i, n, fontsize=8, color=INK)
    ax.set_xlim(-26, W + 121)
    ax.set_ylim(-20, H + 8)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Motor heat fin \u2014 view from the PETG tab side", color=INK, fontsize=11, loc="left")
    plt.savefig(path, bbox_inches="tight", facecolor="white")
    if str(path).endswith(".png"):
        plt.savefig(str(path)[:-4] + ".pdf", bbox_inches="tight", facecolor="white")



INK, MUTED, CL = "#111111", "#555555", "#1f5fbf"


def _sheet(PW, PH, border=10.0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig = plt.figure(figsize=(PW / 25.4, PH / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, PW)
    ax.set_ylim(0, PH)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((border, border), PW - 2 * border, PH - 2 * border, fill=False, ec=INK, lw=1.0))
    return fig, ax


def _bolts():
    cx, cy, sq = W / 2, AXIS_FROM_BOTTOM, BOLT_SQ / 2
    return [(cx + sx * sq, cy + sy * sq) for sy in (-1, 1) for sx in (-1, 1)]


def _arrow(ax, p, q, lw=0.6):
    ax.annotate("", q, p, arrowprops=dict(arrowstyle="<|-|>", color=INK, lw=lw,
                                          shrinkA=0, shrinkB=0, mutation_scale=6))


def _holes(ax, ox, oy, s):
    """Hole circles + centre marks; plate point (x, y) sits at (ox + s*x, oy + s*y)."""
    from matplotlib.patches import Circle
    cx, cy = W / 2, AXIS_FROM_BOTTOM
    for (hx, hy), d in [((cx, cy), PILOT_D)] + [(b, BOLT_D) for b in _bolts()]:
        px, py = ox + s * hx, oy + s * hy
        ax.add_patch(Circle((px, py), s * d / 2, fc="none", ec=INK, lw=1.0))
        ext = s * d / 2 + 2.5
        ax.plot([px - ext, px + ext], [py] * 2, color=CL, lw=0.35, ls=(0, (6, 2, 1, 2)))
        ax.plot([px] * 2, [py - ext, py + ext], color=CL, lw=0.35, ls=(0, (6, 2, 1, 2)))


def _front_view(ax, ox, oy, s, *, fs=7.5, plate_h=H, label_x=None, title=""):
    """Front view of the fin at sheet scale ``s`` with baseline dimensions from
    datum A (bottom edge) and datum B (left edge), hole callouts and datum flags.
    ``plate_h`` < H draws a broken-off bottom portion (1:1 template)."""
    from matplotlib.patches import FancyBboxPatch, Rectangle
    cx, cy = W / 2, AXIS_FROM_BOTTOM
    bolts = _bolts()
    full = plate_h >= H
    P = lambda x, y: (ox + s * x, oy + s * y)
    lw = 0.6
    if full:
        ax.add_patch(FancyBboxPatch((ox, oy), s * W, s * H, boxstyle=f"round,pad=0,rounding_size={s * CORNER_R}",
                                    fc="none", ec=INK, lw=1.2))
    else:                                        # bottom portion + zig-zag break line
        import numpy as np
        top = oy + s * plate_h
        ax.plot([ox, ox, ox + s * W, ox + s * W], [top, oy, oy, top], color=INK, lw=1.2)
        zx = np.linspace(ox, ox + s * W, 9)
        zy = top + np.array([0, 1.5, -1.5, 1.5, -1.5, 1.5, -1.5, 1.5, 0])
        ax.plot(zx, zy, color=INK, lw=0.8)
        ax.text(ox + s * W / 2, top + 4, f"PLATE CONTINUES TO {H:.0f} (break shown)", ha="center",
                fontsize=fs - 0.5, color=MUTED)
    _holes(ax, ox, oy, s)
    ax.plot([ox + s * cx] * 2, [oy - 3, oy + s * plate_h + (3 if full else -3)], color=CL, lw=0.3,
            ls=(0, (8, 2, 1, 2)))

    # baseline dims in X from datum B (left edge), stacked below the part
    xs = sorted({0.0, bolts[0][0], cx, bolts[1][0], W})
    for k, xv in enumerate(xs[1:]):
        yv = oy - 8 - 6 * k
        ax.plot([ox, ox], [oy - 1, yv - 1.5], color=MUTED, lw=0.35)
        start = oy - 1 if xv in (0.0, W) else (
            P(0, cy - PILOT_D / 2)[1] - 0.8 if xv == cx else P(0, bolts[0][1] - BOLT_D / 2)[1] - 0.8)
        ax.plot([ox + s * xv] * 2, [start, yv - 1.5], color=MUTED, lw=0.35)
        _arrow(ax, (ox, yv), (ox + s * xv, yv), lw)
        wide = s * xv > 12
        ax.text(ox + s * xv / 2 if wide else ox + s * xv + 1.5, yv + 0.8, f"{xv:.2f}",
                ha="center" if wide else "left", va="bottom", fontsize=fs, color=INK)
    # baseline dims in Y from datum A (bottom edge), stacked left of the part
    ys = sorted({0.0, bolts[0][1], cy, bolts[2][1]} | ({H} if full else set()))
    for k, yv_ in enumerate(ys[1:]):
        xv = ox - 8 - 7 * k
        ax.plot([ox - 1, xv - 1.5], [oy, oy], color=MUTED, lw=0.35)
        start = ox - 1 if yv_ == H else (P(cx - PILOT_D / 2, 0)[0] - 0.8 if yv_ == cy
                                         else P(bolts[0][0] - BOLT_D / 2, 0)[0] - 0.8)
        ax.plot([start, xv - 1.5], [oy + s * yv_] * 2, color=MUTED, lw=0.35)
        _arrow(ax, (xv, oy), (xv, oy + s * yv_), lw)
        tall = s * yv_ > 12
        ax.text(xv - 0.8, oy + (s * yv_ / 2 if tall else s * yv_ + 1.5), f"{yv_:.2f}", rotation=90, ha="right",
                va="center" if tall else "bottom", fontsize=fs, color=INK)
    # bolt square (reference)
    yb = P(0, bolts[2][1])[1] + 9
    ax.plot([P(*bolts[2])[0], P(*bolts[3])[0]], [yb] * 2, color=MUTED, lw=0.35)
    _arrow(ax, (P(*bolts[2])[0], yb), (P(*bolts[3])[0], yb), lw)
    for b in (bolts[2], bolts[3]):
        ax.plot([P(*b)[0]] * 2, [P(*b)[1] + s * BOLT_D / 2 + 0.8, yb + 1], color=MUTED, lw=0.35)
    ax.text(P(cx, 0)[0], yb + 0.8, f"({BOLT_SQ:.2f}) REF", ha="center", va="bottom", fontsize=fs - 0.5, color=MUTED)

    # hole callouts with leaders
    def callout(px, py, tx, ty, txt):
        ax.annotate(txt, (px, py), (tx, ty), fontsize=fs, color=INK, ha="left", va="center",
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=lw, mutation_scale=6, shrinkA=1, shrinkB=0))
    lx = label_x if label_x is not None else ox + s * W + 14
    r45 = s * PILOT_D / 2 * 0.7071
    pc = P(cx, cy)
    callout(pc[0] + r45, pc[1] + r45, lx, pc[1] + 26, f"Ø{PILOT_D:.2f} THRU  (A)\nmotor boss Ø22.0 + clearance")
    pb = P(*bolts[3])
    rb = s * BOLT_D / 2 * 0.7071
    callout(pb[0] + rb, pb[1] + rb, lx, pb[1] + 40, f"4X Ø{BOLT_D:.2f} THRU  (B-E)\nM3 clearance, NEMA 17 pattern")
    if full:
        ax.text(P(cx, 150)[0], P(cx, 150)[1], "FIN\n(cooling area)\npaint matte black", ha="center",
                va="center", fontsize=8, color=MUTED)
    c0 = P(cx - 21.15, cy - 21.15)
    ax.add_patch(Rectangle(c0, s * 42.3, s * 42.3, fill=False, ec=CL, lw=0.6, ls="--"))
    ax.annotate("motor contact face 42.3 □:\nleave BARE, thermal paste", (c0[0] + s * 42.3, pc[1] - s * 10),
                (lx, oy + 6), fontsize=fs - 0.5, color=CL, va="center",
                arrowprops=dict(arrowstyle="-", color=CL, lw=0.4))
    # datum flags
    for lab, (px, py) in (("A", (ox + s * W * 0.7, oy)), ("B", (ox, oy + s * min(H * 0.55, plate_h * 0.85)))):
        ax.add_patch(Rectangle((px - 2.5, py - 2.5), 5, 5, fc="white", ec=INK, lw=0.6, zorder=5))
        ax.text(px, py, lab, ha="center", va="center", fontsize=7, color=INK, zorder=6, weight="bold")
    ax.text(ox - 4, oy + s * min(H * 0.55, plate_h * 0.85) + 5, "DATUM B\n= left edge", fontsize=6.5, color=MUTED,
            ha="right", va="bottom")
    ax.text(ox + s * cx, oy + s * plate_h + (6 if full else 10), title, ha="center", fontsize=8, color=INK,
            weight="bold")


def _edge_view(ax, ex, oy, s, fs=7.5):
    from matplotlib.patches import Rectangle
    ax.add_patch(Rectangle((ex, oy), max(s * T, 1.0), s * H, fc="none", ec=INK, lw=1.0))
    yt = oy + s * H * 0.45
    w = max(s * T, 1.0)
    for x0, x1 in ((ex - 5, ex), (ex + w + 5, ex + w)):
        ax.annotate("", (x1, yt), (x0, yt), arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.6, mutation_scale=6))
    ax.text(ex - 6, yt, f"{T:.3f}\n(1/8\") PLATE", va="center", ha="right", fontsize=fs, color=INK)
    ax.text(ex + w / 2, oy + s * H + 6, "EDGE VIEW", ha="center", fontsize=8, color=INK, weight="bold")


def _notes(ax, nx, ny, mass_g, qty, fs=6.6, dy=5.2):
    notes = [
        "NOTES",
        "1. MATERIAL: 6061-T6 OR 5052-H32 ALUMINIUM, 1/8\" (3.175) PLATE.",
        f"2. QTY {qty} (ONE PER WINCH STATION).",
        "3. ALL HOLES THRU. HOLE POSITIONS ±0.10 RELATIVE TO EACH",
        "   OTHER; DRILL ALL 5 IN ONE SETUP FROM DATUMS A AND B.",
        "   DATUM A = BOTTOM EDGE (SITS ON DECK), B = LEFT EDGE.",
        "4. BLANK 44.0 x 250.0 ±0.5 (SHEARED). BREAK ALL EDGES;",
        f"   CORNER R{CORNER_R:.0f} OPTIONAL.",
        "5. DEBURR BOTH FACES. MOTOR FACE FLAT, NO RAISED BURRS.",
        "6. FINISH: MATTE BLACK PAINT EXCEPT THE 42.3 SQ. MOTOR",
        "   CONTACT AREA (BOTH FACES MAY BE PAINTED ABOVE IT).",
        "7. ASSEMBLY: MOTOR | FIN | 5 MM PETG TAB, M3 x 12 BOLTS,",
        "   THERMAL PASTE ON MOTOR FACE. MOTOR + SPOOL SHIFT 3.2",
        "   ALONG THE SHAFT.",
        f"8. MASS ≈ {mass_g:.0f} g EACH.",
    ]
    for i, n in enumerate(notes):
        ax.text(nx, ny - dy * i, n, fontsize=fs, color=INK, family="monospace", weight="bold" if i == 0 else "normal")


def _title_block(ax, tx, ty, tw, rh, scale_txt, sheet_txt=None):
    from matplotlib.patches import Rectangle
    tb = [("PART", "MOTOR HEAT FIN  (motor_heat_plate)"), ("PROJECT", "RoomCleaner winch station, gen 2"),
          ("MATERIAL", "AL 6061-T6 / 5052-H32, 3.175 PLATE"), ("UNITS", "mm"), ("SCALE", scale_txt),
          ("GENERAL TOL.", "±0.5 unless noted"), ("REV", "B   2026-10-19"),
          ("SOURCE", "cad/parts/motor_heat_plate.py")]
    if sheet_txt:
        tb.append(("SHEET", sheet_txt))
    ax.add_patch(Rectangle((tx, ty), tw, rh * len(tb), fill=False, ec=INK, lw=0.8))
    for i, (k, v) in enumerate(tb):
        yy = ty + rh * (len(tb) - 1 - i)
        ax.plot([tx, tx + tw], [yy, yy], color=INK, lw=0.3)
        ax.text(tx + 2, yy + rh / 2, k, fontsize=6, color=MUTED, va="center")
        ax.text(tx + 26, yy + rh / 2, v, fontsize=6.8, color=INK, va="center")
    ax.plot([tx + 24, tx + 24], [ty, ty + rh * len(tb)], color=INK, lw=0.3)


def _scale_bar(ax, x0, y0, length=100.0):
    ax.plot([x0, x0 + length], [y0, y0], color=INK, lw=1.0)
    for xv in (x0, x0 + length / 2, x0 + length):
        ax.plot([xv, xv], [y0 - 1.5, y0 + 1.5], color=INK, lw=0.8)
    ax.text(x0 + length / 2, y0 + 2.5, f"SCALE CHECK: this bar must measure {length:.0f} mm", ha="center",
            fontsize=6.5, color=INK)


def shop_drawing(path_pdf, mass_g, qty=4):
    """SolidWorks-style shop drawing, A3 portrait at TRUE 1:1 scale (print at
    100 % / "actual size"): baseline dimensions from datum A (bottom edge) and
    datum B (left edge) to every hole centre, hole callouts, centre marks,
    edge view for thickness, notes and title block."""
    import matplotlib.pyplot as plt
    fig, ax = _sheet(297.0, 420.0)            # A3 portrait, mm
    _front_view(ax, 95.0, 62.0, 1.0, title="FRONT VIEW (from the PETG tab side)  1:1")
    _edge_view(ax, 272.0, 62.0, 1.0)
    _notes(ax, 160.0, 395.0, mass_g, qty)
    _title_block(ax, 160.0, 12.0, 125.0, 6.0, "1:1 on A3 (print 100 %)")
    _scale_bar(ax, 20.0, 15.0)
    fig.savefig(path_pdf, facecolor="white")
    fig.savefig(str(path_pdf)[:-4] + ".png", facecolor="white", dpi=150)
    plt.close(fig)


def shop_drawing_letter(path_pdf, mass_g, qty=4):
    """Two-page drawing for an ordinary US Letter / A4 printer. Content stays
    inside the Letter-A4 overlap with >= 12 mm margins.

    Sheet 1: whole fin, scaled to fit (NOT to scale; dimensions govern).
    Sheet 2: TRUE 1:1 template of the hole end (print at 100 % / "actual
    size"), for checking the layout or taping to the blank and centre-punching.
    """
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    PW, PH = 215.9, 279.4                     # US Letter portrait, mm
    s1 = 0.8
    pages = []

    # ---- sheet 1: full part, 0.8x
    fig, ax = _sheet(PW, PH)
    ox, oy = 60.0, 52.0
    _front_view(ax, ox, oy, s1, fs=6.8, label_x=ox + s1 * W + 10,
                title="FRONT VIEW (PETG tab side)")
    _edge_view(ax, 192.0, oy, s1, fs=6.8)
    _notes(ax, 104.0, 252.0, mass_g, qty, fs=5.6, dy=4.4)
    _title_block(ax, 116.0, 13.0, 87.0, 4.2, "NOT TO SCALE (0.8x) - use dimensions", "1 OF 2")
    ax.text(14.0, 20.0, "DIMENSIONS GOVERN - DO NOT SCALE THIS SHEET.\n1:1 hole template on sheet 2.",
            fontsize=7, color="#b00020", weight="bold", va="top")
    pages.append(fig)

    # ---- sheet 2: 1:1 template of the hole end
    fig, ax = _sheet(PW, PH)
    ox, oy, hcut = 78.0, 100.0, 75.0
    _front_view(ax, ox, oy, 1.0, plate_h=hcut, label_x=ox + W + 12, title="HOLE-END TEMPLATE  1:1")
    tx = 16.0
    lines = [
        "SHEET 2 - TRUE 1:1 HOLE TEMPLATE",
        "PRINT AT 100 % / \"ACTUAL SIZE\". DO NOT \"FIT TO PAGE\".",
        "Check the 100 mm bar below with a ruler before using.",
        "",
        "Use: cut along the plate outline, align the bottom edge with",
        "datum A and the left edge with datum B, tape down, then",
        "centre-punch each crosshair. Machine to the dimensions;",
        "the template is a check / punch guide, not a gauge.",
    ]
    for i, t in enumerate(lines):
        ax.text(tx, 262.0 - 4.6 * i, t, fontsize=7.2 if i == 0 else 6.6, color="#b00020" if i < 2 else INK,
                weight="bold" if i < 2 else "normal", family="monospace", va="top")
    _title_block(ax, 116.0, 13.0, 87.0, 4.6, "1:1 (print 100 %)", "2 OF 2")
    _scale_bar(ax, 14.0, 22.0)
    pages.append(fig)

    with PdfPages(path_pdf) as pdf:
        for i, f in enumerate(pages, 1):
            pdf.savefig(f, facecolor="white")
            f.savefig(str(path_pdf)[:-4] + f"_p{i}.png", facecolor="white", dpi=150)
            plt.close(f)


if __name__ == "__main__":
    p = make()
    out = "solidworks/heat_plate/motor_heat_plate"
    cq.exporters.export(p, out + ".step")
    cq.exporters.export(p.faces("<Z"), out + ".dxf")   # 2D outline + holes for laser/waterjet
    v = p.val().Volume()
    print(f"volume {v:.0f} mm^3, mass {v*2.7e-3:.0f} g (aluminium)")
    drawing(out + "_drawing.png", v * 2.7e-3)
    cq.exporters.export(p, out + ".stl", tolerance=0.02, angularTolerance=0.1)
    shop_drawing(out + "_shop_drawing_A3.pdf", v * 2.7e-3)
    shop_drawing_letter(out + "_shop_drawing_letter.pdf", v * 2.7e-3)
    print(out + ".step / .stl / .dxf / _drawing.png / _shop_drawing_A3.pdf / _shop_drawing_letter.pdf")
