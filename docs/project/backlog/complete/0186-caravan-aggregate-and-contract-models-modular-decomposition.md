---
id: 0186
title: Caravan Aggregate and Contract Models Modular Decomposition
status: Complete
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
pr_url: https://github.com/tyevans/runefoble/pull/246
---
# TASK-0186: Caravan Aggregate and Contract Models Modular Decomposition

## Status
Refined

## Summary
Decompose `services/game_session/src/game_session/caravan.py` (351 lines, 70.2% of limit) and `caravan_ledger.py` (342 lines) into modular submodules under `services/game_session/src/game_session/caravan/`, extracting `CaravanContractState` Pydantic models, transit stage calculations, and escrow ledger validation into separate files (< 150 lines each) per Hard Invariant 6 and ADR-0007.

## Problem Statement
`services/game_session/src/game_session/caravan.py` (351 lines) and `caravan_ledger.py` (342 lines) combine aggregate state transitions, event handling logic, escrow state tracking, and transit stage validation. As Milestone 9 introduces frontier mercenary bounty routers (TASK-0165) and settlement registries (TASK-0164), adding contract types and reward escalations will push both files over 400 lines and breach the 500-line invariant unless decomposed.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `services/game_session/`.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for caravan manifests, contracts, and settlement trades.
- **ADR-0011: PostgreSQL Event Store via eventsource-py**: Clean aggregate lifecycle management with `@handles` methods.

## Detailed Specification & Implementation Plan
1. **Caravan Models Submodule (`services/game_session/src/game_session/caravan/models.py`)**:
   - Extract `CaravanContractState`, risk level enums, reward schemas, and manifest models (< 100 lines).
2. **Caravan Aggregate Logic (`services/game_session/src/game_session/caravan/aggregate.py`)**:
   - Focus strictly on `CaravanContractAggregate` DeclarativeAggregate lifecycle and event handling (< 140 lines).
3. **Caravan Escrow & Ledger Submodule (`services/game_session/src/game_session/caravan/ledger.py`)**:
   - Decompose `caravan_ledger.py` into focused ledger accounting, payout validation, and escrow resolution (< 140 lines).
4. **Backward-Compatible Facade (`services/game_session/src/game_session/caravan.py`)**:
   - Re-export aggregate, models, and ledger routines (< 50 lines).
5. **Verification**:
   - Run `uv run pytest tests/test_blackbox_caravan_board_ui.py` to confirm zero regression.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactoring contained within `services/game_session/src/game_session/caravan/`.
- **Negotiable (N)**: Submodule division (models, aggregate, ledger) cleanly separates state representations from business mutators.
- **Valuable (V)**: Safeguards against Hard Invariant 6 (500 lines) and organizes caravan business logic.
- **Estimable (E)**: Pure refactoring with explicit domain event `@handles` preserved.
- **Small (S)**: Bounded strictly to `services/game_session/src/game_session/caravan/`; all files < 150 lines.
- **Testable (T)**: Frontdoor verification through pytest test suite execution against public endpoints and domain events.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `caravan.py` reduced to strictly < 60 lines.
   - All extracted submodules under `caravan/` strictly < 150 lines each.
2. **Frontdoor Test Verification**:
   - All tests pass via `uv run pytest tests/test_blackbox_caravan_board_ui.py`.
3. **Quality Gates**:
   - Code passes `uv run ruff check .` and `uv run ruff format --check .`.
