---
id: '0113'
title: Character Sheet Aggregate Mutation Handlers and Event Appliers Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0009
- TASK-0018
- TASK-0055
- TASK-0060
governing_adrs:
- ADR-0003
- ADR-0011
target_release: 0.3.0
governing_prds:
- PRD-0006
governing_stories:
- US-0015
- US-0025
- US-0051
pr_url: https://github.com/tyevans/runefoble/pull/126
---
# TASK-0113: Character Sheet Aggregate Mutation Handlers and Event Appliers Decomposition

## Status
Refined

## Summary
Decompose `services/character_sheet/src/character_sheet/aggregate.py` (342 lines, 68.4% of limit) into modular command mutation handlers and `@handles` event state applier sub-modules to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as downtime crafting (TASK-0100) and inventory encumbrance features expand.

## Problem Statement
`services/character_sheet/src/character_sheet/aggregate.py` currently defines the `CharacterAggregate` class spanning 342 lines that directly encapsulates all domain commands and `@handles` event reducers for:
1. Core character vitals: HP modification, death saves, unconscious states, and level-ups.
2. Condition and status mechanics: Blinded, poisoned, stunned, and custom status application/removal.
3. Inventory & equipment: Adding/removing items, slot equipping/unequipping, and weight tracking.
4. Spellbook & spell slots: Spell preparation and slot expenditure/recovery.
5. Stand-in tactical policy configuration and absence penalties.

As Milestone 5 introduces downtime alchemical crafting, bag-of-holding mechanics, and complex item attunement, this file will exceed the 500-line ceiling unless partitioned into domain-focused sub-handlers.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout within `services/character_sheet/`.
- **ADR-0011: eventsource-py Core Event Sourcing**: Event-sourced aggregate state management and `@handles` pattern.

## Product & User Story References
- **Product Requirement**: [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md)
- **User Stories**:
  - [`us-0015-character-inventory-equipment-tracking.md`](../../user_stories/accepted/us-0015-character-inventory-equipment-tracking.md)
  - [`us-0025-personalized-ai-stand-in-tactical-policies.md`](../../user_stories/accepted/us-0025-personalized-ai-stand-in-tactical-policies.md)
  - [`us-0051-character-level-progression-and-spellbook.md`](../../user_stories/accepted/us-0051-character-level-progression-and-spellbook.md)

## Detailed Specification & Implementation Plan
1. **Inventory & Equipment Handlers (`services/character_sheet/src/character_sheet/handlers/inventory.py`)**:
   - Equipment slot mutations and item inventory reducers (< 120 lines).
2. **Spellbook & Progression Handlers (`services/character_sheet/src/character_sheet/handlers/spells.py`)**:
   - Level progression, hit die rolling, spell preparation, and slot tracking reducers (< 120 lines).
3. **Vitals & Policy Handlers (`services/character_sheet/src/character_sheet/handlers/vitals.py`)**:
   - HP damage/healing, condition states, absence penalties, and stand-in guardrails (< 140 lines).
4. **Aggregate Coordinator (`services/character_sheet/src/character_sheet/aggregate.py`)**:
   - Declarative aggregate class composing domain mutation methods and delegating event application (< 120 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal aggregate structure without altering domain event schemas or public repository APIs.
- **Negotiable (N)**: Split boundaries between inventory and vitals handlers can be tailored.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and adheres to ADR-0011 declarative aggregate conventions.
- **Estimable (E)**: Standard domain-driven sub-handler extraction in eventsource-py.
- **Small (S)**: Scope strictly isolated to `services/character_sheet/src/character_sheet/aggregate.py`; all resulting files < 150 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_character_sheet.py tests/test_blackbox_character_inventory.py tests/test_blackbox_campfire_crafting.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Decomposition Executed**:
   - `services/character_sheet/src/character_sheet/aggregate.py` decomposed into `aggregate.py` and dedicated sub-handlers in `services/character_sheet/src/character_sheet/handlers/`.
2. **Strict Line Limit**:
   - All modules in `services/character_sheet/` strictly under 200 lines in compliance with Hard Invariant 6.
3. **Full Backward Compatibility**:
   - 100% backward compatibility for all aggregate methods and event handlers on `CharacterAggregate`.
4. **Frontdoor Test Verification**:
   - All tests pass via `uv run pytest tests/test_character_sheet.py tests/test_blackbox_character_inventory.py`.
