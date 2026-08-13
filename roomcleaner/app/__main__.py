"""
Entry point: ``python -m roomcleaner.app --sim`` (or ``--live``).

Builds the chosen RobotSession, starts its background work, and serves the
unified console on http://127.0.0.1:8000 by default. Live mode needs a camera
(or ``--demo`` for the no-camera walkthrough); winches/gripper are wired only
if reachable, otherwise live mode runs camera-only with motion disabled.
"""

from __future__ import annotations

import argparse
import sys

from .server import DEFAULT_CONF, LiveSession, SimSession, create_app

DEFAULT_PORT = 8000   # the unified app owns the old perception-console port
DEFAULT_HOST = "127.0.0.1"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        prog="python -m roomcleaner.app",
        description="RoomCleaner console (Flask, single page): mission control "
                    "+ live perception in one app.",
    )
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--sim", action="store_true",
                      help="simulation backend -- no hardware needed (default)")
    mode.add_argument("--live", action="store_true",
                      help="real camera feed (capture + YOLO-World inference "
                           "threads); winches + gripper wired only if reachable, "
                           "else camera-only (motion bench-validation pending; "
                           "see docs/APP.md)")
    ap.add_argument("--demo", action="store_true",
                    help="live mode without a camera: simulated laundry through "
                         "the real detection->plan pipeline (implies --live)")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT,
                    help=f"HTTP port (default {DEFAULT_PORT})")
    ap.add_argument("--host", default=DEFAULT_HOST,
                    help=f"bind address (default {DEFAULT_HOST}; 0.0.0.0 = LAN)")
    ap.add_argument("--camera", type=int, default=0, metavar="N",
                    help="camera index for --live (default 0; innomaker was 1)")
    ap.add_argument("--conf", type=float, default=DEFAULT_CONF,
                    help=f"starting detection-confidence threshold "
                         f"(default {DEFAULT_CONF}; tune live in the UI)")
    args = ap.parse_args(argv)

    if args.demo and args.sim:
        ap.error("--demo is a live-mode option; drop --sim (use --live --demo)")

    if args.live or args.demo:
        session = LiveSession(camera_index=args.camera, demo=args.demo,
                              conf=args.conf)
        try:
            session.connect()
        except RuntimeError as exc:
            sys.exit(str(exc))
    else:
        session = SimSession(conf=args.conf)

    session.start_background()
    app = create_app(session)
    print(f"RoomCleaner console ({session.mode} mode): "
          f"http://{args.host}:{args.port}   (Ctrl-C to stop)")
    try:
        app.run(host=args.host, port=args.port, threaded=True)
    finally:
        session.shutdown()


if __name__ == "__main__":
    main()
