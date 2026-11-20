#!/usr/bin/env python3
"""Build the RoomCleaner Station Rev E MILL variant: a double-sided board milled in-house on the
Fab Lab's Makera Carvera (FR4, copper / insulator / copper, NO through-hole plating).

    /usr/bin/python3.12 build_pcb_revE_mill.py              # everything (re-uses routing_mill.json)
    /usr/bin/python3.12 build_pcb_revE_mill.py --reroute    # run the router again

Re-uses the Rev E generator (../station_revE_pcb_20261029/build_pcb_revE.py) and its router
(pathfinder.py, maze_router.py) by import.  The Rev E module's output globals (folder, project
name, footprint library) are pointed at THIS folder before any of its functions run, so nothing
in the Rev E or Rev D folders is written (bytecode writing is disabled too).

What differs from Rev E (mill rules):
  * Through-hole pads exist on ONE copper layer only.  Sockets, JST-XH, the screw terminal, C1,
    JP1 pin 2 and the test pads: B.Cu only (their bodies sit flush on the top side, so they can
    only be soldered underneath).  Exception: JP1 pin 1 is F.Cu only (soldered on top with the
    header's plastic spacer slid up, see README).
  * F.Cu rule areas (keep-outs, pad radius + 0.45 mm) over every bottom-only THT pad, so no top
    copper (track, via, pour) comes near those pins.
  * Vias are WIRE VIAS: 0.8 mm drill, 2.0 mm pads, each pad edge >= 2 mm from every part body
    (courtyard), soldered on both sides with a wire.  The router charges a high cost per via.
  * No GND stitching vias.  GND pour on both layers, 0.5 mm clearance, 0.6 mm minimum width,
    0.8 mm thermal spokes, islands removed.
  * One Excellon file with every hole (all non-plated), including two 3.0 mm registration-pin
    holes outside the board, inside the 90 x 70 mm stock.
  * Essential labels as copper text (F.Cu, plus a B.Cu side marker); silkscreen kept for the
    KiCad documentation only.
Writes into this folder only.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REVE = HERE.parent / "station_revE_pcb_20261029"
sys.path.insert(0, str(REVE))
import build_pcb_revE as E  # noqa: E402  (read-only re-use; its output globals are redirected below)
import maze_router as mr  # noqa: E402
import pathfinder as pf  # noqa: E402

PROJECT = "RoomCleaner_Station_RevE_mill"
LIBNICK = "RoomCleanerRevEMill"
TITLE = "RoomCleaner Station Rev E mill (Carvera, double-sided, unplated)"
DATE = "2026-11-20"
BOARD_W, BOARD_H = E.BOARD_W, E.BOARD_H

# ---- redirect every Rev E output global to this folder ---------------------------------------
E.HERE = HERE
E.PROJECT = PROJECT
E.LIBNICK = LIBNICK
E.LIBDIR = HERE / f"{LIBNICK}.pretty"
E.TITLE = TITLE
E.DATE = DATE
E.PAD_LAYERS = '(layers "B.Cu" "B.Mask")'     # every generated THT pad: bottom copper only

# ---- mill rules -------------------------------------------------------------------------------
VIA_D, VIA_DRILL = 2.0, 0.8            # wire via: 0.8 mm hole, 2.0 mm pad on both sides
E.VIA_D, E.VIA_DRILL = VIA_D, VIA_DRILL
pf.VIA_R = VIA_D / 2                   # router: via pad radius
E.ZONE_CLR, E.ZONE_MIN_W, E.SPOKE_W, E.SPOKE_GAP = 0.5, 0.6, 0.8, 0.5
VIA_BODY_GAP = 2.0                     # via pad edge to any part body (courtyard) >= 2 mm
VIA_SCREW_R = 3.5 + 0.3                # M3 washer radius + margin: wire stub stays clear of it
UNDER_MODULES = 0                      # 1: vias allowed under the plugged-in XIAO / A4988 modules
VIA_COST = 500.0                       # grid cells (0.254 mm) of detour one via is worth
TOP_KEEPOUT_GAP = 0.45                 # F.Cu keep-out radius = pad radius + this
KEEPOUT_GAP_B = 0.45                   # B.Cu keep-out under the top-only JP1 pin 1
ALLOWED_DRILLS = (0.8, 1.0, 1.2, 1.3, 3.0, 3.2)
NO_TOP_COPPER = ("J1", "J2", "J3", "J5", "U1", "U2", "U3", "C1")   # pads checked by check_top_copper()

# registration pins (file coordinates: origin = board lower-left corner, X right, Y up, mm)
STOCK = (-10.0, -10.0, 80.0, 60.0)     # 90 x 70 mm stock rectangle, board centred in it
FLIP_AXIS_X = BOARD_W / 2              # flip the stock left-right about this vertical line
REG_PINS = [("REG1", FLIP_AXIS_X, -5.5), ("REG2", FLIP_AXIS_X, 54.5)]
REG_D = 3.0

# Placement: Rev E unchanged except the parts listed here (see README "Changes vs Rev E").
PLACE = dict(E.PLACE)
E.PLACE = PLACE

# Copper labels: (text, x, y, layer 'F'/'B', size, rotation).  Board mm, top view, y down.
COPPER_TEXT = []


def load_copper_text():
    COPPER_TEXT[:] = [
        ("+12V", 58.6, 17.2, "F", 1.6, 0),
        ("GND", 63.2, 7.6, "F", 1.4, 0),
        ("MOTOR", 62.0, 35.2, "F", 1.4, 0),
        ("1A", 61.9, 30.48, "F", 1.6, 0),
        ("ENC", 13.9, 41.0, "F", 1.6, 0),
        ("SW", 33.2, 46.4, "F", 1.6, 0),
        ("VMOT", 52.07, 8.45, "F", 1.4, 0),
        ("USB", 2.2, 17.78, "F", 1.6, 90),
        ("O+", 29.21, 7.6, "F", 1.6, 0),
        ("C1+", 56.0, 1.9, "F", 1.4, 0),
        ("JP1 ON=12V", 14.0, 7.35, "F", 1.2, 0),
        ("RC STATION E-MILL", 45.0, 38.0, "F", 1.6, 0),
        ("2026-11-20 TOP", 45.0, 40.6, "F", 1.4, 0),
        ("BOTTOM E-MILL", 45.0, 39.4, "B", 1.6, 0),
    ]


# ---------------------------------------------------------------------------
# footprints
# ---------------------------------------------------------------------------
def write_library():
    names = E.write_library()                 # generated into LIBNICK.pretty, pads B.Cu only
    # JP1 exception: pin 1 (diode side, 5VD) on F.Cu only, pin 2 (+5V) on B.Cu only
    lib, name, path = names["HDR2"]
    f = Path(path) / f"{name}.kicad_mod"
    t = f.read_text()
    t2 = re.sub(r'\(pad "1" thru_hole rect ([^\n]*?)\(layers "B\.Cu" "B\.Mask"\)',
                r'(pad "1" thru_hole circle \1(layers "F.Cu" "F.Mask")', t, count=1)
    assert t2 != t, "JP1 pad 1 not patched"
    f.write_text(t2)
    return names


def write_libtables():
    E.write_libtables()
    t = (HERE / "fp-lib-table").read_text()
    t = t.replace("generated by build_pcb_revE.py", "generated by build_pcb_revE_mill.py")
    (HERE / "fp-lib-table").write_text(t)


# ---------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------
def courtyards(pcbnew, board, under_modules=False):
    """[(ref, x0, y0, x1, y1)] part bodies for the via rule: courtyard bounding boxes.  With
    under_modules, the plug-in modules XIAO (U2) and A4988 (U3) count only as their header strips
    (the module itself is plugged in after the vias are soldered and sits 8.5 mm above the board)."""
    out = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("H"):
            continue
        if under_modules and ref in ("U2", "U3"):
            rows = {}
            for pad in fp.Pads():
                x, y = E.bxy(pcbnew, pad.GetPosition())
                rows.setdefault(round(x if ref == "U3" else y, 2), []).append((x, y))
            for pts in rows.values():
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                out.append((ref, min(xs) - 1.27 - 0.25, min(ys) - 1.27 - 0.25, max(xs) + 1.27 + 0.25,
                            max(ys) + 1.27 + 0.25))
            continue
        xs, ys = [], []
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_CrtYd:
                bb = g.GetBoundingBox()
                xs += [pcbnew.ToMM(bb.GetLeft()) - E.OX, pcbnew.ToMM(bb.GetRight()) - E.OX]
                ys += [pcbnew.ToMM(bb.GetTop()) - E.OY, pcbnew.ToMM(bb.GetBottom()) - E.OY]
        if xs:
            out.append((ref, min(xs), min(ys), max(xs), max(ys)))
    return out


def make_text(pcbnew, board, s, x, y, layer, size, rot):
    lid = pcbnew.F_Cu if layer == "F" else pcbnew.B_Cu
    th = 0.4 if size >= 1.5 else 0.35
    t = E.text(pcbnew, board, s, x, y, lid, size=size, th=th, rot=rot)
    if layer == "B":
        t.SetMirrored(True)
    return t


def text_items(pcbnew):
    """Router obstacles for the copper text (bounding boxes, both nets blocked)."""
    tmp = pcbnew.BOARD()
    items = []
    for s, x, y, layer, size, rot in COPPER_TEXT:
        t = make_text(pcbnew, tmp, s, x, y, layer, size, rot)
        bb = t.GetEffectiveTextShape().BBox()          # the stroked glyphs, not the text frame
        x0, x1 = pcbnew.ToMM(bb.GetLeft()) - E.OX, pcbnew.ToMM(bb.GetRight()) - E.OX
        y0, y1 = pcbnew.ToMM(bb.GetTop()) - E.OY, pcbnew.ToMM(bb.GetBottom()) - E.OY
        items.append(dict(kind="rect", cx=(x0 + x1) / 2, cy=(y0 + y1) / 2, hw=(x1 - x0) / 2, hh=(y1 - y0) / 2,
                          net="__TEXT__", clr=0.5, layers=(0,) if layer == "F" else (1,), hole=False, text=s))
    return items


def mill_items(pcbnew, board):
    """Rev E obstacle items plus: every THT pad blocks the layer it is NOT on (no copper of any net,
    its own included, may come within pad radius + 0.5 mm there), plus the copper text."""
    items, centres = E.pad_items(pcbnew, board)
    extra = []
    for it in items:
        if not it.get("hole") or len(it["layers"]) != 1:
            continue
        # the keep-out circle drawn by add_keepouts(); r - 0.5 with clr 0.5, so the track edge stays
        # at least hw + margin outside the keep-out for every net class (all clearances <= 0.5)
        r = it["r"] if it["kind"] == "circle" else math.hypot(it["hw"], it["hh"])
        gap = KEEPOUT_GAP_B if it["layers"] == (0,) else TOP_KEEPOUT_GAP
        extra.append(dict(kind="circle", cx=it["cx"], cy=it["cy"], r=r + gap - 0.5, net="__THT__",
                          clr=0.5, layers=(1 - it["layers"][0],), hole=False))
    txt = text_items(pcbnew)
    for t in txt:            # copper text must stay 0.4 mm outside every keep-out on its layer
        for e in extra:
            if e["layers"] == t["layers"]:
                dx = max(abs(e["cx"] - t["cx"]) - t["hw"], 0)
                dy = max(abs(e["cy"] - t["cy"]) - t["hh"], 0)
                if math.hypot(dx, dy) < e["r"] + 0.5 + 0.4:
                    raise SystemExit(f"copper text '{t['text']}' too close to a single-sided THT pad")
    return items + extra + txt, centres


# ---------------------------------------------------------------------------
# routing (Rev E route_all with layer-restricted pins, wire-via rules)
# ---------------------------------------------------------------------------
def route_all(pcbnew, board, items, centres, nets, iters, via_cost=None, order=None, pres_mul=1.5,
              under_modules=False, log=print):
    import numpy as np
    grid = mr.Grid(BOARD_W, BOARD_H, E.GRID, E.EDGE_CLR)
    # vias: pad edge >= VIA_BODY_GAP from every courtyard, clear of screw heads, off every pad
    via_bad = grid.edge_dist < E.EDGE_CLR + pf.VIA_R + 0.05
    for ref, x0, y0, x1, y1 in courtyards(pcbnew, board, under_modules):
        it = dict(kind="rect", cx=(x0 + x1) / 2, cy=(y0 + y1) / 2, hw=(x1 - x0) / 2, hh=(y1 - y0) / 2)
        R = VIA_BODY_GAP + pf.VIA_R
        sl, d = grid.dist_window(it, R)
        if sl is not None:
            via_bad[sl] |= d < R
    for hx, hy in E.HOLES:
        sl, d = grid.dist_window(dict(kind="circle", cx=hx, cy=hy, r=0), VIA_SCREW_R + pf.VIA_R)
        via_bad[sl] |= d < VIA_SCREW_R + pf.VIA_R
    pnets, hard, vok, exact = [], {}, {}, {}
    for name in E.ROUTE_ORDER:
        w, clr = E.CLASSES[E.ncls(name)]
        masks = [grid.blocked_mask(items, name, clr, w / 2, layer=l) for l in (0, 1)]
        pins = []
        for rp in nets[name]:
            x, y, _, layers = centres[rp]
            i, j = grid.cell(x, y)
            k = grid.idx(i, j)
            for l in layers:
                masks[l][j, i] = False
            pins.append((rp, x, y, k, layers))
            exact[k] = (x, y)
        hard[name] = [bytearray((~m).astype(np.uint8).ravel().tobytes()) for m in masks]
        mv = (grid.blocked_mask(items, name, max(clr, 0.5), pf.VIA_R, layer=0)
              | grid.blocked_mask(items, name, max(clr, 0.5), pf.VIA_R, layer=1) | via_bad)
        vok[name] = bytearray((~mv).astype(np.uint8).ravel().tobytes())
        pnets.append(pf.Net(name, w / 2, pins))
    neg = pf.Negotiator(grid, pnets, hard, vok, via_cost=via_cost or VIA_COST)
    ok = neg.run(order or E.ROUTE_ORDER, iters=iters, pres_mul=pres_mul, log=log)
    if ok:
        reduce_vias(neg, log=log)
    conf, _ = neg.conflicts()
    tracks = neg.tracks(lambda n: E.CLASSES[E.ncls(n)][0], exact)
    return dict(ok=ok, conflicts=sum(conf.values()), tracks=tracks, vias=neg.via_list(),
                length=round(sum(math.hypot(t[4] - t[2], t[5] - t[3]) for t in tracks), 1))


def reduce_vias(neg, rounds=3, log=print):
    """Greedy clean-up after negotiation: re-route one net at a time with every other net's copper
    as a hard obstacle (huge congestion price) and a much higher via price; keep the new route
    only if it is conflict-free and has fewer vias (ties: shorter)."""
    def nvias(n):
        return len(neg.nets[n].vias)

    def length(n):
        return sum(len(c) for _, c in neg.nets[n].paths)

    base_cost = neg.via_cost
    for rnd in range(rounds):
        improved = False
        for name in sorted(neg.nets, key=lambda k: -nvias(k)):
            net = neg.nets[name]
            old = (list(net.paths), list(net.vias), nvias(name), length(name))
            neg.via_cost = base_cost * 6
            routed = neg.route(name, 1e5)
            neg.via_cost = base_cost
            conf, _ = neg.conflicts() if routed else ({name: 1}, None)
            better = routed and not conf and (nvias(name), length(name)) < (old[2], old[3])
            if better and nvias(name) < old[2]:
                log(f"   via clean-up: {name} {old[2]} -> {nvias(name)} vias")
                improved = True
            if not better:
                net.paths, net.vias = old[0], old[1]
                neg._update_maps(name)
        if not improved:
            break


# ---------------------------------------------------------------------------
# finishing
# ---------------------------------------------------------------------------
def add_keepouts(pcbnew, board):
    """Rule area on the copper layer a THT pad is NOT on: no tracks, vias or pour there."""
    n = 0
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
                continue
            on_f, on_b = pad.IsOnLayer(pcbnew.F_Cu), pad.IsOnLayer(pcbnew.B_Cu)
            if on_f and on_b:
                continue
            layer = pcbnew.B_Cu if on_f else pcbnew.F_Cu
            x, y = E.bxy(pcbnew, pad.GetPosition())
            sz = pad.GetSize()
            r = max(pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y)) / 2
            if pad.GetShape() != pcbnew.PAD_SHAPE_CIRCLE:
                r *= math.sqrt(2)
            r += KEEPOUT_GAP_B if on_f else TOP_KEEPOUT_GAP
            z = pcbnew.ZONE(board)
            z.SetIsRuleArea(True)
            z.SetLayer(layer)
            z.SetDoNotAllowCopperPour(True)
            z.SetDoNotAllowTracks(True)
            z.SetDoNotAllowVias(True)
            z.SetDoNotAllowPads(False)
            z.SetDoNotAllowFootprints(False)
            z.SetZoneName(f"NOCU_{fp.GetReference()}_{pad.GetNumber()}")
            ol = z.Outline()
            ol.NewOutline()
            for k in range(32):
                a = 2 * math.pi * k / 32
                ol.Append(pcbnew.FromMM(E.OX + x + r * math.cos(a)), pcbnew.FromMM(E.OY + y + r * math.sin(a)))
            board.Add(z)
            n += 1
    return n


def add_registration_drawing(pcbnew, board):
    """Stock rectangle, flip axis and registration pins on Dwgs.User (documentation layer)."""
    def P(xf, yf):           # file coords (Y up, origin lower-left) -> board coords (y down)
        return E.V(pcbnew, xf, BOARD_H - yf)

    x0, y0, x1, y1 = STOCK
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a))
        s.SetEnd(P(*b))
        s.SetLayer(pcbnew.Dwgs_User)
        s.SetWidth(pcbnew.FromMM(0.2))
        board.Add(s)
    for yy in range(int(y0), int(y1), 4):        # dashed flip axis
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(FLIP_AXIS_X, yy))
        s.SetEnd(P(FLIP_AXIS_X, min(yy + 2, y1)))
        s.SetLayer(pcbnew.Dwgs_User)
        s.SetWidth(pcbnew.FromMM(0.15))
        board.Add(s)
    for name, xf, yf in REG_PINS:
        c = pcbnew.PCB_SHAPE(board)
        c.SetShape(pcbnew.SHAPE_T_CIRCLE)
        c.SetCenter(P(xf, yf))
        c.SetEnd(P(xf + REG_D / 2, yf))
        c.SetLayer(pcbnew.Dwgs_User)
        c.SetWidth(pcbnew.FromMM(0.2))
        board.Add(c)
        E.text(pcbnew, board, f"{name} 3.0 pin", xf + 7.5, BOARD_H - yf, pcbnew.Dwgs_User, size=1.2, th=0.15)
    E.text(pcbnew, board, "stock 90 x 70 mm, flip left-right about the dashed axis", BOARD_W / 2,
           BOARD_H - y0 - 1.6, pcbnew.Dwgs_User, size=1.2, th=0.15)


def copper_labels(pcbnew, board):
    for s, x, y, layer, size, rot in COPPER_TEXT:
        make_text(pcbnew, board, s, x, y, layer, size, rot)


def finish_silk(pcbnew, board):
    for d in board.GetDrawings():
        if d.GetClass() == "PCB_TEXT" and d.GetText() == "RoomCleaner Station Rev E":
            d.SetText("RoomCleaner Station Rev E mill")


def patch_project():
    E.patch_project()
    path = HERE / f"{PROJECT}.kicad_pro"
    d = json.loads(path.read_text())
    rules = d["board"]["design_settings"]["rules"]
    rules.update({"min_through_hole_diameter": 0.8, "min_via_diameter": VIA_D, "min_via_annular_width": 0.5,
                  "min_hole_to_hole": 0.5, "min_hole_clearance": 0.4, "min_connection": 0.6})
    for c in d["net_settings"]["classes"]:
        c["via_diameter"], c["via_drill"] = VIA_D, VIA_DRILL
    path.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# outputs
# ---------------------------------------------------------------------------
def run(cmd, cwd=HERE):
    return E.run(cmd, cwd=cwd)


def holes(pcbnew, board):
    """Every hole as (diameter mm, X, Y) in file coordinates (origin board lower-left, Y up)."""
    out = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetDrillSize().x <= 0:
                continue
            x, y = E.bxy(pcbnew, pad.GetPosition())
            out.append((round(pcbnew.ToMM(pad.GetDrillSize().x), 3), x, BOARD_H - y, f"{fp.GetReference()}.{pad.GetNumber()}"))
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            x, y = E.bxy(pcbnew, t.GetPosition())
            out.append((round(pcbnew.ToMM(t.GetDrillValue()), 3), x, BOARD_H - y, f"via {t.GetNetname()}"))
    for name, xf, yf in REG_PINS:
        out.append((REG_D, xf, yf, name))
    return out


def write_excellon(pcbnew, board, path):
    hs = holes(pcbnew, board)
    tools = sorted({d for d, *_ in hs})
    bad = [d for d in tools if not any(abs(d - a) < 1e-6 for a in ALLOWED_DRILLS)]
    if bad:
        raise SystemExit(f"drill sizes outside the mill set: {bad}")
    L = ["M48", f"; {TITLE}", "; ALL HOLES NON-PLATED (milled/drilled on the Carvera; vias are wire vias)",
         "; origin = board lower-left corner, X right, Y up, mm; includes 2 x 3.0 mm registration-pin holes",
         "; #@! TF.FileFunction,NonPlated,1,2,NPTH", "FMAT,2", "METRIC,TZ"]
    for k, d in enumerate(tools, 1):
        L.append(f"T{k}C{d:.3f}")
    L += ["%", "G90", "G05"]
    for k, d in enumerate(tools, 1):
        L.append(f"T{k}")
        for dd, x, y, _ in sorted(hs, key=lambda h: (h[2], h[1])):
            if dd == d:
                L.append(f"X{x:.3f}Y{y:.3f}")
    L += ["T0", "M30"]
    path.write_text("\n".join(L) + "\n")
    return hs, tools


def exports(pcbnew):
    pcb = f"{PROJECT}.kicad_pcb"
    board = pcbnew.LoadBoard(str(HERE / pcb))
    g = HERE / "_gerbers"
    shutil.rmtree(g, ignore_errors=True)
    g.mkdir()
    run(["kicad-cli", "pcb", "export", "gerbers", "-l", "F.Cu,B.Cu,Edge.Cuts,F.Paste,Dwgs.User",
         "--use-drill-file-origin", "--no-protel-ext", "-o", "_gerbers/", pcb])
    # cross-check: KiCad's own merged drill file must hold the same board holes as ours
    run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm",
         "--drill-origin", "plot", "-o", "_gerbers/kicad_check/", pcb])
    hs, tools = write_excellon(pcbnew, board, g / f"{PROJECT}-ALL-NPTH.drl")
    kc = (g / "kicad_check" / f"{PROJECT}.drl").read_text()
    kpts = sorted((round(float(a), 2), round(float(b), 2)) for a, b in re.findall(r"^X([-\d.]+)Y([-\d.]+)", kc, re.M))
    mine = sorted((round(x, 2), round(y, 2)) for d, x, y, n in hs if not n.startswith("REG"))
    if kpts != mine:
        raise SystemExit(f"drill cross-check failed: kicad {len(kpts)} holes, ours {len(mine)}")
    shutil.rmtree(g / "kicad_check")
    for f in list(g.glob("*.gbrjob")):
        f.unlink()
    for f in list(g.iterdir()):          # readable names
        new = f.name.replace(f"{PROJECT}-", f"{PROJECT}_").replace("User_Drawings", "Registration_User_Drawings")
        f.rename(g / new)
    z = HERE / f"{PROJECT}.zip"
    z.unlink(missing_ok=True)
    files = sorted(p.name for p in g.iterdir())
    run(["zip", "-j", "-X", str(z)] + [str(g / f) for f in files])
    print(f"  {z.name}: {', '.join(files)}")
    print(f"  drill: {len(hs)} holes, tools {', '.join(f'{d:.1f}' for d in tools)} mm")
    shutil.rmtree(g)
    run(["kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "front", "--smd-only",
         "--use-drill-file-origin", "-o", f"{PROJECT}_pos.csv", pcb])
    # 1:1 transfer PDFs (fallback): copper + outline + holes; F.Cu mirrored, B.Cu as seen from the top
    run(["kicad-cli", "pcb", "export", "pdf", "-l", "F.Cu,Edge.Cuts,Dwgs.User", "--mirror", "--black-and-white",
         "--drill-shape-opt", "2", "-o", f"{PROJECT}_F.Cu_mirrored_1to1.pdf", pcb])
    run(["kicad-cli", "pcb", "export", "pdf", "-l", "B.Cu,Edge.Cuts,Dwgs.User", "--black-and-white",
         "--drill-shape-opt", "2", "-o", f"{PROJECT}_B.Cu_mirrored_1to1.pdf", pcb])
    # renders: what the milled board looks like (no silkscreen, no mask)
    tmp = HERE / "_render"
    tmp.mkdir(exist_ok=True)
    run(["kicad-cli", "pcb", "export", "pdf", "-l", "F.Cu,F.Paste,Edge.Cuts,Dwgs.User", "--drill-shape-opt", "2",
         "-o", str(tmp / "top.pdf"), pcb])
    run(["kicad-cli", "pcb", "export", "pdf", "-l", "B.Cu,Edge.Cuts,Dwgs.User", "--drill-shape-opt", "2",
         "--mirror", "-o", str(tmp / "bottom.pdf"), pcb])
    for side in ("top", "bottom"):
        run(["pdftoppm", "-r", "300", "-png", "-singlefile", str(tmp / f"{side}.pdf"), str(tmp / side)])
        run(["convert", str(tmp / f"{side}.png"), "-trim", "+repage", "-bordercolor", "white", "-border", "20",
             str(HERE / f"{PROJECT}_{side}.png")])
    shutil.rmtree(tmp)


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reroute", action="store_true")
    ap.add_argument("--route-only", action="store_true")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--iters", type=int, default=60)
    ap.add_argument("--via-cost", type=float, default=VIA_COST)
    ap.add_argument("--seed", type=int, default=-1, help="shuffle the net order (search runs)")
    ap.add_argument("--pres-mul", type=float, default=1.5)
    ap.add_argument("--under-modules", type=int, default=UNDER_MODULES)
    ap.add_argument("--out", default="routing_mill.json")
    ap.add_argument("--move", action="append", default=[], help="REF=x,y placement override (search runs)")
    a = ap.parse_args()
    import pcbnew
    load_copper_text()
    for mv in a.move:
        ref, xy = mv.split("=")
        key, _, _, rot = PLACE[ref]
        PLACE[ref] = (key, *map(float, xy.split(",")), rot)
    pb = E.pbd.Perfboard()
    nets = E.reve_nets(pb)
    for tp, n in E.TESTPADS.items():
        nets[n].add((tp, "1"))
    libnames = write_library()
    write_libtables()
    board, netinfo = E.build_board(pcbnew, nets, libnames)
    items, centres = mill_items(pcbnew, board)
    pcb_path = HERE / f"{PROJECT}.kicad_pcb"
    rpath = HERE / a.out
    if a.reroute or not rpath.exists():
        t0 = time.time()
        order = list(E.ROUTE_ORDER)
        if a.seed >= 0:
            import random
            random.Random(a.seed).shuffle(order)
        res = route_all(pcbnew, board, items, centres, nets, a.iters, via_cost=a.via_cost, order=order,
                        pres_mul=a.pres_mul, under_modules=bool(a.under_modules))
        res["params"] = dict(via_cost=a.via_cost, seed=a.seed, pres_mul=a.pres_mul,
                             under_modules=a.under_modules, order=order)
        print(f"routing: ok={res['ok']} conflicts={res['conflicts']} vias={len(res['vias'])} "
              f"length={res['length']} mm ({time.time() - t0:.0f} s)")
        rpath.write_text(json.dumps(res, indent=1))
    R = json.loads(rpath.read_text())
    if a.route_only:
        return
    if not R["ok"]:
        raise SystemExit("routing_mill.json holds an unfinished routing; run --reroute")
    E.add_tracks(pcbnew, board, netinfo, R["tracks"], R["vias"])
    E.silk_labels(pcbnew, board, centres)
    finish_silk(pcbnew, board)
    E.set_refs(pcbnew, board)
    copper_labels(pcbnew, board)
    add_registration_drawing(pcbnew, board)
    nk = add_keepouts(pcbnew, board)
    tb = board.GetTitleBlock()
    tb.SetTitle(TITLE)
    tb.SetDate(DATE)
    tb.SetRevision("E-mill")
    board.GetDesignSettings().SetAuxOrigin(E.V(pcbnew, 0, BOARD_H))     # drill / place origin: lower-left
    E.add_gnd_pours(pcbnew, board, netinfo)
    board.Save(str(pcb_path))
    patch_project()
    board = pcbnew.LoadBoard(str(pcb_path))
    E.fill_zones(pcbnew, board)
    board.Save(str(pcb_path))
    patch_project()
    print(f"wire vias: {len(R['vias'])}; stitching vias: 0; F/B keep-outs over single-sided THT pads: {nk}")
    E.drc(pcbnew)
    if not a.no_export:
        exports(pcbnew)
        E.bom(pcbnew)
        b = HERE / f"{PROJECT}_BOM.csv"
        nv = len(json.loads((HERE / "routing_mill.json").read_text())["vias"])
        b.write_text(b.read_text().replace("bare plated pads", "bare pads on bottom copper only (probe from below)")
                     .replace("1 mm copper, 2 mm mask opening", "1 mm bare copper dot, 1.5 mm copper-free ring")
                     + f'not a part,W1-W{nv},{nv},{nv * 10},wire vias,"0.6-0.7 mm bare tinned copper wire (or 0.8 mm '
                       f'via rivet) through each 0.8 mm via hole, soldered top and bottom",,,\n')


if __name__ == "__main__":
    main()
