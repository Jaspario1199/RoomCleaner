"""
Operator web dashboard for the RoomCleaner robot.

A small Flask app that serves a single-page dark-theme dashboard on
http://127.0.0.1:8010 with a live top-down "camera" feed, status cards,
per-cable tension bars, an operations log, and operator controls
(start / pause / resume / STOP / home / park / grip / release / jog).

Two backends implement the same `RobotSession` interface:

    SimSession  -- pure software: the existing planner (Controller) +
                   SimulatedDetector, animated by a background tick thread and
                   rendered to an MJPEG stream with Pillow. No hardware needed.
    LiveSession -- wires the real Webcam + YoloWorldDetector + SerialDriver +
                   WiFiGripper. Heavy deps import lazily; without them it fails
                   with a clear "use --sim" message. NEEDS BENCH VALIDATION.

Run it:

    python -m roomcleaner.app --sim            # simulation (recommended)
    python -m roomcleaner.app --live           # real hardware (bench-validate!)

Design note: the dashboard reuses the existing planning/sim stack unchanged --
`Controller.iter_actions()` is the single source of robot behaviour, exactly as
in `scripts/demo_sim.py` and `hardware/executor.py`. The app only *plays back*
that action stream and draws it.
"""

from .server import create_app, RobotSession, SimSession, LiveSession  # noqa: F401
