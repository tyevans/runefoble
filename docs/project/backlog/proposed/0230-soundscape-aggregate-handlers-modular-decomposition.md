---
id: '0230'
title: Soundscape Aggregate Handlers Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0050
- TASK-0109
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0010
governing_stories:
- US-0039
- US-0053
target_release: 0.8.0
---

# TASK-0230: Soundscape Aggregate Handlers Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/soundscape/src/soundscape/aggregate.py` (319 lines, 63.8% of limit) by extracting tension scoring handlers, foley cue handlers, and stem crossfade logic into dedicated domain handler submodules under `services/soundscape/src/soundscape/handlers/` (`stems.py`, `foley.py`, `tension.py`), ensuring all handler modules remain strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`services/soundscape/src/soundscape/aggregate.py` manages event-sourced state transitions for audio stems, tactical foley sound effects, ambient tension recalculation, and WebAudio ducking parameters. At 319 lines, it combines multiple distinct soundscape domain concerns into a single aggregate file that will exceed the 500-line limit as new boss encounter audio phases and dynamic weather acoustics are added.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module boundaries within bounded contexts.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation within aggregates.
- **ADR-0011: PostgreSQL Event Store via eventsource-py**: Declarative aggregate state transition handlers.

## Scope of Work
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

## Definition of Done
- `aggregate.py` reduced to strictly < 80 lines.
- Extracted handler submodules strictly < 150 lines each.
- Passes `uv run pytest services/soundscape/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
