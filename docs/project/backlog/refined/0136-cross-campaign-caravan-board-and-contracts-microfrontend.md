---
id: '0136'
title: Cross-Campaign Caravan Trading & Frontier Bounty Board Microfrontend
status: Refined
created: 2026-09-26
dependencies:
- TASK-0008
- TASK-0010
- TASK-0127
- TASK-0129
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0013
governing_prds:
- PRD-0007
governing_stories:
- US-0058
target_release: 0.5.0
---

# TASK-0136: Cross-Campaign Caravan Trading & Frontier Bounty Board Microfrontend

## Status
Refined

## Summary
Build the `<runefoble-caravan-board>` microfrontend in `services/game_session/ui/src/` displaying active trade caravans, cargo manifests, escort contracts, payout bounties, transit route risk indicators, and real-time status notifications with Bauhaus design tokens and Storybook stories.

## Problem Statement
TASK-0129 establishes the backend event-sourced ledger for cross-campaign trade contracts and caravan manifests. Players and DMs need an interactive UI board (PRD-0007, US-0058) where groups can inspect available caravan escort jobs, fund merchant expeditions between regional hubs, review danger ratings, and claim bounties upon arrival.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object-Level Authorization**: Enforces role access for contract posting vs. accepting.
- **ADR-0006: Redis Streams Event Bus**: Subscribes to caravan progress updates and ambush alerts.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Self-contained component package vendored strictly inside `services/game_session/ui/src/` with Shadow DOM and Bauhaus design tokens.

## Product & User Story References
- **Product Requirement**: [`prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)
- **User Story**: [`us-0058-west-marches-shared-world-state-and-caravan-trade.md`](../../user_stories/accepted/us-0058-west-marches-shared-world-state-and-caravan-trade.md)

## Detailed Specification & Implementation Plan
1. **Caravan Board Microfrontend Component (`services/game_session/ui/src/runefoble-caravan-board.ts`)**:
   - `<runefoble-caravan-board>` Lit component displaying contracts list, route difficulty badges, and cargo value indicators.
   - One-click "Accept Escort Contract" button triggering SpiceDB-authorized REST call.
2. **Caravan Manifest Details Modal**:
   - Detailed inspection view showing cargo inventory, departure settlement, destination stronghold, and escort fee payout.
3. **Active Transit Route Status Pill**:
   - Visual progress bar showing remaining travel distance and ambush encounter alerts.
4. **Storybook Verification & Component Manifest**:
   - `runefoble-caravan-board.stories.ts` with stories simulating active caravan transit, ambush warnings, and contract payouts.
   - Served via `/game_session/ui/manifest`.

## INVEST Criteria Evaluation
- **Independent (I)**: Interacts with game_session through public REST endpoints without direct coupling to active session board state.
- **Negotiable (N)**: Contract card density and sorting options can be tuned.
- **Valuable (V)**: Bridges economic and collaborative links across disparate adventuring groups.
- **Estimable (E)**: Builds on existing contract aggregates in TASK-0129 and game session UI patterns.
- **Small (S)**: Bounded strictly to `services/game_session/ui/src/`; files < 350 lines.
- **Testable (T)**: Frontdoor tests verify UI manifest, event reaction, and contract actions.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Component Delivery**:
   - `<runefoble-caravan-board>` built and exported from `services/game_session/ui/src/`.
   - Manifest registered and served at `/ui/manifest`.
2. **Storybook Stories**:
   - `runefoble-caravan-board.stories.ts` rendering interactive contracts and transit states.
3. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_caravan_board_ui.py` validating component rendering and manifest registration.
4. **Quality Gates**:
   - Conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `pnpm test` and `pnpm build`.
