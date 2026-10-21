"""Round-2 review: is the 3c (old layout) drag at 0.5 px real or an artefact?  Re-runs the study case 3c, seed 1, corner noise
0.5 px, records at every DragWatch update the MEASURED filtered displacement and the TRUE claw displacement from the simulator
(world.p), and the pretension target error.   OMP_NUM_THREADS=1 /usr/bin/python3 scripts/review_drag.py [seed] [pix]"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import sim_floor_reference_study as S                                   # noqa: E402

from roomcleaner.cdpr import startup as st                              # noqa: E402

seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
pix = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
rec = []
_init, _upd = st.DragWatch.__init__, st.DragWatch.update
world_ref = {}


def init(self, ref, **k):
    _init(self, ref, **k)
    w = world_ref["w"]
    self.truth0 = w.p.copy()


def upd(self, o):
    r = _upd(self, o)
    w = world_ref["w"]
    rec.append((float(self.last_disp_m), float(self.last_thr_m), float(np.linalg.norm(w.p - self.truth0)), bool(r)))
    return r


st.DragWatch.__init__, st.DragWatch.update = init, upd
from roomcleaner.cdpr.sim import harness                                # noqa: E402
_SR = harness.SimRobot.__init__


def sr(self, *a, **k):
    _SR(self, *a, **k)
    world_ref["w"] = self.world


harness.SimRobot.__init__ = sr
spec = dict(S.case_table()["3c sparse 3x3 p0.42 (1.0 m, 9 sheets)"], cfg={"startup.slack_probe": True}, no_whatif=True, pix=pix, est_pix=pix)
out = S.run_one(("3c", spec, seed))
print("result:", out.get("state"), out.get("reasons", out.get("error")), "tags", out.get("floor_tags_in_view"), "att mrad", out.get("floor_attitude_sigma_mrad"))
a = np.array(rec)
if len(a):
    print("DragWatch updates:", len(a), "last 6 [measured filtered mm, threshold mm, TRUE displacement mm, tripped]:")
    print(np.round(a[-6:] * [1e3, 1e3, 1e3, 1], 2))
    print("max measured %.2f mm, max true %.2f mm; |measured - true| median %.2f mm" % (a[:, 0].max() * 1e3, a[:, 2].max() * 1e3, np.median(np.abs(a[:, 0] - a[:, 2])) * 1e3))
