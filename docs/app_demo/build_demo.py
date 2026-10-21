"""Build a single-file demo of the phone app (docs/app_demo/RoomCleaner_app_demo.html).

The page is the real app (roomcleaner/cdpr/static: index.html, app.css, app.js, unchanged) with
mock_robot.js in front of it: a simulated robot that answers the app's /api calls in the browser.
It exists so the app can be opened from a phone link without the robot service; the real app runs on
the host computer (python -m roomcleaner.cdpr.service) and is reached on the home Wi-Fi.

    python3 docs/app_demo/build_demo.py
"""
import base64
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
STATIC = HERE.parents[1] / "roomcleaner" / "cdpr" / "static"
OUT = HERE / "RoomCleaner_app_demo.html"

DARK_RE = re.compile(r"@media \(prefers-color-scheme: dark\) \{\s*:root \{(?P<body>.*?)\}\s*\}", re.S)


def themed_css(css: str) -> str:
    """The app follows the OS theme only; the hosted page also has to follow the viewer's explicit choice
    (data-theme on the root element), and fit inside the host's safe-area padding instead of 100vh."""
    m = DARK_RE.search(css)
    assert m, "dark token block not found in app.css"
    dark = m.group("body").strip()
    block = ("@media (prefers-color-scheme: dark) {\n  :root:not([data-theme=\"light\"]) {\n    " + dark
             + "\n    color-scheme: dark;\n  }\n}\n:root[data-theme=\"dark\"] {\n  " + dark + "\n  color-scheme: dark;\n}")
    css = css[:m.start()] + block + css[m.end():]
    css = css.replace("color-scheme: light dark;", "color-scheme: light;", 1)
    css = css.replace("height: 100vh; height: 100dvh;", "height: 100%;", 1)
    return css


def main():
    html = (STATIC / "index.html").read_text()
    css = themed_css((STATIC / "app.css").read_text())
    app_js = (STATIC / "app.js").read_text()
    mock = (HERE / "mock_robot.js").read_text()
    cap = json.loads((HERE / "captured_api.json").read_text())
    frame = "data:image/jpeg;base64," + base64.b64encode((HERE / "sim_frame.jpg").read_bytes()).decode()

    body = html.split("<body>", 1)[1].rsplit("</body>", 1)[0]
    body = body.replace('<script src="/app.js"></script>', "")
    anchor = '<div id="banner" class="banner" role="alert" hidden></div>'
    assert anchor in body, "banner element not found in index.html"
    body = body.replace(anchor, anchor + '\n<div id="demoNote" class="banner demo" role="note"></div>', 1)
    demo_note = ("Demo: a simulated robot runs inside this page, so nothing here reaches hardware. The real app runs on "
                 "the laptop next to the robot and opens on your phone over home Wi-Fi.")
    page = f"""<title>RoomCleaner App Demo</title>
<style>
{css}
.banner.demo {{ background: var(--surface2); color: var(--ink); border-bottom: 1px solid var(--border); font-weight: 500; font-size: 13px; }}
</style>
{body}
<script>window.__RC_CAPTURE = {json.dumps(cap)}; window.__RC_FRAME = "{frame}";</script>
<script>
{mock}
</script>
<script>
{app_js}
</script>
<script>
(() => {{
  document.getElementById("demoNote").textContent = {json.dumps(demo_note)};
  const mic = document.getElementById("mic"); if (mic) mic.hidden = true;   // the hosted page has no microphone
  window.dispatchEvent(new Event("resize"));
}})();
</script>
"""
    OUT.write_text(page)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
