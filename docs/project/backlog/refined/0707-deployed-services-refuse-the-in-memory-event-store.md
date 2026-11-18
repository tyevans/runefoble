---
id: '0707'
title: Deployed Services Refuse the In-Memory Event Store
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0707: Deployed Services Refuse the In-Memory Event Store

## Status
Refined. Found by the refactor audit round r1 and checked against the code by the orchestrator.

## Summary
`use_postgres_event_store` defaults to `False`. Any service that does not set it runs on `InMemoryEventStore` in production and loses all events on restart. The default must follow the environment, and a deployed service must never select memory.

## Problem Statement
- `libs/runefoble_platform/src/runefoble_platform/config.py:37`: `use_postgres_event_store` defaults to `False`.
- `libs/runefoble_platform/src/runefoble_platform/event_sourcing.py:71` takes the PostgreSQL branch only when the flag is true. The last lines of `get_event_store` assign `InMemoryEventStore()` for every other case, including `environment="production"`.
- `PlatformSettings.is_deployed` (`config.py:67`) has one reader (`services/game_session/src/game_session/dependencies.py:39`).
- Only four Helm templates set the flag: `soundscape.yaml:44`, `services.yaml:59`, `campaign-analytics.yaml:41`, `asset-forge.yaml:45`.
- `get_event_store` is 55 lines and mixes URL normalization, a reachability probe, engine creation and the store choice.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011, ADR-0015.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Make the memory store an explicit test choice. Add a settings value that selects it, for example `event_store_backend: Literal["postgresql", "memory"]`. The default is `postgresql` when `is_deployed` is true.
2. In `get_event_store`, raise `EventStoreInitializationError` when `is_deployed` is true and the backend is `memory`. Do not add a fallback.
3. Split `get_event_store` into `_build_postgres_store(settings)` and the store choice. Each helper is under 30 lines.
4. Set the root test settings to select `memory`. Update every caller that relied on the old default.
5. Update `docs/reference/platform-services.md` with the new setting.

## Frontdoor Blackbox Test Plan
- Start a service app with `RUNEFOBLE_ENVIRONMENT=production` and no store setting and no reachable PostgreSQL. Start-up fails with `EventStoreInitializationError`.
- With a reachable PostgreSQL (existing test container fixture), `GET /healthz` of the service starts and a command survives a new app instance.
- Development settings with `memory` selected start without PostgreSQL.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high
- Source audits: `refactor-r1/libs.md`
