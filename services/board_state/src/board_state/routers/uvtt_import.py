"""APIRouter for Universal VTT map import, interactive doors, and dynamic lights."""

from __future__ import annotations

import logging
from typing import Annotated

from board_state.authz import (
    MANAGE_TRAPS,
    PLAY,
    VIEW,
    VIEW_SECRET_LAYER,
    can_on_board,
    require_board_permission,
    require_campaign_permission,
)
from board_state.dependencies import CallerId, get_board, get_event_bus, get_principal, repo
from board_state.events import publish_board_events
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
from board_state.projection import public_doors, public_portals
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from runefoble_platform.storage import AssetStorageError

logger = logging.getLogger("runefoble.board_state.routers.uvtt_import")
router = APIRouter(tags=["uvtt"], dependencies=[Depends(get_principal)])


async def _publish_board_events(events: list) -> None:
    bus = get_event_bus()
    if bus is not None:
        await publish_board_events(bus, events)


@router.post("/board/{id}/import/uvtt", response_model=UVTTImportResponse)
@router.post("/boards/{id}/import/uvtt", response_model=UVTTImportResponse)
@router.post("/api/v1/board/{id}/import/uvtt", response_model=UVTTImportResponse)
@router.post("/api/v1/boards/{id}/import/uvtt", response_model=UVTTImportResponse)
async def import_uvtt_map_endpoint(
    id: str,
    request: Request,
    user_id: CallerId,
    file: Annotated[UploadFile | None, File()] = None,
) -> UVTTImportResponse:
    """Import a Universal VTT map, extracting walls, interactive doors, lights, and texture."""
    await require_board_permission(user_id, id, MANAGE_TRAPS)
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
        try:
            asset_id, image_url = await store_uvtt_image(
                parsed.image_bytes,
                parsed.image_mime_type,
                owner_id=user_id,
                session_id=id,
            )
        except AssetStorageError as exc:
            logger.error("Silo rejected UVTT battlemap image: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Silo asset storage is unavailable. The map was not imported.",
            ) from exc

    board = await get_board(id)
    apply_uvtt_to_board(board, parsed, asset_id=asset_id, image_url=image_url)
    events = list(board.uncommitted_events)
    await repo.save(board)
    await _publish_board_events(events)

    s = board.state
    can_view_secret = await can_on_board(user_id, id, VIEW_SECRET_LAYER)
    return UVTTImportResponse(
        board_id=board.aggregate_id,
        session_id=str(s.session_id),
        cols=s.cols,
        rows=s.rows,
        pixels_per_grid=s.pixels_per_grid,
        wall_segments=s.wall_segments,
        portals=s.portals if can_view_secret else public_portals(s.portals),
        doors=s.doors if can_view_secret else public_doors(s.doors),
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
    id: str,
    door_id: str,
    user_id: CallerId,
    body: ToggleDoorRequest | None = None,
) -> dict:
    """Toggle state of an interactive door or portal on the board."""
    board = await get_board(id)
    await require_campaign_permission(user_id, id, PLAY)
    status, is_open = (body.status, body.is_open) if body else (None, None)
    result = board.toggle_door(door_id=door_id, status=status, is_open=is_open)
    events = list(board.uncommitted_events)
    await repo.save(board)
    await _publish_board_events(events)
    return {"status": "success", "door": board.state.doors.get(door_id, result)}


@router.get("/board/{id}/doors")
@router.get("/boards/{id}/doors")
async def get_doors_endpoint(id: str, user_id: CallerId) -> dict:
    """Query the doors and portals. Secret ones need `board.view_secret_layer`."""
    board = await get_board(id)
    await require_board_permission(user_id, id, VIEW)
    if await can_on_board(user_id, id, VIEW_SECRET_LAYER):
        return {"doors": board.state.doors, "portals": board.state.portals}
    return {
        "doors": public_doors(board.state.doors),
        "portals": public_portals(board.state.portals),
    }


@router.post("/board/{id}/lights")
@router.post("/boards/{id}/lights")
@router.post("/api/v1/board/{id}/lights")
async def place_light_endpoint(id: str, req: PlaceLightRequest, user_id: CallerId) -> dict:
    """Place or update a dynamic point light source on the tactical board."""
    board = await get_board(id)
    await require_board_permission(user_id, id, MANAGE_TRAPS)
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
    events = list(board.uncommitted_events)
    await repo.save(board)
    await _publish_board_events(events)
    return {"status": "success", "light_id": lid}


@router.get("/board/{id}/lights")
@router.get("/boards/{id}/lights")
async def get_lights_endpoint(id: str, user_id: CallerId) -> dict:
    """Query active dynamic light sources on the board."""
    board = await get_board(id)
    await require_board_permission(user_id, id, VIEW)
    return {"lights": board.state.lights}
