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
from runefoble_auth.websocket import (
    RUNEFOBLE_SUBPROTOCOL,
    WS_POLICY_VIOLATION,
    WebSocketAuthError,
    authenticate_websocket,
)

logger = logging.getLogger("runefoble.board_state.routers.previews_ws")

router = APIRouter(tags=["previews"])

GHOST_ACTIONS = ("preview_move", "ghost_preview", "speech_intent", "SpeechIntentParsed")
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


async def _send_error(
    websocket: WebSocket, session_id: str, status: int, message: str, code: str
) -> None:
    await websocket.send_json(
        {
            "type": "error",
            "code": code,
            "status": status,
            "session_id": session_id,
            "message": message,
        }
    )


async def _admit(websocket: WebSocket, session_id: str) -> str | None:
    """Verify the bearer and `board.view`. Close with 1008 before accept on a refusal."""
    try:
        principal = authenticate_websocket(websocket, get_zitadel_auth_service())
    except WebSocketAuthError as exc:
        logger.warning("Board socket denied on %s: %s", websocket.url.path, exc)
        await websocket.close(code=WS_POLICY_VIOLATION)
        return None
    if not await can_on_board(principal.user_id, session_id, VIEW):
        logger.warning("Board socket denied on %s: board.view is required", websocket.url.path)
        await websocket.close(code=WS_POLICY_VIOLATION)
        return None
    await websocket.accept(subprotocol=RUNEFOBLE_SUBPROTOCOL)
    return principal.user_id


@router.websocket("/ws/boards/{session_id}")
async def board_websocket(websocket: WebSocket, session_id: str):
    """Real-time tactical board WebSocket stream. It needs a bearer and `board.view`."""
    user_id = await _admit(websocket, session_id)
    if user_id is None:
        return
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
            is_cast = action == "SpeechIntentParsed" and (
                data.get("action_type") == "cast_spell"
                or data.get("parameters", {}).get("action") == "cast_spell"
            )

            try:
                await authorize_message(user_id, session_id, action, is_cast, data)
                await _dispatch_action(session_id, action, is_cast, data)
            except BoardActionDenied as exc:
                await _send_error(websocket, session_id, 403, str(exc), "FORBIDDEN")
            except BoardNotFoundError as exc:
                await _send_error(websocket, session_id, 404, str(exc), "NOT_FOUND")
            except UnknownBoardAction as exc:
                await _send_error(
                    websocket, session_id, 422, f"Unknown board action: {exc}", "UNKNOWN_ACTION"
                )
            except ValueError as exc:
                await _send_error(websocket, session_id, 422, str(exc), "INVALID")
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Board socket failed on %s", session_id)
        await websocket.close(code=1011)
    finally:
        board_ws_manager.disconnect(session_id, websocket)


__all__ = ["board_websocket", "router"]
