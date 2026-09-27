---
id: '0160'
title: DM Vocal Modulator Controls & Preset Selector Microfrontend
status: Proposed
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
Proposed

## Summary
Build `<runefoble-vocal-modulator>` Web Component within `services/voice_agent/ui/src/` providing quick-toggle NPC vocal archetype presets ("Dragon", "Goblin", "Ethereal"), live pitch shift sliders, and outgoing formant visualizers in Storybook and the DM Co-Pilot panel.

## Problem Statement
DMs roleplaying NPCs need instant, one-touch access to vocal modulators without opening separate third-party voice changer software. Clear visual cues indicating whether a voice filter is currently active prevent accidental in-character leakage.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Encapsulated Web Component.
- **ADR-0012: Theming System and Accessibility Contrast Invariants**: Active filter badges and status indicators.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Vendored in `services/voice_agent/ui/`.

## Scope of Work
1. **Preset Carousel & Quick Selector**:
   - One-tap buttons for common creature profiles with keyboard shortcuts (< 130 lines).
2. **Formant & Pitch Sliders**:
   - Advanced panel for fine-tuning resonance and pitch offset (< 120 lines).
3. **Active Voice Indicator**:
   - Glowing indicator showing current DSP filter status on DM microphone stream (< 90 lines).
4. **Storybook Stories**:
   - Stories showcasing preset toggles, slider interactions, and active indicator states.
5. **Manifest Export**:
   - Register custom element in `services/voice_agent/` UI manifest.
