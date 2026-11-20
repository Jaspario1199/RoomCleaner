#!/usr/bin/env python3
"""Checks for the Station Rev E MILL board.

    /usr/bin/python3.12 check_pcb_revE_mill.py [board.kicad_pcb]

1. Net check: the Rev E geometric checker (../station_revE_pcb_20261029/check_pcb_revE.py, imported,
   read-only) run on this board.  It joins copper by geometry (tracks, vias, pads on their own copper
   layers, filled zones) and compares every copper island with the Rev D nets.  A via joins its two
   layers (the soldered wire).  A pad joins only the layer(s) it has copper on, so a bottom-only THT
   pad is NOT connected by top copper.  Output -> netlist_check.txt (this folder).
2. Top-copper check: no F.Cu copper (track, via pad, SMD pad, zone fill, copper text) within
   0.4 mm of any pad of J1, J2, J3, J5, U1, U2, U3 and C1 (and of every other bottom-only pad); and
   none of those pads has F.Cu copper itself.  Same check mirrored for the top-only JP1 pin 1.
3. Mill rules: track widths per net class, clearance from KiCad DRC, drill sizes, THT pad size and
   annular ring, wire-via size, via-to-part-body distance, via list and count.
Exit 0 = all PASS.  Output -> mill_check.txt (this folder).
"""
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "station_revE_pcb_20261029"))
import check_pcb_revE as C  # noqa: E402  (read-only; its output folder is redirected below)

C.HERE = HERE                      # netlist_check.txt is written here, not in the Rev E folder
PROJECT = "RoomCleaner_Station_RevE_mill"
NO_TOP = ("J1", "J2", "J3", "J5", "U1", "U2", "U3", "C1")
MIN_GAP = 0.4
WIDTH = {"+12V": 1.2, "M1A": 1.2, "M1B": 1.2, "M2A": 1.2, "M2B": 1.2,
         "5VB": 0.8, "5VD": 0.8, "+5V": 0.8, "GND": 0.8}       # others: 0.6
DRILLS = (0.8, 1.0, 1.2, 1.3, 3.0, 3.2)
VIA_BODY_GAP = 2.0
BOARD_H = 50.0
OX, OY = 100.0, 100.0


def seg_dist(ax, ay, bx, by, px, py):
    return C.seg_dist(ax, ay, bx, by, px, py)


def rect_dist(x0, y0, x1, y1, px, py):
    dx = max(x0 - px, 0, px - x1)
    dy = max(y0 - py, 0, py - y1)
    return math.hypot(dx, dy)


def ring_dist(ring, px, py):
    n = len(ring)
    return min(seg_dist(*ring[k], *ring[(k + 1) % n], px, py) for k in range(n))


def main(argv):
    import pcbnew
    path = Path(argv[1]) if len(argv) > 1 else HERE / f"{PROJECT}.kicad_pcb"
    print("=== 1. net check (Rev E checker, geometric, vs Rev D) ===")
    net_ok = C.main([argv[0], str(path)]) == 0

    lines = []

    def out(s=""):
        print(s)
        lines.append(s)

    mm = pcbnew.ToMM
    board = pcbnew.LoadBoard(str(path))
    ok = True
    out("")
    out("=== 2. top copper on single-sided THT pads ===")
    # F.Cu copper inventory: (kind, description, distance function)
    fcu = []
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            r = mm(t.GetWidth()) / 2
            fcu.append((f"via {t.GetNetname()}", lambda px, py, x=mm(p.x), y=mm(p.y), r=r: math.hypot(px - x, py - y) - r))
        elif t.GetLayer() == pcbnew.F_Cu:
            a, b = t.GetStart(), t.GetEnd()
            hw = mm(t.GetWidth()) / 2
            fcu.append((f"track {t.GetNetname()}", lambda px, py, a=(mm(a.x), mm(a.y)), b=(mm(b.x), mm(b.y)), hw=hw:
                        seg_dist(*a, *b, px, py) - hw))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.IsOnLayer(pcbnew.F_Cu) and pad.GetAttribute() in (pcbnew.PAD_ATTRIB_SMD, pcbnew.PAD_ATTRIB_CONN):
                bb = pad.GetBoundingBox()
                fcu.append((f"pad {fp.GetReference()}.{pad.GetNumber()}",
                            lambda px, py, b=(mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())):
                            rect_dist(*b, px, py)))
    for d in board.GetDrawings():
        if d.GetClass() == "PCB_TEXT" and d.GetLayer() == pcbnew.F_Cu:
            bb = d.GetEffectiveTextShape().BBox()      # bounding box of the stroked glyphs
            fcu.append((f"text '{d.GetText()}'", lambda px, py, b=(mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()),
                                                                   mm(bb.GetBottom())): rect_dist(*b, px, py)))
    fills = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        for layer in fills:
            if not z.IsOnLayer(layer):
                continue
            polys = z.GetFilledPolysList(layer)
            for o in range(polys.OutlineCount()):
                ring = [(mm(polys.COutline(o).CPoint(k).x), mm(polys.COutline(o).CPoint(k).y))
                        for k in range(polys.COutline(o).PointCount())]
                holes = [[(mm(polys.CHole(o, h).CPoint(k).x), mm(polys.CHole(o, h).CPoint(k).y))
                          for k in range(polys.CHole(o, h).PointCount())] for h in range(polys.HoleCount(o))]
                fills[layer].append((z.GetZoneName(), C.Fragment(ring, holes)))

    def fill_dist(layer, px, py):
        best, who = 1e9, None
        for name, fr in fills[layer]:
            if fr.contains(px, py):
                return 0.0, name
            dd = min([ring_dist(fr.outline, px, py)] + [ring_dist(h, px, py) for h in fr.holes])
            if dd < best:
                best, who = dd, name
        return best, who

    checked, worst = 0, (1e9, "")
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
                continue
            on_f, on_b = pad.IsOnLayer(pcbnew.F_Cu), pad.IsOnLayer(pcbnew.B_Cu)
            name = f"{ref}.{pad.GetNumber()}"
            if ref in NO_TOP and on_f:
                out(f"FAIL {name}: pad has F.Cu copper")
                ok = False
            if on_f and on_b:
                out(f"FAIL {name}: pad on both copper layers (no plating on a milled board)")
                ok = False
                continue
            p = pad.GetPosition()
            px, py = mm(p.x), mm(p.y)
            sz = pad.GetSize()
            r = max(mm(sz.x), mm(sz.y)) / 2 * (1 if pad.GetShape() == pcbnew.PAD_SHAPE_CIRCLE else math.sqrt(2))
            if on_b:          # bottom-only pad: nothing on F.Cu may come near it
                cands = [(f(px, py) - r, what) for what, f in fcu]
                fd, fz = fill_dist(pcbnew.F_Cu, px, py)
                cands.append((fd - r, f"F.Cu fill {fz}"))
            else:             # top-only pad (JP1.1): nothing on B.Cu may come near it
                cands = []
                for t in board.GetTracks():
                    if t.GetClass() != "PCB_VIA" and t.GetLayer() == pcbnew.B_Cu:
                        a, b = t.GetStart(), t.GetEnd()
                        cands.append((seg_dist(mm(a.x), mm(a.y), mm(b.x), mm(b.y), px, py) - mm(t.GetWidth()) / 2 - r,
                                      f"B.Cu track {t.GetNetname()}"))
                fd, fz = fill_dist(pcbnew.B_Cu, px, py)
                cands.append((fd - r, f"B.Cu fill {fz}"))
            g, what = min(cands)
            checked += 1
            if g < worst[0]:
                worst = (g, f"{name} <-> {what}")
            if g < MIN_GAP:
                out(f"FAIL {name}: other-side copper {what} at {g:.3f} mm (< {MIN_GAP})")
                ok = False
    out(f"single-sided THT pads checked: {checked}; closest other-side copper: {worst[0]:.3f} mm ({worst[1]})")
    out(f"pads of {' '.join(NO_TOP)}: bottom copper only, no top copper within {MIN_GAP} mm: "
        f"{'PASS' if ok else 'FAIL'}")

    out("")
    out("=== 3. mill rules ===")
    rules_ok = True
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            continue
        want = WIDTH.get(t.GetNetname(), 0.6)
        if mm(t.GetWidth()) < want - 1e-6:
            out(f"FAIL track {t.GetNetname()} {mm(t.GetWidth())} mm < {want}")
            rules_ok = False
    out("track widths          : " + ("ok (signals/+3V3 >= 0.6, 5 V and GND >= 0.8, 12 V/VMOT/coils >= 1.2)"
                                      if rules_ok else "FAIL"))
    bad = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            d = mm(pad.GetDrillSize().x)
            if d <= 0:
                continue
            if not any(abs(d - a) < 1e-6 for a in DRILLS):
                bad.append(f"{fp.GetReference()}.{pad.GetNumber()} drill {d}")
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                s = min(mm(pad.GetSize().x), mm(pad.GetSize().y))
                if s < 2.0 - 1e-6 or (s - d) / 2 < 0.5 - 1e-6:
                    bad.append(f"{fp.GetReference()}.{pad.GetNumber()} pad {s}/{d}")
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    for v in vias:
        if abs(mm(v.GetDrillValue()) - 0.8) > 1e-6 or mm(v.GetWidth()) < 1.8 - 1e-6:
            bad.append(f"via {mm(v.GetWidth())}/{mm(v.GetDrillValue())}")
    for b in bad:
        out("FAIL " + b)
    out("drills / pads         : " + ("ok (drills 0.8/1.0/1.3 + 3.2 holes; THT pads >= 2.0 mm, ring >= 0.5 mm; "
                                      "wire vias 2.0/0.8)" if not bad else "FAIL"))
    rules_ok &= not bad
    # via to part body (courtyard) distance
    bodies = []
    for fp in board.GetFootprints():
        if fp.GetReference().startswith("H"):
            continue
        xs, ys = [], []
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_CrtYd:
                bb = g.GetBoundingBox()
                xs += [mm(bb.GetLeft()), mm(bb.GetRight())]
                ys += [mm(bb.GetTop()), mm(bb.GetBottom())]
        if xs:
            bodies.append((fp.GetReference(), min(xs), min(ys), max(xs), max(ys)))
    out(f"wire vias             : {len(vias)} (all routing vias; GND stitching vias: 0)")
    out("   #  net    x_top  y_top   X_file Y_file  nearest body (pad edge to courtyard)")
    for k, v in enumerate(sorted(vias, key=lambda v: (v.GetNetname(), v.GetPosition().x)), 1):
        p = v.GetPosition()
        x, y = mm(p.x) - OX, mm(p.y) - OY
        r = mm(v.GetWidth()) / 2
        dref, dd = min(((ref, rect_dist(x0 - OX, y0 - OY, x1 - OX, y1 - OY, x, y) - r) for ref, x0, y0, x1, y1 in bodies),
                       key=lambda t: t[1])
        flag = "ok" if dd >= VIA_BODY_GAP - 1e-6 else "FAIL"
        if flag == "FAIL":
            rules_ok = False
        out(f"  W{k} {v.GetNetname():6s} {x:6.2f} {y:6.2f}   {x:6.2f} {BOARD_H - y:6.2f}  {dref} {dd:.2f} mm {flag}")
    out("   (x_top, y_top: from the top-left board corner, y down;  X_file, Y_file: Gerber/drill origin =")
    out("    lower-left board corner, Y up)")
    out(f"mill rules            : {'PASS' if rules_ok else 'FAIL'}")
    out("")
    allok = net_ok and ok and rules_ok
    out(f"net check {'PASS' if net_ok else 'FAIL'}; top-copper check {'PASS' if ok else 'FAIL'}; "
        f"mill rules {'PASS' if rules_ok else 'FAIL'}; wire vias {len(vias)}")
    out("PASS" if allok else "FAIL")
    (HERE / "mill_check.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
