---
id: '0144'
title: Mock SpiceDB Client and Auth Schema Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0008
- TASK-0035
- TASK-0044
governing_adrs:
- ADR-0001
governing_prds:
- PRD-0001
governing_stories:
- US-0009
- US-0013
target_release: 0.4.0
pr_url: https://github.com/tyevans/runefoble/pull/163
---
# TASK-0144: Mock SpiceDB Client and Auth Schema Modular Decomposition

## Status
Refined

## Summary
Decompose `libs/runefoble_auth/src/runefoble_auth/mock_spicedb.py` (457 lines, 91.4% of limit) into clean, single-responsibility submodules under `libs/runefoble_auth/src/runefoble_auth/mock/` (`client.py`, `evaluator.py`, `schema_parser.py`) with facade re-exports in `mock_spicedb.py`, ensuring all auth mock modules remain < 160 lines per Hard Invariant 6.

## Problem Statement
`libs/runefoble_auth/src/runefoble_auth/mock_spicedb.py` currently contains in-memory relationship tuple stores, Zed schema parsing, recursive graph-reachability checks, caveat evaluations, and gRPC client mock stubs across 457 lines. With new relations added for West Marches guilds, multi-campaign shared frontiers, and caravan trading, this file will soon cross the 500-line hard invariant ceiling.

## Governing Architecture & ADRs
- **ADR-0001: Fine-Grained Authorization with SpiceDB Zanzibar**: Clean mock implementation of Zanzibar relational authorization supporting local testing without a live SpiceDB container.

## Product & User Story References
- **Product Requirement**: [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- **User Stories**:
  - [`us-0009-zanzibar-campaign-access-control.md`](../../user_stories/accepted/us-0009-zanzibar-campaign-access-control.md)
  - [`us-0013-gateway-zanzibar-authorization.md`](../../user_stories/accepted/us-0013-gateway-zanzibar-authorization.md)

## Detailed Specification & Implementation Plan
1. **Schema Parser Submodule (`libs/runefoble_auth/src/runefoble_auth/mock/schema_parser.py`)**:
   - Extract Zed definition parsing, object relation parsing, and relation graph construction (< 130 lines).
2. **Permission Evaluator Submodule (`libs/runefoble_auth/src/runefoble_auth/mock/evaluator.py`)**:
   - Extract recursive Zanzibar permission resolution, arrow expressions, and caveat evaluation (< 140 lines).
3. **Mock Client Implementation (`libs/runefoble_auth/src/runefoble_auth/mock/client.py`)**:
   - Extract relationship tuple store, read/write relationships, touch tuples, and check permission methods (< 150 lines).
4. **Mock Client Facade (`libs/runefoble_auth/src/runefoble_auth/mock_spicedb.py`)**:
   - Re-export `MockSpiceDBClient` maintaining 100% backward compatibility for all callers and test suites (< 50 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Internal library refactoring with zero breaking changes to public mock APIs or test suites.
- **Negotiable (N)**: Internal class decomposition and submodule boundaries can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violation while drastically improving test fixture maintainability.
- **Estimable (E)**: Standard Python class extraction.
- **Small (S)**: Bounded strictly to `libs/runefoble_auth/src/runefoble_auth/`; all resulting files < 160 lines.
- **Testable (T)**: Verified by existing full test suite passing with zero regressions.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Architecture**:
   - `libs/runefoble_auth/src/runefoble_auth/mock/` created with `schema_parser.py`, `evaluator.py`, and `client.py`.
   - `mock_spicedb.py` reduced to < 60 lines facade re-export.
2. **Line Count Invariant**:
   - Zero files exceeding 180 lines within `libs/runefoble_auth/src/runefoble_auth/`.
3. **Test Suite Verification**:
   - `uv run pytest libs/runefoble_auth/ tests/test_blackbox_spicedb_auth_sync.py tests/test_blackbox_spicedb_live.py` passes cleanly.
4. **Quality Gates**:
   - Passes `uv run ruff check .` and `uv run ruff format --check .`.
