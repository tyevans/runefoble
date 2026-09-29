---
id: '0350'
title: Rules Compendium Aggregate Handlers Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0048
- TASK-0108
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0009
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0008
governing_stories:
- US-0037
- US-0052
target_release: 0.8.0
---

# TASK-0350: Rules Compendium Aggregate Handlers Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/rules_compendium/src/rules_compendium/aggregate.py` (271 lines, 54.2% of limit) into modular submodules under `services/rules_compendium/src/rules_compendium/aggregate/` (`compendium.py`, `encounter.py`), with an aggregator export at `services/rules_compendium/src/rules_compendium/aggregate.py`, ensuring all submodules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`services/rules_compendium/src/rules_compendium/aggregate.py` couples two independent event-sourced aggregates in a single source file: `CompendiumAggregate` (managing canonical SRD indexing, monster stat blocks, spell descriptions, condition markers, and homebrew rule registration) and `EncounterAggregate` (managing XP budgeting, party level scaling, difficulty tier balancing, and combatant list mutations). As legendary actions, lair hazards, and multi-wave encounter balancing are implemented, this aggregate module will approach the 500-line invariant limit unless decoupled.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout and isolated test execution.
- **ADR-0007: Domain-Driven Design Architecture**: Event-sourced aggregates via `eventsource-py`.
- **ADR-0009: Code Quality and Linting with Ruff and Pre-commit**: Code formatting and linting standards.
- **ADR-0010: Continuous Integration Pipeline**: Rapid and modular test suite execution.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Compendium Aggregate (`services/rules_compendium/src/rules_compendium/aggregate/compendium.py`)**:
   - Extract `CompendiumState`, `CompendiumAggregate`, and mutation appliers for `MonsterIndexed`, `SpellIndexed`, `ConditionIndexed`, and `HomebrewRuleRegistered` (< 110 lines).
2. **Encounter Aggregate (`services/rules_compendium/src/rules_compendium/aggregate/encounter.py`)**:
   - Extract `EncounterState`, `EncounterAggregate`, and mutation appliers for `EncounterBalanced` (< 100 lines).
3. **Backwards-Compatible Entry Point (`services/rules_compendium/src/rules_compendium/aggregate.py`)**:
   - Re-export `CompendiumState`, `CompendiumAggregate`, `EncounterState`, and `EncounterAggregate` (< 30 lines).
4. **Verification**:
   - Verify `uv run pytest tests/test_blackbox_rules_compendium.py` passes with 100% success.

## Definition of Done
- `services/rules_compendium/src/rules_compendium/aggregate/` submodules strictly < 110 lines each per Hard Invariant 6.
- Root `aggregate.py` reduced to a backwards-compatible re-export module (< 40 lines).
- 100% pass rate on `uv run pytest tests/test_blackbox_rules_compendium.py`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
