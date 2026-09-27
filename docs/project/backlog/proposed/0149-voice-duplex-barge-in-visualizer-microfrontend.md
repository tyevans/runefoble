---
id: '0149'
title: Voice Duplex Audio Settings & Real-Time Barge-In Visualizer Microfrontend
status: Proposed
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
governing_stories:
- US-0060
target_release: 0.6.0
---

# TASK-0149: Voice Duplex Audio Settings & Real-Time Barge-In Visualizer Microfrontend

## Status
Proposed

## Summary
Build the `<runefoble-voice-duplex-controls>` Web Component within `services/voice_agent/ui/src/` to provide visual feedback for speech interruptions (barge-in), VAD sensitivity sliders, acoustic ducking meters, and live cancellation indicators in Storybook and the App Shell.

## Problem Statement
When players interrupt The Watcher AI DM via zero-latency neural duplex (TASK-0141), users need clear visual feedback indicating that their speech was recognized, the DM audio stream was safely canceled, and mic input is actively feeding into intent processing.

## Governing Architecture & ADRs
- **ADR-0004: Frontend Application Architecture**: Clean Lit Web Component design with Shadow DOM.
- **ADR-0012: Theming System and Accessibility Contrast Invariants**: Accessible visual indicators across Dark/Light themes.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Component vendored inside `services/voice_agent/ui/`.

## Scope of Work
1. **Barge-In Visualizer Component (`services/voice_agent/ui/src/runefoble-voice-duplex-controls.ts`)**:
   - Visual waveform indicator showing player interjection events and DM audio fadeout (< 180 lines).
2. **Duplex Settings & VAD Calibration**:
   - Sliders for interruption sensitivity threshold and microphone acoustic echo suppression (< 140 lines).
3. **Storybook Stories**:
   - Interactive stories demonstrating idle, player interjection, and DM audio muted states.
4. **Manifest Registration**:
   - Expose `<runefoble-voice-duplex-controls>` via `/ui/manifest`.
