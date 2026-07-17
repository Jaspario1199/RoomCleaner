"""
Host-side motor driver: converts effector positions into winch step targets and
speaks the serial protocol to the Arduino firmware.

Protocol (newline-terminated ASCII, easy to debug in a serial monitor):
    host -> mcu     mcu -> host
    H               HOMED        home all winches to their limit switches
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

from .hw_config import STEPS_PER_M, GRIP_ANGLE, RELEASE_ANGLE, SERIAL_PORT, BAUD


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
        self.homed = False

    # -- length <-> steps ---------------------------------------------------
    def steps_for_point(self, point) -> list[int]:
        """Absolute winch step targets to place the effector at `point`."""
        lengths = self.robot.cable_lengths(point)
        return [int(round((L - Lh) * self.steps_per_m))
                for L, Lh in zip(lengths, self.home_lengths)]

    # -- high-level commands ------------------------------------------------
    def home(self):
        self._command("H", expect="HOMED")
        self.homed = True

    def move_to_point(self, point):
        if not self.homed:
            raise RuntimeError("Home the winches before moving (call home()).")
        s = self.steps_for_point(point)
        self._command(f"M {s[0]} {s[1]} {s[2]} {s[3]}", expect="DONE")

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
        super().__init__(robot, home_lengths, **kw)
        self.port, self.baud, self.timeout = port, baud, timeout
        self._ser = None

    def open(self):
        try:
            import serial
        except ImportError as exc:  # pragma: no cover
            raise ImportError("SerialDriver needs pyserial: pip install pyserial") from exc
        self._ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        # Arduino resets on connect; wait for its READY banner.
        self._readline()
        return self

    def _readline(self) -> str:
        return self._ser.readline().decode(errors="replace").strip()

    def _command(self, line: str, expect: str | None = None):
        if self._ser is None:
            raise RuntimeError("Call open() before sending commands.")
        self._ser.write((line + "\n").encode())
        if expect is None:
            return
        while True:
            resp = self._readline()
            if resp.startswith(expect):
                return
            if resp.startswith("ERR"):
                raise RuntimeError(f"Firmware error for '{line}': {resp}")
            if resp == "":
                raise TimeoutError(f"No '{expect}' reply to '{line}'.")

    def close(self):
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *exc):
        self.close()
