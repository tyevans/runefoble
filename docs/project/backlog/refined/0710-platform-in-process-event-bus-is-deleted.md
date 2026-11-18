---
id: '0710'
title: Platform In-Process Event Bus Is Deleted
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0006
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0710: Platform In-Process Event Bus Is Deleted

## Status
Refined. Found by the refactor audit round r1 and checked against the code by the orchestrator.

## Summary
`runefoble_platform.bus` is a process-local event bus. Most publishes through it reach no subscriber, and the one subscriber also reads the same events from Redis. The module is a hidden second delivery path.

## Problem Statement
- `libs/runefoble_platform/src/runefoble_platform/bus.py:1-37` defines `EventBus` and a global `bus`. `publish` uses `return_exceptions=True`, so it records no failure.
- Publish sites: `services/asset_forge/src/asset_forge/dependencies.py:145-147`, `services/soundscape/src/soundscape/dependencies.py:149-151`, `gateway/api/src/gateway_api/assets.py:170-173` and `:266-269`.
- The only subscriber is `services/soundscape/src/soundscape/event_handlers.py:160-168`. asset_forge and the gateway have none.
- `gateway/api/src/gateway_api/assets.py:162` and `:259` import `get_event_bus` from `gateway_api.main` inside the publish function.
- Soundscape also runs a Redis consumer. A handler may run twice. Not verified.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0006, ADR-0015.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. First write a test that shows whether a soundscape event reaches its handler twice (in-memory plus Redis). Record the result in the PR.
2. Replace each publish site with `publish_best_effort` or `publish_or_fail` on the service `EventBusProvider` bus. State the policy at each call.
3. The gateway reads its bus from its own dependencies module, not from `gateway_api.main`.
4. Soundscape handlers run from the Redis consumer only.
5. Delete `bus.py` and its export. No alias remains.

## Frontdoor Blackbox Test Plan
- Upload an asset through the gateway with the Redis test double. Exactly one entry appears on `runefoble.events.asset.uploaded`.
- A soundscape state change that needs the event is visible through a public query route, once.
- `grep -rn "runefoble_platform.bus" services gateway libs` returns nothing.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r1/libs.md`
