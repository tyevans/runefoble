---
id: '0733'
title: Square-Grid AoE Origin Sits on the Cell Centre and AoE and Spell Bloom Share One Sphere Rule
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0007
governing_prds:
- PRD-0016
governing_stories:
- US-0056
target_bc: board_state
target_release: 0.9.0
---
# TASK-0733: Square-Grid AoE Origin Sits on the Cell Centre and AoE and Spell Bloom Share One Sphere Rule

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
On square grids the AoE origin sits on the cell corner, not the cell centre. The spell bloom uses a second sphere rule. The two disagree on which cells are hit.

## Problem Statement
- `services/board_state/src/board_state/aoe.py:127` and `:161`: for `grid_type="square"` the origin is `origin_x * 5.0, origin_y * 5.0`. Cell centres are `(x + 0.5) * 5.0`. The hex branch subtracts 0.5 and gets the centre.
- Measured by the audit: a 5 ft sphere on cell (5,5) returns `(4,4) (4,5) (5,4) (5,5)`. Centred on the cell it returns `(4,5) (5,4) (5,5) (5,6) (6,5)`.
- `services/board_state/src/board_state/rules.py:~110-135` (`compute_spell_vfx_impact`) uses integer cell distance with `(radius_cells + 0.5) ** 2`. For a 20 ft radius from (5,5) it returns 69 cells. The template returns 52.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0007.
- `docs/how-to/interact-with-radial-action-menu-and-aoe-templates.md` and `docs/how-to/trigger-kinetic-spell-vfx-and-particles.md`. Update both with the final rule.
- US-0056 sets the intended behaviour. Confirm the origin rule against its scenarios before the change. If the story is silent, state the cell-centre rule in the story and the how-to.

## Product & User Story References
- PRD-0016
- US-0056

## Detailed Specification & Implementation Plan
1. Add `board_state/geometry/` that owns cell-centre conversion and sphere, cone, line, and cube containment in feet.
2. `aoe.py`, `rules.compute_spell_vfx_impact`, and `spells.cast_spell` call it. Remove the square-grid corner origin.
3. Move `BoardWebSocketManager` out of `preview.py` into `board_state/realtime.py` so route maths and sockets are separate. Update the four importing routers directly.
4. Write the unit tests per grid type first (square and hex).

## Frontdoor Blackbox Test Plan
- `POST /api/v1/boards/{id}/aoe/evaluate` with a fixed origin and radius. Assert `affected_cells`.
- `POST /api/v1/boards/{id}/spell-vfx` with the same shape. Assert the same cell set.

## Definition of Done
- One module owns sphere containment. A test asserts the AoE and bloom cell sets are equal for the same input.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: high
- Source audits: `board-character-forge.md (F1, F10 in part)`
