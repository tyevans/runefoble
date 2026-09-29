---
id: '0230'
title: Soundscape Aggregate Handlers Modular Decomposition
status: Complete
created: 2026-09-27
dependencies:
- TASK-0050
- TASK-0109
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0011
- ADR-0013
governing_prds:
- PRD-0010
governing_stories:
- US-0039
- US-0053
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/386
---
# TASK-0230: Soundscape Aggregate Handlers Modular Decomposition

## Status
Refined

## Summary
Decompose `services/soundscape/src/soundscape/aggregate.py` (319 lines, 63.8% of limit) by extracting tension scoring handlers, foley cue handlers, and stem crossfade logic into dedicated domain handler submodules under `services/soundscape/src/soundscape/handlers/` (`stems.py`, `foley.py`, `tension.py`), ensuring all handler modules remain strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`services/soundscape/src/soundscape/aggregate.py` manages event-sourced state transitions for audio stems, tactical foley sound effects, ambient tension recalculation, and WebAudio ducking parameters. At 319 lines, it combines multiple distinct soundscape domain concerns into a single aggregate file that will exceed the 500-line limit as new boss encounter audio phases and dynamic weather acoustics are added.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/manage-dynamic-soundscapes-and-audio-ducking.md`: Encounter tension, crossfade stems, tactical foley, and -12dB WebAudio ducking.
  - `docs/how-to/define-event-sourced-aggregates.md`: Declarative aggregate methods and `@handles` registration.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module boundaries within bounded contexts.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation within aggregates.
  - **ADR-0011: PostgreSQL Event Store via eventsource-py**: Declarative aggregate state transition handlers.
  - **ADR-0013: Modular Decomposition**: Single-responsibility domain modules strictly < 150 lines.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0010-adaptive-soundscape-foley-and-tension-scoring.md`](../../product/accepted/prd-0010-adaptive-soundscape-foley-and-tension-scoring.md)
  - [`us-0039-encounter-tension-adaptive-scoring-and-foley.md`](../../user_stories/accepted/us-0039-encounter-tension-adaptive-scoring-and-foley.md)
  - [`us-0053-dm-manual-soundboard-and-foley-triggers.md`](../../user_stories/accepted/us-0053-dm-manual-soundboard-and-foley-triggers.md)

## Detailed Specification & Implementation Plan
1. **Stem Handlers (`services/soundscape/src/soundscape/handlers/stems.py`)**:
   - Extract audio stem playback, crossfade curves, and volume levels (< 120 lines).
2. **Foley Handlers (`services/soundscape/src/soundscape/handlers/foley.py`)**:
   - Extract tactical foley triggers, spatial acoustic positioning, and audio ducking (< 100 lines).
3. **Tension Handlers (`services/soundscape/src/soundscape/handlers/tension.py`)**:
   - Extract encounter tension calculations and dynamic musical mood scaling (< 100 lines).
4. **Aggregate Coordinator (`services/soundscape/src/soundscape/aggregate.py`)**:
   - Retain core `SoundscapeAggregate` definition delegating to handler modules (< 70 lines).
5. **Verification**:
   - Run soundscape test suites to confirm full event sourcing compatibility.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal aggregate decomposition without modifying CloudEvents schemas or public REST APIs.
- **Negotiable (N)**: Handler module boundaries can be tuned.
- **Valuable (V)**: Protects soundscape aggregate from breaching the 500-line invariant limit.
- **Estimable (E)**: Pure extraction of `@handles` methods and helper logic into handler submodules.
- **Small (S)**: Extracted modules will each be strictly < 150 lines.
- **Testable (T)**: Existing soundscape test suites verify state transition replay and event sourcing parity.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `services/soundscape/src/soundscape/aggregate.py` reduced to strictly < 80 lines.
2. Extracted handler submodules under `handlers/` strictly < 150 lines each.
3. Passes `uv run pytest services/soundscape/`.
4. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
