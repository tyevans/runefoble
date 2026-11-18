# Reference: Events Schema & Event Sourcing

All domain events in Runefoble subclass `eventsource.domain.event.DomainEvent` via `BaseRunefobleEvent` in `libs/runefoble_events`.

## Base Event Envelope

Every event includes standard metadata managed by `eventsource-py`:
- `event_id`: UUIDv4
- `event_type`: String (wire identifier: the class `event_type` value, or the class name when none is set; see [Event Identifiers](event-identifiers.md))
- `event_version`: Integer (schema migration version)
- `occurred_at`: UTC Datetime
- `aggregate_id`: UUIDv4
- `aggregate_type`: String (e.g. `GameSession`, `BoardState`, `CharacterSheet`)
- `aggregate_version`: Integer (version of aggregate after applying event)
- `tenant_id`: Optional UUID
- `actor_id`: Optional String
- `correlation_id`: Optional UUID
- `causation_id`: Optional UUID
- `metadata`: Dict[str, Any]

### CloudEvents 1.0 Export
Any domain event can be converted to an external CloudEvent payload via `.to_cloudevent_dict()`.

---

## Modular Package Architecture

The `libs/runefoble_events` package organizes domain event definitions and re-exports into discrete, single-responsibility category modules governed by Hard Invariant 6 (< 150 lines per submodule, < 80 lines per aggregator facade):

- **Aggregator Facades**:
  - `runefoble_events`: Package root. It exports the base event types only: `BaseRunefobleEvent`, `DomainEvent` and `register_event`.
  - `runefoble_events.events`: Subpackage aggregator facade providing unified access to domain event models.
- **Domain Category Submodules (`runefoble_events.events.*`)**:
  - `session_events.py`: Game session lifecycle, turn sequencing, initiative rolls, combat rounds, and reaction pause/triggers.
  - `board_events.py`: Tactical board grid initialization, token kinematics, fog-of-war, spell AoE templates, and secret traps.
  - `narrative_events.py`: The Watcher DM narrations, intent parsing, candidate ghost previews, story recaps, and AI stand-ins.
  - `world_events.py`: West Marches persistent frontier, trade caravans, haven settlements, faction agendas, and lore knowledge.
  - `character_events.py`: Character progression, inventory slots, conditions, alchemical crafting mishaps, and tavern minigames.
  - `media_events.py`: Low-latency voice duplex, audio DSP modulation, dynamic soundscapes, procedural asset forge, and audience polls.
  - `platform_events.py`: Core event base models, privacy-preserving combat analytics, compendium indexing, mercenary contracts, and dynamic MCP tools.
- **The Watcher Domain Events (`runefoble_events.watcher_events.*` and `runefoble_events.watcher` facade)**:
  - `watcher.py`: Public import module for the Watcher events.
  - `watcher_events/narrative.py`: Speech transcription (`PlayerSpokeEvent`), parsed intent (`SpeechIntentParsed`), narration (`WatcherNarrationGenerated`), absentee recaps, and private DM whispers (< 120 lines).
  - `watcher_events/combat.py`: Dice roll telemetry (`DiceRolled`), autonomous combat encounters, candidate ghost previews, combat reaction interrupts, and trap triggers (< 150 lines).
  - `watcher_events/actions.py`: The Watcher DM copilot proposal, veto, approval, modification, and compound action disambiguation (< 150 lines).
  - `watcher_events/factions.py`: Autonomous NPC faction agendas, progress advances, geopolitical territory shifts, and world ticks (< 150 lines).
- **Board Domain Events (`runefoble_events.board_events.*` and `runefoble_events.board` facade)**:
  - `board.py`: Public import module for the board events.
  - `board_events/token.py`: Tactical token placement, movement, actions, knockback impulses (`TokenKnockbackApplied`), and elevation changes (`ElevationChanged`) (< 100 lines).
  - `board_events/fog.py`: Fog-of-war reveal (`FogOfWarRevealed` / `FogRevealed`), shroud reset (`FogOfWarShrouded` / `ShroudReset`), and complete visibility mask updates (`VisibilityMaskUpdated`) (< 80 lines).
  - `board_events/templates.py`: Geometric AoE spell template positioning and removal (`AoETemplatePlaced`, `AoETemplateRemoved`) (< 80 lines).
  - `board_events/lighting.py`: Dynamic point lights and interactive doors (`BoardLightSourcePlacedEvent`, `BoardDoorToggledEvent`) (< 80 lines).
  - `board_events/terrain.py`: Board grid initialization, cell elevation / hazard modifications, and Universal VTT map imports (< 80 lines).
  - `board_events/physics.py`: Rigid-body physical collisions and 3D tumbling dice resting telemetry (< 80 lines).
  - `board_events/spells.py`: Kinetic spell launches, area-of-effect blooms, WebGL particle VFX completion, and decal decay (< 120 lines).

---

## Event Identifiers

[Event Identifiers](event-identifiers.md) lists every registered domain event. The page is generated from the `runefoble_events` registry by `scripts/generate_event_catalogue.py`. Its identifier column is the `event_type` that the code emits. Use it as the source of truth for wire names.

## Catalogue Pages

- [Gameplay](events-catalog-gameplay.md): GameSession and BoardState events.
- [Characters and The Watcher](events-catalog-characters-watcher.md): CharacterSheet events, The Watcher and gameplay stream events.
- [World, Voice and Media](events-catalog-world-media.md): RegionalUnrest, VoiceRoom, Asset, Lore, Atlas, Compendium, Soundscape and Audience events.
- [Platform and Campaign Services](events-catalog-platform.md): Campaign Analytics, Downtime, West Marches, Campaign lifecycle, Settlement, Establishment, NPC worker, Mercenary bounty and Dynamic tool events.

Each catalogue section lists the fields of its events. Field names come from the event classes.

## Known Drift

These sections do not yet match the code. Each item lists its owner. Update a section when its owner lands the code fix.

- **CharacterSheet events**: `StandInPolicyUpdated` payload fields differ from the class in `libs/runefoble_events/src/runefoble_events/character.py`. Items `ItemAddedToInventory`, `ItemRemovedFromInventory`, `EquipmentSlotUpdated`, `ConditionApplied` and `ConditionRemoved` are not yet in the catalogue. Audit: W1 character-sheet F6. Owner: no task yet.
- **Payload drift**: `CharacterControlTransferred` and the hot-swap event payloads differ from the code. Audit: W1 game-session F16. Owner: no task yet.
- **Orphan producers and consumers**: 17 registered classes have no producer and 38 have no code consumer. Some stream names in the catalogue have no producer or consumer. The Watcher world stream is `runefoble.events.world`. Audit: W3 event wiring. Owner: TASK-0579 (partly complete; see the task file).
- **Dead read projections**: `PresenceProjection` and `SessionReadProjection` are never started in production. See [Redis Streams Event Bus](redis-streams-event-bus.md#in-memory-session-projections). Owner: TASK-0567.
- **Code aliases**: the `X = XEvent` aliases are removed. Some `X = Y` aliases remain in code (for example `FogRevealed`, `ShroudReset`, `BoardMapImported`, `BoardMoveEvent`, `GameSessionStarted`). They are not part of TASK-0487. Owner: follow-up task needed.
