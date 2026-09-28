"""Character Sheet Microservice - Powered by eventsource-py.

Manages player and NPC character sheets, hit points, inventories,
equipment, and status conditions (such as DM penalties for missed sessions).
"""

from __future__ import annotations

import json
from pathlib import Path

from character_sheet.crafting_router import router as crafting_router
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
from character_sheet.wardrobe_router import router as wardrobe_router
from fastapi import FastAPI
from runefoble_platform.event_sourcing import get_event_store

app = FastAPI(
    title="Runefoble - Character Sheet Service",
    version="0.1.0",
    description="Character Stats, HP Tracking, Inventory, Equipment, and DM Penalties backed by eventsource-py.",
)

app.include_router(router)
app.include_router(crafting_router)
app.include_router(wardrobe_router)


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
    manifest_path = Path(__file__).resolve().parent.parent.parent / "ui" / "manifest.json"
    if manifest_path.is_file():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "service": "character_sheet",
        "package": "@runefoble/character-sheet-ui",
        "version": "0.1.0",
        "components": [
            "runefoble-character-card",
            "runefoble-absentee-recap",
            "runefoble-stand-in-guardrails",
            "runefoble-character-sheet",
            "runefoble-wardrobe-gallery",
            "runefoble-character-roster",
            "runefoble-character-builder-modal",
        ],
        "tags": [
            "runefoble-character-card",
            "runefoble-absentee-recap",
            "runefoble-stand-in-guardrails",
            "runefoble-character-sheet",
            "runefoble-wardrobe-gallery",
            "runefoble-character-roster",
            "runefoble-character-builder-modal",
        ],
        "styles": [
            "./src/runefoble-absentee-recap.styles.ts",
            "./src/runefoble-stand-in-guardrails.styles.ts",
            "./src/runefoble-character-sheet.styles.ts",
            "./src/runefoble-character-sheet.core.styles.ts",
            "./src/runefoble-character-sheet.inventory.styles.ts",
            "./src/runefoble-character-sheet.conditions.styles.ts",
            "./src/runefoble-wardrobe-gallery.styles.ts",
            "./src/roster/runefoble-character-roster.styles.ts",
            "./src/roster/runefoble-character-builder-modal.styles.ts",
        ],
        "scripts": [
            "./src/index.ts",
        ],
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
