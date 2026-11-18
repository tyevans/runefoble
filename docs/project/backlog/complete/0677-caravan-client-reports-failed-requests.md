---
id: '0677'
title: Caravan Client Shows Failed Dispatch and Fulfilment as Errors
status: Complete
created: 2026-11-17
dependencies:
- TASK-0451
governing_adrs:
- ADR-0004
- ADR-0013
- ADR-0014
- ADR-0015
governing_prds:
- PRD-0018
governing_stories:
- US-0058
target_release: 0.9.0
---

# TASK-0677: Caravan Client Shows Failed Dispatch and Fulfilment as Errors

## Status
Complete

## Summary
`services/game_session/ui/src/caravan/caravan_api.ts` catches every fetch error and then sets the contract to `in_transit` or `fulfilled`. The player sees success for a request the server rejected.

## Problem Statement
- `caravan_api.ts` lines 55-57: `catch { /* offline fallback */ }`, then `contract.status = 'in_transit'`.
- `caravan_api.ts` lines 78-80: the same pattern, then `contract.status = 'fulfilled'`.
- ADR-0015: a failed upstream call returns an error. The client must show it.

## Documentation & Architecture Review
- ADR-0013: the microfrontend owns this client. Keep the fix in `services/game_session/ui/`.
- ADR-0004: Lit components with Storybook stories. Add a story for the error state.
- ADR-0014: the scenario runs in Playwright BDD through the public UI.

## Product & User Story References
- PRD-0018 and US-0058: caravan dispatch and fulfilment must match the server result.

## Detailed Specification & Implementation Plan
1. Change `dispatchCaravan` and `apiFulfillContract` to return a result type (`ok` or `error` with a message). Remove the catch-and-continue blocks.
2. Update `dispatch_modal.ts` and `contract_card.ts` callers. On error, leave the contract status unchanged and show an error message in the component.
3. Add a Storybook story for the error state.
4. Add a Playwright BDD scenario: the caravan dispatch request returns 503 through the gateway double. The contract stays `pending` and the error message is visible.

## Frontdoor Blackbox Test Plan
- Playwright BDD: with the caravan route returning 503 at the network boundary, click dispatch. The card does not show "in transit". The error text is visible.
- Same for fulfil.
- Success path: the same steps with 200 show "in transit" and "fulfilled".

## Definition of Done
- Tests above pass. `grep -n "offline fallback" services/game_session/ui/src/caravan/caravan_api.ts` returns nothing.
- Storybook builds with zero console errors. `pnpm run build` passes for the package.
- Changed files under 500 lines.

## Audit Provenance

- Severity: medium
- Source audits: `work/0613.md`
