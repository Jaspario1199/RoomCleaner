"""Garment perception on the claw camera: floor mapping, pickup / delivery
verification against rendered views (BlobDetector stands in for YOLO-World,
whose weights are not installed in CI)."""
import math

import numpy as np
import pytest

from roomcleaner.cdpr.frames import make_T, rot_z
from roomcleaner.cdpr.garments import BlobDetector, ClawFloorMapper, ClawGarmentPerception
from roomcleaner.cdpr.sim.harness import SimRobot
from roomcleaner.cdpr.sim.render import render_claw_view
from roomcleaner.cdpr.sim.world import FloorBoard
from roomcleaner.cdpr.supervisor import Supervisor
from roomcleaner.cdpr.tasks import TaskRunner
from roomcleaner.cdpr.vision.camera import CameraModel

from .simkit import ITEM_CANDIDATES, assert_no_eq_failures, fast_cfg, item_offsets_with_small_statics_tilt


# ---------------------------------------------------------------- (a) mapper
def _look_down(xy, height, tilt_deg=0.0, yaw=0.3):
    """Camera pose in the room: optical axis straight down (+Z_cam = -Z_room),
    then tilted about the camera x axis."""
    R_down = np.array([[1.0, 0, 0], [0, -1.0, 0], [0, 0, -1.0]])
    t = math.radians(tilt_deg)
    Rx = np.array([[1, 0, 0], [0, math.cos(t), -math.sin(t)], [0, math.sin(t), math.cos(t)]])
    return make_T(rot_z(yaw) @ R_down @ Rx, [xy[0], xy[1], height])


@pytest.mark.parametrize("tilt_deg", [0.0, 10.0])
@pytest.mark.parametrize("dist,tol_m", [([0.0] * 5, 0.002), ([-0.12, 0.05, 0.001, -0.001, 0.0], 0.005)])
def test_floor_mapper_round_trip(tilt_deg, dist, tol_m):
    cam = CameraModel(np.array([[520.0, 0, 400.0], [0, 520.0, 300.0], [0, 0, 1]]), np.array(dist), (800, 600), "t")
    T = _look_down((1.3, 0.9), 1.2, tilt_deg)
    mapper = ClawFloorMapper(cam, T)
    T_C_R = np.linalg.inv(T)
    rng = np.random.default_rng(1)
    checked, worst = 0, 0.0
    for _ in range(400):
        p = np.array([1.3, 0.9, 0.0]) + np.r_[rng.uniform(-0.9, 0.9, 2), 0.0]
        pc = T_C_R[:3, :3] @ p + T_C_R[:3, 3]
        uv = cam.project(pc)[0]
        if not cam.in_image(uv, 5)[0]:
            continue
        worst = max(worst, float(np.linalg.norm(mapper.pixel_to_floor(*uv) - p[:2])))
        checked += 1
    assert checked > 100
    assert worst < tol_m, f"worst round-trip error {worst * 1000:.2f} mm"
    # forward helper agrees with the inverse
    p = np.array([1.5, 1.1, 0.0])
    uv = mapper.floor_to_pixel(p)
    assert np.linalg.norm(mapper.pixel_to_floor(*uv) - p[:2]) < tol_m


# ---------------------------------------------------------------- full-stack fixture
@pytest.fixture(scope="module")
def rig(tmp_path_factory):
    d = tmp_path_factory.mktemp("garments")
    cfg = fast_cfg()
    r = SimRobot(cfg, seed=0, data_dir=d, camera_kw={"board": FloorBoard.nominal(0.15)})     # the printed board (see test_system)
    sup = Supervisor(r.ctx, state_path=d / "state.json", ledger_path=d / "ledger.json")
    rep = sup.start()
    assert sup.state == "READY", rep.reasons
    assert_no_eq_failures(r, "garments rig startup")
    r.world.hamper = (np.asarray(cfg.tasks.hamper_room_m), cfg.tasks.hamper_radius_m)
    return r, sup


def _reset_items(world):
    world.items.clear()
    world.held = None
    world.mass = world.base_mass


def _perception(r):
    rng = np.random.default_rng(7)

    def frame_fn():
        return render_claw_view(r.world, r.camera, r.cfg.claw.T_body_cam, rng=rng)
    return ClawGarmentPerception(BlobDetector(), r.camera, frame_fn)


def _count(per, text):
    return sum(text in line for line in per.log)


def test_rendered_view_shows_items_and_jaw(rig):
    r, _ = rig
    _reset_items(r.world)
    r.world.add_item("sock", r.world.p[:2] + [0.1, 0.1])
    img = render_claw_view(r.world, r.camera, r.cfg.claw.T_body_cam, rng=np.random.default_rng(0))
    assert img.shape == (600, 800, 3) and img.dtype == np.uint8
    dets = BlobDetector().detect(img)
    assert len(dets) == 1
    # deterministic given the rng
    img2 = render_claw_view(r.world, r.camera, r.cfg.claw.T_body_cam, rng=np.random.default_rng(0))
    assert np.array_equal(img, img2)
    _reset_items(r.world)


def test_task_delivers_items_with_visual_verification(rig):
    r, sup = rig
    _reset_items(r.world)
    c = r.world.p[:2].copy()                       # around where the startup left the claw (inside its camera footprint)
    # inside the validated volume, away from the hamper (the scan ignores anything within its radius), and where the cable
    # model's static tilt at the grip pose is within the host's grip limit (it ranges from 2 to 9 deg across the room)
    items = [c + o for o in item_offsets_with_small_statics_tilt(r.ctx, ITEM_CANDIDATES)]
    assert all(np.linalg.norm(xy - np.asarray(r.cfg.tasks.hamper_room_m)) > r.cfg.tasks.hamper_radius_m + 0.1
               for xy in items)
    r.world.add_item("sock", items[0])
    r.world.add_item("jeans", items[1], mass=0.9, height=0.08)
    per = _perception(r)
    out = sup.run_task(TaskRunner(r.ctx, per))
    assert len(out["done"]) == 2, (out, per.log)
    assert not out["failed"] and sup.state == "READY"
    assert all(it["state"] == "hamper" for it in r.world.items)
    assert_no_eq_failures(r, "garment task")
    holds = [line for line in per.log if line.startswith("holding:")]
    # per item: held after the lift-and-shift, then NOT held after the release
    assert [h.endswith("-> True") for h in holds] == [True, False, True, False], per.log
    assert _count(per, "delivery: inside True") == 2          # the garment is actually seen in the hamper
    assert not any("still occupied" in line for line in per.log)


def test_failed_grip_is_detected_and_retried(rig, monkeypatch):
    r, sup = rig
    _reset_items(r.world)
    here = r.world.p[:2].copy()
    r.world.add_item("tee", here + [-0.25, 0.15])
    per = _perception(r)
    real_grip = r.world.grip
    calls = {"missed": 0}

    def flaky(close, *a, **kw):
        if close and calls["missed"] == 0:
            calls["missed"] = 1                      # the first closing grabs nothing
            return None
        return real_grip(close, *a, **kw)
    monkeypatch.setattr(r.world, "grip", flaky)
    out = sup.run_task(TaskRunner(r.ctx, per))
    assert calls["missed"] == 1, (out, per.log, r.world.p, r.world.items)
    holds = [line for line in per.log if line.startswith("holding:")]
    assert holds[0].endswith("-> False"), per.log             # empty jaws + garment still on the floor
    assert "spot clear False" in holds[0]
    assert len(out["done"]) == 1 and not out["failed"], (out, per.log)     # retry succeeded
    assert any(h.endswith("-> True") for h in holds[1:])
    assert r.world.items[0]["state"] == "hamper"


def test_release_failure_is_not_reported_as_delivered(rig, monkeypatch):
    r, sup = rig
    _reset_items(r.world)
    here = r.world.p[:2].copy()
    r.world.add_item("scarf", here + [-0.25, 0.1])
    per = _perception(r)
    real_grip = r.world.grip
    calls = {"stuck": 0}

    def sticky(close, *a, **kw):
        if not close and r.world.held is not None and calls["stuck"] == 0:
            calls["stuck"] = 1                       # the jaws fail to let go once
            return None
        return real_grip(close, *a, **kw)
    monkeypatch.setattr(r.world, "grip", sticky)
    out = sup.run_task(TaskRunner(r.ctx, per))
    assert calls["stuck"] == 1, (out, per.log, r.world.p, r.world.items)
    assert out["done"] == [], (out, per.log)
    assert out["failed"] and out["failed"][0][1] == "item still in the claw after release", out
    holds = [line for line in per.log if line.startswith("holding:")]
    assert holds[0].endswith("-> True") and holds[-1].endswith("-> True")
    assert r.world.held is not None                           # it really is still in the claw
    # tidy up: let go so the shared rig stays consistent
    r.world.grip(False)
