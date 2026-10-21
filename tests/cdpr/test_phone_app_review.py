"""Independent review of the phone app (verification/phone_app_review.md): regression tests.

Findings F3, F1, F2, F4, F5, F6 and F14 are FIXED: their tests assert the corrected behaviour (they failed on the code before the
fix; see verification/phone_app_fixes_results.md). The tests of the findings that are still open (F7-F11) pin the CURRENT behaviour
so that the fix is a deliberate act: when such a defect is fixed its test fails, and the assertion message says what the corrected
behaviour must be. Flip the assertion (or delete the test) in the same change as the fix.
"""
import http.client
import io
import json
import logging
import os
import re
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest
from werkzeug.serving import make_server

from roomcleaner.cdpr import service as service_mod
from roomcleaner.cdpr.chat import Chat, hold_report, parse
from roomcleaner.cdpr.claw_link import CachedFrame
from roomcleaner.cdpr.service import MAX_STREAMS, STATIC, Service, SimFrameSource, create_app
from roomcleaner.cdpr.sim.harness import SimRobot

from .simkit import fast_cfg
from .test_phone_app import FakeHost, make, say
from .test_service import Client


def _serve(svc):
    srv = make_server("127.0.0.1", 0, create_app(svc), threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _stop(srv, svc):
    svc._stop.set()                       # ends any stream generator still looping (they would live as long as the process)
    srv.shutdown()
    srv.server_close()


def _bare_service(tmp_path, frame_source=None):
    r = SimRobot(fast_cfg(), seed=11, data_dir=tmp_path)
    svc = Service(r.ctx, data_dir=tmp_path, frame_source=frame_source)
    svc.poll_claw()
    return r, svc


class Phone(Client):
    """One browser tab: the shared session token plus its own page-load client id (what app.js sends as X-Client)."""

    def __init__(self, app, token, client_id=None):
        super().__init__(app, token)
        if client_id:
            self.h["X-Client"] = client_id


class Frames:
    """A frame source: ``present=False`` is a claw that has delivered no frame; each call returns a new frame while present."""

    def __init__(self, present=True):
        self.present, self.n = present, 0

    def latest_frame(self):
        if not self.present:
            return None
        self.n += 1
        return CachedFrame(b"\xff\xd8\xff\xd9", 0.0, self.n, "test", time.monotonic(), 0.0)


def _wait(cond, timeout=6.0):
    t0 = time.time()
    while not cond() and time.time() - t0 < timeout:
        time.sleep(0.02)
    return cond()


# ---------------------------------------------------------------------------------------------- F1 shared token
def test_f1_a_second_phone_with_the_same_token_cannot_confirm_the_first_phones_question(tmp_path):
    """FIXED. There is ONE session token, so the pending question is keyed on the page-load client id (X-Client), not on the
    token. Phone B's (or an id-less script's) "yes" finds nothing waiting; phone A's own "yes" still works."""
    r, svc, c, app = make(tmp_path)
    svc.sup._set("PAUSED", "review")
    phone_a, phone_b, script = Phone(app, svc.token, "phone-a-0001"), Phone(app, svc.token, "phone-b-0002"), Phone(app, svc.token)
    a = phone_a.post("/api/say", json={"text": "lower the claw"}).get_json()
    assert a["pending_confirm"]["action"] == "lower"
    for other in (phone_b, script):
        b = other.post("/api/say", json={"text": "yes"}).get_json()
        assert b["command_run"] is None and "Nothing is waiting" in b["reply"]
    assert svc.busy is None and svc.sup.state == "PAUSED"
    assert not any(e["kind"] == "chat" for e in c.get("/api/events").get_json()["events"])      # nothing was run for B
    assert svc.chat.pending("c:phone-a-0001") is not None                                         # A's question survived
    ok = phone_a.post("/api/say", json={"text": "yes"}).get_json()
    assert ok["command_run"] == "lower"
    _wait(lambda: not svc.busy, 60)


def test_f1_a_request_without_a_client_id_cannot_confirm_an_id_carrying_clients_question_and_the_other_way_round(tmp_path):
    r, svc, c, app = make(tmp_path)
    svc.sup._set("PAUSED", "review")
    script, phone = Phone(app, svc.token), Phone(app, svc.token, "phone-a-0001")
    assert script.post("/api/say", json={"text": "lower"}).get_json()["pending_confirm"]["action"] == "lower"
    assert phone.post("/api/say", json={"text": "yes"}).get_json()["command_run"] is None
    assert svc.chat.pending(svc.token) is not None                                                # the id-less question is untouched
    assert script.post("/api/say", json={"text": "no"}).get_json()["reply"].startswith("Okay, cancelled")
    assert svc.busy is None


def test_f1_a_malformed_client_id_is_refused_and_the_page_sends_one_per_load(tmp_path):
    r, svc, c, app = make(tmp_path)
    for bad in ("x", "a" * 65, "has space!"):
        res = Phone(app, svc.token, bad).post("/api/say", json={"text": "status"})
        assert res.status_code == 400 and "X-Client" in res.get_json()["error"], bad
    for bad in ("x", "a" * 65, "has space!", "../../etc"):
        assert service_mod.chat_key(bad, "TOK") is None, bad
    assert service_mod.chat_key("", "TOK") == "TOK" and service_mod.chat_key("0123456789abcdef", "TOK") == "c:0123456789abcdef"
    js = (STATIC / "app.js").read_text()
    assert '"X-Client": CLIENT' in js and re.search(r"const CLIENT = newClientId\(\);", js) and "getRandomValues" in js
    assert "randomUUID" not in js.replace("crypto.randomUUID needs", "")                          # not available on plain http


def test_f1_chat_tables_stay_bounded_when_every_page_load_brings_a_new_id():
    host, clock = FakeHost(), type("C", (), {"t": 0.0})()
    chat = Chat(host, clock=lambda: clock.t)
    for i in range(300):
        chat.handle("lower", key=f"c:{i:08d}")
    clock.t = 31.0
    for i in range(300, 340):                                                                       # the old questions have lapsed
        chat.handle("yes", key=f"c:{i:08d}")
    clock.t = 31.0 + 130.0
    chat.handle("status", key="c:zzzzzzzz")
    assert len(chat._pending) == 0 and len(chat._lapsed) <= 64


# ---------------------------------------------------------------------------------------------- F2 pause reply
@pytest.mark.parametrize("state", ["DISARMED", "RECOVERY_REQUIRED", "FAULT"])
def test_f2_pause_reply_does_not_claim_torque_when_the_stations_report_nothing(tmp_path, state):
    """FIXED. The reply (and the PAUSE toast text, returned by /api/command) is built from the stations' reported states: DISARMED
    says nothing is holding; RECOVERY_REQUIRED / FAULT with no station telemetry say the holding state is unknown, the claw
    may be hanging, stay clear."""
    r, svc, c, app = make(tmp_path)
    svc.sup._set(state, "review")
    stations = c.get("/api/status").get_json()["stations"]
    assert all(s["state"] is None for s in stations.values())          # no station has reported anything
    out = say(c, "pause")
    low = out["reply"].lower()
    assert "holding position with torque on" not in low and "not an emergency stop" in low
    if state == "DISARMED":
        assert "nothing is holding" in low and "disarmed" in low
    else:
        assert "unknown" in low and "may be hanging" in low and "stay clear" in low
    hold = c.post("/api/command", json={"cmd": "pause"}).get_json()["hold"]                          # what the toast shows
    assert hold["kind"] == ("disarmed" if state == "DISARMED" else "unknown")
    assert "holding position with torque on" not in hold["text"].lower()


def test_f2_pause_says_holding_only_when_the_stations_really_report_it(tmp_path):
    r, svc, c, app = make(tmp_path)
    r.co.wait(300000)
    r.co.configure()
    r.co.wait_synced(3.0)
    r.co.arm()
    r.co.wait(300000)                                                   # let the stations report their new state
    svc.sup._set("READY", "review")
    stations = c.get("/api/status").get_json()["stations"]
    assert {s["state"] for s in stations.values()} == {"IDLE"} and all(s["online"] for s in stations.values())
    out = say(c, "pause")
    assert "every station reports IDLE, holding position with torque on" in out["reply"]
    assert c.post("/api/command", json={"cmd": "pause"}).get_json()["hold"]["kind"] == "holding"


def _stn(**states):
    return {k: {"state": v, "online": True, "fault": "NONE"} for k, v in states.items()}


@pytest.mark.parametrize("snap,kind,must,mustnt", [
    ({"state": "READY", "stations": _stn(A="IDLE", B="IDLE", C="IDLE", D="IDLE")}, "holding", ["holding position with torque on"], []),
    ({"state": "PAUSED", "stations": _stn(A="IDLE", B="OFF", C="IDLE", D="IDLE")}, "not_holding", ["NOT holding", "station B OFF"], ["torque on"]),
    ({"state": "STARTUP", "stations": _stn(A="RUN", B="HOLD", C="IDLE", D="IDLE")}, "stopping", ["stations A, B still stopping"], ["torque on"]),
    ({"state": "READY", "stations": {**_stn(A="IDLE", B="IDLE"), "C": {"state": None, "online": True}}}, "unknown",
     ["UNKNOWN", "station C", "stay clear"], ["torque on"]),
    ({"state": "READY", "stations": {**_stn(A="IDLE"), "B": {"state": "IDLE", "online": False}}}, "unknown", ["UNKNOWN", "station B"], ["torque on"]),
    ({"state": "FAULT", "stations": _stn(A="IDLE", B="FAULT")}, "unknown", ["UNKNOWN", "station B reports FAULT"], ["torque on"]),
    ({"state": "RECOVERY_REQUIRED", "stations": {}}, "unknown", ["UNKNOWN", "no station telemetry", "may be hanging"], ["torque on"]),
    ({"state": "DISARMED", "stations": _stn(A="IDLE", B="IDLE")}, "disarmed", ["nothing is holding position", "DISARMED"], ["torque on"]),
])
def test_f2_hold_report_follows_the_station_states(snap, kind, must, mustnt):
    rep = hold_report(snap)
    assert rep["kind"] == kind, rep
    for m in must:
        assert m in rep["text"], (m, rep)
    for m in mustnt:
        assert m not in rep["text"], (m, rep)


def test_f2_the_pause_toast_and_the_event_log_make_no_fixed_claim_of_holding(tmp_path):
    js = (STATIC / "app.js").read_text()
    assert "torque stays on" not in js and "r.data.hold" in js
    r, svc, c, app = make(tmp_path)
    say(c, "pause")
    ev = [e["text"] for e in c.get("/api/events").get_json()["events"] if e["kind"] == "pause"]
    assert ev and not any("holding position" in t for t in ev)


# ---------------------------------------------------------------------------------------------- F3 hardware spin
def test_f3_host_loop_backs_off_while_a_command_owns_the_robot_in_hardware_mode(tmp_path):
    """main() passes real_sleep_s=0.0 for hardware. idle_tick() returns at once when a command holds the lock, so the loop
    thread busy-spins (millions of calls per second) and, through the GIL hand-off, makes every short sleep of the command thread
    (the real runtime pumps in 1 ms sleeps) several times longer. Fixed when the loop sleeps/blocks while the lock is busy."""
    r, svc = _bare_service(tmp_path)
    calls = [0]
    orig = svc.idle_tick

    def counted(dt_s=0.02):
        calls[0] += 1
        return orig(dt_s)
    svc.idle_tick = counted
    assert svc.lock.acquire(blocking=False)                             # a command owns the robot (what _run does)
    try:
        svc.start_background(real_sleep_s=0.0)                          # the hardware setting of main()
        t0 = time.perf_counter()
        for _ in range(100):
            time.sleep(0.001)
        per_sleep_ms = (time.perf_counter() - t0) / 100 * 1e3
        time.sleep(0.3)
    finally:
        svc.stop_background()
        svc.lock.release()
    # F3 FIXED (lead, 2026-10-21): the loop backs off BUSY_BACKOFF_S while the lock is held, so it no longer spins
    # (was > 2.6 million calls/s and ~6 ms per 1 ms sleep).  ~0.4 s at 5 ms per call is ~80 calls.
    assert calls[0] < 1000, f"F3 regressed: {calls[0]} idle_tick calls in ~0.4 s with the lock held (busy-spin)"
    assert per_sleep_ms < 4.0, f"1 ms sleep took {per_sleep_ms:.2f} ms with the lock held (spinner back?)"


# ---------------------------------------------------------------------------------------------- F4 / F5 stream slots
def test_f4_head_request_on_the_stream_does_not_take_a_slot(tmp_path, monkeypatch):
    """FIXED. HEAD (valid header token) is answered without a generator and without a slot, so any number of HEADs leaves the
    camera stream available; a real GET afterwards still streams and frees its slot when the client leaves."""
    monkeypatch.setattr(service_mod, "STREAM_PERIOD_S", 0.05)
    r, svc = _bare_service(tmp_path, Frames())
    srv = _serve(svc)
    try:
        for _ in range(MAX_STREAMS + 2):
            conn = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=5)
            conn.request("HEAD", "/api/stream.mjpg", headers={"X-Token": svc.token})
            resp = conn.getresponse()
            assert resp.status == 200 and "multipart/x-mixed-replace" in resp.getheader("Content-Type")
            assert resp.read() == b""
            conn.close()
        time.sleep(0.3)
        assert svc._streams == 0
        conn = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=5)
        conn.request("GET", "/api/stream.mjpg", headers={"X-Token": svc.token})
        resp = conn.getresponse()
        assert resp.status == 200 and b"--frame" in resp.read(64)
        assert svc._streams == 1
        resp.close()                                                    # the response object keeps the socket open until closed
        conn.close()
        assert _wait(lambda: svc._streams == 0), "the slot of a client that went away was not released"
    finally:
        _stop(srv, svc)


def test_f4_a_response_closed_before_its_generator_ran_still_frees_the_slot(tmp_path):
    """The slot is also released on response close (call_on_close), so a stream the server never iterated (a HEAD answered by the
    WSGI server, a client that vanished before the first chunk) cannot leak one. Driven through the raw WSGI interface: the
    Flask test client always pulls the first chunk, which starts the generator."""
    from werkzeug.test import EnvironBuilder
    r, svc = _bare_service(tmp_path, Frames())
    app = create_app(svc)

    def open_stream():
        started = []
        env = EnvironBuilder("/api/stream.mjpg", headers={"X-Token": svc.token}).get_environ()
        body = app(env, lambda status, headers, exc_info=None: started.append(status))      # not iterated
        return body, started[0]
    held = [open_stream() for _ in range(MAX_STREAMS)]
    assert all(st.startswith("200") for _, st in held) and svc._streams == MAX_STREAMS
    extra, status = open_stream()
    assert status.startswith("429")
    extra.close()
    for body, _ in held:
        body.close()                                                    # the generator never started
    assert svc._streams == 0


def test_f5_aborted_streams_do_not_hold_slots_while_the_claw_has_no_frame(tmp_path):
    """FIXED. With no cached frame the route answers 503 at once (the page falls back to stills), so four aborted attempts hold
    nothing and a fifth is not told 429."""
    r, svc = _bare_service(tmp_path)                                    # no frame source: latest_frame() is None
    srv = _serve(svc)
    try:
        for _ in range(MAX_STREAMS + 1):
            s = socket.create_connection(("127.0.0.1", srv.server_port), timeout=5)
            s.sendall(f"GET /api/stream.mjpg?token={svc.token} HTTP/1.1\r\nHost: x\r\n\r\n".encode())
            first = s.recv(200)
            s.close()
            assert b" 503 " in first.split(b"\r\n")[0], first[:60]
        time.sleep(0.3)
        assert svc._streams == 0
    finally:
        _stop(srv, svc)


def test_f5_a_stream_whose_frames_stop_ends_and_frees_its_slot(tmp_path, monkeypatch):
    """A stream that has had no frame to send for STREAM_NOFRAME_S ends by itself (it sends nothing, so it could never notice a
    client that left)."""
    monkeypatch.setattr(service_mod, "STREAM_PERIOD_S", 0.05)
    monkeypatch.setattr(service_mod, "STREAM_NOFRAME_S", 0.4)
    frames = Frames()
    r, svc = _bare_service(tmp_path, frames)
    srv = _serve(svc)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=5)
        conn.request("GET", "/api/stream.mjpg", headers={"X-Token": svc.token})
        resp = conn.getresponse()
        assert resp.status == 200 and b"--frame" in resp.read(64)
        assert svc._streams == 1
        frames.present = False                                          # the camera dies while the client is still connected
        assert _wait(lambda: svc._streams == 0, 3.0), "the stream kept its slot with no frame to send"
        resp.close()
        conn.close()
    finally:
        _stop(srv, svc)


# ---------------------------------------------------------------------------------------------- F6 token in the log
def test_f6_the_session_token_is_not_written_to_the_access_log(tmp_path):
    """FIXED. Werkzeug logs the full request line; the page load (/?token=...) and every stream open
    (/api/stream.mjpg?token=...) now appear as token=<redacted>. (The service prints the URL with the token once at start.)"""
    r, svc = _bare_service(tmp_path, Frames())
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    lg = logging.getLogger("werkzeug")
    old_level = lg.level
    lg.setLevel(logging.INFO)
    lg.addHandler(handler)
    srv = _serve(svc)
    try:
        for path in (f"/?token={svc.token}", f"/?tab=chat&token={svc.token}", "/?token=WRONGTOKEN12345", f"/api/stream.mjpg?token={svc.token}&_=1"):
            conn = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=5)
            conn.request("GET", path)
            resp = conn.getresponse()
            resp.read(32)
            conn.close()
        time.sleep(0.5)
    finally:
        _stop(srv, svc)
        lg.removeHandler(handler)
        lg.setLevel(old_level)
    logged = buf.getvalue()
    assert logged.count("GET /") >= 4
    assert svc.token not in logged and "WRONGTOKEN12345" not in logged, logged
    assert '"GET /?token=<redacted> HTTP/1.1" 200' in logged and "/api/stream.mjpg?token=<redacted>&_=1 HTTP/1.1" in logged
    assert "/?tab=chat&token=<redacted> HTTP/1.1" in logged


def test_f6_the_redaction_filter_is_installed_once_and_rewrites_message_and_args(tmp_path):
    r, svc, c, app = make(tmp_path)
    create_app(svc)
    create_app(svc)
    lg = logging.getLogger("werkzeug")
    assert sum(isinstance(f, service_mod._RedactToken) for f in lg.filters) == 1
    f = service_mod._RedactToken()
    rec = logging.LogRecord("werkzeug", logging.INFO, "x", 1, '127.0.0.1 - - "GET /?a=1&token=SECRET HTTP/1.1" 200 -', (), None)
    assert f.filter(rec) and "SECRET" not in rec.getMessage() and "token=<redacted> HTTP/1.1" in rec.getMessage()
    rec = logging.LogRecord("werkzeug", logging.INFO, "x", 1, '"%s" %s', ("GET /api/stream.mjpg?token=SECRET&_=2 HTTP/1.1", 200), None)
    assert f.filter(rec) and "SECRET" not in rec.getMessage() and rec.args[1] == 200
    rec = logging.LogRecord("werkzeug", logging.INFO, "x", 1, "no secret here", (), None)
    assert f.filter(rec) and rec.getMessage() == "no secret here"


def test_f6_the_page_removes_the_token_from_the_address_bar():
    js = (STATIC / "app.js").read_text()
    m = re.search(r"function stripTokenFromUrl\(\)\s*\{(.*?)\n\}", js, re.S)
    assert m and "history.replaceState" in m.group(1) and 'searchParams.delete("token")' in m.group(1)
    assert re.search(r'if \(store\.get\("rc_token"\) === t\) stripTokenFromUrl\(\);', js)


# ---------------------------------------------------------------------------------------------- F7 voice
def test_f7_voice_transcripts_are_sent_unfiltered_so_ambient_speech_can_confirm():
    """The mic handler sends whatever the browser's recogniser heard straight to /api/say, and a bare "yes" / "go ahead" /
    "do it" is a valid confirmation. Fixed when voice input can never confirm (only the Yes button or typed text can)."""
    js = (STATIC / "app.js").read_text()
    assert re.search(r"rec\.onresult\s*=\s*ev\s*=>\s*\{[^}]*\bsend\(t\)", js), "DEFECT F7 fixed? voice no longer goes straight to send(): flip"
    for phrase in ("yes", "yeah", "go ahead", "do it", "confirm"):
        assert parse(phrase) == "confirm"


# ---------------------------------------------------------------------------------------------- F8 pause vocabulary
@pytest.mark.parametrize("text", ["why is it moving stop it", "what is it doing, stop", "is it going down? stop!", "what the hell stop",
                                  "stopp", "stooop", "hold", "wait"])
def test_f8_chat_pause_is_missed_for_question_words_typos_and_hold(text):
    """pause is suppressed by a leading question word and needs the exact words; none of these runs the pause. (The PAUSE button
    is the primary control; pause is always safe, so the parser should lean towards it.) Fixed when each of these parses as pause."""
    assert parse(text) != "pause", f"DEFECT F8 fixed? {text!r} now pauses: flip this case"


# ---------------------------------------------------------------------------------------------- F9 checklist ticks
def test_f9_checklist_ticks_have_no_expiry():
    """The client-side ticks stay valid for as long as the state is DISARMED / PARKED: nothing in app.js times them out, so a
    tick made an hour ago still lets chat 'start' through. Fixed when ticks expire (e.g. 2 min) or a timestamp is checked."""
    js = (STATIC / "app.js").read_text()
    m = re.search(r"function checklistTicked\(\)\s*\{(.*?)\n\}", js, re.S)
    assert m and "Date.now" not in m.group(1) and "Date.now" not in re.search(r"function renderSetup.*?\n\}\n", js, re.S).group(0), \
        "DEFECT F9 fixed? the checklist now has an expiry: flip this test"


# ---------------------------------------------------------------------------------------------- F10 JSON hygiene
@pytest.mark.parametrize("path,body", [("/api/command", [1]), ("/api/command", "str"), ("/api/command", {"cmd": [1]}),
                                       ("/api/say", [1]),
                                       ("/api/room", {"width_m": 3, "depth_m": 3, "height_m": 3, "anchors": [1]})])
def test_f10_non_object_or_malformed_json_gives_a_500_not_a_400(tmp_path, path, body):
    """Fixed when each of these answers 400 with a JSON error. (A fifth case, anchors for an unknown station id "Z", gave a
    500 KeyError at 953822d; the uncommitted three-station work in the tree already answers 400 "unknown station", so it is not pinned.)"""
    r, svc, c, app = make(tmp_path)
    app.testing = False
    res = Client(app, svc.token).post(path, json=body)
    assert res.status_code == 500, "DEFECT F10 fixed? the route now rejects it cleanly: flip this case"


def test_f10_room_accepts_nan_dimensions_and_anchors(tmp_path):
    """float('nan') passes the range test (every comparison with NaN is False). Fixed when non-finite values are refused (400)."""
    r, svc, c, app = make(tmp_path)
    ok = c.post("/api/room", json={"width_m": "nan", "depth_m": 3, "height_m": 3})
    assert ok.status_code == 200, "DEFECT F10 fixed? NaN is now refused: flip this test"
    svc.ctx.cfg.room_m[:] = [3.0, 3.0, 3.0]
    ok = c.post("/api/room", json={"width_m": 3, "depth_m": 3, "height_m": 3, "anchors": {"A": ["nan", 0, 0]}})
    assert ok.status_code == 200 and b"NaN" in ok.data
    svc.ctx.cfg.station("A").anchor_room_m[:] = [0.05, 0.05, 2.5]


# ---------------------------------------------------------------------------------------------- F11 acknowledge, documented deviation
def test_f11_acknowledge_runs_without_a_question():
    """Implementer's reported deviation, pinned so it stays a decision: acknowledge (FAULT only) re-arms the stations on the
    first message, with no confirmation. Judged acceptable (parity with the Setup button); flip if a confirmation is added."""
    host = FakeHost()
    host.state = "FAULT"
    chat = Chat(host)
    out = chat.handle("ack")
    assert out["command_run"] == "acknowledge" and out["pending_confirm"] is None and host.log == [("acknowledge", {})]

# ---------------------------------------------------------------------------------------------- F14 connect overlay (real browser)
def test_f14_css_ends_the_connect_overlay_above_the_dock_and_keeps_the_dock_on_top():
    css = (STATIC / "app.css").read_text()
    connect = re.search(r"\n\.connect\s*\{([^}]*)\}", css).group(1)
    dock = re.search(r"\n\.dock\s*\{([^}]*)\}", css).group(1)
    assert re.search(r"inset:\s*0 0 var\(--dock-h", connect), "the overlay must leave room for the PAUSE dock and the tab bar"
    z_connect, z_dock = int(re.search(r"z-index:\s*(\d+)", connect).group(1)), int(re.search(r"z-index:\s*(\d+)", dock).group(1))
    assert "position: relative" in dock and z_dock > z_connect
    assert "layout();" in re.search(r"function showConnect\(note\)\s*\{(.*?)\n\}", (STATIC / "app.js").read_text(), re.S).group(1)


# The browser checks run in Node (the playwright package and the pre-installed Chromium are what this environment has); skipped
# where either is missing. One run serves the F14, F6, F1 and F2 browser tests below.
NODE_CHECK = r"""
const { chromium } = require("playwright");
const [base, token] = process.argv.slice(2);

const geometry = () => {
  const inView = r => r.top >= 0 && r.bottom <= innerHeight + 0.5 && r.left >= 0 && r.right <= innerWidth + 0.5;
  const topAt = el => { const r = el.getBoundingClientRect(); const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!e && (e === el || el.contains(e)); };
  const p = document.getElementById("pause"), s = document.querySelector(".estop"), card = document.querySelector("#connect .card");
  const pr = p.getBoundingClientRect(), sr = s.getBoundingClientRect(), cr = card.getBoundingClientRect();
  return { pauseTop: topAt(p), estopTop: topAt(s), pauseIn: inView(pr), estopIn: inView(sr), cardAbovePause: cr.bottom <= pr.top + 0.5, cardIn: cr.top >= 0,
           noHScroll: document.documentElement.scrollWidth <= innerWidth };
};

(async () => {
  const browser = await chromium.launch();
  const out = { connect: [], url: {}, say: {} };
  for (const [w, h] of [[320, 568], [360, 740], [360, 480], [390, 844], [768, 1024], [1280, 800]]) {
    for (const [name, q] of [["no token", ""], ["wrong token", "?token=WRONG"]]) {
      const ctx = await browser.newContext({ viewport: { width: w, height: h } });
      const page = await ctx.newPage();
      await page.goto(base + "/" + q);
      await page.waitForSelector("#connect:not([hidden])", { timeout: 8000 });
      out.connect.push({ w, h, name, ...(await page.evaluate(geometry)) });
      await ctx.close();
    }
  }
  const ids = [];
  async function phone(q) {
    const ctx = await browser.newContext({ viewport: { width: 360, height: 740 } });
    const page = await ctx.newPage();
    page.on("request", r => { if (r.url().endsWith("/api/say")) ids.push(r.headers()["x-client"]); });
    await page.goto(base + "/" + q);
    await page.waitForFunction(() => document.getElementById("connText").textContent === "online", null, { timeout: 8000 });
    return page;
  }
  const a = await phone("?token=" + token + "&tab=chat");
  out.url.afterLoad = await a.evaluate(() => location.search + "|" + location.hash);
  out.url.connectHidden = await a.evaluate(() => document.getElementById("connect").hidden);
  out.url.chatTab = await a.evaluate(() => document.getElementById("tab-chat").hidden === false);
  await a.reload();
  await a.waitForFunction(() => document.getElementById("connText").textContent === "online", null, { timeout: 8000 });
  out.url.afterReloadConnectHidden = await a.evaluate(() => document.getElementById("connect").hidden);
  const b = await phone("?tab=chat#token=" + token);
  out.url.hashAfterLoad = await b.evaluate(() => location.search + "|" + location.hash);
  await a.fill("#say", "lower the claw"); await a.press("#say", "Enter");
  await a.waitForSelector("#pendingBar:not([hidden])", { timeout: 8000 });
  await b.fill("#say", "yes"); await b.press("#say", "Enter");
  await b.waitForFunction(() => document.querySelectorAll(".msg.robot").length > 0, null, { timeout: 8000 });
  out.say.bReply = await b.evaluate(() => [...document.querySelectorAll(".msg.robot")].pop().firstChild.textContent);
  out.say.aStillPending = await a.evaluate(() => !document.getElementById("pendingBar").hidden);
  await a.click("#no");
  await a.waitForFunction(() => document.getElementById("pendingBar").hidden, null, { timeout: 8000 });
  out.say.ids = ids;
  // PAUSE toast text follows the service (the robot here is DISARMED / PAUSED with no station telemetry)
  await a.click("#pause");
  await a.waitForSelector("#toast:not([hidden])", { timeout: 8000 });
  out.toast = await a.evaluate(() => document.getElementById("toast").textContent);
  await browser.close();
  console.log(JSON.stringify(out));
})().catch(e => { console.error(String(e && e.stack || e)); process.exit(1); });
"""


@pytest.fixture(scope="module")
def browser_run(tmp_path_factory):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    npm_root = subprocess.run([shutil.which("npm") or "npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    env = {**os.environ, "NODE_PATH": os.pathsep.join(x for x in (npm_root, "/opt/node22/lib/node_modules") if x)}
    if subprocess.run([node, "-e", "require('playwright')"], env=env, capture_output=True).returncode:
        pytest.skip("the node 'playwright' package is not installed")
    tmp = tmp_path_factory.mktemp("browser")
    (tmp / "data").mkdir()
    script = tmp / "check.js"
    script.write_text(NODE_CHECK)
    r, svc = _bare_service(tmp / "data", Frames())
    svc.sup._set("PAUSED", "review")                                    # no station has reported anything
    srv = _serve(svc)
    try:
        run = subprocess.run([node, str(script), f"http://127.0.0.1:{srv.server_port}", svc.token], env=env, capture_output=True,
                             text=True, timeout=180)
        if run.returncode != 0 and "Executable doesn't exist" in run.stderr:
            pytest.skip("Chromium is not installed for playwright")
        assert run.returncode == 0, run.stderr[-1500:]
        yield json.loads(run.stdout.strip().splitlines()[-1]), svc
    finally:
        _stop(srv, svc)


def test_f14_connect_overlay_does_not_cover_pause_or_the_emergency_stop_line(browser_run):
    """FIXED. With no token and with a wrong token the \"Connect to the robot\" overlay is shown and PAUSE and the e-stop line
    stay inside the viewport and are the topmost elements at their centres, from 320 px to a desktop width (the card sits above
    them)."""
    out, svc = browser_run
    combos = out["connect"]
    assert {(c["w"], c["name"]) for c in combos} >= {(360, "no token"), (360, "wrong token"), (320, "no token"), (1280, "wrong token")}
    for c in combos:
        assert c["pauseTop"] and c["estopTop"] and c["pauseIn"] and c["estopIn"], c
        assert c["cardAbovePause"] and c["cardIn"] and c["noHScroll"], c


def test_f6_in_a_real_browser_the_token_is_gone_from_the_address_bar_but_the_page_keeps_working(browser_run):
    out, svc = browser_run
    u = out["url"]
    assert u["afterLoad"] == "?tab=chat|" and u["hashAfterLoad"] == "?tab=chat|"      # other parameters stay, the token does not
    assert u["connectHidden"] and u["chatTab"] and u["afterReloadConnectHidden"]      # still connected, also after a reload


def test_f1_in_a_real_browser_the_second_phone_cannot_confirm_the_first_phones_question(browser_run):
    out, svc = browser_run
    ids = out["say"]["ids"]
    assert all(re.fullmatch(r"[0-9a-f]{32}", i) for i in ids) and len(set(ids)) == 2      # one id per page load, 3 messages
    assert out["say"]["bReply"] == "Nothing is waiting for confirmation." and out["say"]["aStillPending"]
    assert svc.busy is None and svc.sup.state == "PAUSED"


def test_f2_in_a_real_browser_the_pause_toast_follows_the_station_telemetry(browser_run):
    out, svc = browser_run
    assert "UNKNOWN" in out["toast"] and "stay clear" in out["toast"] and "torque stays on" not in out["toast"]
    assert out["toast"].endswith("This is not an emergency stop.")
