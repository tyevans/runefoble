"""Stage a ghost preview on the board socket. A staged preview never moves a token (TASK-0814).

The Watcher proposes a move. This module computes the route and broadcasts a `ghost_preview`
to every board socket of the session. Only a `confirm_move` from the player commits the move.
"""

from __future__ import annotations

from typing import Any

from board_state.dependencies import get_board
from board_state.preview import compute_kinematic_route_preview
from board_state.realtime import board_ws_manager
from pydantic import BaseModel
from runefoble_platform.domain_errors import DomainNotFoundError


class GhostStageRequest(BaseModel):
    """A proposed move. Pass `token_id`, or `speaker_name` to find the token by name."""

    token_id: str | None = None
    speaker_name: str | None = None
    raw_transcript: str | None = None
    to_x: int
    to_y: int
    from_x: int | None = None
    from_y: int | None = None
    movement_budget: int | None = None
    timeout_seconds: int = 15


class UnknownGhostToken(DomainNotFoundError):
    """Raised when no token on the board matches the proposal."""


def find_token_id(board: Any, token_id: str | None, speaker_name: str | None) -> str | None:
    """Return the token id, or the id of the token whose name matches the speaker."""
    if token_id:
        return token_id
    if speaker_name:
        for tok in board.state.tokens.values():
            if tok.name.lower() == speaker_name.lower():
                return tok.token_id
    return None


async def stage_ghost_preview(session_id: str, req: GhostStageRequest) -> dict[str, Any]:
    """Compute the route, broadcast `ghost_preview` to the session, and return that message.

    Raises `BoardNotFoundError` when the session has no board, and `UnknownGhostToken` when no
    token matches. A route that the board cannot compute raises `DomainRefusedError`.
    """
    board = await get_board(session_id)
    token_id = find_token_id(board, req.token_id, req.speaker_name)
    if token_id is None or token_id not in board.state.tokens:
        raise UnknownGhostToken(f"No token matches the proposal on session '{session_id}'")
    preview = compute_kinematic_route_preview(
        board_aggregate=board,
        token_id=token_id,
        to_x=req.to_x,
        to_y=req.to_y,
        from_x=req.from_x,
        from_y=req.from_y,
        movement_budget=req.movement_budget,
    )
    message = {
        "type": "ghost_preview",
        "action": "ghost_preview",
        "status": "staged",
        "session_id": session_id,
        "speaker_name": req.speaker_name,
        "raw_transcript": req.raw_transcript,
        "preview": preview.model_dump(),
        "timeout_seconds": req.timeout_seconds,
    }
    await board_ws_manager.broadcast(session_id, message)
    return message
