---
id: '0577'
title: Voice Room Aggregate Saved on Every Command, Duplex Playback State Made Shared
status: Refined
created: 2026-11-17
dependencies:
- TASK-0560
- TASK-0561
governing_adrs:
- ADR-0011
- ADR-0007
governing_prds:
- PRD-0020
governing_stories:
- US-0060
target_release: 0.9.0
severity: high
source_audits:
- w2-voice-agent.md
---

# TASK-0577: Voice Room Aggregate Saved on Every Command, Duplex Playback State Made Shared

## Status
Refined

## Summary
The voice room coordinator loads `VoiceRoomAggregate` from the repository but never saves it. Its events go only to Redis. Duplex playback and stream quality state live in module globals, so replicas and restarts answer differently. This task saves each room command through the repository and moves playback and quality state into the room aggregate.

## Problem Statement
- `grep -rn '\.save(' services/voice_agent` returns nothing. `services/voice_agent/src/voice_agent/coordinator.py:57-64` loads but never saves. Events go only to streams via `_publish_event` (w2-voice-agent F6).
- `coordinator.py:61-63` catches every load error and returns an empty room (TASK-0561 fixes the catch).
- `routers/duplex.py:20` (`_active_playbacks`), `routers/stream_diagnostics.py:19-20` (`_qm`, `_abr`), and `coordinator.py:40` (`_telemetry`) are module-level state (w2-voice-agent F12).
- The gateway builds its own coordinator (`gateway/api/src/gateway_api/signaling/manager.py:10-34`). Its signaling peers are not visible to the service. This divergence is a gateway-theme concern. This task only fixes the service's own state.

## Documentation & Architecture Review
- `docs/how-to/handle-neural-voice-duplex-and-speech-interruption.md` and `docs/how-to/connect-mobile-companion-and-haptic-gateway.md` describe room and duplex behavior. Verify them.
- `proposed/0511-voice-duplex-frontdoor-blackbox-test-suite.md` (TASK-0511, proposed) owns duplex blackbox tests. Cite it as related and do not duplicate its tests.

## Product & User Story References
- [`prd-0020-zero-latency-neural-voice-duplex-and-interruption.md`](../../product/accepted/prd-0020-zero-latency-neural-voice-duplex-and-interruption.md)
- [`us-0060-zero-latency-neural-voice-duplex.md`](../../user_stories/accepted/us-0060-zero-latency-neural-voice-duplex.md)

## Detailed Specification & Implementation Plan
1. Each room command in `coordinator.py` calls `create_event`, then `AggregateRepository.save`, then publishes the saved events. A failed save returns 503 (TASK-0564 policy).
2. Add `PlaybackStarted`, `PlaybackAttenuated`, `PlaybackStopped`, and `QualityAdapted` events to `VoiceRoomAggregate`. Replace `_active_playbacks` and `_qm` / `_abr` with aggregate reads.
3. Telemetry snapshots are read from a projection, not kept in `_telemetry`.
4. Document in the how-to that room state is owned by the voice service and replicas must reach it through its frontdoor.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** create a voice room through the public route, restart the service, then `GET /api/v1/voice/rooms/{id}`. Before: 404 or empty. After: the room is returned with its state.
- **Fail before, pass after:** start a duplex playback, restart, then `GET /api/v1/voice/duplex/status/{id}`. Before: no playback. After: playback reported.
- **Fail before, pass after:** a store load failure on a room command returns 503 and saves no events.
- Public routes only.

## Definition of Done
1. Every room command saves through the repository. Grep shows `.save(` in the coordinator.
2. Three tests above pass. Events registered and documented.
3. `uv run pytest` and `make health-check` pass. Files under 500 lines.
4. How-to updated. `CHANGELOG.md` entry.
