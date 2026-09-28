---
id: '0334'
title: Visualizer Graph Test Suite Modular Decomposition
status: Refined
created: 2026-09-28
dependencies:
- TASK-0227
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0009
- ADR-0010
- ADR-0013
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0334: Visualizer Graph Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_visualizer_graph.py` (376 lines, 75.2% of limit) into modular test submodules under `tests/test_visualizer_graph/` (`test_builder.py`, `test_facade.py`, `test_filters_and_metrics.py`, `test_serialization.py`), ensuring all test modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
Following the modular decomposition of `tools/project_visualizer/graph.py` in TASK-0227, additional test coverage for new filtering, metrics, and linking logic expanded `tests/test_visualizer_graph.py` to 376 lines. It now tests graph node/edge creation, backward-compatible facades, entity filtering, metric aggregates, and bundle JSON serialization in a single monolithic test file. Approaching the 500-line invariant ceiling (Hard Invariant 6), it must be decomposed into focused, single-responsibility submodules.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/visualize-project-content.md`: Graph rendering, node filtering, and dependency relationship tracing.
  - `docs/how-to/curate-backlog-and-roadmap.md`: Backlog item tracking and visualizer graph verification.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean tool structure and test isolation.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.
  - **ADR-0009: Code Quality and Linting with Ruff and Pre-commit**: Strict code formatting and linting.
  - **ADR-0010: Continuous Integration Pipeline**: Fast, modular test execution.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Single-responsibility test modules strictly < 150 lines.

## Scope of Work & Implementation Plan
1. **Graph Builder Tests (`tests/test_visualizer_graph/test_builder.py`)**:
   - Extract entity parsing, dependency edge construction, and bidirectional link validation (< 110 lines).
2. **Facade Compatibility Tests (`tests/test_visualizer_graph/test_facade.py`)**:
   - Extract legacy `scan_project`, `build_traceability_graph`, and `GraphBuilder` facade compatibility tests (< 90 lines).
3. **Filtering and Metrics Tests (`tests/test_visualizer_graph/test_filters_and_metrics.py`)**:
   - Extract tag/type filtering, search subgraphs, and health metric calculation assertions (< 100 lines).
4. **Serialization Tests (`tests/test_visualizer_graph/test_serialization.py`)**:
   - Extract standalone JSON bundle serialization, node positioning metadata, and export tests (< 100 lines).
5. **Verification**:
   - Safely remove root `tests/test_visualizer_graph.py` and verify all tests pass via `uv run pytest tests/test_visualizer_graph/`.

## INVEST Criteria Evaluation
- **Independent (I)**: Self-contained test restructuring without altering visualizer production logic.
- **Negotiable (N)**: Test submodule file names and fixtures can be tuned cleanly.
- **Valuable (V)**: Safeguards against Hard Invariant 6 violations on the largest Python test suite in the tools domain.
- **Estimable (E)**: Pure test modularization with existing 100% passing tests.
- **Small (S)**: Submodules will each be strictly < 130 lines.
- **Testable (T)**: Directly executable via `uv run pytest tests/test_visualizer_graph/`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_visualizer_graph.py` decomposed into `tests/test_visualizer_graph/` package.
2. All extracted submodules strictly < 130 lines per Hard Invariant 6.
3. 100% of test assertions pass via `uv run pytest tests/test_visualizer_graph/`.
4. Monolithic `tests/test_visualizer_graph.py` safely removed.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
