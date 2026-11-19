---
id: '0909'
title: "The E2E Harness Runs Green on Kind: Fault Injection, Locators and Ports"
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0005
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: frontend
target_release: 0.9.0
---

# TASK-0909: The E2E Harness Runs Green on Kind: Fault Injection, Locators and Ports

## Status

Refined.

## Summary

Several e2e failures come from the harness, not the product: the lore fault script controls a local process instead of the Kind service, two steps assert text that is wrong or too broad, the caravan 503 scenarios fake our own gateway with `page.route`, and two vitest browser runs at the same time block each other on a fixed port.

## Problem Statement

- `scripts/e2e_lore_fault.py` starts and stops a local uvicorn on :8006 (triage group E). The suite runs on Kind since TASK-0525.
- Smoke "signs in and reaches dashboard" expects the user id in the user menu; after TASK-0890 the menu shows the username (group I).
- `app_shell_routing_state.feature` "empty state": `getByText('Adventurer')` also matches "Manage your adventurers" (group J).
- `e2e/steps/caravan_board_steps.ts:28`: `page.route` fakes a 503 of game_session (ADR-0014).
- Gate run 2026-11-19: `vitest run` in the frontend suite stopped after 240 s while another worktree ran vitest; alone it takes 3 s.

## Documentation & Architecture Review

- `.audit/reports/e2e-triage-1.md` gives the evidence (gateway log lines, error-context files).
- ADR-0014: user flows are verified through Playwright without backdoors or `page.route` fakes of our own services. ADR-0015: no invented values and no success shown after an error.

## Product & User Story References

None beyond the scenarios named below.

## Detailed Specification & Implementation Plan

1. `make e2e-lore-down/up`: scale `deployment/campaign-lore` in `kind-runefoble-local` to 0 and back to 1, and wait until the gateway reports it unreachable, then healthy. Update `docs/reference/e2e-harness.md`.
2. Smoke step: expect the persona's Zitadel username.
3. Empty-state step: use an exact or role-based locator.
4. Caravan 503: inject the fault at the infrastructure level (scale the game-session deployment, as in step 1) or delete the scenario if a frontdoor fault cannot be made; record the choice.
5. Vitest browser config: use a free port (`browser.api.port` 0 or `strictPort: false`) so parallel worktrees do not block.

## Frontdoor Blackbox Test Plan

- `make test-bdd` passes. A unit test of the lore fault script against a fake `kubectl` on PATH.
- Playwright on Kind (orchestrator): smoke, app_shell_routing_state, campaign_analytics_and_codex `@lore-down`, caravan_board.

## Definition of Done

- The plan is done and the tests pass. The orchestrator runs the named Playwright scenarios on Kind. Docs and CHANGELOG updated.

## Audit Provenance

- Severity: medium
- Source audits: .audit/reports/e2e-triage-1.md
