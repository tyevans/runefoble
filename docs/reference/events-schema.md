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
- **`SessionStarted`**: Emitted when the session transitions from lobby to active combat/exploration.
  - `started_at_turn`: Integer (default 1)
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
- **`AbsencePenaltyApplied`**: Emitted when an absent player's character is inflicted with a session miss penalty.
  - `penalty_type`: "drunk" | "foolishness" | "cowardice" | "greed" | "curse"
  - `description`: String
  - `imposed_by`: "human_dm" | "the_watcher"
- **`AbsencePenaltyCleared`**: Emitted when an absence penalty is redeemed.
  - `penalty_type`: String

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
- **`StandInActionDecided`**: Emitted when the AI stand-in acts on behalf of an absent player.
  - `character_name`: String
  - `action_type`: String
  - `dialogue`: String
  - `penalties_applied`: List[String]
- **`DiceRolled`**: Emitted when dice are rolled.
  - `roller_name`: String
  - `dice_notation`: String
  - `individual_rolls`: List[Integer]
  - `modifier`: Integer
  - `total`: Integer
  - `reason`: String
