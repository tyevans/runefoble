---
id: '0685'
title: App Shell Mounts Print Forge, Caravan Board, and Board DM Controls
status: Refined
created: 2026-11-17
dependencies:
- TASK-0645
- TASK-0582
- TASK-0595
governing_adrs:
- ADR-0004
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0015
- PRD-0018
- PRD-0023
governing_stories:
- US-0049
- US-0058
- US-0001
target_release: 0.9.0
---

# TASK-0685: App Shell Mounts Print Forge, Caravan Board, and Board DM Controls

## Status
Refined. Discovered in round 2 audit of implementation reports 0613, 0677 and 0563. TASK-0645 covers the asset forge only.

## Summary
Three owned microfrontends are built and tested in Storybook, but the App Shell never places them. The e2e features for print forge, caravan board and board DM controls are blocked for this reason. This task composes them into the App Shell, following the pattern TASK-0645 sets for the asset forge.

## Problem Statement
- `frontend/src` has no route or view that places `<runefoble-print-forge>` (`services/asset_forge/ui`). TASK-0645 covers only `<runefoble-asset-forge>`.
- `frontend/src` has no route for the caravan board (`<runefoble-caravan-board>`, `services/game_session/ui`). `e2e/features/caravan_board.feature` assumes `#/caravans`, which does not exist.
- `<runefoble-map-switcher>` is exported (`frontend/src/index.ts:22`) but no App Shell view places it. The DM board components get no `boardId` or `campaignId`. Board cell selection that sets `targetX` and `targetY` does not exist.
- `e2e/features/asset_forge.feature` and the board features assume `#/forge`. That route does not exist.
- PROPOSED TASK-0453 also covers caravan integration. Merge 0453 into this task or close it before refinement is pulled.

## Documentation & Architecture Review
- ADR-0013: the App Shell composes components. It does not own their logic. Each component stays in its owning `services/<bc>/ui/` package.
- ADR-0004: Lit components with Shadow DOM. No new styling in the App Shell.
- `docs/how-to/forge-print-ready-maps-standees-and-stl-tokens.md`, `docs/how-to/interact-with-tactile-board-and-ghost-previews.md`: update the route names.

## Product & User Story References
- PRD-0015 and US-0049 (printable forge). PRD-0018 and US-0058 (caravans). US-0001 (spoken board manipulation).

## Detailed Specification & Implementation Plan
1. Add one App Shell view per component, using the route pattern from TASK-0645. Pick the hash routes for the print forge and the caravan board. Update the step definitions and feature files to match the chosen routes. Do not keep `#/forge` as an alias.
2. Add the workspace dependencies in `frontend/package.json` for `@runefoble/asset-forge-ui` (print forge export), `@runefoble/game-session-ui` (caravan board) and `@runefoble/board-state-ui` (map switcher and DM controls), if not already present.
3. Pass `boardId` and `campaignId` from the App Shell to the DM controls. Add board cell selection that sets `targetX` and `targetY` in the move dispatch.
4. Do not add gateway routes here. Gateway proxies come from TASK-0595 (forge) and TASK-0582 (boards).
5. Remove `@blocked` from the caravan, print forge and board scenarios once they pass.

## Frontdoor Blackbox Test Plan
- Playwright BDD (TASK-0525 sign-in): open the print forge from the App Shell, export a PDF, and check the download through the public forge route.
- Open the caravan board for a campaign with one accepted and one in-transit contract (setup through public shared-world routes). Assert the visible contract states.
- Open a board, select a cell, and move a token. Assert the token position from the public board route.
- No injected state. No `page.route` fault injection for these journeys.

## Definition of Done
- The App Shell places all three components. No component reads fixture data.
- `pnpm run build` and the Storybook build pass with zero console errors.
- The three feature groups run without `@blocked` in Playwright BDD.
- Documentation names the new routes.

## Audit Provenance

- Severity: high
- Source audits: `work/0613.md`, `work/0677.md`, `work/0563.md`
