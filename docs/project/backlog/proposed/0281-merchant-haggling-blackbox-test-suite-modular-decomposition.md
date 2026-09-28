---
id: '0281'
title: Merchant Haggling Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0262
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0024
governing_stories:
- US-0075
target_release: 0.8.0
---

# TASK-0281: Merchant Haggling Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_merchant_haggling.py` (359 lines, 71.8% of limit) into modular test submodules under `tests/test_blackbox_merchant_haggling/` (`conftest.py`, `test_bargain_flow.py`, `test_rhetoric_moves.py`, `test_dm_arbitration.py`), ensuring all test files remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_merchant_haggling.py` tests haggling session initialization, player rhetoric moves, merchant mood calculations, patience degradation, DM live price overrides, and deal acceptance in a single 359-line test module. As multi-currency exchange and complex trade bundle tests are added, this test file will breach the 500-line limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test package structuring.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Real-time event testing.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_merchant_haggling/conftest.py`)**:
   - Extract test client setup, mock merchant entities, item catalogs, and token auth fixtures (< 70 lines).
2. **Bargain Flow Tests (`tests/test_blackbox_merchant_haggling/test_bargain_flow.py`)**:
   - Extract session start, price range checks, counter-offer rounds, and walk-away tests (< 110 lines).
3. **Rhetoric & Temperament Tests (`tests/test_blackbox_merchant_haggling/test_rhetoric_moves.py`)**:
   - Extract flattery, intimidation, bundling, and patience threshold failure tests (< 110 lines).
4. **DM Arbitration Tests (`tests/test_blackbox_merchant_haggling/test_dm_arbitration.py`)**:
   - Extract DM price overrides, dialogue injections, deal vetoes, and approval events (< 110 lines).
5. **Verification**:
   - Remove root test file and run `uv run pytest tests/test_blackbox_merchant_haggling/`.

## Definition of Done
- `tests/test_blackbox_merchant_haggling/` submodules strictly < 130 lines each.
- Passes all tests via `uv run pytest tests/test_blackbox_merchant_haggling/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
