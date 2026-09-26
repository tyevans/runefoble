---
id: '0060'
title: Domain Aggregates and Rule Tables Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0018, TASK-0019, TASK-0022]
governing_adrs: [ADR-0003, ADR-0011]
target_release: 0.2.0
---

# TASK-0060: Domain Aggregates and Rule Tables Modular Decomposition

## Status
Proposed

## Summary
Decompose monolithic domain aggregate files across `game_session`, `board_state`, and `character_sheet` bounded contexts by extracting state models and static game rule tables into dedicated modules, keeping all domain aggregate files well clear of Hard Invariant 6 (< 500 lines per file).

## Problem Statement
Health scans identify the three primary event-sourced domain aggregate implementations rapidly approaching the 400-line warning threshold:
- `services/game_session/src/game_session/aggregate.py` (393 lines, 78.6% of limit)
- `services/board_state/src/board_state/aggregate.py` (388 lines, 77.6% of limit)
- `services/character_sheet/src/character_sheet/aggregate.py` (386 lines, 77.2% of limit)

Each file bundles three distinct responsibilities in a single module:
1. Pydantic state models and entity value objects (`ParticipantState`, `GameSessionState`, `TerrainCellState`, `TerrainDict`, `CharacterSheetState`, `InventoryItem`).
2. Static game balance rules and lookup tables (`SPELL_SLOTS_TABLE`, `CLASS_HIT_DIE`, `KNOWN_SPELL_LEVELS`, `DEFAULT_HAZARD_DAMAGE`).
3. The event-sourced `DeclarativeAggregate` classes with command mutators and `@handles` event projection methods.

As upcoming Milestone 2 and 3 features introduce multi-spell slot progression, advanced tactical terrain types, and turn timer constraints, these files will soon breach the 500-line limit.

## Proposed Decomposition
1. **Character Sheet Bounded Context (`services/character_sheet/src/character_sheet/`)**:
   - `rules.py`: Extract `SPELL_SLOTS_TABLE`, `CLASS_HIT_DIE`, and `KNOWN_SPELL_LEVELS` (< 80 lines).
   - `models.py`: Extract `CharacterSheetState`, equipment, condition, and inventory state schemas (< 120 lines).
   - `aggregate.py`: Retain `CharacterAggregate` with command methods and `@handles` event handlers (< 230 lines).
2. **Board State Bounded Context (`services/board_state/src/board_state/`)**:
   - `rules.py`: Extract `DEFAULT_HAZARD_DAMAGE` and hazard damage calculation functions (< 50 lines).
   - `models.py`: Extract `TerrainCellState`, `TerrainDict`, and spatial boundary models (< 80 lines).
   - `aggregate.py`: Retain `BoardAggregate` with movement validation, shroud calculations, and `@handles` handlers (< 250 lines).
3. **Game Session Bounded Context (`services/game_session/src/game_session/`)**:
   - `models.py`: Extract `ParticipantState` and `GameSessionState` models (< 70 lines).
   - `aggregate.py`: Retain `GameSessionAggregate` with combat round transitions, initiative ordering, and `@handles` handlers (< 260 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal bounded context code organization without changing domain events, event schemas, or public API routes.
- **Negotiable (N)**: Structure of `rules.py` vs `models.py` can be tuned per bounded context.
- **Valuable (V)**: Protects against file length limit violations (Hard Invariant 6) as combat and progression mechanics deepen.
- **Estimable (E)**: Standard Python model/rules extraction with zero changes to event-sourcing behavior.
- **Small (S)**: Scope cleanly bounded across the three service contexts; all resulting files < 260 lines.
- **Testable (T)**: Existing unit and blackbox aggregate test suites (`test_event_sourcing.py`, `test_character_aggregate.py`, `test_board_state.py`, `test_blackbox_board_terrain.py`, `test_blackbox_character_progression.py`, `test_blackbox_initiative_tracker.py`) verify identical domain state transitions.

## Acceptance Criteria
1. Re-exports in each bounded context ensure zero breaking changes to imports from `aggregate.py`.
2. All modified and new files strictly under 280 lines.
3. 100% test pass rate across all domain aggregate and blackbox test suites.
4. Conforms strictly to ADR-0011 and Hard Invariant 6 (< 500 lines per file).
