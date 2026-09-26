---
id: 0056
title: Cinematic Director Auto-Camera and OBS Stream Overlay
status: Proposed
created: 2026-09-25
dependencies: [TASK-0012, TASK-0014, TASK-0016]
governing_adrs: [ADR-0004, ADR-0007]
target_release: 0.2.1
governing_prds:
- PRD-0011
governing_stories:
- US-0029
- US-0030
---

# TASK-0056: Cinematic Director Auto-Camera and OBS Stream Overlay

## Status
Proposed

## Summary
Build an autonomous cinematic director virtual camera and a transparent party HUD browser-source overlay for live streamers (Devon) in the frontend and API gateway.

## Problem Statement
Live streamers must currently manually pan/zoom the virtual tabletop and use cluttered player interfaces on stream, causing visual clutter and risking the exposure of private DM secrets.

## Scope of Work
1. **Cinematic Director Camera**: Lit component tracking active character tokens and action centers with smooth cubic-bezier camera easing.
2. **OBS Transparent Overlay Route**: Add `/overlay/party-vitals/{session_id}` route with transparent alpha background showing party HP bars, active afflictions, and dice roll animations.
3. **Spectator Sanitization Filter**: Ensure the spectator stream endpoint purges private token notes, hidden traps, and monster HP values.

## Acceptance Criteria
1. Auto-camera frames active token within 300ms of turn start or movement action.
2. OBS overlay renders with 60 FPS performance and transparent background.
3. Zero private DM notes or trap markers visible on the overlay route.
