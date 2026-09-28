---
id: '0335'
title: Project Visualizer Template Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0224
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0335: Project Visualizer Template Modular Decomposition

## Status
Proposed

## Summary
Decompose `tools/project_visualizer/template.py` (311 lines, 62.2% of limit) into modular Python template submodules under `tools/project_visualizer/templates/` (`shell.py`, `modals.py`, `drawers.py`, `headers.py`), ensuring all modules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`tools/project_visualizer/template.py` generates the HTML shell, live Antigravity (AGY) launcher modals, filter control toolbars, drawer overlays, and script asset inclusions in a single 311-line module. As additional interactive visualizer components (e.g. Gantt zoom controls, entity creation wizards) are added, this file will trend toward the 500-line invariant ceiling unless modularized.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/visualize-project-content.md`: Standalone HTML export, AGY launcher modal, and interactive layout structure.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean tool structure.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.
  - **ADR-0013: Modular Decomposition**: Single-responsibility Python modules strictly < 150 lines.

## Scope of Work & Implementation Plan
1. **Shell and Layout Template (`tools/project_visualizer/templates/shell.py`)**:
   - Extract base HTML5 container, viewport metadata, CSS inclusions, and app root mounting (< 90 lines).
2. **AGY Modal Templates (`tools/project_visualizer/templates/modals.py`)**:
   - Extract AGY launcher modal backdrop, prompt preset triggers, and live server controls (< 90 lines).
3. **Drawer and Inspection Overlays (`tools/project_visualizer/templates/drawers.py`)**:
   - Extract sliding inspection drawer markup, tabs, and action buttons (< 90 lines).
4. **Header and Toolbar Actions (`tools/project_visualizer/templates/headers.py`)**:
   - Extract top navigation bar, filter toggles, search inputs, and view switcher buttons (< 90 lines).
5. **Facade Re-export (`tools/project_visualizer/template.py`)**:
   - Maintain `render_html_shell` facade re-exporting the assembled template with full backwards compatibility (< 40 lines).
6. **Verification**:
   - Verify visualizer generation and tests via `uv run pytest tests/test_visualizer_server.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal template layout decomposition preserving the visualizer's public generation output.
- **Negotiable (N)**: Template breakdown boundaries can be adapted cleanly.
- **Valuable (V)**: Protects visualizer HTML templating from exceeding the 500-line limit.
- **Estimable (E)**: Pure HTML string template segregation.
- **Small (S)**: Submodules will each be strictly < 110 lines.
- **Testable (T)**: Existing visualizer server and client test suites verify HTML output parity.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tools/project_visualizer/template.py` reduced to a facade < 40 lines.
2. Modular submodules in `tools/project_visualizer/templates/` strictly < 110 lines each.
3. Zero regressions in standalone visualizer bundle output or live dev server.
4. All visualizer tests pass via `uv run pytest tests/test_visualizer_server.py`.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
