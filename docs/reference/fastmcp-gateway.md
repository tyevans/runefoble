# FastMCP Gateway Reference

The FastMCP Gateway (`gateway/mcp`) exposes Runefoble tabletop actions, spatial queries, character sheet mutations, and Game Master controls to external LLMs and internal agents via the Model Context Protocol (MCP).

## Architecture

The gateway server entrypoint (`gateway/mcp/src/gateway_mcp/server.py`) operates as a lightweight orchestration shell (< 100 lines) delegating domain capabilities to modular sub-packages:

gateway/mcp/src/gateway_mcp/
├── clients/               # HTTP clients for owning services (board_state, character_sheet, game_session, rules_compendium)
│   └── services.py        # Typed async client and ServiceError types
├── dynamic/               # Dynamic tool registry package (< 140 lines per module)
│   ├── auth.py            # SpiceDB Zanzibar authorization guard & relationship sync
│   ├── builder.py         # Signature builder and callable adapter
│   ├── events.py          # Redis Streams system event bus integration
│   ├── models.py          # Dynamic tool schemas and JSON Schema validation
│   └── registry.py        # Thread-safe tool registry with event notifications
├── routers/               # FastMCP REST routers (< 130 lines)
│   └── tools_registry.py  # REST endpoints for dynamic tool registration & lifecycle
├── asgi.py                # ASGI app (`gateway_mcp.asgi:app`) for the streamable HTTP endpoint
├── main.py                # CLI execution wrapper
├── server.py              # FastMCP orchestration shell, module mounting, and `main()`
├── settings.py            # Required upstream service URLs and the GATEWAY_MCP_HOST/PORT listen address
├── tools/                 # MCP tool implementations (< 180 lines each)
│   ├── dice.py            # Dice notation parsing and rolling (roll_dice)
│   ├── board.py           # Tactical board and encounter tools (HTTP-backed by board_state)
│   ├── character.py       # Character stats, HP, spells, conditions, inventory (HTTP-backed by character_sheet)
│   └── orchestration.py   # The Watcher narration and agent action plan execution
├── resources/             # FastMCP dynamic resource providers (< 120 lines each)
│   └── session.py         # Session context and combat encounter resources
└── prompts/               # FastMCP prompt templates (< 120 lines each)
    └── narrative.py       # Narrative DM guidance and tactical action adviser
```

## Transport

The gateway serves the MCP protocol over **streamable HTTP** only. The endpoint is `/mcp`.

| Setting | Environment Variable | Default |
|---|---|---|
| Bind address | `GATEWAY_MCP_HOST` | `0.0.0.0` |
| Bind port | `GATEWAY_MCP_PORT` | `8012` |

- Run locally: `uv run python -m gateway_mcp.main` (or `gateway_mcp.main` after `uv sync`). Set the five upstream URLs first.
- Container: `gateway_mcp.asgi:app` under uvicorn, port `8012`. The Helm Deployment `gateway-mcp` and ClusterIP Service `gateway-mcp` expose it inside the cluster only. No ingress rule routes to it.
- The process stops at start-up when an upstream URL is unset. The error names the variable.
- The server keeps session state in memory. Run one replica.
- The stdio transport is removed. No developer tool in this repository uses it.
- The endpoint has no OpenAPI document and no `/healthz`. The Helm readiness probe checks the TCP port.

## Tools Registry

All tools are registered onto FastMCP and callable by agents or action orchestrators:

| Tool Name | Parameters | Description |
|---|---|---|
| `roll_dice` | `notation: str`, `reason: str` | Parse standard RPG dice notation (`1d20+3`, `2d6`) and return roll breakdown. |
| `inspect_tactical_board` | `session_id: str` | Read tokens, positions, HP, and grid dimensions from `board_state` (`GET /api/v1/boards/{session_id}`). Returns an error result when the board does not exist. |
| `move_board_token` | `session_id: str`, `token_id: str`, `to_x: int`, `to_y: int` | Move a token through `board_state` (`POST /api/v1/boards/{session_id}/tokens/{token_id}/move`). The board rejects out-of-bounds moves. |
| `get_character_sheet` | `character_id: str` | Read the stored sheet from `character_sheet` (`GET /api/v1/characters/{character_id}`): name, class, level, HP, armor class, ability scores, spell slots, equipment, inventory, conditions, and penalties. An unknown id returns a tool error. |
| `inspect_inventory` | `character_id: str` | Read equipped items and carried inventory from `character_sheet`. |
| `apply_absentee_penalty` | `character_id: str`, `penalty_type: str`, `explanation: str` | Impose a session miss penalty (`drunk`, `foolishness`, `cowardice`, `greed`, `curse`) through `character_sheet` (`POST /api/v1/characters/{character_id}/penalties`). Returns the active penalties. |
| `cast_spell` | `character_id: str`, `spell_name: str`, `spell_level: int` | Expend a spell slot through `character_sheet` (`POST /api/v1/characters/{character_id}/spells/cast`). Returns the remaining spell slots. A `spell_level` of 0 asks the sheet to use the standard level of the spell. An empty slot level returns a tool error. The sheet does not store a target. |
| `modify_character_hp` | `character_id: str`, `delta: int`, `damage_type: str`, `reason: str` | Apply damage (negative `delta`) or healing through `character_sheet` (`POST /api/v1/characters/{character_id}/health`). Returns the stored `current_hp`, `max_hp`, and stabilization state. The `damage_type` and `reason` are recorded in the change source. |
| `add_condition` / `apply_condition` | `character_id: str`, `condition: str`, `duration_rounds: int`, `source: str` | Impose a status condition through `character_sheet` (`POST /api/v1/characters/{character_id}/conditions`). Returns the active conditions. Both tools share one route. |
| `query_encounter_state` | `encounter_id: str` | Read an encounter. Round, active combatant, and turn order come from `game_session` (`GET /api/v1/sessions/{session_id}/combat`). Tokens, grid, and active hazards come from `board_state`. The `encounter_id` is the game session id. Returns `in_combat`, `round`, `active_combatant_id`, `turn_order`, `session_id`, `grid_dimensions`, `tokens`, and `active_hazards`. |
| `create_encounter` | `session_id: str`, `enemies: list[{name, x, y, hp?}]` | Start combat in `game_session` (`POST /api/v1/sessions/{session_id}/combat/start`) with one combatant per enemy. Fetch or create the 10x8 board for the session in `board_state`, then place each enemy as a monster token that is not friendly. The `session_id` is the encounter id. Returns `encounter_id` (equal to `session_id`), `grid`, `enemies_spawned`, `in_combat`, `round`, `active_combatant_id`, and `turn_order`. An unknown or unavailable session returns a tool error and creates no board. |
| `narrate_with_the_watcher` | `campaign_id: str`, `session_id: str`, `scene_prompt: str`, `player_actions: str`, `scene_environment: str`, `tone: str` (default `dark_fantasy`) | Call The Watcher route `POST /api/v1/watcher/narrate`. Returns The Watcher response unchanged: `narrative`, `sensory_details`, `suggested_dm_prompts`, `tension_level`, `source`, and `degraded`. The gateway adds no narration of its own. If the inference worker fails, the tool returns an error. |
| `execute_agent_action_plan` | `session_id: str`, `campaign_id: str`, `actions: list[{tool, actor_name, description?, parameters}]` | Propose each step to The Watcher (`POST /api/v1/watcher/actions/propose`), in order. Each step returns the pending action that The Watcher stored. The DM can veto or change a pending action before it takes effect. No board state changes in this tool. Planning stops at the first failed step. An unknown tool name fails its step before any call. |
| `query_monster_stat_block` | `monster_name: str` | Read the monster stat block from `rules_compendium` (`GET /api/v1/compendium/monsters/{name}`). An unknown name returns a tool error. |
| `calculate_encounter_balance` | `party_levels: list[int]`, `target_difficulty: str` | Call the `rules_compendium` route `POST /api/v1/compendium/encounters/balance`. Returns its CR XP thresholds and recommended monster group. |

### Upstream Service Calls

Board, encounter, and character tools hold no board, combat, or character state. They call the owning services over HTTP through `gateway/mcp/src/gateway_mcp/clients/services.py`:

| Setting | Environment Variable | Default | Owning Service |
|---|---|---|---|
| `board_state_url` | `BOARD_STATE_URL` | Required | `board_state` |
| `character_sheet_url` | `CHARACTER_SHEET_URL` | Required | `character_sheet` |
| `game_session_url` | `GAME_SESSION_URL` | Required | `game_session` |
| `rules_compendium_url` | `RULES_COMPENDIUM_URL` | Required | `rules_compendium` |
| `the_watcher_url` | `THE_WATCHER_URL` | Required | `the_watcher` |

The Helm chart renders these from `services.gatewayMcp` in `values.yaml`. Local runs must export them. There are no localhost defaults.

The client forwards the `Authorization: Bearer` token of the MCP request, when the transport carries one. The gateway never creates a token. Without a token, the client sends no `Authorization` header. The upstream service then decides the result.

An upstream 5xx status or an unreachable service raises `ServiceUnavailableError`. An upstream 4xx status raises `ServiceRejectedError`. FastMCP reports both to the caller as an MCP tool error result. The gateway never returns fallback data.

## Resources Registry

Dynamic FastMCP resources supply structured context to LLMs without requiring explicit parameter passing:

| Resource URI | MIME Type | Description |
|---|---|---|
| `session://{session_id}/state` | `application/json` | Stored session state from `game_session` (`GET /api/v1/sessions/{session_id}`): title, status, turn, combat round, and participants. An unknown session id returns a resource error. |
| `encounter://{session_id}/current` | `application/json` | Encounter of a game session: tokens, grid, and hazards from `board_state`, plus round and turn order from `game_session`. The session id is the encounter id. An unknown id returns a resource error. |

The `session://active` and `encounter://current` resources were removed. They had no session id, so they could not read the session that a caller asked for.

## Prompt Templates

Prompt templates provide standardized prompts for LLM decision-making and narration:

| Prompt Name | Arguments | Description |
|---|---|---|
| `dm_narrative_guidance` | `scene_context: str`, `mood: str` | Formats Watcher AI DM sensory and environmental narrative cues. |
| `tactical_action_adviser` | `tactical_situation: str`, `character_role: str` | Provides combat analysis and optimal action recommendations. |

## Dynamic Runtime Tool Registry

The Dynamic Tool Registry (`gateway/mcp/src/gateway_mcp/dynamic/`) enables tabletop creators, homebrew modders, and external developers to register, update, and hot-reload custom FastMCP tools dynamically at runtime with SpiceDB authorization checks, without restarting the FastMCP gateway or terminating active AI agent sessions (ADR-0001, ADR-0003, ADR-0006, ADR-0007, ADR-0008, TASK-0172).

### Administrative REST Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/mcp/tools/dynamic` (alias: `/mcp/tools`) | List all dynamically registered tools and JSON Schemas |
| `POST` | `/mcp/tools/register` (alias: `/mcp/tools`) | Register a new dynamic tool with parameter validation and SpiceDB authorization. A non-empty declarative `handler` is required; a definition without one returns HTTP 422 and adds no tool. An invalid handler returns HTTP 400 |
| `GET` | `/mcp/tools/{name}` | Retrieve schema and configuration for a specific dynamic tool |
| `PUT` | `/mcp/tools/{name}` | Update an existing dynamic tool definition and hot-reload logic |
| `DELETE` | `/mcp/tools/{tool_name}` | Deregister a dynamic tool and revoke permissions |
| `POST` | `/mcp/tools/{name}/execute` | Invoke a dynamic tool directly via HTTP frontdoor with auth checks |

### SpiceDB Zanzibar Object-Level Authorization

Dynamic tools are guarded by SpiceDB object-level Zanzibar permissions defined in `libs/runefoble_auth/schema/runefoble.zed`:

```zed
definition mcp_tool {
    relation campaign: campaign
    relation author: user

    permission view = author + campaign->view
    permission manage = author + campaign->manage + campaign->run_session
    permission execute = author + campaign->play + manage
}
```

- **Tool Management (`manage`)**: Creating, updating, or deleting custom tools requires the tool author (`author: user`) or campaign DM/GM/Owner (`campaign->run_session`).
- **Tool Execution (`execute`)**: Invoking tools requires campaign players (`campaign->play`), DM/GMs (`campaign->run_session`), or the author.

### Redis Streams Event Notifications

Dynamic tool lifecycle events are published to Redis Streams topic `runefoble.events.system`:
- **`DynamicToolRegisteredEvent`**: Emitted when a dynamic tool is registered or hot-reloaded.
- **`DynamicToolUnregisteredEvent`**: Emitted when a dynamic tool is retired or removed.
- **`DynamicToolInvokedEvent`**: Emitted upon dynamic tool execution with execution duration and telemetry.

The gateway API injects the Redis Streams bus when its module loads (`configure_dynamic_tool_event_bus` in `gateway/api/src/gateway_api/main.py`) from `REDIS_URL`. Startup fails when `REDIS_URL` is empty. The gateway MCP package has no in-memory fallback bus.

A failed publish is not silent. The gateway logs an `ERROR` record that names the event type and the cause. It also adds a `dynamic_tool_event_dropped` event to the active OpenTelemetry span. This applies to a missing bus, a Redis error, and a dispatch with no running event loop.

### Declarative Handlers (ADR-0020)

A dynamic tool handler is a JSON result template. The gateway runs no caller code. `exec`, `eval`, and `compile` are never used on caller input.

| Element | Result |
|---|---|
| `"${name}"` | The argument `name`, type kept |
| `"text ${name}"` | A string with argument values inserted |
| `{"$expr": "..."}` | A number. Allowed: numbers, parameter names, `+ - * / // %`, unary signs, parentheses, `max`, `min`, `abs`, `round`. Limits: 200 characters, 64 elements |
| `{"$dice": "NdS+M"}` | Total of N S-sided dice plus M. Limits: 100 dice, 1000 sides |
| object, list | Evaluated member by member. Limit: 8 levels, 200 elements |

Registration returns HTTP 400 for an unknown parameter name, an unknown `$` directive, a malformed expression, or a limit breach. Execution returns HTTP 400 for an arithmetic error. Calls from one tool to another tool are not supported.

Parameters are validated with JSON Schema Draft-07 at registration.


