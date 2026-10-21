"""Phone app (docs/PHONE_APP_SPEC.md): token guard, chat intents and confirmation, events, camera cache, start-from-chat,
keep-alive while streaming. Flask test client over the ``--sim`` robot, plus pure unit tests of chat.py and the claw
frame cache (against a fake claw HTTP server)."""
import json
import re
import sys
import threading
import time
import types
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import cv2
import numpy as np
import pytest

from roomcleaner.cdpr import service as service_mod
from roomcleaner.cdpr.chat import CONFIRM_TTL_S, Chat, EventLog, Refused, parse
from roomcleaner.cdpr.claw_link import CachedFrame, DetectorFrameSource, HttpClawClient, ThreadedFrameSource
from roomcleaner.cdpr.service import CHECKLIST, STATIC, Service, SimFrameSource, create_app
from roomcleaner.cdpr.sim.harness import SimRobot
from roomcleaner.cdpr.vision.marker import MarkerObservation

from .simkit import fast_cfg
from .test_service import Client, wait_idle


def make(tmp_path, frames=False, **cfg_over):
    r = SimRobot(fast_cfg(**cfg_over), seed=11, data_dir=tmp_path)
    src = None
    if frames:
        src = SimFrameSource(r)
        src.render_once()
    svc = Service(r.ctx, data_dir=tmp_path, frame_source=src)
    svc.poll_claw()
    app = create_app(svc)
    return r, svc, Client(app, svc.token), app


def say(c, text, checklist=None):
    body = {"text": text}
    if checklist is not None:
        body["checklist"] = checklist
    res = c.post("/api/say", json=body)
    assert res.status_code == 200, res.get_json()
    return res.get_json()


# ================================================================================================= token guard
API_GETS = ["/api/status", "/api/checks", "/api/calibration", "/api/events", "/api/events?since=3", "/api/frame.jpg",
            "/api/stream.mjpg"]
API_POSTS = ["/api/room", "/api/command", "/api/say"]


def test_token_required_on_every_api_route_and_on_the_stream(tmp_path):
    r, svc, c, app = make(tmp_path, frames=True)
    raw = app.test_client()
    for path in API_GETS:
        assert raw.get(path).status_code == 401, path
        assert raw.get(path, headers={"X-Token": "wrong"}).status_code == 401, path
    for path in API_POSTS:
        assert raw.post(path, json={"text": "status", "cmd": "pause"}).status_code == 401, path
    # the token in the URL is accepted by the stream ONLY
    for path in ("/api/status", "/api/events", "/api/frame.jpg", "/api/checks", "/api/calibration"):
        assert raw.get(f"{path}{'&' if '?' in path else '?'}token={svc.token}").status_code == 401, path
    assert raw.post(f"/api/say?token={svc.token}", json={"text": "status"}).status_code == 401
    assert raw.get("/api/stream.mjpg?token=wrong").status_code == 401
    assert raw.get("/api/stream.mjpg?token=").status_code == 401
    assert raw.get("/api/stream.mjpg?token=" + "é" * 5).status_code == 401      # non-ASCII must not crash the guard
    ok = raw.get(f"/api/stream.mjpg?token={svc.token}", buffered=False)
    assert ok.status_code == 200 and ok.mimetype == "multipart/x-mixed-replace"
    ok.close()
    # JSON is still required on POSTs
    assert raw.post("/api/say", data='{"text":"pause"}', content_type="text/plain",
                    headers={"X-Token": svc.token}).status_code == 415


def test_static_pages_are_public_and_self_contained(tmp_path):
    r, svc, c, app = make(tmp_path)
    raw = app.test_client()
    page = raw.get("/")
    assert page.status_code == 200 and b"RoomCleaner" in page.data and b'id="pause"' in page.data
    assert b"Emergency stop = the switched power strip. It drops the claw: nobody under the robot." in page.data
    for tab in (b'data-tab="home"', b'data-tab="camera"', b'data-tab="setup"', b'data-tab="chat"'):
        assert tab in page.data
    for path, mime in (("/app.js", "javascript"), ("/app.css", "text/css"), ("/icon.png", "image/png"),
                       ("/icon-192.png", "image/png"), ("/manifest.webmanifest", "manifest+json")):
        resp = raw.get(path)
        assert resp.status_code == 200 and mime in resp.mimetype, path
    m = json.loads(raw.get("/manifest.webmanifest").data)
    assert m["display"] == "standalone" and m["start_url"] == "/" and {i["sizes"] for i in m["icons"]} == {"192x192", "512x512"}
    from PIL import Image
    assert Image.open(STATIC / "icon.png").size == (512, 512) and Image.open(STATIC / "icon-192.png").size == (192, 192)
    # no external CDN, font or script: it must work on a LAN with no internet
    for name in ("index.html", "app.js", "app.css", "manifest.webmanifest"):
        txt = (STATIC / name).read_text()
        assert not re.search(r"""(?:src|href)\s*=\s*["']\s*(?:https?:)?//""", txt), name
        assert not re.search(r"url\(\s*[\"']?\s*(?:https?:)?//", txt), name
        assert "@import" not in txt and "fonts.googleapis" not in txt, name
    # the token travels as a header; the URL form exists only for the stream
    js = (STATIC / "app.js").read_text()
    assert re.findall(r"/api/[a-z.]+\?token=", js) == ["/api/stream.mjpg?token="] and "X-Token" in js and "sessionStorage" in js


def test_v1_page_is_kept_at_v1(tmp_path):
    r, svc, c, app = make(tmp_path)
    raw = app.test_client()
    v1 = raw.get("/v1")
    assert v1.status_code == 200 and b"RoomCleaner setup" in v1.data and b'id="disarm"' in v1.data
    assert (STATIC / "setup_v1.html").read_bytes() == v1.data
    assert not (STATIC / "setup.html").exists()
    assert raw.get("/").data != v1.data


# ================================================================================================= status / checklist
def test_checklist_wording_follows_d31_and_status_is_extended(tmp_path):
    r, svc, c, app = make(tmp_path, frames=True)
    s = c.get("/api/status").get_json()
    assert s["checklist"] == CHECKLIST and len(CHECKLIST) == 5
    assert "Claw battery charged per the charging rule (switch off, attended, 8.4 V charger at ≤ 1 A)" in CHECKLIST
    assert not any("balance charger" in x for x in CHECKLIST)
    assert CHECKLIST[0].startswith("Room cleared") and "Switched power strip" in CHECKLIST[1]
    assert len(CHECKLIST[2:4]) == 2 and "four cables" in CHECKLIST[3]
    # every pre-existing key is still there ...
    for k in ("state", "detail", "level", "claw_supported", "recovery_required", "stations", "reasons", "events", "busy",
              "error", "checklist", "room_m", "profile", "trust"):
        assert k in s, k
    # ... and the per-station / claw / camera telemetry is added
    for sid in "ABCD":
        st = s["stations"][sid]
        assert {"valid", "bead_verified", "state", "fault", "online", "tel_age_s", "boot", "encoder_valid"} <= set(st)
    claw = s["claw"]
    assert claw["online"] is True and claw["battery_v"] == pytest.approx(7.8) and claw["battery_low"] is False
    assert claw["grip_closed"] is False and claw["camera_ok"] is True
    cam = s["camera"]
    assert cam["source"] == "sim" and cam["available"] and cam["age_s"] >= 0 and "marker" in cam["detection"]["text"]
    assert s["state_text"] and set(s["anchors_m"]) == set("ABCD") and "start" in s["allowed"] and "pause" not in s["allowed"]
    json.dumps(s)                                                  # serialisable as is


def test_claw_battery_low_flag_and_offline(tmp_path):
    r, svc, c, app = make(tmp_path)
    r.claw.battery_v = 6.9
    svc.poll_claw()
    s = c.get("/api/status").get_json()["claw"]
    assert s["battery_low"] is True and s["battery_min_v"] == svc.ctx.cfg.startup.battery_min_v
    assert "LOW" in say(c, "battery")["reply"] and "charging rule" in say(c, "battery")["reply"]
    r.claw.online = False
    svc.poll_claw()
    assert c.get("/api/status").get_json()["claw"]["online"] is False
    assert "not reporting" in say(c, "battery")["reply"]


# ================================================================================================= events
def test_events_are_ordered_and_incremental(tmp_path):
    r, svc, c, app = make(tmp_path)
    first = c.get("/api/events?since=0").get_json()
    evs = first["events"]
    assert evs and evs[0]["kind"] == "state" and "DISARMED" in evs[0]["text"]
    ids = [e["id"] for e in evs]
    assert ids == sorted(ids) and len(set(ids)) == len(ids) and first["last_id"] == ids[-1]
    assert all({"id", "t", "kind", "text"} <= set(e) for e in evs)
    assert c.get(f"/api/events?since={first['last_id']}").get_json()["events"] == []
    c.post("/api/command", json={"cmd": "pause"})                       # supervisor event
    assert c.post("/api/command", json={"cmd": "recover"}).status_code == 409    # refusal event
    svc.sup._set("PAUSED", "test")                                      # state-change event with its hint
    second = c.get(f"/api/events?since={first['last_id']}").get_json()
    kinds = [e["kind"] for e in second["events"]]
    assert kinds[:3] == ["pause", "refused", "state"], kinds
    assert all(e["id"] > first["last_id"] for e in second["events"])
    assert [e["id"] for e in second["events"]] == sorted(e["id"] for e in second["events"])
    assert "Say 'resume'" in second["events"][-1]["text"]
    # a client that is ahead of the server (service restarted) gets everything again; junk is a 400
    assert len(c.get("/api/events?since=99999").get_json()["events"]) == len(first["events"]) + len(second["events"])
    assert c.get("/api/events?since=abc").status_code == 400
    # the full log equals the two reads put together
    allv = c.get("/api/events").get_json()["events"]
    assert [e["id"] for e in allv] == ids + [e["id"] for e in second["events"]]


def test_event_log_unit_bounded_and_thread_safe():
    log = EventLog(maxlen=50)
    ts = [threading.Thread(target=lambda: [log.add("k", "x") for _ in range(100)]) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    evs, last = log.since(0)
    assert last == 400 and len(evs) == 50 and [e["id"] for e in evs] == list(range(351, 401))


def test_startup_steps_and_command_results_reach_the_event_log(tmp_path):
    r, svc, c, app = make(tmp_path, **{"startup.max_marker_wait_s": 2.0})
    r.simcam.covered = True                                  # marker hidden: the startup pauses at once
    assert c.post("/api/command", json={"cmd": "start", "checklist": True}).get_json()["ok"]
    wait_idle(svc)
    text = [e["text"] for e in c.get("/api/events").get_json()["events"]]
    assert any("Command 'start' started" in t for t in text)
    assert any(t.startswith("STARTUP") for t in text) and any(t.startswith("PAUSED") for t in text)
    assert any("marker" in t for t in text)                  # the reason, as its own event
    assert any("'start' finished" in t for t in text)
    assert [t.split(".")[0].split(":")[0] for t in text].index("STARTUP") < [t.split(":")[0] for t in text].index("PAUSED")


# ================================================================================================= camera
def test_startup_steps_become_events_once(tmp_path):
    r, svc, c, app = make(tmp_path)
    svc.sup._set("STARTUP", "operator start")
    for step in ("SELF_CHECK", "SLACK_TAKEUP", "SLACK_TAKEUP", "INITIAL_LIFT"):
        svc.sup.detail = step
        c.get("/api/events")                                       # every read syncs; the same step is logged once
    text = [e["text"] for e in c.get("/api/events").get_json()["events"]]
    assert [t for t in text if t.startswith("Startup step")] == [
        "Startup step: self check", "Startup step: slack takeup", "Startup step: initial lift"]


def test_frame_jpg_is_a_jpeg_in_sim_and_503_before_the_first_frame(tmp_path):
    r, svc, c, app = make(tmp_path)
    assert c.get("/api/frame.jpg").status_code == 503
    r, svc, c, app = make(tmp_path, frames=True)
    resp = c.get("/api/frame.jpg")
    assert resp.status_code == 200 and resp.mimetype == "image/jpeg"
    assert resp.data[:3] == b"\xff\xd8\xff" and resp.data[-2:] == b"\xff\xd9"
    assert float(resp.headers["X-Frame-Age-S"]) >= 0 and resp.headers["X-Frame-Id"] == "1"
    img = cv2.imdecode(np.frombuffer(resp.data, np.uint8), cv2.IMREAD_COLOR)
    assert img.shape == (600, 800, 3) and img.std() > 1.0           # a real picture (floor texture and fingers), not blank


def test_sim_frame_source_never_perturbs_the_simulation(tmp_path):
    """The camera tab reads the world only: it must not advance the plant's noise stream (simcam.observe does)."""
    r, svc, c, app = make(tmp_path, frames=True)
    n0, rng0 = r.simcam.frame, r.simcam.rng.bit_generator.state
    for _ in range(3):
        r.simcam.covered = False
        svc.frame_src.render_once()
        svc.frame_src.detection()
    assert r.simcam.frame == n0 and r.simcam.rng.bit_generator.state == rng0
    r.simcam.covered = True
    assert svc.frame_src.detection()["ok"] is False and "covered" in svc.frame_src.detection()["text"]


def test_stream_serves_multipart_jpegs_at_about_5_fps_from_the_cache(tmp_path):
    r, svc, c, app = make(tmp_path, frames=True)
    svc.frame_src.start()                                          # the sim frame thread (what --sim runs)
    try:
        resp = app.test_client().get("/api/stream.mjpg", headers={"X-Token": svc.token}, buffered=False)
        assert resp.status_code == 200 and "boundary=frame" in resp.headers["Content-Type"]
        assert resp.headers["Cache-Control"] == "no-store"
        t0, parts, it = time.time(), [], iter(resp.response)
        while time.time() - t0 < 1.6 and len(parts) < 12:
            parts.append(next(it))
        resp.close()
    finally:
        svc.frame_src.stop()
    assert all(p.startswith(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ") for p in parts)
    assert all(b"\xff\xd8\xff" in p for p in parts)
    rate = len(parts) / (time.time() - t0)
    assert 1.5 <= rate <= 6.5, rate                                # ~5 fps (0.2 s pace), not a flood
    assert svc._streams == 0                                       # the slot was released when the client went away


def test_stream_slots_are_limited(tmp_path):
    r, svc, c, app = make(tmp_path, frames=True)
    cli = app.test_client()
    open_ = [cli.get("/api/stream.mjpg", headers={"X-Token": svc.token}, buffered=False) for _ in range(service_mod.MAX_STREAMS)]
    for resp in open_:
        next(iter(resp.response))                                  # the generator runs (and holds its slot) once read
    over = cli.get("/api/stream.mjpg", headers={"X-Token": svc.token})
    assert over.status_code == 429
    for resp in open_:
        resp.close()
    assert svc._streams == 0


class CountingClaw(BaseHTTPRequestHandler):
    hits = {"frame": 0, "status": 0}

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/status":
            CountingClaw.hits["status"] += 1
            body = json.dumps({"online": True, "t_us": 5_000_000, "battery_v": 7.9, "grip_closed": False}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        else:
            CountingClaw.hits["frame"] += 1
            img = np.random.default_rng(1).integers(0, 255, (60, 80), np.uint8)
            body = cv2.imencode(".jpg", img)[1].tobytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("X-Capture-Us", "4990000")
            self.send_header("X-Frame-Id", "42")
            self.send_header("X-Camera-Mode", "SVGA-800x600-q10")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def fake_claw():
    srv = HTTPServer(("127.0.0.1", 0), CountingClaw)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    CountingClaw.hits.update(frame=0, status=0)
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


class NoMarker:
    def detect(self, img, **kw):
        return MarkerObservation(False, "marker not found", frame_id=kw.get("frame_id"), capture_us=kw.get("capture_us"))


def test_claw_frame_thread_caches_the_jpeg_and_routes_never_fetch_from_the_claw(fake_claw, tmp_path):
    client = HttpClawClient(fake_claw, now_us=lambda: 1e9)
    inner = DetectorFrameSource(client, NoMarker(), camera_mode="SVGA-800x600-q10", T_B_C=np.eye(4))
    assert inner.latest_frame() is None
    obs = inner.observe(None)                                      # what the frame thread does, once
    assert not obs.ok and obs.reason == "marker not found"          # vision result unchanged
    f = inner.latest_frame()
    assert isinstance(f, CachedFrame) and f.jpeg[:3] == b"\xff\xd8\xff" and f.frame_id == 42 and f.mode == "SVGA-800x600-q10"
    assert f.capture_us == pytest.approx(1e9 - 10_000, abs=1.0) and f.lag_s == pytest.approx(0.01, abs=1e-3)
    assert 0 <= f.age_s() < 5 and CountingClaw.hits["frame"] == 1
    # the service routes read that cache only
    r = SimRobot(fast_cfg(), seed=11, data_dir=tmp_path)
    svc = Service(r.ctx, data_dir=tmp_path, frame_source=inner)
    c = Client(create_app(svc), svc.token)
    for _ in range(5):
        resp = c.get("/api/frame.jpg")
        assert resp.status_code == 200 and resp.data == f.jpeg and resp.headers["X-Frame-Id"] == "42"
        c.get("/api/status")
    stream = create_app(svc).test_client().get("/api/stream.mjpg", headers={"X-Token": svc.token}, buffered=False)
    assert f.jpeg in next(iter(stream.response))
    stream.close()
    assert CountingClaw.hits["frame"] == 1                         # not one extra GET /frame
    assert c.get("/api/status").get_json()["camera"]["source"] == "claw"


def test_threaded_frame_source_exposes_the_inner_cache_and_the_detection_status(fake_claw, tmp_path):
    client = HttpClawClient(fake_claw, now_us=lambda: 1e9)
    inner = DetectorFrameSource(client, NoMarker(), camera_mode="SVGA-800x600-q10", T_B_C=np.eye(4))
    thr = ThreadedFrameSource(inner, period_s=0.02)
    try:
        t0 = time.time()
        while thr.latest_frame() is None and time.time() - t0 < 5:
            time.sleep(0.02)
        assert thr.latest_frame() is not None and thr.latest_frame().frame_id == 42
        r = SimRobot(fast_cfg(), seed=11, data_dir=tmp_path)
        r.ctx.vision.src = thr                                     # as in build_hardware_context
        svc = Service(r.ctx, data_dir=tmp_path)                    # finds the frame thread by itself
        assert svc.frame_src is thr
        cam = Client(create_app(svc), svc.token).get("/api/status").get_json()["camera"]
        assert cam["source"] == "claw" and cam["available"] and cam["detection"] == {"ok": False, "n_tags": 0, "text": "marker not found"}
    finally:
        thr.stop()


# ================================================================================================= say: simple intents
def test_say_help_status_battery_why_unknown(tmp_path):
    r, svc, c, app = make(tmp_path)
    h = say(c, "help")
    for word in ("status", "pause", "resume", "start", "acknowledge", "recover", "lower", "open grip", "close grip", "30 s"):
        assert word in h["reply"], word
    assert "Emergency stop = the switched power strip" in h["reply"] and h["pending_confirm"] is None and h["command_run"] is None
    s = say(c, "What's the status?")
    assert "State DISARMED" in s["reply"] and "Stations: A offline" in s["reply"] and "7.80 V" in s["reply"]   # not brought up yet
    assert "grip open" in s["reply"] and "camera unknown" in s["reply"]                                      # no frame source here
    r.co.wait(300000)
    r.co.configure()
    r.co.wait_synced(3.0)
    r.co.arm()
    assert "Stations: A ok, B ok, C ok, D ok." in say(c, "status")["reply"]
    assert "7.80 V" in say(c, "battery")["reply"] and "OK for lifting" in say(c, "how is the battery")["reply"]
    why = say(c, "why")["reply"]
    assert "State DISARMED" in why and "Trust NONE" in why
    unk = say(c, "make me a sandwich")
    assert "didn't understand" in unk["reply"] and "make me a sandwich" in unk["reply"] and "I understand" in unk["reply"]
    assert unk["pending_confirm"] is None and unk["command_run"] is None and unk["chips"]
    assert say(c, "?")["reply"].startswith("I understand")
    assert c.post("/api/say", json={"text": ""}).status_code == 400
    assert c.post("/api/say", json={"nope": 1}).status_code == 400
    assert c.post("/api/say", json={"text": "x" * 501}).status_code == 400


def test_say_pause_runs_at_once_with_no_confirmation_and_says_it_is_not_an_estop(tmp_path):
    r, svc, c, app = make(tmp_path)
    out = say(c, "pause")
    assert out["command_run"] == "pause" and out["pending_confirm"] is None
    assert "holding position" in out["reply"] and "torque" in out["reply"] and "not an emergency stop" in out["reply"]
    assert "Emergency stop = the switched power strip" in out["reply"]
    assert r.co.pause_requested == "operator pause (chat)"          # the supervisor pause path, same as the button
    assert any(e["kind"] == "pause" for e in c.get("/api/events").get_json()["events"])
    for w in ("STOP", "stop!", "hold position", "emergency", "abort"):
        assert say(c, w)["command_run"] == "pause", w
    assert "didn't understand" not in say(c, "why did you stop")["reply"] and say(c, "why did you stop")["command_run"] is None


def test_pause_works_in_every_state_and_clears_a_pending_question(tmp_path):
    r, svc, c, app = make(tmp_path)
    svc.sup._set("PAUSED", "t")
    assert say(c, "resume")["pending_confirm"]["action"] == "resume"
    p = say(c, "pause")
    assert p["command_run"] == "pause" and p["pending_confirm"] is None
    late = say(c, "yes")
    assert late["command_run"] is None and "Nothing is waiting" in late["reply"]
    for st in ("STARTUP", "READY", "TASK", "FAULT", "RECOVERY_REQUIRED", "PARKED"):
        svc.sup._set(st, "t")
        assert say(c, "pause")["command_run"] == "pause", st


def test_disarm_is_not_available_from_chat(tmp_path):
    r, svc, c, app = make(tmp_path)
    for st in ("PARKED", "DISARMED", "FAULT", "PAUSED", "RECOVERY_REQUIRED"):
        svc.sup._set(st, "t")
        for phrase in ("disarm", "Disarm the claw", "power off", "turn off the motors", "release torque", "shut down"):
            out = say(c, phrase, checklist=True)
            assert out["command_run"] is None and out["pending_confirm"] is None, (st, phrase)
            assert "not available from chat" in out["reply"] and "claw_supported" in out["reply"] and out["goto"] == "setup"
            assert say(c, "yes")["command_run"] is None
    assert svc.sup.state == "RECOVERY_REQUIRED" and svc.busy is None
    assert not any("disarm" in e["text"].lower() and e["kind"] == "command" for e in c.get("/api/events").get_json()["events"])


# ================================================================================================= say: confirmation flow
def test_confirmation_flow_runs_only_after_yes(tmp_path):
    r, svc, c, app = make(tmp_path)
    svc.sup._set("PAUSED", "test")
    q = say(c, "resume")
    assert q["command_run"] is None and q["pending_confirm"]["action"] == "resume"
    assert q["pending_confirm"]["expires_in_s"] == 30 and "'yes' within 30 s" in q["reply"] and q["chips"][:2] == ["Yes", "No"]
    assert svc.busy is None and not any("'resume' started" in e["text"] for e in c.get("/api/events").get_json()["events"])
    go = say(c, "yes")                                             # same session token: the question is keyed by it
    assert go["command_run"] == "resume" and go["pending_confirm"] is None and "Resuming" in go["reply"]
    wait_idle(svc)
    s = c.get("/api/status").get_json()
    assert any("stations not ready" in x for x in [s["error"] or ""]), s["error"]   # the supervisor's own refusal is kept
    text = [e["text"] for e in c.get("/api/events").get_json()["events"]]
    assert any("Operator confirmed 'resume' in chat" in t for t in text) and any("Command 'resume' started" in t for t in text)
    assert any("'resume' stopped: stations not ready" in t for t in text)
    assert say(c, "yes")["command_run"] is None                    # one question, one answer


def test_no_cancels_and_any_other_message_drops_the_question(tmp_path):
    r, svc, c, app = make(tmp_path)
    svc.sup._set("PAUSED", "test")
    assert say(c, "resume")["pending_confirm"]
    assert "cancelled" in say(c, "no")["reply"] and say(c, "yes")["command_run"] is None
    assert say(c, "resume")["pending_confirm"]
    say(c, "status")                                               # change of topic ends the question
    assert "Nothing is waiting" in say(c, "yes")["reply"] and svc.busy is None
    assert say(c, "resume")["pending_confirm"] and say(c, "don't")["pending_confirm"] is None
    assert say(c, "yes please")["command_run"] is None


def test_unconfirmed_question_times_out_after_30_seconds(tmp_path):
    r, svc, c, app = make(tmp_path)
    clock = types.SimpleNamespace(t=1000.0)
    svc.chat.clock = lambda: clock.t
    assert CONFIRM_TTL_S == 30.0
    svc.sup._set("PAUSED", "test")
    assert say(c, "resume")["pending_confirm"]
    clock.t += 29.9
    assert svc.chat.pending(svc.token) is not None                 # still valid at 29.9 s
    clock.t += 0.2                                                 # 30.1 s
    assert svc.chat.pending(svc.token) is None
    late = say(c, "yes")
    assert late["command_run"] is None and "timed out" in late["reply"] and "'resume'" in late["reply"]
    assert svc.busy is None and not any("'resume' started" in e["text"] for e in c.get("/api/events").get_json()["events"])
    assert "Nothing is waiting" in say(c, "yes")["reply"]          # the explanation is given once
    # a fresh question after a timeout works again, and "yes" within the window runs it
    assert say(c, "resume")["pending_confirm"]
    clock.t += 29
    assert say(c, "yes")["command_run"] == "resume"
    wait_idle(svc)


def test_yes_rechecks_that_the_command_is_still_allowed(tmp_path):
    r, svc, c, app = make(tmp_path)
    svc.sup._set("PAUSED", "test")
    assert say(c, "resume")["pending_confirm"]
    svc.sup._set("READY", "state changed meanwhile")
    out = say(c, "yes")
    assert out["command_run"] is None and out["reply"].startswith("Not done:") and "PAUSED" in out["reply"]


def test_refusals_explain_why_and_never_ask_for_confirmation(tmp_path):
    r, svc, c, app = make(tmp_path)                                # DISARMED
    for phrase, needle in (("resume", "only available in PAUSED"), ("recover", "RECOVERY_REQUIRED, FAULT"),
                           ("lower", "READY, PAUSED"), ("acknowledge", "only available in FAULT")):
        out = say(c, phrase)
        assert out["pending_confirm"] is None and out["command_run"] is None and needle in out["reply"], phrase
    svc.sup._set("READY", "t")
    assert "only available in DISARMED, PARKED" in say(c, "start", checklist=True)["reply"]
    svc.sup._set("PAUSED", "t")
    svc.busy = "lower"                                             # a command owns the robot: only pause works
    out = say(c, "resume")
    assert "busy with 'lower'" in out["reply"] and out["pending_confirm"] is None
    assert say(c, "pause")["command_run"] == "pause"
    svc.busy = None


# ================================================================================================= start from chat
def test_start_from_chat_needs_the_checklist_which_chat_never_ticks(tmp_path):
    r, svc, c, app = make(tmp_path, **{"startup.max_marker_wait_s": 2.0})
    r.simcam.covered = True                                        # marker hidden: the startup pauses, never lifts
    refused = say(c, "start")                                      # no checklist from the Setup tab
    assert refused["pending_confirm"] is None and refused["command_run"] is None and refused["goto"] == "setup"
    assert "checklist" in refused["reply"] and "can't tick it for you" in refused["reply"] and "Setup" in refused["reply"]
    for bogus in (False, "true", 1, "yes", None):                  # only a literal true counts, as for /api/command
        out = say(c, "please start the calibration", checklist=bogus)
        assert out["pending_confirm"] is None and out["goto"] == "setup", bogus
    assert say(c, "yes", checklist=True)["command_run"] is None    # nothing pending: a lone yes starts nothing
    assert svc.busy is None and svc.sup.state == "DISARMED"
    # with the boxes ticked on the Setup tab it still only asks
    q = say(c, "start", checklist=True)
    assert q["pending_confirm"]["action"] == "start" and q["command_run"] is None and "nobody under the robot" in q["reply"]
    assert svc.sup.state == "DISARMED"
    # ... and the boxes must still be ticked when "yes" arrives
    late = say(c, "yes", checklist=False)
    assert late["command_run"] is None and "checklist" in late["reply"] and late["goto"] == "setup" and svc.sup.state == "DISARMED"
    assert say(c, "start", checklist=True)["pending_confirm"]
    go = say(c, "yes", checklist=True)
    assert go["command_run"] == "start" and "Starting" in go["reply"]
    wait_idle(svc)
    s = c.get("/api/status").get_json()
    assert s["state"] == "PAUSED" and any("marker" in x for x in s["reasons"])   # same outcome as POST /api/command


def test_direct_command_still_needs_the_checklist(tmp_path):
    r, svc, c, app = make(tmp_path)
    assert c.post("/api/command", json={"cmd": "start"}).status_code == 409
    assert c.post("/api/command", json={"cmd": "grip_open"}).status_code == 409       # no grip route on /api/command
    assert c.post("/api/command", json={"cmd": "disarm", "confirm": "yes"}).status_code == 409


# ================================================================================================= grip from chat
def test_grip_only_when_the_claw_is_verified_on_the_floor(tmp_path):
    r, svc, c, app = make(tmp_path)
    for st in ("DISARMED", "READY", "PAUSED", "STARTUP", "TASK", "FAULT", "RECOVERY_REQUIRED"):
        svc.sup._set(st, "t")
        r.ctx.ledger.claw_supported = False
        out = say(c, "close the grip")
        assert out["pending_confirm"] is None and "verified on the floor" in out["reply"] and st in out["reply"], st
    svc.sup._set("DISARMED", "t")
    r.ctx.ledger.claw_supported = True                              # DISARMED with the floor confirmed is fine
    assert say(c, "close grip")["pending_confirm"]["action"] == "grip_close"
    assert say(c, "no")["pending_confirm"] is None
    svc.sup._set("PARKED", "claw on the floor")
    assert say(c, "open the grip")["reply"] == "The grip is already open."
    assert say(c, "grip")["pending_confirm"] is None and "open or close" in say(c, "grip")["reply"]
    q = say(c, "close the claw")
    assert q["pending_confirm"]["action"] == "grip_close" and r.claw.grip_closed is False   # asked, not done
    go = say(c, "yes")
    assert go["command_run"] == "grip_close"
    wait_idle(svc)
    assert r.claw.grip_closed is True and c.get("/api/status").get_json()["claw"]["grip_closed"] is True
    assert say(c, "close grip")["reply"] == "The grip is already closed."
    assert say(c, "release")["pending_confirm"]["action"] == "grip_open"
    assert say(c, "yes")["command_run"] == "grip_open"
    wait_idle(svc)
    assert r.claw.grip_closed is False
    svc.sup._set("READY", "lifted")                                 # in the air: refused even if asked again
    assert "verified on the floor" in say(c, "open grip")["reply"]


def test_grip_offline_claw_is_refused(tmp_path):
    r, svc, c, app = make(tmp_path)
    svc.sup._set("PARKED", "t")
    r.claw.online = False
    svc.poll_claw()
    out = say(c, "close grip")
    assert out["pending_confirm"] is None and "not reporting" in out["reply"]


# ================================================================================================= keep-alive while streaming
def test_host_keepalive_runs_while_the_stream_is_open(tmp_path):
    """No station lease fault during 2 s of streaming: the stream thread never takes the host loop's lock or waits on it."""
    r, svc, c, app = make(tmp_path, frames=True)
    co = r.co
    co.wait(300000)
    co.configure()
    co.wait_synced(3.0)
    co.arm()
    svc.frame_src.start()
    sim_t0 = r.rt.now_us()
    svc.start_background(real_sleep_s=0.01)
    try:
        resp = app.test_client().get(f"/api/stream.mjpg?token={svc.token}", buffered=False)
        t0, parts, it = time.time(), 0, iter(resp.response)
        while time.time() - t0 < 2.0:
            assert b"image/jpeg" in next(it)
            parts += 1
        # status polls while streaming are answered promptly too (they never wait on the claw)
        t1 = time.time()
        for _ in range(5):
            assert c.get("/api/status").status_code == 200
        assert time.time() - t1 < 2.0
        resp.close()
    finally:
        svc.stop_background()
        svc.frame_src.stop()
    assert parts >= 5
    assert (r.rt.now_us() - sim_t0) / 1e6 > 1.0                    # the host loop really ran (simulated time advanced)
    assert all(co.links[s].tel["st"] == 1 and co.links[s].tel["flt"] == 0 for s in "ABCD")   # IDLE, no fault (no LEASE)
    assert svc.sup.state == "DISARMED" and svc.app_error is None
    # control: the check does see a lease fault when the host stops pumping, so the assertion above is not vacuous
    r.rt.wait(1e6)
    co.pump()
    assert all(co.links[s].tel["flt"] == 4 for s in "ABCD")


# ================================================================================================= chat.py unit tests
class FakeHost:
    def __init__(self):
        self.state, self.busy, self.log, self.refuse_run = "PAUSED", None, [], None
        self.claw = {"online": True, "battery_v": 7.8, "battery_low": False, "battery_min_v": 7.0, "grip_closed": False}
        self.blocked = {}

    def snapshot(self):
        return {"state": self.state, "detail": "", "level": "NONE", "busy": self.busy, "error": None, "reasons": [],
                "trust": {"level": "NONE", "reasons": []}, "stations": {"A": {"online": True, "fault": "NONE"}},
                "claw": self.claw, "chips": []}

    def can(self, cmd):
        return self.blocked.get(cmd)

    def run(self, cmd, body):
        if self.refuse_run:
            raise Refused(self.refuse_run)
        self.log.append((cmd, dict(body)))

    def pause(self):
        self.log.append(("pause", {}))


@pytest.mark.parametrize("text,intent", [
    ("pause", "pause"), ("STOP", "pause"), ("hold position", "pause"), ("e-stop", "pause"), ("no stop", "pause"),
    ("yes", "confirm"), ("Yes.", "confirm"), ("confirm", "confirm"), ("yes please", "confirm"), ("do it", "confirm"),
    ("no", "cancel"), ("nope", "cancel"), ("never mind", "cancel"), ("don't lower it", "cancel"), ("cancel", "cancel"),
    ("help", "help"), ("?", "help"), ("what can you do", "help"),
    ("status", "status"), ("what's the status?", "status"), ("is it ready", "status"), ("how are you doing", "status"),
    ("why", "why"), ("why is it paused?", "why"), ("what's wrong", "why"), ("trust level", "why"),
    ("battery", "battery"), ("how is the battery", "battery"), ("what's the voltage", "battery"),
    ("start", "start"), ("please start", "start"), ("can you start the calibration?", "start"), ("restart", "start"),
    ("resume", "resume"), ("continue", "resume"), ("acknowledge", "acknowledge"), ("clear fault", "acknowledge"),
    ("recover", "recover"), ("lower", "lower"), ("lower the claw", "lower"), ("put it down", "lower"),
    ("open grip", "grip_open"), ("release", "grip_open"), ("close the claw", "grip_close"), ("grab", "grip_close"),
    ("grip", "grip_ask"), ("is the grip open?", "status"),
    ("disarm", "disarm"), ("power off", "disarm"), ("release torque", "disarm"),
    ("banana", "unknown"), ("", "unknown"), ("thanks", "unknown"), ("ok", "unknown"),
    ("yes lower it", "lower"), ("yes resume", "resume"),          # a confirm word never carries a different command
])
def test_parse(text, intent):
    assert parse(text) == intent


def test_chat_unit_confirmation_expiry_and_per_token_pending():
    host, clock = FakeHost(), types.SimpleNamespace(t=0.0)
    chat = Chat(host, clock=lambda: clock.t)
    assert chat.handle("lower", key="A")["pending_confirm"]["action"] == "lower"
    assert chat.handle("yes", key="B")["command_run"] is None            # another token cannot confirm A's question
    clock.t = 10
    out = chat.handle("yes", key="A")
    assert out["command_run"] == "lower" and host.log == [("lower", {})]
    assert chat.handle("resume", key="A")["pending_confirm"]
    clock.t = 10 + 30.01
    assert "timed out" in chat.handle("yes", key="A")["reply"] and host.log == [("lower", {})]
    # exactly at the limit is still valid, a hair after is not
    assert chat.handle("resume", key="A")["pending_confirm"]
    clock.t += 30.0
    assert chat.handle("yes", key="A")["command_run"] == "resume"
    # a new motion question replaces the old one: only the latest can be confirmed
    chat.handle("resume", key="A")
    chat.handle("lower", key="A")
    assert chat.handle("yes", key="A")["command_run"] == "lower" and host.log[-1] == ("lower", {})


def test_chat_unit_start_body_grip_and_host_refusal():
    host = FakeHost()
    host.state = "DISARMED"
    chat = Chat(host)
    assert chat.handle("start")["pending_confirm"] is None and host.log == []
    chat.handle("start", checklist=True)
    assert chat.handle("yes", checklist=True)["command_run"] == "start" and host.log == [("start", {"checklist": True})]
    host.refuse_run = "stations not ready"
    chat.handle("start", checklist=True)
    out = chat.handle("yes", checklist=True)
    assert out["command_run"] is None and "Refused: stations not ready" in out["reply"]
    host.refuse_run = None
    host.blocked["lower"] = "'lower' is only available in READY"
    out = chat.handle("lower")
    assert out["pending_confirm"] is None and "only available in READY" in out["reply"]


def test_chat_never_calls_disarm_or_unknown_commands():
    host = FakeHost()
    chat = Chat(host)
    for phrase in ("disarm", "power off", "release torque", "yes", "do it", "confirm", "shut down", "turn off", "motors off"):
        chat.handle(phrase)
    assert host.log == []                                           # nothing ran, not even an unconfirmed command
    for phrase in ("start", "resume", "recover", "lower", "open grip", "close grip", "acknowledge"):
        chat.handle(phrase, checklist=True)
    assert {c for c, _ in host.log} <= {"acknowledge"}              # acknowledge is not a motion: the rest wait for a yes
    assert "disarm" not in {c for c, _ in host.log}


# ================================================================================================= terminal URL / QR
def test_phone_url_with_token_and_optional_qr(monkeypatch):
    monkeypatch.setattr(service_mod, "lan_ip", lambda: "192.168.1.50")
    lines = []
    monkeypatch.setitem(sys.modules, "qrcode", None)                # not installed: an ImportError, the URL still prints
    url = service_mod.print_phone_url("0.0.0.0", 8100, "tok123", out=lines.append)
    assert url == "http://192.168.1.50:8100/?token=tok123" and lines[0] == f"RoomCleaner phone app: {url}"
    assert any("pip install qrcode" in x for x in lines)
    made = {}

    class QR:
        def __init__(self, **kw):
            made["kw"] = kw

        def add_data(self, d):
            made["data"] = d

        def make(self, fit=True):
            made["fit"] = fit

        def print_ascii(self, out=None, invert=False):
            made["printed"] = True
    monkeypatch.setitem(sys.modules, "qrcode", types.SimpleNamespace(QRCode=QR))
    service_mod.print_phone_url("0.0.0.0", 8100, "tok123", out=lines.append)
    assert made["data"] == url and made["printed"]
    lines.clear()
    assert service_mod.print_phone_url("127.0.0.1", 8100, "t", out=lines.append) == "http://127.0.0.1:8100/?token=t"
    assert any("--host 0.0.0.0" in x for x in lines)


def test_cli_has_host_and_port_arguments():
    src = Path(service_mod.__file__).read_text()
    assert '"--host"' in src and '"--port"' in src and "print_phone_url(a.host, a.port, svc.token)" in src
