---
id: 0013
title: Autonomous DM Session & Scene Orchestration Engine
status: Complete
created: 2026-09-25
completed: 2026-09-26
dependencies: [TASK-0002, TASK-0003, TASK-0010, TASK-0012]
governing_adrs: [ADR-0002, ADR-0004, ADR-0006, ADR-0007, ADR-0011, ADR-0012]
target_release: 0.1.0
---

# TASK-0013 — Autonomous DM Session & Scene Orchestration Engine

## Status
Complete

## Summary
Implemented the autonomous Game Master orchestration engine within The Watcher (US-0007, PRD-0001). The engine autonomously sets scene atmospheres, balances and spawns tactical encounters with monster tokens, and adjudicates intelligent NPC/monster tactics during combat rounds. The frontend provides a Bauhaus-styled `<runefoble-autonomous-dm>` control component allowing players to trigger scene generation, encounter spawning, and automated NPC turns without requiring human DM preparation.

## Scope & Key Changes
1. **Domain Events (`libs/runefoble_events/events.py`, `__init__.py`)**:
   - `SceneAtmosphereSet`: `session_id`, `scene_id`, `location_name`, `lighting`, `mood`, `description`, `ambient_audio_prompt` registered with `@register_event("runefoble.events.scene.atmosphere_set")`.
   - `EncounterSpawned`: `session_id`, `encounter_id`, `encounter_name`, `threat_level`, `monsters`, `tactical_objective` registered with `@register_event("runefoble.events.encounter.spawned")`.
   - `AutonomousActionResolved`: `session_id`, `actor_name`, `action_type`, `target_name`, `narrative`, `hp_impact` registered with `@register_event("runefoble.events.encounter.action_resolved")`.
   - Exported in `__all__` across `events.py` and `__init__.py` with full CloudEvents 1.0 serialization and event registry support.
2. **Autonomous DM Logic (`services/the_watcher/src/the_watcher/autonomous_dm.py`)**:
   - `AutonomousDMEngine` class implementing dynamic scene generation across cataloged presets (`dungeon`, `crypt`, `tavern`, `forest`, `dragon_lair`) and procedural fallbacks.
   - Challenge rating (CR) monster generation and encounter balancing across level tiers and threat levels (`easy`, `medium`, `hard`, `deadly`).
   - Tactical NPC decision trees: targeting lowest HP opponents, executing low-HP targets, spellcasting for caster roles, charging in round 1, and standard tactical melee strikes.
   - Maintained under 250 lines (Hard Invariant 6 <400 lines).
3. **The Watcher Endpoints (`services/the_watcher/src/the_watcher/main.py`, `models.py`)**:
   - `POST /api/v1/watcher/scenes/generate` accepting `SceneGenerateRequest`.
   - `POST /api/v1/watcher/encounters/spawn` accepting `EncounterSpawnRequest`.
   - `POST /api/v1/watcher/encounters/npc-turn` accepting `NpcTurnRequest`.
   - Events published over Redis Streams to `STREAM_WATCHER`.
   - Maintained under 465 lines (Hard Invariant 6 <500 lines).
4. **Frontend Lit Component & Storybook (`frontend/src/components/runefoble-autonomous-dm.ts`, `frontend/src/stories/autonomous-dm.stories.ts`)**:
   - Bauhaus-styled `<runefoble-autonomous-dm>` component with controls, mood indicators, active threat monitors, and action dispatchers.
   - Storybook stories for `CryptAmbush`, `SuspensefulTavern`, and `DragonLair`.
   - Exported in `frontend/src/index.ts` and registered in `frontend/src/runefoble-app.ts`.
5. **Tests (`tests/test_autonomous_dm.py`)**:
   - Unit and integration tests for scene generation, encounter calculation, NPC combat decisions, event publishing, and API endpoints.

## Verification
- `uv run pytest tests/test_autonomous_dm.py`: 16/16 passed.
- `uv run pytest`: 112/112 passed across monorepo.
- `uv run ruff check .`: Clean, 0 errors.
- `cd frontend && pnpm run build`: Clean TypeScript check and production bundle.
