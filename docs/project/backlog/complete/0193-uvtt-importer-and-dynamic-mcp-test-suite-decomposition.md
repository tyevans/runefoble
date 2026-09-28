---
id: 0193
title: Universal VTT Importer and Dynamic MCP Test Suite Modular Decomposition
status: Complete
created: 2026-09-27
dependencies:
- TASK-0057
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0008
- ADR-0010
governing_prds:
- PRD-0022
governing_stories:
- US-0008
- US-0033
- US-0035
target_release: 0.7.0
pr_url: https://github.com/tyevans/runefoble/pull/254
---
# TASK-0193: Universal VTT Importer and Dynamic MCP Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_uvtt_import.py` (336 lines, 67.2% of limit) into two focused test modules under `tests/test_blackbox_uvtt_import/` (`test_uvtt_map_import.py` and `test_dynamic_mcp_registry.py`), keeping both test suites strictly < 160 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_blackbox_uvtt_import.py` contains 336 lines testing two distinct bounded contexts: Universal VTT (.dd2vtt) map importing into `board_state` (with Silo S3 asset storage) and dynamic FastMCP tool registration, security sandboxing, and execution lifecycle in `gateway_mcp`. Bundling these disparate concerns into a single test file causes unnecessary coupling and risks exceeding 400 lines as community plugin slots are introduced.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test module segregation across workspace packages.
- **ADR-0007: Domain-Driven Design Architecture**: Strict separation of board state map ingestion from MCP tool execution.
- **ADR-0008: FastMCP Gateway Architecture**: Dynamic MCP tool registration and sandboxed execution validation.
- **ADR-0010: Silo S3 Media Storage Pipeline**: Verification of battlemap texture upload and asset ID persistence.

## INVEST Criteria Evaluation
- **Independent (I)**: Test modular refactoring strictly isolated to `tests/test_blackbox_uvtt_import/` with zero production API disruption.
- **Negotiable (N)**: Test boundaries logically segregated between spatial map ingestion and dynamic MCP registry lifecycle.
- **Valuable (V)**: Safeguards against Hard Invariant 6 (>500 lines) and speeds up test targeting when debugging MCP tool sandboxes.
- **Estimable (E)**: Deterministic test migration into discrete modules sharing existing fixtures and helpers.
- **Small (S)**: Bounded strictly to test reorganization; each module < 160 lines.
- **Testable (T)**: Frontdoor verification via `uv run pytest tests/test_blackbox_uvtt_import/` asserting all map import and MCP registry flows pass.

## Detailed Specification & Implementation Plan
1. **Modular Test Package (`tests/test_blackbox_uvtt_import/`)**:
   - `conftest.py`: Shared fixtures (`board_client`, `gateway_client`, `clean_environment`, `build_sample_dd2vtt_dict`) (< 70 lines).
   - `test_uvtt_map_import.py`: Multipart .dd2vtt upload, JSON payload parsing, wall segments, door portals, lights, obstacle tokens, and Silo S3 background storage (< 140 lines).
   - `test_dynamic_mcp_registry.py`: FastMCP dynamic tool registration, hot discovery, administrative HTTP invocation, sandbox security rejections, and tool lifecycle (< 140 lines).
2. **Backward Compatibility**:
   - Maintain `tests/test_blackbox_uvtt_import.py` as a lightweight re-exporting test shim (< 40 lines).
3. **Verification**:
   - Run `uv run pytest tests/test_blackbox_uvtt_import/` and verify all tests pass.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
- `tests/test_blackbox_uvtt_import.py` decomposed into focused sub-suites under `tests/test_blackbox_uvtt_import/`.
- All test files strictly < 160 lines, well below the 500-line invariant.
- All UVTT import and dynamic MCP blackbox tests pass via `uv run pytest tests/test_blackbox_uvtt_import/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
