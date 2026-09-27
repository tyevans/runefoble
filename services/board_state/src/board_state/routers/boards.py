"""Board aggregate lifecycle and microfrontend discovery router."""

from __future__ import annotations

import logging
from uuid import uuid4

from board_state.aggregate import BoardAggregate, BoardState
from board_state.dependencies import get_or_create_board, repo, to_board_uuid
from board_state.models import CreateBoardRequest
from fastapi import APIRouter

logger = logging.getLogger("runefoble.board_state.routers.boards")

router = APIRouter(tags=["boards"])


@router.get("/ui/manifest")
@router.get("/board_state/ui/manifest")
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
        ],
        "tags": [
            "runefoble-board",
            "runefoble-map-uploader",
            "runefoble-radial-menu",
            "runefoble-aoe-template",
            "runefoble-tabletop-3d",
            "runefoble-dm-trap-controls",
            "runefoble-map-switcher",
        ],
        "styles": [
            "./src/runefoble-board.styles.ts",
            "./src/runefoble-map-uploader.styles.ts",
            "./src/runefoble-dm-trap-controls.styles.ts",
        ],
        "scripts": [
            "./src/index.ts",
        ],
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
