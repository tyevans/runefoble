---
id: '0175'
title: GameSession Aggregate and Reaction Handlers Modular Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0004
- TASK-0155
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0001
governing_stories:
- US-0001
- US-0023
target_release: 0.6.0
---

# TASK-0175: GameSession Aggregate and Reaction Handlers Modular Decomposition

## Status
Refined

## Summary
Decompose `services/game_session/src/game_session/aggregate.py` (453 lines, 90.6% of limit) into modular domain handler modules under `services/game_session/src/game_session/aggregate/` (`session_handlers.py`, `combat_handlers.py`, `reaction_handlers.py`, `aggregate.py`, `__init__.py`), keeping all modules < 160 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/aggregate.py` encapsulates game session lifecycle (lobby, start, player join/leave, hot-swap), turn and initiative ordering, combat encounters, and spoken reaction/ready-action combat interrupt event handlers in a single 453-line file. Approaching the 500-line hard invariant limit, it must be decomposed into focused submodules with clean separation of concerns.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean submodule layout in `services/game_session/`.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation between session lifecycle, combat turns, and reaction interrupts.
- **ADR-0011: eventsource-py Core Event Sourcing**: DeclarativeAggregate `@handles` methods partitioned across mixin/handler classes.

## Product & User Story References
- **Product Requirement**: [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- **User Story**: [`us-0001-player-joins-tabletop-session.md`](../../user_stories/accepted/us-0001-player-joins-tabletop-session.md)
- **User Story**: [`us-0023-spoken-reaction-interrupts-and-ready-actions.md`](../../user_stories/accepted/us-0023-spoken-reaction-interrupts-and-ready-actions.md)

## Detailed Specification & Implementation Plan
1. **Session Lifecycle Handlers (`services/game_session/src/game_session/aggregate/session_handlers.py`)**:
   - Extract session creation, starting, player joining, player departure, and character hot-swapping logic (< 120 lines).
2. **Combat & Initiative Handlers (`services/game_session/src/game_session/aggregate/combat_handlers.py`)**:
   - Extract combat encounter start, initiative rolling, initiative ordering, turn advancement, and combat ending logic (< 140 lines).
3. **Reaction & Ready-Action Handlers (`services/game_session/src/game_session/aggregate/reaction_handlers.py`)**:
   - Extract reaction pausing, reaction resolution, ready-action trigger registration, and ready-action execution (< 130 lines).
4. **Root Aggregate Class (`services/game_session/src/game_session/aggregate/aggregate.py`)**:
   - Inherit handler mixins and define `GameSessionAggregate(DeclarativeAggregate[GameSessionState])` (< 100 lines).
5. **Package Facade & Backward Compatibility (`services/game_session/src/game_session/aggregate.py` and `__init__.py`)**:
   - Re-export `GameSessionAggregate`, `GameSessionState`, and `ParticipantState` for existing imports (< 30 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Internal domain refactoring with zero public HTTP or event schema breaking changes.
- **Negotiable (N)**: Submodule handler grouping can be tuned.
- **Valuable (V)**: Eliminates file size invariant risk (reducing 453-line file to <150 lines per module).
- **Estimable (E)**: Standard eventsource-py aggregate mixin decomposition pattern.
- **Small (S)**: Bounded strictly to `services/game_session/src/game_session/aggregate/`.
- **Testable (T)**: Validated by 100% pass rate in existing blackbox session and reaction test suites.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Architecture**:
   - `services/game_session/src/game_session/aggregate/` created with focused submodules.
   - All Python files strictly < 160 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - `uv run pytest tests/test_blackbox_reactions/` and existing game session tests pass with zero regressions.
3. **Quality Gates**:
   - Passes `uv run ruff check .` and `uv run ruff format --check .`.
