"""APIRouters for Board State microservice."""

from board_state.routers.actions import router as actions_router
from board_state.routers.aoe import router as aoe_router
from board_state.routers.boards import router as boards_router
from board_state.routers.physics import router as physics_router
from board_state.routers.previews import router as previews_router
from board_state.routers.terrain import router as terrain_router
from board_state.routers.tokens import router as tokens_router
from board_state.routers.traps import router as traps_router
from board_state.routers.uvtt_import import router as uvtt_import_router
from board_state.routers.vfx import router as vfx_router

__all__ = [
    "actions_router",
    "aoe_router",
    "boards_router",
    "physics_router",
    "previews_router",
    "terrain_router",
    "tokens_router",
    "traps_router",
    "uvtt_import_router",
    "vfx_router",
]
