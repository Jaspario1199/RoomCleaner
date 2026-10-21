#!/usr/bin/env python3
"""Compare the exported KiCad netlist with the as-soldered perfboard nets, net by net.

    python3 check_netlist.py [netlist.xml]            # netlist check (stdlib only)
    /usr/bin/python3 check_netlist.py --pcb           # also check the .kicad_pcb (needs pcbnew)

Expected data = perfboard_layout.py (PINS / BARE / WIRES / NETMAP) via perfboard_data.py.
It does NOT read the schematic or build_kicad.py layout code: the only thing shared with the
generator is the documented hole -> schematic-pin map.  Prints PASS only if

  * every perfboard net exists in the netlist with exactly the same set of (ref, pin);
  * the netlist has no other connected net;
  * every pin the perfboard connects is connected (a missing pin shows up as a diff);
  * the pins the perfboard leaves unconnected ('nc') are unconnected in the netlist;
  * the component list equals the perfboard part list.
Exit code 0 = PASS, 1 = FAIL.
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import perfboard_data as pbd  # noqa: E402

PROJECT = "RoomCleaner_Station_RevD"


def read_netlist(path):
    root = ET.parse(path).getroot()
    comps = {c.get("ref"): (c.findtext("value"), c.findtext("footprint")) for c in root.find("components")}
    nets, unconnected = {}, set()
    for n in root.find("nets"):
        name = n.get("name")
        pins = {(nd.get("ref"), nd.get("pin")) for nd in n.findall("node")}
        if name.startswith("unconnected-"):
            unconnected |= pins
        else:
            nets[name.lstrip("/")] = pins     # local labels appear as "/NAME"
    return comps, nets, unconnected


def fmt_pins(pins):
    return " ".join(f"{r}.{p}" for r, p in sorted(pins, key=lambda t: (t[0], int(t[1]))))


def check_netlist(path, pb, out):
    comps, nets, unconnected = read_netlist(path)
    expected = pb.nets()
    ok = True
    out(f"netlist : {path.name}")
    out(f"expected: {len(expected)} nets, {sum(len(v) for v in expected.values())} connected pins, "
        f"{len(pb.no_connects())} unconnected pins (from perfboard_layout.py)")
    out(f"found   : {len(nets)} nets, {sum(len(v) for v in nets.values())} connected pins, "
        f"{len(unconnected)} unconnected pins, {len(comps)} components")
    out("")
    out(f"{'net':7s} {'pins':>4s}  result")
    for name in sorted(expected):
        want, got = expected[name], nets.get(name)
        if got is None:
            out(f"{name:7s} {len(want):4d}  FAIL  net missing in netlist (expected {fmt_pins(want)})")
            ok = False
        elif got != want:
            out(f"{name:7s} {len(want):4d}  FAIL")
            if want - got:
                out(f"          missing in netlist: {fmt_pins(want - got)}")
            if got - want:
                out(f"          extra in netlist  : {fmt_pins(got - want)}")
            ok = False
        else:
            out(f"{name:7s} {len(want):4d}  ok    {fmt_pins(want)}")
    for name in sorted(set(nets) - set(expected)):
        out(f"{name:7s} {len(nets[name]):4d}  FAIL  net not on the perfboard: {fmt_pins(nets[name])}")
        ok = False
    want_nc = set(pb.no_connects())
    if unconnected != want_nc:
        out(f"unconnected pins FAIL: expected {fmt_pins(want_nc)} ; netlist has {fmt_pins(unconnected)}")
        ok = False
    else:
        out(f"unconnected pins ok   : {fmt_pins(want_nc)}")
    want_refs = {r for r, _ in pb.pin_net}
    if set(comps) != want_refs:
        out(f"components FAIL: missing {sorted(want_refs - set(comps))} extra {sorted(set(comps) - want_refs)}")
        ok = False
    else:
        out(f"components ok         : {' '.join(sorted(comps, key=lambda r: (r.rstrip('0123456789'), int(r.lstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ')))))}")
    return ok


def check_pcb(pcb_path, pb, out):
    try:
        import pcbnew
    except ImportError:
        out("PCB     : skipped (pcbnew not importable; run with /usr/bin/python3 --pcb)")
        return True
    if not pcb_path.exists():
        out(f"PCB     : {pcb_path.name} not found")
        return False
    board = pcbnew.LoadBoard(str(pcb_path))
    ok = True
    nets, nc_pads, worst = {}, set(), 0.0
    # board origin: hole A01 = first used hole position is recovered from J2 pad 1 (X05)
    ref_pad = None
    for fp in board.GetFootprints():
        if fp.GetReference() == "J2":
            for pad in fp.Pads():
                if pad.GetNumber() == "1":
                    ref_pad = pad.GetPosition()
    ax = pcbnew.ToMM(ref_pad.x) - pbd.hole_xy("X05")[0]
    ay = pcbnew.ToMM(ref_pad.y) - pbd.hole_xy("X05")[1]
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        holes = pb.pin_hole(ref)
        for pad in fp.Pads():
            pin = pad.GetNumber()
            hx, hy = pbd.hole_xy(holes[pin])
            p = pad.GetPosition()
            worst = max(worst, ((pcbnew.ToMM(p.x) - ax - hx) ** 2 + (pcbnew.ToMM(p.y) - ay - hy) ** 2) ** 0.5)
            name = pad.GetNetname()
            if name.startswith("unconnected-"):
                nc_pads.add((ref, pin))
            elif name:
                nets.setdefault(name.lstrip("/"), set()).add((ref, pin))
    expected = pb.nets()
    if nets != expected:
        out("PCB     : FAIL pad nets differ from the perfboard nets")
        for n in sorted(set(nets) | set(expected)):
            if nets.get(n) != expected.get(n):
                out(f"          {n}: pcb {fmt_pins(nets.get(n, set()))} | perfboard {fmt_pins(expected.get(n, set()))}")
        ok = False
    if nc_pads != set(pb.no_connects()):
        out(f"PCB     : FAIL unconnected pads {fmt_pins(nc_pads)} != {fmt_pins(set(pb.no_connects()))}")
        ok = False
    if worst > 0.06:
        out(f"PCB     : FAIL a pad is {worst:.3f} mm off its perfboard hole")
        ok = False
    n_pads = sum(len(v) for v in nets.values()) + len(nc_pads)
    out(f"PCB     : {'ok' if ok else 'FAIL'}   {len(board.GetFootprints())} footprints, {n_pads} pads, "
        f"{len(nets)} nets equal the perfboard nets; worst pad-to-hole error {worst:.3f} mm "
        f"(hole A01 at {ax:.2f}, {ay:.2f} mm)")
    return ok


def main(argv):
    lines = []

    def out(s=""):
        print(s)
        lines.append(s)

    args = [a for a in argv[1:] if not a.startswith("--")]
    net_path = Path(args[0]) if args else HERE / f"{PROJECT}_netlist.xml"
    pb = pbd.Perfboard()
    out(f"perfboard_layout.py: {pb.check_output}")
    ok = check_netlist(net_path, pb, out)
    if "--pcb" in argv:
        ok = check_pcb(HERE / f"{PROJECT}.kicad_pcb", pb, out) and ok
    out("")
    out("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
