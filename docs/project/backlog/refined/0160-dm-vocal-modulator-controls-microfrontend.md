---
id: '0160'
title: DM Vocal Modulator Controls & Preset Selector Microfrontend
status: Refined
created: 2026-09-26
dependencies:
- TASK-0157
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0004
governing_stories:
- US-0020
target_release: 0.6.0
---

# TASK-0160: DM Vocal Modulator Controls & Preset Selector Microfrontend

## Status
Refined

## Summary
Build `<runefoble-vocal-modulator>` Web Component within `services/voice_agent/ui/src/` providing quick-toggle NPC vocal archetype presets ("Dragon", "Goblin", "Ethereal"), live pitch shift sliders, and outgoing formant visualizers in Storybook and the DM Co-Pilot panel.

## Problem Statement
DMs roleplaying NPCs need instant, one-touch access to vocal modulators without opening separate third-party voice changer software. Clear visual cues indicating whether a voice filter is currently active prevent accidental in-character leakage.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Encapsulated Web Component with Shadow DOM.
- **ADR-0012: Theming System and Accessibility Contrast Invariants**: Active filter badges, accessible sliders, and high-contrast status indicators.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Vendored strictly in `services/voice_agent/ui/`.

## Product & User Story References
- **Product Requirement**: [`prd-0004-voice-streaming-and-dsp-pipeline.md`](../../product/accepted/prd-0004-voice-streaming-and-dsp-pipeline.md)
- **User Story**: [`us-0020-dm-voice-modulation-and-npc-personas.md`](../../user_stories/accepted/us-0020-dm-voice-modulation-and-npc-personas.md)

## Detailed Specification & Implementation Plan
1. **Preset Carousel & Quick Selector (`services/voice_agent/ui/src/runefoble-vocal-modulator.ts`)**:
   - One-tap buttons for common creature profiles with keyboard shortcuts and visual indicators (< 140 lines).
2. **Formant & Pitch Sliders (`services/voice_agent/ui/src/runefoble-vocal-sliders.ts`)**:
   - Advanced panel for fine-tuning resonance and pitch offset (< 120 lines).
3. **Component Styles (`services/voice_agent/ui/src/runefoble-vocal-modulator.styles.ts`)**:
   - Glowing active LED indicator and Bauhaus-aligned controls (< 110 lines).
4. **Storybook Stories (`services/voice_agent/ui/src/runefoble-vocal-modulator.stories.ts`)**:
   - Stories showcasing preset toggles, slider interactions, and active indicator states (< 130 lines).
5. **Manifest Export & Integration**:
   - Register custom element in `services/voice_agent/` UI manifest and verify `/ui/manifest`.

## INVEST Criteria Evaluation
- **Independent (I)**: Consumes vocal modulation REST endpoints from TASK-0157 without direct coupling to audio hardware.
- **Negotiable (N)**: Preset icons and slider increments can be configured.
- **Valuable (V)**: Gives DMs intuitive physical-like soundboard controls for NPC voices.
- **Estimable (E)**: Standard Lit component with range inputs and event dispatches.
- **Small (S)**: Bounded strictly to `services/voice_agent/ui/src/`; all files < 160 lines.
- **Testable (T)**: Storybook stories verify visual rendering and blackbox tests verify `/ui/manifest`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Architecture**:
   - Built and vendored inside `services/voice_agent/ui/`.
   - All TypeScript and CSS files strictly < 160 lines per Hard Invariant 6.
2. **Storybook Verification**:
   - Interactive stories render cleanly in Storybook with zero console errors.
3. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_vocal_modulator_ui/` asserts `/ui/manifest` export and custom element script bundles.
4. **Quality Gates**:
   - Passes `pnpm run build`, `uv run ruff check .`, and `uv run ruff format --check .`.
