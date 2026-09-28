---
id: '0219'
title: Project Visualizer Drawer Subviews Modular Decomposition
status: Refined
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
Refined

## Summary
Decompose `tools/project_visualizer/static/js/drawer.js` (358 lines, 71.6% of limit) into modular card view components under `tools/project_visualizer/static/js/drawer/` (`task_card.js`, `adr_card.js`, `prd_card.js`, `persona_card.js`, `controller.js`), keeping all modules strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`tools/project_visualizer/static/js/drawer.js` handles slide-out drawer DOM creation, markdown rendering triggers, metadata badge formatting, and AGY launch button injection for tasks, ADRs, PRDs, and personas in a single 358-line file. As new entity types (such as service maps and test telemetry) are rendered in the inspector drawer, this file will approach the 500-line limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook Design System**: Clean modular component and view structuring.
- **ADR-0012: Bauhaus Theme and Design Tokens**: Geometric card styles and typography tokens.

## Detailed Specification & Implementation Plan
1. **Task Card Subview (`tools/project_visualizer/static/js/drawer/task_card.js`)**:
   - Render task status badges, dependencies list, acceptance criteria, and AGY action controls (< 100 lines).
2. **ADR Card Subview (`tools/project_visualizer/static/js/drawer/adr_card.js`)**:
   - Render ADR context, decision bullets, consequences, and linked tasks (< 90 lines).
3. **PRD & Story Subview (`tools/project_visualizer/static/js/drawer/prd_card.js`)**:
   - Render product requirements, user stories, and acceptance matrices (< 90 lines).
4. **Persona Card Subview (`tools/project_visualizer/static/js/drawer/persona_card.js`)**:
   - Render persona attributes, goals, pain points, and associated user stories (< 80 lines).
5. **Drawer Controller (`tools/project_visualizer/static/js/drawer.js`)**:
   - Lightweight coordinator handling open/close transitions and routing entity rendering to the subviews (< 80 lines).
6. **Verification**:
   - Verify drawer opening, markdown rendering, and AGY button functionality via automated visualizer tests.

## INVEST Criteria Evaluation
- **Independent (I)**: Changes strictly localized to the visualizer drawer view scripts.
- **Negotiable (N)**: Submodules map directly to individual domain entity types displayed in the drawer.
- **Valuable (V)**: Decouples template rendering from drawer state transitions and prevents rule 6 breaches.
- **Estimable (E)**: Pure extraction of rendering template literals into sub-components.
- **Small (S)**: Scope restricted to partitioning `drawer.js` into modular card renderers (< 120 lines each).
- **Testable (T)**: Frontdoor verification via visualizer test suites.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `tools/project_visualizer/static/js/drawer/` components decomposed with all files strictly < 120 lines.
   - Zero files in drawer directory exceed 150 lines.
2. **Frontdoor Verification**:
   - Drawer slide-out animation, card rendering, and copy/action buttons function accurately.
   - All visualizer tests pass via `uv run pytest tests/test_project_visualizer*.py` and `tests/test_visualizer*.py`.
3. **Quality Gates**:
   - Syntax and lint checks pass cleanly.
