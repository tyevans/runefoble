---
id: '0066'
title: Project Visualizer Client Assets and Standalone HTML Template Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0059]
governing_adrs: [ADR-0003]
target_release: 0.2.0
---

# TASK-0066: Project Visualizer Client Assets and Standalone HTML Template Modular Decomposition

## Status
Proposed

## Summary
Decompose `tools/project_visualizer/assets_js.py` (929 lines) and `tools/project_visualizer/template.py` (280 lines) into discrete, modular client JavaScript asset files (`visualizer_core.js`, `visualizer_graph.js`, `visualizer_drawer.js`, `visualizer_kanban.js`) bundled or loaded at runtime, eliminating monolithic 900+ line Python string files.

## Problem Statement
`tools/project_visualizer/assets_js.py` currently spans 929 lines. It defines a single Python function `get_client_js()` that returns an embedded 920-line JavaScript string containing the entire client-side web application for the dynamic project visualizer:
1. State management and event listener setup.
2. SVG traceability graph rendering and node physics.
3. Redstring dependency traversal and bidirectional highlighting.
4. Entity inspection drawer formatting (ADRs, PRDs, User Stories, Backlog tasks).
5. Interactive Kanban board filtering and persona breakdowns.
6. Omnibar search indexing and keyboard shortcuts.
7. Theme switching and live SSE/WebSocket auto-sync polling.

Embedding a 900+ line JS codebase in a Python string makes code formatting, linting, syntax highlighting, and unit testing difficult, while technically violating the principle of Hard Invariant 6 (File length limit < 500 lines).

Similarly, `tools/project_visualizer/template.py` (280 lines) contains large embedded HTML/CSS strings for document structure and styling.

## Proposed Decomposition
1. **Static JavaScript Modules (`tools/project_visualizer/static/js/`)**:
   - `core.js`: State management, theme toggle, omnibar, and live sync (< 150 lines).
   - `graph.js`: Traceability SVG graph layout, node rendering, and zoom/pan (< 200 lines).
   - `drawer.js`: Entity details side drawer, markdown viewer, and links (< 150 lines).
   - `kanban.js`: Kanban board column rendering and status pills (< 150 lines).
2. **Asset Bundler / Loader (`tools/project_visualizer/assets_js.py`)**:
   - Refactor `get_client_js()` to read and concatenate or bundle the static JS modules from `tools/project_visualizer/static/js/` (< 50 lines).
3. **Template Decomposition (`tools/project_visualizer/template.py`)**:
   - Extract CSS styles into `static/css/styles.css` (< 200 lines).
   - Retain `template.py` as a lightweight HTML structure generator (< 120 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal asset packaging without altering the generated HTML output, CLI commands, or visualizer server.
- **Negotiable (N)**: Distribution between static asset files and bundling mechanism can be adjusted.
- **Valuable (V)**: Brings developer tooling into compliance with file length invariants (< 500 lines) and enables proper syntax highlighting and linting for visualizer client code.
- **Estimable (E)**: Pure extraction of JavaScript and CSS strings into native `.js` and `.css` files with a file-reading loader.
- **Small (S)**: Confined strictly to `tools/project_visualizer/`; all resulting files < 220 lines.
- **Testable (T)**: Verified with `python3 scripts/generate_project_graph.py` and `uv run pytest tests/test_project_visualizer.py`.

## Acceptance Criteria
1. `tools/project_visualizer/assets_js.py` and all companion static files are strictly under 250 lines.
2. The generated standalone visualizer HTML bundle functions identically with zero console errors.
3. 100% test pass rate on `tests/test_project_visualizer.py`.
4. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
