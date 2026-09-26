"""APIRouters for Game Session microservice."""

from game_session.routers.autopilot import router as autopilot_router
from game_session.routers.combat import router as combat_router
from game_session.routers.session import router as session_router

__all__ = [
    "autopilot_router",
    "combat_router",
    "session_router",
]
