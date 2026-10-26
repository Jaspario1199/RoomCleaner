"""INDEPENDENT browser verification of the Map tab (docs/ROOM_MAP_SPEC.md 1 "Simple first", 5 "App"), by the verifier.

Same Playwright setup as the builder's tests/cdpr/test_room_map_app.py (the Node 'playwright' package + the preinstalled Chromium,
a real --sim service over HTTP), but a separate script, tests/cdpr/map_app_verify.js, that drives the page like a user: real
touch events (CDP) at phone size, the mouse on the desktop size, light and dark. Screenshots: verification/room_map_verify_screens/.
Round 1 marked the confirmed defects ``xfail(strict=True)``; round 2 (head fcdf1c5, the builder's fixes) turned them back into
plain tests with the round-2 expectation, and added the units-with-the-map, landing-spot and field-message checks."""
import json
import os
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import pytest

from .test_phone_app_review import _bare_service, _serve, _stop

REPO = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).with_name("map_app_verify.js")
SHOTS = REPO / "verification" / "room_map_verify_screens"
EVIDENCE = REPO / "verification" / "room_map_verify_evidence.json"
BANNED = re.compile(r"keep[- ]?out|violation|coverage|obstacle|z_low|height_m|length_m|width_m|diameter_m|yaw_deg", re.I)
CONFIGS = [(360, 740, "light"), (360, 740, "dark"), (1280, 800, "light"), (1280, 800, "dark")]


def _node_env():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    npm_root = subprocess.run([shutil.which("npm") or "npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    env = {**os.environ, "NODE_PATH": os.pathsep.join(x for x in (npm_root, "/opt/node22/lib/node_modules") if x)}
    if subprocess.run([node, "-e", "require('playwright')"], env=env, capture_output=True).returncode:
        pytest.skip("the node 'playwright' package is not installed")
    return node, env


def _evidence(key, value):
    try:
        old = json.loads(EVIDENCE.read_text()) if EVIDENCE.exists() else {}
    except ValueError:
        old = {}
    old[key] = value
    EVIDENCE.write_text(json.dumps(old, indent=1, default=float))


@pytest.fixture(scope="module", params=CONFIGS, ids=[f"{w}x{h}-{s}" for w, h, s in CONFIGS])
def run(request, tmp_path_factory):
    node, env = _node_env()
    w, h, scheme = request.param
    tmp = tmp_path_factory.mktemp(f"mapv_{w}_{scheme}")
    (tmp / "data").mkdir()
    SHOTS.mkdir(parents=True, exist_ok=True)
    r, svc = _bare_service(tmp / "data")
    srv = _serve(svc)
    try:
        p = subprocess.run([node, str(SCRIPT), f"http://127.0.0.1:{srv.server_port}", svc.token, str(w), str(h), scheme, str(SHOTS)],
                           env=env, capture_output=True, text=True, timeout=900)
        if p.returncode != 0 and "Executable doesn't exist" in p.stderr:
            pytest.skip("Chromium is not installed for playwright")
        assert p.returncode == 0, p.stderr[-3000:]
        out = json.loads(p.stdout.strip().splitlines()[-1])
        out["server_obstacles"] = svc.ctx.cfg.obstacles
        out["server_hamper"] = [svc.ctx.cfg.tasks.hamper_room_m, svc.ctx.cfg.tasks.hamper_height_m]
        yield out
    finally:
        _stop(srv, svc)


def _key(out):
    return f"app_{out['w']}x{out['h']}_{out['scheme']}"


# ----------------------------------------------------------------------------------------------- the run itself
def test_every_phase_ran_without_a_page_error(run):
    assert not run["errors"], run["errors"]


# ----------------------------------------------------------------------------------------------- simple first (spec 1)
def test_the_first_screen_is_the_room_three_buttons_save_and_one_more(run):
    f = run["first"]
    assert f["emptyHint"] and "Tap Square, Rectangle or Circle" in f["emptyHint"]
    assert f["moreOpen"] is False
    assert f["controls"][:4] == ["Square", "Rectangle", "Circle", "Save map"], f["controls"]
    assert len(f["controls"]) == 5 and f["controls"][4].startswith("More"), f["controls"]
    assert f["tabs"] == ["Home", "Camera", "Setup", "Map", "Chat"]               # one new tab, no other new navigation
    assert f["saveDisabled"] and f["revertHidden"]
    r = run["rotate"]
    assert r["inspectorRect"] == ["Length", "Width", "Height"] and r["inspectorSquare"] == ["Side", "Height"]
    assert r["moreFields"][:4] == ["Name", "Position x (from wall A-D)", "Position y (from wall A-B)", "Turned (degrees)"]


def test_pause_and_the_emergency_stop_line_stay_visible_and_on_top_and_nothing_scrolls_sideways(run):
    bad = [s for s in run["steps"] if not (s["pause"] and s["estop"] and s["scrollW"] <= s["innerW"] and s["tabScrollW"] <= s["tabClientW"] + 0.5)]
    assert not bad, bad
    assert len(run["steps"]) >= 10
    w = run["w320"]
    assert w["innerW"] == 320 and w["scrollW"] <= 320 and w["pause"] and w["estop"], w


def test_touch_targets_are_at_least_44_px(run):
    small = [t for t in run["targetsFirst"] + run["targetsInspector"] + run["targets320"] if not t.get("shape") and min(t["w"], t["h"]) < 43.9]
    assert not small, small


def test_every_drawn_shape_can_be_grabbed_with_a_finger(run):
    """Round 1 L-2 (fixed): the grab area of a thin shape is at least a finger wide."""
    small = [t for t in run["targetsCrowded"] if min(t["w"], t["h"]) < 43.9]
    _evidence(_key(run) + "_small_shape_bodies", small)
    assert not small, small


def test_html_text_contrast_is_at_least_4_5(run):
    low = [c for k in ("contrastFirst", "contrastInspector", "contrastOverlay") for c in run[k] if c["ratio"] < 4.5]
    assert not low, low


def _rgb(s):
    return tuple(int(float(v)) for v in re.findall(r"[\d.]+", s)[:3])


def _lum(c):
    f = [(v / 255) / 12.92 if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]


def _ratio(a, b):
    x, y = _lum(a), _lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def _svg_label_contrast(run):
    """Per SVG label in each recorded screenshot: the label colour against the most common non-text colour inside its box."""
    from PIL import Image
    rows = []
    for name, rec in run["labelShots"].items():
        im = Image.open(rec["file"]).convert("RGB")
        for lab in rec["labels"]:
            fg = _rgb(lab["fill"])
            box = (max(0, int(lab["x0"])), max(0, int(lab["y0"])), min(im.width, int(lab["x1"]) + 1), min(im.height, int(lab["y1"]) + 1))
            if box[2] - box[0] < 2 or box[3] - box[1] < 2:
                continue
            crop = im.crop(box)
            px = [crop.getpixel((i, j)) for j in range(crop.height) for i in range(crop.width)]
            far = [p for p in px if sum((a - b) ** 2 for a, b in zip(p, fg)) > 90 ** 2]
            if not far:
                continue
            bg = Counter((p[0] // 4 * 4, p[1] // 4 * 4, p[2] // 4 * 4) for p in far).most_common(1)[0][0]
            rows.append({"shot": name, "text": lab["text"], "fg": fg, "bg": bg, "ratio": round(_ratio(fg, bg), 2)})
    return rows


def test_svg_label_contrast_is_at_least_4_5(run):
    rows = _svg_label_contrast(run)
    _evidence(_key(run) + "_svg_label_contrast", rows)
    low = [r for r in rows if r["ratio"] < 4.5 and r["text"] != "Hamper"]
    assert rows and not low, low                                 # shape names, heights and the anchor letters


def test_the_hamper_label_contrast_on_shapes_and_on_the_overlay(run):
    """Round 1 L-3 (fixed): the Hamper label has an opaque pill."""
    low = [r for r in _svg_label_contrast(run) if r["ratio"] < 4.5 and r["text"] == "Hamper"]
    assert not low, low


# ----------------------------------------------------------------------------------------------- editing
def test_add_move_resize_rotate(run):
    assert [a["shape"] for a in run["addedByTap"]] == ["box", "box", "cylinder"]
    a = run["addedByTap"]
    assert a[0]["L"] == a[0]["Wd"] == 0.5 and (a[1]["L"], a[1]["Wd"]) == (1.0, 0.5) and a[2]["d"] == 0.5
    mv = run["move"]
    assert abs(mv["dxRoom"] - mv["expect"][0]) < 0.0254 + 1e-9 and abs(mv["dyRoom"] - mv["expect"][1]) < 0.0254 + 1e-9, mv
    assert all(abs(v - round(v)) < 1e-6 for v in mv["snappedToInch"]), mv                # 1 in grid
    assert abs(run["wallSnap"]["leftEdge"]) < 1e-9                                       # flush to the wall within 5 cm
    assert run["paletteDrop"]["added"] == 1 and run["paletteDrop"]["errM"] < 0.05, run["paletteDrop"]
    rs = run["resize"]
    assert rs["square"]["equalSides"] and rs["square"]["after"][0] > rs["square"]["before"][0] and rs["square"]["handles"] == 1
    assert rs["rect"]["after"][0] > rs["rect"]["before"][0] and rs["rect"]["after"][1] > rs["rect"]["before"][1] and rs["rect"]["handles"] == 4
    assert rs["circle"]["after"][0] > rs["circle"]["before"][0] and rs["circle"]["handles"] == 1
    ro = run["rotate"]
    assert (ro["y0"], ro["y1"], ro["y2"]) == (0, 90, 30) and ro["squareHasTurn"] == 0


INCH = 0.0254
EXPECT_FT_IN = {"5'6\"": 66 * INCH, "66 in": 66 * INCH, "1.68 m": 1.68, "168 cm": 1.68, "5 ft 6 in": 66 * INCH, "5' 6\"": 66 * INCH,
                "5'6": 66 * INCH, "66\"": 66 * INCH, "66": 66 * INCH, "5’6”": 66 * INCH, "1,68 m": 1.68, "1680 mm": 1.68,
                "5'": 60 * INCH, "2 ft": 24 * INCH}


def test_lengths_are_parsed_in_ft_in_and_metres(run):
    got = {r["input"]: r for r in run["parseFtIn"]}
    for t, v in EXPECT_FT_IN.items():
        assert abs(got[t]["height_m"] - v) < 1e-9, (t, got[t])
    for t in ("abc", "-1 m"):
        assert got[t]["height_m"] == 0.75 and "not a length I understand" in got[t]["msg"], got[t]
    gm = {r["input"]: r["height_m"] for r in run["parseM"]}
    assert gm == {"1.68": 1.68, "1.68 m": 1.68, "168 cm": 1.68, "5'6\"": pytest.approx(66 * INCH)}
    assert all(lab.endswith(" m") for lab in run["labelsMetres"]), run["labelsMetres"]
    assert run["unitsLabel"] == "metres"


def test_a_zero_height_is_refused_by_the_field(run):
    """Round 1 L-4 (fixed): 0 is refused in the field, in plain words, and the value stays."""
    z = [r for r in run["parseFtIn"] if r["input"] == "0"][0]
    assert z["height_m"] == 0.75 and "not a height" in z["msg"], z
    m = run["msgs"]["zero"]
    assert m["value"] == 0.75 and "not a height" in m["field"] and not BANNED.search(m["field"]), m


def test_undo_twenty_steps_save_revert_reload(run):
    assert run["undo"]["backToStart"] and run["undo"]["stepsAvailable"] == 20
    assert run["undo"]["undoVisibleWithoutMore"] is False                               # behind More, as the spec asks
    assert run["dirtyDot"] and run["revertVisible"]
    assert run["saveMsg"] == "Saved: the planner now avoids 4 shapes." and run["dirtyDotAfter"] is False
    assert run["revertOk"] and run["reloadSame"]
    assert len(run["server_obstacles"]) >= 4
    fan = run["fanChip"]
    assert fan["shape"] == "cylinder" and fan["z_low_m"] > 2.0 and abs(fan["height_m"] - 2.7432) < 1e-9


def test_hamper_moves_and_its_rim_height_is_saved(run):
    assert run["hamperInspector"] == ["Rim height", "Position x", "Position y"]
    assert run["hamperMove"]["moved"] > 0.1
    hs = run["hamperSaved"]
    assert abs(hs["height_m"] - 24 * INCH) < 1e-9
    assert run["server_hamper"][0] == [hs["x"], hs["y"]] and run["server_hamper"][1] == hs["height_m"]


def test_the_hamper_can_be_dragged_by_its_middle(run):
    """Round 1 M-3 (fixed): the whole hamper marker takes the finger."""
    assert run["hamperMove"]["movedByMiddle"] > 0.05, run["hamperMove"]


def test_where_it_can_pick_overlay(run):
    o = run["overlay"]
    assert o["paths"] >= 1 and o["legend"]
    assert o["updateMs"] < 1000, o                       # spec: about 0.3 s after an edit (300 ms debounce + compute)
    assert o["cellMsg"].startswith("Here (") and ("would" in o["cellMsg"] or "pick" in o["cellMsg"] or "outside" in o["cellMsg"]), o


# ----------------------------------------------------------------------------------------------- words
def test_no_jargon_in_the_normal_screens(run):
    for k in ("textFirst", "textOverlay", "textAfterErrors"):
        hits = BANNED.findall(run[k]["text"] + run[k]["toast"])
        assert not hits, (k, hits)


def test_messages_shown_after_a_refused_save_are_plain(run):
    """Round 1 M-2 (fixed): field refusals, the server's landing-spot refusal and the tapped-cell reason are plain, in the user's
    units, and name shapes by their label, never by id or key."""
    ms = run["msgs"]
    msgs = [ms["zero"]["field"], ms["tooLong"]["field"], ms["tooTall"]["field"], ms["landing"]["afterSave"], run["overlay"]["cellMsg"]]
    _evidence(_key(run) + "_messages", ms | {"cell": run["overlay"]["cellMsg"]})
    bad = [m for m in msgs if BANNED.search(m) or re.search(r"\bshape o\d+\b|\bshape \d+\b", m)]
    assert not bad, bad
    assert "longer than the room" in ms["tooLong"]["field"] and "above the ceiling" in ms["tooTall"]["field"], ms
    assert "landing spot" in ms["landing"]["afterSave"] and "Not saved" in ms["landing"]["afterSave"], ms["landing"]
    assert re.search(r"\d'\d+\"|\d+\"", ms["tooLong"]["field"]), ms["tooLong"]          # the user's units, not metres
    assert "the Square" in run["overlay"]["cellMsg"] or "the robot can pick" in run["overlay"]["cellMsg"], run["overlay"]


# ----------------------------------------------------------------------------------------------- labels
def test_labels_characterisation_is_recorded(run):
    _evidence(_key(run) + "_labels", {k: {"overlaps": run[k]["overlaps"], "clipped": run[k]["clipped"]}
                                      for k in ("labelsAfterTaps", "labelsCrowded", "labelsOnHamper", "labelsOverlay", "labelsAfterReload")})


def test_labels_do_not_overlap_and_stay_inside_the_drawing(run):
    """Round 1 M-4 (fixed): greedy label placement; the lead's circle-on-hamper case included."""
    ov = [o for k in ("labelsAfterTaps", "labelsCrowded", "labelsOnHamper", "labelsOverlay", "labelsAfterReload") for o in run[k]["overlaps"]]
    assert not ov, ov
    clipped = [c for k in ("labelsAfterTaps", "labelsCrowded", "labelsOnHamper") for c in run[k]["clipped"]]
    assert not clipped, clipped


def test_new_shapes_are_placed_clear_of_the_landing_spot(run):
    """Round 2: the app never drops a new shape on the claw's landing column (the service would refuse the save)."""
    assert run["landing"], run.get("landing")
    assert all(d > 0.17 for d in run["addedClearOfLanding"]), run["addedClearOfLanding"]


def test_units_are_saved_with_the_map(run):
    """Round 1 L-1 (fixed): changing the units alone makes the map dirty, Save is enabled, and the server stores the choice."""
    u = run["unitsSaved"]
    assert u["before"] == {"dirty": False, "save": True}, u
    assert u["after"]["dirty"] and not u["after"]["save"] and u["after"]["units"] == "m", u
    assert u["server"] == "m", u


# ----------------------------------------------------------------------------------------------- the first-time user
def test_walkthrough_desk_4_by_2_ft_2_ft_6_tall(run):
    wk = run["walk"]
    _evidence(_key(run) + "_walkthrough", wk)
    # typed route: Rectangle, Length, Width, Height, Save = 5 taps, the Save tap right after typing saves the typed values
    assert wk["tapsTotal"] == 5 and wk["msg"].startswith("Saved"), wk
    s = wk["serverAfterFirstSave"][0]
    assert abs(s["length_m"] - 48 * INCH) < 1e-9 and abs(s["width_m"] - 24 * INCH) < 1e-9
    assert abs(s["height_m"] - 30 * INCH) < 0.013                  # 2'6": 0.75 m shown as 2'6" is kept (L-5, still open: below)
    # chip route: Rectangle, "Desk", Save = 3 taps; the chip's desk is 4'0" x 2'0" x 2'6"
    cr = wk["chipRoute"]
    assert cr["taps"] == 3 and cr["msg"].startswith("Saved") and "Desk 2'6\"" in cr["labels"]
    assert (cr["shape"]["length_m"], cr["shape"]["width_m"], cr["shape"]["height_m"]) == (1.22, 0.61, 0.76)
    if run["w"] < 600:
        assert wk["inspectorTopPx"] < wk["dockTopPx"]              # the shape panel starts on screen after the tap


def test_one_drag_frame_is_cheap_with_50_shapes(run):
    assert run["renderMs"]["fiftyShapes"] < 16, run["renderMs"]


@pytest.mark.xfail(strict=True, reason="FINDING L-5 (round 2: NOT fixed): typing exactly the text the field already shows (2'6\" over "
                                       "the default 0.75 m, which reads 2'6\") is not applied: the browser fires no 'change' event when "
                                       "the text is unchanged, and the field commits only on 'change' (input and blur do fire)")
def test_typing_the_shown_text_sets_the_exact_value(run):
    s = run["walk"]["serverAfterFirstSave"][0]
    assert abs(s["height_m"] - 30 * INCH) < 1e-9, s["height_m"]
