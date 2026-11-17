"""Blackbox TDD integration test suite for FastMCP Gateway Server.

Tests exercise FastMCP public protocol entrypoints exclusively:
- Resource templates ('session://{session_id}/state')
- Tool discovery and execution via 'mcp.get_tool(...)' and 'mcp._tool_manager'
- Multi-turn agent action plan orchestration
- Error handling for invalid tools and out-of-bounds tactical grid movements
"""

import json
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from gateway_mcp.server import mcp
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import CallToolResult

from tests.helpers.live_services import closed_port_url, serve, unavailable_app


@pytest.fixture(scope="module", autouse=True)
def owning_services() -> Iterator[dict[str, str]]:
    """Run board_state and rules_compendium as real HTTP services for the gateway."""
    from board_state.main import app as board_app
    from rules_compendium.main import app as compendium_app

    with (
        pytest.MonkeyPatch.context() as env,
        serve(board_app) as board_url,
        serve(compendium_app) as compendium_url,
    ):
        env.setenv("BOARD_STATE_URL", board_url)
        env.setenv("RULES_COMPENDIUM_URL", compendium_url)
        # Setup through the public board_state HTTP frontdoor: place the active session token.
        with httpx.Client(base_url=board_url) as http:
            placed = http.post(
                "/api/v1/boards/camp1/tokens",
                json={"token_id": "t1", "name": "Valeros", "x": 1, "y": 1},
            )
            assert placed.status_code == 200, placed.text
        yield {"board": board_url, "compendium": compendium_url}


async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Call a tool through the MCP protocol with an in-memory client session."""
    async with create_connected_server_and_client_session(mcp) as session:
        return await session.call_tool(name, arguments)


def tool_text(result: CallToolResult) -> str:
    """Return the text of the first content block of a tool result."""
    assert result.content, "Tool result must contain content"
    return str(result.content[0].text)


def tool_payload(result: CallToolResult) -> dict[str, Any]:
    """Return the JSON payload of a successful tool result."""
    assert not result.isError, f"Tool failed: {tool_text(result)}"
    data = json.loads(tool_text(result))
    assert isinstance(data, dict)
    return data


@pytest.mark.asyncio
async def test_blackbox_read_session_state_resource():
    """Verify reading dynamic resource session://{session_id}/state returns structured session context."""
    # Frontdoor setup & invocation via FastMCP protocol entrypoint
    contents = await mcp.read_resource("session://camp1/state")
    assert contents is not None, "Expected resource contents from FastMCP"
    content_list = list(contents)
    assert len(content_list) > 0, "Resource contents must not be empty"

    raw_text = content_list[0].content
    assert isinstance(raw_text, str), "Resource content should be serialized JSON string"

    data = json.loads(raw_text)
    assert data["session_id"] == "camp1"
    assert "threat_level" in data, "Session state must include threat_level"
    assert data["threat_level"] in {"easy", "medium", "hard", "deadly"}

    tokens = data.get("tokens") or data.get("active_tokens")
    assert isinstance(tokens, list), "Session state must provide active tokens list"
    assert len(tokens) >= 1, "Expected at least one active token in session context"
    assert "name" in tokens[0]

    assert "scene_atmosphere" in data, "Session state must provide scene_atmosphere"
    assert "mood" in data["scene_atmosphere"]
    assert "lighting" in data["scene_atmosphere"]


@pytest.mark.asyncio
async def test_blackbox_execute_agent_action_plan_success():
    """Verify executing multi-turn agent action plan through FastMCP tool manager entrypoint."""
    tool = mcp.get_tool("execute_agent_action_plan")
    assert tool is not None, "execute_agent_action_plan must be registered in FastMCP"

    plan = [
        {
            "tool": "roll_dice",
            "parameters": {"notation": "1d20+3", "reason": "Initiative check"},
        },
        {
            "tool": "move_board_token",
            "parameters": {"token_id": "t1", "to_x": 3, "to_y": 4},
        },
        {
            "tool": "narrate_with_the_watcher",
            "parameters": {
                "scene_prompt": "Goblin dungeon corridor",
                "player_actions": "Valeros rushes forward to engage the vanguard",
            },
        },
    ]

    result = await tool.run({"session_id": "camp1", "actions": plan})

    assert result["status"] == "success"
    assert result["success"] is True
    assert result["session_id"] == "camp1"
    assert result["total_steps"] == 3
    assert result["completed_steps"] == 3
    assert len(result["steps"]) == 3
    assert result["total_duration_ms"] >= 0

    # Assert step 1: dice roll
    step1 = result["steps"][0]
    assert step1["step"] == 1
    assert step1["tool"] == "roll_dice"
    assert step1["status"] == "success"
    assert step1["output"]["notation"] == "1d20+3"
    assert step1["output"]["total"] >= 4
    assert step1["duration_ms"] >= 0

    # Assert step 2: token move
    step2 = result["steps"][1]
    assert step2["step"] == 2
    assert step2["tool"] == "move_board_token"
    assert step2["status"] == "success"
    assert step2["output"]["destination"] == {"x": 3, "y": 4}
    assert step2["output"]["token_id"] == "t1"

    # Assert step 3: narration
    step3 = result["steps"][2]
    assert step3["step"] == 3
    assert step3["tool"] == "narrate_with_the_watcher"
    assert step3["status"] == "success"
    assert "Valeros rushes forward" in step3["output"]["narration"]


@pytest.mark.asyncio
async def test_blackbox_execute_agent_action_plan_invalid_tool():
    """Verify error handling when action plan specifies an invalid or unknown tool."""
    tool = mcp.get_tool("execute_agent_action_plan")
    assert tool is not None

    plan = [
        {
            "tool": "nonexistent_secret_spell_destroy_everything",
            "parameters": {"target": "all"},
        }
    ]

    result = await tool.run({"session_id": "camp1", "actions": plan})

    assert result["status"] == "error"
    assert result["success"] is False
    assert result["completed_steps"] == 0
    assert result["total_steps"] == 1
    assert "nonexistent_secret_spell_destroy_everything" in result["error"]
    assert len(result["steps"]) == 1
    assert result["steps"][0]["status"] == "error"


@pytest.mark.asyncio
async def test_blackbox_execute_agent_action_plan_out_of_bounds_coordinates():
    """Verify error handling when action plan specifies out-of-bounds tactical grid coordinates."""
    tool = mcp.get_tool("execute_agent_action_plan")
    assert tool is not None

    plan = [
        {
            "tool": "roll_dice",
            "parameters": {"notation": "1d20", "reason": "Stealth check"},
        },
        {
            "tool": "move_board_token",
            "parameters": {"token_id": "t1", "to_x": 99, "to_y": -5},
        },
        {
            "tool": "narrate_with_the_watcher",
            "parameters": {
                "scene_prompt": "Dark room",
                "player_actions": "Valeros hides",
            },
        },
    ]

    result = await tool.run({"session_id": "camp1", "actions": plan})

    assert result["status"] == "error"
    assert result["success"] is False
    assert result["completed_steps"] == 1
    assert result["total_steps"] == 3
    assert result["failed_step"] == 2
    assert "bounds" in result["error"].lower() or "coordinates" in result["error"].lower()

    # Step 1 succeeded before failure occurred
    assert result["steps"][0]["status"] == "success"
    assert result["steps"][1]["status"] == "error"
    # Step 3 never ran
    assert len(result["steps"]) == 2


@pytest.mark.asyncio
async def test_blackbox_mcp_tool_discovery():
    """Verify public FastMCP discovery reveals all expected tools including action orchestrator."""
    tools = mcp._tool_manager.list_tools()
    tool_map = {t.name: t for t in tools}

    assert "execute_agent_action_plan" in tool_map
    plan_tool = tool_map["execute_agent_action_plan"]
    assert "actions" in plan_tool.parameters["properties"]
    assert "session_id" in plan_tool.parameters["properties"]


@pytest.mark.asyncio
async def test_blackbox_read_active_session_resource():
    """Verify reading dynamic resource session://active returns active session state."""
    contents = await mcp.read_resource("session://active")
    assert contents is not None
    content_list = list(contents)
    assert len(content_list) > 0

    data = json.loads(content_list[0].content)
    assert data["session_id"] == "camp1"
    assert "tokens" in data
    assert "scene_atmosphere" in data


@pytest.mark.asyncio
async def test_blackbox_read_encounter_current_resource():
    """Verify reading dynamic resource encounter://current returns the active board state."""
    contents = await mcp.read_resource("encounter://current")
    assert contents is not None
    content_list = list(contents)
    assert len(content_list) > 0

    data = json.loads(content_list[0].content)
    assert data["session_id"] == "camp1"
    assert isinstance(data["tokens"], list)


@pytest.mark.asyncio
async def test_blackbox_prompt_templates():
    """Verify prompt templates dm_narrative_guidance and tactical_action_adviser."""
    prompts = await mcp.list_prompts()
    prompt_names = [p.name for p in prompts]
    assert "dm_narrative_guidance" in prompt_names
    assert "tactical_action_adviser" in prompt_names

    p1 = await mcp.get_prompt(
        "dm_narrative_guidance", arguments={"scene_context": "Ruined cathedral"}
    )
    assert "The Watcher" in p1.messages[0].content.text
    assert "Ruined cathedral" in p1.messages[0].content.text

    p2 = await mcp.get_prompt(
        "tactical_action_adviser", arguments={"tactical_situation": "Surrounded by goblins"}
    )
    assert "Tactical Action Adviser" in p2.messages[0].content.text
    assert "Surrounded by goblins" in p2.messages[0].content.text


@pytest.mark.asyncio
async def test_blackbox_character_tools():
    """Verify get_character_sheet and apply_condition through public FastMCP tool interface."""
    sheet_tool = mcp.get_tool("get_character_sheet")
    assert sheet_tool is not None
    sheet_res = await sheet_tool.run({"character_id": "char-1"})
    assert sheet_res["name"] == "Valeros"
    assert sheet_res["class"] == "Fighter"
    assert sheet_res["attributes"]["strength"] == 16

    cond_tool = mcp.get_tool("apply_condition")
    assert cond_tool is not None
    cond_res = await cond_tool.run(
        {"character_id": "char-1", "condition": "prone", "duration_rounds": 1}
    )
    assert cond_res["status"] == "condition_applied"
    assert cond_res["condition"] == "prone"


@pytest.mark.asyncio
async def test_blackbox_create_encounter_stores_enemy_tokens():
    """Verify create_encounter stores enemies on the board that query_encounter_state reads back."""
    created = tool_payload(
        await call_tool(
            "create_encounter",
            {
                "encounter_name": "Ambush at Crossroads",
                "terrain": "forest",
                "enemies": [{"name": "Bandit", "x": 4, "y": 4, "hp": 11}],
            },
        )
    )
    assert created["status"] == "encounter_created"
    assert created["grid"] == {"cols": 10, "rows": 8}

    state = tool_payload(
        await call_tool("query_encounter_state", {"encounter_id": created["encounter_id"]})
    )
    assert state["grid_dimensions"] == {"cols": 10, "rows": 8}
    assert [(t["name"], t["x"], t["y"]) for t in state["tokens"]] == [("Bandit", 4, 4)]


@pytest.mark.asyncio
async def test_blackbox_move_board_token_then_inspect_reports_new_position():
    """Verify a token moved through MCP is read back at its new position from the board."""
    created = tool_payload(
        await call_tool(
            "create_encounter",
            {"encounter_name": "Skirmish", "enemies": [{"name": "Goblin", "x": 2, "y": 2}]},
        )
    )
    session_id = created["encounter_id"]
    token_id = created["enemies_spawned"][0]["token_id"]

    moved = tool_payload(
        await call_tool(
            "move_board_token",
            {"session_id": session_id, "token_id": token_id, "to_x": 6, "to_y": 2},
        )
    )
    assert moved["status"] == "success"
    assert moved["destination"] == {"x": 6, "y": 2}

    board = tool_payload(await call_tool("inspect_tactical_board", {"session_id": session_id}))
    goblin = board["tokens"][0]
    assert (goblin["token_id"], goblin["x"], goblin["y"]) == (token_id, 6, 2)


@pytest.mark.asyncio
async def test_blackbox_move_board_token_out_of_bounds_is_error_result():
    """Verify the board rejects an out-of-bounds move and the MCP result reports an error."""
    created = tool_payload(
        await call_tool(
            "create_encounter",
            {"encounter_name": "Edge", "enemies": [{"name": "Imp", "x": 0, "y": 0}]},
        )
    )
    result = await call_tool(
        "move_board_token",
        {
            "session_id": created["encounter_id"],
            "token_id": created["enemies_spawned"][0]["token_id"],
            "to_x": 99,
            "to_y": -5,
        },
    )
    assert result.isError is True
    assert "bounds" in tool_text(result).lower()


@pytest.mark.asyncio
async def test_blackbox_inspect_board_returns_error_when_board_service_returns_503(monkeypatch):
    """Verify a 503 from board_state becomes an MCP error result, not canned board data."""
    with serve(unavailable_app(503)) as down_url:
        monkeypatch.setenv("BOARD_STATE_URL", down_url)
        result = await call_tool("inspect_tactical_board", {"session_id": "camp-503"})

    assert result.isError is True
    assert "503" in tool_text(result)
    assert "Valeros" not in tool_text(result)


@pytest.mark.asyncio
async def test_blackbox_inspect_board_returns_error_when_board_service_is_unreachable(monkeypatch):
    """Verify an unreachable board_state becomes an MCP error result, not canned board data."""
    monkeypatch.setenv("BOARD_STATE_URL", closed_port_url())
    result = await call_tool("inspect_tactical_board", {"session_id": "camp-down"})

    assert result.isError is True
    assert "unreachable" in tool_text(result)


@pytest.mark.asyncio
async def test_blackbox_calculate_encounter_balance_uses_rules_compendium_route():
    """Verify encounter balance is computed by the rules_compendium public route."""
    balance = tool_payload(
        await call_tool(
            "calculate_encounter_balance",
            {"party_levels": [3, 3, 3, 4], "target_difficulty": "Medium"},
        )
    )
    assert balance["party_size"] == 4
    assert balance["target_difficulty"] == "Medium"
    assert "difficulty_tier" in balance
    assert "encounter_id" in balance
    assert balance["total_monster_count"] == sum(m["count"] for m in balance["monsters"])


@pytest.mark.asyncio
async def test_blackbox_calculate_encounter_balance_rejects_empty_party():
    """Verify rules_compendium validation errors surface as MCP error results."""
    result = await call_tool(
        "calculate_encounter_balance",
        {"party_levels": [], "target_difficulty": "Medium"},
    )
    assert result.isError is True
    assert "rejected the request (422)" in tool_text(result)
