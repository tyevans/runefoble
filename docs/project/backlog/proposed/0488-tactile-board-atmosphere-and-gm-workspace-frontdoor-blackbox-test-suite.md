---
id: '0488'
title: Tactile Board Atmosphere and GM Workspace Frontdoor Blackbox Test Suite
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0485
- TASK-0486
- TASK-0487
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0012
- ADR-0014
governing_prds:
- PRD-0013
governing_stories:
- US-0013
- US-0043
- US-0056
target_release: 0.9.0
---

# TASK-0488: Tactile Board Atmosphere and GM Workspace Frontdoor Blackbox Test Suite

## Status
Proposed

## Summary
Implement a comprehensive frontdoor blackbox test suite (`tests/test_blackbox_board_atmosphere_and_gm_workspace.py` and `frontend/test/board-atmosphere-and-gm-workspace.test.ts`) verifying that dynamic weather overlays, torchlight flicker, spoken ghost preview interactive fine-tuning, and GM God-Mode fog paintbrush and monster spawner operate correctly through public Web Component DOM APIs and Gateway WebSocket endpoints without private internals manipulation.

## Problem Statement
With the introduction of dynamic weather canvas layers, interactive ghost preview adjustment controls, and GM God-Mode workspace tools in `<runefoble-board>`, automated regression tests must verify that public custom events, SpiceDB Zanzibar authorization barriers, and DOM state updates conform strictly to blackbox testing standards (Rule 7 and ADR-0014) to prevent regressions in live tabletop sessions.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Verify non-GM users cannot activate GM God-Mode paintbrush or spawn tokens.
- **ADR-0004: Lit Web Components and Storybook UI**: Component testing through standard DOM events and public properties.
- **ADR-0014: Behavior-Driven Development (BDD) and Frontdoor Blackbox Testing Governance**: Test exclusively through public interfaces and custom events.

## Product & User Story References
- [`prd-0013-immersive-and-intuitive-frontend-experience.md`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)
- [`us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md`](../../user_stories/accepted/us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md)

## Scope of Work
1. **Frontend Blackbox Test Suite (`frontend/test/board-atmosphere-and-gm-workspace.test.ts`)**:
   - Verify setting `weather="rain"`, `weather="embers"`, and `weather="mist"` initializes canvas overlays.
   - Verify dragging ghost preview updates coordinates and triggers `@ghost-preview-adjusted`.
   - Verify clicking Confirm badge dispatches `@ghost-preview-confirmed` with final destination payload.
   - Verify clicking Dismiss badge cancels preview and dispatches `@ghost-preview-cancelled`.
   - Verify GM God-Mode toolbar is visible only when `isGm=true`.
   - Verify fog paintbrush drag dispatches `@shroud-cells-updated` with modified coordinate list.
   - Verify monster palette drag-and-drop onto board emits `@token-spawn-requested`.
2. **Backend Gateway Blackbox Test Suite (`tests/test_blackbox_board_atmosphere_and_gm_workspace.py`)**:
   - Verify WebSocket broadcast of `shroud_updated` and `token_spawned` events across session participants.
   - Verify SpiceDB 403 Forbidden rejection when non-GM attempts to broadcast GM paintbrush mutations.

## Definition of Done
1. Frontend test suite authored and passes 100% assertions via `npm test`.
2. Backend blackbox test suite passes 100% assertions via `uv run pytest tests/test_blackbox_board_atmosphere_and_gm_workspace.py`.
3. Zero direct state backdoors or private property access utilized in test fixtures.
4. Code passes all linting (`npm run lint`, `uv run ruff check`).
