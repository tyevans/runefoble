# Reference: Ports and Endpoints

## Ingress Routes (localhost)

| Ingress Path | Destination Service | Description |
|---|---|---|
| `/` | `frontend:80` | Lit + Vite web application |
| `/api` | `gateway-api:8000` | REST API gateway (`/api/v1/...`) |
| `/ws` | `gateway-api:8000` | WebSocket gateway (`/ws/session/{id}`, `/ws/voice/{id}`, `/ws/campaigns/{id}`, `/ws/minigames/{id}`, and other `/ws/...` routes). Traefik forwards the HTTP upgrade without extra annotations. `/ws/session/{id}` needs `session.observe` (close code 4403 otherwise), relays only inside its own session, and relays inbound frames only from callers with `session.participate` (see [Session WebSocket inbound frames](#session-websocket-inbound-frames)). The minigame table sockets (`/ws/minigames/{id}` and `/ws/establishments/{id}/tables/{table_id}`) are relayed to `game_session`, which verifies the bearer subprotocol and owns the table (TASK-0592). Clients authenticate as described in [Authenticate with Zitadel OIDC](../how-to/authenticate-with-zitadel-oidc.md) |
| `/healthz` | `gateway-api:8000` | Gateway health report. It probes each downstream service and reports its status. |
| `/docs`, `/swagger-ui` | `swagger-ui:8080` | Unified Swagger UI aggregating all OpenAPI specs |
| Host `auth.localhost`, path `/` | `zitadel:8080` | Self-hosted Zitadel identity provider. Zitadel has its own host because it serves only its root path |
| `/analytics` | `openpanel:3000` | Self-hosted OpenPanel privacy-preserving analytics |
| `/mail`, `/mailpit` | `mailpit:8025` | Self-hosted Mailpit email testing & mock SMTP Web UI and API |
| `/` | `frontend:80` | Lit + Vite web application (catch-all, lowest precedence) |

## Local Development Vite Proxy Routes (localhost:5173)

When running the local development environment via `make dev`, Vite proxies requests to local backend services to prevent 502 Bad Gateway and un-proxied SPA interception errors:

| Vite Proxy Path | Destination Target | Description |
|---|---|---|
| `/api`, `/api/v1` | `http://localhost:8000` (`gateway-api`) | REST API endpoints for campaigns, characters, sessions, downtime, and settlements |
| `/ws` | `ws://localhost:8000` (`gateway-api`) | Real-time WebSockets with reconnect tolerance |
| `/docs`, `/openapi.json`, `/redoc` | `http://localhost:8000` (`gateway-api`) | Unified OpenAPI documentation and Swagger schema hub |
| `/campaigns` | `http://localhost:8000` (`gateway-api`) | Direct campaign and settlement management endpoints |
| `/mail`, `/mailpit` | `http://localhost:8025` (`mailpit`) | Mailpit mock SMTP web interface and REST API |
| `/oauth` | `http://localhost:8080` (`zitadel`) | Zitadel OIDC token and discovery endpoints used by the dev proxy. The browser reaches Zitadel at `auth.localhost` for sign-in. The App Shell callback is `/auth/callback` and is served by the SPA fallback |
| `/healthz` | `http://localhost:8000` (`gateway-api`) | Gateway liveness check |

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
| `inference-worker` | `8100` | `/openapi.json` |
| `gateway-mcp` | `8012` | Bearer token on every MCP request (`401` without one). MCP over streamable HTTP at `/mcp`. `/healthz` reports `event_publish_failures`. `/openapi.json` documents the tool admin routes (Swagger UI lists it). The MCP protocol itself has no OpenAPI spec. ClusterIP only, with no ingress path, so the tool routes are reachable inside the cluster only |

## Key Microservice Endpoints

Campaign Lore routes require a verified bearer token, except `/health`, `/healthz`, `/openapi.json`, and `/ui/manifest`. The service never reads the caller from a body field or an identity header (TASK-0531).

| Service | Method | Route | Description |
|---|---|---|---|
| `the-watcher` | POST | `/api/v1/watcher/transcribe-and-act` | Parses spoken transcript, dispatches events to Redis Streams, triggers board actions (alias: `/api/v1/watcher/intent`) |
| `the-watcher` | POST | `/api/v1/watcher/intent/parse` | Decomposes compound voice actions and detects target ambiguity (< 400ms SLA), returning clarification prompts or executable combos |
| `the-watcher` | POST | `/api/v1/watcher/intent/resolve` | Resolves player disambiguation choice and returns the resolved actions |
| `the-watcher` | POST | `/api/v1/watcher/intent/execute` | Executes compound action graphs step-by-step with partial failure and rollback coordination |
| `the-watcher` | POST | `/api/v1/watcher/scenes/generate` | Generates dynamic scene atmosphere, location details, lighting, and ambient audio prompt |
| `the-watcher` | POST | `/api/v1/watcher/encounters/spawn` | Spawns balanced tactical combat monsters and encounter objectives |
| `the-watcher` | POST | `/api/v1/watcher/encounters/npc-turn` | Resolves tactical NPC/monster turn decision trees |
| `the-watcher` | POST | `/api/v1/watcher/stand-in/act` | Generates autonomous action for absent player's character with penalties |
| `the-watcher` | POST | `/api/v1/watcher/stand-in/recap` | Generates humorous absentee session recap for returning players |
| `the-watcher` | POST | `/api/v1/watcher/chronicle/recap` | Generates structured absentee session chronicle and recap event |
| `the-watcher` | POST | `/api/v1/watcher/narrate` | Generates atmospheric narration and DM rulings |
| `the-watcher` | POST | `/api/v1/watcher/actions/propose` | Proposes an AI game action with configurable pre-execution pause window (default 2000ms, alias: `/api/v1/watcher/propose`) |
| `the-watcher` | POST | `/api/v1/watcher/veto` | Cancels pending AI action and halts board state mutation (Zanzibar enforced) |
| `the-watcher` | POST | `/api/v1/watcher/approve` | Commits pending AI action immediately without waiting for pause timeout (Zanzibar enforced) |
| `the-watcher` | POST | `/api/v1/watcher/modify` | Modifies parameters or target of an intercepted AI action before commit (Zanzibar enforced) |
| `the-watcher` | GET | `/api/v1/watcher/actions/pending` | Lists every action a session holds with its status. Needs `session_id` and a DM (Zanzibar enforced). Proxied by `gateway-api` (TASK-0596) |
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
| `game-session` | POST | `/api/v1/sessions/create` | Initializes a new event-sourced game session and links it to `campaign_id` in SpiceDB (`session` and `game_session` objects), so campaign members can observe and control it |
| `game-session` | GET | `/api/v1/sessions/{session_id}` | Loads session state reconstituted from the event stream |
| `game-session` | GET | `/api/v1/sessions/{session_id}/events` | Returns the session chronicle feed in commit order, read from the session event stream. Lines cover `runefoble.events.watcher.stand_in_action_decided`, `DiceRolled`, `runefoble.events.session.started`, and `runefoble.events.session.ended`. Returns `[]` for a session with no such events. Gateway route requires `session.observe`. Returns 404 for an unknown session (TASK-0641) |
| `game-session` | GET | `/api/v1/sessions/{session_id}/spectator` | Audience view of the session: status, combat round, scene atmosphere (location, lighting, mood, description, ambient prompt), and the public chronicle. The DM-only atmosphere fields are not in the response. Needs `session.observe` (`403`). Returns `404` for an unknown session (TASK-0823) |
| `game-session` | GET | `/api/v1/sessions/{session_id}/absentee-recap` | Returns the stand-in turns, penalties, and actions that the session recorded. Derived from stand-in actions only, never from fixed content. Returns an empty recap when no stand-in turn exists. Gateway route requires `session.observe`. Returns 404 for an unknown session (TASK-0641) |
| `game-session` | POST | `/api/v1/sessions/{session_id}/start` | Transitions session from lobby to active and publishes `runefoble.events.session.started` event. Requires `session.control` |
| `game-session` | POST | `/api/v1/sessions/{session_id}/join` | Seats the verified caller and their character in the session lobby. Requires `session.participate`. The body has no player id |
| `game-session` | POST | `/api/v1/sessions/{session_id}/leave` | Records the verified caller's absence, toggling character for AI stand-in takeover. Requires `session.participate`. The body has no player id |
| `game-session` | POST | `/api/v1/campaigns/{campaign_id}/stronghold/treasury/contribute` | Debits the stronghold treasury for a frontier outpost. Requires `stronghold.manage`. Answers `409` on shortfall and records no event |
| `game-session` | POST | `/api/v1/sessions/{session_id}/combat/start` | Starts combat encounter with initiative tracking and turn order. Requires `session.control` |
| `game-session` | POST | `/api/v1/sessions/{session_id}/combat/initiative` | Submits combatant initiative rolls. Requires `session.control` |
| `game-session` | POST | `/api/v1/sessions/{session_id}/combat/next-turn` | Advances initiative turn to next active combatant. Requires `session.control` |
| `game-session` | POST | `/api/v1/sessions/{session_id}/turns/auto-pilot` | Executes automated stand-in turn for absent player using the policy stored on the character, records action, dispatches events, and advances turn (alias: `/api/v1/sessions/{session_id}/autopilot`). The body takes no policy; a `guardrails` field returns 422. Requires `session.control` |
| `game-session` | POST | `/api/v1/sessions/{session_id}/lobby/readiness` | Records the verified caller's lobby readiness (`lobby` status only). Requires `session.participate`. Saved as `runefoble.events.session.readiness_toggled`; the session read model returns `lobby_readiness` |
| `game-session` | POST | `/api/v1/sessions/{session_id}/lobby/character` | Records the character the verified caller brings to the lobby (`lobby` status only). Requires `session.participate`. Saved as `runefoble.events.session.character_selected_for_lobby` |
| `game-session` | POST | `/api/v1/sessions/{session_id}/roll` | Evaluates a dice roll and records it as `DiceRolled` for the verified caller. Requires `session.participate`. The body has no roller id. An unknown session returns 403 |
| `game-session` | POST | `/api/v1/sessions/{session_id}/hot-swap` | Hands off active turn and token control from AI stand-in to the verified caller mid-session (requires `session.participate` and `character.edit`) without disrupting combat round |
| `game-session` | POST | `/api/v1/sessions/{session_id}/next-turn` | Advances the session turn counter and saves `runefoble.events.session.turn_advanced`. Requires `active` status and `session.control` |
| `game-session` | POST | `/api/v1/sessions/{session_id}/dm-override` | Records a DM override (`action`, `reason`, `payload`) as `DMOverrideApplied`. The override appears in `dm_overrides` on the session read model. Returns 404 for an unknown session (TASK-0581) |
| `game-session` | POST | `/api/v1/sessions/{session_id}/atmosphere` | Sets the session location, lighting, mood, and ambient audio prompt as `AtmosphereUpdated`. The value appears in `atmosphere` on the session read model. Returns 404 for an unknown session (TASK-0581) |
| `game-session` | POST | `/sessions/{session_id}/reactions/declare` | Halts active combat turn and initiates reaction window within 500ms (alias: `/api/v1/sessions/{session_id}/reactions/declare`). Requires `session.participate` |
| `game-session` | POST | `/sessions/{session_id}/reactions/ready-action` | Registers conditional ready-action trigger evaluated against combat events (alias: `/api/v1/sessions/{session_id}/reactions/ready-action`). Requires `session.participate` |
| `game-session` | POST | `/sessions/{session_id}/reactions/{reaction_id}/resolve` | Resolves or dismisses declared reaction interrupt, resuming active turn (alias: `/api/v1/sessions/{session_id}/reactions/{reaction_id}/resolve`). Requires `session.participate` |
| `game-session` | GET | `/sessions/{session_id}/reactions/active` | Retrieves current reaction pause state and registered ready actions (alias: `/api/v1/sessions/{session_id}/reactions/active`). Requires `session.observe` |
| `game-session` | POST | `/settlements` | Charters a new communal haven or outpost in a shared world (alias: `/api/v1/settlements`, Zanzibar enforced) |
| `game-session` | GET | `/settlements/{settlement_id}` | Retrieves haven state, fortification ratings, and facility tiers (alias: `/api/v1/settlements/{settlement_id}`, Zanzibar enforced) |
| `game-session` | POST | `/settlements/{settlement_id}/deposit` | Adds gold and materials to the haven treasury. Requires `manage`. Answers `400` on a negative or empty deposit (alias: `/api/v1/settlements/{settlement_id}/deposit`, Zanzibar enforced) |
| `game-session` | POST | `/settlements/{settlement_id}/upgrade` | Upgrades haven workshop, sanctum, watchtower, trading post, or fortifications tier. The price table sets the cost. Answers `409` on a treasury shortfall and records no event (alias: `/api/v1/settlements/{settlement_id}/upgrade`, Zanzibar enforced) |
| `game-session` | POST | `/settlements/{settlement_id}/claim-boon` | Claims haven sanctum resting boons or workshop buffs (alias: `/api/v1/settlements/{settlement_id}/claim-boon`, Zanzibar enforced) |
| `gateway-api` | POST | `/api/v1/campaigns/{campaign_id}/settlements` | Proxies to `game_session`: founds a settlement haven. Returns `201`. The owner checks campaign write (TASK-0592) |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}/settlements` | Proxies to `game_session`: lists the settlements of a campaign (TASK-0592) |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}/settlements/{settlement_id}` | Proxies to `game_session`: reads one settlement projection (TASK-0592) |
| `gateway-api` | POST | `/api/v1/settlements/{settlement_id}/establishments` | Proxies to `game_session`: constructs an establishment in a district. Returns `201` (TASK-0592) |
| `gateway-api` | GET | `/api/v1/settlements/{settlement_id}/establishments` | Proxies to `game_session`: lists the establishments of a settlement (TASK-0592) |
| `gateway-api` | GET | `/api/v1/establishments/{establishment_id}` | Proxies to `game_session`: reads one establishment (TASK-0592) |
| `gateway-api` | POST | `/api/v1/settlements/{settlement_id}/upgrade-tier` | Proxies to `game_session`: upgrades the civic tier of a settlement (TASK-0592) |
| `gateway-api` | POST | `/api/v1/establishments/{establishment_id}/upgrade` | Proxies to `game_session`: upgrades an establishment tier, amenities, or capacity (TASK-0592) |
| `gateway-api` | POST | `/api/v1/settlements/{settlement_id}/bulletin` | Proxies to `game_session`: pins a bulletin notice. Returns `201` (TASK-0592) |
| `gateway-api` | GET | `/api/v1/settlements/{settlement_id}/bulletin` | Proxies to `game_session`: lists the bulletin notices of a settlement (TASK-0592) |
| `gateway-api` | DELETE | `/api/v1/settlements/{settlement_id}/bulletin/{notice_id}` | Proxies to `game_session`: removes or fulfills a notice. Query `reason` is optional (TASK-0592) |
| `gateway-api` | POST | `/api/v1/settlements/{settlement_id}/bulletin/{notice_id}/decrypt` | Proxies to `game_session`: submits a cipher solution for a hidden notice (TASK-0592) |
| `gateway-api` | POST | `/api/v1/campaigns/{campaign_id}/stronghold/deposit` | Proxies to `game_session`: adds gold and materials to the campaign stronghold (owner checks `stronghold.manage`) |
| `gateway-api` | POST | `/api/v1/campaigns/{campaign_id}/stronghold/upgrade` | Proxies to `game_session`: upgrades a stronghold facility (owner checks `play` or `upgrade`) |
| `gateway-api` | POST | `/api/v1/sessions/{session_id}/rest/campfire` | Proxies to `game_session`: runs a campfire rest and returns its boons (owner checks `stronghold.manage`) |
| `gateway-api` | POST | `/api/v1/sessions/{session_id}/tavern/games` | Proxies to `game_session`: starts a tavern minigame (owner checks session participation) |
| `gateway-api` | POST | `/api/v1/sessions/{session_id}/merchants/{merchant_id}/haggle` | Proxies to `game_session` `POST /api/v1/haggling/start`. The gateway puts the session and merchant ids in the body |
| `gateway-api` | POST | `/api/v1/crafting/recipes/combine` | Proxies to `character_sheet`: combines reagents (owner checks `edit` on the character) |
| `game-session` | POST | `/sessions/{session_id}/contracts/bounties` | Posts a new mercenary bounty contract with gold/item escrow (alias: `/api/v1/sessions/{session_id}/contracts/bounties`, Zanzibar enforced) |
| `game-session` | GET | `/sessions/{session_id}/contracts/bounties` | Queries open notice board bounties with status, target type, and minimum reward filters (alias: `/api/v1/sessions/{session_id}/contracts/bounties`) |
| `game-session` | GET | `/sessions/{session_id}/contracts/bounties/{bounty_id}` | Retrieves details and escrow status for a specific bounty contract (alias: `/api/v1/sessions/{session_id}/contracts/bounties/{bounty_id}`) |
| `game-session` | POST | `/sessions/{session_id}/contracts/bounties/{bounty_id}/claim` | Claims an open mercenary bounty on behalf of an adventuring party (alias: `/api/v1/sessions/{session_id}/contracts/bounties/{bounty_id}/claim`, Zanzibar enforced) |
| `game-session` | POST | `/sessions/{session_id}/contracts/bounties/{bounty_id}/complete` | Submits fulfillment proof, resolves contract, and disburses escrow payout (alias: `/api/v1/sessions/{session_id}/contracts/bounties/{bounty_id}/complete`, Zanzibar enforced) |
| `game-session` | GET | `/api/v1/campaigns` | Lists campaigns the caller can `view` (SpiceDB lookup; owner: game_session, ADR-0015 a). Each item carries `permissions` (`view`, `manage`, `invite`, `launch_session`, `assign_roles`), one SpiceDB check per flag (TASK-0644) |
| `game-session` | POST | `/api/v1/campaigns` | Creates a campaign, seeds a staging lobby, and writes the owner tuple after the save |
| `game-session` | GET | `/api/v1/campaigns/{campaign_id}` | Reads one campaign (Zanzibar `view`). Includes the same `permissions` object as the list (TASK-0644) |
| `game-session` | PATCH | `/api/v1/campaigns/{campaign_id}` | Updates campaign fields (Zanzibar `manage`) |
| `game-session` | POST | `/api/v1/campaigns/{campaign_id}/invites` | Issues an invite with role, expiry, and use limit (Zanzibar `run_session`) |
| `game-session` | POST | `/api/v1/campaigns/join` | Redeems an invite and records membership (any verified caller; `400`, `410`, or `409` on a bad invite) |
| `game-session` | GET | `/api/v1/campaigns/{campaign_id}/members` | Lists the owner and members (Zanzibar `view`) |
| `game-session` | DELETE | `/api/v1/campaigns/{campaign_id}/members/{user_id}` | Removes a member and revokes campaign tuples. The owner cannot be removed (Zanzibar `manage`) |
| `game-session` | GET | `/api/v1/campaigns/{campaign_id}/sessions` | Lists sessions and lobbies of a campaign (Zanzibar `view`) |
| `game-session` | POST | `/api/v1/campaigns/{campaign_id}/sessions` | Creates a session or staging lobby (Zanzibar `run_session`) |
| `game-session` | POST | `/api/v1/campaigns/{campaign_id}/roles` | Grants `dungeon_master`, `game_master`, `player`, or `spectator` and records the membership (Zanzibar `manage`). `owner` returns `422`. A failed write returns `503` |
| `game-session` | GET | `/api/v1/campaigns/{campaign_id}/capabilities` | Returns the caller's `manage`, `run_session`, `play`, and `view` flags. Non-members receive all `false` |
| `game-session` | GET | `/api/v1/profile` | Reads the caller's profile. Unedited fields show the verified token's username and email (owner: game_session, ADR-0015 a) |
| `game-session` | PATCH | `/api/v1/profile` | Edits the caller's `display_name`, `avatar_url`, `bio`, or `email`. Only the fields sent change. Returns `409` on a concurrent edit |
| `voice-agent` | POST | `/api/v1/voice/stream/chunk` | Streaming PCM/WAV chunk ingestion with sub-250ms VAD segmentation and Whisper STT. Returns `503` with `error: speech_engine_unavailable` when the configured engine cannot transcribe a completed utterance; publishes no `runefoble.events.watcher.player_spoke` |
| `voice-agent` | WS | `/api/v1/voice/stream/ws` | Real-time bidirectional WebSocket stream for continuous PCM audio frames and STT events. Sends `{"error": "speech_engine_unavailable", ...}` for a failed utterance and keeps the socket open |
| `voice-agent` | POST | `/api/v1/voice/transcribe` | Transcribes player speech from `audio_base64` (STT port) or uses a non-empty typed `transcript`. Returns `source` (`audio` or `client_text`). Returns `422` when neither input is present or the audio is malformed, and `503` with `error: speech_engine_unavailable` when the engine fails. Emits `runefoble.events.watcher.player_spoke` to Redis Streams only for non-empty text, and forwards that text to The Watcher. Never invents text |
| `voice-agent` | POST | `/api/v1/voice/synthesize` | Synthesizes persona speech with the configured engine (`espeak-ng`), applies DSP filters (drunk, underwater, whisper, ghostly) to that audio, and returns the audio it describes. Returns `503` with `error: speech_synthesis_unavailable` when the engine cannot render audio. No tone is returned. See the TTS response schema below |
| `voice-agent` | GET | `/api/v1/voice/personas` | Lists available voice persona models |
| `voice-agent` | GET | `/api/v1/voice/rooms/{session_id}` | Retrieves active WebRTC voice room participants, roles, mute status, and audio telemetry |
| `voice-agent` | POST | `/api/v1/voice/rooms/{session_id}/kick` | DM moderation endpoint kicking disruptive peer from room (Zanzibar enforced) |
| `voice-agent` | WS | `/api/v1/voice/duplex/ws/{session_id}/{speaker_id}` | Zero-latency voice duplex stream with sub-80ms barge-in detection and echo cancellation |
| `voice-agent` | POST | `/api/v1/voice/duplex/playback/start` | Registers active TTS narration playback for barge-in cancellation tracking |
| `voice-agent` | GET | `/api/v1/voice/duplex/status/{session_id}` | Checks active TTS narration playback status |
| `voice-agent` | GET | `/api/v1/voice/presets` | Lists all available NPC voice presets (Ancient Dragon, Goblin Skulker, Celestial Spirit, Robotic Construct) |
| `voice-agent` | POST | `/api/v1/voice/modulate` | Applies real-time DSP pitch and formant shift transformations with <50ms processing latency (Zanzibar enforced) |
| `voice-agent` | GET | `/api/v1/voice/streams/{session_id}/quality` | Queries stream bitrate, packet loss, and Opus codec mode |
| `voice-agent` | POST | `/api/v1/voice/streams/{session_id}/report` | Submits RTCP receiver reports and dynamically adapts Opus bitrate/complexity within 200ms |
| `voice-agent` | POST | `/api/v1/voice/filters/barge-in/evaluate` | Evaluates audio frames for vocal onset (<40ms) and applies 20ms cosine crossfade attenuation (<80ms halt) |
| `voice-agent` | GET | `/healthz` | Readiness check. Reports the active speech engines as `stt_engine` (`faster-whisper` by default, or `whisper-cpp`) and `tts_engine` (default `espeak-ng`). For `whisper-cpp`, the route checks that the server answers `GET /health`. Returns `503` with `status: not_ready` and `problems` when a speech engine is not ready |
| `voice-agent` | POST | `/api/v1/voice/dsp/apply` | Applies DSP filters to supplied base64 PCM or WAV audio. Returns `422` when `audio_base64` is missing or invalid. The route never synthesises a carrier tone |
| `voice-agent` | POST | `/api/v1/voice/dsp/condition` | Conditions speech text for affliction filters (for example `drunk`). Input: `text`, `filters`. Returns `original_text`, `conditioned_text`, `active_filters`, and `dsp_config`. Returns no audio. Called by `game-session` over HTTP at `RUNEFOBLE_VOICE_AGENT_URL` (`http://voice-agent:8005` in Helm) for drink rolls with `speech_text` |
| `voice-agent` | WS | `/ws/voice/{session_id}` | WebRTC voice room signaling. Verifies the bearer, then checks `session.observe` (close `4403` on refusal, `1011` when SpiceDB is unavailable). Owns the room state. A graceful shutdown closes the socket with `1012` and keeps the peer in the room (see [Graceful Restart Keeps Room Seats](../how-to/handle-neural-voice-duplex-and-speech-interruption.md#graceful-restart-keeps-room-seats)) |
| `voice-agent` | WS | `/ws/mobile-companion/{session_id}` | Mobile companion and haptic channel with the same `session.observe` check. Owns the companion connection state |
| `voice-agent` | POST | `/api/v1/mobile/companion/{session_id}/whisper` | Dispatches a secret DM whisper with a haptic ping. Checks `session.control` |
| `voice-agent` | POST | `/api/v1/mobile/companion/{session_id}/turn-alert` | Dispatches a combat turn alert with a haptic ping. Checks `session.control` |
| `voice-agent` | GET | `/api/v1/mobile/companion/profiles` | Lists the adaptive Opus mobile audio profiles |
| `voice-agent` | GET | `/ui/manifest` | Discovers vendored microfrontends (`runefoble-voice-controls`, `runefoble-audio-indicator`, `runefoble-mobile-companion` [subviews: `audio-stream-controller`, `haptic-ping-panel`, `connection-status-badge`], `runefoble-voice-duplex-controls`) |
| `board-state` | POST | `/api/v1/boards` | Creates the tactical grid aggregate. This is the only route that creates a board. Needs a verified user token and `campaign_id` in the body (`400` when absent). The caller needs `campaign.run_session` (`403` otherwise). A second create for the same session returns `409`. The route then writes `board:<id>#campaign@campaign:<cid>`. |
| `board-state` | GET | `/api/v1/boards/{session_id}` | Retrieves tactical grid dimensions, placed token states, and the spectator camera target (`camera`). Needs `board.view` (`403` otherwise, with no board data). Returns `404` when no board exists. Never creates a board or adds tokens. Secret traps, secret doors, and secret portals are absent unless the caller holds `board.view_secret_layer`. A service call with only the service credential has no user and skips the view check. |
| `board-state` | POST | `/api/v1/boards/{session_id}/tokens` | Places token onto tactical grid with bounds check and fog update. Returns `404` when no board exists; create the board with `POST /api/v1/boards` first. A token with `character_id` needs `character.edit` and `campaign.play`. Any other token needs `board.manage_traps`. The route writes `board_token:<id>#campaign` and `#character` tuples (`403`, `400` for an unsafe id, `409` for an id that another campaign owns). |
| `board-state` | POST | `/api/v1/boards/{session_id}/ghost-previews` | Proposes a move as a ghost preview (TASK-0814). Body: `token_id` or `speaker_name`, `to_x`, `to_y`, and optional `from_x`, `from_y`, `movement_budget`, `raw_transcript`, `timeout_seconds`. Needs `board.view`. Broadcasts `ghost_preview` (`status: staged`) to every board socket of the session and returns that message. It never moves a token. Returns `404` for no board or no matching token, `400` for a route the board cannot compute. The Watcher calls it with the speaker's bearer |
| `board-state` | GET | `/api/v1/boards/{session_id}/spectator` | Audience view of the board: grid size, the non-monster tokens, the player characters with hit points (`party`), and the camera target. Monsters never appear. Needs `board.view` (`403` otherwise). Returns `404` when no board exists (TASK-0823) |
| `board-state` | GET | `/api/v1/boards/{session_id}/camera` | Returns the spectator camera target stored for the session. A board without focus events returns the initial target (`reason: init`). Needs `board.view` (`403` otherwise) (TASK-0823) |
| `board-state` | POST | `/api/v1/boards/{session_id}/camera/turn-started` | Centers the camera on the token that starts its turn. Body names `token_id` or `character_id`. Records a `CameraFocused` event. Needs `session.participate` (`403` otherwise). Returns `409` when the token is not on the board (TASK-0823) |
| `board-state` | POST | `/api/v1/boards/{session_id}/camera/token-moved` | Centers the camera on a move destination (`token_id`, `to_x`, `to_y`). Records a `CameraFocused` event. Needs `session.participate` (`403` otherwise) (TASK-0823) |
| `board-state` | GET | `/api/v1/boards/{session_id}/tokens/{token_id}` | Retrieves one placed token with its stored `x` and `y`. Needs `board.view`. Returns `404` for an unknown token |
| `board-state` | POST | `/api/v1/boards/{session_id}/tokens/{token_id}/move` | Moves token across grid, checks movement budget, and evaluates hazards. Needs `board_token.move` on the token or `board.manage_traps` (alias: `/api/v1/boards/{session_id}/move`) |
| `board-state` | DELETE | `/api/v1/boards/{session_id}/tokens/{token_id}` | Removes a token from the tactical grid and deletes its `board_token` tuples. Needs the same permission as a move |
| `board-state` | GET | `/api/v1/boards/{session_id}/visibility` | Computes Chebyshev fog-of-war masks and filters shrouded hostile tokens. Needs `board.view` (`403` otherwise). The DM view needs `board.view_secret_layer`. There is no `is_dm` parameter |
| `board-state` | POST | `/api/v1/boards/{session_id}/terrain` | Configures cell elevation, terrain difficulty, and active hazard types (needs `board.manage_traps`) |
| `board-state` | POST | `/api/v1/boards/{session_id}/fog-of-war/reveal` | Manually reveals specified tactical grid coordinates from fog-of-war (needs `board.view_secret_layer`) |
| `board-state` | POST | `/api/v1/boards/{session_id}/fog-of-war/shroud` | Manually shrouds specified tactical grid coordinates under fog-of-war (needs `board.view_secret_layer`) |
| `board-state` | POST | `/api/v1/boards/{session_id}/tokens/{token_id}/preview` | Computes waypoint trajectory, 5-ft increments, terrain penalties, and hazard warnings. Needs `board.view` (alias: `/api/v1/boards/{session_id}/preview`, `/preview-move`) |
| `board-state` | POST | `/api/v1/boards/{session_id}/tokens/{token_id}/action` | Executes tactical token combat action (Dodge, Dash, Melee, Disengage, Cast). Needs `board_token.move` on the acting token (alias: `/api/v1/boards/{session_id}/actions`) |
| `board-state` | POST | `/api/v1/boards/{session_id}/aoe/evaluate` | Evaluates rotatable AoE cone/sphere/line/cube geometry against grid tokens with 15-degree snapping. Needs `board.view`. `origin_x` and `origin_y` are whole cell indices; the origin is the cell centre. Containment is shared with spell blooms (`board_state.geometry`) |
| `board-state` | POST | `/api/v1/boards/{session_id}/aoe/place` | Places and persists rotatable AoE spell template on tactical grid, emitting `AoETemplatePlaced`. Needs `campaign.play` (alias: `/api/v1/boards/{session_id}/aoe`) |
| `board-state` | GET | `/api/v1/boards/{session_id}/aoe` | Lists active placed AoE spell templates on the board (needs `board.view`) |
| `board-state` | DELETE | `/api/v1/boards/{session_id}/aoe/{template_id}` | Dismisses and removes active AoE spell template, emitting `AoETemplateRemoved` (needs `campaign.play`) |
| `board-state` | POST | `/api/v1/boards/{session_id}/spells/cast` | Casts kinetic spell, generates WebGL particle trajectory, radius blooms, and ephemeral decals. Needs `campaign.play` (alias: `/api/v1/boards/{session_id}/vfx/spell`) |
| `board-state` | POST | `/api/v1/boards/{session_id}/vfx/finish` | Acknowledges completion of WebGL particle animation playback (needs `campaign.play`) |
| `board-state` | GET | `/api/v1/boards/{session_id}/decals` | Retrieves active ephemeral scorched earth, frost, and runic glyph decals (needs `board.view`) |
| `board-state` | POST | `/api/v1/boards/{session_id}/decals/decay` | Advances combat round decay for ephemeral decals over 2 rounds (needs `board.manage_traps`) |
| `board-state` | POST | `/api/v1/boards/{board_id}/physics/simulate-throw` | Simulates tumbling 3D ballistic dice roll across board terrain with floor/wall bounces and face settling (needs `campaign.play`) |
| `board-state` | POST | `/api/v1/boards/{board_id}/physics/knockback` | Applies physical knockback impulse to miniature token, halting upon wall or elevation collisions (needs `board_token.move` on the target token) |
| `board-state` | POST | `/api/v1/board/{id}/import/uvtt` | Ingests Universal VTT (`.dd2vtt`) files, extracts walls/portals/lights, and stores map texture in Silo S3. Returns `404` when no board exists; create the board with `POST /api/v1/boards` first. Needs `board.manage_traps` (alias: `/api/v1/boards/{id}/import/uvtt`) |
| `board-state` | POST | `/api/v1/board/{id}/doors/{door_id}/toggle` | Toggles state of an interactive door or portal. Needs `campaign.play` (alias: `/board/{id}/doors/{door_id}/toggle`) |
| `board-state` | GET | `/api/v1/board/{id}/doors` | Queries interactive doors and portals. Needs `board.view`. Secret ones need `board.view_secret_layer` (alias: `/board/{id}/doors`) |
| `board-state` | POST | `/api/v1/board/{id}/lights` | Places or updates dynamic point light source. Needs `board.manage_traps` (alias: `/board/{id}/lights`) |
| `board-state` | GET | `/boards/{id}/lights` | Queries active dynamic point light sources on the board. Needs `board.view` (alias: `/board/{id}/lights`) |
| `board-state` | WebSocket | `/ws/boards/{session_id}` | Board stream. Needs the bearer subprotocol (else `1008`) and `board.view` (else `4403`). Both close before accept. Each message type needs one permission (see the tactile board how-to). A denied message returns an error frame and the socket stays open. An unexpected error closes it with `1011` |
| `board-state` | POST | `/api/v1/boards/{board_id}/traps` | Creates a secret DM spatial trap or trigger zone (needs `board.manage_traps`, alias: `/boards/{board_id}/traps`) |
| `board-state` | GET | `/api/v1/boards/{board_id}/traps` | Retrieves board traps. Needs `board.view` (`403` otherwise). Without `board.view_secret_layer` the secret ones are absent, and a sprung one shows only its place (alias: `/boards/{board_id}/traps`) |
| `board-state` | POST | `/api/v1/boards/{board_id}/switch-map` | Transitions board to a new battlemap and teleports party tokens atomically in a single event (needs `board.switch_map`, alias: `/boards/{board_id}/switch-map`) |
| `board-state` | POST | `/api/v1/boards/{board_id}/traps/{trap_id}/disarm` | Disarms an active trap on the tactical board (needs `board.manage_traps`, alias: `/boards/{board_id}/traps/{trap_id}/disarm`) |
| `board-state` | WS | `/ws/boards/{session_id}` | Real-time tactical board WebSocket stream for kinematic dragging, radial token actions, live rotatable AoE previews, and spell VFX |
| `board-state` | GET | `/ui/manifest` | Discovers vendored microfrontends (`runefoble-board`, `runefoble-map-uploader`, `runefoble-radial-menu`, `runefoble-aoe-template`) |
| `character-sheet` | GET | `/api/v1/characters` | Lists the characters the verified caller may `view`. Optional `campaignId` query filters one campaign's party |
| `character-sheet` | POST | `/api/v1/characters` | Creates a new character. The verified caller becomes its SpiceDB `owner`. Returns the roster view with `owner_id` |
| `character-sheet` | GET | `/api/v1/characters/{id}` | Retrieves character sheet details, stats, equipment, and active conditions. Needs a user bearer with `view`. The service credential alone gets `401` |
| `character-sheet` | PATCH | `/api/v1/characters/{id}/campaign` | Assigns or unassigns the campaign and writes or removes the `character#campaign` tuple (requires `edit`) |
| `character-sheet` | POST | `/api/v1/characters/{id}/level-up` | Levels up character, increasing HP and unlocking class spell slots |
| `character-sheet` | POST | `/api/v1/characters/{id}/spells/prepare` | Prepares a spell in the character's active spellbook. With `is_prepared: false`, unprepares it and emits `SpellUnprepared` |
| `character-sheet` | POST | `/api/v1/characters/{id}/spells/cast` | Expends a spell slot to cast a spell with slot exhaustion validation |
| `character-sheet` | POST | `/api/v1/characters/{id}/spells/restore` | Restores spent spell slots to maximum (all levels, or one level with optional `slot_level`) |
| `character-sheet` | POST | `/api/v1/characters/{id}/stand-in` | Activates or releases the AI stand-in for a character (body: `active`, optional `session_id`). Emits `StandInActivated` or `StandInReleased` |
| `character-sheet` | POST | `/api/v1/characters/{id}/health` | Updates character hit points with damage or healing (auto-stabilizes stand-in at 0 HP). Optional `session_id` names the session for the published `runefoble.events.character.health_changed` event |
| `character-sheet` | POST | `/api/v1/characters/{id}/penalties` | Inflicts DM session miss penalty on absent player stand-in |
| `character-sheet` | DELETE | `/api/v1/characters/{id}/penalties/{penalty_type}` | Clears active session penalty from character |
| `character-sheet` | POST | `/api/v1/characters/{id}/inventory` | Adds inventory item to character equipment inventory |
| `character-sheet` | DELETE | `/api/v1/characters/{id}/inventory/{item_id}` | Decrements or removes inventory item from character (optional body: `quantity`) |
| `character-sheet` | POST | `/api/v1/characters/{id}/equipment` | Equips item into designated equipment slot |
| `character-sheet` | POST | `/api/v1/characters/{id}/conditions` | Applies tactical status condition with optional round duration |
| `character-sheet` | DELETE | `/api/v1/characters/{id}/conditions/{condition}` | Clears active status condition from character |
| `character-sheet` | PUT | `/api/v1/characters/{id}/guardrails` | Configures tactical guardrail constraints for stand-in AI (SpiceDB Zanzibar enforced) |
| `character-sheet` | GET | `/api/v1/characters/{id}/guardrails` | Retrieves active tactical guardrail profile for character stand-in. Accepts a user with `view`, or the service credential (used by `game-session` for auto-pilot) |
| `character-sheet` | GET | `/api/v1/characters/{id}/portrait` | Resolves active composited SVG portrait data URL and condition overlay badges |
| `character-sheet` | POST | `/api/v1/characters/{id}/portrait/active` | Switches active character portrait to base or wardrobe variant URL |
| `character-sheet` | GET | `/api/v1/characters/{id}/wardrobe` | Lists all unlocked narrative wardrobe variants and active selection |
| `character-sheet` | POST | `/api/v1/characters/{id}/wardrobe` | Adds a new unlocked narrative wardrobe variant to character |
| `character-sheet` | GET | `/ui/manifest` | Discovers vendored microfrontends (`runefoble-character-card`, `runefoble-character-sheet`, `runefoble-absentee-recap`, `runefoble-stand-in-guardrails`, `runefoble-wardrobe-gallery`) |
| `campaign-lore` | POST | `/api/v1/lore/documents` | Ingests worldbuilding markdown/text docs, extracts knowledge graphs, and indexes hybrid chunks |
| `campaign-lore` | GET | `/api/v1/lore/documents/{id}` | Retrieves ingested lore document aggregate (SpiceDB Zanzibar authorized for secret lore) |
| `campaign-lore` | POST | `/api/v1/lore/aliases/consolidate` | Consolidates entity aliases into canonical graph nodes via redstring Consolidator. Requires `document_id`; records the merge on that document. Returns `409` for a repeated or conflicting merge and `503` when the service is not started |
| `campaign-lore` | GET | `/api/v1/lore/aliases/resolve` | Resolves entity titles or aliases to canonical node names |
| `campaign-lore` | POST | `/api/v1/lore/search` | Sub-50ms hybrid RAG search combining BM25, dense embeddings, and graph walks with secret filtering. Requires a bearer token (`401` without one). Body fields: `campaign_id`, `query`, `limit`, `include_graph_walk`. Any other field, including `caller_id`, returns `422`. The caller is the verified token subject |
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
| `campaign-lore` | POST | `/api/v1/campaigns/{campaign_id}/west-marches/stronghold/contribute` | Moves gold from the stronghold treasury (game_session debit) into an outpost store. Body: `gold` (> 0), `outpost_id` (optional). Answers `403`, `404`, `409`, and `503` with no credit |
| `campaign-lore` | GET | `/ui/manifest` | Discovers vendored microfrontends (`runefoble-campaign-atlas`, `runefoble-campaign-codex`, `runefoble-handout-viewer`, `runefoble-relic-inspector`, `runefoble-west-marches-atlas`) |
| `rules-compendium` | GET | `/api/v1/compendium/rules/search` | Sub-50ms hybrid BM25 and vector search for SRD monsters, spells, conditions, and homebrew |
| `rules-compendium` | GET | `/api/v1/compendium/monsters/{name}` | Retrieves full monster stat block by name. A `campaign_id` query value adds the campaign's homebrew monsters the caller may view |
| `rules-compendium` | GET | `/api/v1/compendium/spells/{name}` | Retrieves full spell definition by name |
| `rules-compendium` | GET | `/api/v1/compendium/conditions/{name}` | Retrieves condition mechanics and gameplay effects |
| `rules-compendium` | POST | `/api/v1/compendium/encounters/balance` | Calculates encounter lethality and generates synergistic monster groups for party roster |
| `rules-compendium` | POST | `/api/v1/compendium/homebrew` | Registers campaign homebrew monster or rule guarded by SpiceDB Zanzibar authorization |
| `rules-compendium` | GET | `/api/v1/compendium/homebrew/{campaign_id}` | Retrieves campaign homebrew rules the caller may view (`homebrew_rule.view`). Each rule has a `shadowed` flag when an SRD entry has its name |
| `rules-compendium` | GET | `/ui/manifest` | Discovers vendored microfrontends (`runefoble-rules-compendium`, `runefoble-rules-lookup`, `runefoble-encounter-builder`, `runefoble-homebrew-creator`) |
| `gateway-api` | POST | `/api/v1/forge/battlemap` | Proxies to `asset-forge`. Procedurally generates battlemap texture, extracts wall & hazard geometry, and uploads to Silo S3 |
| `gateway-api` | GET | `/api/v1/forge/battlemap/{asset_id}` | Proxies to `asset-forge`. Retrieves forged battlemap metadata. Needs a bearer and `forged_asset.view` |
| `gateway-api` | GET | `/api/v1/forge/token/{asset_id}` | Proxies to `asset-forge`. Retrieves forged token metadata. Needs a bearer and `forged_asset.view` |
| `gateway-api` | POST | `/api/v1/forge/token` | Proxies to `asset-forge`. Synthesizes circular transparent character/monster token portrait and stores in Silo S3 |
| `gateway-api` | POST | `/api/v1/forge/wardrobe` | Proxies to `asset-forge`. Synthesizes a character wardrobe variant with the configured wardrobe generator (default `placeholder`, which preserves no face) and stores it in Silo S3. The response names the `generator` and states `preserves_face` |
| `gateway-api` | GET | `/api/v1/forge/wardrobe/{variant_id}` | Proxies to `asset-forge`. Retrieves status and image URL of character wardrobe synthesis job |
| `gateway-api` | POST | `/api/v1/forge/print-pdf` | Proxies to `asset-forge`. Slices battlemaps into multi-page print-ready PDFs calibrated to 1-inch grid with crosshairs. Requires `campaign_id` and `campaign.play` |
| `gateway-api` | POST | `/api/v1/forge/standees` | Proxies to `asset-forge`. Generates folding papercraft miniature sheets with mirrored artwork, nameplates, and base tabs. Requires `campaign_id` and `campaign.play` |
| `gateway-api` | POST | `/api/v1/forge/stl-token` | Proxies to `asset-forge`. Procedurally generates watertight 3D printable STL miniature bases with condition clips. Requires `campaign_id` and `campaign.play` |
| `asset-forge` | GET | `/ui/manifest` | Discovers vendored microfrontends (`runefoble-asset-forge`, `runefoble-print-forge`) |
| `soundscape` | POST | `/api/v1/soundscape/cue` | Triggers tactical foley sound effects or acoustic stingers (fireball, sword slash, etc.) |
| `soundscape` | GET | `/api/v1/soundscape/tension` | Retrieves current session encounter tension score (0-100) and active stem weights |
| `soundscape` | POST | `/api/v1/soundscape/tension/calculate` | Calculates encounter tension from rounds, CR balance, and lowest HP, adapting music stems |
| `soundscape` | GET | `/api/v1/soundscape/stems` | Catalogs available stem layers, crossfade weights, and tactical foley presets |
| `soundscape` | POST | `/api/v1/soundscape/stems/volume` | Updates multi-channel stem volume sliders (melody, percussion, drone, ambient) |
| `soundscape` | POST | `/api/v1/soundscape/stems/override` | DM manual mood override forcing stem profile (exploration, tension, combat, boss) |
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
| `audience-studio` | GET | `/readyz` | Readiness: `200` when Redis Streams and PostgreSQL respond, `503` otherwise |
| `campaign-analytics` | GET | `/api/v1/analytics/campaigns/{id}/heatmap` | Aggregated spatial coordinate hit/damage densities |
| `campaign-analytics` | GET | `/api/v1/analytics/campaigns/{id}/mvp` | Per-encounter MVP awards based on damage dealt, healing, and critical hits |
| `campaign-analytics` | GET | `/api/v1/analytics/campaigns/{id}/timeline` | Chronological event milestones linking session recaps and boss encounters |
| `campaign-analytics` | GET | `/ui/manifest` | Discovers vendored microfrontend (`runefoble-campaign-analytics`) |
| `gateway-api` | GET | `/api/v1/profile` | Retrieves the verified bearer token's user profile (`user_id`, `username`, `email`, `display_name`, `avatar_url`, `bio`). Requires a valid Zitadel bearer token (401 otherwise) |
| `gateway-api` | PATCH | `/api/v1/profile` | Updates user profile display name, avatar URL, and bio |
| `gateway-api` | GET | `/api/v1/campaigns` | Proxies to `game_session`: lists the campaigns the caller can `view` (owner-enforced; ADR-0015 a) |
| `gateway-api` | POST | `/api/v1/campaigns` | Proxies to `game_session`: creates a campaign. The caller becomes its owner. Returns `201` |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}` | Proxies to `game_session`: campaign overview (requires `view`) with the `permissions` object (TASK-0644). Unknown ID returns `404` |
| `gateway-api` | PATCH | `/api/v1/campaigns/{campaign_id}` | Proxies to `game_session`: updates campaign fields (requires `manage`) |
| `gateway-api` | POST | `/api/v1/campaigns/{campaign_id}/invites` | Proxies to `game_session`: issues an invite for `player` or `spectator` (requires `run_session`). Returns `201` |
| `gateway-api` | POST | `/api/v1/campaigns/join` | Proxies to `game_session`: redeems an invite and records membership. A used-up invite returns `409` |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}/members` | Proxies to `game_session`: owner and members (requires `view`). The gateway adds `character_name` from its character store |
| `gateway-api` | DELETE | `/api/v1/campaigns/{campaign_id}/members/{user_id}` | Proxies to `game_session`: removes a member and revokes campaign relations (requires `manage`). The owner cannot be removed |
| `gateway-api` | GET | `/api/v1/profile` | Proxies to `game_session`: reads the caller's profile. The gateway holds no profile data (TASK-0742) |
| `gateway-api` | PATCH | `/api/v1/profile` | Proxies to `game_session`: edits the caller's profile fields (TASK-0742) |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}/capabilities` | Proxies to `game_session`: the caller's `manage`, `run_session`, `play`, and `view` flags. Non-members get all `false` |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}/sessions` | Proxies to `game_session`: sessions and staging lobbies of a campaign (requires `view`) |
| `gateway-api` | POST | `/api/v1/campaigns/{campaign_id}/sessions` | Proxies to `game_session`: creates a session or staging lobby (requires `run_session`). Returns `201` |
| `gateway-api` | POST | `/api/v1/campaigns/{campaign_id}/roles` | Proxies to `game_session`: grants `dungeon_master`, `game_master`, `player`, or `spectator` (requires `manage`). `owner` returns `422`. A failed SpiceDB write returns `502` through the gateway |
| `gateway-api` | GET | `/api/v1/sessions/{session_id}` | Proxies to `game_session`: session state (requires `observe`) |
| `gateway-api` | POST | `/api/v1/sessions/{session_id}/start` | Proxies to `game_session`: moves a lobby to `active` (requires `control`) |
| `gateway-api` | POST | `/api/v1/sessions/{session_id}/hot-swap` | Proxies to `game_session`: hands turn control to a player. Body `{characterId}`. The caller is the player. The owner releases the stand-in in `character_sheet` (requires `observe`) |
| `gateway-api` | POST | `/api/v1/sessions/{session_id}/turns/advance` | Proxies to `game_session` `next-turn`: advances the turn (requires `control`) |
| `gateway-api` | POST | `/api/v1/sessions/{session_id}/dm-override` | Proxies to `game_session`: records a DM override (requires `control`) |
| `gateway-api` | POST | `/api/v1/sessions/{session_id}/atmosphere` | Proxies to `game_session`: sets location, lighting, and mood (requires `control`) |
| `gateway-api` | POST | `/api/v1/watcher/speak-and-act` | Proxies to `the_watcher` `POST /api/v1/watcher/intent` (TASK-0583). The body is the Watcher `SpeechInputRequest` (`speaker_id`, `speaker_name`, `transcript`, `session_id`, `campaign_id`, and optional grid fields). The gateway forwards it unchanged with the caller's bearer. The reply is the Watcher `IntentResult`. Status codes: `200` on success. `401` without a verified bearer. `403` when the caller lacks `session.participate` or speaks as another user (the owner decides). `422` for an invalid body (the owner's body). `502` on a Watcher 5xx. `503` when `RUNEFOBLE_WATCHER_URL` is unset or the Watcher is unreachable. A move asks `board_state` to stage a ghost preview (`POST /api/v1/boards/{session_id}/ghost-previews`, TASK-0814). No token moves until the player sends `confirm_move`. A board that cannot stage the move fails the request: the Watcher answers `503` (`backend: board_state`), and the gateway reports that as `502` with `upstream: the_watcher`. The Watcher passes the board's `4xx` through (for example `404` for no board or no token, or `403` without `board.view`) |
| `gateway-api` | POST | `/api/v1/watcher/transcribe-and-act` | Proxies to `the_watcher` `POST /api/v1/watcher/transcribe-and-act` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/watcher/intent/parse` | Proxies to `the_watcher` `POST /api/v1/watcher/intent/parse` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/watcher/intent/resolve` | Proxies to `the_watcher` `POST /api/v1/watcher/intent/resolve` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/watcher/intent/execute` | Proxies to `the_watcher` `POST /api/v1/watcher/intent/execute` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/watcher/scenes/generate` | Proxies to `the_watcher` `POST /api/v1/watcher/scenes/generate` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. The gateway waits `RUNEFOBLE_WATCHER_LLM_PROXY_TIMEOUT_S` (default 15 s) for this route. |
| `gateway-api` | POST | `/api/v1/watcher/encounters/spawn` | Proxies to `the_watcher` `POST /api/v1/watcher/encounters/spawn` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/watcher/encounters/npc-turn` | Proxies to `the_watcher` `POST /api/v1/watcher/encounters/npc-turn` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/watcher/narrate` | Proxies to `the_watcher` `POST /api/v1/watcher/narrate` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. The gateway waits `RUNEFOBLE_WATCHER_LLM_PROXY_TIMEOUT_S` (default 15 s) for this route. |
| `gateway-api` | POST | `/api/v1/watcher/stand-in/act` | Proxies to `the_watcher` `POST /api/v1/watcher/stand-in/act` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. The gateway waits `RUNEFOBLE_WATCHER_LLM_PROXY_TIMEOUT_S` (default 15 s) for this route. |
| `gateway-api` | POST | `/api/v1/watcher/stand-in/recap` | Proxies to `the_watcher` `POST /api/v1/watcher/stand-in/recap` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/watcher/chronicle/recap` | Proxies to `the_watcher` `POST /api/v1/watcher/chronicle/recap` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | GET | `/api/v1/watcher/whispers` | Proxies to `the_watcher` `GET /api/v1/watcher/whispers` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/watcher/whispers` | Proxies to `the_watcher` `POST /api/v1/watcher/whispers` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/watcher/whispers/generate` | Proxies to `the_watcher` `POST /api/v1/watcher/whispers/generate` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. The gateway waits `RUNEFOBLE_WATCHER_LLM_PROXY_TIMEOUT_S` (default 15 s) for this route. |
| `gateway-api` | POST | `/api/v1/watcher/actions/propose` | Proxies to `the_watcher` `POST /api/v1/watcher/actions/propose` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | GET | `/api/v1/watcher/actions/pending` | Proxies to `the_watcher` `GET /api/v1/watcher/actions/pending` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/watcher/veto` | Proxies to `the_watcher` `POST /api/v1/watcher/veto` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/watcher/approve` | Proxies to `the_watcher` `POST /api/v1/watcher/approve` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/watcher/modify` | Proxies to `the_watcher` `POST /api/v1/watcher/modify` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/campaigns/{campaign_id}/world-tick` | Proxies to `the_watcher` `POST /api/v1/campaigns/{campaign_id}/world-tick` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/campaigns/{campaign_id}/factions` | Proxies to `the_watcher` `POST /api/v1/campaigns/{campaign_id}/factions` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}/factions` | Proxies to `the_watcher` `GET /api/v1/campaigns/{campaign_id}/factions` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}/factions/{faction_id}` | Proxies to `the_watcher` `GET /api/v1/campaigns/{campaign_id}/factions/{faction_id}` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}/world-ticks/latest` | Proxies to `the_watcher` `GET /api/v1/campaigns/{campaign_id}/world-ticks/latest` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/factions/{faction_id}/resources/adjust` | Proxies to `the_watcher` `POST /api/v1/factions/{faction_id}/resources/adjust` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/factions/{faction_id}/bribery/resolve` | Proxies to `the_watcher` `POST /api/v1/factions/{faction_id}/bribery/resolve` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/factions/{faction_id}/mercenaries/recruit` | Proxies to `the_watcher` `POST /api/v1/factions/{faction_id}/mercenaries/recruit` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | GET | `/api/v1/factions/{faction_id}/resources` | Proxies to `the_watcher` `GET /api/v1/factions/{faction_id}/resources` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | POST | `/api/v1/factions/skirmish/simulate` | Proxies to `the_watcher` `POST /api/v1/factions/skirmish/simulate` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | GET | `/api/v1/regions/{region_id}/unrest` | Proxies to `the_watcher` `GET /api/v1/regions/{region_id}/unrest` (TASK-0596). The gateway forwards the body and query unchanged with the caller's bearer. `401` without a bearer. `503` when the Watcher is unreachable. The Watcher answers the rest. |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}/atlas` | Retrieves world atlas map layers, milestone pins, and geopolitical territories, forwarding `layer`, `era`, and `session_id` (requires `view`) |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}/codex` | Retrieves campaign lore codex entries and cross-references (requires `view`) |
| `gateway-api` | GET | `/api/v1/campaigns/{campaign_id}/codex/entries` | Lists codex entries, forwarding `era`, `tag`, and `search` (requires `view`) |
| `gateway-api` | POST | `/api/v1/campaigns/{campaign_id}/atlas/pins` | Places a milestone pin on the atlas; forwards the body to campaign-lore (requires `run_session`) |
| `gateway-api` | POST | `/api/v1/campaigns/{campaign_id}/codex/entries` | Publishes a codex entry; forwards the body to campaign-lore (requires `play`) |
| `gateway-api` | GET | `/api/v1/analytics/campaigns/{campaign_id}/heatmap` | Proxies to `campaign-analytics`. Forwards `session_id`, `cell_size`, and `metric` (requires `view`) |
| `gateway-api` | GET | `/api/v1/analytics/campaigns/{campaign_id}/mvp` | Proxies to `campaign-analytics`. Forwards `session_id` and `encounter_id` (requires `view`) |
| `gateway-api` | GET | `/api/v1/analytics/campaigns/{campaign_id}/timeline` | Proxies to `campaign-analytics`. Forwards `session_id` and `limit` (requires `view`) |
| `gateway-api` | GET | `/api/v1/characters` | Proxies to `character_sheet` (`view` filter, optional `campaignId`). Adds `campaign_title` from `game_session` |
| `gateway-api` | POST | `/api/v1/characters` | Proxies to `character_sheet`, which writes the owner tuple. Returns 201. Returns 422 for `level`, `currentHp`, `portraitUrl`, `isAiStandIn` or `id` values the owner cannot store |
| `gateway-api` | GET | `/api/v1/characters/{character_id}` | Proxies to `character_sheet` (requires `view`, checked by the owner) |
| `gateway-api` | PATCH | `/api/v1/characters/{character_id}/campaign` | Proxies to `character_sheet` (requires `edit`, checked and written by the owner) |
| `gateway-api` | POST | `/api/v1/characters/{character_id}/health` | Proxies to `character_sheet`: changes HP (requires `edit`, checked by the gateway and the owner). Owner `4xx` answers pass through unchanged. An unreachable owner returns `503` |
| `gateway-api` | POST | `/api/v1/characters/{character_id}/equipment` | Proxies to `character_sheet`: equips an item into a slot (requires `edit`) |
| `gateway-api` | DELETE | `/api/v1/characters/{character_id}/equipment/{slot}` | Proxies to `character_sheet`: clears an equipment slot (requires `edit`) |
| `gateway-api` | POST | `/api/v1/characters/{character_id}/inventory` | Proxies to `character_sheet`: adds an inventory item (requires `edit`) |
| `gateway-api` | DELETE | `/api/v1/characters/{character_id}/inventory/{item_id}` | Proxies to `character_sheet`: removes or decrements an item, with optional `quantity` query (requires `edit`) |
| `gateway-api` | POST | `/api/v1/characters/{character_id}/conditions` | Proxies to `character_sheet`: applies a tactical condition with optional `durationRounds` (requires `edit`) |
| `gateway-api` | DELETE | `/api/v1/characters/{character_id}/conditions/{condition}` | Proxies to `character_sheet`: clears a tactical condition (requires `edit`) |
| `gateway-api` | POST | `/api/v1/characters/{character_id}/spells/cast` | Proxies to `character_sheet`: casts a spell and deducts the slot tier (requires `edit`) |
| `gateway-api` | POST | `/api/v1/characters/{character_id}/spells/prepare` | Proxies to `character_sheet`: prepares or unprepares a spell (requires `edit`) |
| `gateway-api` | PUT | `/api/v1/characters/{character_id}/guardrails` | Configures tactical guardrail constraints for character stand-in AI (requires `edit`) |
| `gateway-api` | GET | `/api/v1/characters/{character_id}/guardrails` | Retrieves active tactical guardrails for character stand-in AI (requires `view`) |
| `gateway-api` | GET | `/api/v1/characters/{character_id}/wardrobe` | Proxies to `character_sheet`: lists the unlocked wardrobe variants (the owner checks `view`) |
| `gateway-api` | POST | `/api/v1/characters/{character_id}/wardrobe` | Proxies to `character_sheet`: adds a wardrobe variant (the owner checks `edit`). Body fields as in the owner route |
| `gateway-api` | POST | `/api/v1/characters/{character_id}/portrait/active` | Proxies to `character_sheet`: switches the active portrait to a wardrobe variant or a custom image (the owner checks `edit`) |
| `gateway-api` | GET | `/api/v1/auth/sync/health` | Reports Zanzibar synchronization service health and SpiceDB connectivity |
| `gateway-api` | POST | `/api/v1/sessions/{session_id}/start` | Transitions session from lobby to active and broadcasts launch event over WebSockets (requires `run_session`) |
| `gateway-api` | POST | `/api/v1/sessions/{session_id}/hot-swap` | Hands off character control from AI stand-in to returning player mid-session (requires `play_as_character`) |
| `gateway-api` | POST | `/api/v1/sessions/{session_id}/dm-override` | Executes DM narrative or encounter rule override (requires `run_session`) |
| `gateway-api` | POST | `/api/v1/sessions/{session_id}/atmosphere` | Updates campaign sensory atmosphere, lighting, and ambient audio (requires `run_session`) |
| `gateway-api` | GET | `/api/v1/boards/{session_id}` | Proxies to `board_state`: the board of a session (grid, tokens). `404` when no board exists. Board permissions are checked by `board_state` |
| `gateway-api` | GET | `/api/v1/boards/{session_id}/tokens/{token_id}` | Proxies to `board_state`: one placed token (`x`, `y`, state). Needs `board.view`. `404` for an unknown token |
| `gateway-api` | POST | `/api/v1/boards/{session_id}/tokens/{token_id}/move` | Proxies to `board_state`: moves a token. Needs `board_token.move` on the token or `board.manage_traps`. The sessionless `/api/v1/board/tokens/...` routes were removed (`404`) |
| `gateway-api` | WS | `/ws/voice/{session_id}` | Live bidirectional WebRTC voice signaling. Relayed to `voice-agent`, which checks `session.observe` (close `4403` on refusal) |
| `gateway-api` | WS | `/ws/mobile-companion/{session_id}` | Low-bandwidth mobile companion and haptic channel. Relayed to `voice-agent`, which checks `session.observe` (close `4403` on refusal) |
| `gateway-api` | WS | `/ws/campaigns/{campaign_id}` | Real-time Zanzibar-protected campaign WebSocket stream for party state synchronization |
| `gateway-api` | GET | `/api/v1/voice/rooms/{session_id}` | Proxies to `voice-agent`. Retrieves active WebRTC voice room participants, roles, and audio telemetry. Returns `503` when `voice-agent` is unreachable and `502` on an upstream `5xx`. The owner checks the bearer token and `session.observe` |
| `gateway-api` | POST | `/api/v1/voice/rooms/{session_id}/kick` | Proxies to `voice-agent`. The owner checks `session.control` |
| `gateway-api` | GET, POST | `/api/v1/voice/streams/{session_id}/quality`, `/api/v1/voice/streams/{session_id}/report` | Proxies stream diagnostics to `voice-agent`. The owner checks `session.control` |
| `gateway-api` | POST | `/api/v1/mobile/companion/{session_id}/whisper` | Proxies to `voice-agent`, which dispatches the secret DM whisper with a triple-pulse haptic alert. The owner checks `session.control` |
| `gateway-api` | POST | `/api/v1/mobile/companion/{session_id}/turn-alert` | Proxies to `voice-agent`, which triggers the combat turn initiative double-pulse haptic alert. The owner checks `session.control` |
| `gateway-api` | GET | `/api/v1/mobile/companion/profiles` | Proxies to `voice-agent`, which lists the adaptive Opus mobile audio streaming profiles |
| `gateway-api` | GET | `/api/v1/spectate/{session_id}` | Audience-safe spectator state. Needs a verified bearer token and `session.observe` (`403` otherwise, `401` without a token). The gateway joins two owner views: the session view from `game_session` (`GET /api/v1/sessions/{session_id}/spectator`) and the board view from `board_state` (`GET /api/v1/boards/{session_id}/spectator`). Monsters and DM notes are omitted by the owners. The GET publishes no event. |
| `gateway-api` | GET | `/overlay/party-vitals/{session_id}` | Party vitals and camera target as JSON (`position` query: `bottom`, `top`, `sidebar`). Needs a verified bearer token and `session.observe`. The party and the camera come from `board_state`. The gateway serves no HTML: a request with `format=html` or an HTML-only `Accept` header gets `406` with `error: html_not_served`. The OBS page is the App Shell route `#/overlay/party-vitals/:sessionId` (query: `position`, `easing`, `duration`). It reads this JSON route with the viewer's bearer. |
| `gateway-api` | WS | `/ws/overlay/{session_id}` | Real-time spectator WebSocket feed streaming party vitals and camera updates. `turn_started` and `token_moved` frames go to `board_state` (`POST .../camera/turn-started`, `POST .../camera/token-moved`); the owner's camera target is broadcast. A frame that fails the `OverlayFrame` schema gets `INVALID_FRAME`. An owner refusal gets `CAMERA_REJECTED`. An unreachable owner gets `CAMERA_UNAVAILABLE`. The socket stays open after each of these error frames. |
| `gateway-api` | WS | `/ws/spectator/{session_id}` | Real-time spectator WebSocket feed streaming sanitized session state and broadcast updates |
| `gateway-api` | GET | `/readyz` | Kubernetes readiness probe verifying gateway orchestration status |
| `gateway-api` | POST | `/api/v1/soundscape/cue` | Triggers tactical foley sound effects or acoustic stingers (Zanzibar `play` required, proxies to soundscape) |
| `gateway-api` | GET | `/api/v1/soundscape/tension` | Retrieves current session encounter tension score and active stems (proxies to soundscape) |
| `gateway-api` | POST | `/api/v1/soundscape/tension/calculate` | Calculates encounter tension and adapts music stems (proxies to soundscape) |
| `gateway-api` | POST | `/api/v1/soundscape/stems/override` | DM manual mood override forcing stem profile (Zanzibar `run_session`/`manage` required, checked by the owner) |
| `gateway-api` | POST | `/api/v1/soundscape/stems/volume` | Sets stem channel volumes (proxies to soundscape; the owner checks `session.control` or `campaign.run_session`) |
| `gateway-api` | POST | `/api/v1/soundscape/duck` | Engages or releases WebAudio -12dB ducking (proxies to soundscape; the owner checks `session.control`) |
| `gateway-api` | GET | `/api/v1/soundscape/leitmotif/{character_id}` | Retrieves character musical leitmotif timbre configuration (proxies to the owner's `/api/v1/soundscape/leitmotif/profile/{character_id}`) |
| `gateway-api` | POST | `/api/v1/assets/upload` | Proxies to `asset-forge`, which stores binary or base64 assets (battlemap, avatar, audio) to Silo S3. Needs a bearer. The uploader becomes the `forged_asset` creator. An optional `campaign_id` needs `campaign.play` |
| `gateway-api` | GET | `/api/v1/assets/{asset_id}` | Proxies to `asset-forge`. Retrieves or streams stored asset files from Silo S3 storage. The `/stream` and `/download` forms do the same. Needs bearer and `forged_asset.view` (creator or campaign viewer). `401` without a token, `403` without the right |
| `gateway-api` | DELETE | `/api/v1/assets/{asset_id}` | Proxies to `asset-forge`. Deletes an asset. Needs bearer and `forged_asset.manage` (creator, campaign owner, or DM). `401` without a token, `403` without the right |
| `gateway-api` | GET | `/api/v1/compendium/rules/search` | Proxies to `rules_compendium`: hybrid rule search. The query string reaches the owner unchanged. Needs a bearer token (`401` without one) |
| `gateway-api` | GET | `/api/v1/compendium/monsters/{name}` | Proxies to `rules_compendium`: monster stat block. A `campaign_id` query value reads homebrew the caller may view |
| `gateway-api` | GET | `/api/v1/compendium/spells/{name}` | Proxies to `rules_compendium`: spell definition |
| `gateway-api` | GET | `/api/v1/compendium/conditions/{name}` | Proxies to `rules_compendium`: condition mechanics |
| `gateway-api` | POST | `/api/v1/compendium/encounters/balance` | Proxies to `rules_compendium`: encounter balance. A campaign-scoped call needs `campaign.play` (owner check) |
| `gateway-api` | POST | `/api/v1/compendium/homebrew` | Proxies to `rules_compendium`: registers a campaign homebrew rule. The owner checks `manage` or `run_session` and returns `403` otherwise |
| `gateway-api` | GET | `/api/v1/compendium/homebrew/{campaign_id}` | Proxies to `rules_compendium`: campaign homebrew rules the caller may view (`homebrew_rule.view`) |
| `gateway-mcp` | GET/POST | `/mcp/tools` | Lists or registers dynamic FastMCP tools with JSON schema and a declarative handler (ADR-0020). Requires a bearer token (`401` without one). The author is the token subject. Body `author_id` is ignored. The route runs in the MCP process, because that process owns the registry. `gateway-api` returns `404` for it (TASK-0727) |
| `gateway-mcp` | GET/PUT/DELETE | `/mcp/tools/{name}` | Inspects, updates, or deregisters runtime FastMCP tools without server restarts |
| `gateway-mcp` | POST | `/mcp/tools/{name}/execute` | Evaluates a dynamic tool's declarative handler as the verified caller. Requires a bearer token. Body `user_id` is ignored |
| `gateway-mcp` | MCP | `http://gateway-mcp:8012/mcp` (streamable HTTP) | Tabletop tools (`execute_agent_action_plan`, `cast_spell`, `modify_character_hp`, etc.) and resources `session://{session_id}/state` and `encounter://{session_id}/current`. Reached only inside the cluster. The caller sends its bearer on each MCP request. Without a verified bearer the request returns `401` before any tool runs |
| `inference-worker` | GET | `/healthz` | Liveness and readiness check. Reports the active backend and model names. Also served at `/health` |
| `inference-worker` | POST | `/inference/v1/intent` | Parses a natural speech transcript into a `ParsedAction` list (`IntentParseResponse`) |
| `inference-worker` | POST | `/inference/v1/dm-narration` | Generates DM narration and rulings (`DMNarrationResponse`) |
| `inference-worker` | POST | `/inference/v1/stand-in-action` | Generates a stand-in action for an absent player's character (`StandInActionResponse`) |




## Gateway Health Route (`GET /healthz`)

`gateway-api` serves `GET /healthz`, `GET /health`, and `GET /api/v1/health`. The route is public. Each request probes five downstream services in parallel (TASK-0674). Nothing is cached.

| Field | Value |
|---|---|
| `status` | `healthy` while the gateway process runs. A downstream failure does not change it. |
| `downstream_services` | One key for each of `the_watcher`, `game_session`, `board_state`, `character_sheet`, and `voice_agent`. Each value is `operational`, `degraded`, `unreachable`, or `not_configured` |
| `event_publish_failures` | Count of failed event publishes in this process |
| `event_bus` | `connected` or `disconnected` |
| `authorization_engine` | `SpiceDB Zanzibar` |

Each probe sends `GET /healthz` to the service with the service credential (ADR-0015 e). A probe result is:

- `operational`: HTTP 200.
- `degraded`: any other HTTP status.
- `unreachable`: a connect failure, or no answer within `RUNEFOBLE_GATEWAY_HEALTH_PROBE_TIMEOUT_S` (default `1.0` seconds).
- `not_configured`: the matching `RUNEFOBLE_*_URL` variable is unset.

The gateway reads one variable for each probed service. The Helm chart renders them for `gateway-api`: `RUNEFOBLE_WATCHER_URL` (`the_watcher`), `RUNEFOBLE_GAME_SESSION_URL` (`game_session`), `RUNEFOBLE_BOARD_STATE_URL` (`board_state`), `RUNEFOBLE_CHARACTER_SHEET_URL` (`character_sheet`), and `RUNEFOBLE_VOICE_AGENT_URL` (`voice_agent`). See [Service Client](service-client.md#health-probes).

## Gateway WebSocket Authentication

Close codes on every WebSocket route: `1008` means a missing or invalid token. `4403` means an authorization refusal (the token is valid but lacks the object permission). Every gateway WebSocket route (`/ws/*`) takes the caller's identity only from the `runefoble.bearer.<jwt>` subprotocol. The client offers `runefoble.v1` and `runefoble.bearer.<jwt>`. The gateway accepts the handshake with `runefoble.v1`. A handshake without a verified token closes with code `1008` before accept. Identity in the query string (`user_id`, `token`) or in headers (`X-User-Id`, `Authorization`) is refused. A token that is valid but lacks the object permission is refused. `/ws/campaigns/{id}` admits it, sends a `PERMISSION_DENIED` frame, and closes with `4403`. The session sockets (`/ws/session`, `/ws/voice`, `/ws/mobile-companion`, `/ws/overlay`, `/ws/spectator`) need `session.observe` and close with `4403` before accept. They close with `1011` when SpiceDB is unavailable. Overlay and spectator clients that send frames need `session.participate`. The `/ws/voice` and `/ws/mobile-companion` sockets set the room role from the session permissions. `session.control` gives `dungeon_master`, `session.participate` gives `player`, and `session.observe` gives `spectator`. A `role` query parameter does not change it. A `webrtc_join` frame that asks for another role receives `{"type": "error", "code": "ROLE_MISMATCH"}`. A `user_id` in a frame is ignored. `POST /api/v1/mobile/companion/{id}/whisper` and `/turn-alert` need `session.control`. `POST /api/v1/watcher/speak-and-act` needs `session.participate`. All of these return `403` when refused.

### Session WebSocket inbound frames (TASK-0810)

`/ws/session/{id}` admits every `session.observe` caller. Observers receive frames only. Each inbound frame is checked in this order:

1. The text must be a JSON object with a kind. The kind is `type`, or `action` when there is no `type`. Otherwise the gateway sends `INVALID_FRAME` and keeps the socket open.
2. The kind must be one of: `session_started`, `player_readiness`, `player_stand_in`, `token_action`, `aoe_placed`, `spell_vfx`, `confirm_ghost`, `token_moved`, `dice_rolled`, `turn_advanced`, `dm_whisper`. Otherwise the gateway sends `UNKNOWN_FRAME` and does not relay the frame.
3. The caller must hold `session.participate` on the session. Otherwise the gateway sends `PERMISSION_DENIED` (with the `action` field set to the kind) and does not relay the frame. A SpiceDB outage sends `AUTHZ_UNAVAILABLE` and does not relay the frame.

A frame that passes all three checks goes to every socket of the session, sender included. The overlay socket (`/ws/overlay/{id}`) uses the same participate check (`may_publish_frame` in `gateway_api/session_access.py`).

## Voice Agent Identity (TASK-0530)

Every `voice-agent` HTTP route except `GET /healthz` and `GET /ui/manifest` requires `Authorization: Bearer <jwt>`. The service verifies the token against Zitadel (ADR-0015 c). Missing, malformed, or untrusted tokens return `401` with `WWW-Authenticate: Bearer`. `X-User-Id`, `?user_id=`, and `?token=` are ignored.

Every `voice-agent` WebSocket route (`/api/v1/voice/duplex/ws/...`, `/api/v1/voice/stream/ws/...`) admits the handshake only with a valid `runefoble.bearer.<jwt>` subprotocol. The service accepts with `runefoble.v1`. A refused handshake closes with code `1008` before accept.

`game-session` forwards the caller's `Authorization` header on `POST /api/v1/voice/dsp/condition`. `voice-agent` does not accept the service credential yet (ADR-0015 e). Until it does, the caller's token is the only credential for that call.

## Voice Agent Permissions (TASK-0558)

After the bearer token passes, each voice route checks one permission in `libs/runefoble_auth/schema/runefoble.zed`. The check names the action in `ACTION_PERMISSIONS`. SpiceDB failures are not denials.

| Route | Check | Subject |
|---|---|---|
| `POST /api/v1/voice/rooms/{session_id}/kick` | `session.control` | Token subject |
| `POST /api/v1/voice/modulate` | `session.participate` | Token subject |
| `POST /api/v1/voice/aec/benchmark` | `session.control` | Token subject |
| `GET /api/v1/voice/streams/{session_id}/quality`, `POST /api/v1/voice/streams/{session_id}/report` | `session.control` | Token subject |
| `GET /api/v1/voice/duplex/status/{session_id}` | `session.observe` | Token subject |
| `POST /api/v1/voice/duplex/playback/start` | `session.participate` | Token subject |
| `POST /api/v1/voice/synthesize` | Speaker rule | `speaker_id` |
| `POST /api/v1/voice/dsp/apply` | Speaker rule | `speaker_id` |
| `POST /api/v1/voice/filters/barge-in/evaluate` | Speaker rule | `speaker_id` |
| `POST /api/v1/voice/transcribe` | Speaker rule | `speaker_id` |
| `POST /api/v1/voice/stream/chunk` | Speaker rule | `speaker_id` |
| `WS /api/v1/voice/duplex/ws/...` | Speaker rule at connect | `speaker_id` |
| `WS /api/v1/voice/stream/ws/...` | Speaker rule for each new session and speaker pair | `speaker_id` |

The speaker rule has two parts. The named speaker must hold `session.participate`. The token subject may act for another speaker only when the token subject holds `session.control`. A WebSocket handshake or frame that names a speaker the token subject may not act for closes the socket with `4403` (authorization refusal). A missing or invalid token still closes with `1008`.

`session.control` resolves to `campaign->run_session` through the session's campaign relation. A DM holds it. A player and a spectator do not.

| Condition | Response |
|---|---|
| Permission denied | `403` with `{"detail": {"error": "permission_denied", "required_permission": "...", "resource": "...", "subject": "..."}}` |
| SpiceDB unreachable or timed out | `503` with `{"error": "authorization_unavailable"}` |
| Schema mismatch (a name is not in `runefoble.zed`) | `500` with `{"error": "authorization_schema_error", "error_id": "<uuid>"}`. The gRPC detail stays in the log. |

The gateway mounts the voice room and stream diagnostics routers. It registers the same handlers through `runefoble_auth.authz_http.install_authz_error_handlers`.

## Gateway Proxy Identity and Errors

A gateway proxy route forwards the caller's bearer token to the owning service. The owning service verifies it (ADR-0015 c). Some proxy routes also run the gateway identity dependency first. The asset, forge, voice, and companion proxies do not, so the owning service is their only identity check. The full contract is in [Identity and Token Contract](identity-and-token-contract.md).

- The gateway copies the `Authorization` header to the upstream request. It sends the `X-Runefoble-Service-Credential` header and the W3C `traceparent` header on every call. It forwards no other header from the client. A client `X-User-Id` header is not forwarded.
- An upstream `2xx` or `4xx` answer returns to the client with the same status and body.
- An upstream `5xx` returns `502` with `{"detail": "Upstream service is unavailable", "upstream": "<service>"}`.
- A connection failure, a timeout, or an unset base URL returns `503` with the same body shape.
- A `2xx` answer with a non-JSON body returns `502`.

The gateway reads each owning service base URL once, at start-up. The variables are `RUNEFOBLE_CAMPAIGN_LORE_URL`, `RUNEFOBLE_CAMPAIGN_ANALYTICS_URL`, `RUNEFOBLE_SOUNDSCAPE_URL`, and `RUNEFOBLE_CHARACTER_SHEET_URL`. The gateway builds one shared client for each service. See [Service Client](service-client.md).

### Shared-World Caravan Routes (TASK-0807)

The gateway forwards these routes to `game_session` with the caller's bearer token. The status and body of the owner answer pass through. The request and response shapes are those of the owner. A stranger gets the owner's `403`.

| Method | Gateway path | Owner |
|---|---|---|
| `POST` | `/api/v1/shared-worlds` | `game_session` |
| `POST` | `/api/v1/shared-worlds/{shared_world_id}/caravans/contracts` | `game_session` |
| `GET` | `/api/v1/shared-worlds/{shared_world_id}/caravans/contracts` | `game_session` |
| `GET` | `/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}` | `game_session` |
| `POST` | `/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}/accept` | `game_session` |
| `POST` | `/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}/dispatch` | `game_session` |
| `POST` | `/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}/ambush` | `game_session` |
| `POST` | `/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}/fulfill` | `game_session` |

The gateway reads `RUNEFOBLE_GAME_SESSION_URL` at start-up. See [Coordinate West Marches and Caravans](../how-to/coordinate-west-marches-shared-world-and-caravans.md).

### Audience Routes (TASK-0439)

The gateway forwards these routes to `audience_studio` with the caller's bearer token. The owner checks every permission (`audience_poll.view`, `vote`, `moderate`, `approve`, `veto`). The gateway adds no check. The status and body of the owner answer pass through.

| Method | Gateway path | Owner |
|---|---|---|
| `POST` | `/api/v1/audience/polls` | `audience_studio` |
| `GET` | `/api/v1/audience/polls` | `audience_studio` |
| `GET` | `/api/v1/audience/polls/{poll_id}` | `audience_studio` |
| `POST` | `/api/v1/audience/polls/{poll_id}/votes` | `audience_studio` |
| `POST` | `/api/v1/audience/polls/{poll_id}/close` | `audience_studio` |
| `GET` | `/api/v1/audience/proposals` | `audience_studio` |
| `POST` | `/api/v1/audience/proposals/{proposal_id}/approve` | `audience_studio` |
| `POST` | `/api/v1/audience/proposals/{proposal_id}/veto` | `audience_studio` |
| `WS` | `/ws/audience/{campaign_id}` | `audience_studio` |

The gateway reads `RUNEFOBLE_AUDIENCE_STUDIO_URL` at start-up. A refused handshake or a refused socket close code passes through the WebSocket relay. See [Orchestrate Audience Chaos Polls](../how-to/orchestrate-audience-chaos-polls.md).

### Voice Agent TTS Response (`POST /api/v1/voice/synthesize`)

The response describes the audio it carries. Filters run on the synthesised clip only.

| Field | Type | Meaning |
|---|---|---|
| `audio_base64` | string | Base64 of a RIFF/WAVE file (mono, 16-bit PCM) at `sample_rate_hz`. |
| `audio_mime_type` | string | Always `audio/wav`. |
| `sample_rate_hz` | integer | Sample rate of the WAV samples. |
| `duration_ms` | number | Sample count divided by `sample_rate_hz`, in milliseconds. |
| `content_sha256` | string | SHA-256 of the decoded WAV bytes. Equal text gives an equal hash. |
| `engine` | string | Speech engine that rendered the text (`espeak-ng`). |
| `original_text`, `conditioned_text` | string | Input text and the text after affliction transforms. `conditioned_text` is metadata and is not voiced. |
| `effects_applied`, `dsp_parameters`, `latency_ms`, `persona_used` | mixed | DSP and request metadata. |

Engine failure returns `503` with `{"detail": {"error": "speech_synthesis_unavailable", "engine": "espeak-ng", "message": "..."}}`. No audio field is present.

## Service Bearer Token Verification

`asset-forge`, `soundscape`, and `character-sheet` verify the Zitadel bearer token on every route. A request without a valid `Authorization: Bearer <token>` header returns `401`. The `X-User-Id` header is ignored. The creator, owner, or caller is the token `sub`.

Public routes: `/healthz`, `/health`, `/ui/manifest`, and `/openapi.json`.

The shared settings are `RUNEFOBLE_ZITADEL_ISSUER`, `RUNEFOBLE_ZITADEL_AUDIENCE`, and `RUNEFOBLE_ZITADEL_INTERNAL_URL`. The Helm chart sets them for each service. The audience comes from the Secret `runefoble-zitadel-client`.

## Removed Identity Routes

These paths have no route in the gateway. Use the replacement. The full table is in [Identity and Token Contract](identity-and-token-contract.md#6-removed-routes-and-replacements).

| Removed path | Replacement |
|---|---|
| `POST /api/v1/auth/token`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout` | Zitadel OIDC in the App Shell (`frontend/src/auth/oidc-client.ts`) |
| `POST /api/v1/auth/register`, `/verify`, `/verify-email`, `/resend-verification` | Zitadel hosted sign-up (`prompt=create`) |
| `POST /api/v1/auth/admin/seed`, `POST /api/v1/auth/admin/invite` | None. Use `POST /api/v1/campaigns/{campaign_id}/invites`. |
| `POST /api/v1/auth/dev/send-test`, `POST /api/v1/auth/test-email`, `DELETE /api/v1/auth/dev/emails` | Mailpit at `/mail` |
| `POST /api/v1/auth/sync/user` | None. Token claims grant no relation. |
| `POST /api/v1/auth/sync/membership`, `/character-ownership`, `/token-binding` | `POST /api/v1/campaigns/{campaign_id}/roles`, `POST /api/v1/characters`, `POST /api/v1/campaigns/join` |

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


