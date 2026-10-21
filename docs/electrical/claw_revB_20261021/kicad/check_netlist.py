#!/usr/bin/env python3
"""Compare the exported KiCad netlist with the claw Rev B spec's net table, net by net.

    python3 check_netlist.py [netlist.xml]        # stdlib only; exit code 0 = PASS

Expected data = claw_spec.py (the "Nets" table, "Unconnected" line and "Parts" table of
../CLAW_REVB_SPEC.md).  It does not read the schematic or the layout code.  Prints PASS only if

  * every spec net exists in the netlist with exactly the same set of (ref, pin);
  * the netlist has no other connected net;
  * the pins the spec leaves unconnected are flagged no-connect, and no other pin is left open
    (every pin of every part's library symbol is either on a spec net or on the unconnected list);
  * the components equal the spec's parts table (same refs, symbols and values).
"""
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claw_spec as spec  # noqa: E402

PROJECT = "RoomCleaner_Claw_RevB"


def read_netlist(path):
    root = ET.parse(path).getroot()
    comps = {}
    for c in root.find("components"):
        ls = c.find("libsource")
        comps[c.get("ref")] = dict(value=c.findtext("value"), lib_id=f'{ls.get("lib")}:{ls.get("part")}')
    parts = {}
    for lp in root.find("libparts"):
        parts[f'{lp.get("lib")}:{lp.get("part")}'] = {p.get("num") for p in lp.find("pins")}
    nets, unconnected = {}, set()
    for n in root.find("nets"):
        name = n.get("name")
        pins = {(nd.get("ref"), nd.get("pin")) for nd in n.findall("node")}
        if name.startswith("unconnected-"):
            unconnected |= pins
        else:
            nets[name.lstrip("/")] = pins       # local labels appear as "/NAME"
    return comps, parts, nets, unconnected


def fmt(pins):
    return " ".join(f"{r}.{p}" for r, p in sorted(pins, key=lambda t: (t[0], int(t[1]))))


def main(argv):
    lines = []

    def out(s=""):
        print(s)
        lines.append(s)

    path = Path(argv[1]) if len(argv) > 1 else HERE / f"{PROJECT}_netlist.xml"
    expected, want_nc = spec.expected()
    comps, parts, nets, unconnected = read_netlist(path)
    ok = True
    out(f"netlist : {path.name}")
    out(f"expected: {len(expected)} nets, {sum(len(v) for v in expected.values())} connected pins, "
        f"{len(want_nc)} unconnected pins (claw_spec.py = CLAW_REVB_SPEC.md)")
    out(f"found   : {len(nets)} nets, {sum(len(v) for v in nets.values())} connected pins, "
        f"{len(unconnected)} unconnected pins, {len(comps)} components")
    out("")
    out(f"{'net':11s} {'pins':>4s}  result")
    for name in expected:
        want, got = expected[name], nets.get(name)
        if got is None:
            out(f"{name:11s} {len(want):4d}  FAIL  net missing in netlist (expected {fmt(want)})")
            ok = False
        elif got != want:
            out(f"{name:11s} {len(want):4d}  FAIL")
            if want - got:
                out(f"            missing in netlist: {fmt(want - got)}")
            if got - want:
                out(f"            extra in netlist  : {fmt(got - want)}")
            ok = False
        else:
            out(f"{name:11s} {len(want):4d}  ok    {fmt(want)}")
    for name in sorted(set(nets) - set(expected)):
        out(f"{name:11s} {len(nets[name]):4d}  FAIL  net not in the spec: {fmt(nets[name])}")
        ok = False
    if unconnected != want_nc:
        out(f"unconnected pins FAIL: spec {fmt(want_nc)} ; netlist {fmt(unconnected)}")
        ok = False
    else:
        out(f"unconnected pins ok   : {fmt(want_nc)}")
    # no pin may be left open without a no-connect flag
    accounted = set().union(*nets.values()) | unconnected
    open_pins = set()
    for ref, c in comps.items():
        for pin in parts.get(c["lib_id"], ()):
            if (ref, pin) not in accounted:
                open_pins.add((ref, pin))
    if open_pins:
        out(f"open pins FAIL        : {fmt(open_pins)} (neither on a net nor flagged no-connect)")
        ok = False
    else:
        out("open pins ok          : every library pin of every part is on a spec net or flagged no-connect")
    bad = []
    if set(comps) != set(spec.PARTS):
        bad.append(f"refs: missing {sorted(set(spec.PARTS) - set(comps))} extra {sorted(set(comps) - set(spec.PARTS))}")
    for ref, (lib_id, value) in spec.PARTS.items():
        c = comps.get(ref)
        if c and (c["lib_id"] != lib_id or c["value"] != value):
            bad.append(f"{ref}: netlist {c['lib_id']} '{c['value']}' vs spec table {lib_id} '{value}'")
    if bad:
        for b in bad:
            out(f"components FAIL       : {b}")
        ok = False
    else:
        out(f"components ok         : {len(comps)} parts, symbols and values as in the parts table")
    out("")
    out("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
