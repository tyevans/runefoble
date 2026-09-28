"""WebSocket router for real-time multiplayer tavern and casino minigames.

Governed by ADR-0004, ADR-0006, and Hard Invariant 1 (SpiceDB authorization).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from game_session.dependencies import get_spicedb_client
from game_session.minigame_tables.ws_manager import minigame_table_manager
from game_session.settlement.auth import check_establishment_play_permission

logger = logging.getLogger("runefoble.game_session.minigames_ws")

router = APIRouter(tags=["minigames_ws"])


async def handle_table_websocket(
    websocket: WebSocket,
    table_id: str,
    establishment_id: str = "est-default",
) -> None:
    """Handle bidirectional minigames table WebSocket session."""
    user_id = websocket.query_params.get("user_id")
    spicedb = get_spicedb_client()

    # Zanzibar permission check on connect
    if establishment_id and establishment_id != "est-default" and user_id:
        has_perm = await check_establishment_play_permission(spicedb, establishment_id, user_id)
        if not has_perm:
            await websocket.accept()
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "PERMISSION_DENIED",
                    "message": f"User '{user_id}' lacks permission to play at establishment '{establishment_id}'",
                }
            )
            await websocket.close(code=4003, reason="Forbidden")
            return

    await minigame_table_manager.connect(table_id, websocket)
    table = minigame_table_manager.get_or_create_table(table_id, establishment_id)
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

            if action == "join":
                await minigame_table_manager.join_player(
                    table_id=table_id,
                    player_id=data.get("player_id", user_id or "anon"),
                    name=data.get("name", "Adventurer"),
                    chips=data.get("chips", 100),
                    establishment_id=establishment_id,
                    game_type=data.get("game_type", table.game_type),
                )
            elif action == "bet":
                await minigame_table_manager.place_bet(
                    table_id=table_id,
                    player_id=data.get("player_id", user_id or "anon"),
                    amount=int(data.get("amount", 10)),
                    bet_type=data.get("bet_type", "straight"),
                    target=data.get("target"),
                )
            elif action == "throw_dart":
                await minigame_table_manager.throw_dart(
                    table_id=table_id,
                    player_id=data.get("player_id", user_id or "anon"),
                    vx=float(data.get("vx", 0.0)),
                    vy=float(data.get("vy", 0.0)),
                    wind_x=float(data.get("wind_x", 0.0)),
                    wind_y=float(data.get("wind_y", 0.0)),
                )
            elif action == "bid":
                await minigame_table_manager.submit_bid(
                    table_id=table_id,
                    player_id=data.get("player_id", user_id or "anon"),
                    quantity=int(data.get("quantity", 1)),
                    face=int(data.get("face", 1)),
                )
            elif action == "challenge":
                await minigame_table_manager.challenge_bluff(
                    table_id=table_id,
                    challenger_id=data.get("challenger_id", user_id or "anon"),
                )
            elif action == "spin_roulette":
                winning_num = data.get("winning_number")
                await minigame_table_manager.spin_roulette(
                    table_id=table_id,
                    winning_number=int(winning_num) if winning_num is not None else None,
                )
            elif action == "roll_craps":
                dice = data.get("dice")
                await minigame_table_manager.roll_craps(
                    table_id=table_id,
                    dice=dice,
                )
            else:
                # Echo / broadcast generic table action
                await minigame_table_manager.broadcast(table_id, data)
    except WebSocketDisconnect:
        minigame_table_manager.disconnect(table_id, websocket)


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
