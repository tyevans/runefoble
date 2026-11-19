---
id: '0878'
title: Campaign Rules Route Hosts the Homebrew Creator
status: Refined
created: 2026-11-18
dependencies: 
- TASK-0866
governing_adrs:
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0065
target_release: 0.9.0
---

# TASK-0878: Campaign Rules Route Hosts the Homebrew Creator

## Status
Refined

## Summary
Follow-up of TASK-0866. The App Shell route `#/rules` passes no campaign id, so the homebrew creator cannot submit a registration there. Homebrew rules belong to a campaign. Decision (orchestrator): the compendium view with the homebrew creator is a campaign route, `#/campaigns/:campaignId/rules`, like the other campaign views. `#/rules` stays a read-only SRD search without the creator.

## Documentation & Architecture Review
- `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`, `docs/how-to/balance-combat-encounters-and-query-compendium.md`, `docs/reference/microfrontend-architecture.md`.
- ADR-0013, ADR-0014.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)

## Detailed Specification & Implementation Plan
1. Add the route `#/campaigns/:campaignId/rules`. It mounts the compendium with the campaign id. The campaign navigation links to it.
2. `#/rules` mounts the SRD search only. It does not show the homebrew creator.
3. Add `e2e/features/rules_compendium_homebrew.feature`: a DM registers a homebrew monster through the form and sees it in the list; a player without permission sees the owner's refusal. The failure case uses a real refused request, not a `page.route` stub of our own service (TASK-0840 rule).
4. Check the two new Storybook stories for zero console errors.

## Frontdoor Test Plan
The Gherkin scenarios above, through the browser and public routes.

## INVEST Criteria Evaluation
Small. Testable in the Playwright harness.

## Definition of Done
1. Both scenarios pass in Playwright. 2. `make test-bdd` passes. 3. `make health-check` passes.
