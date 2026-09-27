---
id: 0180
title: Board State Stories Modular Decomposition
status: Complete
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0013
governing_stories:
- US-0043
- US-0056
target_release: 0.7.0
pr_url: https://github.com/tyevans/runefoble/pull/236
---
# TASK-0180: Board State Stories Modular Decomposition

## Status
Refined

## Summary
Decompose `services/board_state/ui/src/runefoble-board.stories.ts` (378 lines, 75.6% of limit) by extracting sample token data, terrain configurations, and ghost preview states into a shared mock fixtures file `runefoble-board.stories.fixtures.ts`, keeping all story and fixture files strictly < 200 lines per Hard Invariant 6 and ADR-0013.

## Problem Statement
`services/board_state/ui/src/runefoble-board.stories.ts` contains rich Storybook stories testing token kinematics, distance measurement, ghost previews, elevation cliffs, AoE spell cones/spheres, and tactile interaction. The inline definitions of sample tokens, terrain cells, spell templates, and preview handlers have caused the story file to reach 378 lines. As additional miniature physics and obstacle rebound stories are added, this file will breach the 500-line limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Lit + Vite Microfrontends with Storybook**: Isolated component cataloging and UI story verification.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast Bauhaus dark/light token verification across interactive stories.
- **ADR-0013: Modular Microfrontend Decomposition**: Component subviews and fixtures kept strictly < 200 lines per module.

## Detailed Specification & Implementation Plan
1. **Mock Story Fixtures (`services/board_state/ui/src/runefoble-board.stories.fixtures.ts`)**:
   - Extract `sampleTokens`, `sampleTerrain`, `sampleAoETemplates`, and ghost preview mock states into a dedicated fixtures module (< 160 lines).
2. **Stories Decomposition (`services/board_state/ui/src/runefoble-board.stories.ts`)**:
   - Import mock fixtures and retain clean story definitions (< 200 lines).
3. **Verification**:
   - Verify Storybook builds and stories render without console errors.
   - Run blackbox tests in `tests/test_blackbox_radial_menu_and_aoe.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Story fixture extraction with zero runtime production dependencies.
- **Negotiable (N)**: Fixture data structures can be shared across other board story files if needed.
- **Valuable (V)**: Prevents story file from exceeding Hard Invariant 6 (500 lines) and improves Storybook test maintenance.
- **Estimable (E)**: Pure refactoring and fixture extraction.
- **Small (S)**: Bounded strictly to `services/board_state/ui/src/runefoble-board.stories*`; all files < 200 lines.
- **Testable (T)**: Frontdoor verification via Storybook rendering and board blackbox test suites.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `runefoble-board.stories.ts` reduced to strictly < 200 lines.
   - `runefoble-board.stories.fixtures.ts` created and strictly < 160 lines.
2. **Frontdoor Test Verification**:
   - Storybook visual demonstration renders with zero console errors.
   - Passes `uv run pytest tests/test_blackbox_radial_menu_and_aoe.py`.
3. **Quality Gates**:
   - Passes `uv run ruff check .` and `uv run ruff format --check .`.
