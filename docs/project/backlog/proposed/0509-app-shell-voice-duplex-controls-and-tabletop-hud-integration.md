---
id: '0509'
title: App Shell Voice Duplex Controls and Tabletop HUD Integration
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0073
- TASK-0149
- TASK-0508
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0020
- PRD-0023
governing_stories:
- US-0060
- US-0065
target_release: 0.9.0
---

# TASK-0509: App Shell Voice Duplex Controls and Tabletop HUD Integration

## Status
Proposed

## Summary
Integrate the `<runefoble-voice-duplex-controls>` Web Component into the App Shell settings modal (Audio & Voice tab) and the tabletop live voice HUD (`frontend/src/views/tabletop-view.ts`), connecting to the Gateway duplex WebSocket endpoint, binding real-time barge-in interruption visualizers and VAD sensitivity sliders, and preserving Bauhaus theme design tokens per ADR-0012 and PRD-0020.

## Problem Statement
While `<runefoble-voice-duplex-controls>` was developed in `services/voice_agent/ui/src/runefoble-voice-duplex-controls.ts` and verified in Storybook isolation (TASK-0149), it is not mounted in the frontend App Shell or active tabletop VTT. Players playing in live sessions have no UI controls to calibrate their microphone barge-in threshold, observe real-time speech energy meters, or see visual feedback when an interruption halts AI DM narration.

## Governing Architecture & ADRs
- **ADR-0004: Frontend Settings Modal and Theme Mode Orchestration**: Embedding duplex audio settings into the existing `<runefoble-settings-modal>` audio panel.
- **ADR-0012: CSS Variables for Bauhaus Theme System**: Inheriting Bauhaus geometric design tokens and dark/light contrast rules.
- **ADR-0013: Frontend Microfrontend Architecture**: Composing Lit Web Components via custom element registration and Shadow DOM encapsulation.

## Product & User Story References
- [`prd-0020-zero-latency-neural-voice-duplex-and-interruption.md`](../../product/accepted/prd-0020-zero-latency-neural-voice-duplex-and-interruption.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0060-zero-latency-neural-voice-duplex.md`](../../user_stories/accepted/us-0060-zero-latency-neural-voice-duplex.md)

## Scope of Work
1. **Settings Modal Audio Panel Integration (`frontend/src/components/settings/audio-panel.ts`)**:
   - Embed `<runefoble-voice-duplex-controls>` with mode `"settings"` inside the Audio & Voice settings tab.
   - Bind VAD sensitivity threshold and AEC toggle to local storage configuration.
2. **Tabletop HUD Integration (`frontend/src/views/tabletop-view.ts`)**:
   - Embed compact duplex visualizer badge displaying live audio stream state (`connected`, `monitoring`, `interrupted`) with interruption latency readout.
   - Connect component to Gateway duplex WebSocket URL (`/ws/voice/duplex/{session_id}`).
   - Handle custom event `duplex-interrupted` to trigger subtle UI flash and notify tabletop activity feed.
3. **Storybook & Manifest Alignment**:
   - Verify App Shell view storybook stories reflect voice duplex integration.

## Definition of Done
1. `<runefoble-voice-duplex-controls>` renders within the Settings Modal Audio tab with functional VAD sliders and AEC toggle.
2. Tabletop HUD displays live duplex status badge and displays "BARGE-IN DETECTED" banner when speech onset occurs.
3. All styles adhere to Bauhaus design tokens and maintain WCAG AAA contrast in both light and dark modes.
