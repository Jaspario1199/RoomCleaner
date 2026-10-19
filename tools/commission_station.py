"""Single-station commissioning (handoff steps 2-5), one XIAO-C3 winch on the bench.

UNLOADED SPOOL ONLY (no cable to a suspended load). Power strip in reach.

    python -m tools.commission_station --config config/robot.json --station A status
    python -m tools.commission_station ... direction     # encoder sign + counts/rev check
    python -m tools.commission_station ... jog --mm 50   # bounded move and back, tracking error
    python -m tools.commission_station ... lease         # stop the host pings: station must hold itself

Each run appends a JSON record to data/commissioning/<station>.jsonl with the
firmware boot id, config hash, measurements and pass/fail, so every stage has
saved evidence (handoff: "save the firmware commit, configuration, test setup,
measurements and failures").
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from roomcleaner.cdpr.config import load_config
from roomcleaner.cdpr.coordinator import Coordinator, RealRuntime
from roomcleaner.cdpr.protocol import Fault, State
from roomcleaner.cdpr.trajectory import plan_cable_move


class Bench:
    def __init__(self, cfg, sid, transport, runtime, log=print):
        self.cfg, self.sid, self.log = cfg, sid, log
        self.st = cfg.station(sid)
        self.co = Coordinator(cfg, transport, runtime, ids=(sid,))
        self.spr = self.st.drive.usteps_per_rev

    def link(self):
        return self.co.links[self.sid]

    def tel(self):
        return self.link().tel or {}

    def bring_up(self):
        self.co.wait(300000)
        self.co.configure()
        self.co.wait_synced(5.0)
        self.co.arm(sw_ok=False)
        self.co.wait(200000)

    def status(self):
        self.co.wait(300000)
        t = self.tel()
        return {"boot": self.link().boot, "state": State.NAMES.get(t.get("st")), "fault": Fault.NAMES.get(t.get("flt")),
                "pos": t.get("pos"), "enc": t.get("enc"), "enc_valid": t.get("encv"), "switch_active": t.get("sw")}

    def move(self, usteps, rate=None):
        rate = rate or 0.5 * self.st.drive.max_step_rate_hz
        plan = plan_cable_move(self.co.positions(), [usteps], rate, rate * 4, segment_s=self.cfg.motion.segment_s,
                               label="bench")
        return self.co.execute(plan)

    def direction(self, turns=1.0):
        """Command +turns of payout; the encoder must follow with the configured
        sign and ~counts_per_rev per turn (spool-mounted magnet)."""
        self.bring_up()
        e0, p0 = self.tel()["enc"], self.co.positions()[0]
        r = self.move(int(turns * self.spr))
        self.co.wait(200000)
        e1, p1 = self.tel()["enc"], self.co.positions()[0]
        d_enc, d_pos = e1 - e0, p1 - p0
        expect = d_pos * self.st.encoder.counts_per_rev / self.spr
        ratio = d_enc / expect if expect else float("nan")
        ok = r.ok and abs(ratio - 1.0) < 0.05
        why = "" if ok else ("motion: " + r.reason if not r.ok else
                             f"encoder moved {d_enc} counts for {expect:.0f} expected (ratio {ratio:+.3f}): "
                             + ("flip encoder.sign" if ratio < 0 else "check magnet/mount or microsteps"))
        self.move(-int(turns * self.spr))
        return {"test": "direction", "ok": ok, "why": why, "usteps": d_pos, "enc_counts": d_enc, "ratio": ratio}

    def jog(self, mm):
        """Bounded payout and return using the spool model near the core radius."""
        self.bring_up()
        r_m = self.st.spool.core_radius_m
        usteps = int(round(mm / 1000 / (2 * np.pi * r_m) * self.spr))
        worst = 0.0
        out, back = self.move(usteps), None
        worst = max(worst, abs(self.tel().get("terr", 0.0)))
        if out.ok:
            back = self.move(-usteps)
            worst = max(worst, abs(self.tel().get("terr", 0.0)))
        ok = out.ok and back is not None and back.ok
        return {"test": "jog", "ok": ok, "mm": mm, "usteps": usteps, "final_terr_counts": worst,
                "why": "" if ok else (out.reason if not out.ok else back.reason)}

    def lease(self):
        """Start a long slow move, then stop talking: the station must hold
        itself within lease_s and report a LEASE fault, keeping torque."""
        self.bring_up()
        rate = 0.2 * self.st.drive.max_step_rate_hz
        plan = plan_cable_move(self.co.positions(), [int(rate * 6)], rate, rate * 4,
                               segment_s=self.cfg.motion.segment_s, label="lease")
        mid_reason = {"silenced": False}

        def silence(tau):
            if tau > 1.5 and not mid_reason["silenced"]:
                mid_reason["silenced"] = True
                self.co.tx.send = lambda *a, **k: None       # host goes quiet
            return None
        self.co.execute(plan, monitor=silence, timeout_s=3)
        t = self.tel()
        ok = t.get("flt") == Fault.LEASE and t.get("st") in (State.FAULT, State.IDLE, State.HOLD)
        return {"test": "lease", "ok": ok, "state": State.NAMES.get(t.get("st")), "fault": Fault.NAMES.get(t.get("flt")),
                "torque_kept": t.get("en", None), "why": "" if ok else "station did not self-hold on lease expiry"}


def record(sid, rec, path="data/commissioning"):
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    rec = dict(rec, station=sid, t=time.strftime("%Y-%m-%dT%H:%M:%S"))
    with open(p / f"{sid}.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--station", required=True, choices=list("ABCD"))
    ap.add_argument("test", choices=["status", "direction", "jog", "lease"])
    ap.add_argument("--mm", type=float, default=50.0)
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    missing = cfg.missing("station_bench")
    if missing:
        raise SystemExit(f"measure these first (config): {missing}")
    from roomcleaner.cdpr.transport import UdpHostTransport
    addr = cfg.station(a.station).address
    if not addr:
        raise SystemExit(f"stations[{a.station}].address (ip:port) not set")
    host, port = addr.split(":")
    b = Bench(cfg, a.station, UdpHostTransport({a.station: (host, int(port))}), RealRuntime())
    res = {"status": b.status, "direction": b.direction, "jog": lambda: b.jog(a.mm), "lease": b.lease}[a.test]()
    print(json.dumps(record(a.station, res), indent=2))


if __name__ == "__main__":
    main()
