"""Spectator camera routes. The board owner keeps the camera target for each session."""

from __future__ import annotations

from board_state.authz import VIEW, require_board_permission, require_session_participate
from board_state.camera.director import (
    CameraTokenNotFoundError,
    focus_on_token_moved,
    focus_on_turn_started,
)
from board_state.camera.models import CameraTarget
from board_state.dependencies import CallerId, CallerOrService, get_board, repo
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["Spectator"])


class TurnStartedFocusRequest(BaseModel):
    """Focus the camera on the token that starts its turn. Name the token or its character."""

    token_id: str | None = None
    character_id: str | None = None
    duration_ms: int | None = None
    easing: str | None = None


class TokenMovedFocusRequest(BaseModel):
    """Focus the camera on the destination of a token move."""

    token_id: str
    to_x: int
    to_y: int
    duration_ms: int | None = None
    easing: str | None = None


@router.get("/api/v1/boards/{session_id}/camera", response_model=CameraTarget)
async def read_camera(session_id: str, caller: CallerOrService) -> CameraTarget:
    """Return the current camera target. A board without focus events returns the initial target."""
    board = await get_board(session_id)
    if caller.user_id is not None:
        await require_board_permission(caller.user_id, session_id, VIEW)
    return board.state.camera


@router.post("/api/v1/boards/{session_id}/camera/turn-started", response_model=CameraTarget)
async def focus_turn_started(
    session_id: str, req: TurnStartedFocusRequest, user_id: CallerId
) -> CameraTarget:
    """Center the camera on the active token. The caller needs `session.participate`."""
    board = await get_board(session_id)
    await require_session_participate(user_id, session_id)
    try:
        target = focus_on_turn_started(
            board.state,
            token_id=req.token_id,
            character_id=req.character_id,
            duration_ms=req.duration_ms,
            easing=req.easing,
        )
    except CameraTokenNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    board.focus_camera(target)
    await repo.save(board)
    return target


@router.post("/api/v1/boards/{session_id}/camera/token-moved", response_model=CameraTarget)
async def focus_token_moved(
    session_id: str, req: TokenMovedFocusRequest, user_id: CallerId
) -> CameraTarget:
    """Center the camera on a move destination. The caller needs `session.participate`."""
    board = await get_board(session_id)
    await require_session_participate(user_id, session_id)
    target = focus_on_token_moved(
        token_id=req.token_id,
        to_x=req.to_x,
        to_y=req.to_y,
        duration_ms=req.duration_ms,
        easing=req.easing,
    )
    board.focus_camera(target)
    await repo.save(board)
    return target
