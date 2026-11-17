"""Unit tests for Model Context Protocol (MCP) RPG tools.

Board, encounter, narration, and resource tools call owning services over HTTP.
Their behavior is covered by tests/test_blackbox_mcp_gateway.py and
tests/test_blackbox_mcp_orchestration_and_resources.py.
"""

from gateway_mcp.server import mcp, roll_dice


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
