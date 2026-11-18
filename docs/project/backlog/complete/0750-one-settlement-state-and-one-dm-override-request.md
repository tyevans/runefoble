---
id: '0750'
title: One SettlementState Model and One DMOverrideRequest Model
status: Complete
created: 2026-11-17
dependencies:
- TASK-0491
governing_adrs:
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0024
governing_stories:
- US-0072
- US-0075
target_bc: game_session
target_release: 0.9.0
---
# TASK-0750: One SettlementState Model and One DMOverrideRequest Model

## Status
Complete

## Summary
Two packages define `SettlementState`, and two modules define `DMOverrideRequest`. Two shapes reach the HTTP API under one name. TASK-0491 removes the shadowed facade files but does not choose between these models.

## Problem Statement
- `services/game_session/src/game_session/settlements/models.py:33` (removed) and `settlement/models.py:140` both define `SettlementState`. `dependencies.py:19`, `routers/settlements.py:15`, and `models/settlement.py:5` import the old `settlements/` package.
- `settlements/auth.py` duplicates `settlement/auth/permissions.py`. `settlements/aggregate.py` is a facade of `settlement/settlement_aggregate.py`.
- `DMOverrideRequest` is defined in `models/director.py:10` and `settlement/haggling_models.py:104`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0007, ADR-0011.
- TASK-0491 owns the shadowed files (`aggregate.py`, `caravan.py`, `settlement/auth.py`, `settlement/workers.py`, `settlement/haggling.py`). Index addenda list the extra files. Run after it.

## Product & User Story References
- PRD-0024
- US-0072
- US-0075

## Detailed Specification & Implementation Plan
1. Diff the two `SettlementState` field sets. Keep the one that the HTTP responses use. Move the other fields in, or drop them if no route reads them.
2. Delete the `settlements/` package. Point `dependencies.py`, `routers/settlements.py`, and `models/settlement.py` at `game_session.settlement.*`.
3. Rename the haggling `DMOverrideRequest` to `HaggleDmOverrideRequest` (or the director one to `DirectorOverrideRequest`). Update all call sites. Add no alias.

## Frontdoor Blackbox Test Plan
- Existing settlement, haggling, and bounty blackbox suites pass. Charter, upgrade, and bounty HTTP responses keep the same JSON (assert on one saved response body before and after).

## Definition of Done
- `grep -rn "class SettlementState\|class DMOverrideRequest" services/game_session/src` finds one of each.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: medium
- Source audits: `game-session.md (F1 in part)`
