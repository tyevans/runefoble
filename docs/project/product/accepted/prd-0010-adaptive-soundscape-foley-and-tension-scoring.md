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
