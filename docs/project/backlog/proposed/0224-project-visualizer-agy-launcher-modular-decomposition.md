---
id: '0224'
title: Project Visualizer AGY Launcher Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0004
- ADR-0013
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0224: Project Visualizer AGY Launcher Modular Decomposition

## Status
Proposed

## Summary
Decompose `tools/project_visualizer/static/js/agy_launcher` (354 lines, 70.8% of limit) into modular JavaScript submodules (`agy_modal.js`, `agy_presets.js`, `agy_runner.js`), ensuring all client visualizer modules remain strictly < 150 lines per Hard Invariant 6.

## Problem Statement
The AGY launcher script bundles modal dialog lifecycle management, preset selection and command generation, background execution polling timers, terminal output streaming, and error handling in a single script of 354 lines. As additional CLI flags, multi-agent presets, and workspace targets are added, this script will quickly breach the 500-line invariant unless decomposed.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular tool structure.
- **ADR-0004: Bauhaus Design System**: Modernist visual styling and modal state invariants.
- **ADR-0013: Modular Decomposition**: Single-responsibility client scripts < 150 lines.

## Scope of Work
1. **Modal Controller (`tools/project_visualizer/static/js/agy_modal.js`)**:
   - Extract modal open/close transitions, keyboard shortcuts, and entity badge population (< 100 lines).
2. **Presets & Command Builder (`tools/project_visualizer/static/js/agy_presets.js`)**:
   - Extract prompt preset templates, flag builders, and command preview updates (< 110 lines).
3. **Execution & Stream Runner (`tools/project_visualizer/static/js/agy_runner.js`)**:
   - Extract job launch POST handler, log offset streaming polling, status badges, and elapsed timer (< 130 lines).
4. **Script Aggregation (`static/js/agy_launcher`)**:
   - Maintain backwards-compatible global namespace exports on `window.visualizer` (< 40 lines).
5. **Verification**:
   - Verify all Visualizer tests pass via `uv run pytest tests/test_project_visualizer_agy.py tests/test_visualizer_parser.py`.

## Definition of Done
- Launcher entrypoint reduced to < 50 lines.
- Extracted submodules created and strictly < 150 lines each.
- Visualizer HTML bundle loads and launches AGY jobs with zero console errors.
- Visualizer test suites pass cleanly.
