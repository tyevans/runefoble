---
id: '0303'
title: Bulletin Board Component Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0263
governing_adrs:
- ADR-0004
- ADR-0013
governing_prds:
- PRD-0024
governing_stories:
- US-0076
target_release: 0.8.0
---

# TASK-0303: Bulletin Board Component Modular Decomposition

## Status
Proposed

## Summary
Decompose `frontend/src/components/runefoble-bulletin-board.ts` (299 lines, 59.8% of limit) into modular subview rendering functions under `frontend/src/components/runefoble-bulletin-board.views.ts` or subviews, keeping the main component class strictly < 160 lines per Hard Invariant 6.

## Problem Statement
`frontend/src/components/runefoble-bulletin-board.ts` currently mixes Lit element state management, event dispatchers, audio coordination, filter calculations, and inline HTML template generation for tabs, notice cards, category badges, and cipher solution inputs within a single 299-line file. As civic notices, bounty contracts, and interactive guild seals are expanded, the file will rapidly approach the 500-line invariant limit.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Design System & Theme Engine**: Bauhaus token usage and clean Shadow DOM styles.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (subcomponents < 160 lines).

## Scope of Work
1. **Notice Card & Filter Subviews (`frontend/src/components/runefoble-bulletin-board.views.ts`)**:
   - Extract `renderBoardTabs`, `renderCategoryFilter`, and `renderNoticeCard` helper functions (< 140 lines).
2. **Main Component Refactoring (`frontend/src/components/runefoble-bulletin-board.ts`)**:
   - Focus component strictly on reactive state, properties, event handlers, and modal coordination (< 160 lines).
3. **Verification**:
   - Verify Storybook story rendering and existing blackbox tests for bulletin board interactions.

## Definition of Done
- `frontend/src/components/runefoble-bulletin-board.ts` reduced to < 160 lines.
- Extracted subview file strictly < 140 lines.
- 100% component API and event contract compatibility preserved.
- Storybook stories and settlement tests continue passing cleanly.
