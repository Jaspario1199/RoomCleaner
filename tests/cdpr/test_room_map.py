"""Room map (docs/ROOM_MAP_SPEC.md 2-5): data model and validation, the exact segment tests against brute-force sampling,
the margin and the claw body, compatibility with the old cylinder format, the coverage grid (timing and shadow), the
/api/room_map endpoints and their state rules, persistence, and a three-station startup with a shape near the start point."""
import json
import time
from pathlib import Path

import numpy as np
import pytest

from roomcleaner.cdpr.config import ConfigError, load_config, validate_obstacles
from roomcleaner.cdpr.kinematics import (coverage, geometry_from_config, segment_hits_obstacle, segments_hit_obstacle,
                                         workspace_from_config)
from roomcleaner.cdpr.service import Service, create_app
from roomcleaner.cdpr.sim.harness import SimRobot
from roomcleaner.geometry import segment_intersects_box, segment_intersects_cylinder

from .simkit import fast_cfg
from .test_service import Client

SIM = "config/robot.sim.json"
ROOM = np.array([3.3528, 2.7432, 2.7432])
SHELF = {"id": "o1", "name": "Shelf", "shape": "box", "x": 0.83, "y": 0.68, "length_m": 0.80, "width_m": 0.40, "yaw_deg": 0,
         "z_low_m": 0.0, "height_m": 1.90}
FAN = {"id": "o2", "name": "Ceiling fan", "shape": "cylinder", "x": 1.68, "y": 1.37, "diameter_m": 1.10, "z_low_m": 2.25,
       "height_m": 2.74}


def raw_sim(**over):
    raw = json.loads(Path(SIM).read_text())
    for k, v in over.items():
        d = raw
        ks = k.split(".")
        for x in ks[:-1]:
            d = d[x]
        d[ks[-1]] = v
    return raw


def cfg_ws(obstacles, **over):
    cfg = load_config(raw_sim(obstacles=obstacles, **over))
    A = cfg.anchor_priors()
    geo = geometry_from_config(cfg, A)
    ws = workspace_from_config(cfg, A, lowest_point_z=float(cfg.claw.lowest_point_body_m[2]))
    return cfg, geo, ws


# ============================================================================================ 2. data model
def test_the_spec_example_loads_in_canonical_form():
    cfg = load_config(raw_sim(obstacles=[SHELF, FAN]))
    assert cfg.obstacles == [SHELF, FAN]
    assert cfg.motion.obstacle_margin_m == 0.10 and cfg.claw.body_radius_m == 0.07 and cfg.map_units == "ft-in"


def test_old_cylinder_entries_load_as_cylinders_and_ids_are_given():
    out, errs = validate_obstacles([{"x": 1.0, "y": 1.2, "r": 0.15, "z_low": 0.0, "z_high": 1.4, "name": "lamp"}], ROOM)
    assert not errs
    assert out == [{"id": "o1", "name": "lamp", "shape": "cylinder", "x": 1.0, "y": 1.2, "diameter_m": 0.30, "z_low_m": 0.0,
                    "height_m": 1.4}]


@pytest.mark.parametrize("ob, match", [
    ({"shape": "triangle", "x": 1, "y": 1, "height_m": 1}, "unknown shape"),
    ({"shape": "box", "x": 1, "y": 1, "length_m": 0.02, "width_m": 0.5, "height_m": 1}, "too small"),
    ({"shape": "cylinder", "x": 1, "y": 1, "diameter_m": 0.015, "height_m": 1}, "too small"),
    ({"shape": "box", "x": 1, "y": 1, "length_m": 3.5, "width_m": 0.5, "height_m": 1}, "larger than the room"),
    ({"shape": "box", "x": 1, "y": 1, "length_m": 0.5, "width_m": 0.5, "z_low_m": 1.0, "height_m": 1.0}, "must be below its top"),
    ({"shape": "box", "x": 1, "y": 1, "length_m": 0.5, "width_m": 0.5, "height_m": 2.80}, "above the ceiling"),
    ({"shape": "box", "x": 3.5, "y": 1, "length_m": 0.5, "width_m": 0.5, "height_m": 1}, "outside the room"),
    ({"shape": "box", "x": 1, "y": -0.1, "length_m": 0.5, "width_m": 0.5, "height_m": 1}, "outside the room"),
    ({"shape": "box", "x": 1, "y": 1, "length_m": "big", "width_m": 0.5, "height_m": 1}, "finite number"),
    ({"shape": "cylinder", "x": 1, "y": 1, "diameter_m": 0.5, "height_m": 1, "colour": "red"}, "unknown keys"),
])
def test_each_validation_refusal_has_a_message(ob, match):
    _out, errs = validate_obstacles([ob], ROOM)
    assert errs and match in errs[0], errs
    with pytest.raises(ConfigError, match=match):
        load_config(raw_sim(obstacles=[ob]))


def test_a_top_within_5_cm_of_the_ceiling_is_accepted_and_more_than_50_shapes_are_refused():
    ok = dict(FAN, height_m=float(ROOM[2]) + 0.049)
    assert not validate_obstacles([ok], ROOM)[1]
    many = [dict(SHELF, id=f"s{i}") for i in range(51)]
    assert any("at most 50" in e for e in validate_obstacles(many, ROOM)[1])
    assert any("duplicate" in e for e in validate_obstacles([SHELF, SHELF], ROOM)[1])


# ============================================================================================ 3.1 exact tests
def _dense(a, b, ob, n=4000):
    """Brute force: is any of n points on a -> b inside the shape?"""
    t = np.linspace(0.0, 1.0, n)[:, None]
    q = a + t * (b - a)
    inz = (q[:, 2] >= ob["z_low_m"]) & (q[:, 2] <= ob["height_m"])
    if ob["shape"] == "cylinder":
        inxy = np.hypot(q[:, 0] - ob["x"], q[:, 1] - ob["y"]) <= ob["diameter_m"] / 2
    else:
        a_ = np.radians(ob["yaw_deg"])
        dx, dy = q[:, 0] - ob["x"], q[:, 1] - ob["y"]
        u, v = np.cos(a_) * dx + np.sin(a_) * dy, -np.sin(a_) * dx + np.cos(a_) * dy
        inxy = (np.abs(u) <= ob["length_m"] / 2) & (np.abs(v) <= ob["width_m"] / 2)
    return bool(np.any(inz & inxy))


def test_exact_tests_agree_with_dense_sampling_on_10000_random_pairs():
    rng = np.random.default_rng(7)
    agree = disagree_near = 0
    a_all, b_all, obs = [], [], []
    for k in range(10000):
        if k % 2:
            ob = {"shape": "cylinder", "x": rng.uniform(0.5, 2.5), "y": rng.uniform(0.5, 2.0), "diameter_m": rng.uniform(0.05, 1.0),
                  "z_low_m": rng.uniform(0, 1.5)}
        else:
            ob = {"shape": "box", "x": rng.uniform(0.5, 2.5), "y": rng.uniform(0.5, 2.0), "length_m": rng.uniform(0.05, 1.2),
                  "width_m": rng.uniform(0.05, 1.2), "yaw_deg": rng.uniform(0, 360), "z_low_m": rng.uniform(0, 1.5)}
        ob["height_m"] = ob["z_low_m"] + rng.uniform(0.05, 1.2)
        a = np.r_[rng.uniform(0, 3.35, 2), rng.uniform(1.5, 2.7)]
        b = np.r_[rng.uniform(0, 3.35, 2), rng.uniform(0.0, 2.0)]
        exact = segment_hits_obstacle(a, b, ob)
        dense = _dense(a, b, ob)
        if exact == dense:
            agree += 1
        else:
            # sampling can only MISS a hit (a grazing pass shorter than its spacing), never invent one; and the margin of the
            # miss is below the sample spacing
            assert exact and not dense, (a, b, ob)
            disagree_near += 1
        a_all.append(a), b_all.append(b), obs.append(ob)
    assert agree >= 9990 and disagree_near <= 10, (agree, disagree_near)
    # the vectorised form (coverage) gives the same answer as the scalar one on every pair
    for ob, a, b in list(zip(obs, a_all, b_all))[:2000]:
        assert bool(segments_hit_obstacle(a[None], b[None], ob)[0]) == segment_hits_obstacle(a, b, ob)


def test_the_box_slab_test_and_the_reused_cylinder_test_cover_the_edge_cases():
    box = dict(SHELF, yaw_deg=30.0)
    c = (box["x"], box["y"])
    hl, hw, yaw = 0.4, 0.2, np.radians(30)
    assert segment_intersects_box([c[0], c[1], 2.5], [c[0], c[1], 0.1], c, hl, hw, yaw, 0, 1.9)        # vertical through it
    assert not segment_intersects_box([c[0], c[1], 2.5], [c[0], c[1], 1.95], c, hl, hw, yaw, 0, 1.9)   # stops above it
    assert segment_intersects_box([0, c[1], 1.0], [3, c[1], 1.0], c, hl, hw, yaw, 0, 1.9)              # horizontal through it
    assert not segment_intersects_box([0, c[1] + 0.5, 1.0], [3, c[1] + 0.5, 1.0], c, hl, hw, yaw, 0, 1.9)
    # the old helper is the one used for cylinders
    assert segment_intersects_cylinder([0, 1.37, 2.4], [3, 1.37, 2.4], (1.68, 1.37), 0.55, 2.25, 2.74)


def _old_sampler(a, b, ob, n=24):
    """The 24-point test this replaces (kinematics._segment_hits_cylinder before the room map)."""
    for s in np.linspace(0, 1, n):
        q = a + s * (b - a)
        if ob["z_low"] <= q[2] <= ob["z_high"] and np.hypot(q[0] - ob["x"], q[1] - ob["y"]) <= ob["r"]:
            return True
    return False


def test_a_5_cm_pole_that_the_old_24_sample_test_misses_is_caught():
    cfg, geo, ws = cfg_ws([], **{"motion.obstacle_margin_m": 0.0})
    A = cfg.anchor_priors()[0]
    p = np.array([3.0, 2.4, 0.6])
    b = geo.attach_world(p)[0]
    # a pole on cable A's line, placed half-way between two of the old samples
    s = (5.5 / 23)
    q = A + s * (b - A)
    old = {"x": q[0] + 0.0, "y": q[1], "r": 0.025, "z_low": 0.0, "z_high": float(ROOM[2])}
    q5, q6 = A + (5 / 23) * (b - A), A + (6 / 23) * (b - A)
    assert np.hypot(*(q5 - q6)[:2]) > 0.1                                     # samples ~12 cm apart: the pole slips between
    assert not _old_sampler(A, b, old)
    cfg, geo, ws = cfg_ws([old], **{"motion.obstacle_margin_m": 0.0, "claw.body_radius_m": 0.0})
    assert any("cable A would cross" in v for v in ws.violations(geo, p))


def test_the_deck_shelf_example():
    """docs/presentation/deck_v4: a 1.9 m shelf (0.4 m wide) centred 1.0 m from anchor A along the A-C diagonal; the claw at the
    room centre is refused at 0.8 m (cable A crosses the shelf) and clear at 1.5 m. The deck has no safety margin: with the
    default 0.10 m margin 1.5 m is refused too and the claw clears from about 1.65 m."""
    cfg0 = load_config(raw_sim())
    A = cfg0.anchor_priors()
    u = (A[2, :2] - A[0, :2]) / np.linalg.norm(A[2, :2] - A[0, :2])
    cx, cy = A[0, :2] + 1.0 * u
    shelf = {"name": "Shelf", "shape": "cylinder", "x": float(cx), "y": float(cy), "diameter_m": 0.4, "height_m": 1.9}
    centre = (A[0, :2] + A[2, :2]) / 2
    cfg, geo, ws = cfg_ws([shelf], **{"motion.obstacle_margin_m": 0.0})
    assert any("cable A would cross the Shelf" in v for v in ws.violations(geo, [*centre, 0.8]))
    assert ws.violations(geo, [*centre, 1.5]) == []
    cfg, geo, ws = cfg_ws([shelf])                                          # default margin 0.10 m
    assert any("cable A would cross the Shelf" in v for v in ws.violations(geo, [*centre, 1.5]))
    assert ws.violations(geo, [*centre, 1.7]) == []


def test_the_margin_inflates_sideways_and_in_height_and_the_claw_body_is_checked():
    pole = {"name": "Lamp", "shape": "cylinder", "x": 1.0, "y": 1.37, "diameter_m": 0.2, "height_m": 1.0}
    cfg, geo, ws = cfg_ws([pole])
    zf = -float(cfg.claw.lowest_point_body_m[2])
    # claw body: 0.10 (half) + 0.10 margin + 0.07 body radius = 0.27 m from the lamp axis
    assert any("the claw would enter the Lamp" in v for v in ws.violations(geo, [1.26, 1.37, zf + 0.02], allow_low=True))
    assert not any("claw" in v for v in ws.violations(geo, [1.28, 1.37, zf + 0.02], allow_low=True))
    # in height: the claw's lowest point must stay 0.10 m above the 1.0 m top
    assert any("claw would enter" in v for v in ws.obstacle_violations(geo, [1.0, 1.37, zf + 1.09]))
    assert not any("claw would enter" in v for v in ws.obstacle_violations(geo, [1.0, 1.37, zf + 1.11]))


# ============================================================================================ compatibility
def test_old_entries_give_the_same_answers_as_the_new_cylinder_and_no_obstacles_is_unchanged():
    old = {"x": 1.0, "y": 1.0, "r": 0.2, "z_low": 0.0, "z_high": 1.5, "name": "post"}
    new = {"name": "post", "shape": "cylinder", "x": 1.0, "y": 1.0, "diameter_m": 0.4, "z_low_m": 0.0, "height_m": 1.5}
    _, geo, ws_old = cfg_ws([old])
    _, _, ws_new = cfg_ws([new])
    _, _, ws_none = cfg_ws([])
    rng = np.random.default_rng(3)
    for _ in range(300):
        p = np.r_[rng.uniform(0.2, 3.1), rng.uniform(0.2, 2.5), rng.uniform(0.6, 2.1)]
        assert ws_old.violations(geo, p) == ws_new.violations(geo, p)
        assert ws_none.obstacle_violations(geo, p) == []
    # with no shapes the region is exactly the box / bead / triangle checks it was
    assert ws_none.obstacles == [] and ws_none.violations(geo, [1.6, 1.3, 1.0]) == []
    cfg = load_config(SIM)
    assert cfg.obstacles == []


# ============================================================================================ 3.5 coverage
def test_coverage_is_fast_for_10_shapes_and_a_shelf_casts_a_shadow():
    cfg, geo, ws = cfg_ws([])
    A = cfg.anchor_priors()
    zf = -float(cfg.claw.lowest_point_body_m[2])
    shapes = [dict(SHELF, id=f"s{i}", x=0.5 + 0.25 * i, y=0.5 + 0.15 * i, height_m=0.4 + 0.1 * i) for i in range(10)]
    t = []
    for _ in range(5):
        t0 = time.perf_counter()
        coverage(ws, A, cfg.attachment_points(), shapes, (zf + 0.01, zf + 0.35), cfg.room_m[:2])
        t.append(time.perf_counter() - t0)
    assert min(t) < 0.150, t
    # one shelf near corner A: the floor behind it (seen from anchor A) is blocked for cable A; the cells on A's side of it and
    # the far side of the room from A are not blocked by cable A
    c = coverage(ws, A, cfg.attachment_points(), [SHELF], (zf + 0.01, zf + 0.35), cfg.room_m[:2])
    assert len(c["cells"]) == c["nx"] * c["ny"] == 34 * 28

    def why(x, y):
        k = int(y / c["cell_m"]) * c["nx"] + int(x / c["cell_m"])
        return c["reasons"][c["cells"][k]]
    behind = why(1.75, 1.35)                                                  # on the A -> shelf line, beyond the shelf
    assert behind["kind"] == "shape" and behind.get("cable") == "A" and "Shelf" in behind["text"]
    assert why(3.0, 0.3)["kind"] != "shape" and why(0.3, 2.4)["kind"] != "shape"
    assert why(3.3, 0.05)["kind"] == "area"                                    # within the wall margin
    on = why(0.83, 0.68)
    assert on["kind"] == "shape" and "Shelf" in on["text"]                     # under the shelf itself


# ============================================================================================ 4. API
def make(tmp_path, config_path=None, **over):
    r = SimRobot(fast_cfg(**over), seed=11, data_dir=tmp_path)
    svc = Service(r.ctx, data_dir=tmp_path, config_path=config_path)
    app = create_app(svc)
    return r, svc, Client(app, svc.token), app


def put(c, body):
    return c.c.put("/api/room_map", json=body, headers=c.h)


def test_room_map_round_trip_and_preview_saves_nothing(tmp_path):
    r, svc, c, app = make(tmp_path)
    g = c.get("/api/room_map").get_json()
    assert g["obstacles"] == [] and g["units"] == "ft-in" and g["room_m"] == pytest.approx(list(ROOM))
    assert set(g["anchors"]) == {"A", "B", "C", "D"} and g["start_point_m"] and g["usable_box"] and g["editable"]
    body = {"obstacles": [SHELF, FAN], "hamper": {"x": 2.5, "y": 1.5, "height_m": 0.55}, "units": "m"}
    pv = c.post("/api/room_map/preview", json=body).get_json()
    assert pv["ok"] and pv["errors"] == [] and pv["coverage"]["nx"] == 34 and pv["coverage"]["ms"] < 150
    assert c.get("/api/room_map").get_json()["obstacles"] == []                # preview saved nothing
    res = put(c, body)
    assert res.status_code == 200, res.get_json()
    assert res.get_json()["text"] == "Saved: the planner now avoids 2 shapes"
    g = c.get("/api/room_map").get_json()
    assert g["obstacles"] == [SHELF, FAN] and g["units"] == "m" and g["hamper"]["x"] == 2.5 and g["hamper"]["height_m"] == 0.55
    assert svc.ctx.cfg.obstacles == [SHELF, FAN] and svc.ctx.cfg.tasks.hamper_room_m == [2.5, 1.5]


def test_every_api_validation_refusal(tmp_path):
    r, svc, c, app = make(tmp_path)
    bad = [{"obstacles": [{"shape": "tri", "x": 1, "y": 1, "height_m": 1}]},
           {"obstacles": [dict(SHELF, length_m=0.01)]}, {"obstacles": [dict(SHELF, length_m=4.0)]},
           {"obstacles": [dict(SHELF, z_low_m=2.0)]}, {"obstacles": [dict(FAN, height_m=2.9)]},
           {"obstacles": [dict(SHELF, x=9.0)]}, {"obstacles": [dict(SHELF, id=f"s{i}") for i in range(51)]},
           {"obstacles": [], "hamper": {"x": 9, "y": 1}}, {"obstacles": [], "units": "cubits"}, {"obstacles": "none"}]
    for b in bad:
        res = put(c, b)
        assert res.status_code == 400 and res.get_json()["errors"], (b, res.get_json())
        pv = c.post("/api/room_map/preview", json=b).get_json()
        assert pv["ok"] is False and pv["errors"] and pv["coverage"] is None
    assert svc.ctx.cfg.obstacles == []
    # the token and a JSON body are required like on every /api call
    raw = app.test_client()
    assert raw.get("/api/room_map").status_code == 401
    assert raw.put("/api/room_map", json={"obstacles": []}).status_code == 401
    assert raw.post("/api/room_map/preview", json={"obstacles": []}).status_code == 401
    assert raw.put("/api/room_map", data="{}", content_type="text/plain", headers=c.h).status_code == 415


def test_put_is_refused_while_busy_and_in_states_without_a_safe_claw(tmp_path):
    r, svc, c, app = make(tmp_path)
    svc.busy = "start"
    res = put(c, {"obstacles": [SHELF]})
    assert res.status_code == 409 and "busy" in res.get_json()["error"]
    svc.busy = None
    for st in ("STARTUP", "TASK", "FAULT", "RECOVERY_REQUIRED"):
        svc.sup.state = st
        res = put(c, {"obstacles": [SHELF]})
        assert res.status_code == 409 and st in res.get_json()["error"], st
    svc.sup.state = "PARKED"
    assert put(c, {"obstacles": [SHELF]}).status_code == 200


@pytest.fixture(scope="module")
def ready_robot(tmp_path_factory):
    """A full simulated four-station startup (fast profile, printed floor board as in test_system), reaching READY."""
    from roomcleaner.cdpr.sim.world import FloorBoard
    tmp = tmp_path_factory.mktemp("rm_ready")
    r = SimRobot(fast_cfg(), seed=0, data_dir=tmp, camera_kw={"board": FloorBoard.nominal(0.15)})
    svc = Service(r.ctx, data_dir=tmp)
    svc.sup.start()
    assert svc.sup.state == "READY", svc.sup.reasons[-3:]
    return r, svc, Client(create_app(svc), svc.token)


def test_ready_put_refused_when_the_claw_pose_or_its_lowering_would_be_invalid(ready_robot):
    r, svc, c = ready_robot
    p = svc.ctx.model.pose_from_positions(svc.ctx.co.positions())[0]
    # a pedestal right under the claw: the pose itself is fine (above it), lowering straight down is not
    under = {"name": "Table", "shape": "box", "x": float(p[0]), "y": float(p[1]), "length_m": 0.5, "width_m": 0.5, "height_m": 0.4}
    res = put(c, {"obstacles": [under]})
    assert res.status_code == 409 and "lowering the claw straight down" in res.get_json()["error"], res.get_json()
    # a tall cabinet where the claw is: the pose itself is refused
    tall = dict(under, name="Cabinet", height_m=2.0)
    res = put(c, {"obstacles": [tall]})
    assert res.status_code == 409 and "current pose" in res.get_json()["error"] and "Cabinet" in res.get_json()["error"]
    assert svc.ctx.cfg.obstacles == [] and svc.ctx.ws.obstacles == []
    # a shape far from the claw is accepted in READY and reaches the live workspace
    far = {"name": "Chair", "shape": "box", "x": 3.0, "y": 0.4, "length_m": 0.4, "width_m": 0.4, "height_m": 0.9}
    res = put(c, {"obstacles": [far]})
    assert res.status_code == 200, res.get_json()
    assert svc.ctx.ws.obstacles[0]["name"] == "Chair"
    pv = c.post("/api/room_map/preview", json={"obstacles": [far]}).get_json()
    assert pv["coverage"]["counts"]["ok"] > 0                                  # calibrated: most of the middle can be picked


def test_the_map_is_persisted_to_the_config_file_in_hardware_mode_and_in_memory_in_sim(tmp_path):
    cfg_path = tmp_path / "robot.json"
    cfg_path.write_text(Path(SIM).read_text())
    r, svc, c, app = make(tmp_path / "hw", config_path=cfg_path)
    assert put(c, {"obstacles": [SHELF], "hamper": {"x": 2.0, "y": 1.0, "height_m": 0.5}, "units": "m"}).status_code == 200
    raw = json.loads(cfg_path.read_text())
    assert raw["obstacles"] == [SHELF] and raw["tasks"]["hamper_room_m"] == [2.0, 1.0] and raw["map_units"] == "m"
    again = load_config(cfg_path)                                              # validated again at the next start
    assert again.obstacles == [SHELF] and again.map_units == "m"
    # --sim: no config path, nothing is written
    before = Path(SIM).read_text()
    r2, svc2, c2, _ = make(tmp_path / "sim")
    assert put(c2, {"obstacles": [SHELF]}).status_code == 200
    assert Path(SIM).read_text() == before and svc2.ctx.cfg.obstacles == [SHELF]


# ============================================================================================ startup with a shape
def test_three_station_startup_with_a_shape_near_the_start_point_reaches_ready_and_never_touches_it(tmp_path):
    from roomcleaner.cdpr.sim.world import FloorBoard as WFB
    from roomcleaner.cdpr.startup import to_room
    from roomcleaner.cdpr.supervisor import Supervisor

    from .test_three_station import fast3
    cfg0 = fast3()
    sx, sy = cfg0.start_point_xy()
    lamp = {"name": "Lamp", "shape": "cylinder", "x": float(sx + 0.55), "y": float(sy + 0.25), "diameter_m": 0.25, "height_m": 1.3}
    cfg = fast3(obstacles=[lamp])
    r = SimRobot(cfg, seed=0, data_dir=tmp_path, camera_kw={"board": WFB.nominal(0.15)})
    w = r.world
    seen = []
    step = w.step

    def recording_step(t_us, dt_s):
        out = step(t_us, dt_s)
        seen.append((w.attach_world().copy(), w.p.copy(), w.lowest_z()))
        return out
    w.step = recording_step
    sup = Supervisor(r.ctx, state_path=tmp_path / "state.json", ledger_path=tmp_path / "ledger.json")
    rep = sup.start()
    assert sup.state == "READY" and rep.outcome == "READY", (rep.reasons, sup.state)
    assert len(seen) > 1000
    # the TRUE cables and claw never met the real lamp (no margin) at any simulated step
    for pts, p, low in seen[::5]:
        for i in range(3):
            assert not segment_hits_obstacle(w.anchors[i], pts[i], cfg.obstacles[0]), p
        assert not (np.hypot(p[0] - lamp["x"], p[1] - lamp["y"]) <= lamp["diameter_m"] / 2 and low <= lamp["height_m"]), p
    # and no calibration pose violates it with the planning margin
    ws, geo = r.ctx.ws, r.ctx.model.geometry
    assert len(r.ctx.samples) >= 6
    for s in r.ctx.samples:
        assert ws.obstacle_violations(geo, to_room(r.ctx.T_R_M, s.p)) == []
