---
id: '0734'
title: Hazard Damage Has One Table and the Move Preview Matches the Move
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0005
governing_stories:
- US-0043
target_bc: board_state
target_release: 0.9.0
---
# TASK-0734: Hazard Damage Has One Table and the Move Preview Matches the Move

## Status
Complete

## Summary
The move preview shows different hazard damage than the move applies. Three places hold hazard damage values, and they differ.

## Problem Statement
- `services/board_state/src/board_state/rules/:9-19`: `DEFAULT_HAZARD_DAMAGE` (acid `2d6`, spikes `2d4`, poison `1d4`, lava `2d10`, fire `1d6`). `handlers/tokens.py` applies it.
- `services/board_state/src/board_state/preview.py:145-146`: the preview hard-codes `2d10` for lava and `1d6` otherwise. For acid, spikes, and poison the preview and the move disagree.
- `preview.py:94-178` repeats the bounds check, the difficult-terrain cost (2 per cell), and the hazard walk from `rules.py`. It does not call them.
- `services/asset_forge/src/asset_forge/deterministic_map_generator.py` sets its own damage dice per theme. `libs/runefoble_events/src/runefoble_events/board_events/terrain.py:22-33` (`TerrainCellModified`) has no `damage_dice` field, so those values never reach the board.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0007, ADR-0011.
- `docs/how-to/interact-with-tactile-board-and-ghost-previews.md`. TASK-0704 owns the forge-to-board path: do not add a second path here.
- The rules decision (which table is authoritative) is made in this task: the board table in `rules.py` wins.

## Product & User Story References
- PRD-0005
- US-0043

## Detailed Specification & Implementation Plan
1. Add `board_state/rules/hazards.py` with `HAZARD_DAMAGE` and `walk_path(path, terrain)` returning cost and hazard triggers. `handlers/tokens.py` and `preview.py` both call it.
2. `compute_kinematic_route_preview` returns the same dice as `move_token`.
3. asset_forge keeps a hazard type and drops the damage-dice field from its output. The board owns the dice (coordinate the removal with TASK-0704).

## Frontdoor Blackbox Test Plan
- On a board with each hazard type: `POST /api/v1/boards/{id}/tokens/{tid}/preview` and `.../move`. Assert `damage_dice` is equal in both responses for acid, spikes, poison, lava, and fire.

## Definition of Done
- One table holds hazard dice. A test loops over every hazard type.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: high
- Source audits: `board-character-forge.md (F2)`
