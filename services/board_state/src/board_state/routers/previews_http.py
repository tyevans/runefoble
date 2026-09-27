"""HTTP REST endpoints for kinematics and route preview calculations."""

from __future__ import annotations

from board_state.dependencies import get_or_create_board
from board_state.preview import (
    PreviewMoveRequest,
    PreviewMoveResponse,
    compute_kinematic_route_preview,
)
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["previews"])


@router.post(
    "/api/v1/boards/{session_id}/tokens/{token_id}/preview", response_model=PreviewMoveResponse
)
async def preview_token_move(session_id: str, token_id: str, req: PreviewMoveRequest):
    """Compute waypoint trajectory, 5-ft increments, terrain penalties, and hazard warnings."""
    board = await get_or_create_board(session_id)
    try:
        return compute_kinematic_route_preview(
            board_aggregate=board,
            token_id=token_id,
            to_x=req.to_x,
            to_y=req.to_y,
            from_x=req.from_x,
            from_y=req.from_y,
            movement_budget=req.movement_budget,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/v1/boards/{session_id}/preview", response_model=PreviewMoveResponse)
@router.post("/api/v1/boards/{session_id}/preview-move", response_model=PreviewMoveResponse)
async def preview_move(session_id: str, req: PreviewMoveRequest):
    if not req.token_id:
        raise HTTPException(status_code=400, detail="token_id is required")
    return await preview_token_move(session_id, req.token_id, req)


__all__ = ["preview_move", "preview_token_move", "router"]
