"""Print the multi-sheet floor reference (decision D26) on a home US Letter printer.

    python -m tools.print_floor_board --out prints/floor_board_letter.pdf [--png-dpi 100]
    python -m tools.print_floor_board --out sheet3.pdf --ids 3 --edge-mm 150 --no-instructions

Page 1 is the layout instructions; then one US Letter sheet per tag id (default
ids 0..8, AprilTag 36h11, black square 150 mm = 8 cells of 18.75 mm, white
quiet zone of 1 cell, everything inside the 6.35 mm printer margins).

The tags are VECTOR drawn: every black cell is an exact rectangle in the PDF,
so the physical size is exact at 100 % print scale (turn OFF "fit to page").
After printing, MEASURE the black square with a ruler and enter the measured
value (metres) as marker.edge_m -- the printed size, not the requested one,
is what counts. Sheet 0 defines the floor/marker frame (+X to the right as
printed, +Y up the page).

Needs: reportlab (to write), pypdf (to verify), pdftoppm (optional, PNG previews).
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

from roomcleaner.cdpr.vision.marker import _FAMILIES

MM = 72.0 / 25.4                      # PostScript points per millimetre
LETTER_MM = (215.9, 279.4)            # 8.5 x 11 in
LETTER_PT = (612.0, 792.0)
PRINTER_MARGIN_MM = 6.35              # 1/4 in
QUIET_CELLS = 1
DEFAULT_EDGE_MM = 150.0
BAR_MM = 100.0
TAG_BEGIN = "% FLOORBOARD-TAG-BEGIN"
TAG_END = "% FLOORBOARD-TAG-END"


# ----------------------------------------------------------------- geometry
def tag_cells(marker_id: int, family: str = "apriltag_36h11") -> np.ndarray:
    """(n, n) bool array, True = black cell, incl. the 1-cell black border (n = markerSize + 2)."""
    d = cv2.aruco.getPredefinedDictionary(_FAMILIES[family])
    if not 0 <= marker_id < d.bytesList.shape[0]:
        raise ValueError(f"id {marker_id} is outside the {family} dictionary (0..{d.bytesList.shape[0] - 1})")
    n = d.markerSize + 2
    return cv2.aruco.generateImageMarker(d, marker_id, n, borderBits=1) == 0


def sheet_geometry(edge_mm: float, family: str = "apriltag_36h11", *, top_mm: float = 40.0):
    """Tag placement on a Letter sheet, in mm from the top-left of the page."""
    d = cv2.aruco.getPredefinedDictionary(_FAMILIES[family])
    n = d.markerSize + 2
    cell = edge_mm / n
    quiet = QUIET_CELLS * cell
    outer = edge_mm + 2 * quiet
    usable = LETTER_MM[0] - 2 * PRINTER_MARGIN_MM
    if outer > usable + 1e-9:
        raise ValueError(f"tag edge {edge_mm} mm + quiet zone = {outer:.1f} mm does not fit the "
                         f"{usable:.1f} mm printable width (max edge {usable * n / (n + 2 * QUIET_CELLS):.1f} mm)")
    x0 = (LETTER_MM[0] - edge_mm) / 2
    return {"n": n, "cell_mm": cell, "x0_mm": x0, "y0_mm": top_mm + quiet, "outer_mm": outer, "top_mm": top_mm}


# ---------------------------------------------------------------- drawing
def _draw_tag(c, marker_id, edge_mm, family, geo):
    cells = tag_cells(marker_id, family)
    cell = geo["cell_mm"] * MM
    x0 = geo["x0_mm"] * MM
    y_top = (LETTER_MM[1] - geo["y0_mm"]) * MM        # PDF y grows upward
    c.setFillGray(0)
    c.addLiteral(f"{TAG_BEGIN} id={marker_id} edge_mm={edge_mm}")
    p = c.beginPath()
    for r in range(cells.shape[0]):
        k = 0
        while k < cells.shape[1]:
            if cells[r, k]:
                j = k
                while j < cells.shape[1] and cells[r, j]:
                    j += 1
                p.rect(x0 + k * cell, y_top - (r + 1) * cell, (j - k) * cell, cell)
                k = j
            else:
                k += 1
    c.drawPath(p, stroke=0, fill=1)
    c.addLiteral(TAG_END)


def _arrow(c, x1, y1, x2, y2, head=2.2):
    import math
    c.setLineWidth(0.9)
    c.line(x1 * MM, (LETTER_MM[1] - y1) * MM, x2 * MM, (LETTER_MM[1] - y2) * MM)
    a = math.atan2(-(y2 - y1), x2 - x1)
    for s in (+1, -1):
        ax = x2 - head * math.cos(a - s * 0.45)
        ay = y2 + head * math.sin(a - s * 0.45)
        c.line(x2 * MM, (LETTER_MM[1] - y2) * MM, ax * MM, (LETTER_MM[1] - ay) * MM)


def _text(c, x_mm, y_mm, s, size=9, bold=False):
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.drawString(x_mm * MM, (LETTER_MM[1] - y_mm) * MM, s)


def _tag_sheet(c, marker_id, idx, n_sheets, edge_mm, family, origin_id, ids):
    geo = sheet_geometry(edge_mm, family)
    m = PRINTER_MARGIN_MM
    c.setFillGray(0)
    c.setStrokeGray(0)
    _text(c, m + 4, 36, f"{marker_id}", size=96, bold=True)                  # big id number
    xt = 58
    _text(c, xt, 17, "ROOMCLEANER FLOOR REFERENCE", 15, True)
    _text(c, xt, 24, f"sheet {idx + 1} of {n_sheets}   -   AprilTag {family.replace('apriltag_', '')} id {marker_id}", 10)
    if marker_id == origin_id:
        _text(c, xt, 30, "CENTRE SHEET: put it under the claw. It defines the floor frame:", 9, True)
        _text(c, xt, 34.5, "+X = right as printed, +Y = up the page.", 9)
        _arrow(c, 175, 33, 195, 33)
        _text(c, 196.5, 34.3, "+X", 9, True)
        _arrow(c, 205, 36, 205, 15)
        _text(c, 200.5, 13.5, "+Y", 9, True)
    else:
        _text(c, xt, 30, "Lay flat, any rotation, roughly where the layout page shows.", 9)
        _arrow(c, 205, 33, 205, 15)
        _text(c, 201.2, 13.5, "TOP", 7, True)
    _draw_tag(c, marker_id, edge_mm, family, geo)
    # scale-check bar (100 mm)
    yb = geo["top_mm"] + geo["outer_mm"] + 9
    xb = geo["x0_mm"] - geo["cell_mm"]
    c.setLineWidth(1.2)
    c.line(xb * MM, (LETTER_MM[1] - yb) * MM, (xb + BAR_MM) * MM, (LETTER_MM[1] - yb) * MM)
    for k in range(11):
        h = 2.6 if k % 5 == 0 else 1.5
        c.setLineWidth(0.8)
        c.line((xb + 10 * k) * MM, (LETTER_MM[1] - yb) * MM, (xb + 10 * k) * MM, (LETTER_MM[1] - yb - h) * MM)
    _text(c, xb + BAR_MM + 3, yb + 1.2, "<- must measure 100 mm", 8)
    lines = [
        "1. Print at ACTUAL SIZE / 100 % (never 'fit to page'). Print every sheet in one run, same settings.",
        f"2. With a ruler, MEASURE THE BLACK SQUARE EDGE of this sheet (printed: {edge_mm:.1f} mm). Enter the measured",
        "   value of sheet 0, in metres, as marker.edge_m in the robot config. Check the 100 mm bar above on every sheet.",
        "3. Reprint any sheet whose black square differs from sheet 0 by more than 1 mm.",
    ]
    for k, ln in enumerate(lines):
        _text(c, geo["x0_mm"] - geo["cell_mm"], yb + 8 + 4.3 * k, ln, 7.6)


def _layout_sheet(c, ids, origin_id, edge_mm, pitch_mm=450.0):
    m = PRINTER_MARGIN_MM
    c.setFillGray(0)
    c.setStrokeGray(0)
    _text(c, m + 4, 20, "Floor reference: how to lay it out", 17, True)
    steps = [
        "1. Print this PDF on US Letter at 100 % (Actual size, NOT 'fit to page'); keep this page for yourself.",
        f"2. Measure the black square of sheet {origin_id} (should be {edge_mm:.0f} mm) and enter it, in metres, as marker.edge_m.",
        f"3. Put sheet {origin_id} in the middle, directly under where the claw rests at startup.",
        f"4. Lay the other {len(ids) - 1} sheets roughly as drawn below, about 450 mm centre to centre. Exact spacing",
        "   and rotation do NOT matter - the robot surveys the layout itself - but they must not overlap or touch.",
        "5. Every sheet must lie FLAT and fully visible: tape all corners down, no curl, no folds, no objects or cables",
        "   across a tag, avoid glare (close curtains / matte paper). Carpet ridges and rugs that slide are not OK.",
        f"6. Sheet {origin_id} defines the frame: its +X points right as printed. Enter the approximate room heading of",
        "   that +X as marker.heading_prior_rad.",
        "7. Do NOT move or bump any sheet once startup begins. If one moves, stop and run the survey again.",
    ]
    for k, ln in enumerate(steps):
        _text(c, m + 4, 32 + 5.2 * k, ln, 8.6)
    # schematic: 3x3 grid of Letter sheets (portrait), looking down at the floor
    k = 0.14
    sw, sh = LETTER_MM[0] * k, LETTER_MM[1] * k
    gp = pitch_mm * k
    geo = sheet_geometry(edge_mm)
    tag_dy = geo["y0_mm"] + edge_mm / 2 - LETTER_MM[1] / 2            # tag centre below the sheet centre (mm, real)
    top = 88.0
    cx, cy = LETTER_MM[0] / 2, top + sh / 2 + gp
    _text(c, cx - 50, top - 3.5, "Schematic, looking down at the floor (not to scale; the 0 sheet is the thick one)", 8.5, True)
    order = [origin_id] + [i for i in ids if i != origin_id]
    pos = {order[0]: (0, 0)}
    ring = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]
    for i, rc in zip(order[1:], ring):
        pos[i] = rc
    t = edge_mm * k
    for i, (gx, gy) in pos.items():
        x, y = cx + gx * gp, cy + gy * gp
        c.setLineWidth(1.6 if i == origin_id else 0.6)
        c.rect((x - sw / 2) * MM, (LETTER_MM[1] - (y + sh / 2)) * MM, sw * MM, sh * MM, stroke=1, fill=0)
        c.setLineWidth(0.6)
        yt = y + tag_dy * k
        c.rect((x - t / 2) * MM, (LETTER_MM[1] - (yt + t / 2)) * MM, t * MM, t * MM, stroke=1, fill=0)
        _text(c, x - (2.8 if i == origin_id else 2.2), yt + (2.2 if i == origin_id else 1.8), f"{i}",
              15 if i == origin_id else 11, True)
    ys = cy + gp + sh / 2 + 7
    c.setLineWidth(0.5)
    c.line((cx - gp) * MM, (LETTER_MM[1] - ys) * MM, cx * MM, (LETTER_MM[1] - ys) * MM)
    for xe in (cx - gp, cx):
        c.line(xe * MM, (LETTER_MM[1] - ys + 1.2) * MM, xe * MM, (LETTER_MM[1] - ys - 1.2) * MM)
    _text(c, cx - gp + 2, ys + 4.5, f"about {pitch_mm:.0f} mm centre to centre (~1.1 m overall)", 8.5)


def build_pdf(out, ids=range(9), edge_mm=DEFAULT_EDGE_MM, family="apriltag_36h11", *, instructions=True,
              origin_id=None):
    """Write the multi-page Letter PDF; returns the Path."""
    from reportlab.pdfgen import canvas
    ids = [int(i) for i in ids]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate ids")
    origin_id = ids[0] if origin_id is None else origin_id
    sheet_geometry(edge_mm, family)                          # validates that it fits
    for i in ids:
        tag_cells(i, family)                                 # validates the ids
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(out), pagesize=LETTER_PT, pageCompression=0, invariant=1)
    c.setTitle("RoomCleaner floor reference (US Letter)")
    c.setAuthor("RoomCleaner tools/print_floor_board.py")
    if instructions:
        _layout_sheet(c, ids, origin_id, edge_mm)
        c.showPage()
    for k, i in enumerate(ids):
        _tag_sheet(c, i, k, len(ids), edge_mm, family, origin_id, ids)
        c.showPage()
    c.save()
    return out


# -------------------------------------------------------------- verification
def verify_pdf(path, ids=range(9), edge_mm=DEFAULT_EDGE_MM, family="apriltag_36h11", *, instructions=True,
               tol_mm=0.005):
    """Read the PDF back and check: page count, every page US Letter, and for each
    tag sheet that the vector black cells reproduce the dictionary bit pattern of
    the id exactly with a black-square edge of ``edge_mm`` (to ``tol_mm``).
    Returns a list of human-readable check lines; raises AssertionError on failure."""
    from pypdf import PdfReader
    ids = [int(i) for i in ids]
    rd = PdfReader(str(path))
    n_expected = len(ids) + (1 if instructions else 0)
    assert len(rd.pages) == n_expected, f"{len(rd.pages)} pages, expected {n_expected}"
    report = []
    geo = sheet_geometry(edge_mm, family)
    for p_i, page in enumerate(rd.pages):
        w, h = float(page.mediabox.width), float(page.mediabox.height)
        assert abs(w - LETTER_PT[0]) < 0.01 and abs(h - LETTER_PT[1]) < 0.01, f"page {p_i + 1} is {w}x{h} pt, not Letter"
    report.append(f"{len(rd.pages)} pages, all 612 x 792 pt (US Letter 8.5 x 11 in)")
    first_tag_page = 1 if instructions else 0
    for k, tid in enumerate(ids):
        txt = rd.pages[first_tag_page + k].get_contents().get_data().decode("latin-1")
        a, b = txt.find(TAG_BEGIN), txt.find(TAG_END)
        assert a >= 0 and b > a, f"id {tid}: tag section not found"
        rects = [tuple(map(float, m.groups())) for m in
                 re.finditer(r"(-?[\d.]+) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) re", txt[a:b])]
        assert rects, f"id {tid}: no cells drawn"
        xs0 = min(r[0] for r in rects)
        xs1 = max(r[0] + r[2] for r in rects)
        ys0 = min(r[1] for r in rects)
        ys1 = max(r[1] + r[3] for r in rects)
        edge_w, edge_h = (xs1 - xs0) / MM, (ys1 - ys0) / MM
        assert abs(edge_w - edge_mm) < tol_mm and abs(edge_h - edge_mm) < tol_mm, \
            f"id {tid}: black square {edge_w:.4f} x {edge_h:.4f} mm, expected {edge_mm}"
        cell = geo["cell_mm"] * MM
        n = geo["n"]
        cells = np.zeros((n, n), bool)
        for (x, y, rw, rh) in rects:
            c0, r0 = round((x - xs0) / cell), round((ys1 - (y + rh)) / cell)
            nc, nr = round(rw / cell), round(rh / cell)
            assert abs(rw - nc * cell) < 1e-2 and abs(rh - nr * cell) < 1e-2, f"id {tid}: off-grid rectangle"
            cells[r0:r0 + nr, c0:c0 + nc] = True
        assert np.array_equal(cells, tag_cells(tid, family)), f"id {tid}: drawn cells differ from the dictionary pattern"
        left_mm, right_mm = xs0 / MM, LETTER_MM[0] - xs1 / MM
        assert abs(left_mm - right_mm) < 0.01, f"id {tid}: tag not centred ({left_mm:.3f} / {right_mm:.3f} mm)"
        q = geo["cell_mm"] * QUIET_CELLS
        assert left_mm - q >= PRINTER_MARGIN_MM - 1e-6, f"id {tid}: quiet zone leaves the printable area"
        report.append(f"id {tid}: black square {edge_w:.4f} x {edge_h:.4f} mm (cell {geo['cell_mm']:.4f} mm), "
                      f"pattern matches {family}, quiet zone {q:.2f} mm inside {PRINTER_MARGIN_MM} mm margins")
    return report


def render_pngs(pdf, dpi=100):
    """PNG per page next to the PDF via pdftoppm; returns the file list ([] if pdftoppm is missing)."""
    exe = shutil.which("pdftoppm")
    if not exe:
        return []
    pdf = Path(pdf)
    stem = pdf.with_suffix("")
    subprocess.run([exe, "-r", str(dpi), "-png", str(pdf), str(stem)], check=True)
    return sorted(pdf.parent.glob(stem.name + "-*.png"))


def _ids(values):
    out = []
    for v in values:
        for part in str(v).split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-")
                out += list(range(int(a), int(b) + 1))
            else:
                out.append(int(part))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="prints/floor_board_letter.pdf")
    ap.add_argument("--ids", nargs="+", default=["0-8"], help="tag ids, e.g. 0-8 or 0 1 2 or 0,1,2 (first = origin sheet)")
    ap.add_argument("--edge-mm", type=float, default=DEFAULT_EDGE_MM, help="black square edge (default 150)")
    ap.add_argument("--family", default="apriltag_36h11", choices=sorted(_FAMILIES))
    ap.add_argument("--no-instructions", action="store_true", help="omit the layout page")
    ap.add_argument("--png-dpi", type=int, default=0, help="also write page PNGs at this dpi (needs pdftoppm)")
    a = ap.parse_args(argv)
    ids = _ids(a.ids)
    out = build_pdf(a.out, ids, a.edge_mm, a.family, instructions=not a.no_instructions)
    try:
        for line in verify_pdf(out, ids, a.edge_mm, a.family, instructions=not a.no_instructions):
            print("check:", line)
    except ImportError:
        print("check skipped: pip install pypdf to verify the page size and tag edge", file=sys.stderr)
    print(f"wrote {out} ({len(ids)} tag sheets" + (" + layout page" if not a.no_instructions else "") +
          f"). Print at 100 %, then measure the black square.")
    if a.png_dpi:
        pngs = render_pngs(out, a.png_dpi)
        print(f"wrote {len(pngs)} PNG previews at {a.png_dpi} dpi" if pngs else "pdftoppm not found: no PNGs written")


if __name__ == "__main__":
    main()
