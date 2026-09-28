---
id: '0265'
title: Gateway Campaign Store Test Suite Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0221
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0007
governing_prds:
- PRD-0023
governing_stories:
- US-0063
target_release: 0.8.0
---

# TASK-0265: Gateway Campaign Store Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_gateway_campaign_store_decomposition.py` (313 lines) into modular test submodules under `tests/test_blackbox_gateway_campaign_store/` (`conftest.py`, `test_campaign_crud.py`, `test_campaign_members.py`, `test_campaign_queries.py`), keeping all test files strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_gateway_campaign_store_decomposition.py` covers campaign creation, membership persistence, query filters, and state mutations in a single test module. As session persistence (TASK-0246) and character assignment relations (TASK-0252) add further tests to this test suite, it will approach the 500-line invariant limit unless decomposed into focused, single-responsibility submodules.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Authorization checks and membership relationship testing.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test package structuring.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation between campaigns and sessions.

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_gateway_campaign_store/conftest.py`)**:
   - Extract in-memory store initialization, campaign record factories, and helper functions (< 50 lines).
2. **Campaign CRUD Tests (`tests/test_blackbox_gateway_campaign_store/test_campaign_crud.py`)**:
   - Extract campaign creation, lookup, update, and deletion test cases (< 100 lines).
3. **Campaign Membership Tests (`tests/test_blackbox_gateway_campaign_store/test_campaign_members.py`)**:
   - Extract membership role management, invite token generation, and role update tests (< 100 lines).
4. **Campaign Query and Filter Tests (`tests/test_blackbox_gateway_campaign_store/test_campaign_queries.py`)**:
   - Extract user campaign filtering, pagination, and sorting test cases (< 90 lines).
5. **Verification**:
   - Remove root test module `test_blackbox_gateway_campaign_store_decomposition.py` and run `uv run pytest tests/test_blackbox_gateway_campaign_store/`.

## Definition of Done
- `tests/test_blackbox_gateway_campaign_store/` package created with submodules strictly < 120 lines.
- All test assertions pass via `uv run pytest tests/test_blackbox_gateway_campaign_store/`.
- Zero lint or formatting errors (`uv run ruff check .` and `uv run ruff format --check .`).
