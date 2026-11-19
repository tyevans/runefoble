---
id: '0866'
title: Homebrew Creator Reports Only Real Registrations
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0013
- ADR-0015
governing_prds:
- PRD-0008
governing_stories:
- US-0052
target_bc: rules_compendium
target_release: 0.9.0
---
# TASK-0866: Homebrew Creator Reports Only Real Registrations

## Status
Refined.

## Summary
When the API base URL is empty, the homebrew form says "validated", invents a `rule_id`, and dispatches `homebrew-created`. Nothing is saved. Remove this path. Send the write through the shared JSON request, and show the server detail when it fails.

## Problem Statement
- `services/rules_compendium/ui/src/runefoble-homebrew-creator.ts:84-101`: the `else` branch sets `hbMessage` to "validated", builds `rule_id: 'mock-hb-' + Date.now()`, and dispatches `homebrew-created`. The rule is not stored. This is a substitute payload (ADR-0015 b).
- `runefoble-homebrew-creator.ts:67-75`: a raw `fetch` with a manual `Content-Type` header and `res.json().catch(...)`. This repeats the shared request path in `libs/runefoble_ui/src/http.ts`.
- A search of `frontend/src` and `services/*/ui/src` found no listener for `homebrew-created`. Removing the fake event does not break a known consumer.

## Documentation & Architecture Review
- ADR-0015 (b): no substitute payloads, no hidden failures.
- ADR-0013: the owning UI package sends its own requests through `@runefoble/ui-core`.
- ADR-0004: each visible state has a Storybook story with zero console errors.
- `docs/how-to/balance-combat-encounters-and-query-compendium.md` describes homebrew registration. Check it after the change.

## Product & User Story References
- PRD-0008 (rules compendium and homebrew rules). US-0052 (homebrew spell, monster and rule authoring).

## Detailed Specification & Implementation Plan
1. Delete the `else` branch at lines 84-101. Make a missing `apiBaseUrl` a visible configuration error (`hbError`), and do not submit.
2. Replace the raw `fetch` with `postJson` from `@runefoble/ui-core`. Keep the `AuthConsumerController` headers. Map `HttpError` to `hbError` using the server `detail`.
3. Dispatch `homebrew-created` only after a 2xx response. The event detail is the server body.
4. Add Storybook stories for the success state and the server-error state. Both must show zero console errors.

## Frontdoor Blackbox Test Plan
- Playwright BDD (ADR-0014). Use a live loopback upstream for the rules service, as described in `docs/how-to/test-cross-service-calls-with-live-upstreams.md`.
- Scenario: a signed-in DM submits a homebrew rule. The upstream returns 503 with a detail. The form shows the detail. No `homebrew-created` event is observed.
- Scenario: the upstream returns the created rule. The form shows the registered title, and the event is observed once.
- Assert the request carries `Authorization: Bearer`. Assert no `x-user-id` header.

## Definition of Done
- No `mock-` identifier and no fabricated event in `services/rules_compendium/ui/src`.
- No raw `fetch` in `runefoble-homebrew-creator.ts`.
- Storybook stories for both states; zero console errors.
- Playwright BDD scenarios pass without backdoor state changes.
- `make lint`, `pnpm run build`, and `make health-check` pass. No file over 500 lines.
- No backward-compatibility shim (DoR 9).

## Audit Provenance
- Severity: high
- Source audits: `frontend-ui`
