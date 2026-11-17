# FastMCP Gateway Reference

The FastMCP Gateway (`gateway/mcp`) exposes Runefoble tabletop actions, spatial queries, character sheet mutations, and Game Master controls to external LLMs and internal agents via the Model Context Protocol (MCP).

## Architecture

The gateway server entrypoint (`gateway/mcp/src/gateway_mcp/server.py`) operates as a lightweight orchestration shell (< 80 lines) delegating domain capabilities to modular sub-packages:

gateway/mcp/src/gateway_mcp/
├── clients/               # HTTP clients for owning services (board_state, rules_compendium)
│   └── services.py        # Typed async client and ServiceError types
├── constants.py           # RPG constants (spell effects, condition descriptions)
├── dynamic_registry.py    # Backward-compatible re-exports (< 30 lines)
├── dynamic/               # Dynamic tool registry package (< 140 lines per module)
│   ├── auth.py            # SpiceDB Zanzibar authorization guard & relationship sync
│   ├── builder.py         # Signature builder and callable adapter
│   ├── events.py          # Redis Streams system event bus integration
│   ├── models.py          # Dynamic tool schemas and JSON Schema validation
│   └── registry.py        # Thread-safe tool registry with event notifications
├── routers/               # FastMCP REST routers (< 130 lines)
│   └── tools_registry.py  # REST endpoints for dynamic tool registration & lifecycle
├── main.py                # CLI execution wrapper
├── server.py              # FastMCP orchestration shell and module mounting
├── settings.py            # Upstream service URLs (BOARD_STATE_URL, RULES_COMPENDIUM_URL)
├── tools/                 # MCP tool implementations (< 180 lines each)
│   ├── dice.py            # Dice notation parsing and rolling (roll_dice)
│   ├── board.py           # Tactical board and encounter tools (HTTP-backed by board_state)
│   ├── character.py       # Character stats, HP, spells, conditions, inventory
│   └── orchestration.py   # The Watcher narration and agent action plan execution
├── resources/             # FastMCP dynamic resource providers (< 120 lines each)
│   └── session.py         # Session context and combat encounter resources
└── prompts/               # FastMCP prompt templates (< 120 lines each)
    └── narrative.py       # Narrative DM guidance and tactical action adviser
```

## Tools Registry

All tools are registered onto FastMCP and callable by agents or action orchestrators:

| Tool Name | Parameters | Description |
|---|---|---|
| `roll_dice` | `notation: str`, `reason: str` | Parse standard RPG dice notation (`1d20+3`, `2d6`) and return roll breakdown. |
| `inspect_tactical_board` | `session_id: str` | Read tokens, positions, HP, and grid dimensions from `board_state` (`GET /api/v1/boards/{session_id}`). Returns an error result when the board does not exist. |
| `move_board_token` | `session_id: str`, `token_id: str`, `to_x: int`, `to_y: int` | Move a token through `board_state` (`POST /api/v1/boards/{session_id}/tokens/{token_id}/move`). The board rejects out-of-bounds moves. |
| `get_character_sheet` | `character_id: str` | Retrieve character stats, level, hit points, equipment, and active conditions. |
| `inspect_inventory` | `character_id: str` | Retrieve equipped items, carried inventory, and currency breakdown. |
| `apply_absentee_penalty` | `character_id: str`, `penalty_type: str`, `explanation: str` | Impose session miss penalties (`drunk`, `foolishness`) on absent player PCs. |
| `cast_spell` | `character_id: str`, `spell_name: str`, `spell_level: int`, `target: str` | Cast a spell, tracking spell slot expenditure and mechanical rules. |
| `modify_character_hp` | `character_id: str`, `delta: int`, `damage_type: str`, `reason: str` | Apply damage or healing, calculating `bloodied` or `unconscious` states. |
| `add_condition` / `apply_condition` | `character_id: str`, `condition: str`, `duration_rounds: int`, `source: str` | Impose status condition (`blinded`, `prone`, `frightened`) with rule effects. |
| `query_encounter_state` | `encounter_id: str` | Read the encounter board from `board_state`: tokens, grid, and active hazards. Turn order and round number are not yet tracked by the board service. |
| `create_encounter` | `encounter_name: str`, `terrain: str`, `enemies: list[{name, x, y, hp?}]` | Create a 10x8 board in `board_state` and place enemy monster tokens. Returns the board session id as `encounter_id`. |
| `narrate_with_the_watcher` | `scene_prompt: str`, `player_actions: str` | Invoke The Watcher AI GM for immersive narration and environmental cues. |
| `execute_agent_action_plan` | `session_id: str`, `actions: list` | Sequentially execute multi-turn action plan with step validation and timing. |
| `query_monster_stat_block` | `monster_name: str` | Retrieve full canonical monster stat block, AC, HP, CR, actions, and traits. |
| `calculate_encounter_balance` | `party_levels: list[int]`, `target_difficulty: str` | Call the `rules_compendium` route `POST /api/v1/compendium/encounters/balance`. Returns its CR XP thresholds and recommended monster group. |

### Upstream Service Calls

Board and encounter tools hold no board state. They call the owning service over HTTP through `gateway_mcp/clients/services.py`:

| Setting | Environment Variable | Default | Owning Service |
|---|---|---|---|
| `board_state_url` | `BOARD_STATE_URL` | `http://localhost:8002` | `board_state` |
| `rules_compendium_url` | `RULES_COMPENDIUM_URL` | `http://localhost:8007` | `rules_compendium` |

An upstream 5xx status or an unreachable service raises `ServiceUnavailableError`. An upstream 4xx status raises `ServiceRejectedError`. FastMCP reports both to the caller as an MCP tool error result. The gateway never returns fallback data.

## Resources Registry

Dynamic FastMCP resources supply structured context to LLMs without requiring explicit parameter passing:

| Resource URI | MIME Type | Description |
|---|---|---|
| `session://active` | `application/json` | Active session state including tokens, threat level, and scene atmosphere. |
| `session://{session_id}/state` | `application/json` | Specific session state including active tokens and atmosphere. |
| `encounter://current` | `application/json` | Board state (tokens, grid, and hazards) of the active encounter. |

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
| `POST` | `/mcp/tools/register` (alias: `/mcp/tools`) | Register a new dynamic tool with parameter validation and SpiceDB authorization. A non-blank `handler_code` is required; a definition without one returns HTTP 422 and adds no tool |
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

Dynamic tool lifecycle events are published to Redis Streams topic `runefoble:events:system`:
- **`DynamicToolRegisteredEvent`**: Emitted when a dynamic tool is registered or hot-reloaded.
- **`DynamicToolUnregisteredEvent`**: Emitted when a dynamic tool is retired or removed.
- **`DynamicToolInvokedEvent`**: Emitted upon dynamic tool execution with execution duration and telemetry.

The gateway API injects the Redis Streams bus at startup (`configure_dynamic_tool_event_bus` in `gateway/api/src/gateway_api/main.py`) from `REDIS_URL`. Startup fails when `REDIS_URL` is empty. The gateway MCP package has no in-memory fallback bus.

A failed publish is not silent. The gateway logs an `ERROR` record that names the event type and the cause. It also adds a `dynamic_tool_event_dropped` event to the active OpenTelemetry span. This applies to a missing bus, a Redis error, and a dispatch with no running event loop.

### Security & Sandbox Policies

Dynamic tool definitions containing custom Python logic (`handler_code`) undergo strict AST static analysis and sandboxed execution:
- **Forbidden Imports**: `os`, `sys`, `subprocess`, `shutil`, `socket`, `urllib`, `requests`, `httpx`, `pathlib`, `builtins`, `importlib`.
- **Forbidden Functions**: `open`, `eval`, `exec`, `compile`, `__import__`, `globals`, `locals`, `exit`, `quit`.
- **Attribute Access Restrictions**: Access to dunder attributes (e.g. `__class__`, `__subclasses__`, `__globals__`, `__code__`) is rejected.
- **Allowed Modules**: Safe modules such as `math`, `json`, `re`, `random`.
- **Parameter Validation**: Enforced via JSON Schema Draft-07 specifications with type matching across Python signatures.


