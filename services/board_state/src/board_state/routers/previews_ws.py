"""Real-time tactical board WebSocket stream and ghost preview hub."""

from __future__ import annotations

import logging
from typing import Any

from board_state.authz import VIEW, can_on_board
from board_state.dependencies import (
    BoardNotFoundError,
    get_board,
    get_event_bus,
    get_zitadel_auth_service,
    repo,
)
from board_state.events import save_and_publish
from board_state.ghost_staging import GhostStageRequest, UnknownGhostToken, stage_ghost_preview
from board_state.realtime import board_ws_manager
from board_state.routers.previews_ws_actions import handle_ws_action
from board_state.routers.previews_ws_authz import BoardActionDenied, authorize_message
from board_state.routers.previews_ws_spells import handle_ws_spell
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from runefoble_auth.websocket import WebSocketAuthorizer, admit_websocket, send_socket_error
from runefoble_platform.domain_errors import DomainError

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


async def _handle_ghost_preview(session_id: str, data: dict[str, Any]) -> None:
    """Stage a preview from a socket frame. A frame that names no token stages nothing."""
    if data.get("to_x") is None or data.get("to_y") is None:
        return
    try:
        await stage_ghost_preview(session_id, GhostStageRequest.model_validate(data))
    except UnknownGhostToken:
        return


async def _handle_confirm_move(session_id: str, data: dict[str, Any]) -> None:
    """Move a token. A frame without a token or a target cell is refused, never dropped."""
    token_id, to_x, to_y = data.get("token_id"), data.get("to_x"), data.get("to_y")
    missing = [
        name
        for name, value in (("token_id", token_id), ("to_x", to_x), ("to_y", to_y))
        if value is None or value == ""
    ]
    if missing:
        raise ValueError(f"A move needs {', '.join(missing)}")
    board = await get_board(session_id)
    outcome = board.move_token(
        token_id=token_id,
        to_x=int(to_x),
        to_y=int(to_y),
        initiated_by=data.get("initiated_by", "player"),
        movement_budget=data.get("movement_budget"),
    )
    await save_and_publish(repo, board, get_event_bus())
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
        "active_hazard": tok.active_hazard,
        "version": board.version,
        **outcome.as_wire(),
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


async def _connected_frame(session_id: str) -> dict[str, Any]:
    """The first frame: the board tokens at subscribe time, keyed by token id.

    A client can read the board before its socket opens. The snapshot covers any move that
    was saved in between. `version` is the board version of the snapshot. A client keeps the
    newest version it applied, so a snapshot read before a later move never moves a token back.
    """
    board = await get_board(session_id)
    return {
        "type": "connected",
        "session_id": session_id,
        "message": "Connected to tactical board real-time stream.",
        "version": board.version,
        "tokens": {tid: t.model_dump(mode="json") for tid, t in board.state.tokens.items()},
    }


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
    # Register before the board read. A move saved after the read also reaches this socket,
    # so the `connected` snapshot plus the later frames miss no move.
    board_ws_manager.register(session_id, websocket)
    try:
        await websocket.send_json(await _connected_frame(session_id))
        while True:
            data = await websocket.receive_json()
            action = data.get("action") or data.get("type") or "unknown"
            is_cast = action == "runefoble.events.watcher.speech_intent_parsed" and (
                data.get("action_type") == "cast_spell"
                or data.get("parameters", {}).get("action") == "cast_spell"
            )

            # Each error frame names the action and the token, so the board UI can show it.
            context = {"session_id": session_id, "action": action, "token_id": data.get("token_id")}
            try:
                await authorize_message(user_id, session_id, action, is_cast, data)
                await _dispatch_action(session_id, action, is_cast, data)
            except BoardActionDenied as exc:
                await send_socket_error(
                    websocket, "PERMISSION_DENIED", str(exc), status=403, **context
                )
            except BoardNotFoundError as exc:
                await send_socket_error(websocket, "NOT_FOUND", str(exc), status=404, **context)
            except UnknownBoardAction as exc:
                await send_socket_error(
                    websocket,
                    "UNKNOWN_ACTION",
                    f"Unknown board action: {exc}",
                    status=422,
                    **context,
                )
            except (DomainError, ValueError) as exc:
                # A refused command, or a frame value that does not parse.
                await send_socket_error(websocket, "INVALID", str(exc), status=422, **context)
    except BoardNotFoundError as exc:
        # The view tuple exists, but the board does not: report it and close (4404).
        await send_socket_error(websocket, "NOT_FOUND", str(exc), status=404, session_id=session_id)
        await websocket.close(code=4404)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Board socket failed on %s", session_id)
        await websocket.close(code=1011)
    finally:
        board_ws_manager.disconnect(session_id, websocket)


__all__ = ["board_websocket", "router"]
