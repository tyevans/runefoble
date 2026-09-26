# Reference: Events Schema & Event Sourcing

All domain events in Runefoble subclass `eventsource.domain.event.DomainEvent` via `BaseRunefobleEvent` in `libs/runefoble_events`.

## Base Event Envelope

Every event includes standard metadata managed by `eventsource-py`:
- `event_id`: UUIDv4
- `event_type`: String (automatically derived from class name)
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

## Domain Event Catalog

### GameSession Events (`aggregate_type: GameSession`)

- **`SessionCreated`**: Emitted when a new session aggregate is initialized.
  - `title`: String
  - `dm_id`: String
  - `created_by`: String
- **`SessionStarted`** (alias: `GameSessionStarted`): Emitted when the session transitions from lobby to active combat/exploration.
  - `started_at_turn`: Integer (default 1)
- **`ParticipantJoined`**: Emitted when a user joins the session in a specific role (player, spectator, gm).
  - `session_id`: UUID | str
  - `campaign_id`: UUID | str
  - `user_id`: String
  - `role`: String (default "player")
  - `character_id`: Optional[UUID | str]
- **`PlayerJoinedSession`**: Emitted when a participant connects with an assigned character.
  - `player_id`: String
  - `character_id`: UUID
  - `character_name`: String
  - `character_class`: String
- **`PlayerLeftSession`**: Emitted when a participant disconnects or misses game night.
  - `player_id`: String
  - `reason`: String
- **`TurnAdvanced`**: Emitted when the initiative turn counter advances.
  - `previous_turn`: Integer
  - `new_turn`: Integer
  - `active_character_id`: Optional[UUID]
- **`CombatEncounterStarted`**: Emitted when a combat encounter is initiated.
  - `session_id`: Optional[UUID | str]
  - `round_number`: Integer (default 1)
  - `combatants`: List[Dict[str, Any]]
- **`InitiativeRolled`**: Emitted when a participant or NPC submits an initiative score.
  - `session_id`: Optional[UUID | str]
  - `combatant_id`: String
  - `combatant_name`: String
  - `initiative_score`: Float / Integer
  - `is_npc`: Boolean (default False)
- **`InitiativeTurnAdvanced`**: Emitted when the combat turn cycles to the next combatant.
  - `session_id`: Optional[UUID | str]
  - `round_number`: Integer
  - `active_combatant_id`: String
  - `turn_seconds_remaining`: Integer (default 60)
- **`CombatEncounterEnded`**: Emitted when combat concludes.
  - `session_id`: Optional[UUID | str]
  - `total_rounds`: Integer
- **`SessionEnded`**: Emitted when the session concludes.
  - `summary`: String

### BoardState Events (`aggregate_type: BoardState`)

- **`BoardGridInitialized`**: Emitted when grid dimensions and cell sizes are established.
  - `width`: Integer
  - `height`: Integer
  - `cell_size_px`: Integer
  - `grid_type`: "square" | "hex"
- **`TokenPlaced`**: Emitted when a token is added to the grid.
  - `token_id`: String / UUID
  - `name`: String
  - `token_type`: "pc" | "monster" | "npc" | "obstacle"
  - `x`: Integer, `y`: Integer
  - `hp`: Optional[Integer]
  - `is_friendly`: Boolean
- **`TokenMoved`**: Emitted when a token traverses grid coordinates.
  - `token_id`: String
  - `name`: String
  - `from_x`: Integer, `from_y`: Integer
  - `to_x`: Integer, `to_y`: Integer
  - `initiated_by`: "player" | "the_watcher" | "stand_in"
- **`TokenRemoved`**: Emitted when a token leaves the board.
  - `token_id`: String
  - `reason`: String ("defeated", "retreated", "teleported")
- **`FogOfWarRevealed`**: Emitted when a token's vision reveals uncharted grid cells.
  - `revealed_cells`: List[List[Integer]]
  - `revealed_by_token_id`: Optional[String]
- **`TerrainCellModified`**: Emitted when a tactical grid cell's elevation, terrain difficulty, or hazard is modified (`runefoble.events.board.terrain_modified`).
  - `session_id`: String
  - `board_id`: String
  - `x`: Integer, `y`: Integer
  - `elevation`: Integer (default 0)
  - `terrain_type`: String ("normal", "difficult")
  - `hazard`: Optional[String] (e.g. "lava", "fire", "acid", "spikes", "poison")
- **`TokenHazardTriggered`**: Emitted when a token enters or traverses an environmental hazard cell (`runefoble.events.board.hazard_triggered`).
  - `session_id`: String
  - `board_id`: String
  - `token_id`: String
  - `hazard_type`: String
  - `damage_dice`: String (e.g. "2d10", "1d6")

### CharacterSheet Events (`aggregate_type: CharacterSheet`)

- **`CharacterCreated`**: Emitted when a new character is forged.
  - `name`: String
  - `character_class`: String
  - `max_hp`: Integer, `current_hp`: Integer
  - `player_id`: Optional[String]
  - `personality_traits`: List[String]
- **`CharacterHealthChanged`**: Emitted when hit points change from damage or healing.
  - `delta`: Integer
  - `current_hp`: Integer, `max_hp`: Integer
  - `source`: String
- **`AbsencePenaltyApplied`** (alias: `PlayerAbsenteePenalized`): Emitted when an absent player's character is inflicted with a session miss penalty.
  - `penalty_type`: "drunk" | "foolishness" | "cowardice" | "greed" | "curse"
  - `description`: String
  - `imposed_by`: "human_dm" | "the_watcher"
- **`AbsencePenaltyCleared`**: Emitted when an absence penalty is redeemed.
  - `penalty_type`: String
- **`CharacterLeveledUp`**: Emitted when a character advances in level, gaining hit points and spell slots (`runefoble.events.character.leveled_up`).
  - `session_id`: String
  - `character_id`: String
  - `new_level`: Integer
  - `max_hp_increase`: Integer
  - `spell_slots`: Mapping[Integer, Integer]
- **`SpellPrepared`**: Emitted when a character prepares a spell into active memory (`runefoble.events.character.spell_prepared`).
  - `session_id`: String
  - `character_id`: String
  - `spell_name`: String
  - `spell_level`: Integer
- **`SpellSlotExpended`**: Emitted when a spell is cast and a spell slot is consumed (`runefoble.events.character.spell_slot_expended`).
  - `session_id`: String
  - `character_id`: String
  - `spell_name`: String
  - `slot_level_used`: Integer
  - `remaining_slots`: Integer

### The Watcher & Gameplay Stream Events

- **`PlayerSpokeEvent`**: Emitted when natural player speech is captured and transcribed.
  - `speaker_id`: String
  - `speaker_name`: String
  - `transcript`: String
  - `is_whisper`: Boolean
- **`SpeechIntentParsed`**: Emitted by The Watcher speech parsing pipeline.
  - `speaker_name`: String
  - `action_type`: String ("attack", "cast_spell", "move", "dialogue")
  - `target`: Optional[String]
  - `confidence`: Float
  - `flavor_text`: String
- **`WatcherNarrationGenerated`**: Emitted when The Watcher provides scene description.
  - `narrative_text`: String
  - `tone`: String
  - `sensory_details`: List[String]
  - `suggested_prompts`: List[String]
- **`StandInActionDecided`** (alias: `StandInTurnExecuted`): Emitted when the AI stand-in acts on behalf of an absent player.
  - `character_name`: String
  - `action_type`: String
  - `dialogue`: String
  - `penalties_applied`: List[String]
- **`DiceRolled`**: Emitted when dice are rolled (`runefoble.events.dice.rolled`).
  - `session_id`: String
  - `roller_id`: String
  - `roller_name`: String
  - `formula`: String
  - `total`: Integer
  - `rolls`: List[Integer]
  - `is_crit`: Boolean (default False)
  - `is_fumble`: Boolean (default False)
- **`AbsenteeRecapGenerated`**: Emitted when The Watcher generates a session chronicle and audio-ready recap for a returning absent player (`runefoble.events.recap.generated`).
  - `session_id`: String
  - `character_id`: String
  - `character_name`: String
  - `stand_in_persona`: String
  - `penalties`: List[String]
  - `narrative_summary`: String
  - `highlights`: List[String]
  - `audio_url`: Optional[String]
  - `hp_delta`: Integer
  - `items_acquired`: List[String]
- **`SceneAtmosphereSet`**: Emitted when The Watcher autonomously establishes scene lighting, sensory atmosphere, and background audio prompts (`runefoble.events.scene.atmosphere_set`).
  - `session_id`: String
  - `scene_id`: String
  - `location_name`: String
  - `lighting`: String
  - `mood`: String
  - `description`: String
  - `ambient_audio_prompt`: String
- **`EncounterSpawned`**: Emitted when The Watcher calculates CR balance and spawns an encounter with monster tokens (`runefoble.events.encounter.spawned`).
  - `session_id`: String
  - `encounter_id`: String
  - `encounter_name`: String
  - `threat_level`: String ("easy", "medium", "hard", "deadly")
  - `monsters`: List[Dict[String, Any]]
  - `tactical_objective`: String
- **`AutonomousActionResolved`**: Emitted when an autonomous monster or NPC resolves tactical combat decisions and impacts target HP (`runefoble.events.encounter.action_resolved`).
  - `session_id`: String
  - `actor_name`: String
  - `action_type`: String ("cast_spell", "charge_attack", "melee_strike", "execute_strike", "search")
  - `target_name`: String
  - `narrative`: String
  - `hp_impact`: Integer
- **`SpectatorSessionConnected`**: Emitted when a live stream spectator or OBS overlay source connects to a campaign session (`runefoble.events.spectator.connected`).
  - `session_id`: String
  - `viewer_id`: String
  - `viewer_name`: String
  - `connected_at`: String (ISO-8601 UTC timestamp)
- **`VoiceAudioConditioned`**: Emitted when real-time dynamic DSP audio conditioning or filter presets are applied to speech (`runefoble.events.voice.audio_conditioned`).
  - `session_id`: String
  - `speaker_id`: String
  - `speaker_name`: String
  - `filters_applied`: List[String]
  - `latency_ms`: Float
  - `audio_bytes_length`: Integer

### VoiceRoom Events (`aggregate_type: VoiceRoom`)

- **`VoicePeerJoined`**: Emitted when an audio peer connects and joins the session WebRTC voice room (`runefoble.events.voice.peer_joined`).
  - `session_id`: String
  - `peer_id`: String
  - `user_id`: String
  - `role`: String ("player", "dungeon_master", "spectator")
  - `joined_at`: String (ISO-8601 UTC timestamp)
- **`VoicePeerLeft`**: Emitted when an audio peer leaves or is kicked/disconnected from the voice room (`runefoble.events.voice.peer_left`).
  - `session_id`: String
  - `peer_id`: String
  - `reason`: String ("disconnected", "user_exit", "kicked_by_dm")
- **`VoicePeerMuteToggled`**: Emitted when an audio peer toggles microphone mute state (`runefoble.events.voice.mute_toggled`).
  - `session_id`: String
  - `peer_id`: String
  - `is_muted`: Boolean


### Asset Storage Events (`aggregate_type: Asset`)

- **`AssetUploaded`**: Emitted when a media asset (character avatar, tactical battlemap, or audio soundscape) is stored in Silo S3 (`runefoble.events.asset.uploaded`).
  - `asset_id`: String
  - `bucket`: String
  - `object_key`: String
  - `content_type`: String
  - `byte_size`: Integer
  - `owner_id`: String
  - `url`: String
- **`AssetDeleted`**: Emitted when an asset is deleted from object storage (`runefoble.events.asset.deleted`).
  - `asset_id`: String
  - `bucket`: String
  - `object_key`: String
  - `deleted_by`: String
