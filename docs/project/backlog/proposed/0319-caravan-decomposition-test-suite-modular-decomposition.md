---
id: '0319'
title: Caravan Modular Decomposition Test Suite Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0129
- TASK-0186
governing_adrs:
- ADR-0002
- ADR-0008
- ADR-0013
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0319: Caravan Modular Decomposition Test Suite Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_caravan_modular_decomposition.py` (287 lines, 57.4% of limit) into modular test sub-suites under `tests/test_caravan_modular/` (`test_contracts.py`, `test_transit_ambush.py`, `test_escrow_stock.py`), keeping each test module strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`tests/test_caravan_modular_decomposition.py` verifies caravan trade contract lifecycle, cargo escrow mechanics, transit ambush risk calculations, and economic price modifiers. As cross-campaign trade routes and settlement caravans expand, this test file will approach the 500-line limit unless decomposed into focused, single-responsibility test submodules.

## Governing Architecture & ADRs
- **ADR-0002: Domain Events via eventsource-py**: Event handling and aggregate mutations.
- **ADR-0008: Property-Based and Blackbox Testing**: Frontdoor assertions and domain rule verification.
- **ADR-0013: Modular Decomposition**: All test modules kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Contract Aggregate Suite (`tests/test_caravan_modular/test_contracts.py`)**:
   - Contract creation, state machine validation, dispatch, acceptance, and fulfillment (< 95 lines).
2. **Transit & Ambush Mechanics Suite (`tests/test_caravan_modular/test_transit_ambush.py`)**:
   - Route hazard calculations, ambush checks, party defense modifiers, and payout validation (< 95 lines).
3. **Escrow & Outpost Stock Suite (`tests/test_caravan_modular/test_escrow_stock.py`)**:
   - Outpost inventory updates, refined stock generation, and dynamic economic price adjustments (< 95 lines).
4. **Verification**:
   - Run `uv run pytest tests/test_caravan_modular/` to ensure 100% test pass rate.

## Definition of Done
- `tests/test_caravan_modular_decomposition.py` decomposed into `tests/test_caravan_modular/` package.
- All extracted test modules strictly < 110 lines each per Hard Invariant 6.
- 100% test pass rate preserved across all caravan domain assertions.
