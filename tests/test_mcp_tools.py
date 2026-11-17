"""Unit tests for Model Context Protocol (MCP) RPG tools.

Board and encounter tools call owning services over HTTP. Their behavior is
covered by tests/test_blackbox_mcp_gateway.py.
"""

from gateway_mcp.server import (
    add_condition,
    apply_absentee_penalty,
    apply_condition,
    cast_spell,
    get_character_sheet,
    inspect_inventory,
    mcp,
    modify_character_hp,
    narrate_with_the_watcher,
    roll_dice,
)


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


def test_apply_absentee_penalty():
    """Test applying a penalty to an absentee character."""
    res = apply_absentee_penalty("char-1", "drunk", "Drank excessive tavern cider")
    assert res["status"] == "applied"
    assert res["penalty_type"] == "drunk"
    assert "drunk" in res["watcher_rule"].lower()


def test_narrate_with_the_watcher():
    """Test DM narration generation via MCP."""
    res = narrate_with_the_watcher("Dungeon gate", "Valeros kicks open the gate")
    assert "Valeros kicks open the gate" in res["narration"]
    assert len(res["environmental_effects"]) > 0


def test_cast_spell():
    """Test spellcasting tool logic and slot tracking."""
    fireball = cast_spell("char-1", "Fireball", spell_level=3, target="goblin horde")
    assert fireball["status"] == "cast"
    assert fireball["spell_name"] == "Fireball"
    assert fireball["slot_consumed"] == "level_3"
    assert "8d6 fire damage" in fireball["effect"]

    cantrip = cast_spell("char-2", "Light", spell_level=0)
    assert cantrip["is_cantrip"] is True
    assert cantrip["slot_consumed"] is None


def test_modify_character_hp():
    """Test damage and healing application."""
    damage = modify_character_hp("char-1", -15, damage_type="slashing", reason="Goblin blade")
    assert damage["action_type"] == "damage"
    assert damage["new_hp"] == 15
    assert damage["consciousness"] == "bloodied"

    heal = modify_character_hp("char-1", 10, damage_type="radiant", reason="Healing word")
    assert heal["action_type"] == "heal"
    assert heal["new_hp"] == 40
    assert heal["consciousness"] == "conscious"

    lethal = modify_character_hp("char-1", -50, reason="Dragon breath")
    assert lethal["new_hp"] == 0
    assert lethal["consciousness"] == "unconscious"


def test_add_condition():
    """Test condition assignment and rules lookup."""
    res = add_condition("char-1", "blinded", duration_rounds=2, source="Sand storm")
    assert res["status"] == "condition_applied"
    assert res["condition"] == "blinded"
    assert "sight" in res["rule_effect"].lower()
    assert res["duration_rounds"] == 2


def test_inspect_inventory():
    """Test inventory inspection."""
    res = inspect_inventory("char-1")
    assert res["character_id"] == "char-1"
    assert "Longsword +1" in res["equipped"]["main_hand"]
    assert res["currency"]["gold"] == 45


def test_get_character_sheet():
    """Test retrieving complete character sheet data."""
    sheet = get_character_sheet("char-1")
    assert sheet["character_id"] == "char-1"
    assert sheet["name"] == "Valeros"
    assert sheet["class"] == "Fighter"
    assert sheet["hp"]["current"] == 38
    assert sheet["attributes"]["strength"] == 16
    assert "inventory" in sheet


def test_apply_condition():
    """Test imposing condition via apply_condition alias."""
    res = apply_condition("char-2", "poisoned", duration_rounds=3, source="Venom trap")
    assert res["status"] == "condition_applied"
    assert res["condition"] == "poisoned"
    assert res["duration_rounds"] == 3
