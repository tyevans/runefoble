---
id: '0349'
title: Campaign Lore West Marches Router Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0127
- TASK-0135
- TASK-0145
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0007
- ADR-0009
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0014
- PRD-0018
governing_stories:
- US-0050
- US-0058
target_release: 0.8.0
---

# TASK-0349: Campaign Lore West Marches Router Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/campaign_lore/src/campaign_lore/routers/west_marches.py` (275 lines, 55.0% of limit) into modular submodules under `services/campaign_lore/src/campaign_lore/routers/west_marches/` (`models.py`, `discoveries.py`, `strongholds.py`, `router.py`), with an aggregator export at `services/campaign_lore/src/campaign_lore/routers/west_marches.py`, ensuring all submodules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`services/campaign_lore/src/campaign_lore/routers/west_marches.py` combines Pydantic request payload definitions, SpiceDB Zanzibar access control dependencies (`check_user_can_view_campaign`, `check_user_can_play_campaign`), discovery recording and retrieval endpoints, communal stronghold facility upgrade handling, and rest boon claim workflows in a single monolithic router file. As multi-party territorial influence, frontier supply lines, and seasonal weather events are integrated, this router will breach the 500-line limit unless decomposed into focused modules.

## Governing Architecture & ADRs
- **ADR-0001: Fine-Grained Authorization with SpiceDB Zanzibar Schema**: Object permissions for campaign viewing and play access.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout and isolated test execution.
- **ADR-0007: Domain-Driven Design Architecture**: Clean frontdoor testing across service aggregates.
- **ADR-0009: Code Quality and Linting with Ruff and Pre-commit**: Code formatting and linting standards.
- **ADR-0010: Continuous Integration Pipeline**: Rapid and modular test suite execution.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **West Marches Models (`services/campaign_lore/src/campaign_lore/routers/west_marches/models.py`)**:
   - Extract `RecordDiscoveryPayload`, `UpgradeStrongholdPayload`, and `ClaimRestBoonPayload` (< 60 lines).
2. **Discoveries Endpoints (`services/campaign_lore/src/campaign_lore/routers/west_marches/discoveries.py`)**:
   - Extract `POST /discoveries` and `GET /discoveries` with Zanzibar checks (< 85 lines).
3. **Strongholds & Boons Endpoints (`services/campaign_lore/src/campaign_lore/routers/west_marches/strongholds.py`)**:
   - Extract `POST /strongholds/upgrade`, `GET /strongholds/status`, and `POST /strongholds/rest-boons/claim` (< 100 lines).
4. **Router Aggregator (`services/campaign_lore/src/campaign_lore/routers/west_marches/router.py`)**:
   - Combine endpoints into an APIRouter (< 40 lines).
5. **Backwards-Compatible Entry Point (`services/campaign_lore/src/campaign_lore/routers/west_marches.py`)**:
   - Re-export `router`, models, and dependencies for existing callers (< 30 lines).
6. **Verification**:
   - Verify `uv run pytest tests/test_blackbox_west_marches.py` passes with 100% success.

## Definition of Done
- `services/campaign_lore/src/campaign_lore/routers/west_marches/` submodules strictly < 110 lines each per Hard Invariant 6.
- Root `west_marches.py` reduced to a backwards-compatible re-export module (< 40 lines).
- 100% pass rate on `uv run pytest tests/test_blackbox_west_marches.py`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
