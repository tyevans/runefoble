"""Tactical board and encounter tools for FastMCP gateway."""

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def inspect_tactical_board(session_id: str) -> dict[str, Any]:
    """Retrieve all tokens, coordinates, and grid dimensions for the active session."""
    return {
        "session_id": session_id,
        "grid_dimensions": {"cols": 8, "rows": 8},
        "tokens": [
            {
                "id": "t1",
                "name": "Valeros",
                "class": "Fighter",
                "x": 2,
                "y": 3,
                "hp": 38,
                "max_hp": 45,
                "ai_controlled": False,
            },
            {
                "id": "t2",
                "name": "Kyra",
                "class": "Cleric",
                "x": 3,
                "y": 3,
                "hp": 28,
                "max_hp": 32,
                "ai_controlled": True,
                "penalties": ["drunk"],
            },
            {
                "id": "t3",
                "name": "Goblin Scout",
                "type": "Monstrous",
                "x": 5,
                "y": 1,
                "hp": 7,
                "max_hp": 12,
                "hostile": True,
            },
        ],
    }


def move_board_token(session_id: str, token_id: str, to_x: int, to_y: int) -> dict[str, Any]:
    """Move a token to target coordinates (x, y) on the tactical map."""
    grid_cols, grid_rows = 8, 8
    if not (0 <= to_x < grid_cols and 0 <= to_y < grid_rows):
        raise ValueError(
            f"Coordinates ({to_x}, {to_y}) out of grid bounds ({grid_cols}x{grid_rows})"
        )
    return {
        "status": "success",
        "session_id": session_id,
        "token_id": token_id,
        "destination": {"x": to_x, "y": to_y},
        "watcher_commentary": f"Token {token_id} moved to ({to_x}, {to_y}). Spatial vision updated.",
    }


def query_encounter_state(encounter_id: str = "enc-1") -> dict[str, Any]:
    """Query current turn order, round number, active combatants, and environmental hazards."""
    return {
        "encounter_id": encounter_id,
        "round": 2,
        "active_turn": {
            "token_id": "t1",
            "character_name": "Valeros",
            "initiative_score": 19,
            "actions_remaining": {"action": 1, "bonus_action": 1, "movement_ft": 30},
        },
        "initiative_order": [
            {"token_id": "t1", "name": "Valeros", "initiative": 19, "is_active": True},
            {"token_id": "t3", "name": "Goblin Scout", "initiative": 16, "is_active": False},
            {"token_id": "t2", "name": "Kyra (AI)", "initiative": 12, "is_active": False},
        ],
        "environmental_hazards": ["crumbling_pillars", "torches_dimming"],
        "active_combatants_count": 3,
    }


def create_encounter(
    encounter_name: str,
    terrain: str = "dungeon",
    enemies: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create and initialize a new tactical combat encounter with grid dimensions and enemy placements."""
    enemy_list = enemies or [
        {"name": "Goblin Warrior", "x": 6, "y": 2, "hp": 15},
        {"name": "Goblin Archer", "x": 7, "y": 1, "hp": 10},
    ]
    return {
        "status": "encounter_created",
        "encounter_id": f"enc-{random.randint(100, 999)}",
        "name": encounter_name,
        "terrain": terrain,
        "grid": {"cols": 10, "rows": 8},
        "enemies_spawned": enemy_list,
        "initial_round": 1,
        "watcher_commentary": f"A new encounter '{encounter_name}' begins in {terrain} terrain. Roll initiative!",
    }


def register_board_tools(mcp: "FastMCP") -> None:
    """Register board and encounter tools on the FastMCP application."""
    mcp.tool()(inspect_tactical_board)
    mcp.tool()(move_board_token)
    mcp.tool()(query_encounter_state)
    mcp.tool()(create_encounter)
