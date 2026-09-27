"""APIRouter for Universal VTT map import, interactive doors, and dynamic lights."""

from __future__ import annotations

import contextlib
import logging
from typing import Annotated

from board_state.dependencies import get_event_bus, get_or_create_board, repo
from board_state.models import (
    PlaceLightRequest,
    ToggleDoorRequest,
    UVTTImportResponse,
)
from board_state.parsers.uvtt import (
    apply_uvtt_to_board,
    parse_uvtt_data,
    store_uvtt_image,
)
from fastapi import APIRouter, File, HTTPException, Request, UploadFile

logger = logging.getLogger("runefoble.board_state.routers.uvtt_import")
router = APIRouter(tags=["uvtt"])


async def _publish_latest_event(board) -> None:
    bus = get_event_bus()
    if bus and board.uncommitted_events:
        with contextlib.suppress(Exception):
            await bus.publish(board.uncommitted_events[-1])


@router.post("/board/{id}/import/uvtt", response_model=UVTTImportResponse)
@router.post("/boards/{id}/import/uvtt", response_model=UVTTImportResponse)
@router.post("/api/v1/board/{id}/import/uvtt", response_model=UVTTImportResponse)
@router.post("/api/v1/boards/{id}/import/uvtt", response_model=UVTTImportResponse)
async def import_uvtt_map_endpoint(
    id: str,
    request: Request,
    file: Annotated[UploadFile | None, File()] = None,
) -> UVTTImportResponse:
    """Import a Universal VTT map, extracting walls, interactive doors, lights, and texture."""
    if file is not None:
        content = await file.read()
    else:
        ctype = request.headers.get("content-type", "")
        content = await request.json() if "application/json" in ctype else await request.body()
        if not content:
            raise HTTPException(status_code=400, detail="Missing UVTT payload or file")

    try:
        parsed = parse_uvtt_data(content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Universal VTT format: {exc}") from exc

    asset_id, image_url = None, None
    if parsed.image_bytes:
        with contextlib.suppress(Exception):
            asset_id, image_url = store_uvtt_image(parsed.image_bytes, parsed.image_mime_type)

    board = await get_or_create_board(id)
    apply_uvtt_to_board(board, parsed, asset_id=asset_id, image_url=image_url)
    await repo.save(board)
    await _publish_latest_event(board)

    s = board.state
    return UVTTImportResponse(
        board_id=board.aggregate_id,
        session_id=str(s.session_id),
        cols=s.cols,
        rows=s.rows,
        pixels_per_grid=s.pixels_per_grid,
        wall_segments=s.wall_segments,
        portals=s.portals,
        doors=s.doors,
        lights=s.lights,
        background_image_url=s.background_image_url,
        background_asset_id=s.background_asset_id,
        tokens=s.tokens,
        status="imported",
    )


@router.post("/board/{id}/doors/{door_id}/toggle")
@router.post("/boards/{id}/doors/{door_id}/toggle")
@router.post("/api/v1/board/{id}/doors/{door_id}/toggle")
async def toggle_door_endpoint(
    id: str, door_id: str, body: ToggleDoorRequest | None = None
) -> dict:
    """Toggle state of an interactive door or portal on the board."""
    board = await get_or_create_board(id)
    status, is_open = (body.status, body.is_open) if body else (None, None)
    result = board.toggle_door(door_id=door_id, status=status, is_open=is_open)
    await repo.save(board)
    await _publish_latest_event(board)
    return {"status": "success", "door": board.state.doors.get(door_id, result)}


@router.get("/board/{id}/doors")
@router.get("/boards/{id}/doors")
async def get_doors_endpoint(id: str) -> dict:
    """Query interactive doors and secret portals on the board."""
    board = await get_or_create_board(id)
    return {"doors": board.state.doors, "portals": board.state.portals}


@router.post("/board/{id}/lights")
@router.post("/boards/{id}/lights")
@router.post("/api/v1/board/{id}/lights")
async def place_light_endpoint(id: str, req: PlaceLightRequest) -> dict:
    """Place or update a dynamic point light source on the tactical board."""
    board = await get_or_create_board(id)
    lid = board.place_light_source(
        light_id=req.light_id,
        x=req.x,
        y=req.y,
        color_hex=req.color_hex,
        bright_radius=req.bright_radius,
        dim_radius=req.dim_radius,
        flicker_intensity=req.flicker_intensity,
        intensity=req.intensity,
        shadows=req.shadows,
        metadata=req.metadata,
    )
    await repo.save(board)
    await _publish_latest_event(board)
    return {"status": "success", "light_id": lid}


@router.get("/board/{id}/lights")
@router.get("/boards/{id}/lights")
async def get_lights_endpoint(id: str) -> dict:
    """Query active dynamic light sources on the board."""
    board = await get_or_create_board(id)
    return {"lights": board.state.lights}
