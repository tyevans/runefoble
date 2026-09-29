---
id: '0477'
title: Pre-Game Session Lobby Microphone Preflight and Audio Calibration Component
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0033
- TASK-0212
- TASK-0249
governing_adrs:
- ADR-0002
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0004
- PRD-0020
- PRD-0023
governing_stories:
- US-0065
target_release: 0.9.0
---

# TASK-0477: Pre-Game Session Lobby Microphone Preflight and Audio Calibration Component

## Status
Proposed

## Summary
Add an audio hardware preflight panel component (`<runefoble-audio-preflight>`) to the Pre-Game Session Lobby microfrontend (`services/game_session/ui/src/lobby/`), allowing players to select their microphone input device, monitor live input volume with a WebAudio VU meter, test audio loopback, and broadcast an `audioReady: true` presence state before the Game Master launches the live session.

## Problem Statement
PRD-0023 Section 2 and 4 describe the Pre-Game Session Lobby as the staging environment where players verify audio before entering the live VTT. Currently, `<runefoble-session-lobby>` only provides character selection and readiness toggles; it contains no audio device enumeration, volume testing, or mic verification tools. Players frequently enter live tabletop games with misconfigured default input devices or muted microphones, disrupting early narrative pacing and forcing immediate restarts. Providing a pre-game audio preflight widget in the lobby ensures smooth voice engagement before game launch.

## Governing Architecture & ADRs
- **ADR-0002: Live WebRTC Audio Streaming**: Validating input hardware readiness prior to establishing bidirectional audio rooms.
- **ADR-0004: Lit Web Components and Storybook UI**: Developing an interactive Lit component with Shadow DOM and WebAudio API.
- **ADR-0012: Design System Color Tokens**: Bauhaus-themed VU meters and volume level indicators with WCAG AA compliance.
- **ADR-0013: Frontend Microfrontend Architecture**: Integrating cleanly into the `game_session` lobby bounded context.

## Product & User Story References
- [`prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md`](../../product/accepted/prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md)
- [`prd-0020-zero-latency-neural-voice-duplex-and-interruption.md`](../../product/accepted/prd-0020-zero-latency-neural-voice-duplex-and-interruption.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)

## Scope of Work
1. **Audio Preflight Web Component (`services/game_session/ui/src/lobby/runefoble-audio-preflight.ts`)**:
   - Query `navigator.mediaDevices.enumerateDevices()` to populate audio input device dropdown.
   - On device selection or "Test Mic" click, capture a short test stream using `navigator.mediaDevices.getUserMedia({ audio: { deviceId: { exact: id } } })`.
   - Connect WebAudio `AudioContext` and `AnalyserNode` to compute real-time RMS audio levels (0–100%) rendered on a responsive VU bar meter.
   - Provide an optional 3-second loopback monitor button so players hear how they sound through headphones.
   - Emits `@audio-check-completed` event with `{ deviceId: string, deviceLabel: string, verified: boolean }`.
2. **Lobby Participant State Integration (`services/game_session/ui/src/lobby/runefoble-session-lobby.ts`)**:
   - Embed `<runefoble-audio-preflight>` into the participant staging column.
   - Render an audio status icon (`🎙️ Mic Verified` / `⚠️ Mic Untested`) next to each participant's readiness badge.
   - Persist selected `preferred_mic_id` in localStorage so subsequent sessions auto-calibrate.
3. **Storybook Stories (`services/game_session/ui/src/lobby/runefoble-audio-preflight.stories.ts`)**:
   - Provide mocked device list and animated audio level stories (idle, active speech, clipping, permission denied).

## Definition of Done
1. `<runefoble-audio-preflight>` enumerates available audio input devices in browser environments.
2. WebAudio VU meter displays real-time input amplitude when speaking into selected microphone.
3. Completing audio check marks the player's audio as verified in the lobby UI.
4. Clean teardown: media streams and AudioContext instances are closed when unmounting to avoid browser mic indicator retention.
5. All source files conform to Hard Invariant 6 (< 500 lines per file).
