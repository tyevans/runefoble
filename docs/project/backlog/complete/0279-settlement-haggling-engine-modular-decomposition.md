---
id: 0279
title: Settlement Haggling Engine Modular Decomposition
status: Complete
created: 2026-09-28
dependencies:
- TASK-0262
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0024
governing_stories:
- US-0075
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/370
---
# TASK-0279: Settlement Haggling Engine Modular Decomposition

## Status
Refined

## Summary
Decompose `services/game_session/src/game_session/settlement/haggling.py` (356 lines, 71.2% of limit) into modular domain submodules under `services/game_session/src/game_session/settlement/haggling/` (`state.py`, `rhetoric.py`, `dm_controls.py`), ensuring all haggling modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/settlement/haggling.py` implements the interactive merchant negotiation state machine, rhetoric move resolution (flattery, intimidation, bundling, sob story), merchant patience and temperament adjustments, and live DM arbitration veto/accept controls in a single 356-line file. As new merchant personality quirks and multi-item trade bundle mechanics are added, this file will breach the 500-line invariant unless decomposed into dedicated submodules.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/run-tavern-minigames-and-merchant-haggling.md`: Dynamic haggling negotiation loops and DM oversight.
  - `docs/reference/tavern-and-merchants-events.md`: Event flows for merchant bartering and mood state.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout within bounded contexts.
  - **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Real-time event streaming for haggling states.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.
  - **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 130 lines).

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
  - [`us-0075-dynamic-merchant-haggling-with-dm-arbitration.md`](../../user_stories/accepted/us-0075-dynamic-merchant-haggling-with-dm-arbitration.md)

## Detailed Specification & Implementation Plan
1. **Haggling Session State Machine (`services/game_session/src/game_session/settlement/haggling/state.py`)**:
   - Extract session models, bargain states, price ranges, and patience counters (< 110 lines).
2. **Rhetoric Moves & Temperament Modifiers (`services/game_session/src/game_session/settlement/haggling/rhetoric.py`)**:
   - Extract player bartering moves, skill check formulas, merchant reaction formulas, and patience decay (< 120 lines).
3. **DM Arbitration & Veto Handlers (`services/game_session/src/game_session/settlement/haggling/dm_controls.py`)**:
   - Extract DM intervention endpoints, manual price overrides, dialogue injections, and deal approval/rejection (< 110 lines).
4. **Aggregator Facade (`services/game_session/src/game_session/settlement/haggling.py` / `__init__.py`)**:
   - Maintain re-export facade with full backwards compatibility (< 35 lines).
5. **Verification**:
   - Run haggling tests to confirm state machine and DM control integrity.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal engine decomposition preserving public APIs and event schemas.
- **Negotiable (N)**: Submodule logic boundaries can be tuned.
- **Valuable (V)**: Protects core negotiation engine from exceeding the 500-line invariant.
- **Estimable (E)**: Clear separation between state model, rhetoric resolution, and DM arbitration.
- **Small (S)**: Each extracted submodule strictly < 130 lines.
- **Testable (T)**: Full test coverage in `tests/test_blackbox_merchant_haggling.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `services/game_session/src/game_session/settlement/haggling.py` reduced to strictly < 40 lines.
2. Extracted submodules under `haggling/` strictly < 130 lines each per Hard Invariant 6.
3. 100% backwards compatibility preserved for all imports from `game_session.settlement.haggling`.
4. Passes all haggling blackbox tests via `uv run pytest tests/test_blackbox_merchant_haggling.py`.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
