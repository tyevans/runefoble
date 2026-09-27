"""Kinematics, route preview calculation, and WebSocket streaming router aggregator facade."""

from __future__ import annotations

from board_state.routers.previews_http import (
    preview_move,
    preview_token_move,
)
from board_state.routers.previews_http import (
    router as previews_http_router,
)
from board_state.routers.previews_ws import (
    board_websocket,
)
from board_state.routers.previews_ws import (
    router as previews_ws_router,
)
from fastapi import APIRouter

router = APIRouter(tags=["previews"])
router.include_router(previews_http_router)
router.include_router(previews_ws_router)

__all__ = [
    "board_websocket",
    "preview_move",
    "preview_token_move",
    "previews_http_router",
    "previews_ws_router",
    "router",
]
