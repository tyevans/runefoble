---
id: '0109'
title: Dynamic Soundscape Mixing Panel Microfrontend and WebAudio Ducking Controls
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0050
- TASK-0095
governing_adrs:
- ADR-0003
- ADR-0004
- ADR-0006
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0010
governing_stories:
- US-0039
- US-0053
target_release: 0.4.0
---

# TASK-0109: Dynamic Soundscape Mixing Panel Microfrontend and WebAudio Ducking Controls

## Status
Proposed

## Summary
Develop the Lit Web Component microfrontend `<runefoble-soundscape-controls>` within `services/soundscape/ui/` to expose dynamic stem volume sliders, manual DM soundboard foley buttons, tension state indicators, and client-side WebAudio ducking configuration.

## Problem Statement
The dynamic soundscape service calculates encounter tension and generates audio stem playlists (TASK-0050, PRD-0010). However, Dungeon Masters (Evelyn) need a direct graphical soundboard to trigger instant acoustic effects and adjust ambient audio levels live during play, fulfilling US-0039 and US-0053.

## Governing Architecture & ADRs
- **ADR-0003**: UV Monorepo Workspace (`services/soundscape`).
- **ADR-0004**: Lit Web Components and Storybook UI (Shadow DOM, Bauhaus tokens).
- **ADR-0006**: Redis Streams Event Bus (broadcast `SoundEffectTriggered` and `TensionLevelChanged`).
- **ADR-0007**: Gateway API and WebSocket Fanout.
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring (`services/soundscape/ui/`).

## Scope of Work
1. **Stem Volume & Tension Controls**:
   - Master volume and multi-channel stem sliders (melody, percussion, drone, ambient).
   - Tension state indicator with manual override toggle for DMs.
2. **Tactile Soundboard Grid**:
   - Customizable foley sound buttons (thunder, door slam, steel clash, roar) with auditory earcon feedback.
3. **WebAudio Ducking Coordinator**:
   - Client-side audio ducking (-12dB) triggered by voice chat activity or soundboard cues.
4. **Storybook Stories & Manifest**:
   - Interactive Storybook coverage with simulated stem playback and ducking animations.
   - Register component under `services/soundscape/ui/` manifest.
5. **Frontdoor Blackbox Verification**:
   - Blackbox tests for HTTP routes and WebSocket audio event propagation.
