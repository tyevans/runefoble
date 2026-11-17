---
id: '0613'
title: Asset Forge and Print Forge Components Call Forge API and Show Results
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0009
- PRD-0015
governing_stories:
- US-0038
- US-0049
target_release: 0.9.0
severity: high
source_audits:
- w2-asset-forge.md
---

# TASK-0613: Asset Forge and Print Forge Components Call Forge API and Show Results

## Status
Refined

## Summary
The Asset Forge and Print Forge Lit components only dispatch CustomEvents. No listener exists. No request is sent and no result is shown. This task makes each action call its forge route and show the returned asset. The header text is corrected so it matches the backend.

## Problem Statement
- `services/asset_forge/ui/src/runefoble-asset-forge.ts`: `handleForgeMap`, `handleForgeToken`, `handleProjectGeometry`, `handlePlaceToken` dispatch `forge-battlemap`, `forge-token`, `geometry-projected`, `token-placed`.
- `runefoble-print-forge.ts` (about lines 45-80): `handleExportPdf`, `handleExportStandees`, `handleExportStl` dispatch `export-print-pdf`, `export-standees`, `export-stl-token`.
- No listener exists in the repo. `lastForgedMap` and `lastForgedToken` are never set.
- The header "Procedural Diffusion Engine" is untrue. The backend has no diffusion model.

Source: `.audit/reports/w2-asset-forge.md` F2.

## Documentation & Architecture Review
- ADR-0013: components live in `services/asset_forge/ui/`. They reach the backend through the gateway (asset forge is not yet routed through gateway/api, see w2-asset-forge F3; that gateway route is owned by the gateway theme and is a dependency for end-to-end use).
- ADR-0014: Playwright BDD step must prove the request and the rendered result.
- `docs/how-to/forge-procedural-battlemaps-and-tokens.md` and `docs/how-to/forge-print-ready-maps-standees-and-stl-tokens.md`.

## Product & User Story References
- `docs/project/product/accepted/prd-0009-procedural-battlemap-and-token-asset-generation.md`
- `docs/project/product/accepted/prd-0015-generative-handouts-relic-inspector-and-printable-forge.md`
- `docs/project/user_stories/accepted/us-0038-generative-procedural-battlemaps-and-tokens.md`
- `docs/project/user_stories/accepted/us-0049-printable-tabletop-forge-and-stl-tokens.md`

## Detailed Specification & Implementation Plan
1. Each handler calls the matching forge route with `fetch` (or the shared API client used by other microfrontends). Use the gateway base path.
2. On success, set `lastForgedMap` or `lastForgedToken` from the response and render the asset preview.
3. On error, render the error from the response. No silent success.
4. Dispatch the existing CustomEvents only after the response is received, so board integration still works.
5. Correct the header text to "Procedural Battlemap Forge" or the name the backend supports.
6. Add a Storybook story with a mocked network boundary and a Playwright BDD step.

## Frontdoor Blackbox Test Plan
- Before fix: click "Forge map" with a prompt. No request appears on the forge route (test fails).
- After fix: the route receives the prompt. The preview shows the returned asset id.
- After fix: when the route returns 503, the component shows the error text.
- After fix: "Export PDF" calls the print route and offers the returned file.

## Definition of Done
1. No handler in these two components only dispatches an event without a request.
2. Storybook stories with zero console errors. Files under 500 lines.
3. Playwright BDD scenarios for both actions pass against the running stack.
4. Frontend builds pass (`pnpm run build`).
5. Docs corrected. `CHANGELOG.md` `[Unreleased]` entry added.
