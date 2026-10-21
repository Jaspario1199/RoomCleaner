#!/usr/bin/env python3
"""Run KiCad 7's real Electrical Rules Checker headlessly and save its report (claw Rev B copy of the station runner).

kicad-cli 7.0.11 has NO `sch erc` subcommand (it arrived in KiCad 8.0), so this script drives the
eeschema GUI under Xvfb with synthetic X11 events (ctypes + libX11 + libXtst, no extra packages):
  Inspect > Electrical Rules Checker > Run ERC > Save...

    python3 run_erc_xvfb.py [--project-dir DIR] [--out REPORT.rpt] [--shots DIR]

* The project is COPIED to a temp folder and eeschema runs with its own XDG config dir, so neither
  the project files nor ~/.config/kicad are touched.
* Coordinates assume the default 1280x720 eeschema window on a 1600x1000 Xvfb screen (KiCad 7.0.x,
  fresh config).  It checks the saved report and exits non-zero if the report is missing, if it
  cannot be parsed, or if it contains errors.
* Report format: "ERC messages: N  Errors E  Warnings W".
"""
import argparse
import ctypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = "RoomCleaner_Claw_RevB"
NICK = "RoomCleanerClaw"
FILES = [f"{PROJECT}.kicad_sch", f"{PROJECT}.kicad_pro", f"{NICK}.kicad_sym", "sym-lib-table", "fp-lib-table"]
DISPLAY_NUM = 77

# --- window geometry (screen pixels) -------------------------------------
WELCOME_OK = (1017, 584)
MENU_INSPECT = (206, 12)
MENU_ERC = (282, 37)
ERC_RUN = (923, 540)
ERC_SAVE = (923, 491)


class XDo:
    def __init__(self, display):
        self.x11 = ctypes.CDLL("libX11.so.6")
        self.xtst = ctypes.CDLL("libXtst.so.6")
        x11, xtst = self.x11, self.xtst
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
        x11.XStringToKeysym.restype = ctypes.c_ulong
        x11.XFlush.argtypes = [ctypes.c_void_p]
        xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
        xtst.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
        xtst.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                              ctypes.c_ulong]
        self.d = x11.XOpenDisplay(display.encode())
        if not self.d:
            raise SystemExit(f"cannot open X display {display}")

    def _kc(self, name):
        return self.x11.XKeysymToKeycode(self.d, self.x11.XStringToKeysym(name.encode()))

    def click(self, xy):
        self.xtst.XTestFakeMotionEvent(self.d, -1, xy[0], xy[1], 0)
        self.x11.XFlush(self.d)
        time.sleep(0.2)
        self.xtst.XTestFakeButtonEvent(self.d, 1, 1, 0)
        self.x11.XFlush(self.d)
        time.sleep(0.1)
        self.xtst.XTestFakeButtonEvent(self.d, 1, 0, 0)
        self.x11.XFlush(self.d)
        time.sleep(0.5)

    def key(self, name, mods=()):
        for m in mods:
            self.xtst.XTestFakeKeyEvent(self.d, self._kc(m), 1, 0)
        self.xtst.XTestFakeKeyEvent(self.d, self._kc(name), 1, 0)
        self.xtst.XTestFakeKeyEvent(self.d, self._kc(name), 0, 0)
        for m in reversed(mods):
            self.xtst.XTestFakeKeyEvent(self.d, self._kc(m), 0, 0)
        self.x11.XFlush(self.d)
        time.sleep(0.25)

    def type(self, s):
        names = {"/": "slash", ".": "period", "_": "underscore", "-": "minus", " ": "space"}
        for ch in s:
            if ch == "_":
                self.key("underscore", ("Shift_L",))
            elif ch.isupper():
                self.key(ch.lower(), ("Shift_L",))
            else:
                self.key(names.get(ch, ch))


def screenshot(display, path):
    subprocess.run(["import", "-window", "root", str(path)], env={**os.environ, "DISPLAY": display},
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", default=str(HERE))
    ap.add_argument("--out", default=str(HERE / f"{PROJECT}_erc.rpt"))
    ap.add_argument("--shots", default="", help="folder for debug screenshots")
    a = ap.parse_args()
    src, out = Path(a.project_dir), Path(a.out).resolve()
    for exe in ("Xvfb", "eeschema"):
        if not shutil.which(exe):
            raise SystemExit(f"{exe} not found")
    tmp = Path(tempfile.mkdtemp(prefix="erc_"))
    proj = tmp / "proj"
    cfg = tmp / "cfg" / "kicad" / "7.0"
    proj.mkdir()
    cfg.mkdir(parents=True)
    for f in FILES:
        shutil.copy(src / f, proj / f)
    shutil.copytree(src / f"{NICK}.pretty", proj / f"{NICK}.pretty")
    for t in ("sym-lib-table", "fp-lib-table"):
        shutil.copy(f"/usr/share/kicad/template/{t}", cfg / t)
    display = f":{DISPLAY_NUM}"
    xvfb = subprocess.Popen(["Xvfb", display, "-screen", "0", "1600x1000x24"], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    ee = None
    try:
        time.sleep(2)
        env = {**os.environ, "DISPLAY": display, "XDG_CONFIG_HOME": str(tmp / "cfg"),
               "XDG_DATA_HOME": str(tmp / "data"), "XDG_CACHE_HOME": str(tmp / "cache"),
               "LIBGL_ALWAYS_SOFTWARE": "1", "GDK_BACKEND": "x11"}
        ee = subprocess.Popen(["eeschema", f"{PROJECT}.kicad_sch"], cwd=proj, env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        x = XDo(display)
        shots = Path(a.shots) if a.shots else None
        if shots:
            shots.mkdir(parents=True, exist_ok=True)
        time.sleep(12)
        x.click(WELCOME_OK)                 # "Welcome to KiCad 7.0!" -> start with default settings
        time.sleep(9)
        x.click(MENU_INSPECT)
        x.click(MENU_ERC)
        time.sleep(3)
        x.click(ERC_RUN)
        time.sleep(8)
        if shots:
            screenshot(display, shots / "erc_dialog.png")
        x.click(ERC_SAVE)
        time.sleep(2)
        x.key("a", ("Control_L",))
        x.type(str(tmp / "ERC.rpt"))
        x.key("Return")
        time.sleep(2)
        rpt = tmp / "ERC.rpt"
        if not rpt.exists():
            if shots:
                screenshot(display, shots / "failed.png")
            raise SystemExit("ERC report was not written (GUI automation out of step; use --shots to look)")
        text = rpt.read_text(encoding="utf-8", errors="replace")
        out.write_text(text, encoding="utf-8")
    finally:
        if ee:
            ee.kill()
        xvfb.kill()
        shutil.rmtree(tmp, ignore_errors=True)
    print(text.strip())
    m = re.search(r"Errors (\d+)\s+Warnings (\d+)", text)
    if not m:
        raise SystemExit("could not parse the ERC report")
    print(f"\nreport saved to {out}")
    return 1 if int(m.group(1)) else 0


if __name__ == "__main__":
    sys.exit(main())
