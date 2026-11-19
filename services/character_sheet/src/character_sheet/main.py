"""Character Sheet Microservice - Powered by eventsource-py.

Manages player and NPC character sheets, hit points, inventories,
equipment, and status conditions (such as DM penalties for missed sessions).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from character_sheet.crafting_router import router as crafting_router
from character_sheet.dependencies import (
    STREAM_CHARACTER,
    event_bus_provider,
    get_event_bus,
    get_repository,
    repo,
    set_event_bus,
)
from character_sheet.router import router
from character_sheet.wardrobe_router import router as wardrobe_router
from fastapi import FastAPI
from runefoble_auth.authz_http import install_authz_error_handlers
from runefoble_platform.aggregate_loading import register_store_unavailable_handlers
from runefoble_platform.event_publish import event_publish_failures
from runefoble_platform.event_sourcing import event_store_kind, get_event_store
from runefoble_platform.ui_manifest import load_ui_manifest

# Start-up fails when the manifest is missing or invalid. No fallback manifest exists (ADR-0015 4).
UI_MANIFEST = load_ui_manifest(
    Path(__file__).resolve().parent.parent.parent / "ui" / "manifest.json"
)

# Build the event store now. A deployed service without a reachable store refuses to start (TASK-0707).
get_event_store()

app = FastAPI(
    title="Runefoble - Character Sheet Service",
    version="0.1.0",
    description="Character Stats, HP Tracking, Inventory, Equipment, and DM Penalties backed by eventsource-py.",
    lifespan=event_bus_provider.lifespan,
)

app.include_router(router)
app.include_router(crafting_router)
app.include_router(wardrobe_router)
register_store_unavailable_handlers(app)
install_authz_error_handlers(app)


@app.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "service": "character_sheet",
        "event_store": event_store_kind(),
        "event_publish_failures": event_publish_failures(),
    }


@app.get("/ui/manifest")
def get_ui_manifest() -> dict[str, Any]:
    """Advertise vendored microfrontend components for character sheet."""
    return UI_MANIFEST


def main():
    import uvicorn

    uvicorn.run("character_sheet.main:app", host="0.0.0.0", port=8003, reload=True)


if __name__ == "__main__":
    main()

__all__ = [
    "STREAM_CHARACTER",
    "app",
    "get_event_bus",
    "get_repository",
    "main",
    "repo",
    "router",
    "set_event_bus",
]
