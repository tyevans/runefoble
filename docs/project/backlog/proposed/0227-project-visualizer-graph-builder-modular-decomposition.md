---
id: '0227'
title: Project Visualizer Graph Builder Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0007
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0227: Project Visualizer Graph Builder Modular Decomposition

## Status
Proposed

## Summary
Decompose `tools/project_visualizer/graph.py` (327 lines, 65.4% of limit) into modular Python submodules under `tools/project_visualizer/graph/` (`models.py`, `builder.py`, `filtering.py`), ensuring all modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`tools/project_visualizer/graph.py` handles graph node/edge data structures, dependency graph construction from parsed markdown entities, filtering logic, and JSON serialization in a single file of 327 lines. As entity clustering, temporal milestone filters, and Redstring dependency tracing are added, this file will expand towards the 500-line ceiling unless modularized.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular tool structure.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.

## Scope of Work
1. **Graph Models (`tools/project_visualizer/graph/models.py`)**:
   - Extract `GraphNode`, `GraphEdge`, and `GraphData` dataclasses (< 90 lines).
2. **Graph Construction (`tools/project_visualizer/graph/builder.py`)**:
   - Extract graph node construction from entities and edge synthesis (< 120 lines).
3. **Graph Filtering (`tools/project_visualizer/graph/filtering.py`)**:
   - Extract tag/type filtering, search subgraphs, and layout positioning hints (< 110 lines).
4. **Aggregator Facade (`tools/project_visualizer/graph.py` or `graph/__init__.py`)**:
   - Re-export for complete backwards compatibility (< 30 lines).
5. **Verification**:
   - Verify all tests pass via `uv run pytest tests/test_visualizer_parser.py tests/test_project_visualizer_agy.py`.

## Definition of Done
- Modular `graph/` submodules strictly < 130 lines each.
- Backwards compatibility preserved.
- All visualizer tests pass cleanly.
