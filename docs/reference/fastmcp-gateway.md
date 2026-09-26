# FastMCP Gateway Reference

The FastMCP Gateway (`gateway/mcp`) exposes Runefoble tabletop actions, spatial queries, character sheet mutations, and Game Master controls to external LLMs and internal agents via the Model Context Protocol (MCP).

## Architecture

The gateway server entrypoint (`gateway/mcp/src/gateway_mcp/server.py`) operates as a lightweight orchestration shell (< 80 lines) delegating domain capabilities to modular sub-packages:

gateway/mcp/src/gateway_mcp/
├── constants.py           # RPG constants (spell effects, condition descriptions)
├── dynamic_registry.py    # Runtime tool registration, JSON schema, & sandbox
├── main.py                # CLI execution wrapper
├── server.py              # FastMCP orchestration shell and module mounting
├── tools/                 # MCP tool implementations (< 180 lines each)
│   ├── dice.py            # Dice notation parsing and rolling (roll_dice)
│   ├── board.py           # Tactical board token positioning and encounters
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
| `inspect_tactical_board` | `session_id: str` | Retrieve token positions, HP, control status, and grid dimensions. |
| `move_board_token` | `session_id: str`, `token_id: str`, `to_x: int`, `to_y: int` | Validate coordinates and move a token on the grid. |
| `get_character_sheet` | `character_id: str` | Retrieve character stats, level, hit points, equipment, and active conditions. |
| `inspect_inventory` | `character_id: str` | Retrieve equipped items, carried inventory, and currency breakdown. |
| `apply_absentee_penalty` | `character_id: str`, `penalty_type: str`, `explanation: str` | Impose session miss penalties (`drunk`, `foolishness`) on absent player PCs. |
| `cast_spell` | `character_id: str`, `spell_name: str`, `spell_level: int`, `target: str` | Cast a spell, tracking spell slot expenditure and mechanical rules. |
| `modify_character_hp` | `character_id: str`, `delta: int`, `damage_type: str`, `reason: str` | Apply damage or healing, calculating `bloodied` or `unconscious` states. |
| `add_condition` / `apply_condition` | `character_id: str`, `condition: str`, `duration_rounds: int`, `source: str` | Impose status condition (`blinded`, `prone`, `frightened`) with rule effects. |
| `query_encounter_state` | `encounter_id: str` | Query active combat round, initiative order, active turn, and hazards. |
| `create_encounter` | `encounter_name: str`, `terrain: str`, `enemies: list` | Initialize a new combat encounter with enemy grid placements. |
| `narrate_with_the_watcher` | `scene_prompt: str`, `player_actions: str` | Invoke The Watcher AI GM for immersive narration and environmental cues. |
| `execute_agent_action_plan` | `session_id: str`, `actions: list` | Sequentially execute multi-turn action plan with step validation and timing. |
| `query_monster_stat_block` | `monster_name: str` | Retrieve full canonical monster stat block, AC, HP, CR, actions, and traits. |
| `calculate_encounter_balance` | `party_levels: list[int]`, `target_difficulty: str` | Compute accurate CR XP thresholds and recommend synergistic monster group with role diversity. |

## Resources Registry

Dynamic FastMCP resources supply structured context to LLMs without requiring explicit parameter passing:

| Resource URI | MIME Type | Description |
|---|---|---|
| `session://active` | `application/json` | Active session state including tokens, threat level, and scene atmosphere. |
| `session://{session_id}/state` | `application/json` | Specific session state including active tokens and atmosphere. |
| `encounter://current` | `application/json` | Current combat encounter turn order, round number, and hazards. |

## Prompt Templates

Prompt templates provide standardized prompts for LLM decision-making and narration:

| Prompt Name | Arguments | Description |
|---|---|---|
| `dm_narrative_guidance` | `scene_context: str`, `mood: str` | Formats Watcher AI DM sensory and environmental narrative cues. |
| `tactical_action_adviser` | `tactical_situation: str`, `character_role: str` | Provides combat analysis and optimal action recommendations. |

## Dynamic Runtime Tool Registry

The Dynamic Tool Registry (`gateway/mcp/src/gateway_mcp/dynamic_registry.py`) enables tabletop creators, homebrew modders, and external developers to register custom FastMCP tools dynamically at runtime without restarting the FastMCP gateway or dropping active client SSE connections (ADR-0008, TASK-0057).

### Administrative REST Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/mcp/tools` (or `/api/v1/mcp/tools`) | List all dynamically registered tools and JSON Schemas |
| `POST` | `/mcp/tools` (or `/api/v1/mcp/tools`) | Register a new dynamic tool with parameter validation and sandbox checks |
| `GET` | `/mcp/tools/{name}` | Retrieve schema and configuration for a specific dynamic tool |
| `PUT` | `/mcp/tools/{name}` | Update an existing dynamic tool definition |
| `DELETE` | `/mcp/tools/{name}` | Deregister a dynamic tool and remove it from FastMCP discovery |
| `POST` | `/mcp/tools/{name}/execute` | Invoke a dynamic tool directly via HTTP frontdoor |

### Security & Sandbox Policies

Dynamic tool definitions containing custom Python logic (`handler_code`) undergo strict AST static analysis and sandboxed execution:
- **Forbidden Imports**: `os`, `sys`, `subprocess`, `shutil`, `socket`, `urllib`, `requests`, `httpx`, `pathlib`, `builtins`, `importlib`.
- **Forbidden Functions**: `open`, `eval`, `exec`, `compile`, `__import__`, `globals`, `locals`, `exit`, `quit`.
- **Attribute Access Restrictions**: Access to dunder attributes (e.g. `__class__`, `__subclasses__`, `__globals__`, `__code__`) is rejected.
- **Allowed Modules**: Safe modules such as `math`, `json`, `re`, `random`.
- **Parameter Validation**: Enforced via JSON Schema Draft-07 specifications with type matching across Python signatures.

