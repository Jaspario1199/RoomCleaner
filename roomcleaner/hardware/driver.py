"""
Host-side motor driver: converts effector positions into winch step targets and
speaks the serial protocol to the Arduino firmware.

Protocol (newline-terminated ASCII, easy to debug in a serial monitor):
    host -> mcu     mcu -> host
    H DETACHED     HOMED        home all winches to their limit switches
    M a b c d       DONE         move winches to absolute step counts a,b,c,d
    G <deg>         OK           set the gripper servo angle
    ?               POS a b c d  query current step counts

Step convention: a winch's step target is how far its cable has been paid out
FROM its homed length, in steps:

    steps_i = round( (cable_length_i(P) - HOME_CABLE_LENGTHS[i]) * STEPS_PER_M )

The base `Driver` holds all the logic and is fully testable; `SerialDriver` adds
the real pyserial transport, and `MockDriver` records commands for tests / dry
runs.
"""

from __future__ import annotations

import numpy as np

from .hw_config import STEPS_PER_M, GRIP_ANGLE, RELEASE_ANGLE, SERIAL_PORT, BAUD, HOME_TRIGGER_LENGTHS_M


class Driver:
    """Transport-agnostic driver: builds commands, converts lengths to steps."""

    def __init__(self, robot, home_lengths=None, steps_per_m: float = STEPS_PER_M):
        self.robot = robot
        self.steps_per_m = steps_per_m
        # Home cable lengths: the length of each cable when its winch is homed
        # against its limit switch. CALIBRATE after building (measure each cable).
        # Default: the lengths at the robot's rest pose -- a reasonable placeholder.
        if home_lengths is None:
            home_lengths = robot.cable_lengths(robot.find_rest_position())
        self.home_lengths = np.asarray(home_lengths, dtype=float)
        if self.home_lengths.shape != (4,) or not np.isfinite(self.home_lengths).all() or np.any(self.home_lengths <= 0):
            raise ValueError("Need four finite positive measured home lengths")
        self.homed = False
        self.pose_initialized = False
        self.prepared_pose = None

    # -- length <-> steps ---------------------------------------------------
    def steps_for_point(self, point) -> list[int]:
        """Absolute winch step targets to place the effector at `point`."""
        lengths = self.robot.cable_lengths(point)
        return [int(round((L - Lh) * self.steps_per_m))
                for L, Lh in zip(lengths, self.home_lengths)]

    # -- high-level commands ------------------------------------------------
    def home(self, *, detached=False):
        self.homed = False
        self.pose_initialized = False
        self.prepared_pose = None
        self._command("H DETACHED", expect="HOMED")
        self.homed = True

    def prepare_pose(self, point, *, detached=False):
        """Pay out setup lengths while detached; this does not locate a claw."""
        if not detached:
            raise RuntimeError("Detach the claw before preparing its setup lengths")
        point = np.asarray(point, dtype=float)
        if point.shape != (3,) or not np.isfinite(point).all() or not self.robot.is_reachable(point):
            raise ValueError("Setup pose must be a finite reachable XYZ point")
        self.pose_initialized = False
        self.set_motion_speed(0.008)
        self.move_to_point(point)
        self.prepared_pose = point.copy()

    def confirm_pose(self, *, attached=False):
        if not self.homed or self.prepared_pose is None or not attached:
            raise RuntimeError("Prepare lengths, then attach/measure claw at the setup pose")
        self.pose_initialized = True
        return self.prepared_pose.copy()

    def stop(self):
        self.pose_initialized = False
        self.prepared_pose = None
        self.homed = False
        self._command("X", expect=None)

    def set_motion_speed(self, speed_m_s):
        if not np.isfinite(speed_m_s) or speed_m_s <= 0:
            raise ValueError("Speed must be finite and positive")
        self._command(f"V {min(1200.0, speed_m_s*self.steps_per_m):.3f}", expect="OK")

    def move_to_point(self, point):
        if not self.homed:
            raise RuntimeError("Home the winches before moving (call home()).")
        s = self.steps_for_point(point)
        try:
            self._command(f"M {s[0]} {s[1]} {s[2]} {s[3]}", expect="DONE")
        except Exception:
            self.homed = False
            self.pose_initialized = False
            self.prepared_pose = None
            raise

    def grip(self):
        self._command(f"G {int(GRIP_ANGLE)}", expect="OK")

    def release(self):
        self._command(f"G {int(RELEASE_ANGLE)}", expect="OK")

    # -- transport (overridden by subclasses) -------------------------------
    def _command(self, line: str, expect: str | None = None):
        raise NotImplementedError


class MockDriver(Driver):
    """Records commands instead of sending them -- for tests and dry runs."""

    def __init__(self, robot, home_lengths=None, **kw):
        super().__init__(robot, home_lengths, **kw)
        self.commands: list[str] = []

    def _command(self, line: str, expect: str | None = None):
        self.commands.append(line)


class SerialDriver(Driver):
    """Talks to the Arduino firmware over USB serial (needs `pyserial`)."""

    def __init__(self, robot, home_lengths=None, port: str = SERIAL_PORT,
                 baud: int = BAUD, timeout: float = 30.0, **kw):
        if home_lengths is None:
            if any(v is None for v in HOME_TRIGGER_LENGTHS_M):
                raise ValueError("Fill HOME_TRIGGER_LENGTHS_M with measured bead-triggered lengths")
            home_lengths = HOME_TRIGGER_LENGTHS_M
        super().__init__(robot, home_lengths, **kw)
        self.port, self.baud, self.timeout = port, baud, timeout
        self._ser = None

    def home(self, *, detached=False):
        if not detached:
            raise RuntimeError("Detach the claw before sequential homing; pass detached=True")
        super().home(detached=True)

    def open(self):
        try:
            import serial
        except ImportError as exc:  # pragma: no cover
            raise ImportError("SerialDriver needs pyserial: pip install pyserial") from exc
        self._ser = serial.Serial(self.port, self.baud, timeout=min(self.timeout, 0.5))
        # Arduino resets on connect; wait for its READY banner.
        import time
        ready_deadline = time.monotonic()+self.timeout
        while time.monotonic() < ready_deadline:
            if self._readline() == "READY":
                break
        else:
            self.close()
            raise RuntimeError("Firmware did not send READY")
        return self

    def _readline(self) -> str:
        return self._ser.readline().decode(errors="replace").strip()

    def _command(self, line: str, expect: str | None = None):
        if self._ser is None:
            raise RuntimeError("Call open() before sending commands.")
        self._ser.write((line + "\n").encode())
        if expect is None:
            return
        import time
        deadline = time.monotonic()+(max(self.timeout, 720.0) if line.startswith("H ") else self.timeout)
        while time.monotonic() < deadline:
            resp = self._readline()
            if resp.startswith(expect):
                return
            if resp.startswith("ERR"):
                raise RuntimeError(f"Firmware error for '{line}': {resp}")
            if resp == "":
                continue

        raise TimeoutError(f"No '{expect}' reply to '{line}' within deadline")

    def close(self):
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *exc):
        self.close()
