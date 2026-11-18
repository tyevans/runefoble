---
id: '0560'
title: Shared Event Store Factory, Fail-Fast Initialization & Helm Wiring
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0005
- ADR-0006
- ADR-0011
governing_prds:
- PRD-0005
governing_stories:
- US-0010
target_release: 0.9.0
---

# TASK-0560: Shared Event Store Factory, Fail-Fast Initialization & Helm Wiring

## Status
Complete

## Summary
Make `runefoble_platform.event_sourcing.get_event_store` the single event-store factory for every bounded context. When the PostgreSQL store is configured, a failed initialization must stop the process instead of falling back to `InMemoryEventStore`. Helm must enable the PostgreSQL store for every service that owns `AggregateRepository` state. The health endpoint must report the store kind that is in use.

## Problem Statement
Every deployed service keeps all aggregate state in memory. No Helm template sets `RUNEFOBLE_USE_POSTGRES_EVENT_STORE`, so a restart loses every session, board, character, soundscape mix, and lore document.

Evidence:
- `deployments/helm/runefoble/templates/services.yaml:35-50` sets `RUNEFOBLE_DATABASE_URL` only. `grep -rn RUNEFOBLE_USE_POSTGRES_EVENT_STORE deployments/` returns no hits (w3-event-wiring.md F4).
- `libs/runefoble_platform/src/runefoble_platform/config.py:32-38` defaults the flag to `False`.
- `libs/runefoble_platform/src/runefoble_platform/event_sourcing.py:96-99` logs a warning and returns `InMemoryEventStore()` when PostgreSQL init fails (w1-libs F6).
- `services/game_session/src/game_session/dependencies.py:41` and `services/board_state/src/board_state/dependencies.py:24` build repositories at import time, so the store choice is fixed once per process (w1-game-session F1, w1-board-state F3).
- `services/asset_forge/src/asset_forge/dependencies.py:30`, `services/soundscape/src/soundscape/dependencies.py:32`, `services/rules_compendium/src/rules_compendium/dependencies.py:20-23`, and `services/campaign_lore/src/campaign_lore/dependencies.py:37-42` have the same pattern.
- `services/*/src/*/main.py` health checks report `type(get_event_store()).__name__` (for example `services/board_state/src/board_state/main.py:64`), so the report hides the fallback.
- `docs/reference/platform-services.md:42` documents a "Graceful Fallback" that AGENTS.md Hard Invariant 2 does not allow.
- `libs/runefoble_platform/src/runefoble_platform/consumer_group.py:14,168` and `gateway/mcp/src/gateway_mcp/dynamic/events.py:19-22` reach `MockAsyncRedis` from production code (w1-libs F11). This task removes the store-side mock path only. The Redis mock is handled in TASK-0579.

## Documentation & Architecture Review
- `docs/how-to/define-event-sourced-aggregates.md` section 6 says staging and production use the PostgreSQL store. The code and Helm do not match this. Fix the how-to with this task.
- `docs/reference/platform-services.md:38-42` documents the flag and the fallback. Correct both lines.
- ADR-0011 (eventsource-py) requires persisted aggregate state. ADR-0005 requires Helm to configure the cluster. Both support this change.
- Existing task overlap: none for the flag. TASK-0485 (platform shims) does not touch `event_sourcing.py` behavior.

## Product & User Story References
- [`prd-0005-realtime-websocket-board-sync.md`](../../product/accepted/prd-0005-realtime-websocket-board-sync.md): board state must survive a restart.
- [`us-0010-redis-streams-domain-event-subscription.md`](../../user_stories/accepted/us-0010-redis-streams-domain-event-subscription.md): domain events must be durable and replayable.

## Detailed Specification & Implementation Plan
1. In `libs/runefoble_platform/src/runefoble_platform/event_sourcing.py`, remove the silent fallback in `get_event_store`. If `use_postgres_event_store` is true and the engine or schema init fails, raise `EventStoreInitializationError` and do not return `InMemoryEventStore`. Keep `InMemoryEventStore` only when the flag is false.
2. Add a public `event_store_kind()` helper that returns `"postgresql"` or `"memory"`. Services use it in `/healthz` in place of `type(...).__name__`.
3. In `deployments/helm/runefoble/templates/services.yaml`, add `RUNEFOBLE_USE_POSTGRES_EVENT_STORE: "true"` to the shared env block. The same change applies to the asset-forge, soundscape, campaign-lore, and rules-compendium templates if they define their own env.
4. Do not set the flag for test runs. Tests keep `InMemoryEventStore` by leaving the flag unset.
5. Correct `docs/reference/platform-services.md` lines 38-42 and `docs/how-to/define-event-sourced-aggregates.md` section 6.
6. Add a Helm render check (script in `deployments/helm/runefoble/tests/` or the existing `make` helm target) that fails when a service with an `AggregateRepository` lacks the flag.

Files expected to change: `event_sourcing.py`, `config.py`, `services.yaml`, two or three service templates, two docs, one health helper, one Helm check. Under 15 files.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** start the application with the flag `true` and an unreachable `RUNEFOBLE_DATABASE_URL`. Before: the process starts and `/healthz` reports `memory`. After: the process exits non-zero at start-up and no HTTP route is served.
- **Fail before, pass after:** `helm template` of the umbrella chart. Before: no service env has the flag. After: every aggregate-owning service env has `RUNEFOBLE_USE_POSTGRES_EVENT_STORE: "true"`.
- **Persistence (manual Kind run, not in unit suite):** create a board through `POST /api/v1/boards`, restart the board pod, and read it through `GET`. Before the fix this returns 404.
- **Public surface only:** assertions use HTTP responses and `helm template` output. No private attributes.

## Definition of Done
1. `get_event_store` raises on PostgreSQL init failure when the flag is true. No fallback code path remains.
2. Helm sets the flag for every aggregate-owning service. `helm lint` and `helm template` pass.
3. `/healthz` reports the store kind through the shared helper.
4. The two reference docs no longer describe a fallback.
5. Blackbox test for fail-fast passes. `uv run pytest` and `make health-check` pass.
6. No file exceeds 500 lines. Changes recorded in `CHANGELOG.md` under `[Unreleased]`.

## Audit Provenance

- Severity: critical
- Source audits: `w3-event-wiring.md`, `w1-game-session.md`, `w1-board-state.md`, `w2-asset-forge.md`, `w2-rules-compendium.md`, `w2-campaign-lore.md`, `w1-libs.md`
