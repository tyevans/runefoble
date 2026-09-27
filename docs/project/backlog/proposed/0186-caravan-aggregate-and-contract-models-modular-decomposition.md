---
id: '0186'
title: Caravan Aggregate and Contract Models Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0129
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0007
- PRD-0018
governing_stories:
- US-0058
target_release: 0.7.0
---

# TASK-0186: Caravan Aggregate and Contract Models Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/src/game_session/caravan.py` (351 lines, 70.2% of limit) and `caravan_ledger.py` (342 lines) into modular submodules under `services/game_session/src/game_session/caravan/`, extracting `CaravanContractState` Pydantic models, transit calculations, and escrow ledger validation into separate files (< 150 lines each) per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/caravan.py` (351 lines) and `caravan_ledger.py` (342 lines) combine state models, event handling logic, escrow state tracking, and transit stage validation. As Milestone 9 introduces frontier mercenary bounty routers (TASK-0165) and settlement registries (TASK-0164), adding contract types and reward escalations will quickly push both files over 400 lines and breach the 500-line invariant unless decomposed.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `services/game_session/`.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for caravan manifests, contracts, and settlement trades.
- **ADR-0011: PostgreSQL Multi-Database Persistent Event Store**: Clean aggregate lifecycle management.

## Scope of Work
1. **Caravan Models Submodule (`services/game_session/src/game_session/caravan_models.py` or subpackage)**:
   - Extract `CaravanContractState`, risk level enums, and manifest schemas (< 100 lines).
2. **Caravan Aggregate Logic**:
   - Focus `caravan.py` strictly on `CaravanContractAggregate` event handling and mutators (< 180 lines).
3. **Caravan Escrow & Ledger Submodule**:
   - Decompose `caravan_ledger.py` into focused ledger accounting and payout validation (< 150 lines).
4. **Backward Compatibility**:
   - Maintain clean re-exports in `services/game_session/src/game_session/caravan.py`.
5. **Verification**:
   - Verify existing caravan tests in `tests/test_blackbox_caravan_board_ui.py` and `services/game_session/` pass cleanly.

## Definition of Done
- `caravan.py` and `caravan_ledger.py` decomposed so no file exceeds 200 lines.
- All workspace tests pass via `uv run pytest`.
- Linting passes via `uv run ruff check .` and `uv run ruff format --check .`.
