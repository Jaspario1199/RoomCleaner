"""What the robot is entitled to believe after faults, reboots and restarts.

Every length reference (``L0``: external cable length at motor position 0)
belongs to one station *boot epoch*. The AS5600 is absolute only within a
turn and step counts restart at power-up, so a reboot destroys the epoch.
Room geometry (anchors in the room frame, marker registration) survives
station resets but not a moved marker or a changed camera calibration.

Rules (also tabulated in docs/CONTROL_SYSTEM_V1.md):

=======================  =====================  ==================  ===============
event                    station references     room geometry       level after
=======================  =====================  ==================  ===============
coordinated stop         kept                   kept                unchanged
(pause/lease/underrun/
 peer hold)
tracking / encoder fault that station invalid   kept                RECOVERY
unexpected bead switch   that station suspect   kept                RECOVERY
station reboot           that station lost      kept                RECOVERY
host restart             kept only if every     kept                restored or
                         boot id matches and                        RECOVERY
                         no fault since
whole-system power loss  all lost, claw pose    kept                NONE (floor
                         unknown (may have                          restart)
                         dropped)
marker moved / missing   kept                   marker invalid      LOCAL_ONLY until
                                                                    re-registered
camera calibration       kept                   visual products     NONE for vision
changed                                         invalid
=======================  =====================  ==================  ===============

Levels: NONE (no usable model) < LOCAL_ONLY (visual fit near the start
region; tasks stay inside the validated calibration hull) < VERIFIED
(full-workspace operation).

VERIFIED has a recorded *basis* (decision D26, docs/CONTROL_SYSTEM_V1.md 5/6):

* ``"margin"``: the calibration was accepted, the slack probe was on for the
  suspended samples with a consistent witness chi-squared, and k*sigma of the
  claw position relative to each protected boundary is within the ceiling /
  wall margin everywhere in the commanded workspace (``margin_check`` holds
  the numbers);
* ``"beads"``: every bead reference was found and verified (D24 gating).

It is re-decided at every startup; any event below that drops the level also
clears the basis. ``trust_reasons`` holds plain-language reasons for a level
below VERIFIED.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .protocol import Fault

LEVELS = ("NONE", "LOCAL_ONLY", "VERIFIED")


def tracking_fault_detail(tel, counts_per_rev, radius_m):
    """What a station's tracking error says about its TRACKING fault, in words (message text only; no decision uses it).

    ``tel`` is the station's latest telemetry (``terr`` = measured - expected spool angle in encoder counts, + = payout,
    see ``station_core._check_tracking``); ``radius_m`` is the radius the line leaves the spool at. The encoder is on the
    SPOOL, so a spool that turned toward payout beyond the command means the line pulled harder than the motor holds
    (design intent of calculations/lift_chain_weakest_link.py: the motor is the weakest link); the other sign is a jam
    or a slipping spool. Returns None when there is no usable ``terr`` (no telemetry, missing, not finite, or exactly 0,
    which has no direction): the caller then keeps its plain wording."""
    terr = (tel or {}).get("terr")
    if isinstance(terr, bool) or not isinstance(terr, (int, float)) or not math.isfinite(terr) or terr == 0:
        return None
    turns = abs(terr) / counts_per_rev
    deg, mm = 360.0 * turns, 2e3 * math.pi * radius_m * turns
    if terr > 0:
        return (f"overload: spool turned {deg:.0f} deg ({mm:.1f} mm of line) toward payout beyond the command; "
                "the line pulled harder than the motor holds (motor skipped or spool slipped on the shaft)")
    return (f"spool turned {deg:.0f} deg ({mm:.1f} mm of line) less than commanded toward payout "
            "(jam, or spool slipping on the shaft)")


def atomic_write(path, text: str) -> None:
    import os
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    with open(tmp, "w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)


@dataclass
class StationTrust:
    boot: int | None = None
    L0: float | None = None
    L0_sigma: float | None = None
    source: str | None = None          # visual | bead | onset | restored
    bead_verified: bool = False
    valid: bool = False
    note: str = ""


@dataclass
class TrustLedger:
    """What the robot may believe, per ACTIVE station. The default is all four stations (A-D); three-station mode builds
    the ledger with ``TrustLedger.for_ids(cfg.ids)``, so an inactive station has no entry: it can neither be invalid nor
    block the level, and it never shows up in the status."""
    stations: dict = field(default_factory=lambda: {s: StationTrust() for s in "ABCD"})
    anchors_room: list | None = None   # (n_active)x3
    anchors_sigma: list | None = None
    T_R_M: list | None = None          # marker registration (4x4)
    marker_valid: bool = False
    camera_calibration_id: str | None = None
    level: str = "NONE"
    verified_basis: str | None = None  # "margin" | "beads" while level == VERIFIED, else None
    margin_check: dict | None = None   # numbers behind the last margin decision (k, sigma, margins, worst pose)
    trust_reasons: list = field(default_factory=list)   # plain reasons the level is below VERIFIED
    recovery_required: bool = False
    claw_supported: bool = False       # FAIL CLOSED: unknown means "may be hanging"; set True only by
                                       # a vision floor check, False before the first lift command
    history: list = field(default_factory=list)

    @classmethod
    def for_ids(cls, ids) -> "TrustLedger":
        """A fresh ledger over exactly the stations ``ids`` (the active ones)."""
        return cls(stations={s: StationTrust() for s in ids})

    def restrict_to(self, ids) -> bool:
        """Make the ledger cover exactly ``ids`` (a ledger saved by a run with another active set): entries of stations
        that are not active any more are dropped; an active station the ledger does not know starts invalid. Returns True
        if anything changed (a ledger that already covers ``ids`` is left exactly as it is)."""
        ids = list(ids)
        changed = False
        for s in list(self.stations):
            if s not in ids:
                self._note(f"{s}: not an active station any more; entry dropped")
                del self.stations[s]
                changed = True
        for s in ids:
            if s not in self.stations:
                self.stations[s] = StationTrust(note="not in the saved ledger")
                self._note(f"{s}: new active station, reference not valid")
                changed = True
        if changed:
            self.stations = {s: self.stations[s] for s in ids}
            self._update_level()
        return changed

    # ------------------------------------------------------------- events
    def _note(self, s):
        self.history.append(s)

    def set_reference(self, sid, boot, L0, sigma, source, *, bead=False):
        st = self.stations[sid]
        st.boot, st.L0, st.L0_sigma, st.source, st.valid = boot, float(L0), float(sigma), source, True
        st.bead_verified = bool(bead) or (st.bead_verified and source != "visual")
        st.note = ""
        self._note(f"{sid}: reference {L0:.4f} m +/- {sigma * 1e3:.1f} mm from {source}")

    def invalidate(self, sid, why):
        st = self.stations[sid]
        st.valid = False
        st.bead_verified = False
        st.note = why
        self.recovery_required = True
        self._note(f"{sid}: reference invalid ({why})")
        self._update_level()

    def on_fault(self, sid, code, detail=None):
        """``detail``: plain-language reading of the fault (``tracking_fault_detail``), used for a TRACKING fault only;
        without it the note keeps its old wording."""
        if code == Fault.TRACKING and detail:
            self.invalidate(sid, f"{Fault.NAMES[code]} fault: {detail}")
        elif code in (Fault.TRACKING, Fault.ENCODER, Fault.TIMING):
            self.invalidate(sid, f"{Fault.NAMES[code]} fault: steps may be lost")
        elif code == Fault.SWITCH:
            self.invalidate(sid, "bead switch opened unexpectedly (or wire broken)")
        elif code in (Fault.LEASE, Fault.UNDERRUN):
            # coordinated path stop: positions remain mutually consistent, references kept
            self._note(f"{sid}: {Fault.NAMES[code]} stop; references kept")

    def on_boot_change(self, sid, new_boot):
        self.stations[sid].boot = new_boot
        self.invalidate(sid, "station rebooted: multi-turn epoch lost")

    def on_power_loss(self):
        for sid in self.stations:
            self.invalidate(sid, "power loss")
        self.claw_supported = True
        self._lv("NONE")

    def on_marker_lost(self):
        self.marker_valid = False
        self._note("marker frame invalid (moved or not found)")
        self._update_level()

    def on_camera_calibration(self, cal_id):
        if self.camera_calibration_id is not None and cal_id != self.camera_calibration_id:
            self.marker_valid = False
            self._lv("NONE")
            self._note("camera calibration changed: visual registration invalid")
        self.camera_calibration_id = cal_id

    def restore_after_host_restart(self, boots: dict, faults: dict):
        """Keep references only where the station's epoch is unchanged and it
        reports no latched fault."""
        for sid, st in self.stations.items():
            if not st.valid:
                continue
            if boots.get(sid) != st.boot:
                self.invalidate(sid, "boot id changed while host was down")
            elif faults.get(sid) not in (None, Fault.NONE):
                self.invalidate(sid, f"fault {Fault.NAMES.get(faults[sid])} latched while host was down")
            else:
                st.source = (st.source or "") + "+restored"
        self._update_level()

    def _lv(self, level):
        """Assign the level; the basis exists only while VERIFIED."""
        self.level = level
        if level != "VERIFIED":
            self.verified_basis = None

    def set_level(self, level, *, basis=None, margin_check=None, reasons=None):
        assert level in LEVELS
        assert basis in (None, "margin", "beads")
        self._lv(level)
        if level == "VERIFIED":
            self.verified_basis = basis
            self.trust_reasons = []
        elif reasons is not None:
            self.trust_reasons = list(reasons)
        elif level == "LOCAL_ONLY":
            self.trust_reasons = ["full-workspace trust is decided by a full startup (margin check, D26)"]
        else:
            self.trust_reasons = []
        if margin_check is not None:
            self.margin_check = margin_check
        self._note(f"level -> {level}" + (f" (basis: {basis})" if level == "VERIFIED" and basis else ""))

    def _update_level(self):
        if not any(st.valid for st in self.stations.values()):
            self._lv("NONE")
        elif not all(st.valid for st in self.stations.values()):
            if self.level == "VERIFIED":
                self._lv("LOCAL_ONLY")
                self.trust_reasons = [f"station {sid}: reference lost after verification ({st.note or 'invalid'})"
                                      for sid, st in self.stations.items() if not st.valid]
        if not self.marker_valid and self.level == "VERIFIED":
            self._lv("LOCAL_ONLY")
            self.trust_reasons = ["the marker registration is no longer valid"]

    # ------------------------------------------------------------ queries
    def references(self) -> dict:
        return {sid: st.L0 for sid, st in self.stations.items() if st.valid}

    def all_valid(self) -> bool:
        return all(st.valid for st in self.stations.values())

    def unverified(self) -> list:
        return [sid for sid, st in self.stations.items() if not st.bead_verified]

    # -------------------------------------------------------- persistence
    def save(self, path):
        """Atomic, durable write (temp file + fsync + rename): a crash can never
        leave a truncated or stale-but-plausible ledger."""
        atomic_write(path, json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, path):
        d = json.loads(Path(path).read_text())
        d["stations"] = {k: StationTrust(**v) for k, v in d["stations"].items()}
        return cls(**d)
