"""
The unified RoomCleaner web console.

A small Flask app that serves a single-page dark-theme dashboard on
http://127.0.0.1:8000 with a live feed (MJPEG), status cards, per-cable
tension bars, an operations log, operator controls (start / pause / resume /
STOP / home / park / grip / release / jog), a detected-items panel with a
live sensitivity slider, the Robot & plan panel (nearest-first pickup order,
per-target cable lengths A-D, max tension, reachability), and a 3-D room
view with a Live view / Animate plan toggle.

Two backends implement the same `RobotSession` interface:

    SimSession  -- pure software: the existing planner (Controller) +
                   SimulatedDetector, animated by a background tick thread and
                   rendered to an MJPEG stream with Pillow. No hardware needed.
    LiveSession -- the camera feed runs through `app.perception`'s capture +
                   inference threads (ported intact from the camera-validated
                   perception console); SerialDriver + WiFiGripper are wired
                   only if reachable, else camera-only live mode with motion
                   disabled. `demo=True` needs no camera at all. Motion NEEDS
                   BENCH VALIDATION.

Run it:

    python -m roomcleaner.app --sim              # simulation (default)
    python -m roomcleaner.app --live --camera 1  # real camera (+ hardware if up)
    python -m roomcleaner.app --live --demo      # no camera: simulated laundry,
                                                 # real detection->plan pipeline

Design note: the console reuses the existing planning/sim stack unchanged --
`Controller.iter_actions()` is the single source of robot behaviour, exactly as
in `scripts/demo_sim.py` and `hardware/executor.py`. The app only *plays back*
that action stream and draws it.
"""

from .server import create_app, RobotSession, SimSession, LiveSession  # noqa: F401
