---
id: '0291'
title: Project Visualizer Core Client Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0217
- TASK-0224
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0291: Project Visualizer Core Client Modular Decomposition

## Status
Proposed

## Summary
Decompose `tools/project_visualizer/static/js/core.js` (315 lines, 63.0% of limit) into modular ES scripts under `tools/project_visualizer/static/js/core/` (`state.js`, `kpi.js`, `tabs.js`, `shortcuts.js`), ensuring all modules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`tools/project_visualizer/static/js/core.js` acts as the central client runtime for the developer project content visualizer. It consolidates global visualizer state initialization, KPI summary badge counters, tab switching and content container rendering, keyboard shortcut listeners, theme toggle persistence, and live sync polling into a single 315-line script. As new views and real-time live update metrics are added, this file will approach the 500-line limit unless decomposed into focused, single-responsibility modules.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean tooling modularity and maintainability.
- **ADR-0007: Domain-Driven Design Architecture**: Clean separation between developer tools and runtime platform services.
- **ADR-0013: Modular Decomposition**: Maintain all source files strictly < 500 lines (and submodules < 110 lines).

## Scope of Work
1. **Core State & Initialization (`tools/project_visualizer/static/js/core/state.js`)**:
   - Extract state declaration, default filter definitions, graph viewport settings, and live sync handler (< 90 lines).
2. **KPI Counters & Metrics (`tools/project_visualizer/static/js/core/kpi.js`)**:
   - Extract metric parsing, DOM counter updates, task completion tallying, and badge rendering (< 80 lines).
3. **Tab Navigation & Container Orchestration (`tools/project_visualizer/static/js/core/tabs.js`)**:
   - Extract URL hash detection, tab button active styling, container view dispatch, and scroll preservation (< 100 lines).
4. **Keyboard Shortcuts & Theme (`tools/project_visualizer/static/js/core/shortcuts.js`)**:
   - Extract global keyboard listeners, tab cycling shortcuts, help modal triggers, and theme mode synchronization (< 80 lines).
5. **Template & Bundle Integration**:
   - Update `tools/project_visualizer/template.py` to import modularized scripts cleanly, ensuring zero visualizer regression.

## Definition of Done
- `tools/project_visualizer/static/js/core.js` decomposed into `tools/project_visualizer/static/js/core/` modules.
- All extracted modules strictly < 110 lines per Hard Invariant 6.
- Visualizer HTML bundle renders and functions identically in browser.
- Visualizer test suite passes via `uv run pytest tests/test_visualizer_*.py`.
