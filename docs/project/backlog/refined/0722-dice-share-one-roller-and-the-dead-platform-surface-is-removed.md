---
id: '0722'
title: Dice Share One Roller and the Dead Platform Surface Is Removed
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0007
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0722: Dice Share One Roller and the Dead Platform Surface Is Removed

## Status
Refined. Found by the refactor audit round r1 and checked against the code by the orchestrator.

## Summary
The MCP dice tool copies dice logic and silently rolls `1d20` for bad notation. `UserPrincipal` is dead, and the platform `__init__` re-exports about 70 names.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/tools/dice.py:16-31` rolls with `random.randint`. On a bad notation it returns a `1d20` roll with no error.
- Platform dice: `libs/runefoble_platform/src/runefoble_platform/dice.py:21` (`evaluate_dice`, 73 lines) and `:96` (`parse_and_roll`). Used by `services/game_session/src/game_session/routers/session.py:40,311`.
- `libs/runefoble_platform/src/runefoble_platform/models.py:30` defines `UserPrincipal`. Nothing consumes it. `__init__.py:54,97` exports it.
- `runefoble_platform/__init__.py` (150 lines) re-exports about 70 names from 14 modules.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0007.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. The MCP `roll_dice` calls `parse_and_roll`. A bad notation returns an error result, not a default roll. Keep the fixed-roll test hooks.
2. Split `evaluate_dice` into two or three helpers of under 40 lines.
3. Delete `UserPrincipal` (add it to the TASK-0485 list if that task runs first). Trim `__init__.py` to names that callers import (check with grep). Callers import the rest from submodules. No alias remains.
4. Leave minigame rolls in game_session. Their rules differ.

## Frontdoor Blackbox Test Plan
- MCP `roll_dice` with fixed rolls returns the same shape as `parse_and_roll`. A bad notation returns an error.
- `uv run pytest` passes. Each service `main` module imports.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `refactor-r1/libs.md`

## Orchestrator Addenda (2026-11-17, refactor-r1)

- TASK-0722 (dice share one roller): append "`gateway/mcp/src/gateway_mcp/tools/dice.py:13` uses `re.match` with no end anchor, so `1d20abc` is accepted as `1d20`. The new `roll_dice` rejects trailing text (`fullmatch`). Test: `roll_dice(\"1d20abc\")` returns an error."
