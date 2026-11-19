---
id: '0893'
title: game_session Shared Kernel Package (ADR-0021 Step 1)
status: Complete
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0021
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0893: game_session Shared Kernel Package (ADR-0021 Step 1)

## Status

Complete

## Summary

Create `game_session/shared/` and move the code that two or more domains use. Delete the model shims.

## Problem Statement

- Route identity (`get_principal`, `CallerId`) is in `settlement/auth/tokens.py` and every domain imports it.
- `check_establishment_play_permission` (`settlement/auth/permissions.py:81`) is used by downtime and settlement.
- Child index mechanism (`child_index.py`, `queries/child_index.py`) and stream name constants in `events.py`.
- Shims: `models.py:1-10`, `models/settlement.py:1-23`, `models/__init__.py:39-47` (DoR 9). `tests/test_game_session_models/test_settlements_and_facilities.py:6-13` uses one.

## Documentation & Architecture Review

- [ADR-0021](../../adrs/accepted/adr-0021-game-session-internal-bounded-contexts.md): game_session packages, ports-only import rule, migration order (D7).
- ADR-0015: no substitute values, no shims (DoR 9).

## Product & User Story References

None. Internal structure or data integrity.

## Detailed Specification & Implementation Plan

1. Create `game_session/shared/` with route identity, the shared permission helper, the child index mechanism and the stream names (ADR-0021 D2).
2. Delete the shims and update every import, tests included. No re-exports.
3. `shared` imports no domain module.

## Frontdoor Blackbox Test Plan

- The existing game_session blackbox suites pass unchanged in behaviour.
- The child index stream ids do not change: a list route returns children created before the move (`tests/test_blackbox_child_index_restart.py`).

## Definition of Done

- The plan is done. All game_session blackbox suites stay green. Docs updated. CHANGELOG entry.

## Audit Provenance

- Severity: medium
- Source audits: .audit/work/0753.md
