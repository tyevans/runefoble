---
id: '0915'
title: Voice, The Watcher, and the Inference Worker Catch Only Typed Errors
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0015
- ADR-0011
governing_prds:
- PRD-0001
governing_stories: []
target_bc: voice_agent
target_release: 0.9.0
---
# TASK-0915: Voice, The Watcher, and the Inference Worker Catch Only Typed Errors

## Status
Refined

## Summary
Four `except Exception` blocks hide defects. A failed voice kick still answers "kicked". A malformed audio frame is dropped and the client is not told. The copilot expiry timer retries a permanent error forever. The worker turns every exception, programming errors included, into a 503. The audio stream route also fills missing ids with canned values, and uses the session id as the campaign id.

## Problem Statement
- `services/voice_agent/src/voice_agent/coordinator.py:175-192`: `kick_peer` runs each callback in `try ... except Exception` with a warning log, then returns `"status": "kicked"`. `:181-182` uses `hasattr(res, "__await__")` to detect async callbacks. `:64` and `:69` type the callback as `Callable[[str, str, str], Any]`. The only registrant is `signaling/manager.py:30` and `:36`.
- `services/voice_agent/src/voice_agent/stream_routes.py:141-143`: a JSON audio frame that fails to parse logs a warning and `continue`s. The client gets no error frame.
- `services/voice_agent/src/voice_agent/stream_routes.py:95-107`: the `/ws` route defaults `session_id` to `"session_default"` and `speaker_id` to `"speaker_default"`. `:106` defaults `speaker_name` to `"Player"`. `:107` sets `camp_id = qp.get("campaign_id") or sess_id`: a session id used as a campaign id.
- `services/the_watcher/src/the_watcher/copilot.py:209-217`: `_run_timer` catches every `Exception` and reschedules after `RETRY_SECONDS` (`:29`, 1.0 s) with no limit.
- `services/inference_worker/src/inference_worker/openai_compatible.py:55-61`: every exception from `ainvoke` becomes `backend_unavailable` (503).

## Documentation & Architecture Review
- ADR-0015 problem 4 (fallbacks hide failures). `docs/reference/identifiers-and-uuid-policy.md` (no substitute ids, 400 on bad input).
- `docs/reference/inference-worker-response-contract.md` (503 means the backend is unavailable).
- `docs/how-to/handle-neural-voice-duplex-and-speech-interruption.md` and `docs/how-to/manage-dm-copilot-whispers-and-veto-overrides.md`: update the stated behavior.
- TASK-0345 (proposed) splits the STT pipeline. TASK-0859 (refined) touches `voice_agent/coordinator.py:261-268`. Coordinate edits.
- DoR 9: no default ids kept for old clients.

## Product & User Story References
- PRD-0001 (The Watcher). No story names these failure paths.

## Detailed Specification & Implementation Plan
1. Type the kick callback as an async `Protocol`. Await it directly. Remove the `hasattr` probe. A callback failure propagates, so the kick route answers 5xx and the log has the trace. The room state change (`peer_left`) stays saved.
2. In `stream_routes.py`, catch only `json.JSONDecodeError`, `binascii.Error` and `ValueError` from frame parsing. Send an `INVALID_FRAME` error frame (use `send_socket_error`) and keep the socket open. Move frame parsing into a small function in its own module.
3. Remove the bare `/ws` route and the default ids. Require `session_id` and `speaker_id` in the path. Require `campaign_id` from the query. A missing value closes the socket with policy code 1008 and an error frame. Update the clients that open the socket (find them with `grep -rn "/voice/ws\|ws/" services/voice_agent/ui/src frontend/src`).
4. In `copilot.py`, add a retry limit (for example 5). After the limit, log at error level and record the failure once (event or metric). Catch only store and authz outage errors for retry. Other errors propagate.
5. In `openai_compatible.py`, catch only the transport and API errors of the client library (`openai.APIError` subclasses and `httpx.HTTPError`). Other errors propagate as 500.

## Frontdoor Blackbox Test Plan
- Voice: kick a peer through `services/voice_agent/src/voice_agent/room_routes.py:42` while the signaling peer socket is closed (frontdoor setup). Assert the documented reply.
- Voice: open the audio socket, send one malformed JSON frame, then one valid frame. Assert one `INVALID_FRAME` error frame and one transcript reply.
- Voice: open the audio socket without `campaign_id`. Assert close code 1008.
- Copilot: with the event store stopped (live outage fixture), propose an action with a short expiry. Assert that the timer stops after the retry limit (observe through the public pending-action read).
- Worker: a live loopback upstream that returns a 500 gives 503 `backend_unavailable`. A loopback that returns a malformed body that the client library cannot decode gives the documented status.

## Definition of Done
- No `except Exception` in the four named functions. No default ids in the audio stream route.
- Docs updated. `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `services-backend.md` (finding 4), plus the stream route defaults found by the refactor-r3 synthesis
