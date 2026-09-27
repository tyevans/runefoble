---
id: '0125'
title: Radial Token Action Menu & Rotatable AoE Spell Templates
status: Complete
created: 2026-09-26
dependencies:
- TASK-0004
- TASK-0019
- TASK-0084
governing_adrs:
- ADR-0004
- ADR-0006
- ADR-0013
governing_prds:
- PRD-0013
governing_stories:
- US-0056
target_release: 0.4.0
pr_url: https://github.com/tyevans/runefoble/pull/131
---
# TASK-0125: Radial Token Action Menu & Rotatable AoE Spell Templates

## Status
Refined

## Summary
Build an interactive contextual radial dial for one-tap token actions (Dodge, Dash, Melee, Cast) and draggable, rotatable geometric Area of Effect (AoE) templates (cones, spheres, lines) with live token intersection highlighting on the board grid.

## Problem Statement
Triggering standard tactical combat actions currently requires navigating separate UI panels or relying purely on voice commands (PRD-0013, US-0056). Players like Marcus need tactile one-touch radial dials and rotatable spell cones (e.g. 15-foot Burning Hands) that compute affected targets in real time.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Strict Shadow DOM encapsulation and Bauhaus modernist action icons.
- **ADR-0006: Redis Streams Event Bus**: Event dispatch for `TokenActionExecuted` and `AoETemplatePlaced`.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: UI components vendored in `services/board_state/ui/src/`.

## Product & User Story References
- **Product Requirement**: [`prd-0013-immersive-and-intuitive-frontend-experience.md`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)
- **User Story**: [`us-0056-radial-token-action-menu-and-aoe-templates.md`](../../user_stories/accepted/us-0056-radial-token-action-menu-and-aoe-templates.md)

## Detailed Specification & Implementation Plan
1. **Contextual Radial Action Menu (`services/board_state/ui/src/radial_menu.ts`)**:
   - Circular radial dial blooming outwards on token click or tap (< 150ms animation).
   - Bauhaus geometric glyphs for Attack, Dash, Disengage, Dodge, and Cast.
2. **Rotatable AoE Geometry Engine (`services/board_state/ui/src/aoe_templates.ts`)**:
   - Mathematical calculations for 15ft/30ft cones (53.13 degree spread), spheres (radii: 10ft, 20ft), and lines (5ft x 30ft/60ft).
   - Rotational drag handle with angle snapping (15-degree increments).
3. **Target Intersection Highlighting**:
   - Computes square/hex grid cell coverage and highlights enclosed tokens with glowing targeting halos at 60fps.
4. **Frontdoor Blackbox Verification**:
   - Blackbox test suite validating radial action dispatch, AoE coordinate calculations, and target intersection results.

## INVEST Criteria Evaluation
- **Independent (I)**: Enhances board UI layer without altering underlying spatial grid aggregates.
- **Negotiable (N)**: Angular snapping thresholds and radial item counts can be adjusted.
- **Valuable (V)**: Drastically reduces friction for tactical combat execution.
- **Estimable (E)**: Follows tactile kinematics patterns established in TASK-0084.
- **Small (S)**: Scope strictly isolated to `services/board_state/ui/`; all files < 280 lines.
- **Testable (T)**: Frontdoor tests verify action events and intersection calculations.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Radial Action Menu Component**:
   - `<runefoble-radial-menu>` integrated into `<runefoble-board>` with touch and mouse support.
2. **Rotatable AoE Templates**:
   - Cones, spheres, and lines rotatable with live token intersection detection.
3. **Storybook Stories**:
   - Stories showcasing radial menu blooming and interactive cone/sphere template dragging.
4. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_radial_menu_and_aoe.py` verifying action dispatch and spatial intersection logic via public API endpoints.
5. **Quality Gates**:
   - Conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `pnpm run build` and `uv run pytest tests/test_blackbox_radial_menu_and_aoe.py`.
