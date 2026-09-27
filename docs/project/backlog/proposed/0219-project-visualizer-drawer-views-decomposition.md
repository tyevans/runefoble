---
id: '0219'
title: Project Visualizer Drawer Subviews Modular Decomposition
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

# TASK-0219: Project Visualizer Drawer Subviews Modular Decomposition

## Status
Proposed

## Summary
Decompose `tools/project_visualizer/static/js/drawer.js` (358 lines, 71.6% of limit) into modular card view components under `tools/project_visualizer/static/js/drawer/` (`task_card.js`, `adr_card.js`, `prd_card.js`, `persona_card.js`, `controller.js`), keeping all modules strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`tools/project_visualizer/static/js/drawer.js` handles slide-out drawer DOM creation, markdown rendering triggers, metadata badge formatting, and AGY launch button injection for tasks, ADRs, PRDs, and personas in a single 358-line file. As new entity types (such as service maps and test telemetry) are rendered in the inspector drawer, this file will approach the 500-line limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook Design System**: Clean modular component and view structuring.
- **ADR-0012: Bauhaus Theme and Design Tokens**: Geometric card styles and typography tokens.

## Scope of Work
1. **Task Card Subview (`tools/project_visualizer/static/js/drawer/task_card.js`)**:
   - Render task status badges, dependencies list, acceptance criteria, and AGY action controls (< 100 lines).
2. **ADR Card Subview (`tools/project_visualizer/static/js/drawer/adr_card.js`)**:
   - Render ADR context, decision bullets, consequences, and linked tasks (< 90 lines).
3. **PRD & Story Subview (`tools/project_visualizer/static/js/drawer/prd_card.js`)**:
   - Render product requirements, user stories, and acceptance matrices (< 90 lines).
4. **Drawer Controller (`tools/project_visualizer/static/js/drawer.js`)**:
   - Lightweight coordinator handling open/close transitions and routing to subviews (< 80 lines).
5. **Verification**:
   - Verify drawer opening, markdown rendering, and AGY button functionality via visualizer manual test and automated test suite.

## Definition of Done
- `tools/project_visualizer/static/js/drawer/` components decomposed with all files strictly < 120 lines.
- Zero files in drawer directory exceed 150 lines.
- All visualizer tests pass via `uv run pytest tests/test_project_visualizer*.py`.
