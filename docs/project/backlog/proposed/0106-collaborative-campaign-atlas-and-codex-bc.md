---
id: '0106'
title: Collaborative Campaign World Atlas & Living Party Codex
status: Proposed
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
target_release: 0.4.0
prd_url: docs/project/product/accepted/prd-0015-generative-handouts-relic-inspector-and-printable-forge.md
user_story: US-0050
---

# TASK-0106: Collaborative Campaign World Atlas & Living Party Codex

## Status
Proposed

## Summary
Build an interactive multi-layered world atlas and collaborative party codex with chronological timeline pins, territory boundaries, player secret notes, and automated cross-referencing against the `campaign_lore` redstring graph.

## Problem Statement
Campaign lore and geography are currently disconnected from active session play (PRD-0015, US-0050). Chroniclers like Rowan need a dynamic map where party milestones are pinned to the timeline, and secret lore entries can be shared or kept private with Zanzibar permissions.

## Governing Architecture & ADRs
- **ADR-0001**: SpiceDB Zanzibar Object-Level Authorization (private vs. shared party codex notes).
- **ADR-0003**: UV Monorepo Workspace (`services/campaign_lore`).
- **ADR-0006**: Redis Streams Event Bus (`AtlasPinCreated`, `CodexEntryPublished`).
- **ADR-0011**: eventsource-py Core Event Sourcing (`AtlasAggregate`, `CodexAggregate`).
- **ADR-0013**: Microfrontend Architecture (`<runefoble-campaign-atlas>`).

## Scope of Work
1. **Interactive Multi-Layered Map Engine**:
   - Deep-zoom pan/zoom canvas displaying continental, regional, and city maps with layer toggles.
2. **Timeline Milestone Pins**:
   - Geotagged pins linking historical campaign events, session recaps, and redstring lore entities.
3. **Collaborative Party Codex**:
   - Rich-text markdown editor with automatic entity hyperlinking to NPC, faction, and location lore graphs.
4. **Zanzibar Access Enforcement**:
   - Fine-grained privacy controls allowing players to keep personal theories hidden until revealed.
5. **Frontdoor Blackbox Verification**:
   - Blackbox test suite validating atlas coordinates, Zanzibar authorization queries, and codex event persistence.
