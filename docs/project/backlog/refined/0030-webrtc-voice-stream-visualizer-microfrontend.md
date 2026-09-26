---
id: 0030
title: WebRTC Audio Stream & Real-Time Waveform Visualizer in Voice Agent Microfrontend
status: Refined
created: 2026-09-25
dependencies: [TASK-0026, TASK-0027]
governing_adrs: [ADR-0004, ADR-0012, ADR-0013]
target_release: 0.1.0
---

# TASK-0030: WebRTC Audio Stream & Real-Time Waveform Visualizer in Voice Agent Microfrontend

## Status
Refined (Ready to pull)

## Summary
Enhance the `@runefoble/voice-agent-ui` microfrontend (`<runefoble-voice-controls>`) with an interactive WebAudio API waveform visualizer and WebRTC connection monitor. Allows players and GMs to observe live microphone input levels, active transmission packets, and audio DSP filter indications directly within the collaborative voice channel panel.

## Scope & Architectural Impact
- Service Bounded Context: `services/voice_agent/ui/`
- Component: `<runefoble-voice-controls>`
- Add WebAudio `AnalyserNode` canvas render loop displaying reactive audio waveforms.
- Emits `@voice-level` and `@voice-state` CustomEvents.
- Maintain Bauhaus theme styling with offset drop-shadow and `--rf-accent-*` palette.

## Definition of Ready Checklist
- [x] Bounded context ownership verified (`services/voice_agent/ui/`).
- [x] Governing ADRs cited (ADR-0004, ADR-0012, ADR-0013).
- [x] Testable blackbox acceptance criteria established.
- [x] Storybook stories planned (Inactive, Waveform Active, Low Bandwidth warning).

## Definition of Done
1. Visualizer implemented in `services/voice_agent/ui/src/runefoble-voice-controls.ts`.
2. Interactive Storybook stories added in `services/voice_agent/ui/src/runefoble-voice-controls.stories.ts` with zero console errors.
3. Frontdoor blackbox tests in `tests/test_microfrontends.py` verify component properties and events.
4. `make test` and `make lint` pass cleanly.
5. File length strictly under 500 lines.
