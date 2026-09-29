---
id: '0454'
title: West Marches Multi-Party Gateway and App Shell Blackbox Test Suite
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0451
- TASK-0452
- TASK-0453
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0018
- PRD-0023
governing_stories:
- US-0058
- US-0050
- US-0067
target_release: 0.9.0
---

# TASK-0454: West Marches Multi-Party Gateway and App Shell Blackbox Test Suite

## Status
Proposed

## Summary
Implement a comprehensive end-to-end blackbox test suite (`tests/test_blackbox_west_marches_gateway.py` in Python and `frontend/test/west-marches-app-shell.test.ts` in TypeScript) validating the full West Marches multi-party integration through public frontdoors: Gateway REST proxies, SpiceDB Zanzibar universe isolation, cross-campaign discovery pin synchronization, communal stronghold upgrade thresholds, and caravan trade contract escrow fulfillment.

## Problem Statement
While individual service aggregates (`WestMarchesAtlasAggregate`, `SharedWorldAggregate`, `CaravanAggregate`) have unit and service-level test coverage, there is no end-to-end blackbox test suite exercising the integrated frontdoor pathways through the Gateway API and App Shell. We need an integration test suite confirming that multi-party universe isolation is enforced by SpiceDB Zanzibar, that discoveries by Party A appear immediately on the shared atlas for Party B, and that caravan trade contracts correctly transfer items and gold without duplicates or race conditions.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Verify that campaigns outside the West Marches universe receive 403 Forbidden on universe state mutations.
- **ADR-0006: Event-Driven Architecture with Redis Streams**: Verify event dispatching for frontier discoveries, caravan status changes, and stronghold boons.
- **ADR-0013: Frontend Microfrontend Architecture**: Verify that App Shell loads microfrontends and handles custom events seamlessly.
- **ADR-0014: Behavior-Driven Development (BDD) with Playwright**: Align integration test fixtures with user story requirements.

## Product & User Story References
- [`prd-0018-west-marches-shared-world-state-and-cross-campaign-trade.md`](../../product/accepted/prd-0018-west-marches-shared-world-state-and-cross-campaign-trade.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0058-west-marches-shared-world-state-and-caravan-trade.md`](../../user_stories/accepted/us-0058-west-marches-shared-world-state-and-caravan-trade.md)

## Scope of Work
1. **Gateway Blackbox Test Suite (`tests/test_blackbox_west_marches_gateway.py`)**:
   - Test discovery creation and retrieval across multiple campaign tokens linked to the same universe (< 120 lines).
   - Test communal stronghold upgrade funding threshold calculation and boon event generation (< 100 lines).
   - Test caravan contract posting, claiming by a different party, fulfillment, and escrow payout (< 120 lines).
   - Test Zanzibar authorization rejections (403 Forbidden) when an unlinked campaign attempts to access universe data (< 80 lines).
2. **Frontend Blackbox Integration Suite (`frontend/test/west-marches-app-shell.test.ts`)**:
   - Test navigation to `#/campaigns/:campaignId/frontier` and `#/campaigns/:campaignId/caravans` (< 100 lines).
   - Test `<runefoble-west-marches-atlas>` mounting, pin submission, and stronghold upgrade dispatch (< 100 lines).
   - Test `<runefoble-caravan-board>` mounting, caravan dispatch, and contract claim handling (< 100 lines).
3. **Verification**:
   - Run `uv run pytest tests/test_blackbox_west_marches_gateway.py`.
   - Run `pnpm test` / `npm test` in `frontend/`.

## Definition of Done
1. Python gateway test suite passes 100% of assertions.
2. Frontend integration test suite passes 100% of assertions.
3. Frontdoor interactions strictly adhere to blackbox testing rules (Rule 7).
4. All new test files adhere to Hard Invariant 6 (< 500 lines).
