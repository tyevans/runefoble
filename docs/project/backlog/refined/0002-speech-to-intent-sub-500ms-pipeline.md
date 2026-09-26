# TASK-0002: Speech-to-Intent Sub-500ms Pipeline

## Description
Implement the natural speech-to-intent interpretation engine inside `services/the_watcher` and connect it to `services/voice_agent` and `services/board_state`. Spoken sentences describing movement, attack, spellcasting, and skill checks are converted into domain actions and dispatched across Redis Streams.

## Governing Documents
- ADRs: ADR-0002, ADR-0006, ADR-0007
- PRDs: PRD-0001
- User Stories: US-0001, US-0007

## Definition of Done
1. The Watcher engine parses movement intents (cardinal directions, distance in feet/squares/hexes) with >90% precision.
2. Inferred actions produce `BoardMoveEvent` and `WatcherNarrationEvent`.
3. Invariant property test ensures movement deltas remain strictly within grid constraints.
4. Total latency budget from transcription input to event dispatch is under 200ms.
