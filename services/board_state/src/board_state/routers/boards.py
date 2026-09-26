"""Board aggregate lifecycle and microfrontend discovery router."""

from __future__ import annotations

import contextlib
import logging
from typing import Annotated
from uuid import uuid4

from board_state.aggregate import BoardAggregate, BoardState
from board_state.dependencies import get_event_bus, get_or_create_board, repo, to_board_uuid
from board_state.models import CreateBoardRequest, UVTTImportResponse
from board_state.parsers.uvtt import apply_uvtt_to_board, parse_uvtt_data, store_uvtt_image
from fastapi import APIRouter, File, HTTPException, Request, UploadFile

logger = logging.getLogger("runefoble.board_state.routers.boards")

router = APIRouter(tags=["boards"])


@router.get("/ui/manifest")
def get_ui_manifest():
    """Advertise vendored microfrontend components for board state."""
    return {
        "service": "board_state",
        "package": "@runefoble/board-state-ui",
        "components": ["runefoble-board", "runefoble-map-uploader"],
        "version": "0.1.0",
    }


@router.post("/api/v1/boards", response_model=BoardState)
async def create_board(req: CreateBoardRequest):
    cols = req.cols or req.width or 10
    rows = req.rows or req.height or 10
    sess_id = req.session_id or req.board_id or str(uuid4())
    board_id = to_board_uuid(sess_id)
    board = BoardAggregate(board_id)
    board.initialize_grid(cols=cols, rows=rows, session_id=sess_id)
    await repo.save(board)
    return board.state


@router.get("/api/v1/boards/{session_id}", response_model=BoardState)
async def get_board(session_id: str):
    board = await get_or_create_board(session_id)
    return board.state


@router.post("/api/v1/board/{id}/import/uvtt", response_model=UVTTImportResponse)
@router.post("/api/v1/boards/{id}/import/uvtt", response_model=UVTTImportResponse)
async def import_uvtt_map_endpoint(
    id: str,
    request: Request,
    file: Annotated[UploadFile | None, File()] = None,
) -> UVTTImportResponse:
    """Import a Universal VTT (.dd2vtt) map, populate wall segments and obstacle bounds, and store map texture."""
    if file is not None:
        content = await file.read()
    else:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            content = await request.json()
        else:
            content = await request.body()
            if not content:
                raise HTTPException(status_code=400, detail="Missing UVTT payload or file")

    try:
        parsed = parse_uvtt_data(content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Universal VTT format: {exc}") from exc

    # Store background map texture in Silo S3 if image payload exists
    asset_id, image_url = None, None
    if parsed.image_bytes:
        try:
            asset_id, image_url = store_uvtt_image(
                image_bytes=parsed.image_bytes,
                mime_type=parsed.image_mime_type,
                owner_id="uvtt_importer",
            )
        except Exception as exc:
            logger.warning("Failed to store UVTT image in Silo S3: %s", exc)

    # Load or create board aggregate and apply imported geometry
    board = await get_or_create_board(id)
    apply_uvtt_to_board(board, parsed, asset_id=asset_id, image_url=image_url)
    await repo.save(board)

    # Publish map imported event to event bus if available
    bus = get_event_bus()
    if bus and board.uncommitted_events:
        with contextlib.suppress(Exception):
            await bus.publish(board.uncommitted_events[-1])

    return UVTTImportResponse(
        board_id=board.aggregate_id,
        session_id=str(board.state.session_id),
        cols=board.state.cols,
        rows=board.state.rows,
        pixels_per_grid=board.state.pixels_per_grid,
        wall_segments=board.state.wall_segments,
        portals=board.state.portals,
        lights=board.state.lights,
        background_image_url=board.state.background_image_url,
        background_asset_id=board.state.background_asset_id,
        tokens=board.state.tokens,
        status="imported",
    )
