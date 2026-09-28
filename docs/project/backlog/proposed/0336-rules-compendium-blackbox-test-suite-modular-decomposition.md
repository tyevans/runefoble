---
id: '0336'
title: Rules Compendium Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0048
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0008
governing_stories:
- US-0037
- US-0052
target_release: 0.8.0
---

# TASK-0336: Rules Compendium Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_rules_compendium.py` (287 lines, 57.4% of limit) into modular test submodules under `tests/test_blackbox_rules_compendium/` (`test_rule_search.py`, `test_homebrew_auth.py`, `test_encounter_builder.py`, `test_fastmcp_tools.py`), ensuring all test modules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_rules_compendium.py` consolidates sub-50ms canonical rule searches, SpiceDB Zanzibar homebrew rule authorization checks, CR formula calculations, and FastMCP tool invocations into a single 287-line file. As monster encounter variations and homebrew validation tests expand, this file will trend towards the 500-line invariant limit unless modularized.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/balance-combat-encounters-and-query-compendium.md`: Canonical SRD searches, encounter balance calculations, and homebrew rules.
  - `docs/reference/fastmcp-gateway.md`: Rules compendium MCP tool inventory and request schemas.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Fine-Grained Authorization**: Homebrew rule permissions.
  - **ADR-0007: Domain-Driven Design Architecture**: Rules compendium bounded context.
  - **ADR-0013: Modular Decomposition**: Single-responsibility test modules strictly < 150 lines.

## Scope of Work & Implementation Plan
1. **Rule Search Tests (`tests/test_blackbox_rules_compendium/test_rule_search.py`)**:
   - Extract sub-50ms canonical search, spell indexing, and fuzzy term matching tests (< 90 lines).
2. **Homebrew Authorization Tests (`tests/test_blackbox_rules_compendium/test_homebrew_auth.py`)**:
   - Extract SpiceDB Zanzibar permission checks, DM homebrew rule registration, and player visibility (< 90 lines).
3. **Encounter Builder Tests (`tests/test_blackbox_rules_compendium/test_encounter_builder.py`)**:
   - Extract party level scaling, monster CR arithmetic, and difficulty thresholds (< 90 lines).
4. **FastMCP Tools Tests (`tests/test_blackbox_rules_compendium/test_fastmcp_tools.py`)**:
   - Extract `compendium_search` and `calculate_encounter_cr` MCP tool invocation assertions (< 90 lines).
5. **Verification**:
   - Safely remove monolithic `tests/test_blackbox_rules_compendium.py` and verify all tests pass via `uv run pytest tests/test_blackbox_rules_compendium/`.

## INVEST Criteria Evaluation
- **Independent (I)**: Test reorganization is internal to the test directory and does not affect production rules logic.
- **Negotiable (N)**: Submodule grouping can be adjusted.
- **Valuable (V)**: Prevents test suite growth from violating Hard Invariant 6.
- **Estimable (E)**: Discrete test cases with existing 100% passing coverage.
- **Small (S)**: Each extracted test file will be strictly < 110 lines.
- **Testable (T)**: Directly executable via `uv run pytest tests/test_blackbox_rules_compendium/`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_blackbox_rules_compendium.py` decomposed into modular submodules under `tests/test_blackbox_rules_compendium/`.
2. All extracted submodules strictly < 110 lines per Hard Invariant 6.
3. 100% of blackbox assertions pass via `uv run pytest tests/test_blackbox_rules_compendium/`.
4. Monolithic `tests/test_blackbox_rules_compendium.py` safely removed.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
