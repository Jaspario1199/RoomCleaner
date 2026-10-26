"""Claw node check from the laptop (firmware/claw_s3 flashed, claw on the bench). No stations, no config needed.

    python -m tools.check_claw 192.168.1.70 status          # battery, camera, grip, clock round trip
    python -m tools.check_claw 192.168.1.70 frames --n 5    # saves 5 JPEGs to data/claw_check/ (what the host sees)
    python -m tools.check_claw 192.168.1.70 grip close      # asks first; then 'grip open'
    python -m tools.check_claw 192.168.1.70 all             # status + frames + open/close/open (asks first)

The claw must be on the BENCH for grip (fingers clear of hands). Each run appends a JSON record to
data/commissioning/claw.jsonl, like tools/commission_station.py does for the stations. When this passes, put the same
address in the config as claw.address ("192.168.1.70", no port) and the host service talks to the same endpoints.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from roomcleaner.cdpr.claw_link import HttpClawClient

CUTOFF_V = 6.8       # claw_s3.ino BATT_CUTOFF_V


def check_status(c: HttpClawClient, log=print) -> dict:
    t0 = time.monotonic()
    st = c.status()
    rtt_ms = (time.monotonic() - t0) * 1e3
    if not st.get("online"):
        log(f"OFFLINE: {st.get('error', 'no answer')}. Same Wi-Fi as the claw? Address from the claw's Serial Monitor?")
        return {"ok": False, "status": st}
    v = st.get("battery_v", 0.0)
    log(f"online, round trip {rtt_ms:.0f} ms")
    log(f"battery {v:.2f} V {'LOW: charge before lifting' if st.get('battery_low') else 'ok'}"
        f"{'  (reads ~0: battery off or the R1/R2 divider not connected)' if v < 1.0 else ''}")
    log(f"camera {'ok' if st.get('camera_ok') else 'NOT running'} ({st.get('camera_mode')}), frames served {st.get('frame_id')}")
    log(f"grip {'CLOSED' if st.get('grip_closed') else 'open'} (servo {st.get('servo_us')} us)")
    ok = bool(st.get("camera_ok")) and v >= CUTOFF_V
    return {"ok": ok, "status": st, "rtt_ms": round(rtt_ms, 1)}


def check_frames(c: HttpClawClient, n: int, out_dir="data/claw_check", log=print) -> dict:
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    saved, ages = [], []
    for _ in range(n):
        img, cap_us, fid, mode = c.frame()
        age = (c.now_us() - cap_us) / 1e6
        p = d / f"claw_{time.strftime('%Y%m%d_%H%M%S')}_{fid}.jpg"
        p.write_bytes(c.last_cached.jpeg)
        saved.append(str(p))
        ages.append(age)
        log(f"frame {fid}: {img.shape[1]}x{img.shape[0]} {mode}, age {age * 1e3:.0f} ms -> {p}")
        time.sleep(0.2)
    return {"ok": len(saved) == n, "files": saved, "max_age_s": round(max(ages), 3) if ages else None}


def check_grip(c: HttpClawClient, close: bool, log=print) -> dict:
    ok = c.grip(close)
    time.sleep(0.8)
    st = c.status()
    held = st.get("grip_closed") is close
    log(f"grip {'close' if close else 'open'}: {'ok' if ok and held else 'FAILED'} (servo {st.get('servo_us')} us)")
    return {"ok": ok and held, "close": close, "servo_us": st.get("servo_us")}


def confirm(question) -> bool:
    return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")


def record(rec, path="data/commissioning"):
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    with open(p / "claw.jsonl", "a") as f:
        f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), **rec}) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("address", help="the claw's IP, as printed on its Serial Monitor (e.g. 192.168.1.70)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    f = sub.add_parser("frames")
    f.add_argument("--n", type=int, default=5)
    g = sub.add_parser("grip")
    g.add_argument("action", choices=["open", "close"])
    sub.add_parser("all")
    a = ap.parse_args(argv)
    c = HttpClawClient(f"http://{a.address}", timeout_s=3.0)
    rec = {"cmd": a.cmd, "address": a.address}
    if a.cmd in ("status", "all"):
        rec["status"] = check_status(c)
        if not rec["status"]["status"].get("online"):
            record(rec)
            return 1
    if a.cmd in ("frames", "all"):
        rec["frames"] = check_frames(c, getattr(a, "n", 3) if a.cmd == "frames" else 3)
    if a.cmd == "grip":
        if a.action == "close" and not confirm("Claw on the bench, fingers clear of hands?"):
            return 1
        rec["grip"] = check_grip(c, a.action == "close")
    if a.cmd == "all":
        if confirm("Grip test: open, close, open. Claw on the bench, fingers clear of hands?"):
            rec["grip"] = [check_grip(c, False), check_grip(c, True), check_grip(c, False)]
    parts = [v for k, v in rec.items() if k in ("status", "frames", "grip")]
    flat = [x for p in parts for x in (p if isinstance(p, list) else [p])]
    rec["pass"] = all(x["ok"] for x in flat)
    record(rec)
    print("PASS" if rec["pass"] else "CHECK the lines above")
    return 0 if rec["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
