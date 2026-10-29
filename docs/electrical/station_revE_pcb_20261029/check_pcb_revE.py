#!/usr/bin/env python3
"""Independent net check: does the ROUTED Rev E copper connect exactly the Rev D nets?

    /usr/bin/python3 check_pcb_revE.py [board.kicad_pcb]

Expected nets: Rev D, from ../station_revD_20261021/kicad/perfboard_data.py (which reads the
as-soldered perfboard_layout.py), with the one documented re-numbering of the motor connector J2
(Rev D pin -> Rev E pin: 3->1 (1A), 4->2 (1B), 2->3 (2A), 1->4 (2B)) and the test pads TP1-TP4
(no new nets).  D1 is now an SS14 in SMA: same pins (1 = cathode, 2 = anode), same nets.

The copper is analysed here, not taken from KiCad's net labels: tracks, vias, pads and the filled
GND zone polygons are joined by geometry (union-find), then every resulting copper island is
compared with the expected nets.  Pad net labels are checked separately.  PASS requires:
  * every expected net is one copper island holding exactly its pads (no pad missing, none extra);
  * no copper island holds pads of two nets (no short);
  * pads Rev D leaves unconnected touch no other pad;
  * pad net labels equal the expected nets; components = Rev D parts + TP/H/FID only.
Exit 0 = PASS, 1 = FAIL.  Output is also written to netlist_check.txt.
"""
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "station_revD_20261021" / "kicad"))
import perfboard_data as pbd  # noqa: E402

J2_REMAP = {"3": "1", "4": "2", "2": "3", "1": "4"}
TESTPADS = {"TP1": "+12V", "TP2": "5VB", "TP3": "+3V3", "TP4": "GND"}
NONPARTS = ("TP", "H", "FID")


def expected():
    pb = pbd.Perfboard()
    nets = {}
    for n, pins in pb.nets().items():
        nets[n] = {(r, J2_REMAP[p]) if r == "J2" else (r, p) for r, p in pins}
    for tp, n in TESTPADS.items():
        nets[n].add((tp, "1"))
    nc = {(r, J2_REMAP[p]) if r == "J2" else (r, p) for r, p in pb.no_connects()}
    refs = {r for r, _ in pb.pin_net}
    return nets, nc, refs, pb.check_output


class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def seg_dist(ax, ay, bx, by, px, py):
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    t = 0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


def point_in_ring(x, y, ring):
    inside = False
    n = len(ring)
    for k in range(n):
        x1, y1 = ring[k]
        x2, y2 = ring[(k + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xi > x:
                inside = not inside
    return inside


class Fragment:
    def __init__(self, outline, holes):
        self.outline, self.holes = outline, holes
        xs = [p[0] for p in outline]
        ys = [p[1] for p in outline]
        self.bb = (min(xs), min(ys), max(xs), max(ys))

    def contains(self, x, y):
        x0, y0, x1, y1 = self.bb
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            return False
        return point_in_ring(x, y, self.outline) and not any(point_in_ring(x, y, h) for h in self.holes)


def main(argv):
    import pcbnew
    path = Path(argv[1]) if len(argv) > 1 else HERE / "RoomCleaner_Station_RevE.kicad_pcb"
    lines = []

    def out(s=""):
        print(s)
        lines.append(s)

    nets, nc, refs, chk = expected()
    out(f"perfboard_layout.py: {chk}")
    out(f"board   : {path.name}")
    board = pcbnew.LoadBoard(str(path))
    mm = pcbnew.ToMM
    LAY = {pcbnew.F_Cu: "F", pcbnew.B_Cu: "B"}
    uf = UF()
    ok = True

    # ---- pads
    pads = []      # (key, pad, x, y, layers, r_out)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue
            key = ("pad", fp.GetReference(), pad.GetNumber())
            p = pad.GetPosition()
            layers = [l for l in LAY if pad.IsOnLayer(l)]
            sz = pad.GetSize()
            pads.append((key, pad, mm(p.x), mm(p.y), layers, max(mm(sz.x), mm(sz.y)) / 2))
            uf.find(key)
    # ---- tracks / vias
    tracks, vias = [], []
    for k, t in enumerate(board.GetTracks()):
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            vias.append((("via", k), mm(p.x), mm(p.y), mm(t.GetWidth()) / 2))
        else:
            a, b = t.GetStart(), t.GetEnd()
            tracks.append((("trk", k), t.GetLayer(), mm(a.x), mm(a.y), mm(b.x), mm(b.y), mm(t.GetWidth()) / 2))
    eps = 0.001
    for i, (ka, la, ax1, ay1, ax2, ay2, ra) in enumerate(tracks):
        uf.find(ka)
        for kb, lb, bx1, by1, bx2, by2, rb in tracks[i + 1:]:
            if la != lb:
                continue
            if (seg_dist(bx1, by1, bx2, by2, ax1, ay1) <= rb + eps or seg_dist(bx1, by1, bx2, by2, ax2, ay2) <= rb + eps
                    or seg_dist(ax1, ay1, ax2, ay2, bx1, by1) <= ra + eps
                    or seg_dist(ax1, ay1, ax2, ay2, bx2, by2) <= ra + eps):
                uf.union(ka, kb)
        for kv, vx, vy, vr in vias:
            if seg_dist(ax1, ay1, ax2, ay2, vx, vy) <= ra + eps:
                uf.union(ka, kv)
        for kp, pad, px, py, players, _ in pads:
            if la not in players:
                continue
            if (pad.HitTest(pcbnew.VECTOR2I(pcbnew.FromMM(ax1), pcbnew.FromMM(ay1)))
                    or pad.HitTest(pcbnew.VECTOR2I(pcbnew.FromMM(ax2), pcbnew.FromMM(ay2)))
                    or seg_dist(ax1, ay1, ax2, ay2, px, py) <= ra + eps):
                uf.union(ka, kp)
    for kv, vx, vy, vr in vias:
        uf.find(kv)
    # ---- zone fills
    nfrag = 0
    for z in board.Zones():
        for layer in LAY:
            if not z.IsOnLayer(layer):
                continue
            polys = z.GetFilledPolysList(layer)
            for o in range(polys.OutlineCount()):
                ring = [(mm(polys.COutline(o).CPoint(k).x), mm(polys.COutline(o).CPoint(k).y))
                        for k in range(polys.COutline(o).PointCount())]
                holes = []
                for h in range(polys.HoleCount(o)):
                    hc = polys.CHole(o, h)
                    holes.append([(mm(hc.CPoint(k).x), mm(hc.CPoint(k).y)) for k in range(hc.PointCount())])
                fr = Fragment(ring, holes)
                fk = ("zone", z.GetZoneName(), LAY[layer], o)
                uf.find(fk)
                nfrag += 1
                for kv, vx, vy, vr in vias:
                    if any(fr.contains(vx + vr * 0.7 * math.cos(a), vy + vr * 0.7 * math.sin(a))
                           for a in (0, 1.57, 3.14, 4.71)):
                        uf.union(fk, kv)
                for kp, pad, px, py, players, r in pads:
                    if layer not in players:
                        continue
                    for k in range(72):
                        a = k * math.pi / 36
                        x, y = px + (r + 0.15) * math.cos(a), py + (r + 0.15) * math.sin(a)
                        # the sample point must be in the fill AND the fill must reach into the pad
                        x2, y2 = px + (r - 0.05) * math.cos(a), py + (r - 0.05) * math.sin(a)
                        if fr.contains(x, y) and pad.HitTest(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2))):
                            uf.union(fk, kp)
                            break
                for kt, lt, x1, y1, x2, y2, rt in tracks:
                    if lt != layer:
                        continue
                    L = math.hypot(x2 - x1, y2 - y1)
                    if L == 0:
                        continue
                    nxv, nyv = -(y2 - y1) / L, (x2 - x1) / L
                    steps = max(2, int(L / 0.5))
                    hit = False
                    for s in range(steps + 1):
                        t = s / steps
                        cx, cy = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
                        for sgn in (1, -1):
                            if fr.contains(cx + sgn * nxv * (rt - 0.05), cy + sgn * nyv * (rt - 0.05)) and \
                                    fr.contains(cx + sgn * nxv * (rt + 0.1), cy + sgn * nyv * (rt + 0.1)):
                                hit = True
                                break
                        if hit:
                            break
                    if hit:
                        uf.union(fk, kt)
    # ---- islands
    islands = {}
    for kp, pad, *_ in pads:
        islands.setdefault(uf.find(kp), set()).add((kp[1], kp[2]))
    pin_island = {pin: root for root, pins in islands.items() for pin in pins}
    out(f"copper  : {len(pads)} pads, {len(tracks)} track segments, {len(vias)} vias, {nfrag} zone fragments")
    out(f"expected: {len(nets)} nets, {sum(len(v) for v in nets.values())} pins "
        f"(Rev D 55 + 4 test pads), {len(nc)} pins unconnected")
    out("")
    out(f"{'net':7s} {'pins':>4s}  copper result")
    for name in sorted(nets):
        want = nets[name]
        roots = {pin_island.get(p) for p in want}
        got = set().union(*(islands[r] for r in roots if r is not None))
        fmt = " ".join(f"{r}.{p}" for r, p in sorted(want, key=lambda t: (t[0], int(t[1]))))
        if len(roots) != 1:
            out(f"{name:7s} {len(want):4d}  FAIL  split into {len(roots)} copper islands")
            ok = False
        elif got != want:
            out(f"{name:7s} {len(want):4d}  FAIL  island also holds {sorted(got - want)}")
            ok = False
        else:
            out(f"{name:7s} {len(want):4d}  ok    {fmt}")
    for p in sorted(nc):
        isl = islands.get(pin_island.get(p), set())
        if isl != {p}:
            out(f"nc pin {p} FAIL: connected to {sorted(isl - {p})}")
            ok = False
    out(f"unconnected pins      : {'ok' if ok else 'see above'}  "
        + " ".join(f"{r}.{p}" for r, p in sorted(nc)))
    # ---- KiCad net labels on pads
    lab = {}
    for kp, pad, *_ in pads:
        n = pad.GetNetname()
        if n and not n.startswith("unconnected-"):
            lab.setdefault(n, set()).add((kp[1], kp[2]))
    if lab != nets:
        out("pad net labels FAIL: " + ", ".join(sorted(n for n in set(lab) | set(nets) if lab.get(n) != nets.get(n))))
        ok = False
    else:
        out("pad net labels        : ok (equal to the expected nets)")
    have = {fp.GetReference() for fp in board.GetFootprints()}
    parts = {r for r in have if not r.startswith(NONPARTS)}
    if parts != refs:
        out(f"components FAIL: missing {sorted(refs - parts)} extra {sorted(parts - refs)}")
        ok = False
    else:
        out(f"components            : ok  {' '.join(sorted(parts))} (+ {' '.join(sorted(have - parts))})")
    out("J2 re-numbering       : Rev D J2.3 1A -> E J2.1, J2.4 1B -> J2.2, J2.2 2A -> J2.3, J2.1 2B -> J2.4")
    out("")
    out("PASS" if ok else "FAIL")
    (HERE / "netlist_check.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
