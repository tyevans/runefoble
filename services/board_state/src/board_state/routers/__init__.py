"""APIRouters for Board State microservice."""

from board_state.routers.boards import router as boards_router
from board_state.routers.previews import router as previews_router
from board_state.routers.terrain import router as terrain_router
from board_state.routers.tokens import router as tokens_router
from board_state.routers.vfx import router as vfx_router

__all__ = [
    "boards_router",
    "previews_router",
    "terrain_router",
    "tokens_router",
    "vfx_router",
]
