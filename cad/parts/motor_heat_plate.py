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



def shop_drawing(path_pdf, mass_g, qty=4):
    """SolidWorks-style shop drawing, A3 portrait at TRUE 1:1 scale (print at
    100 % / "actual size"): baseline dimensions from datum A (bottom edge) and
    datum B (left edge) to every hole centre, hole callouts, centre marks,
    edge view for thickness, notes and title block."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

    PW, PH = 297.0, 420.0                     # A3 portrait, mm
    INK, MUTED, CL = "#111111", "#555555", "#1f5fbf"
    fig = plt.figure(figsize=(PW / 25.4, PH / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, PW)
    ax.set_ylim(0, PH)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((10, 10), PW - 20, PH - 20, fill=False, ec=INK, lw=1.0))

    ox, oy = 95.0, 62.0                       # plate bottom-left corner on the sheet (datum A/B)
    cx, cy, sq = W / 2, AXIS_FROM_BOTTOM, BOLT_SQ / 2
    bolts = [(cx + sx * sq, cy + sy * sq) for sy in (-1, 1) for sx in (-1, 1)]
    fs, lw = 7.5, 0.6

    # ---- front view
    ax.add_patch(FancyBboxPatch((ox, oy), W, H, boxstyle=f"round,pad=0,rounding_size={CORNER_R}",
                                fc="none", ec=INK, lw=1.2))
    for (hx, hy), d in [((cx, cy), PILOT_D)] + [(b, BOLT_D) for b in bolts]:
        ax.add_patch(Circle((ox + hx, oy + hy), d / 2, fc="none", ec=INK, lw=1.0))
        ext = d / 2 + 2.5                       # centre mark + centre lines
        ax.plot([ox + hx - ext, ox + hx + ext], [oy + hy] * 2, color=CL, lw=0.35, ls=(0, (6, 2, 1, 2)))
        ax.plot([ox + hx] * 2, [oy + hy - ext, oy + hy + ext], color=CL, lw=0.35, ls=(0, (6, 2, 1, 2)))
    ax.plot([ox + cx, ox + cx], [oy - 3, oy + H + 3], color=CL, lw=0.3, ls=(0, (8, 2, 1, 2)))

    def arrow(p, q):
        ax.annotate("", q, p, arrowprops=dict(arrowstyle="<|-|>", color=INK, lw=lw,
                                              shrinkA=0, shrinkB=0, mutation_scale=6))

    # baseline dims in X from datum B (left edge), stacked below the part
    xs = sorted({0.0, bolts[0][0], cx, bolts[1][0], W})
    for k, xv in enumerate(xs[1:]):
        yv = oy - 8 - 6 * k
        ax.plot([ox, ox], [oy - 1, yv - 1.5], color=MUTED, lw=0.35)
        ax.plot([ox + xv, ox + xv], [oy - 1 if xv in (0.0, W) else oy + (cy if xv == cx else bolts[0][1]) - (PILOT_D / 2 if xv == cx else BOLT_D / 2) - 0.8,
                yv - 1.5], color=MUTED, lw=0.35)
        arrow((ox, yv), (ox + xv, yv))
        ax.text(ox + xv / 2 if xv > 12 else ox + xv + 1.5, yv + 0.8, f"{xv:.2f}", ha="center" if xv > 12 else "left",
                va="bottom", fontsize=fs, color=INK)
    # baseline dims in Y from datum A (bottom edge), stacked left of the part
    ys = sorted({0.0, bolts[0][1], cy, bolts[2][1], H})
    for k, yv_ in enumerate(ys[1:]):
        xv = ox - 8 - 7 * k
        ax.plot([ox - 1, xv - 1.5], [oy, oy], color=MUTED, lw=0.35)
        ax.plot([ox - 1 if yv_ == H else ox + bolts[0][0] - BOLT_D / 2 - 0.8 if yv_ != cy else ox + cx - PILOT_D / 2 - 0.8,
                 xv - 1.5], [oy + yv_] * 2, color=MUTED, lw=0.35)
        arrow((xv, oy), (xv, oy + yv_))
        ax.text(xv - 0.8, oy + (yv_ / 2 if yv_ > 12 else yv_ + 1.5), f"{yv_:.2f}", rotation=90, ha="right",
                va="center" if yv_ > 12 else "bottom", fontsize=fs, color=INK)
    # bolt square (reference)
    ax.plot([ox + bolts[2][0], ox + bolts[3][0]], [oy + bolts[2][1] + 9] * 2, color=MUTED, lw=0.35)
    arrow((ox + bolts[2][0], oy + bolts[2][1] + 9), (ox + bolts[3][0], oy + bolts[2][1] + 9))
    for b in (bolts[2], bolts[3]):
        ax.plot([ox + b[0]] * 2, [oy + b[1] + BOLT_D / 2 + 0.8, oy + b[1] + 10], color=MUTED, lw=0.35)
    ax.text(ox + cx, oy + bolts[2][1] + 9.8, f"({BOLT_SQ:.2f}) REF", ha="center", va="bottom", fontsize=fs - 0.5,
            color=MUTED)

    # hole callouts with leaders
    def callout(px, py, tx, ty, txt):
        ax.annotate(txt, (px, py), (tx, ty), fontsize=fs, color=INK, ha="left", va="center",
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=lw, mutation_scale=6, shrinkA=1, shrinkB=0))
    r45 = PILOT_D / 2 * 0.7071
    callout(ox + cx + r45, oy + cy + r45, ox + W + 14, oy + cy + 26,
            f"Ø{PILOT_D:.2f} THRU  (A)\nmotor boss Ø22.0 + clearance")
    b = bolts[3]
    callout(ox + b[0] + BOLT_D / 2 * 0.7071, oy + b[1] + BOLT_D / 2 * 0.7071, ox + W + 14, oy + b[1] + 40,
            f"4X Ø{BOLT_D:.2f} THRU  (B-E)\nM3 clearance, NEMA 17 pattern")
    ax.text(ox + cx, oy + 150, "FIN\n(cooling area)\npaint matte black", ha="center", va="center", fontsize=8,
            color=MUTED)
    ax.add_patch(Rectangle((ox + cx - 21.15, oy + cy - 21.15), 42.3, 42.3, fill=False, ec=CL, lw=0.6, ls="--"))
    ax.annotate("motor contact face 42.3 □:\nleave BARE, thermal paste", (ox + cx + 21.15, oy + cy + 12),
                (ox + W + 14, oy + cy + 88), fontsize=fs - 0.5, color=CL, va="center",
                arrowprops=dict(arrowstyle="-", color=CL, lw=0.4))
    # datum flags
    for lab, (px, py) in (("A", (ox + W * 0.7, oy)), ("B", (ox, oy + H * 0.55))):
        ax.add_patch(Rectangle((px - 2.5, py - 2.5), 5, 5, fc="white", ec=INK, lw=0.6, zorder=5))
        ax.text(px, py, lab, ha="center", va="center", fontsize=7, color=INK, zorder=6, weight="bold")
    ax.text(ox + W + 3, oy - 2, "DATUM A\n= bottom edge\n(sits on deck)", fontsize=6.5, color=MUTED, va="top")
    ax.text(ox - 4, oy + H * 0.55 + 5, "DATUM B\n= left edge", fontsize=6.5, color=MUTED, ha="right", va="bottom")
    # overall height label already in the Y stack; width in the X stack
    ax.text(ox + cx, oy + H + 6, "FRONT VIEW (from the PETG tab side)  1:1", ha="center", fontsize=8, color=INK,
            weight="bold")

    # ---- edge view (right side), thickness
    ex = 272.0
    ax.add_patch(Rectangle((ex, oy), T, H, fc="none", ec=INK, lw=1.0))
    yt = oy + H * 0.45
    ax.annotate("", (ex, yt), (ex - 5, yt), arrowprops=dict(arrowstyle="-|>", color=INK, lw=lw, mutation_scale=6))
    ax.annotate("", (ex + T, yt), (ex + T + 5, yt),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=lw, mutation_scale=6))
    ax.text(ex - 6, yt, f"{T:.3f}\n(1/8\") PLATE", va="center", ha="right", fontsize=fs, color=INK)
    ax.text(ex + T / 2, oy + H + 6, "EDGE VIEW", ha="center", fontsize=8, color=INK, weight="bold")

    # ---- notes
    nx, ny = 160.0, 395.0
    notes = [
        "NOTES",
        "1. MATERIAL: 6061-T6 OR 5052-H32 ALUMINIUM, 1/8\" (3.175) PLATE.",
        f"2. QTY {qty} (ONE PER WINCH STATION).",
        "3. ALL HOLES THRU. HOLE POSITIONS ±0.10 RELATIVE TO EACH",
        "   OTHER; DRILL ALL 5 IN ONE SETUP FROM DATUMS A AND B.",
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
        ax.text(nx, ny - 5.2 * i, n, fontsize=6.6, color=INK, family="monospace",
                weight="bold" if i == 0 else "normal")

    # ---- title block
    tb = [("PART", "MOTOR HEAT FIN  (motor_heat_plate)"), ("PROJECT", "RoomCleaner winch station, gen 2"),
          ("MATERIAL", "AL 6061-T6 / 5052-H32, 3.175 PLATE"), ("UNITS", "mm"), ("SCALE", "1:1 on A3 (print 100 %)"),
          ("GENERAL TOL.", "±0.5 unless noted"), ("REV", "B   2026-10-19"),
          ("SOURCE", "cad/parts/motor_heat_plate.py")]
    tx, ty, tw, rh = 160.0, 12.0, 125.0, 6.0
    ax.add_patch(Rectangle((tx, ty), tw, rh * len(tb), fill=False, ec=INK, lw=0.8))
    for i, (k, v) in enumerate(tb):
        yy = ty + rh * (len(tb) - 1 - i)
        ax.plot([tx, tx + tw], [yy, yy], color=INK, lw=0.3)
        ax.text(tx + 2, yy + rh / 2, k, fontsize=6, color=MUTED, va="center")
        ax.text(tx + 30, yy + rh / 2, v, fontsize=6.8, color=INK, va="center")
    ax.plot([tx + 28, tx + 28], [ty, ty + rh * len(tb)], color=INK, lw=0.3)
    # 100 mm scale check bar
    ax.plot([20, 120], [15, 15], color=INK, lw=1.0)
    for xv in (20, 70, 120):
        ax.plot([xv, xv], [13.5, 16.5], color=INK, lw=0.8)
    ax.text(70, 17.5, "SCALE CHECK: this bar must measure 100 mm", ha="center", fontsize=6.5, color=INK)
    fig.savefig(path_pdf, facecolor="white")
    fig.savefig(str(path_pdf)[:-4] + ".png", facecolor="white", dpi=150)
    plt.close(fig)

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
    print(out + ".step / .stl / .dxf / _drawing.png / _shop_drawing_A3.pdf")
