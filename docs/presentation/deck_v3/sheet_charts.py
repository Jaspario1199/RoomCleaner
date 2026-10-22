"""Crop the Google Sheets charts out of the Sheet's PDF export for the deck.

The charts are made in the Google Sheet "RoomCleaner engineering calculations" (owner Jasper Buntinx). Export it with
File > Download > PDF (or the Drive API, application/pdf) to docs/presentation/deck_v3/sheet_export.pdf, then:

    /usr/bin/python3 docs/presentation/deck_v3/sheet_charts.py      -> docs/presentation/deck_v3/fig/sheet_*.png
    /usr/bin/python3 docs/presentation/deck_v3/sheet_charts.py <export.pdf> <out_dir>   (another export, e.g. deck_v5)

Each tab prints on its own page; the chart is the large white rectangle on the right of the page, found from the PDF's
vector drawing, then rendered at high resolution with pdftoppm and cropped just inside its border.
"""
import subprocess
import sys
from pathlib import Path

import pdfplumber

HERE = Path(__file__).parent
PDF = HERE / "sheet_export.pdf"
OUT = HERE / "fig"
DPI = 900
TABS = {"Cable tension": "sheet_cable_tension", "Winch pull": "sheet_winch_pull", "Heat fin": "sheet_heat_fin",
        "Motor case temperature": "sheet_motor_temperature", "Wiring": "sheet_wiring", "Bead homing": "sheet_bead_homing",
        "Floor board": "sheet_floor_board", "Lift budget": "sheet_lift_budget"}


def main(PDF=PDF, OUT=OUT):
    OUT.mkdir(exist_ok=True)
    done = []
    with pdfplumber.open(PDF) as pdf:
        for n, page in enumerate(pdf.pages, 1):
            first = (page.extract_text() or "").strip().splitlines()[:1]
            name = next((v for k, v in TABS.items() if first and first[0].startswith(k)), None)
            if not name:
                continue
            boxes = [r for r in page.rects if r["x0"] > page.width * 0.4 and r["width"] > 100 and r["height"] > 60]
            if not boxes:
                sys.exit(f"page {n} ({name}): no chart rectangle found")
            r = max(boxes, key=lambda b: b["width"] * b["height"])
            s = DPI / 72.0
            inset = 1.0                                  # pt, stays inside the chart's border line
            x, y = int((r["x0"] + inset) * s), int((r["top"] + inset) * s)
            w, h = int((r["width"] - 2 * inset) * s), int((r["height"] - 2 * inset) * s)
            subprocess.run(["pdftoppm", "-r", str(DPI), "-f", str(n), "-l", str(n), "-x", str(x), "-y", str(y), "-W", str(w), "-H", str(h),
                            "-png", "-singlefile", str(PDF), str(OUT / name)], check=True, stderr=subprocess.DEVNULL)
            done.append(f"{name}.png {w}x{h}")
    print("\n".join(done))
    if len(done) != len(TABS):
        sys.exit(f"expected {len(TABS)} charts, cropped {len(done)}")


if __name__ == "__main__":
    main(*(Path(a) for a in sys.argv[1:3]))
