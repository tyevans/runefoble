---
id: 0054
title: Post-Session Combat Spatial Heatmaps and Party Damage Analytics
persona: Devon (Streamer)
status: Accepted
created: 2026-09-26
governing_prd: PRD-0012
---

# US-0054 — Post-Session Combat Spatial Heatmaps and Party Damage Analytics

## Governing PRD
- [`PRD-0012: Campaign Telemetry, Analytics & Historical Memory Archive`](../../product/accepted/prd-0012-campaign-telemetry-and-living-chronicle-timeline.md)

## Persona
Devon (Streamer) / Sarah (Absent Player) / Evelyn (DM)

## User Story

**As a** campaign participant and content creator reviewing historical sessions,  
**I want to** inspect visual spatial heatmaps of token movement, party damage distribution charts, and lethal knockout coordinates,  
**So that** players can celebrate heroic moments, streamers can display post-game analysis infographics, and returning absent players can understand combat highlights.

## Acceptance Criteria

1. **Spatial Movement Heatmaps**: Renders 2D grid overlay visualizing high-traffic token corridors, hazard trigger hotspots, and character knockout locations.
2. **Damage & Healing Distribution**: Computes breakdown charts displaying damage dealt, damage taken, healing applied, and spell slot efficiency per character.
3. **Turn-by-Turn Chronicle Timeline**: Interactive scrubber allows stepping through the encounter round-by-round with synchronized event highlights.
4. **Privacy & Offline Persistence**: Telemetry projections are derived asynchronously from Redis Streams domain events and stored in PostgreSQL without tracking external PII.
