---
id: '0516'
title: Settlement Town Haven Frontdoor Blackbox Test Suite
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0513
- TASK-0514
- TASK-0515
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0024
governing_stories:
- US-0072
- US-0073
- US-0074
- US-0075
- US-0076
target_release: 0.9.0
---

# TASK-0516: Settlement Town Haven Frontdoor Blackbox Test Suite

## Status
Proposed

## Summary
Implement end-to-end blackbox frontdoor test suites in `tests/test_blackbox_settlement_haven_frontdoor.py` and `frontend/test/settlement_haven.test.ts` validating settlement navigation, district scaling, establishment inventory queries, NPC worker assignments, and merchant/tavern minigame launches strictly through public HTTP APIs and custom element frontdoors per Hard Invariant 7 and ADR-0014.

## Problem Statement
Hard Invariant 7 mandates that all feature development must be verified by blackbox tests interacting strictly through public frontdoors (public HTTP routes, WebSockets, or standard domain events) rather than reaching into private internals. While isolated unit tests exist for backend settlement routers and aggregates, there is no end-to-end blackbox test suite exercising the complete client-to-gateway settlement workflow, including town route navigation, establishment shelf/vault retrieval, worker assignment event emissions, and mobile minigame triggers.

## Governing Architecture & ADRs
- **ADR-0001: Fine-Grained Authorization with SpiceDB Zanzibar Schema**: Testing permissions across town management endpoints.
- **ADR-0004: Lit Web Components and Storybook UI**: Verifying custom element rendering and event dispatch frontdoors.
- **ADR-0007: Domain-Driven Design Architecture**: Testing aggregates through domain event streams and public API gateways.
- **ADR-0014: Behavior-Driven Development (BDD) and Frontdoor Blackbox Testing Governance**: 100% blackbox testing through public interfaces.

## Product & User Story References
- [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
- [`us-0072-mobile-responsive-settlement-browser-and-town-builder.md`](../../user_stories/accepted/us-0072-mobile-responsive-settlement-browser-and-town-builder.md)
- [`us-0073-customizable-establishments-and-assignable-npc-workers.md`](../../user_stories/accepted/us-0073-customizable-establishments-and-assignable-npc-workers.md)
- [`us-0074-interactive-mobile-tavern-and-casino-minigames.md`](../../user_stories/accepted/us-0074-interactive-mobile-tavern-and-casino-minigames.md)
- [`us-0075-dynamic-merchant-haggling-with-dm-arbitration.md`](../../user_stories/accepted/us-0075-dynamic-merchant-haggling-with-dm-arbitration.md)
- [`us-0076-town-bulletin-board-civic-rumors-and-bounties.md`](../../user_stories/accepted/us-0076-town-bulletin-board-civic-rumors-and-bounties.md)

## Scope of Work
1. **Gateway & Domain Blackbox Test (`tests/test_blackbox_settlement_haven_frontdoor.py`)**:
   - Verify `GET /api/v1/campaigns/{id}/haven` returns settlement scale, districts, and prosperity score with valid JWT token.
   - Verify `POST /api/v1/campaigns/{id}/haven/establishments` creates a new establishment and emits `SettlementEstablishmentCreated` CloudEvent.
   - Verify `POST /api/v1/campaigns/{id}/haven/workers/assign` assigns an NPC worker to an establishment and validates SpiceDB permissions (DM/Owner permitted, Player restricted).
   - Verify `GET /api/v1/campaigns/{id}/haven/establishments/{est_id}/inventory` returns public shelf inventory vs. GM-restricted vault inventory.
2. **Frontend Component & Router Test (`frontend/test/settlement_haven.test.ts`)**:
   - Mount `<runefoble-app>` in simulated DOM, navigate to `#/campaigns/4/town`, and verify breadcrumbs and active tab state.
   - Assert `<runefoble-settlement-haven>` renders district chips and establishment cards.
   - Assert clicking an establishment card opens `<runefoble-establishment-drawer>`.
   - Assert tapping "Haggle with Merchant" emits `open-merchant-haggler` with valid payload.
3. **Verification**:
   - Run `uv run pytest tests/test_blackbox_settlement_haven_frontdoor.py`.
   - Run `pnpm test`.

## Definition of Done
1. `tests/test_blackbox_settlement_haven_frontdoor.py` passes 100% using `httpx.AsyncClient` frontdoor calls.
2. `frontend/test/settlement_haven.test.ts` passes 100% in Vitest/Playwright.
3. Zero direct database or private state manipulation in tests per Hard Invariant 7.
4. All test files remain strictly < 300 lines per Hard Invariant 6.
