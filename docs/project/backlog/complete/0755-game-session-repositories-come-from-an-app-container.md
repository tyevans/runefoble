---
id: '0755'
title: game_session Repositories Come From an App Container Built at Start-Up
status: Complete
created: 2026-11-17
dependencies:
- TASK-0567
- TASK-0753
governing_adrs:
- ADR-0021
- ADR-0015
- ADR-0011
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---
# TASK-0755: game_session Repositories Come From an App Container Built at Start-Up

## Status
Complete

## Summary
`dependencies.py` builds 12 `AggregateRepository` objects at import time and reads the event store and settings at import time. The service cannot fail fast at start-up, and the package split in the ADR needs a container.

## Problem Statement
- `services/game_session/src/game_session/dependencies.py:51-87` (removed) builds 12 repositories at import time. The getters (`:90-125`) return those globals. `:33-48` reads the event store and settings at import time.
- TASK-0567 removes the index dicts at `:122-127`. TASK-0566 covers `ws_manager` memory.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015, ADR-0011.
- ADR-0015 (f): fail fast at start-up. The ADR from TASK-0753 sets package boundaries. Build the container so each package gets its own repository factory.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add `GameSessionContainer` built in the app lifespan. Store it on `app.state`. Expose repositories through FastAPI `Depends` providers.
2. Remove the module globals. Update routers and tests that import the getters.
3. The service fails at start-up when the event store is not configured.

## Frontdoor Blackbox Test Plan
- All existing blackbox HTTP tests pass.
- New: the app fails at start-up when the event store setting is missing (deployed environment setting).

## Definition of Done
- `dependencies.py` builds nothing at import time.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: medium
- Source audits: `game-session.md (F6)`
