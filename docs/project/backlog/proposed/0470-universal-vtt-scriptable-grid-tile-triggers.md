---
id: '0470'
title: Universal VTT Scriptable Grid Tile Triggers and Activation Event Pipeline
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0005
- TASK-0007
- TASK-0057
- TASK-0173
governing_adrs:
- ADR-0006
- ADR-0007
- ADR-0010
governing_prds:
- PRD-0009
- PRD-0022
governing_stories:
- US-0033
target_release: 0.9.0
---

# TASK-0470: Universal VTT Scriptable Grid Tile Triggers and Activation Event Pipeline

## Status
Proposed

## Summary
Extend `services/board_state` and `libs/runefoble_events` with scriptable grid tile triggers (teleporters, pressure plates, sliding hazards, falling pits, and narrative zone triggers). Ingest scriptable tile trigger configurations from Universal VTT (`.dd2vtt` / `.uvtt`) metadata and coordinate rules. When board tokens enter or traverse triggered cells, evaluate trigger activation policies (creature size, passive perception, elevation, elevation delta) and publish standard `TileTriggerActivated` CloudEvents over Redis Streams, applying spatial effects (token translation, hazard conditions) directly to `BoardStateAggregate`.

## Problem Statement
Universal VTT importation (`TASK-0057`, `TASK-0173`) currently extracts wall occlusions, portals, doors, and ambient lighting, but does not support scriptable tile triggers specified in PRD-0022 and US-0033. Homebrew creators and DMs cannot configure dynamic battlemap hazards (e.g. arcane teleportation runes, trap doors, sliding ice sheets, narrative trigger zones) without manual DM intervention during live play. Furthermore, no standard domain event (`TileTriggerActivated`) is broadcast when tokens step onto triggered coordinates, leaving The Watcher copilot and audio soundscapes unaware of physical map hazards.

## Governing Architecture & ADRs
- **ADR-0006: Redis Streams Event Bus**: Publishing `TileTriggerActivated` CloudEvents on the `runefoble.board.triggers` topic for reactive game subsystems.
- **ADR-0007: Real-Time Voice and Board Synchronization**: Sub-500ms kinematic token position updates when teleporter tiles activate.
- **ADR-0010: Eventsource Aggregate Pattern**: Handling tile trigger creation, editing, and activation inside `BoardStateAggregate`.

## Product & User Story References
- [`prd-0009-procedural-battlemap-and-token-asset-generation.md`](../../product/accepted/prd-0009-procedural-battlemap-and-token-asset-generation.md)
- [`prd-0022-extensible-modder-platform-and-mcp-registry.md`](../../product/accepted/prd-0022-extensible-modder-platform-and-mcp-registry.md)
- [`us-0033-universal-vtt-map-importer-and-scriptable-tiles.md`](../../user_stories/accepted/us-0033-universal-vtt-map-importer-and-scriptable-tiles.md)

## Scope of Work
1. **Domain Events & Schemas (`libs/runefoble_events/src/runefoble_events/board.py`)**:
   - Register `TileTriggerConfigured` and `TileTriggerActivated` CloudEvents with schemas containing `session_id`, `trigger_id`, `x`, `y`, `trigger_type` (`teleport`, `hazard`, `narrative`, `trap`), `target_x`, `target_y`, `dc`, `damage_dice`, and `narrative_cue`.
2. **Board Aggregate Tile Trigger Handlers (`services/board_state/src/board_state/domain/triggers.py`)**:
   - Implement `TileTrigger` entity and trigger evaluation engine inside `BoardStateAggregate`.
   - On `move_token`, check if token trajectory intersects triggered coordinates and evaluate triggering criteria.
   - For teleporters, mutate token position to target coordinates and record trigger activation history.
3. **Universal VTT Scriptable Tile Ingestion (`services/board_state/src/board_state/parsers/uvtt_triggers.py`)**:
   - Parse custom script annotations and tile portal objects from `.dd2vtt` metadata into board trigger definitions (< 130 lines).
4. **Tile Triggers APIRouter (`services/board_state/src/board_state/routers/triggers.py`)**:
   - Expose `GET /api/v1/board/{id}/triggers`, `POST /api/v1/board/{id}/triggers`, and `DELETE /api/v1/board/{id}/triggers/{trigger_id}` with SpiceDB Zanzibar authorization checks.

## Definition of Done
1. `libs/runefoble_events` defines `TileTriggerConfigured` and `TileTriggerActivated` events registered with `@register_event`.
2. `services/board_state` evaluates tile triggers during token moves and updates token coordinates on teleportation triggers.
3. Universal VTT parser extracts and registers tile trigger definitions from UVTT metadata.
4. All source files strictly conform to Hard Invariant 6 (< 500 lines per file).
5. Passes `uv run pytest services/board_state/tests/` and lint checks.
