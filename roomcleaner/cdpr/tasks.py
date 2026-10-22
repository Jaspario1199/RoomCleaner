"""Pickup-and-delivery tasks with visual verification.

Workflow per item (each step bounded; failures are counted, never ignored):

SCAN                  claw at scan height; perception lists candidate items.
APPROACH              move above the item (lowest point ``approach_clearance``
                      above it) inside the trusted volume.
GRIP                  settle, then approve on the host (D27: the claw has no IMU
                      and no tilt gate): wait until the claw is still (camera-
                      observed motion below a rate for N frames; with no camera
                      motion signal, a dwell of k pendulum periods), then require
                      the tilt (vision when the floor reference is in view, and
                      the cable model's predicted R_at at the hover and the grip
                      pose) <= grip_tilt_max; descend vertically, close.
PICKUP_VERIFICATION   lift back to approach height; perception must confirm
                      the item is held (and the floor spot is empty). Else
                      open, retry up to ``max_grip_attempts``.
TRANSPORT             move over the hamper at transport height, planned with
                      the claw mass + max payload.
RELEASE               descend to release height, open.
DELIVERY_VERIFICATION perception must confirm the claw is empty and the item
                      is in the hamper. Else count a failure.

``max_consecutive_failures`` failed items -> the task pauses for the operator.

Trusted volume: VERIFIED -> the configured workspace; LOCAL_ONLY -> the
validated calibration volume (convex hull), plus straight vertical descents
below it to the floor for gripping.

Reach (refused before any motion, never discovered half-way through an item):
  * the first scan is planned above the claw if that point is in the trusted volume, else above the claw's start point
    (``SystemConfig.start_point_xy``), else above the centroid of the trusted volume; none allowed -> the task is refused;
  * the hamper's transport / release pose must be in the trusted volume, else the task is refused with the hamper's position
    and the trusted extents;
  * an item whose approach or grip pose is outside the trusted volume or not plannable (workspace, tension) is recorded as
    failed ("unreachable: ...") and skipped; so is an item whose CARRY to the hamper (lift, verify shift, raise, transport, with the
    payload mass) is refused when dry-run planned before the claw moves towards it. Motion faults and pauses still abort, and so does
    a planning refusal after the grip closed (it can no longer happen for the poses the dry run covers).

Keep-alive: while a task owns the robot the idle host loop does not pump the stations (``Service.idle_tick``), so anything
slower than a fraction of ``faults.lease_s`` on the command thread would latch Fault.LEASE. The path check of a planned move
(a tension solve at every path point, both ways) runs through ``startup.run_pumped``; the garment detector does too
(garments.py), and so do the claw's blocking HTTP calls (grip, frame grab) when the claw link says it does blocking I/O
(``claw.blocking_io``, claw_link.HttpClawClient; the simulator's claw is called directly). Settle waits go through ``ctx.wait``,
which pumps.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from .attitude import estimate_attitude, predicted_tilt_rad, wait_until_still
from .startup import StartupAbort, run_pumped
from .trajectory import PlanError, plan_line, plan_line_from

TASK_STATES = ("SCAN", "APPROACH", "GRIP", "PICKUP_VERIFICATION", "TRANSPORT", "RELEASE",
               "DELIVERY_VERIFICATION")


class TaskUnreachable(StartupAbort):
    """A planning refusal that belongs to ONE target: it is outside the trusted volume, or its path leaves the workspace or needs
    more tension than the cables can give. ``TaskRunner.run`` records an item whose approach or grip raised this as failed
    ("unreachable") and goes on to the next; everywhere else (after the grip closed, hamper, scan) it aborts like any StartupAbort.
    Motion faults, pauses and a model that disagrees with the cables are plain ``StartupAbort`` and never skipped."""


# PlanError texts (trajectory._check_path) that mean "this target cannot be planned": the other PlanErrors (model and cables
# disagree, zero cable move, ...) say something about the system, not about the target.
_UNREACHABLE_PLAN = ("workspace:", "tension infeasible")


@dataclass
class ItemSighting:
    id: str
    xy: np.ndarray            # room frame
    height_m: float
    confidence: float


class ItemPerception:
    """Interface. The real implementation needs a garment detector on the claw
    camera (open item: docs/CONTROL_SYSTEM_V1.md); SimItemPerception is the
    simulator's."""

    def scan(self, ctx) -> list:
        raise NotImplementedError("garment detection is not implemented for hardware yet")

    def holding(self, ctx) -> tuple:
        raise NotImplementedError

    def item_at(self, ctx, xy, radius) -> bool:
        raise NotImplementedError


class TrustedVolume:
    def __init__(self, ctx):
        self.ctx = ctx
        self.hull = None
        pts = ctx.validated_volume
        if ctx.ledger.level != "VERIFIED" and pts is not None and len(pts) >= 5:
            from scipy.spatial import Delaunay
            from scipy.spatial import QhullError
            try:
                self.hull = Delaunay(np.asarray(pts))
            except QhullError:                       # flat/degenerate validated set: no trusted volume
                self.hull = None

    def extents(self):
        """(lo, hi) xyz bounds of the validated points of the hull, or None (VERIFIED: the workspace; no usable hull)."""
        if self.hull is None:
            return None
        pts = np.asarray(self.hull.points, float)
        return pts.min(axis=0), pts.max(axis=0)

    def extent_text(self) -> str:
        ext = self.extents()
        if ext is None:
            return "no validated volume"
        lo, hi = ext
        return f"x {lo[0]:.2f}-{hi[0]:.2f}, y {lo[1]:.2f}-{hi[1]:.2f}, z {lo[2]:.2f}-{hi[2]:.2f} m"

    def centroid_xy(self):
        """xy of the centroid of the hull (volume-weighted over its tetrahedra), or None without a hull."""
        if self.hull is None:
            return None
        pts = np.asarray(self.hull.points, float)
        tets = pts[self.hull.simplices]                              # (n, 4, 3)
        vol = np.abs(np.linalg.det(tets[:, 1:] - tets[:, :1])) / 6.0
        c = (tets.mean(axis=1) * vol[:, None]).sum(axis=0) / vol.sum() if vol.sum() > 1e-12 else pts.mean(axis=0)
        return c[:2]

    def allows(self, q, *, below_ok=False) -> bool:
        ctx = self.ctx
        if ctx.ws.violations(ctx.model.geometry, q, allow_low=below_ok):
            return False
        if ctx.ledger.level == "VERIFIED":
            return True
        if self.hull is None:
            return False
        if self.hull.find_simplex(np.asarray(q)) >= 0:
            return True
        if below_ok:                     # vertical descent below a validated point
            top = np.array([q[0], q[1], float(np.min(self.hull.points[:, 2])) + 1e-3])
            return bool(self.hull.find_simplex(top) >= 0)
        return False


class TaskRunner:
    def __init__(self, ctx, perception: ItemPerception):
        self.ctx = ctx
        self.cfg = ctx.cfg
        self.tc = ctx.cfg.tasks
        self.per = perception
        self.vol = TrustedVolume(ctx)
        self.zf = -float(ctx.cfg.claw.lowest_point_body_m[2])      # origin height when the claw rests
        self.log = []
        self.approvals = []           # one record per settle-and-approve (method, wait, tilt, source), for the report

    # -------------------------------------------------------------- motion
    def _move(self, q, *, label, below_ok=False, payload=0.0, slow=1.0):
        ctx = self.ctx
        zmax = self.cfg.motion.task_max_height_m
        if zmax is not None and q[2] > zmax + 1e-9:
            raise StartupAbort("TASK", f"{label}: target height {q[2]:.3f} m is above motion.task_max_height_m "
                                       f"({zmax:.2f} m): the task layer never plans above it (the claw's yaw is only "
                                       f"weakly held by the {'three' if len(self.cfg.ids) == 3 else 'four'} lines near the ceiling)")
        why = self._outside(q, label, below_ok)
        if why:
            raise TaskUnreachable("TASK", why)
        lim = self._limits(payload, slow)
        try:
            # The path check solves the cable tensions at every path point (both ways, with payload and dynamics): tens to
            # hundreds of ms for a task move. It runs on the pumped worker; the stations' positions are read here, on the
            # command thread, and passed in (the worker never touches the coordinator).
            plan = run_pumped(ctx, plan_line_from, ctx.model, ctx.co.positions(), q, lim, ws=ctx.ws, allow_low=below_ok,
                              label=label)
        except PlanError as e:
            raise (TaskUnreachable if str(e).startswith(_UNREACHABLE_PLAN) else StartupAbort)("TASK", f"{label}: {e}")
        r = ctx.co.execute(plan)
        if not r.ok:
            raise StartupAbort("TASK", f"{label}: {r.reason}", paused=r.reason.startswith("paused"))
        return r

    def _limits(self, payload=0.0, slow=1.0):
        ctx = self.ctx
        return replace(ctx.lim, mass_kg=self.cfg.claw.mass_kg + payload, cart_v=ctx.lim.cart_v * slow,
                       cable_v=ctx.lim.cable_v * slow)

    def _grip(self, close):
        """Open / close the claw. The real claw link does blocking HTTP (POST, 1 s timeout) that would outlast ``faults.lease_s`` on
        the command thread, so it runs through ``run_pumped`` when the link says so (``claw.blocking_io``); the simulator's claw
        (a call into the shared world) is called directly. The call touches only the claw link, never the coordinator."""
        claw = self.ctx.claw
        if getattr(claw, "blocking_io", False):
            return run_pumped(self.ctx, claw.grip, close)
        return claw.grip(close)

    def _carry_poses(self, above, hamper):
        """(shift, z_t): where the claw goes first with the garment (a short way toward the hamper, to confirm it moved WITH the claw)
        and the height it is carried and released at."""
        d = hamper - above[:2]
        shift = above.copy()
        if np.linalg.norm(d) > 1e-6:
            shift[:2] += d / np.linalg.norm(d) * min(self.tc.verify_shift_m, float(np.linalg.norm(d)))
        return shift, self._transport_z(above[2])

    def _dry_run_carry(self, item_id, above, grip_pose, hamper):
        """None, or why the garment at ``grip_pose`` cannot be carried to the hamper: lift, verify shift, raise and transport are
        PLANNED (not executed) with the payload mass through the same checks ``_move`` applies (task height limit, trusted volume,
        workspace and tension along the path). Done before the claw moves towards the item, so a refusal costs nothing and nothing
        is in the jaws. The planning runs on the pumped worker (it is a pure function of the model and the poses)."""
        ctx, tc = self.ctx, self.tc
        shift, z_t = self._carry_poses(above, hamper)
        raise_to = np.array([shift[0], shift[1], z_t])
        legs = ((f"lift {item_id}", grip_pose, above, True), (f"verify shift {item_id}", above, shift, False),
                (f"raise {item_id}", shift, raise_to, False),
                (f"transport {item_id}", raise_to, np.array([hamper[0], hamper[1], z_t]), False))
        zmax = self.cfg.motion.task_max_height_m
        for label, _a, b, below in legs:
            if zmax is not None and b[2] > zmax + 1e-9:
                return f"{label}: target height {b[2]:.3f} m is above motion.task_max_height_m ({zmax:.2f} m)"
            why = self._outside(b, label, below)
            if why:
                return why
        lim, model, ws = self._limits(tc.max_payload_kg), ctx.model, ctx.ws

        def plan_legs():
            for label, a, b, below in legs:
                try:
                    plan_line(model, a, b, lim, ws=ws, allow_low=below, label=label)
                except PlanError as e:
                    return f"{label}: {e}"
            return None
        return run_pumped(ctx, plan_legs)

    def _outside(self, q, label, below_ok=False):
        """None if the task layer may plan to ``q``, else the refusal text of ``_move`` (so that a pre-check and the move say the same)."""
        if self.vol.allows(q, below_ok=below_ok):
            return None
        return f"{label}: target {np.round(q, 3).tolist()} outside the trusted volume"

    def _here(self):
        return self.ctx.model.pose_from_positions(self.ctx.co.positions())[0]

    def _transport_z(self, above_z):
        """Height at which an item is carried to the hamper and released: over the rim with the release clearance, but not below
        the approach height of the item."""
        return max(above_z, self.zf + self.tc.hamper_height_m + self.tc.release_clearance_m)

    def _scan_point(self, here):
        """(point, note): where the next scan is planned. Above the claw if that is in the trusted volume (note ""); else above the
        claw's start point (``cfg.start_point_xy``), else above the centroid of the trusted volume. The startup ends wherever its
        last calibration pose left the claw, and that can be outside the volume it validated. None allowed: the task is refused
        before any motion (paused: nothing was moved, the operator can resume)."""
        z = self.tc.scan_height_m
        cands = [("above the claw", np.asarray(here[:2], float)),
                 ("above the claw's start point", np.asarray(self.cfg.start_point_xy(), float))]
        cen = self.vol.centroid_xy()
        if cen is not None:
            cands.append(("above the centre of the calibrated volume", cen))
        tried = []
        for k, (what, xy) in enumerate(cands):
            q = np.array([xy[0], xy[1], z])
            if self.vol.allows(q):
                note = "" if k == 0 else (f"scan from {what} ({xy[0]:.2f}, {xy[1]:.2f}): the claw's own position "
                                          f"({here[0]:.2f}, {here[1]:.2f}) is outside the trusted volume at {z:.2f} m")
                return q, note
            tried.append(f"{what} ({xy[0]:.2f}, {xy[1]:.2f})")
        raise StartupAbort("TASK", f"scan: no point at the scan height {z:.2f} m is inside the trusted volume ({'; '.join(tried)}; "
                                   f"{self.vol.extent_text()}): nothing was moved", paused=True)

    def _check_hamper(self, hamper):
        """Refuse the task before any motion if the hamper's transport pose (``_handle`` also releases there) is not allowed:
        outside the trusted volume or above ``motion.task_max_height_m``. Otherwise the claw would pick an item up and fail at
        TRANSPORT with the garment in its jaws."""
        z = self._transport_z(0.0)                     # the lowest height an item is carried at (taller items only go higher)
        q = np.array([hamper[0], hamper[1], z])
        zmax = self.cfg.motion.task_max_height_m
        sx, sy = np.asarray(self.cfg.start_point_xy(), float)[:2]
        where = f"hamper at ({hamper[0]:.2f}, {hamper[1]:.2f})"
        if zmax is not None and z > zmax + 1e-9:
            raise StartupAbort("TASK", f"{where}: the transport height {z:.2f} m is above motion.task_max_height_m ({zmax:.2f} m): "
                                       "nothing was moved", paused=True)
        if self.vol.allows(q):
            return
        if self.ctx.ledger.level == "VERIFIED":
            v = self.ctx.ws.violations(self.ctx.model.geometry, q, allow_low=False)
            what = f"outside the workspace ({'; '.join(v)})"
        elif self.vol.hull is None:
            what = "outside the calibrated volume (there are no validated points)"
        else:
            what = f"outside the calibrated volume ({self.vol.extent_text()})"
        raise StartupAbort("TASK", f"{where} is {what} at the transport height {z:.2f} m: move it toward the middle of the "
                                   f"calibrated area (the claw's start point is ({sx:.2f}, {sy:.2f})); nothing was moved",
                           paused=True)

    def _settle_and_approve(self, what, target=None, payload_kg=0.0):
        """Wait until the claw is still, then approve on the host. Returns (ok, why). ``target``: the pose the claw
        will go to next (the grip pose); its predicted tilt is checked too. Tilt now: vision when the floor reference
        is in view, else the cable model's static tilt; the predicted tilt (R_at) at the current and target pose must
        also be within ``claw.grip_tilt_max_rad``. ``payload_kg``: mass in the jaws (a release): the full dwell of the
        loaded pendulum is applied (attitude.wait_until_still)."""
        ctx = self.ctx
        lim = self.cfg.claw.grip_tilt_max_rad
        res = wait_until_still(ctx, payload_kg=payload_kg)
        rec = dict(what=what, method=res.method, waited_s=round(res.waited_s, 2), still_ok=res.ok, payload_kg=payload_kg)
        self.approvals.append(rec)
        if not res.ok:
            return False, f"claw would not settle ({res.reason})"
        here = self._here()
        geo = ctx.model.geometry
        est = estimate_attitude(ctx, here)
        pred = max(predicted_tilt_rad(geo, here), predicted_tilt_rad(geo, target) if target is not None else 0.0)
        rec.update(source=est.source, tilt_deg=round(math.degrees(est.tilt_rad), 2),
                   sigma_deg=round(math.degrees(est.sigma_rad), 2), predicted_tilt_deg=round(math.degrees(pred), 2))
        if est.tilt_rad > lim:
            return False, f"{est.source} tilt {math.degrees(est.tilt_rad):.1f} deg > {math.degrees(lim):.1f} deg"
        if pred > lim:
            return False, f"predicted tilt {math.degrees(pred):.1f} deg (cable model) > {math.degrees(lim):.1f} deg"
        rec["approved"] = True
        return True, ""

    # -------------------------------------------------------------- run
    def run(self, *, on_state=lambda s, m="": None, max_items=10):
        ctx, tc = self.ctx, self.tc
        if tc.hamper_room_m is None:
            raise StartupAbort("TASK", "tasks.hamper_room_m not configured")
        hamper = np.asarray(tc.hamper_room_m, float)
        self._check_hamper(hamper)                 # before any motion: not after the grip, at TRANSPORT
        done, failed, consecutive = [], [], 0
        skip = set()
        for _ in range(max_items):
            on_state("SCAN")
            here = self._here()
            scan, note = self._scan_point(here)
            if note:
                self.log.append(note)
                on_state("SCAN", note)
            self._move(scan, label="scan")
            ctx.wait(self.cfg.startup.settle_s)
            items = [it for it in self.per.scan(ctx) if it.id not in skip]
            if not items:
                return {"done": done, "failed": failed, "summary": f"{len(done)} delivered, room clear"}
            items.sort(key=lambda it: np.linalg.norm(it.xy - scan[:2]))
            item = items[0]
            ok, why = self._handle(item, hamper, on_state)
            if ok:
                done.append(item.id)
                consecutive = 0
            else:
                failed.append((item.id, why))
                skip.add(item.id)
                consecutive += 1
                if consecutive >= tc.max_consecutive_failures:
                    return {"done": done, "failed": failed,
                            "pause": f"{consecutive} consecutive failures (last: {why})"}
        return {"done": done, "failed": failed, "summary": f"{len(done)} delivered (item limit)"}

    def _handle(self, item, hamper, on_state):
        ctx, tc = self.ctx, self.tc
        above = np.array([item.xy[0], item.xy[1], self.zf + item.height_m + tc.approach_clearance_m])
        for attempt in range(1, tc.max_grip_attempts + 1):
            on_state("APPROACH", f"{item.id} attempt {attempt}")
            grip_pose = np.array([item.xy[0], item.xy[1], self.zf + tc.grip_clearance_m])
            # An item whose approach or grip pose is outside the trusted volume, or that cannot be planned to, is failed as
            # unreachable (nothing is in the jaws yet) and the run goes on; checked before the claw moves at all.
            for q, label, below in ((above, f"approach {item.id}", False), (grip_pose, f"descend {item.id}", True)):
                why = self._outside(q, label, below)
                if why:
                    return False, f"unreachable: {why}"
            # ... and so is an item that could be gripped but not carried to the hamper (the planning refusal would otherwise come
            # after the jaws have closed, with the garment in the air): the carry legs are dry-run planned with the payload mass
            why = self._dry_run_carry(item.id, above, grip_pose, hamper)
            if why:
                self.log.append(f"{item.id}: carry not plannable: {why}")
                return False, f"unreachable: {why}"
            try:
                self._move(above, label=f"approach {item.id}")
            except TaskUnreachable as e:
                return False, f"unreachable: {e.reason}"
            on_state("GRIP", item.id)
            self._grip(False)
            ok, why = self._settle_and_approve(f"grip {item.id}", grip_pose)
            if not ok:
                return False, f"grip not approved: {why}"
            if hasattr(self.per, "note_target"):
                self.per.note_target(item)
            try:
                self._move(grip_pose, below_ok=True,
                           label=f"descend {item.id}", slow=0.3)    # slow near the object
            except TaskUnreachable as e:                            # the jaws are still open and empty: skip the item
                return False, f"unreachable: {e.reason}"
            self._grip(True)
            ctx.wait(tc.grip_settle_s)
            self._move(above, label=f"lift {item.id}", payload=tc.max_payload_kg, below_ok=True)
            # handoff: move a short way toward the destination, then confirm the
            # garment moved WITH the claw (its old spot is no longer under the jaws)
            shift, _z_t = self._carry_poses(above, hamper)
            self._move(shift, label=f"verify shift {item.id}", payload=tc.max_payload_kg)
            on_state("PICKUP_VERIFICATION", item.id)
            held, conf = self.per.holding(ctx)
            if held:
                break
            self._grip(False)
            ctx.wait(tc.grip_settle_s)
            self._move(above, label=f"back over {item.id}")
            # re-locate the item before the next attempt (it may have been nudged)
            seen = [s for s in self.per.scan(ctx) if s.id == item.id]
            if not seen:
                return False, "item lost after a failed grip"
            item = seen[0]
            above = np.array([item.xy[0], item.xy[1], self.zf + item.height_m + tc.approach_clearance_m])
        else:
            return False, f"not held after {tc.max_grip_attempts} attempts"
        on_state("TRANSPORT", item.id)
        here = self._here()
        z_t = self._transport_z(above[2])
        self._move(np.array([here[0], here[1], z_t]), label="raise", payload=tc.max_payload_kg)
        self._move(np.array([hamper[0], hamper[1], z_t]), label="transport", payload=tc.max_payload_kg)
        on_state("RELEASE", item.id)
        ok, why = self._settle_and_approve(f"release {item.id}", payload_kg=tc.max_payload_kg)
        if not ok:       # the garment is still in the closed jaws: stop over the hamper, never carry it on (task verification F2)
            raise StartupAbort("TASK", f"release {item.id} not approved: {why}; the item is still in the jaws over the hamper",
                               paused=True)
        self._grip(False)
        ctx.wait(tc.grip_settle_s)
        on_state("DELIVERY_VERIFICATION", item.id)
        held, _ = self.per.holding(ctx)
        if held:
            return False, "item still in the claw after release"
        if not self.per.item_at(ctx, hamper, tc.hamper_radius_m):
            return False, "item not seen in the hamper"
        return True, "delivered"


# --------------------------------------------------------------- simulation
class SimItemPerception(ItemPerception):
    """Truth-based perception with a camera footprint, position noise and a
    miss probability, for exercising the workflow logic."""

    def __init__(self, world, *, noise_m=0.01, miss=0.0, seed=0):
        self.w = world
        self.noise = noise_m
        self.miss = miss
        self.rng = np.random.default_rng(seed)

    def scan(self, ctx):
        out = []
        cam_xy = self.w.p[:2]
        h = self.w.p[2]
        half = h * 300 / 520                      # rough footprint half-width at the floor
        for it in self.w.items:
            if it["state"] != "floor":
                continue
            if np.max(np.abs(it["xy"] - cam_xy)) > half or self.rng.random() < self.miss:
                continue
            out.append(ItemSighting(it["id"], it["xy"] + self.rng.normal(0, self.noise, 2), it["height"], 0.9))
        return out

    def holding(self, ctx):
        return (self.w.held is not None), 0.95

    def item_at(self, ctx, xy, radius):
        return any(it["state"] == "hamper" for it in self.w.items if it.get("last_drop") is not None
                   and np.linalg.norm(it["last_drop"] - np.asarray(xy)) <= radius)
