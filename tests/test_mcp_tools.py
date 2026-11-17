"""Unit tests for Model Context Protocol (MCP) RPG tools.

Board and encounter tools call owning services over HTTP. Their behavior is
covered by tests/test_blackbox_mcp_gateway.py.
"""

from gateway_mcp.server import mcp, narrate_with_the_watcher, roll_dice


def test_mcp_registered_tools():
    """Verify that all tools are registered with FastMCP tool manager."""
    tool_names = [tool.name for tool in mcp._tool_manager.list_tools()]
    expected = [
        "roll_dice",
        "inspect_tactical_board",
        "move_board_token",
        "apply_absentee_penalty",
        "narrate_with_the_watcher",
        "cast_spell",
        "modify_character_hp",
        "add_condition",
        "apply_condition",
        "get_character_sheet",
        "query_encounter_state",
        "inspect_inventory",
        "create_encounter",
        "execute_agent_action_plan",
    ]
    for name in expected:
        assert name in tool_names, f"Tool '{name}' not registered in FastMCP"


def test_roll_dice():
    """Test standard dice notation parsing and rolling."""
    res = roll_dice("2d6+3", "Attack roll")
    assert res["notation"] == "2d6+3"
    assert len(res["rolls"]) == 2
    assert res["modifier"] == 3
    assert res["total"] == sum(res["rolls"]) + 3

    # Fallback default
    fallback = roll_dice("invalid", "Check")
    assert fallback["notation"] == "1d20"
    assert 1 <= fallback["total"] <= 20


def test_narrate_with_the_watcher():
    """Test DM narration generation via MCP."""
    res = narrate_with_the_watcher("Dungeon gate", "Valeros kicks open the gate")
    assert "Valeros kicks open the gate" in res["narration"]
    assert len(res["environmental_effects"]) > 0
