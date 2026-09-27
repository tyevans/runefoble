---
id: '0153'
title: Campfire Crafting Engine Recipe Registry and Mishap Table Modular Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0100
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0014
governing_stories:
- US-0044
target_release: 0.5.0
---

# TASK-0153: Campfire Crafting Engine Recipe Registry and Mishap Table Modular Decomposition

## Status
Refined

## Summary
Decompose `services/character_sheet/src/character_sheet/crafting.py` (375 lines, 75.0% of limit) into modular domain submodules under `services/character_sheet/src/character_sheet/crafting/` (`recipes.py`, `mishaps.py`, `engine.py`, `__init__.py`), keeping all modules < 160 lines per Hard Invariant 6.

## Problem Statement
`services/character_sheet/src/character_sheet/crafting.py` encapsulates reagent combination recipes, volatile mishap roll calculation, resting campfire boons, and stronghold crafting workshop bonuses in a single 375-line file. As new alchemical concoctions and masterwork tiers are added, decomposing it into focused modules prevents invariant violations.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout within `services/character_sheet/`.
- **ADR-0007: Domain-Driven Design Architecture**: Clean separation between recipe models, mishap tables, and execution engine.
- **ADR-0011: eventsource-py Core Event Sourcing**: Clean state transition and event dispatch helpers.

## Product & User Story References
- **Product Requirement**: [`prd-0014-downtime-crafting-and-stronghold-engine.md`](../../product/accepted/prd-0014-downtime-crafting-and-stronghold-engine.md)
- **User Story**: [`us-0044-interactive-campfire-downtime-and-crafting.md`](../../user_stories/accepted/us-0044-interactive-campfire-downtime-and-crafting.md)

## Detailed Specification & Implementation Plan
1. **Recipe Registry (`services/character_sheet/src/character_sheet/crafting/recipes.py`)**:
   - Extract recipe definitions, ingredient schemas, and difficulty check calculation (< 120 lines).
2. **Volatile Mishap Tables (`services/character_sheet/src/character_sheet/crafting/mishaps.py`)**:
   - Extract d100 mishap tables, consequence resolvers, and explosion event generators (< 130 lines).
3. **Crafting Engine (`services/character_sheet/src/character_sheet/crafting/engine.py`)**:
   - Extract crafting attempt resolution, proficiency modifier application, and event output (< 130 lines).
4. **Package Export (`services/character_sheet/src/character_sheet/crafting/__init__.py`)**:
   - Re-export `CraftingEngine`, `Recipe`, and `MishapResolver` for backward compatibility (< 30 lines).
5. **Facade Compatibility**:
   - Preserve `crafting.py` re-export for existing imports (< 20 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Internal domain refactoring with zero change to public HTTP API or event contracts.
- **Negotiable (N)**: Submodule organization can be tuned.
- **Valuable (V)**: Protects against file size violations and improves unit testability of alchemical rules.
- **Estimable (E)**: Standard Python package modularization.
- **Small (S)**: Bounded strictly to `services/character_sheet/src/character_sheet/crafting/`; all files < 160 lines.
- **Testable (T)**: Validated by 100% pass rate in existing downtime and crafting blackbox test suites.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Architecture**:
   - `services/character_sheet/src/character_sheet/crafting/` created with focused submodules.
   - All Python files strictly < 180 lines.
2. **Frontdoor Test Verification**:
   - `uv run pytest tests/test_blackbox_crafting/` passes with zero regressions.
3. **Quality Gates**:
   - Passes `uv run ruff check .` and `uv run ruff format --check .`.
