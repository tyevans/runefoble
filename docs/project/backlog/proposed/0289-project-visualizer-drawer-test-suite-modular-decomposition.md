---
id: '0289'
title: Project Visualizer Drawer Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0219
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0289: Project Visualizer Drawer Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_visualizer_drawer.py` (309 lines, 61.8% of limit) into modular test submodules under `tests/test_visualizer_drawer/` (`conftest.py`, `test_drawer_dom.py`, `test_drawer_interactions.py`, `test_drawer_filters.py`), ensuring all test modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`tests/test_visualizer_drawer.py` verifies HTML generation, DOM structure, metadata inspection panels, tab switching, search filtering, and drawer animation contracts for the developer project content visualizer in a single 309-line module. As additional Redstring dependency tracing, PRD status badges, and milestone timeline views are added, this test suite will approach the 500-line invariant limit unless modularized.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test package structuring.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain model and tooling segregation.
- **ADR-0013: Modular Decomposition**: Test files decomposed into single-responsibility submodules < 130 lines.

## Scope of Work
1. **Shared Fixtures (`tests/test_visualizer_drawer/conftest.py`)**:
   - Extract mock graph builder fixtures, HTML drawer generator helpers, and test DOM nodes (< 50 lines).
2. **DOM Structure Tests (`tests/test_visualizer_drawer/test_drawer_dom.py`)**:
   - Extract drawer container verification, header elements, tab button rendering, and metadata attribute tests (< 100 lines).
3. **Drawer Interactions Tests (`tests/test_visualizer_drawer/test_drawer_interactions.py`)**:
   - Extract toggle events, panel transitions, collapse/expand actions, and keyboard shortcuts (< 100 lines).
4. **Search & Filter Tests (`tests/test_visualizer_drawer/test_drawer_filters.py`)**:
   - Extract entity search filtering, tag queries, status badge toggles, and Redstring link rendering (< 100 lines).
5. **Verification**:
   - Safely remove monolithic `tests/test_visualizer_drawer.py` and run `uv run pytest tests/test_visualizer_drawer/`.

## Definition of Done
- `tests/test_visualizer_drawer/` submodules strictly < 130 lines each.
- Root `tests/test_visualizer_drawer.py` safely removed.
- Passes all tests via `uv run pytest tests/test_visualizer_drawer/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
