---
id: '0293'
title: Settlement Haggling Router Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0262
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0006
- ADR-0013
governing_prds:
- PRD-0024
governing_stories:
- US-0075
target_release: 0.8.0
---

# TASK-0293: Settlement Haggling Router Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/src/game_session/settlement/haggling_router.py` (295 lines, 59.0% of limit) into modular sub-routers and handler submodules under `services/game_session/src/game_session/settlement/haggling_router/` (`sessions.py`, `gambits.py`, `dm_arbitration.py`), ensuring all modules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/settlement/haggling_router.py` coordinates negotiation session initiation, gambit execution, posture evaluation, DM veto overrides, and event publishing to multiple Redis streams (`tavern` and `west_marches`). As settlement establishments and NPC merchant interactions grow with automated bartering and loyalty tiers, this monolithic router will approach the 500-line invariant limit unless decomposed into focused, single-responsibility submodules.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Enforces fine-grained `participate`, `read`, and `arbitrate` permissions on negotiation sessions.
- **ADR-0002: Domain Events via eventsource-py**: Aggregates and events for settlement haggling transactions.
- **ADR-0006: Redis Streams Event Bus**: Dual-stream publishing for tavern and West Marches listeners.
- **ADR-0013: Modular Decomposition**: Keep all source files strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Negotiation Session Endpoints (`services/game_session/src/game_session/settlement/haggling_router/sessions.py`)**:
   - Extract `POST /settlements/establishments/{id}/negotiations` and `GET /settlements/negotiations/{id}` handlers (< 100 lines).
2. **Gambits & Bargaining Endpoints (`services/game_session/src/game_session/settlement/haggling_router/gambits.py`)**:
   - Extract `POST /settlements/negotiations/{id}/gambits` handler and posture state transitions (< 100 lines).
3. **DM Arbitration Endpoints (`services/game_session/src/game_session/settlement/haggling_router/dm_arbitration.py`)**:
   - Extract `POST /settlements/negotiations/{id}/dm-override` handler and event publishing helpers (< 100 lines).
4. **Router Aggregation (`services/game_session/src/game_session/settlement/haggling_router/__init__.py`)**:
   - Re-export unified APIRouter preserving all existing endpoint paths and tags (< 40 lines).
5. **Verification**:
   - Verify blackbox tests pass via `uv run pytest tests/test_blackbox_merchant_haggling.py`.

## Definition of Done
- `haggling_router.py` decomposed into `haggling_router/` package.
- All extracted submodules strictly < 110 lines per Hard Invariant 6.
- 100% test passing in blackbox merchant haggling test suite.
- Re-exported router maintains backward compatibility with zero route changes.
