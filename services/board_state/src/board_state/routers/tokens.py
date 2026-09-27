"""Token placement, coordinate relocation, and token removal router."""

from __future__ import annotations

from uuid import uuid4

from board_state.aggregate import PlacedTokenState
from board_state.dependencies import get_event_bus, get_or_create_board, repo
from board_state.models import (
    MoveTokenRequest,
    MoveTokenResponse,
    PlaceTokenRequest,
)
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["tokens"])


@router.post("/api/v1/boards/{session_id}/tokens", response_model=PlacedTokenState)
async def place_token(session_id: str, req: PlaceTokenRequest):
    board = await get_or_create_board(session_id)
    token_id = req.token_id or str(uuid4())
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


@router.post("/api/v1/boards/{session_id}/tokens/{token_id}/move", response_model=MoveTokenResponse)
async def move_token_by_id(session_id: str, token_id: str, req: MoveTokenRequest):
    board = await get_or_create_board(session_id)
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
        if bus and uncommitted:
            for evt in uncommitted:
                try:
                    if hasattr(bus, "publish_event"):
                        await bus.publish_event("runefoble.events.board", evt)
                    elif hasattr(bus, "publish"):
                        await bus.publish(evt)
                except Exception:
                    pass

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


@router.post("/api/v1/boards/{session_id}/move", response_model=MoveTokenResponse)
async def move_token(session_id: str, req: MoveTokenRequest):
    if not req.token_id:
        raise HTTPException(status_code=400, detail="token_id is required")
    return await move_token_by_id(session_id, req.token_id, req)


@router.delete("/api/v1/boards/{session_id}/tokens/{token_id}")
async def remove_token(session_id: str, token_id: str, reason: str = "defeated"):
    board = await get_or_create_board(session_id)
    try:
        board.remove_token(token_id=token_id, reason=reason)
        await repo.save(board)
        return {"token_id": token_id, "status": "removed", "reason": reason}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
