"""Independent verification of the phone-app fixes F1, F2, F4, F5, F6, F14 (commit 678a704; report:
verification/phone_app_fixes_verification.md). Written by the verifier, not by the implementer: it probes the review's EXPECTED
behaviour, not the implementer's tests.

Tests named ``test_v_*_pin_*`` pin a CURRENT, known weakness (like the F7-F11 pins in test_phone_app_review.py): when it is fixed the
test fails and its message says what the corrected behaviour must be. Flip the assertion in the same change as the fix.
"""
import http.client
import json
import logging
import re
import socket
import threading
import time

import pytest

from roomcleaner.cdpr import service as service_mod
from roomcleaner.cdpr.chat import hold_report
from roomcleaner.cdpr.service import STATIC, create_app

from .test_phone_app import make
from .test_phone_app_review import Frames, Phone, _bare_service, _serve, _stop, _wait
from .test_three_station_review import _real_time_robot

A_ID, B_ID = "aaaaaaaa11111111", "bbbbbbbb22222222"


def _say(phone, text, checklist=None):
    body = {"text": text}
    if checklist is not None:
        body["checklist"] = checklist
    res = phone.post("/api/say", json=body)
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def _tel(svc, sid, st, age_s=0.0, flt=0):
    ln = svc.ctx.co.links[sid]
    ln.tel = {"st": st, "flt": flt, "encv": 1}
    ln.tel_host_t = svc.ctx.co.rt.now_us() - int(age_s * 1e6)


def _no_tel(svc):
    for sid in svc.ctx.cfg.ids:
        svc.ctx.co.links[sid].tel = None


# ------------------------------------------------------------------------------------------------------------------- F1
@pytest.mark.parametrize("asker,confirmer", [("A", "B"), ("B", "A"), ("A", "none"), ("B", "none"), ("none", "A"), ("none", "B")])
def test_v_f1_ids_and_no_id_cannot_confirm_each_others_question(tmp_path, asker, confirmer):
    r, svc, c, app = make(tmp_path)
    svc.sup._set("PAUSED", "verify")
    who = {"A": Phone(app, svc.token, A_ID), "B": Phone(app, svc.token, B_ID), "none": Phone(app, svc.token)}
    ran = []
    svc.run_from_chat = lambda cmd, body: ran.append(cmd)                   # record instead of moving the (simulated) robot
    assert _say(who[asker], "lower the claw")["pending_confirm"]["action"] == "lower"
    for word in ("yes", "go ahead", "do it"):
        j = _say(who[confirmer], word)
        assert j["command_run"] is None and "Nothing is waiting" in j["reply"], (asker, confirmer, word, j["reply"])
    assert ran == []
    assert _say(who[asker], "yes")["command_run"] == "lower" and ran == ["lower"]       # the asker's own yes still works


def test_v_f1_start_question_needs_the_same_client_and_a_ticked_checklist(tmp_path):
    r, svc, c, app = make(tmp_path)                                         # DISARMED: 'start' is legal
    ran = []
    svc.run_from_chat = lambda cmd, body: ran.append((cmd, body))
    a, b = Phone(app, svc.token, A_ID), Phone(app, svc.token, B_ID)
    assert _say(a, "start", checklist=True)["pending_confirm"]["action"] == "start"
    assert "Nothing is waiting" in _say(b, "yes", checklist=True)["reply"] and ran == []
    assert "no longer fully ticked" in _say(a, "yes", checklist=False)["reply"] and ran == []     # its own yes needs the ticks too
    assert svc.chat.pending("c:" + A_ID) is None                                                   # the question was consumed


@pytest.mark.parametrize("cid,ok", [("12345678", True), ("a" * 64, True), ("A_b-C_d-1", True), ("1234567", False), ("a" * 65, False),
                                    ("bad id!!!", False), ("abcédefgh", False), ("aaaa:bbbb1", False), ("c:12345678", False),
                                    ("../../etc/x", False)])
def test_v_f1_client_id_syntax(tmp_path, cid, ok):
    r, svc, c, app = make(tmp_path)
    res = Phone(app, svc.token, cid).post("/api/say", json={"text": "status"})
    assert (res.status_code == 200) is ok, (cid, res.status_code)
    pause = Phone(app, svc.token, cid).post("/api/command", json={"cmd": "pause"})                # HTTP PAUSE never looks at X-Client
    assert pause.status_code == 200 and pause.get_json()["ok"] is True


def test_v_f1_pin_two_requests_without_a_client_id_share_one_bucket(tmp_path):
    """PIN (Low). Callers that send no X-Client (scripts, curl) all use the token-keyed legacy bucket, so one of them can confirm
    another's question. The page always sends an id. Fixed when an id-less request cannot confirm anything (it gets a one-shot
    nonce, or the chat refuses id-less requests): then flip to ``ran == []``."""
    r, svc, c, app = make(tmp_path)
    svc.sup._set("PAUSED", "verify")
    ran = []
    svc.run_from_chat = lambda cmd, body: ran.append(cmd)
    first, second = Phone(app, svc.token), Phone(app, svc.token)
    _say(first, "lower")
    _say(second, "yes")
    assert ran == ["lower"], "WEAKNESS FIXED? an id-less caller can no longer confirm another id-less caller's question: flip this pin"


def test_v_f1_pin_a_chat_stop_from_another_phone_does_not_cancel_a_pending_question(tmp_path):
    """PIN (Low). Before F1 the key was shared, so any phone's chat 'stop' cancelled the question by accident; now only the same
    client's stop does (and the PAUSE button never did). Phone A's 'yes' within 30 s still runs the motion after phone B paused.
    Fixed when a pause from anywhere (chat or button) drops every pending motion question: then flip to ``ran == []``."""
    r, svc, c, app = make(tmp_path)
    svc.sup._set("PAUSED", "verify")
    ran = []
    svc.run_from_chat = lambda cmd, body: ran.append(cmd)
    a, b = Phone(app, svc.token, A_ID), Phone(app, svc.token, B_ID)
    _say(a, "lower")
    assert _say(b, "stop")["command_run"] == "pause"
    c.post("/api/command", json={"cmd": "pause"})
    _say(a, "yes")
    assert ran == ["lower"], "WEAKNESS FIXED? a pause now cancels other clients' pending questions: flip this pin"


def test_v_f1_pin_a_chat_stop_with_a_malformed_client_id_is_refused(tmp_path):
    """PIN (Low). /api/say validates X-Client before it looks at the text, so a 'stop' with a malformed id is a 400 and no pause runs.
    The page always sends a valid id and the PAUSE button (/api/command) does not read the header. Fixed when 'stop' is honoured
    whatever X-Client says (validate the id only for the confirmation path): then flip to 200 and command_run == 'pause'."""
    r, svc, c, app = make(tmp_path)
    res = Phone(app, svc.token, "x").post("/api/say", json={"text": "stop"})
    assert res.status_code == 400, "WEAKNESS FIXED? chat 'stop' is now honoured with a malformed X-Client: flip this pin"


# ------------------------------------------------------------------------------------------------------------------- F2
F2_CASES = [
    # (state, per-station setup, expected kind, must contain, must NOT contain)
    ("DISARMED", "none", "disarmed", ["nothing is holding position"], ["holding position with torque on"]),
    ("DISARMED", "off", "disarmed", ["nothing is holding position"], ["holding position with torque on"]),
    ("DISARMED", "idle", "disarmed", ["nothing is holding position"], ["with torque on"]),
    ("RECOVERY_REQUIRED", "none", "unknown", ["UNKNOWN", "stay clear"], ["with torque on"]),
    ("RECOVERY_REQUIRED", "stale_idle", "unknown", ["UNKNOWN", "stay clear"], ["with torque on"]),
    ("RECOVERY_REQUIRED", "one_stale", "unknown", ["UNKNOWN", "station B"], ["with torque on"]),
    ("RECOVERY_REQUIRED", "idle", "holding", ["every station reports IDLE"], ["UNKNOWN", "NOT holding"]),
    ("RECOVERY_REQUIRED", "one_off", "not_holding", ["NOT holding", "station B OFF", "stay clear"], ["with torque on"]),
    ("FAULT", "none", "unknown", ["UNKNOWN", "stay clear"], ["with torque on"]),
    ("FAULT", "stale_idle", "unknown", ["UNKNOWN", "stay clear"], ["with torque on"]),
    ("FAULT", "idle", "holding", ["every station reports IDLE"], ["UNKNOWN"]),
    ("FAULT", "one_off", "not_holding", ["NOT holding", "station B OFF"], ["with torque on"]),
    ("FAULT", "one_fault", "unknown", ["station C reports FAULT"], ["with torque on"]),
    ("PAUSED", "idle", "holding", ["every station reports IDLE", "holding position with torque on"], ["UNKNOWN"]),
    ("PAUSED", "one_run", "stopping", ["station A still stopping"], ["with torque on"]),
    ("PAUSED", "one_hold", "stopping", ["station A still stopping"], ["with torque on"]),
    ("PAUSED", "one_off", "not_holding", ["NOT holding", "station A OFF"], ["with torque on"]),
    ("PARKED", "bad_code", "unknown", ["UNKNOWN"], ["with torque on"]),
]


def _arrange(svc, how):
    ids = list(svc.ctx.cfg.ids)                                             # ['A', 'B', 'C', 'D']
    _no_tel(svc)
    if how == "none":
        return
    for sid in ids:
        _tel(svc, sid, {"off": 0}.get(how, 1), age_s=30.0 if how == "stale_idle" else 0.0)
    if how == "one_stale":
        _tel(svc, "B", 1, age_s=30.0)
    elif how == "one_off":
        _tel(svc, "A" if svc.sup.state in ("PAUSED", "PARKED") else "B", 0)
    elif how == "one_run":
        _tel(svc, "A", 2)
    elif how == "one_hold":
        _tel(svc, "A", 3)
    elif how == "one_fault":
        _tel(svc, "C", 4, flt=1)
    elif how == "bad_code":
        _tel(svc, "A", 9)


@pytest.mark.parametrize("state,how,kind,must,mustnot", F2_CASES, ids=[f"{c[0]}-{c[1]}" for c in F2_CASES])
def test_v_f2_pause_text_follows_the_real_station_telemetry(tmp_path, state, how, kind, must, mustnot):
    r, svc, c, app = make(tmp_path)
    svc.sup._set(state, "verify")
    _arrange(svc, how)
    http_pause = c.post("/api/command", json={"cmd": "pause"})
    assert http_pause.status_code == 200 and http_pause.get_json()["ok"] is True
    hold = http_pause.get_json()["hold"]
    _arrange(svc, how)                                                      # the HTTP pause may have moved the sim; re-arrange for chat
    svc.sup._set(state, "verify")
    chat_reply = _say(Phone(app, svc.token, A_ID), "stop")["reply"]
    assert hold["kind"] == kind, hold
    for text in (hold["text"], chat_reply):
        assert all(s in text for s in must) and not any(s in text for s in mustnot), (state, how, text)
    assert hold_report(svc.status())["kind"] == kind


def test_v_f2_the_event_log_line_makes_no_holding_claim(tmp_path):
    r, svc, c, app = make(tmp_path)
    svc.sup._set("PARKED", "verify")
    c.post("/api/command", json={"cmd": "pause"})
    lines = [e["text"] for e in c.get("/api/events").get_json()["events"] if e["kind"] == "pause"]
    assert lines and not any("holding position" in t for t in lines), lines


def test_v_f2_http_pause_survives_a_failing_status(tmp_path):
    r, svc, c, app = make(tmp_path)
    svc.status = lambda: (_ for _ in ()).throw(RuntimeError("telemetry exploded"))
    res = c.post("/api/command", json={"cmd": "pause"})
    j = res.get_json()
    assert res.status_code == 200 and j["ok"] is True and j["hold"]["kind"] == "unknown" and "RuntimeError" in j["hold"]["text"]


# ------------------------------------------------------------------------------------- PAUSE and commands on the hardware loop
def test_v_pause_and_commands_work_on_the_hardware_loop_setting(tmp_path):
    """The real threaded HTTP server, a runtime that really sleeps, ``start_background(real_sleep_s=0.0)`` (what main() does for the
    hardware). Chat 'start' + 'yes' runs the startup; PAUSE by HTTP and by chat ('stop', 'pause') is accepted within 1 s while it
    runs; the startup ends PAUSED; 'lower' by chat and 'disarm' by HTTP still go through."""
    r, svc, pings = _real_time_robot(tmp_path)
    srv = _serve(svc)
    svc.start_background(real_sleep_s=0.0)
    cid = "abcdef0123456789abcdef0123456789"

    def call(path, body):
        conn = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=20)
        t0 = time.perf_counter()
        conn.request("POST", path, body=json.dumps(body), headers={"X-Token": svc.token, "X-Client": cid, "Content-Type": "application/json"})
        resp = conn.getresponse()
        data = json.loads(resp.read().decode())
        conn.close()
        return resp.status, data, time.perf_counter() - t0
    try:
        time.sleep(0.3)
        sc, j, _ = call("/api/say", {"text": "start", "checklist": True})
        assert sc == 200 and j["pending_confirm"]["action"] == "start"
        sc, j, _ = call("/api/say", {"text": "yes", "checklist": True})
        assert sc == 200 and j["command_run"] == "start", j
        time.sleep(1.2)
        assert svc.busy == "start"
        worst = 0.0
        for body, path in (({"cmd": "pause"}, "/api/command"), ({"text": "stop"}, "/api/say"), ({"cmd": "pause"}, "/api/command"),
                           ({"text": "pause"}, "/api/say")):
            sc, j, dt = call(path, body)
            worst = max(worst, dt)
            assert sc == 200 and (j.get("ok") is True) and (path == "/api/command" or j["command_run"] == "pause"), (path, j)
            time.sleep(0.1)
        assert worst < 1.0, f"a PAUSE took {worst:.2f} s while a command held the robot lock"
        assert _wait(lambda: not svc.busy, 120) and svc.sup.state == "PAUSED", (svc.sup.state, svc.sup.reasons[-2:])
        sc, j, _ = call("/api/say", {"text": "lower"})
        assert sc == 200 and j["pending_confirm"]["action"] == "lower"
        sc, j, _ = call("/api/say", {"text": "yes"})
        assert sc == 200 and j["command_run"] == "lower", j
        assert _wait(lambda: not svc.busy, 120)
        sc, j, _ = call("/api/command", {"cmd": "disarm", "confirm": "claw_supported"})
        assert sc == 200 and j["ok"] is True, j
        assert _wait(lambda: not svc.busy, 120)
    finally:
        svc.stop_background()
        _stop(srv, svc)
        _wait(lambda: not svc.busy, 30)


# ------------------------------------------------------------------------------------------------------------------ F4, F5
def _open(port, token, path="/api/stream.mjpg"):
    s = socket.create_connection(("127.0.0.1", port), timeout=5)
    s.sendall(f"GET {path} HTTP/1.1\r\nHost: x\r\nX-Token: {token}\r\n\r\n".encode())
    return s, s.recv(300).split(b"\r\n")[0].decode()


def test_v_f4_f5_stream_slots_with_head_no_frame_and_closed_clients(tmp_path):
    frames = Frames(present=False)
    r, svc = _bare_service(tmp_path, frames)
    srv = _serve(svc)
    port = srv.server_port
    try:
        for _ in range(6):                                                  # F5: no frame -> 503 at once, no slot
            s, line = _open(port, svc.token)
            assert "503" in line and svc._streams == 0
            s.close()
        frames.present = True
        for _ in range(6):                                                  # F4: HEAD with the header token never holds a slot
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("HEAD", "/api/stream.mjpg", headers={"X-Token": svc.token})
            assert conn.getresponse().status == 200
            conn.close()
        assert svc._streams == 0
        socks = []
        for i in range(service_mod.MAX_STREAMS):
            s, line = _open(port, svc.token)
            assert "200" in line, (i, line)
            socks.append(s)
        s5, line = _open(port, svc.token)
        assert "429" in line
        s5.close()
        for s in socks:
            s.close()
        assert _wait(lambda: svc._streams == 0, 5.0), svc._streams        # every closed client gives its slot back
        s, line = _open(port, svc.token)
        assert "200" in line
        s.close()
    finally:
        _stop(srv, svc)


# ------------------------------------------------------------------------------------------------------------------- F6
def test_v_f6_token_never_in_the_access_log_for_pages_streams_errors_and_odd_spellings(tmp_path):
    r, svc = _bare_service(tmp_path, Frames())
    buf = []

    class Grab(logging.Handler):
        def emit(self, record):
            buf.append(self.format(record))
    h = Grab()
    lg = logging.getLogger("werkzeug")
    lg.addHandler(h)
    old_level = lg.level
    lg.setLevel(logging.INFO)
    srv = _serve(svc)
    tok = svc.token
    try:
        for path in (f"/?token={tok}", f"/?tab=chat&token={tok}&x=1", f"/?TOKEN={tok}", f"/?token={tok}&token={tok}",
                     f"/v1?token={tok}", f"/api/status?token={tok}", "/api/stream.mjpg?token=WRONGWRONG1", "/nope?token=" + tok):
            conn = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=5)
            conn.request("GET", path)
            conn.getresponse().read()
            conn.close()
        s, line = _open(srv.server_port, "")                               # the stream with the token in the URL (what the <img> does)
        s.close()
        conn = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=5)
        conn.request("GET", f"/api/stream.mjpg?token={tok}&_=1")
        resp = conn.getresponse()
        resp.read(50)
        assert resp.status == 200
        conn.close()
        time.sleep(0.4)
    finally:
        _stop(srv, svc)
        lg.removeHandler(h)
        lg.setLevel(old_level)
    text = "\n".join(buf)
    assert "GET" in text and tok not in text and "WRONGWRONG1" not in text, text[-600:]
    assert "token=<redacted>" in text


def test_v_f6_page_keeps_working_when_the_url_has_no_token_source_pin():
    """Source pin: the token leaves the address bar only after sessionStorage really holds it (so a reload still works where storage
    is blocked); a stored token is used when the URL has none."""
    js = (STATIC / "app.js").read_text()
    assert 'if (store.get("rc_token") === t) stripTokenFromUrl();' in js
    assert 'return store.get("rc_token") || "";' in js


# ------------------------------------------------------------------------------------------------------------------ F14
def _css_rule(css, selector):
    m = re.search(r"(?m)^" + re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert m, selector
    return m.group(1)


def test_v_f14_dock_is_above_the_connect_overlay_and_the_overlay_stops_above_it():
    css = (STATIC / "app.css").read_text()
    z = lambda rule: int(re.search(r"z-index:\s*(\d+)", rule).group(1))
    assert z(_css_rule(css, ".dock")) > z(_css_rule(css, ".connect"))
    assert re.search(r"inset:\s*0 0 var\(--dock-h", _css_rule(css, ".connect"))


def test_v_f14_pin_the_pause_failure_toast_is_hidden_behind_the_connect_overlay():
    """PIN (Low, found in Chromium: elementFromPoint at the toast centre returns the connect card). The overlay now ends above PAUSE,
    so the toast ('PAUSE DID NOT REACH THE ROBOT SERVICE...', bottom = dock height + 8 px) lies inside the overlay area and its z-index
    (30) is below the overlay's (50): pressing PAUSE with no or a wrong token shows nothing. Fixed when .toast has a z-index above
    .connect (or the toast is drawn in the overlay): then flip to ``>``."""
    css = (STATIC / "app.css").read_text()
    z = lambda rule: int(re.search(r"z-index:\s*(\d+)", rule).group(1))
    assert z(_css_rule(css, ".toast")) < z(_css_rule(css, ".connect")), "WEAKNESS FIXED? the toast is now above the connect overlay: flip this pin"
