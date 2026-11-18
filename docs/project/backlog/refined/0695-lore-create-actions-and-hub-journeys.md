---
id: '0695'
title: Lore Create Actions in the Codex and Atlas, and Hub Journeys Through the Gateway
status: Refined
created: 2026-11-17
dependencies:
- TASK-0587
- TASK-0646
governing_adrs:
- ADR-0014
- ADR-0013
governing_prds:
- PRD-0007
- PRD-0012
governing_stories:
- US-0050
- US-0040
target_release: 0.9.0
severity: medium
source_audits:
- work/0646.md
---

# TASK-0695: Lore Create Actions in the Codex and Atlas, and Hub Journeys Through the Gateway

## Status
Refined. Discovered in round 2 audit of report 0646. TASK-0646 is complete. Its remaining items had no owner.

## Summary
The Codex and Lore tab emits `pin-create-requested`, but the App Shell does not handle it, and the gateway has no POST proxy for atlas pins. The codex and chronicle e2e journeys were never written. This task wires the create action through the gateway and adds the two journeys.

## Problem Statement
- The App Shell Codex and Lore tab emits `pin-create-requested`. No handler in `frontend/src` creates a pin or refreshes the atlas.
- The gateway POST proxies for atlas pins and codex entries are covered by TASK-0587 (scope). This task depends on them.
- `e2e/features/campaign_analytics_and_codex.feature` does not exist. The second BDD scenario ("Star-Eater Gate" appears in the codex) cannot run.

## Documentation & Architecture Review
- ADR-0014: journeys are Playwright BDD through public frontdoors. No injected state.
- ADR-0013: the Codex and Lore component stays in its owning package. The App Shell only handles the event.
- `docs/how-to/interact-with-campaign-atlas-and-codex.md`: use the gateway base URL in examples (TASK-0587 and TASK-0662).

## Product & User Story References
- US-0050 (campaign atlas and codex). US-0040 (chronicle timeline).

## Detailed Specification & Implementation Plan
1. Handle `pin-create-requested` in the App Shell. Call the gateway POST atlas pin route. On success, refresh the atlas. On failure, show the error.
2. Add the feature file `e2e/features/campaign_analytics_and_codex.feature` with two scenarios: a pin created in the atlas appears in the codex, and a combat event appears in the chronicle timeline.
3. Setup through public routes only: campaign creation, session, combat start (TASK-0686 when merged), and combat event route.
4. Add the step definitions with precise selectors (TASK-0650 rules).

## Frontdoor Blackbox Test Plan
- Playwright BDD: sign in, open the campaign atlas, create a pin, assert it is listed in the atlas and in the codex.
- Playwright BDD: run a combat through public session routes, open the chronicle, assert the event row and the damage total from the public analytics route.
- Gateway down (test double returns 503): the pin form shows an error and no pin appears.

## Definition of Done
- Both scenarios pass in Playwright BDD with no `page.route` or direct DOM edits.
- `pnpm run build` passes. No console errors.
