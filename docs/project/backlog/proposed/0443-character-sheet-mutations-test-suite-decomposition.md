---
id: '0443'
title: Character Sheet Mutations Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0356
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0006
- PRD-0023
governing_stories:
- US-0015
- US-0051
- US-0064
- US-0069
target_release: 0.9.0
---

# TASK-0443: Character Sheet Mutations Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_character_sheet_mutations.py` (313 lines, 62.6% of limit) into modular test submodules under `tests/test_blackbox_character_sheet_mutations/` (`conftest.py`, `test_health_and_stabilization.py`, `test_inventory_and_equipment.py`, `test_spells_and_conditions.py`, `test_auth_and_permissions.py`), ensuring all test submodules remain strictly < 120 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_blackbox_character_sheet_mutations.py` tests health adjustments with positive/negative clamping, 0-HP stand-in stabilization triggers, equipment slot assignments, inventory additions and removals, active condition applications/clearing, spell slot preparation and casting, and SpiceDB Zanzibar 403 authorization rejections across all subresource mutation endpoints in a single 313-line file. As weapon proficiencies, encumbrance limits, and resting mechanics add further tests, this file will rapidly approach the 500-line invariant limit unless modularized into focused test suites.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Tests Zanzibar authorization enforcement across subresources.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for character sub-domains (vitality, equipment, statuses, magic).
- **ADR-0010: Developer Experience & Tooling**: Rapid, modular pytest execution.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 120 lines).

## Product & User Story References
- [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0015-dynamic-equipment-slots-and-encumbrance.md`](../../user_stories/accepted/us-0015-dynamic-equipment-slots-and-encumbrance.md)
- [`us-0051-character-sheet-inventory-equipment-and-conditions.md`](../../user_stories/accepted/us-0051-character-sheet-inventory-equipment-and-conditions.md)
- [`us-0069-deep-linkable-client-routing-and-route-guards.md`](../../user_stories/accepted/us-0069-deep-linkable-client-routing-and-route-guards.md)

## Scope of Work
1. **Shared Fixtures & Helpers (`tests/test_blackbox_character_sheet_mutations/conftest.py`)**:
   - Extract `reset_stores()` fixture and `create_test_character()` helper (< 50 lines).
2. **Health & Stabilization Tests (`tests/test_blackbox_character_sheet_mutations/test_health_and_stabilization.py`)**:
   - Extract HP modification, clamping, and zero-HP stabilization trigger tests (< 90 lines).
3. **Inventory & Equipment Tests (`tests/test_blackbox_character_sheet_mutations/test_inventory_and_equipment.py`)**:
   - Extract item addition, removal, and slot equipment tests (< 90 lines).
4. **Spells & Conditions Tests (`tests/test_blackbox_character_sheet_mutations/test_spells_and_conditions.py`)**:
   - Extract condition toggle and spell slot preparation/casting tests (< 90 lines).
5. **Authorization & Permissions Tests (`tests/test_blackbox_character_sheet_mutations/test_auth_and_permissions.py`)**:
   - Extract SpiceDB Zanzibar 403 Forbidden checks across all mutation endpoints (< 90 lines).
6. **Aggregator Shim (`tests/test_blackbox_character_sheet_mutations.py`)**:
   - Provide backwards-compatible delegation or remove root file cleanly per ADR-0013.
7. **Verification**:
   - Run `uv run pytest tests/test_blackbox_character_sheet_mutations/` asserting 100% passing tests.

## Definition of Done
1. `tests/test_blackbox_character_sheet_mutations.py` decomposed into modular submodules strictly < 120 lines each.
2. All test scenarios pass with zero regressions via `uv run pytest tests/test_blackbox_character_sheet_mutations/`.
3. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
