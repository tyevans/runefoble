---
id: '0645'
title: App Shell Composes the Asset Forge Microfrontend on a Deep-Linkable Route
status: Complete
created: 2026-11-17
dependencies:
- TASK-0595
governing_adrs:
- ADR-0004
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0009
- PRD-0013
- PRD-0015
- PRD-0023
governing_stories:
- US-0038
- US-0049
- US-0055
target_release: 0.9.0
---

# TASK-0645: App Shell Composes the Asset Forge Microfrontend on a Deep-Linkable Route

## Status
Complete

Audit 2026-11-17: proposed TASK-0348 replaced by TASK-0595, which owns the gateway assets proxy that this task needs. TASK-0348 is partly superseded.

## Summary
`services/asset_forge/ui` is built, has stories, and is in the workspace. The App Shell never imports or mounts it. `frontend/package.json` lists 10 `@runefoble/*-ui` packages without `@runefoble/asset-forge-ui`. No route, tab, or element in `frontend/src` uses `runefoble-asset-forge` or `runefoble-print-forge`. Add the dependency and mount the forge on a deep-linkable route, so a user can forge a battlemap or token from the App Shell. Its backend calls go through the gateway (TASK-0348).

## Problem Statement
- `w1-gates-frontend.md` F1: `frontend/package.json` lists 10 UI packages. `@runefoble/asset-forge-ui` is absent. `grep -rn 'asset-forge\|runefoble-asset-forge' frontend/src frontend/test frontend/tests` returns nothing.
- `w2-asset-forge.md` F1 and the composition note (around line 152): the App Shell has no reference to the package. Composition needs the workspace dependency, a route or view, and the element mounted with its properties.
- The forge components dispatch calls that do not reach a backend through the gateway (`w2-asset-forge.md` F3): `handleForgeMap`, `handleForgeToken`, `handleExportPdf`, `handleExportStandees`, `handleExportStl`. TASK-0348 adds the gateway assets router.

## Documentation & Architecture Review
- `docs/how-to/forge-procedural-battlemaps-and-tokens.md` and `docs/how-to/forge-print-ready-maps-standees-and-stl-tokens.md` describe the forge flows. Update them with the route and the real outputs.
- ADR-0013: the App Shell imports `@runefoble/asset-forge-ui` by its package root only. It does not deep-import.
- ADR-0004: the forge stays in its Storybook stories. Composition does not replace them.
- ADR-0013 section 6 runtime manifest loading is out of scope here (see the decision item in the synthesis index).

## Product & User Story References
- [`prd-0009-procedural-battlemap-and-token-asset-generation.md`](../../product/accepted/prd-0009-procedural-battlemap-and-token-asset-generation.md)
- [`prd-0015-generative-handouts-relic-inspector-and-printable-forge.md`](../../product/accepted/prd-0015-generative-handouts-relic-inspector-and-printable-forge.md)
- [`us-0038-generative-procedural-battlemaps-and-tokens.md`](../../user_stories/accepted/us-0038-generative-procedural-battlemaps-and-tokens.md)
- [`us-0049-printable-tabletop-forge-and-stl-tokens.md`](../../user_stories/accepted/us-0049-printable-tabletop-forge-and-stl-tokens.md)

## Detailed Specification & Implementation Plan
1. Add `@runefoble/asset-forge-ui` to `frontend/package.json` and the pnpm workspace lock. Use the same version scheme as the other UI packages.
2. Add a campaign tab or route `#/campaigns/:campaignId/forge` (the route name must be decided at refinement and recorded in `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`).
3. Mount `<runefoble-asset-forge>` and `<runefoble-print-forge>` on that route. Pass `campaign-id`, the current user's permissions from TASK-0644 (`permissions.manage` gates the save and export controls), and the base URL for the gateway.
4. Add the route to `frontend/src/router/view-resolver.ts` (TASK-0643). If TASK-0643 has not landed, add it to the existing route table and note the conflict.
5. Each forge action shows the asset returned by the gateway. The header text must match the backend result. No action shows a fabricated result.
6. Lazy-load the forge view (dynamic import), so the entry chunk does not grow.

## Frontdoor Blackbox Test Plan
Playwright BDD (`e2e/features/asset_forge_composition.feature`):
- Scenario: A DM opens the forge tab and sees the forge element.
  - Given a campaign created through the dashboard and the DM signed in
  - When the DM opens the forge tab
  - Then the page contains a `runefoble-asset-forge` element with a visible "Forge battlemap" control.
- Scenario: Forging a battlemap shows the returned asset.
  - When the DM submits a prompt "crypt with three pillars"
  - Then the preview shows an image URL served by the gateway and the page shows the returned asset id.
- Before the change the tab does not exist and the scenario FAILS. After the change it PASSES.
- Pytest (`tests/test_blackbox_asset_forge_gateway_route.py`) confirms the gateway forge routes return the asset id that the UI shows.

## Definition of Done
1. `@runefoble/asset-forge-ui` is in `frontend/package.json` and the lockfile. `pnpm install --frozen-lockfile` passes.
2. The forge route renders `runefoble-asset-forge` and `runefoble-print-forge` in the browser. Verified by the BDD scenarios.
3. Storybook stories for the forge components still build with zero console errors.
4. Docs in `docs/how-to/forge-procedural-battlemaps-and-tokens.md` and `docs/how-to/forge-print-ready-maps-standees-and-stl-tokens.md` name the route.
5. `pnpm run build` and `make build` pass. Changelog entry under `[Unreleased]`.
6. Files changed stay under 500 lines.

## Audit Provenance

- Severity: medium
- Source audits: `w1-gates-frontend.md`, `w2-asset-forge.md`
