---
id: '0438'
title: Soundscape Tactical Board Event Subscribers for Kinetic Foley Audio Cues
status: Refined
created: 2026-09-28
dependencies:
- TASK-0050
- TASK-0104
- TASK-0150
governing_adrs:
- ADR-0002
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0010
- PRD-0016
- PRD-0021
governing_stories:
- US-0039
- US-0048
- US-0061
target_release: 0.9.0
---

# TASK-0438: Soundscape Tactical Board Event Subscribers for Kinetic Foley Audio Cues

## Status
Refined

## Summary
Expand `services/soundscape/src/soundscape/event_handlers.py` to subscribe to tactical board events (`SpellCast`, `AreaEffectExploded`, `TokenHazardTriggered`, `PhysicsCollisionOccurred`), resolving matching sound effects and publishing `SoundscapeCueTriggered` domain events to provide synchronized tactical audio feedback within 100ms per PRD-0010 checkable outcomes.

## Problem Statement
Currently, `services/soundscape/src/soundscape/event_handlers.py` only subscribes to combat rounds (`CombatEncounterStarted`, `CombatRoundAdvanced`), speech activity (`PlayerSpokeEvent`), and critical hits / death saves (`CriticalHitScored`, `DeathSaveStarted`). When players or The Watcher cast kinetic spells, trigger explosive AoE spell blooms, trip environmental hazards (lava, spike pits), or collide physical dice/tokens, the soundscape service ignores these events, resulting in silent tactical actions.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/manage-dynamic-soundscapes-and-audio-ducking.md`: Tactical foley cues, stem ducking, and tension calculation.
  - `docs/reference/events-schema.md`: CloudEvents definitions for tactical board, spells, and 3D collisions.
  - `docs/explanation/realtime-voice-and-board-sync.md`: Event-driven pipeline and sub-500ms reactive boundaries.
- **Governing Architecture & ADRs**:
  - **ADR-0002: Realtime Voice Duplex & Sub-500ms Audio Pipeline**: Low-latency event-to-audio resolution.
  - **ADR-0006: Redis Streams Distributed Domain Event Streaming**: CloudEvents subscription over the unified platform event bus.
  - **ADR-0007: Domain-Driven Design Architecture**: Cross-context event handling connecting `board_state` to `soundscape`.

## Product & User Story References
- [`prd-0010-adaptive-soundscape-foley-and-tension-scoring.md`](../../product/accepted/prd-0010-adaptive-soundscape-foley-and-tension-scoring.md)
- [`us-0039-encounter-tension-adaptive-scoring-and-foley.md`](../../user_stories/accepted/us-0039-encounter-tension-adaptive-scoring-and-foley.md)
- [`us-0048-kinetic-spell-vfx-and-particle-bloom.md`](../../user_stories/accepted/us-0048-kinetic-spell-vfx-and-particle-bloom.md)
- [`us-0061-tabletop-3d-physics-and-dice-collisions.md`](../../user_stories/accepted/us-0061-tabletop-3d-physics-and-dice-collisions.md)

## Detailed Specification & Implementation Plan
1. **Extend Subscribed Events (`services/soundscape/src/soundscape/event_handlers.py`)**:
   - Add `SpellCast`, `AreaEffectExploded`, `TokenHazardTriggered`, and `PhysicsCollisionOccurred` to `SOUNDSCAPE_SUBSCRIBED_EVENTS`.
2. **Tactical Action Event Handlers**:
   - `_handle_spell_cast`: Map archetype (evocation, abjuration, necromancy) to spell sound presets (`cue-spell-fire`, `cue-spell-shield`, etc.) and record cue on `SoundscapeAggregate`.
   - `_handle_area_effect`: Trigger explosion / shatter foley cue with dynamic volume gain based on radius.
   - `_handle_hazard_trigger`: Trigger trap spring / environmental hazard sound cue.
   - `_handle_physics_collision`: Trigger kinetic impact sound cue scaled by impact velocity/energy.
3. **Blackbox Tests (`tests/test_blackbox_soundscape_tactical_events.py`)**:
   - Publish `SpellCast`, `AreaEffectExploded`, `TokenHazardTriggered`, and `PhysicsCollisionOccurred` to the platform event bus and assert that `SoundscapeCueTriggered` events are recorded and published with valid sound URLs and session IDs.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates strictly over Redis Streams domain events without direct imports from UI or physics engine.
- **Negotiable (N)**: Preset mappings between spell schools and audio files can be refined or extended.
- **Valuable (V)**: Brings life to tactical board combat with responsive audio foley.
- **Estimable (E)**: Implements straightforward handler functions matching existing pattern in `event_handlers.py`.
- **Small (S)**: Handler additions under 100 lines and a focused blackbox test file.
- **Testable (T)**: Frontdoor event publishing via Redis/InMemory event bus asserting published CloudEvents.

## Definition of Done
1. `SOUNDSCAPE_SUBSCRIBED_EVENTS` includes tactical kinetic board events.
2. Incoming board events record cue triggers on the aggregate and emit `SoundscapeCueTriggered`.
3. Frontdoor blackbox test suite `tests/test_blackbox_soundscape_tactical_events.py` passes with 100% assertions.
4. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
