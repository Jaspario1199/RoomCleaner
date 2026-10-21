"""Floor-board survey inside the startup (verification/imu_removal_review.md R6; docs/CONTROL_SYSTEM_V1.md 3.2).

The printed layout page tells the user that exact placement of the nine sheets does not matter because the robot surveys
the layout. This module is that survey: at SELF_CHECK, with the claw resting still on the floor over the sheets, every frame
of the floor camera is given to :class:`vision.board.BoardSurvey` (tag 0 defines the frame; each other tag is placed by its
corner rays on the floor plane and refined by a planar bundle adjustment over all frames), and the layout file
(``marker.board_layout_file``) is updated in place. The detector shares the layout object, so the board pose of every later
frame (floor stage, mount offset, suspended poses) already uses what was just surveyed.

Two stages (both write the layout file when something changed):

1. SELF_CHECK, on the floor (:meth:`FloorBoardSurveyor.run`): it surveys the sheets the RESTING claw sees (the camera is ~0.52 m up:
   sheet 0 and about 2-3 neighbours of the nine, at any rest heading). A sheet surveyed earlier that is in view again is CHECKED: the
   detector's consistency check / the bundle adjustment flag one that moved by more than a few mm, it is cleared and surveyed afresh
   in the same startup (a moved origin sheet clears all the others); a sheet that is not in view is trusted as saved.
2. While the claw hangs (:meth:`offer` from every suspended still window, :meth:`flush` at each calibration sample): the sheets that
   the resting claw could not see come into view as the claw rises and moves; their still frames (thinned, <= ``max_pending``) are
   given to the survey, and a sheet is accepted once it has >= 8 views with a camera pose from surveyed sheets and passes the survey's
   consistency checks. Simulation (verification/board_followups_results.md): all nine sheets known by the end of calibration, and the
   startup as good as with the layout known in advance. No survey flight: nothing is moved for the survey. Cost: a few PnP solves per
   flush and a bundle adjustment (~1 s) when a sheet is ready; on hardware that is time in which the keep-alive is not pumped.

Limits: a sheet that is never seen clearly stays unsurveyed and unused (reported in ``measurements["board_survey"]``); a sheet that
moves during a run is not re-surveyed until the next startup; the survey needs the claw and the board still and a flat floor. It never
aborts the startup because a sheet is missing; it aborts only when the layout cannot be the board that was printed (its tag size is not
the measured ``marker.edge_m``).
"""
from __future__ import annotations

import math
import shutil
from pathlib import Path

import numpy as np

from .vision.board import BoardGeometry, BoardSurvey, FloorBoardLayout

# the layout's tag size and the measured ``marker.edge_m`` are the same ruler; more than this apart and the survey (whose
# own size test is 1.2 %) would reject every sheet or, worse, place them on a wrong scale
EDGE_TOL_REL = 0.005


def edge_mismatch(layout: FloorBoardLayout, edge_m: float | None) -> str | None:
    """Message if the layout's tag edge differs from the measured ``marker.edge_m`` by more than :data:`EDGE_TOL_REL`."""
    if edge_m is None or edge_m <= 0:
        return None
    rel = abs(layout.edge_m - edge_m) / edge_m
    if rel <= EDGE_TOL_REL:
        return None
    return (f"floor board layout edge_m {layout.edge_m * 1e3:.2f} mm differs from marker.edge_m {edge_m * 1e3:.2f} mm "
            f"by {rel * 100:.1f} % (limit {EDGE_TOL_REL * 100:.1f} %): the printed tags are the only ruler of the system, "
            "so both must be the measured black-square edge of sheet 0; fix one of them (a layout that was already "
            "surveyed at another edge cannot be reused)")


def adopt_edge(layout: FloorBoardLayout, edge_m: float | None) -> str | None:
    """Make an UNSURVEYED layout (only the origin tag) use the measured ``marker.edge_m``; a surveyed one that disagrees is a
    mismatch. Returns the mismatch message, or None. Must be called before the detector is built from the layout."""
    msg = edge_mismatch(layout, edge_m)
    if msg is None:
        return None
    if len(layout.surveyed_ids()) <= 1:                      # nothing surveyed yet: the template takes the measured size
        layout.edge_m = float(edge_m)
        return None
    return msg


class FloorBoardSurveyor:
    """Runs a :class:`BoardSurvey` over the live layout during the startup and keeps the layout file current.

    ``layout`` is the object the board detector uses (shared, updated in place). ``path``: where the layout is saved after a
    change (None: not saved). ``corner_sigma_px``: the corner noise of the detector (``camera.corner_sigma_px``); the survey's
    consistency limits scale with it."""

    def __init__(self, layout: FloorBoardLayout, camera, *, path=None, corner_sigma_px: float = 0.3,
                 min_side_px: float = 40.0, border_px: int = 4, log=print):
        self.layout = layout
        self.camera = camera
        self.path = None if path is None else Path(path)
        self.log = log
        self._kw = dict(pixel_sigma=float(corner_sigma_px), min_side_px=min_side_px, border_px=border_px)
        self.survey = BoardSurvey(layout, camera, **self._kw)
        self._backed_up = False
        self._pending: list = []                 # thinned still frames of suspended poses that show a sheet not surveyed yet
        self._last_offer_us = None
        self.max_pending = 60
        self.min_gap_us = 3.0e5

    # ------------------------------------------------------------ top-up
    def offer(self, frames) -> int:
        """Keep (thinned, at most ``max_pending``) the frames of a still window that show a sheet of the layout that is not
        surveyed yet and not rejected: they are used by :meth:`flush` at a safe moment. Cheap; called for every still window."""
        lay, kept = self.layout, 0
        for o in frames or ():
            dets = getattr(o, "dets", None)
            if not dets or len(self._pending) >= self.max_pending:
                continue
            want = [i for i in dets if i in lay.tags and not lay.is_surveyed(i) and self.survey._stat[i].state != "rejected"]
            t = getattr(o, "t_us", None)
            if not want or t is None or (self._last_offer_us is not None and abs(t - self._last_offer_us) < self.min_gap_us):
                continue
            self._pending.append((dets, tuple(getattr(o, "duplicate_ids", ()) or ()), t))
            self._last_offer_us = t
            kept += 1
        return kept

    def flush(self) -> dict | None:
        """Give the offered frames to the survey and accept what now satisfies its criteria (>= 8 views with a camera pose from
        surveyed tags, consistent, right size, sigma <= 2 mm); returns {"frames", "new", "cleared"} or None when nothing was
        pending. Runs a bundle adjustment only if a sheet is ready, so it is usually cheap; call it while the claw is held still."""
        if not self._pending:
            return None
        lay = self.layout
        before = set(lay.surveyed_ids())
        n = len(self._pending)
        for dets, dups, t in self._pending:
            self.survey.add_detections(dets, duplicate_ids=dups, update=False, frame_id=t)
        self._pending.clear()
        self.survey.update()
        new = sorted(set(lay.surveyed_ids()) - before)
        cleared = {}
        if new:
            self.survey.refine()
        for i, st in self.survey.status().items():
            if st.state == "suspect" and i != lay.origin_id and lay.is_surveyed(i):
                cleared[i] = st.reason
                self.survey.reset_tag(i)
        if new or cleared:
            self.save()
        return {"frames": n, "new": new, "cleared": cleared}

    def report(self) -> dict:
        """Current state of the layout for the startup report."""
        lay = self.layout
        st = self.survey.status()
        surveyed = lay.surveyed_ids()
        sig = [lay.tags[i].sigma_xy_m for i in surveyed if i != lay.origin_id]
        return {"expected": len(lay.expected_ids), "surveyed_ids": surveyed,
                "unsurveyed": {int(i): (st[i].reason or st[i].state) for i in lay.expected_ids if i not in surveyed},
                "max_sigma_xy_m": max(sig) if sig else None}

    # -------------------------------------------------------------- frames
    def collect(self, vision, wait_s, *, n_frames: int, interval_s: float, max_wait_s: float) -> int:
        """Feed ``n_frames`` distinct frames of the floor camera (``vision.observe()``: ``PoseObs.dets``) to the survey; stop
        early after ``max_wait_s`` of waiting. Returns the number of frames given."""
        got, waited, last_t = 0, 0.0, None
        while got < n_frames and waited <= max_wait_s:
            o = vision.observe()
            if o.dets and o.t_us != last_t:                  # a new frame (a slow camera repeats the last one)
                last_t = o.t_us
                self.survey.add_detections(o.dets, duplicate_ids=o.duplicate_ids, update=False, frame_id=o.t_us)
                got += 1
            wait_s(interval_s)
            waited += interval_s
        return got

    # ------------------------------------------------------------------ run
    def run(self, vision, wait_s, *, n_frames: int, interval_s: float, max_wait_s: float | None = None,
            edge_m: float | None = None) -> dict:
        """Survey, verify and (if anything changed) save. Returns a JSON-friendly summary for the startup report."""
        lay = self.layout
        msg = edge_mismatch(lay, edge_m)
        if msg is not None:
            raise ValueError(msg)
        max_wait_s = max_wait_s if max_wait_s is not None else max(10.0, 4 * n_frames * interval_s)
        before = set(lay.surveyed_ids())
        poses0 = {i: lay.pose(i) for i in before}
        cleared: dict = {}
        frames = 0
        for rnd in range(2):
            frames += self.collect(vision, wait_s, n_frames=n_frames, interval_s=interval_s, max_wait_s=max_wait_s)
            self.survey.finalize()
            st = self.survey.status()
            bad = [i for i, s in st.items() if s.state == "suspect"]
            if not bad or rnd == 1:
                break
            # a sheet that moved since it was surveyed (or a moved origin: then everything is re-established around it)
            reset = [i for i in lay.surveyed_ids() if i != lay.origin_id] if lay.origin_id in bad else \
                [i for i in bad if i != lay.origin_id]
            for i in reset:
                cleared[i] = st[i].reason or "moved since it was surveyed"
                self.survey.reset_tag(i)
            self.log(f"[startup] floor board: sheet(s) {sorted(reset)} moved since the last survey, surveying them again")
        # a tag still 'suspect' after the second round is not used either: take it out of the layout
        for i, s in self.survey.status().items():
            if s.state == "suspect" and i != lay.origin_id and lay.is_surveyed(i):
                cleared.setdefault(i, s.reason)
                self.survey.reset_tag(i)
        after = set(lay.surveyed_ids())
        status = self.survey.status()
        unsurveyed = {i: (status[i].reason or status[i].state) for i in lay.expected_ids if i not in after}
        sig = [lay.tags[i].sigma_xy_m for i in after if i != lay.origin_id]
        out = {"expected": len(lay.expected_ids), "surveyed_ids": sorted(after), "newly_surveyed": sorted(after - before),
               "cleared": {int(k): v for k, v in cleared.items()}, "unsurveyed": {int(k): v for k, v in unsurveyed.items()},
               "frames": frames, "max_sigma_xy_m": max(sig) if sig else None,
               "warnings": list(self.survey.warnings)}
        so = status[lay.origin_id]
        if so.state == "suspect":
            out["warnings"].append(f"origin sheet {lay.origin_id}: {so.reason}")
        # the file is rewritten only for a real change: a tag added or cleared, or one that moved by more than the survey's own
        # accuracy (a re-estimate from one more static view is not a reason to churn the file)
        moved = any(math.hypot(lay.pose(i)[0] - poses0[i][0], lay.pose(i)[1] - poses0[i][1]) > 1e-3
                    or abs(float(np.angle(np.exp(1j * (lay.pose(i)[2] - poses0[i][2]))))) > 2e-3
                    for i in after & before)
        out["saved"] = self.save() if (cleared or after != before or moved) else None
        return out

    # ----------------------------------------------------------------- file
    def save(self) -> str | None:
        """Write the layout back to its file (atomically; the file as it was before this process first changed it is kept as
        ``<name>.bak``). A file that cannot be written is reported, not fatal: the survey is repeated at the next startup."""
        if self.path is None:
            return None
        from .trust import atomic_write
        try:
            if not self._backed_up and self.path.exists():
                shutil.copyfile(self.path, self.path.with_name(self.path.name + ".bak"))
                self._backed_up = True
            import json
            atomic_write(self.path, json.dumps(self.layout.to_dict(), indent=2))
        except OSError as e:
            self.log(f"[startup] floor board: could not save {self.path}: {e} (the survey will be repeated at the next startup)")
            return None
        return str(self.path)

    def geometry(self) -> BoardGeometry:
        """Visibility / span queries of the tags surveyed so far (the excitation design's view of the board)."""
        return BoardGeometry.from_layout(self.layout)
