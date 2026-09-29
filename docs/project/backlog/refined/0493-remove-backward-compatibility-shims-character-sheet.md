---
id: '0493'
title: Remove Backward Compatibility Shims & Re-exports in character_sheet
status: Refined
created: 2026-09-29
dependencies:
- TASK-0229
- TASK-0277
- TASK-0356
governing_adrs:
- ADR-0003
- ADR-0011
- ADR-0013
governing_prds:
- PRD-0006
- PRD-0009
governing_stories:
- US-0006
- US-0018
- US-0036
target_release: 0.9.0
---

# TASK-0493: Remove Backward Compatibility Shims & Re-exports in character_sheet

## Status
Refined

## Summary
Purge backward-compatibility aggregator facades (`models.py`, `crafting.py`, `ui/src/runefoble-character-sheet.templates.ts`), field aliases (`alias="int"` in `models/base.py`), and facade re-export parity tests from `services/character_sheet`, standardizing on direct imports and canonical field definitions.

## Problem Statement
In `services/character_sheet`:
- `character_sheet/models.py` exists as a 10-line aggregator facade re-exporting models from `character_sheet.models.*` for backward compatibility.
- `character_sheet/crafting.py` exists as a 17-line facade re-exporting crafting module components.
- `character_sheet/models/base.py` retains legacy `alias="int"` and `model_dump(by_alias=True)`.
- `ui/src/runefoble-character-sheet.templates.ts` is an aggregator facade for character templates.
- Tests in `tests/test_character_sheet.py` verify backward compatibility of aggregate exports.
All of these artifacts preserve legacy paths for non-existent external consumers and violate DoR rule 9.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/interact-with-character-sheet-and-inventory.md`: Character stats, inventory, conditions.
  - `docs/how-to/run-campfire-rests-and-alchemical-crafting.md`: Alchemical crafting domain.
- **Governing Architecture & ADRs**:
  - **ADR-0011: eventsource-py Core Event Sourcing**: CharacterAggregate domain modeling.
  - **ADR-0013: Frontend Microfrontend Architecture**: Character sheet microfrontend vendoring.

## Product & User Story References
- [`prd-0006-character-sheet-and-inventory.md`](../../product/accepted/prd-0006-character-sheet-and-inventory.md)
- [`prd-0009-campfire-crafting-and-resting-boons.md`](../../product/accepted/prd-0009-campfire-crafting-and-resting-boons.md)
- [`us-0006-character-sheet-equipment-inventory.md`](../../user_stories/accepted/us-0006-character-sheet-equipment-inventory.md)
- [`us-0018-character-progression-and-spellbook.md`](../../user_stories/accepted/us-0018-character-progression-and-spellbook.md)

## Detailed Specification & Implementation Plan
1. **Delete Facade Modules**:
   - Delete `services/character_sheet/src/character_sheet/models.py`.
   - Delete `services/character_sheet/src/character_sheet/crafting.py`.
   - Delete `services/character_sheet/ui/src/runefoble-character-sheet.templates.ts`.
2. **Remove Model Field Aliases**:
   - In `services/character_sheet/src/character_sheet/models/base.py`, remove `alias="int"` on the `intelligence` field, standardizing on canonical `intelligence`.
   - Update serialization callers to eliminate `by_alias=True` reliance where not required.
3. **Migrate Import Sites**:
   - Update `character_sheet/main.py`, aggregate handlers, gateway routers, and tests to import directly from `character_sheet.models.*`, `character_sheet.crafting.*`, and modular UI template files.
4. **Update Blackbox Test Suites**:
   - In `tests/test_character_sheet.py`, remove `test_character_aggregate_exports_backward_compatibility()`.
   - Ensure all character sheet unit and blackbox tests pass against direct modular imports.

## INVEST Criteria Evaluation
- **Independent (I)**: Isolated to `services/character_sheet` and direct callers.
- **Negotiable (N)**: Clean standard Python and TypeScript import conventions.
- **Valuable (V)**: Removes 3 facade files and eliminates confusing model aliases.
- **Estimable (E)**: Clearly bounded to specific files and tests.
- **Small (S)**: File deletions and import updates adhering to the < 500 lines invariant.
- **Testable (T)**: Verified by `uv run pytest tests/test_character_sheet*` and UI test suites.

## Definition of Done
1. `models.py`, `crafting.py`, and `runefoble-character-sheet.templates.ts` deleted.
2. Field `alias="int"` removed from base models in favor of canonical `intelligence`.
3. All callers across backend and UI migrated to modular paths.
4. Obsolete backward-compatibility tests removed.
5. All character sheet tests pass cleanly.
