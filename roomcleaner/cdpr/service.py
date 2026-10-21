"""Setup / calibration service: HTTP API + phone app for the operator.

    python -m roomcleaner.cdpr.service --sim            # simulated robot
    python -m roomcleaner.cdpr.service --config config/robot.json   # hardware
    ... --host 0.0.0.0 --port 8100                      # reachable from the phone on the home LAN

Pages: ``/`` the phone app (Home / Camera / Setup / Chat; docs/PHONE_APP_SPEC.md), ``/v1`` the first setup page.

Endpoints (JSON):
    GET  /api/status                 supervisor state, trust level, startup step, reasons,
                                     trust {basis, reasons, margin numbers} (D26); phone app: per-station
                                     and claw telemetry, camera status, state text, anchors, quick-reply chips
    GET  /api/checks                 unmeasured configuration per stage
    POST /api/room                   {width_m, depth_m, height_m, anchors?: {A:[x,y,z],...}}
    POST /api/command                {cmd, checklist?, confirm?}
         cmd = start | pause | resume | acknowledge | recover | lower | disarm
    GET  /api/calibration            last calibration result + validation report
    GET  /api/events?since=N         ordered event log {events: [{id, t, kind, text}], last_id}
    POST /api/say                    {text, checklist?} -> {reply, pending_confirm, command_run, goto, chips}
                                     rule-based chat (chat.py); motion needs "yes" within 30 s
    GET  /api/frame.jpg              newest claw frame from the host's frame-thread cache (+ X-Frame-Age-S)
    GET  /api/stream.mjpg?token=     MJPEG at ~5 fps from the same cache (the ONLY route that takes the token as a
                                     query parameter: an <img> cannot send headers)

Long commands run on one worker thread; only ``pause`` may interrupt them.
``start`` requires ``checklist: true`` (the operator ticked the pre-start
safety list on the page); ``disarm`` requires ``confirm: "claw_supported"``.

Host loop (review C1): while no command runs, an idle thread keeps pumping the
coordinator (keep-alive pings at <= lease/4, clock sync) and polls the
supervisor, so an idle READY robot never lease-faults unnoticed and station
reboots/faults reach the trust ledger within ~100 ms.

Access (review H3): every /api call needs the session token printed at start
(``X-Token`` header; the page reads it from its URL) and a JSON content type;
the custom header also blocks cross-site form posts.
"""
from __future__ import annotations

import argparse
import json
import secrets
import socket
import sys
import threading
import time
from pathlib import Path

import numpy as np
from flask import Flask, Response, jsonify, request, send_from_directory

from .chat import STATE_HINT, STATE_TEXT, Chat, EventLog, Refused, chips_for
from .supervisor import ALLOWED, STATES, CommandRefused, Supervisor

STATIC = Path(__file__).parent / "static"
STREAM_PERIOD_S = 0.2            # MJPEG pace (~5 fps)
MAX_STREAMS = 4                  # open camera streams (each holds a server thread)
CLAW_POLL_S = 2.0                # claw telemetry refresh (background thread, never from a request)
CLAW_STALE_S = 10.0
BUSY_BACKOFF_S = 0.005           # host loop sleep while a command holds the robot lock (it pumps the stations itself)
DEFAULT_DATA = Path(__file__).resolve().parents[2] / "data" / "cdpr"
CHECKLIST = [
    "Room cleared; nobody will stand under the workspace",
    "Switched power strip (emergency stop) within reach",
    "Claw upright on the floor near the middle, marker under the camera",
    "All four cables attached and routed over their pulleys",
    "Claw battery charged per the charging rule (switch off, attended, 8.4 V charger at \u2264 1 A)",
]


def checklist_for(cfg) -> list:
    """The pre-start checklist for the ACTIVE stations of ``cfg``. Four stations: ``CHECKLIST`` exactly. Three-station mode
    names the active cables and says where the claw goes (the centroid of the active anchors, not the room centre)."""
    out = list(CHECKLIST)
    if cfg.n_active == 4:
        return out
    ids = ", ".join(cfg.ids)
    sx, sy = cfg.start_point_xy()
    out[2] = (f"Claw upright on the floor at the start point ({sx:.2f}, {sy:.2f}) m, the centroid of anchors {ids} "
              "(NOT the room centre), marker under the camera")
    out[3] = f"All active cables ({ids}) attached and routed over their pulleys"
    return out


def start_point_text(cfg) -> str:
    sx, sy = cfg.start_point_xy()
    if cfg.n_active == 4:
        return f"Start point: the middle of the room, ({sx:.2f}, {sy:.2f}) m. Put the claw upright here, marker under the camera."
    return (f"Start point: ({sx:.2f}, {sy:.2f}) m, the centroid of anchors {', '.join(cfg.ids)} (not the room centre). "
            "Put the claw upright here, marker under the camera.")


def workspace_summary(cfg, anchors=None) -> dict | None:
    """Three-station mode: the triangle the claw can use and the tension-floor margin from each of its edges (m); None for
    four stations. ``anchors``: (3, 3) room-frame anchors (default: the configured priors)."""
    if cfg.n_active != 3:
        return None
    from .config import triangle_geometry
    A = cfg.anchor_priors() if anchors is None else np.asarray(anchors, float)
    g = triangle_geometry(A[:, :2])
    lam = cfg.tension_floor_fraction()
    out = {"ids": list(cfg.ids), "triangle_area_m2": round(g["area_m2"], 3)}
    if lam is None:                                      # the margin is T_floor / (m g): not known until claw.mass_kg is set
        return {**out, "tension_floor_fraction": None, "edge_margin_m": None, "usable_area_m2": None,
                "note": "claw.mass_kg is not set: the edge margin from the tension floor cannot be computed yet"}
    return {**out, "tension_floor_fraction": round(lam, 4),
            "edge_margin_m": {s: round(float(lam * g["altitudes_m"][i]), 3) for i, s in enumerate(cfg.ids)},
            "usable_area_m2": round(g["area_m2"] * (1 - 3 * lam) ** 2, 3)}


class Service:
    def __init__(self, robot_ctx, *, data_dir=DEFAULT_DATA, config_path=None, token=None, task_factory=None,
                 frame_source=None):
        self.ctx = robot_ctx
        self.data_dir = Path(data_dir).resolve()
        self.ctx.data_dir = self.data_dir
        self.config_path = Path(config_path) if config_path else None
        self.sup = Supervisor(robot_ctx, state_path=self.data_dir / "state.json",
                              ledger_path=self.data_dir / "ledger.json")
        self.lock = threading.Lock()
        self.busy = None
        self.last_error = None
        self.token = token or secrets.token_urlsafe(16)
        self.task_factory = task_factory          # ctx -> TaskRunner (None: tasks unavailable)
        self._next_poll = 0.0
        self._stop = threading.Event()
        # -- phone app (docs/PHONE_APP_SPEC.md). Everything here only READS the host's state or logs; nothing in this
        # block moves the robot, and no request handler waits on the claw or on the host loop.
        self.events = EventLog()
        self._ev_lock = threading.Lock()
        self._sup_cursor = self._reason_cursor = 0
        self._last_detail = ""
        self._claw = None                         # newest claw telemetry (polled by a background thread)
        self.app_error = None
        # camera: the frame thread's cache (hardware: vision.src is the ThreadedFrameSource; sim: SimFrameSource)
        self.frame_src = frame_source if frame_source is not None else _vision_frame_source(robot_ctx)
        self._streams = 0
        self._streams_lock = threading.Lock()
        self.chat = Chat(_ChatHost(self))
        self.sync_events()

    # -- host loop -------------------------------------------------------------
    def idle_tick(self, dt_s=0.02):
        """One idle step: pump the stations for dt (keep-alive + sync) and poll
        the supervisor every ~100 ms. Skipped while a command owns the robot."""
        if not self.lock.acquire(blocking=False):
            return False
        try:
            self.ctx.co.wait(dt_s * 1e6)
            if self.ctx.now_s() >= self._next_poll:
                self._next_poll = self.ctx.now_s() + 0.1
                self.sup.poll()
        finally:
            self.lock.release()
        return True

    def start_background(self, real_sleep_s=0.0):
        def loop():
            while not self._stop.is_set():
                try:
                    if not self.idle_tick():       # a command owns the robot and pumps it: do not spin against it (review F3)
                        time.sleep(BUSY_BACKOFF_S)
                except Exception as e:             # never let the keep-alive die silently
                    self.last_error = f"host loop: {type(e).__name__}: {e}"
                    time.sleep(BUSY_BACKOFF_S)
                if real_sleep_s:
                    time.sleep(real_sleep_s)
        threading.Thread(target=loop, daemon=True, name="host-loop").start()
        threading.Thread(target=self._events_loop, daemon=True, name="app-events").start()
        threading.Thread(target=self._claw_loop, daemon=True, name="app-claw").start()

    def stop_background(self):
        self._stop.set()

    def _events_loop(self):
        while not self._stop.wait(0.25):
            try:
                self.sync_events()
            except Exception as e:                 # shown in /api/status, never fatal for the host loop
                self.app_error = f"events: {type(e).__name__}: {e}"

    def _claw_loop(self):
        while not self._stop.is_set():
            self.poll_claw()
            self._stop.wait(CLAW_POLL_S)

    def _run(self, name, fn):
        def work():
            err = None
            try:
                fn()
            except CommandRefused as e:
                self.last_error = err = str(e)
            except Exception as e:                   # surfaced to the operator, never swallowed
                self.last_error = err = f"{type(e).__name__}: {e}"
                self.sup.reasons.append(self.last_error)
                if self.sup.state in ("STARTUP", "TASK"):
                    self.sup._set("FAULT", self.last_error)
            finally:
                try:
                    self.sup.poll()                    # review M1: faults reach the ledger after every command
                except Exception:
                    pass
                self._log_done(name, err)
                self.busy = None
        if not self.lock.acquire(blocking=False):
            raise CommandRefused(f"busy with '{self.busy}'")
        self.busy = name
        self.log_event("command", f"Command '{name}' started")     # before the worker starts: results always follow it

        def wrapped():
            try:
                work()
            finally:
                self.lock.release()
        t = threading.Thread(target=wrapped, daemon=True)
        t.start()
        return t

    def command(self, cmd, body):
        """Run an operator command (the same ones the setup page uses). Every call is logged to the event log."""
        try:
            return self._command(cmd, body)           # a started command is logged by _run, a pause by the supervisor
        except CommandRefused as e:
            self.log_event("refused", f"'{cmd}' refused: {e}")
            raise

    def _command(self, cmd, body):
        self.last_error = None
        if cmd == "pause":
            self.sup.pause(body.get("why", "operator pause"))
            return None
        if cmd == "start":
            if body.get("checklist") is not True:
                raise CommandRefused("complete the pre-start checklist first")
            self.sup._require("start")
            return self._run("start", self.sup.start)
        if cmd == "disarm":
            self.sup._require("disarm")
            if body.get("confirm") != "claw_supported":
                raise CommandRefused("type 'claw_supported' to confirm the claw rests on a support")
            return self._run("disarm", lambda: self.sup.disarm(body.get("confirm", "")))
        if cmd == "task":
            self.sup._require("task")
            if self.task_factory is None:
                raise CommandRefused("tasks unavailable: garment perception is not implemented for hardware yet")
            return self._run("task", lambda: self.sup.run_task(self.task_factory(self.ctx)))
        fns = {"resume": self.sup.resume, "acknowledge": self.sup.acknowledge, "recover": self.sup.recover,
               "lower": self.sup.lower}
        if cmd not in fns:
            raise CommandRefused(f"unknown command {cmd!r}")
        self.sup._require(cmd)
        return self._run(cmd, fns[cmd])

    def set_room(self, body):
        cfg = self.ctx.cfg
        if self.sup.state not in ("DISARMED", "PARKED"):
            raise CommandRefused("room can only be edited while DISARMED or PARKED")
        try:
            room = np.array([float(body["width_m"]), float(body["depth_m"]), float(body["height_m"])])
        except (KeyError, TypeError, ValueError):
            raise CommandRefused("width_m, depth_m and height_m are required numbers")
        if np.any(room < 1.0) or np.any(room > 10.0):
            raise CommandRefused("room dimensions must be 1-10 m")
        old_room, old_anchors = cfg.room_m, {s.id: s.anchor_room_m for s in cfg.all_stations}
        cfg.room_m = room
        for sid, a in (body.get("anchors") or {}).items():
            a = np.asarray(a, float)
            if a.shape != (3,) or np.any(a < -0.2) or np.any(a > room + 0.2):
                raise CommandRefused(f"anchor {sid} outside the room")
            try:
                cfg.record(sid).anchor_room_m = a          # any of the four records (an unmounted station's entry too)
            except KeyError:
                raise CommandRefused(f"unknown station {sid!r}")
        if cfg.n_active == 3:                              # three-station mode: the anchors must still span a triangle
            from .config import ConfigError, _check_triangle
            try:
                _check_triangle(cfg)
            except ConfigError as e:
                cfg.room_m = old_room                      # a refused edit changes nothing
                for st in cfg.all_stations:
                    st.anchor_room_m = old_anchors[st.id]
                raise CommandRefused(str(e))
        if self.config_path:
            raw = json.loads(self.config_path.read_text())
            raw["room"].update(width_m=room[0], depth_m=room[1], height_m=room[2])
            for s in raw["stations"]:
                if s["id"] in (body.get("anchors") or {}):
                    s["anchor_room_m"] = list(map(float, body["anchors"][s["id"]]))
            self.config_path.write_text(json.dumps(raw, indent=2))
        from .calibration import Priors
        self.ctx.cal.priors = self.ctx.priors = Priors.from_config(cfg)
        return {"room_m": room.tolist(), "anchors": cfg.anchor_priors().tolist()}

    def status(self):
        s = self.sup.status()
        cfg = self.ctx.cfg
        s.update(busy=self.busy, error=self.last_error, checklist=checklist_for(cfg),
                 room_m=cfg.room_m.tolist(), profile=cfg.profile)
        # three-station mode (docs/THREE_STATION_MODE.md): which stations are mounted, where the claw starts (additive keys)
        s.update(stations_active=list(cfg.ids), stations_inactive=list(cfg.inactive_ids),
                 start_point_m=[round(float(v), 4) for v in cfg.start_point_xy()], start_point_text=start_point_text(cfg),
                 workspace=workspace_summary(cfg),
                 mode_text=("" if cfg.n_active == 4 else
                            f"THREE-STATION MODE: cables {', '.join(cfg.ids)} only; station {', '.join(cfg.inactive_ids)} is "
                            "not used (not configured, not armed). No spare cable (a failed station drops the claw), about a third of the "
                            "four-cable yaw stiffness, and only the middle of the room is usable."))
        s["trust"] = self.trust_summary()
        # -- phone app additions (every key above is unchanged)
        co, now_us = self.ctx.co, self.ctx.co.rt.now_us()
        for sid, d in s["stations"].items():
            ln = co.links[sid]
            tel = ln.tel or {}
            d.update(online=bool(ln.fresh(now_us, co.tel_max_age)), boot=ln.boot,
                     tel_age_s=None if ln.tel is None else round(max(0.0, (now_us - ln.tel_host_t) / 1e6), 2),
                     encoder_valid=None if ln.tel is None else bool(tel.get("encv")))
        s["claw"] = self.claw_telemetry()
        s["camera"] = self.camera_status()
        s["state_text"] = STATE_TEXT.get(self.sup.state, "")
        s["state_hint"] = STATE_HINT.get(self.sup.state, "")
        s["anchors_m"] = {sid: [float(x) for x in row] for sid, row in zip(self.ctx.cfg.ids, self.ctx.cfg.anchor_priors())}
        s["chips"] = chips_for(self.sup.state, self.busy)
        s["allowed"] = [c for c, st in ALLOWED.items() if self.sup.state in st and c not in ("pause", "task")]
        s["app_error"] = self.app_error
        return s

    # -- event log (phone app) --------------------------------------------------------------------------
    def log_event(self, kind, text):
        """Never raises: a logging problem must not wedge a command (``busy``/the worker lock) or the host loop."""
        try:
            self.sync_events()                  # supervisor events that happened before this one come first
            return self.events.add(kind, text)
        except Exception as e:
            self.app_error = f"events: {type(e).__name__}: {e}"
            return None

    def _log_done(self, name, err):
        self.log_event("error" if err else "command",
                       f"'{name}' stopped: {err}" if err else f"'{name}' finished; state {self.sup.state}")

    def sync_events(self):
        """Copy new supervisor events, reasons and startup steps into the phone event log. Cursor based: the
        supervisor's lists only grow. Read-only on the supervisor; safe to call from any thread, at any time."""
        with self._ev_lock:
            sup = self.sup
            evs, rs = list(sup.events), list(sup.reasons)
            new_ev, new_rs = evs[self._sup_cursor:], rs[self._reason_cursor:]
            self._sup_cursor, self._reason_cursor = len(evs), len(rs)       # advance first: never log an event twice
            for t, label, why in new_ev:
                self._ingest(t, str(label), str(why or ""))
            for r in new_rs:
                self.events.add("reason", str(r))
            d = sup.detail
            if d != self._last_detail:
                self._last_detail = d
                if d and sup.state == "STARTUP":
                    self.events.add("step", "Startup step: " + d.replace("_", " ").lower())

    def _ingest(self, host_t, label, why):
        if label in STATES:
            hint = STATE_HINT.get(label, "") if label in ("FAULT", "RECOVERY_REQUIRED", "PAUSED") else ""
            text = " ".join(x for x in (f"{label}." if not why else f"{label}: {why}.", hint) if x)
            self.events.add("state", text, host_t=host_t)
        elif label.startswith("pause in "):
            self.events.add("pause", f"Pause pressed in {label[9:]}: holding position. {why}".strip(), host_t=host_t)
        elif label.startswith("TASK/"):
            self.events.add("step", f"Task step {label[5:].replace('_', ' ').lower()}. {why}".strip(), host_t=host_t)
        else:
            self.events.add("info", f"{label}. {why}".strip(), host_t=host_t)

    # -- claw telemetry and camera (cache reads only) ----------------------------------------------------
    def poll_claw(self):
        """One claw telemetry read. Called by the background thread (and tests), NEVER from a request handler."""
        try:
            st = dict(self.ctx.claw.status())
        except Exception as e:
            st = {"online": False, "error": f"{type(e).__name__}: {e}"}
        st["_t"] = time.monotonic()
        self._claw = st

    def claw_telemetry(self):
        st = self._claw
        if st is None:
            return {"online": None, "note": "no claw telemetry yet"}
        age = time.monotonic() - st["_t"]
        mn, v = self.ctx.cfg.startup.battery_min_v, st.get("battery_v")
        # the claw reports its own camera state; the simulator does not: there, a frame source is the camera
        cam_ok = st["camera_ok"] if "camera_ok" in st else (None if self.frame_src is None else self.latest_frame() is not None)
        out = {"online": bool(st.get("online")) and age <= CLAW_STALE_S, "stale": age > CLAW_STALE_S,
               "battery_v": v, "battery_min_v": mn, "battery_low": bool(st.get("battery_low")) or (v is not None and v < mn),
               "grip_closed": st.get("grip_closed"), "camera_ok": cam_ok, "camera_mode": st.get("camera_mode"),
               "age_s": round(age, 1)}
        if st.get("error"):
            out["error"] = st["error"]
        return out

    def latest_frame(self):
        fn = getattr(self.frame_src, "latest_frame", None)
        return fn() if fn else None

    def camera_status(self):
        f = self.latest_frame()
        det = getattr(self.frame_src, "detection", None)
        if callable(det):
            d = det()
        else:                                       # hardware: the observation of the frame thread (MarkerObservation)
            obs = getattr(self.frame_src, "latest", None)
            err = getattr(self.frame_src, "error", None)
            if obs is None:
                d = {"ok": None, "text": "no detector status"}
            elif obs.ok:
                n = int(getattr(obs, "n_tags", 1) or 1)
                d = {"ok": True, "n_tags": n, "text": f"marker seen ({n} tag{'s' if n != 1 else ''})"}
            else:
                d = {"ok": False, "n_tags": 0, "text": obs.reason or "marker not seen"}
            if err:
                d["text"] += f" [{err}]"
        return {"source": "sim" if isinstance(self.frame_src, SimFrameSource) else "claw",
                "available": f is not None, "age_s": None if f is None else round(f.age_s(), 2),
                "frame_id": None if f is None else f.frame_id, "mode": None if f is None else f.mode, "detection": d}

    def stream_slot(self):
        with self._streams_lock:
            if self._streams >= MAX_STREAMS:
                return False
            self._streams += 1
            return True

    def release_stream(self):
        with self._streams_lock:
            self._streams = max(0, self._streams - 1)

    # -- chat ----------------------------------------------------------------------------------------------
    def say(self, text, *, key="", checklist=False):
        return self.chat.handle(text, key=key, checklist=checklist)

    def can(self, cmd):
        """None if ``cmd`` is allowed right now, else the plain-language reason (the chat uses it to explain refusals;
        the supervisor re-checks when the command runs)."""
        if cmd in ("grip_open", "grip_close"):
            return self._grip_block()
        states = ALLOWED.get(cmd)
        if states is None:
            return f"unknown command {cmd!r}"
        if self.sup.state not in states:
            return f"'{cmd}' is only available in {', '.join(states)}; the robot is {self.sup.state}"
        if self.busy:
            return f"busy with '{self.busy}'; only pause works until it finishes"
        return None

    def _grip_block(self):
        """The grip is not a supervisor command: it is the claw client's own (the task layer uses it under host approval).
        From the phone it is allowed ONLY when the claw is verified resting on the floor (PARKED, or DISARMED with the
        floor confirmed): opening in the air would drop what the claw holds."""
        if self.busy:
            return f"busy with '{self.busy}'; only pause works until it finishes"
        st = self.sup.state
        if not (st == "PARKED" or (st == "DISARMED" and self.ctx.ledger.claw_supported)):
            return (f"the grip can only be moved from the phone when the claw is verified on the floor (PARKED); "
                    f"the robot is {st}. Opening it in the air would drop what it holds: lower the claw first")
        c = self.claw_telemetry()
        if not c.get("online"):
            return "the claw is not reporting (offline or no telemetry yet)"
        return None

    def grip(self, close: bool):
        """Open/close the grip through the claw client (same call the task layer uses). Gated by ``_grip_block``;
        runs on the command worker (serialised with the other commands) while the keep-alive keeps pumping."""
        why = self._grip_block()
        if why:
            raise CommandRefused(why)
        self.last_error = None

        def do():
            res = {}

            def call():
                try:
                    res["ok"] = self.ctx.claw.grip(close)
                except Exception as e:
                    res["err"] = f"{type(e).__name__}: {e}"
            t = threading.Thread(target=call, daemon=True, name="claw-grip")
            t.start()
            while t.is_alive():                     # the HTTP call may take up to its timeout: keep the stations' lease fed
                self.ctx.co.wait(20000)
                t.join(0.005)
            self.poll_claw()
            if "err" in res:
                raise RuntimeError(res["err"])
            if not res.get("ok"):
                raise CommandRefused("the claw refused the grip command")
        return self._run("grip_close" if close else "grip_open", do)

    def run_from_chat(self, cmd, body):
        self.log_event("chat", f"Operator confirmed '{cmd}' in chat")
        if cmd in ("grip_open", "grip_close"):
            self.grip(cmd == "grip_close")
        else:
            self.command(cmd, body)

    def trust_summary(self):
        """Why the level is what it is (D26): the basis of VERIFIED, or plain reasons it is not, plus the
        margin numbers (k, sigma, margins, worst pose) of the last startup decision."""
        lg = self.ctx.ledger
        mc = lg.margin_check or {}
        keys = ("k", "ok", "ceiling_margin_m", "workspace_margin_m", "sigma_ceiling_m", "sigma_wall_m",
                "k_sigma_ceiling_m", "k_sigma_wall_m", "worst_pose_ceiling_room_m", "worst_pose_wall_room_m",
                "worst_component_ceiling", "worst_component_wall", "slack_probe", "probed_samples",
                "witness_chi2_dof", "witness_chi2_max", "calibration_accepted", "bead_notes")
        return {"level": lg.level, "basis": lg.verified_basis,
                "full_workspace": lg.level == "VERIFIED",
                "reasons": [] if lg.level == "VERIFIED" else list(lg.trust_reasons),
                "margin": {k: mc[k] for k in keys if k in mc}}


def _vision_frame_source(ctx):
    """The frame thread of the hardware context (claw_link.ThreadedFrameSource) if it caches JPEGs, else None."""
    src = getattr(getattr(ctx, "vision", None), "src", None)
    return src if callable(getattr(src, "latest_frame", None)) else None


class _ChatHost:
    """What chat.Chat needs from the service (chat.py stays free of Flask and hardware)."""

    def __init__(self, svc: Service):
        self.svc = svc

    def snapshot(self):
        return self.svc.status()

    def can(self, cmd):
        return self.svc.can(cmd)

    def run(self, cmd, body):
        try:
            self.svc.run_from_chat(cmd, body)
        except CommandRefused as e:
            raise Refused(str(e))

    def pause(self):
        self.svc.command("pause", {"why": "operator pause (chat)"})


class SimFrameSource:
    """``--sim`` only: renders the simulator's claw view (sim/render.py ``render_claw_view``, from the TRUE claw pose) on its
    own thread at about 5 fps into the same ``CachedFrame`` cache the hardware frame thread fills, so the routes read a
    cache in both cases and never render or fetch on request. It only reads the simulated world and never calls
    ``simcam.observe`` (that would advance the plant's noise stream and change simulation results)."""

    def __init__(self, robot, *, period_s=0.2, jpeg_quality=70):
        self.robot, self.period, self.quality = robot, period_s, jpeg_quality
        self._latest = None
        self._n = 0
        self.error = None
        self._stop = threading.Event()

    def render_once(self):
        import cv2

        from .claw_link import CachedFrame
        from .sim.render import render_claw_view
        r = self.robot
        img = render_claw_view(r.world, r.camera, r.cfg.claw.T_body_cam)
        ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), self.quality])
        if not ok:
            raise RuntimeError("JPEG encode failed")
        self._n += 1
        h, w = img.shape[:2]
        self._latest = CachedFrame(buf.tobytes(), r.rt.now_us(), self._n, f"sim-{w}x{h}", time.monotonic(), 0.0)

    def start(self):
        def loop():
            while not self._stop.is_set():
                try:
                    self.render_once()
                    self.error = None
                except Exception as e:             # the world is mutated by other threads: keep going, show the error
                    self.error = f"{type(e).__name__}: {e}"
                self._stop.wait(self.period)
        threading.Thread(target=loop, daemon=True, name="sim-frames").start()
        return self

    def stop(self):
        self._stop.set()

    def latest_frame(self):
        return self._latest

    def detection(self):
        """Is the floor marker in the simulated camera's view? The deterministic half of ``SimCamera.observe`` (no random
        draws), so the Camera tab has a detection line in the simulator too."""
        import numpy as np

        from .frames import inv_T
        cam = self.robot.simcam
        d = {"ok": None, "n_tags": 0, "text": "simulated view; marker detection is modelled"}
        if self.error:
            d["text"] += f" [{self.error}]"
        if cam.covered:
            return {**d, "ok": False, "text": "marker not found (covered)"}
        if cam.board is not None or cam.board_detector is not None:
            return {**d, "text": "floor board (simulated); detection is modelled"}
        T = inv_T(self.robot.world.T_M_B() @ cam.T_B_C)
        h = cam.edge / 2
        pc = np.array([[-h, h, 0], [h, h, 0], [h, -h, 0], [-h, -h, 0]]) @ T[:3, :3].T + T[:3, 3]
        if np.any(pc[:, 2] <= 0.05):
            return {**d, "ok": False, "text": "marker behind the camera"}
        uv = cam.cam.project(pc)
        if not np.all(cam.cam.in_image(uv, 4)):
            return {**d, "ok": False, "text": "marker not in view"}
        side = float(np.mean([np.linalg.norm(uv[k] - uv[(k + 1) % 4]) for k in range(4)]))
        if side < cam.min_side:
            return {**d, "ok": False, "text": f"marker too small ({side:.0f} px)"}
        return {**d, "ok": True, "n_tags": 1, "text": f"marker in view ({side:.0f} px; modelled, not drawn)"}


def create_app(service: Service) -> Flask:
    app = Flask(__name__, static_folder=None)

    def refuse(e, code=409):
        return jsonify({"ok": False, "error": str(e)}), code

    @app.before_request
    def guard():
        if not request.path.startswith("/api/"):
            return None
        tok = request.headers.get("X-Token", "")
        if not tok and request.method == "GET" and request.path == "/api/stream.mjpg":
            tok = request.args.get("token", "")          # the ONE route that takes it in the URL (<img> sends no headers)
        if not secrets.compare_digest(tok.encode("utf-8"), service.token.encode("utf-8")):
            return refuse("missing or wrong session token", 401)
        if request.method == "POST" and not request.is_json:
            return refuse("JSON body required", 415)
        return None

    @app.after_request
    def no_store(resp):
        if request.path.startswith("/api/"):
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    # -- the app and its static files (public: the token guards /api, the page holds no data)
    def static_view(name, mimetype=None):
        def view():
            return send_from_directory(STATIC, name, mimetype=mimetype, max_age=0)
        view.__name__ = "static_" + name.replace(".", "_").replace("-", "_")
        return view
    for route, name, mime in (("/", "index.html", None), ("/v1", "setup_v1.html", None), ("/app.js", "app.js", "text/javascript"),
                              ("/app.css", "app.css", "text/css"),
                              ("/manifest.webmanifest", "manifest.webmanifest", "application/manifest+json"),
                              ("/icon.png", "icon.png", None), ("/icon-192.png", "icon-192.png", None)):
        app.add_url_rule(route, view_func=static_view(name, mime))

    @app.get("/api/status")
    def status():
        return jsonify(service.status())

    @app.get("/api/checks")
    def checks():
        cfg = service.ctx.cfg
        return jsonify({st: cfg.missing(st) for st in cfg.STAGE_ORDER})

    @app.post("/api/room")
    def room():
        try:
            return jsonify({"ok": True, **service.set_room(request.get_json() or {})})
        except CommandRefused as e:
            return refuse(e, 400)

    @app.post("/api/command")
    def command():
        body = request.get_json() or {}
        try:
            service.command(body.get("cmd"), body)
        except CommandRefused as e:
            return refuse(e)
        return jsonify({"ok": True, "state": service.sup.state})

    @app.get("/api/calibration")
    def calibration():
        p = service.data_dir / "calibration.json"
        if not p.exists():
            return refuse("no calibration yet", 404)
        return app.response_class(p.read_text(), mimetype="application/json")

    @app.get("/api/events")
    def events():
        try:
            since = int(request.args.get("since", "0"))
        except ValueError:
            return refuse("since must be an integer", 400)
        service.sync_events()
        evs, last = service.events.since(since)
        return jsonify({"events": evs, "last_id": last})

    @app.post("/api/say")
    def say():
        body = request.get_json(silent=True) or {}
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            return refuse("text is required", 400)
        if len(text) > 500:
            return refuse("text too long (500 characters)", 400)
        key = request.headers.get("X-Token", "")           # the pending question is keyed by the (guard-checked) token
        return jsonify({"ok": True, **service.say(text, key=key, checklist=body.get("checklist") is True)})

    @app.get("/api/frame.jpg")
    def frame():
        f = service.latest_frame()                           # the frame thread's cache: never a fetch from the claw
        if f is None:
            return refuse("no camera frame yet", 503)
        return Response(f.jpeg, mimetype="image/jpeg",
                        headers={"X-Frame-Age-S": f"{f.age_s():.2f}", "X-Frame-Id": str(f.frame_id),
                                 "X-Camera-Mode": f.mode, "Cache-Control": "no-store"})

    @app.get("/api/stream.mjpg")
    def stream():
        if not service.stream_slot():
            return refuse(f"too many camera streams open (max {MAX_STREAMS})", 429)

        def gen():
            try:
                last, sent = None, 0.0
                while not service._stop.is_set():
                    f = service.latest_frame()               # cache read: this loop never touches the claw or the host loop
                    now = time.monotonic()
                    if f is not None and (f is not last or now - sent >= 1.0):
                        last, sent = f, now
                        yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\nX-Frame-Age-S: %.2f\r\n\r\n"
                               % (len(f.jpeg), f.age_s())) + f.jpeg + b"\r\n"
                    time.sleep(STREAM_PERIOD_S)
            finally:
                service.release_stream()
        return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame",
                        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    return app


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--config", default="config/robot.sim.json")
    ap.add_argument("--host", default="0.0.0.0", help="interface to listen on (0.0.0.0: reachable from the phone on the LAN)")
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    a = ap.parse_args(argv)
    factory, frames = None, None
    if a.sim:
        from .sim.harness import SimRobot
        from .tasks import SimItemPerception, TaskRunner
        robot = SimRobot(a.config, data_dir=a.data, log=print)
        ctx = robot.ctx
        factory = lambda c: TaskRunner(c, SimItemPerception(robot.world))
        frames = SimFrameSource(robot).start()              # sim-only frame hook: the claw view for the Camera tab
    else:
        ctx = build_hardware_context(a.config, a.data)      # the frame thread (vision.src) caches the JPEGs itself
        factory = hardware_task_factory()
    svc = Service(ctx, data_dir=a.data, config_path=None if a.sim else a.config, task_factory=factory,
                  frame_source=frames)
    svc.start_background(real_sleep_s=0.01 if a.sim else 0.0)
    print_phone_url(a.host, a.port, svc.token)
    create_app(svc).run(host=a.host, port=a.port, threaded=True)


def lan_ip():
    """This computer's LAN address (the interface a route to the LAN would use); None if it cannot be told."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))                         # UDP connect sends nothing; it only picks the interface
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def print_phone_url(host, port, token, out=print):
    """Print the URL to open on the phone (with the session token) and, if the optional ``qrcode`` package is installed,
    a QR code of it. Returns the URL."""
    if host in ("0.0.0.0", ""):
        ip = lan_ip() or "<this-computer-ip>"
    else:
        ip = host
    url = f"http://{ip}:{port}/?token={token}"
    out(f"RoomCleaner phone app: {url}")
    if host in ("127.0.0.1", "localhost"):
        out("  (listening on this computer only; use --host 0.0.0.0 to reach it from the phone on the home LAN)")
    try:
        import qrcode
    except ImportError:
        out("  (pip install qrcode to also print a QR code for the phone)")
        return url
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(out=sys.stdout, invert=True)
    return url


def hardware_task_factory():
    """Real pickup tasks: the gen-1 YOLO-World garment detector on the claw
    camera (roomcleaner/cdpr/garments.py). None (tasks refused with a reason)
    if the detector's dependencies are not installed."""
    try:
        import ultralytics  # noqa: F401
    except ImportError:
        print("tasks disabled: pip install -r requirements-vision.txt for the garment detector")
        return None
    from ..perception.vision_detector import YoloWorldDetector
    from .claw_link import frame_bgr
    from .garments import ClawGarmentPerception
    from .tasks import TaskRunner
    detector = YoloWorldDetector(mapper=None)            # ClawGarmentPerception sets the pose-aware mapper
    return lambda c: TaskRunner(c, ClawGarmentPerception(detector, c.camera, lambda: frame_bgr(c.claw)))


def build_marker_detector(cfg, cam):
    """The floor-reference detector. With ``marker.board_layout_file`` (a surveyed FloorBoardLayout) the board detector:
    a frame with >= 2 usable tags gets the joint multi-tag pose (startup's floor stage, the suspended poses and the
    mount-offset measurement then run on it), a frame with one tag falls back to the single-tag pose with its own,
    honest covariance. Without a layout: the single tag (marker.id)."""
    from .vision.marker import MarkerDetector
    common = dict(min_side_px=cfg.camera.min_marker_pixels, max_reprojection_px=cfg.camera.max_reprojection_px,
                  ambiguity_ratio_min=cfg.camera.ambiguity_ratio_min, corner_sigma_px=cfg.camera.corner_sigma_px,
                  cov_inflate=cfg.camera.pose_cov_inflate)
    if cfg.marker.board_layout_file:
        from .board_startup import adopt_edge
        from .vision.board import BoardDetector, FloorBoardLayout
        layout = FloorBoardLayout.load(cfg.marker.board_layout_file)
        if not layout.surveyed_ids():
            raise SystemExit(f"marker.board_layout_file {cfg.marker.board_layout_file}: no surveyed tag")
        # the tags are the only ruler: a layout with nothing surveyed yet takes the measured marker.edge_m, a surveyed one that
        # disagrees with it is refused (before the detector is built from its tag size)
        msg = adopt_edge(layout, cfg.marker.edge_m)
        if msg:
            raise SystemExit(f"marker.board_layout_file {cfg.marker.board_layout_file}: {msg}")
        return BoardDetector(layout, cam, **common)
    return MarkerDetector(cfg.marker.family, cfg.marker.id, cfg.marker.edge_m, cam, **common)


def station_addresses(cfg) -> dict:
    """{id: (ip, port)} of the ACTIVE stations: the only ones that need an address and get a transport (three-station mode:
    an inactive station is never addressed, configured or armed). SystemExit if an active station or the claw has none."""
    addrs = {s.id: s.address for s in cfg.stations}
    if any(v is None for v in addrs.values()) or cfg.claw.address is None:
        raise SystemExit("station/claw addresses must be set in the config for hardware mode")
    return {k: (v.split(":")[0], int(v.split(":")[1])) for k, v in addrs.items()}


def build_hardware_context(config_path, data_dir):
    """Wire the real transports: UDP stations, HTTP claw, detector."""
    from .claw_link import DetectorFrameSource, HttpClawClient, ThreadedFrameSource
    from .config import load_config
    from .coordinator import Coordinator, RealRuntime
    from .perception import VisionSource
    from .startup import RobotContext
    from .transport import UdpHostTransport
    from .trust import TrustLedger
    from .vision.camera import CameraModel
    cfg = load_config(config_path)
    rt = RealRuntime()
    co = Coordinator(cfg, UdpHostTransport(station_addresses(cfg)), rt)
    cam = CameraModel.load(cfg.camera.intrinsics_file)
    claw = HttpClawClient(f"http://{cfg.claw.address}", now_us=rt.now_us)
    det = build_marker_detector(cfg, cam)
    src = ThreadedFrameSource(DetectorFrameSource(claw, det, camera_mode="SVGA-800x600-q10",
                                                  T_B_C=cfg.claw.T_body_cam))
    if cfg.claw.imu:
        raise SystemExit("claw.imu = true needs an external roll/pitch provider: the claw node has no IMU (D27). "
                         "Set claw.imu to false (attitude comes from vision and the cable model).")
    vision = VisionSource(src, cfg.claw.T_body_cam, cam.fx, cfg.marker.edge_m, max_age_s=cfg.camera.max_frame_age_s,
                          now_us=rt.now_us, rot_sigma=cfg.claw.vision_attitude_sigma_rad,
                          rot_floor=cfg.claw.vision_attitude_floor_rad, pixel_sigma=cfg.camera.corner_sigma_px)
    ctx = RobotContext(cfg, co, claw, vision, cam, TrustLedger.for_ids(cfg.ids), data_dir=data_dir)
    attach_board_survey(ctx, det, cfg)
    return ctx


def attach_board_survey(ctx, det, cfg):
    """Board detector: the excitation design sees the same tags (``ctx.floor_board``) and, unless ``startup.board_survey`` is
    off, the startup surveys the layout the detector shares (``board_startup.FloorBoardSurveyor``: the sheets the resting claw
    sees; the layout file named by ``marker.board_layout_file`` is updated in place)."""
    layout = getattr(det, "layout", None)
    if layout is None:
        return
    from .board_startup import FloorBoardSurveyor
    from .vision.board import BoardGeometry
    ctx.floor_board = BoardGeometry.from_layout(layout)
    if cfg.startup.board_survey:
        ctx.board_survey = FloorBoardSurveyor(layout, ctx.camera, path=cfg.marker.board_layout_file,
                                              corner_sigma_px=cfg.camera.corner_sigma_px,
                                              min_side_px=cfg.camera.min_marker_pixels, log=ctx.log)


if __name__ == "__main__":
    main()
