---
id: '0480'
title: Gateway Voice DSP and Vocal Modulator API Routing & Zanzibar Proxy
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0008
- TASK-0021
- TASK-0157
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0013
governing_prds:
- PRD-0004
governing_stories:
- US-0011
- US-0020
target_release: 0.9.0
---

# TASK-0480: Gateway Voice DSP and Vocal Modulator API Routing & Zanzibar Proxy

## Status
Proposed

## Summary
Implement a dedicated Gateway API voice DSP proxy router (`gateway/api/src/gateway_api/routers/voice_dsp.py`), mounting endpoints for `/api/v1/voice/presets`, `/api/v1/voice/modulate`, and `/api/v1/voice/dsp/apply` with SpiceDB Zanzibar fine-grained authorization (`control` / `participate` on `session` or `game_session`), registering voice DSP schemas in the unified OpenAPI specification, and configuring local Vite development proxies.

## Problem Statement
While `services/voice_agent/src/voice_agent/routers/vocal_effects.py` and `audio_filters.py` implement NPC formant shifting, pitch modulation, and dynamic DSP filters, these endpoints are isolated inside the `voice-agent` microservice. In `gateway/api/src/gateway_api/main.py`, the API Gateway only mounts room WebRTC routes (`voice_rooms_router`) and telemetry diagnostics (`stream_diagnostics_router`). As a result, client requests calling `/api/v1/voice/modulate`, `/api/v1/voice/presets`, or `/api/v1/voice/dsp/apply` on port 8000 (or via Vite development proxy at port 5173) fail with 404 Not Found, preventing the frontend App Shell and external tools from accessing vocal modulation features.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Protecting `/api/v1/voice/modulate` and DSP conditioning actions with SpiceDB Zanzibar checks ensuring only DMs and authorized session participants can apply vocal filters.
- **ADR-0005: Zitadel OIDC Authentication**: Verifying caller Bearer JWT tokens and extracting user identity claims.
- **ADR-0013: Frontend Microfrontend Architecture**: Exposing public frontdoor API endpoints on `gateway-api` (port 8000) rather than requiring clients to connect directly to internal microservices.

## Product & User Story References
- [`prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md`](../../product/accepted/prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md)
- [`us-0011-dynamic-voice-filters-for-afflicted-characters.md`](../../user_stories/accepted/us-0011-dynamic-voice-filters-for-afflicted-characters.md)
- [`us-0020-dm-vocal-modulator-with-realtime-npc-filtering.md`](../../user_stories/accepted/us-0020-dm-vocal-modulator-with-realtime-npc-filtering.md)

## Scope of Work
1. **Gateway Voice DSP Router (`gateway/api/src/gateway_api/routers/voice_dsp.py`)**:
   - Create router tagged with `"Voice DSP & Vocal Modulation"`.
   - Implement `GET /api/v1/voice/presets` returning available NPC vocal presets (Ancient Dragon, Goblin Skulker, Celestial Spirit, Robotic Construct).
   - Implement `POST /api/v1/voice/modulate` accepting `session_id`, `preset_name`, `pitch_shift_semitones`, `formant_shift`, `resonance_hz`, and optional base64 audio frames.
   - Enforce Zanzibar permission `control` or `participate` on `session:{session_id}` or `game_session:{session_id}`.
   - Implement `POST /api/v1/voice/dsp/apply` accepting audio frames and active affliction filters (`drunk`, `whisper`, `underwater`, `ethereal`).
2. **Gateway App Integration (`gateway/api/src/gateway_api/main.py`)**:
   - Import and include `voice_dsp_router` under prefix `/api/v1/voice`.
   - Ensure routes are registered in Swagger UI / OpenAPI JSON aggregator.
3. **Vite Proxy & Ports Reference Update**:
   - Verify `scripts/dev_server.py` and `vite.config.ts` route `/api/v1/voice` cleanly to port 8000.
   - Update `docs/reference/ports-and-endpoints.md` with Gateway voice DSP routes.

## Definition of Done
1. `GET /api/v1/voice/presets` returns available NPC vocal presets through the Gateway API.
2. `POST /api/v1/voice/modulate` and `POST /api/v1/voice/dsp/apply` are accessible on Gateway API port 8000 and return formatted responses with <50ms processing latency.
3. Requests without valid session permissions are rejected with 403 Forbidden via SpiceDB Zanzibar checks.
4. Voice DSP endpoints are reflected in `http://localhost:8000/openapi.json`.
5. All source files conform strictly to Hard Invariant 6 (< 500 lines).
