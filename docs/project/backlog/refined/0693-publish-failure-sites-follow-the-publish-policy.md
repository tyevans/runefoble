---
id: '0693'
title: Remaining Publish Failure Sites Follow the Publish Failure Policy
status: Refined
created: 2026-11-17
dependencies:
- TASK-0564
- TASK-0684
governing_adrs:
- ADR-0006
- ADR-0015
governing_prds: []
governing_stories: []
target_release: 0.9.0
severity: medium
source_audits:
- work/0564.md
- work/0602.md
- work/0624.md
---

# TASK-0693: Remaining Publish Failure Sites Follow the Publish Failure Policy

## Status
Refined. Discovered in round 2 audit of reports 0564, 0602 and 0624. TASK-0564 set the policy: a domain state change fails the request, and a best-effort notification is counted. It did not reach every site.

## Summary
Some publish sites in voice_agent and gateway_mcp still log a failure and continue, with no count and no 503. The transcribe route also skips the failure event that the stream path publishes. This task applies the policy to these sites and exposes the counters on `/healthz`.

## Problem Statement
- `services/voice_agent/src/voice_agent/dependencies.py:60-78`: `publish_voice_event` and the conditioning loop log warnings and continue. No count.
- `services/voice_agent/src/voice_agent/coordinator.py:159-164`, `routers/duplex.py:50`, `routers/audio_filters.py:96`, `stt.py:159` and `:231`: same pattern (from report 0564).
- `gateway/mcp/src/gateway_mcp/dynamic/events.py:43-53`: dropped system events are logged and traced. They are not counted on `/healthz`.
- `services/voice_agent/src/voice_agent/routers/transcribe.py`: an engine failure does not publish `VoiceTranscriptionFailed`. The stream path in `stt.py` does.
- Report 0578: `gateway_mcp` `server.py` `main()` configures no event bus when run standalone, so dynamic tool events are dropped.
- `/healthz` counters exist in the_watcher, game_session, board_state, asset_forge, soundscape, character_sheet and gateway. They do not exist in campaign_lore, campaign_analytics, rules_compendium, voice_agent or inference_worker.

## Documentation & Architecture Review
- ADR-0006: Redis Streams events. Consumers rely on events for state.
- ADR-0015 (b) and (f): fallbacks hide failures. Count and surface them.
- `docs/reference/redis-streams-event-bus.md`: state the policy per site class.

## Product & User Story References
None. Reliability and observability.

## Detailed Specification & Implementation Plan
1. For each site, classify it as domain state (fail the request with 503) or notification (best effort, counted). Record the class in a code comment or the reference doc.
2. Replace the warn-only loops with the shared helpers from `runefoble_platform.event_publish`.
3. In `transcribe.py`, publish `VoiceTranscriptionFailed` on engine failure, as the stream path does.
4. In gateway_mcp, count dropped events and expose the count on its health route.
5. Add the counter to the `/healthz` of the five services listed above.

## Frontdoor Blackbox Test Plan
- Stop Redis (test double). Post a domain-state request to the voice route. Assert 503 and no state change.
- Stop Redis. Post a notification-class request. Assert success and a count of 1 on `/healthz`.
- Force a transcription engine error through the public transcribe route. Assert a `VoiceTranscriptionFailed` entry on the voice stream.

## Definition of Done
- No warn-only publish site remains in the listed files.
- `/healthz` reports the counter in all eight services.
- `uv run pytest` and `make lint` pass.
