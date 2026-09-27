---
id: '0237'
title: Caravan Board UI Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0136
- TASK-0186
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0018
governing_stories:
- US-0058
target_release: 0.8.0
---

# TASK-0237: Caravan Board UI Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_caravan_board_ui.py` (318 lines, 63.6% of limit) into modular test sub-suites under `tests/test_blackbox_caravan_board_ui/` (`test_contract_board.py`, `test_escrow_dialogs.py`, `test_caravan_routes.py`), keeping all test modules strictly < 130 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_blackbox_caravan_board_ui.py` contains 318 lines testing contract board UI cards, escrow deposit modal interactions, caravan travel waypoint timelines, and trade route risk calculators in a single test module. Decomposing it into modular sub-suites ensures test clarity and prevents breaching the 500-line limit.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular test package structure.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for caravan contracts and trade routes.
- **ADR-0010: Real-Time WebSocket Board Synchronization**: Proper event handling verification.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Microfrontend component isolation and shadow DOM testing.

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_caravan_board_ui/conftest.py`)**:
   - Extract mock caravan contracts, player identity fixtures, and test server setup (< 60 lines).
2. **Contract Board Tests (`tests/test_blackbox_caravan_board_ui/test_contract_board.py`)**:
   - Test bounty contract listing cards, tier filters, reward values, and claim action buttons (< 100 lines).
3. **Escrow Dialogs Tests (`tests/test_blackbox_caravan_board_ui/test_escrow_dialogs.py`)**:
   - Test gold escrow lock modal, collateral inputs, validation errors, and confirmation events (< 100 lines).
4. **Caravan Routes Tests (`tests/test_blackbox_caravan_board_ui/test_caravan_routes.py`)**:
   - Test transit stage progress indicators, danger level badges, and route completion triggers (< 100 lines).
5. **Verification**:
   - Run `uv run pytest tests/test_blackbox_caravan_board_ui/` and ensure all tests pass cleanly.

## Definition of Done
- `tests/test_blackbox_caravan_board_ui.py` replaced by modular sub-suites under `tests/test_blackbox_caravan_board_ui/`.
- All test files strictly < 130 lines each.
- Passes `uv run pytest tests/test_blackbox_caravan_board_ui/`.
- Passes `uv run ruff check .` and `uv run ruff format --check .`.
