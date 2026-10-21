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
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from .attitude import estimate_attitude, predicted_tilt_rad, wait_until_still
from .startup import StartupAbort
from .trajectory import PlanError, plan_line_from

TASK_STATES = ("SCAN", "APPROACH", "GRIP", "PICKUP_VERIFICATION", "TRANSPORT", "RELEASE",
               "DELIVERY_VERIFICATION")


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
        if not self.vol.allows(q, below_ok=below_ok):
            raise StartupAbort("TASK", f"{label}: target {np.round(q, 3).tolist()} outside the trusted volume")
        lim = replace(ctx.lim, mass_kg=self.cfg.claw.mass_kg + payload, cart_v=ctx.lim.cart_v * slow,
                      cable_v=ctx.lim.cable_v * slow)
        try:
            plan = plan_line_from(ctx.model, ctx.co.positions(), q, lim, ws=ctx.ws, allow_low=below_ok,
                                  label=label)
        except PlanError as e:
            raise StartupAbort("TASK", f"{label}: {e}")
        r = ctx.co.execute(plan)
        if not r.ok:
            raise StartupAbort("TASK", f"{label}: {r.reason}", paused=r.reason.startswith("paused"))
        return r

    def _here(self):
        return self.ctx.model.pose_from_positions(self.ctx.co.positions())[0]

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
        done, failed, consecutive = [], [], 0
        skip = set()
        for _ in range(max_items):
            on_state("SCAN")
            here = self._here()
            scan = np.array([here[0], here[1], tc.scan_height_m])
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
            self._move(above, label=f"approach {item.id}")
            on_state("GRIP", item.id)
            ctx.claw.grip(False)
            grip_pose = np.array([item.xy[0], item.xy[1], self.zf + tc.grip_clearance_m])
            ok, why = self._settle_and_approve(f"grip {item.id}", grip_pose)
            if not ok:
                return False, f"grip not approved: {why}"
            if hasattr(self.per, "note_target"):
                self.per.note_target(item)
            self._move(grip_pose, below_ok=True,
                       label=f"descend {item.id}", slow=0.3)        # slow near the object
            ctx.claw.grip(True)
            ctx.wait(tc.grip_settle_s)
            self._move(above, label=f"lift {item.id}", payload=tc.max_payload_kg, below_ok=True)
            # handoff: move a short way toward the destination, then confirm the
            # garment moved WITH the claw (its old spot is no longer under the jaws)
            d = hamper - above[:2]
            shift = above.copy()
            if np.linalg.norm(d) > 1e-6:
                shift[:2] += d / np.linalg.norm(d) * min(tc.verify_shift_m, float(np.linalg.norm(d)))
            self._move(shift, label=f"verify shift {item.id}", payload=tc.max_payload_kg)
            on_state("PICKUP_VERIFICATION", item.id)
            held, conf = self.per.holding(ctx)
            if held:
                break
            ctx.claw.grip(False)
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
        z_t = max(above[2], self.zf + tc.hamper_height_m + tc.release_clearance_m)
        self._move(np.array([here[0], here[1], z_t]), label="raise", payload=tc.max_payload_kg)
        self._move(np.array([hamper[0], hamper[1], z_t]), label="transport", payload=tc.max_payload_kg)
        on_state("RELEASE", item.id)
        ok, why = self._settle_and_approve(f"release {item.id}", payload_kg=tc.max_payload_kg)
        if not ok:
            return False, f"release not approved: {why}"
        ctx.claw.grip(False)
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
