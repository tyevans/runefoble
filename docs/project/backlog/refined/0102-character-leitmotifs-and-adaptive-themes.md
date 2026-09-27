---
id: '0102'
title: Personal Character Leitmotifs & Adaptive Musical Signatures
status: in-progress
created: 2026-09-26
dependencies:
- TASK-0006
- TASK-0021
- TASK-0050
governing_adrs:
- ADR-0002
- ADR-0006
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0016
governing_stories:
- US-0046
target_release: 0.4.0
claimed_by: worker-0102
branch: feat/0102-character-leitmotifs-and-adaptive-themes
---
# TASK-0102: Personal Character Leitmotifs & Adaptive Musical Signatures

## Status
Refined

## Summary
Incorporate personalized musical leitmotifs into the adaptive audio pipeline, dynamically blending distinct instrument themes and heroic fanfares during character triumphs, clutch criticals, and death save struggles.

## Problem Statement
Characters lack individual auditory identity in game sessions (PRD-0016, US-0046). Expressive roleplayers like Nadia want heroic lute flourishes or somber cello melodies to weave seamlessly into combat tension scores when their character takes center stage.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Architecture & Voice Audio**: WebRTC audio stream and stem mixing coordination.
- **ADR-0006: Redis Streams Event Bus**: Event subscriptions for `DiceRolled`, `CriticalHitScored`, `CharacterConditionApplied`, and `LeitmotifTriggered`.
- **ADR-0010: OpenTelemetry Tracing & Metrics**: Tracing audio stem latency and mixer trigger timings.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Lit Web Component `<runefoble-leitmotif-config>` vendored in `services/soundscape/ui/src/`.

## Product & User Story References
- **Product Requirement**: [`prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md`](../../product/accepted/prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md)
- **User Story**: [`us-0046-character-musical-leitmotifs-and-dynamic-themes.md`](../../user_stories/accepted/us-0046-character-musical-leitmotifs-and-dynamic-themes.md)

## Detailed Specification & Implementation Plan
1. **Character Leitmotif Profile Modeling (`services/soundscape/src/soundscape/leitmotif.py`)**:
   - Configuration schema defining instrument timbre (brass, woodwind, strings, lute), tempo multiplier, and triumphant/somber audio stem URLs.
2. **Adaptive Audio Layering Engine**:
   - Sub-250ms dynamic stem cross-fading and stinger triggering on domain events (`CriticalHitRolled`, `DeathSaveStarted`).
   - Smooth volume envelopes preventing abrupt transitions or audio clipping.
3. **Automatic Speech Ducking**:
   - WebAudio sidechain compressor applying -12dB attenuation to leitmotif stems whenever human voice activity is detected.
4. **Microfrontend Configuration Widget (`services/soundscape/ui/src/runefoble-leitmotif-config.ts`)**:
   - Interactive widget allowing players to audition stems and assign instrument styles.
5. **Frontdoor Blackbox Verification**:
   - Blackbox test suite validating leitmotif event dispatch, audio mixing state transitions, and volume envelope parameters.

## INVEST Criteria Evaluation
- **Independent (I)**: Enhances soundscape audio engine without altering dice rolling or rules mechanics.
- **Negotiable (N)**: Preset stem library catalog vs custom user-uploaded stems.
- **Valuable (V)**: Gives characters distinct audio identities and elevates key session moments.
- **Estimable (E)**: Builds directly on existing `services/soundscape/` stem mixer abstractions.
- **Small (S)**: Scope strictly isolated to `services/soundscape/`; all modules < 300 lines.
- **Testable (T)**: Assertions verify event dispatch and mixer state through public REST and WebSocket endpoints.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Leitmotif Trigger Pipeline**:
   - Audio mixer in `services/soundscape/` handles `CriticalHitScored` and `DeathSaveStarted` domain events, scheduling character leitmotifs within 250ms.
2. **Speech Ducking Integration**:
   - Soundscape mixer applies -12dB attenuation to active leitmotif stems during active speech detection.
3. **Microfrontend Element & Storybook**:
   - `<runefoble-leitmotif-config>` built with Shadow DOM and Bauhaus design tokens, verified in Storybook with zero errors.
4. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_character_leitmotifs.py` validating character leitmotif configuration, event triggering, and audio mixer outputs via public REST endpoints.
5. **Quality Gates**:
   - Conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `uv run pytest tests/test_blackbox_character_leitmotifs.py` and frontend build.
