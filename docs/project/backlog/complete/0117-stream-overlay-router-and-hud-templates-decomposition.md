---
id: '0117'
title: Stream Overlay Router and HUD Templates Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0056
- TASK-0080
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0007
- ADR-0013
target_release: 0.4.0
governing_prds:
- PRD-0004
- PRD-0011
governing_stories:
- US-0029
- US-0030
pr_url: https://github.com/tyevans/runefoble/pull/113
---
# TASK-0117: Stream Overlay Router and HUD Templates Modular Decomposition

## Status
Refined

## Summary
Decompose `gateway/api/src/gateway_api/routers/overlay.py` (416 lines, 83.2% of limit) into an APIRouter module (`overlay.py`), Pydantic models module (`overlay_models.py`), and HTML/CSS template generator module (`overlay_templates.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
`gateway/api/src/gateway_api/routers/overlay.py` aggregates several concerns in a single 416-line module:
1. Pydantic wire models (`PartyMemberVitals`, `RollAnimationData`, `PartyVitalsData`).
2. Large embedded multiline HTML/CSS template strings rendering the alpha-transparent HUD browser source page with responsive flex layouts, health bar gradients, dice animation popups, and client-side WebSocket reconnect logic.
3. Fast-path FastAPI route handlers for GET `/overlay/party-vitals/{session_id}` and WebSocket `/overlay/ws/{session_id}` with client connection tracking and broadcast coordination.

As upcoming enhancements introduce multi-track audio meters and camera framing controls for OBS overlays, this file will exceed 500 lines.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Server-side audience sanitization of secret DM notes and hidden traps.
- **ADR-0004: Lit Web Components and Storybook UI**: Alignment of styling tokens with Bauhaus aesthetic standards.
- **ADR-0007: API Gateway Architecture and Service Endpoints**: Gateway routing and WebSocket fanout infrastructure.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Presentation isolation for OBS overlays.

## Product & User Story References
- **Product Requirements**:
  - [`prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md`](../../product/accepted/prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md)
  - [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- **User Stories**:
  - [`us-0029-spectator-dynamic-cinematic-auto-camera.md`](../../user_stories/accepted/us-0029-spectator-dynamic-cinematic-auto-camera.md)
  - [`us-0030-obs-transparent-party-vitals-and-multi-track-audio.md`](../../user_stories/accepted/us-0030-obs-transparent-party-vitals-and-multi-track-audio.md)

## Detailed Specification & Implementation Plan
1. **Overlay Models (`gateway/api/src/gateway_api/overlay_models.py`)**:
   - Pydantic models for party vitals, camera parameters, and roll animations (< 80 lines).
2. **Overlay HUD Templates (`gateway/api/src/gateway_api/overlay_templates.py`)**:
   - Clean HTML template generation function `render_overlay_html(session_id, transparent, theme)` encapsulating HTML markup, CSS styling, and client WebSocket synchronization scripts (< 180 lines).
3. **Overlay Router (`gateway/api/src/gateway_api/routers/overlay.py`)**:
   - APIRouter handling HTTP template serving and WebSocket broadcast lifecycle, delegating rendering to `overlay_templates.py` (< 150 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal server file structure without altering HTTP or WebSocket API wire contracts.
- **Negotiable (N)**: File naming and helper function organization.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and improves template maintainability.
- **Estimable (E)**: Pure refactoring isolating Python strings and Pydantic schemas.
- **Small (S)**: Scope strictly isolated to `gateway/api/src/gateway_api/routers/overlay.py`; all resulting files < 190 lines.
- **Testable (T)**: Verified with `tests/test_blackbox_cinematic_director.py` and `tests/test_spectator_stream_overlay.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Decomposition Executed**:
   - `gateway/api/src/gateway_api/routers/overlay.py` decomposed into `overlay_models.py`, `overlay_templates.py`, and `overlay.py`.
2. **Strict Line Limits**:
   - Every file is strictly under 200 lines in compliance with Hard Invariant 6.
3. **Frontdoor Protocol Verification**:
   - GET `/overlay/party-vitals/{session_id}` returns valid HTML with embedded CSS styling.
   - WebSocket `/overlay/ws/{session_id}` broadcasts sanitized party vitals and camera movements without error.
4. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_cinematic_director.py tests/test_spectator_stream_overlay.py`.
