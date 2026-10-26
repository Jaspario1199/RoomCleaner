"""Map tab in a real browser (docs/ROOM_MAP_SPEC.md 5, "App"): Playwright (Node package + the preinstalled Chromium, as in
test_phone_app_review.py) against the ``--sim`` service at 360 x 740 and 1280 x 800. The script is map_app_check.js; skipped
where node, playwright or Chromium is missing."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from .test_phone_app_review import _bare_service, _serve, _stop

SCRIPT = Path(__file__).with_name("map_app_check.js")


def _node_env():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    npm_root = subprocess.run([shutil.which("npm") or "npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    env = {**os.environ, "NODE_PATH": os.pathsep.join(x for x in (npm_root, "/opt/node22/lib/node_modules") if x)}
    if subprocess.run([node, "-e", "require('playwright')"], env=env, capture_output=True).returncode:
        pytest.skip("the node 'playwright' package is not installed")
    return node, env


@pytest.fixture(scope="module", params=[(360, 740), (1280, 800)], ids=["phone", "desktop"])
def run(request, tmp_path_factory):
    node, env = _node_env()
    w, h = request.param
    tmp = tmp_path_factory.mktemp(f"map_{w}")
    (tmp / "data").mkdir()
    r, svc = _bare_service(tmp / "data")
    srv = _serve(svc)
    try:
        args = [node, str(SCRIPT), f"http://127.0.0.1:{srv.server_port}", svc.token, str(w), str(h)]
        if os.environ.get("MAP_SCREENSHOTS") and w == 360:
            args.append(os.environ["MAP_SCREENSHOTS"])
        p = subprocess.run(args, env=env, capture_output=True, text=True, timeout=240)
        if p.returncode != 0 and "Executable doesn't exist" in p.stderr:
            pytest.skip("Chromium is not installed for playwright")
        assert p.returncode == 0, p.stderr[-2000:]
        yield json.loads(p.stdout.strip().splitlines()[-1]), svc
    finally:
        _stop(srv, svc)


def test_add_by_tap_and_by_drag_move_and_resize(run):
    out, svc = run
    assert not out["errors"], out["errors"]
    assert out["emptyShown"] and out["moreClosed"]                     # simple first screen: empty-state hint, extras folded away
    assert out["afterTap"] == 1 and out["afterDrag"] == 2
    assert out["rectDroppedNear"] < 40, out["rectDroppedNear"]          # dropped where the pointer was lifted (within snapping)
    assert out["circleMovedPx"] > 20 and out["circleGrewPx"] > 5 and out["rectResizedPx"] > 5, out


def test_height_typed_in_ft_in_and_the_inspector_is_short(run):
    out, svc = run
    assert out["inspectorFields"] == ["Length", "Width", "Height"], out["inspectorFields"]
    assert any(t == "Shelf 6'5\"" for t in out["labels"]), out["labels"]


def test_overlay_save_and_reload(run):
    out, svc = run
    assert out["overlay"] >= 1
    assert out["saved"].startswith("Saved: the planner now avoids 2 shapes") and not out["dotAfterSave"]
    assert len(svc.ctx.cfg.obstacles) == 2
    shelf = [o for o in svc.ctx.cfg.obstacles if o["name"] == "Shelf"][0]
    assert abs(shelf["height_m"] - 77 * 0.0254) < 1e-6
    assert out["afterReload"] == 2 and "Shelf 6'5\"" in out["labelsAfterReload"]


def test_pause_stays_visible_and_on_top_and_there_is_no_horizontal_scroll(run):
    out, svc = run
    for c in out["checks"]:
        assert c["pause"] and c["estop"] and c["noHScroll"], c


def test_text_contrast_is_at_least_4_5_in_light_and_dark(run):
    out, svc = run
    for theme in ("lightContrast", "darkContrast"):
        vals = out[theme]
        assert "shapeLabel" in vals and len(vals) >= 4, vals
        for k, v in vals.items():
            assert v >= 4.5, (theme, k, v)
