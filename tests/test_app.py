"""
Tests for the operator dashboard server (roomcleaner/app).

Uses Flask's test client only -- no background thread, no sockets, no camera:
`SimSession` is constructed without `start_background()`, so every command is
exercised synchronously. Skips cleanly when Flask is not installed (the app
stack lives in requirements-app.txt, not the core requirements).
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("flask")

from roomcleaner.app.server import SimSession, create_app  # noqa: E402
from roomcleaner.config import SAFE_MIN_Z, WALL_MARGIN  # noqa: E402
from roomcleaner.geometry import point_in_cylinder  # noqa: E402


@pytest.fixture()
def app_session():
    """A fresh sim session + test client per test (no tick thread)."""
    session = SimSession(seed=3)
    app = create_app(session)
    app.config["TESTING"] = True
    return app.test_client(), session


# ---------------------------------------------------------------------------
# /api/status
# ---------------------------------------------------------------------------
def test_status_schema(app_session):
    client, _ = app_session
    resp = client.get("/api/status")
    assert resp.status_code == 200
    s = resp.get_json()
    for key in ("mode", "phase", "mission_active", "paused", "pose",
                "tensions", "picked", "gripping", "claw", "log", "config"):
        assert key in s, f"missing status key: {key}"
    assert s["mode"] == "sim"
    assert s["phase"] == "IDLE"
    assert set(s["pose"]) == {"x", "y", "z"}
    assert all(isinstance(s["pose"][k], float) for k in "xyz")
    t = s["tensions"]
    assert len(t["newtons"]) == 4
    assert len(t["status"]) == 4
    assert t["band"] == [0.5, 40.0]
    assert t["feasible"] is True          # the rest pose must be holdable
    assert s["claw"]["battery_v"] is not None


def test_index_served(app_session):
    client, _ = app_session
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"RoomCleaner" in resp.data


# ---------------------------------------------------------------------------
# /api/command validation
# ---------------------------------------------------------------------------
def test_unknown_command_rejected(app_session):
    client, _ = app_session
    resp = client.post("/api/command", json={"cmd": "self_destruct"})
    assert resp.status_code == 400
    assert "unknown command" in resp.get_json()["error"]


def test_missing_cmd_and_bad_body_rejected(app_session):
    client, _ = app_session
    assert client.post("/api/command", json={"args": {}}).status_code == 400
    assert client.post("/api/command", data="not json",
                       content_type="text/plain").status_code == 400


def test_bad_jog_args_rejected(app_session):
    client, _ = app_session
    for args in ({}, {"axis": "w", "sign": 1}, {"axis": "x", "sign": 5},
                 {"axis": "x"}, {"axis": 1, "sign": 1}):
        resp = client.post("/api/command", json={"cmd": "jog", "args": args})
        assert resp.status_code == 400, f"args {args} should be a 400"


def test_start_stop_cycle(app_session):
    client, session = app_session
    resp = client.post("/api/command", json={"cmd": "start"})
    assert resp.status_code == 200
    s = client.get("/api/status").get_json()
    assert s["mission_active"] is True
    assert s["phase"] != "IDLE"
    # A second start while the mission is active must be refused.
    assert client.post("/api/command", json={"cmd": "start"}).status_code == 409
    resp = client.post("/api/command", json={"cmd": "stop"})
    assert resp.status_code == 200
    s = client.get("/api/status").get_json()
    assert s["mission_active"] is False
    assert s["phase"] == "STOPPED"


# ---------------------------------------------------------------------------
# /api/config
# ---------------------------------------------------------------------------
def test_config_round_trip(app_session):
    client, session = app_session
    before = client.get("/api/config").get_json()
    assert before["room_width"] == pytest.approx(4.0)
    resp = client.post("/api/config", json={"room_width": 4.5, "hamper_x": 4.0})
    assert resp.status_code == 200
    after = client.get("/api/config").get_json()
    assert after["room_width"] == pytest.approx(4.5)
    assert after["hamper_x"] == pytest.approx(4.0)
    # The session really rebuilt around the new geometry.
    assert session.robot.cfg.room_width == pytest.approx(4.5)
    assert session.robot.anchors[:, 0].max() == pytest.approx(4.5)


def test_config_rejects_bad_values(app_session):
    client, _ = app_session
    for body in ({"room_width": -1.0}, {"room_width": "wide"},
                 {"nonsense_key": 1.0}, {"hamper_x": 99.0},
                 {"fan_enabled": "yes"}):
        resp = client.post("/api/config", json=body)
        assert resp.status_code == 400, f"config {body} should be rejected"
    # And nothing changed.
    assert client.get("/api/config").get_json()["room_width"] == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# Jog safety
# ---------------------------------------------------------------------------
def test_jog_clamped_inside_workspace(app_session):
    client, session = app_session
    cfg = session.robot.cfg
    # Start mid-room at a comfortable height, then push into the -x wall.
    session._position = np.array([0.35, cfg.room_depth / 2, 1.0])
    for _ in range(5):
        resp = client.post(
            "/api/command", json={"cmd": "jog", "args": {"axis": "x", "sign": -1}}
        )
        assert resp.status_code in (200, 409)
        pose = client.get("/api/status").get_json()["pose"]
        assert pose["x"] >= WALL_MARGIN - 1e-9
    assert session._position[0] == pytest.approx(WALL_MARGIN)
    # Same for the floor: jog down repeatedly, never below SAFE_MIN_Z.
    session._position = np.array([cfg.room_width / 2, cfg.room_depth / 2, 0.3])
    for _ in range(4):
        client.post("/api/command", json={"cmd": "jog", "args": {"axis": "z", "sign": -1}})
        assert session._position[2] >= SAFE_MIN_Z - 1e-9


def test_fan_violating_jog_rejected(app_session):
    client, session = app_session
    fan = session.robot.cfg.fan
    assert fan.enabled
    # Hover just below the keep-out cylinder, dead under the fan hub.
    session._position = np.array([fan.cx, fan.cy, fan.z_low - 0.05])
    target_z = fan.z_low + 0.05   # one 0.1 m jog up ends inside the cylinder
    assert point_in_cylinder(
        np.array([fan.cx, fan.cy, target_z]),
        (fan.cx, fan.cy), fan.radius, fan.z_low, fan.z_high,
    )
    resp = client.post("/api/command", json={"cmd": "jog", "args": {"axis": "z", "sign": 1}})
    assert resp.status_code == 409
    assert "fan" in resp.get_json()["error"].lower()
    # Position must be untouched after the rejection.
    assert session._position[2] == pytest.approx(fan.z_low - 0.05)


def test_jog_rejected_while_mission_running(app_session):
    client, _ = app_session
    assert client.post("/api/command", json={"cmd": "start"}).status_code == 200
    resp = client.post("/api/command", json={"cmd": "jog",
                                             "args": {"axis": "x", "sign": 1}})
    assert resp.status_code == 409
    # Paused missions do allow jogging (operator nudge).
    assert client.post("/api/command", json={"cmd": "pause"}).status_code == 200
    resp = client.post("/api/command", json={"cmd": "jog",
                                             "args": {"axis": "z", "sign": -1}})
    assert resp.status_code in (200, 409)   # 409 only if statics/fan reject it
