"""Token placement, coordinate relocation, and token removal router."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from board_state.aggregate import PlacedTokenState
from board_state.authz import bind_token, require_token_move, unbind_token
from board_state.dependencies import (
    get_board,
    get_current_user_id,
    get_event_bus,
    repo,
)
from board_state.events import publish_board_events
from board_state.models import (
    MoveTokenRequest,
    MoveTokenResponse,
    PlaceTokenRequest,
)
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(tags=["tokens"])


@router.post(
    "/api/v1/boards/{session_id}/tokens",
    response_model=PlacedTokenState,
)
async def place_token(
    session_id: str, req: PlaceTokenRequest, user_id: Annotated[str, Depends(get_current_user_id)]
):
    """Place a token. A character token needs its owner. Other tokens need a board manager."""
    board = await get_board(session_id)
    token_id = req.token_id or str(uuid4())
    await bind_token(session_id, token_id, req.character_id, user_id)
    try:
        board.place_token(
            token_id=token_id,
            name=req.name,
            token_type=req.token_type,
            x=req.x,
            y=req.y,
            hp=req.hp,
            is_friendly=req.is_friendly,
            vision_radius=req.vision_radius,
        )
        await repo.save(board)
        return board.state.tokens[token_id]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/api/v1/boards/{session_id}/tokens/{token_id}/move",
    response_model=MoveTokenResponse,
)
async def move_token_by_id(
    session_id: str,
    token_id: str,
    req: MoveTokenRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    board = await get_board(session_id)
    await require_token_move(user_id, session_id, token_id)
    try:
        move_res = board.move_token(
            token_id=token_id,
            to_x=req.to_x,
            to_y=req.to_y,
            initiated_by=req.initiated_by,
            movement_budget=req.movement_budget,
        )
        cost, hazard_trig, dmg_dice = move_res
        trap_trig = getattr(move_res, "trap_triggered", None)
        movement_paused = getattr(move_res, "movement_paused", False)

        bus = get_event_bus()
        uncommitted = list(board.uncommitted_events)
        await repo.save(board)
        if bus is not None:
            await publish_board_events(bus, uncommitted)

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
            movement_cost=cost,
            hazard_triggered=hazard_trig,
            damage_dice=dmg_dice,
            trap_triggered=trap_trig,
            movement_paused=movement_paused,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/api/v1/boards/{session_id}/move",
    response_model=MoveTokenResponse,
)
async def move_token(
    session_id: str, req: MoveTokenRequest, user_id: Annotated[str, Depends(get_current_user_id)]
):
    if not req.token_id:
        raise HTTPException(status_code=400, detail="token_id is required")
    return await move_token_by_id(session_id, req.token_id, req, user_id)


@router.delete("/api/v1/boards/{session_id}/tokens/{token_id}")
async def remove_token(
    session_id: str,
    token_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    reason: str = "defeated",
):
    board = await get_board(session_id)
    await require_token_move(user_id, session_id, token_id)
    try:
        board.remove_token(token_id=token_id, reason=reason)
        await repo.save(board)
        await unbind_token(token_id)
        return {"token_id": token_id, "status": "removed", "reason": reason}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
