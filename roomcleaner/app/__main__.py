"""
Entry point: ``python -m roomcleaner.app --sim`` (or ``--live``).

Builds the chosen RobotSession, starts its background work, and serves the
dashboard on http://127.0.0.1:8010 by default. Live mode refuses to start
(with a pointer at --sim) when the camera / serial / vision stack is missing.
"""

from __future__ import annotations

import argparse
import sys

from .server import LiveSession, SimSession, create_app

DEFAULT_PORT = 8010   # 8000 belongs to the live perception console (scripts/live_app.py)
DEFAULT_HOST = "127.0.0.1"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        prog="python -m roomcleaner.app",
        description="RoomCleaner operator dashboard (Flask, single page).",
    )
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--sim", action="store_true",
                      help="simulation backend -- no hardware needed (default)")
    mode.add_argument("--live", action="store_true",
                      help="real hardware: webcam + YOLO-World + serial winches + "
                           "WiFi gripper (bench-validate first; see docs/APP.md)")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT,
                    help=f"HTTP port (default {DEFAULT_PORT})")
    ap.add_argument("--host", default=DEFAULT_HOST,
                    help=f"bind address (default {DEFAULT_HOST}; keep it local)")
    ap.add_argument("--camera", type=int, default=0, metavar="N",
                    help="camera index for --live (default 0)")
    args = ap.parse_args(argv)

    if args.live:
        session = LiveSession(camera_index=args.camera)
        try:
            session.connect()
        except RuntimeError as exc:
            sys.exit(str(exc))
    else:
        session = SimSession()

    session.start_background()
    app = create_app(session)
    print(f"RoomCleaner dashboard ({session.mode} mode): "
          f"http://{args.host}:{args.port}   (Ctrl-C to stop)")
    try:
        app.run(host=args.host, port=args.port, threaded=True)
    finally:
        session.shutdown()


if __name__ == "__main__":
    main()
