---
id: '0437'
title: App Shell Soundscape Real-Time WebSocket Audio Synchronization & Foley Playback
status: Refined
created: 2026-09-28
dependencies:
- TASK-0109
- TASK-0358
- TASK-0436
governing_adrs:
- ADR-0004
- ADR-0006
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0010
- PRD-0023
governing_stories:
- US-0039
- US-0053
- US-0065
target_release: 0.9.0
---

# TASK-0437: App Shell Soundscape Real-Time WebSocket Audio Synchronization & Foley Playback

## Status
Refined

## Summary
Update the App Shell WebSocket handler (`frontend/src/runefoble-app.ts`) to receive and process real-time soundscape events (`soundscape_cue`, `tension_updated`, `soundscape_track_changed`, `soundscape_ducking`) over `/ws/session/{session_id}`, dispatching reactive DOM events to `<runefoble-soundscape-controls>` and triggering synchronized client-side WebAudio foley playback within 100ms per PRD-0010 and US-0053.

## Problem Statement
While the `<runefoble-soundscape-controls>` Lit component provides stem volume sliders, a tactile foley soundboard, and tension state indicators, the App Shell's session WebSocket message dispatcher drops all soundscape messages. When a player triggers an action that emits a sound cue or when the DM adjusts encounter tension, other players connected to the live session do not receive real-time audio playback or UI state synchronization.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/manage-dynamic-soundscapes-and-audio-ducking.md`: Encounter tension, stem profiles, and foley soundboard playback.
  - `docs/reference/redis-streams-event-bus.md`: Soundscape event channel conventions and WebSocket broadcast envelopes.
  - `docs/explanation/realtime-voice-and-board-sync.md`: Sub-500ms pipeline architecture and optimistic client synchronization.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Loose coupling between App Shell and microfrontends via DOM CustomEvents.
  - **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Real-time broadcast fanout of soundscape domain events to connected WebSocket clients.
  - **ADR-0010: Real-Time Audio Pipeline and Ducking Coordination**: Automatic -12dB WebAudio ducking on player speech or soundboard announcements.
  - **ADR-0013: Frontend Microfrontend Architecture**: Microfrontends communicate through standard events without tight coupling.

## Product & User Story References
- [`prd-0010-adaptive-soundscape-foley-and-tension-scoring.md`](../../product/accepted/prd-0010-adaptive-soundscape-foley-and-tension-scoring.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0039-encounter-tension-adaptive-scoring-and-foley.md`](../../user_stories/accepted/us-0039-encounter-tension-adaptive-scoring-and-foley.md)
- [`us-0053-dm-manual-soundboard-and-foley-triggers.md`](../../user_stories/accepted/us-0053-dm-manual-soundboard-and-foley-triggers.md)
- [`us-0065-game-session-staging-lobby-and-pre-game-assembly.md`](../../user_stories/accepted/us-0065-game-session-staging-lobby-and-pre-game-assembly.md)

## Detailed Specification & Implementation Plan
1. **App Shell WebSocket Message Handlers (`frontend/src/runefoble-app.ts`)**:
   - Add cases in `socket.onmessage` for:
     - `soundscape_cue`: Dispatches custom event `@soundscape-cue-received` or invokes synthesized WebAudio acoustic feedback.
     - `tension_updated`: Updates local session tension indicators and dispatches `@soundscape-tension-changed`.
     - `soundscape_track_changed`: Updates active stem profiles across party clients.
     - `soundscape_ducking`: Triggers -12dB ducking crossfade on background music stems.
2. **Microfrontend Event Binding (`<runefoble-soundscape-controls>`)**:
   - Ensure `<runefoble-soundscape-controls>` reacts to external tension score updates and cue triggers when mounted in `hud-widget` plugin slot.
3. **Blackbox Frontend Tests (`frontend/test/soundscape-websocket-sync.test.ts`)**:
   - Verify incoming WebSocket soundscape messages update component state and trigger custom events without errors.

## INVEST Criteria Evaluation
- **Independent (I)**: Consumes standard WebSocket envelopes independently of soundscape service internal audio generators.
- **Negotiable (N)**: Cue volume curves and ducking attack/release timings can be calibrated.
- **Valuable (V)**: Delivers synchronized immersive audio to all players on game night.
- **Estimable (E)**: Follows existing App Shell WebSocket message routing patterns.
- **Small (S)**: Scope strictly isolated to WebSocket message handling (< 80 lines) and one blackbox test file.
- **Testable (T)**: Mocked WebSocket frontdoor frames asserting DOM custom events and component state updates.

## Definition of Done
1. `runefoble-app.ts` parses `soundscape_cue`, `tension_updated`, and `soundscape_ducking` messages from session WebSocket.
2. Connected players receive synchronized soundboard cues and stem profile transitions in real time.
3. Frontdoor blackbox test suite `frontend/test/soundscape-websocket-sync.test.ts` passes with 100% assertions.
4. Code passes `npm run lint` and TypeScript compilation (`npm run check`).
