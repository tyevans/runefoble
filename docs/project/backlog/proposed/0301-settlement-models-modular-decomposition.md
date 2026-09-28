---
id: '0301'
title: Settlement Models Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0259
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0024
governing_stories:
- US-0072
- US-0073
- US-0075
target_release: 0.8.0
---

# TASK-0301: Settlement Models Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/src/game_session/settlement/models.py` (299 lines, 59.8% of limit) into modular submodules under `services/game_session/src/game_session/settlement/models/` (`enums.py`, `haven.py`, `establishment.py`, `bulletin.py`, `worker.py`, `haggling.py`, `__init__.py`), keeping each submodule strictly < 100 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/settlement/models.py` currently consolidates all data schemas across the settlement haven domain into a single 299-line file:
1. Scale and tier enums, district limits, and civic benefit constants.
2. Haven and district state representations and upgrade request models.
3. Establishment state, production profiles, and creation schemas.
4. Bulletin board proclamations, rumor types, and posting schemas.
5. NPC worker profiles, social relationship graphs, and hiring schemas.
6. Merchant haggling profiles, negotiation sessions, and action models.

As living settlement features, cross-campaign haven trade, and deeper civic mechanics are added, this file will rapidly breach the 500-line limit unless modularized early.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout within bounded contexts.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation of settlement sub-domains.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 100 lines).

## Scope of Work
1. **Enums & Constants Submodule (`services/game_session/src/game_session/settlement/models/enums.py`)**:
   - Extract `SettlementScale`, `EstablishmentCategory`, `BulletinBoardType`, `BulletinCategory`, and scale mapping constants (< 80 lines).
2. **Haven & District Models (`services/game_session/src/game_session/settlement/models/haven.py`)**:
   - Extract `District`, `SettlementHavenState`, `CreateHavenRequest`, `UpgradeHavenRequest` (< 70 lines).
3. **Establishment Models (`services/game_session/src/game_session/settlement/models/establishment.py`)**:
   - Extract `EstablishmentState`, `EstablishmentCreateRequest`, `EstablishmentUpgradeRequest` (< 70 lines).
4. **Bulletin Models (`services/game_session/src/game_session/settlement/models/bulletin.py`)**:
   - Extract `BulletinNoticeItem`, `PostBulletinNoticeRequest`, `InspectNoticeResponse` (< 60 lines).
5. **Worker Models (`services/game_session/src/game_session/settlement/models/worker.py`)**:
   - Extract `WorkerAssignment`, `SocialRelationship`, `HireWorkerRequest` (< 60 lines).
6. **Haggling Models (`services/game_session/src/game_session/settlement/models/haggling.py`)**:
   - Extract `MerchantProfile`, `HaggleNegotiationSession`, `HaggleActionRequest`, `HaggleActionResponse` (< 80 lines).
7. **Package Facade (`services/game_session/src/game_session/settlement/models/__init__.py`)**:
   - Export all domain models and enums with 100% backwards compatibility (< 40 lines).
8. **Verification**:
   - Run `uv run pytest tests/test_blackbox_settlement*.py tests/test_blackbox_merchant_haggling.py` to verify full model compatibility.

## Definition of Done
- `services/game_session/src/game_session/settlement/models.py` replaced by `services/game_session/src/game_session/settlement/models/` package.
- All extracted submodules strictly < 100 lines each per Hard Invariant 6.
- 100% backwards compatibility preserved for all imports from `game_session.settlement.models`.
- All settlement blackbox tests pass cleanly.
