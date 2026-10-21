"""Independent review of the phone app (verification/phone_app_review.md): regression tests that PASS while a reviewed defect is
present.

Each test pins the CURRENT behaviour of one confirmed defect (finding id in the test name) so that the fix is a deliberate act:
when a defect is fixed its test fails, and the assertion message says what the corrected behaviour must be. Flip the assertion
(or delete the test) in the same change as the fix. Nothing here changes production code.
"""
import http.client
import io
import logging
import re
import socket
import threading
import time
from pathlib import Path

import pytest
from werkzeug.serving import make_server

from roomcleaner.cdpr import service as service_mod
from roomcleaner.cdpr.chat import Chat, parse
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


# ---------------------------------------------------------------------------------------------- F1 shared token
def test_f1_a_second_phone_with_the_same_token_confirms_the_first_phones_question(tmp_path):
    """There is ONE session token, so the chat's per-token pending question is shared by every phone and tab. Phone B's "yes"
    runs phone A's "lower". Fixed when the pending question is bound to a per-client id or nonce (B's "yes" then does nothing)."""
    r, svc, c, app = make(tmp_path)
    svc.sup._set("PAUSED", "review")
    phone_a, phone_b = Client(app, svc.token), Client(app, svc.token)
    a = phone_a.post("/api/say", json={"text": "lower the claw"}).get_json()
    assert a["pending_confirm"]["action"] == "lower"
    b = phone_b.post("/api/say", json={"text": "yes"}).get_json()
    assert b["command_run"] == "lower", "DEFECT F1 fixed? phone B can no longer confirm phone A's question: flip this test"
    t0 = time.time()
    while svc.busy and time.time() - t0 < 60:
        time.sleep(0.05)


# ---------------------------------------------------------------------------------------------- F2 pause reply
@pytest.mark.parametrize("state", ["DISARMED", "RECOVERY_REQUIRED", "FAULT"])
def test_f2_pause_reply_claims_torque_on_whatever_the_stations_report(tmp_path, state):
    """The pause reply is a fixed string: "holding position with torque on" even when the supervisor is DISARMED (nothing is
    holding) or the claw may hang with no station telemetry at all. Fixed when the text is built from the stations' reported
    states (and says "NOT holding" for an OFF / unknown / faulted station)."""
    r, svc, c, app = make(tmp_path)
    svc.sup._set(state, "review")
    stations = c.get("/api/status").get_json()["stations"]
    assert all(s["state"] is None for s in stations.values())          # no station has reported anything
    out = say(c, "pause")
    assert "holding position with torque on" in out["reply"], "DEFECT F2 fixed? the reply now depends on the station telemetry: flip this test"


# ---------------------------------------------------------------------------------------------- F3 hardware spin
def test_f3_host_loop_spins_without_sleeping_while_a_command_owns_the_robot_in_hardware_mode(tmp_path):
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
    assert calls[0] > 20000, f"DEFECT F3 fixed? only {calls[0]} idle_tick calls in ~0.5 s with the lock held: flip this test"
    assert per_sleep_ms > 2.0, f"1 ms sleep took {per_sleep_ms:.2f} ms with the spinner (expected ~6 ms; ~1.1 without it)"


# ---------------------------------------------------------------------------------------------- F4 / F5 stream slots
def test_f4_head_request_on_the_stream_leaks_slots_until_restart(tmp_path):
    """The slot is taken in the view and only released by the generator's finally. A HEAD request (valid header token) never
    starts the generator, so close() skips the finally: four HEADs lock the camera stream out until the service restarts.
    Fixed when the slot is released on response close (call_on_close) or HEAD never takes one."""
    r, svc = _bare_service(tmp_path)
    srv = _serve(svc)
    try:
        for _ in range(MAX_STREAMS):
            conn = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=5)
            conn.request("HEAD", "/api/stream.mjpg", headers={"X-Token": svc.token})
            resp = conn.getresponse()
            resp.read()
            conn.close()
        time.sleep(0.5)
        assert svc._streams == MAX_STREAMS, "DEFECT F4 fixed? HEAD no longer leaks a stream slot: flip this test"
        conn = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=5)
        conn.request("GET", "/api/stream.mjpg", headers={"X-Token": svc.token})
        assert conn.getresponse().status == 429
    finally:
        _stop(srv, svc)


def test_f5_aborted_streams_keep_their_slots_while_the_claw_has_no_frame(tmp_path):
    """With no cached frame the stream generator yields nothing, so the server never notices the client has gone: four aborted
    attempts (four visits to the Camera tab during a camera outage) hold all slots until a frame finally arrives. Fixed when the
    route answers 503 / sends a keep-alive part while there is no frame."""
    r, svc = _bare_service(tmp_path)                                    # no frame source: latest_frame() is None
    srv = _serve(svc)
    try:
        for _ in range(MAX_STREAMS):
            s = socket.create_connection(("127.0.0.1", srv.server_port), timeout=5)
            s.sendall(f"GET /api/stream.mjpg?token={svc.token} HTTP/1.1\r\nHost: x\r\n\r\n".encode())
            time.sleep(0.2)
            s.close()
        time.sleep(1.5)
        assert svc._streams == MAX_STREAMS, "DEFECT F5 fixed? aborted no-frame streams now release their slots: flip this test"
    finally:
        _stop(srv, svc)


# ---------------------------------------------------------------------------------------------- F6 token in the log
def test_f6_the_session_token_is_written_to_the_access_log(tmp_path):
    """Werkzeug logs the full request line: the page load (/?token=...) and every stream open (/api/stream.mjpg?token=...)
    put the session token into the console / log file. Fixed when those lines are redacted (or the stream uses a short-lived
    ticket and the page strips the token from its URL)."""
    r, svc = _bare_service(tmp_path)
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    lg = logging.getLogger("werkzeug")
    old_level = lg.level
    lg.setLevel(logging.INFO)
    lg.addHandler(handler)
    srv = _serve(svc)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=5)
        conn.request("GET", f"/?token={svc.token}")
        conn.getresponse().read()
        conn.close()
        time.sleep(0.3)
    finally:
        _stop(srv, svc)
        lg.removeHandler(handler)
        lg.setLevel(old_level)
    assert svc.token in buf.getvalue(), "DEFECT F6 fixed? the token no longer reaches the access log: flip this test"


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
                                       ("/api/room", {"width_m": 3, "depth_m": 3, "height_m": 3, "anchors": [1]}),
                                       ("/api/room", {"width_m": 3, "depth_m": 3, "height_m": 3, "anchors": {"Z": [0, 0, 0]}})])
def test_f10_non_object_or_malformed_json_gives_a_500_not_a_400(tmp_path, path, body):
    """Fixed when each of these answers 400 with a JSON error."""
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
