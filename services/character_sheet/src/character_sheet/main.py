"""Character Sheet Microservice - Powered by eventsource-py.

Manages player and NPC character sheets, hit points, inventories,
equipment, and status conditions (such as DM penalties for missed sessions).
"""

from __future__ import annotations

from character_sheet.dependencies import (
    STREAM_CHARACTER,
    get_event_bus,
    get_repository,
    get_spicedb_client,
    repo,
    set_event_bus,
    set_spicedb_client,
)
from character_sheet.router import router
from fastapi import FastAPI
from runefoble_platform.event_sourcing import get_event_store

app = FastAPI(
    title="Runefoble - Character Sheet Service",
    version="0.1.0",
    description="Character Stats, HP Tracking, Inventory, Equipment, and DM Penalties backed by eventsource-py.",
)

app.include_router(router)


@app.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "service": "character_sheet",
        "event_store": type(get_event_store()).__name__,
    }


@app.get("/ui/manifest")
def get_ui_manifest():
    """Advertise vendored microfrontend components for character sheet."""
    return {
        "service": "character_sheet",
        "package": "@runefoble/character-sheet-ui",
        "components": [
            "runefoble-character-card",
            "runefoble-absentee-recap",
            "runefoble-stand-in-guardrails",
        ],
        "version": "0.1.0",
    }


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
    "get_spicedb_client",
    "main",
    "repo",
    "router",
    "set_event_bus",
    "set_spicedb_client",
]
