---
id: '0704'
title: Forged Battlemap Reaches Board State
status: Refined
created: 2026-11-17
dependencies:
- TASK-0579
governing_adrs:
- ADR-0006
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: board_state
target_release: 0.9.0
---
# TASK-0704: Forged Battlemap Reaches Board State

## Status
Refined. Slice of TASK-0579 (Follow-ups item 3).

## Summary
`BattlemapForged` is published by asset_forge, but board_state does not consume it, so a forged map never becomes board geometry.

## Problem Statement
- No board_state subscriber or route handles `BattlemapForged`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0006, ADR-0015.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add a supervised board_state consumer (docs/how-to/run-supervised-redis-stream-consumers.md) that applies walls and hazards from the event.
2. Use the service credential for any cross-service call (ADR-0015 e).

## Frontdoor Blackbox Test Plan
- Forge a battlemap through the asset_forge public route. Read the board geometry through the board_state public route. Assert walls and hazards match.

## Definition of Done
- A forged battlemap appears on the board through public routes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `work/0579.md`

## Orchestrator Addenda (2026-11-17, refactor-r1)

- TASK-0704 (forged battlemap reaches board_state): append "board_state owns the single obstacle rule and the hazard damage table (see TASK-0734). asset_forge must not return `obstacle_tokens` or `damage_dice`: `asset_forge/geometry.py:21-47` makes obstacles from pillar walls only (`Obstacle Wall (x,y)`), while `board_state` `import_uvtt_map` and `rules.extract_wall_obstacles` use every wall endpoint (`wall-obs-N`). The forge returns layout only (wall segments, hazard types, doors, grid). Add a payload assertion to `tests/test_blackbox_asset_forge_generation.py`."
