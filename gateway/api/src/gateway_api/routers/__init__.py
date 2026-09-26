"""Modular APIRouter packages for Gateway API."""

from gateway_api.routers.campaigns import router as campaigns_router
from gateway_api.routers.health import router as health_router
from gateway_api.routers.overlay import router as overlay_router
from gateway_api.routers.spectator import router as spectator_router

__all__ = [
    "campaigns_router",
    "health_router",
    "overlay_router",
    "spectator_router",
]
