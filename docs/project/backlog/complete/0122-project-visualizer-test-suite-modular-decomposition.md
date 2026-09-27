---
id: '0122'
title: Project Visualizer Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0059
- TASK-0066
governing_adrs:
- ADR-0003
- ADR-0009
target_release: 0.4.0
pr_url: https://github.com/tyevans/runefoble/pull/135
---
# TASK-0122: Project Visualizer Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_project_visualizer.py` (416 lines) into modular test suites (`test_visualizer_parser.py`, `test_visualizer_graph.py`, and `test_visualizer_server.py`), ensuring all test files remain strictly under 250 lines.

## Problem Statement
`tests/test_project_visualizer.py` currently spans 416 lines, approaching the 500-line hard invariant limit (Hard Invariant 6). It consolidates entity parsing, graph edge construction, metric calculations, HTTP server handler, and CLI smoke tests.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module and test organization.
- **ADR-0009: Code Quality and Linting with Ruff and Pre-commit**: High maintainability and fast test execution.

## Detailed Specification & Implementation Plan
1. **Parser Suite (`tests/test_visualizer_parser.py`)**:
   - Tests for `ProjectParser`, entity extraction across personas, ADRs, PRDs, stories, and tasks (< 150 lines).
2. **Graph Builder Suite (`tests/test_visualizer_graph.py`)**:
   - Tests for `ProjectGraphBuilder`, edge relationships (`governed_by`, `specifies`, `desires`), and buffer metrics (< 150 lines).
3. **Server & CLI Suite (`tests/test_visualizer_server.py`)**:
   - Tests for `HTTPServer`, HTTP handlers, SSE live reload endpoints, static asset resolution, and CLI main entrypoint (< 150 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors test structure without changing visualizer parsing, graphing, or serving logic.
- **Negotiable (N)**: Test case grouping can be adjusted between parser and graph tests.
- **Valuable (V)**: Prevents test suite from breaching file length limits while clarifying test failure locations.
- **Estimable (E)**: Pure mechanical pytest decomposition.
- **Small (S)**: Scope strictly isolated to `tests/`; all resulting files < 200 lines.
- **Testable (T)**: Verified by running `uv run pytest tests/test_visualizer_*.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Decomposed Modules**:
   - `tests/test_project_visualizer.py` eliminated; replacement test files each strictly < 250 lines.
2. **Zero Regressions**:
   - 100% of existing visualizer assertions pass without modification.
3. **Quality Gates**:
   - Conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `uv run pytest tests/test_visualizer_*.py` and `uv run ruff check .`.
