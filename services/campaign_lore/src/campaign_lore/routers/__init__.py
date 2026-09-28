"""API Routers for Campaign Lore service."""

from campaign_lore.routers.codex import router as codex_router
from campaign_lore.routers.west_marches import router as west_marches_router

__all__ = ["codex_router", "west_marches_router"]
