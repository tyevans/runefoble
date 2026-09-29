"""Modular APIRouter packages for Gateway API."""

from gateway_api.routers.auth import router as auth_router
from gateway_api.routers.campaigns import router as campaigns_router
from gateway_api.routers.characters import router as characters_router
from gateway_api.routers.downtime import router as downtime_router
from gateway_api.routers.health import router as health_router
from gateway_api.routers.hub_views import router as hub_views_router
from gateway_api.routers.overlay import router as overlay_router
from gateway_api.routers.spectator import router as spectator_router

__all__ = [
    "auth_router",
    "campaigns_router",
    "characters_router",
    "downtime_router",
    "health_router",
    "hub_views_router",
    "overlay_router",
    "spectator_router",
]
