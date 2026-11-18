---
id: '0793'
title: Remaining Compatibility Shims and Stale Duplicates Are Removed
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0011
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0793: Remaining Compatibility Shims and Stale Duplicates Are Removed

## Status
Refined. Found during batch 23 integration, 2026-11-17.

## Summary
Three DoR 9 violations remain: a soundscape route alias, a settlement facade module, and a stale duplicate settlement state model.

## Problem Statement
- `services/soundscape/src/soundscape/routers/stems.py:106`: alias `POST /api/v1/soundscape/override`. `docs/reference/ports-and-endpoints.md:264` lists it.
- `services/game_session/src/game_session/settlements/aggregate.py:1`: facade that re-exports `SettlementAggregate`.
- `services/game_session/src/game_session/settlements/models.py:33`: duplicate `SettlementState` without `gold_treasury`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Delete the alias and its docs row.
2. Delete the facade and the duplicate model. Import from `settlement/` at every call site.

## Frontdoor Blackbox Test Plan
- The alias path answers 404. The canonical `/stems/override` route still works.
- Settlement tests pass with one state model.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `.audit/work/0589.md`, `.audit/work/0786.md` (Discovered)
