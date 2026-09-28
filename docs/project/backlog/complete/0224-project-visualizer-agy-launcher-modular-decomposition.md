---
id: '0224'
title: Project Visualizer AGY Launcher Modular Decomposition
status: Complete
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds: []
governing_stories: []
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/320
---
# TASK-0224: Project Visualizer AGY Launcher Modular Decomposition

## Status
Refined

## Summary
Decompose `tools/project_visualizer/static/js/agy_launcher.js` (353 lines, 70.6% of limit) into modular JavaScript submodules under `tools/project_visualizer/static/js/agy/` (`agy_modal.js`, `agy_presets.js`, `agy_runner.js`), ensuring all client visualizer modules remain strictly < 140 lines per Hard Invariant 6.

## Problem Statement
`tools/project_visualizer/static/js/agy_launcher.js` bundles modal dialog lifecycle management, preset selection and command generation, background execution polling timers, terminal output streaming, and error handling in a single script of 353 lines. As additional CLI flags, multi-agent presets, and workspace targets are added, this script will quickly breach the 500-line invariant unless decomposed.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/visualize-project-content.md`: Project visualizer AGY launcher execution and modal controls.
  - `docs/reference/design-tokens-and-themes.md`: Bauhaus typography and modal dialog styling.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular tool structure.
  - **ADR-0004: Lit Web Components and Storybook UI**: Bauhaus design token usage and high-contrast styling invariants.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: Modernist modal styling and high-contrast terminal panels.
  - **ADR-0013: Modular Decomposition**: Single-responsibility client scripts strictly < 150 lines.

## Product & User Story References
- Technical debt refactoring supporting internal developer tooling:
  - [`docs/how-to/visualize-project-content.md`](../../../how-to/visualize-project-content.md)
  - [`docs/how-to/curate-backlog-and-roadmap.md`](../../../how-to/curate-backlog-and-roadmap.md)

## Detailed Specification & Implementation Plan
1. **Modal Controller (`tools/project_visualizer/static/js/agy/agy_modal.js`)**:
   - Extract modal open/close transitions, keyboard shortcuts, and entity badge population (< 100 lines).
2. **Presets & Command Builder (`tools/project_visualizer/static/js/agy/agy_presets.js`)**:
   - Extract prompt preset templates, flag builders, and command preview updates (< 110 lines).
3. **Execution & Stream Runner (`tools/project_visualizer/static/js/agy/agy_runner.js`)**:
   - Extract job launch POST handler, log offset streaming polling, status badges, and elapsed timer (< 130 lines).
4. **Script Aggregation Facade (`tools/project_visualizer/static/js/agy_launcher.js`)**:
   - Maintain backwards-compatible global namespace exports on `window.visualizer` (< 40 lines).
5. **HTML Template Update (`tools/project_visualizer/template.py`)**:
   - Include modular sub-scripts in script loading tag or bundle.
6. **Verification**:
   - Verify all Visualizer tests pass via `uv run pytest tests/test_project_visualizer_agy.py tests/test_visualizer_parser.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal script decomposition without modifying the visualizer server API.
- **Negotiable (N)**: Submodule naming can be adjusted to match visualizer conventions.
- **Valuable (V)**: Protects visualizer frontend scripts from breaching the 500-line invariant limit.
- **Estimable (E)**: Clean separation of DOM modal handling, command generation, and log streaming.
- **Small (S)**: Submodules will each be under 130 lines.
- **Testable (T)**: Pytest visualizer tests verify launcher generation and server responses.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tools/project_visualizer/static/js/agy_launcher.js` reduced to < 50 lines.
2. Extracted submodules under `tools/project_visualizer/static/js/agy/` strictly < 140 lines each.
3. Visualizer HTML bundle loads and launches AGY jobs with zero console errors.
4. Passes `uv run pytest tests/test_project_visualizer_agy.py tests/test_visualizer_parser.py`.
