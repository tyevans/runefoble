"""Facade backward compatibility re-exporting modular codex router and schemas."""

from __future__ import annotations

from campaign_lore.routers.codex import (
    CrossReferenceContentRequest,
    CrossReferenceResponse,
    PublishCodexEntryRequest,
    UpdateCodexEntryRequest,
    entries_router,
    extract_references,
    format_codex_entry,
    get_entry,
    get_entry_references,
    list_entries,
    publish_entry,
    referencing_router,
    router,
    update_entry,
)

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
