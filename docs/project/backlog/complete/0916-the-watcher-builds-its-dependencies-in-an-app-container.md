---
id: '0916'
title: The Watcher Builds Its Dependencies in an App Container, Not Module Globals
status: Complete
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0021
- ADR-0011
- ADR-0015
governing_prds:
- PRD-0001
governing_stories: []
target_bc: the_watcher
target_release: 0.9.0
---
# TASK-0916: The Watcher Builds Its Dependencies in an App Container, Not Module Globals

## Status
Complete

## Summary
`the_watcher` builds its engines, settings and repositories at import time and keeps them in module globals with `get_`/`set_` seams. TASK-0755 (complete) moved `game_session` to an app container, and TASK-0859 does the same for four other services. The Watcher is not in either task.

## Problem Statement
- `services/the_watcher/src/the_watcher/dependencies.py:38-44`: `engine`, `chronicle_engine`, `autonomous_dm_engine`, `disambiguation_engine`, `compound_action_engine` and `platform_settings` are built at import.
- `:48` and `:56`: `_faction_simulation_engine` with a `global` setter.
- `:60-71`: four `LazyRepository` objects with `get_`/`set_` pairs.
- `:208`: `global copilot_engine`.

## Documentation & Architecture Review
- TASK-0755 (complete) and `docs/how-to/compose-a-service-with-an-app-container.md`: follow the same pattern.
- ADR-0015 (f): production code does not select in-memory adapters.
- DoR 9: remove the `set_` seams. Tests build a container.
- TASK-0919 changes `audience_narration.py`. Land in either order.

## Product & User Story References
- PRD-0001 (The Watcher). Platform quality work.

## Detailed Specification & Implementation Plan
1. Add `the_watcher/container.py` with a dataclass that holds the engines, the repositories, the copilot engine and the watcher ports. Build it in the app lifespan. Store it on `app.state`.
2. Add `Depends` providers that read the container from the request or WebSocket. Change routers to use them.
3. Remove the module globals and every `get_`/`set_` seam from `dependencies.py`. Remove the import-time `PlatformSettings()`.
4. Update test fixtures to build the app with a container that the test supplies (the TASK-0755 test helpers show the shape).
5. If the change touches more than about 15 files, stop after the container and the repository seams, and file the engine seams as a follow-up.

## Frontdoor Blackbox Test Plan
- All existing the_watcher HTTP and WebSocket route tests pass with fixtures that build a container.
- A start without a required setting fails in the lifespan, with the setting name in the error (start the app in a subprocess, as the other start-up tests do).

## Definition of Done
- `grep -n "global " services/the_watcher/src/the_watcher/dependencies.py` returns nothing. No `set_` seam remains.
- Docs updated. `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `services-backend.md` (finding 2)
