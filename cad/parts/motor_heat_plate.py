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


if __name__ == "__main__":
    p = make()
    out = "solidworks/heat_plate/motor_heat_plate"
    cq.exporters.export(p, out + ".step")
    cq.exporters.export(p.faces("<Z"), out + ".dxf")   # 2D outline + holes for laser/waterjet
    v = p.val().Volume()
    print(f"volume {v:.0f} mm^3, mass {v*2.7e-3:.0f} g (aluminium)")
    drawing(out + "_drawing.png", v * 2.7e-3)
    print(out + ".step / .dxf / _drawing.png")
