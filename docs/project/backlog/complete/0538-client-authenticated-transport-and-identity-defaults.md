---
id: '0538'
title: Client Authenticated Transport for API Calls and WebSockets, and Removal of Fixture Identity
status: Complete
created: 2026-11-17
dependencies:
- TASK-0524
- TASK-0522
governing_adrs:
- ADR-0004
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0062
target_release: 0.9.0
---

# TASK-0538: Client Authenticated Transport for API Calls and WebSockets, and Removal of Fixture Identity

## Status
Complete

## Summary
After sign-in works (TASK-0524), every client call must send the Zitadel token. Today the App Shell and several microfrontends send `X-User-Id` or open WebSockets with no token. The App Shell also uses a fixed user (`user-valeros`) and decides privileges from role strings. Send the token on every call, use the subprotocol contract for WebSockets, and remove fixture identity.

## Problem Statement
- `frontend/src/runefoble-app.ts:30` and `:66` use `user-valeros` as the default user. Audit w2-app-shell F4.
- `frontend/src/runefoble-app.ts:67-68` and `frontend/src/components/plugins/plugin_registry.ts:108` decide DM capabilities from role strings. Audit w2-app-shell F6. Invariant 1 applies.
- `frontend/src/runefoble-app.ts:106` opens `/ws/session/...` with no token. `services/game_session/ui/src/runefoble-spectator-overlay.ts:73`, `services/voice_agent/ui/src/runefoble-mobile-companion.ts:115`, and `frontend/src/services/webrtc-voice.ts:52` open WebSockets with no token. Audit w3-authz F6 and F20.
- `services/game_session/ui` and `services/rules_compendium/ui` send `x-user-id` in client code (grep count).
- Storybook fixtures in these packages may carry mock tokens. Check them.

## Documentation & Architecture Review
- The contract is in TASK-0520 (WebSocket subprotocol) and TASK-0537 (identity reference). Use them.
- Microfrontend rule (ADR-0013): each package sends its own calls, but the token comes from one shared client helper in the App Shell or a shared library. Do not copy token logic into each package.
- Plugin slots (`mount-community-plugin-ui-extension-slots.md`) receive the token helper through the slot context, not through a global.

## Product & User Story References
- PRD-0023 (authenticated App Shell). US-0062 (signed-in state).

## Detailed Specification & Implementation Plan
1. **Shared token helper**: one module in the App Shell (`frontend/src/auth/`) exposes `authHeaders()` and `wsProtocols()`. It returns the current access token from the auth service (TASK-0524).
2. **API client**: `frontend/src/services/app-data-service.ts` and every other client `fetch` add `Authorization` through the helper. Remove every `X-User-Id` header.
3. **WebSockets**: each socket opens with protocols `["runefoble.v1", "runefoble.bearer." + token]`. Handle close code 1008 (handshake refused) by sending the user to sign-in.
4. **Fixture identity**: remove `user-valeros`, the placeholder character, and the invented stats in `runefoble-app.ts`. Derive the user from the ID token. Show an empty state where data is missing. The fixed campaign and session ids are a fake-implementation item (audit w2-app-shell F4) that this task may leave to that theme; record the choice.
5. **Role strings**: remove the `['dm','admin','owner']` checks. Show privileged controls only when the gateway returns a permission flag for the campaign. Until the authorization theme exposes that flag, show no privileged controls. Record the dependency in the PR.
6. **Storybook**: replace mock tokens in stories with a stub token helper that is never sent to a real service. Zero console errors.
7. Grep check: `grep -rn "X-User-Id\|x-user-id\|user-valeros\|mocksignature" frontend services/*/ui --include=*.ts`.

## Frontdoor Blackbox Test Plan
Playwright BDD through the App Shell (TASK-0525 runner).
- Before: API calls carry `X-User-Id`. The board WebSocket opens without a token. Fixture user `Valeros` appears with no sign-in.
- After:
  - Every API call in the network log has an `Authorization: Bearer` header and no `X-User-Id`.
  - A WebSocket opened by the App Shell carries the subprotocol token and is accepted.
  - With no session, the App Shell shows the signed-out state and no fixture user.
  - A plain user sees no privileged controls.

## Definition of Done
1. Grep in step 7 returns no matches.
2. `pnpm run build` and Storybook build pass with zero console errors in the stories.
3. Playwright BDD journeys (TASK-0525) pass.
4. The microfrontend how-to (`authoring-service-microfrontends.md`) describes the shared token helper.
5. No file exceeds 500 lines. Split `runefoble-app.ts` changes if the file would exceed the limit (it is already a god component, audit w2-app-shell F5).

## Audit Provenance

- Severity: high
- Source audits: `w2-app-shell.md`, `w3-authz-coverage.md`, `w2-voice-agent.md`

## Orchestrator Addenda (2026-11-17, refactor-r1)

- TASK-0538 (Problem Statement, append): "The microfrontends `character_sheet`, `rules_compendium` (rules lookup, homebrew creator) read `localStorage['runefoble-access-token']`, which the shell never writes (`frontend/src/auth/auth-service.ts:259` uses `rf_auth_session`). TASK-0757 replaces these reads with the shell auth context contract. Do not add a shared storage key here."
- TASK-0538 (Plan, append): "Caravan calls (`services/game_session/ui/src/caravan/caravan_api.ts:24,53`) send `x-user-id` and no token. TASK-0759 moves them to the shared transport. Remove the `x-user-id` header there, not here."
