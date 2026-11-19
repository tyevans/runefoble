---
id: '0840'
title: E2E Forge Failure Through a Frontdoor and the Lobby Negative Scenario
status: Complete
created: 2026-11-18
dependencies: 
- TASK-0649
governing_adrs:
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0016
- US-0063
- US-0065
target_release: 0.9.0
---

# TASK-0840: E2E Forge Failure Through a Frontdoor and the Lobby Negative Scenario

## Status
Complete

## Summary
Follow-up of TASK-0649. Two items stay open after the E2E backdoors were removed.
1. The asset forge 503 scenario used a fault double for our own forge service. That is not an allowed boundary double. Make the scenario cause a real failure through a frontdoor (for example a real invalid request), or stop the owner service in the harness.
2. Add the negative lobby scenario: a player who is not the DM does not see the Launch control.

Both need a Playwright run (`make test-e2e`) to verify.

## Documentation & Architecture Review
- `docs/reference/e2e-harness.md`, `docs/how-to/test-user-flows-with-playwright-bdd.md`.
- ADR-0014 (BDD through frontdoors).

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- User stories US-0016, US-0063, US-0065.

## Detailed Specification & Implementation Plan
1. Rewrite the forge failure scenario as a real failure through a public route.
2. Add the lobby scenario and its step. The step fails when the control is missing or shown by mistake.
3. Run the two scenarios with `make test-e2e ARGS="--grep ..."`.

Addendum (2026-11-18, TASK-0870): 3. Add the lobby readiness scenarios: readiness counts players only (an owner or DM is never counted), and a session with no players shows "No players have joined". 4. Add the campaign members scenario: management controls show only when the server's can-manage flag is set.

## Frontdoor Test Plan
The two Gherkin scenarios above, through the browser only.

## INVEST Criteria Evaluation
Small: two scenarios. Testable in the Playwright harness.

## Definition of Done
1. Both scenarios pass in Playwright. 2. `make test-bdd` passes. 3. `make health-check` passes.
