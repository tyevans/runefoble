"""Live socket groups for multiplayer minigame tables, one WebSocket group per table.

Holds only live socket connections. Table game state is event-sourced on the
TavernGame aggregate (TASK-0566), so a restart loses no table state.
"""

from __future__ import annotations

from runefoble_platform.ws_groups import WebSocketGroups

minigame_table_manager = WebSocketGroups[str]()

__all__ = ["minigame_table_manager"]
