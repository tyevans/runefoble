---
id: '0140'
title: Board State AoE Templates Geometry and Rendering Modular Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0125
- TASK-0132
governing_adrs:
- ADR-0013
governing_prds:
- PRD-0013
governing_stories:
- US-0056
target_release: 0.4.0
---

# TASK-0140: Board State AoE Templates Geometry and Rendering Modular Decomposition

## Status
Refined

## Summary
Decompose `services/board_state/ui/src/aoe_templates.ts` (411 lines, 82.2% of limit) into modular TypeScript files (`aoe_geometry.ts`, `aoe_canvas.ts`, `aoe_types.ts`, `aoe_templates.ts`) ensuring all UI modules remain < 200 lines per Hard Invariant 6.

## Problem Statement
`services/board_state/ui/src/aoe_templates.ts` consolidates mathematical geometry intersection algorithms (circle, cone, line, cube), 2D/WebGL canvas template rendering, rotational snapping (15-degree steps), and Lit lifecycle helpers across 411 lines. Adding further template shapes or projectile path traces risks breaching Hard Invariant 6 (< 500 lines).

## Governing Architecture & ADRs
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Clean separation of rendering logic, geometric intersection algorithms, and component controllers within `services/board_state/ui/src/`.

## Product & User Story References
- **Product Requirement**: [`prd-0013-immersive-and-intuitive-frontend-experience.md`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)
- **User Story**: [`us-0056-radial-token-action-menu-and-aoe-templates.md`](../../user_stories/accepted/us-0056-radial-token-action-menu-and-aoe-templates.md)

## Detailed Specification & Implementation Plan
1. **Types & Interfaces (`services/board_state/ui/src/aoe_types.ts`)**:
   - Extract template definitions, origin structures, shape enums, and color token types (< 80 lines).
2. **Geometric Calculations (`services/board_state/ui/src/aoe_geometry.ts`)**:
   - Extract intersection formulas for cones, spheres, rays, lines, and cubes (< 150 lines).
3. **Canvas Template Renderer (`services/board_state/ui/src/aoe_canvas.ts`)**:
   - Extract canvas stroke paths, dashed targeting outlines, and rotational handles (< 150 lines).
4. **Coordinator Facade (`services/board_state/ui/src/aoe_templates.ts`)**:
   - Re-export functions and maintain backward-compatible API for `<runefoble-tactical-board>` (< 100 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Internal refactoring within `board_state/ui/` with zero breaking changes to custom elements or parent views.
- **Negotiable (N)**: Split boundaries between geometry and canvas rendering can be refined.
- **Valuable (V)**: Safeguards against Hard Invariant 6 breach and improves code readability.
- **Estimable (E)**: Standard TypeScript module decomposition.
- **Small (S)**: Bounded strictly to `services/board_state/ui/src/`; all files < 160 lines.
- **Testable (T)**: Storybook stories and UI unit tests continue to pass cleanly.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Architecture**:
   - `aoe_types.ts`, `aoe_geometry.ts`, and `aoe_canvas.ts` created.
   - `aoe_templates.ts` reduced to < 100 lines facade.
2. **Quality Gates**:
   - All files strictly < 200 lines.
   - Passes `pnpm test` and `pnpm build`.
