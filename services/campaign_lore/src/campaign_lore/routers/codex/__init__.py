"""Modular Party Codex router combining entries and referencing sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from campaign_lore.routers.codex.entries import router as entries_router
from campaign_lore.routers.codex.referencing import router as referencing_router

router = APIRouter(prefix="/api/v1/campaigns/{campaign_id}/codex", tags=["Party Codex"])
router.include_router(entries_router)
router.include_router(referencing_router)

__all__ = ["router"]
