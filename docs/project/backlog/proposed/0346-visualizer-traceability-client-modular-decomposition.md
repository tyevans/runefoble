---
id: '0346'
title: Visualizer Traceability Client Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0217
- TASK-0227
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0013
governing_stories:
- US-0042
target_release: 0.8.0
---

# TASK-0346: Visualizer Traceability Client Modular Decomposition

## Status
Proposed

## Summary
Decompose `tools/project_visualizer/static/js/traceability.js` (278 lines, 55.6% of limit) into modular submodules under `tools/project_visualizer/static/js/traceability/` (`controls.js`, `matrix.js`, `columns.js`), with an aggregator export at `tools/project_visualizer/static/js/traceability.js`, ensuring all submodules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`tools/project_visualizer/static/js/traceability.js` contains the multi-column requirements traceability matrix (Personas, Stories, PRDs, Tasks, ADRs), filter controls (hide done, persona, status), interactive node lineage tracing, SVG dependency arrows, and selection state handling in a single client script. As tag-based filtering, epic groupings, and exportable CSV/SVG matrices are added, this file will exceed 400 lines unless modularized into focused UI components.

## Governing Architecture & ADRs
- **ADR-0004: Frontend Visualizer Architecture**: Clean modular scripts.
- **ADR-0012: Design Tokens and Modern UI Layout**: Standard styling and contrast.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Traceability Controls Bar (`tools/project_visualizer/static/js/traceability/controls.js`)**:
   - Extract filter dropdowns, toggle checkboxes, and reset buttons (< 85 lines).
2. **Column Cards & Nodes (`tools/project_visualizer/static/js/traceability/columns.js`)**:
   - Extract column header rendering, item card templates, status pills, and double-click drawer hooks (< 100 lines).
3. **Matrix Orchestrator & Lineage Tracing (`tools/project_visualizer/static/js/traceability/matrix.js`)**:
   - Extract connection line calculations, lineage highlight traversal, and multi-column flex layout (< 95 lines).
4. **Aggregator Entry Point (`tools/project_visualizer/static/js/traceability.js`)**:
   - Re-export `renderTraceability` facade to bind seamlessly to `window.visualizer` (< 30 lines).
5. **Verification**:
   - Ensure visualizer tests pass via `uv run pytest tests/test_visualizer_graph.py` and visualizer test suites.

## Definition of Done
- `tools/project_visualizer/static/js/traceability/` submodules strictly < 110 lines each per Hard Invariant 6.
- Root `traceability.js` reduced to < 35 lines.
- Visualizer tests pass via `uv run pytest`.
- Code passes lint and format checks.
