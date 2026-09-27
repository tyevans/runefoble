---
id: '0217'
title: Project Visualizer Graph Rendering Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0012
governing_prds: []
governing_stories: []
target_release: 0.7.0
---

# TASK-0217: Project Visualizer Graph Rendering Modular Decomposition

## Status
Proposed

## Summary
Decompose `tools/project_visualizer/static/js/graph.js` (371 lines, 74.2% of limit) into focused ES module components under `tools/project_visualizer/static/js/graph/` (`simulation.js`, `nodes.js`, `links.js`, `zoom.js`), keeping all modules strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`tools/project_visualizer/static/js/graph.js` has grown to 371 lines as force simulation physics, node SVG rendering, edge routing, marker definitions, collision handling, and zoom behaviors were consolidated into a single JavaScript file. As additional entity visual representations (such as subagent clusters and PR status rings) are added, this file will breach the 500-line invariant limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook Design System**: Clean modular component and script structuring.
- **ADR-0012: Bauhaus Theme and Design Tokens**: Geometric node styles and visual token standards.

## Scope of Work
1. **Force Simulation Engine (`tools/project_visualizer/static/js/graph/simulation.js`)**:
   - Extract d3-force layout configuration, charge strengths, link distances, and center gravitation (< 90 lines).
2. **Node Renderer (`tools/project_visualizer/static/js/graph/nodes.js`)**:
   - Extract SVG node circle, label, status badge, and pulse animation rendering (< 110 lines).
3. **Link & Marker Renderer (`tools/project_visualizer/static/js/graph/links.js`)**:
   - Extract directed dependency edge routing, arrow markers, and bidirectional relationship arcs (< 100 lines).
4. **Zoom & Pan Controller (`tools/project_visualizer/static/js/graph/zoom.js`)**:
   - Extract d3-zoom event handling, transform caching, and reset/fit-to-screen controls (< 80 lines).
5. **Graph Orchestrator (`tools/project_visualizer/static/js/graph.js`)**:
   - Maintain a lightweight facade wiring together submodules (< 70 lines).
6. **Verification**:
   - Verify interactive graph rendering, filtering, node clicks, and drawer expansion via `python -m tools.project_visualizer.cli serve`.
   - Verify visualizer automated tests pass via `uv run pytest tests/test_project_visualizer*.py`.

## Definition of Done
- `graph.js` decomposed into focused submodules with all files strictly < 150 lines.
- Zero files in `tools/project_visualizer/static/js/graph/` exceed 200 lines.
- Visualizer graph renders accurately with all link and node interactions functioning.
- Visualizer tests pass via `uv run pytest tests/test_project_visualizer*.py`.
