"""Unit tests for Model Context Protocol (MCP) RPG tools.

Board, encounter, narration, and resource tools call owning services over HTTP.
Their behavior is covered by tests/test_blackbox_mcp_gateway.py and
tests/test_blackbox_mcp_orchestration_and_resources.py.
"""

import pytest
from gateway_mcp.server import mcp, roll_dice
from runefoble_platform.dice import parse_and_roll


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


def test_roll_dice_returns_the_platform_roll_shape():
    """A fixed roll through the MCP tool returns the same shape as parse_and_roll, plus the reason."""
    res = roll_dice("2d6+3", "Attack roll", fixed_rolls=[4, 5])
    expected = parse_and_roll("2d6+3", fixed_rolls=[4, 5])
    assert res == {**expected, "reason": "Attack roll"}
    assert res["formula"] == "2d6+3"
    assert res["kept_rolls"] == [4, 5]
    assert res["total"] == 12


@pytest.mark.parametrize("notation", ["invalid", "1d20abc", "0d6", "1d0", ""])
def test_roll_dice_rejects_bad_notation(notation: str):
    """Bad notation is a tool error. The tool never rolls a default 1d20."""
    with pytest.raises(ValueError):
        roll_dice(notation, "Check")
