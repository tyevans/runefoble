---
id: '0799'
title: Legacy Event Aliases and Structural Facade Tests Are Removed, and Old Shim Tasks Are Reconciled
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: runefoble_events
target_release: 0.9.0
---

# TASK-0799: Legacy Event Aliases and Structural Facade Tests Are Removed, and Old Shim Tasks Are Reconciled

## Status
Complete

## Summary
Two legacy event aliases stay registered, some tests check module structure instead of behaviour, and four refined shim tasks may already be done by TASK-0793.

## Problem Statement
- `libs/runefoble_events/src/runefoble_events/asset.py:119-129`: aliases `BattlemapCreated` and `AssetGenerated` with extra `register_event` calls.
- `tests/test_analytics_modular_decomposition.py` (removed), `tests/test_game_session_modular_decomposition.py:46` and similar: facade and "backward compatibility" structure checks (TASK-0681 allows only `make health-check` as a structural gate).
- Refined TASK-0485, TASK-0491, TASK-0493 and TASK-0750 overlap with TASK-0793.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011, ADR-0014.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Remove the aliases and update every producer and consumer to the canonical event names. The platform has no external users. Development event stores that hold the old names are accepted as lost (DoR 9).
2. Delete structure-only tests. Keep any behaviour assertion they hold by moving it to a frontdoor test.
3. For each of TASK-0485, TASK-0491, TASK-0493 and TASK-0750, check every spec item against main. Write the result to the report: done (with evidence) or the items still open. Do not edit backlog files.

## Frontdoor Blackbox Test Plan
- A battlemap generation publishes only the canonical event name, and the board consumer still reacts to it.
- `grep -rn "BattlemapCreated\|AssetGenerated" libs services gateway` returns nothing.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `.audit/work/0793.md` (Discovered)
