---
id: '0508'
title: Gateway Voice Duplex WebSocket Routing and Zanzibar Proxy
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0008
- TASK-0034
- TASK-0141
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0013
governing_prds:
- PRD-0020
governing_stories:
- US-0060
target_release: 0.9.0
---

# TASK-0508: Gateway Voice Duplex WebSocket Routing and Zanzibar Proxy

## Status
Proposed

## Summary
Implement a dedicated Gateway API voice duplex proxy router (`gateway/api/src/gateway_api/routers/voice_duplex.py`), mounting WebSocket proxy routes `/ws/voice/duplex/{session_id}` and `/ws/v1/voice/duplex/{session_id}` and HTTP metrics endpoint `/api/v1/voice/duplex/stats` with SpiceDB Zanzibar fine-grained authorization (`participate` or `spectate` on `session:{session_id}`), proxying real-time binary audio frames and barge-in control events to `services/voice_agent` with sub-10ms proxy overhead.

## Problem Statement
While `services/voice_agent/src/voice_agent/routers/duplex.py` provides low-latency neural VAD barge-in detection, AEC filtering, and cancellation token management on internal port 8003, the API Gateway does not expose or proxy the duplex WebSocket protocol. External clients connecting to `ws://localhost:8000/ws/voice/duplex/{session_id}` or via Vite development proxy receive 404 Not Found, forcing clients to bypass API Gateway security or preventing duplex barge-in capabilities in the frontend App Shell.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Validating that the connecting user has `participate` (or `spectate`) relation on `session:{session_id}` before establishing the duplex WebSocket stream.
- **ADR-0005: Zitadel OIDC Authentication**: Extracting JWT claims from WebSocket handshake query parameters (`?token=...`) or `Authorization` headers.
- **ADR-0013: Frontend Microfrontend Architecture**: Exposing all interactive audio endpoints through the unified Gateway frontdoor.

## Product & User Story References
- [`prd-0020-zero-latency-neural-voice-duplex-and-interruption.md`](../../product/accepted/prd-0020-zero-latency-neural-voice-duplex-and-interruption.md)
- [`us-0060-zero-latency-neural-voice-duplex.md`](../../user_stories/accepted/us-0060-zero-latency-neural-voice-duplex.md)

## Scope of Work
1. **Gateway Voice Duplex Router (`gateway/api/src/gateway_api/routers/voice_duplex.py`)**:
   - Create router tagged with `"Voice Duplex & Interruption"`.
   - Implement `@router.websocket("/ws/voice/duplex/{session_id}")` and `/ws/v1/voice/duplex/{session_id}`.
   - Enforce Zanzibar permission `participate` or `spectate` on `session:{session_id}` during connection handshake.
   - Establish upstream bidirectional WebSocket bridge to `voice-agent:8003/ws/voice/duplex/{session_id}`.
   - Implement `GET /api/v1/voice/duplex/stats` proxying active playback counts, AEC metrics, and average barge-in latency.
2. **Gateway App Integration (`gateway/api/src/gateway_api/main.py`)**:
   - Register `voice_duplex_router` with FastAPI application.
   - Update OpenAPI aggregator schemas.
3. **Ports Reference Documentation**:
   - Update `docs/reference/ports-and-endpoints.md` with Gateway duplex endpoints.

## Definition of Done
1. WebSocket connection to `/ws/voice/duplex/{session_id}` successfully proxies binary PCM chunks and JSON barge-in events to `voice-agent`.
2. Connection attempts without valid Bearer token or lacking session membership are rejected with HTTP 403 / WebSocket close code 4403.
3. `GET /api/v1/voice/duplex/stats` returns duplex stream diagnostic metrics through Gateway port 8000.
