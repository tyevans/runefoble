---
id: 0218
title: Project Visualizer AGY Test Suite Modular Decomposition
status: Complete
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0003
governing_prds: []
governing_stories: []
target_release: 0.7.0
pr_url: https://github.com/tyevans/runefoble/pull/230
---
# TASK-0218: Project Visualizer AGY Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_project_visualizer_agy.py` (423 lines, 84.6% of limit) into modular test files under `tests/test_project_visualizer_agy/` (`conftest.py`, `test_agy_endpoint.py`, `test_agy_launcher.py`, `test_agy_execution.py`), keeping all test modules strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`tests/test_project_visualizer_agy.py` validates the visualizer's `/api/run-agy` endpoint, mock subprocess execution, CLI launch flags, and error status responses in a monolithic test file of 423 lines. As additional AGY launch modes and slash command integrations are tested, this suite will approach the 500-line invariant ceiling unless decomposed.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular test suite organization and fixture reuse.

## Detailed Specification & Implementation Plan
1. **Shared Fixtures (`tests/test_project_visualizer_agy/conftest.py`)**:
   - Extract test client setup, mock process runners, and temporary task workspace fixtures (< 60 lines).
2. **Endpoint Validation Tests (`tests/test_project_visualizer_agy/test_agy_endpoint.py`)**:
   - Test request body parsing, 422 error states, and task resolution (< 90 lines).
3. **Launcher Flag Tests (`tests/test_project_visualizer_agy/test_agy_launcher.py`)**:
   - Test command line construction, flag forwarding, and terminal environment handling (< 100 lines).
4. **Execution & Stream Tests (`tests/test_project_visualizer_agy/test_agy_execution.py`)**:
   - Test asynchronous process invocation, return code handling, and output capture (< 110 lines).
5. **Verification**:
   - Verify all tests pass via `uv run pytest tests/test_project_visualizer_agy/`.

## INVEST Criteria Evaluation
- **Independent (I)**: Test organization refactor with zero production runtime code changes.
- **Negotiable (N)**: Test function distribution across submodules can be organized logically by feature slice.
- **Valuable (V)**: Protects test suite maintainability, prevents Hard Invariant 6 breach, and improves test discovery.
- **Estimable (E)**: Straightforward refactor of existing passing tests into separate files.
- **Small (S)**: Bounded strictly to `tests/test_project_visualizer_agy/`; all modules < 130 lines.
- **Testable (T)**: Frontdoor verification via `pytest` test runner ensuring 100% test pass rate.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Test Suite Architecture**:
   - `tests/test_project_visualizer_agy/` package created with all files strictly < 130 lines per Hard Invariant 6.
   - Original `tests/test_project_visualizer_agy.py` removed.
2. **Frontdoor Test Verification**:
   - All visualizer tests pass via `uv run pytest tests/test_project_visualizer_agy/`.
3. **Quality Gates**:
   - Code passes `uv run ruff check .` and `uv run ruff format --check .`.
