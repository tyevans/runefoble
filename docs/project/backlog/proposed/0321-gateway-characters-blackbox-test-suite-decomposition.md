---
id: '0321'
title: Gateway Characters Blackbox Test Suite Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0252
- TASK-0258
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0008
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0064
target_release: 0.8.0
---

# TASK-0321: Gateway Characters Blackbox Test Suite Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_gateway_characters.py` (284 lines, 56.8% of limit) into modular test sub-suites under `tests/test_blackbox_gateway_characters/` (`test_character_crud.py`, `test_character_zanzibar_auth.py`, `test_character_campaign_assignment.py`), keeping each test module strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_gateway_characters.py` tests character creation, listing, Zanzibar ownership enforcement, campaign linking, and deletion through the API Gateway frontdoor. As additional character attributes, party bindings, and multi-tenant isolation rules are introduced, this test suite will approach the 500-line ceiling unless decomposed into modular test submodules.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Relationship verification and access control.
- **ADR-0005: Zitadel OIDC Authentication**: User header extraction and identity verification.
- **ADR-0008: Property-Based and Blackbox Testing**: Frontdoor API assertions and HTTP client calls.
- **ADR-0013: Modular Decomposition**: All test modules kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Character CRUD Suite (`tests/test_blackbox_gateway_characters/test_character_crud.py`)**:
   - Character creation, default stats, update, and deletion frontdoor tests (< 95 lines).
2. **Zanzibar Authorization Suite (`tests/test_blackbox_gateway_characters/test_character_zanzibar_auth.py`)**:
   - Ownership tuples, unauthorized read rejection (403), and multi-tenant isolation (< 95 lines).
3. **Campaign Assignment Suite (`tests/test_blackbox_gateway_characters/test_character_campaign_assignment.py`)**:
   - Assigning/unassigning characters to campaigns, party visibility, and casing compatibility (< 95 lines).
4. **Verification**:
   - Run `uv run pytest tests/test_blackbox_gateway_characters/` to ensure 100% test pass rate.

## Definition of Done
- `tests/test_blackbox_gateway_characters.py` decomposed into `tests/test_blackbox_gateway_characters/` package.
- All extracted test modules strictly < 110 lines each per Hard Invariant 6.
- 100% test pass rate preserved across all gateway character API checks.
