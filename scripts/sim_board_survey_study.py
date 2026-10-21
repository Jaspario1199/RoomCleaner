"""Full simulated startup with the floor board SURVEYED by the startup, against the same board known in advance.

    OMP_NUM_THREADS=1 /usr/bin/python3 scripts/sim_board_survey_study.py survey 0     # layout surveyed by the startup (jittered sheets)
    OMP_NUM_THREADS=1 /usr/bin/python3 scripts/sim_board_survey_study.py study 0      # the nominal 0.25 m grid known exactly (as the 3i case)
    ... survey 0 noprobe                                                              # the default profile: slack probe off

One seed per process (about 8-10 min each, startup.slack_probe on unless 'noprobe', 150 mm tags). Prints one JSON line: outcome, trust, tags in view at
the resting claw, the survey report (sheets surveyed at SELF_CHECK, the top-ups, what is unsurveyed), the predicted absolute sigma and the
worst true L0 error. Numbers: verification/board_followups_results.md section 3.
"""
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests" / "cdpr"))

from simkit import fast_cfg  # noqa: E402

from roomcleaner.cdpr.calibration import IDS  # noqa: E402
from roomcleaner.cdpr.sim.harness import SimRobot  # noqa: E402
from roomcleaner.cdpr.sim.world import FloorBoard  # noqa: E402
from roomcleaner.cdpr.supervisor import Supervisor  # noqa: E402
from roomcleaner.cdpr.vision.board import DEFAULT_PITCH_M, FloorBoardLayout  # noqa: E402

EDGE = 0.150


def truth_layout(seed, err=0.015, yaw=0.1, pitch=DEFAULT_PITCH_M):
    """The sheets as a user lays them: the nominal grid with ``err`` m of sloppiness per axis and ``yaw`` rad of rotation."""
    rng = np.random.default_rng(seed + 55)
    lay = FloorBoardLayout.nominal(EDGE, pitch)
    for i in range(1, 9):
        x, y, _ = lay.pose(i)
        lay.set_pose(i, x + rng.normal(0, err), y + rng.normal(0, err), rng.normal(0, yaw))
    return lay


def main(mode, seed, probe=True):
    cfg = fast_cfg(**{"startup.slack_probe": probe, "marker.edge_m": EDGE})
    t0 = time.time()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        if mode == "survey":
            r = SimRobot(cfg, seed=seed, data_dir=td, board_truth=truth_layout(seed), board_path=td / "layout.json")
        else:
            r = SimRobot(cfg, seed=seed, data_dir=td, camera_kw={"board": FloorBoard.nominal(EDGE)})
        sup = Supervisor(r.ctx, state_path=td / "state.json", ledger_path=td / "ledger.json")
        out = dict(mode=mode, seed=seed)
        try:
            rep = sup.start()
        except Exception as ex:                       # a startup abort is a result
            return dict(out, error=f"{type(ex).__name__}: {ex}"[:300])
        m = rep.measurements
        out.update(state=sup.state, complete=rep.outcome == "READY", trust=r.ctx.ledger.level, reasons=[x[:160] for x in rep.reasons][:3],
                   floor_tags_in_view=m.get("floor_tags_in_view"), board_survey=m.get("board_survey"), rocking_check=m.get("rocking_check"))
        if "absolute_sigma_m" in m:
            sig = np.asarray(m["absolute_sigma_m"]) * 1e3
            err = np.array([r.ctx.model.maps[s].L0 - r.world.true_L0(s) for s in IDS]) * 1e3
            out["sigma_abs_max_mm"] = float(sig.max())
            out["L0_err_max_mm"] = float(np.abs(err).max())
        if r.board_layout is not None:
            out["final_surveyed"] = r.board_layout.surveyed_ids()
        out["time_s"] = time.time() - t0
        return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1], int(sys.argv[2]), probe="noprobe" not in sys.argv[3:]), default=str))
