"""Setup / calibration service: HTTP API + phone page for the operator.

    python -m roomcleaner.cdpr.service --sim            # simulated robot
    python -m roomcleaner.cdpr.service --config config/robot.json   # hardware

Endpoints (JSON):
    GET  /api/status                 supervisor state, trust level, startup step, reasons,
                                     trust {basis, reasons, margin numbers} (D26)
    GET  /api/checks                 unmeasured configuration per stage
    POST /api/room                   {width_m, depth_m, height_m, anchors?: {A:[x,y,z],...}}
    POST /api/command                {cmd, checklist?, confirm?}
         cmd = start | pause | resume | acknowledge | recover | lower | disarm
    GET  /api/calibration            last calibration result + validation report

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
import threading
import time
from pathlib import Path

import numpy as np
from flask import Flask, jsonify, request, send_from_directory

from .supervisor import CommandRefused, Supervisor

STATIC = Path(__file__).parent / "static"
DEFAULT_DATA = Path(__file__).resolve().parents[2] / "data" / "cdpr"
CHECKLIST = [
    "Room cleared; nobody will stand under the workspace",
    "Switched power strip (emergency stop) within reach",
    "Claw upright on the floor near the middle, marker under the camera",
    "All four cables attached and routed over their pulleys",
    "LiPo charged with a balance charger",
]


class Service:
    def __init__(self, robot_ctx, *, data_dir=DEFAULT_DATA, config_path=None, token=None, task_factory=None):
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
                    self.idle_tick()
                except Exception as e:             # never let the keep-alive die silently
                    self.last_error = f"host loop: {type(e).__name__}: {e}"
                if real_sleep_s:
                    time.sleep(real_sleep_s)
        threading.Thread(target=loop, daemon=True, name="host-loop").start()

    def stop_background(self):
        self._stop.set()

    def _run(self, name, fn):
        def work():
            try:
                fn()
            except CommandRefused as e:
                self.last_error = str(e)
            except Exception as e:                   # surfaced to the operator, never swallowed
                self.last_error = f"{type(e).__name__}: {e}"
                self.sup.reasons.append(self.last_error)
                if self.sup.state in ("STARTUP", "TASK"):
                    self.sup._set("FAULT", self.last_error)
            finally:
                try:
                    self.sup.poll()                    # review M1: faults reach the ledger after every command
                except Exception:
                    pass
                self.busy = None
        if not self.lock.acquire(blocking=False):
            raise CommandRefused(f"busy with '{self.busy}'")
        self.busy = name

        def wrapped():
            try:
                work()
            finally:
                self.lock.release()
        t = threading.Thread(target=wrapped, daemon=True)
        t.start()
        return t

    def command(self, cmd, body):
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
        cfg.room_m = room
        for sid, a in (body.get("anchors") or {}).items():
            a = np.asarray(a, float)
            if a.shape != (3,) or np.any(a < -0.2) or np.any(a > room + 0.2):
                raise CommandRefused(f"anchor {sid} outside the room")
            cfg.station(sid).anchor_room_m = a
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
        s.update(busy=self.busy, error=self.last_error, checklist=CHECKLIST,
                 room_m=self.ctx.cfg.room_m.tolist(), profile=self.ctx.cfg.profile)
        s["trust"] = self.trust_summary()
        return s

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


def create_app(service: Service) -> Flask:
    app = Flask(__name__, static_folder=None)

    def refuse(e, code=409):
        return jsonify({"ok": False, "error": str(e)}), code

    @app.before_request
    def guard():
        if not request.path.startswith("/api/"):
            return None
        if not secrets.compare_digest(request.headers.get("X-Token", ""), service.token):
            return refuse("missing or wrong session token", 401)
        if request.method == "POST" and not request.is_json:
            return refuse("JSON body required", 415)
        return None

    @app.get("/")
    def page():
        return send_from_directory(STATIC, "setup.html")

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

    return app


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--config", default="config/robot.sim.json")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    a = ap.parse_args(argv)
    factory = None
    if a.sim:
        from .sim.harness import SimRobot
        from .tasks import SimItemPerception, TaskRunner
        robot = SimRobot(a.config, data_dir=a.data, log=print)
        ctx = robot.ctx
        factory = lambda c: TaskRunner(c, SimItemPerception(robot.world))
    else:
        ctx = build_hardware_context(a.config, a.data)
        factory = hardware_task_factory()
    svc = Service(ctx, data_dir=a.data, config_path=None if a.sim else a.config, task_factory=factory)
    svc.start_background(real_sleep_s=0.01 if a.sim else 0.0)
    print(f"RoomCleaner setup: http://<this-computer-ip>:{a.port}/?token={svc.token}")
    create_app(svc).run(host=a.host, port=a.port, threaded=True)


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
    from .vision.marker import MarkerDetector
    cfg = load_config(config_path)
    rt = RealRuntime()
    addrs = {s.id: s.address for s in cfg.stations}
    if any(v is None for v in addrs.values()) or cfg.claw.address is None:
        raise SystemExit("station/claw addresses must be set in the config for hardware mode")
    co = Coordinator(cfg, UdpHostTransport({k: (v.split(":")[0], int(v.split(":")[1])) for k, v in addrs.items()}), rt)
    cam = CameraModel.load(cfg.camera.intrinsics_file)
    claw = HttpClawClient(f"http://{cfg.claw.address}", now_us=rt.now_us)
    det = MarkerDetector(cfg.marker.family, cfg.marker.id, cfg.marker.edge_m, cam,
                         min_side_px=cfg.camera.min_marker_pixels, max_reprojection_px=cfg.camera.max_reprojection_px,
                         ambiguity_ratio_min=cfg.camera.ambiguity_ratio_min)
    src = ThreadedFrameSource(DetectorFrameSource(claw, det, camera_mode="SVGA-800x600-q10",
                                                  T_B_C=cfg.claw.T_body_cam))
    vision = VisionSource(src, cfg.claw.T_body_cam, cam.fx, cfg.marker.edge_m, max_age_s=cfg.camera.max_frame_age_s,
                          now_us=rt.now_us, imu=claw if cfg.claw.imu else None)
    return RobotContext(cfg, co, claw, vision, cam, TrustLedger(), data_dir=data_dir)


if __name__ == "__main__":
    main()
