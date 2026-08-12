"""
One-command RoomCleaner setup. Run with your system Python (3.10+):

    python quickstart.py                     # core install + self-test
    python quickstart.py --vision            # + camera/YOLO stack (big download)
    python quickstart.py --vision --camera 1 # ...then launch live detection

It creates a ./venv, installs everything into it, runs the test suite to
prove the install, and (optionally) starts the webcam detector. Safe to
re-run any time; it only installs what's missing.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import venv

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(ROOT, "venv")


def venv_python() -> str:
    if os.name == "nt":
        return os.path.join(VENV, "Scripts", "python.exe")
    return os.path.join(VENV, "bin", "python")


def run(args: list[str], **kw) -> None:
    print(f"\n$ {' '.join(args)}")
    subprocess.check_call(args, cwd=ROOT, **kw)


def main() -> None:
    # Windows consoles (and redirected stdout) default to cp1252, which cannot
    # encode the checkmark printed on success — that raised UnicodeEncodeError
    # and aborted setup on Windows. Force UTF-8 so it completes cleanly.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vision", action="store_true",
                    help="also install the camera/YOLO stack (torch — several GB)")
    ap.add_argument("--camera", type=int, default=None, metavar="N",
                    help="after setup, launch live detection on camera index N "
                         "(USB cam on a laptop is usually 1)")
    ap.add_argument("--demo", action="store_true",
                    help="after setup, run the full simulation demo")
    args = ap.parse_args()

    if sys.version_info < (3, 10):
        sys.exit(f"Python 3.10+ required (you have {sys.version.split()[0]}). "
                 "Install from python.org and re-run.")

    if not os.path.exists(venv_python()):
        print(f"Creating virtual environment at {VENV} ...")
        venv.EnvBuilder(with_pip=True).create(VENV)
    py = venv_python()

    run([py, "-m", "pip", "install", "--upgrade", "pip", "-q"])
    run([py, "-m", "pip", "install", "-r", "requirements.txt"])
    if args.vision or args.camera is not None:
        print("\nInstalling the vision stack (torch + ultralytics) — this is "
              "a multi-GB download, give it a few minutes...")
        run([py, "-m", "pip", "install", "-r", "requirements-vision.txt"])

    print("\nRunning the self-test suite (~1 min) ...")
    run([py, "-m", "pytest", "-q"])
    print("\n✅ Install verified — every subsystem passed on this machine.")

    if args.demo:
        run([py, "-m", "scripts.demo_sim"])
        print("\nOutputs written to ./output (scene_before.png, workspace.png, run.gif)")

    if args.camera is not None:
        print("\nLaunching live detection (first run downloads YOLO-World "
              "weights, a few hundred MB, one time). Ctrl-C to stop.")
        run([py, "-m", "scripts.detect_webcam", "--camera", str(args.camera)])
    else:
        act = "venv\\Scripts\\activate" if os.name == "nt" else "source venv/bin/activate"
        print(f"""
Next steps:
  {act}
  python -m scripts.demo_sim                  # watch the robot in simulation
  python -m scripts.detect_webcam --camera 1  # live laundry detection
""")


if __name__ == "__main__":
    main()
