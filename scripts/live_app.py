"""Launch the RoomCleaner live web app — camera feed + detection overlays in
your browser.

    python -m scripts.live_app --camera 1
    # then open http://localhost:8000

Prereqs (on the machine with the camera):
    pip install -r requirements-vision.txt -r requirements-app.txt

Unlike a native window, this serves over localhost, so it shows up in any
browser on the machine (and over Tailscale if you bind --host 0.0.0.0).
"""
from __future__ import annotations

import argparse

from roomcleaner.webapp import DetectorApp, create_app


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--camera", type=int, default=1,
                    help="camera index (USB cam is usually 1; try 0/2 if wrong)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1",
                    help="127.0.0.1 = this machine only; 0.0.0.0 = reachable on the LAN/Tailscale")
    ap.add_argument("--conf", type=float, default=0.25,
                    help="starting confidence threshold (tune live in the UI)")
    ap.add_argument("--demo", action="store_true",
                    help="no-camera mode: seed simulated laundry so the console "
                         "(plan + 3-D view) works without hardware")
    args = ap.parse_args()

    state = DetectorApp(camera_index=args.camera, conf=args.conf,
                        source="demo" if args.demo else "camera")
    state.start()
    app = create_app(state)

    shown = "localhost" if args.host in ("127.0.0.1", "0.0.0.0") else args.host
    print(f"\n  RoomCleaner live app running — open  http://{shown}:{args.port}  "
          f"in your browser\n  (camera {args.camera}; Ctrl-C to stop)\n", flush=True)
    try:
        app.run(host=args.host, port=args.port, threaded=True, debug=False, use_reloader=False)
    finally:
        state.stop()


if __name__ == "__main__":
    main()
