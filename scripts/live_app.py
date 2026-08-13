"""DEPRECATED shim — the live perception console moved into the unified app.

The two consoles converged (see docs/APP.md): everything this script served
(camera feed + detection overlays, detected-items panel, sensitivity slider,
Robot & plan panel, 3-D room view, --demo mode) now lives in

    python -m roomcleaner.app --live [--camera N] [--demo] [--conf C]

This shim just maps the old flags and execs the unified app so old muscle
memory and notes keep working.
"""
from __future__ import annotations

import argparse
import os
import sys


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--camera", type=int, default=1,
                    help="camera index (USB cam is usually 1; try 0/2 if wrong)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1",
                    help="127.0.0.1 = this machine only; 0.0.0.0 = LAN/Tailscale")
    ap.add_argument("--conf", type=float, default=0.25,
                    help="starting confidence threshold (tune live in the UI)")
    ap.add_argument("--demo", action="store_true",
                    help="no-camera mode: simulated laundry, real plan pipeline")
    args = ap.parse_args()

    cmd = [sys.executable, "-m", "roomcleaner.app", "--live",
           "--camera", str(args.camera),
           "--port", str(args.port),
           "--host", args.host,
           "--conf", str(args.conf)]
    if args.demo:
        cmd.append("--demo")

    print("scripts.live_app has moved into the unified app "
          "(python -m roomcleaner.app --live); forwarding...", flush=True)
    os.execv(sys.executable, cmd)


if __name__ == "__main__":
    main()
