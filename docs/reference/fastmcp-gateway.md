# FastMCP Gateway Reference

The FastMCP Gateway (`gateway/mcp`) exposes Runefoble tabletop actions, spatial queries, character sheet mutations, and Game Master controls to external LLMs and internal agents via the Model Context Protocol (MCP).

## Architecture

The gateway server entrypoint (`gateway/mcp/src/gateway_mcp/server.py`) is a short orchestration shell. `build_mcp(container)` imports each registration hook from its defining module and calls it. The package `__init__.py` files hold only a docstring and export no names:

gateway/mcp/src/gateway_mcp/
├── caller.py              # Reads the MCP caller's bearer token from the request
├── container.py           # GatewayMcpContainer (registry, permission port, service client pool) and bind_container
├── fastmcp_tools.py       # The one adapter over FastMCP tool registration and lookup
├── permissions.py         # PermissionChecker port, PermissionDenied, AuthorizationUnavailable, and the SpiceDB adapter
├── service_clients.py     # ServiceClientPool: one shared service client per event loop, service, and base URL
├── owning_services.py     # Route helpers for owning services (board_state, character_sheet, game_session, rules_compendium, the_watcher) over the shared service client
├── dynamic/               # Dynamic tool registry package (< 140 lines per module)
│   ├── auth.py            # Authorization functions over the permission port (grant, revoke, check, enforce)
│   ├── builder.py         # Signature builder and callable adapter
│   ├── expressions.py     # Allow-list interpreter for arithmetic and dice expressions (ADR-0020)
│   ├── handlers.py        # Declarative handler validation and evaluation (ADR-0020)
│   ├── models.py          # Dynamic tool schemas and JSON Schema validation
│   └── registry.py        # Thread-safe tool registry, bound to one FastMCP app and one permission port
├── routers/               # FastMCP REST routers (< 130 lines)
│   └── tools_registry.py  # REST endpoints for dynamic tool registration & lifecycle
├── asgi.py                # ASGI app (`gateway_mcp.asgi:app`) for the streamable HTTP endpoint
├── main.py                # `python -m gateway_mcp.main` runs `server.main()`
├── server.py              # `build_mcp(container)` and `build_http_app(container)`, plus `main()`
├── settings.py            # Required upstream service URLs and the GATEWAY_MCP_HOST/PORT listen address
├── tools/                 # MCP tool implementations (< 180 lines each)
│   ├── dice.py            # Dice notation parsing and rolling (roll_dice)
│   ├── board.py           # Tactical board and encounter tools (HTTP-backed by board_state)
│   ├── character.py       # Character stats, HP, spells, conditions, inventory (HTTP-backed by character_sheet)
│   ├── compendium.py      # Monster stat blocks and encounter balance (HTTP-backed by rules_compendium)
│   ├── orchestration.py   # The Watcher narration and agent action plan execution
│   └── plan.py            # Action plan steps: map, validate, then authorize and propose (run_plan)
├── resources/             # FastMCP dynamic resource providers (< 120 lines each)
│   └── session.py         # Session context and combat encounter resources
└── prompts/               # FastMCP prompt templates (< 120 lines each)
    └── narrative.py       # Narrative DM guidance and tactical action adviser
```

## Transport

The gateway serves the MCP protocol over **streamable HTTP** only. The endpoint is `/mcp`.

Every request to `/mcp` must carry `Authorization: Bearer <token>`. The gateway verifies the token (RS256 signature, issuer, audience, expiry, subject) before the MCP server reads the message. A request without a verified token gets HTTP `401` with `WWW-Authenticate: Bearer`, and no tool runs (ADR-0015 c, TASK-0532). `/healthz` is the only public route.

| Setting | Environment Variable | Default |
|---|---|---|
| Bind address | `GATEWAY_MCP_HOST` | `0.0.0.0` |
| Bind port | `GATEWAY_MCP_PORT` | `8012` |

- Run locally: `uv run python -m gateway_mcp.main` (or `gateway_mcp.main` after `uv sync`). Set the five upstream URLs first.
- Container: `gateway_mcp.asgi:app` under uvicorn, port `8012`. The Helm Deployment `gateway-mcp` and ClusterIP Service `gateway-mcp` expose it inside the cluster only. No ingress rule routes to it.
- The process stops at start-up when an upstream URL is unset. The error names the variable.
- The server keeps session state in memory. Run one replica.
- The stdio transport is removed. No developer tool in this repository uses it.
- The endpoint has no OpenAPI document. `/healthz` is public and reports the count of event publish failures. The Helm readiness probe checks the TCP port.

## Tools Registry

All tools are registered onto FastMCP and callable by agents or action orchestrators:

| Tool Name | Parameters | Description |
|---|---|---|
| `roll_dice` | `notation: str`, `reason: str` | Roll standard RPG dice notation (`1d20+3`, `2d6`, `2d20kh1+3`) through `runefoble_platform.dice.parse_and_roll`. Returns the roll breakdown (`formula`, `rolls`, `kept_rolls`, `modifier`, `total`, `is_crit`, `is_fumble`) and `reason`. Bad notation, such as `1d20abc`, is a tool error. No default roll is made. |
| `inspect_tactical_board` | `session_id: str` | Read tokens, positions, HP, and grid dimensions from `board_state` (`GET /api/v1/boards/{session_id}`). Returns an error result when the board does not exist. |
| `move_board_token` | `session_id: str`, `token_id: str`, `to_x: int`, `to_y: int` | Move a token through `board_state` (`POST /api/v1/boards/{session_id}/tokens/{token_id}/move`). The board rejects out-of-bounds moves. |
| `get_character_sheet` | `character_id: str` | Read the stored sheet from `character_sheet` (`GET /api/v1/characters/{character_id}`): name, class, level, HP, armor class, ability scores, spell slots, equipment, inventory, conditions, and penalties. The caller needs `character.view`. A caller without it gets a tool error and no sheet data. |
| `inspect_inventory` | `character_id: str` | Read equipped items and carried inventory from `character_sheet`. The caller needs `character.view`. A caller without it gets a tool error and no inventory data. |
| `apply_absentee_penalty` | `character_id: str`, `penalty_type: str`, `explanation: str` | Impose a session miss penalty (`drunk`, `foolishness`, `cowardice`, `greed`, `curse`) through `character_sheet` (`POST /api/v1/characters/{character_id}/penalties`). Returns the active penalties. |
| `cast_spell` | `character_id: str`, `spell_name: str`, `spell_level: int` | Expend a spell slot through `character_sheet` (`POST /api/v1/characters/{character_id}/spells/cast`). Returns the remaining spell slots. A `spell_level` of 0 asks the sheet to use the standard level of the spell. An empty slot level returns a tool error. The sheet does not store a target. |
| `modify_character_hp` | `character_id: str`, `delta: int`, `damage_type: str`, `reason: str` | Apply damage (negative `delta`) or healing through `character_sheet` (`POST /api/v1/characters/{character_id}/health`). Returns the stored `current_hp`, `max_hp`, and stabilization state. The `damage_type` and `reason` are recorded in the change source. |
| `add_condition` / `apply_condition` | `character_id: str`, `condition: str`, `duration_rounds: int`, `source: str` | Impose a status condition through `character_sheet` (`POST /api/v1/characters/{character_id}/conditions`). Returns the active conditions. Both tools share one route. |
| `query_encounter_state` | `encounter_id: str` | Read an encounter. Round, active combatant, and turn order come from `game_session` (`GET /api/v1/sessions/{session_id}/combat`). Tokens, grid, and active hazards come from `board_state`. The `encounter_id` is the game session id. Returns `in_combat`, `round`, `active_combatant_id`, `turn_order`, `session_id`, `grid_dimensions`, `tokens`, and `active_hazards`. |
| `create_encounter` | `session_id: str`, `campaign_id: str?`, `enemies: list[{name, x, y, hp?, cr?}]` | Read each enemy challenge rating first. An enemy without `cr` takes the `challenge_rating` of its rules_compendium stat block by `name`. The lookup names `campaign_id`, so the campaign's homebrew monsters resolve too (the caller needs `homebrew_rule.view` on them). An enemy with neither is a tool error and starts no combat. Then one write to `game_session` (`POST /api/v1/sessions/{session_id}/encounters/start`) starts combat and records the enemy placements on one event. That write is the commit point. `board_state` creates the board if the session has none, then places each enemy as a monster token that is not friendly, from the session event. A placement that `board_state` refuses (off grid, occupied cell) is dead-lettered. Combat stays started. The `session_id` is the encounter id. Returns `encounter_id` (equal to `session_id`), `enemies_spawned` (the placements that `game_session` accepted), `in_combat`, `round`, `active_combatant_id`, and `turn_order`. Tokens appear on the board after `board_state` consumes the event. Read `query_encounter_state` for them. An unknown or unavailable session returns a tool error and starts no combat. |
| `narrate_with_the_watcher` | `campaign_id: str`, `session_id: str`, `scene_prompt: str`, `player_actions: str`, `scene_environment: str`, `tone: str` (default `dark_fantasy`) | Call The Watcher route `POST /api/v1/watcher/narrate`. Returns The Watcher response unchanged: `narrative`, `sensory_details`, `suggested_dm_prompts`, `tension_level`, and `source`. The gateway adds no narration of its own. If the inference worker fails, the tool returns an error. |
| `execute_agent_action_plan` | `session_id: str`, `campaign_id: str`, `actions: list[{tool, actor_name, description?, parameters}]` | Propose each step to The Watcher (`POST /api/v1/watcher/actions/propose`), in order. Each step returns the pending action that The Watcher stored. The DM can veto or change a pending action before it takes effect. No board state changes in this tool. Planning stops at the first failed step, and the report sets `failed_step` to its 1-based number. Each step names its tool under `tool` only, and its arguments under `parameters` only. The keys `name`, `tool_name`, `arguments`, and `args` are not accepted. A step with a missing `tool` or `actor_name`, or with an unknown tool name, fails before any call to The Watcher. |
| `query_monster_stat_block` | `monster_name: str` | Read the monster stat block from `rules_compendium` (`GET /api/v1/compendium/monsters/{name}`). An unknown name returns a tool error. |
| `calculate_encounter_balance` | `party_levels: list[int]`, `target_difficulty: str` | Call the `rules_compendium` route `POST /api/v1/compendium/encounters/balance`. Returns its CR XP thresholds and recommended monster group. |

### Tool Permissions (TASK-0545)

Each tool that changes state reads the caller from the verified MCP request. It checks one schema permission before it calls a service. A request with no verified caller, a denial, and a SpiceDB error each return a tool error. A SpiceDB error is never a success.

| Tool | Permission checked |
|---|---|
| `apply_absentee_penalty`, `modify_character_hp`, `add_condition`, `apply_condition` | `campaign.run_session` on the campaign that the `character` object links to. A character with no campaign link is denied. |
| `get_character_sheet`, `inspect_inventory` | `character.view` on the `character_id`. The gateway checks it before the read, and `character_sheet` checks the forwarded bearer again. |
| `cast_spell` | `character.edit` |
| `move_board_token` | `board_token.move` on the `token_id` |
| `create_encounter` | `session.control` on the `session_id` |
| `execute_agent_action_plan` | The permission of each step, checked before that step runs. A denied step stops the plan with a per-step error. |
| A dynamic tool | `mcp_tool.execute` on the tool name, on the MCP path and on `POST /mcp/tools/{name}/execute` |

The other read-only tools take no extra check in the gateway. The gateway forwards the caller bearer, and the owning service checks it:

| Tool or resource | Owner check on the forwarded bearer |
|---|---|
| `inspect_tactical_board`, `query_encounter_state`, `encounter://{session_id}/current` | `board.view` in `board_state` (`GET /api/v1/boards/{session_id}`), and the session read in `game_session` |
| `session://{session_id}/state` | The session read in `game_session` (`GET /api/v1/sessions/{session_id}`) |
| `query_monster_stat_block`, `calculate_encounter_balance` | `rules_compendium` checks the homebrew rules of the campaign that the caller names |
| `roll_dice` | None. It reads no owner data. |

A read-only tool that the gateway does not check must forward the caller bearer. A tool that reads owner data without one is a defect.

A plan step that names a dynamic tool needs `mcp_tool.execute` on that tool. A step that names a mutating static tool needs the permission in the table. A step must carry the id that its check needs (`character_id`, `token_id`, or `session_id`). A step without it fails.

Tool-to-tool rule: a dynamic tool handler cannot call another tool yet. When a call step exists, it must check `mcp_tool.execute` for the caller on the called tool before it runs. The caller is the token subject of the MCP request. The tool author is not the caller.

A new tuple write that fails returns `503` and registers nothing. `POST /mcp/tools/register` removes the tool again when the author relation cannot be written.

### Upstream Service Calls

Board, encounter, and character tools hold no board, combat, or character state. They call the owning services over HTTP through `gateway/mcp/src/gateway_mcp/owning_services.py`. That module calls the shared `ServiceClient` from `runefoble_platform.service_client`, so each call sends the service credential and the W3C trace context (see [Service Client](service-client.md)). Each call runs in a client span. Agent-supplied path segments are built with `path(...)`:

| Setting | Environment Variable | Default | Owning Service |
|---|---|---|---|
| `board_state_url` | `RUNEFOBLE_BOARD_STATE_URL` | Required | `board_state` |
| `character_sheet_url` | `RUNEFOBLE_CHARACTER_SHEET_URL` | Required | `character_sheet` |
| `game_session_url` | `RUNEFOBLE_GAME_SESSION_URL` | Required | `game_session` |
| `rules_compendium_url` | `RUNEFOBLE_RULES_COMPENDIUM_URL` | Required | `rules_compendium` |
| `the_watcher_url` | `RUNEFOBLE_WATCHER_URL` | Required | `the_watcher` |

The Helm chart renders these from the `urlEnv` and `consumers` keys of the upstream entries under `services` in `values.yaml`. Local runs must export them. There are no localhost defaults.

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

The Dynamic Tool Registry (`gateway/mcp/src/gateway_mcp/dynamic/`) enables tabletop creators, homebrew modders, and external developers to register, update, and hot-reload custom FastMCP tools dynamically at runtime with SpiceDB authorization checks, without restarting the FastMCP gateway or terminating active AI agent sessions (ADR-0001, ADR-0003, ADR-0006, ADR-0007, TASK-0172).

### Gateway Container and Ports (TASK-0746)

`server.build_mcp(container)` builds one FastMCP app. The container holds the dynamic tool registry, the `PermissionChecker` port, and the service client pool. Each test or app builds its own container, so two apps keep separate registries. The guard in `dynamic/auth.py` raises `PermissionDenied`. The admin router maps it to `403`. The router maps `AuthorizationUnavailable` to `503` with `authorization_unavailable`. A tool maps both to a tool error. The SpiceDB adapter is the only code that imports the SpiceDB client.

### Administrative REST Endpoints

The gateway MCP process serves these routes next to `/mcp` (`mount_tools_registry`). The registry lives in that process, so a tool registered here is at once visible to MCP `tools/list` and callable with `tools/call`. The API gateway does not serve these routes and returns `404` for them (TASK-0727). The routes use the same bearer check, `mcp_tool.manage` check, and `mcp_tool.execute` check as before. `/openapi.json` lists them, and Swagger UI shows that spec.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/mcp/tools/dynamic` | List all dynamically registered tools and JSON Schemas |
| `POST` | `/mcp/tools/register` | Register a new dynamic tool with parameter validation and SpiceDB authorization. A non-empty declarative `handler` is required; a definition without one returns HTTP 422 and adds no tool. An invalid handler returns HTTP 400 |
| `GET` | `/mcp/tools/{name}` | Retrieve schema and configuration for a specific dynamic tool |
| `PUT` | `/mcp/tools/{name}` | Update an existing dynamic tool definition and hot-reload logic |
| `DELETE` | `/mcp/tools/{tool_name}` | Deregister a dynamic tool and revoke permissions |
| `POST` | `/mcp/tools/{name}/execute` | Invoke a dynamic tool directly via HTTP frontdoor with auth checks |

Every route above requires a verified bearer token. Without one, the route returns `401` before it reads the tool.

#### Caller rule (TASK-0532)

- The caller is the token subject. The gateway reads no identity from a header, a query string, or a request body.
- `X-User-Id`, the body fields `author_id` and `user_id`, and any other identity-like field are ignored.
- A new tool's author is the token subject that registered it. The gateway writes the SpiceDB `author` relation for that subject.
- `PUT` keeps the recorded author. The caller needs `manage` on the tool.
- `DELETE` requires `manage` and revokes the recorded author relation. The revoke runs first. The tool is removed only after the revoke succeeds. If SpiceDB cannot apply the revoke, the route returns `503` with `authorization_unavailable` and the tool stays registered. Retry the `DELETE` after the outage.
- `POST .../execute` requires `execute`.
- A tool called through the MCP protocol runs for the token subject of that MCP request. The transport check runs first, so a call without a token never reaches the tool.

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

### Declarative Handlers (ADR-0020)

A dynamic tool handler is a JSON result template. The gateway runs no caller code. `exec`, `eval`, and `compile` are never used on caller input.

| Element | Result |
|---|---|
| `"${name}"` | The argument `name`, type kept |
| `"text ${name}"` | A string with argument values inserted |
| `{"$expr": "..."}` | A number. Allowed: numbers, parameter names, `+ - * / // %`, unary signs, parentheses, `max`, `min`, `abs`, `round`. Limits: 200 characters, 64 elements. Each constant and each argument is a finite number from -1000000000 to 1000000000. The digit count of `round` is an integer from -15 to 15. A float result must be finite |
| `{"$dice": "NdS+M"}` | Total of N S-sided dice plus M. Limits: 100 dice, 1000 sides |
| object, list | Evaluated member by member. Limit: 8 levels, 200 elements |

Registration returns HTTP 400 for an unknown parameter name, an unknown `$` directive, a malformed expression, or a limit breach. Execution returns HTTP 400 for an arithmetic error, an argument outside the number limit, a `round` digit count outside the limit, or a result that is not finite. On the MCP path, the same errors are tool errors. Any other execution failure returns HTTP 500 with the fixed detail `Dynamic tool execution failed.`. The server logs the traceback. The detail never holds the cause. Calls from one tool to another tool are not supported.

These limits keep every handler in bounded time and memory, so the handler runs on the event loop with no time limit and no subprocess (TASK-0737, ADR-0020). A handler cannot call an upstream service. If a handler step that calls an upstream service is added, that step must have a time limit.

Parameters are validated with JSON Schema Draft-07 at registration.


