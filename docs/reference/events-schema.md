# Reference: Events Schema

All platform events inherit from `BaseRunefobleEvent` and include:
- `id` (UUIDv4)
- `timestamp` (ISO8601 UTC)
- `campaign_id` (UUIDv4)
- `session_id` (UUIDv4)
- `event_type` (String)

## Event Registry

### `player.spoke` (`PlayerSpokeEvent`)
Emitted when spoken audio is transcribed.
- `speaker_id`: String
- `speaker_name`: String
- `transcript`: String
- `is_whisper`: Boolean
- `target_character_id`: Optional[String]

### `watcher.narration` (`WatcherNarrationEvent`)
Emitted when The Watcher speaks as Game Master or provides environmental description.
- `narrative_text`: String
- `tone`: String (e.g. "mysterious", "suspenseful", "triumphant")
- `audio_stream_url`: Optional[String]
- `applied_board_mutations`: List[Dict]

### `board.move` (`BoardMoveEvent`)
Emitted when a token changes spatial coordinates on the grid.
- `token_id`: String
- `character_name`: String
- `from_x`: Integer, `from_y`: Integer
- `to_x`: Integer, `to_y`: Integer
- `initiated_by`: "player" | "the_watcher" | "stand_in"

### `game.dice_roll` (`DiceRollEvent`)
Emitted when dice are rolled.
- `roller_name`: String
- `dice_notation`: String (e.g., "1d20+3")
- `individual_rolls`: List[Integer]
- `modifier`: Integer
- `total`: Integer
- `reason`: String

### `session.penalty_applied` (`SessionPenaltyEvent`)
Emitted when an absent player's character is inflicted with a session miss cost.
- `character_id`: String
- `character_name`: String
- `penalty_type`: "drunk" | "foolishness" | "cowardice" | "greed" | "curse"
- `description`: String
- `imposed_by`: "human_dm" | "the_watcher"
