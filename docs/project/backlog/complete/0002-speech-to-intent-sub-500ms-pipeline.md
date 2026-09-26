# TASK-0002: Speech-to-Intent Sub-500ms Pipeline

## Description
Implement the natural speech-to-intent interpretation engine inside `services/the_watcher` and connect it to `services/voice_agent` and `services/board_state`. Spoken sentences describing movement, attack, spellcasting, and skill checks are converted into domain actions and dispatched across Redis Streams.

## Governing Documents
- ADRs: ADR-0002, ADR-0006, ADR-0007
- PRDs: PRD-0001
- User Stories: US-0001, US-0007

## Definition of Done
1. The Watcher engine parses movement intents (cardinal directions, distance in feet/squares/hexes) with >90% precision.
2. Inferred actions produce `TokenMoved` / `BoardMoveEvent` and `WatcherNarrationGenerated` / `WatcherNarrationEvent`.
3. Invariant property test ensures movement deltas remain strictly within grid constraints.
4. Total latency budget from transcription input to event dispatch is under 200ms.

## Deliverables Completed
- [x] Enhanced `TheWatcherEngine` in `services/the_watcher/src/the_watcher/watcher_ai.py` supporting cardinal distance movement (feet, squares, hexes, steps), coordinate navigation ("move to 5, 8"), target token movement ("move to the goblin archer", "flank the skeleton"), attacks ("attack goblin with longsword"), spells ("cast fireball at 4, 6"), and skill checks ("stealth check").
- [x] Added `calculate_bounded_destination` ensuring movement deltas remain strictly clamped within tactical grid bounds.
- [x] Integrated `RedisStreamsEventBus` in `services/the_watcher/src/the_watcher/main.py` to publish `SpeechIntentParsed` and `WatcherNarrationGenerated` to `runefoble.events.watcher`, and `TokenMoved` to `runefoble.events.board`.
- [x] Added `/api/v1/voice/transcribe` endpoint in `services/voice_agent/src/voice_agent/main.py` which emits `PlayerSpokeEvent` to `runefoble.events.session` and forwards transcripts to `the_watcher`.
- [x] Added Hypothesis property-based tests in `tests/test_properties.py` verifying arbitrary feet-to-squares conversion (5ft->1, 10ft->2, 15ft->3) and grid boundary clamping invariants.
- [x] Added unit and integration tests in `tests/test_speech_to_intent.py` verifying cardinal movement, attacks, spells, skill checks, sub-200ms latency budgets, and Redis stream event emission.
- [x] Verified full test suite passes (51/51) and Ruff check/format are 100% clean.
