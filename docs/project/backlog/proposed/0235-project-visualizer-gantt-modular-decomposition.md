---
id: '0235'
title: Project Visualizer Gantt Chart Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0217
governing_adrs:
- ADR-0004
- ADR-0007
governing_prds:
- PRD-0013
governing_stories:
- US-0043
target_release: 0.8.0
---

# TASK-0235: Project Visualizer Gantt Chart Modular Decomposition

## Status
Proposed

## Summary
Decompose `tools/project_visualizer/static/js/gantt.js` (319 lines, 63.8% of limit) into modular client scripts under `tools/project_visualizer/static/js/gantt/` (`scales.js`, `bars.js`, `milestones.js`, `tooltips.js`), keeping all modules strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`tools/project_visualizer/static/js/gantt.js` combines timeline time-scale calculations, task dependency bar SVG generation, milestone marker rendering, and hover tooltip interactions in a single 319-line file. As new milestones and release timeline views are added to the visualizer, this script approaches the refactoring warning limit and will breach 500 lines without modular separation.

## Governing Architecture & ADRs
- **ADR-0004: Frontend Visualizer & Lit Component Architecture**: Clean separation of rendering logic, state management, and visual components.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation of visual timeline models and SVG rendering routines.

## Scope of Work
1. **Time Scales & Coordinates (`tools/project_visualizer/static/js/gantt/scales.js`)**:
   - Extract date math, day-to-pixel coordinate scales, and timeline axis rendering (< 90 lines).
2. **Task Bars & Link Lines (`tools/project_visualizer/static/js/gantt/bars.js`)**:
   - Extract task bar SVG generation, progress fill styling, and dependency link bezier curves (< 100 lines).
3. **Milestone Markers & Tooltips (`tools/project_visualizer/static/js/gantt/milestones.js`)**:
   - Extract milestone diamond pins, completion flags, and hover tooltip event handlers (< 90 lines).
4. **Gantt Aggregator (`tools/project_visualizer/static/js/gantt.js`)**:
   - Re-export the unified `renderGanttChart` facade coordinating the modular sub-renderers (< 50 lines).
5. **Verification**:
   - Verify project visualizer builds and passes standalone HTML bundle verification.

## Definition of Done
- `tools/project_visualizer/static/js/gantt.js` reduced to < 60 lines.
- Extracted submodules under `gantt/` strictly < 120 lines each.
- Standalone HTML export and browser rendering tests pass cleanly.
