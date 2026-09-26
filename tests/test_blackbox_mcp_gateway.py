"""Blackbox TDD integration test suite for FastMCP Gateway Server.

Tests exercise FastMCP public protocol entrypoints exclusively:
- Resource templates ('session://{session_id}/state')
- Tool discovery and execution via 'mcp.get_tool(...)' and 'mcp._tool_manager'
- Multi-turn agent action plan orchestration
- Error handling for invalid tools and out-of-bounds tactical grid movements
"""

import json

import pytest
from gateway_mcp.server import mcp


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
    """Verify reading dynamic resource encounter://current returns encounter state."""
    contents = await mcp.read_resource("encounter://current")
    assert contents is not None
    content_list = list(contents)
    assert len(content_list) > 0

    data = json.loads(content_list[0].content)
    assert data["encounter_id"] == "enc-camp1"
    assert "initiative_order" in data
    assert "active_turn" in data


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
