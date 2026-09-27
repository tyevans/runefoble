---
id: '0181'
title: Soundscape Event Handlers and Dependencies Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0050
- TASK-0095
- TASK-0102
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0010
governing_stories:
- US-0039
- US-0046
target_release: 0.7.0
---

# TASK-0181: Soundscape Event Handlers and Dependencies Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/soundscape/src/soundscape/dependencies.py` (368 lines, 73.6% of limit) by extracting Redis Streams domain event subscription handlers and listener setup into `soundscape/event_handlers.py`, keeping all dependency and event handler modules strictly < 200 lines per Hard Invariant 6.

## Problem Statement
`services/soundscape/src/soundscape/dependencies.py` manages singleton dependency injection for repositories, SpiceDB authorization checks, and session mixer registries, while also containing multiple Redis Streams event handler callbacks (`CharacterHealthChanged`, `DiceRolled`, `CombatEncounterStarted`, etc.). As new audio cues and leitmotif triggers are added, the file approaches the 400+ line threshold.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module boundaries within bounded contexts.
- **ADR-0006: Redis Streams Event Bus**: Event streaming and asynchronous event listener coordination.
- **ADR-0007: Domain-Driven Design Architecture**: Clean separation between application dependencies and event listeners.

## Scope of Work
1. **Event Handlers Module (`services/soundscape/src/soundscape/event_handlers.py`)**:
   - Extract domain event callback functions and dynamic tension recalculation triggers (< 180 lines).
2. **Dependencies Refactoring (`services/soundscape/src/soundscape/dependencies.py`)**:
   - Retain repository factories, SpiceDB permission guards, and session state caches (< 150 lines).
3. **Verification**:
   - Verify all soundscape unit tests and blackbox tests pass.

## Definition of Done
- `dependencies.py` reduced to < 180 lines.
- `soundscape/event_handlers.py` created and strictly < 180 lines.
- All soundscape tests pass with `uv run pytest services/soundscape/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
