"""Compile and exercise the actual portable station core, not a Python mirror."""
from pathlib import Path
import subprocess

def test_detached_station_motion_and_faults(tmp_path):
    root=Path(__file__).resolve().parents[1]
    exe=tmp_path/'motion'
    subprocess.run(['g++','-std=c++11','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(root/'tests/local_station/test_motion.cpp'),'-o',str(exe)],check=True)
    result=subprocess.run([str(exe)],check=True,capture_output=True,text=True)
    assert '14 motion scenarios passed' in result.stdout

def test_independent_debounce_and_arrival_regressions(tmp_path):
    root=Path(__file__).resolve().parents[1]
    exe=tmp_path/'review'
    subprocess.run(['g++','-std=c++11','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(root/'tests/local_station/test_review.cpp'),'-o',str(exe)],check=True)
    result=subprocess.run([str(exe)],check=True,capture_output=True,text=True)
    assert '4 fresh debounce/arrival regression scenarios passed' in result.stdout
