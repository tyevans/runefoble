---
id: '0224'
title: Project Visualizer AGY Launcher Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0004
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0224: Project Visualizer AGY Launcher Modular Decomposition

## Status
Proposed

## Summary
Decompose `tools/project_visualizer/static/js/agy_launcher.js` (353 lines, 70.6% of limit) into modular client submodules under `tools/project_visualizer/static/js/launcher/` (`modal.js`, `presets.js`, `poller.js`, `controller.js`), keeping all modules strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`tools/project_visualizer/static/js/agy_launcher.js` combines AGY prompt input handling, preset prompt templates, asynchronous polling timers, streaming execution logs, and modal DOM event dispatch in a single 353-line file. As new Antigravity slash commands, dynamic parameter inputs, and log formatters are added, this file will rapidly exceed the 500-line hard invariant unless modularized.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Modular client script structuring and encapsulation.

## Scope of Work
1. **Modal & Form Controls (`tools/project_visualizer/static/js/launcher/modal.js`)**:
   - Manage modal open/close lifecycle, backdrop events, keyboard escape listeners, and target entity badge rendering (< 90 lines).
2. **Prompt Presets & Templates (`tools/project_visualizer/static/js/launcher/presets.js`)**:
   - Manage preset definitions (`feature_process`, `test_generation`, `refactor_sweep`) and dynamic prompt interpolation (< 90 lines).
3. **Polling & Log Streaming (`tools/project_visualizer/static/js/launcher/poller.js`)**:
   - Manage polling intervals, offset tracking, streaming log chunks, and timer duration display (< 100 lines).
4. **Coordinator Facade (`tools/project_visualizer/static/js/agy_launcher.js`)**:
   - Wire module lifecycle events and expose clean `window.visualizer.openAgyModal` and helper APIs (< 80 lines).
5. **Verification**:
   - Verify modal opening, preset selection, execution triggers, and log streaming pass existing visualizer tests without regressions.

## Definition of Done
- `tools/project_visualizer/static/js/launcher/` created with all files strictly < 120 lines.
- `tools/project_visualizer/static/js/agy_launcher.js` coordinator reduced to < 80 lines.
- All visualizer tests pass via `uv run pytest tests/test_project_visualizer*.py`.
