---
id: 0029
title: Spectator Dynamic Cinematic Auto-Camera and Safe View Redaction
status: Accepted
created: 2026-09-25
governing_prd: PRD-0011
---

# US-0029 — Spectator Dynamic Cinematic Auto-Camera and Safe View Redaction

## Governing PRD
- [`PRD-0011: Live Spectator Studio & Two-Way Audience Interactivity`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)

## User Story

**As a** live streamer broadcasting games to thousands of viewers (Devon),  
**I want** an autonomous director camera that follows combat action while redacting DM secrets,  
**So that** my stream looks like a cinematic show without requiring manual camera panning or leaking plot spoilers.

## Acceptance Criteria

1. **Autonomous Action Tracking**: The virtual camera smoothly pans and zooms to frame the active token and action target during attacks and spell casts.
2. **Spectator Secret Redaction**: DM notes, hidden traps, invisible monsters, and private creature stats are strictly purged from the spectator feed.
3. **High-Impact Visual FX**: Spell areas-of-effect and critical hit animations render cleanly at high framerates for video broadcast.
