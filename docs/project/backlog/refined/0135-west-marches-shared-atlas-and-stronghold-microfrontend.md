---
id: '0135'
title: West Marches Shared World Atlas Pins & Communal Stronghold Dashboard Microfrontend
status: Refined
created: 2026-09-26
dependencies:
- TASK-0008
- TASK-0010
- TASK-0106
- TASK-0127
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0013
governing_prds:
- PRD-0007
- PRD-0014
governing_stories:
- US-0050
- US-0058
target_release: 0.5.0
---

# TASK-0135: West Marches Shared World Atlas Pins & Communal Stronghold Dashboard Microfrontend

## Status
Refined

## Summary
Build the `<runefoble-west-marches-atlas>` microfrontend in `services/campaign_lore/ui/src/` displaying multi-party persistent frontier map pins, communal tavern rumor bulletin boards, shared stronghold facility levels, and cross-campaign expedition logs with SpiceDB Zanzibar role filtering and Storybook stories.

## Problem Statement
TASK-0127 creates the backend persistence for multi-party West Marches shared states. Adventuring parties need a shared tactical cartography interface (PRD-0007, PRD-0014, US-0058) where Party A's dungeon discovery automatically appears as an expedition pin on Party B's regional map, along with shared stronghold upgrades and communal notice boards.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object-Level Authorization**: Enforces viewer permissions on shared pins vs. party-private notes.
- **ADR-0006: Redis Streams Event Bus**: Real-time WebSocket event ingestion for `CrossCampaignDiscoveryShared` and `StrongholdFacilityUpgraded`.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Self-contained component package vendored strictly inside `services/campaign_lore/ui/src/` with Shadow DOM and Bauhaus design tokens.

## Product & User Story References
- **Product Requirements**:
  - [`prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)
  - [`prd-0014-downtime-crafting-and-stronghold-engine.md`](../../product/accepted/prd-0014-downtime-crafting-and-stronghold-engine.md)
- **User Stories**:
  - [`us-0050-collaborative-campaign-atlas-and-living-codex.md`](../../user_stories/accepted/us-0050-collaborative-campaign-atlas-and-living-codex.md)
  - [`us-0058-west-marches-shared-world-state-and-caravan-trade.md`](../../user_stories/accepted/us-0058-west-marches-shared-world-state-and-caravan-trade.md)

## Detailed Specification & Implementation Plan
1. **Shared Atlas Microfrontend Component (`services/campaign_lore/ui/src/runefoble-west-marches-atlas.ts`)**:
   - `<runefoble-west-marches-atlas>` Lit component rendering regional frontier map, layered milestone pins, and party attribution badges.
   - Interactive pin popover revealing discovering party name, date discovered, danger rating, and expedition notes.
2. **Communal Stronghold Dashboard**:
   - Facility status cards (e.g. Alchemical Workshop Lv 2, Watchtower Lv 3) showing shared rest boons and defensive buffers.
3. **Tavern Rumor Bulletin Tab**:
   - Real-time notice board listing rumors, discovered dungeons, and unclaimed bounties.
4. **Storybook Verification & Component Manifest**:
   - `runefoble-west-marches-atlas.stories.ts` with mock discovery pins and multi-party views.
   - Served via `/lore/ui/manifest`.

## INVEST Criteria Evaluation
- **Independent (I)**: Consumes public REST endpoints `/api/v1/campaigns/{id}/west-marches` and `/lore/` without modifying core session loop.
- **Negotiable (N)**: Map layout coordinates and pin styling can be customized.
- **Valuable (V)**: Delivers core visual identity and social collaboration for multi-party West Marches campaigns.
- **Estimable (E)**: Extends existing campaign atlas component from TASK-0106.
- **Small (S)**: Bounded to `services/campaign_lore/ui/src/`; files < 350 lines.
- **Testable (T)**: Frontdoor tests verify UI manifest, event handling, and pin rendering.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Component Delivery**:
   - `<runefoble-west-marches-atlas>` component built and exported from `services/campaign_lore/ui/src/`.
   - Manifest registered and served at `/ui/manifest`.
2. **Storybook Stories**:
   - `runefoble-west-marches-atlas.stories.ts` rendering interactive frontier pins and stronghold status.
3. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_west_marches_ui.py` validating component mounting and manifest endpoint.
4. **Quality Gates**:
   - Conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `pnpm test` and `pnpm build`.
