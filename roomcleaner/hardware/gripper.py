"""
Gripper backends. The gripper is a swappable module so the effector can be
wired (servo on the central Arduino) OR wireless (servo on an ESP32 on the
effector, commanded over WiFi).

    WiFiGripper  -- the wireless claw: HTTP GET to the effector's ESP32.
    SerialGripper-- the wired fallback: reuses the Arduino "G <deg>" command.
    MockGripper  -- records calls, for tests / dry runs.

Grip/release are not time-critical (unlike coordinated winch motion), so WiFi
latency here is harmless -- which is exactly why the gripper is the right place
to go wireless.
"""

from __future__ import annotations

from .hw_config import GRIP_ANGLE, RELEASE_ANGLE, EFFECTOR_HOST, EFFECTOR_PORT


class Gripper:
    def grip(self):
        raise NotImplementedError

    def release(self):
        raise NotImplementedError


class MockGripper(Gripper):
    """Records grip/release calls -- for tests and dry runs."""

    def __init__(self):
        self.calls: list[str] = []

    def grip(self):
        self.calls.append("grip")

    def release(self):
        self.calls.append("release")


class WiFiGripper(Gripper):
    """Commands the effector's ESP32 over WiFi (plain HTTP, no extra deps)."""

    def __init__(self, host: str = EFFECTOR_HOST, port: int = EFFECTOR_PORT,
                 timeout: float = 5.0):
        self.host, self.port, self.timeout = host, port, timeout

    def _get(self, path: str):
        import urllib.request
        url = f"http://{self.host}:{self.port}{path}"
        with urllib.request.urlopen(url, timeout=self.timeout) as resp:
            if resp.status >= 400:
                raise RuntimeError(f"effector returned {resp.status} for {path}")

    def grip(self):
        self._get(f"/grip?angle={int(GRIP_ANGLE)}")

    def release(self):
        self._get(f"/release?angle={int(RELEASE_ANGLE)}")


class SerialGripper(Gripper):
    """Wired fallback: drive the servo through the motor Arduino's `G` command."""

    def __init__(self, motor_driver):
        self.driver = motor_driver

    def grip(self):
        self.driver.grip()

    def release(self):
        self.driver.release()
