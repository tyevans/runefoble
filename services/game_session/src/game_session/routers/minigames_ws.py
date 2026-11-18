"""WebSocket router for real-time multiplayer tavern and casino minigames.

Governed by ADR-0004, ADR-0006, and Hard Invariant 1 (SpiceDB authorization).
Table state lives on the TavernGame aggregate (TASK-0566). This module only
admits sockets, runs commands, and broadcasts the results.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from game_session.dependencies import get_spicedb_client
from game_session.minigame_tables.service import TableNotFoundError, load_table, run_table_command
from game_session.minigame_tables.ws_commands import table_command_for
from game_session.minigame_tables.ws_manager import minigame_table_manager
from game_session.settlement.auth import check_establishment_play_permission
from game_session.settlement.auth.tokens import get_zitadel_auth_service
from runefoble_auth.principal import BearerVerifier
from runefoble_auth.websocket import admit_websocket

logger = logging.getLogger("runefoble.game_session.minigames_ws")

router = APIRouter(tags=["minigames_ws"])


async def handle_table_websocket(
    websocket: WebSocket,
    table_id: str,
    establishment_id: str,
    verifier: BearerVerifier | None = None,
) -> None:
    """Admit the verified caller, then run the bidirectional minigames table session."""
    principal = await admit_websocket(websocket, verifier or get_zitadel_auth_service())
    if principal is None:
        return
    user_id = principal.user_id
    spicedb = get_spicedb_client()

    # Zanzibar permission check on every connect. No establishment id is exempt.
    has_perm = await check_establishment_play_permission(spicedb, establishment_id, user_id)
    if not has_perm:
        await websocket.send_json(
            {
                "type": "error",
                "code": "PERMISSION_DENIED",
                "message": f"User '{user_id}' lacks permission to play at establishment '{establishment_id}'",
            }
        )
        await websocket.close(code=4003, reason="Forbidden")
        return

    try:
        table = await load_table(table_id)
    except TableNotFoundError:
        await websocket.send_json(
            {
                "type": "error",
                "code": "TABLE_NOT_FOUND",
                "message": f"Table '{table_id}' is not open",
            }
        )
        await websocket.close(code=4404, reason="Table not found")
        return

    minigame_table_manager.register(table_id, websocket)
    await websocket.send_json(
        {
            "type": "connected",
            "table_id": table_id,
            "establishment_id": establishment_id,
            "table_state": table.model_dump(),
        }
    )

    try:
        while True:
            data: dict[str, Any] = await websocket.receive_json()
            action = data.get("action") or data.get("type") or "unknown"
            await _handle_action(websocket, table_id, user_id, action, data)
    except WebSocketDisconnect:
        pass
    finally:
        minigame_table_manager.disconnect(table_id, websocket)


async def _handle_action(
    websocket: WebSocket,
    table_id: str,
    user_id: str,
    action: str,
    data: dict[str, Any],
) -> None:
    command = table_command_for(action, data, user_id)
    if command is None:
        # Pass-through action (for example billiards strokes): echo to the table.
        await minigame_table_manager.broadcast(table_id, data)
        return
    try:
        message = await run_table_command(table_id, command)
    except ValueError as exc:
        await websocket.send_json({"type": "error", "code": "ACTION_REJECTED", "message": str(exc)})
        return
    await minigame_table_manager.broadcast(table_id, message)


@router.websocket("/ws/establishments/{establishment_id}/tables/{table_id}")
async def establishment_table_ws(
    websocket: WebSocket,
    establishment_id: str,
    table_id: str,
) -> None:
    """Establishment-scoped multiplayer minigame table WebSocket channel."""
    await handle_table_websocket(websocket, table_id, establishment_id)


@router.websocket("/ws/minigames/{table_id}")
async def standalone_minigame_ws(
    websocket: WebSocket,
    table_id: str,
) -> None:
    """Standalone multiplayer minigame table WebSocket channel."""
    await handle_table_websocket(websocket, table_id, "est-default")


__all__ = ["handle_table_websocket", "router"]
