"""
Flask server + RobotSession backends for the unified RoomCleaner console.

Architecture
------------
The web layer is deliberately thin: every route talks to ONE object, a
`RobotSession`, which owns the robot state and a lock. Two implementations:

  * `SimSession` -- everything in software. A background thread ticks at
    ~TICK_HZ, advancing the claw along the SAME `Controller.iter_actions()`
    stream the hardware executor consumes, and rendering a top-down "camera"
    frame with Pillow (room, fan keep-out, hamper, laundry with detection
    boxes, cables, claw). The mission loop is: scatter items -> mission ->
    park -> idle, restartable with the `start` command.

  * `LiveSession` -- the same interface wired to real parts. The camera feed
    runs through `app.perception.PerceptionPipeline` -- the capture thread +
    inference thread + self-healing reopen ported intact from the retired
    perception console (camera-validated code). Winches (SerialDriver) and
    gripper (WiFiGripper) are wired only if reachable; otherwise the session
    runs in CAMERA-ONLY live mode with motion commands refused (409) and a
    banner in the UI. `--demo` runs the same session with simulated laundry
    pushed through the real detection->plan pipeline, no camera needed.
    Motion on real hardware STILL NEEDS BENCH VALIDATION -- see docs/APP.md.

Shared by both backends (the panels absorbed from the perception console):
detected-items list (`status.detections`), live confidence slider
(`POST /api/config {"conf": ...}`), the pickup plan with per-target cable
lengths (`/api/plan`), and the 3-D room view (`/api/room.png`, `/api/room.gif`).

Safety
------
Every command is validated server-side. Jogs are clamped to the wall/floor/
ceiling margins and must pass the fan keep-out check (`geometry.py`) plus a
static-tension feasibility check before the position changes. The `stop`
command aborts the mission stream immediately; in live mode no further motion
commands are sent after a stop. THE SOFTWARE STOP IS NOT A SAFETY DEVICE --
the physical kill switch remains the power strip feeding the winch PSU.
"""

from __future__ import annotations

import io
import threading
import time
from collections import deque
from datetime import datetime

import numpy as np
from flask import Flask, Response, jsonify, request, send_from_directory
from PIL import Image, ImageDraw, ImageFont

from ..config import (
    FAN_SAFETY_MARGIN,
    FanZone,
    RobotConfig,
    SAFE_MIN_Z,
    WALL_MARGIN,
    DEFAULT_CONFIG,
    HAS_FAN,
    FAN_CENTER_X,
    FAN_CENTER_Y,
    FAN_BLADE_RADIUS,
    FAN_DROP,
    ROOM_WIDTH,
    ROOM_DEPTH,
    ROOM_HEIGHT,
)
from ..control.state_machine import Controller
from ..control.trajectory import safe_transit, straight_line
from ..geometry import cables_clear_of_fan
from ..kinematics import CableRobot

# ---------------------------------------------------------------------------
# Tunables (named so the numbers in the logic below have one home).
# ---------------------------------------------------------------------------
TICK_HZ = 8.0                 # sim tick / render rate (frames per second)
WAYPOINTS_PER_TICK = 6        # 50 Hz waypoints consumed per tick ~= real-time
STREAM_FPS = 8.0              # MJPEG frame pacing for clients
JOG_STEP_M = 0.10             # one jog button press moves this far
LOG_CAPACITY = 400            # lines kept server-side
LOG_TAIL = 60                 # lines returned by /api/status
JPEG_QUALITY = 80
CEILING_CLEARANCE_M = 0.10    # matches kinematics.is_reachable's z ceiling

# Tension display thresholds: inside [min, max] is legal; we pre-warn near
# the edges so the operator sees amber before red.
TENSION_WARN_LOW_N = 2.0
TENSION_WARN_HIGH_FRACTION = 0.8    # warn above 80 % of the motor limit

# Detection confidence slider range (same clamp the perception console used).
CONF_MIN = 0.05
CONF_MAX = 0.90
DEFAULT_CONF = 0.25

# Plan panel: cap the planning loop like the perception console did.
PLAN_MAX_STEPS = 50
ROOM_GIF_MAX_FRAMES = 45
ROOM_GIF_FPS = 12

# Simulated claw telemetry (2S LiPo on the effector ESP32).
SIM_BATTERY_FULL_V = 8.40
SIM_BATTERY_EMPTY_V = 7.00
SIM_BATTERY_DRAIN_V_PER_TICK = 2e-5

# Camera-frame rendering.
FRAME_MAX_W_PX = 720          # room drawing area is fitted inside this box
FRAME_MAX_H_PX = 540
FRAME_PAD_PX = 34
MIN_ITEM_BOX_M = 0.14         # smallest drawn detection box (real socks are small)
HAMPER_DRAW_M = 0.34          # drawn hamper footprint (display only)

VALID_COMMANDS = (
    "start", "pause", "resume", "stop", "home", "park", "grip", "release", "jog",
)

# The room/fan/hamper values an operator may edit from the settings drawer.
# Everything else (masses, tension limits, margins) stays under source control.
DEFAULT_SETTINGS: dict[str, float | bool] = {
    "room_width": ROOM_WIDTH,
    "room_depth": ROOM_DEPTH,
    "room_height": ROOM_HEIGHT,
    "fan_enabled": HAS_FAN,
    "fan_x": FAN_CENTER_X,
    "fan_y": FAN_CENTER_Y,
    "fan_radius": FAN_BLADE_RADIUS,
    "fan_drop": FAN_DROP,
    "hamper_x": ROOM_WIDTH - 0.5,
    "hamper_y": 0.5,
}

# Absolute sanity bounds per setting (relational checks live in
# validate_settings). Booleans are validated separately.
SETTING_BOUNDS: dict[str, tuple[float, float]] = {
    "room_width": (1.5, 12.0),
    "room_depth": (1.5, 12.0),
    "room_height": (1.8, 6.0),
    "fan_x": (0.0, 12.0),
    "fan_y": (0.0, 12.0),
    "fan_radius": (0.0, 3.0),
    "fan_drop": (0.0, 3.0),
    "hamper_x": (0.0, 12.0),
    "hamper_y": (0.0, 12.0),
}


class CommandError(Exception):
    """A rejected operator command; carries the HTTP status to return."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------------------
# Settings -> RobotConfig
# ---------------------------------------------------------------------------
def validate_settings(s: dict) -> str | None:
    """Return an error string if the settings are unusable, else None."""
    for key, (lo, hi) in SETTING_BOUNDS.items():
        v = s.get(key)
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return f"{key} must be a number"
        if not (lo <= float(v) <= hi):
            return f"{key} must be between {lo} and {hi} (got {v})"
    if not isinstance(s.get("fan_enabled"), bool):
        return "fan_enabled must be true or false"
    w, d, h = float(s["room_width"]), float(s["room_depth"]), float(s["room_height"])
    if s["fan_enabled"]:
        if not (0.0 <= float(s["fan_x"]) <= w and 0.0 <= float(s["fan_y"]) <= d):
            return "fan center must lie inside the room"
        if float(s["fan_drop"]) > h - 1.0:
            return "fan_drop leaves under 1 m of clear height below the fan"
    margin = WALL_MARGIN
    if not (margin <= float(s["hamper_x"]) <= w - margin):
        return f"hamper_x must be {margin}..{w - margin} m (inside the wall margin)"
    if not (margin <= float(s["hamper_y"]) <= d - margin):
        return f"hamper_y must be {margin}..{d - margin} m (inside the wall margin)"
    return None


def build_robot_config(s: dict) -> RobotConfig:
    """Build a RobotConfig for the given room/fan settings.

    Mirrors config.py: anchors in the four ceiling corners (A..D counter-
    clockwise) and a FanZone whose radius/z_low already include the safety
    margin. Masses/tension limits come from the checked-in defaults.
    """
    w, d, h = float(s["room_width"]), float(s["room_depth"]), float(s["room_height"])
    anchors = np.array(
        [[0.0, 0.0, h], [w, 0.0, h], [w, d, h], [0.0, d, h]], dtype=float
    )
    fan = FanZone(
        cx=float(s["fan_x"]),
        cy=float(s["fan_y"]),
        radius=float(s["fan_radius"]) + FAN_SAFETY_MARGIN,
        z_low=max(0.0, h - float(s["fan_drop"]) - FAN_SAFETY_MARGIN),
        z_high=h + 0.01,
        enabled=bool(s["fan_enabled"]),
    )
    return RobotConfig(
        anchors=anchors, room_width=w, room_depth=d, room_height=h, fan=fan
    )


# ---------------------------------------------------------------------------
# Session base
# ---------------------------------------------------------------------------
class RobotSession:
    """Shared state + command validation for sim and live backends.

    Subclasses implement how motion actually happens; everything an operator
    command must AGREE on (clamping, fan keep-out, tension feasibility,
    status shape) lives here so the two modes cannot drift apart.
    """

    mode = "abstract"

    def __init__(self, settings: dict | None = None, conf: float = DEFAULT_CONF):
        self._lock = threading.RLock()
        merged = dict(DEFAULT_SETTINGS)
        if settings:
            merged.update(settings)
        err = validate_settings(merged)
        if err:
            raise ValueError(f"bad session settings: {err}")
        self._settings = merged
        self._conf = float(np.clip(conf, CONF_MIN, CONF_MAX))
        self._render_lock = threading.Lock()  # pyplot global state is not thread-safe
        self._gif_cache: dict = {}            # cached plan animation, keyed by detections
        self._log: deque[str] = deque(maxlen=LOG_CAPACITY)
        self._gripping = False
        self._paused = False
        self._stopped = False        # sticky STOP banner until the next command
        self._homed = False
        self._picked_total = 0
        self.robot: CableRobot | None = None
        self.hamper_xy: tuple[float, float] = (0.0, 0.0)
        self.rest: np.ndarray | None = None
        self._position: np.ndarray | None = None
        self._rebuild_robot()

    # -- construction -------------------------------------------------------
    def _rebuild_robot(self) -> None:
        cfg = build_robot_config(self._settings)
        self.robot = CableRobot(cfg)
        self.hamper_xy = (
            float(self._settings["hamper_x"]),
            float(self._settings["hamper_y"]),
        )
        self.rest = self.robot.find_rest_position(prefer_xy=self.hamper_xy)
        self._position = self.rest.copy()

    def _cruise_z(self) -> float:
        """Safe transit height -- same policy as Controller.__init__."""
        cfg = self.robot.cfg
        cruise = 0.55 * cfg.room_height
        if cfg.fan is not None and cfg.fan.enabled:
            cruise = min(cruise, cfg.fan.z_low - 0.15)
        return max(cruise, SAFE_MIN_Z + 0.4)

    # -- logging ------------------------------------------------------------
    def _append_log(self, msg: str) -> None:
        self._log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    # -- lifecycle (overridden as needed) -----------------------------------
    def start_background(self) -> None:
        """Start any background threads. Safe to skip in tests."""

    def shutdown(self) -> None:
        """Stop background threads and release resources."""

    # -- status -------------------------------------------------------------
    def _mission_active(self) -> bool:
        raise NotImplementedError

    def _phase(self) -> str:
        raise NotImplementedError

    def _claw_status(self) -> dict:
        raise NotImplementedError

    def _motion_enabled(self) -> bool:
        """False when motion commands cannot work (camera-only live mode)."""
        return True

    def _hardware_status(self) -> dict:
        return {"connected": True, "reason": "simulated hardware"}

    def _perception_stats(self) -> dict | None:
        """Capture/inference stats for live mode; None in sim."""
        return None

    def detections(self) -> list[dict]:
        """Current detections above the confidence threshold, as JSON-ready
        dicts: {label, confidence, floor: [x, y], bbox, area}."""
        raise NotImplementedError

    def status(self) -> dict:
        with self._lock:
            cfg = self.robot.cfg
            tensions, feasible = self.robot.solve_tensions(self._position)
            warn_high = TENSION_WARN_HIGH_FRACTION * cfg.max_tension
            per_cable = []
            for t in tensions:
                if not feasible or t < cfg.min_tension or t > cfg.max_tension:
                    per_cable.append("crit")
                elif t < TENSION_WARN_LOW_N or t > warn_high:
                    per_cable.append("warn")
                else:
                    per_cable.append("ok")
            x, y, z = (float(v) for v in self._position)
            return {
                "mode": self.mode,
                "phase": self._phase(),
                "mission_active": self._mission_active(),
                "paused": self._paused,
                "homed": self._homed,
                "pose": {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3)},
                "tensions": {
                    "newtons": [round(float(t), 2) for t in tensions],
                    "status": per_cable,
                    "feasible": bool(feasible),
                    "band": [cfg.min_tension, cfg.max_tension],
                },
                "picked": self._picked_count(),
                "gripping": self._gripping,
                "claw": self._claw_status(),
                "detections": self.detections(),
                "motion_enabled": self._motion_enabled(),
                "hardware": self._hardware_status(),
                "perception": self._perception_stats(),
                "log": list(self._log)[-LOG_TAIL:],
                "config": self.get_settings(),
            }

    def _picked_count(self) -> int:
        return self._picked_total

    # -- settings -----------------------------------------------------------
    def get_settings(self) -> dict:
        with self._lock:
            out = dict(self._settings)
            out["conf"] = self._conf
            return out

    def apply_settings(self, updates: dict) -> dict:
        """Validate and apply new settings.

        `conf` (the detection-sensitivity slider) is applied live -- no
        session restart. Room/fan/hamper geometry rebuilds the whole session
        (the sim restarts): any running mission is aborted and the claw
        re-parks at the freshly computed rest pose.
        """
        if not isinstance(updates, dict):
            raise CommandError("config body must be a JSON object", 400)
        updates = dict(updates)
        if "conf" in updates:
            raw = updates.pop("conf")
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise CommandError("conf must be a number", 400)
            with self._lock:
                self._conf = float(np.clip(float(raw), CONF_MIN, CONF_MAX))
                self._on_conf_changed()
            if not updates:                 # conf-only change: no restart
                return self.get_settings()
        unknown = set(updates) - set(DEFAULT_SETTINGS)
        if unknown:
            raise CommandError(f"unknown config keys: {sorted(unknown)}", 400)
        with self._lock:
            merged = dict(self._settings)
            merged.update(updates)
            err = validate_settings(merged)
            if err:
                raise CommandError(err, 400)
            self._settings = merged
            self._abort_all_motion()
            self._rebuild_robot()
            self._on_settings_applied()
            self._append_log(
                "Configuration applied "
                f"(room {merged['room_width']}x{merged['room_depth']}x"
                f"{merged['room_height']} m); session restarted."
            )
            return self.get_settings()

    def _abort_all_motion(self) -> None:
        """Drop any mission/manual motion (used by config apply and STOP)."""

    def _on_settings_applied(self) -> None:
        """Hook for subclasses after a geometry rebuild."""

    def _on_conf_changed(self) -> None:
        """Hook for subclasses when the confidence threshold changes."""

    # -- commands -----------------------------------------------------------
    def command(self, cmd: str, args: dict | None) -> dict:
        if not isinstance(cmd, str) or cmd not in VALID_COMMANDS:
            raise CommandError(
                f"unknown command {cmd!r}; valid: {', '.join(VALID_COMMANDS)}", 400
            )
        if args is not None and not isinstance(args, dict):
            raise CommandError("args must be a JSON object", 400)
        with self._lock:
            if cmd != "stop":
                self._stopped = False     # any new command clears the banner
            handler = getattr(self, f"_cmd_{cmd}")
            return handler(args or {})

    # Shared jog validation: clamp -> fan keep-out -> static feasibility.
    def _validated_jog_target(self, args: dict) -> np.ndarray:
        axis = args.get("axis")
        sign = args.get("sign")
        if axis not in ("x", "y", "z"):
            raise CommandError("jog args need axis: one of 'x'|'y'|'z'", 400)
        if sign not in (1, -1, 1.0, -1.0):
            raise CommandError("jog args need sign: 1 or -1", 400)
        cfg = self.robot.cfg
        target = self._position.copy()
        target["xyz".index(axis)] += JOG_STEP_M * float(sign)
        # Clamp into the safe box (walls, floor clearance, ceiling clearance).
        target[0] = float(np.clip(target[0], WALL_MARGIN, cfg.room_width - WALL_MARGIN))
        target[1] = float(np.clip(target[1], WALL_MARGIN, cfg.room_depth - WALL_MARGIN))
        target[2] = float(
            np.clip(target[2], SAFE_MIN_Z, cfg.room_height - CEILING_CLEARANCE_M)
        )
        # Fan keep-out: the point AND all four cables must clear the cylinder.
        if not cables_clear_of_fan(self.robot.anchors, target, cfg.fan):
            raise CommandError(
                "jog rejected: target (or a cable to it) violates the fan keep-out",
                409,
            )
        _, feasible = self.robot.solve_tensions(target)
        if not feasible:
            raise CommandError(
                "jog rejected: no feasible cable tensions at the target", 409
            )
        return target

    def _require_idle(self, what: str) -> None:
        if self._mission_active():
            raise CommandError(f"{what} rejected: a mission is active (stop it first)", 409)

    # -- planning + 3-D room view (ported from the perception console) -------
    def _detection_objects(self) -> list:
        """The current detections as perception `Detection` objects."""
        from ..perception.detector import Detection

        return [
            Detection(
                position=np.array([d["floor"][0], d["floor"][1], 0.0]),
                label=d["label"], confidence=float(d["confidence"]),
                area=float(d.get("area", 0.0)),
                bbox=tuple(d["bbox"]) if d.get("bbox") else None,
            )
            for d in self.detections()
        ]

    def _plan_inputs(self):
        """Snapshot (items, robot, hamper, position, rest) under the lock."""
        from ..perception.live import LiveDetector

        with self._lock:
            items = self._detection_objects()
            robot = self.robot
            hamper_xy = self.hamper_xy
            position = self._position.copy()
            rest = self.rest.copy()
        holder = LiveDetector(None)
        holder._items = list(items)
        return items, holder, robot, hamper_xy, position, rest

    def plan(self) -> dict:
        """Plan the pickup order + per-target winch (cable-length) commands for
        the current detections, using the SAME Controller that drives the
        robot. Planning starts from the claw's current pose."""
        from ..control.state_machine import Controller

        items, holder, robot, hamper_xy, position, _ = self._plan_inputs()
        ctrl = Controller(robot, holder, hamper_xy=hamper_xy)
        ctrl.position = position

        anchors = ["A", "B", "C", "D"]
        steps = []
        for _ in range(PLAN_MAX_STEPS):
            actions = ctrl._plan_cycle()
            if actions is None:
                break
            grab_pt = next((p for k, p in actions if k == "grip"), None)
            lengths = robot.cable_lengths(grab_pt)
            tensions, feasible = robot.solve_tensions(grab_pt)
            steps.append({
                "order": len(steps) + 1,
                "label": ctrl.target.label,
                "confidence": round(float(ctrl.target.confidence), 2),
                "floor": [round(float(ctrl.target.position[0]), 2),
                          round(float(ctrl.target.position[1]), 2)],
                "grab_z": round(float(grab_pt[2]), 3),
                "cables": {a: round(float(L), 3) for a, L in zip(anchors, lengths)},
                "max_tension_N": round(float(np.max(tensions)), 1),
                "feasible": bool(feasible),
            })
        return {
            "planned": len(steps),
            "total_detected": len(items),
            "unreachable": max(0, len(items) - len(steps)),
            "trips": len(steps) + (1 if steps else 0),
            "hamper": [round(float(hamper_xy[0]), 2), round(float(hamper_xy[1]), 2)],
            "rest": [round(float(x), 2) for x in ctrl.rest],
            "cruise_z": round(float(ctrl.cruise_z), 2),
            "steps": steps,
        }

    def render_room_png(self) -> bytes:
        """One 3-D matplotlib snapshot of the room with current detections,
        the claw at its current pose, hamper, and rest marker."""
        import matplotlib
        matplotlib.use("Agg", force=True)  # headless render in a worker thread
        import matplotlib.pyplot as plt
        from .. import simulator

        _, holder, robot, hamper_xy, position, rest = self._plan_inputs()
        with self._render_lock:  # pyplot global state -> one render at a time
            fig = plt.figure(figsize=(7, 5))
            ax = fig.add_subplot(111, projection="3d")
            simulator.render_frame(
                robot, effector=position, detector=holder, hamper_xy=hamper_xy,
                rest_xyz=rest, ax=ax, title="Room — detections + plan",
            )
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
            plt.close(fig)
        return buf.getvalue()

    def render_room_gif(self) -> bytes | None:
        """Render an animated GIF of the claw flying the whole planned route.

        Reuses the simulator's animate_run (same code that makes run.gif).
        Cached by a signature of the current detections + room so repeat
        requests are instant. Returns None when nothing is reachable.
        """
        import hashlib
        import os
        import tempfile
        import matplotlib
        matplotlib.use("Agg", force=True)
        from ..control.state_machine import Controller
        from .. import simulator

        items, holder, robot, hamper_xy, _, rest = self._plan_inputs()
        if not items:
            return None
        sig = hashlib.md5(
            repr([(round(float(d.position[0]), 3), round(float(d.position[1]), 3), d.label)
                  for d in items]
                 + [round(float(robot.cfg.room_width), 3),
                    round(float(robot.cfg.room_depth), 3)]).encode()
        ).hexdigest()
        if self._gif_cache.get("sig") == sig and self._gif_cache.get("bytes"):
            return self._gif_cache["bytes"]

        ctrl = Controller(robot, holder, hamper_xy=hamper_xy)
        paths = ctrl.run()  # empties holder as it "picks up" each item
        if not paths:
            return None
        holder._items = list(items)  # restore so laundry shows during the flight

        with self._render_lock:  # pyplot + PillowWriter -> one render at a time
            fd, tmp = tempfile.mkstemp(suffix=".gif")
            os.close(fd)
            try:
                simulator.animate_run(
                    robot, paths, holder, hamper_xy, out_path=tmp,
                    rest_xyz=rest, max_frames=ROOM_GIF_MAX_FRAMES, fps=ROOM_GIF_FPS,
                )
                with open(tmp, "rb") as fh:
                    data = fh.read()
            finally:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
        self._gif_cache = {"sig": sig, "bytes": data}
        return data


# ---------------------------------------------------------------------------
# Simulation backend
# ---------------------------------------------------------------------------
class SimSession(RobotSession):
    """Pure-software session: existing planner + SimulatedDetector + renderer.

    A tick thread advances the claw along `Controller.iter_actions()` output
    (WAYPOINTS_PER_TICK of the 50 Hz waypoints per tick, i.e. roughly real
    time) and caches a rendered JPEG for the MJPEG stream. Without the thread
    (unit tests) every command still works synchronously; queued motion simply
    doesn't play back.
    """

    mode = "sim"

    def __init__(self, settings: dict | None = None, seed: int | None = None,
                 conf: float = DEFAULT_CONF):
        super().__init__(settings, conf=conf)
        self._rng = np.random.default_rng(seed)
        self._homed = True            # sim winches are implicitly homed
        self._tick = 0
        self._battery_v = SIM_BATTERY_FULL_V

        # Mission playback state.
        self._controller: Controller | None = None
        self._actions = None                       # generator from iter_actions
        self._consumed_log = 0
        self._current_path: np.ndarray | None = None
        self._path_i = 0
        # Manual (home/park) playback, outside missions.
        self._manual_path: np.ndarray | None = None
        self._manual_i = 0

        # What the "camera" shows: display copies of the scattered items.
        self._display_items: list[dict] = []
        self._scatter_items(initial=True)

        self._frame_jpeg: bytes | None = None
        self._thread: threading.Thread | None = None
        self._shutdown = threading.Event()
        self._append_log("Simulation session ready; claw parked at rest pose.")

    # -- lifecycle ----------------------------------------------------------
    def start_background(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name="sim-tick")
        self._thread.start()

    def shutdown(self) -> None:
        self._shutdown.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _loop(self) -> None:
        interval = 1.0 / TICK_HZ
        while not self._shutdown.is_set():
            t0 = time.monotonic()
            with self._lock:
                self._step()
                self._frame_jpeg = self._render_frame()
            time.sleep(max(0.0, interval - (time.monotonic() - t0)))

    # -- laundry scatter ----------------------------------------------------
    def _scatter_items(self, initial: bool = False) -> "object":
        """Scatter fresh laundry; returns the SimulatedDetector for a mission."""
        from ..perception.detector import SimulatedDetector

        n_items = int(self._rng.integers(4, 7))
        seed = int(self._rng.integers(0, 2**31 - 1))
        detector = SimulatedDetector(self.robot.cfg, n_items=n_items, seed=seed)
        self._display_items = [
            {
                "x": float(d.position[0]),
                "y": float(d.position[1]),
                "label": d.label,
                "confidence": float(d.confidence),
                "area": float(d.area),
            }
            for d in detector.detect()
        ]
        if not initial:
            self._append_log(f"Scattered {n_items} laundry item(s).")
        return detector

    # -- per-tick physics-free playback --------------------------------------
    def _step(self) -> None:
        self._tick += 1
        self._battery_v = max(
            SIM_BATTERY_EMPTY_V, self._battery_v - SIM_BATTERY_DRAIN_V_PER_TICK
        )
        if self._paused:
            return
        if self._manual_path is not None:
            self._advance_manual()
            return
        if self._actions is not None:
            self._advance_mission()

    def _advance_manual(self) -> None:
        for _ in range(WAYPOINTS_PER_TICK):
            if self._manual_i >= len(self._manual_path):
                self._manual_path = None
                self._append_log(f"Reached target {self._position.round(2)}.")
                return
            self._position = self._manual_path[self._manual_i].copy()
            self._manual_i += 1

    def _advance_mission(self) -> None:
        budget = WAYPOINTS_PER_TICK
        while budget > 0:
            if self._current_path is not None:
                if self._path_i < len(self._current_path):
                    self._position = self._current_path[self._path_i].copy()
                    self._path_i += 1
                    budget -= 1
                    continue
                self._current_path = None
            try:
                kind, payload = next(self._actions)
            except StopIteration:
                self._finish_mission()
                return
            self._drain_controller_log()
            if kind == "move":
                self._current_path = np.asarray(payload, dtype=float)
                self._path_i = 0
            elif kind == "grip":
                self._gripping = True
                self._remove_display_item_near(np.asarray(payload))
                self._append_log("Gripper closed (tendon pulled, fingers curled).")
            elif kind == "release":
                self._gripping = False
                # Count deliveries when they actually happen in playback (the
                # controller's own picked_up increments at planning time).
                self._picked_total += 1
                self._append_log("Gripper opened over the hamper.")

    def _remove_display_item_near(self, point: np.ndarray) -> None:
        """Take the grabbed item off the camera view (nearest to the grab point)."""
        if not self._display_items:
            return
        dists = [
            float(np.hypot(it["x"] - point[0], it["y"] - point[1]))
            for it in self._display_items
        ]
        idx = int(np.argmin(dists))
        if dists[idx] < 0.3:
            self._display_items.pop(idx)

    def _drain_controller_log(self) -> None:
        if self._controller is None:
            return
        lines = self._controller.log_lines
        for line in lines[self._consumed_log:]:
            # The controller narrates at PLANNING time, ahead of real-time
            # playback (e.g. "[DELIVER] Delivered" is logged when the trip is
            # planned, before the claw has flown it). Prefix so an operator
            # can tell planner narration from executed events, which this
            # session logs unprefixed as they actually happen.
            self._append_log(f"plan · {line}")
        self._consumed_log = len(lines)

    def _finish_mission(self) -> None:
        self._drain_controller_log()
        self._controller = None
        self._actions = None
        self._current_path = None
        self._append_log("Mission complete; claw parked. Press Start to run again.")

    # -- status hooks -------------------------------------------------------
    def detections(self) -> list[dict]:
        """What the synthetic 'camera' currently sees, above the conf slider."""
        with self._lock:
            return [
                {
                    "label": it["label"],
                    "confidence": round(float(it["confidence"]), 3),
                    "floor": [round(float(it["x"]), 3), round(float(it["y"]), 3)],
                    "bbox": None,
                    "area": float(it["area"]),
                }
                for it in self._display_items
                if float(it["confidence"]) >= self._conf
            ]

    def _mission_active(self) -> bool:
        return self._actions is not None

    def _phase(self) -> str:
        if self._stopped:
            return "STOPPED"
        if self._paused:
            return "PAUSED"
        if self._actions is not None and self._controller is not None:
            # The planner is lazy: before the first action is consumed the
            # controller still says IDLE -- report the upcoming SCAN instead.
            name = self._controller.state.name
            return "SCAN" if name == "IDLE" else name
        if self._manual_path is not None:
            return "MOVING"
        return "IDLE"

    def _claw_status(self) -> dict:
        # Simulated ESP32 telemetry: a healthy WiFi link and a slow 2S drain.
        rssi = -46 + 4.0 * np.sin(self._tick / 40.0)
        pct = (self._battery_v - SIM_BATTERY_EMPTY_V) / (
            SIM_BATTERY_FULL_V - SIM_BATTERY_EMPTY_V
        )
        return {
            "link": "sim-wifi",
            "rssi_dbm": round(float(rssi), 1),
            "battery_v": round(self._battery_v, 2),
            "battery_pct": round(float(100.0 * pct), 1),
        }

    # -- commands -----------------------------------------------------------
    def _abort_all_motion(self) -> None:
        self._controller = None
        self._actions = None
        self._current_path = None
        self._manual_path = None
        self._paused = False

    def _on_settings_applied(self) -> None:
        self._scatter_items(initial=True)

    def _cmd_start(self, args: dict) -> dict:
        self._require_idle("start")
        detector = self._scatter_items()
        controller = Controller(self.robot, detector, hamper_xy=self.hamper_xy)
        controller.position = self._position.copy()   # plan from the real pose
        self._controller = controller
        self._consumed_log = 0
        self._actions = controller.iter_actions()
        self._manual_path = None
        self._paused = False
        self._append_log("Mission started.")
        return {"ok": True, "phase": self._phase()}

    def _cmd_pause(self, args: dict) -> dict:
        if self._actions is None and self._manual_path is None:
            raise CommandError("pause rejected: nothing is moving", 409)
        self._paused = True
        self._append_log("Paused.")
        return {"ok": True, "phase": self._phase()}

    def _cmd_resume(self, args: dict) -> dict:
        if not self._paused:
            raise CommandError("resume rejected: not paused", 409)
        self._paused = False
        self._reconnect_after_jog()
        self._append_log("Resumed.")
        return {"ok": True, "phase": self._phase()}

    def _reconnect_after_jog(self) -> None:
        """If the operator jogged while paused, glide back to the plan."""
        if self._current_path is None or self._path_i >= len(self._current_path):
            return
        next_wp = self._current_path[self._path_i]
        if np.linalg.norm(next_wp - self._position) > 0.02:
            bridge = straight_line(self._position, next_wp)
            self._current_path = np.vstack([bridge, self._current_path[self._path_i:]])
            self._path_i = 0

    def _cmd_stop(self, args: dict) -> dict:
        self._abort_all_motion()
        self._stopped = True
        self._append_log(
            "STOP: mission aborted, motion halted. "
            "(Software stop only -- the physical kill switch is the power strip.)"
        )
        return {"ok": True, "phase": self._phase()}

    def _cmd_home(self, args: dict) -> dict:
        self._require_idle("home")
        self._manual_path = safe_transit(self._position, self.rest, self._cruise_z())
        self._manual_i = 0
        self._homed = True
        self._append_log("Homing: transiting to the rest pose (sim winches zeroed).")
        return {"ok": True, "phase": self._phase()}

    def _cmd_park(self, args: dict) -> dict:
        self._require_idle("park")
        self._manual_path = safe_transit(self._position, self.rest, self._cruise_z())
        self._manual_i = 0
        self._append_log(f"Parking at rest pose {self.rest.round(2)}.")
        return {"ok": True, "phase": self._phase()}

    def _cmd_grip(self, args: dict) -> dict:
        if self._mission_active() and not self._paused:
            raise CommandError("grip rejected: mission running (pause or stop first)", 409)
        self._gripping = True
        self._append_log("Manual grip.")
        return {"ok": True, "gripping": True}

    def _cmd_release(self, args: dict) -> dict:
        if self._mission_active() and not self._paused:
            raise CommandError("release rejected: mission running (pause or stop first)", 409)
        self._gripping = False
        self._append_log("Manual release.")
        return {"ok": True, "gripping": False}

    def _cmd_jog(self, args: dict) -> dict:
        if self._mission_active() and not self._paused:
            raise CommandError("jog rejected: only allowed while paused or idle", 409)
        if self._manual_path is not None:
            raise CommandError("jog rejected: a home/park move is in progress", 409)
        target = self._validated_jog_target(args)
        self._position = target
        self._append_log(f"Jog -> {target.round(2)}.")
        x, y, z = (round(float(v), 3) for v in target)
        return {"ok": True, "pose": {"x": x, "y": y, "z": z}}

    # -- rendering ----------------------------------------------------------
    def frame_jpeg(self) -> bytes:
        with self._lock:
            if self._frame_jpeg is not None:
                return self._frame_jpeg
            return self._render_frame()

    def _render_frame(self) -> bytes:
        """Draw the top-down 'ceiling camera' view of the sim world."""
        cfg = self.robot.cfg
        ppm = min(FRAME_MAX_W_PX / cfg.room_width, FRAME_MAX_H_PX / cfg.room_depth)
        w_px = int(cfg.room_width * ppm) + 2 * FRAME_PAD_PX
        h_px = int(cfg.room_depth * ppm) + 2 * FRAME_PAD_PX

        def px(x: float, y: float) -> tuple[float, float]:
            """World (x, y) meters -> image pixels (+y up -> screen up)."""
            return (FRAME_PAD_PX + x * ppm, h_px - FRAME_PAD_PX - y * ppm)

        img = Image.new("RGB", (w_px, h_px), (13, 13, 13))
        draw = ImageDraw.Draw(img, "RGBA")

        # Floor plane + a light 0.5 m grid.
        x0, y0 = px(0.0, cfg.room_depth)
        x1, y1 = px(cfg.room_width, 0.0)
        draw.rectangle([x0, y0, x1, y1], fill=(26, 26, 25), outline=(70, 70, 66))
        for gx in np.arange(0.5, cfg.room_width, 0.5):
            a, b = px(gx, 0.0), px(gx, cfg.room_depth)
            draw.line([a, b], fill=(44, 44, 42), width=1)
        for gy in np.arange(0.5, cfg.room_depth, 0.5):
            a, b = px(0.0, gy), px(cfg.room_width, gy)
            draw.line([a, b], fill=(44, 44, 42), width=1)

        # Fan keep-out cylinder (top-down disc).
        fan = cfg.fan
        if fan is not None and fan.enabled:
            cx, cy = px(fan.cx, fan.cy)
            r = fan.radius * ppm
            draw.ellipse(
                [cx - r, cy - r, cx + r, cy + r],
                fill=(208, 59, 59, 42), outline=(208, 59, 59, 170), width=2,
            )
            draw.text((cx, cy), "FAN KEEP-OUT", font=_font_small(),
                      fill=(236, 131, 90, 220), anchor="mm")

        # Hamper.
        hx, hy = px(*self.hamper_xy)
        hr = HAMPER_DRAW_M * 0.5 * ppm
        draw.rectangle([hx - hr, hy - hr, hx + hr, hy + hr],
                       outline=(217, 89, 38, 230), width=2)
        draw.text((hx, hy + hr + 3), "HAMPER", font=_font_small(),
                  fill=(217, 89, 38, 230), anchor="ma")

        # Laundry with detection-style boxes + labels.
        for it in self._display_items:
            side = max(np.sqrt(max(it["area"], 1e-4)), MIN_ITEM_BOX_M)
            bx, by = px(it["x"], it["y"])
            br = side * 0.5 * ppm
            draw.rectangle([bx - br, by - br, bx + br, by + br],
                           outline=(25, 158, 112, 230), width=2)
            draw.ellipse([bx - 3, by - 3, bx + 3, by + 3], fill=(25, 158, 112, 255))
            draw.text((bx - br, by - br - 3), f"{it['label']} {it['confidence']:.2f}",
                      font=_font_small(), fill=(122, 216, 176, 255), anchor="lb")

        # Rest pose marker.
        rx, ry = px(self.rest[0], self.rest[1])
        draw.polygon([(rx, ry - 7), (rx - 6, ry + 5), (rx + 6, ry + 5)],
                     outline=(144, 133, 233, 220))

        # Cables from the four ceiling anchors to the claw.
        ex, ey = px(self._position[0], self._position[1])
        for i, anchor in enumerate(self.robot.anchors):
            ax, ay = px(anchor[0], anchor[1])
            draw.line([(ax, ay), (ex, ey)], fill=(57, 135, 229, 130), width=2)
            draw.rectangle([ax - 5, ay - 5, ax + 5, ay + 5], fill=(200, 200, 195, 255))
            draw.text((ax, ay), "ABCD"[i], font=_font_small(),
                      fill=(13, 13, 13, 255), anchor="mm")

        # The claw: filled when gripping, ring when open; z as a halo + text.
        halo = 6 + 10 * (float(self._position[2]) / cfg.room_height)
        draw.ellipse([ex - halo, ey - halo, ex + halo, ey + halo],
                     outline=(230, 103, 103, 160), width=1)
        if self._gripping:
            draw.ellipse([ex - 6, ey - 6, ex + 6, ey + 6], fill=(230, 103, 103, 255))
        else:
            draw.ellipse([ex - 6, ey - 6, ex + 6, ey + 6],
                         outline=(230, 103, 103, 255), width=2)
        draw.line([(ex - 10, ey), (ex + 10, ey)], fill=(255, 255, 255, 180), width=1)
        draw.line([(ex, ey - 10), (ex, ey + 10)], fill=(255, 255, 255, 180), width=1)
        draw.text((ex + 12, ey), f"z={self._position[2]:.2f} m", font=_font_small(),
                  fill=(255, 255, 255, 210), anchor="lm")

        # OSD (camera-style overlay).
        osd = [
            "SIM CAM 01 - TOPDOWN",
            f"PHASE {self._phase()}   t={self._tick / TICK_HZ:7.1f}s",
            f"POS {self._position[0]:+.2f} {self._position[1]:+.2f} "
            f"{self._position[2]:+.2f} m   PICKED {self._picked_count()}",
        ]
        for i, line in enumerate(osd):
            draw.text((8, 6 + 14 * i), line, font=_font_small(),
                      fill=(195, 194, 183, 235))
        # 1 m scale bar, bottom-right.
        sx1, sy = w_px - FRAME_PAD_PX, h_px - 12
        draw.line([(sx1 - ppm, sy), (sx1, sy)], fill=(137, 135, 129, 255), width=2)
        draw.text((sx1 - ppm / 2, sy - 4), "1 m", font=_font_small(),
                  fill=(137, 135, 129, 255), anchor="mb")

        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=JPEG_QUALITY)
        return buf.getvalue()


_FONT_CACHE: dict[str, ImageFont.ImageFont] = {}


def _font_small() -> ImageFont.ImageFont:
    if "small" not in _FONT_CACHE:
        try:
            _FONT_CACHE["small"] = ImageFont.load_default(size=11)
        except TypeError:  # older Pillow: no size kwarg
            _FONT_CACHE["small"] = ImageFont.load_default()
    return _FONT_CACHE["small"]


# ---------------------------------------------------------------------------
# Live backend  (motion side *** NEEDS BENCH VALIDATION -- see docs/APP.md ***)
# ---------------------------------------------------------------------------
class LiveSession(RobotSession):
    """Same interface as SimSession, wired to the real parts.

    Composition (all existing modules, nothing reimplemented):
        PerceptionPipeline (capture thread + inference thread + self-healing
        reopen, ported intact from the camera-validated perception console)
        -> detections + annotated feed; SerialDriver (winches) + WiFiGripper
        (claw servo) when reachable; Controller.iter_actions() +
        subsample_path (mission execution -- the exact pipeline of
        hardware/executor.run_on_hardware, with pause/stop checks between
        waypoints).

    Degrades gracefully: if the serial link / gripper cannot be opened the
    session still runs as CAMERA-ONLY live mode -- feed, detections, plan and
    3-D view all work; motion commands are refused with 409 and the UI shows
    a banner. `demo=True` skips the camera too and seeds simulated laundry
    through the real detection->plan pipeline (headless verification mode).

    MOTION IS UNTESTED ON HARDWARE. Before trusting it on the bench, validate:
      * serial homing + move round-trips (scripts/hardware_dryrun.py first);
      * the OverheadLinearMapper calibration for YOUR camera mount;
      * WiFiGripper reachability (ESP32 host in hardware/hw_config.py);
      * that STOP between waypoints halts quickly enough at MOVE_STEP_M;
      * claw battery/RSSI telemetry (not implemented -- reported as unknown).
    The physical kill switch remains the power strip.
    """

    mode = "live"

    def __init__(self, camera_index: int = 0, settings: dict | None = None,
                 demo: bool = False, conf: float = DEFAULT_CONF):
        super().__init__(settings, conf=conf)
        self.camera_index = camera_index
        self.demo = demo
        self.pipeline = None
        self.driver = None
        self.gripper = None
        self._hw_connected = False
        self._hw_reason = "not connected yet (call connect())"
        self._controller: Controller | None = None
        self._mission_thread: threading.Thread | None = None
        self._stop_flag = threading.Event()

    # -- lifecycle ----------------------------------------------------------
    def connect(self) -> None:
        """Start the perception pipeline, then try the winches + gripper.

        A missing camera (outside --demo) is fatal; missing hardware is not:
        the session continues camera-only with motion disabled.
        """
        from .perception import PerceptionPipeline

        cfg = self.robot.cfg
        pipeline = PerceptionPipeline(
            camera_index=self.camera_index,
            conf=self._conf,
            source="demo" if self.demo else "camera",
            room_width=cfg.room_width,
            room_depth=cfg.room_depth,
        )
        try:
            pipeline.start()
        except Exception as exc:
            raise RuntimeError(
                f"Live mode unavailable: {exc}\n"
                "Live mode needs opencv-python, ultralytics and a camera. "
                "Run with --sim, or with --live --demo for the no-camera "
                "demo (simulated laundry, real plan pipeline)."
            ) from exc
        self.pipeline = pipeline

        if self.demo:
            self._hw_connected = False
            self._hw_reason = "demo mode: no camera, no hardware (simulated laundry)"
            self._append_log(
                "Live session in --demo mode: simulated laundry through the "
                "real detection->plan pipeline. Motion controls disabled."
            )
            return
        try:
            from ..hardware.driver import SerialDriver
            from ..hardware.gripper import WiFiGripper

            self.driver = SerialDriver(self.robot).open()
            self.gripper = WiFiGripper()
            self._hw_connected = True
            self._hw_reason = "serial winches + WiFi gripper connected"
            self._append_log("Live session connected (camera + serial + gripper).")
        except Exception as exc:
            self.driver = None
            self.gripper = None
            self._hw_connected = False
            self._hw_reason = f"winches/gripper unreachable: {exc}"
            self._append_log(
                "CAMERA-ONLY live mode: winches/gripper unreachable "
                f"({exc}). Feed, detections and planning work; motion "
                "controls are disabled."
            )

    def shutdown(self) -> None:
        self._stop_flag.set()
        if self._mission_thread is not None:
            self._mission_thread.join(timeout=5.0)
        if self.pipeline is not None:
            self.pipeline.stop()
        if self.driver is not None:
            self.driver.close()

    # -- status hooks -------------------------------------------------------
    def detections(self) -> list[dict]:
        if self.pipeline is None:
            return []
        return [d for d in self.pipeline.detections()
                if float(d["confidence"]) >= self._conf]

    def _perception_stats(self) -> dict | None:
        return None if self.pipeline is None else self.pipeline.stats_snapshot()

    def _motion_enabled(self) -> bool:
        return self._hw_connected

    def _hardware_status(self) -> dict:
        return {"connected": self._hw_connected, "reason": self._hw_reason}

    def _on_conf_changed(self) -> None:
        if self.pipeline is not None:
            self.pipeline.conf = self._conf   # inference thread reads it live

    def _mission_active(self) -> bool:
        return self._mission_thread is not None and self._mission_thread.is_alive()

    def _phase(self) -> str:
        if self._stopped:
            return "STOPPED"
        if self._paused:
            return "PAUSED"
        if self._mission_active() and self._controller is not None:
            return self._controller.state.name
        return "IDLE"

    def _claw_status(self) -> dict:
        # BENCH VALIDATION: real RSSI/battery telemetry from the ESP32 is a
        # follow-up (firmware endpoint); until then the link is reported only
        # as configured/unknown.
        if self.gripper is None:
            return {"link": None, "rssi_dbm": None,
                    "battery_v": None, "battery_pct": None}
        from ..hardware.hw_config import EFFECTOR_HOST

        return {"link": f"wifi:{EFFECTOR_HOST}", "rssi_dbm": None,
                "battery_v": None, "battery_pct": None}

    # -- commands (mirror SimSession semantics) ------------------------------
    def _require_hardware(self, what: str) -> None:
        if not self._hw_connected:
            raise CommandError(
                f"{what} rejected: motion hardware not connected "
                f"({self._hw_reason})", 409
            )

    def _abort_all_motion(self) -> None:
        self._stop_flag.set()
        self._paused = False

    def _cmd_start(self, args: dict) -> dict:
        self._require_idle("start")
        self._require_hardware("start")
        if not self._homed:
            raise CommandError("home the winches before starting a mission", 409)
        # One look at the floor: freeze the pipeline's current detections into
        # a Detector the Controller can walk (same holder the plan panel uses).
        from ..perception.live import LiveDetector

        holder = LiveDetector(None)
        holder._items = self._detection_objects()
        controller = Controller(self.robot, holder, hamper_xy=self.hamper_xy)
        controller.position = self._position.copy()
        self._controller = controller
        self._stop_flag.clear()
        self._mission_thread = threading.Thread(
            target=self._run_mission, args=(controller,), daemon=True, name="live-mission"
        )
        self._mission_thread.start()
        self._append_log("Mission started (live).")
        return {"ok": True, "phase": self._phase()}

    def _run_mission(self, controller: Controller) -> None:
        """Execute the plan -- same loop as hardware/executor.run_on_hardware,
        plus pause/stop checks between waypoints so the operator stays in
        control. After a stop, NO further motion commands are sent."""
        from ..hardware.executor import subsample_path

        consumed = 0
        try:
            for kind, payload in controller.iter_actions():
                with self._lock:
                    for line in controller.log_lines[consumed:]:
                        self._append_log(line)
                    consumed = len(controller.log_lines)
                if kind == "move":
                    for wp in subsample_path(np.asarray(payload)):
                        if self._stop_flag.is_set():
                            return
                        while self._paused and not self._stop_flag.is_set():
                            time.sleep(0.1)
                        self.driver.move_to_point(wp)
                        with self._lock:
                            self._position = np.asarray(wp, dtype=float)
                elif kind == "grip":
                    self.gripper.grip()
                    with self._lock:
                        self._gripping = True
                elif kind == "release":
                    self.gripper.release()
                    with self._lock:
                        self._gripping = False
                        self._picked_total += 1   # count at actual delivery
        except Exception as exc:   # surface hardware faults in the log
            with self._lock:
                self._append_log(f"MISSION FAULT: {exc}")
        finally:
            with self._lock:
                self._controller = None

    def _cmd_pause(self, args: dict) -> dict:
        if not self._mission_active():
            raise CommandError("pause rejected: nothing is moving", 409)
        self._paused = True
        self._append_log("Paused (live: no motion commands while paused).")
        return {"ok": True, "phase": self._phase()}

    def _cmd_resume(self, args: dict) -> dict:
        if not self._paused:
            raise CommandError("resume rejected: not paused", 409)
        self._paused = False
        self._append_log("Resumed.")
        return {"ok": True, "phase": self._phase()}

    def _cmd_stop(self, args: dict) -> dict:
        self._abort_all_motion()
        self._stopped = True
        self._append_log(
            "STOP: motion command stream halted. Physical kill switch = power strip."
        )
        return {"ok": True, "phase": self._phase()}

    def _cmd_home(self, args: dict) -> dict:
        self._require_idle("home")
        self._require_hardware("home")
        self.driver.home()
        self._homed = True
        self._position = self.rest.copy()   # homed pose == calibrated rest pose
        self._append_log("Winches homed against their limit switches.")
        return {"ok": True}

    def _cmd_park(self, args: dict) -> dict:
        self._require_idle("park")
        self._require_hardware("park")
        if not self._homed:
            raise CommandError("home the winches before parking", 409)
        from ..hardware.executor import subsample_path

        path = subsample_path(safe_transit(self._position, self.rest, self._cruise_z()))
        self._stop_flag.clear()
        for wp in path:
            if self._stop_flag.is_set():
                break
            self.driver.move_to_point(wp)
            self._position = np.asarray(wp, dtype=float)
        self._append_log("Parked at rest pose.")
        return {"ok": True}

    def _cmd_grip(self, args: dict) -> dict:
        if self._mission_active() and not self._paused:
            raise CommandError("grip rejected: mission running", 409)
        self._require_hardware("grip")
        self.gripper.grip()
        self._gripping = True
        self._append_log("Manual grip.")
        return {"ok": True, "gripping": True}

    def _cmd_release(self, args: dict) -> dict:
        if self._mission_active() and not self._paused:
            raise CommandError("release rejected: mission running", 409)
        self._require_hardware("release")
        self.gripper.release()
        self._gripping = False
        self._append_log("Manual release.")
        return {"ok": True, "gripping": False}

    def _cmd_jog(self, args: dict) -> dict:
        if self._mission_active() and not self._paused:
            raise CommandError("jog rejected: only allowed while paused or idle", 409)
        self._require_hardware("jog")
        if not self._homed:
            raise CommandError("home the winches before jogging", 409)
        target = self._validated_jog_target(args)
        self.driver.move_to_point(target)
        self._position = target
        self._append_log(f"Jog -> {target.round(2)}.")
        x, y, z = (round(float(v), 3) for v in target)
        return {"ok": True, "pose": {"x": x, "y": y, "z": z}}

    # -- feed ---------------------------------------------------------------
    def frame_jpeg(self) -> bytes:
        """The pipeline's annotated camera frame (boxes + HUD burned in), or
        a rendered top-down placeholder in --demo mode."""
        if self.pipeline is None:
            return _placeholder_jpeg("LIVE CAMERA NOT CONNECTED")
        if self.pipeline.source == "demo":
            return self._demo_frame_jpeg()
        jpg = self.pipeline.annotated_jpeg()
        return jpg if jpg is not None else _placeholder_jpeg("waiting for camera...")

    def _demo_frame_jpeg(self) -> bytes:
        """No camera in --demo: draw a simple top-down map of the simulated
        detections so the feed panel still shows what the planner sees."""
        cfg = self.robot.cfg
        w_px, h_px, pad = 640, 400, 30
        ppm = min((w_px - 2 * pad) / cfg.room_width,
                  (h_px - 2 * pad) / cfg.room_depth)

        def px(x: float, y: float) -> tuple[float, float]:
            return (pad + x * ppm, h_px - pad - y * ppm)

        img = Image.new("RGB", (w_px, h_px), (13, 13, 13))
        draw = ImageDraw.Draw(img, "RGBA")
        x0, y0 = px(0.0, cfg.room_depth)
        x1, y1 = px(cfg.room_width, 0.0)
        draw.rectangle([x0, y0, x1, y1], fill=(26, 26, 25), outline=(70, 70, 66))
        for d in self.detections():
            bx, by = px(d["floor"][0], d["floor"][1])
            draw.ellipse([bx - 5, by - 5, bx + 5, by + 5], fill=(25, 158, 112, 255))
            draw.text((bx + 8, by), f'{d["label"]} {d["confidence"]:.2f}',
                      font=_font_small(), fill=(122, 216, 176, 255), anchor="lm")
        hx, hy = px(*self.hamper_xy)
        draw.rectangle([hx - 10, hy - 10, hx + 10, hy + 10],
                       outline=(217, 89, 38, 230), width=2)
        draw.text((8, 6), "LIVE --demo  (no camera; simulated laundry, real plan pipeline)",
                  font=_font_small(), fill=(195, 194, 183, 235))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=JPEG_QUALITY)
        return buf.getvalue()


def _placeholder_jpeg(text: str) -> bytes:
    img = Image.new("RGB", (640, 360), (13, 13, 13))
    draw = ImageDraw.Draw(img)
    draw.text((320, 180), text, font=_font_small(), fill=(195, 194, 183), anchor="mm")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=JPEG_QUALITY)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
def create_app(session: RobotSession) -> Flask:
    """Build the Flask app around one RobotSession (sim or live)."""
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config["ROBOT_SESSION"] = session

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/api/status")
    def api_status():
        return jsonify(session.status())

    @app.post("/api/command")
    def api_command():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or "cmd" not in body:
            return jsonify({"error": "body must be JSON: {cmd: ..., args: {...}}"}), 400
        try:
            result = session.command(body["cmd"], body.get("args"))
        except CommandError as exc:
            return jsonify({"error": str(exc)}), exc.status
        return jsonify(result)

    @app.get("/api/config")
    def api_config_get():
        return jsonify(session.get_settings())

    @app.post("/api/config")
    def api_config_post():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "config body must be a JSON object"}), 400
        try:
            applied = session.apply_settings(body)
        except CommandError as exc:
            return jsonify({"error": str(exc)}), exc.status
        return jsonify(applied)

    @app.get("/api/plan")
    def api_plan():
        return jsonify(session.plan())

    @app.get("/api/room.png")
    def api_room_png():
        return Response(session.render_room_png(), mimetype="image/png")

    @app.get("/api/room.gif")
    def api_room_gif():
        data = session.render_room_gif()
        if data is None:
            return Response(status=204)
        return Response(data, mimetype="image/gif")

    @app.get("/stream.mjpg")
    def stream():
        def frames():
            while True:
                jpg = session.frame_jpeg()
                yield (
                    b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                    + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n"
                )
                time.sleep(1.0 / STREAM_FPS)

        return Response(frames(),
                        mimetype="multipart/x-mixed-replace; boundary=frame")

    return app
