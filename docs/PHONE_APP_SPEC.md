# Phone app — specification (2026-10-21)

Jasper wants to use his phone to talk to the robot, watch the claw camera and
run setup. This spec is the contract for the implementation and the review.

## Architecture (lead decision)

- **Extend the gen-2 service** `roomcleaner/cdpr/service.py` (Flask, session
  token, one command worker, host keep-alive loop). That service is the only
  thing that talks to the stations and the claw, so the phone never reaches the
  hardware directly. The gen-1 console `roomcleaner/app` is kept unchanged as
  history.
- **One mobile-first web app** served by that service: plain HTML/CSS/JS, no
  build step, no CDN (it must work on a home LAN with no internet). Installable
  as a home-screen app (web manifest + icon). The old `static/setup.html` is
  kept as `static/setup_v1.html` and stays reachable at `/v1`.
- **Phone access:** `--host 0.0.0.0` on the home LAN. The terminal prints the
  URL with the token (and a QR code when the optional `qrcode` package is
  installed). The token is required on every `/api` call (already enforced) and
  on the camera stream. For access away from home use Tailscale; no port
  forwarding.

## Screens (bottom tab bar, one-thumb use)

1. **Home.** Supervisor state in large text with plain-language detail; trust
   level (VERIFIED / LOCAL_ONLY / NONE) with its reasons; four station tiles
   A–D (online, fault, state); claw tile (battery V and low flag, grip state,
   camera OK); busy indicator; last error. A large **PAUSE (hold position)**
   button is always visible on every screen. Under it, always: "Emergency stop
   = the switched power strip. It drops the claw: nobody under the robot."
2. **Camera.** Live claw camera from the frame the host already fetched (no
   second client on the claw), about 5 fps, MJPEG with a still-JPEG fallback.
   Shows the frame age and the marker/board detection status. In `--sim`, the
   simulator's claw view (`sim/render.py render_claw_view`).
3. **Setup.** Guided steps:
   (a) room size and anchors (`POST /api/room`);
   (b) unmeasured-configuration checks (`GET /api/checks`), shown per stage;
   (c) the pre-start safety checklist (every box must be ticked);
   (d) Start, then live startup progress (sequencer steps, prompts and reasons);
   (e) the calibration result and trust summary.
   Recovery actions (acknowledge, recover, lower, disarm) appear only when the
   supervisor state allows them. Disarm keeps its typed confirmation
   (`claw_supported`).
4. **Chat ("talk to the robot").** A conversation view. Robot messages come
   from the supervisor events and state changes ("Station B lease fault: tap
   Acknowledge"). The operator types a message or taps a quick-reply chip. A
   rule-based intent parser runs on the server (`POST /api/say`) and maps it to
   the existing commands: status, pause, resume, start (asks for the checklist),
   acknowledge, recover, lower, open/close grip (only where the supervisor
   allows it), battery, trust/why, help. Every motion intent answers with a
   confirmation question first, and the motion only runs after "yes" within
   30 s. Unknown text gets "I didn't understand" plus the help list. Optional
   voice: a mic button that uses the browser's speech recognition where it is
   available (hidden otherwise), and an optional "speak replies" toggle using
   speech synthesis. No cloud AI service and no API key.

## New or extended endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/events?since=N` | Ordered event log (id, time, kind, text) for the chat and Home: supervisor state changes, reasons, startup steps, command results |
| `POST /api/say {text}` | Intent parser. Returns `{reply, pending_confirm?, command_run?}` |
| `GET /api/frame.jpg` | Latest claw frame (JPEG) and its age header |
| `GET /api/stream.mjpg?token=` | MJPEG at ~5 fps. Token as a query parameter, because `<img>` cannot send headers. Only this route accepts it |
| `GET /api/status` | Extended with per-station and claw telemetry |
| `GET /manifest.webmanifest`, `/icon.png`, `/` (new app), `/v1` (old page) | Static files |

The host must cache the latest JPEG inside the frame thread it already runs
(`claw_link.ThreadedFrameSource` / `DetectorFrameSource`), so the camera
screen adds no load to the claw and cannot slow down vision.

## Safety rules (non-negotiable)

- The app adds no new way to move the robot. It only calls the existing
  supervisor commands, with the same refusals. Motion commands from chat need
  an explicit confirmation.
- PAUSE holds torque ("stop never disables", D21). The app never claims to be
  an emergency stop.
- Nobody under the robot: the start checklist stays mandatory.
- Losing the phone connection does nothing to the robot (no dead-man release).
- The camera stream never blocks the host loop: frames are served from the
  cache, never fetched on request.

## Tests

Flask test client in `--sim`: token required on every `/api` route and on the
stream; `say` intents (help, status, pause, the confirmation flow, a timed-out
confirmation, unknown text); events are ordered and incremental; `frame.jpg`
returns a JPEG in sim; the start-from-chat flow needs the checklist; `/v1`
still serves the old page; the host keep-alive still runs while the stream is
open (no station lease fault during 2 s of streaming).
