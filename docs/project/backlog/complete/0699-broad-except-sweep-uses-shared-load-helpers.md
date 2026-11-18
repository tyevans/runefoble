---
id: '0699'
title: Broad Exception Handlers Use the Shared Load and Authorization Error Helpers
status: Complete
created: 2026-11-17
dependencies:
- TASK-0561
governing_adrs:
- ADR-0001
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0699: Broad Exception Handlers Use the Shared Load and Authorization Error Helpers

## Status
Complete

## Summary
Broad `except Exception` blocks remain around aggregate loads and SpiceDB checks outside the TASK-0561 file list. They hide store and SpiceDB outages.

## Problem Statement
- `services/campaign_lore/src/campaign_lore/routers/west_marches.py:102,132,178,216,261` (removed) and `west_marches_aggregate.py:37`.
- `services/game_session/src/game_session/west_marches.py:33`, `settlement/settlement_aggregate.py:33`, `stronghold.py:148,184`.
- `services/soundscape/src/soundscape/routers/leitmotif.py:60`: swallows SpiceDB errors on the character `edit` check.
- `services/game_session/src/game_session/minigame_tables/ws_manager.py` `broadcast`: silent catch around sends.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0001, ADR-0011, ADR-0015.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Replace load-site handlers with the TASK-0561 helpers (not found gives 404 or a new aggregate by contract; a store error gives 503).
2. In `leitmotif.py`, let SpiceDB errors surface through the shared authorization error mapping (503). Keep the fallback to the session/campaign check only for a clean `False`.
3. In `broadcast`, catch only socket-closed errors, remove the dead socket, and count other send failures.
4. Grep all `services/*/src` for remaining `except Exception` around loads or permission checks and fix them in this task.

## Frontdoor Blackbox Test Plan
- For each route group: store outage through the public route gives 503 and writes nothing.
- Leitmotif route with a SpiceDB outage gives 503.

## Definition of Done
- No `except Exception` around an aggregate load or a permission check remains in `services/*/src`.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `work/0561.md`, `work/0566.md`

## Orchestrator Addenda (2026-11-17, refactor-r1)

- TASK-0561 (aggregate load helpers): append "Add `services/game_session/src/game_session/routers/tavern.py:193-194`, `:246-247`, `:266-275`, and `:313-322` (load errors become 404, a new merchant, or a canned merchant). Not found gives 404, a store error gives 503. The canned `Local Merchant` payload is deleted. TASK-0728 owns the structural change. `crafting_router.py:104` and `:193` belong to TASK-0729, not to this task."

## Orchestrator Addenda (2026-11-17, refactor-r1)

- TASK-0699 (broad-except sweep): append "Out of scope for this task, owned elsewhere: game_session router sites (TASK-0751), board_state and character_sheet mutation routes (TASK-0752), crafting router (TASK-0729), tavern router (TASK-0561 and TASK-0728)."
