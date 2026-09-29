---
id: '0342'
title: Campaign Lore RAG Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0047
- TASK-0089
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0007
governing_stories:
- US-0036
target_release: 0.8.0
---

# TASK-0342: Campaign Lore RAG Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_campaign_lore_rag.py` (282 lines, 56.4% of limit) into modular test submodules under `tests/test_blackbox_campaign_lore_rag/` (`conftest.py`, `test_documents_and_aliases.py`, `test_hybrid_search_and_auth.py`, `test_openapi_and_manifest.py`), ensuring all test submodules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_campaign_lore_rag.py` verifies document ingestion, redstring entity extraction, alias consolidation and resolution, sub-50ms hybrid BM25 and embedding search, SpiceDB Zanzibar secret filtering permissions, and OpenAPI / UI manifest endpoints in a single monolithic test file. As campaign knowledge graph expansions, deep cross-campaign lore links, and graph-walking features are added, this test suite will approach the 500-line invariant limit unless modularized into focused test suites.

## Governing Architecture & ADRs
- **ADR-0001: Fine-Grained Authorization with SpiceDB Zanzibar Schema**: Zanzibar object permissions for DM-only secret lore filtering.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test package structuring.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Real-time event propagation and stream broadcasting.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain boundaries.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_campaign_lore_rag/conftest.py`)**:
   - Extract test client setup, app instance binding, and shared test session utilities (< 40 lines).
2. **Document Ingestion & Alias Tests (`tests/test_blackbox_campaign_lore_rag/test_documents_and_aliases.py`)**:
   - Extract document ingestion, public retrieval, and redstring alias consolidation/resolution test functions (< 100 lines).
3. **Hybrid Search & SpiceDB Auth Tests (`tests/test_blackbox_campaign_lore_rag/test_hybrid_search_and_auth.py`)**:
   - Extract sub-50ms hybrid search benchmarking and SpiceDB Zanzibar secret document filtering tests (< 105 lines).
4. **OpenAPI & UI Manifest Tests (`tests/test_blackbox_campaign_lore_rag/test_openapi_and_manifest.py`)**:
   - Extract OpenAPI documentation and UI microfrontend manifest contract checks (< 40 lines).
5. **Verification**:
   - Safely remove root `tests/test_blackbox_campaign_lore_rag.py` and ensure `uv run pytest tests/test_blackbox_campaign_lore_rag/` passes 100%.

## Definition of Done
- `tests/test_blackbox_campaign_lore_rag/` submodules strictly < 110 lines each per Hard Invariant 6.
- Root `tests/test_blackbox_campaign_lore_rag.py` safely removed.
- Passes all tests via `uv run pytest tests/test_blackbox_campaign_lore_rag/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
