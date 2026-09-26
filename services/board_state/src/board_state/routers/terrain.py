"""Terrain elevation, hazard grid mutations, and fog-of-war visibility router."""

from __future__ import annotations

from board_state.aggregate import PlacedTokenState, TerrainCellState
from board_state.dependencies import get_or_create_board, repo
from board_state.models import (
    ConfigureTerrainRequest,
    FogOfWarUpdateRequest,
    VisibilityResponse,
)
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(tags=["terrain"])


@router.get("/api/v1/boards/{session_id}/visibility", response_model=VisibilityResponse)
async def get_visibility(
    session_id: str, is_dm: bool = Query(False, description="Whether caller is Dungeon Master")
):
    """Compute fog-of-war visibility masks and filter hidden enemies."""
    board = await get_or_create_board(session_id)
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


@router.post("/api/v1/boards/{session_id}/terrain", response_model=TerrainCellState)
async def configure_terrain(session_id: str, req: ConfigureTerrainRequest):
    board = await get_or_create_board(session_id)
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
async def reveal_fog_of_war(session_id: str, req: FogOfWarUpdateRequest):
    """Manually reveal fog-of-war cells."""
    board = await get_or_create_board(session_id)
    try:
        board.reveal_cells(cells=req.cells, revealed_by_token_id=req.token_id)
        await repo.save(board)
        return await get_visibility(session_id, is_dm=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/v1/boards/{session_id}/fog-of-war/shroud", response_model=VisibilityResponse)
async def shroud_fog_of_war(session_id: str, req: FogOfWarUpdateRequest):
    """Manually shroud fog-of-war cells."""
    board = await get_or_create_board(session_id)
    try:
        board.shroud_cells(cells=req.cells)
        await repo.save(board)
        return await get_visibility(session_id, is_dm=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
