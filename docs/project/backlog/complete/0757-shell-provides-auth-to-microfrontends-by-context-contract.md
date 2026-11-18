---
id: '0757'
title: The App Shell Provides Auth to Microfrontends Through a Documented Context Contract
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0013
- ADR-0004
- ADR-0015
governing_prds:
- PRD-0023
governing_stories:
- US-0062
- US-0069
target_bc: frontend
target_release: 0.9.0
---
# TASK-0757: The App Shell Provides Auth to Microfrontends Through a Documented Context Contract

## Status
Complete

## Summary
Three microfrontends read the token from `localStorage['runefoble-access-token']`. The App Shell never writes that key. It stores the session under `rf_auth_session`. So these components send no token, and two of them hide the failure. Define one auth context contract. The shell answers it. The three components use it. No shared storage key remains.

## Problem Statement
- `services/character_sheet/ui/src/runefoble-character-sheet.ts:60` reads `runefoble-access-token`. The `catch {}` at line 65 drops every error. `connectedCallback` (line 54) also drops the promise error with `.catch(() => {})`.
- `services/rules_compendium/ui/src/runefoble-rules-lookup.ts:58` reads the same key. The `catch` at lines 74-76 only holds the comment "Local fallback or demo state". This is a fallback that ADR-0015 (b) forbids.
- `services/rules_compendium/ui/src/runefoble-homebrew-creator.ts:63` reads the same key.
- `frontend/src/auth/auth-service.ts:259` writes `STORAGE_KEY` (`rf_auth_session`) and no code writes `runefoble-access-token`.
- `frontend/src/auth/auth-service.ts:250` already dispatches `rf-auth-changed`, but no microfrontend listens to it.

## Documentation & Architecture Review
- ADR-0013 point 1: the shell is the event and communication multiplexer. Point 3: microfrontends declare their interface through DOM attributes, properties and CustomEvents. Negative consequences: no direct internal state references. A shared storage key breaks this. The contract below keeps it.
- ADR-0013 point 4 lists the pnpm packages. Add a small shared package `libs/runefoble_ui` (`@runefoble/ui-core`) to `pnpm-workspace.yaml`, and record the addition in ADR-0013 (amend the point 4 list). TASK-0758 reuses this package.
- ADR-0015 (b): no silent fallbacks.
- `docs/reference/microfrontend-architecture.md` and `docs/how-to/authoring-service-microfrontends.md` must describe the contract.
- Overlap: TASK-0538 sends the token from the shell and the WebSocket paths. It does not name this key mismatch. See the addendum in the index.

## Product & User Story References
- PRD-0023 (App Shell and Campaign Hub). US-0062 (sign-in). US-0069 (character sheet inspector).
- Gherkin scenario to add to US-0069 (setup through the frontdoor sign-in fixture, ADR-0014):
  - Given I signed in through Zitadel and opened a campaign with a character
  - When I open the character sheet
  - Then the request carries an `Authorization: Bearer` header and the HP renders.

## Detailed Specification & Implementation Plan
1. Contract: the W3C Context Community Protocol. A microfrontend dispatches a composed, bubbling `context-request` event for the context key `runefoble-auth`. The shell (a provider on the root element) answers with `{ getAccessToken(): Promise<string | null> }` and re-notifies subscribers on `rf-auth-changed`. Use `@lit/context` in `libs/runefoble_ui` as `authContext`, `AuthConsumerController`.
2. The shell adapts `authService.getAccessToken()` (`frontend/src/auth/auth-service.ts:139`) into the provider. It exports no new storage key.
3. Replace the three `localStorage` reads with the controller. Delete the empty `catch` blocks. A failed call sets an `error` state and renders it. No demo data.
4. With no provider (Storybook alone), the controller returns `null`, the request goes out without a token, and the 401 is shown as an error. Stories mock the provider.
5. Remove the string `runefoble-access-token` from the repository.

## Frontdoor Blackbox Test Plan
- Playwright BDD: sign in through the Zitadel fixture. Open a character sheet and a rules search. Assert the `Authorization: Bearer` header on each request and the rendered HP.
- Upstream returns 503 (live loopback upstream, see `test-cross-service-calls-with-live-upstreams.md`). Assert that each component shows an error message and no demo data.
- Storybook: each of the three components has a story with a mocked provider and a story with no provider. Zero console errors.

## Definition of Done
- No `runefoble-access-token` string remains. No component reads another app's `localStorage` key.
- The contract is documented in `docs/reference/microfrontend-architecture.md` and the how-to guide. ADR-0013 lists the new package.
- `pnpm run build`, `uv run pytest`, `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high
- Source audits: `frontend-ui`
