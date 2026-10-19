"""Operator API wiring (Flask test client, simulated robot)."""
import time

from roomcleaner.cdpr.service import Service, create_app
from roomcleaner.cdpr.sim.harness import SimRobot

from .simkit import fast_cfg


def make(tmp_path, **cfg_over):
    r = SimRobot(fast_cfg(**cfg_over), seed=11, data_dir=tmp_path)
    svc = Service(r.ctx, data_dir=tmp_path)
    return r, svc, create_app(svc).test_client()


def wait_idle(svc, timeout=120):
    t = time.time()
    while svc.busy and time.time() - t < timeout:
        time.sleep(0.05)


def test_page_status_checks_and_room(tmp_path):
    r, svc, c = make(tmp_path)
    assert c.get("/").status_code == 200
    s = c.get("/api/status").get_json()
    assert s["state"] == "DISARMED" and len(s["checklist"]) >= 4
    assert c.get("/api/checks").get_json()["calibration"] == []
    bad = c.post("/api/room", json={"width_m": 0.2, "depth_m": 3, "height_m": 3})
    assert bad.status_code == 400
    ok = c.post("/api/room", json={"width_m": 3.4, "depth_m": 2.8, "height_m": 2.75,
                                   "anchors": {"A": [0.05, 0.05, 2.6]}}).get_json()
    assert ok["ok"] and ok["anchors"][0] == [0.05, 0.05, 2.6]


def test_start_requires_checklist_and_refuses_illegal_commands(tmp_path):
    r, svc, c = make(tmp_path, **{"startup.max_marker_wait_s": 2.0})
    assert c.post("/api/command", json={"cmd": "start"}).status_code == 409
    assert c.post("/api/command", json={"cmd": "recover"}).status_code == 409
    assert c.post("/api/command", json={"cmd": "bogus"}).status_code == 409
    r.simcam.covered = True                         # marker hidden: startup must pause, not guess
    assert c.post("/api/command", json={"cmd": "start", "checklist": True}).get_json()["ok"]
    wait_idle(svc)
    s = c.get("/api/status").get_json()
    assert s["state"] == "PAUSED" and any("marker" in x for x in s["reasons"])
    assert c.post("/api/command", json={"cmd": "disarm", "confirm": "yes"}).status_code == 409
