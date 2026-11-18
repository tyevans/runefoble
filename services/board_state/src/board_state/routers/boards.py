"""Board aggregate lifecycle and microfrontend discovery router."""

from __future__ import annotations

import logging
from uuid import uuid4

from board_state.aggregate import BoardAggregate, BoardState
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
    to_board_uuid,
)
from board_state.models import CreateBoardRequest
from board_state.projection import project_board
from eventsource.domain.exceptions import OptimisticLockError
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("runefoble.board_state.routers.boards")

router = APIRouter(tags=["boards"])
# Microfrontend discovery stays public. It carries no board data.
ui_manifest_router = APIRouter(tags=["boards"])


@ui_manifest_router.get("/ui/manifest")
@ui_manifest_router.get("/board_state/ui/manifest")
def get_ui_manifest():
    """Advertise vendored microfrontend components for board state."""
    return {
        "service": "board_state",
        "package": "@runefoble/board-state-ui",
        "version": "0.1.0",
        "components": [
            "runefoble-board",
            "runefoble-map-uploader",
            "runefoble-radial-menu",
            "runefoble-aoe-template",
            "runefoble-tabletop-3d",
            "runefoble-dm-trap-controls",
            "runefoble-map-switcher",
            "runefoble-dice-tray-3d",
        ],
        "tags": [
            "runefoble-board",
            "runefoble-map-uploader",
            "runefoble-radial-menu",
            "runefoble-aoe-template",
            "runefoble-tabletop-3d",
            "runefoble-dm-trap-controls",
            "runefoble-map-switcher",
            "runefoble-dice-tray-3d",
        ],
        "styles": [
            "./src/runefoble-board.styles.ts",
            "./src/runefoble-map-uploader.styles.ts",
            "./src/runefoble-dm-trap-controls.styles.ts",
            "./src/runefoble-dice-tray-3d.styles.ts",
        ],
        "scripts": [
            "./src/index.ts",
        ],
    }


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
    board_id = to_board_uuid(sess_id)
    board = BoardAggregate(board_id)
    board.initialize_grid(cols=cols, rows=rows, session_id=sess_id)
    try:
        await repo.save(board)
    except OptimisticLockError as exc:
        raise HTTPException(
            status_code=409, detail=f"A board exists for session {sess_id}"
        ) from exc
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
