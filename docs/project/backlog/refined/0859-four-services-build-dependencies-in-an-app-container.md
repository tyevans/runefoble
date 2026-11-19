---
id: '0859'
title: Four Services Build Their Dependencies in an App Container, Not Module Globals
status: Refined
created: 2026-11-18
dependencies:
- TASK-0755
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: platform
target_release: 0.9.0
---
# TASK-0859: Four Services Build Their Dependencies in an App Container, Not Module Globals

## Status
Refined

## Summary
`asset_forge`, `campaign_analytics`, `campaign_lore`, and `voice_agent` keep service objects in module globals. Some globals have `set_` or `get_` seams that tests use. TASK-0755 fixes the same problem in `game_session`. This task applies the same pattern to the other four services. Each service builds one container at start-up and injects it. Start-up fails fast when required configuration is missing.

## Problem Statement
- `services/asset_forge/src/asset_forge/dependencies.py:36` and `:49-51`: `_wardrobe_generator` global with `global` statement.
- `services/asset_forge/src/asset_forge/map_generation_engine.py:8`: `_map_generator` global.
- `services/campaign_analytics/src/campaign_analytics/dependencies.py:27-28`: `_storage` and `_worker` globals.
- `services/campaign_lore/src/campaign_lore/dependencies.py:34`: `_west_marches_repo_override` global.
- `services/voice_agent/src/voice_agent/synthesis_engine.py:8`: `_synthesizer` global.
- `services/voice_agent/src/voice_agent/coordinator.py:261` and `:268`: `_default_coordinator` global with a `set_` setter.
- `services/voice_agent/src/voice_agent/stt.py:241` and `:244-251`: `_pipeline` global with `get_` and `set_`.

## Documentation & Architecture Review
- TASK-0755 (refined) defines the container pattern for `game_session`. Follow it.
- DoR 9: no shims. Remove the `set_` seams. Tests pass a container.
- ADR-0015 (f): production code does not select in-memory adapters.
- TASK-0345 (proposed) splits `stt.py`. Coordinate, or land this task first.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Define one container class per service in its `app.py` or `container.py`. It holds the services built at start-up.
2. Build the container in the FastAPI lifespan. Read settings once. Fail at start-up if a required setting is missing.
3. Inject the container through FastAPI `Depends` in each router.
4. Delete the module globals and the `set_` and `get_` seams.
5. Update tests to build the app with a fake container. Do not patch module attributes.
6. Do one service per commit. Each service is one vertical slice.

## Frontdoor Blackbox Test Plan
- For each service, the existing blackbox HTTP and WebSocket tests keep their assertions.
- Start the service with a missing required setting. Assert start-up fails with a clear message.
- No test imports a private singleton.

## Definition of Done
- No module-level service object remains in the four services.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r2/services-backend.md` (F5)
