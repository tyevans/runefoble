"""Board aggregate lifecycle and microfrontend discovery router."""

from __future__ import annotations

from uuid import uuid4

from board_state.aggregate import BoardAggregate, BoardState
from board_state.dependencies import get_or_create_board, repo, to_board_uuid
from board_state.models import CreateBoardRequest
from fastapi import APIRouter

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
