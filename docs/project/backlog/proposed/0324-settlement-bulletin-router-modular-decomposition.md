---
id: '0324'
title: Settlement Bulletin Router Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0263
- TASK-0273
- TASK-0276
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0006
- ADR-0013
governing_prds:
- PRD-0024
governing_stories:
- US-0076
target_release: 0.8.0
---

# TASK-0324: Settlement Bulletin Router Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/src/game_session/settlement/bulletin_router.py` (281 lines, 56.2% of limit) into modular APIRouter submodules under `services/game_session/src/game_session/settlement/routers/` (`bulletin_notices_router.py`, `bulletin_ciphers_router.py`, and aggregate router), keeping each module strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/settlement/bulletin_router.py` houses endpoints for pinning bulletin notices, listing notices with state filters, archiving notices, and decrypting hidden cipher rumors. As guild bounties, civic proclamations, and faction rumor propagation expand, this router will grow beyond the 500-line limit unless decomposed into specialized routers.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Relationship checks and permission validation.
- **ADR-0002: Domain Events via eventsource-py**: Settlement aggregate persistence and CloudEvent emission.
- **ADR-0006: Redis Streams Transport**: Event bus broadcast of civic proclamations.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 120 lines).

## Scope of Work
1. **Notice Management Router (`services/game_session/src/game_session/settlement/routers/bulletin_notices_router.py`)**:
   - Endpoints for creating/pinning notices, querying active notices, and archiving (< 110 lines).
2. **Cipher & Rumor Router (`services/game_session/src/game_session/settlement/routers/bulletin_ciphers_router.py`)**:
   - Endpoints for decrypting cipher rumors, investigation checks, and rumor network broadcasts (< 100 lines).
3. **Router Aggregator (`services/game_session/src/game_session/settlement/bulletin_router.py`)**:
   - Include sub-routers into unified APIRouter export preserving backward compatibility (< 40 lines).
4. **Verification**:
   - Run blackbox tests (`tests/test_blackbox_bulletin_board.py` and `tests/test_blackbox_settlement_haven/`) to ensure 100% pass rate.

## Definition of Done
- `bulletin_router.py` refactored into modular sub-routers.
- All extracted files strictly < 120 lines each per Hard Invariant 6.
- 100% test pass rate across all settlement bulletin board blackbox test suites.
