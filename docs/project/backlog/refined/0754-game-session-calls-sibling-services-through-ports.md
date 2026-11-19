---
id: '0754'
title: game_session Calls Character, Voice, and Watcher Services Through Ports on the Shared Client
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0021
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---
# TASK-0754: game_session Calls Character, Voice, and Watcher Services Through Ports on the Shared Client

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
Three hand-written HTTP clients in game_session duplicate the shared service client. ADR-0015 (b) requires one shared typed client.

## Problem Statement
- `services/game_session/src/game_session/character_client.py:39` (client per call, custom error class).
- `voice_client.py:58` (same pattern, another timeout variable).
- `routers/autopilot.py:23` (`httpx.AsyncClient(timeout=5.0)` in a router; `:25-31` maps errors to 503).
- `game_session` does not import `runefoble_platform.service_client`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- `docs/reference/service-client.md`, `docs/how-to/test-cross-service-calls-with-live-upstreams.md`. TASK-0744 adds the credential header to the shared client: land it first or run in the same pass.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add `game_session/ports/` with `CharacterSheetPort`, `VoiceAgentPort`, and `WatcherPort`. Build each on the shared `ServiceClient`. Inject them through `dependencies.py`.
2. Move the Watcher call out of `routers/autopilot.py` into `game_session/autopilot.py`.
3. Keep the 503 mapping and the 5 s default timeout. Delete the three old clients.

## Frontdoor Blackbox Test Plan
- One loopback-upstream test per port: 200 on success, 503 on an unreachable upstream, 503 on an upstream 5xx.

## Definition of Done
- `grep -rn "httpx.AsyncClient" services/game_session/src` finds no hit.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: medium
- Source audits: `game-session.md (F5)`
