---
id: '0144'
title: Mock SpiceDB Client and Auth Schema Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0008
- TASK-0035
- TASK-0044
governing_adrs:
- ADR-0001
target_release: 0.4.0
---

# TASK-0144: Mock SpiceDB Client and Auth Schema Modular Decomposition

## Status
Proposed

## Summary
Decompose `libs/runefoble_auth/src/runefoble_auth/mock_spicedb.py` (378 lines) into clean submodules under `libs/runefoble_auth/src/runefoble_auth/mock/` (`client.py`, `evaluator.py`, `schema_parser.py`) to keep all auth mock modules < 150 lines per Hard Invariant 6.

## Problem Statement
`libs/runefoble_auth/src/runefoble_auth/mock_spicedb.py` currently contains in-memory tuple stores, Zed schema parsing, graph-reachability checks, and gRPC client mock stubs across 378 lines. With new relations added for West Marches guilds and factions, decomposing it prevents future file size violations.

## Governing Architecture & ADRs
- **ADR-0001**: SpiceDB Zanzibar authorization schema and mock testing harness.

## Scope of Work
1. **Schema Parser Submodule (`libs/runefoble_auth/src/runefoble_auth/mock/schema_parser.py`)**:
   - Extract Zed definition parsing and relation graph construction (< 130 lines).
2. **Permission Evaluator Submodule (`libs/runefoble_auth/src/runefoble_auth/mock/evaluator.py`)**:
   - Extract recursive Zanzibar permission resolution and caveat evaluation (< 130 lines).
3. **Mock Client Facade (`libs/runefoble_auth/src/runefoble_auth/mock_spicedb.py`)**:
   - Re-export `MockSpiceDBClient` maintaining backward-compatible interface (< 80 lines).
4. **Verification**:
   - Run auth tests and confirm 100% pass rate.
