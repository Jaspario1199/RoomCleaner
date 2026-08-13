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

from roomcleaner.app.server import LiveSession, SimSession, create_app  # noqa: E402
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


# ---------------------------------------------------------------------------
# Absorbed perception-console panels: /api/plan, room views, conf slider
# ---------------------------------------------------------------------------
def test_plan_schema_sim(app_session):
    client, session = app_session
    resp = client.get("/api/plan")
    assert resp.status_code == 200
    p = resp.get_json()
    for key in ("planned", "total_detected", "unreachable", "trips",
                "hamper", "rest", "cruise_z", "steps"):
        assert key in p, f"missing plan key: {key}"
    assert p["total_detected"] == len(session.detections()) > 0
    assert p["planned"] >= 1                      # seed=3 scatter is reachable
    assert p["planned"] == len(p["steps"])
    assert p["unreachable"] == p["total_detected"] - p["planned"]
    for step in p["steps"]:
        assert set(step["cables"]) == {"A", "B", "C", "D"}
        assert all(v > 0 for v in step["cables"].values())
        assert step["max_tension_N"] > 0
        assert isinstance(step["feasible"], bool)
        assert len(step["floor"]) == 2
        assert step["grab_z"] >= 0.0


def test_status_includes_detections(app_session):
    client, _ = app_session
    s = client.get("/api/status").get_json()
    assert s["motion_enabled"] is True            # sim can always move
    assert isinstance(s["detections"], list) and s["detections"]
    d = s["detections"][0]
    assert set(d) == {"label", "confidence", "floor", "bbox", "area"}
    assert len(d["floor"]) == 2


def test_room_png_returns_image(app_session):
    client, _ = app_session
    resp = client.get("/api/room.png")
    assert resp.status_code == 200
    assert resp.content_type == "image/png"
    assert resp.data[:8] == b"\x89PNG\r\n\x1a\n"


def test_conf_slider_round_trip(app_session):
    client, session = app_session
    robot_before = session.robot
    assert client.get("/api/config").get_json()["conf"] == pytest.approx(0.25)
    resp = client.post("/api/config", json={"conf": 0.4})
    assert resp.status_code == 200
    assert resp.get_json()["conf"] == pytest.approx(0.4)
    assert client.get("/api/config").get_json()["conf"] == pytest.approx(0.4)
    # A conf-only change must NOT restart the session (unlike geometry).
    assert session.robot is robot_before
    # Values are clamped to the slider range, like the old console did.
    client.post("/api/config", json={"conf": 5.0})
    assert client.get("/api/config").get_json()["conf"] == pytest.approx(0.9)
    # Raising conf above the sim confidences hides detections from the panel.
    client.post("/api/config", json={"conf": 0.9})
    hidden = [d for d in session.detections() if d["confidence"] < 0.9]
    assert hidden == []
    assert client.post("/api/config",
                       json={"conf": "high"}).status_code == 400


# ---------------------------------------------------------------------------
# --live --demo: the headless merge-verification mode (no camera, no torch)
# ---------------------------------------------------------------------------
@pytest.fixture()
def demo_session():
    session = LiveSession(demo=True)
    session.connect()
    app = create_app(session)
    app.config["TESTING"] = True
    yield app.test_client(), session
    session.shutdown()


def test_live_demo_boots_headless(demo_session):
    client, session = demo_session
    s = client.get("/api/status").get_json()
    assert s["mode"] == "live"
    assert s["phase"] == "IDLE"
    assert s["motion_enabled"] is False           # demo has no winches/gripper
    assert s["hardware"]["connected"] is False
    assert "demo" in s["hardware"]["reason"]
    assert len(s["detections"]) >= 1              # simulated laundry is seeded
    assert s["perception"]["model_ready"] is True
    assert s["perception"]["source"] == "demo"


def test_live_demo_plan_uses_real_pipeline(demo_session):
    client, _ = demo_session
    p = client.get("/api/plan").get_json()
    assert p["total_detected"] >= 1
    assert p["planned"] >= 1                      # real Controller planned trips
    assert all(set(s["cables"]) == {"A", "B", "C", "D"} for s in p["steps"])


def test_live_demo_motion_refused_and_feed_serves(demo_session):
    client, session = demo_session
    for cmd in ("start", "home", "park", "grip", "release"):
        resp = client.post("/api/command", json={"cmd": cmd})
        assert resp.status_code == 409, f"{cmd} must be refused without hardware"
        assert "hardware" in resp.get_json()["error"].lower()
    # STOP always works (it only halts the command stream).
    assert client.post("/api/command", json={"cmd": "stop"}).status_code == 200
    # The feed still serves a JPEG (rendered demo frame, no camera).
    frame = session.frame_jpeg()
    assert frame[:2] == b"\xff\xd8"               # JPEG magic
    # And the room view renders.
    resp = client.get("/api/room.png")
    assert resp.status_code == 200
    assert resp.data[:8] == b"\x89PNG\r\n\x1a\n"
