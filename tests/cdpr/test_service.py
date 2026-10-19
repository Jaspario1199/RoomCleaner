"""Operator API wiring (Flask test client, simulated robot)."""
import time

from roomcleaner.cdpr.service import Service, create_app
from roomcleaner.cdpr.sim.harness import SimRobot

from .simkit import fast_cfg


class Client:
    """Test client that sends the session token like the page does."""

    def __init__(self, app, token):
        self.c, self.h = app.test_client(), {"X-Token": token}

    def get(self, path):
        return self.c.get(path, headers=self.h)

    def post(self, path, json):
        return self.c.post(path, json=json, headers=self.h)


def make(tmp_path, **cfg_over):
    r = SimRobot(fast_cfg(**cfg_over), seed=11, data_dir=tmp_path)
    svc = Service(r.ctx, data_dir=tmp_path)
    app = create_app(svc)
    return r, svc, Client(app, svc.token), app


def wait_idle(svc, timeout=120):
    t = time.time()
    while svc.busy and time.time() - t < timeout:
        time.sleep(0.05)


def test_api_requires_token_and_json(tmp_path):
    r, svc, c, app = make(tmp_path)
    raw = app.test_client()
    assert raw.get("/").status_code == 200                      # the page itself is public
    assert raw.get("/api/status").status_code == 401
    assert raw.post("/api/command", json={"cmd": "start", "checklist": True}).status_code == 401
    assert raw.post("/api/command", data='{"cmd":"pause"}', content_type="text/plain",
                    headers={"X-Token": svc.token}).status_code == 415   # cross-site form posts can't do this


def test_page_status_checks_and_room(tmp_path):
    r, svc, c, app = make(tmp_path)
    s = c.get("/api/status").get_json()
    assert s["state"] == "DISARMED" and len(s["checklist"]) >= 4
    assert c.get("/api/checks").get_json()["calibration"] == []
    bad = c.post("/api/room", json={"width_m": 0.2, "depth_m": 3, "height_m": 3})
    assert bad.status_code == 400
    ok = c.post("/api/room", json={"width_m": 3.4, "depth_m": 2.8, "height_m": 2.75,
                                   "anchors": {"A": [0.05, 0.05, 2.6]}}).get_json()
    assert ok["ok"] and ok["anchors"][0] == [0.05, 0.05, 2.6]


def test_start_requires_checklist_and_refuses_illegal_commands(tmp_path):
    r, svc, c, app = make(tmp_path, **{"startup.max_marker_wait_s": 2.0})
    assert c.post("/api/command", json={"cmd": "start"}).status_code == 409
    assert c.post("/api/command", json={"cmd": "recover"}).status_code == 409
    assert c.post("/api/command", json={"cmd": "bogus"}).status_code == 409
    assert c.post("/api/command", json={"cmd": "task"}).status_code == 409   # not READY
    r.simcam.covered = True                         # marker hidden: startup must pause, not guess
    assert c.post("/api/command", json={"cmd": "start", "checklist": True}).get_json()["ok"]
    wait_idle(svc)
    s = c.get("/api/status").get_json()
    assert s["state"] == "PAUSED" and any("marker" in x for x in s["reasons"])
    assert c.post("/api/command", json={"cmd": "disarm", "confirm": "yes"}).status_code == 409


def test_idle_host_loop_keeps_stations_alive(tmp_path):
    """Review C1: with nothing commanded, stations must not lease-fault."""
    r, svc, c, app = make(tmp_path)
    co = r.co
    co.wait(300000)
    co.configure()
    co.wait_synced(3.0)
    co.arm()
    for _ in range(150):                          # 3 s of idle host time (lease 0.3 s)
        svc.idle_tick()
    assert all(co.links[s].tel["st"] == 1 and co.links[s].tel["flt"] == 0 for s in "ABCD")
    r.rt.wait(1e6)                                # host stalls (no pumping) for 1 s ...
    co.pump()
    assert all(co.links[s].tel["flt"] == 4 for s in "ABCD")    # ... and every station holds itself (LEASE)
