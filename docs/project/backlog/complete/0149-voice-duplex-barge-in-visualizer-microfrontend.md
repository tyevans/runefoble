---
id: 0149
title: Voice Duplex Audio Settings & Real-Time Barge-In Visualizer Microfrontend
status: Complete
created: 2026-09-26
dependencies:
- TASK-0030
- TASK-0109
- TASK-0141
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0004
- PRD-0020
governing_stories:
- US-0060
target_release: 0.6.0
pr_url: https://github.com/tyevans/runefoble/pull/166
---
# TASK-0149: Voice Duplex Audio Settings & Real-Time Barge-In Visualizer Microfrontend

## Status
Refined

## Summary
Build the `<runefoble-voice-duplex-controls>` Web Component within `services/voice_agent/ui/src/` to provide visual feedback for speech interruptions (barge-in), VAD sensitivity sliders, acoustic ducking meters, and live cancellation indicators in Storybook and the App Shell.

## Problem Statement
When players interrupt The Watcher AI DM via zero-latency neural duplex (TASK-0141), users need clear visual feedback indicating that their speech was recognized, the DM audio stream was safely canceled, and mic input is actively feeding into intent processing.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Atomic custom element composition and Storybook coverage.
- **ADR-0012: Theming System and Accessibility Contrast Invariants**: Accessible visual indicators and tokens across Dark/Light themes.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Component vendored strictly inside `services/voice_agent/ui/`.

## Product & User Story References
- **Product Requirement**: [`prd-0020-zero-latency-neural-voice-duplex-and-interruption.md`](../../product/accepted/prd-0020-zero-latency-neural-voice-duplex-and-interruption.md)
- **User Story**: [`us-0060-zero-latency-neural-voice-duplex.md`](../../user_stories/accepted/us-0060-zero-latency-neural-voice-duplex.md)

## Detailed Specification & Implementation Plan
1. **Barge-In Visualizer Component (`services/voice_agent/ui/src/runefoble-voice-duplex-controls.ts`)**:
   - Visual waveform indicator showing player interjection events, soft audio crossfade cancellation, and active mic level (< 180 lines).
2. **Duplex Settings & VAD Calibration (`services/voice_agent/ui/src/duplex/settings_panel.ts`)**:
   - Sliders for interruption sensitivity threshold, mic ducking gain, and acoustic echo suppression (< 140 lines).
3. **Styles Decomposition (`services/voice_agent/ui/src/duplex/styles/`)**:
   - Modular CSS files for duplex meters and control inputs (< 110 lines each).
4. **Storybook Stories (`services/voice_agent/ui/src/runefoble-voice-duplex-controls.stories.ts`)**:
   - Interactive stories demonstrating idle, player interjection, and DM audio muted states.
5. **Manifest Registration**:
   - Expose `<runefoble-voice-duplex-controls>` via `/ui/manifest` in `services/voice_agent/src/voice_agent/main.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Consumes existing duplex WebSocket protocol without modifying backend voice models.
- **Negotiable (N)**: Meter layout and slider ranges can adjust based on UX feedback.
- **Valuable (V)**: Delivers vital visual confirmation for natural speech barge-in.
- **Estimable (E)**: Standard Lit custom element with WebAudio visualizer hooks.
- **Small (S)**: Bounded strictly to `services/voice_agent/ui/`; all files < 180 lines.
- **Testable (T)**: Frontdoor blackbox tests verify `/ui/manifest` and Storybook renders without error.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Architecture**:
   - `<runefoble-voice-duplex-controls>` implemented with Shadow DOM in `services/voice_agent/ui/`.
   - Manifest endpoint `GET /ui/manifest` returns custom element definition.
   - All source and style files strictly < 190 lines.
2. **Storybook & Frontdoor Test Verification**:
   - Interactive Storybook stories render without console errors.
   - Blackbox tests verify manifest response and UI rendering.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_voice_agent/` and frontend build verification.
