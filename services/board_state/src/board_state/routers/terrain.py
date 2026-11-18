"""Terrain elevation, hazard grid mutations, and fog-of-war visibility router."""

from __future__ import annotations

from typing import Annotated

from board_state.aggregate import PlacedTokenState, TerrainCellState
from board_state.authz import (
    MANAGE_TRAPS,
    VIEW_SECRET_LAYER,
    can_on_board,
    require_board_permission,
)
from board_state.dependencies import get_board, get_current_user_id, repo
from board_state.models import (
    ConfigureTerrainRequest,
    FogOfWarUpdateRequest,
    VisibilityResponse,
)
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(tags=["terrain"], dependencies=[Depends(get_current_user_id)])


def _visibility(session_id: str, board, is_dm: bool) -> VisibilityResponse:
    """Compute fog-of-war visibility masks and filter hidden enemies unless the caller is DM."""
    party_visible = board.compute_party_visibility()
    revealed_set = {tuple(c) for c in board.state.revealed_cells}

    filtered_tokens: list[PlacedTokenState] = []
    for token in board.state.tokens.values():
        if (
            is_dm
            or token.is_friendly
            or not board.state.fog_of_war_enabled
            or (token.x, token.y) in revealed_set
        ):
            filtered_tokens.append(token)

    return VisibilityResponse(
        session_id=session_id,
        cols=board.state.cols,
        rows=board.state.rows,
        fog_of_war_enabled=board.state.fog_of_war_enabled,
        revealed_cells=board.state.revealed_cells,
        currently_visible_cells=party_visible,
        tokens=filtered_tokens,
    )


@router.get("/api/v1/boards/{session_id}/visibility", response_model=VisibilityResponse)
async def get_visibility(session_id: str, user_id: Annotated[str, Depends(get_current_user_id)]):
    """Compute visibility. The DM flag comes from `board.view_secret_layer`, never from the caller."""
    board = await get_board(session_id)
    is_dm = await can_on_board(user_id, session_id, VIEW_SECRET_LAYER)
    return _visibility(session_id, board, is_dm)


@router.post("/api/v1/boards/{session_id}/terrain", response_model=TerrainCellState)
async def configure_terrain(
    session_id: str,
    req: ConfigureTerrainRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    """Set terrain on a cell. Needs `board.manage_traps`."""
    await require_board_permission(user_id, session_id, MANAGE_TRAPS)
    board = await get_board(session_id)
    try:
        board.configure_terrain(
            x=req.x,
            y=req.y,
            elevation=req.elevation,
            terrain_type=req.terrain_type,
            hazard=req.hazard,
        )
        await repo.save(board)
        return board.get_terrain(req.x, req.y)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/v1/boards/{session_id}/fog-of-war/reveal", response_model=VisibilityResponse)
async def reveal_fog_of_war(
    session_id: str,
    req: FogOfWarUpdateRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    """Manually reveal fog-of-war cells. Needs `board.view_secret_layer`."""
    await require_board_permission(user_id, session_id, VIEW_SECRET_LAYER)
    board = await get_board(session_id)
    try:
        board.reveal_cells(cells=req.cells, revealed_by_token_id=req.token_id)
        await repo.save(board)
        return _visibility(session_id, board, is_dm=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/v1/boards/{session_id}/fog-of-war/shroud", response_model=VisibilityResponse)
async def shroud_fog_of_war(
    session_id: str,
    req: FogOfWarUpdateRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    """Manually shroud fog-of-war cells. Needs `board.view_secret_layer`."""
    await require_board_permission(user_id, session_id, VIEW_SECRET_LAYER)
    board = await get_board(session_id)
    try:
        board.shroud_cells(cells=req.cells)
        await repo.save(board)
        return _visibility(session_id, board, is_dm=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
