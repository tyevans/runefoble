---
id: '0277'
title: Character Sheet Models Test Suite Modular Decomposition
status: Refined
created: 2026-09-28
dependencies:
- TASK-0229
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0006
governing_stories:
- US-0015
- US-0051
target_release: 0.8.0
---

# TASK-0277: Character Sheet Models Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_character_sheet_models_modular_decomposition.py` (395 lines, 79.0% of limit) into modular test submodules under `tests/test_character_sheet_models_modular_decomposition/` (`conftest.py`, `test_core_models.py`, `test_inventory_models.py`, `test_conditions_progression.py`, `test_routes_integration.py`), ensuring all test files remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`tests/test_character_sheet_models_modular_decomposition.py` currently verifies backward compatibility and schema parity for character sheet models (attribute scores, vitals, inventory items, equipment slots, conditions, spell slots, level progression) and FastAPI HTTP endpoints in a single monolithic test file of 395 lines. As the largest source file in the repository (79% of the 500-line invariant limit), any addition of character customization or multiclassing tests will immediately breach the invariant unless decomposed.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/interact-with-character-sheet-and-inventory.md`: Character inventory, condition effects, and level progression rules.
  - `docs/reference/platform-services.md`: Service boundary contracts and test suite organization.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular test package structuring under UV workspace.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain model segregation and focused test suites.
  - **ADR-0013: Modular Decomposition**: Test files decomposed into single-responsibility modules < 130 lines.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0006-character-sheet-and-inventory-grid.md`](../../product/accepted/prd-0006-character-sheet-and-inventory-grid.md)
  - [`us-0015-character-inventory-and-equipment-slots.md`](../../user_stories/accepted/us-0015-character-inventory-and-equipment-slots.md)
  - [`us-0051-character-sheet-inventory-and-conditions.md`](../../user_stories/accepted/us-0051-character-sheet-inventory-and-conditions.md)

## Detailed Specification & Implementation Plan
1. **Shared Fixtures & Test Client Setup (`tests/test_character_sheet_models_modular_decomposition/conftest.py`)**:
   - Extract test client setup, character state mock builders, and shared payload fixtures (< 60 lines).
2. **Core Attributes & Vitals Tests (`tests/test_character_sheet_models_modular_decomposition/test_core_models.py`)**:
   - Extract attribute score serialization, modifier calculation, health transitions, and guardrail tests (< 110 lines).
3. **Inventory & Equipment Tests (`tests/test_character_sheet_models_modular_decomposition/test_inventory_models.py`)**:
   - Extract equipment slot assignments, encumbrance threshold calculations, and item equip/unequip tests (< 110 lines).
4. **Conditions & Progression Tests (`tests/test_character_sheet_models_modular_decomposition/test_conditions_progression.py`)**:
   - Extract condition modifier application, exhaustion stacking, spell slot preparation, and level-up transition tests (< 110 lines).
5. **FastAPI Route Regression Tests (`tests/test_character_sheet_models_modular_decomposition/test_routes_integration.py`)**:
   - Extract HTTP endpoint tests for character creation, attribute querying, inventory mutations, and condition updates (< 110 lines).
6. **Verification**:
   - Remove root test module `tests/test_character_sheet_models_modular_decomposition.py` and run `uv run pytest tests/test_character_sheet_models_modular_decomposition/`.

## INVEST Criteria Evaluation
- **Independent (I)**: Test reorganization without altering public API contracts or model schemas.
- **Negotiable (N)**: Test grouping and module boundaries can be tuned.
- **Valuable (V)**: Eliminates the single largest file warning in the repository (395 lines) and protects against the 500-line invariant limit.
- **Estimable (E)**: Direct test extraction into focused pytest modules.
- **Small (S)**: Target files will each be strictly < 120 lines.
- **Testable (T)**: Pytest execution verifies 100% test passing and identical assertion coverage.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_character_sheet_models_modular_decomposition.py` decomposed into `tests/test_character_sheet_models_modular_decomposition/` package.
2. All extracted test submodules strictly < 130 lines per Hard Invariant 6.
3. 100% test passing via `uv run pytest tests/test_character_sheet_models_modular_decomposition/`.
4. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
