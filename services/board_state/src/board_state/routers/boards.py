"""Board aggregate lifecycle and microfrontend discovery router."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from board_state.aggregate import BoardAggregate
from board_state.authz import (
    VIEW,
    VIEW_SECRET_LAYER,
    bind_board_to_campaign,
    can_on_board,
    require_board_permission,
    require_campaign_run_session,
)
from board_state.dependencies import (
    CallerId,
    CallerOrService,
    get_board,
    repo,
)
from board_state.models import BoardState, CreateBoardRequest
from board_state.projection import project_board
from fastapi import APIRouter, HTTPException
from runefoble_platform.aggregate_loading import save_or_conflict
from runefoble_platform.identifiers import opaque_aggregate_id
from runefoble_platform.ui_manifest import load_ui_manifest

# Start-up fails when the manifest is missing or invalid. No fallback manifest exists (ADR-0015 4).
UI_MANIFEST = load_ui_manifest(Path(__file__).resolve().parents[3] / "ui" / "manifest.json")

logger = logging.getLogger("runefoble.board_state.routers.boards")

router = APIRouter(tags=["boards"])
# Microfrontend discovery stays public. It carries no board data.
ui_manifest_router = APIRouter(tags=["boards"])


@ui_manifest_router.get("/ui/manifest")
def get_ui_manifest():
    """Advertise vendored microfrontend components for board state."""
    return UI_MANIFEST


@router.post("/api/v1/boards", response_model=BoardState)
async def create_board(req: CreateBoardRequest, user_id: CallerId):
    """Create the board for a session. The caller needs `campaign.run_session` on the campaign.

    The board is saved first. Then `board:<id>#campaign@campaign:<cid>` is written, so a
    request that fails to save never binds an existing board to another campaign.
    """
    if not req.campaign_id:
        raise HTTPException(status_code=400, detail="campaign_id is required to create a board")
    await require_campaign_run_session(user_id, req.campaign_id)
    cols = req.cols or req.width or 10
    rows = req.rows or req.height or 10
    sess_id = req.session_id or req.board_id or str(uuid4())
    board_id = opaque_aggregate_id(sess_id, field="sess_id")
    board = BoardAggregate(board_id)
    board.initialize_grid(cols=cols, rows=rows, session_id=sess_id)
    await save_or_conflict(
        repo,
        board,
        lambda: HTTPException(status_code=409, detail=f"A board exists for session {sess_id}"),
    )
    await bind_board_to_campaign(sess_id, req.campaign_id)
    return board.state


@router.get("/api/v1/boards/{session_id}", response_model=BoardState)
async def read_board(session_id: str, caller: CallerOrService):
    """Return the board for a session. Respond 404 when no board exists. Never creates one.

    A caller without `board.view_secret_layer` gets the public projection. Secret traps,
    secret doors, and secret portals are absent from it.
    """
    board = await get_board(session_id)
    if caller.user_id is not None:
        # A service call with no user (the internal service credential) has no board role to check.
        await require_board_permission(caller.user_id, session_id, VIEW)
    can_view_secret = await can_on_board(caller.user_id, session_id, VIEW_SECRET_LAYER)
    return project_board(board.state, can_view_secret)
