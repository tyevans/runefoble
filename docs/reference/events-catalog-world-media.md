# Reference: Events Catalog: World, Voice and Media

Part of the [Events Schema](events-schema.md). Each event identifier in this page is listed in [Event Identifiers](event-identifiers.md).

## Domain Event Catalog

### RegionalUnrest & Turf War Events (`aggregate_type: RegionalUnrest`)

- **`FactionSkirmishResolvedEvent`** (alias: `FactionSkirmishResolved`): Emitted when a tactical boundary clash between two factions resolves (`runefoble.events.watcher.faction_skirmish_resolved`).
  - `skirmish_id`: String
  - `campaign_id`: String
  - `region_id`: String
  - `contested_node`: String
  - `attacker_faction_id`: String
  - `defender_faction_id`: String
  - `winning_faction_id`: String
  - `is_stalemate`: Boolean
  - `attacker_casualties`: Integer
  - `defender_casualties`: Integer
  - `territory_captured`: Boolean
  - `unrest_delta`: Integer
  - `narrative`: String
- **`FactionTerritoryCapturedEvent`** (alias: `FactionTerritoryCaptured`): Emitted when contested territory or an outpost changes faction ownership (`runefoble.events.watcher.faction_territory_captured`).
  - `campaign_id`: String
  - `region_id`: String
  - `previous_controlling_faction_id`: Optional[String]
  - `new_controlling_faction_id`: String
  - `territory_node`: String
  - `unrest_delta`: Integer
- **`RegionalUnrestEscalatedEvent`** (alias: `RegionalUnrestEscalated`): Emitted when regional instability, guard alert levels, or economic friction escalate (`runefoble.events.watcher.regional_unrest_escalated`).
  - `campaign_id`: String
  - `region_id`: String
  - `previous_unrest`: Integer
  - `current_unrest`: Integer
  - `unrest_delta`: Integer
  - `alert_level`: String ("calm", "guarded", "elevated", "high", "critical")
  - `security_level`: String ("standard", "patrolled", "heightened", "curfew", "martial_law")
  - `economic_friction`: Float (0.0 to 1.0)
  - `cause`: String

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
  - `reason`: String ("disconnected", "user_exit", "kicked_by_dm"). A graceful service restart (close `1012`) emits no `VoicePeerLeft`.
- **`VoicePeerMuteToggled`**: Emitted when an audio peer toggles microphone mute state (`runefoble.events.voice.mute_toggled`).
  - `session_id`: String
  - `peer_id`: String
  - `is_muted`: Boolean
- **`MobileCompanionConnected`**: Emitted when a mobile companion connects via the low-bandwidth gateway (`runefoble.events.voice.mobile_connected`).
  - `session_id`: String
  - `peer_id`: String
  - `user_id`: String
  - `device_type`: String ("mobile")
  - `audio_profile_tier`: String ("mobile_optimized")
  - `haptic_supported`: Boolean
  - `connected_at`: String (ISO-8601 UTC timestamp)
- **`MobileAudioProfileAdapted`**: Emitted when mobile companion audio adapts due to cellular network conditions (`runefoble.events.voice.profile_adapted`).
  - `session_id`: String
  - `peer_id`: String
  - `user_id`: String
  - `previous_tier`: String
  - `current_tier`: String
  - `sample_rate`: Integer (16000)
  - `bitrate_kbps`: Integer
  - `packet_loss`: Float
  - `reason`: String
- **`MobileHapticPingDispatched`**: Emitted when a haptic vibration pulse or lockscreen alert is dispatched to mobile (`runefoble.events.voice.haptic_ping`).
  - `session_id`: String
  - `recipient_id`: String
  - `alert_type`: String ("secret_whisper", "turn_alert", "critical_alert")
  - `vibration_pattern`: List[Integer] (e.g. `[200, 100, 200]`)
  - `whisper_content`: Optional[String]
  - `notification_title`: Optional[String]
  - `notification_body`: Optional[String]
  - `diegetic`: Boolean
  - `dispatched_at`: String (ISO-8601 UTC timestamp)
- **`VoiceSpeechInterrupted`**: Emitted when active TTS narration is interrupted by player speech / barge-in (`runefoble.events.voice.speech_interrupted`).
  - `session_id`: String
  - `speaker_id`: String
  - `speaker_name`: String
  - `timestamp`: Float (epoch timestamp)
  - `interrupted_at`: String (ISO-8601 UTC timestamp)
  - `remaining_narration_text`: Optional[String] (unspoken narration tail)
  - `original_text`: Optional[String]
  - `playback_duration_ms`: Float
  - `cutoff_position_ms`: Float
  - `reason`: String ("player_barge_in")
- **`VocalModulatorPresetAppliedEvent`**: Emitted when a DM applies an NPC vocal archetype preset or modulates live stream parameters (`runefoble.events.voice.modulator_preset_applied`).
  - `session_id`: String
  - `peer_id`: String
  - `preset_name`: String ("Ancient Dragon", "Goblin Skulker", "Celestial Spirit", "Robotic Construct", etc.)
  - `pitch_shift_semitones`: Float
  - `formant_shift`: Float
  - `resonance_hz`: Float
  - `octave_offset`: Float
  - `reverb_wet`: Float
  - `active_filters`: List[String]
  - `user_id`: String
  - `applied_at`: Float (epoch timestamp)
- **`VoiceFilterToggledEvent`**: Emitted when a live voice filter parameter or DSP node is toggled on/off (`runefoble.events.voice.filter_toggled`).
  - `session_id`: String
  - `peer_id`: String
  - `filter_name`: String
  - `enabled`: Boolean
  - `parameters`: Dict[String, Float]
  - `user_id`: String
  - `toggled_at`: Float (epoch timestamp)
- **`VoiceStreamQualityDegradedEvent`**: Emitted when RTCP receiver reports detect packet loss (>5%) or round-trip delay spikes (`runefoble.events.voice.stream_quality_degraded`).
  - `session_id`: String
  - `peer_id`: String
  - `user_id`: Optional[String]
  - `packet_loss`: Float (0.0 to 1.0)
  - `round_trip_time_ms`: Float
  - `jitter_ms`: Float
  - `severity`: String ("nominal", "degraded", "severe")
  - `detected_at`: String (ISO-8601 UTC timestamp)
- **`VoiceStreamCodecAdaptedEvent`**: Emitted when stream bitrate or Opus codec parameters are dynamically adjusted (<50 kbps 16kHz mono) (`runefoble.events.voice.stream_codec_adapted`).
  - `session_id`: String
  - `peer_id`: String
  - `user_id`: Optional[String]
  - `previous_bitrate_kbps`: Integer
  - `new_bitrate_kbps`: Integer
  - `sample_rate`: Integer (16000)
  - `channels`: Integer (1)
  - `complexity`: Integer (0 to 10)
  - `fec_enabled`: Boolean
  - `dtx_enabled`: Boolean
  - `codec_mode`: String ("standard", "mobile_optimized", "cellular_constrained", "ultra_low")
  - `reason`: String
  - `adapted_at`: String (ISO-8601 UTC timestamp)
- **`VoiceStreamQualityMeasured`**: Saved in the room aggregate for every RTCP receiver report. It is not published (`runefoble.events.voice.stream_quality_measured`).
  - `session_id`: String
  - `peer_id`: String
  - `user_id`: Optional[String]
  - `packet_loss`: Float (0.0 to 1.0)
  - `rtt_ms`: Float
  - `jitter_ms`: Float
  - `is_degraded`: Boolean
  - `severity`: String ("nominal", "degraded", "severe")
  - `detection_latency_ms`: Float
  - `measured_at`: String (ISO-8601 UTC timestamp)
- **`VoicePlaybackStarted`**: Saved in the room aggregate when TTS narration starts. It is not published (`runefoble.events.voice.playback_started`).
  - `session_id`: String
  - `playback_id`: String
  - `original_text`: String
  - `duration_ms`: Float
  - `started_at`: Float (epoch timestamp)
- **`VoicePlaybackAttenuated`**: Saved in the room aggregate when player speech starts a 20 ms soft fade of active TTS narration. It is not published (`runefoble.events.voice.playback_attenuated`).
  - `session_id`: String
  - `playback_id`: String
  - `speaker_id`: String
  - `speaker_name`: String
  - `cutoff_position_ms`: Float
  - `remaining_narration_text`: String
  - `fade_ms`: Float (20.0)
- **`VoicePlaybackStopped`**: Saved in the room aggregate when TTS narration ends. It is not published (`runefoble.events.voice.playback_stopped`).
  - `session_id`: String
  - `playback_id`: String
  - `reason`: String ("player_barge_in")
- **`NeuralSpeechBargeInDetectedEvent`**: Emitted when high-precision neural VAD detects vocalization onset during active TTS playback (`runefoble.events.voice.barge_in_detected`).
  - `session_id`: String
  - `speaker_id`: String
  - `speaker_name`: String
  - `onset_latency_ms`: Float (< 40ms)
  - `confidence`: Float
  - `rms_energy`: Float
  - `detected_at`: Float (epoch timestamp)
  - `reason`: String ("human_speech_barge_in")
- **`TTSStreamAttenuatedEvent`**: Emitted when active TTS playback is attenuated gracefully to silence with cosine crossfading (`runefoble.events.voice.tts_stream_attenuated`).
  - `session_id`: String
  - `stream_id`: String
  - `fade_duration_ms`: Float (10ms-30ms, default 20ms)
  - `attenuated_samples_count`: Integer
  - `peak_tail_amplitude`: Integer (<= 1)
  - `cutoff_position_ms`: Float
  - `remaining_text`: Optional[String]
  - `attenuated_at`: Float (epoch timestamp)
- **`EchoSuppressionEngagedEvent`**: Emitted when acoustic echo suppression is engaged on microphone stream (`runefoble.events.voice.echo_suppression_engaged`).
  - `session_id`: String
  - `speaker_id`: String
  - `erle_db`: Float
  - `attenuation_db`: Float
  - `engaged_at`: Float (epoch timestamp)
  - `is_double_talk`: Boolean
- **`AECBenchmarkCompletedEvent`**: Emitted when hardware AEC benchmark finishes validating ERLE > 35dB (`runefoble.events.voice.aec_benchmark_completed`).
  - `session_id`: String
  - `erle_db`: Float
  - `target_erle_db`: Float (default 35.0)
  - `passed`: Boolean
  - `double_talk_detected`: Boolean
  - `filter_length`: Integer
  - `completed_at`: Float (epoch timestamp)



### Asset Storage Events (`aggregate_type: Asset`)

- **`AssetUploaded`**: Emitted when a media asset (character avatar, tactical battlemap, or audio soundscape) is stored in Silo S3 (`runefoble.events.asset.uploaded`).
  - `asset_id`: String
  - `bucket`: String
  - `object_key`: String
  - `content_type`: String
  - `byte_size`: Integer
  - `owner_id`: String
- **`AssetDeleted`**: Emitted when an asset is deleted from object storage (`runefoble.events.asset.deleted`).
  - `asset_id`: String
  - `bucket`: String
  - `object_key`: String
  - `deleted_by`: String
- **`BattlemapForged`** (alias: `BattlemapCreated`): Emitted when a tactical battlemap is procedurally generated and stored in Silo S3 (`runefoble.events.asset.battlemap_forged`).
  - `asset_id`: String
  - `campaign_id`: Optional[UUID]
  - `session_id`: Optional[String]
  - `creator_id`: String
  - `prompt`: String
  - `image_url`: String
  - `width_cells`: Integer
  - `height_cells`: Integer
  - `cell_size_px`: Integer
  - `wall_segments_count`: Integer
  - `hazard_cells_count`: Integer
  - `doors_count`: Integer
  - `theme`: String
- **`TokenAssetForged`** (alias: `AssetGenerated`): Emitted when a character or creature token portrait is procedurally synthesized with alpha transparency (`runefoble.events.asset.token_forged`).
  - `asset_id`: String
  - `campaign_id`: Optional[UUID]
  - `creator_id`: String
  - `prompt`: String
  - `token_name`: String
  - `token_type`: String ("pc", "npc", "monster", "obstacle")
  - `image_url`: String
  - `crop_style`: String ("circular", "square", "hex")
  - `transparent_background`: Boolean
- **`PrintPdfForged`**: Emitted when a multi-page grid-calibrated battlemap PDF or standee sheet is exported (`runefoble.events.asset.print_pdf_forged`).
  - `asset_id`: String
  - `campaign_id`: Optional[UUID]
  - `session_id`: Optional[String]
  - `creator_id`: String
  - `total_pages`: Integer
  - `page_size`: String ("letter", "a4")
  - `grid_scale`: String ("1-inch")
  - `download_url`: String
- **`StlTokenForged`**: Emitted when a watertight 3D-printable miniature base or condition clip is forged (`runefoble.events.asset.stl_token_forged`).
  - `asset_id`: String
  - `campaign_id`: Optional[UUID]
  - `creator_id`: String
  - `diameter_mm`: Float
  - `height_mm`: Float
  - `facet_count`: Integer
  - `condition_label`: String
  - `download_url`: String

### LoreDocument Events (`aggregate_type: LoreDocument`)


- **`LoreDocumentIngested`**: Emitted when a new worldbuilding document is ingested (`LoreDocumentIngested`).
  - `document_id`: UUID
  - `campaign_id`: UUID
  - `title`: String
  - `content`: String
  - `is_secret`: Boolean (default False)
  - `author_id`: Optional[String]
  - `metadata`: Dict[str, Any]
- **`EntitiesExtracted`**: Emitted when entities and relationships are extracted via redstring (`EntitiesExtracted`).
  - `document_id`: UUID
  - `campaign_id`: UUID
  - `entities`: List[Dict[str, Any]]
  - `relationships`: List[Dict[str, Any]]
- **`AliasesConsolidated`**: Emitted when synonymous entity titles and aliases are consolidated into canonical nodes (`AliasesConsolidated`).
  - `campaign_id`: UUID
  - `canonical_entity_id`: UUID
  - `canonical_name`: String
  - `alias_entity_id`: UUID
  - `alias_name`: String
  - `reason`: String
- For schemas of `HandoutGenerated`, `WaxSealBroken`, and `RelicInspected`, see [`diegetic-handouts-and-relics-events.md`](diegetic-handouts-and-relics-events.md).

### Atlas & Party Codex Events (`aggregate_type: Atlas`, `Codex`)

- **`AtlasPinCreated`**: Emitted when a milestone pin is placed on the campaign world atlas (`AtlasPinCreated`).
  - `pin_id`: UUID
  - `campaign_id`: UUID
  - `title`: String
  - `layer`: String (continental, regional, municipal)
  - `coordinates`: Dict[str, float]
  - `description`: String
  - `era`: Optional[String]
  - `session_id`: Optional[String]
  - `linked_entity_ids`: List[String]
  - `created_by`: Optional[String]
  - `metadata`: Dict[str, Any]
- **`AtlasLayerToggled`**: Emitted when map layer visibility is toggled (`AtlasLayerToggled`).
  - `campaign_id`: UUID
  - `layer`: String
  - `is_visible`: Boolean
  - `toggled_by`: Optional[String]
- **`AtlasTerritoryUpdated`**: Emitted when territory polygon boundaries or ownership is defined (`AtlasTerritoryUpdated`).
  - `territory_id`: UUID
  - `campaign_id`: UUID
  - `name`: String
  - `layer`: String
  - `polygon_coordinates`: List[List[Float]]
  - `owner_faction`: String
  - `is_contested`: Boolean
  - `era`: Optional[String]
  - `metadata`: Dict[str, Any]
- **`CodexEntryPublished`**: Emitted when a collaborative party codex note is published with redstring links (`CodexEntryPublished`).
  - `entry_id`: UUID
  - `campaign_id`: UUID
  - `title`: String
  - `content`: String
  - `privacy`: String (private, party_shared, public)
  - `author_id`: String
  - `era`: Optional[String]
  - `tags`: List[String]
  - `linked_entity_ids`: List[String]
  - `metadata`: Dict[str, Any]
- **`CodexEntryUpdated`**: Emitted when codex content, tags, or privacy status are updated (`CodexEntryUpdated`).


### Campaign Lore Stream Topics

The Campaign Lore service publishes every event that its aggregates commit. The repository publishes each event to the stream named below, before the save returns. A failed publish returns HTTP 503, and the client retries. The mapping lives in `services/campaign_lore/src/campaign_lore/events.py`. An event with no mapping fails the save.

| Event | Stream |
|---|---|
| `LoreDocumentIngested` | `runefoble.events.lore.document_ingested` |
| `EntitiesExtracted` | `runefoble.events.lore.entities_extracted` |
| `AliasesConsolidated` | `runefoble.events.lore.aliases_consolidated` |
| `HandoutGenerated` | `runefoble.events.lore.handout_generated` |
| `WaxSealBroken` | `runefoble.events.lore.wax_seal_broken` |
| `InvisibleInkRevealed` | `runefoble.events.lore.invisible_ink_revealed` |
| `RelicForged` | `runefoble.events.lore.relic_forged` |
| `RelicInspected` | `runefoble.events.lore.relic_inspected` |
| `RelicRuneTranslated` | `runefoble.events.lore.relic_rune_translated` |
| `AtlasPinCreated` | `runefoble.events.lore.atlas_pin_created` |
| `AtlasPinUpdated` | `runefoble.events.lore.atlas_pin_updated` |
| `AtlasLayerToggled` | `runefoble.events.lore.atlas_layer_toggled` |
| `AtlasTerritoryUpdated` | `runefoble.events.lore.atlas_territory_updated` |
| `CodexEntryPublished` | `runefoble.events.lore.codex_entry_published` |
| `CodexEntryUpdated` | `runefoble.events.lore.codex_entry_updated` |
| `SharedWorldCreated` | `runefoble.events.lore.shared_world_created` |
| `CampaignRegisteredToSharedWorld` | `runefoble.events.lore.campaign_registered_to_shared_world` |
| `CrossCampaignDiscoveryShared` | `runefoble.events.lore.cross_campaign_discovery_shared` |
| `OutpostEstablished` | `runefoble.events.lore.outpost_established` |
| `OutpostResourcesContributed` | `runefoble.events.lore.outpost_resources_contributed` |
| `SharedStrongholdUpgraded` | `runefoble.events.lore.shared_stronghold_upgraded` |
| `CommunalNoticePosted` | `runefoble.events.lore.communal_notice_posted` |

Each stream entry carries the event type in the `event_type` field and the event JSON in the `payload` field.


### Compendium & Encounter Events (`aggregate_type: Compendium`, `Encounter`)

- **`HomebrewRuleRegistered`**: Emitted when a DM or player registers a campaign homebrew rule or custom monster (`HomebrewRuleRegistered`).
  - `rule_id`: UUID
  - `campaign_id`: UUID
  - `author_id`: String
  - `rule_type`: String ("monster", "spell", "condition", "mechanic")
  - `title`: String
  - `content`: Dict[str, Any]
  - `metadata`: Dict[str, Any]
- **`EncounterBalanced`**: Emitted when an automated combat encounter calculation is recorded (`EncounterBalanced`).
  - `encounter_id`: UUID
  - `campaign_id`: Optional[UUID]
  - `party_levels`: List[Integer]
  - `target_difficulty`: String ("Easy", "Medium", "Hard", "Deadly")
  - `total_party_xp_threshold`: Dict[str, int]
  - `selected_monsters`: List[Dict[str, Any]]
  - `total_xp`: Integer
  - `adjusted_xp`: Integer
  - `difficulty_tier`: String
  - `multiplier`: Float

### Soundscape & Adaptive Audio Events (`aggregate_type: Soundscape`)

- **`SoundscapeTrackChanged`**: Emitted when active soundscape track or stem profile transitions (`runefoble.events.soundscape.track_changed`). Fields: `session_id`, `track_id`, `stem_profile`, `tension_score`, `crossfade_duration_ms`, `active_stems`.
- **`SoundscapeCueTriggered`**: Emitted when a tactical sound foley or acoustic cue is fired (`runefoble.events.soundscape.cue_triggered`). Fields: `session_id`, `cue_id`, `cue_type`, `sound_url`, `volume_gain`, `duck_music`.
- **`SoundscapeTensionUpdated`**: Emitted when encounter tension score is recalculated (`runefoble.events.soundscape.tension_updated`). Fields: `session_id`, `tension_score`, `stem_profile`, `combat_active`, `combat_round`, `enemy_cr_balance`, `lowest_health_ratio`. `combat_active` is `true` while an encounter is live. `enemy_cr_balance` is the sum of the roster Challenge Ratings. `lowest_health_ratio` is the lowest party HP ratio when the score was computed.
- **`SoundscapePartyHealthRecorded`**: Emitted when a character's HP ratio changes in a session (`runefoble.events.soundscape.party_health_recorded`). Fields: `session_id`, `character_id`, `health_ratio` (current HP / max HP, 0.0 to 1.0). The aggregate keeps the latest ratio per character. The lowest ratio feeds the next tension score.
- **`StemProfileOverridden`**: Emitted when DM forces a manual stem profile (mood) override (`runefoble.events.soundscape.stem_profile_overridden`). Fields: `session_id`, `mood`, `overridden_by`.
- **`MasterVolumeChanged`**: Emitted when the session master volume changes (`runefoble.events.soundscape.master_volume_changed`). Fields: `session_id`, `master_volume`. Rebuilds `master_volume` in the aggregate on replay.
- **`ChannelVolumeChanged`**: Emitted when the stem channel sliders change. Holds the full channel map after the change (`runefoble.events.soundscape.channel_volume_changed`). Fields: `session_id`, `channel_volumes`.
- **`DuckingEngaged`**: Emitted when background audio ducking engages (`runefoble.events.soundscape.ducking_engaged`). Fields: `session_id`, `attenuation_db`, `reason`, `duration_ms`. A positive `duration_ms` ends the duck when that time has passed since the event. A `duration_ms` of `0` holds the duck until a `DuckingReleased` event.
- **`DuckingReleased`**: Emitted when background audio ducking is released before its stored duration ends (`runefoble.events.soundscape.ducking_released`). Fields: `session_id`, `reason`.
- **`LeitmotifProfileConfigured`**: Emitted when a character's musical leitmotif and instrument signature profile is configured (`runefoble.events.soundscape.leitmotif_configured`). Fields: `session_id`, `character_id`, `character_name`, `instrument_timbre`, `tempo_multiplier`, `triumphant_stem_url`, `somber_stem_url`, `volume_gain`, `attack_ms`, `release_ms`, `duration_ms`.
- **`LeitmotifTriggered`**: Emitted when a character's triumphant or somber musical stinger is dynamically triggered (`runefoble.events.soundscape.leitmotif_triggered`). Fields: `session_id`, `character_id`, `character_name`, `motif_type`, `instrument_timbre`, `stem_url`, `tempo_multiplier`, `volume_gain`, `attack_ms`, `release_ms`, `duration_ms`, `duck_music`, `trigger_reason`, `playback_id`, `triggered_at`.

### Audience Studio Events (`aggregate_type: AudiencePoll`)

The TypeScript `audience_studio` service publishes these events to the `runefoble.events.audience` stream. A command publishes its events before it stores them. If a publish fails, the command is rejected and nothing is stored. The CloudEvent `id` is `<stream>#<version>`, so a retried command publishes the same id. Poll events use stream `AudiencePoll-<poll_id>`. Proposal events use stream `AudienceModifierProposal-<proposal_id>`. The CloudEvent `time` is the command time.

- **`AudiencePollStarted`**: Emitted when a live spectator chaos poll starts (`runefoble.events.audience.poll_started`). Fields: `poll_id`, `campaign_id`, `session_id`, `title`, `prompt`, `options`, `duration_seconds`, `quorum`, `expires_at`.
- **`AudienceVoteCast`**: Emitted when a spectator casts a vote (`runefoble.events.audience.vote_cast`). Fields: `poll_id`, `campaign_id`, `voter_id`, `option_id`, `channel`, `timestamp`.
- **`AudiencePollCompleted`**: Emitted when poll voting concludes (`runefoble.events.audience.poll_completed`). Fields: `poll_id`, `campaign_id`, `session_id`, `winning_option_id`, `winning_option_label`, `total_votes`, `quorum_met`, `proposed_modifier` (the full proposal object, or `null` when quorum is not met).
- **`AudienceModifierProposed`**: Emitted when winning chaos option enters DM moderation queue (`runefoble.events.audience.modifier_proposed`). Fields: `proposal_id`, `poll_id`, `campaign_id`, `session_id`, `title`, `modifier_type`, `description`, `parameters`, `status`.
- **`AudienceModifierApproved`**: Emitted when the DM decides a proposal (`runefoble.events.audience.modifier_approved`). Fields: `proposal_id`, `poll_id`, `campaign_id`, `session_id`, `approved_by`, `approved`, `modifier_type`, `parameters`, `applied_at` (the decision time). A veto uses the same event type with `approved: false`. No separate veto event exists.

Consumers must check `approved` before they apply a modifier.

