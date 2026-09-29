---
id: '0481'
title: App Shell DM Vocal Modulator Integration & Live Session Preset Synchronization
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0160
- TASK-0358
- TASK-0480
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0004
- PRD-0023
governing_stories:
- US-0011
- US-0020
target_release: 0.9.0
---

# TASK-0481: App Shell DM Vocal Modulator Integration & Live Session Preset Synchronization

## Status
Proposed

## Summary
Wire the `<runefoble-vocal-modulator>` custom element into the App Shell DM inspector / tabletop toolbar (`frontend/src/runefoble-app.ts`), add reactive custom event bindings for `@preset-select` and `@slider-change`, persist and dispatch active modulation parameters through `AppDataService` and the live session WebSocket mesh, and display an active voice modulation pill badge on the tabletop HUD.

## Problem Statement
The `<runefoble-vocal-modulator>` Web Component exists within `services/voice_agent/ui` and is exported in `frontend/src/components/runefoble-vocal-modulator.ts`. However, it is never instantiated or mounted inside `frontend/src/runefoble-app.ts`. A Dungeon Master (Evelyn) running a live game session has no UI controls in the App Shell to activate NPC voice presets or adjust pitch and formant sliders. Furthermore, when voice modulation is active, other players on the tactical board receive no visual indication that the DM is speaking in-character through an NPC filter.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Encapsulating vocal modulator controls within Lit Web Components with Shadow DOM boundary isolation.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Styling the DM vocal modulator drawer and HUD status badge with Bauhaus geometric design tokens.
- **ADR-0013: Frontend Microfrontend Architecture**: Composing microfrontends from `@runefoble/voice-agent-ui` into the App Shell.

## Product & User Story References
- [`prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md`](../../product/accepted/prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0011-dynamic-voice-filters-for-afflicted-characters.md`](../../user_stories/accepted/us-0011-dynamic-voice-filters-for-afflicted-characters.md)
- [`us-0020-dm-vocal-modulator-with-realtime-npc-filtering.md`](../../user_stories/accepted/us-0020-dm-vocal-modulator-with-realtime-npc-filtering.md)

## Scope of Work
1. **App Shell DM Toolbar Mounting (`frontend/src/runefoble-app.ts`)**:
   - Add a toggle button `"🎙️ NPC Voice Modulator"` in the DM Party Inspector panel when the current user has DM/Owner privileges.
   - Render `<runefoble-vocal-modulator>` inside a slide-out drawer or popover in the live tabletop view.
   - Pass active session ID, current preset, pitch shift, and formant parameters as element properties.
2. **Event Listeners and State Synchronization**:
   - Bind `@preset-select` to update the active preset and send parameter adjustments to the backend via `appDataService.setVoiceModulatorPreset()`.
   - Bind `@slider-change` to adjust real-time pitch, formant, and resonance values dynamically.
   - Synchronize modulation state changes over the session WebSocket mesh (`type: "voice_modulator_changed"`).
3. **Tabletop HUD Voice Indicator**:
   - Display a distinct Bauhaus pill badge (`"🎭 Voice: Ancient Dragon"`) in the top navigation bar or HUD audio level widget when modulation is active.
   - Provide one-click bypass toggle to instantly revert to raw microphone pass-through.
4. **App Data Service Enhancements (`frontend/src/services/app-data-service.ts`)**:
   - Add `fetchVoicePresets(): Promise<NPCVoicePreset[]>` with offline fixture fallbacks.
   - Add `applyVoiceModulation(sessionId: string, params: ModulationParams): Promise<void>`.

## Definition of Done
1. DM users can open the vocal modulator drawer directly from the tabletop interface.
2. Selecting an NPC voice preset updates element state, dispatches Gateway API updates, and synchronizes across session peers.
3. The HUD clearly displays the active voice preset name and allows instant bypass.
4. Non-DM players see the in-character voice status badge without accessing DM control sliders.
5. All source files conform strictly to Hard Invariant 6 (< 500 lines).
