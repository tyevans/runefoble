---
id: '0752'
title: Board and Character Mutation Routes Map Typed Errors in One Place
status: Refined
created: 2026-11-17
dependencies:
- TASK-0699
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: board_state
target_release: 0.9.0
---
# TASK-0752: Board and Character Mutation Routes Map Typed Errors in One Place

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
Mutation routes in board_state and character_sheet catch every exception and return 400 or 500. A storage outage looks like a bad request.

## Problem Statement
- board_state: `routers/tokens.py:47` (400), `:96` and `:122` (500); `routers/actions.py:74`; `routers/aoe.py:48`, `:112`; `routers/previews_http.py:34`; `routers/terrain.py:62`, `:76`, `:90`; `routers/physics.py:68`, `:110`.
- character_sheet: `dependencies.py:172` (`execute_character_mutation`, 400 for every error). The routes in `router.py` (`modify_health`, `update_guardrails`) repeat it.
- TASK-0699 covers loads and permission checks. It does not list these mutation routes. TASK-0546 owns the board permission probe.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- TASK-0699 is the owner of the shared load helpers: reuse them.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Map `ValueError` to 400 and `AggregateNotFoundError` to 404 in one exception handler per service. Remove the per-route `except Exception`.
2. Other errors reach the platform handler (503 for storage or SpiceDB outage).
3. Keep the 400 text for validation errors.

## Frontdoor Blackbox Test Plan
- Stub a storage failure through the public test harness (TASK-0697) and assert 503 on a token move, a terrain change, and a character health change.
- A bad input still returns 400.

## Definition of Done
- No `except Exception` remains in the listed routers.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: medium
- Source audits: `board-character-forge.md (F8)`
