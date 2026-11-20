"""Token placement, coordinate relocation, and token removal router."""

from __future__ import annotations

from uuid import uuid4

from board_state.aggregate import PlacedTokenState
from board_state.authz import (
    VIEW,
    bind_token,
    require_board_permission,
    require_token_move,
    unbind_token,
)
from board_state.dependencies import (
    CallerId,
    get_board,
    get_event_bus,
    repo,
)
from board_state.events import save_and_publish
from board_state.models import (
    MoveTokenRequest,
    MoveTokenResponse,
    PlaceTokenRequest,
)
from board_state.realtime import board_ws_manager
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["tokens"])


@router.post(
    "/api/v1/boards/{session_id}/tokens",
    response_model=PlacedTokenState,
)
async def place_token(session_id: str, req: PlaceTokenRequest, user_id: CallerId):
    """Place a token. A character token needs its owner. Other tokens need a board manager.

    After the save, every open board socket of the session gets one `token_placed` frame.
    """
    board = await get_board(session_id)
    token_id = req.token_id or str(uuid4())
    await bind_token(session_id, token_id, req.character_id, user_id, req.token_type)
    board.place_token(
        token_id=token_id,
        name=req.name,
        token_type=req.token_type,
        x=req.x,
        y=req.y,
        hp=req.hp,
        is_friendly=req.is_friendly,
        vision_radius=req.vision_radius,
        character_id=req.character_id,
    )
    await save_and_publish(repo, board, get_event_bus())
    token = board.state.tokens[token_id]
    await board_ws_manager.broadcast(
        session_id,
        {"type": "token_placed", "session_id": session_id, "token": token.model_dump(mode="json")},
    )
    return token


@router.get(
    "/api/v1/boards/{session_id}/tokens/{token_id}",
    response_model=PlacedTokenState,
)
async def read_token(
    session_id: str,
    token_id: str,
    user_id: CallerId,
):
    """Return one placed token of a board. Needs `board.view`. Respond 404 for an unknown token."""
    board = await get_board(session_id)
    await require_board_permission(user_id, session_id, VIEW)
    token = board.state.tokens.get(token_id)
    if token is None:
        raise HTTPException(status_code=404, detail=f"Token not found: {token_id}")
    return token


@router.post(
    "/api/v1/boards/{session_id}/tokens/{token_id}/move",
    response_model=MoveTokenResponse,
)
async def move_token_by_id(
    session_id: str,
    token_id: str,
    req: MoveTokenRequest,
    user_id: CallerId,
):
    board = await get_board(session_id)
    await require_token_move(user_id, session_id, token_id)
    outcome = board.move_token(
        token_id=token_id,
        to_x=req.to_x,
        to_y=req.to_y,
        initiated_by=req.initiated_by,
        movement_budget=req.movement_budget,
    )

    await save_and_publish(repo, board, get_event_bus())

    tok = board.state.tokens[token_id]
    return MoveTokenResponse(
        token_id=tok.token_id,
        name=tok.name,
        token_type=tok.token_type,
        x=tok.x,
        y=tok.y,
        hp=tok.hp,
        is_friendly=tok.is_friendly,
        vision_radius=tok.vision_radius,
        active_hazard=tok.active_hazard,
        hazard_status=tok.hazard_status,
        **outcome.as_wire(),
    )


@router.post(
    "/api/v1/boards/{session_id}/move",
    response_model=MoveTokenResponse,
)
async def move_token(session_id: str, req: MoveTokenRequest, user_id: CallerId):
    if not req.token_id:
        raise HTTPException(status_code=400, detail="token_id is required")
    return await move_token_by_id(session_id, req.token_id, req, user_id)


@router.delete("/api/v1/boards/{session_id}/tokens/{token_id}")
async def remove_token(
    session_id: str,
    token_id: str,
    user_id: CallerId,
    reason: str = "defeated",
):
    board = await get_board(session_id)
    await require_token_move(user_id, session_id, token_id)
    board.remove_token(token_id=token_id, reason=reason)
    await repo.save(board)
    await unbind_token(token_id)
    return {"token_id": token_id, "status": "removed", "reason": reason}
