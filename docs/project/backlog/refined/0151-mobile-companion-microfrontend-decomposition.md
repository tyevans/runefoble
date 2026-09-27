---
id: '0151'
title: Mobile Companion Microfrontend Component and Audio Visualizer Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0128
- TASK-0134
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0019
governing_stories:
- US-0059
target_release: 0.5.0
---

# TASK-0151: Mobile Companion Microfrontend Component and Audio Visualizer Decomposition

## Status
Refined

## Summary
Decompose `services/voice_agent/ui/src/runefoble-mobile-companion.ts` (386 lines, 77.2% of limit) into focused sub-components under `services/voice_agent/ui/src/mobile_companion/` (`audio_stream_controller.ts`, `haptic_ping_panel.ts`, `connection_status_badge.ts`), keeping all source files < 150 lines per Hard Invariant 6.

## Problem Statement
`runefoble-mobile-companion.ts` combines low-bandwidth adaptive Opus WebRTC stream management, tactile vibration / haptic ping triggering, whisper transcript cards, and battery-optimized status indicators in a single 386-line file. Decomposing these concerns prevents invariant breaches as secret DM whisper audio features expand.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Atomic custom element composition.
- **ADR-0012: Theming System and Accessibility Contrast Invariants**: Accessible haptic cue indicators and dark/light tokens.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Microfrontend vendored inside `services/voice_agent/ui/`.

## Product & User Story References
- **Product Requirement**: [`prd-0019-spatial-companion-mobile-and-haptic-ping-gateway.md`](../../product/accepted/prd-0019-spatial-companion-mobile-and-haptic-ping-gateway.md)
- **User Story**: [`us-0059-spatial-companion-mobile-and-haptic-ping-gateway.md`](../../user_stories/accepted/us-0059-spatial-companion-mobile-and-haptic-ping-gateway.md)

## Detailed Specification & Implementation Plan
1. **Audio Stream Controller (`services/voice_agent/ui/src/mobile_companion/audio_controller.ts`)**:
   - WebRTC audio stream playback, bitrate quality selector, and mute controls (< 130 lines).
2. **Haptic Ping Panel (`services/voice_agent/ui/src/mobile_companion/haptic_panel.ts`)**:
   - Secret DM vibration pulse patterns, visual ripple triggers, and acknowledgment taps (< 120 lines).
3. **Connection Status Badge (`services/voice_agent/ui/src/mobile_companion/connection_badge.ts`)**:
   - Connection health indicator, latency readout, and reconnection button (< 90 lines).
4. **Styles Decomposition (`services/voice_agent/ui/src/mobile_companion/styles/`)**:
   - Extract mobile viewport styles and tactile badge styles (< 110 lines each).
5. **Root Orchestrator (`services/voice_agent/ui/src/runefoble-mobile-companion.ts`)**:
   - Compose sub-components into `<runefoble-mobile-companion>` (< 120 lines).
6. **Storybook Stories**:
   - Update `runefoble-mobile-companion.stories.ts` with sub-component stories.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal frontend refactoring with zero change to WebSocket or WebRTC protocol.
- **Negotiable (N)**: Sub-component breakdown can adapt to touch screen ergonomics.
- **Valuable (V)**: Protects against file size violations and improves maintainability of mobile companion code.
- **Estimable (E)**: Standard Lit component extraction.
- **Small (S)**: Bounded strictly to `services/voice_agent/ui/src/mobile_companion/`; all files < 150 lines.
- **Testable (T)**: Storybook stories and existing blackbox tests verify functionality.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular UI Architecture**:
   - `services/voice_agent/ui/src/mobile_companion/` created with focused sub-components.
   - All source and style files strictly < 180 lines.
2. **Storybook & Frontdoor Test Verification**:
   - Storybook stories render without console errors.
   - Frontdoor blackbox tests in `tests/test_blackbox_voice_agent/` pass with zero regressions.
3. **Quality Gates**:
   - Passes `uv run ruff check .` and frontend build verification.
