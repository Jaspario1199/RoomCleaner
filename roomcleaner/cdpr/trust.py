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
region; not allowed to approach beads/corners) < VERIFIED (every required
bead reference checked and the final validation passed).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .protocol import Fault

LEVELS = ("NONE", "LOCAL_ONLY", "VERIFIED")


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
    stations: dict = field(default_factory=lambda: {s: StationTrust() for s in "ABCD"})
    anchors_room: list | None = None   # 4x3
    anchors_sigma: list | None = None
    T_R_M: list | None = None          # marker registration (4x4)
    marker_valid: bool = False
    camera_calibration_id: str | None = None
    level: str = "NONE"
    recovery_required: bool = False
    claw_supported: bool = False       # FAIL CLOSED: unknown means "may be hanging"; set True only by
                                       # a vision floor check, False before the first lift command
    history: list = field(default_factory=list)

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

    def on_fault(self, sid, code):
        if code in (Fault.TRACKING, Fault.ENCODER, Fault.TIMING):
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
        self.level = "NONE"

    def on_marker_lost(self):
        self.marker_valid = False
        self._note("marker frame invalid (moved or not found)")
        self._update_level()

    def on_camera_calibration(self, cal_id):
        if self.camera_calibration_id is not None and cal_id != self.camera_calibration_id:
            self.marker_valid = False
            self.level = "NONE"
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

    def set_level(self, level):
        assert level in LEVELS
        self.level = level
        self._note(f"level -> {level}")

    def _update_level(self):
        if not any(st.valid for st in self.stations.values()):
            self.level = "NONE"
        elif not all(st.valid for st in self.stations.values()):
            if self.level == "VERIFIED":
                self.level = "LOCAL_ONLY"
        if not self.marker_valid and self.level == "VERIFIED":
            self.level = "LOCAL_ONLY"

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
