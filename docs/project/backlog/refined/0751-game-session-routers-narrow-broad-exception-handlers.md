---
id: '0751'
title: game_session Routers Narrow Broad Exception Handlers to Typed Errors
status: Refined
created: 2026-11-17
dependencies:
- TASK-0561
- TASK-0699
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---
# TASK-0751: game_session Routers Narrow Broad Exception Handlers to Typed Errors

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
About 33 broad `except Exception` sites in game_session routers sit outside the TASK-0561 and TASK-0699 lists. They map storage and upstream outages to wrong statuses or to success.

## Problem Statement
- 60 `except Exception` sites exist in `services/game_session/src`. 33 are outside West Marches, stronghold, and settlement paths: `routers/reactions.py` (5), `routers/combat.py` (5), `routers/caravan_trade.py` (4), `routers/campfire.py` (3), `routers/autopilot.py` (2), and single sites in `routers/session.py`, `routers/caravan_contracts/{auth,lifecycle,board}.py`, `minigame_tables/ws_manager.py:38`, `minigame_rules.py:21`, `contracts/auth.py:18`, `caravan/models.py:19`, `campaign/tuples.py:26`.
- `routers/tavern.py` sites belong to TASK-0561 and TASK-0728. `ws_manager.py` `broadcast` belongs to TASK-0699.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- Run `grep -rn "except Exception" services/game_session/src` first and list each site with its owning task.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Narrow each site to the typed exception it expects (`AggregateNotFoundError`, `httpx.HTTPError`, `ValidationError`, a SpiceDB error). Other errors reach the platform handler.
2. Add one exception-to-status mapping in `main.py` (store or upstream outage gives 503, bad upstream reply gives 502).
3. Check each site against its blackbox test. Split the work by router group if it exceeds one session; state the split in the PR.

## Frontdoor Blackbox Test Plan
- For each router group: inject a store or upstream failure through the public seam (loopback upstream, store double). Assert 502 or 503 and no event in the stream.

## Definition of Done
- No `except Exception` remains in `services/game_session/src/game_session/routers/` except where a comment states why and the handler re-raises.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: medium
- Source audits: `game-session.md (F3)`
