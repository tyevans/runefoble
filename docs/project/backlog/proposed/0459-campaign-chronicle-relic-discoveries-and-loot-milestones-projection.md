---
id: '0459'
title: Campaign Chronicle Relic Discoveries and Loot Milestones Projection
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0052
- TASK-0101
- TASK-0110
governing_adrs:
- ADR-0006
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0012
- PRD-0015
governing_stories:
- US-0040
- US-0045
- US-0050
target_release: 0.9.0
---

# TASK-0459: Campaign Chronicle Relic Discoveries and Loot Milestones Projection

## Status
Proposed

## Summary
Expand the `campaign_analytics` living chronicle timeline projection to capture relic discoveries, wax seal breaches, invisible ink reveals, and rare loot acquisitions as first-class timeline milestones. Ingest `campaign_lore` and `character_sheet` loot events from Redis Streams, project them with interactive metadata links into `timeline_table`, and enrich `<runefoble-chronicle-timeline>` to display tactile relic badges and loot discovery markers.

## Problem Statement
PRD-0012 explicitly requires the living campaign timeline to track "past sessions, epic boss battles, character deaths, and acquired relics." While session lifecycles, character knockouts, and boss encounter commencements are currently projected to milestones in `event_handlers.py`, tactile relic discoveries (`RelicForged`, `RelicInspected`, `WaxSealBroken`, `InvisibleInkRevealed`) and legendary equipment finds are ignored by the analytics dispatcher. Consequently, players reviewing past campaign chronicles cannot see when key relics were uncovered or inspect them directly from the historical timeline.

## Governing Architecture & ADRs
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Fanout consumption of `campaign_lore` and `character_sheet` domain events.
- **ADR-0007: Domain-Driven Design Architecture**: Cross-context projection from lore and inventory aggregates into analytics read models.
- **ADR-0011: eventsource-py Core Event Sourcing**: Deterministic projection from domain events into chronological milestones.

## Product & User Story References
- [`prd-0012-campaign-telemetry-and-living-chronicle-timeline.md`](../../product/accepted/prd-0012-campaign-telemetry-and-living-chronicle-timeline.md)
- [`prd-0015-generative-handouts-relic-inspector-and-printable-forge.md`](../../product/accepted/prd-0015-generative-handouts-relic-inspector-and-printable-forge.md)
- [`us-0040-campaign-combat-telemetry-and-living-timeline.md`](../../user_stories/accepted/us-0040-campaign-combat-telemetry-and-living-timeline.md)
- [`us-0045-generative-handouts-wax-seals-and-3d-relics.md`](../../user_stories/accepted/us-0045-generative-handouts-wax-seals-and-3d-relics.md)

## Scope of Work
1. **Loot and Relic Projection Handlers (`services/campaign_analytics/src/campaign_analytics/event_handlers.py`)**:
   - Add event handlers for `RelicForged`, `RelicInspected`, `WaxSealBroken`, `InvisibleInkRevealed`, and `InventoryItemAdded`.
   - Filter items with rarity >= `Rare` or marked as narrative relics.
   - Extract discoverer character name, relic title, 3D relic model URL, and description into timeline milestone metadata.
2. **Timeline Milestone Categories and Filtering (`services/campaign_analytics/src/campaign_analytics/queries/timeline.py`)**:
   - Support `relic_discovery` and `legendary_loot` milestone types.
   - Add query parameter `?type=relic_discovery` to allow filtering the chronicle timeline specifically for relics and major artifacts.
3. **Timeline Microfrontend Milestone Card Enrichment (`services/campaign_analytics/ui/src/runefoble-chronicle-timeline.ts`)**:
   - Render tactile relic discovery cards with golden glowing badge borders and relic icon glyphs.
   - Dispatch `inspect-relic` custom event when a player clicks a relic milestone, enabling seamless transition to `<runefoble-relic-inspector>`.
4. **Frontdoor Blackbox Verification (`tests/test_blackbox_chronicle_relic_milestones.py`)**:
   - Ingest sequence of relic generation and inventory loot events, query timeline endpoint, and verify relic milestones are persisted and returned with metadata.

## Definition of Done
1. `event_handlers.py` and `queries/timeline.py` remain strictly < 300 lines each per Hard Invariant 6.
2. Relic discoveries and high-tier loot are projected into the campaign chronicle timeline with accurate metadata.
3. `<runefoble-chronicle-timeline>` displays relic badge categories with inspect action dispatch.
4. Blackbox test suite passes with 100% assertions via `uv run pytest tests/test_blackbox_chronicle_relic_milestones.py`.
