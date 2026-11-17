---
id: '0593'
title: Gateway Voice Room, Diagnostics, and Companion Proxy to Voice Agent
status: Refined
created: 2026-11-17
dependencies:
- TASK-0580
- TASK-0624
governing_adrs:
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0019
- PRD-0020
governing_stories:
- US-0011
severity: high
source_audits:
- w2-voice-agent.md
- w1-gateway-api.md
- w3-ddd-architecture.md
target_release: 0.9.0
---

# TASK-0593: Gateway Voice Room, Diagnostics, and Companion Proxy to Voice Agent

## Status
Refined

## Summary
The gateway mounts `voice_agent` routers in process and keeps its own companion and signaling managers. Those managers hold connection state that belongs to `voice_agent`. Replace the in-process mounts and the managers with proxies. The duplex audio socket and the DSP route are owned by TASK-0508 and TASK-0480. This task does not change them.

## Problem Statement
- `main.py:41-42` imports `voice_agent.room_routes` and `voice_agent.routers.stream_diagnostics`. Both are mounted at `main.py:85` and `:87` (`w2-voice-agent.md` F7).
- `companion/manager.py:12`, `companion/endpoint.py:20`, `companion/router.py:10` and `signaling/manager.py:10` import `voice_agent.mobile` and `voice_agent.room`.
- `companion/manager.py` and `signaling/manager.py` hold connection state in gateway memory (`w3-ddd-architecture.md` F13).
- `companion/router.py` trusts `X-User-Id` with a default of `the_watcher_dm` (`w1-gateway-api.md` F22). That trust is owned by the authorization theme. This task replaces the default with the verified principal from the shared client.

## Documentation & Architecture Review
- The owner is `services/voice_agent`. Its routes and room state are in `services/voice_agent/src/voice_agent/room_routes.py`, `routers/stream_diagnostics.py` and `mobile.py`.
- `docs/how-to/connect-mobile-companion-and-haptic-gateway.md` and `docs/how-to/handle-neural-voice-duplex-and-speech-interruption.md` describe the public flows.
- Scope boundary: duplex audio WebSocket (`/ws/voice/duplex/{session_id}`, TASK-0508) and voice DSP REST (TASK-0480) stay with their tasks. Signaling for WebRTC rooms is in this task.
- ADR-0007: shared models for the companion profile (`mobile.py`) move to `libs/runefoble_events` only if the gateway and the owner both need them. Otherwise the gateway uses the owner's HTTP contract only.

## Product & User Story References
- [`prd-0019-spatial-companion-mobile-and-haptic-ping-gateway.md`](../../product/accepted/prd-0019-spatial-companion-mobile-and-haptic-ping-gateway.md)
- [`prd-0020-zero-latency-neural-voice-duplex-and-interruption.md`](../../product/accepted/prd-0020-zero-latency-neural-voice-duplex-and-interruption.md)
- [`us-0011-dynamic-voice-filters-for-afflicted-characters.md`](../../user_stories/accepted/us-0011-dynamic-voice-filters-for-afflicted-characters.md)

## Detailed Specification & Implementation Plan
1. Create `gateway/api/src/gateway_api/routers/voice_proxy.py`. Forward the room REST routes and the stream diagnostics routes through `ServiceClient` (TASK-0580). List the owner routes from `room_routes.py` and `stream_diagnostics.py` and map each.
2. Create the companion and signaling relays on top of `websocket_relay` (TASK-0592). The relay forwards frames to `voice_agent`. Remove `companion/manager.py`, `companion/endpoint.py`, `signaling/manager.py` and `signaling/handlers.py` from the gateway, unless a handler validates the message. A validator that only reads the message stays in the gateway. A validator that holds state moves to `voice_agent`.
3. Move companion connection state to `voice_agent`. Owner work is in `services/voice_agent/src/voice_agent/mobile.py` and a new `companion_registry.py` under 300 lines.
4. Replace the companion `X-User-Id` default with the principal from `get_current_user`. Remove the default value.
5. Remove the `voice_agent` import from `gateway/api/pyproject.toml` if no import remains. Record the result in the PR.
6. Update `docs/reference/ports-and-endpoints.md` for the voice and companion rows.

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_gateway_voice_proxy.py`. `voice_agent` runs as an ASGI app for REST and as a uvicorn server for the socket test.

| Case | Expected before fix | Expected after fix |
|---|---|---|
| Create a voice room through the gateway, then GET from the owner | Fails: room in gateway | Passes |
| Companion register with no identity returns 401 | Fails: `the_watcher_dm` default | Passes |
| Companion state survives gateway rebuild with the same owner | Fails: gateway memory | Passes |
| Owner down returns 503 | Fails: local answer | Passes |
| `rg "from voice_agent" gateway/api/src` | Fails: matches | Passes: no match |

## Definition of Done
1. The gateway imports nothing from `voice_agent`.
2. Companion and signaling state live in `voice_agent`.
3. The `the_watcher_dm` default is gone.
4. The blackbox test file passes. `uv run ruff check .` passes.
5. Duplex (TASK-0508) and DSP (TASK-0480) tasks are not changed by this PR.
