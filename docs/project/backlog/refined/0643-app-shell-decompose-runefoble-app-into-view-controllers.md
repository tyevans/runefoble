---
id: '0643'
title: Decompose runefoble-app.ts Into Route View Controllers, Session Client, and Data Loader
status: Refined
created: 2026-11-17
dependencies:
- TASK-0640
- TASK-0642
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0066
- US-0068
target_release: 0.9.0
severity: high
source_audits:
- w2-app-shell.md
---

# TASK-0643: Decompose runefoble-app.ts Into Route View Controllers, Session Client, and Data Loader

## Status
Refined

## Summary
`frontend/src/runefoble-app.ts` owns routing, theme, auth sync, the WebSocket protocol, campaign CRUD, invites, roster, lobby, the live session, modals, and toasts. It renders every view in one `render()` tree. The file has 248 physical lines but 39,664 bytes. Line 172 has 1,286 characters. Split it into focused modules. Move the route-to-view mapping into a pure module that the app and the view-wiring test both import. Load each route's components lazily. This also removes the test-copy problem in F12.

## Problem Statement
- `frontend/src/runefoble-app.ts` has 248 lines, but 24 lines are longer than 300 characters (maximum 3,438). Line 172 has 1,286 characters, and line 168 has 580. The Hard Invariant 6 line count passes, but the file defeats single-responsibility modules.
- The WebSocket dispatch (lines ~104-125) sits inside the component. The campaign CRUD, invite, and roster handlers sit there too.
- `frontend/test/app-shell-views-wiring-audit.test.ts` (header comment, about line 17-19) defines "Pure frontdoor view resolver mirroring RunefobleApp.getActiveView()". The test can pass while the real method is wrong.
- The main bundle is 842 kB (`pnpm run build` warning). Every service UI package loads at startup because `runefoble-app.ts:7-12` imports them all.

## Documentation & Architecture Review
- ADR-0007: each route is a bounded view. Its controller calls the data loader and the session client. The shell does not own domain behaviour.
- ADR-0013: the shell composes UI packages. Lazy loading by route keeps that composition explicit. ADR-0013 runtime manifest loading is out of scope and is handled by a separate decision.
- `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md` describes the lifecycle. Update it with the new module names.
- Concurrent tasks touch `runefoble-app.ts`: TASK-0513 (proposed, town route), TASK-0468, TASK-0478, TASK-0481. Sequence this task before them, or rebase them onto the new modules.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0066-client-side-routing-navigation-and-breadcrumbs.md`](../../user_stories/accepted/us-0066-client-side-routing-navigation-and-breadcrumbs.md)
- [`us-0068-app-shell-view-audit-and-api-proxying.md`](../../user_stories/accepted/us-0068-app-shell-view-audit-and-api-proxying.md)

## Detailed Specification & Implementation Plan
1. `frontend/src/router/view-resolver.ts` (new, pure): maps a parsed route to a view id and parameters. No DOM. Used by `runefoble-app.ts` and by the wiring test.
2. `frontend/src/app/session-client.ts` (new): owns the session WebSocket. It exposes typed events and reconnect policy. It contains no rendering.
3. `frontend/src/app/data-loader.ts` (new): wraps `app-data-service.ts` calls per view and returns the typed result from TASK-0640.
4. `frontend/src/views/` (new): one controller per route (`campaign-dashboard-view.ts`, `campaign-hub-view.ts`, `lobby-view.ts`, `session-view.ts`, `character-view.ts`, `profile-view.ts`). Each view renders its own template. Keep each file under 200 physical lines with one statement per line.
5. `runefoble-app.ts` keeps only the shell: header, route outlet, toasts, and theme. Target: under 200 physical lines.
6. Lazy loading: each view imports its service UI package with dynamic `import()`. The main bundle must drop below 500 kB gzip-independent minified size (the current warning threshold).
7. Replace the test copy with an import of `view-resolver.ts` in `frontend/test/app-shell-views-wiring-audit.test.ts`.
8. Delete the duplicated logic. No compatibility re-export of the old methods.

## Frontdoor Blackbox Test Plan
- Playwright BDD (`e2e/features/app_shell_routes.feature`): for each route in the route matrix (dashboard, campaign hub tabs, lobby, session, character, profile), a signed-in user opens the URL directly. The scenario asserts the expected view's heading. Before the change the view resolver test passes against a copy; the BDD matrix is the real check.
- Unit test `frontend/test/view-resolver.test.ts`: every route in the matrix resolves to exactly one view.
- Bundle check: `pnpm run build` shows no chunk warning above 500 kB for the entry chunk.
- Before the split, the BDD scenarios for the lobby and session pass (regression baseline). They must still pass after the split.

## Definition of Done
1. `runefoble-app.ts` is under 200 physical lines. Each new view and client file is under 200 physical lines and has no line over 140 characters.
2. `view-resolver.ts` is the only route-to-view mapping. The wiring test imports it.
3. Route matrix BDD scenarios pass in all three browsers.
4. Entry chunk is under 500 kB, verified by the build output.
5. `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md` names the new modules.
6. Storybook stories for moved components build with zero console errors.
