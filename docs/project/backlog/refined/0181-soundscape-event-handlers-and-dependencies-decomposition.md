---
id: '0181'
title: Soundscape Event Handlers and Dependencies Modular Decomposition
status: Refined
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
Refined

## Summary
Decompose `services/soundscape/src/soundscape/dependencies.py` (367 lines, 73.4% of limit) by extracting Redis Streams domain event subscription handlers and listener setup into `services/soundscape/src/soundscape/event_handlers.py`, keeping all dependency and event handler modules strictly < 180 lines per Hard Invariant 6 and ADR-0007.

## Problem Statement
`services/soundscape/src/soundscape/dependencies.py` manages singleton dependency injection for repositories, SpiceDB authorization checks, and session mixer registries, while also containing multiple Redis Streams event handler callbacks (`CharacterHealthChanged`, `DiceRolled`, `CombatEncounterStarted`, etc.). As new audio cues and leitmotif triggers are added, the file approaches the 400+ line threshold.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module boundaries within bounded contexts.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Event streaming and asynchronous event listener coordination.
- **ADR-0007: Domain-Driven Design Architecture**: Clean separation between application dependencies and event listeners.

## Detailed Specification & Implementation Plan
1. **Event Handlers Module (`services/soundscape/src/soundscape/event_handlers.py`)**:
   - Extract domain event callback functions and dynamic tension recalculation triggers (< 180 lines).
   - Wire event payloads to soundscape aggregate methods and audio mixer stem transitions.
2. **Dependencies Refactoring (`services/soundscape/src/soundscape/dependencies.py`)**:
   - Retain repository factories, SpiceDB permission guards, and session state caches (< 150 lines).
   - Import and wire `event_handlers.py` during service bootstrap.
3. **Verification**:
   - Verify all soundscape unit tests and blackbox tests pass.
   - Run `uv run pytest tests/test_blackbox_soundscape_ui.py` and `services/soundscape/`.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactoring bounded strictly to the `soundscape` service internal dependencies and event listener modules.
- **Negotiable (N)**: Listener registration patterns can be adjusted between explicit wire functions or class-based subscriber registries.
- **Valuable (V)**: Protects against Hard Invariant 6 (500 lines) and clearly separates DI dependencies from Redis Streams event consumption.
- **Estimable (E)**: Straightforward separation of event callbacks from FastAPI dependency injection providers.
- **Small (S)**: Bounded strictly to `services/soundscape/src/soundscape/`; all modules < 180 lines.
- **Testable (T)**: Frontdoor verification via existing soundscape blackbox test suites.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `services/soundscape/src/soundscape/dependencies.py` reduced to strictly < 180 lines.
   - `services/soundscape/src/soundscape/event_handlers.py` created and strictly < 180 lines.
2. **Frontdoor Test Verification**:
   - All soundscape tests pass with `uv run pytest services/soundscape/`.
   - Passes `uv run pytest tests/test_blackbox_soundscape_ui.py`.
3. **Quality Gates**:
   - Code passes `uv run ruff check .` and `uv run ruff format --check .`.
