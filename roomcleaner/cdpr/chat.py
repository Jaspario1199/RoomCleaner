"""Rule-based "talk to the robot" for the phone app: intent parser, confirmation state, event log.

Pure Python (no Flask, no hardware): the service gives :class:`Chat` a ``host`` object and everything here is unit
testable with a fake one. No cloud AI service, no API key: a handful of keyword rules.

Safety rules this module enforces (docs/PHONE_APP_SPEC.md, "Safety rules"):

* The chat adds no way to move the robot. It maps text onto the host's existing commands and nothing else.
* ``pause`` runs at once, always, with no confirmation, and cancels anything pending (stop never disables, D21).
* Every motion intent (start, resume, recover, lower, open/close grip) is answered with a question first; the motion
  runs only on "yes"/"confirm" within ``CONFIRM_TTL_S`` (30 s) and only if the host still allows it at that moment.
  Any other message drops the pending question, so an old "lower?" cannot be confirmed after a change of topic.
* ``start`` is never run unless the operator has ticked the pre-start checklist themselves (the client says so with
  ``checklist=True``; the chat never ticks it). Without it the reply sends the operator to the Setup tab.
* ``disarm`` is not available here at all (Setup screen, typed confirmation).
* The pending question is keyed by the session token, so one phone cannot confirm another's question.

``host`` interface (duck-typed; the service implements it):

* ``snapshot() -> dict``   the /api/status dict (state, detail, level, busy, error, reasons, trust, stations, claw, ...)
* ``can(cmd) -> str|None`` None if the command is allowed right now, else a plain-language reason
* ``run(cmd, body)``       start the command (returns at once); raises :class:`Refused` with the reason
* ``pause()``              the supervisor pause (always accepted)
"""
from __future__ import annotations

import re
import threading
import time
from collections import deque
from dataclasses import dataclass

CONFIRM_TTL_S = 30.0
MOTION = ("start", "resume", "recover", "lower", "grip_open", "grip_close")
ESTOP_LINE = "Emergency stop = the switched power strip. It drops the claw: nobody under the robot."

STATE_TEXT = {
    "DISARMED": "Disarmed. The stations are not holding the claw; it should be resting on the floor. "
                "Tick the safety checklist on Setup, then Start.",
    "STARTUP": "Starting up: taking up slack, lifting and calibrating. Keep clear of the robot.",
    "READY": "Ready. Calibrated, holding position.",
    "TASK": "Working: running a pickup task.",
    "PAUSED": "Paused. Holding position with torque on. Resume, or lower the claw to the floor.",
    "FAULT": "Fault. Motion is stopped and the references are still trusted. Acknowledge to clear it.",
    "RECOVERY_REQUIRED": "Recovery needed. The claw may be hanging and a reference is no longer trusted. "
                         "Check the scene, then Recover or Lower.",
    "PARKED": "Parked on the floor, cables slack, stations still holding. Start, or Disarm on Setup.",
}
STATE_HINT = {
    "FAULT": "Say 'acknowledge' (or tap Acknowledge on Setup).",
    "RECOVERY_REQUIRED": "Check nobody is under the robot, then say 'recover' or 'lower'.",
    "PAUSED": "Say 'resume' or 'lower' when you are ready.",
    "PARKED": "The claw is on the floor.",
    "READY": "Calibrated and holding position.",
    "DISARMED": "Say 'start' after ticking the checklist on Setup.",
}

# ---------------------------------------------------------------------------------------------------- parsing
_PAUSE_WORDS = {"pause", "stop", "halt", "freeze", "abort", "emergency", "estop"}
_PAUSE_PHRASES = ("hold position", "hold on", "hold still", "hold it", "stand still", "e stop")
_Q_WORDS = {"why", "what", "how", "where", "when", "who", "which", "is", "are", "was", "were", "did", "does", "do",
            "has", "have", "whats", "hows"}
_POLITE = re.compile(r"^(?:(?:please|pls|kindly|hey|ok|okay|robot)\s+)*"
                     r"(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?|i\s+want\s+you\s+to\s+|i\s+want\s+to\s+|"
                     r"i\s+would\s+like\s+to\s+|lets\s+|let\s+us\s+|go\s+ahead\s+and\s+)?")
_CONFIRM_FIRST = {"yes", "yep", "yeah", "yup", "y", "confirm", "confirmed"}
_CONFIRM_EXTRA = {"please", "do", "it", "now", "go", "ahead", "thanks", "thank", "you", "sure", "i", "do"}
_CONFIRM_ALL = {"do it", "go ahead", "please do", "do it now", "yes do it"}
_CANCEL_FIRST = {"no", "nope", "nah", "cancel", "negative", "nevermind", "dont"}
_CANCEL_PHRASES = ("never mind", "do not", "not now", "dont", "don t")

_RX = {
    "help": re.compile(r"\b(help|commands|options|menu)\b|^what can (i|you)\b"),
    "disarm": re.compile(r"\b(disarm|power off|shut down|shutdown|turn off|motors off|release torque)\b"),
    "grip_open": re.compile(r"\b(open|release|unclamp|ungrip|let go)\b"),
    "grip_close": re.compile(r"\b(close|grab|squeeze|clamp|curl)\b"),
    "grip_ask": re.compile(r"\b(grip|gripper|claw|fingers|hand)\b"),
    "start": re.compile(r"\b(start|restart|begin|calibrate|calibration|startup|get started|get going)\b"),
    "resume": re.compile(r"\b(resume|continue|unpause|proceed|carry on|go on|keep going)\b"),
    "acknowledge": re.compile(r"\b(acknowledge|ack|clear (?:the )?faults?|reset (?:the )?fault)\b"),
    "recover": re.compile(r"\b(recover|recovery|re ?reference)\b"),
    "lower": re.compile(r"\b(lower|land|descend|set (?:it )?down|put (?:it )?down|bring (?:it )?down|go down|come down)\b"),
    "battery": re.compile(r"\b(battery|batt|voltage|volts?|charge|charged|charging|power level)\b"),
    "why": re.compile(r"\b(why|reasons?|trust|trusted|verified|confidence|how sure|whats wrong|what is wrong|"
                      r"problems?|errors?|faults?)\b"),
    "status": re.compile(r"\b(status|state|ready|doing|happening|going on|progress|report|update|online|connected|"
                         r"working|running|paused|armed)\b|where are you"),
    "status_q": re.compile(r"\b(ok|okay|fine|how are you)\b"),
}


def normalise(text: str) -> str:
    t = (text or "").lower().replace("’", "'").replace("'", "")
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _is_confirm(tokens, norm) -> bool:
    """Only a bare yes/confirm (plus filler such as "please") confirms: "yes lower it" does not, so a different
    command cannot ride on someone else's question."""
    if norm in _CONFIRM_ALL:
        return True
    return (tokens[0] in _CONFIRM_FIRST and len(tokens) <= 4
            and all(t in _CONFIRM_EXTRA or t in _CONFIRM_FIRST for t in tokens[1:]))


def parse(text: str) -> str:
    """Intent name for ``text``. One of: pause, confirm, cancel, help, status, why, battery, start, resume,
    acknowledge, recover, lower, grip_open, grip_close, grip_ask, disarm, unknown."""
    norm = normalise(text)
    if not norm:
        return "help" if "?" in (text or "") else "unknown"
    tokens = norm.split()
    body = _POLITE.sub("", norm).strip() or norm
    question = body.split()[0] in _Q_WORDS
    # pause first: the safe action wins over everything except a question ABOUT stopping ("why did you stop")
    if not question and (_PAUSE_WORDS & set(tokens) or any(p in norm for p in _PAUSE_PHRASES)):
        return "pause"
    if tokens[0] in _CANCEL_FIRST or any(norm.startswith(p) for p in _CANCEL_PHRASES):
        return "cancel"
    if _is_confirm(tokens, norm):
        return "confirm"
    if _RX["help"].search(body):
        return "help"
    if question:                                           # a question never moves anything
        for name in ("battery", "why", "status", "status_q", "grip_ask"):
            if _RX[name].search(body):
                return "status" if name in ("status_q", "grip_ask") else name
        return "unknown"
    for name in ("disarm", "grip_open", "grip_close", "start", "resume", "acknowledge", "recover", "lower",
                 "battery", "why", "status", "grip_ask"):
        if _RX[name].search(body):
            return name
    return "unknown"


def chips_for(state: str, busy=None, pending=False) -> list:
    """Quick-reply chips for the chat (the client shows them under the conversation)."""
    if pending:
        return ["Yes", "No", "Pause"]
    out = ["Status", "Why?", "Battery"]
    if busy:
        return out + ["Pause"]
    by_state = {"DISARMED": ["Start"], "PARKED": ["Start", "Open grip", "Close grip"], "PAUSED": ["Resume", "Lower"],
                "FAULT": ["Acknowledge", "Recover", "Lower"], "RECOVERY_REQUIRED": ["Recover", "Lower"],
                "READY": ["Lower"], "STARTUP": [], "TASK": []}
    return out + by_state.get(state, []) + ["Pause", "Help"]


# ---------------------------------------------------------------------------------------------------- event log
class EventLog:
    """Ordered, bounded, thread-safe log with increasing ids (the phone polls ``since=<last id>``)."""

    def __init__(self, maxlen=500, wall=time.time):
        self._d = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._n = 0
        self._wall = wall

    def add(self, kind: str, text: str, *, host_t=None) -> int:
        with self._lock:
            self._n += 1
            self._d.append({"id": self._n, "t": round(self._wall(), 3), "kind": kind, "text": text,
                            **({"host_t": host_t} if host_t is not None else {})})
            return self._n

    def since(self, n=0):
        """(events with id > n in order, id of the newest event). A ``since`` beyond the newest id (the service restarted)
        returns everything."""
        with self._lock:
            last = self._n
            if n > last:
                n = 0
            return [dict(e) for e in self._d if e["id"] > n], last


# ---------------------------------------------------------------------------------------------------- chat
class Refused(Exception):
    """The host refused a command (the text is the plain-language reason)."""


@dataclass
class Pending:
    cmd: str
    question: str
    expires: float
    body: dict


QUESTIONS = {
    "start": "Run the startup sequence now? The claw takes up slack, lifts off the floor and moves around the room "
             "while it calibrates. You have ticked the checklist: nobody under the robot, power strip in reach.",
    "resume": "Resume from PAUSED? The robot re-checks the stations and the camera first, then restarts from the "
              "safest step. The claw may move.",
    "recover": "Run recovery now? The stations are re-armed, one cable may be re-referenced from the camera, and the "
               "claw may move slightly while it re-checks.",
    "lower": "Lower the claw to the floor now? It moves over the marker and descends. Nobody under the robot.",
    "grip_open": "Open the grip now? Whatever the claw is holding will be released.",
    "grip_close": "Close the grip now? The fingers curl in.",
}
STARTED = {
    "start": "Starting. Watch Home or Setup for progress. Say 'pause' to hold position at any time.",
    "resume": "Resuming. The robot re-checks first; it may refuse and tell you why. Say 'pause' to hold.",
    "recover": "Recovering. Say 'pause' to hold position.",
    "lower": "Lowering the claw to the floor. Say 'pause' to hold position.",
    "grip_open": "Opening the grip.",
    "grip_close": "Closing the grip.",
    "acknowledge": "Acknowledging the fault: the stations are re-checked. Watch Home for the result.",
}
HELP = ("I understand: status, why (trust and reasons), battery, pause, resume, start, acknowledge, recover, "
        "lower, open grip, close grip, help. Anything that moves the robot asks 'yes' first (within 30 s). "
        "Pause runs at once. Disarm is only on the Setup screen. " + ESTOP_LINE)


class Chat:
    def __init__(self, host, *, clock=time.monotonic, ttl_s=CONFIRM_TTL_S):
        self.host = host
        self.clock = clock
        self.ttl = ttl_s
        self._pending: dict = {}
        self._lapsed: dict = {}              # key -> cmd of a question that timed out (so a late "yes" is explained)
        self._lock = threading.Lock()

    # -- introspection (tests, status)
    def pending(self, key=""):
        p = self._pending.get(key)
        if p is not None and self.clock() > p.expires:
            return None
        return p

    # -- entry point
    def handle(self, text, *, key="", checklist=False) -> dict:
        intent = parse(text)
        if intent == "pause":                                    # never waits behind another chat request
            self._pending.pop(key, None)
            return self._pause()
        with self._lock:
            now = self.clock()
            pend = self._pending.get(key)
            if pend is not None and now > pend.expires:          # timed out: drop it, remember why
                self._pending.pop(key, None)
                self._lapsed[key] = pend.cmd
                pend = None
            if intent == "confirm":
                return self._confirm(key, pend, checklist)
            if pend is not None:                                 # any other message ends the question
                self._pending.pop(key, None)
            self._lapsed.pop(key, None)
            if intent == "cancel":
                return self._out("Okay, cancelled. Nothing was done." if pend is not None
                                 else "Okay. Nothing was waiting for confirmation.")
            fn = getattr(self, "_i_" + intent, None)
            if intent in MOTION:
                return self._motion(key, intent, checklist, now)
            return fn(text) if fn else self._i_unknown(text)

    # -- helpers
    def _snap(self):
        return self.host.snapshot()

    def _out(self, reply, *, pending=None, run=None, goto=None) -> dict:
        s = self._snap()
        return {"reply": reply,
                "pending_confirm": None if pending is None else
                {"action": pending.cmd, "question": pending.question, "expires_in_s": self.ttl},
                "command_run": run, "goto": goto,
                "chips": chips_for(s.get("state", ""), s.get("busy"), pending is not None)}

    # -- pause / confirm / motion
    def _pause(self):
        try:
            self.host.pause()
        except Exception as e:                                   # never hide a failed pause: say so, point at the strip
            return self._out(f"Pause FAILED ({type(e).__name__}: {e}). Use the PAUSE button. {ESTOP_LINE}")
        st = self._snap().get("state", "?")
        return self._out(f"Paused: holding position with torque on (state {st}). This is not an emergency stop. "
                         + ESTOP_LINE, run="pause")

    def _confirm(self, key, pend, checklist):
        if pend is None:
            late = self._lapsed.pop(key, None)
            return self._out(f"That question timed out ({self.ttl:.0f} s), so nothing was done. Ask again ('{late}') "
                             "if you still want it." if late else "Nothing is waiting for confirmation.")
        self._pending.pop(key, None)
        why = self.host.can(pend.cmd)                           # the state may have changed since the question
        if why:
            return self._out(f"Not done: {why}")
        if pend.cmd == "start" and not checklist:
            return self._out("Not done: the safety checklist is no longer fully ticked. Tick it on the Setup tab.",
                             goto="setup")
        try:
            self.host.run(pend.cmd, dict(pend.body))
        except Refused as e:
            return self._out(f"Refused: {e}")
        return self._out(STARTED[pend.cmd], run=pend.cmd)

    def _motion(self, key, cmd, checklist, now):
        why = self.host.can(cmd)
        if why:
            return self._out(f"I can't do that now: {why}")
        if cmd in ("grip_open", "grip_close"):
            closed = (self._snap().get("claw") or {}).get("grip_closed")
            if closed is not None and bool(closed) == (cmd == "grip_close"):
                return self._out(f"The grip is already {'closed' if closed else 'open'}.")
        body = {}
        if cmd == "start":
            if not checklist:
                return self._out(
                    "Starting needs the pre-start safety checklist, and I can't tick it for you. Open the Setup tab, "
                    "confirm every item yourself (room cleared, power strip in reach, claw upright, cables attached, "
                    "battery charged), then say 'start' again.", goto="setup")
            body = {"checklist": True}
        pend = Pending(cmd, QUESTIONS[cmd], now + self.ttl, body)
        self._pending[key] = pend
        self._lapsed.pop(key, None)
        return self._out(f"{pend.question} Say 'yes' within {self.ttl:.0f} s to confirm, or 'no'.", pending=pend)

    # -- non-motion intents
    def _i_acknowledge(self, text):
        why = self.host.can("acknowledge")
        if why:
            return self._out(f"I can't do that now: {why}")
        try:
            self.host.run("acknowledge", {})
        except Refused as e:
            return self._out(f"Refused: {e}")
        return self._out(STARTED["acknowledge"], run="acknowledge")

    def _i_help(self, text):
        return self._out(HELP)

    def _i_unknown(self, text):
        shown = (text or "").strip()[:60]
        return self._out(f"I didn't understand “{shown}”. " + HELP)

    def _i_grip_ask(self, text):
        return self._out("Do you want me to open or close the grip? Say 'open grip' or 'close grip'.")

    def _i_disarm(self, text):
        return self._out("Disarm is not available from chat. Use Setup > Disarm: it needs the claw resting on the "
                         "floor (checked by the camera) and you type 'claw_supported' to confirm.", goto="setup")

    def _i_battery(self, text):
        s = self._snap()
        c = s.get("claw") or {}
        if not c.get("online"):
            return self._out("The claw is not reporting (offline, or no telemetry yet), so I can't read its battery.")
        v, lo = c.get("battery_v"), c.get("battery_low")
        if v is None:
            return self._out("The claw is online but sent no battery reading.")
        mn = c.get("battery_min_v")
        msg = f"Claw battery {v:.2f} V."
        if lo:
            msg += (f" LOW: the host refuses to lift below {mn} V. Charge it per the charging rule (switch off, "
                    "attended, 8.4 V charger at 1 A or less).") if mn else " LOW."
        else:
            msg += " OK for lifting." if mn else ""
        return self._out(msg)

    def _i_why(self, text):
        s = self._snap()
        t = s.get("trust") or {}
        lines = [f"State {s.get('state')}: {STATE_TEXT.get(s.get('state'), '')}".strip()]
        lvl = t.get("level") or s.get("level")
        if lvl == "VERIFIED":
            lines.append(f"Trust VERIFIED (full workspace; basis: {t.get('basis') or 'margins'}).")
        elif lvl:
            why = "; ".join(t.get("reasons") or []) or "no calibrated volume yet"
            lines.append(f"Trust {lvl}: restricted to the calibrated volume. Why: {why}.")
        rs = [r for r in (s.get("reasons") or []) if r]
        if rs:
            lines.append("Recent reasons: " + " | ".join(rs[-3:]))
        if s.get("error"):
            lines.append("Last problem: " + str(s["error"]))
        if len(lines) == 1 and s.get("state") in ("READY", "PARKED", "DISARMED"):
            lines.append("Nothing is wrong that I know of.")
        return self._out("\n".join(lines))

    def _i_status(self, text):
        s = self._snap()
        st = s.get("state")
        lines = [f"State {st}" + (f" ({s['detail']})" if s.get("detail") else "") + f": {STATE_TEXT.get(st, '')}"]
        stn = []
        for k, v in sorted((s.get("stations") or {}).items()):
            f = v.get("fault")
            stn.append(f"{k} fault {f}" if f not in (None, "NONE") else
                       f"{k} offline" if v.get("online") is False else f"{k} ok")
        if stn:
            lines.append("Stations: " + ", ".join(stn) + ".")
        c = s.get("claw") or {}
        if c.get("online"):
            bv = f"{c['battery_v']:.2f} V" if c.get("battery_v") is not None else "no battery reading"
            lines.append(f"Claw: {bv}{' (LOW)' if c.get('battery_low') else ''}, grip "
                         f"{'closed' if c.get('grip_closed') else 'open'}, camera "
                         f"{'unknown' if c.get('camera_ok') is None else 'ok' if c['camera_ok'] else 'FAULT'}.")
        else:
            lines.append("Claw: not reporting.")
        if s.get("busy"):
            lines.append(f"Busy with '{s['busy']}'; only pause works until it finishes.")
        if s.get("error"):
            lines.append("Last problem: " + str(s["error"]))
        hint = STATE_HINT.get(st)
        if hint and st in ("FAULT", "RECOVERY_REQUIRED", "PAUSED"):
            lines.append(hint)
        return self._out("\n".join(lines))
