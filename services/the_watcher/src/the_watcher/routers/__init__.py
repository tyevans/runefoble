"""APIRouters for The Watcher service."""

from the_watcher.routers.autonomous_dm import router as autonomous_dm_router
from the_watcher.routers.chronicle import router as chronicle_router
from the_watcher.routers.copilot import router as copilot_router
from the_watcher.routers.faction_resources import router as faction_resources_router
from the_watcher.routers.factions import router as factions_router
from the_watcher.routers.intent import router as intent_router
from the_watcher.routers.stand_in import router as stand_in_router

__all__ = [
    "autonomous_dm_router",
    "chronicle_router",
    "copilot_router",
    "factions_router",
    "faction_resources_router",
    "intent_router",
    "stand_in_router",
]
