---
id: '0888'
title: Worker Restock Raises an Event, and the Establishment Sync Runs Before the Publish
status: Complete
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0888: Worker Restock Raises an Event, and the Establishment Sync Runs Before the Publish

## Status

Complete

## Summary

The NPC worker restock route changes aggregate state lists directly and raises no domain event. The save stores nothing, so a restock is lost on the next load. Separately, two worker routes sync the establishment summary after the publish, so a 503 on the publish leaves the summary stale.

## Problem Statement

- `services/game_session/src/game_session/settlement/workers/routes_inventory.py:52-75`: `restock_worker_inventory` appends to `agg.state.shelf_inventory` or `backroom_inventory`, or edits an item in place. No `@handles` method and no event. This breaks Hard Invariant 2. The route answers 200 with the item, but a later `GET /api/v1/npcs/{npc_id}/inventory/{item_id}` does not show it after a reload from the store.
- `destination` accepts any string; any value other than `shelf` writes to the backroom.
- `settlement/workers/routes_relationships.py:34-36` and `routes_roster.py:97-98`: the establishment operations sync runs after `publish_aggregate_events`. A publish failure (503) skips the sync.

## Documentation & Architecture Review

- ADR-0011 and `docs/how-to/define-event-sourced-aggregates.md`: state changes flow through events and `@handles`.
- `docs/reference/redis-streams-event-bus.md`: publish failure policy (503 after save).

## Product & User Story References

None. Data integrity defect.

## Detailed Specification & Implementation Plan

1. Add a registered domain event (for example `runefoble.events.west_marches.worker_inventory_restocked`) with `item` and `destination`. The aggregate gets a command method and a `@handles` method that apply it. The route calls the command.
2. `destination` is a `Literal["shelf", "backroom"]`. Another value answers 422.
3. Move the establishment operations sync before the publish in both routes, so a 503 leaves a consistent summary. A retried relationship call must not add a duplicate tie: make the relationship command idempotent for the same pair and kind.
4. Document the new event in the events catalogue.

## Frontdoor Blackbox Test Plan

- Restock through the public route, then read the item through the public route on a fresh app (Postgres-backed event store or a reloaded repository). The quantity is there. Fails on current code.
- `destination=attic` answers 422.
- Mood change with an unreachable stream answers 503, and the establishment summary read shows the new state.
- The same relationship call twice gives one tie.

## Definition of Done

- Tests above pass. Event documented. CHANGELOG `Fixed` entry.

## Audit Provenance

- Severity: high
- Source audits: .audit/work/0886.md
