---
id: 0109
title: Dynamic Soundscape Mixing Panel Microfrontend and WebAudio Ducking Controls
status: Complete
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
pr_url: https://github.com/tyevans/runefoble/pull/110
---
# TASK-0109: Dynamic Soundscape Mixing Panel Microfrontend and WebAudio Ducking Controls

## Status
Refined

## Summary
Develop the Lit Web Component microfrontend `<runefoble-soundscape-controls>` within `services/soundscape/ui/` to expose dynamic stem volume sliders, manual DM soundboard foley buttons, tension state indicators, and client-side WebAudio ducking configuration.

## Problem Statement
The dynamic soundscape service calculates encounter tension and generates audio stem playlists (TASK-0050, PRD-0010). However, Dungeon Masters (Evelyn) need a direct graphical soundboard to trigger instant acoustic effects and adjust ambient audio levels live during play, fulfilling US-0039 and US-0053.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Packaging UI within `services/soundscape/ui/`.
- **ADR-0004: Lit Web Components and Storybook UI**: Shadow DOM encapsulation with Bauhaus geometric design tokens.
- **ADR-0006: Redis Streams Event Bus**: Event broadcasts for `SoundEffectTriggered` and `TensionLevelChanged`.
- **ADR-0007: API Gateway Architecture and Service Endpoints**: Gateway WebSocket broadcast fanout for acoustic cues.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Service-vendored UI package serving `/ui/manifest`.

## Product & User Story References
- **Product Requirement**: [`prd-0010-adaptive-soundscape-foley-and-tension-scoring.md`](../../product/accepted/prd-0010-adaptive-soundscape-foley-and-tension-scoring.md)
- **User Stories**:
  - [`us-0039-encounter-tension-adaptive-scoring-and-foley.md`](../../user_stories/accepted/us-0039-encounter-tension-adaptive-scoring-and-foley.md)
  - [`us-0053-dm-manual-soundboard-and-foley-triggers.md`](../../user_stories/accepted/us-0053-dm-manual-soundboard-and-foley-triggers.md)

## Detailed Specification & Implementation Plan
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

## INVEST Criteria Evaluation
- **Independent (I)**: Decoupled UI consuming soundscape service endpoints and Redis audio events.
- **Negotiable (N)**: Soundboard preset buttons vs dynamic library picker can be adapted.
- **Valuable (V)**: Gives DMs live auditory storytelling control without complex external software.
- **Estimable (E)**: Follows existing microfrontend patterns.
- **Small (S)**: Scope strictly isolated to `services/soundscape/ui/`; all files < 200 lines.
- **Testable (T)**: Frontdoor blackbox tests asserting component registration, stem volume updates, and foley event emissions.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Element**:
   - `<runefoble-soundscape-controls>` component rendered with complete Shadow DOM encapsulation and Bauhaus tokens.
2. **Storybook Stories**:
   - Stories for quiet ambient, high-tension combat, and active foley playback with zero console errors.
3. **Microfrontend Manifest**:
   - Manifest served at `/ui/manifest` exposing tags, styles, and script entries per ADR-0013.
4. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_soundscape_ui.py` validating component registration, manifest endpoint, and REST/WebSocket data binding.
5. **Quality Gates**:
   - Strictly conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `pnpm run build` and `uv run pytest tests/test_blackbox_soundscape_ui.py`.
