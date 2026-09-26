---
id: '0113'
title: Character Sheet Aggregate Mutation Handlers and Event Appliers Decomposition
status: Proposed
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
- US-0016
- US-0025
---

# TASK-0113: Character Sheet Aggregate Mutation Handlers and Event Appliers Decomposition

## Status
Proposed

## Summary
Decompose `services/character_sheet/src/character_sheet/aggregate.py` (342 lines, 68.4% of limit) into modular command mutation handlers and `@handles` event state applier sub-modules to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as downtime crafting (TASK-0100) and inventory encumbrance features land.

## Problem Statement
`services/character_sheet/src/character_sheet/aggregate.py` currently defines the `CharacterAggregate` class spanning 342 lines that directly encapsulates all domain commands and `@handles` event reducers for:
1. Core character vitals: HP modification, death saves, unconscious states, and level-ups.
2. Condition and status mechanics: Blinded, poisoned, stunned, and custom status application/removal.
3. Inventory & equipment: Adding/removing items, slot equipping/unequipping, and weight tracking.
4. Spellbook & spell slots: Spell preparation and slot expenditure/recovery.
5. Stand-in tactical policy configuration and absence penalties.

As Milestone 5 introduces downtime alchemical crafting, bag-of-holding mechanics, and complex item attunement, this file will exceed the 500-line ceiling unless partitioned into domain-focused sub-handlers.

## Proposed Decomposition
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
- **Testable (T)**: Verified with `uv run pytest tests/test_character_sheet.py tests/test_blackbox_character_inventory.py`.

## Acceptance Criteria
1. `services/character_sheet/src/character_sheet/aggregate.py` decomposed into modular files under 150 lines each.
2. 100% test pass rate across all character sheet aggregate, level up, inventory, and policy test cases.
3. Fully compliant with eventsource-py declarative aggregate patterns.
4. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
