---
id: '0180'
title: Board State Stories Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0004
- TASK-0084
- TASK-0125
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
---

# TASK-0180: Board State Stories Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/board_state/ui/src/runefoble-board.stories.ts` (379 lines, 75.8% of limit) by extracting sample token data, terrain configurations, and ghost preview states into a shared mock fixtures file `runefoble-board.stories.fixtures.ts`, keeping all story and fixture files strictly < 200 lines per Hard Invariant 6 and ADR-0013.

## Problem Statement
`services/board_state/ui/src/runefoble-board.stories.ts` contains 8 rich Storybook stories testing token kinematics, distance measurement, ghost previews, elevation cliffs, AoE spell cones/spheres, and tactile interaction. The inline definitions of sample tokens, terrain cells, spell templates, and preview handlers have caused the story file to reach 379 lines.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Design System**: Consistent visual styling and Storybook component cataloging.
- **ADR-0012: Theming and Color Tokens**: Bauhaus dark/light token verification across interactive stories.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Service-isolated Storybook stories.

## Scope of Work
1. **Mock Story Fixtures (`services/board_state/ui/src/runefoble-board.stories.fixtures.ts`)**:
   - Extract `sampleTokens`, `sampleTerrain`, `sampleAoETemplates`, and ghost preview mock states (< 150 lines).
2. **Stories Decomposition (`services/board_state/ui/src/runefoble-board.stories.ts`)**:
   - Import mock fixtures and retain clean story definitions (< 200 lines).
3. **Verification**:
   - Verify Storybook builds and stories render without console errors.

## Definition of Done
- `runefoble-board.stories.ts` reduced to < 200 lines.
- `runefoble-board.stories.fixtures.ts` created and strictly < 150 lines.
- Storybook stories load with zero errors.
- Passes ESLint / Prettier formatting checks.
