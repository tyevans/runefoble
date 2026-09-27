---
id: '0221'
title: Gateway Campaign Store Modular Decomposition
status: Complete
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0007
governing_prds: []
governing_stories: []
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/239
---
# TASK-0221: Gateway Campaign Store Modular Decomposition

## Status
Refined

## Summary
Decompose `gateway/api/src/gateway_api/campaign_store.py` (371 lines, 74.2% of limit) into modular packages under `gateway/api/src/gateway_api/campaign_store/` (`models.py`, `invites.py`, `store.py`), ensuring all modules remain strictly < 160 lines per Hard Invariant 6.

## Problem Statement
`gateway/api/src/gateway_api/campaign_store.py` defines `CampaignRecord`, `CampaignMemberRecord`, `InviteTokenRecord`, and the monolithic `CampaignStore` handling thread-safe campaign creation, member roles, invite redemption, and queries in a single file of 371 lines. As campaign settings, persistent database backing, and additional membership query filters are implemented, this file will approach the 500-line limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular package structure within the Gateway service.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation of storage records, invite token generators, and campaign repositories.

## Detailed Specification & Implementation Plan
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

## INVEST Criteria Evaluation
- **Independent (I)**: Pure internal refactoring of the Gateway store package with zero external API changes.
- **Negotiable (N)**: File naming and helper module boundaries can be adapted to service needs.
- **Valuable (V)**: Protects `campaign_store.py` from exceeding Hard Invariant 6 (500 lines) and improves modularity.
- **Estimable (E)**: Pure extraction of dataclasses, token generators, and store methods.
- **Small (S)**: Bounded strictly to `gateway/api/src/gateway_api/campaign_store/`; all submodules < 160 lines.
- **Testable (T)**: Frontdoor verification via existing Gateway campaign API tests.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `gateway/api/src/gateway_api/campaign_store/` created with modular submodules all < 160 lines.
   - Backward compatibility preserved for all existing imports.
2. **Frontdoor Test Verification**:
   - All tests pass via `uv run pytest gateway/api/`.
3. **Quality Gates**:
   - Passes `uv run ruff check .` and `uv run ruff format --check .`.
