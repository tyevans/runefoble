---
id: '0842'
title: E2E Harness Starts the Owner Services and the Chronicle Journey Runs End to End
status: Proposed
created: 2026-11-18
dependencies:
- TASK-0706
governing_adrs:
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0065
target_release: 0.9.0
---

# TASK-0842: E2E Harness Starts the Owner Services and the Chronicle Journey Runs End to End

## Status
Proposed

## Summary
Split from TASK-0706. `playwright.config.ts` starts only the gateway and the frontend. game_session, campaign_analytics and campaign_lore are not started, so journeys that need them cannot pass. After TASK-0706, add the chronicle timeline scenario: start a session, start combat, advance a turn, read the chronicle, all through the browser and public routes.

## Open Questions
1. Which services does the e2e harness start, and where do their settings (PostgreSQL, Redis, SpiceDB, embeddings) come from? The CI script should provide them, not the config file.
2. Does `e2e/features/session_chronicle_feed.feature` (TASK-0641) pass after TASK-0706?

3. Since TASK-0525, the global setup creates persona users in Zitadel on each run, and nothing deletes them. Add a global teardown that deletes the users that the run created, through the Zitadel management API.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
