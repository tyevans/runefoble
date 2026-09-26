---
id: '0056'
title: Cinematic Director Auto-Camera and OBS Stream Overlay
status: Complete
created: 2026-09-25
dependencies:
- TASK-0012
- TASK-0014
- TASK-0016
- TASK-0051
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0007
- ADR-0013
target_release: 0.3.0
governing_prds:
- PRD-0011
governing_stories:
- US-0029
- US-0030
pr_url: https://github.com/tyevans/runefoble/pull/93
---
# TASK-0056: Cinematic Director Auto-Camera and OBS Stream Overlay

## Status
Refined

## Summary
Build an autonomous cinematic director virtual camera and transparent OBS browser-source party HUD overlay in `gateway/api` and `services/game_session/ui/` for live streamers (Devon) to broadcast high-fidelity, uncluttered tabletop gameplay with zero risk of exposing DM secrets.

## Problem Statement
Live streamers currently have to manually pan and zoom the virtual tabletop while broadcasting cluttered player user interfaces. This creates visual friction for spectators and introduces significant risk of leaking private DM map secrets, hidden monster stats, or trap coordinates (PRD-0011, US-0029, US-0030).

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Enforcing spectator-grade permissions that redact DM notes, hidden traps, and private monster stats.
- **ADR-0004: Lit Web Components & Storybook UI**: Designing `<runefoble-spectator-overlay>` with Bauhaus design tokens.
- **ADR-0007: Real-Time Voice & Board Synchronization**: Synchronizing token camera focus and dice roll animations with sub-100ms WebSocket latency.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Vendoring spectator components inside `services/game_session/ui/`.

## Product & User Story References
- **Product Requirement**: [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- **User Stories**:
  - [`us-0029-spectator-dynamic-cinematic-auto-camera.md`](../../user_stories/accepted/us-0029-spectator-dynamic-cinematic-auto-camera.md)
  - [`us-0030-obs-transparent-party-vitals-and-multi-track-audio.md`](../../user_stories/accepted/us-0030-obs-transparent-party-vitals-and-multi-track-audio.md)

## Detailed Specification & Implementation Plan
1. **Autonomous Cinematic Director Camera**:
   - Track active character turn events (`TurnStarted`) and action centers (`TokenMoved`).
   - Smooth viewport pan/zoom calculation utilizing cubic-bezier easing to center active tokens within 300ms.
2. **OBS Transparent Overlay Route**:
   - Expose `GET /overlay/party-vitals/{session_id}` in `gateway/api` with an alpha-transparent background (`rgba(0, 0, 0, 0)`).
   - Deliver party HP bars, active status condition badges, and roll animations.
3. **Spectator Sanitization Security Filter**:
   - Enforce server-side Zanzibar sanitization: strip DM private GM notes, hidden traps, stealth tokens, and unrevealed monster HP numbers.
4. **Microfrontend Component & Storybook**:
   - Implement `<runefoble-spectator-overlay>` in `services/game_session/ui/src/`.
   - Add interactive Storybook stories showcasing clean overlay states and dice roll animations.

## INVEST Criteria Evaluation
- **Independent (I)**: Consumes existing game session and board state WebSocket events without modifying core game session turn logic.
- **Negotiable (N)**: Camera smoothing easing curves and overlay layout positioning can be configured via URL parameters.
- **Valuable (V)**: Enables broadcast streamers to stream clean, TV-grade visuals without risking private narrative spoiler leaks.
- **Estimable (E)**: Builds on existing WebSocket event broadcast infrastructure and Lit Web Component primitives.
- **Small (S)**: Scope strictly isolated to spectator overlay route and camera controller; all files < 250 lines.
- **Testable (T)**: Verified with blackbox HTTP and WebSocket tests ensuring transparency and sanitization invariants.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Sanitization Invariant**:
   - `GET /overlay/party-vitals/{session_id}` and spectator WebSocket feeds verify 100% exclusion of hidden traps, unrevealed monster HP, and DM-only notes.
2. **Transparent OBS Rendering**:
   - The overlay HTML output serves with an alpha-transparent canvas and zero background color obstruction.
3. **Microfrontend Manifest & Storybook**:
   - `<runefoble-spectator-overlay>` custom element published in `services/game_session/ui/manifest.json` and verified in Storybook with zero console errors.
4. **Frontdoor Blackbox Suite**:
   - `tests/test_blackbox_cinematic_director.py` verifying sanitized WebSocket event delivery, route responses, and camera target updates.
5. **Quality Gates**:
   - Conforms strictly to Hard Invariant 6 (< 500 lines per file).
   - Passes `uv run pytest tests/test_blackbox_cinematic_director.py` and `pnpm run build`.
