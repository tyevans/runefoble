---
id: '0106'
title: Collaborative Campaign World Atlas & Living Party Codex
status: Complete
created: 2026-09-26
dependencies:
- TASK-0008
- TASK-0016
- TASK-0047
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0006
- ADR-0011
- ADR-0013
governing_prds:
- PRD-0015
governing_stories:
- US-0050
target_release: 0.4.0
pr_url: https://github.com/tyevans/runefoble/pull/128
---
# TASK-0106: Collaborative Campaign World Atlas & Living Party Codex

## Status
Refined

## Summary
Build an interactive multi-layered world atlas engine and collaborative party codex with chronological timeline milestone pins, territory boundaries, player secret notes, and automated cross-referencing against the `campaign_lore` redstring graph.

## Problem Statement
Campaign lore and geography are currently disconnected from active session play (PRD-0015, US-0050). Chroniclers like Rowan need a dynamic map where party milestones are pinned to the timeline, and secret lore entries can be shared or kept private with Zanzibar permissions.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object-Level Authorization**: Enforces private vs shared party codex visibility (`relation: reader`, `relation: editor`).
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Domain logic housed in `services/campaign_lore/`.
- **ADR-0006: Redis Streams Event Bus**: Event dispatch for `AtlasPinCreated`, `AtlasLayerToggled`, and `CodexEntryPublished`.
- **ADR-0011: eventsource-py Core Event Sourcing**: Event-sourced `AtlasAggregate` and `CodexAggregate` tracking geographical markers and journal revisions.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Lit Web Component `<runefoble-campaign-atlas>` vendored in `services/campaign_lore/ui/src/`.

## Product & User Story References
- **Product Requirement**: [`prd-0015-generative-handouts-relic-inspector-and-printable-forge.md`](../../product/accepted/prd-0015-generative-handouts-relic-inspector-and-printable-forge.md)
- **User Story**: [`us-0050-collaborative-campaign-atlas-and-living-codex.md`](../../user_stories/accepted/us-0050-collaborative-campaign-atlas-and-living-codex.md)

## Detailed Specification & Implementation Plan
1. **Interactive Multi-Layered Map Engine (`services/campaign_lore/src/campaign_lore/atlas.py`)**:
   - Deep-zoom coordinate projection supporting continental, regional, and municipal layers.
   - Territory polygon boundaries with ownership metadata and contested boundary highlights.
2. **Timeline Milestone Pins & Lore Links**:
   - Geotagged pins linking historical campaign events, session recaps, and redstring knowledge graph entities.
   - Chronological era filtering to view geopolitical borders at different session dates.
3. **Collaborative Party Codex & Secret Notes**:
   - Event-sourced codex entries with markdown body and automatic entity hyperlinking to NPC and location graphs.
   - Privacy status (`private`, `party_shared`, `public`) enforced via SpiceDB Zanzibar client checks.
4. **Microfrontend Component (`services/campaign_lore/ui/src/runefoble-campaign-atlas.ts`)**:
   - High-performance canvas pan/zoom interface with Bauhaus pin markers, filter drawer, and codex sidebar.
5. **Frontdoor Blackbox Verification**:
   - Blackbox test suite exercising public HTTP routes (`/api/v1/campaigns/{id}/atlas`, `/api/v1/campaigns/{id}/codex`), event stream projections, and Zanzibar auth checks.

## INVEST Criteria Evaluation
- **Independent (I)**: Builds on campaign lore redstring index without coupling to combat board mechanics.
- **Negotiable (N)**: Map layer zoom levels and pin icon styles can be adjusted.
- **Valuable (V)**: Transforms campaign worldbuilding into a shared, living geography for players and DMs.
- **Estimable (E)**: Follows established aggregate repository, event store, and Lit microfrontend patterns.
- **Small (S)**: Confined cleanly to `services/campaign_lore/`; all new files < 350 lines.
- **Testable (T)**: Fully verifiable via blackbox REST endpoints and domain event assertions.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Domain Aggregates & Event Handlers**:
   - `AtlasAggregate` and `CodexAggregate` implemented in `services/campaign_lore/` handling pin placement, territory updates, and codex entries.
2. **SpiceDB Zanzibar Enforcement**:
   - Private codex notes verified inaccessible to unauthorized party members through public endpoints.
3. **Microfrontend Element & Storybook**:
   - `<runefoble-campaign-atlas>` rendered with Shadow DOM and Bauhaus design tokens, with interactive Storybook stories.
4. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_campaign_atlas.py` verifying pin creation, timeline filtering, and codex access control via public HTTP routes.
5. **Quality Gates**:
   - Zero files exceeding 500 lines per Hard Invariant 6.
   - Passes `uv run pytest tests/test_blackbox_campaign_atlas.py` and frontend Storybook builds cleanly.
