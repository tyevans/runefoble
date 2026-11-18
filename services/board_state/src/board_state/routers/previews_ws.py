"""Real-time tactical board WebSocket stream and ghost preview hub."""

from __future__ import annotations

import logging
from typing import Any

from board_state.authz import VIEW, can_on_board
from board_state.dependencies import (
    BoardNotFoundError,
    get_board,
    get_zitadel_auth_service,
    repo,
)
from board_state.preview import compute_kinematic_route_preview
from board_state.realtime import board_ws_manager
from board_state.routers.previews_ws_actions import handle_ws_action
from board_state.routers.previews_ws_authz import BoardActionDenied, authorize_message
from board_state.routers.previews_ws_spells import handle_ws_spell
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from runefoble_auth.websocket import WebSocketAuthorizer, admit_websocket, send_socket_error

logger = logging.getLogger("runefoble.board_state.routers.previews_ws")

router = APIRouter(tags=["previews"])

GHOST_ACTIONS = (
    "preview_move",
    "ghost_preview",
    "speech_intent",
    "runefoble.events.watcher.speech_intent_parsed",
)
CONFIRM_ACTIONS = ("confirm_move", "confirm_ghost", "confirm_intent")
CANCEL_ACTIONS = ("cancel_preview", "cancel_ghost")


class UnknownBoardAction(ValueError):
    """Raised for a message type that the board does not define."""


def _find_token_id(board: Any, token_id: str | None, speaker_name: str | None) -> str | None:
    if token_id:
        return token_id
    if speaker_name:
        for tok in board.state.tokens.values():
            if tok.name.lower() == speaker_name.lower():
                return tok.token_id
    return None


async def _handle_ghost_preview(session_id: str, data: dict[str, Any]) -> None:
    board = await get_board(session_id)
    token_id = _find_token_id(board, data.get("token_id"), data.get("speaker_name"))
    to_x, to_y = data.get("to_x"), data.get("to_y")
    if token_id and to_x is not None and to_y is not None:
        preview = compute_kinematic_route_preview(
            board_aggregate=board,
            token_id=token_id,
            to_x=int(to_x),
            to_y=int(to_y),
            from_x=data.get("from_x"),
            from_y=data.get("from_y"),
            movement_budget=data.get("movement_budget"),
        )
        msg = {
            "type": "ghost_preview",
            "action": "ghost_preview",
            "status": "staged",
            "session_id": session_id,
            "speaker_name": data.get("speaker_name"),
            "raw_transcript": data.get("raw_transcript"),
            "preview": preview.model_dump(),
            "timeout_seconds": data.get("timeout_seconds", 15),
        }
        await board_ws_manager.broadcast(session_id, msg)


async def _handle_confirm_move(session_id: str, data: dict[str, Any]) -> None:
    token_id, to_x, to_y = data.get("token_id"), data.get("to_x"), data.get("to_y")
    if not (token_id and to_x is not None and to_y is not None):
        return
    board = await get_board(session_id)
    cost, hazard, dice = board.move_token(
        token_id=token_id,
        to_x=int(to_x),
        to_y=int(to_y),
        initiated_by=data.get("initiated_by", "player"),
        movement_budget=data.get("movement_budget"),
    )
    await repo.save(board)
    tok = board.state.tokens[token_id]
    msg = {
        "type": "token_moved",
        "action": "token_moved",
        "status": "confirmed",
        "session_id": session_id,
        "token_id": token_id,
        "name": tok.name,
        "x": tok.x,
        "y": tok.y,
        "movement_cost": cost,
        "hazard_triggered": hazard,
        "damage_dice": dice,
        "active_hazard": tok.active_hazard,
    }
    await board_ws_manager.broadcast(session_id, msg)


async def _dispatch_action(session_id: str, action: str, is_cast: bool, data: dict[str, Any]):
    if not is_cast and action in GHOST_ACTIONS:
        await _handle_ghost_preview(session_id, data)
    elif action in CONFIRM_ACTIONS:
        await _handle_confirm_move(session_id, data)
    elif action in CANCEL_ACTIONS:
        msg = {
            "type": "preview_cancelled",
            "action": "preview_cancelled",
            "status": "cancelled",
            "session_id": session_id,
            "token_id": data.get("token_id"),
        }
        await board_ws_manager.broadcast(session_id, msg)
    else:
        board = await get_board(session_id)
        handled = await handle_ws_action(session_id, action, data, board) or await handle_ws_spell(
            session_id, action, data, board
        )
        if not handled:
            raise UnknownBoardAction(action)


def _board_view_authorizer(session_id: str) -> WebSocketAuthorizer:
    """Check `board.view` on the session's board."""

    async def _may_view(user_id: str) -> bool:
        return await can_on_board(user_id, session_id, VIEW)

    return _may_view


@router.websocket("/ws/boards/{session_id}")
async def board_websocket(websocket: WebSocket, session_id: str):
    """Real-time tactical board WebSocket stream. It needs a bearer and `board.view`."""
    principal = await admit_websocket(
        websocket, get_zitadel_auth_service(), _board_view_authorizer(session_id)
    )
    if principal is None:
        return
    user_id = principal.user_id
    board_ws_manager.register(session_id, websocket)
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "session_id": session_id,
                "message": "Connected to tactical board real-time stream.",
            }
        )
        while True:
            data = await websocket.receive_json()
            action = data.get("action") or data.get("type") or "unknown"
            is_cast = action == "runefoble.events.watcher.speech_intent_parsed" and (
                data.get("action_type") == "cast_spell"
                or data.get("parameters", {}).get("action") == "cast_spell"
            )

            try:
                await authorize_message(user_id, session_id, action, is_cast, data)
                await _dispatch_action(session_id, action, is_cast, data)
            except BoardActionDenied as exc:
                await send_socket_error(
                    websocket, "PERMISSION_DENIED", str(exc), status=403, session_id=session_id
                )
            except BoardNotFoundError as exc:
                await send_socket_error(
                    websocket, "NOT_FOUND", str(exc), status=404, session_id=session_id
                )
            except UnknownBoardAction as exc:
                await send_socket_error(
                    websocket,
                    "UNKNOWN_ACTION",
                    f"Unknown board action: {exc}",
                    status=422,
                    session_id=session_id,
                )
            except ValueError as exc:
                await send_socket_error(
                    websocket, "INVALID", str(exc), status=422, session_id=session_id
                )
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Board socket failed on %s", session_id)
        await websocket.close(code=1011)
    finally:
        board_ws_manager.disconnect(session_id, websocket)


__all__ = ["board_websocket", "router"]
