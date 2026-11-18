---
id: '0706'
title: App Shell Receives the Session Id and the Chronicle Journey Runs End to End
status: Refined
created: 2026-11-17
dependencies:
- TASK-0695
governing_adrs:
- ADR-0013
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---
# TASK-0706: App Shell Receives the Session Id and the Chronicle Journey Runs End to End

## Status
Refined. Blocked part of TASK-0695.

## Summary
The App Shell never receives the game_session aggregate id, so it cannot start combat, and the chronicle timeline journey cannot run. The e2e web server also starts only the gateway and the frontend.

## Problem Statement
- Combat start needs the session aggregate id. The lobby launch response or session read does not give it to the App Shell.
- `playwright.config.ts` starts only the gateway and the frontend.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0013, ADR-0014.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Return the session id from the launch response (or a public session read) and pass it to the session view.
2. Start the services the journey needs (game_session, campaign_analytics, campaign_lore) in the e2e web server.
3. Write the chronicle timeline Gherkin scenario and steps.

## Frontdoor Blackbox Test Plan
- Playwright BDD: launch a session, start combat, take a turn, open the chronicle, see the turn entry.

## Definition of Done
- The chronicle scenario passes in headless Playwright.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `work/0695.md`
