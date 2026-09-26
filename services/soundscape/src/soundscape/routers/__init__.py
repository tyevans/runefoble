"""Routers package for soundscape microservice."""

from soundscape.routers.cue import router as cue_router
from soundscape.routers.stems import router as stems_router
from soundscape.routers.tension import router as tension_router

__all__ = ["cue_router", "stems_router", "tension_router"]
