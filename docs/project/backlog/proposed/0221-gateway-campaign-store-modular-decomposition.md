---
id: '0221'
title: Gateway Campaign Store Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0007
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0221: Gateway Campaign Store Modular Decomposition

## Status
Proposed

## Summary
Decompose `gateway/api/src/gateway_api/campaign_store.py` (372 lines, 74.4% of limit) into modular packages under `gateway/api/src/gateway_api/campaign_store/` (`models.py`, `invites.py`, `store.py`), ensuring all modules remain strictly < 160 lines per Hard Invariant 6.

## Problem Statement
`gateway/api/src/gateway_api/campaign_store.py` defines `CampaignRecord`, `CampaignMemberRecord`, `InviteTokenRecord`, and the monolithic `CampaignStore` handling thread-safe campaign creation, member roles, invite redemption, and queries in a single file of 372 lines. As campaign settings, persistent database backing, and additional membership query filters are implemented, this file will approach the 500-line limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular package structure within the Gateway service.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation of storage records, invite token generators, and campaign repositories.

## Scope of Work
1. **Record Models (`gateway/api/src/gateway_api/campaign_store/models.py`)**:
   - Extract `CampaignRecord`, `CampaignMemberRecord`, and `InviteTokenRecord` dataclasses with dictionary serialization (< 120 lines).
2. **Invite Management (`gateway/api/src/gateway_api/campaign_store/invites.py`)**:
   - Extract secure token generation, expiration tracking, and invite validation logic (< 100 lines).
3. **Store Repository (`gateway/api/src/gateway_api/campaign_store/store.py`)**:
   - Extract `CampaignStore` state, mutation methods, and queries (< 160 lines).
4. **Package Facade (`gateway/api/src/gateway_api/campaign_store/__init__.py`)**:
   - Re-export `CampaignStore`, `CampaignRecord`, `CampaignMemberRecord`, and `InviteTokenRecord` for complete backwards compatibility (< 40 lines).
5. **Verification**:
   - Verify all Gateway API unit and blackbox tests pass via `uv run pytest gateway/api/tests/`.

## Definition of Done
- `gateway/api/src/gateway_api/campaign_store/` created with modular submodules all < 160 lines.
- Backward compatibility preserved for all existing imports.
- All tests pass via `uv run pytest gateway/api/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
