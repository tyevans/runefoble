---
id: '0456'
title: Audience Studio OBS WebSocket Bridge and Stream Deck Hardware Actions
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0051
- TASK-0056
- TASK-0439
governing_adrs:
- ADR-0004
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0011
governing_stories:
- US-0029
- US-0030
target_release: 0.9.0
---

# TASK-0456: Audience Studio OBS WebSocket Bridge and Stream Deck Hardware Actions

## Status
Proposed

## Summary
Implement an OBS Studio remote controller bridge using `obs-websocket-js` in `services/audience_studio` and a dedicated Stream Deck macro integration API. Coordinate automated OBS scene switching (e.g., Narrative Spotlight, Tactical Combat, Critical Roll Replay) driven by gameplay events, and provide physical Stream Deck one-touch buttons for DMs and streamers to trigger chaos polls, emergency pauses, and instant vetoes.

## Problem Statement
Live streamers (Devon) currently must manually switch OBS scenes and juggle browser tabs while simultaneously DMing and roleplaying (PRD-0011, US-0029). While the autonomous director camera tracks token movements, there is no direct OBS WebSocket interface to switch broadcast scenes or trigger streamer macro pads (such as Elgato Stream Deck) during climactic moments, creating operational burden and distracting from storytelling.

## Governing Architecture & ADRs
- **ADR-0004: Unified API Gateway & Sub-Service Proxying**: Expose integration endpoints to local macro tools.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Listen to combat, turn, and roll events for scene automation.
- **ADR-0007: Domain-Driven Design Architecture**: Keep streaming hardware integrations encapsulated in `services/audience_studio`.

## Product & User Story References
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- [`us-0029-spectator-dynamic-cinematic-auto-camera.md`](../../user_stories/accepted/us-0029-spectator-dynamic-cinematic-auto-camera.md)
- [`us-0030-obs-transparent-party-vitals-and-multi-track-audio.md`](../../user_stories/accepted/us-0030-obs-transparent-party-vitals-and-multi-track-audio.md)

## Scope of Work
1. **OBS WebSocket Bridge (`services/audience_studio/src/integrations/obs.ts`)**:
   - Establish and maintain connection to OBS Studio via `obs-websocket-js` (`ws://localhost:4455`).
   - Listen to Redis Stream events:
     - `CombatInitiativeRolled`: Automatically switch to "Tactical Combat" scene.
     - `DiceRolled` (Natural 20 / Critical Failure): Trigger "Dramatic Stinger" scene overlay or camera shake.
     - `SessionStateUpdated` (Paused / Completed): Switch to "Intermission / Offline" scene.
2. **Stream Deck Macro API (`services/audience_studio/src/integrations/streamdeck.ts`)**:
   - Expose lightweight REST endpoints:
     - `POST /api/v1/integrations/streamdeck/trigger-poll`: Instantly launch a configured chaos poll.
     - `POST /api/v1/integrations/streamdeck/veto-current`: One-touch veto of pending modifier proposal.
     - `POST /api/v1/integrations/streamdeck/approve-current`: One-touch approval of pending modifier proposal.
     - `POST /api/v1/integrations/streamdeck/toggle-camera-director`: Toggle autonomous director camera tracking.
3. **Blackbox Tests (`tests/test_blackbox_obs_websocket_bridge.py`)**:
   - Mock OBS WebSocket server and verify client handshake, authentication, and scene transition commands on domain events.
   - Assert Stream Deck macro endpoints successfully interact with `approvalQueue` and `pollEngine`.

## Definition of Done
1. `services/audience_studio/src/integrations/obs.ts` and `streamdeck.ts` implemented strictly < 300 lines.
2. Automated scene transitions fire in response to domain events.
3. Stream Deck HTTP endpoints trigger immediate state updates.
4. Blackbox test suite passes with 100% assertions.
