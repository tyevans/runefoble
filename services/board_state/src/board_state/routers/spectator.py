"""Audience board projection route. The owner checks `board.view` for a user caller."""

from __future__ import annotations

from board_state.authz import VIEW, require_board_permission
from board_state.dependencies import CallerOrService, get_board
from board_state.spectator import SpectatorBoardView, project_spectator_board
from fastapi import APIRouter

router = APIRouter(tags=["Spectator"])


@router.get("/api/v1/boards/{session_id}/spectator", response_model=SpectatorBoardView)
async def read_spectator_board(session_id: str, caller: CallerOrService) -> SpectatorBoardView:
    """Return the audience view of the board. Respond 404 when no board exists."""
    board = await get_board(session_id)
    if caller.user_id is not None:
        await require_board_permission(caller.user_id, session_id, VIEW)
    return project_spectator_board(board.state)
