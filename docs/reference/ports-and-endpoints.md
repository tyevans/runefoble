# Reference: Ports and Endpoints

## Ingress Routes (localhost)

| Ingress Path | Destination Service | Description |
|---|---|---|
| `/` | `frontend:80` | Lit + Vite web application |
| `/api` | `gateway-api:8000` | REST and WebSocket API gateway |
| `/docs`, `/swagger-ui` | `swagger-ui:8080` | Unified Swagger UI aggregating all OpenAPI specs |
| `/auth` | `zitadel:8080` | Self-hosted Zitadel identity provider |
| `/analytics` | `openpanel:3000` | Self-hosted OpenPanel privacy-preserving analytics |
| `/mail`, `/mailpit` | `mailpit:8025` | Self-hosted Mailpit email testing & mock SMTP Web UI and API |

## Local Development Vite Proxy Routes (localhost:5173)

When running the local development environment via `make dev`, Vite proxies requests to local backend services to prevent 502 Bad Gateway and un-proxied SPA interception errors:

| Vite Proxy Path | Destination Target | Description |
|---|---|---|
| `/api`, `/api/v1` | `http://localhost:8000` (`gateway-api`) | REST API endpoints for campaigns, characters, sessions, downtime, and settlements |
| `/ws` | `ws://localhost:8000` (`gateway-api`) | Real-time WebSockets with reconnect tolerance |
| `/docs`, `/openapi.json`, `/redoc` | `http://localhost:8000` (`gateway-api`) | Unified OpenAPI documentation and Swagger schema hub |
| `/campaigns` | `http://localhost:8000` (`gateway-api`) | Direct campaign and settlement management endpoints |
| `/mail`, `/mailpit` | `http://localhost:8025` (`mailpit`) | Mailpit mock SMTP web interface and REST API |
| `/oauth`, `/auth` | `http://localhost:8080` (`zitadel`) | Zitadel OIDC authentication and token discovery endpoints |

## Microservice Internal Ports

| Service | Internal Port | OpenAPI Path |
|---|---|---|
| `gateway-api` | `8000` | `/openapi.json` |
| `the-watcher` | `8001` | `/openapi.json` |
| `board-state` | `8002` | `/openapi.json` |
| `character-sheet` | `8003` | `/openapi.json` |
| `game-session` | `8004` | `/openapi.json` |
| `voice-agent` | `8005` | `/openapi.json` |
| `campaign-lore` | `8006` | `/openapi.json` |
| `rules-compendium` | `8007` | `/openapi.json` |
| `asset-forge` | `8008` | `/openapi.json` |
| `soundscape` | `8009` | `/openapi.json` |
| `audience-studio` | `8010` | `/openapi.json` |
| `campaign-analytics` | `8011` | `/openapi.json` |

## Key Microservice Endpoints

| Service | Method | Route | Description |
|---|---|---|---|
| `the-watcher` | POST | `/api/v1/watcher/transcribe-and-act` | Parses spoken transcript, dispatches events to Redis Streams, triggers board actions (alias: `/api/v1/watcher/intent`) |
| `the-watcher` | POST | `/api/v1/watcher/intent/parse` | Decomposes compound voice actions and detects target ambiguity (< 400ms SLA), returning clarification prompts or executable combos |
| `the-watcher` | POST | `/api/v1/watcher/intent/resolve` | Resolves player disambiguation choice and emits `CompoundActionResolved` over Redis Streams |
| `the-watcher` | POST | `/api/v1/watcher/intent/execute` | Executes compound action graphs step-by-step with partial failure and rollback coordination |
| `the-watcher` | POST | `/api/v1/watcher/scenes/generate` | Generates dynamic scene atmosphere, location details, lighting, and ambient audio prompt |
| `the-watcher` | POST | `/api/v1/watcher/encounters/spawn` | Spawns balanced tactical combat monsters and encounter objectives |
| `the-watcher` | POST | `/api/v1/watcher/encounters/npc-turn` | Resolves tactical NPC/monster turn decision trees |
| `the-watcher` | POST | `/api/v1/watcher/stand-in/act` | Generates autonomous action for absent player's character with penalties |
| `the-watcher` | POST | `/api/v1/watcher/stand-in/recap` | Generates humorous absentee session recap for returning players |
| `the-watcher` | POST | `/api/v1/watcher/chronicle/recap` | Generates structured absentee session chronicle and recap event |
| `the-watcher` | POST | `/api/v1/watcher/narrate` | Generates atmospheric narration and DM rulings |
| `the-watcher` | POST | `/api/v1/watcher/actions/propose` | Proposes an AI game action with configurable pre-execution pause window (default 2000ms, alias: `/api/v1/watcher/propose`) |
| `the-watcher` | POST | `/api/v1/watcher/veto` | Cancels pending AI action and halts board state mutation, emitting `WatcherActionVetoed` (Zanzibar enforced) |
| `the-watcher` | POST | `/api/v1/watcher/approve` | Commits pending AI action immediately without waiting for pause timeout (Zanzibar enforced) |
| `the-watcher` | POST | `/api/v1/watcher/modify` | Modifies parameters or target of an intercepted AI action before commit (Zanzibar enforced) |
| `the-watcher` | GET | `/api/v1/watcher/whispers` | Retrieves paginated DM private narrative suggestions, tactics, and perception alerts (Zanzibar enforced) |
| `the-watcher` | POST | `/api/v1/watcher/whispers` | Creates a new private narrative suggestion for the DM (Zanzibar enforced) |
| `the-watcher` | POST | `/api/v1/watcher/whispers/generate` | Generates dynamic atmospheric hints, monster tactics, and perception checks (Zanzibar enforced) |
| `the-watcher` | POST | `/api/v1/campaigns/{campaign_id}/world-tick` | Advances background NPC faction agendas, simulates rival clashes, and generates DM intelligence bulletin (alias: `/api/v1/campaigns/{campaign_id}/factions/tick`, Zanzibar enforced) |
| `the-watcher` | POST | `/api/v1/campaigns/{campaign_id}/factions` | Registers and persists an autonomous NPC faction with influence, resources, and agendas (Zanzibar enforced) |
| `the-watcher` | GET | `/api/v1/campaigns/{campaign_id}/factions` | Lists registered and active NPC factions in a campaign (Zanzibar enforced) |
| `the-watcher` | GET | `/api/v1/campaigns/{campaign_id}/factions/{faction_id}` | Retrieves detailed event-sourced aggregate state for an NPC faction (Zanzibar enforced) |
| `the-watcher` | GET | `/api/v1/campaigns/{campaign_id}/world-ticks/latest` | Retrieves the most recent DM intelligence bulletin and geopolitical state (Zanzibar enforced) |
| `the-watcher` | POST | `/factions/{faction_id}/resources/adjust` | Adjusts faction treasury or contraband assets (alias: `/api/v1/factions/{faction_id}/resources/adjust`, Zanzibar enforced) |
| `the-watcher` | POST | `/factions/{faction_id}/bribery/resolve` | Executes bribery attempt against target loyalty and counter-bribes (alias: `/api/v1/factions/{faction_id}/bribery/resolve`, Zanzibar enforced) |
| `the-watcher` | POST | `/factions/{faction_id}/mercenaries/recruit` | Recruits mercenary units against faction treasury and calculates upkeep (alias: `/api/v1/factions/{faction_id}/mercenaries/recruit`, Zanzibar enforced) |
| `the-watcher` | GET | `/factions/{faction_id}/resources` | Queries current faction treasury, contraband, and mercenaries (alias: `/api/v1/factions/{faction_id}/resources`, Zanzibar enforced) |
| `the-watcher` | POST | `/the-watcher/factions/skirmish/simulate` | Simulates ad-hoc boundary skirmish, evaluates terrain advantage and casualties, captures territory, and escalates unrest (alias: `/api/v1/factions/skirmish/simulate`, Zanzibar enforced) |
| `the-watcher` | GET | `/the-watcher/regions/{region_id}/unrest` | Queries regional unrest score, security alert posture, and economic friction modifier (alias: `/api/v1/regions/{region_id}/unrest`, Zanzibar enforced) |
| `game-session` | POST | `/api/v1/sessions/create` | Initializes a new event-sourced game session |
| `game-session` | GET | `/api/v1/sessions/{session_id}` | Loads session state reconstituted from the event stream |
| `game-session` | POST | `/api/v1/sessions/{session_id}/start` | Transitions session from lobby to active and publishes `SessionStarted` event |
| `game-session` | POST | `/api/v1/sessions/{session_id}/join` | Enters player participant and bound character into session lobby |
| `game-session` | POST | `/api/v1/sessions/{session_id}/leave` | Records player absence, toggling character for AI stand-in takeover |
| `game-session` | POST | `/api/v1/sessions/{session_id}/combat/start` | Starts combat encounter with initiative tracking and turn order |
| `game-session` | POST | `/api/v1/sessions/{session_id}/combat/initiative` | Submits combatant initiative rolls |
| `game-session` | POST | `/api/v1/sessions/{session_id}/combat/next-turn` | Advances initiative turn to next active combatant |
| `game-session` | POST | `/api/v1/sessions/{session_id}/turns/auto-pilot` | Executes automated stand-in turn for absent player, records action, dispatches events, and advances turn (alias: `/api/v1/sessions/{session_id}/autopilot`) |
| `game-session` | POST | `/api/v1/sessions/{session_id}/hot-swap` | Hands off active turn and token control from AI stand-in to authenticating player mid-session without disrupting combat round |
| `game-session` | POST | `/sessions/{session_id}/reactions/declare` | Halts active combat turn and initiates reaction window within 500ms (alias: `/api/v1/sessions/{session_id}/reactions/declare`) |
| `game-session` | POST | `/sessions/{session_id}/reactions/ready-action` | Registers conditional ready-action trigger evaluated against combat events (alias: `/api/v1/sessions/{session_id}/reactions/ready-action`) |
| `game-session` | POST | `/sessions/{session_id}/reactions/{reaction_id}/resolve` | Resolves or dismisses declared reaction interrupt, resuming active turn (alias: `/api/v1/sessions/{session_id}/reactions/{reaction_id}/resolve`) |
| `game-session` | GET | `/sessions/{session_id}/reactions/active` | Retrieves current reaction pause state and registered ready actions (alias: `/api/v1/sessions/{session_id}/reactions/active`) |
| `game-session` | POST | `/settlements` | Charters a new communal haven or outpost in a shared world (alias: `/api/v1/settlements`, Zanzibar enforced) |
| `game-session` | GET | `/settlements/{settlement_id}` | Retrieves haven state, fortification ratings, and facility tiers (alias: `/api/v1/settlements/{settlement_id}`, Zanzibar enforced) |
| `game-session` | POST | `/settlements/{settlement_id}/upgrade` | Upgrades haven workshop, sanctum, or fortifications tier (alias: `/api/v1/settlements/{settlement_id}/upgrade`, Zanzibar enforced) |
| `game-session` | POST | `/settlements/{settlement_id}/claim-boon` | Claims haven sanctum resting boons or workshop buffs (alias: `/api/v1/settlements/{settlement_id}/claim-boon`, Zanzibar enforced) |
| `game-session` | POST | `/sessions/{session_id}/contracts/bounties` | Posts a new mercenary bounty contract with gold/item escrow (alias: `/api/v1/sessions/{session_id}/contracts/bounties`, Zanzibar enforced) |
| `game-session` | GET | `/sessions/{session_id}/contracts/bounties` | Queries open notice board bounties with status, target type, and minimum reward filters (alias: `/api/v1/sessions/{session_id}/contracts/bounties`) |
| `game-session` | GET | `/sessions/{session_id}/contracts/bounties/{bounty_id}` | Retrieves details and escrow status for a specific bounty contract (alias: `/api/v1/sessions/{session_id}/contracts/bounties/{bounty_id}`) |
| `game-session` | POST | `/sessions/{session_id}/contracts/bounties/{bounty_id}/claim` | Claims an open mercenary bounty on behalf of an adventuring party (alias: `/api/v1/sessions/{session_id}/contracts/bounties/{bounty_id}/claim`, Zanzibar enforced) |
| `game-session` | POST | `/sessions/{session_id}/contracts/bounties/{bounty_id}/complete` | Submits fulfillment proof, resolves contract, and disburses escrow payout (alias: `/api/v1/sessions/{session_id}/contracts/bounties/{bounty_id}/complete`, Zanzibar enforced) |

| `voice-agent` | POST | `/api/v1/voice/stream/chunk` | Streaming PCM/WAV chunk ingestion with sub-250ms VAD segmentation and Whisper STT |
| `voice-agent` | WS | `/api/v1/voice/stream/ws` | Real-time bidirectional WebSocket stream for continuous PCM audio frames and STT events |
| `voice-agent` | POST | `/api/v1/voice/transcribe` | Transcribes player speech, emits `PlayerSpokeEvent` to Redis Streams, and forwards to The Watcher |
| `voice-agent` | POST | `/api/v1/voice/tts` | Synthesizes TTS audio stream with DSP audio conditioning (drunk slurs, underwater, whisper, ghostly) |
| `voice-agent` | POST | `/api/v1/voice/synthesize` | Backward-compatible TTS synthesis endpoint |
| `voice-agent` | GET | `/api/v1/voice/personas` | Lists available voice persona models |
| `voice-agent` | GET | `/api/v1/voice/rooms/{session_id}` | Retrieves active WebRTC voice room participants, roles, mute status, and audio telemetry |
| `voice-agent` | POST | `/api/v1/voice/rooms/{session_id}/kick` | DM moderation endpoint kicking disruptive peer from room (Zanzibar enforced) |
| `voice-agent` | WS | `/api/v1/voice/duplex/ws/{session_id}/{speaker_id}` | Zero-latency voice duplex stream with sub-80ms barge-in detection and echo cancellation |
| `voice-agent` | POST | `/api/v1/voice/duplex/playback/start` | Registers active TTS narration playback for barge-in cancellation tracking |
| `voice-agent` | GET | `/api/v1/voice/duplex/status/{session_id}` | Checks active TTS narration playback status |
| `voice-agent` | GET | `/voice/presets` | Lists all available NPC voice presets (Ancient Dragon, Goblin Skulker, Celestial Spirit, Robotic Construct) (alias: `/api/v1/voice/presets`) |
| `voice-agent` | POST | `/voice/modulate` | Applies real-time DSP pitch and formant shift transformations with <50ms processing latency (alias: `/api/v1/voice/modulate`, Zanzibar enforced) |
| `voice-agent` | GET | `/voice/streams/{session_id}/quality` | Queries stream bitrate, packet loss, and Opus codec mode (alias: `/api/v1/voice/streams/{session_id}/quality`) |
| `voice-agent` | POST | `/voice/streams/{session_id}/report` | Submits RTCP receiver reports and dynamically adapts Opus bitrate/complexity within 200ms (alias: `/api/v1/voice/streams/{session_id}/report`) |
| `voice-agent` | POST | `/voice/filters/barge-in/evaluate` | Evaluates audio frames for vocal onset (<40ms) and applies 20ms cosine crossfade attenuation (<80ms halt) (alias: `/api/v1/voice/filters/barge-in/evaluate`) |
| `voice-agent` | GET | `/ui/manifest` | Discovers vendored microfrontends (`runefoble-voice-controls`, `runefoble-audio-indicator`, `runefoble-mobile-companion` [subviews: `audio-stream-controller`, `haptic-ping-panel`, `connection-status-badge`], `runefoble-voice-duplex-controls`) |

| `board-state` | POST | `/api/v1/boards` | Initializes tactical grid aggregate with specified dimensions |
| `board-state` | GET | `/api/v1/boards/{session_id}` | Retrieves tactical grid dimensions and placed token states |
| `board-state` | POST | `/api/v1/boards/{session_id}/tokens` | Places token onto tactical grid with bounds check and fog update |
| `board-state` | POST | `/api/v1/boards/{session_id}/tokens/{token_id}/move` | Moves token across grid, checks movement budget, and evaluates hazards (alias: `/api/v1/boards/{session_id}/move`) |
| `board-state` | DELETE | `/api/v1/boards/{session_id}/tokens/{token_id}` | Removes a token from the tactical grid |
| `board-state` | GET | `/api/v1/boards/{session_id}/visibility` | Computes Chebyshev fog-of-war masks and filters shrouded hostile tokens |
| `board-state` | POST | `/api/v1/boards/{session_id}/terrain` | Configures cell elevation, terrain difficulty, and active hazard types |
| `board-state` | POST | `/api/v1/boards/{session_id}/fog-of-war/reveal` | Manually reveals specified tactical grid coordinates from fog-of-war |
| `board-state` | POST | `/api/v1/boards/{session_id}/fog-of-war/shroud` | Manually shrouds specified tactical grid coordinates under fog-of-war |
| `board-state` | POST | `/api/v1/boards/{session_id}/tokens/{token_id}/preview` | Computes waypoint trajectory, 5-ft increments, terrain penalties, and hazard warnings (alias: `/api/v1/boards/{session_id}/preview`, `/preview-move`) |
| `board-state` | POST | `/api/v1/boards/{session_id}/tokens/{token_id}/action` | Executes tactical token combat action (Dodge, Dash, Melee, Disengage, Cast; alias: `/api/v1/boards/{session_id}/actions`) |
| `board-state` | POST | `/api/v1/boards/{session_id}/aoe/evaluate` | Evaluates rotatable AoE cone/sphere/line geometry against grid tokens with 15-degree snapping |
| `board-state` | POST | `/api/v1/boards/{session_id}/aoe/place` | Places and persists rotatable AoE spell template on tactical grid, emitting `AoETemplatePlaced` (alias: `/api/v1/boards/{session_id}/aoe`) |
| `board-state` | GET | `/api/v1/boards/{session_id}/aoe` | Lists active placed AoE spell templates on the board |
| `board-state` | DELETE | `/api/v1/boards/{session_id}/aoe/{template_id}` | Dismisses and removes active AoE spell template, emitting `AoETemplateRemoved` |
| `board-state` | POST | `/api/v1/boards/{session_id}/spells/cast` | Casts kinetic spell, generates WebGL particle trajectory, radius blooms, and ephemeral decals (alias: `/api/v1/boards/{session_id}/vfx/spell`) |
| `board-state` | POST | `/api/v1/boards/{session_id}/vfx/finish` | Acknowledges completion of WebGL particle animation playback |
| `board-state` | GET | `/api/v1/boards/{session_id}/decals` | Retrieves active ephemeral scorched earth, frost, and runic glyph decals |
| `board-state` | POST | `/api/v1/boards/{session_id}/decals/decay` | Advances combat round decay for ephemeral decals over 2 rounds |
| `board-state` | POST | `/api/v1/boards/{board_id}/physics/simulate-throw` | Simulates tumbling 3D ballistic dice roll across board terrain with floor/wall bounces and face settling |
| `board-state` | POST | `/api/v1/boards/{board_id}/physics/knockback` | Applies physical knockback impulse to miniature token, halting upon wall or elevation collisions |
| `board-state` | POST | `/api/v1/board/{id}/import/uvtt` | Ingests Universal VTT (`.dd2vtt`) files, extracts walls/portals/lights, and stores map texture in Silo S3 (alias: `/api/v1/boards/{id}/import/uvtt`) |
| `board-state` | POST | `/api/v1/board/{id}/doors/{door_id}/toggle` | Toggles state of an interactive door or portal (alias: `/board/{id}/doors/{door_id}/toggle`) |
| `board-state` | GET | `/api/v1/board/{id}/doors` | Queries interactive doors and secret portals on the board (alias: `/board/{id}/doors`) |
| `board-state` | POST | `/api/v1/board/{id}/lights` | Places or updates dynamic point light source (alias: `/board/{id}/lights`) |
| `board-state` | GET | `/api/v1/board/{id}/lights` | Queries active dynamic point light sources on the board (alias: `/board/{id}/lights`) |
| `board-state` | POST | `/api/v1/boards/{board_id}/traps` | Creates a secret DM spatial trap or trigger zone (DM only, alias: `/boards/{board_id}/traps`) |
| `board-state` | GET | `/api/v1/boards/{board_id}/traps` | Retrieves board traps, filtering out secret traps for non-DM players (alias: `/boards/{board_id}/traps`) |
| `board-state` | POST | `/api/v1/boards/{board_id}/switch-map` | Transitions board to a new battlemap and teleports party tokens atomically in a single event (DM only, alias: `/boards/{board_id}/switch-map`) |
| `board-state` | POST | `/api/v1/boards/{board_id}/traps/{trap_id}/disarm` | Disarms an active trap on the tactical board (alias: `/boards/{board_id}/traps/{trap_id}/disarm`) |
| `board-state` | WS | `/ws/boards/{session_id}` | Real-time tactical board WebSocket stream for kinematic dragging, radial token actions, live rotatable AoE previews, and spell VFX |
| `board-state` | GET | `/ui/manifest` | Discovers vendored microfrontends (`runefoble-board`, `runefoble-tactical-board`, `runefoble-map-uploader`, `runefoble-radial-menu`, `runefoble-aoe-template`) |
| `character-sheet` | POST | `/api/v1/characters` | Creates a new character with initial level and spell slots (alias: `/api/v1/characters/create`) |
| `character-sheet` | GET | `/api/v1/characters/{id}` | Retrieves character sheet details, stats, equipment, and active conditions |
| `character-sheet` | POST | `/api/v1/characters/{id}/level-up` | Levels up character, increasing HP and unlocking class spell slots |
| `character-sheet` | POST | `/api/v1/characters/{id}/spells/prepare` | Prepares a spell in the character's active spellbook |
| `character-sheet` | POST | `/api/v1/characters/{id}/spells/cast` | Expends a spell slot to cast a spell with slot exhaustion validation |
| `character-sheet` | POST | `/api/v1/characters/{id}/health` | Updates character hit points with damage or healing (auto-stabilizes stand-in at 0 HP) |
| `character-sheet` | POST | `/api/v1/characters/{id}/penalties` | Inflicts DM session miss penalty on absent player stand-in |
| `character-sheet` | DELETE | `/api/v1/characters/{id}/penalties/{penalty_type}` | Clears active session penalty from character |
| `character-sheet` | POST | `/api/v1/characters/{id}/inventory/add` | Adds inventory item to character equipment inventory |
| `character-sheet` | POST | `/api/v1/characters/{id}/inventory/{item_id}/remove` | Decrements or removes inventory item from character |
| `character-sheet` | POST | `/api/v1/characters/{id}/equipment` | Equips item into designated equipment slot |
| `character-sheet` | POST | `/api/v1/characters/{id}/conditions` | Applies tactical status condition with optional round duration |
| `character-sheet` | DELETE | `/api/v1/characters/{id}/conditions/{condition}` | Clears active status condition from character |
| `character-sheet` | PUT | `/api/v1/characters/{id}/guardrails` | Configures tactical guardrail constraints for stand-in AI (SpiceDB Zanzibar enforced) |
| `character-sheet` | GET | `/api/v1/characters/{id}/guardrails` | Retrieves active tactical guardrail profile for character stand-in |
| `character-sheet` | GET | `/api/v1/characters/{id}/portrait` | Resolves active composited SVG portrait data URL and condition overlay badges |
| `character-sheet` | POST | `/api/v1/characters/{id}/portrait/active` | Switches active character portrait to base or wardrobe variant URL |
| `character-sheet` | GET | `/api/v1/characters/{id}/wardrobe` | Lists all unlocked narrative wardrobe variants and active selection |
| `character-sheet` | POST | `/api/v1/characters/{id}/wardrobe` | Adds a new unlocked narrative wardrobe variant to character |
| `character-sheet` | GET | `/ui/manifest` | Discovers vendored microfrontends (`runefoble-character-card`, `runefoble-character-sheet`, `runefoble-absentee-recap`, `runefoble-stand-in-guardrails`, `runefoble-wardrobe-gallery`) |
| `campaign-lore` | POST | `/api/v1/lore/documents` | Ingests worldbuilding markdown/text docs, extracts knowledge graphs, and indexes hybrid chunks |
| `campaign-lore` | GET | `/api/v1/lore/documents/{id}` | Retrieves ingested lore document aggregate (SpiceDB Zanzibar authorized for secret lore) |
| `campaign-lore` | POST | `/api/v1/lore/aliases/consolidate` | Consolidates entity aliases into canonical graph nodes via redstring Consolidator |
| `campaign-lore` | GET | `/api/v1/lore/aliases/resolve` | Resolves entity titles or aliases to canonical node names |
| `campaign-lore` | POST | `/api/v1/lore/search` | Sub-50ms hybrid RAG search combining BM25, dense embeddings, and graph walks with secret filtering |
| `campaign-lore` | GET | `/api/v1/campaigns/{campaign_id}/atlas` | Retrieves multi-layered world atlas state with deep-zoom coordinate projection and era filtering |
| `campaign-lore` | POST | `/api/v1/campaigns/{campaign_id}/atlas/pins` | Places geotagged milestone pin with automatic polygon territory containment detection |
| `campaign-lore` | POST | `/api/v1/campaigns/{campaign_id}/atlas/layers/toggle` | Toggles map layer or contested boundary overlay visibility |
| `campaign-lore` | POST | `/api/v1/campaigns/{campaign_id}/atlas/territories` | Defines geopolitical territory boundary polygon, ownership faction, and contested alerts |
| `campaign-lore` | POST | `/api/v1/campaigns/{campaign_id}/codex/entries` | Publishes collaborative party codex note with automated redstring entity hyperlinking |
| `campaign-lore` | GET | `/api/v1/campaigns/{campaign_id}/codex/entries` | Lists codex entries filtered by era/tag/search under SpiceDB Zanzibar privacy checks |
| `campaign-lore` | GET | `/api/v1/campaigns/{campaign_id}/codex/entries/{id}` | Retrieves illuminated codex entry (SpiceDB Zanzibar enforced: private notes 403 to unauthorized users) |
| `campaign-lore` | PATCH | `/api/v1/campaigns/{campaign_id}/codex/entries/{id}` | Updates codex entry markdown content or promotes privacy from private to party_shared |
| `campaign-lore` | GET | `/api/v1/campaigns/{campaign_id}/codex/entries/{id}/references` | Retrieves entity cross-references and mention links for an illuminated codex entry |
| `campaign-lore` | POST | `/api/v1/campaigns/{campaign_id}/codex/references/extract` | Scans text and extracts redstring entity mentions and hyperlinked content |
| `campaign-lore` | GET | `/api/v1/campaigns/{campaign_id}/west-marches` | Retrieves West Marches shared atlas pins, communal stronghold status, and tavern notices |
| `campaign-lore` | GET | `/ui/manifest` | Discovers vendored microfrontends (`runefoble-campaign-atlas`, `runefoble-campaign-codex`, `runefoble-handout-viewer`, `runefoble-relic-inspector`, `runefoble-west-marches-atlas`) |
| `rules-compendium` | GET | `/api/v1/compendium/rules/search` | Sub-50ms hybrid BM25 and vector search for SRD monsters, spells, conditions, and homebrew |
| `rules-compendium` | GET | `/api/v1/compendium/monsters/{name}` | Retrieves full monster stat block by name |
| `rules-compendium` | GET | `/api/v1/compendium/spells/{name}` | Retrieves full spell definition by name |
| `rules-compendium` | GET | `/api/v1/compendium/conditions/{name}` | Retrieves condition mechanics and gameplay effects |
| `rules-compendium` | POST | `/api/v1/compendium/encounters/balance` | Calculates encounter lethality and generates synergistic monster groups for party roster |
| `rules-compendium` | POST | `/api/v1/compendium/homebrew` | Registers campaign homebrew monster or rule guarded by SpiceDB Zanzibar authorization |
| `rules-compendium` | GET | `/api/v1/compendium/homebrew/{campaign_id}` | Retrieves campaign homebrew rules under Zanzibar authorization |
| `rules-compendium` | GET | `/ui/manifest` | Discovers vendored microfrontends (`runefoble-rules-compendium`, `runefoble-rules-lookup`, `runefoble-encounter-builder`, `runefoble-homebrew-creator`) |
| `asset-forge` | POST | `/api/v1/forge/battlemap` | Procedurally generates battlemap texture, extracts wall & hazard geometry, and uploads to Silo S3 |
| `asset-forge` | POST | `/api/v1/forge/token` | Synthesizes circular transparent character/monster token portrait and stores in Silo S3 |
| `asset-forge` | POST | `/api/v1/forge/wardrobe` | Synthesizes character wardrobe variant preserving face embeddings and stores in Silo S3 |
| `asset-forge` | GET | `/api/v1/forge/wardrobe/{id}` | Retrieves status and image URL of character wardrobe synthesis job |
| `asset-forge` | POST | `/assets/print-pdf` | Slices battlemaps into multi-page print-ready PDFs calibrated to 1-inch grid with crosshairs (alias: `/api/v1/forge/print-pdf`) |
| `asset-forge` | POST | `/assets/standees` | Generates folding papercraft miniature sheets with mirrored artwork, nameplates, and base tabs (alias: `/api/v1/forge/standees`) |
| `asset-forge` | POST | `/assets/stl-token` | Procedurally generates watertight 3D printable STL miniature bases with condition clips (alias: `/api/v1/forge/stl-token`) |
| `asset-forge` | GET | `/ui/manifest` | Discovers vendored microfrontends (`runefoble-asset-forge`, `runefoble-print-forge`) |

| `soundscape` | POST | `/api/v1/soundscape/cue` | Triggers tactical foley sound effects or acoustic stingers (fireball, sword slash, etc.) |
| `soundscape` | GET | `/api/v1/soundscape/tension` | Retrieves current session encounter tension score (0-100) and active stem weights |
| `soundscape` | POST | `/api/v1/soundscape/tension/calculate` | Calculates encounter tension from rounds, CR balance, and lowest HP, adapting music stems |
| `soundscape` | GET | `/api/v1/soundscape/stems` | Catalogs available stem layers, crossfade weights, and tactical foley presets |
| `soundscape` | POST | `/api/v1/soundscape/stems/volume` | Updates multi-channel stem volume sliders (melody, percussion, drone, ambient) |
| `soundscape` | POST | `/api/v1/soundscape/override` | DM manual mood override forcing stem profile (exploration, tension, combat, boss) |
| `soundscape` | POST | `/api/v1/soundscape/duck` | Coordinates WebAudio -12dB background audio ducking during speech or cues |
| `soundscape` | GET | `/api/v1/soundscape/leitmotif/timbres` | Catalogs instrument timbre presets (lute, brass, woodwind, strings, synth) |
| `soundscape` | POST | `/api/v1/soundscape/leitmotif/profile` | Configures character instrument signature, tempo multiplier, and triumphant/somber stem URLs |
| `soundscape` | GET | `/api/v1/soundscape/leitmotif/profile/{character_id}` | Retrieves character leitmotif configuration |
| `soundscape` | POST | `/api/v1/soundscape/leitmotif/trigger` | Triggers or auditions character leitmotif stinger (triumphant/somber) |
| `soundscape` | GET | `/api/v1/soundscape/leitmotif/active` | Inspects currently active leitmotif layer, envelope stage, and voice ducking status |
| `soundscape` | GET | `/ui/manifest` | Discovers vendored microfrontends (`runefoble-soundscape-controls`, `runefoble-leitmotif-config`) |
| `audience-studio` | POST | `/api/v1/audience/polls` | Ingests and initializes live chaos polls with duration and quorum limits |
| `audience-studio` | GET | `/api/v1/audience/polls/{poll_id}` | Retrieves real-time spectator vote tallies and quorum status |
| `audience-studio` | POST | `/api/v1/audience/polls/{poll_id}/votes` | Casts spectator vote from Twitch chat, YouTube, or web with deduplication |
| `audience-studio` | POST | `/api/v1/audience/polls/{poll_id}/close` | Closes poll, aggregates winning outcome, and submits modifier to DM queue |
| `audience-studio` | GET | `/api/v1/audience/proposals` | Lists pending chaos modifier proposals awaiting DM moderation |
| `audience-studio` | POST | `/api/v1/audience/proposals/{id}/approve` | Commits audience chaos modifier to game session (Zanzibar enforced) |
| `audience-studio` | POST | `/api/v1/audience/proposals/{id}/veto` | Rejects audience modifier proposal (Zanzibar enforced) |
| `audience-studio` | WS | `/ws/audience/{campaign_id}` | Real-time WebSocket stream for audience voting and live DM moderation |
| `audience-studio` | GET | `/ui/manifest` | Discovers vendored microfrontend (`runefoble-audience-studio`) |
| `campaign-analytics` | GET | `/api/v1/analytics/campaigns/{id}/heatmap` | Aggregated spatial coordinate hit/damage densities |
| `campaign-analytics` | GET | `/api/v1/analytics/campaigns/{id}/mvp` | Per-encounter MVP awards based on damage dealt, healing, and critical hits |
| `campaign-analytics` | GET | `/api/v1/analytics/campaigns/{id}/timeline` | Chronological event milestones linking session recaps and boss encounters |
| `campaign-analytics` | GET | `/ui/manifest` | Discovers vendored microfrontend (`runefoble-campaign-analytics`) |
| `gateway-api` | GET | `/api/v1/profile` | Retrieves authenticated Zitadel user claims (`user_id`, `username`, `roles`, `email`) |
| `gateway-api` | GET | `/api/v1/campaigns` | Lists all campaigns where authenticated user has Zanzibar `view` permission |
| `gateway-api` | POST | `/api/v1/campaigns` | Creates new campaign, registers owner in SpiceDB Zanzibar (`owner`), returns campaign summary |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}` | Retrieves campaign overview details (requires `view`) |
| `gateway-api` | PATCH | `/api/v1/campaigns/{campaign_id}` | Updates campaign title, description, and settings (requires `manage`) |
| `gateway-api` | POST | `/api/v1/campaigns/{campaign_id}/invites` | Generates shareable invite token for player or spectator (requires `run_session`) |
| `gateway-api` | POST | `/api/v1/campaigns/join` | Accepts invite token and registers membership relation in SpiceDB Zanzibar |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}/members` | Lists campaign members and active Zanzibar roles (requires `view`) |
| `gateway-api` | DELETE | `/api/v1/campaigns/{campaign_id}/members/{user_id}` | Removes a member from campaign and purges SpiceDB Zanzibar relationships (requires `manage`) |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}/sessions` | Lists all sessions and staging lobbies for a campaign (requires `view`) |
| `gateway-api` | POST | `/api/v1/campaigns/{campaign_id}/sessions` | Creates a new session or staging lobby for a campaign (requires `run_session`) |
| `gateway-api` | POST | `/api/v1/campaigns/{campaign_id}/roles` | Assigns fine-grained SpiceDB Zanzibar relationship tuples (owner, DM, player, spectator) |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}/atlas` | Retrieves world atlas map layers, milestone pins, and geopolitical territories (requires `view`) |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}/codex` | Retrieves campaign lore codex entries and cross-references (requires `view`) |
| `gateway-api` | GET | `/api/v1/analytics/campaigns/{campaign_id}` | Retrieves campaign chronicle analytics and telemetry summary (requires `view`) |
| `gateway-api` | GET | `/api/v1/analytics/campaigns/{campaign_id}/heatmap` | Retrieves combat spatial damage and strike heatmap data (requires `view`) |
| `gateway-api` | GET | `/api/v1/analytics/campaigns/{campaign_id}/mvp` | Retrieves turn MVP awards and combatant performance statistics (requires `view`) |
| `gateway-api` | GET | `/api/v1/analytics/campaigns/{campaign_id}/timeline` | Retrieves chronological campaign milestones and narrative chronicle events (requires `view`) |
| `gateway-api` | GET | `/api/v1/characters` | Lists characters where authenticated user has SpiceDB Zanzibar `owner` or `view` relation |
| `gateway-api` | POST | `/api/v1/characters` | Creates new character, registers ownership in SpiceDB Zanzibar (`character:id#owner@user:id`), returns character details |
| `gateway-api` | GET | `/api/v1/characters/{character_id}` | Retrieves character details (requires Zanzibar `view`) |
| `gateway-api` | PATCH | `/api/v1/characters/{character_id}/campaign` | Assigns or unassigns character to/from campaign and updates Zanzibar campaign tuple (requires `edit`) |
| `gateway-api` | DELETE | `/api/v1/characters/{character_id}` | Deletes character record and cleans up SpiceDB Zanzibar relationship tuples (requires `owner`) |
| `gateway-api` | POST | `/api/v1/auth/sync/user` | Syncs Zitadel user claims into SpiceDB Zanzibar tuples |
| `gateway-api` | POST | `/api/v1/auth/sync/membership` | Grants or revokes campaign/session membership roles (`gm`, `player`, `spectator`) |
| `gateway-api` | POST | `/api/v1/auth/sync/character-ownership` | Binds character aggregate to owning user and parent campaign |
| `gateway-api` | POST | `/api/v1/auth/sync/token-binding` | Binds tactical token to character aggregate and campaign grid |
| `gateway-api` | GET | `/api/v1/auth/sync/health` | Reports Zanzibar synchronization service health and SpiceDB connectivity |
| `gateway-api` | POST | `/api/v1/sessions/{session_id}/start` | Transitions session from lobby to active and broadcasts launch event over WebSockets (requires `run_session`) |
| `gateway-api` | POST | `/api/v1/sessions/{session_id}/dm-override` | Executes DM narrative or encounter rule override (requires `run_session`) |
| `gateway-api` | POST | `/api/v1/sessions/{session_id}/atmosphere` | Updates campaign sensory atmosphere, lighting, and ambient audio (requires `run_session`) |
| `gateway-api` | POST | `/api/v1/board/tokens/{token_id}/move` | Moves a tactical token on the board (requires `move` on `board_token`) |
| `gateway-api` | GET | `/api/v1/board/tokens/{token_id}` | Inspects tactical token state (requires `inspect` on `board_token`) |
| `gateway-api` | WS | `/ws/voice/{session_id}` | Zanzibar-authorized live bidirectional WebRTC voice signaling stream |
| `gateway-api` | WS | `/ws/mobile-companion/{session_id}` | Zanzibar-protected low-bandwidth mobile WebRTC companion and haptic gateway |
| `gateway-api` | WS | `/ws/campaigns/{campaign_id}` | Real-time Zanzibar-protected campaign WebSocket stream for party state synchronization |
| `gateway-api` | GET | `/api/v1/voice/rooms/{session_id}` | Retrieves active WebRTC voice room participants, roles, and audio telemetry |
| `gateway-api` | POST | `/api/v1/mobile/companion/{session_id}/whisper` | Dispatches secret DM whisper with triple-pulse haptic alert to mobile companion |
| `gateway-api` | POST | `/api/v1/mobile/companion/{session_id}/turn-alert` | Triggers combat turn initiative double-pulse haptic alert for mobile companion |
| `gateway-api` | GET | `/api/v1/mobile/companion/profiles` | Lists available adaptive Opus mobile audio streaming profiles |
| `gateway-api` | GET | `/api/v1/spectate/{session_id}` | Audience-safe spectator state overlay redacting secret DM notes and monster stats (alias: `/api/v1/spectator/sessions/{session_id}`) |
| `gateway-api` | GET | `/overlay/party-vitals/{session_id}` | OBS transparent party vitals overlay (alpha-transparent rgba(0,0,0,0) canvas, zero DM secrets) |
| `gateway-api` | WS | `/ws/overlay/{session_id}` | Real-time spectator WebSocket feed streaming sanitized party vitals and cinematic camera updates (aliases: `/overlay/ws/{session_id}`, `/ws/spectator/{session_id}`) |
| `gateway-api` | WS | `/ws/spectator/{session_id}` | Real-time spectator WebSocket feed streaming sanitized session state and broadcast updates |
| `gateway-api` | GET | `/readyz` | Kubernetes readiness probe verifying gateway orchestration status |
| `gateway-api` | POST | `/api/v1/assets/upload` | Uploads binary or base64 assets (battlemap, avatar, audio) to Silo S3 |
| `gateway-api` | GET | `/api/v1/assets/{asset_id}` | Retrieves or streams stored asset files from Silo S3 storage |
| `gateway-api` | POST | `/api/v1/auth/register` | Registers a new user account, dispatches verification email to Mailpit SMTP, and returns JWT |
| `gateway-api` | POST | `/api/v1/auth/verify` | Verifies user email using OTP code or activation token captured in Mailpit |
| `gateway-api` | POST | `/api/v1/auth/token` | Exchanges credentials for access and refresh JWT tokens |
| `gateway-api` | POST | `/api/v1/auth/refresh` | Refreshes expired access tokens |
| `gateway-api` | POST | `/api/v1/auth/test-email` | Dispatches test email to Mailpit SMTP to verify developer mail delivery |
| `gateway-api` | GET | `/api/v1/auth/mailpit/status` | Probes Mailpit SMTP and REST API connectivity status |
| `gateway-api` | POST | `/api/v1/auth/admin/seed` | Seeds default local dev admin in SpiceDB and dispatches credentials to Mailpit |
| `gateway-api` | POST | `/api/v1/auth/admin/invite` | Invites admin/DM user, grants Zanzibar permissions, and dispatches invite email to Mailpit |
| `gateway-api` / `gateway-mcp` | GET/POST | `/mcp/tools` | Lists or registers dynamic FastMCP tools with JSON schema and sandboxing (alias: `/api/v1/mcp/tools`) |
| `gateway-api` / `gateway-mcp` | GET/PUT/DELETE | `/mcp/tools/{name}` | Inspects, updates, or deregisters runtime FastMCP tools without server restarts |
| `gateway-api` / `gateway-mcp` | POST | `/mcp/tools/{name}/execute` | Executes sandboxed dynamic FastMCP tool directly |

| `gateway-mcp` | MCP | `Dynamic & Static Tools` | Tabletop tools (`execute_agent_action_plan`, `cast_spell`, `modify_character_hp`, dynamic registry, etc.) and dynamic resource `session://{session_id}/state` |




## Infrastructure Ports

| Infrastructure | Service Name | Port | Description |
|---|---|---|---|
| PostgreSQL | `postgres` | `5432` | Relational database |
| Redis | `runefoble-redis` | `6379` | In-memory datastore and event streaming via Redis Streams |
| Silo (MinIO fork) | `silo` | `9000` (S3), `9001` (Console) | S3 Object Storage |
| SpiceDB | `spicedb` | `50051` (gRPC), `8443` (HTTP) | Zanzibar graph authorization |
| OpenPanel | `openpanel` | `3000` | Self-hosted analytics |
| Mailpit | `mailpit` | `1025` (SMTP), `8025` (HTTP/API) | Mock SMTP server and Web UI for email testing |
| OpenTelemetry Collector | `otel-collector` | `4317` (gRPC), `4318` (HTTP) | OpenTelemetry metrics and distributed trace collector |
| Loki | `loki` | `3100` | Log aggregation |
| Grafana | `grafana` | `3001` | Metrics and observability dashboards |
| Storybook (Dev) | Local | `6006` | Component development studio |
| Vite Dev Server | Local | `5173` | Frontend application dev server with reverse proxy for `/api/v1` and `/ws` to `gateway-api:8000` |


