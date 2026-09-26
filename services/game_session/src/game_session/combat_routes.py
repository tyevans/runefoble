"""Combat encounter and initiative order routes (compatibility shim)."""

from game_session.routers.combat import (
    STREAM_SESSION,
    init_combat_routes,
    router,
)

__all__ = ["STREAM_SESSION", "init_combat_routes", "router"]
