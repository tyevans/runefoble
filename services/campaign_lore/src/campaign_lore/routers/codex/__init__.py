"""Modular Party Codex router combining entries and referencing sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from campaign_lore.routers.codex.entries import (
    get_entry,
    list_entries,
    publish_entry,
    update_entry,
)
from campaign_lore.routers.codex.entries import router as entries_router
from campaign_lore.routers.codex.referencing import (
    extract_references,
    get_entry_references,
)
from campaign_lore.routers.codex.referencing import router as referencing_router
from campaign_lore.routers.codex.schemas import (
    CrossReferenceContentRequest,
    CrossReferenceResponse,
    PublishCodexEntryRequest,
    UpdateCodexEntryRequest,
    format_codex_entry,
)

router = APIRouter(prefix="/api/v1/campaigns/{campaign_id}/codex", tags=["Party Codex"])
router.include_router(entries_router)
router.include_router(referencing_router)

__all__ = [
    "CrossReferenceContentRequest",
    "CrossReferenceResponse",
    "PublishCodexEntryRequest",
    "UpdateCodexEntryRequest",
    "entries_router",
    "extract_references",
    "format_codex_entry",
    "get_entry",
    "get_entry_references",
    "list_entries",
    "publish_entry",
    "referencing_router",
    "router",
    "update_entry",
]
