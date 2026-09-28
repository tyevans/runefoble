---
id: '0227'
title: Project Visualizer Graph Builder Modular Decomposition
status: Complete
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds: []
governing_stories: []
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/330
---

# TASK-0227: Project Visualizer Graph Builder Modular Decomposition

## Status
Complete

## Summary
Decompose `tools/project_visualizer/graph.py` (327 lines, 65.4% of limit) into modular Python submodules under `tools/project_visualizer/graph/` (`models.py`, `builder.py`, `filtering.py`), ensuring all modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`tools/project_visualizer/graph.py` handles graph node/edge data structures, dependency graph construction from parsed markdown entities, filtering logic, and JSON serialization in a single file of 327 lines. As entity clustering, temporal milestone filters, and Redstring dependency tracing are added, this file will expand towards the 500-line ceiling unless modularized.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/visualize-project-content.md`: Graph rendering, node filtering, and dependency relationship tracing.
  - `docs/how-to/curate-backlog-and-roadmap.md`: Backlog item tracking and visualizer graph synchronization.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular tool structure.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.
  - **ADR-0013: Modular Decomposition**: Single-responsibility Python modules strictly < 150 lines.

## Product & User Story References
- Technical debt refactoring supporting internal developer tooling:
  - [`docs/how-to/visualize-project-content.md`](../../../how-to/visualize-project-content.md)

## Detailed Specification & Implementation Plan
1. **Graph Models (`tools/project_visualizer/graph/models.py`)**:
   - Extract `GraphNode`, `GraphEdge`, and `GraphData` dataclasses (< 90 lines).
2. **Graph Construction (`tools/project_visualizer/graph/builder.py`)**:
   - Extract graph node construction from entities and edge synthesis (< 120 lines).
3. **Graph Filtering (`tools/project_visualizer/graph/filtering.py`)**:
   - Extract tag/type filtering, search subgraphs, and layout positioning hints (< 110 lines).
4. **Aggregator Facade (`tools/project_visualizer/graph.py` or `graph/__init__.py`)**:
   - Re-export all classes and functions maintaining complete backwards compatibility (< 35 lines).
5. **Verification**:
   - Verify all tests pass via `uv run pytest tests/test_visualizer_parser.py tests/test_project_visualizer_agy.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal module decomposition without breaking visualizer API or frontend JSON contracts.
- **Negotiable (N)**: Submodule naming can be tailored.
- **Valuable (V)**: Protects visualizer graph generation from breaching the 500-line invariant limit.
- **Estimable (E)**: Pure dataclass and builder separation.
- **Small (S)**: Submodules will each be strictly < 130 lines.
- **Testable (T)**: Existing visualizer test suite verifies graph serialization parity.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tools/project_visualizer/graph.py` facade reduced to < 40 lines.
2. Modular `graph/` submodules strictly < 130 lines each.
3. Backwards compatibility preserved.
4. All visualizer tests pass cleanly via `uv run pytest tests/test_visualizer_parser.py tests/test_project_visualizer_agy.py`.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
