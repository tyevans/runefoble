---
id: '0756'
title: Analytics Rows Are Keyed by Campaign Once the Session Mapping Arrives
status: Complete
created: 2026-11-17
dependencies:
- TASK-0730
governing_adrs:
- ADR-0011
governing_prds:
- PRD-0012
governing_stories:
- US-0054
target_bc: campaign_analytics
target_release: 0.9.0
---
# TASK-0756: Analytics Rows Are Keyed by Campaign Once the Session Mapping Arrives

## Status
Complete

## Summary
When no campaign is known, analytics rows store the session id in the campaign column. Every read then matches four id combinations, and the rows are never re-keyed.

## Problem Statement
- `services/campaign_analytics/src/campaign_analytics/event_handlers.py:67` sets `campaign = cid or sid`.
- `storage.py:51-69` (`campaign_match`) matches each query against four combinations. It runs in every heatmap, MVP, and timeline read.
- TASK-0574 (complete) changed producers and damage keys but not mapping order.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011.
- `docs/how-to/project-campaign-analytics-and-chronicle-timeline.md`. Run after TASK-0730, which edits the same handler and projection.

## Product & User Story References
- PRD-0012
- US-0054

## Detailed Specification & Implementation Plan
1. When `SessionCreated` maps a session to a campaign, re-key pending rows for that session in the same transaction as `map_session`.
2. Until the mapping exists, store rows with a null campaign and a session id column. Do not write the session id into the campaign column.
3. Queries filter on `campaign_id` only. Remove the subqueries from `campaign_match`.
4. Rewrite or drop existing rows: the platform has no external users (DoR 9).

## Frontdoor Blackbox Test Plan
- Publish `TokenMoved` and `CharacterHealthChanged` before `SessionCreated`. Then publish `SessionCreated` with a campaign id. Query the campaign heatmap through the public route. Assert the rows appear under the campaign.

## Definition of Done
- `campaign_match` has one condition.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: medium
- Source audits: `lore-rules-analytics-sound.md (F5)`
