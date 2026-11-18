---
id: '0729'
title: Crafting Combine Is a Typed Service That Fails Loudly and Publishes Health Events
status: Complete
created: 2026-11-17
dependencies:
- TASK-0561
- TASK-0551
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds:
- PRD-0014
governing_stories:
- US-0044
target_bc: character_sheet
target_release: 0.9.0
---
# TASK-0729: Crafting Combine Is a Typed Service That Fails Loudly and Publishes Health Events

## Status
Complete

## Summary
`combine_reagents` hides load failures and returns success without deducting reagents. It saves two aggregates in a fixed order with no guarantee, and mishap damage skips the health events.

## Problem Statement
- `services/character_sheet/src/character_sheet/crafting_router.py:91-181`: one route loads and saves two aggregates, deducts inventory, applies mishap damage, and publishes events.
- `crafting_router.py:104`: `except Exception:` replaces a failed crafting load with an empty `CraftingAggregate`.
- `crafting_router.py:109`: `contextlib.suppress(Exception)` drops a failed character load. The route returns success and deducts no reagents.
- The crafting aggregate is saved and published (`:139-146`) before the character is saved. A failure between the two leaves them out of step.
- Mishap damage calls `char.modify_health(...)` directly. That path does not publish `CharacterHealthChanged` or `CharacterDamaged`. The health route does (`dependencies.py:176-221`).
- `crafting.combine_reagents` returns a dict that the router reads with string keys. `get_crafting_history` (`:193`) turns every error into an empty state.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011, ADR-0015.
- `docs/how-to/run-campfire-rests-and-alchemical-crafting.md`, `docs/reference/downtime-and-crafting-events.md` (document the new health events).
- TASK-0561 does not list `crafting_router.py`. This task owns these sites. TASK-0551 edits the `edit` check on this route. Run after it.

## Product & User Story References
- PRD-0014
- US-0044

## Detailed Specification & Implementation Plan
1. Add `character_sheet/crafting/service.py` with `CombineReagentsService.combine(...)` returning a typed `CombineResult` (dataclass).
2. Load the character with the TASK-0561 `load_or_404` helper. A load error propagates (503). Not found gives 404.
3. Save the character first, then the crafting aggregate. Publish after both saves (publish policy from TASK-0693).
4. Route mishap damage through the same health helper as the health route so the standard events are published.
5. `get_crafting_history` returns an empty state only for not found.

## Frontdoor Blackbox Test Plan
- Combine a reagent set through `POST /api/v1/characters/crafting/recipes/combine`. Assert inventory, HP, and the standard health events on the stream.
- Store failure on the character load (stub repository, not a private patch): assert 503 and no crafting event.

## Definition of Done
- No `except Exception` or `suppress(Exception)` remains in `crafting_router.py`.
- Reference doc lists the mishap health events.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: high
- Source audits: `board-character-forge.md (F4)`
