---
id: '0134'
title: Spatial Companion Mobile WebRTC Audio & Haptic Controller Microfrontend
status: Refined
created: 2026-09-26
dependencies:
- TASK-0002
- TASK-0033
- TASK-0128
governing_adrs:
- ADR-0002
- ADR-0005
- ADR-0013
governing_prds:
- PRD-0004
governing_stories:
- US-0059
target_release: 0.5.0
---

# TASK-0134: Spatial Companion Mobile WebRTC Audio & Haptic Controller Microfrontend

## Status
Refined

## Summary
Build the responsive mobile companion Web Component `<runefoble-mobile-companion>` in `services/voice_agent/ui/src/` providing tactile haptic feedback pulses (via `navigator.vibrate`), low-bandwidth WebRTC audio controls, lockscreen secret DM whisper display, and push-to-talk integration with Bauhaus design tokens.

## Problem Statement
While TASK-0128 implements the backend mobile gateway and WebSocket haptic payload protocol, mobile participants still require a dedicated, battery-efficient, tactile client microfrontend (PRD-0004, US-0059). Players using phones or secondary tablets need an intuitive interface that vibrates upon receiving private narrative DM whispers and provides single-thumb push-to-talk voice streaming.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Architecture & Voice Audio**: Integration with WebAudio pipeline and low-bandwidth Opus voice streaming.
- **ADR-0005: Kubernetes-First Infrastructure**: Clean Traefik routing to `/voice/ui/manifest`.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Self-contained component package vendored strictly inside `services/voice_agent/ui/src/` with Shadow DOM and Bauhaus design tokens.

## Product & User Story References
- **Product Requirement**: [`prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md`](../../product/accepted/prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md)
- **User Story**: [`us-0059-spatial-companion-mobile-and-haptic-ping-gateway.md`](../../user_stories/accepted/us-0059-spatial-companion-mobile-and-haptic-ping-gateway.md)

## Detailed Specification & Implementation Plan
1. **Mobile Companion Web Component (`services/voice_agent/ui/src/runefoble-mobile-companion.ts`)**:
   - `<runefoble-mobile-companion>` Lit component featuring large thumb-friendly PTT button, active channel indicator, and connection status pill.
   - Haptic vibration dispatcher listening for `haptic_vibration` WebSocket frames and triggering `navigator.vibrate(pattern)` with graceful fallback on non-vibrating devices.
2. **Diegetic Secret Whisper Overlay**:
   - Subtle modal/banner revealing private narrative whispers with acoustic cue, dismiss action, and privacy blur.
3. **Low-Bandwidth WebAudio Stream Controller**:
   - Audio buffer monitor and adaptive sample rate indicator reflecting cellular connection quality.
4. **Storybook Verification & Component Manifest**:
   - Interactive stories (`runefoble-mobile-companion.stories.ts`) with knobs for simulating whisper vibrations, audio streaming states, and offline reconnections.
   - Register component in `services/voice_agent/ui/manifest.json`.

## INVEST Criteria Evaluation
- **Independent (I)**: Consumes public gateway WebSockets and operates independently of desktop canvas views.
- **Negotiable (N)**: Haptic pulse timings and UI button ergonomics can be adjusted.
- **Valuable (V)**: Empowers mobile players to participate with immersive physical feedback without burning battery on desktop rendering.
- **Estimable (E)**: Builds upon existing WebRTC visualizer (TASK-0030) and voice signaling (TASK-0033).
- **Small (S)**: Bounded strictly to `services/voice_agent/ui/src/`; all files < 350 lines.
- **Testable (T)**: Frontdoor tests verify WebSocket message parsing, DOM event dispatch, and mock vibration triggers.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Component Delivery**:
   - `<runefoble-mobile-companion>` built and exported from `services/voice_agent/ui/src/`.
   - Manifest entry registered and served at `/ui/manifest`.
2. **Storybook Stories**:
   - `runefoble-mobile-companion.stories.ts` with controls for incoming whispers and connection modes.
3. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_mobile_companion_ui.py` validating UI manifest registration and component rendering.
4. **Quality Gates**:
   - Conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `pnpm test` and `pnpm build`.
