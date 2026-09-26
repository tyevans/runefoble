"""APIRouters for Game Session microservice."""

from game_session.routers.autopilot import router as autopilot_router
from game_session.routers.campfire import router as campfire_router
from game_session.routers.combat import router as combat_router
from game_session.routers.session import router as session_router
from game_session.routers.stronghold import router as stronghold_router

__all__ = [
    "autopilot_router",
    "campfire_router",
    "combat_router",
    "session_router",
    "stronghold_router",
]
