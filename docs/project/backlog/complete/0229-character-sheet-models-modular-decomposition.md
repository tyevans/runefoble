---
id: 0229
title: Character Sheet Models Modular Decomposition
status: Complete
created: 2026-09-27
dependencies:
- TASK-0009
- TASK-0018
governing_adrs:
- ADR-0003
- ADR-0007
governing_prds:
- PRD-0006
governing_stories:
- US-0015
- US-0051
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/310
---
# TASK-0229: Character Sheet Models Modular Decomposition

## Status
Refined

## Summary
Decompose `services/character_sheet/src/character_sheet/models.py` (372 lines, 74.4% of limit) into modular Python submodules under `services/character_sheet/src/character_sheet/models/` (`base.py`, `character.py`, `inventory.py`, `conditions.py`, `progression.py`), ensuring all domain model modules remain strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`services/character_sheet/src/character_sheet/models.py` defines Pydantic domain models for character attributes, health points, spell slots, inventory items, equipment slots, encumbrance limits, condition effects, and level progression in a single 372-line file. As new condition modifiers and equipment traits are introduced, this model definition will breach the 500-line limit unless decomposed.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/interact-with-character-sheet-and-inventory.md`: Inventory encumbrance, condition modifiers, and equipment slots.
  - `docs/reference/platform-services.md`: Domain model definitions and serialization patterns.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module boundaries within bounded contexts.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain entity segregation and focused schema definitions.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0006-character-sheet-and-inventory-grid.md`](../../product/accepted/prd-0006-character-sheet-and-inventory-grid.md)
  - [`us-0015-character-inventory-and-equipment-slots.md`](../../user_stories/accepted/us-0015-character-inventory-and-equipment-slots.md)
  - [`us-0051-character-sheet-inventory-and-conditions.md`](../../user_stories/accepted/us-0051-character-sheet-inventory-and-conditions.md)

## Detailed Specification & Implementation Plan
1. **Core Character Models (`services/character_sheet/src/character_sheet/models/character.py`)**:
   - Extract `CharacterCore`, `AttributeScores`, and base stats (< 100 lines).
2. **Inventory & Equipment Models (`services/character_sheet/src/character_sheet/models/inventory.py`)**:
   - Extract `InventoryItem`, `EquipmentSlot`, and `Encumbrance` (< 90 lines).
3. **Conditions & Progression Models (`services/character_sheet/src/character_sheet/models/conditions.py` & `progression.py`)**:
   - Extract condition modifiers and spell progression models (< 90 lines each).
4. **Aggregator Facade (`services/character_sheet/src/character_sheet/models.py`)**:
   - Re-export all models maintaining full backwards compatibility (< 30 lines).
5. **Verification**:
   - Run character sheet test suites to verify zero breaking changes.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal model decomposition without breaking public serialization formats or schema contracts.
- **Negotiable (N)**: Submodule naming can be adjusted to match domain terminology.
- **Valuable (V)**: Protects character models from breaching the 500-line invariant limit.
- **Estimable (E)**: Pure model extraction and re-export facade.
- **Small (S)**: Submodules are each under 100 lines.
- **Testable (T)**: Existing test suite verifies serialization and validation parity.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `services/character_sheet/src/character_sheet/models.py` re-export facade reduced to < 40 lines.
2. All extracted model submodules strictly < 120 lines per Hard Invariant 6.
3. Passes `uv run pytest services/character_sheet/` and character sheet blackbox suites.
4. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
