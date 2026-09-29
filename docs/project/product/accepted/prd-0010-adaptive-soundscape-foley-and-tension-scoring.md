---
id: 0010
title: Adaptive Soundscape, Environmental Foley & Combat Scoring
status: Accepted
created: 2026-09-25
---

# PRD-0010 — Adaptive Soundscape, Environmental Foley & Combat Scoring

## Who this is for

Casual adventurers (Marcus), live streamers (Devon), and DMs (Evelyn) seeking cinema-grade audio immersion without manual DJing during gameplay.

## What the person cannot do today

Currently, DMs must manually hunt for atmospheric music tracks, switch tracks during combat, and trigger sound effects, distracting from session storytelling and table moderation.

## What good looks like

- **Encounter-Tension Driven Musical Scoring**: Musical themes adapt dynamically based on session events (exploration, rising tension, active combat, near-death stakes, victory).
- **Spatial Environmental Foley**: Generates ambient backgrounds (dungeon dripping, cavern wind, tavern crowd) corresponding to the party's current location in `board_state`.
- **Spoken Action Sound Effects**: Tactical events (critical hits, fireballs, shield bashes) fire synchronized sound effects in the WebAudio pipeline upon action execution.

## What this does not do

- It does not drown out player speech; dynamic ducking automatically attenuates background music and foley whenever a player or DM speaks.
- It does not require external DJ software or third-party audio bots.

## What it costs at scale

Audio stem streaming requires lightweight WebAudio node mixing on the client and low-bitrate spatial audio delivery.

## Checkable Outcomes

1. Background music seamlessly transitions between exploration and combat stems based on `game_session` combat state changes.
2. WebAudio client mixes environmental foley with automatic ducking during player speech.
3. Tactical sound effects trigger within 100ms of domain events broadcast over WebSockets.

## Linked User Stories
- [`US-0039: Encounter Tension-Driven Adaptive Musical Scoring and Foley`](../../user_stories/accepted/us-0039-encounter-tension-adaptive-scoring-and-foley.md)
- [`US-0053: DM Manual Soundboard Triggers and Tactical Foley Overrides`](../../user_stories/accepted/us-0053-dm-manual-soundboard-and-foley-triggers.md)

## Implementing Backlog Tasks
- [`TASK-0050: Dynamic Soundscape & Adaptive Audio Microservice`](../../backlog/complete/0050-dynamic-soundscape-and-adaptive-audio-bc.md)
- [`TASK-0095: Soundscape Blackbox Test Suite and Adaptive Mixer Modular Decomposition`](../../backlog/complete/0095-soundscape-blackbox-test-suite-and-mixer-decomposition.md)
- [`TASK-0109: Dynamic Soundscape Mixing Panel Microfrontend and WebAudio Ducking Controls`](../../backlog/complete/0109-dynamic-soundscape-mixing-panel-microfrontend.md)
- [`TASK-0436: Gateway Soundscape API Routing & Zanzibar Authorization Proxy`](../../backlog/refined/0436-gateway-soundscape-api-routing-and-zanzibar-authorization-proxy.md)
- [`TASK-0437: App Shell Soundscape Real-Time WebSocket Audio Synchronization & Foley Playback`](../../backlog/proposed/0437-app-shell-soundscape-websocket-audio-sync.md)
- [`TASK-0438: Soundscape Tactical Board Event Subscribers for Kinetic Foley Audio Cues`](../../backlog/proposed/0438-soundscape-tactile-board-event-handlers.md)
